# run_bot.py

import asyncio
import subprocess
import logging
import aiohttp
import os
from datetime import date
from datetime import datetime, timedelta
from utils.state_manager import StateManager
# from utils.technical_analysis import analyze_market # Reemplazado por StrategyManager
from strategies.strategy_manager import StrategyManager
from utils.technical_analysis import get_historical_klines
from utils.order_executor import evaluar_y_ejecutar_operacion
from utils.shield_manager import verificar_condiciones_mercado
from utils.binance_client import close_binance_client
from utils.telegram_handler import send_message, shutdown_bot
from utils.message_queue import mq
from utils.risk_manager import (
    riesgo_forzado_activo,
    duracion_riesgo_forzado,
    ganancias_durante_riesgo_forzado,
    operaciones_en_riesgo_forzado,
    calcular_probabilidad_ganancia_perdida,
    recordar_riesgo_forzado,
    restaurar_riesgo_automatico,
    desactivar_recordatorio_hoy
)
# REMOVED: from utils.env_loader import load_env
# from utils.telegram_handler import bot_instance as global_bot_instance # Ya no se importa
# from utils.telegram_handler import TELEGRAM_CHAT_ID as global_chat_id # Ya no se importa
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from utils.logger_setup import setup_logging
import config # ADDED: Import config
from apscheduler.schedulers.asyncio import AsyncIOScheduler # ADDED
from listener_bot import dp # AÑADIR ESTA LÍNEA

setup_logging()
logger = logging.getLogger(__name__) # Moved logger initialization here

# Cargar umbrales optimizados al inicio
from utils import risk_manager
umbrales = risk_manager.cargar_umbrales_optimizado()
# Opcional: podrías querer pasar estos umbrales a las estrategias que los necesiten
# Por ahora, el risk_manager los puede leer si es necesario.
logger.info(f"Umbrales de riesgo optimizados cargados: {umbrales}")

# Guardar referencia global de procesos hijos
active_subprocesses = []

