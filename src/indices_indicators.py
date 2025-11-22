"""
SICAR Indices Technical Indicators
Indicadores técnicos optimizados para trading de índices
Adaptados para timeframes horarios y diarios con detección de régimen de mercado
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Optional, Tuple, Union
import warnings
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suprimir warnings de pandas
warnings.filterwarnings('ignore')

@dataclass
class IndicatorResult:
    """Resultado de un indicador técnico"""
    name: str
    value: float
    signal: str  # 'BUY', 'SELL', 'NEUTRAL'
    strength: float  # 0-1
    timestamp: datetime
    timeframe: str

@dataclass
class MarketRegime:
    """Régimen de mercado detectado"""
    trend: str  # 'BULLISH', 'BEARISH', 'SIDEWAYS'
    volatility: str  # 'LOW', 'NORMAL', 'HIGH'
    momentum: str  # 'STRONG', 'WEAK', 'NEUTRAL'
    confidence: float  # 0-1

class IndicesIndicators:
    """
    Calculadora de indicadores técnicos para índices
    Optimizada para diferentes timeframes y características de índices
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.cache = {}
        
        # Parámetros por defecto optimizados para índices
        self.default_params = {
            # RSI
            'rsi_period': 21,
            'rsi_oversold': 32,
            'rsi_overbought': 68,
            
            # EMAs
            'ema_fast': 12,
            'ema_slow': 26,
            'ema_signal': 9,
            'ema_trend': 50,
            
            # ATR
            'atr_period': 21,
            'atr_multiplier': 2.5,
            
            # Volume
            'volume_period': 20,
            'volume_threshold': 1.5,
            
            # MACD
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            
            # Bollinger Bands
            'bb_period': 20,
            'bb_std': 2.0,
            
            # Stochastic
            'stoch_k': 14,
            'stoch_d': 3,
            
            # Williams %R
            'williams_period': 14
        }
        
        # Actualizar con configuración personalizada
        self.params = {**self.default_params, **self.config}
    
    def calculate_all_indicators(self, data: pd.DataFrame, 
                               symbol: str = 'SPY',
                               timeframe: str = '1h') -> Dict[str, pd.Series]:
        """
        Calcula todos los indicadores técnicos para un dataset
        
        Args:
            data: DataFrame con datos OHLCV
            symbol: Símbolo del índice
            timeframe: Timeframe de los datos
        
        Returns:
            Diccionario con todos los indicadores calculados
        """
        
        if data.empty or len(data) < 50:
            logger.warning(f"Datos insuficientes para calcular indicadores: {len(data)} registros")
            return {}
        
        indicators = {}
        
        try:
            # Indicadores de momentum
            indicators.update(self._calculate_momentum_indicators(data))
            
            # Indicadores de tendencia
            indicators.update(self._calculate_trend_indicators(data))
            
            # Indicadores de volatilidad
            indicators.update(self._calculate_volatility_indicators(data))
            
            # Indicadores de volumen
            indicators.update(self._calculate_volume_indicators(data))
            
            # Indicadores específicos para índices
            indicators.update(self._calculate_indices_specific_indicators(data, symbol, timeframe))
            
            # Detección de régimen de mercado
            indicators['market_regime'] = self._detect_market_regime(data, indicators)
            
            logger.info(f"Calculados {len(indicators)} indicadores para {symbol}")
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {str(e)}")
            return {}
        
        return indicators
    
    def _calculate_momentum_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calcula indicadores de momentum"""
        
        indicators = {}
        
        try:
            # RSI
            indicators['rsi'] = talib.RSI(data['close'], timeperiod=self.params['rsi_period'])
            
            # RSI adaptativo (más sensible para timeframes cortos)
            if len(data) > 100:
                rsi_fast = talib.RSI(data['close'], timeperiod=max(7, self.params['rsi_period'] // 2))
                rsi_slow = talib.RSI(data['close'], timeperiod=self.params['rsi_period'] * 2)
                indicators['rsi_adaptive'] = (rsi_fast + indicators['rsi'] + rsi_slow) / 3
            
            # Stochastic
            stoch_k, stoch_d = talib.STOCH(
                data['high'], data['low'], data['close'],
                fastk_period=self.params['stoch_k'],
                slowk_period=self.params['stoch_d'],
                slowd_period=self.params['stoch_d']
            )
            indicators['stoch_k'] = stoch_k
            indicators['stoch_d'] = stoch_d
            
            # Williams %R
            indicators['williams_r'] = talib.WILLR(
                data['high'], data['low'], data['close'],
                timeperiod=self.params['williams_period']
            )
            
            # ROC (Rate of Change)
            indicators['roc'] = talib.ROC(data['close'], timeperiod=10)
            indicators['roc_long'] = talib.ROC(data['close'], timeperiod=21)
            
            # CCI (Commodity Channel Index)
            indicators['cci'] = talib.CCI(data['high'], data['low'], data['close'], timeperiod=20)
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de momentum: {str(e)}")
        
        return indicators
    
    def _calculate_trend_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calcula indicadores de tendencia"""
        
        indicators = {}
        
        try:
            # EMAs
            indicators['ema_fast'] = talib.EMA(data['close'], timeperiod=self.params['ema_fast'])
            indicators['ema_slow'] = talib.EMA(data['close'], timeperiod=self.params['ema_slow'])
            indicators['ema_trend'] = talib.EMA(data['close'], timeperiod=self.params['ema_trend'])
            
            # SMA para comparación
            indicators['sma_20'] = talib.SMA(data['close'], timeperiod=20)
            indicators['sma_50'] = talib.SMA(data['close'], timeperiod=50)
            indicators['sma_200'] = talib.SMA(data['close'], timeperiod=200)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(
                data['close'],
                fastperiod=self.params['macd_fast'],
                slowperiod=self.params['macd_slow'],
                signalperiod=self.params['macd_signal']
            )
            indicators['macd'] = macd
            indicators['macd_signal'] = macd_signal
            indicators['macd_histogram'] = macd_hist
            
            # ADX (Average Directional Index)
            indicators['adx'] = talib.ADX(data['high'], data['low'], data['close'], timeperiod=14)
            indicators['plus_di'] = talib.PLUS_DI(data['high'], data['low'], data['close'], timeperiod=14)
            indicators['minus_di'] = talib.MINUS_DI(data['high'], data['low'], data['close'], timeperiod=14)
            
            # Parabolic SAR
            indicators['sar'] = talib.SAR(data['high'], data['low'], acceleration=0.02, maximum=0.2)
            
            # Aroon
            aroon_down, aroon_up = talib.AROON(data['high'], data['low'], timeperiod=14)
            indicators['aroon_up'] = aroon_up
            indicators['aroon_down'] = aroon_down
            indicators['aroon_oscillator'] = aroon_up - aroon_down
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de tendencia: {str(e)}")
        
        return indicators
    
    def _calculate_volatility_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calcula indicadores de volatilidad"""
        
        indicators = {}
        
        try:
            # ATR
            indicators['atr'] = talib.ATR(data['high'], data['low'], data['close'], 
                                        timeperiod=self.params['atr_period'])
            
            # ATR normalizado (como % del precio)
            indicators['atr_percent'] = (indicators['atr'] / data['close']) * 100
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(
                data['close'],
                timeperiod=self.params['bb_period'],
                nbdevup=self.params['bb_std'],
                nbdevdn=self.params['bb_std']
            )
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower
            indicators['bb_width'] = (bb_upper - bb_lower) / bb_middle
            indicators['bb_position'] = (data['close'] - bb_lower) / (bb_upper - bb_lower)
            
            # Keltner Channels
            kc_middle = talib.EMA(data['close'], timeperiod=20)
            kc_atr = talib.ATR(data['high'], data['low'], data['close'], timeperiod=20)
            indicators['kc_upper'] = kc_middle + (kc_atr * 2)
            indicators['kc_lower'] = kc_middle - (kc_atr * 2)
            indicators['kc_middle'] = kc_middle
            
            # Volatilidad histórica
            returns = data['close'].pct_change()
            indicators['historical_volatility'] = returns.rolling(window=20).std() * np.sqrt(252) * 100
            
            # True Range
            indicators['true_range'] = talib.TRANGE(data['high'], data['low'], data['close'])
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de volatilidad: {str(e)}")
        
        return indicators
    
    def _calculate_volume_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calcula indicadores de volumen"""
        
        indicators = {}
        
        try:
            if 'volume' not in data.columns or data['volume'].isna().all():
                logger.warning("Datos de volumen no disponibles")
                return indicators
            
            # Volume SMA
            indicators['volume_sma'] = talib.SMA(data['volume'], timeperiod=self.params['volume_period'])
            
            # Volume ratio
            indicators['volume_ratio'] = data['volume'] / indicators['volume_sma']
            
            # OBV (On Balance Volume)
            indicators['obv'] = talib.OBV(data['close'], data['volume'])
            
            # Volume Price Trend
            indicators['vpt'] = talib.AD(data['high'], data['low'], data['close'], data['volume'])
            
            # Money Flow Index
            indicators['mfi'] = talib.MFI(data['high'], data['low'], data['close'], data['volume'], timeperiod=14)
            
            # Chaikin Money Flow
            mfv = ((data['close'] - data['low']) - (data['high'] - data['close'])) / (data['high'] - data['low'])
            mfv = mfv.fillna(0) * data['volume']
            indicators['cmf'] = mfv.rolling(window=20).sum() / data['volume'].rolling(window=20).sum()
            
            # Volume Weighted Average Price (VWAP) - aproximación
            typical_price = (data['high'] + data['low'] + data['close']) / 3
            vwap_num = (typical_price * data['volume']).rolling(window=20).sum()
            vwap_den = data['volume'].rolling(window=20).sum()
            indicators['vwap'] = vwap_num / vwap_den
            
        except Exception as e:
            logger.error(f"Error calculando indicadores de volumen: {str(e)}")
        
        return indicators
    
    def _calculate_indices_specific_indicators(self, data: pd.DataFrame, 
                                             symbol: str, timeframe: str) -> Dict[str, pd.Series]:
        """Calcula indicadores específicos para índices"""
        
        indicators = {}
        
        try:
            # Momentum de índices (comparación con SMA)
            sma_50 = talib.SMA(data['close'], timeperiod=50)
            indicators['index_momentum'] = (data['close'] / sma_50 - 1) * 100
            
            # Fuerza relativa del índice
            returns = data['close'].pct_change()
            indicators['relative_strength'] = returns.rolling(window=20).mean() / returns.rolling(window=20).std()
            
            # Índice de amplitud (simulado con volatilidad)
            high_low_ratio = (data['high'] - data['low']) / data['close']
            indicators['breadth_index'] = high_low_ratio.rolling(window=10).mean()
            
            # Indicador de sesión (para timeframes intraday)
            if timeframe in ['1m', '5m', '15m', '30m', '1h']:
                indicators['session_indicator'] = self._calculate_session_indicator(data)
            
            # Indicador de fin de semana (para timeframes diarios)
            if timeframe in ['1d']:
                indicators['weekend_effect'] = self._calculate_weekend_effect(data)
            
            # Momentum específico por símbolo
            if symbol == 'QQQ':  # Tech momentum
                indicators['tech_momentum'] = self._calculate_tech_momentum(data)
            elif symbol == 'IWM':  # Small cap momentum
                indicators['small_cap_momentum'] = self._calculate_small_cap_momentum(data)
            elif symbol == 'DIA':  # Value momentum
                indicators['value_momentum'] = self._calculate_value_momentum(data)
            
        except Exception as e:
            logger.error(f"Error calculando indicadores específicos: {str(e)}")
        
        return indicators
    
    def _calculate_session_indicator(self, data: pd.DataFrame) -> pd.Series:
        """Calcula indicador de sesión para timeframes intraday"""
        
        try:
            # Simular sesiones basado en el índice temporal
            session_indicator = pd.Series(index=data.index, dtype=float)
            
            for i, timestamp in enumerate(data.index):
                hour = timestamp.hour
                
                if 4 <= hour < 9:  # Pre-market
                    session_indicator.iloc[i] = 0.3
                elif 9 <= hour < 16:  # Regular hours
                    session_indicator.iloc[i] = 1.0
                elif 16 <= hour < 20:  # After hours
                    session_indicator.iloc[i] = 0.5
                else:  # Closed
                    session_indicator.iloc[i] = 0.1
            
            return session_indicator
            
        except Exception as e:
            logger.error(f"Error calculando indicador de sesión: {str(e)}")
            return pd.Series(index=data.index, dtype=float)
    
    def _calculate_weekend_effect(self, data: pd.DataFrame) -> pd.Series:
        """Calcula efecto de fin de semana"""
        
        try:
            weekend_effect = pd.Series(index=data.index, dtype=float)
            
            for i, timestamp in enumerate(data.index):
                weekday = timestamp.weekday()
                
                if weekday == 0:  # Lunes
                    weekend_effect.iloc[i] = 1.2  # Efecto post-weekend
                elif weekday == 4:  # Viernes
                    weekend_effect.iloc[i] = 0.8  # Efecto pre-weekend
                else:
                    weekend_effect.iloc[i] = 1.0
            
            return weekend_effect
            
        except Exception as e:
            logger.error(f"Error calculando efecto de fin de semana: {str(e)}")
            return pd.Series(index=data.index, dtype=float)
    
    def _calculate_tech_momentum(self, data: pd.DataFrame) -> pd.Series:
        """Momentum específico para QQQ (tech)"""
        
        try:
            # Momentum más sensible para tech
            fast_ema = talib.EMA(data['close'], timeperiod=8)
            slow_ema = talib.EMA(data['close'], timeperiod=21)
            tech_momentum = (fast_ema / slow_ema - 1) * 100
            
            return tech_momentum
            
        except Exception as e:
            logger.error(f"Error calculando tech momentum: {str(e)}")
            return pd.Series(index=data.index, dtype=float)
    
    def _calculate_small_cap_momentum(self, data: pd.DataFrame) -> pd.Series:
        """Momentum específico para IWM (small caps)"""
        
        try:
            # Momentum más volátil para small caps
            roc_short = talib.ROC(data['close'], timeperiod=5)
            roc_medium = talib.ROC(data['close'], timeperiod=15)
            small_cap_momentum = (roc_short + roc_medium) / 2
            
            return small_cap_momentum
            
        except Exception as e:
            logger.error(f"Error calculando small cap momentum: {str(e)}")
            return pd.Series(index=data.index, dtype=float)
    
    def _calculate_value_momentum(self, data: pd.DataFrame) -> pd.Series:
        """Momentum específico para DIA (value)"""
        
        try:
            # Momentum más estable para value
            sma_short = talib.SMA(data['close'], timeperiod=10)
            sma_long = talib.SMA(data['close'], timeperiod=30)
            value_momentum = (sma_short / sma_long - 1) * 100
            
            return value_momentum
            
        except Exception as e:
            logger.error(f"Error calculando value momentum: {str(e)}")
            return pd.Series(index=data.index, dtype=float)
    
    def _detect_market_regime(self, data: pd.DataFrame, indicators: Dict) -> pd.Series:
        """Detecta el régimen de mercado actual"""
        
        try:
            regime_series = pd.Series(index=data.index, dtype=object)
            
            for i in range(len(data)):
                if i < 50:  # Datos insuficientes
                    regime_series.iloc[i] = MarketRegime('NEUTRAL', 'NORMAL', 'NEUTRAL', 0.5)
                    continue
                
                # Detectar tendencia
                if 'ema_fast' in indicators and 'ema_slow' in indicators:
                    ema_fast = indicators['ema_fast'].iloc[i]
                    ema_slow = indicators['ema_slow'].iloc[i]
                    
                    if pd.notna(ema_fast) and pd.notna(ema_slow):
                        if ema_fast > ema_slow * 1.02:
                            trend = 'BULLISH'
                        elif ema_fast < ema_slow * 0.98:
                            trend = 'BEARISH'
                        else:
                            trend = 'SIDEWAYS'
                    else:
                        trend = 'NEUTRAL'
                else:
                    trend = 'NEUTRAL'
                
                # Detectar volatilidad
                if 'atr_percent' in indicators:
                    atr_pct = indicators['atr_percent'].iloc[i]
                    
                    if pd.notna(atr_pct):
                        if atr_pct > 2.5:
                            volatility = 'HIGH'
                        elif atr_pct < 1.0:
                            volatility = 'LOW'
                        else:
                            volatility = 'NORMAL'
                    else:
                        volatility = 'NORMAL'
                else:
                    volatility = 'NORMAL'
                
                # Detectar momentum
                if 'rsi' in indicators:
                    rsi = indicators['rsi'].iloc[i]
                    
                    if pd.notna(rsi):
                        if rsi > 60:
                            momentum = 'STRONG'
                        elif rsi < 40:
                            momentum = 'WEAK'
                        else:
                            momentum = 'NEUTRAL'
                    else:
                        momentum = 'NEUTRAL'
                else:
                    momentum = 'NEUTRAL'
                
                # Calcular confianza
                confidence = 0.7  # Base
                if 'adx' in indicators and pd.notna(indicators['adx'].iloc[i]):
                    adx = indicators['adx'].iloc[i]
                    confidence = min(1.0, adx / 50)
                
                regime = MarketRegime(trend, volatility, momentum, confidence)
                regime_series.iloc[i] = regime
            
            return regime_series
            
        except Exception as e:
            logger.error(f"Error detectando régimen de mercado: {str(e)}")
            return pd.Series(index=data.index, dtype=object)
    
    def get_signal_strength(self, indicators: Dict, index: int) -> Dict[str, float]:
        """
        Calcula la fuerza de las señales basada en múltiples indicadores
        
        Returns:
            Dict con fuerza de señales (0-1) para BUY/SELL
        """
        
        try:
            buy_signals = []
            sell_signals = []
            
            # RSI signals
            if 'rsi' in indicators and index < len(indicators['rsi']):
                rsi = indicators['rsi'].iloc[index]
                if pd.notna(rsi):
                    if rsi < self.params['rsi_oversold']:
                        buy_signals.append((100 - rsi) / 100)
                    elif rsi > self.params['rsi_overbought']:
                        sell_signals.append((rsi - 50) / 50)
            
            # MACD signals
            if all(k in indicators for k in ['macd', 'macd_signal']) and index < len(indicators['macd']):
                macd = indicators['macd'].iloc[index]
                macd_signal = indicators['macd_signal'].iloc[index]
                
                if pd.notna(macd) and pd.notna(macd_signal):
                    if macd > macd_signal:
                        buy_signals.append(0.6)
                    else:
                        sell_signals.append(0.6)
            
            # EMA signals
            if all(k in indicators for k in ['ema_fast', 'ema_slow']) and index < len(indicators['ema_fast']):
                ema_fast = indicators['ema_fast'].iloc[index]
                ema_slow = indicators['ema_slow'].iloc[index]
                
                if pd.notna(ema_fast) and pd.notna(ema_slow):
                    if ema_fast > ema_slow:
                        buy_signals.append(0.7)
                    else:
                        sell_signals.append(0.7)
            
            # Calcular fuerza promedio
            buy_strength = np.mean(buy_signals) if buy_signals else 0.0
            sell_strength = np.mean(sell_signals) if sell_signals else 0.0
            
            return {
                'buy_strength': buy_strength,
                'sell_strength': sell_strength,
                'net_strength': buy_strength - sell_strength
            }
            
        except Exception as e:
            logger.error(f"Error calculando fuerza de señales: {str(e)}")
            return {'buy_strength': 0.0, 'sell_strength': 0.0, 'net_strength': 0.0}

def create_indices_indicators(config: Dict = None) -> IndicesIndicators:
    """
    Crea una instancia configurada del calculador de indicadores
    
    Args:
        config: Configuración personalizada
    
    Returns:
        Instancia de IndicesIndicators
    """
    
    return IndicesIndicators(config)

if __name__ == "__main__":
    # Ejemplo de uso
    import yfinance as yf
    
    # Obtener datos de prueba
    spy = yf.Ticker('SPY')
    data = spy.history(period='3mo', interval='1h')
    
    # Crear calculador de indicadores
    calculator = create_indices_indicators()
    
    # Calcular indicadores
    indicators = calculator.calculate_all_indicators(data, 'SPY', '1h')
    
    print(f"Indicadores calculados: {list(indicators.keys())}")
    
    # Mostrar últimos valores
    for name, series in indicators.items():
        if isinstance(series, pd.Series) and not series.empty:
            last_value = series.iloc[-1]
            if pd.notna(last_value):
                print(f"{name}: {last_value}")
    
    # Obtener fuerza de señales
    signal_strength = calculator.get_signal_strength(indicators, -1)
    print(f"Fuerza de señales: {signal_strength}")