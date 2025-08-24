import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
import pandas as pd
import numpy as np
import re

from config import settings
from database.database_manager import init_db
from utils.state_manager import StateManager

# This fixture handles the database setup for all tests in this module.
@pytest.fixture(autouse=True)
def setup_integration_db(monkeypatch):
    """
    Sets up a clean, in-memory SQLite database for each integration test.
    """
    original_db_type = settings.DB_TYPE
    original_db_url = settings.DATABASE_URL

    monkeypatch.setattr(settings, 'DB_TYPE', 'sqlite')
    monkeypatch.setattr(settings, 'DATABASE_URL', 'sqlite:///:memory:')
    
    init_db()

    yield

    monkeypatch.setattr(settings, 'DB_TYPE', original_db_type)
    monkeypatch.setattr(settings, 'DATABASE_URL', original_db_url)


@pytest.fixture
def mock_external_services():
    """
    Fixture to mock external services like Telegram and Binance.
    """
    with patch('modules.analisis_bot.send_message', new_callable=AsyncMock) as mock_send_message, \
         patch('modules.analisis_bot.get_historical_klines', new_callable=AsyncMock) as mock_get_klines, \
         patch('utils.binance_client.get_binance_client', new_callable=AsyncMock) as mock_get_binance_client:
        
        mock_binance_instance = AsyncMock()
        mock_get_binance_client.return_value = mock_binance_instance
        
        yield {
            "send_message": mock_send_message,
            "get_historical_klines": mock_get_klines,
            "binance_client": mock_binance_instance
        }


@pytest.mark.asyncio
async def test_full_analisis_flow(mock_external_services):
    # --- Setup Mocks ---
    mock_send_message = mock_external_services["send_message"]
    mock_get_historical_klines = mock_external_services["get_historical_klines"]

    # --- Mock klines data ---
    klines_data = [[1672531200000 + i * 86400000, f"{100+i*0.1}", f"{102+i*0.1}", f"{99+i*0.1}", f"{101+i*0.1}", "10"] for i in range(100)]
    columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df_klines = pd.DataFrame(klines_data, columns=columns)
    # Add other necessary columns with default values
    for col in ["close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"]:
        df_klines[col] = 0
    mock_get_historical_klines.return_value = df_klines

    # --- Mock Strategy Manager and Active Strategy ---
    with patch('strategies.strategy_manager.StrategyManager') as mock_strategy_manager_class:
        mock_strategy_instance = MagicMock()
        mock_strategy_instance.analyze.return_value = {"decision": "COMPRAR", "score": 3, "symbol": "BTCUSDT", "interval": "1h"}
        
        mock_manager_instance = MagicMock()
        mock_manager_instance.get_active_strategy.return_value = mock_strategy_instance
        mock_strategy_manager_class.return_value = mock_manager_instance

        # --- Execute analysis command ---
        from modules.analisis_bot import procesar_comando_analisis
        
        # Mock the bot instance and chat_id passed to the function
        mock_bot = AsyncMock()
        test_chat_id = 12345

        await procesar_comando_analisis(mock_bot, test_chat_id, "resumen tecnico")

        # --- Assertions ---
        # 1. Verify historical klines were fetched
        mock_get_historical_klines.assert_awaited_once_with(symbol='BTCUSDT', interval='1h', limit=100)

        # 2. Verify the analysis was performed
        mock_strategy_instance.analyze.assert_called_once()

        # 3. Verify Telegram message was sent with the correct content
        assert mock_send_message.call_count == 2
        first_call_args = mock_send_message.call_args_list[0].args
        second_call_args = mock_send_message.call_args_list[1].args

        assert first_call_args[1] == test_chat_id
        assert "Iniciando análisis con la estrategia activa..." in first_call_args[2]

        assert second_call_args[1] == test_chat_id
        sent_message = second_call_args[2]
        clean_message = re.sub(r'<[^>]*>', '', sent_message) # Clean HTML tags
        assert "Resultado del Análisis" in clean_message
        assert "Decisión: COMPRAR" in clean_message


# Helper to create a sample DataFrame
def _get_sample_enriched_df(num_rows: int = 500) -> pd.DataFrame:
    timestamps = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=num_rows, freq='h'))
    data = {
        "timestamp": timestamps,
        "open": np.random.rand(num_rows) * 1000 + 10000,
        "high": np.random.rand(num_rows) * 1000 + 11000,
        "low": np.random.rand(num_rows) * 1000 + 9000,
        "close": np.random.rand(num_rows) * 1000 + 10500,
        "volume": np.random.rand(num_rows) * 1000,
    }
    df = pd.DataFrame(data)
    # Add dummy feature columns that MLStrategy expects
    for col in ['rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci', 'adx', 'plus_di', 'minus_di', 'atr', 'bb_upper', 'bb_lower']:
        df[col] = np.random.rand(len(df))
    df.set_index("timestamp", inplace=True)
    return df


@pytest.mark.asyncio
async def test_full_data_pipeline_integration(monkeypatch):
    # This test checks the flow: download -> build_features -> optimize
    
    # --- Mocks ---
    mock_download = AsyncMock(return_value=_get_sample_enriched_df(500))
    monkeypatch.setattr('download_historical_data.download_and_save_klines', mock_download)

    mock_get_klines = MagicMock(return_value=_get_sample_enriched_df(500))
    monkeypatch.setattr('database.database_manager.get_klines', mock_get_klines)

    mock_build_and_save = MagicMock()
    monkeypatch.setattr('build_feature_store.build_and_save_feature_store', mock_build_and_save)

    mock_guardar_umbrales = MagicMock()
    monkeypatch.setattr('optimize_strategy.guardar_umbrales_optimizado', mock_guardar_umbrales)
    
    monkeypatch.setattr('pandas.read_parquet', MagicMock(return_value=_get_sample_enriched_df(500)))

    # --- Execution ---
    from download_historical_data import download_and_save_klines
    from build_feature_store import build_and_save_feature_store
    from optimize_strategy import optimize_risk_thresholds_ga

    await download_and_save_klines(symbol="TESTUSDT", interval="1h")
    build_and_save_feature_store(symbol="TESTUSDT", interval="1h")
    await optimize_risk_thresholds_ga()

    # --- Assertions ---
    mock_download.assert_awaited_once_with(symbol="TESTUSDT", interval="1h")
    mock_build_and_save.assert_called_once_with(symbol="TESTUSDT", interval="1h")
    mock_guardar_umbrales.assert_called_once()
    
    saved_thresholds = mock_guardar_umbrales.call_args[0][0]
    assert "umbral_alto" in saved_thresholds
    assert "umbral_medio" in saved_thresholds
    assert "umbral_bajo" in saved_thresholds
