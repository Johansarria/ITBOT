# strategies/multi_timeframe_analyzer.py

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import asyncio
from collections import defaultdict, deque
import json
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class TimeFrame(Enum):
    """Marcos temporales soportados"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class SignalStrength(Enum):
    """Fuerza de señal"""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    NEUTRAL = "neutral"

@dataclass
class TimeFrameConfig:
    """Configuración específica por timeframe"""
    timeframe: TimeFrame
    
    # RSI
    rsi_fast: int = 14
    rsi_slow: int = 21
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    macd_threshold_bull: float = 0.1
    macd_threshold_bear: float = -0.1
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    bb_squeeze_threshold: float = 2.0
    
    # EMAs
    ema_fast: int = 9
    ema_slow: int = 21
    ema_trend: int = 50
    ema_long: int = 100
    ema_very_long: int = 200
    
    # Pesos específicos del timeframe
    weight_multiplier: float = 1.0
    
    # Filtros de calidad
    min_volume_multiplier: float = 1.2
    min_volatility_atr: float = 0.005
    max_spread_pct: float = 0.001
    
    @classmethod
    def get_default_configs(cls) -> Dict[TimeFrame, 'TimeFrameConfig']:
        """Configuraciones por defecto optimizadas por timeframe"""
        return {
            TimeFrame.M1: cls(
                timeframe=TimeFrame.M1,
                rsi_fast=7, rsi_slow=14,
                macd_fast=8, macd_slow=17, macd_signal=6,
                bb_period=15, bb_std=2.0,
                ema_fast=5, ema_slow=13, ema_trend=21,
                weight_multiplier=0.5,  # Menor peso para 1m
                min_volume_multiplier=1.5,
                min_volatility_atr=0.002
            ),
            TimeFrame.M5: cls(
                timeframe=TimeFrame.M5,
                rsi_fast=14, rsi_slow=21,
                macd_fast=12, macd_slow=26, macd_signal=9,
                bb_period=20, bb_std=2.0,
                ema_fast=9, ema_slow=21, ema_trend=50,
                weight_multiplier=1.0,  # Peso base
                min_volume_multiplier=1.2,
                min_volatility_atr=0.005
            ),
            TimeFrame.M15: cls(
                timeframe=TimeFrame.M15,
                rsi_fast=14, rsi_slow=21,
                macd_fast=12, macd_slow=26, macd_signal=9,
                bb_period=20, bb_std=2.0,
                ema_fast=9, ema_slow=21, ema_trend=50,
                weight_multiplier=1.2,  # Mayor peso
                min_volume_multiplier=1.1,
                min_volatility_atr=0.008
            ),
            TimeFrame.H1: cls(
                timeframe=TimeFrame.H1,
                rsi_fast=21, rsi_slow=35,
                macd_fast=12, macd_slow=26, macd_signal=9,
                bb_period=25, bb_std=2.0,
                ema_fast=9, ema_slow=21, ema_trend=50,
                weight_multiplier=1.5,  # Alto peso para tendencia
                min_volume_multiplier=1.0,
                min_volatility_atr=0.01
            ),
            TimeFrame.H4: cls(
                timeframe=TimeFrame.H4,
                rsi_fast=21, rsi_slow=35,
                macd_fast=12, macd_slow=26, macd_signal=9,
                bb_period=25, bb_std=2.0,
                ema_fast=9, ema_slow=21, ema_trend=50,
                weight_multiplier=2.0,  # Muy alto peso
                min_volume_multiplier=0.8,
                min_volatility_atr=0.015
            ),
            TimeFrame.D1: cls(
                timeframe=TimeFrame.D1,
                rsi_fast=14, rsi_slow=21,
                macd_fast=12, macd_slow=26, macd_signal=9,
                bb_period=20, bb_std=2.0,
                ema_fast=9, ema_slow=21, ema_trend=50,
                weight_multiplier=3.0,  # Máximo peso para tendencia principal
                min_volume_multiplier=0.5,
                min_volatility_atr=0.02
            )
        }

@dataclass
class TimeFrameSignal:
    """Señal de un timeframe específico"""
    timeframe: TimeFrame
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: SignalStrength
    score: float
    confidence: float
    
    # Componentes de la señal
    rsi_signal: float = 0.0
    macd_signal: float = 0.0
    bb_signal: float = 0.0
    ema_signal: float = 0.0
    momentum_signal: float = 0.0
    volume_signal: float = 0.0
    
    # Indicadores calculados
    rsi_value: Optional[float] = None
    macd_value: Optional[float] = None
    bb_position: Optional[float] = None
    ema_trend: Optional[str] = None
    
    # Filtros de calidad
    volume_filter_passed: bool = True
    volatility_filter_passed: bool = True
    spread_filter_passed: bool = True
    
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class MultiTimeFrameSignal:
    """Señal combinada de múltiples timeframes"""
    symbol: str
    overall_signal: str  # 'BUY', 'SELL', 'HOLD'
    overall_strength: SignalStrength
    overall_score: float
    overall_confidence: float
    
    # Señales por timeframe
    timeframe_signals: Dict[TimeFrame, TimeFrameSignal] = field(default_factory=dict)
    
    # Análisis de confluencia
    bullish_timeframes: List[TimeFrame] = field(default_factory=list)
    bearish_timeframes: List[TimeFrame] = field(default_factory=list)
    neutral_timeframes: List[TimeFrame] = field(default_factory=list)
    
    # Métricas de calidad
    confluence_score: float = 0.0
    trend_alignment: float = 0.0
    momentum_alignment: float = 0.0
    
    timestamp: datetime = field(default_factory=datetime.now)

class MultiTimeFrameAnalyzer:
    """Analizador multi-timeframe con parámetros específicos"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ["BNBUSDT", "SOLUSDT"]
        
        # Configuraciones por timeframe
        self.timeframe_configs = TimeFrameConfig.get_default_configs()
        
        # Datos históricos por símbolo y timeframe
        self.price_data: Dict[str, Dict[TimeFrame, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=500)))
        self.volume_data: Dict[str, Dict[TimeFrame, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=500)))
        
        # Señales actuales
        self.current_signals: Dict[str, MultiTimeFrameSignal] = {}
        
        # Historial de señales
        self.signal_history: Dict[str, List[MultiTimeFrameSignal]] = defaultdict(list)
        
        # Cache de indicadores
        self.indicator_cache: Dict[str, Dict[TimeFrame, Dict]] = defaultdict(lambda: defaultdict(dict))
        
        # Configuración de pesos por timeframe
        self.timeframe_weights = {
            TimeFrame.M1: 0.5,
            TimeFrame.M5: 1.0,
            TimeFrame.M15: 1.2,
            TimeFrame.H1: 1.5,
            TimeFrame.H4: 2.0,
            TimeFrame.D1: 3.0
        }
        
        # Configuraciones específicas por par
        self.symbol_configs = {
            "BNBUSDT": {
                "weight": 0.4,
                "volatility_adjustment": 0.9,  # Menos volátil
                "rsi_adjustment": 1.1,  # RSI más conservador
                "bb_adjustment": 0.9   # BB más conservador
            },
            "SOLUSDT": {
                "weight": 0.6,
                "volatility_adjustment": 1.2,  # Más volátil
                "rsi_adjustment": 0.9,  # RSI más sensible
                "bb_adjustment": 1.1   # BB más agresivo
            }
        }
        
        logger.info(f"MultiTimeFrameAnalyzer inicializado para {len(self.symbols)} símbolos")
    
    def update_market_data(self, symbol: str, timeframe: TimeFrame, 
                          price: float, volume: float, timestamp: datetime = None):
        """Actualiza datos de mercado para análisis"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Almacenar datos
        self.price_data[symbol][timeframe].append((timestamp, price))
        self.volume_data[symbol][timeframe].append((timestamp, volume))
        
        # Limpiar cache de indicadores
        if symbol in self.indicator_cache and timeframe in self.indicator_cache[symbol]:
            self.indicator_cache[symbol][timeframe].clear()
        
        # Generar nueva señal si hay datos suficientes
        self._generate_signal_for_symbol(symbol)
    
    def _generate_signal_for_symbol(self, symbol: str):
        """Genera señal multi-timeframe para un símbolo"""
        timeframe_signals = {}
        
        # Analizar cada timeframe
        for timeframe in [TimeFrame.M5, TimeFrame.M15, TimeFrame.H1, TimeFrame.H4]:
            if len(self.price_data[symbol][timeframe]) >= 50:  # Datos suficientes
                signal = self._analyze_timeframe(symbol, timeframe)
                if signal:
                    timeframe_signals[timeframe] = signal
        
        if not timeframe_signals:
            return
        
        # Combinar señales
        combined_signal = self._combine_timeframe_signals(symbol, timeframe_signals)
        
        # Actualizar señal actual
        self.current_signals[symbol] = combined_signal
        
        # Agregar al historial
        self.signal_history[symbol].append(combined_signal)
        
        # Mantener historial limitado
        if len(self.signal_history[symbol]) > 100:
            self.signal_history[symbol] = self.signal_history[symbol][-100:]
    
    def _analyze_timeframe(self, symbol: str, timeframe: TimeFrame) -> Optional[TimeFrameSignal]:
        """Analiza un timeframe específico"""
        config = self.timeframe_configs[timeframe]
        symbol_config = self.symbol_configs.get(symbol, {})
        
        # Obtener datos
        prices = [p[1] for p in list(self.price_data[symbol][timeframe])]
        volumes = [v[1] for v in list(self.volume_data[symbol][timeframe])]
        
        if len(prices) < max(config.rsi_slow, config.macd_slow, config.bb_period, config.ema_trend) + 10:
            return None
        
        # Calcular indicadores
        indicators = self._calculate_indicators(symbol, timeframe, prices, volumes, config)
        
        # Aplicar filtros de calidad
        quality_filters = self._apply_quality_filters(symbol, timeframe, prices, volumes, config)
        
        # Calcular señales de cada indicador
        rsi_signal = self._calculate_rsi_signal(indicators['rsi'], config, symbol_config)
        macd_signal = self._calculate_macd_signal(indicators['macd'], config)
        bb_signal = self._calculate_bb_signal(indicators['bb_position'], indicators['bb_squeeze'], config)
        ema_signal = self._calculate_ema_signal(indicators['ema_trend'], config)
        momentum_signal = self._calculate_momentum_signal(indicators['momentum'])
        volume_signal = self._calculate_volume_signal(indicators['volume_profile'])
        
        # Calcular puntuación total
        base_weights = {
            'rsi': 2.5,
            'macd': 2.0,
            'bb': 1.8,
            'ema': 1.5,
            'momentum': 1.2,
            'volume': 1.0
        }
        
        # Aplicar multiplicador de timeframe
        weight_multiplier = config.weight_multiplier
        
        total_score = (
            rsi_signal * base_weights['rsi'] * weight_multiplier +
            macd_signal * base_weights['macd'] * weight_multiplier +
            bb_signal * base_weights['bb'] * weight_multiplier +
            ema_signal * base_weights['ema'] * weight_multiplier +
            momentum_signal * base_weights['momentum'] * weight_multiplier +
            volume_signal * base_weights['volume'] * weight_multiplier
        )
        
        # Determinar tipo de señal y fuerza
        signal_type, strength = self._determine_signal_type_and_strength(total_score, config)
        
        # Calcular confianza
        confidence = self._calculate_confidence(indicators, quality_filters, timeframe)
        
        return TimeFrameSignal(
            timeframe=timeframe,
            signal_type=signal_type,
            strength=strength,
            score=total_score,
            confidence=confidence,
            rsi_signal=rsi_signal,
            macd_signal=macd_signal,
            bb_signal=bb_signal,
            ema_signal=ema_signal,
            momentum_signal=momentum_signal,
            volume_signal=volume_signal,
            rsi_value=indicators['rsi'][-1] if indicators['rsi'] else None,
            macd_value=indicators['macd'][-1] if indicators['macd'] else None,
            bb_position=indicators['bb_position'][-1] if indicators['bb_position'] else None,
            ema_trend=indicators['ema_trend'],
            volume_filter_passed=quality_filters['volume'],
            volatility_filter_passed=quality_filters['volatility'],
            spread_filter_passed=quality_filters['spread']
        )
    
    def _calculate_indicators(self, symbol: str, timeframe: TimeFrame, 
                            prices: List[float], volumes: List[float], 
                            config: TimeFrameConfig) -> Dict[str, Any]:
        """Calcula todos los indicadores técnicos"""
        
        # Verificar cache
        cache_key = f"{len(prices)}_{prices[-1]:.6f}"
        if cache_key in self.indicator_cache[symbol][timeframe]:
            return self.indicator_cache[symbol][timeframe][cache_key]
        
        indicators = {}
        
        # RSI
        indicators['rsi'] = self._calculate_rsi(prices, config.rsi_fast)
        indicators['rsi_slow'] = self._calculate_rsi(prices, config.rsi_slow)
        
        # MACD
        indicators['macd'] = self._calculate_macd(prices, config.macd_fast, config.macd_slow, config.macd_signal)
        
        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(prices, config.bb_period, config.bb_std)
        indicators['bb_upper'] = bb_data['upper']
        indicators['bb_lower'] = bb_data['lower']
        indicators['bb_middle'] = bb_data['middle']
        indicators['bb_position'] = bb_data['position']
        indicators['bb_squeeze'] = bb_data['squeeze']
        
        # EMAs
        indicators['ema_fast'] = self._calculate_ema(prices, config.ema_fast)
        indicators['ema_slow'] = self._calculate_ema(prices, config.ema_slow)
        indicators['ema_trend'] = self._determine_ema_trend(indicators['ema_fast'], indicators['ema_slow'])
        
        # Momentum
        indicators['momentum'] = self._calculate_momentum(prices, 10)
        
        # Volumen
        indicators['volume_profile'] = self._calculate_volume_profile(volumes)
        
        # ATR para volatilidad
        indicators['atr'] = self._calculate_atr(prices, 14)
        
        # Guardar en cache
        self.indicator_cache[symbol][timeframe][cache_key] = indicators
        
        return indicators
    
    def _calculate_rsi(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calcula RSI"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        rsi_values = [None] * len(prices)
        
        # Primer cálculo
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        if avg_loss == 0:
            rsi_values[period] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_values[period] = 100 - (100 / (1 + rs))
        
        # Cálculos subsecuentes (suavizado)
        alpha = 1.0 / period
        for i in range(period + 1, len(prices)):
            gain = gains[i-1] if i-1 < len(gains) else 0
            loss = losses[i-1] if i-1 < len(losses) else 0
            
            avg_gain = alpha * gain + (1 - alpha) * avg_gain
            avg_loss = alpha * loss + (1 - alpha) * avg_loss
            
            if avg_loss == 0:
                rsi_values[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100 - (100 / (1 + rs))
        
        return rsi_values
    
    def _calculate_macd(self, prices: List[float], fast: int, slow: int, signal: int) -> List[Optional[float]]:
        """Calcula MACD"""
        if len(prices) < slow + signal:
            return [None] * len(prices)
        
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        macd_line = []
        for i in range(len(prices)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line.append(ema_fast[i] - ema_slow[i])
            else:
                macd_line.append(None)
        
        return macd_line
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int, std_dev: float) -> Dict[str, List[Optional[float]]]:
        """Calcula Bollinger Bands"""
        upper = [None] * len(prices)
        lower = [None] * len(prices)
        middle = [None] * len(prices)
        position = [None] * len(prices)
        squeeze = [None] * len(prices)
        
        for i in range(period - 1, len(prices)):
            window = prices[i - period + 1:i + 1]
            sma = np.mean(window)
            std = np.std(window)
            
            upper[i] = sma + (std_dev * std)
            lower[i] = sma - (std_dev * std)
            middle[i] = sma
            
            # Posición dentro de las bandas (0-1)
            if upper[i] != lower[i]:
                position[i] = (prices[i] - lower[i]) / (upper[i] - lower[i])
            else:
                position[i] = 0.5
            
            # Squeeze (ancho de bandas como % del precio)
            if prices[i] > 0:
                squeeze[i] = ((upper[i] - lower[i]) / prices[i]) * 100
            else:
                squeeze[i] = 0
        
        return {
            'upper': upper,
            'lower': lower,
            'middle': middle,
            'position': position,
            'squeeze': squeeze
        }
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calcula EMA"""
        if len(prices) < period:
            return [None] * len(prices)
        
        ema_values = [None] * len(prices)
        alpha = 2 / (period + 1)
        
        # Primer valor (SMA)
        ema = np.mean(prices[:period])
        ema_values[period - 1] = ema
        
        # Valores subsecuentes
        for i in range(period, len(prices)):
            ema = alpha * prices[i] + (1 - alpha) * ema
            ema_values[i] = ema
        
        return ema_values
    
    def _determine_ema_trend(self, ema_fast: List[Optional[float]], ema_slow: List[Optional[float]]) -> str:
        """Determina tendencia basada en EMAs"""
        if not ema_fast or not ema_slow or ema_fast[-1] is None or ema_slow[-1] is None:
            return "NEUTRAL"
        
        if ema_fast[-1] > ema_slow[-1]:
            return "BULLISH"
        elif ema_fast[-1] < ema_slow[-1]:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def _calculate_momentum(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calcula momentum"""
        momentum = [None] * len(prices)
        
        for i in range(period, len(prices)):
            momentum[i] = (prices[i] - prices[i - period]) / prices[i - period]
        
        return momentum
    
    def _calculate_volume_profile(self, volumes: List[float]) -> List[Optional[float]]:
        """Calcula perfil de volumen"""
        if len(volumes) < 20:
            return [None] * len(volumes)
        
        profile = [None] * len(volumes)
        
        for i in range(20, len(volumes)):
            avg_volume = np.mean(volumes[i-20:i])
            if avg_volume > 0:
                profile[i] = volumes[i] / avg_volume
            else:
                profile[i] = 1.0
        
        return profile
    
    def _calculate_atr(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calcula Average True Range"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        # Simplificado: usar solo high-low (asumiendo que prices son close)
        ranges = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        
        atr_values = [None] * len(prices)
        
        for i in range(period, len(prices)):
            atr_values[i] = np.mean(ranges[i-period:i])
        
        return atr_values
    
    def _apply_quality_filters(self, symbol: str, timeframe: TimeFrame, 
                             prices: List[float], volumes: List[float], 
                             config: TimeFrameConfig) -> Dict[str, bool]:
        """Aplica filtros de calidad"""
        filters = {
            'volume': True,
            'volatility': True,
            'spread': True
        }
        
        if len(volumes) >= 20:
            # Filtro de volumen
            avg_volume = np.mean(volumes[-20:])
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            filters['volume'] = volume_ratio >= config.min_volume_multiplier
        
        if len(prices) >= 14:
            # Filtro de volatilidad (ATR)
            atr_values = self._calculate_atr(prices, 14)
            if atr_values[-1] is not None:
                atr_pct = atr_values[-1] / prices[-1] if prices[-1] > 0 else 0
                filters['volatility'] = atr_pct >= config.min_volatility_atr
        
        # Filtro de spread (simplificado - asumimos spread bajo)
        filters['spread'] = True  # En producción, usar bid/ask real
        
        return filters
    
    def _calculate_rsi_signal(self, rsi_values: List[Optional[float]], 
                            config: TimeFrameConfig, symbol_config: Dict) -> float:
        """Calcula señal RSI"""
        if not rsi_values or rsi_values[-1] is None:
            return 0.0
        
        rsi = rsi_values[-1]
        
        # Ajustes específicos del símbolo
        rsi_adjustment = symbol_config.get('rsi_adjustment', 1.0)
        oversold = config.rsi_oversold * rsi_adjustment
        overbought = config.rsi_overbought * rsi_adjustment
        
        if rsi < oversold:
            # Señal de compra (sobreventa)
            strength = (oversold - rsi) / oversold
            return min(strength * 2, 1.0)  # Máximo 1.0
        elif rsi > overbought:
            # Señal de venta (sobrecompra)
            strength = (rsi - overbought) / (100 - overbought)
            return max(-strength * 2, -1.0)  # Mínimo -1.0
        else:
            # Zona neutral
            return 0.0
    
    def _calculate_macd_signal(self, macd_values: List[Optional[float]], config: TimeFrameConfig) -> float:
        """Calcula señal MACD"""
        if not macd_values or macd_values[-1] is None:
            return 0.0
        
        macd = macd_values[-1]
        
        if macd > config.macd_threshold_bull:
            # Señal alcista
            strength = min(macd / config.macd_threshold_bull, 3.0) / 3.0
            return strength
        elif macd < config.macd_threshold_bear:
            # Señal bajista
            strength = min(abs(macd) / abs(config.macd_threshold_bear), 3.0) / 3.0
            return -strength
        else:
            return 0.0
    
    def _calculate_bb_signal(self, bb_position: List[Optional[float]], 
                           bb_squeeze: List[Optional[float]], config: TimeFrameConfig) -> float:
        """Calcula señal Bollinger Bands"""
        if not bb_position or bb_position[-1] is None:
            return 0.0
        
        position = bb_position[-1]
        squeeze = bb_squeeze[-1] if bb_squeeze and bb_squeeze[-1] is not None else None
        
        # Señal basada en posición
        if position < 0.2:
            # Cerca del límite inferior (compra)
            signal = (0.2 - position) / 0.2
        elif position > 0.8:
            # Cerca del límite superior (venta)
            signal = -(position - 0.8) / 0.2
        else:
            signal = 0.0
        
        # Amplificar si hay squeeze (preparación para breakout)
        if squeeze is not None and squeeze < config.bb_squeeze_threshold:
            signal *= 1.5
        
        return max(-1.0, min(1.0, signal))
    
    def _calculate_ema_signal(self, ema_trend: str, config: TimeFrameConfig) -> float:
        """Calcula señal EMA"""
        if ema_trend == "BULLISH":
            return 0.8
        elif ema_trend == "BEARISH":
            return -0.8
        else:
            return 0.0
    
    def _calculate_momentum_signal(self, momentum_values: List[Optional[float]]) -> float:
        """Calcula señal de momentum"""
        if not momentum_values or momentum_values[-1] is None:
            return 0.0
        
        momentum = momentum_values[-1]
        
        # Normalizar momentum
        if momentum > 0.05:  # 5% momentum positivo
            return min(momentum / 0.05, 1.0)
        elif momentum < -0.05:  # 5% momentum negativo
            return max(momentum / 0.05, -1.0)
        else:
            return momentum / 0.05  # Escalado lineal
    
    def _calculate_volume_signal(self, volume_profile: List[Optional[float]]) -> float:
        """Calcula señal de volumen"""
        if not volume_profile or volume_profile[-1] is None:
            return 0.0
        
        vol_ratio = volume_profile[-1]
        
        if vol_ratio > 1.5:  # Alto volumen
            return min((vol_ratio - 1.0) / 2.0, 0.5)  # Máximo 0.5
        elif vol_ratio < 0.5:  # Bajo volumen
            return max((vol_ratio - 1.0) / 2.0, -0.5)  # Mínimo -0.5
        else:
            return 0.0
    
    def _determine_signal_type_and_strength(self, score: float, config: TimeFrameConfig) -> Tuple[str, SignalStrength]:
        """Determina tipo y fuerza de señal"""
        abs_score = abs(score)
        
        if abs_score >= config.signal_strong if hasattr(config, 'signal_strong') else 6.0:
            strength = SignalStrength.VERY_STRONG
        elif abs_score >= 4.5:
            strength = SignalStrength.STRONG
        elif abs_score >= 3.0:
            strength = SignalStrength.MEDIUM
        elif abs_score >= 1.5:
            strength = SignalStrength.WEAK
        else:
            strength = SignalStrength.NEUTRAL
        
        if score > 0:
            signal_type = "BUY"
        elif score < 0:
            signal_type = "SELL"
        else:
            signal_type = "HOLD"
        
        return signal_type, strength
    
    def _calculate_confidence(self, indicators: Dict[str, Any], 
                            quality_filters: Dict[str, bool], timeframe: TimeFrame) -> float:
        """Calcula confianza de la señal"""
        confidence = 0.5  # Base
        
        # Filtros de calidad
        quality_score = sum(quality_filters.values()) / len(quality_filters)
        confidence += quality_score * 0.2
        
        # Consistencia de indicadores
        signals = []
        if indicators.get('rsi') and indicators['rsi'][-1] is not None:
            rsi = indicators['rsi'][-1]
            if rsi < 30:
                signals.append(1)
            elif rsi > 70:
                signals.append(-1)
            else:
                signals.append(0)
        
        if indicators.get('macd') and indicators['macd'][-1] is not None:
            macd = indicators['macd'][-1]
            if macd > 0.1:
                signals.append(1)
            elif macd < -0.1:
                signals.append(-1)
            else:
                signals.append(0)
        
        # Consistencia
        if len(signals) > 1:
            consistency = 1.0 - (np.std(signals) / 2.0)  # Normalizado
            confidence += consistency * 0.2
        
        # Peso del timeframe
        timeframe_weight = self.timeframe_weights.get(timeframe, 1.0)
        confidence += (timeframe_weight - 1.0) * 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _combine_timeframe_signals(self, symbol: str, 
                                 timeframe_signals: Dict[TimeFrame, TimeFrameSignal]) -> MultiTimeFrameSignal:
        """Combina señales de múltiples timeframes"""
        
        # Clasificar señales por tipo
        bullish_timeframes = []
        bearish_timeframes = []
        neutral_timeframes = []
        
        weighted_score = 0.0
        total_weight = 0.0
        total_confidence = 0.0
        
        for timeframe, signal in timeframe_signals.items():
            weight = self.timeframe_weights.get(timeframe, 1.0)
            
            if signal.signal_type == "BUY":
                bullish_timeframes.append(timeframe)
            elif signal.signal_type == "SELL":
                bearish_timeframes.append(timeframe)
            else:
                neutral_timeframes.append(timeframe)
            
            # Ponderar por peso del timeframe y confianza
            adjusted_weight = weight * signal.confidence
            weighted_score += signal.score * adjusted_weight
            total_weight += adjusted_weight
            total_confidence += signal.confidence * weight
        
        # Calcular puntuación general
        if total_weight > 0:
            overall_score = weighted_score / total_weight
            overall_confidence = total_confidence / sum(self.timeframe_weights[tf] for tf in timeframe_signals.keys())
        else:
            overall_score = 0.0
            overall_confidence = 0.0
        
        # Determinar señal general
        overall_signal, overall_strength = self._determine_signal_type_and_strength(
            overall_score, self.timeframe_configs[TimeFrame.M5]  # Usar config base
        )
        
        # Calcular métricas de confluencia
        confluence_score = self._calculate_confluence_score(bullish_timeframes, bearish_timeframes, neutral_timeframes)
        trend_alignment = self._calculate_trend_alignment(timeframe_signals)
        momentum_alignment = self._calculate_momentum_alignment(timeframe_signals)
        
        return MultiTimeFrameSignal(
            symbol=symbol,
            overall_signal=overall_signal,
            overall_strength=overall_strength,
            overall_score=overall_score,
            overall_confidence=overall_confidence,
            timeframe_signals=timeframe_signals,
            bullish_timeframes=bullish_timeframes,
            bearish_timeframes=bearish_timeframes,
            neutral_timeframes=neutral_timeframes,
            confluence_score=confluence_score,
            trend_alignment=trend_alignment,
            momentum_alignment=momentum_alignment
        )
    
    def _calculate_confluence_score(self, bullish: List[TimeFrame], 
                                  bearish: List[TimeFrame], neutral: List[TimeFrame]) -> float:
        """Calcula puntuación de confluencia"""
        total_timeframes = len(bullish) + len(bearish) + len(neutral)
        if total_timeframes == 0:
            return 0.0
        
        # Preferir confluencia en una dirección
        max_direction = max(len(bullish), len(bearish))
        confluence = max_direction / total_timeframes
        
        # Bonificar si timeframes importantes están alineados
        important_timeframes = [TimeFrame.H1, TimeFrame.H4, TimeFrame.D1]
        important_aligned = 0
        
        for tf in important_timeframes:
            if tf in bullish or tf in bearish:
                # Verificar si está en la dirección mayoritaria
                if (len(bullish) > len(bearish) and tf in bullish) or \
                   (len(bearish) > len(bullish) and tf in bearish):
                    important_aligned += 1
        
        importance_bonus = important_aligned / len(important_timeframes) * 0.3
        
        return min(1.0, confluence + importance_bonus)
    
    def _calculate_trend_alignment(self, timeframe_signals: Dict[TimeFrame, TimeFrameSignal]) -> float:
        """Calcula alineación de tendencia"""
        ema_trends = []
        
        for signal in timeframe_signals.values():
            if signal.ema_trend == "BULLISH":
                ema_trends.append(1)
            elif signal.ema_trend == "BEARISH":
                ema_trends.append(-1)
            else:
                ema_trends.append(0)
        
        if not ema_trends:
            return 0.0
        
        # Calcular consistencia de tendencia
        trend_consistency = 1.0 - (np.std(ema_trends) / 2.0) if len(ema_trends) > 1 else 1.0
        
        return max(0.0, min(1.0, trend_consistency))
    
    def _calculate_momentum_alignment(self, timeframe_signals: Dict[TimeFrame, TimeFrameSignal]) -> float:
        """Calcula alineación de momentum"""
        momentum_signals = [signal.momentum_signal for signal in timeframe_signals.values()]
        
        if not momentum_signals:
            return 0.0
        
        # Calcular consistencia de momentum
        momentum_consistency = 1.0 - (np.std(momentum_signals) / 2.0) if len(momentum_signals) > 1 else 1.0
        
        return max(0.0, min(1.0, momentum_consistency))
    
    def get_current_signal(self, symbol: str) -> Optional[MultiTimeFrameSignal]:
        """Obtiene señal actual para un símbolo"""
        return self.current_signals.get(symbol)
    
    def get_all_current_signals(self) -> Dict[str, MultiTimeFrameSignal]:
        """Obtiene todas las señales actuales"""
        return self.current_signals.copy()
    
    def get_signal_summary(self, symbol: str = None) -> Dict[str, Any]:
        """Resumen de señales"""
        if symbol:
            signal = self.current_signals.get(symbol)
            if not signal:
                return {}
            
            return {
                'symbol': symbol,
                'overall_signal': signal.overall_signal,
                'overall_strength': signal.overall_strength.value,
                'overall_score': signal.overall_score,
                'overall_confidence': signal.overall_confidence,
                'confluence_score': signal.confluence_score,
                'trend_alignment': signal.trend_alignment,
                'momentum_alignment': signal.momentum_alignment,
                'timeframe_breakdown': {
                    tf.value: {
                        'signal': sig.signal_type,
                        'strength': sig.strength.value,
                        'score': sig.score,
                        'confidence': sig.confidence
                    }
                    for tf, sig in signal.timeframe_signals.items()
                },
                'timestamp': signal.timestamp.isoformat()
            }
        else:
            # Resumen de todos los símbolos
            return {
                symbol: {
                    'signal': signal.overall_signal,
                    'strength': signal.overall_strength.value,
                    'score': signal.overall_score,
                    'confidence': signal.overall_confidence,
                    'confluence': signal.confluence_score
                }
                for symbol, signal in self.current_signals.items()
            }

if __name__ == "__main__":
    # Ejemplo de uso
    analyzer = MultiTimeFrameAnalyzer(["BNBUSDT", "SOLUSDT"])
    
    print("=== SIMULACIÓN DE ANÁLISIS MULTI-TIMEFRAME ===")
    
    # Simular datos para diferentes timeframes
    import random
    
    base_price_bnb = 300.0
    base_price_sol = 100.0
    
    # Generar datos históricos
    for i in range(100):
        timestamp = datetime.now() - timedelta(minutes=5*i)
        
        # BNB
        price_change_bnb = random.gauss(0, 0.01)  # 1% volatilidad
        new_price_bnb = base_price_bnb * (1 + price_change_bnb)
        volume_bnb = random.uniform(800, 1200)
        
        analyzer.update_market_data("BNBUSDT", TimeFrame.M5, new_price_bnb, volume_bnb, timestamp)
        
        # SOL
        price_change_sol = random.gauss(0, 0.02)  # 2% volatilidad
        new_price_sol = base_price_sol * (1 + price_change_sol)
        volume_sol = random.uniform(1500, 2500)
        
        analyzer.update_market_data("SOLUSDT", TimeFrame.M5, new_price_sol, volume_sol, timestamp)
        
        base_price_bnb = new_price_bnb
        base_price_sol = new_price_sol
    
    # Generar datos para otros timeframes (simplificado)
    for timeframe in [TimeFrame.M15, TimeFrame.H1, TimeFrame.H4]:
        for i in range(50):
            timestamp = datetime.now() - timedelta(hours=i)
            
            # BNB
            price_bnb = base_price_bnb * (1 + random.gauss(0, 0.005))
            volume_bnb = random.uniform(800, 1200)
            analyzer.update_market_data("BNBUSDT", timeframe, price_bnb, volume_bnb, timestamp)
            
            # SOL
            price_sol = base_price_sol * (1 + random.gauss(0, 0.01))
            volume_sol = random.uniform(1500, 2500)
            analyzer.update_market_data("SOLUSDT", timeframe, price_sol, volume_sol, timestamp)
    
    # Mostrar resultados
    print("\n=== SEÑALES ACTUALES ===")
    summary = analyzer.get_signal_summary()
    
    for symbol, signal_data in summary.items():
        print(f"\n{symbol}:")
        print(f"  Señal General: {signal_data['signal']} ({signal_data['strength']})")
        print(f"  Puntuación: {signal_data['score']:.2f}")
        print(f"  Confianza: {signal_data['confidence']:.2f}")
        print(f"  Confluencia: {signal_data['confluence']:.2f}")
    
    # Detalles por símbolo
    for symbol in ["BNBUSDT", "SOLUSDT"]:
        print(f"\n=== DETALLES {symbol} ===")
        detailed = analyzer.get_signal_summary(symbol)
        
        if detailed:
            print(f"Señal: {detailed['overall_signal']} ({detailed['overall_strength']})")
            print(f"Puntuación: {detailed['overall_score']:.2f}")
            print(f"Confianza: {detailed['overall_confidence']:.2f}")
            print(f"Confluencia: {detailed['confluence_score']:.2f}")
            print(f"Alineación Tendencia: {detailed['trend_alignment']:.2f}")
            print(f"Alineación Momentum: {detailed['momentum_alignment']:.2f}")
            
            print("\nPor Timeframe:")
            for tf, tf_data in detailed['timeframe_breakdown'].items():
                print(f"  {tf}: {tf_data['signal']} ({tf_data['strength']}) - Score: {tf_data['score']:.2f}")
    
    print("\n=== ANÁLISIS COMPLETADO ===")