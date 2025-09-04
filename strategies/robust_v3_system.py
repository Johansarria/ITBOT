#!/usr/bin/env python3
"""
SISTEMA V3 OPTIMIZADO - VERSIÓN ROBUSTA
Implementación mejorada con manejo robusto de casos edge
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

class RobustTradingSystemV3:
    def __init__(self, initial_capital=1000):
        """
        Sistema V3 robusto con manejo mejorado de errores
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        
        # Configuración más permisiva para generar más trades
        self.strategies_config = {
            'mean_reversion': {
                'allocation': 0.50,
                'timeframe': '15m',
                'rsi_oversold': 30,  # Menos estricto
                'rsi_overbought': 70,
                'bb_std': 2.0,
                'min_volume_mult': 1.3,  # Menos estricto
                'stop_loss_atr_mult': 2.0,
                'take_profit_mult': 2.0
            },
            'temporal_arbitrage': {
                'allocation': 0.35,
                'timeframe': '30m',
                'trend_strength_min': 0.005,  # Menos estricto
                'volume_confirmation': 1.2,
                'rsi_range': (30, 70),  # Más amplio
                'stop_loss_atr_mult': 2.0,
                'take_profit_mult': 2.0
            },
            'selective_breakout': {
                'allocation': 0.15,
                'timeframe': '1h',
                'lookback_period': 20,
                'volume_mult_min': 1.8,  # Menos estricto
                'range_min_pct': 0.015,  # Menos estricto
                'stop_loss_atr_mult': 1.5,
                'take_profit_mult': 2.5
            }
        }
        
        self.trading_pairs = ['ETH/USDT', 'BCH/USDT', 'BNB/USDT']
        self.max_trades_per_session = 15  # Más permisivo
        self.trades_count = 0
        
        print(f"🚀 SISTEMA V3 ROBUSTO - Capital: ${initial_capital}")

    def fetch_binance_data(self, symbol, timeframe, days=45):
        """
        Obtener datos de Binance con manejo robusto de errores
        """
        try:
            exchange = ccxt.binance({
                'apiKey': '',
                'secret': '',
                'sandbox': False,
                'rateLimit': 800,
                'enableRateLimit': True,
                'timeout': 30000
            })
            
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            limit = 500
            
            print(f"📥 {symbol} ({timeframe})...", end="")
            
            all_data = []
            current_since = since
            
            while current_since < int(datetime.now().timestamp() * 1000):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=limit)
                    if not ohlcv:
                        break
                    all_data.extend(ohlcv)
                    current_since = ohlcv[-1][0] + 1
                    time.sleep(0.15)
                except Exception as e:
                    print(f"⚠️", end="")
                    time.sleep(1)
                    break
            
            if len(all_data) < 100:
                print(" ❌ Insuficientes")
                return None
                
            df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float).dropna()
            
            print(f" ✅ {len(df)}")
            return df
            
        except Exception as e:
            print(f" ❌ Error: {e}")
            return None

    def add_technical_indicators(self, df):
        """
        Agregar indicadores técnicos básicos pero efectivos
        """
        try:
            # RSI
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.0)
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_middle'] = bb.bollinger_mavg()
            
            # MACD
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_hist'] = macd.macd_diff()
            
            # EMAs
            for period in [9, 21, 50]:
                df[f'ema_{period}'] = ta.trend.EMAIndicator(df['close'], window=period).ema_indicator()
            
            # ATR
            df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
            
            # Volume
            df['vol_sma'] = df['volume'].rolling(window=20).mean()
            df['vol_ratio'] = df['volume'] / df['vol_sma']
            
            # Llenar valores NaN
            df = df.fillna(method='bfill').fillna(method='ffill')
            
            return df
            
        except Exception as e:
            print(f"❌ Error en indicadores: {e}")
            return df

    def mean_reversion_signals(self, df):
        """
        Señales de mean reversion simplificadas pero efectivas
        """
        signals = pd.Series(index=df.index, data=0)
        config = self.strategies_config['mean_reversion']
        
        try:
            # Condiciones básicas pero efectivas
            high_volume = df['vol_ratio'] > config['min_volume_mult']
            uptrend = df['close'] > df['ema_50']
            
            # Señal de compra: RSI oversold + precio cerca banda inferior
            buy_signals = (
                (df['rsi'] < config['rsi_oversold']) &
                (df['close'] <= df['bb_lower'] * 1.01) &  # Cerca de banda inferior
                high_volume &
                uptrend &
                (df['macd_hist'] > df['macd_hist'].shift(1))  # MACD mejorando
            )
            
            # Señal de venta: RSI overbought + precio cerca banda superior  
            sell_signals = (
                (df['rsi'] > config['rsi_overbought']) &
                (df['close'] >= df['bb_upper'] * 0.99) &
                high_volume &
                (~uptrend) &
                (df['macd_hist'] < df['macd_hist'].shift(1))
            )
            
            signals[buy_signals] = 1
            signals[sell_signals] = -1
            
        except Exception as e:
            print(f"❌ Error en mean reversion: {e}")
        
        return signals

    def temporal_arbitrage_signals(self, df):
        """
        Señales de arbitraje temporal simplificadas
        """
        signals = pd.Series(index=df.index, data=0)
        config = self.strategies_config['temporal_arbitrage']
        
        try:
            # Tendencia fuerte
            strong_up = (df['ema_9'] > df['ema_21']) & (df['ema_21'] > df['ema_50'])
            strong_down = (df['ema_9'] < df['ema_21']) & (df['ema_21'] < df['ema_50'])
            
            # Confirmaciones
            vol_ok = df['vol_ratio'] > config['volume_confirmation']
            rsi_ok = (df['rsi'] > config['rsi_range'][0]) & (df['rsi'] < config['rsi_range'][1])
            macd_up = df['macd'] > df['macd_signal']
            
            # Señales
            buy_signals = strong_up & vol_ok & rsi_ok & macd_up
            sell_signals = strong_down & vol_ok & rsi_ok & (~macd_up)
            
            signals[buy_signals] = 1
            signals[sell_signals] = -1
            
        except Exception as e:
            print(f"❌ Error en temporal arbitrage: {e}")
        
        return signals

    def breakout_signals(self, df):
        """
        Señales de breakout simplificadas
        """
        signals = pd.Series(index=df.index, data=0)
        config = self.strategies_config['selective_breakout']
        
        try:
            # Niveles de soporte/resistencia
            lookback = config['lookback_period']
            df['resistance'] = df['high'].rolling(window=lookback).max()
            df['support'] = df['low'].rolling(window=lookback).min()
            
            # Filtros
            big_volume = df['vol_ratio'] > config['volume_mult_min']
            range_ok = (df['resistance'] - df['support']) / df['close'] > config['range_min_pct']
            
            # Rupturas
            breakout_up = (
                (df['close'] > df['resistance'].shift(1)) &
                big_volume &
                range_ok &
                (df['rsi'] > 50) &
                (df['close'] > df['ema_21'])
            )
            
            breakout_down = (
                (df['close'] < df['support'].shift(1)) &
                big_volume &
                range_ok &
                (df['rsi'] < 50) &
                (df['close'] < df['ema_21'])
            )
            
            signals[breakout_up] = 1
            signals[breakout_down] = -1
            
        except Exception as e:
            print(f"❌ Error en breakout: {e}")
        
        return signals

    def simulate_trades(self, symbol, df, signals, strategy_name):
        """
        Simular trades de manera robusta
        """
        trades = []
        position = None
        config = self.strategies_config[strategy_name]
        
        try:
            for i, (timestamp, signal) in enumerate(signals.items()):
                if i < 50 or self.trades_count >= self.max_trades_per_session:
                    continue
                
                current_price = df.loc[timestamp, 'close']
                current_atr = df.loc[timestamp, 'atr']
                
                # Abrir posición
                if signal != 0 and position is None:
                    allocation = config['allocation']
                    capital_for_strategy = self.capital * allocation
                    
                    # Position size básico: 2% de riesgo
                    risk_per_trade = self.capital * 0.02
                    stop_distance = current_atr * config['stop_loss_atr_mult']
                    position_size = min(
                        risk_per_trade / stop_distance,
                        capital_for_strategy * 0.9 / current_price
                    )
                    
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
                
                # Cerrar posición
                elif position is not None:
                    should_close = False
                    exit_reason = "signal"
                    
                    # Verificar stop loss y take profit
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
                    
                    if signal == 0 or should_close:
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
            print(f"❌ Error simulando trades: {e}")
        
        return trades

    def run_balance_test(self, balance, days=45):
        """
        Ejecutar prueba para un balance específico
        """
        print(f"\n💰 PROBANDO BALANCE: ${balance}")
        print("-" * 50)
        
        self.initial_capital = balance
        self.capital = balance
        self.trades_count = 0
        
        all_trades = []
        
        # Estrategias a probar
        strategies = {
            'mean_reversion': self.mean_reversion_signals,
            'temporal_arbitrage': self.temporal_arbitrage_signals,
            'selective_breakout': self.breakout_signals
        }
        
        for pair in self.trading_pairs:
            for strategy_name, strategy_func in strategies.items():
                timeframe = self.strategies_config[strategy_name]['timeframe']
                
                # Obtener datos
                df = self.fetch_binance_data(pair, timeframe, days)
                
                if df is None or len(df) < 200:
                    continue
                
                # Agregar indicadores
                df = self.add_technical_indicators(df)
                
                # Generar señales
                signals = strategy_func(df)
                
                # Simular trades
                trades = self.simulate_trades(pair, df, signals, strategy_name)
                
                if trades:
                    all_trades.extend(trades)
                    pnl = sum([t['pnl_amount'] for t in trades])
                    win_rate = len([t for t in trades if t['pnl_amount'] > 0]) / len(trades) * 100
                    print(f"  ✅ {strategy_name} - {pair}: {len(trades)} trades, ${pnl:.2f}, {win_rate:.1f}% WR")
                else:
                    print(f"  ⚪ {strategy_name} - {pair}: Sin trades")
                
                time.sleep(0.2)  # Rate limiting
        
        return self.analyze_results(all_trades, balance, days)

    def analyze_results(self, trades, balance, days):
        """
        Analizar resultados de manera robusta
        """
        if not trades:
            return {
                'balance': balance,
                'total_trades': 0,
                'total_pnl': 0,
                'total_return': 0,
                'monthly_return': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'avg_trade': 0
            }
        
        # Convertir a DataFrame
        df = pd.DataFrame(trades)
        
        # Métricas básicas
        total_trades = len(trades)
        total_pnl = df['pnl_amount'].sum()
        total_return = (total_pnl / balance) * 100
        monthly_return = (total_return / days) * 30
        
        # Win rate
        winners = df[df['pnl_amount'] > 0]
        losers = df[df['pnl_amount'] < 0]
        win_rate = len(winners) / total_trades * 100
        
        # Profit factor
        total_wins = winners['pnl_amount'].sum() if len(winners) > 0 else 0
        total_losses = abs(losers['pnl_amount'].sum()) if len(losers) > 0 else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Drawdown aproximado
        cumulative = df.sort_values('entry_time')['pnl_amount'].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = ((cumulative - running_max) / balance * 100).min()
        max_drawdown = abs(drawdown)
        
        # Trade promedio
        avg_trade = total_pnl / total_trades
        
        results = {
            'balance': balance,
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'monthly_return': monthly_return,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'avg_trade': avg_trade,
            'avg_win': winners['pnl_amount'].mean() if len(winners) > 0 else 0,
            'avg_loss': losers['pnl_amount'].mean() if len(losers) > 0 else 0,
            'trades_data': trades
        }
        
        # Mostrar resultados
        print(f"\n📊 RESULTADOS ${balance}:")
        print(f"  Trades: {total_trades}")
        print(f"  PnL: ${total_pnl:.2f} ({total_return:.2f}%)")
        print(f"  Mensual: {monthly_return:.2f}%")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Profit Factor: {profit_factor:.2f}")
        print(f"  Max DD: {max_drawdown:.2f}%")
        print(f"  Trade Prom: ${avg_trade:.2f}")
        
        return results

    def run_multi_balance_test(self):
        """
        Ejecutar pruebas con múltiples balances
        """
        print("🚀 INICIANDO PRUEBAS MULTI-BALANCE SISTEMA V3")
        print("="*60)
        
        balances = [500, 1000, 2000]
        results = {}
        
        for balance in balances:
            results[balance] = self.run_balance_test(balance)
            time.sleep(1)
        
        # Mostrar comparación
        print("\n" + "="*80)
        print("📊 COMPARACIÓN FINAL")
        print("="*80)
        
        print(f"\n{'Balance':<10} {'Trades':<8} {'PnL ($)':<10} {'Return %':<10} {'Monthly %':<12} {'Win Rate %':<12} {'Profit Factor':<14}")
        print("-" * 80)
        
        for balance, result in results.items():
            print(f"${balance:<9} {result['total_trades']:<8} ${result['total_pnl']:<9.2f} {result['total_return']:<9.2f} {result['monthly_return']:<11.2f} {result['win_rate']:<11.1f} {result['profit_factor']:<14.2f}")
        
        # Encontrar mejor resultado
        best_monthly = max([r['monthly_return'] for r in results.values()])
        best_balance = [b for b, r in results.items() if r['monthly_return'] == best_monthly][0]
        
        print(f"\n🏆 MEJOR RENDIMIENTO:")
        print(f"  Balance: ${best_balance}")
        print(f"  Retorno Mensual: {best_monthly:.2f}%")
        print(f"  Profit Factor: {results[best_balance]['profit_factor']:.2f}")
        print(f"  Win Rate: {results[best_balance]['win_rate']:.1f}%")
        
        # Evaluación
        if best_monthly >= 8:
            print(f"\n✅ EXCELENTE: Sistema supera expectativas")
        elif best_monthly >= 5:
            print(f"\n⚡ BUENO: Sistema funciona bien")
        elif best_monthly >= 3:
            print(f"\n⚠️ MODERADO: Sistema necesita ajustes")
        else:
            print(f"\n❌ BAJO: Sistema requiere revisión")
        
        # Guardar resultados
        with open('/home/johan/itbot_linux/strategies/V3_ROBUST_RESULTS.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Resultados guardados: V3_ROBUST_RESULTS.json")
        
        return results

if __name__ == "__main__":
    system = RobustTradingSystemV3()
    results = system.run_multi_balance_test()
    print("\n🎯 PRUEBAS COMPLETADAS")
