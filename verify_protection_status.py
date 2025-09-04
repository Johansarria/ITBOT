#!/usr/bin/env python3
"""
VERIFICACIÓN POST-PROTECCIÓN
Estado actual después de aplicar medidas de emergencia
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
from datetime import datetime

def verify_protection_status():
    print("🔍 VERIFICACIÓN POST-PROTECCIÓN")
    print("=" * 60)
    
    client = get_um_futures_client()
    
    try:
        # 1. Estado de órdenes activas
        open_orders = client.futures_get_open_orders()
        print(f"📋 Órdenes activas: {len(open_orders)}")
        
        sl_orders = []
        tp_orders = []
        
        for order in open_orders:
            symbol = order['symbol']
            side = order['side']
            order_type = order['type']
            
            if order_type == 'STOP_MARKET':
                stop_price = float(order['stopPrice'])
                sl_orders.append(f"🛡️ {symbol} SL: ${stop_price:.2f}")
            elif order_type == 'TAKE_PROFIT_MARKET':
                stop_price = float(order['stopPrice']) if order['stopPrice'] != '0' else 'N/A'
                tp_orders.append(f"🎯 {symbol} TP: ${stop_price}")
        
        print("\n🛡️ STOP LOSSES ACTIVOS:")
        for sl in sl_orders:
            print(f"   {sl}")
        
        print("\n🎯 TAKE PROFITS ACTIVOS:")
        for tp in tp_orders:
            print(f"   {tp}")
        
        # 2. Estado de posiciones
        print(f"\n📊 POSICIONES ACTUALES:")
        print("-" * 40)
        
        positions = client.futures_position_information()
        total_unrealized_pnl = 0
        active_positions = []
        
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                symbol = pos['symbol']
                size = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                mark_price = float(pos['markPrice'])
                unrealized_pnl = float(pos['unrealizedPnl'])
                percentage = float(pos['percentage'])
                
                total_unrealized_pnl += unrealized_pnl
                
                print(f"   📈 {symbol}:")
                print(f"      Size: {size}")
                print(f"      Entry: ${entry_price:.2f}")
                print(f"      Current: ${mark_price:.2f}")
                print(f"      PnL: ${unrealized_pnl:.2f} ({percentage:.1f}%)")
                
                # Calcular distancia al SL
                current_sl = None
                for order in open_orders:
                    if order['symbol'] == symbol and order['type'] == 'STOP_MARKET':
                        current_sl = float(order['stopPrice'])
                        break
                
                if current_sl:
                    distance_to_sl = ((mark_price - current_sl) / mark_price) * 100
                    print(f"      🛡️ SL Distance: {distance_to_sl:.1f}%")
                    
                    if distance_to_sl < 2:
                        print(f"      ⚠️ MUY CERCA AL SL!")
                    elif distance_to_sl < 5:
                        print(f"      ⚡ Cerca al SL")
                    else:
                        print(f"      ✅ SL seguro")
                
                active_positions.append(symbol)
        
        # 3. Estado del balance y riesgo
        print(f"\n💰 BALANCE Y RIESGO:")
        print("-" * 40)
        
        account = client.futures_account()
        total_balance = float(account['totalWalletBalance'])
        available_balance = float(account['availableBalance'])
        total_unrealized_pnl_account = float(account['totalUnrealizedPnl'])
        
        print(f"   💼 Balance Total: ${total_balance:.2f}")
        print(f"   💳 Balance Disponible: ${available_balance:.2f}")
        print(f"   📊 PnL No Realizado: ${total_unrealized_pnl_account:.2f}")
        
        # Calcular riesgo actual
        if total_balance > 0:
            risk_percentage = abs(total_unrealized_pnl_account / total_balance) * 100
            print(f"   ⚖️ Riesgo Actual: {risk_percentage:.1f}%")
            
            if risk_percentage < 10:
                risk_status = "✅ BAJO"
            elif risk_percentage < 20:
                risk_status = "⚠️ MODERADO"
            elif risk_percentage < 30:
                risk_status = "🟡 ALTO"
            else:
                risk_status = "🚨 CRÍTICO"
            
            print(f"   🎯 Estado de Riesgo: {risk_status}")
        
        # 4. Recomendaciones actualizadas
        print(f"\n💡 RECOMENDACIONES ACTUALES:")
        print("-" * 40)
        
        if available_balance < 1:
            print("   🚨 Balance disponible muy bajo")
            print("   📌 ACCIÓN: Considerar cierre parcial urgente")
        elif available_balance < 3:
            print("   ⚠️ Balance disponible limitado") 
            print("   📌 ACCIÓN: No abrir nuevas posiciones")
        else:
            print("   ✅ Balance disponible aceptable")
        
        if abs(total_unrealized_pnl_account) > total_balance * 0.15:
            print("   🚨 Pérdidas superiores al 15% del balance")
            print("   📌 ACCIÓN: Protección máxima activada")
        
        # Mostrar precios actuales vs SL
        print(f"\n📊 ANÁLISIS DE PROTECCIÓN:")
        print("-" * 40)
        
        for symbol in active_positions:
            # Obtener precio actual
            ticker = client.futures_symbol_ticker(symbol=symbol)
            current_price = float(ticker['price'])
            
            # Encontrar SL
            sl_price = None
            for order in open_orders:
                if order['symbol'] == symbol and order['type'] == 'STOP_MARKET':
                    sl_price = float(order['stopPrice'])
                    break
            
            if sl_price:
                buffer = ((current_price - sl_price) / current_price) * 100
                print(f"   {symbol}: ${current_price:.2f} | SL: ${sl_price:.2f} | Buffer: {buffer:.1f}%")
        
        print(f"\n⏰ Verificación completada: {datetime.now().strftime('%H:%M:%S')}")
        
        return {
            'total_pnl': total_unrealized_pnl_account,
            'available_balance': available_balance,
            'total_balance': total_balance,
            'risk_percentage': risk_percentage,
            'active_positions': len(active_positions)
        }
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return None

if __name__ == "__main__":
    result = verify_protection_status()
    if result:
        print(f"\n🎯 RESUMEN EJECUTIVO:")
        print(f"   Balance: ${result['total_balance']:.2f}")
        print(f"   PnL: ${result['total_pnl']:.2f}")
        print(f"   Riesgo: {result['risk_percentage']:.1f}%")
        print(f"   Posiciones: {result['active_positions']}")
    else:
        print("\n❌ ERROR EN VERIFICACIÓN")
