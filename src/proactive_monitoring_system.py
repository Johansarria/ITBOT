#!/usr/bin/env python3
"""
Sistema de Monitoreo Proactivo 24/7 Multi-Símbolo
Monitorea continuamente el sistema First Candle y todos los símbolos configurados
con alertas multi-canal y detección automática de anomalías.

Símbolos monitoreados: BTCUSDT, ETHUSDT, ADAUSDT, DOTUSDT, LINKUSDT
Autor: SICAR AI System
Fecha: 2025-01-18
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
import threading
import requests
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import subprocess
import sys
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proactive_monitoring.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Niveles de alerta del sistema"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class MonitoringStatus(Enum):
    """Estados del sistema de monitoreo"""
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"

@dataclass
class AlertMessage:
    """Estructura de mensaje de alerta"""
    timestamp: datetime
    level: AlertLevel
    title: str
    message: str
    symbol: Optional[str] = None
    component: str = "System"
    metadata: Dict[str, Any] = None
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'symbol': self.symbol,
            'component': self.component,
            'metadata': self.metadata or {}
        }

@dataclass
class SystemMetrics:
    """Métricas del sistema"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_status: bool
    api_connectivity: bool
    first_candle_running: bool
    symbols_status: Dict[str, bool]
    last_analysis_time: Optional[datetime] = None
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'disk_percent': self.disk_percent,
            'network_status': self.network_status,
            'api_connectivity': self.api_connectivity,
            'first_candle_running': self.first_candle_running,
            'symbols_status': self.symbols_status,
            'last_analysis_time': self.last_analysis_time.isoformat() if self.last_analysis_time else None
        }

