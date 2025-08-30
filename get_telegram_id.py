#!/usr/bin/env python3
"""
Script temporal para obtener tu ID de Telegram.
Ejecuta este script y luego envía cualquier mensaje al bot.
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler que muestra el ID del usuario que envía un mensaje."""
    user = update.effective_user
    chat = update.effective_chat
    
    info = f"""
🆔 INFORMACIÓN DE TELEGRAM:
    
👤 Usuario:
  - ID: {user.id}
  - Nombre: {user.first_name} {user.last_name or ''}
  - Username: @{user.username or 'Sin username'}
  - Es Bot: {user.is_bot}

💬 Chat:
  - ID: {chat.id}
  - Tipo: {chat.type}
  - Título: {chat.title or 'N/A'}

🔧 Para configurar como admin:
  ADMIN_TELEGRAM_ID={user.id}
    """
    
    print("="*50)
    print(info)
    print("="*50)
    
    await update.message.reply_text(
        f"Tu ID de Telegram es: `{user.id}`\n\n"
        f"Copia esta línea en tu .env:\n"
        f"`ADMIN_TELEGRAM_ID={user.id}`",
        parse_mode='Markdown'
    )

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ ERROR: No se encontró TELEGRAM_BOT_TOKEN en las variables de entorno")
        print("💡 Asegúrate de que el archivo .env esté cargado")
        return
    
    print("🤖 Bot temporal iniciado para obtener ID de Telegram")
    print("📱 Envía cualquier mensaje al bot para obtener tu ID")
    print("🛑 Presiona Ctrl+C para detener")
    
    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_id))
    
    try:
        application.run_polling()
    except KeyboardInterrupt:
        print("\n✅ Bot detenido. ¡Usa el ID mostrado para configurar ADMIN_TELEGRAM_ID!")

if __name__ == "__main__":
    main()
