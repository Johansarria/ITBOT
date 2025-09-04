"""
🚀 SISTEMA V3 DINÁMICO ADAPTATIVO
===================================

Sistema que dinamiza las estrategias V3 según condiciones de mercado en tiempo real.
Evita overfitting y optimiza performance adaptándose automáticamente.

Autor: Johan Sarria
Fecha: 1 septiembre 2025
Versión: 3.1 Dynamic
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass
from enum import Enum

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Regímenes de mercado identificados dinámicamente"""
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear" 
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    CONSOLIDATION = "consolidation"

@dataclass
class MarketCondition:
    """Condiciones de mercado actuales"""
    regime: MarketRegime
    volatility_percentile: float
    trend_strength: float
    volume_ratio: float
    momentum_score: float
    suitable_strategies: List[str]
    confidence: float

@dataclass
class DynamicConfig:
    """Configuración dinámica adaptativa"""
    name: str
    base_config: Dict
    adaptations: Dict[MarketRegime, Dict]
    activation_threshold: float
    performance_weight: float

class V3DynamicSystem:
    """
    🎯 Sistema V3 Dinámico que adapta estrategias según condiciones de mercado
    """
    
    def __init__(self):
        self.current_regime = None
        self.regime_history = []
        self.performance_tracker = {}
        self.adaptive_configs = self._create_adaptive_configs()
        self.market_analyzer = MarketRegimeAnalyzer()
        
        logger.info("🚀 Sistema V3 Dinámico inicializado")
    
    def _create_adaptive_configs(self) -> Dict[str, DynamicConfig]:
        """Crear configuraciones adaptativas para cada estrategia"""
        
        return {
            "scalping_adaptive": DynamicConfig(
                name="Scalping_Adaptativo",
                base_config={
                    "rsi_oversold": 25,
                    "rsi_overbought": 75,
                    "bb_std": 2.0,
                    "volume_threshold": 1.2,
                    "risk_per_trade": 0.015,
                    "atr_multiplier_sl": 1.5,
                    "atr_multiplier_tp": 2.5
                },
                adaptations={
                    MarketRegime.HIGH_VOLATILITY: {
                        "rsi_oversold": 20,
                        "rsi_overbought": 80,
                        "bb_std": 2.5,
                        "risk_per_trade": 0.02,
                        "atr_multiplier_sl": 2.0,
                        "atr_multiplier_tp": 3.0
                    },
                    MarketRegime.LOW_VOLATILITY: {
                        "rsi_oversold": 30,
                        "rsi_overbought": 70,
                        "bb_std": 1.5,
                        "risk_per_trade": 0.01,
                        "atr_multiplier_sl": 1.0,
                        "atr_multiplier_tp": 2.0
                    },
                    MarketRegime.TRENDING_BULL: {
                        "rsi_oversold": 30,
                        "rsi_overbought": 85,
                        "volume_threshold": 1.5,
                        "risk_per_trade": 0.025
                    },
                    MarketRegime.TRENDING_BEAR: {
                        "rsi_oversold": 15,
                        "rsi_overbought": 70,
                        "volume_threshold": 1.8,
                        "risk_per_trade": 0.02
                    },
                    MarketRegime.SIDEWAYS: {
                        # En mercados laterales, desactivar o usar configuración muy conservadora
                        "activation_threshold": 0.3,  # Solo activar si confianza > 30%
                        "risk_per_trade": 0.005,
                        "rsi_oversold": 35,
                        "rsi_overbought": 65
                    }
                },
                activation_threshold=0.6,
                performance_weight=1.0
            ),
            
            "swing_adaptive": DynamicConfig(
                name="Swing_Adaptativo",
                base_config={
                    "rsi_oversold": 30,
                    "rsi_overbought": 70,
                    "bb_std": 2.2,
                    "volume_threshold": 1.1,
                    "risk_per_trade": 0.02,
                    "atr_multiplier_sl": 2.0,
                    "atr_multiplier_tp": 4.0
                },
                adaptations={
                    MarketRegime.TRENDING_BULL: {
                        "rsi_oversold": 35,
                        "rsi_overbought": 80,
                        "risk_per_trade": 0.03,
                        "atr_multiplier_tp": 5.0
                    },
                    MarketRegime.TRENDING_BEAR: {
                        "rsi_oversold": 20,
                        "rsi_overbought": 65,
                        "risk_per_trade": 0.025,
                        "atr_multiplier_tp": 3.5
                    },
                    MarketRegime.CONSOLIDATION: {
                        "bb_std": 1.8,
                        "risk_per_trade": 0.015,
                        "volume_threshold": 0.8
                    },
                    MarketRegime.SIDEWAYS: {
                        "activation_threshold": 0.2,  # Muy conservador en laterales
                        "risk_per_trade": 0.01
                    }
                },
                activation_threshold=0.5,
                performance_weight=1.2
            ),
            
            "hybrid_adaptive": DynamicConfig(
                name="Híbrido_Adaptativo",
                base_config={
                    "rsi_oversold": 25,
                    "rsi_overbought": 75,
                    "bb_std": 2.1,
                    "volume_threshold": 1.15,
                    "risk_per_trade": 0.025,
                    "atr_multiplier_sl": 1.8,
                    "atr_multiplier_tp": 3.5
                },
                adaptations={
                    MarketRegime.BREAKOUT: {
                        "rsi_oversold": 20,
                        "rsi_overbought": 80,
                        "bb_std": 3.0,
                        "risk_per_trade": 0.035,
                        "volume_threshold": 2.0
                    },
                    MarketRegime.HIGH_VOLATILITY: {
                        "bb_std": 2.8,
                        "atr_multiplier_sl": 2.5,
                        "atr_multiplier_tp": 4.0
                    },
                    MarketRegime.LOW_VOLATILITY: {
                        "bb_std": 1.6,
                        "atr_multiplier_sl": 1.2,
                        "atr_multiplier_tp": 2.5,
                        "risk_per_trade": 0.015
                    }
                },
                activation_threshold=0.4,
                performance_weight=1.1
            )
        }
    
    async def analyze_market_and_adapt(self, market_data: pd.DataFrame, 
                                     current_prices: Dict) -> Dict:
        """
        🔍 Analizar mercado y adaptar estrategias dinámicamente
        """
        try:
            # 1. Análisis de régimen de mercado
            current_condition = await self.market_analyzer.analyze_regime(
                market_data, current_prices
            )
            
            # 2. Actualizar historial de regímenes
            self._update_regime_history(current_condition)
            
            # 3. Seleccionar estrategias activas según condiciones
            active_strategies = self._select_active_strategies(current_condition)
            
            # 4. Adaptar configuraciones
            adapted_configs = self._adapt_configurations(
                current_condition, active_strategies
            )
            
            # 5. Calcular scores de confianza
            confidence_scores = self._calculate_confidence_scores(
                current_condition, adapted_configs
            )
            
            analysis_result = {
                "timestamp": datetime.now().isoformat(),
                "market_condition": current_condition,
                "active_strategies": active_strategies,
                "adapted_configs": adapted_configs,
                "confidence_scores": confidence_scores,
                "performance_adjustment": self._get_performance_adjustment(),
                "recommendations": self._generate_recommendations(current_condition)
            }
            
            logger.info(f"📊 Análisis completado - Régimen: {current_condition.regime.value}")
            logger.info(f"🎯 Estrategias activas: {len(active_strategies)}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Error en análisis dinámico: {str(e)}")
            return self._get_fallback_analysis()
    
    def _select_active_strategies(self, condition: MarketCondition) -> List[str]:
        """Seleccionar estrategias que deben estar activas según condiciones"""
        
        active = []
        
        # Reglas de activación según régimen de mercado
        if condition.regime in [MarketRegime.HIGH_VOLATILITY, MarketRegime.BREAKOUT]:
            if condition.confidence > 0.6:
                active.extend(["scalping_adaptive", "hybrid_adaptive"])
        
        if condition.regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR]:
            if condition.trend_strength > 0.5:
                active.extend(["swing_adaptive", "hybrid_adaptive"])
        
        if condition.regime == MarketRegime.CONSOLIDATION:
            if condition.volatility_percentile > 0.3:
                active.append("hybrid_adaptive")
        
        # En mercados laterales, solo activar si hay alta confianza
        if condition.regime == MarketRegime.SIDEWAYS:
            if condition.confidence > 0.8 and condition.momentum_score > 0.6:
                active.append("hybrid_adaptive")  # Solo la más conservadora
        
        # Verificar performance histórica
        active = [s for s in active if self._check_strategy_performance(s)]
        
        return list(set(active))  # Eliminar duplicados
    
    def _adapt_configurations(self, condition: MarketCondition, 
                            active_strategies: List[str]) -> Dict:
        """Adaptar configuraciones según condiciones actuales"""
        
        adapted = {}
        
        for strategy_name in active_strategies:
            if strategy_name not in self.adaptive_configs:
                continue
                
            config = self.adaptive_configs[strategy_name]
            base_config = config.base_config.copy()
            
            # Aplicar adaptaciones específicas del régimen
            if condition.regime in config.adaptations:
                regime_adaptations = config.adaptations[condition.regime]
                base_config.update(regime_adaptations)
            
            # Ajustes dinámicos adicionales basados en métricas
            base_config = self._apply_dynamic_adjustments(
                base_config, condition, strategy_name
            )
            
            adapted[strategy_name] = {
                "config": base_config,
                "activation_threshold": config.activation_threshold,
                "confidence_required": self._calculate_required_confidence(
                    condition, strategy_name
                ),
                "risk_adjustment": self._calculate_risk_adjustment(condition),
                "expected_performance": self._estimate_performance(
                    condition, strategy_name
                )
            }
        
        return adapted
    
    def _apply_dynamic_adjustments(self, config: Dict, condition: MarketCondition,
                                 strategy_name: str) -> Dict:
        """Aplicar ajustes dinámicos basados en condiciones actuales"""
        
        # Ajuste de riesgo basado en volatilidad
        vol_multiplier = 1.0
        if condition.volatility_percentile > 0.8:
            vol_multiplier = 0.8  # Reducir riesgo en alta volatilidad
        elif condition.volatility_percentile < 0.2:
            vol_multiplier = 1.2  # Aumentar riesgo en baja volatilidad
        
        config["risk_per_trade"] = config["risk_per_trade"] * vol_multiplier
        
        # Ajuste de umbrales basado en momentum
        if condition.momentum_score > 0.7:
            # Momentum fuerte - ajustar RSI para entrada más agresiva
            config["rsi_oversold"] = max(15, config["rsi_oversold"] - 5)
            config["rsi_overbought"] = min(85, config["rsi_overbought"] + 5)
        elif condition.momentum_score < 0.3:
            # Momentum débil - ser más conservador
            config["rsi_oversold"] = min(35, config["rsi_oversold"] + 5)
            config["rsi_overbought"] = max(65, config["rsi_overbought"] - 5)
        
        # Ajuste de volumen basado en ratio actual
        if condition.volume_ratio > 1.5:
            config["volume_threshold"] = config["volume_threshold"] * 0.8
        elif condition.volume_ratio < 0.8:
            config["volume_threshold"] = config["volume_threshold"] * 1.3
        
        return config
    
    def _calculate_confidence_scores(self, condition: MarketCondition, 
                                   adapted_configs: Dict) -> Dict:
        """Calcular scores de confianza para cada estrategia"""
        
        confidence_scores = {}
        
        for strategy_name, config_data in adapted_configs.items():
            base_confidence = condition.confidence
            
            # Ajustar confianza basada en régimen de mercado
            regime_bonus = {
                MarketRegime.HIGH_VOLATILITY: 0.1,
                MarketRegime.TRENDING_BULL: 0.15,
                MarketRegime.TRENDING_BEAR: 0.12,
                MarketRegime.BREAKOUT: 0.2,
                MarketRegime.CONSOLIDATION: 0.05,
                MarketRegime.SIDEWAYS: -0.3,  # Penalización fuerte
                MarketRegime.LOW_VOLATILITY: -0.1
            }.get(condition.regime, 0.0)
            
            # Ajustar por performance histórica
            historical_performance = self._get_historical_performance(strategy_name)
            performance_bonus = (historical_performance - 0.5) * 0.2
            
            # Ajustar por condiciones específicas
            condition_bonus = 0.0
            if condition.trend_strength > 0.6 and "swing" in strategy_name:
                condition_bonus += 0.1
            if condition.volatility_percentile > 0.7 and "scalping" in strategy_name:
                condition_bonus += 0.15
            
            final_confidence = min(1.0, max(0.0, 
                base_confidence + regime_bonus + performance_bonus + condition_bonus
            ))
            
            confidence_scores[strategy_name] = {
                "total_confidence": final_confidence,
                "base_confidence": base_confidence,
                "regime_adjustment": regime_bonus,
                "performance_adjustment": performance_bonus,
                "condition_adjustment": condition_bonus,
                "should_activate": final_confidence >= config_data["activation_threshold"]
            }
        
        return confidence_scores
    
    def _generate_recommendations(self, condition: MarketCondition) -> Dict:
        """Generar recomendaciones específicas para las condiciones actuales"""
        
        recommendations = {
            "primary_action": "",
            "risk_level": "medium",
            "expected_activity": "normal",
            "key_factors": [],
            "warnings": []
        }
        
        # Recomendaciones por régimen
        if condition.regime == MarketRegime.SIDEWAYS:
            recommendations.update({
                "primary_action": "HOLD_CONSERVATIVE",
                "risk_level": "very_low", 
                "expected_activity": "minimal",
                "key_factors": ["Mercado lateral", "Pocas oportunidades"],
                "warnings": ["Evitar over-trading", "Esperar breakout"]
            })
        
        elif condition.regime == MarketRegime.HIGH_VOLATILITY:
            recommendations.update({
                "primary_action": "SCALP_AGGRESSIVE",
                "risk_level": "high",
                "expected_activity": "very_high", 
                "key_factors": ["Alta volatilidad", "Oportunidades de scalping"],
                "warnings": ["Controlar drawdown", "Stops más amplios"]
            })
        
        elif condition.regime in [MarketRegime.TRENDING_BULL, MarketRegime.TRENDING_BEAR]:
            recommendations.update({
                "primary_action": "TREND_FOLLOW",
                "risk_level": "medium-high",
                "expected_activity": "high",
                "key_factors": ["Tendencia clara", "Momentum fuerte"],
                "warnings": ["Vigilar reversión", "Trailing stops"]
            })
        
        elif condition.regime == MarketRegime.BREAKOUT:
            recommendations.update({
                "primary_action": "BREAKOUT_CAPTURE",
                "risk_level": "high",
                "expected_activity": "high",
                "key_factors": ["Breakout confirmado", "Volume alto"],
                "warnings": ["Falsos breakouts", "Gestión rápida"]
            })
        
        return recommendations
    
    def _update_regime_history(self, condition: MarketCondition):
        """Actualizar historial de regímenes para análisis de persistencia"""
        
        self.regime_history.append({
            "timestamp": datetime.now(),
            "regime": condition.regime,
            "confidence": condition.confidence,
            "volatility": condition.volatility_percentile,
            "trend_strength": condition.trend_strength
        })
        
        # Mantener solo últimas 100 observaciones
        if len(self.regime_history) > 100:
            self.regime_history = self.regime_history[-100:]
        
        self.current_regime = condition.regime
    
    def _check_strategy_performance(self, strategy_name: str) -> bool:
        """Verificar si la estrategia ha tenido buena performance recientemente"""
        
        if strategy_name not in self.performance_tracker:
            return True  # Nueva estrategia, dar oportunidad
        
        recent_performance = self.performance_tracker[strategy_name].get("recent_return", 0)
        return recent_performance > -0.05  # No activar si pérdidas > 5%
    
    def _calculate_required_confidence(self, condition: MarketCondition, 
                                     strategy_name: str) -> float:
        """Calcular confianza requerida según condiciones"""
        
        base_required = 0.5
        
        # Mercados laterales requieren más confianza
        if condition.regime == MarketRegime.SIDEWAYS:
            base_required = 0.8
        
        # Estrategias de scalping en baja volatilidad requieren más confianza  
        if "scalping" in strategy_name and condition.volatility_percentile < 0.3:
            base_required = 0.7
        
        return base_required
    
    def _calculate_risk_adjustment(self, condition: MarketCondition) -> float:
        """Calcular ajuste de riesgo según condiciones"""
        
        base_risk = 1.0
        
        # Ajustar por volatilidad
        if condition.volatility_percentile > 0.8:
            base_risk *= 0.7  # Reducir riesgo
        elif condition.volatility_percentile < 0.2:
            base_risk *= 1.3  # Aumentar riesgo
        
        # Ajustar por confianza
        confidence_multiplier = 0.5 + (condition.confidence * 0.5)
        base_risk *= confidence_multiplier
        
        return min(2.0, max(0.3, base_risk))
    
    def _estimate_performance(self, condition: MarketCondition, 
                            strategy_name: str) -> Dict:
        """Estimar performance esperada según condiciones"""
        
        base_estimates = {
            "scalping_adaptive": {"monthly_return": 0.08, "win_rate": 0.45, "trades_per_month": 40},
            "swing_adaptive": {"monthly_return": 0.06, "win_rate": 0.55, "trades_per_month": 15}, 
            "hybrid_adaptive": {"monthly_return": 0.07, "win_rate": 0.50, "trades_per_month": 25}
        }
        
        if strategy_name not in base_estimates:
            return {"monthly_return": 0.05, "win_rate": 0.50, "trades_per_month": 20}
        
        base = base_estimates[strategy_name].copy()
        
        # Ajustar por régimen de mercado
        regime_multipliers = {
            MarketRegime.TRENDING_BULL: {"monthly_return": 1.4, "win_rate": 1.2, "trades_per_month": 1.3},
            MarketRegime.TRENDING_BEAR: {"monthly_return": 1.2, "win_rate": 1.1, "trades_per_month": 1.2},
            MarketRegime.HIGH_VOLATILITY: {"monthly_return": 1.6, "win_rate": 1.0, "trades_per_month": 1.8},
            MarketRegime.BREAKOUT: {"monthly_return": 1.8, "win_rate": 1.1, "trades_per_month": 1.5},
            MarketRegime.SIDEWAYS: {"monthly_return": 0.2, "win_rate": 0.7, "trades_per_month": 0.3},
            MarketRegime.LOW_VOLATILITY: {"monthly_return": 0.6, "win_rate": 0.9, "trades_per_month": 0.5},
            MarketRegime.CONSOLIDATION: {"monthly_return": 0.8, "win_rate": 0.95, "trades_per_month": 0.7}
        }
        
        multipliers = regime_multipliers.get(condition.regime, 
                                           {"monthly_return": 1.0, "win_rate": 1.0, "trades_per_month": 1.0})
        
        for key, value in base.items():
            base[key] = value * multipliers[key] * condition.confidence
        
        # Asegurar límites realistas
        base["monthly_return"] = min(0.3, max(-0.1, base["monthly_return"]))
        base["win_rate"] = min(0.9, max(0.3, base["win_rate"]))
        base["trades_per_month"] = min(100, max(1, base["trades_per_month"]))
        
        return base
    
    def _get_performance_adjustment(self) -> Dict:
        """Obtener ajustes basados en performance histórica"""
        
        return {
            "global_multiplier": 1.0,
            "risk_reduction_factor": 1.0,
            "activity_adjustment": 1.0,
            "confidence_boost": 0.0
        }
    
    def _get_historical_performance(self, strategy_name: str) -> float:
        """Obtener performance histórica de la estrategia"""
        
        if strategy_name not in self.performance_tracker:
            return 0.5  # Neutral para nuevas estrategias
        
        return self.performance_tracker[strategy_name].get("win_rate", 0.5)
    
    def _get_fallback_analysis(self) -> Dict:
        """Análisis de respaldo en caso de error"""
        
        return {
            "timestamp": datetime.now().isoformat(),
            "market_condition": MarketCondition(
                regime=MarketRegime.CONSOLIDATION,
                volatility_percentile=0.5,
                trend_strength=0.5,
                volume_ratio=1.0,
                momentum_score=0.5,
                suitable_strategies=["hybrid_adaptive"],
                confidence=0.3
            ),
            "active_strategies": ["hybrid_adaptive"],
            "adapted_configs": {
                "hybrid_adaptive": self.adaptive_configs["hybrid_adaptive"].base_config
            },
            "confidence_scores": {"hybrid_adaptive": {"total_confidence": 0.3}},
            "performance_adjustment": {"global_multiplier": 1.0},
            "recommendations": {
                "primary_action": "HOLD_CONSERVATIVE",
                "risk_level": "low",
                "warnings": ["Análisis de mercado falló", "Usar configuración conservadora"]
            }
        }

