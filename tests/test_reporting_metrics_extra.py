import pandas as pd
from utils import reporting_metrics


def test_generate_report_empty(monkeypatch):
    monkeypatch.setattr(reporting_metrics, 'fetch_operations_df', lambda start=None, end=None: pd.DataFrame())
    out = reporting_metrics.generate_report()
    assert 'No hay operaciones' in out


def test_generate_report_with_values(monkeypatch):
    df = pd.DataFrame({
        'timestamp_open': ['2025-01-01', '2025-01-02', '2025-01-03'],
        'pnl_usdt': [10.0, -5.0, 2.5],
        'pnl_percent': [1.0, -0.5, 0.25]
    })
    monkeypatch.setattr(reporting_metrics, 'fetch_operations_df', lambda start=None, end=None: df)
    out = reporting_metrics.generate_report()
    assert 'Total de operaciones' in out
    assert 'P&L total' in out
