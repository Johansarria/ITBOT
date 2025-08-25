import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from aiogram.exceptions import TelegramUnauthorizedError, TelegramNetworkError

# Import the function to be tested
from test_telegram import test_token

pytestmark = pytest.mark.asyncio

@patch('test_telegram.os.getenv')
@patch('test_telegram.print')
async def test_no_token_scenario(mock_print, mock_getenv):
    """
    Tests that the script handles the case where TELEGRAM_TOKEN is not found.
    """
    # Arrange
    mock_getenv.return_value = None

    # Act
    await test_token()

    # Assert
    mock_getenv.assert_called_with("TELEGRAM_TOKEN")
    mock_print.assert_called_with("❌ Error: TELEGRAM_TOKEN not found in .env file.")

@patch('test_telegram.Bot')
@patch('test_telegram.os.getenv')
@patch('test_telegram.print')
async def test_success_scenario(mock_print, mock_getenv, mock_bot):
    """
    Tests the success path where the token is valid and bot info is fetched.
    """
    # Arrange
    mock_getenv.return_value = "fake_token"

    # Mock the bot instance and its methods
    mock_bot_instance = AsyncMock()
    mock_bot_instance.get_me.return_value = MagicMock(
        id=12345,
        full_name="Test Bot",
        username="test_bot"
    )
    mock_bot.return_value = mock_bot_instance

    # Act
    await test_token()

    # Assert
    mock_getenv.assert_called_with("TELEGRAM_TOKEN")
    mock_bot.assert_called_with(token="fake_token")
    mock_bot_instance.get_me.assert_awaited_once()
    mock_print.assert_any_call("✅ --- SUCCESS --- ✅")
    mock_print.assert_any_call("Bot Name: Test Bot")
    mock_bot_instance.session.close.assert_awaited_once()

@patch('test_telegram.Bot')
@patch('test_telegram.os.getenv')
@patch('test_telegram.print')
async def test_unauthorized_scenario(mock_print, mock_getenv, mock_bot):
    """
    Tests the scenario where the token is invalid/unauthorized.
    """
    # Arrange
    mock_getenv.return_value = "invalid_token"

    mock_bot_instance = AsyncMock()
    # The exception requires method and message arguments
    mock_method = MagicMock()
    mock_bot_instance.get_me.side_effect = TelegramUnauthorizedError(method=mock_method, message="Unauthorized")
    mock_bot.return_value = mock_bot_instance

    # Act
    await test_token()

    # Assert
    mock_bot_instance.get_me.assert_awaited_once()
    mock_print.assert_any_call("❌ --- FAILURE --- ❌")
    mock_print.assert_any_call("Error: Unauthorized. Your TELEGRAM_TOKEN is incorrect or revoked.")

@patch('test_telegram.Bot')
@patch('test_telegram.os.getenv')
@patch('test_telegram.print')
async def test_network_error_scenario(mock_print, mock_getenv, mock_bot):
    """
    Tests the scenario where a network error occurs.
    """
    # Arrange
    mock_getenv.return_value = "fake_token"

    mock_bot_instance = AsyncMock()
    # The exception requires method and message arguments
    mock_method = MagicMock()
    mock_bot_instance.get_me.side_effect = TelegramNetworkError(method=mock_method, message="Connection timed out")
    mock_bot.return_value = mock_bot_instance

    # Act
    await test_token()

    # Assert
    mock_bot_instance.get_me.assert_awaited_once()
    mock_print.assert_any_call("❌ --- FAILURE --- ❌")
    mock_print.assert_any_call("Error: Network issue. Could not connect to Telegram.")

    # Check the "Details" line more robustly
    details_printed = any(
        "Details: " in str(call) and "Connection timed out" in str(call)
        for call in mock_print.call_args_list
    )
    assert details_printed, "The details of the network error were not printed correctly."

@patch('test_telegram.Bot')
@patch('test_telegram.os.getenv')
@patch('test_telegram.print')
async def test_generic_exception_scenario(mock_print, mock_getenv, mock_bot):
    """
    Tests the scenario where a generic exception occurs.
    """
    # Arrange
    mock_getenv.return_value = "fake_token"

    mock_bot_instance = AsyncMock()
    mock_bot_instance.get_me.side_effect = Exception("A wild error appears!")
    mock_bot.return_value = mock_bot_instance

    # Act
    await test_token()

    # Assert
    mock_bot_instance.get_me.assert_awaited_once()
    mock_print.assert_any_call("❌ --- FAILURE --- ❌")
    mock_print.assert_any_call("An unexpected error occurred: A wild error appears!")
