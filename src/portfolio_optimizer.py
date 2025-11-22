"""
Optimizador de Portafolio Multi-Activo - Phase 2
Optimización avanzada de portafolios usando múltiples algoritmos
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum
import json
from scipy.optimize import minimize
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptimizationMethod(Enum):
    """Métodos de optimización disponibles"""
    MARKOWITZ = "markowitz"
    BLACK_LITTERMAN = "black_litterman"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_SHARPE = "maximum_sharpe"
    MAXIMUM_DIVERSIFICATION = "maximum_diversification"
    HIERARCHICAL_RISK_PARITY = "hierarchical_risk_parity"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM_OVERLAY = "momentum_overlay"
    DYNAMIC_ASSET_ALLOCATION = "dynamic_asset_allocation"
    VOLATILITY_WEIGHTED_RISK_PARITY = "volatility_weighted_risk_parity"
    ROBUST_RISK_PARITY = "robust_risk_parity"

class RiskModel(Enum):
    """Modelos de riesgo"""
    HISTORICAL = "historical"
    EXPONENTIAL_WEIGHTED = "exponential_weighted"
    SHRINKAGE = "shrinkage"
    FACTOR_MODEL = "factor_model"

@dataclass
class OptimizationConstraints:
    """Restricciones de optimización"""
    min_weight: float = 0.0
    max_weight: float = 1.0
    max_turnover: Optional[float] = None
    target_return: Optional[float] = None
    max_risk: Optional[float] = None
    sector_limits: Optional[Dict[str, float]] = None
    transaction_costs: float = 0.001

@dataclass
class PortfolioMetrics:
    """Métricas del portafolio optimizado"""
    expected_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float
    cvar_95: float
    diversification_ratio: float
    turnover: float
    total_weight: float

@dataclass
class OptimizationResult:
    """Resultado de la optimización"""
    weights: Dict[str, float]
    metrics: PortfolioMetrics
    method: OptimizationMethod
    success: bool
    message: str
    optimization_time: float
    iterations: int

class PortfolioOptimizer:
    """
    Optimizador avanzado de portafolios multi-activo
    """
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.logger = logging.getLogger(__name__)
        self.risk_free_rate = risk_free_rate
        
        # Parámetros de optimización
        self.lookback_period = 252  # 1 año de datos diarios
        self.rebalance_frequency = 30  # Rebalanceo cada 30 días
        
        # Cache para matrices de covarianza
        self.covariance_cache = {}
        self.returns_cache = {}
        
        # Historial de optimizaciones
        self.optimization_history = []
        
        self.logger.info("✅ PortfolioOptimizer inicializado")
    
    def prepare_data(self, price_data: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Prepara los datos de precios para optimización
        """
        try:
            if not price_data:
                raise ValueError("No hay datos de precios disponibles")
            
            # Combinar datos de precios
            price_df = pd.DataFrame()
            
            for symbol, data in price_data.items():
                if 'close' in data.columns and len(data) > 0:
                    # Usar timestamp como índice si está disponible
                    if 'timestamp' in data.columns:
                        data = data.set_index('timestamp')
                    
                    price_df[symbol] = data['close']
            
            if price_df.empty:
                raise ValueError("No se pudieron extraer precios de cierre")
            
            # Limpiar datos
            price_df = price_df.dropna()
            
            if len(price_df) < 30:
                raise ValueError(f"Datos insuficientes: {len(price_df)} períodos")
            
            # Calcular retornos
            returns_df = price_df.pct_change().dropna()
            
            # Limitar al período de lookback
            if len(returns_df) > self.lookback_period:
                returns_df = returns_df.tail(self.lookback_period)
                price_df = price_df.tail(self.lookback_period + 1)
            
            self.logger.info(f"📊 Datos preparados: {len(returns_df)} períodos, {len(returns_df.columns)} activos")
            
            return price_df, returns_df
            
        except Exception as e:
            self.logger.error(f"❌ Error preparando datos: {e}")
            raise
    
    def calculate_expected_returns(self, returns_df: pd.DataFrame, 
                                 method: str = "historical") -> pd.Series:
        """
        Calcula retornos esperados usando diferentes métodos
        """
        try:
            if method == "historical":
                # Media histórica
                expected_returns = returns_df.mean() * 252  # Anualizar
                
            elif method == "exponential_weighted":
                # Media ponderada exponencialmente
                span = 60  # 60 días
                expected_returns = returns_df.ewm(span=span).mean().iloc[-1] * 252
                
            elif method == "shrinkage":
                # Shrinkage hacia la media del mercado
                historical_mean = returns_df.mean() * 252
                market_mean = historical_mean.mean()
                shrinkage_factor = 0.3
                
                expected_returns = (1 - shrinkage_factor) * historical_mean + \
                                 shrinkage_factor * market_mean
                
            elif method == "capm":
                # CAPM con beta estimado
                market_return = returns_df.mean(axis=1)
                betas = {}
                
                for asset in returns_df.columns:
                    asset_returns = returns_df[asset]
                    covariance = np.cov(asset_returns, market_return)[0, 1]
                    market_variance = np.var(market_return)
                    beta = covariance / market_variance if market_variance > 0 else 1.0
                    betas[asset] = beta
                
                market_premium = market_return.mean() * 252 - self.risk_free_rate
                expected_returns = pd.Series({
                    asset: self.risk_free_rate + beta * market_premium
                    for asset, beta in betas.items()
                })
                
            else:
                # Por defecto: histórico
                expected_returns = returns_df.mean() * 252
            
            self.logger.info(f"📈 Retornos esperados calculados usando método: {method}")
            return expected_returns
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando retornos esperados: {e}")
            return returns_df.mean() * 252  # Fallback
    
    def calculate_covariance_matrix(self, returns_df: pd.DataFrame, 
                                  method: RiskModel = RiskModel.HISTORICAL) -> pd.DataFrame:
        """
        Calcula matriz de covarianza usando diferentes métodos
        """
        try:
            cache_key = f"{method.value}_{len(returns_df)}_{hash(str(returns_df.columns.tolist()))}"
            
            if cache_key in self.covariance_cache:
                return self.covariance_cache[cache_key]
            
            if method == RiskModel.HISTORICAL:
                # Covarianza histórica
                cov_matrix = returns_df.cov() * 252  # Anualizar
                
            elif method == RiskModel.EXPONENTIAL_WEIGHTED:
                # Covarianza ponderada exponencialmente
                cov_matrix = returns_df.ewm(span=60).cov().iloc[-len(returns_df.columns):] * 252
                
            elif method == RiskModel.SHRINKAGE:
                # Shrinkage de Ledoit-Wolf
                sample_cov = returns_df.cov() * 252
                
                # Target: matriz diagonal con varianzas promedio
                avg_variance = np.trace(sample_cov) / len(sample_cov)
                target = np.eye(len(sample_cov)) * avg_variance
                
                # Factor de shrinkage simplificado
                shrinkage_factor = 0.2
                cov_matrix = (1 - shrinkage_factor) * sample_cov + shrinkage_factor * target
                
            elif method == RiskModel.FACTOR_MODEL:
                # Modelo de factores simplificado (factor de mercado)
                market_returns = returns_df.mean(axis=1)
                
                # Calcular betas
                betas = []
                residual_vars = []
                
                for asset in returns_df.columns:
                    asset_returns = returns_df[asset]
                    
                    # Regresión simple
                    covariance = np.cov(asset_returns, market_returns)[0, 1]
                    market_variance = np.var(market_returns)
                    beta = covariance / market_variance if market_variance > 0 else 1.0
                    
                    # Varianza residual
                    predicted_returns = beta * market_returns
                    residuals = asset_returns - predicted_returns
                    residual_var = np.var(residuals)
                    
                    betas.append(beta)
                    residual_vars.append(residual_var)
                
                # Construir matriz de covarianza
                betas = np.array(betas)
                factor_variance = np.var(market_returns)
                
                cov_matrix = np.outer(betas, betas) * factor_variance + np.diag(residual_vars)
                cov_matrix = pd.DataFrame(cov_matrix, 
                                        index=returns_df.columns, 
                                        columns=returns_df.columns) * 252
            
            else:
                # Por defecto: histórica
                cov_matrix = returns_df.cov() * 252
            
            # Asegurar que la matriz sea positiva definida
            eigenvals, eigenvecs = np.linalg.eigh(cov_matrix)
            eigenvals = np.maximum(eigenvals, 1e-8)  # Valores propios mínimos
            cov_matrix = pd.DataFrame(
                eigenvecs @ np.diag(eigenvals) @ eigenvecs.T,
                index=cov_matrix.index,
                columns=cov_matrix.columns
            )
            
            # Guardar en cache
            self.covariance_cache[cache_key] = cov_matrix
            
            self.logger.info(f"📊 Matriz de covarianza calculada usando: {method.value}")
            return cov_matrix
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando matriz de covarianza: {e}")
            # Fallback: matriz diagonal
            return pd.DataFrame(np.diag(returns_df.var() * 252), 
                              index=returns_df.columns, 
                              columns=returns_df.columns)
    
    def optimize_markowitz(self, expected_returns: pd.Series, cov_matrix: pd.DataFrame,
                          constraints: OptimizationConstraints) -> Dict[str, float]:
        """
        Optimización de Markowitz (frontera eficiente)
        """
        try:
            n_assets = len(expected_returns)
            
            # Función objetivo: maximizar Sharpe ratio
            def objective(weights):
                portfolio_return = np.dot(weights, expected_returns)
                portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
                portfolio_std = np.sqrt(portfolio_variance)
                
                if portfolio_std == 0:
                    return -np.inf
                
                sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_std
                return -sharpe_ratio  # Minimizar el negativo
            
            # Restricciones
            constraints_list = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Suma = 1
            ]
            
            # Restricción de retorno objetivo
            if constraints.target_return is not None:
                constraints_list.append({
                    'type': 'eq',
                    'fun': lambda x: np.dot(x, expected_returns) - constraints.target_return
                })
            
            # Restricción de riesgo máximo
            if constraints.max_risk is not None:
                constraints_list.append({
                    'type': 'ineq',
                    'fun': lambda x: constraints.max_risk - np.sqrt(np.dot(x, np.dot(cov_matrix, x)))
                })
            
            # Límites de peso
            bounds = [(constraints.min_weight, constraints.max_weight) for _ in range(n_assets)]
            
            # Punto inicial: pesos iguales
            initial_weights = np.array([1.0 / n_assets] * n_assets)
            
            # Optimización
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': 1000, 'ftol': 1e-9}
            )
            
            if result.success:
                weights = dict(zip(expected_returns.index, result.x))
                return weights
            else:
                self.logger.warning(f"⚠️ Optimización Markowitz falló: {result.message}")
                return dict(zip(expected_returns.index, initial_weights))
                
        except Exception as e:
            self.logger.error(f"❌ Error en optimización Markowitz: {e}")
            # Fallback: pesos iguales
            n_assets = len(expected_returns)
            equal_weights = 1.0 / n_assets
            return dict(zip(expected_returns.index, [equal_weights] * n_assets))
    
    def optimize_black_litterman(self, expected_returns: pd.Series, cov_matrix: pd.DataFrame,
                               market_caps: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Optimización Black-Litterman
        """
        try:
            # Pesos de mercado (si no se proporcionan, usar iguales)
            if market_caps is None:
                market_weights = np.array([1.0 / len(expected_returns)] * len(expected_returns))
            else:
                total_cap = sum(market_caps.values())
                market_weights = np.array([
                    market_caps.get(asset, total_cap / len(expected_returns)) / total_cap
                    for asset in expected_returns.index
                ])
            
            # Parámetros Black-Litterman
            tau = 0.025  # Factor de incertidumbre
            risk_aversion = 3.0  # Aversión al riesgo
            
            # Retornos implícitos del mercado
            pi = risk_aversion * np.dot(cov_matrix, market_weights)
            
            # Views (simplificado: sin views específicas)
            # En una implementación completa, aquí irían las views del analista
            P = np.eye(len(expected_returns))  # Matriz de picking
            Q = expected_returns.values  # Views sobre retornos
            omega = np.diag(np.diag(tau * cov_matrix))  # Incertidumbre de views
            
            # Cálculo Black-Litterman
            tau_cov = tau * cov_matrix
            
            # Nuevos retornos esperados
            M1 = np.linalg.inv(tau_cov)
            M2 = np.dot(P.T, np.dot(np.linalg.inv(omega), P))
            M3 = np.dot(np.linalg.inv(tau_cov), pi)
            M4 = np.dot(P.T, np.dot(np.linalg.inv(omega), Q))
            
            mu_bl = np.dot(np.linalg.inv(M1 + M2), M3 + M4)
            
            # Nueva matriz de covarianza
            cov_bl = np.linalg.inv(M1 + M2)
            
            # Optimización con nuevos parámetros
            def objective(weights):
                portfolio_return = np.dot(weights, mu_bl)
                portfolio_variance = np.dot(weights, np.dot(cov_bl, weights))
                portfolio_std = np.sqrt(portfolio_variance)
                
                if portfolio_std == 0:
                    return -np.inf
                
                sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_std
                return -sharpe_ratio
            
            # Restricciones
            constraints_list = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
            bounds = [(0.0, 1.0) for _ in range(len(expected_returns))]
            initial_weights = market_weights
            
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': 1000}
            )
            
            if result.success:
                weights = dict(zip(expected_returns.index, result.x))
                return weights
            else:
                return dict(zip(expected_returns.index, market_weights))
                
        except Exception as e:
            self.logger.error(f"❌ Error en optimización Black-Litterman: {e}")
            # Fallback: pesos iguales
            n_assets = len(expected_returns)
            equal_weights = 1.0 / n_assets
            return dict(zip(expected_returns.index, [equal_weights] * n_assets))
    
    def optimize_risk_parity(self, cov_matrix: pd.DataFrame, 
                           method: str = 'standard',
                           volatility_target: float = None,
                           risk_budgets: Dict[str, float] = None) -> Dict[str, float]:
        """
        Optimización Risk Parity avanzada con múltiples métodos
        
        Args:
            cov_matrix: Matriz de covarianza
            method: 'standard', 'hierarchical', 'volatility_weighted', 'robust'
            volatility_target: Volatilidad objetivo del portfolio
            risk_budgets: Presupuestos de riesgo personalizados por activo
        """
        try:
            if method == 'hierarchical':
                return self._optimize_hierarchical_risk_parity(cov_matrix)
            elif method == 'volatility_weighted':
                return self._optimize_volatility_weighted_risk_parity(cov_matrix, volatility_target)
            elif method == 'robust':
                return self._optimize_robust_risk_parity(cov_matrix)
            else:
                return self._optimize_standard_risk_parity(cov_matrix, risk_budgets)
                
        except Exception as e:
            self.logger.error(f"❌ Error en optimización Risk Parity: {e}")
            # Fallback: pesos iguales
            n_assets = len(cov_matrix)
            equal_weights = 1.0 / n_assets
            return dict(zip(cov_matrix.index, [equal_weights] * n_assets))
    
    def _optimize_standard_risk_parity(self, cov_matrix: pd.DataFrame, 
                                     risk_budgets: Dict[str, float] = None) -> Dict[str, float]:
        """Risk Parity estándar con presupuestos de riesgo personalizables"""
        n_assets = len(cov_matrix)
        
        # Usar presupuestos iguales si no se especifican
        if risk_budgets is None:
            target_risk_budgets = np.array([1.0 / n_assets] * n_assets)
        else:
            target_risk_budgets = np.array([risk_budgets.get(asset, 1.0/n_assets) 
                                          for asset in cov_matrix.index])
            # Normalizar para que sumen 1
            target_risk_budgets = target_risk_budgets / np.sum(target_risk_budgets)
        
        def risk_budget_objective(weights):
            # Calcular contribuciones de riesgo
            portfolio_variance = np.dot(weights, np.dot(cov_matrix, weights))
            if portfolio_variance <= 0:
                return 1e6
            
            marginal_contrib = np.dot(cov_matrix, weights)
            contrib = weights * marginal_contrib / portfolio_variance
            
            # Objetivo: minimizar diferencias con presupuestos objetivo
            return np.sum((contrib - target_risk_budgets) ** 2)
        
        # Restricciones
        constraints = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        bounds = [(0.001, 0.8) for _ in range(n_assets)]  # Límites más estrictos
        
        # Punto inicial: inverse volatility weighting
        volatilities = np.sqrt(np.diag(cov_matrix))
        initial_weights = (1 / volatilities) / np.sum(1 / volatilities)
        
        result = minimize(
            risk_budget_objective,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 2000, 'ftol': 1e-9}
        )
        
        if result.success:
            return dict(zip(cov_matrix.index, result.x))
        else:
            return dict(zip(cov_matrix.index, initial_weights))
    
    def _optimize_hierarchical_risk_parity(self, cov_matrix: pd.DataFrame) -> Dict[str, float]:
        """Hierarchical Risk Parity (HRP) - Técnica avanzada de QuantConnect"""
        try:
            from scipy.cluster.hierarchy import linkage, dendrogram, cut_tree
            from scipy.spatial.distance import squareform
            
            # Convertir correlaciones a distancias
            corr_matrix = cov_matrix.corr()
            distance_matrix = np.sqrt(0.5 * (1 - corr_matrix))
            
            # Clustering jerárquico
            condensed_distances = squareform(distance_matrix, checks=False)
            linkage_matrix = linkage(condensed_distances, method='ward')
            
            # Función recursiva para asignar pesos
            def _get_cluster_weights(cov_sub, items):
                if len(items) == 1:
                    return np.array([1.0])
                
                # Dividir cluster en dos subclusters
                mid = len(items) // 2
                left_items = items[:mid]
                right_items = items[mid:]
                
                # Calcular varianza de cada subcluster
                left_cov = cov_sub.loc[left_items, left_items]
                right_cov = cov_sub.loc[right_items, right_items]
                
                left_var = self._calculate_cluster_variance(left_cov)
                right_var = self._calculate_cluster_variance(right_cov)
                
                # Asignar pesos inversamente proporcionales a la varianza
                total_var = left_var + right_var
                if total_var > 0:
                    left_weight = right_var / total_var
                    right_weight = left_var / total_var
                else:
                    left_weight = right_weight = 0.5
                
                # Recursión para subclusters
                left_weights = _get_cluster_weights(cov_sub, left_items) * left_weight
                right_weights = _get_cluster_weights(cov_sub, right_items) * right_weight
                
                return np.concatenate([left_weights, right_weights])
            
            # Obtener orden de clustering
            sorted_items = self._get_cluster_order(linkage_matrix, cov_matrix.index.tolist())
            
            # Calcular pesos HRP
            weights = _get_cluster_weights(cov_matrix, sorted_items)
            
            return dict(zip(sorted_items, weights))
            
        except Exception as e:
            self.logger.warning(f"HRP falló, usando Risk Parity estándar: {e}")
            return self._optimize_standard_risk_parity(cov_matrix)
    
    def _optimize_volatility_weighted_risk_parity(self, cov_matrix: pd.DataFrame, 
                                                volatility_target: float = None) -> Dict[str, float]:
        """Risk Parity con weighting por volatilidad - Técnica de QuantConnect"""
        volatilities = np.sqrt(np.diag(cov_matrix))
        
        # Calcular pesos base inversamente proporcionales a volatilidad
        inv_vol_weights = (1 / volatilities) / np.sum(1 / volatilities)
        
        if volatility_target is None:
            return dict(zip(cov_matrix.index, inv_vol_weights))
        
        # Ajustar para volatilidad objetivo
        current_vol = np.sqrt(np.dot(inv_vol_weights, np.dot(cov_matrix, inv_vol_weights)))
        vol_scalar = volatility_target / current_vol if current_vol > 0 else 1.0
        
        # Aplicar scalar manteniendo restricciones
        adjusted_weights = inv_vol_weights * min(vol_scalar, 2.0)  # Límite de escalado
        adjusted_weights = adjusted_weights / np.sum(adjusted_weights)  # Renormalizar
        
        return dict(zip(cov_matrix.index, adjusted_weights))
    
    def _optimize_robust_risk_parity(self, cov_matrix: pd.DataFrame) -> Dict[str, float]:
        """Risk Parity robusto con regularización - Técnica avanzada"""
        try:
            # Regularización de la matriz de covarianza
            regularization_factor = 0.01
            n_assets = len(cov_matrix)
            identity = np.eye(n_assets)
            
            # Shrinkage hacia matriz identidad
            regularized_cov = (1 - regularization_factor) * cov_matrix + \
                            regularization_factor * np.trace(cov_matrix) / n_assets * identity
            
            # Optimización robusta con penalización por concentración
            def robust_objective(weights):
                # Contribuciones de riesgo
                portfolio_variance = np.dot(weights, np.dot(regularized_cov, weights))
                if portfolio_variance <= 0:
                    return 1e6
                
                marginal_contrib = np.dot(regularized_cov, weights)
                contrib = weights * marginal_contrib / portfolio_variance
                
                # Objetivo principal: igualdad de contribuciones
                target_contrib = 1.0 / n_assets
                risk_parity_penalty = np.sum((contrib - target_contrib) ** 2)
                
                # Penalización por concentración (evitar pesos extremos)
                concentration_penalty = np.sum(weights ** 2) * 0.1
                
                # Penalización por turnover (suavidad)
                turnover_penalty = np.sum(np.abs(np.diff(weights))) * 0.05
                
                return risk_parity_penalty + concentration_penalty + turnover_penalty
            
            # Restricciones más estrictas
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
                {'type': 'ineq', 'fun': lambda x: 0.5 - np.max(x)}  # Máximo 50% en un activo
            ]
            bounds = [(0.02, 0.5) for _ in range(n_assets)]  # Límites conservadores
            
            # Punto inicial mejorado
            volatilities = np.sqrt(np.diag(regularized_cov))
            initial_weights = (1 / volatilities) / np.sum(1 / volatilities)
            
            result = minimize(
                robust_objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 3000, 'ftol': 1e-10}
            )
            
            if result.success:
                return dict(zip(cov_matrix.index, result.x))
            else:
                return dict(zip(cov_matrix.index, initial_weights))
                
        except Exception as e:
            self.logger.warning(f"Risk Parity robusto falló: {e}")
            return self._optimize_standard_risk_parity(cov_matrix)
    
    def _calculate_cluster_variance(self, cov_matrix: pd.DataFrame) -> float:
        """Calcular varianza de un cluster para HRP"""
        if len(cov_matrix) == 1:
            return cov_matrix.iloc[0, 0]
        
        # Pesos iguales para el cluster
        weights = np.array([1.0 / len(cov_matrix)] * len(cov_matrix))
        return np.dot(weights, np.dot(cov_matrix, weights))
    
    def _get_cluster_order(self, linkage_matrix, items):
        """Obtener orden de clustering para HRP"""
        try:
            from scipy.cluster.hierarchy import leaves_list
            order = leaves_list(linkage_matrix)
            return [items[i] for i in order]
        except:
            return items
    
    def optimize_momentum_overlay(self, price_data: Dict[str, pd.DataFrame], 
                                base_weights: Dict[str, float],
                                momentum_lookback: int = 60,
                                momentum_strength: float = 0.3) -> Dict[str, float]:
        """
        Aplicar momentum overlay a pesos base - Técnica de QuantConnect
        
        Args:
            price_data: Datos de precios por activo
            base_weights: Pesos base del portfolio
            momentum_lookback: Período de lookback para momentum (días)
            momentum_strength: Fuerza del ajuste por momentum (0-1)
        """
        try:
            momentum_scores = {}
            
            for symbol, data in price_data.items():
                if len(data) < momentum_lookback:
                    momentum_scores[symbol] = 0.0
                    continue
                
                # Calcular momentum como retorno acumulado
                recent_prices = data['close'].tail(momentum_lookback)
                momentum = (recent_prices.iloc[-1] / recent_prices.iloc[0]) - 1
                
                # Normalizar momentum usando z-score
                price_returns = data['close'].pct_change().dropna()
                if len(price_returns) > momentum_lookback:
                    rolling_returns = price_returns.rolling(momentum_lookback).mean()
                    rolling_std = price_returns.rolling(momentum_lookback).std()
                    
                    if rolling_std.iloc[-1] > 0:
                        momentum_z_score = (momentum - rolling_returns.iloc[-1]) / rolling_std.iloc[-1]
                        momentum_scores[symbol] = np.tanh(momentum_z_score)  # Limitar a [-1, 1]
                    else:
                        momentum_scores[symbol] = 0.0
                else:
                    momentum_scores[symbol] = np.tanh(momentum)
            
            # Aplicar overlay de momentum
            adjusted_weights = {}
            total_adjustment = 0
            
            for symbol in base_weights:
                if symbol in momentum_scores:
                    momentum_adjustment = momentum_strength * momentum_scores[symbol]
                    adjusted_weight = base_weights[symbol] * (1 + momentum_adjustment)
                    adjusted_weights[symbol] = max(0.001, adjusted_weight)  # Mínimo 0.1%
                    total_adjustment += adjusted_weights[symbol]
                else:
                    adjusted_weights[symbol] = base_weights[symbol]
                    total_adjustment += adjusted_weights[symbol]
            
            # Renormalizar para que sumen 1
            if total_adjustment > 0:
                for symbol in adjusted_weights:
                    adjusted_weights[symbol] /= total_adjustment
            
            self.logger.info(f"📈 Momentum overlay aplicado - Fuerza: {momentum_strength}")
            return adjusted_weights
            
        except Exception as e:
            self.logger.error(f"❌ Error en momentum overlay: {e}")
            return base_weights
    
    def optimize_dynamic_asset_allocation(self, price_data: Dict[str, pd.DataFrame],
                                        market_regime: str = 'normal',
                                        volatility_threshold: float = 0.02) -> Dict[str, float]:
        """
        Asignación dinámica de activos basada en régimen de mercado - QuantConnect
        
        Args:
            price_data: Datos de precios por activo
            market_regime: 'bull', 'bear', 'normal', 'high_vol', 'low_vol'
            volatility_threshold: Umbral para detectar alta volatilidad
        """
        try:
            # Detectar régimen de mercado automáticamente si no se especifica
            if market_regime == 'auto':
                market_regime = self._detect_market_regime(price_data, volatility_threshold)
            
            # Configuraciones por régimen
            regime_configs = {
                'bull': {'risk_target': 0.15, 'momentum_weight': 0.4, 'min_diversification': 0.6},
                'bear': {'risk_target': 0.08, 'momentum_weight': 0.1, 'min_diversification': 0.8},
                'normal': {'risk_target': 0.12, 'momentum_weight': 0.2, 'min_diversification': 0.7},
                'high_vol': {'risk_target': 0.06, 'momentum_weight': 0.05, 'min_diversification': 0.9},
                'low_vol': {'risk_target': 0.18, 'momentum_weight': 0.3, 'min_diversification': 0.5}
            }
            
            config = regime_configs.get(market_regime, regime_configs['normal'])
            
            # Preparar datos
            price_df, returns_df = self.prepare_data(price_data)
            expected_returns = self.calculate_expected_returns(returns_df)
            cov_matrix = self.calculate_covariance_matrix(returns_df)
            
            # Optimización base con volatilidad objetivo
            base_weights = self._optimize_volatility_weighted_risk_parity(
                cov_matrix, config['risk_target']
            )
            
            # Aplicar momentum overlay
            momentum_weights = self.optimize_momentum_overlay(
                price_data, base_weights, momentum_strength=config['momentum_weight']
            )
            
            # Aplicar restricción de diversificación mínima
            final_weights = self._apply_diversification_constraint(
                momentum_weights, config['min_diversification']
            )
            
            self.logger.info(f"🎯 Asignación dinámica para régimen '{market_regime}' completada")
            return final_weights
            
        except Exception as e:
            self.logger.error(f"❌ Error en asignación dinámica: {e}")
            # Fallback: pesos iguales
            n_assets = len(price_data)
            equal_weight = 1.0 / n_assets
            return {symbol: equal_weight for symbol in price_data.keys()}
    
    def _detect_market_regime(self, price_data: Dict[str, pd.DataFrame], 
                            volatility_threshold: float) -> str:
        """Detectar régimen de mercado automáticamente"""
        try:
            # Calcular volatilidad promedio del mercado
            market_volatilities = []
            market_returns = []
            
            for symbol, data in price_data.items():
                if len(data) > 30:
                    returns = data['close'].pct_change().dropna()
                    vol = returns.std() * np.sqrt(252)  # Volatilidad anualizada
                    avg_return = returns.mean() * 252  # Retorno anualizado
                    
                    market_volatilities.append(vol)
                    market_returns.append(avg_return)
            
            if not market_volatilities:
                return 'normal'
            
            avg_volatility = np.mean(market_volatilities)
            avg_return = np.mean(market_returns)
            
            # Clasificar régimen
            if avg_volatility > volatility_threshold * 2:
                return 'high_vol'
            elif avg_volatility < volatility_threshold * 0.5:
                return 'low_vol'
            elif avg_return > 0.1:  # 10% anual
                return 'bull'
            elif avg_return < -0.05:  # -5% anual
                return 'bear'
            else:
                return 'normal'
                
        except Exception as e:
            self.logger.warning(f"Error detectando régimen: {e}")
            return 'normal'
    
    def _apply_diversification_constraint(self, weights: Dict[str, float], 
                                        min_diversification: float) -> Dict[str, float]:
        """Aplicar restricción de diversificación mínima"""
        try:
            # Calcular índice de concentración (Herfindahl)
            concentration = sum(w**2 for w in weights.values())
            max_concentration = 1.0 - min_diversification
            
            if concentration <= max_concentration:
                return weights  # Ya cumple la restricción
            
            # Ajustar pesos para cumplir diversificación mínima
            n_assets = len(weights)
            min_weight = min_diversification / n_assets
            
            adjusted_weights = {}
            total_excess = 0
            
            # Primera pasada: aplicar peso mínimo
            for symbol, weight in weights.items():
                if weight < min_weight:
                    adjusted_weights[symbol] = min_weight
                else:
                    adjusted_weights[symbol] = weight
                    total_excess += weight - min_weight
            
            # Segunda pasada: redistribuir exceso proporcionalmente
            if total_excess > 0:
                excess_factor = (1.0 - n_assets * min_weight) / total_excess
                for symbol in adjusted_weights:
                    if weights[symbol] >= min_weight:
                        excess = weights[symbol] - min_weight
                        adjusted_weights[symbol] = min_weight + excess * excess_factor
            
            # Renormalizar
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                for symbol in adjusted_weights:
                    adjusted_weights[symbol] /= total_weight
            
            return adjusted_weights
            
        except Exception as e:
            self.logger.warning(f"Error aplicando restricción de diversificación: {e}")
            return weights
    
    def optimize_minimum_variance(self, cov_matrix: pd.DataFrame,
                                constraints: OptimizationConstraints) -> Dict[str, float]:
        """
        Optimización de mínima varianza
        """
        try:
            n_assets = len(cov_matrix)
            
            # Función objetivo: minimizar varianza
            def objective(weights):
                return np.dot(weights, np.dot(cov_matrix, weights))
            
            # Restricciones
            constraints_list = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
            bounds = [(constraints.min_weight, constraints.max_weight) for _ in range(n_assets)]
            
            # Punto inicial
            initial_weights = np.array([1.0 / n_assets] * n_assets)
            
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints_list,
                options={'maxiter': 1000}
            )
            
            if result.success:
                weights = dict(zip(cov_matrix.index, result.x))
                return weights
            else:
                return dict(zip(cov_matrix.index, initial_weights))
                
        except Exception as e:
            self.logger.error(f"❌ Error en optimización de mínima varianza: {e}")
            # Fallback: pesos iguales
            n_assets = len(cov_matrix)
            equal_weights = 1.0 / n_assets
            return dict(zip(cov_matrix.index, [equal_weights] * n_assets))
    
    def calculate_portfolio_metrics(self, weights: Dict[str, float], 
                                  expected_returns: pd.Series, 
                                  cov_matrix: pd.DataFrame,
                                  returns_df: pd.DataFrame) -> PortfolioMetrics:
        """
        Calcula métricas del portafolio
        """
        try:
            # Convertir pesos a array
            weight_array = np.array([weights.get(asset, 0) for asset in expected_returns.index])
            
            # Retorno esperado
            portfolio_return = np.dot(weight_array, expected_returns)
            
            # Volatilidad
            portfolio_variance = np.dot(weight_array, np.dot(cov_matrix, weight_array))
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            # Sharpe ratio
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
            
            # Calcular retornos del portafolio para métricas adicionales
            portfolio_returns = (returns_df * weight_array).sum(axis=1)
            
            # Sortino ratio
            downside_returns = portfolio_returns[portfolio_returns < 0]
            downside_volatility = np.sqrt(np.mean(downside_returns ** 2)) * np.sqrt(252) if len(downside_returns) > 0 else portfolio_volatility
            sortino_ratio = (portfolio_return - self.risk_free_rate) / downside_volatility if downside_volatility > 0 else 0
            
            # Max drawdown
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(drawdowns.min()) if len(drawdowns) > 0 else 0
            
            # VaR 95%
            var_95 = np.percentile(portfolio_returns, 5) * np.sqrt(252)
            
            # CVaR 95%
            tail_returns = portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)]
            cvar_95 = np.mean(tail_returns) * np.sqrt(252) if len(tail_returns) > 0 else var_95
            
            # Diversification ratio
            individual_volatilities = np.sqrt(np.diag(cov_matrix))
            weighted_avg_volatility = np.dot(weight_array, individual_volatilities)
            diversification_ratio = weighted_avg_volatility / portfolio_volatility if portfolio_volatility > 0 else 1
            
            # Turnover (simplificado)
            turnover = 0.0  # Se calcularía comparando con pesos anteriores
            
            # Total weight
            total_weight = sum(weights.values())
            
            return PortfolioMetrics(
                expected_return=portfolio_return,
                volatility=portfolio_volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                max_drawdown=max_drawdown,
                var_95=abs(var_95),
                cvar_95=abs(cvar_95),
                diversification_ratio=diversification_ratio,
                turnover=turnover,
                total_weight=total_weight
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando métricas del portafolio: {e}")
            return PortfolioMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 1)
    
    def optimize_portfolio(self, price_data: Dict[str, pd.DataFrame],
                         method: OptimizationMethod = OptimizationMethod.MARKOWITZ,
                         constraints: Optional[OptimizationConstraints] = None,
                         risk_model: RiskModel = RiskModel.HISTORICAL) -> OptimizationResult:
        """
        Optimiza el portafolio usando el método especificado
        """
        start_time = datetime.now()
        
        try:
            # Usar restricciones por defecto si no se proporcionan
            if constraints is None:
                constraints = OptimizationConstraints()
            
            # Preparar datos
            price_df, returns_df = self.prepare_data(price_data)
            
            # Calcular retornos esperados y matriz de covarianza
            expected_returns = self.calculate_expected_returns(returns_df)
            cov_matrix = self.calculate_covariance_matrix(returns_df, risk_model)
            
            # Optimizar según el método
            if method == OptimizationMethod.MARKOWITZ:
                weights = self.optimize_markowitz(expected_returns, cov_matrix, constraints)
            elif method == OptimizationMethod.BLACK_LITTERMAN:
                weights = self.optimize_black_litterman(expected_returns, cov_matrix)
            elif method == OptimizationMethod.RISK_PARITY:
                weights = self.optimize_risk_parity(cov_matrix)
            elif method == OptimizationMethod.MINIMUM_VARIANCE:
                weights = self.optimize_minimum_variance(cov_matrix, constraints)
            elif method == OptimizationMethod.MAXIMUM_SHARPE:
                weights = self.optimize_markowitz(expected_returns, cov_matrix, constraints)
            elif method == OptimizationMethod.MOMENTUM_OVERLAY:
                # Usar Risk Parity como base y aplicar momentum overlay
                base_weights = self.optimize_risk_parity(cov_matrix)
                weights = self.optimize_momentum_overlay(price_data, base_weights)
            elif method == OptimizationMethod.DYNAMIC_ASSET_ALLOCATION:
                weights = self.optimize_dynamic_asset_allocation(price_data)
            elif method == OptimizationMethod.VOLATILITY_WEIGHTED_RISK_PARITY:
                weights = self.optimize_risk_parity(cov_matrix, method='volatility_weighted')
            elif method == OptimizationMethod.ROBUST_RISK_PARITY:
                weights = self.optimize_risk_parity(cov_matrix, method='robust')
            else:
                # Por defecto: Markowitz
                weights = self.optimize_markowitz(expected_returns, cov_matrix, constraints)
            
            # Calcular métricas
            metrics = self.calculate_portfolio_metrics(weights, expected_returns, cov_matrix, returns_df)
            
            # Tiempo de optimización
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = OptimizationResult(
                weights=weights,
                metrics=metrics,
                method=method,
                success=True,
                message="Optimización completada exitosamente",
                optimization_time=optimization_time,
                iterations=1
            )
            
            # Guardar en historial
            self.optimization_history.append({
                'timestamp': datetime.now(),
                'method': method.value,
                'result': result,
                'assets': list(weights.keys())
            })
            
            # Mantener solo últimas 50 optimizaciones
            if len(self.optimization_history) > 50:
                self.optimization_history = self.optimization_history[-50:]
            
            self.logger.info(f"✅ Optimización {method.value} completada en {optimization_time:.2f}s")
            self.logger.info(f"   Retorno esperado: {metrics.expected_return*100:.2f}%")
            self.logger.info(f"   Volatilidad: {metrics.volatility*100:.2f}%")
            self.logger.info(f"   Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
            
            return result
            
        except Exception as e:
            optimization_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"❌ Error en optimización {method.value}: {e}")
            
            # Resultado de error con pesos iguales
            if 'price_data' in locals() and price_data:
                n_assets = len(price_data)
                equal_weight = 1.0 / n_assets
                weights = {symbol: equal_weight for symbol in price_data.keys()}
            else:
                weights = {}
            
            return OptimizationResult(
                weights=weights,
                metrics=PortfolioMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 1),
                method=method,
                success=False,
                message=f"Error en optimización: {str(e)}",
                optimization_time=optimization_time,
                iterations=0
            )
    
    def compare_methods(self, price_data: Dict[str, pd.DataFrame],
                       methods: List[OptimizationMethod] = None) -> Dict[str, OptimizationResult]:
        """
        Compara múltiples métodos de optimización
        """
        if methods is None:
            methods = [
                OptimizationMethod.MARKOWITZ,
                OptimizationMethod.RISK_PARITY,
                OptimizationMethod.MINIMUM_VARIANCE,
                OptimizationMethod.BLACK_LITTERMAN
            ]
        
        results = {}
        
        self.logger.info(f"🔄 Comparando {len(methods)} métodos de optimización...")
        
        for method in methods:
            try:
                result = self.optimize_portfolio(price_data, method)
                results[method.value] = result
                
                if result.success:
                    self.logger.info(f"  ✅ {method.value}: Sharpe {result.metrics.sharpe_ratio:.3f}")
                else:
                    self.logger.warning(f"  ❌ {method.value}: {result.message}")
                    
            except Exception as e:
                self.logger.error(f"  ❌ Error en {method.value}: {e}")
        
        return results
    
    def get_optimization_summary(self) -> Dict:
        """
        Obtiene resumen de optimizaciones realizadas
        """
        if not self.optimization_history:
            return {
                'total_optimizations': 0,
                'methods_used': [],
                'avg_optimization_time': 0,
                'success_rate': 0
            }
        
        successful = [opt for opt in self.optimization_history if opt['result'].success]
        methods_used = list(set([opt['method'] for opt in self.optimization_history]))
        avg_time = np.mean([opt['result'].optimization_time for opt in self.optimization_history])
        
        return {
            'total_optimizations': len(self.optimization_history),
            'successful_optimizations': len(successful),
            'methods_used': methods_used,
            'avg_optimization_time': avg_time,
            'success_rate': len(successful) / len(self.optimization_history),
            'last_optimization': self.optimization_history[-1]['timestamp'].isoformat()
        }

# Función de prueba
def test_portfolio_optimizer():
    """
    Función de prueba para el optimizador de portafolio
    """
    print("🧪 Iniciando pruebas del Optimizador de Portafolio...")
    
    # Crear optimizador
    optimizer = PortfolioOptimizer(risk_free_rate=0.02)
    
    # Simular datos de mercado
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
    price_data = {}
    
    np.random.seed(42)
    
    for i, symbol in enumerate(symbols):
        # Generar datos sintéticos con diferentes características
        periods = 200
        base_price = [50000, 3000, 1.5, 25, 15][i]
        
        # Diferentes volatilidades y tendencias
        volatility = [0.04, 0.05, 0.06, 0.07, 0.06][i]
        trend = [0.0005, 0.0003, 0.0002, 0.0001, 0.0004][i]
        
        prices = []
        current_price = base_price
        
        for j in range(periods):
            # Tendencia + ruido
            change = trend + np.random.normal(0, volatility)
            current_price *= (1 + change)
            prices.append(current_price)
        
        price_data[symbol] = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-06-01', periods=periods, freq='1D'),
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 10000, periods)
        })
    
    print(f"📊 Datos generados para {len(symbols)} activos con {periods} períodos cada uno")
    
    # Probar optimización individual
    print("\n🎯 Probando optimización Markowitz...")
    constraints = OptimizationConstraints(
        min_weight=0.05,  # Mínimo 5% por activo
        max_weight=0.40,  # Máximo 40% por activo
        target_return=0.15  # Objetivo 15% anual
    )
    
    result = optimizer.optimize_portfolio(
        price_data, 
        OptimizationMethod.MARKOWITZ, 
        constraints
    )
    
    if result.success:
        print(f"✅ Optimización exitosa:")
        print(f"  Retorno esperado: {result.metrics.expected_return*100:.2f}%")
        print(f"  Volatilidad: {result.metrics.volatility*100:.2f}%")
        print(f"  Sharpe Ratio: {result.metrics.sharpe_ratio:.3f}")
        print(f"  Max Drawdown: {result.metrics.max_drawdown*100:.2f}%")
        print(f"  Tiempo de optimización: {result.optimization_time:.2f}s")
        
        print(f"\n💼 Pesos del portafolio:")
        for asset, weight in result.weights.items():
            print(f"  {asset}: {weight*100:.1f}%")
    else:
        print(f"❌ Optimización falló: {result.message}")
    
    # Comparar métodos
    print(f"\n🔄 Comparando múltiples métodos de optimización...")
    
    methods_to_compare = [
        OptimizationMethod.MARKOWITZ,
        OptimizationMethod.RISK_PARITY,
        OptimizationMethod.MINIMUM_VARIANCE,
        OptimizationMethod.BLACK_LITTERMAN
    ]
    
    comparison_results = optimizer.compare_methods(price_data, methods_to_compare)
    
    print(f"\n📊 Resultados de la comparación:")
    print(f"{'Método':<20} {'Retorno':<10} {'Volatilidad':<12} {'Sharpe':<8} {'Éxito'}")
    print("-" * 60)
    
    for method_name, result in comparison_results.items():
        if result.success:
            print(f"{method_name:<20} {result.metrics.expected_return*100:>7.2f}% "
                  f"{result.metrics.volatility*100:>9.2f}% "
                  f"{result.metrics.sharpe_ratio:>6.3f} {'✅'}")
        else:
            print(f"{method_name:<20} {'N/A':<10} {'N/A':<12} {'N/A':<8} {'❌'}")
    
    # Encontrar mejor método por Sharpe ratio
    successful_results = {k: v for k, v in comparison_results.items() if v.success}
    if successful_results:
        best_method = max(successful_results.items(), 
                         key=lambda x: x[1].metrics.sharpe_ratio)
        print(f"\n🏆 Mejor método por Sharpe Ratio: {best_method[0]} "
              f"(Sharpe: {best_method[1].metrics.sharpe_ratio:.3f})")
    
    # Mostrar resumen
    summary = optimizer.get_optimization_summary()
    print(f"\n📋 Resumen de Optimizaciones:")
    print(f"  Total de optimizaciones: {summary['total_optimizations']}")
    print(f"  Optimizaciones exitosas: {summary['successful_optimizations']}")
    print(f"  Tasa de éxito: {summary['success_rate']*100:.1f}%")
    print(f"  Tiempo promedio: {summary['avg_optimization_time']:.2f}s")
    print(f"  Métodos utilizados: {', '.join(summary['methods_used'])}")
    
    print("\n✅ Pruebas del Optimizador de Portafolio completadas")

if __name__ == "__main__":
    test_portfolio_optimizer()