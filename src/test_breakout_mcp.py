"""
Test del Breakout Detector MCP
Prueba de funcionamiento del detector de breakouts como MCP independiente
"""

import asyncio
import json
import time
from datetime import datetime
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_framework import MCPManager
from mcps.breakout_detector_mcp import BreakoutDetectorMCP

async def test_breakout_detector_mcp():
    """Prueba completa del BreakoutDetectorMCP"""
    print("🚀 Iniciando prueba del Breakout Detector MCP...")
    
    # Crear manager de MCPs
    manager = MCPManager()
    
    try:
        # Registrar el MCP del detector de breakouts
        print("\n📝 Registrando BreakoutDetectorMCP...")
        success = manager.register_mcp(BreakoutDetectorMCP, port=8766)
        
        if not success:
            print("❌ Error registrando BreakoutDetectorMCP")
            return
        
        print("✅ BreakoutDetectorMCP registrado exitosamente")
        
        # Iniciar todos los MCPs
        print("\n🔄 Iniciando MCPs...")
        results = await manager.start_all()
        
        if not results.get("breakout_detector", False):
            print("❌ Error iniciando BreakoutDetectorMCP")
            return
        
        print("✅ BreakoutDetectorMCP iniciado exitosamente")
        
        # Esperar un momento para que se establezcan las conexiones
        await asyncio.sleep(2)
        
        # Probar funcionalidades del MCP
        await test_mcp_functionality(manager)
        
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        
    finally:
        # Detener todos los MCPs
        print("\n🛑 Deteniendo MCPs...")
        await manager.stop_all()
        print("✅ MCPs detenidos")

async def test_mcp_functionality(manager: MCPManager):
    """Probar funcionalidades específicas del MCP"""
    print("\n🧪 Probando funcionalidades del MCP...")
    
    # 1. Obtener estado inicial
    print("\n1️⃣ Obteniendo estado inicial...")
    status = await manager.send_request("breakout_detector", "get_detector_status")
    if status:
        print(f"   Estado: {json.dumps(status, indent=2)}")
    else:
        print("   ❌ Error obteniendo estado")
    
    # 2. Iniciar detección
    print("\n2️⃣ Iniciando detección de breakouts...")
    start_result = await manager.send_request("breakout_detector", "start_detection")
    if start_result and start_result.get("success"):
        print("   ✅ Detección iniciada exitosamente")
    else:
        print(f"   ❌ Error iniciando detección: {start_result}")
    
    # 3. Simular datos de precio
    print("\n3️⃣ Simulando datos de precio...")
    await simulate_price_data(manager)
    
    # 4. Obtener señales
    print("\n4️⃣ Obteniendo señales generadas...")
    await asyncio.sleep(2)  # Esperar a que se procesen los datos
    
    signals = await manager.send_request("breakout_detector", "get_signals")
    if signals and signals.get("success"):
        print(f"   Señales encontradas: {signals.get('count', 0)}")
        if signals.get('signals'):
            for signal in signals['signals'][-3:]:  # Mostrar últimas 3
                print(f"   📊 {signal.get('symbol')} - {signal.get('breakout_type')} "
                      f"(Confianza: {signal.get('confidence', 0):.1f}%)")
    else:
        print("   ℹ️ No se encontraron señales")
    
    # 5. Obtener estadísticas
    print("\n5️⃣ Obteniendo estadísticas...")
    stats = await manager.send_request("breakout_detector", "get_stats")
    if stats and stats.get("success"):
        statistics = stats.get("statistics", {})
        print(f"   📈 Señales generadas: {statistics.get('signals_generated', 0)}")
        print(f"   📈 Señales alcistas: {statistics.get('bullish_signals', 0)}")
        print(f"   📈 Señales bajistas: {statistics.get('bearish_signals', 0)}")
        print(f"   📈 Señales fuertes: {statistics.get('strong_signals', 0)}")
        print(f"   ⏱️ Tiempo activo: {statistics.get('uptime_seconds', 0):.1f}s")
    
    # 6. Probar detección forzada
    print("\n6️⃣ Probando detección forzada...")
    force_result = await manager.send_request("breakout_detector", "force_detection", {
        "symbols": ["BTCUSDT", "ETHUSDT"]
    })
    if force_result and force_result.get("success"):
        print("   ✅ Detección forzada completada")
        results = force_result.get("results", {})
        for symbol, result in results.items():
            if result.get("signal_generated"):
                print(f"   🎯 {symbol}: Señal generada")
            else:
                print(f"   ⚪ {symbol}: Sin señal")
    
    # 7. Actualizar sensibilidad
    print("\n7️⃣ Actualizando sensibilidad...")
    sensitivity_result = await manager.send_request("breakout_detector", "update_sensitivity", {
        "sensitivity": 0.7
    })
    if sensitivity_result and sensitivity_result.get("success"):
        print(f"   ✅ Sensibilidad actualizada: {sensitivity_result.get('new_sensitivity')}")
    
    # 8. Obtener historial
    print("\n8️⃣ Obteniendo historial de señales...")
    history = await manager.send_request("breakout_detector", "get_signal_history", {
        "limit": 5
    })
    if history and history.get("success"):
        print(f"   📚 Historial: {history.get('count', 0)} señales recientes")
    
    # 9. Detener detección
    print("\n9️⃣ Deteniendo detección...")
    stop_result = await manager.send_request("breakout_detector", "stop_detection")
    if stop_result and stop_result.get("success"):
        print("   ✅ Detección detenida exitosamente")

