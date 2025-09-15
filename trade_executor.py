import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
from trading_signals import TradingSignal, SignalType, StrategyType
from portfolio_manager import PortfolioManager

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Tipos de órdenes"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderStatus(Enum):
    """Estados de órdenes"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"

class PositionStatus(Enum):
    """Estados de posiciones"""
    OPEN = "open"
    CLOSED = "closed"
    CLOSING = "closing"

@dataclass
class Order:
    """Orden de trading"""
    order_id: str
    symbol: str
    order_type: OrderType
    side: str  # 'buy' or 'sell'
    quantity: float
    price: Optional[float]  # None para market orders
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    filled_timestamp: Optional[datetime] = None
    parent_position_id: Optional[str] = None
    signal_id: Optional[str] = None
    
@dataclass
class Position:
    """Posición de trading"""
    position_id: str
    symbol: str
    side: str  # 'long' or 'short'
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: PositionStatus = PositionStatus.OPEN
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    commission_paid: float = 0.0
    entry_timestamp: datetime = field(default_factory=datetime.now)
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[float] = None
    strategy_type: Optional[StrategyType] = None
    signal_confidence: float = 0.0
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0    # MAE
    
    def update_pnl(self, current_price: float):
        """Actualiza PnL no realizado"""
        self.current_price = current_price
        
        if self.side == 'long':
            pnl_per_unit = current_price - self.entry_price
        else:  # short
            pnl_per_unit = self.entry_price - current_price
            
        self.unrealized_pnl = pnl_per_unit * self.quantity - self.commission_paid
        
        # Actualizar MFE y MAE
        if self.side == 'long':
            favorable_excursion = current_price - self.entry_price
            adverse_excursion = self.entry_price - current_price
        else:
            favorable_excursion = self.entry_price - current_price
            adverse_excursion = current_price - self.entry_price
            
        self.max_favorable_excursion = max(self.max_favorable_excursion, favorable_excursion * self.quantity)
        if adverse_excursion > 0:
            self.max_adverse_excursion = max(self.max_adverse_excursion, adverse_excursion * self.quantity)

@dataclass
class TradeResult:
    """Resultado de un trade cerrado"""
    trade_id: str
    symbol: str
    strategy_type: StrategyType
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    entry_timestamp: datetime
    exit_timestamp: datetime
    duration: timedelta
    gross_pnl: float
    commission: float
    net_pnl: float
    return_pct: float
    signal_confidence: float
    max_favorable_excursion: float
    max_adverse_excursion: float
    exit_reason: str  # 'take_profit', 'stop_loss', 'manual', 'signal_expiry'
    
class TradingSimulator:
    """Simulador de trading en papel"""
    
    def __init__(self, initial_capital: float = 10000.0, commission_rate: float = 0.001):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_rate = commission_rate  # 0.1% por defecto
        
        # Gestión de órdenes y posiciones
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.closed_trades: List[TradeResult] = []
        
        # Contadores para IDs únicos
        self._order_counter = 0
        self._position_counter = 0
        
        # Métricas de performance
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_commission_paid = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
        # Historial de capital
        self.capital_history: List[Tuple[datetime, float]] = [(datetime.now(), initial_capital)]
        
        # Configuración de riesgo
        self.max_risk_per_trade = 0.02  # 2% máximo por trade
        self.max_total_risk = 0.10      # 10% máximo total
        self.max_positions = 10         # Máximo 10 posiciones simultáneas
        
    def execute_signal(self, signal: TradingSignal, current_price: float) -> Optional[str]:
        """Ejecuta una señal de trading"""
        try:
            # Validaciones previas
            if not self._validate_signal(signal, current_price):
                return None
                
            # Calcular tamaño de posición ajustado
            position_size = self._calculate_position_size(signal, current_price)
            if position_size <= 0:
                logger.warning(f"Tamaño de posición inválido para {signal.symbol}")
                return None
                
            # Crear orden de entrada
            order_id = self._generate_order_id()
            entry_order = Order(
                order_id=order_id,
                symbol=signal.symbol,
                order_type=OrderType.MARKET,
                side='buy',  # Asumimos solo posiciones largas por simplicidad
                quantity=position_size,
                price=None,  # Market order
                signal_id=str(id(signal))
            )
            
            # Ejecutar orden inmediatamente (simulación)
            filled_price = self._simulate_market_execution(current_price, signal.symbol)
            commission = self._calculate_commission(position_size, filled_price)
            
            # Verificar capital suficiente
            required_capital = position_size * filled_price + commission
            if required_capital > self.current_capital:
                logger.warning(f"Capital insuficiente para {signal.symbol}. Requerido: ${required_capital:.2f}, Disponible: ${self.current_capital:.2f}")
                return None
                
            # Actualizar orden como ejecutada
            entry_order.status = OrderStatus.FILLED
            entry_order.filled_quantity = position_size
            entry_order.filled_price = filled_price
            entry_order.commission = commission
            entry_order.filled_timestamp = datetime.now()
            
            self.orders[order_id] = entry_order
            
            # Crear posición
            position_id = self._generate_position_id()
            position = Position(
                position_id=position_id,
                symbol=signal.symbol,
                side='long',
                quantity=position_size,
                entry_price=filled_price,
                current_price=filled_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                commission_paid=commission,
                strategy_type=signal.strategy_type,
                signal_confidence=signal.confidence
            )
            
            entry_order.parent_position_id = position_id
            self.positions[position_id] = position
            
            # Actualizar capital
            self.current_capital -= required_capital
            self.total_commission_paid += commission
            
            # Crear órdenes de stop loss y take profit
            if signal.stop_loss:
                self._create_stop_loss_order(position_id, signal.stop_loss, position_size)
                
            if signal.take_profit:
                self._create_take_profit_order(position_id, signal.take_profit, position_size)
                
            logger.info(f"Posición abierta: {signal.symbol} - {position_size:.4f} @ ${filled_price:.2f}")
            return position_id
            
        except Exception as e:
            logger.error(f"Error ejecutando señal para {signal.symbol}: {e}")
            return None
            
    def update_positions(self, price_data: Dict[str, float]):
        """Actualiza todas las posiciones con nuevos precios"""
        for position in self.positions.values():
            if position.status == PositionStatus.OPEN and position.symbol in price_data:
                current_price = price_data[position.symbol]
                position.update_pnl(current_price)
                
                # Verificar órdenes de stop loss y take profit
                self._check_exit_orders(position, current_price)
                
        # Actualizar historial de capital
        total_value = self._calculate_total_portfolio_value(price_data)
        self.capital_history.append((datetime.now(), total_value))
        
        # Actualizar drawdown
        self._update_drawdown(total_value)
        
    def _validate_signal(self, signal: TradingSignal, current_price: float) -> bool:
        """Valida si una señal puede ser ejecutada"""
        # Verificar si ya tenemos posición en este símbolo
        for position in self.positions.values():
            if position.symbol == signal.symbol and position.status == PositionStatus.OPEN:
                logger.info(f"Ya existe posición abierta para {signal.symbol}")
                return False
                
        # Verificar número máximo de posiciones
        open_positions = sum(1 for p in self.positions.values() if p.status == PositionStatus.OPEN)
        if open_positions >= self.max_positions:
            logger.warning(f"Máximo número de posiciones alcanzado ({self.max_positions})")
            return False
            
        # Verificar riesgo total
        current_risk = self._calculate_current_risk()
        signal_risk = signal.max_risk / self.current_capital
        
        if current_risk + signal_risk > self.max_total_risk:
            logger.warning(f"Riesgo total excedería límite: {(current_risk + signal_risk)*100:.1f}% > {self.max_total_risk*100:.1f}%")
            return False
            
        return True
        
    def _calculate_position_size(self, signal: TradingSignal, current_price: float) -> float:
        """Calcula tamaño de posición basado en gestión de riesgo"""
        # Riesgo máximo por trade en términos de capital
        max_risk_capital = self.current_capital * self.max_risk_per_trade
        
        # Riesgo por unidad (diferencia entre precio de entrada y stop loss)
        if signal.stop_loss:
            risk_per_unit = abs(current_price - signal.stop_loss)
            if risk_per_unit > 0:
                # Tamaño basado en riesgo
                risk_based_size = max_risk_capital / risk_per_unit
            else:
                risk_based_size = 0
        else:
            # Sin stop loss, usar tamaño conservador
            risk_based_size = max_risk_capital / (current_price * 0.05)  # 5% de riesgo asumido
            
        # Tamaño basado en confianza de la señal
        confidence_multiplier = signal.confidence / 100.0
        confidence_adjusted_size = risk_based_size * confidence_multiplier
        
        # Tamaño máximo basado en capital disponible (no más del 20% en una posición)
        max_position_value = self.current_capital * 0.20
        max_size_by_capital = max_position_value / current_price
        
        # Tomar el menor de los tamaños calculados
        final_size = min(confidence_adjusted_size, max_size_by_capital, signal.position_size)
        
        return max(0, final_size)
        
    def _simulate_market_execution(self, price: float, symbol: str) -> float:
        """Simula ejecución de orden de mercado con slippage"""
        # Simular slippage basado en volatilidad del símbolo
        slippage_factors = {
            'BTCUSDT': 0.0005,   # 0.05%
            'ETHUSDT': 0.0008,   # 0.08%
            'BNBUSDT': 0.001,    # 0.1%
            'SOLUSDT': 0.0015,   # 0.15%
            'ADAUSDT': 0.0012,   # 0.12%
            'NAS100': 0.0003,    # 0.03%
            'AUDCAD': 0.0002,    # 0.02%
            'XAUUSD': 0.0005,    # 0.05%
        }
        
        slippage_factor = slippage_factors.get(symbol, 0.001)  # Default 0.1%
        slippage = np.random.normal(0, slippage_factor) * price
        
        return price + slippage
        
    def _calculate_commission(self, quantity: float, price: float) -> float:
        """Calcula comisión de trading"""
        return quantity * price * self.commission_rate
        
    def _create_stop_loss_order(self, position_id: str, stop_price: float, quantity: float):
        """Crea orden de stop loss"""
        order_id = self._generate_order_id()
        stop_order = Order(
            order_id=order_id,
            symbol=self.positions[position_id].symbol,
            order_type=OrderType.STOP_LOSS,
            side='sell',
            quantity=quantity,
            price=None,
            stop_price=stop_price,
            parent_position_id=position_id
        )
        self.orders[order_id] = stop_order
        
    def _create_take_profit_order(self, position_id: str, target_price: float, quantity: float):
        """Crea orden de take profit"""
        order_id = self._generate_order_id()
        tp_order = Order(
            order_id=order_id,
            symbol=self.positions[position_id].symbol,
            order_type=OrderType.TAKE_PROFIT,
            side='sell',
            quantity=quantity,
            price=target_price,
            parent_position_id=position_id
        )
        self.orders[order_id] = tp_order
        
    def _check_exit_orders(self, position: Position, current_price: float):
        """Verifica si se deben ejecutar órdenes de salida"""
        if position.status != PositionStatus.OPEN:
            return
            
        # Buscar órdenes de stop loss y take profit para esta posición
        for order in self.orders.values():
            if (order.parent_position_id == position.position_id and 
                order.status == OrderStatus.PENDING):
                
                should_execute = False
                exit_reason = ""
                
                if order.order_type == OrderType.STOP_LOSS:
                    if position.side == 'long' and current_price <= order.stop_price:
                        should_execute = True
                        exit_reason = "stop_loss"
                    elif position.side == 'short' and current_price >= order.stop_price:
                        should_execute = True
                        exit_reason = "stop_loss"
                        
                elif order.order_type == OrderType.TAKE_PROFIT:
                    if position.side == 'long' and current_price >= order.price:
                        should_execute = True
                        exit_reason = "take_profit"
                    elif position.side == 'short' and current_price <= order.price:
                        should_execute = True
                        exit_reason = "take_profit"
                        
                if should_execute:
                    self._execute_exit_order(order, position, current_price, exit_reason)
                    
    def _execute_exit_order(self, order: Order, position: Position, exit_price: float, exit_reason: str):
        """Ejecuta orden de salida"""
        try:
            # Simular ejecución con slippage
            filled_price = self._simulate_market_execution(exit_price, position.symbol)
            commission = self._calculate_commission(order.quantity, filled_price)
            
            # Actualizar orden
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.filled_price = filled_price
            order.commission = commission
            order.filled_timestamp = datetime.now()
            
            # Cerrar posición
            position.status = PositionStatus.CLOSED
            position.exit_price = filled_price
            position.exit_timestamp = datetime.now()
            
            # Calcular PnL realizado
            if position.side == 'long':
                gross_pnl = (filled_price - position.entry_price) * position.quantity
            else:
                gross_pnl = (position.entry_price - filled_price) * position.quantity
                
            total_commission = position.commission_paid + commission
            net_pnl = gross_pnl - total_commission
            
            position.realized_pnl = net_pnl
            position.unrealized_pnl = 0.0
            
            # Actualizar capital
            position_value = position.quantity * filled_price - commission
            self.current_capital += position_value
            self.total_commission_paid += commission
            
            # Crear resultado de trade
            trade_result = TradeResult(
                trade_id=position.position_id,
                symbol=position.symbol,
                strategy_type=position.strategy_type,
                side=position.side,
                quantity=position.quantity,
                entry_price=position.entry_price,
                exit_price=filled_price,
                entry_timestamp=position.entry_timestamp,
                exit_timestamp=position.exit_timestamp,
                duration=position.exit_timestamp - position.entry_timestamp,
                gross_pnl=gross_pnl,
                commission=total_commission,
                net_pnl=net_pnl,
                return_pct=(net_pnl / (position.entry_price * position.quantity)) * 100,
                signal_confidence=position.signal_confidence,
                max_favorable_excursion=position.max_favorable_excursion,
                max_adverse_excursion=position.max_adverse_excursion,
                exit_reason=exit_reason
            )
            
            self.closed_trades.append(trade_result)
            
            # Actualizar estadísticas
            self.total_trades += 1
            if net_pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
                
            # Cancelar otras órdenes pendientes para esta posición
            self._cancel_position_orders(position.position_id, order.order_id)
            
            logger.info(f"Posición cerrada: {position.symbol} - PnL: ${net_pnl:.2f} ({exit_reason})")
            
        except Exception as e:
            logger.error(f"Error ejecutando orden de salida: {e}")
            
    def _cancel_position_orders(self, position_id: str, executed_order_id: str):
        """Cancela órdenes pendientes para una posición"""
        for order in self.orders.values():
            if (order.parent_position_id == position_id and 
                order.order_id != executed_order_id and
                order.status == OrderStatus.PENDING):
                order.status = OrderStatus.CANCELLED
                
    def _calculate_current_risk(self) -> float:
        """Calcula riesgo actual del portafolio"""
        total_risk = 0.0
        
        for position in self.positions.values():
            if position.status == PositionStatus.OPEN and position.stop_loss:
                risk_per_unit = abs(position.entry_price - position.stop_loss)
                position_risk = risk_per_unit * position.quantity
                total_risk += position_risk
                
        return total_risk / self.current_capital if self.current_capital > 0 else 0
        
    def _calculate_total_portfolio_value(self, price_data: Dict[str, float]) -> float:
        """Calcula valor total del portafolio"""
        total_value = self.current_capital
        
        for position in self.positions.values():
            if position.status == PositionStatus.OPEN and position.symbol in price_data:
                current_price = price_data[position.symbol]
                position_value = position.quantity * current_price
                total_value += position_value
                
        return total_value
        
    def _update_drawdown(self, current_value: float):
        """Actualiza drawdown máximo"""
        if current_value > self.peak_capital:
            self.peak_capital = current_value
            
        current_drawdown = (self.peak_capital - current_value) / self.peak_capital
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
    def _generate_order_id(self) -> str:
        """Genera ID único para orden"""
        self._order_counter += 1
        return f"ORD_{self._order_counter:06d}"
        
    def _generate_position_id(self) -> str:
        """Genera ID único para posición"""
        self._position_counter += 1
        return f"POS_{self._position_counter:06d}"
        
    def get_performance_metrics(self) -> Dict:
        """Obtiene métricas de performance"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'average_win': 0,
                'average_loss': 0,
                'profit_factor': 0,
                'max_drawdown': self.max_drawdown,
                'sharpe_ratio': 0,
                'current_capital': self.current_capital,
                'total_return': 0
            }
            
        # Calcular métricas básicas
        total_pnl = sum(trade.net_pnl for trade in self.closed_trades)
        winning_trades = [trade for trade in self.closed_trades if trade.net_pnl > 0]
        losing_trades = [trade for trade in self.closed_trades if trade.net_pnl < 0]
        
        win_rate = len(winning_trades) / len(self.closed_trades) * 100
        average_win = np.mean([trade.net_pnl for trade in winning_trades]) if winning_trades else 0
        average_loss = np.mean([trade.net_pnl for trade in losing_trades]) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(trade.net_pnl for trade in winning_trades)
        gross_loss = abs(sum(trade.net_pnl for trade in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe ratio (simplificado)
        if len(self.capital_history) > 1:
            returns = []
            for i in range(1, len(self.capital_history)):
                prev_value = self.capital_history[i-1][1]
                curr_value = self.capital_history[i][1]
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
                
            if returns and np.std(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Anualizado
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
            
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        
        return {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'average_win': average_win,
            'average_loss': average_loss,
            'profit_factor': profit_factor,
            'max_drawdown': self.max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            'total_return': total_return,
            'total_commission_paid': self.total_commission_paid
        }
        
    def get_open_positions_summary(self) -> List[Dict]:
        """Obtiene resumen de posiciones abiertas"""
        open_positions = []
        
        for position in self.positions.values():
            if position.status == PositionStatus.OPEN:
                open_positions.append({
                    'position_id': position.position_id,
                    'symbol': position.symbol,
                    'side': position.side,
                    'quantity': position.quantity,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'unrealized_pnl': position.unrealized_pnl,
                    'unrealized_pnl_pct': (position.unrealized_pnl / (position.entry_price * position.quantity)) * 100,
                    'stop_loss': position.stop_loss,
                    'take_profit': position.take_profit,
                    'strategy_type': position.strategy_type.value if position.strategy_type else None,
                    'confidence': position.signal_confidence,
                    'duration': datetime.now() - position.entry_timestamp,
                    'mfe': position.max_favorable_excursion,
                    'mae': position.max_adverse_excursion
                })
                
        return open_positions
        
    def close_position_manually(self, position_id: str, current_price: float) -> bool:
        """Cierra posición manualmente"""
        if position_id not in self.positions:
            return False
            
        position = self.positions[position_id]
        if position.status != PositionStatus.OPEN:
            return False
            
        # Crear orden de salida manual
        order_id = self._generate_order_id()
        exit_order = Order(
            order_id=order_id,
            symbol=position.symbol,
            order_type=OrderType.MARKET,
            side='sell',
            quantity=position.quantity,
            price=None,
            parent_position_id=position_id
        )
        
        self.orders[order_id] = exit_order
        self._execute_exit_order(exit_order, position, current_price, "manual")
        
        return True
        
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """Obtiene historial de trades"""
        recent_trades = sorted(self.closed_trades, key=lambda x: x.exit_timestamp, reverse=True)[:limit]
        
        return [{
            'trade_id': trade.trade_id,
            'symbol': trade.symbol,
            'strategy_type': trade.strategy_type.value if trade.strategy_type else None,
            'side': trade.side,
            'quantity': trade.quantity,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'entry_timestamp': trade.entry_timestamp,
            'exit_timestamp': trade.exit_timestamp,
            'duration': str(trade.duration),
            'gross_pnl': trade.gross_pnl,
            'net_pnl': trade.net_pnl,
            'return_pct': trade.return_pct,
            'commission': trade.commission,
            'exit_reason': trade.exit_reason,
            'confidence': trade.signal_confidence,
            'mfe': trade.max_favorable_excursion,
            'mae': trade.max_adverse_excursion
        } for trade in recent_trades]

if __name__ == "__main__":
    # Ejemplo de uso
    simulator = TradingSimulator(initial_capital=10000.0)
    
    # Simular algunas señales y trades
    from trading_signals import TradingSignal, SignalType, StrategyType
    
    # Crear señal de ejemplo
    signal = TradingSignal(
        symbol="BTCUSDT",
        signal_type=SignalType.BUY,
        strategy_type=StrategyType.MOMENTUM,
        entry_price=45000.0,
        stop_loss=44000.0,
        take_profit=47000.0,
        position_size=0.1,
        confidence=75.0,
        risk_reward_ratio=2.0,
        expected_return=200.0,
        max_risk=100.0,
        reasons=["RSI sobreventa", "MACD alcista"],
        timestamp=datetime.now()
    )
    
    # Ejecutar señal
    position_id = simulator.execute_signal(signal, 45000.0)
    print(f"Posición creada: {position_id}")
    
    # Simular movimientos de precio
    price_updates = {
        "BTCUSDT": 45500.0  # Precio sube
    }
    
    simulator.update_positions(price_updates)
    
    # Mostrar posiciones abiertas
    open_positions = simulator.get_open_positions_summary()
    print(f"\nPosiciones abiertas: {len(open_positions)}")
    for pos in open_positions:
        print(f"{pos['symbol']}: PnL ${pos['unrealized_pnl']:.2f} ({pos['unrealized_pnl_pct']:.2f}%)")
        
    # Mostrar métricas
    metrics = simulator.get_performance_metrics()
    print(f"\nCapital actual: ${metrics['current_capital']:.2f}")
    print(f"Retorno total: {metrics['total_return']:.2f}%")