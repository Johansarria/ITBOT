"""
Sistema de Gestión de Riesgo Dinámico - Phase 2
Gestión adaptativa de riesgo basada en condiciones de mercado
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Regímenes de mercado"""
    BULL_TRENDING = "bull_trending"
    BEAR_TRENDING = "bear_trending"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"

class RiskLevel(Enum):
    """Niveles de riesgo"""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"

@dataclass
class RiskMetrics:
    """Métricas de riesgo calculadas"""
    var_95: float  # Value at Risk 95%
    var_99: float  # Value at Risk 99%
    expected_shortfall: float  # Expected Shortfall (CVaR)
    max_drawdown: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    beta: float
    correlation_risk: float
    liquidity_risk: float

@dataclass
class PositionRisk:
    """Riesgo de una posición específica"""
    symbol: str
    position_size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    risk_percentage: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    time_in_position: timedelta
    risk_score: float

@dataclass
class RiskLimits:
    """Límites de riesgo dinámicos"""
    max_position_size: float
    max_portfolio_risk: float
    max_daily_loss: float
    max_drawdown: float
    max_correlation: float
    min_liquidity_score: float
    max_leverage: float
    stop_loss_percentage: float

@dataclass
class RiskAlert:
    """Alerta de riesgo"""
    alert_type: str
    severity: RiskLevel
    message: str
    symbol: Optional[str]
    current_value: float
    threshold: float
    timestamp: datetime
    action_required: bool

