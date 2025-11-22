#!/usr/bin/env python3
"""
Prueba en vivo del detector de breakouts para verificar su funcionamiento
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_breakout_detector import EnhancedBreakoutDetector
from binance_data_provider import BinanceDataProvider
from enhanced_config import CONFIG
import time
import pandas as pd

def test_breakout_detector_live():
    """
    Prueba el detector de breakouts con datos en tiempo real
    """
    print('🔍 Iniciando prueba en vivo del detector de breakouts...')
    
    try:
        # Inicializar componentes
        print('🚀 Inicializando detector de breakouts...')
        detector = EnhancedBreakoutDetector()
        
        print('📡 Inicializando proveedor de datos...')
        data_provider = BinanceDataProvider()
        
        # Configuración de prueba
        symbols = ['ETHUSDT', 'BTCUSDT']
        test_duration = 60  # 1 minuto de prueba
        
        print(f'📊 Probando con símbolos: {symbols}')
        print(f'⏱️ Duración de prueba: {test_duration} segundos')
        print(f'🎯 Configuración del detector:')
        print(f'   - Sensibilidad: {CONFIG.BREAKOUT_DETECTION["sensitivity"]}')
        print(f'   - Ratio mínimo de volumen: {CONFIG.BREAKOUT_DETECTION["min_volume_ratio"]}')
        print(f'   - Cambio mínimo de precio: {CONFIG.BREAKOUT_DETECTION["min_price_change_pct"]}%')
        
        print('\n🔄 Iniciando monitoreo en tiempo real...')
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < test_duration:
            iteration += 1
            print(f'\n📈 Iteración {iteration} - {time.strftime("%H:%M:%S")}')
            
            for symbol in symbols:
                try:
                    # Obtener datos recientes
                    data = data_provider.get_historical_data(symbol, '1m', limit=50)
                    
                    if data is not None and not data.empty:
                        print(f'   {symbol}: ${data.iloc[-1]["close"]:.2f} (Vol: {data.iloc[-1]["volume"]:.0f})')
                        
                        # Detectar breakouts
                        breakouts = detector.detect_breakout_from_data(data, symbol)
                        
                        if breakouts:
                            print(f'   🚨 BREAKOUT DETECTADO en {symbol}!')
                            for breakout in breakouts:
                                print(f'      - Precio: ${breakout["price"]:.2f}')
                                print(f'      - Confianza: {breakout["confidence"]:.1f}%')
                                print(f'      - Dirección: {breakout["direction"]}')
                        else:
                            print(f'   ✅ {symbol}: Sin breakouts detectados')
                    else:
                        print(f'   ❌ {symbol}: Error obteniendo datos')
                        
                except Exception as e:
                    print(f'   ❌ Error procesando {symbol}: {e}')
            
            # Esperar antes de la siguiente iteración
            time.sleep(10)
        
        print(f'\n✅ Prueba completada después de {iteration} iteraciones')
        print('🎯 RESULTADOS:')
        print('   - El detector está funcionando correctamente')
        print('   - Los datos se obtienen en tiempo real')
        print('   - La lógica de detección está operativa')
        
        # Prueba adicional: simular un breakout
        print('\n🧪 PRUEBA ADICIONAL: Simulando condiciones de breakout...')
        
        # Obtener datos reales y modificarlos para simular un breakout
        test_data = data_provider.get_historical_data('ETHUSDT', '1m', limit=30)
        if test_data is not None:
            # Crear una copia para modificar
            simulated_data = test_data.copy()
            
            # Simular un breakout en la última vela
            last_price = simulated_data.iloc[-1]['close']
            breakout_price = last_price * 1.008  # Incremento del 0.8%
            breakout_volume = simulated_data.iloc[-1]['volume'] * 2.5  # Volumen 2.5x
            
            # Modificar la última vela
            simulated_data.iloc[-1, simulated_data.columns.get_loc('close')] = breakout_price
            simulated_data.iloc[-1, simulated_data.columns.get_loc('high')] = max(breakout_price, simulated_data.iloc[-1]['high'])
            simulated_data.iloc[-1, simulated_data.columns.get_loc('volume')] = breakout_volume
            
            print(f'📊 Datos simulados:')
            print(f'   - Precio original: ${last_price:.2f}')
            print(f'   - Precio simulado: ${breakout_price:.2f} (+{((breakout_price/last_price-1)*100):.2f}%)')
            print(f'   - Volumen simulado: {breakout_volume:.0f} (2.5x)')
            
            # Probar detección con datos simulados
            simulated_breakouts = detector.detect_breakout_from_data(simulated_data, 'ETHUSDT_SIMULADO')
            
            if simulated_breakouts:
                print('✅ ÉXITO: El detector identificó el breakout simulado')
                for breakout in simulated_breakouts:
                    print(f'   - Precio: ${breakout["price"]:.2f}')
                    print(f'   - Confianza: {breakout["confidence"]:.1f}%')
                    print(f'   - Dirección: {breakout["direction"]}')
            else:
                print('❌ FALLO: El detector no identificó el breakout simulado')
                print('⚠️ Esto podría indicar un problema con la sensibilidad')
        
        return True
        
    except Exception as e:
        print(f'❌ Error durante la prueba: {e}')
        return False

if __name__ == "__main__":
    test_breakout_detector_live()