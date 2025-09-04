#!/usr/bin/env python3
"""
Test de la estrategia de scalping agresivo
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import numpy as np
import pandas as pd

# Imports locales
from strategies.scalping_aggressive_strategy import ScalpingAggressiveStrategy
from strategies.backtester import Backtester
from utils.binance_client import get_binance_client
from utils.feature_pipeline import FeaturePipeline

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def fetch_klines(symbol: str, interval: str, limit: int = 1000) -> pd.DataFrame:
    """Fetch klines data from Binance API"""
    client = await get_binance_client()
    klines = await client.get_klines(symbol=symbol, interval=interval, limit=limit)
    
    # Convert to DataFrame
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                      'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                                      'taker_buy_quote', 'ignore'])
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    
    # Convert price columns to float
    price_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
    for col in price_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df[price_cols]


def calculate_monthly_return_rate(total_return_pct, days):
    """Calcula tasa de retorno mensual equivalente"""
    if days <= 0 or total_return_pct <= -100:
        return -100.0
    
    daily_rate = (1 + total_return_pct/100) ** (1/days) - 1
    monthly_rate = (1 + daily_rate) ** 30 - 1
    return monthly_rate * 100


# Configuraciones de scalping agresivo
SCALPING_CONFIGS = {
    "MICRO_SCALPER": {
        "name": "Micro Scalper: 0.5% profits, muchos trades",
        "params": {
            'bb_period': 8,
            'bb_std': 1.2,
            'rsi_period': 5,
            'rsi_overbought': 78,
            'rsi_oversold': 22,
            'take_profit_pct': 0.5,  # Solo 0.5% 
            'stop_loss_pct': 0.2,    # Stop ultra-tight
            'momentum_periods': [2, 3]
        }
    },
    
    "AGGRESSIVE_SCALPER": {
        "name": "Aggressive Scalper: 0.8% profits, balance risk/reward",
        "params": {
            'bb_period': 10,
            'bb_std': 1.5,
            'rsi_period': 7,
            'rsi_overbought': 75,
            'rsi_oversold': 25,
            'take_profit_pct': 0.8,  # 0.8% target
            'stop_loss_pct': 0.3,    # 0.3% stop
            'momentum_periods': [3, 5]
        }
    },
    
    "TURBO_SCALPER": {
        "name": "Turbo Scalper: 1.2% profits, más agresivo",
        "params": {
            'bb_period': 12,
            'bb_std': 1.8,
            'rsi_period': 9,
            'rsi_overbought': 72,
            'rsi_oversold': 28,
            'take_profit_pct': 1.2,  # 1.2% target
            'stop_loss_pct': 0.4,    # 0.4% stop
            'momentum_periods': [4, 7]
        }
    }
}


async def test_scalping_config(config_name, config_data, df, target_monthly_pct=20.0):
    """Test una configuración de scalping"""
    logger.info(f"Testing {config_name}: {config_data['name']}")
    
    try:
        # Crear estrategia de scalping
        strategy = ScalpingAggressiveStrategy()
        strategy.set_parameters(config_data['params'])
        
        # Crear backtester
        backtester = Backtester(df, initial_balance=1000.0)
        
        # Ejecutar backtest
        metrics = await backtester.run(strategy)
        
        # Calcular métricas
        total_days = (df.index[-1] - df.index[0]).days
        total_return = metrics.get('total_return_pct', 0)
        monthly_equivalent = calculate_monthly_return_rate(total_return, total_days)
        
        # Stats detalladas
        total_trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate_pct', 0)
        trades_list = metrics.get('trades', [])
        profitable_trades = len([t for t in trades_list if t.get('pnl', 0) > 0])
        
        # Calcular trades por día
        trades_per_day = total_trades / max(total_days, 1)
        
        result = {
            'config': config_name,
            'total_return': total_return,
            'monthly_equivalent': monthly_equivalent,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': win_rate,
            'trades_per_day': trades_per_day,
            'meets_target': monthly_equivalent >= target_monthly_pct,
            'days_tested': total_days,
            'params': config_data['params'].copy()
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing scalping {config_name}: {str(e)}")
        return {
            'config': config_name,
            'error': str(e),
            'meets_target': False
        }


async def test_scalping_strategy():
    """Test de estrategia de scalping agresivo"""
    
    logger.info("=== SCALPING AGGRESSIVE TEST ===")
    logger.info("Buscando 20%+ mensual con scalping ultra-agresivo")
    
    # Cargar datos de 1 hora (mejor para scalping)
    klines = await fetch_klines(symbol='BTCUSDT', interval='1h', limit=720)  # 30 días
    
    # Procesar con FeaturePipeline
    pipeline = FeaturePipeline()
    df = pipeline.transform(klines)
    
    logger.info(f"Datos cargados: {len(df)} velas desde {df.index[0]} hasta {df.index[-1]}")
    
    # Test configuraciones
    results = []
    
    for config_name, config_data in SCALPING_CONFIGS.items():
        result = await test_scalping_config(config_name, config_data, df, target_monthly_pct=20.0)
        results.append(result)
        
        # Log inmediato
        if 'error' in result:
            logger.error(f"❌ {config_name}: ERROR - {result['error']}")
        else:
            status = "✅ MEETS TARGET" if result['meets_target'] else "❌ Below target"
            logger.info(f"{status} {config_name}:")
            logger.info(f"  📈 Return: {result['total_return']:.2f}% total, {result['monthly_equivalent']:.2f}% mensual")
            logger.info(f"  📊 Trades: {result['total_trades']}, Profitable: {result['profitable_trades']}, Win Rate: {result['win_rate']:.1f}%")
            logger.info(f"  🔄 Trades/día: {result['trades_per_day']:.1f}")
    
    # Resumen
    logger.info("\n=== RESUMEN SCALPING ===")
    successful = [r for r in results if r.get('meets_target', False)]
    
    if successful:
        logger.info(f"✅ {len(successful)} configs de scalping alcanzan 20%+ mensual:")
        for result in sorted(successful, key=lambda x: x.get('monthly_equivalent', 0), reverse=True):
            logger.info(f"  🥇 {result['config']}: {result['monthly_equivalent']:.2f}% mensual")
            
        # Mejor config
        best = max(successful, key=lambda x: x.get('monthly_equivalent', 0))
        logger.info(f"\n🏆 MEJOR SCALPING CONFIG: {best['config']}")
        logger.info(f"📊 {best['monthly_equivalent']:.2f}% mensual con {best['trades_per_day']:.1f} trades/día")
        logger.info("🎯 PARÁMETROS GANADORES:")
        for key, value in best['params'].items():
            logger.info(f"  {key}: {value}")
            
    else:
        logger.warning("❌ Ninguna config de scalping alcanza 20% mensual")
        if results and not any('error' in r for r in results):
            best_attempt = max(results, key=lambda x: x.get('monthly_equivalent', -100))
            logger.info(f"💡 Mejor scalping: {best_attempt['config']} con {best_attempt['monthly_equivalent']:.2f}% mensual")


if __name__ == "__main__":
    asyncio.run(test_scalping_strategy())
