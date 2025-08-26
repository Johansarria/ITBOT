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
from utils.structured_logger import setup_structured_logger
import uuid


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Logger estructurado para auditoría de decisiones
structured_logger = setup_structured_logger("logs/decisions_structured.log")

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
    logger.info(f"Procesando decisión: {decision.get('type', 'UNKNOWN')} para {decision.get('symbol')}")

    # 1. Validación de estructura mínima
    required_keys = {"type", "symbol", "side", "quantity", "strategy_id", "timestamp_decision"}
    missing = required_keys - decision.keys()
    trade_id = str(uuid.uuid4())
    model_version = decision.get("model_version", "N/A")
    features = decision.get("features", {})
    score = decision.get("analysis_score", None)
    thresholds = decision.get("thresholds", {})
    reason = decision.get("reason", "N/A")
    # Log a base de datos (Postgres/Timescale)
    log_decision_to_db({
        "trade_id": trade_id,
        "symbol": decision.get("symbol"),
        "type": decision.get("type"),
        "side": decision.get("side"),
        "quantity": decision.get("quantity"),
        "strategy_id": decision.get("strategy_id"),
        "timestamp_decision": decision.get("timestamp_decision"),
        "features": features,
        "score": score,
        "thresholds": thresholds,
        "reason": reason,
        "model_version": model_version,
        "result": None,
        "error": None
    })
    structured_logger.info(
        "decision_received",
        extra={
            "extra": {
                "event": "decision_received",
                "trade_id": trade_id,
                "symbol": decision.get("symbol"),
                "type": decision.get("type"),
                "side": decision.get("side"),
                "quantity": decision.get("quantity"),
                "strategy_id": decision.get("strategy_id"),
                "timestamp_decision": decision.get("timestamp_decision"),
                "features": features,
                "score": score,
                "thresholds": thresholds,
                "reason": reason,
                "model_version": model_version
            }
        }
    )
    if missing:
        logger.error(f"Decisión inválida: faltan claves requeridas {missing}. Decisión: {decision}")
        structured_logger.info(
            "decision_invalid",
            extra={
                "extra": {
                    "event": "decision_invalid",
                    "trade_id": trade_id,
                    "missing_keys": list(missing),
                    "decision": decision
                }
            }
        )
        log_decision_to_db({
            "trade_id": trade_id,
            "symbol": decision.get("symbol"),
            "type": decision.get("type"),
            "side": decision.get("side"),
            "quantity": decision.get("quantity"),
            "strategy_id": decision.get("strategy_id"),
            "timestamp_decision": decision.get("timestamp_decision"),
            "features": features,
            "score": score,
            "thresholds": thresholds,
            "reason": reason,
            "model_version": model_version,
            "result": None,
            "error": f"missing_keys: {missing}"
        })
        return

    # 2. Chequeos de riesgo previos a la ejecución
    try:
        risk_passed, risk_reason = await perform_pre_execution_risk_checks(decision)
    except Exception as e:
        logger.error(f"Error en chequeo de riesgo: {e}", exc_info=True)
        structured_logger.info(
            "risk_check_error",
            extra={
                "extra": {
                    "event": "risk_check_error",
                    "trade_id": trade_id,
                    "error": str(e),
                    "decision": decision
                }
            }
        )
        log_decision_to_db({
            "trade_id": trade_id,
            "symbol": decision.get("symbol"),
            "type": decision.get("type"),
            "side": decision.get("side"),
            "quantity": decision.get("quantity"),
            "strategy_id": decision.get("strategy_id"),
            "timestamp_decision": decision.get("timestamp_decision"),
            "features": features,
            "score": score,
            "thresholds": thresholds,
            "reason": reason,
            "model_version": model_version,
            "result": None,
            "error": str(e)
        })
        return
    if not risk_passed:
        logger.warning(f"Decisión rechazada por riesgo: {risk_reason}. Decisión: {decision}")
        structured_logger.info(
            "decision_risk_rejected",
            extra={
                "extra": {
                    "event": "decision_risk_rejected",
                    "trade_id": trade_id,
                    "risk_reason": risk_reason,
                    "decision": decision
                }
            }
        )
        log_decision_to_db({
            "trade_id": trade_id,
            "symbol": decision.get("symbol"),
            "type": decision.get("type"),
            "side": decision.get("side"),
            "quantity": decision.get("quantity"),
            "strategy_id": decision.get("strategy_id"),
            "timestamp_decision": decision.get("timestamp_decision"),
            "features": features,
            "score": score,
            "thresholds": thresholds,
            "reason": reason,
            "model_version": model_version,
            "result": None,
            "error": f"risk_rejected: {risk_reason}"
        })
        return

    # 3. Ejecución de la orden
    try:
        resultado_analisis = {
            "symbol": decision["symbol"],
            "decision": decision["side"],
            "score": score,
            "strategy_name": decision.get("strategy_id", "UnknownStrategy"),
        }
        execution_message = await evaluar_y_ejecutar_operacion(
            bot_instance=None,
            chat_id=None,
            resultado_analisis=resultado_analisis,
            take_profit=decision.get("take_profit"),
            stop_loss=decision.get("stop_loss")
        )
        logger.info(f"Resultado de la ejecución de orden: {execution_message}")
        structured_logger.info(
            "order_executed",
            extra={
                "extra": {
                    "event": "order_executed",
                    "trade_id": trade_id,
                    "symbol": decision["symbol"],
                    "side": decision["side"],
                    "quantity": decision["quantity"],
                    "score": score,
                    "thresholds": thresholds,
                    "reason": reason,
                    "model_version": model_version,
                    "result": execution_message
                }
            }
        )
        log_decision_to_db({
            "trade_id": trade_id,
            "symbol": decision.get("symbol"),
            "type": decision.get("type"),
            "side": decision.get("side"),
            "quantity": decision.get("quantity"),
            "strategy_id": decision.get("strategy_id"),
            "timestamp_decision": decision.get("timestamp_decision"),
            "features": features,
            "score": score,
            "thresholds": thresholds,
            "reason": reason,
            "model_version": model_version,
            "result": execution_message,
            "error": None
        })
    except Exception as e:
        logger.error(f"Excepción durante la ejecución de la orden: {e}", exc_info=True)
        structured_logger.info(
            "order_execution_error",
            extra={
                "extra": {
                    "event": "order_execution_error",
                    "trade_id": trade_id,
                    "error": str(e),
                    "decision": decision
                }
            }
        )
        log_decision_to_db({
            "trade_id": trade_id,
            "symbol": decision.get("symbol"),
            "type": decision.get("type"),
            "side": decision.get("side"),
            "quantity": decision.get("quantity"),
            "strategy_id": decision.get("strategy_id"),
            "timestamp_decision": decision.get("timestamp_decision"),
            "features": features,
            "score": score,
            "thresholds": thresholds,
            "reason": reason,
            "model_version": model_version,
            "result": None,
            "error": str(e)
        })


