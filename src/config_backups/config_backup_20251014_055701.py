# /src/config.py
import os
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# --- Claves de API ---
# Nota: Estas claves deben estar en tu archivo .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GROK_API_KEY = os.getenv("GROK_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

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

TIMEFRAME = "4h"  # Temporalidad para el análisis
CAPITAL_BASE = 500  # USDT total
RISK_PER_TRADE = 0.02  # 2% del capital por operación (por símbolo)

# --- Parámetros del Bot ---
PAPER_TRADING = True  # True para simulación, False para dinero real
KILL_SWITCH_MAX_DRAWDOWN = 0.15  # 15% de drawdown máximo de la cuenta

# --- Configuración de Modelos ---
SPACY_MODEL = "es_core_news_sm"
N_REGIMES = 4  # Número de regímenes de mercado a clasificar

# --- Configuración de Datos ---
DATA_UPDATE_INTERVAL = 3600  # Segundos entre actualizaciones de datos
LOOKBACK_PERIOD = "5y"  # Período histórico para análisis

# --- Configuración de Logging ---
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# --- Configuración de Backtesting ---
INITIAL_CASH = 10000  # Capital inicial para backtesting
COMMISSION = 0.001  # Comisión por operación (0.1%)

# --- Configuración de Alertas ---
ENABLE_ALERTS = True
ALERT_METHODS = ["console", "log"]  # Métodos de alerta disponibles

# --- Configuración de Seguridad ---
MAX_POSITION_SIZE = 0.1  # Máximo 10% del capital en una posición
STOP_LOSS_PERCENTAGE = 0.05  # Stop loss del 5%
TAKE_PROFIT_PERCENTAGE = 0.15  # Take profit del 15%