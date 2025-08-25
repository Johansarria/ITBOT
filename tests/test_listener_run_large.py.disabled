import asyncio
import pandas as pd
import types
import os
import pytest

import listener_bot as lb


class FakeChat:
    def __init__(self, id=123):
        self.id = id


class FakeUser:
    def __init__(self, id=321):
        self.id = id


class FakeMessage:
    def __init__(self, chat_id=123, user_id=321, text=None):
        self.chat = FakeChat(chat_id)
        self.from_user = FakeUser(user_id)
        self.text = text
        self._answers = []

    async def answer(self, text, reply_markup=None):
        self._answers.append(('answer', text))

    async def edit_text(self, text, reply_markup=None):
        self._answers.append(('edit', text))


class FakeCallbackQuery:
    def __init__(self, data, message=None):
        self.data = data
        self._message = message or FakeMessage()

    @property
    def message(self):
        return self._message

    async def answer(self):
        return True


class FakeState:
    def __init__(self):
        self._state = None
        self._data = {}

    async def set_state(self, s):
        self._state = s

    async def clear(self):
        self._state = None

    async def get_data(self):
        return self._data

    async def update_data(self, **k):
        self._data.update(k)


@pytest.mark.asyncio
async def test_get_main_menu_killswitch_variants(monkeypatch):
    # When killswitch activo
    monkeypatch.setattr(lb, 'escudo_activo', lambda: 'extremo')
    text, markup = lb.get_main_menu()
    assert isinstance(text, str)
    assert 'Menú' in text or text == 'Menú principal'

    # When not active
    monkeypatch.setattr(lb, 'escudo_activo', lambda: '')
    text2, markup2 = lb.get_main_menu()
    assert isinstance(markup2, type(markup))


@pytest.mark.asyncio
async def test_start_command_mode_selection_and_status(monkeypatch):
    fake_msg = FakeMessage()
    fake_state = FakeState()

    # case: session_mode is None -> prompts for mode selection
    monkeypatch.setattr(lb.state_manager, 'get_state', lambda *a, **k: None)
    sent = {}
    async def fake_send_message(bot, chat_id, text, **kwargs):
        sent['last'] = text
    monkeypatch.setattr(lb, 'send_message', fake_send_message)

    await lb.start_command(fake_msg, fake_state)
    assert 'Por favor' in sent.get('last', '') or sent.get('last') is not None

    # case: session_mode set -> sends status and menu
    def fake_get_state(key, *args, **kwargs):
        if key == 'session':
            return 'live'
        if key == 'shield_manager':
            return {'escudo_activo': False, 'tipo_escudo': 'ninguno'}
        return None
    monkeypatch.setattr(lb.state_manager, 'get_state', fake_get_state)
    monkeypatch.setattr(lb, 'get_current_status_text', lambda : asyncio.get_event_loop().create_future())
    # make future return string
    f = asyncio.get_event_loop().create_future()
    f.set_result('STATUS')
    monkeypatch.setattr(lb, 'get_current_status_text', lambda : f)
    called = []
    async def fake_send(bot, chat_id, text, **kwargs):
        called.append(text)
    monkeypatch.setattr(lb, 'send_message', fake_send)

    await lb.start_command(fake_msg, fake_state)
    assert any('STATUS' in c or 'Menú' in c for c in called)


@pytest.mark.asyncio
async def test_process_mode_selection_and_callback_flows(monkeypatch):
    fake_msg = FakeMessage()
    fake_state = FakeState()
    cq = FakeCallbackQuery('select_mode:live', message=fake_msg)

    calls = {}
    monkeypatch.setattr(lb.state_manager, 'set_state', lambda *a, **k: calls.setdefault('set_state', True))

    # patch edit_message_safely and send_message and get_main_menu
    async def fake_edit(msg, text, reply_markup=None):
        calls['edited'] = text
    monkeypatch.setattr(lb, 'edit_message_safely', fake_edit)

    async def fake_send(bot, chat_id, text, **kwargs):
        calls.setdefault('sent', []).append(text)
    monkeypatch.setattr(lb, 'send_message', fake_send)

    monkeypatch.setattr(lb, 'get_main_menu', lambda: ('M', None))

    await lb.process_mode_selection(cq, fake_state)
    assert calls.get('edited') is not None
    assert 'sent' in calls


