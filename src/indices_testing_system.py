"""
SICAR Indices Testing & Validation System
Sistema completo de testing y validación para estrategias de índices
Incluye métricas de performance, tests estadísticos y validación automatizada
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from dataclasses import dataclass, field
from enum import Enum
import warnings
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import json
import os

# Importar módulos del proyecto
from indices_backtester import IndicesBacktester, BacktestResults
from indices_strategies import IndicesStrategies, StrategyType
from indices_risk_manager import IndicesRiskManager
from indices_data_provider import IndicesDataProvider
from market_hours_system import MarketHoursSystem

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestType(Enum):
    """Tipos de tests disponibles"""
    PERFORMANCE = "performance"
    STATISTICAL = "statistical"
    RISK = "risk"
    ROBUSTNESS = "robustness"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"

class ValidationStatus(Enum):
    """Estados de validación"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    NOT_TESTED = "not_tested"

@dataclass
class TestResult:
    """Resultado de un test individual"""
    test_name: str
    test_type: TestType
    status: ValidationStatus
    value: float
    threshold: float
    description: str
    details: Dict = field(default_factory=dict)

@dataclass
class ValidationReport:
    """Reporte completo de validación"""
    strategy_name: str
    symbol: str
    test_period: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    warning_tests: int
    overall_score: float
    results: List[TestResult] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

