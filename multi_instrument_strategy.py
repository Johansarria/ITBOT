#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Estrategia Multi-Instrumento Adaptativa
Estrategia que se adapta automáticamente a Forex, Índices y Metales para 15%+ mensual
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class MultiInstrumentStrategy:
    """
    Estrategia adaptativa para múltiples instrumentos financieros
    """
    
    def __init__(self, instrument_type: str = 'forex', instrument_name: str = 'EURUSD'):
        self.instrument_type = instrument_type
        self.instrument_name = instrument_name
        
        # Configuraciones base por tipo de instrumento
        self.base_configs = {
            'forex': {
                'risk_per_trade': 0.04,        # 4% - Forex permite más riesgo
                'max_daily_trades': 8,         # Más operaciones en Forex
                'stop_loss_pct': 0.006,        # 0.6% - Stops más ajustados
                'take_profit_multiplier': 3.0, # 3:1 ratio
                'rsi_oversold': 25,            # Más agresivo
                'rsi_overbought': 75,
                'volatility_threshold': 0.008,  # Threshold más bajo
                'momentum_threshold': 0.002,
                'volume_threshold': 1.1,       # Menos exigente
                'session_trading': True,       # Trading por sesiones
            },
            'index': {
                'risk_per_trade': 0.035,       # 3.5% - Moderado
                'max_daily_trades': 6,         # Menos operaciones
                'stop_loss_pct': 0.008,        # 0.8% - Stops normales
                'take_profit_multiplier': 2.5, # 2.5:1 ratio
                'rsi_oversold': 30,            # Estándar
                'rsi_overbought': 70,
                'volatility_threshold': 0.012,
                'momentum_threshold': 0.003,
                'volume_threshold': 1.3,       # Más exigente
                'session_trading': False,      # Trading continuo
            },
            'metal': {
                'risk_per_trade': 0.03,        # 3% - Más conservador
                'max_daily_trades': 5,         # Pocas operaciones
                'stop_loss_pct': 0.01,         # 1% - Stops más amplios
                'take_profit_multiplier': 2.0, # 2:1 ratio
                'rsi_oversold': 35,            # Menos agresivo
                'rsi_overbought': 65,
                'volatility_threshold': 0.015,
                'momentum_threshold': 0.004,
                'volume_threshold': 1.5,       # Muy exigente
                'session_trading': False,      # Trading continuo
            }
        }
        
        # Cargar configuración específica
        self.config = self.base_configs.get(instrument_type, self.base_configs['forex']).copy()
        
        # Variables de estado
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_stop = 0
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.session_pnl = 0.0
        
        # Adaptación dinámica
        self.volatility_history = []
        self.performance_history = []
        self.adaptation_period = 100  # Períodos para adaptación
        
    def adapt_to_market_conditions(self, data: pd.DataFrame, current_idx: int):
        """
        Adapta la estrategia a las condiciones actuales del mercado
        """
        if current_idx < self.adaptation_period:
            return
        
        # Analizar volatilidad reciente
        recent_data = data.iloc[current_idx-self.adaptation_period:current_idx]
        current_volatility = recent_data['volatility'].mean()
        
        # Adaptar parámetros según volatilidad
        if current_volatility > self.config['volatility_threshold'] * 1.5:
            # Alta volatilidad - ser más conservador
            self.config['risk_per_trade'] *= 0.8
            self.config['stop_loss_pct'] *= 0.9
            self.config['max_daily_trades'] = max(3, int(self.config['max_daily_trades'] * 0.7))
        elif current_volatility < self.config['volatility_threshold'] * 0.5:
            # Baja volatilidad - ser más agresivo
            self.config['risk_per_trade'] *= 1.1
            self.config['take_profit_multiplier'] *= 1.2
            self.config['max_daily_trades'] = min(10, int(self.config['max_daily_trades'] * 1.3))
        
        # Adaptar según performance reciente
        if len(self.performance_history) >= 10:
            recent_performance = sum(self.performance_history[-10:])
            if recent_performance < -0.05:  # Perdiendo 5%
                self.config['risk_per_trade'] *= 0.7  # Reducir riesgo
            elif recent_performance > 0.08:  # Ganando 8%
                self.config['risk_per_trade'] *= 1.1  # Aumentar riesgo
    
    def calculate_adaptive_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores adaptados al tipo de instrumento
        """
        df = data.copy()
        
        # Indicadores base
        df['rsi'] = self._calculate_rsi(df['close'], 14)
        df['rsi_fast'] = self._calculate_rsi(df['close'], 7)  # RSI rápido
        
        # EMAs adaptadas por instrumento
        if self.instrument_type == 'forex':
            # Forex: EMAs más rápidas
            df['ema_fast'] = df['close'].ewm(span=8).mean()
            df['ema_slow'] = df['close'].ewm(span=21).mean()
            df['ema_trend'] = df['close'].ewm(span=50).mean()
        elif self.instrument_type == 'index':
            # Índices: EMAs estándar
            df['ema_fast'] = df['close'].ewm(span=12).mean()
            df['ema_slow'] = df['close'].ewm(span=26).mean()
            df['ema_trend'] = df['close'].ewm(span=55).mean()
        else:  # metal
            # Metales: EMAs más lentas
            df['ema_fast'] = df['close'].ewm(span=15).mean()
            df['ema_slow'] = df['close'].ewm(span=30).mean()
            df['ema_trend'] = df['close'].ewm(span=60).mean()
        
        # Bollinger Bands adaptadas
        bb_period = 20 if self.instrument_type != 'forex' else 16
        bb_std = 2.0 if self.instrument_type != 'metal' else 1.8
        
        bb_data = self._calculate_bollinger_bands(df['close'], bb_period, bb_std)
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR y volatilidad
        df['atr'] = self._calculate_atr(df)
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
        
        # Momentum adaptado
        momentum_period = 5 if self.instrument_type == 'forex' else 8
        df['momentum'] = df['close'].pct_change(momentum_period)
        
        # Volumen (si está disponible)
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
        else:
            df['volume_ratio'] = 1.0
        
        # Indicadores específicos por tipo
        if self.instrument_type == 'forex':
            df = self._add_forex_indicators(df)
        elif self.instrument_type == 'index':
            df = self._add_index_indicators(df)
        elif self.instrument_type == 'metal':
            df = self._add_metal_indicators(df)
        
        return df
    
    def _add_forex_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade indicadores específicos para Forex"""
        # Detección de sesiones de trading
        df['asian_session'] = df.index.hour.isin(range(0, 9))
        df['london_session'] = df.index.hour.isin(range(8, 17))
        df['ny_session'] = df.index.hour.isin(range(13, 22))
        df['overlap_session'] = df['london_session'] & df['ny_session']
        
        # Fuerza de la moneda (simplificado)
        df['currency_strength'] = df['close'].rolling(50).apply(
            lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() != x.min() else 0.5
        )
        
        return df
    
    def _add_index_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade indicadores específicos para Índices"""
        # Momentum del mercado
        df['market_momentum'] = df['close'].rolling(20).apply(
            lambda x: len([i for i in range(1, len(x)) if x.iloc[i] > x.iloc[i-1]]) / (len(x)-1)
        )
        
        # Detección de breakouts
        df['resistance_20'] = df['high'].rolling(20).max()
        df['support_20'] = df['low'].rolling(20).min()
        df['breakout_up'] = df['close'] > df['resistance_20'].shift(1)
        df['breakout_down'] = df['close'] < df['support_20'].shift(1)
        
        return df
    
    def _add_metal_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Añade indicadores específicos para Metales"""
        # Volatilidad clusters (común en metales)
        df['vol_cluster'] = df['volatility'] > df['volatility'].rolling(50).quantile(0.8)
        
        # Tendencia a largo plazo
        df['long_trend'] = df['close'].rolling(100).mean()
        df['trend_strength'] = (df['close'] - df['long_trend']) / df['long_trend']
        
        # Safe haven indicator (simplificado)
        df['safe_haven'] = (df['volatility'] > df['volatility'].rolling(20).mean() * 1.5) & \
                          (df['close'] > df['close'].shift(5))
        
        return df
    
    def generate_adaptive_signal(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Genera señales adaptadas al tipo de instrumento
        """
        if idx < 50:
            return {'action': 'MANTENER', 'reason': 'Insufficient data'}
        
        # Adaptar estrategia si es necesario
        if idx % self.adaptation_period == 0:
            self.adapt_to_market_conditions(df, idx)
        
        # Verificar límites
        if self.daily_trades >= self.config['max_daily_trades']:
            return {'action': 'MANTENER', 'reason': 'Daily trade limit'}
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        # Filtros básicos
        if current['volatility'] < self.config['volatility_threshold'] * 0.5:
            return {'action': 'MANTENER', 'reason': 'Low volatility'}
        
        # Generar señales según tipo de instrumento
        if self.instrument_type == 'forex':
            return self._generate_forex_signal(df, idx, current, prev)
        elif self.instrument_type == 'index':
            return self._generate_index_signal(df, idx, current, prev)
        elif self.instrument_type == 'metal':
            return self._generate_metal_signal(df, idx, current, prev)
        else:
            return self._generate_generic_signal(df, idx, current, prev)
    
    def _generate_forex_signal(self, df: pd.DataFrame, idx: int, current: pd.Series, prev: pd.Series) -> Dict[str, Any]:
        """Genera señales específicas para Forex"""
        score = 0
        signals = []
        
        # Filtro de sesión (solo operar en sesiones activas)
        if self.config['session_trading']:
            if not (current['london_session'] or current['ny_session'] or current['overlap_session']):
                return {'action': 'MANTENER', 'reason': 'Outside trading session'}
        
        # RSI en zona extrema
        if current['rsi'] < self.config['rsi_oversold']:
            score += 2
            signals.append('RSI oversold')
        elif current['rsi'] > self.config['rsi_overbought']:
            score -= 2
            signals.append('RSI overbought')
        
        # Cruce de EMAs
        if prev['ema_fast'] <= prev['ema_slow'] and current['ema_fast'] > current['ema_slow']:
            score += 3
            signals.append('EMA bullish cross')
        elif prev['ema_fast'] >= prev['ema_slow'] and current['ema_fast'] < current['ema_slow']:
            score -= 3
            signals.append('EMA bearish cross')
        
        # Momentum
        if current['momentum'] > self.config['momentum_threshold']:
            score += 1
            signals.append('Positive momentum')
        elif current['momentum'] < -self.config['momentum_threshold']:
            score -= 1
            signals.append('Negative momentum')
        
        # Fuerza de moneda
        if current['currency_strength'] > 0.7:
            score += 1
            signals.append('Strong currency')
        elif current['currency_strength'] < 0.3:
            score -= 1
            signals.append('Weak currency')
        
        # Sesión de overlap (más volátil)
        if current['overlap_session']:
            score = int(score * 1.2)  # Amplificar señales
            signals.append('Overlap session boost')
        
        return self._evaluate_score(score, signals, 'forex')
    
    def _generate_index_signal(self, df: pd.DataFrame, idx: int, current: pd.Series, prev: pd.Series) -> Dict[str, Any]:
        """Genera señales específicas para Índices"""
        score = 0
        signals = []
        
        # RSI
        if current['rsi'] < self.config['rsi_oversold']:
            score += 2
            signals.append('RSI oversold')
        elif current['rsi'] > self.config['rsi_overbought']:
            score -= 2
            signals.append('RSI overbought')
        
        # Tendencia
        if current['ema_fast'] > current['ema_slow'] > current['ema_trend']:
            score += 2
            signals.append('Strong uptrend')
        elif current['ema_fast'] < current['ema_slow'] < current['ema_trend']:
            score -= 2
            signals.append('Strong downtrend')
        
        # Breakouts
        if current['breakout_up']:
            score += 3
            signals.append('Upward breakout')
        elif current['breakout_down']:
            score -= 3
            signals.append('Downward breakout')
        
        # Momentum del mercado
        if current['market_momentum'] > 0.6:
            score += 1
            signals.append('Market momentum up')
        elif current['market_momentum'] < 0.4:
            score -= 1
            signals.append('Market momentum down')
        
        # Volumen
        if current['volume_ratio'] > self.config['volume_threshold']:
            score = int(score * 1.3)  # Amplificar con volumen
            signals.append('High volume confirmation')
        
        return self._evaluate_score(score, signals, 'index')
    
    def _generate_metal_signal(self, df: pd.DataFrame, idx: int, current: pd.Series, prev: pd.Series) -> Dict[str, Any]:
        """Genera señales específicas para Metales"""
        score = 0
        signals = []
        
        # RSI (menos agresivo)
        if current['rsi'] < self.config['rsi_oversold']:
            score += 2
            signals.append('RSI oversold')
        elif current['rsi'] > self.config['rsi_overbought']:
            score -= 2
            signals.append('RSI overbought')
        
        # Tendencia a largo plazo
        if current['trend_strength'] > 0.05:
            score += 2
            signals.append('Strong uptrend')
        elif current['trend_strength'] < -0.05:
            score -= 2
            signals.append('Strong downtrend')
        
        # Safe haven
        if current['safe_haven']:
            score += 2
            signals.append('Safe haven demand')
        
        # Volatility cluster
        if current['vol_cluster'] and current['close'] > prev['close']:
            score += 1
            signals.append('Volatility cluster up')
        elif current['vol_cluster'] and current['close'] < prev['close']:
            score -= 1
            signals.append('Volatility cluster down')
        
        # Bollinger Bands
        if current['bb_position'] < 0.2:
            score += 1
            signals.append('BB oversold')
        elif current['bb_position'] > 0.8:
            score -= 1
            signals.append('BB overbought')
        
        return self._evaluate_score(score, signals, 'metal')
    
    def _generate_generic_signal(self, df: pd.DataFrame, idx: int, current: pd.Series, prev: pd.Series) -> Dict[str, Any]:
        """Genera señales genéricas"""
        score = 0
        signals = []
        
        # RSI
        if current['rsi'] < 30:
            score += 2
        elif current['rsi'] > 70:
            score -= 2
        
        # EMA
        if current['ema_fast'] > current['ema_slow']:
            score += 1
        else:
            score -= 1
        
        # Momentum
        if current['momentum'] > 0.003:
            score += 1
        elif current['momentum'] < -0.003:
            score -= 1
        
        return self._evaluate_score(score, signals, 'generic')
    
    def _evaluate_score(self, score: int, signals: List[str], signal_type: str) -> Dict[str, Any]:
        """Evalúa el score y determina la acción"""
        min_score = 4 if signal_type == 'forex' else 3
        
        if score >= min_score:
            return {
                'action': 'COMPRAR',
                'score': score,
                'signals': signals,
                'confidence': min(score / 6, 1.0)
            }
        elif score <= -min_score:
            return {
                'action': 'VENDER',
                'score': abs(score),
                'signals': signals,
                'confidence': min(abs(score) / 6, 1.0)
            }
        else:
            return {
                'action': 'MANTENER',
                'score': abs(score),
                'reason': f'Insufficient signals ({score})'
            }
    
    def calculate_position_size(self, price: float, account_balance: float) -> float:
        """Calcula tamaño de posición adaptado"""
        risk_amount = account_balance * self.config['risk_per_trade']
        stop_distance = price * self.config['stop_loss_pct']
        
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
            # Limitar según tipo de instrumento
            max_position_pct = 0.4 if self.instrument_type == 'forex' else 0.3
            max_position_value = account_balance * max_position_pct
            max_position_size = max_position_value / price
            return min(position_size, max_position_size)
        
        return 0
    
    def calculate_stop_loss_take_profit(self, entry_price: float, direction: str, atr: float) -> Tuple[float, float]:
        """Calcula stop loss y take profit adaptados"""
        # Stop loss basado en ATR y configuración
        if self.instrument_type == 'forex':
            stop_distance = max(entry_price * self.config['stop_loss_pct'], atr * 1.5)
        elif self.instrument_type == 'index':
            stop_distance = max(entry_price * self.config['stop_loss_pct'], atr * 2.0)
        else:  # metal
            stop_distance = max(entry_price * self.config['stop_loss_pct'], atr * 2.5)
        
        if direction == "COMPRAR":
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + (stop_distance * self.config['take_profit_multiplier'])
        else:  # VENDER
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - (stop_distance * self.config['take_profit_multiplier'])
        
        return stop_loss, take_profit
    
    def update_performance(self, pnl: float):
        """Actualiza métricas de performance"""
        self.daily_pnl += pnl
        self.session_pnl += pnl
        self.daily_trades += 1
        
        # Guardar para adaptación
        pnl_pct = pnl / 100000  # Asumiendo balance de 100k
        self.performance_history.append(pnl_pct)
        
        # Mantener solo últimos 50 trades
        if len(self.performance_history) > 50:
            self.performance_history.pop(0)
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna información de la estrategia"""
        return {
            'instrument_type': self.instrument_type,
            'instrument_name': self.instrument_name,
            'current_config': self.config,
            'daily_trades': self.daily_trades,
            'daily_pnl': self.daily_pnl,
            'session_pnl': self.session_pnl,
            'adaptation_active': len(self.performance_history) >= 10
        }
    
    # Métodos auxiliares
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int, std_dev: float) -> Dict[str, pd.Series]:
        """Calcula Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return {'upper': upper, 'middle': middle, 'lower': lower}
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=period).mean()


def create_multi_instrument_strategies() -> Dict[str, MultiInstrumentStrategy]:
    """
    Crea estrategias para todos los instrumentos
    """
    strategies = {
        'EURUSD': MultiInstrumentStrategy('forex', 'EURUSD'),
        'AUDCAD': MultiInstrumentStrategy('forex', 'AUDCAD'),
        'NAS100': MultiInstrumentStrategy('index', 'NAS100'),
        'XAUUSD': MultiInstrumentStrategy('metal', 'XAUUSD')
    }
    
    return strategies


if __name__ == "__main__":
    # Crear estrategias para todos los instrumentos
    strategies = create_multi_instrument_strategies()
    
    print("🌍 Estrategias Multi-Instrumento Creadas")
    print("=" * 50)
    
    for name, strategy in strategies.items():
        info = strategy.get_strategy_info()
        print(f"\n📈 {name} ({info['instrument_type'].upper()})")
        print(f"   Riesgo por trade: {info['current_config']['risk_per_trade']*100:.1f}%")
        print(f"   Stop loss: {info['current_config']['stop_loss_pct']*100:.1f}%")
        print(f"   Take profit ratio: {info['current_config']['take_profit_multiplier']:.1f}:1")
        print(f"   Max trades diarios: {info['current_config']['max_daily_trades']}")
    
    print("\n✅ Estrategias listas para backtesting multi-instrumento")