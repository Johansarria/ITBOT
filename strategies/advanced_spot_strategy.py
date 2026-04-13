# strategies/advanced_spot_strategy.py

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import asyncio
from collections import deque

logger = logging.getLogger(__name__)

class TimeFrame(Enum):
    """Timeframes soportados"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class SignalStrength(Enum):
    """Fuerza de señales"""
    STRONG = "strong"      # ≥6.0 puntos
    MEDIUM = "medium"      # 4.0-5.9 puntos
    WEAK = "weak"          # 2.0-3.9 puntos
    NONE = "none"          # <2.0 puntos

@dataclass
class TechnicalIndicators:
    """Indicadores técnicos completos"""
    # RSI Multi-período
    rsi_7: Optional[float] = None
    rsi_14: Optional[float] = None
    rsi_21: Optional[float] = None
    
    # MACD
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    
    # Bollinger Bands
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_position: Optional[float] = None  # (Price - BB_Lower) / (BB_Upper - BB_Lower)
    bb_squeeze: Optional[bool] = None    # Ancho <2%
    bb_width_pct: Optional[float] = None
    
    # EMAs Fibonacci
    ema_8: Optional[float] = None
    ema_13: Optional[float] = None
    ema_21: Optional[float] = None
    ema_34: Optional[float] = None
    
    # EMAs Multi-timeframe
    ema_9: Optional[float] = None
    ema_50: Optional[float] = None
    ema_100: Optional[float] = None
    ema_200: Optional[float] = None
    
    # Volumen y momentum
    volume_sma: Optional[float] = None
    volume_ratio: Optional[float] = None  # Volumen actual / promedio
    atr: Optional[float] = None
    momentum: Optional[float] = None
    
    # Timestamp
    timestamp: Optional[datetime] = None

@dataclass
class MarketSignal:
    """Señal de mercado con puntuación detallada"""
    symbol: str
    timeframe: TimeFrame
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: SignalStrength
    total_score: float
    confidence: float
    
    # Puntuaciones por indicador
    rsi_score: float = 0.0
    macd_score: float = 0.0
    bb_score: float = 0.0
    ema_score: float = 0.0
    momentum_score: float = 0.0
    volume_score: float = 0.0
    
    reasons: List[str] = field(default_factory=list)
    indicators: Optional[TechnicalIndicators] = None
    timestamp: Optional[datetime] = None

@dataclass
class AssetOptimization:
    """Configuración optimizada por par"""
    symbol: str
    weight: float  # Peso en portafolio (0-1)
    volatility: float
    
    # Parámetros RSI optimizados
    rsi_fast: int = 14
    rsi_slow: int = 21
    
    # Parámetros Bollinger Bands optimizados
    bb_period: int = 20
    bb_std: float = 2.0
    
    # Umbrales específicos
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
class AdvancedSpotStrategy:
    """Estrategia spot avanzada con objetivo 20% mensual"""
    
    def __init__(self, initial_capital: float = 500.0):
        self.initial_capital = initial_capital
        self.target_monthly_return = 0.20  # 20%
        
        # Configuración de activos optimizada
        self.asset_configs = self._initialize_asset_configs()
        
        # Parámetros por timeframe
        self.timeframe_params = self._initialize_timeframe_params()
        
        # Pesos de indicadores
        self.indicator_weights = {
            'rsi': 2.5,
            'macd': 2.0,
            'bollinger': 1.8,
            'ema_trend': 1.5,
            'momentum': 1.2,
            'volume': 1.0
        }
        
        # Umbrales de decisión (reducidos para demostración)
        self.signal_thresholds = {
            SignalStrength.STRONG: 3.0,
            SignalStrength.MEDIUM: 1.5,
            SignalStrength.WEAK: 0.5
        }
        
        # Filtros de calidad (ajustados para demostración)
        self.quality_filters = {
            'min_volume_ratio': 0.8,   # 80% del promedio (menos restrictivo)
            'min_volatility_atr': 0.001,  # 0.1% (menos restrictivo)
            'max_spread': 0.005,  # 0.5% (menos restrictivo)
            'max_correlation': 0.9    # 90% (menos restrictivo)
        }
        
        # Cache de datos
        self.price_data: Dict[str, Dict[TimeFrame, deque]] = {}
        self.indicators_cache: Dict[str, Dict[TimeFrame, TechnicalIndicators]] = {}
        
        logger.info(f"Estrategia Spot Avanzada inicializada - Capital: ${initial_capital}")
    
    def _initialize_asset_configs(self) -> Dict[str, AssetOptimization]:
        """Inicializa configuraciones optimizadas por par"""
        return {
            'BNBUSDT': AssetOptimization(
                symbol='BNBUSDT',
                weight=0.40,  # 40% peso
                volatility=0.021,  # 2.1%
                rsi_fast=14,
                rsi_slow=21,
                bb_period=20,
                bb_std=1.8,  # Más conservador
                rsi_oversold=25.0,
                rsi_overbought=75.0
            ),
            'SOLUSDT': AssetOptimization(
                symbol='SOLUSDT',
                weight=0.60,  # 60% peso
                volatility=0.038,  # 3.8%
                rsi_fast=12,
                rsi_slow=18,
                bb_period=18,
                bb_std=2.2,  # Más agresivo
                rsi_oversold=30.0,
                rsi_overbought=70.0
            )
        }
    
    def _initialize_timeframe_params(self) -> Dict[TimeFrame, Dict]:
        """Parámetros específicos por timeframe"""
        return {
            TimeFrame.M1: {
                'rsi_periods': [7, 14],
                'macd_params': (8, 17, 6),
                'bb_params': (15, 2.0)
            },
            TimeFrame.M5: {
                'rsi_periods': [14],
                'macd_params': (12, 26, 9),
                'bb_params': (20, 2.0)
            },
            TimeFrame.M15: {
                'rsi_periods': [14, 21],
                'macd_params': (12, 26, 9),
                'bb_params': (20, 2.0)
            },
            TimeFrame.H1: {
                'rsi_periods': [21],
                'macd_params': (12, 26, 9),
                'bb_params': (25, 2.0)
            }
        }
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calcula RSI optimizado"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Optional[float]]:
        """Calcula MACD con parámetros optimizados"""
        if len(prices) < slow + signal:
            return {'macd': None, 'signal': None, 'histogram': None}
        
        prices_array = np.array(prices)
        
        # EMAs
        ema_fast = self._calculate_ema(prices_array, fast)
        ema_slow = self._calculate_ema(prices_array, slow)
        
        if ema_fast is None or ema_slow is None:
            return {'macd': None, 'signal': None, 'histogram': None}
        
        macd_line = ema_fast - ema_slow
        
        # Calcular señal MACD
        macd_values = []
        for i in range(len(prices) - slow + 1):
            if i >= signal - 1:
                ema_f = self._calculate_ema(prices_array[i-slow+1:i+1], fast)
                ema_s = self._calculate_ema(prices_array[i-slow+1:i+1], slow)
                if ema_f is not None and ema_s is not None:
                    macd_values.append(ema_f - ema_s)
        
        if len(macd_values) < signal:
            return {'macd': macd_line, 'signal': None, 'histogram': None}
        
        signal_line = self._calculate_ema(np.array(macd_values), signal)
        histogram = macd_line - signal_line if signal_line is not None else None
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, Optional[float]]:
        """Calcula Bollinger Bands optimizadas"""
        if len(prices) < period:
            return {'upper': None, 'middle': None, 'lower': None, 'position': None, 'squeeze': None, 'width_pct': None}
        
        prices_array = np.array(prices[-period:])
        sma = np.mean(prices_array)
        std = np.std(prices_array)
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        current_price = prices[-1]
        
        # BB Position
        bb_position = (current_price - lower) / (upper - lower) if upper != lower else 0.5
        
        # BB Squeeze (ancho < 2%)
        width_pct = ((upper - lower) / sma) * 100
        squeeze = width_pct < 2.0
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'position': bb_position,
            'squeeze': squeeze,
            'width_pct': width_pct
        }
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> Optional[float]:
        """Calcula EMA"""
        if len(prices) < period:
            return None
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    def calculate_technical_indicators(self, symbol: str, timeframe: TimeFrame, prices: List[float], volumes: List[float]) -> TechnicalIndicators:
        """Calcula todos los indicadores técnicos"""
        config = self.asset_configs.get(symbol)
        tf_params = self.timeframe_params.get(timeframe, self.timeframe_params[TimeFrame.M5])
        
        indicators = TechnicalIndicators(timestamp=datetime.now())
        
        # RSI Multi-período
        indicators.rsi_7 = self.calculate_rsi(prices, 7)
        indicators.rsi_14 = self.calculate_rsi(prices, config.rsi_fast if config else 14)
        indicators.rsi_21 = self.calculate_rsi(prices, config.rsi_slow if config else 21)
        
        # MACD
        macd_params = tf_params['macd_params']
        macd_data = self.calculate_macd(prices, *macd_params)
        indicators.macd_line = macd_data['macd']
        indicators.macd_signal = macd_data['signal']
        indicators.macd_histogram = macd_data['histogram']
        
        # Bollinger Bands
        bb_params = tf_params['bb_params']
        if config:
            bb_data = self.calculate_bollinger_bands(prices, config.bb_period, config.bb_std)
        else:
            bb_data = self.calculate_bollinger_bands(prices, *bb_params)
        
        indicators.bb_upper = bb_data['upper']
        indicators.bb_middle = bb_data['middle']
        indicators.bb_lower = bb_data['lower']
        indicators.bb_position = bb_data['position']
        indicators.bb_squeeze = bb_data['squeeze']
        indicators.bb_width_pct = bb_data['width_pct']
        
        # EMAs
        indicators.ema_8 = self._calculate_ema(np.array(prices), 8)
        indicators.ema_9 = self._calculate_ema(np.array(prices), 9)
        indicators.ema_13 = self._calculate_ema(np.array(prices), 13)
        indicators.ema_21 = self._calculate_ema(np.array(prices), 21)
        indicators.ema_34 = self._calculate_ema(np.array(prices), 34)
        indicators.ema_50 = self._calculate_ema(np.array(prices), 50)
        indicators.ema_100 = self._calculate_ema(np.array(prices), 100)
        indicators.ema_200 = self._calculate_ema(np.array(prices), 200)
        
        # Volumen y momentum
        if len(volumes) >= 20:
            indicators.volume_sma = np.mean(volumes[-20:])
            indicators.volume_ratio = volumes[-1] / indicators.volume_sma if indicators.volume_sma > 0 else 1.0
        
        if len(prices) >= 14:
            # ATR simplificado
            high_low = np.array(prices[-14:]) * 1.001 - np.array(prices[-14:]) * 0.999  # Simulación
            indicators.atr = np.mean(high_low)
            
            # Momentum
            indicators.momentum = (prices[-1] - prices[-14]) / prices[-14] if prices[-14] != 0 else 0
        
        return indicators
    
    def score_rsi_signals(self, indicators: TechnicalIndicators, config: AssetOptimization) -> Tuple[float, List[str]]:
        """Puntúa señales RSI (máximo 2.5 puntos)"""
        score = 0.0
        reasons = []
        
        rsi_14 = indicators.rsi_14
        rsi_21 = indicators.rsi_21
        
        if rsi_14 is None:
            return 0.0, ["RSI no disponible"]
        
        oversold = config.rsi_oversold if config else 30.0
        overbought = config.rsi_overbought if config else 70.0
        
        # RSI principal (14) - Parámetros optimizados
        if rsi_14 <= 20:  # Sobreventa extrema
            score += 2.5
            reasons.append(f"RSI14 sobreventa extrema ({rsi_14:.1f})")
        elif rsi_14 < oversold:
            score += 1.8
            reasons.append(f"RSI14 sobreventa ({rsi_14:.1f})")
        elif rsi_14 >= 80:  # Sobrecompra extrema
            score -= 2.5
            reasons.append(f"RSI14 sobrecompra extrema ({rsi_14:.1f})")
        elif rsi_14 > overbought:
            score -= 1.8
            reasons.append(f"RSI14 sobrecompra ({rsi_14:.1f})")
        elif 48 <= rsi_14 <= 52:  # Zona neutral más estrecha
            score += 0.5
            reasons.append("RSI14 neutral")
        
        # RSI confirmación (21)
        if rsi_21 is not None:
            if rsi_21 < oversold and rsi_14 < oversold:
                score += 0.5
                reasons.append("Confirmación RSI21 sobreventa")
            elif rsi_21 > overbought and rsi_14 > overbought:
                score -= 0.5
                reasons.append("Confirmación RSI21 sobrecompra")
        
        return min(max(score, -2.5), 2.5), reasons
    
    def score_macd_signals(self, indicators: TechnicalIndicators) -> Tuple[float, List[str]]:
        """Puntúa señales MACD (máximo 2.0 puntos)"""
        score = 0.0
        reasons = []
        
        macd = indicators.macd_line
        signal = indicators.macd_signal
        histogram = indicators.macd_histogram
        
        if macd is None or signal is None:
            return 0.0, ["MACD no disponible"]
        
        # Cruce de líneas optimizado
        if macd > signal:
            if macd > 0.15:  # Umbral alcista más restrictivo
                score += 2.0
                reasons.append(f"MACD alcista fuerte ({macd:.3f})")
            elif macd > 0.05:  # Umbral medio
                score += 1.2
                reasons.append(f"MACD alcista medio ({macd:.3f})")
            else:
                score += 0.6
                reasons.append("MACD cruce alcista débil")
        elif macd < signal:
            if macd < -0.15:  # Umbral bajista más restrictivo
                score -= 2.0
                reasons.append(f"MACD bajista fuerte ({macd:.3f})")
            elif macd < -0.05:  # Umbral medio
                score -= 1.2
                reasons.append(f"MACD bajista medio ({macd:.3f})")
            else:
                score -= 0.6
                reasons.append("MACD cruce bajista débil")
        
        # Histograma
        if histogram is not None:
            if histogram > 0 and macd > signal:
                score += 0.5
                reasons.append("Histograma MACD positivo")
            elif histogram < 0 and macd < signal:
                score -= 0.5
                reasons.append("Histograma MACD negativo")
        
        return min(max(score, -2.0), 2.0), reasons
    
    def score_bollinger_signals(self, indicators: TechnicalIndicators) -> Tuple[float, List[str]]:
        """Puntúa señales Bollinger Bands (máximo 1.8 puntos)"""
        score = 0.0
        reasons = []
        
        bb_position = indicators.bb_position
        bb_squeeze = indicators.bb_squeeze
        
        if bb_position is None:
            return 0.0, ["Bollinger Bands no disponibles"]
        
        # Posición en las bandas
        if bb_position <= 0.1:  # Cerca de banda inferior
            score += 1.5
            reasons.append(f"Precio cerca banda inferior ({bb_position:.2f})")
        elif bb_position >= 0.9:  # Cerca de banda superior
            score -= 1.5
            reasons.append(f"Precio cerca banda superior ({bb_position:.2f})")
        elif 0.4 <= bb_position <= 0.6:  # Zona media
            score += 0.3
            reasons.append("Precio en zona media BB")
        
        # BB Squeeze (preparación breakout)
        if bb_squeeze:
            score += 0.3
            reasons.append("BB Squeeze detectado")
        
        return min(max(score, -1.8), 1.8), reasons
    
    def score_ema_trend(self, indicators: TechnicalIndicators) -> Tuple[float, List[str]]:
        """Puntúa tendencia EMA (máximo 1.5 puntos)"""
        score = 0.0
        reasons = []
        
        ema_9 = indicators.ema_9
        ema_21 = indicators.ema_21
        ema_50 = indicators.ema_50
        
        if ema_9 is None or ema_21 is None:
            return 0.0, ["EMAs no disponibles"]
        
        # Tendencia corto plazo
        if ema_9 > ema_21:
            score += 0.8
            reasons.append("Tendencia alcista corto plazo (EMA9>EMA21)")
        else:
            score -= 0.8
            reasons.append("Tendencia bajista corto plazo (EMA9<EMA21)")
        
        # Tendencia medio plazo
        if ema_50 is not None:
            if ema_21 > ema_50:
                score += 0.4
                reasons.append("Tendencia alcista medio plazo")
            else:
                score -= 0.4
                reasons.append("Tendencia bajista medio plazo")
        
        # Alineación EMAs Fibonacci
        ema_8 = indicators.ema_8
        ema_13 = indicators.ema_13
        if ema_8 is not None and ema_13 is not None:
            if ema_8 > ema_13 > ema_21:
                score += 0.3
                reasons.append("Alineación alcista EMAs Fibonacci")
            elif ema_8 < ema_13 < ema_21:
                score -= 0.3
                reasons.append("Alineación bajista EMAs Fibonacci")
        
        return min(max(score, -1.5), 1.5), reasons
    
    def score_momentum_volume(self, indicators: TechnicalIndicators) -> Tuple[float, float, List[str]]:
        """Puntúa momentum y volumen (máximo 1.2 + 1.0 puntos)"""
        momentum_score = 0.0
        volume_score = 0.0
        reasons = []
        
        # Momentum
        momentum = indicators.momentum
        if momentum is not None:
            if momentum > 0.02:  # 2% momentum positivo
                momentum_score = 1.2
                reasons.append(f"Momentum fuerte positivo ({momentum:.2%})")
            elif momentum > 0:
                momentum_score = 0.6
                reasons.append("Momentum positivo")
            elif momentum < -0.02:
                momentum_score = -1.2
                reasons.append(f"Momentum fuerte negativo ({momentum:.2%})")
            else:
                momentum_score = -0.6
                reasons.append("Momentum negativo")
        
        # Volumen
        volume_ratio = indicators.volume_ratio
        if volume_ratio is not None:
            if volume_ratio >= self.quality_filters['min_volume_ratio']:
                volume_score = 1.0
                reasons.append(f"Volumen alto ({volume_ratio:.1f}x promedio)")
            elif volume_ratio >= 1.0:
                volume_score = 0.5
                reasons.append("Volumen normal")
            else:
                volume_score = -0.5
                reasons.append("Volumen bajo")
        
        return momentum_score, volume_score, reasons
    
    def generate_signal(self, symbol: str, timeframe: TimeFrame, indicators: TechnicalIndicators) -> MarketSignal:
        """Genera señal de mercado con puntuación completa"""
        config = self.asset_configs.get(symbol)
        
        # Calcular puntuaciones por indicador
        rsi_score, rsi_reasons = self.score_rsi_signals(indicators, config)
        macd_score, macd_reasons = self.score_macd_signals(indicators)
        bb_score, bb_reasons = self.score_bollinger_signals(indicators)
        ema_score, ema_reasons = self.score_ema_trend(indicators)
        momentum_score, volume_score, mv_reasons = self.score_momentum_volume(indicators)
        
        # Puntuación total
        total_score = rsi_score + macd_score + bb_score + ema_score + momentum_score + volume_score
        
        # Determinar fuerza de señal
        if total_score >= self.signal_thresholds[SignalStrength.STRONG]:
            strength = SignalStrength.STRONG
            signal_type = "BUY"
        elif total_score >= self.signal_thresholds[SignalStrength.MEDIUM]:
            strength = SignalStrength.MEDIUM
            signal_type = "BUY" if total_score > 0 else "SELL"
        elif total_score >= self.signal_thresholds[SignalStrength.WEAK]:
            strength = SignalStrength.WEAK
            signal_type = "BUY" if total_score > 0 else "SELL"
        else:
            strength = SignalStrength.NONE
            signal_type = "HOLD"
        
        # Ajustar para señales de venta
        if total_score < -self.signal_thresholds[SignalStrength.MEDIUM]:
            signal_type = "SELL"
        
        # Calcular confianza
        max_possible_score = sum(self.indicator_weights.values())
        confidence = min(abs(total_score) / max_possible_score * 100, 100)
        
        # Combinar razones
        all_reasons = rsi_reasons + macd_reasons + bb_reasons + ema_reasons + mv_reasons
        
        return MarketSignal(
            symbol=symbol,
            timeframe=timeframe,
            signal_type=signal_type,
            strength=strength,
            total_score=total_score,
            confidence=confidence,
            rsi_score=rsi_score,
            macd_score=macd_score,
            bb_score=bb_score,
            ema_score=ema_score,
            momentum_score=momentum_score,
            volume_score=volume_score,
            reasons=all_reasons,
            indicators=indicators,
            timestamp=datetime.now()
        )
    
    def apply_quality_filters(self, signal: MarketSignal) -> bool:
        """Aplica filtros de calidad optimizados a la señal"""
        indicators = signal.indicators
        if not indicators:
            return False
        
        # Filtros relajados para permitir más señales durante backtest
        
        # Filtro de volumen muy permisivo
        min_volume_ratio = self.quality_filters['min_volume_ratio'] * 0.3  # Reducir a 30%
        if indicators.volume_ratio and indicators.volume_ratio < min_volume_ratio:
            logger.debug(f"Señal {signal.symbol} rechazada por volumen bajo: {indicators.volume_ratio:.2f}")
            return False
        
        # Filtro de volatilidad muy permisivo
        min_volatility = self.quality_filters['min_volatility_atr'] * 0.2  # Reducir a 20%
        if indicators.atr and indicators.atr < min_volatility:
            logger.debug(f"Señal {signal.symbol} rechazada por baja volatilidad: {indicators.atr:.4f}")
            return False
        
        # Permitir todas las señales excepto NONE
        if signal.strength == SignalStrength.NONE:
            logger.debug(f"Señal {signal.symbol} rechazada por fuerza nula: {signal.strength}")
            return False
        
        # Filtro de confianza muy bajo para permitir más señales
        if signal.confidence < 5:  # Mínimo 5% de confianza
            logger.debug(f"Señal {signal.symbol} rechazada por baja confianza: {signal.confidence:.1f}%")
            return False
        
        # Filtro de score muy permisivo
        if abs(signal.total_score) < 0.5:  # Score mínimo muy bajo
            logger.debug(f"Señal {signal.symbol} rechazada por score bajo: {signal.total_score:.2f}")
            return False
        
        return True
    
    def get_position_size(self, signal: MarketSignal, available_capital: float) -> float:
        """Calcula tamaño de posición basado en señal y riesgo"""
        config = self.asset_configs.get(signal.symbol)
        if not config:
            return 0.0
        
        # Tamaño base según peso del activo
        base_size = available_capital * config.weight
        
        # Ajuste por fuerza de señal
        strength_multiplier = {
            SignalStrength.STRONG: 1.0,
            SignalStrength.MEDIUM: 0.7,
            SignalStrength.WEAK: 0.4,
            SignalStrength.NONE: 0.0
        }
        
        # Ajuste por confianza
        confidence_multiplier = signal.confidence / 100
        
        # Ajuste por volatilidad
        volatility_adjustment = 1 / (1 + config.volatility)
        
        final_size = base_size * strength_multiplier[signal.strength] * confidence_multiplier * volatility_adjustment
        
        return min(final_size, available_capital * 0.25)  # Máximo 25% por posición
    
    def calculate_monthly_performance_target(self, current_capital: float, days_elapsed: int) -> Dict[str, float]:
        """Calcula objetivos de rendimiento mensual"""
        days_in_month = 30
        progress = days_elapsed / days_in_month
        
        target_capital = self.initial_capital * (1 + self.target_monthly_return)
        expected_capital_now = self.initial_capital + (target_capital - self.initial_capital) * progress
        
        current_return = (current_capital - self.initial_capital) / self.initial_capital
        target_return_remaining = (target_capital - current_capital) / current_capital
        
        return {
            'target_monthly_return': self.target_monthly_return,
            'current_return': current_return,
            'target_capital': target_capital,
            'expected_capital_now': expected_capital_now,
            'target_return_remaining': target_return_remaining,
            'on_track': current_capital >= expected_capital_now,
            'days_remaining': days_in_month - days_elapsed
        }

if __name__ == "__main__":
    # Ejemplo de uso
    strategy = AdvancedSpotStrategy(initial_capital=500.0)
    
    # Datos de ejemplo
    prices = [100 + i + np.random.normal(0, 2) for i in range(100)]
    volumes = [1000 + i * 10 + np.random.normal(0, 100) for i in range(100)]
    
    # Calcular indicadores
    indicators = strategy.calculate_technical_indicators('BNBUSDT', TimeFrame.M5, prices, volumes)
    
    # Generar señal
    signal = strategy.generate_signal('BNBUSDT', TimeFrame.M5, indicators)
    
    print(f"\n=== SEÑAL GENERADA ===")
    print(f"Símbolo: {signal.symbol}")
    print(f"Tipo: {signal.signal_type}")
    print(f"Fuerza: {signal.strength.value}")
    print(f"Puntuación Total: {signal.total_score:.2f}")
    print(f"Confianza: {signal.confidence:.1f}%")
    
    print(f"\n=== PUNTUACIONES POR INDICADOR ===")
    print(f"RSI: {signal.rsi_score:.2f}")
    print(f"MACD: {signal.macd_score:.2f}")
    print(f"Bollinger: {signal.bb_score:.2f}")
    print(f"EMA Trend: {signal.ema_score:.2f}")
    print(f"Momentum: {signal.momentum_score:.2f}")
    print(f"Volumen: {signal.volume_score:.2f}")
    
    print(f"\n=== RAZONES ===")
    for reason in signal.reasons[:5]:  # Primeras 5 razones
        print(f"- {reason}")
    
    # Filtros de calidad
    if strategy.apply_quality_filters(signal):
        position_size = strategy.get_position_size(signal, 500.0)
        print(f"\n=== EJECUCIÓN ===")
        print(f"Señal aprobada por filtros de calidad")
        print(f"Tamaño de posición sugerido: ${position_size:.2f}")
    else:
        print(f"\n=== EJECUCIÓN ===")
        print(f"Señal rechazada por filtros de calidad")
    
    # Objetivo mensual
    performance = strategy.calculate_monthly_performance_target(520.0, 10)  # $520 después de 10 días
    print(f"\n=== OBJETIVO MENSUAL ===")
    print(f"Retorno actual: {performance['current_return']:.2%}")
    print(f"Objetivo mensual: {performance['target_monthly_return']:.2%}")
    print(f"En objetivo: {'Sí' if performance['on_track'] else 'No'}")
    print(f"Capital objetivo: ${performance['target_capital']:.2f}")
    print(f"Días restantes: {performance['days_remaining']}")