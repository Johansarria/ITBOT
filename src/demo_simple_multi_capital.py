#!/usr/bin/env python3
"""
Demostración simplificada del sistema de backtesting multi-capital
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_capital_backtester import MultiCapitalBacktester
from advanced_backtester import OrderSide, OrderType

def create_simple_btc_data():
    """Crear datos de BTC simples"""
    dates = pd.date_range('2023-01-01', '2023-01-31', freq='1H')
    np.random.seed(42)
    
    # Datos simples con tendencia
    prices = []
    base_price = 20000
    
    for i in range(len(dates)):
        # Tendencia alcista con ruido
        trend = i * 0.5
        noise = np.random.normal(0, 100)
        price = base_price + trend + noise
        prices.append(max(price, 15000))  # Precio mínimo
    
    data = []
    for i, date in enumerate(dates):
        price = prices[i]
        data.append({
            'timestamp': date,
            'open': price * 0.999,
            'high': price * 1.002,
            'low': price * 0.998,
            'close': price,
            'volume': 1000
        })
    
    return pd.DataFrame(data)

def create_simple_strategy():
    """Crear estrategia simple"""
    
    def simple_strategy(backtester, market_data, timestamp):
        """Estrategia simple de comprar y mantener"""
        if 'BTCUSDT' not in market_data:
            return
        
        btc_data = market_data['BTCUSDT']
        if len(btc_data) < 10:
            return
        
        current_price = btc_data['close'].iloc[-1]
        
        # Comprar al inicio si no tenemos posición
        if (len(backtester.current_positions) == 0 and 
            backtester.current_capital > 100):
            
            quantity = (backtester.current_capital * 0.8) / current_price
            
            backtester.place_order(
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=quantity
            )
    
    return simple_strategy

def run_simple_analysis():
    """Ejecutar análisis simple"""
    
    print("🚀 ANÁLISIS SIMPLE MULTI-CAPITAL")
    print("=" * 50)
    
    try:
        # Crear datos simples
        print("📊 Generando datos simples...")
        btc_data = create_simple_btc_data()
        market_data = {'BTCUSDT': btc_data}
        
        print(f"✅ Datos generados: {len(btc_data)} velas")
        print(f"📈 Precio inicial: ${btc_data['close'].iloc[0]:.2f}")
        print(f"📈 Precio final: ${btc_data['close'].iloc[-1]:.2f}")
        
        # Configurar backtester
        print("\n🏦 Configurando backtester...")
        multi_backtester = MultiCapitalBacktester(
            capital_range=(200, 600),
            capital_steps=3,
            commission_rate=0.001
        )
        
        # Crear estrategia
        strategy = create_simple_strategy()
        
        # Ejecutar análisis
        print("\n🔄 Ejecutando análisis...")
        summary = multi_backtester.run_multi_capital_backtest(
            market_data=market_data,
            strategy_func=strategy,
            start_date='2023-01-01',
            end_date='2023-01-31',
            parallel=False
        )
        
        # Mostrar resultados
        print("\n📊 RESULTADOS:")
        print("-" * 30)
        
        for result in summary.capital_results:
            print(f"Capital: ${result.capital:.0f} | ROI: {result.roi_percentage:.2f}% | P&L: ${result.profit_loss:.2f}")
        
        print(f"\n📈 Mejor capital: ${summary.best_capital:.0f}")
        print(f"📉 Peor capital: ${summary.worst_capital:.0f}")
        print(f"🎯 Score escalabilidad: {summary.scalability_score:.1f}")
        
        print("\n✅ Análisis completado exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_simple_analysis()