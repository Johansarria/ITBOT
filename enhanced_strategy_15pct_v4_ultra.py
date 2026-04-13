#!/usr/bin/env python3
"""
🚀 ESTRATEGIA ENHANCED 15% DAILY V4 ULTRA-AGRESIVA

Estrategia ultra-agresiva diseñada específicamente para alcanzar 15% mensual
con capital base de $500 USDT en trading spot.

Objetivos:
- Capital Base: $500 USDT
- Objetivo Mensual: 15% ($75 USDT)
- Objetivo Diario: 0.5% ($2.5 USDT)
- Retorno por Trade: 1-3% con alta frecuencia

Características V4:
- Scalping ultra-agresivo (1-3 minutos)
- Gestión de capital dinámico
- Take profits escalonados extremos
- Filtros de momentum ultra-sensibles
- Trading de alta frecuencia

Autor: Sistema de Trading Automatizado
Versión: 4.0 Ultra-Agresiva
Fecha: Septiembre 2024
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import talib
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

@dataclass
class UltraTradingConfig:
    """
    Configuración ultra-agresiva para alcanzar 15% mensual con $500 USDT
    """
    
    # Capital y objetivos
    base_capital: float = 500.0  # Capital base en USDT
    daily_target_pct: float = 0.005  # 0.5% diario
    monthly_target_pct: float = 0.15  # 15% mensual
    daily_target_usdt: float = 2.5  # $2.5 USDT diario
    monthly_target_usdt: float = 75.0  # $75 USDT mensual
    
    # Gestión de capital ULTRA-AGRESIVA
    position_size_pct: float = 0.35  # 35% del capital por trade
    max_positions: int = 6  # Máximo 6 posiciones simultáneas
    risk_per_trade: float = 0.012  # 1.2% riesgo por trade
    
    # Indicadores técnicos ultra-sensibles
    rsi_period: int = 7  # RSI más sensible
    rsi_oversold: int = 40  # Más agresivo
    rsi_overbought: int = 60  # Más agresivo
    
    macd_fast: int = 8  # MACD ultra-rápido
    macd_slow: int = 17
    macd_signal: int = 6
    
    bb_period: int = 15  # Bandas más sensibles
    bb_std: float = 1.8
    
    ema_ultra_fast: int = 5  # EMA ultra-rápida
    ema_fast: int = 8
    ema_medium: int = 13
    ema_slow: int = 21
    
    # Filtros de mercado ultra-agresivos
    volume_threshold: float = 1.1  # Volumen mínimo
    volatility_min: float = 0.001  # Volatilidad mínima
    volatility_max: float = 0.20  # Volatilidad máxima
    momentum_threshold: float = 0.0005  # Momentum mínimo
    
    # Take Profits OPTIMIZADOS para 15% mensual
    stop_loss: float = 0.003  # 0.3% SL más ajustado
    take_profit_1: float = 0.020  # 2.0% TP1
    take_profit_2: float = 0.035  # 3.5% TP2
    take_profit_3: float = 0.050  # 5.0% TP3
    
    # Distribución de take profits
    tp1_allocation: float = 0.4  # 40% en TP1
    tp2_allocation: float = 0.35  # 35% en TP2
    tp3_allocation: float = 0.25  # 25% en TP3
    
    # Filtros de fuerza # Umbrales de señal ULTRA-OPTIMIZADOS
    signal_strength_threshold: float = 0.03  # Extremadamente agresivo
    min_signal_confidence: float = 0.10  # Mínimo para máximos trades
    
    # Timeframes para scalping
    primary_timeframe: str = '1m'  # Timeframe principal
    confirmation_timeframe: str = '3m'  # Confirmación
    trend_timeframe: str = '5m'  # Tendencia

class UltraMarketAnalyzer:
    """
    Analizador de mercado ultra-agresivo para scalping de alta frecuencia
    """
    
    def __init__(self, config: UltraTradingConfig):
        self.config = config
    
    def calculate_ultra_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcular indicadores técnicos ultra-sensibles para scalping
        """
        try:
            # Precios básicos
            high = df['high'].values
            low = df['low'].values
            close = df['close'].values
            volume = df['volume'].values
            
            # RSI ultra-sensible
            df['rsi'] = talib.RSI(close, timeperiod=self.config.rsi_period)
            df['rsi_oversold'] = df['rsi'] < self.config.rsi_oversold
            df['rsi_overbought'] = df['rsi'] > self.config.rsi_overbought
            
            # MACD ultra-rápido
            macd, macd_signal, macd_hist = talib.MACD(
                close, 
                fastperiod=self.config.macd_fast,
                slowperiod=self.config.macd_slow, 
                signalperiod=self.config.macd_signal
            )
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_hist
            df['macd_bullish'] = (macd > macd_signal) & (macd_hist > 0)
            df['macd_bearish'] = (macd < macd_signal) & (macd_hist < 0)
            
            # Bandas de Bollinger sensibles
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
            
            # EMAs múltiples para scalping
            df['ema_ultra_fast'] = talib.EMA(close, timeperiod=self.config.ema_ultra_fast)
            df['ema_fast'] = talib.EMA(close, timeperiod=self.config.ema_fast)
            df['ema_medium'] = talib.EMA(close, timeperiod=self.config.ema_medium)
            df['ema_slow'] = talib.EMA(close, timeperiod=self.config.ema_slow)
            
            # Alineación de EMAs
            df['ema_bullish_alignment'] = (
                (df['ema_ultra_fast'] > df['ema_fast']) &
                (df['ema_fast'] > df['ema_medium']) &
                (df['ema_medium'] > df['ema_slow'])
            )
            df['ema_bearish_alignment'] = (
                (df['ema_ultra_fast'] < df['ema_fast']) &
                (df['ema_fast'] < df['ema_medium']) &
                (df['ema_medium'] < df['ema_slow'])
            )
            
            # Momentum ultra-sensible
            df['momentum_1'] = close / df['close'].shift(1) - 1
            df['momentum_3'] = close / df['close'].shift(3) - 1
            df['momentum_5'] = close / df['close'].shift(5) - 1
            
            # Volatilidad instantánea
            df['volatility'] = df['high'] / df['low'] - 1
            df['atr'] = talib.ATR(high, low, close, timeperiod=7)
            df['volatility_normalized'] = df['atr'] / close
            
            # Volumen relativo
            df['volume_sma'] = talib.SMA(volume, timeperiod=10)
            df['volume_ratio'] = volume / df['volume_sma']
            
            # Indicadores de momentum adicionales
            df['stoch_k'], df['stoch_d'] = talib.STOCH(high, low, close, 
                                                      fastk_period=5, 
                                                      slowk_period=3, 
                                                      slowd_period=3)
            
            # Williams %R ultra-sensible
            df['williams_r'] = talib.WILLR(high, low, close, timeperiod=7)
            
            # CCI para momentum extremo
            df['cci'] = talib.CCI(high, low, close, timeperiod=10)
            
            # Precio vs EMAs
            df['price_above_ema_fast'] = close > df['ema_fast']
            df['price_above_ema_medium'] = close > df['ema_medium']
            
            return df
            
        except Exception as e:
            print(f"❌ Error calculando indicadores ultra: {e}")
            return df
    
    def calculate_market_conditions(self, df: pd.DataFrame) -> Dict:
        """
        Evaluar condiciones de mercado para scalping ultra-agresivo
        """
        try:
            latest = df.iloc[-1]
            
            # Volatilidad actual
            current_volatility = latest['volatility_normalized']
            volatility_suitable = (
                self.config.volatility_min <= current_volatility <= self.config.volatility_max
            )
            
            # Volumen suficiente
            volume_suitable = latest['volume_ratio'] >= self.config.volume_threshold
            
            # Momentum presente
            momentum_suitable = abs(latest['momentum_1']) >= self.config.momentum_threshold
            
            # Condiciones de tendencia
            trend_bullish = latest['ema_bullish_alignment']
            trend_bearish = latest['ema_bearish_alignment']
            
            # Condiciones de sobrecompra/sobreventa
            oversold_condition = latest['rsi'] < self.config.rsi_oversold
            overbought_condition = latest['rsi'] > self.config.rsi_overbought
            
            return {
                'volatility_suitable': volatility_suitable,
                'volume_suitable': volume_suitable,
                'momentum_suitable': momentum_suitable,
                'trend_bullish': trend_bullish,
                'trend_bearish': trend_bearish,
                'oversold': oversold_condition,
                'overbought': overbought_condition,
                'current_volatility': current_volatility,
                'volume_ratio': latest['volume_ratio'],
                'momentum': latest['momentum_1']
            }
            
        except Exception as e:
            print(f"❌ Error evaluando condiciones de mercado: {e}")
            return {}

