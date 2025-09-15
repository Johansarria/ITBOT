import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import threading
import time
from colorama import Fore, Back, Style, init
from paper_trading_simulator import PaperTradingSimulator
from performance_reporter import PerformanceReporter
from trade_executor import TradingSimulator, Position, OrderStatus
from trading_signals import SignalType, StrategyType

# Inicializar colorama para colores en consola
init(autoreset=True)

class LogLevel(Enum):
    """Niveles de logging"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    TRADE = "TRADE"
    SIGNAL = "SIGNAL"
    PERFORMANCE = "PERFORMANCE"
    ALERT = "ALERT"

class ConsoleColors:
    """Colores para diferentes tipos de mensajes"""
    TRADE_BUY = Fore.GREEN + Style.BRIGHT
    TRADE_SELL = Fore.RED + Style.BRIGHT
    PROFIT = Fore.GREEN
    LOSS = Fore.RED
    WARNING = Fore.YELLOW + Style.BRIGHT
    ERROR = Fore.RED + Style.BRIGHT
    INFO = Fore.CYAN
    DEBUG = Fore.WHITE
    SIGNAL = Fore.MAGENTA + Style.BRIGHT
    PERFORMANCE = Fore.BLUE + Style.BRIGHT
    ALERT = Fore.YELLOW + Back.RED + Style.BRIGHT
    HEADER = Fore.WHITE + Back.BLUE + Style.BRIGHT
    RESET = Style.RESET_ALL

class ConsoleFormatter(logging.Formatter):
    """Formateador personalizado para logging en consola"""
    
    def __init__(self):
        super().__init__()
        self.formatters = {
            logging.DEBUG: logging.Formatter(
                f'{ConsoleColors.DEBUG}[%(asctime)s] DEBUG: %(message)s{ConsoleColors.RESET}'
            ),
            logging.INFO: logging.Formatter(
                f'{ConsoleColors.INFO}[%(asctime)s] INFO: %(message)s{ConsoleColors.RESET}'
            ),
            logging.WARNING: logging.Formatter(
                f'{ConsoleColors.WARNING}[%(asctime)s] WARNING: %(message)s{ConsoleColors.RESET}'
            ),
            logging.ERROR: logging.Formatter(
                f'{ConsoleColors.ERROR}[%(asctime)s] ERROR: %(message)s{ConsoleColors.RESET}'
            ),
            logging.CRITICAL: logging.Formatter(
                f'{ConsoleColors.ALERT}[%(asctime)s] CRITICAL: %(message)s{ConsoleColors.RESET}'
            )
        }
        
    def format(self, record):
        formatter = self.formatters.get(record.levelno)
        if formatter:
            return formatter.format(record)
        return super().format(record)

class MonitoringSystem:
    """Sistema de monitoreo y logging para paper trading"""
    
    def __init__(self, simulator: PaperTradingSimulator, performance_reporter: PerformanceReporter):
        self.simulator = simulator
        self.performance_reporter = performance_reporter
        
        # Configurar logging
        self.setup_logging()
        
        # Estado del sistema
        self.is_running = False
        self.monitoring_thread = None
        self.last_status_update = datetime.now()
        self.status_update_interval = timedelta(minutes=1)  # Actualización cada minuto
        
        # Contadores y métricas
        self.session_start_time = datetime.now()
        self.last_trade_count = 0
        self.last_signal_count = 0
        self.alerts_shown = set()  # Para evitar alertas duplicadas
        
        # Configuración de display
        self.show_debug = False
        self.show_signals = True
        self.show_performance = True
        self.compact_mode = False
        
    def setup_logging(self):
        """Configura el sistema de logging"""
        # Logger principal
        self.logger = logging.getLogger('PaperTrading')
        self.logger.setLevel(logging.DEBUG)
        
        # Limpiar handlers existentes
        self.logger.handlers.clear()
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ConsoleFormatter())
        self.logger.addHandler(console_handler)
        
        # Handler para archivo (opcional)
        file_handler = logging.FileHandler('paper_trading.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
    def start_monitoring(self):
        """Inicia el sistema de monitoreo"""
        if self.is_running:
            self.logger.warning("El sistema de monitoreo ya está ejecutándose")
            return
            
        self.is_running = True
        self.session_start_time = datetime.now()
        
        # Mostrar banner de inicio
        self.show_startup_banner()
        
        # Iniciar thread de monitoreo
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Sistema de monitoreo iniciado")
        
    def stop_monitoring(self):
        """Detiene el sistema de monitoreo"""
        self.is_running = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
            
        self.show_shutdown_summary()
        self.logger.info("Sistema de monitoreo detenido")
        
    def show_startup_banner(self):
        """Muestra banner de inicio"""
        banner = f"""
{ConsoleColors.HEADER}
╔══════════════════════════════════════════════════════════════╗
║                    PAPER TRADING SIMULATOR                   ║
║                     Sistema de Monitoreo                     ║
╚══════════════════════════════════════════════════════════════╝
{ConsoleColors.RESET}

