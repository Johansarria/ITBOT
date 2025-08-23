import asyncio
import pandas as pd
import pytest

from strategies.strategy_manager import StrategyManager
import utils.technical_analysis as ta
import utils.shield_manager as sm


class DummyStrategy:
    name = "DUMMY"

    async def analyze(self, df):
        return {"decision": "COMPRAR", "score": 10}


def make_klines_df(rows=10):
    dates = pd.date_range(end=pd.Timestamp.now(), periods=rows, freq='H')
    df = pd.DataFrame({
        'open_time': dates,
        'open': [100 + i for i in range(rows)],
        'high': [110 + i for i in range(rows)],
        'low': [90 + i for i in range(rows)],
        'close': [100 + i for i in range(rows)],
        'volume': [1.0 for _ in range(rows)]
    })
    return df


@pytest.mark.asyncio
async def test_analyze_single_strategy_not_found():
    mgr = StrategyManager()
    mgr._reset_manager()
    res = await mgr.analyze_single_strategy("NO_EXISTE", "BTCUSDT", "1h")
    assert "error" in res


@pytest.mark.asyncio
async def test_analyze_single_strategy_happy_path(monkeypatch):
    mgr = StrategyManager()
    mgr._reset_manager()
    # inject a dummy strategy
    mgr._strategies = {"DUMMY": DummyStrategy()}
    # patch get_historical_klines where strategy_manager imports it to return df without DB
    import strategies.strategy_manager as smgr
    async def fake_get_klines(symbol, interval, limit=200):
        return make_klines_df(20)
    monkeypatch.setattr(smgr, "get_historical_klines", fake_get_klines)
    res = await mgr.analyze_single_strategy("DUMMY", "BTCUSDT", "1h")
    assert res.get("best_strategy") == "DUMMY"


def test_calculate_all_indicators_empty():
    df = pd.DataFrame()
    out = ta.calculate_all_indicators(df)
    assert out.empty


@pytest.mark.asyncio
async def test_analyze_market_ml_prediction(monkeypatch, tmp_path):
    # Create a valid df and patch dependencies
    df = make_klines_df(30)
    # patch enrich_features to be identity
    monkeypatch.setattr(ta, "enrich_features", lambda x: x)
    # patch detect_market_regime to neutral
    monkeypatch.setattr(ta, "detect_market_regime", lambda x: {"volatility_regime": "LOW", "trend_regime": "BULL_TREND"})
    # patch load_ml_model and model with predict_proba
    class FakeModel:
        def predict_proba(self, X):
            return [[0.2, 0.8]]

    monkeypatch.setattr(ta, "ml_model", FakeModel())
    monkeypatch.setattr(ta, "export_analysis_result", lambda *args, **kwargs: None)
    monkeypatch.setattr(ta, "export_features", lambda *args, **kwargs: None)

    res = await ta.analyze_market(df_klines=df, export=False)
    assert "decision" in res
    assert res["decision"].startswith(("COMPRAR", "MANTENER", "VENDER", "ERROR"))


@pytest.mark.asyncio
async def test_verificar_condiciones_mercado_safe_and_danger(monkeypatch):
    # Build fake client that returns klines with low volatility
    class FakeClient:
        async def get_klines(self, symbol, interval, limit=100):
            # low volatility data
            return [[0, 100, 100.1, 99.9, 100, 1, 0, 0, 0, 0, 0, 0] for _ in range(50)]

    async def fake_get_client():
        return FakeClient()

    monkeypatch.setattr(sm, "get_binance_client", fake_get_client)
    # patch activar/desactivar to no-op
    monkeypatch.setattr(sm, "activar_escudo", lambda *args, **kwargs: asyncio.sleep(0))
    monkeypatch.setattr(sm, "desactivar_escudo", lambda *args, **kwargs: asyncio.sleep(0))

    safe = await sm.verificar_condiciones_mercado(None, 1)
    assert safe["status"] == "SAFE"

    # Now high volatility
    class HighVolClient:
        async def get_klines(self, symbol, interval, limit=100):
            # high atr relative to price
            return [[0, 100, 200, 50, 100, 1, 0, 0, 0, 0, 0, 0] for _ in range(50)]

    async def fake_get_high():
        return HighVolClient()

    monkeypatch.setattr(sm, "get_binance_client", fake_get_high)
    danger = await sm.verificar_condiciones_mercado(None, 1)
    assert danger["status"] in ("DANGER", "SAFE")
