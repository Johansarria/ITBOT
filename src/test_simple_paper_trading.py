"""
Prueba simplificada del Paper Trading MCP
"""

import asyncio
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_framework import MCPManager
from mcps.paper_trading_mcp import PaperTradingMCP

async def test_simple():
    """Prueba básica del Paper Trading MCP"""
    print("🧪 Iniciando prueba simplificada...")
    
    # Crear manager
    manager = MCPManager()
    
    try:
        # Registrar MCP
        print("📝 Registrando MCP...")
        success = manager.register_mcp(PaperTradingMCP, name="paper_trading", port=8767)
        print(f"   Registro exitoso: {success}")
        
        if not success:
            print("❌ Error en el registro")
            return
        
        # Verificar que está registrado
        print(f"   MCPs registrados: {list(manager.mcps.keys())}")
        
        # Iniciar MCPs
        print("🔄 Iniciando MCPs...")
        results = await manager.start_all()
        print(f"   Resultados de inicio: {results}")
        
        # Esperar un momento
        await asyncio.sleep(3)
        
        # Verificar estado
        print("📊 Verificando estado...")
        health = await manager.get_health_report()
        print(f"   Reporte de salud: {health}")
        
        # Intentar una solicitud simple
        print("📞 Enviando solicitud de estado...")
        status = await manager.send_request("paper_trading", "get_engine_status")
        print(f"   Respuesta: {status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("🛑 Deteniendo MCPs...")
        await manager.stop_all()

if __name__ == "__main__":
    asyncio.run(test_simple())