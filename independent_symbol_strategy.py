#!/usr/bin/env python3
"""
Estrategia de Detección de Símbolos Independientes
Analiza cada símbolo por separado para detectar señales específicas e independientes
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

class IndependentSymbolAnalyzer:
    """Analizador de símbolos independientes"""
    
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

class IndependentSymbolStrategy:
    """Estrategia que detecta símbolos independientes con señales específicas"""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.analyzer = IndependentSymbolAnalyzer()
        self.symbol_results = {}
        
        # Parámetros específicos para detección independiente
        self.min_independence_score = 0.75  # Puntuación mínima de independencia
        self.trade_amount_per_symbol = initial_capital * 0.20  # 20% por símbolo
        
        # Criterios de independencia
        self.independence_criteria = {
            'volume_spike': 2.0,      # Volumen 2x superior al promedio
            'price_momentum': 0.05,   # Movimiento de precio > 5%
            'rsi_divergence': 15,     # Divergencia RSI > 15 puntos
            'volatility_breakout': 1.5, # Volatilidad 1.5x superior
            'pattern_strength': 0.8   # Fuerza del patrón > 80%
        }
        
    def calculate_advanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores avanzados para análisis independiente"""
        if len(df) < 100:
            return df
            
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Medias móviles múltiples
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_100'] = df['close'].rolling(window=100).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['sma_20']
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Volatilidad y volumen
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        df['avg_volume'] = df['volume'].rolling(window=50).mean()
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        
        # Momentum indicators
        df['price_change_1h'] = df['close'].pct_change(1)
        df['price_change_4h'] = df['close'].pct_change(4)
        df['price_change_24h'] = df['close'].pct_change(24)
        
        # Support/Resistance levels
        df['local_high'] = df['high'].rolling(window=20, center=True).max()
        df['local_low'] = df['low'].rolling(window=20, center=True).min()
        
        return df
        
    def detect_independence_signals(self, symbol: str, df: pd.DataFrame) -> List[Dict]:
        """Detecta señales independientes específicas para cada símbolo"""
        signals = []
        
        if len(df) < 100:
            return signals
            
        for i in range(100, len(df)):
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Verificar criterios de independencia
            independence_score = 0
            signal_details = {
                'timestamp': df.index[i],
                'symbol': symbol,
                'price': current['close'],
                'independence_factors': []
            }
            
            # 1. Volume Spike (señal independiente fuerte)
            if (current['volume_ratio'] >= self.independence_criteria['volume_spike'] and
                current['volume_ratio'] > prev['volume_ratio'] * 1.2):
                independence_score += 0.25
                signal_details['independence_factors'].append('Volume Spike')
                
            # 2. Price Momentum Breakout
            if abs(current['price_change_1h']) >= self.independence_criteria['price_momentum']:
                independence_score += 0.20
                signal_details['independence_factors'].append('Price Momentum')
                
            # 3. RSI Divergence
            if i >= 105:  # Necesitamos más datos para divergencia
                price_trend = (current['close'] - df.iloc[i-5]['close']) / df.iloc[i-5]['close']
                rsi_trend = current['rsi'] - df.iloc[i-5]['rsi']
                
                # Divergencia alcista: precio baja, RSI sube
                if price_trend < -0.02 and rsi_trend > self.independence_criteria['rsi_divergence']:
                    independence_score += 0.30
                    signal_details['independence_factors'].append('Bullish RSI Divergence')
                    
            # 4. Volatility Breakout
            if (current['volatility'] >= df['volatility'].rolling(50).mean().iloc[i] * 
                self.independence_criteria['volatility_breakout']):
                independence_score += 0.15
                signal_details['independence_factors'].append('Volatility Breakout')
                
            # 5. MACD Signal
            if (current['macd'] > current['macd_signal'] and 
                prev['macd'] <= prev['macd_signal'] and
                current['macd_histogram'] > 0):
                independence_score += 0.20
                signal_details['independence_factors'].append('MACD Bullish Cross')
                
            # 6. Bollinger Band Squeeze Break
            if (current['bb_width'] < df['bb_width'].rolling(20).mean().iloc[i] * 0.8 and
                current['close'] > current['bb_upper']):
                independence_score += 0.25
                signal_details['independence_factors'].append('BB Squeeze Break')
                
            # 7. Support/Resistance Break
            if (current['close'] > current['local_high'] * 1.001 and  # Break resistance
                current['volume_ratio'] > 1.5):
                independence_score += 0.20
                signal_details['independence_factors'].append('Resistance Break')
                
            # Solo considerar señales con alta independencia
            if independence_score >= self.min_independence_score:
                signal_details['independence_score'] = independence_score
                signal_details['signal_strength'] = min(independence_score * 1.2, 1.0)
                
                # Calcular TP/SL dinámicos basados en volatilidad del símbolo
                volatility = current['volatility']
                tp_pct = max(0.08, min(0.20, volatility * 4))  # 8-20% TP
                sl_pct = max(0.03, min(0.08, volatility * 2))  # 3-8% SL
                
                signal_details['tp_price'] = current['close'] * (1 + tp_pct)
                signal_details['sl_price'] = current['close'] * (1 - sl_pct)
                signal_details['tp_pct'] = tp_pct * 100
                signal_details['sl_pct'] = sl_pct * 100
                
                signals.append(signal_details)
                
        return signals
        
    def analyze_symbol_independently(self, symbol: str, days: int) -> Dict:
        """Analiza un símbolo de forma completamente independiente"""
        print(f"\n=== ANÁLISIS INDEPENDIENTE: {symbol} ===")
        
        # Obtener datos del símbolo
        df = self.analyzer.get_symbol_data(symbol, days)
        if df.empty:
            return {'symbol': symbol, 'status': 'No Data', 'signals': []}
            
        print(f"Datos obtenidos: {len(df)} registros")
        
        # Calcular indicadores
        df = self.calculate_advanced_indicators(df)
        
        # Detectar señales independientes
        signals = self.detect_independence_signals(symbol, df)
        
        print(f"Señales independientes detectadas: {len(signals)}")
        
        # Análisis de calidad de señales
        high_quality_signals = [s for s in signals if s['independence_score'] >= 0.85]
        medium_quality_signals = [s for s in signals if 0.75 <= s['independence_score'] < 0.85]
        
        result = {
            'symbol': symbol,
            'status': 'Analyzed',
            'total_signals': len(signals),
            'high_quality_signals': len(high_quality_signals),
            'medium_quality_signals': len(medium_quality_signals),
            'signals': signals,
            'data_points': len(df),
            'analysis_period': f"{days} days"
        }
        
        # Mostrar mejores señales
        if high_quality_signals:
            print(f"\nMEJORES SEÑALES INDEPENDIENTES ({len(high_quality_signals)}):")
            for i, signal in enumerate(high_quality_signals[:3], 1):
                print(f"  {i}. {signal['timestamp']} - Score: {signal['independence_score']:.2f}")
                print(f"     Factores: {', '.join(signal['independence_factors'])}")
                print(f"     Precio: ${signal['price']:.4f} | TP: {signal['tp_pct']:.1f}% | SL: {signal['sl_pct']:.1f}%")
                
        return result
        
    def run_independent_analysis(self, symbols: List[str], days: int) -> Dict:
        """Ejecuta análisis independiente para múltiples símbolos"""
        print(f"\n{'='*60}")
        print(f"ANÁLISIS DE SÍMBOLOS INDEPENDIENTES - {days} DÍAS")
        print(f"{'='*60}")
        
        results = {}
        summary = {
            'total_symbols': len(symbols),
            'analyzed_symbols': 0,
            'total_signals': 0,
            'high_quality_signals': 0,
            'best_symbols': []
        }
        
        for symbol in symbols:
            try:
                result = self.analyze_symbol_independently(symbol, days)
                results[symbol] = result
                
                if result['status'] == 'Analyzed':
                    summary['analyzed_symbols'] += 1
                    summary['total_signals'] += result['total_signals']
                    summary['high_quality_signals'] += result['high_quality_signals']
                    
                    # Identificar mejores símbolos
                    if result['high_quality_signals'] > 0:
                        summary['best_symbols'].append({
                            'symbol': symbol,
                            'high_quality_signals': result['high_quality_signals'],
                            'independence_score': max([s['independence_score'] for s in result['signals']])
                        })
                        
            except Exception as e:
                print(f"Error analizando {symbol}: {e}")
                results[symbol] = {'symbol': symbol, 'status': 'Error', 'error': str(e)}
                
        # Ordenar mejores símbolos
        summary['best_symbols'].sort(key=lambda x: x['high_quality_signals'], reverse=True)
        
        return {'results': results, 'summary': summary}
        
    def generate_independent_report(self, analysis_results: Dict, days: int) -> str:
        """Genera reporte detallado del análisis independiente"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"independent_analysis_{days}days_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"ANÁLISIS DE SÍMBOLOS INDEPENDIENTES\n")
            f.write(f"Período: {days} días\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
            
            summary = analysis_results['summary']
            f.write(f"RESUMEN EJECUTIVO:\n")
            f.write(f"Símbolos analizados: {summary['analyzed_symbols']}/{summary['total_symbols']}\n")
            f.write(f"Total señales detectadas: {summary['total_signals']}\n")
            f.write(f"Señales de alta calidad: {summary['high_quality_signals']}\n")
            f.write(f"Tasa de calidad: {(summary['high_quality_signals']/max(summary['total_signals'],1)*100):.1f}%\n\n")
            
            f.write(f"RANKING DE SÍMBOLOS INDEPENDIENTES:\n")
            f.write(f"{'='*50}\n")
            for i, symbol_data in enumerate(summary['best_symbols'][:10], 1):
                f.write(f"{i:2d}. {symbol_data['symbol']:10s} - {symbol_data['high_quality_signals']} señales ")
                f.write(f"(Score máx: {symbol_data['independence_score']:.2f})\n")
                
            f.write(f"\nDETALLE POR SÍMBOLO:\n")
            f.write(f"{'='*80}\n")
            
            for symbol, result in analysis_results['results'].items():
                if result['status'] == 'Analyzed' and result['high_quality_signals'] > 0:
                    f.write(f"\n{symbol}:\n")
                    f.write(f"  Señales totales: {result['total_signals']}\n")
                    f.write(f"  Señales alta calidad: {result['high_quality_signals']}\n")
                    f.write(f"  Señales media calidad: {result['medium_quality_signals']}\n")
                    
                    # Mejores señales del símbolo
                    high_signals = [s for s in result['signals'] if s['independence_score'] >= 0.85]
                    if high_signals:
                        f.write(f"  \n  MEJORES SEÑALES:\n")
                        for j, signal in enumerate(high_signals[:3], 1):
                            f.write(f"    {j}. {signal['timestamp']} - Score: {signal['independence_score']:.2f}\n")
                            f.write(f"       Factores: {', '.join(signal['independence_factors'])}\n")
                            f.write(f"       Precio: ${signal['price']:.4f} | TP: {signal['tp_pct']:.1f}% | SL: {signal['sl_pct']:.1f}%\n")
                            
        return filename

def main():
    """Función principal"""
    # Símbolos para análisis independiente
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 
               'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'XRPUSDT', 'MATICUSDT']
    
    # Períodos de análisis
    test_periods = [30, 60, 90]
    
    for days in test_periods:
        print(f"\n{'='*80}")
        print(f"INICIANDO ANÁLISIS INDEPENDIENTE - {days} DÍAS")
        print(f"{'='*80}")
        
        strategy = IndependentSymbolStrategy(initial_capital=1000.0)
        analysis_results = strategy.run_independent_analysis(symbols, days)
        
        # Generar reporte
        report_file = strategy.generate_independent_report(analysis_results, days)
        
        # Mostrar resumen
        summary = analysis_results['summary']
        print(f"\n=== RESUMEN {days} DÍAS ===")
        print(f"Símbolos con señales independientes: {len(summary['best_symbols'])}")
        print(f"Total señales de alta calidad: {summary['high_quality_signals']}")
        
        if summary['best_symbols']:
            print(f"\nTOP 3 SÍMBOLOS INDEPENDIENTES:")
            for i, symbol_data in enumerate(summary['best_symbols'][:3], 1):
                print(f"  {i}. {symbol_data['symbol']} - {symbol_data['high_quality_signals']} señales")
                
        print(f"\nReporte guardado en: {report_file}")
        
if __name__ == "__main__":
    main()