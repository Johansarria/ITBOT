#!/usr/bin/env python3
"""
Test de configuraciones extremas conocidas para crypto trading.
Basado en patrones históricos que han mostrado altos retornos.
"""
import json
import logging
import sys
import requests
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from strategies.aggressive_regime_strategy import AggressiveRegimeStrategy
from strategies.backtester import Backtester
from utils.feature_pipeline import FeaturePipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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


def get_extreme_configurations() -> List[Dict[str, Any]]:
    """Configuraciones extremas basadas en patrones históricos exitosos."""
    
    return [
        {
            "name": "EXTREME_TREND_RIDER",
            "description": "Monta tendencias con TP masivos",
            "params": {
                "adx_trend_min": 5.0,  # Ultra permisivo
                "bb_width_range_max": 0.25,  # Rango máximo
                "rsi_oversold": 50.0,
                "atr_mult_sl": 8.0,  # SL muy amplio
                "atr_mult_tp_trend": 30.0,  # TP extremo
                "atr_mult_tp_range": 20.0,
                "atr_trailing_mult": 6.0,
                "max_bars_in_trade": 1000,  # ~41 días
                "min_bars_required": 10
            }
        },
        {
            "name": "BREAKOUT_HUNTER",
            "description": "Caza breakouts con targets gigantes",
            "params": {
                "adx_trend_min": 8.0,
                "bb_width_range_max": 0.05,  # Solo breakouts reales
                "rsi_oversold": 30.0,
                "atr_mult_sl": 6.0,
                "atr_mult_tp_trend": 25.0,
                "atr_mult_tp_range": 15.0,
                "atr_trailing_mult": 5.0,
                "max_bars_in_trade": 800,
                "min_bars_required": 15
            }
        },
        {
            "name": "VOLATILITY_SCALPER",
            "description": "Aprovecha volatilidad extrema",
            "params": {
                "adx_trend_min": 12.0,
                "bb_width_range_max": 0.15,
                "rsi_oversold": 45.0,
                "atr_mult_sl": 4.0,
                "atr_mult_tp_trend": 18.0,
                "atr_mult_tp_range": 12.0,
                "atr_trailing_mult": 3.5,
                "max_bars_in_trade": 400,
                "min_bars_required": 20
            }
        },
        {
            "name": "MOMENTUM_ROCKET",
            "description": "Momentum puro con stops amplios",
            "params": {
                "adx_trend_min": 10.0,
                "bb_width_range_max": 0.08,
                "rsi_oversold": 40.0,
                "atr_mult_sl": 5.5,
                "atr_mult_tp_trend": 22.0,
                "atr_mult_tp_range": 14.0,
                "atr_trailing_mult": 4.5,
                "max_bars_in_trade": 600,
                "min_bars_required": 18
            }
        },
        {
            "name": "SWING_MONSTER",
            "description": "Swings gigantes en todos los regímenes",
            "params": {
                "adx_trend_min": 6.0,
                "bb_width_range_max": 0.20,
                "rsi_oversold": 55.0,  # Muy permisivo
                "atr_mult_sl": 7.0,
                "atr_mult_tp_trend": 35.0,  # TP monstruoso
                "atr_mult_tp_range": 25.0,
                "atr_trailing_mult": 7.0,
                "max_bars_in_trade": 1200,  # 50 días
                "min_bars_required": 12
            }
        },
        {
            "name": "CRYPTO_MOONSHOT",
            "description": "Optimizado para moonshots crypto",
            "params": {
                "adx_trend_min": 3.0,  # Sin filtro ADX
                "bb_width_range_max": 0.30,  # Todo es válido
                "rsi_oversold": 60.0,  # Sin filtro RSI
                "atr_mult_sl": 10.0,  # SL extremo
                "atr_mult_tp_trend": 50.0,  # TP lunar
                "atr_mult_tp_range": 30.0,
                "atr_trailing_mult": 8.0,
                "max_bars_in_trade": 1500,  # ~62 días
                "min_bars_required": 8
            }
        },
        {
            "name": "RANGE_DESTROYER",
            "description": "Destruye rangos con patience extrema",
            "params": {
                "adx_trend_min": 15.0,
                "bb_width_range_max": 0.12,
                "rsi_oversold": 35.0,
                "atr_mult_sl": 4.5,
                "atr_mult_tp_trend": 20.0,
                "atr_mult_tp_range": 18.0,  # TP alto en rango
                "atr_trailing_mult": 4.0,
                "max_bars_in_trade": 720,
                "min_bars_required": 25
            }
        },
        {
            "name": "PATIENCE_PAYS",
            "description": "Paciencia extrema para el trade perfecto",
            "params": {
                "adx_trend_min": 20.0,
                "bb_width_range_max": 0.06,
                "rsi_oversold": 25.0,  # Extrema sobreventa
                "atr_mult_sl": 6.0,
                "atr_mult_tp_trend": 28.0,
                "atr_mult_tp_range": 20.0,
                "atr_trailing_mult": 5.5,
                "max_bars_in_trade": 900,
                "min_bars_required": 30
            }
        }
    ]


