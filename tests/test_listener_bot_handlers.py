import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey

import listener_bot as lb
from listener_bot import RiskManagementStates

# Fixtures para Mocks reutilizables
@pytest.fixture
def mock_callback_query():
    """Creates a mock aiogram CallbackQuery object with awaitable methods."""
    mock_message = AsyncMock(spec=types.Message)
    mock_message.edit_text = AsyncMock()
    mock_message.answer = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 123
    mock_message.from_user = mock_user
    mock_cb = AsyncMock(spec=types.CallbackQuery)
    mock_cb.message = mock_message
    mock_cb.answer = AsyncMock()
    return mock_cb

@pytest.fixture
def mock_fsm_context():
    """Creates a real FSMContext with an in-memory storage for isolated testing."""
    storage = MemoryStorage()
    key = StorageKey(bot_id=lb.bot.id, chat_id=123, user_id=456)
    return FSMContext(storage=storage, key=key)

@pytest.fixture
def mock_message():
    """Creates a mock aiogram Message object with a from_user attribute."""
    message = AsyncMock(spec=types.Message)
    message.answer = AsyncMock()
    message.text = "/start"
    mock_user = MagicMock()
    mock_user.id = 456
    message.from_user = mock_user
    return message

# --- Pruebas para Command Handlers ---

@pytest.mark.asyncio
async def test_start_command(monkeypatch, mock_message):
    """Tests the /start command handler."""
    mock_get_status = AsyncMock(return_value="Estado de prueba")
    monkeypatch.setattr(lb, 'get_current_status_text', mock_get_status)
    
    mock_get_main_menu = MagicMock(return_value=("Menú principal", types.InlineKeyboardMarkup(inline_keyboard=[[]])))
    monkeypatch.setattr(lb, 'get_main_menu', mock_get_main_menu)

    await lb.start_command(mock_message)

    mock_get_status.assert_awaited_once()
    assert mock_message.answer.call_count == 2

@pytest.mark.asyncio
async def test_help_command(mock_message):
    """Tests the /help command handler."""
    await lb.help_command(mock_message)
    mock_message.answer.assert_awaited_once()
    assert "<b>❓ Ayuda del Bot de Trading</b>" in mock_message.answer.call_args.args[0]

# --- Pruebas para handle_menu_callbacks ---

@pytest.mark.asyncio
@pytest.mark.parametrize("menu_action, expected_text", [
    ("analisis", "Menú de Análisis:"),
    ("riesgo", "Menú de Gestión de Riesgo:"),
    ("reportes", "Menú de Reportes:"),
    ("config", "Menú de Configuración:"),
    ("shields", "Gestión de Escudos"),
    ("main", "Menú principal"),
])
async def test_handle_menu_callbacks_navigation(monkeypatch, mock_callback_query, menu_action, expected_text):
    """Tests that menu navigation callbacks call send_submenu with the correct text."""
    mock_callback_query.data = f"menu:{menu_action}"
    mock_send_submenu = AsyncMock()
    monkeypatch.setattr(lb, 'send_submenu', mock_send_submenu)
    monkeypatch.setattr(lb, 'riesgo_forzado_activo', lambda: False)
    monkeypatch.setattr(lb, 'obtener_estado_escudo_texto', lambda: "INACTIVO")

    await lb.handle_menu_callbacks(mock_callback_query)

    assert mock_send_submenu.call_count == 1
    call_args = mock_send_submenu.call_args[0]
    assert expected_text in call_args[1]
    mock_callback_query.answer.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_menu_callbacks_status(monkeypatch, mock_callback_query):
    """Tests the 'estado' menu action, which should trigger an alert."""
    mock_callback_query.data = "menu:estado"
    mock_get_status = AsyncMock(return_value="Estado de prueba")
    monkeypatch.setattr(lb, 'get_current_status_text', mock_get_status)

    await lb.handle_menu_callbacks(mock_callback_query)

    mock_callback_query.answer.assert_any_await("Estado de prueba", show_alert=True)

# --- Pruebas para handle_command_callbacks ---

@pytest.mark.asyncio
@pytest.mark.parametrize("command, patched_function_str, expected_kwargs", [
    ("release_risk", "listener_bot.restaurar_riesgo_automatico", None),
    ("shield_on_high", "listener_bot.activar_escudo", {'tipo': 'volatilidad_alta', 'fuente': 'manual'}),
    ("shield_off", "listener_bot.desactivar_escudo", {'fuente': 'manual'}),
])
async def test_handle_command_callbacks_actions(monkeypatch, mock_callback_query, mock_fsm_context, command, patched_function_str, expected_kwargs):
    """Tests command callbacks that trigger a direct action."""
    mock_callback_query.data = f"cmd:{command}"
    
    mock_business_logic = AsyncMock() if "activar" in patched_function_str or "desactivar" in patched_function_str else MagicMock()
    monkeypatch.setattr(patched_function_str, mock_business_logic)
    
    monkeypatch.setattr(lb, 'handle_menu_callbacks', AsyncMock())

    await lb.handle_command_callbacks(mock_callback_query, mock_fsm_context)

    if expected_kwargs:
        called_kwargs = mock_business_logic.call_args.kwargs
        for key, value in expected_kwargs.items():
            assert key in called_kwargs
            assert called_kwargs[key] == value
    else:
        mock_business_logic.assert_called_once()

    mock_callback_query.answer.assert_awaited_once()
    mock_callback_query.message.edit_text.assert_called()

