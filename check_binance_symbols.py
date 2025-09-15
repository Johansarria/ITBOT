#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timedelta

def check_binance_symbols():
    """Verifica qué símbolos están disponibles en Binance"""
    try:
        # Obtener información de todos los símbolos
        url = "https://api.binance.com/api/v3/exchangeInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            symbols = [s['symbol'] for s in data['symbols'] if s['status'] == 'TRADING']
            
            # Buscar símbolos relacionados con nuestros instrumentos
            aud_symbols = [s for s in symbols if 'AUD' in s]
            cad_symbols = [s for s in symbols if 'CAD' in s]
            btc_symbols = [s for s in symbols if 'BTC' in s and 'USDT' in s]
            gold_symbols = [s for s in symbols if any(x in s for x in ['XAU', 'GOLD', 'GLD'])]
            
            print("=== SÍMBOLOS DISPONIBLES EN BINANCE ===")
            print(f"\nSímbolos con AUD ({len(aud_symbols)}):")
            for symbol in sorted(aud_symbols)[:20]:  # Mostrar primeros 20
                print(f"  - {symbol}")
            
            print(f"\nSímbolos con CAD ({len(cad_symbols)}):")
            for symbol in sorted(cad_symbols):
                print(f"  - {symbol}")
            
            print(f"\nSímbolos con BTC/USDT ({len([s for s in btc_symbols if 'USDT' in s])}):")
            for symbol in sorted([s for s in btc_symbols if 'USDT' in s])[:10]:
                print(f"  - {symbol}")
            
            print(f"\nSímbolos relacionados con ORO ({len(gold_symbols)}):")
            for symbol in sorted(gold_symbols):
                print(f"  - {symbol}")
            
            # Verificar símbolos específicos
            target_symbols = ['AUDUSDT', 'AUDCAD', 'CADUSD', 'CADUSDT', 'BTCUSDT', 'XAUUSDT']
            print("\n=== VERIFICACIÓN DE SÍMBOLOS OBJETIVO ===")
            for symbol in target_symbols:
                status = "✓ DISPONIBLE" if symbol in symbols else "❌ NO DISPONIBLE"
                print(f"  {symbol}: {status}")
                
        else:
            print(f"Error al obtener símbolos: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

def test_data_download(symbol):
    """Prueba descargar datos de un símbolo específico"""
    try:
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
        
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': '1h',
            'startTime': start_time,
            'endTime': end_time,
            'limit': 100
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ {symbol}: {len(data)} registros obtenidos")
            if data:
                print(f"  Primer precio: {data[0][4]} | Último precio: {data[-1][4]}")
        else:
            print(f"\n❌ {symbol}: Error {response.status_code}")
            
    except Exception as e:
        print(f"\n❌ {symbol}: Error - {e}")

if __name__ == "__main__":
    # Redirigir salida a archivo
    import sys
    with open('binance_symbols_check.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        
        check_binance_symbols()
        
        print("\n=== PRUEBA DE DESCARGA DE DATOS ===")
        test_symbols = ['AUDUSDT', 'BTCUSDT', 'XAUUSDT']
        for symbol in test_symbols:
            test_data_download(symbol)
    
    # Restaurar stdout
    sys.stdout = sys.__stdout__
    print("Resultados guardados en binance_symbols_check.txt")