{ConsoleColors.INFO}📊 Inicio de sesión: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}
💰 Capital inicial: ${self.simulator.trading_simulator.initial_capital:,.2f}
🎯 Símbolos monitoreados: {len(self.simulator.symbols)}
⚙️  Estrategias activas: {len([s for s in StrategyType])}
{ConsoleColors.RESET}

{ConsoleColors.WARNING}🔍 Iniciando monitoreo en tiempo real...{ConsoleColors.RESET}
"""
        print(banner)
        
    def show_shutdown_summary(self):
        """Muestra resumen al cerrar"""
        session_duration = datetime.now() - self.session_start_time
        
        # Obtener métricas finales
        current_status = self.performance_reporter.get_current_status()
        
        summary = f"""
{ConsoleColors.HEADER}
╔══════════════════════════════════════════════════════════════╗
║                      RESUMEN DE SESIÓN                       ║
╚══════════════════════════════════════════════════════════════╝
{ConsoleColors.RESET}

⏱️  Duración de sesión: {str(session_duration).split('.')[0]}
💰 Capital final: ${current_status.get('capital', {}).get('total', 0):,.2f}
📈 Retorno total: {current_status.get('performance', {}).get('total_return_pct', 0):.2f}%
🔄 Trades ejecutados: {current_status.get('trading', {}).get('total_trades', 0)}
🎯 Win Rate: {current_status.get('trading', {}).get('win_rate', 0):.1f}%
📊 Posiciones abiertas: {current_status.get('trading', {}).get('open_positions', 0)}

