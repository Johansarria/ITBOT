#!/usr/bin/env python3
"""
Monitor de Logs en Tiempo Real
Monitorea el crecimiento de los logs y crea backups automáticos cuando sea necesario
"""

import os
import time
import datetime
from pathlib import Path
from backup_logs_system import LogBackupSystem

class LogMonitor:
    def __init__(self, log_file="simulation_logs_detailed.log", max_size_mb=50):
        self.log_file = Path(log_file)
        self.max_size_mb = max_size_mb
        self.backup_system = LogBackupSystem()
        self.last_size = 0
        self.last_backup_time = None
        
    def get_file_size_mb(self):
        """Obtiene el tamaño del archivo en MB"""
        if self.log_file.exists():
            return self.log_file.stat().st_size / (1024 * 1024)
        return 0
    
    def should_create_backup(self):
        """Determina si se debe crear un backup"""
        current_size = self.get_file_size_mb()
        
        # Backup por tamaño
        if current_size >= self.max_size_mb:
            return True, f"Tamaño excedido: {current_size:.2f} MB >= {self.max_size_mb} MB"
        
        # Backup por tiempo (cada 2 horas)
        if self.last_backup_time:
            time_since_backup = datetime.datetime.now() - self.last_backup_time
            if time_since_backup.total_seconds() > 7200:  # 2 horas
                return True, f"Tiempo transcurrido: {time_since_backup}"
        
        return False, None
    
    def print_status(self):
        """Imprime el estado actual del monitor"""
        current_size = self.get_file_size_mb()
        growth = current_size - self.last_size if self.last_size > 0 else 0
        
        print(f"\r📊 Log: {current_size:.2f} MB (+{growth:.2f} MB) | "
              f"Último backup: {self.last_backup_time.strftime('%H:%M:%S') if self.last_backup_time else 'Nunca'} | "
              f"Max: {self.max_size_mb} MB", end="", flush=True)
        
        self.last_size = current_size
    
    def run_monitor(self, check_interval=30):
        """Ejecuta el monitor en tiempo real"""
        print(f"🔍 Iniciando monitor de logs (verificación cada {check_interval}s)")
        print(f"📁 Archivo: {self.log_file.absolute()}")
        print(f"⚠️ Tamaño máximo: {self.max_size_mb} MB")
        print("\n" + "="*80)
        
        try:
            while True:
                # Verificar si necesita backup
                should_backup, reason = self.should_create_backup()
                
                if should_backup:
                    print(f"\n🔄 Creando backup: {reason}")
                    if self.backup_system.create_backup():
                        self.last_backup_time = datetime.datetime.now()
                        self.backup_system.cleanup_old_backups(max_backups=15)
                        print("✅ Backup completado")
                    else:
                        print("❌ Error en backup")
                
                # Mostrar estado
                self.print_status()
                
                # Esperar
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitor detenido por el usuario")
            
            # Crear backup final
            print("🔄 Creando backup final...")
            self.backup_system.create_backup()
            
            # Mostrar resumen
            status = self.backup_system.get_backup_status()
            if status:
                print(f"\n📊 Resumen final:")
                print(f"   • Total de backups: {status['total_backups']}")
                print(f"   • Tamaño total: {status['total_size_mb']} MB")
                print(f"   • Directorio: {status['backup_directory']}")

def main():
    """Función principal"""
    print("🔍 Monitor de Logs en Tiempo Real - ITBOT")
    print("=========================================\n")
    
    # Configuración
    max_size = 50  # MB
    check_interval = 30  # segundos
    
    try:
        print(f"Configuración:")
        print(f"• Tamaño máximo de log: {max_size} MB")
        print(f"• Intervalo de verificación: {check_interval} segundos")
        print(f"• Backup automático por tiempo: cada 2 horas")
        
        response = input("\n¿Iniciar monitor? (y/n): ").lower().strip()
        if response in ['y', 'yes', 'sí', 's']:
            monitor = LogMonitor(max_size_mb=max_size)
            monitor.run_monitor(check_interval=check_interval)
        else:
            print("❌ Monitor cancelado")
            
    except KeyboardInterrupt:
        print("\n🛑 Operación cancelada")

if __name__ == "__main__":
    main()