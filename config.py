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
    # Si es True, antes de confirmar se pedirá contraseña adicional (por defecto False para compatibilidad con tests)
    KILL_SWITCH_REQUIRE_PASSWORD: bool = False
    BINANCE_API_KEY: str
    BINANCE_SECRET_KEY: str
    # Usar Testnet de Binance para Spot/Futuros (solo para pruebas en caliente sin riesgo real)
    BINANCE_USE_TESTNET_SPOT: bool = False
    BINANCE_USE_TESTNET_FUTURES: bool = False

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
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT"
    ])
    INTERVAL: str = "1h"
    MODE: str = "LIVE"

    # --- EJECUCIÓN / INTEGRACIONES ---
    # Objetivo de ejecución: BINANCE (por defecto) o CTRADER
    EXECUTION_TARGET: str = "BINANCE"
    # ID de cuenta cTrader (opcional, para direccionar órdenes)
    CTRADER_ACCOUNT_ID: Optional[str] = None
    # URL base del Web API (usado por procesos internos p.ej. worker/listener)
    WEB_API_BASE_URL: str = os.getenv("WEB_API_BASE_URL", "http://web:8080")
    # Secreto interno para autenticar llamadas servidor-servidor al Web API
    INTERNAL_API_SECRET: Optional[str] = os.getenv("INTERNAL_API_SECRET")

    # --- GESTIÓN DE RIESGO ---
    # Parámetros de riesgo fundamentales para el MVP
    DEFAULT_RISK_PERCENTAGE: float = 1.0  # Mantenido por compatibilidad con lógica existente de riesgo manual.
    MAX_DAILY_OPERATIONS: int = 10  # Límite de operaciones por día, no modificado en esta tarea.
    MAX_TRADE_RISK_PCT: float = 1.0 # Mantenido por si es usado en cálculos de riesgo por operación individuales.

    RISK_PER_TRADE_STOP_LOSS_PCT: float = 2.0
    RISK_PER_TRADE_TAKE_PROFIT_PCT: float = 4.0
    RISK_MAX_EXPOSURE_PCT: float = 30.0
    RISK_MAX_DAILY_DRAWDOWN_PCT: float = 3.0
    RISK_MAX_CONCURRENT_TRADES: int = 2
    # Límites opcionales por símbolo (cuando no son None se aplican en verificaciones)
    RISK_MAX_PER_SYMBOL_TRADES: Optional[int] = None
    RISK_MAX_PER_SYMBOL_EXPOSURE_PCT: Optional[float] = None

    # --- BACKTESTING ---
    BACKTEST_AVERAGE_SPREAD_PCT: float = 0.02 # Spread porcentual promedio para simular en backtests

    # --- COST-AWARE TRADING (RAW SPREAD + COMMISSION MODEL) ---
    # Modelo de costes: 'SIMPLE' (solo % de fee) o 'RAW' (spread + comisión por lote)
    COST_MODEL: str = "RAW"
    # Comisión por lote estándar (ej. 3.5 USD por 1 lote de 100k)
    COMMISSION_PER_LOT: float = 3.5
    # Tamaño del contrato/lote. Para cripto, 1 lote = 1 unidad de la base (e.g., 1 BTC).
    CONTRACT_SIZE: float = 1.0
    # Spread porcentual máximo para abortar una operación antes de ejecutarla.
    MAX_SPREAD_PERCENTAGE: float = 0.07
    # Ratio mínimo de Ganancia/Coste. (e.g., 3.0 -> la ganancia esperada debe ser 3x el coste)
    PROFIT_TO_COST_RATIO: float = 3.0

    # --- MODO MICRO-TRADE (opcional) ---
    # Permite ejecutar pruebas reales con montos muy pequeños usando Futuros USDT-M con apalancamiento controlado.
    ENABLE_MICRO_TRADE: bool = False
    MICRO_TRADE_USE_FUTURES: bool = True
    MICRO_TRADE_LEVERAGE: int = 5
    MICRO_TRADE_MAX_USDT: float = 5.0
    # Limita qué símbolos pueden usarse en micro-trade. Incluye pares con minNotional bajo.
    MICRO_TRADE_ALLOWED_SYMBOLS: List[str] = Field(default=[
    # Restringido a símbolos core para reducir churn y mejorar estabilidad
    "BTCUSDT", "ETHUSDT", "SOLUSDT"
    ])

    # --- MLOPS ---
    ML_MODEL_ID: str = "v2.1.4-beta"
    # Zona horaria para mostrar fecha/hora en Telegram (e.g., "America/Bogota")
    TIMEZONE: str = "America/Bogota"
    # --- UI / Telegram ---
    BANNER_IMAGE_PATH: Optional[str] = None  # Ruta a una imagen (png/jpg) para mostrar en el menú principal
    
    # --- CONFIGURACIÓN ML TRADING OPTIMIZADA PARA 100K DATOS ---
    ML_THRESHOLD_HIGH: float = 0.71       # Umbral para señales fuertes COMPRAR/VENDER (percentil 95)
    ML_THRESHOLD_MEDIUM: float = 0.69     # Umbral para señales moderadas COMPRAR_BAJO/VENDER_ALTO (percentil 90)
    ML_THRESHOLD_LOW: float = 0.60        # Umbral mínimo para considerar la señal (optimizado para mayor selectividad)
    ML_ENABLE_FALLBACK: bool = True       # Habilitar carga fallback desde PKL
    ML_MIN_DATA_POINTS: int = 50          # Mínimo básico para predicción ML (alineado al README y a entornos con menos datos)
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

    # --- UMBRALES DINÁMICOS (opcional) ---
    ML_DYNAMIC_THRESHOLDS: bool = True               # Si True, ajusta umbrales con distribución reciente
    ML_DYNAMIC_WINDOW_HOURS: int = 24                # Ventana de cálculo
    ML_DYNAMIC_HIGH_MIN: float = 0.71                # Límite inferior para high (igual al base por defecto)
    ML_DYNAMIC_HIGH_MAX: float = 0.90                # Límite superior para high
    ML_DYNAMIC_MEDIUM_MIN: float = 0.71              # Igual al high para desactivar moderadas por defecto
    ML_DYNAMIC_MEDIUM_MAX: float = 0.85              # Límite superior para medium

    # --- POLÍTICAS DE EJECUCIÓN ML ---
    # Si False, no se ejecutan señales moderadas (COMPRAR_BAJO / VENDER_ALTO)
    ML_ENABLE_MODERATE_SIGNALS: bool = False
    # Exigir confluencia técnica básica (MACD y ADX) para habilitar COMPRAR/VENDER de ML
    ML_REQUIRE_TECH_CONFLUENCE: bool = True
    ML_CONFLUENCE_ADX_MIN: float = 25.0

    # --- CONFIGURACIÓN DEL RUNNER ---
    AUTONOMOUS_CYCLE_SECONDS: int = 3600
    RETRY_ON_ERROR_SECONDS: int = 300
    ANALYSIS_INTERVAL_SECONDS: int = 180
    # Gestión de posición (autonomous manager)
    TRAIL_ACTIVATE_PCT: float = 0.8      # Activar trailing al +0.8%
    TRAIL_DISTANCE_PCT: float = 0.4      # Distancia del trailing
    TIME_STOP_MINUTES: int = 180         # Cierre forzado por tiempo (mantener en 180 como solicitado)
    BREAK_EVEN_ACTIVATE_PCT: float = 0.5 # Activar break-even a partir de +0.5%
    # Umbral mínimo de ROI sobre margen para abrir (p.ej., 13% sobre margen)
    MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT: float = 18.0
    # --- V3 Dinámico ---
    ENABLE_V3_DYNAMIC_CONTROLLER: bool = True

    # --- AUTONOMÍA: ejecución y gestión avanzada ---
    # WorkingType para triggers de SL/TP en Futuros: 'CONTRACT_PRICE' o 'MARK_PRICE'
    # SL por Mark Price para mejor activación en wicks; TP por Contract Price
    FUTURES_SL_WORKING_TYPE: str = "MARK_PRICE"
    FUTURES_TP_WORKING_TYPE: str = "CONTRACT_PRICE"
    # Filtrar por funding absoluto máximo permitido (en %). Ej: 0.05 -> 0.05%
    FUTURES_MAX_ABS_FUNDING_PCT: float = 0.05
    # Cooldown de reentrada por símbolo (minutos)
    REENTRY_COOLDOWN_MINUTES: int = 60
    # Entrada maker-limit cuando el spread es muy bajo (para reducir fees)
    ENABLE_MAKER_ENTRY: bool = True
    LIMIT_MAKER_SPREAD_MAX_PCT: float = 0.02
    # Offset pasivo en ticks para aumentar la aceptación de órdenes Post Only (GTX)
    LIMIT_MAKER_OFFSET_TICKS: int = 2
    LIMIT_MAKER_MAX_RETRIES: int = 2
    LIMIT_MAKER_RETRY_DELAY_MS: int = 150
    # Logging de eventos a un JSONL local
    EVENT_LOG_PATH: Optional[str] = os.path.join(os.getcwd(), "storage", "trade_events.jsonl")
    # Bloqueo diario: lista de símbolos a pausar (coma-separada) para el día
    DAILY_BLOCKLIST: Optional[str] = "XRPUSDT,BNBUSDT"

    # --- AUTONOMÍA + ML ---
    AUTONOMY_USE_ML: bool = True
    ML_AUTONOMY_INTERVAL: str = "5m"
    ML_AUTONOMY_LIMIT: int = 300
    # Aceptar decisiones fuertes siempre; moderadas según flag global ML_ENABLE_MODERATE_SIGNALS
    ML_MIN_SCORE_FOR_ENTRY: float = 60.0  # score = prob*100
    ML_SIDE_OVERRIDE: bool = True

    # --- RIESGO: Circuit breaker diario ---
    # Límite de pérdida diaria. Si DAILY_MAX_LOSS_PCT > 0, se calcula sobre el baseline dinámico (futures_baseline.json).
    # También puede fijarse un límite absoluto en USDT con DAILY_MAX_LOSS_USDT. Se usa el mayor de ambos si ambos > 0.
    DAILY_MAX_LOSS_PCT: float = 1.5
    DAILY_MAX_LOSS_USDT: float = 0.0
    # Bloqueo de ganancias diario: si se alcanza o supera, no se abren nuevas entradas (solo gestionar abiertas)
    DAILY_PROFIT_LOCK_PCT: float = 0.8
    DAILY_PROFIT_LOCK_USDT: float = 0.0

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
                import warnings
                warnings.warn("Configuración PostgreSQL incompleta; haciendo fallback a SQLite por defecto.")
                self.DB_TYPE = "sqlite"
            else:
                self.DATABASE_URL = (
                    f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
                    f"{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
                )

        if self.DB_TYPE != "postgresql":
            # Default to a file-based SQLite DB in a persistent storage location
            storage_dir = os.path.join(os.getcwd(), "storage")
            os.makedirs(storage_dir, exist_ok=True)
            self.DATABASE_URL = f"sqlite:///{os.path.join(storage_dir, 'itbot.db')}"
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

