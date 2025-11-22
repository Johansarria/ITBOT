#!/usr/bin/env python3
"""
Script para verificar el estado exacto de las posiciones en la base de datos
y diagnosticar por qué el sistema sigue mostrando posiciones activas.
"""

import sqlite3
import json
from datetime import datetime

def verify_database_status():
    """Verifica el estado exacto de todas las posiciones en la base de datos"""
    
    db_path = "auto_trading_alerts.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 VERIFICACIÓN COMPLETA DEL ESTADO DE LA BASE DE DATOS")
        print("=" * 60)
        
        # 1. Verificar estructura de la tabla
        cursor.execute("PRAGMA table_info(executed_trades)")
        columns = cursor.fetchall()
        print("\n📋 ESTRUCTURA DE LA TABLA executed_trades:")
        for col in columns:
            print(f"  • {col[1]} ({col[2]})")
        
        # 2. Obtener todas las posiciones con todos los campos
        cursor.execute("""
            SELECT id, symbol, side, quantity, entry_price, stop_loss, take_profit, 
                   timestamp, status, exit_price, exit_timestamp, pnl, close_reason
            FROM executed_trades
            ORDER BY id
        """)
        
        positions = cursor.fetchall()
        
        print(f"\n📊 TOTAL DE REGISTROS EN LA BASE DE DATOS: {len(positions)}")
        print("\n📈 DETALLE COMPLETO DE TODAS LAS POSICIONES:")
        print("-" * 80)
        
        active_count = 0
        closed_count = 0
        
        for pos in positions:
            id_val, symbol, side, quantity, entry_price, stop_loss, take_profit, timestamp, status, exit_price, exit_timestamp, pnl, close_reason = pos
            
            print(f"\n🔸 POSICIÓN ID: {id_val}")
            print(f"  Symbol: {symbol}")
            print(f"  Side: {side}")
            print(f"  Quantity: {quantity}")
            print(f"  Entry Price: {entry_price}")
            print(f"  Stop Loss: {stop_loss}")
            print(f"  Take Profit: {take_profit}")
            print(f"  Timestamp: {timestamp}")
            print(f"  STATUS: '{status}' (tipo: {type(status)})")
            print(f"  Exit Price: {exit_price}")
            print(f"  Exit Timestamp: {exit_timestamp}")
            print(f"  PnL: {pnl}")
            print(f"  Close Reason: {close_reason}")
            
            # Contar por estado
            if status == 'ACTIVE':
                active_count += 1
            elif status == 'CLOSED':
                closed_count += 1
            else:
                print(f"  ⚠️ ESTADO DESCONOCIDO: '{status}'")
        
        print(f"\n📊 RESUMEN DE ESTADOS:")
        print(f"  • Posiciones ACTIVE: {active_count}")
        print(f"  • Posiciones CLOSED: {closed_count}")
        
        # 3. Verificar específicamente posiciones activas
        cursor.execute("SELECT COUNT(*) FROM executed_trades WHERE status = 'ACTIVE'")
        active_by_query = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM executed_trades WHERE status = 'CLOSED'")
        closed_by_query = cursor.fetchone()[0]
        
        print(f"\n🔍 VERIFICACIÓN POR CONSULTA SQL:")
        print(f"  • SELECT COUNT(*) WHERE status = 'ACTIVE': {active_by_query}")
        print(f"  • SELECT COUNT(*) WHERE status = 'CLOSED': {closed_by_query}")
        
        # 4. Verificar posibles problemas de espacios o caracteres especiales
        cursor.execute("SELECT DISTINCT status FROM executed_trades")
        unique_statuses = cursor.fetchall()
        
        print(f"\n📋 ESTADOS ÚNICOS EN LA BASE DE DATOS:")
        for status_tuple in unique_statuses:
            status = status_tuple[0]
            print(f"  • '{status}' (longitud: {len(status)}, repr: {repr(status)})")
        
        # 5. Generar reporte
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_positions": len(positions),
            "active_positions": active_count,
            "closed_positions": closed_count,
            "active_by_query": active_by_query,
            "closed_by_query": closed_by_query,
            "unique_statuses": [status[0] for status in unique_statuses],
            "positions_detail": []
        }
        
        for pos in positions:
            report["positions_detail"].append({
                "id": pos[0],
                "symbol": pos[1],
                "side": pos[2],
                "status": pos[8],
                "exit_price": pos[9],
                "close_reason": pos[12]
            })
        
        # Guardar reporte
        with open("database_status_verification.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Reporte guardado en: database_status_verification.json")
        
        conn.close()
        
        # Diagnóstico
        print(f"\n🔧 DIAGNÓSTICO:")
        if active_by_query > 0:
            print(f"  ⚠️ HAY {active_by_query} POSICIONES CON STATUS 'ACTIVE' EN LA BASE DE DATOS")
            print(f"  📝 Esto explica por qué el sistema muestra posiciones activas")
        else:
            print(f"  ✅ NO HAY POSICIONES CON STATUS 'ACTIVE' EN LA BASE DE DATOS")
            print(f"  🤔 El problema puede estar en el código de gestión de riesgo")
        
        return report
        
    except Exception as e:
        print(f"❌ Error verificando la base de datos: {e}")
        return None

if __name__ == "__main__":
    verify_database_status()