"""
SICAR Indices Parameters Calibrator
Recalibración de parámetros técnicos específicos para índices
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndicesParametersCalibrator:
    """
    Calibrador de parámetros técnicos para índices
    Adapta parámetros de crypto a índices usando factores de ajuste
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Factores de ajuste base (crypto -> índices)
        self.adjustment_factors = {
            'volatility': {
                'SPY': 0.25,   # S&P 500 menos volátil
                'QQQ': 0.35,   # Nasdaq más volátil
                'IWM': 0.45,   # Small caps más volátiles
                'DIA': 0.25,   # Dow Jones estable
                'VTI': 0.25    # Total market estable
            },
            'timeframe': {
                'SPY': 1.5,    # Timeframes más largos
                'QQQ': 1.3,
                'IWM': 1.2,
                'DIA': 1.5,
                'VTI': 1.5
            },
            'momentum': {
                'SPY': 1.4,    # Períodos de momentum más largos
                'QQQ': 1.2,
                'IWM': 1.1,
                'DIA': 1.4,
                'VTI': 1.4
            },
            'trend': {
                'SPY': 1.6,    # Períodos de tendencia más largos
                'QQQ': 1.4,
                'IWM': 1.2,
                'DIA': 1.6,
                'VTI': 1.6
            }
        }
        
        # Parámetros base de crypto (para referencia)
        self.crypto_base_params = {
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0,
            'ema_short': 9,
            'ema_long': 21,
            'atr_period': 14,
            'volume_sma': 20,
            'volatility_window': 20,
            'trend_window': 50,
            'momentum_window': 14
        }
    
    def calibrate_for_symbol(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calibrar parámetros para un símbolo específico
        
        Args:
            symbol: Símbolo del índice
            data: Datos históricos para análisis
            
        Returns:
            Diccionario con parámetros calibrados
        """
        try:
            self.logger.info(f"Calibrando parámetros para {symbol}")
            
            # Analizar características del mercado
            market_characteristics = self._analyze_market_characteristics(data, symbol)
            
            # Calibrar parámetros específicos
            calibrated_params = {
                'symbol': symbol,
                'calibration_date': datetime.now().isoformat(),
                'market_characteristics': market_characteristics,
                'timeframe_adjustments': self._calibrate_timeframes(symbol, market_characteristics),
                'volatility_adjustments': self._calibrate_volatility_params(symbol, market_characteristics),
                'trend_adjustments': self._calibrate_trend_params(symbol, market_characteristics),
                'momentum_adjustments': self._calibrate_momentum_params(symbol, market_characteristics),
                'risk_adjustments': self._calibrate_risk_params(symbol, market_characteristics),
                'technical_indicators': self._calibrate_technical_indicators(symbol, market_characteristics)
            }
            
            # Validar parámetros calibrados
            validation_result = self._validate_calibrated_params(calibrated_params)
            calibrated_params['validation'] = validation_result
            
            return calibrated_params
            
        except Exception as e:
            self.logger.error(f"Error calibrando parámetros para {symbol}: {e}")
            return self._get_default_params(symbol)
    
    def _analyze_market_characteristics(self, data: pd.DataFrame, symbol: str) -> Dict[str, float]:
        """Analizar características del mercado"""
        try:
            if len(data) < 50:
                return self._get_default_characteristics(symbol)
            
            # Calcular returns si no existen
            if 'returns' not in data.columns:
                data['returns'] = data['Close'].pct_change()
            
            characteristics = {
                'avg_volatility': float(data['returns'].std() * np.sqrt(252)),  # Anualizada
                'avg_volume': float(data['Volume'].mean()) if 'Volume' in data.columns else 1000000,
                'price_range': float((data['Close'].max() - data['Close'].min()) / data['Close'].mean()),
                'trend_strength': self._calculate_trend_strength(data),
                'mean_reversion_tendency': self._calculate_mean_reversion(data),
                'momentum_persistence': self._calculate_momentum_persistence(data),
                'volatility_clustering': self._calculate_volatility_clustering(data),
                'liquidity_score': self._calculate_liquidity_score(data)
            }
            
            return characteristics
            
        except Exception as e:
            self.logger.error(f"Error analizando características para {symbol}: {e}")
            return self._get_default_characteristics(symbol)
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Calcular fuerza de tendencia"""
        try:
            if len(data) < 50:
                return 0.5
            
            # Usar EMA para detectar tendencia
            ema_short = data['Close'].ewm(span=20).mean()
            ema_long = data['Close'].ewm(span=50).mean()
            
            # Calcular porcentaje de tiempo en tendencia
            trend_up = (ema_short > ema_long).sum()
            trend_strength = abs(trend_up / len(data) - 0.5) * 2  # 0-1 scale
            
            return float(min(1.0, max(0.0, trend_strength)))
            
        except:
            return 0.5
    
    def _calculate_mean_reversion(self, data: pd.DataFrame) -> float:
        """Calcular tendencia de reversión a la media"""
        try:
            if len(data) < 30:
                return 0.5
            
            # Calcular autocorrelación de returns
            returns = data['returns'].dropna()
            if len(returns) < 20:
                return 0.5
            
            autocorr = returns.autocorr(lag=1)
            # Convertir a score 0-1 (más negativo = más mean reverting)
            mean_reversion = max(0, -autocorr)
            
            return float(min(1.0, max(0.0, mean_reversion)))
            
        except:
            return 0.5
    
    def _calculate_momentum_persistence(self, data: pd.DataFrame) -> float:
        """Calcular persistencia del momentum"""
        try:
            if len(data) < 30:
                return 0.5
            
            # Calcular momentum usando RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # Calcular persistencia (tiempo en zonas extremas)
            extreme_zones = ((rsi > 70) | (rsi < 30)).sum()
            persistence = extreme_zones / len(rsi.dropna())
            
            return float(min(1.0, max(0.0, persistence)))
            
        except:
            return 0.5
    
    def _calculate_volatility_clustering(self, data: pd.DataFrame) -> float:
        """Calcular clustering de volatilidad"""
        try:
            if len(data) < 50:
                return 0.5
            
            returns = data['returns'].dropna()
            if len(returns) < 30:
                return 0.5
            
            # Calcular volatilidad rolling
            vol_window = min(20, len(returns) // 3)
            rolling_vol = returns.rolling(window=vol_window).std()
            
            # Calcular autocorrelación de volatilidad
            vol_autocorr = rolling_vol.dropna().autocorr(lag=1)
            
            # Convertir a score 0-1
            clustering = max(0, vol_autocorr)
            
            return float(min(1.0, max(0.0, clustering)))
            
        except:
            return 0.5
    
    def _calculate_liquidity_score(self, data: pd.DataFrame) -> float:
        """Calcular score de liquidez"""
        try:
            if 'Volume' not in data.columns or len(data) < 20:
                return 0.5
            
            # Score basado en volumen promedio y consistencia
            avg_volume = data['Volume'].mean()
            vol_std = data['Volume'].std()
            
            # Normalizar (valores típicos para índices principales)
            volume_scores = {
                'SPY': 50000000,
                'QQQ': 30000000,
                'IWM': 20000000,
                'DIA': 5000000,
                'VTI': 3000000
            }
            
            # Score basado en volumen relativo
            expected_volume = volume_scores.get('SPY', 10000000)  # Default
            volume_ratio = min(2.0, avg_volume / expected_volume)
            
            # Score basado en consistencia (menor std relativo = mejor)
            consistency_score = 1 - min(1.0, vol_std / avg_volume)
            
            liquidity_score = (volume_ratio + consistency_score) / 2
            
            return float(min(1.0, max(0.0, liquidity_score)))
            
        except:
            return 0.5
    
    def _calibrate_timeframes(self, symbol: str, characteristics: Dict[str, float]) -> Dict[str, int]:
        """Calibrar timeframes"""
        base_factor = self.adjustment_factors['timeframe'].get(symbol, 1.0)
        
        # Ajustar basado en características del mercado
        volatility_adj = 1 + (characteristics['avg_volatility'] - 0.2) * 0.5
        trend_adj = 1 + characteristics['trend_strength'] * 0.3
        
        total_factor = base_factor * volatility_adj * trend_adj
        
        return {
            'short_window': max(5, int(self.crypto_base_params['ema_short'] * total_factor)),
            'long_window': max(15, int(self.crypto_base_params['ema_long'] * total_factor)),
            'trend_window': max(30, int(self.crypto_base_params['trend_window'] * total_factor)),
            'volatility_window': max(10, int(self.crypto_base_params['volatility_window'] * total_factor))
        }
    
    def _calibrate_volatility_params(self, symbol: str, characteristics: Dict[str, float]) -> Dict[str, float]:
        """Calibrar parámetros de volatilidad"""
        base_factor = self.adjustment_factors['volatility'].get(symbol, 1.0)
        
        # Ajustar basado en volatilidad observada
        vol_adj = characteristics['avg_volatility'] / 0.2  # Normalizar a volatilidad típica
        clustering_adj = 1 + characteristics['volatility_clustering'] * 0.2
        
        return {
            'volatility_multiplier': float(base_factor * vol_adj),
            'volatility_threshold': float(0.02 * base_factor),  # 2% base
            'volatility_window_adj': float(clustering_adj),
            'atr_multiplier': float(2.0 * base_factor)
        }
    
    def _calibrate_trend_params(self, symbol: str, characteristics: Dict[str, float]) -> Dict[str, int]:
        """Calibrar parámetros de tendencia"""
        base_factor = self.adjustment_factors['trend'].get(symbol, 1.0)
        
        # Ajustar basado en fuerza de tendencia
        trend_adj = 1 + characteristics['trend_strength'] * 0.5
        mean_reversion_adj = 1 - characteristics['mean_reversion_tendency'] * 0.3
        
        total_factor = base_factor * trend_adj * mean_reversion_adj
        
        return {
            'trend_period': max(20, int(50 * total_factor)),
            'trend_confirmation': max(3, int(5 * total_factor)),
            'trend_exit_period': max(10, int(20 * total_factor))
        }
    
    def _calibrate_momentum_params(self, symbol: str, characteristics: Dict[str, float]) -> Dict[str, int]:
        """Calibrar parámetros de momentum"""
        base_factor = self.adjustment_factors['momentum'].get(symbol, 1.0)
        
        # Ajustar basado en persistencia de momentum
        momentum_adj = 1 + characteristics['momentum_persistence'] * 0.4
        
        total_factor = base_factor * momentum_adj
        
        return {
            'rsi_period': max(10, int(self.crypto_base_params['rsi_period'] * total_factor)),
            'momentum_window': max(8, int(self.crypto_base_params['momentum_window'] * total_factor)),
            'macd_fast': max(8, int(self.crypto_base_params['macd_fast'] * total_factor)),
            'macd_slow': max(20, int(self.crypto_base_params['macd_slow'] * total_factor))
        }
    
    def _calibrate_risk_params(self, symbol: str, characteristics: Dict[str, float]) -> Dict[str, float]:
        """Calibrar parámetros de riesgo"""
        base_vol = self.adjustment_factors['volatility'].get(symbol, 1.0)
        
        # Ajustar stop loss y take profit basado en volatilidad
        vol_multiplier = characteristics['avg_volatility'] / 0.15  # Normalizar
        liquidity_adj = characteristics['liquidity_score']
        
        return {
            'stop_loss_pct': float(0.015 * vol_multiplier),  # 1.5% base
            'take_profit_pct': float(0.03 * vol_multiplier),  # 3% base
            'position_size_adj': float(liquidity_adj * 0.8 + 0.2),  # 0.2-1.0 range
            'max_drawdown_pct': float(0.05 * vol_multiplier)  # 5% base
        }
    
    def _calibrate_technical_indicators(self, symbol: str, characteristics: Dict[str, float]) -> Dict[str, Any]:
        """Calibrar indicadores técnicos"""
        timeframes = self._calibrate_timeframes(symbol, characteristics)
        
        return {
            'bollinger_bands': {
                'period': timeframes['volatility_window'],
                'std_dev': 2.0 + characteristics['volatility_clustering'] * 0.5
            },
            'moving_averages': {
                'fast_ma': timeframes['short_window'],
                'slow_ma': timeframes['long_window'],
                'trend_ma': timeframes['trend_window']
            },
            'oscillators': {
                'rsi_period': max(10, int(14 * self.adjustment_factors['momentum'].get(symbol, 1.0))),
                'stoch_k': max(10, int(14 * self.adjustment_factors['momentum'].get(symbol, 1.0))),
                'stoch_d': 3
            }
        }
    
    def _validate_calibrated_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validar parámetros calibrados"""
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        try:
            # Validar timeframes
            timeframes = params.get('timeframe_adjustments', {})
            if timeframes.get('short_window', 0) >= timeframes.get('long_window', 0):
                validation['errors'].append("Short window debe ser menor que long window")
                validation['is_valid'] = False
            
            # Validar parámetros de riesgo
            risk_params = params.get('risk_adjustments', {})
            if risk_params.get('stop_loss_pct', 0) >= risk_params.get('take_profit_pct', 0):
                validation['warnings'].append("Stop loss mayor o igual que take profit")
            
            # Validar rangos
            if risk_params.get('stop_loss_pct', 0) > 0.1:  # 10%
                validation['warnings'].append("Stop loss muy alto (>10%)")
            
            if risk_params.get('position_size_adj', 0) > 1.0:
                validation['errors'].append("Ajuste de posición > 100%")
                validation['is_valid'] = False
            
        except Exception as e:
            validation['errors'].append(f"Error en validación: {str(e)}")
            validation['is_valid'] = False
        
        return validation
    
    def _get_default_params(self, symbol: str) -> Dict[str, Any]:
        """Obtener parámetros por defecto"""
        return {
            'symbol': symbol,
            'calibration_date': datetime.now().isoformat(),
            'market_characteristics': self._get_default_characteristics(symbol),
            'timeframe_adjustments': {
                'short_window': 12,
                'long_window': 26,
                'trend_window': 50,
                'volatility_window': 20
            },
            'volatility_adjustments': {
                'volatility_multiplier': 1.0,
                'volatility_threshold': 0.02,
                'volatility_window_adj': 1.0,
                'atr_multiplier': 2.0
            },
            'trend_adjustments': {
                'trend_period': 50,
                'trend_confirmation': 5,
                'trend_exit_period': 20
            },
            'momentum_adjustments': {
                'rsi_period': 14,
                'momentum_window': 14,
                'macd_fast': 12,
                'macd_slow': 26
            },
            'risk_adjustments': {
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.04,
                'position_size_adj': 1.0,
                'max_drawdown_pct': 0.05
            },
            'validation': {'is_valid': True, 'warnings': [], 'errors': []}
        }
    
    def _get_default_characteristics(self, symbol: str) -> Dict[str, float]:
        """Obtener características por defecto"""
        return {
            'avg_volatility': 0.15,
            'avg_volume': 10000000,
            'price_range': 0.5,
            'trend_strength': 0.5,
            'mean_reversion_tendency': 0.3,
            'momentum_persistence': 0.4,
            'volatility_clustering': 0.6,
            'liquidity_score': 0.8
        }
    
    def save_calibrated_params(self, params: Dict[str, Any], filepath: str):
        """Guardar parámetros calibrados"""
        try:
            with open(filepath, 'w') as f:
                json.dump(params, f, indent=2)
            self.logger.info(f"Parámetros guardados en {filepath}")
        except Exception as e:
            self.logger.error(f"Error guardando parámetros: {e}")
    
    def load_calibrated_params(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Cargar parámetros calibrados"""
        try:
            with open(filepath, 'r') as f:
                params = json.load(f)
            self.logger.info(f"Parámetros cargados desde {filepath}")
            return params
        except Exception as e:
            self.logger.error(f"Error cargando parámetros: {e}")
            return None

# Función de utilidad para calibración rápida
def quick_calibrate(symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
    """Calibración rápida de parámetros"""
    calibrator = IndicesParametersCalibrator()
    return calibrator.calibrate_for_symbol(symbol, data)