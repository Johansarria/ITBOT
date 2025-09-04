#!/usr/bin/env python3
"""
Test de Momentum en Múltiples Criptos de Alto Rendimiento
Integra el sistema de selección dinámica con la estrategia de momentum
para encontrar los pares que generen 20%+ mensual
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Imports locales
from strategies.high_momentum_crypto_strategy import HighMomentumCryptoStrategy
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


async def get_top_volume_pairs(limit=20) -> List[str]:
    """Obtiene los pares USDT con mayor volumen (proxy para mejores cryptos)"""
    try:
        client = await get_binance_client()
        
        # Obtener ticker stats 24h
        ticker_stats = await client.get_ticker()
        
        # Filtrar solo pares USDT
        usdt_pairs = [
            ticker for ticker in ticker_stats 
            if ticker['symbol'].endswith('USDT') and 
            float(ticker['quoteVolume']) > 5000000  # Min $5M volumen
        ]
        
        # Ordenar por volumen descendente
        usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        
        # Extraer símbolos
        top_symbols = [pair['symbol'] for pair in usdt_pairs[:limit]]
        
        logger.info(f"Top {len(top_symbols)} pares USDT por volumen:")
        for i, symbol in enumerate(top_symbols[:10]):
            volume = float([p for p in usdt_pairs if p['symbol'] == symbol][0]['quoteVolume']) / 1e6
            logger.info(f"  {i+1}. {symbol}: ${volume:.1f}M volumen 24h")
        
        return top_symbols
        
    except Exception as e:
        logger.error(f"Error obteniendo top pairs: {e}")
        # Fallback a pares conocidos con alto rendimiento
        return [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT',
            'MATICUSDT', 'ARBUSDT', 'LINKUSDT', 'AVAXUSDT', 'ATOMUSDT',
            'NEARUSDT', 'FTMUSDT', 'MANAUSDT', 'SANDUSDT', 'ALGOUSDT'
        ]


async def test_symbol_momentum(symbol: str, strategy_params: Dict, interval='1h', lookback_days=45) -> Dict:
    """Test estrategia de momentum en un símbolo específico"""
    
    try:
        # Calcular límite basado en timeframe
        if interval == '1h':
            limit = lookback_days * 24
        elif interval == '4h':
            limit = lookback_days * 6
        elif interval == '1d':
            limit = lookback_days
        else:
            limit = 1000
            
        # Cargar datos
        klines = await fetch_klines(symbol=symbol, interval=interval, limit=min(limit, 1000))
        
        if len(klines) < 30:
            return {'symbol': symbol, 'error': 'Insufficient data', 'meets_target': False}
        
        # Procesar con FeaturePipeline
        pipeline = FeaturePipeline()
        df = pipeline.transform(klines)
        
        # Crear estrategia
        strategy = HighMomentumCryptoStrategy()
        strategy.set_parameters(strategy_params)
        
        # Crear backtester
        backtester = Backtester(df, initial_balance=1000.0)
        
        # Ejecutar backtest
        metrics = await backtester.run(strategy)
        
        # Calcular métricas
        total_days = max((df.index[-1] - df.index[0]).days, 1)
        total_return = metrics.get('total_return_pct', 0)
        monthly_equivalent = calculate_monthly_return_rate(total_return, total_days)
        
        # Stats
        total_trades = metrics.get('total_trades', 0)
        win_rate = metrics.get('win_rate_pct', 0)
        trades_list = metrics.get('trades', [])
        profitable_trades = len([t for t in trades_list if t.get('pnl', 0) > 0])
        
        # Calcular precio de cambio del período
        price_change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
        
        result = {
            'symbol': symbol,
            'interval': interval,
            'total_return': total_return,
            'monthly_equivalent': monthly_equivalent,
            'price_change_period': price_change,
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': win_rate,
            'meets_target': monthly_equivalent >= 20.0,
            'days_tested': total_days,
            'data_points': len(df)
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error testing {symbol}: {str(e)}")
        return {'symbol': symbol, 'error': str(e), 'meets_target': False}


async def multi_crypto_momentum_test():
    """Test de momentum en múltiples criptos de alto rendimiento"""
    
    logger.info("=== MULTI-CRYPTO MOMENTUM TEST ===")
    logger.info("Buscando 20%+ mensual en criptos de alto rendimiento")
    
    # Configuración de estrategia optimizada para momentum
    momentum_params = {
        'rsi_period': 14,
        'rsi_momentum_threshold': 55,  # Más permisivo para crypto
        'rsi_entry_min': 40,
        'rsi_entry_max': 80,
        'bb_period': 16,               # Más responsive
        'bb_std': 1.8,
        'bb_breakout_factor': 1.003,   # 0.3% breakout
        'volume_surge_multiplier': 1.5, # 50% surge
        'take_profit_pct': 4.0,        # 4% TP
        'stop_loss_pct': 2.0,          # 2% SL
        'trailing_stop_pct': 1.5       # 1.5% trailing
    }
    
    # Obtener top pares por volumen
    logger.info("Obteniendo top pares USDT por volumen...")
    top_pairs = await get_top_volume_pairs(limit=15)
    
    # Test en múltiples timeframes
    intervals_to_test = ['1h', '4h']
    
    all_results = []
    
    for interval in intervals_to_test:
        logger.info(f"\n📊 Testing interval {interval}...")
        
        # Test cada símbolo
        for i, symbol in enumerate(top_pairs[:10]):  # Top 10 para ser rápido
            logger.info(f"  Testing {symbol} ({i+1}/10)...")
            
            result = await test_symbol_momentum(
                symbol=symbol, 
                strategy_params=momentum_params, 
                interval=interval,
                lookback_days=30 if interval == '1h' else 45
            )
            
            result['test_interval'] = interval
            all_results.append(result)
            
            # Log resultado inmediato
            if 'error' in result:
                logger.warning(f"    ❌ {symbol}: {result['error']}")
            else:
                status = "✅ TARGET" if result['meets_target'] else "❌ Below"
                logger.info(f"    {status} {symbol}: {result['monthly_equivalent']:.1f}% mensual, {result['total_trades']} trades")
    
    # Análisis de resultados
    logger.info("\n=== ANÁLISIS DE RESULTADOS ===")
    
    # Filtrar resultados exitosos
    successful = [r for r in all_results if r.get('meets_target', False)]
    
    if successful:
        logger.info(f"🎉 ¡{len(successful)} configuraciones alcanzan 20%+ mensual!")
        
        # Ordenar por performance
        successful.sort(key=lambda x: x.get('monthly_equivalent', 0), reverse=True)
        
        logger.info("🏆 TOP PERFORMERS:")
        for i, result in enumerate(successful[:5]):
            logger.info(f"  {i+1}. {result['symbol']} ({result['test_interval']}): {result['monthly_equivalent']:.1f}% mensual")
            logger.info(f"     📊 {result['total_trades']} trades, {result['win_rate']:.1f}% win rate")
            logger.info(f"     📈 Precio cambió {result['price_change_period']:.1f}% en período")
        
        # Mejor resultado absoluto
        best = max(successful, key=lambda x: x.get('monthly_equivalent', 0))
        logger.info(f"\n🥇 CAMPEÓN ABSOLUTO: {best['symbol']} en {best['test_interval']}")
        logger.info(f"📊 {best['monthly_equivalent']:.2f}% retorno mensual equivalente")
        logger.info(f"📈 {best['total_return']:.2f}% retorno total en {best['days_tested']} días")
        logger.info(f"🎯 {best['total_trades']} trades, {best['profitable_trades']} profitable")
        logger.info(f"🏅 {best['win_rate']:.1f}% win rate")
        
        # Guardar configuración ganadora
        winner_config = {
            'symbol': best['symbol'],
            'interval': best['test_interval'],
            'strategy': 'HighMomentumCryptoStrategy',
            'params': momentum_params,
            'performance': {
                'monthly_return': best['monthly_equivalent'],
                'total_return': best['total_return'],
                'win_rate': best['win_rate'],
                'total_trades': best['total_trades']
            },
            'test_date': datetime.now().isoformat(),
            'target_achieved': True
        }
        
        with open('data/winning_momentum_config.json', 'w') as f:
            json.dump(winner_config, f, indent=2)
        
        logger.info(f"💾 Configuración ganadora guardada en data/winning_momentum_config.json")
        
    else:
        logger.warning("❌ Ningún par alcanza el target de 20% mensual")
        
        # Analizar mejores intentos
        valid_results = [r for r in all_results if 'error' not in r]
        if valid_results:
            valid_results.sort(key=lambda x: x.get('monthly_equivalent', -100), reverse=True)
            
            logger.info("💡 TOP 5 MEJORES INTENTOS:")
            for i, result in enumerate(valid_results[:5]):
                logger.info(f"  {i+1}. {result['symbol']} ({result['test_interval']}): {result['monthly_equivalent']:.1f}% mensual")
                logger.info(f"     📊 {result['total_trades']} trades, {result['win_rate']:.1f}% win rate")
    
    # Resumen por timeframe
    logger.info("\n📊 RESUMEN POR TIMEFRAME:")
    for interval in intervals_to_test:
        interval_results = [r for r in all_results if r.get('test_interval') == interval and 'error' not in r]
        if interval_results:
            avg_return = np.mean([r['monthly_equivalent'] for r in interval_results])
            best_return = max(r['monthly_equivalent'] for r in interval_results)
            successful_count = len([r for r in interval_results if r['meets_target']])
            
            logger.info(f"  {interval}: Avg {avg_return:.1f}%, Best {best_return:.1f}%, {successful_count}/{len(interval_results)} exitosos")


if __name__ == "__main__":
    asyncio.run(multi_crypto_momentum_test())
