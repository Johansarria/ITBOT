#!/usr/bin/env python3
"""
GESTIÓN DE TRANSICIÓN A MICRO-PRUEBAS
Manejar posiciones existentes que exceden límites de micro-pruebas
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
from datetime import datetime

def manage_transition_to_micro_testing():
    print("🔄 GESTIÓN DE TRANSICIÓN A MICRO-PRUEBAS")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    
    client = get_um_futures_client()
    
    try:
        # Obtener estado actual
        account = client.futures_account()
        positions = client.futures_position_information()
        
        total_balance = float(account['totalWalletBalance'])
        available_balance = float(account['availableBalance'])
        
        print(f"\n📊 ESTADO ACTUAL:")
        print(f"   Balance total: ${total_balance:.2f}")
        print(f"   Balance disponible: ${available_balance:.2f}")
        
        # Identificar posiciones que exceden límites
        micro_limit = 0.75
        oversized_positions = []
        compliant_positions = []
        
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                symbol = pos['symbol']
                size = abs(float(pos['positionAmt']))
                notional = abs(float(pos['notional']))
                entry_price = float(pos['entryPrice'])
                
                # Obtener precio actual
                ticker = client.futures_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                
                pnl = (current_price - entry_price) * float(pos['positionAmt'])
                
                position_data = {
                    'symbol': symbol,
                    'size': size,
                    'notional': notional,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'pnl': pnl,
                    'pnl_pct': (pnl / notional) * 100 if notional > 0 else 0
                }
                
                if notional > micro_limit:
                    oversized_positions.append(position_data)
                else:
                    compliant_positions.append(position_data)
        
        print(f"\n🧪 ANÁLISIS DE CUMPLIMIENTO MICRO-PRUEBAS:")
        print(f"   ✅ Posiciones que cumplen límites: {len(compliant_positions)}")
        print(f"   🚨 Posiciones que exceden límites: {len(oversized_positions)}")
        
        # Mostrar posiciones problemáticas
        if oversized_positions:
            print(f"\n🚨 POSICIONES QUE EXCEDEN LÍMITES:")
            for pos in oversized_positions:
                print(f"   📊 {pos['symbol']}:")
                print(f"      Size: ${pos['notional']:.2f} (límite: ${micro_limit:.2f})")
                print(f"      Entry: ${pos['entry_price']:.2f} | Current: ${pos['current_price']:.2f}")
                print(f"      PnL: {pos['pnl_pct']:+.2f}% (${pos['pnl']:+.2f})")
        
        # Opciones de gestión
        print(f"\n💡 OPCIONES DE GESTIÓN:")
        
        if oversized_positions:
            print(f"\n📋 OPCIÓN 1: MANTENER CON MONITOREO ESPECIAL")
            print(f"   ✅ Ventajas: No cerrar posiciones en pérdida")
            print(f"   ✅ Las posiciones existentes mantienen sus SL/TP")
            print(f"   ✅ Nuevas posiciones respetarán límites micro")
            print(f"   ⚠️ Limitación: Exposición actual > límites micro")
            
            print(f"\n📋 OPCIÓN 2: CIERRE PARCIAL GRADUAL")
            for pos in oversized_positions:
                current_size = pos['notional']
                target_size = micro_limit
                reduction_needed = current_size - target_size
                reduction_pct = (reduction_needed / current_size) * 100
                
                print(f"   🎯 {pos['symbol']}: Reducir ${reduction_needed:.2f} ({reduction_pct:.0f}%)")
                print(f"      De ${current_size:.2f} → ${target_size:.2f}")
            
            print(f"\n📋 OPCIÓN 3: MODO HÍBRIDO (RECOMENDADO)")
            print(f"   🎯 Mantener posiciones existentes con protección actual")
            print(f"   🧪 Nuevas operaciones siguen límites micro-pruebas")
            print(f"   📊 Monitoreo dual: posiciones legacy + micro-pruebas")
            print(f"   ✅ Mejor balance entre seguridad y oportunidad")
        
        # Calcular impacto de cada opción
        print(f"\n📊 IMPACTO DE OPCIONES:")
        
        if oversized_positions:
            total_oversized_notional = sum(pos['notional'] for pos in oversized_positions)
            total_oversized_pnl = sum(pos['pnl'] for pos in oversized_positions)
            
            print(f"\n   OPCIÓN 1 (Mantener):")
            print(f"   📊 Exposición actual: ${total_oversized_notional:.2f}")
            print(f"   💰 PnL en riesgo: ${total_oversized_pnl:+.2f}")
            print(f"   🛡️ Protección: SL existentes")
            
            print(f"\n   OPCIÓN 2 (Cierre parcial):")
            impact_if_closed = sum(pos['pnl'] for pos in oversized_positions if pos['pnl'] < 0)
            print(f"   💰 Impacto inmediato: ${impact_if_closed:+.2f}")
            print(f"   📊 Nueva exposición: ${len(oversized_positions) * micro_limit:.2f}")
            print(f"   🛡️ Cumplimiento: 100%")
            
            print(f"\n   OPCIÓN 3 (Híbrido):")
            print(f"   📊 Exposición legacy: ${total_oversized_notional:.2f}")
            print(f"   🧪 Espacio para micro-pruebas: ${available_balance:.2f}")
            print(f"   🎯 Flexibilidad máxima")
        
        # Recomendación
        print(f"\n🎯 RECOMENDACIÓN:")
        if oversized_positions:
            worst_pnl = min((pos['pnl'] for pos in oversized_positions), default=0)
            if worst_pnl < -0.20:  # Si hay pérdidas significativas
                print(f"   ✅ OPCIÓN 3 (Híbrido) - Mejor para situación actual")
                print(f"   💡 Razón: Posiciones en pérdida, mejor mantener con protección")
            else:
                print(f"   ✅ OPCIÓN 1 (Mantener) - Posiciones estables")
                print(f"   💡 Razón: Sin pérdidas significativas")
        else:
            print(f"   ✅ Sistema ya cumple límites micro-pruebas")
        
        print(f"\n🔄 PRÓXIMOS PASOS:")
        print(f"   1️⃣ Mantener monitoreo continuo activo")
        print(f"   2️⃣ Posiciones existentes: Supervisión con SL actuales")
        print(f"   3️⃣ Nuevas operaciones: Estrictos límites micro ($0.75)")
        print(f"   4️⃣ Evaluación diaria de cumplimiento")
        
        return {
            'oversized_positions': len(oversized_positions),
            'total_exposure': sum(pos['notional'] for pos in oversized_positions),
            'recommendation': 'hybrid' if oversized_positions else 'compliant'
        }
        
    except Exception as e:
        print(f"❌ Error en análisis de transición: {e}")
        return None

if __name__ == "__main__":
    result = manage_transition_to_micro_testing()
    
    if result:
        print(f"\n✅ ANÁLISIS DE TRANSICIÓN COMPLETADO")
        if result['oversized_positions'] > 0:
            print(f"🔄 Modo híbrido recomendado para transición gradual")
        else:
            print(f"🧪 Sistema listo para micro-pruebas puras")
    else:
        print(f"\n❌ ERROR EN ANÁLISIS")
