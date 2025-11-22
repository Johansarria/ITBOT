#!/usr/bin/env python3
"""
Prueba del detector de breakouts con configuración ajustada
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_breakout_detector import EnhancedBreakoutDetector
from binance_data_provider import BinanceDataProvider
import pandas as pd

def test_adjusted_detector():
    """
    Prueba el detector con la nueva configuración ajustada
    """
    print('🔧 Probando detector con configuración ajustada...')
    
    try:
        # Inicializar componentes
        detector = EnhancedBreakoutDetector()
        data_provider = BinanceDataProvider()
        
        # Mostrar nueva configuración
        print(f'\n📊 NUEVA CONFIGURACIÓN:')
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
        
        # Probar con datos reales primero
        print(f'\n🔍 PROBANDO CON DATOS REALES:')
        real_breakouts = detector.detect_breakout_from_data(data, 'ETHUSDT_REAL')
        
        if real_breakouts:
            print(f'✅ Breakout detectado en datos reales!')
            for breakout in real_breakouts:
                print(f'   - Tipo: {breakout["type"]}')
                print(f'   - Confianza: {breakout["confidence"]:.1f}%')
                print(f'   - Fuerza: {breakout["strength"]}')
        else:
            print(f'❌ No se detectaron breakouts en datos reales')
        
        # Crear escenarios de prueba más realistas
        scenarios = [
            {'name': 'Breakout Mínimo', 'price_change': 0.3, 'volume_mult': 1.2},
            {'name': 'Breakout Pequeño', 'price_change': 0.5, 'volume_mult': 1.5},
            {'name': 'Breakout Moderado', 'price_change': 0.8, 'volume_mult': 2.0},
        ]
        
        print(f'\n🧪 PROBANDO ESCENARIOS AJUSTADOS:')
        
        for scenario in scenarios:
            print(f'\n📊 {scenario["name"]}:')
            
            # Crear datos simulados
            simulated_data = data.copy()
            last_price = simulated_data.iloc[-1]['close']
            
            # Calcular nuevo precio (breakout alcista)
            price_change_pct = scenario['price_change']
            new_price = last_price * (1 + price_change_pct / 100)
            
            # Calcular nuevo volumen de manera más realista
            volume_mult = scenario['volume_mult']
            avg_volume = simulated_data['volume'].tail(10).mean()  # Promedio de últimas 10 velas
            new_volume = avg_volume * volume_mult
            
            # Modificar la última vela
            simulated_data.iloc[-1, simulated_data.columns.get_loc('close')] = new_price
            simulated_data.iloc[-1, simulated_data.columns.get_loc('high')] = max(new_price, simulated_data.iloc[-1]['high'])
            simulated_data.iloc[-1, simulated_data.columns.get_loc('volume')] = new_volume
            
            print(f'   💰 Precio: ${last_price:.2f} → ${new_price:.2f} (+{price_change_pct:.1f}%)')
            print(f'   📊 Volumen: {avg_volume:.0f} → {new_volume:.0f} ({volume_mult:.1f}x)')
            
            # Probar detección
            breakouts = detector.detect_breakout_from_data(simulated_data, f'ETHUSDT_{scenario["name"].replace(" ", "_")}')
            
            if breakouts:
                breakout = breakouts[0]
                print(f'   ✅ DETECTADO - Confianza: {breakout["confidence"]:.1f}%, Fuerza: {breakout["strength"]}')
                print(f'   📈 Tipo: {breakout["type"]}')
            else:
                print(f'   ❌ NO DETECTADO')
                
                # Analizar criterios
                lookback_volume = simulated_data['volume'].rolling(detector.lookback_periods).mean().iloc[-1]
                volume_ratio = new_volume / lookback_volume if lookback_volume > 0 else 1
                
                print(f'      - Cambio de precio: {price_change_pct:.2f}% (mín: {detector.min_price_change}%)')
                print(f'      - Ratio de volumen: {volume_ratio:.2f}x (mín: {detector.min_volume_ratio}x)')
        
        # Probar breakout bajista también
        print(f'\n📉 PROBANDO BREAKOUT BAJISTA:')
        
        bearish_data = data.copy()
        last_price = bearish_data.iloc[-1]['close']
        new_price = last_price * 0.995  # -0.5% de caída
        avg_volume = bearish_data['volume'].tail(10).mean()
        new_volume = avg_volume * 1.5
        
        bearish_data.iloc[-1, bearish_data.columns.get_loc('close')] = new_price
        bearish_data.iloc[-1, bearish_data.columns.get_loc('low')] = min(new_price, bearish_data.iloc[-1]['low'])
        bearish_data.iloc[-1, bearish_data.columns.get_loc('volume')] = new_volume
        
        print(f'   💰 Precio: ${last_price:.2f} → ${new_price:.2f} (-0.5%)')
        print(f'   📊 Volumen: {avg_volume:.0f} → {new_volume:.0f} (1.5x)')
        
        bearish_breakouts = detector.detect_breakout_from_data(bearish_data, 'ETHUSDT_BEARISH')
        
        if bearish_breakouts:
            breakout = bearish_breakouts[0]
            print(f'   ✅ BREAKOUT BAJISTA DETECTADO - Confianza: {breakout["confidence"]:.1f}%')
        else:
            print(f'   ❌ Breakout bajista no detectado')
        
        print(f'\n✅ Prueba completada con nueva configuración')
        return True
        
    except Exception as e:
        print(f'❌ Error durante la prueba: {e}')
        return False

if __name__ == "__main__":
    test_adjusted_detector()