# /src/module_3_metacontroller.py

import xgboost as xgb
import pandas as pd
import numpy as np
import joblib
import os
import sys
import logging
from typing import Dict, List, Tuple, Optional, Any
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Agregar el directorio padre al path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import N_REGIMES

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Definición de Sub-Estrategias (Ladrillos Lógicos) ---
# Estas son las herramientas que el Metacontrolador aprenderá a usar.

def strategy_momentum(data: pd.DataFrame) -> pd.Series:
    """
    Estrategia simple de seguimiento de tendencia.
    Genera una señal de compra (1) o venta (-1) basada en el cruce de medias móviles.
    
    Args:
        data: DataFrame con datos OHLCV
        
    Returns:
        Serie con señales de trading
    """
    try:
        # Normalizar nombres de columnas
        data = data.copy()
        data.columns = data.columns.str.lower()
        
        sma_fast = data['close'].rolling(window=10).mean()
        sma_slow = data['close'].rolling(window=50).mean()
        signal = pd.Series(np.where(sma_fast > sma_slow, 1, -1), index=data.index)
        # Devuelve la señal directa
        return signal.fillna(0)
    except Exception as e:
        logger.error(f"Error en strategy_momentum: {str(e)}")
        return pd.Series(0, index=data.index)

def strategy_mean_reversion(data: pd.DataFrame) -> pd.Series:
    """
    Estrategia de reversión a la media.
    Genera señales basadas en la desviación del precio respecto a su media.
    
    Args:
        data: DataFrame con datos OHLCV
        
    Returns:
        Serie con señales de trading
    """
    try:
        # Normalizar nombres de columnas
        data = data.copy()
        data.columns = data.columns.str.lower()
        
        sma = data['close'].rolling(window=20).mean()
        std = data['close'].rolling(window=20).std()
        z_score = (data['close'] - sma) / std
        
        # Señal de compra cuando el precio está muy por debajo de la media
        # Señal de venta cuando el precio está muy por encima de la media
        signal = pd.Series(np.where(z_score < -2, 1, np.where(z_score > 2, -1, 0)), index=data.index)
        return signal.fillna(0)
    except Exception as e:
        logger.error(f"Error en strategy_mean_reversion: {str(e)}")
        return pd.Series(0, index=data.index)

def strategy_breakout(data: pd.DataFrame) -> pd.Series:
    """
    Estrategia de ruptura de niveles.
    Genera señales cuando el precio rompe niveles de soporte/resistencia.
    
    Args:
        data: DataFrame con datos OHLCV
        
    Returns:
        Serie con señales de trading
    """
    try:
        # Normalizar nombres de columnas
        data = data.copy()
        data.columns = data.columns.str.lower()
        
        # Calcular máximos y mínimos de los últimos 20 períodos
        high_20 = data['high'].rolling(window=20).max()
        low_20 = data['low'].rolling(window=20).min()
        
        # Señal de compra cuando el precio rompe por encima del máximo
        # Señal de venta cuando el precio rompe por debajo del mínimo
        signal = pd.Series(
            np.where(data['close'] > high_20.shift(1), 1,
                    np.where(data['close'] < low_20.shift(1), -1, 0)),
            index=data.index
        )
        return signal.fillna(0)
    except Exception as e:
        logger.error(f"Error en strategy_breakout: {str(e)}")
        return pd.Series(0, index=data.index)

