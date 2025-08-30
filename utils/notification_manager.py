# utils/notification_manager.py

"""
Sistema de notificaciones inteligente para ITBOT.
Controla qué mensajes se envían al usuario para evitar ruido innecesario.
"""

import logging
from enum import Enum
from typing import Optional, Any
from utils.telegram_handler import send_message as _send_message

logger = logging.getLogger(__name__)

class NotificationLevel(Enum):
    """Niveles de importancia de las notificaciones."""
    SILENT = 0      # No enviar
    INFO = 1        # Información (solo logs)
    IMPORTANT = 2   # Eventos importantes (enviar)
    CRITICAL = 3    # Errores críticos (siempre enviar)
    TRADE = 4       # Operaciones de trading (siempre enviar)

class NotificationManager:
    """Gestor inteligente de notificaciones."""
    
    def __init__(self, min_level: NotificationLevel = NotificationLevel.IMPORTANT):
        self.min_level = min_level
        self._last_daily_summary = None
        
    async def send_notification(
        self, 
        bot_instance: Optional[Any], 
        chat_id: Optional[int], 
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        force: bool = False
    ):
        """
        Envía una notificación según el nivel de importancia.
        
        Args:
            bot_instance: Instancia del bot de Telegram
            chat_id: ID del chat
            message: Mensaje a enviar
            level: Nivel de importancia
            force: Forzar envío independientemente del nivel
        """
        # Siempre log la información
        log_level = logging.INFO
        if level == NotificationLevel.CRITICAL:
            log_level = logging.ERROR
        elif level == NotificationLevel.IMPORTANT:
            log_level = logging.WARNING
            
        logger.log(log_level, f"NOTIFICATION [{level.name}]: {message}")
        
        # Decidir si enviar por Telegram
        should_send = (
            force or 
            level.value >= self.min_level.value or
            level in [NotificationLevel.CRITICAL, NotificationLevel.TRADE]
        )
        
        if should_send and bot_instance and chat_id:
            try:
                await _send_message(bot_instance, chat_id, message)
            except Exception as e:
                logger.error(f"Error enviando notificación: {e}")
    
    async def notify_error(self, bot_instance: Optional[Any], chat_id: Optional[int], error_msg: str):
        """Notificar errores críticos."""
        await self.send_notification(
            bot_instance, chat_id, f"❌ **Error**: {error_msg}", 
            NotificationLevel.CRITICAL
        )
    
    async def notify_trade(self, bot_instance: Optional[Any], chat_id: Optional[int], trade_msg: str):
        """Notificar operaciones de trading."""
        await self.send_notification(
            bot_instance, chat_id, f"💰 **Trading**: {trade_msg}", 
            NotificationLevel.TRADE
        )
    
    async def notify_shield(self, bot_instance: Optional[Any], chat_id: Optional[int], shield_msg: str):
        """Notificar activación del escudo de protección."""
        await self.send_notification(
            bot_instance, chat_id, f"🛡️ **Escudo**: {shield_msg}", 
            NotificationLevel.IMPORTANT
        )
    
    async def notify_system_event(self, bot_instance: Optional[Any], chat_id: Optional[int], event_msg: str):
        """Notificar eventos importantes del sistema."""
        await self.send_notification(
            bot_instance, chat_id, f"⚙️ **Sistema**: {event_msg}", 
            NotificationLevel.IMPORTANT
        )
    
    async def notify_daily_summary(self, bot_instance: Optional[Any], chat_id: Optional[int], summary: dict):
        """Enviar resumen diario (solo una vez por día)."""
        import datetime
        today = datetime.date.today()
        
        if self._last_daily_summary != today:
            trades = summary.get('trades', 0)
            profit = summary.get('profit_pct', 0.0)
            errors = summary.get('errors', 0)
            
            message = f"""📊 **Resumen Diario - {today}**
🔄 Operaciones: {trades}
📈 Rentabilidad: {profit:+.2f}%
⚠️ Errores: {errors}
🤖 Estado: {'LIVE' if summary.get('live_mode', False) else 'PAPER'}"""
            
            await self.send_notification(
                bot_instance, chat_id, message, 
                NotificationLevel.IMPORTANT, force=True
            )
            self._last_daily_summary = today

# Instancia global del gestor de notificaciones
notification_manager = NotificationManager(NotificationLevel.IMPORTANT)

# Funciones de conveniencia para usar en todo el código
async def notify_error(bot_instance: Optional[Any], chat_id: Optional[int], error_msg: str):
    await notification_manager.notify_error(bot_instance, chat_id, error_msg)

async def notify_trade(bot_instance: Optional[Any], chat_id: Optional[int], trade_msg: str):
    await notification_manager.notify_trade(bot_instance, chat_id, trade_msg)

async def notify_shield(bot_instance: Optional[Any], chat_id: Optional[int], shield_msg: str):
    await notification_manager.notify_shield(bot_instance, chat_id, shield_msg)

async def notify_system_event(bot_instance: Optional[Any], chat_id: Optional[int], event_msg: str):
    await notification_manager.notify_system_event(bot_instance, chat_id, event_msg)

async def notify_daily_summary(bot_instance: Optional[Any], chat_id: Optional[int], summary: dict):
    await notification_manager.notify_daily_summary(bot_instance, chat_id, summary)

async def send_silent(message: str):
    """Solo log, sin notificación Telegram."""
    logger.info(f"SILENT: {message}")
