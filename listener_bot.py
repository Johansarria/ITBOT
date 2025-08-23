print("listener_bot.py script started.")
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

import config
import utils.reporte_manager
from config import load_configurations
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot to None and other variables. They will be initialized properly
# when the bot is run directly, but not during test collection.
bot: Optional[Bot] = None
dp = Dispatcher()  # Dispatcher can be initialized, it has no side-effects.
chat_id_int: Optional[int] = None
strategy_manager = StrategyManager()
state_manager = StateManager()

# This block will only run when the script is not being imported by pytest
if "pytest" not in sys.modules:
    if not config.TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN not found in config")

    bot = Bot(token=config.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    if config.TELEGRAM_CHAT_ID:
        chat_id_int = int(config.TELEGRAM_CHAT_ID)

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
    posiciones_summary = get_open_positions_summary(bot)
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
--- Análisis Actual ({strat_name}) ---
Decisión: <b>{res.get('decision', 'N/A')}</b> | Score: {res.get('score', 'N/A')} 
"""
    riesgo_status = f"{('Forzado' if riesgo_activo else 'Automático')} ({riesgo_actual_pct:.2f}%)"
    if riesgo_activo:
        riesgo_status += f' desde hace {duracion_riesgo}'
    
    session_mode = state_manager.get_state("session", "mode", "No definido")
    mode_text = f"Modo Sesión: <b>{session_mode.capitalize()}</b>"

    config_summary = f"""
<b>⚙️ Configuración Clave:</b>
  - Pérdida Máx. Diaria: {config.MAX_DAILY_LOSS_PCT}%
  - Riesgo Máx. por Trade: {config.MAX_TRADE_RISK_PCT}%
  - Máx. Posiciones Concurrentes: {config.MAX_CONCURRENT_POSITIONS}
"""

    return f"""
<b>📊 Estado Actual del Bot:</b>

{mode_text}
📈 Estrategia: <b>{active_strategy_name}</b>
💰 P/L Día: {daily_profit_loss_summary}
📊 Ops Día: {daily_operations_count_text}

🛡️ Escudo: {escudo_estado_texto}
🎯 Riesgo: {riesgo_status}

{posiciones_summary}
{closed_positions_summary}
{config_summary}{analysis_result_text}"""

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
        ganancias = ganancias_duracion_riesgo_forzado()
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
    load_configurations()
    text = f"""
<b>🕹️ Límites y Controles de Riesgo:</b>\n\nEstos son los límites de seguridad globales recomendados.\n\n📉 <b>Pérdida Máx. Diaria:</b> {config.MAX_DAILY_LOSS_PCT}%
   <code>(El bot se detiene si las pérdidas del día superan este %)</code>
⚖️ <b>Riesgo Máx. por Trade:</b> {config.MAX_TRADE_RISK_PCT}%
   <code>(Límite de riesgo para una sola operación)</code>
📊 <b>Máx. Posiciones Concurrentes:</b> {config.MAX_CONCURRENT_POSITIONS}
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

async def send_analysis_submenu(message: Union[Message, types.CallbackQuery], is_edit: bool = False):
    msg_target = getattr(message, 'message', message)
    if not isinstance(msg_target, Message):
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Generar Reporte de KPIs", callback_data="CMD_ANALISIS_GENERAR_KPIS")
    builder.button(text="🧠 Entrenar Modelo ML", callback_data="CMD_ANALISIS_ENTRENAR_ML")
    builder.button(text="🧪 Optimizar Estrategia", callback_data="CMD_ANALISIS_OPTIMIZAR_ESTRATEGIA")
    builder.button(text="🔄 Recargar Datos Históricos", callback_data="CMD_ANALISIS_RECARGAR_DATOS")
    builder.button(text="🔍 Ver Análisis Actual", callback_data="CMD_ANALISIS_VER_ACTUAL")
    builder.button(text="⬅️ Volver", callback_data="CMD_VOLVER")
    builder.adjust(1)
    text = "Opciones de análisis de mercado, datos y estrategias:"
    if is_edit:
        await edit_message_safely(msg_target, text, builder.as_markup())
    else:
        await msg_target.answer(text, reply_markup=builder.as_markup())

async def send_reports_submenu(message: Union[Message, types.CallbackQuery], is_edit: bool = False):
    msg_target = getattr(message, 'message', message)
    if not isinstance(msg_target, Message):
        return
    builder = InlineKeyboardBuilder()
    builder.button(text="📓 Generar Diario de Trading", callback_data="CMD_REPORTES_GENERAR_JOURNAL")
    builder.button(text="📄 Generar Reporte Diario", callback_data="CMD_REPORTES_GENERAR_DIARIO")
    builder.button(text="📜 Ver Historial de Operaciones", callback_data="CMD_REPORTES_VER_HISTORIAL")
    builder.button(text="📥 Descargar Reporte", callback_data="CMD_REPORTES_DESCARGAR")
    builder.button(text="⬅️ Volver", callback_data="CMD_VOLVER")
    builder.adjust(1)
    text = "Opciones para generar y consultar reportes:"
    if is_edit:
        await edit_message_safely(msg_target, text, builder.as_markup())
    else:
        await msg_target.answer(text, reply_markup=builder.as_markup())

async def send_config_submenu(message: Union[Message, types.CallbackQuery], is_edit: bool = False):
    msg_target = getattr(message, 'message', message)
    if not isinstance(msg_target, Message):
        return
    
    session_mode = state_manager.get_state("session", "mode", "No definido")
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Ver Configuración Actual", callback_data="CMD_CONFIG_VER_ACTUAL")
    builder.button(text="🔄 Recargar Configuración", callback_data="CMD_CONFIG_RECARGAR")
    builder.button(text=f"⚙️ Cambiar Modo (Actual: {session_mode.capitalize()})", callback_data="CMD_CONFIG_CHANGE_MODE")
    builder.button(text="⬅️ Volver", callback_data="CMD_VOLVER")
    builder.adjust(1)
    text = "Opciones de configuración del bot:"
    if is_edit:
        await edit_message_safely(msg_target, text, builder.as_markup())
    else:
        await msg_target.answer(text, reply_markup=builder.as_markup())

async def send_historical_operations(message: types.Message):
    operaciones_path = "data/operaciones/operaciones.csv"
    try:
        if not os.path.exists(operaciones_path):
            await message.answer("❌ No se encontró el archivo de historial de operaciones.")
            return
        df = pd.read_csv(operaciones_path, parse_dates=['timestamp_open'])
        if df.empty:
            await message.answer("ℹ️ El historial de operaciones está vacío.")
            return
        
        # Filter by current day
        today = datetime.now().date()
        daily_operations = df[df['timestamp_open'].dt.date == today]

        # Take the last 3 from the daily operations
        df_recent = daily_operations.tail(3)
        
        text = "<b>📜 Últimas 3 Operaciones del Día:</b>\n\n"
        for _, row in df_recent.iterrows():
            pnl_percent = row['pnl_percent']
            emoji = "✅" if pnl_percent >= 0 else "❌"
            timestamp_open_str = pd.to_datetime(row['timestamp_open']).strftime("%Y-%m-%d %H:%M")
            symbol = row['symbol']
            side = row['side']
            entry_price = row['entry_price']
            exit_price = row['exit_price'] if pd.notna(row['exit_price']) else "N/A"
            reason_open = row['reason_open']
            reason_close = row['reason_close'] if pd.notna(row['reason_close']) else "N/A"
            formatted_exit_price = f"{exit_price:.2f}" if pd.notna(row['exit_price']) else str(exit_price)
            formatted_pnl_percent = f"{pnl_percent:+.2f}" if pd.notna(pnl_percent) else "N/A"
            text += f"{emoji} <code>{timestamp_open_str}</code> - <b>{COLUMN_TRANSLATIONS.get('symbol', 'Símbolo')}: {symbol}</b> ({COLUMN_TRANSLATIONS.get('side', 'Tipo')}: {side})\n  - {COLUMN_TRANSLATIONS.get('entry_price', 'Entrada')}: {entry_price:.2f} | {COLUMN_TRANSLATIONS.get('exit_price', 'Salida')}: {formatted_exit_price}\n  - {COLUMN_TRANSLATIONS.get('pnl_percent', 'P&L')}: <b>{formatted_pnl_percent}%</b>\n  - {COLUMN_TRANSLATIONS.get('reason_open', 'Motivo Apertura')}: {reason_open}\n  - {COLUMN_TRANSLATIONS.get('reason_close', 'Motivo Cierre')}: {reason_close}\n\n"
        await message.answer(text)
    except Exception as e:
        logger.error(f"Error al obtener el historial de operaciones: {e}", exc_info=True)
        await message.answer("❌ Ocurrió un error al leer el historial de operaciones.")

async def handle_shield_action(chat_id: int, message: Message, shield_type: str, activate: bool, is_main_menu: bool = False):
    if activate:
        await activar_escudo(bot, chat_id, tipo=shield_type, fuente="manual")
    else:
        await desactivar_escudo(bot, chat_id, fuente="manual")

    if is_main_menu:
        text, keyboard = get_main_menu()
        await edit_message_safely(message, text, keyboard)
    else:
        await send_shield_submenu(message, is_edit=True)

async def send_shield_submenu(message: Union[Message, types.CallbackQuery], is_edit: bool = False):
    msg_target = getattr(message, 'message', message)
    if not isinstance(msg_target, Message):
        return
    builder = InlineKeyboardBuilder()
    is_active, status_text = obtener_estado_escudo()
    text = f"<b>🛡️ Gestión de Escudos de Volatilidad:</b>\n\nEstado actual: {status_text}"
    if not is_active or escudo_activo() != 'volatilidad_alta':
        builder.button(text="Activar (Volatilidad Alta)", callback_data="CMD_ESCUDO_ACTIVAR_VOLATILIDAD_ALTA")
    else:
        builder.button(text="🔓 Desactivar Escudo", callback_data="CMD_ESCUDO_DESACTIVAR")
    builder.button(text="⬅️ Volver a Riesgo", callback_data="CMD_VOLVER_RIESGO")
    builder.adjust(1)
    if is_edit:
        await edit_message_safely(msg_target, text, builder.as_markup())
    else:
        await msg_target.answer(text, reply_markup=builder.as_markup())


async def get_mode_selection_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔴 Modo LIVE", callback_data="select_mode:live")
    builder.button(text="🟢 Modo TEST", callback_data="select_mode:test")
    builder.adjust(1)
    return "Por favor, selecciona el modo de operación del bot:", builder.as_markup()

@dp.message(Command("start", "menu", "home"))
async def start_command(message: Message, state: FSMContext):
    logger.info(f"Comando /start recibido de {message.from_user.id}")
    chat_id = message.chat.id
    session_mode = state_manager.get_state("session", "mode")

    if session_mode is None:
        initial_text, initial_keyboard = await get_mode_selection_keyboard()
        await send_message(bot, chat_id, initial_text, reply_markup=initial_keyboard)
        await state.set_state(InitialStates.waiting_for_mode_selection)
    else:
        status_text = await get_current_status_text()
        await send_message(bot, chat_id, status_text)

        # Asegurar que el menú principal se muestre correctamente
        menu_text, keyboard = get_main_menu()
        if not menu_text or not keyboard:
            logger.error("Error al generar el menú principal. Verifica la función get_main_menu.")
            await send_message(bot, chat_id, "❌ Error al generar el menú principal. Intenta nuevamente más tarde.")
        else:
            await send_message(bot, chat_id, menu_text, reply_markup=keyboard)

@dp.message(Command("help"))
async def help_command(message: Message):
    logger.info(f"Comando /help recibido de {message.from_user.id}")
    help_text = ("""
<b>❓ Ayuda del Bot de Trading</b>

Usa los menús para interactuar con el bot.
- <b>Análisis:</b> Entrenar modelos, optimizar, etc.
- <b>Riesgo:</b> Gestionar el nivel de riesgo y los escudos.
- <b>Reportes:</b> Generar informes de rendimiento.
- <b>Configuración:</b> Ver y recargar ajustes.
- <b>Estado:</b> Ver un resumen del estado actual.
- /start, /menu, /home: Vuelve al menú principal.""")
    await send_message(bot, message.chat.id, help_text)

@dp.message(Command("go_live"))
async def go_live_command(message: Message, state: FSMContext):
    logger.info(f"Comando /go_live recibido de {message.from_user.id}")
    chat_id = message.chat.id
    session_mode = state_manager.get_state("session", "mode")
    if session_mode != "live":
        await send_message(bot, chat_id, "❌ El bot no está en modo LIVE para esta sesión.")
        return
    if not os.path.exists(config.LIVE_UNLOCK_FILE_PATH):
        await send_message(bot, chat_id, f"❌ El archivo de desbloqueo no se encontró.")
        return
    if state_manager.get_state("live_mode", "unlocked", False):
        await send_message(bot, chat_id, "✅ El bot ya está operando en modo LIVE.")
        menu_text, keyboard = get_main_menu()
        await send_message(bot, chat_id, menu_text, reply_markup=keyboard)
        return
    await send_message(bot, chat_id, "⚠️ Para confirmar la operación en modo LIVE, escribe <b>CONFIRMAR LIVE</b>.")
    await state.set_state(LiveModeStates.waiting_for_live_confirmation)

@dp.message(LiveModeStates.waiting_for_live_confirmation)
async def process_live_confirmation(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    if message.text and message.text.upper() == "CONFIRMAR LIVE":
        state_manager.set_state("live_mode", "unlocked", True)
        await send_message(bot, chat_id, "✅ ¡El bot ha sido desbloqueado para operar en modo LIVE!")
        logger.info(f"Bot desbloqueado para modo LIVE por el usuario {message.from_user.id})")
        menu_text, keyboard = get_main_menu()
        await send_message(bot, chat_id, menu_text, reply_markup=keyboard)
        await state.clear()
    else:
        await send_message(bot, chat_id, "❌ Confirmación incorrecta. Por favor, escribe 'CONFIRMAR LIVE' para proceder o /cancelar para anular.")

@dp.callback_query(lambda c: c.data and c.data.startswith('select_mode:'))
async def process_mode_selection(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    message = cast(Message, cq.message)
    mode = cq.data.split(':')[1]
    state_manager.set_state("session", "mode", mode)
    
    confirmation_text = f"✅ Modo de sesión establecido en <b>{mode.capitalize()}</b>."
    await edit_message_safely(message, confirmation_text)

    status_text = await get_current_status_text()
    await send_message(bot, message.chat.id, status_text)
    
    menu_text, keyboard = get_main_menu()
    await send_message(bot, message.chat.id, menu_text, reply_markup=keyboard)
    await state.clear()

@dp.callback_query()
async def handle_callback_query(cq: types.CallbackQuery, state: FSMContext):
    await cq.answer()
    data = cq.data
    message = cast(Message, cq.message)
    chat_id = message.chat.id
    if data == "CMD_VOLVER":
        text, keyboard = get_main_menu()
        await edit_message_safely(message, text, keyboard)
    elif data == "CMD_ESTADO_GENERAL":
        text = await get_current_status_text()
        await send_message(bot, chat_id, text)
    elif data == "CMD_DETENER_BOT":
        await handle_shield_action(chat_id, message, "extremo", True, is_main_menu=True)
    elif data == "CMD_REANUDAR_BOT":
        await handle_shield_action(chat_id, message, "", False, is_main_menu=True)
    elif data == "CMD_MENU_RIESGO":
        await send_risk_submenu(cq, is_edit=True)
    elif data == "CMD_MENU_ANALISIS":
        await send_analysis_submenu(cq, is_edit=True)
    elif data == "CMD_MENU_REPORTES":
        await send_reports_submenu(cq, is_edit=True)
    elif data == "CMD_MENU_CONFIG":
        await send_config_submenu(cq, is_edit=True)
    elif data == "CMD_CONFIG_CHANGE_MODE":
        text, keyboard = await get_mode_selection_keyboard()
        await edit_message_safely(message, text, keyboard)
        await state.set_state(InitialStates.waiting_for_mode_selection)
    elif data == "CMD_RIESGO_FORZAR":
        await message.edit_text("Por favor, envía el porcentaje de riesgo a forzar (ej. `5`).")
        await state.set_state(RiskStates.waiting_for_risk_percentage)
    elif data == "CMD_RIESGO_LIBERAR":
        restaurar_riesgo_automatico()
        await message.edit_text("✅ Riesgo automático restaurado.")
        await send_risk_submenu(cq, is_edit=False)
    elif data == "CMD_RIESGO_GESTIONAR_ESCUDOS":
        await send_shield_submenu(cq, is_edit=True)
    elif data == "CMD_VOLVER_RIESGO":
        await send_risk_submenu(cq, is_edit=True)
    elif data == "CMD_RIESGO_LIMITES":
        await send_risk_limits_submenu(cq, is_edit=True)
    elif data == "CMD_LIMIT_SET_MAX_DAILY_LOSS":
        await state.set_state(RiskStates.waiting_for_limit_value)
        await state.update_data(limit_to_edit="MAX_DAILY_LOSS_PCT", limit_name="Pérdida Máxima Diaria", limit_type="float")
        await message.edit_text("Envíe el nuevo valor para <b>Pérdida Máxima Diaria</b> (ej. `5.5`).")
    elif data == "CMD_LIMIT_SET_MAX_TRADE_RISK":
        await state.set_state(RiskStates.waiting_for_limit_value)
        await state.update_data(limit_to_edit="MAX_TRADE_RISK_PCT", limit_name="Riesgo Máximo por Trade", limit_type="float")
        await message.edit_text("Envíe el nuevo valor para <b>Riesgo Máximo por Trade</b> (ej. `1.0`).")
    elif data == "CMD_LIMIT_SET_MAX_CONCURRENT":
        await state.set_state(RiskStates.waiting_for_limit_value)
        await state.update_data(limit_to_edit="MAX_CONCURRENT_POSITIONS", limit_name="Máximo de Posiciones Concurrentes", limit_type="int")
        await message.edit_text("Envíe el nuevo valor para <b>Máximo de Posiciones Concurrentes</b> (ej. `3`).")
    elif data == "CMD_LIMIT_RESTORE_DEFAULTS":
        defaults = {"MAX_DAILY_LOSS_PCT": "5.0", "MAX_TRADE_RISK_PCT": "1.0", "MAX_CONCURRENT_POSITIONS": "3"}
        for key, value in defaults.items():
            await update_env_file(key, value)
        await message.edit_text("✅ Límites restaurados a los valores recomendados.")
        await send_risk_limits_submenu(cq, is_edit=False)
    elif data == "CMD_ESCUDO_ACTIVAR_VOLATILIDAD_ALTA":
        await handle_shield_action(chat_id, message, "volatilidad_alta", True)
    elif data == "CMD_ESCUDO_DESACTIVAR":
        await handle_shield_action(chat_id, message, "", False)
    elif data == "CMD_REPORTES_VER_HISTORIAL":
        await send_historical_operations(message)
        await send_reports_submenu(cq, is_edit=False)
    elif data == "CMD_ANALISIS_GENERAR_KPIS":
        await edit_message_safely(message, "📊 Generando tu reporte de KPIs. Esto puede tardar un momento...")
        await generar_reporte_kpis(bot, chat_id)
        await send_analysis_submenu(message, is_edit=False)
    elif data == "CMD_REPORTES_GENERAR_DIARIO":
        await message.edit_text("📄 Generando reporte diario...")
        await generar_reporte_diario(bot, chat_id)
        await send_reports_submenu(cq, is_edit=False)
    elif data == "CMD_REPORTES_GENERAR_JOURNAL":
        await message.edit_text("📓 Generando diario de trading...")
        # Por defecto, el diario de los últimos 7 días
        await generar_reporte_journal(bot, chat_id, days=7)
        await send_reports_submenu(cq, is_edit=False)
    elif data == "CMD_MANUAL_BUY_BTC":
        decision_data = {
            "type": "MANUAL_TRADE",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.0001,
            "order_type": "MARKET",
            "strategy_id": "MANUAL_USER_INPUT",
            "timestamp_decision": datetime.now().isoformat(),
            "user_id": message.from_user.id,
        }
        success = mq.publish_decision(decision_data)
        if success:
            await edit_message_safely(message, "✅ Orden de compra manual enviada a la cola de ejecución.")
        else:
            await edit_message_safely(message, "❌ Error al enviar orden manual a la cola.")

async def update_env_file(key: str, value: str) -> bool:
    env_path = ".env"
    try:
        lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
        with open(env_path, 'w') as f:
            found = False
            for line in lines:
                if line.strip().startswith(f"{key}="):
                    f.write(f"{key}={value}\n")
                    found = True
                else:
                    f.write(line)
            if not found:
                f.write(f"\n{key}={value}\n")
        logger.info(f"Archivo .env actualizado: {key}={value}")
        load_configurations()
        return True
    except Exception as e:
        logger.error(f"No se pudo actualizar el archivo .env: {e}", exc_info=True)
        return False

@dp.message(RiskStates.waiting_for_risk_percentage)
async def process_risk_percentage(message: Message, state: FSMContext):
    user_input = message.text or ""
    chat_id = message.chat.id
    try:
        risk_percentage = float(user_input.replace(',', '.'))
        if not (0 <= risk_percentage <= 100):
            await message.answer("❌ El porcentaje de riesgo debe estar entre 0 y 100.")
            return
        activar_riesgo_forzado(risk_percentage / 100) # Convert to decimal
        await message.answer(f"✅ Riesgo forzado activado al <b>{risk_percentage:.2f}%</b>.")
        await state.clear()
        await send_risk_submenu(message, is_edit=False)
    except ValueError:
        await message.answer("❌ Entrada inválida. Por favor, introduce un número válido para el porcentaje de riesgo (ej. `5`).")
    except Exception as e:
        logger.error(f"Error al procesar el porcentaje de riesgo: {e}", exc_info=True)
        await message.answer("❌ Ocurrió un error al forzar el riesgo.")
    finally:
        await state.clear()

@dp.message(RiskStates.waiting_for_limit_value)
async def process_limit_value(message: Message, state: FSMContext):
    user_input = message.text or ""
    state_data = await state.get_data()
    limit_key = state_data.get("limit_to_edit")
    limit_name = state_data.get("limit_name")
    limit_type = state_data.get("limit_type", "float")
    if not limit_key or not limit_name:
        await message.answer("❌ Error interno. Intente de nuevo.")
        await state.clear()
        return
    try:
        if limit_type == "int":
            new_value = int(user_input)
            if new_value <= 0: raise ValueError("El valor debe ser positivo.")
        else:
            new_value = float(user_input.replace(',', '.'))
            if new_value <= 0: raise ValueError("El valor debe ser positivo.")
        success = await update_env_file(limit_key, str(new_value))
        if success:
            await message.answer(f"✅ Límite '<b>{limit_name}</b>' actualizado a <b>{new_value}</b>.")
        else:
            await message.answer(f"❌ Error al actualizar el límite.")
    except (ValueError, TypeError):
        await message.answer("❌ Entrada inválida. Introduce un número válido.")
    finally:
        await state.clear()
        await send_risk_limits_submenu(message, is_edit=False)

# === Main execution ===
async def main():
    # Configure the alerter singleton
    alerter.configure(bot_instance=bot, chat_id=chat_id_int)

    # Set bot commands
    await set_main_bot_commands(bot)
    # Test message after startup
    try:
        await alerter.send_alert(
            alert_key="bot_startup",
            severity=SeverityLevel.INFO,
            source="System",
            message="Bot iniciado y listo para operar.",
            details={"bot_version": "1.2.3"} # Example detail
        )
        logger.info(f"Mensaje de inicio enviado a {chat_id_int}")
    except Exception as e:
        logger.error(f"Error al enviar mensaje de inicio: {e}", exc_info=True)
    # Start polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error durante el polling del bot: {e}", exc_info=True)
        await alerter.send_alert(
            alert_key="bot_critical_failure",
            severity=SeverityLevel.CRITICAL,
            source="System",
            message="El bot ha fallado de forma crítica y se ha detenido.",
            details={"error": str(e)}
        )

if __name__ == "__main__":
    # Load configurations at startup
    load_configurations()
    # Configure logging based on loaded config
    logging.basicConfig(level=config.LOG_LEVEL) # Use config.LOG_LEVEL
    logger = logging.getLogger(__name__)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot detenido manualmente.")
    except Exception as e:
        logger.error(f"Error crítico en el bot: {e}", exc_info=True)