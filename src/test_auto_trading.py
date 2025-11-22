#!/usr/bin/env python3
"""
Script de prueba para verificar el trading automático
"""

import time
import sys
from datetime import datetime
from pathlib import Path

# Agregar el directorio src al path
sys.path.append(str(Path(__file__).parent))

from enhanced_breakout_detector import BreakoutSignal, BreakoutType, BreakoutStrength
from paper_trading_system import PaperTradingEngine, OrderType, PositionSide
from enhanced_config import CONFIG

def test_auto_trading():
    """Probar el sistema de trading automático"""
    print("🚀 Iniciando prueba de trading automático...")
    
    # Inicializar Paper Trading Engine
    paper_engine = PaperTradingEngine(
        initial_capital=CONFIG.PAPER_TRADING_CONFIG['initial_capital'],
        commission_rate=CONFIG.PAPER_TRADING_CONFIG['commission_rate']
    )
    
    # Obtener resumen inicial del portfolio
    initial_summary = paper_engine.get_portfolio_summary()
    print(f"💰 Capital inicial: ${initial_summary['current_capital']:.2f}")
    
    # Crear señal de breakout de prueba
    test_signal = BreakoutSignal(
        symbol="ETHUSDT",
        timestamp=datetime.now(),
        breakout_type=BreakoutType.BULLISH,
        strength=BreakoutStrength.STRONG,
        confidence=0.85,
        price=2150.50,
        volume=1500000,
        resistance_level=2145.00,
        support_level=2100.00,
        price_change_pct=1.25,
        volume_ratio=2.3,
        candle_pattern="strong_bullish",
        technical_indicators={"rsi": 65, "macd": 0.5}
    )
    
    print(f"🚨 Simulando breakout: {test_signal.symbol} - {test_signal.breakout_type.value}")
    print(f"   💲 Precio: ${test_signal.price:.4f}")
    print(f"   🎯 Confianza: {test_signal.confidence:.1%}")
    
    # Simular lógica de trading automático
    try:
        # Determinar dirección del trade
        if test_signal.breakout_type.value == "bullish":
            side = "buy"  # LONG = buy
            direction_text = "LONG"
        else:
            side = "sell"  # SHORT = sell
            direction_text = "SHORT"
        
        # Calcular cantidad basada en el riesgo configurado
        risk_per_trade = CONFIG.PAPER_TRADING_CONFIG['risk_per_trade_pct'] * 100  # Por ejemplo, 2% del capital
        current_capital = initial_summary['current_capital']
        risk_amount = current_capital * (risk_per_trade / 100)
        
        # Calcular cantidad de la orden
        quantity = risk_amount / test_signal.price
        
        print(f"📊 Calculando trade:")
        print(f"   💰 Capital actual: ${current_capital:.2f}")
        print(f"   ⚡ Riesgo por trade: {risk_per_trade}% = ${risk_amount:.2f}")
        print(f"   📦 Cantidad: {quantity:.6f} {test_signal.symbol}")
        
        # Verificar cantidad mínima (apropiada para base de $200)
        if quantity < 0.00001:
            print(f"⚠️ Cantidad muy pequeña: {quantity:.6f}")
            return
        
        # Ejecutar la orden
        print(f"🔄 Ejecutando orden {direction_text}...")
        order_result = paper_engine.place_order(
            symbol=test_signal.symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=test_signal.price  # Precio actual para orden de mercado
        )
        
        if order_result:
            print(f"✅ ORDEN COLOCADA: {direction_text} {test_signal.symbol}")
            print(f"   🆔 Order ID: {order_result}")
            print(f"   💰 Cantidad: {quantity:.6f}")
            print(f"   💲 Precio: ${test_signal.price:.4f}")
            print(f"   🎯 Confianza: {test_signal.confidence:.1%}")
            
            # Simular datos de mercado para ejecutar la orden
            market_data = {test_signal.symbol: test_signal.price}
            paper_engine.process_market_data(market_data)
            print(f"   ✅ Orden procesada con datos de mercado")
            
            # Mostrar estado después del trade
            final_summary = paper_engine.get_portfolio_summary()
            positions_summary = paper_engine.get_positions_summary()
            
            print(f"\n📊 Estado después del trade:")
            print(f"   💰 Nuevo balance: ${final_summary['current_capital']:.2f}")
            print(f"   📈 PnL total: ${final_summary['total_pnl']:.2f}")
            print(f"   📦 Posiciones activas: {final_summary['open_positions']}")
            print(f"   📊 Valor total portfolio: ${final_summary['total_portfolio_value']:.2f}")
            print(f"   📈 Retorno total: {final_summary['total_return_pct']:.2f}%")
            
            if positions_summary:
                print(f"\n📦 Posiciones detalladas:")
                for position in positions_summary:
                    print(f"      {position['symbol']}: {position['size']:.6f} @ ${position['entry_price']:.4f}")
                    print(f"         PnL: ${position['unrealized_pnl']:.2f} ({position['pnl_percentage']:.2f}%)")
            
        else:
            print(f"❌ Error ejecutando trade")
            print(f"   Resultado: {order_result}")
            
    except Exception as e:
        print(f"❌ Error en auto-trading: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auto_trading()