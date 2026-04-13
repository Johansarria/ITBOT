# strategies/quality_filters.py

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import asyncio
from collections import defaultdict, deque
import json
from scipy import stats
from scipy.stats import pearsonr

logger = logging.getLogger(__name__)

class FilterResult(Enum):
    """Resultado de filtro"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"

class FilterType(Enum):
    """Tipos de filtro"""
    VOLUME = "volume"
    VOLATILITY = "volatility"
    SPREAD = "spread"
    CORRELATION = "correlation"
    LIQUIDITY = "liquidity"
    MOMENTUM = "momentum"
    TREND_STRENGTH = "trend_strength"
    MARKET_HOURS = "market_hours"
    NEWS_IMPACT = "news_impact"

@dataclass
class FilterConfig:
    """Configuración de filtros de calidad"""
    # Filtro de Volumen
    min_volume_multiplier: float = 1.2  # 120% del promedio
    volume_lookback_periods: int = 20
    volume_spike_threshold: float = 3.0  # 300% del promedio
    
    # Filtro de Volatilidad
    min_volatility_atr_pct: float = 0.5  # 0.5% ATR mínimo
    max_volatility_atr_pct: float = 5.0  # 5.0% ATR máximo
    volatility_lookback_periods: int = 14
    
    # Filtro de Spread
    max_spread_pct: float = 0.1  # 0.1% spread máximo
    spread_volatility_factor: float = 2.0  # Factor de ajuste por volatilidad
    
    # Filtro de Correlación
    max_correlation: float = 0.7  # Correlación máxima entre pares
    correlation_lookback_periods: int = 50
    correlation_min_data_points: int = 30
    
    # Filtro de Liquidez
    min_market_cap_rank: int = 100  # Top 100 por market cap
    min_daily_volume_usd: float = 10_000_000  # $10M volumen diario mínimo
    order_book_depth_levels: int = 10
    min_bid_ask_depth: float = 50_000  # $50k profundidad mínima
    
    # Filtro de Momentum
    momentum_consistency_threshold: float = 0.6  # 60% consistencia
    momentum_strength_threshold: float = 0.02  # 2% momentum mínimo
    momentum_lookback_periods: int = 10
    
    # Filtro de Fuerza de Tendencia
    min_trend_strength: float = 0.3  # 30% fuerza mínima
    trend_consistency_periods: int = 5
    adx_threshold: float = 25  # ADX mínimo para tendencia fuerte
    
    # Filtro de Horarios de Mercado
    active_market_hours_only: bool = True
    timezone_overlap_bonus: float = 1.2  # Bonificación por overlap de zonas
    weekend_penalty: float = 0.5  # Penalización fin de semana
    
    # Filtro de Impacto de Noticias
    news_impact_window_hours: int = 2  # Ventana de impacto de noticias
    high_impact_news_penalty: float = 0.3  # Penalización por noticias importantes
    earnings_blackout_hours: int = 24  # Horas de blackout por earnings

@dataclass
class FilterResult:
    """Resultado de un filtro específico"""
    filter_type: FilterType
    result: FilterResult
    score: float  # 0.0 - 1.0
    value: float  # Valor medido
    threshold: float  # Umbral configurado
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class QualityAssessment:
    """Evaluación completa de calidad"""
    symbol: str
    overall_score: float  # 0.0 - 1.0
    overall_result: FilterResult
    
    # Resultados por filtro
    filter_results: Dict[FilterType, FilterResult] = field(default_factory=dict)
    
    # Métricas agregadas
    passed_filters: int = 0
    failed_filters: int = 0
    warning_filters: int = 0
    
    # Recomendaciones
    recommendations: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)
    
    timestamp: datetime = field(default_factory=datetime.now)

class QualityFilterEngine:
    """Motor de filtros de calidad avanzados"""
    
    def __init__(self, config: FilterConfig = None):
        self.config = config or FilterConfig()
        
        # Datos de mercado
        self.price_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self.volume_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
        self.spread_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Datos de orden book
        self.order_book_data: Dict[str, Dict] = defaultdict(dict)
        
        # Datos de mercado (market cap, rankings, etc.)
        self.market_data: Dict[str, Dict] = defaultdict(dict)
        
        # Cache de correlaciones
        self.correlation_cache: Dict[Tuple[str, str], Tuple[float, datetime]] = {}
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.correlation_last_update: Optional[datetime] = None
        
        # Datos de noticias y eventos
        self.news_events: List[Dict] = []
        self.earnings_calendar: Dict[str, List[datetime]] = defaultdict(list)
        
        # Historial de evaluaciones
        self.assessment_history: Dict[str, List[QualityAssessment]] = defaultdict(list)
        
        # Configuración de horarios de mercado
        self.market_sessions = {
            'asian': {'start': 0, 'end': 8},    # UTC
            'european': {'start': 7, 'end': 16}, # UTC
            'american': {'start': 13, 'end': 22}  # UTC
        }
        
        logger.info("Quality Filter Engine inicializado")
    
    def update_market_data(self, symbol: str, price: float, volume: float, 
                          bid: float = None, ask: float = None, timestamp: datetime = None):
        """Actualiza datos de mercado"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Almacenar datos
        self.price_data[symbol].append((timestamp, price))
        self.volume_data[symbol].append((timestamp, volume))
        
        # Calcular y almacenar spread si hay bid/ask
        if bid is not None and ask is not None and bid > 0:
            spread_pct = ((ask - bid) / bid) * 100
            self.spread_data[symbol].append((timestamp, spread_pct))
    
    def update_order_book(self, symbol: str, bids: List[Tuple[float, float]], 
                         asks: List[Tuple[float, float]], timestamp: datetime = None):
        """Actualiza datos de order book"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Calcular profundidad del order book
        bid_depth = sum(price * quantity for price, quantity in bids[:self.config.order_book_depth_levels])
        ask_depth = sum(price * quantity for price, quantity in asks[:self.config.order_book_depth_levels])
        
        self.order_book_data[symbol] = {
            'bids': bids,
            'asks': asks,
            'bid_depth': bid_depth,
            'ask_depth': ask_depth,
            'total_depth': bid_depth + ask_depth,
            'timestamp': timestamp
        }
    
    def update_market_info(self, symbol: str, market_cap_rank: int = None, 
                          daily_volume_usd: float = None, **kwargs):
        """Actualiza información de mercado"""
        if market_cap_rank is not None:
            self.market_data[symbol]['market_cap_rank'] = market_cap_rank
        
        if daily_volume_usd is not None:
            self.market_data[symbol]['daily_volume_usd'] = daily_volume_usd
        
        # Otros datos de mercado
        for key, value in kwargs.items():
            self.market_data[symbol][key] = value
    
    def add_news_event(self, symbol: str, event_type: str, impact: str, 
                      timestamp: datetime, description: str = ""):
        """Añade evento de noticias"""
        self.news_events.append({
            'symbol': symbol,
            'type': event_type,
            'impact': impact,  # 'high', 'medium', 'low'
            'timestamp': timestamp,
            'description': description
        })
        
        # Mantener solo eventos recientes
        cutoff = datetime.now() - timedelta(days=7)
        self.news_events = [e for e in self.news_events if e['timestamp'] > cutoff]
    
    def assess_quality(self, symbol: str, symbols_for_correlation: List[str] = None) -> QualityAssessment:
        """Evalúa calidad completa de un símbolo"""
        
        assessment = QualityAssessment(symbol=symbol)
        
        # Ejecutar todos los filtros
        filters_to_run = [
            (FilterType.VOLUME, self._filter_volume),
            (FilterType.VOLATILITY, self._filter_volatility),
            (FilterType.SPREAD, self._filter_spread),
            (FilterType.LIQUIDITY, self._filter_liquidity),
            (FilterType.MOMENTUM, self._filter_momentum),
            (FilterType.TREND_STRENGTH, self._filter_trend_strength),
            (FilterType.MARKET_HOURS, self._filter_market_hours),
            (FilterType.NEWS_IMPACT, self._filter_news_impact)
        ]
        
        # Filtro de correlación (requiere otros símbolos)
        if symbols_for_correlation:
            filters_to_run.append((FilterType.CORRELATION, 
                                 lambda s: self._filter_correlation(s, symbols_for_correlation)))
        
        # Ejecutar filtros
        total_score = 0.0
        total_weight = 0.0
        
        for filter_type, filter_func in filters_to_run:
            try:
                result = filter_func(symbol)
                assessment.filter_results[filter_type] = result
                
                # Contar resultados
                if result.result == FilterResult.PASS:
                    assessment.passed_filters += 1
                elif result.result == FilterResult.FAIL:
                    assessment.failed_filters += 1
                else:
                    assessment.warning_filters += 1
                
                # Ponderar puntuación
                weight = self._get_filter_weight(filter_type)
                total_score += result.score * weight
                total_weight += weight
                
            except Exception as e:
                logger.error(f"Error en filtro {filter_type.value} para {symbol}: {e}")
                # Crear resultado de error
                error_result = FilterResult(
                    filter_type=filter_type,
                    result=FilterResult.FAIL,
                    score=0.0,
                    value=0.0,
                    threshold=0.0,
                    message=f"Error en filtro: {str(e)}"
                )
                assessment.filter_results[filter_type] = error_result
                assessment.failed_filters += 1
        
        # Calcular puntuación general
        if total_weight > 0:
            assessment.overall_score = total_score / total_weight
        else:
            assessment.overall_score = 0.0
        
        # Determinar resultado general
        if assessment.overall_score >= 0.8:
            assessment.overall_result = FilterResult.PASS
        elif assessment.overall_score >= 0.6:
            assessment.overall_result = FilterResult.WARNING
        else:
            assessment.overall_result = FilterResult.FAIL
        
        # Generar recomendaciones
        assessment.recommendations = self._generate_recommendations(assessment)
        assessment.risk_factors = self._identify_risk_factors(assessment)
        
        # Guardar en historial
        self.assessment_history[symbol].append(assessment)
        if len(self.assessment_history[symbol]) > 50:
            self.assessment_history[symbol] = self.assessment_history[symbol][-50:]
        
        return assessment
    
    def _filter_volume(self, symbol: str) -> FilterResult:
        """Filtro de volumen"""
        if len(self.volume_data[symbol]) < self.config.volume_lookback_periods:
            return FilterResult(
                filter_type=FilterType.VOLUME,
                result=FilterResult.FAIL,
                score=0.0,
                value=0.0,
                threshold=self.config.min_volume_multiplier,
                message="Datos insuficientes para análisis de volumen"
            )
        
        # Obtener volúmenes
        volumes = [v[1] for v in list(self.volume_data[symbol])]
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-self.config.volume_lookback_periods:-1])  # Excluir actual
        
        if avg_volume == 0:
            volume_ratio = 0
        else:
            volume_ratio = current_volume / avg_volume
        
        # Evaluar
        if volume_ratio >= self.config.min_volume_multiplier:
            if volume_ratio >= self.config.volume_spike_threshold:
                # Volumen muy alto (puede ser manipulación)
                result = FilterResult.WARNING
                score = 0.8
                message = f"Volumen muy alto: {volume_ratio:.1f}x promedio (posible spike)"
            else:
                result = FilterResult.PASS
                score = min(1.0, volume_ratio / self.config.min_volume_multiplier)
                message = f"Volumen adecuado: {volume_ratio:.1f}x promedio"
        else:
            result = FilterResult.FAIL
            score = volume_ratio / self.config.min_volume_multiplier
            message = f"Volumen bajo: {volume_ratio:.1f}x promedio (mín: {self.config.min_volume_multiplier}x)"
        
        return FilterResult(
            filter_type=FilterType.VOLUME,
            result=result,
            score=score,
            value=volume_ratio,
            threshold=self.config.min_volume_multiplier,
            message=message,
            details={
                'current_volume': current_volume,
                'avg_volume': avg_volume,
                'lookback_periods': self.config.volume_lookback_periods
            }
        )
    
    def _filter_volatility(self, symbol: str) -> FilterResult:
        """Filtro de volatilidad (ATR)"""
        if len(self.price_data[symbol]) < self.config.volatility_lookback_periods + 1:
            return FilterResult(
                filter_type=FilterType.VOLATILITY,
                result=FilterResult.FAIL,
                score=0.0,
                value=0.0,
                threshold=self.config.min_volatility_atr_pct,
                message="Datos insuficientes para análisis de volatilidad"
            )
        
        # Calcular ATR
        prices = [p[1] for p in list(self.price_data[symbol])]
        atr = self._calculate_atr(prices, self.config.volatility_lookback_periods)
        
        if not atr or atr[-1] is None:
            return FilterResult(
                filter_type=FilterType.VOLATILITY,
                result=FilterResult.FAIL,
                score=0.0,
                value=0.0,
                threshold=self.config.min_volatility_atr_pct,
                message="No se pudo calcular ATR"
            )
        
        current_atr = atr[-1]
        current_price = prices[-1]
        atr_pct = (current_atr / current_price) * 100 if current_price > 0 else 0
        
        # Evaluar
        if atr_pct < self.config.min_volatility_atr_pct:
            result = FilterResult.FAIL
            score = atr_pct / self.config.min_volatility_atr_pct
            message = f"Volatilidad muy baja: {atr_pct:.2f}% (mín: {self.config.min_volatility_atr_pct}%)"
        elif atr_pct > self.config.max_volatility_atr_pct:
            result = FilterResult.WARNING
            score = 0.7
            message = f"Volatilidad muy alta: {atr_pct:.2f}% (máx: {self.config.max_volatility_atr_pct}%)"
        else:
            result = FilterResult.PASS
            # Puntuación óptima en el rango medio
            optimal_range = (self.config.min_volatility_atr_pct + self.config.max_volatility_atr_pct) / 2
            distance_from_optimal = abs(atr_pct - optimal_range) / optimal_range
            score = max(0.6, 1.0 - distance_from_optimal)
            message = f"Volatilidad adecuada: {atr_pct:.2f}%"
        
        return FilterResult(
            filter_type=FilterType.VOLATILITY,
            result=result,
            score=score,
            value=atr_pct,
            threshold=self.config.min_volatility_atr_pct,
            message=message,
            details={
                'atr_value': current_atr,
                'current_price': current_price,
                'lookback_periods': self.config.volatility_lookback_periods
            }
        )
    
    def _filter_spread(self, symbol: str) -> FilterResult:
        """Filtro de spread"""
        if len(self.spread_data[symbol]) == 0:
            return FilterResult(
                filter_type=FilterType.SPREAD,
                result=FilterResult.WARNING,
                score=0.5,
                value=0.0,
                threshold=self.config.max_spread_pct,
                message="No hay datos de spread disponibles"
            )
        
        # Obtener spread actual
        current_spread = self.spread_data[symbol][-1][1]
        
        # Ajustar umbral por volatilidad
        adjusted_threshold = self.config.max_spread_pct
        
        if len(self.price_data[symbol]) >= 14:
            prices = [p[1] for p in list(self.price_data[symbol])]
            atr = self._calculate_atr(prices, 14)
            if atr and atr[-1] is not None:
                atr_pct = (atr[-1] / prices[-1]) * 100
                # Ajustar umbral basado en volatilidad
                adjusted_threshold *= (1 + atr_pct * self.config.spread_volatility_factor)
        
        # Evaluar
        if current_spread <= adjusted_threshold:
            result = FilterResult.PASS
            score = max(0.6, 1.0 - (current_spread / adjusted_threshold))
            message = f"Spread aceptable: {current_spread:.3f}% (máx: {adjusted_threshold:.3f}%)"
        else:
            result = FilterResult.FAIL
            score = max(0.0, 1.0 - (current_spread / adjusted_threshold))
            message = f"Spread muy alto: {current_spread:.3f}% (máx: {adjusted_threshold:.3f}%)"
        
        return FilterResult(
            filter_type=FilterType.SPREAD,
            result=result,
            score=score,
            value=current_spread,
            threshold=adjusted_threshold,
            message=message,
            details={
                'original_threshold': self.config.max_spread_pct,
                'volatility_adjusted': adjusted_threshold != self.config.max_spread_pct
            }
        )
    
    def _filter_correlation(self, symbol: str, other_symbols: List[str]) -> FilterResult:
        """Filtro de correlación"""
        if len(other_symbols) == 0:
            return FilterResult(
                filter_type=FilterType.CORRELATION,
                result=FilterResult.PASS,
                score=1.0,
                value=0.0,
                threshold=self.config.max_correlation,
                message="No hay otros símbolos para comparar correlación"
            )
        
        # Actualizar matriz de correlación si es necesario
        self._update_correlation_matrix([symbol] + other_symbols)
        
        if self.correlation_matrix is None or symbol not in self.correlation_matrix.index:
            return FilterResult(
                filter_type=FilterType.CORRELATION,
                result=FilterResult.WARNING,
                score=0.5,
                value=0.0,
                threshold=self.config.max_correlation,
                message="No se pudo calcular correlación"
            )
        
        # Obtener correlaciones del símbolo con otros
        correlations = []
        for other_symbol in other_symbols:
            if other_symbol in self.correlation_matrix.columns:
                corr = abs(self.correlation_matrix.loc[symbol, other_symbol])
                if not np.isnan(corr):
                    correlations.append(corr)
        
        if not correlations:
            return FilterResult(
                filter_type=FilterType.CORRELATION,
                result=FilterResult.WARNING,
                score=0.5,
                value=0.0,
                threshold=self.config.max_correlation,
                message="No se pudieron calcular correlaciones"
            )
        
        max_correlation = max(correlations)
        avg_correlation = np.mean(correlations)
        
        # Evaluar
        if max_correlation <= self.config.max_correlation:
            result = FilterResult.PASS
            score = max(0.6, 1.0 - (max_correlation / self.config.max_correlation))
            message = f"Correlación aceptable: máx {max_correlation:.2f}, promedio {avg_correlation:.2f}"
        else:
            result = FilterResult.FAIL
            score = max(0.0, 1.0 - (max_correlation / self.config.max_correlation))
            message = f"Correlación muy alta: máx {max_correlation:.2f} (límite: {self.config.max_correlation})"
        
        return FilterResult(
            filter_type=FilterType.CORRELATION,
            result=result,
            score=score,
            value=max_correlation,
            threshold=self.config.max_correlation,
            message=message,
            details={
                'max_correlation': max_correlation,
                'avg_correlation': avg_correlation,
                'correlations': dict(zip(other_symbols, correlations))
            }
        )
    
    def _filter_liquidity(self, symbol: str) -> FilterResult:
        """Filtro de liquidez"""
        market_info = self.market_data.get(symbol, {})
        order_book = self.order_book_data.get(symbol, {})
        
        score_components = []
        messages = []
        
        # Market cap rank
        market_cap_rank = market_info.get('market_cap_rank')
        if market_cap_rank is not None:
            if market_cap_rank <= self.config.min_market_cap_rank:
                score_components.append(1.0)
                messages.append(f"Ranking market cap: #{market_cap_rank}")
            else:
                score_components.append(max(0.0, 1.0 - (market_cap_rank - self.config.min_market_cap_rank) / self.config.min_market_cap_rank))
                messages.append(f"Ranking market cap bajo: #{market_cap_rank}")
        
        # Volumen diario en USD
        daily_volume_usd = market_info.get('daily_volume_usd')
        if daily_volume_usd is not None:
            if daily_volume_usd >= self.config.min_daily_volume_usd:
                score_components.append(1.0)
                messages.append(f"Volumen diario: ${daily_volume_usd:,.0f}")
            else:
                score_components.append(daily_volume_usd / self.config.min_daily_volume_usd)
                messages.append(f"Volumen diario bajo: ${daily_volume_usd:,.0f}")
        
        # Profundidad del order book
        if order_book:
            total_depth = order_book.get('total_depth', 0)
            if total_depth >= self.config.min_bid_ask_depth:
                score_components.append(1.0)
                messages.append(f"Profundidad order book: ${total_depth:,.0f}")
            else:
                score_components.append(total_depth / self.config.min_bid_ask_depth)
                messages.append(f"Profundidad order book baja: ${total_depth:,.0f}")
        
        # Calcular puntuación general
        if score_components:
            overall_score = np.mean(score_components)
        else:
            overall_score = 0.5  # Puntuación neutral si no hay datos
            messages.append("Datos de liquidez limitados")
        
        # Determinar resultado
        if overall_score >= 0.8:
            result = FilterResult.PASS
        elif overall_score >= 0.6:
            result = FilterResult.WARNING
        else:
            result = FilterResult.FAIL
        
        return FilterResult(
            filter_type=FilterType.LIQUIDITY,
            result=result,
            score=overall_score,
            value=overall_score,
            threshold=0.8,
            message="; ".join(messages),
            details={
                'market_cap_rank': market_cap_rank,
                'daily_volume_usd': daily_volume_usd,
                'order_book_depth': order_book.get('total_depth'),
                'score_components': score_components
            }
        )
    
    def _filter_momentum(self, symbol: str) -> FilterResult:
        """Filtro de momentum"""
        if len(self.price_data[symbol]) < self.config.momentum_lookback_periods + 1:
            return FilterResult(
                filter_type=FilterType.MOMENTUM,
                result=FilterResult.FAIL,
                score=0.0,
                value=0.0,
                threshold=self.config.momentum_strength_threshold,
                message="Datos insuficientes para análisis de momentum"
            )
        
        prices = [p[1] for p in list(self.price_data[symbol])]
        
        # Calcular momentum en diferentes períodos
        momentum_values = []
        for i in range(1, self.config.momentum_lookback_periods + 1):
            if len(prices) > i:
                momentum = (prices[-1] - prices[-1-i]) / prices[-1-i]
                momentum_values.append(momentum)
        
        if not momentum_values:
            return FilterResult(
                filter_type=FilterType.MOMENTUM,
                result=FilterResult.FAIL,
                score=0.0,
                value=0.0,
                threshold=self.config.momentum_strength_threshold,
                message="No se pudo calcular momentum"
            )
        
        # Calcular métricas
        avg_momentum = np.mean(momentum_values)
        momentum_consistency = self._calculate_momentum_consistency(momentum_values)
        momentum_strength = abs(avg_momentum)
        
        # Evaluar
        strength_ok = momentum_strength >= self.config.momentum_strength_threshold
        consistency_ok = momentum_consistency >= self.config.momentum_consistency_threshold
        
        if strength_ok and consistency_ok:
            result = FilterResult.PASS
            score = min(1.0, (momentum_strength / self.config.momentum_strength_threshold) * momentum_consistency)
            message = f"Momentum fuerte y consistente: {avg_momentum:.2f}% (consistencia: {momentum_consistency:.2f})"
        elif strength_ok or consistency_ok:
            result = FilterResult.WARNING
            score = 0.6
            message = f"Momentum parcial: fuerza {momentum_strength:.2f}%, consistencia {momentum_consistency:.2f}"
        else:
            result = FilterResult.FAIL
            score = min(0.5, momentum_strength / self.config.momentum_strength_threshold)
            message = f"Momentum débil: {avg_momentum:.2f}% (mín: {self.config.momentum_strength_threshold:.2f}%)"
        
        return FilterResult(
            filter_type=FilterType.MOMENTUM,
            result=result,
            score=score,
            value=momentum_strength,
            threshold=self.config.momentum_strength_threshold,
            message=message,
            details={
                'avg_momentum': avg_momentum,
                'momentum_strength': momentum_strength,
                'momentum_consistency': momentum_consistency,
                'momentum_values': momentum_values
            }
        )
    
    def _filter_trend_strength(self, symbol: str) -> FilterResult:
        """Filtro de fuerza de tendencia"""
        if len(self.price_data[symbol]) < 50:
            return FilterResult(
                filter_type=FilterType.TREND_STRENGTH,
                result=FilterResult.FAIL,
                score=0.0,
                value=0.0,
                threshold=self.config.min_trend_strength,
                message="Datos insuficientes para análisis de tendencia"
            )
        
        prices = [p[1] for p in list(self.price_data[symbol])]
        
        # Calcular fuerza de tendencia usando regresión lineal
        x = np.arange(len(prices))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, prices)
        
        # Normalizar slope por precio promedio
        avg_price = np.mean(prices)
        normalized_slope = abs(slope) / avg_price if avg_price > 0 else 0
        
        # R-squared como medida de consistencia de tendencia
        r_squared = r_value ** 2
        
        # Calcular ADX simplificado
        adx = self._calculate_simple_adx(prices)
        
        # Combinar métricas
        trend_strength = (normalized_slope + r_squared + (adx / 100 if adx else 0)) / 3
        
        # Evaluar
        if trend_strength >= self.config.min_trend_strength:
            result = FilterResult.PASS
            score = min(1.0, trend_strength / self.config.min_trend_strength)
            message = f"Tendencia fuerte: {trend_strength:.2f} (R²: {r_squared:.2f}, ADX: {adx:.1f})"
        else:
            result = FilterResult.FAIL
            score = trend_strength / self.config.min_trend_strength
            message = f"Tendencia débil: {trend_strength:.2f} (mín: {self.config.min_trend_strength})"
        
        return FilterResult(
            filter_type=FilterType.TREND_STRENGTH,
            result=result,
            score=score,
            value=trend_strength,
            threshold=self.config.min_trend_strength,
            message=message,
            details={
                'normalized_slope': normalized_slope,
                'r_squared': r_squared,
                'adx': adx,
                'p_value': p_value
            }
        )
    
    def _filter_market_hours(self, symbol: str) -> FilterResult:
        """Filtro de horarios de mercado"""
        now = datetime.now()
        current_hour = now.hour  # UTC
        is_weekend = now.weekday() >= 5  # Sábado = 5, Domingo = 6
        
        score = 1.0
        messages = []
        
        # Penalización por fin de semana
        if is_weekend and self.config.weekend_penalty < 1.0:
            score *= self.config.weekend_penalty
            messages.append(f"Fin de semana (penalización: {self.config.weekend_penalty})")
        
        # Bonificación por overlap de sesiones
        active_sessions = []
        for session_name, session_hours in self.market_sessions.items():
            if session_hours['start'] <= current_hour <= session_hours['end']:
                active_sessions.append(session_name)
        
        if len(active_sessions) > 1:
            score *= self.config.timezone_overlap_bonus
            messages.append(f"Overlap de sesiones: {', '.join(active_sessions)}")
        elif len(active_sessions) == 1:
            messages.append(f"Sesión activa: {active_sessions[0]}")
        else:
            score *= 0.7  # Penalización por horario inactivo
            messages.append("Horario de baja actividad")
        
        # Solo aplicar filtro estricto si está configurado
        if self.config.active_market_hours_only and not active_sessions and not is_weekend:
            result = FilterResult.FAIL
            score = 0.3
        elif score >= 0.8:
            result = FilterResult.PASS
        elif score >= 0.6:
            result = FilterResult.WARNING
        else:
            result = FilterResult.FAIL
        
        return FilterResult(
            filter_type=FilterType.MARKET_HOURS,
            result=result,
            score=score,
            value=score,
            threshold=0.8,
            message="; ".join(messages),
            details={
                'current_hour_utc': current_hour,
                'is_weekend': is_weekend,
                'active_sessions': active_sessions
            }
        )
    
    def _filter_news_impact(self, symbol: str) -> FilterResult:
        """Filtro de impacto de noticias"""
        now = datetime.now()
        cutoff = now - timedelta(hours=self.config.news_impact_window_hours)
        
        # Buscar eventos recientes
        recent_events = [
            event for event in self.news_events
            if event['symbol'] == symbol and event['timestamp'] > cutoff
        ]
        
        # Buscar earnings próximos
        earnings_dates = self.earnings_calendar.get(symbol, [])
        upcoming_earnings = [
            date for date in earnings_dates
            if abs((date - now).total_seconds()) < self.config.earnings_blackout_hours * 3600
        ]
        
        score = 1.0
        messages = []
        
        # Evaluar impacto de noticias
        high_impact_events = [e for e in recent_events if e['impact'] == 'high']
        medium_impact_events = [e for e in recent_events if e['impact'] == 'medium']
        
        if high_impact_events:
            score *= (1 - self.config.high_impact_news_penalty)
            messages.append(f"{len(high_impact_events)} eventos de alto impacto recientes")
        
        if medium_impact_events:
            score *= 0.9
            messages.append(f"{len(medium_impact_events)} eventos de impacto medio recientes")
        
        # Evaluar earnings
        if upcoming_earnings:
            score *= 0.5  # Penalización fuerte por earnings
            messages.append(f"Earnings próximos: {len(upcoming_earnings)}")
        
        # Determinar resultado
        if score >= 0.8:
            result = FilterResult.PASS
            if not messages:
                messages.append("Sin eventos de impacto recientes")
        elif score >= 0.6:
            result = FilterResult.WARNING
        else:
            result = FilterResult.FAIL
        
        return FilterResult(
            filter_type=FilterType.NEWS_IMPACT,
            result=result,
            score=score,
            value=score,
            threshold=0.8,
            message="; ".join(messages),
            details={
                'recent_events': len(recent_events),
                'high_impact_events': len(high_impact_events),
                'medium_impact_events': len(medium_impact_events),
                'upcoming_earnings': len(upcoming_earnings)
            }
        )
    
    def _calculate_atr(self, prices: List[float], period: int) -> List[Optional[float]]:
        """Calcula Average True Range"""
        if len(prices) < period + 1:
            return [None] * len(prices)
        
        # Simplificado: usar solo diferencias de precio
        true_ranges = [abs(prices[i] - prices[i-1]) for i in range(1, len(prices))]
        
        atr_values = [None] * len(prices)
        
        # Primer ATR (promedio simple)
        if len(true_ranges) >= period:
            atr_values[period] = np.mean(true_ranges[:period])
            
            # ATR suavizado
            for i in range(period + 1, len(prices)):
                if i - 1 < len(true_ranges):
                    atr_values[i] = (atr_values[i-1] * (period - 1) + true_ranges[i-1]) / period
        
        return atr_values
    
    def _calculate_momentum_consistency(self, momentum_values: List[float]) -> float:
        """Calcula consistencia del momentum"""
        if len(momentum_values) < 2:
            return 0.0
        
        # Contar cambios de dirección
        direction_changes = 0
        for i in range(1, len(momentum_values)):
            if (momentum_values[i] > 0) != (momentum_values[i-1] > 0):
                direction_changes += 1
        
        # Consistencia = 1 - (cambios / máximo_cambios_posibles)
        max_changes = len(momentum_values) - 1
        consistency = 1.0 - (direction_changes / max_changes) if max_changes > 0 else 1.0
        
        return consistency
    
    def _calculate_simple_adx(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calcula ADX simplificado"""
        if len(prices) < period * 2:
            return None
        
        # Calcular movimientos direccionales
        dm_plus = []
        dm_minus = []
        
        for i in range(1, len(prices)):
            high_diff = prices[i] - prices[i-1]
            low_diff = prices[i-1] - prices[i]
            
            if high_diff > low_diff and high_diff > 0:
                dm_plus.append(high_diff)
                dm_minus.append(0)
            elif low_diff > high_diff and low_diff > 0:
                dm_plus.append(0)
                dm_minus.append(low_diff)
            else:
                dm_plus.append(0)
                dm_minus.append(0)
        
        if len(dm_plus) < period:
            return None
        
        # Promediar
        avg_dm_plus = np.mean(dm_plus[-period:])
        avg_dm_minus = np.mean(dm_minus[-period:])
        
        # Calcular DI
        atr = np.mean([abs(prices[i] - prices[i-1]) for i in range(-period, 0)])
        
        if atr == 0:
            return 0
        
        di_plus = (avg_dm_plus / atr) * 100
        di_minus = (avg_dm_minus / atr) * 100
        
        # Calcular ADX
        dx = abs(di_plus - di_minus) / (di_plus + di_minus) * 100 if (di_plus + di_minus) > 0 else 0
        
        return dx
    
    def _update_correlation_matrix(self, symbols: List[str]):
        """Actualiza matriz de correlación"""
        # Verificar si necesita actualización
        if (self.correlation_last_update and 
            datetime.now() - self.correlation_last_update < timedelta(hours=1)):
            return
        
        # Recopilar datos de precios
        price_data = {}
        min_length = float('inf')
        
        for symbol in symbols:
            if len(self.price_data[symbol]) >= self.config.correlation_min_data_points:
                prices = [p[1] for p in list(self.price_data[symbol])[-self.config.correlation_lookback_periods:]]
                price_data[symbol] = prices
                min_length = min(min_length, len(prices))
        
        if len(price_data) < 2 or min_length < self.config.correlation_min_data_points:
            return
        
        # Truncar a la misma longitud
        for symbol in price_data:
            price_data[symbol] = price_data[symbol][-min_length:]
        
        # Crear DataFrame y calcular correlaciones
        df = pd.DataFrame(price_data)
        self.correlation_matrix = df.corr()
        self.correlation_last_update = datetime.now()
    
    def _get_filter_weight(self, filter_type: FilterType) -> float:
        """Obtiene peso de un filtro"""
        weights = {
            FilterType.VOLUME: 1.5,
            FilterType.VOLATILITY: 1.2,
            FilterType.SPREAD: 1.0,
            FilterType.CORRELATION: 1.3,
            FilterType.LIQUIDITY: 1.1,
            FilterType.MOMENTUM: 0.9,
            FilterType.TREND_STRENGTH: 0.8,
            FilterType.MARKET_HOURS: 0.6,
            FilterType.NEWS_IMPACT: 0.7
        }
        return weights.get(filter_type, 1.0)
    
    def _generate_recommendations(self, assessment: QualityAssessment) -> List[str]:
        """Genera recomendaciones basadas en la evaluación"""
        recommendations = []
        
        for filter_type, result in assessment.filter_results.items():
            if result.result == FilterResult.FAIL:
                if filter_type == FilterType.VOLUME:
                    recommendations.append("Esperar mayor volumen antes de operar")
                elif filter_type == FilterType.VOLATILITY:
                    if result.value < result.threshold:
                        recommendations.append("Volatilidad muy baja - considerar otros activos")
                    else:
                        recommendations.append("Volatilidad muy alta - reducir tamaño de posición")
                elif filter_type == FilterType.SPREAD:
                    recommendations.append("Spread alto - usar órdenes limit")
                elif filter_type == FilterType.CORRELATION:
                    recommendations.append("Alta correlación con otros activos - diversificar")
                elif filter_type == FilterType.LIQUIDITY:
                    recommendations.append("Liquidez limitada - usar órdenes pequeñas")
                elif filter_type == FilterType.MOMENTUM:
                    recommendations.append("Momentum débil - esperar confirmación")
                elif filter_type == FilterType.TREND_STRENGTH:
                    recommendations.append("Tendencia débil - trading de rango")
                elif filter_type == FilterType.MARKET_HOURS:
                    recommendations.append("Horario subóptimo - considerar esperar")
                elif filter_type == FilterType.NEWS_IMPACT:
                    recommendations.append("Eventos de alto impacto - evitar trading")
        
        # Recomendaciones generales
        if assessment.overall_score < 0.5:
            recommendations.append("Calidad general baja - evitar trading")
        elif assessment.overall_score < 0.7:
            recommendations.append("Calidad moderada - usar gestión de riesgo estricta")
        
        return recommendations
    
    def _identify_risk_factors(self, assessment: QualityAssessment) -> List[str]:
        """Identifica factores de riesgo"""
        risk_factors = []
        
        # Analizar filtros fallidos
        failed_filters = [ft for ft, result in assessment.filter_results.items() 
                         if result.result == FilterResult.FAIL]
        
        if FilterType.VOLATILITY in failed_filters:
            risk_factors.append("Volatilidad extrema")
        
        if FilterType.LIQUIDITY in failed_filters:
            risk_factors.append("Liquidez limitada")
        
        if FilterType.CORRELATION in failed_filters:
            risk_factors.append("Alta correlación con otros activos")
        
        if FilterType.NEWS_IMPACT in failed_filters:
            risk_factors.append("Eventos de mercado de alto impacto")
        
        # Factores de riesgo por combinaciones
        if (FilterType.VOLUME in failed_filters and 
            FilterType.VOLATILITY in failed_filters):
            risk_factors.append("Condiciones de mercado anómalas")
        
        return risk_factors
    
    def get_quality_summary(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Resumen de calidad para múltiples símbolos"""
        if symbols is None:
            symbols = list(self.assessment_history.keys())
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'symbols_analyzed': len(symbols),
            'symbol_scores': {},
            'filter_performance': defaultdict(list),
            'overall_statistics': {}
        }
        
        all_scores = []
        
        for symbol in symbols:
            if symbol in self.assessment_history and self.assessment_history[symbol]:
                latest_assessment = self.assessment_history[symbol][-1]
                
                summary['symbol_scores'][symbol] = {
                    'overall_score': latest_assessment.overall_score,
                    'overall_result': latest_assessment.overall_result.value,
                    'passed_filters': latest_assessment.passed_filters,
                    'failed_filters': latest_assessment.failed_filters,
                    'timestamp': latest_assessment.timestamp.isoformat()
                }
                
                all_scores.append(latest_assessment.overall_score)
                
                # Estadísticas por filtro
                for filter_type, result in latest_assessment.filter_results.items():
                    summary['filter_performance'][filter_type.value].append(result.score)
        
        # Estadísticas generales
        if all_scores:
            summary['overall_statistics'] = {
                'avg_score': np.mean(all_scores),
                'min_score': np.min(all_scores),
                'max_score': np.max(all_scores),
                'std_score': np.std(all_scores)
            }
        
        return summary

if __name__ == "__main__":
    # Ejemplo de uso
    filter_engine = QualityFilterEngine()
    
    print("=== SIMULACIÓN DE FILTROS DE CALIDAD ===")
    
    # Simular datos de mercado
    symbols = ["BNBUSDT", "SOLUSDT"]
    
    # Datos simulados
    import random
    
    for symbol in symbols:
        base_price = 300 if symbol == "BNBUSDT" else 100
        
        # Generar datos históricos
        for i in range(100):
            timestamp = datetime.now() - timedelta(minutes=5*i)
            price = base_price * (1 + random.gauss(0, 0.01))
            volume = random.uniform(1000, 2000)
            bid = price * 0.999
            ask = price * 1.001
            
            filter_engine.update_market_data(symbol, price, volume, bid, ask, timestamp)
        
        # Datos de mercado
        filter_engine.update_market_info(
            symbol,
            market_cap_rank=random.randint(10, 50),
            daily_volume_usd=random.uniform(50_000_000, 200_000_000)
        )
        
        # Order book simulado
        bids = [(base_price * (1 - i*0.001), random.uniform(100, 1000)) for i in range(10)]
        asks = [(base_price * (1 + i*0.001), random.uniform(100, 1000)) for i in range(10)]
        filter_engine.update_order_book(symbol, bids, asks)
    
    # Evaluar calidad
    print("\n=== EVALUACIONES DE CALIDAD ===")
    
    for symbol in symbols:
        print(f"\n{symbol}:")
        assessment = filter_engine.assess_quality(symbol, [s for s in symbols if s != symbol])
        
        print(f"  Puntuación General: {assessment.overall_score:.2f} ({assessment.overall_result.value})")
        print(f"  Filtros: {assessment.passed_filters} ✓, {assessment.failed_filters} ✗, {assessment.warning_filters} ⚠")
        
        print("  Resultados por Filtro:")
        for filter_type, result in assessment.filter_results.items():
            status_icon = "✓" if result.result == FilterResult.PASS else "✗" if result.result == FilterResult.FAIL else "⚠"
            print(f"    {filter_type.value}: {result.score:.2f} {status_icon} - {result.message}")
        
        if assessment.recommendations:
            print("  Recomendaciones:")
            for rec in assessment.recommendations:
                print(f"    • {rec}")
        
        if assessment.risk_factors:
            print("  Factores de Riesgo:")
            for risk in assessment.risk_factors:
                print(f"    ⚠ {risk}")
    
    # Resumen general
    print("\n=== RESUMEN GENERAL ===")
    summary = filter_engine.get_quality_summary(symbols)
    
    print(f"Símbolos analizados: {summary['symbols_analyzed']}")
    print(f"Puntuación promedio: {summary['overall_statistics'].get('avg_score', 0):.2f}")
    
    print("\nPuntuaciones por símbolo:")
    for symbol, scores in summary['symbol_scores'].items():
        print(f"  {symbol}: {scores['overall_score']:.2f} ({scores['overall_result']})")
    
    print("\n=== ANÁLISIS COMPLETADO ===")