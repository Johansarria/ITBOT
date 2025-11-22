"""
SICAR Indices Configuration
Configuraciones específicas para trading de índices
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum

class IndexType(Enum):
    """Tipos de índices"""
    BROAD_MARKET = "broad_market"
    SECTOR = "sector"
    STYLE = "style"
    INTERNATIONAL = "international"
    COMMODITY = "commodity"

class MarketCap(Enum):
    """Capitalización de mercado"""
    LARGE_CAP = "large_cap"
    MID_CAP = "mid_cap"
    SMALL_CAP = "small_cap"
    MIXED = "mixed"

@dataclass
class IndexSpecificConfig:
    """Configuración específica para un índice"""
    symbol: str
    name: str
    index_type: IndexType
    market_cap: MarketCap
    
    # Parámetros de trading
    min_volume: int = 1000000
    tick_size: float = 0.01
    
    # Parámetros técnicos
    volatility_lookback: int = 20
    trend_period: int = 50
    momentum_period: int = 14
    
    # Horarios de trading
    regular_hours_start: str = "09:30"
    regular_hours_end: str = "16:00"
    extended_hours: bool = True
    
    # Parámetros de riesgo
    max_position_size: float = 0.2  # 20% del portfolio
    stop_loss_pct: float = 0.02     # 2%
    take_profit_pct: float = 0.04   # 4%
    
    # Filtros específicos
    earnings_filter: bool = True
    dividend_filter: bool = True
    options_expiry_filter: bool = True

class IndicesConfig:
    """
    Configuración principal para índices
    """
    
    def __init__(self):
        self.configs = self._initialize_configs()
    
    def _initialize_configs(self) -> Dict[str, IndexSpecificConfig]:
        """Inicializar configuraciones por defecto"""
        configs = {}
        
        # SPY - S&P 500 ETF
        configs['SPY'] = IndexSpecificConfig(
            symbol='SPY',
            name='SPDR S&P 500 ETF',
            index_type=IndexType.BROAD_MARKET,
            market_cap=MarketCap.LARGE_CAP,
            min_volume=50000000,
            volatility_lookback=20,
            trend_period=50,
            momentum_period=14,
            max_position_size=0.25,
            stop_loss_pct=0.015,
            take_profit_pct=0.03
        )
        
        # QQQ - Nasdaq 100 ETF
        configs['QQQ'] = IndexSpecificConfig(
            symbol='QQQ',
            name='Invesco QQQ ETF',
            index_type=IndexType.SECTOR,
            market_cap=MarketCap.LARGE_CAP,
            min_volume=30000000,
            volatility_lookback=15,
            trend_period=40,
            momentum_period=12,
            max_position_size=0.2,
            stop_loss_pct=0.02,
            take_profit_pct=0.04
        )
        
        # IWM - Russell 2000 ETF
        configs['IWM'] = IndexSpecificConfig(
            symbol='IWM',
            name='iShares Russell 2000 ETF',
            index_type=IndexType.STYLE,
            market_cap=MarketCap.SMALL_CAP,
            min_volume=20000000,
            volatility_lookback=25,
            trend_period=60,
            momentum_period=16,
            max_position_size=0.15,
            stop_loss_pct=0.025,
            take_profit_pct=0.05
        )
        
        # DIA - Dow Jones ETF
        configs['DIA'] = IndexSpecificConfig(
            symbol='DIA',
            name='SPDR Dow Jones ETF',
            index_type=IndexType.BROAD_MARKET,
            market_cap=MarketCap.LARGE_CAP,
            min_volume=5000000,
            volatility_lookback=20,
            trend_period=50,
            momentum_period=14,
            max_position_size=0.2,
            stop_loss_pct=0.015,
            take_profit_pct=0.03
        )
        
        # VTI - Total Stock Market ETF
        configs['VTI'] = IndexSpecificConfig(
            symbol='VTI',
            name='Vanguard Total Stock Market ETF',
            index_type=IndexType.BROAD_MARKET,
            market_cap=MarketCap.MIXED,
            min_volume=3000000,
            volatility_lookback=20,
            trend_period=50,
            momentum_period=14,
            max_position_size=0.25,
            stop_loss_pct=0.015,
            take_profit_pct=0.03
        )
        
        return configs
    
    def get_config(self, symbol: str) -> Optional[IndexSpecificConfig]:
        """Obtener configuración para un símbolo"""
        return self.configs.get(symbol.upper())
    
    def get_all_symbols(self) -> List[str]:
        """Obtener todos los símbolos configurados"""
        return list(self.configs.keys())
    
    def get_symbols_by_type(self, index_type: IndexType) -> List[str]:
        """Obtener símbolos por tipo de índice"""
        return [symbol for symbol, config in self.configs.items() 
                if config.index_type == index_type]
    
    def get_symbols_by_market_cap(self, market_cap: MarketCap) -> List[str]:
        """Obtener símbolos por capitalización"""
        return [symbol for symbol, config in self.configs.items() 
                if config.market_cap == market_cap]
    
    def add_custom_config(self, config: IndexSpecificConfig):
        """Agregar configuración personalizada"""
        self.configs[config.symbol.upper()] = config
    
    def update_config(self, symbol: str, **kwargs):
        """Actualizar configuración existente"""
        if symbol.upper() in self.configs:
            config = self.configs[symbol.upper()]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def get_trading_universe(self) -> List[str]:
        """Obtener universo de trading (símbolos activos)"""
        # Por ahora retorna todos, pero puede filtrar por volumen, etc.
        return self.get_all_symbols()
    
    def validate_config(self, symbol: str) -> bool:
        """Validar configuración de un símbolo"""
        config = self.get_config(symbol)
        if not config:
            return False
        
        # Validaciones básicas
        validations = [
            config.min_volume > 0,
            config.tick_size > 0,
            0 < config.max_position_size <= 1,
            0 < config.stop_loss_pct < 1,
            0 < config.take_profit_pct < 1,
            config.volatility_lookback > 0,
            config.trend_period > 0,
            config.momentum_period > 0
        ]
        
        return all(validations)