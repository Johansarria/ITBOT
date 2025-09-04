#!/usr/bin/env python3
"""
Estrategia Híbrida de Momentum para Criptomonedas de Alto Rendimiento
Diseñada específicamente para aprovechar el sistema de selección dinámica de pares
y generar 20%+ mensual mediante múltiples timeframes y momentum tracking
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
import logging

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class HighMomentumCryptoStrategy(BaseStrategy):
    """
    Estrategia híbrida que combina:
    1. Detección de breakouts en criptos con alta performance
    2. Momentum multi-timeframe 
    3. Volume surge detection
    4. Risk-adjusted position sizing
    """
    
    def __init__(self):
        super().__init__(
            name="HighMomentumCryptoStrategy",
            description="Estrategia híbrida de momentum para criptos de alto rendimiento con targets de 20% mensual"
        )
        
        # Parámetros de momentum
        self.rsi_period = 14
        self.rsi_momentum_threshold = 60  # Para momentum alcista
        self.rsi_entry_min = 45           # Evitar entrar en oversold extremo
        self.rsi_entry_max = 75           # Evitar entrar en overbought extremo
        
        # Bollinger Bands para breakouts
        self.bb_period = 20
        self.bb_std = 2.0
        self.bb_breakout_factor = 1.002   # 0.2% por encima de banda superior
        
        # MACD para confirmar momentum
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
        # Volume surge detection
        self.volume_ma_period = 20
        self.volume_surge_multiplier = 1.8  # 80% más volumen que promedio
        
        # Moving averages para tendencia
        self.ma_fast = 10
        self.ma_slow = 21
        
        # Position sizing y risk management
        self.take_profit_pct = 3.5    # 3.5% TP para aprovechar momentum
        self.stop_loss_pct = 1.5      # 1.5% SL ajustado
        self.trailing_stop_pct = 1.2  # 1.2% trailing stop
        
        # Momentum scoring weights
        self.weight_trend = 0.25      # Tendencia MA
        self.weight_breakout = 0.30   # Breakout de BB
        self.weight_momentum = 0.25   # RSI momentum
        self.weight_volume = 0.20     # Volume surge
        
        # Estado interno
        self._in_position = False
        self._entry_price = 0.0
        self._entry_index = -1
        self._stop_price = 0.0
        self._target_price = 0.0
        self._highest_price = 0.0
        self._trailing_stop_price = 0.0
        
        # Estadísticas de performance
        self._trade_count = 0
        self._win_count = 0
        
        # Configuración mínima
        self.min_bars_required = 30
        
    def get_parameters(self) -> Dict[str, Any]:
        """Devuelve parámetros actuales"""
        return {
            'rsi_period': self.rsi_period,
            'rsi_momentum_threshold': self.rsi_momentum_threshold,
            'rsi_entry_min': self.rsi_entry_min,
            'rsi_entry_max': self.rsi_entry_max,
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'bb_breakout_factor': self.bb_breakout_factor,
            'macd_fast': self.macd_fast,
            'macd_slow': self.macd_slow,
            'macd_signal': self.macd_signal,
            'volume_ma_period': self.volume_ma_period,
            'volume_surge_multiplier': self.volume_surge_multiplier,
            'ma_fast': self.ma_fast,
            'ma_slow': self.ma_slow,
            'take_profit_pct': self.take_profit_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct
        }
    
    def set_parameters(self, params: Dict[str, Any]):
        """Configura parámetros"""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def _calculate_momentum_score(self, current_data: pd.Series, recent_data: pd.DataFrame) -> float:
        """Calcula un score de momentum compuesto (0-1)"""
        try:
            close = float(current_data.get("close", 0))
            
            # 1. Trend Score (MA cross y pendiente)
            ma_fast = current_data.get("ma_fast", close)
            ma_slow = current_data.get("ma_slow", close)
            trend_score = 0.0
            
            if ma_fast > ma_slow:
                trend_strength = (ma_fast - ma_slow) / ma_slow
                trend_score = min(1.0, trend_strength * 50)  # Normalize
            
            # 2. Breakout Score (posición respecto a Bollinger Bands)
            bb_upper = current_data.get("bb_upper", close * 1.02)
            bb_lower = current_data.get("bb_lower", close * 0.98)
            bb_range = bb_upper - bb_lower
            
            breakout_score = 0.0
            if close >= bb_upper * self.bb_breakout_factor:
                breakout_score = min(1.0, (close - bb_upper) / (bb_range * 0.1))
            elif close > bb_upper * 0.99:  # Cerca de breakout
                breakout_score = 0.5
            
            # 3. Momentum Score (RSI)
            rsi = current_data.get("rsi", 50)
            momentum_score = 0.0
            
            if self.rsi_entry_min <= rsi <= self.rsi_entry_max:
                if rsi >= self.rsi_momentum_threshold:
                    momentum_score = (rsi - self.rsi_momentum_threshold) / (100 - self.rsi_momentum_threshold)
                else:
                    momentum_score = 0.3  # Momentum neutral
            
            # 4. Volume Score (surge detection)
            volume = current_data.get("volume", 0)
            volume_ma = current_data.get("volume_ma", volume)
            
            volume_score = 0.0
            if volume_ma > 0:
                volume_ratio = volume / volume_ma
                if volume_ratio >= self.volume_surge_multiplier:
                    volume_score = min(1.0, (volume_ratio - 1.0) / 2.0)  # Normalize
            
            # Score compuesto
            total_score = (
                trend_score * self.weight_trend +
                breakout_score * self.weight_breakout +
                momentum_score * self.weight_momentum +
                volume_score * self.weight_volume
            )
            
            return min(1.0, max(0.0, total_score))
            
        except Exception as e:
            logger.error(f"Error calculando momentum score: {e}")
            return 0.0

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Análisis principal de momentum para criptos de alto rendimiento"""
        if data is None or data.empty or len(data) < self.min_bars_required:
            return {"decision": "MANTENER", "score": 0.0, "regime": "insufficient_data"}

        try:
            # Datos actuales
            current = data.iloc[-1]
            close = float(current.get("close", 0))
            high = float(current.get("high", close))
            low = float(current.get("low", close))
            
            # Datos recientes para análisis
            recent_data = data.tail(20)
            
            # MANEJO DE POSICIÓN EXISTENTE
            if self._in_position:
                # Actualizar trailing stop
                if close > self._highest_price:
                    self._highest_price = close
                    self._trailing_stop_price = close * (1 - self.trailing_stop_pct / 100)
                
                # Verificar condiciones de salida
                hit_target = close >= self._target_price
                hit_stop = close <= self._stop_price
                hit_trailing = close <= self._trailing_stop_price
                
                if hit_target:
                    # Take profit alcanzado
                    self._reset_position()
                    self._trade_count += 1
                    self._win_count += 1
                    return {"decision": "VENDER", "score": 1.0, "regime": "momentum_profit"}
                    
                elif hit_trailing:
                    # Trailing stop hit (buena salida)
                    self._reset_position()
                    self._trade_count += 1
                    self._win_count += 1
                    return {"decision": "VENDER", "score": 0.8, "regime": "momentum_trailing"}
                    
                elif hit_stop:
                    # Stop loss hit
                    self._reset_position()
                    self._trade_count += 1
                    return {"decision": "VENDER", "score": -0.7, "regime": "momentum_stop"}
                    
                else:
                    # Mantener posición - evaluar strength
                    momentum_score = self._calculate_momentum_score(current, recent_data)
                    return {"decision": "MANTENER", "score": momentum_score, "regime": "momentum_hold"}
            
            # LÓGICA DE ENTRADA - MOMENTUM DETECTION
            
            # Calcular momentum score
            momentum_score = self._calculate_momentum_score(current, recent_data)
            
            # Filtros adicionales para entrada
            rsi = current.get("rsi", 50)
            macd = current.get("macd", 0)
            macd_signal = current.get("macd_signal", 0)
            
            # Confirmaciones técnicas
            macd_bullish = macd > macd_signal
            rsi_in_range = self.rsi_entry_min <= rsi <= self.rsi_entry_max
            
            # Análisis de precio reciente (no debe haber caído mucho)
            price_change_5 = recent_data['close'].pct_change(5).iloc[-1] if len(recent_data) >= 5 else 0
            recent_stability = price_change_5 >= -0.05  # No más de 5% de caída reciente
            
            # CONDICIONES DE ENTRADA
            entry_signal = False
            entry_score = 0.0
            
            if momentum_score >= 0.6:  # Score alto de momentum
                if macd_bullish and rsi_in_range and recent_stability:
                    entry_signal = True
                    entry_score = momentum_score
            elif momentum_score >= 0.4:  # Score medio con confirmaciones adicionales
                volume_surge = current.get("volume", 0) / max(current.get("volume_ma", 1), 1) >= self.volume_surge_multiplier
                strong_breakout = close >= current.get("bb_upper", close * 1.02) * self.bb_breakout_factor
                
                if volume_surge and strong_breakout and macd_bullish:
                    entry_signal = True
                    entry_score = momentum_score + 0.2  # Bonus por confirmaciones
            
            # Entrada confirmada
            if entry_signal:
                self._in_position = True
                self._entry_price = close
                self._entry_index = len(data) - 1
                self._highest_price = close
                
                # Configurar targets dinámicos
                self._target_price = close * (1 + self.take_profit_pct / 100)
                self._stop_price = close * (1 - self.stop_loss_pct / 100)
                self._trailing_stop_price = close * (1 - self.trailing_stop_pct / 100)
                
                return {
                    "decision": "COMPRAR", 
                    "score": min(1.0, entry_score), 
                    "regime": "momentum_entry",
                    "momentum_score": momentum_score
                }
            
            # No hay señal de entrada
            return {
                "decision": "MANTENER", 
                "score": 0.0, 
                "regime": "momentum_wait",
                "momentum_score": momentum_score
            }
            
        except Exception as e:
            logger.error(f"Error en HighMomentumCryptoStrategy.analyze: {e}")
            return {"decision": "MANTENER", "score": 0.0, "regime": "error"}
    
    def _reset_position(self):
        """Reset estado de posición"""
        self._in_position = False
        self._entry_price = 0.0
        self._entry_index = -1
        self._stop_price = 0.0
        self._target_price = 0.0
        self._highest_price = 0.0
        self._trailing_stop_price = 0.0
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Estadísticas de performance"""
        win_rate = (self._win_count / max(self._trade_count, 1)) * 100
        return {
            "total_trades": self._trade_count,
            "winning_trades": self._win_count,
            "win_rate": win_rate,
            "strategy": "HighMomentumCrypto"
        }
