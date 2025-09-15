import asyncio
import pandas as pd
from utils.binance_client import BinanceClient
from utils.technical_analysis import get_historical_klines

async def get_nas100_data():
    """Obtener datos históricos del NAS100 desde Binance"""
    client = BinanceClient()
    
    try:
        # Intentar obtener datos del NAS100
        print("Obteniendo datos históricos del NAS100...")
        data = await get_historical_klines('NAS100USDT', '1h', 1000)
        
        if not data.empty:
            print(f"Datos obtenidos: {len(data)} registros")
            print("\nPrimeros 5 registros:")
            print(data.head())
            print("\nÚltimos 5 registros:")
            print(data.tail())
            
            # Guardar datos para análisis posterior
            data.to_csv('nas100_data.csv')
            print("\nDatos guardados en nas100_data.csv")
            
            # Mostrar estadísticas básicas
            print("\nEstadísticas básicas:")
            print(f"Precio mínimo: ${data['low'].min():.2f}")
            print(f"Precio máximo: ${data['high'].max():.2f}")
            print(f"Precio actual: ${data['close'].iloc[-1]:.2f}")
            print(f"Volatilidad (std): {data['close'].pct_change().std():.4f}")
            
        else:
            print("No se pudieron obtener datos del NAS100")
            # Intentar con símbolo alternativo
            print("Intentando con símbolo alternativo...")
            data = await get_historical_klines('BTCUSDT', '1h', 100)
            if not data.empty:
                print(f"Datos de prueba obtenidos: {len(data)} registros de BTCUSDT")
            
    except Exception as e:
        print(f"Error al obtener datos: {e}")
        
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(get_nas100_data())