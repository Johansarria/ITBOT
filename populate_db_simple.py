#!/usr/bin/env python3
"""
Script simplificado para cargar datos históricos en PostgreSQL
Sin dependencias de MLflow
"""

import os
import sys
import pandas as pd
import logging
from pathlib import Path

# Añadir el directorio raíz al sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import add_klines

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_csv_to_db(symbol: str, interval: str = "1h"):
    """Cargar datos desde CSV a PostgreSQL"""
    
    # Buscar archivo CSV
    csv_pattern = f"historical_klines_{symbol}_{interval}_*.csv"
    data_dir = Path("data/analisis")
    
    csv_files = list(data_dir.glob(csv_pattern))
    
    if not csv_files:
        logger.error(f"No se encontró archivo CSV para {symbol}-{interval}")
        return False
    
    csv_file = csv_files[0]
    logger.info(f"Cargando archivo: {csv_file}")
    
    try:
        # Leer CSV
        df = pd.read_csv(csv_file)
        logger.info(f"CSV leído: {len(df)} registros")
        
        # Verificar columnas requeridas
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"Columnas faltantes en CSV. Requeridas: {required_columns}")
            return False
        
        # Convertir timestamp si es necesario
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Cargar a BD en lotes
        batch_size = 1000
        total_records = len(df)
        
        for i in range(0, total_records, batch_size):
            batch_df = df.iloc[i:i + batch_size]
            
            try:
                # Usar add_klines con DataFrame
                add_klines(
                    klines_df=batch_df,
                    symbol=symbol,
                    interval=interval
                )
                logger.info(f"Lote {i//batch_size + 1}: {len(batch_df)} registros cargados")
            except Exception as e:
                logger.error(f"Error en lote {i//batch_size + 1}: {e}")
                continue
        
        logger.info(f"✅ Carga completada para {symbol}-{interval}: {total_records} registros")
        return True
        
    except Exception as e:
        logger.error(f"Error procesando {csv_file}: {e}")
        return False

def main():
    """Cargar datos para múltiples symbols"""
    
    symbols = [
        "BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", 
        "USDCUSDT", "FDUSDUSDT", "BNBUSDT", "XRPUSDT"
    ]
    
    interval = "1h"
    
    logger.info("🚀 Iniciando carga de datos históricos a PostgreSQL")
    
    success_count = 0
    
    for symbol in symbols:
        logger.info(f"📊 Procesando {symbol}")
        
        if load_csv_to_db(symbol, interval):
            success_count += 1
            logger.info(f"✅ {symbol} completado")
        else:
            logger.error(f"❌ {symbol} falló")
    
    logger.info(f"📈 Resumen: {success_count}/{len(symbols)} símbolos cargados exitosamente")

if __name__ == "__main__":
    main()
