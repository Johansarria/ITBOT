#!/usr/bin/env python3
"""
Estrategia Ultra Selectiva de Símbolos Independientes
Detecta únicamente señales de máxima calidad e independencia
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

class UltraSelectiveAnalyzer:
    """Analizador ultra selectivo para señales independientes"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        
    def get_symbol_data(self, symbol: str, days: int) -> pd.DataFrame:
        """Obtiene datos históricos para un símbolo específico"""
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
            
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col])
                
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"Error obteniendo datos para {symbol}: {e}")
            return pd.DataFrame()

class UltraSelectiveStrategy:
    """Estrategia ultra selectiva que detecta solo las mejores señales independientes"""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.analyzer = UltraSelectiveAnalyzer()
        
        # Criterios ultra estrictos para independencia
        self.ultra_criteria = {
            'min_independence_score': 0.90,  # Puntuación mínima 90%
            'volume_explosion': 3.0,         # Volumen 3x superior
            'price_breakout': 0.08,          # Movimiento > 8%
            'rsi_extreme': 25,               # RSI extremo
            'volatility_surge': 2.5,         # Volatilidad 2.5x
            'pattern_perfection': 0.95,      # Patrón casi perfecto
            'momentum_strength': 0.12,       # Momentum > 12%
            'confluence_factors': 5          # Mínimo 5 factores confluentes
        }
        
    def calculate_ultra_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores ultra precisos"""
        if len(df) < 200:
            return df
            
        # RSI múltiples timeframes
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # RSI 21 y 7 para confluencia
        gain_21 = (delta.where(delta > 0, 0)).rolling(window=21).mean()
        loss_21 = (-delta.where(delta < 0, 0)).rolling(window=21).mean()
        rs_21 = gain_21 / loss_21
        df['rsi_21'] = 100 - (100 / (1 + rs_21))
        
        gain_7 = (delta.where(delta > 0, 0)).rolling(window=7).mean()
        loss_7 = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
        rs_7 = gain_7 / loss_7
        df['rsi_7'] = 100 - (100 / (1 + rs_7))
        
        # EMAs múltiples para confluencia
        df['ema_8'] = df['close'].ewm(span=8).mean()
        df['ema_13'] = df['close'].ewm(span=13).mean()
        df['ema_21'] = df['close'].ewm(span=21).mean()
        df['ema_34'] = df['close'].ewm(span=34).mean()
        df['ema_55'] = df['close'].ewm(span=55).mean()
        df['ema_89'] = df['close'].ewm(span=89).mean()
        
        # MACD múltiple
        df['macd_12_26'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
        df['macd_signal_12_26'] = df['macd_12_26'].ewm(span=9).mean()
        df['macd_hist_12_26'] = df['macd_12_26'] - df['macd_signal_12_26']
        
        df['macd_8_21'] = df['close'].ewm(span=8).mean() - df['close'].ewm(span=21).mean()
        df['macd_signal_8_21'] = df['macd_8_21'].ewm(span=5).mean()
        df['macd_hist_8_21'] = df['macd_8_21'] - df['macd_signal_8_21']
        
        # Bollinger Bands múltiples
        df['sma_20'] = df['close'].rolling(window=20).mean()
        bb_std_20 = df['close'].rolling(window=20).std()
        df['bb_upper_20'] = df['sma_20'] + (bb_std_20 * 2)
        df['bb_lower_20'] = df['sma_20'] - (bb_std_20 * 2)
        df['bb_width_20'] = (df['bb_upper_20'] - df['bb_lower_20']) / df['sma_20']
        
        df['sma_10'] = df['close'].rolling(window=10).mean()
        bb_std_10 = df['close'].rolling(window=10).std()
        df['bb_upper_10'] = df['sma_10'] + (bb_std_10 * 2)
        df['bb_lower_10'] = df['sma_10'] - (bb_std_10 * 2)
        
        # Volumen y volatilidad avanzados
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_sma_50'] = df['volume'].rolling(window=50).mean()
        df['volume_ratio_20'] = df['volume'] / df['volume_sma_20']
        df['volume_ratio_50'] = df['volume'] / df['volume_sma_50']
        
        df['volatility_10'] = df['close'].pct_change().rolling(window=10).std()
        df['volatility_20'] = df['close'].pct_change().rolling(window=20).std()
        df['volatility_50'] = df['close'].pct_change().rolling(window=50).std()
        
        # Momentum múltiple
        df['momentum_1h'] = df['close'].pct_change(1)
        df['momentum_2h'] = df['close'].pct_change(2)
        df['momentum_4h'] = df['close'].pct_change(4)
        df['momentum_8h'] = df['close'].pct_change(8)
        df['momentum_24h'] = df['close'].pct_change(24)
        
        # Niveles dinámicos de soporte/resistencia
        df['pivot_high'] = df['high'].rolling(window=10, center=True).max()
        df['pivot_low'] = df['low'].rolling(window=10, center=True).min()
        df['resistance_1'] = df['high'].rolling(window=50).max()
        df['support_1'] = df['low'].rolling(window=50).min()
        
        # Indicadores de confluencia
        df['ema_alignment'] = ((df['ema_8'] > df['ema_13']) & 
                              (df['ema_13'] > df['ema_21']) & 
                              (df['ema_21'] > df['ema_34'])).astype(int)
        
        df['rsi_confluence'] = ((df['rsi_7'] > 50) & 
                               (df['rsi_14'] > 50) & 
                               (df['rsi_21'] > 50)).astype(int)
        
        return df
        
    def detect_ultra_signals(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """Detecta únicamente señales ultra selectivas"""
        ultra_signals = []
        
        if len(df) < 200:
            return ultra_signals
            
        for i in range(200, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            prev_5 = df.iloc[i-5]
            prev_10 = df.iloc[i-10]
            
            confluence_score = 0
            confluence_factors = []
            
            # 1. EXPLOSIÓN DE VOLUMEN EXTREMA
            if (current['volume_ratio_20'] >= self.ultra_criteria['volume_explosion'] and
                current['volume_ratio_50'] >= 2.0):
                confluence_score += 0.20
                confluence_factors.append('Volume Explosion')
                
            # 2. BREAKOUT DE PRECIO SIGNIFICATIVO
            if abs(current['momentum_1h']) >= self.ultra_criteria['price_breakout']:
                confluence_score += 0.18
                confluence_factors.append('Price Breakout')
                
            # 3. RSI CONFLUENCIA EXTREMA
            rsi_momentum = current['rsi_14'] - prev_5['rsi_14']
            if (current['rsi_14'] < 35 and rsi_momentum > self.ultra_criteria['rsi_extreme'] and
                current['rsi_confluence'] == 1):
                confluence_score += 0.25
                confluence_factors.append('RSI Extreme Confluence')
                
            # 4. VOLATILIDAD SURGE
            vol_ratio = current['volatility_10'] / df['volatility_50'].rolling(50).mean().iloc[i]
            if vol_ratio >= self.ultra_criteria['volatility_surge']:
                confluence_score += 0.15
                confluence_factors.append('Volatility Surge')
                
            # 5. MACD DOBLE CONFIRMACIÓN
            if (current['macd_12_26'] > current['macd_signal_12_26'] and
                prev['macd_12_26'] <= prev['macd_signal_12_26'] and
                current['macd_8_21'] > current['macd_signal_8_21'] and
                current['macd_hist_12_26'] > 0 and current['macd_hist_8_21'] > 0):
                confluence_score += 0.22
                confluence_factors.append('MACD Double Confirmation')
                
            # 6. EMA PERFECT ALIGNMENT
            if (current['ema_alignment'] == 1 and
                current['close'] > current['ema_8'] and
                current['ema_8'] > prev['ema_8']):
                confluence_score += 0.18
                confluence_factors.append('EMA Perfect Alignment')
                
            # 7. BOLLINGER SQUEEZE BREAK EXTREMO
            if (current['bb_width_20'] < df['bb_width_20'].rolling(50).mean().iloc[i] * 0.6 and
                current['close'] > current['bb_upper_20'] and
                current['volume_ratio_20'] > 2.5):
                confluence_score += 0.20
                confluence_factors.append('BB Extreme Squeeze Break')
                
            # 8. MOMENTUM MULTI-TIMEFRAME
            momentum_alignment = (current['momentum_1h'] > 0.02 and
                                current['momentum_2h'] > 0.03 and
                                current['momentum_4h'] > 0.05)
            if momentum_alignment:
                confluence_score += 0.15
                confluence_factors.append('Multi-TF Momentum')
                
            # 9. RESISTANCE BREAK CON VOLUMEN
            if (current['close'] > current['resistance_1'] * 1.005 and
                current['volume_ratio_20'] > 2.0 and
                current['momentum_1h'] > 0.03):
                confluence_score += 0.25
                confluence_factors.append('Resistance Break + Volume')
                
            # 10. DIVERGENCIA ALCISTA PERFECTA
            if i >= 210:
                price_trend_10 = (current['close'] - prev_10['close']) / prev_10['close']
                rsi_trend_10 = current['rsi_14'] - prev_10['rsi_14']
                
                if (price_trend_10 < -0.05 and rsi_trend_10 > 20 and
                    current['rsi_14'] < 40):
                    confluence_score += 0.30
                    confluence_factors.append('Perfect Bullish Divergence')
                    
            # FILTROS ULTRA ESTRICTOS
            if (confluence_score >= self.ultra_criteria['min_independence_score'] and
                len(confluence_factors) >= self.ultra_criteria['confluence_factors']):
                
                # Calcular TP/SL ultra precisos
                recent_volatility = current['volatility_10']
                atr_equivalent = (current['high'] - current['low']) / current['close']
                
                # TP/SL basado en volatilidad y momentum
                base_tp = max(0.12, min(0.25, recent_volatility * 6))
                base_sl = max(0.04, min(0.10, recent_volatility * 2.5))
                
                # Ajustar por fuerza de la señal
                signal_strength = min(confluence_score * 1.1, 1.0)
                tp_pct = base_tp * signal_strength
                sl_pct = base_sl * (2 - signal_strength)  # SL más ajustado para señales fuertes
                
                ultra_signal = {
                    'timestamp': df.index[i],
                    'symbol': symbol,
                    'price': current['close'],
                    'confluence_score': confluence_score,
                    'confluence_factors': confluence_factors,
                    'signal_strength': signal_strength,
                    'tp_price': current['close'] * (1 + tp_pct),
                    'sl_price': current['close'] * (1 - sl_pct),
                    'tp_pct': tp_pct * 100,
                    'sl_pct': sl_pct * 100,
                    'volume_ratio': current['volume_ratio_20'],
                    'rsi_14': current['rsi_14'],
                    'momentum_1h': current['momentum_1h'] * 100,
                    'volatility': recent_volatility * 100
                }
                
                ultra_signals.append(ultra_signal)
                
        return ultra_signals
        
    def analyze_symbol_ultra_selective(self, symbol: str, days: int) -> Dict:
        """Análisis ultra selectivo de un símbolo"""
        print(f"\n=== ANÁLISIS ULTRA SELECTIVO: {symbol} ===")
        
        # Obtener datos
        df = self.analyzer.get_symbol_data(symbol, days)
        if df.empty:
            return {'symbol': symbol, 'status': 'No Data', 'signals': []}
            
        print(f"Datos obtenidos: {len(df)} registros")
        
        # Calcular indicadores ultra precisos
        df = self.calculate_ultra_indicators(df)
        
        # Detectar señales ultra selectivas
        ultra_signals = self.detect_ultra_signals(symbol, df)
        
        print(f"Señales ultra selectivas detectadas: {len(ultra_signals)}")
        
        # Clasificar por calidad extrema
        perfect_signals = [s for s in ultra_signals if s['confluence_score'] >= 0.95]
        excellent_signals = [s for s in ultra_signals if 0.90 <= s['confluence_score'] < 0.95]
        
        result = {
            'symbol': symbol,
            'status': 'Analyzed',
            'total_signals': len(ultra_signals),
            'perfect_signals': len(perfect_signals),
            'excellent_signals': len(excellent_signals),
            'signals': ultra_signals,
            'data_points': len(df),
            'analysis_period': f"{days} days"
        }
        
        # Mostrar señales perfectas
        if perfect_signals:
            print(f"\nSEÑALES PERFECTAS ({len(perfect_signals)}):")
            for i, signal in enumerate(perfect_signals[:2], 1):
                print(f"  {i}. {signal['timestamp']} - Score: {signal['confluence_score']:.3f}")
                print(f"     Factores: {', '.join(signal['confluence_factors'][:3])}...")
                print(f"     Precio: ${signal['price']:.4f} | TP: {signal['tp_pct']:.1f}% | SL: {signal['sl_pct']:.1f}%")
                print(f"     Vol: {signal['volume_ratio']:.1f}x | RSI: {signal['rsi_14']:.1f} | Mom: {signal['momentum_1h']:.1f}%")
                
        elif excellent_signals:
            print(f"\nSEÑALES EXCELENTES ({len(excellent_signals)}):")
            for i, signal in enumerate(excellent_signals[:2], 1):
                print(f"  {i}. {signal['timestamp']} - Score: {signal['confluence_score']:.3f}")
                print(f"     Factores: {', '.join(signal['confluence_factors'][:3])}...")
                print(f"     Precio: ${signal['price']:.4f} | TP: {signal['tp_pct']:.1f}% | SL: {signal['sl_pct']:.1f}%")
                
        return result
        
    def run_ultra_analysis(self, symbols: List[str], days: int) -> Dict:
        """Ejecuta análisis ultra selectivo"""
        print(f"\n{'='*70}")
        print(f"ANÁLISIS ULTRA SELECTIVO - {days} DÍAS")
        print(f"Criterio mínimo: {self.ultra_criteria['min_independence_score']*100}% confluencia")
        print(f"{'='*70}")
        
        results = {}
        summary = {
            'total_symbols': len(symbols),
            'analyzed_symbols': 0,
            'total_signals': 0,
            'perfect_signals': 0,
            'excellent_signals': 0,
            'elite_symbols': []
        }
        
        for symbol in symbols:
            try:
                result = self.analyze_symbol_ultra_selective(symbol, days)
                results[symbol] = result
                
                if result['status'] == 'Analyzed':
                    summary['analyzed_symbols'] += 1
                    summary['total_signals'] += result['total_signals']
                    summary['perfect_signals'] += result['perfect_signals']
                    summary['excellent_signals'] += result['excellent_signals']
                    
                    # Solo símbolos con señales perfectas o múltiples excelentes
                    if (result['perfect_signals'] > 0 or result['excellent_signals'] >= 2):
                        max_score = max([s['confluence_score'] for s in result['signals']]) if result['signals'] else 0
                        summary['elite_symbols'].append({
                            'symbol': symbol,
                            'perfect_signals': result['perfect_signals'],
                            'excellent_signals': result['excellent_signals'],
                            'max_score': max_score
                        })
                        
            except Exception as e:
                print(f"Error analizando {symbol}: {e}")
                results[symbol] = {'symbol': symbol, 'status': 'Error', 'error': str(e)}
                
        # Ordenar símbolos elite
        summary['elite_symbols'].sort(key=lambda x: (x['perfect_signals'], x['excellent_signals']), reverse=True)
        
        return {'results': results, 'summary': summary}
        
    def generate_ultra_report(self, analysis_results: Dict, days: int) -> str:
        """Genera reporte ultra selectivo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ultra_selective_{days}days_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"ANÁLISIS ULTRA SELECTIVO DE SÍMBOLOS INDEPENDIENTES\n")
            f.write(f"Período: {days} días | Criterio: ≥90% confluencia\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
            
            summary = analysis_results['summary']
            f.write(f"RESUMEN ULTRA SELECTIVO:\n")
            f.write(f"Símbolos analizados: {summary['analyzed_symbols']}/{summary['total_symbols']}\n")
            f.write(f"Señales detectadas: {summary['total_signals']}\n")
            f.write(f"Señales PERFECTAS (≥95%): {summary['perfect_signals']}\n")
            f.write(f"Señales EXCELENTES (90-95%): {summary['excellent_signals']}\n")
            f.write(f"Símbolos ELITE: {len(summary['elite_symbols'])}\n\n")
            
            if summary['elite_symbols']:
                f.write(f"RANKING SÍMBOLOS ELITE:\n")
                f.write(f"{'='*50}\n")
                for i, symbol_data in enumerate(summary['elite_symbols'], 1):
                    f.write(f"{i:2d}. {symbol_data['symbol']:10s} - ")
                    f.write(f"Perfect: {symbol_data['perfect_signals']}, ")
                    f.write(f"Excellent: {symbol_data['excellent_signals']} ")
                    f.write(f"(Max: {symbol_data['max_score']:.3f})\n")
                    
                f.write(f"\nDETALLE SÍMBOLOS ELITE:\n")
                f.write(f"{'='*80}\n")
                
                for symbol_data in summary['elite_symbols']:
                    symbol = symbol_data['symbol']
                    result = analysis_results['results'][symbol]
                    
                    f.write(f"\n{symbol}:\n")
                    f.write(f"  Señales perfectas: {result['perfect_signals']}\n")
                    f.write(f"  Señales excelentes: {result['excellent_signals']}\n")
                    
                    # Mejores señales
                    top_signals = sorted(result['signals'], key=lambda x: x['confluence_score'], reverse=True)[:2]
                    if top_signals:
                        f.write(f"  \n  TOP SEÑALES:\n")
                        for j, signal in enumerate(top_signals, 1):
                            f.write(f"    {j}. {signal['timestamp']} - Score: {signal['confluence_score']:.3f}\n")
                            f.write(f"       Factores: {', '.join(signal['confluence_factors'][:4])}\n")
                            f.write(f"       Precio: ${signal['price']:.4f} | TP: {signal['tp_pct']:.1f}% | SL: {signal['sl_pct']:.1f}%\n")
                            f.write(f"       Vol: {signal['volume_ratio']:.1f}x | RSI: {signal['rsi_14']:.1f} | Mom: {signal['momentum_1h']:.1f}%\n")
            else:
                f.write(f"No se detectaron símbolos que cumplan los criterios ultra selectivos.\n")
                f.write(f"Considere reducir el umbral de confluencia o ampliar el período de análisis.\n")
                
        return filename

def main():
    """Función principal ultra selectiva"""
    # Símbolos para análisis ultra selectivo
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 
               'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'XRPUSDT', 'MATICUSDT',
               'AVAXUSDT', 'ATOMUSDT', 'NEARUSDT', 'FTMUSDT', 'SANDUSDT']
    
    # Períodos de análisis
    test_periods = [60, 90, 120]
    
    for days in test_periods:
        print(f"\n{'='*80}")
        print(f"INICIANDO ANÁLISIS ULTRA SELECTIVO - {days} DÍAS")
        print(f"{'='*80}")
        
        strategy = UltraSelectiveStrategy(initial_capital=1000.0)
        analysis_results = strategy.run_ultra_analysis(symbols, days)
        
        # Generar reporte
        report_file = strategy.generate_ultra_report(analysis_results, days)
        
        # Mostrar resumen
        summary = analysis_results['summary']
        print(f"\n=== RESUMEN ULTRA SELECTIVO {days} DÍAS ===")
        print(f"Símbolos ELITE detectados: {len(summary['elite_symbols'])}")
        print(f"Señales PERFECTAS: {summary['perfect_signals']}")
        print(f"Señales EXCELENTES: {summary['excellent_signals']}")
        
        if summary['elite_symbols']:
            print(f"\nTOP SÍMBOLOS ELITE:")
            for i, symbol_data in enumerate(summary['elite_symbols'][:3], 1):
                print(f"  {i}. {symbol_data['symbol']} - Perfect: {symbol_data['perfect_signals']}, Excellent: {symbol_data['excellent_signals']}")
        else:
            print(f"\n⚠️  No se detectaron símbolos que cumplan los criterios ultra selectivos")
            print(f"   Los criterios son extremadamente estrictos (≥90% confluencia)")
                
        print(f"\nReporte guardado en: {report_file}")
        
if __name__ == "__main__":
    main()