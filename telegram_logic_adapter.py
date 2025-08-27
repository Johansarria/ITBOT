# telegram_logic_adapter.py

"""
Módulo Adaptador de Lógica para Telegram.

Este archivo actúa como un puente entre los handlers de la interfaz de Telegram
y la lógica de negocio principal del bot ITBOT. Reemplaza los stubs
y llama a los módulos reales para obtener datos y ejecutar acciones.
"""

import asyncio
import logging
import time
from datetime import datetime, time as dt_time
from typing import Dict, Any, List
import pandas as pd
from sqlalchemy import text

# --- Importaciones del núcleo de ITBOT ---
from utils.state_manager import StateManager
from utils.position_manager import get_open_positions
from database.database_manager import get_db_session, get_klines
from utils.technical_analysis import RegimeDetector
from utils.binance_client import get_binance_client, close_binance_client
from utils.order_executor import evaluar_y_ejecutar_operacion
from config import settings
import redis

logger = logging.getLogger(__name__)
state_manager = StateManager()

# --- Nuevas funciones para el resumen del menú principal ---

async def get_risk_capital() -> str:
    """Obtiene el capital en riesgo actual."""
    risk_status = state_manager.get_state("risk_manager", default_value={})
    if risk_status.get("riesgo_forzado") and "porcentaje_forzado" in risk_status:
        return f"{risk_status['porcentaje_forzado']:.2f}% (Manual)"
    return f"{settings.DEFAULT_RISK_PERCENTAGE:.2f}% (Auto)"

async def get_daily_operations_count() -> int:
    """Cuenta las operaciones realizadas hoy."""
    try:
        with get_db_session() as session:
            today = datetime.utcnow().date()
            start_of_day = datetime.combine(today, dt_time.min)
            query = text("SELECT COUNT(*) FROM operations WHERE timestamp_open >= :start_of_day")
            result = session.execute(query, {"start_of_day": start_of_day}).scalar_one_or_none()
            return result or 0
    except Exception as e:
        logger.error(f"Error al contar operaciones diarias: {e}", exc_info=True)
        return -1 # Devolver un valor que indique error

async def get_last_sync_time() -> str:
    """Obtiene el timestamp de la última sincronización de los workers."""
    try:
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)
        analysis_heartbeat = r.get("heartbeat:analysis_bot")
        worker_heartbeat = r.get("heartbeat:execution_worker")
        
        last_sync = 0
        if analysis_heartbeat:
            last_sync = max(last_sync, int(analysis_heartbeat))
        if worker_heartbeat:
            last_sync = max(last_sync, int(worker_heartbeat))

        if last_sync > 0:
            return datetime.fromtimestamp(last_sync).strftime('%Y-%m-%d %H:%M:%S')
        return "Nunca"
    except Exception as e:
        logger.error(f"Error al obtener tiempo de sync: {e}", exc_info=True)
        return "Error"

async def get_main_menu_summary() -> Dict[str, Any]:
    """Recopila todos los datos para el nuevo resumen del menú principal."""
    risk_capital = await get_risk_capital()
    daily_ops = await get_daily_operations_count()
    last_sync = await get_last_sync_time()
    bot_version = settings.ML_MODEL_ID

    return {
        "risk_capital": risk_capital,
        "daily_operations": f"{daily_ops}/{settings.MAX_DAILY_OPERATIONS}",
        "last_sync": last_sync,
        "bot_version": bot_version
    }

# --- Implementaciones Anteriores (Conservadas por si son necesarias en otros menús) ---

async def get_consolidated_status() -> Dict[str, Any]:
    """Obtiene un estado consolidado del bot llamando a los módulos reales."""
    try:
        open_pos_df = get_open_positions()
        shield_status = state_manager.get_state("shield_manager", default_value={})
        risk_status = state_manager.get_state("risk_manager", default_value={})

        status = {
            "mode": state_manager.get_state("session", "mode", "paper"),
            "running": True, # Si el bot de telegram responde, está activo.
            "shield_status": shield_status,
            "open_positions": len(open_pos_df),
            "total_pnl_percent": 0.0, # Placeholder
            "daily_pnl_percent": 0.0, # Placeholder
            "risk_mode": "FORZADO" if risk_status.get("riesgo_forzado") else "AUTOMATICO",
            "model_id": settings.ML_MODEL_ID,
            "market_regime": await get_market_regime(),
        }
        return status
    except Exception as e:
        logger.error(f"Error al consolidar estado: {e}", exc_info=True)
        return {"error": str(e)}

async def get_open_trades() -> List[Dict[str, Any]]:
    """Obtiene la lista de operaciones abiertas desde el position_manager."""
    try:
        positions_df = get_open_positions()
        if positions_df.empty:
            return []
        return positions_df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error al obtener trades abiertos: {e}", exc_info=True)
        return []

