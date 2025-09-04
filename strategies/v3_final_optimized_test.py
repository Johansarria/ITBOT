#!/usr/bin/env python3
"""
SISTEMA V3 - PRUEBA FINAL OPTIMIZADA
===================================
Configuración optimizada basada en todos los análisis realizados
"""

import ccxt
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import json
import warnings
import time
from typing import Dict, List, Tuple, Any

warnings.filterwarnings('ignore')

class OptimizedV3FinalTest:
    def __init__(self):
        """Sistema V3 con configuración final optimizada"""
        self.exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Configuración optimizada basada en todos los análisis
        self.optimized_configs = {
            'scalping_config': {
                'name': 'Scalping_Optimizado',
                'rsi_oversold': 20, 'rsi_overbought': 80,
                'bb_std': 2.0, 'volume_threshold': 1.0,
                'risk_per_trade': 0.02, 'max_trades': 100,
                'atr_multiplier_sl': 1.5, 'atr_multiplier_tp': 3.0
            },
            'swing_config': {
                'name': 'Swing_Optimizado',
                'rsi_oversold': 25, 'rsi_overbought': 75,
                'bb_std': 2.5, 'volume_threshold': 1.3,
                'risk_per_trade': 0.025, 'max_trades': 50,
                'atr_multiplier_sl': 2.0, 'atr_multiplier_tp': 4.0
            },
            'hybrid_config': {
                'name': 'Híbrido_Optimizado',
                'rsi_oversold': 22, 'rsi_overbought': 78,
                'bb_std': 2.2, 'volume_threshold': 1.1,
                'risk_per_trade': 0.03, 'max_trades': 75,
                'atr_multiplier_sl': 1.8, 'atr_multiplier_tp': 3.5
            }
        }
        
        # Activos seleccionados por mejor rendimiento
        self.top_assets = ['ETH/USDT', 'BTC/USDT', 'SOL/USDT']
        
        # Timeframes optimizados
        self.timeframes = ['15m', '30m', '1h']
        
        # Balances de prueba
        self.test_balances = [1000, 2000, 5000]
    
    def fetch_optimized_data(self, symbol: str, timeframe: str, days: int = 30) -> pd.DataFrame:
        """Obtener datos optimizados"""
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
    
    def calculate_optimized_indicators(self, df: pd.DataFrame, bb_std: float = 2.0) -> pd.DataFrame:
        """Calcular indicadores optimizados"""
        try:
            if len(df) < 50:
                return df
                
            # Indicadores principales
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            
            # Bandas de Bollinger optimizadas
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=bb_std)
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle'] * 100
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # MACD optimizado
            macd = ta.trend.MACD(df['close'], window_slow=26, window_fast=12, window_sign=9)
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_histogram'] = macd.macd_diff()
            df['macd_momentum'] = df['macd_histogram'].diff()
            
            # EMAs múltiples
            for period in [9, 21, 50, 200]:
                df[f'ema_{period}'] = ta.trend.EMAIndicator(df['close'], window=period).ema_indicator()
            
            # ATR dinámico
            df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
            df['atr_percent'] = df['atr'] / df['close'] * 100
            
            # Volumen optimizado
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            df['volume_trend'] = ta.trend.EMAIndicator(df['volume'], window=10).ema_indicator()
            df['volume_acceleration'] = df['volume_trend'].pct_change()
            
            # Momentum osciladores
            stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            df['williams_r'] = ta.momentum.WilliamsRIndicator(df['high'], df['low'], df['close']).williams_r()
            
            # CCI para confirmar divergencias
            df['cci'] = ta.trend.CCIIndicator(df['high'], df['low'], df['close'], window=20).cci()
            
            # Tendencia de precio
            df['price_change'] = df['close'].pct_change()
            df['price_momentum'] = df['close'].pct_change(periods=5)
            
            return df.fillna(method='ffill').fillna(method='bfill')
            
        except Exception as e:
            print(f"❌ Error en indicadores: {e}")
            return df
    
    def ultimate_strategy(self, df: pd.DataFrame, config: Dict) -> List[Dict]:
        """Estrategia ultimate optimizada con múltiples confirmaciones"""
        trades = []
        position = None
        
        rsi_oversold = config['rsi_oversold']
        rsi_overbought = config['rsi_overbought']
        volume_threshold = config['volume_threshold']
        max_trades = config['max_trades']
        atr_sl = config['atr_multiplier_sl']
        atr_tp = config['atr_multiplier_tp']
        
        for i in range(50, len(df)):
            if len(trades) >= max_trades:
                break
                
            current = df.iloc[i]
            prev = df.iloc[i-1]
            prev2 = df.iloc[i-2] if i >= 2 else prev
            
            # === CONDICIONES LONG ULTRA-OPTIMIZADAS ===
            long_conditions = [
                # RSI sobreventa
                current['rsi'] < rsi_oversold,
                # Bollinger Bands
                current['close'] <= current['bb_lower'] or current['bb_position'] < 0.2,
                # Volumen confirmatorio
                current['volume_ratio'] > volume_threshold,
                # MACD momentum
                current['macd_histogram'] > prev['macd_histogram'],
                # Stochastic sobreventa
                current['stoch_k'] < 25 and current['stoch_d'] < 25,
                # Williams %R sobreventa
                current['williams_r'] < -75,
                # Tendencia de fondo alcista (EMA 9 > EMA 21)
                current['ema_9'] > current['ema_21'],
                # Precio por encima de EMA 50 para tendencia alcista
                current['close'] > current['ema_50'],
                # CCI sobreventa
                current['cci'] < -100,
                # Momentum de precio positivo
                current['price_momentum'] > -0.02,
                # ATR no excesivamente alto (volatilidad controlada)
                current['atr_percent'] < 8,
                # BB Width indica volatilidad adecuada
                current['bb_width'] > 2,
            ]
            
            # === CONDICIONES SHORT ULTRA-OPTIMIZADAS ===
            short_conditions = [
                # RSI sobrecompra
                current['rsi'] > rsi_overbought,
                # Bollinger Bands
                current['close'] >= current['bb_upper'] or current['bb_position'] > 0.8,
                # Volumen confirmatorio
                current['volume_ratio'] > volume_threshold,
                # MACD momentum
                current['macd_histogram'] < prev['macd_histogram'],
                # Stochastic sobrecompra
                current['stoch_k'] > 75 and current['stoch_d'] > 75,
                # Williams %R sobrecompra
                current['williams_r'] > -25,
                # Tendencia de fondo bajista (EMA 9 < EMA 21)
                current['ema_9'] < current['ema_21'],
                # Precio por debajo de EMA 50 para tendencia bajista
                current['close'] < current['ema_50'],
                # CCI sobrecompra
                current['cci'] > 100,
                # Momentum de precio negativo
                current['price_momentum'] < 0.02,
                # ATR no excesivamente alto
                current['atr_percent'] < 8,
                # BB Width indica volatilidad adecuada
                current['bb_width'] > 2,
            ]
            
            # === ENTRADA LONG (al menos 8 de 12 condiciones) ===
            if sum(long_conditions) >= 8 and position is None:
                entry_price = current['close']
                stop_loss = entry_price - (current['atr'] * atr_sl)
                take_profit = entry_price + (current['atr'] * atr_tp)
                
                # Stop loss dinámico basado en BB
                stop_loss = max(stop_loss, current['bb_lower'] * 0.995)
                
                position = {
                    'type': 'long',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current.name,
                    'conditions_met': sum(long_conditions),
                    'entry_rsi': current['rsi'],
                    'entry_bb_pos': current['bb_position']
                }
            
            # === ENTRADA SHORT (al menos 8 de 12 condiciones) ===
            elif sum(short_conditions) >= 8 and position is None:
                entry_price = current['close']
                stop_loss = entry_price + (current['atr'] * atr_sl)
                take_profit = entry_price - (current['atr'] * atr_tp)
                
                # Stop loss dinámico basado en BB
                stop_loss = min(stop_loss, current['bb_upper'] * 1.005)
                
                position = {
                    'type': 'short',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current.name,
                    'conditions_met': sum(short_conditions),
                    'entry_rsi': current['rsi'],
                    'entry_bb_pos': current['bb_position']
                }
            
            # === GESTIÓN AVANZADA DE POSICIONES ===
            if position:
                if position['type'] == 'long':
                    # Salida por TP/SL
                    if current['close'] >= position['take_profit'] or current['close'] <= position['stop_loss']:
                        pnl = current['close'] - position['entry_price']
                        exit_reason = 'take_profit' if current['close'] >= position['take_profit'] else 'stop_loss'
                        
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'long',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100,
                            'exit_reason': exit_reason,
                            'conditions_met': position['conditions_met'],
                            'entry_rsi': position['entry_rsi'],
                            'exit_rsi': current['rsi'],
                            'duration_hours': (current.name - position['entry_time']).total_seconds() / 3600
                        })
                        position = None
                    
                    # Salida por reversión de momentum
                    elif (current['rsi'] > 75 and current['bb_position'] > 0.85 and 
                          current['macd_histogram'] < prev['macd_histogram']):
                        pnl = current['close'] - position['entry_price']
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'long',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100,
                            'exit_reason': 'momentum_reversal',
                            'conditions_met': position['conditions_met'],
                            'entry_rsi': position['entry_rsi'],
                            'exit_rsi': current['rsi'],
                            'duration_hours': (current.name - position['entry_time']).total_seconds() / 3600
                        })
                        position = None
                
                elif position['type'] == 'short':
                    # Salida por TP/SL
                    if current['close'] <= position['take_profit'] or current['close'] >= position['stop_loss']:
                        pnl = position['entry_price'] - current['close']
                        exit_reason = 'take_profit' if current['close'] <= position['take_profit'] else 'stop_loss'
                        
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'short',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100,
                            'exit_reason': exit_reason,
                            'conditions_met': position['conditions_met'],
                            'entry_rsi': position['entry_rsi'],
                            'exit_rsi': current['rsi'],
                            'duration_hours': (current.name - position['entry_time']).total_seconds() / 3600
                        })
                        position = None
                    
                    # Salida por reversión de momentum
                    elif (current['rsi'] < 25 and current['bb_position'] < 0.15 and 
                          current['macd_histogram'] > prev['macd_histogram']):
                        pnl = position['entry_price'] - current['close']
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'short',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100,
                            'exit_reason': 'momentum_reversal',
                            'conditions_met': position['conditions_met'],
                            'entry_rsi': position['entry_rsi'],
                            'exit_rsi': current['rsi'],
                            'duration_hours': (current.name - position['entry_time']).total_seconds() / 3600
                        })
                        position = None
        
        return trades
    
    def run_optimized_test(self, config_name: str, asset: str, timeframe: str, balance: float) -> Dict:
        """Ejecutar prueba con configuración optimizada"""
        config = self.optimized_configs[config_name]
        
        print(f"🚀 {config['name']} | {asset} | {timeframe} | ${balance}")
        
        # Obtener datos
        df = self.fetch_optimized_data(asset, timeframe, 30)
        if df.empty or len(df) < 100:
            return {'error': 'Datos insuficientes', 'config': config_name, 'asset': asset}
        
        # Calcular indicadores
        df = self.calculate_optimized_indicators(df, config['bb_std'])
        
        # Ejecutar estrategia
        trades = self.ultimate_strategy(df, config)
        
        if not trades:
            return {
                'config': config_name, 'asset': asset, 'timeframe': timeframe,
                'balance': balance, 'trades': 0, 'pnl_usd': 0,
                'monthly_return': 0, 'win_rate': 0, 'profit_factor': 0,
                'avg_duration': 0, 'avg_conditions_met': 0
            }
        
        # Calcular métricas avanzadas
        total_pnl_percent = sum(trade['pnl_percent'] for trade in trades)
        winning_trades = [t for t in trades if t['pnl_percent'] > 0]
        losing_trades = [t for t in trades if t['pnl_percent'] <= 0]
        
        win_rate = len(winning_trades) / len(trades) * 100
        
        gross_profit = sum(t['pnl_percent'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl_percent'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # PnL en USD
        pnl_usd = balance * (total_pnl_percent / 100)
        
        # Retorno mensual
        monthly_return = total_pnl_percent  # Ya calculado para 30 días
        
        # Métricas adicionales
        avg_duration = np.mean([t['duration_hours'] for t in trades])
        avg_conditions_met = np.mean([t['conditions_met'] for t in trades])
        
        # Drawdown análisis
        cumulative_returns = []
        cumulative = 0
        for trade in trades:
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
        
        return {
            'config': config_name,
            'asset': asset,
            'timeframe': timeframe,
            'balance': balance,
            'trades': len(trades),
            'pnl_usd': round(pnl_usd, 2),
            'pnl_percent': round(total_pnl_percent, 2),
            'monthly_return': round(monthly_return, 2),
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown, 2),
            'best_trade': round(max([t['pnl_percent'] for t in trades]), 2),
            'worst_trade': round(min([t['pnl_percent'] for t in trades]), 2),
            'avg_trade': round(total_pnl_percent / len(trades), 2),
            'avg_duration_hours': round(avg_duration, 1),
            'avg_conditions_met': round(avg_conditions_met, 1),
            'long_trades': len([t for t in trades if t['type'] == 'long']),
            'short_trades': len([t for t in trades if t['type'] == 'short']),
            'tp_exits': len([t for t in trades if t['exit_reason'] == 'take_profit']),
            'sl_exits': len([t for t in trades if t['exit_reason'] == 'stop_loss']),
            'momentum_exits': len([t for t in trades if t['exit_reason'] == 'momentum_reversal'])
        }
    
    def run_comprehensive_final_test(self) -> List[Dict]:
        """Ejecutar prueba final comprehensiva"""
        print("🚀 SISTEMA V3 - PRUEBA FINAL OPTIMIZADA")
        print("=" * 80)
        print("⚡ Configuraciones Ultimate basadas en análisis completo")
        print()
        
        all_results = []
        
        for config_name in self.optimized_configs.keys():
            for asset in self.top_assets:
                for timeframe in self.timeframes:
                    for balance in self.test_balances:
                        try:
                            result = self.run_optimized_test(config_name, asset, timeframe, balance)
                            if 'error' not in result:
                                all_results.append(result)
                            
                            # Pausa para rate limiting
                            time.sleep(0.2)
                            
                        except Exception as e:
                            print(f"❌ Error: {e}")
                            continue
        
        return all_results

def main():
    """Función principal"""
    print("🚀 SISTEMA V3 - CONFIGURACIÓN FINAL OPTIMIZADA")
    print("=" * 80)
    
    tester = OptimizedV3FinalTest()
    
    # Ejecutar prueba final
    results = tester.run_comprehensive_final_test()
    
    if not results:
        print("❌ No se obtuvieron resultados")
        return
    
    # Filtrar solo resultados rentables
    profitable_results = [r for r in results if r['monthly_return'] > 0]
    
    print(f"\n📊 RESULTADOS FINALES OPTIMIZADOS")
    print("=" * 80)
    print(f"🔢 Total de Pruebas: {len(results)}")
    print(f"✅ Pruebas Rentables: {len(profitable_results)}")
    print(f"📈 Tasa de Éxito: {len(profitable_results)/len(results)*100:.1f}%")
    
    if profitable_results:
        avg_return = np.mean([r['monthly_return'] for r in profitable_results])
        print(f"🏆 Retorno Mensual Promedio (Rentables): {avg_return:.2f}%")
        
        # Top 10 mejores estrategias
        top_strategies = sorted(profitable_results, key=lambda x: x['monthly_return'], reverse=True)[:10]
        
        print("\n🏆 TOP 10 ESTRATEGIAS OPTIMIZADAS:")
        print("-" * 90)
        for i, strategy in enumerate(top_strategies, 1):
            print(f"{i:2}. {strategy['config'].upper():<20} | {strategy['asset']:<10} | {strategy['timeframe']:<4} | ${strategy['balance']:<5}")
            print(f"    💰 Mensual: {strategy['monthly_return']:+6.2f}% | Trades: {strategy['trades']:3} | WR: {strategy['win_rate']:5.1f}% | PF: {strategy['profit_factor']:4.2f}")
            print(f"    📊 USD: ${strategy['pnl_usd']:+8.2f} | DD: {strategy['max_drawdown']:5.2f}% | Avg: {strategy['avg_duration_hours']:4.1f}h | Cond: {strategy['avg_conditions_met']:4.1f}")
            print()
        
        # Análisis por configuración
        print("📈 ANÁLISIS POR CONFIGURACIÓN:")
        print("-" * 60)
        for config in ['scalping_config', 'swing_config', 'hybrid_config']:
            config_results = [r for r in profitable_results if r['config'] == config]
            if config_results:
                avg_return = np.mean([r['monthly_return'] for r in config_results])
                success_rate = len(config_results) / len([r for r in results if r['config'] == config]) * 100
                print(f"{config.upper().replace('_CONFIG', ''):15}: {success_rate:5.1f}% éxito, {avg_return:6.2f}% mensual")
        
        # Análisis por activo
        print("\n📊 ANÁLISIS POR ACTIVO:")
        print("-" * 60)
        for asset in tester.top_assets:
            asset_results = [r for r in profitable_results if r['asset'] == asset]
            if asset_results:
                avg_return = np.mean([r['monthly_return'] for r in asset_results])
                success_rate = len(asset_results) / len([r for r in results if r['asset'] == asset]) * 100
                print(f"{asset:10}: {success_rate:5.1f}% éxito, {avg_return:6.2f}% mensual")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    final_data = {
        'timestamp': timestamp,
        'configurations': tester.optimized_configs,
        'results': results,
        'profitable_results': profitable_results,
        'summary': {
            'total_tests': len(results),
            'profitable_tests': len(profitable_results),
            'success_rate': len(profitable_results)/len(results)*100 if results else 0,
            'avg_profitable_return': np.mean([r['monthly_return'] for r in profitable_results]) if profitable_results else 0
        }
    }
    
    with open(f'V3_FINAL_OPTIMIZED_RESULTS_{timestamp}.json', 'w') as f:
        json.dump(final_data, f, indent=2, default=str)
    
    print(f"\n💾 Resultados guardados: V3_FINAL_OPTIMIZED_RESULTS_{timestamp}.json")
    print("🎯 PRUEBA FINAL OPTIMIZADA COMPLETADA")

if __name__ == "__main__":
    main()
