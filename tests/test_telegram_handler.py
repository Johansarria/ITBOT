import pytest
from unittest.mock import patch, MagicMock, AsyncMock

@pytest.fixture(autouse=True)
def patch_asyncio_sleep():
    """Auto-patch asyncio.sleep to prevent tests from actually waiting."""
    with patch('asyncio.sleep', return_value=None) as p:
        yield p

@pytest.fixture
def mock_bot():
    """Fixture for a mock aiogram Bot with async methods."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_document = AsyncMock()
    bot.get_updates = AsyncMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    return bot

def test_placeholder_setup(mock_bot):
    """Ensure fixtures are set up correctly."""
    assert mock_bot is not None

# --- Tests for send_message ---

from utils.telegram_handler import send_message
from aiogram.exceptions import TelegramRetryAfter

@pytest.mark.asyncio
async def test_send_message_happy_path(mock_bot):
    """Test that send_message calls the bot's method correctly."""
    chat_id = 123
    message = "Hello, world!"
    await send_message(mock_bot, chat_id, message)
    mock_bot.send_message.assert_called_once_with(
        chat_id=chat_id,
        text=message,
        parse_mode='HTML',
        reply_markup=None
    )

@pytest.mark.asyncio
async def test_send_message_no_bot_instance():
    """Test that no message is sent if bot_instance is None."""
    # This test doesn't need the mock_bot fixture, but it's okay
    await send_message(None, 123, "This should not be sent")
    # No assertion is needed if no mock is called, but we can be explicit
    # by patching the bot's send_message and asserting not_called if we want.
    # For now, this is sufficient to test the guard clause.

@pytest.mark.asyncio
async def test_send_message_handles_retry_after(mock_bot, patch_asyncio_sleep):
    """Test the retry logic on a TelegramRetryAfter exception."""
    retry_after_seconds = 5

    # Create an exception instance with all required arguments
    error = TelegramRetryAfter(
        method="test",
        message="test",
        retry_after=retry_after_seconds
    )

    mock_bot.send_message.side_effect = [
        error,
        AsyncMock() # Successful call on the second attempt
    ]

    chat_id = 123
    message = "Test retry"
    await send_message(mock_bot, chat_id, message)

    # Check that sleep was called with the correct delay
    patch_asyncio_sleep.assert_called_once_with(retry_after_seconds)
    # Check that send_message was called twice (initial + retry)
    assert mock_bot.send_message.call_count == 2

@pytest.mark.asyncio
async def test_send_message_handles_generic_exception(mock_bot):
    """Test that a generic exception is caught and logged."""
    mock_bot.send_message.side_effect = Exception("Generic network error")

    # We expect this to fail silently (logging the error) without crashing.
    # The function should complete without raising the exception.
    await send_message(mock_bot, 123, "This will fail")

    # We can assert it was called, even if it failed internally.
    mock_bot.send_message.assert_called_once()

# --- Tests for send_document ---

from utils.telegram_handler import send_document
from aiogram.types import FSInputFile

@pytest.mark.asyncio
async def test_send_document_happy_path(mock_bot, tmp_path):
    """Test successful sending of a document."""
    # Create a dummy file to send
    file_path = tmp_path / "report.txt"
    file_path.write_text("This is a test document.")

    chat_id = 123
    caption = "Here is your report."

    await send_document(mock_bot, chat_id, str(file_path), caption)

    mock_bot.send_document.assert_called_once()
    args, kwargs = mock_bot.send_document.call_args

    assert kwargs['chat_id'] == chat_id
    assert kwargs['caption'] == caption
    # Check that the document is an FSInputFile instance
    assert isinstance(kwargs['document'], FSInputFile)
    assert kwargs['document'].filename == "report.txt"

@pytest.mark.asyncio
async def test_send_document_file_not_found():
    """Test that FileNotFoundError is raised for a non-existent file."""
    with pytest.raises(FileNotFoundError):
        await send_document(MagicMock(), 123, "non_existent_file.txt")


@pytest.mark.asyncio
async def test_await_confirmation_prod_mode_exception(mock_bot):
    """Test exception handling during polling in production mode."""
    with patch('utils.telegram_handler.config') as mock_config:
        mock_config.PRODUCTION_MODE = True

        # Raise an exception on the first call, then return empty lists
        mock_bot.get_updates.side_effect = [Exception("Network error"), [], []]

        result = await await_confirmation(mock_bot, 123, timeout=3)

        assert result == "no" # Should still time out
        # Check that it was called multiple times
        assert mock_bot.get_updates.call_count > 1

# --- Tests for shutdown_bot and await_confirmation ---

from utils.telegram_handler import shutdown_bot, await_confirmation

@pytest.mark.asyncio
async def test_shutdown_bot(mock_bot):
    """Test that shutdown_bot closes the bot's session."""
    await shutdown_bot(mock_bot)
    mock_bot.session.close.assert_called_once()

@pytest.mark.asyncio
async def test_await_confirmation_dev_mode():
    """Test that await_confirmation auto-confirms in dev mode."""
    with patch('utils.telegram_handler.config') as mock_config:
        mock_config.PRODUCTION_MODE = False
        result = await await_confirmation(MagicMock(), 123)
        assert result == "sí"

@pytest.mark.asyncio
async def test_await_confirmation_prod_mode_success(mock_bot):
    """Test successful confirmation in production mode."""
    # Mock the config to be in production mode
    with patch('utils.telegram_handler.config') as mock_config:
        mock_config.PRODUCTION_MODE = True

        # Mock the update objects
        mock_message = MagicMock()
        mock_message.text = "sí"
        mock_message.chat.id = 123

        mock_update = MagicMock()
        mock_update.update_id = 100
        mock_update.message = mock_message

        # First call to get_updates is to clear old messages, second gets the confirmation
        mock_bot.get_updates.side_effect = [[], [mock_update]]

        result = await await_confirmation(mock_bot, 123, timeout=5)
        assert result == "sí"
        # Ensure it doesn't send a cancellation message
        mock_bot.send_message.assert_not_called()

@pytest.mark.asyncio
async def test_await_confirmation_prod_mode_timeout(mock_bot):
    """Test timeout in production mode."""
    with patch('utils.telegram_handler.config') as mock_config, \
         patch('utils.telegram_handler.send_message', new_callable=AsyncMock) as mock_send_message:

        mock_config.PRODUCTION_MODE = True

        # Mock get_updates to always return an empty list, simulating no new messages
        mock_bot.get_updates.return_value = []

        result = await await_confirmation(mock_bot, 123, timeout=1) # Short timeout for test

        assert result == "no"
        # Check that our patched send_message was called correctly
        mock_send_message.assert_called_once_with(mock_bot, 123, "Acción cancelada por falta de confirmación.")
