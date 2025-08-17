import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "itbot.log")

def setup_logging():
    """
    Configura el sistema de logging para el bot ITBOT.
    Los logs se guardarán en un archivo y se mostrarán en la consola.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    # Crear un logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.INFO) # Nivel mínimo de logging (INFO, DEBUG, WARNING, ERROR, CRITICAL)

    # Evitar añadir handlers múltiples veces si el setup se llama más de una vez
    if not logger.handlers:
        # Formato para los logs
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Handler para la consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Handler para el archivo de log con rotación diaria
        file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1, backupCount=7, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Mensaje de inicio de logging
    logger.info(f"--- ITBOT Logging iniciado a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")

# La llamada a setup_logging() se elimina de aquí. Se hará explícitamente en run_bot.py