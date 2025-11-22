#!/usr/bin/env python3
"""
Script temporal para probar conectividad con Binance
"""

from binance_data_provider import BinanceDataProvider
import pandas as pd
from datetime import datetime

def test_binance_connectivity():
    """Probar conectividad con Binance"""
    print('🔍 Probando conectividad con Binance...')
    
    try:
        provider = BinanceDataProvider()
        print('✅ Cliente de Binance inicializado')
        
        # Obtener datos recientes de ETHUSDT
        print('📊 Obteniendo datos de ETHUSDT...')
        data = provider.get_historical_data('ETHUSDT', '3m', limit=10)
        
        if data is not None and not data.empty:
            print(f'✅ Datos obtenidos: {len(data)} velas')
            
            # Verificar si los datos son recientes (últimos 10 minutos)
            last_timestamp = data.index[-1]  # El timestamp es el índice
            current_time = datetime.now()
            
            # Convertir a timezone naive si es necesario
            if last_timestamp.tz is not None:
                last_timestamp = last_timestamp.tz_localize(None)
            
            time_diff = current_time - last_timestamp
            
            print(f'📈 Última vela:')
            print(f'   Timestamp: {last_timestamp}')
            print(f'   Precio: ${data.iloc[-1]["close"]:.4f}')
            print(f'   Diferencia de tiempo: {time_diff}')
            
            if time_diff.total_seconds() < 600:  # 10 minutos
                print('✅ Datos están actualizados (menos de 10 minutos)')
                print('✅ Conectividad con Binance: ÉXITO')
                return True
            else:
                print('⚠️ Datos no están actualizados (más de 10 minutos)')
                print('❌ Conectividad con Binance: FALLO')
                return False
                
        else:
            print('❌ No se pudieron obtener datos')
            return False
            
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    
    return True

if __name__ == "__main__":
    success = test_binance_connectivity()
    if success:
        print('\n✅ Conectividad con Binance: OK')
    else:
        print('\n❌ Conectividad con Binance: FALLO')