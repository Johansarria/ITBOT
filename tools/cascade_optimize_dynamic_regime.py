#!/usr/bin/env python3
"""
Optimización en cascada para DynamicRegimeStrategy:
 - Etapa 1: Diario (lookback 1 día), objetivo ≥0.9%.
 - Etapa 2: Semanal (7 días), objetivo ≥3%.
 - Etapa 3: Mensual (30 días), objetivo ≥10%.

En cada etapa se realiza una búsqueda aleatoria de hiperparámetros y se avanza
solo si se supera el objetivo. Se registra un reporte JSON por etapa y un
resumen final en logs/cascade_opt_dynamic_regime_<SYMBOL>_<YYYYMMDD>.json
"""
from __future__ import annotations

import os, sys, json, random, logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Reutilizamos utilidades del optimizador simple
from tools.optimize_dynamic_regime import (
    fetch_klines,
    sample_params,
    evaluate_params,
)

logger = logging.getLogger("cascade_optimize_dynamic_regime")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def optimize_window(
    symbol: str,
    interval: str,
    lookback_days: int,
    trials: int,
    initial_balance: float,
    seed: int,
) -> Dict[str, Any]:
    """Optimiza en la ventana dada, añadiendo padding para features y cambiando de intervalo si faltan velas."""
    random.seed(seed)
    end = datetime.now(timezone.utc)
    # Padding de días para indicadores en ventanas cortas
    pad_days = 3 if lookback_days <= 2 else (1 if lookback_days <= 7 else 0)
    # Umbral mínimo de velas para que ADX/MA20/50 funcionen
    min_bars = 80 if lookback_days <= 2 else 60

    # Interválicos candidatos si no alcanzamos min_bars
    if interval == "1h":
        interval_candidates = ["1h", "30m", "15m", "5m"]
    elif interval == "30m":
        interval_candidates = ["30m", "15m", "5m"]
    else:
        interval_candidates = [interval]

    chosen_interval = None
    df = pd.DataFrame()
    for itv in interval_candidates:
        start = end - timedelta(days=lookback_days + pad_days)
        df_try = fetch_klines(symbol, itv, start, end)
        if len(df_try) >= min_bars:
            df = df_try
            chosen_interval = itv
            break
    if df.empty:
        # Último intento sin pad por si excede límites
        start = end - timedelta(days=lookback_days)
        df = fetch_klines(symbol, interval, start, end)
        chosen_interval = interval if not df.empty else None
    if df.empty:
        return {"error": f"Sin datos Binance para {symbol} {interval} últimos {lookback_days} días"}

    best: List[Tuple[float, Dict[str, Any]]] = []
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
        if (i + 1) % max(10, trials // 6) == 0:
            logger.info(f"LB={lookback_days}d {chosen_interval or interval} Iter {i+1}/{trials} - Mejor retorno: {best[0][0]:.2f}%")

    results = {
        "symbol": symbol,
    "interval": chosen_interval or interval,
        "lookback_days": lookback_days,
        "trials": trials,
        "top": [
            {"rank": idx + 1, **detail} for idx, (ret, detail) in enumerate(best)
        ]
    }
    results["top_return_pct"] = best[0][0] if best else 0.0
    results["best"] = best[0][1] if best else None
    return results


def main():
    symbol = os.getenv("REPORT_SYMBOL", "BTCUSDT").upper()
    interval = os.getenv("REPORT_INTERVAL", "1h")
    initial_balance = float(os.getenv("INITIAL_BALANCE", "1000"))
    seed = int(os.getenv("SEED", "1337"))

    # Trials por etapa (pueden ajustarse por env)
    trials_daily = int(os.getenv("TRIALS_DAILY", "120"))
    trials_weekly = int(os.getenv("TRIALS_WEEKLY", "180"))
    trials_monthly = int(os.getenv("TRIALS_MONTHLY", "240"))

    # Umbrales objetivo
    target_daily = float(os.getenv("TARGET_DAILY_PCT", "0.9"))
    target_weekly = float(os.getenv("TARGET_WEEKLY_PCT", "3.0"))
    target_monthly = float(os.getenv("TARGET_MONTHLY_PCT", "20.0"))

    stages = [
        {"name": "daily", "lookback_days": 1, "trials": trials_daily, "target": target_daily},
        {"name": "weekly", "lookback_days": 7, "trials": trials_weekly, "target": target_weekly},
        {"name": "monthly", "lookback_days": 30, "trials": trials_monthly, "target": target_monthly},
    ]

    summary = {"symbol": symbol, "interval": interval, "initial_balance": initial_balance, "stages": []}
    proceed = True
    for st in stages:
        if not proceed:
            break
        name = st["name"]
        logger.info(f"Iniciando etapa: {name} (LB={st['lookback_days']}d, trials={st['trials']}, target={st['target']}%)")
        res = optimize_window(symbol, interval, st["lookback_days"], st["trials"], initial_balance, seed)
        stage_out = {"stage": name, **res}
        meets = res.get("top_return_pct", 0.0) >= st["target"]
        stage_out["meets_target"] = meets
        summary["stages"].append(stage_out)
        if meets:
            logger.info(f"Potencial encontrado en {name}: {res.get('top_return_pct', 0.0):.2f}% >= {st['target']}% → avanzando…")
            proceed = True
        else:
            logger.info(f"Sin potencial suficiente en {name}: {res.get('top_return_pct', 0.0):.2f}% < {st['target']}% → deteniendo cascada.")
            proceed = False

    os.makedirs(os.path.join(ROOT, 'logs'), exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d')
    out_path = os.path.join(ROOT, 'logs', f'cascade_opt_dynamic_regime_{symbol}_{ts}.json')
    with open(out_path, 'w') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    final = {
        "success": True,
        "output": out_path,
        "stages": [
            {
                "stage": s["stage"],
                "lookback_days": s.get("lookback_days"),
                "top_return_pct": s.get("top_return_pct", 0.0),
                "meets_target": s.get("meets_target", False),
            }
            for s in summary["stages"]
        ]
    }
    print(json.dumps(final, ensure_ascii=False))


if __name__ == "__main__":
    main()
