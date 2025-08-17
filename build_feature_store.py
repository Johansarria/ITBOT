# build_feature_store.py

import os
import pandas as pd
import logging
import sys

# Añadir el directorio raíz al sys.path para poder importar los módulos del proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.feature_engineering import enrich_features
from utils.technical_analysis import calculate_all_indicators
from database.database_manager import get_klines # Importar la función para obtener klines de la BD

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Definición de rutas
DATA_DIR = "data"
FEATURE_STORE_DIR = os.path.join(DATA_DIR, "features")
OUTPUT_PATH = os.path.join(FEATURE_STORE_DIR, "klines_enriched.parquet")

def build_and_save_feature_store(symbol: str = "BTCUSDT", interval: str = "4h"):
    """
    Carga los datos históricos desde la BD, calcula todos los indicadores y features,
    y guarda el resultado en un archivo Parquet.
    """
    logger.info(f"Iniciando la construcción del Feature Store para {symbol}-{interval}.")

    # 1. Crear directorio de salida si no existe
    os.makedirs(FEATURE_STORE_DIR, exist_ok=True)
    logger.info(f"Directorio de features asegurado en: {FEATURE_STORE_DIR}")

    # 2. Cargar datos fuente desde la base de datos
    try:
        logger.info(f"Cargando datos desde la base de datos para {symbol}-{interval}.")
        df = get_klines(symbol=symbol, interval=interval)
        
        if df.empty:
            logger.error(f"Error: No se encontraron datos de klines para {symbol}-{interval} en la base de datos.")
            return
        logger.info(f"Datos cargados exitosamente. {len(df)} filas.")
    except Exception as e:
        logger.error(f"Error al cargar datos de klines desde la base de datos: {e}", exc_info=True)
        return

    # 3. Enriquecer con features
    logger.info("Iniciando enriquecimiento de features...")
    df_enriched = enrich_features(df.copy())
    logger.info("Enriquecimiento de features completado.")

    # 4. Calcular indicadores técnicos clásicos
    logger.info("Iniciando cálculo de indicadores técnicos...")
    df_final = calculate_all_indicators(df_enriched)
    logger.info("Cálculo de indicadores técnicos completado.")

    # 5. Guardar en formato Parquet
    try:
        logger.info(f"Guardando feature store en: {OUTPUT_PATH}")
        df_final.to_parquet(OUTPUT_PATH, engine='pyarrow')
        logger.info("Feature Store guardado exitosamente en formato Parquet.")
    except Exception as e:
        logger.error(f"Error al guardar el archivo Parquet: {e}", exc_info=True)
        logger.warning("Asegúrate de tener 'pyarrow' instalado: pip install pyarrow")

if __name__ == "__main__":
    # Ejemplo de uso: Construir el feature store para BTCUSDT en 1h
    build_and_save_feature_store(symbol="BTCUSDT", interval="1h")
