#!/usr/bin/env python3
"""
Sistema de Backtesting Multi-Capital con Debug Avanzado
Versión de debug para identificar errores de índice escalar
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_backtester import AdvancedBacktester
from multi_capital_backtester import MultiCapitalBacktester

def generate_trending_btc_data():
    """Genera datos de BTC con tendencia alcista para testing"""
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 3, 31)
    
    # Generar timestamps cada 4 horas
    timestamps = []
    current = start_date
    while current <= end_date:
        timestamps.append(current)
        current += timedelta(hours=4)
    
    # Precio base con tendencia alcista y volatilidad
    base_price = 20000
    prices = []
    
    for i, timestamp in enumerate(timestamps):
        # Tendencia alcista gradual
        trend = base_price + (i * 50)  # +$50 por período
        
        # Volatilidad aleatoria
        volatility = np.random.normal(0, 500)  # ±$500 de volatilidad
        
        price = max(trend + volatility, 15000)  # Precio mínimo de $15,000
        prices.append(price)
    
    # Crear DataFrame
    data = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': [p * 1.02 for p in prices],  # High 2% mayor
        'low': [p * 0.98 for p in prices],   # Low 2% menor
        'close': prices,
        'volume': np.random.uniform(1000, 5000, len(prices))
    })
    
    return data

def debug_adaptive_momentum_strategy(backtester, market_data, timestamp):
    """Estrategia de momentum adaptativa con debug extensivo"""
    
    print(f"\n🔍 DEBUG - Timestamp: {timestamp}")
    print(f"📊 Market data keys: {list(market_data.keys())}")
    
    if 'BTC' not in market_data:
        print("❌ DEBUG - No hay datos de BTC")
        return
    
    btc_data = market_data['BTC']
    print(f"📈 BTC data type: {type(btc_data)}")
    print(f"📈 BTC data shape: {btc_data.shape if hasattr(btc_data, 'shape') else 'No shape'}")
    print(f"📈 BTC data length: {len(btc_data) if hasattr(btc_data, '__len__') else 'No length'}")
    
    if len(btc_data) == 0:
        print("❌ DEBUG - DataFrame vacío")
        return
    
    print(f"📈 BTC data columns: {list(btc_data.columns)}")
    print(f"📈 BTC close type: {type(btc_data['close'])}")
    
    # Verificar si close es una Serie o un valor escalar
    if isinstance(btc_data['close'], pd.Series):
        print(f"✅ DEBUG - Close es una Serie con {len(btc_data['close'])} elementos")
        print(f"📈 Primeros valores: {btc_data['close'].head().tolist()}")
        print(f"📈 Últimos valores: {btc_data['close'].tail().tolist()}")
    else:
        print(f"⚠️ DEBUG - Close NO es una Serie: {btc_data['close']}")
        print(f"📈 Valor: {btc_data['close']}")
        return
    
    # Parámetros adaptativos basados en capital
    capital = backtester.initial_capital
    
    if capital <= 500:
        lookback = 5
        threshold = 0.02
        position_size = 0.8
    elif capital <= 1000:
        lookback = 10
        threshold = 0.015
        position_size = 0.6
    else:
        lookback = 15
        threshold = 0.01
        position_size = 0.4
    
    print(f"💰 Capital: ${capital}")
    print(f"🔍 Lookback: {lookback}")
    print(f"🎯 Threshold: {threshold}")
    print(f"📊 Position size: {position_size}")
    
    # Obtener precio actual con debug
    try:
        if len(btc_data) == 0:
            print("❌ DEBUG - No hay datos disponibles")
            return
        
        current_price = btc_data['close'].iloc[-1]
        print(f"💰 Precio actual: ${current_price:.2f}")
        
    except Exception as e:
        print(f"❌ DEBUG - Error obteniendo precio actual: {e}")
        print(f"❌ DEBUG - Tipo de error: {type(e)}")
        return
    
    # Verificar si tenemos suficientes datos para lookback
    if len(btc_data) < lookback:
        print(f"⚠️ DEBUG - Datos insuficientes: {len(btc_data)} < {lookback}")
        return
    
    # Obtener precio pasado con debug
    try:
        past_price = btc_data['close'].iloc[-lookback]
        print(f"📈 Precio pasado ({lookback} períodos): ${past_price:.2f}")
        
        price_change = (current_price - past_price) / past_price
        print(f"📊 Cambio de precio: {price_change:.4f} ({price_change*100:.2f}%)")
        
    except Exception as e:
        print(f"❌ DEBUG - Error obteniendo precio pasado: {e}")
        print(f"❌ DEBUG - Tipo de error: {type(e)}")
        return
    
    # Lógica de trading
    current_position = backtester.get_position('BTC')
    print(f"📊 Posición actual: {current_position}")
    
    # Señal de compra: momentum positivo
    if price_change > threshold and current_position == 0:
        order_size = backtester.available_capital * position_size / current_price
        print(f"🟢 SEÑAL DE COMPRA - Size: {order_size:.6f} BTC")
        
        if order_size > 0:
            backtester.place_order('BTC', 'buy', order_size)
            print(f"✅ Orden de compra colocada")
    
    # Señal de venta: momentum negativo o stop loss
    elif price_change < -threshold and current_position > 0:
        print(f"🔴 SEÑAL DE VENTA - Posición: {current_position}")
        backtester.place_order('BTC', 'sell', current_position)
        print(f"✅ Orden de venta colocada")
    
    print(f"🔍 DEBUG - Fin de estrategia\n")

def test_debug_strategy():
    """Prueba la estrategia con debug"""
    print("🚀 Iniciando test de estrategia con debug avanzado")
    
    # Generar datos de prueba
    btc_data = generate_trending_btc_data()
    print(f"📊 Datos generados: {len(btc_data)} registros")
    print(f"📈 Rango de fechas: {btc_data['timestamp'].min()} a {btc_data['timestamp'].max()}")
    print(f"💰 Rango de precios: ${btc_data['close'].min():.2f} - ${btc_data['close'].max():.2f}")
    
    # Configurar backtester
    backtester = AdvancedBacktester(
        initial_capital=1000.0,
        commission_rate=0.001
    )
    
    # Agregar datos de mercado
    backtester.load_market_data({'BTC': btc_data})
    
    print("\n🔬 Ejecutando backtest con debug...")    
    
    # Ejecutar backtest
    try:
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 3, 31)
        results = backtester.run_backtest(debug_adaptive_momentum_strategy, start_date, end_date)
        print(f"\n✅ Backtest completado")
        print(f"📊 Resultados: {results}")
        
    except Exception as e:
        print(f"\n❌ Error en backtest: {e}")
        print(f"❌ Tipo de error: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_debug_strategy()