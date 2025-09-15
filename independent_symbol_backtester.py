#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Completo de Deteccion y Backtesting de Simbolos Independientes
Detecta senales independientes y las valida con backtesting real
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class IndependentSymbolBacktester:
    """Sistema completo de deteccion y backtesting de simbolos independientes"""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.base_url = "https://api.binance.com/api/v3"
        
        # Criterios para senales independientes
        self.independence_criteria = {
            'min_score': 0.80,           # Puntuacion minima 80%
            'volume_spike': 2.5,         # Volumen 2.5x superior
            'price_movement': 0.06,      # Movimiento > 6%
            'rsi_threshold': 20,         # RSI threshold
            'volatility_factor': 2.0,    # Volatilidad 2x
            'min_factors': 4             # Minimo 4 factores
        }
        
    def get_symbol_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Obtiene datos historicos para un simbolo"""
        try:
            end_time = int(time.time() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': '1h',
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000
            }
            
            all_data = []
            current_start = start_time
            
            while current_start < end_time:
                params['startTime'] = current_start
                response = requests.get(url, params=params)
                
                if response.status_code != 200:
                    break
                    
                data = response.json()
                if not data:
                    break
                    
                all_data.extend(data)
                current_start = data[-1][6] + 1
                time.sleep(0.1)
                
            if not all_data:
                return pd.DataFrame()
                
            df = pd.DataFrame(all_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col])
                
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"Error obteniendo datos para {symbol}: {e}")
            return pd.DataFrame()
            
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores tecnicos"""
        if len(df) < 100:
            return df
            
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['sma_20'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma_20'] + (bb_std * 2)
        df['bb_lower'] = df['sma_20'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['sma_20']
        
        # Volumen y volatilidad
        df['avg_volume'] = df['volume'].rolling(window=50).mean()
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        
        # Momentum
        df['momentum_1h'] = df['close'].pct_change(1)
        df['momentum_4h'] = df['close'].pct_change(4)
        df['momentum_24h'] = df['close'].pct_change(24)
        
        # Niveles de soporte/resistencia
        df['resistance'] = df['high'].rolling(window=50).max()
        df['support'] = df['low'].rolling(window=50).min()
        
        return df
        
    def detect_independent_signals(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """Detecta senales independientes especificas"""
        signals = []
        
        if len(df) < 100:
            return signals
            
        for i in range(100, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            independence_score = 0
            factors = []
            
            # 1. Volume Spike
            if current['volume_ratio'] >= self.independence_criteria['volume_spike']:
                independence_score += 0.25
                factors.append('Volume Spike')
                
            # 2. Price Movement
            if abs(current['momentum_1h']) >= self.independence_criteria['price_movement']:
                independence_score += 0.20
                factors.append('Strong Price Movement')
                
            # 3. RSI Conditions
            if current['rsi'] < 35 or current['rsi'] > 65:
                if i >= 105:
                    rsi_change = current['rsi'] - df.iloc[i-5]['rsi']
                    if abs(rsi_change) >= self.independence_criteria['rsi_threshold']:
                        independence_score += 0.20
                        factors.append('RSI Extreme Change')
                        
            # 4. Volatility Breakout
            avg_volatility = df['volatility'].rolling(50).mean().iloc[i]
            if current['volatility'] >= avg_volatility * self.independence_criteria['volatility_factor']:
                independence_score += 0.15
                factors.append('Volatility Breakout')
                
            # 5. MACD Signal
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal']):
                independence_score += 0.20
                factors.append('MACD Bullish Cross')
                
            # 6. Bollinger Band Break
            if current['close'] > current['bb_upper'] and current['volume_ratio'] > 1.5:
                independence_score += 0.15
                factors.append('BB Upper Break')
                
            # 7. EMA Alignment
            if (current['close'] > current['ema_12'] > current['ema_26'] > current['ema_50']):
                independence_score += 0.15
                factors.append('EMA Bullish Alignment')
                
            # 8. Resistance Break
            if (current['close'] > current['resistance'] * 1.002 and 
                current['volume_ratio'] > 1.8):
                independence_score += 0.20
                factors.append('Resistance Break')
                
            # Filtrar senales de calidad
            if (independence_score >= self.independence_criteria['min_score'] and
                len(factors) >= self.independence_criteria['min_factors']):
                
                # Calcular TP/SL dinamicos
                volatility = current['volatility']
                tp_pct = max(0.08, min(0.18, volatility * 4))
                sl_pct = max(0.03, min(0.08, volatility * 2))
                
                signal = {
                    'timestamp': df.index[i],
                    'symbol': symbol,
                    'entry_price': current['close'],
                    'independence_score': independence_score,
                    'factors': factors,
                    'tp_price': current['close'] * (1 + tp_pct),
                    'sl_price': current['close'] * (1 - sl_pct),
                    'tp_pct': tp_pct * 100,
                    'sl_pct': sl_pct * 100,
                    'volume_ratio': current['volume_ratio'],
                    'rsi': current['rsi'],
                    'momentum': current['momentum_1h'] * 100
                }
                
                signals.append(signal)
                
        return signals
        
    def backtest_signals(self, symbol: str, signals: List[Dict], df: pd.DataFrame) -> List[Dict]:
        """Realiza backtesting de las senales detectadas"""
        trades = []
        
        for signal in signals:
            entry_time = signal['timestamp']
            entry_price = signal['entry_price']
            tp_price = signal['tp_price']
            sl_price = signal['sl_price']
            
            # Buscar datos posteriores a la senal
            future_data = df[df.index > entry_time]
            
            if len(future_data) < 5:  # Necesitamos al menos 5 periodos
                continue
                
            trade_result = None
            exit_time = None
            exit_price = None
            exit_reason = None
            
            # Simular el trade
            for i, (timestamp, row) in enumerate(future_data.iterrows()):
                if i >= 72:  # Maximo 72 horas (3 dias)
                    exit_time = timestamp
                    exit_price = row['close']
                    exit_reason = 'Time Limit'
                    break
                    
                # Verificar TP
                if row['high'] >= tp_price:
                    exit_time = timestamp
                    exit_price = tp_price
                    exit_reason = 'Take Profit'
                    break
                    
                # Verificar SL
                if row['low'] <= sl_price:
                    exit_time = timestamp
                    exit_price = sl_price
                    exit_reason = 'Stop Loss'
                    break
                    
            if exit_time is not None:
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                pnl_amount = (exit_price - entry_price) * (self.initial_capital * 0.2 / entry_price)
                
                trade = {
                    'symbol': symbol,
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'tp_price': tp_price,
                    'sl_price': sl_price,
                    'exit_reason': exit_reason,
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'independence_score': signal['independence_score'],
                    'factors': signal['factors'],
                    'duration_hours': (exit_time - entry_time).total_seconds() / 3600
                }
                
                trades.append(trade)
                
        return trades
        
    def analyze_symbol_with_backtest(self, symbol: str, days: int) -> Dict:
        """Analisis completo con backtesting"""
        print(f"\n=== ANALISIS INDEPENDIENTE + BACKTEST: {symbol} ===")
        
        # Obtener datos
        df = self.get_symbol_data(symbol, days)
        if df.empty:
            return {'symbol': symbol, 'status': 'No Data'}
            
        print(f"Datos obtenidos: {len(df)} registros")
        
        # Calcular indicadores
        df = self.calculate_indicators(df)
        
        # Detectar senales independientes
        signals = self.detect_independent_signals(symbol, df)
        print(f"Senales independientes detectadas: {len(signals)}")
        
        if not signals:
            return {
                'symbol': symbol,
                'status': 'No Signals',
                'signals': 0,
                'trades': []
            }
            
        # Realizar backtesting
        trades = self.backtest_signals(symbol, signals, df)
        print(f"Trades ejecutados en backtest: {len(trades)}")
        
        # Calcular metricas
        if trades:
            winning_trades = [t for t in trades if t['pnl_pct'] > 0]
            losing_trades = [t for t in trades if t['pnl_pct'] <= 0]
            
            win_rate = len(winning_trades) / len(trades) * 100
            total_pnl = sum(t['pnl_amount'] for t in trades)
            avg_pnl = total_pnl / len(trades)
            
            best_trade = max(trades, key=lambda x: x['pnl_pct'])
            worst_trade = min(trades, key=lambda x: x['pnl_pct'])
            
            print(f"Win Rate: {win_rate:.1f}% | Total PnL: ${total_pnl:.2f} | Avg PnL: ${avg_pnl:.2f}")
            print(f"Best: {best_trade['pnl_pct']:.1f}% | Worst: {worst_trade['pnl_pct']:.1f}%")
            
            return {
                'symbol': symbol,
                'status': 'Analyzed',
                'signals': len(signals),
                'trades': trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'best_trade_pct': best_trade['pnl_pct'],
                'worst_trade_pct': worst_trade['pnl_pct']
            }
        else:
            return {
                'symbol': symbol,
                'status': 'No Valid Trades',
                'signals': len(signals),
                'trades': []
            }
            
    def run_complete_analysis(self, symbols: List[str], days: int) -> Dict:
        """Ejecuta analisis completo con backtesting"""
        print(f"\n{'='*80}")
        print(f"ANALISIS INDEPENDIENTE + BACKTESTING - {days} DIAS")
        print(f"{'='*80}")
        
        results = {}
        summary = {
            'total_symbols': len(symbols),
            'analyzed_symbols': 0,
            'total_signals': 0,
            'total_trades': 0,
            'profitable_symbols': [],
            'total_pnl': 0
        }
        
        for symbol in symbols:
            try:
                result = self.analyze_symbol_with_backtest(symbol, days)
                results[symbol] = result
                
                if result['status'] == 'Analyzed':
                    summary['analyzed_symbols'] += 1
                    summary['total_signals'] += result['signals']
                    summary['total_trades'] += len(result['trades'])
                    summary['total_pnl'] += result['total_pnl']
                    
                    if result['total_pnl'] > 0 and result['win_rate'] >= 60:
                        summary['profitable_symbols'].append({
                            'symbol': symbol,
                            'win_rate': result['win_rate'],
                            'total_pnl': result['total_pnl'],
                            'trades': len(result['trades'])
                        })
                        
            except Exception as e:
                print(f"Error analizando {symbol}: {e}")
                results[symbol] = {'symbol': symbol, 'status': 'Error', 'error': str(e)}
                
        # Ordenar simbolos rentables
        summary['profitable_symbols'].sort(key=lambda x: x['total_pnl'], reverse=True)
        
        return {'results': results, 'summary': summary}
        
    def generate_complete_report(self, analysis_results: Dict, days: int) -> str:
        """Genera reporte completo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"independent_backtest_{days}days_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"ANALISIS INDEPENDIENTE + BACKTESTING\n")
            f.write(f"Periodo: {days} dias\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
            
            summary = analysis_results['summary']
            f.write(f"RESUMEN EJECUTIVO:\n")
            f.write(f"Simbolos analizados: {summary['analyzed_symbols']}/{summary['total_symbols']}\n")
            f.write(f"Senales detectadas: {summary['total_signals']}\n")
            f.write(f"Trades ejecutados: {summary['total_trades']}\n")
            f.write(f"PnL total: ${summary['total_pnl']:.2f}\n")
            f.write(f"Simbolos rentables: {len(summary['profitable_symbols'])}\n\n")
            
            if summary['profitable_symbols']:
                f.write(f"RANKING SIMBOLOS RENTABLES:\n")
                f.write(f"{'='*60}\n")
                for i, symbol_data in enumerate(summary['profitable_symbols'], 1):
                    f.write(f"{i:2d}. {symbol_data['symbol']:10s} - ")
                    f.write(f"PnL: ${symbol_data['total_pnl']:8.2f} | ")
                    f.write(f"Win Rate: {symbol_data['win_rate']:5.1f}% | ")
                    f.write(f"Trades: {symbol_data['trades']}\n")
                    
                f.write(f"\nDETALLE SIMBOLOS RENTABLES:\n")
                f.write(f"{'='*80}\n")
                
                for symbol_data in summary['profitable_symbols']:
                    symbol = symbol_data['symbol']
                    result = analysis_results['results'][symbol]
                    
                    f.write(f"\n{symbol}:\n")
                    f.write(f"  Senales detectadas: {result['signals']}\n")
                    f.write(f"  Trades ejecutados: {len(result['trades'])}\n")
                    f.write(f"  Win Rate: {result['win_rate']:.1f}%\n")
                    f.write(f"  PnL Total: ${result['total_pnl']:.2f}\n")
                    f.write(f"  Mejor trade: {result['best_trade_pct']:.1f}%\n")
                    f.write(f"  Peor trade: {result['worst_trade_pct']:.1f}%\n")
                    
                    # Mejores trades
                    best_trades = sorted(result['trades'], key=lambda x: x['pnl_pct'], reverse=True)[:3]
                    if best_trades:
                        f.write(f"  \n  MEJORES TRADES:\n")
                        for j, trade in enumerate(best_trades, 1):
                            f.write(f"    {j}. {trade['entry_time']} -> {trade['exit_time']}\n")
                            f.write(f"       Entry: ${trade['entry_price']:.4f} | Exit: ${trade['exit_price']:.4f}\n")
                            f.write(f"       PnL: {trade['pnl_pct']:.1f}% (${trade['pnl_amount']:.2f}) | {trade['exit_reason']}\n")
                            f.write(f"       Score: {trade['independence_score']:.2f} | Duracion: {trade['duration_hours']:.1f}h\n")
            else:
                f.write(f"No se encontraron simbolos rentables con los criterios establecidos.\n")
                
        return filename

def main():
    """Funcion principal"""
    # Simbolos para analisis
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 
               'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'XRPUSDT', 'MATICUSDT']
    
    # Periodos de analisis
    test_periods = [60, 90]
    
    for days in test_periods:
        print(f"\n{'='*80}")
        print(f"INICIANDO ANALISIS COMPLETO - {days} DIAS")
        print(f"{'='*80}")
        
        backtester = IndependentSymbolBacktester(initial_capital=1000.0)
        analysis_results = backtester.run_complete_analysis(symbols, days)
        
        # Generar reporte
        report_file = backtester.generate_complete_report(analysis_results, days)
        
        # Mostrar resumen
        summary = analysis_results['summary']
        print(f"\n=== RESUMEN COMPLETO {days} DIAS ===")
        print(f"Simbolos rentables: {len(summary['profitable_symbols'])}")
        print(f"PnL total: ${summary['total_pnl']:.2f}")
        print(f"Trades totales: {summary['total_trades']}")
        
        if summary['profitable_symbols']:
            print(f"\nTOP SIMBOLOS RENTABLES:")
            for i, symbol_data in enumerate(summary['profitable_symbols'][:3], 1):
                print(f"  {i}. {symbol_data['symbol']} - ${symbol_data['total_pnl']:.2f} ({symbol_data['win_rate']:.1f}% WR)")
                
        print(f"\nReporte guardado en: {report_file}")
        
if __name__ == "__main__":
    main()