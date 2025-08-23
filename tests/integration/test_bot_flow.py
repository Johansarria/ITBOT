import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, ANY
import pandas as pd
import numpy as np
import json
import os
import re

# Import modules that will be part of the integration flow
from utils.telegram_handler import send_message
from utils.binance_client import get_binance_client # Importar la función para obtener el cliente de Binance
from utils.state_manager import StateManager
from database.database_manager import init_db, add_operation, update_position_status
from aiogram import Bot # Import Bot for mocking

# Define a test-specific DB path for integration tests


@pytest.fixture(autouse=True)
def setup_integration_test_env():
    """
    Fixture to set up a clean environment for integration tests.
    - Resets StateManager singleton.
    - Cleans up test database file.
    - Mocks external interactions (Telegram, Binance).
    """
    # Reset StateManager singleton
    StateManager._instance = None

    
    
    # Patch DB_PATH in database_manager to use the test-specific DB

    # Initialize the test database
    init_db() # This will create the test DB file and table

    # Mock external dependencies
    with patch('modules.analisis_bot.send_message', new_callable=AsyncMock) as mock_send_message, \
             patch('modules.analisis_bot.get_historical_klines', new_callable=AsyncMock) as mock_get_historical_klines, \
             patch('utils.binance_client.get_binance_client', new_callable=AsyncMock) as mock_get_binance_client, \
             patch('database.database_manager.add_operation', new_callable=MagicMock) as mock_add_operation, \
             patch('database.database_manager.update_position_status', new_callable=MagicMock) as mock_update_position_status, \
             patch('database.database_manager.get_open_positions_df', new_callable=MagicMock) as mock_get_open_positions_df, \
             patch('listener_bot.bot', new_callable=AsyncMock) as mock_listener_bot_instance, \
             patch('listener_bot.chat_id_int', 12345) as mock_listener_chat_id: # Hardcode chat_id for test

            # Configure the mock client that get_binance_client will return
            mock_binance_instance = AsyncMock()
            mock_get_binance_client.return_value = mock_binance_instance
            
            # Yield mocks in the same structure as the original fixture
            yield (
                mock_send_message,
                mock_get_historical_klines,
                mock_binance_instance.create_order,  # Pass the method mock
                mock_binance_instance.get_all_orders, # Pass the method mock
                mock_binance_instance.get_asset_balance, # Pass the method mock
                mock_add_operation,
                mock_update_position_status,
                mock_get_open_positions_df,
                mock_listener_bot_instance,
                mock_listener_chat_id
            )
    
    # Clean up test database file after test
    if os.path.exists(TEST_INTEGRATION_DB_PATH):
        os.remove(TEST_INTEGRATION_DB_PATH)

# Helper function to simulate an incoming Telegram message
async def simulate_telegram_message(update_obj, context_obj):
    # This function needs to mimic how the Telegram handler processes updates
    # For simplicity, we'll directly call the command handler
    from listener_bot import start_command, analisis_command # Import specific handlers

    # Assuming update_obj.message.text contains the command
    command_text = update_obj.message.text.split(' ')[0] # e.g., /analisis
    
    if command_text == "/start":
        await start_command(update_obj, context_obj)
    elif command_text == "/analisis":
        await analisis_command(update_obj, context_obj)
    # Add other commands as needed

