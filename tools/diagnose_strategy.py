#!/usr/bin/env python3
"""
Diagnóstico de por qué no se generan trades
"""

import sys
import os
sys.path.append('/home/johan/itbot_linux')

from strategies.high_momentum_crypto_strategy import HighMomentumCryptoStrategy
from strategies.backtester import Backtester
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta

def generate_high_momentum_data(symbol="TESTUSDT", days=60):
    """Generar datos sintéticos con momentum claro"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    timestamps = pd.date_range(start=start_date, end=end_date, freq='1h')
    
    base_price = 100
    
    # Generar una tendencia alcista clara con breakouts
    n = len(timestamps)
    
    # Tendencia base fuerte
    trend = np.linspace(1.0, 1.5, n)  # 50% de crecimiento
    
    # Agregar volatilidad con momentum
    volatility = 0.02
    returns = np.random.normal(0, volatility, n)
    
    # Agregar algunos breakouts claros
    for i in range(100, n, 200):  # Cada 200 horas un breakout
        if i < n - 20:
            # Crear un patrón de breakout
            for j in range(20):
                if i + j < n:
                    returns[i + j] += 0.01  # +1% por hora durante 20 horas
    
    # Calcular precios
    price_multipliers = np.cumprod(1 + returns) * trend
    close_prices = base_price * price_multipliers
    
    # Generar OHLV con spreads
    open_prices = np.concatenate([[close_prices[0]], close_prices[:-1]])
    
    spreads = 0.005  # 0.5% spread fijo
    high_prices = np.maximum(open_prices, close_prices) * (1 + spreads)
    low_prices = np.minimum(open_prices, close_prices) * (1 - spreads)
    
    # Volumen alto durante breakouts
    base_volume = 1000000
    volumes = []
    for i in range(n):
        if i > 0 and abs(returns[i]) > 0.008:  # Durante movimientos grandes
            vol = base_volume * 3  # Triple volumen
        else:
            vol = base_volume * np.random.uniform(0.8, 1.2)
        volumes.append(vol)
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=timestamps)
    
    return df

async def diagnose_strategy():
    """Diagnosticar por qué no se generan trades"""
    
    print("🔍 DIAGNÓSTICO DE ESTRATEGIA")
    print("=" * 50)
    
    # Generar datos con momentum claro
    historical_data = generate_high_momentum_data("TESTUSDT", days=30)
    print(f"📊 Datos generados: {len(historical_data)} registros")
    print(f"📈 Precio inicial: {historical_data['close'].iloc[0]:.2f}")
    print(f"📈 Precio final: {historical_data['close'].iloc[-1]:.2f}")
    print(f"📈 Retorno total: {((historical_data['close'].iloc[-1] / historical_data['close'].iloc[0]) - 1) * 100:.2f}%")
    
    # Crear estrategia con parámetros más agresivos
    strategy = HighMomentumCryptoStrategy()
    
    # Hacer la estrategia más sensible
    strategy.take_profit_pct = 3.0    # 3% TP más alcanzable
    strategy.stop_loss_pct = 1.5      # 1.5% SL
    strategy.rsi_momentum_threshold = 50  # RSI menos restrictivo
    strategy.volume_surge_multiplier = 1.2  # Volumen menos restrictivo
    strategy.bb_breakout_factor = 1.001     # Breakout más sensible
    
    print(f"\n⚙️  PARÁMETROS DE ESTRATEGIA:")
    print(f"   • Take Profit: {strategy.take_profit_pct}%")
    print(f"   • Stop Loss: {strategy.stop_loss_pct}%")
    print(f"   • RSI Threshold: {strategy.rsi_momentum_threshold}")
    print(f"   • Volume Multiplier: {strategy.volume_surge_multiplier}")
    
    # Configurar backtester
    backtester = Backtester(
        historical_data=historical_data,
        initial_balance=1000,
        symbol="TESTUSDT",
        interval="1h",
        commission=0.001
    )
    
    print(f"\n🎯 EJECUTANDO BACKTEST...")
    result = await backtester.run(strategy)
    
    print(f"\n📊 RESULTADOS:")
    print(f"   • Trades ejecutados: {len(backtester.trades)}")
    print(f"   • Balance inicial: ${backtester.initial_balance}")
    print(f"   • Balance final: ${backtester.balance:.2f}")
    print(f"   • Retorno: {((backtester.balance / backtester.initial_balance) - 1) * 100:.2f}%")
    
    if len(backtester.trades) > 0:
        trades_df = pd.DataFrame(backtester.trades)
        print(f"\n💼 DETALLE DE TRADES:")
        print("Columnas disponibles:", list(trades_df.columns))
        print(trades_df.head())
        
        # Calcular estadísticas básicas
        if len(trades_df) > 1:
            print(f"\n📈 ESTADÍSTICAS BÁSICAS:")
            print(f"   • Total trades: {len(trades_df)}")
            
            # Buscar columnas de PnL
            pnl_cols = [col for col in trades_df.columns if 'pnl' in col.lower()]
            print(f"   • Columnas PnL encontradas: {pnl_cols}")
            
            if pnl_cols:
                pnl_col = pnl_cols[0]
                winning_trades = trades_df[trades_df[pnl_col] > 0]
                print(f"   • Trades ganadores: {len(winning_trades)}")
                print(f"   • Trades perdedores: {len(trades_df) - len(winning_trades)}")
                if len(trades_df) > 0:
                    print(f"   • Win rate: {(len(winning_trades) / len(trades_df) * 100):.1f}%")
                    print(f"   • PnL promedio: {trades_df[pnl_col].mean():.2f}%")
                    print(f"   • PnL total: {trades_df[pnl_col].sum():.2f}%")
    else:
        print("\n❌ NO SE GENERARON TRADES")
        print("Posibles causas:")
        print("   • Datos no cumplen criterios de entrada")
        print("   • Estrategia muy conservadora")
        print("   • Indicadores técnicos no alineados")
        
        # Analizar algunos puntos de datos
        print(f"\n🔍 ANÁLISIS DE DATOS:")
        sample_data = historical_data.tail(50)  # Últimos 50 registros
        
        # Calcular algunos indicadores manualmente
        closes = sample_data['close']
        volumes = sample_data['volume']
        
        # RSI simple
        deltas = closes.diff()
        gains = deltas.where(deltas > 0, 0).rolling(window=14).mean()
        losses = (-deltas.where(deltas < 0, 0)).rolling(window=14).mean()
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        
        print(f"   • RSI actual: {rsi.iloc[-1]:.2f}")
        print(f"   • RSI promedio: {rsi.mean():.2f}")
        print(f"   • Volumen promedio: {volumes.mean():.0f}")
        print(f"   • Volumen actual: {volumes.iloc[-1]:.0f}")
        print(f"   • Precio cambió: {((closes.iloc[-1] / closes.iloc[-10]) - 1) * 100:.2f}% en últimas 10 velas")

if __name__ == "__main__":
    asyncio.run(diagnose_strategy())
