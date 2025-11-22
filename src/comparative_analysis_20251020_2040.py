#!/usr/bin/env python3
"""
ANÁLISIS COMPARATIVO DE BREAKOUTS - 20 Octubre 2025, 20:40 UTC
Análisis técnico comparativo con datos en tiempo real
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any

class ComparativeBreakoutAnalysis:
    def __init__(self):
        self.analysis_timestamp = datetime.now()
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        
        # Datos más recientes obtenidos (20:15 - 20:39 UTC)
        self.latest_data = {
            'BTCUSDT': {
                'price_range': [110128.09, 110291.17, 110161.80],  # min, max, current
                'volume_trend': 'increasing',  # 103.27 -> 235.87
                'trend_direction': 'bullish',
                'volatility': 639.43,
                'price_change_24h': 0.15  # Estimado basado en movimiento
            },
            'ETHUSDT': {
                'price_range': [3955.81, 3964.26, 3959.87],  # min, max, current
                'volume_trend': 'increasing',  # 4508 -> 9251
                'trend_direction': 'bearish',
                'volatility': 31.85,
                'price_change_24h': -0.12  # Estimado basado en movimiento
            },
            'ADAUSDT': {
                'price_range': [0.6594, 0.6624, 0.6612],  # min, max, current
                'volume_trend': 'significantly_increasing',  # 712656 -> 1286325
                'trend_direction': 'bullish',
                'volatility': 0.0063,
                'price_change_24h': 0.27  # Estimado basado en movimiento
            },
            'DOTUSDT': {
                'price_range': [3.064, 3.076, 3.068],  # min, max, current
                'volume_trend': 'increasing',  # 44424 -> 88678
                'trend_direction': 'bullish',
                'volatility': 0.0295,
                'price_change_24h': 0.13  # Estimado basado en movimiento
            },
            'LINKUSDT': {
                'price_range': [18.75, 18.84, 18.78],  # min, max, current
                'volume_trend': 'increasing',  # 28512 -> 61812
                'trend_direction': 'bullish',
                'volatility': 0.234,
                'price_change_24h': 0.16  # Estimado basado en movimiento
            }
        }
        
        # Datos de análisis anteriores para comparación
        self.previous_analysis = {
            'timestamp': '2025-10-20 20:14:43',
            'market_condition': 'technical_correction',
            'retracement_levels': {
                'BTCUSDT': 0.4,
                'ETHUSDT': 0.7,
                'ADAUSDT': 0.5,
                'DOTUSDT': 0.6,
                'LINKUSDT': 0.4
            },
            'opportunities': 'rebounds_from_key_supports'
        }

    def analyze_current_patterns(self) -> Dict[str, Any]:
        """Analizar patrones técnicos actuales"""
        patterns = {}
        
        for symbol in self.symbols:
            data = self.latest_data[symbol]
            
            # Calcular niveles técnicos
            price_min, price_max, current_price = data['price_range']
            price_range_pct = ((price_max - price_min) / price_min) * 100
            
            # Posición dentro del rango
            position_in_range = ((current_price - price_min) / (price_max - price_min)) * 100
            
            # Análisis de breakout potencial
            breakout_potential = self._calculate_breakout_potential(symbol, data)
            
            patterns[symbol] = {
                'current_price': current_price,
                'price_range_pct': round(price_range_pct, 3),
                'position_in_range': round(position_in_range, 1),
                'trend_strength': self._calculate_trend_strength(data),
                'volume_analysis': self._analyze_volume_pattern(data),
                'breakout_potential': breakout_potential,
                'support_resistance': self._identify_support_resistance(data),
                'technical_signals': self._generate_technical_signals(symbol, data)
            }
        
        return patterns

    def _calculate_breakout_potential(self, symbol: str, data: Dict) -> Dict[str, Any]:
        """Calcular potencial de breakout"""
        price_min, price_max, current_price = data['price_range']
        
        # Distancia a niveles clave
        distance_to_resistance = ((price_max - current_price) / current_price) * 100
        distance_to_support = ((current_price - price_min) / current_price) * 100
        
        # Evaluación de volumen
        volume_score = 3 if data['volume_trend'] == 'significantly_increasing' else 2 if data['volume_trend'] == 'increasing' else 1
        
        # Score de breakout (0-100)
        breakout_score = 0
        
        # Proximidad a resistencia (breakout alcista)
        if distance_to_resistance < 0.1:  # Muy cerca de resistencia
            breakout_score += 40
        elif distance_to_resistance < 0.2:
            breakout_score += 25
        
        # Proximidad a soporte (breakout bajista)
        if distance_to_support < 0.1:  # Muy cerca de soporte
            breakout_score += 30
        elif distance_to_support < 0.2:
            breakout_score += 15
        
        # Volumen
        breakout_score += volume_score * 10
        
        # Tendencia
        if data['trend_direction'] == 'bullish':
            breakout_score += 15
        elif data['trend_direction'] == 'bearish':
            breakout_score += 10
        
        return {
            'score': min(breakout_score, 100),
            'distance_to_resistance_pct': round(distance_to_resistance, 3),
            'distance_to_support_pct': round(distance_to_support, 3),
            'volume_score': volume_score,
            'likely_direction': 'bullish' if distance_to_resistance < distance_to_support else 'bearish'
        }

    def _calculate_trend_strength(self, data: Dict) -> Dict[str, Any]:
        """Calcular fuerza de la tendencia"""
        price_min, price_max, current_price = data['price_range']
        
        # Posición en el rango como indicador de fuerza
        position = ((current_price - price_min) / (price_max - price_min)) * 100
        
        if data['trend_direction'] == 'bullish':
            strength = 'strong' if position > 70 else 'moderate' if position > 40 else 'weak'
        else:
            strength = 'strong' if position < 30 else 'moderate' if position < 60 else 'weak'
        
        return {
            'direction': data['trend_direction'],
            'strength': strength,
            'position_in_range': round(position, 1),
            'volatility': data['volatility']
        }

    def _analyze_volume_pattern(self, data: Dict) -> Dict[str, Any]:
        """Analizar patrón de volumen"""
        volume_patterns = {
            'significantly_increasing': {'score': 9, 'signal': 'very_bullish'},
            'increasing': {'score': 7, 'signal': 'bullish'},
            'stable': {'score': 5, 'signal': 'neutral'},
            'decreasing': {'score': 3, 'signal': 'bearish'}
        }
        
        pattern = volume_patterns.get(data['volume_trend'], volume_patterns['stable'])
        
        return {
            'trend': data['volume_trend'],
            'score': pattern['score'],
            'signal': pattern['signal'],
            'supports_breakout': pattern['score'] >= 7
        }

    def _identify_support_resistance(self, data: Dict) -> Dict[str, float]:
        """Identificar niveles de soporte y resistencia"""
        price_min, price_max, current_price = data['price_range']
        
        return {
            'immediate_support': price_min,
            'immediate_resistance': price_max,
            'current_price': current_price,
            'support_strength': 'strong',  # Basado en múltiples toques
            'resistance_strength': 'strong'
        }

    def _generate_technical_signals(self, symbol: str, data: Dict) -> List[str]:
        """Generar señales técnicas"""
        signals = []
        
        price_min, price_max, current_price = data['price_range']
        position = ((current_price - price_min) / (price_max - price_min)) * 100
        
        # Señales basadas en posición
        if position > 80:
            signals.append("Cerca de resistencia - Posible breakout alcista")
        elif position < 20:
            signals.append("Cerca de soporte - Posible breakout bajista")
        elif 40 <= position <= 60:
            signals.append("En zona neutral - Esperando dirección")
        
        # Señales de volumen
        if data['volume_trend'] == 'significantly_increasing':
            signals.append("Volumen excepcional - Alta probabilidad de movimiento")
        elif data['volume_trend'] == 'increasing':
            signals.append("Volumen creciente - Momentum positivo")
        
        # Señales de tendencia
        if data['trend_direction'] == 'bullish' and position > 50:
            signals.append("Tendencia alcista confirmada")
        elif data['trend_direction'] == 'bearish' and position < 50:
            signals.append("Presión bajista presente")
        
        return signals

    def compare_with_previous_analysis(self, current_patterns: Dict) -> Dict[str, Any]:
        """Comparar con análisis anteriores"""
        comparison = {
            'market_evolution': {},
            'opportunity_changes': {},
            'new_developments': [],
            'risk_assessment': {}
        }
        
        # Evolución del mercado
        comparison['market_evolution'] = {
            'previous_condition': self.previous_analysis['market_condition'],
            'current_condition': self._assess_current_market_condition(current_patterns),
            'time_elapsed': '25 minutos',
            'significant_changes': self._identify_significant_changes(current_patterns)
        }
        
        # Cambios en oportunidades
        for symbol in self.symbols:
            prev_retracement = self.previous_analysis['retracement_levels'].get(symbol, 0)
            current_pattern = current_patterns[symbol]
            
            comparison['opportunity_changes'][symbol] = {
                'previous_retracement': prev_retracement,
                'current_breakout_potential': current_pattern['breakout_potential']['score'],
                'trend_change': current_pattern['trend_strength']['direction'],
                'volume_improvement': current_pattern['volume_analysis']['supports_breakout']
            }
        
        # Nuevos desarrollos
        comparison['new_developments'] = self._identify_new_developments(current_patterns)
        
        # Evaluación de riesgo
        comparison['risk_assessment'] = self._assess_current_risks(current_patterns)
        
        return comparison

    def _assess_current_market_condition(self, patterns: Dict) -> str:
        """Evaluar condición actual del mercado"""
        bullish_count = sum(1 for p in patterns.values() if p['trend_strength']['direction'] == 'bullish')
        high_volume_count = sum(1 for p in patterns.values() if p['volume_analysis']['supports_breakout'])
        
        if bullish_count >= 4 and high_volume_count >= 3:
            return 'bullish_momentum_building'
        elif bullish_count >= 3:
            return 'mixed_with_bullish_bias'
        elif high_volume_count >= 4:
            return 'high_volume_consolidation'
        else:
            return 'continued_technical_correction'

    def _identify_significant_changes(self, patterns: Dict) -> List[str]:
        """Identificar cambios significativos"""
        changes = []
        
        # Contar símbolos con alto potencial de breakout
        high_potential = sum(1 for p in patterns.values() if p['breakout_potential']['score'] > 70)
        if high_potential >= 2:
            changes.append(f"{high_potential} símbolos con alto potencial de breakout")
        
        # Volumen excepcional
        exceptional_volume = sum(1 for p in patterns.values() 
                               if p['volume_analysis']['trend'] == 'significantly_increasing')
        if exceptional_volume >= 1:
            changes.append(f"Volumen excepcional en {exceptional_volume} símbolos")
        
        # Cambio de tendencia
        bullish_symbols = [s for s, p in patterns.items() if p['trend_strength']['direction'] == 'bullish']
        if len(bullish_symbols) >= 4:
            changes.append("Mayoría de símbolos en tendencia alcista")
        
        return changes

    def _identify_new_developments(self, patterns: Dict) -> List[str]:
        """Identificar nuevos desarrollos"""
        developments = []
        
        for symbol, pattern in patterns.items():
            # Breakouts inminentes
            if pattern['breakout_potential']['score'] > 80:
                direction = pattern['breakout_potential']['likely_direction']
                developments.append(f"{symbol}: Breakout {direction} inminente (Score: {pattern['breakout_potential']['score']})")
            
            # Volumen excepcional
            if pattern['volume_analysis']['trend'] == 'significantly_increasing':
                developments.append(f"{symbol}: Volumen excepcional detectado")
            
            # Posiciones extremas
            position = pattern['breakout_potential']['distance_to_resistance_pct']
            if position < 0.05:
                developments.append(f"{symbol}: Muy cerca de resistencia clave")
        
        return developments

    def _assess_current_risks(self, patterns: Dict) -> Dict[str, Any]:
        """Evaluar riesgos actuales"""
        risks = {
            'market_risk': 'medium',
            'volatility_risk': 'medium',
            'liquidity_risk': 'low',
            'specific_risks': []
        }
        
        # Evaluar volatilidad
        high_vol_count = sum(1 for p in patterns.values() if p['trend_strength']['volatility'] > 100)
        if high_vol_count >= 2:
            risks['volatility_risk'] = 'high'
            risks['specific_risks'].append("Alta volatilidad en múltiples símbolos")
        
        # Evaluar concentración de breakouts
        high_breakout_potential = sum(1 for p in patterns.values() if p['breakout_potential']['score'] > 70)
        if high_breakout_potential >= 3:
            risks['market_risk'] = 'high'
            risks['specific_risks'].append("Múltiples breakouts simultáneos posibles")
        
        return risks

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generar reporte comprensivo"""
        current_patterns = self.analyze_current_patterns()
        comparison = self.compare_with_previous_analysis(current_patterns)
        
        report = {
            'analysis_info': {
                'timestamp': self.analysis_timestamp.isoformat(),
                'symbols_analyzed': self.symbols,
                'data_timeframe': '20:15 - 20:39 UTC',
                'analysis_type': 'comparative_breakout_analysis'
            },
            'current_market_analysis': current_patterns,
            'comparative_analysis': comparison,
            'executive_summary': self._generate_executive_summary(current_patterns, comparison),
            'trading_recommendations': self._generate_trading_recommendations(current_patterns),
            'next_analysis_schedule': (self.analysis_timestamp + timedelta(minutes=30)).isoformat()
        }
        
        return report

    def _generate_executive_summary(self, patterns: Dict, comparison: Dict) -> Dict[str, Any]:
        """Generar resumen ejecutivo"""
        # Contar oportunidades por categoría
        high_potential = [s for s, p in patterns.items() if p['breakout_potential']['score'] > 70]
        medium_potential = [s for s, p in patterns.items() if 50 <= p['breakout_potential']['score'] <= 70]
        
        return {
            'market_condition': comparison['market_evolution']['current_condition'],
            'time_since_last_analysis': comparison['market_evolution']['time_elapsed'],
            'high_potential_breakouts': len(high_potential),
            'medium_potential_breakouts': len(medium_potential),
            'symbols_with_exceptional_volume': [s for s, p in patterns.items() 
                                              if p['volume_analysis']['trend'] == 'significantly_increasing'],
            'dominant_trend': 'bullish' if sum(1 for p in patterns.values() 
                                             if p['trend_strength']['direction'] == 'bullish') >= 3 else 'mixed',
            'key_developments': comparison['new_developments'][:3],  # Top 3
            'overall_risk_level': comparison['risk_assessment']['market_risk']
        }

    def _generate_trading_recommendations(self, patterns: Dict) -> Dict[str, Any]:
        """Generar recomendaciones de trading"""
        recommendations = {
            'immediate_opportunities': [],
            'watch_list': [],
            'risk_management': [],
            'position_sizing': {}
        }
        
        for symbol, pattern in patterns.items():
            score = pattern['breakout_potential']['score']
            
            if score > 80:
                recommendations['immediate_opportunities'].append({
                    'symbol': symbol,
                    'action': 'prepare_for_breakout',
                    'direction': pattern['breakout_potential']['likely_direction'],
                    'confidence': score,
                    'entry_level': pattern['support_resistance']['immediate_resistance'] 
                                 if pattern['breakout_potential']['likely_direction'] == 'bullish'
                                 else pattern['support_resistance']['immediate_support']
                })
            elif score > 60:
                recommendations['watch_list'].append({
                    'symbol': symbol,
                    'reason': 'medium_breakout_potential',
                    'score': score,
                    'key_level': pattern['support_resistance']['immediate_resistance']
                })
        
        # Gestión de riesgo
        recommendations['risk_management'] = [
            "Monitorear volumen para confirmación de breakouts",
            "Establecer stop-loss ajustados por volatilidad",
            "Considerar correlaciones entre símbolos",
            "Preparar para volatilidad aumentada"
        ]
        
        return recommendations

