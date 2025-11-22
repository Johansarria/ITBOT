#!/usr/bin/env python3
"""
SICAR - Resumen de Procesos y Análisis Activos
Muestra un resumen completo de todos los sistemas en funcionamiento
"""

import json
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
import psutil
import subprocess

class SicarProcessMonitor:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.logs_path = self.base_path / "logs"
        
    def get_system_info(self):
        """Obtiene información del sistema"""
        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('.').percent
        }
    
    def check_python_processes(self):
        """Verifica procesos Python relacionados con SICAR"""
        sicar_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Buscar scripts SICAR específicos
                    sicar_scripts = [
                        'monitor_session_live.py',
                        'proactive_monitoring_system.py',
                        'paper_trading_system.py',
                        'real_time_first_candle_system.py',
                        'smart_alert_system.py',
                        'drl_monitoring_system.py'
                    ]
                    
                    for script in sicar_scripts:
                        if script in cmdline:
                            runtime = datetime.now() - datetime.fromtimestamp(proc.info['create_time'])
                            sicar_processes.append({
                                'script': script,
                                'pid': proc.info['pid'],
                                'runtime': str(runtime).split('.')[0],
                                'cpu_percent': proc.info['cpu_percent'],
                                'memory_percent': proc.info['memory_percent'],
                                'status': 'ACTIVO'
                            })
                            break
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return sicar_processes
    
    def check_paper_trading_status(self):
        """Verifica el estado del paper trading"""
        try:
            session_file = self.base_path / "paper_trading_session.json"
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    
                return {
                    'status': 'ACTIVO' if session_data.get('active', False) else 'INACTIVO',
                    'session_id': session_data.get('session_id', 'N/A'),
                    'capital_inicial': session_data.get('initial_capital', 0),
                    'capital_actual': session_data.get('current_capital', 0),
                    'auto_trading': session_data.get('auto_trading', False),
                    'total_trades': session_data.get('total_trades', 0),
                    'ultima_actualizacion': session_data.get('last_update', 'N/A')
                }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}
            
        return {'status': 'NO_ENCONTRADO'}
    
    def check_monitoring_databases(self):
        """Verifica las bases de datos de monitoreo"""
        databases = []
        
        db_files = [
            'proactive_monitoring.db',
            'advanced_logging.db',
            'enhanced_trading.db',
            'alertas_database.db',
            'auto_trading_alerts.db'
        ]
        
        for db_file in db_files:
            db_path = self.base_path / db_file
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # Obtener información de las tablas
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    
                    # Obtener estadísticas básicas
                    total_records = 0
                    for table in tables:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                            count = cursor.fetchone()[0]
                            total_records += count
                        except:
                            continue
                    
                    conn.close()
                    
                    databases.append({
                        'database': db_file,
                        'status': 'ACTIVO',
                        'tables': len(tables),
                        'total_records': total_records,
                        'size_mb': round(db_path.stat().st_size / (1024*1024), 2)
                    })
                    
                except Exception as e:
                    databases.append({
                        'database': db_file,
                        'status': 'ERROR',
                        'error': str(e)
                    })
        
        return databases
    
    def check_recent_logs(self):
        """Verifica logs recientes"""
        log_files = []
        
        # Logs principales
        main_logs = [
            'sicar_main.log',
            'sicar_trading.log',
            'sicar_breakouts.log',
            'sicar_errors.log',
            'paper_trading.log',
            'enhanced_integration.log'
        ]
        
        for log_file in main_logs:
            log_path = self.logs_path / log_file
            if log_path.exists():
                try:
                    stat = log_path.stat()
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    age = datetime.now() - modified
                    
                    # Leer últimas líneas
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        last_lines = lines[-3:] if len(lines) >= 3 else lines
                    
                    log_files.append({
                        'file': log_file,
                        'size_kb': round(stat.st_size / 1024, 2),
                        'last_modified': modified.strftime("%Y-%m-%d %H:%M:%S"),
                        'age_minutes': int(age.total_seconds() / 60),
                        'last_entries': [line.strip() for line in last_lines if line.strip()]
                    })
                    
                except Exception as e:
                    log_files.append({
                        'file': log_file,
                        'status': 'ERROR',
                        'error': str(e)
                    })
        
        return log_files
    
    def check_integration_reports(self):
        """Verifica reportes de integración"""
        reports_path = self.logs_path / "integration_reports"
        reports = []
        
        if reports_path.exists():
            for report_file in reports_path.glob("*.json"):
                try:
                    with open(report_file, 'r', encoding='utf-8') as f:
                        report_data = json.load(f)
                    
                    reports.append({
                        'file': report_file.name,
                        'timestamp': report_data.get('timestamp', 'N/A'),
                        'status': report_data.get('status', 'N/A'),
                        'health': report_data.get('health', 'N/A'),
                        'warnings': len(report_data.get('warnings', [])),
                        'trading_activity': report_data.get('trading_activity', 'N/A')
                    })
                    
                except Exception as e:
                    reports.append({
                        'file': report_file.name,
                        'status': 'ERROR',
                        'error': str(e)
                    })
        
        return sorted(reports, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    def display_summary(self):
        """Muestra el resumen completo"""
        print("🔍 SICAR - RESUMEN DE PROCESOS Y ANÁLISIS ACTIVOS")
        print("=" * 80)
        
        # Información del sistema
        system_info = self.get_system_info()
        print(f"\n📊 INFORMACIÓN DEL SISTEMA:")
        print(f"   ⏰ Timestamp: {system_info['timestamp']}")
        print(f"   🖥️  CPU: {system_info['cpu_usage']:.1f}%")
        print(f"   💾 RAM: {system_info['memory_usage']:.1f}%")
        print(f"   💿 Disco: {system_info['disk_usage']:.1f}%")
        
        # Procesos Python activos
        processes = self.check_python_processes()
        print(f"\n🐍 PROCESOS PYTHON SICAR ACTIVOS ({len(processes)}):")
        if processes:
            for proc in processes:
                print(f"   ✅ {proc['script']}")
                print(f"      PID: {proc['pid']} | Runtime: {proc['runtime']}")
                print(f"      CPU: {proc['cpu_percent']:.1f}% | RAM: {proc['memory_percent']:.1f}%")
        else:
            print("   ❌ No se encontraron procesos SICAR activos")
        
        # Estado del Paper Trading
        trading_status = self.check_paper_trading_status()
        print(f"\n💰 ESTADO DEL PAPER TRADING:")
        if trading_status['status'] == 'ACTIVO':
            print(f"   🟢 Estado: {trading_status['status']}")
            print(f"   🆔 Sesión: {trading_status['session_id']}")
            print(f"   💵 Capital: ${trading_status['capital_inicial']:.2f} → ${trading_status['capital_actual']:.2f}")
            print(f"   🤖 Auto-trading: {'✅' if trading_status['auto_trading'] else '❌'}")
            print(f"   🔄 Total trades: {trading_status['total_trades']}")
        else:
            print(f"   🔴 Estado: {trading_status['status']}")
            if 'error' in trading_status:
                print(f"   ❌ Error: {trading_status['error']}")
        
        # Bases de datos
        databases = self.check_monitoring_databases()
        print(f"\n🗄️  BASES DE DATOS DE MONITOREO ({len(databases)}):")
        for db in databases:
            if db['status'] == 'ACTIVO':
                print(f"   ✅ {db['database']}")
                print(f"      Tablas: {db['tables']} | Registros: {db['total_records']} | Tamaño: {db['size_mb']} MB")
            else:
                print(f"   ❌ {db['database']}: {db.get('error', 'Error desconocido')}")
        
        # Logs recientes
        logs = self.check_recent_logs()
        print(f"\n📝 LOGS RECIENTES ({len(logs)}):")
        for log in logs:
            if 'error' not in log:
                age_indicator = "🟢" if log['age_minutes'] < 5 else "🟡" if log['age_minutes'] < 30 else "🔴"
                print(f"   {age_indicator} {log['file']}")
                print(f"      Tamaño: {log['size_kb']} KB | Modificado: {log['last_modified']} ({log['age_minutes']}m)")
                if log['last_entries']:
                    print(f"      Última entrada: {log['last_entries'][-1][:100]}...")
            else:
                print(f"   ❌ {log['file']}: {log['error']}")
        
        # Reportes de integración
        reports = self.check_integration_reports()
        print(f"\n📊 REPORTES DE INTEGRACIÓN ({len(reports)}):")
        for i, report in enumerate(reports[:3]):  # Mostrar solo los 3 más recientes
            if 'error' not in report:
                status_icon = "🟢" if report['status'] == 'active' else "🟡"
                print(f"   {status_icon} {report['file']}")
                print(f"      Estado: {report['status']} | Salud: {report['health']}")
                print(f"      Advertencias: {report['warnings']} | Actividad: {report['trading_activity']}")
            else:
                print(f"   ❌ {report['file']}: {report['error']}")
        
        print(f"\n🎯 RESUMEN EJECUTIVO:")
        active_processes = len([p for p in processes if p['status'] == 'ACTIVO'])
        active_dbs = len([db for db in databases if db['status'] == 'ACTIVO'])
        recent_logs = len([log for log in logs if 'error' not in log and log['age_minutes'] < 30])
        
        print(f"   🔄 Procesos activos: {active_processes}")
        print(f"   🗄️  Bases de datos: {active_dbs}")
        print(f"   📝 Logs recientes: {recent_logs}")
        print(f"   💰 Paper trading: {trading_status['status']}")
        print(f"   📊 Reportes: {len(reports)} disponibles")
        
        print("\n" + "=" * 80)
        print("✅ Resumen completado")

def main():
    monitor = SicarProcessMonitor()
    monitor.display_summary()

if __name__ == "__main__":
    main()