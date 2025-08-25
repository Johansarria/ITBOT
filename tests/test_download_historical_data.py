# tests/test_download_historical_data.py

import asyncio
import pandas as pd
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from binance.exceptions import BinanceAPIException

from download_historical_data import download_and_save_klines

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_binance_client():
    """Fixture to mock the Binance client."""
    mock_client = MagicMock()
    # Mock the async method using AsyncMock
    mock_client.get_historical_klines = AsyncMock()
    return mock_client

@pytest.fixture
def mock_db_add_klines():
    """Fixture to mock the database add_klines function."""
    with patch('download_historical_data.add_klines') as mock_add:
        yield mock_add

@pytest.fixture
def mock_os_and_pandas():
    """Fixture to mock file system operations."""
    with patch('os.path.exists') as mock_exists, \
         patch('os.makedirs') as mock_makedirs, \
         patch('pandas.DataFrame.to_csv') as mock_to_csv, \
         patch('pandas.read_csv') as mock_read_csv:
        # Configure mocks
        mock_exists.return_value = False
        yield {
            "exists": mock_exists,
            "makedirs": mock_makedirs,
            "to_csv": mock_to_csv,
            "read_csv": mock_read_csv
        }

@patch('download_historical_data.get_binance_client', new_callable=AsyncMock)
async def test_download_and_save_klines_happy_path(
    mock_get_client, mock_os_and_pandas, mock_db_add_klines, mock_binance_client
):
    """
    Test the happy path where data is downloaded and saved correctly for the first time.
    """
    # Arrange
    mock_get_client.return_value = mock_binance_client

    # Sample klines data from Binance API
    sample_klines = [
        [1672531200000, '20000', '20100', '19900', '20050', '100', 1672534799999, '2005000', 1000, '50', '1002500', '0'],
        [1672534800000, '20050', '20150', '20000', '20100', '120', 1672538399999, '2412000', 1200, '60', '1206000', '0']
    ]
    # Since get_historical_klines is run in a thread, we can't use await on its mock.
    # We mock the regular method on the client mock.
    mock_binance_client.get_historical_klines = MagicMock(return_value=sample_klines)

    # Act
    result_df = await download_and_save_klines(
        symbol="BTCUSDT",
        interval="1h",
        start_str="1 Jan, 2023",
        end_str="2 Jan, 2023",
        output_path="test_data/",
        append_to_existing=False
    )

    # Assert
    # 1. Check if binance client was called correctly
    mock_get_client.assert_awaited_once()
    # The method is called inside asyncio.to_thread, so we check the regular mock call
    mock_binance_client.get_historical_klines.assert_called_once_with(
        symbol="BTCUSDT",
        interval="1h",
        start_str="1 Jan, 2023",
        end_str="2 Jan, 2023"
    )

    # 2. Check if filesystem operations were called
    mock_os_and_pandas["makedirs"].assert_called_once_with("test_data/", exist_ok=True)
    mock_os_and_pandas["to_csv"].assert_called_once()

    # 3. Check if database function was called
    mock_db_add_klines.assert_called_once()

    # 4. Check the returned DataFrame
    assert not result_df.empty
    assert len(result_df) == 2
    assert result_df.index[0] == pd.to_datetime("2023-01-01 00:00:00")
    assert list(result_df.columns) == ["open", "high", "low", "close", "volume", "close_time",
                                       "quote_asset_volume", "number_of_trades", "taker_buy_base_volume",
                                       "taker_buy_quote_volume", "ignore"]

@patch('download_historical_data.get_binance_client', new_callable=AsyncMock)
async def test_download_and_save_klines_append_mode(
    mock_get_client, mock_os_and_pandas, mock_db_add_klines, mock_binance_client
):
    """
    Test that the function correctly appends data to an existing file.
    """
    # Arrange
    mock_get_client.return_value = mock_binance_client
    mock_os_and_pandas["exists"].return_value = True

    # Existing data in the CSV file
    existing_data = {
        "timestamp": [pd.to_datetime("2023-01-01 00:00:00")],
        "open": [19000], "high": [19100], "low": [18900], "close": [19050], "volume": [80]
    }
    existing_df = pd.DataFrame(existing_data).set_index("timestamp")
    mock_os_and_pandas["read_csv"].return_value = existing_df

    # New klines data to be downloaded
    new_klines = [
        [1672534800000, '20050', '20150', '20000', '20100', '120', 1672538399999, '2412000', 1200, '60', '1206000', '0']
    ]
    mock_binance_client.get_historical_klines = MagicMock(return_value=new_klines)

    # Act
    await download_and_save_klines(
        symbol="BTCUSDT",
        interval="1h",
        start_str="1 Jan, 2023", # Original start_str
        output_path="test_data/",
        append_to_existing=True # Enable append mode
    )

    # Assert
    # 1. Check that the existing file was checked and read
    mock_os_and_pandas["exists"].assert_called_once()
    mock_os_and_pandas["read_csv"].assert_called_once()

    # 2. Check that get_historical_klines was called with the adjusted start time
    # The last timestamp in existing data is 2023-01-01 00:00:00.
    # The code adds 1ms and formats it.
    expected_start_str = (pd.to_datetime("2023-01-01 00:00:00") + pd.Timedelta(milliseconds=1)).strftime("%d %b, %Y %H:%M:%S")
    mock_binance_client.get_historical_klines.assert_called_once_with(
        symbol="BTCUSDT",
        interval="1h",
        start_str=expected_start_str,
        end_str=None
    )

    # 3. Check that data was saved in append mode
    mock_os_and_pandas["to_csv"].assert_called_once()
    # Get the arguments passed to to_csv
    args, kwargs = mock_os_and_pandas["to_csv"].call_args
    assert kwargs['mode'] == 'a'
    assert not kwargs['header'] # Header should not be written in append mode

    # 4. Check if database function was called
    mock_db_add_klines.assert_called_once()

