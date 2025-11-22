"""
SICAR Extensive Backtesting Engine - Phase 7-8
Advanced backtesting system with walk-forward analysis, out-of-sample testing, and robust validation
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
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
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import sharpe_ratio
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
warnings.filterwarnings('ignore')

class BacktestType(Enum):
    SIMPLE = "simple"
    WALK_FORWARD = "walk_forward"
    OUT_OF_SAMPLE = "out_of_sample"
    MONTE_CARLO = "monte_carlo"
    CROSS_VALIDATION = "cross_validation"

class ValidationMethod(Enum):
    TIME_SERIES_SPLIT = "time_series_split"
    PURGED_CROSS_VALIDATION = "purged_cross_validation"
    COMBINATORIAL_PURGED = "combinatorial_purged"

class PerformanceMetric(Enum):
    TOTAL_RETURN = "total_return"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    CALMAR_RATIO = "calmar_ratio"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    EXPECTANCY = "expectancy"

@dataclass
class Trade:
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    commission: float = 0.0
    slippage: float = 0.0
    strategy: str = ""
    timeframe: str = ""

@dataclass
class BacktestPeriod:
    start_date: datetime
    end_date: datetime
    period_type: str  # 'in_sample', 'out_of_sample', 'validation'
    trades: List[Trade] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)

@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    backtest_type: BacktestType
    periods: List[BacktestPeriod] = field(default_factory=list)
    overall_metrics: Dict[str, float] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    drawdown_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    monthly_returns: pd.DataFrame = field(default_factory=pd.DataFrame)
    statistics: Dict[str, Any] = field(default_factory=dict)
    validation_scores: Dict[str, float] = field(default_factory=dict)

@dataclass
class WalkForwardConfig:
    training_window: int = 252  # Trading days
    testing_window: int = 63   # Trading days
    step_size: int = 21        # Trading days
    min_trades: int = 10       # Minimum trades per period
    reoptimize: bool = True    # Reoptimize parameters each step

@dataclass
class BacktestConfig:
    initial_capital: float = 100000.0
    commission: float = 0.001  # 0.1%
    slippage: float = 0.0005   # 0.05%
    margin_requirement: float = 1.0  # 100% for no leverage
    max_position_size: float = 0.1   # 10% of capital per position
    risk_free_rate: float = 0.02     # 2% annual
    benchmark_symbol: str = "SPY"
    
class ExtensiveBacktester:
    """
    Advanced backtesting engine for SICAR strategies
    Implements walk-forward analysis, out-of-sample testing, and robust validation
    """
    
    def __init__(self, data_source: str = "data/phase7_8_real_data/market_data.db"):
        self.data_source = data_source
        self.results_dir = Path("results/backtesting")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logging()
        self.config = BacktestConfig()
        
        # Performance metrics calculators
        self.metric_calculators = {
            PerformanceMetric.TOTAL_RETURN: self._calculate_total_return,
            PerformanceMetric.SHARPE_RATIO: self._calculate_sharpe_ratio,
            PerformanceMetric.SORTINO_RATIO: self._calculate_sortino_ratio,
            PerformanceMetric.MAX_DRAWDOWN: self._calculate_max_drawdown,
            PerformanceMetric.CALMAR_RATIO: self._calculate_calmar_ratio,
            PerformanceMetric.WIN_RATE: self._calculate_win_rate,
            PerformanceMetric.PROFIT_FACTOR: self._calculate_profit_factor,
            PerformanceMetric.EXPECTANCY: self._calculate_expectancy,
        }
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for backtesting"""
        logger = logging.getLogger("ExtensiveBacktester")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(self.results_dir / "backtesting.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    async def run_extensive_backtest(
        self,
        strategy_func: Callable,
        symbols: List[str],
        start_date: str = "2020-01-01",
        end_date: str = "2025-01-01",
        timeframes: List[str] = ["1h"],
        backtest_types: List[BacktestType] = None,
        strategy_params: Dict[str, Any] = None
    ) -> Dict[str, List[BacktestResult]]:
        """
        Run extensive backtesting across multiple symbols, timeframes, and methods
        """
        
        if backtest_types is None:
            backtest_types = [BacktestType.WALK_FORWARD, BacktestType.OUT_OF_SAMPLE]
            
        if strategy_params is None:
            strategy_params = {}
            
        self.logger.info(f"Starting extensive backtesting for {len(symbols)} symbols")
        self.logger.info(f"Period: {start_date} to {end_date}")
        self.logger.info(f"Timeframes: {timeframes}")
        self.logger.info(f"Backtest types: {[bt.value for bt in backtest_types]}")
        
        all_results = {}
        
        # Run backtests for each combination
        for symbol in symbols:
            symbol_results = []
            
            for timeframe in timeframes:
                for backtest_type in backtest_types:
                    try:
                        self.logger.info(f"Running {backtest_type.value} backtest for {symbol} on {timeframe}")
                        
                        result = await self._run_single_backtest(
                            strategy_func=strategy_func,
                            symbol=symbol,
                            timeframe=timeframe,
                            start_date=start_date,
                            end_date=end_date,
                            backtest_type=backtest_type,
                            strategy_params=strategy_params
                        )
                        
                        if result:
                            symbol_results.append(result)
                            self.logger.info(f"Completed {backtest_type.value} for {symbol}")
                        
                    except Exception as e:
                        self.logger.error(f"Error in {backtest_type.value} for {symbol}: {str(e)}")
                        
            all_results[symbol] = symbol_results
            
        self.logger.info("Extensive backtesting completed")
        return all_results
        
    async def _run_single_backtest(
        self,
        strategy_func: Callable,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        backtest_type: BacktestType,
        strategy_params: Dict[str, Any]
    ) -> Optional[BacktestResult]:
        """Run a single backtest with specified parameters"""
        
        # Load market data
        data = await self._load_market_data(symbol, start_date, end_date, timeframe)
        if data.empty:
            self.logger.warning(f"No data available for {symbol}")
            return None
            
        # Choose backtest method
        if backtest_type == BacktestType.WALK_FORWARD:
            return await self._run_walk_forward_backtest(
                strategy_func, symbol, timeframe, data, strategy_params
            )
        elif backtest_type == BacktestType.OUT_OF_SAMPLE:
            return await self._run_out_of_sample_backtest(
                strategy_func, symbol, timeframe, data, strategy_params
            )
        elif backtest_type == BacktestType.MONTE_CARLO:
            return await self._run_monte_carlo_backtest(
                strategy_func, symbol, timeframe, data, strategy_params
            )
        elif backtest_type == BacktestType.CROSS_VALIDATION:
            return await self._run_cross_validation_backtest(
                strategy_func, symbol, timeframe, data, strategy_params
            )
        else:
            return await self._run_simple_backtest(
                strategy_func, symbol, timeframe, data, strategy_params
            )
            
    async def _run_walk_forward_backtest(
        self,
        strategy_func: Callable,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame,
        strategy_params: Dict[str, Any]
    ) -> BacktestResult:
        """Run walk-forward analysis backtest"""
        
        wf_config = WalkForwardConfig()
        periods = []
        all_trades = []
        
        # Calculate walk-forward windows
        total_days = len(data)
        current_start = 0
        
        while current_start + wf_config.training_window + wf_config.testing_window < total_days:
            # Define training and testing periods
            train_end = current_start + wf_config.training_window
            test_start = train_end
            test_end = test_start + wf_config.testing_window
            
            train_data = data.iloc[current_start:train_end]
            test_data = data.iloc[test_start:test_end]
            
            # Optimize parameters on training data (if enabled)
            if wf_config.reoptimize:
                optimized_params = await self._optimize_parameters(
                    strategy_func, train_data, strategy_params
                )
            else:
                optimized_params = strategy_params
                
            # Run strategy on test data
            test_trades = await self._run_strategy(
                strategy_func, test_data, optimized_params, symbol, timeframe
            )
            
            # Create period result
            period = BacktestPeriod(
                start_date=test_data.index[0],
                end_date=test_data.index[-1],
                period_type="out_of_sample",
                trades=test_trades
            )
            
            # Calculate period metrics
            period.metrics = self._calculate_period_metrics(test_trades, test_data)
            period.equity_curve = self._calculate_equity_curve(test_trades, test_data)
            
            periods.append(period)
            all_trades.extend(test_trades)
            
            # Move to next window
            current_start += wf_config.step_size
            
        # Create overall result
        result = BacktestResult(
            strategy_name=strategy_func.__name__,
            symbol=symbol,
            timeframe=timeframe,
            start_date=data.index[0],
            end_date=data.index[-1],
            backtest_type=BacktestType.WALK_FORWARD,
            periods=periods,
            trades=all_trades
        )
        
        # Calculate overall metrics
        result.overall_metrics = self._calculate_overall_metrics(all_trades, data)
        result.equity_curve = self._calculate_overall_equity_curve(periods)
        result.drawdown_curve = self._calculate_drawdown_curve(result.equity_curve)
        result.monthly_returns = self._calculate_monthly_returns(result.equity_curve)
        result.statistics = self._calculate_advanced_statistics(result)
        result.validation_scores = self._calculate_validation_scores(periods)
        
        return result
        
    async def _run_out_of_sample_backtest(
        self,
        strategy_func: Callable,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame,
        strategy_params: Dict[str, Any]
    ) -> BacktestResult:
        """Run out-of-sample backtest with 70/30 split"""
        
        # Split data: 70% in-sample, 30% out-of-sample
        split_point = int(len(data) * 0.7)
        in_sample_data = data.iloc[:split_point]
        out_sample_data = data.iloc[split_point:]
        
        # Optimize on in-sample data
        optimized_params = await self._optimize_parameters(
            strategy_func, in_sample_data, strategy_params
        )
        
        # Test on out-of-sample data
        out_sample_trades = await self._run_strategy(
            strategy_func, out_sample_data, optimized_params, symbol, timeframe
        )
        
        # Create periods
        in_sample_period = BacktestPeriod(
            start_date=in_sample_data.index[0],
            end_date=in_sample_data.index[-1],
            period_type="in_sample"
        )
        
        out_sample_period = BacktestPeriod(
            start_date=out_sample_data.index[0],
            end_date=out_sample_data.index[-1],
            period_type="out_of_sample",
            trades=out_sample_trades
        )
        
        out_sample_period.metrics = self._calculate_period_metrics(out_sample_trades, out_sample_data)
        out_sample_period.equity_curve = self._calculate_equity_curve(out_sample_trades, out_sample_data)
        
        # Create result
        result = BacktestResult(
            strategy_name=strategy_func.__name__,
            symbol=symbol,
            timeframe=timeframe,
            start_date=data.index[0],
            end_date=data.index[-1],
            backtest_type=BacktestType.OUT_OF_SAMPLE,
            periods=[in_sample_period, out_sample_period],
            trades=out_sample_trades
        )
        
        result.overall_metrics = self._calculate_overall_metrics(out_sample_trades, out_sample_data)
        result.equity_curve = out_sample_period.equity_curve
        result.drawdown_curve = self._calculate_drawdown_curve(result.equity_curve)
        result.monthly_returns = self._calculate_monthly_returns(result.equity_curve)
        result.statistics = self._calculate_advanced_statistics(result)
        
        return result
        
    async def _run_monte_carlo_backtest(
        self,
        strategy_func: Callable,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame,
        strategy_params: Dict[str, Any],
        n_simulations: int = 1000
    ) -> BacktestResult:
        """Run Monte Carlo simulation backtest"""
        
        # Run base strategy
        base_trades = await self._run_strategy(strategy_func, data, strategy_params, symbol, timeframe)
        
        # Generate Monte Carlo simulations
        simulation_results = []
        
        for i in range(n_simulations):
            # Shuffle trade order while maintaining timing constraints
            shuffled_trades = self._shuffle_trades_monte_carlo(base_trades)
            
            # Calculate metrics for this simulation
            sim_metrics = self._calculate_period_metrics(shuffled_trades, data)
            simulation_results.append(sim_metrics)
            
        # Create result with Monte Carlo statistics
        result = BacktestResult(
            strategy_name=strategy_func.__name__,
            symbol=symbol,
            timeframe=timeframe,
            start_date=data.index[0],
            end_date=data.index[-1],
            backtest_type=BacktestType.MONTE_CARLO,
            trades=base_trades
        )
        
        result.overall_metrics = self._calculate_overall_metrics(base_trades, data)
        result.equity_curve = self._calculate_equity_curve(base_trades, data)
        result.statistics = self._calculate_monte_carlo_statistics(simulation_results)
        
        return result
        
    async def _run_cross_validation_backtest(
        self,
        strategy_func: Callable,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame,
        strategy_params: Dict[str, Any],
        n_splits: int = 5
    ) -> BacktestResult:
        """Run time series cross-validation backtest"""
        
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_results = []
        all_trades = []
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(data)):
            train_data = data.iloc[train_idx]
            test_data = data.iloc[test_idx]
            
            # Optimize on training fold
            optimized_params = await self._optimize_parameters(
                strategy_func, train_data, strategy_params
            )
            
            # Test on validation fold
            fold_trades = await self._run_strategy(
                strategy_func, test_data, optimized_params, symbol, timeframe
            )
            
            fold_metrics = self._calculate_period_metrics(fold_trades, test_data)
            cv_results.append(fold_metrics)
            all_trades.extend(fold_trades)
            
        # Create result
        result = BacktestResult(
            strategy_name=strategy_func.__name__,
            symbol=symbol,
            timeframe=timeframe,
            start_date=data.index[0],
            end_date=data.index[-1],
            backtest_type=BacktestType.CROSS_VALIDATION,
            trades=all_trades
        )
        
        result.overall_metrics = self._calculate_overall_metrics(all_trades, data)
        result.equity_curve = self._calculate_equity_curve(all_trades, data)
        result.statistics = self._calculate_cross_validation_statistics(cv_results)
        result.validation_scores = self._calculate_cv_validation_scores(cv_results)
        
        return result
        
    async def _load_market_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        timeframe: str
    ) -> pd.DataFrame:
        """Load market data from database"""
        
        try:
            with sqlite3.connect(self.data_source) as conn:
                query = """
                    SELECT timestamp, open, high, low, close, volume
                    FROM market_data
                    WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp
                """
                
                start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
                end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
                
                df = pd.read_sql_query(query, conn, params=(symbol, start_ts, end_ts))
                
                if not df.empty:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                    df.set_index('timestamp', inplace=True)
                    
                return df
                
        except Exception as e:
            self.logger.error(f"Error loading data for {symbol}: {str(e)}")
            return pd.DataFrame()
            
    async def _run_strategy(
        self,
        strategy_func: Callable,
        data: pd.DataFrame,
        params: Dict[str, Any],
        symbol: str,
        timeframe: str
    ) -> List[Trade]:
        """Run strategy on data and return trades"""
        
        try:
            # This is a placeholder - actual strategy execution would depend on strategy implementation
            # For demo purposes, we'll simulate some trades
            trades = []
            
            # Simple moving average crossover example
            short_ma = params.get('short_ma', 20)
            long_ma = params.get('long_ma', 50)
            
            data['short_ma'] = data['close'].rolling(short_ma).mean()
            data['long_ma'] = data['close'].rolling(long_ma).mean()
            
            position = 0
            entry_price = 0
            entry_time = None
            
            for i, (timestamp, row) in enumerate(data.iterrows()):
                if i < long_ma:  # Not enough data for indicators
                    continue
                    
                # Long signal
                if position == 0 and row['short_ma'] > row['long_ma']:
                    position = 1
                    entry_price = row['close']
                    entry_time = timestamp
                    
                # Exit signal
                elif position == 1 and row['short_ma'] < row['long_ma']:
                    exit_price = row['close']
                    pnl = (exit_price - entry_price) * self.config.max_position_size * self.config.initial_capital / entry_price
                    pnl_pct = (exit_price - entry_price) / entry_price
                    
                    trade = Trade(
                        entry_time=entry_time,
                        exit_time=timestamp,
                        symbol=symbol,
                        side='long',
                        entry_price=entry_price,
                        exit_price=exit_price,
                        quantity=self.config.max_position_size * self.config.initial_capital / entry_price,
                        pnl=pnl,
                        pnl_pct=pnl_pct,
                        commission=pnl * self.config.commission,
                        strategy=strategy_func.__name__,
                        timeframe=timeframe
                    )
                    
                    trades.append(trade)
                    position = 0
                    
            return trades
            
        except Exception as e:
            self.logger.error(f"Error running strategy: {str(e)}")
            return []
            
    async def _optimize_parameters(
        self,
        strategy_func: Callable,
        data: pd.DataFrame,
        base_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize strategy parameters on training data"""
        
        # Simple grid search optimization
        # In practice, this would be more sophisticated
        
        best_params = base_params.copy()
        best_sharpe = -np.inf
        
        # Parameter ranges for optimization
        short_ma_range = range(10, 31, 5)
        long_ma_range = range(40, 101, 10)
        
        for short_ma in short_ma_range:
            for long_ma in long_ma_range:
                if short_ma >= long_ma:
                    continue
                    
                test_params = base_params.copy()
                test_params['short_ma'] = short_ma
                test_params['long_ma'] = long_ma
                
                # Run strategy with test parameters
                trades = await self._run_strategy(strategy_func, data, test_params, "TEST", "1h")
                
                if len(trades) > 5:  # Minimum trades for valid test
                    metrics = self._calculate_period_metrics(trades, data)
                    sharpe = metrics.get('sharpe_ratio', -np.inf)
                    
                    if sharpe > best_sharpe:
                        best_sharpe = sharpe
                        best_params = test_params.copy()
                        
        return best_params
        
    def _calculate_period_metrics(self, trades: List[Trade], data: pd.DataFrame) -> Dict[str, float]:
        """Calculate performance metrics for a period"""
        
        if not trades:
            return {metric.value: 0.0 for metric in PerformanceMetric}
            
        metrics = {}
        
        for metric in PerformanceMetric:
            try:
                value = self.metric_calculators[metric](trades, data)
                metrics[metric.value] = value
            except Exception as e:
                self.logger.warning(f"Error calculating {metric.value}: {str(e)}")
                metrics[metric.value] = 0.0
                
        return metrics
        
    def _calculate_total_return(self, trades: List[Trade], data: pd.DataFrame) -> float:
        """Calculate total return"""
        if not trades:
            return 0.0
        return sum(trade.pnl for trade in trades) / self.config.initial_capital
        
    def _calculate_sharpe_ratio(self, trades: List[Trade], data: pd.DataFrame) -> float:
        """Calculate Sharpe ratio"""
        if not trades:
            return 0.0
            
        returns = [trade.pnl_pct for trade in trades]
        if len(returns) < 2:
            return 0.0
            
        excess_returns = np.array(returns) - self.config.risk_free_rate / 252
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252) if np.std(excess_returns) > 0 else 0.0
        
    def _calculate_sortino_ratio(self, trades: List[Trade], data: pd.DataFrame) -> float:
        """Calculate Sortino ratio"""
        if not trades:
            return 0.0
            
        returns = [trade.pnl_pct for trade in trades]
        if len(returns) < 2:
            return 0.0
            
        excess_returns = np.array(returns) - self.config.risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return np.inf
            
        downside_deviation = np.std(downside_returns)
        return np.mean(excess_returns) / downside_deviation * np.sqrt(252) if downside_deviation > 0 else 0.0
        
    def _calculate_max_drawdown(self, trades: List[Trade], data: pd.DataFrame) -> float:
        """Calculate maximum drawdown"""
        if not trades:
            return 0.0
            
        equity_curve = self._calculate_equity_curve(trades, data)
        if equity_curve.empty:
            return 0.0
            
        running_max = equity_curve['equity'].expanding().max()
        drawdown = (equity_curve['equity'] - running_max) / running_max
        return abs(drawdown.min())
        
    def _calculate_calmar_ratio(self, trades: List[Trade], data: pd.DataFrame) -> float:
        """Calculate Calmar ratio"""
        total_return = self._calculate_total_return(trades, data)
        max_drawdown = self._calculate_max_drawdown(trades, data)
        
        return total_return / max_drawdown if max_drawdown > 0 else 0.0
        
    def _calculate_win_rate(self, trades: List[Trade], data: pd.DataFrame) -> float:
        """Calculate win rate"""
        if not trades:
            return 0.0
        winning_trades = sum(1 for trade in trades if trade.pnl > 0)
        return winning_trades / len(trades)
        
    def _calculate_profit_factor(self, trades: List[Trade], data: pd.DataFrame) -> float:
        """Calculate profit factor"""
        if not trades:
            return 0.0
            
        gross_profit = sum(trade.pnl for trade in trades if trade.pnl > 0)
        gross_loss = abs(sum(trade.pnl for trade in trades if trade.pnl < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else np.inf
        
    def _calculate_expectancy(self, trades: List[Trade], data: pd.DataFrame) -> float:
        """Calculate expectancy"""
        if not trades:
            return 0.0
        return np.mean([trade.pnl for trade in trades])
        
    def _calculate_equity_curve(self, trades: List[Trade], data: pd.DataFrame) -> pd.DataFrame:
        """Calculate equity curve"""
        if not trades:
            return pd.DataFrame()
            
        equity_data = []
        current_equity = self.config.initial_capital
        
        for trade in sorted(trades, key=lambda t: t.exit_time):
            current_equity += trade.pnl - trade.commission
            equity_data.append({
                'timestamp': trade.exit_time,
                'equity': current_equity,
                'pnl': trade.pnl,
                'trade_id': len(equity_data)
            })
            
        return pd.DataFrame(equity_data).set_index('timestamp')
        
    def _calculate_overall_metrics(self, trades: List[Trade], data: pd.DataFrame) -> Dict[str, float]:
        """Calculate overall performance metrics"""
        return self._calculate_period_metrics(trades, data)
        
    def _calculate_overall_equity_curve(self, periods: List[BacktestPeriod]) -> pd.DataFrame:
        """Calculate overall equity curve from periods"""
        all_equity_data = []
        
        for period in periods:
            if not period.equity_curve.empty:
                all_equity_data.append(period.equity_curve)
                
        if all_equity_data:
            return pd.concat(all_equity_data).sort_index()
        else:
            return pd.DataFrame()
            
    def _calculate_drawdown_curve(self, equity_curve: pd.DataFrame) -> pd.DataFrame:
        """Calculate drawdown curve"""
        if equity_curve.empty:
            return pd.DataFrame()
            
        running_max = equity_curve['equity'].expanding().max()
        drawdown = (equity_curve['equity'] - running_max) / running_max
        
        return pd.DataFrame({
            'drawdown': drawdown,
            'running_max': running_max
        }, index=equity_curve.index)
        
    def _calculate_monthly_returns(self, equity_curve: pd.DataFrame) -> pd.DataFrame:
        """Calculate monthly returns"""
        if equity_curve.empty:
            return pd.DataFrame()
            
        monthly_equity = equity_curve['equity'].resample('M').last()
        monthly_returns = monthly_equity.pct_change().dropna()
        
        return pd.DataFrame({
            'monthly_return': monthly_returns,
            'cumulative_return': (1 + monthly_returns).cumprod() - 1
        })
        
    def _calculate_advanced_statistics(self, result: BacktestResult) -> Dict[str, Any]:
        """Calculate advanced statistical measures"""
        
        if not result.trades:
            return {}
            
        returns = [trade.pnl_pct for trade in result.trades]
        
        stats_dict = {
            'total_trades': len(result.trades),
            'avg_trade_duration': np.mean([(trade.exit_time - trade.entry_time).total_seconds() / 3600 for trade in result.trades]),
            'return_skewness': stats.skew(returns) if len(returns) > 2 else 0.0,
            'return_kurtosis': stats.kurtosis(returns) if len(returns) > 2 else 0.0,
            'var_95': np.percentile(returns, 5) if returns else 0.0,
            'cvar_95': np.mean([r for r in returns if r <= np.percentile(returns, 5)]) if returns else 0.0,
        }
        
        return stats_dict
        
    def _calculate_validation_scores(self, periods: List[BacktestPeriod]) -> Dict[str, float]:
        """Calculate validation scores across periods"""
        
        if not periods:
            return {}
            
        sharpe_ratios = [p.metrics.get('sharpe_ratio', 0) for p in periods if p.metrics]
        
        return {
            'consistency_score': 1.0 - np.std(sharpe_ratios) if sharpe_ratios else 0.0,
            'stability_score': np.mean(sharpe_ratios) if sharpe_ratios else 0.0,
            'robustness_score': min(sharpe_ratios) if sharpe_ratios else 0.0,
        }
        
    def _shuffle_trades_monte_carlo(self, trades: List[Trade]) -> List[Trade]:
        """Shuffle trades for Monte Carlo simulation"""
        # Simple shuffle - in practice, would maintain timing constraints
        shuffled = trades.copy()
        np.random.shuffle(shuffled)
        return shuffled
        
    def _calculate_monte_carlo_statistics(self, simulation_results: List[Dict]) -> Dict[str, Any]:
        """Calculate Monte Carlo simulation statistics"""
        
        if not simulation_results:
            return {}
            
        sharpe_ratios = [result.get('sharpe_ratio', 0) for result in simulation_results]
        total_returns = [result.get('total_return', 0) for result in simulation_results]
        
        return {
            'mc_mean_sharpe': np.mean(sharpe_ratios),
            'mc_std_sharpe': np.std(sharpe_ratios),
            'mc_5th_percentile_sharpe': np.percentile(sharpe_ratios, 5),
            'mc_95th_percentile_sharpe': np.percentile(sharpe_ratios, 95),
            'mc_mean_return': np.mean(total_returns),
            'mc_std_return': np.std(total_returns),
        }
        
    def _calculate_cross_validation_statistics(self, cv_results: List[Dict]) -> Dict[str, Any]:
        """Calculate cross-validation statistics"""
        
        if not cv_results:
            return {}
            
        sharpe_ratios = [result.get('sharpe_ratio', 0) for result in cv_results]
        
        return {
            'cv_mean_sharpe': np.mean(sharpe_ratios),
            'cv_std_sharpe': np.std(sharpe_ratios),
            'cv_min_sharpe': min(sharpe_ratios),
            'cv_max_sharpe': max(sharpe_ratios),
        }
        
    def _calculate_cv_validation_scores(self, cv_results: List[Dict]) -> Dict[str, float]:
        """Calculate cross-validation scores"""
        
        if not cv_results:
            return {}
            
        sharpe_ratios = [result.get('sharpe_ratio', 0) for result in cv_results]
        
        return {
            'cv_consistency': 1.0 - np.std(sharpe_ratios) / np.mean(sharpe_ratios) if np.mean(sharpe_ratios) > 0 else 0.0,
            'cv_stability': np.mean(sharpe_ratios),
        }
        
    def generate_backtest_report(self, results: Dict[str, List[BacktestResult]], output_path: str):
        """Generate comprehensive backtest report"""
        
        report_data = {
            'summary': self._generate_summary_statistics(results),
            'detailed_results': self._format_detailed_results(results),
            'validation_analysis': self._analyze_validation_results(results),
            'recommendations': self._generate_recommendations(results)
        }
        
        # Save report
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
            
        self.logger.info(f"Backtest report saved to {output_path}")
        
    def _generate_summary_statistics(self, results: Dict[str, List[BacktestResult]]) -> Dict[str, Any]:
        """Generate summary statistics across all results"""
        
        all_results = [result for symbol_results in results.values() for result in symbol_results]
        
        if not all_results:
            return {}
            
        summary = {
            'total_backtests': len(all_results),
            'symbols_tested': len(results),
            'avg_sharpe_ratio': np.mean([r.overall_metrics.get('sharpe_ratio', 0) for r in all_results]),
            'avg_total_return': np.mean([r.overall_metrics.get('total_return', 0) for r in all_results]),
            'avg_max_drawdown': np.mean([r.overall_metrics.get('max_drawdown', 0) for r in all_results]),
            'best_performing_symbol': max(results.keys(), key=lambda s: np.mean([r.overall_metrics.get('sharpe_ratio', 0) for r in results[s]])),
        }
        
        return summary
        
    def _format_detailed_results(self, results: Dict[str, List[BacktestResult]]) -> Dict[str, Any]:
        """Format detailed results for reporting"""
        
        formatted = {}
        
        for symbol, symbol_results in results.items():
            formatted[symbol] = []
            
            for result in symbol_results:
                formatted[symbol].append({
                    'backtest_type': result.backtest_type.value,
                    'timeframe': result.timeframe,
                    'metrics': result.overall_metrics,
                    'statistics': result.statistics,
                    'validation_scores': result.validation_scores,
                    'total_trades': len(result.trades)
                })
                
        return formatted
        
    def _analyze_validation_results(self, results: Dict[str, List[BacktestResult]]) -> Dict[str, Any]:
        """Analyze validation results for robustness"""
        
        validation_analysis = {
            'walk_forward_consistency': [],
            'out_of_sample_performance': [],
            'cross_validation_stability': []
        }
        
        for symbol, symbol_results in results.items():
            for result in symbol_results:
                if result.backtest_type == BacktestType.WALK_FORWARD:
                    consistency = result.validation_scores.get('consistency_score', 0)
                    validation_analysis['walk_forward_consistency'].append(consistency)
                elif result.backtest_type == BacktestType.OUT_OF_SAMPLE:
                    performance = result.overall_metrics.get('sharpe_ratio', 0)
                    validation_analysis['out_of_sample_performance'].append(performance)
                elif result.backtest_type == BacktestType.CROSS_VALIDATION:
                    stability = result.validation_scores.get('cv_stability', 0)
                    validation_analysis['cross_validation_stability'].append(stability)
                    
        return validation_analysis
        
    def _generate_recommendations(self, results: Dict[str, List[BacktestResult]]) -> List[str]:
        """Generate recommendations based on backtest results"""
        
        recommendations = []
        
        # Analyze overall performance
        all_sharpe_ratios = [r.overall_metrics.get('sharpe_ratio', 0) for symbol_results in results.values() for r in symbol_results]
        avg_sharpe = np.mean(all_sharpe_ratios) if all_sharpe_ratios else 0
        
        if avg_sharpe > 1.5:
            recommendations.append("Strategy shows strong risk-adjusted returns across multiple tests")
        elif avg_sharpe > 1.0:
            recommendations.append("Strategy shows good risk-adjusted returns but may need optimization")
        else:
            recommendations.append("Strategy needs significant improvement in risk-adjusted returns")
            
        # Analyze consistency
        sharpe_std = np.std(all_sharpe_ratios) if all_sharpe_ratios else 0
        if sharpe_std < 0.5:
            recommendations.append("Strategy shows good consistency across different market conditions")
        else:
            recommendations.append("Strategy shows high variability - consider parameter stabilization")
            
        return recommendations

# Demo function
async def demo_extensive_backtesting():
    """Demonstrate extensive backtesting capabilities"""
    
    print("🔄 SICAR Extensive Backtesting Engine - Phase 7-8 Demo")
    print("=" * 60)
    
    # Initialize backtester
    backtester = ExtensiveBacktester()
    
    # Define test strategy (simple moving average crossover)
    async def simple_ma_strategy(data, params):
        """Simple moving average crossover strategy"""
        return await backtester._run_strategy(simple_ma_strategy, data, params, "TEST", "1h")
    
    # Test symbols
    test_symbols = ["BTCUSDT", "ETHUSDT"]
    
    print(f"📊 Running extensive backtesting for {len(test_symbols)} symbols")
    print(f"📅 Period: 2020-2025")
    print(f"🔬 Methods: Walk-Forward, Out-of-Sample, Cross-Validation")
    print()
    
    # Run extensive backtesting
    results = await backtester.run_extensive_backtest(
        strategy_func=simple_ma_strategy,
        symbols=test_symbols,
        start_date="2020-01-01",
        end_date="2025-01-01",
        timeframes=["1h"],
        backtest_types=[BacktestType.WALK_FORWARD, BacktestType.OUT_OF_SAMPLE],
        strategy_params={'short_ma': 20, 'long_ma': 50}
    )
    
    print("📈 Backtesting Results Summary:")
    print("-" * 40)
    
    for symbol, symbol_results in results.items():
        print(f"Symbol: {symbol}")
        
        for result in symbol_results:
            print(f"  Method: {result.backtest_type.value}")
            print(f"    📊 Total Trades: {len(result.trades)}")
            print(f"    📈 Total Return: {result.overall_metrics.get('total_return', 0):.2%}")
            print(f"    📊 Sharpe Ratio: {result.overall_metrics.get('sharpe_ratio', 0):.3f}")
            print(f"    📉 Max Drawdown: {result.overall_metrics.get('max_drawdown', 0):.2%}")
            print(f"    🎯 Win Rate: {result.overall_metrics.get('win_rate', 0):.2%}")
            
            if result.validation_scores:
                print(f"    ✅ Consistency: {result.validation_scores.get('consistency_score', 0):.3f}")
                print(f"    🔒 Stability: {result.validation_scores.get('stability_score', 0):.3f}")
            print()
            
    # Generate comprehensive report
    report_path = "results/backtesting/extensive_backtest_report.json"
    backtester.generate_backtest_report(results, report_path)
    
    print(f"📁 Comprehensive report saved to: {report_path}")
    print("✅ Extensive backtesting demonstration completed!")
    
    return backtester, results

if __name__ == "__main__":
    asyncio.run(demo_extensive_backtesting())