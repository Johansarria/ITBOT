"""
SICAR - Adaptador de Estrategias para Índices
============================================

Este módulo adapta las estrategias existentes de criptomonedas para operar con índices de ETFs.
Incluye conversión de parámetros, ajustes de horarios de mercado, y optimización específica para índices.

Autor: SICAR Team
Fecha: Enero 2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import json
import logging
from datetime import datetime, time, timedelta
import pandas as pd
import numpy as np

# Importar módulos SICAR existentes
from .indices_config import IndexType, MarketCap, IndicesConfig
from .vix_analyzer import VIXAnalyzer, VIXLevel
from .advanced_market_hours import AdvancedMarketHours, MarketType, SessionType
from .indices_parameters_calibrator import IndicesParametersCalibrator

class StrategyType(Enum):
    """Tipos de estrategias disponibles"""
    SIMPLE_ROI = "simple_roi"
    BALANCED_ROI = "balanced_roi"
    OPTIMIZED_ROI = "optimized_roi"
    ADVANCED_ROI = "advanced_roi"
    FINAL_OPTIMIZED = "final_optimized"
    ULTIMATE_SICAR = "ultimate_sicar"
    AGGRESSIVE_MOMENTUM = "aggressive_momentum"
    ARBITRAGE = "arbitrage"
    MARKET_MAKING = "market_making"
    ENSEMBLE = "ensemble"

class TradingSession(Enum):
    """Sesiones de trading para índices"""
    PRE_MARKET = "pre_market"
    REGULAR = "regular"
    AFTER_HOURS = "after_hours"
    EXTENDED = "extended"

class RiskProfile(Enum):
    """Perfiles de riesgo adaptados para índices"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    INSTITUTIONAL = "institutional"

@dataclass
class StrategyParameters:
    """Parámetros de estrategia adaptados para índices"""
    # Parámetros básicos
    strategy_type: StrategyType
    target_symbols: List[str] = field(default_factory=list)
    timeframes: List[str] = field(default_factory=list)
    
    # Gestión de riesgo
    max_position_size: float = 0.25  # Reducido para índices
    stop_loss_pct: float = 0.02      # 2% para índices vs 5% crypto
    take_profit_pct: float = 0.05    # 5% para índices vs 10% crypto
    max_daily_loss: float = 0.05     # 5% pérdida máxima diaria
    
    # Parámetros técnicos
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bb_period: int = 20
    bb_std: float = 2.0
    
    # Parámetros específicos de índices
    vix_threshold_low: float = 20.0   # VIX bajo para estrategias agresivas
    vix_threshold_high: float = 30.0  # VIX alto para estrategias defensivas
    market_hours_filter: bool = True  # Filtrar por horarios de mercado
    volume_filter: bool = True        # Filtrar por volumen mínimo
    min_volume: int = 1000000        # Volumen mínimo diario
    
    # Apalancamiento (reducido para índices)
    max_leverage: float = 3.0        # Máximo 3x para índices vs 15x crypto
    leverage_vix_adjustment: bool = True  # Ajustar leverage según VIX
    
    # Horarios de trading
    allowed_sessions: List[TradingSession] = field(default_factory=lambda: [TradingSession.REGULAR])
    avoid_earnings: bool = True       # Evitar trading durante earnings
    avoid_fomc: bool = True          # Evitar trading durante FOMC

@dataclass
class AdaptedStrategy:
    """Estrategia adaptada para índices"""
    name: str
    original_strategy: StrategyType
    parameters: StrategyParameters
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    adaptation_notes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

