"""
Sistema de Alertas y Notificaciones Inteligentes - SICAR
Fase 2: Alertas avanzadas con machine learning y múltiples canales
"""

import asyncio
import json
import logging
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import requests
import sqlite3
import threading
from queue import Queue, PriorityQueue

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Tipos de alertas disponibles"""
    PRICE_MOVEMENT = "price_movement"
    VOLUME_SPIKE = "volume_spike"
    TECHNICAL_SIGNAL = "technical_signal"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_ALERT = "portfolio_alert"
    ANOMALY_DETECTION = "anomaly_detection"
    NEWS_SENTIMENT = "news_sentiment"
    MARKET_REGIME = "market_regime"
    SYSTEM_ERROR = "system_error"
    PERFORMANCE_ALERT = "performance_alert"

class AlertPriority(Enum):
    """Prioridades de alertas"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

class NotificationChannel(Enum):
    """Canales de notificación"""
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    DESKTOP = "desktop"
    MOBILE_PUSH = "mobile_push"

@dataclass
class Alert:
    """Estructura de una alerta"""
    id: str
    type: AlertType
    priority: AlertPriority
    title: str
    message: str
    symbol: Optional[str] = None
    timestamp: datetime = None
    data: Dict[str, Any] = None
    channels: List[NotificationChannel] = None
    conditions_met: Dict[str, bool] = None
    acknowledged: bool = False
    resolved: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.data is None:
            self.data = {}
        if self.channels is None:
            self.channels = [NotificationChannel.EMAIL]
        if self.conditions_met is None:
            self.conditions_met = {}

class AlertCondition:
    """Condición para generar alertas"""
    
    def __init__(self, name: str, condition_func: Callable, 
                 cooldown_minutes: int = 60, 
                 required_confirmations: int = 1):
        self.name = name
        self.condition_func = condition_func
        self.cooldown_minutes = cooldown_minutes
        self.required_confirmations = required_confirmations
        self.last_triggered = None
        self.confirmation_count = 0
        self.last_check_time = None
    
    def check(self, data: Dict[str, Any]) -> bool:
        """Verifica si la condición se cumple"""
        try:
            current_time = datetime.now()
            
            # Verificar cooldown
            if (self.last_triggered and 
                current_time - self.last_triggered < timedelta(minutes=self.cooldown_minutes)):
                return False
            
            # Evaluar condición
            if self.condition_func(data):
                self.confirmation_count += 1
                if self.confirmation_count >= self.required_confirmations:
                    self.last_triggered = current_time
                    self.confirmation_count = 0
                    return True
            else:
                self.confirmation_count = 0
            
            self.last_check_time = current_time
            return False
            
        except Exception as e:
            logger.error(f"Error evaluando condición {self.name}: {e}")
            return False

class AnomalyDetector:
    """Detector de anomalías usando machine learning"""
    
    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.scaler = StandardScaler()
        self.is_fitted = False
        self.feature_history = []
        self.max_history = 1000
    
    def fit(self, data: np.ndarray):
        """Entrena el modelo de detección de anomalías"""
        try:
            if len(data) < 10:
                return False
            
            scaled_data = self.scaler.fit_transform(data)
            self.model.fit(scaled_data)
            self.is_fitted = True
            logger.info(f"Modelo de anomalías entrenado con {len(data)} muestras")
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando detector de anomalías: {e}")
            return False
    
    def detect_anomaly(self, features: np.ndarray) -> tuple:
        """Detecta anomalías en nuevos datos"""
        try:
            if not self.is_fitted:
                return False, 0.0
            
            # Agregar a historial
            self.feature_history.append(features)
            if len(self.feature_history) > self.max_history:
                self.feature_history.pop(0)
            
            # Escalar y predecir
            scaled_features = self.scaler.transform(features.reshape(1, -1))
            prediction = self.model.predict(scaled_features)[0]
            anomaly_score = self.model.decision_function(scaled_features)[0]
            
            is_anomaly = prediction == -1
            confidence = abs(anomaly_score)
            
            return is_anomaly, confidence
            
        except Exception as e:
            logger.error(f"Error detectando anomalía: {e}")
            return False, 0.0

