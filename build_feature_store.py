# build_feature_store.py

import os
import pandas as pd
import logging
import sys

# Añadir el directorio raíz al sys.path para poder importar los módulos del proyecto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import get_klines # Importar la función para obtener klines de la BD
from utils.feature_pipeline import FeaturePipeline

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

    # 3. Aplicar el pipeline de feature engineering
    logger.info("Iniciando aplicación del FeaturePipeline...")
    feature_pipeline = FeaturePipeline()
    df_final = feature_pipeline.transform(df)
    logger.info("Aplicación del FeaturePipeline completada.")

    # 5. Guardar en formato Parquet
    try:
        logger.info(f"Guardando feature store en: {OUTPUT_PATH}")
        df_final.to_parquet(OUTPUT_PATH, engine='pyarrow')
        logger.info("Feature Store guardado exitosamente en formato Parquet.")
    except Exception as e:
        logger.error(f"Error al guardar el archivo Parquet: {e}", exc_info=True)
        logger.warning("Asegúrate de tener 'pyarrow' instalado: pip install pyarrow")

import mlflow

def main():
    # Ejemplo de uso: Construir el feature store para BTCUSDT en 1h
    symbol_to_build = "BTCUSDT"
    interval_to_build = "1h"
    
    # Import the module explicitly and call the function from the module object. This
    # ensures that when tests patch `build_feature_store.build_and_save_feature_store`
    # the patched function is used even if the module is executed under the name
    # "__main__" (for example via runpy.run_module).
    import importlib
    mod = importlib.import_module('build_feature_store')

    with mlflow.start_run(run_name=f"Feature Engineering - {symbol_to_build}-{interval_to_build}"):
        mlflow.log_param("symbol", symbol_to_build)
        mlflow.log_param("interval", interval_to_build)

        # Call the function from the imported module so tests that patch the
        # function on the module object will intercept this call.
        mod.build_and_save_feature_store(symbol=symbol_to_build, interval=interval_to_build)

        # Log the generated feature store as an artifact
        try:
            mlflow.log_artifact(mod.OUTPUT_PATH, artifact_path="feature_store")
        except Exception:
            # If artifact path is not present or logging fails, keep behavior
            # simple and continue (tests assert that log_artifact is called).
            logger.exception("Fallo al loggear el artifact del feature store")

if __name__ == "__main__":
    main()