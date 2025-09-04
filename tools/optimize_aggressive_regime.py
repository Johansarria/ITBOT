#!/usr/bin/env python3
"""
Optimización específica para AggressiveRegimeStrategy con parámetros expandidos.
"""
import json
import logging
import random
import sys
import warnings
import requests
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta, timezone

import pandas as pd

# Configuración de warnings
warnings.filterwarnings("ignore", category=FutureWarning, module='pandas')
warnings.filterwarnings("ignore", category=UserWarning, module='lightgbm')

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


def get_random_params() -> Dict[str, float]:
    """Genera parámetros aleatorios para AggressiveRegimeStrategy con rangos amplios."""
    return {
        # ADX y BB - rangos más amplios para capturar más oportunidades
        "adx_trend_min": random.uniform(10.0, 30.0),  # Muy permisivo
        "bb_width_range_max": random.uniform(0.02, 0.12),  # Rango amplio
        
        # RSI - umbrales más permisivos
        "rsi_oversold": random.uniform(35.0, 50.0),  # Más oportunidades
        "rsi_overbought": random.uniform(70.0, 85.0),
        
        # ATR multipliers - MUY AGRESIVOS para 20%+ mensual
        "atr_mult_sl": random.uniform(1.8, 4.0),  # Stop loss amplio
        "atr_mult_tp_trend": random.uniform(4.0, 12.0),  # TP muy alto
        "atr_mult_tp_range": random.uniform(3.0, 8.0),  # TP alto en rango
        "atr_trailing_mult": random.uniform(2.0, 4.5),  # Trailing conservador
        
        # Tiempo en trades - muy extendido
        "max_bars_in_trade": random.randint(96, 336),  # 4-14 días
        
        # Parámetros adicionales para agresividad
        "min_bars_between_trades": random.randint(1, 3),
        "min_bars_required": random.randint(25, 45)
    }


def evaluate_params(df: pd.DataFrame, params: Dict[str, float], symbol: str, interval: str, balance: float = 1000.0) -> Tuple[float, Dict[str, Any]]:
    """Evalúa un conjunto de parámetros."""
    try:
        # Crear estrategia con parámetros
        strategy = AggressiveRegimeStrategy()
        
        # Configurar para optimización (sin auto-tune)
        strategy.enable_daily_tune = False
        
        # Aplicar parámetros
        strategy.set_parameters(params)
        
        # Backtest
        backtester = Backtester(df.copy(), initial_balance=balance, warmup_period=40, symbol=symbol, interval=interval)
        metrics = asyncio.run(backtester.run(strategy))
        
        total_return = float(metrics.get("total_return_pct", 0.0))
        
        # Crear output estructurado
        output = {
            "params": params,
            "metrics": {
                "total_return_pct": total_return,
                "max_drawdown_pct": metrics.get("max_drawdown_pct", 0.0),
                "trades": metrics.get("total_trades", 0),
                "win_rate_pct": metrics.get("win_rate_pct", 0.0),
                "final_balance": metrics.get("final_balance", balance),
                "sharpe_ratio": metrics.get("sharpe_ratio", 0.0)
            }
        }
        
        return total_return, output
        
    except Exception as e:
        logger.warning(f"Error evaluating params: {e}")
        return -100.0, {
            "params": params,
            "metrics": {
                "total_return_pct": -100.0,
                "final_balance": 0.0,
                "trades": 0,
                "win_rate_pct": 0.0,
                "max_drawdown_pct": 100.0,
                "sharpe_ratio": -10.0
            }
        }


