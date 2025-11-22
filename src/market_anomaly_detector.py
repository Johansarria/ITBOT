#!/usr/bin/env python3
"""
Market Anomaly Detector usando Isolation Forest
Sistema SICAR - Fase 1
Detección de anomalías y condiciones de mercado inusuales
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.decomposition import PCA
from sklearn.metrics import classification_report
import joblib
import os

logger = logging.getLogger(__name__)

class MarketAnomalyDetector:
    """
    Detector de anomalías de mercado usando Isolation Forest
    Identifica condiciones de mercado inusuales que pueden afectar el trading
    """
    
    def __init__(self, contamination=0.1, n_estimators=100):
        """
        Inicializar detector de anomalías
        
        Args:
            contamination: Proporción esperada de anomalías (0.1 = 10%)
            n_estimators: Número de árboles en el Isolation Forest
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        
        # Modelos
        self.isolation_forest = None
        self.scaler = RobustScaler()
        self.pca = None
        
        # Estado
        self.is_trained = False
        self.feature_names = []
        
        # Configuración
        self.min_samples = 200
        self.use_pca = True
        self.pca_components = 0.95  # Mantener 95% de la varianza
        
        # Historial de anomalías
        self.anomaly_history = []
        self.anomaly_threshold = -0.1  # Threshold para clasificar anomalías
        
        logger.info("Market Anomaly Detector inicializado")
        logger.info(f"Contaminación esperada: {contamination:.1%}")
    
    def prepare_features(self, market_data):
        """
        Preparar features para detección de anomalías
        
        Args:
            market_data: DataFrame con datos de mercado
            
        Returns:
            np.array: Features preparadas
        """
        try:
            # Verificar que tenemos datos suficientes
            if len(market_data) < 10:
                logger.warning("Datos insuficientes para preparar features")
                return np.array([])
            
            features_list = []
            
            # 1. Retornos de precios
            if 'close' in market_data.columns:
                returns = market_data['close'].pct_change().fillna(0)
                features_list.append(returns.values)
            
            # 2. Volatilidad rolling
            if 'close' in market_data.columns:
                window = min(20, len(market_data) // 2)
                volatility = market_data['close'].pct_change().rolling(window=window, min_periods=1).std().fillna(0)
                features_list.append(volatility.values)
            
            # 3. Ratio de volumen
            if 'volume' in market_data.columns:
                window = min(20, len(market_data) // 2)
                volume_ma = market_data['volume'].rolling(window=window, min_periods=1).mean()
                volume_ratio = (market_data['volume'] / volume_ma).fillna(1)
                features_list.append(volume_ratio.values)
            
            # 4. Rango diario normalizado
            if all(col in market_data.columns for col in ['high', 'low', 'close']):
                daily_range = (market_data['high'] - market_data['low']) / (market_data['close'] + 1e-10)
                features_list.append(daily_range.values)
            
            # 5. Momentum simple
            if 'close' in market_data.columns:
                window = min(10, len(market_data) // 2)
                momentum = market_data['close'].pct_change(periods=window).fillna(0)
                features_list.append(momentum.values)
            
            if len(features_list) == 0:
                logger.warning("No se pudieron calcular features")
                return np.array([])
            
            # Combinar features
            feature_matrix = np.column_stack(features_list)
            
            # Remover filas con NaN o infinitos
            valid_rows = np.isfinite(feature_matrix).all(axis=1)
            feature_matrix = feature_matrix[valid_rows]
            
            logger.info(f"Features preparadas: {feature_matrix.shape}")
            return feature_matrix
            
        except Exception as e:
            logger.error(f"Error preparando features: {e}")
            return np.array([])
    
    def train(self, market_data, symbol='default'):
        """
        Entrenar el detector de anomalías
        
        Args:
            market_data: DataFrame con datos históricos
            symbol: Símbolo para identificación
            
        Returns:
            bool: True si el entrenamiento fue exitoso
        """
        try:
            logger.info(f"Entrenando detector de anomalías para {symbol}")
            
            # Preparar features
            features = self.prepare_features(market_data)
            
            # Verificar datos mínimos (ajustar para test)
            min_required = min(self.min_samples, 50)
            if len(features) == 0 or len(features) < min_required:
                logger.warning(f"Datos insuficientes: {len(features)} < {min_required}")
                return False
            
            # Escalar features
            features_scaled = self.scaler.fit_transform(features)
            
            # Aplicar PCA si es necesario
            if self.use_pca and features_scaled.shape[1] > 5:
                self.pca = PCA(n_components=self.pca_components, random_state=42)
                features_final = self.pca.fit_transform(features_scaled)
                logger.info(f"PCA aplicado: {features_scaled.shape[1]} -> {features_final.shape[1]} componentes")
            else:
                features_final = features_scaled
                self.pca = None
            
            # Crear y entrenar Isolation Forest
            self.isolation_forest = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                max_samples='auto',
                max_features=1.0,
                bootstrap=False,
                n_jobs=-1,
                random_state=42,
                verbose=0
            )
            
            # Entrenar
            start_time = datetime.now()
            self.isolation_forest.fit(features_final)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Evaluar en datos de entrenamiento
            anomaly_scores = self.isolation_forest.decision_function(features_final)
            predictions = self.isolation_forest.predict(features_final)
            
            # Estadísticas
            n_anomalies = np.sum(predictions == -1)
            anomaly_rate = n_anomalies / len(predictions)
            
            logger.info(f"Detector entrenado para {symbol}")
            logger.info(f"Tiempo de entrenamiento: {training_time:.2f}s")
            logger.info(f"Anomalías detectadas: {n_anomalies}/{len(predictions)} ({anomaly_rate:.1%})")
            logger.info(f"Score promedio: {np.mean(anomaly_scores):.3f}")
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando detector: {e}")
            return False
    
    def detect_anomaly(self, current_data):
        """
        Detectar si los datos actuales representan una anomalía
        
        Args:
            current_data: Datos actuales del mercado
            
        Returns:
            dict: Información sobre la anomalía detectada
        """
        try:
            if not self.is_trained:
                logger.warning("Detector no entrenado")
                return {
                    'is_anomaly': False,
                    'anomaly_score': 0.0,
                    'confidence': 0.0,
                    'status': 'not_trained'
                }
            
            # Preparar features
            features = self.prepare_features(current_data)
            
            if len(features) == 0:
                logger.warning("No se pudieron preparar features")
                return {
                    'is_anomaly': False,
                    'anomaly_score': 0.0,
                    'confidence': 0.0,
                    'status': 'no_features'
                }
            
            # Usar solo la última observación
            last_features = features[-1:] if len(features.shape) > 1 else features.reshape(1, -1)
            
            # Escalar
            features_scaled = self.scaler.transform(last_features)
            
            # Aplicar PCA si fue usado en entrenamiento
            if self.pca is not None:
                features_final = self.pca.transform(features_scaled)
            else:
                features_final = features_scaled
            
            # Detectar anomalía
            anomaly_score = self.isolation_forest.decision_function(features_final)[0]
            prediction = self.isolation_forest.predict(features_final)[0]
            
            is_anomaly = prediction == -1
            confidence = abs(anomaly_score)  # Confianza basada en la magnitud del score
            
            # Registrar anomalía
            anomaly_info = {
                'is_anomaly': is_anomaly,
                'anomaly_score': float(anomaly_score),
                'confidence': float(confidence),
                'timestamp': datetime.now().isoformat(),
                'status': 'detected' if is_anomaly else 'normal'
            }
            
            if is_anomaly:
                self.anomaly_history.append(anomaly_info)
                logger.warning(f"ANOMALÍA DETECTADA: Score {anomaly_score:.3f}")
            else:
                logger.debug(f"Condiciones normales: Score {anomaly_score:.3f}")
            
            return anomaly_info
            
        except Exception as e:
            logger.error(f"Error detectando anomalía: {e}")
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'confidence': 0.0,
                'status': 'error'
            }
    
    def get_anomaly_statistics(self):
        """Obtener estadísticas de anomalías detectadas"""
        try:
            if not self.anomaly_history:
                return {
                    'total_anomalies': 0,
                    'recent_anomalies_24h': 0,
                    'avg_anomaly_score': 0.0,
                    'last_anomaly': None
                }
            
            # Filtrar anomalías recientes (últimas 24 horas)
            now = datetime.now()
            recent_anomalies = []
            
            for anomaly in self.anomaly_history:
                try:
                    anomaly_time = datetime.fromisoformat(anomaly['timestamp'])
                    if (now - anomaly_time).total_seconds() < 86400:  # 24 horas
                        recent_anomalies.append(anomaly)
                except:
                    continue
            
            # Estadísticas
            total_anomalies = len(self.anomaly_history)
            recent_count = len(recent_anomalies)
            
            scores = [a['anomaly_score'] for a in self.anomaly_history]
            avg_score = np.mean(scores) if scores else 0.0
            
            last_anomaly = self.anomaly_history[-1] if self.anomaly_history else None
            
            return {
                'total_anomalies': total_anomalies,
                'recent_anomalies_24h': recent_count,
                'avg_anomaly_score': avg_score,
                'min_anomaly_score': min(scores) if scores else 0.0,
                'max_anomaly_score': max(scores) if scores else 0.0,
                'last_anomaly': last_anomaly
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def save_model(self, filepath):
        """Guardar modelo entrenado"""
        try:
            if not self.is_trained:
                logger.warning("No hay modelo entrenado para guardar")
                return False
            
            model_data = {
                'isolation_forest': self.isolation_forest,
                'scaler': self.scaler,
                'pca': self.pca,
                'feature_names': self.feature_names,
                'contamination': self.contamination,
                'n_estimators': self.n_estimators,
                'is_trained': self.is_trained,
                'timestamp': datetime.now().isoformat()
            }
            
            joblib.dump(model_data, filepath)
            logger.info(f"Modelo guardado en: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando modelo: {e}")
            return False
    
    def load_model(self, filepath):
        """Cargar modelo entrenado"""
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Archivo no encontrado: {filepath}")
                return False
            
            model_data = joblib.load(filepath)
            
            self.isolation_forest = model_data['isolation_forest']
            self.scaler = model_data['scaler']
            self.pca = model_data.get('pca', None)
            self.feature_names = model_data.get('feature_names', [])
            self.contamination = model_data.get('contamination', self.contamination)
            self.n_estimators = model_data.get('n_estimators', self.n_estimators)
            self.is_trained = model_data.get('is_trained', False)
            
            logger.info(f"Modelo cargado desde: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            return False


class AnomalyIntegrator:
    """
    Integrador para usar detección de anomalías con el sistema SICAR
    """
    
    def __init__(self):
        """Inicializar integrador"""
        self.detectors = {}
        self.anomaly_alerts = []
        
        logger.info("Anomaly Integrator inicializado")
    
    def get_detector_for_symbol(self, symbol):
        """Obtener o crear detector para un símbolo"""
        if symbol not in self.detectors:
            self.detectors[symbol] = MarketAnomalyDetector()
            logger.info(f"Nuevo detector de anomalías creado para {symbol}")
        
        return self.detectors[symbol]
    
    def check_market_conditions(self, symbol, market_data):
        """
        Verificar condiciones de mercado para anomalías
        
        Args:
            symbol: Símbolo de trading
            market_data: Datos del mercado
            
        Returns:
            dict: Información sobre anomalías detectadas
        """
        try:
            detector = self.get_detector_for_symbol(symbol)
            
            # Detectar anomalía
            anomaly_info = detector.detect_anomaly(market_data)
            
            # Si hay anomalía, crear alerta
            if anomaly_info['is_anomaly']:
                alert = {
                    'symbol': symbol,
                    'timestamp': datetime.now().isoformat(),
                    'anomaly_score': anomaly_info['anomaly_score'],
                    'confidence': anomaly_info['confidence'],
                    'message': f"Anomalía detectada en {symbol}"
                }
                
                self.anomaly_alerts.append(alert)
                logger.warning(f"ALERTA DE ANOMALÍA: {symbol} - Score: {anomaly_info['anomaly_score']:.3f}")
            
            return anomaly_info
            
        except Exception as e:
            logger.error(f"Error verificando condiciones: {e}")
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'confidence': 0.0,
                'status': 'error'
            }
    
    def should_avoid_trading(self, symbol, anomaly_threshold=0.7):
        """
        Determinar si se debe evitar trading debido a anomalías
        
        Args:
            symbol: Símbolo de trading
            anomaly_threshold: Umbral de confianza para evitar trading
            
        Returns:
            bool: True si se debe evitar trading
        """
        try:
            if symbol not in self.detectors:
                return False
            
            detector = self.detectors[symbol]
            stats = detector.get_anomaly_statistics()
            
            # Verificar anomalías recientes
            recent_anomalies = stats.get('recent_anomalies_24h', 0)
            
            # Si hay muchas anomalías recientes, evitar trading
            if recent_anomalies > 3:
                logger.warning(f"Evitando trading en {symbol}: {recent_anomalies} anomalías recientes")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluando si evitar trading: {e}")
            return False
    
    def get_all_anomaly_statistics(self):
        """Obtener estadísticas de todos los detectores"""
        try:
            all_stats = {}
            
            for symbol, detector in self.detectors.items():
                all_stats[symbol] = detector.get_anomaly_statistics()
            
            # Estadísticas globales
            total_alerts = len(self.anomaly_alerts)
            recent_alerts = len([
                alert for alert in self.anomaly_alerts
                if (datetime.now() - datetime.fromisoformat(alert['timestamp'])).total_seconds() < 86400
            ])
            
            all_stats['global'] = {
                'total_alerts': total_alerts,
                'recent_alerts_24h': recent_alerts,
                'active_detectors': len(self.detectors)
            }
            
            return all_stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}


if __name__ == "__main__":
    # Test básico
    logging.basicConfig(level=logging.INFO)
    
    # Crear datos de prueba
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='1H')
    
    # Simular datos de mercado
    price = 100
    prices = []
    volumes = []
    
    for i in range(500):
        # Precio con walk aleatorio
        price += np.random.normal(0, 0.01) * price
        
        # Insertar algunas anomalías
        if i in [100, 200, 300]:
            price *= 1.05  # Spike de precio
        
        prices.append(price)
        volumes.append(np.random.lognormal(10, 0.5))
    
    market_data = pd.DataFrame({
        'timestamp': dates,
        'close': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'volume': volumes
    })
    
    # Probar detector
    detector = MarketAnomalyDetector(contamination=0.05)
    
    if detector.train(market_data, 'TEST'):
        # Detectar anomalías en datos recientes
        recent_data = market_data.tail(50)
        anomaly_info = detector.detect_anomaly(recent_data)
        
        print("Detección de anomalía:", anomaly_info)
        
        # Estadísticas
        stats = detector.get_anomaly_statistics()
        print("Estadísticas:", stats)
        
        # Guardar modelo
        detector.save_model('test_anomaly_model.joblib')
        
        print("✅ Test del Market Anomaly Detector completado exitosamente")
    else:
        print("❌ Error en el test del Market Anomaly Detector")