"""
SICAR - Sistema de Gestión de Órdenes para Brokers Tradicionales
================================================================

Este módulo proporciona un sistema unificado de gestión de órdenes que funciona
con múltiples brokers tradicionales (Interactive Brokers, TD Ameritrade, etc.).

Características:
- Gestión unificada de órdenes multi-broker
- Enrutamiento inteligente de órdenes
- Monitoreo en tiempo real
- Gestión de riesgo integrada
- Reconciliación automática
- Reporting avanzado

Autor: SICAR Team
Fecha: Enero 2025
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

# Importar conectores
try:
    from .interactive_brokers_connector import InteractiveBrokersConnector, IBOrder, IBOrderStatus
    from .td_ameritrade_connector import TDAmeritradeConnector, TDAOrder, TDAOrderStatus
except ImportError:
    # Para testing sin dependencias
    pass

class OrderStatus(Enum):
    """Estados unificados de órdenes"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    WORKING = "WORKING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class OrderType(Enum):
    """Tipos de órdenes unificados"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"
    MOC = "MOC"  # Market on Close
    LOC = "LOC"  # Limit on Close

class OrderSide(Enum):
    """Lado de la orden"""
    BUY = "BUY"
    SELL = "SELL"
    SELL_SHORT = "SELL_SHORT"
    BUY_TO_COVER = "BUY_TO_COVER"

class BrokerType(Enum):
    """Tipos de brokers soportados"""
    INTERACTIVE_BROKERS = "IB"
    TD_AMERITRADE = "TDA"
    ALPACA = "ALPACA"
    SCHWAB = "SCHWAB"

class OrderPriority(Enum):
    """Prioridad de órdenes"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class RiskLevel(Enum):
    """Niveles de riesgo"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"

@dataclass
class UnifiedOrder:
    """Orden unificada del sistema"""
    # Identificación
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: str = ""
    broker_order_id: Optional[str] = None
    
    # Detalles de la orden
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    quantity: int = 0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    trail_amount: Optional[float] = None
    
    # Configuración
    broker: BrokerType = BrokerType.INTERACTIVE_BROKERS
    account_id: str = ""
    time_in_force: str = "DAY"
    priority: OrderPriority = OrderPriority.NORMAL
    
    # Estado
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    remaining_quantity: int = 0
    avg_fill_price: float = 0.0
    total_commission: float = 0.0
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Metadatos
    strategy_id: str = ""
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Gestión de riesgo
    risk_level: RiskLevel = RiskLevel.MEDIUM
    max_position_size: Optional[int] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    
    def __post_init__(self):
        """Post-inicialización"""
        if not self.client_order_id:
            self.client_order_id = f"SICAR_{int(time.time())}_{self.order_id[:8]}"
        
        self.remaining_quantity = self.quantity

@dataclass
class OrderExecution:
    """Ejecución de orden"""
    execution_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    broker_execution_id: str = ""
    
    quantity: int = 0
    price: float = 0.0
    commission: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Detalles adicionales
    liquidity_flag: str = ""  # Added/Removed
    exchange: str = ""
    contra_broker: str = ""

@dataclass
class RiskCheck:
    """Verificación de riesgo"""
    check_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = ""
    check_type: str = ""
    passed: bool = False
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

class BrokerConnectorInterface(ABC):
    """Interfaz para conectores de brokers"""
    
    @abstractmethod
    async def place_order(self, order: UnifiedOrder) -> Optional[str]:
        """Colocar orden"""
        pass
    
    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancelar orden"""
        pass
    
    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> Optional[Dict]:
        """Obtener estado de orden"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """Obtener posiciones"""
        pass

class OrderManagementSystem:
    """
    Sistema principal de gestión de órdenes
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Almacenamiento de órdenes
        self.orders: Dict[str, UnifiedOrder] = {}
        self.executions: Dict[str, List[OrderExecution]] = {}
        self.risk_checks: Dict[str, List[RiskCheck]] = {}
        
        # Conectores de brokers
        self.brokers: Dict[BrokerType, BrokerConnectorInterface] = {}
        
        # Configuración de riesgo
        self.risk_limits = {
            'max_order_value': 1000000,  # $1M
            'max_daily_volume': 10000000,  # $10M
            'max_position_concentration': 0.1,  # 10%
            'max_sector_exposure': 0.3,  # 30%
        }
        
        # Métricas
        self.daily_volume = 0.0
        self.daily_orders = 0
        self.daily_fills = 0
        self.daily_cancellations = 0
        
        # Callbacks
        self.order_callbacks: List[Callable] = []
        self.execution_callbacks: List[Callable] = []
        self.risk_callbacks: List[Callable] = []
        
        # Estado del sistema
        self.is_running = False
        self.monitoring_task: Optional[asyncio.Task] = None
        
    def register_broker(self, broker_type: BrokerType, connector: BrokerConnectorInterface):
        """
        Registrar conector de broker
        
        Args:
            broker_type: Tipo de broker
            connector: Instancia del conector
        """
        self.brokers[broker_type] = connector
        self.logger.info(f"Broker {broker_type.value} registrado")
    
    def add_order_callback(self, callback: Callable):
        """Agregar callback para eventos de órdenes"""
        self.order_callbacks.append(callback)
    
    def add_execution_callback(self, callback: Callable):
        """Agregar callback para ejecuciones"""
        self.execution_callbacks.append(callback)
    
    def add_risk_callback(self, callback: Callable):
        """Agregar callback para eventos de riesgo"""
        self.risk_callbacks.append(callback)
    
    async def start_monitoring(self):
        """Iniciar monitoreo del sistema"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info("Sistema de monitoreo iniciado")
    
    async def stop_monitoring(self):
        """Detener monitoreo del sistema"""
        self.is_running = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Sistema de monitoreo detenido")
    
    async def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while self.is_running:
            try:
                # Actualizar estados de órdenes
                await self._update_order_statuses()
                
                # Verificar órdenes expiradas
                await self._check_expired_orders()
                
                # Actualizar métricas
                self._update_metrics()
                
                # Esperar antes del siguiente ciclo
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error en loop de monitoreo: {e}")
                await asyncio.sleep(5)
    
    async def _update_order_statuses(self):
        """Actualizar estados de órdenes activas"""
        active_orders = [
            order for order in self.orders.values()
            if order.status in [OrderStatus.SUBMITTED, OrderStatus.WORKING, OrderStatus.PARTIALLY_FILLED]
        ]
        
        for order in active_orders:
            if order.broker_order_id and order.broker in self.brokers:
                try:
                    broker = self.brokers[order.broker]
                    status_data = await broker.get_order_status(order.broker_order_id)
                    
                    if status_data:
                        await self._process_order_update(order, status_data)
                        
                except Exception as e:
                    self.logger.error(f"Error actualizando orden {order.order_id}: {e}")
    
    async def _process_order_update(self, order: UnifiedOrder, status_data: Dict):
        """Procesar actualización de estado de orden"""
        old_status = order.status
        
        # Mapear estado del broker al estado unificado
        new_status = self._map_broker_status(status_data.get('status'), order.broker)
        
        if new_status != old_status:
            order.status = new_status
            
            # Actualizar cantidades
            if 'filled_quantity' in status_data:
                order.filled_quantity = status_data['filled_quantity']
                order.remaining_quantity = order.quantity - order.filled_quantity
            
            # Actualizar precio promedio
            if 'avg_fill_price' in status_data:
                order.avg_fill_price = status_data['avg_fill_price']
            
            # Actualizar timestamps
            if new_status == OrderStatus.FILLED and not order.filled_at:
                order.filled_at = datetime.now()
            elif new_status == OrderStatus.CANCELLED and not order.cancelled_at:
                order.cancelled_at = datetime.now()
            
            # Notificar callbacks
            await self._notify_order_callbacks(order, old_status, new_status)
            
            self.logger.info(f"Orden {order.order_id} actualizada: {old_status.value} -> {new_status.value}")
    
    def _map_broker_status(self, broker_status: str, broker_type: BrokerType) -> OrderStatus:
        """Mapear estado del broker al estado unificado"""
        if broker_type == BrokerType.INTERACTIVE_BROKERS:
            mapping = {
                'Submitted': OrderStatus.SUBMITTED,
                'PreSubmitted': OrderStatus.PENDING,
                'PendingSubmit': OrderStatus.PENDING,
                'Filled': OrderStatus.FILLED,
                'Cancelled': OrderStatus.CANCELLED,
                'ApiCancelled': OrderStatus.CANCELLED,
                'Inactive': OrderStatus.REJECTED,
            }
        elif broker_type == BrokerType.TD_AMERITRADE:
            mapping = {
                'WORKING': OrderStatus.WORKING,
                'FILLED': OrderStatus.FILLED,
                'CANCELED': OrderStatus.CANCELLED,
                'REJECTED': OrderStatus.REJECTED,
                'EXPIRED': OrderStatus.EXPIRED,
                'PENDING_ACTIVATION': OrderStatus.PENDING,
            }
        else:
            mapping = {}
        
        return mapping.get(broker_status, OrderStatus.WORKING)
    
    async def _check_expired_orders(self):
        """Verificar órdenes expiradas"""
        now = datetime.now()
        
        for order in self.orders.values():
            if order.status in [OrderStatus.SUBMITTED, OrderStatus.WORKING]:
                # Verificar si la orden ha expirado (ejemplo: 1 día para DAY orders)
                if order.time_in_force == "DAY":
                    if order.created_at.date() < now.date():
                        order.status = OrderStatus.EXPIRED
                        await self._notify_order_callbacks(order, OrderStatus.WORKING, OrderStatus.EXPIRED)
    
    def _update_metrics(self):
        """Actualizar métricas del sistema"""
        today = datetime.now().date()
        
        # Resetear métricas diarias si es un nuevo día
        if not hasattr(self, '_last_metrics_date') or self._last_metrics_date != today:
            self.daily_volume = 0.0
            self.daily_orders = 0
            self.daily_fills = 0
            self.daily_cancellations = 0
            self._last_metrics_date = today
        
        # Calcular métricas del día
        today_orders = [
            order for order in self.orders.values()
            if order.created_at.date() == today
        ]
        
        self.daily_orders = len(today_orders)
        self.daily_fills = len([o for o in today_orders if o.status == OrderStatus.FILLED])
        self.daily_cancellations = len([o for o in today_orders if o.status == OrderStatus.CANCELLED])
        
        # Calcular volumen
        self.daily_volume = sum(
            order.filled_quantity * order.avg_fill_price
            for order in today_orders
            if order.status == OrderStatus.FILLED and order.avg_fill_price > 0
        )
    
    async def place_order(self, order: UnifiedOrder) -> bool:
        """
        Colocar una orden
        
        Args:
            order: Orden a colocar
            
        Returns:
            bool: True si la orden se colocó exitosamente
        """
        try:
            # Verificaciones de riesgo
            risk_checks = await self._perform_risk_checks(order)
            
            # Si alguna verificación falla, rechazar la orden
            failed_checks = [check for check in risk_checks if not check.passed]
            if failed_checks:
                order.status = OrderStatus.REJECTED
                self.orders[order.order_id] = order
                
                for check in failed_checks:
                    await self._notify_risk_callbacks(check)
                
                self.logger.warning(f"Orden {order.order_id} rechazada por riesgo: {[c.message for c in failed_checks]}")
                return False
            
            # Verificar que el broker esté disponible
            if order.broker not in self.brokers:
                order.status = OrderStatus.REJECTED
                self.orders[order.order_id] = order
                self.logger.error(f"Broker {order.broker.value} no disponible")
                return False
            
            # Colocar orden en el broker
            broker = self.brokers[order.broker]
            broker_order_id = await broker.place_order(order)
            
            if broker_order_id:
                order.broker_order_id = broker_order_id
                order.status = OrderStatus.SUBMITTED
                order.submitted_at = datetime.now()
                
                # Almacenar orden
                self.orders[order.order_id] = order
                
                # Notificar callbacks
                await self._notify_order_callbacks(order, OrderStatus.PENDING, OrderStatus.SUBMITTED)
                
                self.logger.info(f"Orden {order.order_id} colocada exitosamente en {order.broker.value}")
                return True
            else:
                order.status = OrderStatus.REJECTED
                self.orders[order.order_id] = order
                self.logger.error(f"Error colocando orden {order.order_id} en {order.broker.value}")
                return False
                
        except Exception as e:
            order.status = OrderStatus.REJECTED
            self.orders[order.order_id] = order
            self.logger.error(f"Error colocando orden {order.order_id}: {e}")
            return False
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancelar una orden
        
        Args:
            order_id: ID de la orden a cancelar
            
        Returns:
            bool: True si la cancelación fue exitosa
        """
        try:
            if order_id not in self.orders:
                self.logger.error(f"Orden {order_id} no encontrada")
                return False
            
            order = self.orders[order_id]
            
            # Verificar que la orden se pueda cancelar
            if order.status not in [OrderStatus.SUBMITTED, OrderStatus.WORKING, OrderStatus.PARTIALLY_FILLED]:
                self.logger.warning(f"Orden {order_id} no se puede cancelar (estado: {order.status.value})")
                return False
            
            # Cancelar en el broker
            if order.broker_order_id and order.broker in self.brokers:
                broker = self.brokers[order.broker]
                success = await broker.cancel_order(order.broker_order_id)
                
                if success:
                    old_status = order.status
                    order.status = OrderStatus.CANCELLED
                    order.cancelled_at = datetime.now()
                    
                    await self._notify_order_callbacks(order, old_status, OrderStatus.CANCELLED)
                    
                    self.logger.info(f"Orden {order_id} cancelada exitosamente")
                    return True
                else:
                    self.logger.error(f"Error cancelando orden {order_id} en broker")
                    return False
            else:
                self.logger.error(f"No se puede cancelar orden {order_id}: sin broker_order_id o broker no disponible")
                return False
                
        except Exception as e:
            self.logger.error(f"Error cancelando orden {order_id}: {e}")
            return False
    
    async def _perform_risk_checks(self, order: UnifiedOrder) -> List[RiskCheck]:
        """Realizar verificaciones de riesgo"""
        checks = []
        
        # Check 1: Valor máximo de orden
        order_value = order.quantity * (order.price or 0)
        check = RiskCheck(
            order_id=order.order_id,
            check_type="max_order_value",
            passed=order_value <= self.risk_limits['max_order_value'],
            message=f"Valor de orden: ${order_value:,.2f} (límite: ${self.risk_limits['max_order_value']:,.2f})"
        )
        checks.append(check)
        
        # Check 2: Volumen diario
        projected_daily_volume = self.daily_volume + order_value
        check = RiskCheck(
            order_id=order.order_id,
            check_type="daily_volume",
            passed=projected_daily_volume <= self.risk_limits['max_daily_volume'],
            message=f"Volumen diario proyectado: ${projected_daily_volume:,.2f} (límite: ${self.risk_limits['max_daily_volume']:,.2f})"
        )
        checks.append(check)
        
        # Check 3: Tamaño de posición (si se especifica)
        if order.max_position_size:
            check = RiskCheck(
                order_id=order.order_id,
                check_type="position_size",
                passed=order.quantity <= order.max_position_size,
                message=f"Cantidad: {order.quantity} (límite: {order.max_position_size})"
            )
            checks.append(check)
        
        # Almacenar checks
        self.risk_checks[order.order_id] = checks
        
        return checks
    
    async def _notify_order_callbacks(self, order: UnifiedOrder, old_status: OrderStatus, new_status: OrderStatus):
        """Notificar callbacks de órdenes"""
        for callback in self.order_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order, old_status, new_status)
                else:
                    callback(order, old_status, new_status)
            except Exception as e:
                self.logger.error(f"Error en callback de orden: {e}")
    
    async def _notify_execution_callbacks(self, execution: OrderExecution):
        """Notificar callbacks de ejecuciones"""
        for callback in self.execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(execution)
                else:
                    callback(execution)
            except Exception as e:
                self.logger.error(f"Error en callback de ejecución: {e}")
    
    async def _notify_risk_callbacks(self, risk_check: RiskCheck):
        """Notificar callbacks de riesgo"""
        for callback in self.risk_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(risk_check)
                else:
                    callback(risk_check)
            except Exception as e:
                self.logger.error(f"Error en callback de riesgo: {e}")
    
    def get_orders(self, status: Optional[OrderStatus] = None, 
                   broker: Optional[BrokerType] = None,
                   symbol: Optional[str] = None) -> List[UnifiedOrder]:
        """
        Obtener órdenes con filtros opcionales
        
        Args:
            status: Filtrar por estado
            broker: Filtrar por broker
            symbol: Filtrar por símbolo
            
        Returns:
            Lista de órdenes filtradas
        """
        orders = list(self.orders.values())
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        if broker:
            orders = [o for o in orders if o.broker == broker]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        return orders
    
    def get_order_by_id(self, order_id: str) -> Optional[UnifiedOrder]:
        """Obtener orden por ID"""
        return self.orders.get(order_id)
    
    def get_executions(self, order_id: Optional[str] = None) -> List[OrderExecution]:
        """Obtener ejecuciones"""
        if order_id:
            return self.executions.get(order_id, [])
        else:
            all_executions = []
            for executions in self.executions.values():
                all_executions.extend(executions)
            return all_executions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema"""
        total_orders = len(self.orders)
        filled_orders = len([o for o in self.orders.values() if o.status == OrderStatus.FILLED])
        cancelled_orders = len([o for o in self.orders.values() if o.status == OrderStatus.CANCELLED])
        
        fill_rate = (filled_orders / max(total_orders, 1)) * 100
        cancel_rate = (cancelled_orders / max(total_orders, 1)) * 100
        
        return {
            'total_orders': total_orders,
            'filled_orders': filled_orders,
            'cancelled_orders': cancelled_orders,
            'fill_rate': fill_rate,
            'cancel_rate': cancel_rate,
            'daily_volume': self.daily_volume,
            'daily_orders': self.daily_orders,
            'daily_fills': self.daily_fills,
            'daily_cancellations': self.daily_cancellations,
            'active_brokers': len(self.brokers),
            'is_monitoring': self.is_running
        }
    
    def export_orders_to_dataframe(self) -> pd.DataFrame:
        """Exportar órdenes a DataFrame"""
        if not self.orders:
            return pd.DataFrame()
        
        data = []
        for order in self.orders.values():
            data.append({
                'order_id': order.order_id,
                'client_order_id': order.client_order_id,
                'broker_order_id': order.broker_order_id,
                'symbol': order.symbol,
                'side': order.side.value,
                'order_type': order.order_type.value,
                'quantity': order.quantity,
                'price': order.price,
                'stop_price': order.stop_price,
                'broker': order.broker.value,
                'account_id': order.account_id,
                'status': order.status.value,
                'filled_quantity': order.filled_quantity,
                'remaining_quantity': order.remaining_quantity,
                'avg_fill_price': order.avg_fill_price,
                'total_commission': order.total_commission,
                'created_at': order.created_at,
                'submitted_at': order.submitted_at,
                'filled_at': order.filled_at,
                'cancelled_at': order.cancelled_at,
                'strategy_id': order.strategy_id,
                'risk_level': order.risk_level.value
            })
        
        return pd.DataFrame(data)

# Funciones de utilidad
def create_market_order(symbol: str, side: OrderSide, quantity: int,
                       broker: BrokerType = BrokerType.INTERACTIVE_BROKERS,
                       account_id: str = "") -> UnifiedOrder:
    """Crear orden de mercado"""
    return UnifiedOrder(
        symbol=symbol,
        side=side,
        order_type=OrderType.MARKET,
        quantity=quantity,
        broker=broker,
        account_id=account_id
    )

def create_limit_order(symbol: str, side: OrderSide, quantity: int, price: float,
                      broker: BrokerType = BrokerType.INTERACTIVE_BROKERS,
                      account_id: str = "") -> UnifiedOrder:
    """Crear orden límite"""
    return UnifiedOrder(
        symbol=symbol,
        side=side,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        price=price,
        broker=broker,
        account_id=account_id
    )

def create_stop_order(symbol: str, side: OrderSide, quantity: int, stop_price: float,
                     broker: BrokerType = BrokerType.INTERACTIVE_BROKERS,
                     account_id: str = "") -> UnifiedOrder:
    """Crear orden stop"""
    return UnifiedOrder(
        symbol=symbol,
        side=side,
        order_type=OrderType.STOP,
        quantity=quantity,
        stop_price=stop_price,
        broker=broker,
        account_id=account_id
    )

# Demo y testing
if __name__ == "__main__":
    async def demo():
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        
        print("=== SICAR - Sistema de Gestión de Órdenes Demo ===\n")
        
        # Crear sistema
        oms = OrderManagementSystem()
        
        # Simular registro de brokers (sin conectores reales)
        print("1. Registrando brokers simulados...")
        
        class MockBroker(BrokerConnectorInterface):
            def __init__(self, name):
                self.name = name
                self.orders = {}
            
            async def place_order(self, order: UnifiedOrder) -> Optional[str]:
                broker_id = f"{self.name}_{int(time.time())}"
                self.orders[broker_id] = order
                return broker_id
            
            async def cancel_order(self, broker_order_id: str) -> bool:
                return broker_order_id in self.orders
            
            async def get_order_status(self, broker_order_id: str) -> Optional[Dict]:
                if broker_order_id in self.orders:
                    return {'status': 'FILLED', 'filled_quantity': self.orders[broker_order_id].quantity}
                return None
            
            async def get_positions(self) -> List[Dict]:
                return []
        
        oms.register_broker(BrokerType.INTERACTIVE_BROKERS, MockBroker("IB"))
        oms.register_broker(BrokerType.TD_AMERITRADE, MockBroker("TDA"))
        print("   ✓ Brokers registrados")
        
        # Configurar callbacks
        print("\n2. Configurando callbacks...")
        
        async def order_callback(order, old_status, new_status):
            print(f"   📋 Orden {order.order_id[:8]}: {old_status.value} -> {new_status.value}")
        
        async def risk_callback(risk_check):
            if not risk_check.passed:
                print(f"   ⚠️  Riesgo: {risk_check.check_type} - {risk_check.message}")
        
        oms.add_order_callback(order_callback)
        oms.add_risk_callback(risk_callback)
        print("   ✓ Callbacks configurados")
        
        # Iniciar monitoreo
        print("\n3. Iniciando sistema de monitoreo...")
        await oms.start_monitoring()
        print("   ✓ Monitoreo iniciado")
        
        # Crear y colocar órdenes de prueba
        print("\n4. Colocando órdenes de prueba...")
        
        # Orden de mercado
        market_order = create_market_order("SPY", OrderSide.BUY, 100, BrokerType.INTERACTIVE_BROKERS, "IB123")
        market_order.strategy_id = "DEMO_STRATEGY"
        success = await oms.place_order(market_order)
        print(f"   📈 Orden de mercado SPY: {'✓' if success else '✗'}")
        
        # Orden límite
        limit_order = create_limit_order("QQQ", OrderSide.BUY, 50, 380.50, BrokerType.TD_AMERITRADE, "TDA456")
        limit_order.strategy_id = "DEMO_STRATEGY"
        success = await oms.place_order(limit_order)
        print(f"   📊 Orden límite QQQ: {'✓' if success else '✗'}")
        
        # Orden stop
        stop_order = create_stop_order("IWM", OrderSide.SELL, 200, 195.00, BrokerType.INTERACTIVE_BROKERS, "IB123")
        stop_order.strategy_id = "DEMO_STRATEGY"
        success = await oms.place_order(stop_order)
        print(f"   🛑 Orden stop IWM: {'✓' if success else '✗'}")
        
        # Orden que falla verificación de riesgo
        print("\n5. Probando verificaciones de riesgo...")
        risky_order = create_market_order("TSLA", OrderSide.BUY, 1000000, BrokerType.INTERACTIVE_BROKERS, "IB123")
        risky_order.strategy_id = "RISKY_STRATEGY"
        success = await oms.place_order(risky_order)
        print(f"   ⚠️  Orden riesgosa TSLA: {'✓' if success else '✗ (rechazada por riesgo)'}")
        
        # Esperar un poco para que se procesen las actualizaciones
        print("\n6. Esperando actualizaciones...")
        await asyncio.sleep(3)
        
        # Mostrar estadísticas
        print("\n7. Estadísticas del sistema:")
        stats = oms.get_statistics()
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.2f}")
            else:
                print(f"   {key}: {value}")
        
        # Mostrar órdenes
        print("\n8. Órdenes en el sistema:")
        orders = oms.get_orders()
        for order in orders:
            print(f"   {order.order_id[:8]} | {order.symbol} | {order.side.value} {order.quantity} | {order.status.value}")
        
        # Exportar a DataFrame
        print("\n9. Exportando datos...")
        df = oms.export_orders_to_dataframe()
        print(f"   ✓ DataFrame creado con {len(df)} órdenes")
        
        # Detener monitoreo
        print("\n10. Deteniendo sistema...")
        await oms.stop_monitoring()
        print("   ✓ Sistema detenido")
        
        print("\n=== Demo Completado ===")
    
    # Ejecutar demo
    asyncio.run(demo())