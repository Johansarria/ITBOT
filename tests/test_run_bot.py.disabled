import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from aiogram import Bot

# Autouse fixture to patch asyncio.sleep for all tests in this file
@pytest.fixture(autouse=True)
def patch_asyncio_sleep():
    with patch('asyncio.sleep', return_value=None) as p:
        yield p

@pytest.fixture
def mock_bot():
    """Fixture for a mock aiogram Bot."""
    return MagicMock(spec=Bot)

# --- Tests for flujo_principal_por_activo ---

def setup_mock_sm(mock_sm_class, return_value):
    """Helper to set up the StrategyManager mock."""
    mock_manager_instance = MagicMock()
    mock_manager_instance.analyze_all_strategies = AsyncMock(return_value=return_value)
    mock_sm_class.return_value = mock_manager_instance

@pytest.mark.asyncio
async def test_flujo_principal_analysis_error(mock_bot):
    """Test the flow when the strategy analysis returns an error."""
    from run_bot import flujo_principal_por_activo

    with patch('run_bot.StrategyManager') as mock_sm_class, \
         patch('run_bot.send_message', new_callable=AsyncMock) as mock_send:

        setup_mock_sm(mock_sm_class, {"error": "Test analysis error"})

        await flujo_principal_por_activo(mock_bot, 123, "BTCUSDT")

        mock_send.assert_called_once_with(mock_bot, 123, "❌ Error en análisis para BTCUSDT: Test analysis error")

@pytest.mark.asyncio
async def test_flujo_principal_mantener_decision(mock_bot):
    """Test the flow for a 'MANTENER' decision."""
    from run_bot import flujo_principal_por_activo

    with patch('run_bot.StrategyManager') as mock_sm_class, \
         patch('run_bot.mq.publish_decision') as mock_publish:

        setup_mock_sm(mock_sm_class, {"best_decision": "MANTENER"})

        await flujo_principal_por_activo(mock_bot, 123, "BTCUSDT")

        mock_publish.assert_not_called()

@pytest.mark.asyncio
async def test_flujo_principal_publish_failure(mock_bot):
    """Test the flow when publishing to the message queue fails."""
    from run_bot import flujo_principal_por_activo

    with patch('run_bot.StrategyManager') as mock_sm_class, \
         patch('run_bot.mq.publish_decision', return_value=False) as mock_publish, \
         patch('run_bot.send_message', new_callable=AsyncMock) as mock_send:

        analysis_result = {
            "best_decision": "COMPRAR", "best_strategy": "TestStrat",
            "best_score": 1, "symbol": "BTCUSDT"
        }
        setup_mock_sm(mock_sm_class, analysis_result)

        await flujo_principal_por_activo(mock_bot, 123, "BTCUSDT")

        mock_publish.assert_called_once()
        mock_send.assert_called_once_with(mock_bot, 123, "❌ Error al publicar decisión de COMPRAR para BTCUSDT en la cola.")


# --- Tests for Scheduled Tasks ---

@pytest.mark.asyncio
async def test_daily_data_update_task_success(mock_bot):
    """Test the daily data update task successful path."""
    from run_bot import daily_data_update_task

    with patch('run_bot.settings') as mock_settings, \
         patch('run_bot.send_message', new_callable=AsyncMock) as mock_send, \
         patch('run_bot.download_and_save_klines', new_callable=AsyncMock) as mock_download:

        mock_settings.TRADING_PAIRS = ["BTCUSDT"]

        await daily_data_update_task(mock_bot, 123)

        mock_download.assert_called_once()
        assert mock_send.call_count == 2 # Start and end messages
        mock_send.assert_any_call(mock_bot, 123, "✅ Actualización diaria de datos para BTCUSDT completada.")

@pytest.mark.asyncio
async def test_daily_data_update_task_exception(mock_bot):
    """Test the daily data update task with an exception."""
    from run_bot import daily_data_update_task
    error = Exception("Download failed")

    with patch('run_bot.settings') as mock_settings, \
         patch('run_bot.send_message', new_callable=AsyncMock) as mock_send, \
         patch('run_bot.download_and_save_klines', side_effect=error):

        mock_settings.TRADING_PAIRS = ["BTCUSDT"]

        await daily_data_update_task(mock_bot, 123)

        mock_send.assert_any_call(mock_bot, 123, f"❌ Error en actualización diaria para BTCUSDT: {error}")

