#!/usr/bin/env python3
"""
Sistema de Optimización de Parámetros y Validación Cruzada
Optimizado para estrategia Binance Spot con objetivo de 0.6% diario
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from scipy.optimize import differential_evolution, minimize
from sklearn.model_selection import TimeSeriesSplit, ParameterGrid
from sklearn.metrics import mean_squared_error, mean_absolute_error
import itertools
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
from functools import partial
warnings.filterwarnings('ignore')

@dataclass
class OptimizationResult:
    """Resultado de optimización"""
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Dict]
    optimization_time: float
    total_evaluations: int
    convergence_history: List[float]
    validation_scores: List[float]
    out_of_sample_score: float
    stability_score: float
    robustness_score: float
    
@dataclass
class ParameterSpace:
    """Espacio de parámetros para optimización"""
    name: str
    param_type: str  # 'int', 'float', 'choice'
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: Optional[List[Any]] = None
    step: Optional[float] = None
    
@dataclass
class ValidationMetrics:
    """Métricas de validación"""
    daily_return: float
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    volatility: float
    var_95: float
    trades_count: int
    avg_trade_duration: float
    consistency_score: float
    risk_adjusted_return: float
    
class ParameterOptimizer:
    """
    Sistema avanzado de optimización de parámetros que utiliza:
    - Optimización diferencial evolutiva
    - Validación cruzada temporal
    - Análisis de robustez
    - Pruebas de estabilidad
    - Optimización multiobjetivo
    """
    
    def __init__(self, target_daily_return: float = 0.006, 
                 optimization_metric: str = 'risk_adjusted_return'):
        self.target_daily_return = target_daily_return
        self.optimization_metric = optimization_metric
        
        # Configuración de optimización
        self.max_evaluations = 1000
        self.population_size = 50
        self.convergence_tolerance = 1e-6
        self.max_generations = 100
        
        # Configuración de validación cruzada
        self.n_splits = 5
        self.test_size = 0.2
        self.gap_size = 24  # Horas entre train y test
        
        # Pesos para optimización multiobjetivo
        self.objective_weights = {
            'daily_return': 0.4,
            'sharpe_ratio': 0.3,
            'max_drawdown': 0.2,
            'win_rate': 0.1
        }
        
        # Configuración de logging
        self.logger = logging.getLogger(__name__)
        
        # Resultados de optimización
        self.optimization_history: List[OptimizationResult] = []
        self.best_global_params: Optional[Dict] = None
        self.best_global_score: float = -np.inf
        
    def define_parameter_space(self) -> List[ParameterSpace]:
        """Definir espacio de parámetros para optimización"""
        
        parameter_space = [
            # Parámetros RSI
            ParameterSpace('rsi_period', 'int', 10, 25, step=1),
            ParameterSpace('rsi_oversold', 'int', 15, 35, step=5),
            ParameterSpace('rsi_overbought', 'int', 65, 85, step=5),
            
            # Parámetros MACD
            ParameterSpace('macd_fast', 'int', 8, 16, step=2),
            ParameterSpace('macd_slow', 'int', 20, 35, step=3),
            ParameterSpace('macd_signal', 'int', 6, 12, step=2),
            
            # Parámetros Bollinger Bands
            ParameterSpace('bb_period', 'int', 15, 30, step=5),
            ParameterSpace('bb_std', 'float', 1.5, 3.0, step=0.25),
            
            # Parámetros ADX
            ParameterSpace('adx_period', 'int', 10, 20, step=2),
            ParameterSpace('adx_threshold', 'int', 20, 35, step=5),
            
            # Parámetros de gestión de riesgo
            ParameterSpace('stop_loss_atr', 'float', 1.0, 3.0, step=0.25),
            ParameterSpace('take_profit_atr', 'float', 1.5, 4.0, step=0.25),
            ParameterSpace('position_size_pct', 'float', 0.01, 0.05, step=0.005),
            
            # Parámetros de señales
            ParameterSpace('min_signal_strength', 'int', 50, 80, step=10),
            ParameterSpace('min_confidence', 'int', 60, 85, step=5),
            
            # Parámetros de filtros
            ParameterSpace('volume_filter', 'float', 0.8, 2.0, step=0.2),
            ParameterSpace('volatility_filter', 'float', 0.01, 0.06, step=0.01),
            
            # Parámetros de timing
            ParameterSpace('entry_delay', 'int', 0, 3, step=1),
            ParameterSpace('exit_delay', 'int', 0, 2, step=1),
        ]
        
        return parameter_space
        
    def create_parameter_combinations(self, parameter_space: List[ParameterSpace], 
                                    method: str = 'grid') -> List[Dict]:
        """Crear combinaciones de parámetros"""
        
        if method == 'grid':
            return self.create_grid_combinations(parameter_space)
        elif method == 'random':
            return self.create_random_combinations(parameter_space)
        elif method == 'latin_hypercube':
            return self.create_lhs_combinations(parameter_space)
        else:
            raise ValueError(f"Método desconocido: {method}")
            
    def create_grid_combinations(self, parameter_space: List[ParameterSpace]) -> List[Dict]:
        """Crear combinaciones usando grid search"""
        
        param_grids = {}
        
        for param in parameter_space:
            if param.param_type == 'int':
                param_grids[param.name] = list(range(
                    int(param.min_value), 
                    int(param.max_value) + 1, 
                    int(param.step or 1)
                ))
            elif param.param_type == 'float':
                param_grids[param.name] = list(np.arange(
                    param.min_value, 
                    param.max_value + param.step, 
                    param.step
                ))
            elif param.param_type == 'choice':
                param_grids[param.name] = param.choices
                
        # Limitar combinaciones para evitar explosión combinatoria
        total_combinations = np.prod([len(values) for values in param_grids.values()])
        
        if total_combinations > self.max_evaluations:
            self.logger.warning(f"Demasiadas combinaciones ({total_combinations}), usando muestreo")
            return self.create_random_combinations(parameter_space)
            
        combinations = []
        for combination in itertools.product(*param_grids.values()):
            param_dict = dict(zip(param_grids.keys(), combination))
            combinations.append(param_dict)
            
        return combinations[:self.max_evaluations]
        
    def create_random_combinations(self, parameter_space: List[ParameterSpace]) -> List[Dict]:
        """Crear combinaciones aleatorias"""
        
        combinations = []
        
        for _ in range(self.max_evaluations):
            param_dict = {}
            
            for param in parameter_space:
                if param.param_type == 'int':
                    value = np.random.randint(param.min_value, param.max_value + 1)
                elif param.param_type == 'float':
                    value = np.random.uniform(param.min_value, param.max_value)
                elif param.param_type == 'choice':
                    value = np.random.choice(param.choices)
                    
                param_dict[param.name] = value
                
            combinations.append(param_dict)
            
        return combinations
        
    def create_lhs_combinations(self, parameter_space: List[ParameterSpace]) -> List[Dict]:
        """Crear combinaciones usando Latin Hypercube Sampling"""
        
        try:
            from scipy.stats import qmc
            
            # Crear sampler
            sampler = qmc.LatinHypercube(d=len(parameter_space))
            samples = sampler.random(n=self.max_evaluations)
            
            combinations = []
            
            for sample in samples:
                param_dict = {}
                
                for i, param in enumerate(parameter_space):
                    if param.param_type == 'int':
                        value = int(param.min_value + sample[i] * (param.max_value - param.min_value))
                    elif param.param_type == 'float':
                        value = param.min_value + sample[i] * (param.max_value - param.min_value)
                    elif param.param_type == 'choice':
                        idx = int(sample[i] * len(param.choices))
                        value = param.choices[min(idx, len(param.choices) - 1)]
                        
                    param_dict[param.name] = value
                    
                combinations.append(param_dict)
                
            return combinations
            
        except ImportError:
            self.logger.warning("scipy.stats.qmc no disponible, usando muestreo aleatorio")
            return self.create_random_combinations(parameter_space)
            
    def evaluate_parameters(self, params: Dict, data: pd.DataFrame, 
                          strategy_func: Callable) -> ValidationMetrics:
        """Evaluar un conjunto de parámetros"""
        
        try:
            # Ejecutar estrategia con parámetros
            results = strategy_func(data, params)
            
            if not results or 'trades' not in results:
                return self.create_default_metrics()
                
            trades = results['trades']
            equity_curve = results.get('equity_curve', [])
            
            if not trades:
                return self.create_default_metrics()
                
            # Calcular métricas
            metrics = self.calculate_validation_metrics(trades, equity_curve)
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error evaluando parámetros: {e}")
            return self.create_default_metrics()
            
    def create_default_metrics(self) -> ValidationMetrics:
        """Crear métricas por defecto para casos de error"""
        return ValidationMetrics(
            daily_return=0.0,
            total_return=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=1.0,  # Penalizar fuertemente
            win_rate=0.0,
            profit_factor=0.0,
            calmar_ratio=0.0,
            volatility=0.0,
            var_95=0.0,
            trades_count=0,
            avg_trade_duration=0.0,
            consistency_score=0.0,
            risk_adjusted_return=-1.0  # Penalizar
        )
        
    def calculate_validation_metrics(self, trades: List[Dict], 
                                   equity_curve: List[float]) -> ValidationMetrics:
        """Calcular métricas de validación"""
        
        if not trades:
            return self.create_default_metrics()
            
        # Extraer PnLs
        pnls = [trade.get('pnl', 0) for trade in trades if 'pnl' in trade]
        
        if not pnls:
            return self.create_default_metrics()
            
        # Métricas básicas
        total_return = sum(pnls)
        trades_count = len(pnls)
        
        # Retorno diario promedio
        if equity_curve and len(equity_curve) > 1:
            days = len(equity_curve) / 24  # Asumiendo datos horarios
            daily_return = (total_return / equity_curve[0]) / days if days > 0 else 0
        else:
            daily_return = 0
            
        # Win rate
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) if pnls else 0
        
        # Profit factor
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Calcular retornos para métricas de riesgo
        if equity_curve and len(equity_curve) > 1:
            equity_series = pd.Series(equity_curve)
            returns = equity_series.pct_change().dropna()
            
            if len(returns) > 0:
                # Volatilidad
                volatility = returns.std() * np.sqrt(24 * 365)  # Anualizada
                
                # Sharpe ratio
                mean_return = returns.mean() * 24 * 365  # Anualizada
                sharpe_ratio = mean_return / volatility if volatility > 0 else 0
                
                # Sortino ratio
                downside_returns = returns[returns < 0]
                downside_vol = downside_returns.std() * np.sqrt(24 * 365) if len(downside_returns) > 0 else volatility
                sortino_ratio = mean_return / downside_vol if downside_vol > 0 else 0
                
                # Drawdown
                cumulative = (1 + returns).cumprod()
                running_max = cumulative.expanding().max()
                drawdown = (cumulative - running_max) / running_max
                max_drawdown = abs(drawdown.min())
                
                # Calmar ratio
                calmar_ratio = mean_return / max_drawdown if max_drawdown > 0 else 0
                
                # VaR
                var_95 = np.percentile(returns, 5) if len(returns) > 0 else 0
                
            else:
                volatility = sharpe_ratio = sortino_ratio = max_drawdown = calmar_ratio = var_95 = 0
        else:
            volatility = sharpe_ratio = sortino_ratio = max_drawdown = calmar_ratio = var_95 = 0
            
        # Duración promedio de trades
        durations = []
        for trade in trades:
            if 'entry_time' in trade and 'exit_time' in trade:
                duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600  # Horas
                durations.append(duration)
        avg_trade_duration = np.mean(durations) if durations else 0
        
        # Score de consistencia (basado en variabilidad de retornos)
        if len(pnls) > 1:
            consistency_score = 1 / (1 + np.std(pnls) / (abs(np.mean(pnls)) + 1e-6))
        else:
            consistency_score = 0
            
        # Risk-adjusted return (métrica principal)
        if max_drawdown > 0 and volatility > 0:
            risk_adjusted_return = (daily_return - self.target_daily_return) / (max_drawdown + volatility)
        else:
            risk_adjusted_return = daily_return - self.target_daily_return
            
        return ValidationMetrics(
            daily_return=daily_return,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            calmar_ratio=calmar_ratio,
            volatility=volatility,
            var_95=var_95,
            trades_count=trades_count,
            avg_trade_duration=avg_trade_duration,
            consistency_score=consistency_score,
            risk_adjusted_return=risk_adjusted_return
        )
        
    def calculate_objective_score(self, metrics: ValidationMetrics) -> float:
        """Calcular score objetivo para optimización"""
        
        if self.optimization_metric == 'risk_adjusted_return':
            return metrics.risk_adjusted_return
        elif self.optimization_metric == 'sharpe_ratio':
            return metrics.sharpe_ratio
        elif self.optimization_metric == 'daily_return':
            return metrics.daily_return
        elif self.optimization_metric == 'multi_objective':
            # Combinación ponderada de múltiples objetivos
            score = (
                self.objective_weights['daily_return'] * metrics.daily_return +
                self.objective_weights['sharpe_ratio'] * metrics.sharpe_ratio +
                self.objective_weights['max_drawdown'] * (1 - metrics.max_drawdown) +
                self.objective_weights['win_rate'] * metrics.win_rate
            )
            return score
        else:
            return metrics.risk_adjusted_return
            
    def time_series_cross_validation(self, data: pd.DataFrame, params: Dict,
                                   strategy_func: Callable) -> Tuple[float, List[float]]:
        """Validación cruzada temporal"""
        
        tscv = TimeSeriesSplit(n_splits=self.n_splits, gap=self.gap_size)
        scores = []
        
        for train_idx, test_idx in tscv.split(data):
            # Dividir datos
            train_data = data.iloc[train_idx]
            test_data = data.iloc[test_idx]
            
            # Evaluar en datos de prueba
            metrics = self.evaluate_parameters(params, test_data, strategy_func)
            score = self.calculate_objective_score(metrics)
            scores.append(score)
            
        mean_score = np.mean(scores)
        return mean_score, scores
        
    def walk_forward_optimization(self, data: pd.DataFrame, parameter_space: List[ParameterSpace],
                                strategy_func: Callable, window_size: int = 720) -> OptimizationResult:
        """Optimización walk-forward"""
        
        self.logger.info("Iniciando optimización walk-forward...")
        
        all_results = []
        best_params_history = []
        out_of_sample_scores = []
        
        # Dividir datos en ventanas
        n_windows = (len(data) - window_size) // (window_size // 4)  # 75% overlap
        
        for i in range(n_windows):
            start_idx = i * (window_size // 4)
            end_idx = start_idx + window_size
            
            if end_idx >= len(data):
                break
                
            # Datos de entrenamiento
            train_data = data.iloc[start_idx:end_idx]
            
            # Datos de prueba (siguiente ventana)
            test_start = end_idx
            test_end = min(test_start + window_size // 4, len(data))
            test_data = data.iloc[test_start:test_end]
            
            if len(test_data) < 24:  # Mínimo 24 horas de datos de prueba
                continue
                
            self.logger.info(f"Ventana {i+1}/{n_windows}: Train {len(train_data)} Test {len(test_data)}")
            
            # Optimizar en datos de entrenamiento
            window_result = self.optimize_parameters(
                train_data, parameter_space, strategy_func, method='random'
            )
            
            best_params_history.append(window_result.best_params)
            
            # Evaluar en datos de prueba
            test_metrics = self.evaluate_parameters(
                window_result.best_params, test_data, strategy_func
            )
            test_score = self.calculate_objective_score(test_metrics)
            out_of_sample_scores.append(test_score)
            
            all_results.append({
                'window': i + 1,
                'train_score': window_result.best_score,
                'test_score': test_score,
                'best_params': window_result.best_params,
                'train_size': len(train_data),
                'test_size': len(test_data)
            })
            
        # Calcular estabilidad de parámetros
        stability_score = self.calculate_parameter_stability(best_params_history)
        
        # Mejores parámetros promedio
        best_params = self.average_parameters(best_params_history)
        
        return OptimizationResult(
            best_params=best_params,
            best_score=np.mean(out_of_sample_scores),
            all_results=all_results,
            optimization_time=0,  # Se calculará después
            total_evaluations=len(all_results),
            convergence_history=[],
            validation_scores=out_of_sample_scores,
            out_of_sample_score=np.mean(out_of_sample_scores),
            stability_score=stability_score,
            robustness_score=np.std(out_of_sample_scores)  # Menor es mejor
        )
        
    def optimize_parameters(self, data: pd.DataFrame, parameter_space: List[ParameterSpace],
                          strategy_func: Callable, method: str = 'differential_evolution') -> OptimizationResult:
        """Optimizar parámetros usando el método especificado"""
        
        start_time = datetime.now()
        self.logger.info(f"Iniciando optimización con método: {method}")
        
        if method == 'grid_search':
            result = self.grid_search_optimization(data, parameter_space, strategy_func)
        elif method == 'random_search':
            result = self.random_search_optimization(data, parameter_space, strategy_func)
        elif method == 'differential_evolution':
            result = self.differential_evolution_optimization(data, parameter_space, strategy_func)
        elif method == 'bayesian':
            result = self.bayesian_optimization(data, parameter_space, strategy_func)
        else:
            raise ValueError(f"Método de optimización desconocido: {method}")
            
        optimization_time = (datetime.now() - start_time).total_seconds()
        result.optimization_time = optimization_time
        
        self.logger.info(f"Optimización completada en {optimization_time:.2f} segundos")
        self.logger.info(f"Mejor score: {result.best_score:.6f}")
        
        return result
        
    def grid_search_optimization(self, data: pd.DataFrame, parameter_space: List[ParameterSpace],
                               strategy_func: Callable) -> OptimizationResult:
        """Optimización por grid search"""
        
        combinations = self.create_parameter_combinations(parameter_space, 'grid')
        
        best_score = -np.inf
        best_params = None
        all_results = []
        
        for i, params in enumerate(combinations):
            if i % 100 == 0:
                self.logger.info(f"Evaluando combinación {i+1}/{len(combinations)}")
                
            # Validación cruzada
            cv_score, cv_scores = self.time_series_cross_validation(data, params, strategy_func)
            
            result = {
                'params': params,
                'cv_score': cv_score,
                'cv_scores': cv_scores,
                'cv_std': np.std(cv_scores)
            }
            
            all_results.append(result)
            
            if cv_score > best_score:
                best_score = cv_score
                best_params = params.copy()
                
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=all_results,
            optimization_time=0,
            total_evaluations=len(combinations),
            convergence_history=[],
            validation_scores=[r['cv_score'] for r in all_results],
            out_of_sample_score=best_score,
            stability_score=0,
            robustness_score=0
        )
        
    def random_search_optimization(self, data: pd.DataFrame, parameter_space: List[ParameterSpace],
                                 strategy_func: Callable) -> OptimizationResult:
        """Optimización por búsqueda aleatoria"""
        
        combinations = self.create_parameter_combinations(parameter_space, 'random')
        
        best_score = -np.inf
        best_params = None
        all_results = []
        convergence_history = []
        
        for i, params in enumerate(combinations):
            if i % 50 == 0:
                self.logger.info(f"Evaluando combinación {i+1}/{len(combinations)}")
                
            # Validación cruzada
            cv_score, cv_scores = self.time_series_cross_validation(data, params, strategy_func)
            
            result = {
                'params': params,
                'cv_score': cv_score,
                'cv_scores': cv_scores,
                'cv_std': np.std(cv_scores)
            }
            
            all_results.append(result)
            
            if cv_score > best_score:
                best_score = cv_score
                best_params = params.copy()
                
            convergence_history.append(best_score)
            
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=all_results,
            optimization_time=0,
            total_evaluations=len(combinations),
            convergence_history=convergence_history,
            validation_scores=[r['cv_score'] for r in all_results],
            out_of_sample_score=best_score,
            stability_score=0,
            robustness_score=np.std([r['cv_score'] for r in all_results])
        )
        
    def differential_evolution_optimization(self, data: pd.DataFrame, parameter_space: List[ParameterSpace],
                                          strategy_func: Callable) -> OptimizationResult:
        """Optimización por evolución diferencial"""
        
        # Preparar bounds para scipy
        bounds = []
        param_names = []
        
        for param in parameter_space:
            if param.param_type in ['int', 'float']:
                bounds.append((param.min_value, param.max_value))
                param_names.append(param.name)
            else:
                # Para parámetros categóricos, usar índices
                bounds.append((0, len(param.choices) - 1))
                param_names.append(param.name)
                
        # Función objetivo
        def objective_function(x):
            params = {}
            for i, (name, param) in enumerate(zip(param_names, parameter_space)):
                if param.param_type == 'int':
                    params[name] = int(round(x[i]))
                elif param.param_type == 'float':
                    params[name] = x[i]
                elif param.param_type == 'choice':
                    idx = int(round(x[i]))
                    params[name] = param.choices[min(idx, len(param.choices) - 1)]
                    
            # Validación cruzada
            cv_score, _ = self.time_series_cross_validation(data, params, strategy_func)
            return -cv_score  # Minimizar (scipy minimiza)
            
        # Ejecutar optimización
        result = differential_evolution(
            objective_function,
            bounds,
            maxiter=self.max_generations,
            popsize=15,
            seed=42,
            disp=True
        )
        
        # Convertir resultado
        best_params = {}
        for i, (name, param) in enumerate(zip(param_names, parameter_space)):
            if param.param_type == 'int':
                best_params[name] = int(round(result.x[i]))
            elif param.param_type == 'float':
                best_params[name] = result.x[i]
            elif param.param_type == 'choice':
                idx = int(round(result.x[i]))
                best_params[name] = param.choices[min(idx, len(param.choices) - 1)]
                
        return OptimizationResult(
            best_params=best_params,
            best_score=-result.fun,
            all_results=[],
            optimization_time=0,
            total_evaluations=result.nfev,
            convergence_history=[],
            validation_scores=[],
            out_of_sample_score=-result.fun,
            stability_score=0,
            robustness_score=0
        )
        
    def bayesian_optimization(self, data: pd.DataFrame, parameter_space: List[ParameterSpace],
                            strategy_func: Callable) -> OptimizationResult:
        """Optimización bayesiana (requiere scikit-optimize)"""
        
        try:
            from skopt import gp_minimize
            from skopt.space import Real, Integer, Categorical
            
            # Preparar espacio de búsqueda
            dimensions = []
            param_names = []
            
            for param in parameter_space:
                param_names.append(param.name)
                
                if param.param_type == 'int':
                    dimensions.append(Integer(param.min_value, param.max_value))
                elif param.param_type == 'float':
                    dimensions.append(Real(param.min_value, param.max_value))
                elif param.param_type == 'choice':
                    dimensions.append(Categorical(param.choices))
                    
            # Función objetivo
            def objective_function(x):
                params = dict(zip(param_names, x))
                cv_score, _ = self.time_series_cross_validation(data, params, strategy_func)
                return -cv_score  # Minimizar
                
            # Ejecutar optimización
            result = gp_minimize(
                objective_function,
                dimensions,
                n_calls=min(self.max_evaluations, 200),
                random_state=42
            )
            
            best_params = dict(zip(param_names, result.x))
            
            return OptimizationResult(
                best_params=best_params,
                best_score=-result.fun,
                all_results=[],
                optimization_time=0,
                total_evaluations=len(result.func_vals),
                convergence_history=[-val for val in result.func_vals],
                validation_scores=[],
                out_of_sample_score=-result.fun,
                stability_score=0,
                robustness_score=0
            )
            
        except ImportError:
            self.logger.warning("scikit-optimize no disponible, usando búsqueda aleatoria")
            return self.random_search_optimization(data, parameter_space, strategy_func)
            
    def calculate_parameter_stability(self, params_history: List[Dict]) -> float:
        """Calcular estabilidad de parámetros a lo largo del tiempo"""
        
        if len(params_history) < 2:
            return 1.0
            
        # Calcular variabilidad de cada parámetro
        param_variations = {}
        
        for param_name in params_history[0].keys():
            values = [params[param_name] for params in params_history]
            
            if isinstance(values[0], (int, float)):
                # Parámetro numérico
                cv = np.std(values) / (abs(np.mean(values)) + 1e-6)
                param_variations[param_name] = cv
            else:
                # Parámetro categórico
                unique_values = len(set(values))
                param_variations[param_name] = unique_values / len(values)
                
        # Estabilidad promedio (menor variación = mayor estabilidad)
        avg_variation = np.mean(list(param_variations.values()))
        stability = 1 / (1 + avg_variation)
        
        return stability
        
    def average_parameters(self, params_history: List[Dict]) -> Dict:
        """Promediar parámetros de múltiples optimizaciones"""
        
        if not params_history:
            return {}
            
        if len(params_history) == 1:
            return params_history[0]
            
        averaged_params = {}
        
        for param_name in params_history[0].keys():
            values = [params[param_name] for params in params_history]
            
            if isinstance(values[0], (int, float)):
                # Parámetro numérico - promediar
                avg_value = np.mean(values)
                if isinstance(values[0], int):
                    averaged_params[param_name] = int(round(avg_value))
                else:
                    averaged_params[param_name] = avg_value
            else:
                # Parámetro categórico - moda
                from collections import Counter
                counter = Counter(values)
                averaged_params[param_name] = counter.most_common(1)[0][0]
                
        return averaged_params
        
    def stress_test_parameters(self, params: Dict, data: pd.DataFrame,
                             strategy_func: Callable, stress_scenarios: List[str]) -> Dict[str, float]:
        """Probar parámetros bajo diferentes escenarios de estrés"""
        
        stress_results = {}
        
        for scenario in stress_scenarios:
            # Modificar datos según escenario
            stressed_data = self.apply_stress_scenario(data, scenario)
            
            # Evaluar parámetros
            metrics = self.evaluate_parameters(params, stressed_data, strategy_func)
            score = self.calculate_objective_score(metrics)
            
            stress_results[scenario] = score
            
        return stress_results
        
    def apply_stress_scenario(self, data: pd.DataFrame, scenario: str) -> pd.DataFrame:
        """Aplicar escenario de estrés a los datos"""
        
        stressed_data = data.copy()
        
        if scenario == 'high_volatility':
            # Aumentar volatilidad
            returns = stressed_data['close'].pct_change()
            stressed_returns = returns * 2  # Duplicar volatilidad
            stressed_data['close'] = stressed_data['close'].iloc[0] * (1 + stressed_returns).cumprod()
            
        elif scenario == 'trending_market':
            # Agregar tendencia fuerte
            trend = np.linspace(0, 0.5, len(stressed_data))  # 50% de tendencia
            stressed_data['close'] *= (1 + trend)
            
        elif scenario == 'sideways_market':
            # Mercado lateral con ruido
            noise = np.random.normal(0, 0.01, len(stressed_data))
            stressed_data['close'] *= (1 + noise)
            
        elif scenario == 'low_volume':
            # Reducir volumen
            stressed_data['volume'] *= 0.3
            
        elif scenario == 'gap_events':
            # Agregar gaps aleatorios
            gap_indices = np.random.choice(len(stressed_data), size=5, replace=False)
            for idx in gap_indices:
                gap_size = np.random.uniform(-0.05, 0.05)  # ±5% gap
                stressed_data.loc[stressed_data.index[idx]:, 'close'] *= (1 + gap_size)
                
        return stressed_data
        
    def generate_optimization_report(self, result: OptimizationResult) -> Dict:
        """Generar reporte completo de optimización"""
        
        report = {
            'timestamp': datetime.now(),
            'optimization_summary': {
                'best_score': result.best_score,
                'total_evaluations': result.total_evaluations,
                'optimization_time': result.optimization_time,
                'out_of_sample_score': result.out_of_sample_score,
                'stability_score': result.stability_score,
                'robustness_score': result.robustness_score
            },
            'best_parameters': result.best_params,
            'validation_scores': {
                'mean': np.mean(result.validation_scores) if result.validation_scores else 0,
                'std': np.std(result.validation_scores) if result.validation_scores else 0,
                'min': np.min(result.validation_scores) if result.validation_scores else 0,
                'max': np.max(result.validation_scores) if result.validation_scores else 0
            },
            'convergence_analysis': {
                'converged': len(result.convergence_history) > 0,
                'final_improvement': 0,
                'convergence_rate': 0
            }
        }
        
        if result.convergence_history:
            improvements = np.diff(result.convergence_history)
            report['convergence_analysis']['final_improvement'] = improvements[-10:].mean() if len(improvements) >= 10 else 0
            report['convergence_analysis']['convergence_rate'] = len([i for i in improvements if i > 0]) / len(improvements)
            
        return report
        
if __name__ == "__main__":
    # Ejemplo de uso
    optimizer = ParameterOptimizer(target_daily_return=0.006)
    
    # Definir espacio de parámetros
    parameter_space = optimizer.define_parameter_space()
    
    # Generar datos de prueba
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='H')
    test_data = pd.DataFrame({
        'open': np.random.normal(50000, 1000, len(dates)),
        'high': np.random.normal(51000, 1000, len(dates)),
        'low': np.random.normal(49000, 1000, len(dates)),
        'close': np.random.normal(50000, 1000, len(dates)),
        'volume': np.random.normal(1000, 200, len(dates))
    }, index=dates)
    
    # Función de estrategia de prueba
    def test_strategy(data, params):
        # Estrategia simple de prueba
        trades = []
        for i in range(10):
            trades.append({
                'pnl': np.random.normal(5, 20),
                'entry_time': datetime.now(),
                'exit_time': datetime.now() + timedelta(hours=2)
            })
        
        equity_curve = [500 + i * 2 for i in range(len(data))]
        
        return {
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    # Ejecutar optimización
    result = optimizer.optimize_parameters(
        test_data[:1000],  # Usar subset para prueba
        parameter_space[:5],  # Usar subset de parámetros
        test_strategy,
        method='random_search'
    )
    
    # Generar reporte
    report = optimizer.generate_optimization_report(result)
    
    print("=== REPORTE DE OPTIMIZACIÓN ===")
    print(f"Mejor score: {report['optimization_summary']['best_score']:.6f}")
    print(f"Evaluaciones totales: {report['optimization_summary']['total_evaluations']}")
    print(f"Tiempo de optimización: {report['optimization_summary']['optimization_time']:.2f}s")
    print(f"Mejores parámetros: {report['best_parameters']}")