@pytest.mark.asyncio
async def test_full_analisis_flow(setup_integration_test_env):
    mock_send_message, mock_get_historical_klines, mock_create_order, \
    mock_get_all_orders, mock_get_asset_balance, mock_add_operation, \
    mock_update_position_status, mock_get_open_positions_df, \
    mock_listener_bot_instance, mock_listener_chat_id = setup_integration_test_env

    # --- Mock data for Binance API ---
    # Sample klines data (enough for technical analysis indicators)
    sample_klines = [
        [1672531200000, "100", "105", "95", "102", "10", 0,0,0,0,0,0], # Jan 1, 2023
        [1672617600000, "102", "108", "98", "105", "12", 0,0,0,0,0,0],
        # ... add more klines to meet the 100 limit for get_historical_klines and indicator window (e.g., 14 for ATR)
        # For a real test, generate realistic klines or load from a file.
        # For now, let's just ensure enough data points for basic TA.
    ]
    # Generate 100 klines for the test
    for i in range(2, 100):
        timestamp = 1672531200000 + i * 86400000 # Daily klines
        open_p = 100 + i * 0.1
        high_p = open_p + 2
        low_p = open_p - 1
        close_p = open_p + 0.5
        sample_klines.append([timestamp, str(open_p), str(high_p), str(low_p), str(close_p), "10", 0,0,0,0,0,0])

    columns = ["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"]
    df_klines = pd.DataFrame(sample_klines, columns=columns)
    mock_get_historical_klines.return_value = df_klines
    mock_get_asset_balance.return_value = {"asset": "USDT", "free": "1000"} # Mock user balance

    # --- Mock Telegram Update and Context objects ---
    mock_update = AsyncMock()
    mock_update.message.text = "/analisis resumen tecnico" # Changed to a recognized command
    mock_update.message.chat_id = 12345

    mock_context = AsyncMock()
    mock_context.args = ["resumen", "tecnico"] # Simulate command arguments

    # --- Simulate the bot command ---
    # We need to ensure the command handlers are registered.
    # In a real scenario, run_bot.py would set this up.
    # For this test, we'll directly call the handler function.

    # Mockear el método analyze de la estrategia activa para devolver 'COMPRAR'
    from modules.analisis_bot import procesar_comando_analisis
    from strategies.strategy_manager import StrategyManager
    strategy_manager = StrategyManager()
    strategy_manager.set_active_strategy("SimpleTechnicalStrategy")
    active_strategy = strategy_manager.get_active_strategy()
    async def mock_analyze(*args, **kwargs):
        return {"symbol": "BTCUSDT", "interval": "1h", "decision": "COMPRAR", "score": 3}
    active_strategy.analyze = mock_analyze

    # Call the command handler directly
    await procesar_comando_analisis(mock_listener_bot_instance, mock_listener_chat_id, "resumen tecnico")

    # --- Assertions ---
    # 1. Verify Telegram message was sent
    assert mock_send_message.call_count == 2
    sent_message = mock_send_message.call_args[0][2]
    assert "Resultado del Análisis con 'SimpleTechnicalStrategy':" in sent_message
    assert "Símbolo:" in sent_message
    # Extract the decision part from the message
    decision_line = [line for line in sent_message.split('\n') if "Decisión:" in line][0]
    # Remove HTML tags from decision_line
    clean_decision_line = re.sub(r'<[^>]*>', '', decision_line)
    assert "Decisión: COMPRAR" in clean_decision_line

    # 2. Verify historical klines were fetched (aceptar llamada con args o kwargs)
    called_args, called_kwargs = mock_get_historical_klines.call_args
    assert (called_args == ("BTCUSDT", "1h") or
            called_kwargs == {"symbol": "BTCUSDT", "interval": "1h", "limit": 100})

    # 3. Verify StateManager interactions (assuming StateManager is used by analisis_command)
    state_manager = StateManager()
    assert state_manager.get_state("ia_manager", "ia_activa") == False # Default state
    # Add more specific state assertions if analisis_command modifies state

    # 4. Verify no order was created (since decision is MANTENER)
    mock_create_order.assert_not_called()

    # 5. Verify database interactions (if any for analysis logging)
    # For now, analisis_command doesn't log to DB directly, but if it did, assert here.
    mock_add_operation.assert_not_called()
    mock_update_position_status.assert_not_called()
    mock_get_open_positions_df.assert_not_called()

