import pytest
import pandas as pd
from unittest.mock import patch

def test_get_parameters():
    """Test that get_parameters returns the default parameters."""
    from strategies.pullback_strategy import PullbackStrategy
    strategy = PullbackStrategy()
    params = strategy.get_parameters()
    assert isinstance(params, dict)
    assert "ma_long_period" in params
    assert params["ma_long_period"] == 50

def test_set_parameters():
    """Test that set_parameters correctly updates the strategy's parameters."""
    from strategies.pullback_strategy import PullbackStrategy
    strategy = PullbackStrategy()

    assert strategy.get_parameters()["ma_long_period"] == 50

    new_params = {"ma_long_period": 100, "unknown_param": 999}
    strategy.set_parameters(new_params)

    updated_params = strategy.get_parameters()
    assert updated_params["ma_long_period"] == 100
    assert "unknown_param" not in updated_params

@pytest.mark.asyncio
async def test_analyze_insufficient_data():
    """Test that analyze returns 'DATOS_INSUFICIENTES' if data is too short."""
    from strategies.pullback_strategy import PullbackStrategy
    strategy = PullbackStrategy()
    data = {'open': range(49), 'high': range(49), 'low': range(49), 'close': range(49), 'volume': range(49)}
    historical_data = pd.DataFrame(data)

    result = await strategy.analyze(historical_data, "BTCUSDT", "1h")

    assert result["decision"] == "DATOS_INSUFICIENTES"

@pytest.mark.asyncio
async def test_analyze_missing_ma_columns():
    """Test that analyze returns 'ERROR_CONFIG_MA' if MA columns are not in the DataFrame."""
    from strategies.pullback_strategy import PullbackStrategy
    strategy = PullbackStrategy()
    historical_data = pd.DataFrame({'close': range(100)})

    with patch('strategies.pullback_strategy.FeaturePipeline') as mock_pipeline:
        mock_pipeline.return_value.transform.return_value = historical_data
        result = await strategy.analyze(historical_data, "BTCUSDT", "1h")
        assert result["decision"] == "ERROR_CONFIG_MA"

@pytest.fixture
def mock_pipeline():
    """Fixture to create a mock FeaturePipeline."""
    with patch('strategies.pullback_strategy.FeaturePipeline') as mock:
        yield mock

def create_test_df(data, length=50):
    """Helper function to create a DataFrame for testing."""
    base_data = {col: [0] * length for col in data.keys()}
    df = pd.DataFrame(base_data)
    for col, values in data.items():
        df.loc[df.index[-len(values):], col] = values
    return df

@pytest.mark.asyncio
async def test_analyze_buy_signal(mock_pipeline):
    """Test a clear BUY signal scenario."""
    from strategies.pullback_strategy import PullbackStrategy
    strategy = PullbackStrategy()

    test_data = create_test_df({
        'open': [98, 99], 'high': [101, 102], 'low': [97, 98], 'close': [100, 101],
        'ma_20': [98, 99], 'ma_50': [95, 96]
    })
    mock_pipeline.return_value.transform.return_value = test_data

    result = await strategy.analyze(pd.DataFrame(), "BTCUSDT", "1h")

    assert result["decision"] == "COMPRAR"
    assert result["score"] == 1

@pytest.mark.asyncio
async def test_analyze_sell_signal(mock_pipeline):
    """Test a clear SELL signal scenario."""
    from strategies.pullback_strategy import PullbackStrategy
    strategy = PullbackStrategy()

    test_data = create_test_df({
        'open': [102, 101], 'high': [103, 102], 'low': [99, 98], 'close': [100, 99],
        'ma_20': [102, 101], 'ma_50': [105, 104]
    })
    mock_pipeline.return_value.transform.return_value = test_data

    result = await strategy.analyze(pd.DataFrame(), "BTCUSDT", "1h")

    assert result["decision"] == "VENDER"
    assert result["score"] == -1

@pytest.mark.asyncio
async def test_analyze_hold_signal_no_pullback(mock_pipeline):
    """Test a HOLD scenario where there is a trend but no pullback."""
    from strategies.pullback_strategy import PullbackStrategy
    strategy = PullbackStrategy()

    test_data = create_test_df({
        'open': [98, 99], 'high': [101, 102], 'low': [99, 100], 'close': [100, 101],
        'ma_20': [98, 99], 'ma_50': [95, 96]
    })
    mock_pipeline.return_value.transform.return_value = test_data

    result = await strategy.analyze(pd.DataFrame(), "BTCUSDT", "1h")

    assert result["decision"] == "MANTENER"

@pytest.mark.asyncio
async def test_analyze_hold_signal_no_confirmation(mock_pipeline):
    """Test a HOLD scenario where there is a pullback but no confirmation candle."""
    from strategies.pullback_strategy import PullbackStrategy
    strategy = PullbackStrategy()

    test_data = create_test_df({
        'open': [98, 102], 'high': [101, 103], 'low': [97, 98], 'close': [100, 101],
        'ma_20': [98, 99], 'ma_50': [95, 96]
    })
    mock_pipeline.return_value.transform.return_value = test_data

    result = await strategy.analyze(pd.DataFrame(), "BTCUSDT", "1h")

    assert result["decision"] == "MANTENER"
