# strategies/ma_cross_strategy.py

import pandas as pd
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy
from utils.technical_analysis import calculate_all_indicators # Para asegurar que los datos tienen los indicadores

logger = logging.getLogger("strategies.ma_cross_strategy")

class MACrossStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(
            name="MACrossStrategy",
            description="Estrategia de cruce de medias móviles (SMA rápida y lenta)."
        )
        self._fast_ma_period = 10
        self._slow_ma_period = 30

    def analyze(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        logger.info("Ejecutando análisis para MACrossStrategy.")

        # Create a writable copy to avoid SettingWithCopyWarning
        df = historical_data.copy()

        # Asegurarse de que tenemos suficientes datos para las medias móviles
        if len(df) < self._slow_ma_period:
            return {"decision": "MANTENER", "score": 0, "reason": "No hay suficientes datos para MA.", "fast_ma": None, "slow_ma": None}

        # Calcular las medias móviles
        df['fast_ma'] = df['close'].rolling(window=self._fast_ma_period).mean()
        df['slow_ma'] = df['close'].rolling(window=self._slow_ma_period).mean()

        # Asegurarse de que los valores de MA no son NaN (por el rolling window)
        if df['fast_ma'].iloc[-1] is None or df['slow_ma'].iloc[-1] is None:
             return {"decision": "MANTENER", "score": 0, "reason": "MA values are NaN.", "fast_ma": None, "slow_ma": None}

        latest_fast_ma = df['fast_ma'].iloc[-1]
        latest_slow_ma = df['slow_ma'].iloc[-1]

        # Lógica de la estrategia
        decision = "MANTENER"
        score = 0

        # Cruce alcista (Golden Cross)
        # La MA rápida cruza por encima de la MA lenta
        if latest_fast_ma > latest_slow_ma and df['fast_ma'].iloc[-2] <= df['slow_ma'].iloc[-2]:
            decision = "COMPRAR"
            score = 1
        # Cruce bajista (Death Cross)
        # La MA rápida cruza por debajo de la MA lenta
        elif latest_fast_ma < latest_slow_ma and df['fast_ma'].iloc[-2] >= df['slow_ma'].iloc[-2]:
            decision = "VENDER"
            score = -1

        return {
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "decision": decision,
            "score": score,
            "fast_ma": round(latest_fast_ma, 2),
            "slow_ma": round(latest_slow_ma, 2)
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "fast_ma_period": self._fast_ma_period,
            "slow_ma_period": self._slow_ma_period
        }

    def set_parameters(self, params: Dict[str, Any]):
        if "fast_ma_period" in params:
            self._fast_ma_period = int(params["fast_ma_period"])
        if "slow_ma_period" in params:
            self._slow_ma_period = int(params["slow_ma_period"])
