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

from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from telegram.warnings import PTBUserWarning
import warnings

# Importar handlers desde el módulo de handlers
from handlers import start, main_menu_handlers, action_handlers, conv_handlers

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
    for conv_handler in conv_handlers:
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
