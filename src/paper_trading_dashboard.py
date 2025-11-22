# /src/paper_trading_dashboard.py
"""
Dashboard de Paper Trading para SICAR
Integra el monitor de breakouts con simulación de trading.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from first_candle_breakout import FirstCandleBreakoutDetector
from paper_trading_system import PaperTradingEngine, OrderType, PositionSide
from binance_data_provider import BinanceDataProvider

logger = logging.getLogger(__name__)

class PaperTradingDashboard:
    """
    Dashboard integrado para paper trading con detección de breakouts.
    
    Características:
    - Monitor en tiempo real de breakouts
    - Ejecución automática de paper trades
    - Visualización de portfolio virtual
    - Gestión manual de órdenes
    - Reportes de performance
    """
    
    def __init__(self, initial_capital: float = 10000.0):
        """Inicializa el dashboard de paper trading."""
        self.root = tk.Tk()
        self.root.title("SICAR - Paper Trading Dashboard")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e1e')
        
        # Componentes principales
        self.data_provider = BinanceDataProvider()
        self.breakout_detector = FirstCandleBreakoutDetector()
        self.paper_engine = PaperTradingEngine(initial_capital)
        
        # Variables de control
        self.is_running = False
        self.auto_trading_enabled = tk.BooleanVar(value=False)
        self.selected_symbols = tk.StringVar()
        
        # Configuración de auto-trading
        self.auto_trading_config = {
            'position_size_pct': 0.05,  # 5% del capital por trade
            'stop_loss_pct': 0.02,      # 2% stop loss
            'take_profit_pct': 0.04,    # 4% take profit
            'max_positions': 3          # Máximo 3 posiciones simultáneas
        }
        
        # Datos en tiempo real
        self.current_prices = {}
        self.breakout_signals = {}
        self.last_update = None
        
        self.setup_ui()
        self.setup_logging()
        
        logger.info("🎯 Paper Trading Dashboard inicializado")
    
    def setup_ui(self):
        """Configura la interfaz de usuario."""
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#1e1e1e', foreground='white')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), background='#2d2d2d', foreground='white')
        style.configure('Data.TLabel', font=('Arial', 10), background='#2d2d2d', foreground='#00ff00')
        
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title_label = ttk.Label(main_frame, text="🎯 SICAR Paper Trading System", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Frame superior - Controles
        control_frame = ttk.LabelFrame(main_frame, text="Controles", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.setup_control_panel(control_frame)
        
        # Frame medio - Información en tiempo real
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.BOTH, expand=True)
        
        # Panel izquierdo - Portfolio y Posiciones
        left_panel = ttk.LabelFrame(info_frame, text="Portfolio Virtual", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.setup_portfolio_panel(left_panel)
        
        # Panel derecho - Breakouts y Órdenes
        right_panel = ttk.LabelFrame(info_frame, text="Breakouts y Órdenes", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.setup_trading_panel(right_panel)
        
        # Frame inferior - Log
        log_frame = ttk.LabelFrame(main_frame, text="Log de Actividad", padding=10)
        log_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.setup_log_panel(log_frame)
    
    def setup_control_panel(self, parent):
        """Configura el panel de controles."""
        # Botones principales
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        self.start_button = ttk.Button(button_frame, text="▶ Iniciar", command=self.start_monitoring)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="⏹ Detener", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Auto-trading toggle
        auto_trading_check = ttk.Checkbutton(
            button_frame, 
            text="Auto-Trading Activado", 
            variable=self.auto_trading_enabled,
            command=self.toggle_auto_trading
        )
        auto_trading_check.pack(side=tk.LEFT, padx=(20, 10))
        
        # Configuración rápida
        config_frame = ttk.Frame(parent)
        config_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(config_frame, text="Tamaño Posición:").pack(side=tk.LEFT)
        self.position_size_var = tk.StringVar(value="5.0")
        position_size_entry = ttk.Entry(config_frame, textvariable=self.position_size_var, width=8)
        position_size_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(config_frame, text="Stop Loss %:").pack(side=tk.LEFT)
        self.stop_loss_var = tk.StringVar(value="2.0")
        stop_loss_entry = ttk.Entry(config_frame, textvariable=self.stop_loss_var, width=8)
        stop_loss_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        ttk.Label(config_frame, text="Take Profit %:").pack(side=tk.LEFT)
        self.take_profit_var = tk.StringVar(value="4.0")
        take_profit_entry = ttk.Entry(config_frame, textvariable=self.take_profit_var, width=8)
        take_profit_entry.pack(side=tk.LEFT, padx=(5, 15))
        
        # Botón de configuración
        config_button = ttk.Button(config_frame, text="⚙ Configurar", command=self.open_config_dialog)
        config_button.pack(side=tk.RIGHT)
    
    def setup_portfolio_panel(self, parent):
        """Configura el panel del portfolio."""
        # Resumen del portfolio
        summary_frame = ttk.Frame(parent)
        summary_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.portfolio_labels = {}
        portfolio_metrics = [
            ('Capital Inicial:', 'initial_capital'),
            ('Capital Actual:', 'current_capital'),
            ('Valor Portfolio:', 'total_portfolio_value'),
            ('PnL Total:', 'total_pnl'),
            ('Retorno %:', 'total_return_pct'),
            ('Trades:', 'total_trades'),
            ('Win Rate:', 'win_rate'),
            ('Max Drawdown:', 'max_drawdown')
        ]
        
        for i, (label_text, key) in enumerate(portfolio_metrics):
            row = i // 2
            col = i % 2
            
            label_frame = ttk.Frame(summary_frame)
            label_frame.grid(row=row, column=col, sticky='ew', padx=5, pady=2)
            
            ttk.Label(label_frame, text=label_text, font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
            value_label = ttk.Label(label_frame, text="$0.00", font=('Arial', 9), foreground='#00ff00')
            value_label.pack(side=tk.RIGHT)
            
            self.portfolio_labels[key] = value_label
        
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.columnconfigure(1, weight=1)
        
        # Tabla de posiciones
        positions_frame = ttk.LabelFrame(parent, text="Posiciones Abiertas", padding=5)
        positions_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Treeview para posiciones
        columns = ('Symbol', 'Side', 'Size', 'Entry', 'Current', 'PnL', 'PnL%')
        self.positions_tree = ttk.Treeview(positions_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=80, anchor='center')
        
        # Scrollbar para posiciones
        positions_scrollbar = ttk.Scrollbar(positions_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=positions_scrollbar.set)
        
        self.positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        positions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_trading_panel(self, parent):
        """Configura el panel de trading."""
        # Breakouts detectados
        breakouts_frame = ttk.LabelFrame(parent, text="Breakouts Detectados", padding=5)
        breakouts_frame.pack(fill=tk.X, pady=(0, 10))
        
        columns = ('Symbol', 'Tipo', 'Precio', 'Volumen', 'Tiempo')
        self.breakouts_tree = ttk.Treeview(breakouts_frame, columns=columns, show='headings', height=6)
        
        for col in columns:
            self.breakouts_tree.heading(col, text=col)
            self.breakouts_tree.column(col, width=80, anchor='center')
        
        breakouts_scrollbar = ttk.Scrollbar(breakouts_frame, orient=tk.VERTICAL, command=self.breakouts_tree.yview)
        self.breakouts_tree.configure(yscrollcommand=breakouts_scrollbar.set)
        
        self.breakouts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        breakouts_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Panel de órdenes manuales
        manual_frame = ttk.LabelFrame(parent, text="Trading Manual", padding=5)
        manual_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Selección de símbolo
        symbol_frame = ttk.Frame(manual_frame)
        symbol_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(symbol_frame, text="Símbolo:").pack(side=tk.LEFT)
        self.manual_symbol_var = tk.StringVar()
        symbol_combo = ttk.Combobox(symbol_frame, textvariable=self.manual_symbol_var, width=12)
        symbol_combo['values'] = self.breakout_detector.trading_symbols
        symbol_combo.pack(side=tk.LEFT, padx=(5, 10))
        
        # Cantidad
        ttk.Label(symbol_frame, text="Cantidad:").pack(side=tk.LEFT)
        self.manual_quantity_var = tk.StringVar(value="100.0")
        quantity_entry = ttk.Entry(symbol_frame, textvariable=self.manual_quantity_var, width=10)
        quantity_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        # Botones de trading manual
        button_frame = ttk.Frame(manual_frame)
        button_frame.pack(fill=tk.X, pady=(5, 0))
        
        buy_button = ttk.Button(button_frame, text="📈 Comprar", command=lambda: self.manual_trade('buy'))
        buy_button.pack(side=tk.LEFT, padx=(0, 5))
        
        sell_button = ttk.Button(button_frame, text="📉 Vender", command=lambda: self.manual_trade('sell'))
        sell_button.pack(side=tk.LEFT, padx=(0, 5))
        
        close_all_button = ttk.Button(button_frame, text="🔄 Cerrar Todo", command=self.close_all_positions)
        close_all_button.pack(side=tk.RIGHT)
    
    def setup_log_panel(self, parent):
        """Configura el panel de log."""
        log_text_frame = ttk.Frame(parent)
        log_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_text_frame, height=8, bg='#2d2d2d', fg='#ffffff', font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_logging(self):
        """Configura el logging para mostrar en el dashboard."""
        class DashboardLogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
            
            def emit(self, record):
                msg = self.format(record)
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                def append():
                    self.text_widget.insert(tk.END, f"[{timestamp}] {msg}\n")
                    self.text_widget.see(tk.END)
                    
                    # Limitar líneas del log
                    lines = self.text_widget.get("1.0", tk.END).split('\n')
                    if len(lines) > 100:
                        self.text_widget.delete("1.0", "10.0")
                
                self.text_widget.after(0, append)
        
        handler = DashboardLogHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    def start_monitoring(self):
        """Inicia el monitoreo de breakouts y paper trading."""
        if not self.is_running:
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
            # Iniciar thread de monitoreo
            self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            logger.info("🚀 Monitoreo iniciado")
    
    def stop_monitoring(self):
        """Detiene el monitoreo."""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        logger.info("⏹ Monitoreo detenido")
    
    def monitoring_loop(self):
        """Loop principal de monitoreo."""
        while self.is_running:
            try:
                # Obtener datos de mercado
                self.update_market_data()
                
                # Procesar datos en el paper engine
                self.paper_engine.process_market_data(self.current_prices)
                
                # Detectar breakouts
                self.detect_breakouts()
                
                # Ejecutar auto-trading si está habilitado
                if self.auto_trading_enabled.get():
                    self.execute_auto_trading()
                
                # Actualizar UI
                self.root.after(0, self.update_ui)
                
                # Esperar antes del siguiente ciclo
                time.sleep(5)  # 5 segundos entre actualizaciones
                
            except Exception as e:
                logger.error(f"Error en monitoring loop: {e}")
                time.sleep(10)
    
    def update_market_data(self):
        """Actualiza los datos de mercado."""
        try:
            new_prices = {}
            for symbol in self.breakout_detector.symbols:
                try:
                    ticker = self.data_provider.get_ticker_price(symbol)
                    if ticker and 'price' in ticker:
                        new_prices[symbol] = float(ticker['price'])
                except Exception as e:
                    logger.warning(f"Error obteniendo precio de {symbol}: {e}")
            
            self.current_prices.update(new_prices)
            self.last_update = datetime.now()
            
        except Exception as e:
            logger.error(f"Error actualizando datos de mercado: {e}")
    
    def detect_breakouts(self):
        """Detecta breakouts usando el detector existente."""
        try:
            # Obtener datos históricos recientes para análisis
            for symbol in self.breakout_detector.symbols[:5]:  # Limitar para performance
                try:
                    # Obtener datos de 1h para análisis
                    data_1h = self.data_provider.get_historical_data(symbol, '1h', limit=100)
                    if data_1h is not None and len(data_1h) > 0:
                        
                        # Detectar breakout
                        breakout_result = self.breakout_detector.detect_breakout(data_1h, symbol)
                        
                        if breakout_result and breakout_result.get('breakout_detected'):
                            # Nuevo breakout detectado
                            self.breakout_signals[symbol] = {
                                'type': breakout_result.get('breakout_type', 'unknown'),
                                'price': self.current_prices.get(symbol, 0),
                                'volume': breakout_result.get('volume_ratio', 0),
                                'timestamp': datetime.now(),
                                'confidence': breakout_result.get('confidence', 0)
                            }
                            
                            logger.info(f"🔥 Breakout detectado en {symbol}: {breakout_result.get('breakout_type')}")
                
                except Exception as e:
                    logger.warning(f"Error detectando breakout en {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Error en detección de breakouts: {e}")
    
    def execute_auto_trading(self):
        """Ejecuta trades automáticos basados en breakouts."""
        try:
            # Verificar si hay nuevos breakouts para tradear
            for symbol, signal in self.breakout_signals.items():
                # Verificar si ya tenemos posición en este símbolo
                if symbol in self.paper_engine.positions:
                    continue
                
                # Verificar límite de posiciones
                if len(self.paper_engine.positions) >= self.auto_trading_config['max_positions']:
                    continue
                
                # Calcular tamaño de posición
                portfolio_value = self.paper_engine.get_portfolio_summary()['total_portfolio_value']
                position_value = portfolio_value * (float(self.position_size_var.get()) / 100)
                
                current_price = self.current_prices.get(symbol, 0)
                if current_price > 0:
                    quantity = position_value / current_price
                    
                    # Colocar orden de compra
                    order_id = self.paper_engine.place_order(
                        symbol=symbol,
                        side='buy',
                        order_type=OrderType.MARKET,
                        quantity=quantity,
                        price=current_price
                    )
                    
                    logger.info(f"🤖 Auto-trade ejecutado: {symbol} - ${position_value:.2f}")
                    
                    # Configurar stop loss y take profit
                    stop_loss_pct = float(self.stop_loss_var.get()) / 100
                    take_profit_pct = float(self.take_profit_var.get()) / 100
                    
                    # Estas órdenes se procesarán en el siguiente ciclo
                    # cuando la posición esté abierta
            
        except Exception as e:
            logger.error(f"Error en auto-trading: {e}")
    
    def manual_trade(self, side: str):
        """Ejecuta un trade manual."""
        try:
            symbol = self.manual_symbol_var.get()
            quantity = float(self.manual_quantity_var.get())
            
            if not symbol:
                messagebox.showwarning("Error", "Selecciona un símbolo")
                return
            
            current_price = self.current_prices.get(symbol, 0)
            if current_price == 0:
                messagebox.showwarning("Error", f"No hay precio disponible para {symbol}")
                return
            
            order_id = self.paper_engine.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=current_price
            )
            
            logger.info(f"📝 Trade manual: {side.upper()} {quantity} {symbol} @ ${current_price:.2f}")
            
        except ValueError:
            messagebox.showerror("Error", "Cantidad inválida")
        except Exception as e:
            logger.error(f"Error en trade manual: {e}")
            messagebox.showerror("Error", f"Error ejecutando trade: {e}")
    
    def close_all_positions(self):
        """Cierra todas las posiciones abiertas."""
        try:
            positions_to_close = list(self.paper_engine.positions.keys())
            
            for symbol in positions_to_close:
                position = self.paper_engine.positions[symbol]
                current_price = self.current_prices.get(symbol, position.current_price)
                
                side = 'sell' if position.side == PositionSide.LONG else 'buy'
                
                self.paper_engine.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    quantity=position.size,
                    price=current_price
                )
            
            logger.info(f"🔄 Cerrando {len(positions_to_close)} posiciones")
            
        except Exception as e:
            logger.error(f"Error cerrando posiciones: {e}")
    
    def update_ui(self):
        """Actualiza la interfaz de usuario."""
        try:
            # Actualizar resumen del portfolio
            summary = self.paper_engine.get_portfolio_summary()
            
            self.portfolio_labels['initial_capital'].config(text=f"${summary['initial_capital']:,.2f}")
            self.portfolio_labels['current_capital'].config(text=f"${summary['current_capital']:,.2f}")
            self.portfolio_labels['total_portfolio_value'].config(text=f"${summary['total_portfolio_value']:,.2f}")
            
            # Color para PnL
            pnl_color = '#00ff00' if summary['total_pnl'] >= 0 else '#ff4444'
            self.portfolio_labels['total_pnl'].config(text=f"${summary['total_pnl']:,.2f}", foreground=pnl_color)
            
            return_color = '#00ff00' if summary['total_return_pct'] >= 0 else '#ff4444'
            self.portfolio_labels['total_return_pct'].config(text=f"{summary['total_return_pct']:.2f}%", foreground=return_color)
            
            self.portfolio_labels['total_trades'].config(text=f"{summary['total_trades']}")
            self.portfolio_labels['win_rate'].config(text=f"{summary['win_rate']*100:.1f}%")
            self.portfolio_labels['max_drawdown'].config(text=f"{summary['max_drawdown']:.2f}%")
            
            # Actualizar tabla de posiciones
            self.update_positions_table()
            
            # Actualizar tabla de breakouts
            self.update_breakouts_table()
            
        except Exception as e:
            logger.error(f"Error actualizando UI: {e}")
    
    def update_positions_table(self):
        """Actualiza la tabla de posiciones."""
        try:
            # Limpiar tabla
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
            
            # Agregar posiciones actuales
            positions = self.paper_engine.get_positions_summary()
            for pos in positions:
                pnl_color = 'green' if pos['unrealized_pnl'] >= 0 else 'red'
                
                self.positions_tree.insert('', 'end', values=(
                    pos['symbol'],
                    pos['side'].upper(),
                    f"{pos['size']:.4f}",
                    f"${pos['entry_price']:.2f}",
                    f"${pos['current_price']:.2f}",
                    f"${pos['unrealized_pnl']:.2f}",
                    f"{pos['pnl_percentage']:.2f}%"
                ), tags=(pnl_color,))
            
            # Configurar colores
            self.positions_tree.tag_configure('green', foreground='#00ff00')
            self.positions_tree.tag_configure('red', foreground='#ff4444')
            
        except Exception as e:
            logger.error(f"Error actualizando tabla de posiciones: {e}")
    
    def update_breakouts_table(self):
        """Actualiza la tabla de breakouts."""
        try:
            # Limpiar tabla
            for item in self.breakouts_tree.get_children():
                self.breakouts_tree.delete(item)
            
            # Agregar breakouts recientes (últimos 10)
            recent_breakouts = sorted(
                self.breakout_signals.items(),
                key=lambda x: x[1]['timestamp'],
                reverse=True
            )[:10]
            
            for symbol, signal in recent_breakouts:
                self.breakouts_tree.insert('', 'end', values=(
                    symbol,
                    signal['type'].upper(),
                    f"${signal['price']:.2f}",
                    f"{signal['volume']:.2f}",
                    signal['timestamp'].strftime("%H:%M:%S")
                ))
                
        except Exception as e:
            logger.error(f"Error actualizando tabla de breakouts: {e}")
    
    def toggle_auto_trading(self):
        """Activa/desactiva el auto-trading."""
        if self.auto_trading_enabled.get():
            logger.info("🤖 Auto-trading ACTIVADO")
        else:
            logger.info("🤖 Auto-trading DESACTIVADO")
    
    def open_config_dialog(self):
        """Abre el diálogo de configuración."""
        config_window = tk.Toplevel(self.root)
        config_window.title("Configuración de Paper Trading")
        config_window.geometry("400x300")
        config_window.configure(bg='#1e1e1e')
        
        # Aquí se puede agregar más configuración avanzada
        ttk.Label(config_window, text="Configuración Avanzada", font=('Arial', 14, 'bold')).pack(pady=20)
        ttk.Label(config_window, text="(Funcionalidad en desarrollo)").pack()
    
    def save_session(self):
        """Guarda la sesión actual."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"paper_trading_session_{timestamp}.json"
            self.paper_engine.save_state(filename)
            logger.info(f"💾 Sesión guardada: {filename}")
        except Exception as e:
            logger.error(f"Error guardando sesión: {e}")
    
    def run(self):
        """Ejecuta el dashboard."""
        try:
            # Configurar cierre de ventana
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            # Iniciar loop principal
            self.root.mainloop()
            
        except Exception as e:
            logger.error(f"Error ejecutando dashboard: {e}")
    
    def on_closing(self):
        """Maneja el cierre de la aplicación."""
        if self.is_running:
            self.stop_monitoring()
        
        # Guardar sesión automáticamente
        self.save_session()
        
        self.root.destroy()

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear y ejecutar dashboard
    dashboard = PaperTradingDashboard(initial_capital=10000.0)
    dashboard.run()