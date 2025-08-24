# run_bot.py

import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database.database_manager import init_db
from download_historical_data import download_and_save_klines
from listener_bot import dp
from strategies.strategy_manager import StrategyManager
from utils.binance_client import close_binance_client
from utils.logger_setup import setup_logging
from utils.message_queue import mq
from utils.shield_manager import verificar_condiciones_mercado
from utils.state_manager import StateManager
from utils.telegram_handler import send_message, shutdown_bot

setup_logging()
logger = logging.getLogger(__name__)

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
    for symbol in settings.TRADING_PAIRS:
        try:
            await send_message(bot_instance, chat_id, f"⏳ Iniciando actualización diaria de datos para {symbol}...")
            await download_and_save_klines(
                symbol=symbol,
                interval="1h",  # Asumimos 1h, podría ser configurable por activo
                start_str="1 Jan, 2022",
                append_to_existing=True
            )
            await send_message(bot_instance, chat_id, f"✅ Actualización diaria de datos para {symbol} completada.")
        except Exception as e:
            logger.error(f"Error en la tarea de actualización diaria para {symbol}: {e}", exc_info=True)
            await send_message(bot_instance, chat_id, f"❌ Error en actualización diaria para {symbol}: {e}")

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

async def flujo_principal_por_activo(bot_instance: Bot, chat_id: int, symbol: str) -> None:
    """
    Ejecuta el flujo de análisis y decisión para un único activo.
    """
    logger.info(f"Iniciando flujo principal para el activo: {symbol}.")
    try:
        logger.info(f"Cargando Strategy Manager y ejecutando análisis para {symbol}.")
        strategy_manager = StrategyManager()
        interval = "1h" # TODO: Implement per-asset configuration
        analysis_summary = await strategy_manager.analyze_all_strategies(symbol=symbol, interval=interval, limit=200)

        if "error" in analysis_summary:
            logger.error(f"Error en análisis para {symbol}: {analysis_summary['error']}")
            await send_message(bot_instance, chat_id, f"❌ Error en análisis para {symbol}: {analysis_summary['error']}")
            return

        logger.info(f"Análisis para {symbol} completado. Mejor: {analysis_summary['best_strategy']} - Decisión: {analysis_summary['best_decision']}")

        best_decision = analysis_summary.get("best_decision", "Indeciso")
        best_strategy = analysis_summary.get("best_strategy", "UnknownStrategy")
        best_score = analysis_summary.get("best_score", "N/A")

        actionable_decision = None
        if best_decision in ["COMPRAR", "COMPRAR_BAJO"]:
            actionable_decision = "BUY"
        elif best_decision in ["VENDER", "VENDER_ALTO"]:
            actionable_decision = "SELL"

        if actionable_decision:
            decision_data = {
                "type": "AUTOMATED_TRADE",
                "symbol": symbol,
                "side": actionable_decision,
                "quantity": 0.0001,  # Placeholder
                "order_type": "MARKET",
                "strategy_id": best_strategy,
                "timestamp_decision": datetime.now().isoformat(),
                "analysis_score": best_score,
            }
            success = mq.publish_decision(decision_data)
            if success:
                logger.info(f"Decisión de {best_decision} para {symbol} publicada en la cola.")
            else:
                logger.error(f"Fallo al publicar decisión para {symbol}.")
                await send_message(bot_instance, chat_id, f"❌ Error al publicar decisión de {best_decision} para {symbol} en la cola.")
        else:
            logger.info(f"Decisión de análisis para {symbol}: {best_decision}. No se publicó ninguna orden.")

    except Exception as e:
        logger.exception(f"Error inesperado en flujo_principal_por_activo para {symbol}: {e}")
        await send_message(bot_instance, chat_id, f"❌ Error inesperado procesando {symbol}: {e}")

async def main_run_bot() -> None:
    """
    Inicializa el bot y ejecuta el bucle principal de análisis para todos los activos.
    """
    logger.info("run_bot.py ejecutado directamente.")
    init_db()

    chat_id_int = settings.TELEGRAM_CHAT_ID
    if not settings.TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN no está definido.")
    bot_instance = Bot(token=settings.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    state_manager = StateManager()
    session_mode = state_manager.get_state("session", "mode", settings.MODE)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_data_update_task, 'cron', hour=0, minute=0, args=[bot_instance, chat_id_int])
    scheduler.add_job(retrain_ml_model_periodically, 'interval', hours=24, args=[bot_instance, chat_id_int])
    scheduler.start()
    logger.info("Scheduler iniciado con tareas programadas.")

    polling_task = asyncio.create_task(dp.start_polling(bot_instance))

    try:
        if session_mode == "live":
            await send_message(bot_instance, chat_id_int, "✅ ¡El bot está operando en modo LIVE para múltiples activos!")
        else:
            await send_message(bot_instance, chat_id_int, "🤖 Bot en modo PAPER (simulación) para múltiples activos!")

        while True:
            logger.info(f"--- Iniciando nuevo ciclo de análisis para los activos: {', '.join(settings.TRADING_PAIRS)} ---")
            
            escudo_msg_dict = await verificar_condiciones_mercado(bot_instance, chat_id_int)
            if escudo_msg_dict["status"] == "DANGER":
                logger.warning(f"Escudo de Protección Activado: {escudo_msg_dict['reason']}. Saltando todo el ciclo de análisis.")
                await send_message(bot_instance, chat_id_int, f"🛡️ Escudo de Protección Activado 🛡️\nRazón: {escudo_msg_dict['reason']}\nNo se analizarán activos en este ciclo.")
            else:
                tasks = [flujo_principal_por_activo(bot_instance, chat_id_int, symbol) for symbol in settings.TRADING_PAIRS]
                logger.info(f"Lanzando análisis concurrente para {len(tasks)} activos.")
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        symbol = settings.TRADING_PAIRS[i]
                        logger.error(f"Ocurrió una excepción durante el análisis concurrente para {symbol}: {result}", exc_info=False)

            logger.info(f"--- Ciclo de análisis completado. Esperando {settings.ANALYSIS_INTERVAL_SECONDS} segundos ---")
            await asyncio.sleep(settings.ANALYSIS_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        logger.info("Bucle principal cancelado. Procediendo al apagado.")
    finally:
        logger.info("Iniciando secuencia de apagado del bot...")
        if scheduler.running:
            scheduler.shutdown()
        if not polling_task.done():
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
        
        await close_binance_client()
        await shutdown_all_subprocesses()
        await shutdown_bot(bot_instance)
        logger.info("Apagado del bot completado.")

if __name__ == "__main__":
    try:
        asyncio.run(main_run_bot())
    except Exception as e:
        logger.critical(f"Error crítico irrecuperable en la ejecución del bot: {e}", exc_info=True)
