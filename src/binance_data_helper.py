#!/usr/bin/env python3
"""
Helper para obtener datos de Binance de manera robusta
"""

import pandas as pd
import logging
from binance.client import Client

logger = logging.getLogger(__name__)

def get_binance_data_robust(symbol='BTCUSDT', interval='4h', limit=100):
    """
    Obtiene datos reales de Binance de manera robusta.
    
    Args:
        symbol: Par de trading (ej: 'BTCUSDT')
        interval: Intervalo de tiempo ('1h', '4h', '1d')
        limit: Número máximo de velas (máx 1000)
        
    Returns:
        DataFrame con datos OHLCV o None si falla
    """
    try:
        logger.info(f"📊 Obteniendo datos de Binance para {symbol} - Intervalo: {interval} - Límite: {limit}")
        
        # Crear cliente de Binance (sin API keys para datos públicos)
        client = Client()
        
        # Obtener datos históricos
        klines = client.get_historical_klines(symbol, interval, f"{limit} {interval} ago UTC")
        
        if not klines:
            logger.error(f"No se obtuvieron datos de Binance para {symbol}")
            return None
        
        logger.info(f"Datos brutos obtenidos: {len(klines)} velas")
        
        # Convertir a DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convertir tipos de datos
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Convertir timestamp a datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Mantener solo columnas OHLCV
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        # Verificar que tenemos datos válidos
        if df.empty:
            logger.error("DataFrame vacío después de procesamiento inicial")
            return None
        
        logger.info(f"Datos procesados: {len(df)} registros")
        
        # Agregar columnas requeridas por SICAR (formato estándar)
        df['Open'] = df['open']
        df['High'] = df['high']
        df['Low'] = df['low']
        df['Close'] = df['close']
        df['Volume'] = df['volume']
        df['Adj Close'] = df['close']
        
        # Agregar columnas adicionales para análisis
        df['price'] = df['close']
        df['returns'] = df['close'].pct_change()
        
        # Calcular volatilidad con ventana más pequeña para evitar perder muchos datos
        window_size = min(10, len(df) // 2)  # Usar ventana adaptativa
        if window_size > 0:
            df['volatility'] = df['returns'].rolling(window=window_size, min_periods=1).std()
        else:
            df['volatility'] = 0.0
        
        # Rellenar NaNs en lugar de eliminar todas las filas
        df['returns'] = df['returns'].fillna(0.0)
        df['volatility'] = df['volatility'].fillna(df['volatility'].mean())
        
        # Solo eliminar filas donde TODOS los valores son NaN
        df = df.dropna(how='all')
        
        if df.empty:
            logger.error("DataFrame vacío después de limpiar datos")
            return None
        
        logger.info(f"✅ Datos de Binance procesados exitosamente")
        logger.info(f"📈 Dataset final: {len(df)} puntos de datos")
        
        if len(df) > 0:
            logger.info(f"📅 Período: {df.index[0]} a {df.index[-1]}")
            logger.info(f"💰 Precio inicial: ${df['close'].iloc[0]:.2f}")
            logger.info(f"💰 Precio final: ${df['close'].iloc[-1]:.2f}")
            logger.info(f"📊 Rango de precios: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error obteniendo datos de Binance: {str(e)}")
        return None

def test_binance_connection():
    """Prueba la conexión a Binance con diferentes configuraciones."""
    logger.info("=== PROBANDO CONEXIÓN A BINANCE ===")
    
    test_configs = [
        ('BTCUSDT', '1h', 24),
        ('BTCUSDT', '4h', 12),
        ('ETHUSDT', '1h', 24),
        ('BTCUSDT', '1d', 7)
    ]
    
    for symbol, interval, limit in test_configs:
        logger.info(f"Probando: {symbol} - {interval} - {limit} velas")
        data = get_binance_data_robust(symbol, interval, limit)
        
        if data is not None and not data.empty:
            logger.info(f"✅ Éxito: {len(data)} registros obtenidos")
            return data
        else:
            logger.warning(f"❌ Falló: {symbol} {interval}")
    
    logger.error("❌ Todas las pruebas de conexión fallaron")
    return None

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Probar conexión
    data = test_binance_connection()
    if data is not None:
        print(f"✅ Conexión exitosa. Datos obtenidos: {len(data)} registros")
        print(data.head())
    else:
        print("❌ No se pudo establecer conexión con Binance")