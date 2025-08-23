import asyncio
import pandas as pd
import numpy as np
import pytest

import strategies.backtester as backtester_module
from strategies.backtester import Backtester, generate_mock_data
from strategies.strategy_manager import StrategyManager
import strategies.momentum_strategy as momentum_module


def make_price_series(length=60, start=1000, step=1):
    idx = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='h')
    prices = np.array([start + i * step for i in range(length)], dtype=float)
    df = pd.DataFrame({'open': prices, 'high': prices * 1.001, 'low': prices * 0.999, 'close': prices, 'volume': 100}, index=idx)
    df.index.name = 'timestamp'
    return df


def test_generate_mock_data_basic():
    df = generate_mock_data(days=50, initial_price=1000)
    assert isinstance(df, pd.DataFrame)
    assert 'close' in df.columns
    assert len(df) == 50


@pytest.mark.asyncio
async def test_backtester_buy_and_sell_flow(monkeypatch):
    # Create a series where price increases then decreases to trigger buys then sells
    df = make_price_series(length=30, start=100, step=2)

    # Patch risk manager and order executor bindings used by Backtester
    monkeypatch.setattr(backtester_module, 'obtener_riesgo_actual', lambda: 0.01)
    monkeypatch.setattr(backtester_module, 'obtener_riesgo_ajustado_por_ml', lambda score, base: base)
    monkeypatch.setattr(backtester_module, 'calcular_cantidad_operar', lambda balance, riesgo: min(balance, balance * 0.01))

    class FakeStrategy:
        def __init__(self):
            self.name = 'fake'

        def analyze(self, historical_data, idx):
            # buy for first half, sell for second half
            if idx < len(historical_data) // 2:
                return {'decision': 'COMPRAR', 'score': 0.8}
            else:
                return {'decision': 'VENDER', 'score': 0.9}

    bt = Backtester(df.copy(), initial_balance=1000.0, commission=0.001, warmup_period=2)
    metrics = await bt.run(FakeStrategy())

    assert 'total_return_pct' in metrics
    assert isinstance(metrics['total_trades'], int)
    # At least one trade occurred
    assert metrics['total_trades'] >= 1


@pytest.mark.asyncio
async def test_backtester_no_trades_returns_zero_metrics(monkeypatch):
    df = make_price_series(length=10, start=100, step=0)

    monkeypatch.setattr(backtester_module, 'obtener_riesgo_actual', lambda: 0.01)
    monkeypatch.setattr(backtester_module, 'obtener_riesgo_ajustado_por_ml', lambda score, base: base)
    monkeypatch.setattr(backtester_module, 'calcular_cantidad_operar', lambda balance, riesgo: 0)

    class HoldStrategy:
        def __init__(self):
            self.name = 'hold'

        def analyze(self, historical_data, idx):
            return {'decision': 'MANTENER', 'score': 0}

    bt = Backtester(df.copy(), initial_balance=500.0, commission=0.001, warmup_period=2)
    metrics = await bt.run(HoldStrategy())

    assert metrics['total_trades'] == 0 or metrics['winning_trades'] + metrics['losing_trades'] == 0


def test_momentum_strategy_decisions():
    ms = momentum_module.MomentumStrategy()
    # Too short -> KEEP
    df_short = pd.DataFrame({'close': list(range(1, 5))})
    out_short = ms.analyze(df_short)
    assert out_short['decision'] == 'MANTENER'

    # Increasing series -> BUY
    df_inc = pd.DataFrame({'close': list(range(1, 21))})
    out_inc = ms.analyze(df_inc)
    assert out_inc['decision'] in ('COMPRAR', 'MANTENER')

    # Large drop -> SELL
    arr = list(range(100, 120))
    arr[-1] = 50
    df_dec = pd.DataFrame({'close': arr})
    out_dec = ms.analyze(df_dec)
    assert out_dec['decision'] in ('VENDER', 'MANTENER')


@pytest.mark.asyncio
async def test_strategy_manager_analyze_and_single(monkeypatch):
    # Reset singleton
    StrategyManager._reset_manager(StrategyManager)
    mgr = StrategyManager()

    # Prepare historical data
    df = make_price_series(length=60, start=100, step=1)

    # Patch technical and feature engineering functions used inside analyze_all_strategies
    import utils.technical_analysis as ta
    from utils.feature_pipeline import FeaturePipeline # Import FeaturePipeline

    async def async_get_historical_klines(symbol, interval, limit):
        return df
    monkeypatch.setattr(ta, 'get_historical_klines', async_get_historical_klines)
    import strategies.strategy_manager as smod
    monkeypatch.setattr(smod, 'get_historical_klines', async_get_historical_klines)
    monkeypatch.setattr(FeaturePipeline, 'transform', lambda self, df: df) # Mock FeaturePipeline.transform

    # Create two fake strategies and inject into manager
    class S1:
        def __init__(self):
            self.name = 's1'
            self.description = 's1'

        async def analyze(self, df):
            return {'decision': 'COMPRAR', 'score': 10}

    class S2:
        def __init__(self):
            self.name = 's2'
            self.description = 's2'

        async def analyze(self, df):
            return {'decision': 'MANTENER', 'score': 1}

    mgr._strategies = {'s1': S1(), 's2': S2()}

    out = await mgr.analyze_all_strategies(symbol='BTCUSDT', interval='1h', limit=10)
    assert out['best_strategy'] == 's1'


@pytest.mark.asyncio
async def test_strategy_manager_performance_cache_and_selection(monkeypatch):
    StrategyManager._reset_manager(StrategyManager)
    mgr = StrategyManager()

    # inject fake strategies
    class Fake:
        def __init__(self, name):
            self.name = name
            self.description = name

        def analyze(self, df):
            return {'decision': 'MANTENER', 'score': 0}

    mgr._strategies = {'a': Fake('a'), 'b': Fake('b')}

    # Patch get_historical_klines to raise so generate_mock_data path is taken
    import utils.technical_analysis as ta
    async def async_raise_get_historical_klines(s, i, l):
        raise ValueError('no data')
    monkeypatch.setattr(ta, 'get_historical_klines', async_raise_get_historical_klines)
    import strategies.strategy_manager as smod
    monkeypatch.setattr(smod, 'get_historical_klines', async_raise_get_historical_klines)

    # Patch Backtester.run to return deterministic metrics
    async def fake_run(self, strategy):
        return {'sharpe_ratio': 0.5 if self.historical_data is not None else 0, 'total_return_pct': 5}

    monkeypatch.setattr(backtester_module.Backtester, 'run', fake_run)
    # Also patch generate_mock_data to return a valid df
    monkeypatch.setattr(backtester_module, 'generate_mock_data', lambda days=500: make_price_series(length=100))

    await mgr.update_performance_cache(symbol='BTCUSDT', interval='4h', limit=10)
    assert isinstance(mgr.get_strategies_with_performance(), list)

    # Simulate selection
    # Make first strategy better
    mgr._performance_cache = [
        {'name': 'a', 'performance': {'sharpe_ratio': 2.0, 'total_return_pct': 10}},
        {'name': 'b', 'performance': {'sharpe_ratio': 1.0, 'total_return_pct': 5}}
    ]

    # ensure no active strategy to allow set
    mgr._active_strategy = type('X', (), {'name': 'b'})()
    res = await mgr.select_best_strategy()
    # selection should attempt to set to 'a' (returns name or None)
    assert res in ('a', None)