class UltraRiskManager:
    """
    Gestor de riesgos ultra-agresivo para maximizar retornos
    """
    
    def __init__(self, config: UltraTradingConfig):
        self.config = config
    
    def calculate_position_size(self, capital: float, price: float, volatility: float) -> float:
        """
        Calcular tamaño de posición dinámico basado en volatilidad
        """
        try:
            # Tamaño base
            base_size = capital * self.config.position_size_pct
            
            # Ajuste por volatilidad (más volatilidad = menor posición)
            volatility_multiplier = max(0.5, min(1.5, 1 / (volatility * 100 + 1)))
            
            # Tamaño ajustado
            adjusted_size = base_size * volatility_multiplier
            
            # Cantidad en tokens
            quantity = adjusted_size / price
            
            return quantity
            
        except Exception as e:
            print(f"❌ Error calculando tamaño de posición: {e}")
            return 0.0
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """
        Calcular stop loss dinámico
        """
        if side == 'BUY':
            return entry_price * (1 - self.config.stop_loss)
        else:
            return entry_price * (1 + self.config.stop_loss)
    
    def calculate_take_profits(self, entry_price: float, side: str) -> Dict[str, float]:
        """
        Calcular take profits escalonados
        """
        if side == 'BUY':
            return {
                'tp1': entry_price * (1 + self.config.take_profit_1),
                'tp2': entry_price * (1 + self.config.take_profit_2),
                'tp3': entry_price * (1 + self.config.take_profit_3)
            }
        else:
            return {
                'tp1': entry_price * (1 - self.config.take_profit_1),
                'tp2': entry_price * (1 - self.config.take_profit_2),
                'tp3': entry_price * (1 - self.config.take_profit_3)
            }

