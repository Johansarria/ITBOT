#!/usr/bin/env python3
"""
Genera un reporte de cuántas operaciones hubiera hecho cada estrategia por día
entre un rango de fechas (por defecto 2025-08-01 a hoy) usando klines 1h de Binance.

Salida: imprime JSON con { estrategia: { 'YYYY-MM-DD': total_ops } } y guarda en logs/.
"""

from __future__ import annotations

import os
import sys
import json
import time
import math
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

import requests
import pandas as pd

# Asegurar path raíz para imports locales
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from strategies.backtester import Backtester
from strategies.base_strategy import BaseStrategy


logger = logging.getLogger("monthly_backtest_report")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_klines_binance(symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Descarga klines desde el endpoint público de Binance REST.

    Args:
        symbol: Par ej. 'BTCUSDT'
        interval: '1h', '4h', etc.
        start: datetime (naive o UTC)
        end: datetime (naive o UTC)
    Returns:
        DataFrame con index timestamp y columnas: open, high, low, close, volume
    """
    base = "https://api.binance.com/api/v3/klines"
    # Asegurar UTC ms
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000),
        "limit": 1000,
    }
    logger.info(f"Descargando klines de Binance: {symbol} {interval} {start.isoformat()} -> {end.isoformat()}")
    r = requests.get(base, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or not data:
        return pd.DataFrame()
    # Columnas según API: [openTime, open, high, low, close, volume, closeTime, ...]
    cols = [
        "openTime","open","high","low","close","volume","closeTime",
        "qav","numTrades","takerBase","takerQuote","ignore"
    ]
    df = pd.DataFrame(data, columns=cols)
    df["timestamp"] = pd.to_datetime(df["openTime"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[["open","high","low","close","volume"]].dropna()
    # Orden y filtro exacto por fechas
    df = df.sort_index()
    df = df[(df.index >= start) & (df.index <= end)]
    # Normalizar a naive para compat
    df.index = df.index.tz_convert(None)
    return df


def discover_strategies() -> Dict[str, BaseStrategy]:
    """Descubre e instancia estrategias del paquete strategies/.
    Retorna dict nombre->instancia.
    """
    import importlib
    import pkgutil
    import inspect
    strategies_pkg = "strategies"
    pkg_path = os.path.join(ROOT, strategies_pkg)
    out: Dict[str, BaseStrategy] = {}
    for _, modname, ispkg in pkgutil.iter_modules([pkg_path]):
        if ispkg:
            continue
        if modname in {"__init__", "base_strategy", "strategy_manager", "backtester"}:
            continue
        try:
            module = importlib.import_module(f"{strategies_pkg}.{modname}")
        except Exception:
            continue
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            try:
                if isinstance(attr, type) and issubclass(attr, BaseStrategy) and attr is not BaseStrategy:
                    try:
                        inst = attr(name=attr.__name__, description=getattr(attr, "__doc__", "") or "")
                    except TypeError:
                        inst = attr()
                    name = getattr(inst, 'name', None) or attr.__name__
                    out[name] = inst
            except Exception:
                continue
    return out


async def run_backtest_for_strategy(historical: pd.DataFrame, strategy: BaseStrategy, symbol: str, interval: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Ejecuta Backtester para una estrategia y retorna (metrics, trades_raw)."""
    from config import settings
    warmup = 50
    # Ajuste ML si corresponde
    try:
        from strategies.ml_strategy import MLStrategy
        if isinstance(strategy, MLStrategy):
            warmup = max(getattr(settings, 'ML_MIN_DATA_POINTS', 50), 50)
    except Exception:
        pass
    bt = Backtester(historical_data=historical.copy(), initial_balance=10000.0, warmup_period=warmup, symbol=symbol, interval=interval)
    metrics = await bt.run(strategy)
    return metrics, bt.trades


def aggregate_daily_ops(trades: List[Dict[str, Any]]) -> Dict[str, int]:
    """Agrupa por día contando eventos BUY/SELL/SELL_FINAL como operaciones."""
    from collections import defaultdict
    counts: Dict[str, int] = defaultdict(int)
    for t in trades:
        ts = t.get("timestamp")
        if ts is None:
            continue
        # timestamp puede ser pandas.Timestamp o str
        if hasattr(ts, 'date'):
            day = ts.date().isoformat()
        else:
            try:
                day = pd.to_datetime(ts).date().isoformat()
            except Exception:
                continue
        typ = str(t.get("type", "")).upper()
        if typ in ("BUY", "SELL", "SELL_FINAL"):
            counts[day] += 1
    return dict(sorted(counts.items()))


def aggregate_daily_performance(trades: List[Dict[str, Any]]) -> Tuple[Dict[str, float], Dict[str, float], float, int, int, float]:
    """Calcula PnL diario y win rate diario a partir de eventos de venta.

    Considera tipos SELL y SELL_FINAL, utilizando la clave 'profit_loss' (USDT).

    Returns:
        daily_pnl: {YYYY-MM-DD: pnl_usdt}
        daily_win_rate_pct: {YYYY-MM-DD: pct}
        total_pnl: suma pnl_usdt
        wins: total operaciones ganadoras
        losses: total operaciones perdedoras
        overall_win_rate_pct: porcentaje global
    """
    from collections import defaultdict
    daily_pnl: Dict[str, float] = defaultdict(float)
    daily_wins: Dict[str, int] = defaultdict(int)
    daily_losses: Dict[str, int] = defaultdict(int)
    total_pnl = 0.0
    wins = 0
    losses = 0

    for t in trades:
        typ = str(t.get("type", "")).upper()
        if not typ.startswith("SELL"):
            continue
        if "profit_loss" not in t:
            continue
        ts = t.get("timestamp")
        if ts is None:
            continue
        if hasattr(ts, 'date'):
            day = ts.date().isoformat()
        else:
            try:
                day = pd.to_datetime(ts).date().isoformat()
            except Exception:
                continue
        pnl = float(t.get("profit_loss", 0.0))
        daily_pnl[day] += pnl
        total_pnl += pnl
        if pnl > 0:
            daily_wins[day] += 1
            wins += 1
        else:
            daily_losses[day] += 1
            losses += 1

    # Calcular win rate por día
    daily_win_rate: Dict[str, float] = {}
    for day in set(list(daily_wins.keys()) + list(daily_losses.keys())):
        w = daily_wins.get(day, 0)
        l = daily_losses.get(day, 0)
        total = w + l
        daily_win_rate[day] = round((w / total) * 100.0, 2) if total > 0 else 0.0

    overall_win_rate = round((wins / (wins + losses)) * 100.0, 2) if (wins + losses) > 0 else 0.0

    # Ordenar por fecha
    daily_pnl_sorted = dict(sorted(daily_pnl.items()))
    daily_win_rate_sorted = dict(sorted(daily_win_rate.items()))

    return daily_pnl_sorted, daily_win_rate_sorted, round(total_pnl, 4), wins, losses, overall_win_rate


def main():
    import asyncio
    symbol = os.getenv("REPORT_SYMBOL", "BTCUSDT").upper()
    interval = os.getenv("REPORT_INTERVAL", "1h")
    start_str = os.getenv("REPORT_START", "2025-08-01T00:00:00")
    end_dt = datetime.now()
    try:
        end_str_env = os.getenv("REPORT_END")
        if end_str_env:
            end_dt = datetime.fromisoformat(end_str_env)
    except Exception:
        pass

    start_dt = datetime.fromisoformat(start_str)
    df = fetch_klines_binance(symbol, interval, start_dt, end_dt)
    if df.empty:
        print(json.dumps({"error": "Sin datos de Binance para el rango"}, ensure_ascii=False))
        sys.exit(2)

    strategies = discover_strategies()
    if not strategies:
        print(json.dumps({"error": "No se encontraron estrategias"}, ensure_ascii=False))
        sys.exit(3)

    logger.info(f"Estrategias detectadas: {list(strategies.keys())}")

    results: Dict[str, Dict[str, Any]] = {}
    # Ejecutar secuencialmente para simplicidad/estabilidad
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        for name, strat in strategies.items():
            logger.info(f"Backtesting {name}...")
            try:
                metrics, trades = loop.run_until_complete(run_backtest_for_strategy(df, strat, symbol, interval))
                daily_ops = aggregate_daily_ops(trades)
                daily_pnl, daily_wr, total_pnl, wins, losses, overall_wr = aggregate_daily_performance(trades)
                results[name] = {
                    "total_trades": int(metrics.get("total_trades", 0)),
                    "total_pnl_usdt": total_pnl,
                    "wins": wins,
                    "losses": losses,
                    "overall_win_rate_pct": overall_wr,
                    "daily_ops": daily_ops,
                    "daily_pnl_usdt": daily_pnl,
                    "daily_win_rate_pct": daily_wr,
                }
            except Exception as e:
                logger.exception(f"Fallo backtest {name}: {e}")
                results[name] = {"error": str(e)}
    finally:
        try:
            loop.close()
        except Exception:
            pass

    # Guardar en logs
    os.makedirs(os.path.join(ROOT, 'logs'), exist_ok=True)
    out_path = os.path.join(ROOT, 'logs', f'monthly_backtest_{symbol}_2025-08.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(json.dumps({"success": True, "symbol": symbol, "interval": interval, "output": out_path, "results": results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
