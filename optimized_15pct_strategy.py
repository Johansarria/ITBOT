#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Estrategia Optimizada 20% Mensual
Versión balanceada entre agresividad y control de riesgo
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class Optimized15PctStrategy:
    """
    Estrategia optimizada para alcanzar 20% mensual con riesgo controlado
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            # Gestión de riesgo optimizada
            'base_risk_per_trade': 0.04,  # 4% por operación
            'max_risk_per_trade': 0.07,   # 7% máximo
            'min_risk_per_trade': 0.02,   # 2% mínimo
            'daily_risk_limit': 0.20,     # 20% diario
            'max_daily_trades': 12,
            
            # Parámetros técnicos optimizados
            'rsi_period': 10,
            'rsi_oversold': 35,
            'rsi_overbought': 65,
            'macd_fast': 8,
            'macd_slow': 21,
            'macd_signal': 7,
            'bb_period': 18,
            'bb_std': 1.8,
            'atr_period': 12,
            
            # Filtros de entrada más permisivos
            'min_signal_strength': 4,  # Reducido de 6
            'trend_strength_threshold': 0.4,  # Reducido de 0.6
            'min_volatility': 0.002,  # Reducido
            'max_volatility': 0.06,   # Aumentado
            
            # Targets más agresivos
            'profit_target_multiplier': 2.0,  # 2:1 reward/risk
            'stop_loss_atr_multiplier': 1.0,
            'trailing_stop_activation': 0.015,  # 1.5%
            'trailing_stop_distance': 0.008,   # 0.8%
            
            # Momentum trading
            'momentum_threshold': 0.003,  # 0.3%
            'breakout_threshold': 0.005,  # 0.5%
            'volume_confirmation': False,  # Desactivado para más señales
        }
        
        self.position = None
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_stop = 0
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.last_signal_time = None
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos optimizados
        """
        df = data.copy()
        
        # RSI optimizado
        df['rsi'] = self._calculate_rsi(df['close'], self.config['rsi_period'])
        df['rsi_ma'] = df['rsi'].rolling(3).mean()  # RSI suavizado
        
        # MACD optimizado
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        df['macd_momentum'] = df['macd_histogram'].diff()
        
        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_width'] = (bb_data['upper'] - bb_data['lower']) / bb_data['middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # EMAs múltiples
        df['ema_8'] = df['close'].ewm(span=8).mean()
        df['ema_13'] = df['close'].ewm(span=13).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_34'] = df['close'].ewm(span=34).mean()
        
        # ATR y volatilidad
        df['atr'] = self._calculate_atr(df)
        df['volatility'] = df['close'].rolling(10).std() / df['close'].rolling(10).mean()
        
        # Momentum indicators
        df['price_momentum_3'] = df['close'].pct_change(3)
        df['price_momentum_5'] = df['close'].pct_change(5)
        df['price_momentum_8'] = df['close'].pct_change(8)
        
        # Trend indicators
        df['trend_ema'] = np.where(df['ema_8'] > df['ema_21'], 1, 
                                  np.where(df['ema_8'] < df['ema_21'], -1, 0))
        df['trend_strength'] = abs(df['ema_8'] - df['ema_21']) / df['ema_21']
        
        # Support/Resistance dinámicos
        df['support'] = df['low'].rolling(15).min()
        df['resistance'] = df['high'].rolling(15).max()
        df['support_strength'] = (df['close'] - df['support']) / df['close']
        df['resistance_strength'] = (df['resistance'] - df['close']) / df['close']
        
        # Breakout detection
        df['breakout_up'] = (df['close'] > df['resistance'].shift(1)) & (df['close'].shift(1) <= df['resistance'].shift(1))
        df['breakout_down'] = (df['close'] < df['support'].shift(1)) & (df['close'].shift(1) >= df['support'].shift(1))
        
        # Volume analysis (si está disponible)
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            df['volume_momentum'] = df['volume'].pct_change(3)
        else:
            df['volume_ratio'] = 1.0
            df['volume_momentum'] = 0.0
        
        # Candlestick patterns
        df['body_size'] = abs(df['close'] - df['open']) / (df['high'] - df['low'])
        df['upper_shadow'] = (df['high'] - np.maximum(df['open'], df['close'])) / (df['high'] - df['low'])
        df['lower_shadow'] = (np.minimum(df['open'], df['close']) - df['low']) / (df['high'] - df['low'])
        
        # Doji pattern
        df['doji'] = df['body_size'] < 0.1
        
        # Hammer/Shooting star
        df['hammer'] = (df['lower_shadow'] > 0.6) & (df['upper_shadow'] < 0.1) & (df['body_size'] < 0.3)
        df['shooting_star'] = (df['upper_shadow'] > 0.6) & (df['lower_shadow'] < 0.1) & (df['body_size'] < 0.3)
        
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
        Calcula fuerza de señales de compra y venta
        """
        if idx < 30:
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
        
        # RSI momentum
        if current['rsi'] > prev['rsi'] > prev2['rsi'] and current['rsi'] < 50:
            buy_signals += 1
        elif current['rsi'] < prev['rsi'] < prev2['rsi'] and current['rsi'] > 50:
            sell_signals += 1
        
        # MACD signals (peso: 3)
        if prev['macd'] <= prev['macd_signal'] and current['macd'] > current['macd_signal']:
            buy_signals += 3
        elif prev['macd'] >= prev['macd_signal'] and current['macd'] < current['macd_signal']:
            sell_signals += 3
        
        # MACD momentum
        if current['macd_momentum'] > 0 and current['macd_histogram'] > 0:
            buy_signals += 1
        elif current['macd_momentum'] < 0 and current['macd_histogram'] < 0:
            sell_signals += 1
        
        # Bollinger Bands (peso: 2)
        if current['bb_position'] < 0.2 and current['close'] > prev['close']:
            buy_signals += 2
        elif current['bb_position'] > 0.8 and current['close'] < prev['close']:
            sell_signals += 2
        
        # BB squeeze breakout
        if prev['bb_width'] < df['bb_width'].rolling(20).mean().iloc[idx] * 0.8:
            if current['close'] > current['bb_middle'] and current['close'] > prev['close']:
                buy_signals += 2
            elif current['close'] < current['bb_middle'] and current['close'] < prev['close']:
                sell_signals += 2
        
        # EMA trend (peso: 2)
        if current['ema_8'] > current['ema_13'] > current['ema_21']:
            buy_signals += 2
        elif current['ema_8'] < current['ema_13'] < current['ema_21']:
            sell_signals += 2
        
        # EMA crossover
        if prev['ema_8'] <= prev['ema_13'] and current['ema_8'] > current['ema_13']:
            buy_signals += 2
        elif prev['ema_8'] >= prev['ema_13'] and current['ema_8'] < current['ema_13']:
            sell_signals += 2
        
        # Price momentum (peso: 1)
        if current['price_momentum_5'] > self.config['momentum_threshold']:
            buy_signals += 1
        elif current['price_momentum_5'] < -self.config['momentum_threshold']:
            sell_signals += 1
        
        # Breakout signals (peso: 3)
        if current['breakout_up']:
            buy_signals += 3
        elif current['breakout_down']:
            sell_signals += 3
        
        # Support/Resistance (peso: 1)
        if current['support_strength'] < 0.01:  # Near support
            buy_signals += 1
        elif current['resistance_strength'] < 0.01:  # Near resistance
            sell_signals += 1
        
        # Candlestick patterns (peso: 1)
        if current['hammer'] and current['close'] > current['open']:
            buy_signals += 1
        elif current['shooting_star'] and current['close'] < current['open']:
            sell_signals += 1
        
        # Volume confirmation (si está disponible)
        if self.config['volume_confirmation'] and 'volume' in df.columns:
            if current['volume_ratio'] > 1.2:  # Volume alto
                if buy_signals > sell_signals:
                    buy_signals += 1
                elif sell_signals > buy_signals:
                    sell_signals += 1
        
        # Determinar señal final
        if buy_signals >= self.config['min_signal_strength'] and buy_signals > sell_signals + 1:
            return buy_signals, sell_signals, "COMPRAR"
        elif sell_signals >= self.config['min_signal_strength'] and sell_signals > buy_signals + 1:
            return buy_signals, sell_signals, "VENDER"
        else:
            return buy_signals, sell_signals, "MANTENER"
    
    def calculate_dynamic_risk(self, signal_strength: int) -> float:
        """
        Calcula riesgo dinámico basado en fuerza de señal y performance
        """
        base_risk = self.config['base_risk_per_trade']
        
        # Ajustar por fuerza de señal
        signal_multiplier = min(1.5, 1.0 + (signal_strength - self.config['min_signal_strength']) * 0.1)
        
        # Ajustar por pérdidas consecutivas
        if self.consecutive_losses >= 3:
            loss_multiplier = 0.5
        elif self.consecutive_losses >= 2:
            loss_multiplier = 0.7
        elif self.consecutive_losses >= 1:
            loss_multiplier = 0.85
        else:
            loss_multiplier = 1.0
        
        # Ajustar por performance diaria
        if self.daily_pnl > 0.08:  # Si ya ganamos 8% hoy
            performance_multiplier = 0.8
        elif self.daily_pnl > 0.05:  # Si ganamos 5%
            performance_multiplier = 0.9
        elif self.daily_pnl < -0.05:  # Si perdimos 5%
            performance_multiplier = 0.7
        else:
            performance_multiplier = 1.0
        
        dynamic_risk = base_risk * signal_multiplier * loss_multiplier * performance_multiplier
        
        return max(self.config['min_risk_per_trade'], 
                  min(self.config['max_risk_per_trade'], dynamic_risk))
    
    def generate_signal(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Genera señal de trading optimizada
        """
        # Verificar límites diarios
        if self.daily_trades >= self.config['max_daily_trades']:
            return {'action': 'MANTENER', 'reason': 'Max daily trades'}
        
        if abs(self.daily_pnl) >= self.config['daily_risk_limit']:
            return {'action': 'MANTENER', 'reason': 'Daily risk limit'}
        
        current = df.iloc[idx]
        
        # Filtro de volatilidad
        if (current['volatility'] < self.config['min_volatility'] or 
            current['volatility'] > self.config['max_volatility']):
            return {'action': 'MANTENER', 'reason': 'Volatility filter'}
        
        # Calcular fuerza de señales
        buy_strength, sell_strength, signal = self.calculate_signal_strength(df, idx)
        
        if signal == "MANTENER":
            return {'action': 'MANTENER', 'reason': 'Insufficient signal strength'}
        
        # Calcular parámetros de la operación
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
    
    def update_trailing_stop(self, current_price: float, direction: str) -> float:
        """
        Actualiza trailing stop
        """
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
        
        return self.trailing_stop
    
    def should_exit_position(self, current_price: float, direction: str) -> Tuple[bool, str]:
        """
        Determina si debe salir de la posición
        """
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
        self.daily_trades += 1
        
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0


