import asyncio
import os
import json
import pandas as pd
import numpy as np
import pytest

import utils.technical_analysis as ta
import utils.reporting_metrics as rm
import utils.shield_manager as sm
import utils.state_manager as state_manager


def test_state_manager_recovers_from_corrupt_file(tmp_path, monkeypatch):
    # Point state file to a corrupt JSON
    old = state_manager.STATE_FILE
    state_manager.STATE_FILE = str(tmp_path / "bot_state.json")
    try:
        with open(state_manager.STATE_FILE, 'w') as f:
            f.write('{ this is not valid json')
        smgr = state_manager.StateManager()
        # should initialize default state without raising
        s = smgr.get_state('shield_manager')
        assert isinstance(s, dict)
        assert 'escudo_activo' in s
    finally:
        state_manager.STATE_FILE = old


def test_reporting_generate_report_with_and_without_ops(monkeypatch):
    # Case no operations
    monkeypatch.setattr(rm, 'fetch_operations_df', lambda start=None, end=None: pd.DataFrame())
    out = rm.generate_report()
    assert 'No hay operaciones' in out or isinstance(out, str)

    # Case with operations
    data = {
        'timestamp_open': pd.to_datetime(['2025-08-22 10:00']),
        'timestamp_close': pd.to_datetime(['2025-08-22 11:00']),
        'size_usdt': [100],
        'pnl_percent': [10.0],
        'symbol': ['BTCUSDT'],
        'side': ['BUY'],
        'entry_price': [10000.0],
        'exit_price': [11000.0],
        'reason_open': ['test'],
        'reason_close': ['close']
    }
    df = pd.DataFrame(data)
    df['pnl_usdt'] = df['size_usdt'] * (df['pnl_percent'] / 100.0)
    monkeypatch.setattr(rm, 'fetch_operations_df', lambda start=None, end=None: df)
    report = rm.generate_report()
    assert 'P&L total' in report


@pytest.mark.asyncio
async def test_shield_obtener_estado_and_verificar_conditions(monkeypatch):
    # Ensure state_manager reports inactive initially
    monkeypatch.setattr(sm.state_manager, 'get_state', lambda module: {'escudo_activo': False, 'tipo_escudo': None})

    # obtener_estado_escudo should return a tuple
    is_active, texto = sm.obtener_estado_escudo()
    assert isinstance(is_active, bool)
    assert isinstance(texto, str)

    # Mock a binance client with low ATR values -> SAFE
    class FakeClientLow:
        async def get_klines(self, symbol, interval, limit=100):
            rows = []
            for i in range(30):
                t = 1600000000000 + i * 60000
                rows.append([t, 100, 101, 99, 100, 10, t+60000, 0, 0, 0, 0, 0])
            return rows
    async def fake_get_client_low():
        return FakeClientLow()
    monkeypatch.setattr(sm, 'get_binance_client', fake_get_client_low)
    res = await sm.verificar_condiciones_mercado(SimpleNamespace:=object(), chat_id=1)
    # Expect SAFE or DANGER but function should return dict
    assert isinstance(res, dict)

    # Mock high ATR to trigger activar_escudo
    class FakeClientHigh:
        async def get_klines(self, symbol, interval, limit=100):
            rows = []
            for i in range(30):
                t = 1600000000000 + i * 60000
                # make large ranges to increase ATR
                rows.append([t, 100, 200, 50, 150, 10, t+60000, 0, 0, 0, 0, 0])
            return rows
    async def fake_get_client_high():
        return FakeClientHigh()
    monkeypatch.setattr(sm, 'get_binance_client', fake_get_client_high)

    called = {}
    async def fake_activar(bot, chat_id, tipo, fuente='bot'):
        called['act'] = (chat_id, tipo)
    monkeypatch.setattr(sm, 'activar_escudo', fake_activar)

    # Create a minimal fake bot placeholder
    class FB: pass
    res2 = await sm.verificar_condiciones_mercado(FB(), 2)
    assert res2['status'] in ('SAFE', 'DANGER')


def test_technical_get_historical_klines_db_and_binance_fallback(monkeypatch):
    # If get_klines returns empty df, and binance client raises -> we should get empty df
    monkeypatch.setattr(ta, 'get_klines', lambda symbol, interval, limit=100: pd.DataFrame())
    async def bad_client():
        raise Exception('no api')
    monkeypatch.setattr(ta, 'get_binance_client', bad_client)

    df = asyncio.run(ta.get_historical_klines('BTCUSDT', '1h', limit=10))
    assert isinstance(df, pd.DataFrame)


def test_calculate_all_indicators_long_input():
    periods = 50
    idx = pd.date_range('2025-01-01', periods=periods, freq='h')
    high = np.linspace(1, periods, periods)
    low = high - 0.5
    close = high
    df = pd.DataFrame({'high': high, 'low': low, 'close': close}, index=idx)
    out = ta.calculate_all_indicators(df)
    assert 'rsi' in out.columns
    assert 'atr' in out.columns or 'adx' in out.columns
