#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNÓSTICO DE TIMING - SISTEMA PRIMERA VELA
===========================================
Script para diagnosticar por qué no se ejecutó el análisis de primera vela
"""

import json
import logging
from datetime import datetime, timedelta
import pytz

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config():
    """Carga la configuración"""
    try:
        with open('first_candle_strategy_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error cargando configuración: {e}")
        return None

def analyze_timing():
    """Analiza el timing del sistema"""
    config = load_config()
    if not config:
        return
    
    session_hour = config['strategy_parameters']['session_start_hour']
    
    print("="*60)
    print("DIAGNÓSTICO DE TIMING - SISTEMA PRIMERA VELA")
    print("="*60)
    
    # Hora actual
    now_utc = datetime.now(pytz.UTC)
    now_local = datetime.now()
    
    print(f"Hora actual UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Hora actual local: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Hora configurada para análisis: {session_hour}:00 UTC")
    
    # Verificar si es la hora de análisis
    is_analysis_hour = now_utc.hour == session_hour
    print(f"¿Es hora de análisis ahora?: {is_analysis_hour}")
    
    # Calcular próximo análisis
    today_analysis = now_utc.replace(hour=session_hour, minute=0, second=0, microsecond=0)
    
    if now_utc.hour >= session_hour:
        # Ya pasó hoy, próximo es mañana
        next_analysis = today_analysis + timedelta(days=1)
        analysis_passed_today = True
    else:
        # Aún no ha llegado hoy
        next_analysis = today_analysis
        analysis_passed_today = False
    
    print(f"Análisis de hoy ({today_analysis.strftime('%Y-%m-%d %H:%M:%S UTC')}): {'YA PASÓ' if analysis_passed_today else 'AÚN NO LLEGA'}")
    print(f"Próximo análisis: {next_analysis.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Tiempo hasta próximo análisis
    time_until_next = next_analysis - now_utc
    hours, remainder = divmod(time_until_next.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    print(f"Tiempo hasta próximo análisis: {int(hours)}h {int(minutes)}m {int(seconds)}s")
    
    print("\n" + "="*60)
    print("ANÁLISIS DE LOGS")
    print("="*60)
    
    # Revisar logs del día
    try:
        with open('real_time_first_candle.log', 'r', encoding='utf-8') as f:
            logs = f.readlines()
        
        today_str = now_utc.strftime('%Y-%m-%d')
        today_logs = [log for log in logs if today_str in log]
        
        print(f"Logs de hoy ({today_str}): {len(today_logs)} entradas")
        
        if today_logs:
            print("\nÚltimos logs de hoy:")
            for log in today_logs[-5:]:
                print(f"  {log.strip()}")
        
        # Buscar logs de análisis
        analysis_logs = [log for log in logs if 'primera vela' in log.lower() or 'breakout' in log.lower() or 'señal' in log.lower()]
        print(f"\nLogs de análisis encontrados: {len(analysis_logs)}")
        
        if analysis_logs:
            print("Últimos logs de análisis:")
            for log in analysis_logs[-3:]:
                print(f"  {log.strip()}")
        
    except FileNotFoundError:
        print("Archivo de logs no encontrado")
    except Exception as e:
        print(f"Error leyendo logs: {e}")
    
    print("\n" + "="*60)
    print("VERIFICACIÓN DE SISTEMA")
    print("="*60)
    
    # Verificar datos de sesión
    try:
        with open('real_time_session_data.json', 'r', encoding='utf-8') as f:
            session_data = json.load(f)
        
        print(f"Capital actual: ${session_data.get('current_capital', 0):.2f}")
        print(f"Trades totales: {len(session_data.get('trades_history', []))}")
        print(f"Trades de hoy: {session_data.get('session_trades_count', 0)}")
        print(f"Posiciones abiertas: {len([p for p in session_data.get('positions', {}).values() if p.get('status') == 'OPEN'])}")
        
        last_update = session_data.get('timestamp', 'N/A')
        print(f"Última actualización: {last_update}")
        
    except FileNotFoundError:
        print("Archivo de datos de sesión no encontrado")
    except Exception as e:
        print(f"Error leyendo datos de sesión: {e}")
    
    print("\n" + "="*60)
    print("CONCLUSIONES")
    print("="*60)
    
    if analysis_passed_today:
        print("❌ El análisis de hoy YA PASÓ (08:00 UTC)")
        print("❌ El sistema se inició DESPUÉS de la hora de análisis")
        print("✅ El próximo análisis será mañana a las 08:00 UTC")
    else:
        print("⏳ El análisis de hoy AÚN NO HA LLEGADO")
        print("✅ El sistema está esperando la hora correcta")
    
    print(f"⚠️  IMPORTANTE: El sistema debe estar ejecutándose a las {session_hour}:00 UTC para detectar señales")
    print("⚠️  Si el sistema se detiene y reinicia, perderá la oportunidad de análisis del día")

if __name__ == "__main__":
    analyze_timing()