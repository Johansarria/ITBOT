#!/usr/bin/env python3
"""
Prueba simple para verificar el registro del BreakoutDetectorMCP
"""

import asyncio
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_framework import MCPManager
from mcps.breakout_detector_mcp import BreakoutDetectorMCP

async def test_breakout_registration():
    """Prueba simple de registro del BreakoutDetectorMCP"""
    print("🧪 Prueba de registro del BreakoutDetectorMCP")
    print("=" * 50)
    
    manager = MCPManager()
    
    try:
        # 1. Verificar importación
        print("\n📦 Verificando importación...")
        print(f"   BreakoutDetectorMCP: {BreakoutDetectorMCP}")
        print(f"   Tipo: {type(BreakoutDetectorMCP)}")
        
        # 2. Crear instancia directa
        print("\n🏗️ Creando instancia directa...")
        try:
            detector = BreakoutDetectorMCP(port=8766)
            print(f"   Instancia creada: ✅")
            print(f"   Nombre: {detector.name}")
            print(f"   Puerto: {detector.port}")
            print(f"   Info: {detector.get_info()}")
        except Exception as e:
            print(f"   Error creando instancia: ❌ {e}")
            return False
        
        # 3. Registrar con MCPManager
        print("\n📝 Registrando con MCPManager...")
        try:
            success = manager.register_mcp(BreakoutDetectorMCP, name="breakout_detector")
            print(f"   Registro: {'✅' if success else '❌'}")
            print(f"   MCPs registrados: {list(manager.mcps.keys())}")
            
            if success:
                # Verificar que está en la lista
                if "breakout_detector" in manager.mcps:
                    print(f"   Verificación: ✅ MCP encontrado en lista")
                    mcp_instance = manager.mcps["breakout_detector"]
                    print(f"   Instancia: {type(mcp_instance)}")
                else:
                    print(f"   Verificación: ❌ MCP no encontrado en lista")
                    return False
            else:
                print(f"   Registro falló")
                return False
                
        except Exception as e:
            print(f"   Error en registro: ❌ {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 4. Intentar inicializar
        print("\n🚀 Intentando inicializar...")
        try:
            init_success = await detector.initialize()
            print(f"   Inicialización: {'✅' if init_success else '❌'}")
        except Exception as e:
            print(f"   Error en inicialización: ❌ {e}")
            import traceback
            traceback.print_exc()
        
        print("\n✅ Prueba de registro completada exitosamente")
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_breakout_registration())
    sys.exit(0 if result else 1)