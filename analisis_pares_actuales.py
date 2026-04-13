#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Análisis de Pares con Datos Actuales de Binance
Descarga datos en tiempo real para determinar los mejores pares para trading
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class BinanceCurrentAnalyzer:
    """Analizador de pares con datos actuales de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.top_pairs = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'XRPUSDT', 'DOGEUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT',
            'UNIUSDT', 'AVAXUSDT', 'MATICUSDT', 'ATOMUSDT', 'FILUSDT'
        ]
        
    def get_24h_ticker_stats(self) -> Dict:
        """Obtiene estadísticas de 24h para todos los pares"""
        try:
            url = f"{self.base_url}/ticker/24hr"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                # Filtrar solo pares USDT de alto volumen
                usdt_pairs = [item for item in data if item['symbol'].endswith('USDT') and float(item['quoteVolume']) > 10000000]
                return {item['symbol']: item for item in usdt_pairs}
            else:
                print(f"Error obteniendo datos 24h: {response.status_code}")
                return {}
        except Exception as e:
            print(f"Error en get_24h_ticker_stats: {e}")
            return {}
    
    def get_current_klines(self, symbol: str, interval: str = '1h', limit: int = 24) -> pd.DataFrame:
        """Obtiene datos de velas actuales para un símbolo"""
        try:
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_asset_volume', 'number_of_trades',
                    'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                ])
                
                # Convertir tipos
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col])
                
                df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                df.set_index('timestamp', inplace=True)
                
                return df
            else:
                print(f"Error obteniendo klines para {symbol}: {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error en get_current_klines para {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_volatility_metrics(self, df: pd.DataFrame) -> Dict:
        """Calcula métricas de volatilidad y momentum"""
        if df.empty or len(df) < 10:
            return {}
        
        try:
            # Calcular retornos
            df['returns'] = df['close'].pct_change()
            
            # Volatilidad (desviación estándar de retornos)
            volatility = df['returns'].std() * np.sqrt(24)  # Anualizada para 1h
            
            # Rango promedio (high-low)/close
            df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100
            avg_range = df['range_pct'].mean()
            
            # Momentum (cambio en las últimas 6 horas)
            momentum_6h = (df['close'].iloc[-1] - df['close'].iloc[-7]) / df['close'].iloc[-7] * 100 if len(df) >= 7 else 0
            
            # Momentum 24h
            momentum_24h = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0] * 100
            
            # Volumen promedio
            avg_volume = df['volume'].mean()
            
            # Tendencia (regresión lineal simple)
            x = np.arange(len(df))
            y = df['close'].values
            slope = np.polyfit(x, y, 1)[0]
            trend_strength = slope / df['close'].mean() * 100
            
            return {
                'volatility': volatility,
                'avg_range_pct': avg_range,
                'momentum_6h': momentum_6h,
                'momentum_24h': momentum_24h,
                'avg_volume': avg_volume,
                'trend_strength': trend_strength,
                'current_price': df['close'].iloc[-1]
            }
            
        except Exception as e:
            print(f"Error calculando métricas: {e}")
            return {}
    
    def analyze_all_pairs(self) -> List[Dict]:
        """Analiza todos los pares principales"""
        print("🔍 Analizando pares con datos actuales de Binance...")
        print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Obtener estadísticas 24h
        ticker_stats = self.get_24h_ticker_stats()
        
        results = []
        
        for symbol in self.top_pairs:
            print(f"📊 Analizando {symbol}...")
            
            # Obtener datos de velas
            df = self.get_current_klines(symbol, '1h', 24)
            
            if df.empty:
                continue
            
            # Calcular métricas
            metrics = self.calculate_volatility_metrics(df)
            
            if not metrics:
                continue
            
            # Agregar datos de ticker 24h
            ticker_data = ticker_stats.get(symbol, {})
            
            result = {
                'symbol': symbol,
                'current_price': metrics['current_price'],
                'volatility': metrics['volatility'],
                'avg_range_pct': metrics['avg_range_pct'],
                'momentum_6h': metrics['momentum_6h'],
                'momentum_24h': metrics['momentum_24h'],
                'trend_strength': metrics['trend_strength'],
                'volume_24h': float(ticker_data.get('volume', 0)),
                'quote_volume_24h': float(ticker_data.get('quoteVolume', 0)),
                'price_change_24h': float(ticker_data.get('priceChangePercent', 0)),
                'high_24h': float(ticker_data.get('highPrice', 0)),
                'low_24h': float(ticker_data.get('lowPrice', 0))
            }
            
            results.append(result)
            time.sleep(0.1)  # Rate limiting
        
        return results
    
    def rank_pairs_for_trading(self, results: List[Dict]) -> List[Dict]:
        """Rankea los pares según criterios de trading"""
        if not results:
            return []
        
        # Calcular score compuesto para cada par
        for result in results:
            score = 0
            
            # Volatilidad (más volatilidad = más oportunidades, pero controlada)
            vol_score = min(result['volatility'] * 100, 10)  # Cap en 10
            score += vol_score * 0.3
            
            # Rango promedio (más rango = más oportunidades)
            range_score = min(result['avg_range_pct'], 10)  # Cap en 10
            score += range_score * 0.25
            
            # Momentum positivo (preferimos tendencias alcistas)
            momentum_score = max(0, result['momentum_24h']) / 10  # Normalizar
            score += momentum_score * 0.2
            
            # Volumen (más volumen = más liquidez)
            volume_score = min(result['quote_volume_24h'] / 1000000000, 10)  # Normalizar por billones
            score += volume_score * 0.15
            
            # Tendencia (preferimos tendencias fuertes)
            trend_score = abs(result['trend_strength']) * 2
            score += min(trend_score, 5) * 0.1
            
            result['trading_score'] = round(score, 2)
        
        # Ordenar por score descendente
        results.sort(key=lambda x: x['trading_score'], reverse=True)
        
        return results
    
    def generate_report(self, ranked_results: List[Dict]) -> str:
        """Genera reporte detallado"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        report = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    📊 ANÁLISIS DE PARES ACTUALES - BINANCE                   ║