async def get_bot_mode() -> str:
    """Obtiene el modo actual del bot desde el state_manager."""
    return state_manager.get_state("session", "mode", "paper")

async def set_bot_mode(mode: str) -> bool:
    """Establece el modo del bot en el state_manager."""
    if mode in ["LIVE", "PAPER_TRADING"]:
        state_manager.set_state("session", "mode", mode)
        logger.info(f"Modo del bot cambiado a: {mode}")
        return True
    logger.warning(f"Intento de cambiar a modo inválido: {mode}")
    return False

async def get_last_discarded_signals() -> List[Dict[str, str]]:
    """Obtiene las últimas señales descartadas desde la base de datos."""
    try:
        with get_db_session() as session:
            query = text("SELECT * FROM discarded_signals ORDER BY timestamp DESC LIMIT 5")
            df = pd.read_sql(query, session.bind)
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Error al obtener señales descartadas: {e}", exc_info=True)
        return []

async def get_market_regime() -> str:
    """Obtiene el régimen de mercado actual para el activo principal."""
    try:
        symbol = settings.ASSETS_TO_TRADE[0] if settings.ASSETS_TO_TRADE else "BTCUSDT"
        klines_df = get_klines(symbol=symbol, interval=settings.INTERVAL, limit=100)
        if klines_df.empty:
            return "DATA_INSUFFICIENT"
        
        detector = RegimeDetector(klines_df)
        return detector.get_market_regime()
    except Exception as e:
        logger.error(f"Error al detectar régimen de mercado: {e}", exc_info=True)
        return "ERROR"

async def get_ml_model_status() -> Dict[str, Any]:
    """Obtiene el estado del modelo de ML en producción."""
    return {
        "model_id": settings.ML_MODEL_ID,
        "last_retrained": "N/A",
        "performance_drift": "NOT_MONITORED",
        "next_training_scheduled": "N/A",
    }

async def check_services_health() -> Dict[str, str]:
    """Verifica la salud de los servicios críticos del bot."""
    health = {}
    HEARTBEAT_TOLERANCE_SECONDS = settings.ANALYSIS_INTERVAL_SECONDS * 2.5

    try:
        client = await get_binance_client()
        await client.ping()
        health["Binance API"] = "OPERATIONAL"
    except Exception as e:
        health["Binance API"] = f"ERROR: {e}"

    try:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        health["Database Connection"] = "OPERATIONAL"
    except Exception as e:
        health["Database Connection"] = f"ERROR: {e}"

    try:
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)
        r.ping()
        health["Redis Queue"] = "OPERATIONAL"

        analysis_heartbeat = r.get("heartbeat:analysis_bot")
        if analysis_heartbeat and (time.time() - int(analysis_heartbeat) < HEARTBEAT_TOLERANCE_SECONDS):
            health["Analysis Bot"] = "ACTIVE"
        else:
            health["Analysis Bot"] = "INACTIVE/STALLED"

        worker_heartbeat = r.get("heartbeat:execution_worker")
        if worker_heartbeat and (time.time() - int(worker_heartbeat) < HEARTBEAT_TOLERANCE_SECONDS):
            health["Execution Worker"] = "ACTIVE"
        else:
            health["Execution Worker"] = "INACTIVE/STALLED"

    except Exception as e:
        health["Redis Queue"] = f"ERROR: {e}"
        health["Analysis Bot"] = "UNKNOWN (Redis Error)"
        health["Execution Worker"] = "UNKNOWN (Redis Error)"
    
    return health

async def liquidate_all_positions() -> bool:
    """Liquida todas las posiciones abiertas."""
    logger.warning("¡¡¡INICIANDO SECUENCIA DE LIQUIDACIÓN TOTAL!!!")
    try:
        open_positions = get_open_positions()
        if open_positions.empty:
            logger.info("No hay posiciones abiertas para liquidar.")
            return True
        
        client = await get_binance_client()
        for _, position in open_positions.iterrows():
            symbol = position['symbol']
            quantity = position['cantidad_token_operada']
            side = position['side']
            
            close_side = "SELL" if side == "LONG" else "BUY"
            
            logger.info(f"Cerrando posición para {symbol}: Orden {close_side} de {quantity} tokens.")
            
            await client.create_order(
                symbol=symbol,
                side=close_side,
                type="MARKET",
                quantity=quantity
            )
        logger.warning("¡¡¡LIQUIDACIÓN TOTAL COMPLETADA!!!")
        return True
    except Exception as e:
        logger.error(f"Error crítico durante la liquidación total: {e}", exc_info=True)
        return False

async def full_system_stop() -> bool:
    """Detiene la creación de nuevas órdenes en el bot."""
    logger.warning("¡¡¡PAUSA TOTAL DEL SISTEMA INICIADA!!!")
    state_manager.set_state("system", "is_running", False)
    return True
