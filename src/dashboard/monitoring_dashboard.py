"""
SICAR - Dashboard de Monitoreo Multi-Broker
===========================================

Dashboard web interactivo para monitorear múltiples brokers, sistemas de trading,
sincronización de datos y métricas de rendimiento en tiempo real.

Características:
- Monitoreo en tiempo real de múltiples brokers
- Visualización de métricas de trading
- Estado de sincronización de datos
- Alertas y notificaciones
- Análisis de rendimiento
- Gestión de órdenes
- Monitoreo de VIX y volatilidad

Autor: SICAR Team
Fecha: Enero 2025
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import pandas as pd
import numpy as np
from flask import Flask, render_template, jsonify, request, websocket
from flask_socketio import SocketIO, emit
import plotly.graph_objs as go
import plotly.utils

class AlertLevel(Enum):
    """Niveles de alerta"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class SystemStatus(Enum):
    """Estado del sistema"""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    MAINTENANCE = "MAINTENANCE"
    ERROR = "ERROR"

class MetricType(Enum):
    """Tipos de métricas"""
    PERFORMANCE = "PERFORMANCE"
    LATENCY = "LATENCY"
    VOLUME = "VOLUME"
    ERROR_RATE = "ERROR_RATE"
    SUCCESS_RATE = "SUCCESS_RATE"
    PROFIT_LOSS = "PROFIT_LOSS"

@dataclass
class Alert:
    """Alerta del sistema"""
    id: str
    level: AlertLevel
    title: str
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'id': self.id,
            'level': self.level.value,
            'title': self.title,
            'message': self.message,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'resolved': self.resolved,
            'metadata': self.metadata
        }

@dataclass
class SystemMetric:
    """Métrica del sistema"""
    name: str
    value: float
    unit: str
    metric_type: MetricType
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    
    def get_status(self) -> AlertLevel:
        """Obtener estado basado en umbrales"""
        if self.threshold_critical and self.value >= self.threshold_critical:
            return AlertLevel.CRITICAL
        elif self.threshold_warning and self.value >= self.threshold_warning:
            return AlertLevel.WARNING
        else:
            return AlertLevel.INFO
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'type': self.metric_type.value,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'status': self.get_status().value,
            'threshold_warning': self.threshold_warning,
            'threshold_critical': self.threshold_critical
        }

@dataclass
class BrokerStatus:
    """Estado de un broker"""
    broker_id: str
    name: str
    status: SystemStatus
    connection_status: bool
    last_update: datetime
    orders_today: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    total_pnl: float = 0.0
    available_balance: float = 0.0
    used_margin: float = 0.0
    positions_count: int = 0
    avg_latency: float = 0.0
    error_rate: float = 0.0
    
    def get_success_rate(self) -> float:
        """Calcular tasa de éxito"""
        if self.orders_today == 0:
            return 0.0
        return (self.successful_orders / self.orders_today) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'broker_id': self.broker_id,
            'name': self.name,
            'status': self.status.value,
            'connection_status': self.connection_status,
            'last_update': self.last_update.isoformat(),
            'orders_today': self.orders_today,
            'successful_orders': self.successful_orders,
            'failed_orders': self.failed_orders,
            'success_rate': self.get_success_rate(),
            'total_pnl': self.total_pnl,
            'available_balance': self.available_balance,
            'used_margin': self.used_margin,
            'positions_count': self.positions_count,
            'avg_latency': self.avg_latency,
            'error_rate': self.error_rate
        }

