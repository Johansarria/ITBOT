from utils.audit_operations_db import log_operation_to_db

# utils/order_executor.py
from typing import Optional, Any
import os
from datetime import datetime
import uuid
import logging
import aiohttp
import random
import config
from binance.exceptions import BinanceAPIException, BinanceRequestException
from utils.telegram_handler import send_message

async def safe_send_message(bot_instance: Optional["Bot"], chat_id: Optional[int], message: str, reply_markup=None):
    """
    Envía un mensaje por Telegram solo si bot_instance y chat_id no son None.
    """
    if bot_instance is not None and chat_id is not None:
        await send_message(bot_instance, chat_id, message, reply_markup)
from utils.state_manager import StateManager
from utils.risk_manager import (
    obtener_riesgo_actual,
    riesgo_forzado_activo,
    duracion_riesgo_forzado,
    ganancias_durante_riesgo_forzado,
    operaciones_en_riesgo_forzado,
    calcular_probabilidad_ganancia_perdida,
    restaurar_riesgo_automatico,
    registrar_resultado_operacion,
    recordar_riesgo_forzado,
    obtener_riesgo_ajustado_por_ml,
    verificar_permiso_de_operacion  # IMPORTANTE: Importar la nueva función
)
from utils.shield_manager import escudo_activo
from utils.binance_client import get_binance_client # Importar la función para obtener el cliente de Binance
import pandas as pd
import asyncio
from functools import wraps

from typing import Optional, Any
from aiogram import Bot

# Decorador de reintentos con retroceso exponencial
def retry(exceptions, tries=4, delay=3, backoff=2, logger=None):
    def deco_retry(f):
        @wraps(f)
        async def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return await f(*args, **kwargs)
                except exceptions as e:
                    msg = f"{e}, Reintentando en {mdelay} segundos..."
                    if logger:
                        logger.warning(msg)
                    await asyncio.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return await f(*args, **kwargs)
        return f_retry
    return deco_retry

logger = logging.getLogger(__name__)
state_manager = StateManager()
DATA_DIR = "data/operaciones"
os.makedirs(DATA_DIR, exist_ok=True)
OPERATIONS_LOG = os.path.join(DATA_DIR, "operaciones.csv")

def calcular_cantidad_operar(balance_usdt: float, riesgo_pct: float, escudo: str = "ninguno") -> float:
    ajuste_riesgo = 1.0
    if escudo == "conservador" or escudo == "volatilidad_alta":
        ajuste_riesgo = 0.5
    elif escudo == "noticias_negativas":
        ajuste_riesgo = 0.25
    elif escudo == "extremo":
        ajuste_riesgo = 0.0
    elif escudo == "agresivo":
        ajuste_riesgo = 1.5
    
    monto = balance_usdt * riesgo_pct * ajuste_riesgo
    return round(monto, 2)

from typing import Optional

async def registrar_operacion(bot_instance: Optional["Bot"], chat_id: Optional[int], data: dict):
    """
    Registra la operación y, si es posible, notifica por Telegram.
    Si bot_instance o chat_id son None, solo registra localmente.
    """
    # Auditoría: registrar en base de datos
    log_operation_to_db(data)
    if bot_instance is None or chat_id is None:
        return
    logger.info(f"Registrando operación: {data}")
    if not os.path.isfile(OPERATIONS_LOG):
        df_header = pd.DataFrame(columns=list(data.keys()))
        df_header.to_csv(OPERATIONS_LOG, mode="w", header=True, index=False)

    df = pd.DataFrame([data])
    df.to_csv(OPERATIONS_LOG, mode="a", header=False, index=False)
    
    daily_ops_count = state_manager.get_state("general", "daily_operations_count", 0) + 1
    state_manager.set_state("general", "daily_operations_count", daily_ops_count)
    await send_message(bot_instance, chat_id, f"Operaciones diarias: {daily_ops_count}")

async def mostrar_estado_riesgo(bot_instance: Optional["Bot"], chat_id: Optional[int]):
    """
    Muestra el estado de riesgo actual por Telegram si es posible.
    Si bot_instance o chat_id son None, no hace nada.
    """
    if bot_instance is None or chat_id is None:
        return
    if riesgo_forzado_activo() and recordar_riesgo_forzado():
        duracion = duracion_riesgo_forzado()
        ganancias = ganancias_durante_riesgo_forzado()
        operaciones = operaciones_en_riesgo_forzado()
        probabilidad = calcular_probabilidad_ganancia_perdida()
        mensaje = (
            f"⚠️ Riesgo forzado sigue activo desde hace {duracion}.\n"
            f" Ganancia acumulada: {ganancias:.2f}%\n"
            f" Operaciones: {operaciones['total']} "
            f"({operaciones['positivas']} positivas, {operaciones['negativas']} negativas)\n"
            f" Probabilidad heurística si mantienes o subes riesgo:\n"
            f"  ➕ Ganar: {probabilidad['ganar']:.1f}% \n"
            f"  ➖ Perder: {probabilidad['perder']:.1f}%\n\n"
            f"Puedes responder con:\n"
            f" 'volver a automático'\n"
            f"⏳ 'mantener riesgo forzado'\n"
            f" 'no recordar más hoy'"
        )
        await send_message(bot_instance, chat_id, mensaje)

@retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger)
async def get_symbol_info(symbol: str) -> dict:
    client = await get_binance_client()
    exchange_info = await asyncio.to_thread(client.get_exchange_info)
    for s in exchange_info["symbols"]:
        if s["symbol"] == symbol:
            return s
    raise ValueError(f"Símbolo {symbol} no encontrado.")

def apply_filters(quantity: float, price: float, symbol_info: dict) -> tuple[float, float, float, float, float]:
    min_notional = 0.0
    step_size = 0.0
    price_filter_tick_size = 0.0

    for f in symbol_info["filters"]:
        if f["filterType"] == "NOTIONAL":
            min_notional = float(f["minNotional"])
        elif f["filterType"] == "LOT_SIZE":
            step_size = float(f["stepSize"])
        elif f["filterType"] == "PRICE_FILTER":
            price_filter_tick_size = float(f["tickSize"])

    precision = 0
    if step_size > 0:
        s_str = str(step_size)
        if '.' in s_str:
            precision = len(s_str.split('.')[1].rstrip('0'))

    # Ensure quantity meets step_size
    if step_size > 0:
        # If quantity is less than step_size, set it to step_size
        if quantity < step_size:
            quantity = step_size
        else:
            # Otherwise, round down to the nearest step_size multiple
            quantity = float(int(quantity / step_size)) * step_size
        quantity = round(quantity, precision)

    # Ensure quantity meets min_notional
    if quantity * price < min_notional:
        # Calculate the minimum quantity needed to meet min_notional
        min_qty_for_notional = min_notional / price
        
        # If this minimum quantity is less than step_size, use step_size
        if min_qty_for_notional < step_size:
            quantity = step_size
        else:
            # Otherwise, round up to the nearest step_size multiple
            quantity = float(int(min_qty_for_notional / step_size)) * step_size
            if quantity < min_qty_for_notional: # Ensure it's not rounded down below min_qty_for_notional
                quantity += step_size
        quantity = round(quantity, precision)

    price_precision = 0
    if price_filter_tick_size > 0:
        p_str = str(price_filter_tick_size)
        if '.' in p_str:
            price_precision = len(p_str.split('.')[1].rstrip('0'))
        price = round(price, price_precision)
    
    return quantity, price, min_notional, step_size, price_filter_tick_size

from typing import Optional

