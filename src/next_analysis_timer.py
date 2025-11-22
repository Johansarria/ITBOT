#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CALCULADORA DE PRÓXIMO ANÁLISIS
===============================
Script para calcular tiempo exacto hasta el próximo análisis de primera vela
"""

import json
from datetime import datetime, timedelta
import pytz

def load_config():
    """Carga configuración del sistema"""
    try:
        with open('first_candle_strategy_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def calculate_next_analysis():
    """Calcula tiempo hasta el próximo análisis"""
    config = load_config()
    
    # Hora actual en UTC
    utc_now = datetime.now(pytz.UTC)
    session_hour = config.get('strategy_parameters', {}).get('session_start_hour', 8)
    
    print("=" * 60)
    print("⏰ CALCULADORA DE PRÓXIMO ANÁLISIS")
    print("=" * 60)
    print(f"🕐 Hora actual (UTC): {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Hora de análisis: {session_hour}:00 UTC diariamente")
    
    # Próximo análisis hoy
    next_analysis_today = utc_now.replace(hour=session_hour, minute=0, second=0, microsecond=0)
    
    # Si ya pasó la hora de hoy, calcular para mañana
    if utc_now >= next_analysis_today:
        next_analysis = next_analysis_today + timedelta(days=1)
        print(f"📅 Estado: Ya pasó el análisis de hoy")
    else:
        next_analysis = next_analysis_today
        print(f"📅 Estado: Esperando análisis de hoy")
    
    # Calcular tiempo restante
    time_remaining = next_analysis - utc_now
    total_seconds = int(time_remaining.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    print(f"🚀 Próximo análisis: {next_analysis.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)
    print("⏳ TIEMPO RESTANTE:")
    print(f"   {hours:02d} horas, {minutes:02d} minutos, {seconds:02d} segundos")
    print("=" * 60)
    
    # Conversiones a otras zonas horarias
    print("🌍 PRÓXIMO ANÁLISIS EN OTRAS ZONAS:")
    
    # Zona horaria de Colombia (UTC-5)
    colombia_tz = pytz.timezone('America/Bogota')
    next_analysis_colombia = next_analysis.astimezone(colombia_tz)
    print(f"🇨🇴 Colombia:  {next_analysis_colombia.strftime('%Y-%m-%d %H:%M:%S')} COT")
    
    # Zona horaria de España (UTC+1)
    spain_tz = pytz.timezone('Europe/Madrid')
    next_analysis_spain = next_analysis.astimezone(spain_tz)
    print(f"🇪🇸 España:    {next_analysis_spain.strftime('%Y-%m-%d %H:%M:%S')} CET")
    
    # Zona horaria de Nueva York (UTC-5)
    ny_tz = pytz.timezone('America/New_York')
    next_analysis_ny = next_analysis.astimezone(ny_tz)
    print(f"🇺🇸 New York:  {next_analysis_ny.strftime('%Y-%m-%d %H:%M:%S')} EST")
    
    print("=" * 60)
    
    # Información adicional
    print("📊 INFORMACIÓN DEL ANÁLISIS:")
    symbols = config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'])
    print(f"🎯 Símbolos a analizar: {', '.join(symbols)}")
    print(f"📈 Umbral de breakout: {config.get('strategy_parameters', {}).get('breakout_threshold', 0.008)*100:.1f}%")
    print(f"📊 Volumen mínimo: {config.get('strategy_parameters', {}).get('min_volume_ratio', 1.1):.1f}x promedio")
    print(f"💰 Capital actual: ${config.get('capital_management', {}).get('initial_capital', 250):.2f}")
    print("=" * 60)

if __name__ == "__main__":
    calculate_next_analysis()