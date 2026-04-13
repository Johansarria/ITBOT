#!/usr/bin/env python3
"""
Sistema de Estrategias de Trading Adaptativas

Implementa estrategias modulares que se adaptan automáticamente a los regímenes
de mercado detectados por el sistema de detección de regímenes.

Estrategias Implementadas:
1. Seguimiento de Tendencia (para baja volatilidad)
2. Reversión a la Media (para alta volatilidad)
3. Estrategia Conservadora (para volatilidad media)

Autor: Sistema de Trading Adaptativo
Fecha: 2024
Versión: 1.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import warnings
warnings.filterwarnings('ignore')

from adaptive_regime_detector import MarketRegime, RegimeSignal

class SignalType(Enum):
    """Tipos de señales de trading"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"

class PositionType(Enum):
    """Tipos de posición"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"

@dataclass
class TradingSignal:
    """Señal de trading generada por una estrategia"""
    signal_type: SignalType
    confidence: float
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_size: float
    timestamp: pd.Timestamp
    strategy_name: str
    regime: MarketRegime
    additional_info: Dict = None

@dataclass
class Position:
    """Posición de trading activa"""
    position_type: PositionType
    entry_price: float
    size: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_time: pd.Timestamp
    strategy_name: str
    unrealized_pnl: float = 0.0

class TechnicalIndicators:
    """Clase utilitaria para cálculo de indicadores técnicos"""
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD Indicator"""
        ema_fast = data.ewm(span=fast).mean()
        ema_slow = data.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

class BaseStrategy(ABC):
    """Clase base para todas las estrategias de trading"""
    
    def __init__(self, name: str):
        self.name = name
        self.indicators = TechnicalIndicators()
        self.active_positions: List[Position] = []
        self.signal_history: List[TradingSignal] = []
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, regime: MarketRegime) -> List[TradingSignal]:
        """Generar señales de trading basadas en el régimen actual"""
        pass
    
    @abstractmethod
    def is_suitable_for_regime(self, regime: MarketRegime) -> bool:
        """Verificar si la estrategia es adecuada para el régimen dado"""
        pass
    
    def update_positions(self, current_price: float, timestamp: pd.Timestamp):
        """Actualizar PnL de posiciones activas"""
        for position in self.active_positions:
            if position.position_type == PositionType.LONG:
                position.unrealized_pnl = (current_price - position.entry_price) * position.size
            elif position.position_type == PositionType.SHORT:
                position.unrealized_pnl = (position.entry_price - current_price) * position.size