async def retrain_ml_model_periodically(bot_instance: Bot, chat_id: int, interval_hours: int = 24):
    """
    Ejecuta el pipeline de entrenamiento ML de forma periódica y notifica por Telegram.
    """
    global active_subprocesses
    while True:
        try:
            await send_message(bot_instance, chat_id, "🤖 Iniciando retraining automático del modelo ML...")
            python_exec = os.path.join(os.getcwd(), ".venv/bin/python")
            proc = await asyncio.create_subprocess_exec(
                python_exec, 'train_pipeline.py',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            active_subprocesses.append(proc)
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                await send_message(bot_instance, chat_id, "✅ Retraining ML completado exitosamente.")
            else:
                await send_message(bot_instance, chat_id, f"❌ Error en retraining ML:\n{stderr.decode()}")
        except Exception as e:
            await send_message(bot_instance, chat_id, f"❌ Excepción en retraining automático: {e}")
        await asyncio.sleep(interval_hours * 3600)

async def daily_data_update_task(bot_instance: Bot, chat_id: int):
    logger.info("Iniciando tarea de actualización diaria de datos históricos.")
    try:
        await send_message(bot_instance, chat_id, "⏳ Iniciando actualización diaria de datos históricos para el modelo ML...")
        await download_and_save_klines(
            symbol=config.TRADING_PAIR,
            interval="4h", # Assuming 4h is the interval for ML data
            start_str="1 Jan, 2022", # This will be ignored if append_to_existing is True and file exists
            output_path="data/analisis/",
            file_prefix="historical_klines",
            append_to_existing=True
        )
        await send_message(bot_instance, chat_id, "✅ Actualización diaria de datos históricos completada.")
    except Exception as e:
        logger.error(f"Error en la tarea de actualización diaria de datos: {e}", exc_info=True)
        await send_message(bot_instance, chat_id, f"❌ Error en actualización diaria de datos históricos: {e}")

from utils.telegram_handler import await_confirmation
from download_historical_data import download_and_save_klines

async def flujo_principal(bot_instance: Bot, chat_id: int) -> None:
    """
    Ejecuta el flujo principal del bot:
    1. Verifica condiciones de mercado y escudos.
    2. Realiza análisis técnico con la estrategia activa.
    3. Publica decisiones en la cola de ejecución si corresponde.
    4. Envía mensajes de estado y resultado por Telegram.
    Args:
        bot_instance (Bot): Instancia del bot de Telegram.
        chat_id (int): ID del chat de Telegram.
    """
    logger.info("Iniciando flujo principal del bot.")

    try:
        # --- PASO 1: VERIFICACIÓN DE ESCUDOS Y CONDICIONES DE MERCADO ---
        logger.info("Verificando condiciones de mercado y escudos.")
        escudo_msg_dict = await verificar_condiciones_mercado(bot_instance, chat_id)
        if escudo_msg_dict["status"] == "DANGER":
            logger.warning(f"Escudo de protección activado: {escudo_msg_dict['reason']}")
            await send_message(bot_instance, chat_id, f"🛡️ Escudo de Protección Activado 🛡️\n\nRazón: {escudo_msg_dict['reason']}\n\nNo se realizarán operaciones en este ciclo.")
            return

        logger.info("Condiciones de mercado seguras. Procediendo con el análisis.")

        # --- PASO 2: ANÁLISIS TÉCNICO MULTIESTRATEGIA Y SELECCIÓN AUTÓNOMA ---
        logger.info("Cargando Strategy Manager y ejecutando análisis multiestrategia.")
        strategy_manager = StrategyManager()
        analysis_summary = await strategy_manager.analyze_all_strategies(symbol=config.TRADING_PAIR, interval=config.TRADING_INTERVAL, limit=200)

        if "error" in analysis_summary:
            logger.error(f"Error en análisis multiestrategia: {analysis_summary['error']}")
            await send_message(bot_instance, chat_id, f"❌ Error en análisis multiestrategia: {analysis_summary['error']}")
            return

        # Mostrar resultados de todas las estrategias (solo en logs para reducir ruido en Telegram)
        mensaje_analisis = "<b>Resultados de todas las estrategias:</b>\n"
        for strat, res in analysis_summary["results"].items():
            mensaje_analisis += f"\n<b>{strat}</b>: Decisión: {res.get('decision', 'N/A')}, Score: {res.get('score', 'N/A')}"
        mensaje_analisis += f"\n\n<b>Mejor estrategia:</b> {analysis_summary['best_strategy']}\n<b>Decisión recomendada:</b> {analysis_summary['best_decision']} (Score: {analysis_summary['best_score']})"
        logger.info(f"Análisis multiestrategia completado. Mejor: {analysis_summary['best_strategy']} - Decisión: {analysis_summary['best_decision']}")

        # --- PASO 4: DECISIÓN Y EJECUCIÓN DE LA ORDEN ---
        logger.info("Evaluando decisión de ejecución de orden autónoma.")
        best_decision = analysis_summary.get("best_decision", "Indeciso")
        best_strategy = analysis_summary.get("best_strategy", "UnknownStrategy")
        best_score = analysis_summary.get("best_score", "N/A")
        best_result = analysis_summary["results"].get(best_strategy, {}) if best_strategy else {}
        symbol = best_result.get("symbol", config.TRADING_PAIR)

        # Mapear decisiones complejas a acciones simples de compra/venta
        actionable_decision = None
        if best_decision == "COMPRAR" or best_decision == "COMPRAR_BAJO":
            actionable_decision = "BUY"
        elif best_decision == "VENDER" or best_decision == "VENDER_ALTO":
            actionable_decision = "SELL"

        if actionable_decision:
            decision_data = {
                "type": "AUTOMATED_TRADE",
                "symbol": symbol,
                "side": actionable_decision, # Usar la acción mapeada
                "quantity": 0.0001, # Placeholder, ajustar según gestión de riesgo
                "order_type": "MARKET",
                "strategy_id": best_strategy,
                "timestamp_decision": datetime.now().isoformat(),
                "analysis_score": best_score,
                # Otros campos relevantes del análisis
            }
            success = mq.publish_decision(decision_data)
            if success:
                ejecucion_resultado_msg = f"✅ Decisión de {best_decision} para {symbol} publicada en la cola de ejecución."
                logger.info(f"Decisión de trading automatizada publicada: {decision_data}")
            else:
                ejecucion_resultado_msg = f"❌ Error al publicar decisión de {best_decision} para {symbol} en la cola."
                logger.error(f"Fallo al publicar decisión de trading automatizada: {decision_data}")
        elif best_decision == "MANTENER":
            ejecucion_resultado_msg = f"ℹ️ Decisión de análisis: MANTENER. No se publicó ninguna orden."
            logger.info("Decisión de MANTENER registrada. No se requiere acción adicional.")
        else:
            ejecucion_resultado_msg = f"ℹ️ Decisión de análisis: {best_decision}. No se publicó ninguna orden."
            logger.info(f"No se publicó ninguna orden para la decisión: {best_decision}")

        # Enviar mensaje a Telegram solo si hubo un error en la publicación de la decisión
        if "❌ Error" in ejecucion_resultado_msg: # Only send if it's an error message
            await send_message(bot_instance, chat_id, ejecucion_resultado_msg)
        logger.info(f"Resultado de evaluación de decisión: {ejecucion_resultado_msg}")

        # --- PASO 3: VERIFICAR Y MOSTRAR ALERTA DE RIESGO FORZADO (solo en logs) ---
        logger.info("Verificando estado de riesgo forzado.")
        if riesgo_forzado_activo() and recordar_riesgo_forzado():
            duracion = duracion_riesgo_forzado()
            ganancias = ganancias_durante_riesgo_forzado()
            operaciones = operaciones_en_riesgo_forzado()
            probabilidad = calcular_probabilidad_ganancia_perdida()

            mensaje_riesgo = (
                f"⚠️ Riesgo forzado sigue activo desde hace {duracion}.\n"
                f" Ganancia acumulada: {ganancias:.2f}%"
                f" Operaciones: {operaciones['total']} "
                f"({operaciones['positivas']} positivas, {operaciones['negativas']} negativas)\n"
                f" Probabilidad heurística si mantienes o subes riesgo:\n"
                f"  ➕ Ganar: {probabilidad['ganar']:.1f}%"
                f"  - Perder: {probabilidad['prob_perdida']:.1f}%"
                f"Puedes responder con:\n"
                f" 'volver a automático'\n"
                f"⏳ 'mantener riesgo forzado'\n"
                f" 'no recordar más hoy'"
            )
            logger.warning("Alerta de riesgo forzado registrada en logs.")


    except Exception as e:
        logger.exception(f"Error inesperado en flujo_principal: {e}")
        await send_message(bot_instance, chat_id, f"❌ Error inesperado en flujo principal: {e}")

# Función para cerrar todos los subprocessos hijos
async def shutdown_all_subprocesses():
    global active_subprocesses
    for proc in active_subprocesses:
        if proc.returncode is None:
            proc.terminate()
            try:
                await proc.wait()
            except Exception:
                pass
    active_subprocesses.clear()

async def run_analysis_cycle(bot_instance: Bot, chat_id: int) -> None:
    """
    Ejecuta un único ciclo de análisis de mercado y trading.
    """
    logger.info("--- Iniciando nuevo ciclo de análisis ---")
    await flujo_principal(bot_instance, chat_id)
    logger.info(f"--- Ciclo de análisis completado. ---")


async def main_run_bot() -> None:
    """
    Inicializa el bot según el modo de operación y ejecuta el flujo principal.
    Controla el modo LIVE/PAPER y asegura que la lógica crítica solo se ejecute si corresponde.
    """
    logger.info("run_bot.py ejecutado directamente.")

    chat_id_int = config.TELEGRAM_CHAT_ID
    if not config.TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN no está definido en las variables de entorno ni en .env")
    bot_instance = Bot(token=config.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    state_manager = StateManager()

    # Obtener el modo de operación de la sesión (establecido por listener_bot.py)
    session_mode = state_manager.get_state("session", "mode", config.MODE) # Usar config.MODE como fallback

    # Registrar tareas asíncronas
    tasks = []
    # Initialize scheduler
    scheduler = AsyncIOScheduler()
    scheduler.start()
    logger.info("Scheduler iniciado con tareas programadas.")

    retrain_task = asyncio.create_task(retrain_ml_model_periodically(bot_instance, chat_id_int, interval_hours=24))
    tasks.append(retrain_task)

    # Programar la tarea de actualización diaria de datos históricos
    scheduler.add_job(daily_data_update_task, 'cron', hour=0, minute=0, args=[bot_instance, chat_id_int])

    # AÑADIR ESTA LÍNEA PARA INICIAR EL POLLING DEL BOT
    polling_task = asyncio.create_task(dp.start_polling(bot_instance))
    tasks.append(polling_task)

    try:
        # Determinar el modo de operación al inicio
        if session_mode == "live":
            logger.info("Modo de operación de la sesión: LIVE.")
            live_unlocked = state_manager.get_state("live_mode", "unlocked", False)
            if not live_unlocked:
                logger.warning("Bot en modo LIVE pero no desbloqueado. Operando en modo SIMULADO.")
                await send_message(bot_instance, chat_id_int, "⚠️ Bot en modo LIVE pero no desbloqueado. La operación se realizará en modo SIMULADO.")
            else:
                logger.info("Bot en modo LIVE y desbloqueado. Procediendo con operaciones reales.")
                await send_message(bot_instance, chat_id_int, "✅ ¡El bot está operando en modo LIVE!")
        elif session_mode == "paper":
            logger.info("Modo de operación de la sesión: PAPER (simulación).")
            await send_message(bot_instance, chat_id_int, "🤖 Bot en modo PAPER (simulación). No se realizarán operaciones reales.")
            state_manager.set_state("live_mode", "unlocked", False) # Ensure live mode is locked
        else:
            error_msg = f"❌ Modo de operación desconocido: {session_mode}. Se usará modo PAPER por defecto."
            logger.error(error_msg)
            await send_message(bot_instance, chat_id_int, error_msg)
            state_manager.set_state("session", "mode", "paper") # Default to paper
            state_manager.set_state("live_mode", "unlocked", False) # Ensure live mode is locked

        # Bucle principal para ejecutar el análisis periódicamente
        while True:
            await run_analysis_cycle(bot_instance, chat_id_int)
            logger.info(f"--- Esperando {config.ANALYSIS_INTERVAL_SECONDS} segundos para el siguiente ciclo ---")
            await asyncio.sleep(config.ANALYSIS_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        logger.info("Bucle principal cancelado. Procediendo al apagado.")
    finally:
        logger.info("Iniciando secuencia de apagado del bot...")
        # Cancelar y esperar todas las tareas pendientes
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Tarea {task.get_name()} cancelada durante el apagado.")

        # Cerrar cliente de Binance
        await close_binance_client()

        # Cerrar procesos hijos
        await shutdown_all_subprocesses()

        # Asegurar cierre completo de recursos de Telegram
        await shutdown_bot(bot_instance)

        logger.info("Apagado del bot completado.")
        await asyncio.sleep(0.1)  # Breve pausa para garantizar cierre completo

# Bloque para ejecución directa
if __name__ == "__main__":
    try:
        asyncio.run(main_run_bot())
    except Exception as e:
        logger.error(f"Error crítico durante la ejecución del bot: {e}", exc_info=True)
