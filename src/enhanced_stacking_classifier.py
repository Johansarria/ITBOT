#!/usr/bin/env python3
"""
Enhanced Stacking Classifier para Sistema SICAR
Mejora del ensemble actual sin impacto en rendimiento
Fase 1: Implementación inmediata
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier, 
    ExtraTreesClassifier, AdaBoostClassifier, StackingClassifier
)
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from sklearn.base import BaseEstimator, ClassifierMixin
import joblib
import os

logger = logging.getLogger(__name__)

class EnhancedStackingClassifier:
    """
    Stacking Classifier mejorado que combina múltiples modelos base
    con un meta-modelo para decisiones finales más robustas
    """
    
    def __init__(self, use_existing_models=True):
        """
        Inicializar Stacking Classifier
        
        Args:
            use_existing_models: Si usar modelos ya entrenados del sistema
        """
        self.use_existing_models = use_existing_models
        self.base_models = {}
        self.meta_model = None
        self.stacking_classifier = None
        self.scaler = RobustScaler()
        self.is_trained = False
        
        # Configuración
        self.cv_folds = 3  # Reducido para mejor performance
        self.min_samples = 100
        
        logger.info("Enhanced Stacking Classifier inicializado")
    
    def create_base_models(self):
        """Crear modelos base optimizados para stacking"""
        try:
            base_models = []
            
            # 1. Random Forest - Rápido y robusto
            rf = RandomForestClassifier(
                n_estimators=100,  # Reducido para velocidad
                max_depth=10,
                min_samples_split=10,
                max_features='sqrt',
                random_state=42,
                n_jobs=-1
            )
            base_models.append(('rf', rf))
            
            # 2. Gradient Boosting - Buena precisión
            gb = GradientBoostingClassifier(
                n_estimators=50,  # Reducido para velocidad
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            base_models.append(('gb', gb))
            
            # 3. Extra Trees - Diversidad
            et = ExtraTreesClassifier(
                n_estimators=50,
                max_depth=8,
                min_samples_split=10,
                max_features='sqrt',
                random_state=42,
                n_jobs=-1
            )
            base_models.append(('et', et))
            
            # 4. MLP Classifier - Red neuronal simple
            mlp = MLPClassifier(
                hidden_layer_sizes=(50,),
                max_iter=200,
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1
            )
            base_models.append(('mlp', mlp))
            
            # 5. AdaBoost - Boosting alternativo
            ada = AdaBoostClassifier(
                n_estimators=50,
                learning_rate=1.0,
                random_state=42
            )
            base_models.append(('ada', ada))
            
            return base_models
            
        except Exception as e:
            logger.error(f"Error creando modelos base: {e}")
            return []
    
    def create_meta_model(self):
        """Crear meta-modelo para stacking"""
        try:
            # Logistic Regression como meta-modelo (rápido y efectivo)
            meta_model = LogisticRegression(
                C=1.0,
                max_iter=1000,
                random_state=42,
                n_jobs=-1
            )
            
            return meta_model
            
        except Exception as e:
            logger.error(f"Error creando meta-modelo: {e}")
            return LogisticRegression(random_state=42)
    
    def train(self, X, y, symbol='default'):
        """
        Entrenar el Stacking Classifier
        
        Args:
            X: Features de entrenamiento
            y: Target variable
            symbol: Símbolo para identificación
        """
        try:
            logger.info(f"Entrenando Stacking Classifier para {symbol}")
            
            # Validar datos
            if len(X) < self.min_samples:
                logger.warning(f"Datos insuficientes: {len(X)} < {self.min_samples}")
                return False
            
            # Limpiar datos
            valid_idx = ~(pd.isna(y) | np.isinf(X).any(axis=1))
            X_clean = X[valid_idx]
            y_clean = y[valid_idx]
            
            if len(X_clean) < self.min_samples:
                logger.warning(f"Datos válidos insuficientes: {len(X_clean)}")
                return False
            
            # Escalar features
            X_scaled = self.scaler.fit_transform(X_clean)
            
            # Crear modelos
            base_models = self.create_base_models()
            meta_model = self.create_meta_model()
            
            if not base_models:
                logger.error("No se pudieron crear modelos base")
                return False
            
            # Crear Stacking Classifier con configuración simplificada
            self.stacking_classifier = StackingClassifier(
                estimators=base_models,
                final_estimator=meta_model,
                cv=2,  # Reducir a 2-fold para evitar problemas
                stack_method='auto',  # Usar auto en lugar de predict_proba
                n_jobs=1,  # Usar un solo proceso para evitar problemas de concurrencia
                verbose=0
            )
            
            # Entrenar
            start_time = datetime.now()
            self.stacking_classifier.fit(X_scaled, y_clean)
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Evaluar con cross-validation
            cv_scores = cross_val_score(
                self.stacking_classifier, X_scaled, y_clean,
                cv=TimeSeriesSplit(n_splits=3),
                scoring='accuracy',
                n_jobs=-1
            )
            
            avg_cv_score = np.mean(cv_scores)
            
            logger.info(f"Stacking Classifier entrenado para {symbol}")
            logger.info(f"Tiempo de entrenamiento: {training_time:.2f}s")
            logger.info(f"CV Score promedio: {avg_cv_score:.3f}")
            logger.info(f"CV Score std: {np.std(cv_scores):.3f}")
            
            self.is_trained = True
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando Stacking Classifier: {e}")
            return False
    
    def predict(self, X):
        """
        Realizar predicción con el Stacking Classifier
        
        Args:
            X: Features para predicción
            
        Returns:
            dict: Predicción y confianza
        """
        try:
            if not self.is_trained or self.stacking_classifier is None:
                logger.warning("Modelo no entrenado")
                return {'prediction': 1, 'confidence': 0.0, 'probabilities': [0.33, 0.34, 0.33]}
            
            # Escalar features
            X_scaled = self.scaler.transform(X.reshape(1, -1) if X.ndim == 1 else X)
            
            # Predicción
            prediction = self.stacking_classifier.predict(X_scaled)[0]
            probabilities = self.stacking_classifier.predict_proba(X_scaled)[0]
            confidence = np.max(probabilities)
            
            return {
                'prediction': int(prediction),
                'confidence': float(confidence),
                'probabilities': probabilities.tolist()
            }
            
        except Exception as e:
            logger.error(f"Error en predicción: {e}")
            return {'prediction': 1, 'confidence': 0.0, 'probabilities': [0.33, 0.34, 0.33]}
    
    def get_feature_importance(self):
        """Obtener importancia de features del ensemble"""
        try:
            if not self.is_trained:
                return {}
            
            importance_dict = {}
            
            # Importancia de modelos base
            for name, estimator in self.stacking_classifier.named_estimators_.items():
                if hasattr(estimator, 'feature_importances_'):
                    importance_dict[f'{name}_importance'] = estimator.feature_importances_
            
            # Coeficientes del meta-modelo
            if hasattr(self.stacking_classifier.final_estimator_, 'coef_'):
                importance_dict['meta_model_coef'] = self.stacking_classifier.final_estimator_.coef_[0]
            
            return importance_dict
            
        except Exception as e:
            logger.error(f"Error obteniendo importancia: {e}")
            return {}
    
    def save_model(self, filepath):
        """Guardar modelo entrenado"""
        try:
            if not self.is_trained:
                logger.warning("No hay modelo entrenado para guardar")
                return False
            
            model_data = {
                'stacking_classifier': self.stacking_classifier,
                'scaler': self.scaler,
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
            
            self.stacking_classifier = model_data['stacking_classifier']
            self.scaler = model_data['scaler']
            self.is_trained = model_data['is_trained']
            
            logger.info(f"Modelo cargado desde: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            return False
    
    def get_model_info(self):
        """Obtener información del modelo"""
        try:
            if not self.is_trained:
                return {"status": "not_trained"}
            
            info = {
                "status": "trained",
                "base_models": list(self.stacking_classifier.named_estimators_.keys()),
                "meta_model": type(self.stacking_classifier.final_estimator_).__name__,
                "cv_folds": self.cv_folds,
                "scaler": type(self.scaler).__name__
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error obteniendo info del modelo: {e}")
            return {"status": "error", "error": str(e)}


class StackingIntegrator:
    """
    Integrador para usar Stacking Classifier con el sistema SICAR existente
    """
    
    def __init__(self, advanced_ml_engine=None):
        """
        Inicializar integrador
        
        Args:
            advanced_ml_engine: Instancia del motor ML existente
        """
        self.advanced_ml_engine = advanced_ml_engine
        self.stacking_classifiers = {}
        
        logger.info("Stacking Integrator inicializado")
    
    def integrate_with_existing_system(self, symbol, X, y):
        """
        Integrar Stacking Classifier con sistema existente
        
        Args:
            symbol: Símbolo de trading
            X: Features
            y: Target
        """
        try:
            # Crear y entrenar Stacking Classifier
            stacking_clf = EnhancedStackingClassifier()
            
            if stacking_clf.train(X, y, symbol):
                self.stacking_classifiers[symbol] = stacking_clf
                logger.info(f"Stacking Classifier integrado para {symbol}")
                return True
            else:
                logger.warning(f"No se pudo integrar Stacking Classifier para {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error integrando sistema: {e}")
            return False
    
    def get_enhanced_prediction(self, symbol, features):
        """
        Obtener predicción mejorada combinando sistemas
        
        Args:
            symbol: Símbolo de trading
            features: Features para predicción
            
        Returns:
            dict: Predicción combinada
        """
        try:
            predictions = {}
            
            # Predicción del sistema original
            if self.advanced_ml_engine and symbol in self.advanced_ml_engine.models:
                try:
                    original_pred = self.advanced_ml_engine.predict(symbol, features)
                    predictions['original'] = original_pred
                except Exception as e:
                    logger.warning(f"Error en predicción original: {e}")
            
            # Predicción del Stacking Classifier
            if symbol in self.stacking_classifiers:
                try:
                    stacking_pred = self.stacking_classifiers[symbol].predict(features)
                    predictions['stacking'] = stacking_pred
                except Exception as e:
                    logger.warning(f"Error en predicción stacking: {e}")
            
            # Combinar predicciones
            if predictions:
                return self._combine_predictions(predictions)
            else:
                return {'prediction': 1, 'confidence': 0.0, 'method': 'default'}
                
        except Exception as e:
            logger.error(f"Error obteniendo predicción mejorada: {e}")
            return {'prediction': 1, 'confidence': 0.0, 'method': 'error'}
    
    def _combine_predictions(self, predictions):
        """Combinar múltiples predicciones"""
        try:
            if len(predictions) == 1:
                pred_data = list(predictions.values())[0]
                pred_data['method'] = list(predictions.keys())[0]
                return pred_data
            
            # Promedio ponderado por confianza
            total_weight = 0
            weighted_prediction = 0
            avg_confidence = 0
            
            for method, pred_data in predictions.items():
                confidence = pred_data.get('confidence', 0.5)
                prediction = pred_data.get('prediction', 1)
                
                weighted_prediction += prediction * confidence
                total_weight += confidence
                avg_confidence += confidence
            
            if total_weight > 0:
                final_prediction = int(round(weighted_prediction / total_weight))
                final_confidence = avg_confidence / len(predictions)
            else:
                final_prediction = 1
                final_confidence = 0.0
            
            return {
                'prediction': final_prediction,
                'confidence': final_confidence,
                'method': 'combined',
                'individual_predictions': predictions
            }
            
        except Exception as e:
            logger.error(f"Error combinando predicciones: {e}")
            return {'prediction': 1, 'confidence': 0.0, 'method': 'error'}


if __name__ == "__main__":
    # Test básico
    logging.basicConfig(level=logging.INFO)
    
    # Crear datos de prueba
    np.random.seed(42)
    X_test = np.random.randn(200, 20)
    y_test = np.random.randint(0, 3, 200)
    
    # Probar Stacking Classifier
    stacking_clf = EnhancedStackingClassifier()
    
    if stacking_clf.train(X_test, y_test, 'TEST'):
        # Hacer predicción
        test_features = np.random.randn(20)
        prediction = stacking_clf.predict(test_features)
        
        print("Predicción de prueba:", prediction)
        print("Info del modelo:", stacking_clf.get_model_info())
        
        # Guardar modelo
        stacking_clf.save_model('test_stacking_model.joblib')
        
        print("✅ Test del Stacking Classifier completado exitosamente")
    else:
        print("❌ Error en el test del Stacking Classifier")