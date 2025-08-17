import pytest
from utils.reporting_metrics import generate_report
from unittest.mock import patch
import pandas as pd

@patch("utils.reporting_metrics.fetch_operations_df")
def test_generate_report_basic(mock_fetch):
    df = pd.DataFrame([
        {"pnl_usdt": 10, "pnl_percent": 1},
        {"pnl_usdt": -5, "pnl_percent": -0.5},
        {"pnl_usdt": 0, "pnl_percent": 0},
        {"pnl_usdt": 20, "pnl_percent": 2},
    ])
    mock_fetch.return_value = df
    report = generate_report()
    assert "Total de operaciones: 4" in report
    assert "P&L total: 25.00 USDT" in report
    assert "Winrate: 50.0%" in report
    assert "Operaciones ganadoras: 2" in report
    assert "Operaciones perdedoras: 1" in report
