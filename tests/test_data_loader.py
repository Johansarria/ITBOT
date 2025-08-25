import pytest
import pandas as pd
from unittest.mock import patch
from utils.data_loader import load_operations_data

@pytest.mark.asyncio
async def test_load_operations_data_file_not_found():
    """Test that an empty DataFrame is returned if the file doesn't exist."""
    df = await load_operations_data("non_existent_file.csv")
    assert df.empty
    assert isinstance(df, pd.DataFrame)

@pytest.mark.asyncio
async def test_load_operations_data_read_error():
    """Test that an empty DataFrame is returned on a pandas read error."""
    # We need a dummy file to exist for the function to attempt reading it.
    with patch('os.path.exists', return_value=True):
        with patch('pandas.read_csv', side_effect=Exception("CSV parsing error")):
            df = await load_operations_data("dummy_path.csv")
            assert df.empty
            assert isinstance(df, pd.DataFrame)


@pytest.mark.asyncio
async def test_load_operations_data_happy_path(tmp_path):
    """Test loading a CSV with a perfect, standard schema."""
    csv_content = """operation_id,timestamp_open,timestamp_close,symbol,side,entry_price,exit_price,pnl_percent
1,2023-01-01 10:00,2023-01-01 11:00,BTCUSDT,BUY,50000,51000,2.0
"""
    file_path = tmp_path / "standard.csv"
    file_path.write_text(csv_content)

    df = await load_operations_data(str(file_path))

    assert not df.empty
    assert len(df) == 1
    assert 'operation_id' in df.columns
    assert df['pnl_percent'].iloc[0] == 2.0

@pytest.mark.asyncio
async def test_load_operations_data_column_aliasing(tmp_path):
    """Test that columns are correctly renamed from their aliases."""
    # Using different aliases from the COLUMN_ALIASES map
    csv_content = """id,timestamp,close_time,asset,trade_type,price_in,price_out,pnl
1,2023-01-01 10:00,2023-01-01 11:00,ETHUSDT,SELL,3000,2900,-3.33
"""
    file_path = tmp_path / "aliased.csv"
    file_path.write_text(csv_content)

    df = await load_operations_data(str(file_path))

    assert not df.empty
    # Check that standard names are present
    from utils.data_loader import REQUIRED_COLUMNS
    for col in REQUIRED_COLUMNS:
        assert col in df.columns

    # Check that aliased names are gone
    assert 'id' not in df.columns
    assert 'pnl' not in df.columns
    assert df['symbol'].iloc[0] == 'ETHUSDT'

@pytest.mark.asyncio
async def test_load_operations_data_missing_required_column(tmp_path):
    """Test that an empty DataFrame is returned if a required column is missing."""
    # Missing 'symbol' which is in REQUIRED_COLUMNS
    csv_content = """operation_id,timestamp_open,timestamp_close,side,entry_price,exit_price,pnl_percent
1,2023-01-01 10:00,2023-01-01 11:00,BUY,50000,51000,2.0
"""
    file_path = tmp_path / "missing_col.csv"
    file_path.write_text(csv_content)

    df = await load_operations_data(str(file_path))

    assert df.empty


# --- Tests for Date Parsing ---

@pytest.mark.asyncio
async def test_load_operations_data_date_parsing_standard(tmp_path):
    """Test standard date columns are parsed correctly."""
    csv_content = """operation_id,timestamp_open,timestamp_close,symbol,side,entry_price,exit_price,pnl_percent
1,2023-01-01 10:00:00,2023-01-01 11:00:00,BTC,B,1,2,100
"""
    file_path = tmp_path / "dates.csv"
    file_path.write_text(csv_content)
    df = await load_operations_data(str(file_path))

    assert not df.empty
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp_open'])
    assert df['timestamp_open'].iloc[0] == pd.to_datetime('2023-01-01 10:00:00')

@pytest.mark.asyncio
async def test_load_operations_data_date_parsing_aliased(tmp_path):
    """Test aliased date columns are parsed and original columns are dropped."""
    csv_content = """operation_id,timestamp,close_time,symbol,side,entry_price,exit_price,pnl_percent
1,2023-02-01 12:00,2023-02-01 13:00,ETH,S,3,2,-33
"""
    file_path = tmp_path / "aliased_dates.csv"
    file_path.write_text(csv_content)
    df = await load_operations_data(str(file_path))

    assert not df.empty
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp_open'])
    assert pd.api.types.is_datetime64_any_dtype(df['timestamp_close'])
    assert 'timestamp' not in df.columns # Original aliased column should be dropped
    assert 'close_time' not in df.columns

@pytest.mark.asyncio
async def test_load_operations_data_date_parsing_coerce_errors(tmp_path):
    """Test that malformed dates are coerced to NaT."""
    csv_content = """operation_id,timestamp_open,timestamp_close,symbol,side,entry_price,exit_price,pnl_percent
1,2023-01-01 10:00,not-a-date,BTC,B,1,2,100
2,invalid-date,2023-01-02 11:00,BTC,B,1,2,100
"""
    file_path = tmp_path / "bad_dates.csv"
    file_path.write_text(csv_content)
    df = await load_operations_data(str(file_path))

    assert not df.empty
    assert pd.isna(df['timestamp_close'].iloc[0]) # Check for NaT
    assert pd.isna(df['timestamp_open'].iloc[1])

@pytest.mark.asyncio
async def test_load_operations_data_date_parsing_missing_column(tmp_path):
    """Test that a missing required date column is created with NaT."""
    # timestamp_close is missing
    csv_content = """operation_id,timestamp_open,symbol,side,entry_price,exit_price,pnl_percent
1,2023-01-01 10:00,BTC,B,1,2,100
"""
    file_path = tmp_path / "missing_date.csv"
    file_path.write_text(csv_content)
    df = await load_operations_data(str(file_path))

    assert not df.empty
    assert 'timestamp_close' in df.columns
    assert pd.isna(df['timestamp_close'].iloc[0])