class TrendFollowingStrategy(BaseStrategy):
    """
    Estrategia de seguimiento de tendencia.
    
    Óptima para regímenes de baja volatilidad donde las tendencias son más claras.
    Usa cruces de medias móviles y confirmación con MACD.
    """
    
    def __init__(self, 
                 sma_fast: int = 10,
                 sma_slow: int = 20,
                 atr_multiplier: float = 2.0,
                 min_trend_strength: float = 0.02):
        super().__init__("TrendFollowing")
        self.sma_fast = sma_fast
        self.sma_slow = sma_slow
        self.atr_multiplier = atr_multiplier
        self.min_trend_strength = min_trend_strength
    
    def is_suitable_for_regime(self, regime: MarketRegime) -> bool:
        """Adecuada para baja volatilidad"""
        return regime == MarketRegime.LOW_VOLATILITY
    
    def generate_signals(self, data: pd.DataFrame, regime: MarketRegime) -> List[TradingSignal]:
        """Generar señales de seguimiento de tendencia"""
        if not self.is_suitable_for_regime(regime):
            return []
        
        signals = []
        close = data['close']
        high = data['high']
        low = data['low']
        
        # Calcular indicadores
        sma_fast = self.indicators.sma(close, self.sma_fast)
        sma_slow = self.indicators.sma(close, self.sma_slow)
        atr = self.indicators.atr(high, low, close)
        macd_line, macd_signal, macd_hist = self.indicators.macd(close)
        
        # Detectar cruces de medias móviles
        crossover = (sma_fast > sma_slow) & (sma_fast.shift(1) <= sma_slow.shift(1))
        crossunder = (sma_fast < sma_slow) & (sma_fast.shift(1) >= sma_slow.shift(1))
        
        for i, (idx, row) in enumerate(data.iterrows()):
            if i < max(self.sma_slow, 26):  # Esperar suficientes datos
                continue
            
            current_price = row['close']
            current_atr = atr.iloc[i]
            
            if pd.isna(current_atr) or pd.isna(sma_fast.iloc[i]) or pd.isna(sma_slow.iloc[i]):
                continue
            
            # Señal de compra (cruce alcista)
            if crossover.iloc[i]:
                # Confirmar con MACD
                macd_confirmation = macd_line.iloc[i] > macd_signal.iloc[i]
                
                # Verificar fuerza de tendencia
                trend_strength = abs(sma_fast.iloc[i] - sma_slow.iloc[i]) / current_price
                
                if macd_confirmation and trend_strength >= self.min_trend_strength:
                    stop_loss = current_price - (current_atr * self.atr_multiplier)
                    take_profit = current_price + (current_atr * self.atr_multiplier * 2)
                    
                    signal = TradingSignal(
                        signal_type=SignalType.BUY,
                        confidence=min(trend_strength * 10, 1.0),
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        position_size=1.0,  # Se ajustará por risk management
                        timestamp=idx,
                        strategy_name=self.name,
                        regime=regime,
                        additional_info={
                            'sma_fast': sma_fast.iloc[i],
                            'sma_slow': sma_slow.iloc[i],
                            'trend_strength': trend_strength,
                            'macd_confirmation': macd_confirmation
                        }
                    )
                    signals.append(signal)
            
            # Señal de venta (cruce bajista)
            elif crossunder.iloc[i]:
                # Confirmar con MACD
                macd_confirmation = macd_line.iloc[i] < macd_signal.iloc[i]
                
                # Verificar fuerza de tendencia
                trend_strength = abs(sma_fast.iloc[i] - sma_slow.iloc[i]) / current_price
                
                if macd_confirmation and trend_strength >= self.min_trend_strength:
                    stop_loss = current_price + (current_atr * self.atr_multiplier)
                    take_profit = current_price - (current_atr * self.atr_multiplier * 2)
                    
                    signal = TradingSignal(
                        signal_type=SignalType.SELL,
                        confidence=min(trend_strength * 10, 1.0),
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        position_size=1.0,
                        timestamp=idx,
                        strategy_name=self.name,
                        regime=regime,
                        additional_info={
                            'sma_fast': sma_fast.iloc[i],
                            'sma_slow': sma_slow.iloc[i],
                            'trend_strength': trend_strength,
                            'macd_confirmation': macd_confirmation
                        }
                    )
                    signals.append(signal)
        
        return signals

