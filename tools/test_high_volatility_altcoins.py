#!/usr/bin/env python3
"""
Test Altcoins de Alta Volatilidad
Enfocado en tokens con alta volatilidad que pueden generar 20%+ mensual
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


# Tokens de alta volatilidad basados en datos recientes
HIGH_VOLATILITY_TARGETS = [
    # Tokens con alta volatilidad reciente
    'CROUSUSDT',  # Cronos - +80.9% en 7 días
    'SKLUSDT',    # SKALE - +23.1% en 24h  
    'FLOWUSDT',   # Flow - +6.4% 
    'GALAUSDT',   # Gala - +1.6%
    'COREUSDT',   # Core - +4.0%
    'CHZUSDT',    # Chiliz - +2.7%
    'ONEUSDT',    # Harmony - +2.1%
    'WEMIXUSDT',  # Wemix - +4.3%
    'CROSSUSDT',  # Cross - +5.0%
    'GLMRUSDT',   # Moonbeam - +1.0%
    
    # Altcoins conocidas con historial de volatilidad
    'ADAUSDT',    # Cardano
    'MATICUSDT',  # Polygon (si aún existe)  
    'AVAXUSDT',   # Avalanche
    'DOTUSDT',    # Polkadot
    'ATOMUSDT',   # Cosmos
    'NEARUSDT',   # NEAR Protocol
    'FTMUSDT',    # Fantom
    'MANAUSDT',   # Decentraland
    'SANDUSDT',   # Sandbox
    'ALGOUSDT',   # Algorand
]


async def verify_symbol_exists(symbol: str) -> bool:
    """Verifica si un símbolo existe en Binance"""
    try:
        client = await get_binance_client()
        # Intenta obtener un ticker
        ticker = await client.get_ticker(symbol=symbol)
        return ticker is not None
    except Exception:
        return False


async def test_high_volatility_altcoins():
    """Test de altcoins de alta volatilidad para 20%+ mensual"""
    
    logger.info("=== HIGH VOLATILITY ALTCOINS TEST ===")
    logger.info("Buscando 20%+ mensual en altcoins de alta volatilidad")
    
    # Configuración agresiva para altcoins volátiles
    aggressive_params = {
        'rsi_period': 14,
        'rsi_momentum_threshold': 50,  # Más permisivo para altcoins
        'rsi_entry_min': 35,
        'rsi_entry_max': 85,
        'bb_period': 14,               # Más responsive para volatilidad
        'bb_std': 1.6,                # Más estrecho para capturar movimientos
        'bb_breakout_factor': 1.005,   # 0.5% breakout
        'volume_surge_multiplier': 1.3, # 30% surge (altcoins menos líquidas)
        'take_profit_pct': 6.0,        # 6% TP para altcoins volátiles
        'stop_loss_pct': 3.0,          # 3% SL más amplio
        'trailing_stop_pct': 2.0       # 2% trailing
    }
    
    # Verificar y filtrar símbolos que existen
    logger.info("Verificando símbolos disponibles...")
    valid_symbols = []
    
    for symbol in HIGH_VOLATILITY_TARGETS:
        exists = await verify_symbol_exists(symbol)
        if exists:
            valid_symbols.append(symbol)
            logger.info(f"  ✅ {symbol} disponible")
        else:
            logger.warning(f"  ❌ {symbol} no disponible")
    
    logger.info(f"Testing {len(valid_symbols)} altcoins de alta volatilidad")
    
    # Configuración de test
    test_configs = [
        {'interval': '1h', 'lookback_days': 60, 'name': '1h_extended'},
        {'interval': '4h', 'lookback_days': 90, 'name': '4h_extended'},
        {'interval': '1d', 'lookback_days': 120, 'name': '1d_longterm'}
    ]
    
    all_results = []
    
    for config in test_configs:
        interval = config['interval']
        lookback_days = config['lookback_days']
        config_name = config['name']
        
        logger.info(f"\n📊 Testing configuración {config_name} ({interval}, {lookback_days} días)...")
        
        # Test cada símbolo
        for i, symbol in enumerate(valid_symbols[:8]):  # Primeros 8 para ser eficiente
            logger.info(f"  Testing {symbol} ({i+1}/8)...")
            
            try:
                # Calcular límite basado en timeframe
                if interval == '1h':
                    limit = min(lookback_days * 24, 1000)
                elif interval == '4h':
                    limit = min(lookback_days * 6, 1000)
                elif interval == '1d':
                    limit = min(lookback_days, 1000)
                else:
                    limit = 1000
                    
                # Cargar datos
                klines = await fetch_klines(symbol=symbol, interval=interval, limit=limit)
                
                if len(klines) < 30:
                    logger.warning(f"    ❌ {symbol}: Datos insuficientes ({len(klines)} velas)")
                    continue
                
                # Procesar con FeaturePipeline
                pipeline = FeaturePipeline()
                df = pipeline.transform(klines)
                
                # Crear estrategia
                strategy = HighMomentumCryptoStrategy()
                strategy.set_parameters(aggressive_params)
                
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
                
                # Calcular volatilidad del período
                price_std = df['close'].pct_change().std() * 100  # Volatilidad diaria en %
                price_change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100
                
                result = {
                    'symbol': symbol,
                    'config': config_name,
                    'interval': interval,
                    'total_return': total_return,
                    'monthly_equivalent': monthly_equivalent,
                    'price_change_period': price_change,
                    'volatility_daily_pct': price_std,
                    'total_trades': total_trades,
                    'profitable_trades': profitable_trades,
                    'win_rate': win_rate,
                    'meets_target': monthly_equivalent >= 20.0,
                    'days_tested': total_days,
                    'data_points': len(df)
                }
                
                all_results.append(result)
                
                # Log resultado inmediato
                status = "🎯 TARGET HIT" if result['meets_target'] else "❌ Below"
                logger.info(f"    {status} {symbol}: {result['monthly_equivalent']:.1f}% mensual")
                logger.info(f"         📊 {result['total_trades']} trades, {result['win_rate']:.1f}% win, {result['volatility_daily_pct']:.2f}% vol diaria")
                
            except Exception as e:
                logger.error(f"    ❌ {symbol}: Error - {str(e)}")
                all_results.append({
                    'symbol': symbol,
                    'config': config_name,
                    'error': str(e),
                    'meets_target': False
                })
    
    # ANÁLISIS FINAL
    logger.info("\n🏆 === ANÁLISIS FINAL DE ALTCOINS ===")
    
    # Filtrar resultados exitosos
    successful = [r for r in all_results if r.get('meets_target', False)]
    
    if successful:
        logger.info(f"🎉 ¡{len(successful)} configuraciones de altcoins alcanzan 20%+ mensual!")
        
        # Ordenar por performance
        successful.sort(key=lambda x: x.get('monthly_equivalent', 0), reverse=True)
        
        logger.info("🥇 ALTCOINS GANADORAS:")
        for i, result in enumerate(successful[:3]):
            logger.info(f"  {i+1}. {result['symbol']} ({result['config']}): {result['monthly_equivalent']:.1f}% mensual")
            logger.info(f"     📊 {result['total_trades']} trades, {result['win_rate']:.1f}% win rate")
            logger.info(f"     📈 {result['total_return']:.1f}% total return en {result['days_tested']} días")
            logger.info(f"     💹 {result['volatility_daily_pct']:.2f}% volatilidad diaria")
        
        # Campeón absoluto
        champion = max(successful, key=lambda x: x.get('monthly_equivalent', 0))
        logger.info(f"\n👑 ALTCOIN CAMPEÓN: {champion['symbol']} en {champion['config']}")
        logger.info(f"🎯 {champion['monthly_equivalent']:.2f}% retorno mensual equivalente")
        logger.info(f"📈 {champion['total_return']:.2f}% retorno total")
        logger.info(f"🏅 {champion['win_rate']:.1f}% win rate con {champion['total_trades']} trades")
        logger.info(f"💎 {champion['volatility_daily_pct']:.2f}% volatilidad diaria promedio")
        
        # Guardar configuración ganadora
        winner_config = {
            'symbol': champion['symbol'],
            'interval': champion['interval'],
            'config_name': champion['config'],
            'strategy': 'HighMomentumCryptoStrategy',
            'params': aggressive_params,
            'performance': {
                'monthly_return': champion['monthly_equivalent'],
                'total_return': champion['total_return'],
                'win_rate': champion['win_rate'],
                'total_trades': champion['total_trades'],
                'volatility_daily': champion['volatility_daily_pct']
            },
            'test_date': datetime.now().isoformat(),
            'target_achieved': True,
            'category': 'high_volatility_altcoin'
        }
        
        # Guardar
        os.makedirs('data', exist_ok=True)
        with open('data/winning_altcoin_config.json', 'w') as f:
            json.dump(winner_config, f, indent=2)
        
        logger.info(f"💾 Configuración ganadora guardada en data/winning_altcoin_config.json")
        
    else:
        logger.warning("❌ Ninguna altcoin alcanza el target de 20% mensual")
        
        # Analizar mejores intentos
        valid_results = [r for r in all_results if 'error' not in r]
        if valid_results:
            valid_results.sort(key=lambda x: x.get('monthly_equivalent', -100), reverse=True)
            
            logger.info("💡 TOP 5 ALTCOINS CON MEJOR PERFORMANCE:")
            for i, result in enumerate(valid_results[:5]):
                logger.info(f"  {i+1}. {result['symbol']} ({result['config']}): {result['monthly_equivalent']:.1f}% mensual")
                logger.info(f"     📊 {result['total_trades']} trades, {result['win_rate']:.1f}% win, Vol: {result.get('volatility_daily_pct', 0):.2f}%")
    
    # Resumen por configuración
    logger.info("\n📊 RESUMEN POR CONFIGURACIÓN:")
    for config in test_configs:
        config_name = config['name']
        config_results = [r for r in all_results if r.get('config') == config_name and 'error' not in r]
        if config_results:
            avg_return = np.mean([r['monthly_equivalent'] for r in config_results])
            best_return = max(r['monthly_equivalent'] for r in config_results)
            successful_count = len([r for r in config_results if r['meets_target']])
            avg_volatility = np.mean([r.get('volatility_daily_pct', 0) for r in config_results])
            
            logger.info(f"  {config_name}: Avg {avg_return:.1f}%, Best {best_return:.1f}%, {successful_count}/{len(config_results)} exitosos, Vol: {avg_volatility:.2f}%")


if __name__ == "__main__":
    asyncio.run(test_high_volatility_altcoins())
