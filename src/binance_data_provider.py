"""
Proveedor de datos de Binance para el sistema SICAR
Obtiene datos de forex en tiempo real desde la API de Binance
"""

import os
import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import time
from dotenv import load_dotenv
from enhanced_config import CONFIG

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BinanceDataProvider:
    """
    Proveedor de datos de Binance para obtener datos de forex en tiempo real
    """
    
    def __init__(self):
        """Inicializar el cliente de Binance"""
        try:
            # Cargar credenciales desde variables de entorno
            api_key = os.getenv('BINANCE_API_KEY')
            secret_key = os.getenv('BINANCE_SECRET_KEY')
            
            if not api_key or not secret_key:
                self.client = None
                logger.warning("Credenciales de Binance no configuradas, proveedor en modo simulación")
            else:
                modes = CONFIG.safe_runtime_modes()
                use_testnet = modes['trading_mode'] == 'testnet'
                self.client = Client(api_key, secret_key, testnet=use_testnet)
                logger.info("Cliente de Binance inicializado correctamente" + (" (Testnet)" if use_testnet else ""))
            
            # Inicializar cliente de Binance
            self.client = Client(api_key, secret_key, testnet=False)
            
            # Mapeo de símbolos forex a Binance
            self.forex_symbols = {
                'EURUSD': 'EURUSDT',
                'GBPUSD': 'GBPUSDT', 
                'USDJPY': 'USDCJPY',  # Nota: Binance no tiene USDJPY directo
                'AUDUSD': 'AUDUSDT',
                'USDCAD': 'USDCUSDT', # Nota: Binance no tiene USDCAD directo
                'USDCHF': 'USDCUSDT', # Aproximación
                'NZDUSD': 'NZDUSDT',
                'EURGBP': 'EURGBP',   # Si está disponible
                'EURJPY': 'EURJPY',   # Si está disponible
                'GBPJPY': 'GBPJPY'    # Si está disponible
            }
            
            # Símbolos principales disponibles en Binance
            self.available_symbols = [
                'EURUSDT', 'GBPUSDT', 'AUDUSDT', 'NZDUSDT',
                'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT'
            ]
            
        except Exception as e:
            logger.error(f"Error al inicializar cliente de Binance: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Probar la conexión con Binance
        """
        try:
            if not self.client:
                logger.info("Proveedor en modo simulación, sin conexión a Binance")
                return False
            # Probar conexión obteniendo información del servidor
            server_time = self.client.get_server_time()
            logger.info(f"Conexión exitosa con Binance. Hora del servidor: {server_time}")
            return True
        except Exception as e:
            logger.error(f"Error de conexión con Binance: {e}")
            return False
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Obtener información de un símbolo
        """
        try:
            if not self.client:
                return None
            info = self.client.get_symbol_info(symbol)
            return info
        except Exception as e:
            logger.warning(f"No se pudo obtener información para {symbol}: {e}")
            return None
    
    def get_available_symbols(self) -> List[str]:
        """
        Obtener lista de símbolos disponibles para forex/crypto
        """
        try:
            if not self.client:
                return self.available_symbols
            exchange_info = self.client.get_exchange_info()
            symbols = []
            
            for symbol_info in exchange_info['symbols']:
                symbol = symbol_info['symbol']
                # Filtrar símbolos relevantes para forex y crypto principales
                if (symbol.endswith('USDT') and 
                    symbol in ['EURUSDT', 'GBPUSDT', 'AUDUSDT', 'NZDUSDT', 
                              'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT']):
                    symbols.append(symbol)
            
            logger.info(f"Símbolos disponibles: {symbols}")
            return symbols
            
        except Exception as e:
            logger.error(f"Error al obtener símbolos disponibles: {e}")
            return self.available_symbols
    
    def get_historical_data(self, symbol: str, interval: str = '1m', 
                          limit: int = 100) -> Optional[pd.DataFrame]:
        """
        Obtener datos históricos de un símbolo
        
        Args:
            symbol: Símbolo a consultar (ej: 'EURUSDT')
            interval: Intervalo de tiempo ('1m', '5m', '1h', '1d')
            limit: Número de velas a obtener (máximo 1000)
        
        Returns:
            DataFrame con datos OHLCV o None si hay error
        """
        try:
            if not self.client:
                return None
            # Calcular el tiempo basado en el intervalo
            interval_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '2h': 120, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
                '1d': 1440, '3d': 4320, '1w': 10080, '1M': 43200
            }
            
            minutes_needed = limit * interval_minutes.get(interval, 1)
            
            # Obtener datos históricos
            klines = self.client.get_historical_klines(
                symbol, interval, f"{minutes_needed} minutes ago UTC"
            )
            
            if not klines:
                logger.warning(f"No se obtuvieron datos para {symbol}")
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume',
                'ignore'
            ])
            
            # Convertir tipos de datos
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Seleccionar columnas relevantes
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df.set_index('timestamp', inplace=True)
            
            logger.info(f"Datos obtenidos para {symbol}: {len(df)} velas")
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Error de API de Binance para {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error al obtener datos históricos para {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Obtener precio actual de un símbolo
        """
        try:
            if not self.client:
                return None
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            logger.debug(f"Precio actual de {symbol}: {price}")
            return price
        except Exception as e:
            logger.error(f"Error al obtener precio actual de {symbol}: {e}")
            return None

    def get_futures_premium_index(self, symbol: str) -> Optional[Dict]:
        """
        Obtener markPrice, indexPrice y funding (premium index) de Binance Futures (público)
        Endpoint: https://fapi.binance.com/fapi/v1/premiumIndex
        """
        try:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex"
            resp = requests.get(url, params={"symbol": symbol}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "symbol": data.get("symbol", symbol),
                "markPrice": float(data.get("markPrice", 0.0)),
                "indexPrice": float(data.get("indexPrice", 0.0)),
                "lastFundingRate": float(data.get("lastFundingRate", 0.0)),
                "nextFundingTime": data.get("nextFundingTime")
            }
        except Exception as e:
            logger.error(f"Error obteniendo premiumIndex para {symbol}: {e}")
            return None

    def get_futures_open_interest(self, symbol: str) -> Optional[float]:
        """
        Obtener open interest actual de Binance Futures (público)
        Endpoint: https://fapi.binance.com/fapi/v1/openInterest
        """
        try:
            url = "https://fapi.binance.com/fapi/v1/openInterest"
            resp = requests.get(url, params={"symbol": symbol}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("openInterest", 0.0))
        except Exception as e:
            logger.error(f"Error obteniendo openInterest para {symbol}: {e}")
            return None
    
    def get_24h_stats(self, symbol: str) -> Optional[Dict]:
        """
        Obtener estadísticas de 24 horas para un símbolo
        """
        try:
            if not self.client:
                return None
            stats = self.client.get_24hr_ticker(symbol=symbol)
            return {
                'symbol': stats['symbol'],
                'price_change': float(stats['priceChange']),
                'price_change_percent': float(stats['priceChangePercent']),
                'high_price': float(stats['highPrice']),
                'low_price': float(stats['lowPrice']),
                'volume': float(stats['volume']),
                'count': int(stats['count'])
            }
        except Exception as e:
            logger.error(f"Error al obtener estadísticas 24h de {symbol}: {e}")
            return None
    
    def get_multiple_symbols_data(self, symbols: List[str], 
                                interval: str = '1m', 
                                limit: int = 100) -> Dict[str, pd.DataFrame]:
        """
        Obtener datos históricos para múltiples símbolos
        """
        results = {}
        
        for symbol in symbols:
            logger.info(f"Obteniendo datos para {symbol}...")
            data = self.get_historical_data(symbol, interval, limit)
            if data is not None:
                results[symbol] = data
            
            # Pequeña pausa para evitar límites de rate
            time.sleep(0.1)
        
        logger.info(f"Datos obtenidos para {len(results)} de {len(symbols)} símbolos")
        return results
    
    def calculate_breakout_signals(self, df: pd.DataFrame, 
                                 lookback_period: int = 20) -> Dict:
        """
        Calcular señales de ruptura basadas en datos de Binance
        """
        try:
            if len(df) < lookback_period:
                return {'signal': 'insufficient_data', 'strength': 0}
            
            # Calcular niveles de soporte y resistencia
            recent_data = df.tail(lookback_period)
            resistance = recent_data['high'].max()
            support = recent_data['low'].min()
            
            # Precio actual
            current_price = df['close'].iloc[-1]
            
            # Detectar ruptura
            if current_price > resistance * 1.001:  # 0.1% por encima de resistencia
                signal = 'bullish_breakout'
                strength = min((current_price - resistance) / resistance * 100, 10)
            elif current_price < support * 0.999:  # 0.1% por debajo de soporte
                signal = 'bearish_breakout'
                strength = min((support - current_price) / support * 100, 10)
            else:
                signal = 'no_breakout'
                strength = 0
            
            return {
                'signal': signal,
                'strength': strength,
                'current_price': current_price,
                'resistance': resistance,
                'support': support,
                'volume': df['volume'].iloc[-1]
            }
            
        except Exception as e:
            logger.error(f"Error al calcular señales de ruptura: {e}")
            return {'signal': 'error', 'strength': 0}

def test_binance_provider():
    """
    Función de prueba para el proveedor de datos de Binance
    """
    print("🔄 Probando proveedor de datos de Binance...")
    
    try:
        # Inicializar proveedor
        provider = BinanceDataProvider()
        
        # Probar conexión
        if not provider.test_connection():
            print("❌ Error de conexión con Binance")
            return False
        
        # Obtener símbolos disponibles
        symbols = provider.get_available_symbols()
        print(f"✅ Símbolos disponibles: {symbols}")
        
        # Probar con un símbolo
        test_symbol = 'EURUSDT'
        print(f"\n🔍 Probando con {test_symbol}...")
        
        # Obtener datos históricos
        data = provider.get_historical_data(test_symbol, '1m', 50)
        if data is not None:
            print(f"✅ Datos históricos obtenidos: {len(data)} velas")
            print(f"   Último precio: {data['close'].iloc[-1]}")
            
            # Calcular señales
            signals = provider.calculate_breakout_signals(data)
            print(f"✅ Señales calculadas: {signals}")
        else:
            print(f"❌ No se pudieron obtener datos para {test_symbol}")
        
        # Obtener precio actual
        current_price = provider.get_current_price(test_symbol)
        if current_price:
            print(f"✅ Precio actual: {current_price}")
        
        print("\n🎉 Prueba de Binance completada exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba de Binance: {e}")
        return False

if __name__ == "__main__":
    test_binance_provider()