class MeanReversionStrategy(BaseStrategy):
    """
    Estrategia de reversión a la media.
    
    Óptima para regímenes de alta volatilidad donde los precios tienden a revertir.
    Usa RSI y Bandas de Bollinger para identificar extremos.
    """
    
    def __init__(self,
                 rsi_period: int = 14,
                 rsi_oversold: float = 30,
                 rsi_overbought: float = 70,
                 bb_period: int = 20,
                 bb_std: float = 2.0,
                 atr_multiplier: float = 1.5):
        super().__init__("MeanReversion")
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.atr_multiplier = atr_multiplier
    
    def is_suitable_for_regime(self, regime: MarketRegime) -> bool:
        """Adecuada para alta volatilidad"""
        return regime == MarketRegime.HIGH_VOLATILITY
    
    def generate_signals(self, data: pd.DataFrame, regime: MarketRegime) -> List[TradingSignal]:
        """Generar señales de reversión a la media"""
        if not self.is_suitable_for_regime(regime):
            return []
        
        signals = []
        close = data['close']
        high = data['high']
        low = data['low']
        
        # Calcular indicadores
        rsi = self.indicators.rsi(close, self.rsi_period)
        bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(close, self.bb_period, self.bb_std)
        atr = self.indicators.atr(high, low, close)
        
        for i, (idx, row) in enumerate(data.iterrows()):
            if i < max(self.rsi_period, self.bb_period):
                continue
            
            current_price = row['close']
            current_rsi = rsi.iloc[i]
            current_atr = atr.iloc[i]
            
            if pd.isna(current_rsi) or pd.isna(current_atr):
                continue
            
            # Señal de compra (sobreventa)
            if (current_rsi <= self.rsi_oversold and 
                current_price <= bb_lower.iloc[i]):
                
                # Calcular confianza basada en extremos
                rsi_extreme = (self.rsi_oversold - current_rsi) / self.rsi_oversold
                bb_extreme = (bb_lower.iloc[i] - current_price) / bb_lower.iloc[i]
                confidence = min((rsi_extreme + bb_extreme) / 2, 1.0)
                
                stop_loss = current_price - (current_atr * self.atr_multiplier)
                take_profit = bb_middle.iloc[i]  # Objetivo: media de BB
                
                signal = TradingSignal(
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=1.0,
                    timestamp=idx,
                    strategy_name=self.name,
                    regime=regime,
                    additional_info={
                        'rsi': current_rsi,
                        'bb_position': (current_price - bb_lower.iloc[i]) / (bb_upper.iloc[i] - bb_lower.iloc[i]),
                        'rsi_extreme': rsi_extreme,
                        'bb_extreme': bb_extreme
                    }
                )
                signals.append(signal)
            
            # Señal de venta (sobrecompra)
            elif (current_rsi >= self.rsi_overbought and 
                  current_price >= bb_upper.iloc[i]):
                
                # Calcular confianza basada en extremos
                rsi_extreme = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
                bb_extreme = (current_price - bb_upper.iloc[i]) / bb_upper.iloc[i]
                confidence = min((rsi_extreme + bb_extreme) / 2, 1.0)
                
                stop_loss = current_price + (current_atr * self.atr_multiplier)
                take_profit = bb_middle.iloc[i]  # Objetivo: media de BB
                
                signal = TradingSignal(
                    signal_type=SignalType.SELL,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=1.0,
                    timestamp=idx,
                    strategy_name=self.name,
                    regime=regime,
                    additional_info={
                        'rsi': current_rsi,
                        'bb_position': (current_price - bb_lower.iloc[i]) / (bb_upper.iloc[i] - bb_lower.iloc[i]),
                        'rsi_extreme': rsi_extreme,
                        'bb_extreme': bb_extreme
                    }
                )
                signals.append(signal)
        
        return signals

class ConservativeStrategy(BaseStrategy):
    """
    Estrategia conservadora para volatilidad media.
    
    Usa múltiples confirmaciones y posiciones más pequeñas.
    Combina elementos de tendencia y reversión con filtros adicionales.
    """
    
    def __init__(self,
                 ema_fast: int = 12,
                 ema_slow: int = 26,
                 rsi_period: int = 14,
                 rsi_neutral_low: float = 40,
                 rsi_neutral_high: float = 60,
                 atr_multiplier: float = 1.8):
        super().__init__("Conservative")
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_neutral_low = rsi_neutral_low
        self.rsi_neutral_high = rsi_neutral_high
        self.atr_multiplier = atr_multiplier
    
    def is_suitable_for_regime(self, regime: MarketRegime) -> bool:
        """Adecuada para volatilidad media"""
        return regime == MarketRegime.MEDIUM_VOLATILITY
    
    def generate_signals(self, data: pd.DataFrame, regime: MarketRegime) -> List[TradingSignal]:
        """Generar señales conservadoras"""
        if not self.is_suitable_for_regime(regime):
            return []
        
        signals = []
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data.get('volume', pd.Series(index=data.index, data=1))
        
        # Calcular indicadores
        ema_fast = self.indicators.ema(close, self.ema_fast)
        ema_slow = self.indicators.ema(close, self.ema_slow)
        rsi = self.indicators.rsi(close, self.rsi_period)
        atr = self.indicators.atr(high, low, close)
        macd_line, macd_signal, macd_hist = self.indicators.macd(close)
        
        # Volumen promedio para filtro
        volume_ma = volume.rolling(window=20).mean()
        
        for i, (idx, row) in enumerate(data.iterrows()):
            if i < max(self.ema_slow, self.rsi_period, 26):
                continue
            
            current_price = row['close']
            current_rsi = rsi.iloc[i]
            current_atr = atr.iloc[i]
            current_volume = volume.iloc[i]
            
            if pd.isna(current_rsi) or pd.isna(current_atr):
                continue
            
            # Filtros de confirmación
            ema_bullish = ema_fast.iloc[i] > ema_slow.iloc[i]
            ema_bearish = ema_fast.iloc[i] < ema_slow.iloc[i]
            rsi_neutral = self.rsi_neutral_low <= current_rsi <= self.rsi_neutral_high
            volume_confirmation = current_volume > volume_ma.iloc[i] * 1.2
            macd_bullish = macd_line.iloc[i] > macd_signal.iloc[i]
            macd_bearish = macd_line.iloc[i] < macd_signal.iloc[i]
            
            # Señal de compra conservadora
            if (ema_bullish and rsi_neutral and volume_confirmation and macd_bullish):
                confidence = 0.6  # Confianza moderada por naturaleza conservadora
                
                stop_loss = current_price - (current_atr * self.atr_multiplier)
                take_profit = current_price + (current_atr * self.atr_multiplier * 1.5)
                
                signal = TradingSignal(
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=0.5,  # Posición más pequeña
                    timestamp=idx,
                    strategy_name=self.name,
                    regime=regime,
                    additional_info={
                        'ema_fast': ema_fast.iloc[i],
                        'ema_slow': ema_slow.iloc[i],
                        'rsi': current_rsi,
                        'volume_ratio': current_volume / volume_ma.iloc[i],
                        'macd_bullish': macd_bullish
                    }
                )
                signals.append(signal)
            
            # Señal de venta conservadora
            elif (ema_bearish and rsi_neutral and volume_confirmation and macd_bearish):
                confidence = 0.6
                
                stop_loss = current_price + (current_atr * self.atr_multiplier)
                take_profit = current_price - (current_atr * self.atr_multiplier * 1.5)
                
                signal = TradingSignal(
                    signal_type=SignalType.SELL,
                    confidence=confidence,
                    entry_price=current_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    position_size=0.5,
                    timestamp=idx,
                    strategy_name=self.name,
                    regime=regime,
                    additional_info={
                        'ema_fast': ema_fast.iloc[i],
                        'ema_slow': ema_slow.iloc[i],
                        'rsi': current_rsi,
                        'volume_ratio': current_volume / volume_ma.iloc[i],
                        'macd_bearish': macd_bearish
                    }
                )
                signals.append(signal)
        
        return signals

