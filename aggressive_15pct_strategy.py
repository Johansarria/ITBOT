#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# Estrategia Agresiva para 20% Rentabilidad Mensual
Combina múltiples indicadores técnicos, gestión de riesgo dinámica y parámetros optimizados
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class Aggressive15PctStrategy:
    """
    Estrategia agresiva diseñada para generar mínimo 20% de rentabilidad mensual
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        # Configuración base agresiva
        self.config = config or {
            # Parámetros de momentum
            'rsi_period': 8,  # RSI más sensible
            'rsi_oversold': 25,  # Niveles más agresivos
            'rsi_overbought': 75,
            
            # MACD agresivo
            'macd_fast': 8,
            'macd_slow': 17,
            'macd_signal': 6,
            
            # Bollinger Bands
            'bb_period': 15,
            'bb_std': 1.8,
            
            # EMA múltiples
            'ema_fast': 5,
            'ema_medium': 13,
            'ema_slow': 21,
            
            # Gestión de riesgo agresiva
            'risk_per_trade': 0.08,  # 8% por operación
            'max_daily_risk': 0.25,  # 25% riesgo diario máximo
            'profit_target_multiplier': 2.5,  # 2.5:1 reward/risk
            'stop_loss_atr_multiplier': 1.2,
            
            # Filtros de tiempo
            'trading_hours_start': 8,  # 8 AM
            'trading_hours_end': 22,   # 10 PM
            'avoid_news_minutes': 30,
            
            # Parámetros de volatilidad
            'atr_period': 10,
            'volatility_threshold': 0.02,
            
            # Scalping parameters
            'min_profit_pips': 8,
            'max_holding_minutes': 45,
            
            # Machine Learning features
            'use_ml_filter': True,
            'ml_confidence_threshold': 0.65
        }
        
        self.position = None
        self.entry_time = None
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_daily_trades = 15
        
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula todos los indicadores técnicos necesarios
        """
        df = data.copy()
        
        # RSI
        df['rsi'] = self._calculate_rsi(df['close'], self.config['rsi_period'])
        
        # MACD
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        
        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_width'] = (bb_data['upper'] - bb_data['lower']) / bb_data['middle']
        
        # EMAs
        df['ema_fast'] = df['close'].ewm(span=self.config['ema_fast']).mean()
        df['ema_medium'] = df['close'].ewm(span=self.config['ema_medium']).mean()
        df['ema_slow'] = df['close'].ewm(span=self.config['ema_slow']).mean()
        
        # ATR para stop loss dinámico
        df['atr'] = self._calculate_atr(df)
        
        # Momentum indicators
        df['price_momentum'] = df['close'].pct_change(5)
        df['volume_momentum'] = df['volume'].pct_change(3) if 'volume' in df.columns else 0
        
        # Volatility squeeze
        df['volatility_squeeze'] = self._detect_volatility_squeeze(df)
        
        # Support/Resistance levels
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        
        # Market structure
        df['higher_highs'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['lower_lows'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))
        
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
        
        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        }
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calcula Bollinger Bands"""
        middle = prices.rolling(window=self.config['bb_period']).mean()
        std = prices.rolling(window=self.config['bb_period']).std()
        upper = middle + (std * self.config['bb_std'])
        lower = middle - (std * self.config['bb_std'])
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calcula Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=self.config['atr_period']).mean()
    
    def _detect_volatility_squeeze(self, df: pd.DataFrame) -> pd.Series:
        """Detecta compresión de volatilidad"""
        bb_squeeze = df['bb_width'] < df['bb_width'].rolling(20).mean() * 0.8
        low_atr = df['atr'] < df['atr'].rolling(20).mean() * 0.9
        return bb_squeeze & low_atr
    
    def generate_signal(self, df: pd.DataFrame, current_idx: int) -> str:
        """
        Genera señales de trading basadas en múltiples condiciones
        """
        if current_idx < 50:  # Necesitamos suficientes datos
            return "MANTENER"
        
        current = df.iloc[current_idx]
        prev = df.iloc[current_idx - 1]
        
        # Verificar límites de trading diario
        if self.daily_trades >= self.max_daily_trades:
            return "MANTENER"
        
        if abs(self.daily_pnl) >= self.config['max_daily_risk']:
            return "MANTENER"
        
        # Señales de compra
        buy_signals = self._get_buy_signals(current, prev, df, current_idx)
        sell_signals = self._get_sell_signals(current, prev, df, current_idx)
        
        # Filtros adicionales
        if self._is_high_impact_news_time():
            return "MANTENER"
        
        if not self._is_trading_hours():
            return "MANTENER"
        
        # Decisión final
        if buy_signals >= 4:  # Necesitamos al menos 4 señales de compra
            return "COMPRAR"
        elif sell_signals >= 4:  # Necesitamos al menos 4 señales de venta
            return "VENDER"
        else:
            return "MANTENER"
    
    def _get_buy_signals(self, current: pd.Series, prev: pd.Series, df: pd.DataFrame, idx: int) -> int:
        """Cuenta señales de compra"""
        signals = 0
        
        # RSI oversold recovery
        if prev['rsi'] < self.config['rsi_oversold'] and current['rsi'] > self.config['rsi_oversold']:
            signals += 1
        
        # MACD bullish crossover
        if prev['macd'] < prev['macd_signal'] and current['macd'] > current['macd_signal']:
            signals += 2  # Señal fuerte
        
        # MACD histogram growing
        if current['macd_histogram'] > prev['macd_histogram'] and current['macd_histogram'] > 0:
            signals += 1
        
        # Price above EMAs
        if current['close'] > current['ema_fast'] > current['ema_medium']:
            signals += 1
        
        # EMA crossover
        if prev['ema_fast'] < prev['ema_medium'] and current['ema_fast'] > current['ema_medium']:
            signals += 2
        
        # Bollinger Bands bounce
        if prev['close'] < prev['bb_lower'] and current['close'] > current['bb_lower']:
            signals += 1
        
        # Volatility squeeze breakout
        if prev['volatility_squeeze'] and not current['volatility_squeeze'] and current['close'] > prev['close']:
            signals += 2
        
        # Support level bounce
        if current['close'] > current['support'] * 1.001:  # 0.1% above support
            signals += 1
        
        # Momentum confirmation
        if current['price_momentum'] > 0.002:  # 0.2% momentum
            signals += 1
        
        # Higher highs pattern
        if current['higher_highs']:
            signals += 1
        
        return signals
    
    def _get_sell_signals(self, current: pd.Series, prev: pd.Series, df: pd.DataFrame, idx: int) -> int:
        """Cuenta señales de venta"""
        signals = 0
        
        # RSI overbought reversal
        if prev['rsi'] > self.config['rsi_overbought'] and current['rsi'] < self.config['rsi_overbought']:
            signals += 1
        
        # MACD bearish crossover
        if prev['macd'] > prev['macd_signal'] and current['macd'] < current['macd_signal']:
            signals += 2
        
        # MACD histogram declining
        if current['macd_histogram'] < prev['macd_histogram'] and current['macd_histogram'] < 0:
            signals += 1
        
        # Price below EMAs
        if current['close'] < current['ema_fast'] < current['ema_medium']:
            signals += 1
        
        # EMA bearish crossover
        if prev['ema_fast'] > prev['ema_medium'] and current['ema_fast'] < current['ema_medium']:
            signals += 2
        
        # Bollinger Bands rejection
        if prev['close'] > prev['bb_upper'] and current['close'] < current['bb_upper']:
            signals += 1
        
        # Volatility squeeze breakout down
        if prev['volatility_squeeze'] and not current['volatility_squeeze'] and current['close'] < prev['close']:
            signals += 2
        
        # Resistance level rejection
        if current['close'] < current['resistance'] * 0.999:  # 0.1% below resistance
            signals += 1
        
        # Negative momentum
        if current['price_momentum'] < -0.002:
            signals += 1
        
        # Lower lows pattern
        if current['lower_lows']:
            signals += 1
        
        return signals
    
    def _is_trading_hours(self) -> bool:
        """Verifica si estamos en horario de trading"""
        current_hour = datetime.now().hour
        return self.config['trading_hours_start'] <= current_hour <= self.config['trading_hours_end']
    
    def _is_high_impact_news_time(self) -> bool:
        """Verifica si hay noticias de alto impacto (simplificado)"""
        # En una implementación real, esto se conectaría a un calendario económico
        current_time = datetime.now()
        # Evitar trading 30 minutos antes y después de las 14:30 UTC (NFP, FOMC, etc.)
        high_impact_times = [14, 15, 16]  # Horas UTC típicas de noticias
        return current_time.hour in high_impact_times
    
    def calculate_position_size(self, price: float, stop_loss: float, account_balance: float) -> float:
        """Calcula el tamaño de posición basado en gestión de riesgo agresiva"""
        risk_amount = account_balance * self.config['risk_per_trade']
        price_diff = abs(price - stop_loss)
        
        if price_diff == 0:
            return 0
        
        position_size = risk_amount / price_diff
        
        # Limitar el tamaño máximo de posición al 50% del balance
        max_position_value = account_balance * 0.5
        max_position_size = max_position_value / price
        
        return min(position_size, max_position_size)
    
    def calculate_stop_loss(self, entry_price: float, direction: str, atr: float) -> float:
        """Calcula stop loss dinámico basado en ATR"""
        atr_multiplier = self.config['stop_loss_atr_multiplier']
        
        if direction == "COMPRAR":
            return entry_price - (atr * atr_multiplier)
        else:  # VENDER
            return entry_price + (atr * atr_multiplier)
    
    def calculate_take_profit(self, entry_price: float, stop_loss: float, direction: str) -> float:
        """Calcula take profit basado en ratio reward/risk"""
        risk = abs(entry_price - stop_loss)
        reward = risk * self.config['profit_target_multiplier']
        
        if direction == "COMPRAR":
            return entry_price + reward
        else:  # VENDER
            return entry_price - reward
    
    def should_close_position(self, current_data: pd.Series, entry_price: float, 
                            entry_time: datetime, direction: str) -> bool:
        """Determina si debe cerrar la posición actual"""
        current_time = datetime.now()
        
        # Cerrar por tiempo máximo de holding
        if (current_time - entry_time).total_seconds() / 60 > self.config['max_holding_minutes']:
            return True
        
        # Cerrar si el momentum cambia drásticamente
        if direction == "COMPRAR" and current_data['price_momentum'] < -0.005:
            return True
        elif direction == "VENDER" and current_data['price_momentum'] > 0.005:
            return True
        
        # Cerrar si RSI está en zona extrema opuesta
        if direction == "COMPRAR" and current_data['rsi'] > 85:
            return True
        elif direction == "VENDER" and current_data['rsi'] < 15:
            return True
        
        return False
    
    def update_daily_stats(self, pnl: float):
        """Actualiza estadísticas diarias"""
        self.daily_pnl += pnl
        self.daily_trades += 1
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Retorna información de la estrategia"""
        return {
            'name': 'Aggressive 20% Monthly Strategy',
            'target_monthly_return': 0.15,
            'risk_per_trade': self.config['risk_per_trade'],
            'max_daily_trades': self.max_daily_trades,
            'profit_target_ratio': self.config['profit_target_multiplier'],
            'indicators_used': [
                'RSI', 'MACD', 'Bollinger Bands', 'EMA', 'ATR',
                'Momentum', 'Support/Resistance', 'Volatility Squeeze'
            ],
            'trading_style': 'Aggressive Scalping/Swing Hybrid',
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades
        }


