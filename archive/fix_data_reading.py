#!/usr/bin/env python3
"""
Script para arreglar la lectura de datos históricos en el sistema dinámico
Crea una función que lea directamente desde los archivos CSV generados
"""

import pandas as pd
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def read_historical_data_from_csv(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    """
    Lee datos históricos directamente desde archivos CSV
    Args:
        symbol: Par de trading (ej: 'BTCUSDT')
        interval: Intervalo de tiempo (ej: '1h')
        limit: Número máximo de registros a obtener
    Returns:
        DataFrame con los datos históricos
    """
    try:
        # Buscar el archivo CSV correspondiente
        csv_path = f"data/analisis/historical_klines_{symbol}_{interval}_1_Jan_2022_now.csv"
        
        if not os.path.exists(csv_path):
            logger.warning(f"No se encontró archivo CSV para {symbol}-{interval}: {csv_path}")
            return pd.DataFrame()
        
        # Leer el archivo CSV
        df = pd.read_csv(csv_path)
        
        # Asegurar que las columnas estén correctas
        expected_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        if not all(col in df.columns for col in expected_columns):
            logger.error(f"Columnas faltantes en {csv_path}. Esperadas: {expected_columns}, Encontradas: {list(df.columns)}")
            return pd.DataFrame()
        
        # Convertir timestamp a datetime
        if 'timestamp' in df.columns:
            # Los timestamps ya están en formato datetime string, usar formato mixto para robustez
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
            # Eliminar filas con timestamps inválidos
            df = df.dropna(subset=['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        # Asegurar tipos de datos numéricos
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Ordenar por timestamp y tomar los últimos registros
        df = df.sort_index()
        if limit and len(df) > limit:
            df = df.tail(limit)
        
        logger.info(f"✅ Datos históricos cargados para {symbol}-{interval}: {len(df)} registros desde {csv_path}")
        return df
        
    except Exception as e:
        logger.error(f"Error leyendo datos desde CSV para {symbol}-{interval}: {e}")
        return pd.DataFrame()

# Test de la función
if __name__ == "__main__":
    import asyncio
    
    async def test_reading():
        print("🔍 PROBANDO LECTURA DE DATOS DESDE CSV")
        print("=" * 50)
        
        # Lista de pares dinámicos
        dynamic_pairs = ['USDCUSDT', 'FDUSDUSDT', 'BTCUSDT', 'TRXUSDT', 'BNBUSDT', 'ADAUSDT', 'ETHUSDT', 'SOLUSDT']
        
        success_count = 0
        for pair in dynamic_pairs:
            print(f"📊 Probando {pair}...")
            df = read_historical_data_from_csv(pair, '1h', 200)
            if not df.empty:
                success_count += 1
                print(f"  ✅ {len(df)} registros encontrados")
                print(f"  📅 Desde: {df.index.min()} hasta: {df.index.max()}")
            else:
                print(f"  ❌ No se pudieron cargar datos")
            print()
        
        print("=" * 50)
        print(f"📋 RESULTADO: {success_count}/{len(dynamic_pairs)} pares con datos exitosos")
        
        if success_count == len(dynamic_pairs):
            print("🎉 ¡TODOS LOS PARES TIENEN DATOS DISPONIBLES!")
            print("🚀 El sistema dinámico está listo para funcionar")
        else:
            print(f"⚠️  {len(dynamic_pairs) - success_count} pares necesitan atención")
    
    asyncio.run(test_reading())
