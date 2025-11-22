#!/usr/bin/env python3
"""
Debug simple para identificar el error de índice escalar
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_backtester import AdvancedBacktester

def generate_simple_data():
    """Genera datos simples para testing"""
    dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='4H')
    prices = np.random.uniform(20000, 25000, len(dates))
    
    data = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(100, 1000, len(dates))
    })
    
    return data

def simple_strategy(historical_data, current_capital, positions):
    """Estrategia muy simple para debug"""
    print(f"\n🔍 DEBUG - Datos recibidos:")
    print(f"   Tipo de historical_data: {type(historical_data)}")
    
    if isinstance(historical_data, dict):
        for symbol, data in historical_data.items():
            print(f"   {symbol}: {type(data)}, shape: {data.shape if hasattr(data, 'shape') else 'N/A'}")
            if hasattr(data, 'shape') and len(data) > 0:
                print(f"   Últimas 3 filas de {symbol}:")
                print(data.tail(3))
                
                # Intentar acceder al precio actual
                try:
                    if len(data) > 0:
                        current_price = data['close'].iloc[-1]
                        print(f"   ✅ Precio actual de {symbol}: {current_price}")
                    else:
                        print(f"   ⚠️ DataFrame vacío para {symbol}")
                except Exception as e:
                    print(f"   ❌ Error accediendo al precio de {symbol}: {e}")
                    print(f"   Tipo de data['close']: {type(data['close'])}")
                    if hasattr(data['close'], 'shape'):
                        print(f"   Shape de data['close']: {data['close'].shape}")
    
    return []  # No hacer trades, solo debug

def main():
    print("🚀 Iniciando debug simple")
    
    # Generar datos simples
    btc_data = generate_simple_data()
    print(f"📊 Datos generados: {len(btc_data)} registros")
    
    # Configurar backtester
    backtester = AdvancedBacktester(
        initial_capital=1000.0,
        commission_rate=0.001
    )
    
    # Cargar datos
    backtester.load_market_data({'BTC': btc_data})
    
    # Ejecutar backtest
    try:
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 1, 10)
        print(f"\n🔬 Ejecutando backtest desde {start_date} hasta {end_date}")
        
        results = backtester.run_backtest(simple_strategy, start_date, end_date)
        print(f"\n✅ Backtest completado exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error en backtest: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()