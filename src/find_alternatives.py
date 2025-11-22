#!/usr/bin/env python3
"""
Buscar símbolos alternativos para reemplazar los suspendidos
"""

import sys
sys.path.append('.')
from binance_data_provider import BinanceDataProvider

def check_symbol_status(provider, symbol):
    """Verifica el estado de un símbolo"""
    try:
        info = provider.client.get_symbol_info(symbol)
        if info:
            status = info['status']
            trading = info.get('isSpotTradingAllowed', False)
            return status == 'TRADING' and trading
        return False
    except:
        return False

def main():
    """Buscar símbolos alternativos activos"""
    print('🔍 BUSCANDO SÍMBOLOS ALTERNATIVOS ACTIVOS')
    print('=' * 50)

    # Inicializar proveedor
    try:
        provider = BinanceDataProvider()
        print('✅ Cliente Binance inicializado')
    except Exception as e:
        print(f'❌ Error: {e}')
        return

    # Símbolos candidatos para reemplazar los suspendidos
    candidates = {
        'Forex/Stablecoins': [
            'USDCUSDT',  # USD Coin
            'BUSDUSDT',  # Binance USD
            'TUSDUSDT',  # TrueUSD
            'DAIUSDT',   # DAI
            'FDUSDUSDT', # First Digital USD
        ],
        'Altcoins populares': [
            'SHIBUSDT',  # Shiba Inu
            'PEPEUSDT',  # Pepe
            'FLOKIUSDT', # Floki
            'BONKUSDT',  # Bonk
            'WIFUSDT',   # Dogwifhat
        ],
        'Layer 1 adicionales': [
            'APTUSDT',   # Aptos
            'SUIUSDT',   # Sui
            'INJUSDT',   # Injective
            'SEIUSDT',   # Sei
            'TIAUSDT',   # Celestia
        ],
        'DeFi adicionales': [
            'CRVUSDT',   # Curve
            'MKRUSDT',   # Maker
            'SNXUSDT',   # Synthetix
            'YFIUSDT',   # Yearn Finance
            'BALUSDT',   # Balancer
        ]
    }

    active_symbols = []
    
    for category, symbols in candidates.items():
        print(f'\n📂 {category}:')
        print('-' * 30)
        
        for symbol in symbols:
            is_active = check_symbol_status(provider, symbol)
            status_icon = '✅' if is_active else '❌'
            print(f'{status_icon} {symbol}')
            
            if is_active:
                active_symbols.append(symbol)

    print('\n' + '=' * 50)
    print('📋 RESUMEN DE SÍMBOLOS ACTIVOS ENCONTRADOS:')
    print('=' * 50)
    
    if active_symbols:
        print(f'✅ Total encontrados: {len(active_symbols)}')
        print('\nSímbolos activos:')
        for i, symbol in enumerate(active_symbols, 1):
            print(f'{i:2d}. {symbol}')
            
        # Recomendar los mejores 3 para reemplazar
        print('\n🎯 RECOMENDACIONES PARA REEMPLAZAR:')
        print('-' * 40)
        
        recommendations = []
        if 'SHIBUSDT' in active_symbols:
            recommendations.append(('SHIBUSDT', 'Reemplaza MATICUSDT - Alta volatilidad'))
        if 'APTUSDT' in active_symbols:
            recommendations.append(('APTUSDT', 'Reemplaza AUDUSDT - Layer 1 emergente'))
        if 'USDCUSDT' in active_symbols:
            recommendations.append(('USDCUSDT', 'Reemplaza GBPUSDT - Stablecoin líquida'))
        
        # Si no tenemos suficientes, agregar más
        remaining = [s for s in active_symbols if s not in [r[0] for r in recommendations]]
        while len(recommendations) < 3 and remaining:
            symbol = remaining.pop(0)
            recommendations.append((symbol, 'Símbolo alternativo activo'))
            
        for i, (symbol, reason) in enumerate(recommendations[:3], 1):
            print(f'{i}. {symbol} - {reason}')
            
    else:
        print('❌ No se encontraron símbolos activos')

    print('\n🔧 BÚSQUEDA COMPLETADA')

if __name__ == "__main__":
    main()