#!/usr/bin/env python3
"""
Optimización multi-timeframe: probando diferentes intervalos para encontrar 
el que mejor se adapte a generar 20%+ mensual.
"""
import json
import logging
import random
import sys
import warnings
import requests
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone

import pandas as pd

# Configuración de warnings
warnings.filterwarnings("ignore", category=FutureWarning, module='pandas')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from strategies.aggressive_regime_strategy import AggressiveRegimeStrategy
from strategies.backtester import Backtester
from utils.feature_pipeline import FeaturePipeline

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_klines(symbol: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
    """Obtener datos históricos de Binance."""
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
        pass
    return df


def get_optimized_params_for_timeframe(timeframe: str) -> Dict[str, Any]:
    """Parámetros optimizados específicos para cada timeframe."""
    
    # Configuraciones agresivas por timeframe
    configs = {
        "15m": {
            # Más activo para capturar movimientos cortos
            "adx_trend_min": random.uniform(12.0, 25.0),
            "bb_width_range_max": random.uniform(0.02, 0.08),
            "rsi_oversold": random.uniform(30.0, 45.0),
            "atr_mult_sl": random.uniform(1.8, 3.5),
            "atr_mult_tp_trend": random.uniform(4.0, 8.0),  # TP moderado
            "atr_mult_tp_range": random.uniform(3.0, 6.0),
            "atr_trailing_mult": random.uniform(2.0, 3.5),
            "max_bars_in_trade": random.randint(48, 192),  # 12-48 horas
            "min_bars_required": random.randint(20, 35)
        },
        "1h": {
            # Balance entre actividad y tendencia
            "adx_trend_min": random.uniform(10.0, 30.0),
            "bb_width_range_max": random.uniform(0.03, 0.12),
            "rsi_oversold": random.uniform(35.0, 50.0),
            "atr_mult_sl": random.uniform(2.0, 4.0),
            "atr_mult_tp_trend": random.uniform(5.0, 12.0),  # TP alto
            "atr_mult_tp_range": random.uniform(3.5, 8.0),
            "atr_trailing_mult": random.uniform(2.5, 4.0),
            "max_bars_in_trade": random.randint(72, 336),  # 3-14 días
            "min_bars_required": random.randint(25, 45)
        },
        "4h": {
            # Para trends más largos - MUY AGRESIVO
            "adx_trend_min": random.uniform(8.0, 25.0),
            "bb_width_range_max": random.uniform(0.04, 0.15),
            "rsi_oversold": random.uniform(40.0, 55.0),
            "atr_mult_sl": random.uniform(2.5, 5.0),  # SL muy amplio
            "atr_mult_tp_trend": random.uniform(8.0, 20.0),  # TP MUY ALTO
            "atr_mult_tp_range": random.uniform(5.0, 12.0),
            "atr_trailing_mult": random.uniform(3.0, 6.0),
            "max_bars_in_trade": random.randint(36, 168),  # 6-28 días
            "min_bars_required": random.randint(15, 30)
        },
        "1d": {
            # Para trends de largo plazo - ULTRA AGRESIVO
            "adx_trend_min": random.uniform(5.0, 20.0),  # Muy permisivo
            "bb_width_range_max": random.uniform(0.06, 0.20),
            "rsi_oversold": random.uniform(45.0, 60.0),
            "atr_mult_sl": random.uniform(3.0, 8.0),  # SL extremo
            "atr_mult_tp_trend": random.uniform(12.0, 30.0),  # TP extremo
            "atr_mult_tp_range": random.uniform(8.0, 18.0),
            "atr_trailing_mult": random.uniform(4.0, 8.0),
            "max_bars_in_trade": random.randint(5, 30),  # 5-30 días
            "min_bars_required": random.randint(10, 20)
        }
    }
    
    return configs.get(timeframe, configs["1h"])


def evaluate_timeframe(symbol: str, timeframe: str, lookback_days: int, trials: int, target_pct: float) -> Dict[str, Any]:
    """Evalúa un timeframe específico."""
    logger.info(f"=== Evaluando {timeframe} ===")
    
    # Obtener datos
    now = datetime.now()
    end = now
    start = end - timedelta(days=lookback_days)
    
    try:
        raw_data = fetch_klines(symbol, timeframe, start, end)
        if raw_data.empty:
            return {"error": f"No data for {timeframe}"}
            
        feature_pipeline = FeaturePipeline()
        data = feature_pipeline.transform(raw_data)
        
        logger.info(f"{timeframe}: {len(data)} velas cargadas")
        
    except Exception as e:
        logger.error(f"Error cargando {timeframe}: {e}")
        return {"error": str(e)}
    
    # Optimización específica del timeframe
    best_results = []
    targets_met = 0
    
    for trial in range(trials):
        params = get_optimized_params_for_timeframe(timeframe)
        
        try:
            strategy = AggressiveRegimeStrategy()
            strategy.enable_daily_tune = False
            strategy.set_parameters(params)
            
            backtester = Backtester(data.copy(), initial_balance=1000.0, warmup_period=30, symbol=symbol, interval=timeframe)
            metrics = asyncio.run(backtester.run(strategy))
            
            return_pct = float(metrics.get("total_return_pct", 0.0))
            
            if return_pct >= target_pct:
                targets_met += 1
            
            result = {
                "params": params,
                "return_pct": return_pct,
                "trades": metrics.get("total_trades", 0),
                "win_rate": metrics.get("win_rate_pct", 0.0),
                "max_drawdown": metrics.get("max_drawdown_pct", 0.0),
                "final_balance": metrics.get("final_balance", 1000.0)
            }
            
            best_results.append(result)
            best_results.sort(key=lambda x: x["return_pct"], reverse=True)
            best_results = best_results[:5]  # Top 5 per timeframe
            
        except Exception as e:
            logger.warning(f"{timeframe} trial {trial}: {e}")
            continue
    
    if not best_results:
        return {"error": f"No valid results for {timeframe}"}
    
    return {
        "timeframe": timeframe,
        "best_return": best_results[0]["return_pct"],
        "targets_met": targets_met,
        "target_rate": round(100 * targets_met / trials, 1),
        "trials": trials,
        "top_results": best_results
    }


def multi_timeframe_optimization():
    """Optimización en múltiples timeframes."""
    
    # Parámetros
    SYMBOL = os.getenv("REPORT_SYMBOL", "BTCUSDT")
    LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "60"))  # Más días para timeframes largos
    TRIALS_PER_TF = int(os.getenv("TRIALS_PER_TF", "50"))  # Trials por timeframe
    TARGET_MONTHLY = float(os.getenv("TARGET_MONTHLY_PCT", "20.0"))
    SEED = int(os.getenv("SEED", "20250831"))
    
    random.seed(SEED)
    
    # Timeframes a evaluar (de menor a mayor)
    timeframes = ["15m", "1h", "4h", "1d"]
    
    logger.info(f"=== OPTIMIZACIÓN MULTI-TIMEFRAME ===")
    logger.info(f"Symbol: {SYMBOL}, Target: {TARGET_MONTHLY}% mensual")
    logger.info(f"Timeframes: {timeframes}, Trials por TF: {TRIALS_PER_TF}")
    
    results = {}
    
    # Evaluar cada timeframe
    for tf in timeframes:
        try:
            result = evaluate_timeframe(SYMBOL, tf, LOOKBACK_DAYS, TRIALS_PER_TF, TARGET_MONTHLY)
            results[tf] = result
            
            if "error" not in result:
                logger.info(f"{tf}: Mejor {result['best_return']:.2f}%, Targets {result['targets_met']}/{TRIALS_PER_TF} ({result['target_rate']}%)")
            else:
                logger.error(f"{tf}: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error evaluating {tf}: {e}")
            results[tf] = {"error": str(e)}
    
    # Encontrar mejor timeframe
    valid_results = {k: v for k, v in results.items() if "error" not in v}
    
    if valid_results:
        best_tf = max(valid_results.keys(), key=lambda x: valid_results[x]["best_return"])
        best_return = valid_results[best_tf]["best_return"]
        
        logger.info("=== RESULTADOS FINALES ===")
        logger.info(f"Mejor timeframe: {best_tf} con {best_return:.2f}%")
        
        for tf, result in valid_results.items():
            if "error" not in result:
                logger.info(f"{tf}: {result['best_return']:.2f}% (targets: {result['target_rate']}%)")
    else:
        logger.error("No se obtuvieron resultados válidos")
        best_tf = "N/A"
        best_return = 0.0
    
    # Guardar resultados
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
    output_file = f"logs/multi_tf_opt_{SYMBOL}_{timestamp}.json"
    
    output_data = {
        "success": len(valid_results) > 0,
        "strategy": "AggressiveRegimeStrategy",
        "symbol": SYMBOL,
        "lookback_days": LOOKBACK_DAYS,
        "trials_per_timeframe": TRIALS_PER_TF,
        "target_monthly_pct": TARGET_MONTHLY,
        "best_timeframe": best_tf,
        "best_return_pct": best_return,
        "meets_target": best_return >= TARGET_MONTHLY,
        "timeframe_results": results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(json.dumps({
        "success": len(valid_results) > 0,
        "output": output_file,
        "best_timeframe": best_tf,
        "best_return_pct": best_return,
        "meets_target": best_return >= TARGET_MONTHLY
    }))


if __name__ == "__main__":
    multi_timeframe_optimization()