@pytest.mark.asyncio
async def test_retrain_ml_model_periodically_success(mock_bot):
    """Test the ML retraining task successful path."""
    from run_bot import retrain_ml_model_periodically

    # Mock the subprocess to simulate a successful run
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b'Success', b'')
    mock_proc.returncode = 0

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc) as mock_create_proc, \
         patch('run_bot.send_message', new_callable=AsyncMock) as mock_send, \
         patch('asyncio.sleep', side_effect=asyncio.CancelledError): # Break the loop

        with pytest.raises(asyncio.CancelledError):
            await retrain_ml_model_periodically(mock_bot, 123)

        mock_create_proc.assert_called_once()
        mock_send.assert_any_call(mock_bot, 123, "✅ Retraining ML completado exitosamente.")


# --- Tests for main_run_bot loop ---

@pytest.mark.asyncio
async def test_main_run_bot_loop_shield_active():
    """Test the main loop skips analysis when the shield is active."""
    from run_bot import main_run_bot

    with patch('run_bot.init_db'), \
         patch('run_bot.Bot') as mock_bot_class, \
         patch('run_bot.StateManager'), \
         patch('run_bot.AsyncIOScheduler'), \
         patch('run_bot.dp.start_polling', new_callable=AsyncMock), \
         patch('run_bot.settings') as mock_settings, \
         patch('run_bot.send_message') as mock_send, \
         patch('run_bot.verificar_condiciones_mercado', new_callable=AsyncMock, return_value={"status": "DANGER", "reason": "High volatility"}), \
         patch('run_bot.flujo_principal_por_activo') as mock_flujo, \
         patch('run_bot.shutdown_bot', new_callable=AsyncMock) as mock_shutdown, \
         patch('asyncio.sleep', side_effect=asyncio.CancelledError):

        # Configure the mock Bot instance
        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance

        mock_settings.TRADING_PAIRS = ["BTCUSDT", "ETHUSDT"]

        # The function catches the CancelledError, so we don't use pytest.raises
        await main_run_bot()

        mock_send.assert_any_call(mock_bot_instance, ANY, "🛡️ Escudo de Protección Activado 🛡️\nRazón: High volatility\nNo se analizarán activos en este ciclo.")
        mock_flujo.assert_not_called()
        mock_shutdown.assert_called_once_with(mock_bot_instance)

@pytest.mark.asyncio
async def test_main_run_bot_loop_shield_inactive():
    """Test the main loop runs analysis when the shield is inactive."""
    from run_bot import main_run_bot

    with patch('run_bot.init_db'), \
         patch('run_bot.Bot') as mock_bot_class, \
         patch('run_bot.StateManager'), \
         patch('run_bot.AsyncIOScheduler'), \
         patch('run_bot.dp.start_polling', new_callable=AsyncMock), \
         patch('run_bot.settings') as mock_settings, \
         patch('run_bot.send_message'), \
         patch('run_bot.verificar_condiciones_mercado', new_callable=AsyncMock, return_value={"status": "SAFE"}), \
         patch('run_bot.flujo_principal_por_activo', new_callable=AsyncMock) as mock_flujo, \
         patch('run_bot.shutdown_bot', new_callable=AsyncMock), \
         patch('asyncio.sleep', side_effect=asyncio.CancelledError):

        mock_settings.TRADING_PAIRS = ["BTCUSDT", "ETHUSDT"]

        # The function catches the CancelledError, so we don't use pytest.raises
        await main_run_bot()

        assert mock_flujo.call_count == len(mock_settings.TRADING_PAIRS)

# --- Additional Coverage Tests ---

