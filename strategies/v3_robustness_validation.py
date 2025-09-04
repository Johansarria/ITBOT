#!/usr/bin/env python3
"""
SISTEMA V3 - PRUEBAS DE VALIDACIÓN CRUZADA Y ROBUSTEZ
====================================================
Análisis avanzado del mejor rendimiento encontrado: ETH/USDT 1h Conservative
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

class V3RobustnessValidator:
    def __init__(self):
        """Inicializar validador de robustez"""
        self.exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Configuración óptima encontrada
        self.optimal_config = {
            'pair': 'ETH/USDT',
            'timeframe': '1h',
            'strategy_type': 'conservative',
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'bb_std': 2.5,
            'volume_threshold': 1.3,
            'risk_per_trade': 0.015,
            'max_trades': 30
        }
        
        # Variaciones para pruebas de sensibilidad
        self.sensitivity_tests = {
            'rsi_levels': [(20,80), (25,75), (30,70), (35,65)],
            'bb_std_devs': [1.5, 2.0, 2.5, 3.0],
            'volume_thresholds': [1.0, 1.2, 1.3, 1.5, 1.8],
            'risk_levels': [0.01, 0.015, 0.02, 0.025, 0.03],
            'timeframes': ['30m', '1h', '2h', '4h']
        }
        
        # Períodos de validación cruzada
        self.validation_periods = [
            {'start_days': 60, 'end_days': 45, 'label': 'Período_1'},
            {'start_days': 45, 'end_days': 30, 'label': 'Período_2'},
            {'start_days': 30, 'end_days': 15, 'label': 'Período_3'},
            {'start_days': 15, 'end_days': 0, 'label': 'Período_4'},
        ]
    
    def fetch_extended_data(self, symbol: str, timeframe: str, days: int = 90) -> pd.DataFrame:
        """Obtener datos extendidos para validación"""
        try:
            since = self.exchange.milliseconds() - days * 24 * 60 * 60 * 1000
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, since, limit=2000)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            return df
            
        except Exception as e:
            print(f"❌ Error fetching extended data: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame, bb_std: float = 2.5) -> pd.DataFrame:
        """Calcular indicadores con parámetros ajustables"""
        try:
            if len(df) < 50:
                return df
                
            # RSI
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            
            # Bandas de Bollinger con std ajustable
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=bb_std)
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            
            # MACD
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_histogram'] = macd.macd_diff()
            
            # EMAs
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
    
    def enhanced_conservative_strategy(self, df: pd.DataFrame, config: Dict) -> List[Dict]:
        """Estrategia conservadora mejorada basada en mejores resultados"""
        trades = []
        position = None
        
        rsi_oversold = config.get('rsi_oversold', 25)
        rsi_overbought = config.get('rsi_overbought', 75)
        volume_threshold = config.get('volume_threshold', 1.3)
        max_trades = config.get('max_trades', 30)
        
        for i in range(50, len(df)):
            if len(trades) >= max_trades:
                break
                
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Condiciones de entrada LONG mejoradas
            long_conditions = [
                current['rsi'] < rsi_oversold,
                current['close'] < current['bb_lower'],
                current['volume_ratio'] > volume_threshold,
                current['macd'] < current['macd_signal'],
                current['stoch_k'] < 25,
                current['williams_r'] < -75,
                current['ema_9'] > current['ema_21'],  # Tendencia alcista
                current['close'] > current['ema_50'],  # Por encima de EMA largo plazo
            ]
            
            # Condiciones de entrada SHORT mejoradas
            short_conditions = [
                current['rsi'] > rsi_overbought,
                current['close'] > current['bb_upper'],
                current['volume_ratio'] > volume_threshold,
                current['macd'] > current['macd_signal'],
                current['stoch_k'] > 75,
                current['williams_r'] > -25,
                current['ema_9'] < current['ema_21'],  # Tendencia bajista
                current['close'] < current['ema_50'],  # Por debajo de EMA largo plazo
            ]
            
            # Entrada LONG (al menos 5 de 8 condiciones)
            if sum(long_conditions) >= 5 and position is None:
                entry_price = current['close']
                stop_loss = entry_price - (current['atr'] * 2.5)
                take_profit = entry_price + (current['atr'] * 4)
                
                position = {
                    'type': 'long',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current.name,
                    'conditions_met': sum(long_conditions)
                }
            
            # Entrada SHORT (al menos 5 de 8 condiciones)
            elif sum(short_conditions) >= 5 and position is None:
                entry_price = current['close']
                stop_loss = entry_price + (current['atr'] * 2.5)
                take_profit = entry_price - (current['atr'] * 4)
                
                position = {
                    'type': 'short',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'entry_time': current.name,
                    'conditions_met': sum(short_conditions)
                }
            
            # Gestión de posición mejorada
            if position:
                if position['type'] == 'long':
                    # Salida por take profit o stop loss
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
                            'atr_at_entry': df.iloc[i-1]['atr'] if i > 0 else current['atr']
                        })
                        position = None
                    
                    # Salida por reversión de tendencia
                    elif current['rsi'] > 70 and current['close'] > current['bb_upper']:
                        pnl = current['close'] - position['entry_price']
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'long',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100,
                            'exit_reason': 'trend_reversal',
                            'conditions_met': position['conditions_met'],
                            'atr_at_entry': df.iloc[i-1]['atr'] if i > 0 else current['atr']
                        })
                        position = None
                
                elif position['type'] == 'short':
                    # Salida por take profit o stop loss
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
                            'atr_at_entry': df.iloc[i-1]['atr'] if i > 0 else current['atr']
                        })
                        position = None
                    
                    # Salida por reversión de tendencia
                    elif current['rsi'] < 30 and current['close'] < current['bb_lower']:
                        pnl = position['entry_price'] - current['close']
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': current.name,
                            'type': 'short',
                            'entry_price': position['entry_price'],
                            'exit_price': current['close'],
                            'pnl_points': pnl,
                            'pnl_percent': (pnl / position['entry_price']) * 100,
                            'exit_reason': 'trend_reversal',
                            'conditions_met': position['conditions_met'],
                            'atr_at_entry': df.iloc[i-1]['atr'] if i > 0 else current['atr']
                        })
                        position = None
        
        return trades
    
    def run_cross_validation_test(self) -> Dict:
        """Ejecutar validación cruzada en múltiples períodos"""
        print("🔬 VALIDACIÓN CRUZADA - ETH/USDT 1h CONSERVATIVE")
        print("=" * 60)
        
        results = {}
        all_trades = []
        
        # Obtener datos extendidos (90 días)
        df_full = self.fetch_extended_data('ETH/USDT', '1h', 90)
        if df_full.empty:
            return {'error': 'No se pudieron obtener datos extendidos'}
        
        df_full = self.calculate_indicators(df_full, self.optimal_config['bb_std'])
        
        for period in self.validation_periods:
            print(f"📊 Probando {period['label']}: {period['start_days']}-{period['end_days']} días atrás")
            
            # Filtrar datos para el período
            start_time = datetime.now() - timedelta(days=period['start_days'])
            end_time = datetime.now() - timedelta(days=period['end_days'])
            
            df_period = df_full[(df_full.index >= start_time) & (df_full.index < end_time)]
            
            if len(df_period) < 50:
                continue
            
            # Ejecutar estrategia
            trades = self.enhanced_conservative_strategy(df_period, self.optimal_config)
            all_trades.extend(trades)
            
            if not trades:
                results[period['label']] = {
                    'trades': 0, 'pnl_percent': 0, 'win_rate': 0, 
                    'profit_factor': 0, 'period_days': period['start_days'] - period['end_days']
                }
                continue
            
            # Calcular métricas
            total_pnl = sum(t['pnl_percent'] for t in trades)
            winning_trades = [t for t in trades if t['pnl_percent'] > 0]
            win_rate = len(winning_trades) / len(trades) * 100
            
            gross_profit = sum(t['pnl_percent'] for t in winning_trades)
            gross_loss = abs(sum(t['pnl_percent'] for t in trades if t['pnl_percent'] <= 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Retorno mensual extrapolado
            days_in_period = period['start_days'] - period['end_days']
            monthly_return = (total_pnl / days_in_period) * 30
            
            results[period['label']] = {
                'trades': len(trades),
                'pnl_percent': round(total_pnl, 2),
                'monthly_return': round(monthly_return, 2),
                'win_rate': round(win_rate, 1),
                'profit_factor': round(profit_factor, 2),
                'period_days': days_in_period,
                'avg_trade': round(total_pnl / len(trades), 2),
                'best_trade': round(max(t['pnl_percent'] for t in trades), 2),
                'worst_trade': round(min(t['pnl_percent'] for t in trades), 2)
            }
            
            print(f"  ✅ Trades: {len(trades)}, PnL: {total_pnl:.2f}%, Mensual: {monthly_return:.2f}%, WR: {win_rate:.1f}%")
        
        return {'periods': results, 'all_trades': all_trades}
    
    def run_sensitivity_analysis(self) -> Dict:
        """Ejecutar análisis de sensibilidad de parámetros"""
        print("\n🎯 ANÁLISIS DE SENSIBILIDAD DE PARÁMETROS")
        print("=" * 60)
        
        sensitivity_results = {}
        
        # Obtener datos base
        df = self.fetch_extended_data('ETH/USDT', '1h', 45)
        if df.empty:
            return {'error': 'No se pudieron obtener datos para sensibilidad'}
        
        # Pruebas de sensibilidad RSI
        print("📈 Probando niveles de RSI...")
        rsi_results = []
        for oversold, overbought in self.sensitivity_tests['rsi_levels']:
            config = self.optimal_config.copy()
            config['rsi_oversold'] = oversold
            config['rsi_overbought'] = overbought
            
            df_test = self.calculate_indicators(df, config['bb_std'])
            trades = self.enhanced_conservative_strategy(df_test, config)
            
            if trades:
                total_pnl = sum(t['pnl_percent'] for t in trades)
                win_rate = len([t for t in trades if t['pnl_percent'] > 0]) / len(trades) * 100
                rsi_results.append({
                    'levels': f"{oversold}/{overbought}",
                    'trades': len(trades),
                    'pnl': round(total_pnl, 2),
                    'win_rate': round(win_rate, 1)
                })
        
        sensitivity_results['rsi'] = rsi_results
        
        # Pruebas de sensibilidad Bollinger Bands
        print("📊 Probando desviaciones estándar BB...")
        bb_results = []
        for bb_std in self.sensitivity_tests['bb_std_devs']:
            config = self.optimal_config.copy()
            config['bb_std'] = bb_std
            
            df_test = self.calculate_indicators(df, bb_std)
            trades = self.enhanced_conservative_strategy(df_test, config)
            
            if trades:
                total_pnl = sum(t['pnl_percent'] for t in trades)
                win_rate = len([t for t in trades if t['pnl_percent'] > 0]) / len(trades) * 100
                bb_results.append({
                    'std_dev': bb_std,
                    'trades': len(trades),
                    'pnl': round(total_pnl, 2),
                    'win_rate': round(win_rate, 1)
                })
        
        sensitivity_results['bollinger_bands'] = bb_results
        
        # Pruebas de sensibilidad Volumen
        print("📢 Probando umbrales de volumen...")
        volume_results = []
        for vol_threshold in self.sensitivity_tests['volume_thresholds']:
            config = self.optimal_config.copy()
            config['volume_threshold'] = vol_threshold
            
            df_test = self.calculate_indicators(df, config['bb_std'])
            trades = self.enhanced_conservative_strategy(df_test, config)
            
            if trades:
                total_pnl = sum(t['pnl_percent'] for t in trades)
                win_rate = len([t for t in trades if t['pnl_percent'] > 0]) / len(trades) * 100
                volume_results.append({
                    'threshold': vol_threshold,
                    'trades': len(trades),
                    'pnl': round(total_pnl, 2),
                    'win_rate': round(win_rate, 1)
                })
        
        sensitivity_results['volume'] = volume_results
        
        return sensitivity_results
    
    def run_stress_test(self) -> Dict:
        """Ejecutar prueba de estrés en diferentes condiciones de mercado"""
        print("\n⚡ PRUEBA DE ESTRÉS - DIFERENTES CONDICIONES DE MERCADO")
        print("=" * 60)
        
        # Períodos de diferentes condiciones
        stress_periods = [
            {'days': 7, 'label': 'Ultra_Corto'},
            {'days': 14, 'label': 'Corto'},
            {'days': 21, 'label': 'Medio'},
            {'days': 30, 'label': 'Estándar'},
            {'days': 45, 'label': 'Extendido'},
            {'days': 60, 'label': 'Largo_Plazo'}
        ]
        
        stress_results = []
        
        for period in stress_periods:
            print(f"⏰ Probando período {period['label']}: {period['days']} días")
            
            df = self.fetch_extended_data('ETH/USDT', '1h', period['days'])
            if df.empty or len(df) < 50:
                continue
                
            df = self.calculate_indicators(df, self.optimal_config['bb_std'])
            trades = self.enhanced_conservative_strategy(df, self.optimal_config)
            
            if not trades:
                stress_results.append({
                    'period': period['label'],
                    'days': period['days'],
                    'trades': 0,
                    'monthly_return': 0,
                    'win_rate': 0,
                    'status': 'Sin_Trades'
                })
                continue
            
            total_pnl = sum(t['pnl_percent'] for t in trades)
            monthly_return = (total_pnl / period['days']) * 30
            win_rate = len([t for t in trades if t['pnl_percent'] > 0]) / len(trades) * 100
            
            # Determinar estado del mercado por volatilidad
            volatility = df['close'].pct_change().std() * 100
            if volatility > 5:
                market_condition = 'Alto_Volatilidad'
            elif volatility < 2:
                market_condition = 'Bajo_Volatilidad'
            else:
                market_condition = 'Volatilidad_Normal'
            
            stress_results.append({
                'period': period['label'],
                'days': period['days'],
                'trades': len(trades),
                'pnl_percent': round(total_pnl, 2),
                'monthly_return': round(monthly_return, 2),
                'win_rate': round(win_rate, 1),
                'volatility': round(volatility, 2),
                'market_condition': market_condition,
                'status': 'Positivo' if monthly_return > 0 else 'Negativo'
            })
            
            print(f"  📊 {len(trades)} trades, {monthly_return:.2f}% mensual, {market_condition}")
        
        return stress_results

def main():
    """Función principal de validación"""
    print("🔬 SISTEMA V3 - VALIDACIÓN CRUZADA Y ANÁLISIS DE ROBUSTEZ")
    print("=" * 80)
    print("🎯 Análisis profundo de la configuración óptima encontrada")
    print("📈 ETH/USDT | 1h | Conservative | 40.57% mensual")
    print()
    
    validator = V3RobustnessValidator()
    
    # 1. Validación cruzada
    cross_val_results = validator.run_cross_validation_test()
    
    # 2. Análisis de sensibilidad
    sensitivity_results = validator.run_sensitivity_analysis()
    
    # 3. Prueba de estrés
    stress_results = validator.run_stress_test()
    
    # Análisis final
    print("\n📊 RESUMEN DE VALIDACIÓN CRUZADA")
    print("=" * 60)
    
    if 'periods' in cross_val_results:
        periods_data = cross_val_results['periods']
        positive_periods = [p for p in periods_data.values() if p['monthly_return'] > 0]
        
        print(f"✅ Períodos Rentables: {len(positive_periods)}/{len(periods_data)}")
        print(f"📈 Retorno Mensual Promedio: {np.mean([p['monthly_return'] for p in periods_data.values()]):.2f}%")
        print(f"🏆 Mejor Período: {max([p['monthly_return'] for p in periods_data.values()]):.2f}%")
        print(f"📉 Peor Período: {min([p['monthly_return'] for p in periods_data.values()]):.2f}%")
        
        print("\n🔍 DETALLE POR PERÍODO:")
        for label, data in periods_data.items():
            status = "✅" if data['monthly_return'] > 0 else "❌"
            print(f"  {status} {label}: {data['monthly_return']:.2f}% mensual, {data['trades']} trades, {data['win_rate']:.1f}% WR")
    
    print("\n🎯 ANÁLISIS DE SENSIBILIDAD")
    print("=" * 60)
    
    if 'rsi' in sensitivity_results:
        best_rsi = max(sensitivity_results['rsi'], key=lambda x: x['pnl'])
        print(f"🏆 Mejor RSI: {best_rsi['levels']} ({best_rsi['pnl']:.2f}%)")
    
    if 'bollinger_bands' in sensitivity_results:
        best_bb = max(sensitivity_results['bollinger_bands'], key=lambda x: x['pnl'])
        print(f"📊 Mejor BB Std: {best_bb['std_dev']} ({best_bb['pnl']:.2f}%)")
    
    if 'volume' in sensitivity_results:
        best_vol = max(sensitivity_results['volume'], key=lambda x: x['pnl'])
        print(f"📢 Mejor Volumen: {best_vol['threshold']} ({best_vol['pnl']:.2f}%)")
    
    print("\n⚡ ANÁLISIS DE ESTRÉS")
    print("=" * 60)
    
    if stress_results:
        positive_stress = [s for s in stress_results if s['monthly_return'] > 0]
        print(f"💪 Períodos Resistentes: {len(positive_stress)}/{len(stress_results)}")
        
        for result in stress_results:
            status = "✅" if result['monthly_return'] > 0 else "❌"
            print(f"  {status} {result['period']}: {result['monthly_return']:.2f}% ({result['market_condition']})")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    final_results = {
        'timestamp': timestamp,
        'optimal_config': validator.optimal_config,
        'cross_validation': cross_val_results,
        'sensitivity_analysis': sensitivity_results,
        'stress_test': stress_results
    }
    
    with open(f'V3_ROBUSTNESS_VALIDATION_{timestamp}.json', 'w') as f:
        json.dump(final_results, f, indent=2, default=str)
    
    print(f"\n💾 Resultados detallados guardados: V3_ROBUSTNESS_VALIDATION_{timestamp}.json")
    print("🎯 VALIDACIÓN DE ROBUSTEZ COMPLETADA")

if __name__ == "__main__":
    main()
