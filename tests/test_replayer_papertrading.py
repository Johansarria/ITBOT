import pytest
import asyncio
import pandas as pd
from unittest.mock import AsyncMock, patch, MagicMock
from historical_replayer import HistoricalReplayer
from utils import order_executor

@pytest.mark.asyncio
async def test_replayer_and_paper_trading(tmp_path, monkeypatch):
    # Crear CSV de ejemplo
    df = pd.DataFrame([
        {"timestamp": "2025-08-12 10:00:00", "open": 100, "close": 105, "symbol": "BTCUSDT"},
        {"timestamp": "2025-08-12 10:01:00", "open": 105, "close": 110, "symbol": "BTCUSDT"},
    ])
    csv_path = tmp_path / "test_ticks.csv"
    df.to_csv(csv_path, index=False)

    # Mock lógica de análisis y ejecución para simular paper trading
    executed = []
    async def fake_evaluar_y_ejecutar_operacion(bot_instance, chat_id, resultado_analisis, take_profit=None, stop_loss=None):
        executed.append(resultado_analisis)
        return "Simulada"

    monkeypatch.setattr(order_executor, "evaluar_y_ejecutar_operacion", fake_evaluar_y_ejecutar_operacion)

    # Simular on_tick que decide operar en cada tick
    async def on_tick(tick):
        resultado_analisis = {
            "symbol": tick["symbol"],
            "decision": "COMPRAR",
            "score": 0.9,
            "strategy_name": "TestStrategy"
        }
        await order_executor.evaluar_y_ejecutar_operacion(None, None, resultado_analisis)

    replayer = HistoricalReplayer(str(csv_path), on_tick, speed=1000)
    await replayer.run()
    assert len(executed) == 2
    assert executed[0]["symbol"] == "BTCUSDT"
    assert executed[1]["decision"] == "COMPRAR"
