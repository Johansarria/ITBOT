import pytest
from unittest.mock import AsyncMock, patch, ANY

from telegram import Update
from telegram.ext import ConversationHandler

# Import the handlers and state constants to be tested
from handlers import (
    kill_switch_command_handler,
    confirm_kill_switch,
    CONFIRM_KILL_SWITCH,
    cancel_conversation
)

@pytest.mark.asyncio
async def test_kill_switch_flow_admin_confirms():
    """
    Tests the full successful flow of the /kill_switch command:
    1. Admin sends /kill_switch.
    2. Bot asks for confirmation.
    3. Admin sends confirmation text.
    4. Bot executes the action and ends the conversation.
    """
    # 1. Setup Mocks for the initial command
    update = AsyncMock()
    update.message = AsyncMock()
    update.message.from_user = AsyncMock()
    update.message.reply_text = AsyncMock()
    context = AsyncMock()

    # Simulate an admin sending /kill_switch
    update.message.from_user.id = 12345  # Dummy Admin ID
    update.message.text = "/kill_switch"

    # 2. Initiate the conversation by calling the entry point handler
    with patch('handlers.is_admin', return_value=True):
        entry_state = await kill_switch_command_handler(update, context)

    # 3. Assert that the bot asks for confirmation and enters the correct state
    update.message.reply_text.assert_called_once()
    first_call_text = update.message.reply_text.call_args.kwargs['text']
    assert "CONFIRMACIÓN DE KILL SWITCH" in first_call_text
    assert entry_state == CONFIRM_KILL_SWITCH

    # Reset mock for the next interaction
    update.message.reply_text.reset_mock()

    # 4. Simulate the admin sending the confirmation text
    update.message.text = "CONFIRMAR KILL SWITCH"

    # Patch the core logic function to ensure it gets called, and mock its return value
    with patch('handlers.logic_stubs.atomic_kill_switch', new_callable=AsyncMock) as mock_atomic_kill:
        mock_atomic_kill.return_value = {"success": True, "closed_positions": [], "failed_positions": []}

        # 5. Call the state handler for the confirmation
        end_state = await confirm_kill_switch(update, context)

        # 6. Assert that the final action was called and the conversation ended
        mock_atomic_kill.assert_called_once()
        assert end_state == ConversationHandler.END

        # Check that the final success message was sent
        final_call_text = update.message.reply_text.call_args.kwargs['text']
        assert "Liquidación completada" in final_call_text

@pytest.mark.asyncio
async def test_kill_switch_flow_non_admin():
    """
    Tests that a non-admin user is denied access to the /kill_switch command.
    """
    # 1. Setup Mocks
    update = AsyncMock()
    update.message = AsyncMock()
    update.message.from_user = AsyncMock()
    update.message.reply_text = AsyncMock()
    context = AsyncMock()
    update.message.from_user.id = 54321  # Non-admin ID
    update.message.text = "/kill_switch"

    # 2. Initiate and assert
    with patch('handlers.is_admin', return_value=False):
        state = await kill_switch_command_handler(update, context)

        assert state == ConversationHandler.END
        update.message.reply_text.assert_called_once_with("🚫 ACCESO DENEGADO. Este comando solo puede ser ejecutado por un administrador.")

@pytest.mark.asyncio
async def test_kill_switch_flow_cancel():
    """
    Tests that the kill switch conversation can be cancelled.
    """
    # 1. Setup Mocks
    update = AsyncMock()
    update.callback_query = AsyncMock()
    update.callback_query.from_user = AsyncMock()
    update.callback_query.answer = AsyncMock()
    context = AsyncMock()

    # We need to mock the callback_query path for the cancel handler
    update.callback_query.from_user.id = 12345

    # Mock the start function that gets called on cancellation
    with patch('handlers.start', new_callable=AsyncMock) as mock_start:
        # 2. Call the cancel handler
        state = await cancel_conversation(update, context)

        # 3. Assertions
        assert state == ConversationHandler.END
        update.callback_query.answer.assert_called_once()
        mock_start.assert_called_once()
