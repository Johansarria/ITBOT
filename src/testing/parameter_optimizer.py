"""
SICAR Parameter Optimization System - Phase 7-8
Robust parameter optimization with overfitting prevention and statistical validation
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
import json
import logging
from pathlib import Path
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp
from scipy import stats, optimize
from sklearn.model_selection import ParameterGrid, RandomizedSearchCV
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, RBF, ConstantKernel
import optuna
from hyperopt import fmin, tpe, hp, Trials, STATUS_OK
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
warnings.filterwarnings('ignore')

class OptimizationMethod(Enum):
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC_ALGORITHM = "genetic_algorithm"
    OPTUNA = "optuna"
    HYPEROPT = "hyperopt"

class OverfittingPrevention(Enum):
    WALK_FORWARD = "walk_forward"
    OUT_OF_SAMPLE = "out_of_sample"
    CROSS_VALIDATION = "cross_validation"
    MONTE_CARLO = "monte_carlo"
    BOOTSTRAP = "bootstrap"

class ObjectiveFunction(Enum):
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    PROFIT_FACTOR = "profit_factor"
    EXPECTANCY = "expectancy"
    CUSTOM_SCORE = "custom_score"

@dataclass
class ParameterRange:
    name: str
    min_value: Union[int, float]
    max_value: Union[int, float]
    step: Optional[Union[int, float]] = None
    param_type: str = "float"  # 'int', 'float', 'categorical'
    categorical_values: Optional[List[Any]] = None
    distribution: str = "uniform"  # 'uniform', 'normal', 'log_uniform'

@dataclass
class OptimizationResult:
    best_params: Dict[str, Any]
    best_score: float
    optimization_history: List[Dict[str, Any]] = field(default_factory=list)
    validation_scores: Dict[str, float] = field(default_factory=dict)
    overfitting_metrics: Dict[str, float] = field(default_factory=dict)
    statistical_significance: Dict[str, float] = field(default_factory=dict)
    convergence_analysis: Dict[str, Any] = field(default_factory=dict)
    robustness_analysis: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OptimizationConfig:
    method: OptimizationMethod = OptimizationMethod.BAYESIAN
    objective: ObjectiveFunction = ObjectiveFunction.SHARPE_RATIO
    overfitting_prevention: List[OverfittingPrevention] = field(default_factory=lambda: [OverfittingPrevention.WALK_FORWARD])
    max_iterations: int = 100
    n_jobs: int = -1
    random_state: int = 42
    early_stopping_rounds: int = 20
    min_improvement: float = 0.001
    validation_split: float = 0.3
    cross_validation_folds: int = 5
    monte_carlo_runs: int = 1000
    bootstrap_samples: int = 500
    significance_level: float = 0.05

class ParameterOptimizer:
    """
    Advanced parameter optimization system with overfitting prevention
    Implements multiple optimization algorithms and validation methods
    """
    
    def __init__(self, data_source: str = "data/phase7_8_real_data/market_data.db"):
        self.data_source = data_source
        self.results_dir = Path("results/optimization")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logging()
        self.config = OptimizationConfig()
        
        # Optimization methods
        self.optimization_methods = {
            OptimizationMethod.GRID_SEARCH: self._grid_search_optimization,
            OptimizationMethod.RANDOM_SEARCH: self._random_search_optimization,
            OptimizationMethod.BAYESIAN: self._bayesian_optimization,
            OptimizationMethod.OPTUNA: self._optuna_optimization,
            OptimizationMethod.HYPEROPT: self._hyperopt_optimization,
        }
        
        # Objective functions
        self.objective_functions = {
            ObjectiveFunction.SHARPE_RATIO: self._sharpe_objective,
            ObjectiveFunction.SORTINO_RATIO: self._sortino_objective,
            ObjectiveFunction.CALMAR_RATIO: self._calmar_objective,
            ObjectiveFunction.PROFIT_FACTOR: self._profit_factor_objective,
            ObjectiveFunction.EXPECTANCY: self._expectancy_objective,
        }
        
        # Overfitting prevention methods
        self.prevention_methods = {
            OverfittingPrevention.WALK_FORWARD: self._walk_forward_validation,
            OverfittingPrevention.OUT_OF_SAMPLE: self._out_of_sample_validation,
            OverfittingPrevention.CROSS_VALIDATION: self._cross_validation,
            OverfittingPrevention.MONTE_CARLO: self._monte_carlo_validation,
            OverfittingPrevention.BOOTSTRAP: self._bootstrap_validation,
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for optimization"""
        logger = logging.getLogger("ParameterOptimizer")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(self.results_dir / "optimization.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    async def optimize_strategy_parameters(
        self,
        strategy_func: Callable,
        parameter_ranges: List[ParameterRange],
        data: pd.DataFrame,
        symbol: str,
        config: Optional[OptimizationConfig] = None
    ) -> OptimizationResult:
        """
        Optimize strategy parameters with overfitting prevention
        """
        
        if config:
            self.config = config
            
        self.logger.info(f"Starting parameter optimization for {strategy_func.__name__}")
        self.logger.info(f"Symbol: {symbol}, Data points: {len(data)}")
        self.logger.info(f"Method: {self.config.method.value}")
        self.logger.info(f"Objective: {self.config.objective.value}")
        
        start_time = time.time()
        
        # Prepare parameter space
        param_space = self._prepare_parameter_space(parameter_ranges)
        
        # Run optimization
        optimization_method = self.optimization_methods[self.config.method]
        result = await optimization_method(strategy_func, param_space, data, symbol)
        
        # Apply overfitting prevention
        result = await self._apply_overfitting_prevention(
            strategy_func, result, data, symbol, parameter_ranges
        )
        
        # Statistical validation
        result = await self._statistical_validation(
            strategy_func, result, data, symbol, parameter_ranges
        )
        
        # Robustness analysis
        result = await self._robustness_analysis(
            strategy_func, result, data, symbol, parameter_ranges
        )
        
        optimization_time = time.time() - start_time
        self.logger.info(f"Optimization completed in {optimization_time:.2f} seconds")
        
        # Save results
        await self._save_optimization_results(result, symbol, strategy_func.__name__)
        
        return result
        
    def _prepare_parameter_space(self, parameter_ranges: List[ParameterRange]) -> Dict[str, Any]:
        """Prepare parameter space for optimization"""
        
        param_space = {}
        
        for param_range in parameter_ranges:
            if param_range.param_type == "categorical":
                param_space[param_range.name] = param_range.categorical_values
            elif param_range.param_type == "int":
                if param_range.step:
                    param_space[param_range.name] = list(range(
                        int(param_range.min_value),
                        int(param_range.max_value) + 1,
                        int(param_range.step)
                    ))
                else:
                    param_space[param_range.name] = (int(param_range.min_value), int(param_range.max_value))
            else:  # float
                param_space[param_range.name] = (param_range.min_value, param_range.max_value)
                
        return param_space
        
    async def _grid_search_optimization(
        self,
        strategy_func: Callable,
        param_space: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> OptimizationResult:
        """Grid search optimization"""
        
        self.logger.info("Running grid search optimization")
        
        # Create parameter grid
        grid_params = {}
        for param_name, param_values in param_space.items():
            if isinstance(param_values, tuple):
                # Create grid for continuous parameters
                min_val, max_val = param_values
                if isinstance(min_val, int):
                    grid_params[param_name] = list(range(min_val, max_val + 1, max(1, (max_val - min_val) // 10)))
                else:
                    grid_params[param_name] = np.linspace(min_val, max_val, 11).tolist()
            else:
                grid_params[param_name] = param_values
                
        param_grid = list(ParameterGrid(grid_params))
        
        best_score = -np.inf
        best_params = {}
        optimization_history = []
        
        for i, params in enumerate(param_grid):
            if i >= self.config.max_iterations:
                break
                
            score = await self._evaluate_parameters(strategy_func, params, data, symbol)
            
            optimization_history.append({
                'iteration': i,
                'params': params.copy(),
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
                
            if i % 10 == 0:
                self.logger.info(f"Grid search progress: {i}/{min(len(param_grid), self.config.max_iterations)}")
                
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            optimization_history=optimization_history
        )
        
    async def _random_search_optimization(
        self,
        strategy_func: Callable,
        param_space: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> OptimizationResult:
        """Random search optimization"""
        
        self.logger.info("Running random search optimization")
        
        best_score = -np.inf
        best_params = {}
        optimization_history = []
        
        for i in range(self.config.max_iterations):
            # Sample random parameters
            params = {}
            for param_name, param_values in param_space.items():
                if isinstance(param_values, tuple):
                    min_val, max_val = param_values
                    if isinstance(min_val, int):
                        params[param_name] = np.random.randint(min_val, max_val + 1)
                    else:
                        params[param_name] = np.random.uniform(min_val, max_val)
                else:
                    params[param_name] = np.random.choice(param_values)
                    
            score = await self._evaluate_parameters(strategy_func, params, data, symbol)
            
            optimization_history.append({
                'iteration': i,
                'params': params.copy(),
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
                
            if i % 20 == 0:
                self.logger.info(f"Random search progress: {i}/{self.config.max_iterations}")
                
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            optimization_history=optimization_history
        )
        
    async def _bayesian_optimization(
        self,
        strategy_func: Callable,
        param_space: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> OptimizationResult:
        """Bayesian optimization using Gaussian Process"""
        
        self.logger.info("Running Bayesian optimization")
        
        # Prepare for Gaussian Process
        param_names = list(param_space.keys())
        param_bounds = []
        
        for param_name in param_names:
            param_values = param_space[param_name]
            if isinstance(param_values, tuple):
                param_bounds.append(param_values)
            else:
                param_bounds.append((0, len(param_values) - 1))
                
        param_bounds = np.array(param_bounds)
        
        # Initialize with random samples
        n_initial = min(10, self.config.max_iterations // 4)
        X_samples = []
        y_samples = []
        
        for i in range(n_initial):
            x = np.random.uniform(param_bounds[:, 0], param_bounds[:, 1])
            params = self._decode_parameters(x, param_names, param_space)
            score = await self._evaluate_parameters(strategy_func, params, data, symbol)
            
            X_samples.append(x)
            y_samples.append(score)
            
        X_samples = np.array(X_samples)
        y_samples = np.array(y_samples)
        
        # Gaussian Process
        kernel = ConstantKernel(1.0) * Matern(length_scale=1.0, nu=2.5)
        gp = GaussianProcessRegressor(kernel=kernel, alpha=1e-6, normalize_y=True)
        
        best_score = np.max(y_samples)
        best_params = self._decode_parameters(X_samples[np.argmax(y_samples)], param_names, param_space)
        optimization_history = []
        
        for i in range(len(y_samples)):
            optimization_history.append({
                'iteration': i,
                'params': self._decode_parameters(X_samples[i], param_names, param_space),
                'score': y_samples[i]
            })
            
        # Bayesian optimization loop
        for i in range(n_initial, self.config.max_iterations):
            # Fit GP
            gp.fit(X_samples, y_samples)
            
            # Acquisition function (Expected Improvement)
            def acquisition(x):
                x = x.reshape(1, -1)
                mu, sigma = gp.predict(x, return_std=True)
                improvement = mu - best_score - 0.01
                Z = improvement / sigma
                ei = improvement * stats.norm.cdf(Z) + sigma * stats.norm.pdf(Z)
                return -ei[0]  # Minimize negative EI
                
            # Optimize acquisition function
            result = optimize.minimize(
                acquisition,
                x0=np.random.uniform(param_bounds[:, 0], param_bounds[:, 1]),
                bounds=param_bounds,
                method='L-BFGS-B'
            )
            
            x_next = result.x
            params = self._decode_parameters(x_next, param_names, param_space)
            score = await self._evaluate_parameters(strategy_func, params, data, symbol)
            
            # Update samples
            X_samples = np.vstack([X_samples, x_next])
            y_samples = np.append(y_samples, score)
            
            optimization_history.append({
                'iteration': i,
                'params': params,
                'score': score
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
                
            if i % 10 == 0:
                self.logger.info(f"Bayesian optimization progress: {i}/{self.config.max_iterations}")
                
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            optimization_history=optimization_history
        )
        
    async def _optuna_optimization(
        self,
        strategy_func: Callable,
        param_space: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> OptimizationResult:
        """Optuna optimization"""
        
        self.logger.info("Running Optuna optimization")
        
        optimization_history = []
        
        def objective(trial):
            params = {}
            for param_name, param_values in param_space.items():
                if isinstance(param_values, tuple):
                    min_val, max_val = param_values
                    if isinstance(min_val, int):
                        params[param_name] = trial.suggest_int(param_name, min_val, max_val)
                    else:
                        params[param_name] = trial.suggest_float(param_name, min_val, max_val)
                else:
                    params[param_name] = trial.suggest_categorical(param_name, param_values)
                    
            # Run evaluation synchronously within the objective
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            score = loop.run_until_complete(
                self._evaluate_parameters(strategy_func, params, data, symbol)
            )
            loop.close()
            
            optimization_history.append({
                'iteration': trial.number,
                'params': params.copy(),
                'score': score
            })
            
            return score
            
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=self.config.max_iterations)
        
        return OptimizationResult(
            best_params=study.best_params,
            best_score=study.best_value,
            optimization_history=optimization_history
        )
        
    async def _hyperopt_optimization(
        self,
        strategy_func: Callable,
        param_space: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> OptimizationResult:
        """HyperOpt optimization"""
        
        self.logger.info("Running HyperOpt optimization")
        
        # Convert parameter space to HyperOpt format
        hyperopt_space = {}
        for param_name, param_values in param_space.items():
            if isinstance(param_values, tuple):
                min_val, max_val = param_values
                if isinstance(min_val, int):
                    hyperopt_space[param_name] = hp.randint(param_name, min_val, max_val + 1)
                else:
                    hyperopt_space[param_name] = hp.uniform(param_name, min_val, max_val)
            else:
                hyperopt_space[param_name] = hp.choice(param_name, param_values)
                
        optimization_history = []
        
        def objective(params):
            # Run evaluation synchronously within the objective
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            score = loop.run_until_complete(
                self._evaluate_parameters(strategy_func, params, data, symbol)
            )
            loop.close()
            
            optimization_history.append({
                'iteration': len(optimization_history),
                'params': params.copy(),
                'score': score
            })
            
            return {'loss': -score, 'status': STATUS_OK}  # HyperOpt minimizes
            
        trials = Trials()
        best = fmin(
            fn=objective,
            space=hyperopt_space,
            algo=tpe.suggest,
            max_evals=self.config.max_iterations,
            trials=trials
        )
        
        best_score = -trials.best_trial['result']['loss']
        
        return OptimizationResult(
            best_params=best,
            best_score=best_score,
            optimization_history=optimization_history
        )
        
    def _decode_parameters(
        self,
        x: np.ndarray,
        param_names: List[str],
        param_space: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Decode parameter vector to parameter dictionary"""
        
        params = {}
        for i, param_name in enumerate(param_names):
            param_values = param_space[param_name]
            if isinstance(param_values, tuple):
                min_val, max_val = param_values
                if isinstance(min_val, int):
                    params[param_name] = int(np.round(x[i]))
                else:
                    params[param_name] = x[i]
            else:
                idx = int(np.round(x[i]))
                idx = max(0, min(idx, len(param_values) - 1))
                params[param_name] = param_values[idx]
                
        return params
        
    async def _evaluate_parameters(
        self,
        strategy_func: Callable,
        params: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> float:
        """Evaluate strategy with given parameters"""
        
        try:
            # Run strategy (placeholder implementation)
            # In practice, this would call the actual strategy function
            trades = await self._simulate_strategy(params, data, symbol)
            
            # Calculate objective function
            objective_func = self.objective_functions[self.config.objective]
            score = objective_func(trades, data)
            
            return score
            
        except Exception as e:
            self.logger.warning(f"Error evaluating parameters {params}: {str(e)}")
            return -np.inf
            
    async def _simulate_strategy(
        self,
        params: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> List[Dict[str, Any]]:
        """Simulate strategy execution (placeholder)"""
        
        # Simple moving average crossover simulation
        short_ma = params.get('short_ma', 20)
        long_ma = params.get('long_ma', 50)
        
        if short_ma >= long_ma:
            return []
            
        data = data.copy()
        data['short_ma'] = data['close'].rolling(short_ma).mean()
        data['long_ma'] = data['close'].rolling(long_ma).mean()
        
        trades = []
        position = 0
        entry_price = 0
        entry_time = None
        
        for timestamp, row in data.iterrows():
            if pd.isna(row['short_ma']) or pd.isna(row['long_ma']):
                continue
                
            # Long signal
            if position == 0 and row['short_ma'] > row['long_ma']:
                position = 1
                entry_price = row['close']
                entry_time = timestamp
                
            # Exit signal
            elif position == 1 and row['short_ma'] < row['long_ma']:
                exit_price = row['close']
                pnl_pct = (exit_price - entry_price) / entry_price
                
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': timestamp,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'duration': (timestamp - entry_time).total_seconds() / 3600
                })
                
                position = 0
                
        return trades
        
    def _sharpe_objective(self, trades: List[Dict[str, Any]], data: pd.DataFrame) -> float:
        """Calculate Sharpe ratio objective"""
        if not trades:
            return -np.inf
            
        returns = [trade['pnl_pct'] for trade in trades]
        if len(returns) < 2:
            return -np.inf
            
        excess_returns = np.array(returns) - 0.02 / 252  # Risk-free rate
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else -np.inf
        
    def _sortino_objective(self, trades: List[Dict[str, Any]], data: pd.DataFrame) -> float:
        """Calculate Sortino ratio objective"""
        if not trades:
            return -np.inf
            
        returns = [trade['pnl_pct'] for trade in trades]
        if len(returns) < 2:
            return -np.inf
            
        excess_returns = np.array(returns) - 0.02 / 252
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return np.inf
            
        downside_deviation = np.std(downside_returns)
        return np.mean(excess_returns) / downside_deviation * np.sqrt(252) if downside_deviation > 0 else -np.inf
        
    def _calmar_objective(self, trades: List[Dict[str, Any]], data: pd.DataFrame) -> float:
        """Calculate Calmar ratio objective"""
        if not trades:
            return -np.inf
            
        # Calculate total return and max drawdown
        cumulative_returns = np.cumprod([1 + trade['pnl_pct'] for trade in trades])
        total_return = cumulative_returns[-1] - 1
        
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(np.min(drawdowns))
        
        return total_return / max_drawdown if max_drawdown > 0 else -np.inf
        
    def _profit_factor_objective(self, trades: List[Dict[str, Any]], data: pd.DataFrame) -> float:
        """Calculate profit factor objective"""
        if not trades:
            return -np.inf
            
        gross_profit = sum(trade['pnl_pct'] for trade in trades if trade['pnl_pct'] > 0)
        gross_loss = abs(sum(trade['pnl_pct'] for trade in trades if trade['pnl_pct'] < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else np.inf
        
    def _expectancy_objective(self, trades: List[Dict[str, Any]], data: pd.DataFrame) -> float:
        """Calculate expectancy objective"""
        if not trades:
            return -np.inf
            
        return np.mean([trade['pnl_pct'] for trade in trades])
        
    async def _apply_overfitting_prevention(
        self,
        strategy_func: Callable,
        result: OptimizationResult,
        data: pd.DataFrame,
        symbol: str,
        parameter_ranges: List[ParameterRange]
    ) -> OptimizationResult:
        """Apply overfitting prevention methods"""
        
        self.logger.info("Applying overfitting prevention methods")
        
        overfitting_metrics = {}
        
        for method in self.config.overfitting_prevention:
            try:
                prevention_func = self.prevention_methods[method]
                metrics = await prevention_func(strategy_func, result.best_params, data, symbol)
                overfitting_metrics[method.value] = metrics
                
            except Exception as e:
                self.logger.warning(f"Error in {method.value}: {str(e)}")
                
        result.overfitting_metrics = overfitting_metrics
        return result
        
    async def _walk_forward_validation(
        self,
        strategy_func: Callable,
        params: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> Dict[str, float]:
        """Walk-forward validation"""
        
        window_size = len(data) // 5  # 5 periods
        step_size = window_size // 2
        
        scores = []
        
        for i in range(0, len(data) - window_size, step_size):
            window_data = data.iloc[i:i + window_size]
            trades = await self._simulate_strategy(params, window_data, symbol)
            score = self._sharpe_objective(trades, window_data)
            
            if score != -np.inf:
                scores.append(score)
                
        return {
            'mean_score': np.mean(scores) if scores else 0.0,
            'std_score': np.std(scores) if scores else 0.0,
            'consistency': 1.0 - np.std(scores) / np.mean(scores) if scores and np.mean(scores) > 0 else 0.0
        }
        
    async def _out_of_sample_validation(
        self,
        strategy_func: Callable,
        params: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> Dict[str, float]:
        """Out-of-sample validation"""
        
        split_point = int(len(data) * (1 - self.config.validation_split))
        oos_data = data.iloc[split_point:]
        
        trades = await self._simulate_strategy(params, oos_data, symbol)
        oos_score = self._sharpe_objective(trades, oos_data)
        
        return {
            'oos_score': oos_score,
            'oos_trades': len(trades),
            'oos_period_length': len(oos_data)
        }
        
    async def _cross_validation(
        self,
        strategy_func: Callable,
        params: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> Dict[str, float]:
        """Cross-validation"""
        
        fold_size = len(data) // self.config.cross_validation_folds
        scores = []
        
        for i in range(self.config.cross_validation_folds):
            start_idx = i * fold_size
            end_idx = start_idx + fold_size
            
            if end_idx > len(data):
                end_idx = len(data)
                
            fold_data = data.iloc[start_idx:end_idx]
            trades = await self._simulate_strategy(params, fold_data, symbol)
            score = self._sharpe_objective(trades, fold_data)
            
            if score != -np.inf:
                scores.append(score)
                
        return {
            'cv_mean': np.mean(scores) if scores else 0.0,
            'cv_std': np.std(scores) if scores else 0.0,
            'cv_min': np.min(scores) if scores else 0.0,
            'cv_max': np.max(scores) if scores else 0.0
        }
        
    async def _monte_carlo_validation(
        self,
        strategy_func: Callable,
        params: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> Dict[str, float]:
        """Monte Carlo validation"""
        
        # Generate bootstrap samples
        scores = []
        
        for _ in range(min(100, self.config.monte_carlo_runs)):  # Limit for demo
            # Bootstrap sample
            sample_indices = np.random.choice(len(data), size=len(data), replace=True)
            sample_data = data.iloc[sample_indices].sort_index()
            
            trades = await self._simulate_strategy(params, sample_data, symbol)
            score = self._sharpe_objective(trades, sample_data)
            
            if score != -np.inf:
                scores.append(score)
                
        return {
            'mc_mean': np.mean(scores) if scores else 0.0,
            'mc_std': np.std(scores) if scores else 0.0,
            'mc_5th_percentile': np.percentile(scores, 5) if scores else 0.0,
            'mc_95th_percentile': np.percentile(scores, 95) if scores else 0.0
        }
        
    async def _bootstrap_validation(
        self,
        strategy_func: Callable,
        params: Dict[str, Any],
        data: pd.DataFrame,
        symbol: str
    ) -> Dict[str, float]:
        """Bootstrap validation"""
        
        # Similar to Monte Carlo but with different sampling strategy
        scores = []
        
        for _ in range(min(50, self.config.bootstrap_samples)):  # Limit for demo
            # Block bootstrap to maintain time series structure
            block_size = len(data) // 10
            n_blocks = len(data) // block_size
            
            sample_data = []
            for _ in range(n_blocks):
                start_idx = np.random.randint(0, len(data) - block_size)
                block = data.iloc[start_idx:start_idx + block_size]
                sample_data.append(block)
                
            if sample_data:
                combined_data = pd.concat(sample_data).sort_index()
                trades = await self._simulate_strategy(params, combined_data, symbol)
                score = self._sharpe_objective(trades, combined_data)
                
                if score != -np.inf:
                    scores.append(score)
                    
        return {
            'bootstrap_mean': np.mean(scores) if scores else 0.0,
            'bootstrap_std': np.std(scores) if scores else 0.0,
            'bootstrap_confidence_lower': np.percentile(scores, 2.5) if scores else 0.0,
            'bootstrap_confidence_upper': np.percentile(scores, 97.5) if scores else 0.0
        }
        
    async def _statistical_validation(
        self,
        strategy_func: Callable,
        result: OptimizationResult,
        data: pd.DataFrame,
        symbol: str,
        parameter_ranges: List[ParameterRange]
    ) -> OptimizationResult:
        """Statistical significance validation"""
        
        self.logger.info("Performing statistical validation")
        
        # Test statistical significance of best parameters
        trades = await self._simulate_strategy(result.best_params, data, symbol)
        
        if trades:
            returns = [trade['pnl_pct'] for trade in trades]
            
            # T-test against zero
            t_stat, p_value = stats.ttest_1samp(returns, 0)
            
            # Normality test
            shapiro_stat, shapiro_p = stats.shapiro(returns) if len(returns) <= 5000 else (0, 1)
            
            # Autocorrelation test (Ljung-Box)
            from statsmodels.stats.diagnostic import acorr_ljungbox
            ljung_box = acorr_ljungbox(returns, lags=10, return_df=True) if len(returns) > 10 else None
            
            result.statistical_significance = {
                't_statistic': t_stat,
                'p_value': p_value,
                'is_significant': p_value < self.config.significance_level,
                'shapiro_statistic': shapiro_stat,
                'shapiro_p_value': shapiro_p,
                'is_normal': shapiro_p > self.config.significance_level,
                'ljung_box_p_min': ljung_box['lb_pvalue'].min() if ljung_box is not None else 1.0
            }
            
        return result
        
    async def _robustness_analysis(
        self,
        strategy_func: Callable,
        result: OptimizationResult,
        data: pd.DataFrame,
        symbol: str,
        parameter_ranges: List[ParameterRange]
    ) -> OptimizationResult:
        """Analyze parameter robustness"""
        
        self.logger.info("Performing robustness analysis")
        
        robustness_metrics = {}
        
        # Parameter sensitivity analysis
        for param_range in parameter_ranges:
            param_name = param_range.name
            base_value = result.best_params[param_name]
            
            # Test parameter variations
            if param_range.param_type in ['int', 'float']:
                variations = []
                scores = []
                
                # Test ±10% variations
                for factor in [0.9, 0.95, 1.05, 1.1]:
                    test_params = result.best_params.copy()
                    
                    if param_range.param_type == 'int':
                        test_value = max(param_range.min_value, 
                                       min(param_range.max_value, int(base_value * factor)))
                    else:
                        test_value = max(param_range.min_value,
                                       min(param_range.max_value, base_value * factor))
                        
                    test_params[param_name] = test_value
                    
                    trades = await self._simulate_strategy(test_params, data, symbol)
                    score = self._sharpe_objective(trades, data)
                    
                    variations.append(test_value)
                    scores.append(score if score != -np.inf else 0)
                    
                # Calculate sensitivity
                if scores and max(scores) > 0:
                    sensitivity = np.std(scores) / np.mean([s for s in scores if s > 0])
                else:
                    sensitivity = np.inf
                    
                robustness_metrics[param_name] = {
                    'sensitivity': sensitivity,
                    'score_range': max(scores) - min(scores) if scores else 0,
                    'stable': sensitivity < 0.5
                }
                
        result.robustness_analysis = robustness_metrics
        return result
        
    async def _save_optimization_results(
        self,
        result: OptimizationResult,
        symbol: str,
        strategy_name: str
    ):
        """Save optimization results"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimization_{strategy_name}_{symbol}_{timestamp}.json"
        filepath = self.results_dir / filename
        
        # Convert result to serializable format
        result_dict = {
            'best_params': result.best_params,
            'best_score': result.best_score,
            'optimization_history': result.optimization_history,
            'validation_scores': result.validation_scores,
            'overfitting_metrics': result.overfitting_metrics,
            'statistical_significance': result.statistical_significance,
            'robustness_analysis': result.robustness_analysis,
            'convergence_analysis': result.convergence_analysis
        }
        
        with open(filepath, 'w') as f:
            json.dump(result_dict, f, indent=2, default=str)
            
        self.logger.info(f"Optimization results saved to {filepath}")
        
    def generate_optimization_report(
        self,
        result: OptimizationResult,
        symbol: str,
        strategy_name: str
    ) -> str:
        """Generate comprehensive optimization report"""
        
        report = f"""
# Parameter Optimization Report

## Strategy: {strategy_name}
## Symbol: {symbol}
## Optimization Method: {self.config.method.value}
## Objective Function: {self.config.objective.value}

## Best Parameters
{json.dumps(result.best_params, indent=2)}

## Performance Metrics
- Best Score: {result.best_score:.4f}
- Total Iterations: {len(result.optimization_history)}

## Overfitting Prevention Results
"""
        
        for method, metrics in result.overfitting_metrics.items():
            report += f"\n### {method.replace('_', ' ').title()}\n"
            for metric, value in metrics.items():
                report += f"- {metric}: {value:.4f}\n"
                
        if result.statistical_significance:
            report += f"""
## Statistical Significance
- T-statistic: {result.statistical_significance.get('t_statistic', 0):.4f}
- P-value: {result.statistical_significance.get('p_value', 1):.4f}
- Significant: {result.statistical_significance.get('is_significant', False)}
- Normal Distribution: {result.statistical_significance.get('is_normal', False)}
"""

        if result.robustness_analysis:
            report += "\n## Parameter Robustness\n"
            for param, analysis in result.robustness_analysis.items():
                report += f"- {param}: Sensitivity = {analysis.get('sensitivity', 0):.4f}, Stable = {analysis.get('stable', False)}\n"
                
        return report

# Demo function
async def demo_parameter_optimization():
    """Demonstrate parameter optimization capabilities"""
    
    print("🔄 SICAR Parameter Optimization System - Phase 7-8 Demo")
    print("=" * 60)
    
    # Initialize optimizer
    optimizer = ParameterOptimizer()
    
    # Define parameter ranges
    parameter_ranges = [
        ParameterRange(
            name="short_ma",
            min_value=5,
            max_value=30,
            param_type="int"
        ),
        ParameterRange(
            name="long_ma",
            min_value=40,
            max_value=100,
            param_type="int"
        ),
        ParameterRange(
            name="risk_factor",
            min_value=0.01,
            max_value=0.1,
            param_type="float"
        )
    ]
    
    # Create sample data
    dates = pd.date_range(start="2020-01-01", end="2023-01-01", freq="1H")
    np.random.seed(42)
    prices = 100 * np.cumprod(1 + np.random.normal(0, 0.001, len(dates)))
    
    sample_data = pd.DataFrame({
        'open': prices * (1 + np.random.normal(0, 0.0005, len(dates))),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.001, len(dates)))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.001, len(dates)))),
        'close': prices,
        'volume': np.random.randint(1000, 10000, len(dates))
    }, index=dates)
    
    print(f"📊 Sample data created: {len(sample_data)} data points")
    print(f"📅 Period: {sample_data.index[0]} to {sample_data.index[-1]}")
    print()
    
    # Configure optimization
    config = OptimizationConfig(
        method=OptimizationMethod.BAYESIAN,
        objective=ObjectiveFunction.SHARPE_RATIO,
        overfitting_prevention=[
            OverfittingPrevention.WALK_FORWARD,
            OverfittingPrevention.OUT_OF_SAMPLE,
            OverfittingPrevention.CROSS_VALIDATION
        ],
        max_iterations=50,
        cross_validation_folds=5
    )
    
    print(f"🎯 Optimization Configuration:")
    print(f"  Method: {config.method.value}")
    print(f"  Objective: {config.objective.value}")
    print(f"  Max Iterations: {config.max_iterations}")
    print(f"  Overfitting Prevention: {[p.value for p in config.overfitting_prevention]}")
    print()
    
    # Define dummy strategy function
    async def dummy_strategy(data, params):
        return []
    
    # Run optimization
    print("🚀 Starting parameter optimization...")
    result = await optimizer.optimize_strategy_parameters(
        strategy_func=dummy_strategy,
        parameter_ranges=parameter_ranges,
        data=sample_data,
        symbol="DEMO",
        config=config
    )
    
    print("📈 Optimization Results:")
    print("-" * 40)
    print(f"Best Parameters: {result.best_params}")
    print(f"Best Score: {result.best_score:.4f}")
    print(f"Total Iterations: {len(result.optimization_history)}")
    print()
    
    print("🔍 Overfitting Prevention Results:")
    for method, metrics in result.overfitting_metrics.items():
        print(f"  {method}:")
        for metric, value in metrics.items():
            print(f"    {metric}: {value:.4f}")
    print()
    
    if result.statistical_significance:
        print("📊 Statistical Significance:")
        print(f"  P-value: {result.statistical_significance.get('p_value', 1):.4f}")
        print(f"  Significant: {result.statistical_significance.get('is_significant', False)}")
        print()
        
    if result.robustness_analysis:
        print("🔒 Parameter Robustness:")
        for param, analysis in result.robustness_analysis.items():
            print(f"  {param}: Sensitivity = {analysis.get('sensitivity', 0):.4f}")
        print()
        
    # Generate report
    report = optimizer.generate_optimization_report(result, "DEMO", "DummyStrategy")
    report_path = "results/optimization/demo_optimization_report.md"
    
    with open(report_path, 'w') as f:
        f.write(report)
        
    print(f"📁 Optimization report saved to: {report_path}")
    print("✅ Parameter optimization demonstration completed!")
    
    return optimizer, result

if __name__ == "__main__":
    asyncio.run(demo_parameter_optimization())