class DynamicRiskManager:
    """
    Gestor de riesgo dinámico que se adapta a las condiciones del mercado
    """
    
    def __init__(self, initial_capital: float = 100000):
        self.logger = logging.getLogger(__name__)
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Historial de métricas
        self.risk_history = []
        self.position_history = []
        self.alert_history = []
        
        # Configuración de regímenes
        self.regime_config = {
            MarketRegime.BULL_TRENDING: {
                'max_position_size': 0.15,
                'max_portfolio_risk': 0.20,
                'stop_loss_percentage': 0.08,
                'max_leverage': 2.0
            },
            MarketRegime.BEAR_TRENDING: {
                'max_position_size': 0.08,
                'max_portfolio_risk': 0.10,
                'stop_loss_percentage': 0.05,
                'max_leverage': 1.5
            },
            MarketRegime.SIDEWAYS: {
                'max_position_size': 0.12,
                'max_portfolio_risk': 0.15,
                'stop_loss_percentage': 0.06,
                'max_leverage': 1.8
            },
            MarketRegime.HIGH_VOLATILITY: {
                'max_position_size': 0.06,
                'max_portfolio_risk': 0.08,
                'stop_loss_percentage': 0.04,
                'max_leverage': 1.2
            },
            MarketRegime.LOW_VOLATILITY: {
                'max_position_size': 0.18,
                'max_portfolio_risk': 0.25,
                'stop_loss_percentage': 0.10,
                'max_leverage': 2.5
            },
            MarketRegime.CRISIS: {
                'max_position_size': 0.03,
                'max_portfolio_risk': 0.05,
                'stop_loss_percentage': 0.02,
                'max_leverage': 1.0
            }
        }
        
        # Estado actual
        self.current_regime = MarketRegime.SIDEWAYS
        self.current_limits = self._get_risk_limits(self.current_regime)
        self.positions = {}
        self.daily_pnl = 0.0
        self.max_daily_drawdown = 0.0
        
        self.logger.info("✅ DynamicRiskManager inicializado")
    
    def detect_market_regime(self, market_data: Dict[str, pd.DataFrame]) -> MarketRegime:
        """
        Detecta el régimen actual del mercado
        """
        try:
            if not market_data:
                return self.current_regime
            
            # Analizar datos de múltiples símbolos
            volatilities = []
            trends = []
            volumes = []
            
            for symbol, data in market_data.items():
                if len(data) < 20:
                    continue
                
                # Calcular volatilidad
                returns = data['close'].pct_change().dropna()
                volatility = returns.std() * np.sqrt(24 * 365)  # Anualizada
                volatilities.append(volatility)
                
                # Calcular tendencia
                prices = data['close'].values
                trend_slope = np.polyfit(range(len(prices)), prices, 1)[0]
                trend_strength = trend_slope / prices[0]
                trends.append(trend_strength)
                
                # Analizar volumen
                if 'volume' in data.columns:
                    volume_trend = data['volume'].rolling(10).mean().iloc[-1] / data['volume'].rolling(20).mean().iloc[-1]
                    volumes.append(volume_trend)
            
            if not volatilities:
                return self.current_regime
            
            # Métricas agregadas
            avg_volatility = np.mean(volatilities)
            avg_trend = np.mean(trends)
            avg_volume_trend = np.mean(volumes) if volumes else 1.0
            
            # Detectar régimen
            if avg_volatility > 0.8:  # Alta volatilidad
                if avg_volatility > 1.5:
                    regime = MarketRegime.CRISIS
                else:
                    regime = MarketRegime.HIGH_VOLATILITY
            elif avg_volatility < 0.3:  # Baja volatilidad
                regime = MarketRegime.LOW_VOLATILITY
            elif abs(avg_trend) > 0.02:  # Tendencia fuerte
                if avg_trend > 0:
                    regime = MarketRegime.BULL_TRENDING
                else:
                    regime = MarketRegime.BEAR_TRENDING
            else:  # Mercado lateral
                regime = MarketRegime.SIDEWAYS
            
            # Actualizar régimen si cambió
            if regime != self.current_regime:
                self.logger.info(f"🔄 Cambio de régimen: {self.current_regime.value} → {regime.value}")
                self.current_regime = regime
                self.current_limits = self._get_risk_limits(regime)
                
                # Generar alerta de cambio de régimen
                alert = RiskAlert(
                    alert_type="regime_change",
                    severity=RiskLevel.MEDIUM,
                    message=f"Cambio de régimen de mercado a {regime.value}",
                    symbol=None,
                    current_value=avg_volatility,
                    threshold=0.5,
                    timestamp=datetime.now(),
                    action_required=True
                )
                self.alert_history.append(alert)
            
            return regime
            
        except Exception as e:
            self.logger.error(f"❌ Error detectando régimen de mercado: {e}")
            return self.current_regime
    
    def _get_risk_limits(self, regime: MarketRegime) -> RiskLimits:
        """
        Obtiene límites de riesgo para un régimen específico
        """
        config = self.regime_config[regime]
        
        return RiskLimits(
            max_position_size=config['max_position_size'],
            max_portfolio_risk=config['max_portfolio_risk'],
            max_daily_loss=0.05,  # 5% pérdida diaria máxima
            max_drawdown=0.15,    # 15% drawdown máximo
            max_correlation=0.7,   # Correlación máxima entre posiciones
            min_liquidity_score=0.6,  # Score mínimo de liquidez
            max_leverage=config['max_leverage'],
            stop_loss_percentage=config['stop_loss_percentage']
        )
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                              stop_loss: float, confidence: float = 0.5) -> float:
        """
        Calcula el tamaño de posición óptimo basado en riesgo
        """
        try:
            # Riesgo por operación (Kelly Criterion modificado)
            risk_per_trade = min(0.02, self.current_limits.max_position_size * confidence)
            
            # Distancia al stop loss
            if stop_loss <= 0:
                stop_distance = 0.05  # 5% por defecto
            else:
                stop_distance = abs(entry_price - stop_loss) / entry_price
            
            # Tamaño basado en riesgo
            risk_amount = self.current_capital * risk_per_trade
            position_value = risk_amount / stop_distance
            position_size = position_value / entry_price
            
            # Aplicar límites
            max_position_value = self.current_capital * self.current_limits.max_position_size
            max_position_size = max_position_value / entry_price
            
            final_size = min(position_size, max_position_size)
            
            self.logger.info(f"💰 Tamaño calculado para {symbol}: {final_size:.6f} "
                           f"(riesgo: {risk_per_trade*100:.1f}%, stop: {stop_distance*100:.1f}%)")
            
            return final_size
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando tamaño de posición para {symbol}: {e}")
            return 0.0
    
    def evaluate_position_risk(self, symbol: str, position_size: float, 
                             entry_price: float, current_price: float) -> PositionRisk:
        """
        Evalúa el riesgo de una posición específica
        """
        try:
            # Calcular PnL no realizado
            unrealized_pnl = (current_price - entry_price) * position_size
            
            # Porcentaje de riesgo del portafolio
            position_value = position_size * current_price
            risk_percentage = position_value / self.current_capital
            
            # Tiempo en posición
            if symbol in self.positions:
                time_in_position = datetime.now() - self.positions[symbol]['entry_time']
            else:
                time_in_position = timedelta(0)
            
            # Calcular score de riesgo
            risk_score = self._calculate_risk_score(
                risk_percentage, unrealized_pnl, time_in_position
            )
            
            # Calcular stop loss dinámico
            volatility = self._estimate_volatility(symbol)
            stop_loss = entry_price * (1 - self.current_limits.stop_loss_percentage - volatility)
            
            position_risk = PositionRisk(
                symbol=symbol,
                position_size=position_size,
                entry_price=entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                risk_percentage=risk_percentage,
                stop_loss=stop_loss,
                take_profit=entry_price * (1 + self.current_limits.stop_loss_percentage * 2),
                time_in_position=time_in_position,
                risk_score=risk_score
            )
            
            return position_risk
            
        except Exception as e:
            self.logger.error(f"❌ Error evaluando riesgo de posición {symbol}: {e}")
            return PositionRisk(
                symbol=symbol,
                position_size=0,
                entry_price=entry_price,
                current_price=current_price,
                unrealized_pnl=0,
                risk_percentage=0,
                stop_loss=None,
                take_profit=None,
                time_in_position=timedelta(0),
                risk_score=0
            )
    
    def _calculate_risk_score(self, risk_percentage: float, unrealized_pnl: float, 
                            time_in_position: timedelta) -> float:
        """
        Calcula un score de riesgo para una posición
        """
        score = 0.0
        
        # Componente de tamaño
        if risk_percentage > self.current_limits.max_position_size:
            score += 0.4
        elif risk_percentage > self.current_limits.max_position_size * 0.8:
            score += 0.2
        
        # Componente de PnL
        pnl_percentage = unrealized_pnl / self.current_capital
        if pnl_percentage < -0.05:  # Pérdida > 5%
            score += 0.3
        elif pnl_percentage < -0.02:  # Pérdida > 2%
            score += 0.1
        
        # Componente de tiempo
        hours_in_position = time_in_position.total_seconds() / 3600
        if hours_in_position > 168:  # Más de una semana
            score += 0.2
        elif hours_in_position > 72:  # Más de 3 días
            score += 0.1
        
        return min(1.0, score)
    
    def _estimate_volatility(self, symbol: str) -> float:
        """
        Estima la volatilidad de un símbolo
        """
        # Volatilidad base por tipo de activo
        volatility_map = {
            'BTC': 0.04,
            'ETH': 0.05,
            'ADA': 0.06,
            'DOT': 0.07,
            'LINK': 0.06
        }
        
        # Buscar coincidencia
        for key, vol in volatility_map.items():
            if key in symbol.upper():
                return vol
        
        return 0.05  # Volatilidad por defecto
    
    def calculate_portfolio_risk(self, positions: Dict[str, Dict]) -> RiskMetrics:
        """
        Calcula métricas de riesgo del portafolio completo
        """
        try:
            if not positions:
                return RiskMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
            
            # Calcular returns del portafolio
            portfolio_values = []
            total_value = self.current_capital
            
            for symbol, pos_data in positions.items():
                position_value = pos_data['size'] * pos_data['current_price']
                total_value += pos_data.get('unrealized_pnl', 0)
            
            portfolio_values.append(total_value)
            
            # Simular returns históricos (simplificado)
            returns = np.random.normal(0.001, 0.02, 100)  # Simulación
            
            # VaR 95% y 99%
            var_95 = np.percentile(returns, 5) * total_value
            var_99 = np.percentile(returns, 1) * total_value
            
            # Expected Shortfall (CVaR)
            tail_returns = returns[returns <= np.percentile(returns, 5)]
            expected_shortfall = np.mean(tail_returns) * total_value if len(tail_returns) > 0 else 0
            
            # Volatilidad
            volatility = np.std(returns) * np.sqrt(365)
            
            # Sharpe ratio
            risk_free_rate = 0.02  # 2% anual
            excess_return = np.mean(returns) * 365 - risk_free_rate
            sharpe_ratio = excess_return / volatility if volatility > 0 else 0
            
            # Sortino ratio
            downside_returns = returns[returns < 0]
            downside_volatility = np.std(downside_returns) * np.sqrt(365) if len(downside_returns) > 0 else volatility
            sortino_ratio = excess_return / downside_volatility if downside_volatility > 0 else 0
            
            # Beta (simplificado)
            market_returns = np.random.normal(0.0008, 0.015, 100)
            beta = np.cov(returns, market_returns)[0, 1] / np.var(market_returns) if np.var(market_returns) > 0 else 1.0
            
            # Riesgo de correlación
            correlation_risk = self._calculate_correlation_risk(positions)
            
            # Riesgo de liquidez
            liquidity_risk = self._calculate_liquidity_risk(positions)
            
            # Max drawdown (simplificado)
            cumulative_returns = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(np.min(drawdowns))
            
            risk_metrics = RiskMetrics(
                var_95=abs(var_95),
                var_99=abs(var_99),
                expected_shortfall=abs(expected_shortfall),
                max_drawdown=max_drawdown,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                beta=beta,
                correlation_risk=correlation_risk,
                liquidity_risk=liquidity_risk
            )
            
            # Guardar en historial
            self.risk_history.append({
                'timestamp': datetime.now(),
                'metrics': risk_metrics,
                'regime': self.current_regime
            })
            
            # Mantener solo últimos 100 registros
            if len(self.risk_history) > 100:
                self.risk_history = self.risk_history[-100:]
            
            return risk_metrics
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando riesgo del portafolio: {e}")
            return RiskMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def _calculate_correlation_risk(self, positions: Dict[str, Dict]) -> float:
        """
        Calcula el riesgo de correlación entre posiciones
        """
        if len(positions) < 2:
            return 0.0
        
        # Matriz de correlación simplificada
        symbols = list(positions.keys())
        correlations = []
        
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols[i+1:], i+1):
                # Correlación estimada basada en tipo de activo
                corr = self._estimate_correlation(symbol1, symbol2)
                correlations.append(abs(corr))
        
        return np.mean(correlations) if correlations else 0.0
    
    def _estimate_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Estima correlación entre dos símbolos
        """
        # Correlaciones típicas en crypto
        crypto_pairs = {
            ('BTC', 'ETH'): 0.8,
            ('BTC', 'ADA'): 0.7,
            ('BTC', 'DOT'): 0.75,
            ('ETH', 'ADA'): 0.85,
            ('ETH', 'DOT'): 0.82,
            ('ADA', 'DOT'): 0.78
        }
        
        # Buscar correlación
        for (s1, s2), corr in crypto_pairs.items():
            if (s1 in symbol1.upper() and s2 in symbol2.upper()) or \
               (s2 in symbol1.upper() and s1 in symbol2.upper()):
                return corr
        
        return 0.6  # Correlación por defecto para crypto
    
    def _calculate_liquidity_risk(self, positions: Dict[str, Dict]) -> float:
        """
        Calcula el riesgo de liquidez del portafolio
        """
        if not positions:
            return 0.0
        
        # Scores de liquidez por símbolo
        liquidity_scores = []
        
        for symbol in positions.keys():
            score = self._get_liquidity_score(symbol)
            liquidity_scores.append(score)
        
        # Riesgo de liquidez = 1 - score promedio
        avg_liquidity = np.mean(liquidity_scores)
        return 1.0 - avg_liquidity
    
    def _get_liquidity_score(self, symbol: str) -> float:
        """
        Obtiene score de liquidez para un símbolo
        """
        # Scores típicos (0-1, donde 1 es más líquido)
        liquidity_map = {
            'BTCUSDT': 0.95,
            'ETHUSDT': 0.90,
            'ADAUSDT': 0.75,
            'DOTUSDT': 0.70,
            'LINKUSDT': 0.65
        }
        
        return liquidity_map.get(symbol, 0.5)  # Score por defecto
    
    def check_risk_alerts(self, positions: Dict[str, Dict], 
                         portfolio_metrics: RiskMetrics) -> List[RiskAlert]:
        """
        Verifica y genera alertas de riesgo
        """
        alerts = []
        
        try:
            # Verificar límites de portafolio
            total_risk = sum(pos.get('risk_percentage', 0) for pos in positions.values())
            
            if total_risk > self.current_limits.max_portfolio_risk:
                alerts.append(RiskAlert(
                    alert_type="portfolio_risk_exceeded",
                    severity=RiskLevel.HIGH,
                    message=f"Riesgo de portafolio excedido: {total_risk*100:.1f}%",
                    symbol=None,
                    current_value=total_risk,
                    threshold=self.current_limits.max_portfolio_risk,
                    timestamp=datetime.now(),
                    action_required=True
                ))
            
            # Verificar VaR
            if portfolio_metrics.var_95 > self.current_capital * 0.1:  # VaR > 10%
                alerts.append(RiskAlert(
                    alert_type="high_var",
                    severity=RiskLevel.MEDIUM,
                    message=f"VaR 95% elevado: ${portfolio_metrics.var_95:.2f}",
                    symbol=None,
                    current_value=portfolio_metrics.var_95,
                    threshold=self.current_capital * 0.1,
                    timestamp=datetime.now(),
                    action_required=False
                ))
            
            # Verificar drawdown
            if portfolio_metrics.max_drawdown > self.current_limits.max_drawdown:
                alerts.append(RiskAlert(
                    alert_type="max_drawdown_exceeded",
                    severity=RiskLevel.VERY_HIGH,
                    message=f"Drawdown máximo excedido: {portfolio_metrics.max_drawdown*100:.1f}%",
                    symbol=None,
                    current_value=portfolio_metrics.max_drawdown,
                    threshold=self.current_limits.max_drawdown,
                    timestamp=datetime.now(),
                    action_required=True
                ))
            
            # Verificar correlación
            if portfolio_metrics.correlation_risk > self.current_limits.max_correlation:
                alerts.append(RiskAlert(
                    alert_type="high_correlation",
                    severity=RiskLevel.MEDIUM,
                    message=f"Alta correlación entre posiciones: {portfolio_metrics.correlation_risk:.2f}",
                    symbol=None,
                    current_value=portfolio_metrics.correlation_risk,
                    threshold=self.current_limits.max_correlation,
                    timestamp=datetime.now(),
                    action_required=False
                ))
            
            # Verificar posiciones individuales
            for symbol, pos_data in positions.items():
                position_risk = self.evaluate_position_risk(
                    symbol, pos_data['size'], pos_data['entry_price'], pos_data['current_price']
                )
                
                if position_risk.risk_score > 0.7:
                    severity = RiskLevel.HIGH if position_risk.risk_score > 0.8 else RiskLevel.MEDIUM
                    alerts.append(RiskAlert(
                        alert_type="high_position_risk",
                        severity=severity,
                        message=f"Alto riesgo en posición {symbol}: score {position_risk.risk_score:.2f}",
                        symbol=symbol,
                        current_value=position_risk.risk_score,
                        threshold=0.7,
                        timestamp=datetime.now(),
                        action_required=position_risk.risk_score > 0.8
                    ))
            
            # Guardar alertas
            self.alert_history.extend(alerts)
            
            # Mantener solo últimas 50 alertas
            if len(self.alert_history) > 50:
                self.alert_history = self.alert_history[-50:]
            
            if alerts:
                self.logger.warning(f"⚠️ Generadas {len(alerts)} alertas de riesgo")
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"❌ Error verificando alertas de riesgo: {e}")
            return []
    
    def suggest_risk_actions(self, alerts: List[RiskAlert]) -> List[str]:
        """
        Sugiere acciones para mitigar riesgos
        """
        actions = []
        
        try:
            for alert in alerts:
                if alert.action_required:
                    if alert.alert_type == "portfolio_risk_exceeded":
                        actions.append("Reducir tamaños de posición o cerrar posiciones menos prometedoras")
                    elif alert.alert_type == "max_drawdown_exceeded":
                        actions.append("Cerrar posiciones perdedoras y reducir exposición general")
                    elif alert.alert_type == "high_position_risk" and alert.symbol:
                        actions.append(f"Revisar stop loss para {alert.symbol} o reducir tamaño de posición")
                    elif alert.alert_type == "regime_change":
                        actions.append("Ajustar estrategia según nuevo régimen de mercado")
                
                elif alert.severity in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
                    if alert.alert_type == "high_var":
                        actions.append("Considerar diversificar más el portafolio")
                    elif alert.alert_type == "high_correlation":
                        actions.append("Buscar activos menos correlacionados para diversificar")
            
            return list(set(actions))  # Eliminar duplicados
            
        except Exception as e:
            self.logger.error(f"❌ Error sugiriendo acciones de riesgo: {e}")
            return []
    
    def update_capital(self, new_capital: float):
        """
        Actualiza el capital actual
        """
        self.current_capital = new_capital
        self.logger.info(f"💰 Capital actualizado: ${new_capital:.2f}")
    
    def get_risk_summary(self) -> Dict:
        """
        Obtiene resumen completo de riesgo
        """
        recent_alerts = [a for a in self.alert_history if 
                        (datetime.now() - a.timestamp).total_seconds() < 3600]  # Últimas 1 hora
        
        return {
            'current_regime': self.current_regime.value,
            'current_capital': self.current_capital,
            'risk_limits': {
                'max_position_size': self.current_limits.max_position_size,
                'max_portfolio_risk': self.current_limits.max_portfolio_risk,
                'stop_loss_percentage': self.current_limits.stop_loss_percentage,
                'max_leverage': self.current_limits.max_leverage
            },
            'recent_alerts': len(recent_alerts),
            'high_priority_alerts': len([a for a in recent_alerts if a.severity in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]]),
            'total_risk_checks': len(self.risk_history),
            'avg_portfolio_volatility': np.mean([r['metrics'].volatility for r in self.risk_history[-10:]]) if self.risk_history else 0
        }

# Función de prueba
def test_dynamic_risk_manager():
    """
    Función de prueba para el gestor de riesgo dinámico
    """
    print("🧪 Iniciando pruebas del Gestor de Riesgo Dinámico...")
    
    # Crear gestor
    risk_manager = DynamicRiskManager(initial_capital=100000)
    
    # Simular datos de mercado
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    market_data = {}
    
    for symbol in symbols:
        # Generar datos sintéticos
        np.random.seed(42)
        periods = 100
        base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 1.5
        
        prices = []
        current_price = base_price
        
        for _ in range(periods):
            change = np.random.normal(0, 0.02)
            current_price *= (1 + change)
            prices.append(current_price)
        
        market_data[symbol] = pd.DataFrame({
            'timestamp': pd.date_range(start='2025-01-01', periods=periods, freq='1H'),
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000, 10000, periods)
        })
    
    # Detectar régimen de mercado
    regime = risk_manager.detect_market_regime(market_data)
    print(f"📊 Régimen detectado: {regime.value}")
    
    # Simular posiciones
    positions = {}
    for symbol in symbols:
        current_price = market_data[symbol]['close'].iloc[-1]
        entry_price = current_price * 0.98  # Entrada 2% más baja
        
        # Calcular tamaño de posición
        stop_loss = entry_price * 0.95
        position_size = risk_manager.calculate_position_size(
            symbol, entry_price, stop_loss, confidence=0.7
        )
        
        positions[symbol] = {
            'size': position_size,
            'entry_price': entry_price,
            'current_price': current_price,
            'unrealized_pnl': (current_price - entry_price) * position_size,
            'risk_percentage': (position_size * current_price) / risk_manager.current_capital
        }
        
        print(f"  {symbol}: Tamaño {position_size:.6f}, PnL ${(current_price - entry_price) * position_size:.2f}")
    
    # Calcular métricas de riesgo
    portfolio_metrics = risk_manager.calculate_portfolio_risk(positions)
    print(f"\n📈 Métricas de Riesgo del Portafolio:")
    print(f"  VaR 95%: ${portfolio_metrics.var_95:.2f}")
    print(f"  VaR 99%: ${portfolio_metrics.var_99:.2f}")
    print(f"  Max Drawdown: {portfolio_metrics.max_drawdown*100:.2f}%")
    print(f"  Volatilidad: {portfolio_metrics.volatility*100:.2f}%")
    print(f"  Sharpe Ratio: {portfolio_metrics.sharpe_ratio:.3f}")
    print(f"  Riesgo de Correlación: {portfolio_metrics.correlation_risk:.3f}")
    
    # Verificar alertas
    alerts = risk_manager.check_risk_alerts(positions, portfolio_metrics)
    print(f"\n⚠️ Alertas de Riesgo: {len(alerts)}")
    
    for alert in alerts:
        print(f"  - {alert.alert_type}: {alert.message} (Severidad: {alert.severity.value})")
    
    # Sugerir acciones
    if alerts:
        actions = risk_manager.suggest_risk_actions(alerts)
        print(f"\n💡 Acciones Sugeridas:")
        for action in actions:
            print(f"  - {action}")
    
    # Mostrar resumen
    summary = risk_manager.get_risk_summary()
    print(f"\n📋 Resumen de Riesgo:")
    print(f"  Régimen actual: {summary['current_regime']}")
    print(f"  Capital: ${summary['current_capital']:,.2f}")
    print(f"  Límite de posición: {summary['risk_limits']['max_position_size']*100:.1f}%")
    print(f"  Límite de portafolio: {summary['risk_limits']['max_portfolio_risk']*100:.1f}%")
    print(f"  Stop loss: {summary['risk_limits']['stop_loss_percentage']*100:.1f}%")
    print(f"  Alertas recientes: {summary['recent_alerts']}")
    
    print("\n✅ Pruebas del Gestor de Riesgo Dinámico completadas")

if __name__ == "__main__":
    test_dynamic_risk_manager()