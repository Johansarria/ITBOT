#!/usr/bin/env python3
"""
Resumen rápido de posiciones actuales
"""

from binance import Client
import os
from datetime import datetime

def check_current_positions():
    """Verificar estado actual de todas las posiciones"""
    
    client = Client(
        api_key=os.getenv('BINANCE_API_KEY'),
        api_secret=os.getenv('BINANCE_SECRET_KEY')
    )
    
    try:
        print("🔍 ESTADO ACTUAL DE POSICIONES")
        print("="*50)
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        # Obtener información de cuenta
        account_info = client.futures_account()
        total_balance = float(account_info['totalWalletBalance'])
        available_balance = float(account_info['availableBalance'])
        total_unrealized_pnl = float(account_info['totalUnrealizedProfit'])
        
        print(f"\n💰 BALANCE:")
        print(f"   Total: ${total_balance:.2f}")
        print(f"   Disponible: ${available_balance:.2f}")
        print(f"   PnL no realizado: ${total_unrealized_pnl:.2f}")
        
        # Obtener posiciones abiertas
        positions = client.futures_position_information()
        open_positions = []
        
        for pos in positions:
            position_amt = float(pos['positionAmt'])
            if position_amt != 0:
                entry_price = float(pos['entryPrice'])
                mark_price = float(pos['markPrice'])
                unrealized_pnl = float(pos['unRealizedProfit'])
                position_value = abs(position_amt) * mark_price
                percentage = (mark_price - entry_price) / entry_price * 100 if position_amt > 0 else (entry_price - mark_price) / entry_price * 100
                
                open_positions.append({
                    'symbol': pos['symbol'],
                    'side': 'LONG' if position_amt > 0 else 'SHORT',
                    'size': abs(position_amt),
                    'entry_price': entry_price,
                    'mark_price': mark_price,
                    'unrealized_pnl': unrealized_pnl,
                    'position_value': position_value,
                    'percentage': percentage,
                    'margin_type': pos['marginType'],
                    'isolated_margin': float(pos['isolatedMargin'])
                })
        
        if open_positions:
            print(f"\n📊 POSICIONES ABIERTAS ({len(open_positions)}):")
            total_pnl = 0
            for pos in open_positions:
                pnl_icon = "📈" if pos['unrealized_pnl'] > 0 else "📉"
                side_icon = "🟢" if pos['side'] == 'LONG' else "🔴"
                
                print(f"\n   {side_icon} {pos['symbol']} ({pos['side']}):")
                print(f"      Tamaño: {pos['size']:.6f}")
                print(f"      Valor posición: ${pos['position_value']:.2f}")
                print(f"      Precio entrada: ${pos['entry_price']:.4f}")
                print(f"      Precio actual: ${pos['mark_price']:.4f}")
                print(f"      {pnl_icon} PnL: ${pos['unrealized_pnl']:.2f} ({pos['percentage']:.2f}%)")
                print(f"      Margen tipo: {pos['margin_type']}")
                if pos['margin_type'] == 'isolated':
                    print(f"      Margen aislado: ${pos['isolated_margin']:.2f}")
                
                total_pnl += pos['unrealized_pnl']
            
            print(f"\n💹 RESUMEN TOTAL:")
            print(f"   Total posiciones: {len(open_positions)}")
            print(f"   PnL total: ${total_pnl:.2f}")
            print(f"   Balance efectivo: ${total_balance + total_pnl:.2f}")
            
        else:
            print("\n📊 POSICIONES ABIERTAS: Ninguna")
        
        # Verificar órdenes pendientes
        open_orders = client.futures_get_open_orders()
        if open_orders:
            print(f"\n📋 ÓRDENES PENDIENTES ({len(open_orders)}):")
            for order in open_orders:
                order_type = order['type']
                side = order['side']
                symbol = order['symbol']
                price = float(order['price']) if order['price'] != '0' else 'Market'
                qty = float(order['origQty'])
                
                print(f"   🎯 {symbol} {side} {order_type}: {qty} @ {price}")
        
        print("\n" + "="*50)
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_current_positions()
