# run_bot.py

import asyncio
import logging
import os
import time # Importar time
import redis # Importar redis
from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from database.database_manager import init_db
from download_historical_data import download_and_save_klines
# from listener_bot import dp # No longer needed, this bot should not listen.
from strategies.strategy_manager import StrategyManager
from utils.binance_client import close_binance_client
from utils.logger_setup import setup_logging
from utils.message_queue import mq
from utils.shield_manager import verificar_condiciones_mercado
from utils.state_manager import StateManager
from utils.telegram_handler import send_message, shutdown_bot
from utils.structured_logger import StructuredLogger

setup_logging()
logger = StructuredLogger(__name__)

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
            logger.critical(f"Error en la tarea de actualización diaria para {symbol}: {e}", exc_info=True)
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
    logger.info("ANALYSIS_FLOW_START", f"Iniciando flujo principal para el activo: {symbol}.", details={'symbol': symbol})
    try:
        logger.info("STRATEGY_MANAGER_LOAD", f"Cargando Strategy Manager y ejecutando análisis para {symbol}.", details={'symbol': symbol})
        strategy_manager = StrategyManager()
        interval = "1h" # TODO: Implement per-asset configuration
        analysis_summary = await strategy_manager.analyze_all_strategies(symbol=symbol, interval=interval, limit=200)

        if "error" in analysis_summary:
            logger.error("ANALYSIS_ERROR", f"Error en análisis para {symbol}: {analysis_summary['error']}", details={'symbol': symbol, 'error': analysis_summary['error']})
            await send_message(bot_instance, chat_id, f"❌ Error en análisis para {symbol}: {analysis_summary['error']}")
            return

        logger.info(
            "ANALYSIS_COMPLETE",
            f"Análisis para {symbol} completado. Mejor: {analysis_summary['best_strategy']} - Decisión: {analysis_summary['best_decision']}",
            details={
                'symbol': symbol,
                'best_strategy': analysis_summary.get('best_strategy'),
                'best_decision': analysis_summary.get('best_decision'),
                'best_score': analysis_summary.get('best_score')
            }
        )

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
                logger.info("DECISION_PUBLISHED", f"Decisión de {best_decision} para {symbol} publicada en la cola.", details=decision_data)
            else:
                logger.error("DECISION_PUBLISH_FAILED", f"Fallo al publicar decisión para {symbol}.", details=decision_data)
                await send_message(bot_instance, chat_id, f"❌ Error al publicar decisión de {best_decision} para {symbol} en la cola.")
        else:
            logger.info("DECISION_NO_ACTION", f"Decisión de análisis para {symbol}: {best_decision}. No se publicó ninguna orden.", details={'symbol': symbol, 'decision': best_decision})

    except Exception as e:
        logger.error("ANALYSIS_FLOW_ERROR", f"Error inesperado en flujo_principal_por_activo para {symbol}: {e}", details={'symbol': symbol}, exc_info=True)
        await send_message(bot_instance, chat_id, f"❌ Error inesperado procesando {symbol}: {e}")

async def main_run_bot() -> None:
    """
    Inicializa el bot y ejecuta el bucle principal de análisis para todos los activos.
    """
    logger.info("run_bot.py ejecutado directamente.")
    init_db()

    chat_id_int = settings.TELEGRAM_CHAT_ID
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN no está definido.")
    bot_instance = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    state_manager = StateManager()
    session_mode = state_manager.get_state("session", "mode", settings.MODE)

    # Conexión a Redis para Heartbeat
    try:
        redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
        redis_client.ping() # Verificar conexión
        logger.info("Conexión con Redis para heartbeat establecida.")
    except redis.exceptions.ConnectionError as e:
        logger.critical(f"No se pudo conectar a Redis para el heartbeat: {e}")
        redis_client = None

    scheduler = AsyncIOScheduler()
    scheduler.add_job(daily_data_update_task, 'cron', hour=0, minute=0, args=[bot_instance, chat_id_int])
    scheduler.add_job(retrain_ml_model_periodically, 'interval', hours=24, args=[bot_instance, chat_id_int])
    scheduler.start()
    logger.info("Scheduler iniciado con tareas programadas.")

    # Se elimina el polling de Telegram para este proceso.
    # La interacción con el usuario se gestionará a través de main.py.
    # polling_task = asyncio.create_task(dp.start_polling(bot_instance))

    try:
        if session_mode == "live":
            await send_message(bot_instance, chat_id_int, "✅ ¡El bot está operando en modo LIVE para múltiples activos!")
        else:
            await send_message(bot_instance, chat_id_int, "🤖 Bot en modo PAPER (simulación) para múltiples activos!")

        while True:
            # Enviar Heartbeat
            if redis_client:
                try:
                    redis_client.set("heartbeat:analysis_bot", int(time.time()))
                except redis.exceptions.RedisError as e:
                    logger.error("REDIS_HEARTBEAT_ERROR", f"No se pudo enviar el heartbeat a Redis: {e}")

            # Verificar si el sistema está en pausa
            if state_manager.get_state("system", "is_paused", False):
                logger.warning("SYSTEM_PAUSED_SKIP", "Sistema en PAUSA. Saltando ciclo de análisis.")
                await asyncio.sleep(settings.ANALYSIS_INTERVAL_SECONDS)
                continue

            logger.info("ANALYSIS_CYCLE_START", f"--- Iniciando nuevo ciclo de análisis para los activos: {', '.join(settings.TRADING_PAIRS)} ---")
            
            escudo_msg_dict = await verificar_condiciones_mercado(bot_instance, chat_id_int)
            if escudo_msg_dict["status"] == "DANGER":
                logger.warning("SHIELD_ACTIVATED", f"Escudo de Protección Activado: {escudo_msg_dict['reason']}. Saltando todo el ciclo de análisis.", details=escudo_msg_dict)
                await send_message(bot_instance, chat_id_int, f"🛡️ Escudo de Protección Activado 🛡️\nRazón: {escudo_msg_dict['reason']}\nNo se analizarán activos en este ciclo.")
            else:
                tasks = [flujo_principal_por_activo(bot_instance, chat_id_int, symbol) for symbol in settings.ASSETS_TO_TRADE]
                logger.info("CONCURRENT_ANALYSIS_START", f"Lanzando análisis concurrente para {len(tasks)} activos.", details={'asset_count': len(tasks), 'assets': settings.ASSETS_TO_TRADE})
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        symbol = settings.ASSETS_TO_TRADE[i]
                        logger.error("CONCURRENT_ANALYSIS_ERROR", f"Ocurrió una excepción durante el análisis concurrente para {symbol}: {result}", details={'symbol': symbol}, exc_info=False)

            logger.info("ANALYSIS_CYCLE_END", f"--- Ciclo de análisis completado. Esperando {settings.ANALYSIS_INTERVAL_SECONDS} segundos ---")
            await asyncio.sleep(settings.ANALYSIS_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        logger.info("Bucle principal cancelado. Procediendo al apagado.")
    finally:
        logger.info("Iniciando secuencia de apagado del bot...")
        if scheduler.running:
            scheduler.shutdown()
        # if not polling_task.done():
        #     polling_task.cancel()
        #     try:
        #         await polling_task
        #     except asyncio.CancelledError:
        #         pass
        
        await close_binance_client()
        await shutdown_all_subprocesses()
        await shutdown_bot(bot_instance)
        logger.info("Apagado del bot completado.")

if __name__ == "__main__":
    try:
        asyncio.run(main_run_bot())
    except Exception as e:
        logger.critical(f"Error crítico irrecuperable en la ejecución del bot: {e}", exc_info=True)
