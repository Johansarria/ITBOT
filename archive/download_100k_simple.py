#!/usr/bin/env python3
"""
Script Simplificado de Descarga de 100K Datos Históricos
Basado en download_historical_data.py que funciona correctamente
"""

import asyncio
import pandas as pd
import os
from binance.exceptions import BinanceAPIException
import logging
from datetime import datetime

from utils.binance_client import get_binance_client
from utils.logger_setup import setup_logging
from database.database_manager import add_klines

setup_logging()
logger = logging.getLogger(__name__)

async def download_100k_historical_data():
    """
    Descargar aproximadamente 100K datos históricos usando el script que funciona
    """
    logger.info("🚀 INICIANDO DESCARGA DE ~100K DATOS HISTÓRICOS")
    
    # Parámetros de descarga - aproximadamente 100K horas = 11.4 años
    symbol = "BTCUSDT" 
    interval = "1h"
    # Desde enero 2014 hasta ahora debería darnos cerca de 100K registros
    start_str = "1 Jan, 2014"
    end_str = None  # Hasta ahora
    
    output_path = "data/100k_historical/"
    file_prefix = "btcusdt_100k"
    
    # Crear directorio
    os.makedirs(output_path, exist_ok=True)
    
    file_name = f"{output_path}{file_prefix}_{symbol}_{interval}_{start_str.replace(' ','_').replace(',','')}_now.csv"
    
    logger.info(f"📊 Símbolo: {symbol}")
    logger.info(f"📊 Intervalo: {interval}")  
    logger.info(f"📅 Desde: {start_str} hasta: ahora")
    logger.info(f"💾 Archivo: {file_name}")

    try:
        # Usar el cliente asíncrono correctamente
        client_instance = await get_binance_client()
        
        logger.info("📥 Descargando datos históricos...")
        # El AsyncClient tiene métodos asíncronos que necesitan await
        klines = await client_instance.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_str,
            end_str=end_str
        )
        
        if not klines:
            logger.error("❌ No se obtuvieron datos de la API")
            return False
        
        logger.info(f"📊 Procesando {len(klines)} registros...")
        
        # Procesar datos
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
        ])
        
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric)
        
        # Validaciones
        if df.empty:
            logger.warning("⚠️ DataFrame vacío después del procesamiento")
            return False

        required_cols = ["open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required_cols):
            logger.error(f"❌ Faltan columnas requeridas: {required_cols}")
            return False

        # Validación de consistencia de precios
        if not ((df["low"] <= df["open"]) & (df["open"] <= df["high"]) & 
                (df["low"] <= df["close"]) & (df["close"] <= df["high"])).all():
            logger.warning("⚠️ Inconsistencias detectadas en precios")

        # Limitar a 100K registros si tenemos más
        if len(df) > 100000:
            df = df.tail(100000)
            logger.info(f"✂️ Datos limitados a 100,000 registros más recientes")

        logger.info("💾 Guardando datos en CSV...")
        df.to_csv(file_name)
        logger.info(f"✅ CSV guardado: {file_name}")

        # Guardar en base de datos
        try:
            logger.info("💾 Guardando en base de datos...")
            df_to_db = df.copy()
            df_to_db["timestamp"] = df_to_db.index.astype(int) // 10**6
            df_to_db["close_time"] = df_to_db["close_time"].astype(int)
            add_klines(df_to_db, symbol, interval)
            logger.info("✅ Datos guardados en base de datos")
        except Exception as e:
            logger.warning(f"⚠️ Error guardando en BD: {e}")

        # Estadísticas finales
        logger.info("="*60)
        logger.info("🎉 DESCARGA COMPLETADA")
        logger.info(f"📊 Total de registros: {len(df):,}")
        logger.info(f"📅 Período: {df.index[0]} a {df.index[-1]}")
        logger.info(f"💾 Archivo: {file_name}")
        
        # Verificar si alcanzamos cerca de 100K
        if len(df) >= 90000:
            logger.info(f"🎯 ¡Excelente! Obtenidos {len(df):,} registros (~100K objetivo)")
        else:
            logger.info(f"📊 Obtenidos {len(df):,} registros (disponibles en el período)")
        
        logger.info("="*60)
        
        return True

    except BinanceAPIException as e:
        logger.error(f"❌ Error de API Binance: {e}")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}", exc_info=True)
    
    return False

async def main():
    """Función principal"""
    success = await download_100k_historical_data()
    
    if success:
        logger.info("🚀 Sistema listo para operar con datos históricos masivos")
        logger.info("💡 Puedes entrenar el modelo ML con estos datos usando train_pipeline.py")
    else:
        logger.error("❌ Error en la descarga de datos históricos")

if __name__ == "__main__":
    asyncio.run(main())
