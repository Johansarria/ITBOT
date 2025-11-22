#!/usr/bin/env python3
"""
Análisis de datos históricos de ETHUSDT alrededor de las 3:00 AM
para verificar si hubo un breakout que el sistema debería haber detectado
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from binance_data_provider import BinanceDataProvider
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def analyze_breakout_around_3am():
    """
    Analiza los datos de ETHUSDT alrededor de las 3:00 AM para detectar breakouts
    """
    print('🔍 Analizando datos de ETHUSDT alrededor de las 3:00 AM...')
    
    try:
        # Inicializar proveedor de datos
        provider = BinanceDataProvider()
        
        # Obtener datos de las últimas 6 horas con intervalos de 1 minuto
        print('📊 Obteniendo datos históricos de las últimas 6 horas...')
        data = provider.get_historical_data('ETHUSDT', '1m', limit=360)
        
        if data is None or data.empty:
            print('❌ No se pudieron obtener datos históricos')
            return False
        
        print(f'✅ Datos obtenidos: {len(data)} velas de 1 minuto')
        print(f'📅 Rango de tiempo: {data.index[0]} a {data.index[-1]}')
        
        # Filtrar datos alrededor de las 3:00 AM (2:30 AM - 3:30 AM)
        target_time = datetime.now().replace(hour=3, minute=0, second=0, microsecond=0)
        start_time = target_time - timedelta(minutes=30)
        end_time = target_time + timedelta(minutes=30)
        
        print(f'🎯 Buscando datos entre {start_time} y {end_time}')
        
        # Filtrar datos por tiempo
        mask = (data.index >= start_time) & (data.index <= end_time)
        period_data = data[mask]
        
        if period_data.empty:
            print('⚠️ No hay datos específicos para el período 2:30-3:30 AM')
            print('📊 Analizando datos más recientes disponibles...')
            period_data = data.tail(60)  # Últimos 60 minutos
        
        print(f'📈 Datos del período analizado: {len(period_data)} velas')
        print(f'📅 Período real: {period_data.index[0]} a {period_data.index[-1]}')
        
        # Análisis de breakout
        print('\n🔍 ANÁLISIS DE BREAKOUT:')
        
        # Calcular estadísticas básicas
        price_range = period_data['high'].max() - period_data['low'].min()
        avg_volume = period_data['volume'].mean()
        max_volume = period_data['volume'].max()
        
        print(f'💰 Rango de precios: ${period_data["low"].min():.2f} - ${period_data["high"].max():.2f}')
        print(f'📊 Rango total: ${price_range:.2f}')
        print(f'📈 Volumen promedio: {avg_volume:.0f}')
        print(f'📈 Volumen máximo: {max_volume:.0f}')
        
        # Detectar movimientos significativos
        period_data['price_change'] = period_data['close'].pct_change() * 100
        period_data['volume_ratio'] = period_data['volume'] / period_data['volume'].rolling(20).mean()
        
        # Criterios de breakout (similares a los del sistema)
        significant_moves = period_data[
            (abs(period_data['price_change']) > 0.5) |  # Cambio > 0.5%
            (period_data['volume_ratio'] > 1.5)         # Volumen > 1.5x promedio
        ]
        
        if not significant_moves.empty:
            print(f'\n🚨 MOVIMIENTOS SIGNIFICATIVOS DETECTADOS: {len(significant_moves)}')
            for idx, row in significant_moves.iterrows():
                print(f'⏰ {idx}: Precio ${row["close"]:.2f}, Cambio {row["price_change"]:.2f}%, Volumen {row["volume"]:.0f} (ratio: {row["volume_ratio"]:.2f}x)')
        else:
            print('\n✅ No se detectaron movimientos significativos en el período')
        
        # Buscar el mayor movimiento
        max_change_idx = period_data['price_change'].abs().idxmax()
        max_change = period_data.loc[max_change_idx]
        
        print(f'\n📊 MAYOR MOVIMIENTO:')
        print(f'⏰ Tiempo: {max_change_idx}')
        print(f'💰 Precio: ${max_change["close"]:.2f}')
        print(f'📈 Cambio: {max_change["price_change"]:.2f}%')
        print(f'📊 Volumen: {max_change["volume"]:.0f}')
        
        # Verificar si cumple criterios de breakout del sistema
        breakout_detected = (
            abs(max_change["price_change"]) > 0.5 and  # Cambio > 0.5%
            max_change["volume_ratio"] > 1.5           # Volumen > 1.5x promedio
        )
        
        print(f'\n🎯 EVALUACIÓN FINAL:')
        if breakout_detected:
            print('🚨 SÍ se detectó un breakout que el sistema debería haber capturado')
            print('❌ El sistema falló en detectar este breakout')
        else:
            print('✅ No hay evidencia de un breakout significativo')
            print('ℹ️ Es posible que el movimiento no cumpliera los criterios del sistema')
        
        return breakout_detected
        
    except Exception as e:
        print(f'❌ Error durante el análisis: {e}')
        return False

if __name__ == "__main__":
    analyze_breakout_around_3am()