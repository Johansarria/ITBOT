#!/usr/bin/env python3
"""
HANDLERS V3 AUTÓNOMO
===================
Handlers para integrar los comandos V3 con el bot de Telegram existente.

Este módulo proporciona:
- Comandos de Telegram para controlar el sistema V3
- Integración con el sistema de handlers existente
- Callbacks para botones de control V3
"""

import asyncio
from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.v3_controller import (
    handle_v3_start_command,
    handle_v3_stop_command,
    handle_v3_status_command,
    handle_v3_performance_command,
    handle_v3_emergency_stop_command
)
from utils.structured_logger import StructuredLogger

logger = StructuredLogger(__name__)

# =============================================================================
# HANDLERS DE COMANDOS V3
# =============================================================================

async def v3_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para comando /v3_start"""
    try:
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.info(
            "V3_START_HANDLER",
            "Procesando comando /v3_start",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_start_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_START_HANDLER_ERROR", f"Error en handler /v3_start: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error procesando comando: {e}")


async def v3_stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para comando /v3_stop"""
    try:
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.info(
            "V3_STOP_HANDLER",
            "Procesando comando /v3_stop",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_stop_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_STOP_HANDLER_ERROR", f"Error en handler /v3_stop: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error procesando comando: {e}")


async def v3_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para comando /v3_status"""
    try:
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.info(
            "V3_STATUS_HANDLER",
            "Procesando comando /v3_status",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_status_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_STATUS_HANDLER_ERROR", f"Error en handler /v3_status: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error procesando comando: {e}")


async def v3_performance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para comando /v3_performance"""
    try:
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.info(
            "V3_PERFORMANCE_HANDLER",
            "Procesando comando /v3_performance",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_performance_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_PERFORMANCE_HANDLER_ERROR", f"Error en handler /v3_performance: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error procesando comando: {e}")


async def v3_emergency_stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para comando /v3_emergency_stop"""
    try:
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.warning(
            "V3_EMERGENCY_STOP_HANDLER",
            "Procesando comando /v3_emergency_stop",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_emergency_stop_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_EMERGENCY_STOP_HANDLER_ERROR", f"Error en handler /v3_emergency_stop: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error procesando comando: {e}")


# =============================================================================
# HANDLERS DE CALLBACKS (BOTONES)
# =============================================================================

async def v3_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler para botón V3 Start"""
    try:
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.info(
            "V3_START_CALLBACK",
            "Procesando callback v3_start",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_start_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_START_CALLBACK_ERROR", f"Error en callback v3_start: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.message.reply_text(f"❌ Error procesando acción: {e}")


async def v3_stop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler para botón V3 Stop"""
    try:
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.info(
            "V3_STOP_CALLBACK",
            "Procesando callback v3_stop",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_stop_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_STOP_CALLBACK_ERROR", f"Error en callback v3_stop: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.message.reply_text(f"❌ Error procesando acción: {e}")


async def v3_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler para botón V3 Status"""
    try:
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.info(
            "V3_STATUS_CALLBACK",
            "Procesando callback v3_status",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_status_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_STATUS_CALLBACK_ERROR", f"Error en callback v3_status: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.message.reply_text(f"❌ Error procesando acción: {e}")


async def v3_performance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback handler para botón V3 Performance"""
    try:
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        bot_instance = context.bot
        
        logger.info(
            "V3_PERFORMANCE_CALLBACK",
            "Procesando callback v3_performance",
            details={"chat_id": chat_id, "user_id": update.effective_user.id}
        )
        
        await handle_v3_performance_command(bot_instance, chat_id)
        
    except Exception as e:
        logger.error("V3_PERFORMANCE_CALLBACK_ERROR", f"Error en callback v3_performance: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.message.reply_text(f"❌ Error procesando acción: {e}")


# =============================================================================
# COMANDO DE AYUDA V3
# =============================================================================

async def v3_help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para comando /v3_help"""
    try:
        help_message = """🚀 **SISTEMA V3 AUTÓNOMO - AYUDA**
================================

El Sistema V3 utiliza estrategias optimizadas basadas en 540 pruebas comprehensivas con datos reales de Binance.

📊 **ESTRATEGIAS ACTIVAS:**
• ✅ Scalping SOL/USDT 30m (14.15% mensual)
• ✅ Híbrido SOL/USDT 15m (13.47% mensual)  
• ✅ Híbrido BTC/USDT 1h (11.23% mensual)

🎮 **COMANDOS DISPONIBLES:**
• `/v3_start` - Iniciar sistema V3 autónomo
• `/v3_stop` - Detener sistema V3 autónomo
• `/v3_status` - Ver estado actual del sistema
• `/v3_performance` - Ver reporte de rendimiento
• `/v3_emergency_stop` - Parada de emergencia
• `/v3_help` - Mostrar esta ayuda

🔧 **CARACTERÍSTICAS:**
• ✅ Análisis continuo de mercado
• ✅ Múltiples indicadores técnicos
• ✅ Gestión dinámica de riesgo
• ✅ Stop-loss y take-profit automáticos
• ✅ Integración con sistema de órdenes existente

⚠️ **IMPORTANTE:**
- El sistema funciona de manera autónoma una vez iniciado
- Se integra con el sistema de riesgo existente
- Todas las operaciones pasan por validaciones de seguridad
- Los resultados son proyecciones basadas en backtesting

💡 **SOPORTE:**
Para más información, consulta los logs del sistema o contacta al administrador."""

        await update.message.reply_text(help_message, parse_mode='Markdown')
        
        logger.info(
            "V3_HELP_HANDLER",
            "Comando /v3_help ejecutado",
            details={"chat_id": update.effective_chat.id, "user_id": update.effective_user.id}
        )
        
    except Exception as e:
        logger.error("V3_HELP_HANDLER_ERROR", f"Error en handler /v3_help: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error mostrando ayuda: {e}")


# =============================================================================
# DEFINICIÓN DE HANDLERS PARA EXPORTAR
# =============================================================================

# Command Handlers para comandos V3
V3_COMMAND_HANDLERS = {
    "v3_start": v3_start_handler,
    "v3_stop": v3_stop_handler,
    "v3_status": v3_status_handler,
    "v3_performance": v3_performance_handler,
    "v3_emergency_stop": v3_emergency_stop_handler,
    "v3_help": v3_help_handler,
}

# Callback Handlers para botones V3
V3_CALLBACK_HANDLERS = {
    "v3_start": v3_start_callback,
    "v3_stop": v3_stop_callback,
    "v3_status": v3_status_callback,
    "v3_performance": v3_performance_callback,
}

# Lista de CommandHandlers para integración con main.py
V3_COMMAND_HANDLERS_LIST = [
    CommandHandler("v3_start", v3_start_handler),
    CommandHandler("v3_stop", v3_stop_handler),
    CommandHandler("v3_status", v3_status_handler),
    CommandHandler("v3_performance", v3_performance_handler),
    CommandHandler("v3_emergency_stop", v3_emergency_stop_handler),
    CommandHandler("v3_help", v3_help_handler),
]

# Lista de CallbackQueryHandlers para integración con main.py
V3_CALLBACK_HANDLERS_LIST = [
    CallbackQueryHandler(v3_start_callback, pattern="^v3_start$"),
    CallbackQueryHandler(v3_stop_callback, pattern="^v3_stop$"),
    CallbackQueryHandler(v3_status_callback, pattern="^v3_status$"),
    CallbackQueryHandler(v3_performance_callback, pattern="^v3_performance$"),
]


if __name__ == "__main__":
    print("🎮 HANDLERS V3 AUTÓNOMO")
    print("=" * 40)
    print("Handlers para integración del sistema V3 con Telegram.")
    print(f"Comandos disponibles: {len(V3_COMMAND_HANDLERS)}")
    print(f"Callbacks disponibles: {len(V3_CALLBACK_HANDLERS)}")
    print()
    print("Comandos:")
    for cmd in V3_COMMAND_HANDLERS.keys():
        print(f"  • /{cmd}")
    print()
    print("Callbacks:")
    for callback in V3_CALLBACK_HANDLERS.keys():
        print(f"  • {callback}")
