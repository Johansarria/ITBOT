"""
Bot Principal de Telegram para ITBOT - Con UI Mejorada

Este script configura y ejecuta el bot de Telegram con los handlers
de la interfaz mejorada integrada.
"""

import asyncio
import html
import json
import traceback
import warnings
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.warnings import PTBUserWarning

# Importar handlers desde el módulo de handlers
from handlers import start, main_menu_handlers, action_handlers, conv_handlers

# Importar versiones simplificadas de las mejoras de UI
try:
    from handlers.quick_commands_simple import QUICK_COMMANDS
    UI_ENHANCED = True
except ImportError:
    QUICK_COMMANDS = {}
    UI_ENHANCED = False

try:
    from handlers.enhanced_dashboard_simple import ENHANCED_HANDLERS
    DASHBOARD_ENHANCED = True
except ImportError:
    ENHANCED_HANDLERS = {}
    DASHBOARD_ENHANCED = False

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

    # Crear stack trace
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Preparar el mensaje de error
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    error_message = (
        f"Ha ocurrido una excepción mientras se manejaba una actualización\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    try:
        if context.bot_data.get('error_chat_id'):
            await context.bot.send_message(
                chat_id=context.bot_data['error_chat_id'],
                text=error_message,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"No se pudo enviar el mensaje de error: {e}")

def main() -> None:
    """Ejecuta el bot."""
    
    logger.info("=== INICIANDO ITBOT con UI MEJORADA ===")
    
    # Verificar estado de las mejoras
    if UI_ENHANCED:
        logger.info("✅ Comandos rápidos cargados correctamente")
        logger.info(f"📱 Comandos disponibles: {list(QUICK_COMMANDS.keys())}")
    else:
        logger.warning("⚠️ Comandos rápidos no disponibles")
    
    if DASHBOARD_ENHANCED:
        logger.info("✅ Dashboard mejorado cargado")
    else:
        logger.warning("⚠️ Dashboard mejorado no disponible")
    
    # 1. Inicializar Base de Datos
    logger.info("Inicializando base de datos...")
    init_db()

    # 2. Obtener Token y Crear Aplicación
    from config import settings
    token = settings.TELEGRAM_BOT_TOKEN
    
    if not token:
        logger.error("TOKEN DE TELEGRAM NO CONFIGURADO. Verifica config.py o variables de entorno.")
        return

    application = Application.builder().token(token).build()

    # 3. Registrar Handlers
    
    # Registrar el manejador de errores global
    application.add_error_handler(error_handler)

    # Comando de inicio
    application.add_handler(CommandHandler("start", start))
    
    # Registrar comandos rápidos mejorados si están disponibles
    if UI_ENHANCED:
        logger.info(f"Registrando {len(QUICK_COMMANDS)} comandos mejorados...")
        for command, handler in QUICK_COMMANDS.items():
            application.add_handler(CommandHandler(command, handler))
        logger.info("✅ Comandos mejorados registrados")
    
    # Registrar handlers del dashboard mejorado si están disponibles
    if DASHBOARD_ENHANCED:
        logger.info("Registrando handlers del dashboard mejorado...")
        for callback_data, handler in ENHANCED_HANDLERS.items():
            application.add_handler(CallbackQueryHandler(handler, pattern=f"^{callback_data}$"))
        logger.info("✅ Dashboard mejorado registrado")
    
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
    
    # Log de características activas
    total_handlers = len(conv_handlers) + len(all_callback_handlers) + 1  # +1 para start
    if UI_ENHANCED:
        total_handlers += len(QUICK_COMMANDS)
    if DASHBOARD_ENHANCED:
        total_handlers += len(ENHANCED_HANDLERS)
    
    logger.info(f"📊 Total handlers registrados: {total_handlers}")
    logger.info("🚀 ITBOT iniciando con mejoras de UI activas...")

    # 4. Iniciar el Bot
    application.run_polling()

if __name__ == "__main__":
    main()
