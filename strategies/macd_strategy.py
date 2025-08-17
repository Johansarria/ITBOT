# strategies/macd_strategy.py

import pandas as pd
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy
from utils.technical_analysis import calculate_all_indicators # Para asegurar que los datos tienen los indicadores

logger = logging.getLogger("strategies.macd_strategy")

class MACDStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(
            name="MACDStrategy",
            description="Estrategia basada en el cruce de la línea MACD con la línea de señal."
        )
        # Los períodos de MACD se manejan internamente por la librería ta

    def analyze(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Ejecutando análisis para MACDStrategy.")

        # Asegurarse de que tenemos suficientes datos para MACD (generalmente 26 períodos)
        if len(historical_data) < 34: # 26 (lenta) + 9 (señal) - un poco más para estabilidad
            return {"decision": "MANTENER", "score": 0, "reason": "No hay suficientes datos para MACD.", "macd": None, "macd_signal": None}

        df_with_indicators = calculate_all_indicators(historical_data.copy())

        latest = df_with_indicators.iloc[-1]
        previous = df_with_indicators.iloc[-2]

        decision = "MANTENER"
        score = 0

        # Lógica de la estrategia de cruce MACD
        # Cruce alcista: MACD cruza por encima de la línea de señal
        if latest["macd"] > latest["macd_signal"] and previous["macd"] <= previous["macd_signal"]:
            decision = "COMPRAR"
            score = 1
        # Cruce bajista: MACD cruza por debajo de la línea de señal
        elif latest["macd"] < latest["macd_signal"] and previous["macd"] >= previous["macd_signal"]:
            decision = "VENDER"
            score = -1

        return {
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "decision": decision,
            "score": score,
            "macd": round(latest["macd"], 4),
            "macd_signal": round(latest["macd_signal"], 4)
        }

    def get_parameters(self) -> Dict[str, Any]:
        # MACD no tiene parámetros configurables directos en esta implementación simple
        return {}

    def set_parameters(self, params: Dict[str, Any]):
        pass
