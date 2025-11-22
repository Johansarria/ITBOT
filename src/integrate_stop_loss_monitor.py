"""
Script para integrar el monitor de stop loss con el sistema principal
"""

import sqlite3
import os
import shutil
from datetime import datetime

class StopLossIntegrator:
    def __init__(self, db_path="auto_trading_alerts.db"):
        self.db_path = db_path
        
    def add_missing_columns(self):
        """Agrega columnas faltantes a la base de datos si no existen"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar columnas existentes
            cursor.execute("PRAGMA table_info(executed_trades)")
            columns = [col[1] for col in cursor.fetchall()]
            
            columns_added = []
            
            # Agregar columnas faltantes
            if 'exit_price' not in columns:
                cursor.execute("ALTER TABLE executed_trades ADD COLUMN exit_price REAL")
                columns_added.append('exit_price')
            
            if 'exit_timestamp' not in columns:
                cursor.execute("ALTER TABLE executed_trades ADD COLUMN exit_timestamp TEXT")
                columns_added.append('exit_timestamp')
            
            if 'pnl' not in columns:
                cursor.execute("ALTER TABLE executed_trades ADD COLUMN pnl REAL")
                columns_added.append('pnl')
            
            if 'close_reason' not in columns:
                cursor.execute("ALTER TABLE executed_trades ADD COLUMN close_reason TEXT")
                columns_added.append('close_reason')
            
            conn.commit()
            conn.close()
            
            return columns_added
            
        except Exception as e:
            print(f"❌ Error agregando columnas: {e}")
            return []
    
    def create_startup_script(self):
        """Crea un script de inicio que incluye el monitor de stop loss"""
        startup_script = '''"""
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
        
        print("\\n🎯 Todos los sistemas están activos")
        print("   📊 Monitor de stop loss verificando cada 30 segundos")
        print("   🔄 Sistema principal procesando señales")
        print("\\n⚠️  Presiona Ctrl+C para detener todos los sistemas")
        
        return True
    
    def stop_all_systems(self):
        """Detiene todos los sistemas"""
        print("\\n🛑 Deteniendo todos los sistemas...")
        
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
'''
        
        with open('start_trading_system.py', 'w', encoding='utf-8') as f:
            f.write(startup_script)
        
        print("✅ Script de inicio creado: start_trading_system.py")
    
    def create_configuration_file(self):
        """Crea archivo de configuración para el monitor"""
        config = {
            "stop_loss_monitor": {
                "check_interval": 30,
                "enable_logging": True,
                "log_level": "INFO",
                "max_log_size_mb": 10
            },
            "risk_management": {
                "max_positions": 2,
                "default_stop_loss_pct": 2.0,
                "default_take_profit_pct": 4.0,
                "emergency_stop_loss_pct": 5.0
            },
            "notifications": {
                "enable_stop_loss_alerts": True,
                "enable_take_profit_alerts": True,
                "enable_error_alerts": True
            }
        }
        
        import json
        with open('stop_loss_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("✅ Archivo de configuración creado: stop_loss_config.json")
    
    def test_stop_loss_monitor(self):
        """Prueba el monitor de stop loss"""
        print("🧪 Probando monitor de stop loss...")
        
        try:
            from stop_loss_monitor import StopLossMonitor
            
            monitor = StopLossMonitor()
            
            # Verificar posiciones activas
            active_positions = monitor.get_active_positions()
            print(f"   📊 Posiciones activas: {len(active_positions)}")
            
            # Verificar estado
            status = monitor.get_monitoring_status()
            print(f"   🔧 Estado del monitor: {status}")
            
            print("   ✅ Monitor de stop loss funcionando correctamente")
            return True
            
        except Exception as e:
            print(f"   ❌ Error en el monitor: {e}")
            return False
    
    def generate_integration_report(self):
        """Genera un reporte de la integración"""
        print("📋 REPORTE DE INTEGRACIÓN")
        print("=" * 40)
        
        # Verificar archivos
        files_status = {
            'stop_loss_monitor.py': os.path.exists('stop_loss_monitor.py'),
            'start_trading_system.py': os.path.exists('start_trading_system.py'),
            'stop_loss_config.json': os.path.exists('stop_loss_config.json'),
            'alerta_auto_trading_integrada.py': os.path.exists('alerta_auto_trading_integrada.py')
        }
        
        print("📁 Archivos del sistema:")
        for file, exists in files_status.items():
            status = "✅" if exists else "❌"
            print(f"   {status} {file}")
        
        # Verificar base de datos
        columns_added = self.add_missing_columns()
        if columns_added:
            print(f"\\n🗄️ Columnas agregadas a la base de datos:")
            for col in columns_added:
                print(f"   ✅ {col}")
        else:
            print("\\n🗄️ Base de datos ya tenía todas las columnas necesarias")
        
        # Probar monitor
        print("\\n🧪 Prueba del monitor:")
        monitor_ok = self.test_stop_loss_monitor()
        
        # Resumen
        print("\\n📊 RESUMEN:")
        all_files_ok = all(files_status.values())
        
        if all_files_ok and monitor_ok:
            print("   🟢 Integración completada exitosamente")
            print("   🚀 Sistema listo para usar con monitor de stop loss")
            print("\\n📝 Para iniciar el sistema completo:")
            print("   python start_trading_system.py")
        else:
            print("   🔴 Integración incompleta")
            if not all_files_ok:
                print("   ❌ Faltan archivos del sistema")
            if not monitor_ok:
                print("   ❌ Monitor de stop loss no funciona correctamente")

def main():
    print("🔧 INTEGRACIÓN DEL MONITOR DE STOP LOSS")
    print("=" * 50)
    
    integrator = StopLossIntegrator()
    
    # Crear archivos necesarios
    integrator.create_startup_script()
    integrator.create_configuration_file()
    
    # Generar reporte
    integrator.generate_integration_report()
    
    print("\\n🏁 Integración completada")

if __name__ == "__main__":
    main()