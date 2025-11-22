# /src/paper_trading_system.py
"""
Sistema de Paper Trading para SICAR
Simula operaciones de trading sin usar dinero real.
Incluye soporte para operaciones de scalping con timeouts automáticos.
Integrado con sistema DRL avanzado.
"""

import logging
import json
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np

# Importar trade logger
try:
    from trade_logger import trade_logger_instance
    TRADE_LOGGER_AVAILABLE = True
except ImportError:
    TRADE_LOGGER_AVAILABLE = False

logger = logging.getLogger(__name__)

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class PositionSide(Enum):
    LONG = "long"
    SHORT = "short"

@dataclass
class PaperOrder:
    """Representa una orden virtual de paper trading."""
    order_id: str
    symbol: str
    side: str  # 'buy' o 'sell'
    order_type: OrderType
    quantity: float
    price: float
    status: OrderStatus
    created_at: datetime
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    stop_price: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convierte la orden a diccionario para logging."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['filled_at'] = self.filled_at.isoformat() if self.filled_at else None
        data['order_type'] = self.order_type.value
        data['status'] = self.status.value
        return data

@dataclass
class PaperPosition:
    """Representa una posición virtual de paper trading."""
    symbol: str
    side: PositionSide
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    entry_time: datetime = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def __post_init__(self):
        if self.entry_time is None:
            self.entry_time = datetime.now()
    
    @property
    def market_value(self) -> float:
        """Valor de mercado actual de la posición."""
        return self.size * self.current_price
    
    @property
    def pnl_percentage(self) -> float:
        """PnL como porcentaje."""
        if self.entry_price > 0:
            if self.side == PositionSide.LONG:
                return ((self.current_price - self.entry_price) / self.entry_price) * 100
            else:
                return ((self.entry_price - self.current_price) / self.entry_price) * 100
        return 0.0
    
    def update_price(self, new_price: float):
        """Actualiza el precio y calcula PnL no realizado."""
        self.current_price = new_price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = self.size * (new_price - self.entry_price)
        else:
            self.unrealized_pnl = self.size * (self.entry_price - new_price)

