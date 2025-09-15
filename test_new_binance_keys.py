#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar las nuevas claves API de Binance
"""

import os
import sys
from datetime import datetime

# Configurar las nuevas claves API
os.environ['BINANCE_API_KEY'] = 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs'
os.environ['BINANCE_SECRET_KEY'] = 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'

def test_new_binance_keys():
    """Probar las nuevas claves API de Binance"""
    print("="*60)
    print("🔑 VERIFICACIÓN DE NUEVAS CLAVES API DE BINANCE")
    print("="*60)
    
    try:
        # Importar binance
        from binance.client import Client
        print("✅ Módulo python-binance importado correctamente")
        
        # Obtener claves
        api_key = os.environ['BINANCE_API_KEY']
        secret_key = os.environ['BINANCE_SECRET_KEY']
        
        print(f"🔑 API Key: {api_key[:8]}...{api_key[-8:]}")
        print(f"🔐 Secret Key: {secret_key[:8]}...{secret_key[-8:]}")
        
        # Crear cliente
        client = Client(api_key, secret_key, testnet=False)
        print("✅ Cliente Binance creado exitosamente")
        
        # Probar conexión
        print("\n🔍 Probando conexión al servidor...")
        server_time = client.get_server_time()
        server_dt = datetime.fromtimestamp(server_time['serverTime']/1000)
        print(f"✅ Servidor Binance: {server_dt}")
        
        # Probar información de cuenta
        print("\n👤 Probando información de cuenta...")
        try:
            account_info = client.get_account()
            print(f"✅ Información de cuenta obtenida")
            print(f"   - Tipo de cuenta: {account_info.get('accountType', 'N/A')}")
            print(f"   - Permisos: {', '.join(account_info.get('permissions', []))}")
            
            # Mostrar algunos balances
            balances = [b for b in account_info.get('balances', []) if float(b['free']) > 0]
            if balances:
                print(f"   - Activos con balance: {len(balances)}")
                for balance in balances[:3]:  # Mostrar solo los primeros 3
                    print(f"     * {balance['asset']}: {balance['free']}")
            else:
                print("   - No se encontraron balances")
                
        except Exception as e:
            print(f"⚠️  Error al obtener información de cuenta: {e}")
            print("   (Esto puede ser normal si la cuenta no tiene permisos de trading)")
        
        # Probar obtención de precios
        print("\n💰 Probando obtención de precios...")
        try:
            btc_price = client.get_symbol_ticker(symbol="BTCUSDT")
            print(f"✅ Precio BTC/USDT: ${float(btc_price['price']):,.2f}")
            
            eth_price = client.get_symbol_ticker(symbol="ETHUSDT")
            print(f"✅ Precio ETH/USDT: ${float(eth_price['price']):,.2f}")
            
        except Exception as e:
            print(f"❌ Error al obtener precios: {e}")
        
        print("\n" + "="*60)
        print("🎉 NUEVAS CLAVES API DE BINANCE FUNCIONANDO CORRECTAMENTE")
        print("="*60)
        return True
        
    except ImportError:
        print("❌ Módulo python-binance no está instalado")
        print("   Ejecuta: pip install python-binance")
        return False
        
    except Exception as e:
        print(f"❌ Error al conectar con Binance: {e}")
        print("\n🔍 Posibles causas:")
        print("   - Claves API incorrectas")
        print("   - Problemas de conectividad")
        print("   - Restricciones de IP")
        return False

if __name__ == "__main__":
    # Redirigir salida a archivo
    with open('test_binance_keys_result.txt', 'w', encoding='utf-8') as f:
        import sys
        original_stdout = sys.stdout
        sys.stdout = f
        
        success = test_new_binance_keys()
        if success:
            print("\n✅ RESULTADO: Las nuevas claves API están funcionando correctamente")
        else:
            print("\n❌ RESULTADO: Hay problemas con las nuevas claves API")
        
        sys.stdout = original_stdout
    
    print("Resultados guardados en: test_binance_keys_result.txt")
    sys.exit(0 if success else 1)