# utils/daily_operations_counter.py

import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

COUNTER_FILE = "data/daily_operations_count.json"
os.makedirs("data", exist_ok=True)

def _load_counter_state():
    """Carga el estado del contador desde el archivo."""
    if not os.path.exists(COUNTER_FILE):
        return {"date": None, "count": 0}
    with open(COUNTER_FILE, "r") as f:
        return json.load(f)

def _save_counter_state(state):
    """Guarda el estado del contador en el archivo."""
    with open(COUNTER_FILE, "w") as f:
        json.dump(state, f, indent=4)

def get_daily_operations_count() -> int:
    """Devuelve el número de operaciones realizadas hoy, reseteando si es un nuevo día."""
    state = _load_counter_state()
    today_str = datetime.now().strftime("%Y-%m-%d")

    if state["date"] != today_str:
        logger.info(f"Nuevo día detectado. Reseteando contador de operaciones diarias. Anterior: {state['count']}")
        state["date"] = today_str
        state["count"] = 0
        _save_counter_state(state)
    
    return state["count"]

def increment_daily_operations_count():
    """Incrementa el contador de operaciones diarias."""
    state = _load_counter_state()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Asegurarse de que el contador se resetee si es un nuevo día antes de incrementar
    if state["date"] != today_str:
        logger.info(f"Nuevo día detectado al incrementar. Reseteando contador de operaciones diarias. Anterior: {state['count']}")
        state["date"] = today_str
        state["count"] = 0
    
    state["count"] += 1
    _save_counter_state(state)
    logger.info(f"Contador de operaciones diarias incrementado a {state['count']}.")

def reset_daily_operations_count_manual():
    """Resetea manualmente el contador de operaciones diarias (para uso externo, ej. script de medianoche)."""
    state = {"date": datetime.now().strftime("%Y-%m-%d"), "count": 0}
    _save_counter_state(state)
    logger.info("Contador de operaciones diarias reseteado manualmente.")
