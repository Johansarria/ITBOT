import pytest
import pandas as pd
from unittest.mock import patch, AsyncMock
from freezegun import freeze_time


@pytest.mark.asyncio
async def test_daily_pnl_uses_fallback_quantity_and_side_mapping(tmp_path):
    # Arrange: CSV con una operación cerrada hoy y open positions con BUY y sin cantidad explícita
    from utils import risk_manager as rm

    ops_csv = tmp_path / "operaciones.csv"
    ops_df = pd.DataFrame([
        {"timestamp_open": "2025-08-14T09:00:00Z", "timestamp_close": "2025-08-14T10:00:00Z", "pnl_usdt": 5.0}
    ])
    ops_df.to_csv(ops_csv, index=False)

    open_positions = pd.DataFrame([
        {"symbol": "BTCUSDT", "entry_price": 100.0, "size_usdt": 200.0, "side": "BUY"},  # qty fallback = 2.0
        {"symbol": "ETHUSDT", "entry_price": 50.0, "cantidad_token_operada": 4.0, "side": "SHORT"},
    ])

    mock_client = AsyncMock()
    mock_client.get_all_tickers.return_value = [
        {"symbol": "BTCUSDT", "price": "102.0"},  # +2*2 = +4 USDT
        {"symbol": "ETHUSDT", "price": "55.0"},   # SHORT: (50-55)*4 = -20 USDT
    ]
    mock_client.get_asset_balance.return_value = {"free": "1000.0"}

    with patch.object(rm, 'OPERATIONS_LOG', str(ops_csv)), \
         patch.object(rm, 'get_open_positions', return_value=open_positions), \
         patch.object(rm, 'get_binance_client', return_value=mock_client), \
         freeze_time("2025-08-14 12:00:00 UTC"):
        pnl_pct = await rm._get_daily_pnl_pct()

    # Capital = 1000 + size_usdt sum (200 + 0 assumed for ETH due to missing size_usdt -> 0) = 1200
    # Realized = +5, Unrealized = +4 + (-20) = -16, Total = -11 -> -0.9166%
    assert pnl_pct == pytest.approx(-0.9166, abs=1e-3)


@pytest.mark.asyncio
async def test_symbol_limits_block_when_reached():
    from utils.risk_manager import verificar_permiso_de_operacion

    open_positions = pd.DataFrame([
        {"symbol": "BTCUSDT", "size_usdt": 100.0},
        {"symbol": "BTCUSDT", "size_usdt": 150.0},
    ])
    mock_client = AsyncMock()
    mock_client.get_asset_balance.return_value = {"free": "1000.0"}

    with patch('utils.risk_manager.get_open_positions', return_value=open_positions), \
         patch('utils.risk_manager.get_binance_client', return_value=mock_client), \
         patch('utils.risk_manager.settings.RISK_MAX_EXPOSURE_PCT', 90.0), \
         patch('utils.risk_manager._get_daily_pnl_pct', new_callable=AsyncMock, return_value=0.0), \
         patch('utils.risk_manager.StateManager') as mock_sm:

        mock_sm.return_value.get_state.return_value = None

        # Setear params opcionales vía estado de custom params
        def get_state_side_effect(module, key=None, default_value=None):
            if module == 'risk_manager' and key is None:
                return {
                    "custom_params_active": True,
                    "custom_params": {
                        "RISK_MAX_PER_SYMBOL_TRADES": 2,
                        "RISK_MAX_PER_SYMBOL_EXPOSURE_PCT": 30.0,
                    }
                }
            return None

        mock_sm.return_value.get_state.side_effect = get_state_side_effect

        # Ya hay 2 trades en BTC, abrir otro debe bloquear por límite por símbolo
        allowed, reason = await verificar_permiso_de_operacion(new_trade_size_usdt=10.0, symbol='BTCUSDT')
        assert not allowed
        assert 'por símbolo' in reason
