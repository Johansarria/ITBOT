import pytest
from unittest.mock import patch
import pandas as pd
from utils import reporting_visuals

@patch("utils.reporting_visuals.fetch_operations_df")
def test_plot_equity_curve_and_histogram(mock_fetch):
    df = pd.DataFrame([
        {"timestamp_open": "2025-08-12 10:00:00", "pnl_usdt": 10},
        {"timestamp_open": "2025-08-12 10:01:00", "pnl_usdt": -5},
        {"timestamp_open": "2025-08-12 10:02:00", "pnl_usdt": 20},
    ])
    mock_fetch.return_value = df
    # No debe lanzar excepción ni retornar None
    eq_df = reporting_visuals.plot_equity_curve(save_path=None)
    hist_df = reporting_visuals.plot_pnl_histogram(save_path=None)
    assert eq_df is not None
    assert hist_df is not None
    assert "equity" in eq_df.columns
