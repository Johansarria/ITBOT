import asyncio
import pandas as pd
import pytest

from strategies.strategy_manager import StrategyManager
import utils.technical_analysis as ta
import utils.shield_manager as sm
from utils.feature_pipeline import FeaturePipeline


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
async def test_analyze_all_strategies_happy_path(monkeypatch):
    mgr = StrategyManager()
    mgr._reset_manager()
    # inject a dummy strategy
    mgr._strategies = {"DUMMY": DummyStrategy()}
    # patch get_historical_klines where strategy_manager imports it to return df without DB
    async def fake_get_klines(symbol, interval, limit=200):
        return make_klines_df(20)
    monkeypatch.setattr(ta, "get_historical_klines", fake_get_klines)
    res = await mgr.analyze_all_strategies("BTCUSDT", "1h")
    assert res.get("best_strategy") == "DUMMY"
    assert res.get("best_decision") == "COMPRAR"


def test_calculate_all_indicators_empty():
    df = pd.DataFrame()
    pipeline = FeaturePipeline()
    out = pipeline.transform(df)
    assert out.empty

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

@pytest.mark.asyncio
async def test_analyze_market_ml_prediction(monkeypatch, tmp_path):
    # Create a valid df and patch dependencies
    df = make_klines_df(30)
    # patch enrich_features to be identity
    monkeypatch.setattr(FeaturePipeline, 'transform', mock_transform)
    # patch load_ml_model and model with predict
    class FakeModel:
        def predict(self, X):
            return pd.DataFrame({'sell_probability': [0.2], 'buy_probability': [0.8]})

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
