# download_historical_data.py

import asyncio
import pandas as pd
import os
from binance.exceptions import BinanceAPIException
import logging
from datetime import datetime, timezone

import zoneinfo

from utils.binance_client import get_binance_client # Importar la función para obtener el cliente de Binance
from utils.logger_setup import setup_logging
from database.database_manager import add_klines # Importar la función para añadir klines a la BD

setup_logging() # Configurar logging para este script
logger = logging.getLogger(__name__)

async def download_and_save_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    start_str: str = "1 Jan, 2023",
    end_str: str = None,
    output_path: str = "data/analisis/",
    file_prefix: str = "historical_klines",
    append_to_existing: bool = False # Nuevo parámetro
):
    """
    Descarga klines históricos de Binance y los guarda en un archivo CSV y en la base de datos.

    :param symbol: Símbolo del par de trading (ej. "BTCUSDT").
    :param interval: Intervalo de los klines (ej. "1h", "4h", "1d").
    :param start_str: Fecha de inicio en formato legible (ej. "1 Jan, 2023").
    :param end_str: Fecha de fin en formato legible (ej. "1 Jan, 2024"). Si es None, hasta ahora.
    :param output_path: Ruta del directorio donde se guardará el CSV.
    :param file_prefix: Prefijo para el nombre del archivo CSV.
    :param append_to_existing: Si es True, intenta añadir nuevos datos al final del archivo existente.
    """
    file_name = f"{output_path}{file_prefix}_{symbol}_{interval}_{start_str.replace(' ','_').replace(',','')}_{end_str.replace(' ','_').replace(',','') if end_str else 'now'}.csv"
    
    current_start_str = start_str
    if append_to_existing and os.path.exists(file_name):
        try:
            existing_df = pd.read_csv(file_name, index_col="timestamp", parse_dates=True)
            if not existing_df.empty:
                last_timestamp = existing_df.index.max()
                # Asegurarse de que el nuevo start_str sea la siguiente vela después de la última existente
                # Esto es una aproximación, idealmente se calcularía la duración del intervalo
                # Para 1h, sería last_timestamp + timedelta(hours=1)
                # Para 4h, sería last_timestamp + timedelta(hours=4)
                # Para simplificar, usaremos el timestamp de la última vela + 1ms para evitar duplicados
                current_start_str = (last_timestamp + pd.Timedelta(milliseconds=1)).strftime("%d %b, %Y %H:%M:%S")
                logger.info(f"Archivo existente encontrado. Descargando datos desde: {current_start_str}")
            else:
                logger.info("Archivo existente vacío. Descargando desde el inicio especificado.")
        except Exception as e:
            logger.warning(f"Error al leer archivo existente {file_name}: {e}. Descargando todos los datos.")
            append_to_existing = False # Desactivar append si hay error al leer

    logger.info(f"Iniciando descarga de datos históricos para {symbol} - {interval} desde {current_start_str} hasta {end_str if end_str else 'ahora'}.")

    try:
        client_instance = await get_binance_client()
        klines = await client_instance.get_historical_klines(
                                        symbol=symbol,
                                        interval=interval,
                                        start_str=current_start_str, # Usar el start_str ajustado
                                        end_str=end_str)
        
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric)
        
        # --- Validaciones de datos ---
        if df.empty:
            logger.warning(f"No se descargaron datos nuevos para {symbol} - {interval}. No se guardará el archivo.")
            return pd.DataFrame()

        required_cols = ["open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required_cols):
            logger.error(f"Faltan columnas requeridas en los datos de {symbol} - {interval}. Columnas esperadas: {required_cols}")
            return pd.DataFrame()

        # Basic data consistency check: low <= open, close <= high
        # This is a simplified check; more robust checks might involve checking against previous candles
        if not ((df["low"] <= df["open"]) & (df["open"] <= df["high"]) &                 (df["low"] <= df["close"]) & (df["close"] <= df["high"])).all():
            logger.warning(f"Inconsistencia de precios detectada en los datos de {symbol} - {interval}. Se recomienda revisar.")
            # Decide whether to return or proceed; for now, we'll proceed with a warning.

        logger.info(f"Validación de datos para {symbol} - {interval} completada.")
        # --- Fin de validaciones ---

        # Guardar en CSV
        os.makedirs(output_path, exist_ok=True)
        # Si estamos en modo append, no escribir el encabezado y usar 'a' (append)
        df.to_csv(file_name, mode='a', header=not append_to_existing)
        logger.info(f"Datos históricos guardados/actualizados en: {file_name}")

        # Guardar en la base de datos
        # Convertir el índice de datetime a timestamp en ms para la BD
        df_to_db = df.copy()
        df_to_db["timestamp"] = df_to_db.index.astype(int) // 10**6 # Convertir a ms
        df_to_db["close_time"] = df_to_db["close_time"].astype(int) # Asegurarse de que close_time sea int
        add_klines(df_to_db, symbol, interval)
        logger.info(f"Datos históricos guardados/actualizados en la base de datos para {symbol}-{interval}.")

        return df

    except BinanceAPIException as e:
        logger.error(f"Error de la API de Binance al descargar datos: {e}")
    except Exception as e:
        logger.exception(f"Ocurrió un error inesperado durante la descarga: {e}")
    return pd.DataFrame()

async def main():
    # Descargar datos de BTCUSDT en intervalo de 1h desde el 1 de enero de 2022 hasta ahora
    await download_and_save_klines(symbol="BTCUSDT", interval="1h", start_str="1 Jan, 2022", append_to_existing=False)
    
    # Descargar datos de ETHUSDT en intervalo de 1d para un rango específico
    # await download_and_save_klines(symbol="ETHUSDT", interval="1d", start_str="1 Jan, 2021", end_str="31 Dec, 2021")

if __name__ == "__main__":
    asyncio.run(main())
