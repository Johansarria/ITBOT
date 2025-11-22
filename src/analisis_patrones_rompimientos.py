#!/usr/bin/env python3
"""
SICAR - Análisis de Patrones de Rompimientos y Confianza
Analiza el comportamiento del mercado en cuanto a breakouts y niveles de confianza
"""

import json
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import requests
import time
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class BreakoutPatternAnalyzer:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.logs_path = self.base_path / "logs"
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        self.timeframes = ['1h', '4h', '1d']
        
    def get_binance_data(self, symbol: str, interval: str = '1h', limit: int = 100) -> pd.DataFrame:
        """Obtiene datos de Binance"""
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convertir a tipos numéricos
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df[numeric_columns]
            
        except Exception as e:
            print(f"❌ Error obteniendo datos para {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict:
        """Calcula niveles de soporte y resistencia"""
        if df.empty:
            return {}
        
        # Calcular pivotes
        highs = df['high'].rolling(window=window, center=True).max()
        lows = df['low'].rolling(window=window, center=True).min()
        
        # Identificar niveles de resistencia (máximos locales)
        resistance_levels = []
        for i in range(window, len(df) - window):
            if df['high'].iloc[i] == highs.iloc[i]:
                resistance_levels.append(df['high'].iloc[i])
        
        # Identificar niveles de soporte (mínimos locales)
        support_levels = []
        for i in range(window, len(df) - window):
            if df['low'].iloc[i] == lows.iloc[i]:
                support_levels.append(df['low'].iloc[i])
        
        return {
            'resistance_levels': sorted(set(resistance_levels), reverse=True)[:5],
            'support_levels': sorted(set(support_levels))[:5],
            'current_price': df['close'].iloc[-1]
        }
    
    def detect_breakout_patterns(self, df: pd.DataFrame) -> Dict:
        """Detecta patrones de rompimiento"""
        if df.empty or len(df) < 50:
            return {}
        
        current_price = df['close'].iloc[-1]
        
        # Calcular medias móviles
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        # Calcular RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Calcular Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Detectar patrones
        patterns = {}
        
        # 1. Breakout de Bollinger Bands
        if current_price > df['bb_upper'].iloc[-1]:
            patterns['bollinger_breakout'] = {
                'type': 'ALCISTA',
                'confidence': min(95, 70 + ((current_price - df['bb_upper'].iloc[-1]) / df['bb_upper'].iloc[-1] * 100))
            }
        elif current_price < df['bb_lower'].iloc[-1]:
            patterns['bollinger_breakout'] = {
                'type': 'BAJISTA',
                'confidence': min(95, 70 + ((df['bb_lower'].iloc[-1] - current_price) / df['bb_lower'].iloc[-1] * 100))
            }
        
        # 2. Cruce de medias móviles
        if df['sma_20'].iloc[-1] > df['sma_50'].iloc[-1] and df['sma_20'].iloc[-2] <= df['sma_50'].iloc[-2]:
            patterns['ma_crossover'] = {
                'type': 'GOLDEN_CROSS',
                'confidence': 75
            }
        elif df['sma_20'].iloc[-1] < df['sma_50'].iloc[-1] and df['sma_20'].iloc[-2] >= df['sma_50'].iloc[-2]:
            patterns['ma_crossover'] = {
                'type': 'DEATH_CROSS',
                'confidence': 75
            }
        
        # 3. Divergencia RSI
        price_trend = (df['close'].iloc[-5:].iloc[-1] - df['close'].iloc[-5:].iloc[0]) / df['close'].iloc[-5:].iloc[0]
        rsi_trend = (df['rsi'].iloc[-5:].iloc[-1] - df['rsi'].iloc[-5:].iloc[0]) / df['rsi'].iloc[-5:].iloc[0]
        
        if price_trend > 0.02 and rsi_trend < -0.05:
            patterns['rsi_divergence'] = {
                'type': 'BEARISH_DIVERGENCE',
                'confidence': 65
            }
        elif price_trend < -0.02 and rsi_trend > 0.05:
            patterns['rsi_divergence'] = {
                'type': 'BULLISH_DIVERGENCE',
                'confidence': 65
            }
        
        # 4. Volumen de confirmación
        avg_volume = df['volume'].rolling(20).mean().iloc[-1]
        current_volume = df['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if volume_ratio > 1.5:
            patterns['volume_confirmation'] = {
                'type': 'HIGH_VOLUME',
                'confidence': min(90, 60 + (volume_ratio - 1) * 20),
                'ratio': volume_ratio
            }
        
        return patterns
    
    def calculate_market_confidence(self, patterns: Dict, support_resistance: Dict) -> Dict:
        """Calcula el nivel de confianza del mercado"""
        confidence_score = 50  # Base neutral
        confidence_factors = []
        
        current_price = support_resistance.get('current_price', 0)
        
        # Factor 1: Proximidad a niveles clave
        if support_resistance:
            resistance_levels = support_resistance.get('resistance_levels', [])
            support_levels = support_resistance.get('support_levels', [])
            
            # Distancia a resistencia más cercana
            if resistance_levels:
                closest_resistance = min(resistance_levels, key=lambda x: abs(x - current_price))
                resistance_distance = abs(closest_resistance - current_price) / current_price * 100
                
                if resistance_distance < 2:  # Muy cerca de resistencia
                    confidence_score -= 15
                    confidence_factors.append("🔴 Muy cerca de resistencia")
                elif resistance_distance < 5:
                    confidence_score -= 8
                    confidence_factors.append("🟡 Cerca de resistencia")
            
            # Distancia a soporte más cercano
            if support_levels:
                closest_support = min(support_levels, key=lambda x: abs(x - current_price))
                support_distance = abs(closest_support - current_price) / current_price * 100
                
                if support_distance < 2:  # Muy cerca de soporte
                    confidence_score += 10
                    confidence_factors.append("🟢 Cerca de soporte fuerte")
        
        # Factor 2: Patrones detectados
        pattern_confidence = 0
        for pattern_name, pattern_data in patterns.items():
            pattern_conf = pattern_data.get('confidence', 0)
            pattern_type = pattern_data.get('type', '')
            
            if 'BULLISH' in pattern_type or 'GOLDEN' in pattern_type or 'ALCISTA' in pattern_type:
                pattern_confidence += pattern_conf * 0.3
                confidence_factors.append(f"🟢 Patrón alcista: {pattern_name}")
            elif 'BEARISH' in pattern_type or 'DEATH' in pattern_type or 'BAJISTA' in pattern_type:
                pattern_confidence -= pattern_conf * 0.3
                confidence_factors.append(f"🔴 Patrón bajista: {pattern_name}")
            else:
                pattern_confidence += pattern_conf * 0.1
                confidence_factors.append(f"🟡 Patrón neutral: {pattern_name}")
        
        confidence_score += pattern_confidence
        
        # Factor 3: Volumen
        if 'volume_confirmation' in patterns:
            vol_data = patterns['volume_confirmation']
            if vol_data['ratio'] > 2:
                confidence_score += 15
                confidence_factors.append("🟢 Volumen muy alto")
            elif vol_data['ratio'] > 1.5:
                confidence_score += 8
                confidence_factors.append("🟢 Volumen alto")
        
        # Normalizar score
        confidence_score = max(0, min(100, confidence_score))
        
        # Determinar nivel de confianza
        if confidence_score >= 80:
            confidence_level = "MUY ALTA"
            confidence_emoji = "🟢"
        elif confidence_score >= 65:
            confidence_level = "ALTA"
            confidence_emoji = "🟢"
        elif confidence_score >= 50:
            confidence_level = "MEDIA"
            confidence_emoji = "🟡"
        elif confidence_score >= 35:
            confidence_level = "BAJA"
            confidence_emoji = "🟡"
        else:
            confidence_level = "MUY BAJA"
            confidence_emoji = "🔴"
        
        return {
            'score': round(confidence_score, 1),
            'level': confidence_level,
            'emoji': confidence_emoji,
            'factors': confidence_factors
        }
    
    def analyze_symbol(self, symbol: str, timeframe: str = '1h') -> Dict:
        """Analiza un símbolo específico"""
        print(f"📊 Analizando {symbol} ({timeframe})...")
        
        # Obtener datos
        df = self.get_binance_data(symbol, timeframe)
        if df.empty:
            return {'error': 'No se pudieron obtener datos'}
        
        # Calcular soporte y resistencia
        support_resistance = self.calculate_support_resistance(df)
        
        # Detectar patrones
        patterns = self.detect_breakout_patterns(df)
        
        # Calcular confianza
        confidence = self.calculate_market_confidence(patterns, support_resistance)
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'current_price': support_resistance.get('current_price', 0),
            'support_resistance': support_resistance,
            'patterns': patterns,
            'confidence': confidence,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def display_analysis(self):
        """Muestra el análisis completo"""
        print("🔍 SICAR - ANÁLISIS DE PATRONES DE ROMPIMIENTOS Y CONFIANZA")
        print("=" * 80)
        print(f"⏰ Análisis generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        all_analyses = []
        
        for symbol in self.symbols:
            analysis = self.analyze_symbol(symbol, '1h')
            if 'error' not in analysis:
                all_analyses.append(analysis)
                
                print(f"📈 {symbol}")
                print("-" * 40)
                print(f"💰 Precio actual: ${analysis['current_price']:.4f}")
                
                # Mostrar niveles de soporte y resistencia
                sr = analysis['support_resistance']
                if sr.get('resistance_levels'):
                    print(f"🔴 Resistencias: {', '.join([f'${r:.4f}' for r in sr['resistance_levels'][:3]])}")
                if sr.get('support_levels'):
                    print(f"🟢 Soportes: {', '.join([f'${s:.4f}' for s in sr['support_levels'][:3]])}")
                
                # Mostrar patrones detectados
                patterns = analysis['patterns']
                if patterns:
                    print(f"🎯 Patrones detectados:")
                    for pattern_name, pattern_data in patterns.items():
                        pattern_type = pattern_data.get('type', 'N/A')
                        pattern_conf = pattern_data.get('confidence', 0)
                        print(f"   • {pattern_name}: {pattern_type} (Confianza: {pattern_conf:.1f}%)")
                else:
                    print("🎯 Patrones detectados: Ninguno")
                
                # Mostrar confianza del mercado
                confidence = analysis['confidence']
                print(f"📊 Confianza del mercado: {confidence['emoji']} {confidence['level']} ({confidence['score']}%)")
                
                if confidence['factors']:
                    print("📋 Factores de confianza:")
                    for factor in confidence['factors'][:3]:
                        print(f"   • {factor}")
                
                print()
        
        # Resumen general
        if all_analyses:
            print("🎯 RESUMEN GENERAL DEL MERCADO")
            print("=" * 50)
            
            avg_confidence = np.mean([a['confidence']['score'] for a in all_analyses])
            total_patterns = sum([len(a['patterns']) for a in all_analyses])
            
            # Confianza general del mercado
            if avg_confidence >= 70:
                market_sentiment = "🟢 OPTIMISTA"
            elif avg_confidence >= 50:
                market_sentiment = "🟡 NEUTRAL"
            else:
                market_sentiment = "🔴 PESIMISTA"
            
            print(f"📊 Sentimiento general: {market_sentiment}")
            print(f"📈 Confianza promedio: {avg_confidence:.1f}%")
            print(f"🎯 Total de patrones detectados: {total_patterns}")
            
            # Top 3 símbolos por confianza
            sorted_analyses = sorted(all_analyses, key=lambda x: x['confidence']['score'], reverse=True)
            print(f"\n🏆 TOP 3 SÍMBOLOS POR CONFIANZA:")
            for i, analysis in enumerate(sorted_analyses[:3], 1):
                conf = analysis['confidence']
                print(f"   {i}. {analysis['symbol']}: {conf['emoji']} {conf['score']}% ({conf['level']})")
            
            # Alertas importantes
            print(f"\n⚠️  ALERTAS IMPORTANTES:")
            alerts = []
            for analysis in all_analyses:
                symbol = analysis['symbol']
                patterns = analysis['patterns']
                confidence = analysis['confidence']
                
                # Alerta por alta confianza
                if confidence['score'] >= 80:
                    alerts.append(f"🟢 {symbol}: Confianza muy alta ({confidence['score']}%)")
                
                # Alerta por patrones de rompimiento
                for pattern_name, pattern_data in patterns.items():
                    if pattern_data.get('confidence', 0) >= 80:
                        alerts.append(f"🎯 {symbol}: Patrón fuerte detectado - {pattern_name}")
                
                # Alerta por volumen alto
                if 'volume_confirmation' in patterns:
                    vol_ratio = patterns['volume_confirmation'].get('ratio', 1)
                    if vol_ratio > 2:
                        alerts.append(f"📊 {symbol}: Volumen excepcional ({vol_ratio:.1f}x promedio)")
            
            if alerts:
                for alert in alerts[:5]:  # Mostrar máximo 5 alertas
                    print(f"   • {alert}")
            else:
                print("   • No hay alertas críticas en este momento")
        
        print("\n" + "=" * 80)
        print("✅ Análisis completado")

def main():
    analyzer = BreakoutPatternAnalyzer()
    analyzer.display_analysis()

if __name__ == "__main__":
    main()