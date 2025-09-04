#!/usr/bin/env python3
"""
ANÁLISIS DE RIESGO PARA SALIDAS
Evaluación completa de niveles de riesgo para exits actuales
"""

import sys
import os
sys.path.append('/app')

from utils.binance_client import get_um_futures_client
from datetime import datetime
import json

def analyze_exit_risk_levels():
    print("📊 ANÁLISIS DE RIESGO PARA SALIDAS")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    
    client = get_um_futures_client()
    
    try:
        # 1. Estado actual del balance y posiciones
        account = client.futures_account()
        positions = client.futures_position_information()
        open_orders = client.futures_get_open_orders()
        
        total_balance = float(account['totalWalletBalance'])
        available_balance = float(account['availableBalance'])
        
        print(f"\n💰 ESTADO FINANCIERO ACTUAL:")
        print(f"   Balance Total: ${total_balance:.2f}")
        print(f"   Balance Disponible: ${available_balance:.2f}")
        print(f"   Utilización: {((total_balance - available_balance)/total_balance)*100:.1f}%")
        
        # 2. Análisis de posiciones activas
        active_positions = []
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                symbol = pos['symbol']
                size = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                notional = abs(float(pos['notional']))
                
                # Obtener precio actual
                ticker = client.futures_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                
                # Calcular PnL
                pnl_usd = (current_price - entry_price) * size
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                
                active_positions.append({
                    'symbol': symbol,
                    'size': size,
                    'entry_price': entry_price,
                    'current_price': current_price,
                    'notional': notional,
                    'pnl_usd': pnl_usd,
                    'pnl_pct': pnl_pct
                })
        
        print(f"\n📊 POSICIONES ACTIVAS ({len(active_positions)}):")
        
        if not active_positions:
            print("   ✅ Sin posiciones activas - SIN RIESGO DE SALIDA")
            return {
                'overall_risk': 'NINGUNO',
                'exit_recommendations': ['Sin posiciones activas'],
                'risk_score': 0
            }
        
        # 3. Análisis de órdenes de salida existentes
        exit_orders = {}
        for order in open_orders:
            symbol = order['symbol']
            order_type = order['type']
            
            if order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                if symbol not in exit_orders:
                    exit_orders[symbol] = {}
                
                if order_type == 'STOP_MARKET':
                    exit_orders[symbol]['sl_price'] = float(order['stopPrice'])
                elif order_type == 'TAKE_PROFIT_MARKET':
                    exit_orders[symbol]['tp_price'] = float(order['stopPrice'])
        
        print(f"\n🛡️ ÓRDENES DE SALIDA CONFIGURADAS:")
        for symbol, orders in exit_orders.items():
            sl_price = orders.get('sl_price', 'N/A')
            tp_price = orders.get('tp_price', 'N/A')
            print(f"   {symbol}: SL={sl_price} | TP={tp_price}")
        
        # 4. Evaluación de riesgo por posición
        risk_analysis = []
        total_risk_score = 0
        
        for pos in active_positions:
            symbol = pos['symbol']
            current_price = pos['current_price']
            entry_price = pos['entry_price']
            pnl_pct = pos['pnl_pct']
            pnl_usd = pos['pnl_usd']
            notional = pos['notional']
            
            print(f"\n📈 ANÁLISIS DE {symbol}:")
            print(f"   Entry: ${entry_price:.2f} | Current: ${current_price:.2f}")
            print(f"   PnL: {pnl_pct:+.2f}% (${pnl_usd:+.2f})")
            print(f"   Exposición: ${notional:.2f}")
            
            # Análisis de riesgo específico
            risk_factors = []
            position_risk_score = 0
            
            # Factor 1: Distancia al Stop Loss
            if symbol in exit_orders and 'sl_price' in exit_orders[symbol]:
                sl_price = exit_orders[symbol]['sl_price']
                
                if pos['size'] > 0:  # Posición LONG
                    sl_distance_pct = ((current_price - sl_price) / current_price) * 100
                else:  # Posición SHORT
                    sl_distance_pct = ((sl_price - current_price) / current_price) * 100
                
                print(f"   🛡️ Stop Loss: ${sl_price:.2f} ({sl_distance_pct:+.2f}%)")
                
                if sl_distance_pct < 1:
                    risk_factors.append(f"SL muy cerca ({sl_distance_pct:.1f}%)")
                    position_risk_score += 30
                elif sl_distance_pct < 3:
                    risk_factors.append(f"SL cercano ({sl_distance_pct:.1f}%)")
                    position_risk_score += 15
                else:
                    print(f"   ✅ SL con buffer seguro")
            else:
                risk_factors.append("Sin Stop Loss configurado")
                position_risk_score += 25
                print(f"   ⚠️ Sin Stop Loss protector")
            
            # Factor 2: PnL actual
            if pnl_pct < -5:
                risk_factors.append(f"Pérdida significativa ({pnl_pct:.1f}%)")
                position_risk_score += 20
            elif pnl_pct < -2:
                risk_factors.append(f"Pérdida moderada ({pnl_pct:.1f}%)")
                position_risk_score += 10
            elif pnl_pct > 5:
                risk_factors.append(f"Ganancia no protegida (+{pnl_pct:.1f}%)")
                position_risk_score += 5
            
            # Factor 3: Tamaño de exposición vs balance
            exposure_pct = (notional / total_balance) * 100
            if exposure_pct > 200:
                risk_factors.append(f"Sobreexposición ({exposure_pct:.0f}%)")
                position_risk_score += 25
            elif exposure_pct > 100:
                risk_factors.append(f"Exposición alta ({exposure_pct:.0f}%)")
                position_risk_score += 10
            
            # Factor 4: Balance disponible para maniobras
            if available_balance < notional * 0.1:  # Menos del 10% para maniobras
                risk_factors.append("Balance insuficiente para ajustes")
                position_risk_score += 15
            
            # Clasificación de riesgo de la posición
            if position_risk_score >= 50:
                position_risk_level = "🚨 ALTO"
            elif position_risk_score >= 25:
                position_risk_level = "⚠️ MODERADO"
            elif position_risk_score >= 10:
                position_risk_level = "🟡 BAJO"
            else:
                position_risk_level = "✅ MÍNIMO"
            
            print(f"   📊 Factores de riesgo: {len(risk_factors)}")
            for factor in risk_factors:
                print(f"      • {factor}")
            
            print(f"   🎯 Nivel de riesgo: {position_risk_level} ({position_risk_score}/100)")
            
            risk_analysis.append({
                'symbol': symbol,
                'risk_level': position_risk_level,
                'risk_score': position_risk_score,
                'risk_factors': risk_factors,
                'recommendations': []
            })
            
            total_risk_score += position_risk_score
        
        # 5. Recomendaciones específicas de salida
        print(f"\n🎯 RECOMENDACIONES DE SALIDA:")
        
        for analysis in risk_analysis:
            symbol = analysis['symbol']
            risk_score = analysis['risk_score']
            
            recommendations = []
            
            if risk_score >= 50:
                recommendations.extend([
                    f"URGENTE: Considerar cierre inmediato de {symbol}",
                    f"Ajustar SL más conservador si se mantiene",
                    f"Reducir exposición parcialmente"
                ])
            elif risk_score >= 25:
                recommendations.extend([
                    f"Monitoreo intensivo de {symbol} cada 5-10 min",
                    f"Preparar órdenes de cierre manual",
                    f"Considerar trailing stop loss"
                ])
            else:
                recommendations.extend([
                    f"Mantener {symbol} con supervisión normal",
                    f"Evaluar mover SL a break-even si hay ganancia"
                ])
            
            analysis['recommendations'] = recommendations
            
            print(f"\n   📈 {symbol}:")
            for rec in recommendations:
                print(f"      💡 {rec}")
        
        # 6. Evaluación de riesgo general
        avg_risk_score = total_risk_score / len(active_positions) if active_positions else 0
        
        if avg_risk_score >= 40:
            overall_risk = "🚨 CRÍTICO"
            general_action = "Reducir exposición inmediatamente"
        elif avg_risk_score >= 25:
            overall_risk = "⚠️ ALTO"
            general_action = "Supervisión intensiva y preparar exits"
        elif avg_risk_score >= 15:
            overall_risk = "🟡 MODERADO"
            general_action = "Monitoreo regular y ajustes graduales"
        else:
            overall_risk = "✅ BAJO"
            general_action = "Mantener con supervisión estándar"
        
        print(f"\n" + "="*60)
        print(f"📊 EVALUACIÓN GENERAL DE RIESGO DE SALIDAS")
        print(f"="*60)
        print(f"🎯 Nivel de Riesgo: {overall_risk}")
        print(f"📊 Score Promedio: {avg_risk_score:.1f}/100")
        print(f"💡 Acción General: {general_action}")
        print(f"📈 Posiciones Activas: {len(active_positions)}")
        print(f"💰 Balance Disponible: ${available_balance:.2f}")
        
        return {
            'overall_risk': overall_risk,
            'risk_score': avg_risk_score,
            'positions_analysis': risk_analysis,
            'general_action': general_action,
            'available_balance': available_balance,
            'total_balance': total_balance
        }
        
    except Exception as e:
        print(f"❌ Error en análisis de riesgo: {e}")
        return None

if __name__ == "__main__":
    result = analyze_exit_risk_levels()
    if result:
        print(f"\n✅ ANÁLISIS DE RIESGO DE SALIDAS COMPLETADO")
        print(f"📋 Recomendación: {result['general_action']}")
    else:
        print(f"\n❌ ERROR EN ANÁLISIS DE RIESGO")
