import pytest
from utils.reporting_metrics import generate_report, fetch_operations_df
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

@patch("utils.reporting_metrics.psycopg2.connect")
@patch("utils.reporting_metrics.pd.read_sql")
@pytest.mark.parametrize("start, end, expected_query_part, expected_params", [
    (None, None, "SELECT * FROM audit_operations", []),
    ("2023-01-01", None, "WHERE timestamp_open >= %s", ["2023-01-01"]),
    (None, "2023-01-31", "WHERE timestamp_open <= %s", ["2023-01-31"]),
    ("2023-01-01", "2023-01-31", "WHERE timestamp_open >= %s AND timestamp_open <= %s", ["2023-01-01", "2023-01-31"]),
])
def test_fetch_operations_df(mock_read_sql, mock_connect, start, end, expected_query_part, expected_params):
    """
    Tests that fetch_operations_df constructs the correct SQL query based on date filters.
    """
    # Arrange
    mock_conn = mock_connect.return_value.__enter__.return_value

    # Act
    fetch_operations_df(start=start, end=end)

    # Assert
    mock_connect.assert_called_once()
    mock_read_sql.assert_called_once()

    # Check the query string
    actual_query = mock_read_sql.call_args[0][0]
    assert expected_query_part in actual_query

    # Check the parameters
    actual_params = mock_read_sql.call_args.kwargs.get('params')
    assert actual_params == expected_params

@patch("utils.reporting_metrics.fetch_operations_df")
def test_generate_report_empty_dataframe(mock_fetch):
    """
    Tests that generate_report returns a specific message for an empty DataFrame.
    """
    # Arrange
    mock_fetch.return_value = pd.DataFrame()

    # Act
    report = generate_report()

    # Assert
    assert report == "No hay operaciones en el rango seleccionado."

@patch("utils.reporting_metrics.fetch_operations_df")
def test_generate_report_with_non_numeric_pnl(mock_fetch):
    """
    Tests that generate_report handles non-numeric PNL values gracefully.
    """
    # Arrange
    df = pd.DataFrame([
        {"pnl_usdt": 10, "pnl_percent": 1.0},
        {"pnl_usdt": "not a number", "pnl_percent": "invalid"}, # Coerced to NaN
        {"pnl_usdt": -5, "pnl_percent": -0.5},
        {"pnl_usdt": None, "pnl_percent": None} # Ignored
    ])
    mock_fetch.return_value = df

    # Act
    report = generate_report()

    # Assert
    assert "Total de operaciones: 4" in report
    # The sum should skip the non-numeric and None values
    assert "P&L total: 5.00 USDT" in report
    # The winrate should be based on valid numeric trades
    assert "Operaciones ganadoras: 1" in report
    assert "Operaciones perdedoras: 1" in report
