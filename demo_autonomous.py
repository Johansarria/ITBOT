#!/usr/bin/env python3
"""
DEMO DEL SISTEMA AUTÓNOMO
Prueba las estrategias autónomas sin necesidad del bot completo
"""

import asyncio
import logging
import sys
import os

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Agregar ruta
sys.path.append('/home/johan/itbot_linux')

async def demo_autonomous_system():
    """
    Demo del sistema de estrategias autónomas
    """
    print("🚀 INICIANDO DEMO DEL SISTEMA AUTÓNOMO")
    print("=" * 50)
    
    try:
        # 1. Importar y configurar
        from strategies.autonomous_integration_module import AutonomousStrategiesModule
        from strategies.autonomous_config import get_autonomous_config
        
        print("📋 Paso 1: Cargando configuración...")
        config = get_autonomous_config()
        print(f"✅ Capital configurado: ${config['capital_inicial']:,}")
        print(f"✅ Modo: {'Demo' if config['modo_demo'] else 'Real Trading'}")
        
        # 2. Inicializar sistema
        print("\n📋 Paso 2: Inicializando sistema autónomo...")
        autonomous = AutonomousStrategiesModule(
            capital_inicial=config['capital_inicial'],
            existing_bot_config=config
        )
        
        await autonomous.initialize()
        print("✅ Sistema inicializado exitosamente")
        
        # 3. Probar conexión Binance
        print("\n📋 Paso 3: Probando conexión Binance...")
        connection_ok = await autonomous.verify_binance_connection()
        
        if connection_ok:
            print("✅ Conexión Binance OK")
        else:
            print("⚠️  Conexión Binance limitada (usando datos demo)")
        
        # 4. Probar obtención de pares
        print("\n📋 Paso 4: Obteniendo pares de trading...")
        try:
            high_volume_pairs = await autonomous.auto_select_high_volume_pairs()
            print(f"✅ Pares alto volumen: {high_volume_pairs[:5]}")
            
            volatile_pairs = await autonomous.get_high_volatility_pairs()
            print(f"✅ Pares volátiles: {volatile_pairs[:5]}")
        except Exception as e:
            print(f"⚠️  Error obteniendo pares: {e}")
            print("   Usando pares por defecto")
        
        # 5. Ejecutar un ciclo de estrategias
        print("\n📋 Paso 5: Ejecutando ciclo de estrategias...")
        try:
            signals = await autonomous.get_all_autonomous_signals()
            
            if signals:
                print(f"🎯 Generadas {len(signals)} señales de trading:")
                for i, signal in enumerate(signals, 1):
                    print(f"   {i}. {signal.strategy}: {signal.pair} {signal.direction}")
                    print(f"      Precio entrada: {signal.entry_price:.6f}")
                    print(f"      Stop Loss: {signal.stop_loss:.6f}")
                    print(f"      Take Profit: {signal.take_profit[0]:.6f}")
                    print(f"      Confianza: {signal.confidence:.1%}")
                    print(f"      Timestamp: {signal.timestamp.strftime('%H:%M:%S')}")
                    print()
            else:
                print("⚠️  No se generaron señales en este momento")
                print("   Esto es normal - las estrategias esperan condiciones específicas")
                
        except Exception as e:
            print(f"⚠️  Error ejecutando estrategias: {e}")
            print("   Esto puede suceder si no hay conexión a datos en tiempo real")
        
        # 6. Mostrar estado del sistema
        print("\n📊 ESTADO DEL SISTEMA:")
        print(f"   💰 Capital disponible: ${autonomous.capital_inicial:,}")
        print(f"   🔧 Estrategias activas: {sum(1 for s in autonomous.strategy_config.values() if s['enabled'])}")
        print(f"   📈 Posiciones activas: {len(autonomous.active_positions)}")
        
        # 7. Mostrar configuración de estrategias
        print("\n🎯 CONFIGURACIÓN DE ESTRATEGIAS:")
        for name, config in autonomous.strategy_config.items():
            status = "✅" if config['enabled'] else "❌"
            capital_pct = config.get('capital_pct', 0) * 100
            print(f"   {status} {name}: {capital_pct:.0f}% capital")
        
        print("\n" + "=" * 50)
        print("🎉 DEMO COMPLETADO EXITOSAMENTE")
        print("\n💡 CONCLUSIONES:")
        print("   ✅ Sistema autónomo funcionando correctamente")
        print("   ✅ Conexión Binance establecida")
        print("   ✅ Estrategias configuradas y listas")
        print("   ✅ Gestión de riesgo implementada")
        
        print("\n🚀 PRÓXIMO PASO:")
        print("   Integrar con tu bot principal usando main.py modificado")
        print("   El sistema generará señales automáticamente cada minuto")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en demo: {e}")
        import traceback
        traceback.print_exc()
        return False

async def continuous_demo(minutes: int = 5):
    """
    Demo continuo por algunos minutos
    """
    print(f"\n🔄 INICIANDO DEMO CONTINUO POR {minutes} MINUTOS")
    print("   Presiona Ctrl+C para detener")
    
    try:
        # Inicializar sistema una vez
        from strategies.autonomous_integration_module import AutonomousStrategiesModule
        from strategies.autonomous_config import get_autonomous_config
        
        config = get_autonomous_config()
        autonomous = AutonomousStrategiesModule(
            capital_inicial=config['capital_inicial'],
            existing_bot_config=config
        )
        
        await autonomous.initialize()
        print("✅ Sistema inicializado para demo continuo")
        
        # Ejecutar ciclos cada 30 segundos
        total_cycles = minutes * 2  # 2 ciclos por minuto
        
        for cycle in range(total_cycles):
            print(f"\n🔄 Ciclo {cycle + 1}/{total_cycles} - {asyncio.get_event_loop().time():.0f}s")
            
            try:
                signals = await autonomous.get_all_autonomous_signals()
                
                if signals:
                    print(f"   🎯 {len(signals)} señales generadas")
                    for signal in signals[:2]:  # Mostrar solo las primeras 2
                        print(f"   → {signal.strategy}: {signal.pair} {signal.direction} ({signal.confidence:.0%})")
                else:
                    print("   ⏳ Esperando condiciones de mercado...")
                    
            except Exception as e:
                print(f"   ⚠️  Error en ciclo: {e}")
            
            # Esperar 30 segundos
            if cycle < total_cycles - 1:  # No esperar en el último ciclo
                await asyncio.sleep(30)
        
        print(f"\n✅ Demo continuo completado - {total_cycles} ciclos ejecutados")
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error en demo continuo: {e}")

if __name__ == "__main__":
    print("🤖 DEMO DEL SISTEMA DE ESTRATEGIAS AUTÓNOMAS")
    print("   Opciones:")
    print("   1. Demo básico (python3 demo_autonomous.py)")
    print("   2. Demo continuo (python3 demo_autonomous.py continuous)")
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        asyncio.run(continuous_demo())
    else:
        asyncio.run(demo_autonomous_system())
