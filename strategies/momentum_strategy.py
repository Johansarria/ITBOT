# strategies/momentum_strategy.py

import pandas as pd
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy
from utils.technical_analysis import calculate_all_indicators

logger = logging.getLogger("strategies.momentum_strategy")

class MomentumStrategy(BaseStrategy):
    def __init__(self):
        super().__init__(
            name="MomentumStrategy",
            description="Estrategia simple que compra si el precio ha subido en el último período y vende si ha bajado."
        )
        self.momentum_period = 10 # Número de períodos para calcular el momentum

    def analyze(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        if len(historical_data) < self.momentum_period:
            return {"decision": "MANTENER", "score": 0}

        # Calcular el momentum: (precio actual / precio de hace N períodos) - 1
        current_price = historical_data["close"].iloc[-1]
        past_price = historical_data["close"].iloc[-self.momentum_period]
        
        momentum = (current_price / past_price) - 1
        
        decision = "MANTENER"
        score = 0

        if momentum > 0.02: # Si el precio ha subido más de un 2%
            decision = "COMPRAR"
            score = 1
        elif momentum < -0.02: # Si el precio ha bajado más de un 2%
            decision = "VENDER"
            score = -1

        return {
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "decision": decision,
            "score": score,
            "momentum_pct": round(momentum * 100, 2)
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {"momentum_period": self.momentum_period}

    def set_parameters(self, params: Dict[str, Any]):
        if "momentum_period" in params:
            self.momentum_period = int(params["momentum_period"])
