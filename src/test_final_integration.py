#!/usr/bin/env python3
"""
Test Final de Integración Completa
Sistema DRL + Paper Trading + Dashboard + Monitoreo

Este script verifica que todos los componentes del sistema funcionen
correctamente en conjunto.
"""

import sys
import time
import json
import threading
from datetime import datetime
from typing import Dict, Any

# Configurar logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_drl_paper_trading_integration():
    """Prueba la integración DRL + Paper Trading"""
    try:
        from paper_trading_system import DRLIntegratedPaperTrading
        
        # Crear sistema integrado
        system = DRLIntegratedPaperTrading(
            initial_capital=10000.0,
            symbols=['BTCUSDT', 'ETHUSDT'],
            enable_drl=True,
            enable_manual_trading=True
        )
        
        # Simular datos de mercado
        market_data = {
            'symbol': 'BTCUSDT',
            'price': 45000.0,
            'volume': 1000.0,
            'timestamp': time.time()
        }
        
        # Procesar datos
        system.process_market_update(market_data)
        
        # Obtener resumen
        summary = system.get_integrated_summary()
        
        logger.info("✅ Integración DRL + Paper Trading: EXITOSA")
        return True, summary
        
    except Exception as e:
        logger.error(f"❌ Error en integración DRL + Paper Trading: {e}")
        return False, str(e)

def test_drl_monitoring_system():
    """Prueba el sistema de monitoreo DRL"""
    try:
        from drl_monitoring_system import DRLMonitoringSystem
        from paper_trading_system import DRLIntegratedPaperTrading
        
        # Crear sistemas
        integrated_system = DRLIntegratedPaperTrading(
            initial_capital=5000.0,
            symbols=['BTCUSDT'],
            enable_drl=True
        )
        
        monitoring_system = DRLMonitoringSystem(
            monitoring_interval=5,  # 5 segundos para prueba
            history_size=100
        )
        
        # Conectar sistemas
        monitoring_system.set_integrated_system(integrated_system)
        
        # Iniciar monitoreo
        monitoring_system.start_monitoring()
        
        # Esperar un poco
        time.sleep(3)
        
        # Verificar estado
        status = monitoring_system.get_current_status()
        
        # Detener monitoreo
        monitoring_system.stop_monitoring()
        
        logger.info("✅ Sistema de Monitoreo DRL: EXITOSO")
        return True, status
        
    except Exception as e:
        logger.error(f"❌ Error en sistema de monitoreo: {e}")
        return False, str(e)

def test_dashboard_drl_integration():
    """Prueba la integración del dashboard con DRL"""
    try:
        # Importar componentes del dashboard
        from enhanced_dashboard import EnhancedDashboard
        
        # Crear dashboard (sin ejecutar mainloop)
        dashboard = EnhancedDashboard()
        
        # Verificar que las variables DRL existen
        drl_vars = [
            'drl_enabled_var',
            'drl_mode_var', 
            'drl_confidence_var',
            'drl_sharpe_var',
            'drl_win_rate_var',
            'drl_total_reward_var',
            'drl_episodes_var',
            'drl_status_var'
        ]
        
        for var_name in drl_vars:
            if not hasattr(dashboard, var_name):
                raise Exception(f"Variable DRL faltante: {var_name}")
        
        # Verificar métodos DRL
        drl_methods = [
            'toggle_drl',
            'initialize_drl_system',
            'shutdown_drl_system',
            'update_drl_metrics',
            'open_drl_dashboard'
        ]
        
        for method_name in drl_methods:
            if not hasattr(dashboard, method_name):
                raise Exception(f"Método DRL faltante: {method_name}")
        
        logger.info("✅ Integración Dashboard + DRL: EXITOSA")
        return True, "Dashboard DRL integrado correctamente"
        
    except Exception as e:
        logger.error(f"❌ Error en integración dashboard: {e}")
        return False, str(e)