class MarketRegimeAnalyzer:
    """
    🔍 Analizador de regímenes de mercado en tiempo real
    """
    
    def __init__(self):
        self.volatility_lookback = 24  # 24 horas para timeframes cortos
        self.trend_lookback = 48       # 48 períodos para tendencia
        self.volume_lookback = 12      # 12 períodos para volumen
    
    async def analyze_regime(self, market_data: pd.DataFrame, 
                           current_prices: Dict) -> MarketCondition:
        """Analizar régimen de mercado actual"""
        
        try:
            # Calcular indicadores técnicos
            indicators = self._calculate_indicators(market_data)
            
            # Analizar volatilidad
            volatility_analysis = self._analyze_volatility(market_data, indicators)
            
            # Analizar tendencia
            trend_analysis = self._analyze_trend(market_data, indicators)
            
            # Analizar volumen
            volume_analysis = self._analyze_volume(market_data)
            
            # Analizar momentum
            momentum_analysis = self._analyze_momentum(indicators)
            
            # Determinar régimen
            regime = self._determine_regime(
                volatility_analysis, trend_analysis, volume_analysis, momentum_analysis
            )
            
            # Calcular confianza
            confidence = self._calculate_confidence(
                volatility_analysis, trend_analysis, volume_analysis, momentum_analysis
            )
            
            # Determinar estrategias adecuadas
            suitable_strategies = self._determine_suitable_strategies(regime, confidence)
            
            return MarketCondition(
                regime=regime,
                volatility_percentile=volatility_analysis["percentile"],
                trend_strength=trend_analysis["strength"],
                volume_ratio=volume_analysis["ratio"],
                momentum_score=momentum_analysis["score"],
                suitable_strategies=suitable_strategies,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"❌ Error en análisis de régimen: {str(e)}")
            return self._get_default_condition()
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calcular indicadores técnicos necesarios"""
        
        indicators = {}
        
        # ATR para volatilidad
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        indicators['atr'] = true_range.rolling(14).mean()
        
        # EMAs para tendencia
        indicators['ema_fast'] = df['close'].ewm(span=12).mean()
        indicators['ema_slow'] = df['close'].ewm(span=26).mean()
        indicators['ema_long'] = df['close'].ewm(span=50).mean()
        
        # RSI para momentum
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        indicators['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands para volatilidad relativa
        sma_20 = df['close'].rolling(20).mean()
        std_20 = df['close'].rolling(20).std()
        indicators['bb_upper'] = sma_20 + (2 * std_20)
        indicators['bb_lower'] = sma_20 - (2 * std_20)
        indicators['bb_width'] = (indicators['bb_upper'] - indicators['bb_lower']) / sma_20
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        indicators['macd'] = exp1 - exp2
        indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean()
        
        return indicators
    
    def _analyze_volatility(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """Analizar volatilidad del mercado"""
        
        current_atr = indicators['atr'].iloc[-1]
        atr_sma = indicators['atr'].rolling(self.volatility_lookback).mean().iloc[-1]
        
        # Percentil de volatilidad (últimas 100 observaciones)
        atr_percentile = (indicators['atr'].iloc[-100:] < current_atr).mean()
        
        # Ancho de Bollinger Bands
        bb_width_current = indicators['bb_width'].iloc[-1]
        bb_width_avg = indicators['bb_width'].rolling(20).mean().iloc[-1]
        
        # Volatilidad de retornos
        returns = df['close'].pct_change()
        recent_volatility = returns.rolling(24).std().iloc[-1]
        historical_volatility = returns.rolling(100).std().mean()
        
        volatility_ratio = recent_volatility / historical_volatility if historical_volatility > 0 else 1
        
        return {
            "current_atr": current_atr,
            "atr_ratio": current_atr / atr_sma if atr_sma > 0 else 1,
            "percentile": atr_percentile,
            "bb_expansion": bb_width_current / bb_width_avg if bb_width_avg > 0 else 1,
            "volatility_ratio": volatility_ratio,
            "is_high_volatility": atr_percentile > 0.8 and volatility_ratio > 1.3,
            "is_low_volatility": atr_percentile < 0.2 and volatility_ratio < 0.7
        }
    
    def _analyze_trend(self, df: pd.DataFrame, indicators: Dict) -> Dict:
        """Analizar tendencia del mercado"""
        
        # Direcciones de EMAs
        ema_fast = indicators['ema_fast'].iloc[-1]
        ema_slow = indicators['ema_slow'].iloc[-1]
        ema_long = indicators['ema_long'].iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Fuerza de tendencia basada en alineación de EMAs
        if ema_fast > ema_slow > ema_long and current_price > ema_fast:
            trend_direction = "bullish"
            trend_strength = min(1.0, (ema_fast - ema_long) / ema_long * 10)
        elif ema_fast < ema_slow < ema_long and current_price < ema_fast:
            trend_direction = "bearish"  
            trend_strength = min(1.0, (ema_long - ema_fast) / ema_long * 10)
        else:
            trend_direction = "sideways"
            trend_strength = 0.0
        
        # Pendiente de EMA lenta
        ema_slope = (indicators['ema_slow'].iloc[-1] - indicators['ema_slow'].iloc[-5]) / indicators['ema_slow'].iloc[-5]
        
        # Consistencia de tendencia
        price_changes = df['close'].pct_change().iloc[-self.trend_lookback:]
        consistency = len(price_changes[price_changes > 0]) / len(price_changes) if trend_direction == "bullish" else len(price_changes[price_changes < 0]) / len(price_changes)
        
        return {
            "direction": trend_direction,
            "strength": abs(trend_strength),
            "ema_alignment": ema_fast > ema_slow > ema_long if trend_direction == "bullish" else ema_fast < ema_slow < ema_long,
            "slope": ema_slope,
            "consistency": consistency,
            "is_trending": trend_strength > 0.3 and consistency > 0.6
        }
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict:
        """Analizar patrones de volumen"""
        
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].rolling(self.volume_lookback).mean().iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Tendencia de volumen
        volume_trend = df['volume'].rolling(5).mean().iloc[-1] / df['volume'].rolling(20).mean().iloc[-1]
        
        # Volume Price Trend (VPT)
        vpt = ((df['close'].diff() / df['close'].shift()) * df['volume']).cumsum()
        vpt_trend = (vpt.iloc[-1] - vpt.iloc[-10]) / abs(vpt.iloc[-10]) if vpt.iloc[-10] != 0 else 0
        
        return {
            "current_volume": current_volume,
            "ratio": volume_ratio,
            "trend": volume_trend,
            "vpt_trend": vpt_trend,
            "is_high_volume": volume_ratio > 1.5,
            "is_increasing": volume_trend > 1.2
        }
    
    def _analyze_momentum(self, indicators: Dict) -> Dict:
        """Analizar momentum del mercado"""
        
        current_rsi = indicators['rsi'].iloc[-1]
        macd_line = indicators['macd'].iloc[-1]
        macd_signal = indicators['macd_signal'].iloc[-1]
        macd_histogram = macd_line - macd_signal
        
        # Score de momentum combinado
        rsi_score = 0.5  # Neutral en 50
        if current_rsi > 70:
            rsi_score = 1.0  # Fuerte alcista
        elif current_rsi > 60:
            rsi_score = 0.75
        elif current_rsi < 30:
            rsi_score = 0.0  # Fuerte bajista
        elif current_rsi < 40:
            rsi_score = 0.25
        
        # MACD score
        macd_score = 0.5
        if macd_line > macd_signal and macd_histogram > 0:
            macd_score = min(1.0, 0.5 + abs(macd_histogram) * 100)
        elif macd_line < macd_signal and macd_histogram < 0:
            macd_score = max(0.0, 0.5 - abs(macd_histogram) * 100)
        
        # Score combinado
        momentum_score = (rsi_score * 0.6) + (macd_score * 0.4)
        
        return {
            "rsi": current_rsi,
            "macd_histogram": macd_histogram,
            "rsi_score": rsi_score,
            "macd_score": macd_score,
            "score": momentum_score,
            "is_strong": momentum_score > 0.7 or momentum_score < 0.3,
            "direction": "bullish" if momentum_score > 0.6 else "bearish" if momentum_score < 0.4 else "neutral"
        }
    
    def _determine_regime(self, vol_analysis: Dict, trend_analysis: Dict, 
                         volume_analysis: Dict, momentum_analysis: Dict) -> MarketRegime:
        """Determinar el régimen de mercado actual"""
        
        # Prioridad: Volatilidad extrema
        if vol_analysis["is_high_volatility"] and volume_analysis["is_high_volume"]:
            if trend_analysis["is_trending"]:
                return MarketRegime.BREAKOUT
            else:
                return MarketRegime.HIGH_VOLATILITY
        
        if vol_analysis["is_low_volatility"] and not trend_analysis["is_trending"]:
            return MarketRegime.LOW_VOLATILITY
        
        # Tendencias claras
        if trend_analysis["is_trending"]:
            if trend_analysis["direction"] == "bullish":
                return MarketRegime.TRENDING_BULL
            elif trend_analysis["direction"] == "bearish":
                return MarketRegime.TRENDING_BEAR
        
        # Breakout con volumen
        if (volume_analysis["ratio"] > 2.0 and momentum_analysis["is_strong"] and 
            vol_analysis["bb_expansion"] > 1.3):
            return MarketRegime.BREAKOUT
        
        # Consolidación
        if (not vol_analysis["is_high_volatility"] and not trend_analysis["is_trending"] and 
            vol_analysis["percentile"] > 0.2):
            return MarketRegime.CONSOLIDATION
        
        # Por defecto: Sideways
        return MarketRegime.SIDEWAYS
    
    def _calculate_confidence(self, vol_analysis: Dict, trend_analysis: Dict,
                            volume_analysis: Dict, momentum_analysis: Dict) -> float:
        """Calcular confianza en el análisis de régimen"""
        
        confidence_factors = []
        
        # Confianza por volatilidad
        if vol_analysis["is_high_volatility"] or vol_analysis["is_low_volatility"]:
            confidence_factors.append(0.8)  # Volatilidad extrema es clara
        else:
            confidence_factors.append(0.5)
        
        # Confianza por tendencia
        if trend_analysis["is_trending"]:
            confidence_factors.append(min(0.9, 0.5 + trend_analysis["consistency"]))
        else:
            confidence_factors.append(0.3)
        
        # Confianza por volumen
        if volume_analysis["is_high_volume"]:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.4)
        
        # Confianza por momentum
        if momentum_analysis["is_strong"]:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.4)
        
        # Promedio ponderado
        return sum(confidence_factors) / len(confidence_factors)
    
    def _determine_suitable_strategies(self, regime: MarketRegime, confidence: float) -> List[str]:
        """Determinar estrategias adecuadas para el régimen actual"""
        
        strategy_map = {
            MarketRegime.HIGH_VOLATILITY: ["scalping_adaptive", "hybrid_adaptive"],
            MarketRegime.TRENDING_BULL: ["swing_adaptive", "hybrid_adaptive"],
            MarketRegime.TRENDING_BEAR: ["swing_adaptive", "hybrid_adaptive"],
            MarketRegime.BREAKOUT: ["scalping_adaptive", "hybrid_adaptive"],
            MarketRegime.CONSOLIDATION: ["hybrid_adaptive"],
            MarketRegime.LOW_VOLATILITY: ["hybrid_adaptive"],
            MarketRegime.SIDEWAYS: ["hybrid_adaptive"] if confidence > 0.7 else []
        }
        
        return strategy_map.get(regime, ["hybrid_adaptive"])
    
    def _get_default_condition(self) -> MarketCondition:
        """Condición por defecto en caso de error"""
        
        return MarketCondition(
            regime=MarketRegime.CONSOLIDATION,
            volatility_percentile=0.5,
            trend_strength=0.3,
            volume_ratio=1.0,
            momentum_score=0.5,
            suitable_strategies=["hybrid_adaptive"],
            confidence=0.3
        )

if __name__ == "__main__":
    # Test del sistema dinámico
    system = V3DynamicSystem()
    logger.info("🚀 Sistema V3 Dinámico inicializado correctamente")
