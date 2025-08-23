# utils/feature_pipeline.py

import pandas as pd
import logging
from typing import Optional

# Importar las funciones de feature engineering existentes
from utils.feature_engineering import enrich_features
from utils.technical_analysis import calculate_all_indicators

logger = logging.getLogger(__name__)

class FeaturePipeline:
    """
    Encapsula el pipeline de feature engineering para generar features a partir de klines.
    Asegura la consistencia en la generación de features para entrenamiento e inferencia.
    """
    def __init__(self):
        logger.info("FeaturePipeline inicializado.")

    def transform(self, df_klines: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica todas las transformaciones de feature engineering a un DataFrame de klines.

        Args:
            df_klines (pd.DataFrame): DataFrame de klines con columnas OHLCV.

        Returns:
            pd.DataFrame: DataFrame con las features calculadas.
        """
        if df_klines.empty:
            logger.warning("DataFrame de klines vacío proporcionado al FeaturePipeline. Devolviendo DataFrame vacío.")
            return pd.DataFrame()

        df_processed = df_klines.copy()

        # 1. Enriquecer con features avanzados (de utils.feature_engineering)
        logger.debug("Aplicando enriquecimiento de features avanzados.")
        df_processed = enrich_features(df_processed)

        # 2. Calcular indicadores técnicos clásicos (de utils.technical_analysis)
        logger.debug("Calculando indicadores técnicos clásicos.")
        df_processed = calculate_all_indicators(df_processed)

        logger.info("Generación de features completada por FeaturePipeline.")
        return df_processed

# Ejemplo de uso (para pruebas o demostración)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Crear un DataFrame de klines de ejemplo
    data = {
        'open': [100, 102, 105, 103, 106, 108, 110, 109, 112, 115],
        'high': [103, 106, 107, 105, 108, 110, 112, 111, 114, 117],
        'low': [99, 101, 103, 102, 104, 106, 108, 107, 110, 113],
        'close': [102, 105, 103, 106, 108, 110, 109, 112, 115, 114],
        'volume': [1000, 1200, 1100, 1300, 1050, 1150, 1250, 1000, 1350, 1200],
        'open_time': pd.to_datetime(pd.date_range(start='2023-01-01', periods=10, freq='H'))
    }
    df_sample_klines = pd.DataFrame(data)
    df_sample_klines.set_index('open_time', inplace=True)

    pipeline = FeaturePipeline()
    df_features = pipeline.transform(df_sample_klines)

    print("\n--- Features Generadas ---")
    print(df_features.head())
    print(f"Columnas generadas: {df_features.columns.tolist()}")
