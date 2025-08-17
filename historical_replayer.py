import pandas as pd
import asyncio
import logging
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger("historical_replayer")

class HistoricalReplayer:
    def __init__(self, csv_path: str, on_tick: Callable[[dict], None],
                 datetime_col: str = "timestamp",
                 speed: float = 1.0,
                 start: Optional[str] = None,
                 end: Optional[str] = None):
        self.csv_path = csv_path
        self.on_tick = on_tick
        self.datetime_col = datetime_col
        self.speed = speed
        self.start = pd.to_datetime(start) if start else None
        self.end = pd.to_datetime(end) if end else None
        self.df = pd.read_csv(csv_path)
        self.df[self.datetime_col] = pd.to_datetime(self.df[self.datetime_col])
        if self.start:
            self.df = self.df[self.df[self.datetime_col] >= self.start]
        if self.end:
            self.df = self.df[self.df[self.datetime_col] <= self.end]
        self.df = self.df.sort_values(self.datetime_col)

    async def run(self):
        logger.info(f"Iniciando replayer sobre {len(self.df)} ticks...")
        prev_time = None
        for _, row in self.df.iterrows():
            tick = row.to_dict()
            now = tick[self.datetime_col]
            if prev_time is not None:
                delay = (now - prev_time).total_seconds() / self.speed
                if delay > 0:
                    await asyncio.sleep(delay)
            await self.on_tick(tick)
            prev_time = now
        logger.info("Replayer finalizado.")
