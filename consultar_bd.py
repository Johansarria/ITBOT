#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para consultar y gestionar la base de datos de trading
"""

import sqlite3
import sys
from datetime import datetime

def conectar_bd():
    """Conectar a la base de datos"""
    try:
        conn = sqlite3.connect('trading_bot.db')
        return conn
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        return None

def mostrar_operaciones():
    """Mostrar todas las operaciones"""
    conn = conectar_bd()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, symbol, side, quantity, price, status, timestamp, commission
            FROM operaciones 
            ORDER BY timestamp DESC
        ''')
        
        operaciones = cursor.fetchall()
        
        print("\n📊 OPERACIONES REGISTRADAS:")
        print("-" * 80)
        print(f"{'ID':<4} {'Symbol':<10} {'Side':<5} {'Cantidad':<12} {'Precio':<12} {'Estado':<10} {'Comisión':<8}")
        print("-" * 80)
        
        total_compras = 0
        total_ventas = 0
        total_comisiones = 0
        
        for op in operaciones:
            id_op, symbol, side, quantity, price, status, timestamp, commission = op
            valor_total = quantity * price
            
            print(f"{id_op:<4} {symbol:<10} {side:<5} {quantity:<12.6f} ${price:<11.2f} {status:<10} ${commission:<7.2f}")
            
            if side == 'BUY':
                total_compras += valor_total
            else:
                total_ventas += valor_total
            
            total_comisiones += commission or 0
        
        print("-" * 80)
        print(f"Total compras: ${total_compras:,.2f}")
        print(f"Total ventas:  ${total_ventas:,.2f}")
        print(f"Comisiones:    ${total_comisiones:,.2f}")
        print(f"Balance neto:  ${total_ventas - total_compras - total_comisiones:,.2f}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error consultando operaciones: {e}")
        conn.close()

def mostrar_balances():
    """Mostrar balances actuales"""
    conn = conectar_bd()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT asset, free, locked, timestamp
            FROM balances 
            ORDER BY (free + locked) DESC
        ''')
        
        balances = cursor.fetchall()
        
        print("\n💰 BALANCES ACTUALES:")
        print("-" * 50)
        print(f"{'Asset':<8} {'Libre':<15} {'Bloqueado':<15} {'Total':<15}")
        print("-" * 50)
        
        for bal in balances:
            asset, free, locked, timestamp = bal
            total = free + locked
            if total > 0:
                print(f"{asset:<8} {free:<15.6f} {locked:<15.6f} {total:<15.6f}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error consultando balances: {e}")
        conn.close()

def mostrar_precios_recientes():
    """Mostrar precios recientes"""
    conn = conectar_bd()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT symbol, price, timestamp
            FROM precios_historicos 
            ORDER BY timestamp DESC
            LIMIT 10
        ''')
        
        precios = cursor.fetchall()
        
        print("\n📈 PRECIOS RECIENTES:")
        print("-" * 45)
        print(f"{'Symbol':<10} {'Precio':<15} {'Timestamp':<20}")
        print("-" * 45)
        
        for precio in precios:
            symbol, price, timestamp = precio
            print(f"{symbol:<10} ${price:<14.4f} {timestamp}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error consultando precios: {e}")
        conn.close()

def mostrar_configuracion():
    """Mostrar configuración actual"""
    conn = conectar_bd()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT clave, valor, timestamp
            FROM configuracion 
            ORDER BY clave
        ''')
        
        configs = cursor.fetchall()
        
        print("\n⚙️  CONFIGURACIÓN:")
        print("-" * 40)
        print(f"{'Clave':<20} {'Valor':<15}")
        print("-" * 40)
        
        for config in configs:
            clave, valor, timestamp = config
            print(f"{clave:<20} {valor:<15}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error consultando configuración: {e}")
        conn.close()

def agregar_operacion_simulada():
    """Agregar una operación simulada"""
    conn = conectar_bd()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # Operación de ejemplo
        nueva_op = (
            'BTCUSDT',
            'BUY',
            0.0005,
            115800.0,
            'completed',
            f'SIM{datetime.now().strftime("%Y%m%d%H%M%S")}',
            0.058  # 0.1% de comisión
        )
        
        cursor.execute('''
            INSERT INTO operaciones (symbol, side, quantity, price, status, order_id, commission)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', nueva_op)
        
        conn.commit()
        print(f"\n✅ Operación simulada agregada: {nueva_op[1]} {nueva_op[2]} {nueva_op[0]} @ ${nueva_op[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error agregando operación: {e}")
        conn.close()

def estadisticas_trading():
    """Mostrar estadísticas de trading"""
    conn = conectar_bd()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        print("\n📊 ESTADÍSTICAS DE TRADING:")
        print("=" * 40)
        
        # Total de operaciones
        cursor.execute('SELECT COUNT(*) FROM operaciones')
        total_ops = cursor.fetchone()[0]
        print(f"Total operaciones: {total_ops}")
        
        # Operaciones por estado
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM operaciones 
            GROUP BY status
        ''')
        estados = cursor.fetchall()
        print("\nPor estado:")
        for estado, count in estados:
            print(f"  {estado}: {count}")
        
        # Operaciones por símbolo
        cursor.execute('''
            SELECT symbol, COUNT(*), SUM(quantity * price) as volumen
            FROM operaciones 
            WHERE status = 'completed'
            GROUP BY symbol
            ORDER BY volumen DESC
        ''')
        simbolos = cursor.fetchall()
        print("\nPor símbolo (completadas):")
        for symbol, count, volumen in simbolos:
            print(f"  {symbol}: {count} ops, ${volumen:,.2f} volumen")
        
        # Comisiones totales
        cursor.execute('SELECT SUM(commission) FROM operaciones WHERE commission IS NOT NULL')
        total_comisiones = cursor.fetchone()[0] or 0
        print(f"\nComisiones totales: ${total_comisiones:.4f}")
        
        # Última actividad
        cursor.execute('SELECT MAX(timestamp) FROM operaciones')
        ultima_op = cursor.fetchone()[0]
        if ultima_op:
            print(f"Última operación: {ultima_op}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error calculando estadísticas: {e}")
        conn.close()

def menu_principal():
    """Mostrar menú principal"""
    while True:
        print("\n" + "=" * 50)
        print("🏦 GESTOR DE BASE DE DATOS DE TRADING")
        print("=" * 50)
        print("1. Ver operaciones")
        print("2. Ver balances")
        print("3. Ver precios recientes")
        print("4. Ver configuración")
        print("5. Agregar operación simulada")
        print("6. Ver estadísticas")
        print("7. Ver todo (resumen completo)")
        print("0. Salir")
        print("-" * 50)
        
        try:
            opcion = input("Selecciona una opción (0-7): ").strip()
            
            if opcion == '0':
                print("\n👋 ¡Hasta luego!")
                break
            elif opcion == '1':
                mostrar_operaciones()
            elif opcion == '2':
                mostrar_balances()
            elif opcion == '3':
                mostrar_precios_recientes()
            elif opcion == '4':
                mostrar_configuracion()
            elif opcion == '5':
                agregar_operacion_simulada()
            elif opcion == '6':
                estadisticas_trading()
            elif opcion == '7':
                mostrar_operaciones()
                mostrar_balances()
                mostrar_precios_recientes()
                mostrar_configuracion()
                estadisticas_trading()
            else:
                print("\n⚠️  Opción no válida. Intenta de nuevo.")
                
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

def main():
    """Función principal"""
    print("🚀 CONSULTOR DE BASE DE DATOS DE TRADING")
    
    # Verificar que existe la BD
    try:
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        if not tables:
            print("❌ La base de datos está vacía. Ejecuta primero test_bd_binance_simple.py")
            return False
        
        print(f"✅ Base de datos encontrada con {len(tables)} tablas")
        
    except Exception as e:
        print(f"❌ Error accediendo a la BD: {e}")
        print("   Ejecuta primero: python test_bd_binance_simple.py")
        return False
    
    # Mostrar menú
    menu_principal()
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n💥 Error inesperado: {e}")
        sys.exit(1)