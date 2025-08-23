import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import os

from utils.kpi_calculator import (
    get_operations_df,
    calculate_pnl,
    calculate_trade_stats,
    calculate_max_drawdown,
    calculate_trade_frequency_and_duration,
    get_today_summary
)

# Fixture for a dummy DataFrame
@pytest.fixture
def sample_operations_df():
    data = {
        'timestamp_open': [
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 11, 0, 0),
            datetime(2025, 1, 2, 10, 0, 0),
            datetime(2025, 1, 2, 11, 0, 0),
            datetime(2025, 1, 3, 10, 0, 0),
        ],
        'timestamp_close': [
            datetime(2025, 1, 1, 10, 30, 0),
            datetime(2025, 1, 1, 11, 45, 0),
            datetime(2025, 1, 2, 10, 15, 0),
            datetime(2025, 1, 2, 11, 30, 0),
            datetime(2025, 1, 3, 10, 50, 0),
        ],
        'pnl_usdt': [10.0, -5.0, 20.0, -10.0, 15.0],
        'pnl_percent': [1.0, -0.5, 2.0, -1.0, 1.5],
        'size_usdt': [1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
    }
    df = pd.DataFrame(data)
    # Ensure datetime columns are timezone-naive for consistency if not explicitly handled
    for col in ['timestamp_open', 'timestamp_close']:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)
    return df

# --- Tests for get_operations_df ---
@patch('utils.kpi_calculator.get_db_connection')
@patch('pandas.read_sql_query')
def test_get_operations_df_success(mock_read_sql_query, mock_get_db_connection, sample_operations_df):
    mock_read_sql_query.return_value = sample_operations_df
    mock_conn = MagicMock()
    mock_get_db_connection.return_value.__enter__.return_value = mock_conn

    df = get_operations_df(days=30)

    mock_get_db_connection.assert_called_once()
    mock_read_sql_query.assert_called_once()
    assert not df.empty
    assert len(df) == len(sample_operations_df)
    assert 'timestamp_open' in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp_open'])

@patch('utils.kpi_calculator.get_db_connection')
@patch('pandas.read_sql_query')
def test_get_operations_df_empty(mock_read_sql_query, mock_get_db_connection):
    mock_read_sql_query.return_value = pd.DataFrame()
    mock_conn = MagicMock()
    mock_get_db_connection.return_value.__enter__.return_value = mock_conn

    df = get_operations_df(days=30)

    mock_get_db_connection.assert_called_once()
    mock_read_sql_query.assert_called_once()
    assert df.empty

@patch('utils.kpi_calculator.get_db_connection')
@patch('pandas.read_sql_query')
def test_get_operations_df_exception(mock_read_sql_query, mock_get_db_connection):
    mock_read_sql_query.side_effect = Exception("DB Error")
    mock_conn = MagicMock()
    mock_get_db_connection.return_value.__enter__.return_value = mock_conn

    df = get_operations_df(days=30)

    mock_get_db_connection.assert_called_once()
    mock_read_sql_query.assert_called_once()
    assert df.empty

@patch('utils.kpi_calculator.get_db_connection')
@patch('pandas.read_sql_query')
def test_get_operations_df_column_conversion(mock_read_sql_query, mock_get_db_connection):
    # Create a DataFrame with string dates and numeric columns as strings
    raw_data = {
        'timestamp_open': ['2025-01-01 10:00:00', '2025-01-02 11:00:00'],
        'timestamp_close': ['2025-01-01 10:30:00', '2025-01-02 11:45:00'],
        'pnl_usdt': ['10.0', '-5.0'],
        'pnl_percent': ['1.0', '-0.5'],
        'size_usdt': ['1000.0', '1000.0'],
        'other_col': ['abc', 'def'] # A non-numeric column
    }
    mock_read_sql_query.return_value = pd.DataFrame(raw_data)
    mock_conn = MagicMock()
    mock_get_db_connection.return_value.__enter__.return_value = mock_conn

    df = get_operations_df(days=30)

    assert pd.api.types.is_datetime64_any_dtype(df['timestamp_open'])
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp_close'])
    assert pd.api.types.is_float_dtype(df['pnl_usdt'])
    assert pd.api.types.is_float_dtype(df['pnl_percent'])
    assert pd.api.types.is_float_dtype(df['size_usdt'])
    assert df['pnl_usdt'].iloc[0] == 10.0
    assert df['size_usdt'].iloc[1] == 1000.0
    assert df['other_col'].iloc[0] == 'abc' # Ensure other columns are untouched

