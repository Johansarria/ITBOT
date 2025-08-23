# strategies/simple_technical_strategy.py

import pandas as pd
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy
from utils.feature_pipeline import FeaturePipeline

logger = logging.getLogger("strategies.simple_technical_strategy")

class SimpleTechnicalStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(
            name="SimpleTechnicalStrategy",
            description="Estrategia basada en una combinación de indicadores técnicos (RSI, MACD, Stoch, CCI, ADX, BB)."
        )
        self._rsi_oversold = 30
        self._rsi_overbought = 70
        self._stoch_oversold = 20
        self._stoch_overbought = 80
        self._cci_oversold = -100
        self._cci_overbought = 100
        self._adx_strength_threshold = 25
        self._buy_score_threshold = 2
        self._sell_score_threshold = -2

    async def analyze(self, historical_data: pd.DataFrame, symbol: str, interval: str) -> Dict[str, Any]:
        logger.info("Ejecutando análisis para SimpleTechnicalStrategy.")
        
        # Calcular todos los indicadores usando la función auxiliar
        feature_pipeline = FeaturePipeline()
        df_indicators = feature_pipeline.transform(historical_data.copy()) # Pasar una copia para no modificar el original

        if df_indicators.empty:
            logger.warning("DataFrame de indicadores vacío. No se puede analizar.")
            return {"symbol": symbol, "interval": interval, "decision": "No hay datos para analizar", "score": 0}

        latest = df_indicators.iloc[-1]

        score = 0

        # Reglas de puntuación basadas en indicadores
        if latest["rsi"] < self._rsi_oversold: score += 1 # Sobreventa
        elif latest["rsi"] > self._rsi_overbought: score -= 1 # Sobrecompra

        if latest["macd"] > latest["macd_signal"]: score += 1 # Cruce alcista
        else: score -= 1 # Cruce bajista

        if latest["stoch_k"] > latest["stoch_d"] and latest["stoch_k"] < self._stoch_oversold: score += 1 # Cruce alcista en sobreventa
        elif latest["stoch_k"] < latest["stoch_d"] and latest["stoch_k"] > self._stoch_overbought: score -= 1 # Cruce bajista en sobrecompra

        if latest["cci"] < self._cci_oversold: score += 1 # Sobreventa
        elif latest["cci"] > self._cci_overbought: score -= 1 # Sobrecompra

        if latest["adx"] > self._adx_strength_threshold:
            if latest["plus_di"] > latest["minus_di"]: score += 1 # Tendencia alcista fuerte
            else: score -= 1 # Tendencia bajista fuerte

        # Bollinger Bands
        if latest["close"] <= latest["bb_lower"]: score += 1 # Cerca del piso, posible rebote
        elif latest["close"] >= latest["bb_upper"]: score -= 1 # Cerca del techo, posible corrección

        # Confirmación de Volumen
        if latest["volume"] > latest["volume_sma_20"]:
            # Si el volumen es alto, se refuerza la dirección de la puntuación actual
            if score > 0:
                score += 1
            elif score < 0:
                score -= 1

        decision = "MANTENER"
        if score >= self._buy_score_threshold: decision = "COMPRAR"
        elif score <= self._sell_score_threshold: decision = "VENDER"

        return {
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol, # El símbolo ahora está disponible
            "interval": interval, # El intervalo ahora está disponible
            "decision": decision,
            "score": score,
            "rsi": round(latest["rsi"], 2),
            "macd": round(latest["macd"], 4),
            "macd_signal": round(latest["macd_signal"], 4),
            "stoch_k": round(latest["stoch_k"], 2),
            "stoch_d": round(latest["stoch_d"], 2),
            "cci": round(latest["cci"], 2),
            "adx": round(latest["adx"], 2),
            "atr": round(latest["atr"], 4),
            "bb_upper": round(latest["bb_upper"], 4),
            "bb_lower": round(latest["bb_lower"], 4),
            "close": latest["close"]
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "rsi_oversold": self._rsi_oversold,
            "rsi_overbought": self._rsi_overbought,
            "stoch_oversold": self._stoch_oversold,
            "stoch_overbought": self._stoch_overbought,
            "cci_oversold": self._cci_oversold,
            "cci_overbought": self._cci_overbought,
            "adx_strength_threshold": self._adx_strength_threshold,
            "buy_score_threshold": self._buy_score_threshold,
            "sell_score_threshold": self._sell_score_threshold
        }

    def set_parameters(self, params: Dict[str, Any]):
        for key, value in params.items():
            if hasattr(self, f"_{key}"):
                setattr(self, f"_{key}", value)
            else:
                logger.warning(f"Parámetro desconocido para SimpleTechnicalStrategy: {key}")
