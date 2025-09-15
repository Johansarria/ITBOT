# strategies/nas100_strategy.py

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
from datetime import datetime

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("strategies.nas100_strategy")

class NAS100Strategy(BaseStrategy):
    """
    Estrategia específicamente diseñada para el índice NAS100 (NASDAQ-100).
    
    Basada en las características específicas del NAS100:
    - Alta volatilidad durante sesiones NY (9:30 AM - 4:00 PM EST)
    - Sensibilidad a tasas de interés de la Fed
    - Correlación con earnings de empresas tech
    - Momentum fuerte en tendencias
    - Volatilidad máxima en primeros 30-60 minutos de sesión
    
    Combina:
    1. Momentum adaptativo según horarios de trading
    2. Detección de breakouts en niveles clave
    3. Gestión de riesgo basada en volatilidad intradiaria
    4. Filtros de sesión para optimizar entradas
    """
    
    def __init__(self):
        super().__init__(
            name="NAS100Strategy",
            description="Estrategia optimizada para trading del índice NAS100 con enfoque en volatilidad y momentum"
        )
        
        # Parámetros de momentum
        self.momentum_period_short = 5  # Para detección rápida
        self.momentum_period_long = 20  # Para tendencia general
        self.momentum_threshold = 0.015  # 1.5% threshold para señales
        
        # Parámetros de volatilidad
        self.volatility_period = 14
        self.volatility_multiplier = 2.0
        
        # Parámetros de sesión (horarios EST)
        self.ny_session_start = 9.5  # 9:30 AM
        self.ny_session_end = 16.0   # 4:00 PM
        self.high_volatility_window = 1.0  # Primera hora
        
        # Parámetros de breakout
        self.breakout_period = 10
        self.breakout_threshold = 0.02  # 2%
        
        # Gestión de riesgo
        self.max_risk_per_trade = 0.02  # 2% máximo por operación
        self.stop_loss_atr_multiplier = 2.0
        self.take_profit_ratio = 2.0  # Risk:Reward 1:2

    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calcula Average True Range para gestión de riesgo"""
        if len(data) < period + 1:
            return 0.0
            
        high = data['high']
        low = data['low']
        close = data['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        return atr if not pd.isna(atr) else 0.0

    def _is_ny_session(self, timestamp: pd.Timestamp) -> bool:
        """Verifica si estamos en horario de sesión NY"""
        hour = timestamp.hour + timestamp.minute / 60.0
        return self.ny_session_start <= hour <= self.ny_session_end

    def _is_high_volatility_period(self, timestamp: pd.Timestamp) -> bool:
        """Verifica si estamos en período de alta volatilidad (primera hora)"""
        hour = timestamp.hour + timestamp.minute / 60.0
        return self.ny_session_start <= hour <= (self.ny_session_start + self.high_volatility_window)

    def _calculate_momentum_score(self, data: pd.DataFrame) -> float:
        """Calcula score de momentum combinando múltiples timeframes"""
        if len(data) < self.momentum_period_long:
            return 0.0
            
        current_price = data['close'].iloc[-1]
        
        # Momentum corto plazo (más peso)
        short_price = data['close'].iloc[-self.momentum_period_short]
        short_momentum = (current_price / short_price) - 1
        
        # Momentum largo plazo
        long_price = data['close'].iloc[-self.momentum_period_long]
        long_momentum = (current_price / long_price) - 1
        
        # Score combinado (70% corto, 30% largo)
        momentum_score = (short_momentum * 0.7) + (long_momentum * 0.3)
        
        return momentum_score

    def _detect_breakout(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detecta breakouts de niveles de soporte/resistencia"""
        if len(data) < self.breakout_period + 1:
            return {"breakout": False, "direction": None, "strength": 0}
            
        # Calcular niveles de soporte y resistencia
        recent_data = data.tail(self.breakout_period)
        resistance = recent_data['high'].max()
        support = recent_data['low'].min()
        
        current_price = data['close'].iloc[-1]
        current_volume = data['volume'].iloc[-1]
        avg_volume = data['volume'].tail(self.breakout_period).mean()
        
        # Detectar breakout alcista
        if current_price > resistance * (1 + self.breakout_threshold):
            volume_confirmation = current_volume > avg_volume * 1.5
            return {
                "breakout": True,
                "direction": "bullish",
                "strength": min(((current_price / resistance) - 1) * 10, 3.0),
                "volume_confirmed": volume_confirmation
            }
            
        # Detectar breakout bajista
        elif current_price < support * (1 - self.breakout_threshold):
            volume_confirmation = current_volume > avg_volume * 1.5
            return {
                "breakout": True,
                "direction": "bearish",
                "strength": min(((support / current_price) - 1) * 10, 3.0),
                "volume_confirmed": volume_confirmation
            }
            
        return {"breakout": False, "direction": None, "strength": 0}

    def analyze(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Análisis principal de la estrategia NAS100
        """
        if len(historical_data) < max(self.momentum_period_long, self.volatility_period, self.breakout_period):
            return {
                "decision": "MANTENER",
                "score": 0,
                "reason": "Datos insuficientes"
            }

        current_timestamp = pd.Timestamp.now()
        current_price = historical_data['close'].iloc[-1]
        
        # Verificar si estamos en sesión de trading
        in_ny_session = self._is_ny_session(current_timestamp)
        in_high_vol_period = self._is_high_volatility_period(current_timestamp)
        
        # Calcular indicadores
        momentum_score = self._calculate_momentum_score(historical_data)
        atr = self._calculate_atr(historical_data, self.volatility_period)
        breakout_info = self._detect_breakout(historical_data)
        
        # Calcular volatilidad actual
        returns = historical_data['close'].pct_change().tail(self.volatility_period)
        current_volatility = returns.std()
        
        # Inicializar score y decisión
        total_score = 0
        decision = "MANTENER"
        signals = []
        
        # Factor de sesión (más agresivo durante NY session)
        session_multiplier = 1.5 if in_ny_session else 0.8
        volatility_multiplier = 1.3 if in_high_vol_period else 1.0
        
        # Señal de Momentum
        if abs(momentum_score) > self.momentum_threshold:
            momentum_signal = np.sign(momentum_score) * min(abs(momentum_score) / self.momentum_threshold, 2.0)
            total_score += momentum_signal * session_multiplier
            signals.append(f"Momentum: {momentum_score:.3f}")
        
        # Señal de Breakout
        if breakout_info["breakout"]:
            breakout_signal = breakout_info["strength"]
            if breakout_info["direction"] == "bullish":
                total_score += breakout_signal * volatility_multiplier
                signals.append(f"Breakout alcista: {breakout_signal:.2f}")
            elif breakout_info["direction"] == "bearish":
                total_score -= breakout_signal * volatility_multiplier
                signals.append(f"Breakout bajista: {breakout_signal:.2f}")
        
        # Ajuste por volatilidad (reducir posiciones en alta volatilidad extrema)
        if current_volatility > returns.quantile(0.95):  # Top 5% volatilidad
            total_score *= 0.7
            signals.append("Volatilidad extrema: reduciendo exposición")
        
        # Determinar decisión final
        if total_score > 1.0:
            decision = "COMPRAR"
        elif total_score < -1.0:
            decision = "VENDER"
        else:
            decision = "MANTENER"
        
        # Calcular niveles de stop loss y take profit
        stop_loss_distance = atr * self.stop_loss_atr_multiplier
        
        if decision == "COMPRAR":
            stop_loss = current_price - stop_loss_distance
            take_profit = current_price + (stop_loss_distance * self.take_profit_ratio)
        elif decision == "VENDER":
            stop_loss = current_price + stop_loss_distance
            take_profit = current_price - (stop_loss_distance * self.take_profit_ratio)
        else:
            stop_loss = None
            take_profit = None
        
        return {
            "timestamp": current_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "decision": decision,
            "score": round(total_score, 3),
            "current_price": current_price,
            "momentum_score": round(momentum_score, 4),
            "volatility": round(current_volatility, 4),
            "atr": round(atr, 2),
            "in_ny_session": in_ny_session,
            "in_high_vol_period": in_high_vol_period,
            "breakout_detected": breakout_info["breakout"],
            "breakout_direction": breakout_info["direction"],
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "signals": signals,
            "session_multiplier": session_multiplier,
            "volatility_multiplier": volatility_multiplier
        }

    def get_parameters(self) -> Dict[str, Any]:
        """Devuelve los parámetros configurables de la estrategia"""
        return {
            "momentum_period_short": self.momentum_period_short,
            "momentum_period_long": self.momentum_period_long,
            "momentum_threshold": self.momentum_threshold,
            "volatility_period": self.volatility_period,
            "volatility_multiplier": self.volatility_multiplier,
            "breakout_period": self.breakout_period,
            "breakout_threshold": self.breakout_threshold,
            "max_risk_per_trade": self.max_risk_per_trade,
            "stop_loss_atr_multiplier": self.stop_loss_atr_multiplier,
            "take_profit_ratio": self.take_profit_ratio
        }

    def set_parameters(self, params: Dict[str, Any]):
        """Establece los parámetros de la estrategia"""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
                logger.info(f"Parámetro {key} actualizado a {value}")