# --- Tests for calculate_pnl ---
def test_calculate_pnl_basic(sample_operations_df):
    pnl_data = calculate_pnl(sample_operations_df)
    assert pnl_data["total_pnl_usdt"] == 30.0
    assert not pnl_data["daily_pnl_df"].empty
    assert pnl_data["daily_pnl_df"].iloc[0]['daily_pnl'] == 5.0 # 10.0 - 5.0
    assert pnl_data["daily_pnl_df"].iloc[1]['daily_pnl'] == 10.0 # 20.0 - 10.0
    assert pnl_data["daily_pnl_df"].iloc[2]['daily_pnl'] == 15.0

def test_calculate_pnl_empty_df():
    df = pd.DataFrame()
    pnl_data = calculate_pnl(df)
    assert pnl_data["total_pnl_usdt"] == 0
    assert pnl_data["daily_pnl_df"].empty

def test_calculate_pnl_missing_pnl_usdt_column():
    data = {
        'timestamp_open': [
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 11, 0, 0),
        ],
        'pnl_percent': [1.0, -0.5],
        'size_usdt': [1000.0, 1000.0],
    }
    df = pd.DataFrame(data)
    df['timestamp_open'] = df['timestamp_open'].dt.tz_localize(None)

    pnl_data = calculate_pnl(df)
    assert pnl_data["total_pnl_usdt"] == 5.0 # 1000 * 0.01 + 1000 * -0.005 = 10 - 5 = 5
    assert not pnl_data["daily_pnl_df"].empty
    assert pnl_data["daily_pnl_df"].iloc[0]['daily_pnl'] == 5.0

def test_calculate_pnl_with_nan_pnl_usdt():
    data = {
        'timestamp_open': [
            datetime(2025, 1, 1, 10, 0, 0),
            datetime(2025, 1, 1, 11, 0, 0),
        ],
        'pnl_usdt': [10.0, float('nan')],
        'pnl_percent': [1.0, -0.5],
        'size_usdt': [1000.0, 1000.0],
    }
    df = pd.DataFrame(data)
    df['timestamp_open'] = df['timestamp_open'].dt.tz_localize(None)

    pnl_data = calculate_pnl(df)
    assert pnl_data["total_pnl_usdt"] == 10.0 # 10.0 + 0.0 (NaN se convierte a 0) = 10.0
    assert not pnl_data["daily_pnl_df"].empty
    assert pnl_data["daily_pnl_df"].iloc[0]['daily_pnl'] == 5.0

# --- Tests for calculate_trade_stats ---
def test_calculate_trade_stats_basic(sample_operations_df):
    stats = calculate_trade_stats(sample_operations_df)
    assert stats["total_trades"] == 5
    assert stats["winning_trades"] == 3
    assert stats["losing_trades"] == 2
    assert pytest.approx(stats["win_rate"]) == 60.0
    assert pytest.approx(stats["gross_profit"]) == 45.0  # 10 + 20 + 15
    assert pytest.approx(stats["gross_loss"]) == -15.0 # -5 + -10
    assert pytest.approx(stats["profit_factor"]) == 3.0 # 45 / 15
    assert pytest.approx(stats["average_win"]) == 15.0 # 45 / 3
    assert pytest.approx(stats["average_loss"]) == -7.5 # -15 / 2
    # Expectancy = (0.60 * 15.0) + (0.40 * -7.5) = 9.0 - 3.0 = 6.0
    assert pytest.approx(stats["expectancy"]) == 6.0

def test_calculate_trade_stats_empty_df():
    stats = calculate_trade_stats(pd.DataFrame())
    assert stats["total_trades"] == 0
    assert stats["win_rate"] == 0.0
    assert stats["profit_factor"] == 0.0
    assert stats["expectancy"] == 0.0

