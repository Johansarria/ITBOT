import pandas as pd
from typing import Dict, Any
from strategies.base_strategy import BaseStrategy

class AdaptiveRuleStrategy(BaseStrategy):
    """
    Estrategia de ejemplo: toma decisiones usando reglas avanzadas y autoadaptativas sobre features enriquecidos.
    - Si hay cruce alcista de medias y RSI < 70 y volatilidad baja, compra.
    - Si hay cruce bajista de medias y RSI > 30 y volatilidad alta, vende.
    - Si el drawdown reciente supera cierto umbral, reduce tamaño de posición (simulado).
    - Ajusta umbrales automáticamente según el rendimiento reciente (autoadaptativo simple).
    """
    def __init__(self, name="AdaptiveRuleStrategy", description="Estrategia de reglas avanzadas y autoadaptativas."):
        super().__init__(name, description)
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        self.volatility_threshold = 0.03
        self.drawdown_limit = 0.10
        self.performance_window = 50
        self.last_adaptation = None

    async def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        df = df.copy()
        latest = df.iloc[-1]
        decision = "MANTENER"
        score = 0
        # Reglas principales
        if latest.get("bullish_cross", 0) and latest.get("rsi_14", 50) < self.rsi_overbought and latest.get("volatility_20", 0) < self.volatility_threshold:
            decision = "COMPRAR"
            score = 1
        elif latest.get("bearish_cross", 0) and latest.get("rsi_14", 50) > self.rsi_oversold and latest.get("volatility_20", 0) > self.volatility_threshold:
            decision = "VENDER"
            score = -1
        # Drawdown adaptativo (simulado)
        if "cum_return" in df.columns:
            rolling_max = df["cum_return"].rolling(self.performance_window, min_periods=1).max()
            drawdown = (df["cum_return"] - rolling_max) / (rolling_max + 1e-9)
            max_drawdown = drawdown.min()
            if max_drawdown < -self.drawdown_limit:
                decision = "REDUCIR_POSICION"
                score = -0.5
        # Adaptación simple de umbrales
        if self.last_adaptation is None or len(df) - self.last_adaptation > self.performance_window:
            recent_returns = df["returns"].tail(self.performance_window)
            avg_return = recent_returns.mean()
            if avg_return < 0:
                self.volatility_threshold *= 0.95
            else:
                self.volatility_threshold *= 1.05
            self.last_adaptation = len(df)
        return {
            "decision": decision,
            "score": score,
            "rsi": latest.get("rsi_14", None),
            "volatility": latest.get("volatility_20", None),
            "drawdown": float(max_drawdown) if 'max_drawdown' in locals() else None
        }

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "rsi_overbought": self.rsi_overbought,
            "rsi_oversold": self.rsi_oversold,
            "volatility_threshold": self.volatility_threshold,
            "drawdown_limit": self.drawdown_limit,
            "performance_window": self.performance_window
        }

    def set_parameters(self, params: Dict[str, Any]):
        for k, v in params.items():
            if hasattr(self, k):
                setattr(self, k, v)
