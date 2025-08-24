# utils/telegram_handler.py

import os
import asyncio
import logging
from aiogram.exceptions import TelegramRetryAfter
from aiogram import Bot
from aiogram.types import FSInputFile
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)

# --- Funciones asíncronas ---

async def send_message(bot_instance: Bot, chat_id: int, message: str, reply_markup=None, parse_mode: str = ParseMode.HTML):
    """Envía un mensaje de texto al chat especificado con manejo de reintentos por Flood Control."""
    if bot_instance: # Only attempt to send if bot_instance is provided
        try:
            await bot_instance.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except TelegramRetryAfter as e:
            logger.warning(f"Flood control exceeded. Retrying after {e.retry_after} seconds.")
            await asyncio.sleep(e.retry_after)
            if bot_instance: # Check again before retrying
                await bot_instance.send_message( # Retry the message
                    chat_id=chat_id,
                    text=message,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error inesperado al enviar mensaje a Telegram: {e}", exc_info=True)
    else:
        logger.debug(f"No se envió mensaje a Telegram porque bot_instance es None. Mensaje: {message[:50]}...")

async def send_document(bot_instance: Bot, chat_id: int, document_path: str, caption: str = ""):
    """Envía un documento al chat especificado."""
    if not os.path.exists(document_path):
        raise FileNotFoundError(f"El archivo {document_path} no fue encontrado.")
    
    documento = FSInputFile(document_path, filename=os.path.basename(document_path))
    await bot_instance.send_document(
        chat_id=chat_id,
        document=documento,
        caption=caption
    )

async def shutdown_bot(bot_instance: Bot):
    """Cierra la sesión del bot de forma segura."""
    print("Lógica de apagado del bot ejecutada.")
    await bot_instance.session.close()

import config

async def await_confirmation(bot_instance: Bot, chat_id: int, timeout: int = 60) -> str:
    """
    Espera una confirmación explícita del usuario ('sí') en Telegram.
    Si config.PRODUCTION_MODE es False, autoconfirma para facilitar el desarrollo.
    """
    if not config.PRODUCTION_MODE:
        logger.warning("MODO DESARROLLO: La función await_confirmation está configurada para autoconfirmar. El script procederá sin esperar respuesta.")
        return "sí"

    logger.info(f"Esperando confirmación explícita ('sí') en el chat {chat_id} durante {timeout} segundos...")
    last_update_id = 0

    # Primero, vaciar actualizaciones pendientes para no procesar mensajes antiguos
    try:
        updates = await bot_instance.get_updates(offset=-1, timeout=1)
        if updates:
            last_update_id = updates[-1].update_id
    except Exception as e:
        logger.error(f"Error al limpiar actualizaciones pendientes: {e}")

    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            updates = await bot_instance.get_updates(offset=last_update_id + 1, timeout=10, allowed_updates=["message"])
            for update in updates:
                last_update_id = update.update_id
                if update.message and update.message.chat.id == chat_id:
                    if update.message.text and update.message.text.lower().strip() == 'sí':
                        logger.info("Confirmación 'sí' recibida del usuario.")
                        return "sí"
        except Exception as e:
            logger.error(f"Error al obtener actualizaciones de Telegram: {e}")
            # Esperar un poco antes de reintentar en caso de error de red
            await asyncio.sleep(5)
        
        await asyncio.sleep(1)  # Esperar 1 segundo entre cada sondeo

    logger.warning(f"No se recibió confirmación en los {timeout} segundos especificados. Acción cancelada.")
    await send_message(bot_instance, chat_id, "Acción cancelada por falta de confirmación.")
    return "no"