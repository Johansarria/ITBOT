#!/usr/bin/env python3
"""
Script de prueba para el sistema dinámico integrado
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.dynamic_pair_manager import dynamic_pair_manager

async def test_dynamic_integration():
    """
    Prueba completa del sistema dinámico integrado
    """
    
    print("🚀 PROBANDO INTEGRACIÓN COMPLETA DEL SISTEMA DINÁMICO")
    print("=" * 60)
    
    # 1. Inicialización
    print("\n📋 1. INICIALIZACIÓN DEL SISTEMA")
    print("-" * 30)
    success = await dynamic_pair_manager.initialize()
    print(f"✅ Inicialización exitosa: {success}")
    
    if not success:
        print("❌ Error en inicialización. Terminando prueba.")
        return
    
    # 2. Estado inicial
    print("\n📊 2. ESTADO INICIAL")
    print("-" * 30)
    current_pairs = await dynamic_pair_manager.get_current_pairs()
    print(f"📊 Pares activos: {len(current_pairs)}")
    print(f"🎯 Lista de pares: {', '.join(current_pairs)}")
    
    # 3. Reporte de estado completo
    print("\n📋 3. REPORTE DE ESTADO DETALLADO")
    print("-" * 30)
    status_report = await dynamic_pair_manager.get_status_report()
    
    system_status = status_report.get("system_status", {})
    config = status_report.get("configuration", {})
    
    print(f"🟢 Sistema inicializado: {system_status.get('is_initialized')}")
    print(f"📈 Pares configurados: {system_status.get('current_pairs_count')}")
    print(f"⏰ Última evaluación: {system_status.get('last_evaluation')}")
    print(f"🔄 Requiere re-evaluación: {system_status.get('needs_reevaluation')}")
    print(f"⚙️ Máximo pares: {config.get('max_pairs')}")
    print(f"🕐 Intervalo re-evaluación: {config.get('reevaluation_interval_hours')}h")
    
    # 4. Verificar necesidad de actualización
    print("\n🔍 4. VERIFICACIÓN DE ACTUALIZACIONES")
    print("-" * 30)
    changes_made, change_details = await dynamic_pair_manager.check_and_update_pairs()
    
    if changes_made and change_details:
        print("✅ Se realizaron cambios en los pares:")
        print(f"   ➕ Agregados: {change_details.get('pairs_added', [])}")
        print(f"   ➖ Removidos: {change_details.get('pairs_removed', [])}")
        print(f"   🔄 Mantenidos: {change_details.get('pairs_maintained', [])}")
    else:
        print("ℹ️  No se requirieron cambios en la selección actual")
    
    # 5. Estado final
    print("\n📊 5. ESTADO FINAL")
    print("-" * 30)
    final_pairs = await dynamic_pair_manager.get_current_pairs()
    print(f"📊 Pares finales: {len(final_pairs)}")
    print(f"🎯 Lista final: {', '.join(final_pairs)}")
    
    # 6. Historial
    print("\n📈 6. HISTORIAL DE EVALUACIONES")
    print("-" * 30)
    history = await dynamic_pair_manager.get_evaluation_history()
    print(f"📋 Total evaluaciones: {len(history)}")
    
    if history:
        latest = history[-1]
        print(f"🕐 Última evaluación: {latest.get('timestamp', 'N/A')}")
        print(f"🔄 Hubo cambios: {latest.get('changes_made', False)}")
        print(f"⏱️  Duración: {latest.get('evaluation_duration_seconds', 0):.1f}s")
    
    print("\n🎉 PRUEBA COMPLETADA EXITOSAMENTE")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_dynamic_integration())
        if result:
            print("\n✅ Sistema dinámico completamente funcional")
            print("🚀 Listo para integración con run_bot.py")
        else:
            print("\n❌ Error en las pruebas del sistema")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error crítico: {e}")
        sys.exit(1)
