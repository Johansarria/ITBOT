import asyncio
import pandas as pd
import pytest

import utils.technical_analysis as ta
import utils.reporting_metrics as rm
import utils.shield_manager as sm
import database.database_manager as dbm


@pytest.mark.asyncio
async def test_get_historical_klines_db_empty_and_binance_failure(monkeypatch):
    # DB returns empty: patch the symbol used inside the module under test
    monkeypatch.setattr(ta, "get_klines", lambda symbol, interval: pd.DataFrame())
    # binance client raises
    async def fake_get_client():
        raise Exception("api down")
    monkeypatch.setattr(ta, "get_binance_client", fake_get_client)

    df = await ta.get_historical_klines("BTCUSDT", "1h", limit=10)
    assert isinstance(df, pd.DataFrame)
    assert df.empty


from utils.feature_pipeline import FeaturePipeline

def mock_transform(self, df):
    df['rsi'] = 50
    df['macd'] = 0
    df['macd_signal'] = 0
    df['stoch_k'] = 50
    df['stoch_d'] = 50
    df['cci'] = 0
    df['adx'] = 20
    df['atr'] = 1
    df['bb_upper'] = 100
    df['bb_lower'] = 90
    return df

def test_calculate_all_indicators_nan_handling():
    # create longer df (ta indicators like ADX expect a larger window)
    periods = 30
    idx = pd.date_range('2025-01-01', periods=periods, freq='h')
    high = list(range(1, periods + 1))
    low = [h - 0.5 for h in high]
    close = ['a'] + [str(x) for x in range(2, periods + 1)]
    df = pd.DataFrame({'high': high, 'low': low, 'close': close, 'volume': [100]*periods}, index=idx)
    pipeline = FeaturePipeline()
    out = pipeline.transform(df)
    # Indicators should be present and DataFrame should not be empty
    assert 'rsi' in out.columns
    assert 'macd' in out.columns
    assert not out.empty


@pytest.mark.asyncio
async def test_analyze_market_ml_not_loaded(monkeypatch):
    periods = 40
    idx = pd.date_range('2025-01-01', periods=periods, freq='h')
    df = pd.DataFrame({
        'high': list(range(1, periods + 1)),
        'low': [1] * periods,
        'close': list(range(1, periods + 1)),
        'volume': [1] * periods
    }, index=idx)
    # prevent model loading
    monkeypatch.setattr(ta, "ml_model", None)
    monkeypatch.setattr(ta, "load_ml_model", lambda : None)
    monkeypatch.setattr(FeaturePipeline, 'transform', mock_transform)
    monkeypatch.setattr(ta, "export_analysis_result", lambda *a, **k: None)
    monkeypatch.setattr(ta, "export_features", lambda *a, **k: None)

    res = await ta.analyze_market(df_klines=df, export=False)
    assert res['decision'] == 'ERROR_ML_NO_CARGADO'


@pytest.mark.asyncio
async def test_analyze_market_ml_prediction_exception(monkeypatch):
    periods = 40
    idx = pd.date_range('2025-01-01', periods=periods, freq='h')
    df = pd.DataFrame({
        'high': list(range(1, periods + 1)),
        'low': [1] * periods,
        'close': list(range(1, periods + 1)),
        'volume': [1] * periods
    }, index=idx)
    monkeypatch.setattr(FeaturePipeline, 'transform', mock_transform)

    class BadModel:
        def predict(self, X):
            raise RuntimeError("predict failed")

    monkeypatch.setattr(ta, "ml_model", BadModel())
    monkeypatch.setattr(ta, "export_analysis_result", lambda *a, **k: None)
    monkeypatch.setattr(ta, "export_features", lambda *a, **k: None)

    res = await ta.analyze_market(df_klines=df, export=False)
    assert res['decision'] == 'ERROR_ML'


def test_reporting_calculations():
    # generate a DataFrame that matches reporting_metrics expectations (contains pnl_usdt)
    data = {
        'timestamp_open': pd.to_datetime(['2025-08-20 10:00', '2025-08-20 12:00', '2025-08-21 10:00']),
        'timestamp_close': pd.to_datetime(['2025-08-20 11:00', '2025-08-20 13:00', '2025-08-21 11:00']),
        'size_usdt': [100, 200, 150],
        'pnl_percent': [10.0, -5.0, 20.0]
    }
    df = pd.DataFrame(data)
    # compute pnl_usdt column to match what generate_report expects
    df['pnl_usdt'] = df['size_usdt'] * (df['pnl_percent'] / 100.0)

    # patch the fetch function used by the module
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(rm, 'fetch_operations_df', lambda start=None, end=None: df)
        report = rm.generate_report()
        assert 'P&L total' in report
        assert 'Total de operaciones' in report
    finally:
        monkeypatch.undo()


def test_get_today_summary_file_missing(monkeypatch):
    # reporting_metrics does not have get_today_summary; ensure generate_report handles empty fetch
    monkeypatch.setattr(rm, 'fetch_operations_df', lambda start=None, end=None: pd.DataFrame())
    out = rm.generate_report()
    assert 'No hay operaciones' in out


@pytest.mark.asyncio
async def test_shield_manager_activate_deactivate_and_api_exception(monkeypatch):
    calls = {}
    # capture update_module_state
    def fake_update(module, updates):
        calls['updated'] = updates
    monkeypatch.setattr(sm.state_manager, "update_module_state", fake_update)

    async def fake_send_message(bot, chat_id, text):
        calls.setdefault('msgs', []).append(text)
    monkeypatch.setattr(sm, "send_message", fake_send_message)

    # Activate with a fake bot instance (minimal) to satisfy type hints
    class FakeBot: pass
    bot = FakeBot()
    # Ensure state reports no active shield so activation proceeds
    monkeypatch.setattr(sm.state_manager, 'get_state', lambda module: {'escudo_activo': False, 'tipo_escudo': None})
    await sm.activar_escudo(bot, 123, tipo='volatilidad_alta', fuente='manual')
    assert calls.get('updated') is not None

    # API exception during verificar_condiciones_mercado should activate escudo
    async def bad_client():
        raise Exception("boom")
    monkeypatch.setattr(sm, "get_binance_client", bad_client)
    # stub activar_escudo to record
    async def rec_activar(*args, **kwargs):
        calls['activated'] = True
    monkeypatch.setattr(sm, "activar_escudo", rec_activar)

    res = await sm.verificar_condiciones_mercado(bot, 1)
    assert res['status'] == 'DANGER'
    assert calls.get('activated') is True
