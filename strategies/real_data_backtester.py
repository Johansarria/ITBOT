#!/usr/bin/env python3
"""
BACKTESTING CON DATOS REALES DE BINANCE - ÚLTIMOS 90 DÍAS
Sistema completo para validar rendimiento real de nuestras 5 estrategias
"""

import ccxt
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import time
import json
import warnings
warnings.filterwarnings('ignore')

class RealDataBacktester:
    def __init__(self, initial_capital=10000):
        """
        Inicializar backtester con datos reales de Binance
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades_history = []
        self.equity_curve = []
        self.exchange = ccxt.binance({
            'apiKey': '',  # No necesitamos API key para datos públicos
            'secret': '',
            'sandbox': False,
            'rateLimit': 1200,
        })
        
        # Configuración de estrategias
        self.strategies_config = {
            'scalping': {'allocation': 0.35, 'timeframe': '5m', 'lookback': 20},
            'mean_reversion': {'allocation': 0.25, 'timeframe': '15m', 'lookback': 50},
            'breakout_momentum': {'allocation': 0.20, 'timeframe': '1h', 'lookback': 30},
            'temporal_arbitrage': {'allocation': 0.15, 'timeframe': '30m', 'lookback': 40},
            'volatility_trading': {'allocation': 0.05, 'timeframe': '4h', 'lookback': 25},
            'tsmom': {'allocation': 0.20, 'timeframe': '1h', 'lookback': 50}
        }
        
        # Pares de alta liquidez para testing
        self.trading_pairs = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'XRP/USDT',
            'DOT/USDT', 'UNI/USDT', 'LINK/USDT', 'LTC/USDT', 'BCH/USDT'
        ]
        
        print("🔄 Inicializando Backtester con datos reales de Binance...")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print(f"📊 Pares a analizar: {len(self.trading_pairs)}")

    def fetch_historical_data(self, symbol, timeframe, days=90):
        """
        Obtener datos históricos reales de Binance
        """
        try:
            # Calcular timestamp de inicio (90 días atrás)
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            print(f"📥 Descargando datos: {symbol} ({timeframe}) - {days} días...")
            
            # Obtener datos en chunks para evitar límites de API
            all_ohlcv = []
            current_since = since
            
            while current_since < int(datetime.now().timestamp() * 1000):
                try:
                    ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=1000)
                    if not ohlcv:
                        break
                    all_ohlcv.extend(ohlcv)
                    current_since = ohlcv[-1][0] + 1
                    time.sleep(0.1)  # Rate limiting
                except Exception as e:
                    print(f"⚠️ Error obteniendo datos: {e}")
                    time.sleep(1)
                    continue
            
            # Convertir a DataFrame
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float)
            
            print(f"✅ Datos obtenidos: {len(df)} velas para {symbol}")
            return df
            
        except Exception as e:
            print(f"❌ Error obteniendo datos para {symbol}: {e}")
            return None

    def calculate_technical_indicators(self, df):
        """
        Calcular indicadores técnicos necesarios para las estrategias
        """
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], window=20)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        
        # Moving Averages
        df['ema_9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
        df['ema_21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
        df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
        df['ema_200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
        
        # ATR para volatilidad
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        return df

    def scalping_strategy(self, df):
        """
        Estrategia de Scalping - Movimientos rápidos intraday
        """
        signals = pd.Series(index=df.index, data=0)
        
        # Condiciones de compra (scalping alcista)
        buy_condition = (
            (df['ema_9'] > df['ema_21']) &  # Tendencia alcista corto plazo
            (df['close'] > df['ema_9']) &   # Precio sobre EMA rápida
            (df['rsi'] > 30) & (df['rsi'] < 70) &  # RSI en rango medio
            (df['volume'] > df['volume_sma'] * 1.2) &  # Volumen elevado
            (df['macd'] > df['macd_signal'])  # MACD positivo
        )
        
        # Condiciones de venta (scalping bajista)
        sell_condition = (
            (df['ema_9'] < df['ema_21']) &  # Tendencia bajista corto plazo
            (df['close'] < df['ema_9']) &   # Precio bajo EMA rápida
            (df['rsi'] > 30) & (df['rsi'] < 70) &  # RSI en rango medio
            (df['volume'] > df['volume_sma'] * 1.2) &  # Volumen elevado
            (df['macd'] < df['macd_signal'])  # MACD negativo
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def mean_reversion_strategy(self, df):
        """
        Estrategia de Reversión a la Media - Bollinger Bands + RSI
        """
        signals = pd.Series(index=df.index, data=0)
        
        # Señal de compra: precio toca banda inferior + RSI sobreventa
        buy_condition = (
            (df['close'] <= df['bb_lower']) &  # Precio en banda inferior
            (df['rsi'] < 35) &  # RSI sobreventa
            (df['close'] > df['ema_200'])  # Tendencia general alcista
        )
        
        # Señal de venta: precio toca banda superior + RSI sobrecompra
        sell_condition = (
            (df['close'] >= df['bb_upper']) &  # Precio en banda superior
            (df['rsi'] > 65) &  # RSI sobrecompra
            (df['close'] < df['ema_200'])  # Tendencia general bajista
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def breakout_momentum_strategy(self, df):
        """
        Estrategia de Momentum - Rupturas con confirmación
        """
        signals = pd.Series(index=df.index, data=0)
        
        # Calcular niveles de soporte y resistencia
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        
        # Ruptura alcista
        buy_condition = (
            (df['close'] > df['resistance'].shift(1)) &  # Ruptura de resistencia
            (df['volume'] > df['volume_sma'] * 1.5) &  # Alto volumen
            (df['rsi'] > 50) &  # RSI alcista
            (df['macd'] > 0)  # MACD positivo
        )
        
        # Ruptura bajista
        sell_condition = (
            (df['close'] < df['support'].shift(1)) &  # Ruptura de soporte
            (df['volume'] > df['volume_sma'] * 1.5) &  # Alto volumen
            (df['rsi'] < 50) &  # RSI bajista
            (df['macd'] < 0)  # MACD negativo
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def temporal_arbitrage_strategy(self, df):
        """
        Estrategia de Arbitraje Temporal - Diferencias entre timeframes
        """
        signals = pd.Series(index=df.index, data=0)
        
        # Divergencias entre EMAs de diferentes períodos
        short_trend = df['ema_9'] > df['ema_21']
        medium_trend = df['ema_21'] > df['ema_50']
        long_trend = df['ema_50'] > df['ema_200']
        
        # Alineación de tendencias alcistas
        buy_condition = (
            short_trend & medium_trend & long_trend &
            (df['stoch_k'] < 80) &  # No sobrecomprado
            (df['volume'] > df['volume_sma'])
        )
        
        # Alineación de tendencias bajistas
        sell_condition = (
            (~short_trend) & (~medium_trend) & (~long_trend) &
            (df['stoch_k'] > 20) &  # No sobrevendido
            (df['volume'] > df['volume_sma'])
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def volatility_trading_strategy(self, df):
        """
        Estrategia de Trading de Volatilidad - ATR + Bollinger
        """
        signals = pd.Series(index=df.index, data=0)
        
        # Calcular volatilidad
        df['volatility'] = df['atr'] / df['close'] * 100
        df['vol_ma'] = df['volatility'].rolling(window=20).mean()
        
        # Trading en alta volatilidad
        high_vol_condition = df['volatility'] > df['vol_ma'] * 1.3
        
        # Compra en expansión de volatilidad con momentum alcista
        buy_condition = (
            high_vol_condition &
            (df['close'] > df['bb_middle']) &  # Precio sobre media
            (df['macd_histogram'] > df['macd_histogram'].shift(1))  # MACD creciente
        )
        
        # Venta en expansión de volatilidad con momentum bajista
        sell_condition = (
            high_vol_condition &
            (df['close'] < df['bb_middle']) &  # Precio bajo media
            (df['macd_histogram'] < df['macd_histogram'].shift(1))  # MACD decreciente
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def tsmom_strategy(self, df):
        """
        Estrategia Time Series Momentum (TSMOM)
        - Direccionalidad basada en momentum de serie temporal (precio vs. lookback)
        - Filtros de tendencia multi-EMA y confirmación de momentum (MACD, RSI)
        - Filtro de volumen para evitar señales en baja liquidez
        Señales: 1 (long), -1 (short), 0 (flat)
        """
        signals = pd.Series(index=df.index, data=0)
        
        # Parámetros
        lookback = 50
        try:
            # si existe config en el backtester, úsala
            lookback = int(self.strategies_config.get('tsmom', {}).get('lookback', lookback))
        except Exception:
            pass
        
        # Momentum de serie temporal (retorno simple sobre lookback)
        ts_mom = (df['close'] / df['close'].shift(lookback)) - 1.0
        
        # Filtros de tendencia y momentum
        trend_up = (df['ema_21'] > df['ema_50']) & (df['ema_50'] > df['ema_200'])
        trend_down = (df['ema_21'] < df['ema_50']) & (df['ema_50'] < df['ema_200'])
        price_above_ma = df['close'] > df['ema_200']
        price_below_ma = df['close'] < df['ema_200']
        macd_up = df['macd_histogram'] > 0
        macd_down = df['macd_histogram'] < 0
        macd_improving = df['macd_histogram'] > df['macd_histogram'].shift(1)
        macd_worsening = df['macd_histogram'] < df['macd_histogram'].shift(1)
        rsi_bull = df['rsi'] > 55
        rsi_bear = df['rsi'] < 45
        vol_filter = df['volume'] > df['volume_sma']
        
        # Condiciones
        buy_condition = (
            (ts_mom > 0) & trend_up & price_above_ma & macd_up & macd_improving & rsi_bull & vol_filter
        )
        sell_condition = (
            (ts_mom < 0) & trend_down & price_below_ma & macd_down & macd_worsening & rsi_bear & vol_filter
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def execute_strategy(self, symbol, df, strategy_name, long_only=False):
        """
        Ejecutar estrategia específica y calcular trades
        """
        strategy_methods = {
            'scalping': self.scalping_strategy,
            'mean_reversion': self.mean_reversion_strategy,
            'breakout_momentum': self.breakout_momentum_strategy,
            'temporal_arbitrage': self.temporal_arbitrage_strategy,
            'volatility_trading': self.volatility_trading_strategy,
            'tsmom': self.tsmom_strategy,
        }
        
        if strategy_name not in strategy_methods:
            return []
        
        # Obtener señales
        signals = strategy_methods[strategy_name](df)
        
        # Forzar long-only si se solicita (señales -1 pasan a 0/flat)
        if long_only:
            signals = signals.mask(signals < 0, 0)
        # Ejecutar trades basado en señales
        trades = []
        position = None
        
        for i, (timestamp, signal) in enumerate(signals.items()):
            if i < 50:  # Skip initial rows for indicator warmup
                continue
                
            current_price = df.loc[timestamp, 'close']
            
            # Abrir posición
            if signal != 0 and position is None:
                allocation = self.strategies_config[strategy_name]['allocation']
                capital_allocated = self.capital * allocation
                size = capital_allocated * 0.95 / current_price  # 95% para fees
                
                position = {
                    'symbol': symbol,
                    'strategy': strategy_name,
                    'side': 'long' if signal > 0 else 'short',
                    'entry_price': current_price,
                    'entry_time': timestamp,
                    'size': size,
                    'entry_capital': capital_allocated
                }
                
            # Cerrar posición
            elif signal == 0 and position is not None:
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
                    'duration': (timestamp - position['entry_time']).total_seconds() / 3600  # horas
                }
                
                trades.append(trade)
                position = None
        
        return trades

    def run_full_backtest(self, days=90, strategies=None, long_only=False):
        """
        Ejecutar backtest completo con todas o algunas estrategias
        - strategies: lista opcional de nombres de estrategias a ejecutar
        - long_only: si True, ignora cortos (señales -1 se convierten a 0)
        """
        print("\n" + "="*80)
        print(f"🚀 INICIANDO BACKTEST CON DATOS REALES DE BINANCE ({days} DÍAS)")
        print("="*80)
        
        all_trades = []
        
        for pair in self.trading_pairs:
            print(f"\n📊 Procesando {pair}...")
            
            strategies_to_run = strategies or list(self.strategies_config.keys())
            for strategy_name in strategies_to_run:
                timeframe = self.strategies_config[strategy_name]['timeframe']
                
                # Obtener datos históricos
                df = self.fetch_historical_data(pair, timeframe, days=days)
                
                if df is None or len(df) < 100:
                    print(f"⚠️ Datos insuficientes para {pair} en {timeframe}")
                    continue
                
                # Calcular indicadores
                df = self.calculate_technical_indicators(df)
                
                # Ejecutar estrategia
                trades = self.execute_strategy(pair, df, strategy_name, long_only=long_only)
                all_trades.extend(trades)
                
                if trades:
                    total_pnl = sum([t['pnl_amount'] for t in trades])
                    win_rate = len([t for t in trades if t['pnl_amount'] > 0]) / len(trades) * 100
                    print(f"  ✅ {strategy_name}: {len(trades)} trades, PnL: ${total_pnl:.2f}, WR: {win_rate:.1f}%")
                else:
                    print(f"  ⚪ {strategy_name}: Sin trades")
        
        return all_trades

    def analyze_results(self, trades, days=90):
        """
        Analizar resultados del backtest
        """
        if not trades:
            print("❌ No hay trades para analizar")
            return
        
        df_trades = pd.DataFrame(trades)
        
        # Métricas generales
        total_trades = len(trades)
        winning_trades = len(df_trades[df_trades['pnl_amount'] > 0])
        losing_trades = len(df_trades[df_trades['pnl_amount'] < 0])
        win_rate = (winning_trades / total_trades) * 100
        
        total_pnl = df_trades['pnl_amount'].sum()
        total_return = (total_pnl / self.initial_capital) * 100
        
        avg_win = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount'].mean()
        avg_loss = df_trades[df_trades['pnl_amount'] < 0]['pnl_amount'].mean()
        profit_factor = abs(avg_win * winning_trades) / abs(avg_loss * losing_trades) if losing_trades > 0 else float('inf')
        
        # Análisis por estrategia
        strategy_stats = df_trades.groupby('strategy').agg({
            'pnl_amount': ['count', 'sum', 'mean'],
            'pnl_pct': 'mean',
            'duration': 'mean'
        }).round(2)
        
        # Análisis por par
        pair_stats = df_trades.groupby('symbol').agg({
            'pnl_amount': ['count', 'sum'],
            'pnl_pct': 'mean'
        }).round(2)
        
        # Drawdown máximo
        df_trades_sorted = df_trades.sort_values('entry_time')
        cumulative_pnl = df_trades_sorted['pnl_amount'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - running_max) / self.initial_capital * 100
        max_drawdown = drawdown.min()
        
        # Proyección mensual
        days_in_backtest = days
        daily_return = total_return / days_in_backtest
        monthly_return = daily_return * 30
        
        # Mostrar resultados
        print("\n" + "="*80)
        print(f"📊 RESULTADOS DEL BACKTEST - DATOS REALES BINANCE ({days} DÍAS)")
        print("="*80)
        
        print(f"\n💰 RENDIMIENTO GENERAL:")
        print(f"  Capital Inicial:      ${self.initial_capital:,.2f}")
        print(f"  Capital Final:        ${self.initial_capital + total_pnl:,.2f}")
        print(f"  Ganancia Total:       ${total_pnl:,.2f}")
        print(f"  Retorno Total:        {total_return:.2f}%")
        print(f"  Retorno Mensual Prom: {monthly_return:.2f}%")
        
        print(f"\n📈 MÉTRICAS DE TRADING:")
        print(f"  Total Trades:         {total_trades}")
        print(f"  Trades Ganadores:     {winning_trades}")
        print(f"  Trades Perdedores:    {losing_trades}")
        print(f"  Win Rate:            {win_rate:.1f}%")
        print(f"  Ganancia Promedio:    ${avg_win:.2f}")
        print(f"  Pérdida Promedio:     ${avg_loss:.2f}")
        print(f"  Profit Factor:        {profit_factor:.2f}")
        print(f"  Drawdown Máximo:      {max_drawdown:.2f}%")
        
        # Guardar resultados en archivo JSON local (ruta relativa cross-platform)
        try:
            results = {
                'days': days,
                'initial_capital': self.initial_capital,
                'total_pnl': float(total_pnl),
                'total_return_pct': float(total_return),
                'monthly_return_pct': float(monthly_return),
                'win_rate_pct': float(win_rate),
                'profit_factor': float(profit_factor),
                'max_drawdown_pct': float(max_drawdown),
                'strategy_stats': df_trades.groupby('strategy')['pnl_amount'].sum().to_dict(),
                'pair_stats': df_trades.groupby('symbol')['pnl_amount'].sum().to_dict(),
            }
            import os, json
            out_dir = os.path.join(os.path.dirname(__file__))
            out_file = os.path.join(out_dir, f"REAL_BACKTEST_RESULTS_{days}D.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Resultados guardados en: {out_file}")
        except Exception as e:
            print(f"\n⚠️ No se pudieron guardar los resultados: {e}")
        
        # Mostrar resultados por estrategia y por par
        print("\n🎯 RENDIMIENTO POR ESTRATEGIA:")
        for strat, group in df_trades.groupby('strategy'):
            pnl = group['pnl_amount'].sum()
            wr = (len(group[group['pnl_amount'] > 0]) / len(group)) * 100
            dur = group['duration'].mean()
            print(f"  {strat.upper()}:\n    Trades: {len(group)}, PnL: ${pnl:.2f}, WR: {wr:.1f}%, Duración: {dur:.1f}h")
        
        print("\n🏆 TOP 5 PARES MÁS RENTABLES:")
        top_pairs = df_trades.groupby('symbol')['pnl_amount'].sum().sort_values(ascending=False).head(5)
        for sym, pnl in top_pairs.items():
            cnt = len(df_trades[df_trades['symbol'] == sym])
            print(f"  {sym}: {cnt} trades, PnL: ${pnl:.2f}")
        
        # Evaluación rápida del objetivo 15% mensual
        print("\n🎯 EVALUACIÓN DE OBJETIVO (15% MENSUAL):")
        if monthly_return >= 15:
            print("  ✅ EN RUTA: >= 15% mensual")
        else:
            print(f"  ❌ BAJO RENDIMIENTO: {monthly_return:.2f}% vs 15% target")
        
        # Guardar resultados detallados
        results_summary = {
            'backtest_period': f'{days}_days_real_binance_data',
            'initial_capital': self.initial_capital,
            'final_capital': self.initial_capital + total_pnl,
            'total_pnl': total_pnl,
            'total_return_pct': total_return,
            'monthly_return_pct': monthly_return,
            'total_trades': total_trades,
            'win_rate_pct': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown_pct': max_drawdown,
            'strategy_breakdown': strategy_stats.to_dict(),
            'top_pairs': top_pairs.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            import os, json
            out_dir = os.path.join(os.path.dirname(__file__))
            out_file = os.path.join(out_dir, f"REAL_BACKTEST_RESULTS_{days}D.json")
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(results_summary, f, indent=2, default=str)
            print(f"\n💾 Resultados guardados en: {out_file}")
        except Exception as e:
            print(f"\n⚠️ No se pudieron guardar los resultados detallados: {e}")
        print("="*80)
        
        return results_summary

if __name__ == "__main__":
    print("🚀 INICIANDO BACKTEST CON DATOS REALES DE BINANCE")
    print("📅 Período: Últimos 30 días")
    print("💰 Capital inicial: $10,000")
    
    # Crear y ejecutar backtester
    backtester = RealDataBacktester(initial_capital=10000)
    
    # Ejecutar backtest completo
    trades = backtester.run_full_backtest(days=30)
    
    # Analizar y mostrar resultados
    results = backtester.analyze_results(trades, days=30)
    
    print("\n🏁 BACKTEST COMPLETADO CON DATOS REALES")
