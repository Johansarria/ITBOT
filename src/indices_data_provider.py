"""
SICAR Indices Data Provider
Sistema de obtención de datos para índices bursátiles
Soporta múltiples fuentes: Yahoo Finance, Alpha Vantage, IEX Cloud
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import os
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketData:
    """Estructura de datos de mercado estandarizada"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    timeframe: str

class IndicesDataProvider:
    """
    Proveedor de datos para índices bursátiles
    Soporta múltiples fuentes con fallback automático
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.alpha_vantage_key = self.config.get('alpha_vantage_key', os.getenv('ALPHA_VANTAGE_KEY'))
        self.iex_cloud_key = self.config.get('iex_cloud_key', os.getenv('IEX_CLOUD_KEY'))
        
        # Índices principales soportados
        self.supported_indices = {
            'SPY': 'SPDR S&P 500 ETF',
            'QQQ': 'Invesco QQQ Trust',
            'DIA': 'SPDR Dow Jones Industrial Average ETF',
            'IWM': 'iShares Russell 2000 ETF',
            'VTI': 'Vanguard Total Stock Market ETF',
            'VOO': 'Vanguard S&P 500 ETF',
            'VEA': 'Vanguard FTSE Developed Markets ETF',
            'VWO': 'Vanguard FTSE Emerging Markets ETF'
        }
        
        # Horarios de mercado US
        self.market_hours = {
            'pre_market': {'start': '04:00', 'end': '09:30'},
            'regular': {'start': '09:30', 'end': '16:00'},
            'after_hours': {'start': '16:00', 'end': '20:00'}
        }
        
        # Cache para datos
        self.cache = {}
        self.cache_duration = 300  # 5 minutos
        
    def get_data(self, symbol: str, timeframe: str = '1h', 
                 start_date: str = None, end_date: str = None,
                 source: str = 'auto') -> pd.DataFrame:
        """
        Obtiene datos de mercado para un índice
        
        Args:
            symbol: Símbolo del índice (ej: 'SPY')
            timeframe: Timeframe ('1m', '5m', '15m', '1h', '1d')
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            source: Fuente de datos ('yahoo', 'alpha_vantage', 'iex', 'auto')
        
        Returns:
            DataFrame con datos OHLCV
        """
        
        # Validar símbolo
        if symbol not in self.supported_indices:
            logger.warning(f"Símbolo {symbol} no está en la lista de índices soportados")
        
        # Verificar cache
        cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"
        if cache_key in self.cache:
            cache_time, data = self.cache[cache_key]
            if time.time() - cache_time < self.cache_duration:
                logger.info(f"Datos obtenidos del cache para {symbol}")
                return data
        
        # Intentar obtener datos según la fuente especificada
        if source == 'auto':
            data = self._get_data_with_fallback(symbol, timeframe, start_date, end_date)
        elif source == 'yahoo':
            data = self._get_yahoo_data(symbol, timeframe, start_date, end_date)
        elif source == 'alpha_vantage':
            data = self._get_alpha_vantage_data(symbol, timeframe, start_date, end_date)
        elif source == 'iex':
            data = self._get_iex_data(symbol, timeframe, start_date, end_date)
        else:
            raise ValueError(f"Fuente no soportada: {source}")
        
        # Guardar en cache
        if data is not None and not data.empty:
            self.cache[cache_key] = (time.time(), data)
            logger.info(f"Datos guardados en cache para {symbol}")
        
        return data
    
    def _get_data_with_fallback(self, symbol: str, timeframe: str, 
                               start_date: str, end_date: str) -> pd.DataFrame:
        """Obtiene datos con fallback automático entre fuentes"""
        
        sources = ['yahoo', 'alpha_vantage', 'iex']
        
        for source in sources:
            try:
                logger.info(f"Intentando obtener datos de {symbol} desde {source}")
                
                if source == 'yahoo':
                    data = self._get_yahoo_data(symbol, timeframe, start_date, end_date)
                elif source == 'alpha_vantage':
                    data = self._get_alpha_vantage_data(symbol, timeframe, start_date, end_date)
                elif source == 'iex':
                    data = self._get_iex_data(symbol, timeframe, start_date, end_date)
                
                if data is not None and not data.empty:
                    logger.info(f"Datos obtenidos exitosamente desde {source}")
                    return data
                    
            except Exception as e:
                logger.warning(f"Error obteniendo datos desde {source}: {str(e)}")
                continue
        
        logger.error(f"No se pudieron obtener datos para {symbol} desde ninguna fuente")
        return pd.DataFrame()
    
    def _get_yahoo_data(self, symbol: str, timeframe: str, 
                       start_date: str, end_date: str) -> pd.DataFrame:
        """Obtiene datos desde Yahoo Finance"""
        
        try:
            # Mapear timeframes
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', 
                '30m': '30m', '1h': '1h', '1d': '1d'
            }
            
            interval = interval_map.get(timeframe, '1h')
            
            # Configurar fechas
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Obtener datos
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                prepost=True  # Incluir pre/post market
            )
            
            if data.empty:
                logger.warning(f"No se encontraron datos para {symbol} en Yahoo Finance")
                return pd.DataFrame()
            
            # Estandarizar columnas
            data = data.rename(columns={
                'Open': 'open', 'High': 'high', 'Low': 'low', 
                'Close': 'close', 'Volume': 'volume'
            })
            
            # Agregar metadatos
            data['symbol'] = symbol
            data['timeframe'] = timeframe
            data['source'] = 'yahoo'
            
            logger.info(f"Obtenidos {len(data)} registros de Yahoo Finance para {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de Yahoo Finance: {str(e)}")
            raise
    
    def _get_alpha_vantage_data(self, symbol: str, timeframe: str, 
                               start_date: str, end_date: str) -> pd.DataFrame:
        """Obtiene datos desde Alpha Vantage"""
        
        if not self.alpha_vantage_key:
            logger.warning("API key de Alpha Vantage no configurada")
            return pd.DataFrame()
        
        try:
            # Mapear timeframes
            function_map = {
                '1m': 'TIME_SERIES_INTRADAY',
                '5m': 'TIME_SERIES_INTRADAY',
                '15m': 'TIME_SERIES_INTRADAY',
                '30m': 'TIME_SERIES_INTRADAY',
                '1h': 'TIME_SERIES_INTRADAY',
                '1d': 'TIME_SERIES_DAILY'
            }
            
            interval_map = {
                '1m': '1min', '5m': '5min', '15m': '15min',
                '30m': '30min', '1h': '60min'
            }
            
            function = function_map.get(timeframe, 'TIME_SERIES_INTRADAY')
            interval = interval_map.get(timeframe, '60min')
            
            # Construir URL
            base_url = "https://www.alphavantage.co/query"
            params = {
                'function': function,
                'symbol': symbol,
                'apikey': self.alpha_vantage_key,
                'outputsize': 'full'
            }
            
            if function == 'TIME_SERIES_INTRADAY':
                params['interval'] = interval
            
            # Realizar petición
            response = requests.get(base_url, params=params)
            data_json = response.json()
            
            # Procesar respuesta
            if 'Error Message' in data_json:
                logger.error(f"Error de Alpha Vantage: {data_json['Error Message']}")
                return pd.DataFrame()
            
            if 'Note' in data_json:
                logger.warning(f"Límite de API alcanzado: {data_json['Note']}")
                return pd.DataFrame()
            
            # Extraer datos de series temporales
            time_series_key = None
            for key in data_json.keys():
                if 'Time Series' in key:
                    time_series_key = key
                    break
            
            if not time_series_key:
                logger.error("No se encontraron datos de series temporales")
                return pd.DataFrame()
            
            time_series = data_json[time_series_key]
            
            # Convertir a DataFrame
            df_data = []
            for timestamp, values in time_series.items():
                df_data.append({
                    'timestamp': pd.to_datetime(timestamp),
                    'open': float(values['1. open']),
                    'high': float(values['2. high']),
                    'low': float(values['3. low']),
                    'close': float(values['4. close']),
                    'volume': int(values['5. volume'])
                })
            
            data = pd.DataFrame(df_data)
            data.set_index('timestamp', inplace=True)
            data.sort_index(inplace=True)
            
            # Filtrar por fechas si se especifican
            if start_date:
                data = data[data.index >= start_date]
            if end_date:
                data = data[data.index <= end_date]
            
            # Agregar metadatos
            data['symbol'] = symbol
            data['timeframe'] = timeframe
            data['source'] = 'alpha_vantage'
            
            logger.info(f"Obtenidos {len(data)} registros de Alpha Vantage para {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de Alpha Vantage: {str(e)}")
            raise
    
    def _get_iex_data(self, symbol: str, timeframe: str, 
                     start_date: str, end_date: str) -> pd.DataFrame:
        """Obtiene datos desde IEX Cloud"""
        
        if not self.iex_cloud_key:
            logger.warning("API key de IEX Cloud no configurada")
            return pd.DataFrame()
        
        try:
            # IEX Cloud tiene limitaciones en timeframes
            if timeframe in ['1m', '5m', '15m', '30m']:
                logger.warning(f"IEX Cloud no soporta timeframe {timeframe}, usando 1d")
                timeframe = '1d'
            
            # Construir URL
            base_url = f"https://cloud.iexapis.com/stable/stock/{symbol}/chart"
            
            # Determinar rango
            if timeframe == '1h':
                range_param = '1m'  # 1 mes de datos horarios
            else:
                range_param = '1y'  # 1 año de datos diarios
            
            params = {
                'token': self.iex_cloud_key,
                'range': range_param
            }
            
            # Realizar petición
            response = requests.get(base_url, params=params)
            data_json = response.json()
            
            if not data_json:
                logger.warning(f"No se encontraron datos para {symbol} en IEX Cloud")
                return pd.DataFrame()
            
            # Convertir a DataFrame
            df_data = []
            for item in data_json:
                df_data.append({
                    'timestamp': pd.to_datetime(item['date']),
                    'open': float(item['open']) if item['open'] else 0,
                    'high': float(item['high']) if item['high'] else 0,
                    'low': float(item['low']) if item['low'] else 0,
                    'close': float(item['close']) if item['close'] else 0,
                    'volume': int(item['volume']) if item['volume'] else 0
                })
            
            data = pd.DataFrame(df_data)
            data.set_index('timestamp', inplace=True)
            data.sort_index(inplace=True)
            
            # Filtrar por fechas si se especifican
            if start_date:
                data = data[data.index >= start_date]
            if end_date:
                data = data[data.index <= end_date]
            
            # Agregar metadatos
            data['symbol'] = symbol
            data['timeframe'] = timeframe
            data['source'] = 'iex'
            
            logger.info(f"Obtenidos {len(data)} registros de IEX Cloud para {symbol}")
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de IEX Cloud: {str(e)}")
            raise
    
    def is_market_open(self, timestamp: datetime = None) -> Dict[str, bool]:
        """
        Verifica si el mercado está abierto
        
        Returns:
            Dict con estado de cada sesión de mercado
        """
        
        if timestamp is None:
            timestamp = datetime.now()
        
        # Verificar si es día de semana
        if timestamp.weekday() >= 5:  # Sábado o domingo
            return {
                'pre_market': False,
                'regular': False,
                'after_hours': False,
                'any_session': False
            }
        
        # Obtener hora actual en formato HH:MM
        current_time = timestamp.strftime('%H:%M')
        
        # Verificar cada sesión
        pre_market = (self.market_hours['pre_market']['start'] <= current_time < 
                     self.market_hours['pre_market']['end'])
        regular = (self.market_hours['regular']['start'] <= current_time < 
                  self.market_hours['regular']['end'])
        after_hours = (self.market_hours['after_hours']['start'] <= current_time < 
                      self.market_hours['after_hours']['end'])
        
        return {
            'pre_market': pre_market,
            'regular': regular,
            'after_hours': after_hours,
            'any_session': pre_market or regular or after_hours
        }
    
    def get_real_time_quote(self, symbol: str) -> Dict:
        """Obtiene cotización en tiempo real"""
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Obtener datos de precio actual
            current_data = ticker.history(period='1d', interval='1m').tail(1)
            
            if current_data.empty:
                return {}
            
            quote = {
                'symbol': symbol,
                'price': float(current_data['Close'].iloc[0]),
                'change': float(info.get('regularMarketChange', 0)),
                'change_percent': float(info.get('regularMarketChangePercent', 0)),
                'volume': int(current_data['Volume'].iloc[0]),
                'timestamp': current_data.index[0],
                'market_state': info.get('marketState', 'UNKNOWN')
            }
            
            return quote
            
        except Exception as e:
            logger.error(f"Error obteniendo cotización en tiempo real: {str(e)}")
            return {}
    
    def get_supported_symbols(self) -> Dict[str, str]:
        """Retorna lista de símbolos soportados"""
        return self.supported_indices.copy()
    
    def validate_symbol(self, symbol: str) -> bool:
        """Valida si un símbolo está soportado"""
        return symbol in self.supported_indices
    
    def clear_cache(self):
        """Limpia el cache de datos"""
        self.cache.clear()
        logger.info("Cache limpiado")

# Función de utilidad para crear instancia configurada
def create_indices_provider(config: Dict = None) -> IndicesDataProvider:
    """
    Crea una instancia configurada del proveedor de datos
    
    Args:
        config: Diccionario de configuración
    
    Returns:
        Instancia de IndicesDataProvider
    """
    
    default_config = {
        'alpha_vantage_key': os.getenv('ALPHA_VANTAGE_KEY'),
        'iex_cloud_key': os.getenv('IEX_CLOUD_KEY'),
        'cache_duration': 300,
        'default_timeframe': '1h',
        'default_period': '30d'
    }
    
    if config:
        default_config.update(config)
    
    return IndicesDataProvider(default_config)

if __name__ == "__main__":
    # Ejemplo de uso
    provider = create_indices_provider()
    
    # Obtener datos de SPY
    print("Obteniendo datos de SPY...")
    spy_data = provider.get_data('SPY', timeframe='1h', start_date='2024-01-01')
    print(f"Datos obtenidos: {len(spy_data)} registros")
    print(spy_data.head())
    
    # Verificar estado del mercado
    market_status = provider.is_market_open()
    print(f"Estado del mercado: {market_status}")
    
    # Obtener cotización en tiempo real
    quote = provider.get_real_time_quote('SPY')
    print(f"Cotización actual: {quote}")