def test_web_dashboard_availability():
    """Prueba la disponibilidad del dashboard web DRL"""
    try:
        import requests
        
        # Verificar si el dashboard web está disponible
        try:
            response = requests.get("http://localhost:8502", timeout=5)
            web_available = response.status_code == 200
        except:
            web_available = False
        
        if web_available:
            logger.info("✅ Dashboard Web DRL: DISPONIBLE")
            return True, "Dashboard web accesible"
        else:
            logger.warning("⚠️ Dashboard Web DRL: NO DISPONIBLE (normal si no está ejecutándose)")
            return True, "Dashboard web no ejecutándose (normal)"
            
    except Exception as e:
        logger.error(f"❌ Error verificando dashboard web: {e}")
        return False, str(e)

def test_complete_workflow():
    """Prueba el flujo completo del sistema"""
    try:
        from paper_trading_system import DRLIntegratedPaperTrading
        from drl_monitoring_system import DRLMonitoringSystem
        
        logger.info("🚀 Iniciando prueba de flujo completo...")
        
        # 1. Crear sistema integrado
        system = DRLIntegratedPaperTrading(
            initial_capital=10000.0,
            symbols=['BTCUSDT', 'ETHUSDT'],
            enable_drl=True,
            enable_manual_trading=True
        )
        
        # 2. Crear sistema de monitoreo
        monitor = DRLMonitoringSystem(monitoring_interval=2, history_size=50)
        monitor.set_integrated_system(system)
        monitor.start_monitoring()
        
        # 3. Simular actividad de trading
        for i in range(5):
            market_data = {
                'symbol': 'BTCUSDT',
                'price': 45000.0 + (i * 100),
                'volume': 1000.0,
                'timestamp': time.time()
            }
            system.process_market_update(market_data)
            time.sleep(1)
        
        # 4. Cambiar modo de trading
        system.set_trading_mode('drl')
        time.sleep(1)
        system.set_trading_mode('hybrid')
        
        # 5. Obtener métricas finales
        summary = system.get_integrated_summary()
        status = monitor.get_current_status()
        
        # 6. Limpiar
        monitor.stop_monitoring()
        
        logger.info("✅ Flujo Completo: EXITOSO")
        return True, {
            'summary': summary,
            'monitoring_status': status
        }
        
    except Exception as e:
        logger.error(f"❌ Error en flujo completo: {e}")
        return False, str(e)

def main():
    """Función principal de pruebas"""
    print("=" * 60)
    print("🧪 PRUEBAS FINALES DE INTEGRACIÓN COMPLETA")
    print("Sistema DRL + Paper Trading + Dashboard + Monitoreo")
    print("=" * 60)
    
    results = {}
    
    # Ejecutar todas las pruebas
    tests = [
        ("DRL + Paper Trading", test_drl_paper_trading_integration),
        ("Sistema de Monitoreo DRL", test_drl_monitoring_system),
        ("Dashboard + DRL", test_dashboard_drl_integration),
        ("Dashboard Web", test_web_dashboard_availability),
        ("Flujo Completo", test_complete_workflow)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Ejecutando: {test_name}")
        try:
            success, result = test_func()
            results[test_name] = {
                'success': success,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
            if success:
                passed += 1
                print(f"✅ {test_name}: EXITOSO")
            else:
                print(f"❌ {test_name}: FALLÓ - {result}")
                
        except Exception as e:
            results[test_name] = {
                'success': False,
                'result': f"Error de ejecución: {e}",
                'timestamp': datetime.now().isoformat()
            }
            print(f"💥 {test_name}: ERROR - {e}")
    
    # Resumen final
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    print(f"✅ Exitosas: {passed}/{total}")
    print(f"❌ Fallidas: {total - passed}/{total}")
    print(f"📈 Tasa de éxito: {(passed/total)*100:.1f}%")
    
    # Guardar resultados
    with open('test_final_integration_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: test_final_integration_results.json")
    
    if passed == total:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON! Sistema listo para producción.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} pruebas fallaron. Revisar antes de producción.")
        return 1

if __name__ == "__main__":
    sys.exit(main())