{ConsoleColors.INFO}¡Gracias por usar Paper Trading Simulator!{ConsoleColors.RESET}
"""
        print(summary)
        
    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        while self.is_running:
            try:
                # Verificar nuevos trades
                self._check_new_trades()
                
                # Verificar nuevas señales
                self._check_new_signals()
                
                # Actualizar estado periódicamente
                if datetime.now() - self.last_status_update >= self.status_update_interval:
                    self._show_status_update()
                    self.last_status_update = datetime.now()
                    
                # Verificar alertas
                self._check_alerts()
                
                # Pausa antes de la siguiente iteración
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error en loop de monitoreo: {e}")
                time.sleep(5)
                
    def _check_new_trades(self):
        """Verifica y reporta nuevos trades"""
        current_trade_count = len(self.simulator.trading_simulator.closed_trades)
        
        if current_trade_count > self.last_trade_count:
            # Hay nuevos trades
            new_trades = self.simulator.trading_simulator.closed_trades[self.last_trade_count:]
            
            for trade in new_trades:
                self._log_trade(trade)
                
            self.last_trade_count = current_trade_count
            
    def _log_trade(self, trade):
        """Registra un trade en el log"""
        # Determinar color basado en PnL
        color = ConsoleColors.PROFIT if trade.net_pnl > 0 else ConsoleColors.LOSS
        
        # Símbolo de resultado
        result_symbol = "✅" if trade.net_pnl > 0 else "❌"
        
        # Información del trade
        trade_info = f"""{color}{result_symbol} TRADE CERRADO:
   📊 Símbolo: {trade.symbol}
   🎯 Estrategia: {trade.strategy_type.value if trade.strategy_type else 'N/A'}
   💰 PnL: ${trade.net_pnl:,.2f} ({trade.return_pct:.2f}%)
   📈 Precio entrada: ${trade.entry_price:.4f}
   📉 Precio salida: ${trade.exit_price:.4f}
   ⏱️  Duración: {str(trade.duration).split('.')[0]}
   🔄 Razón salida: {trade.exit_reason}
   💸 Comisión: ${trade.commission:.2f}{ConsoleColors.RESET}"""
        
        print(trade_info)
        self.logger.info(f"Trade cerrado: {trade.symbol} PnL: ${trade.net_pnl:.2f}")
        
    def _check_new_signals(self):
        """Verifica y reporta nuevas señales"""
        if not self.show_signals:
            return
            
        # Aquí se verificarían las señales del sistema
        # Por ahora, simulamos con las posiciones abiertas
        open_positions = len([p for p in self.simulator.trading_simulator.positions.values() 
                            if p.status.value == 'open'])
        
        # Log de señales importantes (simplificado)
        if hasattr(self.simulator, 'last_signals'):
            for signal in getattr(self.simulator, 'last_signals', []):
                self._log_signal(signal)
                
    def _log_signal(self, signal_data):
        """Registra una señal en el log"""
        signal_color = ConsoleColors.TRADE_BUY if signal_data.get('type') == 'BUY' else ConsoleColors.TRADE_SELL
        
        signal_info = f"""{signal_color}🎯 SEÑAL DETECTADA:
   📊 Símbolo: {signal_data.get('symbol', 'N/A')}
   🔄 Tipo: {signal_data.get('type', 'N/A')}
   🎯 Estrategia: {signal_data.get('strategy', 'N/A')}
   💪 Fuerza: {signal_data.get('strength', 0):.2f}
   💰 Precio: ${signal_data.get('price', 0):.4f}{ConsoleColors.RESET}"""
        
        print(signal_info)
        
    def _show_status_update(self):
        """Muestra actualización de estado"""
        if not self.show_performance:
            return
            
        try:
            # Obtener estado actual
            status = self.performance_reporter.get_current_status()
            
            if not status or status.get('status') == 'No data available':
                return
                
            # Calcular tiempo de sesión
            session_time = datetime.now() - self.session_start_time
            session_str = str(session_time).split('.')[0]
            
            # Formato compacto o detallado
            if self.compact_mode:
                status_line = f"""{ConsoleColors.PERFORMANCE}📊 [{session_str}] Capital: ${status['capital']['total']:,.2f} | Retorno: {status['performance']['total_return_pct']:.2f}% | Trades: {status['trading']['total_trades']} | Win Rate: {status['trading']['win_rate']:.1f}% | Posiciones: {status['trading']['open_positions']}{ConsoleColors.RESET}"""
                print(status_line)
            else:
                status_update = f"""
{ConsoleColors.PERFORMANCE}📊 ESTADO DEL SISTEMA [{session_str}]
┌─────────────────────────────────────────────────────────────┐
│ 💰 Capital Total: ${status['capital']['total']:>12,.2f}                    │
│ 📈 Retorno Total: {status['performance']['total_return_pct']:>12.2f}%                   │
│ 📊 Retorno Diario: {status['performance']['daily_return_pct']:>11.2f}%                   │
│ 🔄 Trades Totales: {status['trading']['total_trades']:>11}                      │
│ 🎯 Win Rate: {status['trading']['win_rate']:>17.1f}%                   │
│ 📋 Posiciones Abiertas: {status['trading']['open_positions']:>9}                      │
│ ⚠️  Drawdown Actual: {status['risk']['current_drawdown_pct']:>10.2f}%                   │
└─────────────────────────────────────────────────────────────┘{ConsoleColors.RESET}"""
                print(status_update)
                
        except Exception as e:
            self.logger.error(f"Error mostrando actualización de estado: {e}")
            
    def _check_alerts(self):
        """Verifica y muestra alertas"""
        try:
            # Obtener alertas del performance reporter
            current_snapshot = self.performance_reporter.performance_history[-1] if self.performance_reporter.performance_history else None
            
            if not current_snapshot:
                return
                
            alerts = self.performance_reporter._generate_alerts(current_snapshot)
            
            for alert in alerts:
                alert_key = f"{alert['type']}_{alert['message']}"
                
                # Evitar alertas duplicadas
                if alert_key not in self.alerts_shown:
                    self._show_alert(alert)
                    self.alerts_shown.add(alert_key)
                    
                    # Limpiar alertas antiguas (mantener solo las últimas 50)
                    if len(self.alerts_shown) > 50:
                        self.alerts_shown.clear()
                        
        except Exception as e:
            self.logger.error(f"Error verificando alertas: {e}")
            
    def _show_alert(self, alert):
        """Muestra una alerta"""
        severity_colors = {
            'LOW': ConsoleColors.INFO,
            'MEDIUM': ConsoleColors.WARNING,
            'HIGH': ConsoleColors.ALERT
        }
        
        severity_icons = {
            'LOW': '💡',
            'MEDIUM': '⚠️',
            'HIGH': '🚨'
        }
        
        color = severity_colors.get(alert['severity'], ConsoleColors.WARNING)
        icon = severity_icons.get(alert['severity'], '⚠️')
        
        alert_msg = f"""{color}{icon} ALERTA [{alert['severity']}]: {alert['message']}{ConsoleColors.RESET}"""
        print(alert_msg)
        self.logger.warning(f"Alerta {alert['severity']}: {alert['message']}")
        
    def log_custom_event(self, event_type: str, message: str, level: LogLevel = LogLevel.INFO):
        """Registra un evento personalizado"""
        colors = {
            LogLevel.DEBUG: ConsoleColors.DEBUG,
            LogLevel.INFO: ConsoleColors.INFO,
            LogLevel.WARNING: ConsoleColors.WARNING,
            LogLevel.ERROR: ConsoleColors.ERROR,
            LogLevel.CRITICAL: ConsoleColors.ALERT,
            LogLevel.TRADE: ConsoleColors.TRADE_BUY,
            LogLevel.SIGNAL: ConsoleColors.SIGNAL,
            LogLevel.PERFORMANCE: ConsoleColors.PERFORMANCE,
            LogLevel.ALERT: ConsoleColors.ALERT
        }
        
        color = colors.get(level, ConsoleColors.INFO)
        formatted_msg = f"{color}[{event_type.upper()}] {message}{ConsoleColors.RESET}"
        
        print(formatted_msg)
        
        # También registrar en el logger
        log_levels = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.CRITICAL: logging.CRITICAL
        }
        
        log_level = log_levels.get(level, logging.INFO)
        self.logger.log(log_level, f"[{event_type}] {message}")
        
    def set_display_options(self, show_debug: bool = False, show_signals: bool = True, 
                          show_performance: bool = True, compact_mode: bool = False):
        """Configura opciones de display"""
        self.show_debug = show_debug
        self.show_signals = show_signals
        self.show_performance = show_performance
        self.compact_mode = compact_mode
        
        if show_debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
            
        self.logger.info(f"Opciones de display actualizadas: Debug={show_debug}, Signals={show_signals}, Performance={show_performance}, Compact={compact_mode}")
        
    def show_help(self):
        """Muestra ayuda del sistema de monitoreo"""
        help_text = f"""
{ConsoleColors.HEADER}
╔══════════════════════════════════════════════════════════════╗
║                    AYUDA DEL SISTEMA                         ║
╚══════════════════════════════════════════════════════════════╝
{ConsoleColors.RESET}

