#!/usr/bin/env python3
"""
Sistema de Gestión de Riesgos Dinámico

Implementa un sistema avanzado de gestión de riesgos que se adapta automáticamente
a los regímenes de mercado detectados, ajustando tamaños de posición, stops dinámicos
y límites de exposición en tiempo real.

Características:
1. Position Sizing adaptativo por régimen
2. Stops dinámicos basados en ATR
3. Límites de drawdown y exposición
4. Correlación de portfolio
5. Gestión de liquidez

Autor: Sistema de Trading Adaptativo
Fecha: 2024
Versión: 1.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

from adaptive_regime_detector import MarketRegime, RegimeSignal
from adaptive_trading_strategies import TradingSignal, SignalType, PositionType

class RiskLevel(Enum):
    """Niveles de riesgo del sistema"""
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"
    EMERGENCY = "EMERGENCY"

class AlertType(Enum):
    """Tipos de alertas de riesgo"""
    DRAWDOWN_WARNING = "DRAWDOWN_WARNING"
    DRAWDOWN_LIMIT = "DRAWDOWN_LIMIT"
    POSITION_LIMIT = "POSITION_LIMIT"
    CORRELATION_WARNING = "CORRELATION_WARNING"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    LIQUIDITY_WARNING = "LIQUIDITY_WARNING"

@dataclass
class RiskParameters:
    """Parámetros de riesgo por régimen"""
    max_position_size: float  # % del capital por posición
    max_total_exposure: float  # % máximo de exposición total
    stop_loss_atr_multiplier: float  # Multiplicador ATR para stops
    take_profit_ratio: float  # Ratio take profit / stop loss
    max_correlation: float  # Correlación máxima entre posiciones
    volatility_adjustment: float  # Factor de ajuste por volatilidad

@dataclass
class Position:
    """Posición de trading con información de riesgo"""
    symbol: str
    position_type: PositionType
    entry_price: float
    current_price: float
    size: float  # Tamaño en unidades base
    value: float  # Valor en moneda base
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_time: pd.Timestamp
    strategy_name: str
    regime: MarketRegime
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    risk_amount: float = 0.0  # Cantidad en riesgo
    atr_at_entry: float = 0.0
    correlation_score: float = 0.0

@dataclass
class RiskAlert:
    """Alerta de riesgo del sistema"""
    alert_type: AlertType
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    message: str
    timestamp: pd.Timestamp
    current_value: float
    threshold: float
    recommended_action: str
    additional_info: Dict = field(default_factory=dict)

@dataclass
class PortfolioMetrics:
    """Métricas del portfolio"""
    total_equity: float
    total_exposure: float
    exposure_percentage: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    max_drawdown: float
    current_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    total_trades: int
    open_positions: int

class DynamicRiskManager:
    """
    Gestor de riesgos dinámico que adapta parámetros según régimen de mercado.
    """
    
    def __init__(self, 
                 initial_capital: float = 10000,
                 max_daily_loss: float = 0.05,  # 5%
                 max_total_drawdown: float = 0.15,  # 15%
                 emergency_stop_drawdown: float = 0.20):  # 20%
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_daily_loss = max_daily_loss
        self.max_total_drawdown = max_total_drawdown
        self.emergency_stop_drawdown = emergency_stop_drawdown
        
        # Posiciones y historial
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.equity_history: List[Tuple[pd.Timestamp, float]] = []
        self.alerts: List[RiskAlert] = []
        
        # Métricas de performance
        self.peak_equity = initial_capital
        self.current_drawdown = 0.0
        self.max_drawdown_reached = 0.0
        self.daily_pnl = 0.0
        self.daily_start_equity = initial_capital
        
        # Parámetros de riesgo por régimen
        self.risk_parameters = {
            MarketRegime.LOW_VOLATILITY: RiskParameters(
                max_position_size=0.15,  # 15% por posición
                max_total_exposure=0.80,  # 80% exposición total
                stop_loss_atr_multiplier=2.0,
                take_profit_ratio=2.0,
                max_correlation=0.70,
                volatility_adjustment=1.0
            ),
            MarketRegime.MEDIUM_VOLATILITY: RiskParameters(
                max_position_size=0.10,  # 10% por posición
                max_total_exposure=0.60,  # 60% exposición total
                stop_loss_atr_multiplier=2.5,
                take_profit_ratio=1.5,
                max_correlation=0.60,
                volatility_adjustment=0.8
            ),
            MarketRegime.HIGH_VOLATILITY: RiskParameters(
                max_position_size=0.05,  # 5% por posición
                max_total_exposure=0.40,  # 40% exposición total
                stop_loss_atr_multiplier=3.0,
                take_profit_ratio=1.2,
                max_correlation=0.50,
                volatility_adjustment=0.6
            )
        }
        
        # Estado del sistema
        self.risk_level = RiskLevel.MODERATE
        self.trading_enabled = True
        self.last_regime = MarketRegime.MEDIUM_VOLATILITY
    
    def calculate_position_size(self, 
                              signal: TradingSignal, 
                              current_atr: float,
                              regime: MarketRegime) -> Tuple[float, float]:
        """
        Calcular tamaño de posición óptimo basado en riesgo y régimen.
        
        Args:
            signal: Señal de trading
            current_atr: ATR actual del activo
            regime: Régimen de mercado actual
            
        Returns:
            Tuple (tamaño_posición, cantidad_en_riesgo)
        """
        if not self.trading_enabled:
            return 0.0, 0.0
        
        # Obtener parámetros de riesgo para el régimen
        risk_params = self.risk_parameters.get(regime, self.risk_parameters[MarketRegime.MEDIUM_VOLATILITY])
        
        # Calcular stop loss dinámico
        if signal.stop_loss:
            stop_distance = abs(signal.entry_price - signal.stop_loss)
        else:
            stop_distance = current_atr * risk_params.stop_loss_atr_multiplier
        
        # Riesgo máximo por posición
        max_risk_amount = self.current_capital * risk_params.max_position_size
        
        # Ajustar por volatilidad del régimen
        adjusted_risk = max_risk_amount * risk_params.volatility_adjustment
        
        # Ajustar por drawdown actual
        drawdown_adjustment = 1.0 - (self.current_drawdown * 2)  # Reducir riesgo si hay drawdown
        drawdown_adjustment = max(0.2, min(1.0, drawdown_adjustment))
        
        final_risk_amount = adjusted_risk * drawdown_adjustment
        
        # Calcular tamaño de posición
        if stop_distance > 0:
            position_size = final_risk_amount / stop_distance
        else:
            position_size = 0.0
        
        # Verificar límites de exposición
        current_exposure = self.get_total_exposure_percentage()
        if current_exposure >= risk_params.max_total_exposure:
            return 0.0, 0.0
        
        return position_size, final_risk_amount
    
    def validate_new_position(self, 
                            signal: TradingSignal, 
                            position_size: float,
                            regime: MarketRegime) -> Tuple[bool, str]:
        """
        Validar si se puede abrir una nueva posición.
        
        Args:
            signal: Señal de trading
            position_size: Tamaño de posición propuesto
            regime: Régimen de mercado actual
            
        Returns:
            Tuple (es_válida, razón)
        """
        # Verificar si el trading está habilitado
        if not self.trading_enabled:
            return False, "Trading deshabilitado por gestión de riesgos"
        
        # Verificar drawdown
        if self.current_drawdown >= self.max_total_drawdown:
            return False, f"Drawdown máximo alcanzado: {self.current_drawdown:.2%}"
        
        # Verificar pérdida diaria
        daily_loss_pct = abs(self.daily_pnl) / self.daily_start_equity
        if self.daily_pnl < 0 and daily_loss_pct >= self.max_daily_loss:
            return False, f"Límite de pérdida diaria alcanzado: {daily_loss_pct:.2%}"
        
        # Verificar exposición total
        risk_params = self.risk_parameters.get(regime, self.risk_parameters[MarketRegime.MEDIUM_VOLATILITY])
        current_exposure = self.get_total_exposure_percentage()
        
        position_value = position_size * signal.entry_price
        new_exposure = (self.get_total_exposure() + position_value) / self.current_capital
        
        if new_exposure > risk_params.max_total_exposure:
            return False, f"Límite de exposición excedido: {new_exposure:.2%} > {risk_params.max_total_exposure:.2%}"
        
        # Verificar correlación (simplificado)
        if len(self.positions) > 0:
            correlation_risk = self.calculate_correlation_risk(signal)
            if correlation_risk > risk_params.max_correlation:
                return False, f"Riesgo de correlación alto: {correlation_risk:.2%}"
        
        return True, "Posición válida"
    
    def open_position(self, 
                     signal: TradingSignal, 
                     current_atr: float,
                     regime: MarketRegime,
                     symbol: str = "BTC-USD") -> Optional[Position]:
        """
        Abrir nueva posición con gestión de riesgos.
        
        Args:
            signal: Señal de trading
            current_atr: ATR actual
            regime: Régimen de mercado
            symbol: Símbolo del activo
            
        Returns:
            Posición creada o None si no se pudo abrir
        """
        # Calcular tamaño de posición
        position_size, risk_amount = self.calculate_position_size(signal, current_atr, regime)
        
        if position_size <= 0:
            return None
        
        # Validar posición
        is_valid, reason = self.validate_new_position(signal, position_size, regime)
        if not is_valid:
            self.add_alert(AlertType.POSITION_LIMIT, "MEDIUM", reason, signal.timestamp)
            return None
        
        # Determinar tipo de posición
        position_type = PositionType.LONG if signal.signal_type == SignalType.BUY else PositionType.SHORT
        
        # Crear posición
        position = Position(
            symbol=symbol,
            position_type=position_type,
            entry_price=signal.entry_price,
            current_price=signal.entry_price,
            size=position_size,
            value=position_size * signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            entry_time=signal.timestamp,
            strategy_name=signal.strategy_name,
            regime=regime,
            risk_amount=risk_amount,
            atr_at_entry=current_atr
        )
        
        # Agregar a posiciones activas
        position_id = f"{symbol}_{signal.timestamp.strftime('%Y%m%d_%H%M%S')}"
        self.positions[position_id] = position
        
        return position
    
    def update_positions(self, current_prices: Dict[str, float], timestamp: pd.Timestamp):
        """
        Actualizar todas las posiciones con precios actuales.
        
        Args:
            current_prices: Diccionario {símbolo: precio_actual}
            timestamp: Timestamp actual
        """
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            symbol = position.symbol
            if symbol not in current_prices:
                continue
            
            current_price = current_prices[symbol]
            position.current_price = current_price
            
            # Calcular PnL
            if position.position_type == PositionType.LONG:
                position.unrealized_pnl = (current_price - position.entry_price) * position.size
            else:  # SHORT
                position.unrealized_pnl = (position.entry_price - current_price) * position.size
            
            position.unrealized_pnl_pct = position.unrealized_pnl / position.value
            
            # Verificar stops
            should_close, reason = self.check_stop_conditions(position, current_price, timestamp)
            if should_close:
                positions_to_close.append((position_id, reason))
        
        # Cerrar posiciones que alcanzaron stops
        for position_id, reason in positions_to_close:
            self.close_position(position_id, timestamp, reason)
        
        # Actualizar métricas del portfolio
        self.update_portfolio_metrics(timestamp)
    
    def check_stop_conditions(self, position: Position, current_price: float, timestamp: pd.Timestamp) -> Tuple[bool, str]:
        """
        Verificar condiciones de stop loss y take profit.
        
        Args:
            position: Posición a verificar
            current_price: Precio actual
            timestamp: Timestamp actual
            
        Returns:
            Tuple (debe_cerrar, razón)
        """
        # Stop Loss
        if position.stop_loss:
            if position.position_type == PositionType.LONG and current_price <= position.stop_loss:
                return True, "Stop Loss alcanzado"
            elif position.position_type == PositionType.SHORT and current_price >= position.stop_loss:
                return True, "Stop Loss alcanzado"
        
        # Take Profit
        if position.take_profit:
            if position.position_type == PositionType.LONG and current_price >= position.take_profit:
                return True, "Take Profit alcanzado"
            elif position.position_type == PositionType.SHORT and current_price <= position.take_profit:
                return True, "Take Profit alcanzado"
        
        # Stop de emergencia por drawdown
        if self.current_drawdown >= self.emergency_stop_drawdown:
            return True, "Stop de emergencia por drawdown"
        
        return False, ""
    
    def close_position(self, position_id: str, timestamp: pd.Timestamp, reason: str = "Manual") -> Optional[Position]:
        """
        Cerrar posición y actualizar capital.
        
        Args:
            position_id: ID de la posición
            timestamp: Timestamp de cierre
            reason: Razón del cierre
            
        Returns:
            Posición cerrada o None si no existe
        """
        if position_id not in self.positions:
            return None
        
        position = self.positions.pop(position_id)
        
        # Actualizar capital
        self.current_capital += position.unrealized_pnl
        
        # Agregar a historial
        position.additional_info = {'close_reason': reason, 'close_time': timestamp}
        self.closed_positions.append(position)
        
        return position
    
    def update_portfolio_metrics(self, timestamp: pd.Timestamp):
        """
        Actualizar métricas del portfolio.
        
        Args:
            timestamp: Timestamp actual
        """
        # Calcular equity total
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_equity = self.current_capital + total_unrealized_pnl
        
        # Actualizar peak y drawdown
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity
        
        self.current_drawdown = (self.peak_equity - total_equity) / self.peak_equity
        self.max_drawdown_reached = max(self.max_drawdown_reached, self.current_drawdown)
        
        # Actualizar PnL diario
        self.daily_pnl = total_equity - self.daily_start_equity
        
        # Agregar a historial
        self.equity_history.append((timestamp, total_equity))
        
        # Verificar alertas
        self.check_risk_alerts(timestamp)
        
        # Actualizar nivel de riesgo
        self.update_risk_level()
    
    def check_risk_alerts(self, timestamp: pd.Timestamp):
        """
        Verificar y generar alertas de riesgo.
        
        Args:
            timestamp: Timestamp actual
        """
        # Alerta de drawdown
        if self.current_drawdown >= self.max_total_drawdown * 0.8:  # 80% del límite
            self.add_alert(
                AlertType.DRAWDOWN_WARNING, 
                "HIGH",
                f"Drawdown cerca del límite: {self.current_drawdown:.2%}",
                timestamp
            )
        
        if self.current_drawdown >= self.max_total_drawdown:
            self.add_alert(
                AlertType.DRAWDOWN_LIMIT,
                "CRITICAL",
                f"Límite de drawdown alcanzado: {self.current_drawdown:.2%}",
                timestamp
            )
            self.trading_enabled = False
        
        # Alerta de pérdida diaria
        daily_loss_pct = abs(self.daily_pnl) / self.daily_start_equity if self.daily_start_equity > 0 else 0
        if self.daily_pnl < 0 and daily_loss_pct >= self.max_daily_loss * 0.8:
            self.add_alert(
                AlertType.DRAWDOWN_WARNING,
                "MEDIUM",
                f"Pérdida diaria alta: {daily_loss_pct:.2%}",
                timestamp
            )
    
    def add_alert(self, alert_type: AlertType, severity: str, message: str, timestamp: pd.Timestamp, **kwargs):
        """
        Agregar alerta al sistema.
        
        Args:
            alert_type: Tipo de alerta
            severity: Severidad (LOW, MEDIUM, HIGH, CRITICAL)
            message: Mensaje de la alerta
            timestamp: Timestamp de la alerta
            **kwargs: Información adicional
        """
        alert = RiskAlert(
            alert_type=alert_type,
            severity=severity,
            message=message,
            timestamp=timestamp,
            current_value=kwargs.get('current_value', 0.0),
            threshold=kwargs.get('threshold', 0.0),
            recommended_action=kwargs.get('recommended_action', 'Revisar posiciones'),
            additional_info=kwargs
        )
        
        self.alerts.append(alert)
        
        # Imprimir alertas críticas
        if severity == "CRITICAL":
            print(f"🚨 ALERTA CRÍTICA: {message}")
    
    def update_risk_level(self):
        """
        Actualizar nivel de riesgo del sistema basado en métricas actuales.
        """
        if self.current_drawdown >= self.emergency_stop_drawdown:
            self.risk_level = RiskLevel.EMERGENCY
            self.trading_enabled = False
        elif self.current_drawdown >= self.max_total_drawdown * 0.7:
            self.risk_level = RiskLevel.CONSERVATIVE
        elif self.current_drawdown >= self.max_total_drawdown * 0.4:
            self.risk_level = RiskLevel.MODERATE
        else:
            self.risk_level = RiskLevel.AGGRESSIVE
    
    def get_total_exposure(self) -> float:
        """
        Obtener exposición total en valor absoluto.
        
        Returns:
            Valor total de exposición
        """
        return sum(pos.value for pos in self.positions.values())
    
    def get_total_exposure_percentage(self) -> float:
        """
        Obtener exposición total como porcentaje del capital.
        
        Returns:
            Porcentaje de exposición
        """
        if self.current_capital <= 0:
            return 0.0
        return self.get_total_exposure() / self.current_capital
    
    def calculate_correlation_risk(self, signal: TradingSignal) -> float:
        """
        Calcular riesgo de correlación (simplificado).
        
        Args:
            signal: Nueva señal a evaluar
            
        Returns:
            Score de correlación (0-1)
        """
        if not self.positions:
            return 0.0
        
        # Simplificación: asumir correlación alta si misma estrategia y régimen
        same_strategy_count = sum(
            1 for pos in self.positions.values() 
            if pos.strategy_name == signal.strategy_name and pos.regime == signal.regime
        )
        
        correlation_score = same_strategy_count / (len(self.positions) + 1)
        return correlation_score
    
    def get_portfolio_metrics(self) -> PortfolioMetrics:
        """
        Obtener métricas completas del portfolio.
        
        Returns:
            Objeto PortfolioMetrics con todas las métricas
        """
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_equity = self.current_capital + total_unrealized_pnl
        
        # Calcular métricas de trading
        winning_trades = [pos for pos in self.closed_positions if pos.unrealized_pnl > 0]
        losing_trades = [pos for pos in self.closed_positions if pos.unrealized_pnl < 0]
        
        win_rate = len(winning_trades) / len(self.closed_positions) if self.closed_positions else 0
        avg_win = np.mean([pos.unrealized_pnl for pos in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([abs(pos.unrealized_pnl) for pos in losing_trades]) if losing_trades else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Calcular Sharpe ratio (simplificado)
        if len(self.equity_history) > 1:
            returns = []
            for i in range(1, len(self.equity_history)):
                prev_equity = self.equity_history[i-1][1]
                curr_equity = self.equity_history[i][1]
                returns.append((curr_equity - prev_equity) / prev_equity)
            
            if returns:
                sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return PortfolioMetrics(
            total_equity=total_equity,
            total_exposure=self.get_total_exposure(),
            exposure_percentage=self.get_total_exposure_percentage(),
            unrealized_pnl=total_unrealized_pnl,
            unrealized_pnl_pct=total_unrealized_pnl / self.initial_capital,
            max_drawdown=self.max_drawdown_reached,
            current_drawdown=self.current_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            total_trades=len(self.closed_positions),
            open_positions=len(self.positions)
        )
    
    def reset_daily_metrics(self):
        """
        Resetear métricas diarias (llamar al inicio de cada día).
        """
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        self.daily_start_equity = self.current_capital + total_unrealized_pnl
        self.daily_pnl = 0.0
    
    def get_risk_report(self) -> Dict:
        """
        Generar reporte completo de riesgos.
        
        Returns:
            Diccionario con reporte de riesgos
        """
        metrics = self.get_portfolio_metrics()
        
        # Alertas recientes (últimas 24 horas)
        recent_alerts = [
            alert for alert in self.alerts 
            if alert.timestamp >= (pd.Timestamp.now() - timedelta(days=1))
        ]
        
        return {
            'risk_level': self.risk_level.value,
            'trading_enabled': self.trading_enabled,
            'portfolio_metrics': {
                'total_equity': metrics.total_equity,
                'current_drawdown': metrics.current_drawdown,
                'max_drawdown': metrics.max_drawdown,
                'exposure_percentage': metrics.exposure_percentage,
                'open_positions': metrics.open_positions,
                'win_rate': metrics.win_rate,
                'sharpe_ratio': metrics.sharpe_ratio
            },
            'risk_limits': {
                'max_daily_loss': self.max_daily_loss,
                'max_total_drawdown': self.max_total_drawdown,
                'emergency_stop_drawdown': self.emergency_stop_drawdown
            },
            'recent_alerts': [
                {
                    'type': alert.alert_type.value,
                    'severity': alert.severity,
                    'message': alert.message,
                    'timestamp': alert.timestamp.isoformat()
                }
                for alert in recent_alerts
            ],
            'positions_summary': {
                'total_positions': len(self.positions),
                'long_positions': sum(1 for pos in self.positions.values() if pos.position_type == PositionType.LONG),
                'short_positions': sum(1 for pos in self.positions.values() if pos.position_type == PositionType.SHORT),
                'total_risk_amount': sum(pos.risk_amount for pos in self.positions.values())
            }
        }

if __name__ == "__main__":
    print("🛡️ Sistema de Gestión de Riesgos Dinámico")
    print("="*60)
    print("📊 Position Sizing adaptativo por régimen")
    print("🎯 Stops dinámicos basados en ATR")
    print("⚠️ Límites de drawdown y exposición")
    print("🔗 Control de correlación de portfolio")
    print("="*60)
    
    # Ejemplo de uso
    print("\n💡 Ejemplo de uso:")
    print("""
    # Crear gestor de riesgos
    risk_manager = DynamicRiskManager(initial_capital=10000)
    
    # Abrir posición
    position = risk_manager.open_position(signal, current_atr, regime)
    
    # Actualizar posiciones
    risk_manager.update_positions({'BTC-USD': 45000}, pd.Timestamp.now())
    
    # Obtener reporte de riesgos
    report = risk_manager.get_risk_report()
    print(report)
    """)