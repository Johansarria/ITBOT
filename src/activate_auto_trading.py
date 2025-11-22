"""
Script para activar auto trading y monitorear actividad
"""

import json
import time
from datetime import datetime
import pytz
from session_detector import SessionDetector

def activate_auto_trading():
    """Activar auto trading en el archivo de sesión"""
    
    # Leer archivo actual
    with open('paper_trading_session.json', 'r') as f:
        session_data = json.load(f)
    
    # Activar auto trading
    session_data['auto_trading'] = True
    session_data['timestamp'] = datetime.now().isoformat()
    
    # Guardar cambios
    with open('paper_trading_session.json', 'w') as f:
        json.dump(session_data, f, indent=2)
    
    print("✅ Auto trading ACTIVADO")
    print(f"📊 Estado actual: {session_data}")

def monitor_remaining_session():
    """Monitorear los minutos restantes de la sesión"""
    detector = SessionDetector()
    est = pytz.timezone('US/Eastern')
    
    print("\n🔍 MONITOREANDO SESIÓN ASIÁTICA...")
    print("=" * 50)
    
    for i in range(10):  # Monitorear por 10 ciclos (aprox 3 minutos)
        now = datetime.now(est)
        current_session = detector.get_current_session()
        
        print(f"\n⏰ {now.strftime('%H:%M:%S')} EST")
        
        if current_session:
            print(f"✅ Sesión activa: {current_session}")
            
            # Verificar si estamos en ventana asiática
            if now.hour == 19 and now.minute < 5:
                remaining = 5 - now.minute
                print(f"🌏 SESIÓN ASIÁTICA - {remaining} minutos restantes")
            else:
                print("❌ Sesión asiática terminada")
                break
        else:
            print("❌ No hay sesión activa")
            break
        
        # Verificar archivo de sesión
        try:
            with open('paper_trading_session.json', 'r') as f:
                session_data = json.load(f)
            
            print(f"💰 Capital: ${session_data.get('capital', 0):,.2f}")
            print(f"📈 Trades: {session_data.get('total_trades', 0)}")
            print(f"🤖 Auto trading: {session_data.get('auto_trading', False)}")
            
        except Exception as e:
            print(f"❌ Error leyendo sesión: {e}")
        
        time.sleep(20)  # Esperar 20 segundos

if __name__ == "__main__":
    activate_auto_trading()
    monitor_remaining_session()