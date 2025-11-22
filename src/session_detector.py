"""
SICAR - Session Detector Module
Detecta las sesiones de trading específicas para el algoritmo First Candle Breakout
"""

import datetime
from datetime import timezone, timedelta
from typing import Optional, Dict, Any
import pytz
import logging

class SessionDetector:
    """
    Detector de sesiones de trading para estrategia multi-sesión
    Identifica ventanas específicas: Europea, Americana y Asiática
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configuración de sesiones (horarios en EST) - TODAS ACTIVAS
        self.sessions_config = {
            'european': {
                'name': 'Sesión Europea',
                'start_time': '03:00',  # Apertura Londres 8:00 GMT = 3:00 EST
                'end_time': '03:05',
                'timezone': 'EST',
                'active': True,
                'description': 'Apertura del mercado europeo - Frankfurt/Londres'
            },
            'american': {
                'name': 'Sesión Americana', 
                'start_time': '09:30',  # Apertura NYSE 9:30 EST
                'end_time': '09:35',
                'timezone': 'EST',
                'active': True,  # ✅ FASE 2 ACTIVADA
                'description': 'Apertura NYSE/NASDAQ - Wall Street'
            },
            'asian': {
                'name': 'Sesión Asiática',
                'start_time': '19:00',  # Apertura Tokio 9:00 JST = 19:00 EST (día anterior)
                'end_time': '19:05',
                'timezone': 'EST',
                'active': True,  # ✅ FASE 3 ACTIVADA
                'description': 'Apertura mercados asiáticos - Tokio/Sydney'
            }
        }
        
        # Timezone EST
        self.est_tz = pytz.timezone('US/Eastern')
        
    def get_current_session(self) -> Optional[str]:
        """
        Detecta la sesión de trading actual
        
        Returns:
            str: Nombre de la sesión actual ('european', 'american', 'asian') o None
        """
        try:
            # Obtener tiempo actual en EST
            utc_now = datetime.datetime.now(pytz.UTC)
            est_now = utc_now.astimezone(self.est_tz)
            current_time = est_now.strftime('%H:%M')
            
            self.logger.info(f"Tiempo actual EST: {current_time}")
            
            # Verificar cada sesión activa
            for session_name, config in self.sessions_config.items():
                if not config['active']:
                    continue
                    
                if self._is_time_in_session(current_time, config):
                    self.logger.info(f"Sesión detectada: {config['name']}")
                    return session_name
                    
            return None
            
        except Exception as e:
            self.logger.error(f"Error detectando sesión: {e}")
            return None
    
    def _is_time_in_session(self, current_time: str, session_config: Dict) -> bool:
        """
        Verifica si el tiempo actual está dentro de la ventana de sesión
        
        Args:
            current_time: Tiempo actual en formato HH:MM
            session_config: Configuración de la sesión
            
        Returns:
            bool: True si está en la ventana de tiempo
        """
        try:
            start_time = session_config['start_time']
            end_time = session_config['end_time']
            
            # Convertir a minutos para comparación
            current_minutes = self._time_to_minutes(current_time)
            start_minutes = self._time_to_minutes(start_time)
            end_minutes = self._time_to_minutes(end_time)
            
            # Verificar si está en el rango
            if start_minutes <= end_minutes:
                # Mismo día
                return start_minutes <= current_minutes <= end_minutes
            else:
                # Cruza medianoche
                return current_minutes >= start_minutes or current_minutes <= end_minutes
                
        except Exception as e:
            self.logger.error(f"Error verificando tiempo en sesión: {e}")
            return False
    
    def _time_to_minutes(self, time_str: str) -> int:
        """
        Convierte tiempo HH:MM a minutos desde medianoche
        
        Args:
            time_str: Tiempo en formato HH:MM
            
        Returns:
            int: Minutos desde medianoche
        """
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    
    def get_session_info(self, session_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información completa de una sesión
        
        Args:
            session_name: Nombre de la sesión
            
        Returns:
            Dict: Información de la sesión o None si no existe
        """
        return self.sessions_config.get(session_name)
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """
        Obtiene todas las sesiones activas
        
        Returns:
            Dict: Sesiones activas con su configuración
        """
        return {
            name: config for name, config in self.sessions_config.items()
            if config['active']
        }
    
    def activate_session(self, session_name: str) -> bool:
        """
        Activa una sesión específica
        
        Args:
            session_name: Nombre de la sesión a activar
            
        Returns:
            bool: True si se activó correctamente
        """
        if session_name in self.sessions_config:
            self.sessions_config[session_name]['active'] = True
            self.logger.info(f"Sesión {session_name} activada")
            return True
        return False
    
    def deactivate_session(self, session_name: str) -> bool:
        """
        Desactiva una sesión específica
        
        Args:
            session_name: Nombre de la sesión a desactivar
            
        Returns:
            bool: True si se desactivó correctamente
        """
        if session_name in self.sessions_config:
            self.sessions_config[session_name]['active'] = False
            self.logger.info(f"Sesión {session_name} desactivada")
            return True
        return False
    
    def get_next_session(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de la próxima sesión activa
        
        Returns:
            Dict: Información de la próxima sesión o None
        """
        try:
            utc_now = datetime.datetime.now(pytz.UTC)
            est_now = utc_now.astimezone(self.est_tz)
            current_minutes = self._time_to_minutes(est_now.strftime('%H:%M'))
            
            next_session = None
            min_wait_time = float('inf')
            
            for session_name, config in self.sessions_config.items():
                if not config['active']:
                    continue
                    
                start_minutes = self._time_to_minutes(config['start_time'])
                
                # Calcular tiempo de espera
                if start_minutes > current_minutes:
                    wait_time = start_minutes - current_minutes
                else:
                    wait_time = (24 * 60) - current_minutes + start_minutes
                
                if wait_time < min_wait_time:
                    min_wait_time = wait_time
                    next_session = {
                        'session': session_name,
                        'config': config,
                        'wait_minutes': wait_time
                    }
            
            return next_session
            
        except Exception as e:
            self.logger.error(f"Error obteniendo próxima sesión: {e}")
            return None
    
    def is_market_hours(self) -> bool:
        """
        Verifica si estamos en horario de mercado (cualquier sesión activa)
        
        Returns:
            bool: True si hay alguna sesión activa ahora
        """
        return self.get_current_session() is not None
    
    def get_session_status_report(self) -> Dict[str, Any]:
        """
        Genera un reporte completo del estado de las sesiones
        
        Returns:
            Dict: Reporte completo del estado
        """
        try:
            utc_now = datetime.datetime.now(pytz.UTC)
            est_now = utc_now.astimezone(self.est_tz)
            
            current_session = self.get_current_session()
            next_session = self.get_next_session()
            active_sessions = self.get_active_sessions()
            
            report = {
                'timestamp_utc': utc_now.isoformat(),
                'timestamp_est': est_now.isoformat(),
                'current_time_est': est_now.strftime('%H:%M:%S'),
                'current_session': current_session,
                'current_session_info': self.get_session_info(current_session) if current_session else None,
                'next_session': next_session,
                'active_sessions_count': len(active_sessions),
                'active_sessions': list(active_sessions.keys()),
                'is_trading_time': current_session is not None,
                'all_sessions_config': self.sessions_config
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generando reporte: {e}")
            return {'error': str(e)}


# Función de utilidad para uso rápido
def get_current_trading_session() -> Optional[str]:
    """
    Función de utilidad para obtener rápidamente la sesión actual
    
    Returns:
        str: Sesión actual o None
    """
    detector = SessionDetector()
    return detector.get_current_session()


if __name__ == "__main__":
    # Configurar logging para pruebas
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear detector y probar
    detector = SessionDetector()
    
    print("=== SICAR Session Detector - Prueba ===")
    print()
    
    # Mostrar reporte completo
    report = detector.get_session_status_report()
    
    print(f"Tiempo actual EST: {report['current_time_est']}")
    print(f"Sesión actual: {report['current_session'] or 'Ninguna'}")
    print(f"¿En horario de trading?: {report['is_trading_time']}")
    print()
    
    if report['current_session']:
        session_info = report['current_session_info']
        print(f"Información de sesión actual:")
        print(f"  - Nombre: {session_info['name']}")
        print(f"  - Ventana: {session_info['start_time']} - {session_info['end_time']} EST")
        print(f"  - Descripción: {session_info['description']}")
    
    if report['next_session']:
        next_info = report['next_session']
        print(f"Próxima sesión: {next_info['session']} en {next_info['wait_minutes']} minutos")
    
    print()
    print("Sesiones activas:")
    for session_name in report['active_sessions']:
        config = detector.get_session_info(session_name)
        print(f"  - {config['name']}: {config['start_time']}-{config['end_time']} EST")