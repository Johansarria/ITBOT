#!/usr/bin/env python3
"""
Evalúa DynamicRegimeStrategy en agosto 2025 (BTCUSDT 1h) y reporta métricas:
- Ratio beneficio/riesgo esperado
- Frecuencia y duración promedio de operaciones
- Máxima caída (drawdown)
- Porcentaje de operaciones ganadoras vs perdedoras

Guarda JSON en logs/eval_dynamic_strategy_BTCUSDT_2025-08.json
"""

from __future__ import annotations

import os, sys, json, logging
from datetime import datetime, timezone
from typing import Dict, Any, List

import requests
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from strategies.backtester import Backtester
from strategies.dynamic_regime_strategy import DynamicRegimeStrategy

logger = logging.getLogger("evaluate_dynamic_strategy")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_klines(symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
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
    df = df[["open","high","low","close","volume"]].dropna()
    df = df.sort_index()
    df = df[(df.index >= start) & (df.index <= end)]
    df.index = df.index.tz_convert(None)
    return df


def compute_trade_durations(trades: List[Dict[str, Any]]) -> List[int]:
    # Calcula duración en barras entre BUY y SELL/SELL_FINAL
    durations = []
    last_buy_idx = None
    for t in trades:
        typ = str(t.get("type", ""))
        if typ == "BUY":
            last_buy_idx = t.get("timestamp")
        elif typ.startswith("SELL") and last_buy_idx is not None:
            sell_ts = t.get("timestamp")
            if hasattr(sell_ts, 'to_pydatetime'):
                sell_ts = sell_ts.to_pydatetime()
            if hasattr(last_buy_idx, 'to_pydatetime'):
                buy_ts = last_buy_idx.to_pydatetime()
            else:
                buy_ts = last_buy_idx
            # diferencia en horas
            delta_h = int(round((sell_ts - buy_ts).total_seconds() / 3600))
            durations.append(max(1, delta_h))
            last_buy_idx = None
    return durations


def compute_expected_rr(trades: List[Dict[str, Any]]) -> float:
    # Estimación simple: media de ganancia positiva / media de pérdida absoluta
    profits = [float(t["profit_loss"]) for t in trades if t.get("type", "").startswith("SELL") and t.get("profit_loss") is not None and float(t["profit_loss"]) > 0]
    losses = [-float(t["profit_loss"]) for t in trades if t.get("type", "").startswith("SELL") and t.get("profit_loss") is not None and float(t["profit_loss"]) < 0]
    if not profits or not losses:
        return 0.0
    return round((sum(profits) / len(profits)) / (sum(losses) / len(losses)), 3)


def main():
    import asyncio
    symbol = os.getenv("REPORT_SYMBOL", "BTCUSDT").upper()
    interval = os.getenv("REPORT_INTERVAL", "1h")
    start_dt = datetime.fromisoformat(os.getenv("REPORT_START", "2025-08-01T00:00:00"))
    end_dt = datetime.now()

    df = fetch_klines(symbol, interval, start_dt, end_dt)
    if df.empty:
        print(json.dumps({"error": "Sin datos Binance"}, ensure_ascii=False))
        sys.exit(2)

    strat = DynamicRegimeStrategy()
    initial_balance = float(os.getenv("INITIAL_BALANCE", "10000"))
    bt = Backtester(df.copy(), initial_balance=initial_balance, warmup_period=55, symbol=symbol, interval=interval)
    metrics = asyncio.run(bt.run(strat))

    # Métricas solicitadas
    sells = [t for t in bt.trades if str(t.get("type", "")).startswith("SELL") and "profit_loss" in t]
    wins = len([t for t in sells if float(t.get("profit_loss", 0)) > 0])
    losses = len([t for t in sells if float(t.get("profit_loss", 0)) <= 0])
    win_rate = round((wins / (wins + losses)) * 100.0, 2) if (wins + losses) > 0 else 0.0
    max_dd = metrics.get("max_drawdown_pct", 0.0)
    rr = compute_expected_rr(bt.trades)
    durations = compute_trade_durations(bt.trades)
    avg_duration_h = round(sum(durations) / len(durations), 2) if durations else 0.0
    trade_freq = len(sells)

    result = {
        "symbol": symbol,
        "interval": interval,
        "period": "2025-08",
        "strategy": strat.name,
        "metrics": {
            "expected_rr": rr,
            "win_rate_pct": win_rate,
            "max_drawdown_pct": max_dd,
            "trades": trade_freq,
            "avg_trade_duration_hours": avg_duration_h,
        "final_balance": metrics.get("final_balance"),
        "total_return_pct": metrics.get("total_return_pct"),
        "initial_balance": initial_balance,
        }
    }

    os.makedirs(os.path.join(ROOT, 'logs'), exist_ok=True)
    out_path = os.path.join(ROOT, 'logs', f'eval_dynamic_strategy_{symbol}_2025-08.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(json.dumps({"success": True, "output": out_path, "report": result}, ensure_ascii=False))


if __name__ == "__main__":
    main()
