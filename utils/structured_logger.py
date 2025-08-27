import logging
import uuid
from typing import Dict, Any, Optional

class StructuredLogger:
    """
    A wrapper around the standard Python logger to facilitate creating
    structured JSON logs with consistent, detailed context.

    Usage:
        logger = StructuredLogger(__name__)
        logger.info(
            event_type="USER_LOGIN",
            message="User successfully logged in.",
            details={"user_id": "123", "ip_address": "192.168.1.1"}
        )
    """
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def _log(self, level: int, event_type: str, message: str, details: Optional[Dict[str, Any]], exc_info=False):
        """Internal logging method to structure the log message."""
        if details is None:
            details = {}

        # --- Enrich log details automatically ---
        if 'event_id' not in details:
            details['event_id'] = str(uuid.uuid4())

        details['event_type'] = event_type
        details['message'] = message # Ensure message is also in the details payload

        self.logger.log(level, message, extra={'details': details}, exc_info=exc_info)

    def info(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Logs a message with level INFO."""
        self._log(logging.INFO, event_type, message, details)

    def warning(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Logs a message with level WARNING."""
        self._log(logging.WARNING, event_type, message, details)

    def error(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None, exc_info=True):
        """Logs a message with level ERROR, including exception info by default."""
        self._log(logging.ERROR, event_type, message, details, exc_info=exc_info)

    def critical(self, event_type: str, message: str, details: Optional[Dict[str, Any]] = None, exc_info=True):
        """Logs a message with level CRITICAL, including exception info by default."""
        self._log(logging.CRITICAL, event_type, message, details, exc_info=exc_info)
