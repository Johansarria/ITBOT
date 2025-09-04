from utils.audit_operations_db import log_operation_to_db

# utils/order_executor.py
from typing import Optional, Any
import os
from datetime import datetime
import uuid
from utils.structured_logger import StructuredLogger
import aiohttp
import random
import config
from binance.exceptions import BinanceAPIException, BinanceRequestException
from utils.telegram_handler import send_message

def calculate_transaction_cost(trade_size_usdt: float, spread_percentage: float) -> tuple[float, float, float]:
    """
    Calcula el coste total de una transacción basado en el modelo de costes configurado.
    Asume un coste de "round trip" (apertura y cierre).

    Args:
        trade_size_usdt (float): El tamaño de la operación en USDT.
        spread_percentage (float): El spread porcentual actual del mercado.

    Returns:
        tuple[float, float, float]: Una tupla con (coste_spread_usdt, coste_comision_usdt, coste_total_usdt).
    """
    # 1. Coste por Spread (se paga al cruzarlo para abrir la posición)
    coste_spread_usdt = trade_size_usdt * (spread_percentage / 100.0)

    # 2. Coste por Comisión
    coste_comision_usdt = 0.0
    if config.settings.COST_MODEL == "RAW":
        # Asumimos que la comisión en config (COMMISSION_PER_LOT) se define por un volumen estándar de 100,000 USD.
        commission_rate = config.settings.COMMISSION_PER_LOT / 100000.0
        
        # La comisión se paga tanto al abrir como al cerrar (round trip).
        coste_comision_apertura = trade_size_usdt * commission_rate
        coste_comision_cierre = trade_size_usdt * commission_rate
        coste_comision_usdt = coste_comision_apertura + coste_comision_cierre

    # El coste total es el spread que pagas al entrar + las comisiones de entrada y salida.
    coste_total_usdt = coste_spread_usdt + coste_comision_usdt
    
    return coste_spread_usdt, coste_comision_usdt, coste_total_usdt

async def safe_send_message(bot_instance: Optional["Bot"], chat_id: Optional[int], message: str, reply_markup=None):
    """
    Envía un mensaje por Telegram solo si bot_instance y chat_id no son None.
    """
    if bot_instance is not None and chat_id is not None:
        await send_message(bot_instance, chat_id, message, reply_markup)
import utils.state_manager as state_manager_module
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
from utils.binance_client import (
    get_binance_client,
    get_bid_ask_spread,
    get_um_futures_client,
    get_futures_exchange_info,
)
import pandas as pd
import asyncio
from functools import wraps
import inspect

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
                        logger.warning("RETRYING", msg)
                    await asyncio.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return await f(*args, **kwargs)
        return f_retry
    return deco_retry

logger = StructuredLogger(__name__)
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

async def registrar_operacion(bot_instance: Optional["Bot"], chat_id: Optional[int], data: dict, state_manager=None):
    """
    Registra la operación y, si es posible, notifica por Telegram.
    Si bot_instance o chat_id son None, solo registra localmente.
    """
    # Auditoría: registrar en base de datos
    log_operation_to_db(data)
    if bot_instance is None or chat_id is None:
        return
    logger.info("OPERATION_REGISTERED", "Registrando operación en log local.", details={"data": data})
    if not os.path.isfile(OPERATIONS_LOG):
        df_header = pd.DataFrame(columns=list(data.keys()))
        df_header.to_csv(OPERATIONS_LOG, mode="w", header=True, index=False)

    df = pd.DataFrame([data])
    df.to_csv(OPERATIONS_LOG, mode="a", header=False, index=False)
    
    if state_manager is not None:
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
    # AsyncClient: llamar directamente con await
    exchange_info = await client.get_exchange_info()
    symbols = exchange_info.get("symbols", []) if isinstance(exchange_info, dict) else []
    for s in symbols:
        if s.get("symbol") == symbol:
            return s
    # Fallback: remap stablecoins a USDT si el par no existe (ej. USDCUSDT -> USDTUSDT no, usar BTCUSDT para demo no tiene sentido)
    # Mejor: si es par con USDT y no existe, abortar; si es stable-stable no tradable, forzar error claro
    if symbol.endswith("USDT"):
        # El símbolo no existe en exchange_info; producir error claro
        raise ValueError(f"Símbolo {symbol} no encontrado (posible stable-stable pair no soportado).")
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


