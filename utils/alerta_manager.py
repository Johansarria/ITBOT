# utils/alerta_manager.py

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional
import json

from utils.telegram_handler import send_message as send_telegram_message

class SeverityLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Alerter:
    _instance = None

    SEVERITY_EMOJIS = {
        SeverityLevel.INFO: "ℹ️",
        SeverityLevel.WARNING: "⚠️",
        SeverityLevel.ERROR: "❌",
        SeverityLevel.CRITICAL: "🚨",
    }

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Alerter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._bot_instance = None
        self._chat_id = None
        self._last_alerts: Dict[str, datetime] = {}
        self._silence_period = timedelta(minutes=15)
        self._initialized = True
        print("Alerter initialized with deduplication.")

    def configure(self, bot_instance: Any, chat_id: int):
        """Configures the alerter with the bot instance and chat ID."""
        self._bot_instance = bot_instance
        self._chat_id = chat_id
        print(f"Alerter configured with chat_id: {chat_id}")

    def _format_message(self, severity: SeverityLevel, source: str, message: str, details: Optional[Dict[str, Any]] = None) -> str:
        """Formats the alert message for Telegram."""
        emoji = self.SEVERITY_EMOJIS.get(severity, "📢")

        formatted_message = (
            f"{emoji} *{severity.value}: {source}*\n\n"
            f"{message}\n"
        )

        if details:
            try:
                # Use code block for nicely formatted JSON
                details_str = json.dumps(details, indent=2, default=str)
                formatted_message += f"\n*Detalles Adicionales:*\n```json\n{details_str}\n```"
            except TypeError:
                formatted_message += f"\n*Detalles Adicionales:*\n`{str(details)}`"

        return formatted_message

    async def send_alert(
        self,
        alert_key: str,
        severity: SeverityLevel,
        source: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Sends an alert after checking for deduplication.
        If an alert with the same key was sent within the silence period, it will be suppressed.
        """
        now = datetime.now()
        last_alert_time = self._last_alerts.get(alert_key)

        # Tolerancia pequeña para evitar falsos positivos cuando _silence_period
        # es muy corto y el scheduler introduce jitter (tests usan ~0.1s)
        if last_alert_time:
            delta = now - last_alert_time
            epsilon = timedelta(milliseconds=50)
            if (delta + epsilon) < self._silence_period:
                print(f"Alert '{alert_key}' suppressed due to deduplication rules.")
                return

        if not self._bot_instance or not self._chat_id:
            print(f"Alerter not configured. Alert suppressed: {message}")
            return

        formatted_text = self._format_message(severity, source, message, details)

        # In a real scenario, we would use the actual telegram handler.
        try:
            await send_telegram_message(self._bot_instance, self._chat_id, formatted_text, parse_mode="Markdown")
            # Update the timestamp only if the message was sent successfully
            self._last_alerts[alert_key] = now
        except Exception as e:
            print(f"ERROR: Failed to send Telegram alert '{alert_key}'. Reason: {e}")


# Singleton instance
alerter = Alerter()
