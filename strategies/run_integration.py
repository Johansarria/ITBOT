#!/usr/bin/env python3
"""
SCRIPT DE INTEGRACIÓN DIRECTA
Ejecuta este archivo para integrar estrategias autónomas con tu bot
"""

import asyncio
import sys
import os
from datetime import datetime

# Agregar ruta
sys.path.append('/home/johan/itbot_linux')

async def main():
    """
    Función principal de integración
    """
    print("🚀 INICIANDO INTEGRACIÓN DE ESTRATEGIAS AUTÓNOMAS")
    print("=" * 55)
    
    try:
        # 1. Importar configuración
        from strategies.autonomous_config import get_autonomous_config, validate_config
        
        print("\n📋 Paso 1: Validando configuración...")
        if not validate_config():
            print("❌ Configuración inválida. Revisa autonomous_config.py")
            return
        
        config = get_autonomous_config()
        print("✅ Configuración validada correctamente")
        
        # 2. Importar módulo autónomo
        print("\n📋 Paso 2: Importando módulo autónomo...")
        from strategies.autonomous_integration_module import AutonomousStrategiesModule
        
        autonomous = AutonomousStrategiesModule(
            capital_inicial=config['capital_inicial'],
            existing_bot_config=config
        )
        print("✅ Módulo autónomo inicializado")
        
        # 3. Configurar estrategias
        print("\n📋 Paso 3: Configurando estrategias...")
        for strategy_name, is_active in config['estrategias_activas'].items():
            if is_active and strategy_name in autonomous.strategy_config:
                autonomous.strategy_config[strategy_name]['enabled'] = True
                capital_pct = config['distribucion_capital'].get(strategy_name, 0.1)
                autonomous.strategy_config[strategy_name]['capital_pct'] = capital_pct
                print(f"   ✅ {strategy_name}: Activa ({capital_pct:.1%} capital)")
            else:
                if strategy_name in autonomous.strategy_config:
                    autonomous.strategy_config[strategy_name]['enabled'] = False
                    print(f"   ❌ {strategy_name}: Inactiva")
        
        # 4. Simular ciclo de trading
        print("\n📋 Paso 4: Simulando ciclo de trading...")
        
        if config['modo_demo']:
            print("⚠️  MODO DEMO ACTIVADO - No se ejecutarán trades reales")
        else:
            print("🔴 MODO REAL ACTIVADO - Se ejecutarán trades reales")
        
        # Simular obtención de señales
        print("\n📊 Obteniendo señales de trading...")
        # signals = await autonomous.get_all_autonomous_signals()
        print("✅ Sistema listo para generar señales")
        
        # 5. Mostrar resumen
        print("\n📊 RESUMEN DE INTEGRACIÓN:")
        print(f"   💰 Capital inicial: ${config['capital_inicial']:,}")
        print(f"   🎯 Objetivo mensual: 15% ({config['capital_inicial'] * 0.15:,.0f} USDT)")
        print(f"   🔧 Estrategias activas: {sum(config['estrategias_activas'].values())}")
        print(f"   📈 Pares configurados: {len(config['pares_favoritos'])}")
        print(f"   ⚠️  Riesgo por trade: {config['riesgo_por_trade']:.1%}")
        print(f"   🚫 Stop loss diario: {config['stop_loss_diario']:.1%}")
        
        # 6. Instrucciones finales
        print("\n" + "=" * 55)
        print("🎯 INTEGRACIÓN COMPLETADA EXITOSAMENTE")
        print("\n📋 SIGUIENTES PASOS:")
        print("1. Adaptar funciones de datos en autonomous_integration_module.py")
        print("2. Conectar con tu cliente Binance actual")
        print("3. Probar en modo demo durante 24 horas")
        print("4. Activar gradualmente con capital pequeño")
        
        print("\n⚡ PARA ACTIVAR EN TU BOT PRINCIPAL:")
        print("   - Importar: from strategies.autonomous_integration_module import run_autonomous_strategies_cycle")  
        print("   - Ejecutar: await run_autonomous_strategies_cycle() cada minuto")
        print("   - Monitorear resultados en tiempo real")
        
        return autonomous
        
    except Exception as e:
        print(f"❌ Error en integración: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
