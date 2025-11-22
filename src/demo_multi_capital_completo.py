#!/usr/bin/env python3
"""
Demostración completa del sistema de backtesting multi-capital
Con datos más realistas y estrategias optimizadas
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from multi_capital_backtester import MultiCapitalBacktester
from advanced_backtester import OrderSide, OrderType

def create_realistic_btc_data(start_date='2023-01-01', end_date='2023-12-31', freq='1H'):
    """Crear datos de BTC más realistas"""
    dates = pd.date_range(start_date, end_date, freq=freq)
    np.random.seed(42)
    
    # Parámetros para simulación más realista
    initial_price = 20000
    trend = 0.0002  # Tendencia alcista leve
    volatility = 0.02
    
    prices = [initial_price]
    
    for i in range(len(dates)):
        # Componente de tendencia
        trend_component = trend
        
        # Componente de volatilidad
        volatility_component = np.random.normal(0, volatility)
        
        # Componente de reversión a la media
        mean_reversion = -0.1 * (prices[-1] - initial_price) / initial_price
        
        # Precio siguiente
        change = trend_component + volatility_component + mean_reversion
        new_price = prices[-1] * (1 + change)
        new_price = max(new_price, 1000)  # Precio mínimo
        prices.append(new_price)
    
    # Crear OHLCV
    data = []
    for i in range(len(dates)):
        open_price = prices[i]
        close_price = prices[i + 1]
        
        # High y Low basados en volatilidad intraday
        intraday_vol = abs(np.random.normal(0, 0.005))
        high_price = max(open_price, close_price) * (1 + intraday_vol)
        low_price = min(open_price, close_price) * (1 - intraday_vol)
        
        volume = np.random.uniform(500, 2000)
        
        data.append({
            'timestamp': dates[i],
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data)

def create_adaptive_momentum_strategy():
    """Crear estrategia de momentum adaptativa"""
    
    def adaptive_momentum_strategy(backtester, market_data, timestamp):
        """
        Estrategia de momentum que se adapta al tamaño del capital
        """
        if 'BTCUSDT' not in market_data:
            return
        
        btc_data = market_data['BTCUSDT']
        if len(btc_data) < 50:
            return
        
        current_price = btc_data['close'].iloc[-1]
        
        # Parámetros adaptativos basados en el capital
        capital = backtester.initial_capital
        
        if capital <= 300:
            # Capital pequeño: estrategia más agresiva
            sma_fast = 5
            sma_slow = 15
            position_size = 0.9
            stop_loss = 0.05
        elif capital <= 600:
            # Capital medio: estrategia balanceada
            sma_fast = 10
            sma_slow = 25
            position_size = 0.8
            stop_loss = 0.04
        else:
            # Capital grande: estrategia más conservadora
            sma_fast = 15
            sma_slow = 35
            position_size = 0.7
            stop_loss = 0.03
        
        # Calcular medias móviles
        if len(btc_data) < sma_slow:
            return
            
        sma_fast_val = btc_data['close'].tail(sma_fast).mean()
        sma_slow_val = btc_data['close'].tail(sma_slow).mean()
        
        # RSI para filtrar señales
        rsi = calculate_rsi(btc_data['close'], 14)
        current_rsi = 50  # Valor por defecto
        
        if rsi is not None and len(rsi) > 0:
            try:
                # Verificar si rsi es una serie o un escalar
                if hasattr(rsi, 'iloc'):
                    current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
                else:
                    current_rsi = rsi if not pd.isna(rsi) else 50
            except (IndexError, TypeError):
                current_rsi = 50
        
        # Señales de entrada
        momentum_signal = sma_fast_val > sma_slow_val * 1.01
        rsi_oversold = current_rsi < 70  # No comprar si está sobrecomprado
        
        # Señal de compra
        if (momentum_signal and rsi_oversold and 
            len(backtester.current_positions) == 0 and 
            backtester.current_capital > 50):
            
            # Calcular tamaño de posición
            available_capital = backtester.current_capital * position_size
            quantity = available_capital / current_price
            
            backtester.place_order(
                symbol='BTCUSDT',
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=quantity
            )
        
        # Señales de salida
        elif 'BTCUSDT' in backtester.current_positions:
            position = backtester.current_positions['BTCUSDT']
            entry_price = position['entry_price']
            
            # Stop loss
            stop_loss_price = entry_price * (1 - stop_loss)
            
            # Take profit (momentum reversal)
            momentum_reversal = sma_fast_val < sma_slow_val * 0.99
            rsi_overbought = current_rsi > 80
            
            if (current_price <= stop_loss_price or 
                momentum_reversal or rsi_overbought):
                
                backtester.place_order(
                    symbol='BTCUSDT',
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=position['quantity']
                )
    
    return adaptive_momentum_strategy

def calculate_rsi(prices, period=14):
    """Calcular RSI con manejo robusto de errores"""
    try:
        if len(prices) < period + 1:
            return pd.Series([50] * len(prices), index=prices.index)
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Evitar división por cero
        rs = gain / loss.replace(0, 0.0001)
        rsi = 100 - (100 / (1 + rs))
        
        # Rellenar valores NaN con 50
        rsi = rsi.fillna(50)
        
        return rsi
    except Exception as e:
        # En caso de error, devolver una serie con valores neutros
        return pd.Series([50] * len(prices), index=prices.index)

def run_comprehensive_analysis():
    """Ejecutar análisis comprehensivo multi-capital"""
    
    print("🚀 ANÁLISIS COMPREHENSIVO MULTI-CAPITAL")
    print("=" * 60)
    
    # Crear datos realistas
    print("📊 Generando datos de mercado realistas...")
    btc_data = create_realistic_btc_data('2023-01-01', '2023-12-31', '4H')
    market_data = {'BTCUSDT': btc_data}
    
    print(f"✅ Datos generados: {len(btc_data)} velas de 4H")
    print(f"📈 Precio inicial: ${btc_data['close'].iloc[0]:.2f}")
    print(f"📈 Precio final: ${btc_data['close'].iloc[-1]:.2f}")
    print(f"📊 Retorno del mercado: {((btc_data['close'].iloc[-1] / btc_data['close'].iloc[0]) - 1) * 100:.2f}%")
    
    # Configurar backtester multi-capital
    print("\n🏦 Configurando backtester multi-capital...")
    multi_backtester = MultiCapitalBacktester(
        capital_range=(200, 1000),
        capital_steps=9,
        commission_rate=0.001
    )
    
    # Crear estrategia adaptativa
    strategy = create_adaptive_momentum_strategy()
    
    # Ejecutar análisis
    print("\n🔄 Ejecutando análisis multi-capital...")
    summary = multi_backtester.run_multi_capital_backtest(
        market_data=market_data,
        strategy_func=strategy,
        start_date='2023-01-01',
        end_date='2023-12-31',
        parallel=False  # Secuencial para mejor debugging
    )
    
    # Generar reporte completo
    print("\n📄 Generando reporte...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"multi_capital_report_{timestamp}.txt"
    
    report = multi_backtester.generate_report(summary, report_path)
    print(report)
    
    # Exportar resultados a JSON
    json_path = f"multi_capital_results_{timestamp}.json"
    multi_backtester.export_results_to_json(summary, json_path)
    
    # Crear gráficos
    print("\n📊 Generando gráficos...")
    plot_path = f"multi_capital_analysis_{timestamp}.png"
    multi_backtester.plot_capital_analysis(summary, plot_path)
    
    # Análisis adicional
    print("\n🔍 ANÁLISIS ADICIONAL")
    print("-" * 40)
    
    # Encontrar capital óptimo
    best_result = max(summary.capital_results, key=lambda x: x.roi_percentage)
    print(f"💰 Capital óptimo: ${best_result.capital:.0f} USDT")
    print(f"📈 ROI óptimo: {best_result.roi_percentage:.2f}%")
    print(f"💵 Ganancia: ${best_result.profit_loss:.2f}")
    print(f"📊 Sharpe Ratio: {best_result.backtest_result.sharpe_ratio:.3f}")
    
    # Análisis de escalabilidad
    capitals = [r.capital for r in summary.capital_results]
    rois = [r.roi_percentage for r in summary.capital_results]
    
    correlation = np.corrcoef(capitals, rois)[0, 1]
    print(f"\n📈 Correlación Capital-ROI: {correlation:.3f}")
    
    if correlation > 0.5:
        print("✅ Excelente escalabilidad - La estrategia mejora con más capital")
    elif correlation > 0:
        print("⚖️ Escalabilidad positiva - Mejora moderada con más capital")
    else:
        print("⚠️ Escalabilidad negativa - Revisar estrategia para capitales mayores")
    
    # Recomendaciones finales
    print(f"\n💡 RECOMENDACIONES FINALES")
    print("-" * 40)
    
    profitable_results = [r for r in summary.capital_results if r.roi_percentage > 0]
    
    if profitable_results:
        min_profitable = min(profitable_results, key=lambda x: x.capital).capital
        max_profitable = max(profitable_results, key=lambda x: x.capital).capital
        print(f"💰 Rango de capital rentable: ${min_profitable:.0f} - ${max_profitable:.0f} USDT")
    else:
        print("⚠️ Ningún capital mostró rentabilidad - Revisar estrategia")
    
    avg_roi = np.mean(rois)
    std_roi = np.std(rois)
    print(f"📊 ROI promedio: {avg_roi:.2f}% ± {std_roi:.2f}%")
    
    if std_roi < 5:
        print("🎯 Baja variabilidad - Estrategia consistente")
    elif std_roi < 15:
        print("⚖️ Variabilidad moderada - Considerar optimización")
    else:
        print("⚠️ Alta variabilidad - Revisar gestión de riesgo")
    
    print(f"\n✅ Análisis completado. Archivos generados:")
    print(f"   📄 Reporte: {report_path}")
    print(f"   📁 JSON: {json_path}")
    print(f"   📊 Gráficos: {plot_path}")

if __name__ == "__main__":
    run_comprehensive_analysis()