"""
Test del Paper Trading MCP
Prueba completa del sistema de paper trading como MCP independiente
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
from mcps.paper_trading_mcp import PaperTradingMCP

async def test_paper_trading_mcp():
    """Prueba completa del PaperTradingMCP"""
    print("🎯 Iniciando prueba del Paper Trading MCP...")
    
    # Crear manager de MCPs
    manager = MCPManager()
    
    try:
        # Registrar el MCP del paper trading
        print("\n📝 Registrando PaperTradingMCP...")
        success = manager.register_mcp(PaperTradingMCP, port=8767)
        
        if not success:
            print("❌ Error registrando PaperTradingMCP")
            return
        
        print("✅ PaperTradingMCP registrado exitosamente")
        
        # Iniciar todos los MCPs
        print("\n🔄 Iniciando MCPs...")
        results = await manager.start_all()
        
        if not results.get("paper_trading", False):
            print("❌ Error iniciando PaperTradingMCP")
            return
        
        print("✅ PaperTradingMCP iniciado exitosamente")
        
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
    """Probar funcionalidades específicas del Paper Trading MCP"""
    print("\n🧪 Probando funcionalidades del Paper Trading MCP...")
    
    # 1. Inicializar el motor
    print("\n1️⃣ Inicializando motor de paper trading...")
    init_result = await manager.send_request("paper_trading", "initialize_engine", {
        "initial_capital": 10000.0,
        "commission_rate": 0.001
    })
    
    if init_result and init_result.get("success"):
        print(f"   ✅ Motor inicializado con ${init_result.get('initial_capital'):,.2f}")
    else:
        print(f"   ❌ Error inicializando motor: {init_result}")
        return
    
    # 2. Obtener estado inicial
    print("\n2️⃣ Obteniendo estado inicial...")
    status = await manager.send_request("paper_trading", "get_engine_status")
    if status and status.get("success"):
        portfolio = status.get("portfolio_summary", {})
        print(f"   💰 Capital actual: ${portfolio.get('current_capital', 0):,.2f}")
        print(f"   📊 Posiciones abiertas: {status.get('open_positions', 0)}")
        print(f"   📋 Órdenes pendientes: {status.get('pending_orders', 0)}")
    
    # 3. Colocar órdenes de prueba
    print("\n3️⃣ Colocando órdenes de prueba...")
    await test_order_placement(manager)
    
    # 4. Simular datos de mercado
    print("\n4️⃣ Simulando datos de mercado...")
    await simulate_market_data(manager)
    
    # 5. Obtener posiciones
    print("\n5️⃣ Obteniendo posiciones...")
    positions = await manager.send_request("paper_trading", "get_positions")
    if positions and positions.get("success"):
        pos_list = positions.get("positions", [])
        print(f"   📊 Posiciones encontradas: {len(pos_list)}")
        for pos in pos_list[:3]:  # Mostrar primeras 3
            print(f"   📈 {pos.get('symbol')} - {pos.get('side')} "
                  f"${pos.get('unrealized_pnl', 0):.2f} PnL")
    
    # 6. Probar operaciones de scalping
    print("\n6️⃣ Probando operaciones de scalping...")
    await test_scalping_operations(manager)
    
    # 7. Obtener resumen del portfolio
    print("\n7️⃣ Obteniendo resumen del portfolio...")
    summary = await manager.send_request("paper_trading", "get_portfolio_summary")
    if summary and summary.get("success"):
        portfolio = summary.get("portfolio_summary", {})
        print(f"   💰 Capital total: ${portfolio.get('total_portfolio_value', 0):,.2f}")
        print(f"   📈 PnL total: ${portfolio.get('total_pnl', 0):,.2f}")
        print(f"   📊 Retorno: {portfolio.get('total_return_pct', 0):.2f}%")
        print(f"   🎯 Win rate: {portfolio.get('win_rate', 0):.1%}")
        print(f"   📉 Max drawdown: {portfolio.get('max_drawdown', 0):.2f}%")
    
    # 8. Obtener historial de trades
    print("\n8️⃣ Obteniendo historial de trades...")
    history = await manager.send_request("paper_trading", "get_trade_history", {
        "limit": 5
    })
    if history and history.get("success"):
        trades = history.get("trade_history", [])
        print(f"   📚 Trades recientes: {len(trades)}")
        for trade in trades[-3:]:  # Últimos 3
            print(f"   💼 {trade.get('symbol')} - {trade.get('side')} "
                  f"${trade.get('value', 0):.2f}")
    
    # 9. Obtener estadísticas de scalping
    print("\n9️⃣ Obteniendo estadísticas de scalping...")
    scalp_stats = await manager.send_request("paper_trading", "get_scalping_stats")
    if scalp_stats and scalp_stats.get("success"):
        stats = scalp_stats.get("scalping_statistics", {})
        print(f"   🚀 Sesiones de scalping: {stats.get('total_scalping_sessions', 0)}")
        print(f"   💰 PnL de scalping: ${stats.get('scalping_pnl', 0):.2f}")
        print(f"   🎯 Win rate scalping: {stats.get('scalping_win_rate', 0):.1f}%")

async def test_order_placement(manager: MCPManager):
    """Probar colocación de órdenes"""
    orders_to_place = [
        {
            "symbol": "BTCUSDT",
            "side": "buy",
            "order_type": "market",
            "quantity": 0.001,
            "price": 50000.0
        },
        {
            "symbol": "ETHUSDT",
            "side": "buy",
            "order_type": "market",
            "quantity": 0.01,
            "price": 3000.0
        },
        {
            "symbol": "ADAUSDT",
            "side": "buy",
            "order_type": "limit",
            "quantity": 100.0,
            "price": 1.5
        }
    ]
    
    for order in orders_to_place:
        result = await manager.send_request("paper_trading", "place_order", order)
        if result and result.get("success"):
            print(f"   ✅ Orden colocada: {order['symbol']} {order['side']} - ID: {result.get('order_id')}")
        else:
            print(f"   ❌ Error colocando orden {order['symbol']}: {result}")
        
        await asyncio.sleep(0.1)  # Pequeña pausa entre órdenes

async def simulate_market_data(manager: MCPManager):
    """Simular datos de mercado para ejecutar órdenes"""
    market_scenarios = [
        {
            "BTCUSDT": 50100.0,
            "ETHUSDT": 3050.0,
            "ADAUSDT": 1.52,
            "DOTUSDT": 25.0
        },
        {
            "BTCUSDT": 50200.0,
            "ETHUSDT": 3100.0,
            "ADAUSDT": 1.55,
            "DOTUSDT": 25.5
        },
        {
            "BTCUSDT": 49800.0,
            "ETHUSDT": 2950.0,
            "ADAUSDT": 1.48,
            "DOTUSDT": 24.5
        }
    ]
    
    for i, market_data in enumerate(market_scenarios):
        print(f"   📊 Procesando escenario {i+1}...")
        
        result = await manager.send_request("paper_trading", "process_market_data", {
            "market_data": market_data
        })
        
        if result and result.get("success"):
            executed = result.get("executed_orders", [])
            if executed:
                print(f"   ✅ Órdenes ejecutadas: {len(executed)}")
            else:
                print(f"   ℹ️ Sin órdenes ejecutadas en este escenario")
        else:
            print(f"   ❌ Error procesando datos: {result}")
        
        await asyncio.sleep(0.5)  # Pausa entre escenarios

async def test_scalping_operations(manager: MCPManager):
    """Probar operaciones de scalping"""
    scalping_positions = [
        {
            "symbol": "BTCUSDT",
            "direction": "bullish",
            "entry_price": 50000.0,
            "take_profit_pct": 1.5,
            "stop_loss_pct": 0.8,
            "position_size_usd": 200.0,
            "duration_minutes": 3
        },
        {
            "symbol": "ETHUSDT",
            "direction": "bearish",
            "entry_price": 3000.0,
            "take_profit_pct": 2.0,
            "stop_loss_pct": 1.0,
            "position_size_usd": 150.0,
            "duration_minutes": 5
        }
    ]
    
    for scalp in scalping_positions:
        result = await manager.send_request("paper_trading", "create_scalping_position", scalp)
        
        if result and result.get("success"):
            scalp_id = result.get("scalping_id")
            print(f"   🚀 Scalping creado: {scalp['symbol']} {scalp['direction']} - ID: {scalp_id}")
        else:
            print(f"   ❌ Error creando scalping {scalp['symbol']}: {result}")
        
        await asyncio.sleep(0.2)

async def test_integration_with_breakout_mcp():
    """Probar integración entre Paper Trading MCP y Breakout Detector MCP"""
    print("\n🔗 Probando integración entre MCPs...")
    
    manager = MCPManager()
    
    try:
        # Registrar ambos MCPs
        from mcps.breakout_detector_mcp import BreakoutDetectorMCP
        
        manager.register_mcp(PaperTradingMCP, port=8767)
        manager.register_mcp(BreakoutDetectorMCP, port=8766)
        
        # Iniciar ambos
        results = await manager.start_all()
        
        if not all(results.values()):
            print("❌ Error iniciando MCPs para integración")
            return
        
        await asyncio.sleep(2)
        
        # Inicializar paper trading
        await manager.send_request("paper_trading", "initialize_engine", {
            "initial_capital": 5000.0
        })
        
        # Iniciar detección de breakouts
        await manager.send_request("breakout_detector", "start_detection")
        
        # Simular integración: cuando hay breakout, crear trade
        print("   🔄 Simulando integración automática...")
        
        # Simular datos que generen breakout
        breakout_data = [
            {
                "timestamp": datetime.now().isoformat(),
                "open": 49900.0,
                "high": 50200.0,
                "low": 49800.0,
                "close": 50150.0,
                "volume": 2000000
            }
        ]
        
        # Enviar datos al detector
        await manager.send_request("breakout_detector", "update_price_data", {
            "symbol": "BTCUSDT",
            "price_data": breakout_data
        })
        
        await asyncio.sleep(1)
        
        # Verificar si se generó señal
        signals = await manager.send_request("breakout_detector", "get_signals")
        
        if signals and signals.get("signals"):
            print("   📊 Señal de breakout detectada, creando trade automático...")
            
            # Crear trade basado en la señal
            signal = signals["signals"][-1]
            
            await manager.send_request("paper_trading", "place_order", {
                "symbol": signal.get("symbol"),
                "side": "buy" if signal.get("breakout_type") == "bullish" else "sell",
                "order_type": "market",
                "quantity": 0.001,
                "price": signal.get("price")
            })
            
            print("   ✅ Trade automático creado basado en señal de breakout")
        
    except Exception as e:
        print(f"   ❌ Error en integración: {e}")
    
    finally:
        await manager.stop_all()

async def test_performance_under_load():
    """Probar rendimiento del MCP bajo carga"""
    print("\n⚡ Probando rendimiento bajo carga...")
    
    manager = MCPManager()
    
    try:
        manager.register_mcp(PaperTradingMCP, port=8767)
        await manager.start_all()
        await asyncio.sleep(1)
        
        # Inicializar motor
        await manager.send_request("paper_trading", "initialize_engine", {
            "initial_capital": 50000.0
        })
        
        # Crear múltiples órdenes rápidamente
        start_time = time.time()
        
        tasks = []
        for i in range(50):
            task = manager.send_request("paper_trading", "place_order", {
                "symbol": f"TEST{i%5}USDT",
                "side": "buy" if i % 2 == 0 else "sell",
                "order_type": "market",
                "quantity": 0.001,
                "price": 1000.0 + i
            })
            tasks.append(task)
        
        # Ejecutar todas las órdenes concurrentemente
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        
        print(f"   📊 Órdenes procesadas: {successful}/50")
        print(f"   ⏱️ Tiempo total: {end_time - start_time:.2f}s")
        print(f"   🚀 Órdenes por segundo: {successful / (end_time - start_time):.1f}")
        
    except Exception as e:
        print(f"   ❌ Error en prueba de carga: {e}")
    
    finally:
        await manager.stop_all()

if __name__ == "__main__":
    print("🧪 Iniciando suite de pruebas del Paper Trading MCP")
    print("=" * 70)
    
    # Ejecutar prueba principal
    asyncio.run(test_paper_trading_mcp())
    
    print("\n" + "=" * 70)
    print("🔗 Probando integración entre MCPs...")
    asyncio.run(test_integration_with_breakout_mcp())
    
    print("\n" + "=" * 70)
    print("⚡ Probando rendimiento...")
    asyncio.run(test_performance_under_load())
    
    print("\n" + "=" * 70)
    print("🏁 Suite de pruebas completada")