class OptimizedBacktester:
    """
    Backtester optimizado
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
        self.trades = []
        self.balance_history = [initial_balance]
        
    def run_backtest(self, data: pd.DataFrame, strategy: Optimized15PctStrategy) -> Dict[str, Any]:
        """Ejecuta backtest optimizado"""
        df = strategy.calculate_indicators(data)
        
        for i in range(len(df)):
            current_data = df.iloc[i]
            
            # Verificar posición existente
            if self.position is not None:
                self._check_exit_conditions(current_data, strategy)
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
    
    def _open_position(self, data: pd.Series, signal_data: Dict[str, Any], strategy: Optimized15PctStrategy):
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
                self.entry_price = price
                self.stop_loss = signal_data['stop_loss']
                self.take_profit = signal_data['take_profit']
                self.balance -= cost
                
                # Actualizar estrategia
                strategy.position = direction
                strategy.entry_price = price
                strategy.stop_loss = signal_data['stop_loss']
                strategy.take_profit = signal_data['take_profit']
                strategy.trailing_stop = 0
                
                # Registrar trade
                trade = {
                    'entry_time': data.name if hasattr(data, 'name') else len(self.trades),
                    'direction': direction,
                    'entry_price': price,
                    'position_size': position_size,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'buy_strength': signal_data.get('buy_strength', 0),
                    'sell_strength': signal_data.get('sell_strength', 0),
                    'risk_per_trade': risk_per_trade,
                    'status': 'open'
                }
                self.trades.append(trade)
    
    def _check_exit_conditions(self, data: pd.Series, strategy: Optimized15PctStrategy):
        """Verifica condiciones de salida"""
        current_price = data['close']
        
        # Actualizar trailing stop
        strategy.update_trailing_stop(current_price, self.position)
        
        # Verificar condiciones de salida
        should_exit, reason = strategy.should_exit_position(current_price, self.position)
        
        if should_exit:
            self._close_position(current_price, reason)
    
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
            self.trades[-1].update({
                'exit_price': exit_price,
                'exit_reason': reason,
                'pnl': pnl,
                'pnl_pct': (pnl / (self.entry_price * self.position_size)) * 100,
                'status': 'closed'
            })
        
        # Reset position
        self.position = None
        self.position_size = 0
    
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
        
        # Calcular profit factor
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
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
        
        # Estadísticas adicionales
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0
        
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
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown_pct': max_drawdown,
            'target_achieved': monthly_return >= 20.0,
            'balance_history': self.balance_history,
            'trades': self.trades
        }


def generate_enhanced_data(days: int = 90, initial_price: float = 18000) -> pd.DataFrame:
    """
    Genera datos mejorados con más oportunidades de trading
    """
    np.random.seed(456)  # Nuevo seed
    periods_per_day = 24 * 4  # 15 min intervals
    total_periods = days * periods_per_day
    
    dates = pd.date_range(start='2024-01-01', periods=total_periods, freq='15min')
    
    # Generar retornos con más volatilidad y tendencias
    base_volatility = 0.004
    returns = np.random.normal(0, base_volatility, total_periods)
    
    # Añadir ciclos y tendencias más pronunciadas
    trend_cycle = np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 20)) * 0.002
    volatility_cycle = 1 + 0.8 * np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 5))
    
    # Añadir breakouts ocasionales
    breakout_probability = 0.02
    breakouts = np.random.choice([0, 1], total_periods, p=[1-breakout_probability, breakout_probability])
    breakout_magnitude = np.random.choice([-1, 1], total_periods) * 0.01
    
    returns = returns * volatility_cycle + trend_cycle + (breakouts * breakout_magnitude)
    
    # Generar precios
    prices = initial_price * (1 + returns).cumprod()
    
    # Crear OHLC
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'close': prices,
        'volume': np.random.randint(8000, 80000, total_periods)
    })
    
    # Generar high/low realistas
    for i in range(len(df)):
        volatility = abs(returns[i]) * 3
        df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + volatility)
        df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - volatility)
        
        # Ajustar close
        df.loc[i, 'close'] = np.clip(df.loc[i, 'close'], 
                                    df.loc[i, 'low'], 
                                    df.loc[i, 'high'])
    
    df.set_index('timestamp', inplace=True)
    return df


def run_optimized_strategy_test():
    """
    Ejecuta test de la estrategia optimizada
    """
    print("🎯 Iniciando test de Estrategia Optimizada 20% Mensual")
    print("=" * 60)
    
    # Generar datos
    data = generate_enhanced_data(days=120)  # 4 meses
    print(f"📊 Datos generados: {len(data)} períodos")
    
    # Crear estrategia
    strategy = Optimized15PctStrategy()
    print("⚙️ Estrategia optimizada configurada")
    
    # Ejecutar backtest
    backtester = OptimizedBacktester(initial_balance=100000.0)
    results = backtester.run_backtest(data, strategy)
    
    # Mostrar resultados
    print("\n📈 RESULTADOS DEL BACKTEST OPTIMIZADO")
    print("=" * 45)
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return_pct']:.2f}%")
    print(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%")
    print(f"\n🎯 OBJETIVO 20% MENSUAL: {'✅ ALCANZADO' if results['target_achieved'] else '❌ NO ALCANZADO'}")
    
    print(f"\n📊 ESTADÍSTICAS DETALLADAS")
    print(f"Total de operaciones: {results['total_trades']}")
    print(f"Operaciones ganadoras: {results['winning_trades']}")
    print(f"Operaciones perdedoras: {results['losing_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Ganancia promedio: ${results['avg_win']:.2f}")
    print(f"Pérdida promedio: ${results['avg_loss']:.2f}")
    print(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"optimized_15pct_results_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS ESTRATEGIA OPTIMIZADA 20% MENSUAL\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Balance inicial: ${results['initial_balance']:,.2f}\n")
        f.write(f"Balance final: ${results['final_balance']:,.2f}\n")
        f.write(f"Retorno total: {results['total_return_pct']:.2f}%\n")
        f.write(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%\n")
        f.write(f"Objetivo 20% mensual: {'ALCANZADO' if results['target_achieved'] else 'NO ALCANZADO'}\n\n")
        
        f.write("ESTADÍSTICAS DETALLADAS:\n")
        f.write("-" * 25 + "\n")
        f.write(f"Total de operaciones: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
        f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")
        f.write(f"Ganancia bruta: ${results['gross_profit']:.2f}\n")
        f.write(f"Pérdida bruta: ${results['gross_loss']:.2f}\n")
        f.write(f"Ganancia promedio: ${results['avg_win']:.2f}\n")
        f.write(f"Pérdida promedio: ${results['avg_loss']:.2f}\n")
        f.write(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%\n\n")
        
        f.write("CARACTERÍSTICAS OPTIMIZADAS:\n")
        f.write("-" * 30 + "\n")
        f.write("- Gestión de riesgo dinámica\n")
        f.write("- Múltiples indicadores técnicos\n")
        f.write("- Filtros de calidad ajustados\n")
        f.write("- Trailing stop automático\n")
        f.write("- Detección de breakouts\n")
        f.write("- Análisis de patrones de velas\n")
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    # Mostrar algunas operaciones de ejemplo
    if results['trades']:
        print("\n📋 ÚLTIMAS 5 OPERACIONES:")
        print("-" * 40)
        for trade in results['trades'][-5:]:
            if trade.get('status') == 'closed':
                direction = trade['direction']
                pnl = trade.get('pnl', 0)
                pnl_pct = trade.get('pnl_pct', 0)
                reason = trade.get('exit_reason', 'Unknown')
                print(f"{direction}: {pnl_pct:+.2f}% (${pnl:+.2f}) - {reason}")
    
    return results


if __name__ == "__main__":
    results = run_optimized_strategy_test()