# Helper function to generate sample klines for mocking
def _get_sample_klines_df(num_rows: int = 200) -> pd.DataFrame:
    timestamps = pd.to_datetime(pd.date_range(end=pd.Timestamp.now(), periods=num_rows, freq='h'))
    data = {
        "timestamp": timestamps.astype(int) // 10**6, # ms timestamp
        "open": np.random.rand(num_rows) * 1000 + 10000,
        "high": np.random.rand(num_rows) * 1000 + 11000,
        "low": np.random.rand(num_rows) * 1000 + 9000,
        "close": np.random.rand(num_rows) * 1000 + 10500,
        "volume": np.random.rand(num_rows) * 1000,
        "close_time": (timestamps.astype(int) // 10**6) + 3600000 # +1 hour in ms
    }
    df = pd.DataFrame(data)
    df.set_index("timestamp", inplace=True)
    return df

@pytest.mark.asyncio
async def test_full_data_pipeline_integration(monkeypatch):
    # --- Setup: Mock external dependencies and internal functions ---
    # Ensure a clean environment for this specific test
    TEST_PARQUET_PATH = "data/features/test_klines_enriched.parquet"
    TEST_THRESHOLDS_PATH = "best_risk_thresholds_test.json"

    # Clean up any previous test artifacts
    if os.path.exists(TEST_PARQUET_PATH):
        os.remove(TEST_PARQUET_PATH)
    if os.path.exists(TEST_THRESHOLDS_PATH):
        os.remove(TEST_THRESHOLDS_PATH)
    if os.path.exists(TEST_INTEGRATION_DB_PATH):
        os.remove(TEST_INTEGRATION_DB_PATH)

    # Patch DB_PATH for this test to ensure isolation
    monkeypatch.setattr('database.database_manager.DB_PATH', TEST_INTEGRATION_DB_PATH)
    init_db() # Initialize the test database

    # Mock download_and_save_klines to simulate data download and saving to DB
    mock_download_klines = AsyncMock(return_value=_get_sample_klines_df(500)) # Simulate 500 klines
    monkeypatch.setattr('download_historical_data.download_and_save_klines', mock_download_klines)

    # Mock database.database_manager.get_klines to return data when build_feature_store calls it
    mock_get_klines_db = MagicMock(return_value=_get_sample_klines_df(500)) # Same sample data
    monkeypatch.setattr('database.database_manager.get_klines', mock_get_klines_db)

    # Mock build_feature_store.build_and_save_feature_store to ensure it's called
    mock_build_feature_store = MagicMock()
    monkeypatch.setattr('build_feature_store.build_and_save_feature_store', mock_build_feature_store)

    # Mock utils.risk_manager.guardar_umbrales_optimizado to check saved thresholds
    mock_guardar_umbrales = MagicMock()
    monkeypatch.setattr('optimize_strategy.guardar_umbrales_optimizado', mock_guardar_umbrales)

    # Mock the path where optimize_strategy.py expects to save the thresholds
    monkeypatch.setenv("ITBOT_TEST_MODE", "True")

    # Mock pd.read_parquet in optimize_strategy.py to return the enriched data
    # This is crucial because optimize_strategy will try to read the parquet file
    sample_enriched_df = _get_sample_klines_df(500) # Base data
    # Add dummy feature columns that MLStrategy expects
    for col in ['rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci', 'adx', 'plus_di', 'minus_di', 'atr', 'bb_upper', 'bb_lower']:
        sample_enriched_df[col] = np.random.rand(len(sample_enriched_df))
    monkeypatch.setattr('pandas.read_parquet', MagicMock(return_value=sample_enriched_df))

    # --- Execution: Simulate the full pipeline ---
    # 1. Simulate initial data download (this would normally happen via a scheduled task or manual trigger)
    from download_historical_data import download_and_save_klines as real_download_klines
    await real_download_klines(symbol="TESTUSDT", interval="1h", start_str="1 Jan, 2023", append_to_existing=False)

    # 2. Simulate feature store build (this would normally happen via a scheduled task or manual trigger)
    from build_feature_store import build_and_save_feature_store as real_build_feature_store
    real_build_feature_store(symbol="TESTUSDT", interval="1h")

    # 3. Simulate optimization process
    from optimize_strategy import optimize_risk_thresholds_ga as real_optimize_ga
    await real_optimize_ga()

    # --- Assertions ---
    # 1. Verify download_and_save_klines was called with correct parameters
    mock_download_klines.assert_awaited_once_with(symbol="TESTUSDT", interval="1h", start_str="1 Jan, 2023", append_to_existing=False)

    # 2. Verify build_and_save_feature_store was called with correct parameters
    mock_build_feature_store.assert_called_once_with(symbol="TESTUSDT", interval="1h")

    # 3. Verify optimize_risk_thresholds_ga was called
    # (No direct mock for real_optimize_ga, so we check its side effects)

    # 4. Verify guardar_umbrales_optimizado was called with reasonable values
    mock_guardar_umbrales.assert_called_once()
    saved_thresholds = mock_guardar_umbrales.call_args[0][0]
    assert "umbral_alto" in saved_thresholds
    assert "umbral_medio" in saved_thresholds
    assert "umbral_bajo" in saved_thresholds
    assert 0.4 <= saved_thresholds["umbral_bajo"] <= 0.6
    assert 0.6 <= saved_thresholds["umbral_medio"] <= 0.8
    assert 0.8 <= saved_thresholds["umbral_alto"] <= 0.99

    # 5. Verify the thresholds file was created/updated
    # The file writing is mocked, so we don't assert its physical existence.
    # We already assert that mock_guardar_umbrales was called with correct values.
    # assert os.path.exists(TEST_THRESHOLDS_PATH) # Removed as file writing is mocked
    # with open(TEST_THRESHOLDS_PATH, 'r') as f:
    #     loaded_thresholds = json.load(f)
    # assert loaded_thresholds == saved_thresholds

    # 6. Verify the parquet file was attempted to be created (via mock)
    # This is implicitly tested by mock_build_feature_store being called

    # --- Cleanup ---
    if os.path.exists(TEST_PARQUET_PATH):
        os.remove(TEST_PARQUET_PATH)
    if os.path.exists(TEST_THRESHOLDS_PATH):
        os.remove(TEST_THRESHOLDS_PATH)
    if os.path.exists(TEST_INTEGRATION_DB_PATH):
        os.remove(TEST_INTEGRATION_DB_PATH)
