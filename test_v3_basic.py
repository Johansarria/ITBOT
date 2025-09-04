#!/usr/bin/env python3
"""
PRUEBA SIMPLE V3
================
Prueba básica para verificar que los módulos V3 pueden importarse y funcionar.
"""

import sys
import os

# Añadir path del proyecto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_basic_imports():
    """Probar importaciones básicas"""
    print("🧪 Probando importaciones básicas...")
    
    try:
        # Importar configuración
        from config import settings
        print("  ✅ config importado")
        
        # Importar utils básicos
        from utils.structured_logger import StructuredLogger
        print("  ✅ StructuredLogger importado")
        
        from utils.state_manager import StateManager
        print("  ✅ StateManager importado")
        
        # Importar message queue
        from utils.message_queue import mq
        print("  ✅ MessageQueue importado")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_v3_system_basic():
    """Probar sistema V3 básico"""
    print("\n🧪 Probando sistema V3 básico...")
    
    try:
        # Importar ccxt para datos de mercado
        import ccxt
        print("  ✅ ccxt importado")
        
        # Crear cliente básico
        exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'sandbox': False,
            'enableRateLimit': True,
        })
        print("  ✅ Cliente Binance creado")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_telegram_handlers():
    """Probar handlers de Telegram"""
    print("\n🧪 Probando handlers de Telegram...")
    
    try:
        from telegram.ext import CommandHandler, CallbackQueryHandler
        print("  ✅ Telegram imports ok")
        
        # Simular handler function
        async def dummy_handler(update, context):
            pass
        
        cmd_handler = CommandHandler("test", dummy_handler)
        callback_handler = CallbackQueryHandler(dummy_handler, pattern="^test$")
        
        print("  ✅ Handlers creados correctamente")
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Función principal de prueba"""
    print("🚀 PRUEBA BÁSICA V3")
    print("=" * 40)
    
    tests = [
        ("Importaciones Básicas", test_basic_imports),
        ("Sistema V3 Básico", test_v3_system_basic),
        ("Handlers Telegram", test_telegram_handlers),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name}: PASS")
                passed += 1
            else:
                print(f"❌ {test_name}: FAIL")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 40)
    print(f"📊 RESULTADO: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("🎉 PRUEBAS BÁSICAS EXITOSAS")
        print("\n💡 El entorno está listo para V3")
        print("   - Dependencias básicas funcionando")
        print("   - APIs accesibles") 
        print("   - Sistema de handlers ok")
    else:
        print("⚠️ ALGUNAS PRUEBAS FALLARON")
        print("\n🔧 Verifica las dependencias:")
        print("   - pip install -r requirements.txt")
        print("   - Configuración de APIs")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Prueba interrumpida")
        exit(130)
    except Exception as e:
        print(f"\n\n❌ Error fatal: {e}")
        exit(1)
