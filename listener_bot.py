# listener_bot.py
import asyncio
import logging
import sys
import os
from typing import Optional
from zoneinfo import ZoneInfo
from datetime import datetime
from typing import Union, cast

from aiogram.exceptions import TelegramBadRequest
import matplotlib.pyplot as plt
import pandas as pd
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
import utils.reporte_manager
from utils.state_manager import StateManager
from download_historical_data import download_and_save_klines
from ml_model_trainer import train_and_notify, train_and_save_model
from modules.analisis_bot import procesar_comando_analisis
from utils.technical_analysis import get_historical_klines
from optimize_strategy import optimize_and_notify, optimize_risk_thresholds_ga
from strategies.strategy_manager import StrategyManager
from utils.kpi_calculator import get_today_summary
from utils.bot_commands import set_bot_commands as set_main_bot_commands
from utils.daily_operations_counter import reset_daily_operations_count_manual
from utils.order_executor import evaluar_y_ejecutar_operacion
from utils.position_manager import (
    get_open_positions_summary,
    manage_open_positions,
    get_closed_positions_summary
)
from utils.reporte_manager import (
    generar_reporte_diario,
    generar_reporte_kpis,
    generar_reporte_journal,
    ignorar_reporte,
    listar_reportes,
    mover_a_descargados,
    obtener_reporte
)
from utils.reportes_bot import exportar_y_enviar_reporte, generar_y_enviar_reporte_rango, COLUMN_TRANSLATIONS
from utils.risk_manager import (
    activar_riesgo_forzado,
    calcular_probabilidad_ganancia_perdida,
    duracion_riesgo_forzado,
    ganancias_durante_riesgo_forzado,
    obtener_riesgo_actual,
    operaciones_en_riesgo_forzado,
    recordar_riesgo_forzado,
    restaurar_riesgo_automatico,
    riesgo_forzado_activo
)
from utils.shield_manager import (
    activar_escudo,
    desactivar_escudo,
    obtener_estado_escudo,
    escudo_activo
)
from utils.telegram_handler import send_message
from utils.data_loader import load_operations_data
from utils.message_queue import mq
from utils.alerta_manager import alerter, SeverityLevel
import re
from typing import Optional, Tuple

# === Configuración de Logging y Bot ===
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
chat_id_int = settings.TELEGRAM_CHAT_ID
strategy_manager = StrategyManager()
state_manager = StateManager()

# === Definición de Estados (FSM) ===
class RiskStates(StatesGroup):
    waiting_for_risk_percentage = State()
    waiting_for_limit_value = State()

class ReportStates(StatesGroup):
    waiting_for_start_date = State()
    waiting_for_end_date = State()
    waiting_for_format = State()

class LiveModeStates(StatesGroup):
    waiting_for_live_confirmation = State()

class InitialStates(StatesGroup):
    waiting_for_mode_selection = State()

class ChangeModeStates(StatesGroup):
    waiting_for_mode_change_confirmation = State()

# === Caché Global ===
_last_analysis_cache = {"timestamp": None, "result": None, "strategy_name": None}

# === Funciones de Utilidad para Telegram ===
async def edit_message_safely(message: types.Message, text: str, reply_markup=None):
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.info("Intento de editar mensaje sin cambios.")
        else:
            logger.error(f"Error al editar mensaje: {e}", exc_info=True)

# === Funciones de Menús y Submenús ===
def get_main_menu():
    builder = InlineKeyboardBuilder()
    is_killswitch_active = escudo_activo() == 'extremo'
    builder.button(text="📊 Análisis", callback_data="CMD_MENU_ANALISIS")
    builder.button(text="🛡️ Riesgo", callback_data="CMD_MENU_RIESGO")
    builder.button(text="📈 Reportes", callback_data="CMD_MENU_REPORTES")
    builder.button(text="⚙️ Configuración", callback_data="CMD_MENU_CONFIG")
    builder.button(text="ℹ️ Estado", callback_data="CMD_ESTADO_GENERAL")
    builder.button(text="🚀 Comprar BTC (Manual)", callback_data="CMD_MANUAL_BUY_BTC")
    if is_killswitch_active:
        builder.button(text="✅ Reanudar Bot", callback_data="CMD_REANUDAR_BOT")
    else:
        builder.button(text="🛑 Detener Bot (Kill Switch)", callback_data="CMD_DETENER_BOT")
    builder.adjust(1)
    return "Menú principal", builder.as_markup()

