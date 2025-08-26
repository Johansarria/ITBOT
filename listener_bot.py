# listener_bot.py
"""
Módulo principal para el bot de Telegram (Listener).

Este bot actúa como la interfaz de usuario para el sistema de trading.
Permite a los usuarios:
- Ver el estado del bot y las operaciones.
- Iniciar análisis y optimizaciones.
- Gestionar la configuración de riesgo y los escudos de protección.
- Generar y recibir reportes.
- Ejecutar comandos de forma manual.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Union

import pandas as pd
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- Importaciones de Módulos del Proyecto ---
from config import settings
from download_historical_data import download_and_save_klines
from ml_model_trainer import train_and_save_model
from modules.analisis_bot import get_historical_klines, procesar_comando_analisis
from optimize_strategy import optimize_risk_thresholds_ga
from strategies.strategy_manager import StrategyManager
from utils.bot_commands import set_bot_commands as set_main_bot_commands
from utils.daily_operations_counter import reset_daily_operations_count_manual
from utils.order_executor import evaluar_y_ejecutar_operacion
from utils.position_manager import (
    get_closed_positions_summary,
    get_open_positions_summary,
    manage_open_positions)
from utils.reporte_manager import generar_reporte_diario
from utils.reportes_bot import exportar_y_enviar_reporte
from utils.risk_manager import (
                               activar_riesgo_forzado,
                                calcular_probabilidad_ganancia_perdida,
                                duracion_riesgo_forzado,
                                ganancias_durante_riesgo_forzado,
                                obtener_riesgo_actual,
                                operaciones_en_riesgo_forzado,
                                restaurar_riesgo_automatico,
                                riesgo_forzado_activo)
from utils.shield_manager import (
                               activar_escudo, desactivar_escudo,
                                obtener_estado_escudo_texto)
from utils.telegram_handler import send_message

# === Configuración de Logging y Constantes ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Inicialización de Componentes Principales ===
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
strategy_manager = StrategyManager()
CHAT_ID = settings.TELEGRAM_CHAT_ID

# === Definición de Estados (FSM) para Conversaciones ===
class RiskManagementStates(StatesGroup):
    waiting_for_force_risk_percentage = State()

# === Caché Global para el Último Análisis ===
_last_analysis_cache = {"timestamp": None, "result": None, "strategy_name": None}


# === Funciones de Menús y UI ===

def get_main_menu() -> tuple[str, types.InlineKeyboardMarkup]:
    """Construye y devuelve el menú principal del bot."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Análisis", callback_data="menu:analisis")
    builder.button(text="🛡️ Riesgo", callback_data="menu:riesgo")
    builder.button(text="📈 Reportes", callback_data="menu:reportes")
    builder.button(text="⚙️ Configuración", callback_data="menu:config")
    builder.button(text="ℹ️ Estado", callback_data="menu:estado")
    builder.button(text="🛑 Detener Bot", callback_data="cmd:stop_bot")
    builder.adjust(1)
    return "Menú principal", builder.as_markup()

async def get_current_status_text() -> str:
    """Recopila y formatea el texto de estado completo del bot."""
    escudo_estado_texto = obtener_estado_escudo_texto()
    posiciones_summary = await get_open_positions_summary(bot)
    riesgo_activo = riesgo_forzado_activo()
    riesgo_actual_pct = obtener_riesgo_actual() * 100
    duracion_riesgo = duracion_riesgo_forzado() if riesgo_activo else "N/A"
    active_strategy = strategy_manager.get_active_strategy()
    active_strategy_name = active_strategy.name if active_strategy else "N/A"

    # --- Resumen de Operaciones Diarias ---
    daily_profit_loss_summary = "0.00%"
    daily_ops_text = "Total: 0 (Pos: 0, Neg: 0)"
    try:
        ops_df = pd.read_csv("data/operaciones/operaciones.csv", parse_dates=['timestamp_open'])
        today = datetime.now().date()
        daily_ops = ops_df[ops_df['timestamp_open'].dt.date == today]
        if not daily_ops.empty:
            pnl_sum = daily_ops['profit_loss_pct'].sum()
            wins = daily_ops[daily_ops['profit_loss_pct'] >= 0].shape[0]
            losses = daily_ops[daily_ops['profit_loss_pct'] < 0].shape[0]
            daily_profit_loss_summary = f"{pnl_sum:.2f}%"
            daily_ops_text = f"Total: {len(daily_ops)} (Pos: {wins}, Neg: {losses})"
    except FileNotFoundError:
        logger.warning("Archivo de operaciones no encontrado para resumen diario.")
    except Exception as e:
        logger.error(f"Error al calcular resumen diario: {e}", exc_info=True)
        daily_profit_loss_summary = "Error"

    # --- Texto de Último Análisis (desde caché) ---
    analysis_result_text = ""
    if _last_analysis_cache.get("result"):
        res = _last_analysis_cache["result"]
        strat_name = _last_analysis_cache["strategy_name"]
        analysis_result_text = (
            f"\n--- Último Análisis ({strat_name}) ---" 
            f"\nDecisión: <b>{res.get('decision', 'N/A')}</b> | Score: {res.get('score', 'N/A')}"
        )

    # --- Ensamblaje del Texto Final ---
    riesgo_status = f"{('Forzado' if riesgo_activo else 'Automático')} ({riesgo_actual_pct:.2f}%)"
    if riesgo_activo:
        riesgo_status += f' desde hace {duracion_riesgo}'

    return (
        f"<b>📊 Estado Actual del Bot:</b>\n\n"
        f"📈 Estrategia: <b>{active_strategy_name}</b>\n"
        f"💰 P/L Día: {daily_profit_loss_summary}\n"
        f"📊 Ops Día: {daily_ops_text}\n\n"
        f"🛡️ Escudo: {escudo_estado_texto}\n"
        f"🎯 Riesgo: {riesgo_status}\n\n"
        f"{posiciones_summary}\n"
        f"{get_closed_positions_summary()}"
        f"{analysis_result_text}"
    )