@pytest.mark.asyncio
async def test_handle_callback_query_manual_buy_and_other(monkeypatch):
    fake_msg = FakeMessage()
    # manual buy success
    cq_buy = FakeCallbackQuery('CMD_MANUAL_BUY_BTC', message=fake_msg)
    monkeypatch.setattr(lb.mq, 'publish_decision', lambda d: True)
    called = {}
    async def fake_edit(msg, text, reply_markup=None):
        called.setdefault('edit', []).append(text)
    monkeypatch.setattr(lb, 'edit_message_safely', fake_edit)

    await lb.handle_callback_query(cq_buy, FakeState())
    assert any('orden' in t.lower() or 'orden' in t for t in called.get('edit', []))

    # manual buy failure
    cq_buy_fail = FakeCallbackQuery('CMD_MANUAL_BUY_BTC', message=fake_msg)
    monkeypatch.setattr(lb.mq, 'publish_decision', lambda d: False)
    called2 = {}
    async def fake_edit2(msg, text, reply_markup=None):
        called2.setdefault('edit', []).append(text)
    monkeypatch.setattr(lb, 'edit_message_safely', fake_edit2)
    await lb.handle_callback_query(cq_buy_fail, FakeState())
    assert any('error' in t.lower() or 'error' in t for t in called2.get('edit', []))


@pytest.mark.asyncio
async def test_process_risk_percentage_and_limit(monkeypatch):
    fake_msg = FakeMessage(text='5')
    fake_state = FakeState()
    # patch activar_riesgo_forzado
    called = {}
    monkeypatch.setattr(lb, 'activar_riesgo_forzado', lambda pct: called.setdefault('activated', pct))

    # patch send_risk_submenu so it doesn't try to edit actual messages
    async def fake_send_risk(msg, is_edit=False):
        called.setdefault('submenu', True)
    monkeypatch.setattr(lb, 'send_risk_submenu', fake_send_risk)

    await lb.process_risk_percentage(fake_msg, fake_state)
    assert called.get('activated') == 0.05

    # test invalid input
    fake_msg2 = FakeMessage(text='notanumber')
    await lb.process_risk_percentage(fake_msg2, fake_state)

    # process_limit_value: set state data
    fake_msg3 = FakeMessage(text='3')
    fs = FakeState()
    fs._data = {'limit_to_edit': 'MAX_CONCURRENT_POSITIONS', 'limit_name': 'Máximo', 'limit_type': 'int'}
    monkeypatch.setattr(lb, 'update_env_file', lambda k, v: asyncio.get_event_loop().create_future())
    # make update_env_file return True
    async def upd(k, v):
        return True
    monkeypatch.setattr(lb, 'update_env_file', upd)

    await lb.process_limit_value(fake_msg3, fs)


@pytest.mark.asyncio
async def test_send_historical_operations_file_not_found_and_empty(monkeypatch, tmp_path):
    fake_msg = FakeMessage()
    # not found
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    await lb.send_historical_operations(fake_msg)
    # exists but empty
    monkeypatch.setattr(os.path, 'exists', lambda p: True)
    monkeypatch.setattr(pd, 'read_csv', lambda p, parse_dates=None: pd.DataFrame())
    await lb.send_historical_operations(fake_msg)


@pytest.mark.asyncio
async def test_handle_shield_action_calls(monkeypatch):
    fake_msg = FakeMessage()
    calls = {}
    async def fake_activar(bot, chat_id, tipo, fuente='manual'):
        calls['act'] = (chat_id, tipo)
    async def fake_desactivar(bot, chat_id, fuente='manual'):
        calls['des'] = (chat_id, fuente)
    monkeypatch.setattr(lb, 'activar_escudo', fake_activar)
    monkeypatch.setattr(lb, 'desactivar_escudo', fake_desactivar)
    # patch get_main_menu and send_risk_submenu
    monkeypatch.setattr(lb, 'get_main_menu', lambda: ('M', None))
    async def fake_send_risk(msg, is_edit=True):
        calls['risk_sub'] = True
    monkeypatch.setattr(lb, 'send_risk_submenu', fake_send_risk)

    await lb.handle_shield_action(123, fake_msg, 'volatilidad_alta', True, is_main_menu=True)
    assert 'act' in calls
    await lb.handle_shield_action(123, fake_msg, '', False, is_main_menu=False)
    assert 'des' in calls or 'risk_sub' in calls