# Create a single, globally-accessible settings instance
def _create_minimal_settings() -> "Settings":
    """Crea una instancia Settings con valores dummy seguros para entornos sin .env.
    Mantiene SQLite por defecto y evita requisitos de PostgreSQL.
    """
    return Settings(  # type: ignore[call-arg]
        TELEGRAM_BOT_TOKEN="DUMMY",
        TELEGRAM_CHAT_ID=0,
        ADMIN_TELEGRAM_ID=0,
        BINANCE_API_KEY="DUMMY",
        BINANCE_SECRET_KEY="DUMMY",
    )

try:
    settings = Settings()  # type: ignore[call-arg]
except Exception as e:
    # Fallback para desarrollo/testing sin .env completo
    import warnings
    warnings.warn(f"Error al cargar settings: {e}. Usando configuración mínima por defecto.")
    # Crear configuración mínima para desarrollo
    try:
        settings = _create_minimal_settings()
    except Exception as e2:
        warnings.warn(f"No se pudo crear configuración mínima: {e2}")
        settings = None

def get_settings() -> Settings:
    """
    Obtiene la instancia global de configuración, creándola si es necesario.
    """
    global settings
    if settings is None:
        try:
            settings = Settings()  # type: ignore[call-arg]
        except Exception:
            # Como último recurso, usa mínimos dummy
            settings = _create_minimal_settings()
    return settings

def reload_settings() -> Settings:
    """
    Recarga la configuración del bot creando una nueva instancia de Settings.
    Esto permite que los cambios en las variables de entorno o .env sean aplicados.
    """
    global settings # Declara que vamos a modificar la variable global settings
    try:
        settings = Settings()  # type: ignore[call-arg] # Crea una nueva instancia y la asigna a la global
    except Exception as e:
        import warnings
        warnings.warn(f"Error al recargar settings: {e}. Aplicando configuración mínima por defecto.")
        try:
            settings = _create_minimal_settings()
        except Exception:
            if settings is None:
                raise e
    return settings
