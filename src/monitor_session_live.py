"""
Monitor en tiempo real de la sesión de trading
"""

import time
import json
import os
from datetime import datetime
import pytz
from session_detector import SessionDetector

def monitor_session():
    print("🔴 INICIANDO MONITOREO EN TIEMPO REAL")
    print("=" * 60)
    
    session_detector = SessionDetector()
    est = pytz.timezone('US/Eastern')
    
    # Archivos a monitorear
    session_file = "paper_trading_session.json"
    log_files = [
        "../logs/trades_detailed.log",
        "../logs/trades_data.jsonl",
        "paper_trading_dashboard.log"
    ]
    
    last_session = None
    last_capital = None
    last_trades = None
    
    print("⏰ Esperando sesión asiática (19:00-19:05 EST)...")
    print("📊 Monitoreando archivos de trading...")
    print()
    
    while True:
        current_time = datetime.now(est)
        time_str = current_time.strftime("%H:%M:%S")
        
        # Verificar sesión actual
        current_session = session_detector.get_current_session()
        
        # Verificar estado del paper trading
        try:
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    trading_data = json.load(f)
                    current_capital = trading_data.get('capital', 0)
                    current_trades = trading_data.get('total_trades', 0)
                    auto_trading = trading_data.get('auto_trading', False)
            else:
                current_capital = None
                current_trades = None
                auto_trading = False
        except:
            current_capital = None
            current_trades = None
            auto_trading = False
        
        # Detectar cambios
        session_changed = current_session != last_session
        capital_changed = current_capital != last_capital
        trades_changed = current_trades != last_trades
        
        if session_changed or capital_changed or trades_changed or current_session:
            print(f"🕐 {time_str} EST")
            
            if session_changed:
                if current_session:
                    print(f"   🟢 SESIÓN INICIADA: {current_session}")
                else:
                    print(f"   🔴 SESIÓN TERMINADA")
            
            if current_session:
                print(f"   📈 Sesión activa: {current_session}")
            
            if current_capital is not None:
                print(f"   💰 Capital: ${current_capital:,.2f}")
                if capital_changed and last_capital is not None:
                    change = current_capital - last_capital
                    emoji = "📈" if change > 0 else "📉"
                    print(f"   {emoji} Cambio: ${change:+,.2f}")
            
            if current_trades is not None:
                print(f"   🔄 Total trades: {current_trades}")
                if trades_changed and last_trades is not None:
                    new_trades = current_trades - last_trades
                    print(f"   ✨ Nuevos trades: +{new_trades}")
            
            print(f"   🤖 Auto-trading: {'✅ ACTIVO' if auto_trading else '❌ INACTIVO'}")
            print()
        
        # Actualizar valores anteriores
        last_session = current_session
        last_capital = current_capital
        last_trades = current_trades
        
        # Si estamos en sesión asiática, mostrar más detalles
        if current_session == "Sesión Asiática":
            print(f"   🌏 SESIÓN ASIÁTICA EN PROGRESO - {time_str}")
            
            # Verificar logs de trading
            for log_file in log_files:
                if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                    print(f"   📝 Actividad detectada en: {log_file}")
        
        # Parar si ya terminó la sesión asiática
        if last_session == "Sesión Asiática" and current_session is None:
            print("🏁 SESIÓN ASIÁTICA COMPLETADA")
            break
        
        time.sleep(10)  # Verificar cada 10 segundos

if __name__ == "__main__":
    try:
        monitor_session()
    except KeyboardInterrupt:
        print("\n⏹️ Monitoreo detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error en monitoreo: {e}")