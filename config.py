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
    BINANCE_API_KEY: str
    BINANCE_SECRET_KEY: str

    # --- CONFIGURACIÓN DE TRADING ---
    ASSETS_TO_TRADE: List[str] = Field(default=["BTCUSDT"])
    INTERVAL: str = "1h"
    MODE: str = "live"

    # --- GESTIÓN DE RIESGO ---
    DEFAULT_RISK_PERCENTAGE: float = 1.0
    TAKE_PROFIT_PERCENTAGE: float = 3.0
    STOP_LOSS_PERCENTAGE: float = 1.5
    MAX_DAILY_OPERATIONS: int = 10
    MAX_DAILY_LOSS_PCT: float = 5.0
    MAX_TRADE_RISK_PCT: float = 1.0
    MAX_CONCURRENT_POSITIONS: int = 3
    MAX_TOTAL_EXPOSURE_PCT: float = 50.0

    # --- MLOPS ---
    ML_MODEL_ID: str = "v2.1.4-beta"

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
settings = Settings()

def reload_settings() -> Settings:
    """
    Recarga la configuración del bot creando una nueva instancia de Settings.
    Esto permite que los cambios en las variables de entorno o .env sean aplicados.
    """
    global settings # Declara que vamos a modificar la variable global settings
    settings = Settings() # Crea una nueva instancia y la asigna a la global
    return settings
