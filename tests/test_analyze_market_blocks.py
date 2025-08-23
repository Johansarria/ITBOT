import pandas as pd
import numpy as np
import asyncio
import types

import pytest

from utils import technical_analysis as ta
from utils.feature_pipeline import FeaturePipeline


@pytest.mark.asyncio
async def test_analyze_market_no_data(monkeypatch):
    # Force get_historical_klines to return empty
    monkeypatch.setattr(ta, 'get_historical_klines', lambda *a, **k: asyncio.Future())
    f = asyncio.Future()
    f.set_result(pd.DataFrame())
    monkeypatch.setattr(ta, 'get_historical_klines', lambda *a, **k: f)
    res = await ta.analyze_market(symbol='X', interval='1m', export=False)
    assert res['decision'].startswith('No hay') or res['decision'] == 'No hay datos para analizar'


@pytest.mark.asyncio
async def test_analyze_market_with_df_and_no_ml(monkeypatch, tmp_path):
    # Prepare a df with enough rows
    idx = pd.date_range('2025-01-01', periods=30, freq='h')
    df = pd.DataFrame({'open': np.linspace(1,2,len(idx)), 'high': np.linspace(1.1,2.1,len(idx)),
                       'low': np.linspace(0.9,1.9,len(idx)), 'close': np.linspace(1,2,len(idx)), 'volume': np.linspace(1,2,len(idx))}, index=idx)

    # Monkeypatch enrich_features to return df as-is and detect_market_regime
    monkeypatch.setattr(ta, 'enrich_features', lambda d: d)
    monkeypatch.setattr(ta, 'detect_market_regime', lambda d: {'volatility_regime': 'LOW', 'trend_regime': 'BULL_TREND'})
    # Ensure ml_model is None
    monkeypatch.setattr(ta, 'ml_model', None)
    # Avoid file exports
    monkeypatch.setattr(ta, 'export_analysis_result', lambda *a, **k: None)
    monkeypatch.setattr(ta, 'export_features', lambda *a, **k: None)

    res = await ta.analyze_market(symbol='X', interval='1m', export=False, df_klines=df)
    assert 'decision' in res
    assert res['symbol'] == 'X'


@pytest.mark.asyncio
async def test_analyze_market_ml_prediction_branch(monkeypatch):
    # Build df
    idx = pd.date_range('2025-01-01', periods=30, freq='h')
    df = pd.DataFrame({'open': np.linspace(1,2,len(idx)), 'high': np.linspace(1.1,2.1,len(idx)),
                       'low': np.linspace(0.9,1.9,len(idx)), 'close': np.linspace(1,2,len(idx)), 'volume': np.linspace(1,2,len(idx))}, index=idx)

    class FakeModel:
        def predict_proba(self, X):
            return [[0.1, 0.9]]

    monkeypatch.setattr(ta, 'enrich_features', lambda d: d)
    monkeypatch.setattr(ta, 'detect_market_regime', lambda d: {'volatility_regime': 'NORMAL', 'trend_regime': 'NEUTRAL'})
    monkeypatch.setattr(ta, 'export_analysis_result', lambda *a, **k: None)
    monkeypatch.setattr(ta, 'export_features', lambda *a, **k: None)
    monkeypatch.setattr(ta, 'ml_model', FakeModel())

    res = await ta.analyze_market(symbol='X', interval='1m', export=False, df_klines=df)
    assert res['decision'] in ('COMPRAR', 'COMPRAR_BAJO', 'MANTENER')