async def send_submenu(message: Message, text: str, keyboard: types.InlineKeyboardMarkup, is_edit: bool = True):
    """Función genérica para enviar o editar un submenú."""
    try:
        if is_edit:
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            logger.info("Mensaje no modificado, omitiendo edición.")
        else:
            logger.error(f"Error de Telegram al enviar submenú: {e}", exc_info=True)
            # Si la edición falla, intenta enviar un nuevo mensaje
            if is_edit:
                await message.answer(text, reply_markup=keyboard)


# === Manejadores de Comandos de Telegram ===

@dp.message(Command("start", "menu", "home"))
async def start_command(message: Message):
    """Manejador para los comandos /start, /menu y /home. Muestra el estado y el menú principal."""
    logger.info(f"Comando '{message.text}' recibido de {message.from_user.id}")
    status_text = await get_current_status_text()
    await message.answer(status_text)
    menu_text, keyboard = get_main_menu()
    await message.answer(menu_text, reply_markup=keyboard)

@dp.message(Command("help"))
async def help_command(message: Message):
    """Muestra un mensaje de ayuda detallado."""
    logger.info(f"Comando /help recibido de {message.from_user.id}")
    help_text = (
        "<b>❓ Ayuda del Bot de Trading</b>\n\n"
        "Este bot es la interfaz para tu sistema de trading. Usa los botones para navegar.\n\n"
        "- <b>Análisis:</b> Entrena modelos, optimiza estrategias y recarga datos.\n"
        "- <b>Riesgo:</b> Gestiona el riesgo, forzando un porcentaje o usando el modo automático, y controla los escudos de volatilidad.\n"
        "- <b>Reportes:</b> Genera y visualiza reportes de rendimiento.\n"
        "- <b>Configuración:</b> Visualiza y recarga la configuración del sistema.\n"
        "- <b>Estado:</b> Muestra un resumen del estado actual del bot.\n"
        "- <b>Detener Bot:</b> Para de forma segura las operaciones del bot.\n\n"
        "Usa /start o /home para volver al menú principal en cualquier momento."
    )
    await message.answer(help_text)


# === Manejadores de Acciones de Botones (Callback Queries) ===

