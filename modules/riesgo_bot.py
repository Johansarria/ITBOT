# modules/riesgo_bot.py

import logging
from utils.telegram_handler import send_message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.risk_manager import (
    activar_riesgo_forzado,
    obtener_riesgo_actual,
    restaurar_riesgo_automatico,
    recordar_riesgo_forzado,
    desactivar_recordatorio_hoy,
    duracion_riesgo_forzado,
    riesgo_forzado_activo
)

logger = logging.getLogger(__name__)

def es_comando_riesgo(mensaje: str) -> bool:
    comandos = [
        "riesgo", "modo de riesgo", "forzar riesgo", "volver a automático",
        "mantener riesgo forzado", "no recordar más hoy"
    ]
    return any(mensaje.lower().startswith(cmd) for cmd in comandos)


async def procesar_comando_riesgo(bot_instance, chat_id, mensaje: str):
    texto = mensaje.lower().strip()
    logger.info(f"Procesando comando de riesgo: {mensaje}")

    if texto.startswith("forzar riesgo"):
        try:
            porcentaje = int(texto.split("forzar riesgo")[-1].strip().replace("%", ""))
            activar_riesgo_forzado(porcentaje)
            logger.info(f"Riesgo forzado activado al {porcentaje}%. ")
            await send_message(bot_instance, chat_id, f"✅ Riesgo forzado activado al {porcentaje}%. ")
        except ValueError as e:
            logger.error(f"Error al interpretar el porcentaje de riesgo (ValueError): {e}", exc_info=True)
            await send_message(bot_instance, chat_id, "❌ Formato de porcentaje inválido. Usa: 'forzar riesgo 5%' por ejemplo.")
        except Exception as e:
            logger.exception(f"Error inesperado al procesar el comando de riesgo: {e}")
            await send_message(bot_instance, chat_id, "❌ Ocurrió un error inesperado al procesar tu solicitud de riesgo.")
        return

    if texto == "modo de riesgo" or texto == "riesgo":
        modo = "Automático"
        if riesgo_forzado_activo():
            modo = f"⚠️ Forzado ({obtener_riesgo_actual() * 100:.0f}%)"
        duracion = duracion_riesgo_forzado()
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="📊 Ver Modo Actual", callback_data="risk_status")],
            [InlineKeyboardButton(text="💪 Forzar Riesgo", callback_data="force_risk_menu")],
            [InlineKeyboardButton(text="🔄 Volver a Automático", callback_data="set_auto_risk")],
            [InlineKeyboardButton(text="⏳ Mantener Riesgo Forzado", callback_data="keep_forced_risk")],
            [InlineKeyboardButton(text="🔕 No Recordar Más Hoy", callback_data="disable_risk_reminder")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await send_message(bot_instance, chat_id, f"🎯 Modo de riesgo actual: {modo}\n⏱️ Tiempo activo: {duracion}\n\nSelecciona una opción:", reply_markup=reply_markup)
        logger.info("Menú de riesgo enviado a Telegram.")
        return

    if texto == "volver a automático":
        restaurar_riesgo_automatico()
        logger.info("Riesgo automático restaurado. ")
        await send_message(bot_instance, chat_id, "🔄 Riesgo automático restaurado. ")
        return

    if texto == "mantener riesgo forzado":
        logger.info("Manteniendo riesgo forzado activo. ")
        await send_message(bot_instance, chat_id, "⏳ Manteniendo riesgo forzado activo. ")
        return

    if texto == "no recordar más hoy":
        desactivar_recordatorio_hoy()
        logger.info("Recordatorio de riesgo forzado desactivado por hoy. ")
        await send_message(bot_instance, chat_id, "🔕 No se recordará más el riesgo forzado hoy. ")
        return