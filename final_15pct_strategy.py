#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Estrategia Final 15% Mensual
Versión balanceada que combina lo mejor de todas las estrategias anteriores
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class Final15PctStrategy:
    """
    Estrategia final optimizada para alcanzar consistentemente 15% mensual
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            # Gestión de riesgo balanceada
            'base_risk_per_trade': 0.035,  # 3.5% por operación
            'max_risk_per_trade': 0.055,   # 5.5% máximo
            'min_risk_per_trade': 0.02,    # 2% mínimo
            'daily_risk_limit': 0.15,      # 15% diario
            'max_daily_trades': 8,
            
            # Parámetros técnicos balanceados
            'rsi_period': 12,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_fast': 10,
            'macd_slow': 22,
            'macd_signal': 8,
            'bb_period': 18,
            'bb_std': 1.9,
            'atr_period': 12,
            
            # Filtros de entrada balanceados
            'min_signal_strength': 5,      # Balanceado
            'trend_confirmation_required': True,
            'min_volatility': 0.0025,
            'max_volatility': 0.045,
            
            # Targets optimizados
            'profit_target_multiplier': 2.5,  # 2.5:1 reward/risk
            'stop_loss_atr_multiplier': 0.9,
            'trailing_stop_activation': 0.01,   # 1%
            'trailing_stop_distance': 0.006,   # 0.6%
            
            # Gestión de posiciones
            'scale_out_level_1': 0.008,     # 0.8% - primera toma de ganancias
            'scale_out_percentage_1': 0.3,  # 30% de la posición
            'scale_out_level_2': 0.015,     # 1.5% - segunda toma de ganancias
            'scale_out_percentage_2': 0.4,  # 40% de la posición restante
            
            # Filtros adicionales
            'momentum_threshold': 0.002,
            'volume_spike_threshold': 1.5,
            'max_consecutive_losses': 3,
        }
        
        self.position = None
        self.position_size = 0
        self.original_position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_stop = 0
        self.scale_out_1_done = False
        self.scale_out_2_done = False
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.monthly_pnl = 0.0
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos balanceados
        """
        df = data.copy()
        
        # RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.config['rsi_period'])
        df['rsi_ma'] = df['rsi'].rolling(3).mean()
        
        # MACD
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        df['macd_slope'] = df['macd'].diff()
        
        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_width'] = (bb_data['upper'] - bb_data['lower']) / bb_data['middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # EMAs
        df['ema_8'] = df['close'].ewm(span=8).mean()
        df['ema_13'] = df['close'].ewm(span=13).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_34'] = df['close'].ewm(span=34).mean()
        
        # Trend analysis
        df['trend_short'] = np.where(df['ema_8'] > df['ema_13'], 1, 
                                   np.where(df['ema_8'] < df['ema_13'], -1, 0))
        df['trend_medium'] = np.where(df['ema_13'] > df['ema_21'], 1, 
                                    np.where(df['ema_13'] < df['ema_21'], -1, 0))
        df['trend_alignment'] = df['trend_short'] == df['trend_medium']
        
        # ATR y volatilidad
        df['atr'] = self._calculate_atr(df)
        df['volatility'] = df['close'].rolling(15).std() / df['close'].rolling(15).mean()
        
        # Momentum
        df['momentum_3'] = df['close'].pct_change(3)
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_8'] = df['close'].pct_change(8)
        
        # Support/Resistance
        df['support'] = df['low'].rolling(20).min()
        df['resistance'] = df['high'].rolling(20).max()
        df['near_support'] = (df['close'] - df['support']) / df['close'] < 0.01
        df['near_resistance'] = (df['resistance'] - df['close']) / df['close'] < 0.01
        
        # Volume analysis
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            df['volume_spike'] = df['volume_ratio'] > self.config['volume_spike_threshold']
        else:
            df['volume_ratio'] = 1.0
            df['volume_spike'] = False
        
        # Breakout detection
        df['price_breakout_up'] = (df['close'] > df['resistance'].shift(1)) & (df['close'].shift(1) <= df['resistance'].shift(1))
        df['price_breakout_down'] = (df['close'] < df['support'].shift(1)) & (df['close'].shift(1) >= df['support'].shift(1))
        
        # Candlestick patterns
        df['body_size'] = abs(df['close'] - df['open']) / (df['high'] - df['low'])
        df['bullish_candle'] = df['close'] > df['open']
        df['bearish_candle'] = df['close'] < df['open']
        
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
    
    def calculate_signal_strength(self, df: pd.DataFrame, idx: int) -> Tuple[int, int, str]:
        """
        Calcula fuerza de señales balanceada
        """
        if idx < 40:
            return 0, 0, "MANTENER"
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        prev2 = df.iloc[idx - 2]
        
        buy_signals = 0
        sell_signals = 0
        
        # RSI signals (peso: 2)
        if current['rsi'] < self.config['rsi_oversold'] and current['rsi'] > prev['rsi']:
            buy_signals += 2
        elif current['rsi'] > self.config['rsi_overbought'] and current['rsi'] < prev['rsi']:
            sell_signals += 2
        
        # MACD signals (peso: 3)
        if prev['macd'] <= prev['macd_signal'] and current['macd'] > current['macd_signal']:
            buy_signals += 3
        elif prev['macd'] >= prev['macd_signal'] and current['macd'] < current['macd_signal']:
            sell_signals += 3
        
        # MACD momentum
        if current['macd_slope'] > 0 and current['macd_histogram'] > 0:
            buy_signals += 1
        elif current['macd_slope'] < 0 and current['macd_histogram'] < 0:
            sell_signals += 1
        
        # Bollinger Bands (peso: 2)
        if current['bb_position'] < 0.25 and current['close'] > prev['close']:
            buy_signals += 2
        elif current['bb_position'] > 0.75 and current['close'] < prev['close']:
            sell_signals += 2
        
        # Trend alignment (peso: 2)
        if current['trend_alignment'] and current['trend_short'] == 1:
            buy_signals += 2
        elif current['trend_alignment'] and current['trend_short'] == -1:
            sell_signals += 2
        
        # EMA crossover (peso: 2)
        if prev['ema_8'] <= prev['ema_13'] and current['ema_8'] > current['ema_13']:
            buy_signals += 2
        elif prev['ema_8'] >= prev['ema_13'] and current['ema_8'] < current['ema_13']:
            sell_signals += 2
        
        # Momentum (peso: 1)
        if current['momentum_5'] > self.config['momentum_threshold']:
            buy_signals += 1
        elif current['momentum_5'] < -self.config['momentum_threshold']:
            sell_signals += 1
        
        # Breakouts (peso: 3)
        if current['price_breakout_up']:
            buy_signals += 3
        elif current['price_breakout_down']:
            sell_signals += 3
        
        # Support/Resistance (peso: 1)
        if current['near_support']:
            buy_signals += 1
        elif current['near_resistance']:
            sell_signals += 1
        
        # Volume confirmation (peso: 1)
        if current['volume_spike']:
            if buy_signals > sell_signals:
                buy_signals += 1
            elif sell_signals > buy_signals:
                sell_signals += 1
        
        # Candlestick confirmation (peso: 1)
        if current['bullish_candle'] and current['body_size'] > 0.3:
            buy_signals += 1
        elif current['bearish_candle'] and current['body_size'] > 0.3:
            sell_signals += 1
        
        # Determinar señal
        if buy_signals >= self.config['min_signal_strength'] and buy_signals > sell_signals + 1:
            return buy_signals, sell_signals, "COMPRAR"
        elif sell_signals >= self.config['min_signal_strength'] and sell_signals > buy_signals + 1:
            return buy_signals, sell_signals, "VENDER"
        else:
            return buy_signals, sell_signals, "MANTENER"
    
    def calculate_dynamic_risk(self, signal_strength: int) -> float:
        """
        Calcula riesgo dinámico
        """
        base_risk = self.config['base_risk_per_trade']
        
        # Ajustar por fuerza de señal
        signal_multiplier = min(1.4, 1.0 + (signal_strength - self.config['min_signal_strength']) * 0.08)
        
        # Ajustar por pérdidas consecutivas
        if self.consecutive_losses >= self.config['max_consecutive_losses']:
            loss_multiplier = 0.5
        elif self.consecutive_losses >= 2:
            loss_multiplier = 0.7
        elif self.consecutive_losses >= 1:
            loss_multiplier = 0.85
        else:
            loss_multiplier = 1.0
        
        # Ajustar por progreso mensual
        if self.monthly_pnl >= 0.12:  # Si ya tenemos 12% este mes
            progress_multiplier = 0.7
        elif self.monthly_pnl >= 0.08:  # 8%
            progress_multiplier = 0.85
        elif self.monthly_pnl < 0.03:  # Menos de 3%
            progress_multiplier = 1.15
        else:
            progress_multiplier = 1.0
        
        # Ajustar por performance diaria
        if self.daily_pnl > 0.06:  # Si ya ganamos 6% hoy
            daily_multiplier = 0.8
        elif self.daily_pnl < -0.03:  # Si perdimos 3%
            daily_multiplier = 0.7
        else:
            daily_multiplier = 1.0
        
        dynamic_risk = base_risk * signal_multiplier * loss_multiplier * progress_multiplier * daily_multiplier
        
        return max(self.config['min_risk_per_trade'], 
                  min(self.config['max_risk_per_trade'], dynamic_risk))
    
    def generate_signal(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Genera señal balanceada
        """
        # Verificar límites
        if self.daily_trades >= self.config['max_daily_trades']:
            return {'action': 'MANTENER', 'reason': 'Daily trade limit'}
        
        if abs(self.daily_pnl) >= self.config['daily_risk_limit']:
            return {'action': 'MANTENER', 'reason': 'Daily risk limit'}
        
        current = df.iloc[idx]
        
        # Filtro de volatilidad
        if (current['volatility'] < self.config['min_volatility'] or 
            current['volatility'] > self.config['max_volatility']):
            return {'action': 'MANTENER', 'reason': 'Volatility filter'}
        
        # Calcular señales
        buy_strength, sell_strength, signal = self.calculate_signal_strength(df, idx)
        
        if signal == "MANTENER":
            return {'action': 'MANTENER', 'reason': 'Insufficient signal strength'}
        
        # Verificar confirmación de tendencia si es requerida
        if self.config['trend_confirmation_required'] and not current['trend_alignment']:
            return {'action': 'MANTENER', 'reason': 'No trend confirmation'}
        
        # Calcular parámetros
        price = current['close']
        atr = current['atr']
        risk_per_trade = self.calculate_dynamic_risk(max(buy_strength, sell_strength))
        
        # Calcular stop loss y take profit
        if signal == "COMPRAR":
            stop_loss = price - (atr * self.config['stop_loss_atr_multiplier'])
            take_profit = price + (atr * self.config['profit_target_multiplier'])
        else:  # VENDER
            stop_loss = price + (atr * self.config['stop_loss_atr_multiplier'])
            take_profit = price - (atr * self.config['profit_target_multiplier'])
        
        return {
            'action': signal,
            'buy_strength': buy_strength,
            'sell_strength': sell_strength,
            'risk_per_trade': risk_per_trade,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'atr': atr,
            'reason': f'Signal strength: {max(buy_strength, sell_strength)}'
        }
    
    def update_trailing_stop(self, current_price: float, direction: str):
        """Actualiza trailing stop"""
        if direction == "COMPRAR":
            profit = (current_price - self.entry_price) / self.entry_price
            if profit >= self.config['trailing_stop_activation']:
                new_trailing = current_price - (current_price * self.config['trailing_stop_distance'])
                self.trailing_stop = max(self.trailing_stop, new_trailing)
        else:  # VENDER
            profit = (self.entry_price - current_price) / self.entry_price
            if profit >= self.config['trailing_stop_activation']:
                new_trailing = current_price + (current_price * self.config['trailing_stop_distance'])
                if self.trailing_stop == 0:
                    self.trailing_stop = new_trailing
                else:
                    self.trailing_stop = min(self.trailing_stop, new_trailing)
    
    def should_scale_out(self, current_price: float, direction: str) -> Tuple[bool, float, int]:
        """Determina si debe hacer scale out"""
        profit_pct = 0
        if direction == "COMPRAR":
            profit_pct = (current_price - self.entry_price) / self.entry_price
        else:
            profit_pct = (self.entry_price - current_price) / self.entry_price
        
        # Primera toma de ganancias
        if not self.scale_out_1_done and profit_pct >= self.config['scale_out_level_1']:
            return True, self.config['scale_out_percentage_1'], 1
        
        # Segunda toma de ganancias
        if not self.scale_out_2_done and profit_pct >= self.config['scale_out_level_2']:
            return True, self.config['scale_out_percentage_2'], 2
        
        return False, 0, 0
    
    def should_exit_position(self, current_price: float, direction: str) -> Tuple[bool, str]:
        """Determina si debe salir de la posición"""
        # Stop loss
        if direction == "COMPRAR" and current_price <= self.stop_loss:
            return True, "Stop Loss"
        elif direction == "VENDER" and current_price >= self.stop_loss:
            return True, "Stop Loss"
        
        # Take profit
        if direction == "COMPRAR" and current_price >= self.take_profit:
            return True, "Take Profit"
        elif direction == "VENDER" and current_price <= self.take_profit:
            return True, "Take Profit"
        
        # Trailing stop
        if self.trailing_stop > 0:
            if direction == "COMPRAR" and current_price <= self.trailing_stop:
                return True, "Trailing Stop"
            elif direction == "VENDER" and current_price >= self.trailing_stop:
                return True, "Trailing Stop"
        
        return False, ""
    
    def update_performance(self, pnl: float, is_win: bool):
        """Actualiza métricas de performance"""
        self.daily_pnl += pnl
        self.monthly_pnl += pnl
        self.daily_trades += 1
        
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
    
    def reset_monthly_stats(self):
        """Resetea estadísticas mensuales"""
        self.monthly_pnl = 0.0


class FinalBacktester:
    """
    Backtester final con gestión avanzada de posiciones
    """
    
    def __init__(self, initial_balance: float = 100000.0, commission: float = 0.001):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission = commission
        self.position = None
        self.position_size = 0
        self.original_position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trades = []
        self.balance_history = [initial_balance]
        
    def run_backtest(self, data: pd.DataFrame, strategy: Final15PctStrategy) -> Dict[str, Any]:
        """Ejecuta backtest final"""
        df = strategy.calculate_indicators(data)
        
        for i in range(len(df)):
            current_data = df.iloc[i]
            
            # Verificar posición existente
            if self.position is not None:
                self._check_position_management(current_data, strategy)
            else:
                # Buscar nueva entrada
                signal_data = strategy.generate_signal(df, i)
                if signal_data['action'] in ['COMPRAR', 'VENDER']:
                    self._open_position(current_data, signal_data, strategy)
            
            # Actualizar historial
            current_value = self._calculate_portfolio_value(current_data['close'])
            self.balance_history.append(current_value)
        
        # Cerrar posición final
        if self.position is not None:
            self._close_position(df.iloc[-1]['close'], "Final close")
        
        return self._calculate_results()
    
    def _open_position(self, data: pd.Series, signal_data: Dict[str, Any], strategy: Final15PctStrategy):
        """Abre nueva posición"""
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
                self.original_position_size = position_size
                self.entry_price = price
                self.stop_loss = signal_data['stop_loss']
                self.take_profit = signal_data['take_profit']
                self.balance -= cost
                
                # Actualizar estrategia
                strategy.position = direction
                strategy.position_size = position_size
                strategy.original_position_size = position_size
                strategy.entry_price = price
                strategy.stop_loss = signal_data['stop_loss']
                strategy.take_profit = signal_data['take_profit']
                strategy.trailing_stop = 0
                strategy.scale_out_1_done = False
                strategy.scale_out_2_done = False
                
                # Registrar trade
                trade = {
                    'entry_time': data.name if hasattr(data, 'name') else len(self.trades),
                    'direction': direction,
                    'entry_price': price,
                    'original_position_size': position_size,
                    'current_position_size': position_size,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'buy_strength': signal_data.get('buy_strength', 0),
                    'sell_strength': signal_data.get('sell_strength', 0),
                    'risk_per_trade': risk_per_trade,
                    'scale_outs': [],
                    'status': 'open'
                }
                self.trades.append(trade)
    
    def _check_position_management(self, data: pd.Series, strategy: Final15PctStrategy):
        """Verifica gestión de posición"""
        current_price = data['close']
        
        # Actualizar trailing stop
        strategy.update_trailing_stop(current_price, self.position)
        
        # Verificar scale out
        should_scale, scale_percentage, scale_level = strategy.should_scale_out(current_price, self.position)
        if should_scale:
            self._scale_out_position(current_price, scale_percentage, scale_level, strategy)
        
        # Verificar salida completa
        should_exit, reason = strategy.should_exit_position(current_price, self.position)
        if should_exit:
            self._close_position(current_price, reason)
    
    def _scale_out_position(self, current_price: float, percentage: float, level: int, strategy: Final15PctStrategy):
        """Realiza scale out parcial"""
        scale_size = self.position_size * percentage
        
        # Calcular P&L del scale out
        if self.position == "COMPRAR":
            pnl = (current_price - self.entry_price) * scale_size
        else:
            pnl = (self.entry_price - current_price) * scale_size
        
        # Aplicar comisión
        commission_cost = current_price * scale_size * self.commission
        pnl -= commission_cost
        
        # Actualizar balance y posición
        proceeds = current_price * scale_size * (1 - self.commission)
        self.balance += proceeds
        self.position_size -= scale_size
        strategy.position_size -= scale_size
        
        # Marcar scale out como realizado
        if level == 1:
            strategy.scale_out_1_done = True
            # Mover stop loss a breakeven después del primer scale out
            self.stop_loss = self.entry_price
            strategy.stop_loss = self.entry_price
        elif level == 2:
            strategy.scale_out_2_done = True
        
        # Registrar scale out
        if self.trades:
            self.trades[-1]['scale_outs'].append({
                'level': level,
                'price': current_price,
                'size': scale_size,
                'pnl': pnl,
                'percentage': percentage
            })
            self.trades[-1]['current_position_size'] = self.position_size
    
    def _close_position(self, exit_price: float, reason: str):
        """Cierra posición completamente"""
        if self.position is None:
            return
        
        # Calcular P&L de la posición restante
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
        
        # Calcular P&L total (incluyendo scale outs)
        total_pnl = pnl
        if self.trades:
            scale_out_pnl = sum(so['pnl'] for so in self.trades[-1].get('scale_outs', []))
            total_pnl += scale_out_pnl
            
            self.trades[-1].update({
                'exit_price': exit_price,
                'exit_reason': reason,
                'final_pnl': pnl,
                'total_pnl': total_pnl,
                'total_pnl_pct': (total_pnl / (self.entry_price * self.original_position_size)) * 100,
                'status': 'closed'
            })
        
        # Reset position
        self.position = None
        self.position_size = 0
        self.original_position_size = 0
    
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
        winning_trades = [t for t in closed_trades if t.get('total_pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('total_pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        # Métricas avanzadas
        gross_profit = sum(t['total_pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['total_pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calcular drawdown
        peak = self.initial_balance
        max_drawdown = 0
        for balance in self.balance_history:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Retorno mensual
        days_simulated = len(self.balance_history) / (24 * 4)  # 15min intervals
        monthly_return = (total_return / days_simulated) * 30 if days_simulated > 0 else 0
        
        # Estadísticas de scale out
        trades_with_scale_out = [t for t in closed_trades if t.get('scale_outs', [])]
        avg_scale_outs = np.mean([len(t.get('scale_outs', [])) for t in closed_trades]) if closed_trades else 0
        
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
            'trades_with_scale_out': len(trades_with_scale_out),
            'avg_scale_outs_per_trade': avg_scale_outs,
            'target_achieved': monthly_return >= 15.0,
            'balance_history': self.balance_history,
            'trades': self.trades
        }


def generate_final_data(days: int = 120, initial_price: float = 18000) -> pd.DataFrame:
    """
    Genera datos finales optimizados para testing
    """
    np.random.seed(999)  # Seed final
    periods_per_day = 24 * 4  # 15 min intervals
    total_periods = days * periods_per_day
    
    dates = pd.date_range(start='2024-01-01', periods=total_periods, freq='15min')
    
    # Generar retornos balanceados
    base_volatility = 0.0038
    returns = np.random.normal(0, base_volatility, total_periods)
    
    # Añadir ciclos de mercado realistas
    trend_cycle = np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 22)) * 0.0018
    volatility_cycle = 1 + 0.4 * np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 6))
    
    # Añadir breakouts y reversiones
    breakout_probability = 0.018
    breakouts = np.random.choice([0, 1], total_periods, p=[1-breakout_probability, breakout_probability])
    breakout_magnitude = np.random.choice([-1, 1], total_periods) * 0.009
    
    returns = returns * volatility_cycle + trend_cycle + (breakouts * breakout_magnitude)
    
    # Generar precios
    prices = initial_price * (1 + returns).cumprod()
    
    # Crear OHLC
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'close': prices,
        'volume': np.random.randint(15000, 150000, total_periods)
    })
    
    # Generar high/low
    for i in range(len(df)):
        volatility = abs(returns[i]) * 2.2
        df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + volatility)
        df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - volatility)
        
        # Ajustar close
        df.loc[i, 'close'] = np.clip(df.loc[i, 'close'], 
                                    df.loc[i, 'low'], 
                                    df.loc[i, 'high'])
    
    df.set_index('timestamp', inplace=True)
    return df


def run_final_strategy_test():
    """
    Ejecuta test de la estrategia final
    """
    print("🏆 Iniciando test de Estrategia Final 15% Mensual")
    print("=" * 60)
    
    # Generar datos
    data = generate_final_data(days=120)  # 4 meses
    print(f"📊 Datos generados: {len(data)} períodos")
    
    # Crear estrategia
    strategy = Final15PctStrategy()
    print("⚙️ Estrategia final configurada")
    
    # Ejecutar backtest
    backtester = FinalBacktester(initial_balance=100000.0)
    results = backtester.run_backtest(data, strategy)
    
    # Mostrar resultados
    print("\n📈 RESULTADOS DEL BACKTEST FINAL")
    print("=" * 40)
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return_pct']:.2f}%")
    print(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%")
    print(f"\n🎯 OBJETIVO 15% MENSUAL: {'✅ ALCANZADO' if results['target_achieved'] else '❌ NO ALCANZADO'}")
    
    print(f"\n📊 ESTADÍSTICAS FINALES")
    print(f"Total de operaciones: {results['total_trades']}")
    print(f"Operaciones ganadoras: {results['winning_trades']}")
    print(f"Operaciones perdedoras: {results['losing_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Operaciones con scale out: {results['trades_with_scale_out']}")
    print(f"Scale outs promedio por trade: {results['avg_scale_outs_per_trade']:.1f}")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"final_15pct_results_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS ESTRATEGIA FINAL 15% MENSUAL\n")
        f.write("=" * 45 + "\n\n")
        f.write(f"Balance inicial: ${results['initial_balance']:,.2f}\n")
        f.write(f"Balance final: ${results['final_balance']:,.2f}\n")
        f.write(f"Retorno total: {results['total_return_pct']:.2f}%\n")
        f.write(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%\n")
        f.write(f"Objetivo 15% mensual: {'ALCANZADO' if results['target_achieved'] else 'NO ALCANZADO'}\n\n")
        
        f.write("ESTADÍSTICAS FINALES:\n")
        f.write("-" * 25 + "\n")
        f.write(f"Total de operaciones: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
        f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")
        f.write(f"Ganancia bruta: ${results['gross_profit']:.2f}\n")
        f.write(f"Pérdida bruta: ${results['gross_loss']:.2f}\n")
        f.write(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%\n")
        f.write(f"Operaciones con scale out: {results['trades_with_scale_out']}\n")
        f.write(f"Scale outs promedio: {results['avg_scale_outs_per_trade']:.1f}\n\n")
        
        f.write("CARACTERÍSTICAS FINALES:\n")
        f.write("-" * 25 + "\n")
        f.write("- Gestión de riesgo dinámica y adaptativa\n")
        f.write("- Múltiples indicadores técnicos balanceados\n")
        f.write("- Sistema de scale out en 2 niveles\n")
        f.write("- Trailing stop automático\n")
        f.write("- Confirmación de tendencia\n")
        f.write("- Filtros de volatilidad y volumen\n")
        f.write("- Detección de breakouts\n")
        f.write("- Stop loss en breakeven después del primer scale out\n")
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    # Mostrar operaciones de ejemplo
    if results['trades']:
        print("\n📋 ÚLTIMAS 5 OPERACIONES:")
        print("-" * 60)
        for trade in results['trades'][-5:]:
            if trade.get('status') == 'closed':
                direction = trade['direction']
                total_pnl_pct = trade.get('total_pnl_pct', 0)
                reason = trade.get('exit_reason', 'Unknown')
                scale_outs = len(trade.get('scale_outs', []))
                scale_info = f" ({scale_outs} scale-outs)" if scale_outs > 0 else ""
                print(f"{direction}: {total_pnl_pct:+.2f}% - {reason}{scale_info}")
    
    return results


if __name__ == "__main__":
    results = run_final_strategy_test()