def test_calculate_trade_stats_no_losses(sample_operations_df):
    winning_df = sample_operations_df[sample_operations_df['pnl_usdt'] > 0].copy()
    stats = calculate_trade_stats(winning_df)
    assert stats["total_trades"] == 3
    assert stats["winning_trades"] == 3
    assert stats["losing_trades"] == 0
    assert stats["win_rate"] == 100.0
    assert stats["gross_loss"] == 0.0
    assert stats["profit_factor"] == float('inf')
    assert pytest.approx(stats["average_loss"]) == 0.0
    assert pytest.approx(stats["expectancy"]) == 15.0 # (1.0 * 15.0) + (0.0 * 0.0) = 15.0

def test_calculate_trade_stats_no_wins(sample_operations_df):
    losing_df = sample_operations_df[sample_operations_df['pnl_usdt'] < 0].copy()
    stats = calculate_trade_stats(losing_df)
    assert stats["total_trades"] == 2
    assert stats["winning_trades"] == 0
    assert stats["losing_trades"] == 2
    assert stats["win_rate"] == 0.0
    assert stats["gross_profit"] == 0.0
    assert stats["profit_factor"] == 0.0
    assert pytest.approx(stats["average_win"]) == 0.0
    assert pytest.approx(stats["expectancy"]) == -7.5 # (0.0 * 0.0) + (1.0 * -7.5) = -7.5

def test_calculate_trade_stats_missing_pnl_usdt():
    data = {
        'pnl_percent': [1.0, -0.5],
        'size_usdt': [1000.0, 1000.0],
    }
    df = pd.DataFrame(data)
    stats = calculate_trade_stats(df)
    assert stats["total_trades"] == 2
    assert stats["winning_trades"] == 1
    assert stats["losing_trades"] == 1
    assert pytest.approx(stats["gross_profit"]) == 10.0
    assert pytest.approx(stats["gross_loss"]) == -5.0
    assert pytest.approx(stats["profit_factor"]) == 2.0

# --- Tests for calculate_max_drawdown ---
def test_calculate_max_drawdown_basic(sample_operations_df):
    # Equity curve calculation:
    # Initial balance: 1000
    # 1. 1000 + 10 = 1010 (Peak)
    # 2. 1010 - 5 = 1005 (Drawdown: (1005-1010)/1010 = -0.00495)
    # 3. 1005 + 20 = 1025 (New Peak)
    # 4. 1025 - 10 = 1015 (Drawdown: (1015-1025)/1025 = -0.00975)
    # 5. 1015 + 15 = 1030 (New Peak)
    # Max drawdown is -0.00975 * 100 = -0.975...
    mdd = calculate_max_drawdown(sample_operations_df, initial_balance=1000.0)
    assert pytest.approx(mdd, 0.01) == 0.98 # (1015-1025)/1025 * 100

def test_calculate_max_drawdown_empty_df():
    mdd = calculate_max_drawdown(pd.DataFrame())
    assert mdd == 0.0

def test_calculate_max_drawdown_all_wins(sample_operations_df):
    winning_df = sample_operations_df[sample_operations_df['pnl_usdt'] > 0].copy()
    mdd = calculate_max_drawdown(winning_df)
    assert mdd == 0.0

def test_calculate_max_drawdown_missing_pnl_usdt():
    data = {
        'timestamp_open': [datetime(2025, 1, 1), datetime(2025, 1, 2)],
        'pnl_percent': [10.0, -5.0], # +100, -50
        'size_usdt': [1000.0, 1000.0],
    }
    df = pd.DataFrame(data)
    # Equity: 1000 -> 1100 -> 1050
    # Drawdown: (1050 - 1100) / 1100 = -0.04545
    mdd = calculate_max_drawdown(df, initial_balance=1000)
    assert pytest.approx(mdd, 0.01) == 4.55

# --- Tests for calculate_trade_frequency_and_duration ---
def test_calculate_trade_frequency_and_duration_basic(sample_operations_df):
    stats = calculate_trade_frequency_and_duration(sample_operations_df)
    # 5 trades over 3 days. Day 1: 2, Day 2: 2, Day 3: 1. Mean = (2+2+1)/3 = 1.66
    assert pytest.approx(stats["trades_per_day"]) == (2+2+1)/3
    # Durations in minutes: 30, 45, 15, 30, 50. Mean = (30+45+15+30+50)/5 = 170/5 = 34
    assert pytest.approx(stats["avg_trade_duration_minutes"]) == 34.0

