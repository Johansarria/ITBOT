#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar conexión a Binance y crear BD temporal local
"""

import os
import sqlite3
import sys
from datetime import datetime

# Configurar variables de entorno manualmente si no existen
if not os.getenv('BINANCE_API_KEY'):
    os.environ['BINANCE_API_KEY'] = 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs'
if not os.getenv('BINANCE_SECRET_KEY'):
    os.environ['BINANCE_SECRET_KEY'] = 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'
if not os.getenv('BINANCE_TESTNET'):
    os.environ['BINANCE_TESTNET'] = 'true'

def crear_bd_temporal():
    """Crear una base de datos SQLite temporal local"""
    try:
        # Crear BD temporal en memoria
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # Crear tabla de prueba
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insertar datos de prueba
        cursor.execute('''
            INSERT INTO operaciones (symbol, side, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', ('BTCUSDT', 'BUY', 0.001, 45000.0))
        
        cursor.execute('''
            INSERT INTO operaciones (symbol, side, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', ('ETHUSDT', 'SELL', 0.1, 3000.0))
        
        conn.commit()
        
        # Verificar datos
        cursor.execute('SELECT COUNT(*) FROM operaciones')
        count = cursor.fetchone()[0]
        
        print(f"✅ BD temporal creada exitosamente")
        print(f"✅ Tabla 'operaciones' creada con {count} registros de prueba")
        
        # Mostrar datos
        cursor.execute('SELECT * FROM operaciones')
        rows = cursor.fetchall()
        print("\n📊 Datos en la BD temporal:")
        for row in rows:
            print(f"  ID: {row[0]}, Symbol: {row[1]}, Side: {row[2]}, Qty: {row[3]}, Price: {row[4]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creando BD temporal: {e}")
        return False

def probar_conexion_binance():
    """Probar conexión a Binance"""
    try:
        # Intentar importar binance
        from binance.client import Client
        print("✅ Módulo python-binance importado correctamente")
        
        # Obtener credenciales
        api_key = os.getenv('BINANCE_API_KEY')
        secret_key = os.getenv('BINANCE_SECRET_KEY')
        testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
        
        if not api_key or api_key in ['tu_api_key_aqui', 'dummy_api_key_for_tests']:
            print("⚠️  API Key no configurada. Usando modo de solo lectura.")
            # Crear cliente sin autenticación para datos públicos
            client = Client()
        else:
            print(f"🔑 Usando API Key: {api_key[:8]}...")
            # Crear cliente con autenticación
            client = Client(api_key, secret_key, testnet=testnet)
        
        # Probar conexión con datos públicos
        print("\n🔍 Probando conexión a Binance...")
        
        # Obtener información del servidor
        server_time = client.get_server_time()
        print(f"✅ Tiempo del servidor Binance: {datetime.fromtimestamp(server_time['serverTime']/1000)}")
        
        # Obtener precio de BTC
        btc_price = client.get_symbol_ticker(symbol="BTCUSDT")
        print(f"✅ Precio actual BTC/USDT: ${float(btc_price['price']):,.2f}")
        
        # Obtener precio de ETH
        eth_price = client.get_symbol_ticker(symbol="ETHUSDT")
        print(f"✅ Precio actual ETH/USDT: ${float(eth_price['price']):,.2f}")
        
        # Si tenemos credenciales, probar información de cuenta
        if api_key and api_key not in ['tu_api_key_aqui', 'dummy_api_key_for_tests']:
            try:
                account_info = client.get_account()
                print(f"✅ Información de cuenta obtenida")
                print(f"✅ Modo testnet: {testnet}")
                
                # Mostrar algunos balances
                balances = [b for b in account_info['balances'] if float(b['free']) > 0]
                if balances:
                    print("\n💰 Balances disponibles:")
                    for balance in balances[:5]:  # Mostrar solo los primeros 5
                        free = float(balance['free'])
                        if free > 0:
                            print(f"  {balance['asset']}: {free}")
                else:
                    print("\n💰 No hay balances disponibles (cuenta testnet vacía)")
                    
            except Exception as e:
                print(f"⚠️  Error obteniendo información de cuenta: {e}")
                print("   Esto puede ser normal si las credenciales son de prueba")
        
        print("\n✅ Conexión a Binance exitosa")
        return True
        
    except ImportError:
        print("❌ Error: Módulo 'python-binance' no instalado")
        print("   Ejecuta: pip install python-binance")
        return False
    except Exception as e:
        print(f"❌ Error conectando a Binance: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 Iniciando pruebas de conexión y BD temporal")
    print("=" * 50)
    
    # Probar BD temporal
    print("\n1️⃣ Creando base de datos temporal local...")
    bd_ok = crear_bd_temporal()
    
    # Probar conexión Binance
    print("\n2️⃣ Probando conexión a Binance...")
    binance_ok = probar_conexion_binance()
    
    # Resumen
    print("\n" + "=" * 50)
    print("📋 RESUMEN DE PRUEBAS:")
    print(f"   BD Temporal: {'✅ OK' if bd_ok else '❌ FALLO'}")
    print(f"   Binance:     {'✅ OK' if binance_ok else '❌ FALLO'}")
    
    if bd_ok and binance_ok:
        print("\n🎉 ¡Todas las pruebas exitosas!")
        print("\n📝 Próximos pasos:")
        print("   1. Configurar credenciales reales de Binance en .env")
        print("   2. Decidir si usar BD local (SQLite) o PostgreSQL")
        print("   3. Implementar lógica de trading")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")
        
        if not binance_ok:
            print("\n🔧 Para instalar dependencias:")
            print("   pip install python-binance")
    
    return bd_ok and binance_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)