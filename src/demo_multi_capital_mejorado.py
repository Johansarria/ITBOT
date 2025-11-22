#!/usr/bin/env python3
"""
Sistema de backtesting multi-capital mejorado
Con estrategias que realmente se adaptan al tamaño del capital
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

def create_trending_btc_data():
    """Crear datos de BTC con tendencia alcista clara"""
    dates = pd.date_range('2023-01-01', '2023-03-31', freq='4H')
    np.random.seed(42)
    
    # Crear tendencia alcista con volatilidad
    prices = []
    base_price = 20000
    
    for i in range(len(dates)):
        # Tendencia alcista fuerte
        trend = i * 2.0  # Incremento de $2 por período
        
        # Volatilidad controlada
        volatility = np.random.normal(0, 50)
        
        # Algunos retrocesos ocasionales
        if i % 50 == 0 and i > 0:
            retroceso = -200
        else:
            retroceso = 0
        
        price = base_price + trend + volatility + retroceso
        price = max(price, 15000)  # Precio mínimo
        prices.append(price)
    
    data = []
    for i, date in enumerate(dates):
        price = prices[i]
        # OHLC más realista
        open_price = price * (1 + np.random.uniform(-0.001, 0.001))
        high_price = price * (1 + abs(np.random.uniform(0, 0.005)))
        low_price = price * (1 - abs(np.random.uniform(0, 0.005)))
        close_price = price
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': np.random.uniform(800, 1500)
        })
    
    return pd.DataFrame(data)

def create_adaptive_strategy():
    """Crear estrategia que se adapta realmente al capital"""
    
    def adaptive_strategy(backtester, market_data, timestamp):
        """Estrategia adaptativa basada en el capital disponible"""
        if 'BTCUSDT' not in market_data:
            return
        
        btc_data = market_data['BTCUSDT']
        if len(btc_data) < 20:
            return
        
        # Obtener precio actual de forma segura
        try:
            if len(btc_data) == 0:
                return
            current_price = btc_data['close'].iloc[-1] if len(btc_data) > 0 else btc_data['close'].values[0]
        except (IndexError, TypeError, AttributeError):
            return
            
        capital = backtester.initial_capital
        
        # Parámetros adaptativos según el capital
        if capital <= 300:
            # Capital pequeño: estrategia agresiva de momentum
            lookback = 5
            threshold = 0.02  # 2% de cambio
            position_size = 0.95
            stop_loss = 0.08  # 8% stop loss
            take_profit = 0.15  # 15% take profit
        elif capital <= 600:
            # Capital medio: estrategia balanceada
            lookback = 10
            threshold = 0.015  # 1.5% de cambio
            position_size = 0.85
            stop_loss = 0.06  # 6% stop loss
            take_profit = 0.12  # 12% take profit
        else:
            # Capital grande: estrategia conservadora
            lookback = 15
            threshold = 0.01  # 1% de cambio
            position_size = 0.75
            stop_loss = 0.04  # 4% stop loss
            take_profit = 0.08  # 8% take profit
        
        # Calcular momentum de forma segura
        if len(btc_data) >= lookback:
            try:
                if len(btc_data) > lookback:
                    past_price = btc_data['close'].iloc[-lookback]
                else:
                    past_price = current_price  # Fallback si no hay suficientes datos
                price_change = (current_price - past_price) / past_price
            except (IndexError, TypeError, AttributeError):
                past_price = current_price
                price_change = 0
            
            # Señal de compra: momentum positivo
            buy_signal = price_change > threshold
            
            # Señal de venta: momentum negativo
            sell_signal = price_change < -threshold
            
            # Lógica de trading
            current_positions = backtester.current_positions
            
            if buy_signal and 'BTCUSDT' not in current_positions:
                # Comprar
                if backtester.current_capital > 50:
                    available_capital = backtester.current_capital * position_size
                    quantity = available_capital / current_price
                    
                    backtester.place_order(
                        symbol='BTCUSDT',
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=quantity
                    )
            
            elif 'BTCUSDT' in current_positions:
                position = current_positions['BTCUSDT']
                entry_price = position['entry_price']
                
                # Calcular P&L
                pnl_pct = (current_price - entry_price) / entry_price
                
                # Condiciones de venta
                should_sell = (
                    sell_signal or  # Momentum negativo
                    pnl_pct <= -stop_loss or  # Stop loss
                    pnl_pct >= take_profit  # Take profit
                )
                
                if should_sell:
                    backtester.place_order(
                        symbol='BTCUSDT',
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        quantity=position['quantity']
                    )
    
    return adaptive_strategy

def create_mean_reversion_strategy():
    """Crear estrategia de reversión a la media para comparar"""
    
    def mean_reversion_strategy(backtester, market_data, timestamp):
        """Estrategia de reversión a la media"""
        if 'BTCUSDT' not in market_data:
            return
        
        btc_data = market_data['BTCUSDT']
        if len(btc_data) < 30:
            return
        
        # Obtener precio actual de forma segura
        try:
            if len(btc_data) == 0:
                return
            current_price = btc_data['close'].iloc[-1]
        except (IndexError, TypeError, AttributeError):
            return
            
        capital = backtester.initial_capital
        
        # Parámetros según capital
        if capital <= 300:
            sma_period = 10
            std_multiplier = 1.5
            position_size = 0.9
        elif capital <= 600:
            sma_period = 20
            std_multiplier = 2.0
            position_size = 0.8
        else:
            sma_period = 30
            std_multiplier = 2.5
            position_size = 0.7
        
        # Calcular Bandas de Bollinger de forma segura
        try:
            if len(btc_data) >= sma_period:
                sma = btc_data['close'].rolling(window=sma_period).mean().iloc[-1]
                std = btc_data['close'].rolling(window=sma_period).std().iloc[-1]
            else:
                sma = current_price  # Fallback
                std = 0
        except (IndexError, TypeError, AttributeError):
            sma = current_price
            std = 0
            
            upper_band = sma + (std * std_multiplier)
            lower_band = sma - (std * std_multiplier)
            
            current_positions = backtester.current_positions
            
            # Comprar cuando el precio está por debajo de la banda inferior
            if current_price < lower_band and 'BTCUSDT' not in current_positions:
                if backtester.current_capital > 50:
                    available_capital = backtester.current_capital * position_size
                    quantity = available_capital / current_price
                    
                    backtester.place_order(
                        symbol='BTCUSDT',
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        quantity=quantity
                    )
            
            # Vender cuando el precio está por encima de la banda superior
            elif current_price > upper_band and 'BTCUSDT' in current_positions:
                position = current_positions['BTCUSDT']
                backtester.place_order(
                    symbol='BTCUSDT',
                    side=OrderSide.SELL,
                    order_type=OrderType.MARKET,
                    quantity=position['quantity']
                )
    
    return mean_reversion_strategy

def run_comprehensive_test():
    """Ejecutar prueba comprehensiva con múltiples estrategias"""
    
    print("🚀 ANÁLISIS MULTI-CAPITAL MEJORADO")
    print("=" * 60)
    
    try:
        # Crear datos con tendencia alcista
        print("📊 Generando datos de mercado con tendencia alcista...")
        btc_data = create_trending_btc_data()
        market_data = {'BTCUSDT': btc_data}
        
        print(f"✅ Datos generados: {len(btc_data)} velas de 4H")
        
        # Obtener precios de forma segura
        try:
            if len(btc_data) > 0:
                initial_price = btc_data['close'].iloc[0]
                final_price = btc_data['close'].iloc[-1]
            else:
                initial_price = final_price = 0
            
            print(f"📈 Precio inicial: ${initial_price:.2f}")
            print(f"📈 Precio final: ${final_price:.2f}")
            market_return = ((final_price / initial_price) - 1) * 100
        except (IndexError, TypeError, AttributeError):
            print("⚠️ Error al obtener precios del mercado")
            market_return = 0
        print(f"📊 Retorno del mercado: {market_return:.2f}%")
        
        # Probar estrategia adaptativa
        print("\n🎯 PROBANDO ESTRATEGIA ADAPTATIVA")
        print("-" * 50)
        
        multi_backtester = MultiCapitalBacktester(
            capital_range=(200, 1000),
            capital_steps=5,
            commission_rate=0.001
        )
        
        adaptive_strategy = create_adaptive_strategy()
        
        summary_adaptive = multi_backtester.run_multi_capital_backtest(
            market_data=market_data,
            strategy_func=adaptive_strategy,
            start_date='2023-01-01',
            end_date='2023-03-31',
            parallel=False
        )
        
        print("\n📊 RESULTADOS ESTRATEGIA ADAPTATIVA:")
        print("-" * 40)
        
        for result in summary_adaptive.capital_results:
            print(f"Capital: ${result.capital:.0f} | ROI: {result.roi_percentage:.2f}% | P&L: ${result.profit_loss:.2f}")
        
        print(f"\n📈 Mejor capital: ${summary_adaptive.best_capital:.0f}")
        print(f"📉 Peor capital: ${summary_adaptive.worst_capital:.0f}")
        print(f"🎯 Score escalabilidad: {summary_adaptive.scalability_score:.1f}")
        
        # Probar estrategia de reversión a la media
        print("\n🔄 PROBANDO ESTRATEGIA DE REVERSIÓN A LA MEDIA")
        print("-" * 50)
        
        mean_reversion_strategy = create_mean_reversion_strategy()
        
        summary_mean_reversion = multi_backtester.run_multi_capital_backtest(
            market_data=market_data,
            strategy_func=mean_reversion_strategy,
            start_date='2023-01-01',
            end_date='2023-03-31',
            parallel=False
        )
        
        print("\n📊 RESULTADOS ESTRATEGIA REVERSIÓN A LA MEDIA:")
        print("-" * 40)
        
        for result in summary_mean_reversion.capital_results:
            print(f"Capital: ${result.capital:.0f} | ROI: {result.roi_percentage:.2f}% | P&L: ${result.profit_loss:.2f}")
        
        print(f"\n📈 Mejor capital: ${summary_mean_reversion.best_capital:.0f}")
        print(f"📉 Peor capital: ${summary_mean_reversion.worst_capital:.0f}")
        print(f"🎯 Score escalabilidad: {summary_mean_reversion.scalability_score:.1f}")
        
        # Comparación final
        print("\n🏆 COMPARACIÓN FINAL")
        print("-" * 30)
        
        best_adaptive = max(summary_adaptive.capital_results, key=lambda x: x.roi_percentage)
        best_mean_reversion = max(summary_mean_reversion.capital_results, key=lambda x: x.roi_percentage)
        
        print(f"🎯 Mejor resultado adaptativa: {best_adaptive.roi_percentage:.2f}% (Capital: ${best_adaptive.capital:.0f})")
        print(f"🔄 Mejor resultado reversión: {best_mean_reversion.roi_percentage:.2f}% (Capital: ${best_mean_reversion.capital:.0f})")
        
        if best_adaptive.roi_percentage > best_mean_reversion.roi_percentage:
            print("🏅 Ganadora: Estrategia Adaptativa")
        else:
            print("🏅 Ganadora: Estrategia de Reversión a la Media")
        
        print("\n✅ Análisis completado exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_comprehensive_test()