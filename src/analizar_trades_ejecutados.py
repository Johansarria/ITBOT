#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

def analizar_trades_ejecutados():
    """Analiza todos los trades ejecutados en el sistema SICAR"""
    
    print('=== ANÁLISIS DE TRADES EJECUTADOS ===\n')

    # 1. Revisar base de datos de auto trading
    try:
        if os.path.exists('auto_trading_alerts.db'):
            conn = sqlite3.connect('auto_trading_alerts.db')
            cursor = conn.cursor()
            
            # Obtener estructura de la tabla
            cursor.execute("PRAGMA table_info(executed_trades)")
            columns = cursor.fetchall()
            print('📊 ESTRUCTURA DE TABLA executed_trades:')
            for col in columns:
                print(f'   {col[1]} ({col[2]})')
            
            # Obtener todos los trades
            cursor.execute('SELECT * FROM executed_trades ORDER BY timestamp DESC')
            trades = cursor.fetchall()
            
            print(f'\n💰 TRADES EJECUTADOS: {len(trades)} total')
            
            if trades:
                print('\n📋 DETALLE DE TRADES:')
                for i, trade in enumerate(trades, 1):
                    print(f'\n--- TRADE {i} ---')
                    print(f'ID: {trade[0]}')
                    print(f'Signal ID: {trade[1]}')
                    print(f'Símbolo: {trade[2]}')
                    print(f'Lado: {trade[3]}')
                    print(f'Cantidad: {trade[4]}')
                    print(f'Precio entrada: ${trade[5]}')
                    print(f'Stop Loss: ${trade[6]}')
                    print(f'Take Profit: ${trade[7]}')
                    print(f'Timestamp: {trade[8]}')
                    print(f'Estado: {trade[9]}')
                    if len(trade) > 10 and trade[10]:  # exit_price
                        print(f'Precio salida: ${trade[10]}')
                    if len(trade) > 11 and trade[11]:  # exit_timestamp
                        print(f'Timestamp salida: {trade[11]}')
                    if len(trade) > 12 and trade[12]:  # pnl
                        print(f'PnL: ${trade[12]}')
                    if len(trade) > 13 and trade[13]:  # close_reason
                        print(f'Razón cierre: {trade[13]}')
            
            conn.close()
        else:
            print('❌ No existe auto_trading_alerts.db')
        
    except Exception as e:
        print(f'❌ Error accediendo a auto_trading_alerts.db: {e}')

    print('\n' + '='*50)

    # 2. Revisar logs de trades en formato JSONL
    try:
        trades_file = '../logs/trades_data.jsonl'
        if os.path.exists(trades_file):
            print('\n📄 TRADES EN LOGS JSONL:')
            with open(trades_file, 'r', encoding='utf-8') as f:
                trades_count = 0
                for line in f:
                    if line.strip():
                        try:
                            trade = json.loads(line)
                            trades_count += 1
                            print(f'\nTrade {trades_count}:')
                            print(f'  Timestamp: {trade.get("timestamp", "N/A")}')
                            print(f'  Símbolo: {trade.get("symbol", "N/A")}')
                            print(f'  Tipo: {trade.get("event_type", "N/A")}')
                            if 'trade_info' in trade:
                                info = trade['trade_info']
                                print(f'  Precio: ${info.get("entry_price", 0)}')
                                print(f'  Cantidad: {info.get("position_size", 0)}')
                                print(f'  Lado: {info.get("position_type", "N/A")}')
                        except json.JSONDecodeError as e:
                            print(f'  Error decodificando línea: {e}')
            print(f'\nTotal trades en JSONL: {trades_count}')
        else:
            print('\n📄 No existe archivo trades_data.jsonl')
            
    except Exception as e:
        print(f'❌ Error leyendo trades_data.jsonl: {e}')

    print('\n' + '='*50)

    # 3. Revisar enhanced_trading.db
    try:
        if os.path.exists('enhanced_trading.db'):
            conn = sqlite3.connect('enhanced_trading.db')
            cursor = conn.cursor()
            
            # Listar tablas
            cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
            tables = cursor.fetchall()
            print(f'\n🗄️ TABLAS EN enhanced_trading.db: {[t[0] for t in tables]}')
            
            # Buscar tablas relacionadas con trades
            for table in tables:
                table_name = table[0]
                if 'trade' in table_name.lower() or 'execution' in table_name.lower():
                    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                    count = cursor.fetchone()[0]
                    print(f'   {table_name}: {count} registros')
                    
                    if count > 0:
                        cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
                        records = cursor.fetchall()
                        print(f'   Primeros registros: {records}')
            
            conn.close()
        else:
            print('\n🗄️ No existe enhanced_trading.db')
            
    except Exception as e:
        print(f'❌ Error accediendo a enhanced_trading.db: {e}')

    print('\n' + '='*50)

    # 4. Revisar advanced_logging.db para trade executions
    try:
        if os.path.exists('advanced_logging.db'):
            conn = sqlite3.connect('advanced_logging.db')
            cursor = conn.cursor()
            
            # Buscar tabla de trade executions
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%trade%' OR name LIKE '%execution%'")
            trade_tables = cursor.fetchall()
            
            if trade_tables:
                print(f'\n🗄️ TABLAS DE TRADES EN advanced_logging.db: {[t[0] for t in trade_tables]}')
                
                for table in trade_tables:
                    table_name = table[0]
                    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                    count = cursor.fetchone()[0]
                    print(f'   {table_name}: {count} registros')
                    
                    if count > 0:
                        # Obtener estructura
                        cursor.execute(f'PRAGMA table_info({table_name})')
                        columns = cursor.fetchall()
                        print(f'   Columnas: {[col[1] for col in columns]}')
                        
                        # Obtener algunos registros
                        cursor.execute(f'SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 5')
                        records = cursor.fetchall()
                        for i, record in enumerate(records, 1):
                            print(f'   Registro {i}: {record}')
            else:
                print('\n🗄️ No hay tablas de trades en advanced_logging.db')
            
            conn.close()
        else:
            print('\n🗄️ No existe advanced_logging.db')
            
    except Exception as e:
        print(f'❌ Error accediendo a advanced_logging.db: {e}')

    print('\n' + '='*50)

    # 5. Revisar logs de texto detallados
    try:
        trades_detailed_file = '../logs/trades_detailed.log'
        if os.path.exists(trades_detailed_file):
            print('\n📄 TRADES DETAILED LOG:')
            with open(trades_detailed_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                print(f'   Total líneas: {len(lines)}')
                
                # Buscar entradas de trades
                trade_entries = [line for line in lines if 'ENTRADA DE OPERACIÓN' in line or 'TRADE EJECUTADO' in line]
                print(f'   Entradas de trades encontradas: {len(trade_entries)}')
                
                if trade_entries:
                    print('\n   Últimas entradas:')
                    for entry in trade_entries[-3:]:
                        print(f'   {entry}')
        else:
            print('\n📄 No existe trades_detailed.log')
            
    except Exception as e:
        print(f'❌ Error leyendo trades_detailed.log: {e}')

    print('\n' + '='*50)
    print('✅ ANÁLISIS COMPLETADO')

if __name__ == "__main__":
    analizar_trades_ejecutados()