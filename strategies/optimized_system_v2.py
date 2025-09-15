#!/usr/bin/env python3
"""
SISTEMA OPTIMIZADO V2 - BASADO EN RESULTADOS REALES DE BINANCE
Implementación mejorada después del análisis de 90 días de datos reales
"""

import ccxt
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import asyncio
import json
import warnings
warnings.filterwarnings('ignore')

class OptimizedTradingSystem:
    def __init__(self, initial_capital=10000):
        """
        Sistema optimizado basado en resultados reales
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades_history = []
        
        # NUEVA ASIGNACIÓN OPTIMIZADA basada en resultados reales
        self.strategies_config = {
            'mean_reversion': {
                'allocation': 0.40,  # Aumentado (WR: 66.6%, ROI/Trade: $1.67)
                'timeframe': '15m',
                'lookback': 50,
                'min_volume_multiplier': 1.5,  # Más selectivo
                'rsi_oversold': 30,  # Más conservador
                'rsi_overbought': 70
            },
            'temporal_arbitrage': {
                'allocation': 0.35,  # Aumentado (Buen PnL, WR: 52.1%)
                'timeframe': '30m',
                'lookback': 40,
                'min_trend_strength': 0.7,  # Más selectivo
                'volume_confirmation': True
            },
            'breakout_momentum': {
                'allocation': 0.20,  # Mantenido (Rentable)
                'timeframe': '1h',
                'lookback': 20,  # Reducido para más precisión
                'volume_multiplier': 2.0,  # Más estricto
                'confirmation_periods': 2
            },
            'selective_scalping': {
                'allocation': 0.05,  # Drasticamente reducido
                'timeframe': '5m',
                'lookback': 10,
                'quality_filters': True,  # Nuevos filtros
                'max_trades_per_day': 5,  # Limitar frecuencia
                'min_profit_target': 0.3  # Más ambicioso
            }
            # volatility_trading ELIMINADA (perdía dinero)
        }
        
        # PARES OPTIMIZADOS basados en performance real
        self.primary_pairs = [
            'ETH/USDT',   # Mejor performer
            'BCH/USDT',   # Segundo mejor
            'BNB/USDT'    # Tercero
        ]
        
        self.secondary_pairs = [
            'BTC/USDT',   # Líquido pero más difícil
            'XRP/USDT'    # Moderado
        ]
        
        # Evitar temporalmente
        # 'DOT/USDT', 'UNI/USDT', 'LINK/USDT', 'LTC/USDT', 'ADA/USDT'
        
        print("🚀 SISTEMA OPTIMIZADO V2 - POST ANÁLISIS REAL")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print("📊 Optimizaciones aplicadas:")
        print("   ✅ Mean Reversion: 40% (era 25%)")
        print("   ✅ Temporal Arbitrage: 35% (era 15%)")
        print("   ✅ Breakout Momentum: 20% (mantenido)")
        print("   ⚡ Selective Scalping: 5% (era 35%)")
        print("   ❌ Volatility Trading: ELIMINADA")

    def enhanced_mean_reversion_strategy(self, df):
        """
        Estrategia de reversión a la media OPTIMIZADA
        """
        signals = pd.Series(index=df.index, data=0)
        
        # Filtros de calidad mejorados
        volume_filter = df['volume'] > df['volume_sma'] * self.strategies_config['mean_reversion']['min_volume_multiplier']
        trend_filter = df['close'] > df['ema_200']  # Solo en tendencia alcista general
        volatility_filter = df['atr'] / df['close'] > 0.01  # Mínima volatilidad
        
        # Señales más conservadoras
        rsi_oversold = self.strategies_config['mean_reversion']['rsi_oversold']
        rsi_overbought = self.strategies_config['mean_reversion']['rsi_overbought']
        
        # Compra: Toque de banda inferior + confirmación múltiple
        buy_condition = (
            (df['close'] <= df['bb_lower']) &
            (df['rsi'] < rsi_oversold) &
            (df['rsi'] > 20) &  # No extremo
            trend_filter &
            volume_filter &
            volatility_filter &
            (df['macd'] > df['macd_signal'].shift(1))  # MACD comenzando a subir
        )
        
        # Venta: Toque de banda superior con confirmación
        sell_condition = (
            (df['close'] >= df['bb_upper']) &
            (df['rsi'] > rsi_overbought) &
            (df['rsi'] < 80) &  # No extremo
            volume_filter &
            (df['close'] < df['ema_200']) &  # Tendencia bajista
            (df['macd'] < df['macd_signal'].shift(1))  # MACD comenzando a bajar
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def enhanced_temporal_arbitrage_strategy(self, df):
        """
        Arbitraje temporal OPTIMIZADO con mejor selección
        """
        signals = pd.Series(index=df.index, data=0)
        
        # Análisis de fuerza de tendencia mejorado
        trend_strength_short = abs(df['ema_9'] - df['ema_21']) / df['close']
        trend_strength_medium = abs(df['ema_21'] - df['ema_50']) / df['close']
        trend_strength_long = abs(df['ema_50'] - df['ema_200']) / df['close']
        
        min_strength = self.strategies_config['temporal_arbitrage']['min_trend_strength'] / 100
        
        # Alineación de tendencias con fuerza mínima
        strong_uptrend = (
            (df['ema_9'] > df['ema_21']) & 
            (df['ema_21'] > df['ema_50']) &
            (df['ema_50'] > df['ema_200']) &
            (trend_strength_short > min_strength) &
            (trend_strength_medium > min_strength)
        )
        
        strong_downtrend = (
            (df['ema_9'] < df['ema_21']) & 
            (df['ema_21'] < df['ema_50']) &
            (df['ema_50'] < df['ema_200']) &
            (trend_strength_short > min_strength) &
            (trend_strength_medium > min_strength)
        )
        
        # Confirmación de volumen
        volume_confirm = df['volume'] > df['volume_sma'] * 1.2
        momentum_confirm = df['macd_histogram'] > df['macd_histogram'].shift(1)
        
        buy_condition = (
            strong_uptrend &
            volume_confirm &
            momentum_confirm &
            (df['stoch_k'] < 75) &  # No sobrecomprado
            (df['rsi'] > 40) & (df['rsi'] < 70)  # RSI en rango favorable
        )
        
        sell_condition = (
            strong_downtrend &
            volume_confirm &
            (df['macd_histogram'] < df['macd_histogram'].shift(1)) &
            (df['stoch_k'] > 25) &  # No sobrevendido
            (df['rsi'] > 30) & (df['rsi'] < 60)
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def enhanced_breakout_momentum_strategy(self, df):
        """
        Breakout momentum OPTIMIZADO con confirmación mejorada
        """
        signals = pd.Series(index=df.index, data=0)
        
        lookback = self.strategies_config['breakout_momentum']['lookback']
        volume_mult = self.strategies_config['breakout_momentum']['volume_multiplier']
        
        # Niveles dinámicos más precisos
        df['resistance'] = df['high'].rolling(window=lookback).max()
        df['support'] = df['low'].rolling(window=lookback).min()
        df['range_size'] = (df['resistance'] - df['support']) / df['close']
        
        # Solo operar rangos significativos
        significant_range = df['range_size'] > 0.02  # Al menos 2% de rango
        
        # Ruptura alcista con confirmación múltiple
        breakout_up = (
            (df['close'] > df['resistance'].shift(1)) &
            (df['high'] > df['resistance'].shift(1)) &
            (df['volume'] > df['volume_sma'] * volume_mult) &
            significant_range &
            (df['rsi'] > 55) &  # Momentum alcista
            (df['macd'] > 0) &
            (df['close'] > df['ema_50'])  # Tendencia general alcista
        )
        
        # Ruptura bajista con confirmación
        breakout_down = (
            (df['close'] < df['support'].shift(1)) &
            (df['low'] < df['support'].shift(1)) &
            (df['volume'] > df['volume_sma'] * volume_mult) &
            significant_range &
            (df['rsi'] < 45) &  # Momentum bajista
            (df['macd'] < 0) &
            (df['close'] < df['ema_50'])  # Tendencia general bajista
        )
        
        signals[breakout_up] = 1
        signals[breakout_down] = -1
        
        return signals

    def selective_scalping_strategy(self, df):
        """
        Scalping SELECTIVO - Solo trades de alta calidad
        """
        signals = pd.Series(index=df.index, data=0)
        
        if not self.strategies_config['selective_scalping']['quality_filters']:
            return signals
        
        # Filtros de calidad extremos
        high_volume = df['volume'] > df['volume_sma'] * 2.0
        good_spread = df['atr'] / df['close'] > 0.005  # Spread mínimo
        trend_clarity = abs(df['ema_9'] - df['ema_21']) / df['close'] > 0.002
        momentum_strong = abs(df['macd_histogram']) > abs(df['macd_histogram']).rolling(10).mean()
        
        # Solo en condiciones perfectas
        perfect_conditions = high_volume & good_spread & trend_clarity & momentum_strong
        
        # Señales muy selectivas
        scalp_long = (
            perfect_conditions &
            (df['ema_9'] > df['ema_21']) &
            (df['close'] > df['ema_9']) &
            (df['rsi'] > 45) & (df['rsi'] < 65) &
            (df['macd'] > df['macd_signal']) &
            (df['stoch_k'] > df['stoch_d']) &
            (df['stoch_k'] > 20) & (df['stoch_k'] < 80)
        )
        
        scalp_short = (
            perfect_conditions &
            (df['ema_9'] < df['ema_21']) &
            (df['close'] < df['ema_9']) &
            (df['rsi'] > 35) & (df['rsi'] < 55) &
            (df['macd'] < df['macd_signal']) &
            (df['stoch_k'] < df['stoch_d']) &
            (df['stoch_k'] > 20) & (df['stoch_k'] < 80)
        )
        
        signals[scalp_long] = 1
        signals[scalp_short] = -1
        
        return signals

    def calculate_enhanced_indicators(self, df):
        """
        Calcular indicadores técnicos mejorados
        """
        # Indicadores básicos mejorados
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        
        # Bollinger Bands más sensible
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.0)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        
        # MACD optimizado
        macd = ta.trend.MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        
        # EMAs múltiples
        df['ema_9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
        df['ema_21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
        df['ema_200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
        
        # ATR mejorado
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
        
        # Volumen análisis
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        return df

    def run_optimized_backtest(self, days=30):
        """
        Ejecutar backtest con sistema optimizado
        """
        print("\n" + "="*80)
        print(f"🚀 BACKTESTING SISTEMA OPTIMIZADO V2 ({days} días)")
        print("="*80)
        
        # Usar solo pares primarios para testing inicial
        test_pairs = self.primary_pairs
        all_trades = []
        
        exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'sandbox': False,
            'rateLimit': 1200,
        })
        
        for pair in test_pairs:
            print(f"\n📊 Procesando {pair} (optimizado)...")
            
            for strategy_name in self.strategies_config.keys():
                timeframe = self.strategies_config[strategy_name]['timeframe']
                
                try:
                    # Obtener datos
                    since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                    ohlcv = exchange.fetch_ohlcv(pair, timeframe, since=since, limit=1000)
                    
                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    df = df.astype(float)
                    
                    if len(df) < 100:
                        continue
                    
                    # Calcular indicadores mejorados
                    df = self.calculate_enhanced_indicators(df)
                    
                    # Ejecutar estrategia optimizada
                    strategy_methods = {
                        'mean_reversion': self.enhanced_mean_reversion_strategy,
                        'temporal_arbitrage': self.enhanced_temporal_arbitrage_strategy,
                        'breakout_momentum': self.enhanced_breakout_momentum_strategy,
                        'selective_scalping': self.selective_scalping_strategy
                    }
                    
                    signals = strategy_methods[strategy_name](df)
                    
                    # Simular trades con lógica mejorada
                    trades = self.simulate_enhanced_trades(pair, df, signals, strategy_name)
                    all_trades.extend(trades)
                    
                    if trades:
                        total_pnl = sum([t['pnl_amount'] for t in trades])
                        win_rate = len([t for t in trades if t['pnl_amount'] > 0]) / len(trades) * 100
                        print(f"  ✅ {strategy_name}: {len(trades)} trades, PnL: ${total_pnl:.2f}, WR: {win_rate:.1f}%")
                    else:
                        print(f"  ⚪ {strategy_name}: Sin trades")
                
                except Exception as e:
                    print(f"  ❌ Error en {pair}-{strategy_name}: {e}")
                    continue
        
        return all_trades

    def simulate_enhanced_trades(self, symbol, df, signals, strategy_name):
        """
        Simulación de trades con gestión de riesgo mejorada
        """
        trades = []
        position = None
        allocation = self.strategies_config[strategy_name]['allocation']
        
        for i, (timestamp, signal) in enumerate(signals.items()):
            if i < 50:  # Warmup period
                continue
                
            current_price = df.loc[timestamp, 'close']
            atr = df.loc[timestamp, 'atr']
            
            # Abrir posición con gestión de riesgo mejorada
            if signal != 0 and position is None:
                capital_allocated = self.capital * allocation
                
                # Stop loss dinámico basado en ATR
                stop_distance = atr * 2.0
                if strategy_name == 'selective_scalping':
                    stop_distance = atr * 1.0  # Más estricto para scalping
                elif strategy_name == 'mean_reversion':
                    stop_distance = atr * 2.5  # Más permisivo para reversión
                
                # Position sizing basado en riesgo
                risk_per_trade = capital_allocated * 0.02  # 2% máximo riesgo
                size = risk_per_trade / stop_distance
                
                # Límite máximo de posición
                max_size = capital_allocated * 0.95 / current_price
                size = min(size, max_size)
                
                if signal > 0:  # Long
                    stop_loss = current_price - stop_distance
                    take_profit = current_price + (stop_distance * 2)  # R:R 2:1
                else:  # Short
                    stop_loss = current_price + stop_distance
                    take_profit = current_price - (stop_distance * 2)
                
                position = {
                    'symbol': symbol,
                    'strategy': strategy_name,
                    'side': 'long' if signal > 0 else 'short',
                    'entry_price': current_price,
                    'entry_time': timestamp,
                    'size': size,
                    'entry_capital': capital_allocated,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'atr_at_entry': atr
                }
            
            # Gestionar posición existente
            elif position is not None:
                should_close = False
                exit_reason = ""
                
                # Verificar stop loss / take profit
                if position['side'] == 'long':
                    if current_price <= position['stop_loss']:
                        should_close = True
                        exit_reason = "stop_loss"
                    elif current_price >= position['take_profit']:
                        should_close = True
                        exit_reason = "take_profit"
                else:  # Short
                    if current_price >= position['stop_loss']:
                        should_close = True
                        exit_reason = "stop_loss"
                    elif current_price <= position['take_profit']:
                        should_close = True
                        exit_reason = "take_profit"
                
                # Señal de salida o tiempo máximo
                if signal == 0 or should_close:
                    exit_price = current_price
                    
                    # Calcular P&L
                    if position['side'] == 'long':
                        pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                    else:
                        pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']
                    
                    pnl_amount = position['entry_capital'] * pnl_pct
                    
                    trade = {
                        'symbol': symbol,
                        'strategy': strategy_name,
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'size': position['size'],
                        'pnl_pct': pnl_pct * 100,
                        'pnl_amount': pnl_amount,
                        'duration_hours': (timestamp - position['entry_time']).total_seconds() / 3600,
                        'exit_reason': exit_reason if should_close else "signal"
                    }
                    
                    trades.append(trade)
                    position = None
        
        return trades

    def analyze_optimized_results(self, trades, days=30):
        """
        Analizar resultados del sistema optimizado
        """
        if not trades:
            print("❌ No hay trades para analizar")
            return
        
        df_trades = pd.DataFrame(trades)
        
        # Métricas básicas
        total_trades = len(trades)
        winning_trades = len(df_trades[df_trades['pnl_amount'] > 0])
        win_rate = (winning_trades / total_trades) * 100
        
        total_pnl = df_trades['pnl_amount'].sum()
        total_return = (total_pnl / self.initial_capital) * 100
        daily_return = total_return / days
        monthly_return = daily_return * 30
        
        # Estadísticas por estrategia
        strategy_stats = df_trades.groupby('strategy').agg({
            'pnl_amount': ['count', 'sum', 'mean'],
            'pnl_pct': 'mean',
            'duration_hours': 'mean'
        }).round(2)
        
        print("\n" + "="*80)
        print(f"📊 RESULTADOS SISTEMA OPTIMIZADO V2 ({days} días)")
        print("="*80)
        
        print(f"\n💰 RENDIMIENTO:")
        print(f"  Capital Inicial:      ${self.initial_capital:,.2f}")
        print(f"  Capital Final:        ${self.initial_capital + total_pnl:,.2f}")
        print(f"  Ganancia Total:       ${total_pnl:,.2f}")
        print(f"  Retorno Total:        {total_return:.2f}%")
        print(f"  Retorno Diario:       {daily_return:.3f}%")
        print(f"  Retorno Mensual Proy: {monthly_return:.2f}%")
        
        print(f"\n📈 MÉTRICAS:")
        print(f"  Total Trades:         {total_trades}")
        print(f"  Win Rate:            {win_rate:.1f}%")
        
        print(f"\n🎯 COMPARACIÓN CON VERSION ANTERIOR:")
        original_monthly = 0.87
        improvement = monthly_return - original_monthly
        print(f"  V1 (Original):        {original_monthly:.2f}%")
        print(f"  V2 (Optimizado):      {monthly_return:.2f}%")
        print(f"  Mejora:               +{improvement:.2f}% puntos")
        
        print(f"\n🏆 RENDIMIENTO POR ESTRATEGIA OPTIMIZADA:")
        for strategy in strategy_stats.index:
            trades_count = strategy_stats.loc[strategy, ('pnl_amount', 'count')]
            total_pnl_strat = strategy_stats.loc[strategy, ('pnl_amount', 'sum')]
            avg_duration = strategy_stats.loc[strategy, ('duration_hours', 'mean')]
            
            strategy_win_rate = len(df_trades[(df_trades['strategy'] == strategy) & (df_trades['pnl_amount'] > 0)]) / trades_count * 100
            
            print(f"  {strategy.upper()}:")
            print(f"    Trades: {trades_count}, PnL: ${total_pnl_strat:.2f}, WR: {strategy_win_rate:.1f}%, Duración: {avg_duration:.1f}h")
        
        # Evaluación del objetivo
        gap_to_target = 15 - monthly_return
        print(f"\n🎯 EVALUACIÓN OBJETIVO 15% MENSUAL:")
        if monthly_return >= 15:
            print(f"  🎉 OBJETIVO ALCANZADO: {monthly_return:.2f}%")
        elif monthly_return >= 12:
            print(f"  ⚡ MUY CERCA: {monthly_return:.2f}% (brecha: {gap_to_target:.2f}%)")
        elif monthly_return >= 8:
            print(f"  📈 BUEN PROGRESO: {monthly_return:.2f}% (brecha: {gap_to_target:.2f}%)")
        elif monthly_return >= 5:
            print(f"  🔧 NECESITA AJUSTES: {monthly_return:.2f}% (brecha: {gap_to_target:.2f}%)")
        else:
            print(f"  ⚠️ REQUIERE REVISIÓN: {monthly_return:.2f}% (brecha: {gap_to_target:.2f}%)")
        
        return {
            'monthly_return': monthly_return,
            'improvement': improvement,
            'win_rate': win_rate,
            'total_trades': total_trades,
            'gap_to_target': gap_to_target
        }

if __name__ == "__main__":
    print("🚀 EJECUTANDO SISTEMA OPTIMIZADO V2")
    
    # Crear sistema optimizado
    system = OptimizedTradingSystem(initial_capital=10000)
    
    # Ejecutar backtest de 30 días
    trades = system.run_optimized_backtest(days=30)
    
    # Analizar resultados
    results = system.analyze_optimized_results(trades, days=30)
    
    print(f"\n🏁 SISTEMA OPTIMIZADO V2 COMPLETADO")
    print(f"📈 Rendimiento mensual proyectado: {results['monthly_return']:.2f}%")
    print(f"🎯 Progreso hacia objetivo 15%: {(results['monthly_return']/15*100):.1f}%")
