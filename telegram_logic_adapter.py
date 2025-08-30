# telegram_logic_adapter.py

"""
Módulo Adaptador de Lógica para Telegram.

Este archivo actúa como un puente entre los handlers de la interfaz de Telegram
y la lógica de negocio principal del bot ITBOT. Reemplaza los stubs
y llama a los módulos reales para obtener datos y ejecutar acciones.
"""

import asyncio
import time
from datetime import datetime, time as dt_time
from typing import Dict, Any, List, Optional, cast
import pandas as pd
from sqlalchemy import text
import redis
from telegram import Bot
from logging_config import get_logger

# --- Importaciones del núcleo de ITBOT ---
from utils.structured_logger import StructuredLogger
from utils.state_manager import StateManager
from utils.position_manager import get_open_positions, get_open_positions_summary as get_pos_summary_from_manager
from database.database_manager import get_db_session, get_klines
from utils.technical_analysis import RegimeDetector
from utils.binance_client import get_binance_client, close_binance_client
from utils.order_executor import evaluar_y_ejecutar_operacion
from config import settings
from utils.shield_manager import obtener_estado_escudo
from utils.risk_manager import restaurar_riesgo_automatico, activar_riesgo_forzado

logger = StructuredLogger(__name__)
state_manager = StateManager()

# --- Helpers de normalización de modo ---
def _normalize_mode(val: str) -> str:
    if not isinstance(val, str):
        return "PAPER_TRADING"
    v = val.strip().lower()
    if v in ("live",):
        return "LIVE"
    if v in ("paper", "paper_trading", "sim", "simulated", "papertrading"):
        return "PAPER_TRADING"
    # Fallback seguro
    return val.upper() if val else "PAPER_TRADING"

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
        logger.error("DB_QUERY_ERROR", f"Error al contar operaciones diarias: {e}", exc_info=True)
        return -1 # Devolver un valor que indique error

async def get_last_sync_time() -> str:
    """Obtiene el timestamp de la última sincronización de los workers."""
    try:
        r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True)
        analysis_heartbeat = r.get("heartbeat:analysis_bot")
        worker_heartbeat = r.get("heartbeat:execution_worker")
        
        def _to_int(x: Any) -> Optional[int]:
            try:
                if x is None:
                    return None
                if isinstance(x, (int, float)):
                    return int(x)
                s = str(x).strip()
                return int(s)
            except Exception:
                return None
        
        last_sync = 0
        ahb = _to_int(analysis_heartbeat)
        whb = _to_int(worker_heartbeat)
        if ahb is not None:
            last_sync = max(last_sync, ahb)
        if whb is not None:
            last_sync = max(last_sync, whb)

        if last_sync > 0:
            return datetime.fromtimestamp(last_sync).strftime('%Y-%m-%d %H:%M:%S')
        return "Nunca"
    except Exception as e:
        logger.error("REDIS_ERROR", f"Error al obtener tiempo de sync de Redis: {e}", exc_info=True)
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

# --- Funciones para acciones de botones ---

async def get_open_positions_summary(bot: Any) -> str:
    """Obtiene un resumen de las posiciones abiertas."""
    return await get_pos_summary_from_manager(bot)

def get_shield_status() -> str:
    """Obtiene el estado de los escudos."""
    _, status_text = obtener_estado_escudo()
    return status_text

def set_risk_auto() -> None:
    """Establece el modo de riesgo a automático."""
    restaurar_riesgo_automatico()
    logger.info("RISK_MODE_CHANGED", "Risk mode set to AUTO by user.", details={"mode": "auto"})

def set_risk_manual(percentage: float) -> None:
    """Establece el modo de riesgo a manual con un porcentaje fijo."""
    activar_riesgo_forzado(percentage)
    logger.info("RISK_MODE_CHANGED", f"Risk mode set to MANUAL with {percentage}% by user.", details={"mode": "manual", "percentage": percentage})