def optimize_aggressive_strategy():
    """Optimización principal."""
    import os
    
    # Parámetros de optimización
    SYMBOL = os.getenv("REPORT_SYMBOL", "BTCUSDT")
    INTERVAL = os.getenv("REPORT_INTERVAL", "1h") 
    LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "45"))
    TRIALS = int(os.getenv("TRIALS", "250"))
    BALANCE = float(os.getenv("INITIAL_BALANCE", "1000"))
    TARGET_MONTHLY = float(os.getenv("TARGET_MONTHLY_PCT", "20.0"))
    SEED = int(os.getenv("SEED", "20250831"))
    
    random.seed(SEED)
    
    logger.info(f"=== OPTIMIZACIÓN AGRESIVA ===")
    logger.info(f"Symbol: {SYMBOL}, Interval: {INTERVAL}, Lookback: {LOOKBACK_DAYS} días")
    logger.info(f"Trials: {TRIALS}, Balance: ${BALANCE}, Target: {TARGET_MONTHLY}% mensual")
    
    # Cargar y preparar datos
    try:
        # Calcular fechas
        now = datetime.now()
        end = now
        start = end - timedelta(days=LOOKBACK_DAYS)
        
        # Obtener datos de Binance
        raw_data = fetch_klines(SYMBOL, INTERVAL, start, end)
        
        if raw_data is None or raw_data.empty:
            logger.error("No se pudieron cargar los datos de Binance")
            return
            
        # Aplicar feature pipeline
        feature_pipeline = FeaturePipeline()
        data = feature_pipeline.transform(raw_data)
        
        if data is None or data.empty:
            logger.error("No se pudieron procesar las features")
            return
            
        logger.info(f"Datos procesados: {len(data)} velas desde {data.index[0]} hasta {data.index[-1]}")
        
    except Exception as e:
        logger.error(f"Error cargando datos: {e}")
        return
    
    # Optimización
    best_results: List[Tuple[float, Dict[str, Any]]] = []
    target_met_count = 0
    
    for trial in range(1, TRIALS + 1):
        # Generar parámetros aleatorios
        params = get_random_params()
        
        try:
            # Evaluar
            current_return, result_detail = evaluate_params(data, params, SYMBOL, INTERVAL, BALANCE)
            
            # Agregar a resultados
            best_results.append((current_return, result_detail))
            best_results.sort(key=lambda x: x[0], reverse=True)
            best_results = best_results[:10]  # Solo top 10
            
            # Contar targets alcanzados
            if current_return >= TARGET_MONTHLY:
                target_met_count += 1
            
        except Exception as e:
            logger.warning(f"Error en trial {trial}: {e}")
            continue
        
        # Log progreso
        if trial % 25 == 0:
            best_return = best_results[0][0] if best_results else -100.0
            logger.info(f"Trial {trial}/{TRIALS} - Mejor: {best_return:.2f}% - Targets: {target_met_count}")
    
    # Resultados finales
    if not best_results:
        logger.error("No se pudieron obtener resultados válidos")
        return
        
    best_return = best_results[0][0]
    best_params = best_results[0][1]["params"]
    best_metrics = best_results[0][1]["metrics"]
    
    logger.info("=== RESULTADOS FINALES ===")
    logger.info(f"Mejor retorno: {best_return:.2f}% (target: {TARGET_MONTHLY}%)")
    logger.info(f"Trials que alcanzaron target: {target_met_count}/{TRIALS} ({100*target_met_count/TRIALS:.1f}%)")
    logger.info(f"Trades: {best_metrics['trades']}, Win Rate: {best_metrics['win_rate_pct']:.1f}%")
    logger.info(f"Max Drawdown: {best_metrics['max_drawdown_pct']:.2f}%")
    
    # Guardar resultados
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
    output_file = f"logs/aggressive_opt_{SYMBOL}_{timestamp}.json"
    
    output_data = {
        "success": True,
        "strategy": "AggressiveRegimeStrategy", 
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "lookback_days": LOOKBACK_DAYS,
        "trials": TRIALS,
        "target_monthly_pct": TARGET_MONTHLY,
        "best_return_pct": best_return,
        "targets_met": target_met_count,
        "targets_met_pct": round(100 * target_met_count / TRIALS, 2),
        "meets_target": best_return >= TARGET_MONTHLY,
        "best_params": best_params,
        "best_metrics": best_metrics,
        "top_10": [
            {
                "rank": i + 1,
                "params": result["params"],
                "metrics": result["metrics"]
            }
            for i, (ret, result) in enumerate(best_results)
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(json.dumps({
        "success": True,
        "output": output_file,
        "best_return_pct": best_return,
        "targets_met": target_met_count,
        "meets_target": best_return >= TARGET_MONTHLY
    }))


if __name__ == "__main__":
    optimize_aggressive_strategy()
