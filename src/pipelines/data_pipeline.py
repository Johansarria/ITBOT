# /src/pipelines/data_pipeline.py

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import logging
from typing import Optional

# Configurar logging
logger = logging.getLogger(__name__)

class DataPipeline:
    """
    Pipeline para adquisición y procesamiento de datos de mercado.
    Soporta múltiples símbolos de trading simultáneamente.
    """
    
    def __init__(self, data_dir: str = "../data", symbols: list = None):
        """
        Inicializa el pipeline de datos.
        
        Args:
            data_dir: Directorio base para almacenar datos
            symbols: Lista de símbolos a procesar (ej: ['BTCUSDT', 'ETHUSDT'])
        """
        self.data_dir = data_dir
        self.raw_dir = os.path.join(data_dir, "raw")
        self.processed_dir = os.path.join(data_dir, "processed")
        
        # Crear directorios si no existen
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        # Símbolos a procesar
        self.symbols = symbols or ['BTCUSDT']
        
        # Cache para datos de múltiples símbolos
        self.data_cache = {}
        
        logger.info(f"📊 Pipeline inicializado para símbolos: {self.symbols}")
    
    def get_market_data(self, ticker: str, period: str = "1mo", interval: str = "4h") -> pd.DataFrame:
        """
        Descarga datos históricos de mercado desde Binance o Yahoo Finance.
        
        Args:
            ticker: Símbolo del activo (ej: 'BTC/USDT' o 'BTCUSDT')
            period: Período de datos ('1mo', '3mo', '6mo', '1y', '2y', '5y')
            interval: Intervalo de tiempo ('1m', '5m', '15m', '30m', '1h', '4h', '1d')
            
        Returns:
            DataFrame con datos OHLCV y indicadores técnicos
        """
        try:
            logger.info(f"Descargando datos para {ticker}...")
            
            # Intentar obtener datos de Binance primero si es un par de criptomonedas
            if self._is_crypto_pair(ticker):
                data = self._get_binance_data(ticker, period, interval)
                if data is not None and not data.empty:
                    logger.info(f"Datos obtenidos de Binance: {len(data)} barras")
                    return data
            
            allowed_intervals = {"1m","5m","15m","30m","1h","2h","4h","1d"}
            interval = interval if interval in allowed_intervals else "4h"
            yf_ticker = ticker.replace('/', '-')
            if yf_ticker.endswith('USDT'):
                yf_ticker = yf_ticker.replace('USDT', '-USD')
            elif yf_ticker.endswith('USDC'):
                yf_ticker = yf_ticker.replace('USDC', '-USD')
            data = yf.download(yf_ticker, period=period, interval=interval, progress=False)
            
            if data.empty:
                logger.error(f"No se pudieron descargar datos para {ticker}.")
                logger.error("SICAR requiere datos reales para operar correctamente.")
                return pd.DataFrame()
            
            # Limpiar nombres de columnas
            data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
            data.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
            
            # Agregar indicadores técnicos
            data = self._add_technical_indicators(data)
            
            # Guardar datos
            self._save_data(data, f"{ticker.replace('/', '_')}_market_data.csv")
            
            logger.info(f"Datos descargados exitosamente: {len(data)} barras")
            return data
            
        except Exception as e:
            logger.error(f"Error descargando datos: {str(e)}")
            logger.error("SICAR requiere datos reales para operar correctamente.")
            return pd.DataFrame()
    
    def _is_crypto_pair(self, ticker: str) -> bool:
        """
        Determina si el ticker es un par de criptomonedas.
        
        Args:
            ticker: Símbolo del activo
            
        Returns:
            True si es un par de criptomonedas
        """
        crypto_indicators = ['USDT', 'USDC', 'BTC', 'ETH', 'BNB', 'BUSD']
        ticker_upper = ticker.upper().replace('/', '')
        return any(indicator in ticker_upper for indicator in crypto_indicators)
    
    def _get_binance_data(self, ticker: str, period: str, interval: str) -> Optional[pd.DataFrame]:
        """
        Obtiene datos históricos de Binance usando fetcher robusto.
        
        Args:
            ticker: Símbolo del activo
            period: Período de datos
            interval: Intervalo de tiempo
            
        Returns:
            DataFrame con datos OHLCV o None si falla
        """
        try:
            # Importar el fetcher robusto
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from robust_data_fetcher import RobustDataFetcher
            
            # Convertir ticker al formato de Binance
            binance_symbol = ticker.replace('/', '').upper()
            
            # Calcular límite basado en período
            period_limits = {
                '1mo': 720,   # ~30 días * 24 horas / 4h
                '3mo': 2160,  # ~90 días * 24 horas / 4h
                '6mo': 4320,  # ~180 días * 24 horas / 4h
                '1y': 8760,   # ~365 días * 24 horas / 4h
                '2y': 17520,  # ~730 días * 24 horas / 4h
                '5y': 43800   # ~1825 días * 24 horas / 4h
            }
            
            limit = period_limits.get(period, 720)
            
            # Crear fetcher robusto
            fetcher = RobustDataFetcher()
            
            # Obtener datos
            df = fetcher.get_market_data(binance_symbol, interval, limit)
            
            if df is None or df.empty:
                logger.warning(f"No se pudieron obtener datos para {binance_symbol}")
                return None
            
            # Verificar que el DataFrame tiene las columnas necesarias
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"Faltan columnas requeridas en los datos: {required_columns}")
                return None
            
            # Agregar columna Adj Close (igual a Close para crypto)
            df['Adj Close'] = df['Close']
            
            # Agregar indicadores técnicos
            df = self._add_technical_indicators(df)
            
            # Guardar datos
            self._save_data(df, f"{ticker.replace('/', '_')}_binance_data.csv")
            
            logger.info(f"✅ Datos obtenidos exitosamente de Binance para {binance_symbol}")
            logger.info(f"📈 Dataset: {len(df)} puntos de datos")
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de Binance: {str(e)}")
            return None
    
    def _save_data(self, data: pd.DataFrame, filename: str) -> None:
        """
        Guarda los datos en el directorio raw.
        
        Args:
            data: DataFrame a guardar
            filename: Nombre del archivo
        """
        try:
            output_path = os.path.join(self.raw_dir, filename)
            data.to_csv(output_path)
            logger.info(f"Datos guardados en {output_path}")
        except Exception as e:
            logger.error(f"Error guardando datos: {str(e)}")
    
    def _add_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Agrega indicadores técnicos básicos al DataFrame.
        
        Args:
            data: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con indicadores técnicos agregados
        """
        try:
            # Determinar el nombre de la columna de cierre
            close_col = 'Close' if 'Close' in data.columns else 'close'
            volume_col = 'Volume' if 'Volume' in data.columns else 'volume'
            
            # RSI (Relative Strength Index)
            delta = data[close_col].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['rsi'] = 100 - (100 / (1 + rs))
            
            # Medias móviles
            data['sma_20'] = data[close_col].rolling(window=20).mean()
            data['sma_50'] = data[close_col].rolling(window=50).mean()
            data['ema_12'] = data[close_col].ewm(span=12).mean()
            data['ema_26'] = data[close_col].ewm(span=26).mean()
            
            # MACD
            data['macd'] = data['ema_12'] - data['ema_26']
            data['macd_signal'] = data['macd'].ewm(span=9).mean()
            data['macd_histogram'] = data['macd'] - data['macd_signal']
            
            # Bollinger Bands
            data['bb_middle'] = data[close_col].rolling(window=20).mean()
            bb_std = data[close_col].rolling(window=20).std()
            data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
            data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
            
            # Volatilidad
            data['volatility'] = data[close_col].pct_change().rolling(window=20).std()
            
            # Volumen promedio
            if volume_col in data.columns:
                data['volume_sma'] = data[volume_col].rolling(window=20).mean()
            
            logger.info("Indicadores técnicos agregados exitosamente")
            return data
            
        except Exception as e:
            logger.error(f"Error agregando indicadores técnicos: {str(e)}")
            return data
    


    def get_multi_timeframe_data(self, ticker: str, timeframes: list = None, period: str = "1mo") -> dict:
        """
        Obtiene datos de mercado para múltiples timeframes.
        
        Args:
            ticker: Símbolo del activo (ej: 'BTC/USDT')
            timeframes: Lista de timeframes ['15m', '30m', '45m', '1h', '2h', '3h', '4h']
            period: Período de datos ('1mo', '3mo', '6mo', '1y', '2y', '5y')
            
        Returns:
            Diccionario con DataFrames para cada timeframe
        """
        if timeframes is None:
            timeframes = ['15m', '30m', '45m', '1h', '2h', '3h', '4h']
        
        multi_data = {}
        
        logger.info(f"🔄 Obteniendo datos multi-timeframe para {ticker}")
        logger.info(f"📊 Timeframes: {timeframes}")
        
        for tf in timeframes:
            try:
                logger.info(f"⏱️ Procesando timeframe: {tf}")
                data = self.get_market_data(ticker, period=period, interval=tf)
                
                if data is not None and not data.empty:
                    multi_data[tf] = data
                    logger.info(f"✅ {tf}: {len(data)} barras obtenidas")
                else:
                    logger.warning(f"⚠️ No se pudieron obtener datos para {tf}")
                    
            except Exception as e:
                logger.error(f"❌ Error obteniendo datos para {tf}: {str(e)}")
                continue
        
        # Validar que tenemos al menos un timeframe
        if not multi_data:
            logger.error("❌ No se pudieron obtener datos para ningún timeframe")
            return {}
        
        # Sincronizar timestamps entre timeframes
        multi_data = self._synchronize_timeframes(multi_data)
        
        logger.info(f"🎯 Multi-timeframe completado: {list(multi_data.keys())}")
        return multi_data
    
    def _synchronize_timeframes(self, multi_data: dict) -> dict:
        """
        Sincroniza los timestamps entre diferentes timeframes.
        
        Args:
            multi_data: Diccionario con datos de múltiples timeframes
            
        Returns:
            Diccionario con datos sincronizados
        """
        if not multi_data:
            return multi_data
        
        logger.info("🔄 Sincronizando timeframes...")
        
        # Encontrar el rango de fechas común
        start_dates = []
        end_dates = []
        
        for tf, data in multi_data.items():
            if not data.empty:
                start_dates.append(data.index.min())
                end_dates.append(data.index.max())
        
        if not start_dates:
            return multi_data
        
        # Usar el rango más restrictivo (intersección)
        common_start = max(start_dates)
        common_end = min(end_dates)
        
        logger.info(f"📅 Rango común: {common_start} a {common_end}")
        
        # Filtrar cada timeframe al rango común
        synchronized_data = {}
        for tf, data in multi_data.items():
            if not data.empty:
                mask = (data.index >= common_start) & (data.index <= common_end)
                synchronized_data[tf] = data[mask].copy()
                logger.info(f"⏱️ {tf}: {len(synchronized_data[tf])} barras sincronizadas")
        
        return synchronized_data

    def run_full_pipeline(self, ticker: str, period: str = "1mo", interval: str = "4h") -> pd.DataFrame:
        """
        Ejecuta el pipeline completo de datos.
        
        Args:
            ticker: Símbolo del activo
            period: Período de datos
            interval: Intervalo de tiempo
            
        Returns:
            DataFrame procesado con datos de mercado
        """
        logger.info(f"Iniciando pipeline de datos para {ticker}")
        
        # Obtener datos de mercado
        market_data = self.get_market_data(ticker, period, interval)
        
        if market_data is None or market_data.empty:
            logger.error("No se pudieron obtener datos de mercado")
            return pd.DataFrame()
        
        logger.info(f"Pipeline completado: {len(market_data)} registros procesados")
        return market_data
    
    def get_multi_symbol_data(self, period: str = "1mo", interval: str = "4h", 
                             use_cache: bool = True) -> dict:
        """
        Obtiene datos de mercado para múltiples símbolos.
        
        Args:
            period: Período de datos
            interval: Intervalo de tiempo
            use_cache: Si usar cache para datos ya obtenidos
            
        Returns:
            Diccionario con datos por símbolo {symbol: DataFrame}
        """
        logger.info(f"🔄 Obteniendo datos para {len(self.symbols)} símbolos...")
        
        multi_data = {}
        failed_symbols = []
        
        for symbol in self.symbols:
            try:
                # Verificar cache si está habilitado
                cache_key = f"{symbol}_{period}_{interval}"
                if use_cache and cache_key in self.data_cache:
                    logger.info(f"📋 Usando datos en cache para {symbol}")
                    multi_data[symbol] = self.data_cache[cache_key]
                    continue
                
                # Obtener datos frescos
                logger.info(f"📊 Obteniendo datos para {symbol}...")
                data = self.get_market_data(symbol, period, interval)
                
                if data is not None and not data.empty:
                    multi_data[symbol] = data
                    # Guardar en cache
                    if use_cache:
                        self.data_cache[cache_key] = data
                    logger.info(f"✅ {symbol}: {len(data)} registros obtenidos")
                else:
                    failed_symbols.append(symbol)
                    logger.warning(f"⚠️ No se pudieron obtener datos para {symbol}")
                    
            except Exception as e:
                failed_symbols.append(symbol)
                logger.error(f"❌ Error obteniendo datos para {symbol}: {str(e)}")
        
        # Resumen de resultados
        successful_symbols = list(multi_data.keys())
        logger.info(f"📈 Datos obtenidos exitosamente para: {successful_symbols}")
        
        if failed_symbols:
            logger.warning(f"⚠️ Falló la obtención de datos para: {failed_symbols}")
        
        return multi_data
    
    def get_synchronized_data(self, period: str = "1mo", interval: str = "4h") -> pd.DataFrame:
        """
        Obtiene datos sincronizados para múltiples símbolos.
        Alinea los timestamps y crea un DataFrame unificado.
        
        Args:
            period: Período de datos
            interval: Intervalo de tiempo
            
        Returns:
            DataFrame con datos sincronizados de todos los símbolos
        """
        logger.info("🔄 Obteniendo datos sincronizados para múltiples símbolos...")
        
        # Obtener datos de todos los símbolos
        multi_data = self.get_multi_symbol_data(period, interval)
        
        if not multi_data:
            logger.error("❌ No se pudieron obtener datos para ningún símbolo")
            return pd.DataFrame()
        
        # Encontrar el rango de fechas común
        common_start = None
        common_end = None
        
        for symbol, data in multi_data.items():
            if common_start is None or data.index[0] > common_start:
                common_start = data.index[0]
            if common_end is None or data.index[-1] < common_end:
                common_end = data.index[-1]
        
        logger.info(f"📅 Rango común: {common_start} a {common_end}")
        
        # Crear DataFrame sincronizado
        synchronized_data = pd.DataFrame()
        
        for symbol, data in multi_data.items():
            # Filtrar al rango común
            symbol_data = data.loc[common_start:common_end].copy()
            
            # Agregar prefijo del símbolo a las columnas
            symbol_data.columns = [f"{symbol}_{col}" for col in symbol_data.columns]
            
            # Unir al DataFrame principal
            if synchronized_data.empty:
                synchronized_data = symbol_data
            else:
                synchronized_data = synchronized_data.join(symbol_data, how='outer')
        
        # Rellenar valores faltantes con forward fill
        synchronized_data = synchronized_data.fillna(method='ffill')
        
        logger.info(f"✅ Datos sincronizados: {len(synchronized_data)} registros, {len(synchronized_data.columns)} columnas")
        
        return synchronized_data
    
    def update_symbols(self, new_symbols: list) -> None:
        """
        Actualiza la lista de símbolos a procesar.
        
        Args:
            new_symbols: Nueva lista de símbolos
        """
        self.symbols = new_symbols
        # Limpiar cache para evitar inconsistencias
        self.data_cache.clear()
        logger.info(f"📊 Símbolos actualizados: {self.symbols}")
    
    def clear_cache(self) -> None:
        """Limpia el cache de datos."""
        self.data_cache.clear()
        logger.info("🗑️ Cache de datos limpiado")
    
    def get_cache_info(self) -> dict:
        """
        Obtiene información sobre el cache actual.
        
        Returns:
            Diccionario con información del cache
        """
        cache_info = {}
        for key, data in self.data_cache.items():
            cache_info[key] = {
                'records': len(data),
                'columns': len(data.columns),
                'date_range': f"{data.index[0]} to {data.index[-1]}"
            }
        return cache_info

def main():
    """
    Función principal para pruebas del pipeline.
    """
    pipeline = DataPipeline()
    
    # Probar con diferentes símbolos
    symbols = ['BTCUSDT', 'ETHUSDT', 'AAPL']
    
    for symbol in symbols:
        print(f"\n=== Probando {symbol} ===")
        data = pipeline.run_full_pipeline(symbol, period="1mo", interval="4h")
        if not data.empty:
            print(f"Datos obtenidos: {len(data)} registros")
            print(f"Rango de fechas: {data.index[0]} a {data.index[-1]}")
            print(f"Precio actual: ${data['Close'].iloc[-1]:.2f}")
        else:
            print("No se pudieron obtener datos")

if __name__ == "__main__":
    main()
