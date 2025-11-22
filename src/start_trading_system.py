"""
Script de inicio del sistema de trading con monitor de stop loss integrado
"""

import subprocess
import sys
import time
import threading
from stop_loss_monitor import StopLossMonitor
import logging

class TradingSystemManager:
    def __init__(self):
        self.stop_loss_monitor = StopLossMonitor(check_interval=30)
        self.processes = []
        
    def start_stop_loss_monitor(self):
        """Inicia el monitor de stop loss"""
        try:
            self.stop_loss_monitor.start_monitoring()
            print("✅ Monitor de stop loss iniciado")
            return True
        except Exception as e:
            print(f"❌ Error iniciando monitor de stop loss: {e}")
            return False
    
    def start_main_trading_system(self):
        """Inicia el sistema principal de trading"""
        try:
            # Ejecutar el sistema principal en un proceso separado
            process = subprocess.Popen([
                sys.executable, 
                "alerta_auto_trading_integrada.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes.append(process)
            print("✅ Sistema principal de trading iniciado")
            return True
        except Exception as e:
            print(f"❌ Error iniciando sistema principal: {e}")
            return False
    
    def start_all_systems(self):
        """Inicia todos los sistemas"""
        print("🚀 INICIANDO SISTEMA DE TRADING COMPLETO")
        print("=" * 50)
        
        # Iniciar monitor de stop loss
        if self.start_stop_loss_monitor():
            print("   ✅ Monitor de stop loss: ACTIVO")
        else:
            print("   ❌ Monitor de stop loss: ERROR")
            return False
        
        # Iniciar sistema principal
        if self.start_main_trading_system():
            print("   ✅ Sistema principal: ACTIVO")
        else:
            print("   ❌ Sistema principal: ERROR")
            return False
        
        print("\n🎯 Todos los sistemas están activos")
        print("   📊 Monitor de stop loss verificando cada 30 segundos")
        print("   🔄 Sistema principal procesando señales")
        print("\n⚠️  Presiona Ctrl+C para detener todos los sistemas")
        
        return True
    
    def stop_all_systems(self):
        """Detiene todos los sistemas"""
        print("\n🛑 Deteniendo todos los sistemas...")
        
        # Detener monitor de stop loss
        try:
            self.stop_loss_monitor.stop_monitoring()
            print("   ✅ Monitor de stop loss detenido")
        except Exception as e:
            print(f"   ❌ Error deteniendo monitor: {e}")
        
        # Detener procesos
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print("   ✅ Sistema principal detenido")
            except Exception as e:
                print(f"   ❌ Error deteniendo proceso: {e}")
        
        print("🏁 Todos los sistemas detenidos")

def main():
    manager = TradingSystemManager()
    
    try:
        if manager.start_all_systems():
            # Mantener el sistema ejecutándose
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_all_systems()

if __name__ == "__main__":
    main()