{ConsoleColors.INFO}🔧 COMANDOS DISPONIBLES:

• start_monitoring()     - Inicia el monitoreo
• stop_monitoring()      - Detiene el monitoreo
• set_display_options()  - Configura opciones de display
• log_custom_event()     - Registra evento personalizado
• show_help()           - Muestra esta ayuda

🎨 CÓDIGOS DE COLOR:
• {ConsoleColors.TRADE_BUY}Verde{ConsoleColors.RESET}    - Trades ganadores / Señales de compra
• {ConsoleColors.TRADE_SELL}Rojo{ConsoleColors.RESET}      - Trades perdedores / Señales de venta
• {ConsoleColors.WARNING}Amarillo{ConsoleColors.RESET}  - Advertencias
• {ConsoleColors.INFO}Azul{ConsoleColors.RESET}      - Información general
• {ConsoleColors.ALERT}Rojo/Amarillo{ConsoleColors.RESET} - Alertas críticas

📊 MÉTRICAS MOSTRADAS:
• Capital total y retornos
• Número de trades y win rate
• Posiciones abiertas
• Drawdown actual
• Alertas de riesgo

⚙️  CONFIGURACIÓN:
• Los logs se guardan en 'paper_trading.log'
• Actualización de estado cada 1 minuto
• Alertas automáticas por riesgo
{ConsoleColors.RESET}
"""
        print(help_text)
        
    def get_session_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de la sesión actual"""
        session_duration = datetime.now() - self.session_start_time
        status = self.performance_reporter.get_current_status()
        
        return {
            'session_start': self.session_start_time.isoformat(),
            'session_duration_seconds': session_duration.total_seconds(),
            'session_duration_str': str(session_duration).split('.')[0],
            'is_running': self.is_running,
            'total_trades': status.get('trading', {}).get('total_trades', 0),
            'current_capital': status.get('capital', {}).get('total', 0),
            'total_return_pct': status.get('performance', {}).get('total_return_pct', 0),
            'alerts_shown_count': len(self.alerts_shown),
            'display_options': {
                'show_debug': self.show_debug,
                'show_signals': self.show_signals,
                'show_performance': self.show_performance,
                'compact_mode': self.compact_mode
            }
        }

