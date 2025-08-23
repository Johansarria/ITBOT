import os
import pandas as pd
import numpy as np
import tempfile
import pytest

from utils import exporter
from utils import technical_analysis as ta


def make_simple_klines(n=200):
    idx = pd.date_range('2023-01-01', periods=n, freq='h')
    close = np.linspace(100, 120, n)
    open_ = close - np.random.rand(n)
    high = np.maximum(open_, close) + np.random.rand(n)
    low = np.minimum(open_, close) - np.random.rand(n)
    df = pd.DataFrame({'open': open_, 'high': high, 'low': low, 'close': close, 'volume': np.ones(n)}, index=idx)
    return df


def test_generate_analysis_chart_and_export(tmp_path):
    df = make_simple_klines(30)
    old_chart_dir = exporter.CHART_DIR
    exporter.CHART_DIR = str(tmp_path)
    try:
        out = exporter.generate_analysis_chart(df, 'TEST', '1h', 'chart.png')
        assert out is not None
        assert os.path.exists(out)
    finally:
        exporter.CHART_DIR = old_chart_dir


from utils.feature_pipeline import FeaturePipeline

def test_calculate_all_indicators_handles_nans_and_returns_columns():
    df = make_simple_klines(200)
    # Insert NaNs in close to trigger the NaN handling warning paths
    df.iloc[5:8, df.columns.get_loc('close')] = np.nan
    pipeline = FeaturePipeline()
    res = pipeline.transform(df.copy())
    # Check that expected indicator columns exist
    for col in ['rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci', 'adx', 'atr', 'bb_upper', 'bb_lower']:
        assert col in res.columns
    # Ensure no NaNs remain after fill
    assert res.isnull().sum().sum() == 0