@patch('download_historical_data.get_binance_client', new_callable=AsyncMock)
async def test_download_no_new_data(
    mock_get_client, mock_os_and_pandas, mock_db_add_klines, mock_binance_client
):
    """
    Test that nothing is saved when the Binance API returns no new data.
    """
    # Arrange
    mock_get_client.return_value = mock_binance_client
    mock_binance_client.get_historical_klines = MagicMock(return_value=[]) # No data

    # Act
    result_df = await download_and_save_klines()

    # Assert
    assert result_df.empty
    mock_os_and_pandas["to_csv"].assert_not_called()
    mock_db_add_klines.assert_not_called()

@patch('download_historical_data.get_binance_client', new_callable=AsyncMock)
async def test_binance_api_exception(
    mock_get_client, mock_os_and_pandas, mock_db_add_klines, mock_binance_client
):
    """
    Test that the function handles BinanceAPIException gracefully.
    """
    # Arrange
    mock_get_client.return_value = mock_binance_client
    # The exception requires response, status_code, and text
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Invalid request"
    mock_binance_client.get_historical_klines.side_effect = BinanceAPIException(mock_response, mock_response.status_code, mock_response.text)

    # Act
    result_df = await download_and_save_klines()

    # Assert
    assert result_df.empty
    mock_os_and_pandas["to_csv"].assert_not_called()
    mock_db_add_klines.assert_not_called()

@patch('download_historical_data.get_binance_client', new_callable=AsyncMock)
async def test_generic_exception(
    mock_get_client, mock_os_and_pandas, mock_db_add_klines, mock_binance_client
):
    """
    Test that the function handles a generic Exception gracefully.
    """
    # Arrange
    mock_get_client.return_value = mock_binance_client
    mock_binance_client.get_historical_klines.side_effect = Exception("Generic Error")

    # Act
    result_df = await download_and_save_klines()

    # Assert
    assert result_df.empty
    mock_os_and_pandas["to_csv"].assert_not_called()
    mock_db_add_klines.assert_not_called()

@patch('download_historical_data.get_binance_client', new_callable=AsyncMock)
async def test_append_mode_read_error(
    mock_get_client, mock_os_and_pandas, mock_db_add_klines, mock_binance_client
):
    """
    Test that append mode falls back to a full download if reading the existing file fails.
    """
    # Arrange
    mock_get_client.return_value = mock_binance_client
    mock_os_and_pandas["exists"].return_value = True
    mock_os_and_pandas["read_csv"].side_effect = Exception("Cannot read CSV")

    sample_klines = [
        [1672531200000, '20000', '20100', '19900', '20050', '100', 1672534799999, '2005000', 1000, '50', '1002500', '0']
    ]
    mock_binance_client.get_historical_klines = MagicMock(return_value=sample_klines)

    # Act
    await download_and_save_klines(
        start_str="1 Jan, 2023",
        append_to_existing=True
    )

    # Assert
    # Check that get_historical_klines was called with the original start_str, not a calculated one
    mock_binance_client.get_historical_klines.assert_called_once_with(
        symbol="BTCUSDT",
        interval="1h",
        start_str="1 Jan, 2023", # Original start_str
        end_str=None
    )
    # Check that the file is written in write mode ('w'), not append mode ('a')
    mock_os_and_pandas["to_csv"].assert_called_once()
    args, kwargs = mock_os_and_pandas["to_csv"].call_args
    assert kwargs['mode'] == 'w' # Should fall back to write mode
    assert kwargs['header'] is True # Header should be written as it's a fresh write

@patch('download_historical_data.get_binance_client', new_callable=AsyncMock)
async def test_data_inconsistency_warning(
    mock_get_client, mock_os_and_pandas, mock_db_add_klines, mock_binance_client, caplog
):
    """
    Test that a warning is logged for inconsistent data (low > high).
    """
    # Arrange
    mock_get_client.return_value = mock_binance_client
    inconsistent_klines = [
        # open, high, low, close -> low is higher than high
        [1672531200000, '20000', '19900', '20100', '20050', '100', 1672534799999, '2005000', 1000, '50', '1002500', '0']
    ]
    mock_binance_client.get_historical_klines = MagicMock(return_value=inconsistent_klines)

    # Act
    result_df = await download_and_save_klines()

    # Assert
    assert not result_df.empty
    assert "Inconsistencia de precios detectada" in caplog.text
