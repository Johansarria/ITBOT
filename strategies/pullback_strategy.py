# strategies/pullback_strategy.py

import pandas as pd
from typing import Dict, Any
import logging

from strategies.base_strategy import BaseStrategy
from utils.feature_pipeline import FeaturePipeline

logger = logging.getLogger(__name__)

class PullbackStrategy(BaseStrategy):
    """
    Estrategia diseñada para operar retrocesos (pullbacks) dentro de una tendencia establecida.
    - Identifica la tendencia principal usando una media móvil de largo plazo (ej. 50-periodos).
    - Espera a que el precio retroceda a una media móvil de corto plazo (ej. 20-periodos).
    - Busca una señal de continuación de la tendencia para entrar en la operación.
    """
    def __init__(self):
        super().__init__(
            name="PullbackStrategy",
            description="Estrategia que opera retrocesos dentro de una tendencia."
        )
        # Parámetros configurables
        self._ma_long_period = 50
        self._ma_short_period = 20
        self._buy_score_threshold = 1 # Umbral simple para la decisión
        self._sell_score_threshold = -1

    async def analyze(self, historical_data: pd.DataFrame, symbol: str, interval: str) -> Dict[str, Any]:
        """
        Implementa la lógica de la estrategia de pullback.
        """
        logger.info(f"Ejecutando análisis para PullbackStrategy en {symbol} ({interval}).")

        feature_pipeline = FeaturePipeline()
        df_indicators = feature_pipeline.transform(historical_data.copy())

        if df_indicators.empty or len(df_indicators) < self._ma_long_period:
            logger.warning("Datos insuficientes para el análisis de pullback.")
            return {"symbol": symbol, "interval": interval, "decision": "DATOS_INSUFICIENTES", "score": 0}

        # Usar los últimos dos puntos de datos para la lógica
        latest = df_indicators.iloc[-1]
        previous = df_indicators.iloc[-2]

        score = 0
        decision = "MANTENER"

        # Definir nombres de las MAs dinámicamente basados en los parámetros
        ma_short_name = f'ma_{self._ma_short_period}'
        ma_long_name = f'ma_{self._ma_long_period}'

        # Verificar que las columnas de MA existan
        if ma_short_name not in df_indicators.columns or ma_long_name not in df_indicators.columns:
            logger.error(f"Las MAs requeridas ({ma_short_name}, {ma_long_name}) no están en el DataFrame.")
            return {"symbol": symbol, "interval": interval, "decision": "ERROR_CONFIG_MA", "score": 0}

        # Lógica de Compra (Uptrend + Pullback)
        is_uptrend = latest['close'] > latest[ma_long_name]
        pullback_to_ma_short = previous['low'] <= previous[ma_short_name]
        bullish_confirmation = latest['close'] > latest['open']

        if is_uptrend and pullback_to_ma_short and bullish_confirmation:
            score = self._buy_score_threshold
            decision = "COMPRAR"
            logger.info(f"Señal de COMPRA por pullback: Uptrend, retroceso a MA{self._ma_short_period} y vela alcista.")

        # Lógica de Venta (Downtrend + Pullback)
        is_downtrend = latest['close'] < latest[ma_long_name]
        pullback_to_ma_short_sell = previous['high'] >= previous[ma_short_name]
        bearish_confirmation = latest['close'] < latest['open']

        if is_downtrend and pullback_to_ma_short_sell and bearish_confirmation:
            score = self._sell_score_threshold
            decision = "VENDER"
            logger.info(f"Señal de VENTA por pullback: Downtrend, retroceso a MA{self._ma_short_period} y vela bajista.")

        return {
            "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "interval": interval,
            "decision": decision,
            "score": score,
            "close": latest['close'],
            "ma_short": latest[ma_short_name],
            "ma_long": latest[ma_long_name]
        }

    def get_parameters(self) -> Dict[str, Any]:
        """
        Devuelve los parámetros actuales de la estrategia.
        """
        return {
            "ma_long_period": self._ma_long_period,
            "ma_short_period": self._ma_short_period,
            "buy_score_threshold": self._buy_score_threshold,
            "sell_score_threshold": self._sell_score_threshold,
        }

    def set_parameters(self, params: Dict[str, Any]):
        """
        Establece los parámetros de la estrategia.
        """
        for key, value in params.items():
            if hasattr(self, f"_{key}"):
                setattr(self, f"_{key}", value)
            else:
                logger.warning(f"Parámetro desconocido para PullbackStrategy: {key}")
