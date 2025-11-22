#!/usr/bin/env python3
import sqlite3
import os
from datetime import datetime, timedelta

def consultar_base_datos(db_file, descripcion):
    if not os.path.exists(db_file):
        print(f"❌ {descripcion}: Base de datos no encontrada - {db_file}")
        return
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Obtener tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tablas = cursor.fetchall()
        print(f"\n📊 {descripcion}")
        print(f"   Archivo: {db_file}")
        print(f"   Tablas: {[t[0] for t in tablas]}")
        
        # Consultar datos recientes según la tabla
        for tabla in tablas:
            tabla_name = tabla[0]
            try:
                # Obtener estructura de la tabla
                cursor.execute(f"PRAGMA table_info({tabla_name})")
                columnas = cursor.fetchall()
                columnas_nombres = [col[1] for col in columnas]
                
                # Buscar columna de timestamp
                timestamp_col = None
                for col in ['timestamp', 'created_at', 'date', 'time']:
                    if col in columnas_nombres:
                        timestamp_col = col
                        break
                
                if timestamp_col:
                    # Contar registros últimas 24h
                    cursor.execute(f"SELECT COUNT(*) FROM {tabla_name} WHERE {timestamp_col} >= datetime('now', '-1 day')")
                    count_24h = cursor.fetchone()[0]
                    
                    # Obtener últimos registros
                    cursor.execute(f"SELECT * FROM {tabla_name} WHERE {timestamp_col} >= datetime('now', '-1 day') ORDER BY {timestamp_col} DESC LIMIT 5")
                    registros = cursor.fetchall()
                    
                    print(f"   📈 Tabla {tabla_name}: {count_24h} registros últimas 24h")
                    if registros:
                        print(f"      Últimos registros:")
                        for reg in registros:
                            print(f"        {reg}")
                else:
                    # Si no hay timestamp, mostrar total
                    cursor.execute(f"SELECT COUNT(*) FROM {tabla_name}")
                    total = cursor.fetchone()[0]
                    print(f"   📊 Tabla {tabla_name}: {total} registros totales")
                    
                    if total > 0:
                        cursor.execute(f"SELECT * FROM {tabla_name} ORDER BY rowid DESC LIMIT 3")
                        registros = cursor.fetchall()
                        print(f"      Últimos registros:")
                        for reg in registros:
                            print(f"        {reg}")
                            
            except Exception as e:
                print(f"   ❌ Error consultando tabla {tabla_name}: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error consultando {descripcion}: {e}")

def main():
    print("🔍 ANÁLISIS DE LOGS Y BASES DE DATOS - ÚLTIMAS 24 HORAS")
    print("=" * 60)
    
    # Bases de datos a consultar
    bases_datos = [
        ("analisis_rompimientos_tiempo_real.db", "Análisis de Rompimientos"),
        ("analisis_mercado_tiempo_real.db", "Análisis de Mercado"),
        ("alertas_database.db", "Alertas Inteligentes"),
        ("detector_rupturas_velas.db", "Detector de Rupturas de Velas"),
        ("ia_continua_detecciones.db", "IA Continua Detecciones"),
        ("market_preparation.db", "Preparación de Mercado"),
        ("proactive_monitoring.db", "Monitoreo Proactivo"),
        ("advanced_logging.db", "Logging Avanzado")
    ]
    
    for db_file, descripcion in bases_datos:
        consultar_base_datos(db_file, descripcion)
    
    print("\n" + "=" * 60)
    print("✅ Análisis completado")

if __name__ == "__main__":
    main()