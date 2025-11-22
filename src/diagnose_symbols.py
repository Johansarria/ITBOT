#!/usr/bin/env python3
"""
Diagnóstico detallado de símbolos problemáticos
"""

import sys
sys.path.append('.')
from binance_data_provider import BinanceDataProvider
from datetime import datetime, timedelta
import traceback

def diagnose_symbol(provider, symbol):
    """Diagnostica un símbolo específico"""
    print(f'\n📊 ANALIZANDO {symbol}:')
    print('-' * 30)
    
    results = {
        'symbol': symbol,
        'current_price': None,
        'data_1h': False,
        'data_5m': False,
        'symbol_info': None,
        'errors': []
    }
    
    try:
        # 1. Verificar precio actual
        print('1️⃣ Precio actual:')
        current_price = provider.get_current_price(symbol)
        if current_price:
            results['current_price'] = current_price
            print(f'   ✅ Precio: ${current_price:.6f}')
        else:
            print('   ❌ No se pudo obtener precio')
            results['errors'].append('No se pudo obtener precio actual')
            
        # 2. Verificar datos de 1 hora
        print('2️⃣ Datos 1H (últimas 10 velas):')
        try:
            data_1h = provider.get_historical_data(symbol, '1h', 10)
            if data_1h is not None and len(data_1h) > 0:
                results['data_1h'] = True
                print(f'   ✅ Obtenidas {len(data_1h)} velas')
                print(f'   📅 Última vela: {data_1h.index[-1]}')
                last_price = data_1h["close"].iloc[-1]
                print(f'   💰 Último precio: ${last_price:.6f}')
            else:
                print('   ❌ No se pudieron obtener datos 1H')
                results['errors'].append('No se pudieron obtener datos 1H')
        except Exception as e:
            print(f'   ❌ Error en datos 1H: {str(e)}')
            results['errors'].append(f'Error datos 1H: {str(e)}')
            
        # 3. Verificar datos de 5 minutos
        print('3️⃣ Datos 5m (últimas 10 velas):')
        try:
            data_5m = provider.get_historical_data(symbol, '5m', 10)
            if data_5m is not None and len(data_5m) > 0:
                results['data_5m'] = True
                print(f'   ✅ Obtenidas {len(data_5m)} velas')
                print(f'   📅 Última vela: {data_5m.index[-1]}')
                last_price_5m = data_5m["close"].iloc[-1]
                print(f'   💰 Último precio: ${last_price_5m:.6f}')
            else:
                print('   ❌ No se pudieron obtener datos 5m')
                results['errors'].append('No se pudieron obtener datos 5m')
        except Exception as e:
            print(f'   ❌ Error en datos 5m: {str(e)}')
            results['errors'].append(f'Error datos 5m: {str(e)}')
            
        # 4. Verificar información del símbolo
        print('4️⃣ Información del símbolo:')
        try:
            info = provider.client.get_symbol_info(symbol)
            if info:
                results['symbol_info'] = info
                status = info['status']
                trading = info.get('isSpotTradingAllowed', 'N/A')
                print(f'   ✅ Estado: {status}')
                print(f'   📈 Trading: {trading}')
                
                # Verificar si está activo
                if status != 'TRADING':
                    results['errors'].append(f'Símbolo no está en estado TRADING: {status}')
                    
            else:
                print('   ❌ No se pudo obtener información')
                results['errors'].append('No se pudo obtener información del símbolo')
        except Exception as e:
            print(f'   ❌ Error obteniendo info: {str(e)}')
            results['errors'].append(f'Error info símbolo: {str(e)}')
            
    except Exception as e:
        print(f'❌ ERROR GENERAL en {symbol}:')
        print(f'   {str(e)}')
        results['errors'].append(f'Error general: {str(e)}')
        
    return results

def main():
    """Función principal de diagnóstico"""
    print('🔍 DIAGNÓSTICO DETALLADO DE SÍMBOLOS PROBLEMÁTICOS')
    print('=' * 60)

    # Símbolos problemáticos
    problem_symbols = ['GBPUSDT', 'AUDUSDT', 'MATICUSDT']

    # Inicializar proveedor
    try:
        provider = BinanceDataProvider()
        print('✅ Cliente Binance inicializado correctamente')
    except Exception as e:
        print(f'❌ Error inicializando cliente Binance: {e}')
        return

    # Diagnosticar cada símbolo
    all_results = []
    for symbol in problem_symbols:
        result = diagnose_symbol(provider, symbol)
        all_results.append(result)

    # Resumen final
    print('\n' + '=' * 60)
    print('📋 RESUMEN DE DIAGNÓSTICO:')
    print('=' * 60)
    
    for result in all_results:
        symbol = result['symbol']
        errors = len(result['errors'])
        
        if errors == 0:
            status = '✅ FUNCIONANDO'
        elif errors <= 2:
            status = '⚠️ PROBLEMAS MENORES'
        else:
            status = '❌ PROBLEMAS GRAVES'
            
        print(f'{symbol}: {status} ({errors} errores)')
        
        if result['errors']:
            for error in result['errors']:
                print(f'   • {error}')
    
    print('\n🔧 DIAGNÓSTICO COMPLETADO')

if __name__ == "__main__":
    main()