class ProactiveMonitoringSystem:
    """Sistema de Monitoreo Proactivo 24/7 Multi-Símbolo"""
    
    def __init__(self, config_file='proactive_monitoring_config.json'):
        self.config = self.load_config(config_file)
        
        # Símbolos monitoreados (del sistema First Candle)
        self.symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'])
        
        # Base de datos para persistencia
        self.db_path = self.config.get('database_path', 'proactive_monitoring.db')
        self.init_database()
        
        # Estado del sistema
        self.running = False
        self.status = MonitoringStatus.OFFLINE
        self.last_metrics = None
        self.alert_history = []
        
        # Contadores por símbolo
        self.symbol_metrics = {symbol: {} for symbol in self.symbols}
        self.symbol_alerts = {symbol: [] for symbol in self.symbols}
        
        # Hilos de monitoreo
        self.monitoring_thread = None
        self.alert_thread = None
        self.health_check_thread = None
        
        # Control de threading
        self.stop_event = threading.Event()
        self.alert_queue = asyncio.Queue()
        
        logger.info("🚀 Sistema de Monitoreo Proactivo 24/7 Multi-Símbolo inicializado")
        logger.info(f"📊 Símbolos monitoreados: {', '.join(self.symbols)}")
        logger.info(f"💾 Base de datos: {self.db_path}")
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga configuración del sistema"""
        default_config = {
            'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'],
            'monitoring_interval': 30,  # segundos
            'health_check_interval': 60,  # segundos
            'alert_cooldown': 300,  # 5 minutos
            'thresholds': {
                'cpu_warning': 70,
                'cpu_critical': 85,
                'memory_warning': 75,
                'memory_critical': 90,
                'disk_warning': 80,
                'disk_critical': 95,
                'api_timeout': 10,
                'analysis_delay_warning': 300,  # 5 minutos
                'analysis_delay_critical': 900  # 15 minutos
            },
            'notifications': {
                'telegram': {
                    'enabled': True,
                    'bot_token': '',
                    'chat_id': ''
                },
                'email': {
                    'enabled': True,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'username': '',
                    'password': '',
                    'recipients': []
                },
                'webhook': {
                    'enabled': False,
                    'url': '',
                    'headers': {}
                },
                'desktop': {
                    'enabled': True
                }
            },
            'first_candle_system': {
                'script_path': 'real_time_first_candle_system.py',
                'log_file': 'first_candle_system.log',
                'expected_analysis_interval': 3600  # 1 hora
            },
            'database_path': 'proactive_monitoring.db',
            'log_retention_days': 30,
            'max_alert_history': 1000
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
                    logger.info(f"✅ Configuración cargada desde {config_file}")
            else:
                # Crear archivo de configuración por defecto
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                logger.info(f"📝 Archivo de configuración creado: {config_file}")
        except Exception as e:
            logger.error(f"❌ Error cargando configuración: {e}")
        
        return default_config
    
    def init_database(self):
        """Inicializa base de datos de monitoreo"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Tabla de métricas del sistema
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        cpu_percent REAL,
                        memory_percent REAL,
                        disk_percent REAL,
                        network_status BOOLEAN,
                        api_connectivity BOOLEAN,
                        first_candle_running BOOLEAN,
                        symbols_status TEXT,
                        last_analysis_time TEXT,
                        status TEXT
                    )
                """)
                
                # Tabla de alertas
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        symbol TEXT,
                        component TEXT,
                        metadata TEXT,
                        resolved BOOLEAN DEFAULT 0,
                        resolved_at TEXT
                    )
                """)
                
                # Tabla de métricas por símbolo
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS symbol_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        last_analysis TEXT,
                        analysis_count INTEGER DEFAULT 0,
                        signal_count INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0,
                        avg_response_time REAL DEFAULT 0,
                        status TEXT
                    )
                """)
                
                # Tabla de eventos del sistema
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        description TEXT,
                        symbol TEXT,
                        severity TEXT,
                        data TEXT
                    )
                """)
                
                # Índices para optimización
                conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts(level)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_symbol_metrics_symbol ON symbol_metrics(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp)")
                
                conn.commit()
                logger.info("✅ Base de datos de monitoreo inicializada")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
            raise
    
    def start_monitoring(self):
        """Inicia el sistema de monitoreo"""
        if self.running:
            logger.warning("⚠️ Sistema de monitoreo ya está ejecutándose")
            return
        
        self.running = True
        self.status = MonitoringStatus.HEALTHY
        self.stop_event.clear()
        
        # Iniciar hilos de monitoreo
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="MonitoringLoop"
        )
        
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="HealthCheckLoop"
        )
        
        self.alert_thread = threading.Thread(
            target=self._alert_processing_loop,
            daemon=True,
            name="AlertProcessing"
        )
        
        # Iniciar hilos
        self.monitoring_thread.start()
        self.health_check_thread.start()
        self.alert_thread.start()
        
        # Registrar evento de inicio
        self.log_system_event("SYSTEM_START", "Sistema de monitoreo proactivo iniciado")
        
        # Alerta de inicio
        self.send_alert(
            AlertLevel.INFO,
            "🚀 Sistema de Monitoreo Iniciado",
            f"Monitoreo proactivo 24/7 activado para {len(self.symbols)} símbolos"
        )
        
        logger.info("🚀 Sistema de monitoreo proactivo iniciado")
    
    def stop_monitoring(self):
        """Detiene el sistema de monitoreo"""
        if not self.running:
            return
        
        self.running = False
        self.status = MonitoringStatus.OFFLINE
        self.stop_event.set()
        
        # Esperar a que terminen los hilos
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
        
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)
        
        if self.alert_thread and self.alert_thread.is_alive():
            self.alert_thread.join(timeout=5)
        
        # Registrar evento de parada
        self.log_system_event("SYSTEM_STOP", "Sistema de monitoreo detenido")
        
        logger.info("🛑 Sistema de monitoreo detenido")
    
    def _monitoring_loop(self):
        """Bucle principal de monitoreo"""
        logger.info("🔄 Iniciando bucle de monitoreo principal")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Recopilar métricas del sistema
                metrics = self.collect_system_metrics()
                self.last_metrics = metrics
                
                # Evaluar estado del sistema
                self.evaluate_system_health(metrics)
                
                # Guardar métricas en base de datos
                self.save_metrics(metrics)
                
                # Monitorear cada símbolo
                for symbol in self.symbols:
                    self.monitor_symbol(symbol)
                
                # Verificar sistema First Candle
                self.check_first_candle_system()
                
                # Esperar intervalo de monitoreo
                time.sleep(self.config['monitoring_interval'])
                
            except Exception as e:
                logger.error(f"❌ Error en bucle de monitoreo: {e}")
                self.send_alert(
                    AlertLevel.ERROR,
                    "❌ Error en Monitoreo",
                    f"Error en bucle principal: {str(e)}"
                )
                time.sleep(30)  # Esperar antes de reintentar
    
    def _health_check_loop(self):
        """Bucle de verificación de salud del sistema"""
        logger.info("💓 Iniciando bucle de verificación de salud")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Verificar conectividad API
                api_status = self.check_api_connectivity()
                
                # Verificar recursos del sistema
                resource_status = self.check_system_resources()
                
                # Verificar logs del sistema
                log_status = self.check_system_logs()
                
                # Actualizar estado general
                overall_status = self.calculate_overall_status(api_status, resource_status, log_status)
                
                if overall_status != self.status:
                    self.status = overall_status
                    self.send_alert(
                        AlertLevel.WARNING if overall_status == MonitoringStatus.WARNING else AlertLevel.CRITICAL,
                        f"🔄 Cambio de Estado del Sistema",
                        f"Estado del sistema cambió a: {overall_status.value}"
                    )
                
                # Esperar intervalo de health check
                time.sleep(self.config['health_check_interval'])
                
            except Exception as e:
                logger.error(f"❌ Error en health check: {e}")
                time.sleep(60)
    
    def _alert_processing_loop(self):
        """Bucle de procesamiento de alertas"""
        logger.info("📢 Iniciando procesamiento de alertas")
        
        while self.running and not self.stop_event.is_set():
            try:
                # Procesar alertas pendientes
                self.process_pending_alerts()
                
                # Limpiar historial de alertas antiguas
                self.cleanup_old_alerts()
                
                # Esperar antes del siguiente ciclo
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error procesando alertas: {e}")
                time.sleep(60)
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Recopila métricas del sistema"""
        try:
            # Métricas de CPU y memoria
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Estado de red
            network_status = self.check_network_connectivity()
            
            # Conectividad API
            api_connectivity = self.check_api_connectivity()
            
            # Estado del sistema First Candle
            first_candle_running = self.is_first_candle_running()
            
            # Estado de símbolos
            symbols_status = {symbol: self.check_symbol_status(symbol) for symbol in self.symbols}
            
            # Última vez de análisis
            last_analysis_time = self.get_last_analysis_time()
            
            return SystemMetrics(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                network_status=network_status,
                api_connectivity=api_connectivity,
                first_candle_running=first_candle_running,
                symbols_status=symbols_status,
                last_analysis_time=last_analysis_time
            )
            
        except Exception as e:
            logger.error(f"❌ Error recopilando métricas: {e}")
            return None
    
    def check_network_connectivity(self) -> bool:
        """Verifica conectividad de red"""
        try:
            response = requests.get('https://www.google.com', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_api_connectivity(self) -> bool:
        """Verifica conectividad con APIs de trading"""
        try:
            # Verificar Binance API
            response = requests.get('https://api.binance.com/api/v3/ping', timeout=self.config['thresholds']['api_timeout'])
            return response.status_code == 200
        except:
            return False
    
    def is_first_candle_running(self) -> bool:
        """Verifica si el sistema First Candle está ejecutándose"""
        try:
            # Buscar proceso por nombre
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and any('real_time_first_candle_system.py' in cmd for cmd in cmdline):
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception as e:
            logger.error(f"❌ Error verificando First Candle: {e}")
            return False
    
    def check_symbol_status(self, symbol: str) -> bool:
        """Verifica el estado de un símbolo específico"""
        try:
            # Verificar datos de mercado del símbolo
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_last_analysis_time(self) -> Optional[datetime]:
        """Obtiene la hora del último análisis"""
        try:
            log_file = self.config['first_candle_system']['log_file']
            if os.path.exists(log_file):
                # Leer últimas líneas del log para encontrar último análisis
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in reversed(lines[-100:]):  # Revisar últimas 100 líneas
                        if 'análisis completado' in line.lower() or 'analysis completed' in line.lower():
                            # Extraer timestamp del log
                            # Formato esperado: 2025-01-18 08:00:01 - ...
                            try:
                                timestamp_str = line.split(' - ')[0]
                                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                            except:
                                continue
            return None
        except Exception as e:
            logger.error(f"❌ Error obteniendo último análisis: {e}")
            return None
    
    def evaluate_system_health(self, metrics: SystemMetrics):
        """Evalúa la salud del sistema y genera alertas"""
        if not metrics:
            return
        
        thresholds = self.config['thresholds']
        
        # Verificar CPU
        if metrics.cpu_percent >= thresholds['cpu_critical']:
            self.send_alert(
                AlertLevel.CRITICAL,
                "🔥 CPU Crítico",
                f"Uso de CPU: {metrics.cpu_percent:.1f}% (crítico: >{thresholds['cpu_critical']}%)"
            )
        elif metrics.cpu_percent >= thresholds['cpu_warning']:
            self.send_alert(
                AlertLevel.WARNING,
                "⚠️ CPU Alto",
                f"Uso de CPU: {metrics.cpu_percent:.1f}% (advertencia: >{thresholds['cpu_warning']}%)"
            )
        
        # Verificar memoria
        if metrics.memory_percent >= thresholds['memory_critical']:
            self.send_alert(
                AlertLevel.CRITICAL,
                "🔥 Memoria Crítica",
                f"Uso de memoria: {metrics.memory_percent:.1f}% (crítico: >{thresholds['memory_critical']}%)"
            )
        elif metrics.memory_percent >= thresholds['memory_warning']:
            self.send_alert(
                AlertLevel.WARNING,
                "⚠️ Memoria Alta",
                f"Uso de memoria: {metrics.memory_percent:.1f}% (advertencia: >{thresholds['memory_warning']}%)"
            )
        
        # Verificar disco
        if metrics.disk_percent >= thresholds['disk_critical']:
            self.send_alert(
                AlertLevel.CRITICAL,
                "🔥 Disco Crítico",
                f"Uso de disco: {metrics.disk_percent:.1f}% (crítico: >{thresholds['disk_critical']}%)"
            )
        elif metrics.disk_percent >= thresholds['disk_warning']:
            self.send_alert(
                AlertLevel.WARNING,
                "⚠️ Disco Alto",
                f"Uso de disco: {metrics.disk_percent:.1f}% (advertencia: >{thresholds['disk_warning']}%)"
            )
        
        # Verificar conectividad
        if not metrics.network_status:
            self.send_alert(
                AlertLevel.CRITICAL,
                "🌐 Sin Conectividad de Red",
                "No hay conectividad a internet"
            )
        
        if not metrics.api_connectivity:
            self.send_alert(
                AlertLevel.CRITICAL,
                "📡 Sin Conectividad API",
                "No hay conectividad con APIs de trading"
            )
        
        # Verificar sistema First Candle
        if not metrics.first_candle_running:
            self.send_alert(
                AlertLevel.EMERGENCY,
                "🚨 Sistema First Candle Detenido",
                "El sistema First Candle no está ejecutándose"
            )
        
        # Verificar retraso en análisis
        if metrics.last_analysis_time:
            time_since_analysis = (datetime.now(timezone.utc) - metrics.last_analysis_time.replace(tzinfo=timezone.utc)).total_seconds()
            
            if time_since_analysis >= thresholds['analysis_delay_critical']:
                self.send_alert(
                    AlertLevel.CRITICAL,
                    "⏰ Retraso Crítico en Análisis",
                    f"Último análisis hace {time_since_analysis/60:.1f} minutos"
                )
            elif time_since_analysis >= thresholds['analysis_delay_warning']:
                self.send_alert(
                    AlertLevel.WARNING,
                    "⏰ Retraso en Análisis",
                    f"Último análisis hace {time_since_analysis/60:.1f} minutos"
                )
        
        # Verificar estado de símbolos
        for symbol, status in metrics.symbols_status.items():
            if not status:
                self.send_alert(
                    AlertLevel.ERROR,
                    f"📊 Problema con {symbol}",
                    f"No se pueden obtener datos de mercado para {symbol}",
                    symbol=symbol
                )
    
    def monitor_symbol(self, symbol: str):
        """Monitorea un símbolo específico"""
        try:
            # Obtener métricas del símbolo desde el sistema de logging avanzado
            symbol_metrics = self.get_symbol_metrics_from_db(symbol)
            
            # Actualizar métricas locales
            self.symbol_metrics[symbol] = symbol_metrics
            
            # Guardar en base de datos
            self.save_symbol_metrics(symbol, symbol_metrics)
            
        except Exception as e:
            logger.error(f"❌ Error monitoreando {symbol}: {e}")
    
    def get_symbol_metrics_from_db(self, symbol: str) -> Dict[str, Any]:
        """Obtiene métricas de un símbolo desde la base de datos de logging"""
        try:
            # Conectar a la base de datos del sistema de logging avanzado
            logging_db_path = "advanced_logging.db"
            if not os.path.exists(logging_db_path):
                return {}
            
            with sqlite3.connect(logging_db_path) as conn:
                # Obtener estadísticas recientes del símbolo
                cursor = conn.execute("""
                    SELECT COUNT(*) as analyses,
                           MAX(timestamp) as last_analysis
                    FROM decision_contexts 
                    WHERE symbol = ? AND timestamp > datetime('now', '-1 hour')
                """, (symbol,))
                
                result = cursor.fetchone()
                analyses, last_analysis = result if result else (0, None)
                
                return {
                    'recent_analyses': analyses,
                    'last_analysis': last_analysis,
                    'status': 'active' if analyses > 0 else 'inactive'
                }
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo métricas de {symbol}: {e}")
            return {}
    
    def send_alert(self, level: AlertLevel, title: str, message: str, symbol: str = None, component: str = "System"):
        """Envía alerta multi-canal"""
        try:
            alert = AlertMessage(
                timestamp=datetime.now(timezone.utc),
                level=level,
                title=title,
                message=message,
                symbol=symbol,
                component=component
            )
            
            # Verificar cooldown de alertas
            if self.is_alert_in_cooldown(alert):
                return
            
            # Agregar a historial
            self.alert_history.append(alert)
            
            # Guardar en base de datos
            self.save_alert(alert)
            
            # Enviar por todos los canales habilitados
            self.send_telegram_alert(alert)
            self.send_email_alert(alert)
            self.send_webhook_alert(alert)
            self.send_desktop_alert(alert)
            
            logger.info(f"📢 Alerta enviada: {level.value} - {title}")
            
        except Exception as e:
            logger.error(f"❌ Error enviando alerta: {e}")
    
    def is_alert_in_cooldown(self, alert: AlertMessage) -> bool:
        """Verifica si una alerta está en período de cooldown"""
        cooldown_seconds = self.config['alert_cooldown']
        cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
        
        # Buscar alertas similares recientes
        for recent_alert in reversed(self.alert_history[-50:]):  # Revisar últimas 50 alertas
            if (recent_alert.timestamp > cutoff_time and
                recent_alert.title == alert.title and
                recent_alert.symbol == alert.symbol):
                return True
        
        return False
    
    def send_telegram_alert(self, alert: AlertMessage):
        """Envía alerta por Telegram"""
        try:
            telegram_config = self.config['notifications']['telegram']
            if not telegram_config['enabled'] or not telegram_config['bot_token']:
                return
            
            # Formatear mensaje
            emoji_map = {
                AlertLevel.INFO: "ℹ️",
                AlertLevel.WARNING: "⚠️",
                AlertLevel.ERROR: "❌",
                AlertLevel.CRITICAL: "🔥",
                AlertLevel.EMERGENCY: "🚨"
            }
            
            emoji = emoji_map.get(alert.level, "📢")
            symbol_text = f" [{alert.symbol}]" if alert.symbol else ""
            
            text = f"{emoji} *{alert.title}*{symbol_text}\n\n{alert.message}\n\n🕐 {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            
            # Enviar mensaje
            url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
            data = {
                'chat_id': telegram_config['chat_id'],
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.debug(f"✅ Alerta Telegram enviada: {alert.title}")
            else:
                logger.error(f"❌ Error enviando Telegram: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error en alerta Telegram: {e}")
    
    def send_email_alert(self, alert: AlertMessage):
        """Envía alerta por email (deshabilitado temporalmente)"""
        try:
            email_config = self.config['notifications']['email']
            if not email_config['enabled'] or not email_config['recipients']:
                return
            
            # Email temporalmente deshabilitado para evitar problemas de importación
            logger.info(f"📧 Alerta email (simulada): {alert.title}")
            
        except Exception as e:
            logger.error(f"❌ Error en alerta email: {e}")
    

    
    def send_webhook_alert(self, alert: AlertMessage):
        """Envía alerta por webhook"""
        try:
            webhook_config = self.config['notifications']['webhook']
            if not webhook_config['enabled'] or not webhook_config['url']:
                return
            
            # Preparar payload
            payload = alert.to_dict()
            
            # Enviar webhook
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=webhook_config.get('headers', {}),
                timeout=10
            )
            
            if response.status_code in [200, 201, 202]:
                logger.debug(f"✅ Webhook enviado: {alert.title}")
            else:
                logger.error(f"❌ Error webhook: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error en webhook: {e}")
    
    def send_desktop_alert(self, alert: AlertMessage):
        """Envía notificación de escritorio"""
        try:
            desktop_config = self.config['notifications']['desktop']
            if not desktop_config['enabled']:
                return
            
            # En Windows, usar PowerShell para mostrar notificación
            if sys.platform == "win32":
                symbol_text = f" [{alert.symbol}]" if alert.symbol else ""
                title = f"SICAR - {alert.title}{symbol_text}"
                
                ps_command = f'''
                Add-Type -AssemblyName System.Windows.Forms
                $notification = New-Object System.Windows.Forms.NotifyIcon
                $notification.Icon = [System.Drawing.SystemIcons]::Information
                $notification.BalloonTipTitle = "{title}"
                $notification.BalloonTipText = "{alert.message}"
                $notification.Visible = $true
                $notification.ShowBalloonTip(5000)
                '''
                
                subprocess.run(["powershell", "-Command", ps_command], 
                             capture_output=True, text=True, timeout=10)
                
                logger.debug(f"✅ Notificación desktop enviada: {alert.title}")
                
        except Exception as e:
            logger.error(f"❌ Error en notificación desktop: {e}")
    
    def save_metrics(self, metrics: SystemMetrics):
        """Guarda métricas en base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO system_metrics 
                    (timestamp, cpu_percent, memory_percent, disk_percent, 
                     network_status, api_connectivity, first_candle_running, 
                     symbols_status, last_analysis_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp.isoformat(),
                    metrics.cpu_percent,
                    metrics.memory_percent,
                    metrics.disk_percent,
                    metrics.network_status,
                    metrics.api_connectivity,
                    metrics.first_candle_running,
                    json.dumps(metrics.symbols_status),
                    metrics.last_analysis_time.isoformat() if metrics.last_analysis_time else None,
                    self.status.value
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error guardando métricas: {e}")
    
    def save_alert(self, alert: AlertMessage):
        """Guarda alerta en base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO alerts 
                    (timestamp, level, title, message, symbol, component, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.timestamp.isoformat(),
                    alert.level.value,
                    alert.title,
                    alert.message,
                    alert.symbol,
                    alert.component,
                    json.dumps(alert.metadata) if alert.metadata else None
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error guardando alerta: {e}")
    
    def save_symbol_metrics(self, symbol: str, metrics: Dict[str, Any]):
        """Guarda métricas de símbolo en base de datos"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO symbol_metrics 
                    (timestamp, symbol, last_analysis, analysis_count, status)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    symbol,
                    metrics.get('last_analysis'),
                    metrics.get('recent_analyses', 0),
                    metrics.get('status', 'unknown')
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error guardando métricas de {symbol}: {e}")
    
    def log_system_event(self, event_type: str, description: str, symbol: str = None, severity: str = "info", data: Dict = None):
        """Registra evento del sistema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO system_events 
                    (timestamp, event_type, description, symbol, severity, data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    event_type,
                    description,
                    symbol,
                    severity,
                    json.dumps(data) if data else None
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error registrando evento: {e}")
    
    def check_system_resources(self) -> bool:
        """Verifica recursos del sistema"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            thresholds = self.config['thresholds']
            
            return (cpu < thresholds['cpu_critical'] and 
                   memory < thresholds['memory_critical'] and 
                   disk < thresholds['disk_critical'])
        except:
            return False
    
    def check_system_logs(self) -> bool:
        """Verifica logs del sistema por errores críticos"""
        try:
            log_file = self.config['first_candle_system']['log_file']
            if not os.path.exists(log_file):
                return False
            
            # Leer últimas líneas del log
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-50:]  # Últimas 50 líneas
                
                # Buscar errores críticos
                for line in recent_lines:
                    if any(keyword in line.lower() for keyword in ['critical', 'fatal', 'emergency']):
                        return False
            
            return True
        except:
            return False
    
    def calculate_overall_status(self, api_status: bool, resource_status: bool, log_status: bool) -> MonitoringStatus:
        """Calcula el estado general del sistema"""
        if not api_status or not resource_status or not log_status:
            return MonitoringStatus.CRITICAL
        
        if self.last_metrics:
            # Verificar si hay advertencias
            thresholds = self.config['thresholds']
            if (self.last_metrics.cpu_percent >= thresholds['cpu_warning'] or
                self.last_metrics.memory_percent >= thresholds['memory_warning'] or
                self.last_metrics.disk_percent >= thresholds['disk_warning']):
                return MonitoringStatus.WARNING
        
        return MonitoringStatus.HEALTHY
    
    def process_pending_alerts(self):
        """Procesa alertas pendientes"""
        # Implementar lógica de procesamiento de alertas pendientes
        pass
    
    def cleanup_old_alerts(self):
        """Limpia alertas antiguas"""
        try:
            # Mantener solo las últimas alertas según configuración
            max_alerts = self.config['max_alert_history']
            if len(self.alert_history) > max_alerts:
                self.alert_history = self.alert_history[-max_alerts:]
            
            # Limpiar base de datos
            retention_days = self.config['log_retention_days']
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff_date.isoformat(),))
                conn.execute("DELETE FROM system_metrics WHERE timestamp < ?", (cutoff_date.isoformat(),))
                conn.execute("DELETE FROM symbol_metrics WHERE timestamp < ?", (cutoff_date.isoformat(),))
                conn.execute("DELETE FROM system_events WHERE timestamp < ?", (cutoff_date.isoformat(),))
                conn.commit()
                
        except Exception as e:
            logger.error(f"❌ Error limpiando alertas: {e}")
    
    def check_first_candle_system(self):
        """Verifica y reinicia el sistema First Candle si es necesario"""
        try:
            if not self.is_first_candle_running():
                logger.warning("⚠️ Sistema First Candle no está ejecutándose, intentando reiniciar...")
                
                # Intentar reiniciar el sistema
                script_path = self.config['first_candle_system']['script_path']
                
                # Convertir a ruta absoluta si es relativa
                if not os.path.isabs(script_path):
                    # Usar el directorio actual del script de monitoreo como base
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    script_path = os.path.join(current_dir, script_path)
                
                # Normalizar la ruta para Windows
                script_path = os.path.normpath(script_path)
                
                if os.path.exists(script_path):
                    # Obtener el directorio de trabajo correcto
                    work_dir = os.path.dirname(script_path)
                    
                    # Iniciar el proceso con la ruta absoluta
                    subprocess.Popen([sys.executable, script_path], 
                                   cwd=work_dir,
                                   shell=False)
                    
                    logger.info(f"🔄 Reiniciando sistema desde: {script_path}")
                    
                    self.send_alert(
                        AlertLevel.WARNING,
                        "🔄 Reiniciando Sistema First Candle",
                        f"Sistema First Candle reiniciado automáticamente desde {script_path}"
                    )
                    
                    self.log_system_event("SYSTEM_RESTART", f"Sistema First Candle reiniciado automáticamente desde {script_path}")
                else:
                    logger.error(f"❌ Script no encontrado en: {script_path}")
                    self.send_alert(
                        AlertLevel.ERROR,
                        "❌ No se puede reiniciar First Candle",
                        f"Script no encontrado: {script_path}"
                    )
        except Exception as e:
            logger.error(f"❌ Error verificando First Candle: {e}")
    
    def get_status_report(self) -> Dict[str, Any]:
        """Obtiene reporte de estado del sistema"""
        try:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'status': self.status.value,
                'running': self.running,
                'symbols_monitored': self.symbols,
                'last_metrics': self.last_metrics.to_dict() if self.last_metrics else None,
                'symbol_metrics': self.symbol_metrics,
                'recent_alerts': [alert.to_dict() for alert in self.alert_history[-10:]],
                'uptime': time.time() - (self.start_time if hasattr(self, 'start_time') else time.time())
            }
        except Exception as e:
            logger.error(f"❌ Error generando reporte: {e}")
            return {'error': str(e)}

def main():
    """Función principal"""
    try:
        # Crear sistema de monitoreo
        monitoring_system = ProactiveMonitoringSystem()
        
        # Iniciar monitoreo
        monitoring_system.start_monitoring()
        
        # Mantener ejecutándose
        try:
            while True:
                time.sleep(60)
                
                # Mostrar estado cada 10 minutos
                if int(time.time()) % 600 == 0:
                    status = monitoring_system.get_status_report()
                    logger.info(f"📊 Estado del sistema: {status['status']}")
                    
        except KeyboardInterrupt:
            logger.info("🛑 Deteniendo sistema de monitoreo...")
            monitoring_system.stop_monitoring()
            
    except Exception as e:
        logger.error(f"❌ Error en sistema de monitoreo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()