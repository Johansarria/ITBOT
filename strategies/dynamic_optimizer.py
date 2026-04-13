# strategies/dynamic_optimizer.py

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import asyncio
from collections import deque, defaultdict
import json
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Regímenes de mercado"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    BREAKOUT = "breakout"
    REVERSAL = "reversal"

class OptimizationStatus(Enum):
    """Estados de optimización"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    OPTIMIZING = "optimizing"
    APPLYING = "applying"
    ERROR = "error"

@dataclass
class MarketCondition:
    """Condiciones actuales del mercado"""
    regime: MarketRegime
    volatility: float
    trend_strength: float
    volume_profile: float
    correlation_level: float
    momentum: float
    support_resistance_strength: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ParameterSet:
    """Conjunto de parámetros optimizados"""
    # RSI
    rsi_fast: int = 14
    rsi_slow: int = 21
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    macd_threshold_bull: float = 0.1
    macd_threshold_bear: float = -0.1
    
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    bb_squeeze_threshold: float = 2.0
    
    # EMAs
    ema_fast: int = 9
    ema_slow: int = 21
    ema_trend: int = 50
    
    # Pesos de indicadores
    weight_rsi: float = 2.5
    weight_macd: float = 2.0
    weight_bb: float = 1.8
    weight_ema: float = 1.5
    weight_momentum: float = 1.2
    weight_volume: float = 1.0
    
    # Umbrales de señal
    signal_strong: float = 6.0
    signal_medium: float = 4.0
    signal_weak: float = 2.0
    
    # Gestión de riesgo
    stop_loss_pct: float = 0.02
    take_profit_ratio: float = 2.0
    position_size_multiplier: float = 1.0
    
    # Metadatos
    regime: Optional[MarketRegime] = None
    performance_score: float = 0.0
    win_rate: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class OptimizationResult:
    """Resultado de optimización"""
    symbol: str
    timeframe: str
    old_params: ParameterSet
    new_params: ParameterSet
    improvement_score: float
    confidence: float
    backtest_results: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)

class DynamicOptimizer:
    """Optimizador dinámico de parámetros en tiempo real"""
    
    def __init__(self, target_monthly_return: float = 0.20):
        self.target_monthly_return = target_monthly_return
        self.status = OptimizationStatus.IDLE
        
        # Parámetros por símbolo y régimen
        self.parameter_sets: Dict[str, Dict[MarketRegime, ParameterSet]] = defaultdict(lambda: defaultdict(ParameterSet))
        self.current_parameters: Dict[str, ParameterSet] = {}
        
        # Detección de régimen de mercado
        self.market_conditions: Dict[str, MarketCondition] = {}
        self.price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self.volume_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        
        # Métricas de rendimiento
        self.performance_history: Dict[str, List[Dict]] = defaultdict(list)
        self.optimization_history: List[OptimizationResult] = []
        
        # Configuración de optimización
        self.optimization_interval = timedelta(hours=6)  # Optimizar cada 6 horas
        self.min_data_points = 100  # Mínimo de datos para optimizar
        self.confidence_threshold = 0.7  # Confianza mínima para aplicar cambios
        
        # Rangos de optimización
        self.optimization_ranges = {
            'rsi_fast': (7, 21),
            'rsi_slow': (14, 35),
            'rsi_oversold': (20, 35),
            'rsi_overbought': (65, 80),
            'macd_fast': (8, 16),
            'macd_slow': (20, 35),
            'macd_signal': (6, 12),
            'bb_period': (15, 30),
            'bb_std': (1.5, 2.5),
            'ema_fast': (5, 15),
            'ema_slow': (15, 30),
            'stop_loss_pct': (0.01, 0.05),
            'take_profit_ratio': (1.5, 3.0)
        }
        
        # Cache de optimización
        self.optimization_cache: Dict[str, Dict] = {}
        self.last_optimization: Dict[str, datetime] = {}
        
        # Executor para optimizaciones paralelas
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info("Dynamic Optimizer inicializado")
    
    def update_market_data(self, symbol: str, price: float, volume: float, timestamp: datetime = None):
        """Actualiza datos de mercado para análisis"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.price_history[symbol].append((timestamp, price))
        self.volume_history[symbol].append((timestamp, volume))
        
        # Actualizar condiciones de mercado
        self._update_market_conditions(symbol)
    
    def _update_market_conditions(self, symbol: str):
        """Actualiza las condiciones de mercado para un símbolo"""
        if len(self.price_history[symbol]) < 50:
            return
        
        prices = [p[1] for p in list(self.price_history[symbol])[-50:]]
        volumes = [v[1] for v in list(self.volume_history[symbol])[-50:]]
        
        # Calcular métricas
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # Anualizada
        
        # Tendencia (regresión lineal simple)
        x = np.arange(len(prices))
        trend_slope = np.polyfit(x, prices, 1)[0]
        trend_strength = abs(trend_slope) / np.mean(prices)
        
        # Momentum
        momentum = (prices[-1] - prices[-10]) / prices[-10] if len(prices) >= 10 else 0
        
        # Perfil de volumen
        volume_ma = np.mean(volumes)
        volume_profile = volumes[-1] / volume_ma if volume_ma > 0 else 1.0
        
        # Soporte/Resistencia (simplificado)
        price_levels = np.array(prices)
        support_resistance = self._calculate_support_resistance_strength(price_levels)
        
        # Determinar régimen
        regime = self._determine_market_regime(trend_slope, volatility, momentum, trend_strength)
        
        # Crear condición de mercado
        condition = MarketCondition(
            regime=regime,
            volatility=volatility,
            trend_strength=trend_strength,
            volume_profile=volume_profile,
            correlation_level=0.0,  # Se calculará con otros símbolos
            momentum=momentum,
            support_resistance_strength=support_resistance
        )
        
        self.market_conditions[symbol] = condition
        
        # Verificar si necesita optimización
        self._check_optimization_trigger(symbol)
    
    def _calculate_support_resistance_strength(self, prices: np.ndarray) -> float:
        """Calcula la fuerza de soporte/resistencia"""
        if len(prices) < 20:
            return 0.0
        
        # Encontrar niveles de precio frecuentes
        price_bins = np.histogram(prices, bins=10)[0]
        max_frequency = np.max(price_bins)
        total_points = len(prices)
        
        return max_frequency / total_points
    
    def _determine_market_regime(self, trend_slope: float, volatility: float, 
                               momentum: float, trend_strength: float) -> MarketRegime:
        """Determina el régimen de mercado actual"""
        
        # Volatilidad alta/baja
        if volatility > 0.4:
            return MarketRegime.HIGH_VOLATILITY
        elif volatility < 0.1:
            return MarketRegime.LOW_VOLATILITY
        
        # Tendencias
        if trend_strength > 0.02:
            if trend_slope > 0:
                return MarketRegime.TRENDING_UP
            else:
                return MarketRegime.TRENDING_DOWN
        
        # Momentum extremo (breakout/reversal)
        if abs(momentum) > 0.05:
            if momentum > 0:
                return MarketRegime.BREAKOUT
            else:
                return MarketRegime.REVERSAL
        
        # Por defecto: lateral
        return MarketRegime.SIDEWAYS
    
    def _check_optimization_trigger(self, symbol: str):
        """Verifica si se debe activar optimización"""
        
        # Verificar tiempo desde última optimización
        last_opt = self.last_optimization.get(symbol)
        if last_opt and datetime.now() - last_opt < self.optimization_interval:
            return
        
        # Verificar datos suficientes
        if len(self.price_history[symbol]) < self.min_data_points:
            return
        
        # Verificar cambio de régimen
        current_regime = self.market_conditions[symbol].regime
        current_params = self.current_parameters.get(symbol)
        
        if current_params and current_params.regime != current_regime:
            logger.info(f"Cambio de régimen detectado para {symbol}: {current_params.regime} -> {current_regime}")
            self._trigger_optimization(symbol)
        
        # Verificar rendimiento bajo
        if self._is_underperforming(symbol):
            logger.info(f"Rendimiento bajo detectado para {symbol}, activando optimización")
            self._trigger_optimization(symbol)
    
    def _is_underperforming(self, symbol: str) -> bool:
        """Verifica si el símbolo está teniendo bajo rendimiento"""
        if symbol not in self.performance_history or len(self.performance_history[symbol]) < 10:
            return False
        
        recent_performance = self.performance_history[symbol][-10:]
        avg_return = np.mean([p.get('return', 0) for p in recent_performance])
        win_rate = np.mean([1 if p.get('return', 0) > 0 else 0 for p in recent_performance])
        
        # Criterios de bajo rendimiento
        return avg_return < -0.01 or win_rate < 0.4
    
    def _trigger_optimization(self, symbol: str):
        """Activa proceso de optimización para un símbolo"""
        if self.status != OptimizationStatus.IDLE:
            logger.warning(f"Optimización ya en progreso, saltando {symbol}")
            return
        
        logger.info(f"Iniciando optimización para {symbol}")
        
        # Ejecutar optimización en background
        future = self.executor.submit(self._optimize_parameters, symbol)
        
        # Callback para aplicar resultados
        future.add_done_callback(lambda f: self._apply_optimization_result(f.result()))
    
    def _optimize_parameters(self, symbol: str) -> OptimizationResult:
        """Optimiza parámetros para un símbolo específico"""
        self.status = OptimizationStatus.OPTIMIZING
        
        try:
            current_condition = self.market_conditions[symbol]
            current_params = self.current_parameters.get(symbol, ParameterSet())
            
            # Obtener datos históricos
            prices = [p[1] for p in list(self.price_history[symbol])]
            volumes = [v[1] for v in list(self.volume_history[symbol])]
            
            # Generar candidatos de parámetros
            candidates = self._generate_parameter_candidates(current_params, current_condition.regime)
            
            # Evaluar cada candidato
            best_params = current_params
            best_score = -float('inf')
            best_results = {}
            
            for candidate in candidates:
                # Backtest rápido
                results = self._quick_backtest(symbol, candidate, prices, volumes)
                score = self._calculate_optimization_score(results)
                
                if score > best_score:
                    best_score = score
                    best_params = candidate
                    best_results = results
            
            # Calcular mejora y confianza
            current_score = self._calculate_optimization_score(
                self._quick_backtest(symbol, current_params, prices, volumes)
            )
            
            improvement = best_score - current_score
            confidence = min(improvement / abs(current_score) if current_score != 0 else 1.0, 1.0)
            
            # Actualizar parámetros optimizados
            best_params.regime = current_condition.regime
            best_params.performance_score = best_score
            best_params.last_updated = datetime.now()
            
            result = OptimizationResult(
                symbol=symbol,
                timeframe="5m",  # Por defecto
                old_params=current_params,
                new_params=best_params,
                improvement_score=improvement,
                confidence=confidence,
                backtest_results=best_results
            )
            
            logger.info(f"Optimización completada para {symbol}: mejora={improvement:.4f}, confianza={confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error en optimización de {symbol}: {e}")
            self.status = OptimizationStatus.ERROR
            raise
        
        finally:
            self.status = OptimizationStatus.IDLE
    
    def _generate_parameter_candidates(self, base_params: ParameterSet, regime: MarketRegime) -> List[ParameterSet]:
        """Genera candidatos de parámetros para optimización"""
        candidates = []
        
        # Parámetros base adaptados al régimen
        regime_adjustments = self._get_regime_adjustments(regime)
        
        # Generar variaciones
        for i in range(20):  # 20 candidatos
            candidate = ParameterSet()
            
            # Aplicar ajustes de régimen
            for param, adjustment in regime_adjustments.items():
                base_value = getattr(base_params, param, getattr(candidate, param))
                if param in self.optimization_ranges:
                    min_val, max_val = self.optimization_ranges[param]
                    adjusted_value = base_value * adjustment
                    # Mantener en rango válido
                    adjusted_value = max(min_val, min(max_val, adjusted_value))
                    setattr(candidate, param, adjusted_value)
            
            # Añadir variación aleatoria pequeña
            for param in ['rsi_fast', 'rsi_slow', 'macd_fast', 'macd_slow', 'bb_period']:
                if hasattr(candidate, param):
                    current_val = getattr(candidate, param)
                    variation = np.random.normal(0, 0.1) * current_val
                    min_val, max_val = self.optimization_ranges.get(param, (current_val * 0.5, current_val * 1.5))
                    new_val = max(min_val, min(max_val, current_val + variation))
                    setattr(candidate, param, int(new_val) if param.endswith(('_fast', '_slow', '_period')) else new_val)
            
            candidates.append(candidate)
        
        return candidates
    
    def _get_regime_adjustments(self, regime: MarketRegime) -> Dict[str, float]:
        """Obtiene ajustes de parámetros según régimen de mercado"""
        adjustments = {
            MarketRegime.TRENDING_UP: {
                'rsi_oversold': 0.8,  # Más conservador
                'rsi_overbought': 1.1,  # Menos conservador
                'macd_threshold_bull': 0.8,  # Más sensible
                'weight_ema': 1.2,  # Más peso a tendencia
                'stop_loss_pct': 1.2,  # Stop más amplio
                'take_profit_ratio': 1.3  # TP más ambicioso
            },
            MarketRegime.TRENDING_DOWN: {
                'rsi_oversold': 1.2,  # Menos conservador
                'rsi_overbought': 0.8,  # Más conservador
                'macd_threshold_bear': 0.8,  # Más sensible
                'weight_rsi': 1.3,  # Más peso a RSI
                'stop_loss_pct': 0.8,  # Stop más ajustado
                'position_size_multiplier': 0.7  # Posiciones más pequeñas
            },
            MarketRegime.SIDEWAYS: {
                'rsi_oversold': 0.9,  # Más neutral
                'rsi_overbought': 0.9,
                'bb_std': 0.9,  # Bandas más ajustadas
                'weight_bb': 1.3,  # Más peso a BB
                'take_profit_ratio': 0.8,  # TP más conservador
                'signal_strong': 1.1  # Umbral más alto
            },
            MarketRegime.HIGH_VOLATILITY: {
                'rsi_fast': 0.8,  # RSI más rápido
                'bb_std': 1.2,  # Bandas más amplias
                'stop_loss_pct': 1.5,  # Stop más amplio
                'position_size_multiplier': 0.6,  # Posiciones más pequeñas
                'signal_strong': 1.2  # Umbral más alto
            },
            MarketRegime.LOW_VOLATILITY: {
                'rsi_slow': 1.2,  # RSI más lento
                'bb_std': 0.8,  # Bandas más ajustadas
                'stop_loss_pct': 0.8,  # Stop más ajustado
                'position_size_multiplier': 1.2,  # Posiciones más grandes
                'signal_weak': 0.8  # Umbral más bajo
            },
            MarketRegime.BREAKOUT: {
                'macd_fast': 0.8,  # MACD más rápido
                'weight_momentum': 1.5,  # Más peso a momentum
                'take_profit_ratio': 1.5,  # TP más ambicioso
                'signal_medium': 0.9  # Umbral más bajo
            },
            MarketRegime.REVERSAL: {
                'rsi_fast': 1.2,  # RSI más lento
                'weight_rsi': 1.4,  # Más peso a RSI
                'stop_loss_pct': 0.7,  # Stop más ajustado
                'position_size_multiplier': 0.8  # Posiciones más pequeñas
            }
        }
        
        return adjustments.get(regime, {})
    
    def _quick_backtest(self, symbol: str, params: ParameterSet, prices: List[float], volumes: List[float]) -> Dict[str, float]:
        """Backtest rápido para evaluar parámetros"""
        if len(prices) < 50:
            return {'return': 0, 'win_rate': 0, 'sharpe': 0, 'max_dd': 0, 'trades': 0}
        
        # Simular señales con los parámetros
        signals = self._generate_signals_with_params(prices, volumes, params)
        
        # Simular trades
        trades = []
        position = None
        
        for i, signal in enumerate(signals):
            if signal == 'BUY' and position is None:
                position = {'entry': prices[i], 'entry_idx': i}
            elif signal == 'SELL' and position is not None:
                exit_price = prices[i]
                pnl_pct = (exit_price - position['entry']) / position['entry']
                trades.append({
                    'entry': position['entry'],
                    'exit': exit_price,
                    'pnl_pct': pnl_pct,
                    'duration': i - position['entry_idx']
                })
                position = None
        
        # Cerrar posición abierta
        if position is not None:
            exit_price = prices[-1]
            pnl_pct = (exit_price - position['entry']) / position['entry']
            trades.append({
                'entry': position['entry'],
                'exit': exit_price,
                'pnl_pct': pnl_pct,
                'duration': len(prices) - 1 - position['entry_idx']
            })
        
        if not trades:
            return {'return': 0, 'win_rate': 0, 'sharpe': 0, 'max_dd': 0, 'trades': 0}
        
        # Calcular métricas
        returns = [t['pnl_pct'] for t in trades]
        total_return = np.prod([1 + r for r in returns]) - 1
        win_rate = len([r for r in returns if r > 0]) / len(returns)
        
        # Sharpe simplificado
        if len(returns) > 1:
            sharpe = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe = 0
        
        # Max drawdown simplificado
        cumulative = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0
        
        return {
            'return': total_return,
            'win_rate': win_rate,
            'sharpe': sharpe,
            'max_dd': max_dd,
            'trades': len(trades)
        }
    
    def _generate_signals_with_params(self, prices: List[float], volumes: List[float], params: ParameterSet) -> List[str]:
        """Genera señales usando parámetros específicos"""
        signals = ['HOLD'] * len(prices)
        
        if len(prices) < max(params.rsi_slow, params.macd_slow, params.bb_period) + 10:
            return signals
        
        # Calcular indicadores con parámetros
        rsi_values = self._calculate_rsi_with_params(prices, params.rsi_fast)
        macd_values = self._calculate_macd_with_params(prices, params.macd_fast, params.macd_slow, params.macd_signal)
        bb_values = self._calculate_bb_with_params(prices, params.bb_period, params.bb_std)
        
        # Generar señales
        for i in range(len(prices)):
            if i < 50:  # Necesitamos datos suficientes
                continue
            
            score = 0
            
            # RSI
            if i < len(rsi_values) and rsi_values[i] is not None:
                if rsi_values[i] < params.rsi_oversold:
                    score += params.weight_rsi
                elif rsi_values[i] > params.rsi_overbought:
                    score -= params.weight_rsi
            
            # MACD
            if i < len(macd_values) and macd_values[i] is not None:
                if macd_values[i] > params.macd_threshold_bull:
                    score += params.weight_macd
                elif macd_values[i] < params.macd_threshold_bear:
                    score -= params.weight_macd
            
            # Bollinger Bands
            if i < len(bb_values) and bb_values[i] is not None:
                bb_pos = bb_values[i]
                if bb_pos < 0.2:
                    score += params.weight_bb
                elif bb_pos > 0.8:
                    score -= params.weight_bb
            
            # Determinar señal
            if score >= params.signal_strong:
                signals[i] = 'BUY'
            elif score <= -params.signal_strong:
                signals[i] = 'SELL'
        
        return signals
    
    def _calculate_rsi_with_params(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calcula RSI con parámetros específicos"""
        rsi_values = [None] * len(prices)
        
        if len(prices) < period + 1:
            return rsi_values
        
        deltas = np.diff(prices)
        
        for i in range(period, len(prices)):
            gains = np.where(deltas[i-period:i] > 0, deltas[i-period:i], 0)
            losses = np.where(deltas[i-period:i] < 0, -deltas[i-period:i], 0)
            
            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)
            
            if avg_loss == 0:
                rsi_values[i] = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_values[i] = 100 - (100 / (1 + rs))
        
        return rsi_values
    
    def _calculate_macd_with_params(self, prices: List[float], fast: int, slow: int, signal: int) -> List[Optional[float]]:
        """Calcula MACD con parámetros específicos"""
        macd_values = [None] * len(prices)
        
        if len(prices) < slow + signal:
            return macd_values
        
        # EMAs
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        # MACD line
        macd_line = []
        for i in range(len(ema_fast)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line.append(ema_fast[i] - ema_slow[i])
            else:
                macd_line.append(None)
        
        return macd_line
    
    def _calculate_bb_with_params(self, prices: List[float], period: int, std_dev: float) -> List[Optional[float]]:
        """Calcula posición en Bollinger Bands"""
        bb_positions = [None] * len(prices)
        
        for i in range(period, len(prices)):
            window = prices[i-period:i]
            sma = np.mean(window)
            std = np.std(window)
            
            upper = sma + (std_dev * std)
            lower = sma - (std_dev * std)
            
            if upper != lower:
                bb_positions[i] = (prices[i] - lower) / (upper - lower)
            else:
                bb_positions[i] = 0.5
        
        return bb_positions
    
    def _calculate_ema(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calcula EMA"""
        ema_values = [None] * len(prices)
        
        if len(prices) < period:
            return ema_values
        
        alpha = 2 / (period + 1)
        ema = prices[period-1]  # Primer valor
        ema_values[period-1] = ema
        
        for i in range(period, len(prices)):
            ema = alpha * prices[i] + (1 - alpha) * ema
            ema_values[i] = ema
        
        return ema_values
    
    def _calculate_optimization_score(self, results: Dict[str, float]) -> float:
        """Calcula puntuación de optimización"""
        # Pesos para diferentes métricas
        weights = {
            'return': 0.4,
            'win_rate': 0.2,
            'sharpe': 0.2,
            'max_dd': -0.1,  # Penalizar drawdown alto
            'trades': 0.1
        }
        
        score = 0
        for metric, weight in weights.items():
            value = results.get(metric, 0)
            
            # Normalizar métricas
            if metric == 'return':
                normalized = min(value * 10, 1)  # Cap at 10% return
            elif metric == 'win_rate':
                normalized = value
            elif metric == 'sharpe':
                normalized = min(value / 2, 1)  # Cap at Sharpe 2
            elif metric == 'max_dd':
                normalized = value  # Ya es negativo
            elif metric == 'trades':
                normalized = min(value / 20, 1)  # Cap at 20 trades
            else:
                normalized = value
            
            score += weight * normalized
        
        return score
    
    def _apply_optimization_result(self, result: OptimizationResult):
        """Aplica resultado de optimización si cumple criterios"""
        if result.confidence >= self.confidence_threshold and result.improvement_score > 0:
            logger.info(f"Aplicando nuevos parámetros para {result.symbol}")
            
            # Actualizar parámetros actuales
            self.current_parameters[result.symbol] = result.new_params
            
            # Guardar en conjunto de parámetros por régimen
            regime = result.new_params.regime
            if regime:
                self.parameter_sets[result.symbol][regime] = result.new_params
            
            # Actualizar timestamp de optimización
            self.last_optimization[result.symbol] = datetime.now()
            
            # Guardar historial
            self.optimization_history.append(result)
            
            # Guardar en cache
            self._save_optimization_cache()
            
        else:
            logger.info(f"Optimización para {result.symbol} no aplicada: confianza={result.confidence:.2f}, mejora={result.improvement_score:.4f}")
    
    def get_current_parameters(self, symbol: str) -> ParameterSet:
        """Obtiene parámetros actuales para un símbolo"""
        # Verificar si hay parámetros específicos para el régimen actual
        if symbol in self.market_conditions:
            current_regime = self.market_conditions[symbol].regime
            if symbol in self.parameter_sets and current_regime in self.parameter_sets[symbol]:
                return self.parameter_sets[symbol][current_regime]
        
        # Usar parámetros actuales o por defecto
        return self.current_parameters.get(symbol, ParameterSet())
    
    def force_optimization(self, symbol: str) -> bool:
        """Fuerza optimización inmediata para un símbolo"""
        if self.status != OptimizationStatus.IDLE:
            return False
        
        logger.info(f"Optimización forzada para {symbol}")
        self._trigger_optimization(symbol)
        return True
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Resumen del estado de optimización"""
        return {
            'status': self.status.value,
            'symbols_tracked': list(self.market_conditions.keys()),
            'market_conditions': {
                symbol: {
                    'regime': condition.regime.value,
                    'volatility': condition.volatility,
                    'trend_strength': condition.trend_strength,
                    'momentum': condition.momentum
                }
                for symbol, condition in self.market_conditions.items()
            },
            'last_optimizations': {
                symbol: timestamp.isoformat()
                for symbol, timestamp in self.last_optimization.items()
            },
            'optimization_history_count': len(self.optimization_history),
            'recent_improvements': [
                {
                    'symbol': opt.symbol,
                    'improvement': opt.improvement_score,
                    'confidence': opt.confidence,
                    'timestamp': opt.timestamp.isoformat()
                }
                for opt in self.optimization_history[-5:]  # Últimas 5
            ]
        }
    
    def _save_optimization_cache(self):
        """Guarda cache de optimización"""
        try:
            cache_data = {
                'parameter_sets': {
                    symbol: {
                        regime.value: {
                            'rsi_fast': params.rsi_fast,
                            'rsi_slow': params.rsi_slow,
                            'rsi_oversold': params.rsi_oversold,
                            'rsi_overbought': params.rsi_overbought,
                            'macd_fast': params.macd_fast,
                            'macd_slow': params.macd_slow,
                            'macd_signal': params.macd_signal,
                            'bb_period': params.bb_period,
                            'bb_std': params.bb_std,
                            'performance_score': params.performance_score,
                            'created_at': params.created_at.isoformat(),
                            'last_updated': params.last_updated.isoformat()
                        }
                        for regime, params in regime_params.items()
                    }
                    for symbol, regime_params in self.parameter_sets.items()
                },
                'last_optimization': {
                    symbol: timestamp.isoformat()
                    for symbol, timestamp in self.last_optimization.items()
                }
            }
            
            cache_file = "optimization_cache.json"
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error guardando cache de optimización: {e}")
    
    def load_optimization_cache(self):
        """Carga cache de optimización"""
        try:
            cache_file = "optimization_cache.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Cargar parameter sets
                for symbol, regime_data in cache_data.get('parameter_sets', {}).items():
                    for regime_str, params_data in regime_data.items():
                        regime = MarketRegime(regime_str)
                        params = ParameterSet(**params_data)
                        params.created_at = datetime.fromisoformat(params_data['created_at'])
                        params.last_updated = datetime.fromisoformat(params_data['last_updated'])
                        
                        self.parameter_sets[symbol][regime] = params
                
                # Cargar timestamps
                for symbol, timestamp_str in cache_data.get('last_optimization', {}).items():
                    self.last_optimization[symbol] = datetime.fromisoformat(timestamp_str)
                
                logger.info("Cache de optimización cargado exitosamente")
                
        except Exception as e:
            logger.error(f"Error cargando cache de optimización: {e}")

if __name__ == "__main__":
    # Ejemplo de uso
    optimizer = DynamicOptimizer(target_monthly_return=0.20)
    
    # Simular datos de mercado
    print("=== SIMULACIÓN DE OPTIMIZACIÓN DINÁMICA ===")
    
    # Generar datos de precio simulados
    np.random.seed(42)
    base_price = 100
    prices = [base_price]
    volumes = [1000]
    
    for i in range(200):
        # Simular movimiento de precio
        change = np.random.normal(0, 0.02)  # 2% volatilidad
        new_price = prices[-1] * (1 + change)
        new_volume = volumes[-1] * (1 + np.random.normal(0, 0.1))
        
        prices.append(new_price)
        volumes.append(max(new_volume, 100))
        
        # Actualizar optimizer
        optimizer.update_market_data("BNBUSDT", new_price, new_volume)
    
    # Verificar condiciones de mercado
    print("\n=== CONDICIONES DE MERCADO ===")
    summary = optimizer.get_optimization_summary()
    
    for symbol, condition in summary['market_conditions'].items():
        print(f"{symbol}:")
        print(f"  Régimen: {condition['regime']}")
        print(f"  Volatilidad: {condition['volatility']:.3f}")
        print(f"  Fuerza tendencia: {condition['trend_strength']:.3f}")
        print(f"  Momentum: {condition['momentum']:.3f}")
    
    # Obtener parámetros actuales
    print("\n=== PARÁMETROS ACTUALES ===")
    current_params = optimizer.get_current_parameters("BNBUSDT")
    print(f"RSI: {current_params.rsi_fast}/{current_params.rsi_slow}")
    print(f"MACD: {current_params.macd_fast}/{current_params.macd_slow}/{current_params.macd_signal}")
    print(f"BB: {current_params.bb_period}, {current_params.bb_std}")
    print(f"Pesos: RSI={current_params.weight_rsi}, MACD={current_params.weight_macd}")
    
    # Forzar optimización
    print("\n=== OPTIMIZACIÓN FORZADA ===")
    if optimizer.force_optimization("BNBUSDT"):
        print("Optimización iniciada...")
        
        # Esperar a que termine (en producción sería asíncrono)
        import time
        time.sleep(2)
        
        # Verificar resultados
        new_summary = optimizer.get_optimization_summary()
        if new_summary['recent_improvements']:
            latest = new_summary['recent_improvements'][-1]
            print(f"Mejora: {latest['improvement']:.4f}")
            print(f"Confianza: {latest['confidence']:.2f}")
        
        # Nuevos parámetros
        updated_params = optimizer.get_current_parameters("BNBUSDT")
        print(f"\nParámetros actualizados:")
        print(f"RSI: {updated_params.rsi_fast}/{updated_params.rsi_slow}")
        print(f"MACD: {updated_params.macd_fast}/{updated_params.macd_slow}/{updated_params.macd_signal}")
        print(f"Performance Score: {updated_params.performance_score:.4f}")
    
    print("\n=== RESUMEN FINAL ===")
    final_summary = optimizer.get_optimization_summary()
    print(f"Estado: {final_summary['status']}")
    print(f"Símbolos rastreados: {len(final_summary['symbols_tracked'])}")
    print(f"Optimizaciones en historial: {final_summary['optimization_history_count']}")