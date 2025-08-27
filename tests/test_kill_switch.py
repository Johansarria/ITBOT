import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ConversationHandler, ContextTypes

from handlers import (
    kill_switch_start,
    confirm_kill_switch,
    resume_system_start,
    confirm_resume_system,
    CONFIRM_KILL_SWITCH,
    CONFIRM_RESUME,
    is_admin,
    escape_markdown
)
from config import settings

# Mock the entire logic layer that handlers.py imports
@pytest.fixture(autouse=True)
def mock_logic_layer():
    with patch('handlers.logic_stubs', new_callable=AsyncMock) as mock_logic:
        # Pre-configure the return values of async functions
        mock_logic.execute_kill_switch.return_value = {
            "closed_positions": [],
            "failed_positions": []
        }
        yield mock_logic

@pytest.fixture
def mock_context():
    """Provides a mock bot and context."""
    bot = AsyncMock()
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = bot
    return context

@pytest.fixture
def admin_user():
    """Provides a mock admin user."""
    return MagicMock(spec=User, id=settings.ADMIN_TELEGRAM_ID, first_name='Admin')

@pytest.fixture
def non_admin_user():
    """Provides a mock non-admin user."""
    return MagicMock(spec=User, id=999999, first_name='Peasant')

@pytest.fixture
def mock_chat():
    """Provides a mock chat."""
    return MagicMock(spec=Chat, id=12345, type='private')

@pytest.mark.asyncio
async def test_kill_switch_start_authorized(mock_context, admin_user, mock_chat):
    """Test kill_switch_start by an authorized admin."""
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.from_user = admin_user
    callback_query.message = MagicMock(spec=Message)
    callback_query.answer = AsyncMock()
    callback_query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = callback_query

    result = await kill_switch_start(update, mock_context)

    callback_query.answer.assert_called_once_with("❗ ACCIÓN DE EMERGENCIA ❗", show_alert=True)
    callback_query.edit_message_text.assert_called_once()
    assert "CONFIRMACIÓN DE KILL SWITCH" in callback_query.edit_message_text.call_args.kwargs['text']
    assert result == CONFIRM_KILL_SWITCH

@pytest.mark.asyncio
async def test_kill_switch_start_unauthorized(mock_context, non_admin_user, mock_chat):
    """Test kill_switch_start by a non-admin user."""
    callback_query = MagicMock(spec=CallbackQuery)
    callback_query.from_user = non_admin_user
    callback_query.answer = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = callback_query

    result = await kill_switch_start(update, mock_context)

    callback_query.answer.assert_called_once_with("🚫 ACCESO DENEGADO 🚫", show_alert=True)
    assert result == ConversationHandler.END

@pytest.mark.asyncio
async def test_confirm_kill_switch_success(mock_logic_layer, mock_context, admin_user, mock_chat):
    """Test successful confirmation of the kill switch."""
    message = MagicMock(spec=Message)
    message.from_user = admin_user
    message.chat = mock_chat
    message.text = "CONFIRMAR KILL SWITCH"
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.message = message

    result = await confirm_kill_switch(update, mock_context)

    mock_logic_layer.execute_kill_switch.assert_awaited_once()
    mock_logic_layer.full_system_stop.assert_awaited_once()

    # Check the final report message
    final_report_text = message.reply_text.call_args_list[1].kwargs['text']
    assert "Liquidación completada" in final_report_text
    assert "Sistema en Pausa" in final_report_text
    assert result == ConversationHandler.END

@pytest.mark.asyncio
async def test_confirm_kill_switch_partial_failure(mock_logic_layer, mock_context, admin_user, mock_chat):
    """Test kill switch confirmation when some positions fail to close."""
    mock_logic_layer.execute_kill_switch.return_value = {
        "closed_positions": [{'symbol': 'BTCUSDT'}],
        "failed_positions": [{'symbol': 'ETHUSDT'}]
    }

    message = MagicMock(spec=Message)
    message.text = "CONFIRMAR KILL SWITCH"
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.message = message

    await confirm_kill_switch(update, mock_context)

    final_report_text = message.reply_text.call_args_list[1].kwargs['text']
    assert "ATENCIÓN" in final_report_text
    assert "ETHUSDT" in final_report_text

@pytest.mark.asyncio
async def test_confirm_kill_switch_wrong_text(mock_logic_layer, mock_context, admin_user, mock_chat):
    """Test that wrong confirmation text cancels the action."""
    message = MagicMock(spec=Message)
    message.text = "oops wrong text"
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.message = message

    result = await confirm_kill_switch(update, mock_context)

    mock_logic_layer.execute_kill_switch.assert_not_awaited()
    message.reply_text.assert_called_once()
    # Check the positional argument instead of keyword argument
    assert "Texto incorrecto" in message.reply_text.call_args.args[0]
    assert result == CONFIRM_KILL_SWITCH
