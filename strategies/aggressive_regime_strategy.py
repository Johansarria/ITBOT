# strategies/aggressive_regime_strategy.py

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("strategies.aggressive_regime_strategy")


class AggressiveRegimeStrategy(BaseStrategy):
    """
    Versión agresiva de DynamicRegimeStrategy optimizada para mayor rentabilidad.
    
    Cambios principales:
    - Take profits más altos (5x-8x ATR vs 2.5x-1.5x)
    - Stop losses más amplios (2x-3x ATR vs 1.2x)
    - Filtros menos restrictivos (RSI, ADX)
    - Mayor tiempo en trades (120-240 barras vs 48)
    - Trailing stops menos agresivos
    """

    def __init__(self):
        super().__init__(
            name="AggressiveRegimeStrategy",
            description="Estrategia agresiva por régimen optimizada para alta rentabilidad"
        )

        # Parámetros AGRESIVOS
        self.adx_trend_min: float = 15.0  # Más permisivo (era 25)
        self.bb_width_range_max: float = 0.06  # Más rango (era 0.04)
        self.rsi_oversold: float = 40.0  # Menos restrictivo (era 35)
        self.rsi_overbought: float = 75.0  # Más permisivo (era 70)
        
        # STOPS Y TARGETS MÁS AMPLIOS
        self.atr_mult_sl: float = 2.5  # Stop loss más amplio (era 1.2)
        self.atr_mult_tp_trend: float = 6.0  # TP mucho mayor (era 2.5)
        self.atr_mult_tp_range: float = 4.0  # TP mayor en rango (era 1.5)
        self.atr_trailing_mult: float = 2.8  # Trailing menos agresivo (era 1.5)
        
        # TIEMPO EN TRADES EXTENDIDO
        self.max_bars_in_trade: int = 168  # ~7 días en 1h (era 48)
        self.min_bars_between_trades: int = 1  # Más activo (era 2)

        # Estado
        self._in_position: bool = False
        self._entry_price: float = 0.0
        self._entry_index: int = -1
        self._stop_price: float = 0.0
        self._target_price: float = 0.0
        self._trailing_stop: float = 0.0
        self._last_tune_day: str | None = None
        
        # Flags/config
        self.enable_daily_tune = True
        self.min_bars_required = 30  # Menos restrictivo (era 55)

    def _daily_tune(self, df: pd.DataFrame):
        """Auto-ajuste diario más agresivo."""
        if df is None or df.empty or not self.enable_daily_tune:
            return
            
        # Usar ventana más larga para capture trends (5 días)
        lookback = df.tail(min(len(df), 120))

        # Calcular métricas
        adx_series = lookback.get("adx")
        close_series = lookback.get("close")
        atr_series = lookback.get("atr")
        
        # Volatilidad reciente para ajustar agresividad
        volatility = 0.02
        if close_series is not None and len(close_series) > 10:
            returns = close_series.pct_change().dropna()
            volatility = float(returns.std()) if len(returns) > 0 else 0.02
            
        # Ajustar parámetros basado en volatilidad
        if volatility > 0.04:  # Alta volatilidad
            self.atr_mult_tp_trend = 8.0  # TP aún más alto
            self.atr_mult_tp_range = 5.5
            self.atr_mult_sl = 3.0  # SL más amplio
        elif volatility > 0.025:  # Volatilidad media
            self.atr_mult_tp_trend = 6.5
            self.atr_mult_tp_range = 4.5
            self.atr_mult_sl = 2.8
        else:  # Baja volatilidad - más agresivo
            self.atr_mult_tp_trend = 7.0
            self.atr_mult_tp_range = 4.8
            self.atr_mult_sl = 2.2

    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Análisis principal con lógica agresiva."""
        if data is None or data.empty or len(data) < self.min_bars_required:
            return {"decision": "MANTENER", "score": 0.0, "regime": "insufficient_data"}

        # Auto-tune diario
        current_day = str(data.index[-1].date()) if hasattr(data.index[-1], 'date') else str(data.index[-1])[:10]
        if self.enable_daily_tune and current_day != self._last_tune_day:
            self._daily_tune(data)
            self._last_tune_day = current_day

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

        # Detección de régimen MÁS PERMISIVA
        bb_width = (bb_upper - bb_lower) / close if close > 0 else 0
        is_trend = adx >= self.adx_trend_min
        is_range = not is_trend or bb_width <= self.bb_width_range_max
        
        uptrend = is_trend and ma20 > ma50
        downtrend = is_trend and ma20 < ma50

        decision = "MANTENER"
        score = 0.0

        # GESTIÓN DE POSICIONES EXISTENTES
        if self._in_position:
            bars_in_trade = len(data) - self._entry_index
            
            # Actualizar trailing stop MENOS AGRESIVO
            if close > self._entry_price:
                new_trailing = close - self.atr_trailing_mult * atr
                self._trailing_stop = max(self._trailing_stop, new_trailing)

            # Condiciones de salida MÁS PERMISIVAS
            hit_stop = close <= self._stop_price
            hit_target = close >= self._target_price
            hit_trailing = self._trailing_stop > 0 and close <= self._trailing_stop
            timeout = bars_in_trade >= self.max_bars_in_trade

            if hit_stop or hit_target or hit_trailing or timeout:
                decision = "VENDER"
                # Score más optimista
                if hit_target:
                    score = 1.0
                elif hit_trailing:
                    score = 0.8  # Trailing = buena salida
                elif timeout:
                    score = 0.3  # Timeout menos penalizado
                else:
                    score = -0.5  # Stop loss menos penalizado
                    
                # Reset estado
                self._in_position = False
                self._entry_price = 0.0
                self._entry_index = -1
                self._stop_price = 0.0
                self._target_price = 0.0
                self._trailing_stop = 0.0

                return {"decision": decision, "score": score, "regime": "trend" if is_trend else "range"}
            else:
                return {"decision": "MANTENER", "score": 0.3, "regime": "trend" if is_trend else "range"}

        # ENTRADAS MÁS AGRESIVAS
        
        # 1. Tendencia alcista: condiciones más permisivas
        if uptrend:
            prev_close = float(prev.get("close", close))
            near_ma20 = abs(close - ma20) / ma20 <= 0.008  # Más permisivo (era 0.003)
            macd_bull = macd > macd_signal * 0.8  # Menos restrictivo
            rsi_ok = 45.0 <= rsi <= self.rsi_overbought  # Rango más amplio
            
            # También entrar en breakouts
            breakout_up = close > bb_upper and rsi < 80
            
            if (near_ma20 and macd_bull and rsi_ok) or breakout_up:
                decision = "COMPRAR"
                score = 1.0 if breakout_up else 0.9

        # 2. Rango: más oportunidades
        if decision == "MANTENER" and is_range:
            # Rebote en banda inferior
            bounce_low = close <= bb_lower * 1.005  # Más permisivo
            rsi_low = rsi <= self.rsi_oversold * 1.15  # Menos restrictivo
            
            # También entrar en reversiones de rango
            reversal = close < ma20 and rsi < 45 and macd > macd_signal
            
            if (bounce_low and rsi_low) or reversal:
                decision = "COMPRAR" 
                score = 0.8 if bounce_low else 0.7

        # 3. Tendencia bajista: más oportunidades de giro
        if decision == "MANTENER" and downtrend:
            prev_macd = float(prev.get("macd", macd))
            prev_signal = float(prev.get("macd_signal", macd_signal))
            macd_improving = macd > prev_macd  # Solo mejorando
            oversold = rsi < 40  # Menos restrictivo (era 30)
            above_support = close > ma50 * 0.98  # Cerca de soporte
            
            if oversold and macd_improving and above_support:
                decision = "COMPRAR"
                score = 0.7

        # Inicializar posición con objetivos AGRESIVOS
        if decision == "COMPRAR" and atr > 0:
            self._in_position = True
            self._entry_price = close
            self._entry_index = len(data) - 1
            self._stop_price = close - self.atr_mult_sl * atr
            
            # TP dinámico según régimen
            if is_trend:
                self._target_price = close + self.atr_mult_tp_trend * atr
            else:
                self._target_price = close + self.atr_mult_tp_range * atr
                
            self._trailing_stop = 0.0

        return {
            "decision": decision,
            "score": score,
            "regime": "trend" if is_trend else "range",
            "atr_mult_sl": self.atr_mult_sl,
            "atr_mult_tp": self.atr_mult_tp_trend if is_trend else self.atr_mult_tp_range
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
            "enable_daily_tune": self.enable_daily_tune,
            "min_bars_required": self.min_bars_required
        }

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Actualiza los parámetros de la estrategia."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
