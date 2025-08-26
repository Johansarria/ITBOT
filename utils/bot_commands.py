# utils/bot_commands.py

import logging
import aiohttp
from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeDefault

logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    """
    Registra los comandos disponibles para el bot en Telegram.
    Esto crea el menú de comandos en la interfaz de chat.
    """
    commands = [
                BotCommand(command="/start", description="Iniciar el bot y mostrar el menú principal."),
        BotCommand(command="/menu", description="Mostrar el menú principal."),
        BotCommand(command="/help", description="Mostrar este mensaje de ayuda."),
        BotCommand(command="/status", description="Verificar si el bot está funcionando."),
        BotCommand(command="/posiciones", description="Mostrar un resumen de las posiciones abiertas."),
        BotCommand(command="/reportes", description="Generar reportes de operaciones."),
        BotCommand(command="/riesgo", description="Consultar o ajustar el nivel de riesgo."),
        BotCommand(command="/analizar", description="Realizar un análisis técnico del mercado."),
        BotCommand(command="/estrategia", description="Ver/cambiar la estrategia de análisis."),
    ]
    
    try:
        await bot.set_my_commands(commands, BotCommandScopeDefault())
        logger.info("Comandos del bot registrados exitosamente en Telegram.")
    except aiohttp.ClientError as e:
        logger.error(f"Error de conexión o API al registrar los comandos del bot: {e}", exc_info=True)
    except Exception as e:
        logger.exception(f"Error inesperado al registrar los comandos del bot: {e}")