async def get_consolidated_status() -> Dict[str, Any]:
    """Obtiene un estado consolidado del bot llamando a los módulos reales."""
    try:
        open_pos_df = get_open_positions()
        shield_status = state_manager.get_state("shield_manager", default_value={})
        risk_status = state_manager.get_state("risk_manager", default_value={})
        paused = state_manager.get_state("system", "is_paused", False)

        status = {
            "mode": _normalize_mode(state_manager.get_state("session", "mode", settings.MODE)),
            "running": True,  # Si el bot de telegram responde, está activo.
            "is_paused": bool(paused),
            "shield_status": shield_status,
            "open_positions": len(open_pos_df),
            "total_pnl_percent": 0.0,  # Placeholder
            "daily_pnl_percent": 0.0,  # Placeholder
            "risk_mode": "FORZADO" if risk_status.get("riesgo_forzado") else "AUTOMATICO",
            "model_id": settings.ML_MODEL_ID,
            "market_regime": await get_market_regime(),
        }
        return status
    except Exception as e:
        logger.error("STATUS_ERROR", f"Error al consolidar estado: {e}", exc_info=True)
        return {"error": str(e)}

async def get_open_trades() -> List[Dict[str, Any]]:
    """Obtiene la lista de operaciones abiertas desde el position_manager."""
    try:
        positions_df = get_open_positions()
        if positions_df.empty:
            return []
        return cast(List[Dict[str, Any]], positions_df.to_dict(orient='records'))
    except Exception as e:
        logger.error("POSITION_ERROR", f"Error al obtener trades abiertos: {e}", exc_info=True)
        return []

async def get_bot_mode() -> str:
    """Obtiene el modo actual del bot desde el state_manager."""
    return _normalize_mode(state_manager.get_state("session", "mode", settings.MODE))

async def set_bot_mode(mode: str) -> bool:
    """Establece el modo del bot en el state_manager."""
    norm = _normalize_mode(mode)
    if norm in ["LIVE", "PAPER_TRADING"]:
        state_manager.set_state("session", "mode", norm)
        logger.info("BOT_MODE_CHANGED", f"Modo del bot cambiado a: {mode}", details={"mode": mode})
        return True
    logger.warning("INVALID_BOT_MODE", f"Intento de cambiar a modo inválido: {mode}", details={"invalid_mode": mode})
    return False

async def get_last_discarded_signals() -> List[Dict[str, Any]]:
    """Obtiene las últimas señales descartadas desde la base de datos."""
    try:
        with get_db_session() as session:
            query = text("SELECT * FROM discarded_signals ORDER BY timestamp DESC LIMIT 5")
            assert session.bind is not None
            df = pd.read_sql(query, session.bind)
        return cast(List[Dict[str, Any]], df.to_dict(orient='records'))
    except Exception as e:
        logger.error("DB_QUERY_ERROR", f"Error al obtener señales descartadas: {e}", exc_info=True)
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
        logger.error("ANALYSIS_ERROR", f"Error al detectar régimen de mercado: {e}", exc_info=True)
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
        def _to_int(x: Any) -> Optional[int]:
            try:
                if x is None:
                    return None
                if isinstance(x, (int, float)):
                    return int(x)
                s = str(x).strip()
                return int(s)
            except Exception:
                return None

        ahb = _to_int(analysis_heartbeat)
        if ahb is not None and (time.time() - ahb < HEARTBEAT_TOLERANCE_SECONDS):
            health["Analysis Bot"] = "ACTIVE"
        else:
            health["Analysis Bot"] = "INACTIVE/STALLED"

        worker_heartbeat = r.get("heartbeat:execution_worker")
        whb = _to_int(worker_heartbeat)
        if whb is not None and (time.time() - whb < HEARTBEAT_TOLERANCE_SECONDS):
            health["Execution Worker"] = "ACTIVE"
        else:
            health["Execution Worker"] = "INACTIVE/STALLED"

    except Exception as e:
        health["Redis Queue"] = f"ERROR: {e}"
        health["Analysis Bot"] = "UNKNOWN (Redis Error)"
        health["Execution Worker"] = "UNKNOWN (Redis Error)"
    
    return health

