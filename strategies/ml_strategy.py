
import logging
import pandas as pd
from typing import Dict, Any
from strategies.base_strategy import BaseStrategy
from utils.technical_analysis import analyze_market

logger = logging.getLogger("strategies.ml_strategy")

class MLStrategy(BaseStrategy):
    def __init__(self, name="MLStrategy", description="Estrategia de trading basada en Machine Learning (LightGBM).", umbral_alto: float = 0.85, umbral_medio: float = 0.70, umbral_bajo: float = 0.55): # REMOVED probability_threshold
        super().__init__(name, description)
        self.symbol = "BTCUSDT" # Símbolo por defecto
        self.interval = "1h" # Intervalo por defecto
        # REMOVED: self.probability_threshold = probability_threshold # Parámetro de umbral de probabilidad
        self.umbral_alto = umbral_alto
        self.umbral_medio = umbral_medio
        self.umbral_bajo = umbral_bajo

    async def analyze(self, historical_data: pd.DataFrame, current_index: int) -> dict:
        """
        Realiza el análisis utilizando la función analyze_market que integra el modelo de ML.
        """
        analysis_result = await analyze_market(
            symbol=self.symbol,
            interval=self.interval,
            df_klines=historical_data, # Pasar el DataFrame completo
            current_index=current_index, # Pasar el índice actual
            export=False, # No exportar resultados durante el backtesting
            umbral_alto=self.umbral_alto,
            umbral_medio=self.umbral_medio,
            umbral_bajo=self.umbral_bajo
        )
        return analysis_result

    def get_parameters(self) -> Dict[str, Any]:
        """
        Devuelve los parámetros de la estrategia.
        """
        return {
            "symbol": self.symbol,
            "interval": self.interval,
            "name": self.name,
            # REMOVED: "probability_threshold": self.probability_threshold,
            "umbral_alto": self.umbral_alto,
            "umbral_medio": self.umbral_medio,
            "umbral_bajo": self.umbral_bajo
        }

    def set_parameters(self, parameters: Dict[str, Any]):
        """
        Establece los parámetros de la estrategia.
        """
        if "symbol" in parameters: self.symbol = parameters["symbol"]
        if "interval" in parameters: self.interval = parameters["interval"]
        if "name" in parameters: self.name = parameters["name"]
        # REMOVED: if "probability_threshold" in parameters: self.probability_threshold = parameters["probability_threshold"]
        if "umbral_alto" in parameters: self.umbral_alto = parameters["umbral_alto"]
        if "umbral_medio" in parameters: self.umbral_medio = parameters["umbral_medio"]
        if "umbral_bajo" in parameters: self.umbral_bajo = parameters["umbral_bajo"]

