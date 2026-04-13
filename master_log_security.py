#!/usr/bin/env python3
"""
Sistema Maestro de Seguridad de Logs
Integra todos los componentes de seguridad, backup y monitoreo de logs
"""

import os
import sys
import time
import threading
import datetime
from pathlib import Path
import json
import subprocess

class MasterLogSecurity:
    def __init__(self):
        self.base_dir = Path(".")
        self.status_file = self.base_dir / "log_security_status.json"
        self.is_running = False
        self.threads = []
        
        # Estado del sistema
        self.status = {
            "started_at": None,
            "last_backup": None,
            "total_backups_created": 0,
            "monitoring_active": False,
            "auto_backup_active": False,
            "errors": [],
            "log_files_monitored": []
        }
        
        self.load_status()
    
    def load_status(self):
        """Carga el estado desde archivo"""
        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    saved_status = json.load(f)
                    self.status.update(saved_status)
            except Exception as e:
                self.log_error(f"Error cargando estado: {e}")
    
    def save_status(self):
        """Guarda el estado actual"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            self.log_error(f"Error guardando estado: {e}")
    
    def log_error(self, error_msg):
        """Registra un error en el sistema"""
        error_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "message": error_msg
        }
        self.status["errors"].append(error_entry)
        
        # Mantener solo los últimos 50 errores
        if len(self.status["errors"]) > 50:
            self.status["errors"] = self.status["errors"][-50:]
        
        print(f"❌ ERROR: {error_msg}")
        self.save_status()
    
    def create_immediate_backup(self):
        """Crea un backup inmediato de todos los logs"""
        try:
            print("🔄 Iniciando backup inmediato...")
            
            # Ejecutar sistema de backup
            result = subprocess.run(
                [sys.executable, "backup_logs_system.py"],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                self.status["last_backup"] = datetime.datetime.now().isoformat()
                self.status["total_backups_created"] += 1
                print("✅ Backup completado exitosamente")
                return True
            else:
                self.log_error(f"Error en backup: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_error(f"Error ejecutando backup: {e}")
            return False
    
    def start_monitoring(self):
        """Inicia el monitoreo automático de logs"""
        def monitor_thread():
            try:
                print("🔍 Iniciando monitoreo automático...")
                self.status["monitoring_active"] = True
                
                while self.is_running:
                    # Verificar archivos de log
                    log_files = list(Path(".").glob("*.log"))
                    self.status["log_files_monitored"] = [str(f) for f in log_files]
                    
                    # Verificar tamaños
                    for log_file in log_files:
                        if log_file.exists():
                            size_mb = log_file.stat().st_size / (1024 * 1024)
                            if size_mb > 50:  # 50 MB límite
                                print(f"⚠️ Log grande detectado: {log_file.name} ({size_mb:.2f} MB)")
                                self.create_immediate_backup()
                                break
                    
                    self.save_status()
                    time.sleep(60)  # Verificar cada minuto
                    
            except Exception as e:
                self.log_error(f"Error en monitoreo: {e}")
            finally:
                self.status["monitoring_active"] = False
        
        if not self.status["monitoring_active"]:
            thread = threading.Thread(target=monitor_thread, daemon=True)
            thread.start()
            self.threads.append(thread)
    
    def start_auto_backup(self, interval_hours=2):
        """Inicia backups automáticos periódicos"""
        def backup_thread():
            try:
                print(f"⏰ Iniciando backups automáticos cada {interval_hours} horas...")
                self.status["auto_backup_active"] = True
                
                while self.is_running:
                    time.sleep(interval_hours * 3600)  # Convertir horas a segundos
                    
                    if self.is_running:  # Verificar si aún está corriendo
                        print(f"🔄 Backup automático programado ({datetime.datetime.now().strftime('%H:%M:%S')})")
                        self.create_immediate_backup()
                        
            except Exception as e:
                self.log_error(f"Error en backup automático: {e}")
            finally:
                self.status["auto_backup_active"] = False
        
        if not self.status["auto_backup_active"]:
            thread = threading.Thread(target=backup_thread, daemon=True)
            thread.start()
            self.threads.append(thread)
    
    def print_dashboard(self):
        """Muestra un dashboard del estado del sistema"""
        os.system('cls' if os.name == 'nt' else 'clear')  # Limpiar pantalla
        
        print("🔒 SISTEMA MAESTRO DE SEGURIDAD DE LOGS")
        print("=" * 60)
        print(f"📅 Fecha actual: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.status["started_at"]:
            started = datetime.datetime.fromisoformat(self.status["started_at"])
            uptime = datetime.datetime.now() - started
            print(f"⏱️ Tiempo activo: {str(uptime).split('.')[0]}")
        
        print(f"\n📊 Estado del Sistema:")
        print(f"   🔍 Monitoreo: {'🟢 ACTIVO' if self.status['monitoring_active'] else '🔴 INACTIVO'}")
        print(f"   ⏰ Backup automático: {'🟢 ACTIVO' if self.status['auto_backup_active'] else '🔴 INACTIVO'}")
        print(f"   💾 Total de backups: {self.status['total_backups_created']}")
        
        if self.status["last_backup"]:
            last_backup = datetime.datetime.fromisoformat(self.status["last_backup"])
            time_since = datetime.datetime.now() - last_backup
            print(f"   🕐 Último backup: hace {str(time_since).split('.')[0]}")
        else:
            print(f"   🕐 Último backup: Nunca")
        
        print(f"\n📁 Archivos Monitoreados: {len(self.status['log_files_monitored'])}")
        for log_file in self.status['log_files_monitored'][:5]:  # Mostrar solo los primeros 5
            try:
                size_mb = Path(log_file).stat().st_size / (1024 * 1024)
                print(f"   • {Path(log_file).name}: {size_mb:.2f} MB")
            except:
                print(f"   • {Path(log_file).name}: No disponible")
        
        if len(self.status['errors']) > 0:
            print(f"\n⚠️ Errores Recientes: {len(self.status['errors'])}")
            for error in self.status['errors'][-3:]:  # Mostrar últimos 3 errores
                timestamp = datetime.datetime.fromisoformat(error['timestamp'])
                print(f"   • {timestamp.strftime('%H:%M:%S')}: {error['message'][:50]}...")
        
        print("\n" + "=" * 60)
        print("Comandos: [b]ackup | [m]onitor | [a]uto-backup | [s]tatus | [q]uit")
    
    def run_interactive(self):
        """Ejecuta el sistema en modo interactivo"""
        self.is_running = True
        self.status["started_at"] = datetime.datetime.now().isoformat()
        
        print("🚀 Iniciando Sistema Maestro de Seguridad de Logs...")
        
        # Crear backup inicial
        self.create_immediate_backup()
        
        # Iniciar servicios automáticos
        self.start_monitoring()
        self.start_auto_backup()
        
        try:
            while self.is_running:
                self.print_dashboard()
                
                try:
                    command = input("\nComando: ").lower().strip()
                    
                    if command in ['q', 'quit', 'exit']:
                        break
                    elif command in ['b', 'backup']:
                        self.create_immediate_backup()
                    elif command in ['m', 'monitor']:
                        if not self.status["monitoring_active"]:
                            self.start_monitoring()
                        else:
                            print("✅ Monitoreo ya está activo")
                    elif command in ['a', 'auto', 'auto-backup']:
                        if not self.status["auto_backup_active"]:
                            hours = input("Intervalo en horas (default: 2): ").strip()
                            interval = int(hours) if hours.isdigit() else 2
                            self.start_auto_backup(interval)
                        else:
                            print("✅ Backup automático ya está activo")
                    elif command in ['s', 'status']:
                        input("\nPresiona Enter para continuar...")
                    else:
                        print("❌ Comando no reconocido")
                        time.sleep(1)
                        
                except KeyboardInterrupt:
                    break
                    
        except Exception as e:
            self.log_error(f"Error en modo interactivo: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Cierra el sistema de forma segura"""
        print("\n🛑 Cerrando sistema...")
        self.is_running = False
        
        # Crear backup final
        print("🔄 Creando backup final...")
        self.create_immediate_backup()
        
        # Esperar a que terminen los threads
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        # Guardar estado final
        self.status["monitoring_active"] = False
        self.status["auto_backup_active"] = False
        self.save_status()
        
        print("✅ Sistema cerrado correctamente")
        print(f"📊 Resumen: {self.status['total_backups_created']} backups creados")

def main():
    """Función principal"""
    try:
        master_system = MasterLogSecurity()
        master_system.run_interactive()
    except KeyboardInterrupt:
        print("\n🛑 Sistema interrumpido por el usuario")
    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    main()