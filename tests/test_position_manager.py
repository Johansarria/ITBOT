import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import utils.position_manager as pm



from utils.binance_client import get_binance_client

def test_get_open_positions_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "OPERATIONS_LOG", str(tmp_path / "ops.csv"))
    # No archivo creado
    df = pm.get_open_positions()
    assert df.empty

def test_get_open_positions_with_data(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "OPERATIONS_LOG", str(tmp_path / "ops.csv"))
    df = pd.DataFrame([
        {"symbol": "BTCUSDT", "timestamp_close": None, "operation_id": "1"},
        {"symbol": "ETHUSDT", "timestamp_close": "2025-08-12T10:00:00", "operation_id": "2"}
    ])
    df.to_csv(tmp_path / "ops.csv", index=False)
    result = pm.get_open_positions()
    assert len(result) == 1
    assert result.iloc[0]["symbol"] == "BTCUSDT"

def test_get_open_positions_summary_no_positions(monkeypatch):
    monkeypatch.setattr(pm, "get_open_positions", lambda: pd.DataFrame())
    summary = pm.get_open_positions_summary(MagicMock())
    assert "No hay posiciones abiertas" in summary

def test_get_open_positions_summary_with_positions(monkeypatch):
    # Simula una posición abierta
    df = pd.DataFrame([
        {"symbol": "BTCUSDT", "entry_price": 100, "size_usdt": 50, "timestamp_open": "2025-08-12T10:00:00"}
    ])
    monkeypatch.setattr(pm, "get_open_positions", lambda: df)
    
    # Mockear get_binance_client y la instancia del cliente
    mock_client_instance = MagicMock()
    mock_client_instance.get_symbol_ticker.return_value = {"price": "110"}
    
    with patch('utils.position_manager.get_binance_client', return_value=mock_client_instance) as mock_get_client:
        summary = pm.get_open_positions_summary(MagicMock())
        assert "BTCUSDT" in summary
        assert "+10.00%" in summary
        mock_get_client.assert_called_once()
        mock_client_instance.get_symbol_ticker.assert_called_once_with(symbol="BTCUSDT")
