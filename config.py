# config.py
import os
from typing import List, Optional, Union
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Manages all application settings using Pydantic.
    It automatically reads from environment variables and/or a .env file.
    """
    # --- MODO DE OPERACIÓN ---
    PRODUCTION_MODE: bool = False

    # --- CONFIGURACIÓN DE API Y TELEGRAM ---
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_CHAT_ID: int
    ADMIN_TELEGRAM_ID: int
    KILL_SWITCH_PASSWORD: Optional[str] = "emergency123"  # Password por defecto
    BINANCE_API_KEY: str
    BINANCE_SECRET_KEY: str

    # --- CONFIGURACIÓN DE SISTEMA DINÁMICO DE PARES ---
    DYNAMIC_PAIR_SELECTION_ENABLED: bool = True      # Habilitar selección dinámica de pares
    DYNAMIC_MAX_PAIRS: int = 8                        # Número máximo de pares a seleccionar
    DYNAMIC_REEVALUATION_INTERVAL_HOURS: int = 24    # Intervalo de re-evaluación en horas
    DYNAMIC_CHECK_INTERVAL_HOURS: int = 2            # Verificación de cambios cada 2 horas
    DYNAMIC_MIN_VOLUME_24H: float = 1000000          # Volumen mínimo 24h para considerar un par
    DYNAMIC_MAX_SPREAD_PCT: float = 0.5              # Spread máximo permitido (%)
    DYNAMIC_MIN_STABILITY_SCORE: float = 0.1         # Score mínimo de estabilidad
    DYNAMIC_ENABLE_SECTOR_DIVERSIFICATION: bool = True  # Diversificación por sectores
    
    # --- CONFIGURACIÓN DE TRADING MULTI-PAR ---
    ASSETS_TO_TRADE: List[str] = Field(default=[
        "BTCUSDT",   # Bitcoin - Par principal (70K datos disponibles)
        "ETHUSDT",   # Ethereum - Segundo más líquido  
        "BNBUSDT",   # Binance Coin - Nativo del exchange
        "ADAUSDT",   # Cardano - Alt coin establecida
        "XRPUSDT",   # Ripple - Diversificación regulatoria
        "SOLUSDT",   # Solana - Ecosystem DeFi/NFT
        "DOTUSDT",   # Polkadot - Interoperabilidad
        "AVAXUSDT"   # Avalanche - Competencia directa ETH
    ])
    INTERVAL: str = "1h"
    MODE: str = "LIVE"

    # --- GESTIÓN DE RIESGO ---
    # Parámetros de riesgo fundamentales para el MVP
    DEFAULT_RISK_PERCENTAGE: float = 1.0  # Mantenido por compatibilidad con lógica existente de riesgo manual.
    MAX_DAILY_OPERATIONS: int = 10  # Límite de operaciones por día, no modificado en esta tarea.
    MAX_TRADE_RISK_PCT: float = 1.0 # Mantenido por si es usado en cálculos de riesgo por operación individuales.

    RISK_PER_TRADE_STOP_LOSS_PCT: float = 2.0
    RISK_PER_TRADE_TAKE_PROFIT_PCT: float = 4.0
    RISK_MAX_EXPOSURE_PCT: float = 30.0
    RISK_MAX_DAILY_DRAWDOWN_PCT: float = 3.0
    RISK_MAX_CONCURRENT_TRADES: int = 10

    # --- MLOPS ---
    ML_MODEL_ID: str = "v2.1.4-beta"
    # Zona horaria para mostrar fecha/hora en Telegram (e.g., "America/Bogota")
    TIMEZONE: str = "America/Bogota"
    # --- UI / Telegram ---
    BANNER_IMAGE_PATH: Optional[str] = None  # Ruta a una imagen (png/jpg) para mostrar en el menú principal
    
    # --- CONFIGURACIÓN ML TRADING OPTIMIZADA PARA 100K DATOS ---
    ML_THRESHOLD_HIGH: float = 0.80       # Umbral para señales fuertes COMPRAR/VENDER (ajustado para 100K)
    ML_THRESHOLD_MEDIUM: float = 0.65     # Umbral para señales moderadas COMPRAR_BAJO/VENDER_ALTO
    ML_THRESHOLD_LOW: float = 0.55        # Umbral mínimo para considerar la señal
    ML_ENABLE_FALLBACK: bool = True       # Habilitar carga fallback desde PKL
    ML_MIN_DATA_POINTS: int = 2000        # Mínimo básico para predicción ML
    ML_OPTIMAL_DATA_POINTS: int = 70273   # CONFIGURADO PARA DATOS REALES (8 años históricos)
    ML_INSTITUTIONAL_DATA_POINTS: int = 70273  # Target con datos reales disponibles
    ML_MAX_DATA_AGE_DAYS: int = 2933      # ~8 años de datos reales desde Binance
    ML_TARGET_ACCURACY: float = 0.617     # Accuracy objetivo con 70K datos reales (61.7%)
    ML_MAX_ANALYSIS_TIME: float = 8.0     # Máximo 8 segundos por análisis
    
    # Estándares institucionales de acertividad
    ML_INSTITUTIONAL_MIN_ACCURACY: float = 0.55      # 55% accuracy mínima institucional
    ML_INSTITUTIONAL_MIN_SHARPE: float = 1.5         # Sharpe ratio mínimo institucional
    ML_INSTITUTIONAL_MAX_DRAWDOWN: float = 0.15      # Máximo 15% drawdown institucional
    ML_INSTITUTIONAL_MIN_HIT_RATE: float = 0.52      # 52% hit rate mínimo institucional

    # --- CONFIGURACIÓN DEL RUNNER ---
    AUTONOMOUS_CYCLE_SECONDS: int = 3600
    RETRY_ON_ERROR_SECONDS: int = 300
    ANALYSIS_INTERVAL_SECONDS: int = 300

    # --- CONFIGURACIÓN DE REDIS ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_DECISION_QUEUE_NAME: str = "trading_decisions_queue"

    # --- CONFIGURACIÓN DE BASE DE DATOS ---
    DB_TYPE: str = "sqlite"
    POSTGRES_HOST: Optional[str] = None
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: Optional[str] = None
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    DATABASE_URL: Optional[str] = None

    # --- OTROS ---
    LOG_LEVEL: str = "INFO"
    LIVE_UNLOCK_FILE_PATH: str = os.path.join(os.getcwd(), "LIVE_UNLOCK.txt")

    # --- COMPATIBILIDAD CON TESTS LEGADOS ---
    # Algunos tests esperan una propiedad TRADING_PAIRS; la mapeamos a ASSETS_TO_TRADE
    @property
    def TRADING_PAIRS(self) -> List[str]:
        return self.ASSETS_TO_TRADE

    @TRADING_PAIRS.setter
    def TRADING_PAIRS(self, pairs: List[str]) -> None:
        self.ASSETS_TO_TRADE = list(pairs)

    @model_validator(mode='after')
    def construct_database_url(self) -> 'Settings':
        if self.DB_TYPE == "postgresql":
            if not all([self.POSTGRES_HOST, self.POSTGRES_DB, self.POSTGRES_USER, self.POSTGRES_PASSWORD]):
                raise ValueError("For PostgreSQL, all POSTGRES_* variables must be set.")
            self.DATABASE_URL = (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        else:
            # Default to a file-based SQLite DB in a persistent storage location
            storage_dir = os.path.join(os.getcwd(), "storage")
            os.makedirs(storage_dir, exist_ok=True)
            self.DATABASE_URL = f"sqlite:///{os.path.join(storage_dir, 'itbot.db')}"
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

# Create a single, globally-accessible settings instance
try:
    settings = Settings()
except Exception as e:
    # Fallback para desarrollo/testing sin .env completo
    import warnings
    warnings.warn(f"Error al cargar settings: {e}. Usando configuración por defecto.")
    # Crear configuración mínima para desarrollo
    settings = None

def get_settings() -> Settings:
    """
    Obtiene la instancia global de configuración, creándola si es necesario.
    """
    global settings
    if settings is None:
        settings = Settings()
    return settings

def reload_settings() -> Settings:
    """
    Recarga la configuración del bot creando una nueva instancia de Settings.
    Esto permite que los cambios en las variables de entorno o .env sean aplicados.
    """
    global settings # Declara que vamos a modificar la variable global settings
    try:
        settings = Settings() # Crea una nueva instancia y la asigna a la global
    except Exception as e:
        import warnings
        warnings.warn(f"Error al recargar settings: {e}")
        if settings is None:
            raise e
    return settings
