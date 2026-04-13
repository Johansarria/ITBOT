#!/usr/bin/env python3
"""
Test rápido de la estrategia V4 Ultra
"""

import pandas as pd
import numpy as np
from enhanced_strategy_15pct_v4_ultra import Enhanced15PercentStrategyV4Ultra

def create_test_data():
    """Crear datos de prueba"""
    dates = pd.date_range('2024-01-01', periods=100, freq='1min')
    
    # Crear datos con tendencia y volatilidad
    base_price = 50000
    price_changes = np.random.normal(0, 0.002, 100)
    prices = [base_price]
    
    for change in price_changes:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    prices = prices[1:]  # Remover el primer elemento
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.001))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.001))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(1000, 5000, 100)
    })
    
    return df

def test_strategy():
    """Probar la estrategia"""
    print("🚀 PROBANDO ESTRATEGIA V4 ULTRA")
    
    # Crear estrategia
    strategy = Enhanced15PercentStrategyV4Ultra()
    
    # Crear datos de prueba
    df = create_test_data()
    print(f"📊 Datos creados: {len(df)} filas")
    
    # Probar generación de señales
    signals_generated = 0
    buy_signals = 0
    sell_signals = 0
    
    for i in range(50, len(df)):
        window_data = df.iloc[i-50:i+1].copy()
        
        # Generar señal
        signal_data = strategy.generate_ultra_signal(window_data)
        
        if signal_data:
            signals_generated += 1
            if signal_data['signal'] == 'BUY':
                buy_signals += 1
                print(f"✅ SEÑAL BUY #{buy_signals} - Fuerza: {signal_data['signal_strength']:.3f}")
            elif signal_data['signal'] == 'SELL':
                sell_signals += 1
                print(f"🔴 SEÑAL SELL #{sell_signals} - Fuerza: {signal_data['signal_strength']:.3f}")
    
    print(f"\n📈 RESULTADOS:")
    print(f"   Total señales: {signals_generated}")
    print(f"   Señales BUY: {buy_signals}")
    print(f"   Señales SELL: {sell_signals}")
    print(f"   Señales HOLD: {signals_generated - buy_signals - sell_signals}")
    
    if buy_signals > 0 or sell_signals > 0:
        print("✅ ¡Estrategia generando señales!")
    else:
        print("❌ Estrategia no genera señales de trading")

if __name__ == "__main__":
    test_strategy()