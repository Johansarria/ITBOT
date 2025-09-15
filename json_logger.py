import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time
from pathlib import Path

class LogType(Enum):
    """Tipos de logs para el sistema"""
    SYSTEM = "system"
    TRADE = "trade"
    SIGNAL = "signal"
    PERFORMANCE = "performance"
    ALERT = "alert"
    ERROR = "error"
    PORTFOLIO = "portfolio"
    MARKET_DATA = "market_data"

@dataclass
class LogEntry:
    """Entrada de log estructurada"""
    timestamp: str
    log_type: str
    level: str
    message: str
    data: Dict[str, Any]
    session_id: str
    symbol: Optional[str] = None
    strategy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ResilientJSONLogger:
    """Logger JSON resiliente con backup automático y recuperación"""
    
    def __init__(self, base_filename: str = "paper_trading_logs", max_file_size_mb: int = 50):
        self.base_filename = base_filename
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Crear directorio de logs si no existe
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Archivos de log
        self.current_log_file = self.logs_dir / f"{base_filename}_{self.session_id}.json"
        self.backup_dir = self.logs_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Buffer para escritura asíncrona
        self.log_buffer: List[LogEntry] = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 100
        
        # Control de escritura
        self.writing_thread = None
        self.stop_writing = False
        self.write_interval = 5  # segundos
        
        # Inicializar archivo de log
        self._initialize_log_file()
        
        # Iniciar thread de escritura
        self._start_writing_thread()
        
    def _initialize_log_file(self):
        """Inicializa el archivo de log con metadata"""
        try:
            initial_data = {
                "session_info": {
                    "session_id": self.session_id,
                    "start_time": datetime.now().isoformat(),
                    "system": "Paper Trading Simulator",
                    "version": "1.0.0"
                },
                "logs": []
            }
            
            with open(self.current_log_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error inicializando archivo de log: {e}")
            
    def _start_writing_thread(self):
        """Inicia el thread de escritura asíncrona"""
        self.writing_thread = threading.Thread(target=self._writing_loop, daemon=True)
        self.writing_thread.start()
        
    def _writing_loop(self):
        """Loop de escritura asíncrona"""
        while not self.stop_writing:
            try:
                self._flush_buffer()
                time.sleep(self.write_interval)
            except Exception as e:
                print(f"Error en loop de escritura: {e}")
                time.sleep(1)
                
    def _flush_buffer(self):
        """Escribe el buffer al archivo"""
        if not self.log_buffer:
            return
            
        with self.buffer_lock:
            if not self.log_buffer:
                return
                
            logs_to_write = self.log_buffer.copy()
            self.log_buffer.clear()
            
        try:
            # Verificar tamaño del archivo
            if self.current_log_file.exists() and self.current_log_file.stat().st_size > self.max_file_size_bytes:
                self._rotate_log_file()
                
            # Leer archivo actual
            if self.current_log_file.exists():
                with open(self.current_log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                self._initialize_log_file()
                with open(self.current_log_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
            # Agregar nuevos logs
            for log_entry in logs_to_write:
                data["logs"].append(log_entry.to_dict())
                
            # Escribir archivo actualizado
            temp_file = self.current_log_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            # Reemplazar archivo original
            temp_file.replace(self.current_log_file)
            
        except Exception as e:
            print(f"Error escribiendo logs: {e}")
            # Revertir buffer en caso de error
            with self.buffer_lock:
                self.log_buffer = logs_to_write + self.log_buffer
                
    def _rotate_log_file(self):
        """Rota el archivo de log cuando alcanza el tamaño máximo"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{self.base_filename}_{timestamp}.json"
            
            # Mover archivo actual a backup
            if self.current_log_file.exists():
                self.current_log_file.rename(backup_file)
                
            # Crear nuevo archivo
            self._initialize_log_file()
            
            print(f"Log rotado: {backup_file}")
            
        except Exception as e:
            print(f"Error rotando archivo de log: {e}")
            
    def log(self, log_type: LogType, level: str, message: str, data: Dict[str, Any] = None, 
            symbol: str = None, strategy: str = None):
        """Registra una entrada de log"""
        try:
            log_entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                log_type=log_type.value,
                level=level,
                message=message,
                data=data or {},
                session_id=self.session_id,
                symbol=symbol,
                strategy=strategy
            )
            
            with self.buffer_lock:
                self.log_buffer.append(log_entry)
                
                # Flush inmediato si el buffer está lleno o es crítico
                if len(self.log_buffer) >= self.max_buffer_size or level in ['ERROR', 'CRITICAL']:
                    threading.Thread(target=self._flush_buffer, daemon=True).start()
                    
        except Exception as e:
            print(f"Error registrando log: {e}")
            
    def log_trade(self, trade_data: Dict[str, Any]):
        """Log específico para trades"""
        self.log(
            LogType.TRADE,
            "INFO",
            f"Trade {trade_data.get('action', 'unknown')} - {trade_data.get('symbol', 'unknown')}",
            trade_data,
            symbol=trade_data.get('symbol'),
            strategy=trade_data.get('strategy')
        )
        
    def log_signal(self, signal_data: Dict[str, Any]):
        """Log específico para señales"""
        self.log(
            LogType.SIGNAL,
            "INFO",
            f"Signal {signal_data.get('type', 'unknown')} - {signal_data.get('symbol', 'unknown')}",
            signal_data,
            symbol=signal_data.get('symbol'),
            strategy=signal_data.get('strategy')
        )
        
    def log_performance(self, performance_data: Dict[str, Any]):
        """Log específico para performance"""
        self.log(
            LogType.PERFORMANCE,
            "INFO",
            "Performance update",
            performance_data
        )
        
    def log_alert(self, alert_data: Dict[str, Any]):
        """Log específico para alertas"""
        level = "WARNING" if alert_data.get('severity') == 'medium' else "ERROR"
        self.log(
            LogType.ALERT,
            level,
            alert_data.get('message', 'Alert triggered'),
            alert_data
        )
        
    def log_error(self, error_message: str, error_data: Dict[str, Any] = None):
        """Log específico para errores"""
        self.log(
            LogType.ERROR,
            "ERROR",
            error_message,
            error_data or {}
        )
        
    def get_logs_by_type(self, log_type: LogType, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Obtiene logs por tipo en las últimas horas"""
        try:
            if not self.current_log_file.exists():
                return []
                
            with open(self.current_log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            filtered_logs = []
            for log in data.get("logs", []):
                if log.get("log_type") == log_type.value:
                    log_time = datetime.fromisoformat(log.get("timestamp", ""))
                    if log_time >= cutoff_time:
                        filtered_logs.append(log)
                        
            return filtered_logs
            
        except Exception as e:
            print(f"Error obteniendo logs: {e}")
            return []
            
    def get_session_summary(self) -> Dict[str, Any]:
        """Obtiene resumen de la sesión actual"""
        try:
            if not self.current_log_file.exists():
                return {}
                
            with open(self.current_log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            logs = data.get("logs", [])
            
            # Contar por tipo
            type_counts = {}
            for log in logs:
                log_type = log.get("log_type", "unknown")
                type_counts[log_type] = type_counts.get(log_type, 0) + 1
                
            # Obtener trades
            trades = [log for log in logs if log.get("log_type") == "trade"]
            
            # Calcular estadísticas
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.get("data", {}).get("pnl", 0) > 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            return {
                "session_id": self.session_id,
                "session_info": data.get("session_info", {}),
                "total_logs": len(logs),
                "logs_by_type": type_counts,
                "trading_stats": {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "win_rate": win_rate
                },
                "file_size_mb": self.current_log_file.stat().st_size / (1024 * 1024) if self.current_log_file.exists() else 0
            }
            
        except Exception as e:
            print(f"Error obteniendo resumen: {e}")
            return {}
            
    def close(self):
        """Cierra el logger y escribe logs pendientes"""
        self.stop_writing = True
        if self.writing_thread and self.writing_thread.is_alive():
            self.writing_thread.join(timeout=10)
            
        # Flush final
        self._flush_buffer()
        
        print(f"Logger cerrado. Logs guardados en: {self.current_log_file}")
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == "__main__":
    # Ejemplo de uso
    with ResilientJSONLogger("test_logs") as logger:
        
        # Log de sistema
        logger.log(LogType.SYSTEM, "INFO", "Sistema iniciado", {"version": "1.0.0"})
        
        # Log de trade
        logger.log_trade({
            "action": "BUY",
            "symbol": "BTCUSDT",
            "price": 43250.45,
            "quantity": 0.1,
            "strategy": "MOMENTUM",
            "pnl": 127.45
        })
        
        # Log de señal
        logger.log_signal({
            "type": "BUY",
            "symbol": "ETHUSDT",
            "strength": 0.78,
            "strategy": "BREAKOUT",
            "indicators": {
                "rsi": 68.5,
                "macd": "bullish"
            }
        })
        
        # Log de performance
        logger.log_performance({
            "total_capital": 10245.67,
            "total_return_pct": 2.46,
            "daily_return_pct": 0.85,
            "total_trades": 8,
            "win_rate": 62.5
        })
        
        # Log de alerta
        logger.log_alert({
            "type": "HIGH_DRAWDOWN",
            "message": "Drawdown alto detectado",
            "severity": "high",
            "value": 4.5
        })
        
        time.sleep(2)  # Permitir que se escriban los logs
        
        # Mostrar resumen
        summary = logger.get_session_summary()
        print("\nResumen de sesión:")
        print(json.dumps(summary, indent=2, ensure_ascii=False))