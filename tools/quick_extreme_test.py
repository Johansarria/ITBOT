#!/usr/bin/env python3
"""
Quick test de 3 configuraciones extremas ultra-agresivas para generar 20%+ mensual
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

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuraciones extremas más prometedoras
EXTREME_CONFIGS = {
    "CRYPTO_MOONSHOT": {
        "name": "CRYPTO_MOONSHOT: Para gains de otro planeta",
        "params": {
            'adx_period': 14,
            'adx_threshold': 25,
            'bb_period': 20, 
            'bb_std': 2.0,
            'ma_short': 10,
            'ma_long': 30,
            'rsi_period': 14,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'take_profit_atr_multiplier': 50.0,  # 50x ATR - para la luna
            'stop_loss_atr_multiplier': 10.0,    # 10x ATR - más tolerante
            'min_trade_duration': 1500,          # ~62 días de hold mínimo
            'atr_period': 14
        }
    },
    
    "SWING_MONSTER": {
        "name": "SWING_MONSTER: Come volatilidad para breakfast", 
        "params": {
            'adx_period': 14,
            'adx_threshold': 15,  # Más permisivo
            'bb_period': 20,
            'bb_std': 2.0,
            'ma_short': 5,   # Más agresivo
            'ma_long': 20,   # Más agresivo
            'rsi_period': 14,
            'rsi_overbought': 75,  # Más extremo
            'rsi_oversold': 25,    # Más extremo
            'take_profit_atr_multiplier': 35.0,  # 35x ATR
            'stop_loss_atr_multiplier': 8.0,     # 8x ATR
            'min_trade_duration': 1000,          # ~41 días
            'atr_period': 14
        }
    },
    
    "HODL_HUNTER": {
        "name": "HODL_HUNTER: Para los que saben esperar gains masivos",
        "params": {
            'adx_period': 21,      # Período más largo
            'adx_threshold': 20,   # Moderado
            'bb_period': 50,       # BB muy largo para filtrar ruido
            'bb_std': 2.5,         # Más sensible
            'ma_short': 12,
            'ma_long': 26,
            'rsi_period': 21,      # RSI más largo
            'rsi_overbought': 65,  # Menos extremo
            'rsi_oversold': 35,    # Menos extremo
            'take_profit_atr_multiplier': 40.0,  # 40x ATR
            'stop_loss_atr_multiplier': 12.0,    # 12x ATR - ultra tolerante
            'min_trade_duration': 2000,          # ~83 días de hold
            'atr_period': 21
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


async def test_config(config_name, config_data, df, target_monthly_pct=20.0):
    """Testea una configuración específica"""
    logger.info(f"Testing {config_name}: {config_data['name']}")
    
    try:
        # Crear estrategia
        strategy = AggressiveRegimeStrategy()
        strategy.set_parameters(config_data['params'])
        
        # Crear backtester con balance inicial
        initial_balance = float(os.getenv('INITIAL_BALANCE', '1000'))
        backtester = Backtester(df, initial_balance=initial_balance)
        
        # Ejecutar backtest
        metrics = await backtester.run(strategy)
        
        # Calcular métricas
        total_days = (df.index[-1] - df.index[0]).days
        total_return = metrics.get('total_return_percentage', 0)
        monthly_equivalent = calculate_monthly_return_rate(total_return, total_days)
        
        # Métricas de trading
        total_trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate', 0)
        avg_trade_return = metrics.get('average_trade_return_percentage', 0)
        max_drawdown = metrics.get('max_drawdown_percentage', 0)
        
        result = {
            'config': config_name,
            'total_return': total_return,
            'monthly_equivalent': monthly_equivalent,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_trade_return': avg_trade_return,
            'max_drawdown': max_drawdown,
            'meets_target': monthly_equivalent >= target_monthly_pct,
            'params': config_data['params'].copy()
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing {config_name}: {str(e)}")
        return {
            'config': config_name,
            'error': str(e),
            'meets_target': False
        }


async def quick_extreme_test():
    """Test rápido de configuraciones extremas"""
    symbol = os.getenv('REPORT_SYMBOL', 'BTCUSDT')
    interval = os.getenv('REPORT_INTERVAL', '1h')
    lookback_days = int(os.getenv('LOOKBACK_DAYS', '30'))  # Más corto para ser rápido
    target_monthly_pct = float(os.getenv('TARGET_MONTHLY_PCT', '20.0'))
    
    logger.info("=== QUICK EXTREME TEST ===")
    logger.info(f"Symbol: {symbol}, Interval: {interval}, Target: {target_monthly_pct}%")
    
    # Cargar datos
    try:
        klines = await fetch_klines(
            symbol=symbol,
            interval=interval,
            limit=lookback_days * 24 if interval == '1h' else 1000
        )
        
        # Procesar con FeaturePipeline
        pipeline = FeaturePipeline()
        df = pipeline.transform(klines)
        
        logger.info(f"Datos cargados: {len(df)} velas desde {df.index[0]} hasta {df.index[-1]}")
        
    except Exception as e:
        logger.error(f"Error cargando datos: {e}")
        return
    
    # Testear configuraciones
    results = []
    
    for config_name, config_data in EXTREME_CONFIGS.items():
        result = await test_config(config_name, config_data, df, target_monthly_pct)
        results.append(result)
        
        # Log resultado inmediato
        if 'error' in result:
            logger.error(f"❌ {config_name}: ERROR - {result['error']}")
        else:
            status = "✅ MEETS TARGET" if result['meets_target'] else "❌ Below target"
            logger.info(f"{status} {config_name}:")
            logger.info(f"  📈 Return: {result['total_return']:.2f}% total, {result['monthly_equivalent']:.2f}% monthly equiv")
            logger.info(f"  📊 Trades: {result['total_trades']}, Win Rate: {result['win_rate']:.1f}%")
            logger.info(f"  💹 Avg Trade: {result['avg_trade_return']:.2f}%, Max DD: {result['max_drawdown']:.2f}%")
    
    # Resumen final
    logger.info("\n=== RESUMEN FINAL ===")
    successful = [r for r in results if r.get('meets_target', False)]
    
    if successful:
        logger.info(f"✅ {len(successful)} configuraciones alcanzan el target de {target_monthly_pct}%:")
        for result in sorted(successful, key=lambda x: x.get('monthly_equivalent', 0), reverse=True):
            logger.info(f"  🥇 {result['config']}: {result['monthly_equivalent']:.2f}% mensual")
            
        # Mejor configuración
        best = max(successful, key=lambda x: x.get('monthly_equivalent', 0))
        logger.info(f"\n🏆 MEJOR CONFIGURACIÓN: {best['config']}")
        logger.info(f"📊 Retorno mensual equivalente: {best['monthly_equivalent']:.2f}%")
        logger.info(f"📈 Retorno total: {best['total_return']:.2f}%")
        logger.info(f"🎯 Trades: {best['total_trades']}, Win Rate: {best['win_rate']:.1f}%")
        logger.info("📋 PARÁMETROS:")
        for key, value in best['params'].items():
            logger.info(f"  {key}: {value}")
            
    else:
        logger.warning(f"❌ Ninguna configuración alcanza el target de {target_monthly_pct}% mensual")
        if results and not any('error' in r for r in results):
            best_attempt = max(results, key=lambda x: x.get('monthly_equivalent', -100))
            logger.info(f"💡 Mejor intento: {best_attempt['config']} con {best_attempt['monthly_equivalent']:.2f}% mensual")


if __name__ == "__main__":
    asyncio.run(quick_extreme_test())
