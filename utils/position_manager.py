from utils.audit_operations_db import log_operation_to_db

import os
import pandas as pd
from utils.structured_logger import StructuredLogger
from config import settings
from utils.telegram_handler import send_message
import asyncio
from datetime import datetime
from utils.binance_client import get_binance_client # Importar la función para obtener el cliente de Binance
from binance.exceptions import BinanceAPIException, BinanceRequestException
import aiohttp
from aiogram import Bot

logger = StructuredLogger(__name__)

OPERATIONS_LOG = "data/operaciones/operaciones.csv"

def _read_operations_log(path: str = OPERATIONS_LOG) -> pd.DataFrame:
    """
    Lee el archivo de operaciones y devuelve un DataFrame. Si no existe, devuelve vacío.
    """
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        logger.info("OPERATIONS_LOG_NOT_FOUND", f"Archivo de operaciones no encontrado en: {path}", details={"path": path})
        return pd.DataFrame()
    except Exception as e:
        logger.error("OPERATIONS_LOG_READ_ERROR", f"Error al leer el archivo de operaciones en: {path}", details={"path": path}, exc_info=True)
        return pd.DataFrame()

def _write_operations_log(df: pd.DataFrame, path: str = OPERATIONS_LOG) -> None:
    """
    Escribe el DataFrame en el archivo de operaciones.
    """
    df.to_csv(path, index=False)


def get_open_positions(path: str = None) -> pd.DataFrame:
    """
    Devuelve un DataFrame con las posiciones abiertas (sin timestamp_close).
    Args:
        path (str): Ruta al archivo de operaciones. Si es None, usa OPERATIONS_LOG.
    Returns:
        pd.DataFrame: DataFrame con posiciones abiertas.
    """
    if path is None:
        path = OPERATIONS_LOG
    df = _read_operations_log(path)
    if "timestamp_close" in df.columns:
        return df[df["timestamp_close"].isna()]
    if not df.empty:
        logger.warning("COLUMN_NOT_FOUND", "Columna 'timestamp_close' no encontrada en el log de operaciones.", details={"path": path})
    return pd.DataFrame()

    from binance.exceptions import BinanceAPIException, BinanceRequestException # ADDED
    import aiohttp # ADDED

def close_position(operation_id: str, exit_price: float, reason_close: str, path: str = OPERATIONS_LOG) -> None:
    """
    Actualiza el registro de una operación en el CSV con los datos de cierre.
    Args:
        operation_id (str): ID de la operación a cerrar.
        exit_price (float): Precio de cierre.
        reason_close (str): Motivo del cierre.
        path (str): Ruta al archivo de operaciones.
    """
    try:
        backup_path = path + ".bak"
        if os.path.exists(path):
            df_current = _read_operations_log(path)
            _write_operations_log(df_current, backup_path)
            logger.info("OPERATIONS_LOG_BACKUP", f"Copia de seguridad de {path} creada en {backup_path}.", details={"original_path": path, "backup_path": backup_path})
        else:
            logger.warning("OPERATIONS_LOG_NOT_FOUND_ON_CLOSE", f"El archivo {path} no existe al intentar cerrar la posición.", details={"operation_id": operation_id})

        df = _read_operations_log(backup_path)
        position_index = df[df["operation_id"] == operation_id].index
        if not position_index.empty:
            entry_price = df.loc[position_index, 'entry_price'].iloc[0]
            size_usdt = df.loc[position_index, 'size_usdt'].iloc[0]
            pnl_usdt = (exit_price - entry_price) * size_usdt / entry_price
            pnl_percent = (exit_price - entry_price) / entry_price * 100
            now_str = datetime.now().isoformat()
            df.loc[position_index, 'timestamp_close'] = now_str
            df.loc[position_index, 'exit_price'] = exit_price
            df.loc[position_index, 'pnl_usdt'] = pnl_usdt
            df.loc[position_index, 'pnl_percent'] = pnl_percent
            df.loc[position_index, 'reason_close'] = reason_close
            df.loc[position_index, 'market_score_close'] = None
            df.loc[position_index, 'notes'] = "Cierre automático por " + reason_close
            _write_operations_log(df, path)
            logger.info(
                "POSITION_CLOSED",
                f"Posición {operation_id} cerrada por {reason_close}.",
                details={
                    "operation_id": operation_id,
                    "exit_price": exit_price,
                    "reason_close": reason_close,
                    "pnl_usdt": pnl_usdt,
                    "pnl_percent": pnl_percent
                }
            )
            # Auditoría: registrar cierre en base de datos
            cierre_data = df.loc[position_index].to_dict(orient="records")[0]
            # Asegura que todas las claves sean str para cumplir con el tipado
            cierre_data_str = {str(k): v for k, v in cierre_data.items()}
            log_operation_to_db(cierre_data_str)
        else:
            logger.warning("POSITION_NOT_FOUND_ON_CLOSE", f"No se encontró la operación {operation_id} para cerrar en el log.", details={"operation_id": operation_id})
    except Exception as e:
        logger.error(
            "POSITION_CLOSE_ERROR",
            f"Error al cerrar la posición {operation_id} en CSV: {e}",
            details={"operation_id": operation_id, "path": path},
            exc_info=True
        )


