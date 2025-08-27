# utils/risk_manager.py
import logging
from datetime import datetime, date
import json
import os
import pandas as pd
import asyncio
from utils.state_manager import StateManager
from config import settings
from utils.shield_manager import escudo_activo
from utils.position_manager import get_open_positions
from utils.binance_client import get_binance_client

logger = logging.getLogger(__name__)

_OPTIMIZED_THRESHOLDS_PATH = "best_risk_thresholds.json" # Ruta por defecto para los umbrales optimizados
UMBRAL_FILE = _OPTIMIZED_THRESHOLDS_PATH
OPERATIONS_LOG = "data/operaciones/operaciones.csv"

# -----------------------------
# Funciones de verificación de límites de riesgo
# -----------------------------

def _get_daily_pnl_pct() -> float:
    """
    Calcula el P&L porcentual acumulado para el día de hoy.
    Returns:
        float: P&L porcentual acumulado del día.
    """
    if not os.path.exists(OPERATIONS_LOG):
        return 0.0

    try:
        df = pd.read_csv(OPERATIONS_LOG, parse_dates=['timestamp_open'])
        today = date.today()
        # Asegurarse que la columna de timestamp es de tipo datetime
        df['timestamp_open'] = pd.to_datetime(df['timestamp_open'])
        todays_ops = df[df['timestamp_open'].dt.date == today]

        if todays_ops.empty:
            return 0.0
        
        # Usar la columna 'pnl_percent' que ya está calculada
        daily_pnl = todays_ops['pnl_percent'].sum()
        return daily_pnl
    except Exception as e:
        logger.error(f"Error calculando P&L diario: {e}", exc_info=True)
        return 0.0

def check_stop_loss_take_profit(position_data: dict, current_price: float) -> tuple[bool, str]:
    """
    Verifica si se ha alcanzado el Stop Loss o Take Profit para una posición abierta.

    Args:
        position_data (dict): Diccionario con los datos de la posición abierta,
                              incluyendo 'entry_price', 'stop_loss' y 'take_profit'.
        current_price (float): Precio actual del activo.

    Returns:
        tuple[bool, str]: (True, "SL hit") si se activó el Stop Loss,
                          (True, "TP hit") si se activó el Take Profit,
                          (False, "No trigger") en caso contrario.
    """
    entry_price = position_data.get('entry_price')
    stop_loss = position_data.get('stop_loss')
    take_profit = position_data.get('take_profit')
    side = position_data.get('side') # 'BUY' or 'SELL'

    if not entry_price:
        logger.warning(f"No se encontró 'entry_price' en los datos de la posición: {position_data}")
        return False, "No trigger (missing entry_price)"

    # For BUY orders: SL is below entry, TP is above entry
    if side == 'BUY':
        if stop_loss and current_price <= stop_loss:
            logger.info(f"Stop Loss activado para BUY. Precio actual: {current_price}, SL: {stop_loss}")
            return True, "SL hit"
        if take_profit and current_price >= take_profit:
            logger.info(f"Take Profit activado para BUY. Precio actual: {current_price}, TP: {take_profit}")
            return True, "TP hit"
    # For SELL orders: SL is above entry, TP is below entry
    elif side == 'SELL':
        if stop_loss and current_price >= stop_loss:
            logger.info(f"Stop Loss activado para SELL. Precio actual: {current_price}, SL: {stop_loss}")
            return True, "SL hit"
        if take_profit and current_price <= take_profit:
            logger.info(f"Take Profit activado para SELL. Precio actual: {current_price}, TP: {take_profit}")
            return True, "TP hit"
    else:
        logger.warning(f"Lado de operación desconocido: {side} en {position_data}")

    return False, "No trigger"

