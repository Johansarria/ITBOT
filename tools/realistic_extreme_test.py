#!/usr/bin/env python3
"""
Test con configuraciones más realistas pero agresivas para lograr 20% mensual
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

# Imports locales
from strategies.aggressive_regime_strategy import AggressiveRegimeStrategy
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
    
    return df[price_cols]  # Return only needed columns


# Configuraciones más balanceadas pero aún agresivas
REALISTIC_EXTREME_CONFIGS = {
    "SWING_MASTER_4H": {
        "name": "Swing Master 4H: Timeframes largos para captures masivos",
        "interval": "4h",
        "params": {
            'adx_period': 14,
            'adx_threshold': 20,
            'bb_period': 14,  # Más responsive
            'bb_std': 2.0,
            'ma_short': 8,
            'ma_long': 21,
            'rsi_period': 14,
            'rsi_overbought': 75,
            'rsi_oversold': 25,
            'take_profit_atr_multiplier': 4.0,  # 4x ATR en 4h es agresivo pero realista
            'stop_loss_atr_multiplier': 2.0,    # 2x ATR stop
            'min_trade_duration': 12,           # 12 barras = 2 días en 4h
            'atr_period': 14
        }
    },
    
    "DAILY_TITAN": {
        "name": "Daily Titan: Timeframe diario para captures épicos",
        "interval": "1d", 
        "params": {
            'adx_period': 14,
            'adx_threshold': 25,
            'bb_period': 10,  # Más reactive en daily
            'bb_std': 2.2,
            'ma_short': 5,
            'ma_long': 13, 
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'take_profit_atr_multiplier': 3.0,  # 3x ATR en daily puede ser masivo
            'stop_loss_atr_multiplier': 1.5,    # 1.5x ATR stop
            'min_trade_duration': 5,            # 5 días mínimo
            'atr_period': 14
        }
    },
    
    "HOURLY_BEAST": {
        "name": "Hourly Beast: 1h optimizado para profits rápidos",
        "interval": "1h",
        "params": {
            'adx_period': 14,
            'adx_threshold': 18,  # Más permisivo
            'bb_period': 16,
            'bb_std': 1.8,   # Más tight para más señales
            'ma_short': 12,
            'ma_long': 26,
            'rsi_period': 14,
            'rsi_overbought': 72,
            'rsi_oversold': 28,
            'take_profit_atr_multiplier': 2.5,  # Más realista en 1h
            'stop_loss_atr_multiplier': 1.2,    # Stop más tight
            'min_trade_duration': 24,           # 1 día mínimo 
            'atr_period': 14
        }
    }
}


def calculate_monthly_return_rate(total_return_pct, days):
    """Calcula tasa de retorno mensual equivalente"""
    if days <= 0 or total_return_pct <= -100:
        return -100.0
    
    daily_rate = (1 + total_return_pct/100) ** (1/days) - 1
    monthly_rate = (1 + daily_rate) ** 30 - 1
    return monthly_rate * 100


async def test_realistic_config(config_name, config_data, target_monthly_pct=20.0):
    """Test una configuración específica con timeframe apropiado"""
    logger.info(f"Testing {config_name}: {config_data['name']}")
    
    try:
        interval = config_data['interval']
        
        # Calcular límite basado en timeframe
        if interval == '1h':
            limit = 720  # 30 días
        elif interval == '4h':
            limit = 180  # 30 días  
        elif interval == '1d':
            limit = 60   # 60 días
        else:
            limit = 500
            
        # Cargar datos
        klines = await fetch_klines(symbol='BTCUSDT', interval=interval, limit=limit)
        
        # Procesar con FeaturePipeline
        pipeline = FeaturePipeline()
        df = pipeline.transform(klines)
        
        logger.info(f"Datos {interval}: {len(df)} velas desde {df.index[0]} hasta {df.index[-1]}")
        
        # Crear estrategia
        strategy = AggressiveRegimeStrategy()
        strategy.set_parameters(config_data['params'])
        
        # Crear backtester
        backtester = Backtester(df, initial_balance=1000.0)
        
        # Ejecutar backtest
        metrics = await backtester.run(strategy)
        
        # Calcular métricas
        total_days = (df.index[-1] - df.index[0]).days
        total_return = metrics.get('total_return_pct', 0)
        monthly_equivalent = calculate_monthly_return_rate(total_return, total_days)
        
        # Stats de trading
        total_trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate_pct', 0)
        trades_list = metrics.get('trades', [])
        
        # Analizar trades
        profitable_trades = len([t for t in trades_list if t.get('pnl', 0) > 0])
        
        result = {
            'config': config_name,
            'interval': interval,
            'total_return': total_return,
            'monthly_equivalent': monthly_equivalent,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': win_rate,
            'meets_target': monthly_equivalent >= target_monthly_pct,
            'days_tested': total_days
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing {config_name}: {str(e)}")
        return {
            'config': config_name,
            'error': str(e),
            'meets_target': False
        }


async def realistic_extreme_test():
    """Test con configuraciones más realistas para 20% mensual"""
    
    logger.info("=== REALISTIC EXTREME TEST ===")
    logger.info("Buscando 20%+ mensual con configs realistas pero agresivas")
    
    results = []
    
    for config_name, config_data in REALISTIC_EXTREME_CONFIGS.items():
        result = await test_realistic_config(config_name, config_data, target_monthly_pct=20.0)
        results.append(result)
        
        # Log resultado inmediato
        if 'error' in result:
            logger.error(f"❌ {config_name}: ERROR - {result['error']}")
        else:
            status = "✅ MEETS TARGET" if result['meets_target'] else "❌ Below target"
            logger.info(f"{status} {config_name} ({result['interval']}):")
            logger.info(f"  📈 Return: {result['total_return']:.2f}% total, {result['monthly_equivalent']:.2f}% mensual equiv")
            logger.info(f"  📊 Trades: {result['total_trades']}, Profitable: {result['profitable_trades']}, Win Rate: {result['win_rate']:.1f}%")
            logger.info(f"  📅 Período: {result['days_tested']} días")
    
    # Resumen final
    logger.info("\n=== RESUMEN FINAL ===")
    successful = [r for r in results if r.get('meets_target', False)]
    
    if successful:
        logger.info(f"✅ {len(successful)} configuraciones alcanzan el target de 20%:")
        for result in sorted(successful, key=lambda x: x.get('monthly_equivalent', 0), reverse=True):
            logger.info(f"  🥇 {result['config']} ({result['interval']}): {result['monthly_equivalent']:.2f}% mensual")
            
        # Mejor configuración
        best = max(successful, key=lambda x: x.get('monthly_equivalent', 0))
        logger.info(f"\n🏆 MEJOR CONFIG: {best['config']} ({best['interval']})")
        logger.info(f"📊 Retorno mensual: {best['monthly_equivalent']:.2f}%")
        logger.info(f"📈 Retorno total: {best['total_return']:.2f}% en {best['days_tested']} días")
        logger.info(f"🎯 {best['total_trades']} trades, {best['profitable_trades']} profitable, {best['win_rate']:.1f}% win rate")
            
    else:
        logger.warning(f"❌ Ninguna configuración alcanza el target de 20% mensual")
        if results and not any('error' in r for r in results):
            best_attempt = max(results, key=lambda x: x.get('monthly_equivalent', -100))
            logger.info(f"💡 Mejor intento: {best_attempt['config']} ({best_attempt['interval']}) con {best_attempt['monthly_equivalent']:.2f}% mensual")


if __name__ == "__main__":
    asyncio.run(realistic_extreme_test())
