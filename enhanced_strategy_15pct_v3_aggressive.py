#!/usr/bin/env python3
"""
Estrategia Enhanced 15% V3 - Agresiva y Optimizada
Basada en análisis de múltiples backtests con datos reales
Versión más agresiva con mejor win rate y frecuencia de trades

Autor: AI Trading Assistant
Fecha: 21 de Diciembre de 2024
Versión: 3.0 (Agresiva)
"""

import pandas as pd
import numpy as np
import talib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class AggressiveTradingConfig:
    """Configuración agresiva optimizada para mayor frecuencia"""
    
    # Capital y objetivos (más agresivos)
    initial_capital: float = 10000
    min_daily_target: float = 0.005  # 0.5% diario (más agresivo)
    monthly_target: float = 0.15     # 15% mensual (más ambicioso)
    
    # Gestión de riesgo agresiva
    max_risk_per_trade: float = 0.02   # 2% por trade (más agresivo)
    max_daily_drawdown: float = 0.05   # 5% drawdown diario máximo
    max_positions: int = 5             # Máximo 5 posiciones simultáneas
    
    # Parámetros técnicos muy sensibles
    rsi_period: int = 14
    rsi_oversold: float = 45          # Muy sensible
    rsi_overbought: float = 55        # Muy sensible
    
    macd_fast: int = 8               # Más rápido
    macd_slow: int = 21              # Más rápido
    macd_signal: int = 7             # Más rápido
    
    bb_period: int = 15              # Más sensible
    bb_std: float = 1.8              # Más sensible
    
    ema_short: int = 7               # Muy rápido
    ema_medium: int = 15             # Más rápido
    ema_long: int = 30               # Más rápido
    
    # Gestión de posiciones agresiva
    stop_loss: float = 0.012         # 1.2% stop loss (más ajustado)
    take_profit_1: float = 0.018     # 1.8% primer TP (más conservador)
    take_profit_2: float = 0.035     # 3.5% segundo TP
    trailing_stop: float = 0.006     # 0.6% trailing stop
    
    # Filtros muy permisivos
    volume_threshold: float = 1.2     # Volumen mínimo 1.2x promedio
    volatility_min: float = 0.003     # Volatilidad mínima muy baja
    volatility_max: float = 0.15      # Volatilidad máxima muy alta
    signal_strength_threshold: float = 0.15  # Muy permisivo
    
    # Filtros adicionales agresivos
    momentum_threshold: float = 0.001  # Momentum mínimo muy bajo
    trend_alignment_threshold: float = 0.4  # Alineación menos estricta
    
    # Scalping parameters
    enable_scalping: bool = True
    scalping_timeframe: str = '15m'   # Timeframe más corto
    min_profit_scalp: float = 0.008   # 0.8% mínimo para scalping
    
    # Pares optimizados para alta frecuencia
    priority_pairs: List[str] = None
    
    def __post_init__(self):
        if self.priority_pairs is None:
            self.priority_pairs = [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
                'DOTUSDT', 'LINKUSDT', 'AVAXUSDT', 'MATICUSDT', 'LTCUSDT',
                'XRPUSDT', 'TRXUSDT', 'EOSUSDT', 'XLMUSDT', 'VETUSDT'  # Más pares
            ]

