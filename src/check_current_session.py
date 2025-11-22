"""
Verificador simple de sesión actual
"""

from session_detector import SessionDetector
from datetime import datetime
import pytz

def check_now():
    detector = SessionDetector()
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    
    print(f"🕐 Hora actual: {now.strftime('%H:%M:%S')} EST")
    
    current_session = detector.get_current_session()
    
    if current_session:
        print(f"✅ SESIÓN ACTIVA: {current_session}")
        
        # Obtener info de la sesión
        if current_session == "Sesión Asiática":
            print("🌏 ¡SESIÓN ASIÁTICA EN PROGRESO!")
            print("   Ventana: 19:00 - 19:05 EST")
            print("   Duración: 5 minutos")
            print("   Símbolo: ETHUSDT")
            print("   Estrategia: First Candle Breakout")
    else:
        print("❌ No hay sesión activa")
    
    # Verificar próxima sesión
    next_session = detector.get_next_session()
    if next_session:
        print(f"\n⏭️ Próxima sesión: {next_session['session']}")
        print(f"   En {next_session['wait_minutes']} minutos")

if __name__ == "__main__":
    check_now()