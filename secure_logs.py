#!/usr/bin/env python3
"""
Sistema de Seguridad de Logs Completo
Configura rotación automática, backups y monitoreo de logs
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
import datetime
import json
import shutil

class SecureLogSystem:
    def __init__(self, base_dir="."):
        self.base_dir = Path(base_dir)
        self.logs_dir = self.base_dir / "logs_secure"
        self.backup_dir = self.base_dir / "logs_backup"
        self.config_file = self.base_dir / "log_security_config.json"
        
        # Crear directorios
        self.logs_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Configuración por defecto
        self.config = {
            "max_log_size_mb": 10,
            "max_backup_count": 20,
            "backup_interval_hours": 1,
            "compression": True,
            "encryption": False,
            "log_level": "INFO"
        }
        
        self.load_config()
        
    def load_config(self):
        """Carga la configuración desde archivo"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
            except Exception as e:
                print(f"⚠️ Error cargando configuración: {e}")
    
    def save_config(self):
        """Guarda la configuración actual"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error guardando configuración: {e}")
    
    def setup_rotating_logger(self, name="secure_trading"):
        """Configura un logger con rotación automática"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self.config["log_level"]))
        
        # Limpiar handlers existentes
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Handler con rotación por tamaño
        log_file = self.logs_dir / f"{name}.log"
        max_bytes = self.config["max_log_size_mb"] * 1024 * 1024
        
        rotating_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=self.config["max_backup_count"],
            encoding='utf-8'
        )
        
        # Formato detallado
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        rotating_handler.setFormatter(formatter)
        
        logger.addHandler(rotating_handler)
        
        # Handler para consola (opcional)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def create_backup_archive(self):
        """Crea un archivo comprimido con todos los logs"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"logs_archive_{timestamp}"
        archive_path = self.backup_dir / archive_name
        
        try:
            # Crear archivo comprimido
            shutil.make_archive(str(archive_path), 'zip', str(self.logs_dir))
            
            # Información del archivo
            zip_file = Path(f"{archive_path}.zip")
            size_mb = zip_file.stat().st_size / (1024 * 1024)
            
            return {
                "success": True,
                "file": str(zip_file),
                "size_mb": round(size_mb, 2),
                "timestamp": timestamp
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_old_archives(self, max_archives=10):
        """Limpia archivos de backup antiguos"""
        archives = list(self.backup_dir.glob("logs_archive_*.zip"))
        archives.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        deleted = []
        for archive in archives[max_archives:]:
            try:
                archive.unlink()
                deleted.append(archive.name)
            except Exception as e:
                print(f"⚠️ Error eliminando {archive.name}: {e}")
        
        return deleted
    
    def get_system_status(self):
        """Obtiene el estado del sistema de logs"""
        status = {
            "timestamp": datetime.datetime.now().isoformat(),
            "logs_directory": str(self.logs_dir),
            "backup_directory": str(self.backup_dir),
            "config": self.config.copy()
        }
        
        # Información de logs
        log_files = list(self.logs_dir.glob("*.log*"))
        status["log_files"] = {
            "count": len(log_files),
            "total_size_mb": round(sum(f.stat().st_size for f in log_files) / (1024 * 1024), 2),
            "files": [{
                "name": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            } for f in log_files]
        }
        
        # Información de backups
        backup_files = list(self.backup_dir.glob("*.zip"))
        status["backup_files"] = {
            "count": len(backup_files),
            "total_size_mb": round(sum(f.stat().st_size for f in backup_files) / (1024 * 1024), 2),
            "files": [{
                "name": f.name,
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                "created": datetime.datetime.fromtimestamp(f.stat().st_ctime).isoformat()
            } for f in backup_files]
        }
        
        return status
    
    def print_status_report(self):
        """Imprime un reporte del estado del sistema"""
        status = self.get_system_status()
        
        print("🔒 Sistema de Seguridad de Logs - Estado")
        print("=" * 50)
        print(f"📅 Fecha: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Directorio de logs: {status['logs_directory']}")
        print(f"💾 Directorio de backups: {status['backup_directory']}")
        
        print("\n📊 Archivos de Log:")
        print(f"   • Cantidad: {status['log_files']['count']}")
        print(f"   • Tamaño total: {status['log_files']['total_size_mb']} MB")
        
        for log_file in status['log_files']['files'][:5]:  # Mostrar solo los primeros 5
            print(f"   • {log_file['name']}: {log_file['size_mb']} MB")
        
        print("\n💾 Archivos de Backup:")
        print(f"   • Cantidad: {status['backup_files']['count']}")
        print(f"   • Tamaño total: {status['backup_files']['total_size_mb']} MB")
        
        for backup_file in status['backup_files']['files'][:3]:  # Mostrar solo los primeros 3
            print(f"   • {backup_file['name']}: {backup_file['size_mb']} MB")
        
        print("\n⚙️ Configuración:")
        for key, value in status['config'].items():
            print(f"   • {key}: {value}")

def main():
    """Función principal para configurar el sistema"""
    print("🔒 Configuración del Sistema de Seguridad de Logs")
    print("=" * 55)
    
    # Inicializar sistema
    secure_system = SecureLogSystem()
    
    # Mostrar estado actual
    secure_system.print_status_report()
    
    print("\n🔧 Opciones disponibles:")
    print("1. Crear backup inmediato")
    print("2. Configurar logger rotativo")
    print("3. Limpiar backups antiguos")
    print("4. Mostrar estado detallado")
    print("5. Salir")
    
    while True:
        try:
            choice = input("\nSelecciona una opción (1-5): ").strip()
            
            if choice == "1":
                print("🔄 Creando backup...")
                result = secure_system.create_backup_archive()
                if result["success"]:
                    print(f"✅ Backup creado: {result['file']} ({result['size_mb']} MB)")
                else:
                    print(f"❌ Error: {result['error']}")
            
            elif choice == "2":
                logger_name = input("Nombre del logger (default: secure_trading): ").strip() or "secure_trading"
                logger = secure_system.setup_rotating_logger(logger_name)
                print(f"✅ Logger '{logger_name}' configurado con rotación automática")
                
                # Ejemplo de uso
                logger.info("Logger configurado correctamente")
                logger.info(f"Configuración: {secure_system.config}")
                
            elif choice == "3":
                max_archives = int(input("Máximo de archivos a mantener (default: 10): ") or "10")
                deleted = secure_system.cleanup_old_archives(max_archives)
                if deleted:
                    print(f"🗑️ Eliminados {len(deleted)} archivos antiguos")
                else:
                    print("✅ No hay archivos antiguos para eliminar")
            
            elif choice == "4":
                secure_system.print_status_report()
            
            elif choice == "5":
                print("👋 Sistema configurado. ¡Logs seguros!")
                break
            
            else:
                print("❌ Opción inválida")
                
        except KeyboardInterrupt:
            print("\n🛑 Operación cancelada")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()