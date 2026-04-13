# strategies/real_time_paper_trader.py

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import json
import sqlite3
from pathlib import Path
import websockets
import aiohttp
from collections import defaultdict, deque
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import schedule

# Importar componentes de la estrategia
from .advanced_spot_strategy import AdvancedSpotStrategy, SpotSignal
from .advanced_risk_manager import AdvancedRiskManager, RiskMetrics
from .quality_filters import QualityFilterEngine, QualityAssessment
from .multi_timeframe_analyzer import MultiTimeframeAnalyzer
from .dynamic_optimizer import DynamicOptimizer

# Importar utilidades del proyecto
try:
    from ..utils.binance_client import BinanceClient
    from ..config import BINANCE_API_KEY, BINANCE_SECRET_KEY
except ImportError:
    # Fallback para testing
    BinanceClient = None
    BINANCE_API_KEY = "test_key"
    BINANCE_SECRET_KEY = "test_secret"

logger = logging.getLogger(__name__)

class TradingMode(Enum):
    """Modos de trading"""
    PAPER = "paper"  # Paper trading
    LIVE = "live"    # Trading real
    SIMULATION = "simulation"  # Simulación acelerada

class OrderStatus(Enum):
    """Estados de orden"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIAL = "partial"

class AlertType(Enum):
    """Tipos de alerta"""
    SIGNAL = "signal"
    RISK = "risk"
    PERFORMANCE = "performance"
    ERROR = "error"
    INFO = "info"

@dataclass
class PaperOrder:
    """Orden de paper trading"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit'
    quantity: float
    price: float
    timestamp: datetime
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    filled_timestamp: Optional[datetime] = None
    
    # Metadatos
    signal_strength: float = 0.0
    strategy_name: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'status': self.status.value,
            'filled_price': self.filled_price,
            'filled_quantity': self.filled_quantity,
            'filled_timestamp': self.filled_timestamp.isoformat() if self.filled_timestamp else None,
            'signal_strength': self.signal_strength,
            'strategy_name': self.strategy_name,
            'notes': self.notes
        }

