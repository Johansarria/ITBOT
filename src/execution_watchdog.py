#!/usr/bin/env python3
"""
Sistema Watchdog de Ejecución - SICAR
Garantiza la ejecución del análisis crítico a las 08:00 UTC
Implementa redundancia y recuperación automática
"""

import asyncio
import json
import logging
import os
import subprocess
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import requests
import sqlite3
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('execution_watchdog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WatchdogStatus(Enum):
    """Estados del Watchdog"""
    MONITORING = "monitoring"
    PRE_ANALYSIS = "pre_analysis"
    ANALYSIS_RUNNING = "analysis_running"
    POST_ANALYSIS = "post_analysis"
    BACKUP_TRIGGERED = "backup_triggered"
    CRITICAL_FAILURE = "critical_failure"

class AlertLevel(Enum):
    """Niveles de alerta"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class WatchdogEvent:
    """Evento del Watchdog"""
    timestamp: datetime
    event_type: str
    status: WatchdogStatus
    alert_level: AlertLevel
    message: str
    data: Dict[str, Any] = None
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'status': self.status.value,
            'alert_level': self.alert_level.value,
            'message': self.message,
            'data': self.data or {}
        }

class ExecutionWatchdog:
    """Sistema Watchdog de Ejecución"""
    
    def __init__(self, config_file: str = "watchdog_config.json"):
        """Inicializa el Watchdog"""
        self.config = self._load_config(config_file)
        self.status = WatchdogStatus.MONITORING
        self.running = False
        self.events: List[WatchdogEvent] = []
        
        # Configuración crítica
        self.analysis_hour = 8  # 08:00 UTC
        self.pre_check_minutes = 5  # Verificar 5 minutos antes
        self.post_check_minutes = 5  # Verificar 5 minutos después
        self.backup_delay_minutes = 2  # Activar backup si no hay respuesta en 2 min
        
        # Rutas críticas
        self.main_script = "real_time_first_candle_system.py"
        self.backup_script = "backup_first_candle_system.py"
        self.log_file = "real_time_first_candle.log"
        
        # Base de datos para persistencia
        self.db_path = "watchdog_events.db"
        self._init_database()
        
        # Sistema de alertas
        self.alert_channels = {
            'telegram': self._send_telegram_alert,
            'email': self._send_email_alert,
            'desktop': self._send_desktop_alert,
            'webhook': self._send_webhook_alert
        }
        
        # Estado del sistema
        self.last_analysis_time = None
        self.system_health = {
            'api_connectivity': False,
            'disk_space': 0,
            'memory_usage': 0,
            'cpu_usage': 0,
            'network_status': False
        }
        
        logger.info("🔒 ExecutionWatchdog inicializado")
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga configuración del Watchdog"""
        default_config = {
            'telegram': {
                'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
                'chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
                'enabled': True
            },
            'email': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': os.getenv('EMAIL_USERNAME', ''),
                'password': os.getenv('EMAIL_PASSWORD', ''),
                'to_email': os.getenv('ALERT_EMAIL', ''),
                'enabled': True
            },
            'webhook': {
                'url': os.getenv('WEBHOOK_URL', ''),
                'enabled': False
            },
            'monitoring': {
                'check_interval': 30,  # segundos
                'health_check_interval': 60,  # segundos
                'max_retry_attempts': 3,
                'backup_timeout': 300  # 5 minutos
            },
            'thresholds': {
                'min_disk_space_gb': 1.0,
                'max_memory_usage_percent': 90,
                'max_cpu_usage_percent': 95
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Error cargando config, usando defaults: {e}")
        
        return default_config
    
    def _init_database(self):
        """Inicializa base de datos de eventos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS watchdog_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        event_type TEXT,
                        status TEXT,
                        alert_level TEXT,
                        message TEXT,
                        data TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_health (
                        timestamp TEXT PRIMARY KEY,
                        api_connectivity INTEGER,
                        disk_space REAL,
                        memory_usage REAL,
                        cpu_usage REAL,
                        network_status INTEGER
                    )
                """)
        except Exception as e:
            logger.error(f"Error inicializando DB: {e}")
    
    def start_monitoring(self):
        """Inicia el monitoreo del Watchdog"""
        if self.running:
            logger.warning("Watchdog ya está ejecutándose")
            return
        
        self.running = True
        self.status = WatchdogStatus.MONITORING
        
        # Hilo principal de monitoreo
        monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        # Hilo de verificación de salud del sistema
        health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        health_thread.start()
        
        self._log_event(
            "watchdog_started",
            WatchdogStatus.MONITORING,
            AlertLevel.INFO,
            "Sistema Watchdog iniciado correctamente"
        )
        
        logger.info("🚀 Watchdog de ejecución iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.running = False
        self.status = WatchdogStatus.MONITORING
        
        self._log_event(
            "watchdog_stopped",
            WatchdogStatus.MONITORING,
            AlertLevel.INFO,
            "Sistema Watchdog detenido"
        )
        
        logger.info("⏹️ Watchdog de ejecución detenido")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        logger.info("🔄 Loop de monitoreo Watchdog iniciado")
        
        while self.running:
            try:
                current_time = datetime.now(timezone.utc)
                current_hour = current_time.hour
                current_minute = current_time.minute
                
                # Verificación pre-análisis (07:55 UTC)
                if (current_hour == self.analysis_hour - 1 and 
                    current_minute >= 60 - self.pre_check_minutes):
                    self._pre_analysis_check()
                
                # Verificación durante análisis (08:00-08:05 UTC)
                elif (current_hour == self.analysis_hour and 
                      current_minute <= self.post_check_minutes):
                    self._analysis_monitoring()
                
                # Verificación post-análisis (08:05-08:10 UTC)
                elif (current_hour == self.analysis_hour and 
                      current_minute > self.post_check_minutes and 
                      current_minute <= self.post_check_minutes * 2):
                    self._post_analysis_check()
                
                # Monitoreo general
                else:
                    self._general_monitoring()
                
                # Esperar antes del siguiente ciclo
                time.sleep(self.config['monitoring']['check_interval'])
                
            except Exception as e:
                logger.error(f"Error en loop de monitoreo: {e}")
                self._log_event(
                    "monitoring_error",
                    self.status,
                    AlertLevel.CRITICAL,
                    f"Error en loop de monitoreo: {str(e)}"
                )
                time.sleep(60)  # Esperar más tiempo en caso de error
        
        logger.info("🔄 Loop de monitoreo Watchdog finalizado")
    
    def _pre_analysis_check(self):
        """Verificación pre-análisis (07:55 UTC)"""
        if self.status != WatchdogStatus.PRE_ANALYSIS:
            self.status = WatchdogStatus.PRE_ANALYSIS
            logger.info("🔍 Iniciando verificación pre-análisis")
            
            # Verificar que el sistema principal esté ejecutándose
            if not self._is_main_system_running():
                self._trigger_emergency_start()
            
            # Verificar conectividad de APIs
            if not self._check_api_connectivity():
                self._send_alert(
                    AlertLevel.CRITICAL,
                    "API de Binance no disponible antes del análisis crítico"
                )
            
            # Verificar recursos del sistema
            self._check_system_resources()
            
            # Verificar logs recientes
            self._check_recent_logs()
            
            self._log_event(
                "pre_analysis_check",
                WatchdogStatus.PRE_ANALYSIS,
                AlertLevel.INFO,
                "Verificación pre-análisis completada"
            )
    
    def _analysis_monitoring(self):
        """Monitoreo durante análisis (08:00-08:05 UTC)"""
        if self.status != WatchdogStatus.ANALYSIS_RUNNING:
            self.status = WatchdogStatus.ANALYSIS_RUNNING
            logger.info("⚡ Monitoreando análisis crítico en progreso")
        
        # Verificar que el análisis esté ejecutándose
        analysis_detected = self._detect_analysis_execution()
        
        if not analysis_detected:
            # Si no se detecta análisis después de 2 minutos, activar backup
            current_time = datetime.now(timezone.utc)
            if current_time.minute >= self.backup_delay_minutes:
                self._trigger_backup_system()
        
        # Monitorear logs en tiempo real
        self._monitor_analysis_logs()
    
    def _post_analysis_check(self):
        """Verificación post-análisis (08:05-08:10 UTC)"""
        if self.status != WatchdogStatus.POST_ANALYSIS:
            self.status = WatchdogStatus.POST_ANALYSIS
            logger.info("✅ Verificando resultados post-análisis")
            
            # Verificar que el análisis se completó exitosamente
            analysis_success = self._verify_analysis_completion()
            
            if analysis_success:
                self._log_event(
                    "analysis_success",
                    WatchdogStatus.POST_ANALYSIS,
                    AlertLevel.INFO,
                    "Análisis crítico completado exitosamente"
                )
                self._send_alert(
                    AlertLevel.INFO,
                    "✅ Análisis de 08:00 UTC completado exitosamente"
                )
            else:
                self._log_event(
                    "analysis_failure",
                    WatchdogStatus.CRITICAL_FAILURE,
                    AlertLevel.EMERGENCY,
                    "FALLO CRÍTICO: Análisis de 08:00 UTC no se completó"
                )
                self._send_alert(
                    AlertLevel.EMERGENCY,
                    "🚨 FALLO CRÍTICO: Análisis de 08:00 UTC falló"
                )
    
    def _general_monitoring(self):
        """Monitoreo general del sistema"""
        # Verificar que el sistema principal siga ejecutándose
        if not self._is_main_system_running():
            self._log_event(
                "main_system_down",
                WatchdogStatus.CRITICAL_FAILURE,
                AlertLevel.CRITICAL,
                "Sistema principal no está ejecutándose"
            )
            self._restart_main_system()
    
    def _health_check_loop(self):
        """Loop de verificación de salud del sistema"""
        while self.running:
            try:
                # Verificar conectividad API
                self.system_health['api_connectivity'] = self._check_api_connectivity()
                
                # Verificar recursos del sistema
                self.system_health.update(self._get_system_resources())
                
                # Verificar conectividad de red
                self.system_health['network_status'] = self._check_network_connectivity()
                
                # Guardar métricas en DB
                self._save_health_metrics()
                
                # Verificar umbrales críticos
                self._check_health_thresholds()
                
                time.sleep(self.config['monitoring']['health_check_interval'])
                
            except Exception as e:
                logger.error(f"Error en health check: {e}")
                time.sleep(60)
    
    def _is_main_system_running(self) -> bool:
        """Verifica si el sistema principal está ejecutándose"""
        try:
            # Verificar proceso por nombre
            result = subprocess.run(
                ['tasklist', '/FI', f'IMAGENAME eq python.exe'],
                capture_output=True,
                text=True,
                shell=True
            )
            
            # Buscar el script específico en los procesos
            if self.main_script in result.stdout:
                return True
            
            # Verificar archivo de log reciente
            if os.path.exists(self.log_file):
                stat = os.stat(self.log_file)
                last_modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                time_diff = datetime.now(timezone.utc) - last_modified
                
                # Si el log fue modificado en los últimos 5 minutos
                if time_diff.total_seconds() < 300:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando sistema principal: {e}")
            return False
    
    def _check_api_connectivity(self) -> bool:
        """Verifica conectividad con API de Binance"""
        try:
            response = requests.get(
                'https://api.binance.com/api/v3/ping',
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def _get_system_resources(self) -> Dict[str, float]:
        """Obtiene métricas de recursos del sistema"""
        try:
            import psutil
            
            # Espacio en disco
            disk_usage = psutil.disk_usage('.')
            disk_free_gb = disk_usage.free / (1024**3)
            
            # Uso de memoria
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Uso de CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            return {
                'disk_space': disk_free_gb,
                'memory_usage': memory_percent,
                'cpu_usage': cpu_percent
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo recursos del sistema: {e}")
            return {
                'disk_space': 0,
                'memory_usage': 0,
                'cpu_usage': 0
            }
    
    def _check_network_connectivity(self) -> bool:
        """Verifica conectividad de red"""
        try:
            response = requests.get('https://www.google.com', timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def _detect_analysis_execution(self) -> bool:
        """Detecta si el análisis está ejecutándose"""
        try:
            # Verificar logs recientes
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                    # Buscar indicadores de análisis en las últimas líneas
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                    
                    for line in recent_lines:
                        if any(keyword in line.lower() for keyword in [
                            'análisis iniciado',
                            'analysis started',
                            'generating signal',
                            'procesando datos'
                        ]):
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detectando análisis: {e}")
            return False
    
    def _verify_analysis_completion(self) -> bool:
        """Verifica que el análisis se completó exitosamente"""
        try:
            # Verificar logs de finalización
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Buscar indicadores de finalización exitosa
                    success_indicators = [
                        'análisis completado',
                        'analysis completed',
                        'signal generated',
                        'no signal generated'  # También es éxito
                    ]
                    
                    for indicator in success_indicators:
                        if indicator in content.lower():
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando finalización: {e}")
            return False
    
    def _trigger_emergency_start(self):
        """Activa inicio de emergencia del sistema principal"""
        try:
            logger.warning("🚨 Activando inicio de emergencia del sistema principal")
            
            # Intentar iniciar el sistema principal
            subprocess.Popen([
                'python',
                self.main_script
            ], cwd=os.getcwd())
            
            self._log_event(
                "emergency_start",
                WatchdogStatus.BACKUP_TRIGGERED,
                AlertLevel.WARNING,
                "Sistema principal iniciado en modo emergencia"
            )
            
            self._send_alert(
                AlertLevel.WARNING,
                "⚠️ Sistema principal iniciado en modo emergencia"
            )
            
        except Exception as e:
            logger.error(f"Error en inicio de emergencia: {e}")
            self._send_alert(
                AlertLevel.CRITICAL,
                f"❌ Fallo en inicio de emergencia: {str(e)}"
            )
    
    def _trigger_backup_system(self):
        """Activa el sistema de backup"""
        try:
            logger.critical("🚨 ACTIVANDO SISTEMA DE BACKUP")
            
            self.status = WatchdogStatus.BACKUP_TRIGGERED
            
            # Crear script de backup si no existe
            self._create_backup_script()
            
            # Ejecutar sistema de backup
            subprocess.Popen([
                'python',
                self.backup_script
            ], cwd=os.getcwd())
            
            self._log_event(
                "backup_triggered",
                WatchdogStatus.BACKUP_TRIGGERED,
                AlertLevel.CRITICAL,
                "Sistema de backup activado por fallo del principal"
            )
            
            self._send_alert(
                AlertLevel.CRITICAL,
                "🚨 SISTEMA DE BACKUP ACTIVADO - Fallo del sistema principal"
            )
            
        except Exception as e:
            logger.error(f"Error activando backup: {e}")
            self._send_alert(
                AlertLevel.EMERGENCY,
                f"💥 FALLO CRÍTICO: No se pudo activar backup: {str(e)}"
            )
    
    def _create_backup_script(self):
        """Crea script de backup simplificado"""
        backup_content = '''#!/usr/bin/env python3
"""
Sistema de Backup de Emergencia - SICAR
Ejecuta análisis crítico cuando el sistema principal falla
"""

import logging
import json
from datetime import datetime, timezone
from real_time_first_candle_system import RealTimeFirstCandleSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def emergency_analysis():
    """Ejecuta análisis de emergencia"""
    try:
        logger.info("🚨 INICIANDO ANÁLISIS DE EMERGENCIA")
        
        # Crear instancia del sistema
        system = RealTimeFirstCandleSystem()
        
        # Ejecutar análisis forzado
        system.force_analysis()
        
        logger.info("✅ Análisis de emergencia completado")
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de emergencia: {e}")

if __name__ == "__main__":
    emergency_analysis()
'''
        
        try:
            with open(self.backup_script, 'w', encoding='utf-8') as f:
                f.write(backup_content)
            logger.info(f"Script de backup creado: {self.backup_script}")
        except Exception as e:
            logger.error(f"Error creando script de backup: {e}")
    
    def _restart_main_system(self):
        """Reinicia el sistema principal"""
        try:
            logger.warning("🔄 Reiniciando sistema principal")
            
            # Intentar terminar procesos existentes
            subprocess.run([
                'taskkill', '/F', '/IM', 'python.exe'
            ], capture_output=True)
            
            time.sleep(5)  # Esperar a que terminen
            
            # Reiniciar sistema principal
            subprocess.Popen([
                'python',
                self.main_script
            ], cwd=os.getcwd())
            
            self._log_event(
                "system_restart",
                WatchdogStatus.MONITORING,
                AlertLevel.WARNING,
                "Sistema principal reiniciado"
            )
            
        except Exception as e:
            logger.error(f"Error reiniciando sistema: {e}")
    
    def _send_alert(self, level: AlertLevel, message: str, data: Dict = None):
        """Envía alerta por todos los canales configurados"""
        try:
            for channel_name, send_func in self.alert_channels.items():
                if self.config.get(channel_name, {}).get('enabled', False):
                    try:
                        send_func(level, message, data)
                    except Exception as e:
                        logger.error(f"Error enviando alerta por {channel_name}: {e}")
        except Exception as e:
            logger.error(f"Error general enviando alertas: {e}")
    
    def _send_telegram_alert(self, level: AlertLevel, message: str, data: Dict = None):
        """Envía alerta por Telegram"""
        try:
            config = self.config['telegram']
            if not config.get('bot_token') or not config.get('chat_id'):
                return
            
            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.CRITICAL: "🚨",
                AlertLevel.EMERGENCY: "💥"
            }
            
            emoji = emoji_map.get(level, "📢")
            
            text = f"{emoji} *SICAR WATCHDOG*\n\n"
            text += f"*Nivel:* {level.value.upper()}\n"
            text += f"*Tiempo:* {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}\n\n"
            text += f"{message}"
            
            if data:
                text += f"\n\n*Datos:*\n```json\n{json.dumps(data, indent=2)}\n```"
            
            url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
            
            requests.post(url, json={
                'chat_id': config['chat_id'],
                'text': text,
                'parse_mode': 'Markdown'
            }, timeout=10)
            
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")
    
    def _send_email_alert(self, level: AlertLevel, message: str, data: Dict = None):
        """Envía alerta por email"""
        try:
            import smtplib
            from email.mime.text import MimeText
            from email.mime.multipart import MimeMultipart
            
            config = self.config['email']
            if not all([config.get('username'), config.get('password'), config.get('to_email')]):
                return
            
            msg = MimeMultipart()
            msg['From'] = config['username']
            msg['To'] = config['to_email']
            msg['Subject'] = f"SICAR Watchdog - {level.value.upper()}"
            
            body = f"""
Alerta del Sistema Watchdog SICAR

Nivel: {level.value.upper()}
Tiempo: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
Estado: {self.status.value}

Mensaje:
{message}

Datos adicionales:
{json.dumps(data or {}, indent=2)}

---
Sistema de Monitoreo SICAR
"""
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            server.login(config['username'], config['password'])
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
    
    def _send_desktop_alert(self, level: AlertLevel, message: str, data: Dict = None):
        """Envía notificación de escritorio"""
        try:
            title = f"SICAR Watchdog - {level.value.upper()}"
            
            # Usar PowerShell para notificación en Windows
            ps_script = f'''
$notification = New-Object System.Windows.Forms.NotifyIcon
$notification.Icon = [System.Drawing.SystemIcons]::Warning
$notification.BalloonTipTitle = "{title}"
$notification.BalloonTipText = "{message[:100]}..."
$notification.Visible = $true
$notification.ShowBalloonTip(10000)
'''
            
            subprocess.run([
                'powershell', '-Command', ps_script
            ], capture_output=True)
            
        except Exception as e:
            logger.error(f"Error enviando notificación de escritorio: {e}")
    
    def _send_webhook_alert(self, level: AlertLevel, message: str, data: Dict = None):
        """Envía alerta por webhook"""
        try:
            config = self.config['webhook']
            if not config.get('url'):
                return
            
            payload = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'level': level.value,
                'status': self.status.value,
                'message': message,
                'data': data or {}
            }
            
            requests.post(
                config['url'],
                json=payload,
                timeout=10
            )
            
        except Exception as e:
            logger.error(f"Error enviando webhook: {e}")
    
    def _log_event(self, event_type: str, status: WatchdogStatus, 
                   alert_level: AlertLevel, message: str, data: Dict = None):
        """Registra evento en logs y base de datos"""
        event = WatchdogEvent(
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            status=status,
            alert_level=alert_level,
            message=message,
            data=data
        )
        
        self.events.append(event)
        
        # Mantener solo los últimos 1000 eventos en memoria
        if len(self.events) > 1000:
            self.events = self.events[-1000:]
        
        # Guardar en base de datos
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO watchdog_events 
                    (timestamp, event_type, status, alert_level, message, data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event.timestamp.isoformat(),
                    event.event_type,
                    event.status.value,
                    event.alert_level.value,
                    event.message,
                    json.dumps(event.data or {})
                ))
        except Exception as e:
            logger.error(f"Error guardando evento en DB: {e}")
    
    def _save_health_metrics(self):
        """Guarda métricas de salud en base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO system_health
                    (timestamp, api_connectivity, disk_space, memory_usage, cpu_usage, network_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    int(self.system_health['api_connectivity']),
                    self.system_health['disk_space'],
                    self.system_health['memory_usage'],
                    self.system_health['cpu_usage'],
                    int(self.system_health['network_status'])
                ))
        except Exception as e:
            logger.error(f"Error guardando métricas de salud: {e}")
    
    def _check_health_thresholds(self):
        """Verifica umbrales críticos de salud del sistema"""
        thresholds = self.config['thresholds']
        
        # Verificar espacio en disco
        if self.system_health['disk_space'] < thresholds['min_disk_space_gb']:
            self._send_alert(
                AlertLevel.CRITICAL,
                f"Espacio en disco crítico: {self.system_health['disk_space']:.2f} GB"
            )
        
        # Verificar uso de memoria
        if self.system_health['memory_usage'] > thresholds['max_memory_usage_percent']:
            self._send_alert(
                AlertLevel.WARNING,
                f"Uso de memoria alto: {self.system_health['memory_usage']:.1f}%"
            )
        
        # Verificar uso de CPU
        if self.system_health['cpu_usage'] > thresholds['max_cpu_usage_percent']:
            self._send_alert(
                AlertLevel.WARNING,
                f"Uso de CPU alto: {self.system_health['cpu_usage']:.1f}%"
            )
        
        # Verificar conectividad API
        if not self.system_health['api_connectivity']:
            self._send_alert(
                AlertLevel.CRITICAL,
                "API de Binance no disponible"
            )
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del Watchdog"""
        return {
            'status': self.status.value,
            'running': self.running,
            'system_health': self.system_health,
            'last_analysis_time': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'recent_events': [event.to_dict() for event in self.events[-10:]],
            'uptime': datetime.now(timezone.utc).isoformat()
        }
    
    def force_analysis_check(self):
        """Fuerza verificación de análisis (para testing)"""
        logger.info("🔍 Forzando verificación de análisis")
        self._analysis_monitoring()
    
    def test_alerts(self):
        """Prueba el sistema de alertas"""
        logger.info("🧪 Probando sistema de alertas")
        
        self._send_alert(
            AlertLevel.INFO,
            "Prueba del sistema de alertas Watchdog",
            {'test': True, 'timestamp': datetime.now(timezone.utc).isoformat()}
        )

def main():
    """Función principal"""
    print("🔒 Iniciando Sistema Watchdog de Ejecución SICAR...")
    
    # Crear instancia del Watchdog
    watchdog = ExecutionWatchdog()
    
    try:
        # Iniciar monitoreo
        watchdog.start_monitoring()
        
        print("✅ Watchdog iniciado correctamente")
        print("📊 Estado del sistema:")
        status = watchdog.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # Mantener ejecutándose
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo Watchdog...")
        watchdog.stop_monitoring()
        print("✅ Watchdog detenido correctamente")

if __name__ == "__main__":
    main()