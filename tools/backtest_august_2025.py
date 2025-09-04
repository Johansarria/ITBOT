#!/usr/bin/env python3
"""
Backtest rápido en Binance (agosto 2025) para contar operaciones por estrategia.

Uso:
  python3 tools/backtest_august_2025.py [SYMBOL] [INTERVAL]

Por defecto: SYMBOL=BTCUSDT, INTERVAL=1h
"""
import asyncio
import importlib.util
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

import pandas as pd

# Ensure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys
if ROOT not in sys.path:
    sys.path.append(ROOT)

from strategies.base_strategy import BaseStrategy
from strategies.backtester import Backtester
from utils.binance_client import get_binance_client, close_binance_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bt_aug_2025")


async def fetch_klines(symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
    client = await get_binance_client()
    # python-binance acepta timestamps en ms
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    kl = await client.get_historical_klines(
        symbol=symbol,
        interval=interval,
        start_str=start_ms,
        end_str=end_ms,
    )
    if not kl:
        return pd.DataFrame()
    cols = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
        "ignore",
    ]
    df = pd.DataFrame(kl, columns=cols)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    # Guardar CSV opcionalmente
    out_dir = os.path.join(ROOT, "data", "analisis")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"historical_klines_{symbol}_{interval}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv")
    try:
        df.to_csv(out_path)
        logger.info(f"Datos guardados en {out_path} ({len(df)} filas)")
    except Exception:
        pass
    return df


def discover_strategies() -> Dict[str, BaseStrategy]:
    strategies: Dict[str, BaseStrategy] = {}
    strat_dir = os.path.join(ROOT, "strategies")
    for filename in os.listdir(strat_dir):
        if not filename.endswith('.py'):
            continue
        if filename in {"__init__.py", "base_strategy.py", "strategy_manager.py", "backtester.py"}:
            continue
        mod_name = filename[:-3]
        file_path = os.path.join(strat_dir, filename)
        try:
            spec = importlib.util.spec_from_file_location(mod_name, file_path)
            if not spec or not spec.loader:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                try:
                    if isinstance(attr, type) and issubclass(attr, BaseStrategy) and attr is not BaseStrategy:
                        try:
                            inst = attr(name=attr.__name__, description=getattr(attr, "__doc__", "") or "")
                        except TypeError:
                            inst = attr()
                        name = getattr(inst, 'name', None) or attr.__name__
                        strategies[name] = inst
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"No se pudo cargar estrategia desde {filename}: {e}")
    return strategies


async def run_backtests(df: pd.DataFrame, symbol: str, interval: str) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    strategies = discover_strategies()
    if not strategies:
        logger.error("No se encontraron estrategias para backtestear.")
        return results

    for name, strat in strategies.items():
        try:
            bt = Backtester(historical_data=df.copy(), initial_balance=10_000.0, warmup_period=50, symbol=symbol, interval=interval)
            metrics = await bt.run(strat)
            results.append({
                "strategy": name,
                "total_trades": metrics.get("total_trades", 0) if isinstance(metrics, dict) else 0,
                "win_rate_pct": metrics.get("win_rate_pct") if isinstance(metrics, dict) else None,
                "sharpe_ratio": metrics.get("sharpe_ratio") if isinstance(metrics, dict) else None,
            })
        except Exception as e:
            logger.warning(f"Backtest falló para {name}: {e}")
            results.append({"strategy": name, "error": str(e), "total_trades": 0})
    return results


async def main(symbol: str = "BTCUSDT", interval: str = "1h"):
    # Rango de agosto 2025 en UTC
    start = datetime(2025, 8, 1)
    end = datetime(2025, 9, 1)
    df = await fetch_klines(symbol, interval, start, end)
    if df.empty:
        print(json.dumps({"error": "Sin datos de Binance para el rango"}, ensure_ascii=False))
        return
    results = await run_backtests(df, symbol, interval)
    print(json.dumps({
        "symbol": symbol,
        "interval": interval,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "strategies": results,
    }, ensure_ascii=False))
    await close_binance_client()


if __name__ == "__main__":
    import sys as _sys
    sym = _sys.argv[1] if len(_sys.argv) > 1 else "BTCUSDT"
    itv = _sys.argv[2] if len(_sys.argv) > 2 else "1h"
    asyncio.run(main(sym, itv))
