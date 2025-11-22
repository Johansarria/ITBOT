#!/usr/bin/env python3
"""
SICAR Indices Parameters Calibrator
Sistema de recalibración de parámetros técnicos específicos para índices
Adapta parámetros de crypto a índices considerando diferencias de mercado
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

from indices_data_provider import IndicesDataProvider, create_indices_provider
from market_hours_system import MarketHoursSystem
from indices_config import IndicesConfigManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndicesParametersCalibrator:
    """
    Calibrador de parámetros técnicos específicos para índices
    
    Recalibra parámetros de crypto a índices considerando:
    - Diferencias de volatilidad
    - Horarios de mercado
    - Características específicas de cada índice
    - Timeframes apropiados
    """
    
    def __init__(self):
        """Inicializar el calibrador de parámetros"""
        self.data_provider = create_indices_provider()
        self.market_hours = MarketHoursSystem()
        self.config_manager = IndicesConfigManager()
        
        # Parámetros base de crypto (para referencia)
        self.crypto_base_params = {
            'timeframes': ['1m', '5m', '15m', '30m', '1h', '4h', '1d'],
            'volatility_window': 14,
            'rsi_period': 14,
            'ma_periods': [20, 50, 200],
            'bollinger_period': 20,
            'bollinger_std': 2.0,
            'atr_period': 14,
            'volume_ma_period': 20,
            'momentum_period': 10,
            'stoch_k_period': 14,
            'stoch_d_period': 3,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9
        }
        
        # Factores de ajuste por índice
        self.index_adjustment_factors = {
            'SPY': {
                'volatility_factor': 0.6,    # Menos volátil que crypto
                'timeframe_factor': 2.0,     # Timeframes más largos
                'momentum_factor': 0.8,      # Momentum más suave
                'trend_factor': 1.2          # Tendencias más persistentes
            },
            'QQQ': {
                'volatility_factor': 0.8,    # Más volátil que SPY
                'timeframe_factor': 1.8,
                'momentum_factor': 1.0,
                'trend_factor': 1.0
            },
            'DIA': {
                'volatility_factor': 0.5,    # Menos volátil
                'timeframe_factor': 2.2,
                'momentum_factor': 0.7,
                'trend_factor': 1.3
            },
            'IWM': {
                'volatility_factor': 1.0,    # Más volátil (small caps)
                'timeframe_factor': 1.5,
                'momentum_factor': 1.1,
                'trend_factor': 0.9
            }
        }
        
        logger.info("🔧 Calibrador de parámetros para índices inicializado")
    
    def calibrate_all_parameters(self, symbol: str, historical_data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Calibrar todos los parámetros técnicos para un índice específico
        
        Args:
            symbol: Símbolo del índice
            historical_data: Datos históricos (opcional)
            
        Returns:
            Diccionario con parámetros calibrados
        """
        try:
            logger.info(f"🎯 Calibrando parámetros para {symbol}...")
            
            # Obtener datos históricos si no se proporcionan
            if historical_data is None:
                historical_data = self._get_calibration_data(symbol)
            
            if historical_data is None or historical_data.empty:
                logger.error(f"No hay datos disponibles para calibrar {symbol}")
                return self._get_default_parameters(symbol)
            
            # Analizar características del mercado
            market_characteristics = self._analyze_market_characteristics(historical_data, symbol)
            
            # Calibrar parámetros específicos
            calibrated_params = {
                'symbol': symbol,
                'calibration_date': datetime.now(),
                'market_characteristics': market_characteristics,
                'timeframes': self._calibrate_timeframes(symbol, market_characteristics),
                'volatility_params': self._calibrate_volatility_parameters(symbol, historical_data, market_characteristics),
                'trend_params': self._calibrate_trend_parameters(symbol, historical_data, market_characteristics),
                'momentum_params': self._calibrate_momentum_parameters(symbol, historical_data, market_characteristics),
                'oscillator_params': self._calibrate_oscillator_parameters(symbol, historical_data, market_characteristics),
                'volume_params': self._calibrate_volume_parameters(symbol, historical_data, market_characteristics),
                'risk_params': self._calibrate_risk_parameters(symbol, historical_data, market_characteristics)
            }
            
            # Validar parámetros calibrados
            validation_results = self._validate_calibrated_parameters(calibrated_params, historical_data)
            calibrated_params['validation'] = validation_results
            
            logger.info(f"✅ Parámetros calibrados exitosamente para {symbol}")
            return calibrated_params
            
        except Exception as e:
            logger.error(f"Error calibrando parámetros para {symbol}: {e}")
            return self._get_default_parameters(symbol)
    
    def _get_calibration_data(self, symbol: str, period: str = '2y') -> Optional[pd.DataFrame]:
        """Obtener datos históricos para calibración"""
        try:
            df = self.data_provider.get_historical_data(
                symbol=symbol,
                period=period,
                interval='1d'
            )
            
            if df is not None and not df.empty:
                logger.info(f"📊 Datos de calibración obtenidos: {len(df)} registros para {symbol}")
                return df
            else:
                logger.warning(f"No se pudieron obtener datos de calibración para {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo datos de calibración: {e}")
            return None
    
    def _analyze_market_characteristics(self, df: pd.DataFrame, symbol: str) -> Dict[str, float]:
        """Analizar características específicas del mercado"""
        try:
            characteristics = {}
            
            # Calcular volatilidad anualizada
            returns = df['Close'].pct_change().dropna()
            characteristics['annual_volatility'] = returns.std() * np.sqrt(252)
            
            # Calcular volatilidad promedio diaria
            characteristics['daily_volatility'] = returns.std()
            
            # Calcular rango promedio (High-Low)/Close
            daily_range = (df['High'] - df['Low']) / df['Close']
            characteristics['average_daily_range'] = daily_range.mean()
            
            # Calcular persistencia de tendencia (autocorrelación)
            if len(returns) > 20:
                characteristics['trend_persistence'] = returns.autocorr(lag=1)
            else:
                characteristics['trend_persistence'] = 0.0
            
            # Calcular frecuencia de gaps
            gaps = abs(df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)
            characteristics['gap_frequency'] = (gaps > 0.01).mean()  # Gaps > 1%
            
            # Calcular sesgo de retornos
            characteristics['return_skewness'] = returns.skew()
            
            # Calcular curtosis de retornos
            characteristics['return_kurtosis'] = returns.kurtosis()
            
            # Calcular ratio de Sharpe aproximado
            if characteristics['annual_volatility'] > 0:
                characteristics['sharpe_ratio'] = (returns.mean() * 252) / characteristics['annual_volatility']
            else:
                characteristics['sharpe_ratio'] = 0.0
            
            # Calcular máximo drawdown
            cumulative_returns = (1 + returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            characteristics['max_drawdown'] = abs(drawdowns.min())
            
            logger.info(f"📈 Características analizadas para {symbol}: Vol={characteristics['annual_volatility']:.2%}")
            return characteristics
            
        except Exception as e:
            logger.error(f"Error analizando características del mercado: {e}")
            return {}
    
    def _calibrate_timeframes(self, symbol: str, market_characteristics: Dict) -> Dict[str, Any]:
        """Calibrar timeframes apropiados para el índice"""
        try:
            # Obtener factor de ajuste
            adjustment_factor = self.index_adjustment_factors.get(symbol, {})
            timeframe_factor = adjustment_factor.get('timeframe_factor', 1.5)
            
            # Timeframes base para índices (más largos que crypto)
            base_timeframes = {
                'scalping': ['1m', '5m'],      # Para análisis muy corto plazo
                'intraday': ['15m', '30m', '1h'], # Para trading intraday
                'swing': ['4h', '1d'],         # Para swing trading
                'position': ['1d', '1wk'],     # Para posiciones largas
                'analysis': ['1d', '1wk', '1mo'] # Para análisis general
            }
            
            # Ajustar según volatilidad
            volatility = market_characteristics.get('annual_volatility', 0.2)
            
            if volatility < 0.15:  # Baja volatilidad
                # Usar timeframes más largos
                recommended_timeframes = {
                    'primary': '1d',
                    'secondary': '4h',
                    'confirmation': '1wk'
                }
            elif volatility < 0.25:  # Volatilidad normal
                recommended_timeframes = {
                    'primary': '4h',
                    'secondary': '1h',
                    'confirmation': '1d'
                }
            else:  # Alta volatilidad
                # Usar timeframes más cortos
                recommended_timeframes = {
                    'primary': '1h',
                    'secondary': '30m',
                    'confirmation': '4h'
                }
            
            return {
                'base_timeframes': base_timeframes,
                'recommended': recommended_timeframes,
                'adjustment_factor': timeframe_factor,
                'volatility_based': True
            }
            
        except Exception as e:
            logger.error(f"Error calibrando timeframes: {e}")
            return {'recommended': {'primary': '1d', 'secondary': '4h', 'confirmation': '1wk'}}
    
    def _calibrate_volatility_parameters(self, symbol: str, df: pd.DataFrame, market_characteristics: Dict) -> Dict[str, Any]:
        """Calibrar parámetros de volatilidad"""
        try:
            # Obtener factor de ajuste
            adjustment_factor = self.index_adjustment_factors.get(symbol, {})
            vol_factor = adjustment_factor.get('volatility_factor', 0.7)
            
            # Parámetros base ajustados
            base_window = int(self.crypto_base_params['volatility_window'] * vol_factor)
            
            # Calibrar ventana de volatilidad basada en datos
            returns = df['Close'].pct_change().dropna()
            
            # Encontrar ventana óptima para volatilidad
            optimal_window = self._find_optimal_volatility_window(returns)
            
            # Parámetros de Bollinger Bands ajustados
            bb_period = max(10, int(self.crypto_base_params['bollinger_period'] * vol_factor))
            bb_std = self.crypto_base_params['bollinger_std'] * (1 + market_characteristics.get('annual_volatility', 0.2))
            
            # ATR ajustado
            atr_period = max(7, int(self.crypto_base_params['atr_period'] * vol_factor))
            
            return {
                'volatility_window': optimal_window,
                'bollinger_bands': {
                    'period': bb_period,
                    'std_dev': bb_std,
                    'adaptive': True
                },
                'atr': {
                    'period': atr_period,
                    'multiplier': 2.0 * vol_factor
                },
                'volatility_regime_thresholds': {
                    'low': market_characteristics.get('annual_volatility', 0.2) * 0.7,
                    'high': market_characteristics.get('annual_volatility', 0.2) * 1.5
                }
            }
            
        except Exception as e:
            logger.error(f"Error calibrando parámetros de volatilidad: {e}")
            return {'volatility_window': 14, 'bollinger_bands': {'period': 20, 'std_dev': 2.0}}
    
    def _calibrate_trend_parameters(self, symbol: str, df: pd.DataFrame, market_characteristics: Dict) -> Dict[str, Any]:
        """Calibrar parámetros de tendencia"""
        try:
            # Obtener factor de ajuste
            adjustment_factor = self.index_adjustment_factors.get(symbol, {})
            trend_factor = adjustment_factor.get('trend_factor', 1.1)
            
            # Ajustar períodos de medias móviles
            base_ma_periods = self.crypto_base_params['ma_periods']
            adjusted_ma_periods = [int(period * trend_factor) for period in base_ma_periods]
            
            # Calibrar basado en persistencia de tendencia
            trend_persistence = market_characteristics.get('trend_persistence', 0.0)
            
            if trend_persistence > 0.1:  # Tendencias persistentes
                # Usar períodos más largos
                ma_periods = [int(p * 1.2) for p in adjusted_ma_periods]
            elif trend_persistence < -0.1:  # Tendencias poco persistentes
                # Usar períodos más cortos
                ma_periods = [int(p * 0.8) for p in adjusted_ma_periods]
            else:
                ma_periods = adjusted_ma_periods
            
            # Parámetros de MACD ajustados
            macd_fast = max(8, int(self.crypto_base_params['macd_fast'] * trend_factor))
            macd_slow = max(20, int(self.crypto_base_params['macd_slow'] * trend_factor))
            macd_signal = max(6, int(self.crypto_base_params['macd_signal'] * trend_factor))
            
            return {
                'moving_averages': {
                    'periods': ma_periods,
                    'types': ['SMA', 'EMA', 'WMA'],
                    'adaptive': True
                },
                'macd': {
                    'fast_period': macd_fast,
                    'slow_period': macd_slow,
                    'signal_period': macd_signal
                },
                'trend_strength_threshold': 0.6 * trend_factor,
                'trend_persistence_factor': trend_persistence
            }
            
        except Exception as e:
            logger.error(f"Error calibrando parámetros de tendencia: {e}")
            return {'moving_averages': {'periods': [20, 50, 200]}}
    
    def _calibrate_momentum_parameters(self, symbol: str, df: pd.DataFrame, market_characteristics: Dict) -> Dict[str, Any]:
        """Calibrar parámetros de momentum"""
        try:
            # Obtener factor de ajuste
            adjustment_factor = self.index_adjustment_factors.get(symbol, {})
            momentum_factor = adjustment_factor.get('momentum_factor', 0.9)
            
            # RSI ajustado
            rsi_period = max(10, int(self.crypto_base_params['rsi_period'] * momentum_factor))
            
            # Momentum period ajustado
            momentum_period = max(5, int(self.crypto_base_params['momentum_period'] * momentum_factor))
            
            # Calibrar umbrales de RSI basados en características del mercado
            volatility = market_characteristics.get('annual_volatility', 0.2)
            
            if volatility < 0.15:  # Baja volatilidad
                rsi_thresholds = {'oversold': 25, 'overbought': 75}
            elif volatility < 0.25:  # Volatilidad normal
                rsi_thresholds = {'oversold': 30, 'overbought': 70}
            else:  # Alta volatilidad
                rsi_thresholds = {'oversold': 35, 'overbought': 65}
            
            return {
                'rsi': {
                    'period': rsi_period,
                    'thresholds': rsi_thresholds,
                    'adaptive': True
                },
                'momentum': {
                    'period': momentum_period,
                    'threshold': 0.02 * momentum_factor
                },
                'rate_of_change': {
                    'period': momentum_period,
                    'threshold': 0.05 * momentum_factor
                }
            }
            
        except Exception as e:
            logger.error(f"Error calibrando parámetros de momentum: {e}")
            return {'rsi': {'period': 14, 'thresholds': {'oversold': 30, 'overbought': 70}}}
    
    def _calibrate_oscillator_parameters(self, symbol: str, df: pd.DataFrame, market_characteristics: Dict) -> Dict[str, Any]:
        """Calibrar parámetros de osciladores"""
        try:
            # Obtener factor de ajuste
            adjustment_factor = self.index_adjustment_factors.get(symbol, {})
            
            # Stochastic ajustado
            stoch_k = max(10, int(self.crypto_base_params['stoch_k_period'] * 0.9))
            stoch_d = max(2, int(self.crypto_base_params['stoch_d_period'] * 0.9))
            
            # Williams %R ajustado
            williams_period = max(10, int(14 * 0.9))
            
            return {
                'stochastic': {
                    'k_period': stoch_k,
                    'd_period': stoch_d,
                    'smooth': 3,
                    'thresholds': {'oversold': 20, 'overbought': 80}
                },
                'williams_r': {
                    'period': williams_period,
                    'thresholds': {'oversold': -80, 'overbought': -20}
                },
                'cci': {
                    'period': 20,
                    'thresholds': {'oversold': -100, 'overbought': 100}
                }
            }
            
        except Exception as e:
            logger.error(f"Error calibrando parámetros de osciladores: {e}")
            return {'stochastic': {'k_period': 14, 'd_period': 3}}
    
    def _calibrate_volume_parameters(self, symbol: str, df: pd.DataFrame, market_characteristics: Dict) -> Dict[str, Any]:
        """Calibrar parámetros de volumen"""
        try:
            # Volumen promedio
            if 'Volume' in df.columns:
                avg_volume = df['Volume'].mean()
                volume_std = df['Volume'].std()
                
                # Umbrales de volumen
                high_volume_threshold = avg_volume + volume_std
                low_volume_threshold = avg_volume - volume_std * 0.5
                
                return {
                    'volume_ma_period': 20,
                    'volume_thresholds': {
                        'high': high_volume_threshold,
                        'low': max(0, low_volume_threshold),
                        'average': avg_volume
                    },
                    'volume_spike_threshold': 2.0,  # 2x volumen promedio
                    'on_balance_volume': {
                        'period': 20,
                        'signal_threshold': 0.1
                    }
                }
            else:
                return {
                    'volume_ma_period': 20,
                    'volume_spike_threshold': 2.0
                }
                
        except Exception as e:
            logger.error(f"Error calibrando parámetros de volumen: {e}")
            return {'volume_ma_period': 20}
    
    def _calibrate_risk_parameters(self, symbol: str, df: pd.DataFrame, market_characteristics: Dict) -> Dict[str, Any]:
        """Calibrar parámetros de gestión de riesgo"""
        try:
            # Obtener factor de ajuste
            adjustment_factor = self.index_adjustment_factors.get(symbol, {})
            vol_factor = adjustment_factor.get('volatility_factor', 0.7)
            
            # Calcular ATR para stop loss dinámico
            high_low = df['High'] - df['Low']
            high_close = abs(df['High'] - df['Close'].shift(1))
            low_close = abs(df['Low'] - df['Close'].shift(1))
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(window=14).mean().iloc[-1]
            
            # Stop loss basado en ATR
            atr_multiplier = 2.0 * vol_factor
            dynamic_stop_loss = atr * atr_multiplier / df['Close'].iloc[-1]
            
            # Parámetros de riesgo ajustados
            max_position_size = 0.1 * vol_factor  # Máximo 10% ajustado por volatilidad
            risk_per_trade = 0.01 * vol_factor    # 1% ajustado por volatilidad
            
            return {
                'stop_loss': {
                    'fixed_percentage': 0.02 * vol_factor,  # 2% fijo ajustado
                    'atr_based': dynamic_stop_loss,
                    'atr_multiplier': atr_multiplier,
                    'adaptive': True
                },
                'take_profit': {
                    'risk_reward_ratio': 2.0,  # 2:1 ratio
                    'atr_based': dynamic_stop_loss * 2.0,
                    'adaptive': True
                },
                'position_sizing': {
                    'max_position_size': max_position_size,
                    'risk_per_trade': risk_per_trade,
                    'volatility_adjusted': True
                },
                'drawdown_limits': {
                    'max_drawdown': 0.08 * vol_factor,  # 8% máximo ajustado
                    'daily_loss_limit': 0.02 * vol_factor
                }
            }
            
        except Exception as e:
            logger.error(f"Error calibrando parámetros de riesgo: {e}")
            return {'stop_loss': {'fixed_percentage': 0.02}, 'take_profit': {'risk_reward_ratio': 2.0}}
    
    def _find_optimal_volatility_window(self, returns: pd.Series) -> int:
        """Encontrar ventana óptima para cálculo de volatilidad"""
        try:
            if len(returns) < 50:
                return 14  # Default
            
            # Probar diferentes ventanas
            windows = [7, 10, 14, 20, 30]
            best_window = 14
            best_score = float('inf')
            
            for window in windows:
                if len(returns) > window * 2:
                    # Calcular volatilidad con esta ventana
                    vol = returns.rolling(window=window).std()
                    
                    # Calcular estabilidad de la volatilidad
                    vol_changes = vol.pct_change().abs().mean()
                    
                    if vol_changes < best_score:
                        best_score = vol_changes
                        best_window = window
            
            return best_window
            
        except Exception as e:
            logger.error(f"Error encontrando ventana óptima: {e}")
            return 14
    
    def _validate_calibrated_parameters(self, params: Dict, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """Validar parámetros calibrados"""
        try:
            validation = {
                'status': 'valid',
                'warnings': [],
                'recommendations': []
            }
            
            # Validar timeframes
            timeframes = params.get('timeframes', {}).get('recommended', {})
            if not timeframes:
                validation['warnings'].append('No se pudieron calibrar timeframes')
            
            # Validar parámetros de volatilidad
            vol_params = params.get('volatility_params', {})
            if vol_params.get('volatility_window', 0) < 5:
                validation['warnings'].append('Ventana de volatilidad muy pequeña')
            
            # Validar parámetros de riesgo
            risk_params = params.get('risk_params', {})
            stop_loss = risk_params.get('stop_loss', {}).get('fixed_percentage', 0)
            if stop_loss > 0.05:  # Más del 5%
                validation['recommendations'].append('Stop loss muy amplio para índices')
            
            return validation
            
        except Exception as e:
            logger.error(f"Error validando parámetros: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_default_parameters(self, symbol: str) -> Dict[str, Any]:
        """Obtener parámetros por defecto para un índice"""
        try:
            # Parámetros conservadores por defecto
            return {
                'symbol': symbol,
                'calibration_date': datetime.now(),
                'source': 'default',
                'timeframes': {
                    'recommended': {
                        'primary': '1d',
                        'secondary': '4h',
                        'confirmation': '1wk'
                    }
                },
                'volatility_params': {
                    'volatility_window': 14,
                    'bollinger_bands': {'period': 20, 'std_dev': 2.0}
                },
                'trend_params': {
                    'moving_averages': {'periods': [20, 50, 200]}
                },
                'momentum_params': {
                    'rsi': {'period': 14, 'thresholds': {'oversold': 30, 'overbought': 70}}
                },
                'risk_params': {
                    'stop_loss': {'fixed_percentage': 0.02},
                    'take_profit': {'risk_reward_ratio': 2.0}
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo parámetros por defecto: {e}")
            return {}
    
    def save_calibrated_parameters(self, symbol: str, parameters: Dict) -> bool:
        """Guardar parámetros calibrados"""
        try:
            import json
            import os
            
            # Crear directorio si no existe
            params_dir = 'calibrated_parameters'
            os.makedirs(params_dir, exist_ok=True)
            
            # Guardar parámetros
            filename = f"{params_dir}/{symbol}_calibrated_params.json"
            with open(filename, 'w') as f:
                json.dump(parameters, f, indent=2, default=str)
            
            logger.info(f"💾 Parámetros guardados en {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando parámetros: {e}")
            return False
    
    def load_calibrated_parameters(self, symbol: str) -> Optional[Dict]:
        """Cargar parámetros calibrados guardados"""
        try:
            import json
            
            filename = f"calibrated_parameters/{symbol}_calibrated_params.json"
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    parameters = json.load(f)
                
                logger.info(f"📂 Parámetros cargados desde {filename}")
                return parameters
            else:
                logger.info(f"No se encontraron parámetros guardados para {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error cargando parámetros: {e}")
            return None

def calibrate_all_indices():
    """Función para calibrar parámetros de todos los índices"""
    calibrator = IndicesParametersCalibrator()
    indices = ['SPY', 'QQQ', 'DIA', 'IWM']
    
    results = {}
    
    for symbol in indices:
        print(f"\n🎯 Calibrando {symbol}...")
        params = calibrator.calibrate_all_parameters(symbol)
        
        if params:
            calibrator.save_calibrated_parameters(symbol, params)
            results[symbol] = params
            print(f"✅ {symbol} calibrado exitosamente")
        else:
            print(f"❌ Error calibrando {symbol}")
    
    return results

if __name__ == "__main__":
    # Test del calibrador
    print("🧪 Testing Indices Parameters Calibrator...")
    
    calibrator = IndicesParametersCalibrator()
    
    # Calibrar SPY como ejemplo
    params = calibrator.calibrate_all_parameters('SPY')
    
    if params:
        print("✅ Calibración exitosa")
        print(f"Timeframes recomendados: {params.get('timeframes', {}).get('recommended', {})}")
        print(f"Parámetros de volatilidad: {params.get('volatility_params', {}).get('volatility_window', 'N/A')}")
    else:
        print("❌ Error en calibración")
    
    print("\n🏁 Test completado")