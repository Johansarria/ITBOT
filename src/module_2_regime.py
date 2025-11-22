# /src/module_2_regime.py
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import joblib
import os
import sys
import logging
from typing import Dict, List, Tuple, Optional, Any
import json
from datetime import datetime
import warnings
from scipy import stats
from scipy.stats import jarque_bera, normaltest, kstest
from scipy.signal import find_peaks
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.stats.diagnostic import het_breuschpagan
import ruptures as rpt  # Para detección de cambios estructurales
warnings.filterwarnings('ignore')

# Agregar el directorio padre al path para importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import N_REGIMES

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExtremeNonStationarityDetector:
    """
    Detector avanzado de no-estacionariedad extrema
    Utiliza múltiples tests estadísticos y análisis de cambios estructurales
    """
    
    def __init__(self):
        """Inicializar detector de no-estacionariedad extrema"""
        self.extreme_threshold = 0.95  # Umbral para considerar extremo
        self.structural_change_threshold = 0.01  # p-value para cambios estructurales
        self.volatility_spike_threshold = 3.0  # Múltiplo de desviación estándar
        
        # Historial de detecciones
        self.extreme_events_history = []
        self.structural_changes_history = []
        
        logger.info("Detector de No-Estacionariedad Extrema inicializado")
    
    def detect_extreme_nonstationarity(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Detecta no-estacionariedad extrema usando múltiples métodos
        
        Args:
            market_data: DataFrame con datos de mercado
            
        Returns:
            Dict con resultados de detección
        """
        try:
            logger.info("Iniciando detección de no-estacionariedad extrema...")
            
            # Preparar datos
            prices = market_data['close'].dropna()
            returns = np.diff(np.log(prices))
            
            if len(returns) < 50:
                logger.warning("Datos insuficientes para análisis de no-estacionariedad")
                return self._create_default_result()
            
            # 1. Tests de estacionariedad
            stationarity_results = self._test_stationarity(returns)
            
            # 2. Detección de cambios estructurales
            structural_changes = self._detect_structural_changes(returns)
            
            # 3. Análisis de volatilidad extrema
            volatility_analysis = self._analyze_extreme_volatility(returns)
            
            # 4. Tests de normalidad y distribución
            distribution_tests = self._test_distribution_properties(returns)
            
            # 5. Detección de regímenes extremos
            extreme_regimes = self._detect_extreme_regimes(market_data)
            
            # 6. Análisis de autocorrelación
            autocorr_analysis = self._analyze_autocorrelation(returns)
            
            # 7. Calcular score de extremidad
            extremity_score = self._calculate_extremity_score(
                stationarity_results, structural_changes, volatility_analysis,
                distribution_tests, extreme_regimes, autocorr_analysis
            )
            
            # Compilar resultados
            results = {
                'timestamp': datetime.now().isoformat(),
                'extremity_score': extremity_score,
                'is_extreme': extremity_score > self.extreme_threshold,
                'stationarity_tests': stationarity_results,
                'structural_changes': structural_changes,
                'volatility_analysis': volatility_analysis,
                'distribution_tests': distribution_tests,
                'extreme_regimes': extreme_regimes,
                'autocorrelation_analysis': autocorr_analysis,
                'recommendations': self._generate_recommendations(extremity_score)
            }
            
            # Guardar evento extremo si se detecta
            if results['is_extreme']:
                self._log_extreme_event(results)
            
            logger.info(f"Detección completada. Score de extremidad: {extremity_score:.3f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en detección de no-estacionariedad extrema: {e}")
            return self._create_default_result()
    
    def _test_stationarity(self, returns: np.ndarray) -> Dict[str, Any]:
        """Tests de estacionariedad (ADF, KPSS)"""
        try:
            # Test Augmented Dickey-Fuller
            adf_stat, adf_pvalue, adf_lags, adf_nobs, adf_critical, adf_icbest = adfuller(returns, autolag='AIC')
            
            # Test KPSS
            kpss_stat, kpss_pvalue, kpss_lags, kpss_critical = kpss(returns, regression='c')
            
            return {
                'adf_test': {
                    'statistic': adf_stat,
                    'pvalue': adf_pvalue,
                    'critical_values': adf_critical,
                    'is_stationary': adf_pvalue < 0.05
                },
                'kpss_test': {
                    'statistic': kpss_stat,
                    'pvalue': kpss_pvalue,
                    'critical_values': kpss_critical,
                    'is_stationary': kpss_pvalue > 0.05
                }
            }
        except Exception as e:
            logger.error(f"Error en tests de estacionariedad: {e}")
            return {'adf_test': {}, 'kpss_test': {}}
    
    def _detect_structural_changes(self, returns: np.ndarray) -> Dict[str, Any]:
        """Detecta cambios estructurales usando ruptures"""
        try:
            # Detección de cambios en la media
            algo_mean = rpt.Pelt(model="rbf").fit(returns.reshape(-1, 1))
            mean_changes = algo_mean.predict(pen=10)
            
            # Detección de cambios en la varianza
            algo_var = rpt.Pelt(model="rbf").fit(returns**2)
            var_changes = algo_var.predict(pen=10)
            
            # Calcular significancia de los cambios
            n_changes = len(mean_changes) + len(var_changes) - 2  # -2 porque incluyen el final
            change_intensity = n_changes / len(returns)
            
            return {
                'mean_changes': mean_changes[:-1],  # Excluir el último punto (final de serie)
                'variance_changes': var_changes[:-1],
                'total_changes': n_changes,
                'change_intensity': change_intensity,
                'has_structural_changes': change_intensity > 0.05  # Más del 5% de puntos son cambios
            }
        except Exception as e:
            logger.error(f"Error en detección de cambios estructurales: {e}")
            return {'mean_changes': [], 'variance_changes': [], 'total_changes': 0, 'change_intensity': 0.0, 'has_structural_changes': False}
    
    def _analyze_extreme_volatility(self, returns: np.ndarray) -> Dict[str, Any]:
        """Analiza volatilidad extrema y spikes"""
        try:
            # Calcular volatilidad rolling
            window = min(20, len(returns) // 4)
            rolling_vol = pd.Series(returns).rolling(window=window).std()
            
            # Detectar spikes de volatilidad
            vol_mean = rolling_vol.mean()
            vol_std = rolling_vol.std()
            vol_threshold = vol_mean + self.volatility_spike_threshold * vol_std
            
            vol_spikes = rolling_vol > vol_threshold
            n_spikes = vol_spikes.sum()
            
            # Calcular GARCH-like volatility clustering
            abs_returns = np.abs(returns)
            autocorr_vol = np.corrcoef(abs_returns[:-1], abs_returns[1:])[0, 1] if len(abs_returns) > 1 else 0
            
            # Detectar volatilidad persistente
            high_vol_periods = rolling_vol > rolling_vol.quantile(0.8)
            vol_persistence = self._calculate_persistence(high_vol_periods)
            
            return {
                'current_volatility': rolling_vol.iloc[-1] if len(rolling_vol) > 0 else 0,
                'volatility_spikes': n_spikes,
                'spike_intensity': n_spikes / len(returns),
                'volatility_clustering': autocorr_vol,
                'volatility_persistence': vol_persistence,
                'is_extreme_volatility': n_spikes > len(returns) * 0.1  # Más del 10% son spikes
            }
        except Exception as e:
            logger.error(f"Error en análisis de volatilidad extrema: {e}")
            return {'current_volatility': 0, 'volatility_spikes': 0, 'spike_intensity': 0, 'volatility_clustering': 0, 'volatility_persistence': 0, 'is_extreme_volatility': False}
    
    def _test_distribution_properties(self, returns: np.ndarray) -> Dict[str, Any]:
        """Tests de propiedades de distribución"""
        try:
            # Test de normalidad Jarque-Bera
            jb_stat, jb_pvalue = jarque_bera(returns)
            
            # Test de normalidad D'Agostino
            da_stat, da_pvalue = normaltest(returns)
            
            # Test Kolmogorov-Smirnov contra distribución normal
            ks_stat, ks_pvalue = kstest(returns, 'norm', args=(np.mean(returns), np.std(returns)))
            
            # Calcular momentos
            skewness = stats.skew(returns)
            kurtosis = stats.kurtosis(returns)
            
            # Detectar colas pesadas
            heavy_tails = abs(kurtosis) > 3  # Kurtosis excesiva
            
            return {
                'jarque_bera': {'statistic': jb_stat, 'pvalue': jb_pvalue, 'is_normal': jb_pvalue > 0.05},
                'dagostino': {'statistic': da_stat, 'pvalue': da_pvalue, 'is_normal': da_pvalue > 0.05},
                'kolmogorov_smirnov': {'statistic': ks_stat, 'pvalue': ks_pvalue, 'is_normal': ks_pvalue > 0.05},
                'skewness': skewness,
                'kurtosis': kurtosis,
                'heavy_tails': heavy_tails,
                'is_non_normal': jb_pvalue < 0.01 and da_pvalue < 0.01  # Fuertemente no-normal
            }
        except Exception as e:
            logger.error(f"Error en tests de distribución: {e}")
            return {'jarque_bera': {}, 'dagostino': {}, 'kolmogorov_smirnov': {}, 'skewness': 0, 'kurtosis': 0, 'heavy_tails': False, 'is_non_normal': False}
    
    def _detect_extreme_regimes(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Detecta regímenes extremos de mercado"""
        try:
            prices = market_data['close']
            returns = np.diff(np.log(prices))
            
            # Detectar crashes (caídas extremas)
            daily_returns = pd.Series(returns)
            crash_threshold = daily_returns.quantile(0.01)  # 1% más bajo
            crashes = daily_returns < crash_threshold
            
            # Detectar burbujas (subidas extremas)
            bubble_threshold = daily_returns.quantile(0.99)  # 1% más alto
            bubbles = daily_returns > bubble_threshold
            
            # Detectar períodos de pánico (alta volatilidad + retornos negativos)
            vol_window = min(10, len(returns) // 5)
            rolling_vol = daily_returns.rolling(window=vol_window).std()
            high_vol_threshold = rolling_vol.quantile(0.9)
            
            panic_periods = (rolling_vol > high_vol_threshold) & (daily_returns < 0)
            
            # Detectar estancamiento (baja volatilidad prolongada)
            low_vol_threshold = rolling_vol.quantile(0.1)
            stagnation_periods = rolling_vol < low_vol_threshold
            stagnation_persistence = self._calculate_persistence(stagnation_periods)
            
            return {
                'crashes_detected': crashes.sum(),
                'bubbles_detected': bubbles.sum(),
                'panic_periods': panic_periods.sum(),
                'stagnation_persistence': stagnation_persistence,
                'extreme_events_ratio': (crashes.sum() + bubbles.sum()) / len(returns),
                'has_extreme_regimes': (crashes.sum() + bubbles.sum()) > len(returns) * 0.05
            }
        except Exception as e:
            logger.error(f"Error en detección de regímenes extremos: {e}")
            return {'crashes_detected': 0, 'bubbles_detected': 0, 'panic_periods': 0, 'stagnation_persistence': 0, 'extreme_events_ratio': 0, 'has_extreme_regimes': False}
    
    def _analyze_autocorrelation(self, returns: np.ndarray) -> Dict[str, Any]:
        """Analiza autocorrelación y dependencia temporal"""
        try:
            # Autocorrelación de retornos
            returns_autocorr = np.corrcoef(returns[:-1], returns[1:])[0, 1] if len(returns) > 1 else 0
            
            # Autocorrelación de retornos al cuadrado (volatility clustering)
            squared_returns = returns**2
            vol_autocorr = np.corrcoef(squared_returns[:-1], squared_returns[1:])[0, 1] if len(squared_returns) > 1 else 0
            
            # Test de independencia (Ljung-Box aproximado)
            from scipy.stats import chi2
            n = len(returns)
            lags = min(10, n // 4)
            
            # Calcular estadístico Q aproximado
            autocorrs = [np.corrcoef(returns[:-i], returns[i:])[0, 1] for i in range(1, lags+1)]
            q_stat = n * (n + 2) * sum([(autocorrs[i]**2) / (n - i - 1) for i in range(lags)])
            q_pvalue = 1 - chi2.cdf(q_stat, lags)
            
            return {
                'returns_autocorr': returns_autocorr,
                'volatility_autocorr': vol_autocorr,
                'ljung_box_stat': q_stat,
                'ljung_box_pvalue': q_pvalue,
                'has_serial_correlation': q_pvalue < 0.05,
                'volatility_clustering': vol_autocorr > 0.1
            }
        except Exception as e:
            logger.error(f"Error en análisis de autocorrelación: {e}")
            return {'returns_autocorr': 0, 'volatility_autocorr': 0, 'ljung_box_stat': 0, 'ljung_box_pvalue': 1, 'has_serial_correlation': False, 'volatility_clustering': False}
    
    def _calculate_persistence(self, binary_series: pd.Series) -> float:
        """Calcula persistencia de una serie binaria"""
        try:
            if len(binary_series) == 0:
                return 0.0
            
            # Encontrar runs (secuencias consecutivas de True)
            runs = []
            current_run = 0
            
            for value in binary_series:
                if value:
                    current_run += 1
                else:
                    if current_run > 0:
                        runs.append(current_run)
                        current_run = 0
            
            if current_run > 0:
                runs.append(current_run)
            
            # Calcular persistencia promedio
            return np.mean(runs) if runs else 0.0
            
        except Exception as e:
            logger.error(f"Error calculando persistencia: {e}")
            return 0.0
    
    def _calculate_extremity_score(self, stationarity_results: Dict, structural_changes: Dict,
                                 volatility_analysis: Dict, distribution_tests: Dict,
                                 extreme_regimes: Dict, autocorr_analysis: Dict) -> float:
        """Calcula score de extremidad combinando todos los indicadores"""
        try:
            score = 0.0
            
            # Peso por no-estacionariedad (20%)
            if not stationarity_results.get('adf_test', {}).get('is_stationary', True):
                score += 0.1
            if not stationarity_results.get('kpss_test', {}).get('is_stationary', True):
                score += 0.1
            
            # Peso por cambios estructurales (25%)
            if structural_changes.get('has_structural_changes', False):
                score += 0.15
            score += min(0.1, structural_changes.get('change_intensity', 0) * 2)
            
            # Peso por volatilidad extrema (20%)
            if volatility_analysis.get('is_extreme_volatility', False):
                score += 0.1
            score += min(0.1, volatility_analysis.get('spike_intensity', 0) * 2)
            
            # Peso por propiedades de distribución (15%)
            if distribution_tests.get('is_non_normal', False):
                score += 0.075
            if distribution_tests.get('heavy_tails', False):
                score += 0.075
            
            # Peso por regímenes extremos (15%)
            if extreme_regimes.get('has_extreme_regimes', False):
                score += 0.075
            score += min(0.075, extreme_regimes.get('extreme_events_ratio', 0) * 3)
            
            # Peso por autocorrelación (5%)
            if autocorr_analysis.get('has_serial_correlation', False):
                score += 0.025
            if autocorr_analysis.get('volatility_clustering', False):
                score += 0.025
            
            return min(1.0, score)  # Normalizar a [0, 1]
            
        except Exception as e:
            logger.error(f"Error calculando score de extremidad: {e}")
            return 0.0
    
    def _generate_recommendations(self, extremity_score: float) -> List[str]:
        """Genera recomendaciones basadas en el score de extremidad"""
        recommendations = []
        
        if extremity_score > 0.9:
            recommendations.extend([
                "ALERTA MÁXIMA: Condiciones de mercado extremadamente no-estacionarias",
                "Suspender trading automático y revisar modelos",
                "Implementar gestión de riesgo defensiva",
                "Considerar hedging o posiciones neutrales"
            ])
        elif extremity_score > 0.7:
            recommendations.extend([
                "ALERTA ALTA: Condiciones de mercado altamente volátiles",
                "Reducir tamaños de posición significativamente",
                "Aumentar frecuencia de rebalanceo",
                "Monitorear indicadores de riesgo continuamente"
            ])
        elif extremity_score > 0.5:
            recommendations.extend([
                "PRECAUCIÓN: Condiciones de mercado inestables",
                "Reducir exposición moderadamente",
                "Aumentar diversificación",
                "Revisar stop-losses y take-profits"
            ])
        else:
            recommendations.extend([
                "Condiciones de mercado relativamente estables",
                "Mantener estrategia normal con monitoreo",
                "Aprovechar oportunidades de trading"
            ])
        
        return recommendations
    
    def _log_extreme_event(self, results: Dict[str, Any]):
        """Registra evento extremo en el historial"""
        event = {
            'timestamp': results['timestamp'],
            'extremity_score': results['extremity_score'],
            'key_indicators': {
                'structural_changes': results['structural_changes']['has_structural_changes'],
                'extreme_volatility': results['volatility_analysis']['is_extreme_volatility'],
                'extreme_regimes': results['extreme_regimes']['has_extreme_regimes'],
                'non_normal_distribution': results['distribution_tests']['is_non_normal']
            }
        }
        
        self.extreme_events_history.append(event)
        
        # Mantener solo los últimos 100 eventos
        if len(self.extreme_events_history) > 100:
            self.extreme_events_history = self.extreme_events_history[-100:]
        
        logger.warning(f"Evento extremo registrado: Score {results['extremity_score']:.3f}")
    
    def _create_default_result(self) -> Dict[str, Any]:
        """Crea resultado por defecto en caso de error"""
        return {
            'timestamp': datetime.now().isoformat(),
            'extremity_score': 0.0,
            'is_extreme': False,
            'stationarity_tests': {},
            'structural_changes': {},
            'volatility_analysis': {},
            'distribution_tests': {},
            'extreme_regimes': {},
            'autocorrelation_analysis': {},
            'recommendations': ["Error en análisis - usar configuración conservadora"]
        }

class RegimeClassifier:
    """
    Módulo 2: Clasificador de Regímenes
    
    Analiza el estado del mapa causal y los datos de mercado para clasificar
    la "personalidad" actual del mercado en regímenes discretos.
    """
    
    def __init__(self, n_regimes: int = N_REGIMES):
        """
        Inicializa el clasificador de regímenes.
        
        Args:
            n_regimes: Número de regímenes a identificar
        """
        self.n_regimes = n_regimes
        self.scaler = StandardScaler()
        self.kmeans = KMeans(n_clusters=n_regimes, random_state=42, n_init=10)
        self.pca = PCA(n_components=0.95)  # Mantener 95% de la varianza
        self.is_fitted = False
        self.regime_labels = {}
        self.feature_importance = {}
        
        # Inicializar detector de no-estacionariedad extrema
        self.extreme_detector = ExtremeNonStationarityDetector()
        
        # Definir nombres descriptivos para los regímenes
        self.regime_names = {
            0: "Lateral/Consolidación",
            1: "Tendencia Alcista",
            2: "Tendencia Bajista", 
            3: "Alta Volatilidad/Pánico"
        }
        
        # Directorio para guardar modelos
        self.models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
        os.makedirs(self.models_dir, exist_ok=True)
    
    def calculate_market_features(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula características para la clasificación de regímenes.
        
        Args:
            market_data: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con características calculadas
        """
        try:
            logger.info("Calculando características de mercado...")
            
            df = market_data.copy()
            
            # Debug: verificar tipos de datos
            logger.info(f"Tipos de datos originales: {df.dtypes}")
            logger.info(f"Tipo de índice: {type(df.index)}")
            
            # Normalizar nombres de columnas a minúsculas para compatibilidad
            df.columns = df.columns.str.lower()
            
            # Eliminar columnas duplicadas
            df = df.loc[:, ~df.columns.duplicated()]
            
            # Debug: verificar tipos después de normalizar columnas
            logger.info(f"Tipos después de normalizar: {df.dtypes}")
            logger.info(f"Columnas disponibles: {list(df.columns)}")
            
            # Asegurar que tenemos las columnas necesarias
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                logger.error(f"Columnas faltantes: {missing_cols}")
                return pd.DataFrame()
            
            # Determinar ventanas adaptativas según la cantidad de datos
            data_length = len(df)
            window_small = min(5, data_length // 4)
            window_medium = min(20, data_length // 2)
            window_large = min(50, data_length - 1)
            
            logger.info(f"Datos disponibles: {data_length}, Ventanas: {window_small}, {window_medium}, {window_large}")
            
            # 1. Características de Volatilidad
            logger.info("Calculando volatilidad...")
            df['returns'] = df['close'].pct_change()
            if window_small > 0:
                df['volatility_5'] = df['returns'].rolling(window=window_small).std()
            if window_medium > 0:
                df['volatility_20'] = df['returns'].rolling(window=window_medium).std()
            if window_large > 0:
                df['volatility_50'] = df['returns'].rolling(window=window_large).std()
            
            # 2. Características de Momentum
            logger.info("Calculando momentum...")
            if window_small > 0:
                df['momentum_5'] = df['close'].pct_change(periods=window_small)
            if window_medium > 0:
                df['momentum_20'] = df['close'].pct_change(periods=window_medium)
            if window_large > 0:
                df['momentum_50'] = df['close'].pct_change(periods=window_large)
            
            # 3. Características de Tendencia
            logger.info("Calculando tendencia...")
            try:
                if window_medium > 0:
                    logger.info(f"Calculando SMA {window_medium}...")
                    df['sma_20'] = df['close'].rolling(window=window_medium).mean()
                    logger.info("SMA 20 calculada exitosamente")
                    logger.info(f"Tipo close: {df['close'].dtype}")
                    logger.info(f"Tipo sma_20: {type(df['sma_20'])}")
                    logger.info(f"Primeros valores close: {df['close'].head()}")
                    logger.info(f"Primeros valores sma_20: {df['sma_20'].head()}")
                    
                    # Asegurar que sma_20 es una Serie
                    if hasattr(df['sma_20'], 'values'):
                        sma_20_values = df['sma_20'].values
                    else:
                        sma_20_values = df['sma_20']
                    
                    df['trend_strength'] = (df['close'] - sma_20_values) / sma_20_values
                    logger.info("Trend strength calculada exitosamente")
                if window_large > 0:
                    logger.info(f"Calculando SMA {window_large}...")
                    df['sma_50'] = df['close'].rolling(window=window_large).mean()
                    logger.info("SMA 50 calculada exitosamente")
            except Exception as e:
                logger.error(f"Error en cálculo de tendencia: {e}")
                raise
            
            # Dirección de tendencia solo si tenemos ambas SMAs
            if 'sma_20' in df.columns and 'sma_50' in df.columns:
                logger.info("Calculando dirección de tendencia...")
                logger.info(f"Tipo sma_20: {df['sma_20'].dtype}")
                logger.info(f"Tipo sma_50: {df['sma_50'].dtype}")
                logger.info(f"Primeros valores sma_20: {df['sma_20'].head()}")
                logger.info(f"Primeros valores sma_50: {df['sma_50'].head()}")
                df['trend_direction'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
            else:
                df['trend_direction'] = 0
            
            # 4. Características de Volumen
            logger.info("Calculando volumen...")
            if window_medium > 0:
                df['volume_sma'] = df['volume'].rolling(window=window_medium).mean()
                df['volume_ratio'] = df['volume'] / df['volume_sma']
            if window_small > 0:
                df['volume_trend'] = df['volume'].pct_change(periods=window_small)
            
            # 5. Características de Rango de Precios
            logger.info("Calculando rango de precios...")
            # Asegurar tipos numéricos para el cálculo del true range
            high_num = df['high'].astype(float)
            low_num = df['low'].astype(float)
            close_num = df['close'].astype(float)
            
            df['true_range'] = np.maximum(
                high_num - low_num,
                np.maximum(
                    abs(high_num - close_num.shift(1)),
                    abs(low_num - close_num.shift(1))
                )
            )
            df['atr'] = df['true_range'].rolling(window=14).mean()
            df['price_range'] = (df['high'] - df['low']) / df['close']
            
            # 6. Características de Gaps
            logger.info("Calculando gaps...")
            df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
            df['gap_magnitude'] = abs(df['gap'])
            
            # 7. Características de Patrones de Velas
            logger.info("Calculando patrones de velas...")
            df['body_size'] = abs(df['close'] - df['open']) / df['close']
            
            # Asegurar que los datos son numéricos antes de usar np.maximum/minimum
            df_numeric = df[['open', 'high', 'low', 'close']].astype(float)
            df['upper_shadow'] = (df_numeric['high'] - np.maximum(df_numeric['open'], df_numeric['close'])) / df_numeric['close']
            df['lower_shadow'] = (np.minimum(df_numeric['open'], df_numeric['close']) - df_numeric['low']) / df_numeric['close']
            
            # 8. Características de Momentum Avanzado
            logger.info("Calculando momentum avanzado...")
            df['rsi'] = self._calculate_rsi(df['close'])
            df['macd'], df['macd_signal'] = self._calculate_macd(df['close'])
            
            # 9. Características de Bollinger Bands
            logger.info("Calculando Bollinger Bands...")
            df['bb_position'] = self._calculate_bollinger_position(df['close'])
            
            # 10. Características de Correlación con Volumen
            logger.info("Calculando correlación precio-volumen...")
            df['price_volume_corr'] = df['returns'].rolling(window=20).corr(df['volume_trend'])
            
            # 11. Características de Estacionalidad (hora del día, día de la semana)
            logger.info("Calculando características de estacionalidad...")
            if hasattr(df.index, 'hour'):
                df['hour'] = df.index.hour
                df['day_of_week'] = df.index.dayofweek
            else:
                df['hour'] = 0
                df['day_of_week'] = 0
            
            logger.info("Seleccionando características finales...")
            # Seleccionar características finales
            feature_columns = [
                'volatility_5', 'volatility_20', 'volatility_50',
                'momentum_5', 'momentum_20', 'momentum_50',
                'trend_strength', 'trend_direction',
                'volume_ratio', 'volume_trend',
                'atr', 'price_range',
                'gap_magnitude',
                'body_size', 'upper_shadow', 'lower_shadow',
                'rsi', 'macd', 'bb_position',
                'price_volume_corr',
                'hour', 'day_of_week'
            ]
            
            # Filtrar características que existen
            available_features = [col for col in feature_columns if col in df.columns]
            features_df = df[available_features].copy()
            
            logger.info("Eliminando valores NaN...")
            # Eliminar filas con NaN
            features_df = features_df.dropna()
            
            logger.info(f"Características calculadas: {len(available_features)} features, {len(features_df)} muestras")
            
            return features_df
            
        except Exception as e:
            logger.error(f"Error calculando características de mercado: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calcula el RSI (Relative Strength Index)."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Calcula MACD y su señal."""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9).mean()
        return macd, macd_signal
    
    def _calculate_bollinger_position(self, prices: pd.Series, window: int = 20) -> pd.Series:
        """Calcula la posición dentro de las Bandas de Bollinger."""
        sma = prices.rolling(window=window).mean()
        std = prices.rolling(window=window).std()
        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)
        bb_position = (prices - lower_band) / (upper_band - lower_band)
        return bb_position
    
    def classify_regimes(self, market_data: pd.DataFrame, 
                        causal_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Clasifica los datos de mercado en diferentes regímenes usando K-Means.
        
        Args:
            market_data: DataFrame con datos de mercado
            causal_data: DataFrame con datos del grafo causal (opcional)
            
        Returns:
            DataFrame con regímenes clasificados
        """
        try:
            logger.info("Iniciando clasificación de regímenes...")
            
            # Calcular características de mercado
            features = self.calculate_market_features(market_data)
            
            if len(features) == 0:
                logger.error("No se pudieron calcular características")
                return pd.DataFrame()
            
            # Agregar características del grafo causal si están disponibles
            if causal_data is not None and len(causal_data) > 0:
                causal_features = self._extract_causal_features(causal_data, features.index)
                features = pd.concat([features, causal_features], axis=1)
            
            # Escalar características
            features_scaled = self.scaler.fit_transform(features)
            
            # Aplicar PCA para reducir dimensionalidad
            features_pca = self.pca.fit_transform(features_scaled)
            
            # Encontrar número óptimo de clusters si no está especificado
            if not self.is_fitted:
                optimal_k = self._find_optimal_clusters(features_pca)
                if optimal_k != self.n_regimes:
                    logger.info(f"Número óptimo de clusters: {optimal_k}, usando: {self.n_regimes}")
            
            # Aplicar K-Means
            regime_labels = self.kmeans.fit_predict(features_pca)
            
            # Crear DataFrame de resultados
            results = features.copy()
            results['regime'] = regime_labels
            results['regime_name'] = [self.regime_names.get(r, f"Régimen {r}") for r in regime_labels]
            
            # Calcular estadísticas por régimen
            regime_stats = self._calculate_regime_statistics(results)
            
            # Guardar modelo y estadísticas
            self._save_model_and_stats(regime_stats)
            
            self.is_fitted = True
            
            logger.info(f"Clasificación completada: {len(results)} muestras en {self.n_regimes} regímenes")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en clasificación de regímenes: {str(e)}")
            return pd.DataFrame()
    
    def _extract_causal_features(self, causal_data: pd.DataFrame, 
                                market_index: pd.Index) -> pd.DataFrame:
        """
        Extrae características del grafo causal para cada período de tiempo.
        
        Args:
            causal_data: DataFrame con relaciones causales
            market_index: Índice temporal del mercado
            
        Returns:
            DataFrame con características causales
        """
        try:
            # Características básicas del grafo causal
            causal_features = pd.DataFrame(index=market_index)
            
            # Número total de relaciones
            causal_features['causal_relations_count'] = len(causal_data)
            
            # Peso promedio de las relaciones
            causal_features['causal_avg_weight'] = causal_data['weight'].mean() if len(causal_data) > 0 else 0
            
            # Sentimiento promedio
            causal_features['causal_avg_sentiment'] = causal_data['avg_sentiment'].mean() if len(causal_data) > 0 else 0
            
            # Número de entidades únicas
            if len(causal_data) > 0:
                unique_entities = set(causal_data['entity1'].tolist() + causal_data['entity2'].tolist())
                causal_features['causal_unique_entities'] = len(unique_entities)
            else:
                causal_features['causal_unique_entities'] = 0
            
            # Densidad del grafo (relaciones / entidades posibles)
            n_entities = causal_features['causal_unique_entities'].iloc[0]
            max_relations = n_entities * (n_entities - 1) / 2 if n_entities > 1 else 1
            causal_features['causal_density'] = causal_features['causal_relations_count'] / max_relations
            
            return causal_features
            
        except Exception as e:
            logger.error(f"Error extrayendo características causales: {str(e)}")
            return pd.DataFrame(index=market_index)
    
    def _find_optimal_clusters(self, features: np.ndarray, max_k: int = 8) -> int:
        """
        Encuentra el número óptimo de clusters usando el método del codo y silhouette score.
        
        Args:
            features: Array de características
            max_k: Número máximo de clusters a probar
            
        Returns:
            Número óptimo de clusters
        """
        try:
            inertias = []
            silhouette_scores = []
            k_range = range(2, min(max_k + 1, len(features) // 10))
            
            for k in k_range:
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(features)
                
                inertias.append(kmeans.inertia_)
                silhouette_scores.append(silhouette_score(features, labels))
            
            # Encontrar el codo en la curva de inercia
            if len(inertias) >= 2:
                # Calcular la segunda derivada para encontrar el codo
                second_derivatives = []
                for i in range(1, len(inertias) - 1):
                    second_deriv = inertias[i-1] - 2*inertias[i] + inertias[i+1]
                    second_derivatives.append(second_deriv)
                
                if second_derivatives:
                    elbow_idx = np.argmax(second_derivatives) + 1
                    optimal_k_elbow = list(k_range)[elbow_idx]
                else:
                    optimal_k_elbow = self.n_regimes
            else:
                optimal_k_elbow = self.n_regimes
            
            # Encontrar el mejor silhouette score
            if silhouette_scores:
                best_silhouette_idx = np.argmax(silhouette_scores)
                optimal_k_silhouette = list(k_range)[best_silhouette_idx]
            else:
                optimal_k_silhouette = self.n_regimes
            
            # Combinar ambos métodos (dar más peso al silhouette score)
            if abs(optimal_k_silhouette - optimal_k_elbow) <= 1:
                optimal_k = optimal_k_silhouette
            else:
                optimal_k = optimal_k_silhouette
            
            logger.info(f"Análisis de clusters - Codo: {optimal_k_elbow}, Silhouette: {optimal_k_silhouette}, Elegido: {optimal_k}")
            
            return optimal_k
            
        except Exception as e:
            logger.error(f"Error encontrando clusters óptimos: {str(e)}")
            return self.n_regimes
    
    def _calculate_regime_statistics(self, results: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcula estadísticas descriptivas para cada régimen.
        
        Args:
            results: DataFrame con regímenes clasificados
            
        Returns:
            Diccionario con estadísticas por régimen
        """
        try:
            regime_stats = {}
            
            for regime in range(self.n_regimes):
                regime_data = results[results['regime'] == regime]
                
                if len(regime_data) == 0:
                    continue
                
                stats = {
                    'name': self.regime_names.get(regime, f"Régimen {regime}"),
                    'count': len(regime_data),
                    'percentage': len(regime_data) / len(results) * 100,
                    'avg_volatility': regime_data.get('volatility_20', pd.Series([0])).mean(),
                    'avg_momentum': regime_data.get('momentum_20', pd.Series([0])).mean(),
                    'avg_volume_ratio': regime_data.get('volume_ratio', pd.Series([1])).mean(),
                    'avg_rsi': regime_data.get('rsi', pd.Series([50])).mean()
                }
                
                regime_stats[regime] = stats
            
            return regime_stats
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas de regímenes: {str(e)}")
            return {}
    
    def _save_model_and_stats(self, regime_stats: Dict[str, Any]):
        """
        Guarda el modelo entrenado y las estadísticas.
        
        Args:
            regime_stats: Estadísticas de los regímenes
        """
        try:
            # Guardar modelo de K-Means
            model_path = os.path.join(self.models_dir, "regime_classifier.joblib")
            joblib.dump({
                'kmeans': self.kmeans,
                'scaler': self.scaler,
                'pca': self.pca,
                'n_regimes': self.n_regimes,
                'regime_names': self.regime_names
            }, model_path)
            
            # Guardar estadísticas
            stats_path = os.path.join(self.models_dir, "regime_statistics.json")
            stats_to_save = {
                'regime_stats': regime_stats,
                'model_info': {
                    'n_regimes': self.n_regimes,
                    'trained_at': datetime.now().isoformat(),
                    'model_type': 'KMeans'
                }
            }
            
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats_to_save, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Modelo guardado en {model_path}")
            logger.info(f"Estadísticas guardadas en {stats_path}")
            
        except Exception as e:
            logger.error(f"Error guardando modelo: {str(e)}")
    
    def predict_regime(self, market_features: pd.DataFrame) -> int:
        """
        Predice el régimen para nuevos datos de mercado.
        
        Args:
            market_features: DataFrame con características de mercado
            
        Returns:
            Etiqueta del régimen predicho
        """
        try:
            if not self.is_fitted:
                logger.error("El modelo no ha sido entrenado")
                return 0
            
            # Escalar características
            features_scaled = self.scaler.transform(market_features)
            
            # Aplicar PCA
            features_pca = self.pca.transform(features_scaled)
            
            # Predecir régimen
            regime = self.kmeans.predict(features_pca)[0]
            
            return regime
            
        except Exception as e:
            logger.error(f"Error prediciendo régimen: {str(e)}")
            return 0
    
    def load_model(self, model_path: str = None) -> bool:
        """
        Carga un modelo previamente entrenado.
        
        Args:
            model_path: Ruta al archivo del modelo
            
        Returns:
            True si se cargó exitosamente, False en caso contrario
        """
        try:
            if model_path is None:
                model_path = os.path.join(self.models_dir, "regime_classifier.joblib")
            
            if not os.path.exists(model_path):
                logger.warning(f"Archivo de modelo no encontrado: {model_path}")
                return False
            
            model_data = joblib.load(model_path)
            
            self.kmeans = model_data['kmeans']
            self.scaler = model_data['scaler']
            self.pca = model_data['pca']
            self.n_regimes = model_data['n_regimes']
            self.regime_names = model_data['regime_names']
            self.is_fitted = True
            
            logger.info(f"Modelo cargado exitosamente desde {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {str(e)}")
            return False
    
    def analyze_multi_timeframe_regimes(self, multi_data: dict, causal_state: dict = None) -> dict:
        """
        Analiza regímenes en múltiples timeframes.
        
        Args:
            multi_data: Diccionario con datos de múltiples timeframes
            causal_state: Estado del mapa causal (opcional)
            
        Returns:
            Diccionario con análisis de regímenes por timeframe
        """
        logger.info("🔄 Iniciando análisis multi-timeframe de regímenes...")
        
        multi_regime_analysis = {}
        
        for timeframe, data in multi_data.items():
            try:
                logger.info(f"⏱️ Analizando régimen en {timeframe}...")
                
                # Calcular características para este timeframe
                features = self.calculate_market_features(data)
                
                if features.empty:
                    logger.warning(f"⚠️ No se pudieron calcular características para {timeframe}")
                    continue
                
                # Predecir régimen
                if self.is_fitted:
                    # Adaptar predict_regime para devolver diccionario completo
                    regime_num = self.predict_regime(features)
                    regime_prediction = {
                        'current_regime': regime_num,
                        'regime_name': self.regime_names.get(regime_num, f'Régimen {regime_num}'),
                        'confidence': 0.8  # Valor por defecto, se puede mejorar
                    }
                    
                    # Análisis adicional específico del timeframe
                    regime_analysis = self._analyze_timeframe_regime(
                        timeframe, data, features, regime_prediction
                    )
                    
                    multi_regime_analysis[timeframe] = regime_analysis
                    logger.info(f"✅ {timeframe}: Régimen {regime_prediction['current_regime']} - {regime_prediction['regime_name']}")
                    
                else:
                    logger.warning(f"⚠️ Modelo no entrenado, entrenando con datos de {timeframe}...")
                    # Entrenar con datos actuales
                    self.classify_regimes(data)
                    regime_num = self.predict_regime(features)
                    regime_prediction = {
                        'current_regime': regime_num,
                        'regime_name': self.regime_names.get(regime_num, f'Régimen {regime_num}'),
                        'confidence': 0.8
                    }
                    
                    regime_analysis = self._analyze_timeframe_regime(
                        timeframe, data, features, regime_prediction
                    )
                    
                    multi_regime_analysis[timeframe] = regime_analysis
                    
            except Exception as e:
                logger.error(f"❌ Error analizando {timeframe}: {str(e)}")
                continue
        
        # Análisis de consenso entre timeframes
        consensus_analysis = self._calculate_regime_consensus(multi_regime_analysis)
        
        result = {
            'timeframe_analysis': multi_regime_analysis,
            'consensus': consensus_analysis,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"🎯 Análisis multi-timeframe completado: {len(multi_regime_analysis)} timeframes")
        return result
    
    def _analyze_timeframe_regime(self, timeframe: str, data: pd.DataFrame, 
                                features: pd.DataFrame, regime_prediction: dict) -> dict:
        """
        Análisis específico del régimen para un timeframe.
        
        Args:
            timeframe: Timeframe analizado
            data: Datos de mercado
            features: Características calculadas
            regime_prediction: Predicción del régimen
            
        Returns:
            Diccionario con análisis detallado
        """
        try:
            # Calcular métricas específicas del timeframe
            latest_data = data.tail(10)  # Últimas 10 barras
            
            # Normalizar nombres de columnas
            latest_data.columns = latest_data.columns.str.lower()
            
            # Tendencia
            price_change = (latest_data['close'].iloc[-1] - latest_data['close'].iloc[0]) / latest_data['close'].iloc[0]
            
            # Volatilidad reciente
            recent_volatility = latest_data['close'].pct_change().std()
            
            # Volumen promedio
            avg_volume = latest_data['volume'].mean()
            
            # Momentum
            momentum = self._calculate_momentum(latest_data)
            
            # Fuerza del régimen (confianza)
            regime_strength = regime_prediction.get('confidence', 0.5)
            
            analysis = {
                'timeframe': timeframe,
                'regime': regime_prediction['current_regime'],
                'regime_name': regime_prediction['regime_name'],
                'confidence': regime_prediction['confidence'],
                'regime_strength': regime_strength,
                'price_change_pct': price_change * 100,
                'recent_volatility': recent_volatility,
                'avg_volume': avg_volume,
                'momentum': momentum,
                'trend_direction': 'alcista' if price_change > 0.01 else 'bajista' if price_change < -0.01 else 'lateral',
                'volatility_level': 'alta' if recent_volatility > 0.03 else 'media' if recent_volatility > 0.015 else 'baja'
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error en análisis de timeframe {timeframe}: {str(e)}")
            return {
                'timeframe': timeframe,
                'regime': regime_prediction.get('current_regime', 0),
                'regime_name': regime_prediction.get('regime_name', 'Desconocido'),
                'confidence': 0.5,
                'error': str(e)
            }
    
    def _calculate_momentum(self, data: pd.DataFrame) -> float:
        """
        Calcula el momentum del precio.
        
        Args:
            data: Datos de mercado
            
        Returns:
            Valor de momentum
        """
        try:
            if len(data) < 5:
                return 0.0
            
            # Momentum simple: diferencia entre medias móviles corta y larga
            short_ma = data['close'].tail(3).mean()
            long_ma = data['close'].tail(7).mean() if len(data) >= 7 else data['close'].mean()
            
            momentum = (short_ma - long_ma) / long_ma if long_ma != 0 else 0.0
            return momentum
            
        except Exception:
            return 0.0
    
    def _calculate_regime_consensus(self, multi_regime_analysis: dict) -> dict:
        """
        Calcula el consenso entre regímenes de diferentes timeframes.
        
        Args:
            multi_regime_analysis: Análisis de regímenes por timeframe
            
        Returns:
            Diccionario con análisis de consenso
        """
        if not multi_regime_analysis:
            return {'consensus_regime': 0, 'consensus_strength': 0.0, 'agreement_level': 'bajo'}
        
        # Extraer regímenes y confianzas
        regimes = []
        confidences = []
        timeframe_weights = {
            '45m': 0.15,  # Peso menor para timeframes cortos
            '1h': 0.25,
            '3h': 0.35,
            '4h': 0.25    # Peso mayor para timeframes largos
        }
        
        for tf, analysis in multi_regime_analysis.items():
            if 'regime' in analysis:
                regimes.append(analysis['regime'])
                confidences.append(analysis.get('confidence', 0.5))
        
        if not regimes:
            return {'consensus_regime': 0, 'consensus_strength': 0.0, 'agreement_level': 'bajo'}
        
        # Calcular régimen de consenso (moda ponderada)
        regime_counts = {}
        for i, regime in enumerate(regimes):
            tf = list(multi_regime_analysis.keys())[i]
            weight = timeframe_weights.get(tf, 0.25)
            confidence = confidences[i]
            
            if regime not in regime_counts:
                regime_counts[regime] = 0
            regime_counts[regime] += weight * confidence
        
        # Régimen con mayor peso
        consensus_regime = max(regime_counts, key=regime_counts.get)
        
        # Calcular fuerza del consenso
        total_weight = sum(regime_counts.values())
        consensus_strength = regime_counts[consensus_regime] / total_weight if total_weight > 0 else 0.0
        
        # Nivel de acuerdo
        unique_regimes = len(set(regimes))
        if unique_regimes == 1:
            agreement_level = 'alto'
        elif unique_regimes == 2:
            agreement_level = 'medio'
        else:
            agreement_level = 'bajo'
        
        # Análisis de divergencias
        divergences = []
        for tf, analysis in multi_regime_analysis.items():
            if analysis.get('regime') != consensus_regime:
                divergences.append({
                    'timeframe': tf,
                    'regime': analysis.get('regime'),
                    'regime_name': analysis.get('regime_name')
                })
        
        consensus = {
            'consensus_regime': consensus_regime,
            'consensus_regime_name': self.regime_names.get(consensus_regime, f'Régimen {consensus_regime}'),
            'consensus_strength': consensus_strength,
            'agreement_level': agreement_level,
            'unique_regimes': unique_regimes,
            'divergences': divergences,
            'regime_distribution': regime_counts
        }
        
        logger.info(f"🎯 Consenso: Régimen {consensus_regime} ({agreement_level} acuerdo, {consensus_strength:.2f} fuerza)")
        
        return consensus
 
def main():
    """Función principal para probar el clasificador de regímenes."""
    # Crear datos de ejemplo
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=1000, freq='4H')
    
    # Simular datos de mercado con diferentes regímenes
    price = 100
    prices = []
    volumes = []
    
    for i in range(len(dates)):
        # Simular diferentes regímenes
        if i < 250:  # Régimen lateral
            change = np.random.normal(0, 0.01)
            volume = np.random.normal(1000, 200)
        elif i < 500:  # Régimen alcista
            change = np.random.normal(0.005, 0.015)
            volume = np.random.normal(1500, 300)
        elif i < 750:  # Régimen bajista
            change = np.random.normal(-0.005, 0.015)
            volume = np.random.normal(1200, 250)
        else:  # Régimen volátil
            change = np.random.normal(0, 0.03)
            volume = np.random.normal(2000, 500)
        
        price *= (1 + change)
        prices.append(price)
        volumes.append(max(volume, 100))
    
    # Crear DataFrame de mercado
    market_data = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'close': prices,
        'volume': volumes
    }, index=dates)
    
    # Crear clasificador y entrenar
    classifier = RegimeClassifier(n_regimes=4)
    
    logger.info("Ejecutando ejemplo del Clasificador de Regímenes...")
    results = classifier.classify_regimes(market_data)
    
    if len(results) > 0:
        print("\n=== CLASIFICACIÓN DE REGÍMENES ===")
        print(f"Total de muestras: {len(results)}")
        
        # Mostrar distribución de regímenes
        regime_counts = results['regime'].value_counts().sort_index()
        print(f"\n=== DISTRIBUCIÓN DE REGÍMENES ===")
        for regime, count in regime_counts.items():
            regime_name = classifier.regime_names.get(regime, f"Régimen {regime}")
            percentage = count / len(results) * 100
            print(f"{regime_name}: {count} muestras ({percentage:.1f}%)")
        
        # Mostrar últimos regímenes
        print(f"\n=== ÚLTIMOS 10 REGÍMENES ===")
        recent = results[['regime', 'regime_name']].tail(10)
        for idx, row in recent.iterrows():
            print(f"{idx}: {row['regime_name']}")
        
        print(f"\n✅ Clasificación completada exitosamente")
    else:
        print("❌ Error en la clasificación de regímenes")

if __name__ == '__main__':
    main()