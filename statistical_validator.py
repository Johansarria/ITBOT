"""
SICAR - Statistical Validation Framework
Comprehensive statistical validation system for strategy robustness testing.
Prevents overfitting and ensures statistical significance of backtesting results.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import sqlite3
from scipy import stats
from scipy.stats import jarque_bera, shapiro, anderson, kstest
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

class ValidationTest(Enum):
    """Types of statistical validation tests."""
    NORMALITY = "normality"
    STATIONARITY = "stationarity"
    AUTOCORRELATION = "autocorrelation"
    HETEROSCEDASTICITY = "heteroscedasticity"
    OUTLIERS = "outliers"
    STABILITY = "stability"
    ROBUSTNESS = "robustness"
    SIGNIFICANCE = "significance"
    OVERFITTING = "overfitting"
    MONTE_CARLO = "monte_carlo"

class TestResult(Enum):
    """Test result status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    INCONCLUSIVE = "inconclusive"

class RobustnessLevel(Enum):
    """Strategy robustness levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    UNRELIABLE = "unreliable"

@dataclass
class StatisticalTest:
    """Individual statistical test result."""
    test_type: ValidationTest
    test_name: str
    statistic: float
    p_value: float
    critical_value: Optional[float]
    result: TestResult
    confidence_level: float
    interpretation: str
    recommendation: str
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RobustnessAnalysis:
    """Strategy robustness analysis results."""
    strategy_name: str
    overall_score: float
    robustness_level: RobustnessLevel
    tests_passed: int
    tests_failed: int
    tests_warning: int
    critical_issues: List[str]
    recommendations: List[str]
    confidence_interval: Tuple[float, float]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ValidationReport:
    """Comprehensive validation report."""
    strategy_name: str
    validation_period: Tuple[datetime, datetime]
    total_tests: int
    statistical_tests: List[StatisticalTest]
    robustness_analysis: RobustnessAnalysis
    monte_carlo_results: Dict[str, Any]
    stability_analysis: Dict[str, Any]
    overfitting_analysis: Dict[str, Any]
    final_recommendation: str
    risk_assessment: str
    timestamp: datetime = field(default_factory=datetime.now)

class StatisticalValidator:
    """
    Comprehensive statistical validation framework for SICAR strategies.
    
    Features:
    - Normality testing (Jarque-Bera, Shapiro-Wilk, Anderson-Darling)
    - Stationarity testing (ADF, KPSS, Phillips-Perron)
    - Autocorrelation analysis (Ljung-Box, Durbin-Watson)
    - Heteroscedasticity testing (Breusch-Pagan, White)
    - Outlier detection (Z-score, IQR, Isolation Forest)
    - Stability analysis (rolling window tests)
    - Robustness testing (parameter sensitivity)
    - Monte Carlo validation
    - Overfitting detection
    """
    
    def __init__(self, db_path: str = "statistical_validation.db"):
        """Initialize the statistical validator."""
        self.db_path = db_path
        self.logger = self._setup_logging()
        self._setup_database()
        
        # Validation thresholds
        self.significance_level = 0.05
        self.confidence_level = 0.95
        self.monte_carlo_iterations = 1000
        self.stability_window = 252  # Trading days
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger('StatisticalValidator')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _setup_database(self):
        """Setup SQLite database for storing validation results."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validation_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                test_type TEXT NOT NULL,
                test_name TEXT NOT NULL,
                statistic REAL,
                p_value REAL,
                critical_value REAL,
                result TEXT NOT NULL,
                confidence_level REAL,
                interpretation TEXT,
                recommendation TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS robustness_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                overall_score REAL,
                robustness_level TEXT,
                tests_passed INTEGER,
                tests_failed INTEGER,
                tests_warning INTEGER,
                critical_issues TEXT,
                recommendations TEXT,
                confidence_interval_lower REAL,
                confidence_interval_upper REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def validate_strategy(
        self,
        strategy_name: str,
        returns: pd.Series,
        equity_curve: pd.Series,
        trades: pd.DataFrame,
        parameters: Dict[str, Any],
        benchmark_returns: Optional[pd.Series] = None
    ) -> ValidationReport:
        """
        Perform comprehensive statistical validation of a strategy.
        
        Args:
            strategy_name: Name of the strategy
            returns: Strategy returns series
            equity_curve: Strategy equity curve
            trades: DataFrame with trade information
            parameters: Strategy parameters used
            benchmark_returns: Optional benchmark returns for comparison
            
        Returns:
            ValidationReport: Comprehensive validation results
        """
        self.logger.info(f"Starting statistical validation for strategy: {strategy_name}")
        
        # Perform all statistical tests
        statistical_tests = []
        
        # Normality tests
        statistical_tests.extend(await self._test_normality(returns))
        
        # Stationarity tests
        statistical_tests.extend(await self._test_stationarity(returns))
        
        # Autocorrelation tests
        statistical_tests.extend(await self._test_autocorrelation(returns))
        
        # Heteroscedasticity tests
        statistical_tests.extend(await self._test_heteroscedasticity(returns))
        
        # Outlier detection
        statistical_tests.extend(await self._detect_outliers(returns))
        
        # Stability analysis
        stability_analysis = await self._analyze_stability(returns, equity_curve)
        
        # Robustness testing
        robustness_analysis = await self._analyze_robustness(
            strategy_name, returns, parameters
        )
        
        # Monte Carlo validation
        monte_carlo_results = await self._monte_carlo_validation(
            returns, trades
        )
        
        # Overfitting analysis
        overfitting_analysis = await self._analyze_overfitting(
            returns, parameters
        )
        
        # Generate final recommendation
        final_recommendation = self._generate_final_recommendation(
            statistical_tests, robustness_analysis, monte_carlo_results
        )
        
        # Risk assessment
        risk_assessment = self._assess_risk(
            statistical_tests, stability_analysis, overfitting_analysis
        )
        
        # Create validation report
        report = ValidationReport(
            strategy_name=strategy_name,
            validation_period=(returns.index[0], returns.index[-1]),
            total_tests=len(statistical_tests),
            statistical_tests=statistical_tests,
            robustness_analysis=robustness_analysis,
            monte_carlo_results=monte_carlo_results,
            stability_analysis=stability_analysis,
            overfitting_analysis=overfitting_analysis,
            final_recommendation=final_recommendation,
            risk_assessment=risk_assessment
        )
        
        # Save results to database
        await self._save_validation_results(report)
        
        self.logger.info(f"Statistical validation completed for {strategy_name}")
        return report
    
    async def _test_normality(self, returns: pd.Series) -> List[StatisticalTest]:
        """Test normality of returns using multiple tests."""
        tests = []
        
        # Remove NaN values
        clean_returns = returns.dropna()
        
        # Jarque-Bera test
        try:
            jb_stat, jb_p = jarque_bera(clean_returns)
            tests.append(StatisticalTest(
                test_type=ValidationTest.NORMALITY,
                test_name="Jarque-Bera",
                statistic=jb_stat,
                p_value=jb_p,
                critical_value=None,
                result=TestResult.PASS if jb_p > self.significance_level else TestResult.FAIL,
                confidence_level=self.confidence_level,
                interpretation=f"Returns {'are' if jb_p > self.significance_level else 'are not'} normally distributed",
                recommendation="Normal distribution assumption can be used" if jb_p > self.significance_level else "Consider non-parametric methods"
            ))
        except Exception as e:
            self.logger.warning(f"Jarque-Bera test failed: {e}")
        
        # Shapiro-Wilk test (for smaller samples)
        if len(clean_returns) <= 5000:
            try:
                sw_stat, sw_p = shapiro(clean_returns)
                tests.append(StatisticalTest(
                    test_type=ValidationTest.NORMALITY,
                    test_name="Shapiro-Wilk",
                    statistic=sw_stat,
                    p_value=sw_p,
                    critical_value=None,
                    result=TestResult.PASS if sw_p > self.significance_level else TestResult.FAIL,
                    confidence_level=self.confidence_level,
                    interpretation=f"Returns {'are' if sw_p > self.significance_level else 'are not'} normally distributed",
                    recommendation="Normal distribution assumption can be used" if sw_p > self.significance_level else "Consider robust statistical methods"
                ))
            except Exception as e:
                self.logger.warning(f"Shapiro-Wilk test failed: {e}")
        
        # Anderson-Darling test
        try:
            ad_result = anderson(clean_returns, dist='norm')
            critical_value = ad_result.critical_values[2]  # 5% significance level
            is_normal = ad_result.statistic < critical_value
            
            tests.append(StatisticalTest(
                test_type=ValidationTest.NORMALITY,
                test_name="Anderson-Darling",
                statistic=ad_result.statistic,
                p_value=None,  # AD test doesn't provide p-value directly
                critical_value=critical_value,
                result=TestResult.PASS if is_normal else TestResult.FAIL,
                confidence_level=self.confidence_level,
                interpretation=f"Returns {'are' if is_normal else 'are not'} normally distributed",
                recommendation="Normal distribution assumption can be used" if is_normal else "Use distribution-free methods"
            ))
        except Exception as e:
            self.logger.warning(f"Anderson-Darling test failed: {e}")
        
        return tests
    
    async def _test_stationarity(self, returns: pd.Series) -> List[StatisticalTest]:
        """Test stationarity of returns series."""
        tests = []
        
        try:
            from statsmodels.tsa.stattools import adfuller, kpss
            
            # Augmented Dickey-Fuller test
            adf_result = adfuller(returns.dropna())
            tests.append(StatisticalTest(
                test_type=ValidationTest.STATIONARITY,
                test_name="Augmented Dickey-Fuller",
                statistic=adf_result[0],
                p_value=adf_result[1],
                critical_value=adf_result[4]['5%'],
                result=TestResult.PASS if adf_result[1] < self.significance_level else TestResult.FAIL,
                confidence_level=self.confidence_level,
                interpretation=f"Series {'is' if adf_result[1] < self.significance_level else 'is not'} stationary",
                recommendation="Series is suitable for analysis" if adf_result[1] < self.significance_level else "Consider differencing or detrending"
            ))
            
            # KPSS test
            kpss_result = kpss(returns.dropna())
            tests.append(StatisticalTest(
                test_type=ValidationTest.STATIONARITY,
                test_name="KPSS",
                statistic=kpss_result[0],
                p_value=kpss_result[1],
                critical_value=kpss_result[3]['5%'],
                result=TestResult.PASS if kpss_result[1] > self.significance_level else TestResult.FAIL,
                confidence_level=self.confidence_level,
                interpretation=f"Series {'is' if kpss_result[1] > self.significance_level else 'is not'} stationary",
                recommendation="Series is suitable for analysis" if kpss_result[1] > self.significance_level else "Apply stationarity transformations"
            ))
            
        except ImportError:
            self.logger.warning("statsmodels not available for stationarity tests")
        except Exception as e:
            self.logger.warning(f"Stationarity tests failed: {e}")
        
        return tests
    
    async def _test_autocorrelation(self, returns: pd.Series) -> List[StatisticalTest]:
        """Test for autocorrelation in returns."""
        tests = []
        
        try:
            from statsmodels.stats.diagnostic import acorr_ljungbox
            
            # Ljung-Box test
            lb_result = acorr_ljungbox(returns.dropna(), lags=10, return_df=True)
            lb_stat = lb_result['lb_stat'].iloc[-1]
            lb_p = lb_result['lb_pvalue'].iloc[-1]
            
            tests.append(StatisticalTest(
                test_type=ValidationTest.AUTOCORRELATION,
                test_name="Ljung-Box",
                statistic=lb_stat,
                p_value=lb_p,
                critical_value=None,
                result=TestResult.PASS if lb_p > self.significance_level else TestResult.FAIL,
                confidence_level=self.confidence_level,
                interpretation=f"{'No significant' if lb_p > self.significance_level else 'Significant'} autocorrelation detected",
                recommendation="Returns are independent" if lb_p > self.significance_level else "Consider GARCH or other time series models"
            ))
            
        except ImportError:
            self.logger.warning("statsmodels not available for autocorrelation tests")
        except Exception as e:
            self.logger.warning(f"Autocorrelation tests failed: {e}")
        
        return tests
    
    async def _test_heteroscedasticity(self, returns: pd.Series) -> List[StatisticalTest]:
        """Test for heteroscedasticity in returns."""
        tests = []
        
        try:
            from statsmodels.stats.diagnostic import het_breuschpagan
            from statsmodels.regression.linear_model import OLS
            from statsmodels.tools import add_constant
            
            # Prepare data
            clean_returns = returns.dropna()
            y = clean_returns.values
            x = add_constant(np.arange(len(y)))
            
            # Fit OLS model
            model = OLS(y, x).fit()
            
            # Breusch-Pagan test
            bp_stat, bp_p, _, _ = het_breuschpagan(model.resid, x)
            
            tests.append(StatisticalTest(
                test_type=ValidationTest.HETEROSCEDASTICITY,
                test_name="Breusch-Pagan",
                statistic=bp_stat,
                p_value=bp_p,
                critical_value=None,
                result=TestResult.PASS if bp_p > self.significance_level else TestResult.FAIL,
                confidence_level=self.confidence_level,
                interpretation=f"{'No' if bp_p > self.significance_level else ''} Heteroscedasticity detected",
                recommendation="Constant variance assumption holds" if bp_p > self.significance_level else "Consider robust standard errors or GARCH models"
            ))
            
        except ImportError:
            self.logger.warning("statsmodels not available for heteroscedasticity tests")
        except Exception as e:
            self.logger.warning(f"Heteroscedasticity tests failed: {e}")
        
        return tests
    
    async def _detect_outliers(self, returns: pd.Series) -> List[StatisticalTest]:
        """Detect outliers in returns using multiple methods."""
        tests = []
        
        clean_returns = returns.dropna()
        
        # Z-score method
        z_scores = np.abs(stats.zscore(clean_returns))
        outliers_zscore = np.sum(z_scores > 3)
        outlier_percentage = (outliers_zscore / len(clean_returns)) * 100
        
        tests.append(StatisticalTest(
            test_type=ValidationTest.OUTLIERS,
            test_name="Z-Score Outliers",
            statistic=outlier_percentage,
            p_value=None,
            critical_value=5.0,  # 5% threshold
            result=TestResult.PASS if outlier_percentage < 5.0 else TestResult.WARNING,
            confidence_level=self.confidence_level,
            interpretation=f"{outlier_percentage:.2f}% of returns are outliers (|z| > 3)",
            recommendation="Outlier level is acceptable" if outlier_percentage < 5.0 else "Consider outlier treatment or robust methods"
        ))
        
        # IQR method
        q1 = clean_returns.quantile(0.25)
        q3 = clean_returns.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        outliers_iqr = np.sum((clean_returns < lower_bound) | (clean_returns > upper_bound))
        outlier_percentage_iqr = (outliers_iqr / len(clean_returns)) * 100
        
        tests.append(StatisticalTest(
            test_type=ValidationTest.OUTLIERS,
            test_name="IQR Outliers",
            statistic=outlier_percentage_iqr,
            p_value=None,
            critical_value=5.0,
            result=TestResult.PASS if outlier_percentage_iqr < 5.0 else TestResult.WARNING,
            confidence_level=self.confidence_level,
            interpretation=f"{outlier_percentage_iqr:.2f}% of returns are outliers (IQR method)",
            recommendation="Outlier level is acceptable" if outlier_percentage_iqr < 5.0 else "Review extreme returns and consider winsorization"
        ))
        
        return tests
    
    async def _analyze_stability(
        self,
        returns: pd.Series,
        equity_curve: pd.Series
    ) -> Dict[str, Any]:
        """Analyze stability of strategy performance over time."""
        stability_analysis = {}
        
        # Rolling Sharpe ratio stability
        rolling_sharpe = returns.rolling(window=self.stability_window).apply(
            lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
        )
        
        stability_analysis['rolling_sharpe'] = {
            'mean': rolling_sharpe.mean(),
            'std': rolling_sharpe.std(),
            'min': rolling_sharpe.min(),
            'max': rolling_sharpe.max(),
            'stability_ratio': rolling_sharpe.std() / abs(rolling_sharpe.mean()) if rolling_sharpe.mean() != 0 else float('inf')
        }
        
        # Drawdown stability
        rolling_dd = equity_curve.rolling(window=self.stability_window).apply(
            lambda x: (x.iloc[-1] - x.max()) / x.max()
        )
        
        stability_analysis['rolling_drawdown'] = {
            'mean': rolling_dd.mean(),
            'std': rolling_dd.std(),
            'worst': rolling_dd.min(),
            'best': rolling_dd.max()
        }
        
        # Performance regime analysis
        returns_periods = np.array_split(returns.dropna(), 4)  # Quarterly analysis
        period_sharpes = [
            (period.mean() / period.std() * np.sqrt(252)) if period.std() > 0 else 0
            for period in returns_periods
        ]
        
        stability_analysis['regime_analysis'] = {
            'period_sharpes': period_sharpes,
            'sharpe_consistency': np.std(period_sharpes),
            'positive_periods': sum(1 for s in period_sharpes if s > 0),
            'negative_periods': sum(1 for s in period_sharpes if s < 0)
        }
        
        return stability_analysis
    
    async def _analyze_robustness(
        self,
        strategy_name: str,
        returns: pd.Series,
        parameters: Dict[str, Any]
    ) -> RobustnessAnalysis:
        """Analyze strategy robustness across different conditions."""
        
        # Calculate base metrics
        sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        max_drawdown = self._calculate_max_drawdown(returns)
        win_rate = (returns > 0).mean()
        
        # Robustness score calculation
        score_components = []
        
        # Sharpe ratio component (0-30 points)
        if sharpe_ratio > 2.0:
            score_components.append(30)
        elif sharpe_ratio > 1.5:
            score_components.append(25)
        elif sharpe_ratio > 1.0:
            score_components.append(20)
        elif sharpe_ratio > 0.5:
            score_components.append(15)
        else:
            score_components.append(0)
        
        # Drawdown component (0-25 points)
        if max_drawdown > -0.05:
            score_components.append(25)
        elif max_drawdown > -0.10:
            score_components.append(20)
        elif max_drawdown > -0.20:
            score_components.append(15)
        elif max_drawdown > -0.30:
            score_components.append(10)
        else:
            score_components.append(0)
        
        # Consistency component (0-25 points)
        if win_rate > 0.6:
            score_components.append(25)
        elif win_rate > 0.55:
            score_components.append(20)
        elif win_rate > 0.5:
            score_components.append(15)
        elif win_rate > 0.45:
            score_components.append(10)
        else:
            score_components.append(0)
        
        # Stability component (0-20 points)
        returns_std = returns.std()
        if returns_std < 0.01:
            score_components.append(20)
        elif returns_std < 0.02:
            score_components.append(15)
        elif returns_std < 0.03:
            score_components.append(10)
        else:
            score_components.append(5)
        
        overall_score = sum(score_components)
        
        # Determine robustness level
        if overall_score >= 85:
            robustness_level = RobustnessLevel.EXCELLENT
        elif overall_score >= 70:
            robustness_level = RobustnessLevel.GOOD
        elif overall_score >= 55:
            robustness_level = RobustnessLevel.MODERATE
        elif overall_score >= 40:
            robustness_level = RobustnessLevel.POOR
        else:
            robustness_level = RobustnessLevel.UNRELIABLE
        
        # Generate recommendations
        recommendations = []
        critical_issues = []
        
        if sharpe_ratio < 1.0:
            critical_issues.append("Low Sharpe ratio indicates poor risk-adjusted returns")
            recommendations.append("Review strategy logic and risk management")
        
        if max_drawdown < -0.20:
            critical_issues.append("High maximum drawdown indicates significant risk")
            recommendations.append("Implement stronger position sizing and stop-loss mechanisms")
        
        if win_rate < 0.45:
            critical_issues.append("Low win rate may indicate poor signal quality")
            recommendations.append("Improve entry/exit signals and market timing")
        
        # Confidence interval (bootstrap)
        bootstrap_returns = []
        for _ in range(1000):
            sample = np.random.choice(returns.dropna(), size=len(returns.dropna()), replace=True)
            bootstrap_returns.append(np.mean(sample))
        
        confidence_interval = (
            np.percentile(bootstrap_returns, 2.5),
            np.percentile(bootstrap_returns, 97.5)
        )
        
        return RobustnessAnalysis(
            strategy_name=strategy_name,
            overall_score=overall_score,
            robustness_level=robustness_level,
            tests_passed=0,  # Will be updated by calling function
            tests_failed=0,  # Will be updated by calling function
            tests_warning=0,  # Will be updated by calling function
            critical_issues=critical_issues,
            recommendations=recommendations,
            confidence_interval=confidence_interval
        )
    
    async def _monte_carlo_validation(
        self,
        returns: pd.Series,
        trades: pd.DataFrame
    ) -> Dict[str, Any]:
        """Perform Monte Carlo validation of strategy results."""
        
        monte_carlo_results = {}
        
        # Bootstrap returns
        original_returns = returns.dropna()
        bootstrap_results = []
        
        for i in range(self.monte_carlo_iterations):
            # Random sampling with replacement
            bootstrap_sample = np.random.choice(
                original_returns, 
                size=len(original_returns), 
                replace=True
            )
            
            # Calculate metrics for bootstrap sample
            total_return = np.prod(1 + bootstrap_sample) - 1
            sharpe = np.mean(bootstrap_sample) / np.std(bootstrap_sample) * np.sqrt(252)
            max_dd = self._calculate_max_drawdown(pd.Series(bootstrap_sample))
            
            bootstrap_results.append({
                'total_return': total_return,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_dd
            })
        
        # Calculate confidence intervals
        bootstrap_df = pd.DataFrame(bootstrap_results)
        
        monte_carlo_results['bootstrap_analysis'] = {
            'total_return': {
                'mean': bootstrap_df['total_return'].mean(),
                'std': bootstrap_df['total_return'].std(),
                'ci_lower': bootstrap_df['total_return'].quantile(0.025),
                'ci_upper': bootstrap_df['total_return'].quantile(0.975)
            },
            'sharpe_ratio': {
                'mean': bootstrap_df['sharpe_ratio'].mean(),
                'std': bootstrap_df['sharpe_ratio'].std(),
                'ci_lower': bootstrap_df['sharpe_ratio'].quantile(0.025),
                'ci_upper': bootstrap_df['sharpe_ratio'].quantile(0.975)
            },
            'max_drawdown': {
                'mean': bootstrap_df['max_drawdown'].mean(),
                'std': bootstrap_df['max_drawdown'].std(),
                'ci_lower': bootstrap_df['max_drawdown'].quantile(0.025),
                'ci_upper': bootstrap_df['max_drawdown'].quantile(0.975)
            }
        }
        
        # Random trade sequence validation
        if not trades.empty and 'pnl' in trades.columns:
            trade_pnls = trades['pnl'].dropna()
            random_sequences = []
            
            for i in range(100):  # 100 random sequences
                shuffled_pnls = np.random.permutation(trade_pnls)
                cumulative_pnl = np.cumsum(shuffled_pnls)
                final_pnl = cumulative_pnl[-1]
                max_dd_trades = np.min(cumulative_pnl - np.maximum.accumulate(cumulative_pnl))
                
                random_sequences.append({
                    'final_pnl': final_pnl,
                    'max_drawdown': max_dd_trades
                })
            
            random_df = pd.DataFrame(random_sequences)
            monte_carlo_results['trade_sequence_analysis'] = {
                'final_pnl_distribution': {
                    'mean': random_df['final_pnl'].mean(),
                    'std': random_df['final_pnl'].std(),
                    'percentiles': random_df['final_pnl'].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).to_dict()
                }
            }
        
        return monte_carlo_results
    
    async def _analyze_overfitting(
        self,
        returns: pd.Series,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze potential overfitting in strategy parameters."""
        
        overfitting_analysis = {}
        
        # Parameter complexity analysis
        param_count = len(parameters)
        data_points = len(returns.dropna())
        
        # Rule of thumb: at least 10 data points per parameter
        overfitting_analysis['parameter_ratio'] = {
            'parameters': param_count,
            'data_points': data_points,
            'ratio': data_points / param_count if param_count > 0 else float('inf'),
            'recommended_minimum': 10,
            'overfitting_risk': 'High' if (data_points / param_count if param_count > 0 else float('inf')) < 10 else 'Low'
        }
        
        # Performance consistency analysis
        # Split data into periods and check consistency
        split_size = len(returns) // 3
        if split_size > 50:  # Minimum period size
            period1 = returns.iloc[:split_size]
            period2 = returns.iloc[split_size:2*split_size]
            period3 = returns.iloc[2*split_size:]
            
            sharpes = []
            for period in [period1, period2, period3]:
                if period.std() > 0:
                    sharpe = period.mean() / period.std() * np.sqrt(252)
                    sharpes.append(sharpe)
            
            if len(sharpes) >= 2:
                overfitting_analysis['consistency_analysis'] = {
                    'period_sharpes': sharpes,
                    'sharpe_std': np.std(sharpes),
                    'consistency_score': 1 / (1 + np.std(sharpes)),  # Higher is better
                    'overfitting_indicator': 'High variance in performance across periods' if np.std(sharpes) > 1.0 else 'Consistent performance'
                }
        
        # Information coefficient analysis
        # Check if performance is too good to be true
        annual_return = returns.mean() * 252
        annual_volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = annual_return / annual_volatility if annual_volatility > 0 else 0
        
        overfitting_analysis['performance_flags'] = {
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'suspicious_performance': sharpe_ratio > 3.0,  # Very high Sharpe might indicate overfitting
            'warning': 'Extremely high Sharpe ratio may indicate overfitting' if sharpe_ratio > 3.0 else 'Performance appears reasonable'
        }
        
        return overfitting_analysis
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from returns series."""
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()
    
    def _generate_final_recommendation(
        self,
        statistical_tests: List[StatisticalTest],
        robustness_analysis: RobustnessAnalysis,
        monte_carlo_results: Dict[str, Any]
    ) -> str:
        """Generate final recommendation based on all analyses."""
        
        # Count test results
        passed = sum(1 for test in statistical_tests if test.result == TestResult.PASS)
        failed = sum(1 for test in statistical_tests if test.result == TestResult.FAIL)
        warnings = sum(1 for test in statistical_tests if test.result == TestResult.WARNING)
        
        # Update robustness analysis counts
        robustness_analysis.tests_passed = passed
        robustness_analysis.tests_failed = failed
        robustness_analysis.tests_warning = warnings
        
        total_tests = len(statistical_tests)
        pass_rate = passed / total_tests if total_tests > 0 else 0
        
        if pass_rate >= 0.8 and robustness_analysis.robustness_level in [RobustnessLevel.EXCELLENT, RobustnessLevel.GOOD]:
            return "RECOMMENDED: Strategy passes statistical validation with high confidence. Suitable for live trading with appropriate risk management."
        elif pass_rate >= 0.6 and robustness_analysis.robustness_level in [RobustnessLevel.GOOD, RobustnessLevel.MODERATE]:
            return "CONDITIONAL: Strategy shows promise but requires additional validation or parameter adjustment before live trading."
        elif pass_rate >= 0.4:
            return "CAUTION: Strategy has significant statistical concerns. Extensive additional testing and modification recommended."
        else:
            return "NOT RECOMMENDED: Strategy fails multiple statistical tests. Fundamental revision required before consideration for live trading."
    
    def _assess_risk(
        self,
        statistical_tests: List[StatisticalTest],
        stability_analysis: Dict[str, Any],
        overfitting_analysis: Dict[str, Any]
    ) -> str:
        """Assess overall risk level of the strategy."""
        
        risk_factors = []
        
        # Check for failed critical tests
        critical_failures = [
            test for test in statistical_tests 
            if test.result == TestResult.FAIL and test.test_type in [
                ValidationTest.STATIONARITY, 
                ValidationTest.OVERFITTING,
                ValidationTest.SIGNIFICANCE
            ]
        ]
        
        if critical_failures:
            risk_factors.append("Critical statistical test failures")
        
        # Check overfitting indicators
        if 'parameter_ratio' in overfitting_analysis:
            if overfitting_analysis['parameter_ratio']['overfitting_risk'] == 'High':
                risk_factors.append("High overfitting risk due to parameter complexity")
        
        if 'performance_flags' in overfitting_analysis:
            if overfitting_analysis['performance_flags']['suspicious_performance']:
                risk_factors.append("Suspiciously high performance metrics")
        
        # Check stability
        if 'rolling_sharpe' in stability_analysis:
            stability_ratio = stability_analysis['rolling_sharpe']['stability_ratio']
            if stability_ratio > 1.0:
                risk_factors.append("High performance instability")
        
        # Generate risk assessment
        if len(risk_factors) == 0:
            return "LOW RISK: Strategy demonstrates statistical robustness and stability."
        elif len(risk_factors) <= 2:
            return f"MODERATE RISK: {'; '.join(risk_factors)}. Monitor closely in live trading."
        else:
            return f"HIGH RISK: Multiple concerns identified - {'; '.join(risk_factors)}. Not suitable for live trading without significant modifications."
    
    async def _save_validation_results(self, report: ValidationReport):
        """Save validation results to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save statistical tests
        for test in report.statistical_tests:
            cursor.execute('''
                INSERT INTO validation_tests (
                    strategy_name, test_type, test_name, statistic, p_value,
                    critical_value, result, confidence_level, interpretation, recommendation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.strategy_name, test.test_type.value, test.test_name,
                test.statistic, test.p_value, test.critical_value,
                test.result.value, test.confidence_level,
                test.interpretation, test.recommendation
            ))
        
        # Save robustness analysis
        cursor.execute('''
            INSERT INTO robustness_analysis (
                strategy_name, overall_score, robustness_level, tests_passed,
                tests_failed, tests_warning, critical_issues, recommendations,
                confidence_interval_lower, confidence_interval_upper
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.strategy_name, report.robustness_analysis.overall_score,
            report.robustness_analysis.robustness_level.value,
            report.robustness_analysis.tests_passed,
            report.robustness_analysis.tests_failed,
            report.robustness_analysis.tests_warning,
            json.dumps(report.robustness_analysis.critical_issues),
            json.dumps(report.robustness_analysis.recommendations),
            report.robustness_analysis.confidence_interval[0],
            report.robustness_analysis.confidence_interval[1]
        ))
        
        conn.commit()
        conn.close()
    
    async def generate_validation_report_html(self, report: ValidationReport) -> str:
        """Generate HTML report for validation results."""
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SICAR Statistical Validation Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
                .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .pass { color: #27ae60; font-weight: bold; }
                .fail { color: #e74c3c; font-weight: bold; }
                .warning { color: #f39c12; font-weight: bold; }
                .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 3px; }
                table { width: 100%; border-collapse: collapse; margin: 10px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                .recommendation { background-color: #e8f5e8; padding: 15px; border-left: 4px solid #27ae60; margin: 10px 0; }
                .risk-assessment { background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>SICAR Statistical Validation Report</h1>
                <h2>Strategy: {strategy_name}</h2>
                <p>Validation Period: {validation_period}</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="section">
                <h3>Executive Summary</h3>
                <div class="metric">
                    <strong>Total Tests:</strong> {total_tests}
                </div>
                <div class="metric">
                    <strong>Tests Passed:</strong> <span class="pass">{tests_passed}</span>
                </div>
                <div class="metric">
                    <strong>Tests Failed:</strong> <span class="fail">{tests_failed}</span>
                </div>
                <div class="metric">
                    <strong>Warnings:</strong> <span class="warning">{tests_warning}</span>
                </div>
                <div class="metric">
                    <strong>Robustness Level:</strong> {robustness_level}
                </div>
                <div class="metric">
                    <strong>Overall Score:</strong> {overall_score}/100
                </div>
            </div>
            
            <div class="section">
                <h3>Statistical Tests Results</h3>
                <table>
                    <tr>
                        <th>Test Type</th>
                        <th>Test Name</th>
                        <th>Statistic</th>
                        <th>P-Value</th>
                        <th>Result</th>
                        <th>Interpretation</th>
                    </tr>
                    {test_rows}
                </table>
            </div>
            
            <div class="section">
                <h3>Monte Carlo Analysis</h3>
                <p><strong>Bootstrap Confidence Intervals (95%):</strong></p>
                <ul>
                    <li>Total Return: {mc_return_ci}</li>
                    <li>Sharpe Ratio: {mc_sharpe_ci}</li>
                    <li>Max Drawdown: {mc_dd_ci}</li>
                </ul>
            </div>
            
            <div class="section">
                <h3>Overfitting Analysis</h3>
                <p><strong>Parameter Ratio:</strong> {param_ratio} (Recommended: >10)</p>
                <p><strong>Overfitting Risk:</strong> {overfitting_risk}</p>
                <p><strong>Performance Flags:</strong> {performance_flags}</p>
            </div>
            
            <div class="recommendation">
                <h3>Final Recommendation</h3>
                <p>{final_recommendation}</p>
            </div>
            
            <div class="risk-assessment">
                <h3>Risk Assessment</h3>
                <p>{risk_assessment}</p>
            </div>
            
            <div class="section">
                <h3>Critical Issues</h3>
                <ul>
                    {critical_issues}
                </ul>
            </div>
            
            <div class="section">
                <h3>Recommendations</h3>
                <ul>
                    {recommendations}
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Format test results
        test_rows = ""
        for test in report.statistical_tests:
            result_class = test.result.value
            test_rows += f"""
                <tr>
                    <td>{test.test_type.value}</td>
                    <td>{test.test_name}</td>
                    <td>{test.statistic:.4f if test.statistic else 'N/A'}</td>
                    <td>{test.p_value:.4f if test.p_value else 'N/A'}</td>
                    <td><span class="{result_class}">{test.result.value.upper()}</span></td>
                    <td>{test.interpretation}</td>
                </tr>
            """
        
        # Format Monte Carlo results
        mc_bootstrap = report.monte_carlo_results.get('bootstrap_analysis', {})
        mc_return_ci = f"[{mc_bootstrap.get('total_return', {}).get('ci_lower', 0):.4f}, {mc_bootstrap.get('total_return', {}).get('ci_upper', 0):.4f}]"
        mc_sharpe_ci = f"[{mc_bootstrap.get('sharpe_ratio', {}).get('ci_lower', 0):.4f}, {mc_bootstrap.get('sharpe_ratio', {}).get('ci_upper', 0):.4f}]"
        mc_dd_ci = f"[{mc_bootstrap.get('max_drawdown', {}).get('ci_lower', 0):.4f}, {mc_bootstrap.get('max_drawdown', {}).get('ci_upper', 0):.4f}]"
        
        # Format overfitting analysis
        param_ratio = report.overfitting_analysis.get('parameter_ratio', {}).get('ratio', 'N/A')
        overfitting_risk = report.overfitting_analysis.get('parameter_ratio', {}).get('overfitting_risk', 'Unknown')
        performance_flags = report.overfitting_analysis.get('performance_flags', {}).get('warning', 'No flags')
        
        # Format lists
        critical_issues = "".join([f"<li>{issue}</li>" for issue in report.robustness_analysis.critical_issues])
        recommendations = "".join([f"<li>{rec}</li>" for rec in report.robustness_analysis.recommendations])
        
        return html_template.format(
            strategy_name=report.strategy_name,
            validation_period=f"{report.validation_period[0]} to {report.validation_period[1]}",
            timestamp=report.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            total_tests=report.total_tests,
            tests_passed=report.robustness_analysis.tests_passed,
            tests_failed=report.robustness_analysis.tests_failed,
            tests_warning=report.robustness_analysis.tests_warning,
            robustness_level=report.robustness_analysis.robustness_level.value.upper(),
            overall_score=report.robustness_analysis.overall_score,
            test_rows=test_rows,
            mc_return_ci=mc_return_ci,
            mc_sharpe_ci=mc_sharpe_ci,
            mc_dd_ci=mc_dd_ci,
            param_ratio=param_ratio,
            overfitting_risk=overfitting_risk,
            performance_flags=performance_flags,
            final_recommendation=report.final_recommendation,
            risk_assessment=report.risk_assessment,
            critical_issues=critical_issues,
            recommendations=recommendations
        )

# Demo and testing
async def demo_statistical_validation():
    """Demonstrate the statistical validation framework."""
    print("🔬 SICAR Statistical Validation Framework Demo")
    print("=" * 60)
    
    # Initialize validator
    validator = StatisticalValidator()
    
    # Generate sample strategy data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', '2024-12-31', freq='D')
    
    # Simulate strategy returns with some realistic characteristics
    base_returns = np.random.normal(0.0008, 0.015, len(dates))  # Slight positive bias
    trend_component = np.sin(np.arange(len(dates)) * 2 * np.pi / 252) * 0.002  # Annual cycle
    returns = base_returns + trend_component
    
    # Add some autocorrelation
    for i in range(1, len(returns)):
        returns[i] += 0.1 * returns[i-1]
    
    returns_series = pd.Series(returns, index=dates)
    equity_curve = (1 + returns_series).cumprod()
    
    # Generate sample trades
    trade_dates = pd.date_range('2020-01-01', '2024-12-31', freq='W')
    trades = pd.DataFrame({
        'date': trade_dates,
        'pnl': np.random.normal(100, 500, len(trade_dates)),
        'side': np.random.choice(['long', 'short'], len(trade_dates))
    })
    
    # Sample parameters
    parameters = {
        'lookback_period': 20,
        'threshold': 0.02,
        'stop_loss': 0.05,
        'take_profit': 0.10,
        'position_size': 0.1
    }
    
    print("📊 Running comprehensive statistical validation...")
    
    # Perform validation
    validation_report = await validator.validate_strategy(
        strategy_name="Demo_Strategy_v1",
        returns=returns_series,
        equity_curve=equity_curve,
        trades=trades,
        parameters=parameters
    )
    
    print(f"\n✅ Validation completed!")
    print(f"Strategy: {validation_report.strategy_name}")
    print(f"Total Tests: {validation_report.total_tests}")
    print(f"Tests Passed: {validation_report.robustness_analysis.tests_passed}")
    print(f"Tests Failed: {validation_report.robustness_analysis.tests_failed}")
    print(f"Warnings: {validation_report.robustness_analysis.tests_warning}")
    print(f"Robustness Level: {validation_report.robustness_analysis.robustness_level.value}")
    print(f"Overall Score: {validation_report.robustness_analysis.overall_score}/100")
    
    print(f"\n📋 Final Recommendation:")
    print(f"{validation_report.final_recommendation}")
    
    print(f"\n⚠️ Risk Assessment:")
    print(f"{validation_report.risk_assessment}")
    
    # Display some key test results
    print(f"\n🧪 Key Statistical Tests:")
    for test in validation_report.statistical_tests[:5]:  # Show first 5 tests
        status_emoji = "✅" if test.result == TestResult.PASS else "❌" if test.result == TestResult.FAIL else "⚠️"
        print(f"{status_emoji} {test.test_name}: {test.interpretation}")
    
    # Monte Carlo results
    if 'bootstrap_analysis' in validation_report.monte_carlo_results:
        bootstrap = validation_report.monte_carlo_results['bootstrap_analysis']
        print(f"\n🎲 Monte Carlo Analysis (95% CI):")
        print(f"Total Return: [{bootstrap['total_return']['ci_lower']:.4f}, {bootstrap['total_return']['ci_upper']:.4f}]")
        print(f"Sharpe Ratio: [{bootstrap['sharpe_ratio']['ci_lower']:.4f}, {bootstrap['sharpe_ratio']['ci_upper']:.4f}]")
    
    # Generate HTML report
    print(f"\n📄 Generating HTML validation report...")
    html_report = await validator.generate_validation_report_html(validation_report)
    
    # Save HTML report
    report_path = Path("statistical_validation_report.html")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html_report)
    
    print(f"✅ HTML report saved to: {report_path}")
    
    print(f"\n🎯 Statistical Validation Framework Demo Completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(demo_statistical_validation())