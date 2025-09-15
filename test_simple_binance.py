#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simplificado para probar conexión a Binance y BD temporal
"""

import os
import sqlite3
import sys
from datetime import datetime

def test_imports():
    """Probar importaciones"""
    print("🔍 Probando importaciones...")
    
    try:
        import sqlite3
        print("✅ sqlite3 disponible")
    except ImportError as e:
        print(f"❌ sqlite3 no disponible: {e}")
        return False
    
    try:
        from binance.client import Client
        print("✅ python-binance disponible")
        return True
    except ImportError as e:
        print(f"❌ python-binance no disponible: {e}")
        print("   Instalando...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "python-binance"])
            print("✅ python-binance instalado")
            from binance.client import Client
            print("✅ python-binance importado después de instalación")
            return True
        except Exception as install_error:
            print(f"❌ Error instalando python-binance: {install_error}")
            return False

def crear_bd_temporal():
    """Crear BD SQLite temporal"""
    print("\n📊 Creando base de datos temporal...")
    try:
        # BD en memoria
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # Crear tabla
        cursor.execute('''
            CREATE TABLE operaciones (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                side TEXT,
                quantity REAL,
                price REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insertar datos de prueba
        test_data = [
            ('BTCUSDT', 'BUY', 0.001, 45000.0),
            ('ETHUSDT', 'SELL', 0.1, 3000.0),
            ('ADAUSDT', 'BUY', 100.0, 0.5)
        ]
        
        cursor.executemany(
            'INSERT INTO operaciones (symbol, side, quantity, price) VALUES (?, ?, ?, ?)',
            test_data
        )
        conn.commit()
        
        # Verificar
        cursor.execute('SELECT COUNT(*) FROM operaciones')
        count = cursor.fetchone()[0]
        print(f"✅ BD temporal creada con {count} registros")
        
        # Mostrar datos
        cursor.execute('SELECT * FROM operaciones')
        rows = cursor.fetchall()
        print("\n📋 Datos en BD:")
        for row in rows:
            print(f"  {row[1]} {row[2]} {row[3]} @ ${row[4]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error con BD: {e}")
        return False

def test_binance_connection():
    """Probar conexión a Binance"""
    print("\n🔗 Probando conexión a Binance...")
    
    try:
        from binance.client import Client
        
        # Cliente público (sin autenticación)
        client = Client()
        
        # Probar conexión
        print("📡 Obteniendo tiempo del servidor...")
        server_time = client.get_server_time()
        server_dt = datetime.fromtimestamp(server_time['serverTime']/1000)
        print(f"✅ Servidor Binance: {server_dt}")
        
        # Obtener precios
        print("\n💰 Obteniendo precios actuales...")
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        for symbol in symbols:
            try:
                ticker = client.get_symbol_ticker(symbol=symbol)
                price = float(ticker['price'])
                print(f"✅ {symbol}: ${price:,.4f}")
            except Exception as e:
                print(f"❌ Error obteniendo {symbol}: {e}")
        
        # Probar información de exchange
        print("\n📊 Información del exchange...")
        exchange_info = client.get_exchange_info()
        symbols_count = len(exchange_info['symbols'])
        print(f"✅ Exchange activo con {symbols_count} pares de trading")
        
        return True
        
    except Exception as e:
        print(f"❌ Error conectando a Binance: {e}")
        return False

def main():
    """Función principal"""
    print("🚀 PRUEBA DE CONEXIONES")
    print("=" * 40)
    
    # Test 1: Importaciones
    imports_ok = test_imports()
    
    # Test 2: BD temporal
    bd_ok = crear_bd_temporal()
    
    # Test 3: Binance
    binance_ok = False
    if imports_ok:
        binance_ok = test_binance_connection()
    else:
        print("\n⚠️  Saltando prueba de Binance (falta python-binance)")
    
    # Resumen
    print("\n" + "=" * 40)
    print("📋 RESULTADOS:")
    print(f"   Importaciones: {'✅' if imports_ok else '❌'}")
    print(f"   BD Temporal:   {'✅' if bd_ok else '❌'}")
    print(f"   Binance:       {'✅' if binance_ok else '❌'}")
    
    if imports_ok and bd_ok and binance_ok:
        print("\n🎉 ¡Todo funcionando correctamente!")
        print("\n📝 Listo para:")
        print("   • Usar BD SQLite local para desarrollo")
        print("   • Conectar a Binance API")
        print("   • Implementar estrategias de trading")
        return True
    else:
        print("\n⚠️  Algunos componentes fallaron")
        if not imports_ok:
            print("   • Instalar: pip install python-binance")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrumpido por usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Error inesperado: {e}")
        sys.exit(1)