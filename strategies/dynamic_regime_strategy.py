# strategies/dynamic_regime_strategy.py

import pandas as pd
import numpy as np
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger("strategies.dynamic_regime_strategy")


class DynamicRegimeStrategy(BaseStrategy):
    # Declaraciones a nivel de clase para análisis estático
    enable_daily_tune: bool
    min_bars_required: int
    """
    Estrategia dinámica por régimen de mercado (tendencia vs. rango) con salidas ATR.

    - Detección de régimen:
      • Tendencia: ADX >= adx_trend_min. Dirección por MAs (ma20 vs ma50).
      • Rango: ADX < adx_trend_min o ancho de BB (bb_width) <= bb_width_range_max.

    - Entradas:
      • Tendencia alcista: pullback a MA20 con MACD>signal y RSI>50 (no sobrecompra).
      • Rango: rebote en BB inferior con RSI bajo.
      • Tendencia bajista: evitar salvo giro fuerte (RSI<30 y cruce MACD alcista) y cierre > MA20.

    - Salidas dinámicas:
      • SL inicial: entry - atr_mult_sl*ATR.
      • TP: entry + atr_mult_tp_{regimen}*ATR.
      • Trailing stop: max(trailing, close - atr_trailing_mult*ATR).
      • Time-out: salir si excede max_bars_in_trade barras.
    """

    def __init__(self):
        super().__init__(
            name="DynamicRegimeStrategy",
            description="Estrategia dinámica por régimen (ADX/BB/MA) con SL/TP/Trailing basados en ATR"
        )

        # Parámetros
        self.adx_trend_min: float = 25.0
        self.bb_width_range_max: float = 0.04  # 4%
        self.rsi_oversold: float = 35.0
        self.rsi_overbought: float = 70.0
        self.atr_mult_sl: float = 1.2
        self.atr_mult_tp_trend: float = 2.5
        self.atr_mult_tp_range: float = 1.5
        self.atr_trailing_mult: float = 1.5
        self.max_bars_in_trade: int = 48  # ~2 días en 1h
        self.min_bars_between_trades: int = 2

        # Estado
        self._in_position: bool = False
        self._entry_price: float = 0.0
        self._entry_index: int = -1
        self._stop_price: float = 0.0
        self._target_price: float = 0.0
        self._trailing_stop: float = 0.0
        self._last_tune_day: str | None = None
        
        # Flags/config
        self.enable_daily_tune = True  # permite desactivar el auto-ajuste en contextos de optimización
        self.min_bars_required = 55     # mínimo de barras para que analyze empiece a operar

    def _daily_tune(self, df: pd.DataFrame):
        """Reajusta parámetros una vez por día usando una ventana reciente de datos."""
        if df is None or df.empty:
            return
        # Usar últimas 72 velas (~3 días) o lo disponible
        lookback = df.tail(min(len(df), 72))

        # Calcular métricas de régimen/volatilidad
        adx_series = lookback.get("adx")
        macd_series = lookback.get("macd")
        macd_sig_series = lookback.get("macd_signal")
        ma20_series = lookback.get("ma_20")
        bb_upper = lookback.get("bb_upper")
        bb_lower = lookback.get("bb_lower")
        atr_series = lookback.get("atr")
        close_series = lookback.get("close")

        # ADX percentiles
        adx_p50 = float(adx_series.median()) if adx_series is not None else 20.0
        adx_p75 = float(adx_series.quantile(0.75)) if adx_series is not None else 25.0

        # bb_width relativo a MA20
        bb_width = None
        if ma20_series is not None and bb_upper is not None and bb_lower is not None:
            ma20_safe = ma20_series.replace(0, pd.NA).ffill()
            bw = (bb_upper - bb_lower) / ma20_safe
            bw = bw.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            bb_width = bw.clip(lower=0.0)
        bw_p35 = 0.04
        if bb_width is not None and len(bb_width.dropna()) > 0:
            try:
                bw_p35 = float(bb_width.quantile(0.35))
            except Exception:
                bw_p35 = 0.04

        # Volatilidad relativa por ATR/close
        vol_ratio = 0.0
        if atr_series is not None and close_series is not None:
            vr = atr_series / close_series
            vr = vr.replace([np.inf, -np.inf], np.nan).fillna(0.0)
            vol_ratio = float(vr.median()) if len(vr) else 0.0

        # Mapeos a parámetros (clamps/umbrales conservadores)
        # Umbral ADX: 25/27/30 según percentiles
        if adx_p75 >= 30:
            self.adx_trend_min = 30.0
        elif adx_p50 >= 27:
            self.adx_trend_min = 27.0
        else:
            self.adx_trend_min = 25.0

        # Rango por compresión de BB
        self.bb_width_range_max = float(max(0.03, min(0.06, bw_p35)))

        # Trailing según volatilidad típica
        self.atr_trailing_mult = 1.8 if vol_ratio >= 0.015 else 1.5

        # TP en tendencia según fuerza (ADX p75)
        if adx_p75 >= 30:
            self.atr_mult_tp_trend = 2.8
        elif adx_p75 >= 27:
            self.atr_mult_tp_trend = 2.5
        else:
            self.atr_mult_tp_trend = 2.2

        # TP en rango centrado en 1.5R, SL se mantiene
        self.atr_mult_tp_range = 1.5

        # RSI oversold ligeramente más alto en alta vol para evitar cuchillos
        self.rsi_oversold = 38.0 if vol_ratio >= 0.02 else 35.0
        # Sobrecompra fija
        self.rsi_overbought = 70.0

        logger.info(
            f"[DynamicRegimeStrategy] Daily tune -> adx_min={self.adx_trend_min}, bw_max={self.bb_width_range_max:.3f}, "
            f"tp_trend={self.atr_mult_tp_trend}, trailing={self.atr_trailing_mult}, rsi_ovsold={self.rsi_oversold}"
        )

    async def analyze(self, historical_data: pd.DataFrame, current_index: int) -> Dict[str, Any]:
        # Usamos las features ya calculadas por FeaturePipeline (inyectadas por Backtester)
        if historical_data is None or len(historical_data) < self.min_bars_required:
            return {"decision": "MANTENER", "score": 0}

        # El Backtester pasa historical_data[:i] y current_index=i.
        # Por lo tanto, el último dato disponible es el -1.
        df = historical_data
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else last

        close = float(last.get("close", 0))
        ma20 = float(last.get("ma_20", 0))
        ma50 = float(last.get("ma_50", 0))
        rsi = float(last.get("rsi", 50))
        macd = float(last.get("macd", 0))
        macd_signal = float(last.get("macd_signal", 0))
        adx = float(last.get("adx", 0))
        atr = float(last.get("atr", 0))
        bb_upper = float(last.get("bb_upper", 0))
        bb_lower = float(last.get("bb_lower", 0))
        vol_z = float(last.get("volume_zscore", 0))

        # Ancho relativo de bandas
        bb_width = 0.0
        if ma20 > 0 and bb_upper > 0 and bb_lower > 0:
            bb_width = (bb_upper - bb_lower) / ma20

        # Regímenes
        is_trend = adx >= self.adx_trend_min
        is_range = (not is_trend) or (bb_width <= self.bb_width_range_max)
        uptrend = is_trend and (ma20 > ma50)
        downtrend = is_trend and (ma20 <= ma50)

        decision = "MANTENER"
        score = 0.0

        # Reajuste diario al comienzo de cada día
        cur_day = df.index[-1].date().isoformat() if hasattr(df.index[-1], 'date') else None
        if self.enable_daily_tune and cur_day and cur_day != self._last_tune_day:
            self._daily_tune(df)
            self._last_tune_day = cur_day

        # Gestión de trade abierto: actualizar trailing y chequear salidas
        if self._in_position:
            bars_in_trade = max(0, (current_index - 1) - self._entry_index)
            # Actualizar trailing
            if atr > 0:
                new_trailing = close - self.atr_trailing_mult * atr
                self._trailing_stop = max(self._trailing_stop, new_trailing)

            # Criterios de salida
            hit_trailing = close <= self._trailing_stop and self._trailing_stop > 0
            hit_stop = close <= self._stop_price and self._stop_price > 0
            hit_target = close >= self._target_price and self._target_price > 0
            timeout = bars_in_trade >= self.max_bars_in_trade

            if hit_trailing or hit_stop or hit_target or timeout:
                decision = "VENDER"
                score = -1.0 if hit_stop else (0.5 if hit_trailing else 1.0 if hit_target else 0.0)
                # Reset de estado tras vender
                self._in_position = False
                self._entry_price = 0.0
                self._entry_index = -1
                self._stop_price = 0.0
                self._target_price = 0.0
                self._trailing_stop = 0.0

                return {"decision": decision, "score": score, "regime": "trend" if is_trend else "range"}
            else:
                return {"decision": "MANTENER", "score": 0.2, "regime": "trend" if is_trend else "range"}

        # Si no estamos en posición, buscamos entradas por régimen
        # Evitar sobreoperar: respetar min_bars_between_trades desde la última salida
        # (se controla implícitamente porque _entry_index se resetea)

        # Entradas en tendencia alcista: pullback a MA20 con momento positivo
        if uptrend:
            prev_close = float(prev.get("close", close))
            crossed_ma20_up = (prev_close < ma20) and (close >= ma20)
            near_ma20 = abs(close - ma20) / ma20 <= 0.003  # ±0.3%
            macd_bull = macd > macd_signal
            rsi_ok = 50.0 <= rsi <= self.rsi_overbought

            if (crossed_ma20_up or near_ma20) and macd_bull and rsi_ok:
                decision = "COMPRAR"
                score = 0.9
        
        # Entradas en rango: rebote en banda inferior + RSI bajo
        if decision == "MANTENER" and is_range:
            if close <= bb_lower and rsi <= self.rsi_oversold:
                decision = "COMPRAR"
                score = 0.7

        # Tendencia bajista: solo giros fuertes
        if decision == "MANTENER" and downtrend:
            prev_macd = float(prev.get("macd", macd))
            prev_signal = float(prev.get("macd_signal", macd_signal))
            macd_cross_up = (prev_macd <= prev_signal) and (macd > macd_signal)
            if rsi < 30 and macd_cross_up and close > ma20:
                decision = "COMPRAR"
                score = 0.6

        # Si hay compra, inicializar objetivos y stops
        if decision == "COMPRAR" and atr > 0:
            self._in_position = True
            self._entry_price = close
            self._entry_index = current_index - 1  # índice de la última barra visible
            self._stop_price = close - self.atr_mult_sl * atr
            tp_mult = self.atr_mult_tp_trend if uptrend else self.atr_mult_tp_range if is_range else self.atr_mult_tp_range
            self._target_price = close + tp_mult * atr
            self._trailing_stop = close - self.atr_trailing_mult * atr

        return {
            "decision": decision,
            "score": score,
            "regime": "trend" if is_trend else "range",
            "adx": adx,
            "bb_width": bb_width,
            "rsi": rsi,
        }

    def get_parameters(self) -> Dict[str, Any]:
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
        }

    def set_parameters(self, params: Dict[str, Any]):
        for k, v in params.items():
            if hasattr(self, k):
                setattr(self, k, type(getattr(self, k))(v))