class PaperTradingEngine:
    """
    Motor de paper trading que simula la ejecución de órdenes.
    
    Características:
    - Simulación realista de slippage
    - Gestión de órdenes pendientes
    - Tracking de posiciones virtuales
    - Cálculo de comisiones simuladas
    """
    
    def __init__(self, initial_capital: float = 10000.0, commission_rate: float = 0.001):
        """
        Inicializa el motor de paper trading.
        
        Args:
            initial_capital: Capital inicial virtual
            commission_rate: Tasa de comisión simulada (0.1% por defecto)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.commission_rate = commission_rate
        
        # Gestión de órdenes y posiciones
        self.orders: Dict[str, PaperOrder] = {}
        self.positions: Dict[str, PaperPosition] = {}
        self.order_history: List[PaperOrder] = []
        self.trade_history: List[Dict] = []
        
        # Configuración de slippage
        self.slippage_config = {
            'base_slippage': 0.0005,  # 0.05% base
            'volatility_multiplier': 2.0,
            'volume_impact': 0.0001
        }
        
        # Métricas de performance
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
        logger.info(f"🎯 Paper Trading Engine inicializado con ${initial_capital:,.2f}")
    
    def calculate_slippage(self, symbol: str, side: str, quantity: float, 
                          current_price: float, volatility: float = 0.01) -> float:
        """
        Calcula el slippage realista para una orden.
        
        Args:
            symbol: Símbolo del activo
            side: 'buy' o 'sell'
            quantity: Cantidad de la orden
            current_price: Precio actual del mercado
            volatility: Volatilidad estimada del activo
            
        Returns:
            Precio ajustado con slippage
        """
        base_slippage = self.slippage_config['base_slippage']
        volatility_impact = volatility * self.slippage_config['volatility_multiplier']
        
        # Calcular impacto por volumen (simulado)
        volume_impact = min(quantity / 1000000, 0.01) * self.slippage_config['volume_impact']
        
        total_slippage = base_slippage + volatility_impact + volume_impact
        
        # Aplicar slippage según el lado de la orden
        if side.lower() == 'buy':
            slipped_price = current_price * (1 + total_slippage)
        else:
            slipped_price = current_price * (1 - total_slippage)
        
        return slipped_price
    
    def place_order(self, symbol: str, side: str, order_type: OrderType, 
                   quantity: float, price: float = None, 
                   stop_price: float = None) -> str:
        """
        Coloca una orden virtual en el sistema.
        
        Args:
            symbol: Símbolo del activo
            side: 'buy' o 'sell'
            order_type: Tipo de orden
            quantity: Cantidad
            price: Precio (para órdenes limit)
            stop_price: Precio de stop (para órdenes stop)
            
        Returns:
            ID de la orden
        """
        order_id = str(uuid.uuid4())[:8]
        
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side.lower(),
            order_type=order_type,
            quantity=quantity,
            price=price or 0.0,
            status=OrderStatus.PENDING,
            created_at=datetime.now(),
            stop_price=stop_price
        )
        
        self.orders[order_id] = order
        
        logger.info(f"📝 Orden colocada: {order_id} - {side.upper()} {quantity:.6f} {symbol} @ ${price or 0:.2f}")
        return order_id
    
    def process_market_data(self, market_data: Dict[str, float]):
        """
        Procesa datos de mercado y ejecuta órdenes pendientes.
        
        Args:
            market_data: Diccionario con precios actuales {symbol: price}
        """
        # Actualizar precios de posiciones existentes
        for symbol, position in self.positions.items():
            if symbol in market_data:
                position.update_price(market_data[symbol])
                self._check_stop_loss_take_profit(position, market_data[symbol])
        
        # Procesar órdenes pendientes
        orders_to_process = [order for order in self.orders.values() 
                           if order.status == OrderStatus.PENDING]
        
        for order in orders_to_process:
            if order.symbol in market_data:
                self._try_fill_order(order, market_data[order.symbol])
    
    def _try_fill_order(self, order: PaperOrder, current_price: float):
        """Intenta ejecutar una orden pendiente."""
        should_fill = False
        fill_price = current_price
        
        if order.order_type == OrderType.MARKET:
            should_fill = True
            # Aplicar slippage para órdenes de mercado
            fill_price = self.calculate_slippage(
                order.symbol, order.side, order.quantity, current_price
            )
        
        elif order.order_type == OrderType.LIMIT:
            if order.side == 'buy' and current_price <= order.price:
                should_fill = True
                fill_price = order.price
            elif order.side == 'sell' and current_price >= order.price:
                should_fill = True
                fill_price = order.price
        
        elif order.order_type == OrderType.STOP_LOSS:
            if order.side == 'sell' and current_price <= order.stop_price:
                should_fill = True
                fill_price = self.calculate_slippage(
                    order.symbol, order.side, order.quantity, current_price
                )
        
        if should_fill:
            self._fill_order(order, fill_price)
    
    def _fill_order(self, order: PaperOrder, fill_price: float):
        """Ejecuta una orden y actualiza el portfolio."""
        # Calcular comisión
        trade_value = order.quantity * fill_price
        commission = trade_value * self.commission_rate
        
        # Verificar capital suficiente para compras
        if order.side == 'buy':
            total_cost = trade_value + commission
            if total_cost > self.current_capital:
                order.status = OrderStatus.REJECTED
                logger.warning(f"❌ Orden rechazada por capital insuficiente: {order.order_id}")
                return
            
            self.current_capital -= total_cost
        else:
            self.current_capital += (trade_value - commission)
        
        # Actualizar orden
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.now()
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        
        # Gestionar posición
        self._update_position(order, fill_price, commission)
        
        # Registrar trade
        self._record_trade(order, fill_price, commission)
        
        # Mover a historial
        self.order_history.append(order)
        del self.orders[order.order_id]
        
        logger.info(f"✅ Orden ejecutada: {order.order_id} - {order.side.upper()} "
                   f"{order.quantity:.6f} {order.symbol} @ ${fill_price or 0:.2f}")
    
    def _update_position(self, order: PaperOrder, fill_price: float, commission: float):
        """Actualiza o crea posiciones basado en la orden ejecutada."""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # Nueva posición
            if order.side == 'buy':
                new_position = PaperPosition(
                    symbol=symbol,
                    side=PositionSide.LONG,
                    size=order.quantity,
                    entry_price=fill_price,
                    current_price=fill_price
                )
                self.positions[symbol] = new_position
                
                # Log de apertura de posición
                if TRADE_LOGGER_AVAILABLE:
                    try:
                        position_value = order.quantity * fill_price
                        trade_logger_instance.info(
                            f"POSITION OPENED | {symbol} | LONG | "
                            f"Size: {order.quantity:.6f} | Entry: ${fill_price:.4f} | "
                            f"Value: ${position_value:.2f} | Capital: ${self.current_capital:.2f}"
                        )
                    except Exception as e:
                        logger.warning(f"Error logging position open: {e}")
            else:
                new_position = PaperPosition(
                    symbol=symbol,
                    side=PositionSide.SHORT,
                    size=order.quantity,
                    entry_price=fill_price,
                    current_price=fill_price
                )
                self.positions[symbol] = new_position
                
                # Log de apertura de posición
                if TRADE_LOGGER_AVAILABLE:
                    try:
                        position_value = order.quantity * fill_price
                        trade_logger_instance.info(
                            f"POSITION OPENED | {symbol} | SHORT | "
                            f"Size: {order.quantity:.6f} | Entry: ${fill_price:.4f} | "
                            f"Value: ${position_value:.2f} | Capital: ${self.current_capital:.2f}"
                        )
                    except Exception as e:
                        logger.warning(f"Error logging position open: {e}")
        else:
            # Posición existente - cerrar o modificar
            position = self.positions[symbol]
            
            if ((position.side == PositionSide.LONG and order.side == 'sell') or
                (position.side == PositionSide.SHORT and order.side == 'buy')):
                
                # Cerrar posición (total o parcial)
                if order.quantity >= position.size:
                    # Cierre total
                    realized_pnl = self._calculate_realized_pnl(position, fill_price, order.quantity)
                    position.realized_pnl += realized_pnl
                    self.total_pnl += realized_pnl
                    
                    # Log del cierre de posición
                    if TRADE_LOGGER_AVAILABLE:
                        try:
                            duration = datetime.now() - position.entry_time
                            pnl_pct = (realized_pnl / (position.entry_price * position.size)) * 100
                            
                            trade_logger_instance.info(
                                f"POSITION CLOSED | {symbol} | {position.side.value} | "
                                f"Entry: ${position.entry_price:.4f} | Exit: ${fill_price:.4f} | "
                                f"PnL: ${realized_pnl:.2f} ({pnl_pct:+.2f}%) | Duration: {duration}"
                            )
                        except Exception as e:
                            logger.warning(f"Error logging position close: {e}")
                    
                    del self.positions[symbol]
                    self.total_trades += 1
                    if realized_pnl > 0:
                        self.winning_trades += 1
                else:
                    # Cierre parcial
                    realized_pnl = self._calculate_realized_pnl(position, fill_price, order.quantity)
                    position.realized_pnl += realized_pnl
                    position.size -= order.quantity
                    self.total_pnl += realized_pnl
    
    def _calculate_realized_pnl(self, position: PaperPosition, exit_price: float, quantity: float) -> float:
        """Calcula el PnL realizado para una posición cerrada."""
        if position.side == PositionSide.LONG:
            return quantity * (exit_price - position.entry_price)
        else:
            return quantity * (position.entry_price - exit_price)
    
    def _check_stop_loss_take_profit(self, position: PaperPosition, current_price: float):
        """Verifica si se deben activar stop loss o take profit."""
        if position.stop_loss and current_price <= position.stop_loss:
            # Activar stop loss
            side = 'sell' if position.side == PositionSide.LONG else 'buy'
            self.place_order(
                position.symbol, side, OrderType.MARKET, 
                position.size, current_price
            )
        
        elif position.take_profit and current_price >= position.take_profit:
            # Activar take profit
            side = 'sell' if position.side == PositionSide.LONG else 'buy'
            self.place_order(
                position.symbol, side, OrderType.MARKET, 
                position.size, current_price
            )
    
    def _record_trade(self, order: PaperOrder, fill_price: float, commission: float):
        """Registra un trade en el historial."""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side,
            'quantity': order.quantity,
            'price': fill_price,
            'value': order.quantity * fill_price,
            'commission': commission,
            'capital_after': self.current_capital
        }
        
        self.trade_history.append(trade_record)
        
        # Registrar en trade logger si está disponible
        if TRADE_LOGGER_AVAILABLE:
            try:
                # Log detallado en formato texto
                trade_logger_instance.info(
                    f"PAPER TRADE EXECUTED | {order.symbol} | {order.side.upper()} | "
                    f"Qty: {order.quantity:.6f} | Price: ${fill_price:.4f} | "
                    f"Value: ${trade_record['value']:.2f} | Commission: ${commission:.4f} | "
                    f"Capital: ${self.current_capital:.2f} | Order: {order.order_id}"
                )
                
                # Log en formato JSON para análisis
                json_record = {
                    "event_type": "paper_trade",
                    "timestamp": trade_record['timestamp'],
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.quantity,
                    "fill_price": fill_price,
                    "trade_value": trade_record['value'],
                    "commission": commission,
                    "capital_after": self.current_capital,
                    "order_type": order.order_type.value if hasattr(order.order_type, 'value') else str(order.order_type),
                    "session_type": "paper_trading"
                }
                
                # Escribir al archivo JSON
                import os
                logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                
                json_log_file = os.path.join(logs_dir, 'trades_data.jsonl')
                with open(json_log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(json_record) + '\n')
                    
            except Exception as e:
                logger.warning(f"Error registrando en trade logger: {e}")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Obtiene un resumen completo del portfolio virtual."""
        total_position_value = sum(pos.market_value for pos in self.positions.values())
        total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        total_portfolio_value = self.current_capital + total_position_value
        
        # Calcular drawdown
        if total_portfolio_value > self.peak_capital:
            self.peak_capital = total_portfolio_value
        
        current_drawdown = (self.peak_capital - total_portfolio_value) / self.peak_capital
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # Win rate
        win_rate = (self.winning_trades / self.total_trades) if self.total_trades > 0 else 0
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_position_value': total_position_value,
            'total_portfolio_value': total_portfolio_value,
            'total_pnl': self.total_pnl,
            'unrealized_pnl': total_unrealized_pnl,
            'total_return_pct': ((total_portfolio_value - self.initial_capital) / self.initial_capital) * 100,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': win_rate,
            'max_drawdown': self.max_drawdown * 100,
            'open_positions': len(self.positions),
            'pending_orders': len([o for o in self.orders.values() if o.status == OrderStatus.PENDING])
        }
    
    def get_positions_summary(self) -> List[Dict]:
        """Obtiene resumen de todas las posiciones abiertas."""
        return [
            {
                'symbol': pos.symbol,
                'side': pos.side.value,
                'size': pos.size,
                'entry_price': pos.entry_price,
                'current_price': pos.current_price,
                'market_value': pos.market_value,
                'unrealized_pnl': pos.unrealized_pnl,
                'pnl_percentage': pos.pnl_percentage,
                'entry_time': pos.entry_time.isoformat(),
                'duration': str(datetime.now() - pos.entry_time)
            }
            for pos in self.positions.values()
        ]
    
    def save_state(self, filepath: str):
        """Guarda el estado del paper trading en un archivo."""
        state = {
            'engine_config': {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'commission_rate': self.commission_rate,
                'slippage_config': self.slippage_config
            },
            'portfolio_summary': self.get_portfolio_summary(),
            'positions': self.get_positions_summary(),
            'trade_history': self.trade_history[-100:],  # Últimos 100 trades
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        logger.info(f"💾 Estado del paper trading guardado en: {filepath}")
    
    def reset_capital(self, new_initial_capital: float, close_positions: bool = True, reset_history: bool = True):
        """
        Resetea el capital inicial y opcionalmente cierra posiciones y resetea historial.
        
        Args:
            new_initial_capital: Nuevo capital inicial
            close_positions: Si cerrar todas las posiciones abiertas
            reset_history: Si resetear el historial de trades
        """
        logger.info(f"🔄 Reseteando capital de ${self.initial_capital:.2f} a ${new_initial_capital:.2f}")
        
        # Cerrar todas las posiciones si se solicita
        if close_positions and self.positions:
            logger.info("🔒 Cerrando todas las posiciones abiertas...")
            for symbol in list(self.positions.keys()):
                position = self.positions[symbol]
                # Simular cierre de posición al precio actual
                self.current_capital += position.market_value
                self.total_pnl += position.unrealized_pnl
                
                # Registrar el trade de cierre
                self.trade_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol,
                    'side': 'SELL' if position.side == PositionSide.LONG else 'BUY',
                    'quantity': position.size,
                    'price': position.current_price,
                    'type': 'MARKET_CLOSE',
                    'pnl': position.unrealized_pnl,
                    'reason': 'Capital Reset'
                })
                
                del self.positions[symbol]
        
        # Resetear capital
        self.initial_capital = new_initial_capital
        self.current_capital = new_initial_capital
        
        # Resetear historial si se solicita
        if reset_history:
            logger.info("📊 Reseteando historial de trades...")
            self.trade_history = []
            self.total_trades = 0
            self.winning_trades = 0
            self.total_pnl = 0
            self.max_drawdown = 0
        
        # Cancelar órdenes pendientes
        pending_orders = [o for o in self.orders.values() if o.status == OrderStatus.PENDING]
        for order in pending_orders:
            order.status = OrderStatus.CANCELLED
            logger.info(f"❌ Orden cancelada: {order.symbol} {order.side.value} {order.quantity}")
    
    # 🚀 FUNCIONALIDADES DE SCALPING
    
    def create_scalping_position(self, symbol: str, direction: str, entry_price: float, 
                               take_profit_pct: float = 2.0, stop_loss_pct: float = 1.0,
                               position_size_usd: float = 100.0, duration_minutes: int = 5) -> Optional[str]:
        """
        Crea una posición de scalping con take profit y stop loss automáticos.
        
        Args:
            symbol: Símbolo del activo
            direction: 'bullish' o 'bearish'
            entry_price: Precio de entrada
            take_profit_pct: Porcentaje de take profit
            stop_loss_pct: Porcentaje de stop loss
            position_size_usd: Tamaño de la posición en USD
            duration_minutes: Duración máxima en minutos
            
        Returns:
            ID de la posición de scalping o None si falla
        """
        try:
            # Calcular cantidad basada en el tamaño en USD
            quantity = position_size_usd / entry_price
            
            # Verificar capital suficiente
            total_cost = position_size_usd + (position_size_usd * self.commission_rate)
            if total_cost > self.current_capital:
                logger.warning(f"❌ Capital insuficiente para scalping {symbol}: ${total_cost:.2f} > ${self.current_capital:.2f}")
                return None
            
            # Determinar lado de la orden
            side = 'buy' if direction.lower() == 'bullish' else 'sell'
            
            # Crear orden de entrada
            entry_order_id = self.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=entry_price
            )
            
            # Calcular precios de take profit y stop loss
            if direction.lower() == 'bullish':
                take_profit_price = entry_price * (1 + take_profit_pct / 100)
                stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
                exit_side = 'sell'
            else:
                take_profit_price = entry_price * (1 - take_profit_pct / 100)
                stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
                exit_side = 'buy'
            
            # Programar cierre automático por tiempo
            scalping_id = f"scalp_{entry_order_id}_{int(datetime.now().timestamp())}"
            
            def auto_close_position():
                """Función para cerrar automáticamente la posición por tiempo"""
                import time
                time.sleep(duration_minutes * 60)  # Esperar duración especificada
                
                try:
                    # Verificar si la posición aún existe
                    if symbol in self.positions:
                        position = self.positions[symbol]
                        
                        # Crear orden de cierre por tiempo
                        close_order_id = self.place_order(
                            symbol=symbol,
                            side=exit_side,
                            order_type=OrderType.MARKET,
                            quantity=position.size,
                            price=position.current_price
                        )
                        
                        logger.info(f"⏰ SCALPING TIMEOUT: Cerrando {symbol} por tiempo límite ({duration_minutes}min)")
                        
                        # Registrar en historial
                        self.trade_history.append({
                            'timestamp': datetime.now().isoformat(),
                            'symbol': symbol,
                            'side': exit_side.upper(),
                            'quantity': position.size,
                            'price': position.current_price,
                            'type': 'SCALPING_TIMEOUT',
                            'pnl': position.unrealized_pnl,
                            'reason': f'Timeout {duration_minutes}min',
                            'scalping_id': scalping_id
                        })
                        
                except Exception as e:
                    logger.error(f"Error en cierre automático de scalping {symbol}: {e}")
            
            # Iniciar hilo para cierre automático
            timeout_thread = threading.Thread(target=auto_close_position, daemon=True)
            timeout_thread.start()
            
            # Registrar operación de scalping
            self.trade_history.append({
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': side.upper(),
                'quantity': quantity,
                'price': entry_price,
                'type': 'SCALPING_ENTRY',
                'take_profit_price': take_profit_price,
                'stop_loss_price': stop_loss_price,
                'duration_minutes': duration_minutes,
                'scalping_id': scalping_id,
                'direction': direction
            })
            
            logger.info(f"🚀 SCALPING CREADO: {symbol} {direction.upper()} ${position_size_usd:.2f} "
                       f"(TP: ${take_profit_price or 0:.4f}, SL: ${stop_loss_price or 0:.4f}, {duration_minutes}min)")
            
            return scalping_id
            
        except Exception as e:
            logger.error(f"Error creando posición de scalping {symbol}: {e}")
            return None
    
    def get_scalping_statistics(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas específicas de operaciones de scalping.
        
        Returns:
            Diccionario con estadísticas de scalping
        """
        scalping_trades = [trade for trade in self.trade_history 
                          if trade.get('type', '').startswith('SCALPING')]
        
        if not scalping_trades:
            return {
                'total_scalping_trades': 0,
                'scalping_pnl': 0.0,
                'scalping_win_rate': 0.0,
                'avg_scalping_duration': 0.0,
                'scalping_success_rate': 0.0
            }
        
        # Agrupar por scalping_id para calcular PnL completo
        scalping_sessions = {}
        for trade in scalping_trades:
            scalp_id = trade.get('scalping_id')
            if scalp_id:
                if scalp_id not in scalping_sessions:
                    scalping_sessions[scalp_id] = []
                scalping_sessions[scalp_id].append(trade)
        
        total_pnl = 0.0
        winning_sessions = 0
        total_sessions = len(scalping_sessions)
        
        for session_trades in scalping_sessions.values():
            session_pnl = sum(trade.get('pnl', 0.0) for trade in session_trades)
            total_pnl += session_pnl
            if session_pnl > 0:
                winning_sessions += 1
        
        win_rate = (winning_sessions / total_sessions * 100) if total_sessions > 0 else 0.0
        
        return {
            'total_scalping_trades': len(scalping_trades),
            'total_scalping_sessions': total_sessions,
            'scalping_pnl': total_pnl,
            'scalping_win_rate': win_rate,
            'winning_sessions': winning_sessions,
            'losing_sessions': total_sessions - winning_sessions,
            'avg_pnl_per_session': total_pnl / total_sessions if total_sessions > 0 else 0.0
        }


class DRLIntegratedPaperTrading:
    """
    Sistema de Paper Trading integrado con DRL.
    Combina el motor de paper trading tradicional con el agente DRL avanzado.
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 symbols: List[str] = None,
                 enable_drl: bool = True,
                 enable_manual_trading: bool = True):
        """
        Inicializa el sistema integrado DRL + Paper Trading.
        
        Args:
            initial_capital: Capital inicial
            symbols: Lista de símbolos a tradear
            enable_drl: Habilitar trading automático DRL
            enable_manual_trading: Habilitar trading manual
        """
        self.initial_capital = initial_capital
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        self.enable_drl = enable_drl
        self.enable_manual_trading = enable_manual_trading
        
        # Inicializar motor de paper trading
        self.paper_engine = PaperTradingEngine(
            initial_capital=initial_capital,
            commission_rate=0.001
        )
        
        # Inicializar adaptador DRL si está habilitado
        self.drl_adapter = None
        if self.enable_drl:
            try:
                from drl_paper_trading_adapter import DRLPaperTradingAdapter
                self.drl_adapter = DRLPaperTradingAdapter(
                    initial_capital=initial_capital,
                    symbols=self.symbols
                )
                logger.info("🤖 Sistema DRL integrado exitosamente")
            except ImportError as e:
                logger.warning(f"No se pudo cargar el adaptador DRL: {e}")
                self.enable_drl = False
        
        # Estado del sistema
        self.trading_mode = 'hybrid'  # 'manual', 'drl', 'hybrid'
        self.drl_performance = {
            'total_drl_trades': 0,
            'drl_win_rate': 0.0,
            'drl_total_pnl': 0.0,
            'drl_confidence_avg': 0.0
        }
        
        logger.info(f"🔄 Sistema Integrado DRL+Paper Trading inicializado")
        logger.info(f"   💰 Capital: ${initial_capital:,.2f}")
        logger.info(f"   🤖 DRL: {'✅' if self.enable_drl else '❌'}")
        logger.info(f"   👤 Manual: {'✅' if self.enable_manual_trading else '❌'}")
    
    def process_market_update(self, market_data: Dict[str, float]):
        """
        Procesa actualización de mercado para ambos sistemas.
        
        Args:
            market_data: Datos de mercado {symbol: price}
        """
        try:
            # Actualizar motor de paper trading
            self.paper_engine.process_market_data(market_data)
            
            # Procesar con DRL si está habilitado
            if self.enable_drl and self.drl_adapter:
                if self.trading_mode in ['drl', 'hybrid']:
                    self.drl_adapter.process_market_update(market_data)
                    self._update_drl_performance()
            
        except Exception as e:
            logger.error(f"Error procesando actualización de mercado: {e}")
    
    def place_manual_order(self, symbol: str, side: str, order_type: OrderType, 
                          quantity: float, price: Optional[float] = None) -> Optional[str]:
        """
        Coloca una orden manual (no DRL).
        
        Args:
            symbol: Símbolo del activo
            side: 'buy' o 'sell'
            order_type: Tipo de orden
            quantity: Cantidad
            price: Precio (para órdenes limit)
            
        Returns:
            ID de la orden o None
        """
        if not self.enable_manual_trading:
            logger.warning("Trading manual deshabilitado")
            return None
        
        return self.paper_engine.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price
        )
    
    def set_trading_mode(self, mode: str):
        """
        Cambia el modo de trading.
        
        Args:
            mode: 'manual', 'drl', o 'hybrid'
        """
        valid_modes = ['manual', 'drl', 'hybrid']
        if mode not in valid_modes:
            raise ValueError(f"Modo inválido. Usar: {valid_modes}")
        
        self.trading_mode = mode
        logger.info(f"🔄 Modo de trading cambiado a: {mode.upper()}")
    
    def get_drl_signals(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene señales del agente DRL para un símbolo.
        
        Args:
            symbol: Símbolo del activo
            
        Returns:
            Diccionario con señal DRL o None
        """
        if not self.enable_drl or not self.drl_adapter:
            return None
        
        try:
            action, confidence, value = self.drl_adapter.get_drl_trading_signal(symbol)
            
            return {
                'symbol': symbol,
                'action': action,  # 0: Hold, 1: Buy, 2: Sell
                'action_name': ['Hold', 'Buy', 'Sell'][action],
                'confidence': confidence,
                'value_estimate': value,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo señal DRL para {symbol}: {e}")
            return None
    
    def _update_drl_performance(self):
        """Actualiza métricas de performance del DRL."""
        if not self.drl_adapter:
            return
        
        try:
            drl_status = self.drl_adapter.get_system_status()
            performance = drl_status.get('performance', {})
            
            self.drl_performance.update({
                'total_drl_trades': performance.get('total_trades', 0),
                'drl_win_rate': performance.get('win_rate', 0.0),
                'drl_total_pnl': performance.get('total_pnl', 0.0),
                'drl_confidence_avg': performance.get('drl_confidence_avg', 0.0)
            })
            
        except Exception as e:
            logger.error(f"Error actualizando performance DRL: {e}")
    
    def get_integrated_summary(self) -> Dict[str, Any]:
        """
        Obtiene resumen completo del sistema integrado.
        
        Returns:
            Diccionario con métricas completas
        """
        try:
            # Resumen base del paper trading
            base_summary = self.paper_engine.get_portfolio_summary()
            
            # Agregar información DRL
            integrated_summary = {
                **base_summary,
                'trading_mode': self.trading_mode,
                'drl_enabled': self.enable_drl,
                'manual_enabled': self.enable_manual_trading,
                'drl_performance': self.drl_performance,
                'system_status': {
                    'paper_engine_active': True,
                    'drl_adapter_active': self.drl_adapter is not None,
                    'total_symbols': len(self.symbols),
                    'active_positions': len(self.paper_engine.positions)
                }
            }
            
            # Agregar estado DRL detallado si está disponible
            if self.drl_adapter:
                drl_status = self.drl_adapter.get_system_status()
                integrated_summary['drl_detailed'] = drl_status
            
            return integrated_summary
            
        except Exception as e:
            logger.error(f"Error generando resumen integrado: {e}")
            return self.paper_engine.get_portfolio_summary()
    
    def save_integrated_state(self, filepath: str):
        """
        Guarda el estado completo del sistema integrado.
        
        Args:
            filepath: Ruta del archivo
        """
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'config': {
                    'initial_capital': self.initial_capital,
                    'symbols': self.symbols,
                    'enable_drl': self.enable_drl,
                    'enable_manual_trading': self.enable_manual_trading,
                    'trading_mode': self.trading_mode
                },
                'paper_trading': self.paper_engine.get_portfolio_summary(),
                'drl_performance': self.drl_performance,
                'integrated_summary': self.get_integrated_summary()
            }
            
            # Agregar estado DRL si está disponible
            if self.drl_adapter:
                drl_state_file = filepath.replace('.json', '_drl.json')
                self.drl_adapter.save_state(drl_state_file)
                state['drl_state_file'] = drl_state_file
            
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"💾 Estado integrado guardado en: {filepath}")
            
        except Exception as e:
            logger.error(f"Error guardando estado integrado: {e}")


if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Crear sistema integrado
    integrated_system = DRLIntegratedPaperTrading(
        initial_capital=10000.0,
        symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
        enable_drl=True,
        enable_manual_trading=True
    )
    
    print("🚀 Sistema Integrado DRL + Paper Trading creado!")
    print(f"📊 Resumen: {integrated_system.get_integrated_summary()}")