from utils.audit_db import log_decision_to_db

import asyncio
import logging
import sys
import os
import time # Importar time
import redis # Importar redis
from typing import Any, Dict, Optional

# Asegura que el root del proyecto esté en sys.path para ejecución directa
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from config import settings
from utils.message_queue import mq
from utils.order_executor import evaluar_y_ejecutar_operacion
from utils.risk_manager import perform_pre_execution_risk_checks
from utils.state_manager import StateManager
from utils.structured_logger import StructuredLogger
from utils.logger_setup import setup_logging
import uuid

# Configurar el logging centralizado al inicio
setup_logging()
logger = StructuredLogger(__name__)

state_manager = StateManager()


async def process_decision(decision: Dict[str, Any]) -> None:
    """
    Procesa una decisión de trading recibida desde la cola.
    1. Valida la estructura de la decisión.
    2. Realiza chequeos de riesgo previos a la ejecución.
    3. Ejecuta la orden usando la lógica central del bot.
    Args:
        decision (Dict[str, Any]): Diccionario con los datos de la decisión de trading.
    """
    trade_id = str(uuid.uuid4())
    symbol = decision.get('symbol', 'UNKNOWN')
    logger.info(
        "DECISION_RECEIVED",
        f"Procesando decisión: {decision.get('type', 'N/A')} para {symbol}",
        details={"trade_id": trade_id, **decision}
    )

    # 1. Validación de estructura mínima, dependiente del tipo
    decision_type = str(decision.get("type", "")).upper()
    trade_types = {"AUTOMATED_TRADE", "MANUAL_TRADE", "TRADE"}
    if decision_type not in trade_types:
        # Tipos no ejecutables por este worker: registramos y salimos sin error
        logger.info(
            "DECISION_SKIPPED",
            f"Tipo de decisión no ejecutable por el worker: {decision_type}",
            details={"trade_id": trade_id, **decision}
        )
        return

    # Para decisiones de trade, exigimos campos mínimos y completamos defaults si faltan
    required_keys = {"type", "symbol", "side", "quantity"}
    missing_keys = required_keys - decision.keys()

    # Log a base de datos (Postgres/Timescale)
    # This part can be simplified or removed if the structured log is the single source of truth
    # For now, we keep it but ensure it's robust.
    db_log_payload = {
        "trade_id": trade_id,
        "symbol": symbol,
        "type": decision.get("type"),
        "side": decision.get("side"),
        "quantity": decision.get("quantity"),
        "strategy_id": decision.get("strategy_id"),
        "timestamp_decision": decision.get("timestamp_decision"),
        "features": decision.get("features", {}),
        "score": decision.get("analysis_score"),
        "thresholds": decision.get("thresholds", {}),
        "reason": decision.get("reason", "N/A"),
        "model_version": decision.get("model_version", "N/A"),
        "result": None,
        "error": None
    }
    log_decision_to_db(db_log_payload)

    if missing_keys:
        error_msg = f"Decisión inválida: faltan claves requeridas {missing_keys}."
        logger.error(
            "DECISION_INVALID",
            error_msg,
            details={"trade_id": trade_id, "missing_keys": list(missing_keys), "decision": decision}
        )
        db_log_payload["error"] = error_msg
        log_decision_to_db(db_log_payload)
        return

    # Defaults opcionales para mayor robustez
    if not decision.get("timestamp_decision"):
        from datetime import datetime
        decision["timestamp_decision"] = datetime.utcnow().isoformat()
    if not decision.get("strategy_id"):
        decision["strategy_id"] = "unknown"

    # 2. Chequeos de riesgo previos a la ejecución
    try:
        risk_passed, risk_reason = await perform_pre_execution_risk_checks(decision)
    except Exception as e:
        error_msg = f"Error en chequeo de riesgo: {e}"
        logger.error("RISK_CHECK_ERROR", error_msg, details={"trade_id": trade_id, "decision": decision}, exc_info=True)
        db_log_payload["error"] = error_msg
        log_decision_to_db(db_log_payload)
        return

    if not risk_passed:
        rejection_msg = f"Decisión rechazada por riesgo: {risk_reason}."
        logger.warning(
            "DECISION_RISK_REJECTED",
            rejection_msg,
            details={"trade_id": trade_id, "risk_reason": risk_reason, "decision": decision}
        )
        db_log_payload["error"] = f"risk_rejected: {risk_reason}"
        log_decision_to_db(db_log_payload)
        return

    # 3. Ejecución de la orden
    try:
        resultado_analisis = {
            "symbol": decision["symbol"],
            "decision": decision.get("decision") or decision["side"],
            "score": decision.get("analysis_score"),
            "strategy_name": decision.get("strategy_id", "UnknownStrategy"),
        }
        execution_message = await evaluar_y_ejecutar_operacion(
            bot_instance=None,
            chat_id=None,
            resultado_analisis=resultado_analisis,
            take_profit=decision.get("take_profit"),
            stop_loss=decision.get("stop_loss")
        )
        logger.info(
            "ORDER_EXECUTED",
            f"Resultado de la ejecución de orden: {execution_message}",
            details={"trade_id": trade_id, "result": execution_message, **decision}
        )
        db_log_payload["result"] = execution_message
        log_decision_to_db(db_log_payload)

    except Exception as e:
        error_msg = f"Excepción durante la ejecución de la orden: {e}"
        logger.error("ORDER_EXECUTION_ERROR", error_msg, details={"trade_id": trade_id, "decision": decision}, exc_info=True)
        db_log_payload["error"] = error_msg
        log_decision_to_db(db_log_payload)


async def main() -> None:
    """
    Bucle principal del worker de ejecución. Espera y procesa decisiones de la cola de mensajes.
    """
    logger.info("WORKER_START", "Worker de ejecución iniciado. Esperando decisiones...")
    
    # Conexión a Redis para Heartbeat
    try:
        redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
        redis_client.ping() # Verificar conexión
        logger.info("REDIS_CONNECT_SUCCESS", "Conexión con Redis para heartbeat del worker establecida.")
    except redis.ConnectionError as e:
        logger.critical("REDIS_CONNECT_ERROR", f"No se pudo conectar a Redis para el heartbeat del worker: {e}", exc_info=True)
        redis_client = None

    while True:
        # Enviar Heartbeat
        if redis_client:
            try:
                redis_client.set("heartbeat:execution_worker", int(time.time()))
            except redis.RedisError as e:
                logger.error("REDIS_HEARTBEAT_ERROR", f"No se pudo enviar el heartbeat del worker a Redis: {e}", exc_info=True)

        try:
            decision = mq.get_decision() # Este es un llamado bloqueante con timeout
            if decision:
                await process_decision(decision)
            else:
                # Si get_decision devuelve None (por timeout), el bucle continúa y envía un nuevo heartbeat.
                pass
        except Exception as e:
            logger.error("WORKER_LOOP_ERROR", f"Error en el bucle principal del worker: {e}", exc_info=True)
            await asyncio.sleep(5) # Esperar antes de reintentar en caso de error

def run_worker() -> None:
    """
    Punto de entrada para lanzar el worker desde otros scripts o CLI.
    """
    asyncio.run(main())

if __name__ == "__main__":
    run_worker()