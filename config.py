# config.py

import os
from utils.env_loader import load_env
import logging

logger = logging.getLogger(__name__)


# Todas las variables sensibles y de configuración se cargan solo desde variables de entorno
TELEGRAM_TOKEN = None
TELEGRAM_CHAT_ID = None
BINANCE_API_KEY = None
BINANCE_SECRET_KEY = None
TRADING_PAIR = None
TRADING_INTERVAL = None
MODE = None
LIVE_UNLOCK_FILE_PATH = None
DEFAULT_RISK_PERCENTAGE = None
TAKE_PROFIT_PERCENTAGE = None
STOP_LOSS_PERCENTAGE = None
MAX_DAILY_OPERATIONS = None
MAX_DAILY_LOSS_PCT = None
MAX_TRADE_RISK_PCT = None
MAX_CONCURRENT_POSITIONS = None
AUTONOMOUS_CYCLE_SECONDS = None
RETRY_ON_ERROR_SECONDS = None
ANALYSIS_INTERVAL_SECONDS = None
REDIS_HOST = None
REDIS_PORT = None
REDIS_DB = None
REDIS_DECISION_QUEUE_NAME = None
LOG_LEVEL = None # ADDED

VERBOSE_NOTIFICATIONS = None

def load_configurations():
    """
    Carga o recarga todas las configuraciones desde las variables de entorno.
    """
    global TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, BINANCE_API_KEY, BINANCE_SECRET_KEY,            TRADING_PAIR, TRADING_INTERVAL, MODE, LIVE_UNLOCK_FILE_PATH, DEFAULT_RISK_PERCENTAGE,            TAKE_PROFIT_PERCENTAGE, STOP_LOSS_PERCENTAGE, MAX_DAILY_OPERATIONS,            MAX_DAILY_LOSS_PCT, MAX_TRADE_RISK_PCT, MAX_CONCURRENT_POSITIONS,            AUTONOMOUS_CYCLE_SECONDS, RETRY_ON_ERROR_SECONDS, ANALYSIS_INTERVAL_SECONDS,            REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_DECISION_QUEUE_NAME, PRODUCTION_MODE


    _env_vars = load_env()

    # --- MODO DE OPERACIÓN ---
    # Si PRODUCTION_MODE es True, el bot requerirá confirmaciones y operará con más seguridad.
    PRODUCTION_MODE = os.environ.get("PRODUCTION_MODE", "False").lower() in ('true', '1', 't')

    # --- CONFIGURACIÓN DE API Y TELEGRAM ---
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", 0))
    BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
    BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY")

    # --- CONFIGURACIÓN DE TRADING ---
    TRADING_PAIR = os.environ.get("TRADING_PAIR", "BTCUSDT")
    TRADING_INTERVAL = os.environ.get("TRADING_INTERVAL", "1h")
    MODE = os.environ.get("MODE", "live")

    # --- CONFIGURACIÓN DE SEGURIDAD PARA MODO LIVE ---
    LIVE_UNLOCK_FILE_PATH = os.path.join(os.getcwd(), "LIVE_UNLOCK.txt")

    # --- GESTIÓN DE RIESGO ---
    DEFAULT_RISK_PERCENTAGE = float(os.environ.get("DEFAULT_RISK_PERCENTAGE", 1.0))
    TAKE_PROFIT_PERCENTAGE = float(os.environ.get("TAKE_PROFIT_PERCENTAGE", 3.0))
    STOP_LOSS_PERCENTAGE = float(os.environ.get("STOP_LOSS_PERCENTAGE", 1.5))
    MAX_DAILY_OPERATIONS = int(os.environ.get("MAX_DAILY_OPERATIONS", 10))
    MAX_DAILY_LOSS_PCT = float(os.environ.get("MAX_DAILY_LOSS_PCT", 5.0))
    MAX_TRADE_RISK_PCT = float(os.environ.get("MAX_TRADE_RISK_PCT", 1.0))
    MAX_CONCURRENT_POSITIONS = int(os.environ.get("MAX_CONCURRENT_POSITIONS", 3))

    # --- CONFIGURACIÓN DEL RUNNER ---
    AUTONOMOUS_CYCLE_SECONDS = int(os.environ.get("AUTONOMOUS_CYCLE_SECONDS", 3600))
    RETRY_ON_ERROR_SECONDS = int(os.environ.get("RETRY_ON_ERROR_SECONDS", 300))
    ANALYSIS_INTERVAL_SECONDS = int(os.environ.get("ANALYSIS_INTERVAL_SECONDS", 300))

    # --- CONFIGURACIÓN DE REDIS ---
    REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
    REDIS_DB = int(os.environ.get("REDIS_DB", 0))
    REDIS_DECISION_QUEUE_NAME = os.environ.get("REDIS_DECISION_QUEUE_NAME", "trading_decisions_queue")

    # --- VALIDACIONES BÁSICAS ---
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN no está definido en las variables de entorno.")
    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID no está definido o no es un número válido en las variables de entorno.")
    if not BINANCE_API_KEY:
        logger.error("BINANCE_API_KEY no está definido en las variables de entorno.")
    if not BINANCE_SECRET_KEY:
        logger.error("BINANCE_SECRET_KEY no está definido en las variables de entorno.")

    logger.info(f"Configuraciones cargadas/recargadas. Modo Producción: {PRODUCTION_MODE}")


# Cargar configuraciones al importar el módulo por primera vez
load_configurations()

# NOTA DE SEGURIDAD:
# Nunca almacenes claves o secretos en este archivo ni en el repositorio.
# Usa solo variables de entorno y .env (excluido del control de versiones).
# Realiza rotación periódica de claves y revisa los accesos.
