#!/usr/bin/env python3
"""
Script de prueba para verificar que el bot detecta correctamente tu balance real
"""
import asyncio
import os
import sys

# Añadir el directorio del proyecto al path
sys.path.insert(0, os.path.abspath('.'))

from utils.binance_client import get_binance_client, get_um_futures_client
from utils.order_executor import evaluar_y_ejecutar_operacion
import config

async def test_balance_detection():
    print("🔍 Probando detección de balance real...")
    
    # Test 1: Balance Spot
    print("\n📊 Test 1: Balance Spot USDT")
    try:
        client = await get_binance_client()
        balance_info = await client.get_asset_balance(asset="USDT")
        spot_balance = float(balance_info.get("free", 0.0))
        print(f"   ✅ Balance Spot USDT: ${spot_balance:.2f}")
    except Exception as e:
        print(f"   ❌ Error obteniendo balance Spot: {e}")
    
    # Test 2: Balance Futuros 
    print("\n📊 Test 2: Balance Futuros USDT")
    try:
        fut_client = get_um_futures_client()
        fut_balances = fut_client.futures_account_balance()
        if isinstance(fut_balances, list):
            usdt_items = [b for b in fut_balances if str(b.get('asset')).upper() == 'USDT']
            if usdt_items:
                item = usdt_items[0]
                avail = item.get('balance') or item.get('availableBalance') or item.get('withdrawAvailable')
                futures_balance = float(avail) if avail else 0.0
                print(f"   ✅ Balance Futuros USDT disponible: ${futures_balance:.2f}")
                print(f"   📋 Datos completos Futuros USDT: {item}")
            else:
                print("   ❌ No se encontró USDT en balances de Futuros")
        else:
            print("   ❌ Formato de respuesta de Futuros inesperado")
    except Exception as e:
        print(f"   ❌ Error obteniendo balance Futuros: {e}")
    
    # Test 3: Configuración de micro-trade
    print("\n⚙️  Test 3: Configuración de micro-trade")
    print(f"   📌 EXECUTION_TARGET: {config.settings.EXECUTION_TARGET}")
    print(f"   📌 ENABLE_MICRO_TRADE: {config.settings.ENABLE_MICRO_TRADE}")
    print(f"   📌 MICRO_TRADE_USE_FUTURES: {config.settings.MICRO_TRADE_USE_FUTURES}")
    print(f"   📌 MICRO_TRADE_MAX_USDT: {config.settings.MICRO_TRADE_MAX_USDT}")
    print(f"   📌 MICRO_TRADE_LEVERAGE: {config.settings.MICRO_TRADE_LEVERAGE}")
    
    # Test 4: Simulación de evaluación de operación (sin ejecutar)
    print("\n🧪 Test 4: Simulación de evaluación")
    resultado_mock = {
        "symbol": "BTCUSDT",
        "decision": "BUY",
        "score": 75.0
    }
    
    print(f"   📊 Simulando evaluación para {resultado_mock['symbol']}")
    print(f"   📊 Decisión simulada: {resultado_mock['decision']}")
    print(f"   📊 Score simulado: {resultado_mock['score']}")
    print("\n   💡 Para ver la detección de balance en tiempo real, se necesitaría:")
    print("      1. Una señal BUY/SELL real del ML")
    print("      2. O desbloquear temporalmente el modo LIVE")
    
    print("\n✅ Test de detección de balance completado!")

if __name__ == "__main__":
    asyncio.run(test_balance_detection())
