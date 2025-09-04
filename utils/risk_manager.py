# utils/risk_manager.py
from datetime import datetime, date, timezone
import json
import os
import pandas as pd
import os
from utils.state_manager import StateManager
from config import settings
from utils.shield_manager import escudo_activo
from utils.position_manager import get_open_positions
from utils.structured_logger import StructuredLogger
from utils.binance_client import get_binance_client

logger = StructuredLogger(__name__)

_OPTIMIZED_THRESHOLDS_PATH = "best_risk_thresholds.json" # Ruta por defecto para los umbrales optimizados
UMBRAL_FILE = _OPTIMIZED_THRESHOLDS_PATH
OPERATIONS_LOG = "data/operaciones/operaciones.csv"

# -----------------------------
# Funciones de verificación de límites de riesgo
# -----------------------------

async def _get_daily_pnl_pct() -> float:
    """
    Calcula el P&L porcentual total del día (realizado + no realizado).
    El P&L se calcula en USDT y luego se convierte a un porcentaje del capital total.
    """
    realized_pnl_usdt = 0.0
    unrealized_pnl_usdt = 0.0
    total_capital_usdt = 0.0
    state_manager = StateManager() # Instancia local para evitar problemas de concurrencia

    try:
        client = await get_binance_client()

        # 1. Calcular PnL Realizado de operaciones cerradas hoy
        if os.path.exists(OPERATIONS_LOG):
            # Leer CSV y normalizar timestamps a UTC de forma robusta
            ops_df = pd.read_csv(OPERATIONS_LOG)
            today = datetime.now(timezone.utc).date()

            if 'timestamp_close' in ops_df.columns:
                ts_close = pd.to_datetime(ops_df['timestamp_close'], utc=True, errors='coerce')
                closed_today_ops = ops_df[(ts_close.notna()) & (ts_close.dt.date == today)]
            else:
                closed_today_ops = pd.DataFrame()

            if not closed_today_ops.empty:
                realized_pnl_usdt = closed_today_ops['pnl_usdt'].sum()

        # 2. Calcular PnL No Realizado de posiciones abiertas
        open_positions = get_open_positions()

        if not open_positions.empty:
            all_tickers = await client.get_all_tickers()
            tickers_map = {ticker['symbol']: float(ticker['price']) for ticker in all_tickers}

            for _, pos in open_positions.iterrows():
                symbol = pos.get('symbol')
                if symbol in tickers_map:
                    current_price = tickers_map[symbol]
                    entry_price = float(pos.get('entry_price', 0.0) or 0.0)
                    # Fallback de cantidad: usar cantidad_token_operada si existe, si no, size_usdt / entry_price
                    qty = pos.get('cantidad_token_operada')
                    if qty is None or (isinstance(qty, float) and pd.isna(qty)):
                        size_usdt = float(pos.get('size_usdt', 0.0) or 0.0)
                        qty = (size_usdt / entry_price) if entry_price > 0 else 0.0
                    quantity = float(qty or 0.0)
                    side_val = str(pos.get('side', '')).upper()
                    # Mapear BUY/SELL a LONG/SHORT
                    is_long = side_val in ('LONG', 'BUY', 'COMPRA')

                    pnl = (current_price - entry_price) * quantity if is_long else (entry_price - current_price) * quantity
                    unrealized_pnl_usdt += pnl
                else:
                    logger.warning("PNL_CALC_NO_TICKER", f"No se encontró el ticker para {symbol} al calcular PnL no realizado.")

        # 3. Calcular Capital Total
        # Considerar equity de cTrader SOLO si el objetivo de ejecución es CTRADER
        total_capital_usdt = 0.0
        try:
            from config import settings as _settings
            use_ctrader_equity = str(getattr(_settings, 'EXECUTION_TARGET', 'BINANCE')).upper() == 'CTRADER'
        except Exception:
            use_ctrader_equity = False

        if use_ctrader_equity:
            ctrader_account_path = os.path.join('data', 'ctrader', 'account.json')
            if os.path.exists(ctrader_account_path):
                try:
                    with open(ctrader_account_path, 'r') as f:
                        acc = json.load(f)
                        eq = acc.get('equity')
                        if eq is not None:
                            total_capital_usdt = float(eq)
                except Exception:
                    total_capital_usdt = 0.0

        if total_capital_usdt <= 0:
            balance_info = await client.get_asset_balance(asset="USDT")
            usdt_balance = float(balance_info['free']) if balance_info else 0.0
            open_positions_value = open_positions['size_usdt'].sum() if not open_positions.empty else 0.0
            total_capital_usdt = usdt_balance + open_positions_value

        if total_capital_usdt == 0:
            return 0.0

        # 4. Calcular PnL Total y Porcentaje
        total_pnl_usdt = realized_pnl_usdt + unrealized_pnl_usdt
        pnl_percentage = (total_pnl_usdt / total_capital_usdt) * 100
        
        state_manager.update_module_state("risk_metrics", {
            "daily_realized_pnl_usdt": realized_pnl_usdt,
            "daily_unrealized_pnl_usdt": unrealized_pnl_usdt,
            "daily_total_pnl_usdt": total_pnl_usdt,
            "total_capital_usdt": total_capital_usdt,
            "daily_pnl_percentage": pnl_percentage
        })

        return pnl_percentage

    except Exception as e:
        logger.error("DAILY_PNL_CALCULATION_ERROR", f"Error crítico calculando P&L diario: {e}", exc_info=True)
        return 0.0


