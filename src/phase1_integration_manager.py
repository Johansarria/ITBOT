#!/usr/bin/env python3
"""
Phase 1 Integration Manager
Sistema SICAR - Integración de nuevos modelos ML
Combina Stacking Classifier, Q-Learning y Anomaly Detection con el sistema existente
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import time
import warnings
warnings.filterwarnings('ignore')

# Importar nuevos módulos
from enhanced_stacking_classifier import EnhancedStackingClassifier, StackingIntegrator
from qlearning_position_optimizer import QLearningPositionOptimizer, PositionSizeIntegrator
from market_anomaly_detector import MarketAnomalyDetector, AnomalyIntegrator

# Importar sistema existente
try:
    from advanced_ml_engine import AdvancedMLEngine
except ImportError:
    logger.warning("AdvancedMLEngine no disponible, usando modo simulado")
    AdvancedMLEngine = None

logger = logging.getLogger(__name__)

class Phase1IntegrationManager:
    """
    Manager principal para integrar todos los modelos de Fase 1
    Coordina Stacking Classifier, Q-Learning y Anomaly Detection
    """
    
    def __init__(self, existing_ml_engine=None):
        """
        Inicializar Integration Manager
        
        Args:
            existing_ml_engine: Instancia del motor ML existente
        """
        self.existing_ml_engine = existing_ml_engine
        
        # Integradores de nuevos modelos
        self.stacking_integrator = StackingIntegrator(existing_ml_engine)
        self.position_integrator = PositionSizeIntegrator()
        self.anomaly_integrator = AnomalyIntegrator()
        
        # Estado del sistema
        self.active_symbols = set()
        self.integration_stats = {}
        self.performance_metrics = {}
        
        # Configuración
        self.enable_stacking = True
        self.enable_qlearning = True
        self.enable_anomaly_detection = True
        self.min_data_points = 100
        
        logger.info("Phase 1 Integration Manager inicializado")
        logger.info(f"Stacking: {self.enable_stacking}, Q-Learning: {self.enable_qlearning}, Anomaly: {self.enable_anomaly_detection}")
    
    def initialize_symbol(self, symbol, historical_data):
        """
        Inicializar nuevos modelos para un símbolo específico
        
        Args:
            symbol: Símbolo de trading
            historical_data: Datos históricos para entrenamiento
            
        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            logger.info(f"Inicializando modelos de Fase 1 para {symbol}")
            
            if len(historical_data) < self.min_data_points:
                logger.warning(f"Datos insuficientes para {symbol}: {len(historical_data)} < {self.min_data_points}")
                return False
            
            success_count = 0
            total_models = 0
            
            # 1. Inicializar Stacking Classifier
            if self.enable_stacking:
                total_models += 1
                try:
                    # Preparar datos para ML
                    features, targets = self._prepare_ml_data(historical_data)
                    
                    if len(features) > 0:
                        success = self.stacking_integrator.integrate_with_existing_system(
                            symbol, features, targets
                        )
                        if success:
                            success_count += 1
                            logger.info(f"✅ Stacking Classifier inicializado para {symbol}")
                        else:
                            logger.warning(f"❌ Error inicializando Stacking Classifier para {symbol}")
                    else:
                        logger.warning(f"No se pudieron preparar features ML para {symbol}")
                        
                except Exception as e:
                    logger.error(f"Error en Stacking Classifier para {symbol}: {e}")
            
            # 2. Inicializar Q-Learning (no requiere entrenamiento inicial)
            if self.enable_qlearning:
                total_models += 1
                try:
                    # El Q-Learning se inicializa automáticamente al usarse
                    agent = self.position_integrator.get_agent_for_symbol(symbol)
                    success_count += 1
                    logger.info(f"✅ Q-Learning Agent inicializado para {symbol}")
                except Exception as e:
                    logger.error(f"Error en Q-Learning para {symbol}: {e}")
            
            # 3. Inicializar Anomaly Detection
            if self.enable_anomaly_detection:
                total_models += 1
                try:
                    detector = self.anomaly_integrator.get_detector_for_symbol(symbol)
                    success = detector.train(historical_data, symbol)
                    
                    if success:
                        success_count += 1
                        logger.info(f"✅ Anomaly Detector inicializado para {symbol}")
                    else:
                        logger.warning(f"❌ Error inicializando Anomaly Detector para {symbol}")
                        
                except Exception as e:
                    logger.error(f"Error en Anomaly Detector para {symbol}: {e}")
            
            # Registrar símbolo como activo
            if success_count > 0:
                self.active_symbols.add(symbol)
                self.integration_stats[symbol] = {
                    'initialized_models': success_count,
                    'total_models': total_models,
                    'success_rate': success_count / total_models,
                    'initialization_time': datetime.now().isoformat()
                }
                
                logger.info(f"Inicialización completada para {symbol}: {success_count}/{total_models} modelos")
                return True
            else:
                logger.error(f"Falló la inicialización para {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error inicializando {symbol}: {e}")
            return False
    
    def get_enhanced_prediction(self, symbol, current_data, market_context=None):
        """
        Obtener predicción mejorada combinando todos los modelos
        
        Args:
            symbol: Símbolo de trading
            current_data: Datos actuales del mercado
            market_context: Contexto adicional del mercado
            
        Returns:
            dict: Predicción mejorada con información de todos los modelos
        """
        try:
            start_time = time.time()
            
            if symbol not in self.active_symbols:
                logger.warning(f"Símbolo {symbol} no inicializado")
                return self._get_default_prediction()
            
            enhanced_prediction = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'models_used': [],
                'predictions': {},
                'final_prediction': 1,
                'confidence': 0.0,
                'position_size': 0.3,
                'anomaly_detected': False,
                'processing_time': 0.0
            }
            
            # 1. Verificar anomalías primero
            anomaly_info = None
            if self.enable_anomaly_detection:
                try:
                    anomaly_info = self.anomaly_integrator.check_market_conditions(symbol, current_data)
                    enhanced_prediction['anomaly_detected'] = anomaly_info.get('is_anomaly', False)
                    enhanced_prediction['anomaly_score'] = anomaly_info.get('anomaly_score', 0.0)
                    enhanced_prediction['models_used'].append('anomaly_detection')
                    
                    # Si hay anomalía severa, ser más conservador
                    if anomaly_info.get('is_anomaly', False) and anomaly_info.get('confidence', 0) > 0.7:
                        logger.warning(f"Anomalía severa detectada en {symbol}, siendo conservador")
                        enhanced_prediction['position_size'] = 0.1  # Posición muy pequeña
                        
                except Exception as e:
                    logger.error(f"Error en detección de anomalías: {e}")
            
            # 2. Obtener predicción del Stacking Classifier
            stacking_prediction = None
            if self.enable_stacking:
                try:
                    features = self._prepare_current_features(current_data)
                    if len(features) > 0:
                        stacking_prediction = self.stacking_integrator.get_enhanced_prediction(symbol, features)
                        enhanced_prediction['predictions']['stacking'] = stacking_prediction
                        enhanced_prediction['models_used'].append('stacking_classifier')
                except Exception as e:
                    logger.error(f"Error en Stacking Classifier: {e}")
            
            # 3. Determinar predicción final
            if stacking_prediction and 'prediction' in stacking_prediction:
                enhanced_prediction['final_prediction'] = stacking_prediction['prediction']
                enhanced_prediction['confidence'] = stacking_prediction.get('confidence', 0.0)
            else:
                # Fallback a predicción por defecto
                enhanced_prediction['final_prediction'] = 1
                enhanced_prediction['confidence'] = 0.5
            
            # 4. Optimizar tamaño de posición con Q-Learning
            if self.enable_qlearning and not enhanced_prediction['anomaly_detected']:
                try:
                    # Preparar contexto de mercado
                    if market_context is None:
                        market_context = self._prepare_market_context(current_data, enhanced_prediction)
                    
                    position_decision = self.position_integrator.optimize_position_size(
                        symbol, current_data, enhanced_prediction
                    )
                    
                    enhanced_prediction['position_size'] = position_decision.get('position_size', 0.3)
                    enhanced_prediction['position_confidence'] = position_decision.get('confidence', 0.0)
                    enhanced_prediction['models_used'].append('qlearning_position')
                    
                except Exception as e:
                    logger.error(f"Error en Q-Learning: {e}")
            
            # 5. Aplicar filtros de seguridad
            enhanced_prediction = self._apply_safety_filters(enhanced_prediction, anomaly_info)
            
            # Tiempo de procesamiento
            enhanced_prediction['processing_time'] = time.time() - start_time
            
            logger.debug(f"Predicción mejorada para {symbol}: {enhanced_prediction['final_prediction']} "
                        f"(confianza: {enhanced_prediction['confidence']:.2f}, "
                        f"posición: {enhanced_prediction['position_size']:.1%})")
            
            return enhanced_prediction
            
        except Exception as e:
            logger.error(f"Error obteniendo predicción mejorada: {e}")
            return self._get_default_prediction()
    
    def update_from_trade_result(self, symbol, trade_info):
        """
        Actualizar modelos con resultado de trade
        
        Args:
            symbol: Símbolo de trading
            trade_info: Información completa del trade
        """
        try:
            if symbol not in self.active_symbols:
                return
            
            # Actualizar Q-Learning con resultado del trade
            if self.enable_qlearning:
                try:
                    self.position_integrator.update_from_trade_result(symbol, trade_info)
                except Exception as e:
                    logger.error(f"Error actualizando Q-Learning: {e}")
            
            # Actualizar métricas de rendimiento
            self._update_performance_metrics(symbol, trade_info)
            
            logger.debug(f"Modelos actualizados para {symbol}")
            
        except Exception as e:
            logger.error(f"Error actualizando modelos: {e}")
    
    def get_system_performance(self):
        """Obtener métricas de rendimiento del sistema integrado"""
        try:
            performance = {
                'active_symbols': len(self.active_symbols),
                'integration_stats': self.integration_stats,
                'timestamp': datetime.now().isoformat()
            }
            
            # Métricas de Q-Learning
            if self.enable_qlearning:
                qlearning_metrics = self.position_integrator.get_all_performance_metrics()
                performance['qlearning_metrics'] = qlearning_metrics
            
            # Métricas de detección de anomalías
            if self.enable_anomaly_detection:
                anomaly_stats = self.anomaly_integrator.get_all_anomaly_statistics()
                performance['anomaly_stats'] = anomaly_stats
            
            # Métricas generales
            performance['performance_metrics'] = self.performance_metrics
            
            return performance
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return {}
    
    def _prepare_ml_data(self, historical_data):
        """Preparar datos para entrenamiento ML"""
        try:
            # Implementación simplificada - en producción usar el sistema existente
            if 'close' not in historical_data.columns:
                return np.array([]), np.array([])
            
            prices = historical_data['close'].values
            
            # Features básicas
            features = []
            targets = []
            
            for i in range(20, len(prices) - 1):
                # Features: últimos 20 returns
                window_prices = prices[i-20:i]
                returns = np.diff(np.log(window_prices))
                
                # Target: dirección del próximo movimiento
                next_return = (prices[i+1] - prices[i]) / prices[i]
                if next_return > 0.001:
                    target = 2  # Subida
                elif next_return < -0.001:
                    target = 0  # Bajada
                else:
                    target = 1  # Lateral
                
                features.append(returns)
                targets.append(target)
            
            return np.array(features), np.array(targets)
            
        except Exception as e:
            logger.error(f"Error preparando datos ML: {e}")
            return np.array([]), np.array([])
    
    def _prepare_current_features(self, current_data):
        """Preparar features de datos actuales"""
        try:
            if 'close' not in current_data.columns or len(current_data) < 20:
                return np.array([])
            
            prices = current_data['close'].values[-20:]
            returns = np.diff(np.log(prices))
            
            return returns
            
        except Exception as e:
            logger.error(f"Error preparando features actuales: {e}")
            return np.array([])
    
    def _prepare_market_context(self, current_data, prediction):
        """Preparar contexto de mercado para Q-Learning"""
        try:
            context = {
                'volatility': 0.02,
                'trend_strength': 0.5,
                'confidence': prediction.get('confidence', 0.5)
            }
            
            # Calcular volatilidad si hay datos suficientes
            if 'close' in current_data.columns and len(current_data) > 20:
                prices = current_data['close'].values[-20:]
                returns = np.diff(np.log(prices))
                context['volatility'] = np.std(returns) * np.sqrt(252)
            
            return context
            
        except Exception as e:
            logger.error(f"Error preparando contexto: {e}")
            return {'volatility': 0.02, 'trend_strength': 0.5, 'confidence': 0.5}
    
    def _apply_safety_filters(self, prediction, anomaly_info):
        """Aplicar filtros de seguridad a la predicción"""
        try:
            # Limitar tamaño de posición en caso de anomalías
            if prediction.get('anomaly_detected', False):
                prediction['position_size'] = min(prediction['position_size'], 0.2)
            
            # Limitar tamaño de posición si confianza es baja
            if prediction.get('confidence', 0) < 0.3:
                prediction['position_size'] = min(prediction['position_size'], 0.1)
            
            # Asegurar valores válidos
            prediction['position_size'] = max(0.05, min(1.0, prediction['position_size']))
            prediction['confidence'] = max(0.0, min(1.0, prediction['confidence']))
            
            return prediction
            
        except Exception as e:
            logger.error(f"Error aplicando filtros de seguridad: {e}")
            return prediction
    
    def _get_default_prediction(self):
        """Obtener predicción por defecto"""
        return {
            'symbol': 'unknown',
            'timestamp': datetime.now().isoformat(),
            'models_used': [],
            'predictions': {},
            'final_prediction': 1,
            'confidence': 0.0,
            'position_size': 0.1,  # Posición muy conservadora
            'anomaly_detected': False,
            'processing_time': 0.0
        }
    
    def _update_performance_metrics(self, symbol, trade_info):
        """Actualizar métricas de rendimiento"""
        try:
            if symbol not in self.performance_metrics:
                self.performance_metrics[symbol] = {
                    'total_trades': 0,
                    'successful_trades': 0,
                    'total_pnl': 0.0,
                    'avg_processing_time': 0.0
                }
            
            metrics = self.performance_metrics[symbol]
            
            # Actualizar contadores
            metrics['total_trades'] += 1
            
            pnl = trade_info.get('pnl', 0.0)
            metrics['total_pnl'] += pnl
            
            if pnl > 0:
                metrics['successful_trades'] += 1
            
            # Actualizar tiempo de procesamiento
            processing_time = trade_info.get('processing_time', 0.0)
            if processing_time > 0:
                current_avg = metrics['avg_processing_time']
                total_trades = metrics['total_trades']
                metrics['avg_processing_time'] = (current_avg * (total_trades - 1) + processing_time) / total_trades
            
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")


