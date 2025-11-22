#!/usr/bin/env python3
"""
Análisis de sensibilidad del detector de breakouts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_breakout_detector import EnhancedBreakoutDetector
from binance_data_provider import BinanceDataProvider
from enhanced_config import CONFIG
import pandas as pd

def analyze_detector_sensitivity():
    """
    Analiza la sensibilidad del detector y sugiere ajustes
    """
    print('🔍 Analizando sensibilidad del detector de breakouts...')
    
    try:
        # Inicializar componentes
        detector = EnhancedBreakoutDetector()
        data_provider = BinanceDataProvider()
        
        # Mostrar configuración actual
        print(f'\n📊 CONFIGURACIÓN ACTUAL:')
        print(f'   - Sensibilidad: {detector.sensitivity}')
        print(f'   - Ratio mínimo de volumen: {detector.min_volume_ratio}')
        print(f'   - Cambio mínimo de precio: {detector.min_price_change}%')
        print(f'   - Períodos de lookback: {detector.lookback_periods}')
        
        # Obtener datos reales
        print(f'\n📈 Obteniendo datos de ETHUSDT...')
        data = data_provider.get_historical_data('ETHUSDT', '1m', limit=50)
        
        if data is None or data.empty:
            print('❌ No se pudieron obtener datos')
            return False
        
        print(f'✅ Datos obtenidos: {len(data)} velas')
        
        # Crear diferentes escenarios de breakout
        scenarios = [
            {'name': 'Breakout Suave', 'price_change': 0.5, 'volume_mult': 1.5},
            {'name': 'Breakout Moderado', 'price_change': 0.8, 'volume_mult': 2.0},
            {'name': 'Breakout Fuerte', 'price_change': 1.2, 'volume_mult': 2.5},
            {'name': 'Breakout Extremo', 'price_change': 2.0, 'volume_mult': 3.0},
        ]
        
        print(f'\n🧪 PROBANDO DIFERENTES ESCENARIOS:')
        
        for scenario in scenarios:
            print(f'\n📊 {scenario["name"]}:')
            
            # Crear datos simulados
            simulated_data = data.copy()
            last_price = simulated_data.iloc[-1]['close']
            
            # Calcular nuevo precio (breakout alcista)
            price_change_pct = scenario['price_change']
            new_price = last_price * (1 + price_change_pct / 100)
            
            # Calcular nuevo volumen
            volume_mult = scenario['volume_mult']
            new_volume = simulated_data.iloc[-1]['volume'] * volume_mult
            
            # Modificar la última vela
            simulated_data.iloc[-1, simulated_data.columns.get_loc('close')] = new_price
            simulated_data.iloc[-1, simulated_data.columns.get_loc('high')] = max(new_price, simulated_data.iloc[-1]['high'])
            simulated_data.iloc[-1, simulated_data.columns.get_loc('volume')] = new_volume
            
            print(f'   💰 Precio: ${last_price:.2f} → ${new_price:.2f} (+{price_change_pct:.1f}%)')
            print(f'   📊 Volumen: {simulated_data.iloc[-2]["volume"]:.0f} → {new_volume:.0f} ({volume_mult:.1f}x)')
            
            # Probar detección
            breakouts = detector.detect_breakout_from_data(simulated_data, f'ETHUSDT_{scenario["name"].replace(" ", "_")}')
            
            if breakouts:
                breakout = breakouts[0]
                print(f'   ✅ DETECTADO - Confianza: {breakout["confidence"]:.1f}%, Fuerza: {breakout["strength"]}')
            else:
                print(f'   ❌ NO DETECTADO')
                
                # Analizar por qué no se detectó
                print(f'   🔍 Análisis de criterios:')
                
                # Calcular métricas manualmente
                avg_volume = simulated_data['volume'].rolling(detector.lookback_periods).mean().iloc[-1]
                volume_ratio = new_volume / avg_volume if avg_volume > 0 else 1
                
                print(f'      - Cambio de precio: {price_change_pct:.2f}% (mín: {detector.min_price_change}%)')
                print(f'      - Ratio de volumen: {volume_ratio:.2f}x (mín: {detector.min_volume_ratio}x)')
                
                # Verificar cada criterio
                price_ok = price_change_pct >= detector.min_price_change
                volume_ok = volume_ratio >= detector.min_volume_ratio
                
                print(f'      - Criterio precio: {"✅" if price_ok else "❌"}')
                print(f'      - Criterio volumen: {"✅" if volume_ok else "❌"}')
        
        # Sugerir ajustes de sensibilidad
        print(f'\n💡 SUGERENCIAS DE AJUSTE:')
        
        current_config = CONFIG.BREAKOUT_DETECTION
        
        if not any(detector.detect_breakout_from_data(data.copy(), 'TEST') for _ in range(1)):
            print(f'   📉 El detector parece muy conservador')
            print(f'   🔧 Sugerencias:')
            print(f'      - Reducir sensibilidad de {detector.sensitivity} a {max(0.1, detector.sensitivity - 0.1):.1f}')
            print(f'      - Reducir ratio mínimo de volumen de {detector.min_volume_ratio} a {max(1.2, detector.min_volume_ratio - 0.2):.1f}')
            print(f'      - Reducir cambio mínimo de precio de {detector.min_price_change}% a {max(0.3, detector.min_price_change - 0.1):.1f}%')
        
        # Probar con sensibilidad ajustada
        print(f'\n🔧 PROBANDO CON SENSIBILIDAD AJUSTADA:')
        
        # Crear detector con sensibilidad reducida
        test_detector = EnhancedBreakoutDetector()
        test_detector.sensitivity = max(0.1, detector.sensitivity - 0.15)
        test_detector.min_volume_ratio = max(1.2, detector.min_volume_ratio - 0.3)
        test_detector.min_price_change = max(0.3, detector.min_price_change - 0.2)
        
        print(f'   📊 Nueva configuración:')
        print(f'      - Sensibilidad: {test_detector.sensitivity}')
        print(f'      - Ratio mínimo de volumen: {test_detector.min_volume_ratio}')
        print(f'      - Cambio mínimo de precio: {test_detector.min_price_change}%')
        
        # Probar escenario moderado con nueva configuración
        moderate_scenario = scenarios[1]  # Breakout Moderado
        simulated_data = data.copy()
        last_price = simulated_data.iloc[-1]['close']
        new_price = last_price * (1 + moderate_scenario['price_change'] / 100)
        new_volume = simulated_data.iloc[-1]['volume'] * moderate_scenario['volume_mult']
        
        simulated_data.iloc[-1, simulated_data.columns.get_loc('close')] = new_price
        simulated_data.iloc[-1, simulated_data.columns.get_loc('high')] = max(new_price, simulated_data.iloc[-1]['high'])
        simulated_data.iloc[-1, simulated_data.columns.get_loc('volume')] = new_volume
        
        adjusted_breakouts = test_detector.detect_breakout_from_data(simulated_data, 'ETHUSDT_ADJUSTED')
        
        if adjusted_breakouts:
            breakout = adjusted_breakouts[0]
            print(f'   ✅ ÉXITO: Breakout detectado con configuración ajustada')
            print(f'      - Confianza: {breakout["confidence"]:.1f}%')
            print(f'      - Fuerza: {breakout["strength"]}')
            print(f'   💡 Se recomienda aplicar estos ajustes al sistema')
        else:
            print(f'   ❌ Aún no se detecta con configuración ajustada')
            print(f'   ⚠️ Puede ser necesario un ajuste más agresivo')
        
        return True
        
    except Exception as e:
        print(f'❌ Error durante el análisis: {e}')
        return False

if __name__ == "__main__":
    analyze_detector_sensitivity()