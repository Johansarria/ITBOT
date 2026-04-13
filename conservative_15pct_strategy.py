#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Estrategia Conservadora 20% Mensual
Enfoque en consistencia y control de riesgo para alcanzar 20% mensual sostenible
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class Conservative15PctStrategy:
    """
    Estrategia conservadora diseñada para alcanzar 20% mensual de forma consistente
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            # Gestión de riesgo conservadora
            'base_risk_per_trade': 0.025,  # 2.5% por operación
            'max_risk_per_trade': 0.04,    # 4% máximo
            'min_risk_per_trade': 0.015,   # 1.5% mínimo
            'daily_risk_limit': 0.12,      # 12% diario
            'max_daily_trades': 6,         # Menos operaciones, más calidad
            'max_consecutive_losses': 2,
            
            # Parámetros técnicos conservadores
            'rsi_period': 14,
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0,
            'atr_period': 14,
            
            # Filtros de calidad estrictos
            'min_signal_strength': 7,      # Señales muy fuertes
            'min_trend_confirmation': 3,   # Confirmación de tendencia
            'min_volatility': 0.003,
            'max_volatility': 0.035,
            'volume_confirmation_required': True,
            
            # Targets conservadores pero efectivos
            'profit_target_multiplier': 3.0,  # 3:1 reward/risk
            'stop_loss_atr_multiplier': 0.8,  # Stop loss más ajustado
            'partial_profit_level': 0.012,    # Tomar ganancia parcial en 1.2%
            'partial_profit_percentage': 0.5,  # 50% de la posición
            
            # Filtros de tiempo
            'avoid_first_hour': True,
            'avoid_last_hour': True,
            'min_time_between_trades': 30,  # 30 minutos mínimo
            
            # Confirmaciones adicionales
            'require_multiple_timeframe': True,
            'require_momentum_confirmation': True,
            'require_volume_confirmation': True,
        }
        
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.partial_profit_taken = False
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.last_trade_time = None
        self.monthly_target_progress = 0.0
        
    def calculate_comprehensive_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos comprehensivos
        """
        df = data.copy()
        
        # RSI con múltiples períodos
        df['rsi_14'] = self._calculate_rsi(df['close'], 14)
        df['rsi_21'] = self._calculate_rsi(df['close'], 21)
        df['rsi_avg'] = (df['rsi_14'] + df['rsi_21']) / 2
        
        # MACD estándar y optimizado
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        df['macd_slope'] = df['macd'].diff()
        df['macd_signal_slope'] = df['macd_signal'].diff()
        
        # Bollinger Bands con análisis de posición
        bb_data = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_width'] = (bb_data['upper'] - bb_data['lower']) / bb_data['middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(20).mean() * 0.8
        
        # EMAs para análisis de tendencia
        periods = [8, 13, 21, 34, 55, 89]
        for period in periods:
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
        
        # Análisis de tendencia multi-timeframe
        df['trend_short'] = np.where(df['ema_8'] > df['ema_21'], 1, 
                                   np.where(df['ema_8'] < df['ema_21'], -1, 0))
        df['trend_medium'] = np.where(df['ema_21'] > df['ema_55'], 1, 
                                    np.where(df['ema_21'] < df['ema_55'], -1, 0))
        df['trend_long'] = np.where(df['ema_55'] > df['ema_89'], 1, 
                                  np.where(df['ema_55'] < df['ema_89'], -1, 0))
        
        # Fuerza de tendencia
        df['trend_strength'] = (df['trend_short'] + df['trend_medium'] + df['trend_long']) / 3
        df['trend_alignment'] = (df['trend_short'] == df['trend_medium']) & (df['trend_medium'] == df['trend_long'])
        
        # ATR y volatilidad
        df['atr'] = self._calculate_atr(df)
        df['atr_normalized'] = df['atr'] / df['close']
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
        
        # Momentum indicators
        df['momentum_3'] = df['close'].pct_change(3)
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_8'] = df['close'].pct_change(8)
        df['momentum_13'] = df['close'].pct_change(13)
        
        # Momentum strength
        df['momentum_strength'] = (
            np.sign(df['momentum_3']) + 
            np.sign(df['momentum_5']) + 
            np.sign(df['momentum_8'])
        ) / 3
        
        # Support/Resistance levels
        df['support_20'] = df['low'].rolling(20).min()
        df['resistance_20'] = df['high'].rolling(20).max()
        df['support_50'] = df['low'].rolling(50).min()
        df['resistance_50'] = df['high'].rolling(50).max()
        
        # Distance to S/R levels
        df['support_distance'] = (df['close'] - df['support_20']) / df['close']
        df['resistance_distance'] = (df['resistance_20'] - df['close']) / df['close']
        
        # Volume analysis
        if 'volume' in df.columns:
            df['volume_sma_20'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_20']
            df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
            
            # Price-Volume relationship
            df['pv_trend'] = np.where(
                (df['close'] > df['close'].shift(1)) & (df['volume'] > df['volume_sma_20']), 1,
                np.where(
                    (df['close'] < df['close'].shift(1)) & (df['volume'] > df['volume_sma_20']), -1, 0
                )
            )
        else:
            df['volume_ratio'] = 1.0
            df['volume_trend'] = 1.0
            df['pv_trend'] = 0
        
        # Advanced patterns
        df['higher_highs'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['lower_lows'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))
        df['higher_lows'] = (df['low'] > df['low'].shift(1)) & (df['low'].shift(1) > df['low'].shift(2))
        df['lower_highs'] = (df['high'] < df['high'].shift(1)) & (df['high'].shift(1) < df['high'].shift(2))
        
        # Market structure
        df['bullish_structure'] = df['higher_highs'] & df['higher_lows']
        df['bearish_structure'] = df['lower_highs'] & df['lower_lows']
        
        # Divergence detection
        df['price_momentum_div'] = self._detect_divergence(df['close'], df['rsi_14'])
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calcula MACD"""
        ema_fast = prices.ewm(span=self.config['macd_fast']).mean()
        ema_slow = prices.ewm(span=self.config['macd_slow']).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.config['macd_signal']).mean()
        histogram = macd - signal
        
        return {'macd': macd, 'signal': signal, 'histogram': histogram}
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calcula Bollinger Bands"""
        middle = prices.rolling(window=self.config['bb_period']).mean()
        std = prices.rolling(window=self.config['bb_period']).std()
        upper = middle + (std * self.config['bb_std'])
        lower = middle - (std * self.config['bb_std'])
        
        return {'upper': upper, 'middle': middle, 'lower': lower}
    
    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calcula Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=self.config['atr_period']).mean()
    
    def _detect_divergence(self, price: pd.Series, indicator: pd.Series, window: int = 10) -> pd.Series:
        """Detecta divergencias entre precio e indicador"""
        price_trend = price.rolling(window).apply(lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1)
        indicator_trend = indicator.rolling(window).apply(lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1)
        
        # Divergencia: precio y indicador van en direcciones opuestas
        return (price_trend != indicator_trend).astype(int)
    
    def calculate_signal_quality(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Calcula la calidad de la señal con múltiples confirmaciones
        """
        if idx < 60:  # Necesitamos suficientes datos
            return {'quality_score': 0, 'signal': 'MANTENER', 'reasons': []}
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        prev2 = df.iloc[idx - 2]
        
        buy_score = 0
        sell_score = 0
        reasons = []
        
        # 1. RSI Analysis (peso: 3)
        if current['rsi_avg'] < self.config['rsi_oversold'] and current['rsi_avg'] > prev['rsi_avg']:
            buy_score += 3
            reasons.append("RSI oversold recovery")
        elif current['rsi_avg'] > self.config['rsi_overbought'] and current['rsi_avg'] < prev['rsi_avg']:
            sell_score += 3
            reasons.append("RSI overbought decline")
        
        # 2. MACD Analysis (peso: 4)
        if (prev['macd'] <= prev['macd_signal'] and current['macd'] > current['macd_signal'] and
            current['macd_slope'] > 0):
            buy_score += 4
            reasons.append("MACD bullish crossover with momentum")
        elif (prev['macd'] >= prev['macd_signal'] and current['macd'] < current['macd_signal'] and
              current['macd_slope'] < 0):
            sell_score += 4
            reasons.append("MACD bearish crossover with momentum")
        
        # 3. Trend Alignment (peso: 5)
        if current['trend_alignment'] and current['trend_strength'] > 0.6:
            buy_score += 5
            reasons.append("Strong bullish trend alignment")
        elif current['trend_alignment'] and current['trend_strength'] < -0.6:
            sell_score += 5
            reasons.append("Strong bearish trend alignment")
        
        # 4. Bollinger Bands (peso: 3)
        if (current['bb_position'] < 0.15 and current['close'] > prev['close'] and
            not current['bb_squeeze']):
            buy_score += 3
            reasons.append("BB lower band bounce")
        elif (current['bb_position'] > 0.85 and current['close'] < prev['close'] and
              not current['bb_squeeze']):
            sell_score += 3
            reasons.append("BB upper band rejection")
        
        # 5. Momentum Confirmation (peso: 3)
        if current['momentum_strength'] > 0.6 and current['momentum_5'] > 0.005:
            buy_score += 3
            reasons.append("Strong bullish momentum")
        elif current['momentum_strength'] < -0.6 and current['momentum_5'] < -0.005:
            sell_score += 3
            reasons.append("Strong bearish momentum")
        
        # 6. Volume Confirmation (peso: 2)
        if self.config['require_volume_confirmation']:
            if current['volume_ratio'] > 1.3 and current['pv_trend'] == 1:
                buy_score += 2
                reasons.append("Volume confirms bullish move")
            elif current['volume_ratio'] > 1.3 and current['pv_trend'] == -1:
                sell_score += 2
                reasons.append("Volume confirms bearish move")
        
        # 7. Support/Resistance (peso: 2)
        if current['support_distance'] < 0.008:  # Near support
            buy_score += 2
            reasons.append("Near support level")
        elif current['resistance_distance'] < 0.008:  # Near resistance
            sell_score += 2
            reasons.append("Near resistance level")
        
        # 8. Market Structure (peso: 2)
        if current['bullish_structure']:
            buy_score += 2
            reasons.append("Bullish market structure")
        elif current['bearish_structure']:
            sell_score += 2
            reasons.append("Bearish market structure")
        
        # 9. Divergence (peso: 3)
        if current['price_momentum_div'] == 1:
            # Divergencia puede indicar reversión
            if current['rsi_avg'] < 50:  # RSI bajo sugiere compra
                buy_score += 3
                reasons.append("Bullish divergence detected")
            else:  # RSI alto sugiere venta
                sell_score += 3
                reasons.append("Bearish divergence detected")
        
        # Determinar señal final
        quality_score = max(buy_score, sell_score)
        
        if buy_score >= self.config['min_signal_strength'] and buy_score > sell_score + 2:
            signal = "COMPRAR"
        elif sell_score >= self.config['min_signal_strength'] and sell_score > buy_score + 2:
            signal = "VENDER"
        else:
            signal = "MANTENER"
        
        return {
            'quality_score': quality_score,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'signal': signal,
            'reasons': reasons
        }
    
    def calculate_conservative_risk(self, quality_score: int) -> float:
        """
        Calcula riesgo conservador basado en calidad de señal y condiciones
        """
        base_risk = self.config['base_risk_per_trade']
        
        # Ajustar por calidad de señal
        quality_multiplier = min(1.3, 1.0 + (quality_score - self.config['min_signal_strength']) * 0.05)
        
        # Reducir riesgo después de pérdidas
        if self.consecutive_losses >= self.config['max_consecutive_losses']:
            loss_multiplier = 0.4
        elif self.consecutive_losses >= 1:
            loss_multiplier = 0.7
        else:
            loss_multiplier = 1.0
        
        # Ajustar por progreso mensual
        if self.monthly_target_progress >= 0.12:  # Si ya tenemos 12% este mes
            progress_multiplier = 0.6  # Ser más conservador
        elif self.monthly_target_progress >= 0.08:  # 8%
            progress_multiplier = 0.8
        elif self.monthly_target_progress < 0.02:  # Menos de 2%
            progress_multiplier = 1.1  # Ser un poco más agresivo
        else:
            progress_multiplier = 1.0
        
        conservative_risk = base_risk * quality_multiplier * loss_multiplier * progress_multiplier
        
        return max(self.config['min_risk_per_trade'], 
                  min(self.config['max_risk_per_trade'], conservative_risk))
    
    def generate_conservative_signal(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Genera señal conservadora con múltiples filtros
        """
        # Verificar límites básicos
        if self.daily_trades >= self.config['max_daily_trades']:
            return {'action': 'MANTENER', 'reason': 'Daily trade limit reached'}
        
        if abs(self.daily_pnl) >= self.config['daily_risk_limit']:
            return {'action': 'MANTENER', 'reason': 'Daily risk limit reached'}
        
        # Verificar tiempo entre operaciones
        current_time = df.index[idx] if hasattr(df.index[idx], 'hour') else datetime.now()
        if (self.last_trade_time and 
            (current_time - self.last_trade_time).total_seconds() < self.config['min_time_between_trades'] * 60):
            return {'action': 'MANTENER', 'reason': 'Too soon since last trade'}
        
        current = df.iloc[idx]
        
        # Filtros de volatilidad
        if (current['volatility'] < self.config['min_volatility'] or 
            current['volatility'] > self.config['max_volatility']):
            return {'action': 'MANTENER', 'reason': 'Volatility outside acceptable range'}
        
        # Calcular calidad de señal
        signal_analysis = self.calculate_signal_quality(df, idx)
        
        if signal_analysis['signal'] == 'MANTENER':
            return {
                'action': 'MANTENER', 
                'reason': f"Insufficient signal quality (score: {signal_analysis['quality_score']})"
            }
        
        # Verificar confirmaciones adicionales
        if self.config['require_multiple_timeframe']:
            if not current['trend_alignment']:
                return {'action': 'MANTENER', 'reason': 'No multi-timeframe alignment'}
        
        if self.config['require_momentum_confirmation']:
            if abs(current['momentum_strength']) < 0.4:
                return {'action': 'MANTENER', 'reason': 'Insufficient momentum confirmation'}
        
        # Calcular parámetros de la operación
        price = current['close']
        atr = current['atr']
        risk_per_trade = self.calculate_conservative_risk(signal_analysis['quality_score'])
        
        # Calcular stop loss y take profit conservadores
        if signal_analysis['signal'] == "COMPRAR":
            stop_loss = price - (atr * self.config['stop_loss_atr_multiplier'])
            take_profit = price + (atr * self.config['profit_target_multiplier'])
        else:  # VENDER
            stop_loss = price + (atr * self.config['stop_loss_atr_multiplier'])
            take_profit = price - (atr * self.config['profit_target_multiplier'])
        
        return {
            'action': signal_analysis['signal'],
            'quality_score': signal_analysis['quality_score'],
            'buy_score': signal_analysis['buy_score'],
            'sell_score': signal_analysis['sell_score'],
            'reasons': signal_analysis['reasons'],
            'risk_per_trade': risk_per_trade,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'partial_profit_price': price + (price * self.config['partial_profit_level']) if signal_analysis['signal'] == "COMPRAR" else price - (price * self.config['partial_profit_level']),
            'atr': atr
        }
    
    def should_take_partial_profit(self, current_price: float, direction: str) -> bool:
        """
        Determina si debe tomar ganancia parcial
        """
        if self.partial_profit_taken:
            return False
        
        profit_pct = 0
        if direction == "COMPRAR":
            profit_pct = (current_price - self.entry_price) / self.entry_price
        else:
            profit_pct = (self.entry_price - current_price) / self.entry_price
        
        return profit_pct >= self.config['partial_profit_level']
    
    def update_performance(self, pnl: float, is_win: bool):
        """Actualiza métricas de performance"""
        self.daily_pnl += pnl
        self.daily_trades += 1
        self.monthly_target_progress += pnl
        
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        self.last_trade_time = datetime.now()
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
    
    def reset_monthly_stats(self):
        """Resetea estadísticas mensuales"""
        self.monthly_target_progress = 0.0


class ConservativeBacktester:
    """
    Backtester conservador con gestión de riesgo estricta
    """
    
    def __init__(self, initial_balance: float = 100000.0, commission: float = 0.001):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission = commission
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.partial_profit_price = 0
        self.partial_profit_taken = False
        self.trades = []
        self.balance_history = [initial_balance]
        
    def run_backtest(self, data: pd.DataFrame, strategy: Conservative15PctStrategy) -> Dict[str, Any]:
        """Ejecuta backtest conservador"""
        df = strategy.calculate_comprehensive_indicators(data)
        
        for i in range(len(df)):
            current_data = df.iloc[i]
            
            # Verificar posición existente
            if self.position is not None:
                self._check_exit_conditions(current_data, strategy)
            else:
                # Buscar nueva entrada
                signal_data = strategy.generate_conservative_signal(df, i)
                if signal_data['action'] in ['COMPRAR', 'VENDER']:
                    self._open_position(current_data, signal_data, strategy)
            
            # Actualizar historial
            current_value = self._calculate_portfolio_value(current_data['close'])
            self.balance_history.append(current_value)
        
        # Cerrar posición final
        if self.position is not None:
            self._close_position(df.iloc[-1]['close'], "Final close")
        
        return self._calculate_results()
    
    def _open_position(self, data: pd.Series, signal_data: Dict[str, Any], strategy: Conservative15PctStrategy):
        """Abre nueva posición conservadora"""
        price = data['close']
        direction = signal_data['action']
        risk_per_trade = signal_data['risk_per_trade']
        
        # Calcular tamaño de posición
        risk_amount = self.balance * risk_per_trade
        price_diff = abs(price - signal_data['stop_loss'])
        
        if price_diff > 0:
            position_size = risk_amount / price_diff
            cost = position_size * price * (1 + self.commission)
            
            if cost <= self.balance:
                self.position = direction
                self.position_size = position_size
                self.entry_price = price
                self.stop_loss = signal_data['stop_loss']
                self.take_profit = signal_data['take_profit']
                self.partial_profit_price = signal_data['partial_profit_price']
                self.partial_profit_taken = False
                self.balance -= cost
                
                # Actualizar estrategia
                strategy.position = direction
                strategy.entry_price = price
                strategy.partial_profit_taken = False
                
                # Registrar trade
                trade = {
                    'entry_time': data.name if hasattr(data, 'name') else len(self.trades),
                    'direction': direction,
                    'entry_price': price,
                    'position_size': position_size,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'quality_score': signal_data['quality_score'],
                    'reasons': signal_data['reasons'],
                    'risk_per_trade': risk_per_trade,
                    'status': 'open'
                }
                self.trades.append(trade)
    
    def _check_exit_conditions(self, data: pd.Series, strategy: Conservative15PctStrategy):
        """Verifica condiciones de salida conservadoras"""
        current_price = data['close']
        
        # Verificar ganancia parcial
        if not self.partial_profit_taken and strategy.should_take_partial_profit(current_price, self.position):
            self._take_partial_profit(current_price, strategy)
        
        # Stop loss
        if ((self.position == "COMPRAR" and current_price <= self.stop_loss) or
            (self.position == "VENDER" and current_price >= self.stop_loss)):
            self._close_position(current_price, "Stop Loss")
            return
        
        # Take profit
        if ((self.position == "COMPRAR" and current_price >= self.take_profit) or
            (self.position == "VENDER" and current_price <= self.take_profit)):
            self._close_position(current_price, "Take Profit")
            return
    
    def _take_partial_profit(self, current_price: float, strategy: Conservative15PctStrategy):
        """Toma ganancia parcial"""
        partial_size = self.position_size * strategy.config['partial_profit_percentage']
        
        # Calcular P&L parcial
        if self.position == "COMPRAR":
            partial_pnl = (current_price - self.entry_price) * partial_size
        else:
            partial_pnl = (self.entry_price - current_price) * partial_size
        
        # Aplicar comisión
        commission_cost = current_price * partial_size * self.commission
        partial_pnl -= commission_cost
        
        # Actualizar balance y posición
        proceeds = current_price * partial_size * (1 - self.commission)
        self.balance += proceeds
        self.position_size -= partial_size
        
        # Mover stop loss a breakeven
        self.stop_loss = self.entry_price
        
        self.partial_profit_taken = True
        strategy.partial_profit_taken = True
        
        # Actualizar trade
        if self.trades:
            self.trades[-1]['partial_profit_taken'] = True
            self.trades[-1]['partial_pnl'] = partial_pnl
    
    def _close_position(self, exit_price: float, reason: str):
        """Cierra posición"""
        if self.position is None:
            return
        
        # Calcular P&L
        if self.position == "COMPRAR":
            pnl = (exit_price - self.entry_price) * self.position_size
        else:
            pnl = (self.entry_price - exit_price) * self.position_size
        
        # Aplicar comisión
        commission_cost = exit_price * self.position_size * self.commission
        pnl -= commission_cost
        
        # Actualizar balance
        proceeds = exit_price * self.position_size * (1 - self.commission)
        self.balance += proceeds
        
        # Actualizar trade
        if self.trades:
            total_pnl = pnl + self.trades[-1].get('partial_pnl', 0)
            self.trades[-1].update({
                'exit_price': exit_price,
                'exit_reason': reason,
                'pnl': total_pnl,
                'pnl_pct': (total_pnl / (self.entry_price * (self.trades[-1]['position_size']))) * 100,
                'status': 'closed'
            })
        
        # Reset position
        self.position = None
        self.position_size = 0
        self.partial_profit_taken = False
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """Calcula valor del portfolio"""
        if self.position is None:
            return self.balance
        return self.balance + (self.position_size * current_price)
    
    def _calculate_results(self) -> Dict[str, Any]:
        """Calcula resultados finales"""
        final_balance = self.balance_history[-1]
        total_return = (final_balance / self.initial_balance - 1) * 100
        
        closed_trades = [t for t in self.trades if t.get('status') == 'closed']
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        # Métricas avanzadas
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calcular drawdown
        peak = self.initial_balance
        max_drawdown = 0
        drawdown_periods = 0
        current_drawdown_periods = 0
        
        for balance in self.balance_history:
            if balance > peak:
                peak = balance
                current_drawdown_periods = 0
            else:
                current_drawdown_periods += 1
                drawdown_periods = max(drawdown_periods, current_drawdown_periods)
            
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Retorno mensual
        days_simulated = len(self.balance_history) / (24 * 4)  # 15min intervals
        monthly_return = (total_return / days_simulated) * 30 if days_simulated > 0 else 0
        
        # Estadísticas de calidad
        avg_quality_score = np.mean([t.get('quality_score', 0) for t in closed_trades]) if closed_trades else 0
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_return_pct': total_return,
            'monthly_return_pct': monthly_return,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_drawdown_pct': max_drawdown,
            'max_drawdown_periods': drawdown_periods,
            'avg_quality_score': avg_quality_score,
            'target_achieved': monthly_return >= 20.0,
            'balance_history': self.balance_history,
            'trades': self.trades
        }