class AggressiveMarketAnalyzer:
    """Analizador de mercado agresivo V3"""
    
    def __init__(self, config: AggressiveTradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos agresivos"""
        try:
            # Precios básicos
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            volume = df['volume'].values
            
            # RSI agresivo
            df['rsi'] = talib.RSI(close, timeperiod=self.config.rsi_period)
            df['rsi_fast'] = talib.RSI(close, timeperiod=7)  # RSI rápido adicional
            
            # MACD agresivo
            macd, macd_signal, macd_hist = talib.MACD(
                close, 
                fastperiod=self.config.macd_fast,
                slowperiod=self.config.macd_slow, 
                signalperiod=self.config.macd_signal
            )
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_hist
            
            # Bandas de Bollinger agresivas
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                close, 
                timeperiod=self.config.bb_period,
                nbdevup=self.config.bb_std,
                nbdevdn=self.config.bb_std
            )
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            df['bb_width'] = (bb_upper - bb_lower) / bb_middle
            df['bb_position'] = (close - bb_lower) / (bb_upper - bb_lower)
            
            # EMAs agresivas
            df['ema_short'] = talib.EMA(close, timeperiod=self.config.ema_short)
            df['ema_medium'] = talib.EMA(close, timeperiod=self.config.ema_medium)
            df['ema_long'] = talib.EMA(close, timeperiod=self.config.ema_long)
            
            # Indicadores adicionales para scalping
            df['stoch_k'], df['stoch_d'] = talib.STOCH(high, low, close, fastk_period=5)
            df['williams_r'] = talib.WILLR(high, low, close, timeperiod=7)
            df['cci'] = talib.CCI(high, low, close, timeperiod=10)
            df['atr'] = talib.ATR(high, low, close, timeperiod=10)
            
            # Volumen agresivo
            df['volume_sma'] = talib.SMA(volume, timeperiod=10)
            df['volume_ratio'] = volume / df['volume_sma']
            df['volume_spike'] = df['volume_ratio'] > self.config.volume_threshold
            
            # Momentum muy sensible
            df['momentum'] = talib.MOM(close, timeperiod=5)
            df['roc'] = talib.ROC(close, timeperiod=5)
            df['momentum_normalized'] = df['momentum'] / close
            
            # Volatilidad
            df['volatility'] = df['close'].pct_change().rolling(10).std()
            
            # Indicadores de tendencia agresivos
            df['trend_strength'] = abs(df['ema_short'] - df['ema_medium']) / df['ema_medium']
            df['trend_direction'] = np.where(df['ema_short'] > df['ema_medium'], 1, 
                                   np.where(df['ema_short'] < df['ema_medium'], -1, 0))
            
            # Alineación de tendencia
            df['trend_alignment'] = (
                (df['ema_short'] > df['ema_medium']).astype(int) +
                (df['ema_medium'] > df['ema_long']).astype(int) +
                (df['close'] > df['ema_short']).astype(int)
            ) / 3
            
            # Indicadores de reversión
            df['price_change'] = df['close'].pct_change()
            df['price_acceleration'] = df['price_change'].diff()
            
            # Squeeze indicator (para detectar breakouts)
            df['squeeze'] = (df['bb_width'] < df['bb_width'].rolling(20).quantile(0.2))
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculando indicadores: {e}")
            return df
    
    def generate_aggressive_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera señales agresivas para alta frecuencia"""
        try:
            # Inicializar señales
            df['signal_rsi'] = 0
            df['signal_rsi_fast'] = 0
            df['signal_macd'] = 0
            df['signal_bb'] = 0
            df['signal_ema'] = 0
            df['signal_momentum'] = 0
            df['signal_volume'] = 0
            df['signal_trend'] = 0
            df['signal_stoch'] = 0
            df['signal_squeeze'] = 0
            
            # Señales RSI muy agresivas
            df.loc[df['rsi'] < self.config.rsi_oversold, 'signal_rsi'] = 1
            df.loc[df['rsi'] > self.config.rsi_overbought, 'signal_rsi'] = -1
            
            # RSI rápido para scalping
            df.loc[df['rsi_fast'] < 35, 'signal_rsi_fast'] = 1
            df.loc[df['rsi_fast'] > 65, 'signal_rsi_fast'] = -1
            
            # Señales MACD agresivas
            df.loc[(df['macd'] > df['macd_signal']) & 
                   (df['macd'].shift(1) <= df['macd_signal'].shift(1)), 'signal_macd'] = 1
            df.loc[(df['macd'] < df['macd_signal']) & 
                   (df['macd'].shift(1) >= df['macd_signal'].shift(1)), 'signal_macd'] = -1
            
            # Señales Bollinger Bands agresivas
            df.loc[df['bb_position'] < 0.25, 'signal_bb'] = 1  # Más permisivo
            df.loc[df['bb_position'] > 0.75, 'signal_bb'] = -1  # Más permisivo
            
            # Señales EMA (tendencia)
            df.loc[(df['ema_short'] > df['ema_medium']) & 
                   (df['ema_short'].shift(1) <= df['ema_medium'].shift(1)), 'signal_ema'] = 1
            df.loc[(df['ema_short'] < df['ema_medium']) & 
                   (df['ema_short'].shift(1) >= df['ema_medium'].shift(1)), 'signal_ema'] = -1
            
            # Señales de momentum agresivas
            df.loc[df['momentum_normalized'] > self.config.momentum_threshold, 'signal_momentum'] = 1
            df.loc[df['momentum_normalized'] < -self.config.momentum_threshold, 'signal_momentum'] = -1
            
            # Señales de volumen
            df.loc[df['volume_spike'], 'signal_volume'] = 1
            
            # Señales de tendencia
            df.loc[df['trend_alignment'] > self.config.trend_alignment_threshold, 'signal_trend'] = 1
            df.loc[df['trend_alignment'] < (1 - self.config.trend_alignment_threshold), 'signal_trend'] = -1
            
            # Señales Stochastic
            df.loc[(df['stoch_k'] < 25) & (df['stoch_k'] > df['stoch_d']), 'signal_stoch'] = 1
            df.loc[(df['stoch_k'] > 75) & (df['stoch_k'] < df['stoch_d']), 'signal_stoch'] = -1
            
            # Señales de squeeze breakout
            df.loc[df['squeeze'] & (df['price_acceleration'] > 0), 'signal_squeeze'] = 1
            df.loc[df['squeeze'] & (df['price_acceleration'] < 0), 'signal_squeeze'] = -1
            
            # Combinar señales con pesos optimizados para alta frecuencia
            weights = {
                'rsi': 0.20,
                'rsi_fast': 0.15,
                'macd': 0.15,
                'bb': 0.15,
                'ema': 0.10,
                'momentum': 0.10,
                'volume': 0.05,
                'trend': 0.05,
                'stoch': 0.03,
                'squeeze': 0.02
            }
            
            df['signal_combined'] = (
                df['signal_rsi'] * weights['rsi'] +
                df['signal_rsi_fast'] * weights['rsi_fast'] +
                df['signal_macd'] * weights['macd'] +
                df['signal_bb'] * weights['bb'] +
                df['signal_ema'] * weights['ema'] +
                df['signal_momentum'] * weights['momentum'] +
                df['signal_volume'] * weights['volume'] +
                df['signal_trend'] * weights['trend'] +
                df['signal_stoch'] * weights['stoch'] +
                df['signal_squeeze'] * weights['squeeze']
            )
            
            # Generar señal final agresiva
            df['signal'] = 0
            df.loc[df['signal_combined'] > self.config.signal_strength_threshold, 'signal'] = 1
            df.loc[df['signal_combined'] < -self.config.signal_strength_threshold, 'signal'] = -1
            
            # Filtros mínimos (muy permisivos)
            volatility_filter = (
                (df['volatility'] >= self.config.volatility_min) & 
                (df['volatility'] <= self.config.volatility_max)
            )
            
            # Aplicar filtros solo si son muy restrictivos
            df.loc[~volatility_filter, 'signal'] = 0
            
            # Calcular confianza de la señal
            df['signal_confidence'] = abs(df['signal_combined'])
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error generando señales: {e}")
            return df

class AggressiveRiskManager:
    """Gestor de riesgo agresivo V3"""
    
    def __init__(self, config: AggressiveTradingConfig):
        self.config = config
        self.daily_pnl = 0
        self.daily_trades = 0
        self.current_positions = 0
        self.consecutive_losses = 0
        self.logger = logging.getLogger(__name__)
        
    def calculate_aggressive_position_size(self, signal_strength: float, volatility: float,
                                         current_capital: float, atr: float = None) -> float:
        """Calcula tamaño de posición agresivo"""
        try:
            # Tamaño base más agresivo
            base_size = self.config.max_risk_per_trade
            
            # Multiplicador por fuerza de señal (más agresivo)
            signal_multiplier = min(signal_strength * 3, 2.0)
            
            # Ajuste por volatilidad (menos conservador)
            volatility_multiplier = min(0.03 / max(volatility, 0.005), 1.8)
            
            # Ajuste por ATR
            atr_multiplier = 1.0
            if atr is not None and atr > 0:
                atr_multiplier = min(0.015 / atr, 1.3)
            
            # Ajuste por racha de pérdidas
            loss_multiplier = max(0.5, 1 - (self.consecutive_losses * 0.1))
            
            # Tamaño final
            position_size = base_size * signal_multiplier * volatility_multiplier * atr_multiplier * loss_multiplier
            
            # Límites agresivos
            position_size = max(position_size, 0.008)  # Mínimo 0.8%
            position_size = min(position_size, 0.04)   # Máximo 4%
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculando tamaño de posición: {e}")
            return self.config.max_risk_per_trade
    
    def should_enter_trade_aggressive(self, signal: int, current_capital: float, 
                                    signal_strength: float = 0.5) -> bool:
        """Determina si se debe entrar en un trade (versión agresiva)"""
        try:
            # Verificar señal válida
            if signal == 0:
                return False
            
            # Verificar fuerza de señal (más permisivo)
            if signal_strength < self.config.signal_strength_threshold:
                return False
            
            # Verificar límite de posiciones
            if self.current_positions >= self.config.max_positions:
                return False
            
            # Verificar drawdown diario (más permisivo)
            if self.daily_pnl < -self.config.max_daily_drawdown:
                return False
            
            # Verificar capital mínimo (más agresivo)
            if current_capital < self.config.initial_capital * 0.7:
                return False
            
            # Límite de pérdidas consecutivas
            if self.consecutive_losses >= 5:
                return False
            
            return True
            
        except Exception:
            return False
    
    def update_consecutive_losses(self, trade_result: str):
        """Actualiza contador de pérdidas consecutivas"""
        if trade_result == "SL":
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

class Enhanced15PercentStrategyV3:
    """Estrategia mejorada V3 - Agresiva y de alta frecuencia"""
    
    def __init__(self, config: AggressiveTradingConfig = None):
        self.config = config or AggressiveTradingConfig()
        self.analyzer = AggressiveMarketAnalyzer(self.config)
        self.risk_manager = AggressiveRiskManager(self.config)
        self.logger = logging.getLogger(__name__)
        
        # Estado de la estrategia
        self.current_capital = self.config.initial_capital
        self.positions = {}
        self.trade_history = []
        self.daily_stats = []
        
    def analyze_pair_aggressive(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Analiza un par con configuración agresiva"""
        try:
            # Calcular indicadores
            df = self.analyzer.calculate_technical_indicators(df)
            
            # Generar señales agresivas
            df = self.analyzer.generate_aggressive_signals(df)
            
            # Análisis actual
            latest = df.iloc[-1]
            
            analysis = {
                'symbol': symbol,
                'timestamp': latest.name if hasattr(latest, 'name') else datetime.now(),
                'current_price': latest['close'],
                'signal': latest['signal'],
                'signal_strength': latest['signal_confidence'],
                'signal_combined': latest['signal_combined'],
                
                # Indicadores técnicos
                'rsi': latest['rsi'],
                'rsi_fast': latest['rsi_fast'],
                'macd_histogram': latest['macd_histogram'],
                'bb_position': latest['bb_position'],
                'volatility': latest['volatility'],
                'volume_ratio': latest['volume_ratio'],
                'momentum': latest['momentum_normalized'],
                'trend_alignment': latest['trend_alignment'],
                'atr': latest['atr'],
                'stoch_k': latest['stoch_k'],
                'squeeze': latest['squeeze'],
                
                # Recomendación agresiva
                'recommendation': self._get_aggressive_recommendation(latest),
                'confidence': latest['signal_confidence'],
                'risk_level': self._assess_aggressive_risk_level(latest)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analizando {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _get_aggressive_recommendation(self, data: pd.Series) -> str:
        """Genera recomendación agresiva"""
        try:
            signal = data['signal']
            strength = data['signal_confidence']
            trend_alignment = data['trend_alignment']
            
            if signal == 1:
                if strength > 0.4 and trend_alignment > 0.6:
                    return "COMPRA AGRESIVA"
                elif strength > 0.25:
                    return "COMPRA RÁPIDA"
                else:
                    return "COMPRA SCALP"
            elif signal == -1:
                if strength > 0.4 and trend_alignment < 0.4:
                    return "VENTA AGRESIVA"
                elif strength > 0.25:
                    return "VENTA RÁPIDA"
                else:
                    return "VENTA SCALP"
            else:
                return "ESPERAR"
                
        except Exception:
            return "ESPERAR"
    
    def _assess_aggressive_risk_level(self, data: pd.Series) -> str:
        """Evalúa el nivel de riesgo agresivo"""
        try:
            volatility = data['volatility']
            bb_width = data.get('bb_width', 0.05)
            
            if volatility > 0.08 or bb_width > 0.12:
                return "EXTREMO"
            elif volatility > 0.05 or bb_width > 0.08:
                return "ALTO"
            elif volatility > 0.03 or bb_width > 0.05:
                return "MEDIO"
            else:
                return "BAJO"
                
        except Exception:
            return "MEDIO"

def main():
    """Función principal para testing"""
    print("🚀 Enhanced 15% Strategy V3 - AGRESIVA")
    print("⚡ Configuración de alta frecuencia y máxima rentabilidad")
    print("🎯 Optimizada para generar más señales y trades")
    
    # Crear configuración agresiva
    config = AggressiveTradingConfig()
    
    print(f"\n📋 Configuración Agresiva:")
    print(f"   • Objetivo diario: {config.min_daily_target*100:.1f}%")
    print(f"   • Objetivo mensual: {config.monthly_target*100:.1f}%")
    print(f"   • Riesgo por trade: {config.max_risk_per_trade*100:.1f}%")
    print(f"   • Umbral de señal: {config.signal_strength_threshold:.2f}")
    print(f"   • RSI oversold/overbought: {config.rsi_oversold}/{config.rsi_overbought}")
    print(f"   • Volumen mínimo: {config.volume_threshold}x")
    print(f"   • Scalping habilitado: {config.enable_scalping}")
    
    # Crear estrategia
    strategy = Enhanced15PercentStrategyV3(config)
    
    print(f"\n✅ Estrategia V3 Agresiva inicializada")
    print(f"💰 Capital inicial: ${config.initial_capital:,.2f}")
    print(f"🚀 Lista para trading de alta frecuencia")

if __name__ == "__main__":
    main()