async def verificar_permiso_de_operacion(new_trade_size_usdt: float = 0.0, symbol: str | None = None) -> tuple[bool, str]:
    """
    Verifica todas las reglas de riesgo antes de permitir una nueva operación.
    Requiere el tamaño de la nueva operación para el chequeo de exposición.
    """
    state_manager = StateManager()

    # REGLA 0: Verificar si el sistema está en pausa (Kill Switch o pausa por Drawdown)
    if state_manager.get_state("system", "is_paused", False):
        reason = "Sistema en pausa global (Kill Switch manual activado)."
        logger.warning("TRADE_REJECTED", reason, details={"rule": "system_paused"})
        return False, reason

    drawdown_pause_until_str = state_manager.get_state("system", "drawdown_pause_until")
    if drawdown_pause_until_str:
        drawdown_pause_until = datetime.fromisoformat(drawdown_pause_until_str)
        if datetime.now(timezone.utc) < drawdown_pause_until:
            reason = f"Pausa por Drawdown activa hasta {drawdown_pause_until.strftime('%Y-%m-%d %H:%M:%S UTC')}."
            logger.warning("TRADE_REJECTED", reason, details={"rule": "drawdown_pause", "paused_until": drawdown_pause_until_str})
            return False, reason
        else:
            state_manager.set_state("system", "drawdown_pause_until", None)
            logger.info("DRAWDOWN_PAUSE_LIFTED", "La pausa por drawdown diario ha expirado y ha sido levantada.")

    # REGLA 1: Verificar Límite de Operaciones Concurrentes
    open_positions_df = get_open_positions()
    current_positions = len(open_positions_df)
    params = get_effective_risk_params()
    if current_positions >= params["RISK_MAX_CONCURRENT_TRADES"]:
        reason = f"Límite de operaciones concurrentes ({params['RISK_MAX_CONCURRENT_TRADES']}) alcanzado."
        logger.warning("TRADE_REJECTED", reason, details={"rule": "max_concurrent_trades", "limit": params['RISK_MAX_CONCURRENT_TRADES'], "current": current_positions})
        return False, reason

    # REGLA 1b (opcional): Limitar trades por símbolo si está configurado
    max_trades_per_symbol = params.get("RISK_MAX_PER_SYMBOL_TRADES")
    if symbol and isinstance(max_trades_per_symbol, int) and max_trades_per_symbol > 0:
        try:
            per_symbol = len(open_positions_df[open_positions_df.get('symbol') == symbol])
        except Exception:
            per_symbol = 0
        if per_symbol >= max_trades_per_symbol:
            reason = f"Límite de operaciones por símbolo ({max_trades_per_symbol}) alcanzado para {symbol}."
            logger.warning("TRADE_REJECTED", reason, details={"rule": "max_trades_per_symbol", "symbol": symbol, "limit": max_trades_per_symbol, "current": per_symbol})
            return False, reason

    # REGLA 2: Verificar Límite de Exposición Máxima
    try:
        client = await get_binance_client()
        balance_info = await client.get_asset_balance(asset="USDT")
        usdt_balance = float(balance_info['free']) if balance_info else 0.0

        open_positions_value = open_positions_df['size_usdt'].sum() if not open_positions_df.empty else 0.0
        # Considerar equity de cTrader SOLO si el objetivo de ejecución es CTRADER
        try:
            from config import settings as _settings
            use_ctrader_equity = str(getattr(_settings, 'EXECUTION_TARGET', 'BINANCE')).upper() == 'CTRADER'
        except Exception:
            use_ctrader_equity = False

        total_capital = 0.0
        if use_ctrader_equity:
            ctrader_account_path = os.path.join('data', 'ctrader', 'account.json')
            if os.path.exists(ctrader_account_path):
                try:
                    with open(ctrader_account_path, 'r') as f:
                        acc = json.load(f)
                        eq = acc.get('equity')
                        if eq is not None:
                            total_capital = float(eq)
                except Exception:
                    total_capital = 0.0

        if total_capital <= 0:
            total_capital = usdt_balance + open_positions_value

        if total_capital > 0:
            current_exposure_pct = (open_positions_value / total_capital) * 100
            new_trade_exposure_pct = (new_trade_size_usdt / total_capital) * 100

            if current_exposure_pct + new_trade_exposure_pct > params["RISK_MAX_EXPOSURE_PCT"]:
                reason = f"Límite de exposición máxima ({params['RISK_MAX_EXPOSURE_PCT']}%) superado."
                logger.warning("TRADE_REJECTED", reason, details={"rule": "max_exposure", "limit_pct": params['RISK_MAX_EXPOSURE_PCT'], "current_exposure_pct": current_exposure_pct, "new_trade_exposure_pct": new_trade_exposure_pct})
                return False, reason
            # REGLA 2b (opcional): Límite de exposición por símbolo
            per_symbol_exposure_limit = params.get("RISK_MAX_PER_SYMBOL_EXPOSURE_PCT")
            if symbol and isinstance(per_symbol_exposure_limit, (int, float)) and per_symbol_exposure_limit > 0:
                try:
                    sym_usdt = float(open_positions_df.loc[open_positions_df.get('symbol') == symbol, 'size_usdt'].sum())
                except Exception:
                    sym_usdt = 0.0
                sym_exposure_pct_after = ((sym_usdt + new_trade_size_usdt) / total_capital) * 100
                if sym_exposure_pct_after > float(per_symbol_exposure_limit):
                    reason = (
                        f"Límite de exposición por símbolo ({per_symbol_exposure_limit}%) superado para {symbol}."
                    )
                    logger.warning("TRADE_REJECTED", reason, details={
                        "rule": "max_symbol_exposure", "symbol": symbol, "limit_pct": per_symbol_exposure_limit,
                        "sym_exposure_pct_after": sym_exposure_pct_after
                    })
                    return False, reason
    except Exception as e:
        logger.error("MAX_EXPOSURE_CHECK_ERROR", f"Error verificando la exposición máxima: {e}", exc_info=True)
        return False, "Error en chequeo de exposición"

    # REGLA 3: Verificar Límite de Drawdown Máximo Diario
    daily_pnl_pct = await _get_daily_pnl_pct()
    if daily_pnl_pct < -params["RISK_MAX_DAILY_DRAWDOWN_PCT"]:
        end_of_day = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59, microsecond=999999)
        state_manager.set_state("system", "drawdown_pause_until", end_of_day.isoformat())
        reason = f"Límite de drawdown diario ({params['RISK_MAX_DAILY_DRAWDOWN_PCT']}%) alcanzado. P&L de hoy: {daily_pnl_pct:.2f}%. Sistema en pausa."
        logger.critical("MAX_DRAWDOWN_REACHED", reason, details={"rule": "max_daily_drawdown", "limit_pct": params['RISK_MAX_DAILY_DRAWDOWN_PCT'], "current_pnl_pct": daily_pnl_pct})
        return False, reason

    logger.info("TRADE_PERMISSION_GRANTED", "Verificación de permisos de operación superada.")
    return True, "Permitido"

