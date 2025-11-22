"""
Gestor de Integración Mejorada para SICAR
Conecta todos los sistemas optimizados sin interrumpir la simulación actual
"""

import asyncio
import json
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from enhanced_logger import SICAR_LOGGER
from autonomous_decision_engine import AUTONOMOUS_ENGINE, get_autonomous_status
from advanced_pattern_recognition import PATTERN_RECOGNITION_SYSTEM, get_pattern_stats
from enhanced_xai_breakout_integration import EnhancedXAIBreakoutSystem
from module_xai import generate_dynamic_cognitive_report

logger = logging.getLogger(__name__)

class EnhancedIntegrationManager:
    """Gestor principal de la integración mejorada"""
    
    def __init__(self):
        self.is_active = False
        self.integration_thread = None
        self.performance_monitor = None
        
        # Sistemas integrados
        self.autonomous_engine = AUTONOMOUS_ENGINE
        self.pattern_system = PATTERN_RECOGNITION_SYSTEM
        self.xai_breakout_system = EnhancedXAIBreakoutSystem()
        
        # Módulos XAI individuales (se inicializan en _initialize_systems)
        self.metacontroller = None
        self.regime_classifier = None
        self.causal_cartographer = None
        
        # Métricas de rendimiento
        self.performance_metrics = {
            'integration_start_time': None,
            'total_decisions': 0,
            'successful_integrations': 0,
            'total_integration_attempts': 0,  # Nuevo: total de intentos de integración
            'pattern_detections': 0,
            'xai_analyses': 0,
            'breakout_alerts': 0,
            'system_uptime': 0,
            'last_update': datetime.now()
        }
        
        # Configuración
        self.config = {
            'monitoring_interval': 15,  # segundos
            'performance_log_interval': 300,  # 5 minutos
            'auto_optimization': True,
            'adaptive_thresholds': True,
            'real_time_feedback': True
        }
        
        SICAR_LOGGER.log_alert("INTEGRATION_MANAGER_INIT", 
                              "Gestor de integración mejorada inicializado", "INFO")
    
    async def start_enhanced_integration(self):
        """Iniciar la integración mejorada sin interrumpir la simulación"""
        try:
            if self.is_active:
                SICAR_LOGGER.log_warning("INTEGRATION_START", "La integración ya está activa")
                return False
            
            self.is_active = True
            self.performance_metrics['integration_start_time'] = datetime.now()
            
            SICAR_LOGGER.log_alert("INTEGRATION_START", 
                                  "Iniciando integración mejorada de sistemas SICAR", "INFO")
            
            # Iniciar sistemas en paralelo
            await self._initialize_systems()
            
            # Iniciar monitoreo de rendimiento
            self._start_performance_monitoring()
            
            # Iniciar bucle principal de integración
            self.integration_thread = threading.Thread(
                target=self._run_integration_loop,
                daemon=True
            )
            self.integration_thread.start()
            
            SICAR_LOGGER.log_alert("INTEGRATION_ACTIVE", 
                                  "Integración mejorada activa y funcionando", "INFO")
            
            return True
            
        except Exception as e:
            SICAR_LOGGER.log_error("INTEGRATION_START", f"Error iniciando integración: {e}")
            self.is_active = False
            return False
    
    async def stop_enhanced_integration(self):
        """Detener la integración mejorada"""
        try:
            if not self.is_active:
                return True
            
            self.is_active = False
            
            # Detener sistemas
            await self.autonomous_engine.stop_autonomous_trading()
            self.xai_breakout_system.stop_system()
            
            # Esperar a que termine el hilo
            if self.integration_thread and self.integration_thread.is_alive():
                self.integration_thread.join(timeout=5)
            
            SICAR_LOGGER.log_alert("INTEGRATION_STOP", 
                                  "Integración mejorada detenida correctamente", "INFO")
            
            return True
            
        except Exception as e:
            SICAR_LOGGER.log_error("INTEGRATION_STOP", f"Error deteniendo integración: {e}")
            return False
    
    async def _initialize_systems(self):
        """Inicializar todos los sistemas integrados"""
        try:
            # Inicializar módulos XAI individuales
            try:
                from module_1_causal import CausalCartographer
                from module_2_regime import RegimeClassifier  
                from module_3_metacontroller import MetaController
                
                # Inicializar módulos XAI si no están ya inicializados
                if not hasattr(self, 'causal_cartographer') or not self.causal_cartographer:
                    self.causal_cartographer = CausalCartographer()
                    SICAR_LOGGER.log_alert("XAI_INIT", "CausalCartographer inicializado", "INFO")
                
                if not hasattr(self, 'regime_classifier') or not self.regime_classifier:
                    self.regime_classifier = RegimeClassifier()
                    SICAR_LOGGER.log_alert("XAI_INIT", "RegimeClassifier inicializado", "INFO")
                
                if not hasattr(self, 'metacontroller') or not self.metacontroller:
                    self.metacontroller = MetaController()
                    SICAR_LOGGER.log_alert("XAI_INIT", "MetaController inicializado", "INFO")
                    
            except ImportError as e:
                SICAR_LOGGER.log_warning("XAI_INIT", f"No se pudieron importar módulos XAI: {e}")
                self.metacontroller = None
                self.regime_classifier = None
                self.causal_cartographer = None
            
            # Inicializar sistema XAI-Breakout
            self.xai_breakout_system.start_system()
            
            # Configurar motor autónomo para modo no intrusivo
            self.autonomous_engine.config.update({
                'enable_autonomous_execution': False,  # Solo análisis, no ejecución real
                'decision_interval': 30,
                'min_confidence_threshold': 0.75
            })
            
            # Iniciar motor autónomo en modo análisis
            asyncio.create_task(self.autonomous_engine.start_autonomous_trading())
            
            SICAR_LOGGER.log_alert("SYSTEMS_INIT", "Sistemas integrados inicializados correctamente", "INFO")
            
        except Exception as e:
            SICAR_LOGGER.log_error("SYSTEMS_INIT", f"Error inicializando sistemas: {e}")
            raise
    
    def _run_integration_loop(self):
        """Bucle principal de integración (ejecuta en hilo separado)"""
        try:
            while self.is_active:
                try:
                    # Ejecutar ciclo de integración
                    asyncio.run(self._integration_cycle())
                    
                    # Pausa entre ciclos
                    time.sleep(self.config['monitoring_interval'])
                    
                except Exception as e:
                    SICAR_LOGGER.log_error("INTEGRATION_LOOP", f"Error en ciclo de integración: {e}")
                    time.sleep(5)  # Pausa corta antes de reintentar
            
        except Exception as e:
            SICAR_LOGGER.log_error("INTEGRATION_LOOP", f"Error crítico en bucle de integración: {e}")
    
    async def _integration_cycle(self):
        """Ciclo de integración que coordina todos los sistemas"""
        try:
            # Actualizar métricas de tiempo
            self.performance_metrics['last_update'] = datetime.now()
            if self.performance_metrics['integration_start_time']:
                uptime = datetime.now() - self.performance_metrics['integration_start_time']
                self.performance_metrics['system_uptime'] = uptime.total_seconds()
            
            # Obtener estado de todos los sistemas
            autonomous_status = get_autonomous_status()
            pattern_stats = get_pattern_stats()
            
            # Generar análisis XAI integrado
            xai_analysis = await self._generate_integrated_xai_analysis()
            
            # Coordinar sistemas basado en el estado actual
            await self._coordinate_systems(autonomous_status, pattern_stats, xai_analysis)
            
            # Optimizar parámetros si está habilitado
            if self.config['auto_optimization']:
                await self._auto_optimize_parameters()
            
            # Actualizar métricas
            self.performance_metrics['total_integration_attempts'] += 1
            self.performance_metrics['successful_integrations'] += 1
            
        except Exception as e:
            # Incrementar intentos incluso en caso de error
            self.performance_metrics['total_integration_attempts'] += 1
            SICAR_LOGGER.log_error("INTEGRATION_CYCLE", f"Error en ciclo de integración: {e}")
    
    async def _generate_integrated_xai_analysis(self) -> Optional[Dict[str, Any]]:
        """Generar análisis XAI integrado con todos los sistemas"""
        try:
            # Obtener reporte cognitivo base
            base_report = None
            try:
                # Verificar si los módulos XAI están disponibles
                if (hasattr(self, 'metacontroller') and self.metacontroller and
                    hasattr(self, 'regime_classifier') and self.regime_classifier and
                    hasattr(self, 'causal_cartographer') and self.causal_cartographer):
                    
                    # Obtener datos de mercado simulados para el análisis
                    import pandas as pd
                    import numpy as np
                    from datetime import datetime, timedelta
                    
                    # Crear datos de mercado básicos para el análisis
                    dates = pd.date_range(end=datetime.now(), periods=100, freq='1min')
                    market_data = pd.DataFrame({
                        'timestamp': dates,
                        'open': np.random.uniform(45000, 47000, 100),
                        'high': np.random.uniform(46000, 48000, 100),
                        'low': np.random.uniform(44000, 46000, 100),
                        'close': np.random.uniform(45000, 47000, 100),
                        'volume': np.random.uniform(100, 1000, 100)
                    })
                    
                    # Generar reporte XAI con argumentos completos
                    base_report = generate_dynamic_cognitive_report(
                        metacontroller=self.metacontroller,
                        regime_classifier=self.regime_classifier,
                        causal_cartographer=self.causal_cartographer,
                        market_data=market_data,
                        decision="HOLD",
                        strategy="integration_analysis",
                        confidence=0.75,
                        additional_context={'source': 'integrated_analysis', 'timestamp': datetime.now().isoformat()}
                    )
                else:
                    base_report = "Análisis XAI no disponible - módulos no inicializados"
                    
            except Exception as xai_error:
                SICAR_LOGGER.log_error("INTEGRATED_XAI", f"Error generando análisis XAI integrado: {xai_error}")
                base_report = "Análisis XAI no disponible"
            
            # Enriquecer con datos de patrones
            pattern_stats = get_pattern_stats()
            
            # Enriquecer con estado autónomo
            autonomous_status = get_autonomous_status()
            
            # Crear análisis integrado
            integrated_analysis = {
                'timestamp': datetime.now().isoformat(),
                'base_xai': base_report,
                'pattern_context': {
                    'total_patterns_detected': pattern_stats.get('total_patterns', 0),
                    'recent_patterns': pattern_stats.get('recent_patterns', 0),
                    'average_confidence': pattern_stats.get('average_confidence', 0),
                    'pattern_distribution': pattern_stats.get('pattern_counts', {})
                },
                'autonomous_context': {
                    'is_running': autonomous_status.get('is_running', False),
                    'decisions_this_hour': autonomous_status.get('decisions_this_hour', 0),
                    'active_positions': autonomous_status.get('position_status', {}).get('active_positions', 0),
                    'total_risk': autonomous_status.get('position_status', {}).get('total_risk', 0)
                },
                'integration_metrics': self.performance_metrics.copy()
            }
            
            # Calcular score de confianza integrado
            confidence_factors = []
            
            # base_report es una cadena por ahora, no un diccionario
            # if base_report.get('confidence'):
            #     confidence_factors.append(base_report['confidence'])
            
            if pattern_stats.get('average_confidence'):
                confidence_factors.append(pattern_stats['average_confidence'])
            
            if confidence_factors:
                integrated_analysis['integrated_confidence'] = sum(confidence_factors) / len(confidence_factors)
            else:
                integrated_analysis['integrated_confidence'] = 0.5
            
            # Generar recomendación integrada
            integrated_analysis['integrated_recommendation'] = self._generate_integrated_recommendation(
                integrated_analysis
            )
            
            self.performance_metrics['xai_analyses'] += 1
            
            return integrated_analysis
            
        except Exception as e:
            SICAR_LOGGER.log_error("INTEGRATED_XAI", f"Error generando análisis XAI integrado: {e}")
            return None
    
    def _generate_integrated_recommendation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generar recomendación basada en análisis integrado"""
        try:
            # base_xai es una cadena por ahora, no un diccionario
            base_decision = 'HOLD'  # Valor por defecto hasta que XAI esté completamente configurado
            integrated_confidence = analysis.get('integrated_confidence', 0.5)
            recent_patterns = analysis.get('pattern_context', {}).get('recent_patterns', 0)
            active_positions = analysis.get('autonomous_context', {}).get('active_positions', 0)
            
            # Lógica de recomendación integrada
            recommendation = {
                'action': base_decision,
                'confidence': integrated_confidence,
                'reasoning': [],
                'risk_level': 'MEDIUM',
                'urgency': 5
            }
            
            # Ajustar por patrones recientes
            if recent_patterns > 2:
                recommendation['confidence'] *= 1.1
                recommendation['reasoning'].append(f"Múltiples patrones detectados ({recent_patterns})")
                recommendation['urgency'] += 1
            
            # Ajustar por posiciones activas
            if active_positions > 3:
                recommendation['confidence'] *= 0.9
                recommendation['reasoning'].append(f"Alto número de posiciones activas ({active_positions})")
                recommendation['risk_level'] = 'HIGH'
            
            # Ajustar por confianza integrada
            if integrated_confidence > 0.8:
                recommendation['urgency'] += 2
                recommendation['reasoning'].append("Alta confianza en análisis integrado")
            elif integrated_confidence < 0.6:
                recommendation['risk_level'] = 'HIGH'
                recommendation['reasoning'].append("Baja confianza en análisis integrado")
            
            # Normalizar valores
            recommendation['confidence'] = min(1.0, max(0.0, recommendation['confidence']))
            recommendation['urgency'] = min(10, max(1, recommendation['urgency']))
            
            return recommendation
            
        except Exception as e:
            SICAR_LOGGER.log_error("INTEGRATED_RECOMMENDATION", f"Error generando recomendación: {e}")
            return {'action': 'HOLD', 'confidence': 0.5, 'reasoning': ['Error en análisis'], 'risk_level': 'HIGH', 'urgency': 1}
    
    async def _coordinate_systems(self, autonomous_status: Dict, pattern_stats: Dict, xai_analysis: Optional[Dict]):
        """Coordinar todos los sistemas basado en el estado actual"""
        try:
            # Coordinar basado en análisis XAI
            if xai_analysis:
                recommendation = xai_analysis.get('integrated_recommendation', {})
                
                # Ajustar parámetros del motor autónomo
                if recommendation.get('confidence', 0) > 0.8:
                    self.autonomous_engine.config['min_confidence_threshold'] = 0.7
                else:
                    self.autonomous_engine.config['min_confidence_threshold'] = 0.75
                
                # Ajustar frecuencia de decisiones
                if recommendation.get('urgency', 5) > 7:
                    self.autonomous_engine.config['decision_interval'] = 20  # Más frecuente
                else:
                    self.autonomous_engine.config['decision_interval'] = 30  # Normal
            
            # Coordinar basado en patrones
            if pattern_stats.get('recent_patterns', 0) > 3:
                # Muchos patrones recientes, aumentar sensibilidad
                if hasattr(self.pattern_system, 'config'):
                    self.pattern_system.config['min_confidence'] = 0.6
            
            # Log de coordinación
            SICAR_LOGGER.log_alert("SYSTEM_COORDINATION", 
                f"Sistemas coordinados - Patrones: {pattern_stats.get('recent_patterns', 0)}, "
                f"Decisiones/hora: {autonomous_status.get('decisions_this_hour', 0)}", "INFO")
            
        except Exception as e:
            SICAR_LOGGER.log_error("SYSTEM_COORDINATION", f"Error coordinando sistemas: {e}")
    
    async def _auto_optimize_parameters(self):
        """Optimizar automáticamente parámetros basado en rendimiento"""
        try:
            # Obtener métricas de rendimiento
            uptime_hours = self.performance_metrics['system_uptime'] / 3600
            
            if uptime_hours < 1:  # No optimizar hasta tener al menos 1 hora de datos
                return
            
            # Calcular tasas de éxito
            total_attempts = self.performance_metrics['total_integration_attempts']
            successful_integrations = self.performance_metrics['successful_integrations']
            
            if total_attempts > 0:
                success_rate = successful_integrations / total_attempts
                
                # Ajustar parámetros basado en tasa de éxito
                if success_rate > 0.9:
                    # Alto éxito, ser más agresivo
                    self.autonomous_engine.config['min_confidence_threshold'] *= 0.95
                elif success_rate < 0.7:
                    # Bajo éxito, ser más conservador
                    self.autonomous_engine.config['min_confidence_threshold'] *= 1.05
                
                # Mantener límites razonables
                self.autonomous_engine.config['min_confidence_threshold'] = max(0.6, 
                    min(0.9, self.autonomous_engine.config['min_confidence_threshold']))
            
            SICAR_LOGGER.log_alert("AUTO_OPTIMIZATION", 
                f"Parámetros optimizados - Umbral confianza: {self.autonomous_engine.config['min_confidence_threshold']:.3f}", "INFO")
            
        except Exception as e:
            SICAR_LOGGER.log_error("AUTO_OPTIMIZATION", f"Error en auto-optimización: {e}")
    
    def _start_performance_monitoring(self):
        """Iniciar monitoreo de rendimiento"""
        try:
            def monitor_performance():
                while self.is_active:
                    try:
                        # Log de métricas cada 5 minutos
                        time.sleep(self.config['performance_log_interval'])
                        
                        if self.is_active:
                            self._log_performance_metrics()
                    
                    except Exception as e:
                        SICAR_LOGGER.log_error("PERFORMANCE_MONITOR", f"Error en monitoreo: {e}")
            
            self.performance_monitor = threading.Thread(target=monitor_performance, daemon=True)
            self.performance_monitor.start()
            
        except Exception as e:
            SICAR_LOGGER.log_error("PERFORMANCE_MONITOR_START", f"Error iniciando monitoreo: {e}")
    
    def _log_performance_metrics(self):
        """Registrar métricas de rendimiento"""
        try:
            uptime_hours = self.performance_metrics['system_uptime'] / 3600
            
            metrics_summary = {
                'uptime_hours': round(uptime_hours, 2),
                'total_decisions': self.performance_metrics['total_decisions'],
                'successful_integrations': self.performance_metrics['successful_integrations'],
                'pattern_detections': self.performance_metrics['pattern_detections'],
                'xai_analyses': self.performance_metrics['xai_analyses'],
                'breakout_alerts': self.performance_metrics['breakout_alerts']
            }
            
            SICAR_LOGGER.log_alert("PERFORMANCE_METRICS", 
                f"Métricas de rendimiento: {json.dumps(metrics_summary, indent=2)}", "INFO")
            
        except Exception as e:
            SICAR_LOGGER.log_error("PERFORMANCE_LOG", f"Error registrando métricas: {e}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Obtener estado completo de la integración"""
        try:
            return {
                'is_active': self.is_active,
                'performance_metrics': self.performance_metrics.copy(),
                'config': self.config.copy(),
                'autonomous_status': get_autonomous_status(),
                'pattern_stats': get_pattern_stats(),
                'system_health': {
                    'integration_thread_alive': self.integration_thread.is_alive() if self.integration_thread else False,
                    'performance_monitor_alive': self.performance_monitor.is_alive() if self.performance_monitor else False,
                    'last_update': self.performance_metrics['last_update'].isoformat()
                }
            }
            
        except Exception as e:
            SICAR_LOGGER.log_error("INTEGRATION_STATUS", f"Error obteniendo estado: {e}")
            return {'error': str(e), 'is_active': False}
    
    def generate_integration_report(self) -> Dict[str, Any]:
        """Generar reporte completo de la integración"""
        try:
            status = self.get_integration_status()
            
            # Calcular estadísticas adicionales
            uptime_hours = self.performance_metrics['system_uptime'] / 3600
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'integration_summary': {
                    'status': 'ACTIVE' if self.is_active else 'INACTIVE',
                    'uptime_hours': round(uptime_hours, 2),
                    'total_operations': sum([
                        self.performance_metrics['total_decisions'],
                        self.performance_metrics['pattern_detections'],
                        self.performance_metrics['xai_analyses']
                    ])
                },
                'system_performance': {
                    'decisions_per_hour': self.performance_metrics['total_decisions'] / max(uptime_hours, 1),
                    'patterns_per_hour': self.performance_metrics['pattern_detections'] / max(uptime_hours, 1),
                    'analyses_per_hour': self.performance_metrics['xai_analyses'] / max(uptime_hours, 1),
                    'integration_success_rate': (self.performance_metrics['successful_integrations'] / 
                                               max(self.performance_metrics['total_integration_attempts'], 1))
                },
                'current_configuration': self.config.copy(),
                'recommendations': self._generate_optimization_recommendations()
            }
            
            return report
            
        except Exception as e:
            SICAR_LOGGER.log_error("INTEGRATION_REPORT", f"Error generando reporte: {e}")
            return {'error': str(e)}
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generar recomendaciones de optimización"""
        try:
            recommendations = []
            
            uptime_hours = self.performance_metrics['system_uptime'] / 3600
            
            if uptime_hours > 1:
                # Analizar tasas de operación
                decisions_per_hour = self.performance_metrics['total_decisions'] / uptime_hours
                
                if decisions_per_hour < 2:
                    recommendations.append("Considerar reducir umbral de confianza para más decisiones")
                elif decisions_per_hour > 10:
                    recommendations.append("Considerar aumentar umbral de confianza para filtrar decisiones")
                
                # Analizar éxito de integración
                if self.performance_metrics['total_integration_attempts'] > 0:
                    success_rate = (self.performance_metrics['successful_integrations'] / 
                                  self.performance_metrics['total_integration_attempts'])
                    
                    if success_rate < 0.8:
                        recommendations.append("Revisar parámetros de coordinación entre sistemas")
                    elif success_rate > 0.95:
                        recommendations.append("Sistema funcionando óptimamente, considerar aumentar agresividad")
            
            if not recommendations:
                recommendations.append("Sistema funcionando dentro de parámetros normales")
            
            return recommendations
            
        except Exception as e:
            SICAR_LOGGER.log_error("OPTIMIZATION_RECOMMENDATIONS", f"Error generando recomendaciones: {e}")
            return ["Error generando recomendaciones"]

# Instancia global del gestor de integración
INTEGRATION_MANAGER = EnhancedIntegrationManager()

async def start_enhanced_integration():
    """Función de conveniencia para iniciar integración mejorada"""
    return await INTEGRATION_MANAGER.start_enhanced_integration()

async def stop_enhanced_integration():
    """Función de conveniencia para detener integración mejorada"""
    return await INTEGRATION_MANAGER.stop_enhanced_integration()

def get_integration_status() -> Dict[str, Any]:
    """Función de conveniencia para obtener estado de integración"""
    return INTEGRATION_MANAGER.get_integration_status()

def generate_integration_report() -> Dict[str, Any]:
    """Función de conveniencia para generar reporte de integración"""
    return INTEGRATION_MANAGER.generate_integration_report()