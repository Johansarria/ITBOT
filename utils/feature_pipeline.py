# utils/feature_pipeline.py

import pandas as pd
import numpy as np
import logging
from typing import Optional

# Imports from ta library, as seen in technical_analysis.py
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, CCIIndicator, ADXIndicator
from ta.volatility import AverageTrueRange, BollingerBands

logger = logging.getLogger(__name__)

class FeaturePipeline:
    """
    Encapsula el pipeline de feature engineering para generar features a partir de klines.
    Asegura la consistencia en la generación de features para entrenamiento e inferencia.
    """
    def __init__(self):
        logger.info("FeaturePipeline inicializado.")
        self._feature_columns = [
            'rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci',
            'adx', 'plus_di', 'minus_di', 'atr', 'bb_upper', 'bb_lower',
            'ma_20', 'ma_50', 'volatility_20', 'returns', 'cum_return',
            'volume_sma_20', 'volume_zscore', 'bullish_cross', 'bearish_cross'
        ]

    def _calculate_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula todos los indicadores técnicos y features enriquecidos.
        Esta es la única fuente de verdad para la generación de features.
        """
        if df.empty:
            return df

        # Ensure 'high', 'low', 'close', 'volume' columns are numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # --- Features from technical_analysis.py (using ta library) ---
        logger.debug("Calculando indicadores técnicos con la librería 'ta'.")
        df["rsi"] = RSIIndicator(close=df["close"]).rsi()
        macd = MACD(close=df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        stoch = StochasticOscillator(high=df["high"], low=df["low"], close=df["close"])
        df["stoch_k"] = stoch.stoch()
        df["stoch_d"] = stoch.stoch_signal()
        df["cci"] = CCIIndicator(high=df["high"], low=df["low"], close=df["close"]).cci()
        adx = ADXIndicator(high=df["high"], low=df["low"], close=df["close"])
        df["adx"] = adx.adx()
        df["plus_di"] = adx.adx_pos()
        df["minus_di"] = adx.adx_neg()
        df["atr"] = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"]).average_true_range()
        bb = BollingerBands(close=df["close"])
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()

        # --- Features from feature_engineering.py (non-overlapping) ---
        logger.debug("Calculando features adicionales y estadísticos.")
        df['ma_20'] = df['close'].rolling(window=20).mean()
        df['ma_50'] = df['close'].rolling(window=50).mean()
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volatility_20'] = df['close'].rolling(window=20).std()
        df['returns'] = df['close'].pct_change()
        df['cum_return'] = (1 + df['returns']).cumprod() - 1
        df['volume_zscore'] = (df['volume'] - df['volume'].rolling(20).mean()) / df['volume'].rolling(20).std()
        df['bullish_cross'] = (df['ma_20'] > df['ma_50']).astype(int)
        df['bearish_cross'] = (df['ma_20'] < df['ma_50']).astype(int)

        # Rellenar NaN con 0 después de calcular todos los indicadores
        df.fillna(0, inplace=True)

        logger.debug("Cálculo de todos los features completado.")
        return df


    def transform(self, df_klines: pd.DataFrame) -> pd.DataFrame:
        """
        Aplica todas las transformaciones de feature engineering a un DataFrame de klines.

        Args:
            df_klines (pd.DataFrame): DataFrame de klines con columnas OHLCV.

        Returns:
            pd.DataFrame: DataFrame con las features calculadas.
        """
        if df_klines.empty:
            logger.warning("DataFrame de klines vacío proporcionado al FeaturePipeline. Devolviendo DataFrame vacío.")
            return pd.DataFrame()

        df_processed = df_klines.copy()

        df_processed = self._calculate_all_features(df_processed)

        logger.info("Generación de features completada por FeaturePipeline.")
        return df_processed

    def get_feature_names(self) -> list[str]:
        """
        Devuelve la lista de nombres de las columnas de features generadas.
        """
        return self._feature_columns


# Ejemplo de uso (para pruebas o demostración)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Crear un DataFrame de klines de ejemplo
    data = {
        'open': [100, 102, 105, 103, 106, 108, 110, 109, 112, 115] * 5,
        'high': [103, 106, 107, 105, 108, 110, 112, 111, 114, 117] * 5,
        'low': [99, 101, 103, 102, 104, 106, 108, 107, 110, 113] * 5,
        'close': [102, 105, 103, 106, 108, 110, 109, 112, 115, 114] * 5,
        'volume': [1000, 1200, 1100, 1300, 1050, 1150, 1250, 1000, 1350, 1200] * 5,
        'open_time': pd.to_datetime(pd.date_range(start='2023-01-01', periods=50, freq='H'))
    }
    df_sample_klines = pd.DataFrame(data)
    # df_sample_klines.set_index('open_time', inplace=True) # The pipeline expects a column, not an index

    pipeline = FeaturePipeline()
    df_features = pipeline.transform(df_sample_klines)

    print("\n--- Features Generadas ---")
    print(df_features.head())
    print(f"\nColumnas generadas: {df_features.columns.tolist()}")
    print(f"\nNombres de features según el pipeline: {pipeline.get_feature_names()}")
