# modules/analisis_bot.py

import logging
import aiohttp
from utils.telegram_handler import send_message
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Mis Módulos ---
from strategies.strategy_manager import StrategyManager
from utils.technical_analysis import get_historical_klines
from utils.position_manager import get_open_positions_summary

logger = logging.getLogger(__name__)

def es_comando_analisis(mensaje: str) -> bool:
    comandos = ["analizar", "resumen tecnico", "score tecnico", "recomendar accion", "posiciones", "estado"]
    return any(mensaje.lower().startswith(cmd) for cmd in comandos)

async def procesar_comando_analisis(bot_instance: Bot, chat_id: int, mensaje: str, send_telegram_message: bool = True):
    texto_lower = mensaje.lower().strip()
    logger.info(f"Procesando comando de análisis: {mensaje}")

    if texto_lower == "analizar":
        if send_telegram_message:
            keyboard_buttons = [
                [InlineKeyboardButton(text="📊 Resumen Técnico", callback_data="analyze_summary")],
                [InlineKeyboardButton(text="📈 Score Técnico", callback_data="analyze_score")],
                [InlineKeyboardButton(text="💡 Recomendar Acción", callback_data="analyze_recommendation")],
                [InlineKeyboardButton(text="💰 Posiciones Abiertas", callback_data="show_positions")]
            ]
            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await send_message(bot_instance, chat_id, "Selecciona el tipo de análisis que deseas realizar:", reply_markup=reply_markup)
            logger.info("Menú de análisis enviado a Telegram.")
        return {"status": "menu_sent"}
    
    elif texto_lower in ["resumen tecnico", "score tecnico", "recomendar accion"]:
        if send_telegram_message:
            await send_message(bot_instance, chat_id, "🔄 Realizando análisis con la estrategia activa, esto puede tardar un momento...")
        try:
            strategy_manager = StrategyManager()
            active_strategy = strategy_manager.get_active_strategy()
            
            # Obtener datos históricos para el análisis
            historical_data = await get_historical_klines("BTCUSDT", "1h")
            if historical_data.empty:
                if send_telegram_message:
                    await send_message(bot_instance, chat_id, "⚠️ No se pudieron obtener datos del mercado para el análisis.")
                return {"status": "error", "message": "No se pudieron obtener datos del mercado para el análisis."}

            # Detectar si la estrategia requiere symbol/interval
            import inspect
            analyze_sig = inspect.signature(active_strategy.analyze)
            params = list(analyze_sig.parameters.keys())
            if len(params) >= 3:
                resultado = await active_strategy.analyze(historical_data, "BTCUSDT", "1h")
            else:
                resultado = await active_strategy.analyze(historical_data)
            
            decision = resultado.get("decision", "Indeciso")
            score = resultado.get("score", "N/A")
            symbol = resultado.get("symbol", "BTCUSDT")

            texto = (
                f"📊 Resultado del Análisis con '{active_strategy.name}':\n\n"
                f"<b>Símbolo:</b> {symbol}\n"
                f"<b>Decisión:</b> {decision}\n"
                f"<b>Score:</b> {score}"
            )
            if send_telegram_message:
                await send_message(bot_instance, chat_id, texto)
                logger.info(f"Análisis con estrategia '{active_strategy.name}' enviado a Telegram.")
            return resultado

        except aiohttp.ClientError as e:
            logger.error(f"Error de conexión o API al realizar el análisis: {e}", exc_info=True)
            if send_telegram_message:
                await send_message(bot_instance, chat_id, f"❌ Error de conexión al realizar el análisis: {e}")
            return {"status": "error", "message": f"Error de conexión al realizar el análisis: {e}"}
        except Exception as e:
            logger.exception(f"Error inesperado al realizar el análisis: {e}")
            if send_telegram_message:
                await send_message(bot_instance, chat_id, f"❌ Ocurrió un error inesperado al realizar el análisis: {e}")
            return {"status": "error", "message": f"Ocurrió un error inesperado al realizar el análisis: {e}"}

    elif texto_lower in ["posiciones", "estado"]:
        summary = await get_open_positions_summary(bot_instance)
        if send_telegram_message:
            await send_message(bot_instance, chat_id, summary)
            logger.info("Resumen de posiciones enviado a Telegram.")
        return {"status": "success", "summary": summary}
    
    else:
        if send_telegram_message:
            await send_message(bot_instance, chat_id, "🤖 Comando de análisis no reconocido. Prueba con: `analizar` o `posiciones`.")
            logger.warning(f"Comando de análisis desconocido recibido: {mensaje}")
        return {"status": "error", "message": "Comando de análisis no reconocido."}