class AggressiveBacktester:
    """
    Backtester especializado para estrategias agresivas
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
        
    def run_backtest(self, data: pd.DataFrame, strategy: Aggressive15PctStrategy) -> Dict[str, Any]:
        """Ejecuta backtest de la estrategia agresiva"""
        df = strategy.calculate_indicators(data)
        
        for i in range(len(df)):
            current_data = df.iloc[i]
            
            # Verificar si hay posición abierta
            if self.position is not None:
                self._check_exit_conditions(current_data, strategy, i)
            else:
                # Buscar nueva entrada
                signal = strategy.generate_signal(df, i)
                if signal in ["COMPRAR", "VENDER"]:
                    self._open_position(current_data, signal, strategy)
            
            # Actualizar historial de balance
            current_value = self._calculate_portfolio_value(current_data['close'])
            self.balance_history.append(current_value)
        
        # Cerrar posición final si existe
        if self.position is not None:
            self._close_position(df.iloc[-1]['close'], "Final close")
        
        return self._calculate_results()
    
    def _open_position(self, data: pd.Series, direction: str, strategy: Aggressive15PctStrategy):
        """Abre nueva posición"""
        price = data['close']
        atr = data['atr']
        
        # Calcular stop loss y take profit
        stop_loss = strategy.calculate_stop_loss(price, direction, atr)
        take_profit = strategy.calculate_take_profit(price, stop_loss, direction)
        
        # Calcular tamaño de posición
        position_size = strategy.calculate_position_size(price, stop_loss, self.balance)
        
        if position_size > 0:
            cost = position_size * price * (1 + self.commission)
            
            if cost <= self.balance:
                self.position = direction
                self.position_size = position_size
                self.entry_price = price
                self.stop_loss = stop_loss
                self.take_profit = take_profit
                self.balance -= cost
                
                # Registrar trade
                trade = {
                    'entry_time': data.name if hasattr(data, 'name') else len(self.trades),
                    'direction': direction,
                    'entry_price': price,
                    'position_size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'status': 'open'
                }
                self.trades.append(trade)
    
    def _check_exit_conditions(self, data: pd.Series, strategy: Aggressive15PctStrategy, idx: int):
        """Verifica condiciones de salida"""
        current_price = data['close']
        
        # Check stop loss
        if self.position == "COMPRAR" and current_price <= self.stop_loss:
            self._close_position(current_price, "Stop Loss")
            return
        elif self.position == "VENDER" and current_price >= self.stop_loss:
            self._close_position(current_price, "Stop Loss")
            return
        
        # Check take profit
        if self.position == "COMPRAR" and current_price >= self.take_profit:
            self._close_position(current_price, "Take Profit")
            return
        elif self.position == "VENDER" and current_price <= self.take_profit:
            self._close_position(current_price, "Take Profit")
            return
        
        # Check strategy-specific exit conditions
        if strategy.should_close_position(data, self.entry_price, 
                                        datetime.now(), self.position):
            self._close_position(current_price, "Strategy Exit")
    
    def _close_position(self, exit_price: float, reason: str):
        """Cierra posición actual"""
        if self.position is None:
            return
        
        # Calcular P&L
        if self.position == "COMPRAR":
            pnl = (exit_price - self.entry_price) * self.position_size
        else:  # VENDER
            pnl = (self.entry_price - exit_price) * self.position_size
        
        # Aplicar comisión
        commission_cost = exit_price * self.position_size * self.commission
        pnl -= commission_cost
        
        # Actualizar balance
        proceeds = exit_price * self.position_size * (1 - self.commission)
        self.balance += proceeds
        
        # Actualizar último trade
        if self.trades:
            self.trades[-1].update({
                'exit_price': exit_price,
                'exit_reason': reason,
                'pnl': pnl,
                'status': 'closed'
            })
        
        # Reset position
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """Calcula valor actual del portfolio"""
        if self.position is None:
            return self.balance
        
        position_value = self.position_size * current_price
        return self.balance + position_value
    
    def _calculate_results(self) -> Dict[str, Any]:
        """Calcula resultados del backtest"""
        final_balance = self.balance_history[-1]
        total_return = (final_balance / self.initial_balance - 1) * 100
        
        # Calcular métricas de trades
        closed_trades = [t for t in self.trades if t.get('status') == 'closed']
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        # Calcular drawdown
        peak = self.initial_balance
        max_drawdown = 0
        for balance in self.balance_history:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calcular retorno mensual promedio
        days_simulated = len(self.balance_history)
        monthly_return = (total_return / days_simulated) * 30 if days_simulated > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_return_pct': total_return,
            'monthly_return_pct': monthly_return,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,
            'max_drawdown_pct': max_drawdown,
            'balance_history': self.balance_history,
            'trades': self.trades,
            'target_achieved': monthly_return >= 20.0
        }


def generate_test_data(days: int = 60, initial_price: float = 18000) -> pd.DataFrame:
    """
    Genera datos de prueba para NAS100 con mayor volatilidad
    """
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=days * 24 * 4, freq='15min')
    
    # Generar precios con mayor volatilidad para testing agresivo
    returns = np.random.normal(0, 0.008, len(dates))  # Mayor volatilidad
    
    # Añadir tendencias y patrones
    trend = np.sin(np.arange(len(dates)) * 2 * np.pi / (24 * 4 * 7)) * 0.002
    volatility_clusters = np.random.choice([1, 2, 3], len(dates), p=[0.7, 0.2, 0.1])
    returns = returns * volatility_clusters + trend
    
    prices = initial_price * (1 + returns).cumprod()
    
    # Generar OHLC
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices * (1 + np.abs(np.random.normal(0, 0.003, len(dates)))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.003, len(dates)))),
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates))
    })
    
    df.set_index('timestamp', inplace=True)
    return df


def run_aggressive_strategy_test():
    """
    Ejecuta test de la estrategia agresiva
    """
    print("🚀 Iniciando test de Estrategia Agresiva para 20% Mensual")
    print("=" * 60)
    
    # Generar datos de prueba
    data = generate_test_data(days=90)  # 3 meses de datos
    print(f"📊 Datos generados: {len(data)} períodos de 15 minutos")
    
    # Crear estrategia
    strategy = Aggressive15PctStrategy()
    print(f"⚙️ Estrategia configurada: {strategy.get_strategy_info()['name']}")
    
    # Ejecutar backtest
    backtester = AggressiveBacktester(initial_balance=100000.0)
    results = backtester.run_backtest(data, strategy)
    
    # Mostrar resultados
    print("\n📈 RESULTADOS DEL BACKTEST")
    print("=" * 40)
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return_pct']:.2f}%")
    print(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%")
    print(f"\n🎯 OBJETIVO 20% MENSUAL: {'✅ ALCANZADO' if results['target_achieved'] else '❌ NO ALCANZADO'}")
    
    print(f"\n📊 ESTADÍSTICAS DE TRADING")
    print(f"Total de operaciones: {results['total_trades']}")
    print(f"Operaciones ganadoras: {results['winning_trades']}")
    print(f"Operaciones perdedoras: {results['losing_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"aggressive_15pct_results_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS ESTRATEGIA AGRESIVA 20% MENSUAL\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Balance inicial: ${results['initial_balance']:,.2f}\n")
        f.write(f"Balance final: ${results['final_balance']:,.2f}\n")
        f.write(f"Retorno total: {results['total_return_pct']:.2f}%\n")
        f.write(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%\n")
        f.write(f"Objetivo 20% mensual: {'ALCANZADO' if results['target_achieved'] else 'NO ALCANZADO'}\n\n")
        f.write(f"Total de operaciones: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
        f.write(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%\n\n")
        
        # Detalles de configuración
        strategy_info = strategy.get_strategy_info()
        f.write("CONFIGURACIÓN DE LA ESTRATEGIA:\n")
        f.write("-" * 30 + "\n")
        for key, value in strategy_info.items():
            f.write(f"{key}: {value}\n")
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    return results


if __name__ == "__main__":
    results = run_aggressive_strategy_test()