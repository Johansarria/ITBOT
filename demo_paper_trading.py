#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demostración del Sistema de Paper Trading
Muestra datos simulados de ejemplo para demostrar la funcionalidad
"""

import json
import time
from datetime import datetime

# Datos de demostración simulados
DEMO_DATA = {
    "market_data": {
        "SOLUSDT": {
            "price": 198.45,
            "price_change_24h": 5.23,
            "price_change_percent_24h": 2.71,
            "volume_24h": 2450000,
            "high_24h": 205.80,
            "low_24h": 192.10
        },
        "BNBUSDT": {
            "price": 715.30,
            "price_change_24h": 12.45,
            "price_change_percent_24h": 1.77,
            "volume_24h": 1850000,
            "high_24h": 720.50,
            "low_24h": 698.20
        },
        "ADAUSDT": {
            "price": 0.9234,
            "price_change_24h": -0.0156,
            "price_change_percent_24h": -1.66,
            "volume_24h": 3200000,
            "high_24h": 0.9450,
            "low_24h": 0.9180
        }
    },
    "positions": {
        "SOLUSDT": {
            "quantity": 0.8421,
            "avg_price": 195.20,
            "unrealized_pnl": 2.74,
            "realized_pnl": 0.0
        },
        "BNBUSDT": {
            "quantity": 0.2334,
            "avg_price": 708.50,
            "unrealized_pnl": 1.59,
            "realized_pnl": 0.0
        },
        "ADAUSDT": {
            "quantity": 0.0,
            "avg_price": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": -5.23
        }
    },
    "recent_trades": [
        {
            "time": "14:32:15",
            "symbol": "SOLUSDT",
            "side": "BUY",
            "quantity": 0.8421,
            "price": 195.20
        },
        {
            "time": "14:28:42",
            "symbol": "BNBUSDT",
            "side": "BUY",
            "quantity": 0.2334,
            "price": 708.50
        },
        {
            "time": "14:15:33",
            "symbol": "ADAUSDT",
            "side": "SELL",
            "quantity": 540.12,
            "price": 0.9156
        }
    ],
    "performance": {
        "total_value": 1498.67,
        "initial_balance": 1500.0,
        "total_pnl": -1.33,
        "total_return_pct": -0.09,
        "total_trades": 5,
        "balance_usdt": 1331.34
    }
}

def format_number(num, decimals=2):
    """Formatea números para visualización"""
    if abs(num) >= 1000000:
        return f"{num/1000000:.{decimals}f}M"
    elif abs(num) >= 1000:
        return f"{num/1000:.{decimals}f}K"
    else:
        return f"{num:.{decimals}f}"

def display_demo():
    """Muestra la demostración del sistema"""
    print("\n" + "="*80)
    print("🚀 DEMO: PAPER TRADING EN TIEMPO REAL - BINANCE")
    print("Actualización automática cada 30 segundos")
    print(f"Hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Datos de mercado
    print("\n📊 DATOS DE MERCADO EN TIEMPO REAL")
    print("-"*80)
    print(f"{'Símbolo':<10} {'Precio':<12} {'24h %':<10} {'Volumen 24h':<15} {'Última Act.':<20}")
    print("-"*80)
    
    for symbol, data in DEMO_DATA["market_data"].items():
        price_str = f"${format_number(data['price'], 4)}"
        change_str = f"{data['price_change_percent_24h']:+.2f}%"
        volume_str = format_number(data['volume_24h'])
        time_str = datetime.now().strftime("%H:%M:%S")
        
        change_indicator = "↗" if data['price_change_percent_24h'] >= 0 else "↘"
        
        print(f"{symbol:<10} {price_str:<12} {change_indicator}{change_str:<9} {volume_str:<15} {time_str:<20}")
    
    # Posiciones
    print("\n💼 POSICIONES ACTUALES")
    print("-"*80)
    print(f"{'Símbolo':<10} {'Cantidad':<12} {'Precio Prom':<12} {'PnL Real':<12} {'PnL No Real':<12}")
    print("-"*80)
    
    for symbol, pos in DEMO_DATA["positions"].items():
        if pos['quantity'] > 0:
            qty_str = format_number(pos['quantity'], 6)
            price_str = f"${format_number(pos['avg_price'], 4)}"
            real_pnl_str = f"${pos['realized_pnl']:+.2f}"
            unreal_pnl_str = f"${pos['unrealized_pnl']:+.2f}"
            
            print(f"{symbol:<10} {qty_str:<12} {price_str:<12} {real_pnl_str:<12} {unreal_pnl_str:<12}")
        else:
            print(f"{symbol:<10} {'0':<12} {'$0.00':<12} {f'${pos["realized_pnl"]:+.2f}':<12} {'$0.00':<12}")
    
    # Trades recientes
    print("\n📈 TRADES RECIENTES")
    print("-"*80)
    print(f"{'Hora':<10} {'Símbolo':<10} {'Lado':<6} {'Cantidad':<12} {'Precio':<12}")
    print("-"*80)
    
    for trade in DEMO_DATA["recent_trades"]:
        qty_str = format_number(trade['quantity'], 6)
        price_str = f"${format_number(trade['price'], 4)}"
        side_indicator = "↗" if trade['side'] == 'BUY' else "↘"
        
        print(f"{trade['time']:<10} {trade['symbol']:<10} {side_indicator}{trade['side']:<5} {qty_str:<12} {price_str:<12}")
    
    # Rendimiento
    perf = DEMO_DATA["performance"]
    print("\n📊 RENDIMIENTO DEL PORTAFOLIO")
    print("-"*80)
    
    print(f"💰 Valor Total del Portafolio: ${format_number(perf['total_value'])}")
    print(f"💵 Balance en USDT: ${format_number(perf['balance_usdt'])}")
    print(f"📈 PnL Total: ${perf['total_pnl']:+.2f}")
    print(f"📊 Retorno Total: {perf['total_return_pct']:+.2f}%")
    print(f"🔄 Total de Trades: {perf['total_trades']}")
    
    print("\n" + "="*80)
    print("Esta es una demostración del sistema de Paper Trading")
    print("En funcionamiento real, los datos se actualizarían cada 30 segundos")
    print("="*80)

def main():
    """Función principal de demostración"""
    print("🚀 DEMOSTRACIÓN: Sistema de Paper Trading en Tiempo Real")
    print("\nEste es un ejemplo de cómo se vería el sistema funcionando:")
    
    try:
        # Mostrar 3 actualizaciones simuladas
        for i in range(3):
            print(f"\n\n--- ACTUALIZACIÓN {i+1}/3 ---")
            display_demo()
            
            if i < 2:  # No esperar en la última iteración
                print("\n⏳ Esperando 5 segundos para la siguiente actualización...")
                time.sleep(5)
                
                # Simular pequeños cambios en los precios
                import random
                for symbol in DEMO_DATA["market_data"]:
                    current_price = DEMO_DATA["market_data"][symbol]["price"]
                    change = random.uniform(-0.02, 0.02)  # ±2% cambio
                    new_price = current_price * (1 + change)
                    DEMO_DATA["market_data"][symbol]["price"] = new_price
                    DEMO_DATA["market_data"][symbol]["price_change_percent_24h"] += change * 100
        
        print("\n\n🎉 DEMOSTRACIÓN COMPLETADA")
        print("\nCaracterísticas del sistema completo:")
        print("✅ Conexión en tiempo real con Binance WebSocket")
        print("✅ Actualización automática cada 30 segundos")
        print("✅ Estrategia de trading automatizada")
        print("✅ Gestión de posiciones y riesgo")
        print("✅ Cálculo de PnL en tiempo real")
        print("✅ Visualización clara en consola")
        print("✅ Historial de trades")
        print("✅ Métricas de rendimiento")
        
    except KeyboardInterrupt:
        print("\n👋 Demostración detenida por el usuario")
    except Exception as e:
        print(f"\n❌ Error en la demostración: {e}")

if __name__ == "__main__":
    main()