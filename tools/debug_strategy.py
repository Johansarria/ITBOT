#!/usr/bin/env python3
"""
Debug rápido para entender por qué los trades tienen 0% retorno
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


async def debug_strategy():
    """Debug de la estrategia para ver por qué no genera profits"""
    
    # Configuración simple
    test_params = {
        'adx_period': 14,
        'adx_threshold': 25,
        'bb_period': 20, 
        'bb_std': 2.0,
        'ma_short': 10,
        'ma_long': 30,
        'rsi_period': 14,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
        'take_profit_atr_multiplier': 10.0,  # Solo 10x para debug
        'stop_loss_atr_multiplier': 5.0,     # Solo 5x para debug
        'min_trade_duration': 168,           # 1 semana
        'atr_period': 14
    }
    
    logger.info("=== DEBUG STRATEGY ===")
    
    # Cargar datos
    klines = await fetch_klines(symbol='BTCUSDT', interval='1h', limit=500)
    
    # Procesar con FeaturePipeline  
    pipeline = FeaturePipeline()
    df = pipeline.transform(klines)
    
    logger.info(f"Datos cargados: {len(df)} velas desde {df.index[0]} hasta {df.index[-1]}")
    
    # Crear estrategia
    strategy = AggressiveRegimeStrategy()
    strategy.set_parameters(test_params)
    
    # Crear backtester
    backtester = Backtester(df, initial_balance=1000.0)
    
    # Ejecutar backtest
    logger.info("Ejecutando backtest...")
    metrics = await backtester.run(strategy)
    
    # Analizar trades
    trades = backtester.trades
    logger.info(f"📊 Total trades: {len(trades)}")
    
    if trades:
        buy_trades = [t for t in trades if t['type'] == 'BUY']
        sell_trades = [t for t in trades if t['type'] == 'SELL']
        
        logger.info(f"  📈 Compras: {len(buy_trades)}")
        logger.info(f"  📉 Ventas: {len(sell_trades)}")
        
        if buy_trades:
            logger.info(f"  💰 Primera compra: ${buy_trades[0]['price']:.2f} en {buy_trades[0]['timestamp']}")
            logger.info(f"  💰 Última compra: ${buy_trades[-1]['price']:.2f} en {buy_trades[-1]['timestamp']}")
            
        if sell_trades:
            logger.info(f"  💸 Primera venta: ${sell_trades[0]['price']:.2f} en {sell_trades[0]['timestamp']}")
            logger.info(f"  💸 Última venta: ${sell_trades[-1]['price']:.2f} en {sell_trades[-1]['timestamp']}")
            
        # Calcular retornos por trade
        for i, buy in enumerate(buy_trades):
            if i < len(sell_trades):
                sell = sell_trades[i]
                trade_return = ((sell['price'] - buy['price']) / buy['price']) * 100
                logger.info(f"  🔄 Trade {i+1}: {trade_return:.2f}% ({buy['price']:.2f} → {sell['price']:.2f})")
    
    # Métricas finales
    logger.info(f"📋 Métricas finales:")
    for key, value in metrics.items():
        logger.info(f"  {key}: {value}")
    
    # Balance final
    logger.info(f"💼 Balance inicial: $1000.00")
    logger.info(f"💼 Balance final: ${backtester.balance:.2f}")
    logger.info(f"💼 Portfolio valor: ${backtester.get_portfolio_value(df['close'].iloc[-1]):.2f}")


if __name__ == "__main__":
    asyncio.run(debug_strategy())
