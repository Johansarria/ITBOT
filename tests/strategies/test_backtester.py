# tests/strategies/test_backtester.py

import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

# Importar la clase a probar
from strategies.backtester import Backtester
from strategies.base_strategy import BaseStrategy

# Fixture para una estrategia mock
@pytest.fixture
def mock_strategy():
    strategy = AsyncMock(spec=BaseStrategy)
    strategy.name = "MockStrategy"
    return strategy

# Datos de klines de ejemplo para simular
def get_simple_klines(num_rows: int = 100) -> pd.DataFrame:
    timestamps = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(num_rows)]
    close_prices = [100 + i * 0.1 for i in range(num_rows)]
    data = {
        "open": [c - 0.5 for c in close_prices],
        "high": [c + 1 for c in close_prices],
        "low": [c - 1 for c in close_prices],
        "close": close_prices,
        "volume": [100] * num_rows
    }
    df = pd.DataFrame(data, index=pd.to_datetime(timestamps))
    df.index.name = "timestamp"
    return df

# --- Tests para Backtester ---

@pytest.mark.asyncio
async def test_backtester_empty_data(mock_strategy):
    historical_data = pd.DataFrame()
    backtester = Backtester(historical_data)
    results = await backtester.run(mock_strategy)
    assert results == {}

@pytest.mark.asyncio
async def test_backtester_with_signals(mock_strategy):
    historical_data = get_simple_klines(num_rows=110) # Suficientes datos para el warmup y algunas operaciones

    # Configurar el mock de la estrategia para devolver señales específicas
    side_effects = [
        {"decision": "COMPRAR", "score": 0.8},  # i = 100
        {"decision": "MANTENER", "score": 0.1}, # i = 101
        {"decision": "VENDER", "score": -0.8}, # i = 102
        {"decision": "COMPRAR", "score": 0.9},  # i = 103
        {"decision": "MANTENER", "score": 0.2}, # i = 104
        {"decision": "VENDER", "score": -0.9}, # i = 105
        {"decision": "MANTENER", "score": 0.0}, # i = 106
        {"decision": "MANTENER", "score": 0.0}, # i = 107
        {"decision": "MANTENER", "score": 0.0}, # i = 108
        {"decision": "MANTENER", "score": 0.0}, # i = 109
    ]
    async def side_effect_func(*args, **kwargs):
        return side_effects.pop(0)

    mock_strategy.analyze.side_effect = side_effect_func

    backtester = Backtester(historical_data, initial_balance=1000.0, commission=0.001, warmup_period=100)
    results = await backtester.run(mock_strategy)

    assert results["total_trades"] > 0
    assert "total_return_pct" in results
    assert "win_rate_pct" in results
    assert "max_drawdown_pct" in results
    assert "sharpe_ratio" in results

    # Verificar que analyze fue llamado para cada punto de datos después del warmup
    assert mock_strategy.analyze.call_count == 10