# Enabled copy of tests/test_listener_bot.py.disabled

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, mock_open, MagicMock, call
from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from datetime import datetime
from zoneinfo import ZoneInfo
import listener_bot

# Mockear las dependencias externas
@pytest.fixture
def mock_bot_dependencies():
    """Fixture para mockear dependencias comunes del bot de Telegram."""
    with (
        patch('listener_bot.bot', new_callable=AsyncMock) as mock_bot,
        patch('listener_bot.send_message', new_callable=AsyncMock) as mock_send_message,
        patch('listener_bot.edit_message_safely', new_callable=AsyncMock) as mock_edit_message,
        patch('listener_bot.state_manager', new_callable=MagicMock) as mock_state_manager,
        patch('listener_bot.strategy_manager', new_callable=MagicMock) as mock_strategy_manager,
        patch('listener_bot.mq', new_callable=MagicMock) as mock_mq
    ):
        yield {
            "bot": mock_bot,
            "send_message": mock_send_message,
            "edit_message": mock_edit_message,
            "state_manager": mock_state_manager,
            "strategy_manager": mock_strategy_manager,
            "mq": mock_mq,
        }

@pytest.fixture
def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=123, user_id=123)
    return FSMContext(storage=storage, key=key)

@pytest.mark.asyncio
async def test_start_command_initial_state(mock_bot_dependencies, fsm_context):
    mock_bot_dependencies["state_manager"].get_state.return_value = None
    message = AsyncMock(spec=Message, chat=MagicMock(id=123), from_user=MagicMock(id=123))

    await listener_bot.start_command(message, fsm_context)

    mock_bot_dependencies["send_message"].assert_called_once()
    assert "reply_markup" in mock_bot_dependencies["send_message"].call_args.kwargs
    assert await fsm_context.get_state() == listener_bot.InitialStates.waiting_for_mode_selection

@pytest.mark.asyncio
async def test_start_command_mode_set(mock_bot_dependencies, fsm_context):
    mock_bot_dependencies["state_manager"].get_state.return_value = "test"
    message = AsyncMock(spec=Message, chat=MagicMock(id=123), from_user=MagicMock(id=123))

    with (
        patch('listener_bot.get_current_status_text', return_value="Status") as mock_status,
        patch('listener_bot.get_main_menu', return_value=("Menu", MagicMock())) as mock_menu
    ):
        await listener_bot.start_command(message, fsm_context)
        mock_status.assert_called_once()
        mock_menu.assert_called_once()
        calls = [
            call(mock_bot_dependencies["bot"], 123, "Status"),
            call(mock_bot_dependencies["bot"], 123, "Menu", reply_markup=mock_menu.return_value[1])
        ]
        mock_bot_dependencies["send_message"].assert_has_calls(calls)

@pytest.mark.asyncio
async def test_help_command(mock_bot_dependencies):
    message = AsyncMock(spec=Message, chat=MagicMock(id=123), from_user=MagicMock(id=123))
    await listener_bot.help_command(message)
    mock_bot_dependencies["send_message"].assert_called_once()
    sent_text = mock_bot_dependencies["send_message"].call_args[0][2]
    assert "Ayuda del Bot de Trading" in sent_text

@pytest.mark.asyncio
async def test_process_mode_selection(mock_bot_dependencies, fsm_context):
    cq = AsyncMock(spec=CallbackQuery, data="select_mode:live")
    cq.message = AsyncMock(spec=Message, chat=MagicMock(id=123))
    cq.answer = AsyncMock()

    with (
        patch('listener_bot.get_current_status_text', return_value="Status") as mock_status,
        patch('listener_bot.get_main_menu', return_value=("Menu", MagicMock())) as mock_menu
    ):
        await listener_bot.process_mode_selection(cq, fsm_context)
        cq.answer.assert_called_once()
        mock_bot_dependencies["state_manager"].set_state.assert_called_once_with("session", "mode", "live")
        mock_bot_dependencies["edit_message"].assert_called_once()
        args, kwargs = mock_bot_dependencies["edit_message"].call_args
        assert "Status" in args[0]
        assert "Menu" in args[0]
        assert kwargs.get("reply_markup") is not None
        mock_bot_dependencies["send_message"].assert_not_called()
        assert await fsm_context.get_state() is None

@pytest.mark.asyncio
@patch('listener_bot.restaurar_riesgo_automatico')
@patch('listener_bot.send_risk_submenu', new_callable=AsyncMock)
async def test_handle_callback_query_liberar_riesgo(mock_send_risk_submenu, mock_restaurar_riesgo, mock_bot_dependencies, fsm_context):
    cq = AsyncMock(spec=CallbackQuery, data="CMD_RIESGO_LIBERAR")
    cq.message = AsyncMock(spec=Message, chat=MagicMock(id=123))
    cq.message.edit_text = AsyncMock()
    cq.answer = AsyncMock()

    await listener_bot.handle_callback_query(cq, fsm_context)

    cq.answer.assert_called_once()
    mock_restaurar_riesgo.assert_called_once()
    cq.message.edit_text.assert_called_once_with("✅ Riesgo automático restaurado.")
    mock_send_risk_submenu.assert_called_once_with(cq, is_edit=False)

@pytest.mark.asyncio
@patch('listener_bot.handle_shield_action', new_callable=AsyncMock)
async def test_handle_callback_query_detener_bot(mock_handle_shield, mock_bot_dependencies, fsm_context):
    cq = AsyncMock(spec=CallbackQuery, data="CMD_DETENER_BOT")
    cq.message = AsyncMock(spec=Message, chat=MagicMock(id=123))
    cq.answer = AsyncMock()

    await listener_bot.handle_callback_query(cq, fsm_context)

    cq.answer.assert_called_once()
    mock_handle_shield.assert_called_once_with(123, cq.message, "extremo", True, is_main_menu=True)

@pytest.mark.asyncio
@patch('listener_bot.generar_reporte_kpis', new_callable=AsyncMock)
async def test_handle_callback_query_generar_kpis(mock_generar_kpis, mock_bot_dependencies, fsm_context):
    cq = AsyncMock(spec=CallbackQuery, data="CMD_ANALISIS_GENERAR_KPIS")
    cq.message = AsyncMock(spec=Message, chat=MagicMock(id=123))
    cq.answer = AsyncMock()

    await listener_bot.handle_callback_query(cq, fsm_context)

    cq.answer.assert_called_once_with("Generando reporte de KPIs...")
    mock_generar_kpis.assert_called_once_with(mock_bot_dependencies["bot"], 123)
    mock_bot_dependencies["edit_message"].assert_not_called()

@pytest.mark.asyncio
@patch('listener_bot.set_main_bot_commands', new_callable=AsyncMock)
@patch('listener_bot.dp.start_polling', new_callable=AsyncMock)
async def test_main_function(mock_start_polling, mock_set_commands, mock_bot_dependencies, monkeypatch):
    monkeypatch.setattr(listener_bot, 'chat_id_int', 12345)
    monkeypatch.setattr(listener_bot, 'bot', mock_bot_dependencies["bot"])

    with patch('listener_bot.alerter.send_alert') as mock_alert:
        await listener_bot.main()

        mock_set_commands.assert_called_once_with(mock_bot_dependencies["bot"])
        mock_alert.assert_called_once()
        mock_start_polling.assert_called_once_with(mock_bot_dependencies["bot"])
