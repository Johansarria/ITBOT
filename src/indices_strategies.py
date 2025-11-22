"""
SICAR Indices Strategies
Estrategias específicas para trading de índices
Incluye momentum, mean reversion y estrategias híbridas
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import logging
from dataclasses import dataclass
from enum import Enum

# Importar módulos del proyecto
from indices_indicators import IndicesIndicators
from market_hours_system import MarketHoursSystem, MarketSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StrategyType(Enum):
    """Tipos de estrategias"""
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    HYBRID = "hybrid"
    BREAKOUT = "breakout"
    TREND_FOLLOWING = "trend_following"

class SignalStrength(Enum):
    """Fuerza de las señales"""
    WEAK = 1
    MEDIUM = 2
    STRONG = 3

@dataclass
class StrategySignal:
    """Señal de trading generada por una estrategia"""
    timestamp: datetime
    signal: int  # -1 (sell), 0 (hold), 1 (buy)
    strength: SignalStrength
    confidence: float  # 0-1
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy_name: str = ""
    reason: str = ""

class IndicesStrategies:
    """
    Colección de estrategias específicas para índices
    Optimizadas para las características únicas de los índices
    """
    
    def __init__(self):
        self.indicators = IndicesIndicators()
        self.market_hours = MarketHoursSystem()
        
        # Configuraciones por defecto
        self.default_config = {
            'risk_per_trade': 0.02,  # 2%
            'stop_loss_pct': 0.05,   # 5%
            'take_profit_pct': 0.10, # 10%
            'max_hold_days': 30,
            'min_volume_ratio': 1.2,
            'volatility_threshold': 0.02
        }
    
    def momentum_strategy(self, data: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
        """
        Estrategia de momentum para índices
        Busca tendencias fuertes y las sigue
        
        Args:
            data: DataFrame con datos OHLCV e indicadores
            config: Configuración de la estrategia
        
        Returns:
            DataFrame con señales de trading
        """
        
        if config is None:
            config = self.default_config.copy()
        
        logger.info("Ejecutando estrategia de momentum para índices")
        
        # Verificar que tenemos los indicadores necesarios
        required_indicators = ['RSI', 'EMA_Fast', 'EMA_Slow', 'MACD', 'MACD_Signal', 'ATR']
        if not all(ind in data.columns for ind in required_indicators):
            logger.error("Faltan indicadores necesarios para la estrategia de momentum")
            return pd.DataFrame()
        
        signals = pd.DataFrame(index=data.index)
        signals['Signal'] = 0
        signals['Exit_Signal'] = 0
        signals['Strength'] = 0
        signals['Confidence'] = 0.0
        signals['Stop_Loss'] = np.nan
        signals['Take_Profit'] = np.nan
        
        # Parámetros de la estrategia
        rsi_oversold = config.get('rsi_oversold', 30)
        rsi_overbought = config.get('rsi_overbought', 70)
        volume_threshold = config.get('min_volume_ratio', 1.2)
        
        for i in range(1, len(data)):
            current_idx = data.index[i]
            prev_idx = data.index[i-1]
            
            current = data.iloc[i]
            previous = data.iloc[i-1]
            
            # Verificar horarios de mercado
            if not self._is_trading_time(current_idx):
                continue
            
            # Condiciones de entrada LONG (momentum alcista)
            momentum_long = (
                # Tendencia alcista confirmada
                current['EMA_Fast'] > current['EMA_Slow'] and
                previous['EMA_Fast'] <= previous['EMA_Slow'] and
                
                # MACD confirma momentum
                current['MACD'] > current['MACD_Signal'] and
                current['MACD'] > previous['MACD'] and
                
                # RSI no está sobrecomprado
                current['RSI'] < rsi_overbought and
                current['RSI'] > 50 and
                
                # Volumen confirma el movimiento
                self._check_volume_confirmation(current, config) and
                
                # Precio por encima de EMA rápida
                current['Close'] > current['EMA_Fast'] and
                
                # Filtro de volatilidad
                self._check_volatility_filter(current, config)
            )
            
            # Condiciones de entrada SHORT (momentum bajista)
            momentum_short = (
                # Tendencia bajista confirmada
                current['EMA_Fast'] < current['EMA_Slow'] and
                previous['EMA_Fast'] >= previous['EMA_Slow'] and
                
                # MACD confirma momentum bajista
                current['MACD'] < current['MACD_Signal'] and
                current['MACD'] < previous['MACD'] and
                
                # RSI no está sobrevendido
                current['RSI'] > rsi_oversold and
                current['RSI'] < 50 and
                
                # Volumen confirma el movimiento
                self._check_volume_confirmation(current, config) and
                
                # Precio por debajo de EMA rápida
                current['Close'] < current['EMA_Fast'] and
                
                # Filtro de volatilidad
                self._check_volatility_filter(current, config)
            )
            
            # Calcular fuerza y confianza de la señal
            if momentum_long:
                strength, confidence = self._calculate_signal_strength(current, 'long', config)
                signals.loc[current_idx, 'Signal'] = 1
                signals.loc[current_idx, 'Strength'] = strength
                signals.loc[current_idx, 'Confidence'] = confidence
                
                # Calcular stop loss y take profit
                atr_multiplier = config.get('atr_stop_multiplier', 2.0)
                stop_loss = current['Close'] - (current['ATR'] * atr_multiplier)
                take_profit = current['Close'] + (current['ATR'] * atr_multiplier * 2)
                
                signals.loc[current_idx, 'Stop_Loss'] = stop_loss
                signals.loc[current_idx, 'Take_Profit'] = take_profit
            
            elif momentum_short:
                strength, confidence = self._calculate_signal_strength(current, 'short', config)
                signals.loc[current_idx, 'Signal'] = -1
                signals.loc[current_idx, 'Strength'] = strength
                signals.loc[current_idx, 'Confidence'] = confidence
                
                # Calcular stop loss y take profit para short
                atr_multiplier = config.get('atr_stop_multiplier', 2.0)
                stop_loss = current['Close'] + (current['ATR'] * atr_multiplier)
                take_profit = current['Close'] - (current['ATR'] * atr_multiplier * 2)
                
                signals.loc[current_idx, 'Stop_Loss'] = stop_loss
                signals.loc[current_idx, 'Take_Profit'] = take_profit
        
        # Filtrar señales por calidad
        min_confidence = config.get('min_confidence', 0.6)
        signals.loc[signals['Confidence'] < min_confidence, 'Signal'] = 0
        
        logger.info(f"Estrategia de momentum generó {(signals['Signal'] != 0).sum()} señales")
        
        return signals
    
    def mean_reversion_strategy(self, data: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
        """
        Estrategia de reversión a la media para índices
        Busca sobreextensiones para entrar en contra de la tendencia
        
        Args:
            data: DataFrame con datos OHLCV e indicadores
            config: Configuración de la estrategia
        
        Returns:
            DataFrame con señales de trading
        """
        
        if config is None:
            config = self.default_config.copy()
        
        logger.info("Ejecutando estrategia de reversión a la media para índices")
        
        # Verificar indicadores necesarios
        required_indicators = ['RSI', 'BB_Upper', 'BB_Lower', 'BB_Middle', 'ATR']
        if not all(ind in data.columns for ind in required_indicators):
            logger.error("Faltan indicadores necesarios para la estrategia de reversión a la media")
            return pd.DataFrame()
        
        signals = pd.DataFrame(index=data.index)
        signals['Signal'] = 0
        signals['Exit_Signal'] = 0
        signals['Strength'] = 0
        signals['Confidence'] = 0.0
        signals['Stop_Loss'] = np.nan
        signals['Take_Profit'] = np.nan
        
        # Parámetros de la estrategia
        rsi_oversold = config.get('rsi_oversold', 25)
        rsi_overbought = config.get('rsi_overbought', 75)
        
        for i in range(2, len(data)):
            current_idx = data.index[i]
            current = data.iloc[i]
            previous = data.iloc[i-1]
            prev2 = data.iloc[i-2]
            
            # Verificar horarios de mercado
            if not self._is_trading_time(current_idx):
                continue
            
            # Condiciones de entrada LONG (reversión desde sobrevendido)
            mean_reversion_long = (
                # RSI sobrevendido y empezando a recuperar
                current['RSI'] < rsi_oversold and
                current['RSI'] > previous['RSI'] and
                previous['RSI'] > prev2['RSI'] and
                
                # Precio tocó o atravesó banda inferior
                (previous['Close'] <= previous['BB_Lower'] or
                 current['Close'] <= current['BB_Lower']) and
                current['Close'] > previous['Close'] and
                
                # Volumen confirma el rebote
                self._check_volume_confirmation(current, config) and
                
                # No estamos en una tendencia bajista muy fuerte
                current['Close'] > current['BB_Middle'] * 0.98 and
                
                # Filtro de volatilidad
                self._check_volatility_filter(current, config)
            )
            
            # Condiciones de entrada SHORT (reversión desde sobrecomprado)
            mean_reversion_short = (
                # RSI sobrecomprado y empezando a declinar
                current['RSI'] > rsi_overbought and
                current['RSI'] < previous['RSI'] and
                previous['RSI'] < prev2['RSI'] and
                
                # Precio tocó o atravesó banda superior
                (previous['Close'] >= previous['BB_Upper'] or
                 current['Close'] >= current['BB_Upper']) and
                current['Close'] < previous['Close'] and
                
                # Volumen confirma la caída
                self._check_volume_confirmation(current, config) and
                
                # No estamos en una tendencia alcista muy fuerte
                current['Close'] < current['BB_Middle'] * 1.02 and
                
                # Filtro de volatilidad
                self._check_volatility_filter(current, config)
            )
            
            # Calcular señales
            if mean_reversion_long:
                strength, confidence = self._calculate_signal_strength(current, 'long', config)
                signals.loc[current_idx, 'Signal'] = 1
                signals.loc[current_idx, 'Strength'] = strength
                signals.loc[current_idx, 'Confidence'] = confidence
                
                # Stop loss más ajustado para reversión a la media
                stop_loss = current['BB_Lower'] * 0.995
                take_profit = current['BB_Middle']
                
                signals.loc[current_idx, 'Stop_Loss'] = stop_loss
                signals.loc[current_idx, 'Take_Profit'] = take_profit
            
            elif mean_reversion_short:
                strength, confidence = self._calculate_signal_strength(current, 'short', config)
                signals.loc[current_idx, 'Signal'] = -1
                signals.loc[current_idx, 'Strength'] = strength
                signals.loc[current_idx, 'Confidence'] = confidence
                
                # Stop loss más ajustado para reversión a la media
                stop_loss = current['BB_Upper'] * 1.005
                take_profit = current['BB_Middle']
                
                signals.loc[current_idx, 'Stop_Loss'] = stop_loss
                signals.loc[current_idx, 'Take_Profit'] = take_profit
        
        # Filtrar señales por calidad
        min_confidence = config.get('min_confidence', 0.65)
        signals.loc[signals['Confidence'] < min_confidence, 'Signal'] = 0
        
        logger.info(f"Estrategia de reversión a la media generó {(signals['Signal'] != 0).sum()} señales")
        
        return signals
    
    def hybrid_strategy(self, data: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
        """
        Estrategia híbrida que combina momentum y reversión a la media
        Adapta el enfoque según las condiciones del mercado
        
        Args:
            data: DataFrame con datos OHLCV e indicadores
            config: Configuración de la estrategia
        
        Returns:
            DataFrame con señales de trading
        """
        
        if config is None:
            config = self.default_config.copy()
        
        logger.info("Ejecutando estrategia híbrida para índices")
        
        # Verificar indicadores necesarios
        required_indicators = ['RSI', 'EMA_Fast', 'EMA_Slow', 'MACD', 'MACD_Signal', 
                              'BB_Upper', 'BB_Lower', 'BB_Middle', 'ATR', 'Market_Regime']
        if not all(ind in data.columns for ind in required_indicators):
            logger.error("Faltan indicadores necesarios para la estrategia híbrida")
            return pd.DataFrame()
        
        # Generar señales de ambas estrategias
        momentum_signals = self.momentum_strategy(data, config)
        mean_reversion_signals = self.mean_reversion_strategy(data, config)
        
        if momentum_signals.empty or mean_reversion_signals.empty:
            return pd.DataFrame()
        
        # Combinar señales basado en el régimen de mercado
        signals = pd.DataFrame(index=data.index)
        signals['Signal'] = 0
        signals['Exit_Signal'] = 0
        signals['Strength'] = 0
        signals['Confidence'] = 0.0
        signals['Stop_Loss'] = np.nan
        signals['Take_Profit'] = np.nan
        signals['Strategy_Used'] = ""
        
        for i in range(len(data)):
            current_idx = data.index[i]
            current = data.iloc[i]
            
            # Determinar qué estrategia usar basado en el régimen de mercado
            market_regime = current.get('Market_Regime', 'trending')
            
            if market_regime == 'trending':
                # En mercados con tendencia, usar momentum
                if current_idx in momentum_signals.index:
                    momentum_signal = momentum_signals.loc[current_idx]
                    if momentum_signal['Signal'] != 0:
                        signals.loc[current_idx] = momentum_signal
                        signals.loc[current_idx, 'Strategy_Used'] = 'momentum'
            
            elif market_regime == 'ranging':
                # En mercados laterales, usar reversión a la media
                if current_idx in mean_reversion_signals.index:
                    mr_signal = mean_reversion_signals.loc[current_idx]
                    if mr_signal['Signal'] != 0:
                        signals.loc[current_idx] = mr_signal
                        signals.loc[current_idx, 'Strategy_Used'] = 'mean_reversion'
            
            else:
                # En mercados inciertos, usar la señal con mayor confianza
                momentum_conf = 0
                mr_conf = 0
                
                if current_idx in momentum_signals.index:
                    momentum_conf = momentum_signals.loc[current_idx, 'Confidence']
                
                if current_idx in mean_reversion_signals.index:
                    mr_conf = mean_reversion_signals.loc[current_idx, 'Confidence']
                
                if momentum_conf > mr_conf and momentum_conf > 0.7:
                    if current_idx in momentum_signals.index:
                        momentum_signal = momentum_signals.loc[current_idx]
                        if momentum_signal['Signal'] != 0:
                            signals.loc[current_idx] = momentum_signal
                            signals.loc[current_idx, 'Strategy_Used'] = 'momentum'
                
                elif mr_conf > 0.7:
                    if current_idx in mean_reversion_signals.index:
                        mr_signal = mean_reversion_signals.loc[current_idx]
                        if mr_signal['Signal'] != 0:
                            signals.loc[current_idx] = mr_signal
                            signals.loc[current_idx, 'Strategy_Used'] = 'mean_reversion'
        
        logger.info(f"Estrategia híbrida generó {(signals['Signal'] != 0).sum()} señales")
        
        return signals
    
    def breakout_strategy(self, data: pd.DataFrame, config: Dict = None) -> pd.DataFrame:
        """
        Estrategia de breakout para índices
        Busca rupturas de niveles clave con confirmación
        
        Args:
            data: DataFrame con datos OHLCV e indicadores
            config: Configuración de la estrategia
        
        Returns:
            DataFrame con señales de trading
        """
        
        if config is None:
            config = self.default_config.copy()
        
        logger.info("Ejecutando estrategia de breakout para índices")
        
        signals = pd.DataFrame(index=data.index)
        signals['Signal'] = 0
        signals['Exit_Signal'] = 0
        signals['Strength'] = 0
        signals['Confidence'] = 0.0
        signals['Stop_Loss'] = np.nan
        signals['Take_Profit'] = np.nan
        
        # Parámetros de la estrategia
        lookback_period = config.get('breakout_lookback', 20)
        volume_multiplier = config.get('breakout_volume_multiplier', 1.5)
        
        # Calcular niveles de soporte y resistencia
        data['Resistance'] = data['High'].rolling(window=lookback_period).max()
        data['Support'] = data['Low'].rolling(window=lookback_period).min()
        
        for i in range(lookback_period, len(data)):
            current_idx = data.index[i]
            current = data.iloc[i]
            previous = data.iloc[i-1]
            
            # Verificar horarios de mercado
            if not self._is_trading_time(current_idx):
                continue
            
            # Breakout alcista
            breakout_long = (
                # Precio rompe resistencia
                current['Close'] > previous['Resistance'] and
                previous['Close'] <= previous['Resistance'] and
                
                # Confirmación con volumen
                self._check_volume_confirmation(current, config, volume_multiplier) and
                
                # Momentum confirma
                current['Close'] > current['Open'] and
                
                # Filtro de volatilidad
                self._check_volatility_filter(current, config)
            )
            
            # Breakout bajista
            breakout_short = (
                # Precio rompe soporte
                current['Close'] < previous['Support'] and
                previous['Close'] >= previous['Support'] and
                
                # Confirmación con volumen
                self._check_volume_confirmation(current, config, volume_multiplier) and
                
                # Momentum confirma
                current['Close'] < current['Open'] and
                
                # Filtro de volatilidad
                self._check_volatility_filter(current, config)
            )
            
            if breakout_long:
                strength, confidence = self._calculate_signal_strength(current, 'long', config)
                signals.loc[current_idx, 'Signal'] = 1
                signals.loc[current_idx, 'Strength'] = strength
                signals.loc[current_idx, 'Confidence'] = confidence
                
                # Stop loss en el nivel de resistencia anterior
                stop_loss = previous['Resistance'] * 0.995
                take_profit = current['Close'] + (current['Close'] - stop_loss) * 2
                
                signals.loc[current_idx, 'Stop_Loss'] = stop_loss
                signals.loc[current_idx, 'Take_Profit'] = take_profit
            
            elif breakout_short:
                strength, confidence = self._calculate_signal_strength(current, 'short', config)
                signals.loc[current_idx, 'Signal'] = -1
                signals.loc[current_idx, 'Strength'] = strength
                signals.loc[current_idx, 'Confidence'] = confidence
                
                # Stop loss en el nivel de soporte anterior
                stop_loss = previous['Support'] * 1.005
                take_profit = current['Close'] - (stop_loss - current['Close']) * 2
                
                signals.loc[current_idx, 'Stop_Loss'] = stop_loss
                signals.loc[current_idx, 'Take_Profit'] = take_profit
        
        # Filtrar señales por calidad
        min_confidence = config.get('min_confidence', 0.7)
        signals.loc[signals['Confidence'] < min_confidence, 'Signal'] = 0
        
        logger.info(f"Estrategia de breakout generó {(signals['Signal'] != 0).sum()} señales")
        
        return signals
    
    def _is_trading_time(self, timestamp) -> bool:
        """Verifica si es momento válido para trading"""
        
        # Convertir timestamp si es necesario
        if isinstance(timestamp, str):
            dt = datetime.strptime(timestamp, '%Y-%m-%d')
        else:
            dt = timestamp
        
        # Verificar día de trading
        market_day = self.market_hours.get_market_day_info(dt.date())
        return market_day.is_trading_day
    
    def _check_volume_confirmation(self, current_data: pd.Series, config: Dict, 
                                  multiplier: float = None) -> bool:
        """Verifica confirmación por volumen"""
        
        if 'Volume_Ratio' not in current_data:
            return True  # Si no hay datos de volumen, no filtrar
        
        if multiplier is None:
            multiplier = config.get('min_volume_ratio', 1.2)
        
        return current_data['Volume_Ratio'] >= multiplier
    
    def _check_volatility_filter(self, current_data: pd.Series, config: Dict) -> bool:
        """Verifica filtro de volatilidad"""
        
        if 'ATR' not in current_data:
            return True  # Si no hay ATR, no filtrar
        
        # Calcular volatilidad como porcentaje del precio
        volatility_pct = current_data['ATR'] / current_data['Close']
        
        min_volatility = config.get('min_volatility', 0.005)  # 0.5%
        max_volatility = config.get('max_volatility', 0.05)   # 5%
        
        return min_volatility <= volatility_pct <= max_volatility
    
    def _calculate_signal_strength(self, current_data: pd.Series, direction: str, 
                                  config: Dict) -> Tuple[int, float]:
        """Calcula la fuerza y confianza de una señal"""
        
        strength_score = 0
        confidence_factors = []
        
        # Factor RSI
        if 'RSI' in current_data:
            rsi = current_data['RSI']
            if direction == 'long':
                if rsi < 30:
                    strength_score += 3
                    confidence_factors.append(0.9)
                elif rsi < 50:
                    strength_score += 2
                    confidence_factors.append(0.7)
                else:
                    strength_score += 1
                    confidence_factors.append(0.5)
            else:  # short
                if rsi > 70:
                    strength_score += 3
                    confidence_factors.append(0.9)
                elif rsi > 50:
                    strength_score += 2
                    confidence_factors.append(0.7)
                else:
                    strength_score += 1
                    confidence_factors.append(0.5)
        
        # Factor MACD
        if 'MACD' in current_data and 'MACD_Signal' in current_data:
            macd_diff = current_data['MACD'] - current_data['MACD_Signal']
            if direction == 'long' and macd_diff > 0:
                strength_score += 2
                confidence_factors.append(0.8)
            elif direction == 'short' and macd_diff < 0:
                strength_score += 2
                confidence_factors.append(0.8)
        
        # Factor volumen
        if 'Volume_Ratio' in current_data:
            vol_ratio = current_data['Volume_Ratio']
            if vol_ratio > 2.0:
                strength_score += 3
                confidence_factors.append(0.9)
            elif vol_ratio > 1.5:
                strength_score += 2
                confidence_factors.append(0.7)
            elif vol_ratio > 1.2:
                strength_score += 1
                confidence_factors.append(0.6)
        
        # Factor de sesión
        if 'Session_Effect' in current_data:
            session_effect = current_data['Session_Effect']
            if abs(session_effect) > 0.5:
                strength_score += 1
                confidence_factors.append(0.6)
        
        # Determinar fuerza final
        if strength_score >= 7:
            strength = SignalStrength.STRONG.value
        elif strength_score >= 4:
            strength = SignalStrength.MEDIUM.value
        else:
            strength = SignalStrength.WEAK.value
        
        # Calcular confianza promedio
        confidence = np.mean(confidence_factors) if confidence_factors else 0.5
        
        return strength, confidence
    
    def get_strategy_performance_summary(self, signals: pd.DataFrame, 
                                       data: pd.DataFrame) -> Dict:
        """
        Genera un resumen de rendimiento de la estrategia
        
        Args:
            signals: DataFrame con señales generadas
            data: DataFrame con datos de precios
        
        Returns:
            Diccionario con métricas de rendimiento
        """
        
        if signals.empty or (signals['Signal'] == 0).all():
            return {
                'total_signals': 0,
                'signal_frequency': 0,
                'avg_confidence': 0,
                'strong_signals': 0,
                'medium_signals': 0,
                'weak_signals': 0
            }
        
        # Contar señales por fuerza
        signal_counts = signals[signals['Signal'] != 0]['Strength'].value_counts()
        
        total_signals = (signals['Signal'] != 0).sum()
        signal_frequency = total_signals / len(signals) * 100
        avg_confidence = signals[signals['Signal'] != 0]['Confidence'].mean()
        
        return {
            'total_signals': total_signals,
            'signal_frequency': signal_frequency,
            'avg_confidence': avg_confidence,
            'strong_signals': signal_counts.get(3, 0),
            'medium_signals': signal_counts.get(2, 0),
            'weak_signals': signal_counts.get(1, 0),
            'long_signals': (signals['Signal'] == 1).sum(),
            'short_signals': (signals['Signal'] == -1).sum()
        }

# Funciones de utilidad para usar las estrategias

def create_momentum_strategy() -> IndicesStrategies:
    """Crea una instancia de estrategias configurada para momentum"""
    return IndicesStrategies()

def create_mean_reversion_strategy() -> IndicesStrategies:
    """Crea una instancia de estrategias configurada para reversión a la media"""
    return IndicesStrategies()

def create_hybrid_strategy() -> IndicesStrategies:
    """Crea una instancia de estrategias híbrida"""
    return IndicesStrategies()

# Configuraciones predefinidas para diferentes tipos de mercado

MOMENTUM_CONFIG = {
    'risk_per_trade': 0.02,
    'stop_loss_pct': 0.04,
    'take_profit_pct': 0.08,
    'max_hold_days': 20,
    'min_volume_ratio': 1.3,
    'min_volatility': 0.008,
    'max_volatility': 0.04,
    'rsi_oversold': 35,
    'rsi_overbought': 65,
    'atr_stop_multiplier': 2.0,
    'min_confidence': 0.6
}

MEAN_REVERSION_CONFIG = {
    'risk_per_trade': 0.015,
    'stop_loss_pct': 0.03,
    'take_profit_pct': 0.06,
    'max_hold_days': 10,
    'min_volume_ratio': 1.2,
    'min_volatility': 0.005,
    'max_volatility': 0.03,
    'rsi_oversold': 25,
    'rsi_overbought': 75,
    'min_confidence': 0.65
}

BREAKOUT_CONFIG = {
    'risk_per_trade': 0.025,
    'stop_loss_pct': 0.05,
    'take_profit_pct': 0.12,
    'max_hold_days': 30,
    'min_volume_ratio': 1.5,
    'breakout_volume_multiplier': 1.8,
    'breakout_lookback': 20,
    'min_volatility': 0.01,
    'max_volatility': 0.06,
    'min_confidence': 0.7
}

HYBRID_CONFIG = {
    'risk_per_trade': 0.02,
    'stop_loss_pct': 0.04,
    'take_profit_pct': 0.08,
    'max_hold_days': 25,
    'min_volume_ratio': 1.25,
    'min_volatility': 0.006,
    'max_volatility': 0.045,
    'rsi_oversold': 30,
    'rsi_overbought': 70,
    'atr_stop_multiplier': 2.0,
    'min_confidence': 0.65
}

if __name__ == "__main__":
    # Ejemplo de uso
    strategies = IndicesStrategies()
    
    # Crear datos de ejemplo
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
    np.random.seed(42)
    
    data = pd.DataFrame({
        'Open': 100 + np.random.randn(len(dates)).cumsum() * 0.5,
        'High': 100 + np.random.randn(len(dates)).cumsum() * 0.5 + 1,
        'Low': 100 + np.random.randn(len(dates)).cumsum() * 0.5 - 1,
        'Close': 100 + np.random.randn(len(dates)).cumsum() * 0.5,
        'Volume': np.random.randint(1000000, 5000000, len(dates))
    }, index=dates)
    
    # Agregar indicadores básicos para el ejemplo
    indicators = IndicesIndicators()
    data['RSI'] = indicators.rsi(data['Close'], 14)
    data['EMA_Fast'] = indicators.ema(data['Close'], 12)
    data['EMA_Slow'] = indicators.ema(data['Close'], 26)
    
    macd_data = indicators.macd(data['Close'], 12, 26, 9)
    data = pd.concat([data, macd_data], axis=1)
    
    bb_data = indicators.bollinger_bands(data['Close'], 20, 2)
    data = pd.concat([data, bb_data], axis=1)
    
    data['ATR'] = indicators.atr(data['High'], data['Low'], data['Close'], 14)
    data['Volume_SMA'] = indicators.sma(data['Volume'], 20)
    data['Volume_Ratio'] = data['Volume'] / data['Volume_SMA']
    data['Market_Regime'] = 'trending'
    
    # Probar estrategia de momentum
    momentum_signals = strategies.momentum_strategy(data, MOMENTUM_CONFIG)
    print(f"Señales de momentum generadas: {(momentum_signals['Signal'] != 0).sum()}")
    
    # Resumen de rendimiento
    performance = strategies.get_strategy_performance_summary(momentum_signals, data)
    print(f"Resumen de rendimiento: {performance}")