║                         Datos en Tiempo Real                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

📅 Fecha de Análisis: {timestamp}
🎯 Objetivo: Identificar mejores pares para trading con datos actuales

╔══════════════════════════════════════════════════════════════════════════════╗
║                           🏆 TOP 5 PARES RECOMENDADOS                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""
        
        for i, result in enumerate(ranked_results[:5], 1):
            report += f"""
🥇 #{i} - {result['symbol']}
   💰 Precio Actual: ${result['current_price']:,.4f}
   📈 Cambio 24h: {result['price_change_24h']:+.2f}%
   🎯 Score Trading: {result['trading_score']}/10
   📊 Volatilidad: {result['volatility']:.4f}
   📏 Rango Promedio: {result['avg_range_pct']:.2f}%
   🚀 Momentum 6h: {result['momentum_6h']:+.2f}%
   💹 Volumen 24h: ${result['quote_volume_24h']:,.0f}
   ----------------------------------------
"""
        
        report += f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                           📋 ANÁLISIS COMPLETO                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

"""
        
        for result in ranked_results:
            report += f"""
{result['symbol']:>10} | Score: {result['trading_score']:>5.2f} | Precio: ${result['current_price']:>10.4f} | 24h: {result['price_change_24h']:>+6.2f}% | Vol: {result['volatility']:>6.4f}
"""
        
        report += f"""

╔══════════════════════════════════════════════════════════════════════════════╗
║                           💡 RECOMENDACIONES                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

🎯 PARES ÓPTIMOS PARA OBJETIVO 20-30% MENSUAL:
   • Top 3 pares con mayor score de trading
   • Volatilidad controlada pero suficiente para oportunidades
   • Volumen alto para buena liquidez
   • Momentum positivo actual

⚠️  CONSIDERACIONES:
   • Datos basados en comportamiento actual de mercado
   • Volatilidad puede cambiar rápidamente
   • Siempre usar gestión de riesgo adecuada
   • Monitorear condiciones de mercado continuamente

📊 PRÓXIMOS PASOS:
   1. Implementar estrategias en los top 3 pares
   2. Configurar alertas de volatilidad
   3. Establecer límites de riesgo por par
   4. Monitorear rendimiento en tiempo real
"""
        
        return report
    
    def save_results(self, results: List[Dict], report: str):
        """Guarda resultados en archivos"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Guardar datos JSON
        json_file = f"analisis_pares_actuales_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Guardar reporte
        report_file = f"reporte_pares_actuales_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n✅ Resultados guardados:")
        print(f"   📊 Datos: {json_file}")
        print(f"   📋 Reporte: {report_file}")

def main():
    """Función principal"""
    print("🚀 INICIANDO ANÁLISIS DE PARES CON DATOS ACTUALES")
    print("=" * 60)
    
    analyzer = BinanceCurrentAnalyzer()
    
    # Analizar todos los pares
    results = analyzer.analyze_all_pairs()
    
    if not results:
        print("❌ No se pudieron obtener datos")
        return
    
    # Rankear pares
    ranked_results = analyzer.rank_pairs_for_trading(results)
    
    # Generar reporte
    report = analyzer.generate_report(ranked_results)
    
    # Mostrar reporte
    print(report)
    
    # Guardar resultados
    analyzer.save_results(ranked_results, report)
    
    print("\n🏁 ANÁLISIS COMPLETADO")

if __name__ == "__main__":
    main()