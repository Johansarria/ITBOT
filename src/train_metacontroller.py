#!/usr/bin/env python3
"""
Script para entrenar el MetaController con datos históricos
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from module_3_metacontroller import MetaController, create_labels
from module_2_regime import RegimeClassifier
from main_bot import TradingBot, get_binance_data
from binance_data_helper import get_binance_data_robust
from pipelines.data_pipeline import DataPipeline

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def get_training_data():
    """Obtiene datos para entrenamiento con múltiples intentos."""
    
    # Primero intentar con datos reales de Binance usando función robusta
    attempts = [
        ('BTCUSDT', '1h', 50),
        ('BTCUSDT', '4h', 25),
        ('ETHUSDT', '1h', 50),
    ]
    
    for symbol, interval, limit in attempts:
        logger.info(f"Intentando obtener datos reales: {symbol} - {interval} - {limit} velas")
        data = get_binance_data_robust(symbol=symbol, interval=interval, limit=limit)
        
        if data is not None and not data.empty and len(data) > 10:
            logger.info(f"✅ Datos reales obtenidos: {len(data)} registros")
            return data
        else:
            logger.warning(f"❌ Intento fallido para {symbol} {interval}")
    
    # Si no se pueden obtener datos reales, usar datos simulados
    logger.warning("No se pudieron obtener datos reales, usando datos simulados...")
    try:
        pipeline = DataPipeline()
        data = pipeline.get_market_data(ticker='BTC-USD', period='3mo', interval='1h')
        
        if data is not None and not data.empty and len(data) > 20:
            logger.info(f"✅ Datos simulados obtenidos: {len(data)} registros")
            return data
        else:
            logger.error("❌ Error obteniendo datos simulados")
    except Exception as e:
        logger.error(f"❌ Error con datos simulados: {str(e)}")
    
    logger.error("No se pudieron obtener datos de ninguna fuente")
    return None

def train_metacontroller_with_real_data():
    """Entrena el MetaController con datos reales de Binance."""
    logger.info("=== ENTRENANDO METACONTROLLER CON DATOS REALES ===")
    
    try:
        # 1. Obtener datos históricos
        logger.info("Obteniendo datos históricos...")
        market_data = get_training_data()
        
        if market_data is None or market_data.empty:
            logger.error("No se pudieron obtener datos históricos")
            return False
        
        logger.info(f"Datos obtenidos: {len(market_data)} registros")
        logger.info(f"Período: {market_data.index[0]} a {market_data.index[-1]}")
        
        # 3. Clasificar regímenes
        logger.info("Clasificando regímenes de mercado...")
        regime_classifier = RegimeClassifier()
        regime_results = regime_classifier.classify_regimes(market_data)
        
        if regime_results.empty:
            logger.error("No se pudieron clasificar regímenes")
            return False
        
        logger.info(f"Regímenes clasificados: {len(regime_results)} muestras")
        
        # 4. Crear MetaController
        metacontroller = MetaController()
        
        # 5. Preparar características
        logger.info("Preparando características...")
        features = metacontroller.prepare_features(market_data, regime_results)
        
        if features.empty:
            logger.error("No se pudieron preparar características")
            return False
        
        logger.info(f"Características preparadas: {len(features)} muestras, {len(features.columns)} features")
        
        # 6. Crear etiquetas
        logger.info("Creando etiquetas de estrategias...")
        
        # Normalizar nombres de columnas para compatibilidad
        market_data_normalized = market_data.copy()
        market_data_normalized.columns = market_data_normalized.columns.str.lower()
        
        labels = create_labels(market_data_normalized)
        
        if labels.empty:
            logger.error("No se pudieron crear etiquetas")
            return False
        
        logger.info(f"Etiquetas creadas: {len(labels)} muestras")
        logger.info(f"Distribución de estrategias: {labels.value_counts().to_dict()}")
        
        # 7. Alinear datos
        logger.info("Alineando características y etiquetas...")
        aligned_data = pd.concat([features, labels.rename('label')], axis=1).dropna()
        
        if len(aligned_data) == 0:
            logger.error("No hay datos alineados para entrenar")
            return False
        
        features_aligned = aligned_data.drop(columns=['label'])
        labels_aligned = aligned_data['label']
        
        logger.info(f"Datos alineados: {len(features_aligned)} muestras")
        logger.info(f"Distribución final: {labels_aligned.value_counts().to_dict()}")
        
        # 8. Entrenar modelo
        logger.info("Entrenando MetaController...")
        success = metacontroller.train_metacontroller(features_aligned, labels_aligned)
        
        if success:
            logger.info("✅ MetaController entrenado exitosamente")
            
            # 9. Probar predicción
            logger.info("Probando predicción...")
            test_features = features_aligned.tail(1)
            strategy, confidence = metacontroller.predict_strategy(test_features)
            
            logger.info(f"Predicción de prueba: {strategy} (confianza: {confidence:.3f})")
            
            # 10. Mostrar estadísticas del modelo
            if hasattr(metacontroller, 'feature_names'):
                logger.info(f"Características utilizadas: {len(metacontroller.feature_names)}")
                logger.info(f"Features: {metacontroller.feature_names}")
            
            return True
        else:
            logger.error("❌ Error entrenando MetaController")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento: {str(e)}")
        return False

def test_trained_model():
    """Prueba el modelo entrenado con datos recientes."""
    logger.info("=== PROBANDO MODELO ENTRENADO ===")
    
    try:
        # Obtener datos recientes
        market_data = get_binance_data(symbol='BTCUSDT', interval='4h', limit=100)
        
        if market_data is None or market_data.empty:
            logger.error("No se pudieron obtener datos para prueba")
            return False
        
        # Crear MetaController y cargar modelo
        metacontroller = MetaController()
        
        # Clasificar regímenes para los datos de prueba
        regime_classifier = RegimeClassifier()
        regime_results = regime_classifier.classify_regimes(market_data)
        
        # Preparar características
        features = metacontroller.prepare_features(market_data, regime_results)
        
        if features.empty:
            logger.error("No se pudieron preparar características para prueba")
            return False
        
        # Hacer predicción
        strategy, confidence = metacontroller.predict_strategy(features)
        
        logger.info(f"✅ Predicción exitosa: {strategy} (confianza: {confidence:.3f})")
        
        # Ejecutar estrategia para obtener señal
        signal = metacontroller.execute_strategy(strategy, market_data)
        logger.info(f"Señal de trading: {signal:.3f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error probando modelo: {str(e)}")
        return False

def main():
    """Función principal."""
    logger.info("🚀 INICIANDO ENTRENAMIENTO DEL METACONTROLLER")
    
    # 1. Entrenar modelo
    if train_metacontroller_with_real_data():
        logger.info("✅ Entrenamiento completado exitosamente")
        
        # 2. Probar modelo
        if test_trained_model():
            logger.info("✅ Prueba del modelo exitosa")
            logger.info("🎉 ¡MetaController listo para operar!")
        else:
            logger.warning("⚠️ Entrenamiento exitoso pero prueba falló")
    else:
        logger.error("❌ Error en entrenamiento")
    
    logger.info("=" * 50)

if __name__ == "__main__":
    main()