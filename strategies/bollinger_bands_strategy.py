# strategies/bollinger_bands_strategy.py

import pandas as pd
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy
from utils.technical_analysis import calculate_all_indicators # Para asegurar que los datos tienen los indicadores

logger = logging.getLogger("strategies.bollinger_bands_strategy")

class BollingerBandsStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(
            name="BollingerBandsStrategy",
            description="Estrategia de rebote de Bandas de Bollinger (compra en banda inferior, vende en superior)."
        )
        self._window = 20
        self._window_dev = 2

    def analyze(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Ejecutando análisis para BollingerBandsStrategy.")

        # Asegurarse de que tenemos suficientes datos para las Bandas de Bollinger
        if len(historical_data) < self._window:
            return {"decision": "MANTENER", "score": 0, "reason": "No hay suficientes datos para BB.", "bb_upper": None, "bb_lower": None}

        # Calcular Bandas de Bollinger (ya se hace en calculate_all_indicators, pero lo haremos explícito aquí si no se usa esa función)
        # Si calculate_all_indicators ya se encarga, solo necesitamos acceder a las columnas
        df_with_indicators = calculate_all_indicators(historical_data.copy())

        latest = df_with_indicators.iloc[-1]

        decision = "MANTENER"
        score = 0

        # Lógica de la estrategia de rebote
        # Compra si el precio cierra por debajo de la banda inferior
        if latest["close"] < latest["bb_lower"]:
            decision = "COMPRAR"
            score = 1
        # Vende si el precio cierra por encima de la banda superior
        elif latest["close"] > latest["bb_upper"]:
            decision = "VENDER"
            score = -1

        return {
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "decision": decision,
            "score": score,
            "close_price": round(latest["close"], 2),
            "bb_upper": round(latest["bb_upper"], 2),
            "bb_lower": round(latest["bb_lower"], 2)
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "window": self._window,
            "window_dev": self._window_dev
        }

    def set_parameters(self, params: Dict[str, Any]):
        if "window" in params:
            self._window = int(params["window"])
        if "window_dev" in params:
            self._window_dev = int(params["window_dev"])
