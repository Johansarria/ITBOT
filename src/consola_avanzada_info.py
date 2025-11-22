#!/usr/bin/env python3
"""
Sistema de Información Avanzada por Consola
Proporciona visualización mejorada y detallada del estado del sistema
"""

import json
import os
import time
import psutil
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import logging
from dataclasses import dataclass
import subprocess

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | CONSOLA_INFO | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('consola_avanzada.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_status: bool
    active_processes: int
    timestamp: datetime

@dataclass
class TradingStatus:
    session_active: bool
    current_capital: float
    initial_capital: float
    total_trades: int
    open_positions: int
    auto_trading: bool
    last_update: datetime

class AdvancedConsoleInfo:
    def __init__(self):
        self.running = False
        self.refresh_interval = 5  # segundos
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        
        # Archivos de estado
        self.session_file = 'data/paper_trading_session.json'
        self.config_file = 'sicar_config.json'
        self.signals_file = 'filtros_ia_signals.json'
        
        # Historial para gráficos ASCII
        self.price_history = {symbol: [] for symbol in self.symbols}
        self.system_history = []
        
    def clear_screen(self):
        """Limpiar pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_system_status(self) -> SystemStatus:
        """Obtener estado del sistema"""
        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Verificar conectividad de red
            try:
                requests.get('https://api.binance.com/api/v3/ping', timeout=5)
                network_status = True
            except:
                network_status = False
            
            active_processes = len([p for p in psutil.process_iter() if p.is_running()])
            
            return SystemStatus(
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                network_status=network_status,
                active_processes=active_processes,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Error obteniendo estado del sistema: {e}")
            return SystemStatus(0, 0, 0, False, 0, datetime.now())
    
    def get_trading_status(self) -> Optional[TradingStatus]:
        """Obtener estado del trading"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                
                return TradingStatus(
                    session_active=session_data.get('session_active', False),
                    current_capital=session_data.get('current_capital', 0),
                    initial_capital=session_data.get('initial_capital', 0),
                    total_trades=session_data.get('total_trades', 0),
                    open_positions=len(session_data.get('positions', [])),
                    auto_trading=session_data.get('auto_trading', False),
                    last_update=datetime.fromisoformat(session_data.get('last_sync', datetime.now().isoformat()))
                )
            return None
        except Exception as e:
            logger.error(f"Error obteniendo estado del trading: {e}")
            return None
    
    def get_market_prices(self) -> Dict[str, Dict]:
        """Obtener precios actuales del mercado"""
        prices = {}
        try:
            for symbol in self.symbols:
                try:
                    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
                    response = requests.get(url, timeout=5)
                    data = response.json()
                    
                    prices[symbol] = {
                        'price': float(data['lastPrice']),
                        'change': float(data['priceChangePercent']),
                        'volume': float(data['quoteVolume']),
                        'high': float(data['highPrice']),
                        'low': float(data['lowPrice'])
                    }
                    
                    # Actualizar historial para gráfico
                    self.price_history[symbol].append(prices[symbol]['price'])
                    if len(self.price_history[symbol]) > 20:
                        self.price_history[symbol] = self.price_history[symbol][-20:]
                        
                except Exception as e:
                    logger.error(f"Error obteniendo precio de {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error general obteniendo precios: {e}")
        
        return prices
    
    def get_ai_signals(self) -> List[Dict]:
        """Obtener señales de IA"""
        try:
            if os.path.exists(self.signals_file):
                with open(self.signals_file, 'r') as f:
                    signals = json.load(f)
                
                # Filtrar señales recientes (última hora)
                recent_signals = []
                current_time = datetime.now()
                
                for signal in signals:
                    signal_time = datetime.fromisoformat(signal['timestamp'])
                    if (current_time - signal_time).total_seconds() < 3600:
                        recent_signals.append(signal)
                
                return recent_signals
            return []
        except Exception as e:
            logger.error(f"Error obteniendo señales de IA: {e}")
            return []
    
    def create_ascii_chart(self, data: List[float], width: int = 30, height: int = 8) -> List[str]:
        """Crear gráfico ASCII simple"""
        if not data or len(data) < 2:
            return [" " * width for _ in range(height)]
        
        # Normalizar datos
        min_val = min(data)
        max_val = max(data)
        
        if max_val == min_val:
            return [" " * width for _ in range(height)]
        
        chart = []
        for i in range(height):
            line = ""
            for j in range(min(width, len(data))):
                # Calcular posición normalizada
                normalized = (data[j] - min_val) / (max_val - min_val)
                chart_pos = int(normalized * (height - 1))
                
                if chart_pos == (height - 1 - i):
                    line += "█"
                elif chart_pos > (height - 1 - i):
                    line += "▄"
                else:
                    line += " "
            chart.append(line)
        
        return chart
    
    def format_number(self, num: float, decimals: int = 2) -> str:
        """Formatear números con separadores"""
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        else:
            return f"{num:.{decimals}f}"
    
    def get_progress_bar(self, value: float, max_value: float, width: int = 20) -> str:
        """Crear barra de progreso"""
        if max_value == 0:
            return "█" * width
        
        filled = int((value / max_value) * width)
        bar = "█" * filled + "░" * (width - filled)
        return bar
    
    def display_header(self):
        """Mostrar encabezado"""
        now = datetime.now()
        print("╔" + "═" * 118 + "╗")
        print(f"║ 🚀 SICAR - SISTEMA INTEGRAL DE CRIPTOMONEDAS Y ANÁLISIS ROBUSTO {now.strftime('%Y-%m-%d %H:%M:%S')} ║")
        print("╚" + "═" * 118 + "╝")
    
    def display_system_status(self, system_status: SystemStatus):
        """Mostrar estado del sistema"""
        print("\n┌─ 💻 ESTADO DEL SISTEMA ─────────────────────────────────────────────────────────┐")
        
        # CPU
        cpu_bar = self.get_progress_bar(system_status.cpu_usage, 100, 15)
        cpu_color = "🟢" if system_status.cpu_usage < 50 else "🟡" if system_status.cpu_usage < 80 else "🔴"
        
        # Memoria
        mem_bar = self.get_progress_bar(system_status.memory_usage, 100, 15)
        mem_color = "🟢" if system_status.memory_usage < 70 else "🟡" if system_status.memory_usage < 90 else "🔴"
        
        # Red
        net_status = "🟢 CONECTADO" if system_status.network_status else "🔴 DESCONECTADO"
        
        print(f"│ {cpu_color} CPU: {system_status.cpu_usage:5.1f}% [{cpu_bar}] │ {mem_color} RAM: {system_status.memory_usage:5.1f}% [{mem_bar}] │ 🌐 {net_status} │")
        print(f"│ 💾 Disco: {system_status.disk_usage:5.1f}% │ 🔄 Procesos: {system_status.active_processes:4d} │ ⏰ {system_status.timestamp.strftime('%H:%M:%S')} │")
        print("└─────────────────────────────────────────────────────────────────────────────────┘")
    
    def display_trading_status(self, trading_status: Optional[TradingStatus]):
        """Mostrar estado del trading"""
        print("\n┌─ 💰 ESTADO DEL PAPER TRADING ───────────────────────────────────────────────────┐")
        
        if trading_status:
            # Calcular P&L
            pnl = trading_status.current_capital - trading_status.initial_capital
            pnl_percent = (pnl / trading_status.initial_capital * 100) if trading_status.initial_capital > 0 else 0
            
            # Estado de la sesión
            session_emoji = "🟢" if trading_status.session_active else "🔴"
            auto_emoji = "🤖" if trading_status.auto_trading else "👤"
            
            # P&L color
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            print(f"│ {session_emoji} Sesión: {'ACTIVA' if trading_status.session_active else 'INACTIVA':8} │ {auto_emoji} Modo: {'AUTO' if trading_status.auto_trading else 'MANUAL':6} │")
            print(f"│ 💵 Capital Inicial: ${trading_status.initial_capital:8.2f} │ 💰 Capital Actual: ${trading_status.current_capital:8.2f} │")
            print(f"│ {pnl_emoji} P&L: ${pnl:+8.2f} ({pnl_percent:+5.1f}%) │ 📊 Trades: {trading_status.total_trades:4d} │ 📈 Posiciones: {trading_status.open_positions:2d} │")
            print(f"│ ⏰ Última actualización: {trading_status.last_update.strftime('%H:%M:%S')} │")
        else:
            print("│ ❌ No se pudo cargar el estado del paper trading │")
        
        print("└─────────────────────────────────────────────────────────────────────────────────┘")
    
    def display_market_overview(self, prices: Dict[str, Dict]):
        """Mostrar resumen del mercado"""
        print("\n┌─ 📈 RESUMEN DEL MERCADO ────────────────────────────────────────────────────────┐")
        
        if prices:
            print("│ Símbolo    │ Precio      │ Cambio 24h │ Volumen    │ Máx/Mín 24h      │ Gráfico │")
            print("├────────────┼─────────────┼────────────┼────────────┼──────────────────┼─────────┤")
            
            for symbol, data in prices.items():
                # Formatear datos
                price_str = f"${data['price']:>9.2f}" if data['price'] < 1000 else f"${self.format_number(data['price']):>9}"
                change_emoji = "🟢" if data['change'] >= 0 else "🔴"
                change_str = f"{change_emoji}{data['change']:+6.2f}%"
                volume_str = f"{self.format_number(data['volume']):>9}"
                range_str = f"${self.format_number(data['high'])}/{self.format_number(data['low'])}"
                
                # Mini gráfico
                if symbol in self.price_history and len(self.price_history[symbol]) > 1:
                    chart = self.create_ascii_chart(self.price_history[symbol][-10:], 7, 1)
                    mini_chart = chart[0] if chart else " " * 7
                else:
                    mini_chart = " " * 7
                
                print(f"│ {symbol:10} │ {price_str} │ {change_str:10} │ {volume_str:10} │ {range_str:16} │ {mini_chart} │")
        else:
            print("│ ❌ No se pudieron cargar los datos del mercado │")
        
        print("└─────────────────────────────────────────────────────────────────────────────────┘")
    
    def display_ai_signals(self, signals: List[Dict]):
        """Mostrar señales de IA"""
        print("\n┌─ 🧠 SEÑALES DE IA RECIENTES ────────────────────────────────────────────────────┐")
        
        if signals:
            print("│ Símbolo  │ Señal │ Confianza │ Riesgo │ Hora  │ Puntuaciones (T/S/V)     │")
            print("├──────────┼───────┼───────────┼────────┼───────┼──────────────────────────┤")
            
            for signal in signals[-5:]:  # Últimas 5 señales
                # Emojis según tipo de señal
                signal_emoji = "🟢" if signal['signal_type'] == 'BUY' else "🔴" if signal['signal_type'] == 'SELL' else "🟡"
                
                # Color de riesgo
                risk_emoji = "🟢" if signal['risk_level'] == 'LOW' else "🟡" if signal['risk_level'] == 'MEDIUM' else "🔴"
                
                # Formatear tiempo
                signal_time = datetime.fromisoformat(signal['timestamp'])
                time_str = signal_time.strftime('%H:%M')
                
                # Puntuaciones
                scores = f"{signal['technical_score']:4.1f}/{signal['sentiment_score']:4.1f}/{signal['volume_score']:4.1f}"
                
                print(f"│ {signal['symbol']:8} │ {signal_emoji}{signal['signal_type']:4} │ {signal['confidence']:7.1f}% │ {risk_emoji}{signal['risk_level']:4} │ {time_str} │ {scores:24} │")
        else:
            print("│ ℹ️ No hay señales de IA recientes │")
        
        print("└─────────────────────────────────────────────────────────────────────────────────┘")
    
    def display_active_systems(self):
        """Mostrar sistemas activos"""
        print("\n┌─ ⚙️ SISTEMAS ACTIVOS ───────────────────────────────────────────────────────────┐")
        
        # Lista de procesos Python relacionados con SICAR
        sicar_processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python.exe' and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if any(keyword in cmdline.lower() for keyword in ['sicar', 'analisis', 'trading', 'mercado', 'ia_continua']):
                            script_name = os.path.basename(proc.info['cmdline'][-1]) if proc.info['cmdline'] else 'Unknown'
                            sicar_processes.append({
                                'pid': proc.info['pid'],
                                'script': script_name,
                                'status': '🟢 ACTIVO'
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error obteniendo procesos: {e}")
        
        if sicar_processes:
            print("│ PID   │ Script                           │ Estado     │")
            print("├───────┼──────────────────────────────────┼────────────┤")
            for proc in sicar_processes[:8]:  # Máximo 8 procesos
                print(f"│ {proc['pid']:5d} │ {proc['script']:32} │ {proc['status']:10} │")
        else:
            print("│ ℹ️ No se detectaron sistemas SICAR activos │")
        
        print("└─────────────────────────────────────────────────────────────────────────────────┘")
    
    def display_footer(self):
        """Mostrar pie de página"""
        print(f"\n🔄 Actualización automática cada {self.refresh_interval} segundos | Presiona Ctrl+C para salir")
        print("─" * 120)
    
    def run_continuous_display(self):
        """Ejecutar visualización continua"""
        logger.info("🖥️ Iniciando consola de información avanzada...")
        self.running = True
        
        while self.running:
            try:
                # Limpiar pantalla
                self.clear_screen()
                
                # Obtener datos
                system_status = self.get_system_status()
                trading_status = self.get_trading_status()
                market_prices = self.get_market_prices()
                ai_signals = self.get_ai_signals()
                
                # Mostrar información
                self.display_header()
                self.display_system_status(system_status)
                self.display_trading_status(trading_status)
                self.display_market_overview(market_prices)
                self.display_ai_signals(ai_signals)
                self.display_active_systems()
                self.display_footer()
                
                # Esperar antes de la siguiente actualización
                time.sleep(self.refresh_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Deteniendo consola de información...")
                break
            except Exception as e:
                logger.error(f"❌ Error en visualización: {e}")
                time.sleep(5)
        
        self.running = False

def main():
    """Función principal"""
    console_info = AdvancedConsoleInfo()
    
    try:
        console_info.run_continuous_display()
    except KeyboardInterrupt:
        print("\n🛑 Consola detenida por el usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())