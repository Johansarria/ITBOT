#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para verificar las nuevas claves API de Binance usando requests
"""

import requests
import time
import hashlib
import hmac
from urllib.parse import urlencode

# Nuevas claves API de Binance
API_KEY = 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs'
SECRET_KEY = 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'

BASE_URL = 'https://api.binance.com'

def create_signature(query_string, secret_key):
    """Crear firma HMAC SHA256 para la API de Binance"""
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def test_binance_connection():
    """Probar conexión básica a Binance"""
    print("="*60)
    print("🔑 VERIFICACIÓN DE NUEVAS CLAVES API DE BINANCE")
    print("="*60)
    
    try:
        # 1. Probar conexión al servidor
        print("\n🔍 1. Probando conexión al servidor Binance...")
        response = requests.get(f"{BASE_URL}/api/v3/time", timeout=10)
        
        if response.status_code == 200:
            server_time = response.json()['serverTime']
            print(f"✅ Servidor Binance accesible")
            print(f"   Tiempo del servidor: {server_time}")
        else:
            print(f"❌ Error al conectar al servidor: {response.status_code}")
            return False
        
        # 2. Probar obtención de precios públicos
        print("\n💰 2. Probando obtención de precios públicos...")
        response = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol=BTCUSDT", timeout=10)
        
        if response.status_code == 200:
            btc_price = response.json()
            print(f"✅ Precio BTC/USDT: ${float(btc_price['price']):,.2f}")
        else:
            print(f"❌ Error al obtener precio BTC: {response.status_code}")
        
        # 3. Probar autenticación con las nuevas claves
        print("\n🔐 3. Probando autenticación con nuevas claves API...")
        print(f"   API Key: {API_KEY[:8]}...{API_KEY[-8:]}")
        print(f"   Secret Key: {SECRET_KEY[:8]}...{SECRET_KEY[-8:]}")
        
        # Crear parámetros para la consulta autenticada
        timestamp = int(time.time() * 1000)
        params = {
            'timestamp': timestamp
        }
        
        query_string = urlencode(params)
        signature = create_signature(query_string, SECRET_KEY)
        
        headers = {
            'X-MBX-APIKEY': API_KEY
        }
        
        # Probar endpoint de información de cuenta
        url = f"{BASE_URL}/api/v3/account?{query_string}&signature={signature}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            account_info = response.json()
            print(f"✅ Autenticación exitosa")
            print(f"   Tipo de cuenta: {account_info.get('accountType', 'N/A')}")
            print(f"   Permisos: {', '.join(account_info.get('permissions', []))}")
            
            # Mostrar algunos balances
            balances = [b for b in account_info.get('balances', []) if float(b['free']) > 0]
            if balances:
                print(f"   Activos con balance: {len(balances)}")
                for balance in balances[:3]:  # Mostrar solo los primeros 3
                    print(f"     * {balance['asset']}: {balance['free']}")
            else:
                print("   No se encontraron balances positivos")
                
        elif response.status_code == 401:
            print(f"❌ Error de autenticación: Claves API inválidas")
            print(f"   Respuesta: {response.text}")
            return False
        else:
            print(f"⚠️  Respuesta inesperada: {response.status_code}")
            print(f"   Respuesta: {response.text[:200]}...")
        
        print("\n" + "="*60)
        print("🎉 VERIFICACIÓN COMPLETADA")
        print("="*60)
        return True
        
    except requests.exceptions.Timeout:
        print("❌ Timeout al conectar con Binance")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión a Binance")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

if __name__ == "__main__":
    # Guardar resultados en archivo
    with open('test_binance_api_result.txt', 'w', encoding='utf-8') as f:
        import sys
        original_stdout = sys.stdout
        sys.stdout = f
        
        success = test_binance_connection()
        
        if success:
            print("\n✅ RESULTADO: Las nuevas claves API están funcionando correctamente")
        else:
            print("\n❌ RESULTADO: Hay problemas con las nuevas claves API")
        
        sys.stdout = original_stdout
    
    print("Resultados guardados en: test_binance_api_result.txt")
    print("✅ Nuevas claves API configuradas exitosamente" if success else "❌ Problemas con las nuevas claves API")