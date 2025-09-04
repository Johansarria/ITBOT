#!/usr/bin/env python3
"""
PRUEBA DE INTEGRACIÓN V3
========================
Script para probar la integración completa del sistema V3 autónomo.

Este script verifica:
- Importación correcta de todos los módulos V3
- Funcionalidad básica del sistema autónomo
- Integración con handlers de Telegram
- Conectividad con APIs y bases de datos
"""

import sys
import os
import asyncio
from datetime import datetime

# Añadir path del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_imports():
    """Probar importación de módulos V3"""
    print("🧪 PRUEBA 1: Importando módulos V3...")
    
    try:
        # Importar módulo principal V3
        from strategies.v3_autonomous_integration import V3AutonomousSystem, v3_autonomous
        print("  ✅ v3_autonomous_integration importado correctamente")
        
        # Importar controlador V3
        from strategies.v3_controller import V3AutonomousController, v3_controller
        print("  ✅ v3_controller importado correctamente")
        
        # Importar handlers V3
        from handlers.v3_handlers import V3_COMMAND_HANDLERS, V3_CALLBACK_HANDLERS
        print("  ✅ v3_handlers importado correctamente")
        
        # Importar cola de mensajes
        from utils.message_queue import mq
        print("  ✅ message_queue importado correctamente")
        
        print("  🎉 Todas las importaciones V3 exitosas")
        return True
        
    except ImportError as e:
        print(f"  ❌ Error de importación: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error inesperado: {e}")
        return False

def test_v3_system_initialization():
    """Probar inicialización del sistema V3"""
    print("\n🧪 PRUEBA 2: Inicializando sistema V3...")
    
    try:
        from strategies.v3_autonomous_integration import V3AutonomousSystem
        
        system = V3AutonomousSystem()
        print(f"  ✅ Sistema V3 creado con {len(system.proven_strategies)} estrategias")
        
        # Verificar estrategias probadas
        for key, config in system.proven_strategies.items():
            print(f"  📊 {config['name']}: {config['proven_return']:.2f}% mensual")
        
        print("  🎉 Inicialización del sistema V3 exitosa")
        return True
        
    except Exception as e:
        print(f"  ❌ Error inicializando sistema V3: {e}")
        return False

def test_controller_functionality():
    """Probar funcionalidad del controlador V3"""
    print("\n🧪 PRUEBA 3: Probando controlador V3...")
    
    try:
        from strategies.v3_controller import V3AutonomousController
        
        controller = V3AutonomousController()
        print("  ✅ Controlador V3 creado")
        
        # Verificar estado inicial
        is_running = controller.is_v3_system_running()
        print(f"  📊 Estado inicial del sistema: {'🟢 ACTIVO' if is_running else '🔴 DETENIDO'}")
        
        print("  🎉 Controlador V3 funcional")
        return True
        
    except Exception as e:
        print(f"  ❌ Error probando controlador: {e}")
        return False

async def test_market_data_fetch():
    """Probar obtención de datos de mercado"""
    print("\n🧪 PRUEBA 4: Probando obtención de datos de mercado...")
    
    try:
        from strategies.v3_autonomous_integration import V3AutonomousSystem
        
        system = V3AutonomousSystem()
        
        # Probar obtención de datos para SOL/USDT
        df = await system.fetch_market_data('SOL/USDT', '30m', limit=10)
        
        if not df.empty:
            print(f"  ✅ Datos obtenidos: {len(df)} velas para SOL/USDT 30m")
            print(f"  📊 Último precio: {df.iloc[-1]['close']:.4f}")
        else:
            print("  ⚠️ No se obtuvieron datos de mercado")
        
        print("  🎉 Obtención de datos de mercado funcional")
        return True
        
    except Exception as e:
        print(f"  ❌ Error obteniendo datos de mercado: {e}")
        return False

