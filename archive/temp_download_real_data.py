#!/usr/bin/env python3
import asyncio
from utils.binance_client import get_binance_client
import pandas as pd
import os

async def get_real_data():
    print('📥 DESCARGANDO DATOS REALES DE BINANCE')
    print('=' * 40)
    
    try:
        client = await get_binance_client()
        print('✅ Cliente Binance conectado')
        
        # Obtener últimas 500 velas de 1h
        print('📊 Obteniendo datos históricos...')
        klines = await client.get_historical_klines('BTCUSDT', '1h', '500 hours ago UTC')
        
        if klines:
            # Convertir a DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col])
            
            # Guardar archivo
            os.makedirs('data/analisis', exist_ok=True)
            output_file = 'data/analisis/btc_real_data.csv'
            df_clean = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            df_clean.to_csv(output_file, index=False)
            
            print(f'✅ Datos guardados: {len(df)} registros')
            print(f'📁 Archivo: {output_file}')
            print(f'📅 Período: {df["timestamp"].min()} a {df["timestamp"].max()}')
            print(f'💰 Precio inicial: ${df["close"].iloc[0]:,.2f}')
            print(f'💰 Precio actual: ${df["close"].iloc[-1]:,.2f}')
            
            change_pct = ((df['close'].iloc[-1] / df['close'].iloc[0]) - 1) * 100
            print(f'📈 Cambio total: {change_pct:+.2f}%')
            
            return df_clean
        else:
            print('❌ No se obtuvieron datos')
            return None
            
    except Exception as e:
        print(f'❌ Error: {e}')
        return None

if __name__ == "__main__":
    data = asyncio.run(get_real_data())
