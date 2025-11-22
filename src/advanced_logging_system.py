#!/usr/bin/env python3
"""
Sistema de Logging Avanzado Multi-Símbolo - SICAR
Captura métricas granulares para optimización continua
Análisis profundo de comportamiento del sistema
Símbolos monitoreados: BTCUSDT, ETHUSDT, ADAUSDT, DOTUSDT, LINKUSDT
"""

import json
import logging
import os
import sqlite3
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import pandas as pd
import numpy as np
from pathlib import Path
import psutil
import hashlib

# Importar el analizador de orderbook
try:
    from orderbook_analyzer import OrderBookAnalyzer, integrate_with_market_conditions
    ORDERBOOK_ANALYZER_AVAILABLE = True
except ImportError:
    ORDERBOOK_ANALYZER_AVAILABLE = False
    logger.warning("OrderBook Analyzer no disponible - funcionando sin análisis de depth")

# Configuración de logging base
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LogLevel(Enum):
    """Niveles de logging específicos"""
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    PERFORMANCE = "performance"
    DECISION = "decision"
    MARKET = "market"
    EXECUTION = "execution"

class EventType(Enum):
    """Tipos de eventos del sistema"""
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    ANALYSIS_START = "analysis_start"
    ANALYSIS_END = "analysis_end"
    ANALYSIS_COMPLETE = "analysis_complete"
    SIGNAL_GENERATED = "signal_generated"
    NO_SIGNAL = "no_signal"
    MARKET_DATA_RECEIVED = "market_data_received"
    INDICATOR_CALCULATED = "indicator_calculated"
    CONDITION_EVALUATED = "condition_evaluated"
    EXECUTION_ATTEMPT = "execution_attempt"
    EXECUTION_SUCCESS = "execution_success"
    EXECUTION_FAILURE = "execution_failure"
    TRADE_EXECUTED = "trade_executed"
    FIRST_CANDLE_DETECTED = "first_candle_detected"
    SESSION_SUMMARY = "session_summary"
    ERROR_OCCURRED = "error_occurred"
    ERROR = "error"
    PERFORMANCE_METRIC = "performance_metric"
    HEALTH_CHECK = "health_check"

@dataclass
class MarketConditions:
    """Condiciones de mercado en el momento del análisis"""
    timestamp: datetime
    symbol: str
    price: float
    volume: float
    volatility: float
    trend_direction: str
    market_session: str
    spread: float
    order_book_depth: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'price': self.price,
            'volume': self.volume,
            'volatility': self.volatility,
            'trend_direction': self.trend_direction,
            'market_session': self.market_session,
            'spread': self.spread,
            'order_book_depth': self.order_book_depth
        }

@dataclass
class TechnicalIndicators:
    """Indicadores técnicos calculados"""
    timestamp: datetime
    symbol: str
    ema_20: float
    ema_50: float
    rsi: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    atr: float
    volume_ratio: float
    momentum: float
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'ema_20': self.ema_20,
            'ema_50': self.ema_50,
            'rsi': self.rsi,
            'macd_line': self.macd_line,
            'macd_signal': self.macd_signal,
            'macd_histogram': self.macd_histogram,
            'bb_upper': self.bb_upper,
            'bb_middle': self.bb_middle,
            'bb_lower': self.bb_lower,
            'atr': self.atr,
            'volume_ratio': self.volume_ratio,
            'momentum': self.momentum
        }

@dataclass
class DecisionContext:
    """Contexto de decisión para generación de señales"""
    timestamp: datetime
    symbol: str
    decision_id: str
    conditions_met: List[str]
    conditions_failed: List[str]
    confidence_score: float
    risk_assessment: Dict[str, float]
    signal_strength: float
    market_conditions: MarketConditions
    technical_indicators: TechnicalIndicators
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'decision_id': self.decision_id,
            'conditions_met': self.conditions_met,
            'conditions_failed': self.conditions_failed,
            'confidence_score': self.confidence_score,
            'risk_assessment': self.risk_assessment,
            'signal_strength': self.signal_strength,
            'market_conditions': self.market_conditions.to_dict(),
            'technical_indicators': self.technical_indicators.to_dict()
        }

@dataclass
class PerformanceMetrics:
    """Métricas de rendimiento del sistema"""
    timestamp: datetime
    analysis_duration_ms: float
    data_fetch_duration_ms: float
    indicator_calculation_duration_ms: float
    signal_generation_duration_ms: float
    memory_usage_mb: float
    cpu_usage_percent: float
    api_response_time_ms: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'analysis_duration_ms': self.analysis_duration_ms,
            'data_fetch_duration_ms': self.data_fetch_duration_ms,
            'indicator_calculation_duration_ms': self.indicator_calculation_duration_ms,
            'signal_generation_duration_ms': self.signal_generation_duration_ms,
            'memory_usage_mb': self.memory_usage_mb,
            'cpu_usage_percent': self.cpu_usage_percent,
            'api_response_time_ms': self.api_response_time_ms,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests
        }

@dataclass
class ExecutionEvent:
    """Evento de ejecución de trade"""
    timestamp: datetime
    symbol: str
    trade_type: str  # BUY, SELL
    order_type: str  # MARKET, LIMIT
    quantity: float
    price: float
    execution_time_ms: float
    fees: float
    slippage: float
    order_id: str
    status: str  # FILLED, PARTIAL, REJECTED
    remaining_capital: float
    position_size_after: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    profit_loss: Optional[float] = None
    
    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'trade_type': self.trade_type,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'price': self.price,
            'execution_time_ms': self.execution_time_ms,
            'fees': self.fees,
            'slippage': self.slippage,
            'order_id': self.order_id,
            'status': self.status,
            'remaining_capital': self.remaining_capital,
            'position_size_after': self.position_size_after,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'profit_loss': self.profit_loss
        }

@dataclass
class LogEntry:
    """Entrada de log estructurada"""
    timestamp: datetime
    level: LogLevel
    event_type: EventType
    message: str
    session_id: str
    component: str
    data: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Optional[PerformanceMetrics] = None
    decision_context: Optional[DecisionContext] = None
    
    def to_dict(self):
        result = {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'event_type': self.event_type.value,
            'message': self.message,
            'session_id': self.session_id,
            'component': self.component,
            'data': self.data
        }
        
        if self.performance_metrics:
            result['performance_metrics'] = self.performance_metrics.to_dict()
        
        if self.decision_context:
            result['decision_context'] = self.decision_context.to_dict()
        
        return result

