#!/usr/bin/env python3
"""
Optimización aleatoria de parámetros para DynamicRegimeStrategy en un periodo dado (por defecto 2025-08, BTCUSDT 1h).

Objetivo: maximizar total_return_pct y encontrar configuraciones que superen +10% mensual.
Guarda resultados en logs/opt_dynamic_regime_<SYMBOL>_<PERIOD>.json
"""

from __future__ import annotations

import os, sys, json, random, logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple

import requests
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from strategies.backtester import Backtester
from strategies.dynamic_regime_strategy import DynamicRegimeStrategy

logger = logging.getLogger("optimize_dynamic_regime")
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
    df = df[["open","high","low","close","volume"]].dropna().sort_index()
    df = df[(df.index >= start) & (df.index <= end)]
    try:
        df.index = df.index.tz_convert(None)  # type: ignore[attr-defined]
    except Exception:
        # Si no es un índice con tz, ignorar
        pass
    return df


def sample_params() -> Dict[str, Any]:
    """Muestrea hiperparámetros en rangos más amplios y continuos para explorar configuraciones agresivas y conservadoras."""
    return {
        # Filtrado de tendencia/regímenes
        "adx_trend_min": round(random.uniform(10.0, 35.0), 1),
        "bb_width_range_max": round(random.uniform(0.015, 0.080), 3),
        # Entradas
        "rsi_oversold": round(random.uniform(20.0, 45.0), 1),
        # Gestión de riesgo y salidas
        "atr_mult_sl": round(random.uniform(0.4, 2.0), 1),
        "atr_mult_tp_trend": round(random.uniform(1.2, 5.0), 1),
        "atr_mult_tp_range": round(random.uniform(1.0, 3.0), 1),
        "atr_trailing_mult": round(random.uniform(0.6, 2.5), 1),
        # Duración máxima del trade
        "max_bars_in_trade": random.choice([24, 36, 48, 60, 72, 96, 120]),
    }


def evaluate_params(df: pd.DataFrame, params: Dict[str, Any], symbol: str, interval: str, initial_balance: float) -> Tuple[float, Dict[str, Any]]:
    import asyncio
    strat = DynamicRegimeStrategy()
    # En optimización, desactivamos el auto-tune para evaluar solo los hiperparámetros muestreados
    try:
        strat.enable_daily_tune = False  # type: ignore[attr-defined]
    except Exception:
        pass
    # Warmup adaptable: al menos 10, máximo 55, proporcional al tamaño del dataset
    n = len(df)
    warmup = max(10, min(55, n // 3 if n else 55))
    # Reducimos el mínimo de barras requeridas para permitir operativa en ventanas cortas
    try:
        strat.min_bars_required = max(10, min(40, warmup))  # type: ignore[attr-defined]
    except Exception:
        pass
    # Aplicar parámetros tras configurar flags
    strat.set_parameters(params)
    bt = Backtester(df.copy(), initial_balance=initial_balance, warmup_period=warmup, symbol=symbol, interval=interval)
    metrics = asyncio.run(bt.run(strat))
    total_return = float(metrics.get("total_return_pct", 0.0))
    # Añadimos algunas métricas extra
    out = {
        "params": params,
        "metrics": {
            "total_return_pct": total_return,
            "max_drawdown_pct": metrics.get("max_drawdown_pct", 0.0),
            "trades": metrics.get("total_trades", 0),
            "win_rate_pct": metrics.get("win_rate_pct", 0.0),
            "final_balance": metrics.get("final_balance", initial_balance),
        }
    }
    return total_return, out


def main():
    symbol = os.getenv("REPORT_SYMBOL", "BTCUSDT").upper()
    interval = os.getenv("REPORT_INTERVAL", "1h")
    period = os.getenv("REPORT_PERIOD", "2025-08")
    trials = int(os.getenv("TRIALS", "120"))
    seed = int(os.getenv("SEED", "1337"))
    initial_balance = float(os.getenv("INITIAL_BALANCE", "1000"))
    random.seed(seed)

    # Soporte de fechas: LOOKBACK_DAYS tiene prioridad, luego START/END, si no se usa PERIOD mensual
    now = datetime.now()
    start_env = os.getenv("START_DATE")  # ISO: YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS
    end_env = os.getenv("END_DATE")
    lookback_days = os.getenv("LOOKBACK_DAYS")

    if lookback_days:
        try:
            days = int(lookback_days)
            end = now
            start = end - timedelta(days=days)
        except Exception:
            # fallback a periodo
            start = datetime.fromisoformat(f"{period}-01T00:00:00")
            end = now
    elif start_env or end_env:
        try:
            start = datetime.fromisoformat((start_env or (now - timedelta(days=7)).strftime('%Y-%m-%d')) + ('' if 'T' in (start_env or '') else 'T00:00:00'))
        except Exception:
            start = now - timedelta(days=7)
        try:
            end = datetime.fromisoformat((end_env or now.strftime('%Y-%m-%d')) + ('' if 'T' in (end_env or '') else 'T23:59:59'))
        except Exception:
            end = now
    else:
        start = datetime.fromisoformat(f"{period}-01T00:00:00")
        end = now
    df = fetch_klines(symbol, interval, start, end)
    if df.empty:
        print(json.dumps({"error": "Sin datos Binance"}, ensure_ascii=False))
        sys.exit(2)

    best: List[Tuple[float, Dict[str, Any]]] = []
    target = 10.0

    for i in range(trials):
        params = sample_params()
        try:
            ret, detail = evaluate_params(df, params, symbol, interval, initial_balance)
        except Exception as e:
            logger.exception(f"Fallo en evaluación de params {params}: {e}")
            continue
        best.append((ret, detail))
        best.sort(key=lambda x: x[0], reverse=True)
        best = best[:10]
        if (i + 1) % 10 == 0:
            logger.info(f"Iter {i+1}/{trials} - Mejor retorno: {best[0][0]:.2f}% (target {target}%)")

    results = {
        "symbol": symbol,
        "interval": interval,
        "period": period,
        "initial_balance": initial_balance,
        "trials": trials,
        "top": [
            {
                "rank": idx + 1,
                **detail,
            } for idx, (ret, detail) in enumerate(best)
        ]
    }

    os.makedirs(os.path.join(ROOT, 'logs'), exist_ok=True)
    out_path = os.path.join(ROOT, 'logs', f'opt_dynamic_regime_{symbol}_{period}.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Log resumen y meta
    top_ret = best[0][0] if best else 0.0
    meets = top_ret >= target
    print(json.dumps({"success": True, "output": out_path, "top_return_pct": top_ret, "meets_target": meets, "results": results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