class IndicesStrategyAdapter:
    """
    Adaptador principal para convertir estrategias de crypto a índices
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.indices_config = IndicesConfig()
        self.vix_analyzer = VIXAnalyzer()
        self.market_hours = AdvancedMarketHours()
        self.calibrator = IndicesParametersCalibrator()
        
        # Factores de conversión crypto -> índices
        self.conversion_factors = {
            'volatility_reduction': 0.3,    # Índices 30% menos volátiles
            'timeframe_extension': 1.5,     # Timeframes 50% más largos
            'leverage_reduction': 0.2,      # Leverage 80% menor
            'position_size_reduction': 0.5, # Posiciones 50% menores
            'stop_loss_tightening': 0.4,   # Stop loss 60% más ajustado
            'take_profit_reduction': 0.5,   # Take profit 50% menor
        }
        
        # Mapeo de símbolos crypto -> índices
        self.symbol_mapping = {
            'BTCUSDT': 'SPY',    # Bitcoin -> S&P 500
            'ETHUSDT': 'QQQ',    # Ethereum -> NASDAQ
            'ADAUSDT': 'IWM',    # Cardano -> Russell 2000
            'BNBUSDT': 'DIA',    # Binance -> Dow Jones
            'SOLUSDT': 'VTI',    # Solana -> Total Market
            'DOTUSDT': 'ARKK',   # Polkadot -> Innovation
            'LINKUSDT': 'XLF',   # Chainlink -> Financials
            'AVAXUSDT': 'XLK',   # Avalanche -> Technology
        }
        
        # Configuraciones predefinidas por tipo de estrategia
        self.strategy_configs = self._initialize_strategy_configs()
    
    def _initialize_strategy_configs(self) -> Dict[StrategyType, Dict]:
        """Inicializar configuraciones predefinidas para cada tipo de estrategia"""
        return {
            StrategyType.SIMPLE_ROI: {
                'target_roi_monthly': 0.05,  # 5% mensual para índices
                'max_positions': 2,
                'timeframes': ['1h', '4h'],
                'risk_profile': RiskProfile.CONSERVATIVE,
                'allowed_sessions': [TradingSession.REGULAR],
            },
            StrategyType.BALANCED_ROI: {
                'target_roi_monthly': 0.08,  # 8% mensual
                'max_positions': 3,
                'timeframes': ['30m', '1h', '4h'],
                'risk_profile': RiskProfile.MODERATE,
                'allowed_sessions': [TradingSession.REGULAR, TradingSession.EXTENDED],
            },
            StrategyType.OPTIMIZED_ROI: {
                'target_roi_monthly': 0.10,  # 10% mensual
                'max_positions': 4,
                'timeframes': ['15m', '30m', '1h', '4h'],
                'risk_profile': RiskProfile.MODERATE,
                'allowed_sessions': [TradingSession.REGULAR, TradingSession.EXTENDED],
            },
            StrategyType.ADVANCED_ROI: {
                'target_roi_monthly': 0.12,  # 12% mensual
                'max_positions': 5,
                'timeframes': ['15m', '30m', '1h', '4h', '1d'],
                'risk_profile': RiskProfile.AGGRESSIVE,
                'allowed_sessions': [TradingSession.PRE_MARKET, TradingSession.REGULAR, TradingSession.AFTER_HOURS],
            },
            StrategyType.ULTIMATE_SICAR: {
                'target_roi_monthly': 0.15,  # 15% mensual (objetivo original)
                'max_positions': 6,
                'timeframes': ['15m', '30m', '1h', '4h', '1d'],
                'risk_profile': RiskProfile.INSTITUTIONAL,
                'allowed_sessions': [TradingSession.PRE_MARKET, TradingSession.REGULAR, TradingSession.AFTER_HOURS],
            },
        }
    
    def adapt_strategy(self, strategy_type: StrategyType, 
                      custom_params: Optional[Dict] = None) -> AdaptedStrategy:
        """
        Adaptar una estrategia específica para índices
        
        Args:
            strategy_type: Tipo de estrategia a adaptar
            custom_params: Parámetros personalizados opcionales
            
        Returns:
            AdaptedStrategy: Estrategia adaptada para índices
        """
        self.logger.info(f"Adaptando estrategia {strategy_type.value} para índices")
        
        # Obtener configuración base
        base_config = self.strategy_configs.get(strategy_type, {})
        
        # Crear parámetros adaptados
        adapted_params = self._create_adapted_parameters(strategy_type, base_config, custom_params)
        
        # Aplicar calibración específica
        calibrated_params = self._calibrate_parameters(adapted_params)
        
        # Crear estrategia adaptada
        adapted_strategy = AdaptedStrategy(
            name=f"{strategy_type.value}_indices_adapted",
            original_strategy=strategy_type,
            parameters=calibrated_params,
            adaptation_notes=self._generate_adaptation_notes(strategy_type)
        )
        
        self.logger.info(f"Estrategia {strategy_type.value} adaptada exitosamente")
        return adapted_strategy
    
    def _create_adapted_parameters(self, strategy_type: StrategyType, 
                                 base_config: Dict, 
                                 custom_params: Optional[Dict]) -> StrategyParameters:
        """Crear parámetros adaptados para la estrategia"""
        
        # Símbolos objetivo basados en el tipo de estrategia
        target_symbols = self._get_target_symbols(strategy_type)
        
        # Timeframes adaptados
        timeframes = base_config.get('timeframes', ['1h', '4h'])
        
        # Parámetros de riesgo adaptados
        risk_profile = base_config.get('risk_profile', RiskProfile.MODERATE)
        risk_params = self._get_risk_parameters(risk_profile)
        
        # Crear parámetros base
        params = StrategyParameters(
            strategy_type=strategy_type,
            target_symbols=target_symbols,
            timeframes=timeframes,
            **risk_params
        )
        
        # Aplicar parámetros personalizados si se proporcionan
        if custom_params:
            for key, value in custom_params.items():
                if hasattr(params, key):
                    setattr(params, key, value)
        
        return params
    
    def _get_target_symbols(self, strategy_type: StrategyType) -> List[str]:
        """Obtener símbolos objetivo según el tipo de estrategia"""
        
        symbol_sets = {
            StrategyType.SIMPLE_ROI: ['SPY', 'QQQ'],
            StrategyType.BALANCED_ROI: ['SPY', 'QQQ', 'IWM'],
            StrategyType.OPTIMIZED_ROI: ['SPY', 'QQQ', 'IWM', 'DIA'],
            StrategyType.ADVANCED_ROI: ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI'],
            StrategyType.ULTIMATE_SICAR: ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI', 'ARKK'],
            StrategyType.AGGRESSIVE_MOMENTUM: ['QQQ', 'ARKK', 'XLK', 'TQQQ'],
            StrategyType.MARKET_MAKING: ['SPY', 'QQQ', 'IWM'],
            StrategyType.ARBITRAGE: ['SPY', 'VOO', 'IVV'],  # ETFs similares
        }
        
        return symbol_sets.get(strategy_type, ['SPY', 'QQQ'])
    
    def _get_risk_parameters(self, risk_profile: RiskProfile) -> Dict:
        """Obtener parámetros de riesgo según el perfil"""
        
        risk_configs = {
            RiskProfile.CONSERVATIVE: {
                'max_position_size': 0.15,
                'stop_loss_pct': 0.015,
                'take_profit_pct': 0.03,
                'max_leverage': 1.0,
                'max_daily_loss': 0.02,
            },
            RiskProfile.MODERATE: {
                'max_position_size': 0.25,
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.05,
                'max_leverage': 2.0,
                'max_daily_loss': 0.05,
            },
            RiskProfile.AGGRESSIVE: {
                'max_position_size': 0.35,
                'stop_loss_pct': 0.025,
                'take_profit_pct': 0.07,
                'max_leverage': 3.0,
                'max_daily_loss': 0.08,
            },
            RiskProfile.INSTITUTIONAL: {
                'max_position_size': 0.40,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.08,
                'max_leverage': 3.0,
                'max_daily_loss': 0.10,
            },
        }
        
        return risk_configs.get(risk_profile, risk_configs[RiskProfile.MODERATE])
    
    def _calibrate_parameters(self, params: StrategyParameters) -> StrategyParameters:
        """Calibrar parámetros usando el calibrador de índices"""
        
        # Obtener análisis VIX actual
        vix_analysis = self.vix_analyzer.get_current_analysis()
        
        # Ajustar parámetros según VIX
        if vix_analysis and params.leverage_vix_adjustment:
            vix_level = vix_analysis.vix_level
            
            if vix_level == VIXLevel.VERY_HIGH:
                params.max_leverage *= 0.5
                params.max_position_size *= 0.7
                params.stop_loss_pct *= 0.8
            elif vix_level == VIXLevel.HIGH:
                params.max_leverage *= 0.7
                params.max_position_size *= 0.85
                params.stop_loss_pct *= 0.9
            elif vix_level == VIXLevel.LOW:
                params.max_leverage *= 1.2
                params.max_position_size *= 1.1
        
        # Calibrar indicadores técnicos
        calibrated_indicators = self.calibrator.calibrate_technical_indicators(
            params.target_symbols[0] if params.target_symbols else 'SPY'
        )
        
        # Aplicar calibración
        params.rsi_period = calibrated_indicators.get('rsi_period', params.rsi_period)
        params.macd_fast = calibrated_indicators.get('macd_fast', params.macd_fast)
        params.macd_slow = calibrated_indicators.get('macd_slow', params.macd_slow)
        params.bb_period = calibrated_indicators.get('bb_period', params.bb_period)
        
        return params
    
    def _generate_adaptation_notes(self, strategy_type: StrategyType) -> List[str]:
        """Generar notas de adaptación para la estrategia"""
        
        base_notes = [
            f"Estrategia {strategy_type.value} adaptada para trading de índices ETF",
            "Parámetros de riesgo ajustados para menor volatilidad de índices",
            "Timeframes extendidos para adaptarse a movimientos de índices",
            "Leverage reducido para gestión de riesgo conservadora",
            "Filtros de horarios de mercado aplicados",
        ]
        
        strategy_specific_notes = {
            StrategyType.ULTIMATE_SICAR: [
                "Objetivo de ROI mensual mantenido en 15%",
                "Diversificación en 6 ETFs principales",
                "Integración con análisis VIX para gestión de riesgo",
                "Sistema de machine learning adaptado para patrones de índices",
            ],
            StrategyType.AGGRESSIVE_MOMENTUM: [
                "Enfoque en ETFs de tecnología y crecimiento",
                "Detección de breakouts adaptada para índices",
                "Filtros de volumen específicos para ETFs",
            ],
            StrategyType.MARKET_MAKING: [
                "Spreads ajustados para liquidez de ETFs",
                "Horarios de market making limitados a sesión regular",
                "Gestión de inventario adaptada para índices",
            ],
        }
        
        specific_notes = strategy_specific_notes.get(strategy_type, [])
        return base_notes + specific_notes
    
    def adapt_all_strategies(self) -> Dict[StrategyType, AdaptedStrategy]:
        """Adaptar todas las estrategias disponibles"""
        
        self.logger.info("Iniciando adaptación de todas las estrategias")
        adapted_strategies = {}
        
        for strategy_type in StrategyType:
            try:
                adapted_strategy = self.adapt_strategy(strategy_type)
                adapted_strategies[strategy_type] = adapted_strategy
                self.logger.info(f"Estrategia {strategy_type.value} adaptada exitosamente")
            except Exception as e:
                self.logger.error(f"Error adaptando estrategia {strategy_type.value}: {e}")
        
        self.logger.info(f"Adaptación completada: {len(adapted_strategies)} estrategias")
        return adapted_strategies
    
    def get_strategy_recommendations(self, 
                                   capital: float, 
                                   risk_tolerance: str,
                                   experience_level: str) -> List[Tuple[StrategyType, str]]:
        """
        Obtener recomendaciones de estrategias según perfil del usuario
        
        Args:
            capital: Capital disponible
            risk_tolerance: Tolerancia al riesgo ('low', 'medium', 'high')
            experience_level: Nivel de experiencia ('beginner', 'intermediate', 'advanced')
            
        Returns:
            Lista de tuplas (StrategyType, razón)
        """
        
        recommendations = []
        
        # Recomendaciones basadas en capital
        if capital < 1000:
            recommendations.append((
                StrategyType.SIMPLE_ROI,
                "Capital bajo - estrategia conservadora recomendada"
            ))
        elif capital < 5000:
            recommendations.append((
                StrategyType.BALANCED_ROI,
                "Capital moderado - estrategia balanceada apropiada"
            ))
        else:
            recommendations.append((
                StrategyType.OPTIMIZED_ROI,
                "Capital suficiente para estrategia optimizada"
            ))
        
        # Recomendaciones basadas en tolerancia al riesgo
        if risk_tolerance.lower() == 'low':
            recommendations.append((
                StrategyType.SIMPLE_ROI,
                "Baja tolerancia al riesgo - estrategia conservadora"
            ))
        elif risk_tolerance.lower() == 'high':
            recommendations.append((
                StrategyType.ULTIMATE_SICAR,
                "Alta tolerancia al riesgo - estrategia agresiva disponible"
            ))
        
        # Recomendaciones basadas en experiencia
        if experience_level.lower() == 'beginner':
            recommendations.append((
                StrategyType.SIMPLE_ROI,
                "Principiante - comenzar con estrategia simple"
            ))
        elif experience_level.lower() == 'advanced':
            recommendations.append((
                StrategyType.ULTIMATE_SICAR,
                "Avanzado - estrategia completa disponible"
            ))
        
        return recommendations
    
    def export_adapted_strategy(self, strategy: AdaptedStrategy, 
                              file_path: str) -> bool:
        """Exportar estrategia adaptada a archivo JSON"""
        
        try:
            strategy_dict = {
                'name': strategy.name,
                'original_strategy': strategy.original_strategy.value,
                'parameters': {
                    'strategy_type': strategy.parameters.strategy_type.value,
                    'target_symbols': strategy.parameters.target_symbols,
                    'timeframes': strategy.parameters.timeframes,
                    'max_position_size': strategy.parameters.max_position_size,
                    'stop_loss_pct': strategy.parameters.stop_loss_pct,
                    'take_profit_pct': strategy.parameters.take_profit_pct,
                    'max_leverage': strategy.parameters.max_leverage,
                    'vix_threshold_low': strategy.parameters.vix_threshold_low,
                    'vix_threshold_high': strategy.parameters.vix_threshold_high,
                    'allowed_sessions': [s.value for s in strategy.parameters.allowed_sessions],
                },
                'adaptation_notes': strategy.adaptation_notes,
                'created_at': strategy.created_at.isoformat(),
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(strategy_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Estrategia exportada a {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exportando estrategia: {e}")
            return False
    
    def generate_strategy_comparison(self, 
                                   strategies: Dict[StrategyType, AdaptedStrategy]) -> pd.DataFrame:
        """Generar comparación de estrategias adaptadas"""
        
        comparison_data = []
        
        for strategy_type, strategy in strategies.items():
            params = strategy.parameters
            
            comparison_data.append({
                'Estrategia': strategy.name,
                'Tipo Original': strategy_type.value,
                'Símbolos': len(params.target_symbols),
                'Timeframes': len(params.timeframes),
                'Max Position %': f"{params.max_position_size*100:.1f}%",
                'Stop Loss %': f"{params.stop_loss_pct*100:.1f}%",
                'Take Profit %': f"{params.take_profit_pct*100:.1f}%",
                'Max Leverage': f"{params.max_leverage:.1f}x",
                'Sesiones': len(params.allowed_sessions),
                'Complejidad': self._calculate_complexity_score(params),
            })
        
        return pd.DataFrame(comparison_data)
    
    def _calculate_complexity_score(self, params: StrategyParameters) -> str:
        """Calcular puntuación de complejidad de la estrategia"""
        
        score = 0
        score += len(params.target_symbols) * 10
        score += len(params.timeframes) * 15
        score += int(params.max_leverage * 10)
        score += len(params.allowed_sessions) * 5
        
        if score < 50:
            return "Baja"
        elif score < 100:
            return "Media"
        elif score < 150:
            return "Alta"
        else:
            return "Muy Alta"

# Función de utilidad para uso directo
def adapt_strategy_for_indices(strategy_type: str, 
                             custom_params: Optional[Dict] = None) -> AdaptedStrategy:
    """
    Función de utilidad para adaptar una estrategia específica
    
    Args:
        strategy_type: Nombre del tipo de estrategia
        custom_params: Parámetros personalizados opcionales
        
    Returns:
        AdaptedStrategy: Estrategia adaptada
    """
    adapter = IndicesStrategyAdapter()
    strategy_enum = StrategyType(strategy_type)
    return adapter.adapt_strategy(strategy_enum, custom_params)

# Demo y testing
if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(level=logging.INFO)
    
    # Crear adaptador
    adapter = IndicesStrategyAdapter()
    
    print("=== SICAR - Adaptador de Estrategias para Índices ===\n")
    
    # Adaptar estrategia Ultimate SICAR
    print("1. Adaptando Ultimate SICAR System...")
    ultimate_strategy = adapter.adapt_strategy(StrategyType.ULTIMATE_SICAR)
    print(f"   ✓ Estrategia adaptada: {ultimate_strategy.name}")
    print(f"   ✓ Símbolos objetivo: {ultimate_strategy.parameters.target_symbols}")
    print(f"   ✓ Leverage máximo: {ultimate_strategy.parameters.max_leverage}x")
    print(f"   ✓ Stop loss: {ultimate_strategy.parameters.stop_loss_pct*100:.1f}%")
    
    # Adaptar todas las estrategias
    print("\n2. Adaptando todas las estrategias...")
    all_strategies = adapter.adapt_all_strategies()
    print(f"   ✓ {len(all_strategies)} estrategias adaptadas exitosamente")
    
    # Generar comparación
    print("\n3. Generando comparación de estrategias...")
    comparison = adapter.generate_strategy_comparison(all_strategies)
    print(comparison.to_string(index=False))
    
    # Obtener recomendaciones
    print("\n4. Recomendaciones para diferentes perfiles:")
    
    profiles = [
        (1000, 'low', 'beginner'),
        (5000, 'medium', 'intermediate'),
        (10000, 'high', 'advanced'),
    ]
    
    for capital, risk, experience in profiles:
        recommendations = adapter.get_strategy_recommendations(capital, risk, experience)
        print(f"\n   Capital: ${capital}, Riesgo: {risk}, Experiencia: {experience}")
        for strategy_type, reason in recommendations:
            print(f"   - {strategy_type.value}: {reason}")
    
    print("\n=== Adaptación de Estrategias Completada ===")