async def main() -> None:
    """
    Bucle principal del worker de ejecución. Espera y procesa decisiones de la cola de mensajes.
    """
    logger.info("Worker de ejecución iniciado. Esperando decisiones...")
    
    # Conexión a Redis para Heartbeat
    try:
        redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
        redis_client.ping() # Verificar conexión
        logger.info("Conexión con Redis para heartbeat del worker establecida.")
    except redis.exceptions.ConnectionError as e:
        logger.critical(f"No se pudo conectar a Redis para el heartbeat del worker: {e}")
        redis_client = None

    while True:
        # Enviar Heartbeat
        if redis_client:
            try:
                redis_client.set("heartbeat:execution_worker", int(time.time()))
            except redis.exceptions.RedisError as e:
                logger.error(f"No se pudo enviar el heartbeat del worker a Redis: {e}")

        try:
            decision = mq.get_decision() # Este es un llamado bloqueante con timeout
            if decision:
                await process_decision(decision)
            else:
                # Si get_decision devuelve None (por timeout), el bucle continúa y envía un nuevo heartbeat.
                pass
        except Exception as e:
            logger.error(f"Error en el bucle principal del worker: {e}", exc_info=True)
            await asyncio.sleep(5) # Esperar antes de reintentar en caso de error

def run_worker() -> None:
    """
    Punto de entrada para lanzar el worker desde otros scripts o CLI.
    """
    asyncio.run(main())

if __name__ == "__main__":
    run_worker()