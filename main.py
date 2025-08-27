# main.py

"""
Punto de entrada principal para el bot de Telegram de ITBOT.

Este script se encarga de:
1. Cargar la configuración (token del bot).
2. Inicializar la aplicación de `python-telegram-bot`.
3. Registrar todos los handlers (comandos, callbacks, conversaciones).
4. Iniciar el bot para que comience a escuchar actualizaciones.
"""

import logging
import os
import html
import json
import traceback
import warnings

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.warnings import PTBUserWarning

# Importar handlers desde el módulo de handlers
from handlers import start, main_menu_handlers, action_handlers, conv_handlers
from database.database_manager import init_db

# --- Configuración de Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
# Silenciar warnings de PTB que no son críticos para esta implementación
warnings.filterwarnings("ignore", category=PTBUserWarning)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loguea el error y envía un mensaje de Telegram para notificar al desarrollador."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    update_str = update.to_json() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(json.loads(update_str), indent=2, ensure_ascii=False))}"
        f"</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Usar un chat_id de fallback si no está disponible
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_FALLBACK_CHAT_ID")
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)


def main() -> None:
    """Función principal que configura y ejecuta el bot."""
    
    # 1. Cargar Token
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("No se encontró la variable de entorno TELEGRAM_BOT_TOKEN. El bot no puede iniciar.")
        return

    # Inicializar la base de datos
    init_db()

    # 2. Inicializar Application
    application = Application.builder().token(token).build()

    # 3. Registrar Handlers
    
    # Registrar el manejador de errores global
    application.add_error_handler(error_handler)

    # Comando de inicio
    application.add_handler(CommandHandler("start", start))
    
    # Handlers de Conversación
    for conv_handler in conv_handlers:
        application.add_handler(conv_handler)

    # Handlers de menús y acciones (CallbackQueryHandlers)
    # Se agrupan para mantener el código limpio
    all_callback_handlers = main_menu_handlers + action_handlers
    for handler in all_callback_handlers:
        application.add_handler(handler)

    # Un handler genérico para el botón "Volver" que apunta a main_menu
    application.add_handler(CallbackQueryHandler(start, pattern="^main_menu$"))

    logger.info("Bot configurado y listo para iniciar...")

    # 4. Iniciar el Bot
    application.run_polling()

if __name__ == "__main__":
    main()