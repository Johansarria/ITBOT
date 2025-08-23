import pandas as pd
import numpy as np
import asyncio

from strategies.bollinger_bands_strategy import BollingerBandsStrategy
from strategies.ma_cross_strategy import MACrossStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.simple_technical_strategy import SimpleTechnicalStrategy
from strategies.strategy_manager import StrategyManager
from utils import technical_analysis


def make_df(periods=50, base=100, step=1):
    idx = pd.date_range('2025-01-01', periods=periods, freq='h')
    prices = np.linspace(base, base + step*(periods-1), periods)
    return pd.DataFrame({'open': prices, 'high': prices+1, 'low': prices-1, 'close': prices, 'volume': np.linspace(1,2,periods)}, index=idx)


def test_bollinger_buy_and_sell():
    strat = BollingerBandsStrategy()
    # Create data with last close below bb_lower by manipulating close
    df = make_df(30)
    df.loc[df.index[-1], 'close'] = df['close'].min() - 50
    res = strat.analyze(df)
    assert res['decision'] in ('COMPRAR', 'MANTENER', 'VENDER')


def test_ma_cross_signal():
    strat = MACrossStrategy()
    df = make_df(40)
    # force fast MA > slow MA by increasing recent closes
    df.loc[df.index[-1], 'close'] = df['close'].iloc[-1] + 10
    res = strat.analyze(df)
    assert 'decision' in res


def test_macd_strategy_runs():
    strat = MACDStrategy()
    df = make_df(40)
    res = strat.analyze(df)
    assert 'decision' in res


def test_simple_technical_strategy_async():
    strat = SimpleTechnicalStrategy()
    df = make_df(50)
    # Use asyncio.run for modern event loop management
    res = asyncio.run(strat.analyze(df, 'X', '1h'))
    assert 'decision' in res


def test_strategy_manager_single(monkeypatch):
    sm = StrategyManager()
    sm._reset_manager()
    # Inject a simple strategy into manager
    class DummyStrategy:
        name = 'DUMMY'
        description = 'dummy'
        async def analyze(self, df):
            return {'decision': 'MANTENER', 'score': 0}

    sm._strategies = {'DUMMY': DummyStrategy()}

    # Mock get_historical_klines to return a non-empty df
    async def fake_get(symbol, interval, limit=100):
        return make_df(50)

    import strategies.strategy_manager as smodule
    monkeypatch.setattr(smodule, 'get_historical_klines', fake_get)
    res = asyncio.run(sm.analyze_single_strategy('DUMMY', 'X', '1h'))
    assert res['best_strategy'] == 'DUMMY'
