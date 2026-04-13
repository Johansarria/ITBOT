#!/usr/bin/env python3
"""
Archivo de configuración de ejemplo para el Bot de Trading Algorítmico
Renombra este archivo a 'config.py' y ajusta los valores según tus necesidades
"""

import os
from typing import List, Dict

class TradingConfig:
    """Configuración principal del bot de trading"""
    
    # ============================================================================
    # CONFIGURACIÓN BÁSICA
    # ============================================================================
    
    # Capital inicial en USDT
    INITIAL_CAPITAL = 500.0
    
    # Objetivo de rendimiento diario (0.6% = 0.006)
    DAILY_TARGET_RETURN = 0.006
    
    # Máxima pérdida diaria permitida (2% = 0.02)
    MAX_DAILY_LOSS = 0.02
    
    # Tamaño máximo de posición como porcentaje del capital (10% = 0.1)
    MAX_POSITION_SIZE = 0.1
    
    # Monto mínimo por trade en USDT
    MIN_TRADE_AMOUNT = 10.0
    
    # ============================================================================
    # CONFIGURACIÓN DE BINANCE API
    # ============================================================================
    
    # API Keys de Binance (configurar en variables de entorno)
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    
    # Usar testnet (True para pruebas, False para producción)
    USE_TESTNET = True
    
    # Tasa de comisión de Binance (0.1% = 0.001)
    COMMISSION_RATE = 0.001
    
    # Factor de slippage estimado (0.05% = 0.0005)
    SLIPPAGE_FACTOR = 0.0005
    
    # ============================================================================
    # PARES DE TRADING
    # ============================================================================
    
    # Pares principales recomendados para 500 USDT
    PRIMARY_TRADING_PAIRS = [
        'BTCUSDT',   # Bitcoin
        'ETHUSDT',   # Ethereum
        'ADAUSDT',   # Cardano
        'DOTUSDT',   # Polkadot
        'LINKUSDT',  # Chainlink
    ]
    
    # Pares secundarios (menor liquidez pero más oportunidades)
    SECONDARY_TRADING_PAIRS = [
        'LTCUSDT',   # Litecoin
        'BCHUSDT',   # Bitcoin Cash
        'XLMUSDT',   # Stellar
        'EOSUSDT',   # EOS
        'TRXUSDT',   # Tron
    ]
    
    # Todos los pares disponibles
    ALL_TRADING_PAIRS = PRIMARY_TRADING_PAIRS + SECONDARY_TRADING_PAIRS
    
    # ============================================================================
    # PARÁMETROS DE ANÁLISIS TÉCNICO
    # ============================================================================
    
    # Configuración RSI
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    
    # Configuración EMA
    EMA_FAST_PERIOD = 12
    EMA_SLOW_PERIOD = 26
    
    # Configuración MACD
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # Configuración Bollinger Bands
    BB_PERIOD = 20
    BB_STD_DEV = 2.0
    
    # Configuración Stochastic
    STOCH_K_PERIOD = 14
    STOCH_D_PERIOD = 3
    
    # ============================================================================
    # GESTIÓN DE RIESGOS
    # ============================================================================
    
    # Stop Loss como porcentaje (2% = 0.02)
    STOP_LOSS_PERCENTAGE = 0.02
    
    # Take Profit como porcentaje (4% = 0.04)
    TAKE_PROFIT_PERCENTAGE = 0.04
    
    # Máximo número de posiciones simultáneas
    MAX_CONCURRENT_POSITIONS = 3
    
    # Máximo drawdown permitido (10% = 0.1)
    MAX_DRAWDOWN = 0.1
    
    # Factor de Kelly para dimensionamiento de posiciones
    KELLY_FACTOR = 0.25
    
    # ============================================================================
    # CONFIGURACIÓN DE MACHINE LEARNING
    # ============================================================================
    
    # Número de características para el modelo
    ML_FEATURES_COUNT = 20
    
    # Período de entrenamiento en días
    ML_TRAINING_PERIOD = 90
    
    # Umbral de confianza para señales ML (0.7 = 70%)
    ML_CONFIDENCE_THRESHOLD = 0.7
    
    # Reentrenamiento del modelo cada N días
    ML_RETRAIN_INTERVAL = 7
    
    # ============================================================================
    # CONFIGURACIÓN DE BACKTESTING
    # ============================================================================
    
    # Período de backtesting en días
    BACKTEST_PERIOD_DAYS = 365
    
    # Número de simulaciones Monte Carlo
    MONTE_CARLO_SIMULATIONS = 1000
    
    # Período de validación cruzada
    CROSS_VALIDATION_FOLDS = 5
    
    # ============================================================================
    # CONFIGURACIÓN DE OPTIMIZACIÓN
    # ============================================================================
    
    # Número máximo de iteraciones para optimización
    OPTIMIZATION_MAX_ITERATIONS = 100
    
    # Métrica objetivo para optimización
    OPTIMIZATION_TARGET_METRIC = 'sharpe_ratio'  # 'sharpe_ratio', 'total_return', 'win_rate'
    
    # Tolerancia para convergencia
    OPTIMIZATION_TOLERANCE = 1e-6
    
    # ============================================================================
    # CONFIGURACIÓN DE LOGGING
    # ============================================================================
    
    # Nivel de logging
    LOG_LEVEL = 'INFO'  # 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    
    # Archivo de log
    LOG_FILE = 'trading_bot.log'
    
    # Rotación de logs (tamaño máximo en MB)
    LOG_MAX_SIZE_MB = 10
    
    # Número de archivos de backup
    LOG_BACKUP_COUNT = 5
    
    # ============================================================================
    # CONFIGURACIÓN DE NOTIFICACIONES
    # ============================================================================
    
    # Telegram Bot Token (opcional)
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # Telegram Chat ID (opcional)
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Enviar notificaciones por email (configurar SMTP)
    EMAIL_NOTIFICATIONS = False
    SMTP_SERVER = 'smtp.gmail.com'
    SMTP_PORT = 587
    EMAIL_USER = os.getenv('EMAIL_USER', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    EMAIL_RECIPIENT = os.getenv('EMAIL_RECIPIENT', '')
    
    # ============================================================================
    # CONFIGURACIÓN DE BASE DE DATOS
    # ============================================================================
    
    # URL de conexión a la base de datos
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
    
    # Configuración Redis para cache
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    # ============================================================================
    # CONFIGURACIÓN DE MONITOREO
    # ============================================================================
    
    # Intervalo de monitoreo en segundos
    MONITORING_INTERVAL = 60
    
    # Puerto para métricas Prometheus
    PROMETHEUS_PORT = 8000
    
    # Habilitar métricas detalladas
    ENABLE_DETAILED_METRICS = True
    
    # ============================================================================
    # CONFIGURACIÓN AVANZADA
    # ============================================================================
    
    # Modo de ejecución
    EXECUTION_MODE = 'simulation'  # 'simulation', 'paper_trading', 'live_trading'
    
    # Intervalo entre trades en segundos (para evitar spam)
    MIN_TRADE_INTERVAL = 30
    
    # Timeout para órdenes en segundos
    ORDER_TIMEOUT = 60
    
    # Número de reintentos para órdenes fallidas
    ORDER_RETRY_COUNT = 3
    
    # Habilitar trading durante fines de semana
    ENABLE_WEEKEND_TRADING = True
    
    # Horario de trading (UTC)
    TRADING_START_HOUR = 0
    TRADING_END_HOUR = 24
    
    # ============================================================================
    # VALIDACIÓN DE CONFIGURACIÓN
    # ============================================================================
    
    @classmethod
    def validate_config(cls) -> Dict[str, bool]:
        """Validar la configuración"""
        validation_results = {
            'capital_valid': cls.INITIAL_CAPITAL >= 100,
            'target_realistic': 0.001 <= cls.DAILY_TARGET_RETURN <= 0.02,
            'risk_acceptable': cls.MAX_DAILY_LOSS <= 0.05,
            'position_size_safe': cls.MAX_POSITION_SIZE <= 0.2,
            'min_trade_sufficient': cls.MIN_TRADE_AMOUNT >= 10,
            'pairs_available': len(cls.ALL_TRADING_PAIRS) >= 5,
            'api_configured': bool(cls.BINANCE_API_KEY and cls.BINANCE_API_SECRET) or cls.USE_TESTNET
        }
        
        return validation_results
    
    @classmethod
    def get_config_summary(cls) -> str:
        """Obtener resumen de la configuración"""
        validation = cls.validate_config()
        all_valid = all(validation.values())
        
        summary = f"""
🤖 CONFIGURACIÓN DEL BOT DE TRADING
{'='*50}
💰 Capital inicial: ${cls.INITIAL_CAPITAL:,.2f} USDT
🎯 Objetivo diario: {cls.DAILY_TARGET_RETURN:.2%}
🛡️ Máxima pérdida diaria: {cls.MAX_DAILY_LOSS:.2%}
📊 Pares de trading: {len(cls.ALL_TRADING_PAIRS)}
🔧 Modo: {'Testnet' if cls.USE_TESTNET else 'Producción'}

✅ Configuración {'VÁLIDA' if all_valid else 'REQUIERE ATENCIÓN'}
"""
        
        if not all_valid:
            summary += "\n⚠️ Problemas detectados:\n"
            for key, valid in validation.items():
                if not valid:
                    summary += f"  - {key}: ❌\n"
        
        return summary

# ============================================================================
# CONFIGURACIONES PREDEFINIDAS
# ============================================================================

class ConservativeConfig(TradingConfig):
    """Configuración conservadora para principiantes"""
    DAILY_TARGET_RETURN = 0.003  # 0.3%
    MAX_DAILY_LOSS = 0.01        # 1%
    MAX_POSITION_SIZE = 0.05     # 5%
    STOP_LOSS_PERCENTAGE = 0.015 # 1.5%
    MAX_CONCURRENT_POSITIONS = 2

class AggressiveConfig(TradingConfig):
    """Configuración agresiva para traders experimentados"""
    DAILY_TARGET_RETURN = 0.01   # 1%
    MAX_DAILY_LOSS = 0.03        # 3%
    MAX_POSITION_SIZE = 0.15     # 15%
    STOP_LOSS_PERCENTAGE = 0.025 # 2.5%
    MAX_CONCURRENT_POSITIONS = 5

class BalancedConfig(TradingConfig):
    """Configuración balanceada (por defecto)"""
    pass  # Usa los valores por defecto de TradingConfig

# ============================================================================
# FUNCIÓN DE AYUDA
# ============================================================================

def get_config_by_profile(profile: str = 'balanced') -> TradingConfig:
    """Obtener configuración según el perfil de riesgo"""
    profiles = {
        'conservative': ConservativeConfig,
        'balanced': BalancedConfig,
        'aggressive': AggressiveConfig
    }
    
    config_class = profiles.get(profile.lower(), BalancedConfig)
    return config_class()

if __name__ == "__main__":
    # Mostrar resumen de configuración
    print(TradingConfig.get_config_summary())
    
    # Mostrar validación
    validation = TradingConfig.validate_config()
    print("\n🔍 Validación detallada:")
    for key, valid in validation.items():
        status = "✅" if valid else "❌"
        print(f"  {key}: {status}")