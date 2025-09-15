#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script final para probar Binance y BD temporal local
"""

import os
import sqlite3
import sys
from datetime import datetime

def crear_bd_temporal():
    """Crear base de datos SQLite temporal"""
    print("📊 Creando base de datos temporal SQLite...")
    
    try:
        # Crear BD en archivo temporal
        db_path = 'temp_trading.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Crear tablas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset TEXT NOT NULL,
                free REAL NOT NULL,
                locked REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS precios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insertar datos de prueba
        test_operations = [
            ('BTCUSDT', 'BUY', 0.001, 45000.0, 'completed'),
            ('ETHUSDT', 'SELL', 0.1, 3000.0, 'completed'),
            ('ADAUSDT', 'BUY', 100.0, 0.5, 'pending'),
            ('BNBUSDT', 'BUY', 1.0, 300.0, 'cancelled')
        ]
        
        cursor.executemany(
            'INSERT INTO operaciones (symbol, side, quantity, price, status) VALUES (?, ?, ?, ?, ?)',
            test_operations
        )
        
        test_balances = [
            ('USDT', 1000.0, 0.0),
            ('BTC', 0.001, 0.0),
            ('ETH', 0.0, 0.1),
            ('ADA', 100.0, 0.0)
        ]
        
        cursor.executemany(
            'INSERT INTO balances (asset, free, locked) VALUES (?, ?, ?)',
            test_balances
        )
        
        conn.commit()
        
        # Verificar datos
        cursor.execute('SELECT COUNT(*) FROM operaciones')
        ops_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM balances')
        bal_count = cursor.fetchone()[0]
        
        print(f"✅ BD creada: {db_path}")
        print(f"✅ {ops_count} operaciones de prueba")
        print(f"✅ {bal_count} balances de prueba")
        
        # Mostrar algunas operaciones
        cursor.execute('SELECT symbol, side, quantity, price, status FROM operaciones LIMIT 3')
        ops = cursor.fetchall()
        print("\n📋 Operaciones recientes:")
        for op in ops:
            print(f"  {op[0]} {op[1]} {op[2]} @ ${op[3]} ({op[4]})")
        
        # Mostrar balances
        cursor.execute('SELECT asset, free FROM balances WHERE free > 0')
        bals = cursor.fetchall()
        print("\n💰 Balances disponibles:")
        for bal in bals:
            print(f"  {bal[0]}: {bal[1]}")
        
        conn.close()
        return True, db_path
        
    except Exception as e:
        print(f"❌ Error creando BD: {e}")
        return False, None

def test_binance_connection():
    """Probar conexión a Binance API"""
    print("\n🔗 Probando conexión a Binance...")
    
    try:
        from binance.client import Client
        print("✅ Módulo python-binance importado")
        
        # Cliente público (sin autenticación)
        client = Client()
        
        # Test 1: Tiempo del servidor
        print("\n⏰ Verificando servidor Binance...")
        server_time = client.get_server_time()
        server_dt = datetime.fromtimestamp(server_time['serverTime']/1000)
        print(f"✅ Servidor activo: {server_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test 2: Información del exchange
        print("\n📊 Obteniendo información del exchange...")
        exchange_info = client.get_exchange_info()
        symbols_count = len(exchange_info['symbols'])
        print(f"✅ Exchange operativo con {symbols_count} pares")
        
        # Test 3: Precios en tiempo real
        print("\n💰 Precios actuales:")
        symbols_to_check = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']
        
        precios_obtenidos = []
        for symbol in symbols_to_check:
            try:
                ticker = client.get_symbol_ticker(symbol=symbol)
                price = float(ticker['price'])
                print(f"✅ {symbol}: ${price:,.4f}")
                precios_obtenidos.append((symbol, price))
            except Exception as e:
                print(f"⚠️  Error obteniendo {symbol}: {e}")
        
        # Test 4: Libro de órdenes (depth)
        print("\n📈 Probando libro de órdenes BTC/USDT...")
        try:
            depth = client.get_order_book(symbol='BTCUSDT', limit=5)
            bids = len(depth['bids'])
            asks = len(depth['asks'])
            print(f"✅ Libro de órdenes: {bids} bids, {asks} asks")
            
            if bids > 0 and asks > 0:
                best_bid = float(depth['bids'][0][0])
                best_ask = float(depth['asks'][0][0])
                spread = best_ask - best_bid
                print(f"✅ Spread BTC/USDT: ${spread:.2f}")
        except Exception as e:
            print(f"⚠️  Error obteniendo libro de órdenes: {e}")
        
        # Test 5: Klines (velas)
        print("\n📊 Probando datos históricos...")
        try:
            klines = client.get_klines(symbol='BTCUSDT', interval='1h', limit=3)
            print(f"✅ Obtenidas {len(klines)} velas de 1h para BTC/USDT")
            
            if klines:
                latest = klines[-1]
                open_price = float(latest[1])
                close_price = float(latest[4])
                print(f"✅ Última vela: Open ${open_price:,.2f}, Close ${close_price:,.2f}")
        except Exception as e:
            print(f"⚠️  Error obteniendo klines: {e}")
        
        return True, precios_obtenidos
        
    except ImportError:
        print("❌ python-binance no está instalado")
        print("   Ejecuta: pip install python-binance")
        return False, []
    except Exception as e:
        print(f"❌ Error conectando a Binance: {e}")
        return False, []

def guardar_precios_en_bd(db_path, precios):
    """Guardar precios obtenidos en la BD"""
    if not db_path or not precios:
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for symbol, price in precios:
            cursor.execute(
                'INSERT INTO precios (symbol, price) VALUES (?, ?)',
                (symbol, price)
            )
        
        conn.commit()
        conn.close()
        print(f"\n💾 {len(precios)} precios guardados en BD")
        
    except Exception as e:
        print(f"⚠️  Error guardando precios: {e}")

def main():
    """Función principal"""
    print("🚀 PRUEBA COMPLETA: BD TEMPORAL + BINANCE")
    print("=" * 50)
    
    # Test 1: Crear BD temporal
    print("\n1️⃣ CREANDO BASE DE DATOS TEMPORAL")
    bd_ok, db_path = crear_bd_temporal()
    
    # Test 2: Probar Binance
    print("\n2️⃣ PROBANDO CONEXIÓN A BINANCE")
    binance_ok, precios = test_binance_connection()
    
    # Test 3: Integrar datos
    if bd_ok and binance_ok and precios:
        print("\n3️⃣ INTEGRANDO DATOS")
        guardar_precios_en_bd(db_path, precios)
    
    # Resumen final
    print("\n" + "=" * 50)
    print("📋 RESUMEN FINAL:")
    print(f"   BD Temporal:  {'✅ OK' if bd_ok else '❌ FALLO'}")
    print(f"   Binance API:  {'✅ OK' if binance_ok else '❌ FALLO'}")
    print(f"   Integración:  {'✅ OK' if (bd_ok and binance_ok) else '❌ FALLO'}")
    
    if bd_ok and binance_ok:
        print("\n🎉 ¡SISTEMA LISTO PARA TRADING!")
        print("\n📝 Próximos pasos:")
        print("   • Configurar credenciales de Binance (.env)")
        print("   • Implementar estrategias de trading")
        print("   • Configurar gestión de riesgo")
        print("   • Añadir logging y monitoreo")
        
        if db_path:
            print(f"\n📁 BD temporal creada en: {db_path}")
            print("   (Puedes examinarla con cualquier cliente SQLite)")
    else:
        print("\n⚠️  Sistema no completamente funcional")
        if not bd_ok:
            print("   • Problema con SQLite")
        if not binance_ok:
            print("   • Problema con Binance API")
            print("   • Verifica: pip install python-binance")
    
    return bd_ok and binance_ok

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)