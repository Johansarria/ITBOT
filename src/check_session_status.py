"""
Script para verificar el estado actual de las sesiones de trading
"""

from session_detector import SessionDetector
from datetime import datetime
import pytz

def check_current_status():
    print("🔍 VERIFICANDO ESTADO ACTUAL DEL SISTEMA")
    print("=" * 50)
    
    # Inicializar detector de sesiones
    session_detector = SessionDetector()
    
    # Obtener hora actual
    est = pytz.timezone('US/Eastern')
    current_time = datetime.now(est)
    
    print(f"⏰ Hora actual EST: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print()
    
    # Verificar sesión actual
    current_session = session_detector.get_current_session()
    
    if current_session:
        print("✅ SESIÓN ACTIVA DETECTADA:")
        print(f"   Nombre: {current_session['name']}")
        print(f"   Descripción: {current_session['description']}")
        print(f"   Horario: {current_session['start']} - {current_session['end']} EST")
        print(f"   Activa: {current_session['active']}")
    else:
        print("❌ NO HAY SESIÓN ACTIVA ACTUALMENTE")
    
    print()
    
    # Mostrar todas las sesiones configuradas
    print("📋 SESIONES CONFIGURADAS:")
    sessions = session_detector.sessions_config
    active_sessions = session_detector.get_active_sessions()
    
    for session_id, session_config in sessions.items():
        is_active = session_id in active_sessions
        status = "🟢 ACTIVA" if is_active else "🔴 INACTIVA"
        print(f"   {status} - {session_config['name']}")
        print(f"      Horario: {session_config['start_time']} - {session_config['end_time']} EST")
        print(f"      Descripción: {session_config['description']}")
        print()
    
    # Mostrar reporte de estado
    print("📊 REPORTE DE ESTADO:")
    status_report = session_detector.get_session_status_report()
    for key, value in status_report.items():
        print(f"   {key}: {value}")
    print()

if __name__ == "__main__":
    check_current_status()