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

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from telegram.warnings import PTBUserWarning
import warnings

# Importar handlers desde el módulo de handlers
from handlers import start, main_menu_handlers, action_handlers, conv_handlers, CONFIRM_LIVE, CONFIRM_LIQUIDATE, CONFIRM_STOP, CONFIRM_MANUAL_RISK, cancel_conversation, change_mode_start, confirm_live_mode, liquidate_start, confirm_liquidate, stop_start, confirm_stop

# --- Configuración de Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
# Silenciar warnings de PTB que no son críticos para esta implementación
warnings.filterwarnings("ignore", category=PTBUserWarning)
logger = logging.getLogger(__name__)

def main() -> None:
    """Función principal que configura y ejecuta el bot."""
    
    # 1. Cargar Token
    # El token se debe guardar en una variable de entorno llamada TELEGRAM_BOT_TOKEN
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.critical("No se encontró la variable de entorno TELEGRAM_BOT_TOKEN. El bot no puede iniciar.")
        return

    # 2. Inicializar Application
    application = Application.builder().token(token).build()

    # 3. Registrar Handlers
    
    # Comando de inicio
    application.add_handler(CommandHandler("start", start))
    
    # Handlers de Conversación (deben registrarse antes que los CallbackQueryHandlers generales)
    conv_handlers_list = [
        ConversationHandler(
            entry_points=[CallbackQueryHandler(change_mode_start, pattern="^control_change_mode$")],
            states={
                CONFIRM_LIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_live_mode)]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        ),
        ConversationHandler(
            entry_points=[CallbackQueryHandler(liquidate_start, pattern="^emergency_liquidate$")],
            states={
                CONFIRM_LIQUIDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_liquidate)]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        ),
        ConversationHandler(
            entry_points=[CallbackQueryHandler(stop_start, pattern="^emergency_full_stop$")],
            states={
                CONFIRM_STOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_stop)]
            },
            fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        ),
        
    ]

    for conv_handler in conv_handlers_list:
        application.add_handler(conv_handler)

    # Handlers de menús y acciones
    # Se agrupan para mantener el código limpio
    all_callback_handlers = main_menu_handlers + action_handlers
    for handler in all_callback_handlers:
        application.add_handler(handler)

    # Un handler genérico para el comando /start como callback query (para el botón "Volver")
    # Esto es redundante con el `main_menu` handler pero es una buena práctica tenerlo
    application.add_handler(CallbackQueryHandler(start, pattern="^start$"))

    logger.info("Bot configurado y listo para iniciar...")

    # 4. Iniciar el Bot
    application.run_polling()

if __name__ == "__main__":
    main()