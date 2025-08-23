import pandas as pd
import numpy as np
import asyncio

from utils import technical_analysis as ta


from utils.feature_pipeline import FeaturePipeline

def test_calculate_all_indicators_empty():
    df = pd.DataFrame()
    pipeline = FeaturePipeline()
    out = pipeline.transform(df)
    assert out.empty


def test_calculate_all_indicators_basic():
    idx = pd.date_range("2025-01-01", periods=30, freq="h")
    df = pd.DataFrame({'open': np.linspace(100, 120, len(idx)),
                       'high': np.linspace(101, 121, len(idx)),
                       'low': np.linspace(99, 119, len(idx)),
                       'close': np.linspace(100, 120, len(idx)),
                       'volume': np.linspace(10, 20, len(idx))}, index=idx)
    pipeline = FeaturePipeline()
    out = pipeline.transform(df.copy())
    # Check that indicators columns exist
    for col in ['rsi','macd','macd_signal','stoch_k','stoch_d','cci','adx','plus_di','minus_di','atr','bb_upper','bb_lower']:
        assert col in out.columns
    # No NaNs after calculation
    assert not out.isnull().values.any()