async def verificar_permiso_de_operacion() -> tuple[bool, str]:
    """
    Verifica todas las reglas de riesgo antes de permitir una nueva operación.
    Es una función asíncrona porque necesita consultar el balance actual.
    Returns:
        tuple[bool, str]: (True, "Permitido") si se puede operar, o (False, "Razón") si no.
    """
    # 1. Verificar Kill Switch (Escudo Extremo)
    tipo_escudo = escudo_activo()
    if tipo_escudo == 'extremo':
        reason = "Kill Switch (Escudo Extremo) está activado."
        logger.warning(f"Operación bloqueada: {reason}")
        return False, reason

    # 2. Verificar Límite de Pérdida Diaria
    daily_pnl = _get_daily_pnl_pct()
    if daily_pnl < -settings.MAX_DAILY_LOSS_PCT:
        reason = f"Límite de pérdida diaria ({settings.MAX_DAILY_LOSS_PCT}%) alcanzado. P&L de hoy: {daily_pnl:.2f}%."
        logger.warning(f"Operación bloqueada: {reason}")
        return False, reason

    # 3. Verificar Límite de Posiciones Concurrentes y Exposición Total
    open_positions_df = get_open_positions()
    current_positions = len(open_positions_df)
    if current_positions >= settings.MAX_CONCURRENT_POSITIONS:
        reason = f"Límite de posiciones concurrentes ({settings.MAX_CONCURRENT_POSITIONS}) alcanzado. Abiertas: {current_positions}."
        logger.warning(f"Operación bloqueada: {reason}")
        return False, reason

    # 4. Verificar Límite de Exposición Total del Capital
    if not open_positions_df.empty:
        try:
            client = await get_binance_client()
            balance_info = await asyncio.to_thread(client.get_asset_balance, asset="USDT")
            current_balance = float(balance_info['free'])
            
            total_exposure_usdt = open_positions_df['size_usdt'].sum()
            
            # Incluir el balance actual en el cálculo de la exposición total
            total_capital = current_balance + total_exposure_usdt
            if total_capital > 0:
                exposure_pct = (total_exposure_usdt / total_capital) * 100
                if exposure_pct > settings.MAX_TOTAL_EXPOSURE_PCT:
                    reason = f"Límite de exposición total ({settings.MAX_TOTAL_EXPOSURE_PCT}%) excedido. Exposición actual: {exposure_pct:.2f}%."
                    logger.warning(f"Operación bloqueada: {reason}")
                    return False, reason
        except Exception as e:
            logger.error(f"Error al verificar la exposición del capital: {e}", exc_info=True)
            # Decidir si bloquear la operación en caso de error. Por seguridad, es mejor bloquearla.
            return False, "Error al verificar la exposición del capital."


    logger.info("Verificación de permisos de operación superada. Todos los límites de riesgo están dentro de los parámetros.")
    return True, "Permitido"

from typing import Tuple, Dict, Any