async def manage_open_positions(bot: Bot):
    """
    Función principal que gestiona las posiciones abiertas.
    Comprueba Take Profit y Stop Loss para cada una.
    Args:
        bot (Bot): Instancia del bot de Telegram para enviar mensajes.
    """
    logger.info("POSITION_MANAGEMENT_START", "Iniciando ciclo de gestión de posiciones abiertas.")
    open_positions = get_open_positions()

    if open_positions.empty:
        logger.info("NO_OPEN_POSITIONS", "No hay posiciones abiertas para gestionar.")
        return

    client = await get_binance_client() # Get the client instance here

    for _, position in open_positions.iterrows():
        symbol = position["symbol"]
        try:
            ticker = await client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])

            # Usar los nuevos nombres de columna
            entry_price = position["entry_price"]
            operation_id = position["operation_id"]
            take_profit = position["take_profit"]
            stop_loss = position["stop_loss"]

            # Calcular P&L actual para monitoreo
            price_change_pct = ((current_price - entry_price) / entry_price) * 100

            # Comprobar Take Profit
            if take_profit and price_change_pct >= take_profit:
                reason = "TAKE_PROFIT"
                close_position(operation_id, current_price, reason)
                await send_message(bot, settings.TELEGRAM_CHAT_ID, f"📈 TAKE PROFIT alcanzado para {symbol}. Posición cerrada a {current_price}.")
                continue

            # Comprobar Stop Loss
            if stop_loss and price_change_pct <= stop_loss:
                reason = "STOP_LOSS"
                close_position(operation_id, current_price, reason)
                await send_message(bot, settings.TELEGRAM_CHAT_ID, f"📉 STOP LOSS alcanzado para {symbol}. Posición cerrada a {current_price}.")

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(
                "POSITION_MANAGEMENT_BINANCE_ERROR",
                f"Error de la API de Binance al gestionar la posición {position['operation_id']}: {e}",
                details={"operation_id": position['operation_id']},
                exc_info=True
            )
        except aiohttp.ClientError as e:
            logger.error(
                "POSITION_MANAGEMENT_CONNECTION_ERROR",
                f"Error de conexión al gestionar la posición {position['operation_id']}: {e}",
                details={"operation_id": position['operation_id']},
                exc_info=True
            )
        except Exception as e:
            logger.error(
                "POSITION_MANAGEMENT_UNEXPECTED_ERROR",
                f"Error inesperado al gestionar la posición {position['operation_id']}: {e}",
                details={"operation_id": position['operation_id']},
                exc_info=True
            )