@pytest.mark.asyncio
async def test_retrain_ml_model_exception(mock_bot):
    """Test the exception handling in the retraining task."""
    from run_bot import retrain_ml_model_periodically
    error = Exception("Subprocess creation failed")

    with patch('asyncio.create_subprocess_exec', side_effect=error), \
         patch('run_bot.send_message', new_callable=AsyncMock) as mock_send, \
         patch('asyncio.sleep', side_effect=asyncio.CancelledError):

        with pytest.raises(asyncio.CancelledError):
            await retrain_ml_model_periodically(mock_bot, 123)

        mock_send.assert_any_call(mock_bot, 123, f"❌ Excepción en retraining automático: {error}")

@pytest.mark.asyncio
async def test_main_run_bot_loop_gather_exception(mock_bot):
    """Test the main loop handles exceptions from asyncio.gather."""
    from run_bot import main_run_bot

    with patch('run_bot.init_db'), \
         patch('run_bot.Bot'), \
         patch('run_bot.StateManager'), \
         patch('run_bot.AsyncIOScheduler'), \
         patch('run_bot.dp.start_polling', new_callable=AsyncMock), \
         patch('run_bot.settings') as mock_settings, \
         patch('run_bot.send_message'), \
         patch('run_bot.verificar_condiciones_mercado', new_callable=AsyncMock, return_value={"status": "SAFE"}), \
         patch('run_bot.flujo_principal_por_activo', new_callable=AsyncMock, side_effect=ValueError("Test exc")), \
         patch('run_bot.shutdown_bot', new_callable=AsyncMock), \
         patch('asyncio.sleep', side_effect=asyncio.CancelledError):

        mock_settings.TRADING_PAIRS = ["BTCUSDT"]

        await main_run_bot()
        # No crash should occur, and the error is logged internally.
        # We can't easily assert the log, but we know the code path was taken if the test completes.
        pass

@pytest.mark.asyncio
async def test_main_run_bot_no_token():
    """Test that main_run_bot raises ValueError if no token is set."""
    from run_bot import main_run_bot
    with patch('run_bot.settings') as mock_settings:
        mock_settings.TELEGRAM_BOT_TOKEN = None
        with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN no está definido"):
            await main_run_bot()

@pytest.mark.asyncio
async def test_retrain_ml_model_periodically_failure(mock_bot):
    """Test the ML retraining task failure path."""
    from run_bot import retrain_ml_model_periodically
    mock_proc = AsyncMock()
    mock_proc.communicate.return_value = (b'', b'Error output')
    mock_proc.returncode = 1 # Non-zero return code

    with patch('asyncio.create_subprocess_exec', return_value=mock_proc), \
         patch('run_bot.send_message', new_callable=AsyncMock) as mock_send, \
         patch('asyncio.sleep', side_effect=asyncio.CancelledError):

        with pytest.raises(asyncio.CancelledError):
            await retrain_ml_model_periodically(mock_bot, 123)

        mock_send.assert_any_call(mock_bot, 123, "❌ Error en retraining ML:\nError output")

@pytest.mark.asyncio
async def test_main_run_bot_live_mode_message():
    """Test the main loop sends the correct message in LIVE mode."""
    from run_bot import main_run_bot

    with patch('run_bot.init_db'), \
         patch('run_bot.Bot') as mock_bot_class, \
         patch('run_bot.StateManager') as mock_sm, \
         patch('run_bot.AsyncIOScheduler'), \
         patch('run_bot.dp.start_polling', new_callable=AsyncMock), \
         patch('run_bot.settings') as mock_settings, \
         patch('run_bot.send_message') as mock_send, \
         patch('run_bot.verificar_condiciones_mercado', new_callable=AsyncMock, return_value={"status": "SAFE"}), \
         patch('run_bot.flujo_principal_por_activo'), \
         patch('run_bot.shutdown_bot'), \
         patch('asyncio.sleep', side_effect=asyncio.CancelledError):

        # Set session_mode to 'live'
        mock_sm.return_value.get_state.return_value = "live"
        mock_bot_instance = MagicMock()
        mock_bot_class.return_value = mock_bot_instance

        await main_run_bot()

        mock_send.assert_any_call(mock_bot_instance, ANY, "✅ ¡El bot está operando en modo LIVE para múltiples activos!")
