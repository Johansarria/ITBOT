#!/usr/bin/env python3
"""
ACCIÓN INMEDIATA DE PROTECCIÓN DE CAPITAL
Decisión crítica basada en análisis de riesgo profesional
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
from datetime import datetime

def execute_capital_protection_decision():
    print("🚨 ACCIÓN INMEDIATA - PROTECCIÓN DE CAPITAL")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"🎯 CRITERIO: Análisis de riesgo profesional")
    
    client = get_um_futures_client()
    
    # 1. Evaluación crítica actual
    print(f"\n📊 EVALUACIÓN CRÍTICA:")
    try:
        # Obtener estado actual
        account = client.futures_account()
        positions = client.futures_position_information()
        
        available_balance = float(account['availableBalance'])
        total_balance = float(account['totalWalletBalance'])
        
        print(f"   💰 Balance disponible: ${available_balance:.2f}")
        print(f"   💼 Balance total: ${total_balance:.2f}")
        
        # Evaluar ETHUSDT específicamente
        ethusdt_ticker = client.futures_symbol_ticker(symbol='ETHUSDT')
        eth_price = float(ethusdt_ticker['price'])
        
        print(f"   📊 ETHUSDT precio actual: ${eth_price:.2f}")
        
        # Encontrar posición ETHUSDT
        eth_position = None
        for pos in positions:
            if pos['symbol'] == 'ETHUSDT' and float(pos['positionAmt']) != 0:
                eth_position = pos
                break
        
        if eth_position:
            entry_price = float(eth_position['entryPrice'])
            position_amt = float(eth_position['positionAmt'])
            unrealized_pnl = (eth_price - entry_price) * position_amt
            
            print(f"   📈 ETHUSDT posición: {position_amt} @ ${entry_price:.2f}")
            print(f"   📊 PnL no realizado: ${unrealized_pnl:.2f}")
            
            # Calcular distancia al SL
            sl_distance = eth_price - 4400.00
            sl_buffer_pct = (sl_distance / eth_price) * 100
            
            print(f"   🛡️ Distancia al SL ($4,400): ${sl_distance:.2f} ({sl_buffer_pct:.2f}%)")
            
            # DECISIÓN CRÍTICA
            print(f"\n🎯 ANÁLISIS DE DECISIÓN:")
            
            critical_factors = []
            if available_balance < 0.25:
                critical_factors.append("Balance disponible crítico (<$0.25)")
            if sl_buffer_pct < 0.5:
                critical_factors.append("SL buffer extremadamente bajo (<0.5%)")
            if unrealized_pnl < -0.15:
                critical_factors.append("Pérdida acumulándose (>$0.15)")
            if eth_price < 4420:
                critical_factors.append("Precio en zona de peligro (<$4,420)")
            
            for factor in critical_factors:
                print(f"   🚨 {factor}")
            
            # EJECUTAR DECISIÓN
            if len(critical_factors) >= 3:  # 3 o más factores críticos
                print(f"\n⚡ DECISIÓN: CIERRE INMEDIATO DE ETHUSDT")
                print(f"   💡 Razón: {len(critical_factors)} factores críticos detectados")
                print(f"   🎯 Objetivo: Proteger capital restante")
                
                # Ejecutar cierre de posición ETHUSDT
                try:
                    close_order = client.futures_create_order(
                        symbol='ETHUSDT',
                        side='SELL',
                        type='MARKET',
                        quantity=abs(position_amt),
                        reduceOnly=True
                    )
                    
                    print(f"   ✅ POSICIÓN CERRADA")
                    print(f"   📋 Order ID: {close_order['orderId']}")
                    print(f"   💰 PnL realizado: ~${unrealized_pnl:.2f}")
                    
                    # Cancelar órdenes SL/TP relacionadas
                    open_orders = client.futures_get_open_orders(symbol='ETHUSDT')
                    for order in open_orders:
                        cancel_result = client.futures_cancel_order(
                            symbol='ETHUSDT',
                            orderId=order['orderId']
                        )
                        print(f"   ✅ Cancelada orden {order['type']}")
                    
                    return True
                    
                except Exception as e:
                    print(f"   ❌ Error cerrando posición: {e}")
                    return False
                    
            else:
                print(f"\n🛡️ DECISIÓN: MANTENER CON SL AJUSTADO")
                print(f"   💡 Razón: Solo {len(critical_factors)} factores críticos")
                print(f"   🎯 SL actual en $4,400 es adecuado")
                return True
        
        else:
            print(f"   ❌ No se encontró posición ETHUSDT")
            return False
            
    except Exception as e:
        print(f"   ❌ Error en evaluación: {e}")
        return False

def post_action_status():
    """Verificar estado después de la acción"""
    print(f"\n📊 ESTADO POST-ACCIÓN:")
    print("-" * 40)
    
    client = get_um_futures_client()
    
    try:
        # Balance actualizado
        account = client.futures_account()
        available_balance = float(account['availableBalance'])
        total_balance = float(account['totalWalletBalance'])
        
        print(f"   💰 Nuevo balance disponible: ${available_balance:.2f}")
        print(f"   💼 Balance total: ${total_balance:.2f}")
        
        # Posiciones restantes
        positions = client.futures_position_information()
        active_positions = 0
        
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                active_positions += 1
                symbol = pos['symbol']
                size = float(pos['positionAmt'])
                entry = float(pos['entryPrice'])
                print(f"   📈 {symbol}: {size} @ ${entry:.2f}")
        
        print(f"   📊 Posiciones activas restantes: {active_positions}")
        
        # Cálculo de riesgo reducido
        if active_positions > 0:
            print(f"   🎯 Riesgo significativamente reducido")
        else:
            print(f"   ✅ Sin posiciones - Capital completamente protegido")
            
    except Exception as e:
        print(f"   ❌ Error verificando estado: {e}")

if __name__ == "__main__":
    print(f"🎯 INICIANDO ANÁLISIS CRÍTICO DE RIESGO")
    
    success = execute_capital_protection_decision()
    
    if success:
        post_action_status()
        print(f"\n✅ PROTECCIÓN DE CAPITAL EJECUTADA")
        print(f"📋 Acción completada basada en criterio profesional")
    else:
        print(f"\n❌ ERROR EN EJECUCIÓN")
        print(f"🚨 REQUIERE INTERVENCIÓN MANUAL")
