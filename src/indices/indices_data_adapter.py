"""
SICAR Indices Data Adapter
Adaptador para migrar de datos de Binance (crypto) a Yahoo Finance/IEX (índices)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndicesDataAdapter:
    """
    Adaptador de datos para migrar de crypto (Binance) a índices (Yahoo Finance/IEX)
    Mantiene compatibilidad con el sistema SICAR existente
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Mapeo de símbolos crypto a índices
        self.crypto_to_index_mapping = {
            'BTCUSDT': 'SPY',    # Bitcoin -> S&P 500
            'ETHUSDT': 'QQQ',    # Ethereum -> Nasdaq 100
            'ADAUSDT': 'IWM',    # Cardano -> Russell 2000
            'BNBUSDT': 'DIA',    # Binance Coin -> Dow Jones
            'SOLUSDT': 'VTI',    # Solana -> Total Market
            'DOTUSDT': 'SPY',    # Polkadot -> S&P 500
            'LINKUSDT': 'QQQ',   # Chainlink -> Nasdaq 100
            'MATICUSDT': 'IWM'   # Polygon -> Russell 2000
        }
        
        # Mapeo de intervalos crypto a índices
        self.interval_mapping = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '1d',    # 4h crypto -> 1d índices
            '1d': '1d',
            '1w': '1wk',
            '1M': '1mo'
        }
        
        # Factores de ajuste para diferentes características
        self.adjustment_factors = {
            'volatility': {
                'SPY': 0.3,    # Índices menos volátiles que crypto
                'QQQ': 0.4,
                'IWM': 0.5,
                'DIA': 0.3,
                'VTI': 0.3
            },
            'volume': {
                'SPY': 50000000,   # Volúmenes típicos
                'QQQ': 30000000,
                'IWM': 20000000,
                'DIA': 5000000,
                'VTI': 3000000
            }
        }
    
    def map_crypto_to_index(self, crypto_symbol: str) -> Optional[str]:
        """
        Mapear símbolo de crypto a índice equivalente
        
        Args:
            crypto_symbol: Símbolo de crypto (ej: 'BTCUSDT')
            
        Returns:
            Símbolo de índice equivalente o None
        """
        return self.crypto_to_index_mapping.get(crypto_symbol.upper())
    
    def map_interval(self, crypto_interval: str) -> str:
        """
        Mapear intervalo de crypto a intervalo de índice
        
        Args:
            crypto_interval: Intervalo de crypto (ej: '1h')
            
        Returns:
            Intervalo equivalente para índices
        """
        return self.interval_mapping.get(crypto_interval, '1d')
    
    def calculate_period_from_interval(self, interval: str, days_back: int = 100) -> str:
        """
        Calcular período para Yahoo Finance basado en intervalo
        
        Args:
            interval: Intervalo de datos
            days_back: Días hacia atrás
            
        Returns:
            Período en formato Yahoo Finance
        """
        if interval in ['1m', '5m']:
            return '7d'  # Máximo 7 días para intervalos de minutos
        elif interval in ['15m', '30m']:
            return '60d'  # Máximo 60 días
        elif interval == '1h':
            return '730d'  # Máximo 2 años
        else:
            return 'max'  # Para intervalos diarios o mayores
    
    def adapt_data_format(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Adaptar formato de datos para mantener compatibilidad con SICAR
        
        Args:
            data: DataFrame con datos OHLCV
            symbol: Símbolo del índice
            
        Returns:
            DataFrame adaptado con columnas SICAR
        """
        try:
            # Crear copia para no modificar original
            adapted_data = data.copy()
            
            # Asegurar que tenemos las columnas básicas OHLCV
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in adapted_data.columns:
                    self.logger.warning(f"Columna {col} faltante para {symbol}")
                    # Crear columna con valores por defecto si falta
                    if col == 'Volume':
                        adapted_data[col] = self.adjustment_factors['volume'].get(symbol, 1000000)
                    else:
                        adapted_data[col] = adapted_data.get('Close', 100.0)
            
            # Agregar columna Adj Close si no existe
            if 'Adj Close' not in adapted_data.columns:
                adapted_data['Adj Close'] = adapted_data['Close']
            
            # Agregar columnas requeridas por SICAR
            adapted_data['price'] = adapted_data['Close']
            
            # Calcular returns
            adapted_data['returns'] = adapted_data['Close'].pct_change()
            
            # Calcular volatilidad (rolling 20 períodos)
            adapted_data['volatility'] = adapted_data['returns'].rolling(window=20).std()
            
            # Aplicar factores de ajuste específicos del índice
            if symbol in self.adjustment_factors['volatility']:
                vol_factor = self.adjustment_factors['volatility'][symbol]
                adapted_data['volatility'] = adapted_data['volatility'] * vol_factor
            
            # Limpiar datos
            adapted_data = self._clean_data(adapted_data, symbol)
            
            return adapted_data
            
        except Exception as e:
            self.logger.error(f"Error adaptando datos para {symbol}: {e}")
            return data
    
    def _clean_data(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Limpiar y validar datos"""
        try:
            # Eliminar filas con valores NaN en columnas críticas
            critical_columns = ['Open', 'High', 'Low', 'Close']
            data = data.dropna(subset=critical_columns)
            
            # Validar relaciones OHLC
            invalid_mask = (
                (data['High'] < data['Low']) |
                (data['High'] < data['Open']) |
                (data['High'] < data['Close']) |
                (data['Low'] > data['Open']) |
                (data['Low'] > data['Close'])
            )
            
            if invalid_mask.any():
                self.logger.warning(f"Eliminando {invalid_mask.sum()} registros con OHLC inválido para {symbol}")
                data = data[~invalid_mask]
            
            # Eliminar precios negativos o cero
            price_columns = ['Open', 'High', 'Low', 'Close']
            for col in price_columns:
                negative_mask = data[col] <= 0
                if negative_mask.any():
                    self.logger.warning(f"Eliminando {negative_mask.sum()} registros con {col} <= 0 para {symbol}")
                    data = data[~negative_mask]
            
            # Eliminar volumen negativo
            if 'Volume' in data.columns:
                negative_vol_mask = data['Volume'] < 0
                if negative_vol_mask.any():
                    self.logger.warning(f"Corrigiendo {negative_vol_mask.sum()} registros con volumen negativo para {symbol}")
                    data.loc[negative_vol_mask, 'Volume'] = 0
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error limpiando datos para {symbol}: {e}")
            return data
    
    def apply_market_hours_filter(self, data: pd.DataFrame, 
                                 session_type: str = 'regular') -> pd.DataFrame:
        """
        Aplicar filtro de horarios de mercado
        
        Args:
            data: DataFrame con datos
            session_type: Tipo de sesión ('regular', 'extended', 'all')
            
        Returns:
            DataFrame filtrado por horarios
        """
        try:
            if session_type == 'all':
                return data
            
            # Filtrar por horarios de mercado US
            if hasattr(data.index, 'hour'):
                if session_type == 'regular':
                    # Horario regular: 9:30 AM - 4:00 PM ET
                    market_hours_mask = (
                        (data.index.hour >= 9) & 
                        (data.index.hour < 16) |
                        ((data.index.hour == 9) & (data.index.minute >= 30))
                    )
                elif session_type == 'extended':
                    # Horario extendido: 4:00 AM - 8:00 PM ET
                    market_hours_mask = (
                        (data.index.hour >= 4) & 
                        (data.index.hour < 20)
                    )
                else:
                    market_hours_mask = pd.Series([True] * len(data), index=data.index)
                
                # Filtrar solo días de semana (lunes=0, domingo=6)
                weekday_mask = data.index.weekday < 5
                
                final_mask = market_hours_mask & weekday_mask
                return data[final_mask]
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error aplicando filtro de horarios: {e}")
            return data
    
    def apply_quality_filters(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Aplicar filtros de calidad específicos para índices
        
        Args:
            data: DataFrame con datos
            symbol: Símbolo del índice
            
        Returns:
            DataFrame filtrado
        """
        try:
            if len(data) == 0:
                return data
            
            # Filtro de volumen mínimo
            min_volume = self.adjustment_factors['volume'].get(symbol, 100000)
            if 'Volume' in data.columns:
                volume_mask = data['Volume'] >= min_volume * 0.1  # 10% del volumen típico
                data = data[volume_mask]
            
            # Filtro de volatilidad extrema (eliminar outliers)
            if 'returns' in data.columns:
                returns = data['returns'].dropna()
                if len(returns) > 0:
                    # Eliminar returns extremos (más de 3 desviaciones estándar)
                    std_threshold = 3
                    mean_return = returns.mean()
                    std_return = returns.std()
                    
                    outlier_mask = (
                        abs(data['returns'] - mean_return) > std_threshold * std_return
                    )
                    
                    if outlier_mask.any():
                        self.logger.info(f"Eliminando {outlier_mask.sum()} outliers de volatilidad para {symbol}")
                        data = data[~outlier_mask]
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error aplicando filtros de calidad para {symbol}: {e}")
            return data
    
    def get_data_summary(self, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Obtener resumen de datos adaptados
        
        Args:
            data: DataFrame con datos
            symbol: Símbolo del índice
            
        Returns:
            Diccionario con estadísticas resumidas
        """
        try:
            if len(data) == 0:
                return {'error': 'No data available'}
            
            summary = {
                'symbol': symbol,
                'total_records': len(data),
                'date_range': {
                    'start': data.index.min().strftime('%Y-%m-%d') if hasattr(data.index.min(), 'strftime') else str(data.index.min()),
                    'end': data.index.max().strftime('%Y-%m-%d') if hasattr(data.index.max(), 'strftime') else str(data.index.max())
                },
                'price_stats': {
                    'min': float(data['Close'].min()),
                    'max': float(data['Close'].max()),
                    'mean': float(data['Close'].mean()),
                    'current': float(data['Close'].iloc[-1])
                },
                'volume_stats': {
                    'min': float(data['Volume'].min()) if 'Volume' in data.columns else 0,
                    'max': float(data['Volume'].max()) if 'Volume' in data.columns else 0,
                    'mean': float(data['Volume'].mean()) if 'Volume' in data.columns else 0
                },
                'volatility_stats': {
                    'mean': float(data['volatility'].mean()) if 'volatility' in data.columns else 0,
                    'std': float(data['volatility'].std()) if 'volatility' in data.columns else 0
                },
                'data_quality': {
                    'missing_values': int(data.isnull().sum().sum()),
                    'completeness': float(1 - data.isnull().sum().sum() / (len(data) * len(data.columns)))
                }
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generando resumen para {symbol}: {e}")
            return {'error': str(e)}

# Función de utilidad para adaptación rápida
def quick_adapt_data(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Adaptación rápida de datos"""
    adapter = IndicesDataAdapter()
    return adapter.adapt_data_format(data, symbol)