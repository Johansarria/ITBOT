# /src/session_manager.py
"""
Gestor de Sesiones SICAR - Sistema de Nombres para Conjuntos de Sistemas
Mantiene en memoria los nombres de las sesiones activas y sus sistemas asociados
"""

import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading
import psutil

class SessionManager:
    """Gestor de sesiones para sistemas SICAR en ejecución"""
    
    def __init__(self, memory_file: str = "sicar_sessions_memory.json"):
        self.memory_file = os.path.join(os.path.dirname(__file__), memory_file)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
        self.load_from_memory()
        
    def load_from_memory(self):
        """Carga las sesiones desde el archivo de memoria"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = data.get('sessions', {})
                    print(f"✅ Sesiones cargadas desde memoria: {len(self.sessions)} sesiones activas")
            else:
                print("📝 Archivo de memoria no existe, iniciando con sesiones vacías")
        except Exception as e:
            print(f"⚠️ Error cargando memoria de sesiones: {e}")
            self.sessions = {}
    
    def save_to_memory(self):
        """Guarda las sesiones en el archivo de memoria"""
        try:
            with self.lock:
                data = {
                    'sessions': self.sessions,
                    'last_updated': datetime.now().isoformat(),
                    'total_sessions': len(self.sessions)
                }
                with open(self.memory_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"💾 Sesiones guardadas en memoria: {len(self.sessions)} sesiones")
        except Exception as e:
            print(f"❌ Error guardando memoria de sesiones: {e}")
    
    def create_session(self, name: Optional[str] = None, description: str = "") -> str:
        """
        Crea una nueva sesión con nombre único
        
        Args:
            name: Nombre personalizado (opcional)
            description: Descripción de la sesión
            
        Returns:
            session_id: ID único de la sesión creada
        """
        with self.lock:
            session_id = str(uuid.uuid4())[:8]
            
            if not name:
                # Generar nombre automático basado en timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name = f"SICAR_Session_{timestamp}"
            
            # Asegurar que el nombre sea único
            original_name = name
            counter = 1
            while any(session['name'] == name for session in self.sessions.values()):
                name = f"{original_name}_{counter}"
                counter += 1
            
            self.sessions[session_id] = {
                'id': session_id,
                'name': name,
                'description': description,
                'created_at': datetime.now().isoformat(),
                'systems': [],
                'status': 'active',
                'last_activity': datetime.now().isoformat()
            }
            
            self.save_to_memory()
            print(f"🎯 Nueva sesión creada: {name} (ID: {session_id})")
            return session_id
    
    def add_system_to_session(self, session_id: str, system_info: Dict[str, Any]):
        """
        Añade un sistema a una sesión existente
        
        Args:
            session_id: ID de la sesión
            system_info: Información del sistema (script, command_id, terminal_id, etc.)
        """
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['systems'].append({
                    **system_info,
                    'added_at': datetime.now().isoformat()
                })
                self.sessions[session_id]['last_activity'] = datetime.now().isoformat()
                self.save_to_memory()
                print(f"🔧 Sistema añadido a sesión {self.sessions[session_id]['name']}: {system_info.get('script', 'Unknown')}")
            else:
                print(f"❌ Sesión {session_id} no encontrada")
    
    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Obtiene la sesión activa más reciente"""
        if not self.sessions:
            return None
        
        # Buscar la sesión más reciente con status 'active'
        active_sessions = [s for s in self.sessions.values() if s['status'] == 'active']
        if not active_sessions:
            return None
        
        return max(active_sessions, key=lambda x: x['last_activity'])
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """Lista todas las sesiones"""
        return list(self.sessions.values())
    
    def get_session_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Obtiene una sesión por su nombre"""
        for session in self.sessions.values():
            if session['name'] == name:
                return session
        return None
    
    def update_session_status(self, session_id: str, status: str):
        """Actualiza el estado de una sesión"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['status'] = status
                self.sessions[session_id]['last_activity'] = datetime.now().isoformat()
                self.save_to_memory()
                print(f"📊 Estado de sesión {self.sessions[session_id]['name']} actualizado a: {status}")
    
    def detect_running_systems(self) -> List[Dict[str, Any]]:
        """Detecta sistemas SICAR en ejecución"""
        running_systems = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and len(cmdline) > 1:
                        if 'python' in cmdline[0].lower() and any(
                            script in ' '.join(cmdline) for script in [
                                'filtros_ia_inteligentes.py',
                                'alerta_btc_rompimiento.py',
                                'forex_metals_trading_system.py',
                                'alerta_auto_trading_integrada.py',
                                'sicar_', 'trading_', 'alert'
                            ]
                        ):
                            script_name = None
                            for arg in cmdline:
                                if arg.endswith('.py'):
                                    script_name = os.path.basename(arg)
                                    break
                            
                            if script_name:
                                running_systems.append({
                                    'pid': proc.info['pid'],
                                    'script': script_name,
                                    'cmdline': ' '.join(cmdline),
                                    'detected_at': datetime.now().isoformat()
                                })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"⚠️ Error detectando sistemas: {e}")
        
        return running_systems
    
    def auto_create_session_for_current_systems(self) -> str:
        """Crea automáticamente una sesión para los sistemas actualmente en ejecución"""
        running_systems = self.detect_running_systems()
        
        if not running_systems:
            print("ℹ️ No se detectaron sistemas SICAR en ejecución")
            return None
        
        # Crear nombre descriptivo basado en los sistemas detectados
        system_names = [sys['script'].replace('.py', '') for sys in running_systems]
        session_name = f"SICAR_Auto_{len(system_names)}sistemas_{datetime.now().strftime('%H%M')}"
        
        session_id = self.create_session(
            name=session_name,
            description=f"Sesión automática para {len(running_systems)} sistemas detectados"
        )
        
        # Añadir todos los sistemas detectados
        for system in running_systems:
            self.add_system_to_session(session_id, system)
        
        print(f"🚀 Sesión automática creada: {session_name}")
        print(f"📋 Sistemas incluidos: {', '.join(system_names)}")
        
        return session_id
    
    def get_session_summary(self, session_id: str) -> str:
        """Obtiene un resumen de la sesión"""
        if session_id not in self.sessions:
            return f"❌ Sesión {session_id} no encontrada"
        
        session = self.sessions[session_id]
        systems_count = len(session['systems'])
        
        summary = f"""
🎯 SESIÓN: {session['name']}
📅 Creada: {session['created_at']}
📊 Estado: {session['status']}
🔧 Sistemas: {systems_count}
📝 Descripción: {session['description']}
⏰ Última actividad: {session['last_activity']}

💻 SISTEMAS EN EJECUCIÓN:
"""
        
        for i, system in enumerate(session['systems'], 1):
            summary += f"  {i}. {system.get('script', 'Unknown')} (PID: {system.get('pid', 'N/A')})\n"
        
        return summary

# Instancia global del gestor de sesiones
session_manager = SessionManager()

def get_session_manager() -> SessionManager:
    """Obtiene la instancia global del gestor de sesiones"""
    return session_manager

if __name__ == "__main__":
    # Demo del sistema
    print("🎯 SICAR Session Manager - Demo")
    print("=" * 50)
    
    # Crear sesión automática para sistemas actuales
    session_id = session_manager.auto_create_session_for_current_systems()
    
    if session_id:
        print("\n" + session_manager.get_session_summary(session_id))
    
    # Mostrar todas las sesiones
    print("\n📋 TODAS LAS SESIONES:")
    for session in session_manager.list_sessions():
        print(f"  • {session['name']} ({session['status']}) - {len(session['systems'])} sistemas")