async def simulate_price_data(manager: MCPManager):
    """Simular datos de precio para generar señales"""
    symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
    
    for symbol in symbols:
        # Generar datos de precio simulados
        base_price = 50000 if symbol == "BTCUSDT" else 3000 if symbol == "ETHUSDT" else 1.5
        
        price_data = []
        for i in range(20):
            # Simular movimiento de precio con breakout
            if i < 15:
                # Precio estable
                price = base_price + (i * 0.001 * base_price)
            else:
                # Breakout simulado
                price = base_price * (1.02 if i % 2 == 0 else 0.98)
            
            price_data.append({
                "timestamp": datetime.now().isoformat(),
                "open": price * 0.999,
                "high": price * 1.001,
                "low": price * 0.998,
                "close": price,
                "volume": 1000000 * (2 if i >= 15 else 1)  # Mayor volumen en breakout
            })
        
        # Enviar datos al MCP
        result = await manager.send_request("breakout_detector", "update_price_data", {
            "symbol": symbol,
            "price_data": price_data
        })
        
        if result and result.get("success"):
            print(f"   ✅ Datos enviados para {symbol}: {len(price_data)} puntos")
        else:
            print(f"   ❌ Error enviando datos para {symbol}")
        
        # Pequeña pausa entre símbolos
        await asyncio.sleep(0.1)

async def test_health_monitoring():
    """Probar monitoreo de salud del MCP"""
    print("\n🏥 Probando monitoreo de salud...")
    
    manager = MCPManager()
    
    try:
        # Registrar e iniciar MCP
        manager.register_mcp(BreakoutDetectorMCP, port=8767)
        await manager.start_all()
        
        # Obtener reporte de salud
        health_report = await manager.get_health_report()
        print(f"📊 Reporte de salud: {json.dumps(health_report, indent=2)}")
        
        # Probar ping
        statuses = await manager.get_all_statuses()
        print(f"🏓 Estados de MCPs: {json.dumps(statuses, indent=2)}")
        
    finally:
        await manager.stop_all()

if __name__ == "__main__":
    print("🧪 Iniciando pruebas del Breakout Detector MCP")
    print("=" * 60)
    
    # Ejecutar prueba principal
    asyncio.run(test_breakout_detector_mcp())
    
    print("\n" + "=" * 60)
    print("🏁 Pruebas completadas")