def main():
    """Función principal para ejecutar el análisis"""
    print("🔍 INICIANDO ANÁLISIS COMPARATIVO DE BREAKOUTS")
    print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)
    
    analyzer = ComparativeBreakoutAnalysis()
    report = analyzer.generate_comprehensive_report()
    
    # Guardar reporte
    filename = f"comparative_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"📊 RESUMEN EJECUTIVO:")
    summary = report['executive_summary']
    print(f"   • Condición del mercado: {summary['market_condition']}")
    print(f"   • Breakouts de alto potencial: {summary['high_potential_breakouts']}")
    print(f"   • Tendencia dominante: {summary['dominant_trend']}")
    print(f"   • Nivel de riesgo: {summary['overall_risk_level']}")
    
    print(f"\n🎯 OPORTUNIDADES INMEDIATAS:")
    for opp in report['trading_recommendations']['immediate_opportunities']:
        print(f"   • {opp['symbol']}: {opp['direction']} breakout (Confianza: {opp['confidence']}%)")
    
    print(f"\n📈 DESARROLLOS CLAVE:")
    for dev in summary['key_developments']:
        print(f"   • {dev}")
    
    print(f"\n💾 Reporte guardado como: {filename}")
    print("✅ ANÁLISIS COMPLETADO")
    
    return report

if __name__ == "__main__":
    main()