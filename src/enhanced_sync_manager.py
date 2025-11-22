"""
Sistema de Sincronización Mejorado para SICAR
Maneja la sincronización entre dashboard y archivo JSON
"""

import json
import threading
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from enhanced_config import CONFIG
from enhanced_logger import SICAR_LOGGER

class SyncManager:
    """Gestor de sincronización entre dashboard y JSON"""
    
    def __init__(self, json_file_path: str):
        self.json_file_path = Path(json_file_path)
        self.lock = threading.RLock()
        self.last_modified = 0
        self.data_cache = {}
        self.observers = []
        self.sync_interval = CONFIG.SYNC_CONFIG['sync_interval']
        self.auto_sync_enabled = CONFIG.SYNC_CONFIG['auto_sync_enabled']
        self.sync_thread = None
        self.running = False
        
        # Asegurar que el archivo existe
        self._ensure_file_exists()
        
        # Cargar datos iniciales
        self._load_initial_data()
    
    def _ensure_file_exists(self):
        """Asegurar que el archivo JSON existe"""
        if not self.json_file_path.exists():
            # Crear archivo con estructura inicial
            initial_data = {
                "timestamp": datetime.now().isoformat(),
                "initial_capital": CONFIG.PAPER_TRADING_CONFIG['initial_capital'],
                "current_capital": CONFIG.PAPER_TRADING_CONFIG['initial_capital'],
                "positions": [],
                "total_trades": 0,
                "auto_trading": CONFIG.AUTO_TRADING_DEFAULT,
                "session_active": False,
                "current_session": None,
                "last_sync": datetime.now().isoformat()
            }
            self._write_data(initial_data)
            SICAR_LOGGER.log_sync_operation("INIT", True, "Archivo JSON creado con datos iniciales")
    
    def _load_initial_data(self):
        """Cargar datos iniciales del archivo"""
        try:
            with self.lock:
                if self.json_file_path.exists():
                    with open(self.json_file_path, 'r', encoding='utf-8') as f:
                        self.data_cache = json.load(f)
                    self.last_modified = self.json_file_path.stat().st_mtime
                    SICAR_LOGGER.log_sync_operation("LOAD", True, f"Datos cargados: {len(self.data_cache)} campos")
                else:
                    self.data_cache = {}
        except Exception as e:
            SICAR_LOGGER.log_error("SYNC_LOAD", str(e), {"file": str(self.json_file_path)})
            self.data_cache = {}
    
    def _write_data(self, data: Dict[str, Any]):
        """Escribir datos al archivo JSON"""
        try:
            # Agregar timestamp de sincronización
            data["last_sync"] = datetime.now().isoformat()
            
            # Crear backup si existe el archivo
            if self.json_file_path.exists():
                backup_path = self.json_file_path.with_suffix('.json.bak')
                self.json_file_path.replace(backup_path)
            
            # Escribir datos
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Actualizar cache y timestamp
            self.data_cache = data.copy()
            self.last_modified = self.json_file_path.stat().st_mtime
            
        except Exception as e:
            SICAR_LOGGER.log_error("SYNC_WRITE", str(e), {"file": str(self.json_file_path)})
            raise
    
    def start_auto_sync(self):
        """Iniciar sincronización automática"""
        if self.auto_sync_enabled and not self.running:
            self.running = True
            self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
            self.sync_thread.start()
            SICAR_LOGGER.log_sync_operation("AUTO_SYNC", True, "Sincronización automática iniciada")
    
    def stop_auto_sync(self):
        """Detener sincronización automática"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        SICAR_LOGGER.log_sync_operation("AUTO_SYNC", True, "Sincronización automática detenida")
    
    def _sync_loop(self):
        """Loop de sincronización automática"""
        while self.running:
            try:
                self.check_for_external_changes()
                time.sleep(self.sync_interval)
            except Exception as e:
                SICAR_LOGGER.log_error("SYNC_LOOP", str(e))
                time.sleep(self.sync_interval * 2)  # Esperar más tiempo en caso de error
    
    def check_for_external_changes(self):
        """Verificar cambios externos en el archivo"""
        try:
            if not self.json_file_path.exists():
                return
            
            current_modified = self.json_file_path.stat().st_mtime
            
            if current_modified > self.last_modified:
                with self.lock:
                    with open(self.json_file_path, 'r', encoding='utf-8') as f:
                        new_data = json.load(f)
                    
                    # Detectar cambios específicos
                    changes = self._detect_changes(self.data_cache, new_data)
                    
                    if changes:
                        self.data_cache = new_data
                        self.last_modified = current_modified
                        
                        # Notificar a observadores
                        self._notify_observers(changes)
                        
                        SICAR_LOGGER.log_sync_operation("EXTERNAL_CHANGE", True, 
                                                      f"Cambios detectados: {list(changes.keys())}")
        
        except Exception as e:
            SICAR_LOGGER.log_error("SYNC_CHECK", str(e))
    
    def _detect_changes(self, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """Detectar cambios entre datos antiguos y nuevos"""
        changes = {}
        
        # Campos importantes a monitorear
        important_fields = [
            'auto_trading', 'current_capital', 'positions', 
            'total_trades', 'session_active', 'current_session'
        ]
        
        for field in important_fields:
            old_value = old_data.get(field)
            new_value = new_data.get(field)
            
            if old_value != new_value:
                changes[field] = {
                    'old': old_value,
                    'new': new_value,
                    'timestamp': datetime.now().isoformat()
                }
        
        return changes
    
    def _notify_observers(self, changes: Dict[str, Any]):
        """Notificar cambios a observadores"""
        for observer in self.observers:
            try:
                observer(changes)
            except Exception as e:
                SICAR_LOGGER.log_error("OBSERVER_NOTIFY", str(e))
    
    def add_observer(self, callback: Callable[[Dict[str, Any]], None]):
        """Agregar observador de cambios"""
        self.observers.append(callback)
    
    def remove_observer(self, callback: Callable[[Dict[str, Any]], None]):
        """Remover observador de cambios"""
        if callback in self.observers:
            self.observers.remove(callback)
    
    def get_data(self, key: str = None) -> Any:
        """Obtener datos del cache"""
        with self.lock:
            if key is None:
                return self.data_cache.copy()
            return self.data_cache.get(key)
    
    def update_data(self, updates: Dict[str, Any], force_sync: bool = True):
        """Actualizar datos y sincronizar"""
        try:
            with self.lock:
                # Actualizar cache
                self.data_cache.update(updates)
                
                # Escribir al archivo si se requiere sincronización
                if force_sync:
                    self._write_data(self.data_cache)
                    SICAR_LOGGER.log_sync_operation("UPDATE", True, 
                                                  f"Campos actualizados: {list(updates.keys())}")
        
        except Exception as e:
            SICAR_LOGGER.log_error("SYNC_UPDATE", str(e), {"updates": updates})
            raise
    
    def set_auto_trading(self, enabled: bool, reason: str = ""):
        """Actualizar estado del auto trading"""
        self.update_data({
            'auto_trading': enabled,
            'auto_trading_changed_at': datetime.now().isoformat(),
            'auto_trading_reason': reason
        })
        SICAR_LOGGER.log_auto_trading_status(enabled, reason)
    
    def update_capital(self, new_capital: float):
        """Actualizar capital actual"""
        self.update_data({
            'current_capital': new_capital,
            'capital_updated_at': datetime.now().isoformat()
        })
    
    def add_trade(self, trade_info: Dict[str, Any]):
        """Agregar nuevo trade"""
        current_trades = self.get_data('total_trades') or 0
        self.update_data({
            'total_trades': current_trades + 1,
            'last_trade': trade_info,
            'last_trade_at': datetime.now().isoformat()
        })
        SICAR_LOGGER.log_trade_executed(trade_info)
    
    def update_session_status(self, session_name: str, active: bool):
        """Actualizar estado de la sesión"""
        self.update_data({
            'session_active': active,
            'current_session': session_name if active else None,
            'session_updated_at': datetime.now().isoformat()
        })
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Obtener estado de sincronización"""
        return {
            'file_exists': self.json_file_path.exists(),
            'last_modified': datetime.fromtimestamp(self.last_modified).isoformat() if self.last_modified else None,
            'cache_size': len(self.data_cache),
            'auto_sync_enabled': self.auto_sync_enabled,
            'sync_running': self.running,
            'observers_count': len(self.observers)
        }

# Instancia global del gestor de sincronización
SYNC_MANAGER = SyncManager(CONFIG.FILE_PATHS['paper_trading_session'])

# Funciones de conveniencia
def get_trading_data(key: str = None) -> Any:
    """Obtener datos de trading"""
    return SYNC_MANAGER.get_data(key)

def update_trading_data(updates: Dict[str, Any]):
    """Actualizar datos de trading"""
    SYNC_MANAGER.update_data(updates)

def set_auto_trading(enabled: bool, reason: str = ""):
    """Configurar auto trading"""
    SYNC_MANAGER.set_auto_trading(enabled, reason)