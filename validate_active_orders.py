#!/usr/bin/env python3
"""
Validación completa de órdenes activas, recálculo y sugerencias de optimización
"""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.abspath('.'))

import config
from utils.binance_client import get_binance_client, get_um_futures_client

async def validate_active_orders():
    print("🔍 VALIDACIÓN COMPLETA DE ÓRDENES ACTIVAS")
    print("=" * 70)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. Obtener balance actual
        print("\n💰 1. ESTADO DEL BALANCE:")
        fut_client = get_um_futures_client()
        fut_balances = fut_client.futures_account_balance()
        
        total_balance = 0
        available_balance = 0
        for balance in fut_balances:
            asset = balance.get('asset', '').upper()
            if asset in ['USDT', 'USDC']:
                bal = float(balance.get('balance', 0))
                avail = float(balance.get('availableBalance', 0))
                if bal != 0 or avail != 0:
                    print(f"   {asset}: Balance=${bal:.4f}, Disponible=${avail:.4f}")
                    total_balance += bal
                    available_balance += avail
        
        print(f"   💰 TOTAL: Balance=${total_balance:.4f}, Disponible=${available_balance:.4f}")
        
        # 2. Obtener posiciones abiertas
        print("\n📊 2. POSICIONES ABIERTAS:")
        positions = fut_client.futures_position_information()
        open_positions = []
        
        for pos in positions:
            size = float(pos.get('positionAmt', 0))
            if size != 0:  # Posición abierta
                symbol = pos.get('symbol', '')
                side = 'LONG' if size > 0 else 'SHORT'
                entry_price = float(pos.get('entryPrice', 0))
                mark_price = float(pos.get('markPrice', 0))
                unrealized_pnl = float(pos.get('unRealizedProfit', 0))
                roe = float(pos.get('percentage', 0))
                
                open_positions.append({
                    'symbol': symbol,
                    'side': side,
                    'size': abs(size),
                    'entry_price': entry_price,
                    'mark_price': mark_price,
                    'unrealized_pnl': unrealized_pnl,
                    'roe': roe
                })
                
                print(f"   🎯 {symbol} {side}:")
                print(f"      Cantidad: {abs(size)}")
                print(f"      Precio entrada: ${entry_price:.4f}")
                print(f"      Precio actual: ${mark_price:.4f}")
                print(f"      PnL no realizado: ${unrealized_pnl:+.4f}")
                print(f"      ROE: {roe:+.2f}%")
        
        if not open_positions:
            print("   ✅ No hay posiciones abiertas actualmente")
        
        # 3. Obtener órdenes activas
        print("\n📋 3. ÓRDENES ACTIVAS:")
        active_orders = []
        
        symbols_to_check = config.settings.ASSETS_TO_TRADE
        for symbol in symbols_to_check:
            try:
                orders = fut_client.futures_get_open_orders(symbol=symbol)
                for order in orders:
                    order_info = {
                        'symbol': order.get('symbol', ''),
                        'side': order.get('side', ''),
                        'type': order.get('type', ''),
                        'quantity': float(order.get('origQty', 0)),
                        'price': float(order.get('price', 0)),
                        'stop_price': float(order.get('stopPrice', 0)),
                        'time_in_force': order.get('timeInForce', ''),
                        'status': order.get('status', ''),
                        'order_id': order.get('orderId', ''),
                        'client_order_id': order.get('clientOrderId', ''),
                        'working_type': order.get('workingType', ''),
                        'time': order.get('time', 0)
                    }
                    active_orders.append(order_info)
                    
                    print(f"   🎯 {order_info['symbol']} - {order_info['side']} {order_info['type']}:")
                    print(f"      Cantidad: {order_info['quantity']}")
                    if order_info['price'] > 0:
                        print(f"      Precio: ${order_info['price']:.4f}")
                    if order_info['stop_price'] > 0:
                        print(f"      Stop Price: ${order_info['stop_price']:.4f}")
                    print(f"      Estado: {order_info['status']}")
                    print(f"      Working Type: {order_info['working_type']}")
            
            except Exception as e:
                print(f"   ⚠️  Error obteniendo órdenes de {symbol}: {e}")
        
        if not active_orders:
            print("   ✅ No hay órdenes activas pendientes")
        
        # 4. Análisis y recálculos
        print("\n🧮 4. ANÁLISIS Y RECÁLCULOS:")
        
        # Configuración actual
        max_usdt = config.settings.MICRO_TRADE_MAX_USDT
        leverage = config.settings.MICRO_TRADE_LEVERAGE
        tp_pct = config.settings.RISK_PER_TRADE_TAKE_PROFIT_PCT
        sl_pct = config.settings.RISK_PER_TRADE_STOP_LOSS_PCT
        min_roi = config.settings.MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT
        
        print(f"   📊 Configuración actual:")
        print(f"      Max USDT: ${max_usdt}")
        print(f"      Leverage: {leverage}x")
        print(f"      TP: {tp_pct}% | SL: {sl_pct}%")
        print(f"      ROI mínimo: {min_roi}%")
        
        # Recalcular métricas
        margin_per_trade = max_usdt / leverage
        tp_gain = max_usdt * (tp_pct / 100)
        sl_loss = max_usdt * (sl_pct / 100)
        roi_tp = (tp_gain / margin_per_trade * 100)
        roi_sl = (sl_loss / margin_per_trade * 100)
        
        print(f"\n   🎯 Métricas por trade:")
        print(f"      Margen usado: ${margin_per_trade:.2f}")
        print(f"      Ganancia TP: ${tp_gain:.2f} → ROI: +{roi_tp:.1f}%")
        print(f"      Pérdida SL: ${sl_loss:.2f} → ROI: -{roi_sl:.1f}%")
        print(f"      Risk/Reward: 1:{tp_pct/sl_pct:.1f}")
        
        # 5. Evaluación de riesgo actual
        print("\n🛡️  5. EVALUACIÓN DE RIESGO:")
        
        total_exposure = sum([abs(pos['size']) * pos['entry_price'] for pos in open_positions])
        margin_used = sum([abs(pos['size']) * pos['entry_price'] / leverage for pos in open_positions])
        
        print(f"   📊 Exposición total: ${total_exposure:.2f}")
        print(f"   📊 Margen usado: ${margin_used:.2f}")
        print(f"   📊 Margen disponible: ${available_balance:.2f}")
        print(f"   📊 Utilización: {(margin_used/max(available_balance, 0.01)*100):.1f}%")
        
        # Capacidad de trades adicionales
        additional_trades = int(available_balance / margin_per_trade) if margin_per_trade > 0 else 0
        print(f"   🎯 Trades adicionales posibles: {additional_trades}")
        
        # 6. SUGERENCIAS DE OPTIMIZACIÓN
        print("\n🎯 6. SUGERENCIAS DE OPTIMIZACIÓN (PROTEGER CAPITAL + MAXIMIZAR GANANCIAS):")
        
        suggestions = []
        
        # Análisis de posiciones abiertas
        if open_positions:
            for pos in open_positions:
                symbol = pos['symbol']
                pnl = pos['unrealized_pnl']
                roe = pos['roe']
                
                print(f"\n   📈 {symbol} ({pos['side']}):")
                
                if pnl > 0 and roe > 1.0:
                    suggestions.append(f"✅ {symbol}: Considerar activar trailing stop (ganancia +{roe:.1f}%)")
                    print(f"      ✅ GANANDO: Activar trailing stop para proteger ganancias")
                elif pnl > 0 and roe > 0.5:
                    suggestions.append(f"⚡ {symbol}: Mover SL a break-even (ganancia +{roe:.1f}%)")
                    print(f"      ⚡ GANANDO: Mover SL a break-even")
                elif pnl < 0 and roe < -1.5:
                    suggestions.append(f"⚠️  {symbol}: Considerar cierre manual (pérdida {roe:.1f}%)")
                    print(f"      ⚠️  PERDIENDO: Revisar fundamentales del trade")
                else:
                    print(f"      📊 NEUTRAL: Mantener vigilancia")
        
        # Sugerencias generales de optimización
        print(f"\n   🚀 OPTIMIZACIONES GENERALES:")
        
        # 1. Protección de capital
        if len(open_positions) >= 3:
            suggestions.append("🛡️  Limitar nuevas entradas - Ya tienes 3+ posiciones")
            print("      🛡️  PROTECCIÓN: Evitar sobreexposición")
        
        # 2. Maximización de ganancias
        if roi_tp >= 20 and additional_trades >= 2:
            suggestions.append(f"🚀 ROI excelente ({roi_tp:.1f}%) - Aprovechar oportunidades")
            print(f"      🚀 MAXIMIZACIÓN: ROI de {roi_tp:.1f}% permite trading activo")
        
        # 3. Gestión de riesgo
        margin_usage = (margin_used / max(available_balance, 0.01)) * 100
        if margin_usage > 70:
            suggestions.append("⚠️  Alto uso de margen - Reducir exposición")
            print("      ⚠️  RIESGO: Reducir exposición por alto uso de margen")
        elif margin_usage < 30:
            suggestions.append("💡 Bajo uso de margen - Oportunidad de crecimiento")
            print("      💡 OPORTUNIDAD: Margen infrautilizado")
        
        # 7. RECOMENDACIONES ESPECÍFICAS
        print("\n📋 7. RECOMENDACIONES ESPECÍFICAS:")
        
        # Obtener precios actuales para análisis
        client = await get_binance_client()
        current_prices = {}
        for symbol in symbols_to_check:
            try:
                ticker = await client.get_symbol_ticker(symbol=symbol)
                current_prices[symbol] = float(ticker['price'])
            except:
                pass
        
        # Análisis de cada símbolo
        for symbol in symbols_to_check:
            if symbol in current_prices:
                price = current_prices[symbol]
                print(f"\n   🎯 {symbol} (${price:,.2f}):")
                
                # Verificar si hay posición abierta
                pos_open = any(pos['symbol'] == symbol for pos in open_positions)
                orders_open = any(order['symbol'] == symbol for order in active_orders)
                
                if pos_open:
                    pos = next(pos for pos in open_positions if pos['symbol'] == symbol)
                    if pos['roe'] > 2:
                        print("      ✅ ACCIÓN: Activar trailing stop")
                    elif pos['roe'] > 0.5:
                        print("      📈 ACCIÓN: Mover SL a break-even")
                    elif pos['roe'] < -1.5:
                        print("      ⚠️  ACCIÓN: Evaluar cierre anticipado")
                    else:
                        print("      📊 ACCIÓN: Mantener vigilancia")
                elif orders_open:
                    print("      ⏳ ESTADO: Órdenes pendientes")
                else:
                    print("      💡 ESTADO: Disponible para nueva entrada")
        
        # 8. PLAN DE ACCIÓN INMEDIATO
        print("\n⚡ 8. PLAN DE ACCIÓN INMEDIATO:")
        
        priority_actions = []
        
        # Prioridad 1: Proteger ganancias
        winning_positions = [pos for pos in open_positions if pos['roe'] > 1.0]
        if winning_positions:
            priority_actions.append("🥇 PRIORIDAD 1: Proteger ganancias con trailing stops")
            for pos in winning_positions:
                print(f"      🎯 {pos['symbol']}: Trailing stop en +{pos['roe']:.1f}%")
        
        # Prioridad 2: Gestionar pérdidas
        losing_positions = [pos for pos in open_positions if pos['roe'] < -1.0]
        if losing_positions:
            priority_actions.append("🥈 PRIORIDAD 2: Revisar posiciones perdedoras")
            for pos in losing_positions:
                print(f"      ⚠️  {pos['symbol']}: Evaluar en {pos['roe']:.1f}%")
        
        # Prioridad 3: Optimizar nuevas entradas
        if additional_trades > 0 and margin_usage < 50:
            priority_actions.append("🥉 PRIORIDAD 3: Buscar oportunidades de alta probabilidad")
            print(f"      💡 Espacio para {additional_trades} trades adicionales")
        
        # Resumen final
        print("\n" + "="*70)
        print("🎯 RESUMEN EJECUTIVO:")
        print(f"   💰 Balance disponible: ${available_balance:.2f}")
        print(f"   📊 Posiciones abiertas: {len(open_positions)}")
        print(f"   📋 Órdenes activas: {len(active_orders)}")
        print(f"   🎯 ROI por trade: +{roi_tp:.1f}% / -{roi_sl:.1f}%")
        print(f"   🛡️  Uso de margen: {margin_usage:.1f}%")
        
        print(f"\n✅ ESTADO GENERAL: ", end="")
        if margin_usage > 70:
            print("⚠️  ALTO RIESGO - Reducir exposición")
        elif len(winning_positions) > len(losing_positions):
            print("🟢 POSITIVO - Proteger ganancias")
        elif additional_trades >= 2 and margin_usage < 50:
            print("💡 OPORTUNIDAD - Espacio para crecimiento")
        else:
            print("📊 ESTABLE - Mantener vigilancia")
        
        print("\n" + "="*70)
        print("✅ Validación completada!")
        
        return {
            'balance': available_balance,
            'positions': open_positions,
            'orders': active_orders,
            'suggestions': suggestions,
            'priorities': priority_actions
        }
        
    except Exception as e:
        print(f"❌ Error durante validación: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(validate_active_orders())