@dp.callback_query(F.data.startswith("menu:"))
async def handle_menu_callbacks(cb: types.CallbackQuery):
    """Manejador principal para la navegación de menús."""
    action = cb.data.split(":")[1]
    message = cb.message
    if not message: return

    logger.info(f"Navegando al menú: {action}")

    if action == "analisis":
        builder = InlineKeyboardBuilder()
        builder.button(text="🧠 Entrenar Modelo ML", callback_data="cmd:train_ml")
        builder.button(text="🧪 Optimizar Estrategia", callback_data="cmd:optimize_strategy")
        builder.button(text="🔄 Recargar Datos Históricos", callback_data="cmd:reload_data")
        builder.button(text="⬅️ Volver", callback_data="menu:main")
        builder.adjust(1)
        await send_submenu(message, "Menú de Análisis:", builder.as_markup())

    elif action == "riesgo":
        riesgo_activo = riesgo_forzado_activo()
        builder = InlineKeyboardBuilder()
        if riesgo_activo:
            builder.button(text="🔓 Liberar Riesgo", callback_data="cmd:release_risk")
        else:
            builder.button(text="🔒 Forzar Riesgo", callback_data="cmd:force_risk")
        builder.button(text="🛡️ Gestionar Escudos", callback_data="menu:shields")
        builder.button(text="⬅️ Volver", callback_data="menu:main")
        builder.adjust(1)
        await send_submenu(message, "Menú de Gestión de Riesgo:", builder.as_markup())

    elif action == "reportes":
        builder = InlineKeyboardBuilder()
        builder.button(text="📄 Reporte Diario", callback_data="cmd:report_daily")
        builder.button(text="📜 Reporte por Rango", callback_data="cmd:report_range")
        builder.button(text="⬅️ Volver", callback_data="menu:main")
        builder.adjust(1)
        await send_submenu(message, "Menú de Reportes:", builder.as_markup())

    elif action == "config":
        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Ver Configuración", callback_data="cmd:view_config")
        builder.button(text="🔄 Recargar Configuración", callback_data="cmd:reload_config")
        builder.button(text="⬅️ Volver", callback_data="menu:main")
        builder.adjust(1)
        await send_submenu(message, "Menú de Configuración:", builder.as_markup())

    elif action == "estado":
        status_text = await get_current_status_text()
        await cb.answer(status_text, show_alert=True)

    elif action == "shields":
        is_shield_active = "ACTIVO" in obtener_estado_escudo_texto()
        builder = InlineKeyboardBuilder()
        if not is_shield_active:
            builder.button(text="🛡️ Activar (Volatilidad Alta)", callback_data="cmd:shield_on_high")
            builder.button(text="🚨 Activar (Extremo)", callback_data="cmd:shield_on_extreme")
        else:
            builder.button(text="🔓 Desactivar Escudo", callback_data="cmd:shield_off")
        builder.button(text="⬅️ Volver a Riesgo", callback_data="menu:riesgo")
        builder.adjust(1)
        await send_submenu(message, f"Gestión de Escudos\nEstado: {obtener_estado_escudo_texto()}", builder.as_markup())

    elif action == "main":
        menu_text, keyboard = get_main_menu()
        await send_submenu(message, menu_text, keyboard)

    await cb.answer()


@dp.callback_query(F.data.startswith("cmd:"))
async def handle_command_callbacks(cb: types.CallbackQuery, state: FSMContext):
    """Manejador para callbacks que ejecutan una acción."""
    action = cb.data.split(":")[1]
    message = cb.message
    if not message: return

    logger.info(f"Ejecutando comando: {action}")
    await cb.answer(f"Ejecutando: {action}...") # Feedback inmediato al usuario

    # --- Acciones de Riesgo y Escudos ---
    if action == "release_risk":
        restaurar_riesgo_automatico()
        await message.edit_text("✅ Riesgo automático restaurado.")
        await asyncio.sleep(1)
        await handle_menu_callbacks(cb) # Vuelve al menú
    
    elif action == "force_risk":
        await state.set_state(RiskManagementStates.waiting_for_force_risk_percentage)
        await message.edit_text("Por favor, envía el porcentaje de riesgo a forzar (ej. `5` para 5%).")

    elif action.startswith("shield_on"):
        shield_type = "extremo" if action.endswith("extreme") else "volatilidad_alta"
        await message.edit_text(f"Activando escudo '{shield_type}'...")
        await activar_escudo(bot, CHAT_ID, tipo=shield_type, fuente="manual")
        await message.edit_text(f"✅ Escudo '{shield_type}' activado.")
    
    elif action == "shield_off":
        await message.edit_text("Desactivando escudo...")
        await desactivar_escudo(bot, CHAT_ID, fuente="manual")
        await message.edit_text("✅ Escudo desactivado.")

    # --- Acciones de Análisis y Datos ---
    elif action == "train_ml":
        await message.edit_text("🧠 Iniciando entrenamiento del modelo ML. Esto puede tardar horas...")
        try:
            await asyncio.to_thread(train_and_save_model)
            await message.answer("✅ Entrenamiento del modelo ML completado.")
        except Exception as e:
            logger.error(f"Error en entrenamiento ML: {e}", exc_info=True)
            await message.answer(f"❌ Error en entrenamiento: {e}")

    elif action == "optimize_strategy":
        await message.edit_text("🧪 Iniciando optimización de estrategia. Esto puede tardar horas...")
        try:
            await asyncio.to_thread(optimize_risk_thresholds_ga)
            await message.answer("✅ Optimización de estrategia completada.")
        except Exception as e:
            logger.error(f"Error en optimización: {e}", exc_info=True)
            await message.answer(f"❌ Error en optimización: {e}")

    elif action == "reload_data":
        await message.edit_text("🔄 Recargando datos históricos (BTCUSDT, 4h, desde 2022)...")
        try:
            await download_and_save_klines(symbol="BTCUSDT", interval="4h", start_str="1 Jan, 2022")
            await message.answer("✅ Datos históricos recargados.")
        except Exception as e:
            logger.error(f"Error recargando datos: {e}", exc_info=True)
            await message.answer(f"❌ Error recargando datos: {e}")

    # --- Acciones de Reportes ---
    elif action == "report_daily":
        await message.edit_text("📄 Generando reporte diario...")
        # La función de generar reporte ya envía el mensaje, no necesitamos hacer más.
        await generar_reporte_diario(bot, CHAT_ID)

    # --- Lógica de Parada Segura ---
    elif action == "stop_bot":
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ SÍ, DETENER AHORA", callback_data="cmd:stop_bot_confirm")
        builder.button(text="❌ NO, CANCELAR", callback_data="menu:main")
        await send_submenu(message, "<b>¿Estás seguro?</b> Esto detendrá el sondeo de mensajes y apagará el bot.", builder.as_markup())

    elif action == "stop_bot_confirm":
        await message.edit_text("🛑 Deteniendo el bot de forma segura...")
        # dp.stop_polling() se llama en el bloque finally de start_bot()
        # para asegurar una parada limpia.
        # Aquí simplemente iniciamos el apagado.
        await dp.storage.close()
        await dp.fsm.storage.close()
        await bot.session.close()
        asyncio.get_running_loop().stop() # Detiene el bucle de eventos
        logger.info("Apagado iniciado por el usuario.")

    # Al final de una acción, usualmente volvemos a un menú
    if action not in ["force_risk", "stop_bot", "stop_bot_confirm"]:
        await handle_menu_callbacks(cb)


