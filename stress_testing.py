#!/usr/bin/env python3
"""
Sistema de Pruebas de Estrés para Estrategia de Trading Algorítmico
Evalúa robustez bajo diferentes condiciones de mercado
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
from enum import Enum
warnings.filterwarnings('ignore')

class MarketRegime(Enum):
    """Regímenes de mercado"""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    RANGING = "ranging"
    CRISIS = "crisis"
    RECOVERY = "recovery"

@dataclass
class StressScenario:
    """Escenario de estrés"""
    name: str
    description: str
    regime: MarketRegime
    parameters: Dict[str, Any]
    duration_days: int
    severity: float  # 0-1, donde 1 es máximo estrés
    
@dataclass
class StressTestResult:
    """Resultado de prueba de estrés"""
    scenario_name: str
    regime: MarketRegime
    total_return: float
    daily_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_factor: float
    var_95: float
    trades_count: int
    volatility: float
    calmar_ratio: float
    recovery_time: float
    stress_score: float  # Score compuesto de resistencia al estrés
    passed: bool  # Si pasó los criterios mínimos
    
@dataclass
class StressTestSuite:
    """Suite completa de pruebas de estrés"""
    results: List[StressTestResult]
    overall_score: float
    robustness_rating: str  # Excelente, Bueno, Regular, Malo
    critical_failures: List[str]
    recommendations: List[str]
    risk_assessment: Dict[str, Any]
    
class StressTester:
    """
    Sistema avanzado de pruebas de estrés que evalúa:
    - Resistencia a diferentes regímenes de mercado
    - Comportamiento bajo volatilidad extrema
    - Recuperación después de drawdowns
    - Estabilidad en mercados laterales
    - Rendimiento en crisis financieras
    """
    
    def __init__(self, target_daily_return: float = 0.006,
                 max_acceptable_drawdown: float = 0.15,
                 min_sharpe_ratio: float = 1.0):
        
        self.target_daily_return = target_daily_return
        self.max_acceptable_drawdown = max_acceptable_drawdown
        self.min_sharpe_ratio = min_sharpe_ratio
        
        # Configuración de logging
        self.logger = logging.getLogger(__name__)
        
        # Criterios de aprobación
        self.pass_criteria = {
            'min_daily_return': target_daily_return * 0.5,  # 50% del objetivo
            'max_drawdown': max_acceptable_drawdown,
            'min_sharpe': min_sharpe_ratio * 0.7,  # 70% del objetivo
            'min_win_rate': 0.45,
            'min_profit_factor': 1.1,
            'max_var_95': -0.05  # Máximo 5% VaR diario
        }
        
        # Pesos para score compuesto
        self.stress_weights = {
            'return_stability': 0.25,
            'drawdown_control': 0.30,
            'risk_management': 0.25,
            'consistency': 0.20
        }
        
    def create_stress_scenarios(self) -> List[StressScenario]:
        """Crear escenarios de estrés comprehensivos"""
        
        scenarios = [
            # Mercado alcista extremo
            StressScenario(
                name="Bull Market Extremo",
                description="Mercado alcista con tendencia fuerte y baja volatilidad",
                regime=MarketRegime.BULL,
                parameters={
                    'trend_strength': 0.8,
                    'volatility_multiplier': 0.6,
                    'volume_increase': 1.5,
                    'gap_frequency': 0.1
                },
                duration_days=90,
                severity=0.3
            ),
            
            # Mercado bajista severo
            StressScenario(
                name="Bear Market Severo",
                description="Caída sostenida con alta volatilidad y pánico",
                regime=MarketRegime.BEAR,
                parameters={
                    'trend_strength': -0.7,
                    'volatility_multiplier': 2.5,
                    'volume_increase': 2.0,
                    'gap_frequency': 0.3,
                    'panic_events': 5
                },
                duration_days=60,
                severity=0.9
            ),
            
            # Mercado lateral con whipsaws
            StressScenario(
                name="Sideways con Whipsaws",
                description="Mercado lateral con múltiples señales falsas",
                regime=MarketRegime.SIDEWAYS,
                parameters={
                    'range_bound': 0.05,
                    'whipsaw_frequency': 0.4,
                    'volatility_multiplier': 1.2,
                    'false_breakouts': 8
                },
                duration_days=120,
                severity=0.6
            ),
            
            # Alta volatilidad extrema
            StressScenario(
                name="Volatilidad Extrema",
                description="Volatilidad intraday extrema sin dirección clara",
                regime=MarketRegime.HIGH_VOLATILITY,
                parameters={
                    'volatility_multiplier': 4.0,
                    'intraday_range': 0.15,
                    'gap_frequency': 0.5,
                    'volume_spikes': 10
                },
                duration_days=30,
                severity=0.8
            ),
            
            # Baja volatilidad (mercado dormido)
            StressScenario(
                name="Baja Volatilidad",
                description="Mercado con muy baja volatilidad y volumen",
                regime=MarketRegime.LOW_VOLATILITY,
                parameters={
                    'volatility_multiplier': 0.3,
                    'volume_reduction': 0.4,
                    'range_compression': 0.8,
                    'spread_widening': 1.5
                },
                duration_days=45,
                severity=0.4
            ),
            
            # Crisis financiera
            StressScenario(
                name="Crisis Financiera",
                description="Colapso del mercado con liquidez limitada",
                regime=MarketRegime.CRISIS,
                parameters={
                    'crash_magnitude': -0.5,
                    'volatility_multiplier': 5.0,
                    'liquidity_reduction': 0.3,
                    'correlation_breakdown': True,
                    'circuit_breakers': 3
                },
                duration_days=21,
                severity=1.0
            ),
            
            # Recuperación post-crisis
            StressScenario(
                name="Recuperación Post-Crisis",
                description="Recuperación volátil después de una crisis",
                regime=MarketRegime.RECOVERY,
                parameters={
                    'recovery_rate': 0.6,
                    'volatility_multiplier': 2.0,
                    'false_rallies': 4,
                    'volume_inconsistency': 1.8
                },
                duration_days=60,
                severity=0.7
            ),
            
            # Mercado trending fuerte
            StressScenario(
                name="Trending Fuerte",
                description="Tendencia muy fuerte con pocas correcciones",
                regime=MarketRegime.TRENDING,
                parameters={
                    'trend_strength': 0.9,
                    'correction_frequency': 0.1,
                    'momentum_persistence': 0.9,
                    'volume_confirmation': True
                },
                duration_days=75,
                severity=0.5
            ),
            
            # Mercado ranging con breakouts falsos
            StressScenario(
                name="Ranging con Breakouts Falsos",
                description="Mercado en rango con múltiples breakouts falsos",
                regime=MarketRegime.RANGING,
                parameters={
                    'range_size': 0.08,
                    'false_breakout_frequency': 0.6,
                    'volatility_clusters': True,
                    'support_resistance_tests': 12
                },
                duration_days=90,
                severity=0.6
            )
        ]
        
        return scenarios
        
    def apply_stress_scenario(self, data: pd.DataFrame, scenario: StressScenario) -> pd.DataFrame:
        """Aplicar escenario de estrés a los datos históricos"""
        
        stressed_data = data.copy()
        params = scenario.parameters
        
        if scenario.regime == MarketRegime.BULL:
            stressed_data = self._apply_bull_stress(stressed_data, params)
        elif scenario.regime == MarketRegime.BEAR:
            stressed_data = self._apply_bear_stress(stressed_data, params)
        elif scenario.regime == MarketRegime.SIDEWAYS:
            stressed_data = self._apply_sideways_stress(stressed_data, params)
        elif scenario.regime == MarketRegime.HIGH_VOLATILITY:
            stressed_data = self._apply_high_volatility_stress(stressed_data, params)
        elif scenario.regime == MarketRegime.LOW_VOLATILITY:
            stressed_data = self._apply_low_volatility_stress(stressed_data, params)
        elif scenario.regime == MarketRegime.CRISIS:
            stressed_data = self._apply_crisis_stress(stressed_data, params)
        elif scenario.regime == MarketRegime.RECOVERY:
            stressed_data = self._apply_recovery_stress(stressed_data, params)
        elif scenario.regime == MarketRegime.TRENDING:
            stressed_data = self._apply_trending_stress(stressed_data, params)
        elif scenario.regime == MarketRegime.RANGING:
            stressed_data = self._apply_ranging_stress(stressed_data, params)
            
        return stressed_data
        
    def _apply_bull_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de mercado alcista"""
        
        # Tendencia alcista fuerte
        trend_strength = params.get('trend_strength', 0.8)
        days = len(data) / 24  # Asumiendo datos horarios
        trend = np.linspace(0, trend_strength, len(data))
        
        # Reducir volatilidad
        vol_mult = params.get('volatility_multiplier', 0.6)
        returns = data['close'].pct_change().fillna(0)
        adjusted_returns = returns * vol_mult + trend / len(data)
        
        # Aplicar cambios
        data['close'] = data['close'].iloc[0] * (1 + adjusted_returns).cumprod()
        data['high'] = data['close'] * (1 + abs(returns) * 0.5)
        data['low'] = data['close'] * (1 - abs(returns) * 0.3)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        # Aumentar volumen
        vol_increase = params.get('volume_increase', 1.5)
        data['volume'] *= vol_increase
        
        return data
        
    def _apply_bear_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de mercado bajista"""
        
        # Tendencia bajista fuerte
        trend_strength = params.get('trend_strength', -0.7)
        trend = np.linspace(0, trend_strength, len(data))
        
        # Aumentar volatilidad significativamente
        vol_mult = params.get('volatility_multiplier', 2.5)
        returns = data['close'].pct_change().fillna(0)
        
        # Agregar eventos de pánico
        panic_events = params.get('panic_events', 5)
        panic_indices = np.random.choice(len(data), size=panic_events, replace=False)
        
        adjusted_returns = returns * vol_mult + trend / len(data)
        
        # Aplicar eventos de pánico
        for idx in panic_indices:
            panic_drop = np.random.uniform(-0.15, -0.05)  # Caídas del 5-15%
            adjusted_returns.iloc[idx] = panic_drop
            
        # Aplicar cambios
        data['close'] = data['close'].iloc[0] * (1 + adjusted_returns).cumprod()
        data['high'] = data['close'] * (1 + np.maximum(adjusted_returns, 0) * 1.2)
        data['low'] = data['close'] * (1 + np.minimum(adjusted_returns, 0) * 1.5)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        # Aumentar volumen durante pánico
        vol_increase = params.get('volume_increase', 2.0)
        data['volume'] *= vol_increase
        
        return data
        
    def _apply_sideways_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de mercado lateral"""
        
        range_bound = params.get('range_bound', 0.05)
        whipsaw_freq = params.get('whipsaw_frequency', 0.4)
        
        # Crear movimiento lateral con whipsaws
        base_price = data['close'].iloc[0]
        
        # Generar señales falsas
        false_signals = np.random.random(len(data)) < whipsaw_freq
        
        # Movimiento lateral con ruido
        lateral_movement = np.random.uniform(-range_bound, range_bound, len(data))
        
        # Agregar whipsaws
        whipsaw_magnitude = np.where(false_signals, 
                                   np.random.uniform(-0.03, 0.03, len(data)), 0)
        
        total_movement = lateral_movement + whipsaw_magnitude
        
        # Aplicar cambios
        data['close'] = base_price * (1 + total_movement.cumsum() * 0.1)
        
        # Ajustar OHLV
        volatility = abs(total_movement) * params.get('volatility_multiplier', 1.2)
        data['high'] = data['close'] * (1 + volatility)
        data['low'] = data['close'] * (1 - volatility)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        return data
        
    def _apply_high_volatility_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de alta volatilidad"""
        
        vol_mult = params.get('volatility_multiplier', 4.0)
        intraday_range = params.get('intraday_range', 0.15)
        
        # Aumentar volatilidad extremadamente
        returns = data['close'].pct_change().fillna(0)
        high_vol_returns = returns * vol_mult
        
        # Agregar gaps aleatorios
        gap_freq = params.get('gap_frequency', 0.5)
        gap_events = np.random.random(len(data)) < gap_freq
        gaps = np.where(gap_events, np.random.uniform(-0.08, 0.08, len(data)), 0)
        
        total_returns = high_vol_returns + gaps
        
        # Aplicar cambios
        data['close'] = data['close'].iloc[0] * (1 + total_returns).cumprod()
        
        # Rangos intraday extremos
        data['high'] = data['close'] * (1 + intraday_range)
        data['low'] = data['close'] * (1 - intraday_range)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        # Spikes de volumen
        volume_spikes = params.get('volume_spikes', 10)
        spike_indices = np.random.choice(len(data), size=volume_spikes, replace=False)
        for idx in spike_indices:
            data['volume'].iloc[idx] *= np.random.uniform(5, 15)
            
        return data
        
    def _apply_low_volatility_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de baja volatilidad"""
        
        vol_mult = params.get('volatility_multiplier', 0.3)
        vol_reduction = params.get('volume_reduction', 0.4)
        
        # Reducir volatilidad drásticamente
        returns = data['close'].pct_change().fillna(0)
        low_vol_returns = returns * vol_mult
        
        # Comprimir rangos
        range_compression = params.get('range_compression', 0.8)
        
        # Aplicar cambios
        data['close'] = data['close'].iloc[0] * (1 + low_vol_returns).cumprod()
        
        # Rangos muy pequeños
        range_size = abs(low_vol_returns) * range_compression
        data['high'] = data['close'] * (1 + range_size)
        data['low'] = data['close'] * (1 - range_size)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        # Reducir volumen
        data['volume'] *= vol_reduction
        
        return data
        
    def _apply_crisis_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de crisis financiera"""
        
        crash_magnitude = params.get('crash_magnitude', -0.5)
        vol_mult = params.get('volatility_multiplier', 5.0)
        liquidity_reduction = params.get('liquidity_reduction', 0.3)
        
        # Crash inicial
        crash_period = len(data) // 4  # Primer 25% del período
        crash_returns = np.linspace(0, crash_magnitude, crash_period)
        
        # Alta volatilidad durante toda la crisis
        returns = data['close'].pct_change().fillna(0)
        crisis_returns = returns * vol_mult
        
        # Combinar crash y volatilidad
        total_returns = crisis_returns.copy()
        total_returns.iloc[:crash_period] += crash_returns
        
        # Circuit breakers (pausas en trading)
        circuit_breakers = params.get('circuit_breakers', 3)
        cb_indices = np.random.choice(len(data), size=circuit_breakers, replace=False)
        for idx in cb_indices:
            # Simular pausa: precio se mantiene
            total_returns.iloc[idx:idx+3] = 0
            
        # Aplicar cambios
        data['close'] = data['close'].iloc[0] * (1 + total_returns).cumprod()
        
        # Rangos extremos
        data['high'] = data['close'] * (1 + abs(total_returns) * 1.5)
        data['low'] = data['close'] * (1 - abs(total_returns) * 2.0)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        # Reducir liquidez (volumen)
        data['volume'] *= liquidity_reduction
        
        return data
        
    def _apply_recovery_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de recuperación post-crisis"""
        
        recovery_rate = params.get('recovery_rate', 0.6)
        vol_mult = params.get('volatility_multiplier', 2.0)
        
        # Tendencia de recuperación con volatilidad
        recovery_trend = np.linspace(0, recovery_rate, len(data))
        
        # Alta volatilidad durante recuperación
        returns = data['close'].pct_change().fillna(0)
        volatile_returns = returns * vol_mult
        
        # Falsos rallies
        false_rallies = params.get('false_rallies', 4)
        rally_indices = np.random.choice(len(data), size=false_rallies, replace=False)
        
        total_returns = volatile_returns + recovery_trend / len(data)
        
        # Agregar falsos rallies seguidos de caídas
        for idx in rally_indices:
            if idx < len(data) - 10:
                # Rally falso
                total_returns.iloc[idx:idx+3] += 0.05
                # Caída posterior
                total_returns.iloc[idx+3:idx+6] -= 0.07
                
        # Aplicar cambios
        data['close'] = data['close'].iloc[0] * (1 + total_returns).cumprod()
        data['high'] = data['close'] * (1 + np.maximum(total_returns, 0) * 1.3)
        data['low'] = data['close'] * (1 + np.minimum(total_returns, 0) * 1.8)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        return data
        
    def _apply_trending_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de mercado trending fuerte"""
        
        trend_strength = params.get('trend_strength', 0.9)
        correction_freq = params.get('correction_frequency', 0.1)
        
        # Tendencia fuerte y persistente
        trend = np.linspace(0, trend_strength, len(data))
        
        # Pocas correcciones
        corrections = np.random.random(len(data)) < correction_freq
        correction_magnitude = np.where(corrections, 
                                      np.random.uniform(-0.05, -0.02, len(data)), 0)
        
        # Aplicar cambios
        returns = data['close'].pct_change().fillna(0)
        trending_returns = returns * 0.8 + trend / len(data) + correction_magnitude
        
        data['close'] = data['close'].iloc[0] * (1 + trending_returns).cumprod()
        data['high'] = data['close'] * (1 + abs(trending_returns) * 0.7)
        data['low'] = data['close'] * (1 - abs(trending_returns) * 0.5)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        return data
        
    def _apply_ranging_stress(self, data: pd.DataFrame, params: Dict) -> pd.DataFrame:
        """Aplicar estrés de mercado en rango"""
        
        range_size = params.get('range_size', 0.08)
        false_breakout_freq = params.get('false_breakout_frequency', 0.6)
        
        # Movimiento en rango
        base_price = data['close'].iloc[0]
        range_movement = np.sin(np.linspace(0, 4*np.pi, len(data))) * range_size
        
        # Breakouts falsos
        false_breakouts = np.random.random(len(data)) < false_breakout_freq
        breakout_magnitude = np.where(false_breakouts,
                                    np.random.uniform(-0.04, 0.04, len(data)), 0)
        
        total_movement = range_movement + breakout_magnitude
        
        # Aplicar cambios
        data['close'] = base_price * (1 + total_movement)
        data['high'] = data['close'] * (1 + abs(total_movement) * 1.2)
        data['low'] = data['close'] * (1 - abs(total_movement) * 1.2)
        data['open'] = data['close'].shift(1).fillna(data['close'].iloc[0])
        
        return data
        
    def run_stress_test(self, strategy_func: Callable, data: pd.DataFrame,
                       params: Dict, scenario: StressScenario) -> StressTestResult:
        """Ejecutar una prueba de estrés individual"""
        
        self.logger.info(f"Ejecutando prueba de estrés: {scenario.name}")
        
        try:
            # Aplicar escenario de estrés
            stressed_data = self.apply_stress_scenario(data, scenario)
            
            # Ejecutar estrategia
            results = strategy_func(stressed_data, params)
            
            if not results or 'trades' not in results:
                return self._create_failed_result(scenario)
                
            trades = results['trades']
            equity_curve = results.get('equity_curve', [])
            
            if not trades:
                return self._create_failed_result(scenario)
                
            # Calcular métricas
            metrics = self._calculate_stress_metrics(trades, equity_curve, scenario)
            
            # Evaluar si pasó la prueba
            passed = self._evaluate_pass_criteria(metrics)
            
            return StressTestResult(
                scenario_name=scenario.name,
                regime=scenario.regime,
                total_return=metrics['total_return'],
                daily_return=metrics['daily_return'],
                max_drawdown=metrics['max_drawdown'],
                sharpe_ratio=metrics['sharpe_ratio'],
                sortino_ratio=metrics['sortino_ratio'],
                win_rate=metrics['win_rate'],
                profit_factor=metrics['profit_factor'],
                var_95=metrics['var_95'],
                trades_count=metrics['trades_count'],
                volatility=metrics['volatility'],
                calmar_ratio=metrics['calmar_ratio'],
                recovery_time=metrics['recovery_time'],
                stress_score=metrics['stress_score'],
                passed=passed
            )
            
        except Exception as e:
            self.logger.error(f"Error en prueba de estrés {scenario.name}: {e}")
            return self._create_failed_result(scenario)
            
    def _create_failed_result(self, scenario: StressScenario) -> StressTestResult:
        """Crear resultado fallido"""
        return StressTestResult(
            scenario_name=scenario.name,
            regime=scenario.regime,
            total_return=-1.0,
            daily_return=-1.0,
            max_drawdown=1.0,
            sharpe_ratio=-10.0,
            sortino_ratio=-10.0,
            win_rate=0.0,
            profit_factor=0.0,
            var_95=-1.0,
            trades_count=0,
            volatility=0.0,
            calmar_ratio=-10.0,
            recovery_time=999.0,
            stress_score=0.0,
            passed=False
        )
        
    def _calculate_stress_metrics(self, trades: List[Dict], equity_curve: List[float],
                                scenario: StressScenario) -> Dict:
        """Calcular métricas específicas para pruebas de estrés"""
        
        # Métricas básicas
        pnls = [trade.get('pnl', 0) for trade in trades if 'pnl' in trade]
        
        if not pnls:
            return self._get_default_metrics()
            
        total_return = sum(pnls)
        trades_count = len(pnls)
        
        # Retorno diario
        if equity_curve and len(equity_curve) > 1:
            days = len(equity_curve) / 24
            daily_return = (total_return / equity_curve[0]) / days if days > 0 else 0
        else:
            daily_return = 0
            
        # Win rate y profit factor
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) if pnls else 0
        
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Métricas de riesgo
        if equity_curve and len(equity_curve) > 1:
            equity_series = pd.Series(equity_curve)
            returns = equity_series.pct_change().dropna()
            
            if len(returns) > 0:
                # Volatilidad
                volatility = returns.std() * np.sqrt(24 * 365)
                
                # Sharpe y Sortino
                mean_return = returns.mean() * 24 * 365
                sharpe_ratio = mean_return / volatility if volatility > 0 else 0
                
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
                
                # Tiempo de recuperación
                recovery_time = self._calculate_recovery_time(drawdown)
                
            else:
                volatility = sharpe_ratio = sortino_ratio = max_drawdown = 0
                calmar_ratio = var_95 = recovery_time = 0
        else:
            volatility = sharpe_ratio = sortino_ratio = max_drawdown = 0
            calmar_ratio = var_95 = recovery_time = 0
            
        # Score de estrés compuesto
        stress_score = self._calculate_stress_score({
            'daily_return': daily_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'volatility': volatility
        }, scenario.severity)
        
        return {
            'total_return': total_return,
            'daily_return': daily_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'var_95': var_95,
            'trades_count': trades_count,
            'volatility': volatility,
            'calmar_ratio': calmar_ratio,
            'recovery_time': recovery_time,
            'stress_score': stress_score
        }
        
    def _get_default_metrics(self) -> Dict:
        """Métricas por defecto para casos de error"""
        return {
            'total_return': 0,
            'daily_return': 0,
            'max_drawdown': 1.0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'var_95': 0,
            'trades_count': 0,
            'volatility': 0,
            'calmar_ratio': 0,
            'recovery_time': 999,
            'stress_score': 0
        }
        
    def _calculate_recovery_time(self, drawdown_series: pd.Series) -> float:
        """Calcular tiempo promedio de recuperación de drawdowns"""
        
        if len(drawdown_series) == 0:
            return 0
            
        # Encontrar períodos de drawdown
        in_drawdown = drawdown_series < -0.01  # Drawdown > 1%
        
        if not in_drawdown.any():
            return 0
            
        # Calcular duraciones de drawdown
        drawdown_periods = []
        current_period = 0
        
        for is_dd in in_drawdown:
            if is_dd:
                current_period += 1
            else:
                if current_period > 0:
                    drawdown_periods.append(current_period)
                    current_period = 0
                    
        if current_period > 0:
            drawdown_periods.append(current_period)
            
        return np.mean(drawdown_periods) if drawdown_periods else 0
        
    def _calculate_stress_score(self, metrics: Dict, severity: float) -> float:
        """Calcular score compuesto de resistencia al estrés"""
        
        # Normalizar métricas (0-1, donde 1 es mejor)
        return_score = max(0, min(1, (metrics['daily_return'] - (-0.01)) / (self.target_daily_return + 0.01)))
        drawdown_score = max(0, 1 - metrics['max_drawdown'] / self.max_acceptable_drawdown)
        risk_score = max(0, min(1, metrics['sharpe_ratio'] / self.min_sharpe_ratio))
        consistency_score = metrics['win_rate']
        
        # Score ponderado
        weighted_score = (
            self.stress_weights['return_stability'] * return_score +
            self.stress_weights['drawdown_control'] * drawdown_score +
            self.stress_weights['risk_management'] * risk_score +
            self.stress_weights['consistency'] * consistency_score
        )
        
        # Ajustar por severidad del escenario
        severity_adjustment = 1 - (severity * 0.3)  # Escenarios más severos son más difíciles
        
        return weighted_score * severity_adjustment
        
    def _evaluate_pass_criteria(self, metrics: Dict) -> bool:
        """Evaluar si las métricas cumplen los criterios mínimos"""
        
        criteria_met = [
            metrics['daily_return'] >= self.pass_criteria['min_daily_return'],
            metrics['max_drawdown'] <= self.pass_criteria['max_drawdown'],
            metrics['sharpe_ratio'] >= self.pass_criteria['min_sharpe'],
            metrics['win_rate'] >= self.pass_criteria['min_win_rate'],
            metrics['profit_factor'] >= self.pass_criteria['min_profit_factor'],
            metrics['var_95'] >= self.pass_criteria['max_var_95']
        ]
        
        # Debe cumplir al menos 4 de 6 criterios
        return sum(criteria_met) >= 4
        
    def run_comprehensive_stress_test(self, strategy_func: Callable, data: pd.DataFrame,
                                    params: Dict) -> StressTestSuite:
        """Ejecutar suite completa de pruebas de estrés"""
        
        self.logger.info("Iniciando suite completa de pruebas de estrés...")
        
        scenarios = self.create_stress_scenarios()
        results = []
        
        for scenario in scenarios:
            result = self.run_stress_test(strategy_func, data, params, scenario)
            results.append(result)
            
            self.logger.info(f"{scenario.name}: {'PASÓ' if result.passed else 'FALLÓ'} "
                           f"(Score: {result.stress_score:.3f})")
            
        # Análisis general
        overall_analysis = self._analyze_overall_performance(results)
        
        return StressTestSuite(
            results=results,
            overall_score=overall_analysis['overall_score'],
            robustness_rating=overall_analysis['robustness_rating'],
            critical_failures=overall_analysis['critical_failures'],
            recommendations=overall_analysis['recommendations'],
            risk_assessment=overall_analysis['risk_assessment']
        )
        
    def _analyze_overall_performance(self, results: List[StressTestResult]) -> Dict:
        """Analizar rendimiento general de todas las pruebas"""
        
        # Estadísticas básicas
        passed_tests = [r for r in results if r.passed]
        failed_tests = [r for r in results if not r.passed]
        
        pass_rate = len(passed_tests) / len(results) if results else 0
        avg_stress_score = np.mean([r.stress_score for r in results]) if results else 0
        
        # Score general ponderado por severidad
        severity_weights = {
            MarketRegime.CRISIS: 0.25,
            MarketRegime.BEAR: 0.20,
            MarketRegime.HIGH_VOLATILITY: 0.15,
            MarketRegime.RECOVERY: 0.15,
            MarketRegime.SIDEWAYS: 0.10,
            MarketRegime.RANGING: 0.05,
            MarketRegime.BULL: 0.05,
            MarketRegime.TRENDING: 0.03,
            MarketRegime.LOW_VOLATILITY: 0.02
        }
        
        weighted_score = 0
        for result in results:
            weight = severity_weights.get(result.regime, 0.1)
            weighted_score += result.stress_score * weight
            
        # Rating de robustez
        if weighted_score >= 0.8 and pass_rate >= 0.8:
            robustness_rating = "Excelente"
        elif weighted_score >= 0.6 and pass_rate >= 0.6:
            robustness_rating = "Bueno"
        elif weighted_score >= 0.4 and pass_rate >= 0.4:
            robustness_rating = "Regular"
        else:
            robustness_rating = "Malo"
            
        # Identificar fallas críticas
        critical_failures = []
        for result in failed_tests:
            if result.regime in [MarketRegime.CRISIS, MarketRegime.BEAR, MarketRegime.HIGH_VOLATILITY]:
                critical_failures.append(f"Falla crítica en {result.scenario_name}")
                
        # Generar recomendaciones
        recommendations = self._generate_recommendations(results, pass_rate, weighted_score)
        
        # Evaluación de riesgos
        risk_assessment = self._assess_risks(results)
        
        return {
            'overall_score': weighted_score,
            'robustness_rating': robustness_rating,
            'critical_failures': critical_failures,
            'recommendations': recommendations,
            'risk_assessment': risk_assessment,
            'pass_rate': pass_rate,
            'avg_stress_score': avg_stress_score
        }
        
    def _generate_recommendations(self, results: List[StressTestResult], 
                                pass_rate: float, weighted_score: float) -> List[str]:
        """Generar recomendaciones basadas en resultados"""
        
        recommendations = []
        
        # Análisis por tipo de falla
        failed_by_regime = {}
        for result in results:
            if not result.passed:
                regime = result.regime
                if regime not in failed_by_regime:
                    failed_by_regime[regime] = []
                failed_by_regime[regime].append(result)
                
        # Recomendaciones específicas
        if MarketRegime.CRISIS in failed_by_regime:
            recommendations.append("Mejorar gestión de riesgo para crisis financieras")
            recommendations.append("Implementar circuit breakers más agresivos")
            
        if MarketRegime.BEAR in failed_by_regime:
            recommendations.append("Optimizar estrategia para mercados bajistas")
            recommendations.append("Considerar estrategias de cobertura")
            
        if MarketRegime.HIGH_VOLATILITY in failed_by_regime:
            recommendations.append("Ajustar parámetros para alta volatilidad")
            recommendations.append("Implementar filtros de volatilidad más estrictos")
            
        if MarketRegime.SIDEWAYS in failed_by_regime:
            recommendations.append("Mejorar detección de mercados laterales")
            recommendations.append("Implementar filtros anti-whipsaw")
            
        # Recomendaciones generales
        if pass_rate < 0.6:
            recommendations.append("Revisar completamente los parámetros de la estrategia")
            recommendations.append("Considerar estrategias más conservadoras")
            
        if weighted_score < 0.5:
            recommendations.append("Implementar gestión de riesgo más estricta")
            recommendations.append("Reducir tamaño de posición en condiciones adversas")
            
        return recommendations
        
    def _assess_risks(self, results: List[StressTestResult]) -> Dict[str, Any]:
        """Evaluar riesgos basados en resultados de estrés"""
        
        # Métricas de riesgo agregadas
        max_drawdowns = [r.max_drawdown for r in results]
        daily_returns = [r.daily_return for r in results]
        var_95_values = [r.var_95 for r in results]
        
        risk_assessment = {
            'worst_case_drawdown': max(max_drawdowns) if max_drawdowns else 0,
            'worst_case_daily_return': min(daily_returns) if daily_returns else 0,
            'worst_case_var': min(var_95_values) if var_95_values else 0,
            'drawdown_volatility': np.std(max_drawdowns) if max_drawdowns else 0,
            'return_volatility': np.std(daily_returns) if daily_returns else 0,
            'tail_risk_score': 0,
            'regime_sensitivity': {},
            'overall_risk_level': 'Bajo'
        }
        
        # Análisis de sensibilidad por régimen
        for regime in MarketRegime:
            regime_results = [r for r in results if r.regime == regime]
            if regime_results:
                avg_score = np.mean([r.stress_score for r in regime_results])
                risk_assessment['regime_sensitivity'][regime.value] = avg_score
                
        # Score de riesgo de cola
        tail_events = [r for r in results if r.max_drawdown > 0.2 or r.daily_return < -0.01]
        risk_assessment['tail_risk_score'] = len(tail_events) / len(results) if results else 0
        
        # Nivel de riesgo general
        if risk_assessment['worst_case_drawdown'] > 0.3 or risk_assessment['tail_risk_score'] > 0.3:
            risk_assessment['overall_risk_level'] = 'Alto'
        elif risk_assessment['worst_case_drawdown'] > 0.2 or risk_assessment['tail_risk_score'] > 0.2:
            risk_assessment['overall_risk_level'] = 'Medio'
        else:
            risk_assessment['overall_risk_level'] = 'Bajo'
            
        return risk_assessment
        
    def generate_stress_report(self, suite: StressTestSuite) -> str:
        """Generar reporte detallado de pruebas de estrés"""
        
        report = []
        report.append("=" * 80)
        report.append("REPORTE DE PRUEBAS DE ESTRÉS - ESTRATEGIA BINANCE SPOT")
        report.append("=" * 80)
        report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Objetivo: {self.target_daily_return:.2%} retorno diario")
        report.append("")
        
        # Resumen ejecutivo
        report.append("RESUMEN EJECUTIVO")
        report.append("-" * 40)
        report.append(f"Score General: {suite.overall_score:.3f}/1.000")
        report.append(f"Rating de Robustez: {suite.robustness_rating}")
        report.append(f"Pruebas Pasadas: {len([r for r in suite.results if r.passed])}/{len(suite.results)}")
        report.append(f"Nivel de Riesgo: {suite.risk_assessment['overall_risk_level']}")
        report.append("")
        
        # Resultados por escenario
        report.append("RESULTADOS POR ESCENARIO")
        report.append("-" * 40)
        
        for result in suite.results:
            status = "✓ PASÓ" if result.passed else "✗ FALLÓ"
            report.append(f"{result.scenario_name:30} {status:8} Score: {result.stress_score:.3f}")
            report.append(f"  Retorno Diario: {result.daily_return:.3%:>8} Drawdown: {result.max_drawdown:.1%:>6} Sharpe: {result.sharpe_ratio:.2f:>6}")
            
        report.append("")
        
        # Fallas críticas
        if suite.critical_failures:
            report.append("FALLAS CRÍTICAS")
            report.append("-" * 40)
            for failure in suite.critical_failures:
                report.append(f"• {failure}")
            report.append("")
            
        # Evaluación de riesgos
        report.append("EVALUACIÓN DE RIESGOS")
        report.append("-" * 40)
        report.append(f"Peor Drawdown: {suite.risk_assessment['worst_case_drawdown']:.1%}")
        report.append(f"Peor Retorno Diario: {suite.risk_assessment['worst_case_daily_return']:.3%}")
        report.append(f"Riesgo de Cola: {suite.risk_assessment['tail_risk_score']:.1%}")
        report.append("")
        
        # Recomendaciones
        if suite.recommendations:
            report.append("RECOMENDACIONES")
            report.append("-" * 40)
            for i, rec in enumerate(suite.recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")
            
        # Conclusión
        report.append("CONCLUSIÓN")
        report.append("-" * 40)
        
        if suite.overall_score >= 0.7:
            report.append("La estrategia muestra BUENA robustez bajo condiciones de estrés.")
            report.append("Recomendada para implementación con monitoreo continuo.")
        elif suite.overall_score >= 0.5:
            report.append("La estrategia muestra robustez MODERADA bajo condiciones de estrés.")
            report.append("Requiere optimización antes de implementación en vivo.")
        else:
            report.append("La estrategia muestra BAJA robustez bajo condiciones de estrés.")
            report.append("NO recomendada para implementación sin mejoras significativas.")
            
        report.append("=" * 80)
        
        return "\n".join(report)
        
if __name__ == "__main__":
    # Ejemplo de uso
    stress_tester = StressTester(target_daily_return=0.006)
    
    # Generar datos de prueba
    dates = pd.date_range('2024-01-01', '2024-06-30', freq='H')
    test_data = pd.DataFrame({
        'open': np.random.normal(50000, 1000, len(dates)),
        'high': np.random.normal(51000, 1000, len(dates)),
        'low': np.random.normal(49000, 1000, len(dates)),
        'close': np.random.normal(50000, 1000, len(dates)),
        'volume': np.random.normal(1000, 200, len(dates))
    }, index=dates)
    
    # Función de estrategia de prueba
    def test_strategy(data, params):
        trades = []
        for i in range(20):
            trades.append({
                'pnl': np.random.normal(3, 15),
                'entry_time': datetime.now(),
                'exit_time': datetime.now() + timedelta(hours=2)
            })
        
        equity_curve = [500 + i * 1.5 for i in range(len(data))]
        
        return {
            'trades': trades,
            'equity_curve': equity_curve
        }
    
    # Ejecutar pruebas de estrés
    test_params = {'rsi_period': 14, 'stop_loss': 0.02}
    
    suite = stress_tester.run_comprehensive_stress_test(
        test_strategy, test_data, test_params
    )
    
    # Generar reporte
    report = stress_tester.generate_stress_report(suite)
    print(report)