async def perform_pre_execution_risk_checks(decision: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Realiza comprobaciones de riesgo específicas antes de la ejecución de una orden.
    Esta función es llamada por el worker de ejecución.
    Args:
        decision (Dict[str, Any]): Diccionario con los datos de la decisión de trading.
    Returns:
        Tuple[bool, str]: (True, "Permitido") si pasa los chequeos, o (False, "Razón") si no.
    """
    logger.info(f"Realizando comprobaciones de riesgo pre-ejecución para decisión: {decision.get('type', 'UNKNOWN')} {decision.get('symbol')}")

    # Re-use existing general permission check
    permiso_general, razon_general = await verificar_permiso_de_operacion()
    if not permiso_general:
        return False, razon_general

    # Additional checks based on decision data (e.g., MAX_TRADE_RISK_PCT)
    # This part would need more sophisticated logic based on the actual trade size
    # and the bot's current balance, which is not directly available here.
    # For now, we'll assume the quantity in the decision is already risk-adjusted
    # or that the order_executor will handle the final risk check.

    # Example: Check if quantity is reasonable (very basic)
    if decision.get('quantity', 0) <= 0:
        return False, "Cantidad de operación inválida (cero o negativa)."
    
    # Example: Check if symbol is valid (basic)
    if not decision.get('symbol'):
        return False, "Símbolo de operación no especificado."

    logger.info("Comprobaciones de riesgo pre-ejecución superadas.")
    return True, "Permitido"


# -----------------------------
# Gestión de umbrales optimizados
# -----------------------------
_OPTIMIZED_THRESHOLDS = {} # Module-level variable to store loaded thresholds

def cargar_umbrales_optimizado():
    """Carga los umbrales desde el archivo de optimización."""
    global _OPTIMIZED_THRESHOLDS # Declare as global to modify
    if os.path.exists(UMBRAL_FILE):
        try:
            with open(UMBRAL_FILE, "r") as f:
                data = json.load(f)
                _OPTIMIZED_THRESHOLDS = data # Store in global variable
                logger.info(f"Umbrales cargados desde {UMBRAL_FILE}: {data}")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"Error de formato JSON en {UMBRAL_FILE}: {e}", exc_info=True)
        except Exception as e:
            logger.exception(f"Error inesperado cargando {UMBRAL_FILE}: {e}")
    else:
        logger.warning(f"No se encontró {UMBRAL_FILE}, usando valores por defecto.")
    
    # Default values if file not found or error
    default_thresholds = {
        "umbral_alto": 0.9,
        "umbral_medio": 0.7,
        "umbral_bajo": 0.4
    }
    _OPTIMIZED_THRESHOLDS = default_thresholds # Store default in global variable
    return default_thresholds

# Load thresholds at module import time
cargar_umbrales_optimizado()

# -----------------------------
# Gestión de estado de riesgo
# -----------------------------
def _get_risk_state():
    sm = StateManager()
    return sm.get_state("risk_manager")

def _update_risk_state(updates: dict):
    sm = StateManager()
    sm.update_module_state("risk_manager", updates)

def obtener_riesgo_actual() -> float:
    return _get_risk_state().get("riesgo_actual", settings.DEFAULT_RISK_PERCENTAGE / 100)

def riesgo_forzado_activo() -> bool:
    return _get_risk_state().get("riesgo_forzado", False)

def activar_riesgo_forzado(porcentaje: float):
    updates = {
        "riesgo_actual": porcentaje / 100,
        "riesgo_forzado": True,
        "tiempo_riesgo_forzado": datetime.now().isoformat(),
        "recordatorio_riesgo_forzado_hoy": True
    }
    _update_risk_state(updates)
    logger.info(f"Riesgo forzado activado al {porcentaje}%.")

def restaurar_riesgo_automatico():
    updates = {
        "riesgo_actual": settings.DEFAULT_RISK_PERCENTAGE / 100,
        "riesgo_forzado": False,
        "tiempo_riesgo_forzado": None,
        "ganancias_riesgo_forzado": 0.0,
        "operaciones_riesgo_forzado": []
    }
    _update_risk_state(updates)
    logger.info("Riesgo restaurado a modo automático.")

def registrar_resultado_operacion(ganancia_pct: float):
    if riesgo_forzado_activo():
        state = _get_risk_state()
        state["ganancias_riesgo_forzado"] += ganancia_pct
        state["operaciones_riesgo_forzado"].append(ganancia_pct)
        _update_risk_state(state)

def duracion_riesgo_forzado() -> str:
    tiempo_activacion_str = _get_risk_state().get("tiempo_riesgo_forzado")
    if not tiempo_activacion_str:
        return "0h"
    tiempo_activacion = datetime.fromisoformat(tiempo_activacion_str)
    duracion = datetime.now() - tiempo_activacion
    return f"{int(duracion.total_seconds() // 3600)}h"

def ganancias_durante_riesgo_forzado() -> float:
    return _get_risk_state().get("ganancias_riesgo_forzado", 0.0)

def operaciones_en_riesgo_forzado() -> dict:
    operaciones = _get_risk_state().get("operaciones_riesgo_forzado", [])
    return {
        "total": len(operaciones),
        "positivas": sum(1 for p in operaciones if p > 0),
        "negativas": sum(1 for p in operaciones if p <= 0)
    }

def calcular_probabilidad_ganancia_perdida() -> dict:
    operaciones = _get_risk_state().get("operaciones_riesgo_forzado", [])
    if not operaciones:
        return {"ganar": 50.0, "perder": 50.0}
    positivas = sum(1 for p in operaciones if p > 0)
    return {
        "ganar": (positivas / len(operaciones)) * 100,
        "perder": ((len(operaciones) - positivas) / len(operaciones)) * 100
    }

def recordar_riesgo_forzado() -> bool:
    return _get_risk_state().get("recordatorio_riesgo_forzado_hoy", True)

def desactivar_recordatorio_hoy():
    _update_risk_state({"recordatorio_riesgo_forzado_hoy": False})
    logger.info("Recordatorio de riesgo forzado desactivado para hoy.")

def obtener_riesgo_ajustado_por_ml(score: float, riesgo_base: float) -> float:
    # Use the globally loaded optimized thresholds
    umbral_alto = _OPTIMIZED_THRESHOLDS.get("umbral_alto", 0.85) # Fallback to default if not found
    umbral_medio = _OPTIMIZED_THRESHOLDS.get("umbral_medio", 0.70)
    umbral_bajo = _OPTIMIZED_THRESHOLDS.get("umbral_bajo", 0.55)

    if score > umbral_alto:
        return riesgo_base * 1.5
    elif score >= umbral_medio:
        return riesgo_base * 1.0
    elif score >= umbral_bajo:
        return riesgo_base * 0.75
    else:
        return riesgo_base * 0.5

def obtener_riesgo_ajustado(score: float, riesgo_base: float, volatilidad: float, drawdown: float, señales_técnicas: float) -> float:
    """
    Calcula el riesgo ajustado combinando el score del modelo ML con volatilidad, drawdown y señales técnicas.

    Args:
        score (float): Score del modelo ML.
        riesgo_base (float): Riesgo base configurado.
        volatilidad (float): Métrica de volatilidad del mercado.
        drawdown (float): Métrica de drawdown.
        señales_técnicas (float): Métrica de señales técnicas.

    Returns:
        float: Riesgo ajustado calculado.
    """
    # Pesos para cada métrica (pueden ajustarse según necesidades)
    peso_score = 0.4
    peso_volatilidad = 0.2
    peso_drawdown = 0.2
    peso_señales = 0.2

    # Normalizar métricas y centrar alrededor de 1.0
    # Cuando una métrica es 0.5, su valor normalizado será 1.0
    score_normalizado = 2 * min(max(score, 0), 1)  # [0,1] -> [0,2]
    volatilidad_normalizada = 2 * min(max(volatilidad, 0), 1)
    drawdown_normalizado = 2 * (1 - min(max(drawdown, 0), 1))  # Invertir drawdown
    señales_normalizadas = 2 * min(max(señales_técnicas, 0), 1)

    # Calcular factor de ajuste combinado
    factor_ajuste = (
        peso_score * score_normalizado +
        peso_volatilidad * volatilidad_normalizada +
        peso_drawdown * drawdown_normalizado +
        peso_señales * señales_normalizadas
    ) / (peso_score + peso_volatilidad + peso_drawdown + peso_señales)

    # Cuando todas las métricas son 0.5, factor_ajuste será 1.0
    return riesgo_base * factor_ajuste

def guardar_umbrales_optimizado(umbrales: dict):
    """Guarda los umbrales optimizados en archivo."""
    try:
        with open(UMBRAL_FILE, "w") as f:
            json.dump(umbrales, f, indent=4)
        logger.info(f"Umbrales guardados en {UMBRAL_FILE}: {umbrales}")
    except Exception as e:
        logger.exception(f"No se pudieron guardar los umbrales: {e}")