@dataclass
class PaperPosition:
    """Posición de paper trading"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    entry_timestamp: datetime
    last_update: datetime
    
    # Stop loss y take profit
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'quantity': self.quantity,
            'avg_price': self.avg_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'entry_timestamp': self.entry_timestamp.isoformat(),
            'last_update': self.last_update.isoformat(),
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit
        }

@dataclass
class TradingAlert:
    """Alerta de trading"""
    id: str
    alert_type: AlertType
    symbol: str
    message: str
    timestamp: datetime
    severity: str = "info"  # 'low', 'medium', 'high', 'critical'
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.alert_type.value,
            'symbol': self.symbol,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity,
            'data': self.data
        }

@dataclass
class TradingConfig:
    """Configuración de trading en tiempo real"""
    # Modo de trading
    trading_mode: TradingMode = TradingMode.PAPER
    
    # Capital
    initial_capital: float = 500.0
    
    # Símbolos a tradear
    symbols: List[str] = field(default_factory=lambda: ["BNBUSDT", "SOLUSDT"])
    
    # Configuración de órdenes
    max_position_size: float = 0.4  # 40% del capital por posición
    max_total_exposure: float = 0.8  # 80% exposición total máxima
    min_order_size: float = 10.0    # $10 mínimo por orden
    
    # Timeframes
    primary_timeframe: str = "5m"
    update_frequency: int = 30  # segundos
    
    # Gestión de riesgo
    enable_risk_management: bool = True
    max_daily_loss: float = 0.05  # 5%
    max_drawdown: float = 0.15    # 15%
    
    # Filtros de calidad
    enable_quality_filters: bool = True
    min_quality_score: float = 0.6
    
    # Optimización dinámica
    enable_dynamic_optimization: bool = True
    optimization_frequency: str = "hourly"  # 'never', 'hourly', 'daily'
    
    # Alertas
    enable_alerts: bool = True
    alert_channels: List[str] = field(default_factory=lambda: ["console", "file"])
    
    # Reportes
    enable_reporting: bool = True
    report_frequency: str = "daily"  # 'hourly', 'daily', 'weekly'
    
    # Persistencia
    save_to_database: bool = True
    database_path: str = "paper_trading.db"
    
    # API
    enable_web_interface: bool = True
    web_port: int = 8080

class RealTimePaperTrader:
    """Sistema de paper trading en tiempo real"""
    
    def __init__(self, config: TradingConfig = None):
        self.config = config or TradingConfig()
        
        # Componentes de la estrategia
        self.strategy = AdvancedSpotStrategy()
        self.risk_manager = AdvancedRiskManager()
        self.quality_filter = QualityFilterEngine() if self.config.enable_quality_filters else None
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        self.optimizer = DynamicOptimizer() if self.config.enable_dynamic_optimization else None
        
        # Estado del trading
        self.current_capital = self.config.initial_capital
        self.positions: Dict[str, PaperPosition] = {}
        self.orders: List[PaperOrder] = []
        self.alerts: List[TradingAlert] = []
        
        # Datos de mercado en tiempo real
        self.market_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.current_prices: Dict[str, float] = {}
        self.last_update: Dict[str, datetime] = {}
        
        # Métricas en tiempo real
        self.performance_metrics: Dict[str, Any] = {}
        self.daily_pnl: float = 0.0
        self.total_pnl: float = 0.0
        self.max_drawdown: float = 0.0
        self.peak_capital: float = self.config.initial_capital
        
        # Control de ejecución
        self.is_running = False
        self.is_trading_enabled = True
        self.last_signal_time: Dict[str, datetime] = {}
        
        # Hilos y tareas
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.websocket_task: Optional[asyncio.Task] = None
        self.trading_task: Optional[asyncio.Task] = None
        
        # Base de datos
        if self.config.save_to_database:
            self._init_database()
        
        # Cliente de Binance
        self.binance_client = None
        if BinanceClient:
            try:
                self.binance_client = BinanceClient()
            except Exception as e:
                logger.warning(f"No se pudo inicializar cliente Binance: {e}")
        
        # Callbacks
        self.signal_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        self.performance_callbacks: List[Callable] = []
        
        logger.info(f"RealTimePaperTrader inicializado en modo {self.config.trading_mode.value}")
    
    def _init_database(self):
        """Inicializa base de datos"""
        conn = sqlite3.connect(self.config.database_path)
        
        # Tabla de órdenes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                symbol TEXT,
                side TEXT,
                order_type TEXT,
                quantity REAL,
                price REAL,
                timestamp TEXT,
                status TEXT,
                filled_price REAL,
                filled_quantity REAL,
                filled_timestamp TEXT,
                signal_strength REAL,
                strategy_name TEXT,
                notes TEXT
            )
        """)
        
        # Tabla de posiciones
        conn.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                quantity REAL,
                avg_price REAL,
                current_price REAL,
                unrealized_pnl REAL,
                realized_pnl REAL,
                entry_timestamp TEXT,
                last_update TEXT,
                stop_loss REAL,
                take_profit REAL
            )
        """)
        
        # Tabla de alertas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                alert_type TEXT,
                symbol TEXT,
                message TEXT,
                timestamp TEXT,
                severity TEXT,
                data TEXT
            )
        """)
        
        # Tabla de métricas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                timestamp TEXT PRIMARY KEY,
                capital REAL,
                total_pnl REAL,
                daily_pnl REAL,
                drawdown REAL,
                num_positions INTEGER,
                data TEXT
            )
        """)
        
        conn.close()
    
    async def start(self):
        """Inicia el sistema de trading"""
        if self.is_running:
            logger.warning("El sistema ya está ejecutándose")
            return
        
        logger.info("Iniciando sistema de paper trading...")
        self.is_running = True
        
        try:
            # Inicializar cliente Binance si está disponible
            if self.binance_client:
                await self.binance_client.initialize()
            
            # Iniciar tareas asíncronas
            tasks = []
            
            # Tarea de datos de mercado
            if self.binance_client:
                self.websocket_task = asyncio.create_task(self._websocket_handler())
                tasks.append(self.websocket_task)
            else:
                # Simulación de datos
                self.websocket_task = asyncio.create_task(self._simulate_market_data())
                tasks.append(self.websocket_task)
            
            # Tarea principal de trading
            self.trading_task = asyncio.create_task(self._trading_loop())
            tasks.append(self.trading_task)
            
            # Tarea de reportes
            if self.config.enable_reporting:
                report_task = asyncio.create_task(self._reporting_loop())
                tasks.append(report_task)
            
            # Tarea de optimización
            if self.config.enable_dynamic_optimization and self.optimizer:
                optimization_task = asyncio.create_task(self._optimization_loop())
                tasks.append(optimization_task)
            
            # Esperar a que todas las tareas terminen
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error en el sistema de trading: {e}")
            await self.stop()
        
        logger.info("Sistema de paper trading detenido")
    
    async def stop(self):
        """Detiene el sistema de trading"""
        logger.info("Deteniendo sistema de paper trading...")
        self.is_running = False
        
        # Cancelar tareas
        if self.websocket_task and not self.websocket_task.done():
            self.websocket_task.cancel()
        
        if self.trading_task and not self.trading_task.done():
            self.trading_task.cancel()
        
        # Cerrar cliente Binance
        if self.binance_client:
            await self.binance_client.close()
        
        # Guardar estado final
        if self.config.save_to_database:
            self._save_state_to_database()
    
    async def _websocket_handler(self):
        """Maneja conexión WebSocket para datos en tiempo real"""
        if not self.binance_client:
            return
        
        logger.info("Iniciando conexión WebSocket...")
        
        # Crear streams para todos los símbolos
        streams = []
        for symbol in self.config.symbols:
            streams.append(f"{symbol.lower()}@ticker")
            streams.append(f"{symbol.lower()}@kline_{self.config.primary_timeframe}")
        
        stream_url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
        
        try:
            async with websockets.connect(stream_url) as websocket:
                logger.info("Conexión WebSocket establecida")
                
                while self.is_running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        await self._process_websocket_data(data)
                        
                    except asyncio.TimeoutError:
                        # Ping para mantener conexión
                        await websocket.ping()
                    except Exception as e:
                        logger.error(f"Error procesando datos WebSocket: {e}")
                        break
        
        except Exception as e:
            logger.error(f"Error en conexión WebSocket: {e}")
            # Fallback a simulación
            await self._simulate_market_data()
    
    async def _simulate_market_data(self):
        """Simula datos de mercado para testing"""
        logger.info("Iniciando simulación de datos de mercado...")
        
        # Precios base
        base_prices = {
            "BNBUSDT": 300.0,
            "SOLUSDT": 100.0
        }
        
        while self.is_running:
            try:
                for symbol in self.config.symbols:
                    if symbol not in base_prices:
                        base_prices[symbol] = 50.0
                    
                    # Simular movimiento de precio
                    volatility = 0.021 if symbol == "BNBUSDT" else 0.038
                    change = np.random.normal(0, volatility / 100)
                    new_price = base_prices[symbol] * (1 + change)
                    
                    # Actualizar precio
                    base_prices[symbol] = new_price
                    self.current_prices[symbol] = new_price
                    self.last_update[symbol] = datetime.now()
                    
                    # Simular datos de kline
                    kline_data = {
                        'symbol': symbol,
                        'open': new_price * 0.999,
                        'high': new_price * 1.001,
                        'low': new_price * 0.998,
                        'close': new_price,
                        'volume': np.random.uniform(1000, 2000),
                        'timestamp': datetime.now()
                    }
                    
                    # Almacenar datos
                    self.market_data[symbol].append(kline_data)
                    
                    # Actualizar filtros de calidad
                    if self.quality_filter:
                        self.quality_filter.update_market_data(
                            symbol, new_price, kline_data['volume']
                        )
                
                await asyncio.sleep(1)  # Actualizar cada segundo
                
            except Exception as e:
                logger.error(f"Error en simulación de datos: {e}")
                await asyncio.sleep(5)
    
    async def _process_websocket_data(self, data: Dict[str, Any]):
        """Procesa datos recibidos por WebSocket"""
        try:
            if 'stream' in data:
                stream = data['stream']
                stream_data = data['data']
                
                if '@ticker' in stream:
                    # Datos de ticker
                    symbol = stream_data['s']
                    price = float(stream_data['c'])
                    
                    self.current_prices[symbol] = price
                    self.last_update[symbol] = datetime.now()
                
                elif '@kline' in stream:
                    # Datos de kline
                    kline = stream_data['k']
                    symbol = kline['s']
                    
                    if kline['x']:  # Kline cerrada
                        kline_data = {
                            'symbol': symbol,
                            'open': float(kline['o']),
                            'high': float(kline['h']),
                            'low': float(kline['l']),
                            'close': float(kline['c']),
                            'volume': float(kline['v']),
                            'timestamp': datetime.fromtimestamp(kline['T'] / 1000)
                        }
                        
                        self.market_data[symbol].append(kline_data)
                        
                        # Actualizar filtros de calidad
                        if self.quality_filter:
                            self.quality_filter.update_market_data(
                                symbol, kline_data['close'], kline_data['volume']
                            )
        
        except Exception as e:
            logger.error(f"Error procesando datos WebSocket: {e}")
    
    async def _trading_loop(self):
        """Loop principal de trading"""
        logger.info("Iniciando loop de trading...")
        
        while self.is_running:
            try:
                if self.is_trading_enabled:
                    # Actualizar posiciones
                    self._update_positions()
                    
                    # Verificar gestión de riesgo
                    if self.config.enable_risk_management:
                        await self._check_risk_management()
                    
                    # Generar y procesar señales
                    signals = await self._generate_signals()
                    await self._process_signals(signals)
                    
                    # Actualizar métricas
                    self._update_performance_metrics()
                
                await asyncio.sleep(self.config.update_frequency)
                
            except Exception as e:
                logger.error(f"Error en loop de trading: {e}")
                await asyncio.sleep(10)
    
    async def _generate_signals(self) -> Dict[str, SpotSignal]:
        """Genera señales de trading"""
        signals = {}
        
        for symbol in self.config.symbols:
            try:
                # Verificar si tenemos datos suficientes
                if (symbol not in self.market_data or 
                    len(self.market_data[symbol]) < 50):
                    continue
                
                # Verificar tiempo desde última señal
                if symbol in self.last_signal_time:
                    time_since_last = datetime.now() - self.last_signal_time[symbol]
                    if time_since_last < timedelta(minutes=5):  # Mínimo 5 minutos entre señales
                        continue
                
                # Evaluar calidad si está habilitado
                if self.quality_filter:
                    assessment = self.quality_filter.assess_quality(
                        symbol, [s for s in self.config.symbols if s != symbol]
                    )
                    if assessment.overall_score < self.config.min_quality_score:
                        continue
                
                # Convertir datos a DataFrame
                data_list = list(self.market_data[symbol])
                df = pd.DataFrame(data_list)
                df.set_index('timestamp', inplace=True)
                
                # Generar señal
                signal = self.strategy.generate_signal(symbol, df)
                
                if signal and signal.strength > 0.5:
                    signals[symbol] = signal
                    self.last_signal_time[symbol] = datetime.now()
                    
                    # Crear alerta de señal
                    await self._create_alert(
                        AlertType.SIGNAL,
                        symbol,
                        f"Señal {signal.action}: fuerza {signal.strength:.2f}, confianza {signal.confidence:.2f}",
                        "medium",
                        {'signal': signal.__dict__}
                    )
            
            except Exception as e:
                logger.error(f"Error generando señal para {symbol}: {e}")
        
        return signals
    
    async def _process_signals(self, signals: Dict[str, SpotSignal]):
        """Procesa señales de trading"""
        for symbol, signal in signals.items():
            try:
                current_position = self.positions.get(symbol)
                
                if signal.action == "buy" and (not current_position or current_position.quantity <= 0):
                    await self._place_buy_order(symbol, signal)
                elif signal.action == "sell" and current_position and current_position.quantity > 0:
                    await self._place_sell_order(symbol, signal)
                
                # Notificar callbacks
                for callback in self.signal_callbacks:
                    try:
                        await callback(symbol, signal)
                    except Exception as e:
                        logger.error(f"Error en callback de señal: {e}")
            
            except Exception as e:
                logger.error(f"Error procesando señal para {symbol}: {e}")
    
    async def _place_buy_order(self, symbol: str, signal: SpotSignal):
        """Coloca orden de compra"""
        try:
            current_price = self.current_prices.get(symbol)
            if not current_price:
                return
            
            # Calcular tamaño de posición
            available_capital = self._get_available_capital()
            max_position_value = self.current_capital * self.config.max_position_size
            position_value = min(available_capital * signal.confidence, max_position_value)
            
            if position_value < self.config.min_order_size:
                return
            
            quantity = position_value / current_price
            
            # Aplicar gestión de riesgo
            if self.config.enable_risk_management:
                risk_metrics = self.risk_manager.calculate_position_size(
                    symbol, current_price, self.current_capital, signal.strength
                )
                quantity = min(quantity, risk_metrics.max_position_size)
            
            # Crear orden
            order = PaperOrder(
                id=f"buy_{symbol}_{datetime.now().timestamp()}",
                symbol=symbol,
                side="buy",
                order_type="market",
                quantity=quantity,
                price=current_price,
                timestamp=datetime.now(),
                signal_strength=signal.strength,
                strategy_name="AdvancedSpotStrategy"
            )
            
            # Ejecutar orden
            await self._execute_order(order)
            
        except Exception as e:
            logger.error(f"Error colocando orden de compra para {symbol}: {e}")
    
    async def _place_sell_order(self, symbol: str, signal: SpotSignal):
        """Coloca orden de venta"""
        try:
            position = self.positions.get(symbol)
            if not position or position.quantity <= 0:
                return
            
            current_price = self.current_prices.get(symbol)
            if not current_price:
                return
            
            # Calcular cantidad a vender
            sell_quantity = position.quantity * signal.confidence
            
            # Crear orden
            order = PaperOrder(
                id=f"sell_{symbol}_{datetime.now().timestamp()}",
                symbol=symbol,
                side="sell",
                order_type="market",
                quantity=sell_quantity,
                price=current_price,
                timestamp=datetime.now(),
                signal_strength=signal.strength,
                strategy_name="AdvancedSpotStrategy"
            )
            
            # Ejecutar orden
            await self._execute_order(order)
            
        except Exception as e:
            logger.error(f"Error colocando orden de venta para {symbol}: {e}")
    
    async def _execute_order(self, order: PaperOrder):
        """Ejecuta una orden de paper trading"""
        try:
            # Simular slippage
            slippage = np.random.normal(0, 0.0005)  # 0.05% promedio
            if order.side == "buy":
                fill_price = order.price * (1 + abs(slippage))
            else:
                fill_price = order.price * (1 - abs(slippage))
            
            # Actualizar orden
            order.status = OrderStatus.FILLED
            order.filled_price = fill_price
            order.filled_quantity = order.quantity
            order.filled_timestamp = datetime.now()
            
            # Añadir a lista de órdenes
            self.orders.append(order)
            
            # Actualizar posición
            self._update_position_from_order(order)
            
            # Actualizar capital
            commission = order.quantity * fill_price * 0.001  # 0.1% comisión
            if order.side == "buy":
                self.current_capital -= (order.quantity * fill_price + commission)
            else:
                self.current_capital += (order.quantity * fill_price - commission)
            
            # Crear alerta
            await self._create_alert(
                AlertType.INFO,
                order.symbol,
                f"Orden {order.side} ejecutada: {order.quantity:.6f} @ ${fill_price:.4f}",
                "low",
                {'order': order.to_dict()}
            )
            
            # Guardar en base de datos
            if self.config.save_to_database:
                self._save_order_to_database(order)
            
            logger.info(f"Orden ejecutada: {order.side} {order.quantity:.6f} {order.symbol} @ ${fill_price:.4f}")
            
        except Exception as e:
            logger.error(f"Error ejecutando orden: {e}")
            order.status = OrderStatus.REJECTED
    
    def _update_position_from_order(self, order: PaperOrder):
        """Actualiza posición basada en orden ejecutada"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            if order.side == "buy":
                # Nueva posición
                self.positions[symbol] = PaperPosition(
                    symbol=symbol,
                    quantity=order.filled_quantity,
                    avg_price=order.filled_price,
                    current_price=order.filled_price,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    entry_timestamp=order.filled_timestamp,
                    last_update=order.filled_timestamp
                )
        else:
            position = self.positions[symbol]
            
            if order.side == "buy":
                # Aumentar posición
                total_cost = (position.quantity * position.avg_price + 
                             order.filled_quantity * order.filled_price)
                total_quantity = position.quantity + order.filled_quantity
                position.avg_price = total_cost / total_quantity
                position.quantity = total_quantity
            else:
                # Reducir posición
                if order.filled_quantity >= position.quantity:
                    # Cerrar posición completamente
                    pnl = (order.filled_price - position.avg_price) * position.quantity
                    position.realized_pnl += pnl
                    self.total_pnl += pnl
                    del self.positions[symbol]
                else:
                    # Reducir posición parcialmente
                    pnl = (order.filled_price - position.avg_price) * order.filled_quantity
                    position.realized_pnl += pnl
                    position.quantity -= order.filled_quantity
                    self.total_pnl += pnl
            
            if symbol in self.positions:
                self.positions[symbol].last_update = order.filled_timestamp
    
    def _update_positions(self):
        """Actualiza todas las posiciones con precios actuales"""
        for symbol, position in self.positions.items():
            if symbol in self.current_prices:
                current_price = self.current_prices[symbol]
                position.current_price = current_price
                
                # Calcular P&L no realizado
                unrealized_pnl = (current_price - position.avg_price) * position.quantity
                position.unrealized_pnl = unrealized_pnl
                position.last_update = datetime.now()
    
    def _get_available_capital(self) -> float:
        """Calcula capital disponible"""
        used_capital = sum(
            abs(pos.quantity * pos.current_price) 
            for pos in self.positions.values()
        )
        
        max_exposure = self.current_capital * self.config.max_total_exposure
        available = max_exposure - used_capital
        
        return max(0, min(available, self.current_capital * 0.5))
    
    async def _check_risk_management(self):
        """Verifica reglas de gestión de riesgo"""
        try:
            total_value = self._calculate_total_portfolio_value()
            
            # Actualizar peak capital
            if total_value > self.peak_capital:
                self.peak_capital = total_value
            
            # Calcular drawdown actual
            current_drawdown = (self.peak_capital - total_value) / self.peak_capital
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
            
            # Verificar límites de riesgo
            risk_alerts = []
            
            # Drawdown máximo
            if current_drawdown > self.config.max_drawdown:
                risk_alerts.append(f"Drawdown máximo excedido: {current_drawdown:.2%}")
                self.is_trading_enabled = False
            
            # Pérdida diaria
            daily_loss = (self.config.initial_capital - total_value) / self.config.initial_capital
            if daily_loss > self.config.max_daily_loss:
                risk_alerts.append(f"Pérdida diaria máxima excedida: {daily_loss:.2%}")
                self.is_trading_enabled = False
            
            # Crear alertas de riesgo
            for alert_msg in risk_alerts:
                await self._create_alert(
                    AlertType.RISK,
                    "PORTFOLIO",
                    alert_msg,
                    "critical",
                    {
                        'total_value': total_value,
                        'drawdown': current_drawdown,
                        'daily_loss': daily_loss
                    }
                )
            
            if risk_alerts:
                logger.warning(f"Alertas de riesgo: {'; '.join(risk_alerts)}")
        
        except Exception as e:
            logger.error(f"Error en verificación de riesgo: {e}")
    
    def _calculate_total_portfolio_value(self) -> float:
        """Calcula valor total del portafolio"""
        total_value = self.current_capital
        
        for symbol, position in self.positions.items():
            if symbol in self.current_prices:
                position_value = position.quantity * self.current_prices[symbol]
                total_value += position_value
        
        return total_value
    
    def _update_performance_metrics(self):
        """Actualiza métricas de rendimiento"""
        try:
            total_value = self._calculate_total_portfolio_value()
            
            # P&L total
            total_pnl = total_value - self.config.initial_capital
            total_pnl_pct = (total_pnl / self.config.initial_capital) * 100
            
            # P&L no realizado
            unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            
            # Actualizar métricas
            self.performance_metrics.update({
                'timestamp': datetime.now().isoformat(),
                'total_value': total_value,
                'total_pnl': total_pnl,
                'total_pnl_pct': total_pnl_pct,
                'realized_pnl': self.total_pnl,
                'unrealized_pnl': unrealized_pnl,
                'num_positions': len(self.positions),
                'num_orders': len(self.orders),
                'max_drawdown': self.max_drawdown,
                'is_trading_enabled': self.is_trading_enabled
            })
            
            # Verificar objetivo mensual (simplificado)
            days_running = 1  # Simplificado para demo
            if days_running >= 30:
                monthly_return = ((total_value / self.config.initial_capital) ** (30/days_running) - 1) * 100
                self.performance_metrics['monthly_return_projection'] = monthly_return
                self.performance_metrics['target_achieved'] = monthly_return >= 20.0
        
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")
    
    async def _create_alert(self, alert_type: AlertType, symbol: str, message: str, 
                           severity: str = "info", data: Dict[str, Any] = None):
        """Crea una alerta"""
        try:
            alert = TradingAlert(
                id=f"alert_{datetime.now().timestamp()}",
                alert_type=alert_type,
                symbol=symbol,
                message=message,
                timestamp=datetime.now(),
                severity=severity,
                data=data or {}
            )
            
            self.alerts.append(alert)
            
            # Mantener solo las últimas 1000 alertas
            if len(self.alerts) > 1000:
                self.alerts = self.alerts[-1000:]
            
            # Procesar alertas según canales configurados
            if "console" in self.config.alert_channels:
                severity_icon = {
                    "low": "ℹ",
                    "medium": "⚠",
                    "high": "🔥",
                    "critical": "🚨"
                }.get(severity, "ℹ")
                
                print(f"{severity_icon} [{alert_type.value.upper()}] {symbol}: {message}")
            
            # Guardar en base de datos
            if self.config.save_to_database:
                self._save_alert_to_database(alert)
            
            # Notificar callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    logger.error(f"Error en callback de alerta: {e}")
        
        except Exception as e:
            logger.error(f"Error creando alerta: {e}")
    
    async def _reporting_loop(self):
        """Loop de reportes periódicos"""
        logger.info("Iniciando loop de reportes...")
        
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Cada hora
                
                # Generar reporte
                report = self._generate_performance_report()
                
                # Crear alerta de rendimiento
                await self._create_alert(
                    AlertType.PERFORMANCE,
                    "PORTFOLIO",
                    f"Reporte horario: P&L {self.performance_metrics.get('total_pnl_pct', 0):.2f}%",
                    "info",
                    {'report': report}
                )
                
            except Exception as e:
                logger.error(f"Error en loop de reportes: {e}")
                await asyncio.sleep(300)  # Esperar 5 minutos antes de reintentar
    
    async def _optimization_loop(self):
        """Loop de optimización dinámica"""
        if not self.optimizer:
            return
        
        logger.info("Iniciando loop de optimización...")
        
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Cada hora
                
                # Ejecutar optimización
                if len(self.orders) >= 10:  # Mínimo 10 trades para optimizar
                    optimization_result = await self._run_optimization()
                    
                    if optimization_result:
                        await self._create_alert(
                            AlertType.INFO,
                            "OPTIMIZER",
                            f"Parámetros optimizados: mejora estimada {optimization_result.get('improvement', 0):.2f}%",
                            "medium",
                            {'optimization': optimization_result}
                        )
                
            except Exception as e:
                logger.error(f"Error en loop de optimización: {e}")
                await asyncio.sleep(1800)  # Esperar 30 minutos antes de reintentar
    
    async def _run_optimization(self) -> Optional[Dict[str, Any]]:
        """Ejecuta optimización de parámetros"""
        try:
            # Implementación simplificada
            # En la práctica, esto ejecutaría el DynamicOptimizer
            
            current_performance = self.performance_metrics.get('total_pnl_pct', 0)
            
            # Simular optimización
            improvement = np.random.uniform(-1, 2)  # -1% a +2% mejora
            
            return {
                'current_performance': current_performance,
                'improvement': improvement,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error en optimización: {e}")
            return None
    
    def _generate_performance_report(self) -> Dict[str, Any]:
        """Genera reporte de rendimiento"""
        total_value = self._calculate_total_portfolio_value()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'capital_inicial': self.config.initial_capital,
            'valor_actual': total_value,
            'pnl_total': total_value - self.config.initial_capital,
            'pnl_porcentaje': ((total_value / self.config.initial_capital) - 1) * 100,
            'posiciones_abiertas': len(self.positions),
            'ordenes_ejecutadas': len([o for o in self.orders if o.status == OrderStatus.FILLED]),
            'drawdown_maximo': self.max_drawdown * 100,
            'trading_habilitado': self.is_trading_enabled,
            'posiciones': {symbol: pos.to_dict() for symbol, pos in self.positions.items()}
        }
    
    def _save_order_to_database(self, order: PaperOrder):
        """Guarda orden en base de datos"""
        try:
            conn = sqlite3.connect(self.config.database_path)
            conn.execute("""
                INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.id, order.symbol, order.side, order.order_type,
                order.quantity, order.price, order.timestamp.isoformat(),
                order.status.value, order.filled_price, order.filled_quantity,
                order.filled_timestamp.isoformat() if order.filled_timestamp else None,
                order.signal_strength, order.strategy_name, order.notes
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error guardando orden en BD: {e}")
    
    def _save_alert_to_database(self, alert: TradingAlert):
        """Guarda alerta en base de datos"""
        try:
            conn = sqlite3.connect(self.config.database_path)
            conn.execute("""
                INSERT INTO alerts VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.id, alert.alert_type.value, alert.symbol,
                alert.message, alert.timestamp.isoformat(),
                alert.severity, json.dumps(alert.data)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error guardando alerta en BD: {e}")
    
    def _save_state_to_database(self):
        """Guarda estado actual en base de datos"""
        try:
            conn = sqlite3.connect(self.config.database_path)
            
            # Guardar posiciones
            for symbol, position in self.positions.items():
                conn.execute("""
                    INSERT OR REPLACE INTO positions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    position.symbol, position.quantity, position.avg_price,
                    position.current_price, position.unrealized_pnl, position.realized_pnl,
                    position.entry_timestamp.isoformat(), position.last_update.isoformat(),
                    position.stop_loss, position.take_profit
                ))
            
            # Guardar métricas
            conn.execute("""
                INSERT INTO metrics VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                self._calculate_total_portfolio_value(),
                self.total_pnl,
                self.daily_pnl,
                self.max_drawdown,
                len(self.positions),
                json.dumps(self.performance_metrics)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error guardando estado en BD: {e}")
    
    # Métodos públicos para interacción
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene estado actual del sistema"""
        return {
            'is_running': self.is_running,
            'is_trading_enabled': self.is_trading_enabled,
            'current_capital': self.current_capital,
            'total_value': self._calculate_total_portfolio_value(),
            'positions': {symbol: pos.to_dict() for symbol, pos in self.positions.items()},
            'recent_orders': [order.to_dict() for order in self.orders[-10:]],
            'recent_alerts': [alert.to_dict() for alert in self.alerts[-10:]],
            'performance_metrics': self.performance_metrics,
            'last_update': max(self.last_update.values()) if self.last_update else None
        }
    
    def enable_trading(self):
        """Habilita trading"""
        self.is_trading_enabled = True
        logger.info("Trading habilitado")
    
    def disable_trading(self):
        """Deshabilita trading"""
        self.is_trading_enabled = False
        logger.info("Trading deshabilitado")
    
    def add_signal_callback(self, callback: Callable):
        """Añade callback para señales"""
        self.signal_callbacks.append(callback)
    
    def add_alert_callback(self, callback: Callable):
        """Añade callback para alertas"""
        self.alert_callbacks.append(callback)
    
    def add_performance_callback(self, callback: Callable):
        """Añade callback para métricas de rendimiento"""
        self.performance_callbacks.append(callback)

if __name__ == "__main__":
    # Ejemplo de uso
    async def main():
        print("=== PAPER TRADING EN TIEMPO REAL ===")
        
        # Configuración
        config = TradingConfig(
            trading_mode=TradingMode.PAPER,
            initial_capital=500.0,
            symbols=["BNBUSDT", "SOLUSDT"],
            max_position_size=0.4,
            enable_quality_filters=True,
            enable_dynamic_optimization=True,
            update_frequency=30
        )
        
        # Crear trader
        trader = RealTimePaperTrader(config)
        
        # Callbacks de ejemplo
        async def on_signal(symbol: str, signal):
            print(f"📊 Señal recibida: {symbol} - {signal.action} (fuerza: {signal.strength:.2f})")
        
        async def on_alert(alert):
            if alert.severity in ['high', 'critical']:
                print(f"🚨 ALERTA {alert.severity.upper()}: {alert.message}")
        
        trader.add_signal_callback(on_signal)
        trader.add_alert_callback(on_alert)
        
        try:
            # Iniciar sistema
            print("Iniciando sistema de paper trading...")
            print("Presiona Ctrl+C para detener")
            
            # Ejecutar por tiempo limitado para demo
            await asyncio.wait_for(trader.start(), timeout=300)  # 5 minutos
            
        except asyncio.TimeoutError:
            print("\nDemo completada")
        except KeyboardInterrupt:
            print("\nDeteniendo sistema...")
        finally:
            await trader.stop()
            
            # Mostrar resumen final
            status = trader.get_status()
            print("\n=== RESUMEN FINAL ===")
            print(f"Capital inicial: ${config.initial_capital}")
            print(f"Valor final: ${status['total_value']:.2f}")
            print(f"P&L: ${status['total_value'] - config.initial_capital:.2f}")
            print(f"Órdenes ejecutadas: {len([o for o in trader.orders if o.status == OrderStatus.FILLED])}")
            print(f"Posiciones abiertas: {len(status['positions'])}")
            print(f"Alertas generadas: {len(trader.alerts)}")
    
    # Ejecutar
    asyncio.run(main())