class Enhanced15PercentStrategyV4Ultra:
    """
    Estrategia Enhanced 15% V4 Ultra-Agresiva
    Diseñada para alcanzar 15% mensual con $500 USDT
    """
    
    def __init__(self):
        self.config = UltraTradingConfig()
        self.analyzer = UltraMarketAnalyzer(self.config)
        self.risk_manager = UltraRiskManager(self.config)
    
    def generate_ultra_signal(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Generar señales ultra-agresivas para scalping
        """
        try:
            # print(f"🔍 DEBUG: generate_ultra_signal llamado con {len(df)} filas")
            # Calcular indicadores
            df_with_indicators = self.analyzer.calculate_ultra_indicators(df)
            
            if len(df_with_indicators) < 50:
                # print(f"🔍 DEBUG: Insuficientes datos ({len(df_with_indicators)} < 50)")
                return None
            
            # Evaluar condiciones de mercado
            market_conditions = self.analyzer.calculate_market_conditions(df_with_indicators)
            
            if not market_conditions:
                return None
            
            # Datos actuales
            current = df_with_indicators.iloc[-1]
            prev = df_with_indicators.iloc[-2]
            
            # Verificar condiciones básicas
            if not (market_conditions['volatility_suitable'] and 
                   market_conditions['volume_suitable'] and
                   market_conditions['momentum_suitable']):
                return None
            
            # Generar señales ultra-agresivas
            signal_strength = 0.0
            signal_type = 'HOLD'
            signal_reasons = []
            
            # === SEÑALES DE COMPRA ULTRA-AGRESIVAS ===
            buy_signals = 0
            buy_strength = 0.0
            
            # Debug info (comentado para performance)
            # print(f"🔍 DEBUG: RSI={current['rsi']:.2f}, Momentum={current['momentum_1']:.6f}, MACD={current['macd']:.6f}")
            
            # 1. RSI oversold (más agresivo)
            if current['rsi'] < self.config.rsi_oversold:
                buy_strength += 0.20
                signal_reasons.append("RSI oversold")
                # print(f"🔍 DEBUG: Buy signal 1 triggered - RSI oversold")
            
            # 1b. Momentum positivo
            if current['momentum_1'] > 0:
                buy_strength += 0.15
                signal_reasons.append("Momentum positivo")
                # print(f"🔍 DEBUG: Buy signal 1b triggered - Momentum positivo")
            
            # 2. MACD bullish crossover
            if (current['macd_bullish'] and not prev['macd_bullish']):
                buy_signals += 1
                buy_strength += 0.2
                signal_reasons.append("MACD bullish crossover")
            
            # 3. Precio rebota en banda inferior
            if (current['bb_position'] < 0.2 and current['close'] > prev['close']):
                buy_signals += 1
                buy_strength += 0.15
                signal_reasons.append("Rebote banda inferior")
            
            # 4. Alineación bullish de EMAs
            if current['ema_bullish_alignment']:
                buy_signals += 1
                buy_strength += 0.15
                signal_reasons.append("Alineación EMA bullish")
            
            # 5. Stochastic oversold
            if current['stoch_k'] < 20 and current['stoch_k'] > prev['stoch_k']:
                buy_signals += 1
                buy_strength += 0.1
                signal_reasons.append("Stochastic oversold recovery")
            
            # 6. Williams %R extremo
            if current['williams_r'] < -80 and current['williams_r'] > prev['williams_r']:
                buy_signals += 1
                buy_strength += 0.1
                signal_reasons.append("Williams %R extremo")
            
            # 7. Momentum múltiple positivo
            if (current['momentum_1'] > 0 and current['momentum_3'] > 0):
                buy_signals += 1
                buy_strength += 0.05
                signal_reasons.append("Momentum múltiple+")
            
            # === SEÑALES DE VENTA ULTRA-AGRESIVAS ===
            sell_signals = 0
            sell_strength = 0.0
            
            # 1. RSI overbought + momentum negativo
            if (current['rsi'] > self.config.rsi_overbought and 
                current['momentum_1'] < 0):
                sell_signals += 1
                sell_strength += 0.25
                signal_reasons.append("RSI overbought + momentum-")
            
            # 2. MACD bearish crossover
            if (current['macd_bearish'] and not prev['macd_bearish']):
                sell_signals += 1
                sell_strength += 0.2
                signal_reasons.append("MACD bearish crossover")
            
            # 3. Precio rechaza banda superior
            if (current['bb_position'] > 0.8 and current['close'] < prev['close']):
                sell_signals += 1
                sell_strength += 0.15
                signal_reasons.append("Rechazo banda superior")
            
            # 4. Alineación bearish de EMAs
            if current['ema_bearish_alignment']:
                sell_signals += 1
                sell_strength += 0.15
                signal_reasons.append("Alineación EMA bearish")
            
            # 5. Stochastic overbought
            if current['stoch_k'] > 80 and current['stoch_k'] < prev['stoch_k']:
                sell_signals += 1
                sell_strength += 0.1
                signal_reasons.append("Stochastic overbought decline")
            
            # 6. Williams %R extremo
            if current['williams_r'] > -20 and current['williams_r'] < prev['williams_r']:
                sell_signals += 1
                sell_strength += 0.1
                signal_reasons.append("Williams %R extremo")
            
            # 7. Momentum múltiple negativo
            if (current['momentum_1'] < 0 and current['momentum_3'] < 0):
                sell_signals += 1
                sell_strength += 0.05
                signal_reasons.append("Momentum múltiple-")
            
            # Determinar señal final (EXTREMADAMENTE agresivo: solo 1 señal mínima)
            if buy_signals >= 1 and buy_strength >= self.config.signal_strength_threshold:
                signal_type = 'BUY'
                signal_strength = min(1.0, buy_strength)
            elif sell_signals >= 1 and sell_strength >= self.config.signal_strength_threshold:
                signal_type = 'SELL'
                signal_strength = min(1.0, sell_strength)
            
            # Verificar confianza mínima
            if signal_strength < self.config.min_signal_confidence and signal_type != 'HOLD':
                signal_type = 'HOLD'
                signal_strength = 0.0
            
            # Calcular probabilidad de éxito REALISTA
            # Máximo 65% para señales muy fuertes, promedio 55%
            success_probability = min(0.65, 0.45 + signal_strength * 0.2)
            
            result = {
                'signal': signal_type,
                'signal_strength': signal_strength,
                'success_probability': success_probability,
                'current_price': current['close'],
                'reasons': signal_reasons,
                'market_conditions': market_conditions,
                'indicators': {
                    'rsi': current['rsi'],
                    'macd': current['macd'],
                    'bb_position': current['bb_position'],
                    'momentum': current['momentum_1'],
                    'volatility': current['volatility_normalized'],
                    'volume_ratio': current['volume_ratio']
                },
                'risk_metrics': {
                    'volatility': current['volatility_normalized'],
                    'atr': current['atr']
                }
            }
            # print(f"🔍 DEBUG: Señal generada: {signal_type}, Fuerza: {signal_strength:.3f}, Probabilidad: {success_probability:.3f}")
            return result
            
        except Exception as e:
            print(f"❌ Error generando señal ultra: {e}")
            return None
    
    def calculate_trade_plan(self, signal_data: Dict, capital: float) -> Dict:
        """
        Calcular plan de trading completo
        """
        try:
            if not signal_data or signal_data['signal'] == 'HOLD':
                return {}
            
            entry_price = signal_data['current_price']
            volatility = signal_data['risk_metrics']['volatility']
            
            # Calcular tamaño de posición
            quantity = self.risk_manager.calculate_position_size(
                capital, entry_price, volatility
            )
            
            # Calcular stop loss
            stop_loss = self.risk_manager.calculate_stop_loss(
                entry_price, signal_data['signal']
            )
            
            # Calcular take profits
            take_profits = self.risk_manager.calculate_take_profits(
                entry_price, signal_data['signal']
            )
            
            # Calcular distribución de cantidad
            tp1_qty = quantity * self.config.tp1_allocation
            tp2_qty = quantity * self.config.tp2_allocation
            tp3_qty = quantity * self.config.tp3_allocation
            
            return {
                'entry_price': entry_price,
                'quantity': quantity,
                'stop_loss': stop_loss,
                'take_profits': take_profits,
                'quantity_distribution': {
                    'tp1': tp1_qty,
                    'tp2': tp2_qty,
                    'tp3': tp3_qty
                },
                'risk_reward_ratios': {
                    'tp1': abs(take_profits['tp1'] - entry_price) / abs(entry_price - stop_loss),
                    'tp2': abs(take_profits['tp2'] - entry_price) / abs(entry_price - stop_loss),
                    'tp3': abs(take_profits['tp3'] - entry_price) / abs(entry_price - stop_loss)
                },
                'max_loss_usdt': quantity * abs(entry_price - stop_loss),
                'potential_profits': {
                    'tp1': tp1_qty * abs(take_profits['tp1'] - entry_price),
                    'tp2': tp2_qty * abs(take_profits['tp2'] - entry_price),
                    'tp3': tp3_qty * abs(take_profits['tp3'] - entry_price)
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculando plan de trading: {e}")
            return {}

def main():
    """
    Función principal para testing
    """
    print("🚀 ESTRATEGIA V4 ULTRA-AGRESIVA INICIALIZADA")
    print(f"💰 Capital Base: ${UltraTradingConfig().base_capital}")
    print(f"🎯 Objetivo Diario: ${UltraTradingConfig().daily_target_usdt}")
    print(f"🎯 Objetivo Mensual: ${UltraTradingConfig().monthly_target_usdt}")
    print("⚡ Configuración ultra-agresiva para scalping de alta frecuencia")
    
    strategy = Enhanced15PercentStrategyV4Ultra()
    print("✅ Estrategia V4 Ultra lista para implementación")

if __name__ == "__main__":
    main()