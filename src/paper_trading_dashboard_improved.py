"""
Dashboard Mejorado de Paper Trading para SICAR
Versión optimizada que evita problemas de cuelgue
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import queue

# Importaciones del sistema SICAR
from first_candle_breakout import FirstCandleBreakoutDetector
from paper_trading_system import PaperTradingEngine, OrderType, OrderStatus
from binance_data_provider import BinanceDataProvider
from session_detector import SessionDetector

class ImprovedPaperTradingDashboard:
    def __init__(self):
        """Inicializar el dashboard mejorado de paper trading"""
        self.setup_logging()
        
        # Configuración de threading
        self.running = False
        self.update_queue = queue.Queue()
        
        # Inicializar componentes del sistema
        self.init_trading_components()
        
        # Configurar la interfaz gráfica
        self.setup_gui()
        
        # Variables de control
        self.auto_trading_enabled = True  # ACTIVADO PARA PRUEBA
        self.last_update = datetime.now()
        
        # Configurar actualizaciones periódicas
        self.setup_periodic_updates()
        
    def setup_logging(self):
        """Configurar el sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('paper_trading_dashboard.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def init_trading_components(self):
        """Inicializar los componentes de trading de forma segura"""
        try:
            self.logger.info("Inicializando componentes de trading...")
            
            # Inicializar detector de breakouts
            self.breakout_detector = FirstCandleBreakoutDetector()
            self.logger.info("Detector de breakouts inicializado")
            
            # Inicializar detector de sesiones
            self.session_detector = SessionDetector()
            self.logger.info("Detector de sesiones inicializado")
            
            # Inicializar proveedor de datos
            self.data_provider = BinanceDataProvider()
            self.logger.info("Proveedor de datos Binance inicializado")
            
            # Cargar configuración correcta
            config_file = 'sicar_config.json'
            initial_capital = 250.0  # Valor por defecto según análisis previo
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    initial_capital = config.get('PAPER_TRADING_CONFIG', {}).get('initial_capital', 200.0)
            
            # Inicializar motor de paper trading
            self.paper_engine = PaperTradingEngine(initial_capital=initial_capital)
            self.logger.info(f"Motor de paper trading inicializado con capital: ${initial_capital}")
            
            # Lista de símbolos activos - Solo ETH para análisis específico
            self.active_symbols = ['ETHUSDT']
            
            # Inicializar diccionario de precios actuales
            self.current_prices = {}
            
            self.logger.info(f"Símbolos activos: {len(self.active_symbols)}")
            
        except Exception as e:
            self.logger.error(f"Error inicializando componentes: {e}")
            messagebox.showerror("Error", f"Error inicializando sistema: {e}")
            
    def setup_gui(self):
        """Configurar la interfaz gráfica de usuario"""
        self.root = tk.Tk()
        self.root.title("SICAR - Paper Trading Dashboard (Mejorado)")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configurar estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        # Crear notebook para pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Crear pestañas
        self.create_trading_tab()
        self.create_portfolio_tab()
        self.create_performance_tab()
        self.create_log_tab()
        
        # Barra de estado
        self.create_status_bar()
        
    def create_trading_tab(self):
        """Crear la pestaña de trading"""
        trading_frame = ttk.Frame(self.notebook)
        self.notebook.add(trading_frame, text="Trading")
        
        # Panel de control
        control_frame = ttk.LabelFrame(trading_frame, text="Control de Trading")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Botones de control
        ttk.Button(control_frame, text="Iniciar Auto-Trading", 
                  command=self.toggle_auto_trading).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Actualizar Datos", 
                  command=self.manual_update).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Cerrar Todas las Posiciones", 
                  command=self.close_all_positions).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Modificar Capital", 
                  command=self.modify_capital).pack(side=tk.LEFT, padx=5)
        
        # Panel de trading manual
        manual_frame = ttk.LabelFrame(trading_frame, text="Trading Manual")
        manual_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Controles de trading manual
        ttk.Label(manual_frame, text="Símbolo:").grid(row=0, column=0, padx=5, pady=5)
        self.symbol_var = tk.StringVar(value="ETHUSDT")
        symbol_combo = ttk.Combobox(manual_frame, textvariable=self.symbol_var, 
                                   values=["ETHUSDT"])  # Solo ETH para análisis específico
        symbol_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(manual_frame, text="Cantidad:").grid(row=0, column=2, padx=5, pady=5)
        self.quantity_var = tk.StringVar(value="100")
        ttk.Entry(manual_frame, textvariable=self.quantity_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Button(manual_frame, text="Comprar", 
                  command=lambda: self.manual_trade("BUY")).grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(manual_frame, text="Vender", 
                  command=lambda: self.manual_trade("SELL")).grid(row=0, column=5, padx=5, pady=5)
        
        # Lista de breakouts detectados
        breakout_frame = ttk.LabelFrame(trading_frame, text="Breakouts Detectados")
        breakout_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview para breakouts
        columns = ("Símbolo", "Tipo", "Precio", "Volumen", "Tiempo")
        self.breakout_tree = ttk.Treeview(breakout_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.breakout_tree.heading(col, text=col)
            self.breakout_tree.column(col, width=120)
            
        self.breakout_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar para breakouts
        breakout_scroll = ttk.Scrollbar(breakout_frame, orient=tk.VERTICAL, command=self.breakout_tree.yview)
        self.breakout_tree.configure(yscrollcommand=breakout_scroll.set)
        breakout_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_portfolio_tab(self):
        """Crear la pestaña de portfolio"""
        portfolio_frame = ttk.Frame(self.notebook)
        self.notebook.add(portfolio_frame, text="Portfolio")
        
        # Información del capital
        capital_frame = ttk.LabelFrame(portfolio_frame, text="Capital")
        capital_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.capital_label = ttk.Label(capital_frame, text="Capital: $10,000.00", font=("Arial", 12, "bold"))
        self.capital_label.pack(pady=10)
        
        self.pnl_label = ttk.Label(capital_frame, text="PnL: $0.00 (0.00%)", font=("Arial", 10))
        self.pnl_label.pack(pady=5)
        
        # Posiciones activas
        positions_frame = ttk.LabelFrame(portfolio_frame, text="Posiciones Activas")
        positions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview para posiciones
        pos_columns = ("Símbolo", "Lado", "Cantidad", "Precio Entrada", "Precio Actual", "PnL", "PnL %")
        self.positions_tree = ttk.Treeview(positions_frame, columns=pos_columns, show="headings", height=10)
        
        for col in pos_columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100)
            
        self.positions_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar para posiciones
        pos_scroll = ttk.Scrollbar(positions_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=pos_scroll.set)
        pos_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
    def create_performance_tab(self):
        """Crear la pestaña de rendimiento"""
        performance_frame = ttk.Frame(self.notebook)
        self.notebook.add(performance_frame, text="Rendimiento")
        
        # Métricas de rendimiento
        metrics_frame = ttk.LabelFrame(performance_frame, text="Métricas de Rendimiento")
        metrics_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.metrics_text = scrolledtext.ScrolledText(metrics_frame, height=15, width=80)
        self.metrics_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Botón para actualizar métricas
        ttk.Button(metrics_frame, text="Actualizar Métricas", 
                  command=self.update_performance_metrics).pack(pady=5)
        
    def create_log_tab(self):
        """Crear la pestaña de logs"""
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Logs")
        
        # Área de logs
        self.log_text = scrolledtext.ScrolledText(log_frame, height=25, width=100)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Botón para limpiar logs
        ttk.Button(log_frame, text="Limpiar Logs", 
                  command=lambda: self.log_text.delete(1.0, tk.END)).pack(pady=5)
        
    def create_status_bar(self):
        """Crear la barra de estado"""
        self.status_bar = ttk.Label(self.root, text="Sistema iniciado", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_periodic_updates(self):
        """Configurar actualizaciones periódicas de forma segura"""
        def safe_update():
            try:
                if self.running:
                    self.update_dashboard()
                    self.root.after(5000, safe_update)  # Actualizar cada 5 segundos
            except Exception as e:
                self.logger.error(f"Error en actualización periódica: {e}")
                self.root.after(10000, safe_update)  # Reintentar en 10 segundos
                
        self.root.after(1000, safe_update)  # Iniciar después de 1 segundo
        
    def update_market_data(self):
        """Actualizar los datos de mercado y precios actuales"""
        try:
            new_prices = {}
            for symbol in self.active_symbols:
                try:
                    price = self.data_provider.get_current_price(symbol)
                    if price:
                        new_prices[symbol] = float(price)
                except Exception as e:
                    self.logger.warning(f"Error obteniendo precio de {symbol}: {e}")
            
            self.current_prices.update(new_prices)
            self.last_update = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error actualizando datos de mercado: {e}")
        
    def toggle_auto_trading(self):
        """Alternar el auto-trading"""
        self.auto_trading_enabled = not self.auto_trading_enabled
        status = "activado" if self.auto_trading_enabled else "desactivado"
        self.log_message(f"Auto-trading {status}")
        self.update_status(f"Auto-trading {status}")
        
    def execute_auto_trading(self):
        """Ejecutar auto-trading basado en detección de breakouts"""
        try:
            # Obtener sesión actual
            current_session = self.session_detector.get_current_session()
            if not current_session:
                self.log_message("⏰ No hay sesión activa - Auto-trading en espera")
                return
                
            # Detectar breakouts para cada símbolo activo
            for symbol in self.active_symbols:
                # Verificar si ya tenemos posición en este símbolo
                if symbol in self.paper_engine.positions:
                    continue
                
                # Verificar límite de posiciones (máximo 3)
                if len(self.paper_engine.positions) >= 3:
                    continue
                
                # Detectar breakout
                try:
                    breakout_signal = self.breakout_detector.detect_breakout(symbol, current_session)
                    
                    if breakout_signal and breakout_signal.signal_type in ['bullish', 'bearish']:
                        current_price = self.current_prices.get(symbol, 0)
                        if current_price == 0:
                            continue
                            
                        # Calcular tamaño de posición (5% del capital)
                        portfolio_value = self.paper_engine.current_capital
                        position_value = portfolio_value * 0.05  # 5% del capital
                        quantity = position_value / current_price
                        
                        # Ejecutar orden según el tipo de breakout
                        if breakout_signal.signal_type == 'bullish':
                            order_id = self.paper_engine.place_order(
                                symbol=symbol,
                                side='buy',
                                order_type=OrderType.MARKET,
                                quantity=quantity,
                                price=current_price
                            )
                            
                            self.log_message(f"🤖 AUTO-TRADE BULLISH: {symbol} - Cantidad: {quantity:.4f} - Precio: ${current_price:.2f}")
                            self.log_message(f"   Señal: Confianza {breakout_signal.confidence:.2f} - Volumen {breakout_signal.volume_ratio:.2f}x")
                            
                        elif breakout_signal.signal_type == 'bearish':
                            # Para señales bearish, podríamos hacer short (venta)
                            # Por ahora solo registramos la señal
                            self.log_message(f"🔻 SEÑAL BEARISH detectada: {symbol} - Precio: ${current_price:.2f}")
                            self.log_message(f"   Señal: Confianza {breakout_signal.confidence:.2f} - Volumen {breakout_signal.volume_ratio:.2f}x")
                            
                except Exception as e:
                    self.logger.warning(f"Error detectando breakout para {symbol}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error en auto-trading: {e}")
        
    def manual_trade(self, side):
        """Ejecutar una operación manual"""
        try:
            symbol = self.symbol_var.get()
            quantity = float(self.quantity_var.get())
            
            # Obtener precio actual para la orden
            current_price = self.current_prices.get(symbol, 0)
            if current_price == 0:
                raise ValueError(f"No hay precio disponible para {symbol}")
            
            if side == "BUY":
                order_id = self.paper_engine.place_order(
                    symbol=symbol, 
                    side='buy', 
                    order_type=OrderType.MARKET, 
                    quantity=quantity, 
                    price=current_price
                )
            else:
                order_id = self.paper_engine.place_order(
                    symbol=symbol, 
                    side='sell', 
                    order_type=OrderType.MARKET, 
                    quantity=quantity, 
                    price=current_price
                )
                
            self.log_message(f"Orden {side} ejecutada: {symbol} x {quantity} (ID: {order_id})")
            self.update_portfolio_display()
            
        except Exception as e:
            self.logger.error(f"Error en trading manual: {e}")
            messagebox.showerror("Error", f"Error ejecutando orden: {e}")
            
    def close_all_positions(self):
        """Cerrar todas las posiciones abiertas"""
        try:
            closed_count = 0
            for symbol, position in self.paper_engine.positions.items():
                if position.size != 0:
                    # Obtener precio actual
                    current_price = self.current_prices.get(symbol, position.current_price)
                    
                    # Cerrar posición
                    if position.size > 0:
                        order_id = self.paper_engine.place_order(
                            symbol=symbol, 
                            side='sell', 
                            order_type=OrderType.MARKET, 
                            quantity=abs(position.size), 
                            price=current_price
                        )
                    else:
                        order_id = self.paper_engine.place_order(
                            symbol=symbol, 
                            side='buy', 
                            order_type=OrderType.MARKET, 
                            quantity=abs(position.size), 
                            price=current_price
                        )
                    closed_count += 1
                    
            self.log_message(f"Cerradas {closed_count} posiciones")
            self.update_portfolio_display()
            
        except Exception as e:
            self.logger.error(f"Error cerrando posiciones: {e}")
            
    def modify_capital(self):
        """Abre un diálogo para modificar el capital inicial."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Modificar Capital Inicial")
        dialog.geometry("400x350")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Centrar el diálogo
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (dialog.winfo_screenheight() // 2) - (350 // 2)
        dialog.geometry(f"400x350+{x}+{y}")
        
        # Frame principal
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Información actual
        ttk.Label(main_frame, text="Capital Actual:", font=('Arial', 12, 'bold')).pack(anchor='w')
        current_info = f"Capital Inicial: ${self.paper_engine.initial_capital:,.2f}\n"
        current_info += f"Capital Disponible: ${self.paper_engine.current_capital:,.2f}\n"
        current_info += f"Posiciones Abiertas: {len(self.paper_engine.positions)}\n"
        current_info += f"Órdenes Pendientes: {len([o for o in self.paper_engine.orders.values() if o.status.name == 'PENDING'])}"
        ttk.Label(main_frame, text=current_info, font=('Arial', 10)).pack(anchor='w', pady=(0, 20))
        
        # Nuevo capital
        ttk.Label(main_frame, text="Nuevo Capital Inicial:", font=('Arial', 12, 'bold')).pack(anchor='w')
        capital_var = tk.StringVar(value=str(self.paper_engine.initial_capital))
        capital_entry = ttk.Entry(main_frame, textvariable=capital_var, font=('Arial', 12))
        capital_entry.pack(fill='x', pady=(5, 20))
        capital_entry.select_range(0, tk.END)
        capital_entry.focus()
        
        # Opciones
        close_positions_var = tk.BooleanVar(value=True)
        reset_history_var = tk.BooleanVar(value=False)
        
        options_frame = ttk.LabelFrame(main_frame, text="Opciones", padding="10")
        options_frame.pack(fill='x', pady=(0, 20))
        
        ttk.Checkbutton(options_frame, text="Cerrar todas las posiciones abiertas", 
                       variable=close_positions_var).pack(anchor='w', pady=2)
        ttk.Checkbutton(options_frame, text="Resetear historial de operaciones", 
                       variable=reset_history_var).pack(anchor='w', pady=2)
        
        # Advertencia
        warning_text = "⚠️ ADVERTENCIA: Esta acción modificará permanentemente el estado del paper trading."
        ttk.Label(main_frame, text=warning_text, font=('Arial', 9), foreground='red').pack(anchor='w', pady=(0, 10))
        
        # Frame para botones
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        def apply_changes():
            try:
                new_capital = float(capital_var.get())
                if new_capital <= 0:
                    messagebox.showerror("Error", "El capital debe ser mayor que 0")
                    return
                
                # Confirmar cambios
                message = f"¿Confirmar cambio de capital a ${new_capital:,.2f}?"
                if close_positions_var.get():
                    message += "\n• Se cerrarán todas las posiciones abiertas"
                if reset_history_var.get():
                    message += "\n• Se reseteará el historial de operaciones"
                message += "\n\nEsta acción no se puede deshacer."
                
                if messagebox.askyesno("Confirmar Cambios", message):
                    try:
                        # Aplicar cambios usando la nueva función del motor
                        self.paper_engine.reset_capital(
                            new_capital, 
                            close_positions_var.get(), 
                            reset_history_var.get()
                        )
                        
                        # Actualizar displays
                        self.update_portfolio_display()
                        self.update_performance_metrics()
                        
                        # Limpiar logs si se reseteó el historial
                        if reset_history_var.get():
                            self.log_text.delete(1.0, tk.END)
                            self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Capital reseteado a ${new_capital:,.2f}\n")
                        
                        # Mensaje de éxito
                        messagebox.showinfo("Éxito", f"Capital modificado exitosamente a ${new_capital:,.2f}")
                        dialog.destroy()
                        
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al aplicar cambios: {str(e)}")
                    
            except ValueError:
                messagebox.showerror("Error", "Por favor ingrese un valor numérico válido")
            except Exception as e:
                messagebox.showerror("Error", f"Error al procesar entrada: {str(e)}")
        
        ttk.Button(button_frame, text="Aplicar", command=apply_changes).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancelar", command=dialog.destroy).pack(side='right')
        
        # Bind Enter key
        dialog.bind('<Return>', lambda e: apply_changes())
            
    def manual_update(self):
        """Actualización manual de datos"""
        self.log_message("Actualizando datos manualmente...")
        self.update_dashboard()
        
    def update_dashboard(self):
        """Actualizar el dashboard de forma segura"""
        try:
            # Actualizar solo si la ventana existe y está visible
            if not self.root.winfo_exists():
                return
                
            # Actualizar precios de mercado
            self.update_market_data()
            
            # Ejecutar auto-trading si está activado
            if self.auto_trading_enabled:
                self.execute_auto_trading()
                
            # Actualizar displays
            self.update_portfolio_display()
            self.update_breakout_display()
            
            # Actualizar timestamp
            self.last_update = datetime.now()
            status_text = f"Última actualización: {self.last_update.strftime('%H:%M:%S')}"
            if self.auto_trading_enabled:
                status_text += " | AUTO-TRADING ACTIVO"
            self.update_status(status_text)
            
        except Exception as e:
            self.logger.error(f"Error actualizando dashboard: {e}")
            
    def update_portfolio_display(self):
        """Actualizar la visualización del portfolio"""
        try:
            # Actualizar capital
            capital = self.paper_engine.current_capital
            total_pnl = sum(pos.unrealized_pnl for pos in self.paper_engine.positions.values())
            pnl_percent = (total_pnl / self.paper_engine.initial_capital) * 100
            
            self.capital_label.config(text=f"Capital: ${capital:,.2f}")
            
            color = "green" if total_pnl >= 0 else "red"
            self.pnl_label.config(text=f"PnL: ${total_pnl:,.2f} ({pnl_percent:.2f}%)", foreground=color)
            
            # Limpiar y actualizar posiciones
            for item in self.positions_tree.get_children():
                self.positions_tree.delete(item)
                
            for symbol, position in self.paper_engine.positions.items():
                if position.size != 0:
                    side = "LONG" if position.size > 0 else "SHORT"
                    pnl_pct = (position.unrealized_pnl / (abs(position.size) * position.entry_price)) * 100
                    
                    self.positions_tree.insert("", "end", values=(
                        symbol,
                        side,
                        f"{abs(position.size):.4f}",
                        f"${position.entry_price:.4f}",
                        f"${position.current_price:.4f}",
                        f"${position.unrealized_pnl:.2f}",
                        f"{pnl_pct:.2f}%"
                    ))
                    
        except Exception as e:
            self.logger.error(f"Error actualizando portfolio: {e}")
            
    def update_breakout_display(self):
        """Actualizar la visualización de breakouts (simplificada)"""
        try:
            # Simulación de breakouts para evitar sobrecarga de API
            current_time = datetime.now()
            
            # Limpiar breakouts antiguos (más de 1 hora)
            for item in self.breakout_tree.get_children():
                self.breakout_tree.delete(item)
                
            # Agregar algunos breakouts simulados para demostración
            if len(self.breakout_tree.get_children()) < 5:
                import random
                symbol = random.choice(self.active_symbols[:5])
                breakout_type = random.choice(["Alcista", "Bajista"])
                price = random.uniform(20000, 50000)
                volume = random.uniform(1000000, 5000000)
                
                self.breakout_tree.insert("", "end", values=(
                    symbol,
                    breakout_type,
                    f"${price:.2f}",
                    f"{volume:,.0f}",
                    current_time.strftime("%H:%M:%S")
                ))
                
        except Exception as e:
            self.logger.error(f"Error actualizando breakouts: {e}")
            
    def update_performance_metrics(self):
        """Actualizar métricas de rendimiento"""
        try:
            metrics = self.paper_engine.get_performance_metrics()
            
            metrics_text = f"""
MÉTRICAS DE RENDIMIENTO - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}

Capital Inicial: ${metrics['initial_capital']:,.2f}
Capital Actual: ${metrics['current_capital']:,.2f}
PnL Total: ${metrics['total_pnl']:,.2f}
Retorno Total: {metrics['total_return']:.2f}%

Operaciones Totales: {metrics['total_trades']}
Operaciones Ganadoras: {metrics['winning_trades']}
Operaciones Perdedoras: {metrics['losing_trades']}
Tasa de Éxito: {metrics['win_rate']:.2f}%

Ganancia Promedio: ${metrics['avg_win']:,.2f}
Pérdida Promedio: ${metrics['avg_loss']:,.2f}
Ratio Ganancia/Pérdida: {metrics['profit_factor']:.2f}

Drawdown Máximo: {metrics['max_drawdown']:.2f}%
Posiciones Activas: {len([p for p in self.paper_engine.positions.values() if p.size != 0])}

Comisiones Pagadas: ${metrics.get('total_commission', 0):,.2f}
Slippage Total: ${metrics.get('total_slippage', 0):,.2f}
            """
            
            self.metrics_text.delete(1.0, tk.END)
            self.metrics_text.insert(1.0, metrics_text)
            
        except Exception as e:
            self.logger.error(f"Error actualizando métricas: {e}")
            
    def log_message(self, message):
        """Agregar mensaje al log"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            
            # Limitar el tamaño del log
            lines = self.log_text.get(1.0, tk.END).split('\n')
            if len(lines) > 1000:
                self.log_text.delete(1.0, f"{len(lines)-500}.0")
                
        except Exception as e:
            self.logger.error(f"Error agregando log: {e}")
            
    def update_status(self, message):
        """Actualizar la barra de estado"""
        try:
            self.status_bar.config(text=message)
        except Exception as e:
            self.logger.error(f"Error actualizando status: {e}")
            
    def on_closing(self):
        """Manejar el cierre de la aplicación"""
        try:
            self.running = False
            self.logger.info("Cerrando dashboard de paper trading...")
            
            # Guardar estado si es necesario
            self.save_session()
            
            # Cerrar ventana
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"Error cerrando aplicación: {e}")
            
    def save_session(self):
        """Guardar la sesión actual"""
        try:
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'capital': self.paper_engine.current_capital,
                'positions': len([p for p in self.paper_engine.positions.values() if p.size != 0]),
                'total_trades': len(self.paper_engine.order_history),
                'auto_trading': self.auto_trading_enabled
            }
            
            with open('data/paper_trading_session.json', 'w') as f:
                json.dump(session_data, f, indent=2)
                
            self.logger.info("Sesión guardada correctamente")
            
        except Exception as e:
            self.logger.error(f"Error guardando sesión: {e}")
            
    def run(self):
        """Ejecutar el dashboard"""
        try:
            self.running = True
            self.logger.info("Iniciando dashboard de paper trading mejorado...")
            
            # Mensaje inicial
            self.log_message("Dashboard de Paper Trading SICAR iniciado")
            self.log_message(f"Capital inicial: ${self.paper_engine.initial_capital:,.2f}")
            self.log_message(f"Símbolos activos: {len(self.active_symbols)}")
            
            # Iniciar loop principal
            self.root.mainloop()
            
        except Exception as e:
            self.logger.error(f"Error ejecutando dashboard: {e}")
            messagebox.showerror("Error Fatal", f"Error ejecutando dashboard: {e}")

def main():
    """Función principal"""
    try:
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        
        # Crear y ejecutar dashboard
        dashboard = ImprovedPaperTradingDashboard()
        dashboard.run()
        
    except Exception as e:
        logging.error(f"Error fatal en main: {e}")
        print(f"Error fatal: {e}")

if __name__ == "__main__":
    main()