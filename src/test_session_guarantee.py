#!/usr/bin/env python3
"""
🚨 TEST DE GARANTÍA DE BREAKOUTS EN VENTANAS DE SESIÓN
Este script verifica que el sistema SIEMPRE genere operaciones durante las ventanas críticas
"""

import sys
import os
import time
import logging
from datetime import datetime, timedelta
import pytz

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_breakout_detector import EnhancedBreakoutDetector
from binance_data_provider import BinanceDataProvider
from enhanced_config import CONFIG

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def simulate_session_window_test():
    """
    🧪 SIMULAR PRUEBA DE VENTANA DE SESIÓN
    Fuerza el sistema a estar en una ventana crítica y verifica la garantía
    """
    print("🚨 INICIANDO TEST DE GARANTÍA DE BREAKOUTS EN VENTANAS DE SESIÓN")
    print("=" * 70)
    
    # Inicializar componentes
    detector = EnhancedBreakoutDetector()
    data_provider = BinanceDataProvider()
    
    # Configurar símbolo de prueba
    test_symbol = "ETHUSDT"
    
    print(f"📊 Obteniendo datos para {test_symbol}...")
    
    # Obtener datos reales
    df = data_provider.get_historical_data(test_symbol, "1m", 50)
    if df is None or df.empty:
        print("❌ Error obteniendo datos")
        return False
    
    # Convertir DataFrame a formato de lista de diccionarios para el detector
    data = []
    for timestamp, row in df.iterrows():
        data.append({
            'timestamp': timestamp,
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume']
        })
    
    # Agregar datos al detector
    detector.price_history[test_symbol] = data
    
    print(f"✅ Datos obtenidos: {len(data)} velas")
    print(f"💰 Precio actual: ${data[-1]['close']:.4f}")
    print(f"📈 Volumen actual: {data[-1]['volume']:.2f}")
    
    # Mostrar configuración ultra-sensible
    ultra_config = CONFIG.BREAKOUT_DETECTION['session_window_config']
    print(f"\n🎯 CONFIGURACIÓN ULTRA-SENSIBLE:")
    print(f"   • Sensibilidad: {ultra_config['sensitivity']}")
    print(f"   • Ratio volumen mín: {ultra_config['min_volume_ratio']}")
    print(f"   • Cambio precio mín: {ultra_config['min_price_change_pct']}%")
    print(f"   • Forzar detección: {ultra_config['force_detection']}")
    
    print(f"\n🚨 SIMULANDO VENTANAS CRÍTICAS DE SESIÓN...")
    print("-" * 50)
    
    # Simular cada sesión
    sessions = ["Asian", "European", "American"]
    results = []
    
    for session_name in sessions:
        print(f"\n🌍 PROBANDO SESIÓN {session_name.upper()}")
        
        # Simular que estamos en ventana crítica
        # Modificamos temporalmente el método _is_in_session_window
        original_method = detector._is_in_session_window
        
        def mock_session_window():
            return True, session_name
        
        detector._is_in_session_window = mock_session_window
        
        try:
            # Intentar análisis normal
            print(f"   🔍 Analizando con criterios ultra-sensibles...")
            signal = detector._analyze_symbol(test_symbol)
            
            if signal:
                print(f"   ✅ BREAKOUT DETECTADO:")
                print(f"      • Tipo: {signal.breakout_type.value}")
                print(f"      • Fuerza: {signal.strength.value}")
                print(f"      • Confianza: {signal.confidence:.1f}%")
                print(f"      • Cambio precio: {signal.price_change_pct:.4f}%")
                print(f"      • Patrón: {signal.candle_pattern}")
                results.append(True)
            else:
                print(f"   ❌ NO SE DETECTÓ BREAKOUT NATURAL")
                
                # Probar función de garantía directamente
                print(f"   🚨 ACTIVANDO GARANTÍA DE BREAKOUT...")
                guaranteed_signal = detector._guarantee_session_breakout(test_symbol, session_name)
                
                if guaranteed_signal:
                    print(f"   ✅ BREAKOUT GARANTIZADO GENERADO:")
                    print(f"      • Tipo: {guaranteed_signal.breakout_type.value}")
                    print(f"      • Fuerza: {guaranteed_signal.strength.value}")
                    print(f"      • Confianza: {guaranteed_signal.confidence:.1f}%")
                    print(f"      • Cambio precio: {guaranteed_signal.price_change_pct:.4f}%")
                    print(f"      • Patrón: {guaranteed_signal.candle_pattern}")
                    results.append(True)
                else:
                    print(f"   ❌ FALLÓ LA GARANTÍA DE BREAKOUT")
                    results.append(False)
        
        except Exception as e:
            print(f"   ❌ ERROR en sesión {session_name}: {e}")
            results.append(False)
        
        finally:
            # Restaurar método original
            detector._is_in_session_window = original_method
        
        time.sleep(1)  # Pausa entre pruebas
    
    # Resultados finales
    print(f"\n📊 RESULTADOS FINALES:")
    print("=" * 50)
    
    successful_sessions = sum(results)
    total_sessions = len(results)
    
    for i, session in enumerate(sessions):
        status = "✅ ÉXITO" if results[i] else "❌ FALLO"
        print(f"   {session}: {status}")
    
    print(f"\n🎯 RESUMEN:")
    print(f"   • Sesiones exitosas: {successful_sessions}/{total_sessions}")
    print(f"   • Tasa de éxito: {(successful_sessions/total_sessions)*100:.1f}%")
    
    if successful_sessions == total_sessions:
        print(f"\n🎉 ¡PERFECTO! El sistema garantiza breakouts en TODAS las ventanas críticas")
        return True
    else:
        print(f"\n⚠️  ATENCIÓN: El sistema no garantiza breakouts en todas las ventanas")
        return False