class AdaptiveStrategyManager:
    """
    Gestor de estrategias adaptativo que selecciona automáticamente
    la estrategia más adecuada según el régimen de mercado detectado.
    """
    
    def __init__(self):
        self.strategies = {
            MarketRegime.LOW_VOLATILITY: TrendFollowingStrategy(),
            MarketRegime.HIGH_VOLATILITY: MeanReversionStrategy(),
            MarketRegime.MEDIUM_VOLATILITY: ConservativeStrategy()
        }
        
        self.signal_history: List[TradingSignal] = []
        self.regime_history: List[Tuple[pd.Timestamp, MarketRegime]] = []
    
    def generate_adaptive_signals(self, 
                                data: pd.DataFrame, 
                                regime_signals: List[RegimeSignal]) -> List[TradingSignal]:
        """
        Generar señales adaptativas basadas en regímenes detectados.
        
        Args:
            data: DataFrame con datos OHLCV
            regime_signals: Lista de señales de régimen
            
        Returns:
            Lista de señales de trading adaptativas
        """
        all_signals = []
        
        # Crear diccionario de regímenes por timestamp
        regime_dict = {signal.timestamp: signal.regime for signal in regime_signals}
        
        # Agrupar datos por régimen para procesamiento eficiente
        regime_groups = {}
        for timestamp, regime in regime_dict.items():
            if regime not in regime_groups:
                regime_groups[regime] = []
            regime_groups[regime].append(timestamp)
        
        # Generar señales para cada régimen
        for regime, timestamps in regime_groups.items():
            if regime not in self.strategies:
                continue
            
            strategy = self.strategies[regime]
            
            # Filtrar datos para este régimen
            regime_data = data[data.index.isin(timestamps)]
            
            if len(regime_data) < 10:  # Mínimo de datos requerido
                continue
            
            # Generar señales para este régimen
            regime_signals_list = strategy.generate_signals(regime_data, regime)
            all_signals.extend(regime_signals_list)
            
            # Actualizar historial
            self.regime_history.extend([(ts, regime) for ts in timestamps])
        
        # Ordenar señales por timestamp
        all_signals.sort(key=lambda x: x.timestamp)
        
        # Actualizar historial de señales
        self.signal_history.extend(all_signals)
        
        return all_signals
    
    def get_strategy_performance(self) -> Dict:
        """
        Analizar performance de cada estrategia.
        
        Returns:
            Diccionario con métricas de performance por estrategia
        """
        strategy_stats = {}
        
        for signal in self.signal_history:
            strategy_name = signal.strategy_name
            
            if strategy_name not in strategy_stats:
                strategy_stats[strategy_name] = {
                    'total_signals': 0,
                    'avg_confidence': 0,
                    'buy_signals': 0,
                    'sell_signals': 0,
                    'regimes_used': set()
                }
            
            stats = strategy_stats[strategy_name]
            stats['total_signals'] += 1
            stats['avg_confidence'] += signal.confidence
            stats['regimes_used'].add(signal.regime.value)
            
            if signal.signal_type == SignalType.BUY:
                stats['buy_signals'] += 1
            elif signal.signal_type == SignalType.SELL:
                stats['sell_signals'] += 1
        
        # Calcular promedios
        for strategy_name, stats in strategy_stats.items():
            if stats['total_signals'] > 0:
                stats['avg_confidence'] /= stats['total_signals']
                stats['regimes_used'] = list(stats['regimes_used'])
        
        return strategy_stats
    
    def get_regime_distribution(self) -> Dict:
        """
        Obtener distribución de regímenes en el historial.
        
        Returns:
            Diccionario con conteo y porcentaje de cada régimen
        """
        regime_counts = {}
        total_periods = len(self.regime_history)
        
        for timestamp, regime in self.regime_history:
            regime_name = regime.value
            regime_counts[regime_name] = regime_counts.get(regime_name, 0) + 1
        
        # Calcular porcentajes
        regime_distribution = {}
        for regime, count in regime_counts.items():
            regime_distribution[regime] = {
                'count': count,
                'percentage': (count / total_periods * 100) if total_periods > 0 else 0
            }
        
        return regime_distribution