def test_calculate_trade_frequency_and_duration_empty_df():
    stats = calculate_trade_frequency_and_duration(pd.DataFrame())
    assert stats["trades_per_day"] == 0.0
    assert stats["avg_trade_duration_minutes"] == 0.0

def test_calculate_trade_frequency_and_duration_missing_timestamps():
    data = {
        'timestamp_open': [datetime(2025, 1, 1), None],
        'timestamp_close': [None, datetime(2025, 1, 1, 1, 0)],
    }
    df = pd.DataFrame(data)
    stats = calculate_trade_frequency_and_duration(df)
    assert stats["trades_per_day"] == 1.0
    assert stats["avg_trade_duration_minutes"] == 0.0

def test_calculate_trade_frequency_and_duration_invalid_duration():
    data = {
        'timestamp_open': [datetime(2025, 1, 1, 1, 0)],
        'timestamp_close': [datetime(2025, 1, 1, 0, 0)], # close before open
    }
    df = pd.DataFrame(data)
    stats = calculate_trade_frequency_and_duration(df)
    assert stats["avg_trade_duration_minutes"] == 0.0

def test_calculate_trade_frequency_and_duration_missing_column():
    data = {
        'timestamp_open': [datetime(2025, 1, 1, 1, 0)],
    }
    df = pd.DataFrame(data)
    stats = calculate_trade_frequency_and_duration(df)
    assert stats["avg_trade_duration_minutes"] == 0.0
    assert stats["trades_per_day"] == 0.0 # Changed from 1.0 to 0.0

# --- Tests for get_today_summary ---
@patch('utils.kpi_calculator.os.path.exists')
@patch('utils.kpi_calculator.pd.read_csv')
def test_get_today_summary_file_found(mock_read_csv, mock_exists):
    mock_exists.return_value = True
    today_str = datetime.now().strftime('%Y-%m-%d')
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    csv_data = {
        'timestamp_open': [f'{today_str} 10:00', f'{today_str} 11:00', f'{yesterday_str} 12:00'],
        'pnl_percent': [1.5, -0.5, 5.0]
    }
    mock_read_csv.return_value = pd.DataFrame(csv_data)

    summary = get_today_summary('dummy_path.csv')

    assert summary["pnl_sum"] == 1.0
    assert summary["ops_count"] == 2
    assert summary["wins"] == 1
    assert summary["losses"] == 1

@patch('utils.kpi_calculator.os.path.exists')
def test_get_today_summary_file_not_found(mock_exists):
    mock_exists.return_value = False
    summary = get_today_summary('non_existent_path.csv')
    assert summary["pnl_sum"] == 0.0
    assert summary["ops_count"] == 0

@patch('utils.kpi_calculator.os.path.exists')
@patch('utils.kpi_calculator.pd.read_csv')
def test_get_today_summary_empty_file(mock_read_csv, mock_exists):
    mock_exists.return_value = True
    mock_read_csv.return_value = pd.DataFrame({'timestamp_open': [], 'pnl_percent': []})

    summary = get_today_summary('dummy_path.csv')

    assert summary["pnl_sum"] == 0.0
    assert summary["ops_count"] == 0

@patch('utils.kpi_calculator.os.path.exists')
@patch('utils.kpi_calculator.pd.read_csv')
def test_get_today_summary_no_ops_today(mock_read_csv, mock_exists):
    mock_exists.return_value = True
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    csv_data = {
        'timestamp_open': [f'{yesterday_str} 12:00'],
        'pnl_percent': [5.0]
    }
    mock_read_csv.return_value = pd.DataFrame(csv_data)

    summary = get_today_summary('dummy_path.csv')

    assert summary["pnl_sum"] == 0.0
    assert summary["ops_count"] == 0

@patch('utils.kpi_calculator.os.path.exists')
@patch('utils.kpi_calculator.pd.read_csv')
def test_get_today_summary_exception(mock_read_csv, mock_exists):
    mock_exists.return_value = True
    mock_read_csv.side_effect = Exception("Read Error")

    summary = get_today_summary('dummy_path.csv')

    assert summary["pnl_sum"] == 0.0
    assert summary["ops_count"] == 0
