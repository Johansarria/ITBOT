#!/usr/bin/env python3
"""
Verificar que los símbolos de reemplazo funcionen correctamente
"""

import sys
sys.path.append('.')
from binance_data_provider import BinanceDataProvider
from first_candle_breakout import FirstCandleBreakoutDetector

def test_replacement_symbols():
    """Probar los símbolos de reemplazo"""
    print('🧪 PROBANDO SÍMBOLOS DE REEMPLAZO')
    print('=' * 45)

    # Símbolos reemplazados
    replacements = {
        'USDCUSDT': 'Reemplaza GBPUSDT',
        'APTUSDT': 'Reemplaza AUDUSDT', 
        'SHIBUSDT': 'Reemplaza MATICUSDT'
    }

    # Inicializar proveedor
    try:
        provider = BinanceDataProvider()
        print('✅ Cliente Binance inicializado')
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

    # Probar cada símbolo
    all_working = True
    
    for symbol, description in replacements.items():
        print(f'\n📊 Probando {symbol} ({description}):')
        print('-' * 40)
        
        try:
            # 1. Precio actual
            price = provider.get_current_price(symbol)
            if price:
                print(f'✅ Precio actual: ${price:.6f}')
            else:
                print('❌ No se pudo obtener precio')
                all_working = False
                continue
                
            # 2. Datos históricos 1H
            data_1h = provider.get_historical_data(symbol, '1h', 10)
            if data_1h is not None and len(data_1h) > 0:
                print(f'✅ Datos 1H: {len(data_1h)} velas')
            else:
                print('❌ Error en datos 1H')
                all_working = False
                continue
                
            # 3. Datos históricos 5m
            data_5m = provider.get_historical_data(symbol, '5m', 10)
            if data_5m is not None and len(data_5m) > 0:
                print(f'✅ Datos 5m: {len(data_5m)} velas')
            else:
                print('❌ Error en datos 5m')
                all_working = False
                continue
                
            # 4. Estado del símbolo
            info = provider.client.get_symbol_info(symbol)
            if info and info['status'] == 'TRADING':
                print(f'✅ Estado: {info["status"]}')
            else:
                print(f'❌ Estado problemático: {info["status"] if info else "N/A"}')
                all_working = False
                continue
                
            print('✅ Símbolo completamente funcional')
            
        except Exception as e:
            print(f'❌ Error general: {str(e)}')
            all_working = False

    # Probar detector completo
    print('\n' + '=' * 45)
    print('🔧 PROBANDO DETECTOR COMPLETO:')
    print('=' * 45)
    
    try:
        detector = FirstCandleBreakoutDetector()
        print(f'✅ Detector inicializado con {len(detector.trading_symbols)} símbolos')
        
        # Verificar que los nuevos símbolos estén en la lista
        for symbol in replacements.keys():
            if symbol in detector.trading_symbols:
                print(f'✅ {symbol} está en la lista de trading')
            else:
                print(f'❌ {symbol} NO está en la lista de trading')
                all_working = False
                
        # Verificar que los viejos símbolos NO estén
        old_symbols = ['GBPUSDT', 'AUDUSDT', 'MATICUSDT']
        for symbol in old_symbols:
            if symbol not in detector.trading_symbols:
                print(f'✅ {symbol} (suspendido) removido correctamente')
            else:
                print(f'❌ {symbol} (suspendido) aún está en la lista')
                all_working = False
                
    except Exception as e:
        print(f'❌ Error en detector: {str(e)}')
        all_working = False

    # Resultado final
    print('\n' + '=' * 45)
    if all_working:
        print('🎉 TODOS LOS REEMPLAZOS FUNCIONAN CORRECTAMENTE')
        print('✅ Sistema listo para operar con símbolos activos')
    else:
        print('❌ ALGUNOS REEMPLAZOS TIENEN PROBLEMAS')
        print('⚠️ Revisar errores arriba')
    print('=' * 45)
    
    return all_working

if __name__ == "__main__":
    test_replacement_symbols()