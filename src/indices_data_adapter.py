#!/usr/bin/env python3
"""
SICAR Indices Data Adapter
Adaptador para migrar de fuentes de datos de crypto (Binance) a índices (Yahoo Finance/IEX)
Mantiene compatibilidad con el sistema SICAR existente
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import warnings
warnings.filterwarnings('ignore')

# Importar el proveedor de datos de índices
from indices_data_provider import IndicesDataProvider, create_indices_provider
from market_hours_system import MarketHoursSystem, MarketSession
from indices_config import IndicesConfigManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndicesDataAdapter:
    """
    Adaptador que migra el sistema SICAR de crypto (Binance) a índices (Yahoo Finance/IEX)
    Mantiene la misma interfaz que el sistema original para compatibilidad
    """
    
    def __init__(self):
        """Inicializar el adaptador de datos para índices"""
        self.data_provider = create_indices_provider()
        self.market_hours = MarketHoursSystem()
        self.config_manager = IndicesConfigManager()
        
        # Mapeo de símbolos crypto a índices
        self.symbol_mapping = {
            'BTCUSDT': 'SPY',    # Bitcoin -> S&P 500
            'ETHUSDT': 'QQQ',    # Ethereum -> NASDAQ
            'ADAUSDT': 'DIA',    # Cardano -> Dow Jones
            'SOLUSDT': 'IWM',    # Solana -> Russell 2000
            'BNBUSDT': 'SPY',    # Binance Coin -> S&P 500
            'XRPUSDT': 'QQQ',    # Ripple -> NASDAQ
            'DOTUSDT': 'DIA',    # Polkadot -> Dow Jones
            'LINKUSDT': 'IWM',   # Chainlink -> Russell 2000
        }
        
        # Mapeo de intervalos crypto a índices
        self.interval_mapping = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '1d',    # 4h crypto -> 1d índices (más apropiado)
            '1d': '1d',
            '1w': '1wk',
            '1M': '1mo'
        }
        
        logger.info("🔄 Adaptador de datos para índices inicializado")
    
    def get_binance_data(self, symbol: str = 'BTCUSDT', interval: str = '4h', limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Método de compatibilidad que mantiene la misma interfaz que get_binance_data
        pero obtiene datos de índices en lugar de crypto
        
        Args:
            symbol: Símbolo crypto (será mapeado a índice)
            interval: Intervalo de tiempo
            limit: Número de períodos
            
        Returns:
            DataFrame con datos de índices en formato compatible con SICAR
        """
        try:
            # Mapear símbolo crypto a índice
            index_symbol = self.symbol_mapping.get(symbol, 'SPY')
            
            # Mapear intervalo
            index_interval = self.interval_mapping.get(interval, '1d')
            
            logger.info(f"🔄 Adaptando {symbol} -> {index_symbol}, {interval} -> {index_interval}")
            
            # Calcular período basado en limit
            period = self._calculate_period(limit, index_interval)
            
            # Obtener datos del índice
            df = self.data_provider.get_historical_data(
                symbol=index_symbol,
                period=period,
                interval=index_interval
            )
            
            if df is None or df.empty:
                logger.error(f"No se pudieron obtener datos para {index_symbol}")
                return None
            
            # Adaptar formato para compatibilidad con SICAR
            df = self._adapt_data_format(df, symbol, index_symbol)
            
            # Aplicar filtros específicos para índices
            df = self._apply_indices_filters(df, index_symbol, index_interval)
            
            # Limitar a la cantidad solicitada
            if len(df) > limit:
                df = df.tail(limit)
            
            logger.info(f"✅ Datos adaptados exitosamente: {len(df)} registros")
            logger.info(f"📈 Índice: {index_symbol}, Período: {df.index[0]} a {df.index[-1]}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error en adaptador de datos: {e}")
            return None
    
    def get_market_data(self, symbol: str, interval: str = '1d', limit: int = 500) -> Optional[pd.DataFrame]:
        """
        Método alternativo para obtener datos de mercado
        """
        return self.get_binance_data(symbol, interval, limit)
    
    def _calculate_period(self, limit: int, interval: str) -> str:
        """Calcular período basado en limit e interval"""
        try:
            if interval in ['1m', '5m', '15m', '30m']:
                # Para intervalos intraday, usar días
                days = max(1, limit // (24 * 60 // int(interval.replace('m', ''))))
                return f"{min(days, 30)}d"  # Máximo 30 días para intraday
            elif interval == '1h':
                days = max(1, limit // 24)
                return f"{min(days, 60)}d"  # Máximo 60 días para horario
            elif interval == '1d':
                return f"{min(limit, 252)}d"  # Máximo 1 año para diario
            elif interval == '1wk':
                weeks = min(limit, 52)
                return f"{weeks * 7}d"
            elif interval == '1mo':
                months = min(limit, 24)
                return f"{months * 30}d"
            else:
                return "1y"
        except:
            return "1y"
    
    def _adapt_data_format(self, df: pd.DataFrame, original_symbol: str, index_symbol: str) -> pd.DataFrame:
        """
        Adaptar formato de datos para compatibilidad con SICAR
        """
        try:
            # Asegurar que tenemos las columnas estándar
            if 'Adj Close' not in df.columns and 'Close' in df.columns:
                df['Adj Close'] = df['Close']
            
            # Agregar columnas adicionales requeridas por SICAR
            df['price'] = df['Close']
            df['returns'] = df['Close'].pct_change()
            
            # Calcular volatilidad con ventana adaptativa
            window_size = min(20, len(df) // 4)
            if window_size > 1:
                df['volatility'] = df['returns'].rolling(window=window_size, min_periods=1).std()
            else:
                df['volatility'] = 0.0
            
            # Rellenar valores NaN
            df['returns'] = df['returns'].fillna(0.0)
            df['volatility'] = df['volatility'].fillna(df['volatility'].mean() if not df['volatility'].isna().all() else 0.01)
            
            # Agregar metadatos del símbolo
            df.attrs['original_symbol'] = original_symbol
            df.attrs['index_symbol'] = index_symbol
            df.attrs['data_source'] = 'indices_adapter'
            
            return df
            
        except Exception as e:
            logger.error(f"Error adaptando formato de datos: {e}")
            return df
    
    def _apply_indices_filters(self, df: pd.DataFrame, symbol: str, interval: str) -> pd.DataFrame:
        """
        Aplicar filtros específicos para índices
        """
        try:
            # Filtrar solo horarios de mercado para intervalos intraday
            if interval in ['1m', '5m', '15m', '30m', '1h']:
                df = self._filter_market_hours(df)
            
            # Aplicar filtros de calidad de datos
            df = self._apply_quality_filters(df, symbol)
            
            # Aplicar filtros de volatilidad específicos para índices
            df = self._apply_volatility_filters(df, symbol)
            
            return df
            
        except Exception as e:
            logger.error(f"Error aplicando filtros: {e}")
            return df
    
    def _filter_market_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtrar datos para incluir solo horarios de mercado
        """
        try:
            filtered_data = []
            
            for timestamp, row in df.iterrows():
                market_status = self.market_hours.is_market_open(timestamp)
                
                # Incluir solo datos de mercado abierto y pre/post market
                if market_status.get('is_open', False) or market_status.get('current_session') in [
                    MarketSession.PRE_MARKET, MarketSession.REGULAR, MarketSession.AFTER_HOURS
                ]:
                    filtered_data.append(row)
            
            if filtered_data:
                result_df = pd.DataFrame(filtered_data, index=[row.name for row in filtered_data])
                return result_df
            else:
                return df  # Si no hay datos válidos, devolver original
                
        except Exception as e:
            logger.error(f"Error filtrando horarios de mercado: {e}")
            return df
    
    def _apply_quality_filters(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Aplicar filtros de calidad de datos específicos para índices
        """
        try:
            # Filtrar valores extremos (outliers)
            for col in ['Open', 'High', 'Low', 'Close']:
                if col in df.columns:
                    q1 = df[col].quantile(0.01)
                    q99 = df[col].quantile(0.99)
                    df = df[(df[col] >= q1) & (df[col] <= q99)]
            
            # Filtrar volumen mínimo (para evitar datos de baja liquidez)
            if 'Volume' in df.columns:
                min_volume = df['Volume'].quantile(0.1)  # 10% percentil
                df = df[df['Volume'] >= min_volume]
            
            # Filtrar gaps excesivos (más del 5% para índices)
            if len(df) > 1:
                price_changes = df['Close'].pct_change().abs()
                df = df[price_changes <= 0.05]  # Máximo 5% de cambio
            
            return df
            
        except Exception as e:
            logger.error(f"Error aplicando filtros de calidad: {e}")
            return df
    
    def _apply_volatility_filters(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Aplicar filtros de volatilidad específicos para índices
        """
        try:
            # Obtener configuración específica del índice
            config = self.config_manager.get_config(symbol)
            
            # Filtrar volatilidad extrema
            if 'volatility' in df.columns and len(df) > 10:
                vol_threshold = config.volatility_filter.max_volatility
                df = df[df['volatility'] <= vol_threshold]
            
            return df
            
        except Exception as e:
            logger.error(f"Error aplicando filtros de volatilidad: {e}")
            return df
    
    def get_symbol_mapping(self) -> Dict[str, str]:
        """Obtener mapeo de símbolos crypto a índices"""
        return self.symbol_mapping.copy()
    
    def get_available_indices(self) -> List[str]:
        """Obtener lista de índices disponibles"""
        return list(set(self.symbol_mapping.values()))
    
    def is_market_open_now(self) -> bool:
        """Verificar si el mercado está abierto ahora"""
        status = self.market_hours.is_market_open()
        return status.get('is_open', False)
    
    def get_market_status(self) -> Dict:
        """Obtener estado completo del mercado"""
        return self.market_hours.is_market_open()

# Función de compatibilidad global
def get_binance_data(symbol='BTCUSDT', interval='4h', limit=500):
    """
    Función de compatibilidad que mantiene la misma interfaz
    pero usa datos de índices en lugar de crypto
    """
    adapter = IndicesDataAdapter()
    return adapter.get_binance_data(symbol, interval, limit)

# Crear instancia global para compatibilidad
indices_data_adapter = IndicesDataAdapter()

if __name__ == "__main__":
    # Test del adaptador
    print("🧪 Testing Indices Data Adapter...")
    
    adapter = IndicesDataAdapter()
    
    # Test con diferentes símbolos
    test_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    
    for symbol in test_symbols:
        print(f"\n📊 Testing {symbol}...")
        df = adapter.get_binance_data(symbol, '1d', 50)
        
        if df is not None:
            print(f"✅ {symbol} -> {adapter.symbol_mapping.get(symbol)}: {len(df)} registros")
            print(f"   Período: {df.index[0]} a {df.index[-1]}")
            print(f"   Precio: ${df['Close'].iloc[-1]:.2f}")
        else:
            print(f"❌ Error obteniendo datos para {symbol}")
    
    print(f"\n🏁 Test completado")