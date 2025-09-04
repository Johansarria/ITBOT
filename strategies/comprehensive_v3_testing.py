#!/usr/bin/env python3
"""
SISTEMA V3 - PRUEBAS COMPREHENSIVAS
==================================
Pruebas extensivas del Sistema V3 con múltiples configuraciones y escenarios
"""

import ccxt
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import json
import warnings
import time
import random
from typing import Dict, List, Tuple, Any

warnings.filterwarnings('ignore')

class ComprehensiveV3Tester:
    def __init__(self):
        """Inicializar el sistema de pruebas comprehensivas"""
        self.exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Configuraciones de prueba
        self.test_configs = {
            'conservative': {
                'rsi_oversold': 25, 'rsi_overbought': 75,
                'bb_std': 2.5, 'volume_threshold': 1.3,
                'risk_per_trade': 0.015, 'max_trades': 30
            },
            'aggressive': {
                'rsi_oversold': 20, 'rsi_overbought': 80,
                'bb_std': 2.0, 'volume_threshold': 1.1,
                'risk_per_trade': 0.03, 'max_trades': 50
            },
            'ultra_aggressive': {
                'rsi_oversold': 15, 'rsi_overbought': 85,
                'bb_std': 1.8, 'volume_threshold': 1.0,
                'risk_per_trade': 0.04, 'max_trades': 70
            },
            'scalping': {
                'rsi_oversold': 30, 'rsi_overbought': 70,
                'bb_std': 2.2, 'volume_threshold': 1.5,
                'risk_per_trade': 0.01, 'max_trades': 100
            }
        }
        
        # Múltiples pares de trading
        self.extended_pairs = [
            'ETH/USDT', 'BTC/USDT', 'BNB/USDT', 'ADA/USDT',
            'SOL/USDT', 'MATIC/USDT', 'DOT/USDT', 'AVAX/USDT',
            'LINK/USDT', 'UNI/USDT', 'LTC/USDT', 'BCH/USDT'
        ]
        
        # Timeframes múltiples
        self.timeframes = ['5m', '15m', '30m', '1h']
        
        # Balances de prueba
        self.test_balances = [250, 500, 750, 1000, 1500, 2000, 3000, 5000]
        
        # Períodos de prueba
        self.test_periods = [7, 14, 21, 30, 45, 60]
        
    def fetch_market_data(self, symbol: str, timeframe: str, days: int = 30) -> pd.DataFrame:
        """Obtener datos de mercado"""
        try:
            since = self.exchange.milliseconds() - days * 24 * 60 * 60 * 1000
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            return df
            
        except Exception as e:
            print(f"❌ Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_enhanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores técnicos mejorados"""
        try:
            if len(df) < 50:
                return df
                
            # RSI mejorado
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            
            # Bandas de Bollinger
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2.0)
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            
            # MACD
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_histogram'] = macd.macd_diff()
            
            # EMAs múltiples
            for period in [9, 21, 50]:
                df[f'ema_{period}'] = ta.trend.EMAIndicator(df['close'], window=period).ema_indicator()
            
            # ATR
            df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
            
            # Volumen relativo
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Stochastic
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            # Williams %R
            df['williams_r'] = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close']).williams_r()
            
            return df.fillna(method='ffill').fillna(method='bfill')
            
        except Exception as e:
            print(f"❌ Error en indicadores: {e}")
            return df
    
    def advanced_mean_reversion_strategy(self, df: pd.DataFrame, config: Dict) -> List[Dict]:
        """Estrategia de reversión a la media avanzada"""
        trades = []
        position = None
        
        for i in range(50, len(df)):
            current = df.iloc[i]
            
            # Condiciones de entrada LONG (sobreventa)
            long_conditions = [
                current['rsi'] < config['rsi_oversold'],
                current['close'] < current['bb_lower'],
                current['volume_ratio'] > config['volume_threshold'],
                current['macd'] < current['macd_signal'],
                current['stoch_k'] < 20,
                current['williams_r'] < -80
            ]
            
            # Condiciones de entrada SHORT (sobrecompra)
            short_conditions = [
                current['rsi'] > config['rsi_overbought'],
                current['close'] > current['bb_upper'],
                current['volume_ratio'] > config['volume_threshold'],
                current['macd'] > current['macd_signal'],
                current['stoch_k'] > 80,
                current['williams_r'] > -20
            ]
            
            # Entrada LONG (al menos 4 de 6 condiciones)
            if sum(long_conditions) >= 4 and position is None:
                entry_price = current['close']
                stop_loss = entry_price - (current['atr'] * 2)
                take_profit = entry_price + (current['atr'] * 3)
                
                position = {
                    'type': 'long',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current.name
                }
            
            # Entrada SHORT (al menos 4 de 6 condiciones)
            elif sum(short_conditions) >= 4 and position is None:
                entry_price = current['close']
                stop_loss = entry_price + (current['atr'] * 2)
                take_profit = entry_price - (current['atr'] * 3)
                
                position = {
                    'type': 'short',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current.name
                }
            
            # Gestión de posición
            if position:
                if position['type'] == 'long':
                    if current['close'] >= position['take_profit'] or current['close'] <= position['stop_loss']:
                        pnl = current['close'] - position['entry_price']
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'long',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100
                        })
                        position = None
                
                elif position['type'] == 'short':
                    if current['close'] <= position['take_profit'] or current['close'] >= position['stop_loss']:
                        pnl = position['entry_price'] - current['close']
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'short',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100
                        })
                        position = None
        
        return trades
    
    def momentum_breakout_strategy(self, df: pd.DataFrame, config: Dict) -> List[Dict]:
        """Estrategia de ruptura de momentum"""
        trades = []
        position = None
        
        for i in range(50, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Condiciones de ruptura alcista
            bullish_breakout = [
                current['close'] > current['bb_upper'],
                current['rsi'] > 60,
                current['volume_ratio'] > config['volume_threshold'] * 1.5,
                current['ema_9'] > current['ema_21'],
                current['macd'] > current['macd_signal'],
                current['close'] > prev['high']
            ]
            
            # Condiciones de ruptura bajista
            bearish_breakout = [
                current['close'] < current['bb_lower'],
                current['rsi'] < 40,
                current['volume_ratio'] > config['volume_threshold'] * 1.5,
                current['ema_9'] < current['ema_21'],
                current['macd'] < current['macd_signal'],
                current['close'] < prev['low']
            ]
            
            # Entrada LONG (ruptura alcista)
            if sum(bullish_breakout) >= 4 and position is None:
                entry_price = current['close']
                stop_loss = current['bb_middle']
                take_profit = entry_price + (current['atr'] * 4)
                
                position = {
                    'type': 'long',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current.name
                }
            
            # Entrada SHORT (ruptura bajista)
            elif sum(bearish_breakout) >= 4 and position is None:
                entry_price = current['close']
                stop_loss = current['bb_middle']
                take_profit = entry_price - (current['atr'] * 4)
                
                position = {
                    'type': 'short',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current.name
                }
            
            # Gestión de posición
            if position:
                if position['type'] == 'long':
                    if current['close'] >= position['take_profit'] or current['close'] <= position['stop_loss']:
                        pnl = current['close'] - position['entry_price']
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'long',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100
                        })
                        position = None
                
                elif position['type'] == 'short':
                    if current['close'] <= position['take_profit'] or current['close'] >= position['stop_loss']:
                        pnl = position['entry_price'] - current['close']
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'short',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100
                        })
                        position = None
        
        return trades
    
    def run_comprehensive_test(self, config_name: str, pair: str, timeframe: str, 
                             balance: float, days: int) -> Dict:
        """Ejecutar una prueba comprehensiva"""
        print(f"🧪 Probando {config_name} | {pair} | {timeframe} | ${balance} | {days}d")
        
        config = self.test_configs[config_name]
        df = self.fetch_market_data(pair, timeframe, days)
        
        if df.empty or len(df) < 100:
            return {'error': 'Datos insuficientes'}
        
        df = self.calculate_enhanced_indicators(df)
        
        # Ejecutar ambas estrategias
        mean_reversion_trades = self.advanced_mean_reversion_strategy(df, config)
        breakout_trades = self.momentum_breakout_strategy(df, config)
        
        # Combinar trades
        all_trades = mean_reversion_trades + breakout_trades
        all_trades = sorted(all_trades, key=lambda x: x['entry_time'])
        
        # Limitar número de trades
        if len(all_trades) > config['max_trades']:
            all_trades = all_trades[:config['max_trades']]
        
        if not all_trades:
            return {
                'config': config_name, 'pair': pair, 'timeframe': timeframe,
                'balance': balance, 'days': days, 'trades': 0, 'pnl_usd': 0,
                'monthly_return': 0, 'win_rate': 0, 'profit_factor': 0,
                'max_drawdown': 0, 'sharpe_ratio': 0
            }
        
        # Calcular métricas
        total_pnl_percent = sum(trade['pnl_percent'] for trade in all_trades)
        winning_trades = [t for t in all_trades if t['pnl_percent'] > 0]
        losing_trades = [t for t in all_trades if t['pnl_percent'] <= 0]
        
        win_rate = len(winning_trades) / len(all_trades) * 100 if all_trades else 0
        
        gross_profit = sum(t['pnl_percent'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl_percent'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # PnL en USD
        pnl_usd = balance * (total_pnl_percent / 100)
        
        # Retorno mensual extrapolado
        monthly_return = (total_pnl_percent / days) * 30
        
        # Calcular drawdown
        cumulative_returns = []
        cumulative = 0
        for trade in all_trades:
            cumulative += trade['pnl_percent']
            cumulative_returns.append(cumulative)
        
        peak = 0
        max_drawdown = 0
        for cum_return in cumulative_returns:
            if cum_return > peak:
                peak = cum_return
            drawdown = peak - cum_return
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Sharpe ratio simplificado
        returns = [t['pnl_percent'] for t in all_trades]
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if len(returns) > 1 else 0
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        
        return {
            'config': config_name,
            'pair': pair,
            'timeframe': timeframe,
            'balance': balance,
            'days': days,
            'trades': len(all_trades),
            'pnl_usd': round(pnl_usd, 2),
            'pnl_percent': round(total_pnl_percent, 2),
            'monthly_return': round(monthly_return, 2),
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'best_trade': round(max(returns) if returns else 0, 2),
            'worst_trade': round(min(returns) if returns else 0, 2),
            'avg_trade': round(avg_return, 2)
        }
    
    def run_all_tests(self) -> List[Dict]:
        """Ejecutar todas las pruebas comprehensivas"""
        print("🚀 INICIANDO PRUEBAS COMPREHENSIVAS SISTEMA V3")
        print("=" * 80)
        
        all_results = []
        total_tests = 0
        successful_tests = 0
        
        # Seleccionar muestra representativa para evitar demasiadas pruebas
        selected_configs = ['conservative', 'aggressive', 'ultra_aggressive']
        selected_pairs = ['ETH/USDT', 'BTC/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']
        selected_timeframes = ['15m', '30m', '1h']
        selected_balances = [500, 1000, 2000, 5000]
        selected_periods = [14, 30, 45]
        
        for config in selected_configs:
            for pair in selected_pairs:
                for timeframe in selected_timeframes:
                    for balance in selected_balances:
                        for days in selected_periods:
                            total_tests += 1
                            
                            try:
                                result = self.run_comprehensive_test(config, pair, timeframe, balance, days)
                                if 'error' not in result:
                                    all_results.append(result)
                                    successful_tests += 1
                                
                                # Pausa para evitar rate limiting
                                time.sleep(0.1)
                                
                            except Exception as e:
                                print(f"❌ Error en prueba: {e}")
                                continue
        
        print(f"\n📊 PRUEBAS COMPLETADAS: {successful_tests}/{total_tests}")
        return all_results
    
    def analyze_results(self, results: List[Dict]) -> Dict:
        """Analizar los resultados de las pruebas"""
        if not results:
            return {}
        
        # Filtrar solo resultados rentables
        profitable_results = [r for r in results if r['monthly_return'] > 0]
        
        # Análisis por configuración
        config_analysis = {}
        for config in ['conservative', 'aggressive', 'ultra_aggressive']:
            config_results = [r for r in results if r['config'] == config]
            if config_results:
                config_analysis[config] = {
                    'total_tests': len(config_results),
                    'profitable_tests': len([r for r in config_results if r['monthly_return'] > 0]),
                    'avg_monthly_return': np.mean([r['monthly_return'] for r in config_results]),
                    'avg_win_rate': np.mean([r['win_rate'] for r in config_results]),
                    'avg_profit_factor': np.mean([r['profit_factor'] for r in config_results]),
                    'best_monthly': max([r['monthly_return'] for r in config_results]),
                    'worst_monthly': min([r['monthly_return'] for r in config_results])
                }
        
        # Análisis por par
        pair_analysis = {}
        for pair in set(r['pair'] for r in results):
            pair_results = [r for r in results if r['pair'] == pair]
            if pair_results:
                pair_analysis[pair] = {
                    'total_tests': len(pair_results),
                    'profitable_tests': len([r for r in pair_results if r['monthly_return'] > 0]),
                    'avg_monthly_return': np.mean([r['monthly_return'] for r in pair_results]),
                    'best_config': max(pair_results, key=lambda x: x['monthly_return'])['config'],
                    'best_return': max([r['monthly_return'] for r in pair_results])
                }
        
        # Mejores estrategias
        top_strategies = sorted(profitable_results, key=lambda x: x['monthly_return'], reverse=True)[:10]
        
        return {
            'total_tests': len(results),
            'profitable_tests': len(profitable_results),
            'success_rate': len(profitable_results) / len(results) * 100,
            'overall_avg_return': np.mean([r['monthly_return'] for r in results]),
            'profitable_avg_return': np.mean([r['monthly_return'] for r in profitable_results]) if profitable_results else 0,
            'config_analysis': config_analysis,
            'pair_analysis': pair_analysis,
            'top_strategies': top_strategies
        }

def main():
    """Función principal"""
    print("🧪 SISTEMA V3 - PRUEBAS COMPREHENSIVAS")
    print("=" * 80)
    
    tester = ComprehensiveV3Tester()
    
    # Ejecutar todas las pruebas
    results = tester.run_all_tests()
    
    if not results:
        print("❌ No se obtuvieron resultados válidos")
        return
    
    # Analizar resultados
    analysis = tester.analyze_results(results)
    
    print("\n📊 ANÁLISIS DE RESULTADOS COMPREHENSIVOS")
    print("=" * 80)
    
    print(f"🔢 Total de Pruebas: {analysis['total_tests']}")
    print(f"✅ Pruebas Rentables: {analysis['profitable_tests']}")
    print(f"📈 Tasa de Éxito: {analysis['success_rate']:.1f}%")
    print(f"📊 Retorno Promedio General: {analysis['overall_avg_return']:.2f}%")
    print(f"🏆 Retorno Promedio Rentables: {analysis['profitable_avg_return']:.2f}%")
    
    print("\n📈 ANÁLISIS POR CONFIGURACIÓN:")
    print("-" * 50)
    for config, data in analysis['config_analysis'].items():
        profitability = data['profitable_tests'] / data['total_tests'] * 100
        print(f"{config.upper()}:")
        print(f"  Rentabilidad: {profitability:.1f}% ({data['profitable_tests']}/{data['total_tests']})")
        print(f"  Retorno Promedio: {data['avg_monthly_return']:.2f}%")
        print(f"  Win Rate Promedio: {data['avg_win_rate']:.1f}%")
        print(f"  Mejor Mes: {data['best_monthly']:.2f}%")
        print()
    
    print("🏆 TOP 5 ESTRATEGIAS MÁS RENTABLES:")
    print("-" * 70)
    for i, strategy in enumerate(analysis['top_strategies'][:5], 1):
        print(f"{i}. {strategy['config'].upper()} | {strategy['pair']} | {strategy['timeframe']}")
        print(f"   Balance: ${strategy['balance']} | Período: {strategy['days']}d")
        print(f"   Retorno Mensual: {strategy['monthly_return']:.2f}%")
        print(f"   Trades: {strategy['trades']} | Win Rate: {strategy['win_rate']:.1f}%")
        print(f"   Profit Factor: {strategy['profit_factor']:.2f} | Sharpe: {strategy['sharpe_ratio']:.2f}")
        print()
    
    print("📊 ANÁLISIS POR PAR DE TRADING:")
    print("-" * 50)
    for pair, data in analysis['pair_analysis'].items():
        profitability = data['profitable_tests'] / data['total_tests'] * 100
        print(f"{pair}: {profitability:.1f}% rentable ({data['best_return']:.2f}% mejor)")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with open(f'COMPREHENSIVE_V3_RESULTS_{timestamp}.json', 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'results': results,
            'analysis': analysis
        }, f, indent=2, default=str)
    
    print(f"\n💾 Resultados guardados: COMPREHENSIVE_V3_RESULTS_{timestamp}.json")
    print("🎯 PRUEBAS COMPREHENSIVAS COMPLETADAS")

if __name__ == "__main__":
    main()