if __name__ == "__main__":
    # Test básico del sistema integrado
    logging.basicConfig(level=logging.INFO)
    
    # Crear datos de prueba
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=300, freq='1H')
    
    price = 100
    prices = []
    volumes = []
    
    for i in range(300):
        price += np.random.normal(0, 0.01) * price
        prices.append(price)
        volumes.append(np.random.lognormal(10, 0.5))
    
    historical_data = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'volume': volumes
    })
    
    # Probar sistema integrado
    integration_manager = Phase1IntegrationManager()
    
    # Inicializar para símbolo de prueba
    if integration_manager.initialize_symbol('BTCUSDT', historical_data):
        # Obtener predicción mejorada
        current_data = historical_data.tail(50)
        prediction = integration_manager.get_enhanced_prediction('BTCUSDT', current_data)
        
        print("Predicción mejorada:", prediction)
        
        # Simular resultado de trade
        trade_info = {
            'pnl': 0.02,
            'position_size': prediction['position_size'],
            'processing_time': prediction['processing_time']
        }
        
        integration_manager.update_from_trade_result('BTCUSDT', trade_info)
        
        # Obtener métricas del sistema
        performance = integration_manager.get_system_performance()
        print("Rendimiento del sistema:", performance)
        
        print("✅ Test del Phase 1 Integration Manager completado exitosamente")
    else:
        print("❌ Error en el test del Phase 1 Integration Manager")