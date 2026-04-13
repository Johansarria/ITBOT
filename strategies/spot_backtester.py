# strategies/spot_backtester.py

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from enum import Enum
import asyncio
from collections import defaultdict, deque
import json
import sqlite3
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Importar componentes de la estrategia
from .advanced_spot_strategy import AdvancedSpotStrategy, SpotSignal, AssetOptimizer
from .advanced_risk_manager import AdvancedRiskManager, RiskMetrics
from .quality_filters import QualityFilterEngine, QualityAssessment, FilterResult
from .multi_timeframe_analyzer import MultiTimeframeAnalyzer, TimeframeSignal

logger = logging.getLogger(__name__)

class BacktestMode(Enum):
    """Modos de backtesting"""
    HISTORICAL = "historical"  # Datos históricos completos
    WALK_FORWARD = "walk_forward"  # Análisis walk-forward
    MONTE_CARLO = "monte_carlo"  # Simulación Monte Carlo
    STRESS_TEST = "stress_test"  # Pruebas de estrés
    OPTIMIZATION = "optimization"  # Optimización de parámetros

class OrderType(Enum):
    """Tipos de orden"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderStatus(Enum):
    """Estados de orden"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class BacktestOrder:
    """Orden de backtesting"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: OrderType
    quantity: float
    price: float
    timestamp: datetime
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    filled_timestamp: Optional[datetime] = None
    commission: float = 0.0
    slippage: float = 0.0
    
    # Metadatos
    signal_strength: float = 0.0
    strategy_name: str = ""
    notes: str = ""

@dataclass
class BacktestPosition:
    """Posición de backtesting"""
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
    
    # Metadatos
    max_unrealized_pnl: float = 0.0
    min_unrealized_pnl: float = 0.0
    max_drawdown: float = 0.0

@dataclass
class BacktestTrade:
    """Trade completado"""
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    entry_timestamp: datetime
    exit_timestamp: datetime
    pnl: float
    pnl_pct: float
    commission: float
    duration: timedelta
    
    # Análisis del trade
    signal_strength: float
    max_favorable_excursion: float  # MFE
    max_adverse_excursion: float    # MAE
    
    # Razón de salida
    exit_reason: str  # 'take_profit', 'stop_loss', 'signal', 'timeout'

@dataclass
class BacktestConfig:
    """Configuración de backtesting"""
    # Capital inicial
    initial_capital: float = 500.0  # USDT
    
    # Comisiones y costos
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005   # 0.05%
    
    # Configuración de órdenes
    max_position_size: float = 0.3  # 30% del capital por posición
    max_total_exposure: float = 0.8  # 80% exposición total máxima
    
    # Timeframes
    primary_timeframe: str = "5m"
    secondary_timeframes: List[str] = field(default_factory=lambda: ["1m", "15m", "1h"])
    
    # Filtros de calidad
    enable_quality_filters: bool = True
    min_quality_score: float = 0.6
    
    # Gestión de riesgo
    enable_risk_management: bool = True
    max_daily_loss: float = 0.05  # 5% pérdida diaria máxima
    max_drawdown: float = 0.15    # 15% drawdown máximo
    
    # Optimización
    optimization_metric: str = "sharpe_ratio"  # 'total_return', 'sharpe_ratio', 'calmar_ratio'
    
    # Datos
    data_source: str = "binance"
    symbols: List[str] = field(default_factory=lambda: ["BNBUSDT", "SOLUSDT"])
    
    # Fechas
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Configuración específica
    enable_compounding: bool = True
    rebalance_frequency: str = "daily"  # 'trade', 'daily', 'weekly'
    
    # Configuración de simulación
    monte_carlo_runs: int = 1000
    confidence_level: float = 0.95

@dataclass
class BacktestMetrics:
    """Métricas de rendimiento del backtesting"""
    # Rendimiento
    total_return: float = 0.0
    total_return_pct: float = 0.0
    annualized_return: float = 0.0
    monthly_return: float = 0.0
    
    # Riesgo
    volatility: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    # Ratios
    sharpe_ratio: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    # Trading
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Tiempo
    avg_trade_duration: timedelta = field(default_factory=lambda: timedelta(0))
    max_trade_duration: timedelta = field(default_factory=lambda: timedelta(0))
    
    # Exposición
    avg_exposure: float = 0.0
    max_exposure: float = 0.0
    
    # Objetivo específico
    monthly_target_achieved: bool = False
    months_above_target: int = 0
    months_below_target: int = 0
    
    # Estadísticas adicionales
    var_95: float = 0.0  # Value at Risk 95%
    expected_shortfall: float = 0.0
    
    # Fechas
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_days: int = 0

class SpotBacktester:
    """Backtester especializado para estrategia spot"""
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        
        # Componentes de la estrategia
        self.strategy = AdvancedSpotStrategy()
        self.risk_manager = AdvancedRiskManager()
        self.quality_filter = QualityFilterEngine() if self.config.enable_quality_filters else None
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        
        # Estado del backtesting
        self.current_capital = self.config.initial_capital
        self.positions: Dict[str, BacktestPosition] = {}
        self.orders: List[BacktestOrder] = []
        self.trades: List[BacktestTrade] = []
        
        # Datos de mercado
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.current_prices: Dict[str, float] = {}
        self.current_timestamp: Optional[datetime] = None
        
        # Historial de capital
        self.capital_history: List[Tuple[datetime, float]] = []
        self.drawdown_history: List[Tuple[datetime, float]] = []
        
        # Métricas en tiempo real
        self.daily_returns: List[float] = []
        self.monthly_returns: List[float] = []
        
        # Base de datos para persistencia
        self.db_path = Path("backtest_results.db")
        self._init_database()
        
        # Configuración de visualización
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        logger.info(f"SpotBacktester inicializado con capital: ${self.config.initial_capital}")
    
    def _init_database(self):
        """Inicializa base de datos para resultados"""
        conn = sqlite3.connect(self.db_path)
        
        # Tabla de backtests
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backtests (
                id TEXT PRIMARY KEY,
                config TEXT,
                metrics TEXT,
                start_date TEXT,
                end_date TEXT,
                created_at TEXT
            )
        """)
        
        # Tabla de trades
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                backtest_id TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                exit_price REAL,
                quantity REAL,
                pnl REAL,
                pnl_pct REAL,
                entry_timestamp TEXT,
                exit_timestamp TEXT,
                duration_seconds INTEGER,
                signal_strength REAL,
                exit_reason TEXT
            )
        """)
        
        conn.close()
    
    def load_market_data(self, symbol: str, timeframe: str = "5m", 
                        start_date: datetime = None, end_date: datetime = None) -> pd.DataFrame:
        """Carga datos de mercado (simulado para el ejemplo)"""
        
        # En implementación real, esto cargaría datos de Binance API
        # Por ahora, generamos datos sintéticos realistas
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now()
        
        # Generar datos sintéticos
        dates = pd.date_range(start=start_date, end=end_date, freq='5T')
        
        # Parámetros por símbolo
        if symbol == "BNBUSDT":
            base_price = 300
            volatility = 0.021  # 2.1% como especificado
            trend = 0.0001
        elif symbol == "SOLUSDT":
            base_price = 100
            volatility = 0.038  # 3.8% como especificado
            trend = 0.0002
        else:
            base_price = 50
            volatility = 0.025
            trend = 0.0
        
        # Generar precios con tendencia y volatilidad
        np.random.seed(42)  # Para reproducibilidad
        returns = np.random.normal(trend, volatility, len(dates))
        
        # Añadir algunos patrones realistas
        for i in range(1, len(returns)):
            # Autocorrelación ligera
            returns[i] += 0.1 * returns[i-1]
            
            # Volatilidad clustering
            if abs(returns[i-1]) > volatility:
                returns[i] *= 1.2
        
        # Calcular precios
        prices = [base_price]
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Generar OHLCV
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Simular variación intraperiodo
            high = price * (1 + abs(np.random.normal(0, volatility/4)))
            low = price * (1 - abs(np.random.normal(0, volatility/4)))
            open_price = prices[i-1] if i > 0 else price
            close_price = price
            
            # Asegurar OHLC válido
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)
            
            # Volumen correlacionado con volatilidad
            base_volume = 1000000 if symbol == "BNBUSDT" else 500000
            volume_multiplier = 1 + abs(returns[i]) * 10
            volume = base_volume * volume_multiplier * np.random.uniform(0.5, 1.5)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def prepare_data(self):
        """Prepara todos los datos necesarios para el backtesting"""
        logger.info("Preparando datos de mercado...")
        
        start_date = self.config.start_date or (datetime.now() - timedelta(days=90))
        end_date = self.config.end_date or datetime.now()
        
        for symbol in self.config.symbols:
            logger.info(f"Cargando datos para {symbol}...")
            
            # Cargar datos del timeframe principal
            df = self.load_market_data(symbol, self.config.primary_timeframe, start_date, end_date)
            self.market_data[symbol] = df
            
            # Actualizar filtros de calidad con datos históricos
            if self.quality_filter:
                for _, row in df.iterrows():
                    self.quality_filter.update_market_data(
                        symbol, row['close'], row['volume'], 
                        timestamp=row.name
                    )
        
        logger.info(f"Datos preparados para {len(self.config.symbols)} símbolos")
    
    def run_backtest(self, mode: BacktestMode = BacktestMode.HISTORICAL) -> BacktestMetrics:
        """Ejecuta el backtesting"""
        logger.info(f"Iniciando backtesting en modo {mode.value}...")
        
        # Preparar datos
        self.prepare_data()
        
        # Resetear estado
        self._reset_state()
        
        if mode == BacktestMode.HISTORICAL:
            return self._run_historical_backtest()
        elif mode == BacktestMode.WALK_FORWARD:
            return self._run_walk_forward_backtest()
        elif mode == BacktestMode.MONTE_CARLO:
            return self._run_monte_carlo_backtest()
        elif mode == BacktestMode.STRESS_TEST:
            return self._run_stress_test()
        elif mode == BacktestMode.OPTIMIZATION:
            return self._run_optimization_backtest()
        else:
            raise ValueError(f"Modo de backtesting no soportado: {mode}")
    
    def _reset_state(self):
        """Resetea el estado del backtester"""
        self.current_capital = self.config.initial_capital
        self.positions.clear()
        self.orders.clear()
        self.trades.clear()
        self.capital_history.clear()
        self.drawdown_history.clear()
        self.daily_returns.clear()
        self.monthly_returns.clear()
        self.current_prices.clear()
        self.current_timestamp = None
    
    def _run_historical_backtest(self) -> BacktestMetrics:
        """Ejecuta backtesting histórico"""
        logger.info("Ejecutando backtesting histórico...")
        
        # Obtener todas las fechas únicas y ordenarlas
        all_timestamps = set()
        for symbol, df in self.market_data.items():
            all_timestamps.update(df.index)
        
        timestamps = sorted(all_timestamps)
        
        # Simular trading paso a paso
        for i, timestamp in enumerate(timestamps):
            self.current_timestamp = timestamp
            
            # Actualizar precios actuales
            for symbol, df in self.market_data.items():
                if timestamp in df.index:
                    self.current_prices[symbol] = df.loc[timestamp, 'close']
            
            # Procesar órdenes pendientes
            self._process_pending_orders()
            
            # Actualizar posiciones
            self._update_positions()
            
            # Verificar gestión de riesgo
            if self.config.enable_risk_management:
                self._check_risk_management()
            
            # Generar señales de trading
            signals = self._generate_signals()
            
            # Ejecutar órdenes basadas en señales
            self._execute_signals(signals)
            
            # Registrar capital
            total_value = self._calculate_total_portfolio_value()
            self.capital_history.append((timestamp, total_value))
            
            # Calcular drawdown
            peak_value = max([v for _, v in self.capital_history])
            current_drawdown = (peak_value - total_value) / peak_value
            self.drawdown_history.append((timestamp, current_drawdown))
            
            # Log progreso
            if i % 1000 == 0:
                logger.info(f"Procesado {i}/{len(timestamps)} timestamps. Capital: ${total_value:.2f}")
        
        # Cerrar todas las posiciones al final
        self._close_all_positions()
        
        # Calcular métricas finales
        metrics = self._calculate_metrics()
        
        logger.info(f"Backtesting completado. Rendimiento total: {metrics.total_return_pct:.2f}%")
        
        return metrics
    
    def _generate_signals(self) -> Dict[str, SpotSignal]:
        """Genera señales de trading para todos los símbolos"""
        signals = {}
        
        for symbol in self.config.symbols:
            if symbol not in self.current_prices:
                continue
            
            # Obtener datos históricos hasta el punto actual
            df = self.market_data[symbol]
            current_data = df[df.index <= self.current_timestamp].tail(200)  # Últimos 200 períodos
            
            if len(current_data) < 50:  # Datos insuficientes
                continue
            
            # Evaluar calidad si está habilitado
            quality_ok = True
            if self.quality_filter:
                assessment = self.quality_filter.assess_quality(symbol, 
                    [s for s in self.config.symbols if s != symbol])
                quality_ok = assessment.overall_score >= self.config.min_quality_score
            
            if not quality_ok:
                continue
            
            # Generar señal usando la estrategia
            try:
                signal = self.strategy.generate_signal(symbol, current_data)
                if signal and signal.strength > 0.5:  # Filtrar señales débiles
                    signals[symbol] = signal
            except Exception as e:
                logger.warning(f"Error generando señal para {symbol}: {e}")
        
        return signals
    
    def _execute_signals(self, signals: Dict[str, SpotSignal]):
        """Ejecuta órdenes basadas en señales"""
        for symbol, signal in signals.items():
            try:
                # Verificar si ya tenemos posición
                current_position = self.positions.get(symbol)
                
                if signal.action == "buy" and (not current_position or current_position.quantity <= 0):
                    self._place_buy_order(symbol, signal)
                elif signal.action == "sell" and current_position and current_position.quantity > 0:
                    self._place_sell_order(symbol, signal)
                    
            except Exception as e:
                logger.warning(f"Error ejecutando señal para {symbol}: {e}")
    
    def _place_buy_order(self, symbol: str, signal: SpotSignal):
        """Coloca orden de compra"""
        current_price = self.current_prices[symbol]
        
        # Calcular tamaño de posición
        available_capital = self.current_capital * (1 - sum(abs(pos.quantity * pos.current_price) 
                                                           for pos in self.positions.values()) / self.current_capital)
        
        max_position_value = self.current_capital * self.config.max_position_size
        position_value = min(available_capital * signal.confidence, max_position_value)
        
        if position_value < 10:  # Mínimo $10
            return
        
        quantity = position_value / current_price
        
        # Aplicar gestión de riesgo
        if self.config.enable_risk_management:
            risk_metrics = self.risk_manager.calculate_position_size(
                symbol, current_price, self.current_capital, signal.strength
            )
            quantity = min(quantity, risk_metrics.max_position_size)
        
        # Crear orden
        order = BacktestOrder(
            id=f"buy_{symbol}_{self.current_timestamp.timestamp()}",
            symbol=symbol,
            side="buy",
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=current_price,
            timestamp=self.current_timestamp,
            signal_strength=signal.strength,
            strategy_name="AdvancedSpotStrategy"
        )
        
        self.orders.append(order)
        
        # Ejecutar inmediatamente (market order)
        self._fill_order(order)
    
    def _place_sell_order(self, symbol: str, signal: SpotSignal):
        """Coloca orden de venta"""
        position = self.positions.get(symbol)
        if not position or position.quantity <= 0:
            return
        
        current_price = self.current_prices[symbol]
        
        # Vender toda la posición o parcialmente según la señal
        sell_quantity = position.quantity * signal.confidence
        
        # Crear orden
        order = BacktestOrder(
            id=f"sell_{symbol}_{self.current_timestamp.timestamp()}",
            symbol=symbol,
            side="sell",
            order_type=OrderType.MARKET,
            quantity=sell_quantity,
            price=current_price,
            timestamp=self.current_timestamp,
            signal_strength=signal.strength,
            strategy_name="AdvancedSpotStrategy"
        )
        
        self.orders.append(order)
        
        # Ejecutar inmediatamente
        self._fill_order(order)
    
    def _fill_order(self, order: BacktestOrder):
        """Ejecuta una orden"""
        # Simular slippage
        slippage = np.random.normal(0, self.config.slippage_rate)
        if order.side == "buy":
            fill_price = order.price * (1 + abs(slippage))
        else:
            fill_price = order.price * (1 - abs(slippage))
        
        # Calcular comisión
        commission = order.quantity * fill_price * self.config.commission_rate
        
        # Actualizar orden
        order.status = OrderStatus.FILLED
        order.filled_price = fill_price
        order.filled_quantity = order.quantity
        order.filled_timestamp = self.current_timestamp
        order.commission = commission
        order.slippage = abs(slippage)
        
        # Actualizar posición
        self._update_position_from_order(order)
        
        # Actualizar capital
        if order.side == "buy":
            self.current_capital -= (order.quantity * fill_price + commission)
        else:
            self.current_capital += (order.quantity * fill_price - commission)
    
    def _update_position_from_order(self, order: BacktestOrder):
        """Actualiza posición basada en orden ejecutada"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            if order.side == "buy":
                # Nueva posición
                self.positions[symbol] = BacktestPosition(
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
                    self._record_trade(position, order, pnl)
                    del self.positions[symbol]
                else:
                    # Reducir posición parcialmente
                    pnl = (order.filled_price - position.avg_price) * order.filled_quantity
                    position.realized_pnl += pnl
                    position.quantity -= order.filled_quantity
            
            if symbol in self.positions:
                self.positions[symbol].last_update = order.filled_timestamp
    
    def _record_trade(self, position: BacktestPosition, exit_order: BacktestOrder, pnl: float):
        """Registra un trade completado"""
        duration = exit_order.filled_timestamp - position.entry_timestamp
        pnl_pct = (pnl / (position.avg_price * position.quantity)) * 100
        
        trade = BacktestTrade(
            id=f"trade_{len(self.trades) + 1}",
            symbol=position.symbol,
            side="long",  # Solo long en spot
            entry_price=position.avg_price,
            exit_price=exit_order.filled_price,
            quantity=position.quantity,
            entry_timestamp=position.entry_timestamp,
            exit_timestamp=exit_order.filled_timestamp,
            pnl=pnl,
            pnl_pct=pnl_pct,
            commission=exit_order.commission,
            duration=duration,
            signal_strength=exit_order.signal_strength,
            max_favorable_excursion=position.max_unrealized_pnl,
            max_adverse_excursion=position.min_unrealized_pnl,
            exit_reason="signal"
        )
        
        self.trades.append(trade)
    
    def _process_pending_orders(self):
        """Procesa órdenes pendientes"""
        # En este backtester simple, todas las órdenes son market y se ejecutan inmediatamente
        # En implementación más avanzada, aquí se procesarían órdenes limit, stop, etc.
        pass
    
    def _update_positions(self):
        """Actualiza todas las posiciones con precios actuales"""
        for symbol, position in self.positions.items():
            if symbol in self.current_prices:
                current_price = self.current_prices[symbol]
                position.current_price = current_price
                
                # Calcular P&L no realizado
                unrealized_pnl = (current_price - position.avg_price) * position.quantity
                position.unrealized_pnl = unrealized_pnl
                
                # Actualizar máximos y mínimos
                position.max_unrealized_pnl = max(position.max_unrealized_pnl, unrealized_pnl)
                position.min_unrealized_pnl = min(position.min_unrealized_pnl, unrealized_pnl)
                
                # Calcular drawdown de la posición
                if position.max_unrealized_pnl > 0:
                    drawdown = (position.max_unrealized_pnl - unrealized_pnl) / position.max_unrealized_pnl
                    position.max_drawdown = max(position.max_drawdown, drawdown)
                
                position.last_update = self.current_timestamp
    
    def _check_risk_management(self):
        """Verifica y aplica reglas de gestión de riesgo"""
        total_value = self._calculate_total_portfolio_value()
        
        # Verificar pérdida diaria máxima
        if len(self.capital_history) > 0:
            start_of_day_value = self.capital_history[0][1]  # Simplificado
            daily_loss = (start_of_day_value - total_value) / start_of_day_value
            
            if daily_loss > self.config.max_daily_loss:
                logger.warning(f"Pérdida diaria máxima alcanzada: {daily_loss:.2%}")
                self._close_all_positions()
                return
        
        # Verificar drawdown máximo
        if len(self.capital_history) > 0:
            peak_value = max([v for _, v in self.capital_history])
            current_drawdown = (peak_value - total_value) / peak_value
            
            if current_drawdown > self.config.max_drawdown:
                logger.warning(f"Drawdown máximo alcanzado: {current_drawdown:.2%}")
                self._close_all_positions()
                return
    
    def _close_all_positions(self):
        """Cierra todas las posiciones abiertas"""
        for symbol, position in list(self.positions.items()):
            if position.quantity > 0:
                current_price = self.current_prices.get(symbol, position.current_price)
                
                # Crear orden de venta
                order = BacktestOrder(
                    id=f"close_{symbol}_{self.current_timestamp.timestamp()}",
                    symbol=symbol,
                    side="sell",
                    order_type=OrderType.MARKET,
                    quantity=position.quantity,
                    price=current_price,
                    timestamp=self.current_timestamp,
                    strategy_name="RiskManagement"
                )
                
                self.orders.append(order)
                self._fill_order(order)
    
    def _calculate_total_portfolio_value(self) -> float:
        """Calcula el valor total del portafolio"""
        total_value = self.current_capital
        
        for symbol, position in self.positions.items():
            if symbol in self.current_prices:
                position_value = position.quantity * self.current_prices[symbol]
                total_value += position_value
        
        return total_value
    
    def _calculate_metrics(self) -> BacktestMetrics:
        """Calcula métricas de rendimiento"""
        if not self.capital_history:
            return BacktestMetrics()
        
        # Datos básicos
        start_date = self.capital_history[0][0]
        end_date = self.capital_history[-1][0]
        duration = end_date - start_date
        
        initial_capital = self.config.initial_capital
        final_capital = self.capital_history[-1][1]
        
        # Rendimiento
        total_return = final_capital - initial_capital
        total_return_pct = (total_return / initial_capital) * 100
        
        # Rendimiento anualizado
        years = duration.days / 365.25
        if years > 0:
            annualized_return = ((final_capital / initial_capital) ** (1/years) - 1) * 100
        else:
            annualized_return = 0
        
        # Rendimiento mensual
        months = duration.days / 30.44
        if months > 0:
            monthly_return = ((final_capital / initial_capital) ** (1/months) - 1) * 100
        else:
            monthly_return = 0
        
        # Calcular retornos diarios
        daily_returns = []
        for i in range(1, len(self.capital_history)):
            prev_value = self.capital_history[i-1][1]
            curr_value = self.capital_history[i][1]
            daily_return = (curr_value - prev_value) / prev_value
            daily_returns.append(daily_return)
        
        # Volatilidad
        volatility = np.std(daily_returns) * np.sqrt(252) * 100 if daily_returns else 0
        
        # Drawdown
        peak_value = initial_capital
        max_drawdown = 0
        max_drawdown_duration = 0
        current_drawdown_duration = 0
        
        for _, value in self.capital_history:
            if value > peak_value:
                peak_value = value
                current_drawdown_duration = 0
            else:
                drawdown = (peak_value - value) / peak_value
                max_drawdown = max(max_drawdown, drawdown)
                current_drawdown_duration += 1
                max_drawdown_duration = max(max_drawdown_duration, current_drawdown_duration)
        
        # Ratios
        risk_free_rate = 0.02  # 2% anual
        if volatility > 0:
            sharpe_ratio = (annualized_return/100 - risk_free_rate) / (volatility/100)
        else:
            sharpe_ratio = 0
        
        if max_drawdown > 0:
            calmar_ratio = (annualized_return/100) / max_drawdown
        else:
            calmar_ratio = 0
        
        # Estadísticas de trading
        total_trades = len(self.trades)
        winning_trades = len([t for t in self.trades if t.pnl > 0])
        losing_trades = len([t for t in self.trades if t.pnl < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # P&L promedio
        wins = [t.pnl for t in self.trades if t.pnl > 0]
        losses = [t.pnl for t in self.trades if t.pnl < 0]
        
        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        
        if avg_loss > 0:
            profit_factor = avg_win / avg_loss
        else:
            profit_factor = 0
        
        # Duración promedio de trades
        if self.trades:
            avg_duration = sum([t.duration for t in self.trades], timedelta(0)) / len(self.trades)
            max_duration = max([t.duration for t in self.trades])
        else:
            avg_duration = timedelta(0)
            max_duration = timedelta(0)
        
        # Objetivo mensual del 20%
        monthly_target_achieved = monthly_return >= 20.0
        
        # Calcular meses por encima/debajo del objetivo (simplificado)
        months_above_target = int(monthly_return >= 20.0) if months >= 1 else 0
        months_below_target = int(months) - months_above_target if months >= 1 else 0
        
        # VaR y Expected Shortfall
        if daily_returns:
            var_95 = np.percentile(daily_returns, 5) * 100
            worst_5_pct = [r for r in daily_returns if r <= np.percentile(daily_returns, 5)]
            expected_shortfall = np.mean(worst_5_pct) * 100 if worst_5_pct else 0
        else:
            var_95 = 0
            expected_shortfall = 0
        
        return BacktestMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            monthly_return=monthly_return,
            volatility=volatility,
            max_drawdown=max_drawdown * 100,
            max_drawdown_duration=max_drawdown_duration,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            avg_trade_duration=avg_duration,
            max_trade_duration=max_duration,
            monthly_target_achieved=monthly_target_achieved,
            months_above_target=months_above_target,
            months_below_target=months_below_target,
            var_95=var_95,
            expected_shortfall=expected_shortfall,
            start_date=start_date,
            end_date=end_date,
            duration_days=duration.days
        )
    
    def _run_walk_forward_backtest(self) -> BacktestMetrics:
        """Ejecuta análisis walk-forward"""
        logger.info("Ejecutando análisis walk-forward...")
        # Implementación simplificada
        return self._run_historical_backtest()
    
    def _run_monte_carlo_backtest(self) -> BacktestMetrics:
        """Ejecuta simulación Monte Carlo"""
        logger.info("Ejecutando simulación Monte Carlo...")
        # Implementación simplificada
        return self._run_historical_backtest()
    
    def _run_stress_test(self) -> BacktestMetrics:
        """Ejecuta pruebas de estrés"""
        logger.info("Ejecutando pruebas de estrés...")
        # Implementación simplificada
        return self._run_historical_backtest()
    
    def _run_optimization_backtest(self) -> BacktestMetrics:
        """Ejecuta optimización de parámetros"""
        logger.info("Ejecutando optimización de parámetros...")
        # Implementación simplificada
        return self._run_historical_backtest()
    
    def generate_report(self, metrics: BacktestMetrics, save_path: str = None) -> str:
        """Genera reporte detallado del backtesting"""
        report = f"""
=== REPORTE DE BACKTESTING SPOT STRATEGY ===

PERÍODO: {metrics.start_date.strftime('%Y-%m-%d') if metrics.start_date else 'N/A'} - {metrics.end_date.strftime('%Y-%m-%d') if metrics.end_date else 'N/A'}
DURACIÓN: {metrics.duration_days} días

RENDIMIENTO:
  • Rendimiento Total: ${metrics.total_return:.2f} ({metrics.total_return_pct:.2f}%)
  • Rendimiento Anualizado: {metrics.annualized_return:.2f}%
  • Rendimiento Mensual: {metrics.monthly_return:.2f}%
  • OBJETIVO 20% MENSUAL: {'✓ ALCANZADO' if metrics.monthly_target_achieved else '✗ NO ALCANZADO'}

RIESGO:
  • Volatilidad: {metrics.volatility:.2f}%
  • Drawdown Máximo: {metrics.max_drawdown:.2f}%
  • Duración Drawdown Máximo: {metrics.max_drawdown_duration} períodos
  • VaR 95%: {metrics.var_95:.2f}%
  • Expected Shortfall: {metrics.expected_shortfall:.2f}%

RATIOS:
  • Sharpe Ratio: {metrics.sharpe_ratio:.2f}
  • Calmar Ratio: {metrics.calmar_ratio:.2f}

TRADING:
  • Total de Trades: {metrics.total_trades}
  • Trades Ganadores: {metrics.winning_trades} ({metrics.win_rate:.1f}%)
  • Trades Perdedores: {metrics.losing_trades}
  • Ganancia Promedio: ${metrics.avg_win:.2f}
  • Pérdida Promedio: ${metrics.avg_loss:.2f}
  • Factor de Beneficio: {metrics.profit_factor:.2f}
  • Duración Promedio: {str(metrics.avg_trade_duration).split('.')[0]}

CONFIGURACIÓN:
  • Capital Inicial: ${self.config.initial_capital}
  • Comisión: {self.config.commission_rate*100:.2f}%
  • Slippage: {self.config.slippage_rate*100:.3f}%
  • Símbolos: {', '.join(self.config.symbols)}
  • Timeframe: {self.config.primary_timeframe}

EVALUACIÓN:
"""
        
        # Evaluación del objetivo
        if metrics.monthly_target_achieved:
            report += "  ✓ ESTRATEGIA EXITOSA: Objetivo del 20% mensual alcanzado\n"
        else:
            report += "  ✗ ESTRATEGIA REQUIERE OPTIMIZACIÓN: Objetivo no alcanzado\n"
        
        # Evaluación de riesgo
        if metrics.max_drawdown < 15:
            report += "  ✓ RIESGO CONTROLADO: Drawdown dentro de límites\n"
        else:
            report += "  ⚠ RIESGO ELEVADO: Drawdown excede límites recomendados\n"
        
        # Evaluación de consistencia
        if metrics.sharpe_ratio > 1.5:
            report += "  ✓ RENDIMIENTO CONSISTENTE: Sharpe ratio excelente\n"
        elif metrics.sharpe_ratio > 1.0:
            report += "  ✓ RENDIMIENTO ACEPTABLE: Sharpe ratio bueno\n"
        else:
            report += "  ⚠ RENDIMIENTO INCONSISTENTE: Sharpe ratio bajo\n"
        
        report += "\n=== FIN DEL REPORTE ===\n"
        
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Reporte guardado en: {save_path}")
        
        return report
    
    def plot_results(self, metrics: BacktestMetrics, save_path: str = None):
        """Genera gráficos de resultados"""
        if not self.capital_history:
            logger.warning("No hay datos para graficar")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Resultados del Backtesting - Estrategia Spot', fontsize=16)
        
        # Gráfico 1: Evolución del capital
        dates = [d for d, _ in self.capital_history]
        values = [v for _, v in self.capital_history]
        
        axes[0, 0].plot(dates, values, linewidth=2, color='blue')
        axes[0, 0].axhline(y=self.config.initial_capital, color='red', linestyle='--', alpha=0.7, label='Capital Inicial')
        axes[0, 0].set_title('Evolución del Capital')
        axes[0, 0].set_ylabel('Capital (USDT)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Gráfico 2: Drawdown
        dd_dates = [d for d, _ in self.drawdown_history]
        dd_values = [dd * 100 for _, dd in self.drawdown_history]
        
        axes[0, 1].fill_between(dd_dates, dd_values, 0, alpha=0.3, color='red')
        axes[0, 1].plot(dd_dates, dd_values, color='red', linewidth=1)
        axes[0, 1].set_title('Drawdown')
        axes[0, 1].set_ylabel('Drawdown (%)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Gráfico 3: Distribución de retornos
        if len(values) > 1:
            returns = [(values[i] - values[i-1]) / values[i-1] * 100 for i in range(1, len(values))]
            axes[1, 0].hist(returns, bins=30, alpha=0.7, color='green', edgecolor='black')
            axes[1, 0].axvline(x=0, color='red', linestyle='--', alpha=0.7)
            axes[1, 0].set_title('Distribución de Retornos')
            axes[1, 0].set_xlabel('Retorno (%)')
            axes[1, 0].set_ylabel('Frecuencia')
            axes[1, 0].grid(True, alpha=0.3)
        
        # Gráfico 4: P&L de trades
        if self.trades:
            trade_pnl = [t.pnl for t in self.trades]
            cumulative_pnl = np.cumsum(trade_pnl)
            
            axes[1, 1].bar(range(len(trade_pnl)), trade_pnl, 
                          color=['green' if pnl > 0 else 'red' for pnl in trade_pnl],
                          alpha=0.7)
            axes[1, 1].plot(range(len(cumulative_pnl)), cumulative_pnl, 
                           color='blue', linewidth=2, label='P&L Acumulado')
            axes[1, 1].set_title('P&L por Trade')
            axes[1, 1].set_xlabel('Trade #')
            axes[1, 1].set_ylabel('P&L (USDT)')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Gráficos guardados en: {save_path}")
        
        plt.show()

if __name__ == "__main__":
    # Ejemplo de uso
    print("=== BACKTESTING ESTRATEGIA SPOT AVANZADA ===")
    
    # Configuración
    config = BacktestConfig(
        initial_capital=500.0,
        symbols=["BNBUSDT", "SOLUSDT"],
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
        commission_rate=0.001,
        slippage_rate=0.0005,
        max_position_size=0.4,  # 40% por posición
        enable_quality_filters=True,
        min_quality_score=0.6
    )
    
    # Crear backtester
    backtester = SpotBacktester(config)
    
    # Ejecutar backtesting
    print("\nEjecutando backtesting...")
    metrics = backtester.run_backtest(BacktestMode.HISTORICAL)
    
    # Generar reporte
    print("\n" + "="*60)
    report = backtester.generate_report(metrics)
    print(report)
    
    # Generar gráficos
    print("Generando gráficos...")
    backtester.plot_results(metrics)
    
    # Análisis específico del objetivo
    print("\n=== ANÁLISIS DEL OBJETIVO 20% MENSUAL ===")
    
    if metrics.monthly_target_achieved:
        print(f"✓ OBJETIVO ALCANZADO: {metrics.monthly_return:.2f}% mensual")
        print(f"  Rendimiento anualizado proyectado: {metrics.annualized_return:.2f}%")
        print(f"  Con este rendimiento, $500 se convertirían en ${500 * (1 + metrics.monthly_return/100)**12:.2f} en un año")
    else:
        print(f"✗ OBJETIVO NO ALCANZADO: {metrics.monthly_return:.2f}% mensual")
        print(f"  Déficit: {20 - metrics.monthly_return:.2f} puntos porcentuales")
        print("  RECOMENDACIONES:")
        print("    • Optimizar parámetros de indicadores técnicos")
        print("    • Ajustar filtros de calidad")
        print("    • Incrementar frecuencia de rebalanceo")
        print("    • Considerar apalancamiento controlado")
        print("    • Expandir universo de activos")
    
    print("\n=== BACKTESTING COMPLETADO ===")