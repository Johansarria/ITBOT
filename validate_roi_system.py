#!/usr/bin/env python3
"""
Validación completa del sistema para ROI >= 13%
"""
import asyncio
import json
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

import config
from utils.binance_client import get_binance_client, get_um_futures_client
from utils.risk_manager import cargar_umbrales_optimizado

async def validate_roi_system():
    print("🔍 VALIDACIÓN COMPLETA DEL SISTEMA ROI >= 13%")
    print("=" * 60)
    
    # 1. Configuración de ROI
    print("\n📊 1. CONFIGURACIÓN DE ROI:")
    min_roi = config.settings.MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT
    print(f"   ✅ ROI Mínimo para Entrada: {min_roi}%")
    
    if min_roi >= 13.0:
        print(f"   ✅ CUMPLE: ROI mínimo {min_roi}% >= 13%")
    else:
        print(f"   ❌ NO CUMPLE: ROI mínimo {min_roi}% < 13%")
        print(f"   📝 RECOMENDACIÓN: Ajustar MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT a >= 13.0")
    
    # 2. Configuración de ML y Umbrales
    print("\n🤖 2. CONFIGURACIÓN ML Y UMBRALES:")
    print(f"   ML_THRESHOLD_HIGH: {config.settings.ML_THRESHOLD_HIGH}")
    print(f"   ML_THRESHOLD_MEDIUM: {config.settings.ML_THRESHOLD_MEDIUM}")  
    print(f"   ML_THRESHOLD_LOW: {config.settings.ML_THRESHOLD_LOW}")
    print(f"   ML_DYNAMIC_THRESHOLDS: {config.settings.ML_DYNAMIC_THRESHOLDS}")
    
    # Cargar umbrales optimizados
    print("\n   📋 Umbrales Optimizados:")
    try:
        cargar_umbrales_optimizado()
        if os.path.exists("best_risk_thresholds.json"):
            with open("best_risk_thresholds.json", "r") as f:
                optimized = json.load(f)
                print(f"   ✅ Umbral Alto Optimizado: {optimized.get('umbral_alto', 'N/A')}")
                print(f"   ✅ Umbral Medio Optimizado: {optimized.get('umbral_medio', 'N/A')}")
                print(f"   ✅ Umbral Bajo Optimizado: {optimized.get('umbral_bajo', 'N/A')}")
        else:
            print("   ❌ No se encontraron umbrales optimizados")
    except Exception as e:
        print(f"   ❌ Error cargando umbrales: {e}")
    
    # 3. Configuración de Trading
    print("\n💰 3. CONFIGURACIÓN DE TRADING:")
    print(f"   Leverage: {config.settings.MICRO_TRADE_LEVERAGE}x")
    print(f"   Max USDT por Trade: ${config.settings.MICRO_TRADE_MAX_USDT}")
    print(f"   Take Profit: {config.settings.RISK_PER_TRADE_TAKE_PROFIT_PCT}%")
    print(f"   Stop Loss: {config.settings.RISK_PER_TRADE_STOP_LOSS_PCT}%")
    
    # Calcular ratio Risk/Reward
    tp = config.settings.RISK_PER_TRADE_TAKE_PROFIT_PCT
    sl = config.settings.RISK_PER_TRADE_STOP_LOSS_PCT
    rr_ratio = tp / sl if sl > 0 else 0
    print(f"   Risk/Reward Ratio: 1:{rr_ratio:.1f}")
    
    if rr_ratio >= 2.0:
        print("   ✅ EXCELENTE: Ratio R/R >= 2.0")
    elif rr_ratio >= 1.5:
        print("   ⚠️  ACEPTABLE: Ratio R/R >= 1.5")
    else:
        print("   ❌ MEJORAR: Ratio R/R < 1.5")
    
    # 4. Simulación de ROI
    print("\n🎯 4. SIMULACIÓN DE ROI:")
    leverage = config.settings.MICRO_TRADE_LEVERAGE
    max_usdt = config.settings.MICRO_TRADE_MAX_USDT
    
    # Calcular margen usado
    margin_used = max_usdt / leverage
    print(f"   Capital por Trade: ${max_usdt}")
    print(f"   Margen Usado (${max_usdt} / {leverage}x): ${margin_used:.2f}")
    
    # Simular ganancias
    tp_gain_usdt = max_usdt * (tp / 100)
    tp_roi_on_margin = (tp_gain_usdt / margin_used) * 100 if margin_used > 0 else 0
    
    sl_loss_usdt = max_usdt * (sl / 100)
    sl_roi_on_margin = (sl_loss_usdt / margin_used) * 100 if margin_used > 0 else 0
    
    print(f"   Si TP ({tp}%): Ganancia ${tp_gain_usdt:.2f} → ROI sobre margen: {tp_roi_on_margin:.1f}%")
    print(f"   Si SL ({sl}%): Pérdida ${sl_loss_usdt:.2f} → ROI sobre margen: -{sl_roi_on_margin:.1f}%")
    
    if tp_roi_on_margin >= 13.0:
        print(f"   ✅ CUMPLE: ROI TP {tp_roi_on_margin:.1f}% >= 13%")
    else:
        print(f"   ❌ NO CUMPLE: ROI TP {tp_roi_on_margin:.1f}% < 13%")
        
        # Calcular ajustes necesarios
        required_tp_pct = (13.0 * margin_used / max_usdt) * 100
        print(f"   📝 NECESARIO: TP >= {required_tp_pct:.1f}% para ROI >= 13%")
    
    # 5. Balance Disponible
    print("\n💳 5. BALANCE DISPONIBLE:")
    try:
        fut_client = get_um_futures_client()
        fut_balances = fut_client.futures_account_balance()
        
        total_available = 0
        for balance in fut_balances:
            asset = balance.get('asset', '').upper()
            if asset in ['USDT', 'USDC']:
                avail = float(balance.get('balance', 0))
                if avail > 0:
                    print(f"   {asset}: ${avail:.2f}")
                    total_available += avail
        
        print(f"   💰 Total Disponible: ${total_available:.2f}")
        
        # Calcular número de trades posibles
        trades_possible = int(total_available / margin_used) if margin_used > 0 else 0
        print(f"   📊 Trades Simultáneos Posibles: {trades_possible}")
        
        if trades_possible >= 1:
            print("   ✅ Balance suficiente para operar")
        else:
            print("   ❌ Balance insuficiente")
            
    except Exception as e:
        print(f"   ❌ Error obteniendo balance: {e}")
    
    # 6. Recomendaciones Finales
    print("\n🎯 6. RECOMENDACIONES PARA ROI >= 13%:")
    
    recommendations = []
    
    if min_roi < 13.0:
        recommendations.append("Aumentar MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT a >= 13.0")
    
    if tp_roi_on_margin < 13.0:
        required_tp = (13.0 * margin_used / max_usdt) * 100
        recommendations.append(f"Aumentar RISK_PER_TRADE_TAKE_PROFIT_PCT a >= {required_tp:.1f}%")
    
    if rr_ratio < 2.0:
        recommendations.append("Mejorar ratio Risk/Reward a >= 2.0")
        
    if config.settings.ML_THRESHOLD_LOW < 0.6:
        recommendations.append("Considerar aumentar ML_THRESHOLD_LOW para mayor selectividad")
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
    else:
        print("   ✅ Sistema ya optimizado para ROI >= 13%")
    
    print("\n" + "=" * 60)
    print("✅ Validación completada!")

if __name__ == "__main__":
    asyncio.run(validate_roi_system())
