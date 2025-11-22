#!/usr/bin/env python3
"""
Test simple del sistema multi-capital
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_multi_capital_simple():
    """Test simple del sistema multi-capital"""
    try:
        print("🧪 Iniciando test del sistema multi-capital...")
        
        # Importar después de configurar el path
        from multi_capital_backtester import MultiCapitalBacktester, create_sample_strategy
        
        print("✅ Imports exitosos")
        
        # Crear datos de prueba simples
        dates = pd.date_range('2023-01-01', '2023-01-31', freq='1H')
        np.random.seed(42)
        
        # Datos de BTC simplificados
        prices = []
        base_price = 20000
        for i in range(len(dates)):
            change = np.random.normal(0, 0.01)
            base_price = base_price * (1 + change)
            prices.append(max(base_price, 1000))
        
        btc_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': [1000] * len(dates)
        })
        
        market_data = {'BTCUSDT': btc_data}
        print("✅ Datos de prueba creados")
        
        # Crear backtester multi-capital con rango pequeño
        multi_backtester = MultiCapitalBacktester(
            capital_range=(200, 500),
            capital_steps=4
        )
        print("✅ MultiCapitalBacktester creado")
        
        # Crear estrategia simple
        strategy = create_sample_strategy()
        print("✅ Estrategia creada")
        
        # Ejecutar análisis (sin paralelo para debugging)
        print("🚀 Ejecutando análisis...")
        summary = multi_backtester.run_multi_capital_backtest(
            market_data=market_data,
            strategy_func=strategy,
            start_date='2023-01-01',
            end_date='2023-01-31',
            parallel=False
        )
        
        print("✅ Análisis completado")
        
        # Mostrar resultados básicos
        print(f"\n📊 RESULTADOS:")
        print(f"Mejor capital: ${summary.best_capital}")
        print(f"Peor capital: ${summary.worst_capital}")
        print(f"Score de escalabilidad: {summary.scalability_score:.1f}")
        
        print("\n📈 Detalle por capital:")
        for result in summary.capital_results:
            print(f"  ${result.capital:.0f}: ROI {result.roi_percentage:.2f}%, "
                  f"Trades: {result.trades_count}")
        
        print("\n✅ Test completado exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_multi_capital_simple()