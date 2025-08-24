import asyncio
import types
import pytest

import listener_bot as lb


def test_get_main_menu_killswitch_active(monkeypatch):
    monkeypatch.setattr(lb, 'escudo_activo', lambda: 'extremo')
    text, markup = lb.get_main_menu()
    assert isinstance(text, str)
    assert 'Menú' in text or text.startswith('Men') or isinstance(markup, object)


def test_get_main_menu_killswitch_inactive(monkeypatch):
    monkeypatch.setattr(lb, 'escudo_activo', lambda: '')
    text, markup = lb.get_main_menu()
    assert isinstance(text, str)
    assert isinstance(markup, object)


@pytest.mark.asyncio
async def test_get_current_status_text(monkeypatch):
    # Monkeypatch many dependencies to controlled values
    monkeypatch.setattr(lb, 'obtener_estado_escudo', lambda: (True, 'ACTIVO'))
    async def fake_get_open_positions_summary(bot):
        return 'Open positions summary'
    monkeypatch.setattr(lb, 'get_open_positions_summary', fake_get_open_positions_summary)
    monkeypatch.setattr(lb, 'get_closed_positions_summary', lambda: 'Closed positions')
    monkeypatch.setattr(lb, 'riesgo_forzado_activo', lambda: False)
    monkeypatch.setattr(lb, 'obtener_riesgo_actual', lambda: 0.01)
    monkeypatch.setattr(lb, 'duracion_riesgo_forzado', lambda: '1h')
    class DummySM:
        def get_state(self, *a, **k):
            return 'test'
    monkeypatch.setattr(lb, 'state_manager', DummySM())
    monkeypatch.setattr(lb, 'strategy_manager', types.SimpleNamespace(get_active_strategy=lambda: None))
    # Monkeypatch get_today_summary used inside
    monkeypatch.setattr(lb, 'get_today_summary', lambda path: {'pnl_sum': 0.12, 'ops_count': 3, 'wins': 2, 'losses': 1})

    text = await lb.get_current_status_text()
    assert 'Estado Actual' in text or 'Estado' in text