if __name__ == "__main__":
    # Ejemplo de uso
    from paper_trading_simulator import PaperTradingSimulator
    from performance_reporter import PerformanceReporter
    
    # Inicializar componentes
    simulator = PaperTradingSimulator()
    reporter = PerformanceReporter(simulator.trading_simulator, simulator.portfolio_manager)
    monitor = MonitoringSystem(simulator, reporter)
    
    # Mostrar ayuda
    monitor.show_help()
    
    # Configurar opciones
    monitor.set_display_options(show_debug=False, compact_mode=True)
    
    # Iniciar monitoreo
    monitor.start_monitoring()
    
    try:
        # Simular operación
        print(f"\n{ConsoleColors.INFO}Sistema ejecutándose... Presiona Ctrl+C para detener{ConsoleColors.RESET}")
        
        # Simular algunos eventos
        import time
        time.sleep(2)
        monitor.log_custom_event("SYSTEM", "Conexión a Binance establecida", LogLevel.INFO)
        
        time.sleep(3)
        monitor.log_custom_event("ANALYSIS", "Análisis técnico completado para BTCUSDT", LogLevel.INFO)
        
        time.sleep(5)
        monitor.log_custom_event("SIGNAL", "Señal de compra detectada en ETHUSDT", LogLevel.SIGNAL)
        
        # Mantener ejecutándose
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n{ConsoleColors.WARNING}Deteniendo sistema...{ConsoleColors.RESET}")
        monitor.stop_monitoring()
        print(f"{ConsoleColors.INFO}Sistema detenido correctamente{ConsoleColors.RESET}")