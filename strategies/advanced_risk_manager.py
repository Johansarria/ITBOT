# strategies/advanced_risk_manager.py

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Niveles de riesgo"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

class PositionStatus(Enum):
    """Estados de posición"""
    OPEN = "open"
    CLOSED = "closed"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"

@dataclass
class RiskMetrics:
    """Métricas de riesgo en tiempo real"""
    portfolio_var_95: float = 0.0  # Value at Risk 95%
    portfolio_var_99: float = 0.0  # Value at Risk 99%
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    volatility: float = 0.0
    correlation_risk: float = 0.0
    concentration_risk: float = 0.0
    leverage_ratio: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Position:
    """Posición con gestión de riesgo avanzada"""
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    entry_price: float
    current_price: float
    entry_time: datetime
    
    # Stop Loss dinámico
    initial_stop_loss: float
    current_stop_loss: float
    stop_loss_type: str = "fixed"  # 'fixed', 'trailing', 'atr'
    
    # Take Profit
    take_profit_levels: List[Tuple[float, float]] = field(default_factory=list)  # (price, quantity_pct)
    
    # Métricas de riesgo
    max_risk_pct: float = 0.02  # 2% máximo riesgo por posición
    atr_multiplier: float = 2.0
    trailing_stop_pct: float = 0.05  # 5% trailing stop
    
    # Estado
    status: PositionStatus = PositionStatus.OPEN
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Tracking
    highest_price: float = 0.0  # Para trailing stop
    lowest_price: float = float('inf')  # Para trailing stop en short
    
    def update_price(self, new_price: float, atr: Optional[float] = None):
        """Actualiza precio y métricas de la posición"""
        self.current_price = new_price
        
        # Actualizar PnL
        if self.side == 'BUY':
            self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
            self.unrealized_pnl_pct = (new_price - self.entry_price) / self.entry_price
            
            # Tracking para trailing stop
            if new_price > self.highest_price:
                self.highest_price = new_price
                
                # Actualizar trailing stop
                if self.stop_loss_type == "trailing":
                    new_stop = self.highest_price * (1 - self.trailing_stop_pct)
                    self.current_stop_loss = max(self.current_stop_loss, new_stop)
                elif self.stop_loss_type == "atr" and atr:
                    new_stop = new_price - (atr * self.atr_multiplier)
                    self.current_stop_loss = max(self.current_stop_loss, new_stop)
        
        else:  # SELL
            self.unrealized_pnl = (self.entry_price - new_price) * self.quantity
            self.unrealized_pnl_pct = (self.entry_price - new_price) / self.entry_price
            
            # Tracking para trailing stop
            if new_price < self.lowest_price:
                self.lowest_price = new_price
                
                # Actualizar trailing stop
                if self.stop_loss_type == "trailing":
                    new_stop = self.lowest_price * (1 + self.trailing_stop_pct)
                    self.current_stop_loss = min(self.current_stop_loss, new_stop)
                elif self.stop_loss_type == "atr" and atr:
                    new_stop = new_price + (atr * self.atr_multiplier)
                    self.current_stop_loss = min(self.current_stop_loss, new_stop)
    
    def should_close_position(self) -> Tuple[bool, str]:
        """Verifica si la posición debe cerrarse"""
        if self.side == 'BUY':
            # Stop Loss
            if self.current_price <= self.current_stop_loss:
                return True, "stop_loss"
            
            # Take Profit
            for tp_price, tp_qty_pct in self.take_profit_levels:
                if self.current_price >= tp_price:
                    return True, f"take_profit_{tp_price}"
        
        else:  # SELL
            # Stop Loss
            if self.current_price >= self.current_stop_loss:
                return True, "stop_loss"
            
            # Take Profit
            for tp_price, tp_qty_pct in self.take_profit_levels:
                if self.current_price <= tp_price:
                    return True, f"take_profit_{tp_price}"
        
        return False, ""

