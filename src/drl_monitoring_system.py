#!/usr/bin/env python3
"""
Sistema de Monitoreo DRL en Tiempo Real para SICAR
Monitorea y visualiza el rendimiento del agente DRL integrado con paper trading.
"""

import logging
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import threading
from collections import deque
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class DRLMetrics:
    """Métricas del sistema DRL."""
    timestamp: str
    total_trades: int
    winning_trades: int
    win_rate: float
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    current_capital: float
    portfolio_value: float
    drl_confidence_avg: float
    active_positions: int
    trading_mode: str
    
    # Métricas específicas DRL
    experience_buffer_size: int
    training_episodes: int
    last_actions: Dict[str, int]
    
    # Métricas de rendimiento
    trades_per_hour: float
    avg_trade_duration: float
    risk_adjusted_return: float

@dataclass
class DRLSignalData:
    """Datos de señales DRL."""
    timestamp: str
    symbol: str
    action: int
    action_name: str
    confidence: float
    value_estimate: float
    current_price: float
    position_size: float

class DRLMonitoringSystem:
    """
    Sistema de monitoreo en tiempo real para el agente DRL.
    
    Características:
    - Recolección de métricas en tiempo real
    - Almacenamiento de historial de performance
    - Detección de anomalías
    - Alertas automáticas
    - Exportación de datos para análisis
    """
    
    def __init__(self, 
                 monitoring_interval: int = 30,
                 history_size: int = 1000,
                 alert_thresholds: Dict[str, float] = None):
        """
        Inicializa el sistema de monitoreo DRL.
        
        Args:
            monitoring_interval: Intervalo de monitoreo en segundos
            history_size: Tamaño del historial de métricas
            alert_thresholds: Umbrales para alertas
        """
        self.monitoring_interval = monitoring_interval
        self.history_size = history_size
        
        # Umbrales por defecto para alertas
        self.alert_thresholds = alert_thresholds or {
            'min_win_rate': 40.0,  # %
            'max_drawdown': 15.0,  # %
            'min_confidence': 0.3,
            'max_consecutive_losses': 5,
            'min_sharpe_ratio': 0.5
        }
        
        # Almacenamiento de datos
        self.metrics_history = deque(maxlen=history_size)
        self.signals_history = deque(maxlen=history_size * 2)
        self.alerts_history = deque(maxlen=100)
        
        # Estado del sistema
        self.is_monitoring = False
        self.monitoring_thread = None
        self.integrated_system = None
        
        # Estadísticas de sesión
        self.session_start = datetime.now()
        self.session_stats = {
            'total_monitoring_time': 0.0,
            'total_alerts_generated': 0,
            'peak_performance': 0.0,
            'worst_drawdown': 0.0
        }
        
        logger.info(f"📊 Sistema de Monitoreo DRL inicializado")
        logger.info(f"   ⏱️ Intervalo: {monitoring_interval}s")
        logger.info(f"   📈 Historial: {history_size} registros")
    
    def set_integrated_system(self, integrated_system):
        """
        Establece el sistema integrado a monitorear.
        
        Args:
            integrated_system: Instancia de DRLIntegratedPaperTrading
        """
        self.integrated_system = integrated_system
        logger.info("🔗 Sistema integrado DRL conectado al monitoreo")
    
    def start_monitoring(self):
        """Inicia el monitoreo en tiempo real."""
        if self.is_monitoring:
            logger.warning("El monitoreo ya está activo")
            return
        
        if not self.integrated_system:
            logger.error("No hay sistema integrado configurado")
            return
        
        self.is_monitoring = True
        self.session_start = datetime.now()
        
        # Iniciar hilo de monitoreo
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitoring_thread.start()
        
        logger.info("🚀 Monitoreo DRL iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo."""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        # Actualizar estadísticas de sesión
        session_duration = (datetime.now() - self.session_start).total_seconds()
        self.session_stats['total_monitoring_time'] += session_duration
        
        logger.info("⏹️ Monitoreo DRL detenido")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo."""
        logger.info("🔄 Loop de monitoreo DRL iniciado")
        
        while self.is_monitoring:
            try:
                # Recopilar métricas
                metrics = self._collect_metrics()
                if metrics:
                    self.metrics_history.append(metrics)
                    
                    # Verificar alertas
                    self._check_alerts(metrics)
                    
                    # Actualizar estadísticas de sesión
                    self._update_session_stats(metrics)
                
                # Recopilar señales DRL
                self._collect_drl_signals()
                
                # Esperar siguiente ciclo
                time.sleep(self.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Error en loop de monitoreo: {e}")
                time.sleep(5)  # Esperar antes de reintentar
        
        logger.info("🔄 Loop de monitoreo DRL finalizado")
    
    def _collect_metrics(self) -> Optional[DRLMetrics]:
        """Recopila métricas del sistema integrado."""
        try:
            if not self.integrated_system:
                return None
            
            # Obtener resumen integrado
            summary = self.integrated_system.get_integrated_summary()
            drl_perf = summary.get('drl_performance', {})
            system_status = summary.get('system_status', {})
            
            # Calcular métricas adicionales
            trades_per_hour = self._calculate_trades_per_hour()
            avg_trade_duration = self._calculate_avg_trade_duration()
            risk_adjusted_return = self._calculate_risk_adjusted_return(summary)
            
            metrics = DRLMetrics(
                timestamp=datetime.now().isoformat(),
                total_trades=summary.get('total_trades', 0),
                winning_trades=summary.get('winning_trades', 0),
                win_rate=summary.get('win_rate', 0.0),
                total_pnl=summary.get('total_pnl', 0.0),
                sharpe_ratio=drl_perf.get('sharpe_ratio', 0.0),
                max_drawdown=summary.get('max_drawdown', 0.0),
                current_capital=summary.get('current_capital', 0.0),
                portfolio_value=summary.get('total_portfolio_value', 0.0),
                drl_confidence_avg=drl_perf.get('drl_confidence_avg', 0.0),
                active_positions=system_status.get('active_positions', 0),
                trading_mode=summary.get('trading_mode', 'unknown'),
                experience_buffer_size=0,  # Se actualizará si está disponible
                training_episodes=0,  # Se actualizará si está disponible
                last_actions=drl_perf.get('last_actions', {}),
                trades_per_hour=trades_per_hour,
                avg_trade_duration=avg_trade_duration,
                risk_adjusted_return=risk_adjusted_return
            )
            
            # Agregar datos DRL detallados si están disponibles
            drl_detailed = summary.get('drl_detailed', {})
            if drl_detailed:
                drl_agent_info = drl_detailed.get('drl_agent', {})
                metrics.experience_buffer_size = drl_agent_info.get('experience_buffer_size', 0)
                metrics.training_episodes = drl_agent_info.get('training_count', 0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recopilando métricas: {e}")
            return None
    
    def _collect_drl_signals(self):
        """Recopila señales DRL recientes."""
        try:
            if not self.integrated_system or not self.integrated_system.drl_adapter:
                return
            
            # Obtener señales para cada símbolo
            for symbol in self.integrated_system.symbols:
                signal_data = self.integrated_system.get_drl_signals(symbol)
                if signal_data:
                    # Obtener precio actual y tamaño de posición
                    current_position = self.integrated_system.paper_engine.positions.get(symbol)
                    position_size = current_position.size if current_position else 0.0
                    
                    # Obtener precio actual (simulado)
                    current_price = 0.0
                    if hasattr(self.integrated_system.drl_adapter, 'market_data_history'):
                        history = self.integrated_system.drl_adapter.market_data_history.get(symbol, [])
                        if history:
                            current_price = history[-1].get('price', 0.0)
                    
                    signal = DRLSignalData(
                        timestamp=signal_data['timestamp'],
                        symbol=signal_data['symbol'],
                        action=signal_data['action'],
                        action_name=signal_data['action_name'],
                        confidence=signal_data['confidence'],
                        value_estimate=signal_data['value_estimate'],
                        current_price=current_price,
                        position_size=position_size
                    )
                    
                    self.signals_history.append(signal)
                    
        except Exception as e:
            logger.error(f"Error recopilando señales DRL: {e}")
    
    def _calculate_trades_per_hour(self) -> float:
        """Calcula trades por hora basado en el historial."""
        try:
            if len(self.metrics_history) < 2:
                return 0.0
            
            # Obtener métricas de la última hora
            current_time = datetime.now()
            hour_ago = current_time - timedelta(hours=1)
            
            recent_metrics = [
                m for m in self.metrics_history
                if datetime.fromisoformat(m.timestamp) >= hour_ago
            ]
            
            if len(recent_metrics) < 2:
                return 0.0
            
            trades_diff = recent_metrics[-1].total_trades - recent_metrics[0].total_trades
            time_diff = (
                datetime.fromisoformat(recent_metrics[-1].timestamp) -
                datetime.fromisoformat(recent_metrics[0].timestamp)
            ).total_seconds() / 3600.0  # Convertir a horas
            
            return trades_diff / max(time_diff, 0.01)
            
        except Exception as e:
            logger.error(f"Error calculando trades por hora: {e}")
            return 0.0
    
    def _calculate_avg_trade_duration(self) -> float:
        """Calcula duración promedio de trades."""
        try:
            if not self.integrated_system:
                return 0.0
            
            # Obtener historial de trades
            trade_history = self.integrated_system.paper_engine.trade_history
            if len(trade_history) < 2:
                return 0.0
            
            # Calcular duración promedio de los últimos 10 trades
            recent_trades = trade_history[-10:]
            durations = []
            
            for i in range(1, len(recent_trades)):
                prev_time = datetime.fromisoformat(recent_trades[i-1]['timestamp'])
                curr_time = datetime.fromisoformat(recent_trades[i]['timestamp'])
                duration = (curr_time - prev_time).total_seconds() / 60.0  # minutos
                durations.append(duration)
            
            return np.mean(durations) if durations else 0.0
            
        except Exception as e:
            logger.error(f"Error calculando duración promedio: {e}")
            return 0.0
    
    def _calculate_risk_adjusted_return(self, summary: Dict[str, Any]) -> float:
        """Calcula retorno ajustado por riesgo."""
        try:
            total_return = summary.get('total_return_pct', 0.0)
            max_drawdown = summary.get('max_drawdown', 1.0)
            
            # Evitar división por cero
            if max_drawdown <= 0:
                max_drawdown = 0.01
            
            return total_return / max_drawdown
            
        except Exception as e:
            logger.error(f"Error calculando retorno ajustado por riesgo: {e}")
            return 0.0
    
    def _check_alerts(self, metrics: DRLMetrics):
        """Verifica y genera alertas basadas en umbrales."""
        try:
            alerts = []
            
            # Verificar win rate
            if metrics.win_rate < self.alert_thresholds['min_win_rate']:
                alerts.append({
                    'type': 'LOW_WIN_RATE',
                    'message': f'Win rate bajo: {metrics.win_rate:.1f}% (mín: {self.alert_thresholds["min_win_rate"]}%)',
                    'severity': 'warning',
                    'value': metrics.win_rate,
                    'threshold': self.alert_thresholds['min_win_rate']
                })
            
            # Verificar drawdown
            if metrics.max_drawdown > self.alert_thresholds['max_drawdown']:
                alerts.append({
                    'type': 'HIGH_DRAWDOWN',
                    'message': f'Drawdown alto: {metrics.max_drawdown:.1f}% (máx: {self.alert_thresholds["max_drawdown"]}%)',
                    'severity': 'critical',
                    'value': metrics.max_drawdown,
                    'threshold': self.alert_thresholds['max_drawdown']
                })
            
            # Verificar confianza DRL
            if metrics.drl_confidence_avg < self.alert_thresholds['min_confidence']:
                alerts.append({
                    'type': 'LOW_DRL_CONFIDENCE',
                    'message': f'Confianza DRL baja: {metrics.drl_confidence_avg:.2f} (mín: {self.alert_thresholds["min_confidence"]})',
                    'severity': 'warning',
                    'value': metrics.drl_confidence_avg,
                    'threshold': self.alert_thresholds['min_confidence']
                })
            
            # Verificar Sharpe ratio
            if metrics.sharpe_ratio < self.alert_thresholds['min_sharpe_ratio']:
                alerts.append({
                    'type': 'LOW_SHARPE_RATIO',
                    'message': f'Sharpe ratio bajo: {metrics.sharpe_ratio:.2f} (mín: {self.alert_thresholds["min_sharpe_ratio"]})',
                    'severity': 'info',
                    'value': metrics.sharpe_ratio,
                    'threshold': self.alert_thresholds['min_sharpe_ratio']
                })
            
            # Registrar alertas
            for alert in alerts:
                alert_record = {
                    'timestamp': datetime.now().isoformat(),
                    'metrics_timestamp': metrics.timestamp,
                    **alert
                }
                self.alerts_history.append(alert_record)
                
                # Log según severidad
                if alert['severity'] == 'critical':
                    logger.error(f"🚨 ALERTA CRÍTICA: {alert['message']}")
                elif alert['severity'] == 'warning':
                    logger.warning(f"⚠️ ALERTA: {alert['message']}")
                else:
                    logger.info(f"ℹ️ INFO: {alert['message']}")
            
            if alerts:
                self.session_stats['total_alerts_generated'] += len(alerts)
                
        except Exception as e:
            logger.error(f"Error verificando alertas: {e}")
    
    def _update_session_stats(self, metrics: DRLMetrics):
        """Actualiza estadísticas de la sesión."""
        try:
            # Actualizar pico de performance
            if metrics.total_pnl > self.session_stats['peak_performance']:
                self.session_stats['peak_performance'] = metrics.total_pnl
            
            # Actualizar peor drawdown
            if metrics.max_drawdown > self.session_stats['worst_drawdown']:
                self.session_stats['worst_drawdown'] = metrics.max_drawdown
                
        except Exception as e:
            logger.error(f"Error actualizando estadísticas de sesión: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del monitoreo."""
        try:
            latest_metrics = self.metrics_history[-1] if self.metrics_history else None
            recent_alerts = list(self.alerts_history)[-5:]  # Últimas 5 alertas
            
            session_duration = (datetime.now() - self.session_start).total_seconds()
            
            return {
                'monitoring_active': self.is_monitoring,
                'session_duration_minutes': session_duration / 60.0,
                'metrics_collected': len(self.metrics_history),
                'signals_collected': len(self.signals_history),
                'total_alerts': len(self.alerts_history),
                'latest_metrics': asdict(latest_metrics) if latest_metrics else None,
                'recent_alerts': recent_alerts,
                'session_stats': self.session_stats,
                'alert_thresholds': self.alert_thresholds
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado actual: {e}")
            return {'error': str(e)}
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Obtiene resumen de performance de las últimas N horas.
        
        Args:
            hours: Número de horas hacia atrás
            
        Returns:
            Diccionario con resumen de performance
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            # Filtrar métricas del período
            period_metrics = [
                m for m in self.metrics_history
                if datetime.fromisoformat(m.timestamp) >= cutoff_time
            ]
            
            if not period_metrics:
                return {'error': 'No hay datos para el período especificado'}
            
            # Calcular estadísticas
            win_rates = [m.win_rate for m in period_metrics]
            pnls = [m.total_pnl for m in period_metrics]
            confidences = [m.drl_confidence_avg for m in period_metrics]
            
            return {
                'period_hours': hours,
                'total_data_points': len(period_metrics),
                'performance': {
                    'avg_win_rate': np.mean(win_rates),
                    'min_win_rate': np.min(win_rates),
                    'max_win_rate': np.max(win_rates),
                    'final_pnl': period_metrics[-1].total_pnl,
                    'pnl_change': period_metrics[-1].total_pnl - period_metrics[0].total_pnl,
                    'avg_confidence': np.mean(confidences),
                    'min_confidence': np.min(confidences),
                    'max_confidence': np.max(confidences)
                },
                'trading_activity': {
                    'total_trades': period_metrics[-1].total_trades - period_metrics[0].total_trades,
                    'avg_trades_per_hour': (period_metrics[-1].total_trades - period_metrics[0].total_trades) / hours,
                    'avg_active_positions': np.mean([m.active_positions for m in period_metrics])
                },
                'alerts': {
                    'total_alerts': len([a for a in self.alerts_history 
                                       if datetime.fromisoformat(a['timestamp']) >= cutoff_time]),
                    'critical_alerts': len([a for a in self.alerts_history 
                                          if datetime.fromisoformat(a['timestamp']) >= cutoff_time 
                                          and a['severity'] == 'critical'])
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando resumen de performance: {e}")
            return {'error': str(e)}
    
    def export_data(self, filepath: str, include_signals: bool = True):
        """
        Exporta datos de monitoreo a archivo JSON.
        
        Args:
            filepath: Ruta del archivo
            include_signals: Incluir datos de señales DRL
        """
        try:
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'session_info': {
                    'session_start': self.session_start.isoformat(),
                    'monitoring_interval': self.monitoring_interval,
                    'history_size': self.history_size,
                    'alert_thresholds': self.alert_thresholds
                },
                'metrics_history': [asdict(m) for m in self.metrics_history],
                'alerts_history': list(self.alerts_history),
                'session_stats': self.session_stats,
                'current_status': self.get_current_status()
            }
            
            if include_signals:
                export_data['signals_history'] = [asdict(s) for s in self.signals_history]
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"📁 Datos de monitoreo exportados a: {filepath}")
            
        except Exception as e:
            logger.error(f"Error exportando datos: {e}")


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Crear sistema de monitoreo
    monitoring = DRLMonitoringSystem(
        monitoring_interval=30,
        history_size=1000
    )
    
    print("📊 Sistema de Monitoreo DRL creado!")
    print(f"Estado: {monitoring.get_current_status()}")