def test_real_time_session_detection():
    """
    🕐 PROBAR DETECCIÓN DE VENTANAS EN TIEMPO REAL
    """
    print(f"\n🕐 PROBANDO DETECCIÓN DE VENTANAS EN TIEMPO REAL")
    print("-" * 50)
    
    detector = EnhancedBreakoutDetector()
    
    # Probar detección actual
    is_session, session_name = detector._is_in_session_window()
    
    current_time = datetime.now(pytz.timezone('US/Eastern'))
    print(f"⏰ Hora actual (ET): {current_time.strftime('%H:%M:%S')}")
    
    if is_session:
        print(f"🚨 ¡VENTANA CRÍTICA ACTIVA! Sesión: {session_name}")
        print(f"   • El sistema debe estar en modo ultra-sensible")
        print(f"   • Detección acelerada cada 10 segundos")
        print(f"   • Garantía de breakout activada")
    else:
        print(f"😴 No hay ventana crítica activa")
        print(f"   • Sistema en modo normal")
        print(f"   • Detección cada 30 segundos")
    
    # Mostrar próximas ventanas
    print(f"\n📅 PRÓXIMAS VENTANAS CRÍTICAS:")
    sessions_config = CONFIG.SESSIONS_CONFIG
    
    for session_name, config in sessions_config.items():
        if config['active']:
            start_time = config['start_time']
            end_time = config['end_time']
            print(f"   • {session_name}: {start_time} - {end_time} ET")

if __name__ == "__main__":
    try:
        # Configurar logging
        logger.info("Iniciando test de garantía de sesiones")
        
        # Ejecutar pruebas
        success = simulate_session_window_test()
        test_real_time_session_detection()
        
        if success:
            print(f"\n🎉 ¡TEST COMPLETADO CON ÉXITO!")
            print(f"   El sistema garantiza operaciones en todas las ventanas críticas")
        else:
            print(f"\n⚠️  TEST COMPLETADO CON ADVERTENCIAS")
            print(f"   Revisar la lógica de garantía de breakouts")
        
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        logger.error(f"Error en test: {e}")