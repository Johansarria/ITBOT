#!/usr/bin/env python3
"""
Corrección de precisión para órdenes de futuros
"""

from binance import Client
import os
import json

def check_symbol_precision():
    """Verificar precisión de símbolos para futuros"""
    
    client = Client(
        api_key=os.getenv('BINANCE_API_KEY'),
        api_secret=os.getenv('BINANCE_SECRET_KEY')
    )
    
    try:
        print("🔍 VERIFICANDO PRECISIÓN DE SÍMBOLOS")
        print("="*50)
        
        # Obtener info de futuros
        exchange_info = client.futures_exchange_info()
        
        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        
        for symbol in symbols:
            symbol_info = next((s for s in exchange_info['symbols'] if s['symbol'] == symbol), None)
            
            if symbol_info:
                print(f"\n📊 {symbol}:")
                
                # Extraer filtros importantes
                for filter_info in symbol_info['filters']:
                    if filter_info['filterType'] == 'LOT_SIZE':
                        print(f"   📏 Cantidad:")
                        print(f"      Min: {filter_info['minQty']}")
                        print(f"      Max: {filter_info['maxQty']}")
                        print(f"      Step: {filter_info['stepSize']}")
                    
                    elif filter_info['filterType'] == 'PRICE_FILTER':
                        print(f"   💰 Precio:")
                        print(f"      Min: {filter_info['minPrice']}")
                        print(f"      Max: {filter_info['maxPrice']}")
                        print(f"      Tick: {filter_info['tickSize']}")
                    
                    elif filter_info['filterType'] == 'MIN_NOTIONAL':
                        print(f"   🎯 Notional mínimo: {filter_info['notional']}")
                
                # Precisión de cantidad
                print(f"   🔢 Precisión cantidad: {symbol_info['quantityPrecision']}")
                print(f"   🔢 Precisión precio: {symbol_info['pricePrecision']}")
                
                # Calcular ejemplo para $0.75
                ticker = client.get_symbol_ticker(symbol=symbol)
                price = float(ticker['price'])
                
                # Con apalancamiento 5x
                position_value = 0.75 * 5
                raw_quantity = position_value / price
                
                # Ajustar a step size
                step_size = float([f['stepSize'] for f in symbol_info['filters'] 
                                 if f['filterType'] == 'LOT_SIZE'][0])
                
                adjusted_qty = (raw_quantity // step_size) * step_size
                
                print(f"   💡 Ejemplo $0.75 (5x):")
                print(f"      Precio actual: ${price:.4f}")
                print(f"      Cantidad raw: {raw_quantity:.8f}")
                print(f"      Cantidad ajustada: {adjusted_qty:.8f}")
                print(f"      Valor real: ${adjusted_qty * price:.2f}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_symbol_precision()
