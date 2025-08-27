import pytest
import pandas as pd
from aiogram import types
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime

# Import the module to be tested
import listener_bot as lb

def test_get_main_menu():
    """
    Tests the main menu generation.
    """
    text, markup = lb.get_main_menu()
    assert isinstance(text, str)
    assert "Menú principal" in text
    assert isinstance(markup, types.InlineKeyboardMarkup)
    assert any(button.text == "📊 Análisis" for row in markup.inline_keyboard for button in row)

@pytest.mark.asyncio
async def test_get_current_status_text_happy_path(monkeypatch):
    """
    Tests the status text generation under normal, happy-path conditions.
    All patches are applied to the 'listener_bot' (lb) namespace where the functions are looked up.
    """
    # Mock async dependencies
    mock_get_open_positions = AsyncMock(return_value="Resumen de Posiciones Abiertas")
    monkeypatch.setattr(lb, 'get_open_positions_summary', mock_get_open_positions)

    # Mock synchronous dependencies
    monkeypatch.setattr(lb, 'obtener_estado_escudo_texto', lambda: "🛡️ Escudo: INACTIVO")
    monkeypatch.setattr(lb, 'get_closed_positions_summary', lambda: "Resumen de Posiciones Cerradas")
    monkeypatch.setattr(lb, 'riesgo_forzado_activo', lambda: True)
    monkeypatch.setattr(lb, 'obtener_riesgo_actual', lambda: 0.05) # 5%
    monkeypatch.setattr(lb, 'duracion_riesgo_forzado', lambda: "2h 30m")

    mock_strategy = MagicMock()
    mock_strategy.name = "Estrategia de Prueba"
    mock_sm = MagicMock()
    mock_sm.get_active_strategy.return_value = mock_strategy
    monkeypatch.setattr(lb, 'strategy_manager', mock_sm)

    mock_df = pd.DataFrame({
        'timestamp_open': pd.to_datetime(['2023-10-27 10:00:00', '2023-10-27 12:00:00']),
        'profit_loss_pct': [0.5, -0.2]
    })
    monkeypatch.setattr(pd, 'read_csv', lambda *args, **kwargs: mock_df) # Patching pandas directly
    
    class MockDateTime(datetime):
        @classmethod
        def now(cls):
            return datetime(2023, 10, 27)
    monkeypatch.setattr(lb, 'datetime', MockDateTime)

    status_text = await lb.get_current_status_text()

    mock_get_open_positions.assert_awaited_once_with(lb.bot)
    assert "Estrategia: <b>Estrategia de Prueba</b>" in status_text
    assert "P/L Día: 0.30%" in status_text
    assert "Riesgo: Forzado (5.00%) desde hace 2h 30m" in status_text
    assert "Resumen de Posiciones Abiertas" in status_text

@pytest.mark.asyncio
async def test_get_current_status_text_no_operations_file(monkeypatch):
    """
    Tests status text generation when the operations file is not found.
    """
    monkeypatch.setattr(lb, 'get_open_positions_summary', AsyncMock(return_value=""))
    monkeypatch.setattr(lb, 'obtener_estado_escudo_texto', lambda: "")
    monkeypatch.setattr(lb, 'get_closed_positions_summary', lambda: "")
    monkeypatch.setattr(lb, 'riesgo_forzado_activo', lambda: False)
    monkeypatch.setattr(lb, 'obtener_riesgo_actual', lambda: 0.01)
    monkeypatch.setattr(lb, 'strategy_manager', MagicMock())
    monkeypatch.setattr(pd, 'read_csv', MagicMock(side_effect=FileNotFoundError("File not found")))

    status_text = await lb.get_current_status_text()

    assert "P/L Día: 0.00%" in status_text
    assert "Ops Día: Total: 0 (Pos: 0, Neg: 0)" in status_text

@pytest.mark.asyncio
async def test_send_submenu_modes():
    """Tests that send_submenu calls the correct message method."""
    mock_message = AsyncMock(spec=types.Message)
    mock_message.edit_text = AsyncMock()
    mock_message.answer = AsyncMock()
    mock_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[]])

    # Test edit mode
    await lb.send_submenu(mock_message, "Edit Text", mock_keyboard, is_edit=True)
    mock_message.edit_text.assert_awaited_once_with("Edit Text", reply_markup=mock_keyboard)
    mock_message.answer.assert_not_called()

    # Reset mocks and test answer mode
    mock_message.edit_text.reset_mock()
    mock_message.answer.reset_mock()
    await lb.send_submenu(mock_message, "Answer Text", mock_keyboard, is_edit=False)
    mock_message.answer.assert_awaited_once_with("Answer Text", reply_markup=mock_keyboard)
    mock_message.edit_text.assert_not_called()
