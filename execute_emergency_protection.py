#!/usr/bin/env python3
"""
EJECUCIÓN INMEDIATA DE PROTECCIÓN DE CAPITAL
Ajustar Stop Loss para minimizar riesgo de liquidación
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
import time
from datetime import datetime

def execute_emergency_protection():
    print("🚨 EJECUTANDO PROTECCIÓN INMEDIATA DE CAPITAL")
    print("=" * 60)
    
    client = get_um_futures_client()
    
    # 1. Obtener órdenes activas primero
    try:
        open_orders = client.futures_get_open_orders()
        print(f"📋 Órdenes activas encontradas: {len(open_orders)}")
        
        for order in open_orders:
            symbol = order['symbol']
            side = order['side']
            type = order['type']
            price = float(order['price'])
            print(f"   • {symbol} | {side} | {type} | ${price:.2f}")
        
    except Exception as e:
        print(f"❌ Error obteniendo órdenes: {e}")
        return False
    
    # 2. Ejecutar ajustes de Stop Loss más conservadores
    protection_orders = [
        {
            'symbol': 'ETHUSDT',
            'new_sl': 4400.00,  # Más conservador que 4380
            'reason': 'Protección contra liquidación - posición con mayor pérdida'
        },
        {
            'symbol': 'SOLUSDT', 
            'new_sl': 209.00,   # Más conservador que 208
            'reason': 'Protección contra liquidación - reducir exposición'
        }
    ]
    
    print("\n🛡️ AJUSTANDO STOP LOSS PROTECTORES:")
    print("-" * 50)
    
    for protection in protection_orders:
        symbol = protection['symbol']
        new_sl = protection['new_sl']
        reason = protection['reason']
        
        try:
            # Cancelar SL existente primero
            existing_sl_orders = [order for order in open_orders 
                                if order['symbol'] == symbol and order['type'] == 'STOP_MARKET']
            
            for sl_order in existing_sl_orders:
                cancel_result = client.futures_cancel_order(
                    symbol=symbol,
                    orderId=sl_order['orderId']
                )
                print(f"   ✅ Cancelado SL anterior para {symbol}: ${float(sl_order['stopPrice']):.2f}")
            
            # Crear nuevo SL más conservador
            new_sl_order = client.futures_create_order(
                symbol=symbol,
                side='SELL',  # Para posiciones LONG
                type='STOP_MARKET',
                stopPrice=new_sl,
                closePosition=True,
                workingType='MARK_PRICE',
                timeInForce='GTC'
            )
            
            print(f"   🎯 NUEVO SL {symbol}: ${new_sl:.2f}")
            print(f"   💡 Razón: {reason}")
            print(f"   ✅ Order ID: {new_sl_order['orderId']}")
            
        except Exception as e:
            print(f"   ❌ Error ajustando SL para {symbol}: {e}")
    
    # 3. Mostrar estado final de protección
    print(f"\n📊 ESTADO DE PROTECCIÓN ACTUALIZADO:")
    print("-" * 50)
    
    try:
        # Obtener nuevas órdenes activas
        updated_orders = client.futures_get_open_orders()
        
        for order in updated_orders:
            if order['type'] == 'STOP_MARKET':
                symbol = order['symbol']
                stop_price = float(order['stopPrice'])
                print(f"   🛡️ {symbol} Stop Loss: ${stop_price:.2f}")
        
        # Obtener posiciones actuales
        positions = client.futures_position_information()
        total_pnl = 0
        
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                symbol = pos['symbol']
                pnl = float(pos['unRealizedPnl'])
                entry_price = float(pos['entryPrice'])
                mark_price = float(pos['markPrice'])
                total_pnl += pnl
                
                print(f"   📈 {symbol}: Entrada ${entry_price:.2f} | Actual ${mark_price:.2f} | PnL ${pnl:.2f}")
        
        print(f"\n💰 PnL Total: ${total_pnl:.2f}")
        
        # Calcular riesgo reducido
        account = client.futures_account()
        available_balance = float(account['availableBalance'])
        total_balance = float(account['totalWalletBalance'])
        
        print(f"💳 Balance disponible: ${available_balance:.2f}")
        print(f"💼 Balance total: ${total_balance:.2f}")
        
        if total_balance > 0:
            risk_pct = abs(total_pnl / total_balance) * 100
            print(f"⚖️  Riesgo actual: {risk_pct:.1f}% del balance")
            
            if risk_pct < 15:
                print("✅ Riesgo REDUCIDO - Capital mejor protegido")
            elif risk_pct < 25:
                print("⚠️ Riesgo MODERADO - Continuar monitoreando")
            else:
                print("🚨 Riesgo AÚN ALTO - Considerar cierre parcial")
        
    except Exception as e:
        print(f"❌ Error verificando estado final: {e}")
    
    print(f"\n⏰ Protección ejecutada: {datetime.now().strftime('%H:%M:%S')}")
    print("🔄 RECOMENDACIÓN: Monitorear cada 15 minutos")
    print("🎯 OBJETIVO: Mover a break-even cuando sea posible")
    
    return True

if __name__ == "__main__":
    success = execute_emergency_protection()
    if success:
        print("\n✅ PROTECCIÓN DE CAPITAL APLICADA")
    else:
        print("\n❌ ERROR EN PROTECCIÓN - REVISAR MANUALMENTE")