class AdvancedLoggingSystem:
    """Sistema de Logging Avanzado Multi-Símbolo"""
    
    def __init__(self, config_file: str = "advanced_logging_config.json", symbols: List[str] = None):
        """Inicializa el sistema de logging avanzado multi-símbolo"""
        self.config = self._load_config(config_file)
        self.session_id = self._generate_session_id()
        self.running = False
        
        # Símbolos monitoreados (por defecto los del sistema First Candle)
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        
        # Base de datos para persistencia
        self.db_path = "advanced_logging.db"
        self._init_database()
        
        # Buffers para optimización (organizados por símbolo)
        self.log_buffer: List[LogEntry] = []
        self.performance_buffer = {symbol: [] for symbol in self.symbols}
        self.decision_buffer = {symbol: [] for symbol in self.symbols}
        self.market_buffer = {symbol: [] for symbol in self.symbols}
        self.execution_buffer = {symbol: [] for symbol in self.symbols}
        self.buffer_lock = threading.Lock()
        self.buffer_size = self.config.get('buffer_size', 100)
        
        # Métricas en tiempo real por símbolo
        self.current_metrics = {
            'total_logs': 0,
            'logs_by_level': {},
            'logs_by_type': {},
            'session_start': datetime.now(timezone.utc),
            'last_flush': datetime.now(timezone.utc)
        }
        
        # Contadores por símbolo
        self.symbol_counters = {
            symbol: {
                'trades': 0,
                'signals': 0,
                'errors': 0,
                'analyses': 0,
                'market_updates': 0
            } for symbol in self.symbols
        }
        
        # Archivos de log especializados
        self.log_files = {
            'main': 'advanced_system.log',
            'performance': 'performance_metrics.log',
            'decisions': 'decision_analysis.log',
            'market': 'market_conditions.log',
            'errors': 'system_errors.log'
        }
        
        # Configurar loggers especializados
        self._setup_specialized_loggers()
        
        # Hilo de procesamiento asíncrono
        self.processing_thread = None
        
        # Inicializar OrderBook Analyzer si está disponible
        self.orderbook_analyzer = None
        if ORDERBOOK_ANALYZER_AVAILABLE:
            try:
                self.orderbook_analyzer = OrderBookAnalyzer()
                logger.info("🔍 OrderBook Analyzer integrado exitosamente")
            except Exception as e:
                logger.warning(f"Error inicializando OrderBook Analyzer: {e}")
                self.orderbook_analyzer = None
        
        logger.info(f"📊 AdvancedLoggingSystem Multi-Símbolo inicializado - Sesión: {self.session_id}")
        logger.info(f"🎯 Símbolos monitoreados: {', '.join(self.symbols)}")
    
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Carga configuración del sistema de logging"""
        default_config = {
            'buffer_size': 100,
            'flush_interval_seconds': 30,
            'max_log_file_size_mb': 100,
            'max_log_files': 10,
            'enable_performance_logging': True,
            'enable_decision_logging': True,
            'enable_market_logging': True,
            'log_levels': ['info', 'warning', 'error', 'critical', 'performance', 'decision'],
            'retention_days': 30,
            'compression_enabled': True,
            'real_time_analysis': True,
            'export_formats': ['json', 'csv', 'parquet'],
            'analysis_intervals': {
                'performance_summary': 3600,  # 1 hora
                'decision_analysis': 1800,    # 30 minutos
                'market_analysis': 900        # 15 minutos
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Error cargando config de logging: {e}")
        
        return default_config
    
    def _generate_session_id(self) -> str:
        """Genera ID único de sesión"""
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        hash_part = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        return f"SICAR_{timestamp}_{hash_part}"
    
    def _init_database(self):
        """Inicializa base de datos de logs"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Tabla principal de logs
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS log_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        level TEXT,
                        event_type TEXT,
                        message TEXT,
                        session_id TEXT,
                        component TEXT,
                        data TEXT,
                        performance_metrics TEXT,
                        decision_context TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Tabla de métricas de rendimiento (con soporte multi-símbolo)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        session_id TEXT,
                        symbol TEXT,
                        analysis_duration_ms REAL,
                        data_fetch_duration_ms REAL,
                        indicator_calculation_duration_ms REAL,
                        signal_generation_duration_ms REAL,
                        memory_usage_mb REAL,
                        cpu_usage_percent REAL,
                        api_response_time_ms REAL,
                        total_requests INTEGER,
                        successful_requests INTEGER,
                        failed_requests INTEGER
                    )
                """)
                
                # Tabla de contexto de decisiones
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS decision_contexts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        session_id TEXT,
                        symbol TEXT,
                        decision_id TEXT,
                        conditions_met TEXT,
                        conditions_failed TEXT,
                        confidence_score REAL,
                        risk_assessment TEXT,
                        signal_strength REAL,
                        market_conditions TEXT,
                        technical_indicators TEXT
                    )
                """)
                
                # Tabla de condiciones de mercado
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS market_conditions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        session_id TEXT,
                        symbol TEXT,
                        price REAL,
                        volume REAL,
                        volatility REAL,
                        trend_direction TEXT,
                        market_session TEXT,
                        spread REAL,
                        order_book_depth TEXT
                    )
                """)
                
                # Nueva tabla para ejecuciones de trading por símbolo
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trade_executions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        session_id TEXT,
                        symbol TEXT NOT NULL,
                        action TEXT NOT NULL,
                        success BOOLEAN NOT NULL,
                        order_id TEXT,
                        error_message TEXT,
                        execution_time_ms REAL
                    )
                """)
                
                # Nueva tabla para estadísticas por símbolo
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS symbol_statistics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        session_id TEXT,
                        symbol TEXT NOT NULL,
                        total_analyses INTEGER DEFAULT 0,
                        total_signals INTEGER DEFAULT 0,
                        total_trades INTEGER DEFAULT 0,
                        total_errors INTEGER DEFAULT 0,
                        success_rate REAL DEFAULT 0,
                        avg_confidence REAL DEFAULT 0,
                        last_update TEXT NOT NULL
                    )
                """)
                
                # Índices para optimización
                conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON log_entries(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON log_entries(session_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_level ON log_entries(level)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON log_entries(event_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_performance_symbol ON performance_metrics(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_decision_symbol ON decision_contexts(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_market_symbol ON market_conditions(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trade_executions(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_stats_symbol ON symbol_statistics(symbol)")
                
        except Exception as e:
            logger.error(f"Error inicializando DB de logging: {e}")
    
    def _setup_specialized_loggers(self):
        """Configura loggers especializados"""
        self.loggers = {}
        
        for log_type, filename in self.log_files.items():
            specialized_logger = logging.getLogger(f"sicar_{log_type}")
            specialized_logger.setLevel(logging.DEBUG)
            
            # Handler para archivo
            file_handler = logging.FileHandler(filename, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # Formato específico para cada tipo
            if log_type == 'performance':
                formatter = logging.Formatter(
                    '%(asctime)s - PERF - %(message)s'
                )
            elif log_type == 'decisions':
                formatter = logging.Formatter(
                    '%(asctime)s - DECISION - %(message)s'
                )
            elif log_type == 'market':
                formatter = logging.Formatter(
                    '%(asctime)s - MARKET - %(message)s'
                )
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s'
                )
            
            file_handler.setFormatter(formatter)
            specialized_logger.addHandler(file_handler)
            
            self.loggers[log_type] = specialized_logger
    
    def start_logging(self):
        """Inicia el sistema de logging"""
        if self.running:
            logger.warning("Sistema de logging ya está ejecutándose")
            return
        
        self.running = True
        
        # Iniciar hilo de procesamiento
        self.processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True
        )
        self.processing_thread.start()
        
        self.log(
            LogLevel.INFO,
            EventType.SYSTEM_START,
            "Sistema de logging avanzado iniciado",
            "AdvancedLoggingSystem"
        )
        
        logger.info("🚀 Sistema de logging avanzado iniciado")
    
    def stop_logging(self):
        """Detiene el sistema de logging"""
        self.running = False
        
        # Procesar buffer restante
        self._flush_buffer()
        
        self.log(
            LogLevel.INFO,
            EventType.SYSTEM_STOP,
            "Sistema de logging avanzado detenido",
            "AdvancedLoggingSystem"
        )
        
        logger.info("⏹️ Sistema de logging avanzado detenido")
    
    def log(self, level: LogLevel, event_type: EventType, message: str, 
            component: str, data: Dict[str, Any] = None,
            performance_metrics: PerformanceMetrics = None,
            decision_context: DecisionContext = None):
        """Registra entrada de log"""
        
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            event_type=event_type,
            message=message,
            session_id=self.session_id,
            component=component,
            data=data or {},
            performance_metrics=performance_metrics,
            decision_context=decision_context
        )
        
        # Agregar al buffer
        with self.buffer_lock:
            self.log_buffer.append(entry)
            
            # Actualizar métricas
            self.current_metrics['total_logs'] += 1
            
            level_key = level.value
            if level_key not in self.current_metrics['logs_by_level']:
                self.current_metrics['logs_by_level'][level_key] = 0
            self.current_metrics['logs_by_level'][level_key] += 1
            
            type_key = event_type.value
            if type_key not in self.current_metrics['logs_by_type']:
                self.current_metrics['logs_by_type'][type_key] = 0
            self.current_metrics['logs_by_type'][type_key] += 1
            
            # Flush si el buffer está lleno
            if len(self.log_buffer) >= self.buffer_size:
                self._flush_buffer()
        
        # Log a archivo especializado
        self._log_to_specialized_file(entry)
    
    def log_performance(self, metrics: PerformanceMetrics, component: str = "System", symbol: str = None):
        """Registra métricas de rendimiento"""
        # Si se especifica símbolo, agregar a buffer específico
        if symbol and symbol in self.performance_buffer:
            with self.buffer_lock:
                self.performance_buffer[symbol].append(metrics)
        
        message = f"Métricas de rendimiento: {metrics.analysis_duration_ms:.2f}ms análisis"
        if symbol:
            message = f"Métricas de rendimiento - {symbol}: {metrics.analysis_duration_ms:.2f}ms análisis"
        
        self.log(
            LogLevel.PERFORMANCE,
            EventType.PERFORMANCE_METRIC,
            message,
            component,
            performance_metrics=metrics
        )
    
    def log_decision(self, context: DecisionContext, component: str = "DecisionEngine"):
        """Registra contexto de decisión"""
        signal_type = "SEÑAL GENERADA" if context.conditions_met else "SIN SEÑAL"
        
        # Actualizar contador del símbolo
        if context.symbol in self.symbol_counters:
            self.symbol_counters[context.symbol]['analyses'] += 1
            if context.conditions_met:
                self.symbol_counters[context.symbol]['signals'] += 1
        
        # Agregar a buffer específico del símbolo
        if context.symbol in self.decision_buffer:
            with self.buffer_lock:
                self.decision_buffer[context.symbol].append(context)
        
        self.log(
            LogLevel.DECISION,
            EventType.SIGNAL_GENERATED if context.conditions_met else EventType.NO_SIGNAL,
            f"{signal_type} - {context.symbol} - Confianza: {context.confidence_score:.2f}",
            component,
            decision_context=context
        )
    
    def process_orderbook_data(self, symbol: str, depth_data: Dict) -> Dict:
        """
        Procesa datos de orderbook usando el analizador integrado
        
        Args:
            symbol: Símbolo del par de trading
            depth_data: Datos de depth de Binance API
            
        Returns:
            Dict con métricas de orderbook procesadas
        """
        if not self.orderbook_analyzer or not depth_data:
            return {}
        
        try:
            # Analizar datos de depth
            metrics = self.orderbook_analyzer.analyze_depth_data(symbol, depth_data)
            
            if metrics:
                # Log de métricas de orderbook
                self.log(
                    LogLevel.INFO,
                    EventType.MARKET_DATA_RECEIVED,
                    f"OrderBook analizado - {symbol}: Spread={metrics.spread_percentage:.3f}%, Liquidez={metrics.liquidity_score:.1f}",
                    "OrderBookAnalyzer",
                    data=metrics.to_dict()
                )
                
                # Retornar métricas para integración
                return {
                    'bid_price': metrics.bid_price,
                    'ask_price': metrics.ask_price,
                    'spread_pct': metrics.spread_percentage,
                    'liquidity_score': metrics.liquidity_score,
                    'volume_imbalance': metrics.volume_imbalance,
                    'depth_quality': metrics.depth_quality,
                    'market_impact': (metrics.market_impact_buy + metrics.market_impact_sell) / 2,
                    'weighted_mid_price': metrics.weighted_mid_price
                }
            
        except Exception as e:
            logger.error(f"Error procesando orderbook para {symbol}: {e}")
        
        return {}

    def log_market_conditions(self, conditions: MarketConditions, component: str = "MarketData", depth_data: Dict = None):
        """Registra condiciones de mercado con análisis de orderbook integrado"""
        # Procesar datos de orderbook si están disponibles
        if depth_data and self.orderbook_analyzer:
            orderbook_metrics = self.process_orderbook_data(conditions.symbol, depth_data)
            if orderbook_metrics:
                # Actualizar order_book_depth con métricas procesadas
                conditions.order_book_depth = orderbook_metrics
        
        # Actualizar contador del símbolo
        if conditions.symbol in self.symbol_counters:
            self.symbol_counters[conditions.symbol]['market_updates'] += 1
        
        # Agregar a buffer específico del símbolo
        if conditions.symbol in self.market_buffer:
            with self.buffer_lock:
                self.market_buffer[conditions.symbol].append(conditions)
        
        # Mensaje mejorado con información de orderbook
        orderbook_info = ""
        if conditions.order_book_depth:
            spread = conditions.order_book_depth.get('spread_pct', 0)
            liquidity = conditions.order_book_depth.get('liquidity_score', 0)
            orderbook_info = f" | Spread: {spread:.3f}% | Liquidez: {liquidity:.1f}"
        
        self.log(
            LogLevel.MARKET,
            EventType.MARKET_DATA_RECEIVED,
            f"Condiciones de mercado - {conditions.symbol}: ${conditions.price:.4f}{orderbook_info}",
            component,
            data=conditions.to_dict()
        )
    
    def log_technical_indicators(self, indicators: TechnicalIndicators, component: str = "TechnicalAnalysis"):
        """Registra indicadores técnicos"""
        self.log(
            LogLevel.DEBUG,
            EventType.INDICATOR_CALCULATED,
            f"Indicadores calculados - {indicators.symbol}: RSI={indicators.rsi:.2f}",
            component,
            data=indicators.to_dict()
        )
    
    def log_execution_attempt(self, symbol: str, action: str, quantity: float, 
                            price: float, component: str = "ExecutionEngine"):
        """Registra intento de ejecución"""
        self.log(
            LogLevel.INFO,
            EventType.EXECUTION_ATTEMPT,
            f"Intento de ejecución: {action} {quantity} {symbol} @ ${price:.4f}",
            component,
            data={
                'symbol': symbol,
                'action': action,
                'quantity': quantity,
                'price': price
            }
        )
    
    def log_execution_result(self, symbol: str, action: str, success: bool, 
                           order_id: str = None, error: str = None,
                           component: str = "ExecutionEngine"):
        """Registra resultado de ejecución"""
        event_type = EventType.EXECUTION_SUCCESS if success else EventType.EXECUTION_FAILURE
        level = LogLevel.INFO if success else LogLevel.ERROR
        
        # Actualizar contadores del símbolo
        if symbol in self.symbol_counters:
            if success:
                self.symbol_counters[symbol]['trades'] += 1
            else:
                self.symbol_counters[symbol]['errors'] += 1
        
        # Agregar a buffer de ejecución del símbolo
        execution_data = {
            'timestamp': datetime.now(timezone.utc),
            'symbol': symbol,
            'action': action,
            'success': success,
            'order_id': order_id,
            'error': error
        }
        
        if symbol in self.execution_buffer:
            with self.buffer_lock:
                self.execution_buffer[symbol].append(execution_data)
        
        message = f"Ejecución {'exitosa' if success else 'fallida'}: {action} {symbol}"
        if order_id:
            message += f" - Order ID: {order_id}"
        
        data = {
            'symbol': symbol,
            'action': action,
            'success': success,
            'order_id': order_id,
            'error': error
        }
        
        self.log(level, event_type, message, component, data)
    
    def log_execution_event(self, execution_event: ExecutionEvent, component: str = "ExecutionEngine"):
        """Registra evento de ejecución de trade"""
        # Actualizar contadores del símbolo
        if execution_event.symbol in self.symbol_counters:
            self.symbol_counters[execution_event.symbol]['trades'] += 1
            if execution_event.profit_loss:
                if execution_event.profit_loss > 0:
                    self.symbol_counters[execution_event.symbol]['successful_trades'] += 1
        
        # Agregar a buffer de ejecución del símbolo
        if execution_event.symbol in self.execution_buffer:
            with self.buffer_lock:
                self.execution_buffer[execution_event.symbol].append(execution_event.to_dict())
        
        # Guardar en base de datos
        try:
            with self.db_lock:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    INSERT INTO trade_executions (
                        timestamp, symbol, trade_type, order_type, quantity, price,
                        execution_time_ms, fees, slippage, order_id, status,
                        remaining_capital, position_size_after, stop_loss, take_profit, profit_loss
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution_event.timestamp.isoformat(),
                    execution_event.symbol,
                    execution_event.trade_type,
                    execution_event.order_type,
                    execution_event.quantity,
                    execution_event.price,
                    execution_event.execution_time_ms,
                    execution_event.fees,
                    execution_event.slippage,
                    execution_event.order_id,
                    execution_event.status,
                    execution_event.remaining_capital,
                    execution_event.position_size_after,
                    execution_event.stop_loss,
                    execution_event.take_profit,
                    execution_event.profit_loss
                ))
                self.db_connection.commit()
        except Exception as e:
            logging.error(f"Error guardando evento de ejecución en BD: {str(e)}")
        
        # Log del evento
        message = f"Trade ejecutado: {execution_event.trade_type} {execution_event.quantity:.4f} {execution_event.symbol} @ ${execution_event.price:.4f}"
        if execution_event.profit_loss:
            message += f" - P&L: ${execution_event.profit_loss:.2f}"
        
        self.log(
            LogLevel.EXECUTION,
            EventType.TRADE_EXECUTED,
            message,
            component,
            symbol=execution_event.symbol,
            data=execution_event.to_dict()
        )
    
    def log_error(self, error: Exception, component: str, context: Dict[str, Any] = None):
        """Registra error del sistema"""
        self.log(
            LogLevel.ERROR,
            EventType.ERROR_OCCURRED,
            f"Error en {component}: {str(error)}",
            component,
            data={
                'error_type': type(error).__name__,
                'error_message': str(error),
                'context': context or {}
            }
        )
    
    def _log_to_specialized_file(self, entry: LogEntry):
        """Registra en archivo especializado"""
        try:
            # Determinar logger especializado
            if entry.level == LogLevel.PERFORMANCE:
                logger_name = 'performance'
            elif entry.level == LogLevel.DECISION:
                logger_name = 'decisions'
            elif entry.level == LogLevel.MARKET:
                logger_name = 'market'
            elif entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                logger_name = 'errors'
            else:
                logger_name = 'main'
            
            specialized_logger = self.loggers.get(logger_name)
            if specialized_logger:
                # Formatear mensaje con datos adicionales
                log_message = entry.message
                
                if entry.data:
                    log_message += f" | Data: {json.dumps(entry.data, ensure_ascii=False)}"
                
                if entry.performance_metrics:
                    log_message += f" | Performance: {json.dumps(entry.performance_metrics.to_dict(), ensure_ascii=False)}"
                
                if entry.decision_context:
                    log_message += f" | Decision: {json.dumps(entry.decision_context.to_dict(), ensure_ascii=False)}"
                
                # Log según nivel
                if entry.level == LogLevel.ERROR:
                    specialized_logger.error(log_message)
                elif entry.level == LogLevel.CRITICAL:
                    specialized_logger.critical(log_message)
                elif entry.level == LogLevel.WARNING:
                    specialized_logger.warning(log_message)
                else:
                    specialized_logger.info(log_message)
                    
        except Exception as e:
            logger.error(f"Error escribiendo a archivo especializado: {e}")
    
    def _processing_loop(self):
        """Loop de procesamiento asíncrono"""
        logger.info("🔄 Loop de procesamiento de logs iniciado")
        
        while self.running:
            try:
                # Flush periódico del buffer
                time.sleep(self.config['flush_interval_seconds'])
                
                if self.log_buffer:
                    self._flush_buffer()
                
                # Análisis periódico
                self._periodic_analysis()
                
            except Exception as e:
                logger.error(f"Error en loop de procesamiento: {e}")
                time.sleep(60)
        
        logger.info("🔄 Loop de procesamiento de logs finalizado")
    
    def _flush_buffer(self):
        """Flush del buffer a base de datos"""
        if not self.log_buffer:
            return
        
        try:
            with self.buffer_lock:
                entries_to_process = self.log_buffer.copy()
                self.log_buffer.clear()
            
            # Procesar entradas
            with sqlite3.connect(self.db_path) as conn:
                for entry in entries_to_process:
                    # Insertar en tabla principal
                    conn.execute("""
                        INSERT INTO log_entries 
                        (timestamp, level, event_type, message, session_id, component, data, performance_metrics, decision_context)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.timestamp.isoformat(),
                        entry.level.value,
                        entry.event_type.value,
                        entry.message,
                        entry.session_id,
                        entry.component,
                        json.dumps(entry.data),
                        json.dumps(entry.performance_metrics.to_dict()) if entry.performance_metrics else None,
                        json.dumps(entry.decision_context.to_dict()) if entry.decision_context else None
                    ))
                    
                    # Insertar métricas de rendimiento
                    if entry.performance_metrics:
                        metrics = entry.performance_metrics
                        conn.execute("""
                            INSERT INTO performance_metrics 
                            (timestamp, session_id, analysis_duration_ms, data_fetch_duration_ms, 
                             indicator_calculation_duration_ms, signal_generation_duration_ms,
                             memory_usage_mb, cpu_usage_percent, api_response_time_ms,
                             total_requests, successful_requests, failed_requests)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            metrics.timestamp.isoformat(),
                            entry.session_id,
                            metrics.analysis_duration_ms,
                            metrics.data_fetch_duration_ms,
                            metrics.indicator_calculation_duration_ms,
                            metrics.signal_generation_duration_ms,
                            metrics.memory_usage_mb,
                            metrics.cpu_usage_percent,
                            metrics.api_response_time_ms,
                            metrics.total_requests,
                            metrics.successful_requests,
                            metrics.failed_requests
                        ))
                    
                    # Insertar contexto de decisión
                    if entry.decision_context:
                        context = entry.decision_context
                        conn.execute("""
                            INSERT INTO decision_contexts 
                            (timestamp, session_id, symbol, decision_id, conditions_met, conditions_failed,
                             confidence_score, risk_assessment, signal_strength, market_conditions, technical_indicators)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            context.timestamp.isoformat(),
                            entry.session_id,
                            context.symbol,
                            context.decision_id,
                            json.dumps(context.conditions_met),
                            json.dumps(context.conditions_failed),
                            context.confidence_score,
                            json.dumps(context.risk_assessment),
                            context.signal_strength,
                            json.dumps(context.market_conditions.to_dict()),
                            json.dumps(context.technical_indicators.to_dict())
                        ))
                        
                        # Insertar condiciones de mercado
                        market = context.market_conditions
                        conn.execute("""
                            INSERT INTO market_conditions 
                            (timestamp, session_id, symbol, price, volume, volatility,
                             trend_direction, market_session, spread, order_book_depth)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            market.timestamp.isoformat(),
                            entry.session_id,
                            market.symbol,
                            market.price,
                            market.volume,
                            market.volatility,
                            market.trend_direction,
                            market.market_session,
                            market.spread,
                            json.dumps(market.order_book_depth)
                        ))
            
            self.current_metrics['last_flush'] = datetime.now(timezone.utc)
            
        except Exception as e:
            logger.error(f"Error en flush del buffer: {e}")
    
    def _periodic_analysis(self):
        """Análisis periódico de logs"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Análisis de rendimiento cada hora
            if hasattr(self, '_last_performance_analysis'):
                time_diff = (current_time - self._last_performance_analysis).total_seconds()
                if time_diff >= self.config['analysis_intervals']['performance_summary']:
                    self._analyze_performance()
                    self._last_performance_analysis = current_time
            else:
                self._last_performance_analysis = current_time
            
            # Análisis de decisiones cada 30 minutos
            if hasattr(self, '_last_decision_analysis'):
                time_diff = (current_time - self._last_decision_analysis).total_seconds()
                if time_diff >= self.config['analysis_intervals']['decision_analysis']:
                    self._analyze_decisions()
                    self._last_decision_analysis = current_time
            else:
                self._last_decision_analysis = current_time
                
        except Exception as e:
            logger.error(f"Error en análisis periódico: {e}")
    
    def _analyze_performance(self):
        """Analiza métricas de rendimiento"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Obtener métricas de la última hora
                one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
                
                cursor = conn.execute("""
                    SELECT AVG(analysis_duration_ms), AVG(memory_usage_mb), AVG(cpu_usage_percent),
                           AVG(api_response_time_ms), COUNT(*) as total_analyses
                    FROM performance_metrics 
                    WHERE timestamp > ? AND session_id = ?
                """, (one_hour_ago, self.session_id))
                
                result = cursor.fetchone()
                
                if result and result[4] > 0:  # Si hay datos
                    avg_analysis_time, avg_memory, avg_cpu, avg_api_time, total = result
                    
                    performance_summary = {
                        'period': 'last_hour',
                        'avg_analysis_duration_ms': avg_analysis_time,
                        'avg_memory_usage_mb': avg_memory,
                        'avg_cpu_usage_percent': avg_cpu,
                        'avg_api_response_time_ms': avg_api_time,
                        'total_analyses': total,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    self.log(
                        LogLevel.PERFORMANCE,
                        EventType.PERFORMANCE_METRIC,
                        f"Resumen de rendimiento (1h): {total} análisis, {avg_analysis_time:.2f}ms promedio",
                        "PerformanceAnalyzer",
                        data=performance_summary
                    )
                    
        except Exception as e:
            logger.error(f"Error analizando rendimiento: {e}")
    
    def _analyze_decisions(self):
        """Analiza patrones de decisión"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Obtener decisiones de los últimos 30 minutos
                thirty_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
                
                cursor = conn.execute("""
                    SELECT AVG(confidence_score), AVG(signal_strength), COUNT(*) as total_decisions,
                           SUM(CASE WHEN conditions_met != '[]' THEN 1 ELSE 0 END) as signals_generated
                    FROM decision_contexts 
                    WHERE timestamp > ? AND session_id = ?
                """, (thirty_min_ago, self.session_id))
                
                result = cursor.fetchone()
                
                if result and result[2] > 0:  # Si hay datos
                    avg_confidence, avg_strength, total, signals = result
                    
                    decision_summary = {
                        'period': 'last_30_minutes',
                        'avg_confidence_score': avg_confidence,
                        'avg_signal_strength': avg_strength,
                        'total_decisions': total,
                        'signals_generated': signals,
                        'signal_rate': (signals / total) * 100 if total > 0 else 0,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    self.log(
                        LogLevel.DECISION,
                        EventType.SIGNAL_GENERATED,
                        f"Resumen de decisiones (30m): {signals}/{total} señales ({decision_summary['signal_rate']:.1f}%)",
                        "DecisionAnalyzer",
                        data=decision_summary
                    )
                    
        except Exception as e:
            logger.error(f"Error analizando decisiones: {e}")
    
    def update_symbol_statistics(self, symbol: str):
        """Actualiza estadísticas para un símbolo específico"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Obtener estadísticas actuales del símbolo
                cursor = conn.execute("""
                    SELECT COUNT(*) as analyses,
                           SUM(CASE WHEN conditions_met != '[]' THEN 1 ELSE 0 END) as signals,
                           AVG(confidence_score) as avg_confidence
                    FROM decision_contexts 
                    WHERE session_id = ? AND symbol = ?
                """, (self.session_id, symbol))
                
                stats = cursor.fetchone()
                analyses, signals, avg_confidence = stats if stats else (0, 0, 0)
                
                # Obtener número de trades exitosos
                cursor = conn.execute("""
                    SELECT COUNT(*) as trades
                    FROM trade_executions 
                    WHERE session_id = ? AND symbol = ? AND success = 1
                """, (self.session_id, symbol))
                
                trades = cursor.fetchone()[0] if cursor.fetchone() else 0
                
                # Calcular tasa de éxito
                success_rate = (trades / signals * 100) if signals > 0 else 0
                
                # Insertar o actualizar estadísticas
                conn.execute("""
                    INSERT OR REPLACE INTO symbol_statistics 
                    (timestamp, session_id, symbol, total_analyses, total_signals, 
                     total_trades, success_rate, avg_confidence, last_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(timezone.utc).isoformat(),
                    self.session_id,
                    symbol,
                    analyses,
                    signals,
                    trades,
                    success_rate,
                    avg_confidence or 0,
                    datetime.now(timezone.utc).isoformat()
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error actualizando estadísticas para {symbol}: {e}")
    
    def get_symbol_metrics(self, symbol: str) -> Dict[str, Any]:
        """Obtiene métricas específicas de un símbolo"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Estadísticas de decisiones
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_decisions,
                           SUM(CASE WHEN conditions_met != '[]' THEN 1 ELSE 0 END) as signals_generated,
                           AVG(confidence_score) as avg_confidence,
                           MAX(confidence_score) as max_confidence,
                           MIN(confidence_score) as min_confidence
                    FROM decision_contexts 
                    WHERE session_id = ? AND symbol = ?
                """, (self.session_id, symbol))
                
                decision_stats = cursor.fetchone()
                
                # Estadísticas de rendimiento
                cursor = conn.execute("""
                    SELECT AVG(analysis_duration_ms) as avg_analysis_time,
                           MIN(analysis_duration_ms) as min_analysis_time,
                           MAX(analysis_duration_ms) as max_analysis_time,
                           AVG(memory_usage_mb) as avg_memory,
                           AVG(cpu_usage_percent) as avg_cpu
                    FROM performance_metrics 
                    WHERE session_id = ? AND symbol = ?
                """, (self.session_id, symbol))
                
                perf_stats = cursor.fetchone()
                
                # Estadísticas de mercado
                cursor = conn.execute("""
                    SELECT COUNT(*) as market_updates,
                           AVG(price) as avg_price,
                           MIN(price) as min_price,
                           MAX(price) as max_price,
                           AVG(volume) as avg_volume,
                           AVG(volatility) as avg_volatility
                    FROM market_conditions 
                    WHERE session_id = ? AND symbol = ?
                """, (self.session_id, symbol))
                
                market_stats = cursor.fetchone()
                
                # Estadísticas de ejecución
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_executions,
                           SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions,
                           AVG(execution_time_ms) as avg_execution_time
                    FROM trade_executions 
                    WHERE session_id = ? AND symbol = ?
                """, (self.session_id, symbol))
                
                execution_stats = cursor.fetchone()
                
                return {
                    'symbol': symbol,
                    'decisions': {
                        'total': decision_stats[0] if decision_stats else 0,
                        'signals_generated': decision_stats[1] if decision_stats else 0,
                        'avg_confidence': decision_stats[2] if decision_stats else 0,
                        'max_confidence': decision_stats[3] if decision_stats else 0,
                        'min_confidence': decision_stats[4] if decision_stats else 0,
                        'signal_rate': (decision_stats[1] / decision_stats[0] * 100) if decision_stats and decision_stats[0] > 0 else 0
                    },
                    'performance': {
                        'avg_analysis_time_ms': perf_stats[0] if perf_stats else 0,
                        'min_analysis_time_ms': perf_stats[1] if perf_stats else 0,
                        'max_analysis_time_ms': perf_stats[2] if perf_stats else 0,
                        'avg_memory_mb': perf_stats[3] if perf_stats else 0,
                        'avg_cpu_percent': perf_stats[4] if perf_stats else 0
                    },
                    'market': {
                        'updates': market_stats[0] if market_stats else 0,
                        'avg_price': market_stats[1] if market_stats else 0,
                        'min_price': market_stats[2] if market_stats else 0,
                        'max_price': market_stats[3] if market_stats else 0,
                        'avg_volume': market_stats[4] if market_stats else 0,
                        'avg_volatility': market_stats[5] if market_stats else 0
                    },
                    'executions': {
                        'total': execution_stats[0] if execution_stats else 0,
                        'successful': execution_stats[1] if execution_stats else 0,
                        'success_rate': (execution_stats[1] / execution_stats[0] * 100) if execution_stats and execution_stats[0] > 0 else 0,
                        'avg_execution_time_ms': execution_stats[2] if execution_stats else 0
                    },
                    'counters': self.symbol_counters.get(symbol, {})
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo métricas para {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de la sesión actual con estadísticas por símbolo"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Estadísticas generales
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_logs, 
                           MIN(timestamp) as first_log,
                           MAX(timestamp) as last_log
                    FROM log_entries 
                    WHERE session_id = ?
                """, (self.session_id,))
                
                general_stats = cursor.fetchone()
                
                # Estadísticas por nivel
                cursor = conn.execute("""
                    SELECT level, COUNT(*) as count
                    FROM log_entries 
                    WHERE session_id = ?
                    GROUP BY level
                """, (self.session_id,))
                
                level_stats = dict(cursor.fetchall())
                
                # Estadísticas de rendimiento
                cursor = conn.execute("""
                    SELECT AVG(analysis_duration_ms), AVG(memory_usage_mb), 
                           AVG(cpu_usage_percent), COUNT(*) as performance_records
                    FROM performance_metrics 
                    WHERE session_id = ?
                """, (self.session_id,))
                
                perf_stats = cursor.fetchone()
                
                # Estadísticas de decisiones por símbolo
                cursor = conn.execute("""
                    SELECT symbol, COUNT(*) as total_decisions,
                           SUM(CASE WHEN conditions_met != '[]' THEN 1 ELSE 0 END) as signals_generated,
                           AVG(confidence_score) as avg_confidence
                    FROM decision_contexts 
                    WHERE session_id = ?
                    GROUP BY symbol
                """, (self.session_id,))
                
                symbol_decision_stats = {}
                for row in cursor.fetchall():
                    symbol, total, signals, avg_conf = row
                    symbol_decision_stats[symbol] = {
                        'total_decisions': total,
                        'signals_generated': signals or 0,
                        'avg_confidence': avg_conf or 0,
                        'signal_rate': (signals / total * 100) if total > 0 else 0
                    }
                
                # Estadísticas de mercado por símbolo
                cursor = conn.execute("""
                    SELECT symbol, COUNT(*) as market_updates,
                           AVG(price) as avg_price,
                           AVG(volume) as avg_volume,
                           AVG(volatility) as avg_volatility
                    FROM market_conditions 
                    WHERE session_id = ?
                    GROUP BY symbol
                """, (self.session_id,))
                
                symbol_market_stats = {}
                for row in cursor.fetchall():
                    symbol, updates, avg_price, avg_vol, avg_volatility = row
                    symbol_market_stats[symbol] = {
                        'market_updates': updates,
                        'avg_price': avg_price or 0,
                        'avg_volume': avg_vol or 0,
                        'avg_volatility': avg_volatility or 0
                    }
                
                # Estadísticas generales de decisiones
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_decisions,
                           SUM(CASE WHEN conditions_met != '[]' THEN 1 ELSE 0 END) as signals_generated,
                           AVG(confidence_score) as avg_confidence
                    FROM decision_contexts 
                    WHERE session_id = ?
                """, (self.session_id,))
                
                decision_stats = cursor.fetchone()
                
                return {
                    'session_id': self.session_id,
                    'symbols_monitored': self.symbols,
                    'session_start': self.current_metrics['session_start'].isoformat(),
                    'current_time': datetime.now(timezone.utc).isoformat(),
                    'general': {
                        'total_logs': general_stats[0] if general_stats else 0,
                        'first_log': general_stats[1] if general_stats else None,
                        'last_log': general_stats[2] if general_stats else None
                    },
                    'by_level': level_stats,
                    'performance': {
                        'avg_analysis_duration_ms': perf_stats[0] if perf_stats else 0,
                        'avg_memory_usage_mb': perf_stats[1] if perf_stats else 0,
                        'avg_cpu_usage_percent': perf_stats[2] if perf_stats else 0,
                        'total_records': perf_stats[3] if perf_stats else 0
                    },
                    'decisions': {
                        'total_decisions': decision_stats[0] if decision_stats else 0,
                        'signals_generated': decision_stats[1] if decision_stats else 0,
                        'avg_confidence': decision_stats[2] if decision_stats else 0,
                        'signal_rate': (decision_stats[1] / decision_stats[0] * 100) if decision_stats and decision_stats[0] > 0 else 0
                    },
                    'by_symbol': {
                        'decisions': symbol_decision_stats,
                        'market': symbol_market_stats,
                        'counters': self.symbol_counters
                    },
                    'current_metrics': self.current_metrics
                }
                
        except Exception as e:
            logger.error(f"Error obteniendo resumen de sesión: {e}")
            return {'error': str(e)}
    
    def export_logs(self, format_type: str = 'json', 
                   start_time: datetime = None, 
                   end_time: datetime = None) -> str:
        """Exporta logs en formato especificado"""
        try:
            if not start_time:
                start_time = datetime.now(timezone.utc) - timedelta(hours=24)
            if not end_time:
                end_time = datetime.now(timezone.utc)
            
            filename = f"sicar_logs_{start_time.strftime('%Y%m%d_%H%M')}_{end_time.strftime('%Y%m%d_%H%M')}.{format_type}"
            
            with sqlite3.connect(self.db_path) as conn:
                if format_type == 'json':
                    cursor = conn.execute("""
                        SELECT * FROM log_entries 
                        WHERE timestamp BETWEEN ? AND ? AND session_id = ?
                        ORDER BY timestamp
                    """, (start_time.isoformat(), end_time.isoformat(), self.session_id))
                    
                    logs = []
                    for row in cursor.fetchall():
                        log_dict = {
                            'id': row[0],
                            'timestamp': row[1],
                            'level': row[2],
                            'event_type': row[3],
                            'message': row[4],
                            'session_id': row[5],
                            'component': row[6],
                            'data': json.loads(row[7]) if row[7] else {},
                            'performance_metrics': json.loads(row[8]) if row[8] else None,
                            'decision_context': json.loads(row[9]) if row[9] else None
                        }
                        logs.append(log_dict)
                    
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(logs, f, indent=2, ensure_ascii=False)
                
                elif format_type == 'csv':
                    df = pd.read_sql_query("""
                        SELECT timestamp, level, event_type, message, component, session_id
                        FROM log_entries 
                        WHERE timestamp BETWEEN ? AND ? AND session_id = ?
                        ORDER BY timestamp
                    """, conn, params=(start_time.isoformat(), end_time.isoformat(), self.session_id))
                    
                    df.to_csv(filename, index=False, encoding='utf-8')
                
                elif format_type == 'parquet':
                    df = pd.read_sql_query("""
                        SELECT * FROM log_entries 
                        WHERE timestamp BETWEEN ? AND ? AND session_id = ?
                        ORDER BY timestamp
                    """, conn, params=(start_time.isoformat(), end_time.isoformat(), self.session_id))
                    
                    df.to_parquet(filename, index=False)
            
            logger.info(f"Logs exportados a: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error exportando logs: {e}")
            return None

def main():
    """Función principal para testing"""
    print("📊 Iniciando Sistema de Logging Avanzado SICAR...")
    
    # Crear instancia del sistema
    logging_system = AdvancedLoggingSystem()
    
    try:
        # Iniciar logging
        logging_system.start_logging()
        
        print("✅ Sistema de logging iniciado correctamente")
        
        # Ejemplo de uso multi-símbolo
        print("🧪 Ejecutando pruebas de logging multi-símbolo...")
        
        # Log básico
        logging_system.log(
            LogLevel.INFO,
            EventType.SYSTEM_START,
            "Sistema de prueba multi-símbolo iniciado",
            "TestComponent"
        )
        
        # Simular datos para cada símbolo
        for symbol in ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']:
            # Log con métricas de rendimiento por símbolo
            performance = PerformanceMetrics(
                timestamp=datetime.now(timezone.utc),
                analysis_duration_ms=150.5 + hash(symbol) % 50,
                data_fetch_duration_ms=45.2,
                indicator_calculation_duration_ms=30.1,
                signal_generation_duration_ms=25.8,
                memory_usage_mb=128.5,
                cpu_usage_percent=15.2,
                api_response_time_ms=89.3,
                total_requests=10,
                successful_requests=9,
                failed_requests=1
            )
            
            logging_system.log_performance(performance, "TestPerformance", symbol)
            
            # Simular condiciones de mercado
            market_conditions = MarketConditions(
                timestamp=datetime.now(timezone.utc),
                symbol=symbol,
                price=50000.0 + hash(symbol) % 10000,
                volume=1000000.0,
                volatility=0.02,
                trend_direction="bullish",
                market_session="active",
                spread=0.01
            )
            
            logging_system.log_market_conditions(market_conditions)
            
            print(f"✅ Datos de prueba generados para {symbol}")
        
        # Mostrar resumen multi-símbolo
        print("\n📈 Resumen de sesión multi-símbolo:")
        summary = logging_system.get_session_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        
        # Mostrar estadísticas por símbolo
        print("\n🎯 Estadísticas por símbolo:")
        if 'by_symbol' in summary:
            for symbol in logging_system.symbols:
                print(f"\n{symbol}:")
                if symbol in summary['by_symbol']['counters']:
                    counters = summary['by_symbol']['counters'][symbol]
                    print(f"  - Análisis: {counters['analyses']}")
                    print(f"  - Señales: {counters['signals']}")
                    print(f"  - Trades: {counters['trades']}")
                    print(f"  - Actualizaciones de mercado: {counters['market_updates']}")
                    print(f"  - Errores: {counters['errors']}")
        
        # Mantener ejecutándose por un tiempo
        time.sleep(5)
        
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo sistema de logging...")
    finally:
        logging_system.stop_logging()
        print("✅ Sistema de logging detenido correctamente")

if __name__ == "__main__":
    main()