class NotificationManager:
    """Gestor de notificaciones multi-canal"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.notification_queue = Queue()
        self.rate_limits = {}
        self.failed_notifications = []
        
    async def send_notification(self, alert: Alert) -> bool:
        """Envía notificación por todos los canales especificados"""
        success_count = 0
        total_channels = len(alert.channels)
        
        for channel in alert.channels:
            try:
                if self._check_rate_limit(channel, alert.priority):
                    success = await self._send_to_channel(channel, alert)
                    if success:
                        success_count += 1
                    else:
                        self.failed_notifications.append({
                            'alert_id': alert.id,
                            'channel': channel,
                            'timestamp': datetime.now(),
                            'retry_count': 0
                        })
                        
            except Exception as e:
                logger.error(f"Error enviando notificación por {channel}: {e}")
        
        return success_count > 0
    
    def _check_rate_limit(self, channel: NotificationChannel, priority: AlertPriority) -> bool:
        """Verifica límites de tasa para evitar spam"""
        current_time = time.time()
        channel_key = f"{channel.value}_{priority.value}"
        
        # Límites por canal y prioridad
        limits = {
            f"{NotificationChannel.EMAIL.value}_{AlertPriority.LOW.value}": (10, 3600),  # 10 por hora
            f"{NotificationChannel.EMAIL.value}_{AlertPriority.HIGH.value}": (50, 3600),  # 50 por hora
            f"{NotificationChannel.SMS.value}_{AlertPriority.LOW.value}": (5, 3600),  # 5 por hora
            f"{NotificationChannel.TELEGRAM.value}_{AlertPriority.LOW.value}": (20, 3600),  # 20 por hora
        }
        
        max_count, window = limits.get(channel_key, (100, 3600))
        
        if channel_key not in self.rate_limits:
            self.rate_limits[channel_key] = []
        
        # Limpiar ventana de tiempo
        self.rate_limits[channel_key] = [
            t for t in self.rate_limits[channel_key] 
            if current_time - t < window
        ]
        
        # Verificar límite
        if len(self.rate_limits[channel_key]) >= max_count:
            return False
        
        self.rate_limits[channel_key].append(current_time)
        return True
    
    async def _send_to_channel(self, channel: NotificationChannel, alert: Alert) -> bool:
        """Envía notificación a un canal específico"""
        try:
            if channel == NotificationChannel.EMAIL:
                return self._send_email(alert)
            elif channel == NotificationChannel.TELEGRAM:
                return await self._send_telegram(alert)
            elif channel == NotificationChannel.WEBHOOK:
                return await self._send_webhook(alert)
            elif channel == NotificationChannel.DESKTOP:
                return self._send_desktop_notification(alert)
            else:
                logger.warning(f"Canal {channel} no implementado")
                return False
                
        except Exception as e:
            logger.error(f"Error enviando a {channel}: {e}")
            return False
    
    def _send_email(self, alert: Alert) -> bool:
        """Envía notificación por email"""
        try:
            email_config = self.config.get('email', {})
            if not email_config.get('enabled', False):
                return False
            
            msg = MimeMultipart()
            msg['From'] = email_config['from']
            msg['To'] = email_config['to']
            msg['Subject'] = f"[SICAR] {alert.priority.name} - {alert.title}"
            
            body = f"""
            Alerta SICAR
            
            Tipo: {alert.type.value}
            Prioridad: {alert.priority.name}
            Símbolo: {alert.symbol or 'N/A'}
            Tiempo: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            
            Mensaje:
            {alert.message}
            
            Datos adicionales:
            {json.dumps(alert.data, indent=2, default=str)}
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email enviado para alerta {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return False
    
    async def _send_telegram(self, alert: Alert) -> bool:
        """Envía notificación por Telegram"""
        try:
            telegram_config = self.config.get('telegram', {})
            if not telegram_config.get('enabled', False):
                return False
            
            bot_token = telegram_config['bot_token']
            chat_id = telegram_config['chat_id']
            
            # Formatear mensaje
            priority_emoji = {
                AlertPriority.LOW: "🔵",
                AlertPriority.MEDIUM: "🟡", 
                AlertPriority.HIGH: "🟠",
                AlertPriority.CRITICAL: "🔴",
                AlertPriority.EMERGENCY: "🚨"
            }
            
            emoji = priority_emoji.get(alert.priority, "ℹ️")
            
            message = f"""
{emoji} *SICAR Alert*

*Tipo:* {alert.type.value}
*Prioridad:* {alert.priority.name}
*Símbolo:* {alert.symbol or 'N/A'}
*Tiempo:* {alert.timestamp.strftime('%H:%M:%S')}

*Mensaje:*
{alert.message}
            """
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Telegram enviado para alerta {alert.id}")
                return True
            else:
                logger.error(f"Error Telegram: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error enviando Telegram: {e}")
            return False
    
    async def _send_webhook(self, alert: Alert) -> bool:
        """Envía notificación por webhook"""
        try:
            webhook_config = self.config.get('webhook', {})
            if not webhook_config.get('enabled', False):
                return False
            
            payload = {
                'alert_id': alert.id,
                'type': alert.type.value,
                'priority': alert.priority.value,
                'title': alert.title,
                'message': alert.message,
                'symbol': alert.symbol,
                'timestamp': alert.timestamp.isoformat(),
                'data': alert.data
            }
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=webhook_config.get('headers', {}),
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Webhook enviado para alerta {alert.id}")
                return True
            else:
                logger.error(f"Error webhook: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error enviando webhook: {e}")
            return False
    
    def _send_desktop_notification(self, alert: Alert) -> bool:
        """Envía notificación de escritorio"""
        try:
            # Implementación básica para Windows
            import subprocess
            
            title = f"SICAR - {alert.priority.name}"
            message = f"{alert.title}\n{alert.message}"
            
            # PowerShell para mostrar notificación en Windows
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $notification = New-Object System.Windows.Forms.NotifyIcon
            $notification.Icon = [System.Drawing.SystemIcons]::Information
            $notification.BalloonTipTitle = "{title}"
            $notification.BalloonTipText = "{message}"
            $notification.Visible = $true
            $notification.ShowBalloonTip(5000)
            '''
            
            subprocess.run(['powershell', '-Command', ps_script], 
                         capture_output=True, timeout=10)
            
            logger.info(f"Notificación de escritorio enviada para alerta {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando notificación de escritorio: {e}")
            return False

class SmartAlertSystem:
    """Sistema principal de alertas inteligentes"""
    
    def __init__(self, config_file: str = "alert_config.json"):
        self.config = self._load_config(config_file)
        self.notification_manager = NotificationManager(self.config)
        self.anomaly_detector = AnomalyDetector()
        
        # Base de datos para persistencia
        self.db_path = "alerts.db"
        self._init_database()
        
        # Condiciones y alertas
        self.conditions: Dict[str, AlertCondition] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        
        # Control de ejecución
        self.running = False
        self.monitoring_thread = None
        self.alert_queue = PriorityQueue()
        
        # Métricas
        self.metrics = {
            'total_alerts': 0,
            'alerts_by_type': {},
            'alerts_by_priority': {},
            'notification_success_rate': 0.0,
            'false_positive_rate': 0.0
        }
        
        logger.info("✅ SmartAlertSystem inicializado")
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga configuración desde archivo"""
        default_config = {
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'from': '',
                'to': '',
                'username': '',
                'password': ''
            },
            'telegram': {
                'enabled': False,
                'bot_token': '',
                'chat_id': ''
            },
            'webhook': {
                'enabled': False,
                'url': '',
                'headers': {}
            },
            'monitoring': {
                'check_interval': 30,  # segundos
                'anomaly_detection': True,
                'max_alerts_per_hour': 100
            }
        }
        
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except FileNotFoundError:
            logger.warning(f"Archivo de configuración {config_file} no encontrado, usando configuración por defecto")
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
        
        return default_config
    
    def _init_database(self):
        """Inicializa base de datos SQLite"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    priority INTEGER,
                    title TEXT,
                    message TEXT,
                    symbol TEXT,
                    timestamp TEXT,
                    data TEXT,
                    acknowledged BOOLEAN,
                    resolved BOOLEAN
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alert_metrics (
                    date TEXT PRIMARY KEY,
                    total_alerts INTEGER,
                    critical_alerts INTEGER,
                    false_positives INTEGER,
                    notification_failures INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
    
    def add_condition(self, condition: AlertCondition):
        """Agrega una condición de alerta"""
        self.conditions[condition.name] = condition
        logger.info(f"Condición '{condition.name}' agregada")
    
    def create_price_movement_condition(self, symbol: str, threshold_percent: float):
        """Crea condición para movimientos de precio"""
        def price_condition(data: Dict[str, Any]) -> bool:
            if symbol not in data.get('prices', {}):
                return False
            
            current_price = data['prices'][symbol]['close']
            previous_price = data['prices'][symbol].get('previous_close')
            
            if previous_price is None:
                return False
            
            change_percent = abs((current_price - previous_price) / previous_price * 100)
            return change_percent >= threshold_percent
        
        condition = AlertCondition(
            name=f"price_movement_{symbol}_{threshold_percent}",
            condition_func=price_condition,
            cooldown_minutes=15,
            required_confirmations=1
        )
        
        self.add_condition(condition)
    
    def create_volume_spike_condition(self, symbol: str, multiplier: float = 3.0):
        """Crea condición para picos de volumen"""
        def volume_condition(data: Dict[str, Any]) -> bool:
            if symbol not in data.get('volumes', {}):
                return False
            
            current_volume = data['volumes'][symbol]['current']
            avg_volume = data['volumes'][symbol].get('average_24h')
            
            if avg_volume is None or avg_volume == 0:
                return False
            
            return current_volume >= avg_volume * multiplier
        
        condition = AlertCondition(
            name=f"volume_spike_{symbol}_{multiplier}",
            condition_func=volume_condition,
            cooldown_minutes=30,
            required_confirmations=2
        )
        
        self.add_condition(condition)
    
    def create_anomaly_condition(self, symbol: str):
        """Crea condición para detección de anomalías"""
        def anomaly_condition(data: Dict[str, Any]) -> bool:
            if symbol not in data.get('features', {}):
                return False
            
            features = np.array(data['features'][symbol])
            is_anomaly, confidence = self.anomaly_detector.detect_anomaly(features)
            
            return is_anomaly and confidence > 0.5
        
        condition = AlertCondition(
            name=f"anomaly_{symbol}",
            condition_func=anomaly_condition,
            cooldown_minutes=60,
            required_confirmations=1
        )
        
        self.add_condition(condition)
    
    async def generate_alert(self, alert_type: AlertType, priority: AlertPriority,
                           title: str, message: str, symbol: str = None,
                           data: Dict[str, Any] = None,
                           channels: List[NotificationChannel] = None) -> str:
        """Genera una nueva alerta"""
        
        alert_id = f"{alert_type.value}_{symbol}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            type=alert_type,
            priority=priority,
            title=title,
            message=message,
            symbol=symbol,
            data=data or {},
            channels=channels or [NotificationChannel.EMAIL, NotificationChannel.TELEGRAM]
        )
        
        # Agregar a cola con prioridad
        priority_value = 6 - priority.value  # Invertir para que mayor prioridad = menor número
        self.alert_queue.put((priority_value, alert))
        
        # Guardar en base de datos
        self._save_alert_to_db(alert)
        
        # Actualizar métricas
        self._update_metrics(alert)
        
        logger.info(f"Alerta generada: {alert_id} - {title}")
        return alert_id
    
    def _save_alert_to_db(self, alert: Alert):
        """Guarda alerta en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO alerts 
                (id, type, priority, title, message, symbol, timestamp, data, acknowledged, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.id,
                alert.type.value,
                alert.priority.value,
                alert.title,
                alert.message,
                alert.symbol,
                alert.timestamp.isoformat(),
                json.dumps(alert.data, default=str),
                alert.acknowledged,
                alert.resolved
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error guardando alerta en DB: {e}")
    
    def _update_metrics(self, alert: Alert):
        """Actualiza métricas del sistema"""
        self.metrics['total_alerts'] += 1
        
        # Por tipo
        alert_type = alert.type.value
        if alert_type not in self.metrics['alerts_by_type']:
            self.metrics['alerts_by_type'][alert_type] = 0
        self.metrics['alerts_by_type'][alert_type] += 1
        
        # Por prioridad
        priority = alert.priority.name
        if priority not in self.metrics['alerts_by_priority']:
            self.metrics['alerts_by_priority'][priority] = 0
        self.metrics['alerts_by_priority'][priority] += 1
    
    async def process_alerts(self):
        """Procesa alertas en la cola"""
        while self.running:
            try:
                if not self.alert_queue.empty():
                    priority, alert = self.alert_queue.get()
                    
                    # Enviar notificaciones
                    success = await self.notification_manager.send_notification(alert)
                    
                    if success:
                        self.active_alerts[alert.id] = alert
                        logger.info(f"Alerta {alert.id} procesada exitosamente")
                    else:
                        logger.error(f"Error procesando alerta {alert.id}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error procesando alertas: {e}")
                await asyncio.sleep(5)
    
    def start_monitoring(self):
        """Inicia el monitoreo de alertas"""
        if self.running:
            logger.warning("El monitoreo ya está en ejecución")
            return
        
        self.running = True
        
        # Iniciar procesamiento de alertas
        asyncio.create_task(self.process_alerts())
        
        logger.info("🚀 Monitoreo de alertas iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo de alertas"""
        self.running = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join()
        
        logger.info("⏹️ Monitoreo de alertas detenido")
    
    def acknowledge_alert(self, alert_id: str, user: str = "system"):
        """Marca una alerta como reconocida"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            self._save_alert_to_db(self.active_alerts[alert_id])
            logger.info(f"Alerta {alert_id} reconocida por {user}")
    
    def resolve_alert(self, alert_id: str, user: str = "system"):
        """Marca una alerta como resuelta"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            self._save_alert_to_db(self.active_alerts[alert_id])
            logger.info(f"Alerta {alert_id} resuelta por {user}")
    
    def get_active_alerts(self) -> List[Alert]:
        """Obtiene alertas activas"""
        return [alert for alert in self.active_alerts.values() 
                if not alert.resolved]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del sistema"""
        return self.metrics.copy()
    
    def train_anomaly_detector(self, historical_data: np.ndarray):
        """Entrena el detector de anomalías"""
        return self.anomaly_detector.fit(historical_data)

# Función de prueba
async def test_smart_alert_system():
    """Prueba el sistema de alertas inteligentes"""
    print("🚀 Iniciando prueba del Sistema de Alertas Inteligentes...")
    
    # Crear sistema
    alert_system = SmartAlertSystem()
    
    # Configurar condiciones
    alert_system.create_price_movement_condition("BTCUSDT", 5.0)
    alert_system.create_volume_spike_condition("ETHUSDT", 2.5)
    
    # Generar datos de prueba para entrenamiento
    np.random.seed(42)
    normal_data = np.random.normal(0, 1, (100, 5))
    alert_system.train_anomaly_detector(normal_data)
    
    # Crear condición de anomalía
    alert_system.create_anomaly_condition("BTCUSDT")
    
    # Iniciar monitoreo
    alert_system.start_monitoring()
    
    # Generar alertas de prueba
    await alert_system.generate_alert(
        AlertType.PRICE_MOVEMENT,
        AlertPriority.HIGH,
        "Movimiento significativo de precio",
        "BTCUSDT ha subido 7.5% en los últimos 15 minutos",
        symbol="BTCUSDT",
        data={"price_change": 7.5, "timeframe": "15m"},
        channels=[NotificationChannel.DESKTOP, NotificationChannel.TELEGRAM]
    )
    
    await alert_system.generate_alert(
        AlertType.VOLUME_SPIKE,
        AlertPriority.MEDIUM,
        "Pico de volumen detectado",
        "ETHUSDT muestra volumen 3.2x superior al promedio",
        symbol="ETHUSDT",
        data={"volume_multiplier": 3.2}
    )
    
    await alert_system.generate_alert(
        AlertType.ANOMALY_DETECTION,
        AlertPriority.CRITICAL,
        "Anomalía detectada",
        "Comportamiento anómalo en patrones de trading",
        symbol="BTCUSDT",
        data={"anomaly_score": 0.85, "confidence": 0.92}
    )
    
    # Esperar procesamiento
    await asyncio.sleep(3)
    
    # Mostrar resultados
    active_alerts = alert_system.get_active_alerts()
    metrics = alert_system.get_metrics()
    
    print(f"\n📊 Resultados de la prueba:")
    print(f"✅ Alertas activas: {len(active_alerts)}")
    print(f"📈 Total de alertas generadas: {metrics['total_alerts']}")
    print(f"📋 Alertas por tipo: {metrics['alerts_by_type']}")
    print(f"⚡ Alertas por prioridad: {metrics['alerts_by_priority']}")
    
    # Reconocer y resolver alertas
    for alert in active_alerts[:2]:
        alert_system.acknowledge_alert(alert.id, "test_user")
        alert_system.resolve_alert(alert.id, "test_user")
    
    print(f"✅ {len(active_alerts[:2])} alertas reconocidas y resueltas")
    
    # Detener monitoreo
    alert_system.stop_monitoring()
    
    print("✅ Prueba del Sistema de Alertas Inteligentes completada!")

if __name__ == "__main__":
    asyncio.run(test_smart_alert_system())