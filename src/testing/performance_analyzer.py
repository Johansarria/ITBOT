"""
SICAR Performance Analysis and Reporting System - Phase 7-8
Comprehensive analysis of backtesting results with advanced metrics and visualizations
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import sqlite3
import json
import logging
from pathlib import Path
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.linear_model import LinearRegression
import empyrical as emp
import quantstats as qs
import pyfolio as pf
from statsmodels.tsa.stattools import adfuller
from statsmodels.stats.diagnostic import acorr_ljungbox
import yfinance as yf
warnings.filterwarnings('ignore')

class AnalysisType(Enum):
    RETURNS = "returns"
    RISK = "risk"
    DRAWDOWN = "drawdown"
    CORRELATION = "correlation"
    ATTRIBUTION = "attribution"
    REGIME = "regime"
    FACTOR = "factor"

class ReportFormat(Enum):
    HTML = "html"
    PDF = "pdf"
    EXCEL = "excel"
    JSON = "json"

class BenchmarkType(Enum):
    SPY = "SPY"
    QQQ = "QQQ"
    VTI = "VTI"
    CUSTOM = "custom"

@dataclass
class PerformanceMetrics:
    # Return metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    downside_deviation: float = 0.0
    
    # Trade metrics
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    avg_trade_duration: float = 0.0
    
    # Advanced metrics
    information_ratio: float = 0.0
    treynor_ratio: float = 0.0
    jensen_alpha: float = 0.0
    beta: float = 0.0
    tracking_error: float = 0.0

@dataclass
class DrawdownAnalysis:
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    avg_drawdown: float = 0.0
    avg_drawdown_duration: int = 0
    recovery_factor: float = 0.0
    drawdown_periods: List[Dict[str, Any]] = field(default_factory=list)
    underwater_curve: pd.Series = field(default_factory=pd.Series)

@dataclass
class RiskAnalysis:
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    cvar_99: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    tail_ratio: float = 0.0
    common_sense_ratio: float = 0.0

@dataclass
class PerformanceReport:
    strategy_name: str
    symbol: str
    period: Tuple[datetime, datetime]
    metrics: PerformanceMetrics
    drawdown_analysis: DrawdownAnalysis
    risk_analysis: RiskAnalysis
    benchmark_comparison: Dict[str, Any] = field(default_factory=dict)
    factor_analysis: Dict[str, Any] = field(default_factory=dict)
    regime_analysis: Dict[str, Any] = field(default_factory=dict)
    attribution_analysis: Dict[str, Any] = field(default_factory=dict)

class PerformanceAnalyzer:
    """
    Comprehensive performance analysis and reporting system
    Provides detailed analysis of backtesting results with advanced metrics
    """
    
    def __init__(self, results_dir: str = "results/performance"):
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logging()
        
        # Style configuration for plots
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Benchmark data cache
        self.benchmark_cache = {}
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for performance analysis"""
        logger = logging.getLogger("PerformanceAnalyzer")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler(self.results_dir / "performance_analysis.log")
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    async def analyze_strategy_performance(
        self,
        returns: pd.Series,
        trades: List[Dict[str, Any]],
        strategy_name: str,
        symbol: str,
        benchmark: str = "SPY",
        risk_free_rate: float = 0.02
    ) -> PerformanceReport:
        """
        Comprehensive performance analysis of strategy
        """
        
        self.logger.info(f"Starting performance analysis for {strategy_name} on {symbol}")
        
        start_time = time.time()
        
        # Ensure returns is properly indexed
        if not isinstance(returns.index, pd.DatetimeIndex):
            returns.index = pd.to_datetime(returns.index)
            
        # Calculate basic metrics
        metrics = await self._calculate_performance_metrics(
            returns, trades, risk_free_rate
        )
        
        # Drawdown analysis
        drawdown_analysis = await self._analyze_drawdowns(returns)
        
        # Risk analysis
        risk_analysis = await self._analyze_risk_metrics(returns)
        
        # Benchmark comparison
        benchmark_comparison = await self._benchmark_comparison(
            returns, benchmark, risk_free_rate
        )
        
        # Factor analysis
        factor_analysis = await self._factor_analysis(returns, benchmark)
        
        # Regime analysis
        regime_analysis = await self._regime_analysis(returns)
        
        # Attribution analysis
        attribution_analysis = await self._attribution_analysis(returns, trades)
        
        # Create performance report
        report = PerformanceReport(
            strategy_name=strategy_name,
            symbol=symbol,
            period=(returns.index[0], returns.index[-1]),
            metrics=metrics,
            drawdown_analysis=drawdown_analysis,
            risk_analysis=risk_analysis,
            benchmark_comparison=benchmark_comparison,
            factor_analysis=factor_analysis,
            regime_analysis=regime_analysis,
            attribution_analysis=attribution_analysis
        )
        
        analysis_time = time.time() - start_time
        self.logger.info(f"Performance analysis completed in {analysis_time:.2f} seconds")
        
        return report
        
    async def _calculate_performance_metrics(
        self,
        returns: pd.Series,
        trades: List[Dict[str, Any]],
        risk_free_rate: float
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        if len(returns) == 0:
            return PerformanceMetrics()
            
        # Basic return metrics
        total_return = emp.cum_returns_final(returns)
        annualized_return = emp.annual_return(returns)
        volatility = emp.annual_volatility(returns)
        
        # Risk-adjusted metrics
        sharpe_ratio = emp.sharpe_ratio(returns, risk_free=risk_free_rate)
        sortino_ratio = emp.sortino_ratio(returns, required_return=risk_free_rate)
        calmar_ratio = emp.calmar_ratio(returns)
        
        # Risk metrics
        max_drawdown = emp.max_drawdown(returns)
        downside_deviation = emp.downside_risk(returns)
        
        # VaR and CVaR
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean()
        
        # Trade-based metrics
        if trades:
            trade_returns = [trade.get('pnl_pct', 0) for trade in trades]
            win_rate = len([r for r in trade_returns if r > 0]) / len(trade_returns)
            
            gross_profit = sum(r for r in trade_returns if r > 0)
            gross_loss = abs(sum(r for r in trade_returns if r < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
            
            expectancy = np.mean(trade_returns)
            
            durations = [trade.get('duration', 0) for trade in trades if 'duration' in trade]
            avg_trade_duration = np.mean(durations) if durations else 0
        else:
            win_rate = 0
            profit_factor = 0
            expectancy = 0
            avg_trade_duration = 0
            
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            cvar_95=cvar_95,
            downside_deviation=downside_deviation,
            total_trades=len(trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            avg_trade_duration=avg_trade_duration
        )
        
    async def _analyze_drawdowns(self, returns: pd.Series) -> DrawdownAnalysis:
        """Analyze drawdown characteristics"""
        
        if len(returns) == 0:
            return DrawdownAnalysis()
            
        # Calculate cumulative returns and running maximum
        cumulative_returns = emp.cum_returns(returns, starting_value=1)
        running_max = cumulative_returns.expanding().max()
        
        # Calculate drawdown
        drawdown = (cumulative_returns - running_max) / running_max
        
        # Find drawdown periods
        drawdown_periods = []
        in_drawdown = False
        start_date = None
        peak_value = 0
        trough_value = 0
        
        for date, dd in drawdown.items():
            if dd < 0 and not in_drawdown:
                # Start of drawdown
                in_drawdown = True
                start_date = date
                peak_value = running_max[date]
                trough_value = cumulative_returns[date]
                
            elif dd < 0 and in_drawdown:
                # Continue drawdown
                trough_value = min(trough_value, cumulative_returns[date])
                
            elif dd == 0 and in_drawdown:
                # End of drawdown
                in_drawdown = False
                duration = (date - start_date).days
                magnitude = (trough_value - peak_value) / peak_value
                
                drawdown_periods.append({
                    'start': start_date,
                    'end': date,
                    'duration': duration,
                    'magnitude': magnitude,
                    'peak_value': peak_value,
                    'trough_value': trough_value
                })
                
        # Calculate statistics
        max_drawdown = abs(drawdown.min())
        max_drawdown_duration = 0
        avg_drawdown = 0
        avg_drawdown_duration = 0
        
        if drawdown_periods:
            max_drawdown_duration = max(period['duration'] for period in drawdown_periods)
            avg_drawdown = np.mean([abs(period['magnitude']) for period in drawdown_periods])
            avg_drawdown_duration = np.mean([period['duration'] for period in drawdown_periods])
            
        # Recovery factor
        recovery_factor = abs(returns.sum()) / max_drawdown if max_drawdown > 0 else np.inf
        
        return DrawdownAnalysis(
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            avg_drawdown=avg_drawdown,
            avg_drawdown_duration=avg_drawdown_duration,
            recovery_factor=recovery_factor,
            drawdown_periods=drawdown_periods,
            underwater_curve=drawdown
        )
        
    async def _analyze_risk_metrics(self, returns: pd.Series) -> RiskAnalysis:
        """Analyze risk characteristics"""
        
        if len(returns) == 0:
            return RiskAnalysis()
            
        # VaR and CVaR at different confidence levels
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        cvar_95 = returns[returns <= var_95].mean()
        cvar_99 = returns[returns <= var_99].mean()
        
        # Higher moments
        skewness = stats.skew(returns)
        kurtosis = stats.kurtosis(returns)
        
        # Tail ratio
        tail_ratio = abs(np.percentile(returns, 95)) / abs(np.percentile(returns, 5))
        
        # Common sense ratio
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]
        
        if len(positive_returns) > 0 and len(negative_returns) > 0:
            common_sense_ratio = (
                len(positive_returns) * np.mean(positive_returns)
            ) / (
                len(negative_returns) * abs(np.mean(negative_returns))
            )
        else:
            common_sense_ratio = 0
            
        return RiskAnalysis(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            skewness=skewness,
            kurtosis=kurtosis,
            tail_ratio=tail_ratio,
            common_sense_ratio=common_sense_ratio
        )
        
    async def _benchmark_comparison(
        self,
        returns: pd.Series,
        benchmark: str,
        risk_free_rate: float
    ) -> Dict[str, Any]:
        """Compare strategy performance against benchmark"""
        
        try:
            # Get benchmark data
            benchmark_returns = await self._get_benchmark_returns(
                benchmark, returns.index[0], returns.index[-1]
            )
            
            if benchmark_returns is None or len(benchmark_returns) == 0:
                return {"error": f"Could not retrieve benchmark data for {benchmark}"}
                
            # Align returns
            aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
            
            if len(aligned_returns) == 0:
                return {"error": "No overlapping dates between strategy and benchmark"}
                
            # Calculate relative metrics
            excess_returns = aligned_returns - aligned_benchmark
            tracking_error = excess_returns.std() * np.sqrt(252)
            information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
            
            # Beta and alpha
            if len(aligned_returns) > 1 and aligned_benchmark.std() > 0:
                beta = np.cov(aligned_returns, aligned_benchmark)[0, 1] / np.var(aligned_benchmark)
                alpha = aligned_returns.mean() - beta * aligned_benchmark.mean()
                treynor_ratio = (aligned_returns.mean() - risk_free_rate / 252) / beta
            else:
                beta = 0
                alpha = 0
                treynor_ratio = 0
                
            # Correlation
            correlation = aligned_returns.corr(aligned_benchmark)
            
            # Performance comparison
            strategy_total_return = emp.cum_returns_final(aligned_returns)
            benchmark_total_return = emp.cum_returns_final(aligned_benchmark)
            
            strategy_sharpe = emp.sharpe_ratio(aligned_returns, risk_free=risk_free_rate)
            benchmark_sharpe = emp.sharpe_ratio(aligned_benchmark, risk_free=risk_free_rate)
            
            strategy_volatility = emp.annual_volatility(aligned_returns)
            benchmark_volatility = emp.annual_volatility(aligned_benchmark)
            
            return {
                "benchmark_symbol": benchmark,
                "correlation": correlation,
                "beta": beta,
                "alpha": alpha,
                "tracking_error": tracking_error,
                "information_ratio": information_ratio,
                "treynor_ratio": treynor_ratio,
                "strategy_total_return": strategy_total_return,
                "benchmark_total_return": benchmark_total_return,
                "outperformance": strategy_total_return - benchmark_total_return,
                "strategy_sharpe": strategy_sharpe,
                "benchmark_sharpe": benchmark_sharpe,
                "strategy_volatility": strategy_volatility,
                "benchmark_volatility": benchmark_volatility
            }
            
        except Exception as e:
            self.logger.warning(f"Error in benchmark comparison: {str(e)}")
            return {"error": str(e)}
            
    async def _get_benchmark_returns(
        self,
        benchmark: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.Series]:
        """Get benchmark returns data"""
        
        cache_key = f"{benchmark}_{start_date.date()}_{end_date.date()}"
        
        if cache_key in self.benchmark_cache:
            return self.benchmark_cache[cache_key]
            
        try:
            # Download benchmark data
            ticker = yf.Ticker(benchmark)
            data = ticker.history(start=start_date, end=end_date + timedelta(days=1))
            
            if data.empty:
                return None
                
            # Calculate returns
            returns = data['Close'].pct_change().dropna()
            returns.index = pd.to_datetime(returns.index).tz_localize(None)
            
            # Cache the data
            self.benchmark_cache[cache_key] = returns
            
            return returns
            
        except Exception as e:
            self.logger.warning(f"Error downloading benchmark {benchmark}: {str(e)}")
            return None
            
    async def _factor_analysis(
        self,
        returns: pd.Series,
        benchmark: str
    ) -> Dict[str, Any]:
        """Perform factor analysis"""
        
        try:
            # Get factor data (simplified - in practice would use proper factor models)
            factors = {}
            
            # Market factor
            market_returns = await self._get_benchmark_returns(
                benchmark, returns.index[0], returns.index[-1]
            )
            
            if market_returns is not None:
                aligned_returns, aligned_market = returns.align(market_returns, join='inner')
                
                if len(aligned_returns) > 10:
                    # Simple linear regression
                    X = aligned_market.values.reshape(-1, 1)
                    y = aligned_returns.values
                    
                    model = LinearRegression()
                    model.fit(X, y)
                    
                    factors['market_beta'] = model.coef_[0]
                    factors['alpha'] = model.intercept_
                    factors['r_squared'] = model.score(X, y)
                    
            return factors
            
        except Exception as e:
            self.logger.warning(f"Error in factor analysis: {str(e)}")
            return {}
            
    async def _regime_analysis(self, returns: pd.Series) -> Dict[str, Any]:
        """Analyze performance across different market regimes"""
        
        try:
            # Simple regime classification based on volatility
            rolling_vol = returns.rolling(window=30).std()
            vol_median = rolling_vol.median()
            
            high_vol_periods = rolling_vol > vol_median * 1.5
            low_vol_periods = rolling_vol < vol_median * 0.5
            normal_vol_periods = ~(high_vol_periods | low_vol_periods)
            
            regimes = {
                'high_volatility': {
                    'returns': returns[high_vol_periods],
                    'periods': high_vol_periods.sum()
                },
                'normal_volatility': {
                    'returns': returns[normal_vol_periods],
                    'periods': normal_vol_periods.sum()
                },
                'low_volatility': {
                    'returns': returns[low_vol_periods],
                    'periods': low_vol_periods.sum()
                }
            }
            
            # Calculate performance in each regime
            regime_analysis = {}
            
            for regime_name, regime_data in regimes.items():
                regime_returns = regime_data['returns']
                
                if len(regime_returns) > 0:
                    regime_analysis[regime_name] = {
                        'periods': regime_data['periods'],
                        'total_return': emp.cum_returns_final(regime_returns),
                        'annualized_return': emp.annual_return(regime_returns),
                        'volatility': emp.annual_volatility(regime_returns),
                        'sharpe_ratio': emp.sharpe_ratio(regime_returns),
                        'max_drawdown': emp.max_drawdown(regime_returns)
                    }
                    
            return regime_analysis
            
        except Exception as e:
            self.logger.warning(f"Error in regime analysis: {str(e)}")
            return {}
            
    async def _attribution_analysis(
        self,
        returns: pd.Series,
        trades: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze return attribution"""
        
        try:
            if not trades:
                return {}
                
            # Group trades by various attributes
            attribution = {}
            
            # By trade duration
            short_trades = [t for t in trades if t.get('duration', 0) < 24]  # < 1 day
            medium_trades = [t for t in trades if 24 <= t.get('duration', 0) < 168]  # 1-7 days
            long_trades = [t for t in trades if t.get('duration', 0) >= 168]  # > 7 days
            
            attribution['by_duration'] = {
                'short_term': {
                    'count': len(short_trades),
                    'total_pnl': sum(t.get('pnl_pct', 0) for t in short_trades),
                    'avg_pnl': np.mean([t.get('pnl_pct', 0) for t in short_trades]) if short_trades else 0
                },
                'medium_term': {
                    'count': len(medium_trades),
                    'total_pnl': sum(t.get('pnl_pct', 0) for t in medium_trades),
                    'avg_pnl': np.mean([t.get('pnl_pct', 0) for t in medium_trades]) if medium_trades else 0
                },
                'long_term': {
                    'count': len(long_trades),
                    'total_pnl': sum(t.get('pnl_pct', 0) for t in long_trades),
                    'avg_pnl': np.mean([t.get('pnl_pct', 0) for t in long_trades]) if long_trades else 0
                }
            }
            
            # By trade outcome
            winning_trades = [t for t in trades if t.get('pnl_pct', 0) > 0]
            losing_trades = [t for t in trades if t.get('pnl_pct', 0) < 0]
            
            attribution['by_outcome'] = {
                'winning_trades': {
                    'count': len(winning_trades),
                    'total_pnl': sum(t.get('pnl_pct', 0) for t in winning_trades),
                    'avg_pnl': np.mean([t.get('pnl_pct', 0) for t in winning_trades]) if winning_trades else 0
                },
                'losing_trades': {
                    'count': len(losing_trades),
                    'total_pnl': sum(t.get('pnl_pct', 0) for t in losing_trades),
                    'avg_pnl': np.mean([t.get('pnl_pct', 0) for t in losing_trades]) if losing_trades else 0
                }
            }
            
            return attribution
            
        except Exception as e:
            self.logger.warning(f"Error in attribution analysis: {str(e)}")
            return {}
            
    async def generate_performance_visualizations(
        self,
        report: PerformanceReport,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict[str, str]:
        """Generate comprehensive performance visualizations"""
        
        self.logger.info("Generating performance visualizations")
        
        visualization_paths = {}
        
        # 1. Cumulative returns chart
        fig_cumulative = await self._create_cumulative_returns_chart(
            returns, benchmark_returns, report.strategy_name
        )
        cumulative_path = self.results_dir / f"{report.strategy_name}_cumulative_returns.html"
        fig_cumulative.write_html(str(cumulative_path))
        visualization_paths['cumulative_returns'] = str(cumulative_path)
        
        # 2. Drawdown chart
        fig_drawdown = await self._create_drawdown_chart(
            report.drawdown_analysis.underwater_curve, report.strategy_name
        )
        drawdown_path = self.results_dir / f"{report.strategy_name}_drawdown.html"
        fig_drawdown.write_html(str(drawdown_path))
        visualization_paths['drawdown'] = str(drawdown_path)
        
        # 3. Returns distribution
        fig_distribution = await self._create_returns_distribution(
            returns, report.strategy_name
        )
        distribution_path = self.results_dir / f"{report.strategy_name}_returns_distribution.html"
        fig_distribution.write_html(str(distribution_path))
        visualization_paths['returns_distribution'] = str(distribution_path)
        
        # 4. Rolling metrics
        fig_rolling = await self._create_rolling_metrics_chart(
            returns, report.strategy_name
        )
        rolling_path = self.results_dir / f"{report.strategy_name}_rolling_metrics.html"
        fig_rolling.write_html(str(rolling_path))
        visualization_paths['rolling_metrics'] = str(rolling_path)
        
        # 5. Risk-return scatter
        if benchmark_returns is not None:
            fig_risk_return = await self._create_risk_return_scatter(
                returns, benchmark_returns, report.strategy_name
            )
            risk_return_path = self.results_dir / f"{report.strategy_name}_risk_return.html"
            fig_risk_return.write_html(str(risk_return_path))
            visualization_paths['risk_return'] = str(risk_return_path)
            
        return visualization_paths
        
    async def _create_cumulative_returns_chart(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series],
        strategy_name: str
    ) -> go.Figure:
        """Create cumulative returns chart"""
        
        fig = go.Figure()
        
        # Strategy cumulative returns
        cumulative_returns = emp.cum_returns(returns, starting_value=1)
        fig.add_trace(go.Scatter(
            x=cumulative_returns.index,
            y=cumulative_returns.values,
            mode='lines',
            name=strategy_name,
            line=dict(color='blue', width=2)
        ))
        
        # Benchmark cumulative returns
        if benchmark_returns is not None:
            aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
            benchmark_cumulative = emp.cum_returns(aligned_benchmark, starting_value=1)
            
            fig.add_trace(go.Scatter(
                x=benchmark_cumulative.index,
                y=benchmark_cumulative.values,
                mode='lines',
                name='Benchmark',
                line=dict(color='red', width=2, dash='dash')
            ))
            
        fig.update_layout(
            title=f'Cumulative Returns - {strategy_name}',
            xaxis_title='Date',
            yaxis_title='Cumulative Return',
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
        
    async def _create_drawdown_chart(
        self,
        underwater_curve: pd.Series,
        strategy_name: str
    ) -> go.Figure:
        """Create drawdown chart"""
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=underwater_curve.index,
            y=underwater_curve.values * 100,
            mode='lines',
            name='Drawdown',
            fill='tonexty',
            fillcolor='rgba(255, 0, 0, 0.3)',
            line=dict(color='red', width=1)
        ))
        
        fig.update_layout(
            title=f'Underwater Curve - {strategy_name}',
            xaxis_title='Date',
            yaxis_title='Drawdown (%)',
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
        
    async def _create_returns_distribution(
        self,
        returns: pd.Series,
        strategy_name: str
    ) -> go.Figure:
        """Create returns distribution chart"""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['Histogram', 'Q-Q Plot', 'Box Plot', 'Time Series'],
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Histogram
        fig.add_trace(
            go.Histogram(x=returns.values, nbinsx=50, name='Returns'),
            row=1, col=1
        )
        
        # Q-Q plot
        qq_data = stats.probplot(returns.values, dist="norm")
        fig.add_trace(
            go.Scatter(x=qq_data[0][0], y=qq_data[0][1], mode='markers', name='Q-Q'),
            row=1, col=2
        )
        
        # Box plot
        fig.add_trace(
            go.Box(y=returns.values, name='Returns'),
            row=2, col=1
        )
        
        # Time series
        fig.add_trace(
            go.Scatter(x=returns.index, y=returns.values, mode='lines', name='Returns'),
            row=2, col=2
        )
        
        fig.update_layout(
            title=f'Returns Distribution Analysis - {strategy_name}',
            template='plotly_white'
        )
        
        return fig
        
    async def _create_rolling_metrics_chart(
        self,
        returns: pd.Series,
        strategy_name: str
    ) -> go.Figure:
        """Create rolling metrics chart"""
        
        # Calculate rolling metrics
        window = min(252, len(returns) // 4)  # 1 year or quarter of data
        
        rolling_sharpe = returns.rolling(window).apply(
            lambda x: emp.sharpe_ratio(x) if len(x) == window else np.nan
        )
        rolling_vol = returns.rolling(window).std() * np.sqrt(252)
        rolling_return = returns.rolling(window).mean() * 252
        
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=['Rolling Sharpe Ratio', 'Rolling Volatility', 'Rolling Return'],
            shared_xaxes=True
        )
        
        # Rolling Sharpe
        fig.add_trace(
            go.Scatter(x=rolling_sharpe.index, y=rolling_sharpe.values, 
                      mode='lines', name='Sharpe Ratio'),
            row=1, col=1
        )
        
        # Rolling Volatility
        fig.add_trace(
            go.Scatter(x=rolling_vol.index, y=rolling_vol.values,
                      mode='lines', name='Volatility'),
            row=2, col=1
        )
        
        # Rolling Return
        fig.add_trace(
            go.Scatter(x=rolling_return.index, y=rolling_return.values,
                      mode='lines', name='Return'),
            row=3, col=1
        )
        
        fig.update_layout(
            title=f'Rolling Performance Metrics - {strategy_name}',
            template='plotly_white'
        )
        
        return fig
        
    async def _create_risk_return_scatter(
        self,
        returns: pd.Series,
        benchmark_returns: pd.Series,
        strategy_name: str
    ) -> go.Figure:
        """Create risk-return scatter plot"""
        
        # Calculate rolling risk-return metrics
        window = 252  # 1 year
        
        strategy_rolling_return = returns.rolling(window).mean() * 252
        strategy_rolling_vol = returns.rolling(window).std() * np.sqrt(252)
        
        benchmark_rolling_return = benchmark_returns.rolling(window).mean() * 252
        benchmark_rolling_vol = benchmark_returns.rolling(window).std() * np.sqrt(252)
        
        fig = go.Figure()
        
        # Strategy points
        fig.add_trace(go.Scatter(
            x=strategy_rolling_vol,
            y=strategy_rolling_return,
            mode='markers',
            name=strategy_name,
            marker=dict(color='blue', size=8)
        ))
        
        # Benchmark points
        fig.add_trace(go.Scatter(
            x=benchmark_rolling_vol,
            y=benchmark_rolling_return,
            mode='markers',
            name='Benchmark',
            marker=dict(color='red', size=8)
        ))
        
        fig.update_layout(
            title=f'Risk-Return Analysis - {strategy_name}',
            xaxis_title='Volatility (Annualized)',
            yaxis_title='Return (Annualized)',
            template='plotly_white'
        )
        
        return fig
        
    async def generate_html_report(
        self,
        report: PerformanceReport,
        visualization_paths: Dict[str, str]
    ) -> str:
        """Generate comprehensive HTML report"""
        
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Performance Report - {report.strategy_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
        .metric-value {{ font-size: 18px; font-weight: bold; color: #333; }}
        .metric-label {{ font-size: 12px; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .positive {{ color: green; }}
        .negative {{ color: red; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Performance Analysis Report</h1>
        <h2>{report.strategy_name} - {report.symbol}</h2>
        <p>Period: {report.period[0].strftime('%Y-%m-%d')} to {report.period[1].strftime('%Y-%m-%d')}</p>
    </div>
    
    <div class="section">
        <h3>Key Performance Metrics</h3>
        <div class="metric">
            <div class="metric-value {'positive' if report.metrics.total_return > 0 else 'negative'}">{report.metrics.total_return:.2%}</div>
            <div class="metric-label">Total Return</div>
        </div>
        <div class="metric">
            <div class="metric-value {'positive' if report.metrics.annualized_return > 0 else 'negative'}">{report.metrics.annualized_return:.2%}</div>
            <div class="metric-label">Annualized Return</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.metrics.volatility:.2%}</div>
            <div class="metric-label">Volatility</div>
        </div>
        <div class="metric">
            <div class="metric-value {'positive' if report.metrics.sharpe_ratio > 0 else 'negative'}">{report.metrics.sharpe_ratio:.2f}</div>
            <div class="metric-label">Sharpe Ratio</div>
        </div>
        <div class="metric">
            <div class="metric-value negative">{report.metrics.max_drawdown:.2%}</div>
            <div class="metric-label">Max Drawdown</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report.metrics.win_rate:.2%}</div>
            <div class="metric-label">Win Rate</div>
        </div>
    </div>
    
    <div class="section">
        <h3>Risk Metrics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Value at Risk (95%)</td><td class="negative">{report.risk_analysis.var_95:.2%}</td></tr>
            <tr><td>Conditional VaR (95%)</td><td class="negative">{report.risk_analysis.cvar_95:.2%}</td></tr>
            <tr><td>Skewness</td><td>{report.risk_analysis.skewness:.3f}</td></tr>
            <tr><td>Kurtosis</td><td>{report.risk_analysis.kurtosis:.3f}</td></tr>
            <tr><td>Downside Deviation</td><td>{report.metrics.downside_deviation:.2%}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h3>Trade Statistics</h3>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Trades</td><td>{report.metrics.total_trades}</td></tr>
            <tr><td>Win Rate</td><td>{report.metrics.win_rate:.2%}</td></tr>
            <tr><td>Profit Factor</td><td>{report.metrics.profit_factor:.2f}</td></tr>
            <tr><td>Expectancy</td><td class="{'positive' if report.metrics.expectancy > 0 else 'negative'}">{report.metrics.expectancy:.2%}</td></tr>
            <tr><td>Avg Trade Duration</td><td>{report.metrics.avg_trade_duration:.1f} hours</td></tr>
        </table>
    </div>
"""
        
        # Add benchmark comparison if available
        if report.benchmark_comparison and 'error' not in report.benchmark_comparison:
            html_template += f"""
    <div class="section">
        <h3>Benchmark Comparison</h3>
        <table>
            <tr><th>Metric</th><th>Strategy</th><th>Benchmark</th><th>Difference</th></tr>
            <tr>
                <td>Total Return</td>
                <td class="{'positive' if report.benchmark_comparison['strategy_total_return'] > 0 else 'negative'}">{report.benchmark_comparison['strategy_total_return']:.2%}</td>
                <td class="{'positive' if report.benchmark_comparison['benchmark_total_return'] > 0 else 'negative'}">{report.benchmark_comparison['benchmark_total_return']:.2%}</td>
                <td class="{'positive' if report.benchmark_comparison['outperformance'] > 0 else 'negative'}">{report.benchmark_comparison['outperformance']:.2%}</td>
            </tr>
            <tr>
                <td>Sharpe Ratio</td>
                <td>{report.benchmark_comparison['strategy_sharpe']:.2f}</td>
                <td>{report.benchmark_comparison['benchmark_sharpe']:.2f}</td>
                <td class="{'positive' if report.benchmark_comparison['strategy_sharpe'] > report.benchmark_comparison['benchmark_sharpe'] else 'negative'}">{report.benchmark_comparison['strategy_sharpe'] - report.benchmark_comparison['benchmark_sharpe']:.2f}</td>
            </tr>
            <tr>
                <td>Volatility</td>
                <td>{report.benchmark_comparison['strategy_volatility']:.2%}</td>
                <td>{report.benchmark_comparison['benchmark_volatility']:.2%}</td>
                <td>{report.benchmark_comparison['strategy_volatility'] - report.benchmark_comparison['benchmark_volatility']:.2%}</td>
            </tr>
            <tr>
                <td>Beta</td>
                <td colspan="2">{report.benchmark_comparison['beta']:.3f}</td>
                <td>-</td>
            </tr>
            <tr>
                <td>Alpha</td>
                <td colspan="2" class="{'positive' if report.benchmark_comparison['alpha'] > 0 else 'negative'}">{report.benchmark_comparison['alpha']:.2%}</td>
                <td>-</td>
            </tr>
        </table>
    </div>
"""
        
        html_template += """
    <div class="section">
        <h3>Performance Charts</h3>
        <p>Interactive charts have been generated and saved separately:</p>
        <ul>
"""
        
        for chart_name, path in visualization_paths.items():
            html_template += f'<li><a href="{Path(path).name}">{chart_name.replace("_", " ").title()}</a></li>'
            
        html_template += """
        </ul>
    </div>
    
    <div class="section">
        <h3>Report Generated</h3>
        <p>Generated on: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
    </div>
    
</body>
</html>
"""
        
        # Save HTML report
        report_path = self.results_dir / f"{report.strategy_name}_performance_report.html"
        with open(report_path, 'w') as f:
            f.write(html_template)
            
        self.logger.info(f"HTML report saved to {report_path}")
        return str(report_path)

# Demo function
async def demo_performance_analysis():
    """Demonstrate performance analysis capabilities"""
    
    print("📊 SICAR Performance Analysis System - Phase 7-8 Demo")
    print("=" * 60)
    
    # Initialize analyzer
    analyzer = PerformanceAnalyzer()
    
    # Create sample returns data
    dates = pd.date_range(start="2020-01-01", end="2023-01-01", freq="D")
    np.random.seed(42)
    
    # Simulate strategy returns with some realistic characteristics
    daily_returns = np.random.normal(0.0005, 0.015, len(dates))  # Slight positive bias
    daily_returns[::50] *= 3  # Add some outliers
    returns = pd.Series(daily_returns, index=dates)
    
    # Create sample trades
    trades = []
    for i in range(100):
        entry_date = dates[np.random.randint(0, len(dates)-10)]
        duration = np.random.randint(1, 168)  # 1 hour to 1 week
        pnl_pct = np.random.normal(0.002, 0.02)  # Random P&L
        
        trades.append({
            'entry_time': entry_date,
            'exit_time': entry_date + timedelta(hours=duration),
            'duration': duration,
            'pnl_pct': pnl_pct,
            'entry_price': 100 + np.random.normal(0, 5),
            'exit_price': 100 + np.random.normal(0, 5)
        })
    
    print(f"📈 Sample data created:")
    print(f"  Returns: {len(returns)} daily observations")
    print(f"  Trades: {len(trades)} trades")
    print(f"  Period: {returns.index[0].date()} to {returns.index[-1].date()}")
    print()
    
    # Run performance analysis
    print("🔍 Running comprehensive performance analysis...")
    report = await analyzer.analyze_strategy_performance(
        returns=returns,
        trades=trades,
        strategy_name="DemoStrategy",
        symbol="DEMO",
        benchmark="SPY"
    )
    
    print("📊 Performance Analysis Results:")
    print("-" * 40)
    print(f"Total Return: {report.metrics.total_return:.2%}")
    print(f"Annualized Return: {report.metrics.annualized_return:.2%}")
    print(f"Volatility: {report.metrics.volatility:.2%}")
    print(f"Sharpe Ratio: {report.metrics.sharpe_ratio:.2f}")
    print(f"Sortino Ratio: {report.metrics.sortino_ratio:.2f}")
    print(f"Max Drawdown: {report.metrics.max_drawdown:.2%}")
    print(f"Win Rate: {report.metrics.win_rate:.2%}")
    print(f"Profit Factor: {report.metrics.profit_factor:.2f}")
    print()
    
    print("🎯 Risk Analysis:")
    print(f"  VaR (95%): {report.risk_analysis.var_95:.2%}")
    print(f"  CVaR (95%): {report.risk_analysis.cvar_95:.2%}")
    print(f"  Skewness: {report.risk_analysis.skewness:.3f}")
    print(f"  Kurtosis: {report.risk_analysis.kurtosis:.3f}")
    print()
    
    print("📉 Drawdown Analysis:")
    print(f"  Max Drawdown: {report.drawdown_analysis.max_drawdown:.2%}")
    print(f"  Max DD Duration: {report.drawdown_analysis.max_drawdown_duration} days")
    print(f"  Recovery Factor: {report.drawdown_analysis.recovery_factor:.2f}")
    print(f"  Drawdown Periods: {len(report.drawdown_analysis.drawdown_periods)}")
    print()
    
    if report.benchmark_comparison and 'error' not in report.benchmark_comparison:
        print("📈 Benchmark Comparison:")
        print(f"  Outperformance: {report.benchmark_comparison['outperformance']:.2%}")
        print(f"  Beta: {report.benchmark_comparison['beta']:.3f}")
        print(f"  Alpha: {report.benchmark_comparison['alpha']:.2%}")
        print(f"  Information Ratio: {report.benchmark_comparison['information_ratio']:.2f}")
        print()
    
    # Generate visualizations
    print("📊 Generating performance visualizations...")
    visualization_paths = await analyzer.generate_performance_visualizations(
        report, returns
    )
    
    print("📈 Visualizations created:")
    for chart_name, path in visualization_paths.items():
        print(f"  {chart_name}: {path}")
    print()
    
    # Generate HTML report
    print("📄 Generating comprehensive HTML report...")
    html_report_path = await analyzer.generate_html_report(report, visualization_paths)
    
    print(f"📁 Reports generated:")
    print(f"  HTML Report: {html_report_path}")
    print(f"  Visualizations: {len(visualization_paths)} charts")
    print()
    
    print("✅ Performance analysis demonstration completed!")
    print(f"📂 All files saved to: {analyzer.results_dir}")
    
    return analyzer, report

if __name__ == "__main__":
    asyncio.run(demo_performance_analysis())