class AdvancedRiskManager:
    """Gestor de riesgo avanzado para estrategia spot"""
    
    def __init__(self, initial_capital: float = 500.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.available_capital = initial_capital
        
        # Límites de riesgo
        self.max_portfolio_risk = 0.10  # 10% máximo riesgo total
        self.max_position_risk = 0.02   # 2% máximo por posición
        self.max_correlation_exposure = 0.60  # 60% máximo en activos correlacionados
        self.max_single_asset_weight = 0.25   # 25% máximo por activo
        
        # Configuración de stop loss
        self.default_stop_loss_pct = 0.02  # 2%
        self.atr_stop_multiplier = 2.0
        self.trailing_stop_pct = 0.05  # 5%
        
        # Posiciones activas
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        
        # Métricas históricas
        self.daily_returns: List[float] = []
        self.portfolio_values: List[Tuple[datetime, float]] = []
        self.drawdown_history: List[float] = []
        
        # Correlaciones entre activos
        self.correlation_matrix: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self.price_history: Dict[str, List[float]] = defaultdict(list)
        
        logger.info(f"Advanced Risk Manager inicializado - Capital: ${initial_capital}")
    
    def calculate_position_size(self, symbol: str, entry_price: float, stop_loss_price: float, 
                              signal_strength: float = 1.0, max_risk_override: Optional[float] = None) -> Tuple[float, float]:
        """Calcula tamaño de posición basado en riesgo"""
        
        # Riesgo máximo por posición
        max_risk = max_risk_override or self.max_position_risk
        risk_amount = self.available_capital * max_risk
        
        # Ajuste por fuerza de señal
        risk_amount *= signal_strength
        
        # Calcular tamaño basado en stop loss
        price_diff = abs(entry_price - stop_loss_price)
        if price_diff == 0:
            return 0.0, 0.0
        
        position_size = risk_amount / price_diff
        position_value = position_size * entry_price
        
        # Verificar límites
        max_position_value = self.available_capital * self.max_single_asset_weight
        if position_value > max_position_value:
            position_size = max_position_value / entry_price
            position_value = max_position_value
        
        # Verificar capital disponible
        if position_value > self.available_capital:
            position_size = self.available_capital / entry_price
            position_value = self.available_capital
        
        return position_size, position_value
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, side: str, 
                          atr: Optional[float] = None, stop_type: str = "fixed") -> float:
        """Calcula stop loss dinámico"""
        
        if stop_type == "fixed":
            if side == 'BUY':
                return entry_price * (1 - self.default_stop_loss_pct)
            else:
                return entry_price * (1 + self.default_stop_loss_pct)
        
        elif stop_type == "atr" and atr:
            if side == 'BUY':
                return entry_price - (atr * self.atr_stop_multiplier)
            else:
                return entry_price + (atr * self.atr_stop_multiplier)
        
        elif stop_type == "trailing":
            # Inicial igual a fixed, se ajustará dinámicamente
            if side == 'BUY':
                return entry_price * (1 - self.trailing_stop_pct)
            else:
                return entry_price * (1 + self.trailing_stop_pct)
        
        # Fallback a fixed
        return self.calculate_stop_loss(symbol, entry_price, side, atr, "fixed")
    
    def calculate_take_profit_levels(self, entry_price: float, side: str, 
                                   risk_reward_ratios: List[float] = [1.5, 2.0, 3.0]) -> List[Tuple[float, float]]:
        """Calcula niveles de take profit"""
        stop_loss = self.calculate_stop_loss("", entry_price, side)
        risk_per_share = abs(entry_price - stop_loss)
        
        tp_levels = []
        quantity_splits = [0.3, 0.4, 0.3]  # 30%, 40%, 30%
        
        for i, rr_ratio in enumerate(risk_reward_ratios):
            if side == 'BUY':
                tp_price = entry_price + (risk_per_share * rr_ratio)
            else:
                tp_price = entry_price - (risk_per_share * rr_ratio)
            
            tp_quantity_pct = quantity_splits[i] if i < len(quantity_splits) else 0.1
            tp_levels.append((tp_price, tp_quantity_pct))
        
        return tp_levels
    
    def open_position(self, symbol: str, side: str, quantity: float, entry_price: float, 
                     atr: Optional[float] = None, stop_type: str = "trailing") -> bool:
        """Abre nueva posición con gestión de riesgo"""
        
        # Verificar si ya existe posición
        if symbol in self.positions:
            logger.warning(f"Posición ya existe para {symbol}")
            return False
        
        # Calcular stop loss
        stop_loss = self.calculate_stop_loss(symbol, entry_price, side, atr, stop_type)
        
        # Calcular take profit levels
        tp_levels = self.calculate_take_profit_levels(entry_price, side)
        
        # Crear posición
        position = Position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            current_price=entry_price,
            entry_time=datetime.now(),
            initial_stop_loss=stop_loss,
            current_stop_loss=stop_loss,
            stop_loss_type=stop_type,
            take_profit_levels=tp_levels,
            highest_price=entry_price if side == 'BUY' else 0.0,
            lowest_price=entry_price if side == 'SELL' else float('inf')
        )
        
        # Verificar límites de riesgo
        position_value = quantity * entry_price
        if not self._check_risk_limits(symbol, position_value):
            logger.warning(f"Posición {symbol} rechazada por límites de riesgo")
            return False
        
        # Añadir posición
        self.positions[symbol] = position
        self.available_capital -= position_value
        
        logger.info(f"Posición abierta: {symbol} {side} {quantity:.4f} @ ${entry_price:.4f}")
        logger.info(f"Stop Loss: ${stop_loss:.4f}, Take Profits: {len(tp_levels)} niveles")
        
        return True
    
    def update_position(self, symbol: str, current_price: float, atr: Optional[float] = None) -> Optional[str]:
        """Actualiza posición y verifica condiciones de cierre"""
        
        if symbol not in self.positions:
            return None
        
        position = self.positions[symbol]
        position.update_price(current_price, atr)
        
        # Verificar condiciones de cierre
        should_close, reason = position.should_close_position()
        
        if should_close:
            return self.close_position(symbol, reason)
        
        return None
    
    def close_position(self, symbol: str, reason: str = "manual") -> str:
        """Cierra posición"""
        
        if symbol not in self.positions:
            return f"Posición {symbol} no encontrada"
        
        position = self.positions[symbol]
        
        # Calcular PnL final
        final_pnl = position.unrealized_pnl
        final_pnl_pct = position.unrealized_pnl_pct
        
        # Actualizar capital
        position_value = position.quantity * position.current_price
        self.available_capital += position_value
        self.current_capital += final_pnl
        
        # Marcar como cerrada
        position.status = PositionStatus.CLOSED
        if reason.startswith("stop_loss"):
            position.status = PositionStatus.STOP_LOSS
        elif reason.startswith("take_profit"):
            position.status = PositionStatus.TAKE_PROFIT
        elif reason.startswith("trailing"):
            position.status = PositionStatus.TRAILING_STOP
        
        # Mover a historial
        self.closed_positions.append(position)
        del self.positions[symbol]
        
        logger.info(f"Posición cerrada: {symbol} - Razón: {reason}")
        logger.info(f"PnL: ${final_pnl:.2f} ({final_pnl_pct:.2%})")
        
        return f"Posición {symbol} cerrada: {reason}, PnL: ${final_pnl:.2f}"
    
    def _check_risk_limits(self, symbol: str, position_value: float) -> bool:
        """Verifica límites de riesgo antes de abrir posición"""
        
        # Verificar peso máximo por activo
        weight = position_value / self.current_capital
        if weight > self.max_single_asset_weight:
            logger.warning(f"Peso {weight:.2%} excede límite {self.max_single_asset_weight:.2%}")
            return False
        
        # Verificar capital disponible
        if position_value > self.available_capital:
            logger.warning(f"Valor posición ${position_value:.2f} excede capital disponible ${self.available_capital:.2f}")
            return False
        
        # Verificar correlación
        if not self._check_correlation_limits(symbol, position_value):
            return False
        
        return True
    
    def _check_correlation_limits(self, new_symbol: str, new_position_value: float) -> bool:
        """Verifica límites de correlación"""
        
        if not self.positions:  # Primera posición
            return True
        
        # Calcular exposición correlacionada
        correlated_exposure = 0.0
        
        for existing_symbol, position in self.positions.items():
            correlation = self.get_correlation(new_symbol, existing_symbol)
            if abs(correlation) > 0.7:  # Alta correlación
                existing_value = position.quantity * position.current_price
                correlated_exposure += existing_value
        
        total_correlated = correlated_exposure + new_position_value
        correlation_weight = total_correlated / self.current_capital
        
        if correlation_weight > self.max_correlation_exposure:
            logger.warning(f"Exposición correlacionada {correlation_weight:.2%} excede límite {self.max_correlation_exposure:.2%}")
            return False
        
        return True
    
    def update_price_history(self, symbol: str, price: float):
        """Actualiza historial de precios para correlaciones"""
        self.price_history[symbol].append(price)
        
        # Mantener solo últimos 100 precios
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        # Actualizar correlaciones si hay suficientes datos
        if len(self.price_history[symbol]) >= 30:
            self._update_correlations(symbol)
    
    def _update_correlations(self, symbol: str):
        """Actualiza matriz de correlaciones"""
        for other_symbol, other_prices in self.price_history.items():
            if other_symbol != symbol and len(other_prices) >= 30:
                # Calcular correlación de retornos
                returns1 = np.diff(self.price_history[symbol][-30:]) / self.price_history[symbol][-31:-1]
                returns2 = np.diff(other_prices[-30:]) / other_prices[-31:-1]
                
                correlation = np.corrcoef(returns1, returns2)[0, 1]
                if not np.isnan(correlation):
                    self.correlation_matrix[symbol][other_symbol] = correlation
                    self.correlation_matrix[other_symbol][symbol] = correlation
    
    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Obtiene correlación entre dos símbolos"""
        return self.correlation_matrix.get(symbol1, {}).get(symbol2, 0.0)
    
    def calculate_portfolio_metrics(self) -> RiskMetrics:
        """Calcula métricas de riesgo del portafolio"""
        
        # Valor total del portafolio
        total_value = self.available_capital
        for position in self.positions.values():
            total_value += position.quantity * position.current_price
        
        # Retornos diarios
        if len(self.portfolio_values) > 1:
            returns = []
            for i in range(1, len(self.portfolio_values)):
                prev_value = self.portfolio_values[i-1][1]
                curr_value = self.portfolio_values[i][1]
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
            
            self.daily_returns = returns
        
        # Calcular métricas
        metrics = RiskMetrics()
        
        if self.daily_returns:
            returns_array = np.array(self.daily_returns)
            
            # VaR
            metrics.portfolio_var_95 = np.percentile(returns_array, 5) * total_value
            metrics.portfolio_var_99 = np.percentile(returns_array, 1) * total_value
            
            # Volatilidad
            metrics.volatility = np.std(returns_array) * np.sqrt(252)  # Anualizada
            
            # Sharpe Ratio (asumiendo risk-free rate = 0)
            if metrics.volatility > 0:
                metrics.sharpe_ratio = np.mean(returns_array) * np.sqrt(252) / metrics.volatility
            
            # Sortino Ratio
            negative_returns = returns_array[returns_array < 0]
            if len(negative_returns) > 0:
                downside_deviation = np.std(negative_returns) * np.sqrt(252)
                if downside_deviation > 0:
                    metrics.sortino_ratio = np.mean(returns_array) * np.sqrt(252) / downside_deviation
        
        # Drawdown
        if self.portfolio_values:
            peak = self.initial_capital
            current_dd = 0.0
            max_dd = 0.0
            
            for _, value in self.portfolio_values:
                if value > peak:
                    peak = value
                
                current_dd = (peak - value) / peak
                max_dd = max(max_dd, current_dd)
            
            metrics.current_drawdown = current_dd
            metrics.max_drawdown = max_dd
            
            # Calmar Ratio
            if max_dd > 0 and self.daily_returns:
                annual_return = np.mean(self.daily_returns) * 252
                metrics.calmar_ratio = annual_return / max_dd
        
        # Riesgo de concentración
        if self.positions:
            position_weights = []
            for position in self.positions.values():
                weight = (position.quantity * position.current_price) / total_value
                position_weights.append(weight)
            
            # Índice Herfindahl-Hirschman
            hhi = sum(w**2 for w in position_weights)
            metrics.concentration_risk = hhi
        
        # Nivel de riesgo general
        risk_score = 0
        if metrics.volatility > 0.3: risk_score += 1
        if metrics.max_drawdown > 0.15: risk_score += 1
        if metrics.concentration_risk > 0.5: risk_score += 1
        if len(self.positions) > 5: risk_score += 1
        
        if risk_score >= 3:
            metrics.risk_level = RiskLevel.EXTREME
        elif risk_score >= 2:
            metrics.risk_level = RiskLevel.HIGH
        elif risk_score >= 1:
            metrics.risk_level = RiskLevel.MEDIUM
        else:
            metrics.risk_level = RiskLevel.LOW
        
        # Actualizar historial
        self.portfolio_values.append((datetime.now(), total_value))
        
        # Mantener solo últimos 100 valores
        if len(self.portfolio_values) > 100:
            self.portfolio_values = self.portfolio_values[-100:]
        
        return metrics
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Resumen completo de riesgo"""
        metrics = self.calculate_portfolio_metrics()
        
        total_value = self.available_capital
        for position in self.positions.values():
            total_value += position.quantity * position.current_price
        
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            'capital_inicial': self.initial_capital,
            'capital_actual': self.current_capital,
            'capital_disponible': self.available_capital,
            'valor_total_portafolio': total_value,
            'pnl_no_realizado': total_unrealized_pnl,
            'retorno_total': (total_value - self.initial_capital) / self.initial_capital,
            
            'posiciones_activas': len(self.positions),
            'posiciones_cerradas': len(self.closed_positions),
            
            'metricas_riesgo': {
                'var_95': metrics.portfolio_var_95,
                'var_99': metrics.portfolio_var_99,
                'max_drawdown': metrics.max_drawdown,
                'drawdown_actual': metrics.current_drawdown,
                'volatilidad': metrics.volatility,
                'sharpe_ratio': metrics.sharpe_ratio,
                'sortino_ratio': metrics.sortino_ratio,
                'calmar_ratio': metrics.calmar_ratio,
                'concentracion': metrics.concentration_risk,
                'nivel_riesgo': metrics.risk_level.value
            },
            
            'limites_riesgo': {
                'max_riesgo_portafolio': self.max_portfolio_risk,
                'max_riesgo_posicion': self.max_position_risk,
                'max_peso_activo': self.max_single_asset_weight,
                'max_correlacion': self.max_correlation_exposure
            },
            
            'posiciones_detalle': {
                symbol: {
                    'lado': pos.side,
                    'cantidad': pos.quantity,
                    'precio_entrada': pos.entry_price,
                    'precio_actual': pos.current_price,
                    'stop_loss': pos.current_stop_loss,
                    'pnl': pos.unrealized_pnl,
                    'pnl_pct': pos.unrealized_pnl_pct,
                    'valor': pos.quantity * pos.current_price
                }
                for symbol, pos in self.positions.items()
            }
        }

