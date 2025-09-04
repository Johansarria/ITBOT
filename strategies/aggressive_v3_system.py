#!/usr/bin/env python3
"""
SISTEMA V3 MEJORADO - CONFIGURACIÓN AGRESIVA PARA MAYOR RENTABILIDAD
Basado en análisis de resultados, ajustado para generar más trades rentables
"""

import ccxt
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import json
import time
import warnings
warnings.filterwarnings('ignore')

class AggressiveTradingSystemV3:
    def __init__(self, initial_capital=1000):
        """
        Sistema V3 con configuración agresiva para mayor rentabilidad
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        
        # Configuración más agresiva y permisiva
        self.strategies_config = {
            'enhanced_mean_reversion': {
                'allocation': 0.60,  # Mayor asignación
                'timeframe': '15m',
                'rsi_oversold': 35,  # Más permisivo
                'rsi_overbought': 65,
                'bb_std': 1.8,  # Bandas más cercanas = más señales
                'volume_mult': 1.1,  # Muy permisivo
                'stop_loss_mult': 1.8,
                'take_profit_mult': 1.5  # Más conservador para cerrar ganancias
            },
            'trend_following': {
                'allocation': 0.40,  # Nueva estrategia basada en momentum
                'timeframe': '30m',
                'ema_fast': 8,
                'ema_slow': 21,
                'rsi_threshold': 45,  # Muy permisivo
                'volume_mult': 1.0,  # Sin filtro de volumen
                'stop_loss_mult': 2.0,
                'take_profit_mult': 2.0
            }
        }
        
        # Pares más agresivos - incluir más opciones
        self.trading_pairs = ['ETH/USDT', 'BCH/USDT', 'BNB/USDT', 'BTC/USDT', 'XRP/USDT']
        
        # Límites más permisivos
        self.max_trades_per_session = 50  # Mucho más permisivo
        self.trades_count = 0
        
        print(f"🚀 SISTEMA V3 AGRESIVO - Capital: ${initial_capital}")
        print("⚡ Configuración optimizada para máxima rentabilidad")

    def fetch_market_data(self, symbol, timeframe, days=30):
        """
        Obtener datos de mercado con período más corto para condiciones recientes
        """
        try:
            exchange = ccxt.binance({
                'apiKey': '',
                'secret': '',
                'sandbox': False,
                'rateLimit': 600,
                'enableRateLimit': True
            })
            
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            print(f"📥 {symbol} ({timeframe})...", end=" ")
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1500)
            
            if len(ohlcv) < 100:
                print("❌")
                return None
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float)
            
            print(f"✅ {len(df)}")
            return df
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def add_aggressive_indicators(self, df):
        """
        Indicadores optimizados para generar más señales
        """
        try:
            # RSI más sensible
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=10).rsi()  # Más sensible
            df['rsi_smooth'] = df['rsi'].rolling(window=2).mean()
            
            # Bollinger Bands más cercanas
            bb = ta.volatility.BollingerBands(df['close'], window=15, window_dev=1.8)  # Más sensible
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_squeeze'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            # MACD más sensible
            macd = ta.trend.MACD(df['close'], window_fast=8, window_slow=21, window_sign=5)
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_hist'] = macd.macd_diff()
            
            # EMAs rápidas para trend following
            df['ema_8'] = ta.trend.EMAIndicator(df['close'], window=8).ema_indicator()
            df['ema_21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
            df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
            
            # ATR para stops
            df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=10).average_true_range()
            
            # Volume simple
            df['vol_sma'] = df['volume'].rolling(window=10).mean()
            df['vol_ratio'] = df['volume'] / df['vol_sma']
            
            # Momentum indicators
            df['roc'] = ta.momentum.ROCIndicator(df['close'], window=5).roc()  # Rate of change
            df['stoch'] = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'], window=10).stoch()
            
            # Limpiar NaN
            df = df.fillna(method='bfill').fillna(method='ffill')
            
            return df
            
        except Exception as e:
            print(f"❌ Error en indicadores: {e}")
            return df

    def enhanced_mean_reversion_strategy(self, df):
        """
        Mean reversion más agresivo con múltiples condiciones de entrada
        """
        signals = pd.Series(index=df.index, data=0)
        config = self.strategies_config['enhanced_mean_reversion']
        
        try:
            # Filtros básicos muy permisivos
            decent_volume = df['vol_ratio'] > config['volume_mult']
            
            # Múltiples condiciones de compra (OR logic para más señales)
            buy_condition_1 = (
                (df['rsi_smooth'] < config['rsi_oversold']) &
                (df['close'] < df['bb_lower']) &
                (df['macd_hist'] > df['macd_hist'].shift(1))
            )
            
            buy_condition_2 = (
                (df['close'] < df['bb_lower'] * 1.005) &  # Muy cerca de banda inferior
                (df['rsi_smooth'] < 45) &
                (df['roc'] < -1)  # Precio bajando
            )
            
            buy_condition_3 = (
                (df['rsi_smooth'] < 40) &
                (df['stoch'] < 25) &
                (df['close'] > df['ema_50'])  # Tendencia general alcista
            )
            
            # Múltiples condiciones de venta
            sell_condition_1 = (
                (df['rsi_smooth'] > config['rsi_overbought']) &
                (df['close'] > df['bb_upper']) &
                (df['macd_hist'] < df['macd_hist'].shift(1))
            )
            
            sell_condition_2 = (
                (df['close'] > df['bb_upper'] * 0.995) &
                (df['rsi_smooth'] > 55) &
                (df['roc'] > 1)
            )
            
            sell_condition_3 = (
                (df['rsi_smooth'] > 60) &
                (df['stoch'] > 75) &
                (df['close'] < df['ema_50'])
            )
            
            # Combinar condiciones (OR para más señales)
            buy_signals = (buy_condition_1 | buy_condition_2 | buy_condition_3) & decent_volume
            sell_signals = (sell_condition_1 | sell_condition_2 | sell_condition_3) & decent_volume
            
            signals[buy_signals] = 1
            signals[sell_signals] = -1
            
        except Exception as e:
            print(f"❌ Error en mean reversion: {e}")
        
        return signals

    def trend_following_strategy(self, df):
        """
        Nueva estrategia de seguimiento de tendencia muy agresiva
        """
        signals = pd.Series(index=df.index, data=0)
        config = self.strategies_config['trend_following']
        
        try:
            # Condiciones de tendencia alcista
            uptrend = df['ema_8'] > df['ema_21']
            strong_uptrend = (df['ema_8'] > df['ema_21']) & (df['ema_21'] > df['ema_50'])
            momentum_up = df['macd'] > df['macd_signal']
            rsi_ok = df['rsi_smooth'] > config['rsi_threshold']
            
            # Condiciones de tendencia bajista  
            downtrend = df['ema_8'] < df['ema_21']
            strong_downtrend = (df['ema_8'] < df['ema_21']) & (df['ema_21'] < df['ema_50'])
            momentum_down = df['macd'] < df['macd_signal']
            rsi_down = df['rsi_smooth'] < (100 - config['rsi_threshold'])
            
            # Señales de compra - múltiples condiciones
            buy_signals = (
                (uptrend & momentum_up & rsi_ok) |
                (strong_uptrend & (df['rsi_smooth'] > 40)) |
                ((df['ema_8'] > df['ema_8'].shift(1)) & 
                 (df['close'] > df['ema_8']) & 
                 (df['roc'] > 0.5))
            )
            
            # Señales de venta
            sell_signals = (
                (downtrend & momentum_down & rsi_down) |
                (strong_downtrend & (df['rsi_smooth'] < 60)) |
                ((df['ema_8'] < df['ema_8'].shift(1)) & 
                 (df['close'] < df['ema_8']) & 
                 (df['roc'] < -0.5))
            )
            
            signals[buy_signals] = 1
            signals[sell_signals] = -1
            
        except Exception as e:
            print(f"❌ Error en trend following: {e}")
        
        return signals

    def execute_aggressive_trades(self, symbol, df, signals, strategy_name):
        """
        Ejecución de trades más agresiva con gestión de riesgo optimizada
        """
        trades = []
        position = None
        config = self.strategies_config[strategy_name]
        
        try:
            for i, (timestamp, signal) in enumerate(signals.items()):
                if i < 30 or self.trades_count >= self.max_trades_per_session:  # Warmup más corto
                    continue
                
                current_price = df.loc[timestamp, 'close']
                current_atr = df.loc[timestamp, 'atr']
                
                # Abrir posición con sizing más agresivo
                if signal != 0 and position is None:
                    allocation = config['allocation']
                    
                    # Risk más agresivo - 3% por trade
                    risk_per_trade = self.capital * 0.03
                    stop_distance = current_atr * config['stop_loss_mult']
                    
                    # Position size basado en riesgo
                    position_size = risk_per_trade / stop_distance
                    
                    # Límite máximo por asignación
                    max_size = (self.capital * allocation * 0.95) / current_price
                    position_size = min(position_size, max_size)
                    
                    if position_size > 0:
                        if signal > 0:  # Long
                            stop_loss = current_price - stop_distance
                            take_profit = current_price + (stop_distance * config['take_profit_mult'])
                        else:  # Short
                            stop_loss = current_price + stop_distance
                            take_profit = current_price - (stop_distance * config['take_profit_mult'])
                        
                        position = {
                            'symbol': symbol,
                            'strategy': strategy_name,
                            'side': 'long' if signal > 0 else 'short',
                            'entry_price': current_price,
                            'entry_time': timestamp,
                            'size': position_size,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit
                        }
                        
                        self.trades_count += 1
                
                # Gestión de posición más agresiva
                elif position is not None:
                    should_close = False
                    exit_reason = "signal"
                    
                    # Stops más estrictos
                    if position['side'] == 'long':
                        if current_price <= position['stop_loss']:
                            should_close = True
                            exit_reason = "stop_loss"
                        elif current_price >= position['take_profit']:
                            should_close = True
                            exit_reason = "take_profit"
                    else:
                        if current_price >= position['stop_loss']:
                            should_close = True
                            exit_reason = "stop_loss"
                        elif current_price <= position['take_profit']:
                            should_close = True
                            exit_reason = "take_profit"
                    
                    # Salida por señal contraria o stops
                    if signal == 0 or should_close or (signal * (1 if position['side'] == 'long' else -1) < 0):
                        # Calcular PnL
                        if position['side'] == 'long':
                            pnl_pct = (current_price - position['entry_price']) / position['entry_price']
                        else:
                            pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
                        
                        position_value = position['size'] * position['entry_price']
                        pnl_amount = position_value * pnl_pct
                        
                        trade = {
                            'symbol': symbol,
                            'strategy': strategy_name,
                            'side': position['side'],
                            'entry_price': position['entry_price'],
                            'exit_price': current_price,
                            'entry_time': position['entry_time'],
                            'exit_time': timestamp,
                            'size': position['size'],
                            'position_value': position_value,
                            'pnl_pct': pnl_pct * 100,
                            'pnl_amount': pnl_amount,
                            'duration_hours': (timestamp - position['entry_time']).total_seconds() / 3600,
                            'exit_reason': exit_reason
                        }
                        
                        trades.append(trade)
                        position = None
        
        except Exception as e:
            print(f"❌ Error ejecutando trades: {e}")
        
        return trades

    def run_aggressive_backtest(self, balance, days=30):
        """
        Backtest agresivo con período más corto para condiciones actuales
        """
        print(f"\n💰 BALANCE: ${balance} - CONFIGURACIÓN AGRESIVA")
        print("-" * 55)
        
        self.initial_capital = balance
        self.capital = balance
        self.trades_count = 0
        
        all_trades = []
        
        strategies = {
            'enhanced_mean_reversion': self.enhanced_mean_reversion_strategy,
            'trend_following': self.trend_following_strategy
        }
        
        for pair in self.trading_pairs:
            for strategy_name, strategy_func in strategies.items():
                timeframe = self.strategies_config[strategy_name]['timeframe']
                
                # Obtener datos recientes
                df = self.fetch_market_data(pair, timeframe, days)
                
                if df is None or len(df) < 150:
                    continue
                
                # Agregar indicadores
                df = self.add_aggressive_indicators(df)
                
                # Generar señales
                signals = strategy_func(df)
                
                # Ejecutar trades
                trades = self.execute_aggressive_trades(pair, df, signals, strategy_name)
                
                if trades:
                    all_trades.extend(trades)
                    pnl = sum([t['pnl_amount'] for t in trades])
                    win_rate = len([t for t in trades if t['pnl_amount'] > 0]) / len(trades) * 100
                    print(f"  ✅ {strategy_name} - {pair}: {len(trades)} trades, ${pnl:.2f}, {win_rate:.1f}% WR")
                else:
                    print(f"  ⚪ {strategy_name} - {pair}: Sin trades")
                
                time.sleep(0.1)
        
        return self.analyze_aggressive_results(all_trades, balance, days)

    def analyze_aggressive_results(self, trades, balance, days):
        """
        Análisis optimizado de resultados
        """
        if not trades:
            return {
                'balance': balance,
                'total_trades': 0,
                'total_pnl': 0,
                'monthly_return': 0,
                'win_rate': 0,
                'profit_factor': 0
            }
        
        df = pd.DataFrame(trades)
        
        # Métricas básicas
        total_trades = len(trades)
        total_pnl = df['pnl_amount'].sum()
        monthly_return = (total_pnl / balance) * (30 / days) * 100
        
        # Win rate
        winners = df[df['pnl_amount'] > 0]
        win_rate = len(winners) / total_trades * 100
        
        # Profit factor
        total_wins = winners['pnl_amount'].sum() if len(winners) > 0 else 0
        total_losses = abs(df[df['pnl_amount'] < 0]['pnl_amount'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Métricas avanzadas
        avg_win = winners['pnl_amount'].mean() if len(winners) > 0 else 0
        avg_loss = df[df['pnl_amount'] < 0]['pnl_amount'].mean() if len(df[df['pnl_amount'] < 0]) > 0 else 0
        
        results = {
            'balance': balance,
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'monthly_return': monthly_return,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'best_trade': df['pnl_amount'].max(),
            'worst_trade': df['pnl_amount'].min()
        }
        
        print(f"\n📊 RESULTADOS AGRESIVOS ${balance}:")
        print(f"  Trades: {total_trades}")
        print(f"  PnL: ${total_pnl:.2f}")
        print(f"  Mensual: {monthly_return:.2f}%")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Mejor Trade: ${results['best_trade']:.2f}")
        print(f"  Peor Trade: ${results['worst_trade']:.2f}")
        
        return results

    def run_full_aggressive_test(self):
        """
        Ejecutar prueba completa con configuración agresiva
        """
        print("🚀 INICIANDO SISTEMA V3 AGRESIVO")
        print("="*60)
        print("⚡ Optimizado para máxima generación de trades rentables")
        print("🎯 Usando datos de mercado más recientes (30 días)")
        
        balances = [500, 1000, 2000]
        results = {}
        
        for balance in balances:
            results[balance] = self.run_aggressive_backtest(balance)
            time.sleep(0.5)
        
        # Comparación final
        print("\n" + "="*80)
        print("📊 COMPARACIÓN SISTEMA AGRESIVO")
        print("="*80)
        
        print(f"\n{'Balance':<10} {'Trades':<8} {'PnL ($)':<12} {'Monthly %':<12} {'Win Rate %':<12} {'P.Factor':<10}")
        print("-" * 75)
        
        best_monthly = -999
        best_balance = 0
        
        for balance, result in results.items():
            print(f"${balance:<9} {result['total_trades']:<8} ${result['total_pnl']:<11.2f} {result['monthly_return']:<11.2f} {result['win_rate']:<11.1f} {result['profit_factor']:<10.2f}")
            
            if result['monthly_return'] > best_monthly:
                best_monthly = result['monthly_return']
                best_balance = balance
        
        print(f"\n🏆 MEJOR RENDIMIENTO:")
        if best_balance > 0:
            best = results[best_balance]
            print(f"  Balance: ${best_balance}")
            print(f"  Retorno Mensual: {best['monthly_return']:.2f}%")
            print(f"  Total Trades: {best['total_trades']}")
            print(f"  Win Rate: {best['win_rate']:.1f}%")
            print(f"  Profit Factor: {best['profit_factor']:.2f}")
        
        # Evaluación del sistema
        if best_monthly >= 10:
            print(f"\n🎉 EXCELENTE: Sistema supera objetivo con {best_monthly:.2f}% mensual")
        elif best_monthly >= 5:
            print(f"\n✅ MUY BUENO: Sistema alcanza {best_monthly:.2f}% mensual")
        elif best_monthly >= 2:
            print(f"\n⚡ BUENO: Sistema genera {best_monthly:.2f}% mensual")
        elif best_monthly >= 0:
            print(f"\n⚠️ MODERADO: Sistema break-even a {best_monthly:.2f}% mensual")
        else:
            print(f"\n❌ REQUIERE AJUSTES: Sistema pierde {abs(best_monthly):.2f}% mensual")
        
        # Guardar resultados
        with open('/home/johan/itbot_linux/strategies/V3_AGGRESSIVE_RESULTS.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Resultados guardados: V3_AGGRESSIVE_RESULTS.json")
        
        return results

if __name__ == "__main__":
    system = AggressiveTradingSystemV3()
    results = system.run_full_aggressive_test()
    print("\n🎯 BACKTESTING AGRESIVO COMPLETADO")
