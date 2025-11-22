#!/usr/bin/env python3
"""
Módulo robusto para obtener datos de mercado con manejo de errores,
timeouts, reintentos y múltiples fuentes de datos.
"""

import pandas as pd
import numpy as np
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import json
import os

logger = logging.getLogger(__name__)

class RobustDataFetcher:
    """
    Fetcher robusto de datos de mercado con múltiples fuentes y fallbacks.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 30  # Timeout más largo
        
        # Configurar headers para evitar bloqueos
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache'
        })
        
        # URLs alternativas para Binance
        self.binance_urls = [
            'https://api.binance.com',
            'https://api1.binance.com',
            'https://api2.binance.com',
            'https://api3.binance.com'
        ]
        
        # Cache local para datos
        self.cache_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def get_market_data(self, symbol='BTCUSDT', interval='4h', limit=500) -> Optional[pd.DataFrame]:
        """
        Obtiene datos de mercado usando múltiples estrategias de fallback.
        
        Args:
            symbol: Símbolo del activo
            interval: Intervalo de tiempo
            limit: Número de velas
            
        Returns:
            DataFrame con datos OHLCV o None si falla
        """
        logger.info(f"🔄 Obteniendo datos para {symbol} ({interval}) - {limit} velas")
        
        # Estrategia 1: Binance API directa con múltiples URLs
        data = self._try_binance_api(symbol, interval, limit)
        if data is not None:
            logger.info("✅ Datos obtenidos de Binance API")
            self._cache_data(data, symbol, interval)
            return data
        
        # Estrategia 2: Binance API sin autenticación
        data = self._try_binance_public(symbol, interval, limit)
        if data is not None:
            logger.info("✅ Datos obtenidos de Binance API pública")
            self._cache_data(data, symbol, interval)
            return data
        
        # Estrategia 3: Yahoo Finance como fallback
        data = self._try_yahoo_finance(symbol, interval, limit)
        if data is not None:
            logger.info("✅ Datos obtenidos de Yahoo Finance")
            self._cache_data(data, symbol, interval)
            return data
        
        # Estrategia 4: Cache local (solo si es reciente)
        data = self._load_cached_data(symbol, interval)
        if data is not None:
            logger.info("✅ Datos cargados desde cache local")
            return data
        
        logger.error("❌ No se pudieron obtener datos reales de ninguna fuente")
        logger.error("❌ SICAR requiere datos reales para operar correctamente")
        return None
    
    def _try_binance_api(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Intenta obtener datos usando la API de Binance con reintentos."""
        for attempt in range(3):
            for base_url in self.binance_urls:
                try:
                    logger.info(f"Intento {attempt + 1}: {base_url}")
                    
                    url = f"{base_url}/api/v3/klines"
                    params = {
                        'symbol': symbol,
                        'interval': interval,
                        'limit': limit
                    }
                    
                    response = self.session.get(url, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            return self._process_binance_data(data)
                    
                    logger.warning(f"Respuesta HTTP {response.status_code} de {base_url}")
                    
                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout conectando a {base_url}")
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Error de conexión a {base_url}")
                except Exception as e:
                    logger.warning(f"Error inesperado con {base_url}: {str(e)}")
                
                time.sleep(1)  # Pausa entre intentos
        
        return None
    
    def _try_binance_public(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Intenta obtener datos usando endpoints públicos alternativos."""
        try:
            # Usar requests directamente sin autenticación
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': min(limit, 1000)  # Límite máximo de Binance
            }
            
            response = requests.get(url, params=params, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return self._process_binance_data(data)
            
        except Exception as e:
            logger.warning(f"Error en API pública de Binance: {str(e)}")
        
        return None
    
    def _process_binance_data(self, raw_data: List) -> pd.DataFrame:
        """Procesa datos brutos de Binance en DataFrame."""
        try:
            df = pd.DataFrame(raw_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos de datos
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convertir timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Renombrar columnas al formato estándar
            df = df.rename(columns={
                'open': 'Open',
                'high': 'High', 
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            })
            
            # Mantener solo columnas necesarias
            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
            
            # Agregar Adj Close
            df['Adj Close'] = df['Close']
            
            # Agregar indicadores básicos
            df = self._add_basic_indicators(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error procesando datos de Binance: {str(e)}")
            return None
    
    def _try_yahoo_finance(self, symbol: str, interval: str, limit: int) -> Optional[pd.DataFrame]:
        """Intenta obtener datos usando Yahoo Finance como fallback."""
        try:
            import yfinance as yf
            
            logger.info(f"Intentando obtener datos de Yahoo Finance para {symbol}")
            
            # Convertir símbolo de Binance a Yahoo Finance
            if symbol.endswith('USDT'):
                yf_symbol = symbol.replace('USDT', '-USD')
            elif symbol.endswith('USDC'):
                yf_symbol = symbol.replace('USDC', '-USD')
            else:
                yf_symbol = symbol
            
            # Mapear intervalos
            interval_map = {
                '1m': '1m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '2h': '2h',
                '4h': '4h',
                '1d': '1d'
            }
            
            yf_interval = interval_map.get(interval, '1h')
            
            # Calcular período basado en el límite
            if interval in ['1m', '5m']:
                period = '7d'  # Yahoo Finance limita datos intraday
            elif interval in ['15m', '30m']:
                period = '60d'
            elif interval in ['1h', '2h']:
                period = '730d'  # 2 años
            else:
                period = '2y'
            
            # Descargar datos
            ticker = yf.Ticker(yf_symbol)
            data = ticker.history(period=period, interval=yf_interval)
            
            if data.empty:
                logger.warning(f"No se obtuvieron datos de Yahoo Finance para {yf_symbol}")
                return None
            
            # Limpiar nombres de columnas si es necesario
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            
            # Asegurar que tenemos las columnas correctas
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_cols):
                logger.warning(f"Faltan columnas requeridas en datos de Yahoo Finance")
                return None
            
            # Tomar solo el número de registros solicitado
            data = data.tail(limit)
            
            # Agregar Adj Close si no existe
            if 'Adj Close' not in data.columns:
                data['Adj Close'] = data['Close']
            
            # Agregar indicadores básicos
            data = self._add_basic_indicators(data)
            
            logger.info(f"Datos de Yahoo Finance obtenidos: {len(data)} registros")
            return data
            
        except ImportError:
            logger.warning("yfinance no está instalado")
            return None
        except Exception as e:
            logger.warning(f"Error obteniendo datos de Yahoo Finance: {str(e)}")
            return None
    
    def _add_basic_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Agrega indicadores técnicos básicos."""
        try:
            # SMA
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            
            # EMA
            df['EMA_12'] = df['Close'].ewm(span=12).mean()
            df['EMA_26'] = df['Close'].ewm(span=26).mean()
            
            # MACD
            df['MACD'] = df['EMA_12'] - df['EMA_26']
            df['MACD_signal'] = df['MACD'].ewm(span=9).mean()
            
            # RSI
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # Volatilidad
            df['volatility'] = df['Close'].pct_change().rolling(window=20).std()
            
            # Bollinger Bands
            df['BB_middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
            df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
            
            return df
            
        except Exception as e:
            logger.warning(f"Error agregando indicadores: {str(e)}")
            return df
    
    def _cache_data(self, data: pd.DataFrame, symbol: str, interval: str):
        """Guarda datos en cache local."""
        try:
            cache_file = os.path.join(self.cache_dir, f"{symbol}_{interval}_cache.csv")
            data.to_csv(cache_file)
            logger.info(f"Datos guardados en cache: {cache_file}")
        except Exception as e:
            logger.warning(f"Error guardando cache: {str(e)}")
    
    def _load_cached_data(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """Carga datos desde cache local."""
        try:
            cache_file = os.path.join(self.cache_dir, f"{symbol}_{interval}_cache.csv")
            if os.path.exists(cache_file):
                # Verificar que el cache no sea muy viejo (máximo 1 hora)
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < 3600:  # 1 hora
                    df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    logger.info(f"Cache cargado: {len(df)} registros")
                    return df
                else:
                    logger.info("Cache muy antiguo, ignorando")
        except Exception as e:
            logger.warning(f"Error cargando cache: {str(e)}")
        
        return None

def test_robust_fetcher():
    """Prueba el fetcher robusto."""
    logger.info("=== PROBANDO FETCHER ROBUSTO ===")
    
    fetcher = RobustDataFetcher()
    
    test_cases = [
        ('BTCUSDT', '4h', 100),
        ('ETHUSDT', '1h', 50),
        ('BTCUSDT', '15m', 200)
    ]
    
    for symbol, interval, limit in test_cases:
        logger.info(f"\n--- Probando {symbol} {interval} ---")
        data = fetcher.get_market_data(symbol, interval, limit)
        
        if data is not None and not data.empty:
            logger.info(f"✅ Éxito: {len(data)} registros")
            logger.info(f"Rango: {data.index[0]} a {data.index[-1]}")
            logger.info(f"Precio actual: ${data['Close'].iloc[-1]:.2f}")
        else:
            logger.error(f"❌ Falló: {symbol} {interval}")

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_robust_fetcher()