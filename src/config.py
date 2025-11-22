# /src/config.py
import os
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# --- Claves de API ---
# Nota: Estas claves deben estar en tu archivo .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

# --- Parámetros de Trading ---
# Configuración Multi-Símbolo
TRADING_SYMBOLS = ["BTCUSDT", "ETHUSDT"]  # Lista de símbolos a operar
PRIMARY_SYMBOL = "BTCUSDT"  # Símbolo principal (para compatibilidad)
TRADING_PAIR = "BTC/USDT"  # Mantenido para compatibilidad con código legacy

# Distribución de capital por símbolo (debe sumar 1.0)
CAPITAL_ALLOCATION = {
    "BTCUSDT": 0.6,  # 60% del capital
    "ETHUSDT": 0.4   # 40% del capital
}

TIMEFRAME = os.getenv('TIMEFRAME', '1h')
CAPITAL_BASE = float(os.getenv('CAPITAL_BASE', '500'))

# --- PARÁMETROS OPTIMIZADOS PARA 15% ROI MENSUAL ---
RISK_PER_TRADE = float(os.getenv('RISK_PER_TRADE', '0.10'))
STOP_LOSS_PCT = float(os.getenv('STOP_LOSS_PCT', '0.10'))
TAKE_PROFIT_PCT = float(os.getenv('TAKE_PROFIT_PCT', '0.15'))
POSITION_SIZE_PCT = float(os.getenv('POSITION_SIZE_PCT', '0.70'))
CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', '0.55'))
MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', '3'))

# --- Parámetros del Bot ---
TRADING_MODE = os.getenv('TRADING_MODE', 'testnet').lower()
PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
KILL_SWITCH_MAX_DRAWDOWN = float(os.getenv('KILL_SWITCH_MAX_DRAWDOWN', '0.25'))

# --- Configuración de Modelos ---
SPACY_MODEL = os.getenv('SPACY_MODEL', 'es_core_news_sm')
N_REGIMES = int(os.getenv('N_REGIMES', '4'))

# --- Configuración de Datos ---
DATA_UPDATE_INTERVAL = int(os.getenv('DATA_UPDATE_INTERVAL', '3600'))
LOOKBACK_PERIOD = os.getenv('LOOKBACK_PERIOD', '5y')

# --- Configuración de Logging ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Configuración de Backtesting ---
INITIAL_CASH = float(os.getenv('INITIAL_CASH', '10000'))
COMMISSION = float(os.getenv('COMMISSION', '0.001'))

# --- Configuración de Alertas ---
ENABLE_ALERTS = os.getenv('ENABLE_ALERTS', 'true').lower() == 'true'
ALERT_METHODS = [m.strip() for m in os.getenv('ALERT_METHODS', 'console,log').split(',') if m.strip()]
ALERT_WEBHOOK_URL = os.getenv('ALERT_WEBHOOK_URL')

# --- Configuración de Seguridad (VALORES OPTIMIZADOS) ---
MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.70'))
STOP_LOSS_PERCENTAGE = float(os.getenv('STOP_LOSS_PERCENTAGE', '0.05'))
TAKE_PROFIT_PERCENTAGE = float(os.getenv('TAKE_PROFIT_PERCENTAGE', '0.15'))

# --- Parámetros Adicionales Optimizados ---
SIGNAL_QUALITY_MIN = float(os.getenv('SIGNAL_QUALITY_MIN', '0.60'))
REBALANCE_FREQUENCY = int(os.getenv('REBALANCE_FREQUENCY', '2'))
DRAWDOWN_LIMIT = float(os.getenv('DRAWDOWN_LIMIT', '0.25'))
TRAILING_STOP = os.getenv('TRAILING_STOP', 'true').lower() == 'true'
DYNAMIC_POSITION_SIZING = os.getenv('DYNAMIC_POSITION_SIZING', 'true').lower() == 'true'

def _safe_defaults():
    binance_keys_present = bool(BINANCE_API_KEY) and bool(BINANCE_API_SECRET)
    mode = TRADING_MODE if binance_keys_present else 'testnet'
    paper = PAPER_TRADING if binance_keys_present else True
    return mode, paper

SAFE_TRADING_MODE, SAFE_PAPER_TRADING = _safe_defaults()
