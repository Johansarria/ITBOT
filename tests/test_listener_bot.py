# tests/test_listener_bot.py

import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch, mock_open, MagicMock, call
from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from datetime import datetime
from zoneinfo import ZoneInfo

# Importar las funciones a probar y sus dependencias
from listener_bot import (
    start_command, help_command, go_live_command, process_live_confirmation,
    process_mode_selection, handle_callback_query, main, get_main_menu,
    RiskStates, InitialStates, LiveModeStates, get_current_status_text,
    send_risk_submenu, send_analysis_submenu, send_reports_submenu, send_config_submenu,
    get_mode_selection_keyboard, send_risk_limits_submenu, send_shield_submenu,
    send_historical_operations, process_risk_percentage, process_limit_value
)

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
        patch('listener_bot.mq', new_callable=MagicMock) as mock_mq,
        patch('listener_bot.settings') as mock_settings
    ):
        mock_settings.TELEGRAM_CHAT_ID = 12345
        mock_settings.LIVE_UNLOCK_FILE_PATH = '/mock/path/unlock.file'
        mock_state_manager.get_state.return_value = None
        
        yield {
            "bot": mock_bot,
            "send_message": mock_send_message,
            "edit_message": mock_edit_message,
            "state_manager": mock_state_manager,
            "strategy_manager": mock_strategy_manager,
            "mq": mock_mq,
            "settings": mock_settings
        }