@pytest.mark.asyncio
async def test_handle_command_callbacks_force_risk_fsm(mock_callback_query, mock_fsm_context):
    """Tests that 'force_risk' command correctly sets the FSM state."""
    mock_callback_query.data = "cmd:force_risk"

    await lb.handle_command_callbacks(mock_callback_query, mock_fsm_context)

    state = await mock_fsm_context.get_state()
    assert state == RiskManagementStates.waiting_for_force_risk_percentage.state
    mock_callback_query.message.edit_text.assert_awaited_once()

@pytest.mark.asyncio
@pytest.mark.parametrize("command, patched_function_str", [
    ("train_ml", "listener_bot.train_and_save_model"),
    ("optimize_strategy", "listener_bot.optimize_risk_thresholds_ga"),
    ("reload_data", "listener_bot.download_and_save_klines"),
])
async def test_handle_command_callbacks_long_running(monkeypatch, mock_callback_query, mock_fsm_context, command, patched_function_str):
    """Tests handlers for long-running tasks, ensuring they are called correctly."""
    mock_callback_query.data = f"cmd:{command}"
    mock_long_task = AsyncMock() if "reload" in command else MagicMock()
    monkeypatch.setattr(patched_function_str, mock_long_task)
    monkeypatch.setattr(lb.asyncio, 'to_thread', AsyncMock())

    await lb.handle_command_callbacks(mock_callback_query, mock_fsm_context)

    if "reload" in command:
        mock_long_task.assert_awaited_once()
    else:
        lb.asyncio.to_thread.assert_awaited_once_with(mock_long_task)
    
    assert mock_callback_query.message.edit_text.call_count > 0

@pytest.mark.asyncio
async def test_handle_command_callbacks_long_running_errors(monkeypatch, mock_callback_query, mock_fsm_context):
    """Tests that errors in long-running tasks are caught and reported."""
    mock_callback_query.data = "cmd:train_ml"
    error_message = "Entrenamiento fallido"
    monkeypatch.setattr(lb.asyncio, 'to_thread', AsyncMock(side_effect=Exception(error_message)))

    await lb.handle_command_callbacks(mock_callback_query, mock_fsm_context)

    mock_callback_query.message.answer.assert_awaited_once()
    assert f"❌ Error en entrenamiento: {error_message}" in mock_callback_query.message.answer.call_args.args[0]

@pytest.mark.asyncio
async def test_handle_command_callbacks_stop_bot(monkeypatch, mock_callback_query, mock_fsm_context):
    """Tests the stop_bot command confirmation."""
    mock_callback_query.data = "cmd:stop_bot"
    mock_send_submenu = AsyncMock()
    monkeypatch.setattr(lb, 'send_submenu', mock_send_submenu)

    await lb.handle_command_callbacks(mock_callback_query, mock_fsm_context)

    mock_send_submenu.assert_awaited_once()
    assert "<b>¿Estás seguro?</b>" in mock_send_submenu.call_args.args[1]

@pytest.mark.asyncio
async def test_handle_command_callbacks_stop_bot_confirm(monkeypatch, mock_callback_query, mock_fsm_context):
    """Tests the stop_bot_confirm command logic."""
    mock_callback_query.data = "cmd:stop_bot_confirm"
    
    # Mock a running loop
    mock_loop = MagicMock()
    monkeypatch.setattr("asyncio.get_running_loop", lambda: mock_loop)
    
    # Mock dependencies that need to be closed
    monkeypatch.setattr(lb.dp, 'storage', AsyncMock())
    monkeypatch.setattr(lb.dp.fsm, 'storage', AsyncMock())
    monkeypatch.setattr(lb.bot, 'session', AsyncMock())

    await lb.handle_command_callbacks(mock_callback_query, mock_fsm_context)

    lb.dp.storage.close.assert_awaited_once()
    lb.dp.fsm.storage.close.assert_awaited_once()
    lb.bot.session.close.assert_awaited_once()
    mock_loop.stop.assert_called_once()

# --- Pruebas para FSM Handlers ---

@pytest.mark.asyncio
async def test_process_forced_risk_percentage_valid(monkeypatch, mock_fsm_context):
    """Tests the FSM handler with valid numeric input."""
    mock_message = AsyncMock(spec=types.Message)
    mock_message.text = "5"
    mock_message.answer = AsyncMock()
    
    mock_activar_riesgo = MagicMock()
    monkeypatch.setattr(lb, 'activar_riesgo_forzado', mock_activar_riesgo)
    monkeypatch.setattr(lb, 'send_submenu', AsyncMock())

    await lb.process_forced_risk_percentage(mock_message, mock_fsm_context)

    mock_activar_riesgo.assert_called_once_with(0.05)
    mock_message.answer.assert_awaited_once_with("✅ Riesgo forzado activado al <b>5.0%</b>.")
    
    current_state = await mock_fsm_context.get_state()
    assert current_state is None

@pytest.mark.asyncio
async def test_process_forced_risk_percentage_invalid(mock_fsm_context):
    """Tests the FSM handler with invalid (non-numeric) input."""
    mock_message = AsyncMock(spec=types.Message)
    mock_message.text = "abc"
    mock_message.answer = AsyncMock()

    await mock_fsm_context.set_state(RiskManagementStates.waiting_for_force_risk_percentage)

    await lb.process_forced_risk_percentage(mock_message, mock_fsm_context)

    mock_message.answer.assert_awaited_once_with("Por favor, envía solo un número para el porcentaje. Inténtalo de nuevo.")
    
    current_state = await mock_fsm_context.get_state()
    assert current_state == RiskManagementStates.waiting_for_force_risk_percentage.state

# --- Pruebas para la Lógica del Scheduler ---

def test_setup_scheduler():
    """Tests that the scheduler is configured with the correct number of jobs."""
    scheduler = lb.setup_scheduler()
    jobs = scheduler.get_jobs()
    assert len(jobs) == 4 # Check if all scheduled jobs were added
