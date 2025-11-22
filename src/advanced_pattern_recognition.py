"""
Sistema de Reconocimiento de Patrones Avanzado para SICAR
Utiliza machine learning para identificar patrones complejos de trading
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

from enhanced_logger import SICAR_LOGGER

logger = logging.getLogger(__name__)

class PatternType(Enum):
    """Tipos de patrones detectables"""
    BULLISH_REVERSAL = "bullish_reversal"
    BEARISH_REVERSAL = "bearish_reversal"
    CONTINUATION_BULLISH = "continuation_bullish"
    CONTINUATION_BEARISH = "continuation_bearish"
    CONSOLIDATION = "consolidation"
    BREAKOUT_PREPARATION = "breakout_preparation"
    VOLUME_ANOMALY = "volume_anomaly"
    MOMENTUM_SHIFT = "momentum_shift"

class PatternStrength(Enum):
    """Fuerza del patrón detectado"""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"

@dataclass
class PatternSignal:
    """Señal de patrón detectado"""
    symbol: str
    timestamp: datetime
    pattern_type: PatternType
    strength: PatternStrength
    confidence: float
    probability: float
    features: Dict[str, float]
    prediction_horizon: int  # En minutos
    expected_move: float     # Movimiento esperado en %
    risk_reward_ratio: float

class AdvancedPatternRecognition:
    """Sistema avanzado de reconocimiento de patrones"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.pattern_history = []
        self.is_trained = False
        
        # Configuración
        self.config = {
            'lookback_periods': 50,
            'min_confidence': 0.65,
            'feature_window': 20,
            'prediction_horizons': [5, 15, 30, 60],  # minutos
            'retrain_frequency': 100  # cada 100 nuevas muestras
        }
        
        # Inicializar modelos
        self._initialize_models()
        
        SICAR_LOGGER.log_alert("PATTERN_RECOGNITION_INIT", 
                              "Sistema de reconocimiento de patrones inicializado", "INFO")
    
    def _initialize_models(self):
        """Inicializar modelos de machine learning"""
        try:
            # Modelo principal para clasificación de patrones
            self.models['pattern_classifier'] = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42
            )
            
            # Modelo para detección de anomalías
            self.models['anomaly_detector'] = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            
            # Escaladores para normalización
            self.scalers['main'] = StandardScaler()
            self.scalers['anomaly'] = StandardScaler()
            
            SICAR_LOGGER.log_alert("MODELS_INIT", "Modelos ML inicializados correctamente", "INFO")
            
        except Exception as e:
            SICAR_LOGGER.log_error("MODELS_INIT", f"Error inicializando modelos: {e}")
    
    def extract_advanced_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extraer características avanzadas para ML"""
        try:
            if data is None or data.empty or len(data) < self.config['lookback_periods']:
                return pd.DataFrame()
            
            features = pd.DataFrame(index=data.index)
            
            # Características básicas de precio
            features['price_change'] = data['Close'].pct_change()
            features['high_low_ratio'] = (data['High'] - data['Low']) / data['Close']
            features['open_close_ratio'] = (data['Close'] - data['Open']) / data['Open']
            
            # Características de volumen
            features['volume_change'] = data['Volume'].pct_change()
            features['volume_price_trend'] = features['price_change'] * features['volume_change']
            features['volume_ma_ratio'] = data['Volume'] / data['Volume'].rolling(20).mean()
            
            # Indicadores técnicos avanzados
            features = self._add_technical_indicators(features, data)
            
            # Características de momentum
            features = self._add_momentum_features(features, data)
            
            # Características de volatilidad
            features = self._add_volatility_features(features, data)
            
            # Características de patrones de velas
            features = self._add_candlestick_patterns(features, data)
            
            # Características de microestructura
            features = self._add_microstructure_features(features, data)
            
            # Limpiar NaN y valores infinitos
            features = features.replace([np.inf, -np.inf], np.nan)
            features = features.fillna(method='ffill').fillna(0)
            
            return features
            
        except Exception as e:
            SICAR_LOGGER.log_error("FEATURE_EXTRACTION", f"Error extrayendo características: {e}")
            return pd.DataFrame()
    
    def _add_technical_indicators(self, features: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
        """Agregar indicadores técnicos avanzados"""
        try:
            # RSI con múltiples períodos
            for period in [14, 21, 30]:
                delta = data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                features[f'rsi_{period}'] = 100 - (100 / (1 + rs))
            
            # MACD con diferentes configuraciones
            exp1 = data['Close'].ewm(span=12).mean()
            exp2 = data['Close'].ewm(span=26).mean()
            features['macd'] = exp1 - exp2
            features['macd_signal'] = features['macd'].ewm(span=9).mean()
            features['macd_histogram'] = features['macd'] - features['macd_signal']
            
            # Bandas de Bollinger
            bb_period = 20
            bb_std = 2
            bb_ma = data['Close'].rolling(bb_period).mean()
            bb_std_dev = data['Close'].rolling(bb_period).std()
            features['bb_upper'] = bb_ma + (bb_std_dev * bb_std)
            features['bb_lower'] = bb_ma - (bb_std_dev * bb_std)
            features['bb_position'] = (data['Close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
            features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / bb_ma
            
            # Stochastic Oscillator
            low_min = data['Low'].rolling(window=14).min()
            high_max = data['High'].rolling(window=14).max()
            features['stoch_k'] = 100 * (data['Close'] - low_min) / (high_max - low_min)
            features['stoch_d'] = features['stoch_k'].rolling(window=3).mean()
            
            # Williams %R
            features['williams_r'] = -100 * (high_max - data['Close']) / (high_max - low_min)
            
            # Average True Range (ATR)
            high_low = data['High'] - data['Low']
            high_close = np.abs(data['High'] - data['Close'].shift())
            low_close = np.abs(data['Low'] - data['Close'].shift())
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            features['atr'] = true_range.rolling(window=14).mean()
            features['atr_ratio'] = features['atr'] / data['Close']
            
            return features
            
        except Exception as e:
            SICAR_LOGGER.log_error("TECHNICAL_INDICATORS", f"Error en indicadores técnicos: {e}")
            return features
    
    def _add_momentum_features(self, features: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
        """Agregar características de momentum"""
        try:
            # Rate of Change (ROC) con múltiples períodos
            for period in [5, 10, 20]:
                features[f'roc_{period}'] = ((data['Close'] - data['Close'].shift(period)) / 
                                           data['Close'].shift(period)) * 100
            
            # Momentum
            features['momentum_10'] = data['Close'] - data['Close'].shift(10)
            features['momentum_20'] = data['Close'] - data['Close'].shift(20)
            
            # Commodity Channel Index (CCI)
            tp = (data['High'] + data['Low'] + data['Close']) / 3
            sma_tp = tp.rolling(window=20).mean()
            mad = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
            features['cci'] = (tp - sma_tp) / (0.015 * mad)
            
            # Money Flow Index (MFI)
            typical_price = (data['High'] + data['Low'] + data['Close']) / 3
            money_flow = typical_price * data['Volume']
            
            positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
            negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
            
            positive_mf = positive_flow.rolling(window=14).sum()
            negative_mf = negative_flow.rolling(window=14).sum()
            
            mfi_ratio = positive_mf / negative_mf
            features['mfi'] = 100 - (100 / (1 + mfi_ratio))
            
            return features
            
        except Exception as e:
            SICAR_LOGGER.log_error("MOMENTUM_FEATURES", f"Error en características de momentum: {e}")
            return features
    
    def _add_volatility_features(self, features: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
        """Agregar características de volatilidad"""
        try:
            # Volatilidad histórica con múltiples ventanas
            returns = data['Close'].pct_change()
            for window in [5, 10, 20, 30]:
                features[f'volatility_{window}'] = returns.rolling(window=window).std() * np.sqrt(252)
            
            # Volatilidad relativa
            features['vol_ratio_short_long'] = (features['volatility_5'] / features['volatility_20'])
            
            # Parkinson volatility (usando High-Low)
            features['parkinson_vol'] = np.sqrt(
                (1 / (4 * np.log(2))) * 
                np.log(data['High'] / data['Low']).rolling(window=20).var()
            )
            
            # Garman-Klass volatility
            features['gk_vol'] = np.sqrt(
                0.5 * np.log(data['High'] / data['Low'])**2 - 
                (2 * np.log(2) - 1) * np.log(data['Close'] / data['Open'])**2
            ).rolling(window=20).mean()
            
            # Volatility clustering
            vol_short = returns.rolling(window=5).std()
            vol_long = returns.rolling(window=20).std()
            features['vol_clustering'] = vol_short / vol_long
            
            return features
            
        except Exception as e:
            SICAR_LOGGER.log_error("VOLATILITY_FEATURES", f"Error en características de volatilidad: {e}")
            return features
    
    def _add_candlestick_patterns(self, features: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
        """Agregar patrones de velas japonesas"""
        try:
            # Tamaño del cuerpo de la vela
            features['body_size'] = np.abs(data['Close'] - data['Open']) / data['Open']
            
            # Tamaño de las sombras
            features['upper_shadow'] = (data['High'] - np.maximum(data['Open'], data['Close'])) / data['Open']
            features['lower_shadow'] = (np.minimum(data['Open'], data['Close']) - data['Low']) / data['Open']
            
            # Ratio sombra/cuerpo
            features['shadow_body_ratio'] = (features['upper_shadow'] + features['lower_shadow']) / features['body_size']
            
            # Doji pattern (cuerpo pequeño)
            features['is_doji'] = (features['body_size'] < 0.001).astype(int)
            
            # Hammer pattern
            features['is_hammer'] = (
                (features['lower_shadow'] > 2 * features['body_size']) & 
                (features['upper_shadow'] < 0.5 * features['body_size'])
            ).astype(int)
            
            # Shooting star pattern
            features['is_shooting_star'] = (
                (features['upper_shadow'] > 2 * features['body_size']) & 
                (features['lower_shadow'] < 0.5 * features['body_size'])
            ).astype(int)
            
            # Engulfing patterns
            prev_body = np.abs(data['Close'].shift(1) - data['Open'].shift(1))
            curr_body = np.abs(data['Close'] - data['Open'])
            
            features['bullish_engulfing'] = (
                (data['Close'] > data['Open']) &  # Vela actual alcista
                (data['Close'].shift(1) < data['Open'].shift(1)) &  # Vela anterior bajista
                (data['Open'] < data['Close'].shift(1)) &  # Apertura menor que cierre anterior
                (data['Close'] > data['Open'].shift(1)) &  # Cierre mayor que apertura anterior
                (curr_body > prev_body)  # Cuerpo actual mayor que anterior
            ).astype(int)
            
            features['bearish_engulfing'] = (
                (data['Close'] < data['Open']) &  # Vela actual bajista
                (data['Close'].shift(1) > data['Open'].shift(1)) &  # Vela anterior alcista
                (data['Open'] > data['Close'].shift(1)) &  # Apertura mayor que cierre anterior
                (data['Close'] < data['Open'].shift(1)) &  # Cierre menor que apertura anterior
                (curr_body > prev_body)  # Cuerpo actual mayor que anterior
            ).astype(int)
            
            return features
            
        except Exception as e:
            SICAR_LOGGER.log_error("CANDLESTICK_PATTERNS", f"Error en patrones de velas: {e}")
            return features
    
    def _add_microstructure_features(self, features: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
        """Agregar características de microestructura del mercado"""
        try:
            # Spread implícito (High - Low)
            features['spread'] = (data['High'] - data['Low']) / data['Close']
            
            # Eficiencia del precio (qué tan directo es el movimiento)
            price_change = np.abs(data['Close'] - data['Open'])
            total_range = data['High'] - data['Low']
            features['price_efficiency'] = price_change / total_range
            
            # Presión de compra/venta
            features['buy_pressure'] = (data['Close'] - data['Low']) / (data['High'] - data['Low'])
            features['sell_pressure'] = (data['High'] - data['Close']) / (data['High'] - data['Low'])
            
            # Volume-Price Trend (VPT)
            features['vpt'] = (data['Volume'] * ((data['Close'] - data['Close'].shift(1)) / data['Close'].shift(1))).cumsum()
            
            # Ease of Movement
            distance_moved = ((data['High'] + data['Low']) / 2) - ((data['High'].shift(1) + data['Low'].shift(1)) / 2)
            box_height = data['Volume'] / (data['High'] - data['Low'])
            features['ease_of_movement'] = distance_moved / box_height
            features['ease_of_movement_ma'] = features['ease_of_movement'].rolling(window=14).mean()
            
            # Chaikin Money Flow
            mf_multiplier = ((data['Close'] - data['Low']) - (data['High'] - data['Close'])) / (data['High'] - data['Low'])
            mf_volume = mf_multiplier * data['Volume']
            features['cmf'] = mf_volume.rolling(window=20).sum() / data['Volume'].rolling(window=20).sum()
            
            return features
            
        except Exception as e:
            SICAR_LOGGER.log_error("MICROSTRUCTURE_FEATURES", f"Error en características de microestructura: {e}")
            return features
    
    def detect_patterns(self, data: pd.DataFrame, symbol: str) -> List[PatternSignal]:
        """Detectar patrones en los datos"""
        try:
            if data is None or data.empty:
                return []
            
            # Extraer características
            features = self.extract_advanced_features(data)
            if features.empty:
                return []
            
            patterns = []
            
            # Si el modelo está entrenado, usar predicciones ML
            if self.is_trained and 'pattern_classifier' in self.models:
                ml_patterns = self._detect_ml_patterns(features, data, symbol)
                patterns.extend(ml_patterns)
            
            # Detectar patrones basados en reglas
            rule_patterns = self._detect_rule_based_patterns(features, data, symbol)
            patterns.extend(rule_patterns)
            
            # Detectar anomalías
            anomaly_patterns = self._detect_anomalies(features, data, symbol)
            patterns.extend(anomaly_patterns)
            
            # Filtrar por confianza mínima
            filtered_patterns = [
                pattern for pattern in patterns 
                if pattern.confidence >= self.config['min_confidence']
            ]
            
            # Registrar patrones detectados
            self.pattern_history.extend(filtered_patterns)
            
            if filtered_patterns:
                SICAR_LOGGER.log_alert("PATTERNS_DETECTED", 
                    f"Detectados {len(filtered_patterns)} patrones en {symbol}", "INFO")
            
            return filtered_patterns
            
        except Exception as e:
            SICAR_LOGGER.log_error("PATTERN_DETECTION", f"Error detectando patrones: {e}")
            return []
    
    def _detect_ml_patterns(self, features: pd.DataFrame, data: pd.DataFrame, symbol: str) -> List[PatternSignal]:
        """Detectar patrones usando modelos ML"""
        try:
            patterns = []
            
            if len(features) < self.config['feature_window']:
                return patterns
            
            # Preparar datos para predicción
            recent_features = features.tail(self.config['feature_window'])
            feature_cols = [col for col in recent_features.columns if not recent_features[col].isna().all()]
            
            if not feature_cols:
                return patterns
            
            X = recent_features[feature_cols].fillna(0)
            
            # Escalar características
            if 'main' in self.scalers and hasattr(self.scalers['main'], 'scale_'):
                X_scaled = self.scalers['main'].transform(X)
            else:
                X_scaled = X.values
            
            # Hacer predicción
            if hasattr(self.models['pattern_classifier'], 'predict_proba'):
                probabilities = self.models['pattern_classifier'].predict_proba(X_scaled[-1:])
                predictions = self.models['pattern_classifier'].predict(X_scaled[-1:])
                
                # Convertir predicción a patrón
                pattern_type = self._prediction_to_pattern_type(predictions[0])
                confidence = np.max(probabilities[0])
                
                if confidence >= self.config['min_confidence']:
                    pattern = PatternSignal(
                        symbol=symbol,
                        timestamp=datetime.now(),
                        pattern_type=pattern_type,
                        strength=self._confidence_to_strength(confidence),
                        confidence=confidence,
                        probability=confidence,
                        features=dict(zip(feature_cols, X.iloc[-1].values)),
                        prediction_horizon=15,  # 15 minutos por defecto
                        expected_move=self._estimate_expected_move(pattern_type, confidence),
                        risk_reward_ratio=self._calculate_risk_reward(pattern_type, confidence)
                    )
                    patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            SICAR_LOGGER.log_error("ML_PATTERN_DETECTION", f"Error en detección ML: {e}")
            return []
    
    def _detect_rule_based_patterns(self, features: pd.DataFrame, data: pd.DataFrame, symbol: str) -> List[PatternSignal]:
        """Detectar patrones basados en reglas"""
        try:
            patterns = []
            
            if len(features) < 5:
                return patterns
            
            current_idx = len(features) - 1
            
            # Patrón de reversión alcista
            if self._is_bullish_reversal_pattern(features, current_idx):
                pattern = PatternSignal(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=PatternStrength.MODERATE,
                    confidence=0.75,
                    probability=0.75,
                    features={},
                    prediction_horizon=30,
                    expected_move=2.5,
                    risk_reward_ratio=2.0
                )
                patterns.append(pattern)
            
            # Patrón de reversión bajista
            if self._is_bearish_reversal_pattern(features, current_idx):
                pattern = PatternSignal(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=PatternStrength.MODERATE,
                    confidence=0.75,
                    probability=0.75,
                    features={},
                    prediction_horizon=30,
                    expected_move=-2.5,
                    risk_reward_ratio=2.0
                )
                patterns.append(pattern)
            
            # Patrón de preparación para breakout
            if self._is_breakout_preparation_pattern(features, current_idx):
                pattern = PatternSignal(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    pattern_type=PatternType.BREAKOUT_PREPARATION,
                    strength=PatternStrength.STRONG,
                    confidence=0.80,
                    probability=0.80,
                    features={},
                    prediction_horizon=15,
                    expected_move=3.0,
                    risk_reward_ratio=2.5
                )
                patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            SICAR_LOGGER.log_error("RULE_PATTERN_DETECTION", f"Error en detección por reglas: {e}")
            return []
    
    def _detect_anomalies(self, features: pd.DataFrame, data: pd.DataFrame, symbol: str) -> List[PatternSignal]:
        """Detectar anomalías en el comportamiento del mercado"""
        try:
            patterns = []
            
            if len(features) < self.config['feature_window']:
                return patterns
            
            # Preparar datos para detección de anomalías
            recent_features = features.tail(self.config['feature_window'])
            feature_cols = [col for col in recent_features.columns if not recent_features[col].isna().all()]
            
            if not feature_cols:
                return patterns
            
            X = recent_features[feature_cols].fillna(0)
            
            # Detectar anomalías si el modelo está entrenado
            if hasattr(self.models['anomaly_detector'], 'decision_function'):
                anomaly_scores = self.models['anomaly_detector'].decision_function(X)
                is_anomaly = self.models['anomaly_detector'].predict(X)
                
                # Si la última observación es una anomalía
                if is_anomaly[-1] == -1:
                    anomaly_score = abs(anomaly_scores[-1])
                    
                    # Determinar tipo de anomalía basado en características
                    if 'volume_change' in features.columns and features['volume_change'].iloc[-1] > 2:
                        pattern_type = PatternType.VOLUME_ANOMALY
                    else:
                        pattern_type = PatternType.MOMENTUM_SHIFT
                    
                    pattern = PatternSignal(
                        symbol=symbol,
                        timestamp=datetime.now(),
                        pattern_type=pattern_type,
                        strength=PatternStrength.STRONG,
                        confidence=min(0.9, 0.5 + anomaly_score * 0.1),
                        probability=min(0.9, 0.5 + anomaly_score * 0.1),
                        features={'anomaly_score': anomaly_score},
                        prediction_horizon=10,
                        expected_move=1.5 * np.sign(features['price_change'].iloc[-1]),
                        risk_reward_ratio=1.5
                    )
                    patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            SICAR_LOGGER.log_error("ANOMALY_DETECTION", f"Error en detección de anomalías: {e}")
            return []
    
    def _is_bullish_reversal_pattern(self, features: pd.DataFrame, idx: int) -> bool:
        """Detectar patrón de reversión alcista"""
        try:
            if idx < 4:
                return False
            
            # Condiciones para reversión alcista
            conditions = [
                features.get('rsi_14', pd.Series()).iloc[idx] < 30,  # RSI oversold
                features.get('is_hammer', pd.Series()).iloc[idx] == 1,  # Hammer pattern
                features.get('buy_pressure', pd.Series()).iloc[idx] > 0.7,  # Strong buy pressure
                features.get('volume_ma_ratio', pd.Series()).iloc[idx] > 1.5  # High volume
            ]
            
            return sum(conditions) >= 3
            
        except Exception:
            return False
    
    def _is_bearish_reversal_pattern(self, features: pd.DataFrame, idx: int) -> bool:
        """Detectar patrón de reversión bajista"""
        try:
            if idx < 4:
                return False
            
            # Condiciones para reversión bajista
            conditions = [
                features.get('rsi_14', pd.Series()).iloc[idx] > 70,  # RSI overbought
                features.get('is_shooting_star', pd.Series()).iloc[idx] == 1,  # Shooting star
                features.get('sell_pressure', pd.Series()).iloc[idx] > 0.7,  # Strong sell pressure
                features.get('volume_ma_ratio', pd.Series()).iloc[idx] > 1.5  # High volume
            ]
            
            return sum(conditions) >= 3
            
        except Exception:
            return False
    
    def _is_breakout_preparation_pattern(self, features: pd.DataFrame, idx: int) -> bool:
        """Detectar patrón de preparación para breakout"""
        try:
            if idx < 10:
                return False
            
            # Condiciones para preparación de breakout
            recent_vol = features.get('volatility_5', pd.Series()).iloc[idx-5:idx].mean()
            long_vol = features.get('volatility_20', pd.Series()).iloc[idx]
            
            conditions = [
                recent_vol < long_vol * 0.7,  # Volatilidad comprimida
                features.get('bb_width', pd.Series()).iloc[idx] < 0.02,  # Bandas estrechas
                features.get('volume_ma_ratio', pd.Series()).iloc[idx] > 1.2,  # Volumen creciente
                abs(features.get('price_change', pd.Series()).iloc[idx-5:idx].mean()) < 0.005  # Precio lateral
            ]
            
            return sum(conditions) >= 3
            
        except Exception:
            return False
    
    def _prediction_to_pattern_type(self, prediction: int) -> PatternType:
        """Convertir predicción numérica a tipo de patrón"""
        pattern_map = {
            0: PatternType.BULLISH_REVERSAL,
            1: PatternType.BEARISH_REVERSAL,
            2: PatternType.CONTINUATION_BULLISH,
            3: PatternType.CONTINUATION_BEARISH,
            4: PatternType.CONSOLIDATION,
            5: PatternType.BREAKOUT_PREPARATION
        }
        return pattern_map.get(prediction, PatternType.CONSOLIDATION)
    
    def _confidence_to_strength(self, confidence: float) -> PatternStrength:
        """Convertir confianza a fuerza del patrón"""
        if confidence >= 0.9:
            return PatternStrength.VERY_STRONG
        elif confidence >= 0.8:
            return PatternStrength.STRONG
        elif confidence >= 0.7:
            return PatternStrength.MODERATE
        else:
            return PatternStrength.WEAK
    
    def _estimate_expected_move(self, pattern_type: PatternType, confidence: float) -> float:
        """Estimar movimiento esperado del precio"""
        base_moves = {
            PatternType.BULLISH_REVERSAL: 2.0,
            PatternType.BEARISH_REVERSAL: -2.0,
            PatternType.CONTINUATION_BULLISH: 1.5,
            PatternType.CONTINUATION_BEARISH: -1.5,
            PatternType.BREAKOUT_PREPARATION: 3.0,
            PatternType.VOLUME_ANOMALY: 1.0,
            PatternType.MOMENTUM_SHIFT: 1.5,
            PatternType.CONSOLIDATION: 0.5
        }
        
        base_move = base_moves.get(pattern_type, 1.0)
        return base_move * confidence
    
    def _calculate_risk_reward(self, pattern_type: PatternType, confidence: float) -> float:
        """Calcular ratio riesgo/recompensa"""
        base_ratios = {
            PatternType.BULLISH_REVERSAL: 2.5,
            PatternType.BEARISH_REVERSAL: 2.5,
            PatternType.CONTINUATION_BULLISH: 2.0,
            PatternType.CONTINUATION_BEARISH: 2.0,
            PatternType.BREAKOUT_PREPARATION: 3.0,
            PatternType.VOLUME_ANOMALY: 1.5,
            PatternType.MOMENTUM_SHIFT: 2.0,
            PatternType.CONSOLIDATION: 1.0
        }
        
        base_ratio = base_ratios.get(pattern_type, 1.5)
        return base_ratio * (1 + confidence * 0.5)
    
    def train_models(self, historical_data: Dict[str, pd.DataFrame]):
        """Entrenar modelos con datos históricos"""
        try:
            SICAR_LOGGER.log_alert("MODEL_TRAINING", "Iniciando entrenamiento de modelos", "INFO")
            
            # Preparar datos de entrenamiento
            X_list = []
            y_list = []
            
            for symbol, data in historical_data.items():
                if data is None or data.empty:
                    continue
                
                features = self.extract_advanced_features(data)
                if features.empty:
                    continue
                
                # Crear etiquetas basadas en movimientos futuros
                labels = self._create_labels(data)
                
                # Alinear características y etiquetas
                min_len = min(len(features), len(labels))
                if min_len > self.config['lookback_periods']:
                    X_list.append(features.iloc[-min_len:])
                    y_list.append(labels[-min_len:])
            
            if not X_list:
                SICAR_LOGGER.log_warning("MODEL_TRAINING", "No hay datos suficientes para entrenamiento")
                return False
            
            # Combinar datos
            X = pd.concat(X_list, ignore_index=True)
            y = np.concatenate(y_list)
            
            # Limpiar datos
            X = X.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # Dividir en entrenamiento y prueba
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Escalar características
            X_train_scaled = self.scalers['main'].fit_transform(X_train)
            X_test_scaled = self.scalers['main'].transform(X_test)
            
            # Entrenar clasificador de patrones
            self.models['pattern_classifier'].fit(X_train_scaled, y_train)
            
            # Entrenar detector de anomalías
            self.scalers['anomaly'].fit(X_train)
            X_anomaly = self.scalers['anomaly'].transform(X_train)
            self.models['anomaly_detector'].fit(X_anomaly)
            
            # Evaluar modelo
            train_score = self.models['pattern_classifier'].score(X_train_scaled, y_train)
            test_score = self.models['pattern_classifier'].score(X_test_scaled, y_test)
            
            # Guardar importancia de características
            if hasattr(self.models['pattern_classifier'], 'feature_importances_'):
                self.feature_importance = dict(zip(
                    X.columns, 
                    self.models['pattern_classifier'].feature_importances_
                ))
            
            self.is_trained = True
            
            SICAR_LOGGER.log_alert("MODEL_TRAINING", 
                f"Modelos entrenados - Train: {train_score:.3f}, Test: {test_score:.3f}", "INFO")
            
            return True
            
        except Exception as e:
            SICAR_LOGGER.log_error("MODEL_TRAINING", f"Error entrenando modelos: {e}")
            return False
    
    def _create_labels(self, data: pd.DataFrame) -> np.ndarray:
        """Crear etiquetas para entrenamiento"""
        try:
            labels = []
            
            for i in range(len(data) - 5):  # Predecir 5 períodos adelante
                current_price = data['Close'].iloc[i]
                future_price = data['Close'].iloc[i + 5]
                
                price_change = (future_price - current_price) / current_price
                
                # Clasificar movimiento
                if price_change > 0.02:  # +2%
                    if i > 10 and data['Close'].iloc[i-10:i].mean() > current_price:
                        labels.append(0)  # BULLISH_REVERSAL
                    else:
                        labels.append(2)  # CONTINUATION_BULLISH
                elif price_change < -0.02:  # -2%
                    if i > 10 and data['Close'].iloc[i-10:i].mean() < current_price:
                        labels.append(1)  # BEARISH_REVERSAL
                    else:
                        labels.append(3)  # CONTINUATION_BEARISH
                else:
                    labels.append(4)  # CONSOLIDATION
            
            return np.array(labels)
            
        except Exception as e:
            SICAR_LOGGER.log_error("LABEL_CREATION", f"Error creando etiquetas: {e}")
            return np.array([])
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de patrones detectados"""
        try:
            if not self.pattern_history:
                return {}
            
            # Contar patrones por tipo
            pattern_counts = {}
            for pattern in self.pattern_history:
                pattern_type = pattern.pattern_type.value
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
            
            # Calcular confianza promedio
            avg_confidence = np.mean([p.confidence for p in self.pattern_history])
            
            # Patrones recientes (última hora)
            recent_patterns = [
                p for p in self.pattern_history 
                if (datetime.now() - p.timestamp).seconds < 3600
            ]
            
            return {
                'total_patterns': len(self.pattern_history),
                'pattern_counts': pattern_counts,
                'average_confidence': avg_confidence,
                'recent_patterns': len(recent_patterns),
                'model_trained': self.is_trained,
                'feature_importance': dict(list(self.feature_importance.items())[:10]) if self.feature_importance else {}
            }
            
        except Exception as e:
            SICAR_LOGGER.log_error("PATTERN_STATS", f"Error calculando estadísticas: {e}")
            return {}

# Instancia global del sistema de reconocimiento de patrones
PATTERN_RECOGNITION_SYSTEM = AdvancedPatternRecognition()

def detect_advanced_patterns(data: pd.DataFrame, symbol: str) -> List[PatternSignal]:
    """Función de conveniencia para detectar patrones"""
    return PATTERN_RECOGNITION_SYSTEM.detect_patterns(data, symbol)

def train_pattern_models(historical_data: Dict[str, pd.DataFrame]) -> bool:
    """Función de conveniencia para entrenar modelos"""
    return PATTERN_RECOGNITION_SYSTEM.train_models(historical_data)

def get_pattern_stats() -> Dict[str, Any]:
    """Función de conveniencia para obtener estadísticas"""
    return PATTERN_RECOGNITION_SYSTEM.get_pattern_statistics()