async def get_current_status_text():
    _, escudo_estado_texto = obtener_estado_escudo()
    posiciones_summary = await get_open_positions_summary(bot)
    closed_positions_summary = get_closed_positions_summary()
    riesgo_activo = riesgo_forzado_activo()
    riesgo_actual_pct = obtener_riesgo_actual() * 100
    duracion_riesgo = duracion_riesgo_forzado() if riesgo_activo else "N/A"
    active_strategy_name = strategy_manager.get_active_strategy().name if strategy_manager.get_active_strategy() else "N/A"
    
    today_summary = get_today_summary("data/operaciones/operaciones.csv")
    daily_profit_loss_summary = f"{today_summary['pnl_sum']:.2f}%"
    daily_operations_count_text = f"Total: {today_summary['ops_count']} (Pos: {today_summary['wins']}, Neg: {today_summary['losses']})"
    
    analysis_result_text = "\n-- Análisis no disponible --"
    if _last_analysis_cache["result"]:
        res = _last_analysis_cache["result"]
        strat_name = _last_analysis_cache["strategy_name"]
        analysis_result_text = f"""
---Análisis Actual ({strat_name})---
Decisión: <b>{res.get('decision', 'N/A')}</b> | Score: {res.get('score', 'N/A')} 
"""

    riesgo_status = f"{('Forzado' if riesgo_activo else 'Automático')} ({riesgo_actual_pct:.2f}%)"
    if riesgo_activo:
        riesgo_status += f' desde hace {duracion_riesgo}'
    
    session_mode = state_manager.get_state("session", "mode", "No definido")
    mode_text = f"Modo Sesión: <b>{session_mode.capitalize()}</b>"

    config_summary = f"""
<b>⚙️ Configuración Clave:</b>
  - Pérdida Máx. Diaria: {settings.MAX_DAILY_LOSS_PCT}%
  - Riesgo Máx. por Trade: {settings.MAX_TRADE_RISK_PCT}%
  - Máx. Posiciones Concurrentes: {settings.MAX_CONCURRENT_POSITIONS} """

    return f"""
<b> Estado Actual del Bot:</b>

{mode_text}
Estrategia: <b>{active_strategy_name}</b>
 P/L Día: {daily_profit_loss_summary}
 Ops Día: {daily_operations_count_text}

  Escudo: {escudo_estado_texto}
  Riesgo: {riesgo_status}

{posiciones_summary}
{closed_positions_summary}
{config_summary}{analysis_result_text}   """

async def send_risk_submenu(message: Union[Message, types.CallbackQuery], is_edit: bool = False):
    msg_target = getattr(message, 'message', message)
    if not isinstance(msg_target, Message):
        return
    builder = InlineKeyboardBuilder()
    riesgo_activo = riesgo_forzado_activo()
    is_killswitch_active = escudo_activo() == 'extremo'
    text = f"<b>🛡️ Gestión de Riesgo:</b>\n\n"
    if is_killswitch_active:
        text += "<b>🚨 KILL SWITCH ACTIVO - OPERACIONES BLOQUEADAS 🚨</b>\n\n"
    if riesgo_activo:
        riesgo_actual_pct = obtener_riesgo_actual() * 100
        duracion_riesgo = duracion_riesgo_forzado()
        ganancias = ganancias_durante_riesgo_forzado()
        ops = operaciones_en_riesgo_forzado()
        text += f"""
Modo actual: <b>Forzado ({riesgo_actual_pct:.2f}%)</b>
  - Activo desde: {duracion_riesgo}
  - Ganancia: {ganancias:.2f}%
  - Operaciones: {ops['total']} (✅{ops['positivas']} / ❌{ops['negativas']})
"""
        builder.button(text="🔓 Liberar Riesgo", callback_data="CMD_RIESGO_LIBERAR")
    else:
        text += f"Modo actual: <b>Automático</b>\n"
        builder.button(text="🔒 Forzar Riesgo", callback_data="CMD_RIESGO_FORZAR")
    builder.button(text="🕹️ Límites y Controles", callback_data="CMD_RIESGO_LIMITES")
    builder.button(text="🛡️ Gestionar Escudos de Volatilidad", callback_data="CMD_RIESGO_GESTIONAR_ESCUDOS")
    builder.button(text="⬅️ Volver", callback_data="CMD_VOLVER")
    builder.adjust(1)
    if is_edit:
        await edit_message_safely(msg_target, text, builder.as_markup())
    else:
        await msg_target.answer(text, reply_markup=builder.as_markup())

async def send_risk_limits_submenu(message: Union[Message, types.CallbackQuery], is_edit: bool = False):
    msg_target = getattr(message, 'message', message)
    if not isinstance(msg_target, Message):
        return
    text = f"""
<b>🕹️ Límites y Controles de Riesgo:</b>

Estos son los límites de seguridad globales recomendados.

📉 <b>Pérdida Máx. Diaria:</b> {settings.MAX_DAILY_LOSS_PCT}%
   <code>(El bot se detiene si las pérdidas del día superan este %)</code>
⚖️ <b>Riesgo Máx. por Trade:</b> {settings.MAX_TRADE_RISK_PCT}%
   <code>(Límite de riesgo para una sola operación)</code>
📊 <b>Máx. Posiciones Concurrentes:</b> {settings.MAX_CONCURRENT_POSITIONS}
   <code>(Cuántas operaciones puede tener abiertas a la vez)</code>
"""
    builder = InlineKeyboardBuilder()
    builder.button(text="Cambiar Pérdida Máx. Diaria", callback_data="CMD_LIMIT_SET_MAX_DAILY_LOSS")
    builder.button(text="Cambiar Riesgo Máx. por Trade", callback_data="CMD_LIMIT_SET_MAX_TRADE_RISK")
    builder.button(text="Cambiar Máx. Posiciones", callback_data="CMD_LIMIT_SET_MAX_CONCURRENT")
    builder.button(text="⚙️ Restaurar Valores Recomendados", callback_data="CMD_LIMIT_RESTORE_DEFAULTS")
    builder.button(text="⬅️ Volver a Riesgo", callback_data="CMD_VOLVER_RIESGO")
    builder.adjust(1)
    if is_edit:
        await edit_message_safely(msg_target, text, builder.as_markup())
    else:
        await msg_target.answer(text, reply_markup=builder.as_markup())

# ... (resto del archivo sin cambios)