class IndicesTestingSystem:
    """
    Sistema completo de testing y validación para estrategias de índices
    """
    
    def __init__(self, data_provider: IndicesDataProvider = None):
        
        self.data_provider = data_provider or IndicesDataProvider()
        self.market_hours = MarketHoursSystem()
        
        # Configuración de tests
        self.test_config = {
            # Tests de performance
            'min_sharpe_ratio': 1.0,
            'min_sortino_ratio': 1.2,
            'max_drawdown': -0.15,  # -15%
            'min_win_rate': 0.45,   # 45%
            'min_profit_factor': 1.2,
            'min_annual_return': 0.08,  # 8%
            
            # Tests estadísticos
            'min_trades': 30,
            'max_correlation_spy': 0.95,
            'min_information_ratio': 0.5,
            'max_var_95': -0.03,  # -3% VaR diario
            
            # Tests de robustez
            'min_calmar_ratio': 0.5,
            'max_volatility': 0.25,  # 25% anual
            'min_stability': 0.7,
            
            # Walk-forward
            'wf_periods': 6,
            'wf_min_consistency': 0.6,
            
            # Monte Carlo
            'mc_simulations': 1000,
            'mc_confidence': 0.95
        }
        
        # Resultados de tests
        self.test_results = {}
        
    def run_comprehensive_test(self, 
                             strategy_type: StrategyType,
                             symbol: str,
                             start_date: str,
                             end_date: str,
                             initial_capital: float = 100000) -> ValidationReport:
        """
        Ejecuta un test completo de una estrategia
        
        Args:
            strategy_type: Tipo de estrategia a testear
            symbol: Símbolo del índice
            start_date: Fecha de inicio
            end_date: Fecha de fin
            initial_capital: Capital inicial
        
        Returns:
            Reporte completo de validación
        """
        
        logger.info(f"Iniciando test completo para {strategy_type.value} en {symbol}")
        
        # Obtener datos
        data = self.data_provider.get_historical_data(symbol, start_date, end_date)
        if data.empty:
            raise ValueError(f"No se pudieron obtener datos para {symbol}")
        
        # Ejecutar backtest base
        backtester = IndicesBacktester(initial_capital=initial_capital)
        strategies = IndicesStrategies()
        
        # Configurar estrategia
        if strategy_type == StrategyType.MOMENTUM:
            strategy_config = strategies.get_momentum_config()
        elif strategy_type == StrategyType.MEAN_REVERSION:
            strategy_config = strategies.get_mean_reversion_config()
        elif strategy_type == StrategyType.HYBRID:
            strategy_config = strategies.get_hybrid_config()
        else:
            strategy_config = strategies.get_breakout_config()
        
        # Ejecutar backtest
        results = backtester.run_backtest(data, symbol, strategy_config)
        
        # Crear reporte de validación
        report = ValidationReport(
            strategy_name=strategy_type.value,
            symbol=symbol,
            test_period=f"{start_date} to {end_date}",
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            warning_tests=0,
            overall_score=0.0
        )
        
        # Ejecutar todos los tests
        test_results = []
        
        # 1. Tests de Performance
        test_results.extend(self._run_performance_tests(results))
        
        # 2. Tests Estadísticos
        test_results.extend(self._run_statistical_tests(results, data))
        
        # 3. Tests de Riesgo
        test_results.extend(self._run_risk_tests(results))
        
        # 4. Tests de Robustez
        test_results.extend(self._run_robustness_tests(results, data, strategy_config))
        
        # 5. Walk-Forward Analysis
        wf_results = self._run_walk_forward_test(
            strategy_type, symbol, start_date, end_date, initial_capital
        )
        test_results.extend(wf_results)
        
        # 6. Monte Carlo Simulation
        mc_results = self._run_monte_carlo_test(results, data)
        test_results.extend(mc_results)
        
        # Compilar resultados
        report.results = test_results
        report.total_tests = len(test_results)
        report.passed_tests = sum(1 for r in test_results if r.status == ValidationStatus.PASSED)
        report.failed_tests = sum(1 for r in test_results if r.status == ValidationStatus.FAILED)
        report.warning_tests = sum(1 for r in test_results if r.status == ValidationStatus.WARNING)
        
        # Calcular score general
        report.overall_score = self._calculate_overall_score(test_results)
        
        # Generar recomendaciones
        report.recommendations = self._generate_recommendations(test_results, results)
        
        # Guardar resultados
        self.test_results[f"{strategy_type.value}_{symbol}"] = report
        
        logger.info(f"Test completo finalizado. Score: {report.overall_score:.2f}")
        
        return report
    
    def _run_performance_tests(self, results: BacktestResults) -> List[TestResult]:
        """Ejecuta tests de performance"""
        
        tests = []
        
        # Test Sharpe Ratio
        tests.append(TestResult(
            test_name="Sharpe Ratio",
            test_type=TestType.PERFORMANCE,
            status=ValidationStatus.PASSED if results.sharpe_ratio >= self.test_config['min_sharpe_ratio'] 
                   else ValidationStatus.FAILED,
            value=results.sharpe_ratio,
            threshold=self.test_config['min_sharpe_ratio'],
            description="Ratio de retorno ajustado por riesgo"
        ))
        
        # Test Sortino Ratio
        tests.append(TestResult(
            test_name="Sortino Ratio",
            test_type=TestType.PERFORMANCE,
            status=ValidationStatus.PASSED if results.sortino_ratio >= self.test_config['min_sortino_ratio']
                   else ValidationStatus.FAILED,
            value=results.sortino_ratio,
            threshold=self.test_config['min_sortino_ratio'],
            description="Ratio de retorno ajustado por downside risk"
        ))
        
        # Test Maximum Drawdown
        tests.append(TestResult(
            test_name="Maximum Drawdown",
            test_type=TestType.PERFORMANCE,
            status=ValidationStatus.PASSED if results.max_drawdown >= self.test_config['max_drawdown']
                   else ValidationStatus.FAILED,
            value=results.max_drawdown,
            threshold=self.test_config['max_drawdown'],
            description="Máxima pérdida desde el pico"
        ))
        
        # Test Win Rate
        win_rate = len([t for t in results.trades if t.pnl > 0]) / len(results.trades) if results.trades else 0
        tests.append(TestResult(
            test_name="Win Rate",
            test_type=TestType.PERFORMANCE,
            status=ValidationStatus.PASSED if win_rate >= self.test_config['min_win_rate']
                   else ValidationStatus.WARNING if win_rate >= self.test_config['min_win_rate'] - 0.05
                   else ValidationStatus.FAILED,
            value=win_rate,
            threshold=self.test_config['min_win_rate'],
            description="Porcentaje de trades ganadores"
        ))
        
        # Test Profit Factor
        winning_trades = [t.pnl for t in results.trades if t.pnl > 0]
        losing_trades = [abs(t.pnl) for t in results.trades if t.pnl < 0]
        
        profit_factor = (sum(winning_trades) / sum(losing_trades)) if losing_trades else float('inf')
        
        tests.append(TestResult(
            test_name="Profit Factor",
            test_type=TestType.PERFORMANCE,
            status=ValidationStatus.PASSED if profit_factor >= self.test_config['min_profit_factor']
                   else ValidationStatus.FAILED,
            value=profit_factor,
            threshold=self.test_config['min_profit_factor'],
            description="Ratio de ganancias brutas vs pérdidas brutas"
        ))
        
        # Test Annual Return
        annual_return = results.total_return * (252 / len(results.equity_curve)) if results.equity_curve else 0
        tests.append(TestResult(
            test_name="Annual Return",
            test_type=TestType.PERFORMANCE,
            status=ValidationStatus.PASSED if annual_return >= self.test_config['min_annual_return']
                   else ValidationStatus.WARNING if annual_return >= self.test_config['min_annual_return'] - 0.02
                   else ValidationStatus.FAILED,
            value=annual_return,
            threshold=self.test_config['min_annual_return'],
            description="Retorno anualizado"
        ))
        
        return tests
    
    def _run_statistical_tests(self, results: BacktestResults, data: pd.DataFrame) -> List[TestResult]:
        """Ejecuta tests estadísticos"""
        
        tests = []
        
        # Test número mínimo de trades
        tests.append(TestResult(
            test_name="Minimum Trades",
            test_type=TestType.STATISTICAL,
            status=ValidationStatus.PASSED if len(results.trades) >= self.test_config['min_trades']
                   else ValidationStatus.WARNING if len(results.trades) >= self.test_config['min_trades'] * 0.7
                   else ValidationStatus.FAILED,
            value=len(results.trades),
            threshold=self.test_config['min_trades'],
            description="Número suficiente de trades para validez estadística"
        ))
        
        # Test de normalidad de retornos
        if len(results.equity_curve) > 10:
            returns = pd.Series(results.equity_curve).pct_change().dropna()
            _, p_value = stats.normaltest(returns)
            
            tests.append(TestResult(
                test_name="Returns Normality",
                test_type=TestType.STATISTICAL,
                status=ValidationStatus.PASSED if p_value > 0.05
                       else ValidationStatus.WARNING,
                value=p_value,
                threshold=0.05,
                description="Test de normalidad de retornos (p-value)"
            ))
        
        # Test de autocorrelación
        if len(results.equity_curve) > 20:
            returns = pd.Series(results.equity_curve).pct_change().dropna()
            autocorr = returns.autocorr(lag=1)
            
            tests.append(TestResult(
                test_name="Returns Autocorrelation",
                test_type=TestType.STATISTICAL,
                status=ValidationStatus.PASSED if abs(autocorr) < 0.3
                       else ValidationStatus.WARNING,
                value=autocorr,
                threshold=0.3,
                description="Autocorrelación de retornos (lag 1)"
            ))
        
        # Test de correlación con SPY (si no es SPY)
        if 'SPY' not in results.symbol:
            try:
                spy_data = self.data_provider.get_historical_data('SPY', 
                    data.index[0].strftime('%Y-%m-%d'), 
                    data.index[-1].strftime('%Y-%m-%d'))
                
                if not spy_data.empty and len(results.equity_curve) > 10:
                    strategy_returns = pd.Series(results.equity_curve).pct_change().dropna()
                    spy_returns = spy_data['Close'].pct_change().dropna()
                    
                    # Alinear fechas
                    common_dates = strategy_returns.index.intersection(spy_returns.index)
                    if len(common_dates) > 10:
                        correlation = strategy_returns.loc[common_dates].corr(
                            spy_returns.loc[common_dates])
                        
                        tests.append(TestResult(
                            test_name="SPY Correlation",
                            test_type=TestType.STATISTICAL,
                            status=ValidationStatus.PASSED if correlation < self.test_config['max_correlation_spy']
                                   else ValidationStatus.WARNING,
                            value=correlation,
                            threshold=self.test_config['max_correlation_spy'],
                            description="Correlación con SPY"
                        ))
            except Exception as e:
                logger.warning(f"No se pudo calcular correlación con SPY: {e}")
        
        return tests
    
    def _run_risk_tests(self, results: BacktestResults) -> List[TestResult]:
        """Ejecuta tests de riesgo"""
        
        tests = []
        
        # Test Calmar Ratio
        calmar_ratio = abs(results.total_return / results.max_drawdown) if results.max_drawdown != 0 else 0
        tests.append(TestResult(
            test_name="Calmar Ratio",
            test_type=TestType.RISK,
            status=ValidationStatus.PASSED if calmar_ratio >= self.test_config['min_calmar_ratio']
                   else ValidationStatus.FAILED,
            value=calmar_ratio,
            threshold=self.test_config['min_calmar_ratio'],
            description="Ratio de retorno anual vs drawdown máximo"
        ))
        
        # Test Volatilidad
        if len(results.equity_curve) > 10:
            returns = pd.Series(results.equity_curve).pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)
            
            tests.append(TestResult(
                test_name="Volatility",
                test_type=TestType.RISK,
                status=ValidationStatus.PASSED if volatility <= self.test_config['max_volatility']
                       else ValidationStatus.WARNING if volatility <= self.test_config['max_volatility'] + 0.05
                       else ValidationStatus.FAILED,
                value=volatility,
                threshold=self.test_config['max_volatility'],
                description="Volatilidad anualizada"
            ))
            
            # Test VaR 95%
            var_95 = np.percentile(returns, 5)
            tests.append(TestResult(
                test_name="VaR 95%",
                test_type=TestType.RISK,
                status=ValidationStatus.PASSED if var_95 >= self.test_config['max_var_95']
                       else ValidationStatus.WARNING if var_95 >= self.test_config['max_var_95'] - 0.01
                       else ValidationStatus.FAILED,
                value=var_95,
                threshold=self.test_config['max_var_95'],
                description="Value at Risk al 95% de confianza"
            ))
        
        # Test de consistencia de retornos
        if len(results.trades) > 12:
            monthly_returns = self._calculate_monthly_returns(results)
            positive_months = sum(1 for r in monthly_returns if r > 0)
            consistency = positive_months / len(monthly_returns)
            
            tests.append(TestResult(
                test_name="Return Consistency",
                test_type=TestType.RISK,
                status=ValidationStatus.PASSED if consistency >= 0.6
                       else ValidationStatus.WARNING if consistency >= 0.5
                       else ValidationStatus.FAILED,
                value=consistency,
                threshold=0.6,
                description="Porcentaje de meses positivos"
            ))
        
        return tests
    
    def _run_robustness_tests(self, results: BacktestResults, 
                            data: pd.DataFrame, strategy_config: Dict) -> List[TestResult]:
        """Ejecuta tests de robustez"""
        
        tests = []
        
        # Test de estabilidad temporal
        stability_score = self._calculate_temporal_stability(results)
        tests.append(TestResult(
            test_name="Temporal Stability",
            test_type=TestType.ROBUSTNESS,
            status=ValidationStatus.PASSED if stability_score >= self.test_config['min_stability']
                   else ValidationStatus.WARNING if stability_score >= self.test_config['min_stability'] - 0.1
                   else ValidationStatus.FAILED,
            value=stability_score,
            threshold=self.test_config['min_stability'],
            description="Estabilidad de performance a lo largo del tiempo"
        ))
        
        # Test de sensibilidad a parámetros
        sensitivity_score = self._test_parameter_sensitivity(data, strategy_config)
        tests.append(TestResult(
            test_name="Parameter Sensitivity",
            test_type=TestType.ROBUSTNESS,
            status=ValidationStatus.PASSED if sensitivity_score >= 0.7
                   else ValidationStatus.WARNING if sensitivity_score >= 0.5
                   else ValidationStatus.FAILED,
            value=sensitivity_score,
            threshold=0.7,
            description="Robustez ante cambios en parámetros"
        ))
        
        return tests
    
    def _run_walk_forward_test(self, strategy_type: StrategyType, symbol: str,
                             start_date: str, end_date: str, 
                             initial_capital: float) -> List[TestResult]:
        """Ejecuta análisis walk-forward"""
        
        tests = []
        
        try:
            # Dividir período en ventanas
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            total_days = (end_dt - start_dt).days
            
            if total_days < 365:  # Menos de un año
                logger.warning("Período muy corto para walk-forward analysis")
                return tests
            
            window_size = total_days // self.test_config['wf_periods']
            wf_results = []
            
            for i in range(self.test_config['wf_periods']):
                wf_start = start_dt + timedelta(days=i * window_size)
                wf_end = min(start_dt + timedelta(days=(i + 1) * window_size), end_dt)
                
                # Ejecutar backtest para esta ventana
                data = self.data_provider.get_historical_data(
                    symbol, wf_start.strftime('%Y-%m-%d'), wf_end.strftime('%Y-%m-%d')
                )
                
                if not data.empty:
                    backtester = IndicesBacktester(initial_capital=initial_capital)
                    strategies = IndicesStrategies()
                    
                    if strategy_type == StrategyType.MOMENTUM:
                        config = strategies.get_momentum_config()
                    elif strategy_type == StrategyType.MEAN_REVERSION:
                        config = strategies.get_mean_reversion_config()
                    else:
                        config = strategies.get_hybrid_config()
                    
                    result = backtester.run_backtest(data, symbol, config)
                    wf_results.append(result.total_return)
            
            if wf_results:
                # Calcular consistencia
                positive_periods = sum(1 for r in wf_results if r > 0)
                consistency = positive_periods / len(wf_results)
                
                tests.append(TestResult(
                    test_name="Walk-Forward Consistency",
                    test_type=TestType.WALK_FORWARD,
                    status=ValidationStatus.PASSED if consistency >= self.test_config['wf_min_consistency']
                           else ValidationStatus.WARNING if consistency >= 0.5
                           else ValidationStatus.FAILED,
                    value=consistency,
                    threshold=self.test_config['wf_min_consistency'],
                    description="Consistencia en análisis walk-forward",
                    details={'periods': len(wf_results), 'returns': wf_results}
                ))
        
        except Exception as e:
            logger.error(f"Error en walk-forward analysis: {e}")
        
        return tests
    
    def _run_monte_carlo_test(self, results: BacktestResults, 
                            data: pd.DataFrame) -> List[TestResult]:
        """Ejecuta simulación Monte Carlo"""
        
        tests = []
        
        try:
            if len(results.trades) < 10:
                return tests
            
            # Extraer retornos de trades
            trade_returns = [t.pnl / 10000 for t in results.trades]  # Normalizar
            
            # Simulaciones Monte Carlo
            mc_results = []
            np.random.seed(42)
            
            for _ in range(self.test_config['mc_simulations']):
                # Resamplear trades aleatoriamente
                simulated_trades = np.random.choice(trade_returns, len(trade_returns), replace=True)
                mc_results.append(sum(simulated_trades))
            
            # Calcular percentiles
            mc_results = np.array(mc_results)
            percentile_5 = np.percentile(mc_results, 5)
            percentile_95 = np.percentile(mc_results, 95)
            actual_return = sum(trade_returns)
            
            # Test de robustez Monte Carlo
            confidence_score = (actual_return - percentile_5) / (percentile_95 - percentile_5)
            
            tests.append(TestResult(
                test_name="Monte Carlo Robustness",
                test_type=TestType.MONTE_CARLO,
                status=ValidationStatus.PASSED if confidence_score >= 0.3
                       else ValidationStatus.WARNING if confidence_score >= 0.1
                       else ValidationStatus.FAILED,
                value=confidence_score,
                threshold=0.3,
                description="Robustez en simulación Monte Carlo",
                details={
                    'percentile_5': percentile_5,
                    'percentile_95': percentile_95,
                    'actual_return': actual_return
                }
            ))
        
        except Exception as e:
            logger.error(f"Error en Monte Carlo simulation: {e}")
        
        return tests
    
    def _calculate_overall_score(self, test_results: List[TestResult]) -> float:
        """Calcula score general basado en todos los tests"""
        
        if not test_results:
            return 0.0
        
        # Pesos por tipo de test
        weights = {
            TestType.PERFORMANCE: 0.3,
            TestType.STATISTICAL: 0.15,
            TestType.RISK: 0.25,
            TestType.ROBUSTNESS: 0.15,
            TestType.WALK_FORWARD: 0.1,
            TestType.MONTE_CARLO: 0.05
        }
        
        # Calcular score por tipo
        type_scores = {}
        for test_type in TestType:
            type_tests = [t for t in test_results if t.test_type == test_type]
            if type_tests:
                passed = sum(1 for t in type_tests if t.status == ValidationStatus.PASSED)
                warning = sum(1 for t in type_tests if t.status == ValidationStatus.WARNING)
                total = len(type_tests)
                
                # Score: 100% passed, 50% warning, 0% failed
                type_score = (passed + warning * 0.5) / total
                type_scores[test_type] = type_score
        
        # Score ponderado
        overall_score = sum(
            type_scores.get(test_type, 0) * weight 
            for test_type, weight in weights.items()
        )
        
        return overall_score * 100  # Convertir a porcentaje
    
    def _generate_recommendations(self, test_results: List[TestResult], 
                                results: BacktestResults) -> List[str]:
        """Genera recomendaciones basadas en los resultados"""
        
        recommendations = []
        
        # Analizar tests fallidos
        failed_tests = [t for t in test_results if t.status == ValidationStatus.FAILED]
        warning_tests = [t for t in test_results if t.status == ValidationStatus.WARNING]
        
        # Recomendaciones por performance
        performance_failed = [t for t in failed_tests if t.test_type == TestType.PERFORMANCE]
        if performance_failed:
            if any('Sharpe' in t.test_name for t in performance_failed):
                recommendations.append("Considerar ajustar parámetros para mejorar ratio riesgo-retorno")
            if any('Drawdown' in t.test_name for t in performance_failed):
                recommendations.append("Implementar stops más estrictos o reducir tamaño de posición")
            if any('Win Rate' in t.test_name for t in performance_failed):
                recommendations.append("Revisar criterios de entrada y salida para mejorar precisión")
        
        # Recomendaciones por riesgo
        risk_failed = [t for t in failed_tests if t.test_type == TestType.RISK]
        if risk_failed:
            if any('Volatility' in t.test_name for t in risk_failed):
                recommendations.append("Reducir frecuencia de trading o implementar filtros de volatilidad")
            if any('VaR' in t.test_name for t in risk_failed):
                recommendations.append("Implementar límites de pérdida diaria más estrictos")
        
        # Recomendaciones por robustez
        robustness_failed = [t for t in failed_tests if t.test_type == TestType.ROBUSTNESS]
        if robustness_failed:
            recommendations.append("Optimizar parámetros con validación cruzada")
            recommendations.append("Considerar ensemble de estrategias para mayor robustez")
        
        # Recomendaciones generales
        if len(failed_tests) > len(test_results) * 0.3:
            recommendations.append("Estrategia requiere optimización significativa antes de implementación")
        elif len(warning_tests) > len(test_results) * 0.2:
            recommendations.append("Monitorear de cerca el performance en trading en vivo")
        
        if not recommendations:
            recommendations.append("Estrategia muestra buen performance general - proceder con implementación")
        
        return recommendations
    
    def _calculate_monthly_returns(self, results: BacktestResults) -> List[float]:
        """Calcula retornos mensuales"""
        
        if not results.equity_curve:
            return []
        
        equity_series = pd.Series(results.equity_curve)
        monthly_equity = equity_series.resample('M').last()
        monthly_returns = monthly_equity.pct_change().dropna().tolist()
        
        return monthly_returns
    
    def _calculate_temporal_stability(self, results: BacktestResults) -> float:
        """Calcula estabilidad temporal de la estrategia"""
        
        if len(results.equity_curve) < 50:
            return 0.5  # Score neutral para datos insuficientes
        
        # Dividir en períodos y calcular retornos
        equity_series = pd.Series(results.equity_curve)
        n_periods = min(5, len(equity_series) // 10)
        
        if n_periods < 2:
            return 0.5
        
        period_size = len(equity_series) // n_periods
        period_returns = []
        
        for i in range(n_periods):
            start_idx = i * period_size
            end_idx = min((i + 1) * period_size, len(equity_series))
            
            if end_idx > start_idx + 1:
                period_equity = equity_series.iloc[start_idx:end_idx]
                period_return = (period_equity.iloc[-1] - period_equity.iloc[0]) / period_equity.iloc[0]
                period_returns.append(period_return)
        
        if len(period_returns) < 2:
            return 0.5
        
        # Calcular estabilidad como 1 - coeficiente de variación
        mean_return = np.mean(period_returns)
        std_return = np.std(period_returns)
        
        if mean_return == 0:
            return 0.0
        
        cv = abs(std_return / mean_return)
        stability = max(0, 1 - cv)
        
        return min(1.0, stability)
    
    def _test_parameter_sensitivity(self, data: pd.DataFrame, 
                                  strategy_config: Dict) -> float:
        """Testa sensibilidad a cambios en parámetros"""
        
        # Simplificado - en producción hacer grid search completo
        try:
            base_config = strategy_config.copy()
            
            # Variar parámetros clave ±20%
            variations = [0.8, 0.9, 1.1, 1.2]
            results = []
            
            for variation in variations:
                modified_config = base_config.copy()
                
                # Modificar parámetros principales
                if 'rsi_period' in modified_config:
                    modified_config['rsi_period'] = int(modified_config['rsi_period'] * variation)
                if 'ema_fast' in modified_config:
                    modified_config['ema_fast'] = int(modified_config['ema_fast'] * variation)
                
                # Ejecutar backtest rápido
                backtester = IndicesBacktester(initial_capital=100000)
                result = backtester.run_backtest(data, 'TEST', modified_config)
                results.append(result.total_return)
            
            # Calcular estabilidad de resultados
            if results:
                std_results = np.std(results)
                mean_results = np.mean(results)
                
                if mean_results != 0:
                    sensitivity_score = max(0, 1 - abs(std_results / mean_results))
                else:
                    sensitivity_score = 0
            else:
                sensitivity_score = 0
            
            return min(1.0, sensitivity_score)
        
        except Exception as e:
            logger.warning(f"Error en test de sensibilidad: {e}")
            return 0.5
    
    def save_report(self, report: ValidationReport, filepath: str):
        """Guarda el reporte en formato JSON"""
        
        # Convertir a diccionario serializable
        report_dict = {
            'strategy_name': report.strategy_name,
            'symbol': report.symbol,
            'test_period': report.test_period,
            'total_tests': report.total_tests,
            'passed_tests': report.passed_tests,
            'failed_tests': report.failed_tests,
            'warning_tests': report.warning_tests,
            'overall_score': report.overall_score,
            'results': [
                {
                    'test_name': r.test_name,
                    'test_type': r.test_type.value,
                    'status': r.status.value,
                    'value': r.value,
                    'threshold': r.threshold,
                    'description': r.description,
                    'details': r.details
                }
                for r in report.results
            ],
            'recommendations': report.recommendations,
            'generated_at': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Reporte guardado en: {filepath}")
    
    def create_visual_report(self, report: ValidationReport, save_path: str = None):
        """Crea reporte visual con gráficos"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Reporte de Validación: {report.strategy_name} - {report.symbol}', 
                    fontsize=16, fontweight='bold')
        
        # 1. Distribución de resultados por tipo de test
        test_types = [r.test_type.value for r in report.results]
        statuses = [r.status.value for r in report.results]
        
        status_counts = pd.DataFrame({'type': test_types, 'status': statuses})
        status_pivot = status_counts.pivot_table(index='type', columns='status', 
                                                aggfunc=len, fill_value=0)
        
        status_pivot.plot(kind='bar', ax=axes[0,0], stacked=True, 
                         color=['green', 'red', 'orange'])
        axes[0,0].set_title('Resultados por Tipo de Test')
        axes[0,0].set_xlabel('Tipo de Test')
        axes[0,0].set_ylabel('Número de Tests')
        axes[0,0].legend(title='Status')
        axes[0,0].tick_params(axis='x', rotation=45)
        
        # 2. Score general
        score_data = [report.overall_score, 100 - report.overall_score]
        colors = ['green' if report.overall_score >= 70 else 'orange' if report.overall_score >= 50 else 'red', 'lightgray']
        
        axes[0,1].pie(score_data, labels=['Score', 'Restante'], colors=colors, 
                     autopct='%1.1f%%', startangle=90)
        axes[0,1].set_title(f'Score General: {report.overall_score:.1f}%')
        
        # 3. Tests fallidos vs umbrales
        failed_tests = [r for r in report.results if r.status == ValidationStatus.FAILED]
        if failed_tests:
            test_names = [r.test_name for r in failed_tests]
            values = [r.value for r in failed_tests]
            thresholds = [r.threshold for r in failed_tests]
            
            x = np.arange(len(test_names))
            width = 0.35
            
            axes[1,0].bar(x - width/2, values, width, label='Valor Actual', alpha=0.7)
            axes[1,0].bar(x + width/2, thresholds, width, label='Umbral', alpha=0.7)
            axes[1,0].set_title('Tests Fallidos vs Umbrales')
            axes[1,0].set_xlabel('Tests')
            axes[1,0].set_ylabel('Valor')
            axes[1,0].set_xticks(x)
            axes[1,0].set_xticklabels(test_names, rotation=45, ha='right')
            axes[1,0].legend()
        else:
            axes[1,0].text(0.5, 0.5, 'No hay tests fallidos', 
                          ha='center', va='center', transform=axes[1,0].transAxes,
                          fontsize=14, color='green')
            axes[1,0].set_title('Tests Fallidos')
        
        # 4. Resumen de recomendaciones
        axes[1,1].axis('off')
        recommendations_text = '\n'.join([f"• {rec}" for rec in report.recommendations[:5]])
        axes[1,1].text(0.05, 0.95, 'Recomendaciones Principales:', 
                      transform=axes[1,1].transAxes, fontsize=12, fontweight='bold')
        axes[1,1].text(0.05, 0.85, recommendations_text, 
                      transform=axes[1,1].transAxes, fontsize=10, 
                      verticalalignment='top', wrap=True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Reporte visual guardado en: {save_path}")
        
        plt.show()

# Función de utilidad
def create_testing_system(data_provider: IndicesDataProvider = None) -> IndicesTestingSystem:
    """Crea una instancia del sistema de testing"""
    return IndicesTestingSystem(data_provider)

if __name__ == "__main__":
    # Ejemplo de uso
    testing_system = create_testing_system()
    
    # Ejecutar test completo
    report = testing_system.run_comprehensive_test(
        strategy_type=StrategyType.MOMENTUM,
        symbol='SPY',
        start_date='2023-01-01',
        end_date='2023-12-31',
        initial_capital=100000
    )
    
    print(f"Score general: {report.overall_score:.2f}%")
    print(f"Tests pasados: {report.passed_tests}/{report.total_tests}")
    print(f"Recomendaciones: {len(report.recommendations)}")
    
    # Guardar reporte
    testing_system.save_report(report, 'validation_report.json')
    testing_system.create_visual_report(report, 'validation_report.png')