def test_extreme_configs():
    """Test todas las configuraciones extremas."""
    
    # Parámetros
    SYMBOL = os.getenv("REPORT_SYMBOL", "BTCUSDT")
    INTERVAL = os.getenv("REPORT_INTERVAL", "1h")
    LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "60"))
    TARGET_MONTHLY = float(os.getenv("TARGET_MONTHLY_PCT", "20.0"))
    BALANCE = float(os.getenv("INITIAL_BALANCE", "1000"))
    
    logger.info(f"=== TEST CONFIGURACIONES EXTREMAS ===")
    logger.info(f"Symbol: {SYMBOL}, Interval: {INTERVAL}, Target: {TARGET_MONTHLY}%")
    
    # Cargar datos
    try:
        now = datetime.now()
        end = now
        start = end - timedelta(days=LOOKBACK_DAYS)
        
        raw_data = fetch_klines(SYMBOL, INTERVAL, start, end)
        feature_pipeline = FeaturePipeline()
        data = feature_pipeline.transform(raw_data)
        
        logger.info(f"Datos cargados: {len(data)} velas desde {data.index[0]} hasta {data.index[-1]}")
        
    except Exception as e:
        logger.error(f"Error cargando datos: {e}")
        return
    
    # Test cada configuración
    configs = get_extreme_configurations()
    results = []
    targets_met = 0
    
    for config in configs:
        name = config["name"]
        params = config["params"]
        description = config["description"]
        
        try:
            logger.info(f"Testing {name}: {description}")
            
            # Crear estrategia
            strategy = AggressiveRegimeStrategy()
            strategy.enable_daily_tune = False
            strategy.set_parameters(params)
            
            # Backtest
            backtester = Backtester(
                data.copy(), 
                initial_balance=BALANCE, 
                warmup_period=max(10, params.get("min_bars_required", 20)), 
                symbol=SYMBOL, 
                interval=INTERVAL
            )
            metrics = asyncio.run(backtester.run(strategy))
            
            return_pct = float(metrics.get("total_return_pct", 0.0))
            trades = metrics.get("total_trades", 0)
            win_rate = metrics.get("win_rate_pct", 0.0)
            max_dd = metrics.get("max_drawdown_pct", 0.0)
            final_balance = metrics.get("final_balance", BALANCE)
            
            result = {
                "name": name,
                "description": description,
                "return_pct": return_pct,
                "trades": trades,
                "win_rate": win_rate,
                "max_drawdown": max_dd,
                "final_balance": final_balance,
                "meets_target": return_pct >= TARGET_MONTHLY,
                "params": params
            }
            
            results.append(result)
            
            if return_pct >= TARGET_MONTHLY:
                targets_met += 1
            
            logger.info(f"{name}: {return_pct:.2f}%, {trades} trades, {win_rate:.1f}% WR, {max_dd:.2f}% DD")
            
        except Exception as e:
            logger.error(f"Error testing {name}: {e}")
            continue
    
    # Ordenar por retorno
    results.sort(key=lambda x: x["return_pct"], reverse=True)
    
    # Resultados finales
    logger.info("=== RESULTADOS CONFIGURACIONES EXTREMAS ===")
    if results:
        best = results[0]
        logger.info(f"MEJOR: {best['name']} - {best['return_pct']:.2f}%")
        logger.info(f"Configs que alcanzaron target: {targets_met}/{len(results)}")
        
        for i, result in enumerate(results[:5], 1):
            status = "✅" if result["meets_target"] else "❌"
            logger.info(f"{i}. {result['name']}: {result['return_pct']:.2f}% {status}")
    
    # Guardar resultados
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
    output_file = f"logs/extreme_configs_{SYMBOL}_{timestamp}.json"
    
    output_data = {
        "success": len(results) > 0,
        "strategy": "AggressiveRegimeStrategy",
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "lookback_days": LOOKBACK_DAYS,
        "target_monthly_pct": TARGET_MONTHLY,
        "configs_tested": len(configs),
        "targets_met": targets_met,
        "best_config": results[0] if results else None,
        "all_results": results
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(json.dumps({
        "success": len(results) > 0,
        "output": output_file,
        "best_return_pct": results[0]["return_pct"] if results else 0.0,
        "targets_met": targets_met,
        "meets_target": (results[0]["return_pct"] >= TARGET_MONTHLY) if results else False
    }))


if __name__ == "__main__":
    test_extreme_configs()
