"""
Calculadora de próxima sesión de trading automático
"""

import pytz
from datetime import datetime, timedelta

def calculate_next_session():
    # Configurar zonas horarias
    est = pytz.timezone('US/Eastern')
    
    # Obtener hora actual EST
    now_est = datetime.now(est)
    current_time = now_est.strftime("%H:%M:%S")
    
    print(f"Hora actual EST: {current_time}")
    print()
    
    # Configuración de sesiones (igual que en session_detector.py)
    sessions = {
        'european': {'start': '03:00', 'end': '03:05', 'name': 'Sesión Europea'},
        'american': {'start': '09:30', 'end': '09:35', 'name': 'Sesión Americana'},
        'asian': {'start': '19:00', 'end': '19:05', 'name': 'Sesión Asiática'}
    }
    
    # Encontrar la próxima sesión
    next_sessions = []
    
    for session_name, config in sessions.items():
        start_hour, start_minute = map(int, config['start'].split(':'))
        
        # Crear datetime para hoy
        session_today = now_est.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
        
        # Si ya pasó hoy, programar para mañana
        if session_today <= now_est:
            session_next = session_today + timedelta(days=1)
        else:
            session_next = session_today
            
        # Calcular tiempo restante
        time_remaining = session_next - now_est
        hours = int(time_remaining.total_seconds() // 3600)
        minutes = int((time_remaining.total_seconds() % 3600) // 60)
        
        next_sessions.append({
            'name': config['name'],
            'datetime': session_next,
            'time_remaining_hours': hours,
            'time_remaining_minutes': minutes,
            'total_minutes': int(time_remaining.total_seconds() // 60)
        })
    
    # Ordenar por tiempo restante
    next_sessions.sort(key=lambda x: x['total_minutes'])
    
    # Mostrar la próxima sesión
    next_session = next_sessions[0]
    
    print("🚀 PRÓXIMA OPERACIÓN AUTOMÁTICA:")
    print(f"   Sesión: {next_session['name']}")
    print(f"   Fecha y hora EST: {next_session['datetime'].strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"   Tiempo restante: {next_session['time_remaining_hours']} horas y {next_session['time_remaining_minutes']} minutos")
    print()
    
    # Mostrar todas las sesiones del día
    print("📅 TODAS LAS SESIONES PROGRAMADAS:")
    for session in next_sessions:
        status = "⏰ PRÓXIMA" if session == next_session else "⏳ SIGUIENTE"
        print(f"   {status} - {session['name']}")
        print(f"      {session['datetime'].strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"      En {session['time_remaining_hours']}h {session['time_remaining_minutes']}m")
        print()

if __name__ == "__main__":
    calculate_next_session()