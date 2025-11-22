#!/usr/bin/env python3
"""
Análisis Comparativo de Breakouts - 21 de Octubre 2025 - 12:35 UTC
Sistema SICAR - Análisis Técnico Avanzado con Comparación Temporal
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import re
from typing import Dict, List, Tuple, Any
import os

class ComparativeBreakoutAnalyzer:
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        self.analysis_timestamp = datetime.now(timezone.utc)
        self.market_data = {}
        self.previous_analysis = None
        
    def load_market_data(self) -> Dict[str, Any]:
        """Cargar datos de mercado más recientes del log"""
        try:
            log_file = "market_conditions.log"
            if not os.path.exists(log_file):
                print(f"Archivo {log_file} no encontrado")
                return {}
                
            # Leer las últimas 200 líneas para obtener datos completos
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-200:] if len(lines) > 200 else lines
            
            market_data = {}
            
            for line in recent_lines:
                if 'Condiciones de mercado' in line:
                    try:
                        # Extraer símbolo y datos JSON
                        parts = line.split('Data: ')
                        if len(parts) > 1:
                            json_str = parts[1].strip()
                            data = json.loads(json_str)
                            symbol = data.get('symbol')
                            
                            if symbol in self.symbols:
                                if symbol not in market_data:
                                    market_data[symbol] = []
                                market_data[symbol].append(data)
                    except (json.JSONDecodeError, KeyError) as e:
                        continue
            
            # Mantener solo los últimos 20 registros por símbolo
            for symbol in market_data:
                market_data[symbol] = market_data[symbol][-20:]
            
            self.market_data = market_data
            return market_data
            
        except Exception as e:
            print(f"Error cargando datos de mercado: {e}")
            return {}
    
    def load_previous_analysis(self) -> Dict[str, Any]:
        """Cargar análisis anterior para comparación"""
        try:
            # Buscar el archivo de análisis más reciente
            analysis_files = [f for f in os.listdir('.') if f.startswith('comparative_analysis_') and f.endswith('.json')]
            if analysis_files:
                latest_file = sorted(analysis_files)[-1]
                with open(latest_file, 'r', encoding='utf-8') as f:
                    self.previous_analysis = json.load(f)
                print(f"Análisis anterior cargado: {latest_file}")
                return self.previous_analysis
        except Exception as e:
            print(f"Error cargando análisis anterior: {e}")
        return {}
    
    def calculate_technical_indicators(self, symbol_data: List[Dict]) -> Dict[str, float]:
        """Calcular indicadores técnicos avanzados"""
        if not symbol_data or len(symbol_data) < 5:
            return {}
        
        prices = [float(d['price']) for d in symbol_data]
        volumes = [float(d['volume']) for d in symbol_data]
        volatilities = [float(d['volatility']) for d in symbol_data]
        
        # Precio actual y cambios
        current_price = prices[-1]
        price_change_5min = ((current_price - prices[-5]) / prices[-5]) * 100 if len(prices) >= 5 else 0
        price_change_10min = ((current_price - prices[-10]) / prices[-10]) * 100 if len(prices) >= 10 else 0
        
        # Medias móviles
        sma_5 = np.mean(prices[-5:]) if len(prices) >= 5 else current_price
        sma_10 = np.mean(prices[-10:]) if len(prices) >= 10 else current_price
        
        # Tendencia
        trend_strength = (current_price - sma_10) / sma_10 * 100 if sma_10 > 0 else 0
        
        # Volumen
        avg_volume = np.mean(volumes)
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volatilidad
        avg_volatility = np.mean(volatilities)
        current_volatility = volatilities[-1]
        volatility_ratio = current_volatility / avg_volatility if avg_volatility > 0 else 1
        
        # RSI simplificado
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        return {
            'current_price': current_price,
            'price_change_5min': price_change_5min,
            'price_change_10min': price_change_10min,
            'sma_5': sma_5,
            'sma_10': sma_10,
            'trend_strength': trend_strength,
            'volume_ratio': volume_ratio,
            'volatility_ratio': volatility_ratio,
            'rsi': rsi,
            'current_volume': current_volume,
            'avg_volume': avg_volume
        }
    
    def detect_breakout_potential(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Detectar potencial de breakout basado en indicadores"""
        if not indicators:
            return {'potential': 0, 'direction': 'neutral', 'confidence': 0, 'signals': []}
        
        signals = []
        score = 0
        direction = 'neutral'
        
        # Análisis de precio y tendencia
        if indicators['trend_strength'] > 2:
            signals.append("Tendencia alcista fuerte")
            score += 25
            direction = 'bullish'
        elif indicators['trend_strength'] < -2:
            signals.append("Tendencia bajista fuerte")
            score += 25
            direction = 'bearish'
        elif abs(indicators['trend_strength']) > 1:
            signals.append("Tendencia moderada")
            score += 15
        
        # Análisis de volumen
        if indicators['volume_ratio'] > 2:
            signals.append("Volumen excepcional")
            score += 30
        elif indicators['volume_ratio'] > 1.5:
            signals.append("Volumen elevado")
            score += 20
        elif indicators['volume_ratio'] > 1.2:
            signals.append("Volumen por encima del promedio")
            score += 10
        
        # Análisis de volatilidad
        if indicators['volatility_ratio'] > 1.5:
            signals.append("Volatilidad elevada")
            score += 15
        elif indicators['volatility_ratio'] > 1.2:
            signals.append("Volatilidad moderada")
            score += 10
        
        # Análisis RSI
        if indicators['rsi'] > 70:
            signals.append("RSI sobrecomprado")
            score += 10
            if direction == 'neutral':
                direction = 'bearish'
        elif indicators['rsi'] < 30:
            signals.append("RSI sobrevendido")
            score += 10
            if direction == 'neutral':
                direction = 'bullish'
        
        # Análisis de cambios de precio
        if abs(indicators['price_change_5min']) > 1:
            signals.append(f"Movimiento significativo 5min: {indicators['price_change_5min']:.2f}%")
            score += 15
        
        # Determinar confianza
        confidence = min(score, 100)
        
        # Ajustar dirección basada en cambios recientes
        if indicators['price_change_5min'] > 0.5 and direction != 'bearish':
            direction = 'bullish'
        elif indicators['price_change_5min'] < -0.5 and direction != 'bullish':
            direction = 'bearish'
        
        return {
            'potential': confidence,
            'direction': direction,
            'confidence': confidence,
            'signals': signals,
            'entry_price': indicators['current_price'],
            'volume_support': indicators['volume_ratio'] > 1.2
        }
    
    def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Análisis completo de un símbolo"""
        if symbol not in self.market_data or not self.market_data[symbol]:
            return {'error': f'No hay datos para {symbol}'}
        
        symbol_data = self.market_data[symbol]
        indicators = self.calculate_technical_indicators(symbol_data)
        breakout_analysis = self.detect_breakout_potential(indicators)
        
        # Determinar estado de tendencia
        trend_state = "neutral"
        if indicators.get('trend_strength', 0) > 1:
            trend_state = "bullish"
        elif indicators.get('trend_strength', 0) < -1:
            trend_state = "bearish"
        
        # Análisis de soporte y resistencia
        prices = [float(d['price']) for d in symbol_data]
        support_level = min(prices[-10:]) if len(prices) >= 10 else min(prices)
        resistance_level = max(prices[-10:]) if len(prices) >= 10 else max(prices)
        
        return {
            'symbol': symbol,
            'timestamp': self.analysis_timestamp.isoformat(),
            'current_price': indicators.get('current_price', 0),
            'trend_state': trend_state,
            'trend_strength': indicators.get('trend_strength', 0),
            'breakout_potential': breakout_analysis['potential'],
            'breakout_direction': breakout_analysis['direction'],
            'confidence': breakout_analysis['confidence'],
            'volume_ratio': indicators.get('volume_ratio', 1),
            'volatility_ratio': indicators.get('volatility_ratio', 1),
            'rsi': indicators.get('rsi', 50),
            'support_level': support_level,
            'resistance_level': resistance_level,
            'technical_signals': breakout_analysis['signals'],
            'volume_support': breakout_analysis['volume_support'],
            'entry_price': breakout_analysis['entry_price'],
            'price_change_5min': indicators.get('price_change_5min', 0),
            'price_change_10min': indicators.get('price_change_10min', 0)
        }
    
    def compare_with_previous(self, current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Comparar análisis actual con el anterior"""
        if not self.previous_analysis:
            return {'status': 'No hay análisis anterior para comparar'}
        
        comparison = {
            'time_difference': 'N/A',
            'market_evolution': {},
            'symbol_changes': {},
            'key_developments': []
        }
        
        try:
            # Calcular diferencia de tiempo
            prev_time = datetime.fromisoformat(self.previous_analysis.get('timestamp', ''))
            current_time = datetime.fromisoformat(current_analysis['timestamp'])
            time_diff = current_time - prev_time
            comparison['time_difference'] = f"{time_diff.total_seconds() / 60:.1f} minutos"
            
            # Comparar condición general del mercado
            prev_condition = self.previous_analysis.get('executive_summary', {}).get('market_condition', 'unknown')
            current_condition = current_analysis.get('executive_summary', {}).get('market_condition', 'unknown')
            
            comparison['market_evolution'] = {
                'previous': prev_condition,
                'current': current_condition,
                'change': 'evolved' if prev_condition != current_condition else 'stable'
            }
            
            # Comparar símbolos individuales
            prev_symbols = self.previous_analysis.get('symbol_analysis', {})
            current_symbols = current_analysis.get('symbol_analysis', {})
            
            for symbol in self.symbols:
                if symbol in prev_symbols and symbol in current_symbols:
                    prev_data = prev_symbols[symbol]
                    current_data = current_symbols[symbol]
                    
                    price_change = ((current_data.get('current_price', 0) - prev_data.get('current_price', 0)) / 
                                  prev_data.get('current_price', 1)) * 100
                    
                    breakout_change = current_data.get('breakout_potential', 0) - prev_data.get('breakout_potential', 0)
                    
                    comparison['symbol_changes'][symbol] = {
                        'price_change_pct': price_change,
                        'breakout_potential_change': breakout_change,
                        'trend_change': {
                            'from': prev_data.get('trend_state', 'unknown'),
                            'to': current_data.get('trend_state', 'unknown')
                        },
                        'volume_change': current_data.get('volume_ratio', 1) - prev_data.get('volume_ratio', 1)
                    }
                    
                    # Identificar desarrollos clave
                    if abs(price_change) > 1:
                        comparison['key_developments'].append(
                            f"{symbol}: Cambio de precio significativo {price_change:+.2f}%"
                        )
                    
                    if abs(breakout_change) > 20:
                        comparison['key_developments'].append(
                            f"{symbol}: Cambio en potencial de breakout {breakout_change:+.1f} puntos"
                        )
                    
                    if prev_data.get('trend_state') != current_data.get('trend_state'):
                        comparison['key_developments'].append(
                            f"{symbol}: Cambio de tendencia de {prev_data.get('trend_state')} a {current_data.get('trend_state')}"
                        )
            
        except Exception as e:
            comparison['error'] = f"Error en comparación: {e}"
        
        return comparison
    
    def generate_trading_recommendations(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generar recomendaciones de trading basadas en el análisis"""
        recommendations = []
        
        symbol_analysis = analysis.get('symbol_analysis', {})
        
        for symbol, data in symbol_analysis.items():
            if data.get('breakout_potential', 0) > 70:
                recommendations.append({
                    'type': 'immediate_opportunity',
                    'symbol': symbol,
                    'action': f"Preparar para breakout {data.get('breakout_direction', 'neutral')}",
                    'confidence': data.get('confidence', 0),
                    'entry_price': data.get('entry_price', 0),
                    'reasoning': f"Potencial de breakout {data.get('breakout_potential', 0)}% con {data.get('confidence', 0)}% confianza"
                })
            elif data.get('breakout_potential', 0) > 50:
                recommendations.append({
                    'type': 'watch_list',
                    'symbol': symbol,
                    'action': "Monitorear de cerca",
                    'confidence': data.get('confidence', 0),
                    'reasoning': f"Potencial medio de breakout {data.get('breakout_potential', 0)}%"
                })
        
        # Recomendación de gestión de riesgo
        high_volatility_symbols = [
            symbol for symbol, data in symbol_analysis.items() 
            if data.get('volatility_ratio', 1) > 1.5
        ]
        
        if high_volatility_symbols:
            recommendations.append({
                'type': 'risk_management',
                'symbols': high_volatility_symbols,
                'action': "Ajustar tamaño de posición por alta volatilidad",
                'reasoning': "Volatilidad elevada detectada"
            })
        
        return recommendations
    
    def run_analysis(self) -> Dict[str, Any]:
        """Ejecutar análisis completo"""
        print("🔄 Iniciando análisis comparativo de breakouts...")
        
        # Cargar datos
        market_data = self.load_market_data()
        if not market_data:
            return {'error': 'No se pudieron cargar datos de mercado'}
        
        previous_analysis = self.load_previous_analysis()
        
        # Análizar cada símbolo
        symbol_analysis = {}
        for symbol in self.symbols:
            print(f"📊 Analizando {symbol}...")
            symbol_analysis[symbol] = self.analyze_symbol(symbol)
        
        # Generar resumen ejecutivo
        total_symbols = len([s for s in symbol_analysis.values() if 'error' not in s])
        high_potential_breakouts = len([
            s for s in symbol_analysis.values() 
            if s.get('breakout_potential', 0) > 70
        ])
        
        bullish_trends = len([
            s for s in symbol_analysis.values() 
            if s.get('trend_state') == 'bullish'
        ])
        
        bearish_trends = len([
            s for s in symbol_analysis.values() 
            if s.get('trend_state') == 'bearish'
        ])
        
        # Determinar condición general del mercado
        if bullish_trends > bearish_trends:
            if high_potential_breakouts > 0:
                market_condition = "bullish_momentum_building"
            else:
                market_condition = "bullish_consolidation"
        elif bearish_trends > bullish_trends:
            if high_potential_breakouts > 0:
                market_condition = "bearish_pressure_building"
            else:
                market_condition = "bearish_consolidation"
        else:
            market_condition = "mixed_signals"
        
        # Determinar nivel de riesgo
        avg_volatility = np.mean([
            s.get('volatility_ratio', 1) for s in symbol_analysis.values() 
            if 'error' not in s
        ])
        
        if avg_volatility > 1.5:
            risk_level = "high"
        elif avg_volatility > 1.2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Compilar análisis completo
        complete_analysis = {
            'timestamp': self.analysis_timestamp.isoformat(),
            'analysis_type': 'comparative_breakout_analysis',
            'data_timeframe': '21_octubre_2025_12:35_UTC',
            'symbol_analysis': symbol_analysis,
            'executive_summary': {
                'market_condition': market_condition,
                'total_symbols_analyzed': total_symbols,
                'high_potential_breakouts': high_potential_breakouts,
                'dominant_trend': 'bullish' if bullish_trends > bearish_trends else 'bearish' if bearish_trends > bullish_trends else 'mixed',
                'risk_level': risk_level,
                'key_developments': []
            }
        }
        
        # Agregar desarrollos clave
        for symbol, data in symbol_analysis.items():
            if 'error' not in data:
                if data.get('breakout_potential', 0) > 80:
                    complete_analysis['executive_summary']['key_developments'].append(
                        f"Breakout inminente en {symbol} ({data.get('confidence', 0)}% confianza)"
                    )
                elif data.get('volume_ratio', 1) > 2:
                    complete_analysis['executive_summary']['key_developments'].append(
                        f"Volumen excepcional detectado en {symbol}"
                    )
        
        # Comparar con análisis anterior
        comparison = self.compare_with_previous(complete_analysis)
        complete_analysis['comparative_analysis'] = comparison
        
        # Generar recomendaciones
        recommendations = self.generate_trading_recommendations(complete_analysis)
        complete_analysis['trading_recommendations'] = recommendations
        
        return complete_analysis

def main():
    """Función principal"""
    analyzer = ComparativeBreakoutAnalyzer()
    
    try:
        # Ejecutar análisis
        results = analyzer.run_analysis()
        
        if 'error' in results:
            print(f"❌ Error en análisis: {results['error']}")
            return
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"comparative_analysis_{timestamp}.json"
        
        # Convertir tipos numpy a tipos nativos de Python para JSON
        def convert_numpy_types(obj):
            if isinstance(obj, np.bool_):
                return bool(obj)
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {key: convert_numpy_types(value) for key, value in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            return obj
        
        results_serializable = convert_numpy_types(results)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_serializable, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Análisis completado y guardado en: {filename}")
        
        # Mostrar resumen
        summary = results.get('executive_summary', {})
        print(f"\n📈 RESUMEN EJECUTIVO:")
        print(f"   Condición del mercado: {summary.get('market_condition', 'N/A')}")
        print(f"   Breakouts de alto potencial: {summary.get('high_potential_breakouts', 0)}")
        print(f"   Tendencia dominante: {summary.get('dominant_trend', 'N/A')}")
        print(f"   Nivel de riesgo: {summary.get('risk_level', 'N/A')}")
        
        # Mostrar desarrollos clave
        key_developments = summary.get('key_developments', [])
        if key_developments:
            print(f"\n🔥 DESARROLLOS CLAVE:")
            for dev in key_developments:
                print(f"   • {dev}")
        
        # Mostrar recomendaciones inmediatas
        recommendations = results.get('trading_recommendations', [])
        immediate_ops = [r for r in recommendations if r.get('type') == 'immediate_opportunity']
        if immediate_ops:
            print(f"\n⚡ OPORTUNIDADES INMEDIATAS:")
            for op in immediate_ops:
                print(f"   • {op.get('symbol')}: {op.get('action')} ({op.get('confidence')}% confianza)")
        
        return results
        
    except Exception as e:
        print(f"❌ Error ejecutando análisis: {e}")
        return None

if __name__ == "__main__":
    main()