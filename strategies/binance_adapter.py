#!/usr/bin/env python3
"""
ADAPTADOR PARA BINANCE CLIENT
Conecta el sistema autónomo con el cliente Binance existente
"""

import asyncio
import aiohttp
import pandas as pd
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta
import hashlib
import hmac
import urllib.parse
import sys
import os

# Agregar el directorio padre al path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import get_settings
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Configuración de fallback para pruebas
    class FallbackSettings:
        BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', 'dummy_key')
        BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', 'dummy_secret')

class BinanceAdapter:
    """
    Adaptador para conectar con Binance API usando la configuración existente
    """
    
    def __init__(self):
        if CONFIG_AVAILABLE:
            self.settings = get_settings()
            self.api_key = self.settings.BINANCE_API_KEY
            self.secret_key = self.settings.BINANCE_SECRET_KEY
        else:
            fallback = FallbackSettings()
            self.api_key = fallback.BINANCE_API_KEY
            self.secret_key = fallback.BINANCE_SECRET_KEY
            
        self.base_url = "https://api.binance.com"
        self.session = None
        self.logger = logging.getLogger(__name__)
    
    async def _get_session(self):
        """Obtener sesión HTTP"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    def _generate_signature(self, query_string: str) -> str:
        """Generar signature para autenticación"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def get_recent_klines(self, symbol: str, interval: str, limit: int = 500) -> List[Dict]:
        """
        Obtener datos de velas recientes
        """
        try:
            session = await self._get_session()
            
            # Mapear intervalos
            interval_map = {
                '1m': '1m', '3m': '3m', '5m': '5m',
                '15m': '15m', '30m': '30m', '1h': '1h',
                '2h': '2h', '4h': '4h', '6h': '6h',
                '8h': '8h', '12h': '12h', '1d': '1d'
            }
            
            binance_interval = interval_map.get(interval, '1h')
            
            # Parámetros de la request
            params = {
                'symbol': symbol.upper(),
                'interval': binance_interval,
                'limit': min(limit, 1000)  # Binance limit
            }
            
            url = f"{self.base_url}/api/v3/klines"
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Convertir a formato DataFrame compatible
                    klines = []
                    for item in data:
                        klines.append({
                            'timestamp': item[0],
                            'open': float(item[1]),
                            'high': float(item[2]),
                            'low': float(item[3]),
                            'close': float(item[4]),
                            'volume': float(item[5]),
                            'close_time': item[6],
                            'quote_volume': float(item[7]),
                            'trades_count': item[8],
                            'taker_buy_base': float(item[9]),
                            'taker_buy_quote': float(item[10])
                        })
                    
                    return klines
                else:
                    self.logger.error(f"Error obteniendo klines: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error en get_recent_klines: {e}")
            return []
    
    async def get_24h_ticker(self) -> List[Dict]:
        """
        Obtener ticker de 24h para todos los pares
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/v3/ticker/24hr"
            
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"Error obteniendo ticker 24h: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Error en get_24h_ticker: {e}")
            return []
    
    async def get_high_volume_pairs(self, limit: int = 20) -> List[str]:
        """
        Obtener pares con mayor volumen en 24h
        """
        try:
            ticker_data = await self.get_24h_ticker()
            
            # Filtrar solo pares USDT
            usdt_pairs = [
                item for item in ticker_data 
                if item['symbol'].endswith('USDT') and 
                float(item['quoteVolume']) > 10000000  # Mínimo 10M USDT volumen
            ]
            
            # Ordenar por volumen
            usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
            
            # Retornar solo los símbolos
            return [pair['symbol'] for pair in usdt_pairs[:limit]]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo pares de alto volumen: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT']  # Fallback
    
    async def get_high_volatility_pairs(self, limit: int = 10) -> List[str]:
        """
        Obtener pares con alta volatilidad (cambio de precio en 24h)
        """
        try:
            ticker_data = await self.get_24h_ticker()
            
            # Filtrar pares USDT con volumen decente
            usdt_pairs = [
                item for item in ticker_data 
                if item['symbol'].endswith('USDT') and 
                float(item['quoteVolume']) > 5000000 and  # Mínimo 5M USDT
                abs(float(item['priceChangePercent'])) > 2.0  # Mínimo 2% cambio
            ]
            
            # Ordenar por volatilidad (cambio porcentual absoluto)
            usdt_pairs.sort(
                key=lambda x: abs(float(x['priceChangePercent'])), 
                reverse=True
            )
            
            return [pair['symbol'] for pair in usdt_pairs[:limit]]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo pares volátiles: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT']  # Fallback
    
    async def get_pair_info(self, symbol: str) -> Optional[Dict]:
        """
        Obtener información específica de un par
        """
        try:
            ticker_data = await self.get_24h_ticker()
            
            for pair in ticker_data:
                if pair['symbol'] == symbol.upper():
                    return pair
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error obteniendo info del par {symbol}: {e}")
            return None
    
    async def get_current_price(self, symbol: str) -> float:
        """
        Obtener precio actual de un par
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/v3/ticker/price"
            params = {'symbol': symbol.upper()}
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data['price'])
                else:
                    return 0.0
                    
        except Exception as e:
            self.logger.error(f"Error obteniendo precio de {symbol}: {e}")
            return 0.0
    
    async def close(self):
        """Cerrar sesión HTTP"""
        if self.session:
            await self.session.close()

# Instancia global del adaptador
binance_adapter = BinanceAdapter()

async def cleanup_binance_adapter():
    """Función para limpiar el adaptador"""
    await binance_adapter.close()

# Funciones de conveniencia para el módulo autónomo
async def get_klines_data(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    """
    Obtener datos de klines como DataFrame para uso en estrategias
    """
    try:
        klines = await binance_adapter.get_recent_klines(symbol, interval, limit)
        
        if not klines:
            return pd.DataFrame()
        
        # Convertir a DataFrame
        df = pd.DataFrame(klines)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
        
    except Exception as e:
        logging.error(f"Error convirtiendo klines a DataFrame: {e}")
        return pd.DataFrame()

async def test_binance_connection():
    """
    Probar la conexión con Binance
    """
    try:
        # Probar obtener precio de BTC
        btc_price = await binance_adapter.get_current_price('BTCUSDT')
        
        if btc_price > 0:
            print(f"✅ Conexión Binance OK - BTC Price: ${btc_price:,.2f}")
            
            # Probar obtener klines
            klines = await binance_adapter.get_recent_klines('BTCUSDT', '1h', 10)
            print(f"✅ Klines obtenidas: {len(klines)} registros")
            
            # Probar pares de alto volumen
            high_vol_pairs = await binance_adapter.get_high_volume_pairs(5)
            print(f"✅ Pares alto volumen: {high_vol_pairs}")
            
            return True
        else:
            print("❌ Error: No se pudo obtener precio de BTC")
            return False
            
    except Exception as e:
        print(f"❌ Error probando conexión Binance: {e}")
        return False
    finally:
        await binance_adapter.close()

if __name__ == "__main__":
    # Test del adaptador
    asyncio.run(test_binance_connection())
