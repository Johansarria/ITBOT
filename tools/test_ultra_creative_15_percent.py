#!/usr/bin/env python3
"""
Exploración Avanzada para 15%+ Mensual
Estrategias ultra-agresivas y creativas para mercados laterales
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
import random

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
    
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume',
                                      'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                                      'taker_buy_quote', 'ignore'])
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    
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


class UltraScalpingStrategy:
    """Estrategia de scalping ultra-agresiva para mercados laterales"""
    
    def __init__(self):
        self.name = "UltraScalpingStrategy"
        self.params = {
            'rsi_period': 7,
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'bb_period': 8,
            'bb_std': 1.2,
            'take_profit_pct': 0.4,  # 0.4% TP ultra-pequeño
            'stop_loss_pct': 0.8,    # 0.8% SL amplio
            'volume_multiplier': 1.1  # 10% incremento volumen
        }
    
    def set_parameters(self, params):
        self.params.update(params)
    
    async def analyze(self, df):
        """Análisis ultra-agresivo de scalping"""
        if len(df) < 20:
            return 'MANTENER'
        
        # RSI ultra-responsive
        rsi = df['rsi_14'].iloc[-1] if 'rsi_14' in df.columns else 50
        
        # Bollinger Bands estrechas
        bb_upper = df['bb_upper_20'].iloc[-1] if 'bb_upper_20' in df.columns else df['close'].iloc[-1] * 1.01
        bb_lower = df['bb_lower_20'].iloc[-1] if 'bb_lower_20' in df.columns else df['close'].iloc[-1] * 0.99
        price = df['close'].iloc[-1]
        
        # Volumen
        vol_avg = df['volume'].rolling(10).mean().iloc[-1]
        vol_current = df['volume'].iloc[-1]
        
        # Lógica ultra-agresiva
        if (rsi < self.params['rsi_oversold'] and 
            price <= bb_lower * 1.002 and 
            vol_current > vol_avg * self.params['volume_multiplier']):
            return 'COMPRAR_AGRESIVO'
        
        if (rsi > self.params['rsi_overbought'] and 
            price >= bb_upper * 0.998):
            return 'VENDER'
        
        # Momentum micro-scalping
        price_change_1m = ((price - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100
        if abs(price_change_1m) > 0.1 and vol_current > vol_avg * 1.5:
            return 'COMPRAR_AGRESIVO' if price_change_1m > 0 else 'VENDER'
        
        return 'MANTENER'


# Tokens con patrones únicos para exploración
EXPERIMENTAL_TOKENS = [
    # DeFi con alta actividad
    'UNIUSDT', 'AAVEUSDT', 'CRVUSDT', 'COMPUSDT', 
    'MKRUSDT', 'YFIUSDT', 'SNXUSDT', 'SUSHIUSDT',
    
    # Gaming/Metaverse volatility
    'AXSUSDT', 'MANAUSDT', 'SANDUSDT', 'ENJUSDT',
    'GALAUSDT', 'CHZUSDT', 'FLOWUSDT',
    
    # Layer 1/2 emergentes  
    'ARBUSDT', 'OPUSDT', 'MATICUSDT', 'AVAXUSDT',
    'FTMUSDT', 'ADAUSDT', 'DOTUSDT', 'ATOMUSDT',
    
    # Meme coins alta volatilidad
    'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT',
    'BONKUSDT', 'WIFUSDT',
    
    # AI/Oracle
    'LINKUSDT', 'FETUSDT', 'OCEANUSDT', 'AGIXUSDT'
]


async def verify_symbol_exists(symbol: str) -> bool:
    """Verifica si un símbolo existe en Binance"""
    try:
        client = await get_binance_client()
        ticker = await client.get_ticker(symbol=symbol)
        return ticker is not None
    except Exception:
        return False


async def test_ultra_creative_strategies():
    """Test ultra-creativo para alcanzar 15%+ mensual"""
    
    logger.info("=== EXPLORACIÓN ULTRA-CREATIVA PARA 15%+ MENSUAL ===")
    logger.info("Probando estrategias experimentales en mercados laterales")
    
    # Configuraciones experimentales
    experimental_configs = [
        {
            'name': 'micro_scalping',
            'strategy_class': UltraScalpingStrategy,
            'params': {
                'rsi_period': 5,
                'rsi_oversold': 20,
                'rsi_overbought': 80,
                'take_profit_pct': 0.3,
                'stop_loss_pct': 0.6,
                'volume_multiplier': 1.2
            },
            'intervals': ['5m', '15m'],
            'lookback_days': [15, 30]
        },
        {
            'name': 'extreme_momentum',
            'strategy_class': HighMomentumCryptoStrategy,
            'params': {
                'rsi_period': 8,
                'rsi_momentum_threshold': 40,
                'rsi_entry_min': 25,
                'rsi_entry_max': 95,
                'bb_period': 10,
                'bb_std': 1.0,
                'bb_breakout_factor': 1.001,
                'volume_surge_multiplier': 1.1,
                'take_profit_pct': 12.0,  # 12% TP extremo
                'stop_loss_pct': 6.0,     # 6% SL
                'trailing_stop_pct': 4.0  # 4% trailing
            },
            'intervals': ['15m', '1h'],
            'lookback_days': [20, 45]
        },
        {
            'name': 'volatility_hunter',
            'strategy_class': HighMomentumCryptoStrategy,
            'params': {
                'rsi_period': 6,
                'rsi_momentum_threshold': 35,
                'rsi_entry_min': 20,
                'rsi_entry_max': 90,
                'bb_period': 8,
                'bb_std': 0.8,
                'bb_breakout_factor': 1.0005,
                'volume_surge_multiplier': 1.05,
                'take_profit_pct': 15.0,  # 15% TP cazador volatilidad
                'stop_loss_pct': 8.0,     # 8% SL
                'trailing_stop_pct': 5.0  # 5% trailing
            },
            'intervals': ['1h', '4h'],
            'lookback_days': [30, 60]
        }
    ]
    
    # Verificar tokens disponibles
    logger.info("Verificando tokens experimentales...")
    valid_tokens = []
    for token in EXPERIMENTAL_TOKENS[:15]:  # Primeros 15
        exists = await verify_symbol_exists(token)
        if exists:
            valid_tokens.append(token)
            logger.info(f"  ✅ {token}")
        else:
            logger.warning(f"  ❌ {token} no disponible")
    
    if len(valid_tokens) < 5:
        logger.error("❌ Tokens insuficientes para testing")
        return False
    
    all_results = []
    success_found = False
    
    for config in experimental_configs:
        config_name = config['name']
        strategy_class = config['strategy_class']
        base_params = config['params']
        intervals = config['intervals']
        lookback_days_list = config['lookback_days']
        
        logger.info(f"\n🚀 TESTING ESTRATEGIA: {config_name.upper()}")
        
        # Combinaciones de timeframe y lookback
        for interval in intervals:
            for lookback_days in lookback_days_list:
                combo_name = f"{config_name}_{interval}_{lookback_days}d"
                logger.info(f"  🎯 Combo: {combo_name}")
                
                # Seleccionar tokens aleatorios para diversidad
                selected_tokens = random.sample(valid_tokens, min(8, len(valid_tokens)))
                
                for i, token in enumerate(selected_tokens):
                    try:
                        # Calcular límite
                        if interval == '5m':
                            limit = min(lookback_days * 288, 1000)  # 288 = 24*12
                        elif interval == '15m':
                            limit = min(lookback_days * 96, 1000)   # 96 = 24*4
                        elif interval == '1h':
                            limit = min(lookback_days * 24, 1000)
                        elif interval == '4h':
                            limit = min(lookback_days * 6, 1000)
                        else:
                            limit = 1000
                        
                        # Cargar datos
                        klines = await fetch_klines(symbol=token, interval=interval, limit=limit)
                        
                        if len(klines) < 50:
                            continue
                        
                        # Procesar features
                        pipeline = FeaturePipeline()
                        df = pipeline.transform(klines)
                        
                        # Crear estrategia
                        if strategy_class == UltraScalpingStrategy:
                            strategy = UltraScalpingStrategy()
                        else:
                            strategy = HighMomentumCryptoStrategy()
                        
                        strategy.set_parameters(base_params)
                        
                        # Backtester
                        backtester = Backtester(df, initial_balance=1000.0)
                        metrics = await backtester.run(strategy)
                        
                        # Análisis
                        total_days = max((df.index[-1] - df.index[0]).days, 1)
                        total_return = metrics.get('total_return_pct', 0)
                        monthly_equivalent = calculate_monthly_return_rate(total_return, total_days)
                        
                        # Métricas adicionales
                        total_trades = metrics.get('total_trades', 0)
                        win_rate = metrics.get('win_rate_pct', 0)
                        max_drawdown = metrics.get('max_drawdown_pct', 0)
                        sharpe_ratio = metrics.get('sharpe_ratio', 0)
                        
                        # Volatilidad
                        volatility_daily = df['close'].pct_change().std() * 100
                        
                        result = {
                            'strategy': config_name,
                            'combo': combo_name,
                            'token': token,
                            'interval': interval,
                            'lookback_days': lookback_days,
                            'monthly_equivalent': monthly_equivalent,
                            'total_return': total_return,
                            'total_trades': total_trades,
                            'win_rate': win_rate,
                            'max_drawdown': max_drawdown,
                            'sharpe_ratio': sharpe_ratio,
                            'volatility_daily': volatility_daily,
                            'days_tested': total_days,
                            'meets_15_target': monthly_equivalent >= 15.0
                        }
                        
                        all_results.append(result)
                        
                        # Log inmediato
                        if result['meets_15_target']:
                            success_found = True
                            logger.info(f"    🎉 *** 15% TARGET HIT *** {token}: {monthly_equivalent:.1f}% mensual!")
                            logger.info(f"         🏆 Estrategia: {config_name} | {interval} | {lookback_days}d")
                            logger.info(f"         📊 {total_trades} trades, {win_rate:.1f}% win, DD: {max_drawdown:.1f}%")
                        else:
                            logger.info(f"    📈 {token}: {monthly_equivalent:.1f}% mensual ({config_name})")
                        
                    except Exception as e:
                        logger.error(f"    💥 {token}: Error - {str(e)}")
    
    # === ANÁLISIS FINAL ===
    logger.info("\n🏆 === ANÁLISIS FINAL ULTRA-CREATIVO ===")
    
    # Filtrar éxitos (15%+)
    successful_15 = [r for r in all_results if r.get('meets_15_target', False)]
    
    if successful_15:
        success_found = True
        logger.info(f"🎉 ¡¡¡ {len(successful_15)} CONFIGURACIONES ALCANZAN 15%+ MENSUAL !!!")
        
        # Ordenar por performance
        successful_15.sort(key=lambda x: x.get('monthly_equivalent', 0), reverse=True)
        
        logger.info("🥇 *** ESTRATEGIAS GANADORAS 15%+ ***")
        for i, result in enumerate(successful_15[:5]):
            logger.info(f"  {i+1}. 🏆 {result['token']} - {result['strategy']}")
            logger.info(f"     💰 {result['monthly_equivalent']:.1f}% RETORNO MENSUAL")
            logger.info(f"     ⚙️ Config: {result['combo']} ({result['interval']}, {result['lookback_days']}d)")
            logger.info(f"     📊 {result['total_trades']} trades, {result['win_rate']:.1f}% win")
            logger.info(f"     🛡️ DD: {result['max_drawdown']:.1f}%, Sharpe: {result['sharpe_ratio']:.2f}")
        
        # *** CAMPEÓN 15% ***
        champion = max(successful_15, key=lambda x: x.get('monthly_equivalent', 0))
        logger.info(f"\n👑 *** CAMPEÓN 15% MENSUAL ***")
        logger.info(f"🏆 TOKEN: {champion['token']}")
        logger.info(f"⚙️ ESTRATEGIA: {champion['strategy']}")
        logger.info(f"📅 CONFIG: {champion['combo']}")
        logger.info(f"💰 RETORNO MENSUAL: {champion['monthly_equivalent']:.2f}%")
        logger.info(f"📈 RETORNO TOTAL: {champion['total_return']:.2f}%")
        logger.info(f"🎯 {champion['total_trades']} trades, {champion['win_rate']:.1f}% win rate")
        logger.info(f"📊 Vol diaria: {champion['volatility_daily']:.2f}%")
        logger.info(f"🛡️ Max DD: {champion['max_drawdown']:.1f}%")
        
        # Guardar configuración ganadora
        winner_config = {
            'token': champion['token'],
            'strategy': champion['strategy'],
            'combo': champion['combo'],
            'interval': champion['interval'],
            'lookback_days': champion['lookback_days'],
            'performance': {
                'monthly_return': champion['monthly_equivalent'],
                'total_return': champion['total_return'],
                'win_rate': champion['win_rate'],
                'total_trades': champion['total_trades'],
                'max_drawdown': champion['max_drawdown'],
                'sharpe_ratio': champion['sharpe_ratio']
            },
            'test_date': datetime.now().isoformat(),
            'target_achieved': '15_percent_monthly',
            'status': 'SUCCESS'
        }
        
        os.makedirs('data', exist_ok=True)
        with open('data/WINNER_15_PERCENT_CONFIG.json', 'w') as f:
            json.dump(winner_config, f, indent=2)
        
        logger.info(f"💾 *** CONFIGURACIÓN 15% GUARDADA en data/WINNER_15_PERCENT_CONFIG.json ***")
    
    else:
        # Analizar mejores intentos
        logger.warning("❌ No se alcanzó 15% mensual")
        
        # Mejores resultados
        valid_results = [r for r in all_results if 'monthly_equivalent' in r]
        if valid_results:
            valid_results.sort(key=lambda x: x.get('monthly_equivalent', -100), reverse=True)
            
            logger.info("🔝 TOP 10 MEJORES RESULTADOS:")
            for i, result in enumerate(valid_results[:10]):
                logger.info(f"  {i+1}. {result['token']} ({result['strategy']}): {result['monthly_equivalent']:.1f}% mensual")
                logger.info(f"     Config: {result['combo']}, {result['total_trades']} trades, {result['win_rate']:.1f}% win")
            
            # Análisis de mejores estrategias
            best = valid_results[0]
            logger.info(f"\n💡 MEJOR RESULTADO: {best['monthly_equivalent']:.1f}% mensual")
            logger.info(f"🎯 Token: {best['token']} | Estrategia: {best['strategy']}")
            logger.info(f"⚙️ Config: {best['combo']}")
    
    # Resumen por estrategia
    logger.info(f"\n📊 RESUMEN POR ESTRATEGIA:")
    for config in experimental_configs:
        config_name = config['name']
        strategy_results = [r for r in all_results if r.get('strategy') == config_name and 'monthly_equivalent' in r]
        
        if strategy_results:
            avg_return = np.mean([r['monthly_equivalent'] for r in strategy_results])
            best_return = max(r['monthly_equivalent'] for r in strategy_results)
            success_count = len([r for r in strategy_results if r.get('meets_15_target', False)])
            avg_trades = np.mean([r.get('total_trades', 0) for r in strategy_results])
            
            logger.info(f"  {config_name}:")
            logger.info(f"    💰 Promedio: {avg_return:.1f}%, Mejor: {best_return:.1f}%")
            logger.info(f"    🎯 {success_count}/{len(strategy_results)} exitosos")
            logger.info(f"    📊 Trades promedio: {avg_trades:.1f}")
    
    return success_found


if __name__ == "__main__":
    success = asyncio.run(test_ultra_creative_strategies())
    if success:
        print("\n🎉 *** ÉXITO: Estrategia de 15%+ mensual encontrada! ***")
    else:
        print("\n😔 *** Target de 15% mensual no alcanzado ***")
