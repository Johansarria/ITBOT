#!/usr/bin/env python3
"""
Prueba de integración completa entre MCPs y Dashboard
"""

import asyncio
import json
import time
from datetime import datetime
from mcp_framework.mcp_manager import MCPManager
from mcps.paper_trading_mcp import PaperTradingMCP
from mcps.breakout_detector_mcp import BreakoutDetectorMCP

async def test_mcp_dashboard_integration():
    """Prueba la integración completa entre MCPs y el dashboard"""
    
    print("🧪 Iniciando prueba de integración MCP-Dashboard...")
    
    # Crear manager de MCPs
    manager = MCPManager()
    
    try:
        # 1. Registrar MCPs
        print("\n📝 Registrando MCPs...")
        
        # Registrar Paper Trading MCP
        paper_trading_success = manager.register_mcp(PaperTradingMCP, name="paper_trading")
        print(f"   Paper Trading MCP: {'✅' if paper_trading_success else '❌'}")
        
        # Registrar Breakout Detector MCP
        breakout_success = manager.register_mcp(BreakoutDetectorMCP, name="breakout_detector")
        print(f"   Breakout Detector MCP: {'✅' if breakout_success else '❌'}")
        
        print(f"   MCPs registrados: {list(manager.mcps.keys())}")
        
        # 2. Iniciar MCPs
        print("\n🔄 Iniciando MCPs...")
        start_results = await manager.start_all()
        
        for mcp_name, success in start_results.items():
            print(f"   {mcp_name}: {'✅' if success else '❌'}")
        
        # Esperar un momento para que se inicialicen
        await asyncio.sleep(2)
        
        # 3. Verificar estado de salud
        print("\n📊 Verificando estado de salud...")
        health_report = await manager.get_health_report()
        print(f"   MCPs saludables: {health_report['healthy_mcps']}/{health_report['total_mcps']}")
        print(f"   Estado del manager: {health_report['manager_status']}")
        
        # 4. Probar Paper Trading MCP
        print("\n💰 Probando Paper Trading MCP...")
        
        # Inicializar engine
        init_response = await manager.send_request(
            "paper_trading", 
            "initialize_engine", 
            {"initial_capital": 10000, "commission_rate": 0.001}
        )
        print(f"   Inicialización: {'✅' if init_response is not None else '❌'}")
        
        # Obtener estado del engine
        status_response = await manager.send_request(
            "paper_trading", 
            "get_engine_status", 
            {}
        )
        print(f"   Estado del engine: {'✅' if status_response is not None else '❌'}")
        if status_response:
            print(f"      Activo: {status_response.get('is_active', False)}")
            print(f"      Inicializado: {status_response.get('engine_initialized', False)}")
        
        # Colocar una orden de prueba
        order_response = await manager.send_request(
            "paper_trading",
            "place_order",
            {
                "symbol": "BTCUSDT",
                "side": "buy",
                "order_type": "market",
                "quantity": 0.001
            }
        )
        print(f"   Orden de prueba: {'✅' if order_response is not None else '❌'}")
        if order_response:
            print(f"      Order ID: {order_response.get('order_id', 'N/A')}")
            print(f"      Estado: {order_response.get('status', 'N/A')}")
        
        # 5. Probar Breakout Detector MCP
        print("\n📈 Probando Breakout Detector MCP...")
        
        # Obtener estado
        bd_status_response = await manager.send_request(
            "breakout_detector",
            "get_detector_status",
            {}
        )
        print(f"   Estado: {'✅' if bd_status_response is not None else '❌'}")
        
        # Obtener señales recientes
        signals_response = await manager.send_request(
            "breakout_detector",
            "get_signal_history",
            {"limit": 5}
        )
        print(f"   Señales recientes: {'✅' if signals_response is not None else '❌'}")
        
        # Procesar datos de mercado de prueba
        market_data_response = await manager.send_request(
            "breakout_detector",
            "update_price_data",
            {
                "symbol": "BTCUSDT",
                "price": 45000.0,
                "volume": 1000.0,
                "timestamp": datetime.now().isoformat()
            }
        )
        print(f"   Procesamiento de datos: {'✅' if market_data_response is not None else '❌'}")
        
        # 6. Probar comunicación entre MCPs
        print("\n🔄 Probando comunicación entre MCPs...")
        
        # Simular datos de mercado para el detector
        market_data = {
            "symbol": "BTCUSDT",
            "price": 45000.0,
            "volume": 1000.0,
            "timestamp": datetime.now().isoformat()
        }
        
        detector_update = await manager.send_request(
            "breakout_detector",
            "update_price_data",
            {
                "symbol": market_data["symbol"],
                "price": market_data["price"],
                "volume": market_data["volume"],
                "timestamp": market_data["timestamp"]
            }
        )
        print(f"   Actualización de datos: {'✅' if detector_update is not None else '❌'}")
        
        # 7. Verificar métricas de rendimiento
        print("\n⚡ Verificando métricas de rendimiento...")
        
        start_time = time.time()
        
        # Enviar múltiples solicitudes para medir rendimiento
        tasks = []
        for i in range(10):
            task = manager.send_request(
                "paper_trading",
                "get_engine_status",
                {}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful_responses = sum(1 for r in responses if not isinstance(r, Exception) and r is not None)
        total_time = end_time - start_time
        
        print(f"   Solicitudes exitosas: {successful_responses}/10")
        print(f"   Tiempo total: {total_time:.3f}s")
        print(f"   Solicitudes por segundo: {10/total_time:.1f}")
        
        # 8. Reporte final
        print("\n📋 Reporte final de integración...")
        final_health = await manager.get_health_report()
        
        print(f"   ✅ MCPs registrados: {final_health['total_mcps']}")
        print(f"   ✅ MCPs saludables: {final_health['healthy_mcps']}")
        print(f"   ✅ Solicitudes totales: {final_health['statistics']['total_requests']}")
        print(f"   ✅ Solicitudes exitosas: {final_health['statistics']['successful_requests']}")
        print(f"   ✅ Tiempo de actividad: {final_health['uptime_seconds']:.1f}s")
        
        # Verificar si la integración fue exitosa
        integration_success = (
            final_health['healthy_mcps'] >= 2 and
            final_health['statistics']['successful_requests'] > 0 and
            successful_responses >= 8  # Al menos 80% de éxito
        )
        
        print(f"\n🎯 Integración MCP-Dashboard: {'✅ EXITOSA' if integration_success else '❌ FALLIDA'}")
        
        return integration_success
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba de integración: {e}")
        return False
        
    finally:
        # Limpiar recursos
        print("\n🛑 Deteniendo MCPs...")
        await manager.stop_all()

if __name__ == "__main__":
    success = asyncio.run(test_mcp_dashboard_integration())
    exit(0 if success else 1)