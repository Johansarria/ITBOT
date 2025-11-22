"""
SICAR - Conector Interactive Brokers
===================================

Este módulo proporciona conectividad con Interactive Brokers (IBKR) para trading de índices ETF.
Incluye autenticación, gestión de órdenes, datos de mercado en tiempo real y gestión de posiciones.

Autor: SICAR Team
Fecha: Enero 2025
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
import pandas as pd
import numpy as np

# Simulación de la API de Interactive Brokers (ib_insync)
# En producción, usar: from ib_insync import IB, Stock, Order, MarketOrder, LimitOrder, etc.

class OrderType(Enum):
    """Tipos de órdenes soportadas"""
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP LMT"
    TRAIL = "TRAIL"
    TRAIL_LIMIT = "TRAIL LIMIT"

class OrderAction(Enum):
    """Acciones de orden"""
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    """Estados de orden"""
    PENDING = "PendingSubmit"
    SUBMITTED = "Submitted"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "ApiCancelled"

class ConnectionStatus(Enum):
    """Estados de conexión"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class IBOrder:
    """Representación de una orden de Interactive Brokers"""
    order_id: int
    symbol: str
    action: OrderAction
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "DAY"
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    commission: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None

@dataclass
class IBPosition:
    """Representación de una posición en Interactive Brokers"""
    symbol: str
    quantity: int
    avg_cost: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    realized_pnl: float
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class IBMarketData:
    """Datos de mercado de Interactive Brokers"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    high: float
    low: float
    close: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class IBAccountInfo:
    """Información de cuenta de Interactive Brokers"""
    account_id: str
    net_liquidation: float
    total_cash: float
    buying_power: float
    gross_position_value: float
    unrealized_pnl: float
    realized_pnl: float
    available_funds: float
    excess_liquidity: float
    updated_at: datetime = field(default_factory=datetime.now)

class InteractiveBrokersConnector:
    """
    Conector principal para Interactive Brokers
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        self.host = host
        self.port = port
        self.client_id = client_id
        
        self.logger = logging.getLogger(__name__)
        self.connection_status = ConnectionStatus.DISCONNECTED
        
        # Simulación de conexión IB (en producción usar ib_insync.IB())
        self.ib = None
        self.is_connected = False
        
        # Almacenamiento de datos
        self.orders: Dict[int, IBOrder] = {}
        self.positions: Dict[str, IBPosition] = {}
        self.market_data: Dict[str, IBMarketData] = {}
        self.account_info: Optional[IBAccountInfo] = None
        
        # Callbacks
        self.order_callbacks: List[Callable] = []
        self.position_callbacks: List[Callable] = []
        self.market_data_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        # Control de threading
        self.data_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Configuración
        self.max_retries = 3
        self.retry_delay = 5
        self.heartbeat_interval = 30
        
        # Contadores
        self.next_order_id = 1
        self.total_orders = 0
        self.successful_orders = 0
        
    async def connect(self) -> bool:
        """
        Conectar a Interactive Brokers TWS/Gateway
        
        Returns:
            bool: True si la conexión es exitosa
        """
        try:
            self.logger.info(f"Conectando a IB en {self.host}:{self.port}")
            self.connection_status = ConnectionStatus.CONNECTING
            
            # En producción, usar:
            # self.ib = IB()
            # await self.ib.connectAsync(self.host, self.port, clientId=self.client_id)
            
            # Simulación de conexión exitosa
            await asyncio.sleep(1)
            self.is_connected = True
            self.connection_status = ConnectionStatus.CONNECTED
            
            # Inicializar datos de cuenta
            await self._initialize_account_data()
            
            # Iniciar thread de monitoreo
            self._start_monitoring_thread()
            
            self.logger.info("Conexión a Interactive Brokers establecida")
            return True
            
        except Exception as e:
            self.logger.error(f"Error conectando a IB: {e}")
            self.connection_status = ConnectionStatus.ERROR
            return False
    
    async def disconnect(self):
        """Desconectar de Interactive Brokers"""
        try:
            self.logger.info("Desconectando de Interactive Brokers")
            
            # Detener thread de monitoreo
            self.stop_event.set()
            if self.data_thread and self.data_thread.is_alive():
                self.data_thread.join(timeout=5)
            
            # En producción, usar:
            # if self.ib:
            #     self.ib.disconnect()
            
            self.is_connected = False
            self.connection_status = ConnectionStatus.DISCONNECTED
            
            self.logger.info("Desconectado de Interactive Brokers")
            
        except Exception as e:
            self.logger.error(f"Error desconectando de IB: {e}")
    
    async def _initialize_account_data(self):
        """Inicializar datos de cuenta"""
        try:
            # En producción, obtener datos reales de la cuenta
            # account_summary = await self.ib.accountSummaryAsync()
            
            # Simulación de datos de cuenta
            self.account_info = IBAccountInfo(
                account_id="DU123456",
                net_liquidation=100000.0,
                total_cash=50000.0,
                buying_power=200000.0,
                gross_position_value=50000.0,
                unrealized_pnl=1500.0,
                realized_pnl=2500.0,
                available_funds=150000.0,
                excess_liquidity=150000.0
            )
            
            self.logger.info("Datos de cuenta inicializados")
            
        except Exception as e:
            self.logger.error(f"Error inicializando datos de cuenta: {e}")
    
    def _start_monitoring_thread(self):
        """Iniciar thread de monitoreo de datos"""
        self.data_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.data_thread.start()
        self.logger.info("Thread de monitoreo iniciado")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while not self.stop_event.is_set():
            try:
                if self.is_connected:
                    # Actualizar datos de mercado
                    self._update_market_data()
                    
                    # Actualizar posiciones
                    self._update_positions()
                    
                    # Verificar órdenes
                    self._check_orders()
                
                time.sleep(1)  # Actualizar cada segundo
                
            except Exception as e:
                self.logger.error(f"Error en loop de monitoreo: {e}")
                time.sleep(5)
    
    def _update_market_data(self):
        """Actualizar datos de mercado (simulación)"""
        # En producción, obtener datos reales del mercado
        symbols = ['SPY', 'QQQ', 'IWM', 'DIA', 'VTI']
        
        for symbol in symbols:
            # Simulación de datos de mercado
            base_price = {'SPY': 450, 'QQQ': 380, 'IWM': 200, 'DIA': 350, 'VTI': 240}.get(symbol, 100)
            variation = np.random.normal(0, 0.5)
            
            self.market_data[symbol] = IBMarketData(
                symbol=symbol,
                bid=base_price + variation - 0.01,
                ask=base_price + variation + 0.01,
                last=base_price + variation,
                volume=np.random.randint(1000000, 5000000),
                high=base_price + variation + 2,
                low=base_price + variation - 2,
                close=base_price + variation - 0.5
            )
    
    def _update_positions(self):
        """Actualizar posiciones (simulación)"""
        # En producción, obtener posiciones reales
        # positions = await self.ib.positionsAsync()
        pass
    
    def _check_orders(self):
        """Verificar estado de órdenes"""
        for order_id, order in self.orders.items():
            if order.status == OrderStatus.SUBMITTED:
                # Simulación de llenado de orden
                if np.random.random() < 0.1:  # 10% probabilidad de llenado por ciclo
                    self._simulate_order_fill(order)
    
    def _simulate_order_fill(self, order: IBOrder):
        """Simular llenado de orden"""
        market_data = self.market_data.get(order.symbol)
        if not market_data:
            return
        
        # Determinar precio de llenado
        if order.order_type == OrderType.MARKET:
            fill_price = market_data.ask if order.action == OrderAction.BUY else market_data.bid
        elif order.order_type == OrderType.LIMIT and order.price:
            fill_price = order.price
        else:
            return
        
        # Actualizar orden
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price
        order.commission = order.quantity * 0.005  # $0.005 por acción
        order.filled_at = datetime.now()
        
        # Actualizar posición
        self._update_position_from_fill(order)
        
        # Notificar callbacks
        for callback in self.order_callbacks:
            try:
                callback(order)
            except Exception as e:
                self.logger.error(f"Error en callback de orden: {e}")
        
        self.successful_orders += 1
        self.logger.info(f"Orden {order.order_id} llenada: {order.quantity} {order.symbol} @ ${fill_price:.2f}")
    
    def _update_position_from_fill(self, order: IBOrder):
        """Actualizar posición basada en llenado de orden"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            self.positions[symbol] = IBPosition(
                symbol=symbol,
                quantity=0,
                avg_cost=0.0,
                market_price=order.avg_fill_price,
                market_value=0.0,
                unrealized_pnl=0.0,
                realized_pnl=0.0
            )
        
        position = self.positions[symbol]
        
        if order.action == OrderAction.BUY:
            # Compra - aumentar posición
            total_cost = position.quantity * position.avg_cost + order.filled_quantity * order.avg_fill_price
            position.quantity += order.filled_quantity
            position.avg_cost = total_cost / position.quantity if position.quantity > 0 else 0
        else:
            # Venta - reducir posición
            position.quantity -= order.filled_quantity
            if position.quantity < 0:
                position.quantity = 0  # No permitir posiciones cortas por simplicidad
        
        # Actualizar valores de mercado
        market_data = self.market_data.get(symbol)
        if market_data:
            position.market_price = market_data.last
            position.market_value = position.quantity * position.market_price
            position.unrealized_pnl = (position.market_price - position.avg_cost) * position.quantity
        
        position.updated_at = datetime.now()
    
    async def place_order(self, symbol: str, action: OrderAction, quantity: int,
                         order_type: OrderType = OrderType.MARKET,
                         price: Optional[float] = None,
                         stop_price: Optional[float] = None) -> Optional[IBOrder]:
        """
        Colocar una orden
        
        Args:
            symbol: Símbolo del instrumento
            action: BUY o SELL
            quantity: Cantidad de acciones
            order_type: Tipo de orden
            price: Precio límite (para órdenes LIMIT)
            stop_price: Precio de stop (para órdenes STOP)
            
        Returns:
            IBOrder: Orden creada o None si hay error
        """
        try:
            if not self.is_connected:
                self.logger.error("No conectado a Interactive Brokers")
                return None
            
            # Validaciones
            if quantity <= 0:
                self.logger.error("Cantidad debe ser positiva")
                return None
            
            if order_type == OrderType.LIMIT and price is None:
                self.logger.error("Precio requerido para orden LIMIT")
                return None
            
            # Crear orden
            order = IBOrder(
                order_id=self.next_order_id,
                symbol=symbol,
                action=action,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                status=OrderStatus.SUBMITTED
            )
            
            # En producción, enviar orden real:
            # contract = Stock(symbol, 'SMART', 'USD')
            # ib_order = MarketOrder(action.value, quantity) if order_type == OrderType.MARKET else LimitOrder(action.value, quantity, price)
            # trade = self.ib.placeOrder(contract, ib_order)
            
            # Almacenar orden
            self.orders[order.order_id] = order
            self.next_order_id += 1
            self.total_orders += 1
            
            self.logger.info(f"Orden colocada: {order.order_id} - {action.value} {quantity} {symbol}")
            return order
            
        except Exception as e:
            self.logger.error(f"Error colocando orden: {e}")
            return None
    
    async def cancel_order(self, order_id: int) -> bool:
        """
        Cancelar una orden
        
        Args:
            order_id: ID de la orden a cancelar
            
        Returns:
            bool: True si la cancelación es exitosa
        """
        try:
            if order_id not in self.orders:
                self.logger.error(f"Orden {order_id} no encontrada")
                return False
            
            order = self.orders[order_id]
            
            if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                self.logger.error(f"Orden {order_id} ya está {order.status.value}")
                return False
            
            # En producción, cancelar orden real:
            # self.ib.cancelOrder(order)
            
            order.status = OrderStatus.CANCELLED
            
            self.logger.info(f"Orden {order_id} cancelada")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cancelando orden {order_id}: {e}")
            return False
    
    def get_positions(self) -> Dict[str, IBPosition]:
        """Obtener todas las posiciones"""
        return self.positions.copy()
    
    def get_position(self, symbol: str) -> Optional[IBPosition]:
        """Obtener posición específica"""
        return self.positions.get(symbol)
    
    def get_orders(self, symbol: Optional[str] = None) -> List[IBOrder]:
        """Obtener órdenes, opcionalmente filtradas por símbolo"""
        orders = list(self.orders.values())
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        return orders
    
    def get_market_data(self, symbol: str) -> Optional[IBMarketData]:
        """Obtener datos de mercado para un símbolo"""
        return self.market_data.get(symbol)
    
    def get_account_info(self) -> Optional[IBAccountInfo]:
        """Obtener información de cuenta"""
        return self.account_info
    
    def subscribe_to_market_data(self, symbols: List[str]):
        """Suscribirse a datos de mercado en tiempo real"""
        try:
            for symbol in symbols:
                # En producción, suscribirse a datos reales:
                # contract = Stock(symbol, 'SMART', 'USD')
                # self.ib.reqMktData(contract, '', False, False)
                
                self.logger.info(f"Suscrito a datos de mercado: {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error suscribiéndose a datos de mercado: {e}")
    
    def add_order_callback(self, callback: Callable[[IBOrder], None]):
        """Agregar callback para eventos de órdenes"""
        self.order_callbacks.append(callback)
    
    def add_position_callback(self, callback: Callable[[IBPosition], None]):
        """Agregar callback para eventos de posiciones"""
        self.position_callbacks.append(callback)
    
    def add_market_data_callback(self, callback: Callable[[IBMarketData], None]):
        """Agregar callback para datos de mercado"""
        self.market_data_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable[[str], None]):
        """Agregar callback para errores"""
        self.error_callbacks.append(callback)
    
    def get_connection_status(self) -> ConnectionStatus:
        """Obtener estado de conexión"""
        return self.connection_status
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del conector"""
        return {
            'connection_status': self.connection_status.value,
            'total_orders': self.total_orders,
            'successful_orders': self.successful_orders,
            'success_rate': self.successful_orders / max(self.total_orders, 1) * 100,
            'active_positions': len([p for p in self.positions.values() if p.quantity > 0]),
            'total_market_value': sum(p.market_value for p in self.positions.values()),
            'total_unrealized_pnl': sum(p.unrealized_pnl for p in self.positions.values()),
            'symbols_tracked': len(self.market_data),
            'uptime': datetime.now() - datetime.now(),  # Placeholder
        }
    
    async def get_historical_data(self, symbol: str, duration: str = "1 D",
                                bar_size: str = "1 min") -> pd.DataFrame:
        """
        Obtener datos históricos
        
        Args:
            symbol: Símbolo del instrumento
            duration: Duración de los datos (ej: "1 D", "1 W", "1 M")
            bar_size: Tamaño de las barras (ej: "1 min", "5 mins", "1 hour")
            
        Returns:
            DataFrame con datos históricos
        """
        try:
            # En producción, obtener datos históricos reales:
            # contract = Stock(symbol, 'SMART', 'USD')
            # bars = await self.ib.reqHistoricalDataAsync(
            #     contract, endDateTime='', durationStr=duration,
            #     barSizeSetting=bar_size, whatToShow='TRADES', useRTH=True
            # )
            
            # Simulación de datos históricos
            periods = 100
            dates = pd.date_range(end=datetime.now(), periods=periods, freq='1min')
            
            base_price = {'SPY': 450, 'QQQ': 380, 'IWM': 200, 'DIA': 350, 'VTI': 240}.get(symbol, 100)
            
            # Generar datos simulados
            returns = np.random.normal(0, 0.001, periods)
            prices = base_price * np.exp(np.cumsum(returns))
            
            data = pd.DataFrame({
                'datetime': dates,
                'open': prices * (1 + np.random.normal(0, 0.0005, periods)),
                'high': prices * (1 + np.abs(np.random.normal(0, 0.001, periods))),
                'low': prices * (1 - np.abs(np.random.normal(0, 0.001, periods))),
                'close': prices,
                'volume': np.random.randint(100000, 1000000, periods)
            })
            
            data.set_index('datetime', inplace=True)
            
            self.logger.info(f"Datos históricos obtenidos para {symbol}: {len(data)} barras")
            return data
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos históricos para {symbol}: {e}")
            return pd.DataFrame()

