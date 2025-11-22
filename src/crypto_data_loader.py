#!/usr/bin/env python3
"""
Módulo de datos de criptomonedas para entrenar PatchTST
Obtiene datos históricos de Bitcoin y prepara datasets de entrenamiento
"""

import yfinance as yf
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
import ta
from sklearn.preprocessing import StandardScaler, MinMaxScaler

logger = logging.getLogger(__name__)

class CryptoDataLoader:
    """
    Cargador de datos de criptomonedas para PatchTST
    """
    
    def __init__(self, symbol: str = "BTC-USD", timeframe: str = "1h"):
        self.symbol = symbol
        self.timeframe = timeframe
        self.exchange = ccxt.binance()
        # Mapeo de símbolos comunes
        self.symbol_map = {
            "BTC-USD": "BTC-USD",
            "BTCUSD": "BTC-USD", 
            "BTC": "BTC-USD",
            "ETH-USD": "ETH-USD",
            "ETH": "ETH-USD"
        }
        
    def get_yahoo_data(self, 
                      start_date: str = None, 
                      end_date: str = None,
                      period: str = "2y") -> pd.DataFrame:
        """
        Obtener datos de Yahoo Finance
        
        Args:
            start_date: Fecha inicial (YYYY-MM-DD)
            end_date: Fecha final (YYYY-MM-DD)
            period: Período predefinido (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            
        Returns:
            DataFrame con datos OHLCV
        """
        logger.info(f"Obteniendo datos de Yahoo Finance para {self.symbol} período {period}")
        
        try:
            # Intentar con el símbolo original
            ticker = yf.Ticker(self.symbol)
            
            if start_date and end_date:
                data = ticker.history(start=start_date, end=end_date, interval=self.timeframe)
            else:
                data = ticker.history(period=period, interval=self.timeframe)
            
            # Si no hay datos, intentar con símbolos alternativos
            if data.empty:
                logger.warning(f"Sin datos para {self.symbol}, intentando alternativas")
                
                # Probar con símbolos alternativos
                alt_symbols = [self.symbol.replace('-', ''), f"{self.symbol}-USD", "BTC-USD"]
                
                for alt_symbol in alt_symbols:
                    if alt_symbol != self.symbol:
                        logger.info(f"Intentando con símbolo alternativo: {alt_symbol}")
                        try:
                            alt_ticker = yf.Ticker(alt_symbol)
                            if start_date and end_date:
                                data = alt_ticker.history(start=start_date, end=end_date, interval=self.timeframe)
                            else:
                                data = alt_ticker.history(period=period, interval=self.timeframe)
                            
                            if not data.empty:
                                logger.info(f"Datos obtenidos con símbolo alternativo: {alt_symbol}")
                                break
                        except Exception as e:
                            logger.warning(f"Error con símbolo {alt_symbol}: {e}")
                            continue
            
            # Si aún no hay datos, crear datos sintéticos para pruebas
            if data.empty:
                logger.warning("No se pudieron obtener datos reales, creando datos sintéticos")
                return self._generate_synthetic_data(period)
            
            # Renombrar columnas al formato estándar
            data.columns = [col.lower().replace(' ', '_') for col in data.columns]
            
            # Agregar timestamp
            data['timestamp'] = data.index
            
            logger.info(f"Datos obtenidos: {len(data)} registros")
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de Yahoo Finance: {e}")
            logger.info("Creando datos sintéticos para pruebas")
            return self._generate_synthetic_data(period)
    
    def _generate_synthetic_data(self, period: str = "2y") -> pd.DataFrame:
        """
        Generar datos sintéticos de criptomonedas para pruebas
        
        Args:
            period: Período predefinido
            
        Returns:
            DataFrame con datos sintéticos OHLCV
        """
        logger.info(f"Generando datos sintéticos para período {period}")
        
        # Mapear períodos a días
        period_days = {
            "1d": 1, "5d": 5, "1mo": 30, "3mo": 90, 
            "6mo": 180, "1y": 365, "2y": 730, "5y": 1825, "max": 2555
        }
        
        days = period_days.get(period, 730)
        
        # Generar timestamps (hora a hora)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        timestamps = pd.date_range(start=start_date, end=end_date, freq='H')
        
        # Parámetros de simulación
        n_points = len(timestamps)
        initial_price = 50000  # Precio inicial de Bitcoin
        volatility = 0.02  # Volatilidad diaria
        trend = 0.0001  # Tendencia alcista suave
        
        # Generar camino de precios (modelo de caminata aleatoria con tendencia)
        returns = np.random.normal(trend, volatility, n_points)
        price_path = initial_price * np.exp(np.cumsum(returns))
        
        # Generar datos OHLCV
        data = pd.DataFrame({
            'timestamp': timestamps,
            'close': price_path
        })
        
        # Generar open, high, low basados en close
        data['open'] = data['close'].shift(1)
        data['open'] = data['open'].fillna(initial_price)
        
        # High y low con volatilidad intradía
        intraday_vol = 0.01
        data['high'] = data[['open', 'close']].max(axis=1) * (1 + np.random.uniform(0, intraday_vol, n_points))
        data['low'] = data[['open', 'close']].min(axis=1) * (1 - np.random.uniform(0, intraday_vol, n_points))
        
        # Volumen sintético (correlacionado con volatilidad)
        price_change = data['close'].pct_change().abs()
        data['volume'] = np.random.uniform(1000, 10000, n_points) * (1 + price_change * 100)
        data['volume'] = data['volume'].fillna(5000)
        
        # Reordenar columnas
        data = data[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        logger.info(f"Datos sintéticos generados: {len(data)} registros")
        return data
    
    def get_yahoo_data(self, 
                      start_date: str = None, 
                      end_date: str = None,
                      period: str = "2y") -> pd.DataFrame:
        """
        Obtener datos de Yahoo Finance
        
        Args:
            start_date: Fecha inicial (YYYY-MM-DD)
            end_date: Fecha final (YYYY-MM-DD)
            period: Período predefinido (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            
        Returns:
            DataFrame con datos OHLCV
        """
        logger.info(f"Obteniendo datos de Yahoo Finance para {self.symbol} período {period}")
        
        try:
            # Intentar con el símbolo original
            ticker = yf.Ticker(self.symbol)
            
            if start_date and end_date:
                data = ticker.history(start=start_date, end=end_date, interval=self.timeframe)
            else:
                data = ticker.history(period=period, interval=self.timeframe)
            
            # Si no hay datos, intentar con símbolos alternativos
            if data.empty:
                logger.warning(f"Sin datos para {self.symbol}, intentando alternativas")
                
                # Probar con símbolos alternativos
                alt_symbols = [self.symbol.replace('-', ''), f"{self.symbol}-USD", "BTC-USD"]
                
                for alt_symbol in alt_symbols:
                    if alt_symbol != self.symbol:
                        logger.info(f"Intentando con símbolo alternativo: {alt_symbol}")
                        try:
                            alt_ticker = yf.Ticker(alt_symbol)
                            if start_date and end_date:
                                data = alt_ticker.history(start=start_date, end=end_date, interval=self.timeframe)
                            else:
                                data = alt_ticker.history(period=period, interval=self.timeframe)
                            
                            if not data.empty:
                                logger.info(f"Datos obtenidos con símbolo alternativo: {alt_symbol}")
                                break
                        except Exception as e:
                            logger.warning(f"Error con símbolo {alt_symbol}: {e}")
                            continue
            
            # Si aún no hay datos, crear datos sintéticos para pruebas
            if data.empty:
                logger.warning("No se pudieron obtener datos reales, creando datos sintéticos")
                return self._generate_synthetic_data(period)
            
            # Renombrar columnas al formato estándar
            data.columns = [col.lower().replace(' ', '_') for col in data.columns]
            
            # Agregar timestamp
            data['timestamp'] = data.index
            
            logger.info(f"Datos obtenidos: {len(data)} registros")
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de Yahoo Finance: {e}")
            logger.info("Creando datos sintéticos para pruebas")
            return self._generate_synthetic_data(period)
    
    def get_binance_data(self, 
                        start_time: str = None,
                        limit: int = 1000,
                        days_back: int = 90) -> pd.DataFrame:
        """
        Obtener datos de Binance API con múltiples llamadas para obtener datos históricos
        
        Args:
            start_time: Tiempo inicial en milisegundos
            limit: Número de registros por llamada (máx 1000)
            days_back: Días hacia atrás para obtener datos
            
        Returns:
            DataFrame con datos OHLCV
        """
        logger.info(f"Obteniendo datos de Binance para {self.symbol} timeframe {self.timeframe}")
        
        try:
            # Convertir símbolo a formato Binance
            binance_symbol = self.symbol.replace('-', '').replace('USD', 'USDT')
            
            # Si no se especifica start_time, calcular para obtener datos de los últimos days_back días
            if start_time is None:
                end_time = datetime.now()
                start_time = end_time - timedelta(days=days_back)
                start_time_ms = int(start_time.timestamp() * 1000)
            else:
                start_time_ms = start_time
            
            all_data = []
            current_time = start_time_ms
            
            # Obtener datos en bloques de 1000 registros
            while True:
                logger.info(f"Obteniendo datos desde {pd.to_datetime(current_time, unit='ms')}")
                
                # Obtener datos
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=binance_symbol,
                    timeframe=self.timeframe,
                    since=current_time,
                    limit=limit
                )
                
                if not ohlcv:
                    break
                    
                all_data.extend(ohlcv)
                
                # Si obtenemos menos datos que el límite, hemos llegado al final
                if len(ohlcv) < limit:
                    break
                
                # El último timestamp + 1 hora para la siguiente iteración
                current_time = ohlcv[-1][0] + 3600000  # +1 hora en milisegundos
                
                # Limitar para no sobrecargar
                if len(all_data) >= days_back * 24:  # Máximo días*24 horas
                    break
            
            # Crear DataFrame
            df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Eliminar duplicados
            df = df.drop_duplicates(subset=['timestamp'])
            df = df.sort_values('timestamp')
            
            logger.info(f"Datos de Binance obtenidos: {len(df)} registros")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de Binance: {e}")
            # Crear datos sintéticos como fallback
            return self._generate_synthetic_data(f"{days_back}d")
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcular indicadores técnicos para enriquecer el dataset
        
        Args:
            df: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con indicadores adicionales
        """
        logger.info("Calculando indicadores técnicos")
        
        # RSI
        df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Bollinger Bands
        bollinger = ta.volatility.BollingerBands(df['close'])
        df['bb_high'] = bollinger.bollinger_hband()
        df['bb_low'] = bollinger.bollinger_lband()
        df['bb_mid'] = bollinger.bollinger_mavg()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        
        # Price changes
        df['price_change'] = df['close'].pct_change()
        df['price_change_24h'] = df['price_change'].rolling(window=24).sum()
        
        # Volatility
        df['volatility'] = df['price_change'].rolling(window=24).std()
        
        # ATR (Average True Range) - CRÍTICO PARA FILTROS DINÁMICOS
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'])
        df['atr'] = atr.average_true_range()
        df['atr_percent'] = (df['atr'] / df['close']) * 100  # ATR como porcentaje del precio
        
        # ATR móvil para tendencia de volatilidad
        df['atr_ma_14'] = df['atr'].rolling(window=14).mean()
        df['atr_ratio'] = df['atr'] / df['atr_ma_14']  # Ratio ATR actual vs media
        
        # Rangos dinámicos basados en ATR
        df['dynamic_support'] = df['close'] - (df['atr'] * 2)  # Soporte dinámico (-2 ATR)
        df['dynamic_resistance'] = df['close'] + (df['atr'] * 2)  # Resistencia dinámica (+2 ATR)
        
        # Filtros de volatilidad ATR
        df['low_volatility'] = df['atr_percent'] < df['atr_percent'].rolling(30).quantile(0.25)  # 25% inferior
        df['high_volatility'] = df['atr_percent'] > df['atr_percent'].rolling(30).quantile(0.75)  # 75% superior
        df['normal_volatility'] = ~(df['low_volatility'] | df['high_volatility'])
        
        # Señales de quiebre ATR
        df['atr_breakout_up'] = (df['close'] > df['dynamic_resistance']) & (df['volume'] > df['volume'].rolling(20).mean())
        df['atr_breakout_down'] = (df['close'] < df['dynamic_support']) & (df['volume'] > df['volume'].rolling(20).mean())
        
        logger.info(f"Indicadores calculados: {len(df.columns)} columnas (incluyendo ATR dinámico)")
        return df
    
    def create_patchtst_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Crear features compatibles con formato ETTh1 de PatchTST
        
        Args:
            df: DataFrame con datos OHLCV e indicadores
            
        Returns:
            DataFrame con features formateadas
        """
        logger.info("Creando features compatibles con PatchTST")
        
        # Mapear a formato ETTh1 (7 canales)
        patchtst_df = pd.DataFrame()
        patchtst_df['timestamp'] = df['timestamp']
        
        # Canal 1: High Upper FL (HUFL) - Precio alto normalizado
        scaler_high = MinMaxScaler()
        patchtst_df['HUFL'] = scaler_high.fit_transform(df[['high']])
        
        # Canal 2: High Upper LL (HULL) - Precio bajo normalizado  
        scaler_low = MinMaxScaler()
        patchtst_df['HULL'] = scaler_low.fit_transform(df[['low']])
        
        # Canal 3: Mid Upper FL (MUFL) - Precio de apertura normalizado
        scaler_open = MinMaxScaler()
        patchtst_df['MUFL'] = scaler_open.fit_transform(df[['open']])
        
        # Canal 4: Mid Upper LL (MULL) - Precio de cierre normalizado (TARGET)
        scaler_close = MinMaxScaler()
        patchtst_df['MULL'] = scaler_close.fit_transform(df[['close']])
        
        # Canal 5: Low Upper FL (LUFL) - Volumen normalizado
        scaler_volume = MinMaxScaler()
        patchtst_df['LUFL'] = scaler_volume.fit_transform(df[['volume']])
        
        # Canal 6: Low Upper LL (LULL) - Volatilidad normalizada
        scaler_vol = MinMaxScaler()
        patchtst_df['LULL'] = scaler_vol.fit_transform(df[['volatility']].fillna(0))
        
        # Canal 7: OT (Output Target) - Precio de cierre (mismo que MULL)
        patchtst_df['OT'] = patchtst_df['MULL']
        
        # Guardar scalers para uso futuro
        self.scalers = {
            'high': scaler_high,
            'low': scaler_low,
            'open': scaler_open,
            'close': scaler_close,
            'volume': scaler_volume,
            'volatility': scaler_vol
        }
        
        logger.info("Features creadas en formato ETTh1 compatible")
        return patchtst_df
    
    def prepare_training_data(self, 
                            days_back: int = 90,  # Reducido de 365 a 90 días para mejor adaptación
                            test_split: float = 0.2,
                            val_split: float = 0.1) -> Dict:
        """
        Preparar dataset completo para entrenamiento usando solo Binance
        
        Returns:
            Dict con datasets de train, validation y test
        """
        logger.info(f"Preparando dataset completo con {days_back} días de datos desde Binance")
        
        # Obtener datos de Binance únicamente
        df = self.get_binance_data(limit=1000)
        
        # Calcular indicadores
        df = self.calculate_technical_indicators(df)
        
        # Crear features PatchTST
        patchtst_df = self.create_patchtst_features(df)
        
        # Eliminar NaN
        patchtst_df = patchtst_df.dropna()
        
        logger.info(f"Dataset final: {len(patchtst_df)} registros")
        
        # Dividir en train/val/test
        n_samples = len(patchtst_df)
        n_test = int(n_samples * test_split)
        n_val = int(n_samples * val_split)
        n_train = n_samples - n_test - n_val
        
        train_data = patchtst_df.iloc[:n_train]
        val_data = patchtst_df.iloc[n_train:n_train + n_val]
        test_data = patchtst_df.iloc[n_train + n_val:]
        
        # Aplicar ponderación temporal exponencial solo a datos de entrenamiento
        # Esto da más peso a datos recientes sin contaminar validación/test
        train_data_weighted = self.apply_time_weighting(
            train_data, 
            half_life_days=30,  # 30 días de half-life para adaptación rápida
            target_columns=['HUFL', 'HULL', 'MUFL', 'MULL', 'LUFL', 'LULL']  # Solo features, no target
        )
        
        logger.info(f"Ponderación temporal aplicada: datos train={len(train_data)} → pesados={len(train_data_weighted)}")
        
        # Definir columnas de features y target
        feature_cols = ['HUFL', 'HULL', 'MUFL', 'LUFL', 'LULL']  # Excluir MULL y OT del target
        target_cols = ['MULL', 'OT']  # Target es el precio de cierre
        scalers = self.scalers if hasattr(self, 'scalers') else {}
        
        result = {
            'full_dataset': patchtst_df,
            'train': train_data_weighted,  # Usar datos ponderados temporalmente
            'train_original': train_data,   # Mantener datos originales para referencia
            'validation': val_data,
            'test': test_data,
            'feature_columns': feature_cols,
            'target_columns': target_cols,
            'scalers': scalers
        }
        
        return result
    
    def get_atr_analysis(self, data: pd.DataFrame, current_price: float = None) -> Dict:
        """
        Obtener análisis completo de ATR dinámico para filtros de sensibilidad
        
        Args:
            data: DataFrame con datos OHLCV
            current_price: Precio actual (opcional)
            
        Returns:
            Dict con análisis ATR completo
        """
        if data.empty:
            return {}
            
        if current_price is None:
            current_price = data['close'].iloc[-1]
        
        # Calcular ATR si no existe
        if 'atr' not in data.columns:
            atr = ta.volatility.AverageTrueRange(data['high'], data['low'], data['close'])
            data['atr'] = atr.average_true_range()
            data['atr_percent'] = (data['atr'] / data['close']) * 100
        
        # Estadísticas ATR actuales
        current_atr = data['atr'].iloc[-1]
        current_atr_percent = data['atr_percent'].iloc[-1]
        
        # Análisis histórico de ATR (últimos 30 días)
        atr_history = data['atr_percent'].tail(720)  # 720 horas = 30 días
        
        # Percentiles de volatilidad
        atr_percentiles = {
            'p10': atr_history.quantile(0.10),
            'p25': atr_history.quantile(0.25),
            'p50': atr_history.quantile(0.50),
            'p75': atr_history.quantile(0.75),
            'p90': atr_history.quantile(0.90)
        }
        
        # Clasificar volatilidad actual
        if current_atr_percent <= atr_percentiles['p25']:
            volatility_level = "LOW"
            volatility_factor = 1.2  # Mayor confianza en baja volatilidad
        elif current_atr_percent >= atr_percentiles['p75']:
            volatility_level = "HIGH"
            volatility_factor = 0.7  # Menor confianza en alta volatilidad
        else:
            volatility_level = "NORMAL"
            volatility_factor = 1.0  # Confianza normal
        
        # Rangos dinámicos de precio basados en ATR
        atr_multiplier = 2.0  # Multiplicador estándar
        dynamic_ranges = {
            'support_1atr': current_price - (current_atr * 1),
            'support_2atr': current_price - (current_atr * 2),
            'support_3atr': current_price - (current_atr * 3),
            'resistance_1atr': current_price + (current_atr * 1),
            'resistance_2atr': current_price + (current_atr * 2),
            'resistance_3atr': current_price + (current_atr * 3)
        }
        
        # Análisis de tendencia de volatilidad
        if len(data) >= 14:
            atr_ma_14 = data['atr'].rolling(window=14).mean().iloc[-1]
            atr_ratio = current_atr / atr_ma_14 if atr_ma_14 > 0 else 1.0
            
            if atr_ratio > 1.2:
                volatility_trend = "INCREASING"
            elif atr_ratio < 0.8:
                volatility_trend = "DECREASING"
            else:
                volatility_trend = "STABLE"
        else:
            atr_ratio = 1.0
            volatility_trend = "UNKNOWN"
        
        # Señales de breakout basadas en ATR
        recent_high = data['high'].tail(24).max()  # Máximo de últimas 24h
        recent_low = data['low'].tail(24).min()   # Mínimo de últimas 24h
        
        breakout_signals = {
            'high_breakout': recent_high > dynamic_ranges['resistance_1atr'],
            'low_breakout': recent_low < dynamic_ranges['support_1atr'],
            'high_breakout_2atr': recent_high > dynamic_ranges['resistance_2atr'],
            'low_breakout_2atr': recent_low < dynamic_ranges['support_2atr']
        }
        
        logger.info(f"ATR Analysis: {volatility_level} volatility ({current_atr_percent:.2f}%), factor: {volatility_factor}")
        
        return {
            'current_atr': float(current_atr),
            'current_atr_percent': float(current_atr_percent),
            'volatility_level': volatility_level,
            'volatility_factor': float(volatility_factor),
            'volatility_trend': volatility_trend,
            'atr_ratio': float(atr_ratio),
            'atr_percentiles': {k: float(v) for k, v in atr_percentiles.items()},
            'dynamic_ranges': {k: float(v) for k, v in dynamic_ranges.items()},
            'breakout_signals': breakout_signals,
            'timestamp': data.index[-1].isoformat() if hasattr(data.index[-1], 'isoformat') else str(data.index[-1])
        }
    
    def apply_time_weighting(self, data: pd.DataFrame, half_life_days: int = 30, target_columns: list = None) -> pd.DataFrame:
        """
        Aplicar ponderación temporal exponencial a los datos
        
        Args:
            data: DataFrame con datos históricos
            half_life_days: Días para el half-life del decaimiento exponencial
            target_columns: Columnas a ponderar (None = todas las numéricas)
            
        Returns:
            DataFrame con datos ponderados temporalmente
        """
        if len(data) < 10:  # Mínimo de datos
            return data
        
        # Crear copia para no modificar original
        weighted_data = data.copy()
        
        # Calcular pesos exponenciales
        # w_t = λ^(T-t) donde λ = 0.5^(1/half_life)
        lambda_factor = 0.5 ** (1 / (half_life_days * 24))  # Convertir a horas
        n_periods = len(data)
        weights = np.array([lambda_factor ** (n_periods - 1 - i) for i in range(n_periods)])
        
        # Normalizar pesos (el más reciente = 1)
        weights = weights / weights[-1]
        
        # Aplicar a columnas numéricas
        if target_columns is None:
            target_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in target_columns:
            if col in weighted_data.columns:
                weighted_data[col] = weighted_data[col] * weights
        
        # Agregar metadata de ponderación
        weighted_data.attrs['time_weights'] = weights
        weighted_data.attrs['half_life_days'] = half_life_days
        
        logger.info(f"Ponderación temporal aplicada: half_life={half_life_days}d, peso_max={weights[-1]:.3f}, peso_min={weights[0]:.3f}")
        return weighted_data
    
    def get_structural_levels(self, days_back: int = 365) -> Dict:
        """
        Obtener niveles estructurales de soporte/resistencia usando datos históricos largos
        
        Args:
            days_back: Días hacia atrás para análisis estructural (default: 365)
            
        Returns:
            Dict con niveles de soporte, resistencia y volatilidad estructural
        """
        logger.info(f"Obteniendo niveles estructurales con {days_back} días de datos")
        
        # Obtener datos históricos extendidos para análisis estructural
        df = self.get_binance_data(days_back=days_back)
        
        # Calcular niveles clave usando datos históricos completos
        max_price = df['high'].max()
        min_price = df['low'].min()
        current_price = df['close'].iloc[-1]
        
        # Niveles de soporte/resistencia usando pivots históricos
        support_levels = []
        resistance_levels = []
        
        # Identificar pivots significativos (mínimos/máximos locales)
        window = 20  # 20 períodos para identificar pivots
        for i in range(window, len(df) - window):
            # Mínimo local (soporte)
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                support_levels.append(df['low'].iloc[i])
            
            # Máximo local (resistencia)  
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                resistance_levels.append(df['high'].iloc[i])
        
        # Eliminar duplicados y ordenar
        support_levels = sorted(list(set(support_levels)))[-5:]  # Últimos 5 soportes
        resistance_levels = sorted(list(set(resistance_levels)))[:5]  # Primeros 5 resistencias
        
        # Volatilidad estructural
        structural_volatility = df['close'].pct_change().std() * np.sqrt(365)  # Anualizada
        
        result = {
            'max_price': max_price,
            'min_price': min_price,
            'current_price': current_price,
            'support_levels': support_levels,
            'resistance_levels': resistance_levels,
            'structural_volatility': structural_volatility,
            'price_range_pct': ((max_price - min_price) / min_price) * 100
        }
        
        logger.info(f"Niveles estructurales calculados: Soporte {support_levels}, Resistencia {resistance_levels}")
        return result
    
    def save_dataset(self, dataset: Dict, filepath: str):
        """Guardar dataset preparado"""
        import pickle
        
        with open(filepath, 'wb') as f:
            pickle.dump(dataset, f)
        
        logger.info(f"Dataset guardado en {filepath}")
    
    def load_dataset(self, filepath: str) -> Dict:
        """Cargar dataset preparado"""
        import pickle
        
        with open(filepath, 'rb') as f:
            dataset = pickle.load(f)
        
        logger.info(f"Dataset cargado desde {filepath}")
        return dataset

