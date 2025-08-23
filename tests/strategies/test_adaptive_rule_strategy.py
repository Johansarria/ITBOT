
import pytest
import pandas as pd
from strategies.adaptive_rule_strategy import AdaptiveRuleStrategy

@pytest.fixture
def sample_data():
    # Proporciona datos de ejemplo para las pruebas
    data = {
        'bullish_cross': [0, 1, 0, 0, 0],
        'bearish_cross': [0, 0, 1, 0, 0],
        'rsi_14': [50, 60, 40, 80, 20],
        'volatility_20': [0.02, 0.02, 0.04, 0.04, 0.01],
        'cum_return': [1.0, 1.01, 0.9, 0.95, 1.02],
        'returns': [0.0, 0.01, -0.11, 0.05, 0.07]
    }
    return pd.DataFrame(data)

@pytest.mark.asyncio
async def test_strategy_buy_decision(sample_data):
    strategy = AdaptiveRuleStrategy()
    # Seleccionar una fila que cumpla las condiciones de compra
    df_buy = sample_data.iloc[[1]]
    result = await strategy.analyze(df_buy)
    assert result['decision'] == 'COMPRAR'
    assert result['score'] == 1

@pytest.mark.asyncio
async def test_strategy_sell_decision(sample_data):
    strategy = AdaptiveRuleStrategy()
    # Seleccionar una fila que cumpla las condiciones de venta
    df_sell = sample_data.iloc[[2]]
    result = await strategy.analyze(df_sell)
    assert result['decision'] == 'VENDER'
    assert result['score'] == -1

@pytest.mark.asyncio
async def test_strategy_hold_decision(sample_data):
    strategy = AdaptiveRuleStrategy()
    # Seleccionar una fila que no cumpla ninguna condición
    df_hold = sample_data.iloc[[0]]
    result = await strategy.analyze(df_hold)
    assert result['decision'] == 'MANTENER'
    assert result['score'] == 0

@pytest.mark.asyncio
async def test_strategy_reduce_position_on_drawdown(sample_data):
    strategy = AdaptiveRuleStrategy()
    strategy.drawdown_limit = 0.05 # Bajar el límite para que se active
    # Modificar cum_return para simular un drawdown
    data = sample_data.copy()
    data['cum_return'] = [1.0, 1.01, 0.90, 0.85, 0.82]
    df_drawdown = pd.DataFrame(data)
    
    result = await strategy.analyze(df_drawdown)
    assert result['decision'] == 'REDUCIR_POSICION'
    assert result['score'] == -0.5

@pytest.mark.asyncio
async def test_adaptive_threshold_increase():
    strategy = AdaptiveRuleStrategy()
    initial_threshold = strategy.volatility_threshold
    # Asegurarse de que el retorno promedio sea positivo
    data = {
        'bullish_cross': [0] * strategy.performance_window,
        'bearish_cross': [0] * strategy.performance_window,
        'rsi_14': [50] * strategy.performance_window,
        'volatility_20': [0.02] * strategy.performance_window,
        'cum_return': [1.0] * strategy.performance_window,
        'returns': [0.01] * strategy.performance_window
    }
    df_positive_returns = pd.DataFrame(data)
    
    await strategy.analyze(df_positive_returns)
    assert strategy.volatility_threshold > initial_threshold

@pytest.mark.asyncio
async def test_adaptive_threshold_decrease():
    strategy = AdaptiveRuleStrategy()
    initial_threshold = strategy.volatility_threshold
    # Asegurarse de que el retorno promedio sea negativo
    data = {
        'bullish_cross': [0] * strategy.performance_window,
        'bearish_cross': [0] * strategy.performance_window,
        'rsi_14': [50] * strategy.performance_window,
        'volatility_20': [0.02] * strategy.performance_window,
        'cum_return': [1.0] * strategy.performance_window,
        'returns': [-0.01] * strategy.performance_window
    }
    df_negative_returns = pd.DataFrame(data)
    
    await strategy.analyze(df_negative_returns)
    assert strategy.volatility_threshold < initial_threshold

def test_get_parameters():
    strategy = AdaptiveRuleStrategy()
    params = strategy.get_parameters()
    assert isinstance(params, dict)
    assert 'rsi_overbought' in params
    assert params['volatility_threshold'] == 0.03

def test_set_parameters():
    strategy = AdaptiveRuleStrategy()
    new_params = {
        'rsi_overbought': 80,
        'volatility_threshold': 0.05,
        'non_existent_param': 123
    }
    strategy.set_parameters(new_params)
    assert strategy.rsi_overbought == 80
    assert strategy.volatility_threshold == 0.05
    assert not hasattr(strategy, 'non_existent_param')
