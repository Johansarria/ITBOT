#!/usr/bin/env python3
"""
Plan de acción inmediato para reducir riesgo y proteger capital
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from utils.binance_client import get_um_futures_client

async def emergency_risk_management():
    print("🚨 PLAN DE ACCIÓN INMEDIATO - PROTEGER CAPITAL")
    print("=" * 60)
    
    print("📊 SITUACIÓN ACTUAL:")
    print("   ⚠️  Uso de margen: 2,116.5% (CRÍTICO)")
    print("   💰 Solo $0.27 disponible")
    print("   📉 Ambas posiciones en pérdida")
    print("   🎯 Risk/Liquidación: ALTO")
    
    print("\n🎯 ACCIONES RECOMENDADAS (ORDEN DE PRIORIDAD):")
    
    print("\n🥇 PRIORIDAD 1: PROTEGER CONTRA LIQUIDACIÓN")
    print("   1️⃣ INMEDIATO - Ajustar Stop Loss más conservadores:")
    print("      • ETHUSDT: Mover SL de $4,365.64 → $4,380.00 (más cerca)")
    print("      • SOLUSDT: Mover SL de $206.57 → $208.00 (más cerca)")
    print("      💡 Razón: Proteger contra pérdidas mayores")
    
    print("\n   2️⃣ CONSIDERAR - Cierre parcial de posición más perdedora:")
    print("      • ETHUSDT está perdiendo más (-$0.23 vs -$0.08)")
    print("      • Cerrar 50% de ETHUSDT para liberar margen")
    print("      💡 Razón: Reducir exposición manteniendo upside")
    
    print("\n🥈 PRIORIDAD 2: OPTIMIZAR GESTIÓN DE RIESGO")
    print("   3️⃣ Activar alertas de precio:")
    print("      • ETHUSDT: Alerta si cae por debajo de $4,400")
    print("      • SOLUSDT: Alerta si cae por debajo de $207")
    print("      💡 Razón: Reacción rápida a movimientos adversos")
    
    print("\n   4️⃣ Ajustar configuración para futuros trades:")
    print("      • Reducir MICRO_TRADE_MAX_USDT de $7.52 → $3.76")
    print("      • Usar solo 50% del balance disponible por trade")
    print("      💡 Razón: Prevenir futura sobreexposición")
    
    print("\n🥉 PRIORIDAD 3: MAXIMIZAR OPORTUNIDADES DE RECUPERACIÓN")
    print("   5️⃣ Monitoreo activo cada 15 minutos:")
    print("      • Revisar si alguna posición se acerca a break-even")
    print("      • Estar listo para mover SL a break-even en +0.5%")
    print("      💡 Razón: Proteger cualquier ganancia que aparezca")
    
    print("\n   6️⃣ Preparar para reversión:")
    print("      • Si ETHUSDT sube a $4,430, mover SL a $4,420")
    print("      • Si SOLUSDT sube a $210, mover SL a $209")
    print("      💡 Razón: Capturar cualquier momentum positivo")
    
    print("\n💡 CÁLCULOS DE PROTECCIÓN:")
    
    # Calcular escenarios
    eth_current = 4407.00
    eth_entry = 4453.34
    sol_current = 208.13
    sol_entry = 210.80
    
    # Pérdida máxima actual con SL
    eth_sl_loss = (4453.34 - 4365.64) * 0.005  # $0.44
    sol_sl_loss = (210.80 - 206.57) * 0.03     # $0.13
    total_max_loss = eth_sl_loss + sol_sl_loss
    
    print(f"   📊 Pérdida máxima actual con SL: ${total_max_loss:.2f}")
    print(f"   📊 Esto representa: {(total_max_loss/6.11)*100:.1f}% del balance total")
    
    # Escenario de cierre inmediato
    current_loss = 0.08 + 0.23  # $0.31
    print(f"   📊 Pérdida si cierra ahora: ${current_loss:.2f} ({(current_loss/6.11)*100:.1f}% del balance)")
    
    print("\n🎯 RECOMENDACIÓN FINAL:")
    if total_max_loss > 0.50:  # Más del 8% del balance
        print("   🚨 ACCIÓN: Ajustar SL inmediatamente - Riesgo muy alto")
        print("   💡 SL recomendados: ETH $4,400 | SOL $209")
    else:
        print("   📊 MANTENER: SL actuales están en rango aceptable")
        print("   💡 Pero monitorear muy de cerca por uso de margen alto")
    
    print("\n⚠️  ADVERTENCIA IMPORTANTE:")
    print("   🔥 Con 2,116% de uso de margen, cualquier movimiento")
    print("      adverso del 2-3% puede activar liquidación")
    print("   🛡️  La protección del capital es PRIORIDAD ABSOLUTA")
    print("   📈 Solo después de reducir riesgo, pensar en maximizar")
    
    print("\n" + "="*60)
    print("✅ Plan de acción completado!")

if __name__ == "__main__":
    asyncio.run(emergency_risk_management())