@dp.message(RiskManagementStates.waiting_for_force_risk_percentage)
async def process_forced_risk_percentage(message: Message, state: FSMContext):
    """Procesa el porcentaje de riesgo enviado por el usuario."""
    if not message.text or not message.text.isdigit():
        await message.answer("Por favor, envía solo un número para el porcentaje. Inténtalo de nuevo.")
        return

    risk_pct = float(message.text)
    activar_riesgo_forzado(risk_pct / 100.0)
    await message.answer(f"✅ Riesgo forzado activado al <b>{risk_pct}%</b>.")
    await state.clear()

    # Regresar al menú de riesgo
    builder = InlineKeyboardBuilder()
    builder.button(text="🔓 Liberar Riesgo", callback_data="cmd:release_risk")
    builder.button(text="🛡️ Gestionar Escudos", callback_data="menu:shields")
    builder.button(text="⬅️ Volver", callback_data="menu:main")
    builder.adjust(1)
    await send_submenu(message, "Menú de Gestión de Riesgo:", builder.as_markup(), is_edit=False)


# === Tareas Programadas (Scheduler) ===

async def main_trading_flow_task():
    """Tarea periódica que ejecuta el flujo principal de trading."""
    logger.info("Iniciando flujo principal de operación...")
    try:
        analysis_result = await procesar_comando_analisis(bot, CHAT_ID, "recomendar accion", send_telegram_message=False)
        if analysis_result and analysis_result.get("status") != "error":
            await evaluar_y_ejecutar_operacion(bot, CHAT_ID, analysis_result)
        await manage_open_positions()
        logger.info("Flujo principal de operación completado.")
    except Exception as e:
        logger.error(f"Error en el flujo principal de operación: {e}", exc_info=True)
        await send_message(bot, CHAT_ID, f"❌ Error en el flujo principal: {e}")

async def daily_reset_task():
    """Resetea contadores diarios."""
    logger.info("Ejecutando tarea diaria de reseteo.")
    reset_daily_operations_count_manual()
    await send_message(bot, CHAT_ID, "✅ Contadores diarios reseteados.")


# === Lógica de Arranque del Bot ===

def setup_scheduler() -> AsyncIOScheduler:
    """Crea, configura y devuelve el scheduler. No lo inicia."""
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(main_trading_flow_task, 'interval', minutes=15)
    scheduler.add_job(daily_reset_task, 'cron', hour=23, minute=59)
    scheduler.add_job(generar_reporte_diario, 'cron', hour=0, minute=5, args=[bot, CHAT_ID])
    scheduler.add_job(train_and_save_model, 'cron', day_of_week='sun', hour=2, minute=0)
    return scheduler

async def start_bot():
    """Función principal que configura y arranca el bot y el scheduler."""
    await set_main_bot_commands(bot)

    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler iniciado con tareas programadas.")

    await send_message(bot, CHAT_ID, "✅ <b>Bot iniciado y operativo.</b>")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Bot y scheduler detenidos limpiamente.")

# === Punto de Entrada Principal ===
if __name__ == "__main__":
    # Este bloque SÓLO se ejecuta cuando corres `python listener_bot.py`
    # NUNCA se ejecutará cuando pytest importe el archivo.
    logger.info("Iniciando el bot...")
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot detenido manualmente.")