if __name__ == "__main__":
    # Ejemplo de uso
    risk_manager = AdvancedRiskManager(initial_capital=500.0)
    
    # Simular apertura de posiciones
    print("=== APERTURA DE POSICIONES ===")
    
    # Posición BNB
    bnb_entry = 300.0
    bnb_stop = risk_manager.calculate_stop_loss("BNBUSDT", bnb_entry, "BUY", stop_type="trailing")
    bnb_size, bnb_value = risk_manager.calculate_position_size("BNBUSDT", bnb_entry, bnb_stop, 0.8)
    
    print(f"BNB - Tamaño: {bnb_size:.4f}, Valor: ${bnb_value:.2f}, Stop: ${bnb_stop:.2f}")
    
    success = risk_manager.open_position("BNBUSDT", "BUY", bnb_size, bnb_entry, stop_type="trailing")
    print(f"Posición BNB abierta: {success}")
    
    # Posición SOL
    sol_entry = 100.0
    sol_stop = risk_manager.calculate_stop_loss("SOLUSDT", sol_entry, "BUY", stop_type="atr")
    sol_size, sol_value = risk_manager.calculate_position_size("SOLUSDT", sol_entry, sol_stop, 0.9)
    
    print(f"SOL - Tamaño: {sol_size:.4f}, Valor: ${sol_value:.2f}, Stop: ${sol_stop:.2f}")
    
    success = risk_manager.open_position("SOLUSDT", "BUY", sol_size, sol_entry, atr=2.5, stop_type="atr")
    print(f"Posición SOL abierta: {success}")
    
    # Simular actualizaciones de precio
    print("\n=== ACTUALIZACIONES DE PRECIO ===")
    
    # BNB sube
    risk_manager.update_price_history("BNBUSDT", 305.0)
    result = risk_manager.update_position("BNBUSDT", 305.0)
    print(f"BNB @ $305: {result or 'Posición activa'}")
    
    # SOL baja
    risk_manager.update_price_history("SOLUSDT", 95.0)
    result = risk_manager.update_position("SOLUSDT", 95.0, atr=2.3)
    print(f"SOL @ $95: {result or 'Posición activa'}")
    
    # BNB sigue subiendo
    result = risk_manager.update_position("BNBUSDT", 320.0)
    print(f"BNB @ $320: {result or 'Posición activa'}")
    
    # Resumen de riesgo
    print("\n=== RESUMEN DE RIESGO ===")
    summary = risk_manager.get_risk_summary()
    
    print(f"Capital Total: ${summary['valor_total_portafolio']:.2f}")
    print(f"PnL No Realizado: ${summary['pnl_no_realizado']:.2f}")
    print(f"Retorno Total: {summary['retorno_total']:.2%}")
    print(f"Posiciones Activas: {summary['posiciones_activas']}")
    print(f"Nivel de Riesgo: {summary['metricas_riesgo']['nivel_riesgo']}")
    
    print("\nPosiciones Detalle:")
    for symbol, details in summary['posiciones_detalle'].items():
        print(f"  {symbol}: {details['lado']} ${details['valor']:.2f} | PnL: ${details['pnl']:.2f} ({details['pnl_pct']:.2%})")