@pytest.fixture
def fsm_context():
    """Fixture para crear un FSMContext para las pruebas."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=123, user_id=123)
    return FSMContext(storage=storage, key=key)

# === Pruebas para Comandos ===

@pytest.mark.asyncio
async def test_start_command_initial_state(mock_bot_dependencies, fsm_context):
    """Prueba /start cuando no hay un modo de sesión configurado."""
    mock_bot_dependencies["state_manager"].get_state.return_value = None
    message = AsyncMock(spec=Message, chat=MagicMock(id=123), from_user=MagicMock(id=123))
    
    with patch('listener_bot.get_mode_selection_keyboard') as mock_get_keyboard:
        mock_get_keyboard.return_value = ("Select mode", MagicMock())
        await start_command(message, fsm_context)
    
    mock_get_keyboard.assert_called_once()
    mock_bot_dependencies["send_message"].assert_called_once_with(
        mock_bot_dependencies["bot"], 123, "Select mode", reply_markup=mock_get_keyboard.return_value[1]
    )
    assert await fsm_context.get_state() == InitialStates.waiting_for_mode_selection

@pytest.mark.asyncio
async def test_start_command_mode_set(mock_bot_dependencies, fsm_context):
    """Prueba /start cuando ya existe un modo de sesión."""
    mock_bot_dependencies["state_manager"].get_state.return_value = "test"
    message = AsyncMock(spec=Message, chat=MagicMock(id=123), from_user=MagicMock(id=123))

    with (
        patch('listener_bot.get_current_status_text', return_value="Status") as mock_status,
        patch('listener_bot.get_main_menu', return_value=("Menu", MagicMock())) as mock_menu
    ):
        await start_command(message, fsm_context)
        mock_status.assert_called_once()
        mock_menu.assert_called_once()
        calls = [
            call(mock_bot_dependencies["bot"], 123, "Status"),
            call(mock_bot_dependencies["bot"], 123, "Menu", reply_markup=mock_menu.return_value[1])
        ]
        mock_bot_dependencies["send_message"].assert_has_calls(calls)

@pytest.mark.asyncio
async def test_help_command(mock_bot_dependencies):
    """Prueba el comando /help."""
    message = AsyncMock(spec=Message, chat=MagicMock(id=123), from_user=MagicMock(id=123))
    await help_command(message)
    mock_bot_dependencies["send_message"].assert_called_once()
    sent_text = mock_bot_dependencies["send_message"].call_args[0][2]
    assert "Ayuda del Bot de Trading" in sent_text

# === Pruebas para Callbacks y FSM ===

@pytest.mark.asyncio
async def test_process_mode_selection(mock_bot_dependencies, fsm_context):
    """Prueba la selección de modo desde el teclado inline."""
    cq = AsyncMock(spec=CallbackQuery, data="select_mode:live")
    cq.message = AsyncMock(spec=Message, chat=MagicMock(id=123))
    cq.answer = AsyncMock()

    with (
        patch('listener_bot.get_current_status_text', return_value="Status") as mock_status,
        patch('listener_bot.get_main_menu', return_value=("Menu", MagicMock())) as mock_menu
    ):
        await process_mode_selection(cq, fsm_context)
        cq.answer.assert_called_once()
        mock_bot_dependencies["state_manager"].set_state.assert_called_once_with("session", "mode", "live")
        mock_bot_dependencies["edit_message"].assert_called_once()
        mock_bot_dependencies["send_message"].assert_has_calls([
            call(mock_bot_dependencies["bot"], 123, "Status"),
            call(mock_bot_dependencies["bot"], 123, "Menu", reply_markup=mock_menu.return_value[1])
        ])
        assert await fsm_context.get_state() is None

@pytest.mark.asyncio
@patch('listener_bot.restaurar_riesgo_automatico')
@patch('listener_bot.send_risk_submenu', new_callable=AsyncMock)
async def test_handle_callback_query_liberar_riesgo(mock_send_risk_submenu, mock_restaurar_riesgo, mock_bot_dependencies, fsm_context):
    """Prueba el callback para liberar el riesgo forzado."""
    cq = AsyncMock(spec=CallbackQuery, data="CMD_RIESGO_LIBERAR")
    cq.message = AsyncMock(spec=Message, chat=MagicMock(id=123))
    cq.message.edit_text = AsyncMock()
    cq.answer = AsyncMock()

    await handle_callback_query(cq, fsm_context)

    cq.answer.assert_called_once()
    mock_restaurar_riesgo.assert_called_once()
    cq.message.edit_text.assert_called_once_with("✅ Riesgo automático restaurado.")
    mock_send_risk_submenu.assert_called_once_with(cq, is_edit=False)

@pytest.mark.asyncio
@patch('listener_bot.handle_shield_action', new_callable=AsyncMock)
async def test_handle_callback_query_detener_bot(mock_handle_shield, mock_bot_dependencies, fsm_context):
    """Prueba el callback para el kill switch."""
    cq = AsyncMock(spec=CallbackQuery, data="CMD_DETENER_BOT")
    cq.message = AsyncMock(spec=Message, chat=MagicMock(id=123))
    cq.answer = AsyncMock()

    await handle_callback_query(cq, fsm_context)

    cq.answer.assert_called_once()
    mock_handle_shield.assert_called_once_with(123, cq.message, "extremo", True, is_main_menu=True)

@pytest.mark.asyncio
@patch('listener_bot.generar_reporte_kpis', new_callable=AsyncMock)
@patch('listener_bot.send_analysis_submenu', new_callable=AsyncMock)
async def test_handle_callback_query_generar_kpis(mock_send_analysis_submenu, mock_generar_kpis, mock_bot_dependencies, fsm_context):
    """Prueba el callback para generar KPIs."""
    cq = AsyncMock(spec=CallbackQuery, data="CMD_ANALISIS_GENERAR_KPIS")
    cq.message = AsyncMock(spec=Message, chat=MagicMock(id=123))
    cq.answer = AsyncMock()

    await handle_callback_query(cq, fsm_context)

    cq.answer.assert_called_once()
    mock_bot_dependencies["edit_message"].assert_called_once()
    mock_generar_kpis.assert_called_once_with(mock_bot_dependencies["bot"], 123)
    mock_send_analysis_submenu.assert_called_once()

@pytest.mark.asyncio
@patch('listener_bot.set_main_bot_commands', new_callable=AsyncMock)
@patch('listener_bot.dp.start_polling', new_callable=AsyncMock)
async def test_main_function(mock_start_polling, mock_set_commands, mock_bot_dependencies):
    """Prueba la función principal de arranque del bot."""
    with patch('asyncio.run') as mock_asyncio_run:
        await main()

        mock_set_commands.assert_called_once_with(mock_bot_dependencies["bot"])
        mock_bot_dependencies["send_message"].assert_called_once_with(
            mock_bot_dependencies["bot"], 12345, "✅ Bot iniciado y listo para operar."
        )
        mock_start_polling.assert_called_once_with(mock_bot_dependencies["bot"])