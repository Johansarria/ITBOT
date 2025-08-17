# estado_diario.py

import asyncio
from datetime import datetime, timezone
import zoneinfo
from utils.telegram_handler import send_message, shutdown_bot
from utils.state_manager import StateManager
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
# REMOVED: from utils.env_loader import load_env
import config # ADDED: Import config

# La función ahora recibe bot_instance y chat_id
async def enviar_estado_diario(bot_instance: Bot, chat_id: int):
    state_manager = StateManager()
    
    # Obtener estado de riesgo
    risk_state = state_manager.get_state("risk_manager")
    riesgo_forzado = risk_state.get("riesgo_forzado", False)
    riesgo_actual_pct = risk_state.get("riesgo_actual", 0.01) * 100
    tiempo_riesgo_forzado = risk_state.get("tiempo_riesgo_forzado")
    
    # Obtener estado de escudo (asumiendo que lo implementaremos en shield_manager)
    shield_state = state_manager.get_state("shield_manager")
    escudo_activo = shield_state.get("escudo_activo", False)
    tipo_escudo = shield_state.get("tipo_escudo", "NINGUNO")

    # Obtener estado de IA (asumiendo que lo implementaremos en ia_manager)
    ia_state = state_manager.get_state("ia_manager")
    ia_activa = ia_state.get("ia_activa", False)
    modo_ia = ia_state.get("modo_ia", "normal")

    # Obtener última fecha de reporte diario
    last_report_date_str = state_manager.get_state("general", "last_daily_report_date")
    last_report_date = datetime.fromisoformat(last_report_date_str).replace(tzinfo=zoneinfo.ZoneInfo("UTC")) if last_report_date_str else None

    # Construir mensaje
    mensaje = """⏰ *ESTADO DIARIO DEL BOT:*"""
    mensaje += f"\n- Fecha del reporte: {datetime.now(zoneinfo.ZoneInfo('UTC')).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
    
    mensaje += f"- Riesgo forzado: {'✅' if riesgo_forzado else '❌'} ({riesgo_actual_pct:.0f}%)"
    if riesgo_forzado and tiempo_riesgo_forzado:
        if isinstance(tiempo_riesgo_forzado, str):
            tiempo_riesgo_forzado = datetime.fromisoformat(tiempo_riesgo_forzado).replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        duracion = datetime.now() - tiempo_riesgo_forzado
        horas = int(duracion.total_seconds() // 3600)
        mensaje += f" desde hace {horas}h\n"
    else:
        mensaje += "\n"

    mensaje += f"- Escudo activo: {'✅' if escudo_activo else '❌'} ({tipo_escudo})\n"
    mensaje += f"- IA activa: {'✅' if ia_activa else '❌'} (Modo: {modo_ia})\n"
    mensaje += f"- Último reporte diario enviado: {last_report_date.strftime('%Y-%m-%d') if last_report_date else 'N/A'}\n"

    # Enviar mensaje usando la instancia del bot y el chat_id
    await send_message(bot_instance, chat_id, mensaje)

    # Actualizar la fecha del último reporte diario
    state_manager.set_state("general", "last_daily_report_date", datetime.now(zoneinfo.ZoneInfo("UTC")).isoformat())

# El bloque __main__ ya no necesita inicializar el bot, solo llamar a la función
if __name__ == "__main__":
    # Este bloque solo se usa para pruebas directas de estado_diario.py
    # En producción, será llamado por el scheduler en listener_bot.py
    async def test_enviar_estado_diario():
        # REMOVED: env_vars = load_env()
        # REMOVED: token = env_vars.get("TELEGRAM_TOKEN")
        # REMOVED: chat_id_str = env_vars.get("TELEGRAM_CHAT_ID")
        # REMOVED: if not token or not chat_id_str or not chat_id_str.isdigit():
        # REMOVED:     raise ValueError("Token o Chat ID no definidos para prueba directa.")
        
        bot_instance = Bot(token=config.TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) # MODIFIED
        await enviar_estado_diario(bot_instance, config.TELEGRAM_CHAT_ID) # MODIFIED
        await shutdown_bot(bot_instance) # Cerrar la sesión del bot

    asyncio.run(test_enviar_estado_diario())