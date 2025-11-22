#!/usr/bin/env python3
"""
Test para verificar que el sistema genera trades con valores normales
basados en análisis técnico real durante las ventanas críticas.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_breakout_detector import EnhancedBreakoutDetector
from binance_data_provider import BinanceDataProvider
from enhanced_config import CONFIG

def test_normal_trading_values():
    """Test que verifica valores normales de trading"""
    
    print("🔍 INICIANDO TEST DE VALORES NORMALES DE TRADING")
    print("=" * 60)
    
    try:
        # Inicializar componentes
        data_provider = BinanceDataProvider()
        detector = EnhancedBreakoutDetector()
        
        # Obtener datos reales
        symbol = 'ETHUSDT'
        print(f"📊 Obteniendo datos para {symbol}...")
        
        df = data_provider.get_historical_data(symbol, '1m', 50)
        print(f"✅ Datos obtenidos: {len(df)} velas")
        
        # Convertir DataFrame a formato de lista para el detector
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
        
        detector.price_history[symbol] = data
        
        # Mostrar datos del mercado actual
        current_price = df['close'].iloc[-1]
        current_volume = df['volume'].iloc[-1]
        
        print(f"💰 Precio actual: ${current_price:.4f}")
        print(f"📈 Volumen actual: {current_volume:.2f}")
        
        # Calcular estadísticas de mercado
        recent_changes = []
        recent_volumes = df['volume'].tail(10).values
        
        for i in range(min(10, len(df)-1)):
            prev_close = df['close'].iloc[-(i+2)]
            curr_close = df['close'].iloc[-(i+1)]
            change = ((curr_close - prev_close) / prev_close) * 100
            recent_changes.append(abs(change))
        
        avg_movement = np.mean(recent_changes)
        avg_volume = np.mean(recent_volumes)
        current_volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        print(f"\n📊 ANÁLISIS DE MERCADO:")
        print(f"   • Movimiento promedio: {avg_movement:.4f}%")
        print(f"   • Volumen promedio: {avg_volume:.2f}")
        print(f"   • Ratio volumen actual: {current_volume_ratio:.2f}x")
        
        # Probar la función de garantía con valores normales
        print(f"\n🧪 PROBANDO GENERACIÓN DE BREAKOUT NORMAL...")
        
        # Simular ventana de sesión
        session_name = "TEST"
        
        # Verificar que tenemos datos
        print(f"   • Datos en price_history: {len(detector.price_history)}")
        
        # Llamar directamente a la función de garantía
        try:
            normal_signal = detector._guarantee_session_breakout(symbol, session_name)
            print(f"   • Resultado de la función: {normal_signal is not None}")
        except Exception as e:
            print(f"   • Error en la función: {e}")
            normal_signal = None
        
        if normal_signal:
            print(f"\n✅ SEÑAL NORMAL GENERADA:")
            print(f"   • Símbolo: {normal_signal.symbol}")
            print(f"   • Tipo: {normal_signal.breakout_type.value}")
            print(f"   • Fuerza: {normal_signal.strength.value}")
            print(f"   • Confianza: {normal_signal.confidence:.1f}%")
            print(f"   • Precio: ${normal_signal.price:.4f}")
            print(f"   • Cambio precio: {normal_signal.price_change_pct:.4f}%")
            print(f"   • Volumen: {normal_signal.volume:.2f}")
            print(f"   • Ratio volumen: {normal_signal.volume_ratio:.2f}x")
            print(f"   • Patrón: {normal_signal.candle_pattern}")
            
            # Verificar que los valores son realistas
            print(f"\n🔍 VERIFICACIÓN DE VALORES NORMALES:")
            
            # Verificar movimiento de precio
            is_normal_movement = abs(normal_signal.price_change_pct) >= avg_movement * 0.3
            print(f"   • Movimiento realista: {'✅' if is_normal_movement else '❌'} "
                  f"({abs(normal_signal.price_change_pct):.4f}% vs min {avg_movement * 0.3:.4f}%)")
            
            # Verificar volumen
            is_normal_volume = normal_signal.volume_ratio >= 1.1 and normal_signal.volume_ratio <= 3.0
            print(f"   • Volumen realista: {'✅' if is_normal_volume else '❌'} "
                  f"({normal_signal.volume_ratio:.2f}x entre 1.1x-3.0x)")
            
            # Verificar confianza
            is_normal_confidence = normal_signal.confidence >= 60.0 and normal_signal.confidence <= 85.0
            print(f"   • Confianza realista: {'✅' if is_normal_confidence else '❌'} "
                  f"({normal_signal.confidence:.1f}% entre 60%-85%)")
            
            # Verificar patrón
            is_normal_pattern = "NORMAL" in normal_signal.candle_pattern
            print(f"   • Patrón normal: {'✅' if is_normal_pattern else '❌'} "
                  f"({normal_signal.candle_pattern})")
            
            # Resultado final
            all_normal = all([is_normal_movement, is_normal_volume, is_normal_confidence, is_normal_pattern])
            
            print(f"\n🎯 RESULTADO FINAL:")
            if all_normal:
                print("   ✅ TODOS LOS VALORES SON NORMALES Y REALISTAS")
                print("   🎉 El sistema genera trades con valores de mercado reales")
            else:
                print("   ❌ ALGUNOS VALORES NO SON COMPLETAMENTE NORMALES")
                print("   ⚠️  Se requieren ajustes adicionales")
                
            return all_normal
        else:
            print("❌ No se pudo generar señal normal")
            return False
            
    except Exception as e:
        logger.error(f"Error en test: {e}")
        print(f"❌ ERROR EN TEST: {e}")
        return False

if __name__ == "__main__":
    success = test_normal_trading_values()
    
    if success:
        print(f"\n🎉 ¡TEST EXITOSO!")
        print("   El sistema ahora genera trades con valores completamente normales")
    else:
        print(f"\n❌ TEST FALLIDO")
        print("   Se requieren ajustes adicionales en el sistema")