def create_sample_crypto_dataset():
    """Crear dataset de ejemplo para pruebas"""
    loader = CryptoDataLoader("BTC-USD", "1h")
    
    # Crear dataset con 180 días de datos
    dataset = loader.prepare_training_data(days_back=180)
    
    # Guardar dataset
    loader.save_dataset(dataset, "data/crypto_dataset_btc.pkl")
    
    print("📊 Dataset de criptomonedas creado exitosamente!")
    print(f"   Total de registros: {len(dataset['full_dataset'])}")
    print(f"   Features: {dataset['feature_columns']}")
    print(f"   Período: {dataset['full_dataset']['timestamp'].min()} a {dataset['full_dataset']['timestamp'].max()}")
    
    return dataset

if __name__ == '__main__':
    print("🚀 Creador de Dataset de Criptomonedas para PatchTST")
    print("="*60)
    
    try:
        dataset = create_sample_crypto_dataset()
        print("\n✅ Dataset creado y guardado exitosamente!")
        
        # Mostrar muestra de datos
        print("\n📋 Muestra de datos:")
        print(dataset['full_dataset'][['timestamp', 'HUFL', 'HULL', 'MULL', 'OT']].head())
        
    except Exception as e:
        print(f"\n❌ Error creando dataset: {e}")
        import traceback
        traceback.print_exc()