async def get_open_positions_summary(bot: Bot) -> str:
    """Devuelve un resumen formateado de las posiciones abiertas."""
    open_positions = get_open_positions()

    if open_positions.empty:
        return "✅ No hay posiciones abiertas en este momento."

    # Convert 'timestamp_open' to datetime objects for proper sorting
    open_positions['timestamp_open'] = pd.to_datetime(open_positions['timestamp_open'])

    # Sort by timestamp_open in descending order and take the top 5
    recent_open_positions = open_positions.sort_values(by='timestamp_open', ascending=False).head(5)

    summary = "📊 <b>Últimas 5 Posiciones Abiertas:</b>\n"
    client = await get_binance_client() # Get the client instance here
    for _, position in recent_open_positions.iterrows():
        symbol = position["symbol"]
        entry_price = position["entry_price"]
        size_usdt = position["size_usdt"]
        timestamp_open = position["timestamp_open"]

        try:
            ticker = await client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            pnl_usdt = (current_price - entry_price) * (size_usdt / entry_price) # Asumiendo size_usdt es el valor nocional

            summary += (
                f"\n- <b>Símbolo:</b> <code>{symbol}</code>\n"
                f"  - <b>Precio Entrada:</b> {entry_price:.2f}\n"
                f"  - <b>Tamaño (USDT):</b> {size_usdt:.2f}\n"
                f"  - <b>Precio Actual:</b> {current_price:.2f}\n"
                f"  - <b>P&L:</b> {pnl_percent:+.2f}% ({pnl_usdt:+.2f} USDT)\n"
                f"  - <b>Abierta desde:</b> {timestamp_open.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error("SUMMARY_BINANCE_ERROR", f"Error de API de Binance al obtener precio para resumen de {symbol}", details={"symbol": symbol}, exc_info=True)
            summary += (
                f"\n- <b>Símbolo:</b> <code>{symbol}</code>\n"
                f"  - <b>Estado:</b> ERROR de API al obtener precio\n"
            )
        except aiohttp.ClientError as e:
            logger.error("SUMMARY_CONNECTION_ERROR", f"Error de conexión al obtener precio para resumen de {symbol}", details={"symbol": symbol}, exc_info=True)
            summary += (
                f"\n- <b>Símbolo:</b> <code>{symbol}</code>\n"
                f"  - <b>Estado:</b> ERROR de conexión al obtener precio\n"
            )
        except Exception as e:
            logger.error("SUMMARY_UNEXPECTED_ERROR", f"Error inesperado al obtener precio para resumen de {symbol}", details={"symbol": symbol}, exc_info=True)
            summary += (
                f"\n- <b>Símbolo:</b> <code>{symbol}</code>\n"
                f"  - <b>Estado:</b> ERROR inesperado al obtener precio\n"
            )
    return summary

def get_closed_positions(path: str = None) -> pd.DataFrame:
    """
    Devuelve un DataFrame con las posiciones cerradas (con timestamp_close).
    Args:
        path (str): Ruta al archivo de operaciones. Si es None, usa OPERATIONS_LOG.
    Returns:
        pd.DataFrame: DataFrame con posiciones cerradas.
    """
    if path is None:
        path = OPERATIONS_LOG
    df = _read_operations_log(path)
    if "timestamp_close" in df.columns:
        return df[df["timestamp_close"].notna()]
    return pd.DataFrame()

def get_closed_positions_summary() -> str:
    """Devuelve un resumen formateado de las posiciones cerradas."""
    closed_positions = get_closed_positions()

    if closed_positions.empty:
        return "✅ No hay posiciones cerradas en este momento."

    # Convert 'timestamp_close' to datetime objects for proper sorting
    closed_positions['timestamp_close'] = pd.to_datetime(closed_positions['timestamp_close'])

    # Sort by timestamp_close in descending order and take the top 5
    recent_closed_positions = closed_positions.sort_values(by='timestamp_close', ascending=False).head(5)

    summary = "📈 <b>Últimas 5 Posiciones Cerradas:</b>\n"
    for _, position in recent_closed_positions.iterrows():
        symbol = position["symbol"]
        entry_price = position["entry_price"]
        exit_price = position["exit_price"]
        pnl_percent = position["pnl_percent"]
        timestamp_close = position["timestamp_close"]

        summary += (
            f"\n- <b>Símbolo:</b> <code>{symbol}</code>\n"
            f"  - <b>Entrada:</b> {entry_price:.2f} | <b>Salida:</b> {exit_price:.2f}\n"
            f"  - <b>P&L:</b> {pnl_percent:+.2f}%\n"
            f"  - <b>Cerrada:</b> {timestamp_close.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
    return summary