def backtest_adaptive_strategies(data: pd.DataFrame, 
                               regime_signals: List[RegimeSignal],
                               initial_capital: float = 10000) -> Dict:
    """
    Realizar backtesting de las estrategias adaptativas.
    
    Args:
        data: DataFrame con datos OHLCV
        regime_signals: Lista de señales de régimen
        initial_capital: Capital inicial para backtesting
        
    Returns:
        Diccionario con resultados del backtesting
    """
    manager = AdaptiveStrategyManager()
    
    # Generar señales adaptativas
    trading_signals = manager.generate_adaptive_signals(data, regime_signals)
    
    if not trading_signals:
        return {'error': 'No se generaron señales de trading'}
    
    # Simular trading
    capital = initial_capital
    positions = []
    trades = []
    equity_curve = []
    
    for signal in trading_signals:
        current_price = signal.entry_price
        
        # Simular ejecución de señal
        if signal.signal_type in [SignalType.BUY, SignalType.SELL]:
            position_value = capital * signal.position_size * 0.1  # 10% del capital por posición
            
            trade = {
                'timestamp': signal.timestamp,
                'signal_type': signal.signal_type.value,
                'entry_price': current_price,
                'position_size': position_value / current_price,
                'strategy': signal.strategy_name,
                'regime': signal.regime.value,
                'confidence': signal.confidence
            }
            trades.append(trade)
        
        equity_curve.append({
            'timestamp': signal.timestamp,
            'equity': capital
        })
    
    # Calcular métricas
    total_trades = len(trades)
    strategy_performance = manager.get_strategy_performance()
    regime_distribution = manager.get_regime_distribution()
    
    return {
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_trades': total_trades,
        'total_signals': len(trading_signals),
        'strategy_performance': strategy_performance,
        'regime_distribution': regime_distribution,
        'equity_curve': equity_curve,
        'trades': trades[:10]  # Primeros 10 trades como muestra
    }

if __name__ == "__main__":
    print("🚀 Sistema de Estrategias de Trading Adaptativas")
    print("="*60)
    print("📈 Seguimiento de Tendencia (Baja Volatilidad)")
    print("🔄 Reversión a la Media (Alta Volatilidad)")
    print("🛡️ Estrategia Conservadora (Volatilidad Media)")
    print("="*60)
    
    # Ejemplo de uso
    print("\n💡 Ejemplo de uso:")
    print("""
    # Crear gestor de estrategias
    manager = AdaptiveStrategyManager()
    
    # Generar señales adaptativas
    signals = manager.generate_adaptive_signals(data, regime_signals)
    
    # Realizar backtesting
    results = backtest_adaptive_strategies(data, regime_signals)
    print(results)
    """)