async def execute_kill_switch() -> Dict[str, Any]:
    """
    Liquida todas las posiciones abiertas de forma robusta, con reintentos,
    y devuelve un resumen de la operación.
    """
    logger.warning("KILL_SWITCH_START", "¡¡¡SECUENCIA DE KILL SWITCH INICIADA!!!")

    results = {
        "success": True,
        "closed_positions": [],
        "failed_positions": []
    }

    try:
        open_positions = get_open_positions()
        if open_positions.empty:
            logger.info("KILL_SWITCH_SKIP", "No hay posiciones abiertas para liquidar.")
            return results
        
        client = await get_binance_client()

        for _, position in open_positions.iterrows():
            symbol = position['symbol']
            quantity = position['cantidad_token_operada']
            side = position['side']
            close_side = "SELL" if side == "LONG" else "BUY"
            
            for attempt in range(2): # Intentar 2 veces (1 original + 1 reintento)
                try:
                    logger.info(
                        "KILL_SWITCH_CLOSE_ATTEMPT",
                        f"Intento {attempt + 1}: Cerrando {symbol} ({quantity} {close_side})",
                        details=position.to_dict()
                    )
                    await client.create_order(symbol=symbol, side=close_side, type="MARKET", quantity=quantity)
                    results["closed_positions"].append(position.to_dict())
                    logger.info("KILL_SWITCH_CLOSE_SUCCESS", f"Posición {symbol} cerrada con éxito.")
                    break # Salir del bucle de reintentos si tiene éxito
                except Exception as e:
                    logger.error(
                        "KILL_SWITCH_CLOSE_ERROR",
                        f"Fallo en intento {attempt + 1} al cerrar {symbol}: {e}",
                        details={"attempt": attempt + 1, **position.to_dict()},
                        exc_info=True
                    )
                    if attempt == 1: # Si es el segundo intento (el reintento) y falla
                        results["failed_positions"].append(position.to_dict())
                        results["success"] = False
                    else:
                        await asyncio.sleep(1) # Esperar 1 segundo antes de reintentar

        if results["success"]:
            logger.warning("KILL_SWITCH_COMPLETE", "Kill Switch completado con éxito. Todas las posiciones cerradas.")
        else:
            logger.critical("KILL_SWITCH_PARTIAL_FAILURE", "Kill Switch completado con fallos.", details=results)
            
    except Exception as e:
        logger.critical("KILL_SWITCH_FATAL_ERROR", f"Error crítico durante la ejecución del Kill Switch: {e}", exc_info=True)
        results["success"] = False

    return results

async def atomic_kill_switch() -> Dict[str, Any]:
    """
    Activa el kill switch de forma atómica: primero pausa el sistema y LUEGO
    liquida todas las posiciones para asegurar que no entren nuevas operaciones
    durante el proceso.
    """
    logger.critical("ATOMIC_KILL_SWITCH", "Secuencia de Kill Switch Atómico iniciada por un usuario.")

    # 1. Pausar el sistema para prevenir cualquier nueva operación de forma inmediata.
    await full_system_stop()
    logger.info("ATOMIC_KILL_SWITCH_STEP", "Paso 1/2: Sistema pausado. No se crearán nuevas órdenes.")

    # 2. Liquidar todas las posiciones abiertas existentes.
    logger.info("ATOMIC_KILL_SWITCH_STEP", "Paso 2/2: Iniciando liquidación de todas las posiciones abiertas.")
    liquidation_results = await execute_kill_switch()

    logger.critical("ATOMIC_KILL_SWITCH_COMPLETE", "Secuencia de Kill Switch Atómico finalizada.", details=liquidation_results)

    return liquidation_results


async def full_system_stop() -> bool:
    """Pone el bot en estado de pausa, deteniendo la creación de nuevas órdenes."""
    logger.warning("SYSTEM_PAUSE", "Iniciando pausa del sistema. No se crearán nuevas operaciones.")
    state_manager.set_state("system", "is_paused", True)
    return True

async def resume_system() -> bool:
    """Reanuda la operativa del bot."""
    logger.warning("SYSTEM_RESUME", "Reanudando la operativa del sistema.")
    state_manager.set_state("system", "is_paused", False)
    return True