class MonitoringDashboard:
    """
    Dashboard principal de monitoreo
    """
    
    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        
        # Flask app
        self.app = Flask(__name__, template_folder='templates', static_folder='static')
        self.app.config['SECRET_KEY'] = 'sicar_monitoring_dashboard_2025'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Estado del sistema
        self.brokers: Dict[str, BrokerStatus] = {}
        self.alerts: List[Alert] = []
        self.metrics: Dict[str, List[SystemMetric]] = {}  # {metric_name: [metrics]}
        self.is_running = False
        
        # Configuración
        self.max_alerts = 1000
        self.max_metrics_per_type = 1000
        self.update_interval = 1  # segundos
        
        # Callbacks
        self.data_callbacks: List[Callable] = []
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Configurar rutas
        self._setup_routes()
        self._setup_websocket_events()
        
        # Datos simulados para demo
        self._setup_demo_data()
    
    def _setup_routes(self):
        """Configurar rutas de la aplicación"""
        
        @self.app.route('/')
        def index():
            """Página principal"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/brokers')
        def get_brokers():
            """Obtener estado de todos los brokers"""
            return jsonify([broker.to_dict() for broker in self.brokers.values()])
        
        @self.app.route('/api/alerts')
        def get_alerts():
            """Obtener alertas"""
            limit = request.args.get('limit', 50, type=int)
            level = request.args.get('level', None)
            
            alerts = self.alerts[-limit:]
            if level:
                alerts = [a for a in alerts if a.level.value == level.upper()]
            
            return jsonify([alert.to_dict() for alert in alerts])
        
        @self.app.route('/api/metrics/<metric_name>')
        def get_metrics(metric_name):
            """Obtener métricas específicas"""
            limit = request.args.get('limit', 100, type=int)
            
            if metric_name not in self.metrics:
                return jsonify([])
            
            metrics = self.metrics[metric_name][-limit:]
            return jsonify([metric.to_dict() for metric in metrics])
        
        @self.app.route('/api/summary')
        def get_summary():
            """Obtener resumen del sistema"""
            total_brokers = len(self.brokers)
            online_brokers = len([b for b in self.brokers.values() if b.status == SystemStatus.ONLINE])
            total_alerts = len(self.alerts)
            critical_alerts = len([a for a in self.alerts if a.level == AlertLevel.CRITICAL and not a.resolved])
            
            total_pnl = sum(broker.total_pnl for broker in self.brokers.values())
            total_orders = sum(broker.orders_today for broker in self.brokers.values())
            avg_success_rate = np.mean([broker.get_success_rate() for broker in self.brokers.values()]) if self.brokers else 0
            
            return jsonify({
                'total_brokers': total_brokers,
                'online_brokers': online_brokers,
                'offline_brokers': total_brokers - online_brokers,
                'total_alerts': total_alerts,
                'critical_alerts': critical_alerts,
                'total_pnl': total_pnl,
                'total_orders': total_orders,
                'avg_success_rate': avg_success_rate,
                'system_uptime': self._get_system_uptime(),
                'last_update': datetime.now().isoformat()
            })
        
        @self.app.route('/api/charts/pnl')
        def get_pnl_chart():
            """Obtener gráfico de P&L"""
            # Simular datos históricos de P&L
            dates = pd.date_range(start=datetime.now() - timedelta(days=30), end=datetime.now(), freq='D')
            cumulative_pnl = np.cumsum(np.random.normal(100, 500, len(dates)))
            
            trace = go.Scatter(
                x=dates,
                y=cumulative_pnl,
                mode='lines',
                name='P&L Acumulado',
                line=dict(color='#2E8B57', width=2)
            )
            
            layout = go.Layout(
                title='P&L Acumulado (30 días)',
                xaxis=dict(title='Fecha'),
                yaxis=dict(title='P&L ($)'),
                template='plotly_white'
            )
            
            fig = go.Figure(data=[trace], layout=layout)
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        @self.app.route('/api/charts/orders')
        def get_orders_chart():
            """Obtener gráfico de órdenes"""
            broker_names = [broker.name for broker in self.brokers.values()]
            successful_orders = [broker.successful_orders for broker in self.brokers.values()]
            failed_orders = [broker.failed_orders for broker in self.brokers.values()]
            
            trace1 = go.Bar(name='Exitosas', x=broker_names, y=successful_orders, marker_color='#2E8B57')
            trace2 = go.Bar(name='Fallidas', x=broker_names, y=failed_orders, marker_color='#DC143C')
            
            layout = go.Layout(
                title='Órdenes por Broker (Hoy)',
                xaxis=dict(title='Broker'),
                yaxis=dict(title='Número de Órdenes'),
                barmode='stack',
                template='plotly_white'
            )
            
            fig = go.Figure(data=[trace1, trace2], layout=layout)
            return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        @self.app.route('/api/alerts/<alert_id>/acknowledge', methods=['POST'])
        def acknowledge_alert(alert_id):
            """Reconocer alerta"""
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    self._emit_alert_update(alert)
                    return jsonify({'success': True})
            
            return jsonify({'success': False, 'error': 'Alert not found'}), 404
        
        @self.app.route('/api/alerts/<alert_id>/resolve', methods=['POST'])
        def resolve_alert(alert_id):
            """Resolver alerta"""
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.resolved = True
                    self._emit_alert_update(alert)
                    return jsonify({'success': True})
            
            return jsonify({'success': False, 'error': 'Alert not found'}), 404
    
    def _setup_websocket_events(self):
        """Configurar eventos de WebSocket"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Cliente conectado"""
            self.logger.info(f"Cliente conectado: {request.sid}")
            emit('connected', {'message': 'Conectado al dashboard de monitoreo'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Cliente desconectado"""
            self.logger.info(f"Cliente desconectado: {request.sid}")
        
        @self.socketio.on('subscribe_broker')
        def handle_subscribe_broker(data):
            """Suscribirse a actualizaciones de broker"""
            broker_id = data.get('broker_id')
            if broker_id in self.brokers:
                emit('broker_subscribed', {'broker_id': broker_id})
        
        @self.socketio.on('request_data')
        def handle_request_data():
            """Solicitar datos actuales"""
            emit('data_update', {
                'brokers': [broker.to_dict() for broker in self.brokers.values()],
                'alerts': [alert.to_dict() for alert in self.alerts[-10:]],
                'timestamp': datetime.now().isoformat()
            })
    
    def _setup_demo_data(self):
        """Configurar datos de demostración"""
        # Brokers de ejemplo
        self.add_broker(BrokerStatus(
            broker_id="IB_MAIN",
            name="Interactive Brokers",
            status=SystemStatus.ONLINE,
            connection_status=True,
            last_update=datetime.now(),
            orders_today=45,
            successful_orders=42,
            failed_orders=3,
            total_pnl=2450.75,
            available_balance=50000.00,
            used_margin=15000.00,
            positions_count=8,
            avg_latency=125.5,
            error_rate=6.7
        ))
        
        self.add_broker(BrokerStatus(
            broker_id="TDA_MAIN",
            name="TD Ameritrade",
            status=SystemStatus.ONLINE,
            connection_status=True,
            last_update=datetime.now(),
            orders_today=32,
            successful_orders=30,
            failed_orders=2,
            total_pnl=1875.25,
            available_balance=35000.00,
            used_margin=8500.00,
            positions_count=5,
            avg_latency=98.2,
            error_rate=6.25
        ))
        
        self.add_broker(BrokerStatus(
            broker_id="CRYPTO_MAIN",
            name="Crypto Exchange",
            status=SystemStatus.DEGRADED,
            connection_status=True,
            last_update=datetime.now() - timedelta(minutes=2),
            orders_today=78,
            successful_orders=71,
            failed_orders=7,
            total_pnl=-325.50,
            available_balance=25000.00,
            used_margin=12000.00,
            positions_count=12,
            avg_latency=245.8,
            error_rate=8.97
        ))
        
        # Alertas de ejemplo
        self.add_alert(Alert(
            id="alert_001",
            level=AlertLevel.WARNING,
            title="Alta Latencia Detectada",
            message="El broker Crypto Exchange está experimentando latencias superiores a 200ms",
            source="CRYPTO_MAIN"
        ))
        
        self.add_alert(Alert(
            id="alert_002",
            level=AlertLevel.INFO,
            title="Conexión Restaurada",
            message="La conexión con TD Ameritrade ha sido restaurada exitosamente",
            source="TDA_MAIN"
        ))
    
    def add_broker(self, broker: BrokerStatus):
        """Agregar o actualizar broker"""
        self.brokers[broker.broker_id] = broker
        self._emit_broker_update(broker)
    
    def update_broker(self, broker_id: str, **kwargs):
        """Actualizar datos de broker"""
        if broker_id in self.brokers:
            broker = self.brokers[broker_id]
            for key, value in kwargs.items():
                if hasattr(broker, key):
                    setattr(broker, key, value)
            
            broker.last_update = datetime.now()
            self._emit_broker_update(broker)
    
    def add_alert(self, alert: Alert):
        """Agregar nueva alerta"""
        self.alerts.append(alert)
        
        # Mantener límite de alertas
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        self._emit_alert_update(alert)
        self.logger.info(f"Nueva alerta: {alert.level.value} - {alert.title}")
    
    def add_metric(self, metric: SystemMetric):
        """Agregar nueva métrica"""
        if metric.name not in self.metrics:
            self.metrics[metric.name] = []
        
        self.metrics[metric.name].append(metric)
        
        # Mantener límite de métricas
        if len(self.metrics[metric.name]) > self.max_metrics_per_type:
            self.metrics[metric.name] = self.metrics[metric.name][-self.max_metrics_per_type:]
        
        # Verificar umbrales y generar alertas si es necesario
        status = metric.get_status()
        if status in [AlertLevel.WARNING, AlertLevel.CRITICAL]:
            alert = Alert(
                id=f"metric_{metric.name}_{int(time.time())}",
                level=status,
                title=f"Umbral de {metric.name} Excedido",
                message=f"{metric.name} ha alcanzado {metric.value} {metric.unit} en {metric.source}",
                source=metric.source,
                metadata={'metric': metric.to_dict()}
            )
            self.add_alert(alert)
        
        self._emit_metric_update(metric)
    
    def _emit_broker_update(self, broker: BrokerStatus):
        """Emitir actualización de broker via WebSocket"""
        if hasattr(self, 'socketio'):
            self.socketio.emit('broker_update', broker.to_dict())
    
    def _emit_alert_update(self, alert: Alert):
        """Emitir actualización de alerta via WebSocket"""
        if hasattr(self, 'socketio'):
            self.socketio.emit('alert_update', alert.to_dict())
    
    def _emit_metric_update(self, metric: SystemMetric):
        """Emitir actualización de métrica via WebSocket"""
        if hasattr(self, 'socketio'):
            self.socketio.emit('metric_update', metric.to_dict())
    
    def _get_system_uptime(self) -> str:
        """Obtener tiempo de actividad del sistema"""
        # Simulado para demo
        uptime_seconds = 3600 * 24 * 5  # 5 días
        days = uptime_seconds // (3600 * 24)
        hours = (uptime_seconds % (3600 * 24)) // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        return f"{days}d {hours}h {minutes}m"
    
    async def start_monitoring_loop(self):
        """Iniciar loop de monitoreo en background"""
        self.is_running = True
        
        while self.is_running:
            try:
                # Simular actualizaciones de datos
                await self._simulate_data_updates()
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Error en loop de monitoreo: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _simulate_data_updates(self):
        """Simular actualizaciones de datos para demo"""
        # Actualizar métricas de brokers
        for broker_id, broker in self.brokers.items():
            # Simular cambios en latencia
            new_latency = max(50, broker.avg_latency + np.random.normal(0, 10))
            self.update_broker(broker_id, avg_latency=new_latency)
            
            # Agregar métrica de latencia
            latency_metric = SystemMetric(
                name="latency",
                value=new_latency,
                unit="ms",
                metric_type=MetricType.LATENCY,
                source=broker_id,
                threshold_warning=200.0,
                threshold_critical=500.0
            )
            self.add_metric(latency_metric)
            
            # Simular nuevas órdenes ocasionalmente
            if np.random.random() < 0.1:  # 10% probabilidad
                success = np.random.random() > 0.05  # 95% tasa de éxito
                if success:
                    self.update_broker(broker_id, 
                                     successful_orders=broker.successful_orders + 1,
                                     orders_today=broker.orders_today + 1)
                else:
                    self.update_broker(broker_id,
                                     failed_orders=broker.failed_orders + 1,
                                     orders_today=broker.orders_today + 1)
            
            # Simular cambios en P&L
            pnl_change = np.random.normal(0, 50)
            new_pnl = broker.total_pnl + pnl_change
            self.update_broker(broker_id, total_pnl=new_pnl)
    
    def run(self, debug: bool = False):
        """Ejecutar dashboard"""
        self.logger.info(f"Iniciando dashboard en http://{self.host}:{self.port}")
        
        # Iniciar loop de monitoreo en background
        import threading
        
        def run_monitoring():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_monitoring_loop())
        
        monitoring_thread = threading.Thread(target=run_monitoring, daemon=True)
        monitoring_thread.start()
        
        # Ejecutar Flask app
        self.socketio.run(self.app, host=self.host, port=self.port, debug=debug)
    
    def stop(self):
        """Detener dashboard"""
        self.is_running = False
        self.logger.info("Dashboard detenido")

# Template HTML para el dashboard
DASHBOARD_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SICAR - Dashboard de Monitoreo</title>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .status-online { color: #28a745; }
        .status-offline { color: #dc3545; }
        .status-degraded { color: #ffc107; }
        .alert-critical { border-left: 4px solid #dc3545; }
        .alert-warning { border-left: 4px solid #ffc107; }
        .alert-info { border-left: 4px solid #17a2b8; }
        .metric-card { transition: all 0.3s ease; }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
        .real-time-indicator { 
            display: inline-block; 
            width: 8px; 
            height: 8px; 
            background-color: #28a745; 
            border-radius: 50%; 
            animation: pulse 2s infinite; 
        }
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body class="bg-light">
    <nav class="navbar navbar-dark bg-dark">
        <div class="container-fluid">
            <span class="navbar-brand mb-0 h1">
                <i class="fas fa-chart-line"></i> SICAR - Dashboard de Monitoreo
                <span class="real-time-indicator ms-2"></span>
            </span>
            <span class="navbar-text" id="last-update">
                Última actualización: --
            </span>
        </div>
    </nav>

    <div class="container-fluid mt-3">
        <!-- Resumen del Sistema -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">Brokers Online</h5>
                        <h2 class="text-success" id="online-brokers">--</h2>
                        <small class="text-muted">de <span id="total-brokers">--</span> total</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">P&L Total</h5>
                        <h2 id="total-pnl" class="text-success">$--</h2>
                        <small class="text-muted">Hoy</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">Órdenes</h5>
                        <h2 class="text-primary" id="total-orders">--</h2>
                        <small class="text-muted">Ejecutadas hoy</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card metric-card">
                    <div class="card-body text-center">
                        <h5 class="card-title">Alertas Críticas</h5>
                        <h2 class="text-danger" id="critical-alerts">--</h2>
                        <small class="text-muted">Sin resolver</small>
                    </div>
                </div>
            </div>
        </div>

        <!-- Estado de Brokers -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-server"></i> Estado de Brokers</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover">
                                <thead>
                                    <tr>
                                        <th>Broker</th>
                                        <th>Estado</th>
                                        <th>Órdenes Hoy</th>
                                        <th>Tasa Éxito</th>
                                        <th>P&L</th>
                                        <th>Latencia</th>
                                        <th>Última Act.</th>
                                    </tr>
                                </thead>
                                <tbody id="brokers-table">
                                    <!-- Datos dinámicos -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Gráficos -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-area"></i> P&L Acumulado</h5>
                    </div>
                    <div class="card-body">
                        <div id="pnl-chart" style="height: 300px;"></div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-bar"></i> Órdenes por Broker</h5>
                    </div>
                    <div class="card-body">
                        <div id="orders-chart" style="height: 300px;"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Alertas -->
        <div class="row">
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-exclamation-triangle"></i> Alertas Recientes</h5>
                    </div>
                    <div class="card-body">
                        <div id="alerts-container">
                            <!-- Alertas dinámicas -->
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Configurar WebSocket
        const socket = io();
        
        socket.on('connect', function() {
            console.log('Conectado al dashboard');
            socket.emit('request_data');
        });
        
        socket.on('data_update', function(data) {
            updateDashboard(data);
        });
        
        socket.on('broker_update', function(broker) {
            updateBrokerRow(broker);
        });
        
        socket.on('alert_update', function(alert) {
            addAlert(alert);
        });
        
        // Funciones de actualización
        function updateDashboard(data) {
            // Actualizar resumen
            updateSummary();
            
            // Actualizar tabla de brokers
            updateBrokersTable(data.brokers);
            
            // Actualizar alertas
            updateAlerts(data.alerts);
            
            // Actualizar timestamp
            document.getElementById('last-update').textContent = 
                'Última actualización: ' + new Date().toLocaleTimeString();
        }
        
        function updateSummary() {
            fetch('/api/summary')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('online-brokers').textContent = data.online_brokers;
                    document.getElementById('total-brokers').textContent = data.total_brokers;
                    document.getElementById('total-pnl').textContent = '$' + data.total_pnl.toFixed(2);
                    document.getElementById('total-pnl').className = data.total_pnl >= 0 ? 'text-success' : 'text-danger';
                    document.getElementById('total-orders').textContent = data.total_orders;
                    document.getElementById('critical-alerts').textContent = data.critical_alerts;
                });
        }
        
        function updateBrokersTable(brokers) {
            const tbody = document.getElementById('brokers-table');
            tbody.innerHTML = '';
            
            brokers.forEach(broker => {
                const row = createBrokerRow(broker);
                tbody.appendChild(row);
            });
        }
        
        function createBrokerRow(broker) {
            const row = document.createElement('tr');
            row.id = 'broker-' + broker.broker_id;
            
            const statusClass = {
                'ONLINE': 'status-online',
                'OFFLINE': 'status-offline',
                'DEGRADED': 'status-degraded'
            }[broker.status] || '';
            
            const successRateClass = broker.success_rate >= 95 ? 'text-success' : 
                                   broker.success_rate >= 90 ? 'text-warning' : 'text-danger';
            
            const pnlClass = broker.total_pnl >= 0 ? 'text-success' : 'text-danger';
            
            row.innerHTML = `
                <td><strong>${broker.name}</strong></td>
                <td><i class="fas fa-circle ${statusClass}"></i> ${broker.status}</td>
                <td>${broker.successful_orders}/${broker.orders_today}</td>
                <td><span class="${successRateClass}">${broker.success_rate.toFixed(1)}%</span></td>
                <td><span class="${pnlClass}">$${broker.total_pnl.toFixed(2)}</span></td>
                <td>${broker.avg_latency.toFixed(0)}ms</td>
                <td>${new Date(broker.last_update).toLocaleTimeString()}</td>
            `;
            
            return row;
        }
        
        function updateBrokerRow(broker) {
            const existingRow = document.getElementById('broker-' + broker.broker_id);
            if (existingRow) {
                const newRow = createBrokerRow(broker);
                existingRow.parentNode.replaceChild(newRow, existingRow);
            }
        }
        
        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            container.innerHTML = '';
            
            alerts.forEach(alert => {
                addAlert(alert);
            });
        }
        
        function addAlert(alert) {
            const container = document.getElementById('alerts-container');
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${alert.level.toLowerCase()} alert-${alert.level.toLowerCase()} mb-2`;
            
            const timeAgo = getTimeAgo(new Date(alert.timestamp));
            
            alertDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <strong>${alert.title}</strong>
                        <p class="mb-1">${alert.message}</p>
                        <small class="text-muted">
                            <i class="fas fa-clock"></i> ${timeAgo} - 
                            <i class="fas fa-server"></i> ${alert.source}
                        </small>
                    </div>
                    <div>
                        ${!alert.acknowledged ? `<button class="btn btn-sm btn-outline-secondary me-1" onclick="acknowledgeAlert('${alert.id}')">Reconocer</button>` : ''}
                        ${!alert.resolved ? `<button class="btn btn-sm btn-outline-success" onclick="resolveAlert('${alert.id}')">Resolver</button>` : ''}
                    </div>
                </div>
            `;
            
            container.insertBefore(alertDiv, container.firstChild);
        }
        
        function acknowledgeAlert(alertId) {
            fetch(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateSummary();
                    }
                });
        }
        
        function resolveAlert(alertId) {
            fetch(`/api/alerts/${alertId}/resolve`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateSummary();
                    }
                });
        }
        
        function getTimeAgo(date) {
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            
            if (diffMins < 1) return 'Ahora';
            if (diffMins < 60) return `${diffMins}m`;
            if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h`;
            return `${Math.floor(diffMins / 1440)}d`;
        }
        
        // Cargar gráficos
        function loadCharts() {
            // Gráfico P&L
            fetch('/api/charts/pnl')
                .then(response => response.json())
                .then(data => {
                    Plotly.newPlot('pnl-chart', data.data, data.layout, {responsive: true});
                });
            
            // Gráfico de órdenes
            fetch('/api/charts/orders')
                .then(response => response.json())
                .then(data => {
                    Plotly.newPlot('orders-chart', data.data, data.layout, {responsive: true});
                });
        }
        
        // Inicializar dashboard
        document.addEventListener('DOMContentLoaded', function() {
            updateSummary();
            loadCharts();
            
            // Actualizar cada 30 segundos
            setInterval(updateSummary, 30000);
            setInterval(loadCharts, 60000);
        });
    </script>
</body>
</html>
"""

def create_dashboard_template():
    """Crear archivo de template HTML"""
    import os
    
    # Crear directorio templates si no existe
    templates_dir = "C:/Users/johan/OneDrive/Escritorio/SICAR/sicar_project/src/dashboard/templates"
    os.makedirs(templates_dir, exist_ok=True)
    
    # Escribir template
    template_path = os.path.join(templates_dir, "dashboard.html")
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(DASHBOARD_HTML_TEMPLATE)
    
    return template_path

# Demo y testing
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    print("=== SICAR - Dashboard de Monitoreo Demo ===\n")
    
    # Crear template HTML
    template_path = create_dashboard_template()
    print(f"Template HTML creado en: {template_path}")
    
    # Crear dashboard
    dashboard = MonitoringDashboard(host="localhost", port=5000)
    
    print("\nIniciando dashboard...")
    print("Accede a: http://localhost:5000")
    print("Presiona Ctrl+C para detener\n")
    
    try:
        dashboard.run(debug=True)
    except KeyboardInterrupt:
        print("\nDeteniendo dashboard...")
        dashboard.stop()
        print("Dashboard detenido")