def _round_to_tick_size(price: float, tick_size_str: str) -> float:
    """Rounds a price to the nearest tick size."""
    tick_size = float(tick_size_str)
    if tick_size == 0:
        return price

    # Calculate precision from the tick_size string
    if 'e-' in tick_size_str:
        precision = int(tick_size_str.split('e-')[-1])
    elif '.' in tick_size_str:
        precision = len(tick_size_str.split('.')[-1].rstrip('0'))
    else:
        precision = 0

    return round(price, precision)


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
    """
    try:
        # State manager
        StateManagerRef = state_manager_module.StateManager
        sm = StateManagerRef() if isinstance(StateManagerRef, type) else StateManagerRef

        logger.info(
            "ORDER_EVALUATION_START",
            f"Iniciando evaluación y ejecución para: {resultado_analisis.get('symbol', 'N/A')}",
            details=resultado_analisis,
        )
        client = await get_binance_client()

        # Determinar modo efectivo
        default_mode = getattr(getattr(config, 'settings', object()), "MODE", "LIVE")
        session_mode_raw = sm.get_state("session", "mode", default_mode)
        session_mode_val = session_mode_raw if isinstance(session_mode_raw, str) else default_mode
        session_mode_norm = session_mode_val.strip().lower() if session_mode_val else "simulated"
        live_unlocked_raw = sm.get_state("live_mode", "unlocked", False)
        live_mode_unlocked = live_unlocked_raw if isinstance(live_unlocked_raw, bool) else False
        warn_live_locked = session_mode_norm == "live" and not live_mode_unlocked
        trade_mode_actual = "REAL" if session_mode_norm == "live" and live_mode_unlocked else "SIMULATED"

        logger.info("EFFECTIVE_TRADE_MODE", f"Modo de operación efectivo: {trade_mode_actual}", details={"mode": trade_mode_actual})

        # Determinar objetivo de ejecución (para pausar cTrader si no aplica)
        exec_target = str(getattr(getattr(config, 'settings', object()), 'EXECUTION_TARGET', 'BINANCE')).upper()

        # Símbolo de la operación (necesario para decidir si se usa Futuros)
        symbol = resultado_analisis.get("symbol", "BTCUSDT")

        # Balance (usar cuenta REAL correcta según ruta de ejecución)
        balance = 0.0
        if exec_target == 'CTRADER':
            # Si el objetivo es cTrader, usar equity de cTrader
            try:
                import json as _json
                acc_path = os.path.join('data', 'ctrader', 'account.json')
                if os.path.exists(acc_path):
                    with open(acc_path, 'r') as f:
                        acc = _json.load(f)
                        eq = acc.get('equity')
                        if eq is not None:
                            balance = float(eq)
            except Exception:
                balance = 0.0
        else:
            # Si vamos a ejecutar en Futuros (micro-trade en modo REAL), usar balance de Futuros; si no, Spot
            micro_futures_flags = bool(getattr(getattr(config, 'settings', object()), 'ENABLE_MICRO_TRADE', False)) and bool(getattr(getattr(config, 'settings', object()), 'MICRO_TRADE_USE_FUTURES', True))
            allowed_list = list(getattr(getattr(config, 'settings', object()), 'MICRO_TRADE_ALLOWED_SYMBOLS', []))
            use_futures_for_balance = (trade_mode_actual == "REAL") and micro_futures_flags and (symbol in allowed_list if allowed_list else True)
            if use_futures_for_balance:
                try:
                    fut_client = get_um_futures_client()
                    fut_balances = await asyncio.to_thread(fut_client.futures_account_balance)
                    # Buscar USDT y USDC en balances de Futuros (priorizar el mayor)
                    if isinstance(fut_balances, list):
                        # Buscar USDT primero
                        usdt_items = [b for b in fut_balances if str(b.get('asset')).upper() == 'USDT']
                        usdt_balance = 0.0
                        if usdt_items:
                            item = usdt_items[0]
                            avail = item.get('balance') or item.get('availableBalance') or item.get('withdrawAvailable')
                            try:
                                usdt_balance = float(avail)
                            except Exception:
                                usdt_balance = 0.0
                        
                        # Buscar USDC también
                        usdc_items = [b for b in fut_balances if str(b.get('asset')).upper() == 'USDC']
                        usdc_balance = 0.0
                        if usdc_items:
                            item = usdc_items[0]
                            avail = item.get('balance') or item.get('availableBalance') or item.get('withdrawAvailable')
                            try:
                                usdc_balance = float(avail)
                            except Exception:
                                usdc_balance = 0.0
                        
                        # Usar el balance mayor entre USDT y USDC
                        if usdc_balance > usdt_balance:
                            balance = usdc_balance
                            logger.info("USING_FUTURES_BALANCE", f"Balance Futuros USDC: ${balance:.2f} (convertido a USD)")
                        elif usdt_balance > 0:
                            balance = usdt_balance
                            logger.info("USING_FUTURES_BALANCE", f"Balance Futuros USDT: ${balance:.2f}")
                        else:
                            balance = 0.0
                except Exception as e:
                    logger.warning("FUTURES_BALANCE_ERROR", f"Error obteniendo balance de Futuros: {e}")
                    balance = 0.0
            if balance <= 0:
                # Fallback a Spot si no tenemos balance de Futuros o no aplica
                # Intentar USDT primero
                balance_info = await retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger)(
                    lambda: asyncio.to_thread(client.get_asset_balance, asset="USDT")
                )()
                usdt_balance = float(balance_info.get("free", 0.0)) if isinstance(balance_info, dict) else 0.0
                
                # Intentar USDC también
                balance_info_usdc = await retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger)(
                    lambda: asyncio.to_thread(client.get_asset_balance, asset="USDC")
                )()
                usdc_balance = float(balance_info_usdc.get("free", 0.0)) if isinstance(balance_info_usdc, dict) else 0.0
                
                # Usar el balance mayor
                if usdc_balance > usdt_balance:
                    balance = usdc_balance
                    logger.info("USING_SPOT_BALANCE", f"Balance Spot USDC: ${balance:.2f} (convertido a USD)")
                else:
                    balance = usdt_balance
                    logger.info("USING_SPOT_BALANCE", f"Balance Spot USDT: ${balance:.2f}")

        escudo = escudo_activo()
        riesgo_base_pct = obtener_riesgo_actual()
        score_ml = resultado_analisis.get("score", 0.0)
        symbol = resultado_analisis.get("symbol", "BTCUSDT")
        decision = resultado_analisis.get("decision", "MANTENER")

        # Info de símbolo
        symbol_info = await get_symbol_info(symbol)
        if not symbol_info:
            logger.error("SYMBOL_INFO_FETCH_ERROR", f"No se pudo obtener información del símbolo para {symbol}.", details={"symbol": symbol})
            await safe_send_message(bot_instance, chat_id, f"❌ Error: No se pudo obtener información del símbolo {symbol}.")
            return "Error: Símbolo no encontrado."

        riesgo_pct = riesgo_base_pct if decision == "MANTENER" else obtener_riesgo_ajustado_por_ml(score_ml, riesgo_base_pct)
        cantidad_usdt = calcular_cantidad_operar(balance, riesgo_pct, escudo)

        permiso, razon = await verificar_permiso_de_operacion(new_trade_size_usdt=cantidad_usdt, symbol=symbol)
        if not permiso:
            return f"Operación cancelada por gestor de riesgo: {razon}"

        min_notional = float(next((f for f in symbol_info.get("filters", []) if f.get("filterType") == "NOTIONAL"), {}).get("minNotional", 0.0))
        if cantidad_usdt < min_notional:
            logger.warning("TRADE_SIZE_ADJUSTED_MIN_NOTIONAL", f"Cantidad en USDT ({cantidad_usdt}) ajustada a minNotional ({min_notional}).", details={"calculated_usdt": cantidad_usdt, "min_notional": min_notional})
            cantidad_usdt = min_notional

        if cantidad_usdt > balance:
            logger.warning("INSUFFICIENT_BALANCE", "Balance insuficiente para operar.", details={"required_usdt": cantidad_usdt, "available_usdt": balance})
            await safe_send_message(bot_instance, chat_id, f"❌ Error: Balance insuficiente para operar. Necesitas al menos {cantidad_usdt:.2f} USDT.")
            return "Error: Balance insuficiente."

        # --- Validación de costes y spread ---
        bid, ask, spread, spread_percentage = await get_bid_ask_spread(symbol)
        if spread_percentage is None:
            logger.error("SPREAD_FETCH_ERROR", f"No se pudo obtener el spread para {symbol}. Abortando.", details={"symbol": symbol})
            await safe_send_message(bot_instance, chat_id, f"❌ Error: No se pudo obtener el spread para {symbol}.")
            return "Error: Spread no disponible."
        if spread_percentage > config.settings.MAX_SPREAD_PERCENTAGE:
            logger.warning("MAX_SPREAD_EXCEEDED", f"El spread actual ({spread_percentage:.4f}%) para {symbol} supera el máximo permitido ({config.settings.MAX_SPREAD_PERCENTAGE}%).", details={"symbol": symbol, "spread_pct": spread_percentage})
            await safe_send_message(bot_instance, chat_id, f"⚠️ Operación cancelada: El spread para {symbol} es demasiado alto ({spread_percentage:.4f}%).")
            return "Operación cancelada: Spread muy alto."
        coste_spread_usdt, coste_comision_usdt, coste_total_usdt = calculate_transaction_cost(cantidad_usdt, spread_percentage)
        expected_profit_pct = take_profit if take_profit is not None else config.settings.RISK_PER_TRADE_TAKE_PROFIT_PCT
        expected_profit_usdt = cantidad_usdt * (expected_profit_pct / 100.0)
        if expected_profit_usdt < coste_total_usdt * config.settings.PROFIT_TO_COST_RATIO:
            logger.warning("PROFIT_COST_RATIO_TOO_LOW", f"El ratio ganancia/coste para {symbol} es bajo. Esperado: ${expected_profit_usdt:.2f}, Coste: ${coste_total_usdt:.2f}")
            await safe_send_message(bot_instance, chat_id, f"⚠️ Operación cancelada: El beneficio esperado (${expected_profit_usdt:.2f}) no cubre el coste (${coste_total_usdt:.2f}).")
            return "Operación cancelada: Ratio Ganancia/Coste bajo."
        logger.info("COST_ANALYSIS_PASSED", f"Coste total estimado: ${coste_total_usdt:.4f}", details={"symbol": symbol})

        # Decisión
        tipo_operacion = "BUY" if decision == "BUY" else ("SELL" if decision == "SELL" else None)
        if not tipo_operacion:
            logger.info("NO_TRADE_DECISION", f"Decisión del análisis ({decision}) no recomienda operar.")
            if getattr(config, "VERBOSE_NOTIFICATIONS", False):
                await safe_send_message(bot_instance, chat_id, f"ℹ️ Decisión del análisis ({decision}) no recomienda operar.")
            return "No se ejecutó operación."

        # Precio actual
        # Obtener ticker actual de forma asíncrona correcta
        precio_actual_ticker = await client.get_symbol_ticker(symbol=symbol)
        price_val = precio_actual_ticker.get("price") if isinstance(precio_actual_ticker, dict) else getattr(precio_actual_ticker, "price", None)
        precio_actual = float(price_val) if price_val is not None else 0.0
        if precio_actual == 0:
            logger.error("ZERO_PRICE_ERROR", f"Precio actual de {symbol} es cero.")
            await safe_send_message(bot_instance, chat_id, f"❌ Error: Precio actual de {symbol} es cero.")
            return "Error: Precio cero."

        # Cantidad filtrada
        cantidad_token_bruta = cantidad_usdt / precio_actual
        cantidad_token, precio_actual_filtrado, min_notional_val, step_size_val, price_tick_size_val = apply_filters(cantidad_token_bruta, precio_actual, symbol_info)

        min_notional_filter = next((f for f in symbol_info.get("filters", []) if f.get("filterType") == "MIN_NOTIONAL"), None)
        if min_notional_filter and cantidad_token * precio_actual_filtrado < float(min_notional_filter.get("minNotional", 0.0)) - 1e-9:
            logger.warning("MIN_QTY_TOO_SMALL", f"Cantidad calculada para {symbol} es muy pequeña. No se puede operar.")
            await safe_send_message(bot_instance, chat_id, f"❌ Error: Cantidad calculada para {symbol} es muy pequeña.")
            return "Error: Cantidad muy pequeña."

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        operation_id = str(uuid.uuid4())
        ganancia_pct_operacion = 0.0

        logger.info("TRADE_DECISION_ATTEMPT", f"Intento de operación {tipo_operacion} para {symbol}", details={
            "symbol": symbol,
            "decision": tipo_operacion,
            "reason_open": decision,
            "market_score_open": score_ml,
            "risk_percent": riesgo_pct,
            "size_usdt": cantidad_usdt,
            "active_shield": escudo,
            "trade_mode": trade_mode_actual,
            "take_profit_pct": take_profit,
            "stop_loss_pct": stop_loss,
        })

        entry_order_id = f"sim_{operation_id}"
        oco_order_list_id = None
        entry_order_status = "FILLED"
        final_entry_price = precio_actual_filtrado
        slippage_pct = 0.0

        if warn_live_locked:
            await safe_send_message(bot_instance, chat_id, "⚠️ El bot está en modo LIVE pero no ha sido desbloqueado. La operación se realizará en modo SIMULADO.")

        if exec_target == 'CTRADER':
            try:
                base_url = getattr(getattr(config, 'settings', object()), 'WEB_API_BASE_URL', 'http://web:8080')
                secret = getattr(getattr(config, 'settings', object()), 'INTERNAL_API_SECRET', None)
                order_payload = {
                    'symbol': symbol,
                    'side': tipo_operacion,
                    'type': 'MARKET',
                    'quantity': cantidad_token,
                    'price': None,
                    'sl': stop_loss if stop_loss is not None else getattr(getattr(config, 'settings', object()), 'RISK_PER_TRADE_STOP_LOSS_PCT', 2.0),
                    'tp': take_profit if take_profit is not None else getattr(getattr(config, 'settings', object()), 'RISK_PER_TRADE_TAKE_PROFIT_PCT', 4.0),
                    'client_order_id': entry_order_id
                }
                import requests
                def _post_order():
                    headers = {'Content-Type': 'application/json'}
                    if secret:
                        headers['X-Internal-Secret'] = str(secret)
                    url = f"{base_url.rstrip('/')}/api/ctrader/orders/queue"
                    return requests.post(url, json=order_payload, headers=headers, timeout=10)
                resp = await asyncio.to_thread(_post_order)
                if resp.status_code == 200:
                    logger.info("CTRADER_ORDER_QUEUED", "Orden encolada para cTrader", details=order_payload)
                    await safe_send_message(bot_instance, chat_id, f"📤 Orden enviada a cTrader: {tipo_operacion} {cantidad_token} {symbol} (MKT)")
                    entry_order_status = "QUEUED_CTRADER"
                    oco_order_list_id = None
                    mensaje_ejecucion = f"📤 Enviada a cTrader: {tipo_operacion} {cantidad_token} {symbol} a mercado."
                else:
                    logger.error("CTRADER_ORDER_QUEUE_ERROR", f"Fallo al encolar orden cTrader: HTTP {resp.status_code} {resp.text}")
                    await safe_send_message(bot_instance, chat_id, f"❌ Error al encolar orden cTrader: {resp.status_code}")
                    return "Error al encolar orden cTrader."
            except Exception as e:
                logger.error("CTRADER_ORDER_QUEUE_EXCEPTION", f"Excepción al encolar: {e}")
                await safe_send_message(bot_instance, chat_id, f"❌ Excepción en envío a cTrader: {e}")
                return "Error cTrader."
        elif trade_mode_actual == "REAL":
            # ¿Micro-trade con Futuros?
            micro_futures = bool(getattr(getattr(config, 'settings', object()), 'ENABLE_MICRO_TRADE', False)) and bool(getattr(getattr(config, 'settings', object()), 'MICRO_TRADE_USE_FUTURES', True))
            allowed_list = list(getattr(getattr(config, 'settings', object()), 'MICRO_TRADE_ALLOWED_SYMBOLS', []))
            use_futures = micro_futures and (symbol in allowed_list if allowed_list else True)

            if use_futures:
                logger.warning("EXECUTION_MODE_REAL_FUTURES", "Ejecutando orden en Binance Futuros (micro-trade REAL).")
                
                # Limitar tamaño a micro-trade
                try:
                    max_usdt = float(getattr(getattr(config, 'settings', object()), 'MICRO_TRADE_MAX_USDT', 5.0))
                    leverage = float(getattr(getattr(config, 'settings', object()), 'MICRO_TRADE_LEVERAGE', 5.0))
                    tp_pct = float(getattr(getattr(config, 'settings', object()), 'RISK_PER_TRADE_TAKE_PROFIT_PCT', 4.0))
                    min_roi_margin = float(getattr(getattr(config, 'settings', object()), 'MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT', 18.0))
                except Exception:
                    max_usdt = 5.0
                    leverage = 5.0
                    tp_pct = 4.0
                    min_roi_margin = 18.0
                
                size_usdt_fut = min(cantidad_usdt, max_usdt)
                
                # ✅ VALIDACIÓN ROI >= 13% PARA FUTUROS
                margin_used = size_usdt_fut / leverage
                tp_gain_usdt = size_usdt_fut * (tp_pct / 100)
                roi_tp_on_margin = (tp_gain_usdt / margin_used * 100.0) if margin_used > 0 else 0.0
                
                if roi_tp_on_margin < min_roi_margin:
                    logger.warning("ROI_FILTER_REJECTED", f"ROI {roi_tp_on_margin:.1f}% < mínimo {min_roi_margin:.1f}%")
                    await safe_send_message(bot_instance, chat_id, f"❌ Trade rechazado: ROI {roi_tp_on_margin:.1f}% < mínimo {min_roi_margin:.1f}%")
                    return "Trade rechazado por ROI insuficiente."
                else:
                    logger.info("ROI_FILTER_PASSED", f"ROI {roi_tp_on_margin:.1f}% >= mínimo {min_roi_margin:.1f}%")
                
                await safe_send_message(bot_instance, chat_id, f"⚠️ Ejecutando (Futuros) REAL: {tipo_operacion} {symbol}… ROI: {roi_tp_on_margin:.1f}%")

                # Obtener info de Futuros para filtros
                fut_info_all = get_futures_exchange_info() or {}
                fut_symbol_info = None
                try:
                    for s in fut_info_all.get('symbols', []):
                        if s.get('symbol') == symbol:
                            fut_symbol_info = s
                            break
                except Exception:
                    fut_symbol_info = None

                # Derivar precision de qty y precio
                fut_step_size = 0.0
                fut_tick_size = 0.0
                if fut_symbol_info:
                    for f in fut_symbol_info.get('filters', []):
                        if f.get('filterType') == 'LOT_SIZE':
                            fut_step_size = float(f.get('stepSize', 0.0))
                        if f.get('filterType') == 'PRICE_FILTER':
                            fut_tick_size = float(f.get('tickSize', 0.0))

                # Calcular qty base
                qty_base = size_usdt_fut / precio_actual
                # Aplicar step size de Futuros si está disponible
                if fut_step_size and fut_step_size > 0:
                    qty_base = float(int(qty_base / fut_step_size)) * fut_step_size or fut_step_size

                # Preparar precios SL/TP con workingType de Futuros
                try:
                    sl_pct = float(stop_loss) if stop_loss is not None else float(getattr(getattr(config, 'settings', object()), 'RISK_PER_TRADE_STOP_LOSS_PCT', 2.0))
                except Exception:
                    sl_pct = 2.0
                try:
                    tp_pct = float(take_profit) if take_profit is not None else float(getattr(getattr(config, 'settings', object()), 'RISK_PER_TRADE_TAKE_PROFIT_PCT', 4.0))
                except Exception:
                    tp_pct = 4.0

                if tipo_operacion == 'BUY':
                    sl_price = precio_actual * (1 - sl_pct / 100)
                    tp_price = precio_actual * (1 + tp_pct / 100)
                    exit_side = 'SELL'
                else:
                    sl_price = precio_actual * (1 + sl_pct / 100)
                    tp_price = precio_actual * (1 - tp_pct / 100)
                    exit_side = 'BUY'

                # Redondear precios a tick de Futuros si está disponible
                if fut_tick_size and fut_tick_size > 0:
                    tick_str = f"{fut_tick_size}"
                    sl_price = _round_to_tick_size(sl_price, tick_str)
                    tp_price = _round_to_tick_size(tp_price, tick_str)

                fut_client = get_um_futures_client()
                # Ajustar apalancamiento (ignorar errores si ya está configurado)
                try:
                    await asyncio.to_thread(fut_client.futures_change_leverage, symbol=symbol, leverage=int(getattr(getattr(config, 'settings', object()), 'MICRO_TRADE_LEVERAGE', 5)))
                except Exception as e:
                    logger.warning("FUT_LEVERAGE_SET_WARN", f"No se pudo ajustar leverage: {e}")

                # Ejecutar entrada a mercado
                try:
                    entry_res = await asyncio.to_thread(
                        fut_client.futures_create_order,
                        symbol=symbol,
                        side=tipo_operacion,
                        type='MARKET',
                        quantity=qty_base,
                    )
                    entry_order_id = entry_res.get('orderId')
                    entry_order_status = entry_res.get('status', 'NEW')
                    final_entry_price = precio_actual  # Aproximación
                    logger.info("FUTURES_ENTRY_OK", "Entrada FUTURES ejecutada.", details=entry_res)
                except Exception as e:
                    logger.error("FUTURES_ENTRY_ERROR", f"Error al ejecutar entrada FUTURES: {e}")
                    await safe_send_message(bot_instance, chat_id, f"❌ Error entrada Futuros: {e}")
                    return "Error Futuros entrada."

                # Colocar SL y TP como órdenes reduceOnly
                try:
                    sl_working = str(getattr(getattr(config, 'settings', object()), 'FUTURES_SL_WORKING_TYPE', 'MARK_PRICE'))
                    tp_working = str(getattr(getattr(config, 'settings', object()), 'FUTURES_TP_WORKING_TYPE', 'CONTRACT_PRICE'))
                    sl_res = await asyncio.to_thread(
                        fut_client.futures_create_order,
                        symbol=symbol,
                        side=exit_side,
                        type='STOP_MARKET',
                        stopPrice=sl_price,
                        workingType=sl_working,
                        reduceOnly='true',
                        quantity=qty_base,
                    )
                    tp_res = await asyncio.to_thread(
                        fut_client.futures_create_order,
                        symbol=symbol,
                        side=exit_side,
                        type='TAKE_PROFIT_MARKET',
                        stopPrice=tp_price,
                        workingType=tp_working,
                        reduceOnly='true',
                        quantity=qty_base,
                    )
                    logger.info("FUTURES_PROTECTION_OK", "SL/TP FUTURES colocados.", details={"sl": sl_res, "tp": tp_res})
                    mensaje_ejecucion = f"✅ FUTUROS (REAL) con SL/TP:\n- Entrada: {tipo_operacion} {qty_base} {symbol} @ ~{final_entry_price:.4f}\n- SL: {sl_price:.4f}\n- TP: {tp_price:.4f}"
                except Exception as e:
                    logger.error("FUTURES_PROTECTION_ERROR", f"Error al colocar SL/TP FUTURES: {e}")
                    await safe_send_message(bot_instance, chat_id, f"⚠️ Entrada hecha, pero fallo SL/TP: {e}")
                    mensaje_ejecucion = f"⚠️ FUTUROS (REAL) SIN SL/TP: entrada ejecutada, fallo protección: {e}"
            else:
                logger.warning("EXECUTION_MODE_REAL_SPOT", "Ejecutando orden en Binance Spot (REAL).")
                await safe_send_message(bot_instance, chat_id, f"⚠️ Ejecutando orden REAL Spot: {tipo_operacion} {cantidad_token} {symbol}...")
                try:
                    entrada_res = await retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger)(
                        lambda: asyncio.to_thread(
                            client.create_order,
                            symbol=symbol,
                            side=tipo_operacion,
                            type="MARKET",
                            quantity=cantidad_token,
                        )
                    )()
                    orden_entrada = await entrada_res if inspect.isawaitable(entrada_res) else entrada_res
                    logger.info("ENTRY_ORDER_SUCCESS", "Orden de entrada ejecutada.", details=orden_entrada)
                except BinanceAPIException as e:
                    logger.error("BINANCE_API_ERROR", f"Error al crear orden: {e}")
                    await safe_send_message(bot_instance, chat_id, f"❌ Error de Binance: {e}")
                    return "Error de Binance."
                except aiohttp.ClientError as e:
                    logger.error("AIOHTTP_ERROR", f"Error de conexión: {e}")
                    await safe_send_message(bot_instance, chat_id, f"❌ Error de conexión: {e}")
                    return "Error de conexión."

                entry_order_id = orden_entrada.get('orderId')
                entry_order_status = orden_entrada.get('status')
                if 'cummulativeQuoteQty' in orden_entrada and 'executedQty' in orden_entrada and float(orden_entrada['executedQty']) > 0:
                    final_entry_price = float(orden_entrada['cummulativeQuoteQty']) / float(orden_entrada['executedQty'])
                else:
                    logger.warning("REAL_ENTRY_PRICE_FALLBACK", "No se pudo calcular precio de entrada real. Usando precio de ticker.", details=orden_entrada)

                price_tick_size = next((f['tickSize'] for f in symbol_info.get('filters', []) if f.get('filterType') == 'PRICE_FILTER'), '0.0')
                if stop_loss is not None:
                    sl_pct = float(stop_loss)
                else:
                    try:
                        sl_pct = float(getattr(getattr(config, 'settings', object()), 'RISK_PER_TRADE_STOP_LOSS_PCT'))
                    except Exception:
                        sl_pct = 2.0
                if take_profit is not None:
                    tp_pct = float(take_profit)
                else:
                    try:
                        tp_pct = float(getattr(getattr(config, 'settings', object()), 'RISK_PER_TRADE_TAKE_PROFIT_PCT'))
                    except Exception:
                        tp_pct = 4.0

                if tipo_operacion == 'BUY':
                    sl_price = _round_to_tick_size(final_entry_price * (1 - sl_pct / 100), price_tick_size)
                    tp_price = _round_to_tick_size(final_entry_price * (1 + tp_pct / 100), price_tick_size)
                    oco_side = 'SELL'
                else:
                    sl_price = _round_to_tick_size(final_entry_price * (1 + sl_pct / 100), price_tick_size)
                    tp_price = _round_to_tick_size(final_entry_price * (1 - tp_pct / 100), price_tick_size)
                    oco_side = 'BUY'

                await safe_send_message(bot_instance, chat_id, f"… colocando orden OCO (SL: {sl_price:.4f}, TP: {tp_price:.4f})...")
                oco_res = await retry((BinanceAPIException, BinanceRequestException), tries=3, delay=2, logger=logger)(
                    lambda: asyncio.to_thread(
                        client.create_oco_order,
                        symbol=symbol,
                        side=oco_side,
                        quantity=cantidad_token,
                        price=tp_price,
                        stopPrice=sl_price,
                    )
                )()
                orden_oco = await oco_res if inspect.isawaitable(oco_res) else oco_res
                logger.info("OCO_ORDER_SUCCESS", "Orden OCO (SL/TP) colocada.", details=orden_oco)
                oco_order_list_id = orden_oco.get('orderListId')
                mensaje_ejecucion = f"✅ ORDEN REAL EJECUTADA y PROTEGIDA (OCO):\n- Entrada: {tipo_operacion} {cantidad_token} {symbol} @ ~{final_entry_price:.4f}\n- SL: {sl_price:.4f}\n- TP: {tp_price:.4f}"
        else:
            logger.info("SIMULATED_TRADE_EXECUTION", "Ejecutando orden en MODO SIMULADO.")
            slippage_pct = random.uniform(-0.05, 0.05)
            final_entry_price = precio_actual * (1 + slippage_pct / 100)
            fee_pct = 0.1
            fee_usdt = cantidad_usdt * fee_pct / 100
            mensaje_ejecucion = f"⚙️ ORDEN SIMULADA: {tipo_operacion} {cantidad_token} {symbol} a {final_entry_price:.2f} USDT (slippage {slippage_pct:+.3f}%, fee {fee_usdt:.2f} USDT)."
            ganancia_pct_operacion = random.uniform(-3, 5) - fee_pct
            registrar_resultado_operacion(ganancia_pct_operacion)

        log_data = {
            "operation_id": operation_id,
            "timestamp_open": timestamp,
            "timestamp_close": None,
            "symbol": symbol,
            "side": tipo_operacion,
            "entry_price": final_entry_price,
            "exit_price": None,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "size_usdt": cantidad_usdt,
            "risk_percent": riesgo_pct,
            "mode": trade_mode_actual,
            "pnl_usdt": None,
            "pnl_percent": ganancia_pct_operacion,
            "reason_open": decision,
            "reason_close": None,
            "market_score_open": score_ml,
            "market_score_close": None,
            "version_bot": "1.0.0",
            "notes": f"slippage={slippage_pct:.3f}%",
            "balance_usdt_al_abrir": balance,
            "escudo_activo_al_abrir": escudo_activo(),
            "tipo_escudo_al_abrir": escudo_activo(),
            "riesgo_forzado_al_abrir": riesgo_forzado_activo(),
            "cantidad_token_operada": cantidad_token,
            "min_notional_filter": min_notional_val,
            "step_size_filter": step_size_val,
            "price_tick_size_filter": price_tick_size_val,
            "slippage_apertura_pct": slippage_pct,
            "order_id_binance": entry_order_id,
            "order_status_binance": entry_order_status,
            "oco_order_list_id": oco_order_list_id,
            "cost_spread_usdt": coste_spread_usdt,
            "cost_commission_usdt": coste_comision_usdt,
            "cost_total_usdt": coste_total_usdt,
        }
        await registrar_operacion(bot_instance, chat_id, log_data)

        if exec_target == 'CTRADER':
            await safe_send_message(bot_instance, chat_id, mensaje_ejecucion)
        elif trade_mode_actual == "SIMULATED":
            await safe_send_message(bot_instance, chat_id, mensaje_ejecucion + f" Resultado simulado: {ganancia_pct_operacion:+.2f}%")
        else:
            await safe_send_message(bot_instance, chat_id, mensaje_ejecucion)
        await mostrar_estado_riesgo(bot_instance, chat_id)
        return "Operación procesada."
    except Exception as e:
        logger.error("UNEXPECTED_ERROR", f"Error inesperado en ejecución de orden: {e}")
        return "Error inesperado."

