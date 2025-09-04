#!/usr/bin/env python3
"""
CONFIGURACIÓN DE STOP LOSS PARA SOLUSDT
Completar la protección de la posición restante
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
from datetime import datetime

def configure_solusdt_stop_loss():
    print("🛡️ CONFIGURACIÓN DE STOP LOSS PARA SOLUSDT")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    
    client = get_um_futures_client()
    
    try:
        # 1. Verificar posición actual de SOLUSDT
        positions = client.futures_position_information(symbol='SOLUSDT')
        solusdt_position = None
        
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                solusdt_position = pos
                break
        
        if not solusdt_position:
            print("❌ No se encontró posición activa de SOLUSDT")
            return False
        
        # 2. Datos de la posición
        position_amt = float(solusdt_position['positionAmt'])
        entry_price = float(solusdt_position['entryPrice'])
        
        # Obtener precio actual
        ticker = client.futures_symbol_ticker(symbol='SOLUSDT')
        current_price = float(ticker['price'])
        
        print(f"\n📊 POSICIÓN SOLUSDT:")
        print(f"   Size: {position_amt}")
        print(f"   Entry: ${entry_price:.2f}")
        print(f"   Current: ${current_price:.2f}")
        print(f"   PnL: {((current_price - entry_price) / entry_price) * 100:+.2f}%")
        
        # 3. Calcular Stop Loss óptimo
        # Para posición LONG, SL debe estar por debajo del precio actual
        if position_amt > 0:  # Posición LONG
            # Opción conservadora: 1.5% por debajo del precio actual
            # O 2% por debajo del precio de entrada, el que esté más cerca
            
            sl_option1 = current_price * 0.985  # 1.5% por debajo del actual
            sl_option2 = entry_price * 0.98     # 2% por debajo de entrada
            
            # Elegir el SL más conservador (más alto)
            recommended_sl = max(sl_option1, sl_option2)
            
            # Ajustar para estar por debajo del precio actual
            if recommended_sl >= current_price:
                recommended_sl = current_price * 0.985
            
        else:  # Posición SHORT (no debería ser el caso)
            recommended_sl = current_price * 1.015
        
        print(f"\n🎯 CÁLCULO DE STOP LOSS:")
        print(f"   Opción 1 (1.5% del actual): ${sl_option1:.2f}")
        print(f"   Opción 2 (2% de entrada): ${sl_option2:.2f}")
        print(f"   ✅ SL Recomendado: ${recommended_sl:.2f}")
        
        # Verificar distancia del SL
        sl_distance_pct = ((current_price - recommended_sl) / current_price) * 100
        print(f"   📊 Distancia SL: {sl_distance_pct:.2f}%")
        
        if sl_distance_pct < 0.5:
            print("   ⚠️ SL muy cerca - ajustando...")
            recommended_sl = current_price * 0.995  # 0.5% buffer mínimo
            sl_distance_pct = 0.5
        
        # 4. Verificar si ya existe SL
        existing_orders = client.futures_get_open_orders(symbol='SOLUSDT')
        existing_sl = None
        
        for order in existing_orders:
            if order['type'] == 'STOP_MARKET':
                existing_sl = order
                print(f"   ⚠️ SL existente encontrado: ${float(order['stopPrice']):.2f}")
                break
        
        # 5. Configurar Stop Loss
        print(f"\n⚡ CONFIGURANDO STOP LOSS:")
        
        if existing_sl:
            # Cancelar SL existente
            cancel_result = client.futures_cancel_order(
                symbol='SOLUSDT',
                orderId=existing_sl['orderId']
            )
            print(f"   ✅ SL anterior cancelado")
        
        # Crear nuevo Stop Loss
        sl_order = client.futures_create_order(
            symbol='SOLUSDT',
            side='SELL',  # Para cerrar posición LONG
            type='STOP_MARKET',
            stopPrice=round(recommended_sl, 2),
            closePosition=True,
            workingType='MARK_PRICE',
            timeInForce='GTC'
        )
        
        print(f"   ✅ STOP LOSS CONFIGURADO")
        print(f"   📋 Order ID: {sl_order['orderId']}")
        print(f"   🎯 Precio SL: ${recommended_sl:.2f}")
        print(f"   🛡️ Protección: {sl_distance_pct:.1f}% buffer")
        
        # 6. Verificar configuración completa
        print(f"\n📊 PROTECCIÓN COMPLETA VERIFICADA:")
        
        # Obtener todas las órdenes activas
        all_orders = client.futures_get_open_orders(symbol='SOLUSDT')
        
        sl_configured = False
        tp_configured = False
        
        for order in all_orders:
            if order['type'] == 'STOP_MARKET':
                sl_price = float(order['stopPrice'])
                sl_configured = True
                print(f"   🛡️ Stop Loss: ${sl_price:.2f} ✅")
            elif order['type'] == 'TAKE_PROFIT_MARKET':
                tp_price = float(order['stopPrice'])
                tp_configured = True
                print(f"   🎯 Take Profit: ${tp_price:.2f} ✅")
        
        # 7. Evaluación final de riesgo
        if sl_configured and tp_configured:
            protection_status = "✅ COMPLETAMENTE PROTEGIDA"
        elif sl_configured:
            protection_status = "🛡️ PROTEGIDA CONTRA PÉRDIDAS"
        else:
            protection_status = "❌ SIN PROTECCIÓN"
        
        print(f"\n🎯 ESTADO FINAL: {protection_status}")
        
        # Calcular pérdida máxima potencial
        if sl_configured:
            max_loss = (current_price - recommended_sl) * abs(position_amt)
            max_loss_pct = (max_loss / 5.86) * 100  # vs balance total
            
            print(f"   💰 Pérdida máxima: ${max_loss:.2f} ({max_loss_pct:.1f}% del balance)")
            
            if max_loss_pct < 5:
                risk_level = "✅ BAJO RIESGO"
            elif max_loss_pct < 10:
                risk_level = "⚠️ RIESGO MODERADO"
            else:
                risk_level = "🚨 ALTO RIESGO"
            
            print(f"   📊 Nivel de riesgo: {risk_level}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error configurando Stop Loss: {e}")
        return False

def final_protection_summary():
    """Resumen final del estado de protección"""
    print(f"\n" + "="*60)
    print(f"📋 RESUMEN FINAL DE PROTECCIÓN")
    print(f"="*60)
    
    client = get_um_futures_client()
    
    try:
        # Balance
        account = client.futures_account()
        total_balance = float(account['totalWalletBalance'])
        available_balance = float(account['availableBalance'])
        
        # Posiciones
        positions = client.futures_position_information()
        active_count = 0
        
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                active_count += 1
        
        # Órdenes protectoras
        orders = client.futures_get_open_orders()
        sl_count = sum(1 for o in orders if o['type'] == 'STOP_MARKET')
        tp_count = sum(1 for o in orders if o['type'] == 'TAKE_PROFIT_MARKET')
        
        print(f"💰 Balance: ${total_balance:.2f} total | ${available_balance:.2f} disponible")
        print(f"📈 Posiciones activas: {active_count}")
        print(f"🛡️ Stop Losses activos: {sl_count}")
        print(f"🎯 Take Profits activos: {tp_count}")
        
        # Estado de protección
        if active_count == sl_count:
            protection_status = "✅ TODAS LAS POSICIONES PROTEGIDAS"
        elif sl_count > 0:
            protection_status = f"⚠️ {sl_count}/{active_count} POSICIONES PROTEGIDAS"
        else:
            protection_status = "❌ SIN PROTECCIÓN"
        
        print(f"\n🎯 ESTADO: {protection_status}")
        print(f"💡 Recomendación: Monitoreo cada 15-30 minutos")
        
    except Exception as e:
        print(f"❌ Error en resumen: {e}")

if __name__ == "__main__":
    success = configure_solusdt_stop_loss()
    
    if success:
        final_protection_summary()
        print(f"\n✅ STOP LOSS CONFIGURADO EXITOSAMENTE")
        print(f"🛡️ PROTECCIÓN DE CAPITAL COMPLETADA")
    else:
        print(f"\n❌ ERROR EN CONFIGURACIÓN")
        print(f"🚨 REQUIERE CONFIGURACIÓN MANUAL")
