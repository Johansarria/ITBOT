import pytest
import asyncio
import pandas as pd
from unittest.mock import AsyncMock, patch
from historical_replayer import HistoricalReplayer

@pytest.mark.asyncio
async def test_replayer_runs_through_all_ticks(tmp_path):
    # Crear un CSV de ejemplo
    df = pd.DataFrame([
        {"timestamp": "2025-08-12 10:00:00", "open": 100, "close": 105},
        {"timestamp": "2025-08-12 10:01:00", "open": 105, "close": 110},
        {"timestamp": "2025-08-12 10:02:00", "open": 110, "close": 108},
    ])
    csv_path = tmp_path / "test_ticks.csv"
    df.to_csv(csv_path, index=False)

    ticks = []
    async def on_tick(tick):
        ticks.append(tick)

    replayer = HistoricalReplayer(str(csv_path), on_tick, speed=1000)
    await replayer.run()
    assert len(ticks) == 3
    assert ticks[0]["open"] == 100
    assert ticks[-1]["close"] == 108
