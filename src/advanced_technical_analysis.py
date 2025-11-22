"""
Módulo de Análisis Técnico Avanzado
Incluye múltiples timeframes, indicadores técnicos y cálculo preciso de soportes/resistencias
"""

import pandas as pd
import numpy as np
import talib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

class AdvancedTechnicalAnalysis:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.timeframes = ['1h', '4h', '1d']
        self.binance_base_url = "https://api.binance.com/api/v3"
        
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """
        Obtiene datos de velas de Binance para un símbolo y timeframe específico
        """
        try:
            url = f"{self.binance_base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos de datos
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            df.set_index('timestamp', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos de {symbol} {interval}: {e}")
            return pd.DataFrame()
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula el RSI (Relative Strength Index)"""
        return talib.RSI(prices.values, timeperiod=period)
    
    def calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calcula MACD, señal y histograma"""
        macd, signal, histogram = talib.MACD(prices.values)
        return {
            'macd': pd.Series(macd, index=prices.index),
            'signal': pd.Series(signal, index=prices.index),
            'histogram': pd.Series(histogram, index=prices.index)
        }
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calcula las Bandas de Bollinger"""
        upper, middle, lower = talib.BBANDS(prices.values, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        return {
            'upper': pd.Series(upper, index=prices.index),
            'middle': pd.Series(middle, index=prices.index),
            'lower': pd.Series(lower, index=prices.index)
        }
    
    def calculate_support_resistance(self, df: pd.DataFrame, window: int = 20) -> Dict[str, List[float]]:
        """
        Calcula niveles de soporte y resistencia con mayor precisión
        Utiliza pivots y clustering de precios
        """
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        # Encontrar pivots altos y bajos
        pivot_highs = []
        pivot_lows = []
        
        for i in range(window, len(highs) - window):
            # Pivot alto: máximo local
            if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
               all(highs[i] >= highs[i+j] for j in range(1, window+1)):
                pivot_highs.append(highs[i])
            
            # Pivot bajo: mínimo local
            if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
               all(lows[i] <= lows[i+j] for j in range(1, window+1)):
                pivot_lows.append(lows[i])
        
        # Clustering de niveles similares
        def cluster_levels(levels: List[float], tolerance: float = 0.01) -> List[float]:
            if not levels:
                return []
            
            levels = sorted(levels)
            clusters = []
            current_cluster = [levels[0]]
            
            for level in levels[1:]:
                if abs(level - current_cluster[-1]) / current_cluster[-1] <= tolerance:
                    current_cluster.append(level)
                else:
                    clusters.append(np.mean(current_cluster))
                    current_cluster = [level]
            
            clusters.append(np.mean(current_cluster))
            return clusters
        
        # Obtener niveles de soporte y resistencia más significativos
        resistance_levels = cluster_levels(pivot_highs)[-5:]  # Top 5 resistencias
        support_levels = cluster_levels(pivot_lows)[-5:]      # Top 5 soportes
        
        return {
            'resistance': sorted(resistance_levels, reverse=True),
            'support': sorted(support_levels, reverse=True)
        }
    
    def calculate_volatility(self, prices: pd.Series, period: int = 20) -> float:
        """Calcula la volatilidad histórica"""
        returns = prices.pct_change().dropna()
        return returns.rolling(window=period).std().iloc[-1] * np.sqrt(365) * 100
    
    def analyze_momentum(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analiza el momentum del precio"""
        closes = df['close']
        
        # Rate of Change (ROC)
        roc_5 = ((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6]) * 100
        roc_10 = ((closes.iloc[-1] - closes.iloc[-11]) / closes.iloc[-11]) * 100
        
        # Momentum
        momentum = closes.iloc[-1] - closes.iloc[-11]
        
        # Williams %R
        high_14 = df['high'].rolling(window=14).max().iloc[-1]
        low_14 = df['low'].rolling(window=14).min().iloc[-1]
        williams_r = ((high_14 - closes.iloc[-1]) / (high_14 - low_14)) * -100
        
        return {
            'roc_5': roc_5,
            'roc_10': roc_10,
            'momentum': momentum,
            'williams_r': williams_r
        }
    
    def get_comprehensive_analysis(self, symbol: str) -> Dict[str, any]:
        """
        Realiza un análisis técnico completo en múltiples timeframes
        """
        analysis_result = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'timeframes': {},
            'overall_signal': 'NEUTRAL',
            'confidence': 0.0,
            'risk_level': 'MEDIUM'
        }
        
        signals = []
        confidences = []
        
        for timeframe in self.timeframes:
            try:
                # Obtener datos
                df = self.get_klines(symbol, timeframe, 100)
                if df.empty:
                    continue
                
                closes = df['close']
                current_price = closes.iloc[-1]
                
                # Calcular indicadores
                rsi = self.calculate_rsi(closes)
                macd_data = self.calculate_macd(closes)
                bb_data = self.calculate_bollinger_bands(closes)
                sr_levels = self.calculate_support_resistance(df)
                volatility = self.calculate_volatility(closes)
                momentum = self.analyze_momentum(df)
                
                # Análisis de tendencia
                sma_20 = talib.SMA(closes.values, timeperiod=20)
                sma_50 = talib.SMA(closes.values, timeperiod=50)
                ema_12 = talib.EMA(closes.values, timeperiod=12)
                ema_26 = talib.EMA(closes.values, timeperiod=26)
                
                # Determinar señal para este timeframe
                tf_signal, tf_confidence = self._analyze_timeframe_signal(
                    current_price, rsi[-1], macd_data, bb_data, 
                    sr_levels, momentum, sma_20[-1], sma_50[-1],
                    ema_12[-1], ema_26[-1]
                )
                
                # Guardar análisis del timeframe
                analysis_result['timeframes'][timeframe] = {
                    'signal': tf_signal,
                    'confidence': tf_confidence,
                    'current_price': current_price,
                    'rsi': rsi[-1],
                    'macd': {
                        'macd': macd_data['macd'].iloc[-1],
                        'signal': macd_data['signal'].iloc[-1],
                        'histogram': macd_data['histogram'].iloc[-1]
                    },
                    'bollinger': {
                        'upper': bb_data['upper'].iloc[-1],
                        'middle': bb_data['middle'].iloc[-1],
                        'lower': bb_data['lower'].iloc[-1],
                        'position': self._get_bb_position(current_price, bb_data)
                    },
                    'support_resistance': sr_levels,
                    'volatility': volatility,
                    'momentum': momentum,
                    'trend': {
                        'sma_20': sma_20[-1],
                        'sma_50': sma_50[-1],
                        'ema_12': ema_12[-1],
                        'ema_26': ema_26[-1],
                        'trend_direction': 'BULLISH' if ema_12[-1] > ema_26[-1] else 'BEARISH'
                    }
                }
                
                signals.append(tf_signal)
                confidences.append(tf_confidence)
                
            except Exception as e:
                self.logger.error(f"Error analizando {symbol} en {timeframe}: {e}")
                continue
        
        # Determinar señal general
        if signals:
            # Ponderar por timeframe (1d > 4h > 1h)
            weights = {'1h': 1, '4h': 2, '1d': 3}
            weighted_signals = []
            weighted_confidences = []
            
            for i, tf in enumerate(self.timeframes[:len(signals)]):
                weight = weights.get(tf, 1)
                if signals[i] == 'BUY':
                    weighted_signals.extend([1] * weight)
                elif signals[i] == 'SELL':
                    weighted_signals.extend([-1] * weight)
                else:
                    weighted_signals.extend([0] * weight)
                
                weighted_confidences.extend([confidences[i]] * weight)
            
            avg_signal = np.mean(weighted_signals)
            avg_confidence = np.mean(weighted_confidences)
            
            if avg_signal > 0.3:
                analysis_result['overall_signal'] = 'BUY'
            elif avg_signal < -0.3:
                analysis_result['overall_signal'] = 'SELL'
            else:
                analysis_result['overall_signal'] = 'NEUTRAL'
            
            analysis_result['confidence'] = min(avg_confidence, 100.0)
            
            # Determinar nivel de riesgo basado en volatilidad y confirmaciones
            volatilities = [tf_data.get('volatility', 0) for tf_data in analysis_result['timeframes'].values()]
            avg_volatility = np.mean(volatilities) if volatilities else 0
            
            confirmations = sum(1 for signal in signals if signal == analysis_result['overall_signal'])
            total_timeframes = len(signals)
            
            if avg_volatility > 50 or confirmations < total_timeframes * 0.6:
                analysis_result['risk_level'] = 'HIGH'
            elif avg_volatility < 25 and confirmations >= total_timeframes * 0.8:
                analysis_result['risk_level'] = 'LOW'
            else:
                analysis_result['risk_level'] = 'MEDIUM'
        
        return analysis_result
    
    def _analyze_timeframe_signal(self, price: float, rsi: float, macd_data: Dict, 
                                bb_data: Dict, sr_levels: Dict, momentum: Dict,
                                sma_20: float, sma_50: float, ema_12: float, ema_26: float) -> Tuple[str, float]:
        """Analiza la señal para un timeframe específico"""
        
        signals = []
        
        # RSI
        if rsi < 30:
            signals.append(('BUY', 70))
        elif rsi > 70:
            signals.append(('SELL', 70))
        elif 30 <= rsi <= 45:
            signals.append(('BUY', 40))
        elif 55 <= rsi <= 70:
            signals.append(('SELL', 40))
        
        # MACD
        macd_val = macd_data['macd'].iloc[-1]
        signal_val = macd_data['signal'].iloc[-1]
        histogram = macd_data['histogram'].iloc[-1]
        
        if macd_val > signal_val and histogram > 0:
            signals.append(('BUY', 60))
        elif macd_val < signal_val and histogram < 0:
            signals.append(('SELL', 60))
        
        # Bollinger Bands
        bb_upper = bb_data['upper'].iloc[-1]
        bb_lower = bb_data['lower'].iloc[-1]
        bb_middle = bb_data['middle'].iloc[-1]
        
        if price <= bb_lower:
            signals.append(('BUY', 65))
        elif price >= bb_upper:
            signals.append(('SELL', 65))
        
        # Soporte y Resistencia
        if sr_levels['support']:
            nearest_support = min(sr_levels['support'], key=lambda x: abs(x - price))
            if abs(price - nearest_support) / price < 0.02:  # Cerca del soporte
                signals.append(('BUY', 55))
        
        if sr_levels['resistance']:
            nearest_resistance = min(sr_levels['resistance'], key=lambda x: abs(x - price))
            if abs(price - nearest_resistance) / price < 0.02:  # Cerca de la resistencia
                signals.append(('SELL', 55))
        
        # Tendencia (EMAs)
        if ema_12 > ema_26 and price > sma_20 > sma_50:
            signals.append(('BUY', 50))
        elif ema_12 < ema_26 and price < sma_20 < sma_50:
            signals.append(('SELL', 50))
        
        # Momentum
        if momentum['roc_5'] > 2 and momentum['williams_r'] < -20:
            signals.append(('BUY', 45))
        elif momentum['roc_5'] < -2 and momentum['williams_r'] > -80:
            signals.append(('SELL', 45))
        
        # Determinar señal final
        if not signals:
            return 'NEUTRAL', 0.0
        
        buy_signals = [conf for signal, conf in signals if signal == 'BUY']
        sell_signals = [conf for signal, conf in signals if signal == 'SELL']
        
        buy_strength = sum(buy_signals)
        sell_strength = sum(sell_signals)
        
        if buy_strength > sell_strength and buy_strength > 100:
            return 'BUY', min(buy_strength / len(buy_signals), 100.0)
        elif sell_strength > buy_strength and sell_strength > 100:
            return 'SELL', min(sell_strength / len(sell_signals), 100.0)
        else:
            return 'NEUTRAL', max(buy_strength, sell_strength) / max(len(signals), 1)
    
    def _get_bb_position(self, price: float, bb_data: Dict) -> str:
        """Determina la posición del precio respecto a las Bandas de Bollinger"""
        upper = bb_data['upper'].iloc[-1]
        lower = bb_data['lower'].iloc[-1]
        middle = bb_data['middle'].iloc[-1]
        
        if price >= upper:
            return 'ABOVE_UPPER'
        elif price <= lower:
            return 'BELOW_LOWER'
        elif price > middle:
            return 'ABOVE_MIDDLE'
        else:
            return 'BELOW_MIDDLE'

# Función de prueba
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    analyzer = AdvancedTechnicalAnalysis()
    
    # Probar con BTCUSDT
    print("Analizando BTCUSDT...")
    result = analyzer.get_comprehensive_analysis('BTCUSDT')
    
    print(f"\nResultado del análisis:")
    print(f"Símbolo: {result['symbol']}")
    print(f"Señal general: {result['overall_signal']}")
    print(f"Confianza: {result['confidence']:.2f}%")
    print(f"Nivel de riesgo: {result['risk_level']}")
    
    print(f"\nAnálisis por timeframes:")
    for tf, data in result['timeframes'].items():
        print(f"{tf}: {data['signal']} (Confianza: {data['confidence']:.2f}%)")