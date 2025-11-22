"""
Verificador de configuración del dashboard
"""

import json
import os
from datetime import datetime
import pytz

def check_config():
    print("🔍 ANÁLISIS DE CONFIGURACIÓN DEL DASHBOARD")
    print("=" * 50)
    
    # 1. Verificar archivo de sesión
    session_file = "paper_trading_session.json"
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        print("📊 ESTADO DEL PAPER TRADING:")
        print(f"   💰 Capital: ${session_data.get('capital', 0):,.2f}")
        print(f"   📈 Posiciones: {session_data.get('positions', 0)}")
        print(f"   🔄 Total trades: {session_data.get('total_trades', 0)}")
        print(f"   🤖 Auto trading: {session_data.get('auto_trading', False)}")
        print(f"   ⏰ Última actualización: {session_data.get('timestamp', 'N/A')}")
    else:
        print("❌ No se encontró paper_trading_session.json")
    
    print()
    
    # 2. Verificar archivos de configuración
    config_files = ["config.py", "paper_trading_dashboard_improved.py"]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ Encontrado: {config_file}")
        else:
            print(f"❌ No encontrado: {config_file}")
    
    print()
    
    # 3. Verificar hora actual y sesión
    est = pytz.timezone('US/Eastern')
    now = datetime.now(est)
    print(f"🕐 Hora actual: {now.strftime('%H:%M:%S')} EST")
    
    # Verificar si estamos en ventana de sesión asiática
    hour = now.hour
    minute = now.minute
    
    if hour == 19 and minute <= 5:
        print("✅ ESTAMOS EN SESIÓN ASIÁTICA (19:00-19:05)")
        remaining = 5 - minute
        print(f"   ⏱️ Tiempo restante: {remaining} minutos")
    else:
        print("❌ No estamos en ventana de sesión asiática")
    
    print()
    
    # 4. Verificar archivos de log
    log_files = [
        "paper_trading_dashboard.log",
        "sicar_bot.log", 
        "trades_detailed.log"
    ]
    
    print("📝 ARCHIVOS DE LOG:")
    for log_file in log_files:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            print(f"   ✅ {log_file} ({size} bytes)")
        else:
            print(f"   ❌ {log_file} (no existe)")

if __name__ == "__main__":
    check_config()