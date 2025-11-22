# /src/simple_paper_trading_dashboard.py
"""
Dashboard simplificado de Paper Trading para SICAR
Versión estable sin problemas de cuelgue
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

from paper_trading_system import PaperTradingEngine, OrderType
from binance_data_provider import BinanceDataProvider

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimplePaperTradingDashboard:
    """
    Dashboard simplificado de Paper Trading.
    Versión estable con funcionalidades básicas.
    """
    
    def __init__(self, initial_capital: float = 10000.0):
        """Inicializa el dashboard simplificado."""
        logger.info("🚀 Iniciando Simple Paper Trading Dashboard")
        
        # Componentes principales
        self.data_provider = BinanceDataProvider()
        self.paper_engine = PaperTradingEngine(
            initial_capital=initial_capital,
            commission_rate=0.001,
            slippage_factor=0.0005
        )
        
        # Variables de control
        self.is_running = False
        self.monitoring_thread = None
        
        # Símbolos para trading
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'DOTUSDT', 'LINKUSDT', 'UNIUSDT', 'AVAXUSDT', 'ATOMUSDT'
        ]
        
        # Crear interfaz
        self.setup_ui()
        
        logger.info("✅ Simple Paper Trading Dashboard inicializado")
    
    def setup_ui(self):
        """Configura la interfaz de usuario simplificada."""
        # Ventana principal
        self.root = tk.Tk()
        self.root.title("SICAR - Simple Paper Trading Dashboard")
        self.root.geometry("800x600")
        self.root.configure(bg='#1e1e1e')
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title_label = ttk.Label(
            main_frame, 
            text="🎯 SICAR Paper Trading Dashboard",
            font=('Arial', 16, 'bold')
        )
        title_label.pack(pady=(0, 20))
        
        # Panel de información
        self.setup_info_panel(main_frame)
        
        # Panel de trading
        self.setup_trading_panel(main_frame)
        
        # Panel de control
        self.setup_control_panel(main_frame)
        
        # Actualizar información inicial
        self.update_display()
    
    def setup_info_panel(self, parent):
        """Configura el panel de información."""
        info_frame = ttk.LabelFrame(parent, text="📊 Información del Portfolio", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Variables de información
        self.capital_var = tk.StringVar(value="$10,000.00")
        self.pnl_var = tk.StringVar(value="$0.00")
        self.positions_var = tk.StringVar(value="0")
        self.trades_var = tk.StringVar(value="0")
        
        # Labels de información
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X)
        
        ttk.Label(info_grid, text="💰 Capital:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(info_grid, textvariable=self.capital_var, font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(info_grid, text="📈 PnL:").grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        ttk.Label(info_grid, textvariable=self.pnl_var, font=('Arial', 10, 'bold')).grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(info_grid, text="📋 Posiciones:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(info_grid, textvariable=self.positions_var).grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(info_grid, text="🔄 Trades:").grid(row=1, column=2, sticky=tk.W, padx=(20, 10))
        ttk.Label(info_grid, textvariable=self.trades_var).grid(row=1, column=3, sticky=tk.W)
    
    def setup_trading_panel(self, parent):
        """Configura el panel de trading manual."""
        trading_frame = ttk.LabelFrame(parent, text="🎮 Trading Manual", padding=10)
        trading_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Selección de símbolo
        symbol_frame = ttk.Frame(trading_frame)
        symbol_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(symbol_frame, text="Símbolo:").pack(side=tk.LEFT)
        self.symbol_var = tk.StringVar(value=self.symbols[0])
        symbol_combo = ttk.Combobox(symbol_frame, textvariable=self.symbol_var, values=self.symbols, width=15)
        symbol_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        # Cantidad
        ttk.Label(symbol_frame, text="Cantidad:").pack(side=tk.LEFT)
        self.quantity_var = tk.StringVar(value="0.1")
        quantity_entry = ttk.Entry(symbol_frame, textvariable=self.quantity_var, width=10)
        quantity_entry.pack(side=tk.LEFT, padx=(5, 20))
        
        # Botones de trading
        button_frame = ttk.Frame(trading_frame)
        button_frame.pack(fill=tk.X)
        
        buy_button = ttk.Button(
            button_frame, 
            text="🟢 COMPRAR", 
            command=lambda: self.execute_manual_trade('buy')
        )
        buy_button.pack(side=tk.LEFT, padx=(0, 10))
        
        sell_button = ttk.Button(
            button_frame, 
            text="🔴 VENDER", 
            command=lambda: self.execute_manual_trade('sell')
        )
        sell_button.pack(side=tk.LEFT)
    
    def setup_control_panel(self, parent):
        """Configura el panel de control."""
        control_frame = ttk.LabelFrame(parent, text="⚙️ Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Botones de control
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(
            button_frame, 
            text="▶️ INICIAR MONITOREO", 
            command=self.start_monitoring
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(
            button_frame, 
            text="⏹️ DETENER", 
            command=self.stop_monitoring,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        refresh_button = ttk.Button(
            button_frame, 
            text="🔄 ACTUALIZAR", 
            command=self.update_display
        )
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Log area
        log_frame = ttk.LabelFrame(parent, text="📝 Log de Actividad", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text widget para logs
        self.log_text = tk.Text(log_frame, height=10, bg='#2d2d2d', fg='white', font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Mensaje inicial
        self.add_log("🎯 Dashboard inicializado - Listo para trading")
    
    def execute_manual_trade(self, side: str):
        """Ejecuta un trade manual."""
        try:
            symbol = self.symbol_var.get()
            quantity = float(self.quantity_var.get())
            
            if quantity <= 0:
                messagebox.showerror("Error", "La cantidad debe ser mayor a 0")
                return
            
            # Obtener precio actual
            ticker = self.data_provider.get_ticker_price(symbol)
            if not ticker:
                messagebox.showerror("Error", f"No se pudo obtener precio para {symbol}")
                return
            
            price = float(ticker['price'])
            
            # Ejecutar orden
            order_id = self.paper_engine.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=price
            )
            
            # Procesar datos de mercado
            market_data = {symbol: price}
            self.paper_engine.process_market_data(market_data)
            
            # Log del trade
            self.add_log(f"✅ {side.upper()} {quantity} {symbol} @ ${price:,.2f}")
            
            # Actualizar display
            self.update_display()
            
        except ValueError:
            messagebox.showerror("Error", "Cantidad inválida")
        except Exception as e:
            messagebox.showerror("Error", f"Error ejecutando trade: {e}")
            logger.error(f"Error en trade manual: {e}")
    
    def start_monitoring(self):
        """Inicia el monitoreo automático."""
        if not self.is_running:
            self.is_running = True
            self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            self.add_log("🚀 Monitoreo automático iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo automático."""
        if self.is_running:
            self.is_running = False
            
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            self.add_log("⏹️ Monitoreo automático detenido")
    
    def monitoring_loop(self):
        """Loop principal de monitoreo."""
        while self.is_running:
            try:
                # Obtener datos de mercado para algunos símbolos
                market_data = {}
                for symbol in self.symbols[:5]:  # Solo primeros 5 para no sobrecargar
                    ticker = self.data_provider.get_ticker_price(symbol)
                    if ticker:
                        market_data[symbol] = float(ticker['price'])
                
                if market_data:
                    # Procesar datos
                    self.paper_engine.process_market_data(market_data)
                    
                    # Actualizar display en el hilo principal
                    self.root.after(0, self.update_display)
                
                # Esperar antes del siguiente ciclo
                time.sleep(30)  # 30 segundos entre actualizaciones
                
            except Exception as e:
                logger.error(f"Error en monitoring loop: {e}")
                time.sleep(5)
    
    def update_display(self):
        """Actualiza la información mostrada."""
        try:
            summary = self.paper_engine.get_portfolio_summary()
            
            # Actualizar variables
            self.capital_var.set(f"${summary['current_capital']:,.2f}")
            self.pnl_var.set(f"${summary['total_pnl']:,.2f}")
            self.positions_var.set(str(summary['open_positions']))
            self.trades_var.set(str(summary['total_trades']))
            
        except Exception as e:
            logger.error(f"Error actualizando display: {e}")
    
    def add_log(self, message: str):
        """Añade un mensaje al log."""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            self.log_text.insert(tk.END, log_message)
            self.log_text.see(tk.END)
            
            # Limitar líneas del log
            lines = self.log_text.get("1.0", tk.END).split('\n')
            if len(lines) > 100:
                self.log_text.delete("1.0", "2.0")
                
        except Exception as e:
            logger.error(f"Error añadiendo log: {e}")
    
    def run(self):
        """Ejecuta el dashboard."""
        try:
            # Configurar cierre de ventana
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            logger.info("🎯 Iniciando interfaz gráfica...")
            
            # Iniciar loop principal
            self.root.mainloop()
            
        except Exception as e:
            logger.error(f"Error ejecutando dashboard: {e}")
    
    def on_closing(self):
        """Maneja el cierre de la aplicación."""
        if self.is_running:
            self.stop_monitoring()
        
        logger.info("👋 Cerrando dashboard...")
        self.root.destroy()

def main():
    """Función principal."""
    try:
        logger.info("🚀 Iniciando Simple Paper Trading Dashboard")
        
        # Crear y ejecutar dashboard
        dashboard = SimplePaperTradingDashboard(initial_capital=10000.0)
        dashboard.run()
        
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        messagebox.showerror("Error Crítico", f"Error iniciando dashboard: {e}")

if __name__ == "__main__":
    main()