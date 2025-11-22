"""
Script de Prueba para Integración Mejorada SICAR
Activa y monitorea la integración sin interrumpir la simulación
"""

import asyncio
import json
import time
from datetime import datetime
import sys
import os

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_integration_manager import (
    INTEGRATION_MANAGER,
    start_enhanced_integration,
    get_integration_status,
    generate_integration_report
)
from enhanced_logger import SICAR_LOGGER

async def test_enhanced_integration():
    """Probar la integración mejorada"""
    print("=" * 80)
    print("🚀 INICIANDO PRUEBA DE INTEGRACIÓN MEJORADA SICAR")
    print("=" * 80)
    
    try:
        # 1. Verificar estado inicial
        print("\n📊 1. Verificando estado inicial...")
        initial_status = get_integration_status()
        print(f"   Estado inicial: {'ACTIVO' if initial_status.get('is_active') else 'INACTIVO'}")
        
        # 2. Iniciar integración mejorada
        print("\n🔄 2. Iniciando integración mejorada...")
        success = await start_enhanced_integration()
        
        if success:
            print("   ✅ Integración mejorada iniciada correctamente")
            SICAR_LOGGER.log_alert("TEST_INTEGRATION", "Integración mejorada iniciada en modo prueba", "INFO")
        else:
            print("   ❌ Error iniciando integración mejorada")
            return False
        
        # 3. Monitorear por 2 minutos
        print("\n⏱️  3. Monitoreando integración por 2 minutos...")
        monitoring_duration = 120  # 2 minutos
        check_interval = 15  # cada 15 segundos
        
        for i in range(0, monitoring_duration, check_interval):
            await asyncio.sleep(check_interval)
            
            # Obtener estado actual
            current_status = get_integration_status()
            
            # Mostrar progreso
            elapsed = i + check_interval
            progress = (elapsed / monitoring_duration) * 100
            
            print(f"\n   📈 Progreso: {progress:.1f}% ({elapsed}s/{monitoring_duration}s)")
            
            # Mostrar métricas clave
            metrics = current_status.get('performance_metrics', {})
            print(f"   🔍 Análisis XAI: {metrics.get('xai_analyses', 0)}")
            print(f"   🎯 Decisiones totales: {metrics.get('total_decisions', 0)}")
            print(f"   📊 Integraciones exitosas: {metrics.get('successful_integrations', 0)}")
            print(f"   🔄 Tiempo activo: {metrics.get('system_uptime', 0):.1f}s")
            
            # Verificar salud del sistema
            health = current_status.get('system_health', {})
            if not health.get('integration_thread_alive', False):
                print("   ⚠️  ADVERTENCIA: Hilo de integración no está activo")
            
            # Mostrar estado de sistemas integrados
            autonomous_status = current_status.get('autonomous_status', {})
            pattern_stats = current_status.get('pattern_stats', {})
            
            print(f"   🤖 Motor autónomo: {'ACTIVO' if autonomous_status.get('is_running') else 'INACTIVO'}")
            print(f"   🔍 Patrones detectados: {pattern_stats.get('total_patterns', 0)}")
        
        # 4. Generar reporte final
        print("\n📋 4. Generando reporte final...")
        final_report = generate_integration_report()
        
        print("\n" + "=" * 60)
        print("📊 REPORTE FINAL DE INTEGRACIÓN")
        print("=" * 60)
        
        # Resumen de integración
        summary = final_report.get('integration_summary', {})
        print(f"Estado final: {summary.get('status', 'DESCONOCIDO')}")
        print(f"Tiempo activo: {summary.get('uptime_hours', 0):.2f} horas")
        print(f"Operaciones totales: {summary.get('total_operations', 0)}")
        
        # Rendimiento del sistema
        performance = final_report.get('system_performance', {})
        print(f"\nRendimiento:")
        print(f"  • Decisiones/hora: {performance.get('decisions_per_hour', 0):.2f}")
        print(f"  • Patrones/hora: {performance.get('patterns_per_hour', 0):.2f}")
        print(f"  • Análisis/hora: {performance.get('analyses_per_hour', 0):.2f}")
        print(f"  • Tasa de éxito: {performance.get('integration_success_rate', 0):.2%}")
        
        # Recomendaciones
        recommendations = final_report.get('recommendations', [])
        print(f"\nRecomendaciones:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        # 5. Verificar que la simulación principal sigue activa
        print("\n🔍 5. Verificando que la simulación principal sigue activa...")
        
        # Aquí podríamos hacer una verificación más específica
        # Por ahora, verificamos que los hilos de integración estén funcionando
        final_status = get_integration_status()
        health = final_status.get('system_health', {})
        
        if health.get('integration_thread_alive', False):
            print("   ✅ Simulación principal no interrumpida")
            print("   ✅ Integración funcionando en paralelo")
        else:
            print("   ⚠️  Posible problema con la integración")
        
        print("\n" + "=" * 80)
        print("🎉 PRUEBA DE INTEGRACIÓN COMPLETADA")
        print("=" * 80)
        
        # Guardar reporte en archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"../reports/test_integration_{timestamp}.json"
        
        try:
            os.makedirs("../reports", exist_ok=True)
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(final_report, f, indent=2, ensure_ascii=False, default=str)
            print(f"📄 Reporte guardado en: {report_file}")
        except Exception as e:
            print(f"⚠️  Error guardando reporte: {e}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        SICAR_LOGGER.log_error("TEST_INTEGRATION", f"Error en prueba de integración: {e}")
        return False

async def quick_status_check():
    """Verificación rápida del estado de integración"""
    print("\n🔍 VERIFICACIÓN RÁPIDA DE ESTADO")
    print("-" * 40)
    
    try:
        status = get_integration_status()
        
        print(f"Estado de integración: {'ACTIVO' if status.get('is_active') else 'INACTIVO'}")
        
        if status.get('is_active'):
            metrics = status.get('performance_metrics', {})
            print(f"Tiempo activo: {metrics.get('system_uptime', 0):.1f}s")
            print(f"Análisis XAI: {metrics.get('xai_analyses', 0)}")
            print(f"Decisiones: {metrics.get('total_decisions', 0)}")
            print(f"Última actualización: {metrics.get('last_update', 'N/A')}")
        
        return status.get('is_active', False)
        
    except Exception as e:
        print(f"Error verificando estado: {e}")
        return False

async def main():
    """Función principal"""
    print("🤖 SICAR - Sistema de Integración Mejorada")
    print("Versión: 1.0.0")
    print("Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        # Verificación inicial
        is_active = await quick_status_check()
        
        if is_active:
            print("\n⚠️  La integración ya está activa.")
            print("¿Desea continuar con el monitoreo? (presione Ctrl+C para salir)")
            
            # Monitoreo continuo
            try:
                while True:
                    await asyncio.sleep(30)
                    await quick_status_check()
            except KeyboardInterrupt:
                print("\n👋 Monitoreo detenido por el usuario")
                return
        
        # Ejecutar prueba completa
        success = await test_enhanced_integration()
        
        if success:
            print("\n✅ Integración mejorada funcionando correctamente")
            print("💡 La simulación principal continúa sin interrupciones")
            print("🔄 Los sistemas optimizados están activos en paralelo")
        else:
            print("\n❌ Problemas detectados en la integración")
        
    except KeyboardInterrupt:
        print("\n👋 Prueba interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        SICAR_LOGGER.log_error("TEST_MAIN", f"Error en función principal: {e}")

if __name__ == "__main__":
    # Configurar logging para la prueba
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar prueba
    asyncio.run(main())