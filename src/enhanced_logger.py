"""
Sistema de Logging Mejorado para SICAR
Implementa logs detallados y categorizados
"""

import logging
import logging.handlers
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from enhanced_config import CONFIG

class SicarLogger:
    """Sistema de logging mejorado para SICAR"""
    
    def __init__(self):
        self.loggers: Dict[str, logging.Logger] = {}
        self.setup_logging()
    
    def setup_logging(self):
        """Configurar el sistema de logging"""
        # Asegurar que existan los directorios
        CONFIG.ensure_directories()
        
        # Configurar cada tipo de logger
        log_types = ['main', 'trading', 'breakouts', 'sessions', 'errors']
        
        for log_type in log_types:
            logger = self._create_logger(log_type)
            self.loggers[log_type] = logger
    
    def _create_logger(self, log_type: str) -> logging.Logger:
        """Crear un logger específico"""
        logger_name = f"sicar.{log_type}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(CONFIG.LOGGING_CONFIG['level'])
        
        # Evitar duplicar handlers
        if logger.handlers:
            return logger
        
        # Handler para archivo con rotación
        log_file = CONFIG.get_log_file_path(log_type)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=CONFIG.LOGGING_CONFIG['max_file_size'],
            backupCount=CONFIG.LOGGING_CONFIG['backup_count'],
            encoding='utf-8'
        )
        
        # Handler para consola (solo para main y errors)
        if log_type in ['main', 'errors']:
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # Formatter para archivo
        file_formatter = logging.Formatter(
            CONFIG.LOGGING_CONFIG['format'],
            datefmt=CONFIG.LOGGING_CONFIG['date_format']
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def log_session_start(self, session_name: str, session_info: Dict[str, Any]):
        """Log del inicio de sesión"""
        logger = self.loggers['sessions']
        logger.info(f"🚀 SESIÓN INICIADA: {session_name}")
        logger.info(f"   Configuración: {json.dumps(session_info, indent=2)}")
    
    def log_session_end(self, session_name: str, summary: Dict[str, Any]):
        """Log del fin de sesión"""
        logger = self.loggers['sessions']
        logger.info(f"🏁 SESIÓN FINALIZADA: {session_name}")
        logger.info(f"   Resumen: {json.dumps(summary, indent=2)}")
    
    def log_breakout_detected(self, symbol: str, breakout_info: Dict[str, Any]):
        """Log de breakout detectado"""
        logger = self.loggers['breakouts']
        logger.info(f"📈 BREAKOUT DETECTADO: {symbol}")
        logger.info(f"   Tipo: {breakout_info.get('signal_type', 'N/A')}")
        logger.info(f"   Confianza: {breakout_info.get('confidence', 0):.2%}")
        logger.info(f"   Precio: ${breakout_info.get('price', 0):.4f}")
        logger.info(f"   Volumen: {breakout_info.get('volume', 0):,.0f}")
    
    def log_trade_executed(self, trade_info: Dict[str, Any]):
        """Log de trade ejecutado"""
        logger = self.loggers['trading']
        logger.info(f"💰 TRADE EJECUTADO")
        logger.info(f"   Símbolo: {trade_info.get('symbol', 'N/A')}")
        logger.info(f"   Lado: {trade_info.get('side', 'N/A')}")
        logger.info(f"   Cantidad: {trade_info.get('quantity', 0):.6f}")
        logger.info(f"   Precio: ${trade_info.get('price', 0):.4f}")
        logger.info(f"   Valor: ${trade_info.get('value', 0):.2f}")
        logger.info(f"   ID: {trade_info.get('order_id', 'N/A')}")
    
    def log_position_update(self, symbol: str, position_info: Dict[str, Any]):
        """Log de actualización de posición"""
        logger = self.loggers['trading']
        logger.info(f"📊 POSICIÓN ACTUALIZADA: {symbol}")
        logger.info(f"   PnL: ${position_info.get('pnl', 0):.2f} ({position_info.get('pnl_pct', 0):.2f}%)")
        logger.info(f"   Precio actual: ${position_info.get('current_price', 0):.4f}")
        logger.info(f"   Precio entrada: ${position_info.get('entry_price', 0):.4f}")
    
    def log_auto_trading_status(self, enabled: bool, reason: str = ""):
        """Log del estado del auto trading"""
        logger = self.loggers['main']
        status = "ACTIVADO" if enabled else "DESACTIVADO"
        logger.info(f"🤖 AUTO TRADING {status}")
        if reason:
            logger.info(f"   Razón: {reason}")
    
    def log_sync_operation(self, operation: str, success: bool, details: str = ""):
        """Log de operaciones de sincronización"""
        logger = self.loggers['main']
        status = "✅ ÉXITO" if success else "❌ ERROR"
        logger.info(f"🔄 SYNC {operation}: {status}")
        if details:
            logger.info(f"   Detalles: {details}")
    
    def log_error(self, error_type: str, error_msg: str, context: Dict[str, Any] = None):
        """Log de errores"""
        logger = self.loggers['errors']
        logger.error(f"❌ ERROR {error_type}: {error_msg}")
        if context:
            logger.error(f"   Contexto: {json.dumps(context, indent=2)}")
    
    def log_performance_metrics(self, metrics: Dict[str, Any]):
        """Log de métricas de performance"""
        logger = self.loggers['trading']
        logger.info("📈 MÉTRICAS DE PERFORMANCE")
        logger.info(f"   Capital total: ${metrics.get('total_capital', 0):.2f}")
        logger.info(f"   PnL total: ${metrics.get('total_pnl', 0):.2f}")
        logger.info(f"   Trades totales: {metrics.get('total_trades', 0)}")
        logger.info(f"   Trades ganadores: {metrics.get('winning_trades', 0)}")
        logger.info(f"   Win rate: {metrics.get('win_rate', 0):.2%}")
        logger.info(f"   Drawdown máximo: {metrics.get('max_drawdown', 0):.2%}")
    
    def log_alert(self, alert_type: str, message: str, priority: str = "INFO"):
        """Log de alertas"""
        logger = self.loggers['main']
        emoji = {"HIGH": "🚨", "MEDIUM": "⚠️", "LOW": "ℹ️"}.get(priority, "📢")
        logger.info(f"{emoji} ALERTA {alert_type}: {message}")
    
    def get_logger(self, log_type: str) -> logging.Logger:
        """Obtener un logger específico"""
        return self.loggers.get(log_type, self.loggers['main'])

# Instancia global del logger
SICAR_LOGGER = SicarLogger()

# Funciones de conveniencia
def log_session_start(session_name: str, session_info: Dict[str, Any]):
    SICAR_LOGGER.log_session_start(session_name, session_info)

def log_breakout_detected(symbol: str, breakout_info: Dict[str, Any]):
    SICAR_LOGGER.log_breakout_detected(symbol, breakout_info)

def log_trade_executed(trade_info: Dict[str, Any]):
    SICAR_LOGGER.log_trade_executed(trade_info)

def log_auto_trading_status(enabled: bool, reason: str = ""):
    SICAR_LOGGER.log_auto_trading_status(enabled, reason)

def log_error(error_type: str, error_msg: str, context: Dict[str, Any] = None):
    SICAR_LOGGER.log_error(error_type, error_msg, context)

def log_alert(alert_type: str, message: str, priority: str = "INFO"):
    SICAR_LOGGER.log_alert(alert_type, message, priority)