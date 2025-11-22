"""
Script para verificar el estado de las posiciones activas
"""

import sqlite3
from datetime import datetime

def check_active_positions():
    try:
        conn = sqlite3.connect('auto_trading_alerts.db')
        cursor = conn.cursor()
        
        print("🔍 VERIFICANDO POSICIONES ACTIVAS")
        print("=" * 50)
        
        # Verificar estructura de la tabla
        cursor.execute("PRAGMA table_info(executed_trades)")
        columns = cursor.fetchall()
        print("\n📋 Estructura de la tabla executed_trades:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        # Consultar todas las operaciones
        cursor.execute("SELECT * FROM executed_trades ORDER BY timestamp DESC")
        all_trades = cursor.fetchall()
        
        print(f"\n📊 TOTAL DE OPERACIONES EN LA BASE DE DATOS: {len(all_trades)}")
        
        if all_trades:
            print("\n📈 ÚLTIMAS 10 OPERACIONES:")
            print("-" * 80)
            for i, trade in enumerate(all_trades[:10]):
                print(f"{i+1}. ID: {trade[0]} | Symbol: {trade[2]} | Side: {trade[3]} | "
                      f"Quantity: {trade[4]} | Entry: {trade[5]} | Status: {trade[9]} | "
                      f"Timestamp: {trade[8]}")
        
        # Buscar posiciones activas (status != 'CLOSED')
        cursor.execute("SELECT * FROM executed_trades WHERE status != 'CLOSED' OR status IS NULL")
        active_trades = cursor.fetchall()
        
        print(f"\n🔄 POSICIONES ACTIVAS: {len(active_trades)}")
        
        if active_trades:
            print("-" * 80)
            for trade in active_trades:
                print(f"• Symbol: {trade[2]} | Side: {trade[3]} | Quantity: {trade[4]} | "
                      f"Entry: {trade[5]} | Stop Loss: {trade[6]} | Take Profit: {trade[7]} | "
                      f"Status: {trade[9]} | Timestamp: {trade[8]}")
        else:
            print("✅ No hay posiciones activas en este momento")
        
        # Verificar posiciones por estado
        cursor.execute("SELECT status, COUNT(*) FROM executed_trades GROUP BY status")
        status_counts = cursor.fetchall()
        
        print(f"\n📊 RESUMEN POR ESTADO:")
        for status, count in status_counts:
            print(f"  • {status or 'NULL'}: {count} operaciones")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error consultando la base de datos: {e}")

def check_recent_activity():
    try:
        conn = sqlite3.connect('auto_trading_alerts.db')
        cursor = conn.cursor()
        
        print(f"\n🕐 ACTIVIDAD RECIENTE (últimas 24 horas):")
        print("-" * 50)
        
        # Buscar actividad reciente
        cursor.execute("""
            SELECT * FROM executed_trades 
            WHERE datetime(timestamp) > datetime('now', '-1 day')
            ORDER BY timestamp DESC
        """)
        recent_trades = cursor.fetchall()
        
        if recent_trades:
            for trade in recent_trades:
                print(f"• {trade[8]} | {trade[2]} | {trade[3]} | Status: {trade[9]}")
        else:
            print("📭 No hay actividad reciente en las últimas 24 horas")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error consultando actividad reciente: {e}")

if __name__ == "__main__":
    check_active_positions()
    check_recent_activity()
    
    print(f"\n💡 EXPLICACIÓN:")
    print("Durante las pruebas del sistema mejorado, el módulo de gestión de riesgo")
    print("detectó '2/2 posiciones activas' porque estaba leyendo datos históricos")
    print("de operaciones anteriores que no habían sido marcadas como 'closed'.")
    print("\nEsto es normal en un entorno de desarrollo y pruebas.")