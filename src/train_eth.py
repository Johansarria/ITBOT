#!/usr/bin/env python3
"""
Script simple para entrenar modelos SICAR para ETH/USDT
"""

import logging
import pandas as pd
from pipelines.data_pipeline import DataPipeline
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_eth_models():
    """Entrena modelos SICAR para ETH/USDT."""
    try:
        logger.info("=== ENTRENANDO MODELOS PARA ETH/USDT ===")
        
        # 1. Obtener datos
        logger.info("Obteniendo datos de ETH/USDT...")
        data_pipeline = DataPipeline()
        market_data = data_pipeline.get_market_data('ETHUSDT', period='2y', interval='4h')
        
        if market_data.empty:
            logger.error("No se pudieron obtener datos")
            return False
        
        logger.info(f"Datos obtenidos: {len(market_data)} registros")
        logger.info(f"Columnas: {list(market_data.columns)}")
        logger.info(f"Índice: {type(market_data.index)}")
        logger.info(f"Primeras fechas: {market_data.index[:5]}")
        
        # 2. Entrenar Regime Classifier
        logger.info("Entrenando Regime Classifier...")
        regime_classifier = RegimeClassifier()
        
        # Usar solo los últimos 1000 registros para evitar problemas
        train_data = market_data.tail(1000).copy()
        logger.info(f"Datos de entrenamiento: {len(train_data)} registros")
        
        regime_results = regime_classifier.classify_regimes(train_data)
        
        if regime_results.empty:
            logger.error("Error clasificando regímenes")
            return False
        
        logger.info(f"Regímenes clasificados: {len(regime_results)} muestras")
        
        # 3. Entrenar MetaController
        logger.info("Entrenando MetaController...")
        metacontroller = MetaController()
        
        # Preparar características
        features = metacontroller.prepare_features(train_data, regime_results)
        
        if features.empty:
            logger.error("Error preparando características")
            return False
        
        logger.info(f"Características preparadas: {len(features)} muestras")
        
        # Crear etiquetas
        from module_3_metacontroller import create_labels
        labels = create_labels(train_data)
        
        if labels.empty:
            logger.error("Error creando etiquetas")
            return False
        
        logger.info(f"Etiquetas creadas: {len(labels)} muestras")
        
        # Alinear datos
        aligned_data = pd.concat([features, labels.rename('label')], axis=1).dropna()
        
        if len(aligned_data) == 0:
            logger.error("No hay datos alineados")
            return False
        
        features_aligned = aligned_data.drop(columns=['label'])
        labels_aligned = aligned_data['label']
        
        logger.info(f"Datos alineados: {len(features_aligned)} muestras")
        
        # Entrenar
        success = metacontroller.train_metacontroller(features_aligned, labels_aligned)
        
        if success:
            logger.info("✅ Modelos entrenados exitosamente para ETH/USDT")
            return True
        else:
            logger.error("❌ Error entrenando MetaController")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error en entrenamiento: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    train_eth_models()