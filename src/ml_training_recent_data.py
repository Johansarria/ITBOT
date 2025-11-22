#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SICAR - Entrenamiento de Modelos ML con Datos Recientes
========================================================

Este módulo entrena modelos de Machine Learning utilizando los datos más recientes
desde la implementación de Grok xAI y OpenAI en el sistema SICAR.

Características:
- Extrae datos de análisis de patrones recientes
- Procesa datos de múltiples timeframes
- Entrena modelos optimizados para multi-timeframe
- Integra características de análisis de IA
- Guarda modelos entrenados para uso en paper trading

Autor: SICAR Team
Fecha: 2025-01-21
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
import joblib
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import re
from pathlib import Path

# Configuración de warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ml_training_recent_data.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importar módulos SICAR
try:
    from binance_data_provider import BinanceDataProvider
    from advanced_ml_engine import AdvancedMLEngine
    from data_pipeline import DataPipeline
except ImportError as e:
    logger.warning(f"Algunos módulos SICAR no están disponibles: {e}")

class RecentDataMLTrainer:
    """
    Entrenador de modelos ML con datos recientes desde implementación de IA
    """
    
    def __init__(self):
        """Inicializar el entrenador"""
        self.project_root = Path(__file__).parent.parent
        self.src_dir = Path(__file__).parent
        self.models_dir = self.project_root / "models"
        self.data_dir = self.project_root / "data"
        
        # Crear directorios si no existen
        self.models_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        # Configuración de símbolos y timeframes
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        self.timeframes = ['1m', '5m', '15m', '1h']
        
        # Inicializar componentes
        self.data_provider = None
        self.ml_engine = None
        self.data_pipeline = None
        
        # Datos procesados
        self.recent_data = {}
        self.training_features = []
        self.training_targets = []
        
        logger.info("✅ RecentDataMLTrainer inicializado")
    
    def initialize_components(self):
        """Inicializar componentes SICAR"""
        try:
            self.data_provider = BinanceDataProvider()
            self.ml_engine = AdvancedMLEngine()
            self.data_pipeline = DataPipeline()
            logger.info("✅ Componentes SICAR inicializados")
            return True
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron inicializar todos los componentes: {e}")
            return False
    
    def extract_recent_pattern_data(self) -> Dict[str, Any]:
        """
        Extrae datos recientes del archivo de análisis de patrones
        """
        logger.info("📊 Extrayendo datos recientes de análisis de patrones...")
        
        pattern_file = self.src_dir / "SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO (1 minuto).txt"
        
        if not pattern_file.exists():
            logger.error(f"❌ Archivo de patrones no encontrado: {pattern_file}")
            return {}
        
        recent_data = {
            'timestamps': [],
            'market_data': [],
            'ai_analyses': [],
            'patterns': [],
            'signals': []
        }
        
        try:
            with open(pattern_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extraer iteraciones recientes (últimas 1000 líneas para datos más recientes)
            lines = content.split('\n')
            recent_lines = lines[-10000:] if len(lines) > 10000 else lines
            
            current_iteration = {}
            in_analysis = False
            analysis_type = None
            
            for line in recent_lines:
                line = line.strip()
                
                # Detectar nueva iteración
                if "Iteración:" in line and "Actualización:" in line:
                    if current_iteration:
                        self._process_iteration_data(current_iteration, recent_data)
                    current_iteration = {
                        'timestamp': self._extract_timestamp(line),
                        'symbols': {},
                        'ai_analysis': {},
                        'market_summary': {}
                    }
                
                # Extraer datos de símbolos
                elif line.startswith("📊") and any(symbol in line for symbol in self.symbols):
                    symbol = self._extract_symbol(line)
                    if symbol:
                        current_iteration['symbols'][symbol] = {}
                
                # Extraer datos de precios y indicadores
                elif "Precio Actual:" in line:
                    price = self._extract_price(line)
                    if price and current_iteration.get('symbols'):
                        last_symbol = list(current_iteration['symbols'].keys())[-1]
                        current_iteration['symbols'][last_symbol]['price'] = price
                
                elif "RSI:" in line:
                    rsi = self._extract_rsi(line)
                    if rsi and current_iteration.get('symbols'):
                        last_symbol = list(current_iteration['symbols'].keys())[-1]
                        current_iteration['symbols'][last_symbol]['rsi'] = rsi
                
                elif "Vol. Ratio:" in line:
                    vol_ratio = self._extract_volume_ratio(line)
                    if vol_ratio and current_iteration.get('symbols'):
                        last_symbol = list(current_iteration['symbols'].keys())[-1]
                        current_iteration['symbols'][last_symbol]['volume_ratio'] = vol_ratio
                
                elif "Confianza:" in line:
                    confidence = self._extract_confidence(line)
                    if confidence and current_iteration.get('symbols'):
                        last_symbol = list(current_iteration['symbols'].keys())[-1]
                        current_iteration['symbols'][last_symbol]['confidence'] = confidence
                
                # Detectar análisis de IA
                elif "🤖 ANÁLISIS OPENAI" in line:
                    in_analysis = True
                    analysis_type = "openai"
                elif "🧠 ANÁLISIS GROK xAI" in line:
                    in_analysis = True
                    analysis_type = "grok"
                elif in_analysis and line and not line.startswith("="):
                    if analysis_type not in current_iteration['ai_analysis']:
                        current_iteration['ai_analysis'][analysis_type] = []
                    current_iteration['ai_analysis'][analysis_type].append(line)
                elif line.startswith("=") and in_analysis:
                    in_analysis = False
                    analysis_type = None
            
            # Procesar última iteración
            if current_iteration:
                self._process_iteration_data(current_iteration, recent_data)
            
            logger.info(f"✅ Extraídos {len(recent_data['timestamps'])} registros de datos recientes")
            return recent_data
            
        except Exception as e:
            logger.error(f"❌ Error extrayendo datos de patrones: {e}")
            return {}
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extrae timestamp de la línea"""
        try:
            # Buscar patrón de fecha: 2025-10-22 06:53:47
            match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if match:
                return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
        except:
            pass
        return None
    
    def _extract_symbol(self, line: str) -> Optional[str]:
        """Extrae símbolo de la línea"""
        for symbol in self.symbols:
            if symbol in line:
                return symbol
        return None
    
    def _extract_price(self, line: str) -> Optional[float]:
        """Extrae precio de la línea"""
        try:
            match = re.search(r'\$([0-9,]+\.?\d*)', line)
            if match:
                return float(match.group(1).replace(',', ''))
        except:
            pass
        return None
    
    def _extract_rsi(self, line: str) -> Optional[float]:
        """Extrae RSI de la línea"""
        try:
            match = re.search(r'RSI:\s*([0-9.]+)', line)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _extract_volume_ratio(self, line: str) -> Optional[float]:
        """Extrae ratio de volumen de la línea"""
        try:
            match = re.search(r'([0-9.]+)x', line)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _extract_confidence(self, line: str) -> Optional[float]:
        """Extrae confianza de la línea"""
        try:
            match = re.search(r'([0-9.]+)%', line)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _process_iteration_data(self, iteration: Dict, recent_data: Dict):
        """Procesa datos de una iteración"""
        if not iteration.get('timestamp'):
            return
        
        recent_data['timestamps'].append(iteration['timestamp'])
        recent_data['market_data'].append(iteration.get('symbols', {}))
        recent_data['ai_analyses'].append(iteration.get('ai_analysis', {}))
    
    def get_binance_historical_data(self, days_back: int = 30) -> Dict[str, pd.DataFrame]:
        """
        Obtiene datos históricos de Binance para complementar el entrenamiento
        """
        logger.info(f"📈 Obteniendo datos históricos de Binance ({days_back} días)...")
        
        historical_data = {}
        
        if not self.data_provider:
            logger.warning("⚠️ Data provider no disponible, usando datos simulados")
            return self._generate_simulated_data(days_back)
        
        try:
            for symbol in self.symbols:
                for timeframe in self.timeframes:
                    try:
                        # Obtener datos históricos
                        df = self.data_provider.get_historical_data(
                            symbol=symbol,
                            interval=timeframe,
                            limit=1000
                        )
                        
                        if df is not None and not df.empty:
                            key = f"{symbol}_{timeframe}"
                            historical_data[key] = df
                            logger.info(f"✅ Datos obtenidos para {key}: {len(df)} registros")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Error obteniendo datos para {symbol}_{timeframe}: {e}")
            
            return historical_data
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos históricos: {e}")
            return self._generate_simulated_data(days_back)
    
    def _generate_simulated_data(self, days_back: int) -> Dict[str, pd.DataFrame]:
        """Genera datos simulados para entrenamiento"""
        logger.info("🔄 Generando datos simulados para entrenamiento...")
        
        simulated_data = {}
        
        # Precios base para cada símbolo
        base_prices = {
            'BTCUSDT': 107000,
            'ETHUSDT': 3800,
            'ADAUSDT': 0.63,
            'DOTUSDT': 2.97,
            'LINKUSDT': 17.36
        }
        
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                # Generar datos simulados
                periods = self._get_periods_for_timeframe(timeframe, days_back)
                dates = pd.date_range(
                    start=datetime.now() - timedelta(days=days_back),
                    periods=periods,
                    freq=self._get_freq_for_timeframe(timeframe)
                )
                
                base_price = base_prices[symbol]
                
                # Generar precios con movimiento aleatorio
                np.random.seed(42)  # Para reproducibilidad
                price_changes = np.random.normal(0, 0.02, periods)
                prices = [base_price]
                
                for change in price_changes[1:]:
                    new_price = prices[-1] * (1 + change)
                    prices.append(new_price)
                
                # Crear DataFrame
                df = pd.DataFrame({
                    'timestamp': dates,
                    'open': prices,
                    'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                    'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                    'close': prices,
                    'volume': np.random.uniform(1000000, 10000000, periods)
                })
                
                # Agregar indicadores técnicos
                df = self._add_technical_indicators(df)
                
                key = f"{symbol}_{timeframe}"
                simulated_data[key] = df
        
        logger.info(f"✅ Datos simulados generados para {len(simulated_data)} pares símbolo-timeframe")
        return simulated_data
    
    def _get_periods_for_timeframe(self, timeframe: str, days: int) -> int:
        """Calcula número de períodos para un timeframe"""
        multipliers = {
            '1m': 24 * 60,
            '5m': 24 * 12,
            '15m': 24 * 4,
            '1h': 24
        }
        return days * multipliers.get(timeframe, 24)
    
    def _get_freq_for_timeframe(self, timeframe: str) -> str:
        """Obtiene frecuencia pandas para timeframe"""
        freq_map = {
            '1m': '1T',
            '5m': '5T',
            '15m': '15T',
            '1h': '1H'
        }
        return freq_map.get(timeframe, '1H')
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Agrega indicadores técnicos al DataFrame"""
        try:
            # RSI
            df['rsi'] = self._calculate_rsi(df['close'])
            
            # MACD
            df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])
            
            # Bollinger Bands
            df['bb_upper'], df['bb_middle'], df['bb_lower'] = self._calculate_bollinger_bands(df['close'])
            
            # Moving Averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            return df
            
        except Exception as e:
            logger.warning(f"⚠️ Error agregando indicadores técnicos: {e}")
            return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Calcula MACD"""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        return macd, signal
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calcula Bollinger Bands"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        return upper, sma, lower
    
    def prepare_training_data(self, historical_data: Dict[str, pd.DataFrame], 
                            recent_data: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepara datos para entrenamiento combinando datos históricos y recientes
        """
        logger.info("🔄 Preparando datos para entrenamiento...")
        
        features = []
        targets = []
        
        # Procesar datos históricos
        for key, df in historical_data.items():
            if df.empty:
                continue
            
            try:
                # Preparar características
                feature_cols = [
                    'rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower',
                    'sma_20', 'ema_12', 'volume_ratio'
                ]
                
                # Filtrar columnas existentes
                available_cols = [col for col in feature_cols if col in df.columns]
                
                if not available_cols:
                    continue
                
                # Extraer características
                df_features = df[available_cols].fillna(0)
                
                # Crear target (movimiento de precio futuro)
                df['future_return'] = df['close'].pct_change(periods=5).shift(-5)
                df['target'] = (df['future_return'] > 0.01).astype(int)  # 1% threshold
                
                # Eliminar filas con NaN
                valid_rows = ~(df_features.isna().any(axis=1) | df['target'].isna())
                
                if valid_rows.sum() > 0:
                    features.extend(df_features[valid_rows].values.tolist())
                    targets.extend(df['target'][valid_rows].values.tolist())
                
            except Exception as e:
                logger.warning(f"⚠️ Error procesando {key}: {e}")
        
        # Procesar datos recientes de análisis de patrones
        self._add_recent_pattern_features(recent_data, features, targets)
        
        if not features:
            logger.error("❌ No se pudieron preparar características para entrenamiento")
            return np.array([]), np.array([])
        
        features_array = np.array(features)
        targets_array = np.array(targets)
        
        logger.info(f"✅ Datos preparados: {features_array.shape[0]} muestras, {features_array.shape[1]} características")
        
        return features_array, targets_array
    
    def _add_recent_pattern_features(self, recent_data: Dict[str, Any], 
                                   features: List, targets: List):
        """Agrega características de datos recientes de patrones"""
        try:
            if not recent_data.get('market_data'):
                return
            
            for i, market_snapshot in enumerate(recent_data['market_data']):
                for symbol, data in market_snapshot.items():
                    if symbol in self.symbols:
                        # Extraer características disponibles
                        feature_row = [
                            data.get('rsi', 50),
                            data.get('volume_ratio', 1.0),
                            data.get('confidence', 50),
                            # Agregar más características según disponibilidad
                            1 if data.get('confidence', 0) > 70 else 0,  # High confidence signal
                            1 if data.get('rsi', 50) < 30 else 0,  # Oversold
                            1 if data.get('rsi', 50) > 70 else 0,  # Overbought
                            data.get('volume_ratio', 1.0) if data.get('volume_ratio', 1.0) > 2 else 0,  # High volume
                        ]
                        
                        # Pad to match expected feature count
                        while len(feature_row) < 9:  # Match historical data features
                            feature_row.append(0)
                        
                        features.append(feature_row[:9])  # Limit to expected size
                        
                        # Target basado en confianza (simplificado)
                        target = 1 if data.get('confidence', 0) > 60 else 0
                        targets.append(target)
            
        except Exception as e:
            logger.warning(f"⚠️ Error agregando características de patrones recientes: {e}")
    
    def train_models(self, features: np.ndarray, targets: np.ndarray) -> Dict[str, Any]:
        """
        Entrena múltiples modelos ML con los datos preparados
        """
        logger.info("🤖 Entrenando modelos de Machine Learning...")
        
        if features.size == 0 or targets.size == 0:
            logger.error("❌ No hay datos para entrenar")
            return {}
        
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.svm import SVC
        from sklearn.metrics import accuracy_score, classification_report
        from sklearn.preprocessing import StandardScaler
        
        # Dividir datos
        X_train, X_test, y_train, y_test = train_test_split(
            features, targets, test_size=0.2, random_state=42, stratify=targets
        )
        
        # Escalar características
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        models = {}
        
        # Random Forest
        logger.info("🌲 Entrenando Random Forest...")
        rf_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(X_train_scaled, y_train)
        rf_pred = rf_model.predict(X_test_scaled)
        rf_accuracy = accuracy_score(y_test, rf_pred)
        
        models['random_forest'] = {
            'model': rf_model,
            'scaler': scaler,
            'accuracy': rf_accuracy,
            'predictions': rf_pred
        }
        
        # Gradient Boosting
        logger.info("🚀 Entrenando Gradient Boosting...")
        gb_model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42
        )
        gb_model.fit(X_train_scaled, y_train)
        gb_pred = gb_model.predict(X_test_scaled)
        gb_accuracy = accuracy_score(y_test, gb_pred)
        
        models['gradient_boosting'] = {
            'model': gb_model,
            'scaler': scaler,
            'accuracy': gb_accuracy,
            'predictions': gb_pred
        }
        
        # Logistic Regression
        logger.info("📈 Entrenando Logistic Regression...")
        lr_model = LogisticRegression(random_state=42, max_iter=1000)
        lr_model.fit(X_train_scaled, y_train)
        lr_pred = lr_model.predict(X_test_scaled)
        lr_accuracy = accuracy_score(y_test, lr_pred)
        
        models['logistic_regression'] = {
            'model': lr_model,
            'scaler': scaler,
            'accuracy': lr_accuracy,
            'predictions': lr_pred
        }
        
        # Mostrar resultados
        logger.info("📊 Resultados del entrenamiento:")
        for name, model_info in models.items():
            logger.info(f"  {name}: {model_info['accuracy']:.4f}")
        
        # Seleccionar mejor modelo
        best_model_name = max(models.keys(), key=lambda k: models[k]['accuracy'])
        logger.info(f"🏆 Mejor modelo: {best_model_name} ({models[best_model_name]['accuracy']:.4f})")
        
        return models
    
    def save_trained_models(self, models: Dict[str, Any]):
        """Guarda los modelos entrenados"""
        logger.info("💾 Guardando modelos entrenados...")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for name, model_info in models.items():
            try:
                # Guardar modelo
                model_path = self.models_dir / f"multi_timeframe_{name}_{timestamp}.joblib"
                joblib.dump({
                    'model': model_info['model'],
                    'scaler': model_info['scaler'],
                    'accuracy': model_info['accuracy'],
                    'timestamp': timestamp,
                    'features_count': model_info['model'].n_features_in_ if hasattr(model_info['model'], 'n_features_in_') else 'unknown'
                }, model_path)
                
                logger.info(f"✅ Modelo guardado: {model_path}")
                
            except Exception as e:
                logger.error(f"❌ Error guardando modelo {name}: {e}")
        
        # Guardar metadatos
        metadata = {
            'training_timestamp': timestamp,
            'models_trained': list(models.keys()),
            'best_model': max(models.keys(), key=lambda k: models[k]['accuracy']),
            'accuracies': {name: info['accuracy'] for name, info in models.items()},
            'symbols': self.symbols,
            'timeframes': self.timeframes
        }
        
        metadata_path = self.models_dir / f"multi_timeframe_metadata_{timestamp}.json"
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ Metadatos guardados: {metadata_path}")
    
    def run_training_pipeline(self):
        """Ejecuta el pipeline completo de entrenamiento"""
        logger.info("🚀 Iniciando pipeline de entrenamiento con datos recientes...")
        
        try:
            # 1. Inicializar componentes
            components_ok = self.initialize_components()
            
            # 2. Extraer datos recientes de patrones
            recent_data = self.extract_recent_pattern_data()
            
            # 3. Obtener datos históricos
            historical_data = self.get_binance_historical_data(days_back=30)
            
            # 4. Preparar datos para entrenamiento
            features, targets = self.prepare_training_data(historical_data, recent_data)
            
            if features.size == 0:
                logger.error("❌ No se pudieron preparar datos para entrenamiento")
                return False
            
            # 5. Entrenar modelos
            models = self.train_models(features, targets)
            
            if not models:
                logger.error("❌ No se pudieron entrenar modelos")
                return False
            
            # 6. Guardar modelos
            self.save_trained_models(models)
            
            logger.info("✅ Pipeline de entrenamiento completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en pipeline de entrenamiento: {e}")
            return False

def main():
    """Función principal"""
    logger.info("=" * 80)
    logger.info("🤖 SICAR - Entrenamiento ML con Datos Recientes")
    logger.info("=" * 80)
    
    trainer = RecentDataMLTrainer()
    success = trainer.run_training_pipeline()
    
    if success:
        logger.info("🎉 Entrenamiento completado exitosamente")
    else:
        logger.error("💥 Error en el entrenamiento")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    main()