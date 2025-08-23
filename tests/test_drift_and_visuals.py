import pandas as pd
import numpy as np
import os

from utils import drift_detection
from utils import reporting_visuals
from utils import reporting_metrics


def test_detect_feature_drift_no_drift():
    ref = pd.DataFrame({'a': np.random.normal(0,1,100), 'b': np.random.normal(0,1,100)})
    new = pd.DataFrame({'a': np.random.normal(0,1,100), 'b': np.random.normal(0,1,100)})
    drifted = drift_detection.detect_feature_drift(ref, new)
    assert isinstance(drifted, list)


def test_detect_feature_drift_with_drift():
    ref = pd.DataFrame({'a': np.random.normal(0,1,200), 'b': np.random.normal(0,1,200)})
    new = pd.DataFrame({'a': np.random.normal(5,1,200), 'b': np.random.normal(0,1,200)})
    drifted = drift_detection.detect_feature_drift(ref, new)
    assert any(col == 'a' for col, _ in drifted)


def test_plot_equity_and_histogram(tmp_path, monkeypatch):
    # Prepare sample data
    df = pd.DataFrame({
        'timestamp_open': ['2025-01-01','2025-01-02','2025-01-03'],
        'pnl_usdt': [10, -5, 2.5]
    })
    monkeypatch.setattr(reporting_metrics, 'fetch_operations_df', lambda s=None, e=None: df)
    out1 = reporting_visuals.plot_equity_curve(save_path=str(tmp_path / 'equity.png'))
    assert out1 is not None
    assert (tmp_path / 'equity.png').exists()
    out2 = reporting_visuals.plot_pnl_histogram(save_path=str(tmp_path / 'hist.png'))
    assert out2 is not None
    assert (tmp_path / 'hist.png').exists()
