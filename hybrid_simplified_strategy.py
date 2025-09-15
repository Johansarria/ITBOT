#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Estrategia Híbrida Simplificada para 15% Mensual
Combina lo mejor de las estrategias anteriores con máxima simplicidad
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class HybridSimplifiedStrategy:
    """
    Estrategia híbrida simplificada - menos filtros, más operaciones
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            # Gestión de riesgo simplificada
            'risk_per_trade': 0.03,        # 3% fijo por operación
            'max_daily_risk': 0.12,        # 12% máximo diario
            'max_daily_trades': 6,         # Máximo 6 operaciones por día
            'stop_loss_pct': 0.008,        # 0.8% stop loss fijo
            'take_profit_pct': 0.020,      # 2% take profit fijo (2.5:1 ratio)
            
            # Indicadores simplificados (solo 3 principales)
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'ema_fast': 9,
            'ema_slow': 21,
            'bb_period': 20,
            'bb_std': 2.0,
            
            # Filtros mínimos
            'min_signal_score': 3,         # Solo 3 puntos mínimo
            'volume_threshold': 1.2,       # 20% más volumen
            'min_volatility': 0.002,
            'max_volatility': 0.05,
            
            # Gestión de posiciones
            'partial_profit_level': 0.012, # 1.2% - tomar 50%
            'trailing_stop_activation': 0.015, # 1.5%
            'trailing_stop_distance': 0.005,   # 0.5%
        }
        
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trailing_stop = 0
        self.partial_taken = False
        self.daily_trades = 0
        self.daily_pnl = 0.0
        
    def calculate_simple_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula solo los indicadores esenciales
        """
        df = data.copy()
        
        # RSI (indicador principal de momentum)
        df['rsi'] = self._calculate_rsi(df['close'], self.config['rsi_period'])
        
        # EMAs (tendencia)
        df['ema_fast'] = df['close'].ewm(span=self.config['ema_fast']).mean()
        df['ema_slow'] = df['close'].ewm(span=self.config['ema_slow']).mean()
        df['ema_trend'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
        
        # Bollinger Bands (volatilidad y extremos)
        bb_data = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Volatilidad simple
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
        
        # Momentum simple
        df['momentum'] = df['close'].pct_change(5)
        
        # Volume ratio (si está disponible)
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
        else:
            df['volume_ratio'] = 1.0
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calcula Bollinger Bands"""
        middle = prices.rolling(window=self.config['bb_period']).mean()
        std = prices.rolling(window=self.config['bb_period']).std()
        upper = middle + (std * self.config['bb_std'])
        lower = middle - (std * self.config['bb_std'])
        
        return {'upper': upper, 'middle': middle, 'lower': lower}
    
    def generate_simple_signal(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Genera señales con lógica simplificada
        """
        if idx < 30:  # Necesitamos datos suficientes
            return {'action': 'MANTENER', 'reason': 'Insufficient data'}
        
        # Verificar límites diarios
        if self.daily_trades >= self.config['max_daily_trades']:
            return {'action': 'MANTENER', 'reason': 'Daily trade limit'}
        
        if abs(self.daily_pnl) >= self.config['max_daily_risk']:
            return {'action': 'MANTENER', 'reason': 'Daily risk limit'}
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        # Filtro de volatilidad
        if (current['volatility'] < self.config['min_volatility'] or 
            current['volatility'] > self.config['max_volatility']):
            return {'action': 'MANTENER', 'reason': 'Volatility filter'}
        
        # Calcular puntuación de señales
        buy_score = 0
        sell_score = 0
        
        # 1. RSI (peso: 2 puntos)
        if current['rsi'] < self.config['rsi_oversold']:
            buy_score += 2
        elif current['rsi'] > self.config['rsi_overbought']:
            sell_score += 2
        
        # 2. Tendencia EMA (peso: 2 puntos)
        if current['ema_trend'] == 1 and prev['ema_trend'] != 1:  # Nuevo cruce alcista
            buy_score += 2
        elif current['ema_trend'] == -1 and prev['ema_trend'] != -1:  # Nuevo cruce bajista
            sell_score += 2
        elif current['ema_trend'] == 1:  # Tendencia alcista establecida
            buy_score += 1
        elif current['ema_trend'] == -1:  # Tendencia bajista establecida
            sell_score += 1
        
        # 3. Bollinger Bands (peso: 2 puntos)
        if current['bb_position'] < 0.2:  # Cerca del límite inferior
            buy_score += 2
        elif current['bb_position'] > 0.8:  # Cerca del límite superior
            sell_score += 2
        
        # 4. Momentum (peso: 1 punto)
        if current['momentum'] > 0.003:  # Momentum positivo fuerte
            buy_score += 1
        elif current['momentum'] < -0.003:  # Momentum negativo fuerte
            sell_score += 1
        
        # 5. Volumen (peso: 1 punto)
        if current['volume_ratio'] > self.config['volume_threshold']:
            if buy_score > sell_score:
                buy_score += 1
            elif sell_score > buy_score:
                sell_score += 1
        
        # Decisión final (muy simple)
        if buy_score >= self.config['min_signal_score'] and buy_score > sell_score:
            return {
                'action': 'COMPRAR',
                'score': buy_score,
                'reason': f'Buy signals: {buy_score}'
            }
        elif sell_score >= self.config['min_signal_score'] and sell_score > buy_score:
            return {
                'action': 'VENDER',
                'score': sell_score,
                'reason': f'Sell signals: {sell_score}'
            }
        else:
            return {
                'action': 'MANTENER',
                'reason': f'Insufficient signals (B:{buy_score}, S:{sell_score})'
            }
    
    def calculate_position_size(self, price: float, account_balance: float) -> float:
        """
        Calcula tamaño de posición simple
        """
        risk_amount = account_balance * self.config['risk_per_trade']
        stop_distance = price * self.config['stop_loss_pct']
        
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
            # Limitar a máximo 30% del balance
            max_position_value = account_balance * 0.3
            max_position_size = max_position_value / price
            return min(position_size, max_position_size)
        
        return 0
    
    def update_trailing_stop(self, current_price: float, direction: str):
        """Actualiza trailing stop simple"""
        if direction == "COMPRAR":
            profit_pct = (current_price - self.entry_price) / self.entry_price
            if profit_pct >= self.config['trailing_stop_activation']:
                new_trailing = current_price * (1 - self.config['trailing_stop_distance'])
                self.trailing_stop = max(self.trailing_stop, new_trailing)
        else:  # VENDER
            profit_pct = (self.entry_price - current_price) / self.entry_price
            if profit_pct >= self.config['trailing_stop_activation']:
                new_trailing = current_price * (1 + self.config['trailing_stop_distance'])
                if self.trailing_stop == 0:
                    self.trailing_stop = new_trailing
                else:
                    self.trailing_stop = min(self.trailing_stop, new_trailing)
    
    def should_take_partial_profit(self, current_price: float, direction: str) -> bool:
        """Determina si tomar ganancia parcial"""
        if self.partial_taken:
            return False
        
        profit_pct = 0
        if direction == "COMPRAR":
            profit_pct = (current_price - self.entry_price) / self.entry_price
        else:
            profit_pct = (self.entry_price - current_price) / self.entry_price
        
        return profit_pct >= self.config['partial_profit_level']
    
    def should_exit_position(self, current_price: float, direction: str) -> Tuple[bool, str]:
        """Determina si salir de la posición"""
        # Stop loss fijo
        if direction == "COMPRAR" and current_price <= self.stop_loss:
            return True, "Stop Loss"
        elif direction == "VENDER" and current_price >= self.stop_loss:
            return True, "Stop Loss"
        
        # Take profit fijo
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
    
    def update_performance(self, pnl: float):
        """Actualiza métricas simples"""
        self.daily_pnl += pnl
        self.daily_trades += 1
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0


class SimplifiedBacktester:
    """
    Backtester simplificado para la estrategia híbrida
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
        
    def run_backtest(self, data: pd.DataFrame, strategy: HybridSimplifiedStrategy) -> Dict[str, Any]:
        """Ejecuta backtest simplificado"""
        df = strategy.calculate_simple_indicators(data)
        
        print(f"📊 Iniciando backtest con {len(df)} registros")
        print(f"   Rango: {df.index[0]} a {df.index[-1]}")
        
        for i in range(len(df)):
            current_data = df.iloc[i]
            
            # Verificar posición existente
            if self.position is not None:
                self._manage_position(current_data, strategy)
            else:
                # Buscar nueva entrada
                signal_data = strategy.generate_simple_signal(df, i)
                if signal_data['action'] in ['COMPRAR', 'VENDER']:
                    self._open_position(current_data, signal_data, strategy)
            
            # Actualizar historial
            current_value = self._calculate_portfolio_value(current_data['close'])
            self.balance_history.append(current_value)
            
            # Mostrar progreso cada 1000 registros
            if i % 1000 == 0 and i > 0:
                progress = (i / len(df)) * 100
                print(f"   Progreso: {progress:.1f}% - Trades: {len(self.trades)} - Balance: ${current_value:,.0f}")
        
        # Cerrar posición final
        if self.position is not None:
            self._close_position(df.iloc[-1]['close'], "Final close")
        
        print(f"✅ Backtest completado - {len(self.trades)} operaciones")
        
        return self._calculate_results()
    
    def _open_position(self, data: pd.Series, signal_data: Dict[str, Any], strategy: HybridSimplifiedStrategy):
        """Abre nueva posición"""
        price = data['close']
        direction = signal_data['action']
        
        # Calcular tamaño de posición
        position_size = strategy.calculate_position_size(price, self.balance)
        
        if position_size > 0:
            cost = position_size * price * (1 + self.commission)
            
            if cost <= self.balance:
                self.position = direction
                self.position_size = position_size
                self.entry_price = price
                
                # Calcular stop loss y take profit fijos
                if direction == "COMPRAR":
                    self.stop_loss = price * (1 - strategy.config['stop_loss_pct'])
                    self.take_profit = price * (1 + strategy.config['take_profit_pct'])
                else:  # VENDER
                    self.stop_loss = price * (1 + strategy.config['stop_loss_pct'])
                    self.take_profit = price * (1 - strategy.config['take_profit_pct'])
                
                self.balance -= cost
                
                # Actualizar estrategia
                strategy.position = direction
                strategy.position_size = position_size
                strategy.entry_price = price
                strategy.stop_loss = self.stop_loss
                strategy.take_profit = self.take_profit
                strategy.trailing_stop = 0
                strategy.partial_taken = False
                
                # Registrar trade
                trade = {
                    'entry_time': data.name if hasattr(data, 'name') else len(self.trades),
                    'direction': direction,
                    'entry_price': price,
                    'position_size': position_size,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'signal_score': signal_data.get('score', 0),
                    'status': 'open'
                }
                self.trades.append(trade)
    
    def _manage_position(self, data: pd.Series, strategy: HybridSimplifiedStrategy):
        """Gestiona posición existente"""
        current_price = data['close']
        
        # Verificar ganancia parcial
        if strategy.should_take_partial_profit(current_price, self.position):
            self._take_partial_profit(current_price, strategy)
        
        # Actualizar trailing stop
        strategy.update_trailing_stop(current_price, self.position)
        
        # Verificar salida
        should_exit, reason = strategy.should_exit_position(current_price, self.position)
        if should_exit:
            self._close_position(current_price, reason)
    
    def _take_partial_profit(self, current_price: float, strategy: HybridSimplifiedStrategy):
        """Toma ganancia parcial (50%)"""
        partial_size = self.position_size * 0.5
        
        # Calcular P&L parcial
        if self.position == "COMPRAR":
            pnl = (current_price - self.entry_price) * partial_size
        else:
            pnl = (self.entry_price - current_price) * partial_size
        
        # Aplicar comisión
        commission_cost = current_price * partial_size * self.commission
        pnl -= commission_cost
        
        # Actualizar balance y posición
        proceeds = current_price * partial_size * (1 - self.commission)
        self.balance += proceeds
        self.position_size -= partial_size
        strategy.position_size -= partial_size
        
        # Mover stop loss a breakeven
        self.stop_loss = self.entry_price
        strategy.stop_loss = self.entry_price
        
        strategy.partial_taken = True
        
        # Actualizar trade
        if self.trades:
            self.trades[-1]['partial_profit_taken'] = True
            self.trades[-1]['partial_pnl'] = pnl
    
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
        
        # Calcular P&L total
        total_pnl = pnl + self.trades[-1].get('partial_pnl', 0) if self.trades else pnl
        
        # Actualizar trade
        if self.trades:
            self.trades[-1].update({
                'exit_price': exit_price,
                'exit_reason': reason,
                'final_pnl': pnl,
                'total_pnl': total_pnl,
                'total_pnl_pct': (total_pnl / (self.entry_price * self.trades[-1]['position_size'])) * 100,
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
        winning_trades = [t for t in closed_trades if t.get('total_pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('total_pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        # Métricas
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
        
        # Retorno mensual estimado
        days_simulated = len(self.balance_history) / (24 * 4)  # Asumiendo 15min intervals
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
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_drawdown_pct': max_drawdown,
            'avg_signal_score': np.mean([t.get('signal_score', 0) for t in closed_trades]) if closed_trades else 0,
            'target_achieved': monthly_return >= 15.0,
            'balance_history': self.balance_history,
            'trades': self.trades
        }


def run_hybrid_simplified_test(data: pd.DataFrame = None):
    """
    Ejecuta test de la estrategia híbrida simplificada
    """
    print("🔥 Iniciando test de Estrategia Híbrida Simplificada")
    print("=" * 60)
    
    if data is None:
        print("⚠️ No se proporcionaron datos, usando datos sintéticos")
        # Generar datos sintéticos como fallback
        data = generate_fallback_data()
    
    print(f"📊 Datos para backtesting: {len(data)} registros")
    print(f"   Rango: {data.index[0]} a {data.index[-1]}")
    
    # Crear estrategia
    strategy = HybridSimplifiedStrategy()
    print("⚙️ Estrategia híbrida simplificada configurada")
    print(f"   Riesgo por trade: {strategy.config['risk_per_trade']*100}%")
    print(f"   Stop loss: {strategy.config['stop_loss_pct']*100}%")
    print(f"   Take profit: {strategy.config['take_profit_pct']*100}%")
    
    # Ejecutar backtest
    backtester = SimplifiedBacktester(initial_balance=100000.0)
    results = backtester.run_backtest(data, strategy)
    
    # Mostrar resultados
    print("\n📈 RESULTADOS DEL BACKTEST HÍBRIDO SIMPLIFICADO")
    print("=" * 55)
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return_pct']:.2f}%")
    print(f"Retorno mensual estimado: {results['monthly_return_pct']:.2f}%")
    print(f"\n🎯 OBJETIVO 15% MENSUAL: {'✅ ALCANZADO' if results['target_achieved'] else '❌ NO ALCANZADO'}")
    
    print(f"\n📊 ESTADÍSTICAS SIMPLIFICADAS")
    print(f"Total de operaciones: {results['total_trades']}")
    print(f"Operaciones ganadoras: {results['winning_trades']}")
    print(f"Operaciones perdedoras: {results['losing_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Score promedio de señales: {results['avg_signal_score']:.1f}")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"hybrid_simplified_results_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS ESTRATEGIA HÍBRIDA SIMPLIFICADA\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Balance inicial: ${results['initial_balance']:,.2f}\n")
        f.write(f"Balance final: ${results['final_balance']:,.2f}\n")
        f.write(f"Retorno total: {results['total_return_pct']:.2f}%\n")
        f.write(f"Retorno mensual estimado: {results['monthly_return_pct']:.2f}%\n")
        f.write(f"Objetivo 15% mensual: {'ALCANZADO' if results['target_achieved'] else 'NO ALCANZADO'}\n\n")
        
        f.write("ESTADÍSTICAS:\n")
        f.write("-" * 15 + "\n")
        f.write(f"Total de operaciones: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
        f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")
        f.write(f"Ganancia bruta: ${results['gross_profit']:.2f}\n")
        f.write(f"Pérdida bruta: ${results['gross_loss']:.2f}\n")
        f.write(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%\n")
        f.write(f"Score promedio: {results['avg_signal_score']:.1f}\n\n")
        
        f.write("CONFIGURACIÓN SIMPLIFICADA:\n")
        f.write("-" * 25 + "\n")
        f.write("- Solo 3 indicadores principales (RSI, EMA, BB)\n")
        f.write("- Gestión de riesgo fija (3% por trade)\n")
        f.write("- Stop loss y take profit fijos\n")
        f.write("- Toma de ganancias parciales automática\n")
        f.write("- Trailing stop simple\n")
        f.write("- Filtros mínimos para más operaciones\n")
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    # Mostrar últimas operaciones
    if results['trades']:
        print("\n📋 ÚLTIMAS 5 OPERACIONES:")
        print("-" * 50)
        for trade in results['trades'][-5:]:
            if trade.get('status') == 'closed':
                direction = trade['direction']
                total_pnl_pct = trade.get('total_pnl_pct', 0)
                reason = trade.get('exit_reason', 'Unknown')
                score = trade.get('signal_score', 0)
                partial = " (Parcial)" if trade.get('partial_profit_taken', False) else ""
                print(f"{direction}: {total_pnl_pct:+.2f}% (Score:{score}) - {reason}{partial}")
    
    return results


def generate_fallback_data(days: int = 90, initial_price: float = 18000) -> pd.DataFrame:
    """
    Genera datos sintéticos como fallback
    """
    np.random.seed(12345)
    periods_per_day = 24 * 4
    total_periods = days * periods_per_day
    
    dates = pd.date_range(start='2024-01-01', periods=total_periods, freq='15min')
    
    # Generar retornos más realistas
    base_volatility = 0.004
    returns = np.random.normal(0, base_volatility, total_periods)
    
    # Añadir tendencias y ciclos
    trend_cycle = np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 20)) * 0.002
    volatility_cycle = 1 + 0.5 * np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 5))
    
    returns = returns * volatility_cycle + trend_cycle
    
    # Generar precios
    prices = initial_price * (1 + returns).cumprod()
    
    # Crear OHLC
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'close': prices,
        'volume': np.random.randint(20000, 200000, total_periods)
    })
    
    # Generar high/low
    for i in range(len(df)):
        volatility = abs(returns[i]) * 2
        df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + volatility)
        df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - volatility)
        df.loc[i, 'close'] = np.clip(df.loc[i, 'close'], df.loc[i, 'low'], df.loc[i, 'high'])
    
    df.set_index('timestamp', inplace=True)
    return df


if __name__ == "__main__":
    results = run_hybrid_simplified_test()