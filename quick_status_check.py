#!/usr/bin/env python3
"""
ESTADO ACTUAL SIMPLIFICADO
Verificación rápida del estado post-protección
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
from datetime import datetime

def quick_status_check():
    print("🔍 ESTADO ACTUAL POST-PROTECCIÓN")
    print("=" * 50)
    
    client = get_um_futures_client()
    
    try:
        # 1. Órdenes activas
        open_orders = client.futures_get_open_orders()
        print(f"📋 Órdenes activas: {len(open_orders)}")
        
        for order in open_orders:
            symbol = order['symbol']
            order_type = order['type']
            stop_price = order.get('stopPrice', '0')
            
            if order_type == 'STOP_MARKET':
                print(f"   🛡️ {symbol} SL: ${float(stop_price):.2f}")
            elif order_type == 'TAKE_PROFIT_MARKET':
                print(f"   🎯 {symbol} TP: ${float(stop_price):.2f}")
        
        # 2. Posiciones activas
        positions = client.futures_position_information()
        print(f"\n📊 POSICIONES:")
        
        total_notional = 0
        active_count = 0
        
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                symbol = pos['symbol']
                size = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                notional = float(pos['notional'])
                
                total_notional += abs(notional)
                active_count += 1
                
                print(f"   📈 {symbol}: {size} @ ${entry_price:.2f} (${abs(notional):.2f})")
        
        # 3. Balance
        account = client.futures_account()
        total_balance = float(account['totalWalletBalance'])
        available_balance = float(account['availableBalance'])
        
        print(f"\n💰 BALANCE:")
        print(f"   Total: ${total_balance:.2f}")
        print(f"   Disponible: ${available_balance:.2f}")
        
        # 4. Riesgo calculado
        if total_balance > 0:
            exposure_ratio = (total_notional / total_balance) * 100
            print(f"   📊 Exposición: {exposure_ratio:.1f}%")
            
            if exposure_ratio > 500:
                print(f"   🚨 ALTO RIESGO - Exposición crítica")
            elif exposure_ratio > 200:
                print(f"   ⚠️ RIESGO MODERADO")
            else:
                print(f"   ✅ Riesgo controlado")
        
        # 5. Precios actuales vs SL
        print(f"\n📊 PROTECCIÓN ACTUAL:")
        
        sl_orders = {order['symbol']: float(order['stopPrice']) 
                    for order in open_orders 
                    if order['type'] == 'STOP_MARKET'}
        
        for symbol, sl_price in sl_orders.items():
            try:
                ticker = client.futures_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                buffer = ((current_price - sl_price) / current_price) * 100
                
                if buffer < 2:
                    status = "🚨 MUY CERCA"
                elif buffer < 5:
                    status = "⚠️ CERCA"
                else:
                    status = "✅ SEGURO"
                
                print(f"   {symbol}: ${current_price:.2f} → SL ${sl_price:.2f} ({buffer:.1f}%) {status}")
                
            except Exception as e:
                print(f"   {symbol}: Error obteniendo precio - {e}")
        
        # 6. Recomendación inmediata
        print(f"\n💡 ESTADO ACTUAL:")
        
        if available_balance < 0.5:
            print("   🚨 CRÍTICO: Balance muy bajo")
            print("   📌 ACCIÓN: Monitorear cada 5 minutos")
        elif available_balance < 2:
            print("   ⚠️ PRECAUCIÓN: Balance limitado")
            print("   📌 ACCIÓN: Monitorear cada 15 minutos")
        else:
            print("   ✅ ESTABLE: Balance aceptable")
        
        print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Verificación completada")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    quick_status_check()
