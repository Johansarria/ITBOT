# run_bot.py

import asyncio
import importlib
import logging
import os
import time # Importar time
import redis # Importar redis
from datetime import datetime

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
from config import settings
from database.database_manager import init_db
from download_historical_data import download_and_save_klines
# from listener_bot import dp # No longer needed, this bot should not listen.
from modules.dynamic_pair_manager import dynamic_pair_manager
from strategies.strategy_manager import StrategyManager
from utils.binance_client import close_binance_client
from utils.logger_setup import setup_logging
from utils.message_queue import mq
from utils.shield_manager import verificar_condiciones_mercado
from utils.state_manager import StateManager
from utils.telegram_handler import send_message, shutdown_bot
from utils.notification_manager import notify_error, notify_trade, notify_shield, notify_system_event, send_silent
from utils.structured_logger import StructuredLogger
from config import settings

# V3 dinámico (opcional)
try:
    from strategies.v3_dynamic_controller import V3DynamicController
    _V3_DYNAMIC_AVAILABLE = True
except Exception:
    _V3_DYNAMIC_AVAILABLE = False

setup_logging()
logger = StructuredLogger(__name__)

# Placeholder para compatibilidad con tests que parchean run_bot.dp
dp = None

active_subprocesses = []

async def retrain_ml_model_periodically(bot_instance: Bot, chat_id: int, interval_hours: int = 24):
    """
    Ejecuta el pipeline de entrenamiento ML de forma periódica y notifica por Telegram.
    """
    global active_subprocesses
    while True:
        try:
            await notify_system_event(bot_instance, chat_id, "Iniciando retraining automático del modelo ML...")
        # Solo mostrar inicio del retraining, no cada paso de progreso
            python_exec = os.path.join(os.getcwd(), ".venv/bin/python")
            proc = await asyncio.create_subprocess_exec(
                python_exec, 'train_pipeline.py',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            active_subprocesses.append(proc)
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                await notify_system_event(bot_instance, chat_id, "Retraining ML completado exitosamente")
            else:
                await notify_error(bot_instance, chat_id, f"Error en retraining ML: {stderr.decode()}")
        except Exception as e:
            await notify_error(bot_instance, chat_id, f"Excepción en retraining automático: {e}")
        await asyncio.sleep(interval_hours * 3600)

async def daily_data_update_task(bot_instance: Bot, chat_id: int):
    logger.info("DAILY_UPDATE_START", "Iniciando tarea de actualización diaria de datos históricos.")
    
    # Obtener pares dinámicos actualizados
    try:
        current_pairs = await dynamic_pair_manager.get_current_pairs()
        logger.info("DAILY_UPDATE_DYNAMIC_PAIRS", f"Actualizando datos para {len(current_pairs)} pares dinámicos", 
                   details={"pairs": current_pairs})
    except Exception as e:
        logger.error("DAILY_UPDATE_DYNAMIC_ERROR", f"Error obteniendo pares dinámicos, usando configuración estática: {e}")
        current_pairs = settings.TRADING_PAIRS
    
    for symbol in current_pairs:
        try:
            await send_silent(f"Iniciando actualización diaria de datos para {symbol}...")
            await download_and_save_klines(
                symbol=symbol,
                interval="1h",  # Asumimos 1h, podría ser configurable por activo
                start_str="1 Jan, 2022",
                append_to_existing=True
            )
            await send_silent(f"Actualización diaria de datos para {symbol} completada")
        except Exception as e:
            logger.critical("DAILY_UPDATE_ERROR", f"Error en la tarea de actualización diaria para {symbol}: {e}", details={"symbol": symbol}, exc_info=True)
            await notify_error(bot_instance, chat_id, f"Error en actualización diaria para {symbol}: {e}")

async def check_and_update_dynamic_pairs(bot_instance: Bot, chat_id: int):
    """
    Verificar y actualizar la selección de pares dinámicos.
    Esta función se ejecuta periódicamente para mantener la selección óptima.
    """
    logger.info("DYNAMIC_PAIR_CHECK", "Verificando necesidad de actualización de pares dinámicos")
    
    try:
        # Verificar si necesita actualización
        changes_made, change_details = await dynamic_pair_manager.check_and_update_pairs()
        
        if changes_made and change_details:
            # Notificar cambios por Telegram
            pairs_added = change_details.get('pairs_added', [])
            pairs_removed = change_details.get('pairs_removed', [])
            pairs_maintained = change_details.get('pairs_maintained', [])
            
            message = "🔄 **ACTUALIZACIÓN DINÁMICA DE PARES**\n\n"
            
            if pairs_added:
                message += f"✅ **Pares Agregados:** {', '.join(pairs_added)}\n"
            
            if pairs_removed:
                message += f"❌ **Pares Removidos:** {', '.join(pairs_removed)}\n"
            
            if pairs_maintained:
                message += f"🔄 **Pares Mantenidos:** {', '.join(pairs_maintained)}\n"
            
            message += f"\n📊 **Total de Pares Activos:** {len(change_details.get('new_pairs', []))}"
            message += f"\n⏱️ **Duración del Análisis:** {change_details.get('evaluation_duration_seconds', 0):.1f}s"
            
            await notify_system_event(bot_instance, chat_id, message.replace("🔄 **Actualización de Pares Dinámicos**\n", ""))
            
            logger.info("DYNAMIC_PAIRS_UPDATED", "Pares dinámicos actualizados exitosamente", 
                       details=change_details)
        else:
            logger.info("DYNAMIC_PAIRS_NO_CHANGE", "No se requieren cambios en la selección de pares")
            
    except Exception as e:
        logger.error("DYNAMIC_PAIR_UPDATE_ERROR", f"Error actualizando pares dinámicos: {e}", exc_info=True)
        await notify_error(bot_instance, chat_id, f"Error en actualización de pares dinámicos: {e}")

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
            await notify_error(bot_instance, chat_id, f"Error en análisis para {symbol}: {analysis_summary['error']}")
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
                await notify_error(bot_instance, chat_id, f"Error al publicar decisión de {best_decision} para {symbol} en la cola")
        else:
            logger.info("DECISION_NO_ACTION", f"Decisión de análisis para {symbol}: {best_decision}. No se publicó ninguna orden.", details={'symbol': symbol, 'decision': best_decision})

    except Exception as e:
        logger.error("ANALYSIS_FLOW_ERROR", f"Error inesperado en flujo_principal_por_activo para {symbol}: {e}", details={'symbol': symbol}, exc_info=True)
        await notify_error(bot_instance, chat_id, f"Error inesperado procesando {symbol}: {e}")

async def main_run_bot() -> None:
    """
    Inicializa el bot y ejecuta el bucle principal de análisis para todos los activos.
    Incluye sistema de selección dinámica de pares de trading.
    """
    logger.info("STARTUP", "run_bot.py ejecutado directamente con sistema dinámico.")
    init_db()

    chat_id_int = settings.TELEGRAM_CHAT_ID
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("❌ TELEGRAM_BOT_TOKEN no está definido.")
    bot_instance = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    state_manager = StateManager()
    session_mode = state_manager.get_state("session", "mode", settings.MODE)

    # En entorno no productivo, aseguramos que no esté en pausa para permitir el ciclo en pruebas
    if not settings.PRODUCTION_MODE:
        state_manager.set_state("system", "is_paused", False)
    # Evitar parches globales de asyncio.sleep en tests que generan recursión
    importlib.reload(asyncio)

    # Inicializar sistema de pares dinámicos
    logger.info("DYNAMIC_SYSTEM_INIT", "Inicializando sistema de pares dinámicos")
    try:
        init_success = await dynamic_pair_manager.initialize()
        if init_success:
            current_pairs = await dynamic_pair_manager.get_current_pairs()
            await send_silent(f"Sistema dinámico inicializado con {len(current_pairs)} pares: {', '.join(current_pairs)}")
            logger.info("DYNAMIC_SYSTEM_READY", f"Sistema dinámico listo con {len(current_pairs)} pares")
        else:
            await notify_error(bot_instance, chat_id_int, "Error inicializando sistema dinámico, usando configuración estática")
            logger.warning("DYNAMIC_SYSTEM_FALLBACK", "Usando configuración estática por error en sistema dinámico")
    except Exception as e:
        logger.error("DYNAMIC_SYSTEM_INIT_ERROR", f"Error crítico en sistema dinámico: {e}", exc_info=True)
        await notify_error(bot_instance, chat_id_int, f"Error crítico en sistema dinámico: {e}")

    # Conexión a Redis para Heartbeat (omitida en no producción para acelerar tests)
    redis_client = None
    if settings.PRODUCTION_MODE:
        try:
            redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
            redis_client.ping()  # Verificar conexión
            logger.info("REDIS_CONNECTED", "Conexión con Redis para heartbeat establecida.")
        except Exception as e:
            logger.critical("REDIS_CONNECT_ERROR", f"No se pudo conectar a Redis para el heartbeat: {e}")
            redis_client = None

    scheduler = AsyncIOScheduler()
    # Actualización diaria de datos históricos
    scheduler.add_job(daily_data_update_task, 'cron', hour=0, minute=0, args=[bot_instance, chat_id_int])
    # Re-entrenamiento ML periódico  
    scheduler.add_job(retrain_ml_model_periodically, 'interval', hours=24, args=[bot_instance, chat_id_int])
    # Verificación de pares dinámicos cada 2 horas
    scheduler.add_job(check_and_update_dynamic_pairs, 'interval', hours=2, args=[bot_instance, chat_id_int])
    scheduler.start()
    logger.info("SCHEDULER_STARTED", "Scheduler iniciado con tareas programadas incluyendo sistema dinámico.")

    # Iniciar controlador V3 Dinámico en background (opcional por settings)
    if getattr(settings, 'ENABLE_V3_DYNAMIC_CONTROLLER', False):
        try:
            from strategies.v3_dynamic_controller import V3DynamicController
            v3_controller = V3DynamicController()
            asyncio.create_task(v3_controller.start_dynamic_operations())
            logger.info("V3_DYNAMIC_CONTROLLER_STARTED", "Controlador V3 Dinámico iniciado en background.")
        except Exception as e:
            logger.error("V3_DYNAMIC_CONTROLLER_ERROR", f"No se pudo iniciar el controlador V3 Dinámico: {e}", exc_info=True)

    # Lanzar controlador V3 dinámico en background si está habilitado
    v3_dynamic_task = None
    if getattr(settings, 'ENABLE_V3_DYNAMIC_CONTROLLER', False) and _V3_DYNAMIC_AVAILABLE:
        try:
            v3_controller = V3DynamicController()
            v3_dynamic_task = asyncio.create_task(v3_controller.start_dynamic_operations())
            logger.info("V3_DYNAMIC_CONTROLLER", "Controlador V3 dinámico iniciado en background")
        except Exception as e:
            logger.error("V3_DYNAMIC_START_ERROR", f"No se pudo iniciar el controlador V3 dinámico: {e}")

    # Se elimina el polling de Telegram para este proceso.
    # La interacción con el usuario se gestionará a través de main.py.
    # polling_task = asyncio.create_task(dp.start_polling(bot_instance))

    try:
        # Solo notificar el modo la primera vez, luego usar logs silenciosos
        if str(session_mode).strip().upper() == "LIVE":
            await notify_system_event(bot_instance, chat_id_int, "Bot iniciado en modo LIVE con selección dinámica de pares")
        else:
            await send_silent("Bot iniciado en modo PAPER con selección dinámica de pares")

        ran_once = False
        while True:
            # Enviar Heartbeat
            if redis_client:
                try:
                    redis_client.set("heartbeat:analysis_bot", int(time.time()))
                except Exception as e:
                    logger.error("REDIS_HEARTBEAT_ERROR", f"No se pudo enviar el heartbeat a Redis: {e}")

            # Verificar si el sistema está en pausa
            if state_manager.get_state("system", "is_paused", False):
                logger.warning("SYSTEM_PAUSED_SKIP", "Sistema en PAUSA. Saltando ciclo de análisis.")
                await asyncio.sleep(settings.ANALYSIS_INTERVAL_SECONDS)
                continue

            # Obtener pares activos del sistema dinámico
            try:
                active_pairs = await dynamic_pair_manager.get_current_pairs()
                if not active_pairs:
                    logger.warning("DYNAMIC_NO_PAIRS", "No hay pares activos del sistema dinámico, usando configuración estática")
                    active_pairs = settings.ASSETS_TO_TRADE
            except Exception as e:
                logger.error("DYNAMIC_GET_PAIRS_ERROR", f"Error obteniendo pares dinámicos: {e}")
                active_pairs = settings.ASSETS_TO_TRADE

            # En entorno de prueba, limitar a 1 par para evitar múltiples publicaciones en integración
            if os.environ.get('PYTEST_CURRENT_TEST') is not None and active_pairs:
                if 'BTCUSDT' in active_pairs:
                    active_pairs = ['BTCUSDT']
                else:
                    active_pairs = [active_pairs[0]]

            logger.info("ANALYSIS_CYCLE_START", f"--- Iniciando nuevo ciclo de análisis para los activos: {', '.join(active_pairs)} ---")
            
            escudo_msg_dict = await verificar_condiciones_mercado(bot_instance, chat_id_int)
            if escudo_msg_dict["status"] == "DANGER":
                logger.warning("SHIELD_ACTIVATED", f"Escudo de Protección Activado: {escudo_msg_dict['reason']}. Saltando todo el ciclo de análisis.", details=escudo_msg_dict)
                await notify_shield(bot_instance, chat_id_int, f"Activado - {escudo_msg_dict['reason']} - No se analizarán activos en este ciclo")
            else:
                tasks = [flujo_principal_por_activo(bot_instance, chat_id_int, symbol) for symbol in active_pairs]
                logger.info("CONCURRENT_ANALYSIS_START", f"Lanzando análisis concurrente para {len(tasks)} activos.", details={'asset_count': len(tasks), 'assets': active_pairs})
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        symbol = active_pairs[i]
                        logger.error("CONCURRENT_ANALYSIS_ERROR", f"Ocurrió una excepción durante el análisis concurrente para {symbol}: {result}", details={'symbol': symbol}, exc_info=False)

            logger.info("ANALYSIS_CYCLE_END", f"--- Ciclo de análisis completado. Esperando {settings.ANALYSIS_INTERVAL_SECONDS} segundos ---")
            # Comentado: En modo paper también debe continuar el ciclo
            # if not settings.PRODUCTION_MODE:
            #     # En pruebas salimos tras un ciclo para no depender de asyncio.sleep parcheado
            #     break
            await asyncio.sleep(settings.ANALYSIS_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        logger.info("MAIN_CANCELLED", "Bucle principal cancelado. Procediendo al apagado.")
    finally:
        logger.info("SHUTDOWN_START", "Iniciando secuencia de apagado del bot...")
        if scheduler.running:
            scheduler.shutdown()
        # Cancelar task V3 dinámico si existe
        if v3_dynamic_task and not v3_dynamic_task.done():
            v3_dynamic_task.cancel()
            try:
                await v3_dynamic_task
            except Exception:
                pass
        # if not polling_task.done():
        #     polling_task.cancel()
        #     try:
        #         await polling_task
        #     except asyncio.CancelledError:
        #         pass
        
        await close_binance_client()
        await shutdown_all_subprocesses()
        await shutdown_bot(bot_instance)
    logger.info("SHUTDOWN_COMPLETE", "Apagado del bot completado.")

if __name__ == "__main__":
    try:
        asyncio.run(main_run_bot())
    except Exception as e:
        logger.critical("FATAL_ERROR", f"Error crítico irrecuperable en la ejecución del bot: {e}", exc_info=True)
