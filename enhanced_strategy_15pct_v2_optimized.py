#!/usr/bin/env python3
"""
Estrategia Enhanced 15% V2 - Optimizada con Datos Reales
Basada en resultados de backtest con datos históricos de Binance
Optimizaciones implementadas para mejorar frecuencia y rentabilidad

Autor: AI Trading Assistant
Fecha: 21 de Diciembre de 2024
Versión: 2.0 (Optimizada)
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
class OptimizedTradingConfig:
    """Configuración optimizada basada en resultados reales"""
    
    # Capital y objetivos (ajustados)
    initial_capital: float = 10000
    min_daily_target: float = 0.003  # 0.3% diario (más realista)
    monthly_target: float = 0.09     # 9% mensual (más alcanzable)
    
    # Gestión de riesgo optimizada
    max_risk_per_trade: float = 0.015  # 1.5% por trade (más agresivo)
    max_daily_drawdown: float = 0.03   # 3% drawdown diario máximo
    max_positions: int = 3             # Máximo 3 posiciones simultáneas
    
    # Parámetros técnicos optimizados (más sensibles)
    rsi_period: int = 14
    rsi_oversold: float = 40          # Más sensible para generar más señales
    rsi_overbought: float = 60        # Más sensible para generar más señales
    
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    bb_period: int = 20
    bb_std: float = 2.0
    
    ema_short: int = 9               # Más rápido (era 12)
    ema_medium: int = 21
    ema_long: int = 50
    
    # Gestión de posiciones optimizada
    stop_loss: float = 0.015         # 1.5% stop loss
    take_profit_1: float = 0.025     # 2.5% primer TP
    take_profit_2: float = 0.045     # 4.5% segundo TP
    trailing_stop: float = 0.008     # 0.8% trailing stop
    
    # Filtros de mercado mejorados
    volume_threshold: float = 1.5     # Volumen mínimo 1.5x promedio (más permisivo)
    volatility_min: float = 0.005     # Volatilidad mínima muy reducida
    volatility_max: float = 0.10      # Volatilidad máxima aumentada
    signal_strength_threshold: float = 0.2  # Mucho menos restrictivo
    
    # Nuevos filtros
    momentum_threshold: float = 0.002  # Momentum mínimo
    trend_alignment_threshold: float = 0.6  # Alineación de tendencia
    
    # Pares optimizados
    priority_pairs: List[str] = None
    
    def __post_init__(self):
        if self.priority_pairs is None:
            self.priority_pairs = [
                'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 
                'SOLUSDT', 'DOTUSDT', 'LINKUSDT', 'AVAXUSDT',
                'MATICUSDT', 'LTCUSDT'  # Añadidos más pares
            ]

class OptimizedMarketAnalyzer:
    """Analizador de mercado optimizado V2"""
    
    def __init__(self, config: OptimizedTradingConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos optimizados"""
        try:
            # Precios básicos
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            volume = df['volume'].values
            
            # RSI optimizado
            df['rsi'] = talib.RSI(close, timeperiod=self.config.rsi_period)
            
            # MACD optimizado
            macd, macd_signal, macd_hist = talib.MACD(
                close, 
                fastperiod=self.config.macd_fast,
                slowperiod=self.config.macd_slow, 
                signalperiod=self.config.macd_signal
            )
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_hist
            
            # Bandas de Bollinger
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
            
            # EMAs optimizadas
            df['ema_short'] = talib.EMA(close, timeperiod=self.config.ema_short)
            df['ema_medium'] = talib.EMA(close, timeperiod=self.config.ema_medium)
            df['ema_long'] = talib.EMA(close, timeperiod=self.config.ema_long)
            
            # Indicadores adicionales
            df['stoch_k'], df['stoch_d'] = talib.STOCH(high, low, close)
            df['williams_r'] = talib.WILLR(high, low, close)
            df['cci'] = talib.CCI(high, low, close)
            df['atr'] = talib.ATR(high, low, close, timeperiod=14)
            
            # Volumen optimizado
            df['volume_sma'] = talib.SMA(volume, timeperiod=20)
            df['volume_ratio'] = volume / df['volume_sma']
            df['volume_spike'] = df['volume_ratio'] > self.config.volume_threshold
            
            # Momentum mejorado
            df['momentum'] = talib.MOM(close, timeperiod=10)
            df['roc'] = talib.ROC(close, timeperiod=10)
            df['momentum_normalized'] = df['momentum'] / close
            
            # Volatilidad
            df['volatility'] = df['close'].pct_change().rolling(20).std()
            
            # Nuevos indicadores de tendencia
            df['trend_strength'] = abs(df['ema_short'] - df['ema_long']) / df['ema_long']
            df['trend_direction'] = np.where(df['ema_short'] > df['ema_medium'], 1, 
                                   np.where(df['ema_short'] < df['ema_medium'], -1, 0))
            
            # Indicador de alineación de tendencia
            df['trend_alignment'] = (
                (df['ema_short'] > df['ema_medium']).astype(int) +
                (df['ema_medium'] > df['ema_long']).astype(int) +
                (df['close'] > df['ema_short']).astype(int)
            ) / 3
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error calculando indicadores: {e}")
            return df
    
    def generate_optimized_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera señales optimizadas basadas en datos reales"""
        try:
            # Inicializar señales
            df['signal_rsi'] = 0
            df['signal_macd'] = 0
            df['signal_bb'] = 0
            df['signal_ema'] = 0
            df['signal_momentum'] = 0
            df['signal_volume'] = 0
            df['signal_trend'] = 0
            
            # Señales RSI optimizadas (más sensibles)
            df.loc[df['rsi'] < self.config.rsi_oversold, 'signal_rsi'] = 1
            df.loc[df['rsi'] > self.config.rsi_overbought, 'signal_rsi'] = -1
            
            # Señales MACD optimizadas
            df.loc[(df['macd'] > df['macd_signal']) & 
                   (df['macd'].shift(1) <= df['macd_signal'].shift(1)), 'signal_macd'] = 1
            df.loc[(df['macd'] < df['macd_signal']) & 
                   (df['macd'].shift(1) >= df['macd_signal'].shift(1)), 'signal_macd'] = -1
            
            # Señales Bollinger Bands
            df.loc[df['bb_position'] < 0.2, 'signal_bb'] = 1  # Cerca del límite inferior
            df.loc[df['bb_position'] > 0.8, 'signal_bb'] = -1  # Cerca del límite superior
            
            # Señales EMA (tendencia)
            df.loc[(df['ema_short'] > df['ema_medium']) & 
                   (df['ema_short'].shift(1) <= df['ema_medium'].shift(1)), 'signal_ema'] = 1
            df.loc[(df['ema_short'] < df['ema_medium']) & 
                   (df['ema_short'].shift(1) >= df['ema_medium'].shift(1)), 'signal_ema'] = -1
            
            # Señales de momentum
            df.loc[df['momentum_normalized'] > self.config.momentum_threshold, 'signal_momentum'] = 1
            df.loc[df['momentum_normalized'] < -self.config.momentum_threshold, 'signal_momentum'] = -1
            
            # Señales de volumen
            df.loc[df['volume_spike'], 'signal_volume'] = 1
            
            # Señales de tendencia
            df.loc[df['trend_alignment'] > self.config.trend_alignment_threshold, 'signal_trend'] = 1
            df.loc[df['trend_alignment'] < (1 - self.config.trend_alignment_threshold), 'signal_trend'] = -1
            
            # Combinar señales con pesos optimizados
            weights = {
                'rsi': 0.25,
                'macd': 0.20,
                'bb': 0.15,
                'ema': 0.20,
                'momentum': 0.10,
                'volume': 0.05,
                'trend': 0.05
            }
            
            df['signal_combined'] = (
                df['signal_rsi'] * weights['rsi'] +
                df['signal_macd'] * weights['macd'] +
                df['signal_bb'] * weights['bb'] +
                df['signal_ema'] * weights['ema'] +
                df['signal_momentum'] * weights['momentum'] +
                df['signal_volume'] * weights['volume'] +
                df['signal_trend'] * weights['trend']
            )
            
            # Generar señal final
            df['signal'] = 0
            df.loc[df['signal_combined'] > self.config.signal_strength_threshold, 'signal'] = 1
            df.loc[df['signal_combined'] < -self.config.signal_strength_threshold, 'signal'] = -1
            
            # Filtros adicionales
            # Filtro de volatilidad
            volatility_filter = (
                (df['volatility'] >= self.config.volatility_min) & 
                (df['volatility'] <= self.config.volatility_max)
            )
            
            # Aplicar filtros
            df.loc[~volatility_filter, 'signal'] = 0
            
            # Calcular confianza de la señal
            df['signal_confidence'] = abs(df['signal_combined'])
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error generando señales: {e}")
            return df

class OptimizedRiskManager:
    """Gestor de riesgo optimizado V2"""
    
    def __init__(self, config: OptimizedTradingConfig):
        self.config = config
        self.daily_pnl = 0
        self.daily_trades = 0
        self.current_positions = 0
        self.logger = logging.getLogger(__name__)
        
    def calculate_dynamic_position_size(self, signal_strength: float, volatility: float,
                                      current_capital: float, atr: float = None) -> float:
        """Calcula tamaño de posición dinámico basado en volatilidad y ATR"""
        try:
            # Tamaño base
            base_size = self.config.max_risk_per_trade
            
            # Ajuste por fuerza de señal
            signal_multiplier = min(signal_strength * 2, 1.5)
            
            # Ajuste por volatilidad (inverso)
            volatility_multiplier = min(0.02 / max(volatility, 0.01), 2.0)
            
            # Ajuste por ATR si está disponible
            atr_multiplier = 1.0
            if atr is not None and atr > 0:
                atr_multiplier = min(0.01 / atr, 1.5)
            
            # Tamaño final
            position_size = base_size * signal_multiplier * volatility_multiplier * atr_multiplier
            
            # Límites
            position_size = max(position_size, 0.005)  # Mínimo 0.5%
            position_size = min(position_size, 0.03)   # Máximo 3%
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculando tamaño de posición: {e}")
            return self.config.max_risk_per_trade
    
    def should_enter_trade(self, signal: int, current_capital: float, 
                          signal_strength: float = 0.5) -> bool:
        """Determina si se debe entrar en un trade"""
        try:
            # Verificar señal válida
            if signal == 0:
                return False
            
            # Verificar fuerza de señal
            if signal_strength < self.config.signal_strength_threshold:
                return False
            
            # Verificar límite de posiciones
            if self.current_positions >= self.config.max_positions:
                return False
            
            # Verificar drawdown diario
            if self.daily_pnl < -self.config.max_daily_drawdown:
                return False
            
            # Verificar capital mínimo
            if current_capital < self.config.initial_capital * 0.8:
                return False
            
            return True
            
        except Exception:
            return False
    
    def calculate_dynamic_stop_loss(self, entry_price: float, signal: int,
                                   volatility: float, atr: float = None) -> float:
        """Calcula stop loss dinámico"""
        try:
            # Stop loss base
            base_stop = self.config.stop_loss
            
            # Ajuste por volatilidad
            volatility_multiplier = max(volatility / 0.02, 0.5)
            
            # Ajuste por ATR
            atr_multiplier = 1.0
            if atr is not None and atr > 0:
                atr_multiplier = max(atr / (entry_price * 0.01), 0.5)
            
            # Stop loss dinámico
            dynamic_stop = base_stop * volatility_multiplier * atr_multiplier
            dynamic_stop = max(dynamic_stop, 0.008)  # Mínimo 0.8%
            dynamic_stop = min(dynamic_stop, 0.025)  # Máximo 2.5%
            
            if signal == 1:  # Compra
                return entry_price * (1 - dynamic_stop)
            else:  # Venta
                return entry_price * (1 + dynamic_stop)
                
        except Exception as e:
            self.logger.error(f"Error calculando stop loss: {e}")
            if signal == 1:
                return entry_price * (1 - self.config.stop_loss)
            else:
                return entry_price * (1 + self.config.stop_loss)
    
    def calculate_dynamic_take_profit(self, entry_price: float, signal: int,
                                    volatility: float, atr: float = None) -> Tuple[float, float]:
        """Calcula take profit dinámico"""
        try:
            # Take profit base
            tp1_base = self.config.take_profit_1
            tp2_base = self.config.take_profit_2
            
            # Ajuste por volatilidad
            volatility_multiplier = max(volatility / 0.02, 0.8)
            
            # Ajuste por ATR
            atr_multiplier = 1.0
            if atr is not None and atr > 0:
                atr_multiplier = max(atr / (entry_price * 0.01), 0.8)
            
            # Take profits dinámicos
            tp1_distance = tp1_base * volatility_multiplier * atr_multiplier
            tp2_distance = tp2_base * volatility_multiplier * atr_multiplier
            
            # Límites
            tp1_distance = max(tp1_distance, 0.015)  # Mínimo 1.5%
            tp1_distance = min(tp1_distance, 0.04)   # Máximo 4%
            tp2_distance = max(tp2_distance, 0.03)   # Mínimo 3%
            tp2_distance = min(tp2_distance, 0.08)   # Máximo 8%
            
            if signal == 1:  # Compra
                tp1 = entry_price * (1 + tp1_distance)
                tp2 = entry_price * (1 + tp2_distance)
            else:  # Venta
                tp1 = entry_price * (1 - tp1_distance)
                tp2 = entry_price * (1 - tp2_distance)
            
            return tp1, tp2
            
        except Exception as e:
            self.logger.error(f"Error calculando take profit: {e}")
            if signal == 1:
                return entry_price * 1.025, entry_price * 1.045
            else:
                return entry_price * 0.975, entry_price * 0.955

class Enhanced15PercentStrategyV2:
    """Estrategia mejorada V2 optimizada con datos reales"""
    
    def __init__(self, config: OptimizedTradingConfig = None):
        self.config = config or OptimizedTradingConfig()
        self.analyzer = OptimizedMarketAnalyzer(self.config)
        self.risk_manager = OptimizedRiskManager(self.config)
        self.logger = logging.getLogger(__name__)
        
        # Estado de la estrategia
        self.current_capital = self.config.initial_capital
        self.positions = {}
        self.trade_history = []
        self.daily_stats = []
        
    def analyze_pair_optimized(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Analiza un par con optimizaciones V2"""
        try:
            # Calcular indicadores
            df = self.analyzer.calculate_technical_indicators(df)
            
            # Generar señales optimizadas
            df = self.analyzer.generate_optimized_signals(df)
            
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
                'macd_histogram': latest['macd_histogram'],
                'bb_position': latest['bb_position'],
                'volatility': latest['volatility'],
                'volume_ratio': latest['volume_ratio'],
                'momentum': latest['momentum_normalized'],
                'trend_alignment': latest['trend_alignment'],
                'atr': latest['atr'],
                
                # Recomendación optimizada
                'recommendation': self._get_optimized_recommendation(latest),
                'confidence': latest['signal_confidence'],
                'risk_level': self._assess_risk_level(latest)
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analizando {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _get_optimized_recommendation(self, data: pd.Series) -> str:
        """Genera recomendación optimizada"""
        try:
            signal = data['signal']
            strength = data['signal_confidence']
            trend_alignment = data['trend_alignment']
            
            if signal == 1:
                if strength > 0.6 and trend_alignment > 0.7:
                    return "COMPRA FUERTE"
                elif strength > 0.4:
                    return "COMPRA"
                else:
                    return "COMPRA DÉBIL"
            elif signal == -1:
                if strength > 0.6 and trend_alignment < 0.3:
                    return "VENTA FUERTE"
                elif strength > 0.4:
                    return "VENTA"
                else:
                    return "VENTA DÉBIL"
            else:
                return "MANTENER"
                
        except Exception:
            return "MANTENER"
    
    def _assess_risk_level(self, data: pd.Series) -> str:
        """Evalúa el nivel de riesgo"""
        try:
            volatility = data['volatility']
            bb_width = data.get('bb_width', 0.05)
            
            if volatility > 0.04 or bb_width > 0.08:
                return "ALTO"
            elif volatility > 0.025 or bb_width > 0.05:
                return "MEDIO"
            else:
                return "BAJO"
                
        except Exception:
            return "MEDIO"
    
    def get_performance_report_v2(self) -> Dict:
        """Genera reporte de rendimiento optimizado"""
        try:
            if not self.trade_history:
                return {
                    'total_trades': 0,
                    'current_capital': self.current_capital,
                    'total_return': 0,
                    'message': 'No hay trades ejecutados'
                }
            
            trades_df = pd.DataFrame(self.trade_history)
            
            # Métricas básicas
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['return_pct'] > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Retornos
            total_return = (self.current_capital - self.config.initial_capital) / self.config.initial_capital
            avg_return_per_trade = trades_df['return_pct'].mean() if total_trades > 0 else 0
            
            # Drawdown
            equity_curve = [self.config.initial_capital]
            for trade in self.trade_history:
                equity_curve.append(equity_curve[-1] + trade['pnl'])
            
            equity_series = pd.Series(equity_curve)
            running_max = equity_series.expanding().max()
            drawdown = (equity_series - running_max) / running_max
            max_drawdown = abs(drawdown.min())
            
            # Sharpe ratio
            if total_trades > 1:
                returns = trades_df['return_pct'] / 100
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Evaluación de objetivos
            daily_return = total_return / max(1, len(self.daily_stats)) if self.daily_stats else total_return
            monthly_return = daily_return * 30
            
            meets_daily_target = daily_return >= self.config.min_daily_target
            meets_monthly_target = monthly_return >= self.config.monthly_target
            
            return {
                'timestamp': datetime.now(),
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate * 100,
                'current_capital': self.current_capital,
                'total_return': total_return * 100,
                'daily_return': daily_return * 100,
                'monthly_return': monthly_return * 100,
                'avg_return_per_trade': avg_return_per_trade,
                'max_drawdown': max_drawdown * 100,
                'sharpe_ratio': sharpe_ratio,
                'meets_daily_target': meets_daily_target,
                'meets_monthly_target': meets_monthly_target,
                'risk_level': 'OPTIMIZADO',
                'strategy_version': '2.0'
            }
            
        except Exception as e:
            self.logger.error(f"Error generando reporte: {e}")
            return {'error': str(e)}

def main():
    """Función principal para testing"""
    print("🚀 Enhanced 15% Strategy V2 - Optimizada")
    print("📊 Basada en resultados de backtest con datos reales de Binance")
    print("⚡ Optimizaciones implementadas para mayor frecuencia y rentabilidad")
    
    # Crear configuración optimizada
    config = OptimizedTradingConfig()
    
    print(f"\n📋 Configuración Optimizada:")
    print(f"   • Objetivo diario: {config.min_daily_target*100:.1f}%")
    print(f"   • Objetivo mensual: {config.monthly_target*100:.1f}%")
    print(f"   • Riesgo por trade: {config.max_risk_per_trade*100:.1f}%")
    print(f"   • Umbral de señal: {config.signal_strength_threshold:.1f}")
    print(f"   • RSI oversold/overbought: {config.rsi_oversold}/{config.rsi_overbought}")
    print(f"   • Volumen mínimo: {config.volume_threshold}x")
    
    # Crear estrategia
    strategy = Enhanced15PercentStrategyV2(config)
    
    print(f"\n✅ Estrategia V2 inicializada correctamente")
    print(f"💰 Capital inicial: ${config.initial_capital:,.2f}")
    print(f"🎯 Listo para trading optimizado")

if __name__ == "__main__":
    main()