import pandas as pd
import numpy as np
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDataSystem:
    """
    Sistema robusto para obtener SIEMPRE datos reales de criptomonedas.
    Prioriza APIs que funcionan y elimina dependencias problemáticas.
    """
    
    def __init__(self):
        """Inicializar sistema de datos reales"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SICAR-Trading-Bot/1.0'
        })
        
        # APIs verificadas como funcionales
        self.apis = {
            'binance': {
                'base_url': 'https://api.binance.com/api/v3',
                'priority': 1,  # Máxima prioridad
                'working': True,
                'rate_limit': 0.1  # 10 requests/segundo
            },
            'coingecko': {
                'base_url': 'https://api.coingecko.com/api/v3',
                'priority': 2,
                'working': True,
                'rate_limit': 1.0  # 1 request/segundo
            },
            'coinbase': {
                'base_url': 'https://api.coinbase.com/v2',
                'priority': 3,
                'working': True,
                'rate_limit': 0.8
            }
        }
        
        # Mapeo de símbolos para cada API
        self.symbol_mapping = {
            'BTCUSDT': {
                'binance': 'BTCUSDT',
                'coingecko': 'bitcoin',
                'coinbase': 'BTC-USD'
            },
            'ETHUSDT': {
                'binance': 'ETHUSDT',
                'coingecko': 'ethereum',
                'coinbase': 'ETH-USD'
            },
            'ADAUSDT': {
                'binance': 'ADAUSDT',
                'coingecko': 'cardano',
                'coinbase': 'ADA-USD'
            },
            'BNBUSDT': {
                'binance': 'BNBUSDT',
                'coingecko': 'binancecoin',
                'coinbase': 'BNB-USD'
            },
            'SOLUSDT': {
                'binance': 'SOLUSDT',
                'coingecko': 'solana',
                'coinbase': 'SOL-USD'
            }
        }
        
        # Cache para evitar requests innecesarios
        self.cache = {}
        self.cache_duration = 60  # 1 minuto
        
        # Estadísticas
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'api_usage': {api: 0 for api in self.apis.keys()}
        }
        
        logger.info("🚀 Sistema de Datos Reales inicializado")
        logger.info(f"📊 APIs disponibles: {list(self.apis.keys())}")
    
    def get_historical_data(self, symbol: str = 'BTCUSDT', interval: str = '4h', 
                          limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Obtener datos históricos REALES con sistema de fallback robusto.
        
        Args:
            symbol: Símbolo de la criptomoneda
            interval: Intervalo de tiempo ('1m', '5m', '15m', '30m', '1h', '4h', '1d')
            limit: Número de velas (máximo 1000)
            
        Returns:
            DataFrame con datos OHLCV reales o None si falla
        """
        logger.info(f"📊 Obteniendo datos históricos REALES para {symbol}")
        
        # Verificar cache
        cache_key = f"{symbol}_{interval}_{limit}"
        if self._is_cache_valid(cache_key):
            logger.info("💾 Datos obtenidos del cache")
            return self.cache[cache_key]['data']
        
        # Intentar con cada API en orden de prioridad
        apis_sorted = sorted(self.apis.items(), key=lambda x: x[1]['priority'])
        
        for api_name, api_config in apis_sorted:
            if not api_config['working']:
                continue
                
            logger.info(f"🔄 Intentando obtener datos de {api_name.upper()}...")
            
            try:
                data = None
                
                if api_name == 'binance':
                    data = self._get_binance_historical(symbol, interval, limit)
                elif api_name == 'coingecko':
                    data = self._get_coingecko_historical(symbol, limit)
                elif api_name == 'coinbase':
                    data = self._get_coinbase_historical(symbol, limit)
                
                if data is not None and len(data) >= 10:
                    logger.info(f"✅ Datos REALES obtenidos de {api_name.upper()}: {len(data)} velas")
                    
                    # Validar calidad de datos
                    if self._validate_data_quality(data):
                        self._cache_data(cache_key, data)
                        self.stats['successful_requests'] += 1
                        self.stats['api_usage'][api_name] += 1
                        return data
                    else:
                        logger.warning(f"⚠️ Datos de {api_name} no pasaron validación de calidad")
                        
            except Exception as e:
                logger.error(f"❌ Error con {api_name}: {e}")
                continue
        
        logger.error("🚨 CRÍTICO: No se pudieron obtener datos REALES de ninguna API")
        return None
    
    def _get_binance_historical(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Obtener datos históricos de Binance"""
        try:
            self._respect_rate_limit('binance')
            
            if symbol not in self.symbol_mapping:
                return None
            
            binance_symbol = self.symbol_mapping[symbol]['binance']
            
            url = f"{self.apis['binance']['base_url']}/klines"
            params = {
                'symbol': binance_symbol,
                'interval': interval,
                'limit': min(limit, 1000)
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Procesar datos
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Seleccionar columnas principales
            df = df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.set_index('timestamp', inplace=True)
            
            self.stats['total_requests'] += 1
            return df
            
        except Exception as e:
            logger.error(f"Error Binance: {e}")
            return None
    
    def _get_coingecko_historical(self, symbol: str, days: int) -> Optional[pd.DataFrame]:
        """Obtener datos históricos de CoinGecko"""
        try:
            self._respect_rate_limit('coingecko')
            
            if symbol not in self.symbol_mapping:
                return None
            
            coin_id = self.symbol_mapping[symbol]['coingecko']
            
            # Convertir limit a días aproximados
            days = min(days // 6, 365)  # Aproximadamente 6 velas de 4h por día
            
            url = f"{self.apis['coingecko']['base_url']}/coins/{coin_id}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days,
                'interval': 'hourly' if days <= 90 else 'daily'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            prices = data.get('prices', [])
            volumes = data.get('total_volumes', [])
            
            if not prices or len(prices) < 10:
                return None
            
            # Crear DataFrame
            df_data = []
            for i, (timestamp, price) in enumerate(prices):
                volume = volumes[i][1] if i < len(volumes) else 0
                df_data.append({
                    'timestamp': pd.to_datetime(timestamp, unit='ms'),
                    'Close': price,
                    'Volume': volume,
                    'Open': price,  # CoinGecko no proporciona OHLC, usar Close
                    'High': price,
                    'Low': price
                })
            
            df = pd.DataFrame(df_data)
            df.set_index('timestamp', inplace=True)
            
            self.stats['total_requests'] += 1
            return df
            
        except Exception as e:
            logger.error(f"Error CoinGecko: {e}")
            return None
    
    def _get_coinbase_historical(self, symbol: str, limit: int) -> Optional[pd.DataFrame]:
        """Obtener datos históricos de Coinbase"""
        try:
            self._respect_rate_limit('coinbase')
            
            if symbol not in self.symbol_mapping:
                return None
            
            coinbase_symbol = self.symbol_mapping[symbol]['coinbase']
            
            # Coinbase Pro API para datos históricos
            url = f"https://api.exchange.coinbase.com/products/{coinbase_symbol}/candles"
            
            # Calcular período
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=limit * 4)  # Asumiendo 4h por vela
            
            params = {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'granularity': 14400  # 4 horas en segundos
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'Low', 'High', 'Open', 'Close', 'Volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Reordenar columnas
            df = df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            
            self.stats['total_requests'] += 1
            return df
            
        except Exception as e:
            logger.error(f"Error Coinbase: {e}")
            return None
    
    def _validate_data_quality(self, df: pd.DataFrame) -> bool:
        """Validar calidad de los datos"""
        try:
            if df is None or df.empty:
                return False
            
            # Verificar columnas requeridas
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_cols):
                return False
            
            # Verificar que no hay valores nulos en columnas críticas
            if df[['Close', 'Volume']].isnull().any().any():
                return False
            
            # Verificar que los precios son positivos
            if (df['Close'] <= 0).any():
                return False
            
            # Verificar consistencia OHLC
            if ((df['High'] < df['Low']) | 
                (df['High'] < df['Open']) | 
                (df['High'] < df['Close']) |
                (df['Low'] > df['Open']) | 
                (df['Low'] > df['Close'])).any():
                return False
            
            return True
            
        except Exception:
            return False
    
    def _respect_rate_limit(self, api_name: str):
        """Respetar límites de velocidad de API"""
        if not hasattr(self, '_last_request'):
            self._last_request = {}
        
        if api_name not in self._last_request:
            self._last_request[api_name] = 0
        
        elapsed = time.time() - self._last_request[api_name]
        min_interval = self.apis[api_name]['rate_limit']
        
        if elapsed < min_interval:
            sleep_time = min_interval - elapsed
            time.sleep(sleep_time)
        
        self._last_request[api_name] = time.time()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verificar si el cache es válido"""
        if cache_key not in self.cache:
            return False
        
        cache_time = self.cache[cache_key]['timestamp']
        return (time.time() - cache_time) < self.cache_duration
    
    def _cache_data(self, cache_key: str, data: pd.DataFrame):
        """Guardar datos en cache"""
        self.cache[cache_key] = {
            'data': data.copy(),
            'timestamp': time.time()
        }
    
    def get_current_price(self, symbol: str = 'BTCUSDT') -> Optional[Dict]:
        """Obtener precio actual en tiempo real"""
        logger.info(f"💰 Obteniendo precio actual de {symbol}")
        
        # Intentar con Binance primero (más rápido)
        try:
            self._respect_rate_limit('binance')
            
            if symbol in self.symbol_mapping:
                binance_symbol = self.symbol_mapping[symbol]['binance']
                
                url = f"{self.apis['binance']['base_url']}/ticker/24hr"
                params = {'symbol': binance_symbol}
                
                response = self.session.get(url, params=params, timeout=5)
                response.raise_for_status()
                
                data = response.json()
                
                result = {
                    'symbol': symbol,
                    'price': float(data['lastPrice']),
                    'change_24h': float(data['priceChangePercent']),
                    'volume_24h': float(data['volume']),
                    'timestamp': datetime.now(),
                    'source': 'binance'
                }
                
                logger.info(f"✅ Precio actual de {symbol}: ${result['price']:,.2f}")
                return result
                
        except Exception as e:
            logger.error(f"Error obteniendo precio de Binance: {e}")
        
        return None
    
    def get_performance_stats(self) -> Dict:
        """Obtener estadísticas de rendimiento"""
        total = self.stats['total_requests']
        success = self.stats['successful_requests']
        
        return {
            'total_requests': total,
            'successful_requests': success,
            'success_rate': (success / total * 100) if total > 0 else 0,
            'api_usage': self.stats['api_usage'].copy(),
            'working_apis': [name for name, config in self.apis.items() if config['working']],
            'cache_size': len(self.cache)
        }
    
    def test_connectivity(self) -> Dict:
        """Probar conectividad con todas las APIs"""
        logger.info("🔍 Probando conectividad con APIs...")
        
        results = {}
        
        for api_name in self.apis.keys():
            try:
                if api_name == 'binance':
                    url = f"{self.apis['binance']['base_url']}/ping"
                    response = self.session.get(url, timeout=5)
                    results[api_name] = response.status_code == 200
                    
                elif api_name == 'coingecko':
                    url = f"{self.apis['coingecko']['base_url']}/ping"
                    response = self.session.get(url, timeout=5)
                    results[api_name] = response.status_code == 200
                    
                elif api_name == 'coinbase':
                    url = f"{self.apis['coinbase']['base_url']}/time"
                    response = self.session.get(url, timeout=5)
                    results[api_name] = response.status_code == 200
                    
            except Exception as e:
                logger.error(f"Error probando {api_name}: {e}")
                results[api_name] = False
        
        working_count = sum(results.values())
        logger.info(f"📊 APIs funcionando: {working_count}/{len(results)}")
        
        return results


# Función de conveniencia para uso directo
def get_real_crypto_data(symbol: str = 'BTCUSDT', interval: str = '4h', 
                        limit: int = 500) -> Optional[pd.DataFrame]:
    """
    Función de conveniencia para obtener datos reales de criptomonedas.
    
    Args:
        symbol: Símbolo de la criptomoneda
        interval: Intervalo de tiempo
        limit: Número de velas
        
    Returns:
        DataFrame con datos OHLCV reales
    """
    system = RealDataSystem()
    return system.get_historical_data(symbol, interval, limit)


if __name__ == "__main__":
    # Prueba del sistema
    logger.info("🚀 Iniciando prueba del Sistema de Datos Reales")
    
    system = RealDataSystem()
    
    # Probar conectividad
    connectivity = system.test_connectivity()
    logger.info(f"Conectividad: {connectivity}")
    
    # Probar obtención de datos
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    
    for symbol in symbols:
        logger.info(f"\n📊 Probando {symbol}...")
        
        # Datos históricos
        data = system.get_historical_data(symbol, '4h', 100)
        if data is not None:
            logger.info(f"✅ {symbol}: {len(data)} velas obtenidas")
            logger.info(f"   Último precio: ${data['Close'].iloc[-1]:,.2f}")
        else:
            logger.error(f"❌ {symbol}: No se pudieron obtener datos")
        
        # Precio actual
        current = system.get_current_price(symbol)
        if current:
            logger.info(f"💰 Precio actual: ${current['price']:,.2f}")
    
    # Estadísticas finales
    stats = system.get_performance_stats()
    logger.info(f"\n📈 Estadísticas finales: {stats}")