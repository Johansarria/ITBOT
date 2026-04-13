#!/usr/bin/env python3
"""
Sistema de Respaldo Automático de Logs
Asegura que los logs de trading no se pierdan mediante copias de seguridad automáticas
"""

import os
import shutil
import datetime
import time
import logging
from pathlib import Path

class LogBackupSystem:
    def __init__(self, log_file_path="simulation_logs_detailed.log", backup_dir="logs_backup"):
        self.log_file_path = Path(log_file_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Configurar logging para el sistema de backup
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - BACKUP - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backup_system.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def create_backup(self):
        """Crea una copia de seguridad del archivo de logs actual"""
        if not self.log_file_path.exists():
            self.logger.warning(f"Archivo de logs no encontrado: {self.log_file_path}")
            return False
            
        try:
            # Generar nombre de backup con timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"simulation_logs_backup_{timestamp}.log"
            backup_path = self.backup_dir / backup_filename
            
            # Copiar archivo
            shutil.copy2(self.log_file_path, backup_path)
            
            # Obtener tamaño del archivo
            file_size = backup_path.stat().st_size / (1024 * 1024)  # MB
            
            self.logger.info(f"✅ Backup creado: {backup_filename} ({file_size:.2f} MB)")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error creando backup: {e}")
            return False
    
    def cleanup_old_backups(self, max_backups=10):
        """Elimina backups antiguos manteniendo solo los más recientes"""
        try:
            backup_files = list(self.backup_dir.glob("simulation_logs_backup_*.log"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if len(backup_files) > max_backups:
                files_to_delete = backup_files[max_backups:]
                for file_path in files_to_delete:
                    file_path.unlink()
                    self.logger.info(f"🗑️ Backup antiguo eliminado: {file_path.name}")
                    
        except Exception as e:
            self.logger.error(f"❌ Error limpiando backups antiguos: {e}")
    
    def get_backup_status(self):
        """Obtiene el estado actual del sistema de backups"""
        try:
            backup_files = list(self.backup_dir.glob("simulation_logs_backup_*.log"))
            total_backups = len(backup_files)
            
            if backup_files:
                latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
                latest_time = datetime.datetime.fromtimestamp(latest_backup.stat().st_mtime)
                total_size = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)  # MB
            else:
                latest_backup = None
                latest_time = None
                total_size = 0
            
            status = {
                'total_backups': total_backups,
                'latest_backup': latest_backup.name if latest_backup else None,
                'latest_backup_time': latest_time,
                'total_size_mb': round(total_size, 2),
                'backup_directory': str(self.backup_dir.absolute())
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo estado de backups: {e}")
            return None
    
    def run_continuous_backup(self, interval_minutes=30):
        """Ejecuta backups automáticos en intervalos regulares"""
        self.logger.info(f"🚀 Iniciando sistema de backup automático (cada {interval_minutes} minutos)")
        
        while True:
            try:
                # Crear backup
                self.create_backup()
                
                # Limpiar backups antiguos
                self.cleanup_old_backups()
                
                # Mostrar estado
                status = self.get_backup_status()
                if status:
                    self.logger.info(f"📊 Estado: {status['total_backups']} backups, {status['total_size_mb']} MB total")
                
                # Esperar hasta el próximo backup
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Sistema de backup detenido por el usuario")
                break
            except Exception as e:
                self.logger.error(f"❌ Error en backup automático: {e}")
                time.sleep(60)  # Esperar 1 minuto antes de reintentar

def main():
    """Función principal para ejecutar el sistema de backup"""
    backup_system = LogBackupSystem()
    
    print("🔒 Sistema de Respaldo de Logs - ITBOT")
    print("=====================================\n")
    
    # Mostrar estado actual
    status = backup_system.get_backup_status()
    if status:
        print(f"📊 Estado actual:")
        print(f"   • Total de backups: {status['total_backups']}")
        print(f"   • Último backup: {status['latest_backup'] or 'Ninguno'}")
        print(f"   • Tamaño total: {status['total_size_mb']} MB")
        print(f"   • Directorio: {status['backup_directory']}\n")
    
    # Crear backup inmediato
    print("🔄 Creando backup inmediato...")
    backup_system.create_backup()
    
    # Preguntar si ejecutar backup continuo
    try:
        response = input("\n¿Ejecutar backup automático continuo? (y/n): ").lower().strip()
        if response in ['y', 'yes', 'sí', 's']:
            backup_system.run_continuous_backup(interval_minutes=30)
        else:
            print("✅ Backup manual completado. Sistema finalizado.")
    except KeyboardInterrupt:
        print("\n🛑 Operación cancelada por el usuario")

if __name__ == "__main__":
    main()