def generate_conservative_data(days: int = 120, initial_price: float = 18000) -> pd.DataFrame:
    """
    Genera datos para testing conservador
    """
    np.random.seed(789)  # Seed específico para consistencia
    periods_per_day = 24 * 4  # 15 min intervals
    total_periods = days * periods_per_day
    
    dates = pd.date_range(start='2024-01-01', periods=total_periods, freq='15min')
    
    # Generar retornos más estables
    base_volatility = 0.0035
    returns = np.random.normal(0, base_volatility, total_periods)
    
    # Añadir tendencias suaves
    trend_cycle = np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 25)) * 0.0015
    volatility_cycle = 1 + 0.3 * np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 7))
    
    # Añadir algunos breakouts controlados
    breakout_probability = 0.015
    breakouts = np.random.choice([0, 1], total_periods, p=[1-breakout_probability, breakout_probability])
    breakout_magnitude = np.random.choice([-1, 1], total_periods) * 0.008
    
    returns = returns * volatility_cycle + trend_cycle + (breakouts * breakout_magnitude)
    
    # Generar precios
    prices = initial_price * (1 + returns).cumprod()
    
    # Crear OHLC
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'close': prices,
        'volume': np.random.randint(10000, 100000, total_periods)
    })
    
    # Generar high/low
    for i in range(len(df)):
        volatility = abs(returns[i]) * 2.5
        df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + volatility)
        df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - volatility)
        
        # Ajustar close
        df.loc[i, 'close'] = np.clip(df.loc[i, 'close'], 
                                    df.loc[i, 'low'], 
                                    df.loc[i, 'high'])
    
    df.set_index('timestamp', inplace=True)
    return df


