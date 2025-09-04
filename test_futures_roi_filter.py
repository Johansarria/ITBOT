#!/usr/bin/env python3
"""
Prueba específica de filtro ROI >= 13% en Futuros
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.abspath('.'))

import config
from utils.binance_client import get_binance_client

async def test_futures_roi_filter():
    print("🔍 PRUEBA FILTRO ROI >= 13% EN FUTUROS")
    print("=" * 50)
    
    # Configuración actual
    max_usdt = config.settings.MICRO_TRADE_MAX_USDT
    leverage = config.settings.MICRO_TRADE_LEVERAGE
    tp_pct = config.settings.RISK_PER_TRADE_TAKE_PROFIT_PCT
    min_roi_margin = config.settings.MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT
    
    print(f"📊 Max USDT por trade: ${max_usdt}")
    print(f"📊 Leverage: {leverage}x")
    print(f"📊 Take Profit: {tp_pct}%")
    print(f"📊 ROI mínimo requerido: {min_roi_margin}%")
    
    # Calcular ROI actual
    margin_used = max_usdt / leverage
    tp_gain_usdt = max_usdt * (tp_pct / 100)
    roi_tp_on_margin = (tp_gain_usdt / margin_used * 100.0) if margin_used > 0 else 0.0
    
    print(f"\n🧮 CÁLCULOS:")
    print(f"   Margen usado: ${max_usdt} / {leverage} = ${margin_used:.2f}")
    print(f"   Ganancia TP: ${max_usdt} * {tp_pct}% = ${tp_gain_usdt:.2f}")
    print(f"   ROI sobre margen: ${tp_gain_usdt:.2f} / ${margin_used:.2f} * 100 = {roi_tp_on_margin:.1f}%")
    
    print(f"\n🎯 VALIDACIÓN FILTRO:")
    if roi_tp_on_margin >= min_roi_margin:
        print(f"   ✅ APROBADO: {roi_tp_on_margin:.1f}% >= {min_roi_margin:.1f}%")
        print("   ✅ El trade PASARÍA el filtro ROI")
    else:
        print(f"   ❌ RECHAZADO: {roi_tp_on_margin:.1f}% < {min_roi_margin:.1f}%")
        print("   ❌ El trade SERÍA RECHAZADO por ROI insuficiente")
    
    print(f"\n🔧 CONFIGURACIÓN PARA DIFERENTES ESCENARIOS:")
    
    # Escenario 1: ROI exactamente 13%
    required_tp_for_13_pct = (13.0 * margin_used / max_usdt) * 100
    print(f"   Para ROI exacto 13%: TP necesario = {required_tp_for_13_pct:.1f}%")
    
    # Escenario 2: ROI 20%
    required_tp_for_20_pct = (20.0 * margin_used / max_usdt) * 100
    print(f"   Para ROI 20%: TP necesario = {required_tp_for_20_pct:.1f}%")
    
    # Escenario 3: Con leverage diferente
    print(f"\n📈 CON DIFERENTES LEVERAGES:")
    for test_lev in [3, 5, 10, 20]:
        test_margin = max_usdt / test_lev
        test_roi = (tp_gain_usdt / test_margin * 100.0) if test_margin > 0 else 0.0
        status = "✅ PASA" if test_roi >= min_roi_margin else "❌ NO PASA"
        print(f"   Leverage {test_lev}x: ROI {test_roi:.1f}% - {status}")
    
    print(f"\n🎯 VERIFICACIÓN SISTEMA ACTUAL:")
    use_futures = config.settings.MICRO_TRADE_USE_FUTURES
    print(f"   MICRO_TRADE_USE_FUTURES: {use_futures}")
    
    if use_futures and roi_tp_on_margin >= min_roi_margin:
        print("   ✅ SISTEMA COMPLETAMENTE FUNCIONAL PARA ROI >= 13%")
    elif use_futures and roi_tp_on_margin < min_roi_margin:
        print("   ⚠️  FUTUROS HABILITADO PERO ROI INSUFICIENTE")
    else:
        print("   ❌ FUTUROS DESHABILITADO")
    
    print(f"\n" + "=" * 50)
    print("✅ Prueba de filtro ROI completada!")

if __name__ == "__main__":
    asyncio.run(test_futures_roi_filter())
