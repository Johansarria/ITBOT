"""
SICAR Indices Configuration
Configuración especializada para trading de índices bursátiles
Parámetros optimizados para SPY, QQQ, DIA, IWM y otros ETFs principales
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import time
import json
import os

@dataclass
class TechnicalIndicators:
    """Configuración de indicadores técnicos"""
    
    # RSI
    rsi_period: int = 21
    rsi_oversold: float = 32
    rsi_overbought: float = 68
    rsi_extreme_oversold: float = 25
    rsi_extreme_overbought: float = 75
    
    # EMAs
    ema_fast: int = 12
    ema_slow: int = 26
    ema_signal: int = 9
    ema_trend: int = 50
    
    # ATR
    atr_period: int = 21
    atr_multiplier: float = 2.5
    
    # Volume
    volume_sma_period: int = 20
    volume_spike_threshold: float = 1.5
    
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0

@dataclass
class RiskManagement:
    """Configuración de gestión de riesgo"""
    
    # Stop Loss y Take Profit
    stop_loss_atr_multiplier: float = 2.5
    take_profit_atr_multiplier: float = 4.0
    trailing_stop_atr_multiplier: float = 1.5
    
    # Position Sizing
    max_position_size: float = 0.02  # 2% del capital por operación
    max_daily_risk: float = 0.05     # 5% del capital por día
    max_portfolio_risk: float = 0.10  # 10% del capital total
    
    # Drawdown Protection
    max_drawdown_threshold: float = 0.15  # 15%
    daily_loss_limit: float = 500.0       # $500 USD
    
    # Dynamic Position Sizing
    volatility_adjustment: bool = True
    trend_adjustment: bool = True
    correlation_adjustment: bool = True

@dataclass
class MarketSessions:
    """Configuración de sesiones de mercado"""
    
    # Horarios en UTC-5 (Eastern Time)
    pre_market_start: time = time(4, 0)   # 4:00 AM
    pre_market_end: time = time(9, 30)    # 9:30 AM
    
    regular_start: time = time(9, 30)     # 9:30 AM
    regular_end: time = time(16, 0)       # 4:00 PM
    
    after_hours_start: time = time(16, 0) # 4:00 PM
    after_hours_end: time = time(20, 0)   # 8:00 PM
    
    # Configuración de trading por sesión
    trade_pre_market: bool = False
    trade_regular_hours: bool = True
    trade_after_hours: bool = False
    
    # Días de trading
    trading_days: List[int] = field(default_factory=lambda: [0, 1, 2, 3, 4])  # Lun-Vie

@dataclass
class VolatilityFilters:
    """Filtros de volatilidad"""
    
    # VIX Filters
    vix_enabled: bool = True
    vix_max_threshold: float = 30.0
    vix_extreme_threshold: float = 40.0
    
    # ATR Volatility
    atr_volatility_enabled: bool = True
    atr_volatility_threshold: float = 2.0
    atr_lookback_period: int = 20
    
    # Market Regime Detection
    regime_detection_enabled: bool = True
    trend_strength_threshold: float = 0.6
    volatility_regime_threshold: float = 1.5

@dataclass
class SeasonalAdjustments:
    """Ajustes estacionales"""
    
    # Protección Octubre (October Effect)
    october_protection: bool = True
    october_position_reduction: float = 0.5  # Reducir posiciones al 50%
    october_stop_tighter: float = 1.5        # Stop loss más ajustado
    
    # Protección Septiembre
    september_protection: bool = True
    september_position_reduction: float = 0.7  # Reducir posiciones al 70%
    
    # Fin de año (December)
    december_adjustment: bool = True
    december_position_increase: float = 1.2   # Incrementar posiciones 20%
    
    # Earnings Season
    earnings_protection: bool = True
    earnings_position_reduction: float = 0.6

@dataclass
class IndexSpecificConfig:
    """Configuración específica por índice"""
    
    symbol: str
    name: str
    
    # Parámetros técnicos específicos
    technical_indicators: TechnicalIndicators
    risk_management: RiskManagement
    volatility_filters: VolatilityFilters
    
    # Características del índice
    average_daily_volume: int
    average_spread: float
    volatility_factor: float
    correlation_spy: float
    
    # Timeframes preferidos
    preferred_timeframes: List[str] = field(default_factory=lambda: ['1h', '4h', '1d'])
    
    # Estrategias recomendadas
    recommended_strategies: List[str] = field(default_factory=list)

class IndicesConfigManager:
    """Gestor de configuraciones para índices"""
    
    def __init__(self):
        self.configs = {}
        self._initialize_default_configs()
    
    def _initialize_default_configs(self):
        """Inicializa configuraciones por defecto para cada índice"""
        
        # SPY - S&P 500 ETF (Configuración base)
        spy_config = IndexSpecificConfig(
            symbol='SPY',
            name='SPDR S&P 500 ETF',
            technical_indicators=TechnicalIndicators(),
            risk_management=RiskManagement(),
            volatility_filters=VolatilityFilters(),
            average_daily_volume=80000000,
            average_spread=0.01,
            volatility_factor=1.0,
            correlation_spy=1.0,
            recommended_strategies=['momentum', 'mean_reversion', 'trend_following']
        )
        
        # QQQ - NASDAQ 100 ETF (Más volátil)
        qqq_indicators = TechnicalIndicators(
            rsi_period=18,  # Más sensible para tech
            rsi_oversold=28,
            rsi_overbought=72,
            atr_multiplier=3.0  # Mayor volatilidad
        )
        
        qqq_risk = RiskManagement(
            stop_loss_atr_multiplier=3.0,
            take_profit_atr_multiplier=5.0,
            max_position_size=0.015,  # Menor tamaño por mayor volatilidad
            daily_loss_limit=400.0
        )
        
        qqq_volatility = VolatilityFilters(
            vix_max_threshold=35.0,  # Más permisivo para tech
            atr_volatility_threshold=2.5
        )
        
        qqq_config = IndexSpecificConfig(
            symbol='QQQ',
            name='Invesco QQQ Trust',
            technical_indicators=qqq_indicators,
            risk_management=qqq_risk,
            volatility_filters=qqq_volatility,
            average_daily_volume=45000000,
            average_spread=0.01,
            volatility_factor=1.3,
            correlation_spy=0.85,
            recommended_strategies=['momentum', 'breakout', 'tech_rotation']
        )
        
        # DIA - Dow Jones ETF (Menos volátil)
        dia_indicators = TechnicalIndicators(
            rsi_period=24,  # Menos sensible
            rsi_oversold=35,
            rsi_overbought=65,
            atr_multiplier=2.0
        )
        
        dia_risk = RiskManagement(
            stop_loss_atr_multiplier=2.0,
            take_profit_atr_multiplier=3.5,
            max_position_size=0.025,  # Mayor tamaño por menor volatilidad
            daily_loss_limit=600.0
        )
        
        dia_config = IndexSpecificConfig(
            symbol='DIA',
            name='SPDR Dow Jones Industrial Average ETF',
            technical_indicators=dia_indicators,
            risk_management=dia_risk,
            volatility_filters=VolatilityFilters(vix_max_threshold=25.0),
            average_daily_volume=4000000,
            average_spread=0.02,
            volatility_factor=0.8,
            correlation_spy=0.92,
            recommended_strategies=['mean_reversion', 'value_rotation', 'dividend_momentum']
        )
        
        # IWM - Russell 2000 ETF (Small caps, muy volátil)
        iwm_indicators = TechnicalIndicators(
            rsi_period=16,  # Muy sensible para small caps
            rsi_oversold=25,
            rsi_overbought=75,
            atr_multiplier=3.5
        )
        
        iwm_risk = RiskManagement(
            stop_loss_atr_multiplier=3.5,
            take_profit_atr_multiplier=6.0,
            max_position_size=0.01,   # Menor tamaño por alta volatilidad
            daily_loss_limit=300.0
        )
        
        iwm_volatility = VolatilityFilters(
            vix_max_threshold=40.0,   # Muy permisivo
            atr_volatility_threshold=3.0
        )
        
        iwm_config = IndexSpecificConfig(
            symbol='IWM',
            name='iShares Russell 2000 ETF',
            technical_indicators=iwm_indicators,
            risk_management=iwm_risk,
            volatility_filters=iwm_volatility,
            average_daily_volume=25000000,
            average_spread=0.03,
            volatility_factor=1.6,
            correlation_spy=0.75,
            recommended_strategies=['momentum', 'small_cap_rotation', 'volatility_breakout']
        )
        
        # Guardar configuraciones
        self.configs = {
            'SPY': spy_config,
            'QQQ': qqq_config,
            'DIA': dia_config,
            'IWM': iwm_config
        }
        
        # Agregar configuraciones adicionales
        self._add_additional_etfs()
    
    def _add_additional_etfs(self):
        """Agrega configuraciones para ETFs adicionales"""
        
        # VTI - Total Stock Market
        vti_config = IndexSpecificConfig(
            symbol='VTI',
            name='Vanguard Total Stock Market ETF',
            technical_indicators=TechnicalIndicators(rsi_period=22),
            risk_management=RiskManagement(max_position_size=0.02),
            volatility_filters=VolatilityFilters(),
            average_daily_volume=5000000,
            average_spread=0.01,
            volatility_factor=0.95,
            correlation_spy=0.98,
            recommended_strategies=['broad_market_momentum', 'trend_following']
        )
        
        # VOO - S&P 500 (Vanguard)
        voo_config = IndexSpecificConfig(
            symbol='VOO',
            name='Vanguard S&P 500 ETF',
            technical_indicators=TechnicalIndicators(),
            risk_management=RiskManagement(),
            volatility_filters=VolatilityFilters(),
            average_daily_volume=6000000,
            average_spread=0.01,
            volatility_factor=1.0,
            correlation_spy=0.99,
            recommended_strategies=['momentum', 'mean_reversion']
        )
        
        self.configs.update({
            'VTI': vti_config,
            'VOO': voo_config
        })
    
    def get_config(self, symbol: str) -> Optional[IndexSpecificConfig]:
        """Obtiene configuración para un símbolo específico"""
        return self.configs.get(symbol.upper())
    
    def get_all_symbols(self) -> List[str]:
        """Retorna lista de todos los símbolos configurados"""
        return list(self.configs.keys())
    
    def add_custom_config(self, config: IndexSpecificConfig):
        """Agrega una configuración personalizada"""
        self.configs[config.symbol.upper()] = config
    
    def save_config(self, filepath: str):
        """Guarda configuraciones a archivo JSON"""
        config_dict = {}
        for symbol, config in self.configs.items():
            config_dict[symbol] = {
                'symbol': config.symbol,
                'name': config.name,
                'technical_indicators': config.technical_indicators.__dict__,
                'risk_management': config.risk_management.__dict__,
                'volatility_filters': config.volatility_filters.__dict__,
                'average_daily_volume': config.average_daily_volume,
                'average_spread': config.average_spread,
                'volatility_factor': config.volatility_factor,
                'correlation_spy': config.correlation_spy,
                'preferred_timeframes': config.preferred_timeframes,
                'recommended_strategies': config.recommended_strategies
            }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=2, default=str)
    
    def load_config(self, filepath: str):
        """Carga configuraciones desde archivo JSON"""
        if not os.path.exists(filepath):
            return
        
        with open(filepath, 'r') as f:
            config_dict = json.load(f)
        
        for symbol, data in config_dict.items():
            # Reconstruir objetos dataclass
            technical_indicators = TechnicalIndicators(**data['technical_indicators'])
            risk_management = RiskManagement(**data['risk_management'])
            volatility_filters = VolatilityFilters(**data['volatility_filters'])
            
            config = IndexSpecificConfig(
                symbol=data['symbol'],
                name=data['name'],
                technical_indicators=technical_indicators,
                risk_management=risk_management,
                volatility_filters=volatility_filters,
                average_daily_volume=data['average_daily_volume'],
                average_spread=data['average_spread'],
                volatility_factor=data['volatility_factor'],
                correlation_spy=data['correlation_spy'],
                preferred_timeframes=data['preferred_timeframes'],
                recommended_strategies=data['recommended_strategies']
            )
            
            self.configs[symbol] = config

@dataclass
class GlobalIndicesConfig:
    """Configuración global para el sistema de índices"""
    
    # Configuración de mercado
    market_sessions: MarketSessions = field(default_factory=MarketSessions)
    seasonal_adjustments: SeasonalAdjustments = field(default_factory=SeasonalAdjustments)
    
    # Configuración de datos
    default_timeframe: str = '1h'
    data_lookback_days: int = 252  # 1 año de trading
    
    # Configuración de backtesting
    initial_capital: float = 10000.0
    commission_per_trade: float = 1.0
    slippage_bps: float = 2.0  # 2 basis points
    
    # Configuración de alertas
    enable_alerts: bool = True
    alert_methods: List[str] = field(default_factory=lambda: ['email', 'webhook'])
    
    # Configuración de logging
    log_level: str = 'INFO'
    log_trades: bool = True
    log_signals: bool = True
    
    # Configuración de performance
    benchmark_symbol: str = 'SPY'
    performance_metrics: List[str] = field(default_factory=lambda: [
        'total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'profit_factor'
    ])

# Instancia global del gestor de configuraciones
config_manager = IndicesConfigManager()

# Configuración global
global_config = GlobalIndicesConfig()

def get_index_config(symbol: str) -> Optional[IndexSpecificConfig]:
    """Función de utilidad para obtener configuración de un índice"""
    return config_manager.get_config(symbol)

def get_supported_indices() -> List[str]:
    """Función de utilidad para obtener lista de índices soportados"""
    return config_manager.get_all_symbols()

def create_custom_index_config(
    symbol: str,
    name: str,
    volatility_factor: float = 1.0,
    correlation_spy: float = 0.8,
    **kwargs
) -> IndexSpecificConfig:
    """
    Crea una configuración personalizada para un nuevo índice
    
    Args:
        symbol: Símbolo del índice
        name: Nombre descriptivo
        volatility_factor: Factor de volatilidad relativo a SPY
        correlation_spy: Correlación con SPY
        **kwargs: Parámetros adicionales
    
    Returns:
        Configuración personalizada
    """
    
    # Ajustar parámetros basados en volatilidad
    base_indicators = TechnicalIndicators()
    base_risk = RiskManagement()
    base_volatility = VolatilityFilters()
    
    if volatility_factor > 1.2:  # Alta volatilidad
        base_indicators.atr_multiplier *= volatility_factor
        base_risk.stop_loss_atr_multiplier *= volatility_factor
        base_risk.max_position_size *= 0.8
        base_volatility.vix_max_threshold *= 1.2
    elif volatility_factor < 0.8:  # Baja volatilidad
        base_indicators.atr_multiplier *= 0.8
        base_risk.stop_loss_atr_multiplier *= 0.8
        base_risk.max_position_size *= 1.2
        base_volatility.vix_max_threshold *= 0.8
    
    config = IndexSpecificConfig(
        symbol=symbol.upper(),
        name=name,
        technical_indicators=base_indicators,
        risk_management=base_risk,
        volatility_filters=base_volatility,
        average_daily_volume=kwargs.get('average_daily_volume', 1000000),
        average_spread=kwargs.get('average_spread', 0.02),
        volatility_factor=volatility_factor,
        correlation_spy=correlation_spy,
        preferred_timeframes=kwargs.get('preferred_timeframes', ['1h', '1d']),
        recommended_strategies=kwargs.get('recommended_strategies', ['momentum'])
    )
    
    return config

if __name__ == "__main__":
    # Ejemplo de uso
    print("Configuraciones de índices disponibles:")
    for symbol in get_supported_indices():
        config = get_index_config(symbol)
        print(f"{symbol}: {config.name}")
        print(f"  - Volatilidad: {config.volatility_factor}")
        print(f"  - Correlación SPY: {config.correlation_spy}")
        print(f"  - Estrategias: {config.recommended_strategies}")
        print()
    
    # Guardar configuraciones
    config_manager.save_config('indices_config.json')
    print("Configuraciones guardadas en indices_config.json")