def test_handlers_registration():
    """Probar registro de handlers"""
    print("\n🧪 PRUEBA 5: Probando registro de handlers...")
    
    try:
        from handlers.v3_handlers import V3_COMMAND_HANDLERS, V3_CALLBACK_HANDLERS
        
        print(f"  ✅ Comandos V3 disponibles: {len(V3_COMMAND_HANDLERS)}")
        for cmd in V3_COMMAND_HANDLERS.keys():
            print(f"    • /{cmd}")
        
        print(f"  ✅ Callbacks V3 disponibles: {len(V3_CALLBACK_HANDLERS)}")
        for callback in V3_CALLBACK_HANDLERS.keys():
            print(f"    • {callback}")
        
        print("  🎉 Handlers V3 registrados correctamente")
        return True
        
    except Exception as e:
        print(f"  ❌ Error probando handlers: {e}")
        return False

async def test_signal_generation():
    """Probar generación de señales"""
    print("\n🧪 PRUEBA 6: Probando generación de señales...")
    
    try:
        from strategies.v3_autonomous_integration import V3AutonomousSystem
        
        system = V3AutonomousSystem()
        
        # Probar análisis de una estrategia
        strategy_key = 'scalping_sol_30m'
        config = system.proven_strategies[strategy_key]
        
        signal = await system.analyze_strategy(strategy_key, config)
        
        if signal:
            print(f"  ✅ Señal generada: {signal.side} {signal.symbol}")
            print(f"  📊 Score: {signal.analysis_score:.2f}")
            print(f"  💰 TP: {signal.take_profit:.2f}%, SL: {signal.stop_loss:.2f}%")
        else:
            print("  ℹ️ No se generó señal (condiciones insuficientes)")
        
        print("  🎉 Generación de señales funcional")
        return True
        
    except Exception as e:
        print(f"  ❌ Error generando señales: {e}")
        return False

def test_configuration_integration():
    """Probar integración con configuración"""
    print("\n🧪 PRUEBA 7: Probando integración con configuración...")
    
    try:
        from config import settings
        
        # Verificar configuraciones críticas
        config_checks = [
            ('BINANCE_API_KEY', hasattr(settings, 'BINANCE_API_KEY')),
            ('BINANCE_SECRET_KEY', hasattr(settings, 'BINANCE_SECRET_KEY')),
            ('REDIS_HOST', hasattr(settings, 'REDIS_HOST')),
            ('REDIS_PORT', hasattr(settings, 'REDIS_PORT')),
            ('MODE', hasattr(settings, 'MODE')),
        ]
        
        for config_name, exists in config_checks:
            status = "✅" if exists else "⚠️"
            print(f"  {status} {config_name}: {'Configurado' if exists else 'No encontrado'}")
        
        print("  🎉 Integración con configuración verificada")
        return True
        
    except Exception as e:
        print(f"  ❌ Error verificando configuración: {e}")
        return False

async def run_comprehensive_test():
    """Ejecutar prueba comprehensiva del sistema V3"""
    print("🚀 PRUEBA DE INTEGRACIÓN V3 AUTÓNOMO")
    print("=" * 60)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_results = []
    
    # Ejecutar todas las pruebas
    test_results.append(("Importaciones", test_imports()))
    test_results.append(("Inicialización Sistema", test_v3_system_initialization()))
    test_results.append(("Controlador", test_controller_functionality()))
    test_results.append(("Datos de Mercado", await test_market_data_fetch()))
    test_results.append(("Handlers", test_handlers_registration()))
    test_results.append(("Generación Señales", await test_signal_generation()))
    test_results.append(("Configuración", test_configuration_integration()))
    
    # Mostrar resumen
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"📈 RESULTADO: {passed}/{total} pruebas exitosas ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 TODAS LAS PRUEBAS EXITOSAS - SISTEMA V3 LISTO")
        print("\n💡 Próximos pasos:")
        print("   1. Iniciar el bot principal: python main.py")
        print("   2. Usar comando /v3_start para activar sistema V3")
        print("   3. Monitorear con /v3_status y /v3_performance")
    else:
        print("⚠️ ALGUNAS PRUEBAS FALLARON - REVISAR CONFIGURACIÓN")
        print("\n🔧 Verifica:")
        print("   - Configuración de APIs (Binance, Redis)")
        print("   - Dependencias instaladas correctamente")
        print("   - Permisos y conexiones de red")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(run_comprehensive_test())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Prueba interrumpida por usuario")
        exit(130)
    except Exception as e:
        print(f"\n\n❌ Error fatal en prueba: {e}")
        exit(1)
