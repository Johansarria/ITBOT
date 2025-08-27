import logging
import os
import json
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "itbot.log")

class JsonFormatter(logging.Formatter):
    """
    Formats log records as a JSON string.
    """
    def format(self, record):
        # Create a base log object from the record
        log_object = {
            "timestamp_utc": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        # This is the magic part: if the log call includes `extra={'details': ...}`
        # those details will be on the record object.
        if hasattr(record, 'details') and isinstance(record.details, dict):
            log_object.update(record.details)

        # Add exception info if it exists
        if record.exc_info:
            log_object['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_object, default=str)

class ConsoleFormatter(logging.Formatter):
    """
    Formats log records for console output with colors for better readability.
    """
    GREY = "\x1b[38;5;240m"
    WHITE = "\x1b[37m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

    # Define format string
    format_str = "%(asctime)s - %(name)-18s - %(levelname)-8s - %(message)s"

    FORMATS = {
        logging.DEBUG: GREY + format_str + RESET,
        logging.INFO: WHITE + format_str + RESET,
        logging.WARNING: YELLOW + format_str + RESET,
        logging.ERROR: RED + format_str + RESET,
        logging.CRITICAL: BOLD_RED + format_str + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

def setup_logging():
    """
    Configura el sistema de logging para el bot ITBOT.
    Los logs se guardarán en un archivo (JSON) y se mostrarán en la consola (texto).
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Evitar añadir handlers múltiples veces
    if logger.handlers:
        # Limpiar handlers existentes para reconfigurar
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    # Handler para la consola con formato de texto
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)

    # Handler para el archivo de log con rotación diaria y formato JSON
    file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    # Mensaje de inicio de logging. El logger estructurado se encargará de añadir detalles.
    logger.info("--- ITBOT Logging iniciado ---")

# La llamada a setup_logging() se elimina de aquí. Se hará explícitamente en run_bot.py