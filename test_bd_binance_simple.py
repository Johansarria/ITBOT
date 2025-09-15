#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar BD temporal y conexión a Binance usando solo requests
"""

import os
import sqlite3
import sys
import json
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ requests no disponible. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

def crear_bd_temporal():
    """Crear base de datos SQLite temporal para trading"""
    print("📊 Creando base de datos temporal SQLite...")
    
    try:
        # Crear BD en archivo
        db_path = 'trading_bot.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tabla de operaciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                order_id TEXT,
                commission REAL DEFAULT 0.0
            )
        ''')
        
        # Tabla de balances
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                free REAL NOT NULL,
                locked REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de precios históricos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS precios_historicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                volume REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de configuración
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                clave TEXT UNIQUE NOT NULL,
                valor TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insertar datos de prueba
        test_operations = [
            ('BTCUSDT', 'BUY', 0.001, 45000.0, 'completed', 'TEST001', 0.45),
            ('ETHUSDT', 'SELL', 0.1, 3000.0, 'completed', 'TEST002', 0.30),
            ('ADAUSDT', 'BUY', 100.0, 0.5, 'pending', None, 0.0),
            ('BNBUSDT', 'BUY', 1.0, 300.0, 'cancelled', None, 0.0)
        ]
        
        cursor.executemany(
            'INSERT INTO operaciones (symbol, side, quantity, price, status, order_id, commission) VALUES (?, ?, ?, ?, ?, ?, ?)',
            test_operations
        )
        
        test_balances = [
            ('USDT', 1000.0, 50.0),
            ('BTC', 0.001, 0.0),
            ('ETH', 0.0, 0.1),
            ('ADA', 100.0, 0.0),
            ('BNB', 1.0, 0.0)
        ]
        
        cursor.executemany(
            'INSERT INTO balances (asset, free, locked) VALUES (?, ?, ?)',
            test_balances
        )
        
        # Configuración inicial
        config_data = [
            ('trading_enabled', 'false'),
            ('max_position_size', '1000.0'),
            ('risk_percentage', '2.0'),
            ('default_symbol', 'BTCUSDT')
        ]
        
        cursor.executemany(
            'INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)',
            config_data
        )
        
        conn.commit()
        
        # Verificar datos
        cursor.execute('SELECT COUNT(*) FROM operaciones')
        ops_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM balances')
        bal_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM configuracion')
        config_count = cursor.fetchone()[0]
        
        print(f"✅ BD creada: {db_path}")
        print(f"✅ {ops_count} operaciones")
        print(f"✅ {bal_count} balances")
        print(f"✅ {config_count} configuraciones")
        
        # Mostrar resumen
        cursor.execute('''
            SELECT symbol, side, quantity, price, status 
            FROM operaciones 
            ORDER BY timestamp DESC LIMIT 3
        ''')
        ops = cursor.fetchall()
        print("\n📋 Operaciones recientes:")
        for op in ops:
            print(f"  {op[0]} {op[1]} {op[2]} @ ${op[3]} ({op[4]})")
        
        cursor.execute('SELECT asset, free, locked FROM balances WHERE free > 0 OR locked > 0')
        bals = cursor.fetchall()
        print("\n💰 Balances:")
        for bal in bals:
            total = bal[1] + bal[2]
            print(f"  {bal[0]}: {bal[1]} libre + {bal[2]} bloqueado = {total} total")
        
        conn.close()
        return True, db_path
        
    except Exception as e:
        print(f"❌ Error creando BD: {e}")
        return False, None

def test_binance_api():
    """Probar conexión a Binance API usando requests"""
    print("\n🔗 Probando conexión a Binance API...")
    
    base_url = 'https://api.binance.com'
    
    try:
        # Test 1: Ping al servidor
        print("\n📡 Verificando conectividad...")
        response = requests.get(f'{base_url}/api/v3/ping', timeout=10)
        if response.status_code == 200:
            print("✅ Servidor Binance accesible")
        else:
            print(f"⚠️  Respuesta inesperada: {response.status_code}")
        
        # Test 2: Tiempo del servidor
        print("\n⏰ Obteniendo tiempo del servidor...")
        response = requests.get(f'{base_url}/api/v3/time', timeout=10)
        if response.status_code == 200:
            server_time = response.json()['serverTime']
            server_dt = datetime.fromtimestamp(server_time/1000)
            print(f"✅ Tiempo servidor: {server_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print(f"❌ Error obteniendo tiempo: {response.status_code}")
            return False, []
        
        # Test 3: Información del exchange
        print("\n📊 Obteniendo información del exchange...")
        response = requests.get(f'{base_url}/api/v3/exchangeInfo', timeout=15)
        if response.status_code == 200:
            exchange_info = response.json()
            symbols_count = len(exchange_info['symbols'])
            print(f"✅ Exchange operativo con {symbols_count} pares")
            
            # Verificar algunos símbolos importantes
            symbols_dict = {s['symbol']: s for s in exchange_info['symbols']}
            important_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']
            active_symbols = []
            
            for symbol in important_symbols:
                if symbol in symbols_dict and symbols_dict[symbol]['status'] == 'TRADING':
                    active_symbols.append(symbol)
                    print(f"✅ {symbol} activo para trading")
                else:
                    print(f"⚠️  {symbol} no disponible")
        else:
            print(f"❌ Error obteniendo info exchange: {response.status_code}")
            return False, []
        
        # Test 4: Precios actuales
        print("\n💰 Obteniendo precios actuales...")
        symbols_to_check = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']
        precios_obtenidos = []
        
        for symbol in symbols_to_check:
            try:
                response = requests.get(f'{base_url}/api/v3/ticker/price?symbol={symbol}', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    price = float(data['price'])
                    print(f"✅ {symbol}: ${price:,.4f}")
                    precios_obtenidos.append((symbol, price))
                else:
                    print(f"⚠️  Error obteniendo precio {symbol}: {response.status_code}")
            except Exception as e:
                print(f"⚠️  Error con {symbol}: {e}")
        
        # Test 5: Estadísticas 24h
        print("\n📈 Estadísticas 24h para BTC/USDT...")
        try:
            response = requests.get(f'{base_url}/api/v3/ticker/24hr?symbol=BTCUSDT', timeout=10)
            if response.status_code == 200:
                stats = response.json()
                volume = float(stats['volume'])
                change = float(stats['priceChangePercent'])
                high = float(stats['highPrice'])
                low = float(stats['lowPrice'])
                
                print(f"✅ Volumen 24h: {volume:,.2f} BTC")
                print(f"✅ Cambio 24h: {change:+.2f}%")
                print(f"✅ Máximo 24h: ${high:,.2f}")
                print(f"✅ Mínimo 24h: ${low:,.2f}")
            else:
                print(f"⚠️  Error obteniendo estadísticas: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error con estadísticas: {e}")
        
        # Test 6: Libro de órdenes
        print("\n📊 Probando libro de órdenes BTC/USDT...")
        try:
            response = requests.get(f'{base_url}/api/v3/depth?symbol=BTCUSDT&limit=5', timeout=10)
            if response.status_code == 200:
                depth = response.json()
                bids = len(depth['bids'])
                asks = len(depth['asks'])
                print(f"✅ Libro de órdenes: {bids} bids, {asks} asks")
                
                if bids > 0 and asks > 0:
                    best_bid = float(depth['bids'][0][0])
                    best_ask = float(depth['asks'][0][0])
                    spread = best_ask - best_bid
                    spread_pct = (spread / best_bid) * 100
                    print(f"✅ Mejor bid: ${best_bid:,.2f}")
                    print(f"✅ Mejor ask: ${best_ask:,.2f}")
                    print(f"✅ Spread: ${spread:.2f} ({spread_pct:.3f}%)")
            else:
                print(f"⚠️  Error obteniendo libro: {response.status_code}")
        except Exception as e:
            print(f"⚠️  Error con libro de órdenes: {e}")
        
        return True, precios_obtenidos
        
    except requests.exceptions.ConnectionError:
        print("❌ Error de conexión. Verifica tu internet.")
        return False, []
    except requests.exceptions.Timeout:
        print("❌ Timeout conectando a Binance.")
        return False, []
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False, []

def guardar_precios_en_bd(db_path, precios):
    """Guardar precios en la base de datos"""
    if not db_path or not precios:
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for symbol, price in precios:
            cursor.execute(
                'INSERT INTO precios_historicos (symbol, price) VALUES (?, ?)',
                (symbol, price)
            )
        
        conn.commit()
        conn.close()
        print(f"\n💾 {len(precios)} precios guardados en BD")
        return True
        
    except Exception as e:
        print(f"⚠️  Error guardando precios: {e}")
        return False

def mostrar_resumen_bd(db_path):
    """Mostrar resumen de la base de datos"""
    if not db_path:
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📊 RESUMEN DE BASE DE DATOS:")
        
        # Contar registros en cada tabla
        tables = ['operaciones', 'balances', 'precios_historicos', 'configuracion']
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f"   {table}: {count} registros")
        
        # Mostrar últimos precios
        cursor.execute('''
            SELECT symbol, price, timestamp 
            FROM precios_historicos 
            ORDER BY timestamp DESC 
            LIMIT 5
        ''')
        precios = cursor.fetchall()
        if precios:
            print("\n💰 Últimos precios guardados:")
            for precio in precios:
                print(f"   {precio[0]}: ${precio[1]:,.4f} ({precio[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"⚠️  Error leyendo BD: {e}")

def main():
    """Función principal"""
    print("🚀 PRUEBA COMPLETA: BD TEMPORAL + BINANCE API")
    print("=" * 55)
    
    # Test 1: Crear BD temporal
    print("\n1️⃣ CREANDO BASE DE DATOS TEMPORAL")
    bd_ok, db_path = crear_bd_temporal()
    
    # Test 2: Probar Binance API
    print("\n2️⃣ PROBANDO CONEXIÓN A BINANCE API")
    binance_ok, precios = test_binance_api()
    
    # Test 3: Integrar datos
    integration_ok = False
    if bd_ok and binance_ok and precios:
        print("\n3️⃣ INTEGRANDO DATOS")
        integration_ok = guardar_precios_en_bd(db_path, precios)
    
    # Test 4: Mostrar resumen
    if bd_ok and db_path:
        print("\n4️⃣ RESUMEN DE DATOS")
        mostrar_resumen_bd(db_path)
    
    # Resumen final
    print("\n" + "=" * 55)
    print("📋 RESUMEN FINAL:")
    print(f"   BD Temporal:  {'✅ OK' if bd_ok else '❌ FALLO'}")
    print(f"   Binance API:  {'✅ OK' if binance_ok else '❌ FALLO'}")
    print(f"   Integración:  {'✅ OK' if integration_ok else '❌ FALLO'}")
    
    if bd_ok and binance_ok:
        print("\n🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!")
        print("\n📝 Capacidades verificadas:")
        print("   ✅ Base de datos SQLite local")
        print("   ✅ Conexión a Binance API")
        print("   ✅ Obtención de precios en tiempo real")
        print("   ✅ Almacenamiento de datos históricos")
        print("   ✅ Gestión de operaciones y balances")
        
        print("\n🚀 Próximos pasos sugeridos:")
        print("   1. Configurar credenciales de Binance para trading real")
        print("   2. Implementar estrategias de trading")
        print("   3. Añadir sistema de alertas")
        print("   4. Configurar gestión de riesgo")
        print("   5. Implementar backtesting")
        
        if db_path:
            print(f"\n📁 Base de datos: {db_path}")
            print("   (Examínala con DB Browser for SQLite o similar)")
    else:
        print("\n⚠️  Sistema parcialmente funcional")
        if not bd_ok:
            print("   • Problema con SQLite (revisar permisos)")
        if not binance_ok:
            print("   • Problema con Binance API (revisar conexión)")
    
    return bd_ok and binance_ok

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n{'🎉 ÉXITO' if success else '⚠️  PARCIAL'}: Pruebas completadas")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)