def run_conservative_strategy_test():
    """
    Ejecuta test de la estrategia conservadora
    """
    print("🛡️ Iniciando test de Estrategia Conservadora 20% Mensual")
    print("=" * 60)
    
    # Generar datos
    data = generate_conservative_data(days=150)  # 5 meses
    print(f"📊 Datos generados: {len(data)} períodos")
    
    # Crear estrategia
    strategy = Conservative15PctStrategy()
    print("⚙️ Estrategia conservadora configurada")
    
    # Ejecutar backtest
    backtester = ConservativeBacktester(initial_balance=100000.0)
    results = backtester.run_backtest(data, strategy)
    
    # Mostrar resultados
    print("\n📈 RESULTADOS DEL BACKTEST CONSERVADOR")
    print("=" * 45)
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return_pct']:.2f}%")
    print(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%")
    print(f"\n🎯 OBJETIVO 20% MENSUAL: {'✅ ALCANZADO' if results['target_achieved'] else '❌ NO ALCANZADO'}")
    
    print(f"\n📊 ESTADÍSTICAS CONSERVADORAS")
    print(f"Total de operaciones: {results['total_trades']}")
    print(f"Operaciones ganadoras: {results['winning_trades']}")
    print(f"Operaciones perdedoras: {results['losing_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Períodos en Drawdown: {results['max_drawdown_periods']}")
    print(f"Calidad promedio de señales: {results['avg_quality_score']:.1f}")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conservative_15pct_results_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS ESTRATEGIA CONSERVADORA 20% MENSUAL\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Balance inicial: ${results['initial_balance']:,.2f}\n")
        f.write(f"Balance final: ${results['final_balance']:,.2f}\n")
        f.write(f"Retorno total: {results['total_return_pct']:.2f}%\n")
        f.write(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%\n")
        f.write(f"Objetivo 20% mensual: {'ALCANZADO' if results['target_achieved'] else 'NO ALCANZADO'}\n\n")
        
        f.write("ESTADÍSTICAS CONSERVADORAS:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total de operaciones: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
        f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")
        f.write(f"Ganancia bruta: ${results['gross_profit']:.2f}\n")
        f.write(f"Pérdida bruta: ${results['gross_loss']:.2f}\n")
        f.write(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%\n")
        f.write(f"Períodos en Drawdown: {results['max_drawdown_periods']}\n")
        f.write(f"Calidad promedio de señales: {results['avg_quality_score']:.1f}\n\n")
        
        f.write("CARACTERÍSTICAS CONSERVADORAS:\n")
        f.write("-" * 35 + "\n")
        f.write("- Gestión de riesgo ultra-conservadora\n")
        f.write("- Filtros de calidad estrictos (score ≥ 7)\n")
        f.write("- Confirmación multi-timeframe obligatoria\n")
        f.write("- Toma de ganancias parciales automática\n")
        f.write("- Máximo 6 operaciones por día\n")
        f.write("- Stop loss en breakeven después de ganancia parcial\n")
        f.write("- Análisis de divergencias\n")
        f.write("- Confirmación de volumen requerida\n")
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    # Mostrar operaciones de ejemplo
    if results['trades']:
        print("\n📋 ÚLTIMAS 5 OPERACIONES:")
        print("-" * 50)
        for trade in results['trades'][-5:]:
            if trade.get('status') == 'closed':
                direction = trade['direction']
                pnl_pct = trade.get('pnl_pct', 0)
                quality = trade.get('quality_score', 0)
                reason = trade.get('exit_reason', 'Unknown')
                partial = " (Parcial)" if trade.get('partial_profit_taken', False) else ""
                print(f"{direction}: {pnl_pct:+.2f}% (Q:{quality}) - {reason}{partial}")
    
    return results


if __name__ == "__main__":
    results = run_conservative_strategy_test()