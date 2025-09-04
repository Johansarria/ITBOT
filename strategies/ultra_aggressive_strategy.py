# strategies/ultra_aggressive_strategy.py

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("strategies.ultra_aggressive_strategy")


class UltraAggressiveStrategy(BaseStrategy):
    """
    Estrategia ultra-agresiva diseñada específicamente para alcanzar 20%+ mensual.
    
    Características extremas:
    - Take profits masivos (10x-25x ATR)
    - Stop losses muy amplios (4x-8x ATR) 
    - Entradas múltiples en breakouts y reversiones
    - Tiempo extendido en trades (hasta 30 días)
    - Filtros mínimos para máxima actividad
    """

    def __init__(self):
        super().__init__(
            name="UltraAggressiveStrategy",
            description="Estrategia ultra-agresiva para máxima rentabilidad mensual"
        )

        # Parámetros ULTRA AGRESIVOS
        self.adx_trend_min: float = 8.0  # Extremadamente permisivo
        self.bb_width_range_max: float = 0.15  # Rango muy amplio
        self.rsi_oversold: float = 45.0  # Filtro mínimo
        self.rsi_overbought: float = 80.0  # Muy permisivo
        
        # STOPS Y TARGETS EXTREMOS
        self.atr_mult_sl: float = 5.0  # Stop loss MUY amplio
        self.atr_mult_tp_trend: float = 15.0  # Take profit MASIVO
        self.atr_mult_tp_range: float = 8.0  # TP alto en rango
        self.atr_trailing_mult: float = 4.0  # Trailing muy conservador
        
        # TIEMPO MÁXIMO EN TRADES
        self.max_bars_in_trade: int = 720  # 30 días en 1h
        self.min_bars_between_trades: int = 1  # Sin descanso
        
        # CONFIGURACIÓN AGRESIVA
        self.enable_breakout_entries: bool = True  # Entradas por breakout
        self.enable_reversal_entries: bool = True  # Entradas por reversión
        self.enable_momentum_scaling: bool = True  # Escalado por momentum
        self.volatility_multiplier: float = 1.5  # Multiplicador por volatilidad

        # Estado
        self._in_position: bool = False
        self._entry_price: float = 0.0
        self._entry_index: int = -1
        self._stop_price: float = 0.0
        self._target_price: float = 0.0
        self._trailing_stop: float = 0.0
        self._position_size_multiplier: float = 1.0
        
        # Flags
        self.enable_daily_tune = True
        self.min_bars_required = 15  # Muy permisivo

    def _dynamic_volatility_adjustment(self, df: pd.DataFrame):
        """Ajusta parámetros basado en volatilidad reciente."""
        if df is None or df.empty:
            return
            
        lookback = df.tail(min(len(df), 168))  # 7 días
        close_series = lookback.get("close")
        
        if close_series is not None and len(close_series) > 10:
            returns = close_series.pct_change().dropna()
            volatility = float(returns.std()) if len(returns) > 0 else 0.03
            
            # Ajustes extremos basados en volatilidad
            if volatility > 0.06:  # Volatilidad muy alta
                self.atr_mult_tp_trend = 25.0  # TP extremo
                self.atr_mult_tp_range = 15.0
                self.atr_mult_sl = 8.0  # SL extremo
                self.volatility_multiplier = 2.0
            elif volatility > 0.04:  # Alta volatilidad  
                self.atr_mult_tp_trend = 20.0
                self.atr_mult_tp_range = 12.0
                self.atr_mult_sl = 6.0
                self.volatility_multiplier = 1.8
            elif volatility > 0.025:  # Media volatilidad
                self.atr_mult_tp_trend = 15.0
                self.atr_mult_tp_range = 10.0
                self.atr_mult_sl = 5.0
                self.volatility_multiplier = 1.5
            else:  # Baja volatilidad - aún más agresivo
                self.atr_mult_tp_trend = 18.0
                self.atr_mult_tp_range = 12.0
                self.atr_mult_sl = 4.0
                self.volatility_multiplier = 1.3

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Análisis ultra-agresivo."""
        if data is None or data.empty or len(data) < self.min_bars_required:
            return {"decision": "MANTENER", "score": 0.0, "regime": "insufficient_data"}

        # Auto-ajuste por volatilidad
        if self.enable_daily_tune:
            self._dynamic_volatility_adjustment(data)

        # Obtener datos actuales
        current = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else current
        
        close = float(current.get("close", 0))
        adx = float(current.get("adx", 0))
        rsi = float(current.get("rsi", 50))
        macd = float(current.get("macd", 0))
        macd_signal = float(current.get("macd_signal", 0))
        ma20 = float(current.get("ma_20", close))
        ma50 = float(current.get("ma_50", close))
        bb_upper = float(current.get("bb_upper", close))
        bb_lower = float(current.get("bb_lower", close))
        atr = float(current.get("atr", 0))

        if close <= 0 or atr <= 0:
            return {"decision": "MANTENER", "score": 0.0, "regime": "invalid_data"}

        # Detección de régimen ULTRA PERMISIVA
        bb_width = (bb_upper - bb_lower) / close if close > 0 else 0
        is_trend = adx >= self.adx_trend_min
        is_range = bb_width <= self.bb_width_range_max
        
        uptrend = ma20 > ma50
        downtrend = ma20 < ma50

        decision = "MANTENER"
        score = 0.0

        # GESTIÓN DE POSICIONES - Salidas menos restrictivas
        if self._in_position:
            bars_in_trade = len(data) - self._entry_index
            
            # Trailing stop MENOS agresivo
            if close > self._entry_price * 1.05:  # Solo después de 5% ganancia
                new_trailing = close - self.atr_trailing_mult * atr * self.volatility_multiplier
                self._trailing_stop = max(self._trailing_stop, new_trailing)

            # Condiciones de salida MUY PERMISIVAS
            hit_stop = close <= self._stop_price
            hit_target = close >= self._target_price
            hit_trailing = self._trailing_stop > 0 and close <= self._trailing_stop
            timeout = bars_in_trade >= self.max_bars_in_trade

            if hit_stop or hit_target or hit_trailing or timeout:
                decision = "VENDER"
                if hit_target:
                    score = 1.0  # Máxima recompensa por target
                elif hit_trailing:
                    score = 0.9  # Alta recompensa por trailing
                elif timeout:
                    score = 0.4  # Timeout menos penalizado
                else:
                    score = -0.3  # Stop loss menos penalizado
                    
                # Reset estado
                self._in_position = False
                self._entry_price = 0.0
                self._entry_index = -1
                self._stop_price = 0.0
                self._target_price = 0.0
                self._trailing_stop = 0.0
                self._position_size_multiplier = 1.0

                return {"decision": decision, "score": score, "regime": "exit"}
            else:
                return {"decision": "MANTENER", "score": 0.4, "regime": "holding"}

        # ENTRADAS ULTRA AGRESIVAS - MÚLTIPLES SEÑALES

        entry_signals = []
        entry_scores = []

        # 1. BREAKOUTS - Muy agresivos
        if self.enable_breakout_entries:
            # Breakout alcista
            breakout_up = close > bb_upper * 0.999 and rsi < 85  # Casi sin filtro RSI
            momentum_up = macd > macd_signal * 0.7  # Filtro muy relajado
            
            if breakout_up and momentum_up:
                entry_signals.append("BREAKOUT_UP")
                entry_scores.append(1.0)
            
            # Breakout bajista (contrario) - apostar a reversión
            breakout_down = close < bb_lower * 1.001 and rsi > 15  # Filtro mínimo
            if breakout_down:
                entry_signals.append("BREAKOUT_REVERSAL")
                entry_scores.append(0.9)

        # 2. REVERSIONES DE TENDENCIA - Muy permisivas
        if self.enable_reversal_entries:
            # Reversión alcista en downtrend
            if downtrend:
                reversal_signal = (
                    rsi < 50 and  # RSI bajo pero no extremo
                    macd > macd_signal * 0.5 and  # MACD mejorando
                    close > ma50 * 0.97  # Cerca del soporte
                )
                if reversal_signal:
                    entry_signals.append("REVERSAL_UP")
                    entry_scores.append(0.8)
            
            # Reversión en uptrend (pullback)
            if uptrend:
                pullback = (
                    abs(close - ma20) / ma20 <= 0.01 and  # Cerca de MA20
                    rsi >= 40 and  # RSI no demasiado bajo
                    macd > macd_signal * 0.6  # Momentum positivo
                )
                if pullback:
                    entry_signals.append("PULLBACK")
                    entry_scores.append(0.95)

        # 3. MOMENTUM PURO - Sin filtros técnicos
        if self.enable_momentum_scaling:
            # Momentum alcista fuerte
            momentum_strong = (
                macd > macd_signal and
                close > prev.get("close", close) and
                rsi < 75  # Solo evitar sobrecompra extrema
            )
            if momentum_strong:
                entry_signals.append("MOMENTUM")
                entry_scores.append(0.85)

        # 4. ENTRADAS DE RANGO - Muy amplias
        range_entry = (
            bb_width <= self.bb_width_range_max * 1.5 and  # Rango ampliado
            rsi <= self.rsi_oversold * 1.3 and  # RSI permisivo
            close <= bb_lower * 1.01  # Cerca banda inferior
        )
        if range_entry:
            entry_signals.append("RANGE_BOUNCE")
            entry_scores.append(0.75)

        # TOMAR LA MEJOR SEÑAL
        if entry_signals and entry_scores:
            best_idx = entry_scores.index(max(entry_scores))
            decision = "COMPRAR"
            score = entry_scores[best_idx]
            signal_type = entry_signals[best_idx]
            
            # Ajustar multiplicador basado en señal
            if "BREAKOUT" in signal_type:
                self._position_size_multiplier = 1.5  # Más agresivo en breakouts
            elif "MOMENTUM" in signal_type:
                self._position_size_multiplier = 1.3
            else:
                self._position_size_multiplier = 1.0

        # INICIALIZAR POSICIÓN CON OBJETIVOS EXTREMOS
        if decision == "COMPRAR" and atr > 0:
            self._in_position = True
            self._entry_price = close
            self._entry_index = len(data) - 1
            
            # Stop loss ULTRA amplio
            sl_mult = self.atr_mult_sl * self.volatility_multiplier
            self._stop_price = close - sl_mult * atr
            
            # Take profit MASIVO - depende del régimen
            if is_trend:
                tp_mult = self.atr_mult_tp_trend * self.volatility_multiplier
            else:
                tp_mult = self.atr_mult_tp_range * self.volatility_multiplier
                
            self._target_price = close + tp_mult * atr
            self._trailing_stop = 0.0

            logger.info(f"Ultra-aggressive entry: SL={sl_mult:.1f}xATR, TP={tp_mult:.1f}xATR")

        return {
            "decision": decision,
            "score": score,
            "regime": "trend" if is_trend else "range",
            "atr_mult_sl": getattr(self, 'atr_mult_sl', 5.0),
            "atr_mult_tp": getattr(self, 'atr_mult_tp_trend', 15.0),
            "position_multiplier": self._position_size_multiplier,
            "signals": entry_signals if entry_signals else []
        }

    def get_parameters(self) -> Dict[str, Any]:
        """Retorna los parámetros actuales de la estrategia."""
        return {
            "adx_trend_min": self.adx_trend_min,
            "bb_width_range_max": self.bb_width_range_max,
            "rsi_oversold": self.rsi_oversold,
            "rsi_overbought": self.rsi_overbought,
            "atr_mult_sl": self.atr_mult_sl,
            "atr_mult_tp_trend": self.atr_mult_tp_trend,
            "atr_mult_tp_range": self.atr_mult_tp_range,
            "atr_trailing_mult": self.atr_trailing_mult,
            "max_bars_in_trade": self.max_bars_in_trade,
            "min_bars_between_trades": self.min_bars_between_trades,
            "volatility_multiplier": self.volatility_multiplier,
            "enable_breakout_entries": self.enable_breakout_entries,
            "enable_reversal_entries": self.enable_reversal_entries,
            "enable_momentum_scaling": self.enable_momentum_scaling
        }

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Actualiza los parámetros de la estrategia."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
