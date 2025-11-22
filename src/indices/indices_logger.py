"""
SICAR Indices Logger
Sistema de logging adaptado para trading de índices
"""

import logging
import logging.handlers
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import pandas as pd
from enum import Enum

class LogLevel(Enum):
    """Niveles de logging específicos para índices"""
    MARKET_DATA = "MARKET_DATA"
    TRADING = "TRADING"
    RISK = "RISK"
    PERFORMANCE = "PERFORMANCE"
    SYSTEM = "SYSTEM"
    ERROR = "ERROR"
    DEBUG = "DEBUG"

class MarketSession(Enum):
    """Sesiones de mercado para logging"""
    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"

class IndicesLogger:
    """
    Logger especializado para trading de índices
    Incluye funcionalidades específicas para mercados estadounidenses
    """
    
    def __init__(self, 
                 name: str = "sicar_indices",
                 log_dir: str = "logs/indices",
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5):
        
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurar logger principal
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar duplicación de handlers
        if not self.logger.handlers:
            self._setup_handlers(max_file_size, backup_count)
        
        # Configurar loggers especializados
        self._setup_specialized_loggers()
        
        # Métricas de sesión
        self.session_metrics = {
            'trades_count': 0,
            'data_requests': 0,
            'errors_count': 0,
            'session_start': None,
            'current_session': MarketSession.CLOSED
        }
    
    def _setup_handlers(self, max_file_size: int, backup_count: int):
        """Configurar handlers de logging"""
        
        # Formatter principal
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(session)s | %(symbol)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para archivo principal
        main_file = self.log_dir / f"{self.name}.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_file, 
            maxBytes=max_file_size, 
            backupCount=backup_count
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(formatter)
        
        # Handler para errores
        error_file = self.log_dir / f"{self.name}_errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        
        # Añadir handlers
        self.logger.addHandler(main_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
    
    def _setup_specialized_loggers(self):
        """Configurar loggers especializados"""
        
        # Logger para datos de mercado
        self.market_logger = logging.getLogger(f"{self.name}.market")
        market_file = self.log_dir / "market_data.log"
        market_handler = logging.handlers.TimedRotatingFileHandler(
            market_file, when='midnight', interval=1, backupCount=30
        )
        market_formatter = logging.Formatter(
            '%(asctime)s | %(symbol)s | %(source)s | %(message)s'
        )
        market_handler.setFormatter(market_formatter)
        self.market_logger.addHandler(market_handler)
        
        # Logger para trading
        self.trading_logger = logging.getLogger(f"{self.name}.trading")
        trading_file = self.log_dir / "trading.log"
        trading_handler = logging.handlers.TimedRotatingFileHandler(
            trading_file, when='midnight', interval=1, backupCount=90
        )
        trading_formatter = logging.Formatter(
            '%(asctime)s | %(symbol)s | %(action)s | %(quantity)s | %(price)s | %(message)s'
        )
        trading_handler.setFormatter(trading_formatter)
        self.trading_logger.addHandler(trading_handler)
        
        # Logger para performance
        self.performance_logger = logging.getLogger(f"{self.name}.performance")
        perf_file = self.log_dir / "performance.log"
        perf_handler = logging.handlers.TimedRotatingFileHandler(
            perf_file, when='midnight', interval=1, backupCount=365
        )
        perf_formatter = logging.Formatter(
            '%(asctime)s | %(metric)s | %(value)s | %(period)s | %(message)s'
        )
        perf_handler.setFormatter(perf_formatter)
        self.performance_logger.addHandler(perf_handler)
    
    def log_market_data(self, 
                       symbol: str,
                       source: str,
                       data_type: str,
                       message: str,
                       data_quality: Optional[float] = None,
                       session: Optional[MarketSession] = None):
        """Log de datos de mercado"""
        
        extra = {
            'symbol': symbol,
            'source': source,
            'session': session.value if session else self._get_current_session().value
        }
        
        log_message = f"{data_type} | {message}"
        if data_quality is not None:
            log_message += f" | Quality: {data_quality:.2f}"
        
        self.market_logger.info(log_message, extra=extra)
        self.session_metrics['data_requests'] += 1
    
    def log_trade(self,
                  symbol: str,
                  action: str,  # BUY, SELL, CLOSE
                  quantity: Union[int, float],
                  price: float,
                  order_type: str = "MARKET",
                  session: Optional[MarketSession] = None,
                  additional_info: Optional[Dict] = None):
        """Log de operaciones de trading"""
        
        extra = {
            'symbol': symbol,
            'action': action,
            'quantity': str(quantity),
            'price': str(price),
            'session': session.value if session else self._get_current_session().value
        }
        
        message = f"{order_type}"
        if additional_info:
            message += f" | {json.dumps(additional_info)}"
        
        self.trading_logger.info(message, extra=extra)
        self.session_metrics['trades_count'] += 1
        
        # Log también en el logger principal
        self.info(f"TRADE | {symbol} | {action} {quantity} @ {price}", 
                 symbol=symbol, session=session)
    
    def log_performance(self,
                       metric: str,
                       value: Union[float, int, str],
                       period: str = "daily",
                       portfolio_value: Optional[float] = None,
                       benchmark_comparison: Optional[Dict] = None):
        """Log de métricas de performance"""
        
        extra = {
            'metric': metric,
            'value': str(value),
            'period': period
        }
        
        message = ""
        if portfolio_value:
            message += f"Portfolio: ${portfolio_value:,.2f} | "
        
        if benchmark_comparison:
            message += f"vs Benchmark: {json.dumps(benchmark_comparison)}"
        
        self.performance_logger.info(message.strip(" | "), extra=extra)
    
    def log_risk_event(self,
                      event_type: str,
                      symbol: str,
                      severity: str,  # LOW, MEDIUM, HIGH, CRITICAL
                      description: str,
                      current_exposure: Optional[float] = None,
                      recommended_action: Optional[str] = None):
        """Log de eventos de riesgo"""
        
        level = logging.WARNING if severity in ['MEDIUM', 'HIGH'] else logging.ERROR
        
        message = f"RISK | {event_type} | {severity} | {symbol} | {description}"
        
        if current_exposure:
            message += f" | Exposure: {current_exposure:.2%}"
        
        if recommended_action:
            message += f" | Action: {recommended_action}"
        
        self.logger.log(level, message, extra={
            'symbol': symbol,
            'session': self._get_current_session().value
        })
        
        if severity == 'CRITICAL':
            self.session_metrics['errors_count'] += 1
    
    def log_session_start(self, session: MarketSession, symbols: List[str]):
        """Log de inicio de sesión de mercado"""
        
        self.session_metrics['session_start'] = datetime.now()
        self.session_metrics['current_session'] = session
        self.session_metrics['trades_count'] = 0
        self.session_metrics['data_requests'] = 0
        self.session_metrics['errors_count'] = 0
        
        message = f"SESSION START | {session.value} | Symbols: {', '.join(symbols)}"
        self.info(message, session=session)
    
    def log_session_end(self, session: MarketSession, summary: Optional[Dict] = None):
        """Log de fin de sesión de mercado"""
        
        duration = None
        if self.session_metrics['session_start']:
            duration = datetime.now() - self.session_metrics['session_start']
        
        message = f"SESSION END | {session.value}"
        
        if duration:
            message += f" | Duration: {duration}"
        
        message += f" | Trades: {self.session_metrics['trades_count']}"
        message += f" | Data Requests: {self.session_metrics['data_requests']}"
        message += f" | Errors: {self.session_metrics['errors_count']}"
        
        if summary:
            message += f" | Summary: {json.dumps(summary)}"
        
        self.info(message, session=session)
    
    def log_data_quality_issue(self,
                              symbol: str,
                              source: str,
                              issue_type: str,
                              severity: str,
                              details: str):
        """Log de problemas de calidad de datos"""
        
        message = f"DATA QUALITY | {symbol} | {source} | {issue_type} | {severity} | {details}"
        
        level = logging.WARNING if severity in ['LOW', 'MEDIUM'] else logging.ERROR
        self.logger.log(level, message, extra={
            'symbol': symbol,
            'session': self._get_current_session().value
        })
    
    def log_system_event(self,
                        event_type: str,
                        component: str,
                        status: str,
                        details: Optional[str] = None):
        """Log de eventos del sistema"""
        
        message = f"SYSTEM | {event_type} | {component} | {status}"
        
        if details:
            message += f" | {details}"
        
        level = logging.INFO if status == 'OK' else logging.WARNING
        self.logger.log(level, message, extra={
            'symbol': 'SYSTEM',
            'session': self._get_current_session().value
        })
    
    def info(self, message: str, symbol: str = "", session: Optional[MarketSession] = None):
        """Log de información general"""
        self.logger.info(message, extra={
            'symbol': symbol,
            'session': session.value if session else self._get_current_session().value
        })
    
    def warning(self, message: str, symbol: str = "", session: Optional[MarketSession] = None):
        """Log de advertencia"""
        self.logger.warning(message, extra={
            'symbol': symbol,
            'session': session.value if session else self._get_current_session().value
        })
    
    def error(self, message: str, symbol: str = "", session: Optional[MarketSession] = None, exc_info: bool = False):
        """Log de error"""
        self.logger.error(message, extra={
            'symbol': symbol,
            'session': session.value if session else self._get_current_session().value
        }, exc_info=exc_info)
        
        self.session_metrics['errors_count'] += 1
    
    def debug(self, message: str, symbol: str = "", session: Optional[MarketSession] = None):
        """Log de debug"""
        self.logger.debug(message, extra={
            'symbol': symbol,
            'session': session.value if session else self._get_current_session().value
        })
    
    def _get_current_session(self) -> MarketSession:
        """Determinar sesión actual del mercado"""
        now = datetime.now()
        current_time = now.time()
        
        # Verificar si es fin de semana
        if now.weekday() >= 5:
            return MarketSession.CLOSED
        
        # Horarios Eastern Time (simplificado)
        if current_time >= datetime.strptime("04:00", "%H:%M").time() and current_time < datetime.strptime("09:30", "%H:%M").time():
            return MarketSession.PRE_MARKET
        elif current_time >= datetime.strptime("09:30", "%H:%M").time() and current_time < datetime.strptime("16:00", "%H:%M").time():
            return MarketSession.REGULAR
        elif current_time >= datetime.strptime("16:00", "%H:%M").time() and current_time < datetime.strptime("20:00", "%H:%M").time():
            return MarketSession.AFTER_HOURS
        else:
            return MarketSession.CLOSED
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Obtener métricas de la sesión actual"""
        return self.session_metrics.copy()
    
    def export_logs_to_csv(self, 
                          log_type: str = "trading",
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> str:
        """Exportar logs a CSV para análisis"""
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        log_file = self.log_dir / f"{log_type}.log"
        
        if not log_file.exists():
            return ""
        
        # Leer y parsear logs
        logs_data = []
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    # Parsear línea de log
                    parts = line.strip().split(' | ')
                    if len(parts) >= 4:
                        timestamp_str = parts[0]
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        
                        if start_date <= timestamp <= end_date:
                            logs_data.append({
                                'timestamp': timestamp,
                                'symbol': parts[1] if len(parts) > 1 else '',
                                'action': parts[2] if len(parts) > 2 else '',
                                'details': ' | '.join(parts[3:]) if len(parts) > 3 else ''
                            })
                except:
                    continue
        
        # Crear DataFrame y exportar
        if logs_data:
            df = pd.DataFrame(logs_data)
            output_file = self.log_dir / f"{log_type}_export_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            df.to_csv(output_file, index=False)
            return str(output_file)
        
        return ""
    
    def cleanup_old_logs(self, days_to_keep: int = 90):
        """Limpiar logs antiguos"""
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    self.info(f"Deleted old log file: {log_file.name}")
            except Exception as e:
                self.error(f"Error deleting log file {log_file.name}: {e}")

# Instancia global del logger
indices_logger = IndicesLogger()

# Funciones de conveniencia
def log_trade(symbol: str, action: str, quantity: Union[int, float], price: float, **kwargs):
    """Función de conveniencia para logging de trades"""
    indices_logger.log_trade(symbol, action, quantity, price, **kwargs)

def log_market_data(symbol: str, source: str, data_type: str, message: str, **kwargs):
    """Función de conveniencia para logging de datos de mercado"""
    indices_logger.log_market_data(symbol, source, data_type, message, **kwargs)

def log_performance(metric: str, value: Union[float, int, str], **kwargs):
    """Función de conveniencia para logging de performance"""
    indices_logger.log_performance(metric, value, **kwargs)

def log_risk_event(event_type: str, symbol: str, severity: str, description: str, **kwargs):
    """Función de conveniencia para logging de riesgo"""
    indices_logger.log_risk_event(event_type, symbol, severity, description, **kwargs)

def get_logger(name: str = "sicar_indices") -> IndicesLogger:
    """Obtener instancia del logger"""
    return IndicesLogger(name)