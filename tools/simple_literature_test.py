#!/usr/bin/env python3
"""
Test simplificado de estrategias basadas en literatura
Solo usando la estrategia base con parámetros modificados
"""

import sys
import os
sys.path.append('/home/johan/itbot_linux')

from strategies.high_momentum_crypto_strategy import HighMomentumCryptoStrategy
from strategies.backtester import Backtester
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import asyncio

def generate_synthetic_crypto_data(symbol, days=60):
    """Generar datos sintéticos de crypto con patrones realistas"""
    # Configuración base por tipo de token
    if 'USDT' in symbol:
        base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 1.0
        volatility = 0.03 if 'BTC' in symbol else 0.04 if 'ETH' in symbol else 0.06
    else:
        base_price = 100
        volatility = 0.08  # Mayor volatilidad para altcoins
    
    # Generar timestamps
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    timestamps = pd.date_range(start=start_date, end=end_date, freq='1h')
    
    # Generar precios con tendencia y volatilidad
    np.random.seed(hash(symbol) % 2**32)  # Seed basada en símbolo para consistencia
    
    # Crear una tendencia sutil
    trend = np.linspace(1.0, 1.2, len(timestamps))  # 20% de tendencia alcista
    
    # Generar retornos con distribución realista
    returns = np.random.normal(0, volatility/24, len(timestamps))
    
    # Agregar algunos patrones de momentum
    for i in range(1, len(returns)):
        if abs(returns[i-1]) > volatility/12:  # Si hubo movimiento grande
            returns[i] += returns[i-1] * 0.3  # Continuar la dirección
    
    # Calcular precios
    price_multipliers = np.cumprod(1 + returns) * trend
    close_prices = base_price * price_multipliers
    
    # Generar OHLV
    open_prices = np.concatenate([[close_prices[0]], close_prices[:-1]])
    
    # High y Low con spread realista
    spreads = np.random.uniform(0.002, 0.01, len(timestamps))
    high_prices = np.maximum(open_prices, close_prices) * (1 + spreads)
    low_prices = np.minimum(open_prices, close_prices) * (1 - spreads)
    
    # Volumen correlacionado con volatilidad
    volatility_proxy = np.abs(returns)
    base_volume = 1000000
    volumes = base_volume * (1 + volatility_proxy * 50) * np.random.uniform(0.5, 2.0, len(timestamps))
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=timestamps)
    
    return df

def modify_strategy_for_literature(strategy, concept_name):
    """Modificar parámetros de estrategia según conceptos de literatura"""
    
    if concept_name == "ultra_scalping":
        # Conceptos de "5 Pasos Scalping Criptomonedas"
        strategy.take_profit_pct = 0.5   # 0.5% TP ultra conservador
        strategy.stop_loss_pct = 0.3     # 0.3% SL estricto
        strategy.volume_surge_multiplier = 3.0  # Más filtro de volumen
        strategy.rsi_momentum_threshold = 55    # Menos agresivo en RSI
        
    elif concept_name == "volatility_straddle":
        # Conceptos de "Trading Algorítmico - Volatilidad" 
        strategy.take_profit_pct = 8.0   # 8% TP para movimientos grandes
        strategy.stop_loss_pct = 4.0     # 4% SL
        strategy.bb_breakout_factor = 1.005  # Breakouts más conservadores
        strategy.volume_surge_multiplier = 2.0
        
    elif concept_name == "fibonacci_spiral":
        # Conceptos de "Espiral Logarítmica"
        strategy.take_profit_pct = 12.0  # 12% TP para ondas Elliott
        strategy.stop_loss_pct = 6.0     # 6% SL
        strategy.rsi_momentum_threshold = 65  # Más momentum requerido
        strategy.macd_patience_bars = 3       # Más confirmación
        
    elif concept_name == "multi_indicator":
        # Conceptos de "Sistemas Automáticos"
        strategy.take_profit_pct = 10.0  # 10% TP balanceado
        strategy.stop_loss_pct = 5.0     # 5% SL
        strategy.rsi_momentum_threshold = 60  # RSI balanceado
        strategy.volume_surge_multiplier = 1.5
        
    elif concept_name == "crypto_depth":
        # Conceptos de "Crypto Trading Pro"
        strategy.take_profit_pct = 6.0   # 6% TP crypto-específico
        strategy.stop_loss_pct = 3.0     # 3% SL
        strategy.volume_surge_multiplier = 4.0  # Detectar ballenas
        strategy.bb_breakout_factor = 1.008     # Breakouts más significativos

