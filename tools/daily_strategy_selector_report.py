#!/usr/bin/env python3
"""
Selector diario de estrategia basado en el rendimiento del día anterior.

Para cada día del periodo (por defecto 2025-08), evalúa TODAS las estrategias con datos del día anterior
 y selecciona la mejor según PnL (empates por win rate y número de trades). Luego ejecuta SOLO la
 estrategia elegida en el día actual y agrega resultados por estrategia a lo largo del mes.

Salida: JSON con
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "period": "2025-08",
  "selection_log": { "YYYY-MM-DD": "StrategyName" },
  "per_strategy": {
     "StrategyName": { "selected_days": n, "pnl_usdt": x, "wins": w, "losses": l, "win_rate_pct": r }
  }
}

Se guarda en logs/daily_selector_report_<SYMBOL>_<PERIOD>.json
"""

from __future__ import annotations

import os
import sys
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple, Type

import pandas as pd

# Asegurar path raíz para imports locales
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from strategies.backtester import Backtester
from strategies.base_strategy import BaseStrategy


logger = logging.getLogger("daily_strategy_selector_report")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_klines_binance(symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Descarga klines desde Binance REST (público) y retorna OHLCV indexado por timestamp (naive)."""
    import requests
    base = "https://api.binance.com/api/v3/klines"
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
    cols = [
        "openTime","open","high","low","close","volume","closeTime",
        "qav","numTrades","takerBase","takerQuote","ignore"
    ]
    df = pd.DataFrame(data, columns=cols)
    df["timestamp"] = pd.to_datetime(df["openTime"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[["open","high","low","close","volume"]].dropna().sort_index()
    df = df[(df.index >= start) & (df.index <= end)]
    df.index = df.index.tz_convert(None)
    return df


def discover_strategy_classes() -> Dict[str, Type[BaseStrategy]]:
    """Descubre clases de estrategias (no instancias)."""
    import importlib
    import pkgutil
    strategies_pkg = "strategies"
    pkg_path = os.path.join(ROOT, strategies_pkg)
    out: Dict[str, Type[BaseStrategy]] = {}
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
                    out[attr.__name__] = attr
            except Exception:
                continue
    return out


def instantiate_strategy(cls: Type[BaseStrategy]) -> BaseStrategy:
    """Intenta instanciar una estrategia con o sin kwargs name/description."""
    try:
        return cls(name=cls.__name__, description=getattr(cls, "__doc__", "") or "")
    except TypeError:
        return cls()


async def run_backtest(historical: pd.DataFrame, strategy: BaseStrategy, symbol: str, interval: str, initial_balance: float, warmup: int) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Ejecuta un backtest y retorna (metrics, trades)."""
    # Ajuste warmup para ML si corresponde
    from config import settings
    try:
        from strategies.ml_strategy import MLStrategy
        if isinstance(strategy, MLStrategy):
            warmup = max(getattr(settings, 'ML_MIN_DATA_POINTS', 50), warmup)
    except Exception:
        pass
    bt = Backtester(historical_data=historical.copy(), initial_balance=initial_balance, warmup_period=warmup, symbol=symbol, interval=interval)
    metrics = await bt.run(strategy)
    return metrics, bt.trades


def slice_day(df: pd.DataFrame, day_start: datetime, day_end: datetime, warmup_hours: int = 24) -> pd.DataFrame:
    """Devuelve un slice con warmup previo (por horas) antes de day_start."""
    start_with_warmup = day_start - timedelta(hours=warmup_hours)
    return df[(df.index >= start_with_warmup) & (df.index <= day_end)].copy()


def aggregate_day_results(trades: List[Dict[str, Any]], day: datetime) -> Tuple[float, int, int, int]:
    """Suma PnL de SELL/SELL_FINAL del día y cuenta wins/losses/total_trades del día."""
    target_date = day.date()
    pnl = 0.0
    wins = 0
    losses = 0
    total = 0
    for t in trades:
        typ = str(t.get("type", "")).upper()
        if not typ.startswith("SELL"):
            continue
        ts = t.get("timestamp")
        if ts is None:
            continue
        try:
            d = (ts.date() if hasattr(ts, 'date') else pd.to_datetime(ts).date())
        except Exception:
            continue
        if d != target_date:
            continue
        p = float(t.get("profit_loss", 0.0))
        pnl += p
        total += 1
        if p > 0:
            wins += 1
        else:
            losses += 1
    return round(pnl, 6), wins, losses, total


def choose_best_strategy(yday_eval: Dict[str, Dict[str, Any]]) -> str:
    """Elige la mejor estrategia del día anterior por PnL, luego win rate, luego trades."""
    # yday_eval: { name: { pnl, wins, losses, total } }
    def key_fn(item):
        name, stats = item
        pnl = stats.get("pnl", 0.0)
        total = stats.get("total", 0)
        wins = stats.get("wins", 0)
        wr = (wins / total) if total > 0 else 0.0
        return (pnl, wr, total, name)
    # max selecciona por mayor pnl, luego mayor wr, luego mayor total, luego nombre
    best_name, _ = max(yday_eval.items(), key=key_fn)
    return best_name


def main():
    import asyncio
    symbol = os.getenv("REPORT_SYMBOL", "BTCUSDT").upper()
    interval = os.getenv("REPORT_INTERVAL", "1h")
    period = os.getenv("REPORT_PERIOD", "2025-08")  # formato YYYY-MM
    initial_balance = float(os.getenv("INITIAL_BALANCE", "1000"))
    warmup_bars = int(os.getenv("WARMUP_BARS", "30"))

    period_start = datetime.fromisoformat(f"{period}-01T00:00:00")
    # Fin de periodo: si es mes actual, usar ahora; si no, fin del mes
    now = datetime.now()
    if now.strftime("%Y-%m") == period:
        period_end = now
    else:
        # obtener último día del mes
        if period.endswith("-12"):
            period_end = datetime.fromisoformat(f"{period.split('-')[0]}-12-31T23:59:59")
        else:
            y, m = period.split("-")
            y = int(y)
            m = int(m)
            next_month = datetime(y + (m // 12), ((m % 12) + 1), 1)
            period_end = next_month - timedelta(seconds=1)

    # Para la primera selección (día 1) necesitamos hasta 2 días previos
    fetch_start = period_start - timedelta(days=2)
    df = fetch_klines_binance(symbol, interval, fetch_start, period_end)
    if df.empty:
        print(json.dumps({"error": "Sin datos de Binance para el rango"}, ensure_ascii=False))
        sys.exit(2)

    strategy_classes = discover_strategy_classes()
    if not strategy_classes:
        print(json.dumps({"error": "No se encontraron estrategias"}, ensure_ascii=False))
        sys.exit(3)
    logger.info(f"Estrategias detectadas: {list(strategy_classes.keys())}")

    # Rango de días del periodo
    days: List[datetime] = []
    cursor = period_start
    # Limitar a medianoche para estabilidad
    end_day = datetime(period_end.year, period_end.month, period_end.day, 23, 59, 59)
    while cursor <= end_day:
        days.append(datetime(cursor.year, cursor.month, cursor.day))
        cursor += timedelta(days=1)

    selection_log: Dict[str, str] = {}
    per_strategy: Dict[str, Dict[str, Any]] = {name: {"selected_days": 0, "pnl_usdt": 0.0, "wins": 0, "losses": 0} for name in strategy_classes.keys()}

    # Event loop para backtests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        for day in days:
            yday = day - timedelta(days=1)
            # Evaluación del día anterior para TODAS las estrategias
            yday_eval: Dict[str, Dict[str, Any]] = {}
            for name, cls in strategy_classes.items():
                strat = instantiate_strategy(cls)
                # ventana: [yday - 1 día, yday 23:59]
                win_start = yday - timedelta(days=1)
                win_end = datetime(yday.year, yday.month, yday.day, 23, 59, 59)
                df_y = slice_day(df, win_start, win_end, warmup_hours=24)
                if len(df_y) < max(10, warmup_bars + 5):
                    yday_eval[name] = {"pnl": 0.0, "wins": 0, "losses": 0, "total": 0}
                    continue
                try:
                    _, trades_y = loop.run_until_complete(run_backtest(df_y, strat, symbol, interval, initial_balance, warmup_bars))
                    pnl_y, wins_y, losses_y, total_y = aggregate_day_results(trades_y, yday)
                except Exception as e:
                    logger.exception(f"Fallo evaluación yday para {name} {yday.date()}: {e}")
                    pnl_y, wins_y, losses_y, total_y = 0.0, 0, 0, 0
                yday_eval[name] = {"pnl": pnl_y, "wins": wins_y, "losses": losses_y, "total": total_y}

            # Elegir mejor estrategia según yday
            best_name = choose_best_strategy(yday_eval)
            selection_log[day.date().isoformat()] = best_name

            # Ejecutar la estrategia elegida en el día actual
            cls = strategy_classes[best_name]
            strat_today = instantiate_strategy(cls)
            win_start_today = day - timedelta(days=1)  # incluir warmup de 24h
            win_end_today = datetime(day.year, day.month, day.day, 23, 59, 59)
            df_t = slice_day(df, win_start_today, win_end_today, warmup_hours=24)
            pnl_t, wins_t, losses_t, _ = 0.0, 0, 0, 0
            if len(df_t) >= max(10, warmup_bars + 5):
                try:
                    _, trades_t = loop.run_until_complete(run_backtest(df_t, strat_today, symbol, interval, initial_balance, warmup_bars))
                    pnl_t, wins_t, losses_t, _ = aggregate_day_results(trades_t, day)
                except Exception as e:
                    logger.exception(f"Fallo ejecución día actual para {best_name} {day.date()}: {e}")

            # Agregar a per_strategy
            ps = per_strategy[best_name]
            ps["selected_days"] += 1
            ps["pnl_usdt"] = round(ps["pnl_usdt"] + pnl_t, 6)
            ps["wins"] += wins_t
            ps["losses"] += losses_t

        # Calcular win_rate por estrategia
        for name, st in per_strategy.items():
            w = st.get("wins", 0)
            l = st.get("losses", 0)
            total = w + l
            st["win_rate_pct"] = round((w / total) * 100.0, 2) if total > 0 else 0.0

    finally:
        try:
            loop.close()
        except Exception:
            pass

    # Salida
    out = {
        "symbol": symbol,
        "interval": interval,
        "period": period,
        "selection_log": selection_log,
        "per_strategy": per_strategy,
    }

    os.makedirs(os.path.join(ROOT, 'logs'), exist_ok=True)
    out_path = os.path.join(ROOT, 'logs', f'daily_selector_report_{symbol}_{period}.json')
    with open(out_path, 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps({"success": True, "output": out_path, "results": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
