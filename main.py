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

# --- Configuración de Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
# Silenciar warnings de PTB que no son críticos para esta implementación
warnings.filterwarnings("ignore", category=PTBUserWarning)
logger = logging.getLogger(__name__)

# Importar handlers desde el módulo de handlers
from handlers import start, main_menu_handlers, action_handlers, conv_handlers, get_my_id, get_my_id, get_my_id

# Flags para características UI mejoradas
UI_ENHANCED = True
DASHBOARD_ENHANCED = True

# Intentar importar mejoras de UI, con fallback si no están disponibles
ENHANCED_HANDLERS = {}
QUICK_COMMANDS = {}

if UI_ENHANCED:
    try:
        from handlers.enhanced_dashboard import ENHANCED_HANDLERS as ENHANCED_DASH
        ENHANCED_HANDLERS.update(ENHANCED_DASH)
    except ImportError:
        logger.warning("Enhanced dashboard no disponible, usando interfaz estándar")

if DASHBOARD_ENHANCED:
    try:
        from handlers.quick_commands import QUICK_COMMANDS as QUICK_CMD
        QUICK_COMMANDS.update(QUICK_CMD)
    except ImportError:
        logger.warning("Quick commands no disponibles, usando comandos estándar")

from database.database_manager import init_db

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Loguea el error y envía un mensaje de Telegram para notificar al desarrollador."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception_only(type(context.error), context.error)
    tb_string = "".join(tb_list)[-1500:]  # Limitar longitud del traceback

    brief_update = ""
    if isinstance(update, Update):
        try:
            data = update.to_dict()
            # Limitar el tamaño del payload para evitar mensajes demasiado largos
            brief_update = html.escape(json.dumps({k: data.get(k) for k in ['update_id', 'message', 'callback_query'] if k in data}, ensure_ascii=False))
        except Exception:
            brief_update = html.escape(str(update))
    else:
        brief_update = html.escape(str(update))

    message = (
        f"<b>Unhandled exception</b>\n"
        f"<pre>{tb_string}</pre>\n"
        f"<b>Update</b>: <pre>{brief_update[:1500]}</pre>"
    )

    # Usar un chat_id de fallback si no está disponible
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_FALLBACK_CHAT_ID")
    try:
        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception:
        # En caso extremo, enviar un resumen en texto plano
        fallback = f"Unhandled exception: {str(context.error)[:1000]}"
        await context.bot.send_message(chat_id=chat_id, text=fallback)


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
    
    # Comandos útiles
    application.add_handler(CommandHandler("myid", get_my_id))
    application.add_handler(CommandHandler("id", get_my_id))  # Alias
    
    # Registrar comandos rápidos mejorados
    for command, handler in QUICK_COMMANDS.items():
        application.add_handler(CommandHandler(command, handler))
    
    # Registrar handlers del dashboard mejorado (CallbackQueryHandlers)
    for callback_data, handler in ENHANCED_HANDLERS.items():
        application.add_handler(CallbackQueryHandler(handler, pattern=f"^{callback_data}$"))
    
    # Handlers de Conversación
    for conv_handler in conv_handlers:
        application.add_handler(conv_handler)

    # Handlers de menús y acciones (CallbackQueryHandlers)
    # Se agrupan para mantener el código limpio
    all_callback_handlers = main_menu_handlers + action_handlers
    for handler in all_callback_handlers:
        application.add_handler(handler)

    # Nota: el handler para "main_menu" ya está registrado en handlers.main_menu_handlers
    # para evitar duplicados, no lo agregamos aquí.

    logger.info("Bot configurado y listo para iniciar...")

    # 4. Iniciar el Bot
    application.run_polling()

if __name__ == "__main__":
    main()