def create_labels(data: pd.DataFrame) -> pd.Series:
    """
    Crea las etiquetas para entrenar el metacontrolador.
    Para cada punto en el tiempo, determina qué estrategia habría sido la más rentable.
    Esta es la "respuesta correcta" que el modelo aprenderá.
    
    Args:
        data: DataFrame con datos OHLCV
        
    Returns:
        Serie con etiquetas de estrategias óptimas
    """
    try:
        logger.info("Creando etiquetas para entrenamiento del metacontrolador...")
        
        # Buscar la columna de precios de cierre
        close_col = None
        for col in ['close', 'Close', 'CLOSE']:
            if col in data.columns:
                close_col = col
                break
        
        if close_col is None:
            raise ValueError("No se encontró columna de precios de cierre (close/Close/CLOSE)")
        
        logger.info(f"Usando columna '{close_col}' para precios de cierre")
        
        # Usamos shift(-1) para mirar el retorno del siguiente período y evitar sesgo de anticipación
        returns = data[close_col].pct_change().shift(-1)
        
        # Calculamos los retornos hipotéticos de cada estrategia
        # Usamos shift(1) en las señales para asegurar que operamos con la información de la vela anterior
        momentum_signals = strategy_momentum(data).shift(1)
        mean_reversion_signals = strategy_mean_reversion(data).shift(1)
        breakout_signals = strategy_breakout(data).shift(1)
        
        momentum_returns = momentum_signals * returns
        mean_reversion_returns = mean_reversion_signals * returns
        breakout_returns = breakout_signals * returns
        
        # Creamos un DataFrame con los retornos de cada opción
        strategy_returns = pd.DataFrame({
            'momentum': momentum_returns,
            'mean_reversion': mean_reversion_returns,
            'breakout': breakout_returns,
            'hold': 0  # La opción de no hacer nada siempre tiene un retorno de 0
        }).fillna(0)
        
        # La etiqueta es el nombre de la estrategia con el máximo retorno para cada vela
        labels = strategy_returns.idxmax(axis=1)
        
        # Mapeamos los nombres a números para el entrenamiento del modelo
        label_map = {'momentum': 0, 'mean_reversion': 1, 'breakout': 2, 'hold': 3}
        numeric_labels = labels.map(label_map)
        
        logger.info(f"Etiquetas creadas: {len(numeric_labels)} muestras")
        logger.info(f"Distribución de estrategias: {labels.value_counts().to_dict()}")
        
        return numeric_labels
        
    except Exception as e:
        logger.error(f"Error creando etiquetas: {str(e)}")
        return pd.Series(dtype=int)

