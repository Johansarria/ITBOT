import asyncio
import pytest
import types

import listener_bot as lb


class FakeState:
    def __init__(self):
        self._state = None
        self._data = {}

    async def set_state(self, state):
        self._state = state

    async def get_data(self):
        return self._data

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def clear(self):
        self._state = None
        self._data = {}


class FakeMsg:
    def __init__(self, text=None):
        self.text = text
        self.chat = types.SimpleNamespace(id=999)
        self.from_user = types.SimpleNamespace(id=42)
        self.sent = []

    async def answer(self, text, reply_markup=None):
        self.sent.append(("answer", text))

    async def edit_text(self, text, reply_markup=None):
        self.sent.append(("edit_text", text))


class FakeCQ:
    def __init__(self, data, msg=None):
        self.data = data
        self.message = msg or FakeMsg()
        self.answered = False

    async def answer(self):
        self.answered = True


@pytest.mark.asyncio
async def test_start_command_shows_mode_selection_when_no_session(monkeypatch):
    fake_msg = FakeMsg()
    fake_state = FakeState()
    # state_manager.get_state returns None
    monkeypatch.setattr(lb.state_manager, "get_state", lambda *args, **kwargs: None)
    calls = []
    async def fake_send_message(bot, chat_id, text, **kwargs):
        calls.append((chat_id, text))
    monkeypatch.setattr(lb, "send_message", fake_send_message)

    await lb.start_command(fake_msg, fake_state)
    assert any("modo" in c[1].lower() or "selecciona el modo" in c[1].lower() for c in calls)


@pytest.mark.asyncio
async def test_start_command_shows_status_and_menu_when_session_defined(monkeypatch):
    fake_msg = FakeMsg()
    fake_state = FakeState()
    def fake_get_state(*args, **kwargs):
        # return dict for shield_manager queries, otherwise session mode
        if args and args[0] == "shield_manager":
            return {"escudo_activo": False, "tipo_escudo": "ninguno"}
        return "live"
    monkeypatch.setattr(lb.state_manager, "get_state", fake_get_state)
    async def fake_status():
        return "STATUS"
    monkeypatch.setattr(lb, "get_current_status_text", fake_status)
    sent = []
    async def fake_send_message(bot, chat_id, text, **kwargs):
        sent.append(text)
    monkeypatch.setattr(lb, "send_message", fake_send_message)

    await lb.start_command(fake_msg, fake_state)
    assert any("STATUS" in t or "Estado" in t or "Menú principal" in t for t in sent)


@pytest.mark.asyncio
async def test_help_command_calls_send_message(monkeypatch):
    fake_msg = FakeMsg()
    sent = []
    async def fake_send_message(bot, chat_id, text, **kwargs):
        sent.append(text)
    monkeypatch.setattr(lb, "send_message", fake_send_message)
    await lb.help_command(fake_msg)
    assert sent and "Ayuda" in sent[0]


@pytest.mark.asyncio
async def test_go_live_command_blocks_when_not_live(monkeypatch, tmp_path):
    fake_msg = FakeMsg()
    fake_state = FakeState()
    monkeypatch.setattr(lb.state_manager, "get_state", lambda *args, **kwargs: "test")
    sent = []
    async def fake_send_message(bot, chat_id, text, **kwargs):
        sent.append(text)
    monkeypatch.setattr(lb, "send_message", fake_send_message)
    # ensure unlock file missing
    monkeypatch.setattr(lb.os.path, "exists", lambda p: False)
    await lb.go_live_command(fake_msg, fake_state)
    assert sent


@pytest.mark.asyncio
async def test_process_live_confirmation_success(monkeypatch):
    fake_msg = FakeMsg(text="CONFIRMAR LIVE")
    fake_state = FakeState()
    sent = []
    monkeypatch.setattr(lb.state_manager, "set_state", lambda *args, **kwargs: None)
    async def fake_send_message2(bot, chat_id, text, **kwargs):
        sent.append(text)
    monkeypatch.setattr(lb, "send_message", fake_send_message2)
    await lb.process_live_confirmation(fake_msg, fake_state)
    assert any("desbloqueado" in t.lower() or "confirm" in t.lower() or "¡el bot" in t.lower() for t in sent)


@pytest.mark.asyncio
async def test_process_mode_selection_sets_state_and_sends_messages(monkeypatch):
    fake_msg = FakeMsg()
    fake_cq = FakeCQ("select_mode:live", msg=fake_msg)
    fake_state = FakeState()
    # Patch state manager and send_message
    monkeypatch.setattr(lb.state_manager, "set_state", lambda *args, **kwargs: None)
    sent = []
    async def fake_send_message3(bot, chat_id, text, **kwargs):
        sent.append(text)
    monkeypatch.setattr(lb, "send_message", fake_send_message3)
    async def fake_status():
        return "STATUS"
    monkeypatch.setattr(lb, "get_current_status_text", fake_status)
    await lb.process_mode_selection(fake_cq, fake_state)
    assert fake_cq.answered
    assert any("STATUS" in s or "Modo" in s for s in sent)


@pytest.mark.asyncio
async def test_handle_callback_query_various_branches(monkeypatch):
    fake_msg = FakeMsg()
    fake_cq = FakeCQ("CMD_MENU_RIESGO", msg=fake_msg)
    fake_state = FakeState()
    called = {}
    async def fake_send_risk_submenu(*args, **kwargs):
        called.setdefault("risk", True)
    monkeypatch.setattr(lb, "send_risk_submenu", fake_send_risk_submenu)
    await lb.handle_callback_query(fake_cq, fake_state)
    assert called.get("risk") is True

    # test CMD_RIESGO_FORZAR path
    fake_msg2 = FakeMsg()
    fake_cq2 = FakeCQ("CMD_RIESGO_FORZAR", msg=fake_msg2)
    await lb.handle_callback_query(fake_cq2, fake_state)
    # check that message.edit_text was called and stored in fake_msg2.sent
    assert any("envía" in s[1].lower() or "por favor" in s[1].lower() for s in fake_msg2.sent)


@pytest.mark.asyncio
async def test_process_risk_percentage_valid_and_invalid(monkeypatch):
    # valid
    fake_msg = FakeMsg(text="5")
    fake_state = FakeState()
    monkeypatch.setattr(lb, "activar_riesgo_forzado", lambda pct: None)
    await lb.process_risk_percentage(fake_msg, fake_state)
    # invalid
    fake_msg2 = FakeMsg(text="xyz")
    await lb.process_risk_percentage(fake_msg2, fake_state)
    # ensure both messages had replies stored
    assert fake_msg.sent and fake_msg2.sent


@pytest.mark.asyncio
async def test_process_limit_value_success_and_invalid(monkeypatch):
    fake_msg = FakeMsg(text="3")
    fake_state = FakeState()
    async def fake_get_data():
        return {"limit_to_edit": "MAX_CONCURRENT_POSITIONS", "limit_name": "Máximo de Posiciones", "limit_type": "int"}
    fake_state.get_data = fake_get_data
    async def fake_update_env_file(key, val):
        return True
    monkeypatch.setattr(lb, "update_env_file", fake_update_env_file)
    await lb.process_limit_value(fake_msg, fake_state)

    fake_msg2 = FakeMsg(text="-1")
    fake_state2 = FakeState()
    fake_state2.get_data = fake_get_data
    await lb.process_limit_value(fake_msg2, fake_state2)
    assert fake_msg.sent and fake_msg2.sent