async def test_literature_concepts():
    """Probar conceptos de literatura con la estrategia base"""
    
    print("🚀 PROBANDO CONCEPTOS DE LITERATURA DE TRADING")
    print("=" * 70)
    
    # Tokens de prueba (enfoque en alta volatilidad)
    test_tokens = [
        'UNIUSDT', 'AAVEUSDT', 'COMPUSDT', 'MKRUSDT',
        'AXSUSDT', 'SANDUSDT', 'MANAUSDT', 'ENJUSDT',
        'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 'MATICUSDT',
        'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT',
        'FETUSDT', 'AGIXUSDT', 'OCEANUSDT'
    ]
    
    # Conceptos de literatura a probar
    literature_concepts = [
        ("ultra_scalping", "Ultra Scalping (5 Pasos)"),
        ("volatility_straddle", "Volatilidad Straddle"),
        ("fibonacci_spiral", "Espiral Fibonacci"),
        ("multi_indicator", "Multi-Indicador"),
        ("crypto_depth", "Crypto Market Depth")
    ]
    
    # Timeframes
    timeframes = ['5m', '15m', '30m', '1h']
    
    results = []
    
    for concept_key, concept_name in literature_concepts:
        print(f"\n📚 PROBANDO: {concept_name}")
        print("-" * 50)
        
        for timeframe in timeframes:
            print(f"\n⏱️  Timeframe: {timeframe}")
            
            for symbol in test_tokens[:10]:  # 10 tokens por concepto
                try:
                    # Generar datos sintéticos
                    historical_data = generate_synthetic_crypto_data(symbol, days=60)
                    
                    if len(historical_data) < 100:
                        continue
                    
                    # Crear estrategia y modificar parámetros
                    strategy = HighMomentumCryptoStrategy()
                    modify_strategy_for_literature(strategy, concept_key)
                    
                    # Configurar backtester
                    backtester = Backtester(
                        historical_data=historical_data,
                        initial_balance=1000,
                        symbol=symbol,
                        interval=timeframe,
                        commission=0.001
                    )
                    
                    # Ejecutar backtest
                    result = await backtester.run(strategy)
                    
                    if len(backtester.trades) > 0:
                        # Calcular estadísticas
                        trades_df = pd.DataFrame(backtester.trades)
                        
                        if 'pnl_pct' in trades_df.columns and len(trades_df) > 0:
                            total_return = trades_df['pnl_pct'].sum()
                            monthly_return = total_return
                            
                            winning_trades = trades_df[trades_df['pnl_pct'] > 0]
                            win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
                            
                            avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
                            losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
                            avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
                            
                            results.append({
                                'concept': concept_name,
                                'symbol': symbol,
                                'timeframe': timeframe,
                                'monthly_return_pct': monthly_return,
                                'total_return_pct': total_return,
                                'total_trades': len(trades_df),
                                'win_rate': win_rate,
                                'avg_win_pct': avg_win,
                                'avg_loss_pct': avg_loss
                            })
                            
                            status = "🟢 EXCELENTE" if monthly_return >= 15 else "🟡 BUENO" if monthly_return >= 10 else "🔴 BAJO"
                            print(f"    {symbol}: {monthly_return:.2f}% mensual {status}")
                            
                            if monthly_return >= 10:
                                print(f"      📊 {len(trades_df)} trades, {win_rate:.1f}% win rate")
                        
                except Exception as e:
                    print(f"    {symbol}: ❌ Error - {str(e)[:40]}")
                    continue
    
    # Análisis de resultados
    print("\n" + "="*70)
    print("📊 ANÁLISIS DE RESULTADOS - CONCEPTOS DE LITERATURA")
    print("="*70)
    
    if results:
        df_results = pd.DataFrame(results)
        
        # Mejores por concepto
        print("\n🏆 MEJORES RESULTADOS POR CONCEPTO:")
        for concept in df_results['concept'].unique():
            concept_results = df_results[df_results['concept'] == concept]
            if len(concept_results) > 0:
                best = concept_results.loc[concept_results['monthly_return_pct'].idxmax()]
                
                print(f"\n📈 {concept}:")
                print(f"   🥇 Mejor: {best['symbol']} - {best['monthly_return_pct']:.2f}% mensual")
                print(f"   📊 {best['timeframe']} | {best['total_trades']} trades | {best['win_rate']:.1f}% win rate")
        
        # Top 10 general
        print(f"\n🚀 TOP 10 CONFIGURACIONES GENERALES:")
        top_10 = df_results.nlargest(10, 'monthly_return_pct')
        
        for i, (_, row) in enumerate(top_10.iterrows(), 1):
            print(f"{i:2d}. {row['concept'][:25]:<25} | {row['symbol']:<8} | {row['timeframe']:<4} | {row['monthly_return_pct']:6.2f}%")
        
        # Estadísticas
        successful = df_results[df_results['monthly_return_pct'] >= 15]
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   • Total configuraciones: {len(results)}")
        print(f"   • Configuraciones 15%+: {len(successful)}")
        print(f"   • Mejor resultado: {df_results['monthly_return_pct'].max():.2f}%")
        print(f"   • Promedio: {df_results['monthly_return_pct'].mean():.2f}%")
        
        if len(successful) > 0:
            print(f"\n🎯 MEJORES CONCEPTOS (15%+):")
            best_concepts = successful.groupby('concept')['monthly_return_pct'].count().sort_values(ascending=False)
            for concept, count in best_concepts.items():
                print(f"   • {concept}: {count} configuraciones exitosas")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'/home/johan/itbot_linux/data/literatura_concepts_{timestamp}.json'
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'objective': '15% monthly return',
            'literature_sources': [
                '5 Pasos para Realizar Scalping Criptomonedas',
                'Trading Algorítmico - Estrategia Basada en Volatilidad', 
                'Trading Avanzado - La Espiral Logarítmica',
                'Análisis Técnico: Sistemas Automáticos',
                'Crypto Trading Pro'
            ],
            'concepts_tested': len(literature_concepts),
            'total_configurations': len(results),
            'results': results
        }, f, indent=2)
    
    print(f"\n💾 Resultados guardados en: {results_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_literature_concepts())
