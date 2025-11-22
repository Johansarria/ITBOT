#!/usr/bin/env python3
"""
Test simple para métricas avanzadas
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_backtester import AdvancedBacktester, OrderSide, OrderType

def test_advanced_metrics_simple():
    """Test simple de métricas avanzadas"""
    try:
        print("🧪 Iniciando test de métricas avanzadas...")
        
        # Crear datos de prueba simples (6 meses)
        dates = pd.date_range(start='2024-01-01', end='2024-06-30', freq='1D')
        np.random.seed(42)
        
        # Simular precio de BTC con tendencia alcista
        base_price = 50000
        returns = np.random.normal(0.001, 0.02, len(dates))  # 0.1% retorno diario promedio
        prices = [base_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, 1000))
        
        btc_data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 5000, len(dates))
        })
        
        print(f"📊 Datos generados: {len(btc_data)} días")
        print(f"💰 Precio inicial: ${prices[0]:,.2f}")
        print(f"💰 Precio final: ${prices[-1]:,.2f}")
        
        # Inicializar backtester
        backtester = AdvancedBacktester(
            initial_capital=100000,
            commission_rate=0.001
        )
        
        # Cargar datos de mercado
        backtester.load_market_data({'BTCUSDT': btc_data})
        
        # Estrategia simple de buy and hold
        def simple_strategy(backtester_ref, market_data, current_time):
            if 'BTCUSDT' not in market_data:
                return
            
            # Solo comprar al inicio si no tenemos posición
            if len(backtester_ref.current_positions) == 0 and backtester_ref.current_capital > 1000:
                # Invertir 90% del capital
                investment = backtester_ref.current_capital * 0.9
                current_price = backtester_ref.current_prices['BTCUSDT']
                quantity = investment / current_price
                
                backtester_ref.place_order(
                    symbol='BTCUSDT',
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=quantity
                )
        
        # Ejecutar backtest
        print("🚀 Ejecutando backtest...")
        result = backtester.run_backtest(
            strategy_func=simple_strategy,
            start_date=dates[0],
            end_date=dates[-1]
        )
        
        if result.success:
            print("✅ Backtest completado exitosamente!")
            print(f"📈 Retorno total: {result.metrics.total_return:.2%}")
            print(f"📊 Sharpe Ratio: {result.metrics.sharpe_ratio:.3f}")
            print(f"📉 Max Drawdown: {result.metrics.max_drawdown:.2%}")
            
            # Mostrar métricas avanzadas si están disponibles
            if result.advanced_metrics:
                print("\n🔬 MÉTRICAS AVANZADAS:")
                print("=" * 50)
                
                # Risk-Adjusted Return Metrics
                print("\n📊 MÉTRICAS DE RETORNO AJUSTADO POR RIESGO:")
                print(f"  • Treynor Ratio: {result.advanced_metrics.treynor_ratio:.4f}")
                print(f"  • Jensen Alpha: {result.advanced_metrics.jensen_alpha:.4f}")
                print(f"  • Modigliani Ratio: {result.advanced_metrics.modigliani_ratio:.4f}")
                print(f"  • Information Ratio: {result.advanced_metrics.information_ratio:.4f}")
                print(f"  • Tracking Error: {result.advanced_metrics.tracking_error:.4f}")
                
                # Advanced Drawdown Metrics
                print("\n📉 MÉTRICAS AVANZADAS DE DRAWDOWN:")
                print(f"  • Ulcer Index: {result.advanced_metrics.ulcer_index:.4f}")
                print(f"  • Pain Index: {result.advanced_metrics.pain_index:.4f}")
                print(f"  • Lake Ratio: {result.advanced_metrics.lake_ratio:.4f}")
                print(f"  • Burke Ratio: {result.advanced_metrics.burke_ratio:.4f}")
                
                # Consistency Metrics
                print("\n🎯 MÉTRICAS DE CONSISTENCIA:")
                print(f"  • Gain to Pain Ratio: {result.advanced_metrics.gain_to_pain_ratio:.4f}")
                print(f"  • Sterling Ratio: {result.advanced_metrics.sterling_ratio:.4f}")
                print(f"  • Kappa Three: {result.advanced_metrics.kappa_three:.4f}")
                print(f"  • Omega Ratio: {result.advanced_metrics.omega_ratio:.4f}")
                
                # Tail Risk Metrics
                print("\n⚠️ MÉTRICAS DE RIESGO DE COLA:")
                print(f"  • Tail Ratio: {result.advanced_metrics.tail_ratio:.4f}")
                print(f"  • Expected Shortfall Ratio: {result.advanced_metrics.expected_shortfall_ratio:.4f}")
                print(f"  • Conditional Drawdown Risk: {result.advanced_metrics.conditional_drawdown_risk:.4f}")
                print(f"  • Max Adverse Excursion: {result.advanced_metrics.maximum_adverse_excursion:.4f}")
                
                # Timing Metrics
                print("\n⏰ MÉTRICAS DE TIMING:")
                print(f"  • Up Capture Ratio: {result.advanced_metrics.up_capture_ratio:.4f}")
                print(f"  • Down Capture Ratio: {result.advanced_metrics.down_capture_ratio:.4f}")
                print(f"  • Capture Ratio: {result.advanced_metrics.capture_ratio:.4f}")
                print(f"  • Batting Average: {result.advanced_metrics.batting_average:.4f}")
                
                # Stability Metrics
                print("\n🔒 MÉTRICAS DE ESTABILIDAD:")
                print(f"  • Return Stability: {result.advanced_metrics.return_stability:.4f}")
                print(f"  • Sharpe Stability: {result.advanced_metrics.sharpe_stability:.4f}")
                print(f"  • Performance Consistency: {result.advanced_metrics.performance_consistency:.4f}")
                print(f"  • Rolling Sharpe Std: {result.advanced_metrics.rolling_sharpe_std:.4f}")
                
                print("\n✅ Métricas avanzadas calculadas exitosamente!")
            else:
                print("⚠️ No se calcularon métricas avanzadas")
        else:
            print(f"❌ Error en backtest: {result.message}")
            
    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_advanced_metrics_simple()