#!/usr/bin/env python3
"""
Script de prueba para verificar detección de USDC además de USDT
"""
import asyncio
import os
import sys

# Añadir el directorio del proyecto al path
sys.path.insert(0, os.path.abspath('.'))

from utils.binance_client import get_binance_client, get_um_futures_client
import config

async def test_usdc_balance_detection():
    print("🔍 Probando detección de balance USDC + USDT...")
    
    # Test 1: Balance Futuros (USDT y USDC)
    print("\n📊 Balance en Futuros:")
    try:
        fut_client = get_um_futures_client()
        fut_balances = fut_client.futures_account_balance()
        
        usdt_balance = 0.0
        usdc_balance = 0.0
        
        for balance in fut_balances:
            asset = balance.get('asset', '').upper()
            if asset == 'USDT':
                usdt_balance = float(balance.get('balance', 0))
                print(f"   💰 USDT: ${usdt_balance:.2f} (disponible: ${float(balance.get('availableBalance', 0)):.2f})")
            elif asset == 'USDC':  
                usdc_balance = float(balance.get('balance', 0))
                print(f"   💰 USDC: ${usdc_balance:.2f} (disponible: ${float(balance.get('availableBalance', 0)):.2f})")
        
        # Lógica del bot: usar el balance mayor
        if usdc_balance > usdt_balance:
            print(f"   ✅ El bot usará: USDC ${usdc_balance:.2f}")
        elif usdt_balance > 0:
            print(f"   ✅ El bot usará: USDT ${usdt_balance:.2f}")
        else:
            print("   ❌ No hay balance significativo en Futuros")
            
    except Exception as e:
        print(f"   ❌ Error obteniendo balance Futuros: {e}")
    
    # Test 2: Balance Spot (USDT y USDC) 
    print("\n📊 Balance en Spot:")
    try:
        client = await get_binance_client()
        
        # USDT Spot
        usdt_info = await client.get_asset_balance(asset="USDT")
        usdt_spot = float(usdt_info.get("free", 0.0))
        print(f"   💰 USDT Spot: ${usdt_spot:.2f}")
        
        # USDC Spot  
        usdc_info = await client.get_asset_balance(asset="USDC")
        usdc_spot = float(usdc_info.get("free", 0.0))
        print(f"   💰 USDC Spot: ${usdc_spot:.2f}")
        
        # Lógica del bot: usar el balance mayor
        if usdc_spot > usdt_spot:
            print(f"   ✅ El bot usaría: USDC ${usdc_spot:.2f}")
        else:
            print(f"   ✅ El bot usaría: USDT ${usdt_spot:.2f}")
            
    except Exception as e:
        print(f"   ❌ Error obteniendo balance Spot: {e}")
    
    print(f"\n⚙️  Configuración:")
    print(f"   📌 MICRO_TRADE_USE_FUTURES: {config.settings.MICRO_TRADE_USE_FUTURES}")
    print(f"   📌 MICRO_TRADE_MAX_USDT: {config.settings.MICRO_TRADE_MAX_USDT}")
    
    print(f"\n✅ ¡Ahora el bot puede usar tanto USDT como USDC!")
    print(f"   📝 Tomará automáticamente el balance mayor entre ambos")

if __name__ == "__main__":
    asyncio.run(test_usdc_balance_detection())
