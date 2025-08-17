"""
utils/feature_engineering.py

Funciones para calcular y almacenar features técnicos y estadísticos avanzados para análisis y toma de decisiones autónomas.
"""

import pandas as pd
import numpy as np

def enrich_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indicadores técnicos y estadísticos enriquecidos sobre un DataFrame OHLCV.
    Requiere columnas: ['open', 'high', 'low', 'close', 'volume']
    """
    df = df.copy()
    # Indicadores técnicos clásicos
    df['ma_20'] = df['close'].rolling(window=20).mean()
    df['ma_50'] = df['close'].rolling(window=50).mean()
    df['rsi_14'] = compute_rsi(df['close'], window=14)
    df['macd'], df['macd_signal'] = compute_macd(df['close'])
    df['atr_14'] = compute_atr(df, window=14)
    df['volatility_20'] = df['close'].rolling(window=20).std()
    # Estadísticas adicionales
    df['returns'] = df['close'].pct_change()
    df['cum_return'] = (1 + df['returns']).cumprod() - 1
    df['volume_zscore'] = (df['volume'] - df['volume'].rolling(20).mean()) / df['volume'].rolling(20).std()
    # Señales simples
    df['bullish_cross'] = (df['ma_20'] > df['ma_50']).astype(int)
    df['bearish_cross'] = (df['ma_20'] < df['ma_50']).astype(int)
    return df

def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal

def compute_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=window).mean()
    return atr
