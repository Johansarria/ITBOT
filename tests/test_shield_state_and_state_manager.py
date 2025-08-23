import os
import json
from datetime import datetime, timedelta
from utils import state_manager
from utils import shield_manager


def test_state_manager_read_write(tmp_path, monkeypatch):
    # Point STATE_FILE to tmp path
    old = state_manager.STATE_FILE
    state_manager.STATE_FILE = str(tmp_path / "bot_state.json")
    try:
        sm = state_manager.StateManager()
        sm.set_state('test_mod', 'k', 123)
        assert sm.get_state('test_mod', 'k') == 123
        # Update module state
        sm.update_module_state('test_mod', {'x': 1, 'y': 2})
        assert sm.get_state('test_mod')['x'] == 1
    finally:
        state_manager.STATE_FILE = old


def test_shield_activate_deactivate(monkeypatch, tmp_path):
    # Use a fresh StateManager file
    old_file = state_manager.STATE_FILE
    state_manager.STATE_FILE = str(tmp_path / "bot_state.json")
    try:
        sm = state_manager.StateManager()
        # Ensure shield inactive
        sm.update_module_state('shield_manager', {'escudo_activo': False, 'tipo_escudo': None})

        class FakeBot: pass

        async def run_actions():
            await shield_manager.activar_escudo(FakeBot(), 1, 'test', fuente='manual', send_notification=False)
            assert shield_manager.escudo_activo() == 'test'
            await shield_manager.desactivar_escudo(FakeBot(), 1, fuente='manual', send_notification=False)
            assert shield_manager.escudo_activo() == 'ninguno' or shield_manager.escudo_activo() is None

        import asyncio
        # Use asyncio.run for Python 3.7+ to ensure an event loop is available
        asyncio.run(run_actions())
    finally:
        state_manager.STATE_FILE = old_file