class MetaController:
    """
    Módulo 3: Metacontrolador
    
    El cerebro de SICAR que aprende a seleccionar la mejor estrategia
    basándose en las características del mercado y el régimen actual.
    """
    
    def __init__(self):
        """Inicializa el metacontrolador."""
        self.model = None
        self.is_fitted = False
        self.feature_names = []
        self.strategy_names = {
            0: 'momentum',
            1: 'mean_reversion', 
            2: 'breakout',
            3: 'hold'
        }
        self.strategy_functions = {
            'momentum': strategy_momentum,
            'mean_reversion': strategy_mean_reversion,
            'breakout': strategy_breakout
        }
        
        # Directorio para guardar modelos
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        os.makedirs(self.models_dir, exist_ok=True)
    
    def prepare_features(self, market_data: pd.DataFrame, 
                        regime_data: Optional[pd.DataFrame] = None,
                        causal_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Prepara las características para el entrenamiento/predicción.
        
        Args:
            market_data: DataFrame con datos de mercado procesados
            regime_data: DataFrame con clasificación de regímenes (opcional)
            causal_data: DataFrame con datos causales (opcional)
            
        Returns:
            DataFrame con características preparadas
        """
        try:
            logger.info("Preparando características para el metacontrolador...")
            
            # Normalizar nombres de columnas a minúsculas para compatibilidad
            market_data = market_data.copy()
            market_data.columns = market_data.columns.str.lower()
            
            features = pd.DataFrame(index=market_data.index)
            
            # 1. Características básicas de mercado
            if 'volatility' in market_data.columns:
                vol_data = market_data['volatility']
                if isinstance(vol_data, pd.DataFrame):
                    features['volatility'] = vol_data.iloc[:, 0]
                else:
                    features['volatility'] = vol_data
            else:
                features['volatility'] = market_data['close'].pct_change().rolling(20).std()
            
            if 'momentum_20' in market_data.columns:
                mom_data = market_data['momentum_20']
                if isinstance(mom_data, pd.DataFrame):
                    features['momentum'] = mom_data.iloc[:, 0]
                else:
                    features['momentum'] = mom_data
            else:
                features['momentum'] = market_data['close'].pct_change(20)
            
            if 'rsi' in market_data.columns:
                # Si hay múltiples columnas RSI, tomar la primera
                rsi_data = market_data['rsi']
                if isinstance(rsi_data, pd.DataFrame):
                    features['rsi'] = rsi_data.iloc[:, 0]  # Tomar la primera columna
                else:
                    features['rsi'] = rsi_data
            else:
                # Calcular RSI básico
                delta = market_data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                features['rsi'] = 100 - (100 / (1 + rs))
            
            if 'volume_ratio' in market_data.columns:
                vol_ratio_data = market_data['volume_ratio']
                if isinstance(vol_ratio_data, pd.DataFrame):
                    features['volume_ratio'] = vol_ratio_data.iloc[:, 0]
                else:
                    features['volume_ratio'] = vol_ratio_data
            else:
                volume_sma = market_data['volume'].rolling(20).mean()
                features['volume_ratio'] = market_data['volume'] / volume_sma
            
            # 2. Características de tendencia
            sma_20 = market_data['close'].rolling(20).mean()
            sma_50 = market_data['close'].rolling(50).mean()
            features['trend_strength'] = (market_data['close'] - sma_20) / sma_20
            features['trend_direction'] = np.where(sma_20 > sma_50, 1, -1)
            
            # 3. Características de régimen (si están disponibles)
            if regime_data is not None and 'regime' in regime_data.columns:
                # Crear variables dummy para cada régimen
                for regime in range(N_REGIMES):
                    features[f'regime_{regime}'] = (regime_data['regime'] == regime).astype(int)
            else:
                # Valores por defecto si no hay datos de régimen
                for regime in range(N_REGIMES):
                    features[f'regime_{regime}'] = 0
            
            # 4. Características causales (si están disponibles)
            if causal_data is not None and len(causal_data) > 0:
                # Agregar características del grafo causal
                features['causal_relations'] = len(causal_data)
                features['causal_sentiment'] = causal_data['avg_sentiment'].mean() if 'avg_sentiment' in causal_data.columns else 0
            else:
                features['causal_relations'] = 0
                features['causal_sentiment'] = 0
            
            # 5. Características temporales
            if hasattr(features.index, 'hour'):
                features['hour'] = features.index.hour
                features['day_of_week'] = features.index.dayofweek
            else:
                features['hour'] = 0
                features['day_of_week'] = 0
            
            # Rellenar valores NaN con métodos apropiados
            # Para características numéricas, usar forward fill y luego backward fill
            numeric_cols = ['volatility', 'momentum', 'rsi', 'volume_ratio', 'trend_strength']
            for col in numeric_cols:
                if col in features.columns:
                    features[col] = features[col].fillna(method='ffill').fillna(method='bfill')
            
            # Para características categóricas, usar valores por defecto
            categorical_cols = ['trend_direction'] + [f'regime_{i}' for i in range(N_REGIMES)]
            for col in categorical_cols:
                if col in features.columns:
                    features[col] = features[col].fillna(0)
            
            # Para características temporales y causales, usar valores por defecto
            default_cols = ['hour', 'day_of_week', 'causal_relations', 'causal_sentiment']
            for col in default_cols:
                if col in features.columns:
                    features[col] = features[col].fillna(0)
            
            # Solo eliminar filas donde TODAS las características sean NaN
            features = features.dropna(how='all')
            
            # Si aún hay NaN, rellenar con 0
            features = features.fillna(0)
            
            # Guardar nombres de características
            self.feature_names = features.columns.tolist()
            
            logger.info(f"Características preparadas: {len(self.feature_names)} features, {len(features)} muestras")
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparando características: {str(e)}")
            return pd.DataFrame()
    
    def train_metacontroller(self, features: pd.DataFrame, labels: pd.Series) -> bool:
        """
        Entrena un clasificador XGBoost para que aprenda a seleccionar la mejor estrategia
        basándose en las características del mercado.
        
        Args:
            features: DataFrame con características
            labels: Serie con etiquetas de estrategias óptimas
            
        Returns:
            True si el entrenamiento fue exitoso, False en caso contrario
        """
        try:
            logger.info("Entrenando metacontrolador XGBoost...")
            
            # Asegurar que las características y las etiquetas estén alineadas y sin valores nulos
            combined = pd.concat([features, labels.rename('label')], axis=1).dropna()
            
            if len(combined) == 0:
                logger.error("No hay datos válidos para entrenar")
                return False
            
            X = combined.drop(columns=['label'])
            y = combined['label']
            
            # Verificar que tenemos todas las clases
            unique_labels = y.unique()
            logger.info(f"Clases encontradas en entrenamiento: {unique_labels}")
            
            # Definir el modelo XGBoost para clasificación multiclase
            self.model = xgb.XGBClassifier(
                objective='multi:softmax',
                num_class=4,  # momentum, mean_reversion, breakout, hold
                use_label_encoder=False,
                eval_metric='mlogloss',
                random_state=42,
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8
            )
            
            # Entrenar el modelo
            self.model.fit(X, y)
            
            # Calcular importancia de características
            feature_importance = dict(zip(X.columns, self.model.feature_importances_))
            sorted_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
            
            logger.info("Importancia de características:")
            for feature, importance in list(sorted_importance.items())[:10]:
                logger.info(f"  {feature}: {importance:.4f}")
            
            # Establecer como entrenado ANTES de guardar
            self.is_fitted = True
            
            # Guardar modelo
            self._save_model(sorted_importance)
            
            logger.info("Metacontrolador XGBoost entrenado con éxito.")
            
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando metacontrolador: {str(e)}")
            return False
    
    def predict_strategy(self, features: pd.DataFrame) -> Tuple[str, float]:
        """
        Predice la mejor estrategia para las características dadas.
        
        Args:
            features: DataFrame con características actuales
            
        Returns:
            Tupla con (nombre_estrategia, confianza)
        """
        try:
            if not self.is_fitted or self.model is None:
                logger.warning("Modelo no entrenado, usando estrategia por defecto")
                return 'hold', 0.0
            
            # Asegurar que tenemos todas las características necesarias
            missing_features = set(self.feature_names) - set(features.columns)
            if missing_features:
                logger.warning(f"Características faltantes: {missing_features}")
                # Agregar características faltantes con valor 0
                for feature in missing_features:
                    features[feature] = 0
            
            # Reordenar columnas para coincidir con el entrenamiento
            features = features[self.feature_names]
            
            # Predecir estrategia
            prediction = self.model.predict(features.iloc[[-1]])[0]
            
            # Obtener probabilidades para calcular confianza
            probabilities = self.model.predict_proba(features.iloc[[-1]])[0]
            confidence = max(probabilities)
            
            strategy_name = self.strategy_names.get(prediction, 'hold')
            
            logger.info(f"Estrategia predicha: {strategy_name} (confianza: {confidence:.2f})")
            
            return strategy_name, confidence
            
        except Exception as e:
            logger.error(f"Error prediciendo estrategia: {str(e)}")
            return 'hold', 0.0
    
    def execute_strategy(self, strategy_name: str, market_data: pd.DataFrame) -> float:
        """
        Ejecuta la estrategia seleccionada y devuelve la señal.
        
        Args:
            strategy_name: Nombre de la estrategia a ejecutar
            market_data: DataFrame con datos de mercado
            
        Returns:
            Señal de trading (-1, 0, 1)
        """
        try:
            if strategy_name == 'hold':
                return 0.0
            
            if strategy_name not in self.strategy_functions:
                logger.warning(f"Estrategia desconocida: {strategy_name}")
                return 0.0
            
            strategy_func = self.strategy_functions[strategy_name]
            signals = strategy_func(market_data)
            
            # Devolver la última señal
            if len(signals) > 0:
                return float(signals.iloc[-1])
            else:
                return 0.0
                
        except Exception as e:
            logger.error(f"Error ejecutando estrategia {strategy_name}: {str(e)}")
            return 0.0
    
    def _save_model(self, feature_importance: Dict[str, float]):
        """
        Guarda el modelo entrenado y metadatos.
        
        Args:
            feature_importance: Diccionario con importancia de características
        """
        try:
            # Guardar modelo XGBoost
            model_path = os.path.join(self.models_dir, "metacontroller.joblib")
            joblib.dump({
                'model': self.model,
                'feature_names': self.feature_names,
                'strategy_names': self.strategy_names,
                'is_fitted': self.is_fitted
            }, model_path)
            
            # Guardar metadatos
            metadata_path = os.path.join(self.models_dir, "metacontroller_metadata.json")
            metadata = {
                'feature_importance': feature_importance,
                'feature_names': self.feature_names,
                'strategy_names': self.strategy_names,
                'trained_at': datetime.now().isoformat(),
                'model_type': 'XGBoost'
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Modelo guardado en {model_path}")
            logger.info(f"Metadatos guardados en {metadata_path}")
            
        except Exception as e:
            logger.error(f"Error guardando modelo: {str(e)}")
    
    def load_model(self, model_path: str = None) -> bool:
        """
        Carga un modelo previamente entrenado.
        
        Args:
            model_path: Ruta al archivo del modelo
            
        Returns:
            True si se cargó exitosamente, False en caso contrario
        """
        try:
            if model_path is None:
                model_path = os.path.join(self.models_dir, "metacontroller.joblib")
            
            if not os.path.exists(model_path):
                logger.warning(f"Archivo de modelo no encontrado: {model_path}")
                return False
            
            model_data = joblib.load(model_path)
            
            self.model = model_data['model']
            self.feature_names = model_data['feature_names']
            self.strategy_names = model_data['strategy_names']
            self.is_fitted = model_data['is_fitted']
            
            logger.info(f"Modelo cargado exitosamente desde {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {str(e)}")
            return False
    
    def analyze_multi_timeframe_strategies(self, multi_data: dict, 
                                         multi_regime_analysis: dict = None) -> dict:
        """
        Analiza estrategias óptimas para múltiples timeframes.
        
        Args:
            multi_data: Diccionario con datos de múltiples timeframes
            multi_regime_analysis: Análisis de regímenes por timeframe
            
        Returns:
            Diccionario con estrategias recomendadas por timeframe
        """
        logger.info("🔄 Iniciando análisis multi-timeframe de estrategias...")
        
        multi_strategy_analysis = {}
        
        for timeframe, data in multi_data.items():
            try:
                logger.info(f"⏱️ Analizando estrategias en {timeframe}...")
                
                # Obtener análisis de régimen para este timeframe
                regime_data = None
                if multi_regime_analysis and timeframe in multi_regime_analysis.get('timeframe_analysis', {}):
                    regime_data = multi_regime_analysis['timeframe_analysis'][timeframe]
                
                # Preparar características para este timeframe
                features = self._prepare_timeframe_features(data, regime_data, timeframe)
                
                if features.empty:
                    logger.warning(f"⚠️ No se pudieron preparar características para {timeframe}")
                    continue
                
                # Predecir estrategia óptima
                if self.is_fitted:
                    strategy, confidence = self.predict_strategy(features.tail(1))
                    
                    # Análisis adicional específico del timeframe
                    strategy_analysis = self._analyze_timeframe_strategy(
                        timeframe, data, strategy, confidence, regime_data
                    )
                    
                    multi_strategy_analysis[timeframe] = strategy_analysis
                    logger.info(f"✅ {timeframe}: Estrategia {strategy} (confianza: {confidence:.2f})")
                    
                else:
                    logger.warning(f"⚠️ Modelo no entrenado, usando estrategia por defecto para {timeframe}")
                    strategy_analysis = {
                        'timeframe': timeframe,
                        'strategy': 'hold',
                        'confidence': 0.5,
                        'signal': 0.0,
                        'risk_level': 'medio'
                    }
                    multi_strategy_analysis[timeframe] = strategy_analysis
                    
            except Exception as e:
                logger.error(f"❌ Error analizando estrategias en {timeframe}: {str(e)}")
                continue
        
        # Análisis de consenso entre estrategias de diferentes timeframes
        consensus_analysis = self._calculate_strategy_consensus(multi_strategy_analysis)
        
        result = {
            'timeframe_analysis': multi_strategy_analysis,
            'consensus': consensus_analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"🎯 Análisis multi-timeframe de estrategias completado: {len(multi_strategy_analysis)} timeframes")
        return result
    
    def _prepare_timeframe_features(self, data: pd.DataFrame, 
                                  regime_data: dict = None, 
                                  timeframe: str = None) -> pd.DataFrame:
        """
        Prepara características específicas para un timeframe.
        
        Args:
            data: Datos de mercado del timeframe
            regime_data: Análisis de régimen del timeframe
            timeframe: Nombre del timeframe
            
        Returns:
            DataFrame con características preparadas
        """
        try:
            # Preparar características básicas de mercado
            features = self.prepare_features(data)
            
            # Agregar características específicas del timeframe
            if regime_data:
                # Agregar información del régimen
                features['regime'] = regime_data.get('regime', 0)
                features['regime_confidence'] = regime_data.get('confidence', 0.5)
                features['regime_strength'] = regime_data.get('regime_strength', 0.5)
                features['momentum'] = regime_data.get('momentum', 0.0)
                features['volatility_level'] = self._encode_volatility_level(
                    regime_data.get('volatility_level', 'media')
                )
                features['trend_direction'] = self._encode_trend_direction(
                    regime_data.get('trend_direction', 'lateral')
                )
            
            # Agregar peso del timeframe (distribución jerárquica)
            timeframe_weights = {
                '15m': 0.08,   # Timeframes cortos: ruido pero útiles para timing
                '30m': 0.12,
                '45m': 0.15,
                '1h': 0.20,    # Timeframes intermedios: balance entre señal y ruido
                '2h': 0.18,
                '3h': 0.15,    # Timeframes largos: tendencias principales
                '4h': 0.12
            }
            features['timeframe_weight'] = timeframe_weights.get(timeframe, 0.25)
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparando características para {timeframe}: {str(e)}")
            return pd.DataFrame()
    
    def _encode_volatility_level(self, volatility_level: str) -> float:
        """Codifica el nivel de volatilidad como número."""
        mapping = {'baja': 0.0, 'media': 0.5, 'alta': 1.0}
        return mapping.get(volatility_level, 0.5)
    
    def _encode_trend_direction(self, trend_direction: str) -> float:
        """Codifica la dirección de tendencia como número."""
        mapping = {'bajista': -1.0, 'lateral': 0.0, 'alcista': 1.0}
        return mapping.get(trend_direction, 0.0)
    
    def _analyze_timeframe_strategy(self, timeframe: str, data: pd.DataFrame,
                                  strategy: str, confidence: float,
                                  regime_data: dict = None) -> dict:
        """
        Análisis específico de la estrategia para un timeframe.
        
        Args:
            timeframe: Timeframe analizado
            data: Datos de mercado
            strategy: Estrategia recomendada
            confidence: Confianza de la predicción
            regime_data: Datos del régimen
            
        Returns:
            Diccionario con análisis detallado
        """
        try:
            # Ejecutar la estrategia para obtener señal
            signal = self.execute_strategy(strategy, data.tail(50))
            
            # Calcular métricas de riesgo
            recent_volatility = data['close'].pct_change().tail(20).std()
            
            # Determinar nivel de riesgo
            if recent_volatility > 0.03:
                risk_level = 'alto'
            elif recent_volatility > 0.015:
                risk_level = 'medio'
            else:
                risk_level = 'bajo'
            
            # Calcular fuerza de la señal
            signal_strength = abs(signal) * confidence
            
            analysis = {
                'timeframe': timeframe,
                'strategy': strategy,
                'confidence': confidence,
                'signal': signal,
                'signal_strength': signal_strength,
                'risk_level': risk_level,
                'recent_volatility': recent_volatility,
                'regime_info': regime_data if regime_data else {},
                'recommendation': self._generate_recommendation(strategy, signal, confidence, risk_level)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error en análisis de estrategia para {timeframe}: {str(e)}")
            return {
                'timeframe': timeframe,
                'strategy': strategy,
                'confidence': confidence,
                'signal': 0.0,
                'risk_level': 'medio',
                'error': str(e)
            }
    
    def _generate_recommendation(self, strategy: str, signal: float, 
                               confidence: float, risk_level: str) -> str:
        """
        Genera una recomendación textual basada en el análisis.
        
        Args:
            strategy: Estrategia recomendada
            signal: Señal generada
            confidence: Confianza de la predicción
            risk_level: Nivel de riesgo
            
        Returns:
            Recomendación textual
        """
        if strategy == 'hold' or abs(signal) < 0.1:
            return f"Mantener posición. Confianza: {confidence:.1%}, Riesgo: {risk_level}"
        
        action = "Comprar" if signal > 0 else "Vender"
        strength = "fuerte" if abs(signal) > 0.7 else "moderada" if abs(signal) > 0.3 else "débil"
        
        return f"{action} - Señal {strength} ({strategy}). Confianza: {confidence:.1%}, Riesgo: {risk_level}"
    
    def _calculate_strategy_consensus(self, multi_strategy_analysis: dict) -> dict:
        """
        Calcula el consenso entre estrategias de diferentes timeframes.
        
        Args:
            multi_strategy_analysis: Análisis de estrategias por timeframe
            
        Returns:
            Diccionario con análisis de consenso
        """
        if not multi_strategy_analysis:
            return {
                'consensus_strategy': 'hold',
                'consensus_signal': 0.0,
                'agreement_level': 'bajo',
                'overall_confidence': 0.0
            }
        
        # Extraer estrategias, señales y confianzas
        strategies = []
        signals = []
        confidences = []
        timeframe_weights = {
            '45m': 0.15,
            '1h': 0.25,
            '3h': 0.35,
            '4h': 0.25
        }
        
        for tf, analysis in multi_strategy_analysis.items():
            strategies.append(analysis.get('strategy', 'hold'))
            signals.append(analysis.get('signal', 0.0))
            confidences.append(analysis.get('confidence', 0.5))
        
        if not strategies:
            return {
                'consensus_strategy': 'hold',
                'consensus_signal': 0.0,
                'agreement_level': 'bajo',
                'overall_confidence': 0.0
            }
        
        # Calcular señal ponderada
        weighted_signal = 0.0
        total_weight = 0.0
        
        for i, (tf, analysis) in enumerate(multi_strategy_analysis.items()):
            weight = timeframe_weights.get(tf, 0.25)
            confidence = confidences[i]
            signal = signals[i]
            
            weighted_signal += weight * confidence * signal
            total_weight += weight * confidence
        
        consensus_signal = weighted_signal / total_weight if total_weight > 0 else 0.0
        
        # Determinar estrategia de consenso
        strategy_counts = {}
        for strategy in strategies:
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        consensus_strategy = max(strategy_counts, key=strategy_counts.get)
        
        # Calcular nivel de acuerdo
        unique_strategies = len(set(strategies))
        if unique_strategies == 1:
            agreement_level = 'alto'
        elif unique_strategies == 2:
            agreement_level = 'medio'
        else:
            agreement_level = 'bajo'
        
        # Confianza general
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Análisis de divergencias
        divergences = []
        for tf, analysis in multi_strategy_analysis.items():
            if analysis.get('strategy') != consensus_strategy:
                divergences.append({
                    'timeframe': tf,
                    'strategy': analysis.get('strategy'),
                    'signal': analysis.get('signal', 0.0)
                })
        
        consensus = {
            'consensus_strategy': consensus_strategy,
            'consensus_signal': consensus_signal,
            'agreement_level': agreement_level,
            'overall_confidence': overall_confidence,
            'unique_strategies': unique_strategies,
            'divergences': divergences,
            'strategy_distribution': strategy_counts,
            'final_recommendation': self._generate_recommendation(
                consensus_strategy, consensus_signal, overall_confidence, 'medio'
            )
        }
        
        logger.info(f"🎯 Consenso de estrategias: {consensus_strategy} (señal: {consensus_signal:.2f}, acuerdo: {agreement_level})")
        
        return consensus

def main():
    """Función principal para probar el metacontrolador."""
    try:
        logger.info("Ejecutando ejemplo del Metacontrolador...")
        
        # Crear datos de ejemplo
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=1000, freq='4H')
        
        # Simular datos de mercado con diferentes patrones
        price = 100
        prices = []
        volumes = []
        
        for i in range(len(dates)):
            # Simular diferentes regímenes de mercado
            if i < 250:  # Tendencia alcista
                change = np.random.normal(0.002, 0.01)
            elif i < 500:  # Lateral
                change = np.random.normal(0, 0.008)
            elif i < 750:  # Tendencia bajista
                change = np.random.normal(-0.002, 0.01)
            else:  # Volátil
                change = np.random.normal(0, 0.02)
            
            price *= (1 + change)
            prices.append(price)
            volumes.append(np.random.normal(1000, 200))
        
        # Crear DataFrame de mercado
        market_data = pd.DataFrame({
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'close': prices,
            'volume': volumes
        }, index=dates)
        
        # Crear metacontrolador
        metacontroller = MetaController()
        
        # Preparar características (usando el módulo 2 si está disponible)
        try:
            from module_2_regime import RegimeClassifier
            regime_classifier = RegimeClassifier()
            regime_results = regime_classifier.classify_regimes(market_data)
            features = metacontroller.prepare_features(market_data, regime_results)
        except ImportError:
            logger.warning("Módulo 2 no disponible, usando características básicas")
            features = metacontroller.prepare_features(market_data)
        
        # Crear etiquetas
        labels = create_labels(market_data)
        
        # Alinear características y etiquetas
        aligned_data = pd.concat([features, labels.rename('label')], axis=1).dropna()
        if len(aligned_data) == 0:
            logger.error("No hay datos alineados para entrenar")
            return
        
        features_aligned = aligned_data.drop(columns=['label'])
        labels_aligned = aligned_data['label']
        
        # Entrenar metacontrolador
        success = metacontroller.train_metacontroller(features_aligned, labels_aligned)
        
        if success:
            print("\n=== METACONTROLADOR ENTRENADO ===")
            print(f"Características utilizadas: {len(metacontroller.feature_names)}")
            print(f"Muestras de entrenamiento: {len(features_aligned)}")
            
            # Probar predicción
            test_features = features_aligned.tail(1)
            strategy, confidence = metacontroller.predict_strategy(test_features)
            
            print(f"\n=== PREDICCIÓN DE EJEMPLO ===")
            print(f"Estrategia recomendada: {strategy}")
            print(f"Confianza: {confidence:.2f}")
            
            # Ejecutar estrategia
            signal = metacontroller.execute_strategy(strategy, market_data.tail(50))
            print(f"Señal generada: {signal}")
            
            print(f"\n✅ Metacontrolador funcionando correctamente")
        else:
            print("❌ Error en el entrenamiento del metacontrolador")
            
    except Exception as e:
        logger.error(f"Error en main: {str(e)}")
        print(f"❌ Error ejecutando ejemplo: {str(e)}")

if __name__ == '__main__':
    main()