from typing import Tuple, Dict, Any

async def perform_pre_execution_risk_checks(decision: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Realiza comprobaciones de riesgo BÁSICAS y de formato antes de la ejecución.
    Las comprobaciones de riesgo completas (drawdown, exposición, etc.) se realizan
    dentro de `evaluar_y_ejecutar_operacion` donde se conoce el tamaño final de la orden.
    """
    event_details = {"decision_type": decision.get('type', 'UNKNOWN'), "symbol": decision.get('symbol')}
    logger.info("PRE_EXECUTION_CHECK_START", "Iniciando comprobaciones de riesgo pre-ejecución básicas.", details=event_details)

    if not decision.get('symbol'):
        logger.warning("PRE_EXECUTION_CHECK_FAIL", "Símbolo no especificado en la decisión.", details=event_details)
        return False, "Símbolo de operación no especificado."

    # Aceptar 'side' como alias de 'decision'
    decision_value = decision.get('decision') or decision.get('side')
    if decision_value not in ['BUY', 'SELL', 'MANTENER']:
        reason = f"Decisión inválida: {decision_value}"
        logger.warning("PRE_EXECUTION_CHECK_FAIL", reason, details={**event_details, "reason": reason})
        return False, reason

    logger.info("PRE_EXECUTION_CHECK_SUCCESS", "Comprobaciones de riesgo pre-ejecución básicas superadas.", details=event_details)
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
                logger.info("THRESHOLDS_LOADED", f"Umbrales cargados desde {UMBRAL_FILE}", details={"data": data})
                return data
        except json.JSONDecodeError as e:
            logger.error(
                "OPTIMIZED_THRESHOLDS_JSON_ERROR",
                f"Error de formato JSON en {UMBRAL_FILE}: {e}",
                details={"file_path": UMBRAL_FILE},
                exc_info=True
            )
        except Exception as e:
            logger.error(
                "OPTIMIZED_THRESHOLDS_LOAD_ERROR",
                f"Error inesperado cargando {UMBRAL_FILE}: {e}",
                details={"file_path": UMBRAL_FILE},
                exc_info=True
            )
    else:
        logger.warning("THRESHOLDS_FILE_NOT_FOUND", f"No se encontró {UMBRAL_FILE}, usando valores por defecto.")
    
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
    state = sm.get_state("risk_manager")
    return state or {}

def _update_risk_state(updates: dict):
    sm = StateManager()
    sm.update_module_state("risk_manager", updates)

def _get_custom_params_state() -> dict:
    state = _get_risk_state() or {}
    return {
        "active": state.get("custom_params_active", False),
        "params": state.get("custom_params", {})
    }

def custom_risk_params_active() -> bool:
    return bool(_get_custom_params_state().get("active", False))

def get_effective_risk_params() -> dict:
    """Devuelve los parámetros efectivos de riesgo (custom si activos, de settings si no)."""
    custom = _get_custom_params_state()
    params = {
        "RISK_PER_TRADE_STOP_LOSS_PCT": float(getattr(settings, "RISK_PER_TRADE_STOP_LOSS_PCT", 2.0)),
        "RISK_PER_TRADE_TAKE_PROFIT_PCT": float(getattr(settings, "RISK_PER_TRADE_TAKE_PROFIT_PCT", 4.0)),
        "RISK_MAX_CONCURRENT_TRADES": int(getattr(settings, "RISK_MAX_CONCURRENT_TRADES", 4)),
        "RISK_MAX_EXPOSURE_PCT": float(getattr(settings, "RISK_MAX_EXPOSURE_PCT", 30.0)),
        "RISK_MAX_DAILY_DRAWDOWN_PCT": float(getattr(settings, "RISK_MAX_DAILY_DRAWDOWN_PCT", 3.0)),
        "DEFAULT_RISK_PERCENTAGE": float(getattr(settings, "DEFAULT_RISK_PERCENTAGE", 1.0)),
        # Claves opcionales por símbolo (None por defecto, aplican solo si se configuran)
        "RISK_MAX_PER_SYMBOL_TRADES": getattr(settings, "RISK_MAX_PER_SYMBOL_TRADES", None),
        "RISK_MAX_PER_SYMBOL_EXPOSURE_PCT": getattr(settings, "RISK_MAX_PER_SYMBOL_EXPOSURE_PCT", None),
    }
    if custom.get("active") and isinstance(custom.get("params"), dict):
        # Solo actualiza claves conocidas y con valores no nulos
        params.update({k: v for k, v in custom["params"].items() if k in params and v is not None})
    return params

def set_custom_risk_params(new_params: dict):
    """Activa parámetros personalizados y los persiste en el estado."""
    allowed = {
        "RISK_PER_TRADE_STOP_LOSS_PCT",
        "RISK_PER_TRADE_TAKE_PROFIT_PCT",
        "RISK_MAX_CONCURRENT_TRADES",
        "RISK_MAX_EXPOSURE_PCT",
        "RISK_MAX_DAILY_DRAWDOWN_PCT",
        "DEFAULT_RISK_PERCENTAGE",
        # Nuevas claves opcionales por símbolo
        "RISK_MAX_PER_SYMBOL_TRADES",
        "RISK_MAX_PER_SYMBOL_EXPOSURE_PCT",
    }
    clean = {k: new_params[k] for k in new_params.keys() if k in allowed}
    state = _get_risk_state()
    state["custom_params_active"] = True
    state["custom_params"] = {**state.get("custom_params", {}), **clean}
    _update_risk_state(state)
    logger.info("CUSTOM_RISK_PARAMS_SET", "Parámetros de riesgo personalizados activados.", details=clean)
    # Si no estamos en modo manual (riesgo forzado), sincronizar riesgo_actual con el base efectivo
    try:
        if not riesgo_forzado_activo():
            params = get_effective_risk_params()
            _update_risk_state({
                "riesgo_actual": params["DEFAULT_RISK_PERCENTAGE"] / 100
            })
            logger.info("CURRENT_RISK_SYNCED", "Riesgo actual sincronizado con el base efectivo tras cambio de parámetros personalizados.", details={"riesgo_actual_pct": params["DEFAULT_RISK_PERCENTAGE"]})
    except Exception as e:
        logger.warning("CURRENT_RISK_SYNC_FAIL", f"No se pudo sincronizar riesgo_actual: {e}")

def reset_custom_risk_params():
    state = _get_risk_state()
    state["custom_params_active"] = False
    state["custom_params"] = {}
    _update_risk_state(state)
    logger.info("CUSTOM_RISK_PARAMS_RESET", "Parámetros de riesgo personalizados desactivados. Volviendo a valores por defecto")

def obtener_riesgo_actual() -> float:
    params = get_effective_risk_params()
    return _get_risk_state().get("riesgo_actual", params["DEFAULT_RISK_PERCENTAGE"] / 100)

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
    logger.info("MANUAL_RISK_ACTIVATED", f"Riesgo forzado activado al {porcentaje}%.", details={"percentage": porcentaje})

def restaurar_riesgo_automatico():
    params = get_effective_risk_params()
    updates = {
        "riesgo_actual": params["DEFAULT_RISK_PERCENTAGE"] / 100,
        "riesgo_forzado": False,
        "tiempo_riesgo_forzado": None,
        "ganancias_riesgo_forzado": 0.0,
        "operaciones_riesgo_forzado": []
    }
    _update_risk_state(updates)
    logger.info("AUTO_RISK_RESTORED", "Riesgo restaurado a modo automático.")

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
    logger.info("MANUAL_RISK_REMINDER_OFF", "Recordatorio de riesgo forzado desactivado para hoy.")

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
        logger.info("THRESHOLDS_SAVED", f"Umbrales guardados en {UMBRAL_FILE}", details={"umbrales": umbrales})
    except Exception as e:
        logger.error("THRESHOLDS_SAVE_ERROR", f"No se pudieron guardar los umbrales: {e}", exc_info=True)