# Función de utilidad para crear conexión
async def create_ib_connection(host: str = "127.0.0.1", port: int = 7497, 
                              client_id: int = 1) -> Optional[InteractiveBrokersConnector]:
    """
    Crear y establecer conexión con Interactive Brokers
    
    Args:
        host: Dirección del servidor TWS/Gateway
        port: Puerto de conexión
        client_id: ID del cliente
        
    Returns:
        InteractiveBrokersConnector conectado o None si falla
    """
    connector = InteractiveBrokersConnector(host, port, client_id)
    
    if await connector.connect():
        return connector
    else:
        return None

# Demo y testing
if __name__ == "__main__":
    async def demo():
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        
        print("=== SICAR - Conector Interactive Brokers Demo ===\n")
        
        # Crear conexión
        print("1. Conectando a Interactive Brokers...")
        ib_connector = await create_ib_connection()
        
        if not ib_connector:
            print("   ✗ Error conectando a IB")
            return
        
        print("   ✓ Conectado exitosamente")
        
        # Suscribirse a datos de mercado
        print("\n2. Suscribiéndose a datos de mercado...")
        symbols = ['SPY', 'QQQ', 'IWM']
        ib_connector.subscribe_to_market_data(symbols)
        
        # Esperar datos de mercado
        await asyncio.sleep(2)
        
        # Mostrar datos de mercado
        print("\n3. Datos de mercado actuales:")
        for symbol in symbols:
            data = ib_connector.get_market_data(symbol)
            if data:
                print(f"   {symbol}: ${data.last:.2f} (Bid: ${data.bid:.2f}, Ask: ${data.ask:.2f})")
        
        # Colocar orden de prueba
        print("\n4. Colocando orden de prueba...")
        order = await ib_connector.place_order(
            symbol='SPY',
            action=OrderAction.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        if order:
            print(f"   ✓ Orden colocada: {order.order_id}")
        
        # Esperar posible llenado
        await asyncio.sleep(3)
        
        # Verificar órdenes
        print("\n5. Estado de órdenes:")
        orders = ib_connector.get_orders()
        for order in orders:
            print(f"   Orden {order.order_id}: {order.status.value} - {order.action.value} {order.quantity} {order.symbol}")
        
        # Mostrar posiciones
        print("\n6. Posiciones actuales:")
        positions = ib_connector.get_positions()
        for symbol, position in positions.items():
            if position.quantity > 0:
                print(f"   {symbol}: {position.quantity} acciones @ ${position.avg_cost:.2f} (P&L: ${position.unrealized_pnl:.2f})")
        
        # Mostrar información de cuenta
        print("\n7. Información de cuenta:")
        account = ib_connector.get_account_info()
        if account:
            print(f"   Liquidación neta: ${account.net_liquidation:,.2f}")
            print(f"   Poder de compra: ${account.buying_power:,.2f}")
            print(f"   P&L no realizado: ${account.unrealized_pnl:,.2f}")
        
        # Obtener datos históricos
        print("\n8. Obteniendo datos históricos...")
        historical_data = await ib_connector.get_historical_data('SPY', '1 D', '5 mins')
        print(f"   ✓ {len(historical_data)} barras históricas obtenidas")
        
        # Mostrar estadísticas
        print("\n9. Estadísticas del conector:")
        stats = ib_connector.get_statistics()
        for key, value in stats.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.2f}")
            else:
                print(f"   {key}: {value}")
        
        # Desconectar
        print("\n10. Desconectando...")
        await ib_connector.disconnect()
        print("    ✓ Desconectado")
        
        print("\n=== Demo Completado ===")
    
    # Ejecutar demo
    asyncio.run(demo())