"""
Sistema de Alertas y Notificaciones Inteligentes - SICAR 2025
Desarrollado para detectar oportunidades y riesgos en tiempo real
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
from threading import Thread, Event
import sqlite3
from pathlib import Path

# Importaciones opcionales
try:
    import requests
except ImportError:
    requests = None

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Tipos de alertas disponibles"""
    PRICE_MOVEMENT = "price_movement"
    VOLUME_SPIKE = "volume_spike"
    TECHNICAL_SIGNAL = "technical_signal"
    RISK_WARNING = "risk_warning"
    OPPORTUNITY = "opportunity"
    PORTFOLIO_ALERT = "portfolio_alert"
    MARKET_REGIME = "market_regime"
    ANOMALY = "anomaly"

class AlertPriority(Enum):
    """Prioridades de alertas"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class NotificationChannel(Enum):
    """Canales de notificación"""
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    SMS = "sms"
    DESKTOP = "desktop"

@dataclass
class Alert:
    """Estructura de una alerta"""
    id: str
    type: AlertType
    priority: AlertPriority
    symbol: str
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: datetime
    triggered: bool = False
    acknowledged: bool = False
    channels: List[NotificationChannel] = None
    
    def to_dict(self) -> Dict:
        """Convierte la alerta a diccionario"""
        return {
            'id': self.id,
            'type': self.type.value,
            'priority': self.priority.value,
            'symbol': self.symbol,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'triggered': self.triggered,
            'acknowledged': self.acknowledged,
            'channels': [ch.value for ch in (self.channels or [])]
        }

class SmartAlertsSystem:
    """Sistema de Alertas Inteligentes"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Inicializa el sistema de alertas"""
        self.config = config or self._default_config()
        self.alerts: Dict[str, Alert] = {}
        self.rules: Dict[str, Callable] = {}
        self.running = False
        self.stop_event = Event()
        
        # Base de datos para persistencia
        self.db_path = Path("data/alerts.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        
        # Canales de notificación
        self.notification_channels = {
            NotificationChannel.EMAIL: self._send_email,
            NotificationChannel.TELEGRAM: self._send_telegram,
            NotificationChannel.DISCORD: self._send_discord,
            NotificationChannel.WEBHOOK: self._send_webhook,
            NotificationChannel.DESKTOP: self._send_desktop
        }
        
        # Métricas del sistema
        self.metrics = {
            'alerts_generated': 0,
            'alerts_triggered': 0,
            'notifications_sent': 0,
            'false_positives': 0,
            'response_time_avg': 0.0
        }
        
        logger.info("✅ SmartAlertsSystem inicializado")
    
    def _default_config(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            'email': {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_email': ''
            },
            'telegram': {
                'bot_token': '',
                'chat_id': ''
            },
            'discord': {
                'webhook_url': ''
            },
            'thresholds': {
                'price_change_pct': 5.0,
                'volume_spike_multiplier': 3.0,
                'risk_score_threshold': 0.8,
                'drawdown_threshold': 0.15
            },
            'cooldown_minutes': 15,
            'max_alerts_per_hour': 20
        }
    
    def _init_database(self):
        """Inicializa la base de datos SQLite"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    priority INTEGER,
                    symbol TEXT,
                    title TEXT,
                    message TEXT,
                    data TEXT,
                    timestamp TEXT,
                    triggered BOOLEAN,
                    acknowledged BOOLEAN
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id TEXT,
                    action TEXT,
                    timestamp TEXT,
                    details TEXT
                )
            """)
    
    def add_rule(self, name: str, rule_func: Callable, enabled: bool = True):
        """Añade una regla de alerta personalizada"""
        self.rules[name] = {
            'function': rule_func,
            'enabled': enabled,
            'last_triggered': None,
            'trigger_count': 0
        }
        logger.info(f"📋 Regla '{name}' añadida al sistema")
    
    def create_alert(self, 
                    alert_type: AlertType,
                    priority: AlertPriority,
                    symbol: str,
                    title: str,
                    message: str,
                    data: Dict[str, Any] = None,
                    channels: List[NotificationChannel] = None) -> Alert:
        """Crea una nueva alerta"""
        
        alert_id = f"{alert_type.value}_{symbol}_{int(time.time())}"
        
        alert = Alert(
            id=alert_id,
            type=alert_type,
            priority=priority,
            symbol=symbol,
            title=title,
            message=message,
            data=data or {},
            timestamp=datetime.now(),
            channels=channels or [NotificationChannel.DESKTOP]
        )
        
        self.alerts[alert_id] = alert
        self.metrics['alerts_generated'] += 1
        
        # Guardar en base de datos
        self._save_alert_to_db(alert)
        
        logger.info(f"🚨 Alerta creada: {title} ({symbol})")
        return alert
    
    def trigger_alert(self, alert_id: str) -> bool:
        """Dispara una alerta específica"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        
        # Verificar cooldown
        if self._is_in_cooldown(alert):
            return False
        
        # Verificar límite de alertas por hora
        if self._exceeds_hourly_limit():
            return False
        
        alert.triggered = True
        self.metrics['alerts_triggered'] += 1
        
        # Enviar notificaciones
        for channel in alert.channels:
            try:
                self.notification_channels[channel](alert)
                self.metrics['notifications_sent'] += 1
            except Exception as e:
                logger.error(f"❌ Error enviando notificación por {channel.value}: {e}")
        
        # Actualizar base de datos
        self._update_alert_in_db(alert)
        self._log_alert_action(alert_id, "triggered", {"channels": [ch.value for ch in alert.channels]})
        
        logger.info(f"🔔 Alerta disparada: {alert.title}")
        return True
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Marca una alerta como reconocida"""
        if alert_id not in self.alerts:
            return False
        
        alert = self.alerts[alert_id]
        alert.acknowledged = True
        
        self._update_alert_in_db(alert)
        self._log_alert_action(alert_id, "acknowledged", {})
        
        logger.info(f"✅ Alerta reconocida: {alert.title}")
        return True
    
    def start_monitoring(self):
        """Inicia el monitoreo en tiempo real"""
        if self.running:
            return
        
        self.running = True
        self.stop_event.clear()
        
        # Hilo principal de monitoreo
        monitor_thread = Thread(target=self._monitoring_loop, daemon=True)
        monitor_thread.start()
        
        logger.info("🚀 Sistema de alertas iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.running = False
        self.stop_event.set()
        logger.info("⏹️ Sistema de alertas detenido")
    
    def _monitoring_loop(self):
        """Bucle principal de monitoreo"""
        while self.running and not self.stop_event.is_set():
            try:
                # Ejecutar reglas personalizadas
                for rule_name, rule_info in self.rules.items():
                    if rule_info['enabled']:
                        try:
                            rule_info['function'](self)
                        except Exception as e:
                            logger.error(f"❌ Error en regla {rule_name}: {e}")
                
                # Limpiar alertas antiguas
                self._cleanup_old_alerts()
                
                # Esperar antes del siguiente ciclo
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Error en bucle de monitoreo: {e}")
                time.sleep(10)
    
    def _is_in_cooldown(self, alert: Alert) -> bool:
        """Verifica si la alerta está en período de cooldown"""
        cooldown_minutes = self.config.get('cooldown_minutes', 15)
        
        # Buscar alertas similares recientes
        cutoff_time = datetime.now() - timedelta(minutes=cooldown_minutes)
        
        for existing_alert in self.alerts.values():
            if (existing_alert.type == alert.type and 
                existing_alert.symbol == alert.symbol and
                existing_alert.triggered and
                existing_alert.timestamp > cutoff_time):
                return True
        
        return False
    
    def _exceeds_hourly_limit(self) -> bool:
        """Verifica si se excede el límite de alertas por hora"""
        max_alerts = self.config.get('max_alerts_per_hour', 20)
        cutoff_time = datetime.now() - timedelta(hours=1)
        
        recent_alerts = sum(1 for alert in self.alerts.values() 
                          if alert.triggered and alert.timestamp > cutoff_time)
        
        return recent_alerts >= max_alerts
    
    def _cleanup_old_alerts(self):
        """Limpia alertas antiguas"""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        old_alerts = [alert_id for alert_id, alert in self.alerts.items()
                     if alert.timestamp < cutoff_time]
        
        for alert_id in old_alerts:
            del self.alerts[alert_id]
    
    def _save_alert_to_db(self, alert: Alert):
        """Guarda alerta en base de datos"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alerts 
                (id, type, priority, symbol, title, message, data, timestamp, triggered, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id, alert.type.value, alert.priority.value, alert.symbol,
                alert.title, alert.message, json.dumps(alert.data),
                alert.timestamp.isoformat(), alert.triggered, alert.acknowledged
            ))
    
    def _update_alert_in_db(self, alert: Alert):
        """Actualiza alerta en base de datos"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE alerts SET triggered = ?, acknowledged = ? WHERE id = ?
            """, (alert.triggered, alert.acknowledged, alert.id))
    
    def _log_alert_action(self, alert_id: str, action: str, details: Dict):
        """Registra acción de alerta"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alert_history (id, action, timestamp, details)
                VALUES (?, ?, ?, ?)
            """, (alert_id, action, datetime.now().isoformat(), json.dumps(details)))
    
    def _send_email(self, alert: Alert):
        """Envía notificación por email"""
        if not EMAIL_AVAILABLE:
            logger.warning("⚠️ Módulo de email no disponible")
            return
            
        email_config = self.config.get('email', {})
        
        if not all(email_config.get(key) for key in ['smtp_server', 'username', 'password']):
            logger.warning("⚠️ Configuración de email incompleta")
            return
        
        msg = MIMEMultipart()
        msg['From'] = email_config['from_email']
        msg['To'] = email_config['username']
        msg['Subject'] = f"🚨 SICAR Alert: {alert.title}"
        
        body = f"""
        Alerta SICAR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Símbolo: {alert.symbol}
        Tipo: {alert.type.value}
        Prioridad: {alert.priority.name}
        
        {alert.message}
        
        Datos adicionales:
        {json.dumps(alert.data, indent=2)}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
            server.starttls()
            server.login(email_config['username'], email_config['password'])
            server.send_message(msg)
            server.quit()
            logger.info("📧 Email enviado exitosamente")
        except Exception as e:
            logger.error(f"❌ Error enviando email: {e}")
    
    def _send_telegram(self, alert: Alert):
        """Envía notificación por Telegram"""
        if not requests:
            logger.warning("⚠️ Módulo requests no disponible")
            return
            
        telegram_config = self.config.get('telegram', {})
        
        if not all(telegram_config.get(key) for key in ['bot_token', 'chat_id']):
            logger.warning("⚠️ Configuración de Telegram incompleta")
            return
        
        message = f"""
🚨 *SICAR Alert*
        
📊 *{alert.symbol}* - {alert.type.value.upper()}
🔥 *Prioridad:* {alert.priority.name}
        
{alert.message}
        
⏰ {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
        data = {
            'chat_id': telegram_config['chat_id'],
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("📱 Telegram enviado exitosamente")
            else:
                logger.error(f"❌ Error enviando Telegram: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error enviando Telegram: {e}")
    
    def _send_discord(self, alert: Alert):
        """Envía notificación por Discord"""
        if not requests:
            logger.warning("⚠️ Módulo requests no disponible")
            return
            
        discord_config = self.config.get('discord', {})
        
        if not discord_config.get('webhook_url'):
            logger.warning("⚠️ Configuración de Discord incompleta")
            return
        
        embed = {
            "title": f"🚨 SICAR Alert: {alert.title}",
            "description": alert.message,
            "color": self._get_alert_color(alert.priority),
            "fields": [
                {"name": "Símbolo", "value": alert.symbol, "inline": True},
                {"name": "Tipo", "value": alert.type.value, "inline": True},
                {"name": "Prioridad", "value": alert.priority.name, "inline": True}
            ],
            "timestamp": alert.timestamp.isoformat()
        }
        
        data = {"embeds": [embed]}
        
        try:
            response = requests.post(discord_config['webhook_url'], json=data, timeout=10)
            if response.status_code == 204:
                logger.info("🎮 Discord enviado exitosamente")
            else:
                logger.error(f"❌ Error enviando Discord: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error enviando Discord: {e}")
    
    def _send_webhook(self, alert: Alert):
        """Envía notificación por webhook personalizado"""
        if not requests:
            logger.warning("⚠️ Módulo requests no disponible")
            return
            
        webhook_url = self.config.get('webhook_url')
        
        if not webhook_url:
            logger.warning("⚠️ URL de webhook no configurada")
            return
        
        data = alert.to_dict()
        
        try:
            response = requests.post(webhook_url, json=data, timeout=10)
            if response.status_code == 200:
                logger.info("🔗 Webhook enviado exitosamente")
            else:
                logger.error(f"❌ Error enviando webhook: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Error enviando webhook: {e}")
    
    def _send_desktop(self, alert: Alert):
        """Envía notificación de escritorio"""
        try:
            import plyer
            plyer.notification.notify(
                title=f"SICAR Alert: {alert.symbol}",
                message=alert.message,
                timeout=10
            )
            logger.info("🖥️ Notificación de escritorio enviada")
        except ImportError:
            logger.warning("⚠️ Plyer no disponible para notificaciones de escritorio")
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de escritorio: {e}")
    
    def _get_alert_color(self, priority: AlertPriority) -> int:
        """Obtiene color para Discord según prioridad"""
        colors = {
            AlertPriority.LOW: 0x00ff00,      # Verde
            AlertPriority.MEDIUM: 0xffff00,   # Amarillo
            AlertPriority.HIGH: 0xff8000,     # Naranja
            AlertPriority.CRITICAL: 0xff0000  # Rojo
        }
        return colors.get(priority, 0x808080)
    
    def get_active_alerts(self) -> List[Dict]:
        """Obtiene alertas activas"""
        return [alert.to_dict() for alert in self.alerts.values() 
                if alert.triggered and not alert.acknowledged]
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas del sistema"""
        total_alerts = len(self.alerts)
        triggered_alerts = sum(1 for alert in self.alerts.values() if alert.triggered)
        acknowledged_alerts = sum(1 for alert in self.alerts.values() if alert.acknowledged)
        
        return {
            'total_alerts': total_alerts,
            'triggered_alerts': triggered_alerts,
            'acknowledged_alerts': acknowledged_alerts,
            'pending_alerts': triggered_alerts - acknowledged_alerts,
            'metrics': self.metrics,
            'rules_count': len(self.rules),
            'active_rules': sum(1 for rule in self.rules.values() if rule['enabled'])
        }

def test_smart_alerts_system():
    """Función de prueba del sistema de alertas"""
    print("🚀 Iniciando prueba del Sistema de Alertas Inteligentes...")
    
    # Configuración de prueba
    config = {
        'thresholds': {
            'price_change_pct': 3.0,
            'volume_spike_multiplier': 2.0
        },
        'cooldown_minutes': 1,
        'max_alerts_per_hour': 50
    }
    
    # Inicializar sistema
    alerts_system = SmartAlertsSystem(config)
    
    # Crear alertas de prueba
    print("\n📋 Creando alertas de prueba...")
    
    # Alerta de movimiento de precio
    price_alert = alerts_system.create_alert(
        alert_type=AlertType.PRICE_MOVEMENT,
        priority=AlertPriority.HIGH,
        symbol="BTCUSDT",
        title="Movimiento significativo de precio",
        message="BTC ha subido un 8.5% en los últimos 15 minutos",
        data={
            'price_change_pct': 8.5,
            'current_price': 67500,
            'previous_price': 62200,
            'timeframe': '15m'
        },
        channels=[NotificationChannel.DESKTOP]
    )
    
    # Alerta de volumen
    volume_alert = alerts_system.create_alert(
        alert_type=AlertType.VOLUME_SPIKE,
        priority=AlertPriority.MEDIUM,
        symbol="ETHUSDT",
        title="Pico de volumen detectado",
        message="ETH muestra un volumen 4x superior al promedio",
        data={
            'volume_multiplier': 4.2,
            'current_volume': 125000,
            'avg_volume': 29800
        },
        channels=[NotificationChannel.DESKTOP]
    )
    
    # Alerta de riesgo
    risk_alert = alerts_system.create_alert(
        alert_type=AlertType.RISK_WARNING,
        priority=AlertPriority.CRITICAL,
        symbol="PORTFOLIO",
        title="Alerta de riesgo crítico",
        message="El drawdown del portfolio ha superado el 15%",
        data={
            'current_drawdown': 0.187,
            'threshold': 0.15,
            'portfolio_value': 85600
        },
        channels=[NotificationChannel.DESKTOP]
    )
    
    print(f"✅ Creadas {len(alerts_system.alerts)} alertas")
    
    # Disparar alertas
    print("\n🔔 Disparando alertas...")
    alerts_system.trigger_alert(price_alert.id)
    alerts_system.trigger_alert(volume_alert.id)
    alerts_system.trigger_alert(risk_alert.id)
    
    # Reconocer una alerta
    print("\n✅ Reconociendo alerta de volumen...")
    alerts_system.acknowledge_alert(volume_alert.id)
    
    # Mostrar estadísticas
    print("\n📊 Estadísticas del sistema:")
    stats = alerts_system.get_alert_statistics()
    for key, value in stats.items():
        if key != 'metrics':
            print(f"   {key}: {value}")
    
    print("\n📈 Métricas detalladas:")
    for key, value in stats['metrics'].items():
        print(f"   {key}: {value}")
    
    # Mostrar alertas activas
    print("\n🚨 Alertas activas:")
    active_alerts = alerts_system.get_active_alerts()
    for alert in active_alerts:
        print(f"   - {alert['title']} ({alert['symbol']}) - Prioridad: {alert['priority']}")
    
    print("\n✅ Prueba del Sistema de Alertas completada exitosamente!")
    return alerts_system

if __name__ == "__main__":
    test_smart_alerts_system()