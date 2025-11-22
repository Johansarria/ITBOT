"""
Módulo de Confirmaciones de Señales
Incluye verificación de volumen, confirmación en múltiples timeframes y momentum
"""

import pandas as pd
import numpy as np
import requests
import talib
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

class SignalConfirmations:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.binance_base_url = "https://api.binance.com/api/v3"
        self.timeframes = ['1h', '4h', '1d']
        
        # Configuración de confirmaciones
        self.config = {
            'volume_multiplier': 2.0,      # Volumen 2x superior al promedio
            'min_timeframe_confirmations': 2,  # Mínimo 2 timeframes confirmando
            'momentum_threshold': 0.6,     # Umbral de momentum
            'volume_lookback': 20,         # Períodos para calcular volumen promedio
            'momentum_lookback': 14,       # Períodos para calcular momentum
            'price_action_threshold': 0.5, # Umbral para acción del precio
            'trend_strength_min': 0.6      # Fuerza mínima de tendencia
        }
    
    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """Obtiene datos de velas de Binance"""
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
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            df.set_index('timestamp', inplace=True)
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos de {symbol} {interval}: {e}")
            return pd.DataFrame()
    
    def check_volume_confirmation(self, symbol: str, timeframe: str = '1h') -> Dict[str, any]:
        """
        Verifica si el volumen actual es al menos 2x el promedio
        """
        try:
            df = self.get_klines(symbol, timeframe, self.config['volume_lookback'] + 5)
            if df.empty or len(df) < self.config['volume_lookback']:
                return {
                    'volume_confirmed': False,
                    'reason': 'Datos insuficientes',
                    'current_volume': 0,
                    'average_volume': 0,
                    'volume_ratio': 0
                }
            
            volumes = df['volume'].values
            current_volume = volumes[-1]
            average_volume = np.mean(volumes[:-1])  # Excluir el volumen actual
            
            volume_ratio = current_volume / average_volume if average_volume > 0 else 0
            volume_confirmed = volume_ratio >= self.config['volume_multiplier']
            
            return {
                'volume_confirmed': volume_confirmed,
                'reason': f'Volumen {volume_ratio:.2f}x el promedio' if volume_confirmed else f'Volumen insuficiente: {volume_ratio:.2f}x < {self.config["volume_multiplier"]}x',
                'current_volume': current_volume,
                'average_volume': average_volume,
                'volume_ratio': volume_ratio
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando volumen para {symbol}: {e}")
            return {
                'volume_confirmed': False,
                'reason': f'Error: {str(e)}',
                'current_volume': 0,
                'average_volume': 0,
                'volume_ratio': 0
            }
    
    def check_timeframe_confirmations(self, symbol: str, expected_signal: str) -> Dict[str, any]:
        """
        Verifica confirmación de señal en múltiples timeframes
        """
        try:
            confirmations = {}
            confirmed_timeframes = []
            
            for tf in self.timeframes:
                tf_result = self._analyze_timeframe_signal(symbol, tf, expected_signal)
                confirmations[tf] = tf_result
                
                if tf_result['signal'] == expected_signal and tf_result['confidence'] > 60:
                    confirmed_timeframes.append(tf)
            
            total_confirmations = len(confirmed_timeframes)
            confirmation_met = total_confirmations >= self.config['min_timeframe_confirmations']
            
            return {
                'timeframe_confirmed': confirmation_met,
                'confirmed_timeframes': confirmed_timeframes,
                'total_confirmations': total_confirmations,
                'required_confirmations': self.config['min_timeframe_confirmations'],
                'details': confirmations,
                'reason': f'{total_confirmations}/{len(self.timeframes)} timeframes confirman la señal'
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando confirmaciones de timeframes para {symbol}: {e}")
            return {
                'timeframe_confirmed': False,
                'confirmed_timeframes': [],
                'total_confirmations': 0,
                'required_confirmations': self.config['min_timeframe_confirmations'],
                'details': {},
                'reason': f'Error: {str(e)}'
            }
    
    def check_momentum_confirmation(self, symbol: str, expected_signal: str, timeframe: str = '1h') -> Dict[str, any]:
        """
        Verifica el momentum usando múltiples indicadores
        """
        try:
            df = self.get_klines(symbol, timeframe, 50)
            if df.empty or len(df) < 30:
                return {
                    'momentum_confirmed': False,
                    'reason': 'Datos insuficientes para momentum',
                    'indicators': {}
                }
            
            closes = df['close']
            highs = df['high']
            lows = df['low']
            volumes = df['volume']
            
            # Calcular indicadores de momentum
            indicators = {}
            
            # RSI
            rsi = talib.RSI(closes.values, timeperiod=14)
            indicators['rsi'] = rsi[-1]
            
            # MACD
            macd, signal, histogram = talib.MACD(closes.values)
            indicators['macd'] = {
                'macd': macd[-1],
                'signal': signal[-1],
                'histogram': histogram[-1]
            }
            
            # Rate of Change
            roc = talib.ROC(closes.values, timeperiod=10)
            indicators['roc'] = roc[-1]
            
            # Williams %R
            williams_r = talib.WILLR(highs.values, lows.values, closes.values, timeperiod=14)
            indicators['williams_r'] = williams_r[-1]
            
            # Commodity Channel Index
            cci = talib.CCI(highs.values, lows.values, closes.values, timeperiod=14)
            indicators['cci'] = cci[-1]
            
            # Stochastic
            slowk, slowd = talib.STOCH(highs.values, lows.values, closes.values)
            indicators['stoch'] = {
                'k': slowk[-1],
                'd': slowd[-1]
            }
            
            # Money Flow Index
            mfi = talib.MFI(highs.values, lows.values, closes.values, volumes.values, timeperiod=14)
            indicators['mfi'] = mfi[-1]
            
            # Evaluar momentum según la señal esperada
            momentum_score = self._calculate_momentum_score(indicators, expected_signal)
            momentum_confirmed = momentum_score >= self.config['momentum_threshold']
            
            return {
                'momentum_confirmed': momentum_confirmed,
                'momentum_score': momentum_score,
                'threshold': self.config['momentum_threshold'],
                'indicators': indicators,
                'reason': f'Momentum score: {momentum_score:.2f} {"≥" if momentum_confirmed else "<"} {self.config["momentum_threshold"]}'
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando momentum para {symbol}: {e}")
            return {
                'momentum_confirmed': False,
                'momentum_score': 0,
                'threshold': self.config['momentum_threshold'],
                'indicators': {},
                'reason': f'Error: {str(e)}'
            }
    
    def check_price_action_confirmation(self, symbol: str, expected_signal: str, timeframe: str = '1h') -> Dict[str, any]:
        """
        Verifica la acción del precio (patrones de velas, breakouts, etc.)
        """
        try:
            df = self.get_klines(symbol, timeframe, 20)
            if df.empty or len(df) < 10:
                return {
                    'price_action_confirmed': False,
                    'reason': 'Datos insuficientes para acción del precio',
                    'patterns': {}
                }
            
            patterns = {}
            
            # Patrones de velas
            opens = df['open'].values
            highs = df['high'].values
            lows = df['low'].values
            closes = df['close'].values
            
            # Doji
            doji = talib.CDLDOJI(opens, highs, lows, closes)
            patterns['doji'] = doji[-1]
            
            # Hammer
            hammer = talib.CDLHAMMER(opens, highs, lows, closes)
            patterns['hammer'] = hammer[-1]
            
            # Engulfing
            engulfing = talib.CDLENGULFING(opens, highs, lows, closes)
            patterns['engulfing'] = engulfing[-1]
            
            # Morning Star
            morning_star = talib.CDLMORNINGSTAR(opens, highs, lows, closes)
            patterns['morning_star'] = morning_star[-1]
            
            # Evening Star
            evening_star = talib.CDLEVENINGSTAR(opens, highs, lows, closes)
            patterns['evening_star'] = evening_star[-1]
            
            # Shooting Star
            shooting_star = talib.CDLSHOOTINGSTAR(opens, highs, lows, closes)
            patterns['shooting_star'] = shooting_star[-1]
            
            # Evaluar patrones según la señal esperada
            price_action_score = self._calculate_price_action_score(patterns, expected_signal)
            price_action_confirmed = price_action_score >= self.config['price_action_threshold']
            
            # Verificar breakout
            breakout_info = self._check_breakout(df, expected_signal)
            patterns.update(breakout_info)
            
            return {
                'price_action_confirmed': price_action_confirmed,
                'price_action_score': price_action_score,
                'threshold': self.config['price_action_threshold'],
                'patterns': patterns,
                'reason': f'Price action score: {price_action_score:.2f} {"≥" if price_action_confirmed else "<"} {self.config["price_action_threshold"]}'
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando acción del precio para {symbol}: {e}")
            return {
                'price_action_confirmed': False,
                'price_action_score': 0,
                'threshold': self.config['price_action_threshold'],
                'patterns': {},
                'reason': f'Error: {str(e)}'
            }
    
    def get_comprehensive_confirmations(self, symbol: str, expected_signal: str) -> Dict[str, any]:
        """
        Realiza todas las verificaciones de confirmación
        """
        try:
            # Verificar volumen
            volume_check = self.check_volume_confirmation(symbol)
            
            # Verificar timeframes
            timeframe_check = self.check_timeframe_confirmations(symbol, expected_signal)
            
            # Verificar momentum
            momentum_check = self.check_momentum_confirmation(symbol, expected_signal)
            
            # Verificar acción del precio
            price_action_check = self.check_price_action_confirmation(symbol, expected_signal)
            
            # Calcular score total de confirmaciones
            confirmations_passed = sum([
                volume_check['volume_confirmed'],
                timeframe_check['timeframe_confirmed'],
                momentum_check['momentum_confirmed'],
                price_action_check['price_action_confirmed']
            ])
            
            total_confirmations = 4
            confirmation_score = (confirmations_passed / total_confirmations) * 100
            
            # Determinar si todas las confirmaciones críticas están cumplidas
            critical_confirmations = [
                timeframe_check['timeframe_confirmed'],  # Crítico
                momentum_check['momentum_confirmed']      # Crítico
            ]
            
            all_critical_passed = all(critical_confirmations)
            
            # Recomendación final
            if confirmation_score >= 75 and all_critical_passed:
                recommendation = 'EXECUTE'
            elif confirmation_score >= 50:
                recommendation = 'CAUTION'
            else:
                recommendation = 'REJECT'
            
            return {
                'symbol': symbol,
                'expected_signal': expected_signal,
                'timestamp': datetime.now(),
                'confirmation_score': confirmation_score,
                'confirmations_passed': confirmations_passed,
                'total_confirmations': total_confirmations,
                'recommendation': recommendation,
                'all_critical_passed': all_critical_passed,
                'details': {
                    'volume': volume_check,
                    'timeframes': timeframe_check,
                    'momentum': momentum_check,
                    'price_action': price_action_check
                },
                'summary': f'{confirmations_passed}/{total_confirmations} confirmaciones pasadas ({confirmation_score:.1f}%)'
            }
            
        except Exception as e:
            self.logger.error(f"Error en confirmaciones comprehensivas para {symbol}: {e}")
            return {
                'symbol': symbol,
                'expected_signal': expected_signal,
                'timestamp': datetime.now(),
                'confirmation_score': 0,
                'confirmations_passed': 0,
                'total_confirmations': 4,
                'recommendation': 'REJECT',
                'all_critical_passed': False,
                'details': {},
                'summary': f'Error en verificación: {str(e)}'
            }
    
    def _analyze_timeframe_signal(self, symbol: str, timeframe: str, expected_signal: str) -> Dict[str, any]:
        """Analiza la señal en un timeframe específico"""
        try:
            df = self.get_klines(symbol, timeframe, 50)
            if df.empty:
                return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': 'Sin datos'}
            
            closes = df['close']
            
            # Indicadores básicos
            rsi = talib.RSI(closes.values, timeperiod=14)[-1]
            macd, signal, histogram = talib.MACD(closes.values)
            sma_20 = talib.SMA(closes.values, timeperiod=20)[-1]
            sma_50 = talib.SMA(closes.values, timeperiod=50)[-1]
            
            # Determinar señal
            signals = []
            
            if rsi < 30:
                signals.append('BUY')
            elif rsi > 70:
                signals.append('SELL')
            
            if macd[-1] > signal[-1]:
                signals.append('BUY')
            elif macd[-1] < signal[-1]:
                signals.append('SELL')
            
            if closes.iloc[-1] > sma_20 > sma_50:
                signals.append('BUY')
            elif closes.iloc[-1] < sma_20 < sma_50:
                signals.append('SELL')
            
            # Contar señales
            buy_count = signals.count('BUY')
            sell_count = signals.count('SELL')
            
            if buy_count > sell_count:
                tf_signal = 'BUY'
                confidence = (buy_count / len(signals)) * 100 if signals else 0
            elif sell_count > buy_count:
                tf_signal = 'SELL'
                confidence = (sell_count / len(signals)) * 100 if signals else 0
            else:
                tf_signal = 'NEUTRAL'
                confidence = 50
            
            return {
                'signal': tf_signal,
                'confidence': confidence,
                'reason': f'{buy_count} BUY, {sell_count} SELL signals'
            }
            
        except Exception as e:
            return {'signal': 'NEUTRAL', 'confidence': 0, 'reason': f'Error: {str(e)}'}
    
    def _calculate_momentum_score(self, indicators: Dict, expected_signal: str) -> float:
        """Calcula el score de momentum basado en indicadores"""
        score = 0
        total_indicators = 0
        
        try:
            # RSI
            rsi = indicators.get('rsi', 50)
            if expected_signal == 'BUY':
                if rsi < 30:
                    score += 1
                elif rsi < 50:
                    score += 0.5
            else:  # SELL
                if rsi > 70:
                    score += 1
                elif rsi > 50:
                    score += 0.5
            total_indicators += 1
            
            # MACD
            macd_data = indicators.get('macd', {})
            if macd_data:
                macd_val = macd_data.get('macd', 0)
                signal_val = macd_data.get('signal', 0)
                histogram = macd_data.get('histogram', 0)
                
                if expected_signal == 'BUY':
                    if macd_val > signal_val and histogram > 0:
                        score += 1
                    elif macd_val > signal_val:
                        score += 0.5
                else:  # SELL
                    if macd_val < signal_val and histogram < 0:
                        score += 1
                    elif macd_val < signal_val:
                        score += 0.5
                total_indicators += 1
            
            # ROC
            roc = indicators.get('roc', 0)
            if expected_signal == 'BUY':
                if roc > 2:
                    score += 1
                elif roc > 0:
                    score += 0.5
            else:  # SELL
                if roc < -2:
                    score += 1
                elif roc < 0:
                    score += 0.5
            total_indicators += 1
            
            # Williams %R
            williams_r = indicators.get('williams_r', -50)
            if expected_signal == 'BUY':
                if williams_r < -80:
                    score += 1
                elif williams_r < -50:
                    score += 0.5
            else:  # SELL
                if williams_r > -20:
                    score += 1
                elif williams_r > -50:
                    score += 0.5
            total_indicators += 1
            
            # Stochastic
            stoch = indicators.get('stoch', {})
            if stoch:
                k = stoch.get('k', 50)
                if expected_signal == 'BUY':
                    if k < 20:
                        score += 1
                    elif k < 50:
                        score += 0.5
                else:  # SELL
                    if k > 80:
                        score += 1
                    elif k > 50:
                        score += 0.5
                total_indicators += 1
            
            return score / total_indicators if total_indicators > 0 else 0
            
        except Exception as e:
            self.logger.error(f"Error calculando momentum score: {e}")
            return 0
    
    def _calculate_price_action_score(self, patterns: Dict, expected_signal: str) -> float:
        """Calcula el score de acción del precio"""
        score = 0
        
        try:
            if expected_signal == 'BUY':
                # Patrones alcistas
                if patterns.get('hammer', 0) > 0:
                    score += 0.3
                if patterns.get('morning_star', 0) > 0:
                    score += 0.4
                if patterns.get('engulfing', 0) > 0:
                    score += 0.3
            else:  # SELL
                # Patrones bajistas
                if patterns.get('shooting_star', 0) > 0:
                    score += 0.3
                if patterns.get('evening_star', 0) > 0:
                    score += 0.4
                if patterns.get('engulfing', 0) < 0:
                    score += 0.3
            
            # Breakout
            if patterns.get('breakout_confirmed', False):
                score += 0.5
            
            return min(score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculando price action score: {e}")
            return 0
    
    def _check_breakout(self, df: pd.DataFrame, expected_signal: str) -> Dict[str, any]:
        """Verifica si hay un breakout confirmado"""
        try:
            if len(df) < 10:
                return {'breakout_confirmed': False, 'breakout_type': 'NONE'}
            
            highs = df['high'].values
            lows = df['low'].values
            closes = df['close'].values
            volumes = df['volume'].values
            
            # Calcular resistencia y soporte recientes
            recent_high = np.max(highs[-10:-1])  # Excluir la vela actual
            recent_low = np.min(lows[-10:-1])
            current_close = closes[-1]
            current_volume = volumes[-1]
            avg_volume = np.mean(volumes[-10:-1])
            
            # Verificar breakout
            breakout_confirmed = False
            breakout_type = 'NONE'
            
            if expected_signal == 'BUY' and current_close > recent_high:
                if current_volume > avg_volume * 1.5:  # Volumen confirmando
                    breakout_confirmed = True
                    breakout_type = 'BULLISH'
            elif expected_signal == 'SELL' and current_close < recent_low:
                if current_volume > avg_volume * 1.5:  # Volumen confirmando
                    breakout_confirmed = True
                    breakout_type = 'BEARISH'
            
            return {
                'breakout_confirmed': breakout_confirmed,
                'breakout_type': breakout_type,
                'recent_high': recent_high,
                'recent_low': recent_low,
                'current_close': current_close,
                'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando breakout: {e}")
            return {'breakout_confirmed': False, 'breakout_type': 'NONE'}

# Función de prueba
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    confirmations = SignalConfirmations()
    
    # Probar confirmaciones con BTCUSDT
    print("Probando confirmaciones de señales con BTCUSDT...")
    result = confirmations.get_comprehensive_confirmations('BTCUSDT', 'BUY')
    
    print(f"\nResultado de confirmaciones:")
    print(f"Símbolo: {result['symbol']}")
    print(f"Señal esperada: {result['expected_signal']}")
    print(f"Score de confirmación: {result['confirmation_score']:.1f}%")
    print(f"Recomendación: {result['recommendation']}")
    print(f"Resumen: {result['summary']}")
    
    print(f"\nDetalles:")
    for check_type, details in result['details'].items():
        if isinstance(details, dict) and 'reason' in details:
            print(f"  {check_type}: {details['reason']}")