async def evaluar_y_ejecutar_operacion(
    bot_instance: Optional["Bot"],
    chat_id: Optional[int],
    resultado_analisis: dict,
    take_profit: Optional[float] = None,
    stop_loss: Optional[float] = None
) -> str:
    """
    Evalúa y ejecuta una operación de trading según el análisis recibido.
    Permite operar en modo Telegram (con bot y chat_id) o en modo worker (sin bot ni chat_id).
    Args:
        bot_instance (Optional[Bot]): Instancia del bot de Telegram o None si es worker.
        chat_id (Optional[int]): ID del chat de Telegram o None si es worker.
        resultado_analisis (dict): Resultado del análisis de mercado.
        take_profit (Optional[float]): Nivel de take profit.
        stop_loss (Optional[float]): Nivel de stop loss.
    Returns:
        str: Mensaje de resultado de la ejecución.
    """
    try:
        logger.info(f"Iniciando evaluación y ejecución de orden para: {resultado_analisis.get('symbol', 'N/A')}")
        client = await get_binance_client()

        permiso, razon = verificar_permiso_de_operacion()
        if not permiso:
            logger.warning(f"Operación cancelada. Razón: {razon}")
            await safe_send_message(bot_instance, chat_id, f"❌ Operación cancelada: {razon}")
            return f"Operación cancelada: {razon}"

        session_mode = state_manager.get_state("session", "mode", config.MODE)
        live_mode_unlocked = state_manager.get_state("live_mode", "unlocked", False)

        if session_mode == "LIVE" and not live_mode_unlocked:
            trade_mode_actual = "SIMULATED"
            await safe_send_message(bot_instance, chat_id, "⚠️ El bot está en modo LIVE pero no ha sido desbloqueado. La operación se realizará en modo SIMULADO.")
        elif session_mode == "LIVE" and live_mode_unlocked:
            trade_mode_actual = "REAL"
        else:
            trade_mode_actual = "SIMULATED"

        logger.info(f"Modo de operación efectivo: {trade_mode_actual}")

        balance_info = await retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger)(lambda: asyncio.to_thread(client.get_asset_balance, asset="USDT"))()
        if balance_info is None or "free" not in balance_info:
            balance = 0.0
        else:
            balance = float(balance_info["free"])

        escudo = escudo_activo()
        riesgo_base_pct = obtener_riesgo_actual()
        score_ml = resultado_analisis.get("score", 0.0)
        symbol = resultado_analisis.get("symbol", "BTCUSDT")
        decision = resultado_analisis.get("decision", "MANTENER")

        # Obtener información del símbolo antes de calcular la cantidad
        symbol_info = await get_symbol_info(symbol)
        if not symbol_info:
            logger.error(f"No se pudo obtener información del símbolo para {symbol}. Cancelando operación.")
            await safe_send_message(bot_instance, chat_id, f"❌ Error: No se pudo obtener información del símbolo {symbol}.")
            return "Error: Símbolo no encontrado."

        riesgo_pct = riesgo_base_pct
        if decision != "MANTENER":
            riesgo_pct = obtener_riesgo_ajustado_por_ml(score_ml, riesgo_base_pct)

        cantidad_usdt = calcular_cantidad_operar(balance, riesgo_pct, escudo)

        # Asegurarse de que la cantidad en USDT sea al menos el minNotional
        min_notional = float(next((f for f in symbol_info["filters"] if f["filterType"] == "NOTIONAL"), {}).get("minNotional", 0.0))
        if cantidad_usdt < min_notional:
            logger.warning(f"La cantidad calculada en USDT ({cantidad_usdt}) es menor que el minNotional ({min_notional}). Ajustando a minNotional.")
            cantidad_usdt = min_notional

        # Verificar si el balance disponible es suficiente para la cantidad ajustada
        if cantidad_usdt > balance:
            logger.warning(f"Balance insuficiente para operar. Cantidad requerida: {cantidad_usdt} USDT, Balance disponible: {balance} USDT.")
            await safe_send_message(bot_instance, chat_id, f"❌ Error: Balance insuficiente para operar. Necesitas al menos {cantidad_usdt:.2f} USDT.")
            return "Error: Balance insuficiente."

        tipo_operacion = None
        logger.debug(f"DEBUG: Decisión antes de la asignación: '{decision}' (Tipo: {type(decision)})")
        if decision == "BUY":
            tipo_operacion = "BUY"
        elif decision == "SELL":
            tipo_operacion = "SELL"

        if not tipo_operacion:
            logger.debug(f"DEBUG: tipo_operacion es None. Decisión original: {decision} (Tipo: {type(decision)})")
            logger.info(f"Decisión del análisis ({decision}) no recomienda operar.")
            if config.VERBOSE_NOTIFICATIONS:
                await safe_send_message(bot_instance, chat_id, f"ℹ️ Decisión del análisis ({decision}) no recomienda operar.")
            return "No se ejecutó operación."

        precio_actual_ticker = await retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger)(lambda: asyncio.to_thread(client.get_symbol_ticker, symbol=symbol))()
        precio_actual = float(precio_actual_ticker["price"])

        if precio_actual == 0:
            logger.error(f"Precio actual de {symbol} es cero.")
            await safe_send_message(bot_instance, chat_id, f"❌ Error: Precio actual de {symbol} es cero.")
            return "Error: Precio cero."

        symbol_info = await get_symbol_info(symbol)
        logger.info(f"DEBUG: symbol_info={symbol_info}")
        cantidad_token_bruta = cantidad_usdt / precio_actual
        cantidad_token, precio_actual_filtrado, min_notional_val, step_size_val, price_tick_size_val = apply_filters(cantidad_token_bruta, precio_actual, symbol_info)

        min_notional_filter = next((f for f in symbol_info["filters"] if f["filterType"] == "MIN_NOTIONAL"), None)
        if min_notional_filter and cantidad_token * precio_actual_filtrado < float(min_notional_filter["minNotional"]) - 1e-9:
            logger.warning(f"Cantidad calculada para {symbol} es muy pequeña. No se puede operar.")
            await safe_send_message(bot_instance, chat_id, f"❌ Error: Cantidad calculada para {symbol} es muy pequeña.")
            return "Error: Cantidad muy pequeña."

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        operation_id = str(uuid.uuid4())
        ganancia_pct_operacion = 0.0
        orden = {}

        if trade_mode_actual == "REAL":
            logger.warning("Ejecutando orden en MODO REAL.")
            await safe_send_message(bot_instance, chat_id, f"⚠️ Ejecutando orden REAL: {tipo_operacion} {cantidad_token} {symbol} a {precio_actual_filtrado} USDT.")
            
            logger.info(f"DEBUG: cantidad_usdt={cantidad_usdt}, precio_actual={precio_actual}, cantidad_token_bruta={cantidad_token_bruta}")
            logger.info(f"DEBUG: cantidad_token (after filters)={cantidad_token}, min_notional_val={min_notional_val}, step_size_val={step_size_val}")

            orden = await retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger)(lambda: asyncio.to_thread(client.create_order,
                symbol=symbol,
                side=tipo_operacion,
                type="MARKET",
                quantity=cantidad_token
            ))()
            mensaje_ejecucion = f"✅ ORDEN REAL EJECUTADA: {tipo_operacion} {cantidad_token} {symbol}. ID: {orden.get('orderId')}"
            logger.info(f"Orden real ejecutada: {orden}")
            slippage_pct = ((precio_actual_filtrado - precio_actual) / precio_actual) * 100
            fee_pct = 0.1  # Fee real de Binance (0.1%)
        else: # SIMULATED
            logger.info("Ejecutando orden en MODO SIMULADO.")
            # Simulación de slippage aleatorio ±0.05%
            slippage_pct = random.uniform(-0.05, 0.05)
            precio_simulado = precio_actual * (1 + slippage_pct / 100)
            fee_pct = 0.1  # Fee simulado (0.1%)
            fee_usdt = cantidad_usdt * fee_pct / 100
            mensaje_ejecucion = f"⚙️ ORDEN SIMULADA: {tipo_operacion} {cantidad_token} {symbol} a {precio_simulado:.2f} USDT (slippage {slippage_pct:+.3f}%, fee {fee_usdt:.2f} USDT)."
            ganancia_pct_operacion = random.uniform(-3, 5) - fee_pct
            precio_actual_filtrado = precio_simulado

        registrar_resultado_operacion(ganancia_pct_operacion)

        log_data = {
            "operation_id": operation_id, "timestamp_open": timestamp, "timestamp_close": None,
            "symbol": symbol, "side": tipo_operacion, "entry_price": precio_actual_filtrado,
            "exit_price": None, "take_profit": take_profit, "stop_loss": stop_loss,
            "size_usdt": cantidad_usdt, "risk_percent": riesgo_pct, "mode": trade_mode_actual,
            "pnl_usdt": None, "pnl_percent": ganancia_pct_operacion, "reason_open": decision,
            "reason_close": None, "market_score_open": score_ml, "market_score_close": None,
            "version_bot": "1.0.0", "notes": f"slippage={slippage_pct:+.3f}%, fee={fee_pct:.3f}%", "balance_usdt_al_abrir": balance,
            "escudo_activo_al_abrir": escudo_activo(), "tipo_escudo_al_abrir": escudo_activo(),
            "riesgo_forzado_al_abrir": riesgo_forzado_activo(), "cantidad_token_operada": cantidad_token,
            "min_notional_filter": min_notional_val, "step_size_filter": step_size_val,
            "price_tick_size_filter": price_tick_size_val,
            "slippage_apertura_pct": slippage_pct,
            "order_id_binance": orden.get('orderId'), "order_status_binance": orden.get('status')
        }
        await registrar_operacion(bot_instance, chat_id, log_data)

        await safe_send_message(bot_instance, chat_id, mensaje_ejecucion + f" Resultado simulado: {ganancia_pct_operacion:+.2f}%")
        await mostrar_estado_riesgo(bot_instance, chat_id)

        return "Operación procesada."

    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"Error de Binance al ejecutar orden: {e}", exc_info=True)
        await safe_send_message(bot_instance, chat_id, f"❌ Error de Binance: {e}")
        return "Error de Binance."
    except aiohttp.ClientError as e:
        logger.error(f"Error de conexión al ejecutar orden: {e}", exc_info=True)
        await safe_send_message(bot_instance, chat_id, f"❌ Error de conexión: {e}")
        return "Error de conexión."
    except Exception as e:
        logger.exception(f"Error general inesperado al ejecutar orden: {e}")
        await safe_send_message(bot_instance, chat_id, f"❌ Error inesperado: {e}")
        return "Error al procesar operación."
