#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICADOR DE BASES DE DATOS SICAR
===================================
Script para verificar el estado y funcionamiento de todas las bases de datos
"""

import sqlite3
import os
import pandas as pd
from datetime import datetime
import colorama
from colorama import Fore, Style

# Inicializar colorama
colorama.init()

def verificar_base_datos(db_path, nombre_db):
    """Verificar una base de datos específica"""
    print(f"\n{Fore.CYAN}🔍 VERIFICANDO: {nombre_db}")
    print(f"{Fore.CYAN}{'='*60}")
    
    if not os.path.exists(db_path):
        print(f"{Fore.RED}❌ Base de datos NO EXISTE: {db_path}")
        return False
    
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Obtener información del archivo
        file_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        file_modified = datetime.fromtimestamp(os.path.getmtime(db_path))
        
        print(f"{Fore.GREEN}✅ Base de datos EXISTE")
        print(f"{Fore.WHITE}📁 Ruta: {db_path}")
        print(f"{Fore.WHITE}📊 Tamaño: {file_size:.2f} MB")
        print(f"{Fore.WHITE}🕐 Última modificación: {file_modified}")
        
        # Obtener lista de tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = cursor.fetchall()
        
        print(f"{Fore.YELLOW}📋 Tablas encontradas: {len(tablas)}")
        
        for tabla in tablas:
            tabla_nombre = tabla[0]
            print(f"{Fore.WHITE}├─ {tabla_nombre}")
            
            # Contar registros en cada tabla
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla_nombre}")
                count = cursor.fetchone()[0]
                print(f"{Fore.WHITE}│  📊 Registros: {count}")
                
                # Mostrar últimos registros si existen
                if count > 0:
                    cursor.execute(f"SELECT * FROM {tabla_nombre} ORDER BY rowid DESC LIMIT 3")
                    ultimos = cursor.fetchall()
                    
                    # Obtener nombres de columnas
                    cursor.execute(f"PRAGMA table_info({tabla_nombre})")
                    columnas = [col[1] for col in cursor.fetchall()]
                    
                    print(f"{Fore.WHITE}│  🔍 Últimos registros:")
                    for i, registro in enumerate(ultimos):
                        print(f"{Fore.WHITE}│    {i+1}. {dict(zip(columnas[:3], registro[:3]))}")
                        
            except Exception as e:
                print(f"{Fore.RED}│  ❌ Error leyendo tabla: {e}")
        
        conn.close()
        print(f"{Fore.GREEN}✅ Verificación EXITOSA")
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error verificando base de datos: {e}")
        return False

def verificar_base_datos_fase2():
    """Verificar específicamente la base de datos de Fase 2"""
    db_path = "ia_continua_detecciones.db"
    
    print(f"\n{Fore.MAGENTA}🧠 VERIFICANDO BASE DE DATOS IA CONTINUA - FASE 2")
    print(f"{Fore.MAGENTA}{'='*60}")
    
    if not os.path.exists(db_path):
        print(f"{Fore.YELLOW}⚠️ Base de datos de Fase 2 NO EXISTE aún")
        print(f"{Fore.YELLOW}   Esto es normal si el sistema no ha detectado anomalías/patrones")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas esperadas
        tablas_esperadas = [
            'anomalias_detectadas',
            'patrones_detectados', 
            'analisis_xai'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas_existentes = [t[0] for t in cursor.fetchall()]
        
        print(f"{Fore.WHITE}📋 Tablas esperadas: {len(tablas_esperadas)}")
        print(f"{Fore.WHITE}📋 Tablas existentes: {len(tablas_existentes)}")
        
        for tabla in tablas_esperadas:
            if tabla in tablas_existentes:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"{Fore.GREEN}✅ {tabla}: {count} registros")
                
                # Mostrar último registro si existe
                if count > 0:
                    cursor.execute(f"SELECT * FROM {tabla} ORDER BY timestamp DESC LIMIT 1")
                    ultimo = cursor.fetchone()
                    print(f"{Fore.WHITE}   📅 Último registro: {ultimo[1] if len(ultimo) > 1 else 'N/A'}")
            else:
                print(f"{Fore.RED}❌ {tabla}: NO EXISTE")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error verificando BD Fase 2: {e}")
        return False

def main():
    """Función principal"""
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🔍 VERIFICADOR DE BASES DE DATOS SICAR")
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.WHITE}🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Lista de bases de datos a verificar
    bases_datos = [
        ("advanced_logging.db", "Sistema de Logging Avanzado"),
        ("proactive_monitoring.db", "Sistema de Monitoreo Proactivo"),
        ("ia_continua_detecciones.db", "IA Continua - Detecciones")
    ]
    
    resultados = []
    
    # Verificar cada base de datos
    for db_file, nombre in bases_datos:
        resultado = verificar_base_datos(db_file, nombre)
        resultados.append((nombre, resultado))
    
    # Verificación específica de Fase 2
    verificar_base_datos_fase2()
    
    # Resumen final
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}📊 RESUMEN DE VERIFICACIÓN")
    print(f"{Fore.CYAN}{'='*80}")
    
    for nombre, resultado in resultados:
        estado = f"{Fore.GREEN}✅ FUNCIONANDO" if resultado else f"{Fore.RED}❌ PROBLEMA"
        print(f"{Fore.WHITE}├─ {nombre}: {estado}")
    
    # Verificar si el sistema de Fase 2 está funcionando
    print(f"\n{Fore.MAGENTA}🧠 ESTADO SISTEMA IA CONTINUA:")
    
    # Verificar si hay procesos activos
    try:
        import psutil
        procesos_ia = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and any('ia_continua' in str(cmd) for cmd in proc.info['cmdline']):
                    procesos_ia.append(proc.info)
            except:
                pass
        
        if procesos_ia:
            print(f"{Fore.GREEN}✅ Sistema IA Continua ACTIVO ({len(procesos_ia)} procesos)")
            for proc in procesos_ia:
                print(f"{Fore.WHITE}   PID {proc['pid']}: {proc['name']}")
        else:
            print(f"{Fore.YELLOW}⚠️ No se detectaron procesos IA Continua activos")
            
    except ImportError:
        print(f"{Fore.YELLOW}⚠️ No se puede verificar procesos (psutil no disponible)")
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.GREEN}✅ Verificación completada")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()