#!/usr/bin/env python3
"""
Script para probar los comandos V3 del sistema autónomo
"""

import asyncio
import logging
from telegram import Bot
from config import settings

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def test_v3_commands():
    """
    Probar los comandos V3 disponibles
    """
    try:
        # Inicializar bot
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        # Obtener chat ID (debes reemplazar esto con tu chat ID real)
        # Para obtener tu chat ID, envía cualquier mensaje al bot y verifica los logs
        CHAT_ID = settings.ADMIN_CHAT_ID  # O reemplaza con tu chat ID
        
        logger.info("🧪 Iniciando pruebas de comandos V3...")
        
        # Lista de comandos a probar
        commands_to_test = [
            "/v3_help",
            "/v3_status", 
            "/v3_performance"
        ]
        
        for command in commands_to_test:
            logger.info(f"📤 Enviando comando: {command}")
            try:
                await bot.send_message(
                    chat_id=CHAT_ID, 
                    text=command
                )
                logger.info(f"✅ Comando {command} enviado correctamente")
                await asyncio.sleep(2)  # Esperar 2 segundos entre comandos
                
            except Exception as e:
                logger.error(f"❌ Error enviando {command}: {e}")
        
        logger.info("🏁 Pruebas completadas")
        
    except Exception as e:
        logger.error(f"❌ Error general en las pruebas: {e}")

if __name__ == "__main__":
    asyncio.run(test_v3_commands())
