"""
Dashboard Mejorado de SICAR
Integra todos los sistemas de mejora implementados
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json
from pathlib import Path

# Importar sistemas mejorados
from enhanced_config import CONFIG
from enhanced_logger import SICAR_LOGGER
from enhanced_sync_manager import SYNC_MANAGER
from enhanced_breakout_detector import BREAKOUT_DETECTOR, BreakoutSignal, BreakoutType, BreakoutStrength
from session_detector import SessionDetector

# Importar integración breakout-portfolio
try:
    from breakout_portfolio_integration import (
        BreakoutPortfolioIntegrator, 
        BreakoutPortfolioStrategy, 
        BreakoutPortfolioSignal
    )
    from portfolio_optimizer import PortfolioOptimizer
    PORTFOLIO_INTEGRATION_AVAILABLE = True
except ImportError as e:
    SICAR_LOGGER.log_error("PORTFOLIO_IMPORT", f"No se pudo importar integración de portfolio: {e}")
    PORTFOLIO_INTEGRATION_AVAILABLE = False

# Importar sistema de paper trading
try:
    from paper_trading_system import PaperTradingEngine, OrderType, PositionSide
    PAPER_TRADING_AVAILABLE = True
except ImportError as e:
    SICAR_LOGGER.log_error("PAPER_TRADING_IMPORT", f"No se pudo importar sistema de paper trading: {e}")
    PAPER_TRADING_AVAILABLE = False

class EnhancedDashboard:
    """Dashboard mejorado con todas las funcionalidades integradas"""
    
    def __init__(self):
        # Cargar configuración desde archivo al inicio
        CONFIG.load_config_from_file()
        
        self.root = tk.Tk()
        self.root.title("SICAR - Sistema Mejorado de Trading")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e1e')
        
        # Sistemas integrados
        self.sync_manager = SYNC_MANAGER
        self.session_detector = SessionDetector()
        
        # Variables de estado
        self.auto_trading_var = tk.BooleanVar(value=CONFIG.AUTO_TRADING_DEFAULT)
        self.current_session_var = tk.StringVar(value="Ninguna")
        self.capital_var = tk.StringVar(value=f"${CONFIG.PAPER_TRADING_CONFIG['initial_capital']:,.2f}")
        self.pnl_var = tk.StringVar(value="$0.00")
        self.trades_var = tk.StringVar(value="0")
        
        # Variables para próximas sesiones
        self.next_session_var = tk.StringVar(value="Calculando...")
        self.next_session_time_var = tk.StringVar(value="--:--")
        
        # Estado de sistemas
        self.systems_running = False
        self.update_thread = None
        
        # Control de popups eliminado - ahora usamos solo consola
        
        # Variables para integración de portfolio
        if PORTFOLIO_INTEGRATION_AVAILABLE:
            self.portfolio_integrator = None
            self.portfolio_integration_active = tk.BooleanVar(value=False)
            self.portfolio_strategy_var = tk.StringVar(value="momentum_weighted")
            self.portfolio_signals_count = tk.StringVar(value="0")
            self.portfolio_performance = tk.StringVar(value="0.00%")
            self.portfolio_allocation = tk.StringVar(value="Sin datos")
            # Variables adicionales para la UI del portfolio
            self.portfolio_signals_count_var = tk.StringVar(value="0")
            self.portfolio_performance_var = tk.StringVar(value="0.00%")
            self.portfolio_allocation_var = tk.StringVar(value="Sin asignación")
            self.portfolio_status_var = tk.StringVar(value="🔴 No iniciada")
        
        # Inicializar sistema de paper trading
        if PAPER_TRADING_AVAILABLE:
            self.paper_engine = PaperTradingEngine(
                initial_capital=CONFIG.PAPER_TRADING_CONFIG['initial_capital'],
                commission_rate=CONFIG.PAPER_TRADING_CONFIG['commission_rate']
            )
            self.paper_trading_active = tk.BooleanVar(value=True)  # Activado por defecto
            SICAR_LOGGER.log_alert("PAPER_TRADING", f"Motor de paper trading inicializado con ${CONFIG.PAPER_TRADING_CONFIG['initial_capital']:,.2f}", "INFO")
        else:
            self.paper_engine = None
            self.paper_trading_active = tk.BooleanVar(value=False)
        
        # Inicializar breakout detector con paper trading
        from enhanced_breakout_detector import EnhancedBreakoutDetector
        self.breakout_detector = EnhancedBreakoutDetector(paper_trading_system=self.paper_engine)
        
        # Variables para estadísticas de scalping
        self.scalping_enabled_var = tk.BooleanVar(value=CONFIG.SCALPING_CONFIG.get('enabled', True))
        self.scalping_trades_var = tk.StringVar(value="0")
        self.scalping_pnl_var = tk.StringVar(value="$0.00")
        self.scalping_win_rate_var = tk.StringVar(value="0.0%")
        self.scalping_sessions_var = tk.StringVar(value="0")
        self.scalping_active_positions_var = tk.StringVar(value="0")
        
        # Variables para métricas DRL
        self.drl_enabled_var = tk.BooleanVar(value=False)
        self.drl_mode_var = tk.StringVar(value="Manual")
        self.drl_confidence_var = tk.StringVar(value="0.00")
        self.drl_sharpe_var = tk.StringVar(value="0.00")
        self.drl_win_rate_var = tk.StringVar(value="0.0%")
        self.drl_total_reward_var = tk.StringVar(value="0.00")
        self.drl_episodes_var = tk.StringVar(value="0")
        self.drl_status_var = tk.StringVar(value="🔴 Desconectado")
        
        # Sistema DRL integrado
        self.drl_integrated_system = None
        self.drl_monitoring_system = None
        
        # Configurar interfaz
        self.setup_ui()
        
        # Configurar callbacks
        self.setup_callbacks()
        
        # Iniciar sistemas
        self.start_systems()
        
        SICAR_LOGGER.log_alert("DASHBOARD", "Dashboard mejorado iniciado correctamente", "INFO")
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Panel superior - Métricas principales
        self.create_metrics_panel(main_frame)
        
        # Panel central - Información detallada
        self.create_info_panel(main_frame)
        
        # Panel inferior - Controles y logs
        self.create_controls_panel(main_frame)
    
    def create_metrics_panel(self, parent):
        """Crear panel de métricas principales"""
        metrics_frame = ttk.LabelFrame(parent, text="📊 Métricas Principales", padding=10)
        metrics_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Frame principal con layout horizontal
        main_container = ttk.Frame(metrics_frame)
        main_container.pack(fill=tk.X)
        
        # Frame izquierdo para métricas principales
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Grid de métricas principales
        metrics_grid = ttk.Frame(left_frame)
        metrics_grid.pack(fill=tk.X)
        
        # Capital actual
        ttk.Label(metrics_grid, text="💰 Capital:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(metrics_grid, textvariable=self.capital_var, font=('Arial', 10)).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        # PnL
        ttk.Label(metrics_grid, text="📈 PnL:", font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        ttk.Label(metrics_grid, textvariable=self.pnl_var, font=('Arial', 10)).grid(row=0, column=3, sticky=tk.W, padx=(0, 20))
        
        # Trades
        ttk.Label(metrics_grid, text="🔄 Trades:", font=('Arial', 10, 'bold')).grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        ttk.Label(metrics_grid, textvariable=self.trades_var, font=('Arial', 10)).grid(row=0, column=5, sticky=tk.W, padx=(0, 20))
        
        # Sesión actual
        ttk.Label(metrics_grid, text="📅 Sesión:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        ttk.Label(metrics_grid, textvariable=self.current_session_var, font=('Arial', 10)).grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(0, 20), pady=(10, 0))
        
        # Auto Trading toggle
        ttk.Checkbutton(metrics_grid, text="🤖 Auto Trading", variable=self.auto_trading_var, 
                       command=self.toggle_auto_trading).grid(row=1, column=3, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        # Panel de scalping (nueva fila)
        scalping_frame = ttk.LabelFrame(left_frame, text="🚀 Scalping Automático", padding=8)
        scalping_frame.pack(fill=tk.X, pady=(10, 0))
        
        scalping_grid = ttk.Frame(scalping_frame)
        scalping_grid.pack(fill=tk.X)
        
        # Scalping habilitado/deshabilitado
        ttk.Checkbutton(scalping_grid, text="🚀 Scalping Activo", variable=self.scalping_enabled_var, 
                       command=self.toggle_scalping).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        # Trades de scalping
        ttk.Label(scalping_grid, text="📊 Trades:", font=('Arial', 9, 'bold')).grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        ttk.Label(scalping_grid, textvariable=self.scalping_trades_var, font=('Arial', 9)).grid(row=0, column=2, sticky=tk.W, padx=(0, 15))
        
        # PnL de scalping
        ttk.Label(scalping_grid, text="💰 PnL:", font=('Arial', 9, 'bold')).grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        ttk.Label(scalping_grid, textvariable=self.scalping_pnl_var, font=('Arial', 9)).grid(row=0, column=4, sticky=tk.W, padx=(0, 15))
        
        # Win Rate
        ttk.Label(scalping_grid, text="🎯 Win Rate:", font=('Arial', 9, 'bold')).grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Label(scalping_grid, textvariable=self.scalping_win_rate_var, font=('Arial', 9)).grid(row=1, column=2, sticky=tk.W, padx=(0, 15), pady=(5, 0))
        
        # Posiciones activas
        ttk.Label(scalping_grid, text="⚡ Activas:", font=('Arial', 9, 'bold')).grid(row=1, column=3, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Label(scalping_grid, textvariable=self.scalping_active_positions_var, font=('Arial', 9)).grid(row=1, column=4, sticky=tk.W, padx=(0, 15), pady=(5, 0))
        
        # Frame derecho para próximas sesiones
        right_frame = ttk.LabelFrame(main_container, text="⏰ Próximas Sesiones", padding=8)
        right_frame.pack(side=tk.RIGHT, padx=(20, 0))
        
        # Widget de próximas sesiones
        sessions_grid = ttk.Frame(right_frame)
        sessions_grid.pack()
        
        ttk.Label(sessions_grid, text="🚀 Próxima:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(sessions_grid, textvariable=self.next_session_var, font=('Arial', 9)).grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        
        ttk.Label(sessions_grid, text="🕐 Hora:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Label(sessions_grid, textvariable=self.next_session_time_var, font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        
        # Panel de DRL (nueva sección)
        drl_frame = ttk.LabelFrame(left_frame, text="🤖 Sistema DRL Avanzado", padding=8)
        drl_frame.pack(fill=tk.X, pady=(10, 0))
        
        drl_grid = ttk.Frame(drl_frame)
        drl_grid.pack(fill=tk.X)
        
        # DRL habilitado/deshabilitado y estado
        ttk.Checkbutton(drl_grid, text="🤖 DRL Activo", variable=self.drl_enabled_var, 
                       command=self.toggle_drl).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(drl_grid, text="📊 Estado:", font=('Arial', 9, 'bold')).grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        ttk.Label(drl_grid, textvariable=self.drl_status_var, font=('Arial', 9)).grid(row=0, column=2, sticky=tk.W, padx=(0, 15))
        
        # Modo de trading DRL
        ttk.Label(drl_grid, text="🔄 Modo:", font=('Arial', 9, 'bold')).grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        ttk.Label(drl_grid, textvariable=self.drl_mode_var, font=('Arial', 9)).grid(row=0, column=4, sticky=tk.W, padx=(0, 15))
        
        # Segunda fila de métricas DRL
        # Confianza DRL
        ttk.Label(drl_grid, text="🎯 Confianza:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Label(drl_grid, textvariable=self.drl_confidence_var, font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, padx=(0, 15), pady=(5, 0))
        
        # Sharpe Ratio
        ttk.Label(drl_grid, text="📈 Sharpe:", font=('Arial', 9, 'bold')).grid(row=1, column=2, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Label(drl_grid, textvariable=self.drl_sharpe_var, font=('Arial', 9)).grid(row=1, column=3, sticky=tk.W, padx=(0, 15), pady=(5, 0))
        
        # Win Rate DRL
        ttk.Label(drl_grid, text="🏆 Win Rate:", font=('Arial', 9, 'bold')).grid(row=1, column=4, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Label(drl_grid, textvariable=self.drl_win_rate_var, font=('Arial', 9)).grid(row=1, column=5, sticky=tk.W, padx=(0, 15), pady=(5, 0))
        
        # Tercera fila de métricas DRL
        # Recompensa total
        ttk.Label(drl_grid, text="💰 Reward:", font=('Arial', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Label(drl_grid, textvariable=self.drl_total_reward_var, font=('Arial', 9)).grid(row=2, column=1, sticky=tk.W, padx=(0, 15), pady=(5, 0))
        
        # Episodios completados
        ttk.Label(drl_grid, text="🔄 Episodios:", font=('Arial', 9, 'bold')).grid(row=2, column=2, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Label(drl_grid, textvariable=self.drl_episodes_var, font=('Arial', 9)).grid(row=2, column=3, sticky=tk.W, padx=(0, 15), pady=(5, 0))
        
        # Botón para abrir dashboard DRL
        ttk.Button(drl_grid, text="📊 Dashboard DRL", 
                  command=self.open_drl_dashboard).grid(row=2, column=4, columnspan=2, sticky=tk.W, pady=(5, 0))
    
    def create_info_panel(self, parent):
        """Crear panel de información detallada"""
        info_frame = ttk.LabelFrame(parent, text="📋 Información del Sistema", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Notebook para diferentes secciones
        notebook = ttk.Notebook(info_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Pestaña de estado
        status_frame = ttk.Frame(notebook)
        notebook.add(status_frame, text="📊 Estado")
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=10, bg='#2d2d2d', fg='#ffffff', font=('Consolas', 9))
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # Pestaña de breakouts
        breakouts_frame = ttk.Frame(notebook)
        notebook.add(breakouts_frame, text="🚨 Breakouts")
        
        self.breakouts_text = scrolledtext.ScrolledText(breakouts_frame, height=10, bg='#2d2d2d', fg='#ffffff', font=('Consolas', 9))
        self.breakouts_text.pack(fill=tk.BOTH, expand=True)
        
        # Pestaña de sincronización
        sync_frame = ttk.Frame(notebook)
        notebook.add(sync_frame, text="🔄 Sincronización")
        
        self.sync_text = scrolledtext.ScrolledText(sync_frame, height=10, bg='#2d2d2d', fg='#ffffff', font=('Consolas', 9))
        self.sync_text.pack(fill=tk.BOTH, expand=True)
        
        # Pestaña de scalping
        scalping_frame = ttk.Frame(notebook)
        notebook.add(scalping_frame, text="🚀 Scalping")
        
        self.scalping_text = scrolledtext.ScrolledText(scalping_frame, height=10, bg='#2d2d2d', fg='#ffffff', font=('Consolas', 9))
        self.scalping_text.pack(fill=tk.BOTH, expand=True)
        
        # Pestaña de integración de portfolio (solo si está disponible)
        if PORTFOLIO_INTEGRATION_AVAILABLE:
            self.create_portfolio_tab(notebook)
    
    def create_controls_panel(self, parent):
        """Crear panel de controles y logs"""
        controls_frame = ttk.LabelFrame(parent, text="🎛️ Controles y Logs", padding=10)
        controls_frame.pack(fill=tk.X)
        
        # Botones de control
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(buttons_frame, text="🔄 Actualizar", command=self.manual_update).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="🚨 Test Breakout", command=self.test_breakout_alert).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="📝 Ver Logs", command=self.show_detailed_logs).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="⚙️ Configuración", command=self.show_config).pack(side=tk.LEFT, padx=(0, 5))
        
        # Área de logs
        self.logs_text = scrolledtext.ScrolledText(controls_frame, height=8, bg='#1a1a1a', fg='#cccccc', font=('Consolas', 8))
        self.logs_text.pack(fill=tk.X)
    
    def create_portfolio_tab(self, notebook):
        """Crear pestaña de integración de portfolio"""
        portfolio_frame = ttk.Frame(notebook)
        notebook.add(portfolio_frame, text="💼 Portfolio Integration")
        
        # Frame principal con scroll
        canvas = tk.Canvas(portfolio_frame, bg='#2d2d2d')
        scrollbar = ttk.Scrollbar(portfolio_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Panel de control
        control_frame = ttk.LabelFrame(scrollable_frame, text="🎛️ Control de Integración", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Estado de integración
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(status_frame, text="Estado:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.portfolio_status_label = ttk.Label(status_frame, text="🔴 Inactivo", font=('Arial', 10))
        self.portfolio_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Botones de control
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.start_portfolio_btn = ttk.Button(buttons_frame, text="🚀 Iniciar Integración", 
                                            command=self.start_portfolio_integration)
        self.start_portfolio_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_portfolio_btn = ttk.Button(buttons_frame, text="🛑 Detener Integración", 
                                           command=self.stop_portfolio_integration, state='disabled')
        self.stop_portfolio_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Configuración de estrategia
        strategy_frame = ttk.LabelFrame(control_frame, text="⚙️ Configuración de Estrategia", padding=5)
        strategy_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(strategy_frame, text="Estrategia:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        strategy_combo = ttk.Combobox(strategy_frame, textvariable=self.portfolio_strategy_var, 
                                    values=["momentum_weighted", "risk_adjusted", "confidence_scaled", 
                                           "dynamic_allocation", "sector_rotation"], state="readonly")
        strategy_combo.grid(row=0, column=1, sticky=tk.W)
        
        # Panel de métricas
        metrics_frame = ttk.LabelFrame(scrollable_frame, text="📊 Métricas de Portfolio", padding=10)
        metrics_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Grid de métricas
        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill=tk.X)
        
        # Las variables del portfolio ya están inicializadas en el constructor
        
        ttk.Label(metrics_grid, text="🔢 Señales Procesadas:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(metrics_grid, textvariable=self.portfolio_signals_count_var, font=('Arial', 9)).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(metrics_grid, text="📈 Performance:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        ttk.Label(metrics_grid, textvariable=self.portfolio_performance_var, font=('Arial', 9)).grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(metrics_grid, text="💼 Asignación Actual:", font=('Arial', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        ttk.Label(metrics_grid, textvariable=self.portfolio_allocation_var, font=('Arial', 9)).grid(row=2, column=1, sticky=tk.W, pady=(5, 0))
        
        # Panel de señales recientes
        signals_frame = ttk.LabelFrame(scrollable_frame, text="🚨 Señales Recientes", padding=10)
        signals_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.portfolio_signals_text = scrolledtext.ScrolledText(signals_frame, height=8, bg='#2d2d2d', 
                                                              fg='#ffffff', font=('Consolas', 8))
        self.portfolio_signals_text.pack(fill=tk.BOTH, expand=True)
        
        # Configurar canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def setup_callbacks(self):
        """Configurar callbacks de los sistemas"""
        try:
            # Callback para breakouts
            self.breakout_detector.add_observer(self.on_breakout_detected)
            
            # Callback para cambios de sincronización
            self.sync_manager.add_observer(self.on_sync_change)
            
        except Exception as e:
            SICAR_LOGGER.log_error("CALLBACKS_SETUP", str(e))
    
    def start_systems(self):
        """Iniciar todos los sistemas"""
        try:
            self.systems_running = True
            
            # Iniciar sincronización automática
            self.sync_manager.start_auto_sync()
            
            # Iniciar detección de breakouts
            self.breakout_detector.start_detection()
            
            # Iniciar hilo de actualización de UI
            self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
            self.update_thread.start()
            
            self.add_log("🟢 Todos los sistemas iniciados correctamente")
            
        except Exception as e:
            self.add_log(f"❌ Error iniciando sistemas: {e}")
            SICAR_LOGGER.log_error("SYSTEMS_START", str(e))
    
    def update_loop(self):
        """Bucle principal de actualización optimizado"""
        update_counter = 0
        last_session_check = 0
        
        while self.systems_running:
            try:
                current_time = time.time()
                
                # Actualización básica cada 5 segundos
                self.root.after(0, self._update_basic_ui)
                
                # Actualización completa cada 15 segundos (cada 3 ciclos)
                if update_counter % 3 == 0:
                    self.root.after(0, self._update_full_ui)
                
                # Verificación de sesión cada 60 segundos
                if current_time - last_session_check > 60:
                    self.root.after(0, self._update_session_info)
                    last_session_check = current_time
                
                update_counter += 1
                time.sleep(5)  # Actualizar cada 5 segundos
                
            except Exception as e:
                SICAR_LOGGER.log_error("UPDATE_LOOP", str(e))
                time.sleep(10)
    
    def _update_basic_ui(self):
        """Actualización básica de UI (solo métricas principales)"""
        try:
            trading_data = self.sync_manager.get_data()
            self._update_ui_variables(trading_data)
        except Exception as e:
            SICAR_LOGGER.log_error("BASIC_UI_UPDATE", str(e))
    
    def _update_full_ui(self):
        """Actualización completa de UI (incluye textos de estado)"""
        try:
            trading_data = self.sync_manager.get_data()
            self._update_status_texts(trading_data)
        except Exception as e:
            SICAR_LOGGER.log_error("FULL_UI_UPDATE", str(e))
    
    def _update_session_info(self):
        """Actualización de información de sesión (menos frecuente)"""
        try:
            self._update_next_sessions()
        except Exception as e:
            SICAR_LOGGER.log_error("SESSION_INFO_UPDATE", str(e))
    
    def update_status(self):
        """Actualizar estado del dashboard"""
        try:
            # Obtener datos de trading
            trading_data = self.sync_manager.get_data()
            
            # Actualizar variables de UI
            self._update_ui_variables(trading_data)
            
            # Actualizar textos de estado
            self._update_status_texts(trading_data)
            
        except Exception as e:
            SICAR_LOGGER.log_error("STATUS_UPDATE", str(e))
    
    def _update_ui_variables(self, trading_data):
        """Actualizar variables de la interfaz"""
        try:
            # Capital actual
            current_capital = trading_data.get('current_capital', CONFIG.PAPER_TRADING_CONFIG['initial_capital'])
            self.capital_var.set(f"${current_capital:,.2f}")
            
            # PnL
            initial_capital = trading_data.get('initial_capital', 0)
            pnl = current_capital - initial_capital
            pnl_pct = (pnl / initial_capital * 100) if initial_capital > 0 else 0
            self.pnl_var.set(f"${pnl:,.2f} ({pnl_pct:+.2f}%)")
            
            # Trades
            total_trades = trading_data.get('total_trades', 0)
            self.trades_var.set(str(total_trades))
            
            # Sesión actual
            current_session = trading_data.get('current_session', 'Ninguna')
            session_active = trading_data.get('session_active', False)
            session_status = f"{current_session} {'🟢' if session_active else '🔴'}"
            self.current_session_var.set(session_status)
            
            # Auto trading
            auto_trading = trading_data.get('auto_trading', False)
            if self.auto_trading_var.get() != auto_trading:
                self.auto_trading_var.set(auto_trading)
            
            # Próximas sesiones
            self._update_next_sessions()
            
            # Estadísticas de scalping
            self._update_scalping_statistics()
                
        except Exception as e:
            SICAR_LOGGER.log_error("UI_UPDATE", str(e))
    
    def _update_next_sessions(self):
        """Actualizar información de próximas sesiones"""
        try:
            import pytz
            from datetime import datetime, timedelta
            
            # Obtener hora actual EST
            est = pytz.timezone('US/Eastern')
            now_est = datetime.now(est)
            
            # Configuración de sesiones (igual que en session_detector.py)
            sessions = {
                'european': {'start': '03:00', 'name': 'Europea'},
                'american': {'start': '09:30', 'name': 'Americana'},
                'asian': {'start': '19:00', 'name': 'Asiática'}
            }
            
            # Encontrar la próxima sesión
            next_sessions = []
            
            for session_name, config in sessions.items():
                start_hour, start_minute = map(int, config['start'].split(':'))
                
                # Crear datetime para hoy
                session_today = now_est.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
                
                # Si ya pasó hoy, programar para mañana
                if session_today <= now_est:
                    session_next = session_today + timedelta(days=1)
                else:
                    session_next = session_today
                    
                # Calcular tiempo restante
                time_remaining = session_next - now_est
                total_minutes = int(time_remaining.total_seconds() // 60)
                
                next_sessions.append({
                    'name': config['name'],
                    'datetime': session_next,
                    'total_minutes': total_minutes
                })
            
            # Ordenar por tiempo restante
            next_sessions.sort(key=lambda x: x['total_minutes'])
            
            # Actualizar variables de UI con la próxima sesión
            if next_sessions:
                next_session = next_sessions[0]
                hours = next_session['total_minutes'] // 60
                minutes = next_session['total_minutes'] % 60
                
                self.next_session_var.set(next_session['name'])
                
                # Formatear tiempo restante
                if hours > 0:
                    time_str = f"{hours}h {minutes}m"
                else:
                    time_str = f"{minutes}m"
                
                # Mostrar hora de inicio y tiempo restante
                session_time = next_session['datetime'].strftime('%H:%M')
                self.next_session_time_var.set(f"{session_time} (en {time_str})")
            else:
                self.next_session_var.set("N/A")
                self.next_session_time_var.set("--:--")
                
        except Exception as e:
            SICAR_LOGGER.log_error("NEXT_SESSIONS_UPDATE", str(e))
            self.next_session_var.set("Error")
            self.next_session_time_var.set("--:--")
    
    def _update_status_texts(self, trading_data):
        """Actualizar textos de estado con límites de memoria"""
        try:
            # Estado general
            status_info = self._generate_status_info(trading_data)
            self._update_text_widget_safely(self.status_text, status_info)
            
            # Breakouts recientes
            breakouts_info = self._generate_breakouts_info()
            self._update_text_widget_safely(self.breakouts_text, breakouts_info)
            
            # Estado de sincronización
            sync_info = self._generate_sync_info()
            self._update_text_widget_safely(self.sync_text, sync_info)
            
            # Actualizar métricas de portfolio si está disponible
            if PORTFOLIO_INTEGRATION_AVAILABLE and hasattr(self, 'portfolio_signals_text'):
                self._update_portfolio_metrics()
            
        except Exception as e:
            SICAR_LOGGER.log_error("TEXT_UPDATE", str(e))
    
    def _update_text_widget_safely(self, text_widget, content, max_lines=100):
        """Actualizar widget de texto de forma segura con límites de memoria"""
        try:
            # Limpiar contenido anterior
            text_widget.delete(1.0, tk.END)
            
            # Insertar nuevo contenido
            text_widget.insert(tk.END, content)
            
            # Verificar y limitar número de líneas
            lines = text_widget.get(1.0, tk.END).split('\n')
            if len(lines) > max_lines:
                # Mantener solo las últimas max_lines líneas
                limited_content = '\n'.join(lines[-max_lines:])
                text_widget.delete(1.0, tk.END)
                text_widget.insert(tk.END, limited_content)
            
            # Scroll automático al final
            text_widget.see(tk.END)
            
        except Exception as e:
            SICAR_LOGGER.log_error("TEXT_WIDGET_UPDATE", str(e))
    
    def _generate_status_info(self, trading_data) -> str:
        """Generar información de estado"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            info = f"""🕐 Última actualización: {current_time}

📊 ESTADO DEL TRADING:
   • Auto Trading: {'🟢 Activado' if trading_data.get('auto_trading') else '🔴 Desactivado'}
   • Capital inicial: ${trading_data.get('initial_capital', 0):,.2f}
   • Capital actual: ${trading_data.get('current_capital', 0):,.2f}
   • Trades totales: {trading_data.get('total_trades', 0)}
   • Posiciones abiertas: {len(trading_data.get('positions', []))}

📅 SESIÓN ACTUAL:
   • Nombre: {trading_data.get('current_session', 'Ninguna')}
   • Estado: {'🟢 Activa' if trading_data.get('session_active') else '🔴 Inactiva'}
   • Última sincronización: {trading_data.get('last_sync', 'N/A')}

🔧 SISTEMAS:
   • Detector de breakouts: {'🟢 Activo' if self.breakout_detector.running else '🔴 Inactivo'}
   • Sincronización: {'🟢 Activa' if self.sync_manager.running else '🔴 Inactiva'}
   • Observadores: {len(self.sync_manager.observers)}
"""
            return info
            
        except Exception as e:
            return f"Error generando sincronización: {e}"
    
    def _update_portfolio_metrics(self):
        """Actualizar métricas de portfolio en tiempo real"""
        if not PORTFOLIO_INTEGRATION_AVAILABLE:
            return
            
        try:
            # Actualizar contadores y métricas
            self.portfolio_signals_count_var.set(str(self.portfolio_signals_count))
            
            # Formatear performance
            if self.portfolio_performance and isinstance(self.portfolio_performance, (int, float)):
                perf_text = f"{self.portfolio_performance:.2%}"
                self.portfolio_performance_var.set(perf_text)
            else:
                self.portfolio_performance_var.set("0.00%")
            
            # Formatear allocation
            if self.portfolio_allocation and isinstance(self.portfolio_allocation, dict):
                # Mostrar solo los primeros 3 activos con mayor asignación
                sorted_allocation = sorted(self.portfolio_allocation.items(), 
                                         key=lambda x: x[1], reverse=True)[:3]
                allocation_text = ", ".join([f"{symbol}: {weight:.1%}" 
                                           for symbol, weight in sorted_allocation 
                                           if isinstance(weight, (int, float))])
                self.portfolio_allocation_var.set(allocation_text if allocation_text else "Sin asignación")
            else:
                self.portfolio_allocation_var.set("Sin asignación")
            
            # Actualizar estado de integración
            if hasattr(self, 'portfolio_integrator') and self.portfolio_integrator:
                status = "🟢 Activa" if self.portfolio_integration_active else "🔴 Inactiva"
            else:
                status = "🔴 No iniciada"
            
            # Actualizar tanto la variable como el label si existen
            if hasattr(self, 'portfolio_status_var'):
                self.portfolio_status_var.set(status)
            if hasattr(self, 'portfolio_status_label'):
                self.portfolio_status_label.config(text=status)
            
        except Exception as e:
            SICAR_LOGGER.log_error("PORTFOLIO_METRICS_UPDATE", str(e))
    
    def _generate_breakouts_info(self) -> str:
        """Generar información de breakouts"""
        try:
            recent_signals = self.breakout_detector.get_recent_signals(hours=24)
            
            if not recent_signals:
                return "📈 No hay breakouts detectados en las últimas 24 horas."
            
            info = f"📈 BREAKOUTS RECIENTES ({len(recent_signals)}):\n\n"
            
            for signal in recent_signals[-10:]:  # Últimos 10
                timestamp = signal.timestamp.strftime("%H:%M:%S")
                direction = "📈" if signal.breakout_type.value == "bullish" else "📉"
                strength_emoji = {
                    "weak": "🟡",
                    "moderate": "🟠", 
                    "strong": "🔴",
                    "very_strong": "🟣"
                }.get(signal.strength.value, "⚪")
                
                info += f"{timestamp} | {direction} {signal.symbol}\n"
                info += f"   Fuerza: {strength_emoji} {signal.strength.value.title()}\n"
                info += f"   Confianza: {signal.confidence:.1%}\n"
                info += f"   Precio: ${signal.price:.4f}\n"
                info += f"   Volumen: {signal.volume_ratio:.1f}x\n\n"
            
            return info
            
        except Exception as e:
            return f"Error generando breakouts: {e}"
    
    def _generate_sync_info(self) -> str:
        """Generar información de sincronización"""
        try:
            sync_status = self.sync_manager.get_sync_status()
            
            info = f"""🔄 ESTADO DE SINCRONIZACIÓN:

📁 ARCHIVO:
   • Existe: {'✅' if sync_status['file_exists'] else '❌'}
   • Última modificación: {sync_status['last_modified'] or 'N/A'}
   • Tamaño del cache: {sync_status['cache_size']} campos

⚙️ CONFIGURACIÓN:
   • Auto-sync: {'🟢 Activado' if sync_status['auto_sync_enabled'] else '🔴 Desactivado'}
   • Sync ejecutándose: {'🟢 Sí' if sync_status['sync_running'] else '🔴 No'}
   • Observadores: {sync_status['observers_count']}

📊 DATOS ACTUALES:
"""
            
            # Agregar datos clave del cache
            data = self.sync_manager.get_data()
            for key in ['auto_trading', 'current_capital', 'total_trades', 'session_active']:
                value = data.get(key, 'N/A')
                info += f"   • {key}: {value}\n"
            
            return info
            
        except Exception as e:
            return f"Error generando sync info: {e}"
    
    def toggle_auto_trading(self):
        """Alternar auto trading"""
        try:
            enabled = self.auto_trading_var.get()
            reason = "Activado desde dashboard" if enabled else "Desactivado desde dashboard"
            
            self.sync_manager.set_auto_trading(enabled, reason)
            self.add_log(f"🤖 Auto Trading {'activado' if enabled else 'desactivado'}")
            
        except Exception as e:
            self.add_log(f"❌ Error cambiando auto trading: {e}")
            SICAR_LOGGER.log_error("AUTO_TRADING_TOGGLE", str(e))
    
    def manual_update(self):
        """Actualización manual"""
        try:
            self.update_status()
            self.add_log("🔄 Actualización manual completada")
        except Exception as e:
            self.add_log(f"❌ Error en actualización manual: {e}")
    
    def test_breakout_alert(self):
        """Probar alerta de breakout"""
        try:
            # Crear señal de prueba
            test_signal = BreakoutSignal(
                symbol="ETHUSDT",
                timestamp=datetime.now(),
                breakout_type=BreakoutType.BULLISH,
                strength=BreakoutStrength.STRONG,
                confidence=0.85,
                price=2150.50,
                volume=1500000,
                resistance_level=2145.00,
                support_level=2100.00,
                price_change_pct=1.25,
                volume_ratio=2.3,
                candle_pattern="strong_bullish",
                technical_indicators={"rsi": 65, "macd": 0.5}
            )
            
            self.on_breakout_detected(test_signal)
            self.add_log("🚨 Alerta de breakout de prueba enviada")
            
        except Exception as e:
            self.add_log(f"❌ Error en test de breakout: {e}")
    
    def on_breakout_detected(self, signal: BreakoutSignal):
        """Callback para breakout detectado"""
        try:
            direction = "📈 ALCISTA" if signal.breakout_type.value == "bullish" else "📉 BAJISTA"
            message = f"🚨 BREAKOUT {direction} - {signal.symbol} - Confianza: {signal.confidence:.1%}"
            
            self.add_log(message)
            
            # Ejecutar trading automático si está habilitado
            if self.auto_trading_var.get() and self.paper_engine:
                self._execute_auto_trade(signal)
            
            # Mostrar información de breakout en consola (sin popup)
            if signal.strength.value in ["strong", "very_strong"]:
                self._log_breakout_to_console(signal)
                
        except Exception as e:
            SICAR_LOGGER.log_error("BREAKOUT_CALLBACK", str(e))
    
    def _log_breakout_to_console(self, signal: BreakoutSignal):
        """Mostrar información de breakout en la consola del dashboard"""
        try:
            direction = "ALCISTA" if signal.breakout_type.value == "bullish" else "BAJISTA"
            
            # Crear mensaje detallado para la consola
            console_message = f"""🚨 BREAKOUT {signal.strength.value.upper()} DETECTADO 🚨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Símbolo: {signal.symbol}
📈 Dirección: {direction}
⚡ Fuerza: {signal.strength.value.title()}
🎯 Confianza: {signal.confidence:.1%}
💰 Precio: ${signal.price:.4f}
📊 Cambio: {signal.price_change_pct:+.2f}%
📈 Volumen: {signal.volume_ratio:.1f}x promedio
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
            
            # Mostrar en la consola del dashboard
            self.add_log(console_message)
            
            # También actualizar el texto de breakouts
            trading_data = self.sync_manager.get_data()
            self._update_status_texts(trading_data)
            
        except Exception as e:
            SICAR_LOGGER.log_error("BREAKOUT_CONSOLE", str(e))
    
    def _execute_auto_trade(self, signal: BreakoutSignal):
        """Ejecutar trade automático basado en la señal de breakout"""
        try:
            # Verificar que estamos en una sesión activa
            current_session = self.session_detector.get_current_session()
            if not current_session:
                self.add_log(f"⚠️ No hay sesión activa - Trade cancelado para {signal.symbol}")
                return
            
            # Determinar dirección del trade
            if signal.breakout_type.value == "bullish":
                side = "buy"  # LONG = buy
                direction_text = "LONG"
            else:
                side = "sell"  # SHORT = sell
                direction_text = "SHORT"
            
            # Obtener resumen del portfolio
            portfolio_summary = self.paper_engine.get_portfolio_summary()
            
            # Calcular cantidad basada en riesgo configurado
            risk_per_trade = CONFIG.PAPER_TRADING_CONFIG['risk_per_trade_pct'] * 100  # 2% del capital
            current_capital = portfolio_summary['current_capital']
            risk_amount = current_capital * (risk_per_trade / 100)
            
            # Calcular cantidad de la orden (simplificado)
            quantity = risk_amount / signal.price
            
            # Verificar cantidad mínima (apropiada para base de $200)
            min_quantity = 0.00001  # Cantidad mínima muy baja para capital pequeño
            if quantity < min_quantity:
                self.add_log(f"⚠️ Cantidad muy pequeña para {signal.symbol}: {quantity:.6f}")
                return
            
            # Ejecutar la orden
            order_result = self.paper_engine.place_order(
                symbol=signal.symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=signal.price  # Precio actual para orden de mercado
            )
            
            if order_result:
                self.add_log(f"✅ ORDEN COLOCADA: {direction_text} {signal.symbol}")
                self.add_log(f"   🆔 Order ID: {order_result}")
                self.add_log(f"   💰 Cantidad: {quantity:.6f}")
                self.add_log(f"   💲 Precio: ${signal.price:.4f}")
                self.add_log(f"   🎯 Confianza: {signal.confidence:.1%}")
                
                # Procesar datos de mercado para ejecutar la orden
                market_data = {signal.symbol: signal.price}
                self.paper_engine.process_market_data(market_data)
                self.add_log(f"   ✅ Orden procesada con datos de mercado")
                
                # Actualizar métricas si están disponibles
                self.update_trading_metrics()
                
            else:
                self.add_log(f"❌ Error ejecutando trade para {signal.symbol}")
                
        except Exception as e:
            SICAR_LOGGER.log_error("AUTO_TRADE", str(e))
            self.add_log(f"❌ Error en auto-trading: {e}")
    
    def update_trading_metrics(self):
        """Actualizar métricas de trading"""
        try:
            if not self.paper_engine:
                return
                
            # Obtener métricas del paper trading engine
            balance = self.paper_engine.get_balance()
            positions = self.paper_engine.get_positions()
            pnl = self.paper_engine.get_total_pnl()
            
            # Actualizar variables de la UI si existen
            if hasattr(self, 'balance_var'):
                self.balance_var.set(f"${balance:.2f}")
            if hasattr(self, 'pnl_var'):
                self.pnl_var.set(f"${pnl:.2f}")
            if hasattr(self, 'positions_var'):
                self.positions_var.set(f"{len(positions)} posiciones")
                
            # Log de actualización
            self.add_log(f"📊 Métricas actualizadas - Balance: ${balance:.2f}, PnL: ${pnl:.2f}")
            
            # Actualizar métricas DRL si está habilitado
            if self.drl_enabled_var.get():
                self.update_drl_metrics()
            
        except Exception as e:
            SICAR_LOGGER.log_error("TRADING_METRICS", str(e))
    
    def on_sync_change(self, changes: Dict[str, Any]):
        """Callback para cambios de sincronización"""
        try:
            for field, change_info in changes.items():
                old_val = change_info['old']
                new_val = change_info['new']
                self.add_log(f"🔄 {field}: {old_val} → {new_val}")
                
        except Exception as e:
            SICAR_LOGGER.log_error("SYNC_CALLBACK", str(e))
    
    def show_detailed_logs(self):
        """Mostrar logs detallados"""
        try:
            log_window = tk.Toplevel(self.root)
            log_window.title("📝 Logs Detallados")
            log_window.geometry("800x600")
            log_window.configure(bg='#1e1e1e')
            
            # Notebook para diferentes tipos de logs
            notebook = ttk.Notebook(log_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Cargar diferentes logs
            log_types = ['main', 'trading', 'breakouts', 'sessions', 'errors']
            
            for log_type in log_types:
                frame = ttk.Frame(notebook)
                notebook.add(frame, text=log_type.title())
                
                text_widget = scrolledtext.ScrolledText(
                    frame, 
                    bg='#1a1a1a', 
                    fg='#cccccc',
                    font=('Consolas', 9)
                )
                text_widget.pack(fill=tk.BOTH, expand=True)
                
                # Cargar contenido del log
                try:
                    log_file_path = CONFIG.get_log_file_path(log_type)
                    log_file = Path(log_file_path)
                    if log_file.exists():
                        with open(log_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        text_widget.insert(tk.END, content)
                    else:
                        text_widget.insert(tk.END, f"Log {log_type} no encontrado.")
                except Exception as e:
                    text_widget.insert(tk.END, f"Error cargando log {log_type}: {e}")
            
        except Exception as e:
            self.add_log(f"❌ Error mostrando logs: {e}")
    
    def show_config(self):
        """Mostrar configuración interactiva"""
        try:
            config_window = tk.Toplevel(self.root)
            config_window.title("⚙️ Configuración del Sistema")
            config_window.geometry("750x650")
            config_window.configure(bg='#1e1e1e')
            config_window.resizable(True, True)
            
            # Frame principal
            main_frame = ttk.Frame(config_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
            
            # Título
            title_label = ttk.Label(main_frame, text="⚙️ Configuración del Sistema SICAR", 
                                   font=('Arial', 14, 'bold'))
            title_label.pack(pady=(0, 15))
            
            # Notebook para diferentes secciones
            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            
            # Variables para almacenar valores
            self.config_vars = {}
            
            # Crear pestañas de configuración
            self._create_auto_trading_tab(notebook)
            self._create_breakouts_tab(notebook)
            self._create_sync_tab(notebook)
            self._create_paper_trading_tab(notebook)
            
            # Frame de botones - SIEMPRE VISIBLE
            buttons_frame = ttk.Frame(main_frame)
            buttons_frame.pack(fill=tk.X, side=tk.BOTTOM)
            
            # Separador visual
            separator = ttk.Separator(buttons_frame, orient='horizontal')
            separator.pack(fill=tk.X, pady=(0, 10))
            
            # Contenedor de botones
            button_container = ttk.Frame(buttons_frame)
            button_container.pack(fill=tk.X)
            
            # Botones con estilo mejorado
            save_btn = ttk.Button(button_container, text="💾 Guardar Cambios", 
                                 command=lambda: self._save_config_changes(config_window))
            save_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            restore_btn = ttk.Button(button_container, text="🔄 Restaurar Defaults", 
                                   command=self._restore_config_defaults)
            restore_btn.pack(side=tk.LEFT, padx=(0, 10))
            
            cancel_btn = ttk.Button(button_container, text="❌ Cancelar", 
                                  command=config_window.destroy)
            cancel_btn.pack(side=tk.RIGHT)
            
            # Información adicional
            info_label = ttk.Label(button_container, 
                                 text="💡 Los cambios se aplicarán inmediatamente al guardar", 
                                 font=('Arial', 9), foreground='gray')
            info_label.pack(side=tk.LEFT, padx=(20, 0))
            
            # Centrar ventana
            config_window.transient(self.root)
            config_window.grab_set()
            
            # Posicionar en el centro de la pantalla principal
            config_window.update_idletasks()
            x = (config_window.winfo_screenwidth() // 2) - (config_window.winfo_width() // 2)
            y = (config_window.winfo_screenheight() // 2) - (config_window.winfo_height() // 2)
            config_window.geometry(f"+{x}+{y}")
            
        except Exception as e:
            self.add_log(f"❌ Error mostrando configuración: {e}")
    
    def _create_auto_trading_tab(self, notebook):
        """Crear pestaña de configuración de auto trading"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🤖 Auto Trading")
        
        # Auto trading por defecto
        ttk.Label(frame, text="Activado por defecto:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['auto_trading_default'] = tk.BooleanVar(value=CONFIG.AUTO_TRADING_DEFAULT)
        ttk.Checkbutton(frame, variable=self.config_vars['auto_trading_default']).grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Información adicional
        info_text = """
ℹ️ Configuración de Auto Trading:

• Activado por defecto: Determina si el auto trading se inicia automáticamente
  al arrancar el sistema.

• Esta configuración afecta el comportamiento inicial del dashboard.
        """
        
        info_label = ttk.Label(frame, text=info_text, font=('Arial', 9), foreground='gray')
        info_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=10, pady=10)
    
    def _create_breakouts_tab(self, notebook):
        """Crear pestaña de configuración de breakouts"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="📊 Breakouts")
        
        # Sensibilidad
        ttk.Label(frame, text="Sensibilidad:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['breakout_sensitivity'] = tk.DoubleVar(value=CONFIG.BREAKOUT_DETECTION['sensitivity'])
        sensitivity_scale = ttk.Scale(frame, from_=0.1, to=1.0, variable=self.config_vars['breakout_sensitivity'], orient=tk.HORIZONTAL)
        sensitivity_scale.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)
        sensitivity_label = ttk.Label(frame, text="")
        sensitivity_label.grid(row=0, column=2, padx=5)
        
        # Volumen mínimo
        ttk.Label(frame, text="Volumen mínimo (x):", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['min_volume_ratio'] = tk.DoubleVar(value=CONFIG.BREAKOUT_DETECTION['min_volume_ratio'])
        volume_entry = ttk.Entry(frame, textvariable=self.config_vars['min_volume_ratio'], width=10)
        volume_entry.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Cambio mínimo de precio
        ttk.Label(frame, text="Cambio mínimo (%):", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['min_price_change_pct'] = tk.DoubleVar(value=CONFIG.BREAKOUT_DETECTION['min_price_change_pct'] * 100)
        price_change_entry = ttk.Entry(frame, textvariable=self.config_vars['min_price_change_pct'], width=10)
        price_change_entry.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Intervalo de detección
        ttk.Label(frame, text="Intervalo detección (s):", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['detection_interval'] = tk.IntVar(value=CONFIG.BREAKOUT_DETECTION['detection_interval'])
        interval_entry = ttk.Entry(frame, textvariable=self.config_vars['detection_interval'], width=10)
        interval_entry.grid(row=3, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Actualizar etiqueta de sensibilidad
        def update_sensitivity_label(*args):
            value = self.config_vars['breakout_sensitivity'].get()
            sensitivity_label.config(text=f"{value:.1%}")
        
        self.config_vars['breakout_sensitivity'].trace('w', update_sensitivity_label)
        update_sensitivity_label()
        
        frame.columnconfigure(1, weight=1)
    
    def _create_sync_tab(self, notebook):
        """Crear pestaña de configuración de sincronización"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🔄 Sincronización")
        
        # Auto-sync habilitado
        ttk.Label(frame, text="Auto-sync habilitado:", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['auto_sync_enabled'] = tk.BooleanVar(value=CONFIG.SYNC_CONFIG['auto_sync_enabled'])
        ttk.Checkbutton(frame, variable=self.config_vars['auto_sync_enabled']).grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Intervalo de sincronización
        ttk.Label(frame, text="Intervalo (segundos):", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['sync_interval'] = tk.IntVar(value=CONFIG.SYNC_CONFIG['sync_interval'])
        sync_interval_entry = ttk.Entry(frame, textvariable=self.config_vars['sync_interval'], width=10)
        sync_interval_entry.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
    
    def _create_paper_trading_tab(self, notebook):
        """Crear pestaña de configuración de paper trading"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="💰 Paper Trading")
        
        # Capital inicial
        ttk.Label(frame, text="Capital inicial ($):", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['initial_capital'] = tk.DoubleVar(value=CONFIG.PAPER_TRADING_CONFIG['initial_capital'])
        capital_entry = ttk.Entry(frame, textvariable=self.config_vars['initial_capital'], width=15)
        capital_entry.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Comisión
        ttk.Label(frame, text="Comisión:", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['commission_rate'] = tk.DoubleVar(value=CONFIG.PAPER_TRADING_CONFIG['commission_rate'])
        commission_entry = ttk.Entry(frame, textvariable=self.config_vars['commission_rate'], width=10)
        commission_entry.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Slippage
        ttk.Label(frame, text="Slippage (%):", font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)
        self.config_vars['slippage_base'] = tk.DoubleVar(value=CONFIG.PAPER_TRADING_CONFIG['slippage_base'] * 100)  # Convertir a porcentaje para mostrar
        slippage_entry = ttk.Entry(frame, textvariable=self.config_vars['slippage_base'], width=10)
        slippage_entry.grid(row=2, column=1, sticky=tk.W, padx=10, pady=5)
    
    def _save_config_changes(self, config_window):
        """Guardar cambios de configuración"""
        try:
            # Validar valores antes de guardar
            validation_errors = []
            
            # Validar sensibilidad de breakout
            sensitivity = self.config_vars['breakout_sensitivity'].get()
            if not (0.1 <= sensitivity <= 1.0):
                validation_errors.append("La sensibilidad debe estar entre 0.1 y 1.0")
            
            # Validar volumen mínimo
            min_volume = self.config_vars['min_volume_ratio'].get()
            if min_volume <= 0:
                validation_errors.append("El volumen mínimo debe ser mayor que 0")
            
            # Validar cambio mínimo de precio
            min_price_change = self.config_vars['min_price_change_pct'].get()
            if not (0.01 <= min_price_change <= 10.0):
                validation_errors.append("El cambio mínimo de precio debe estar entre 0.01% y 10%")
            
            # Validar intervalo de detección
            detection_interval = self.config_vars['detection_interval'].get()
            if not (5 <= detection_interval <= 300):
                validation_errors.append("El intervalo de detección debe estar entre 5 y 300 segundos")
            
            # Validar intervalo de sincronización
            sync_interval = self.config_vars['sync_interval'].get()
            if not (10 <= sync_interval <= 3600):
                validation_errors.append("El intervalo de sincronización debe estar entre 10 y 3600 segundos")
            
            # Validar capital inicial
            initial_capital = self.config_vars['initial_capital'].get()
            if initial_capital <= 0:
                validation_errors.append("El capital inicial debe ser mayor que 0")
            
            # Si hay errores de validación, mostrarlos
            if validation_errors:
                error_message = "Errores de validación:\n\n" + "\n".join(f"• {error}" for error in validation_errors)
                messagebox.showerror("Errores de Validación", error_message)
                return
            
            # Actualizar configuración en memoria
            CONFIG.AUTO_TRADING_DEFAULT = self.config_vars['auto_trading_default'].get()
            
            CONFIG.BREAKOUT_DETECTION['sensitivity'] = sensitivity
            CONFIG.BREAKOUT_DETECTION['min_volume_ratio'] = min_volume
            CONFIG.BREAKOUT_DETECTION['min_price_change_pct'] = min_price_change / 100
            CONFIG.BREAKOUT_DETECTION['detection_interval'] = detection_interval
            
            CONFIG.SYNC_CONFIG['auto_sync_enabled'] = self.config_vars['auto_sync_enabled'].get()
            CONFIG.SYNC_CONFIG['sync_interval'] = sync_interval
            
            CONFIG.PAPER_TRADING_CONFIG['initial_capital'] = initial_capital
            CONFIG.PAPER_TRADING_CONFIG['commission_rate'] = self.config_vars['commission_rate'].get()
            CONFIG.PAPER_TRADING_CONFIG['slippage_base'] = self.config_vars['slippage_base'].get() / 100  # Convertir de porcentaje a decimal
            
            # Aplicar cambios a los sistemas activos
            self.breakout_detector.update_sensitivity(CONFIG.BREAKOUT_DETECTION['sensitivity'])
            
            # Actualizar variables de la interfaz
            self.auto_trading_var.set(CONFIG.AUTO_TRADING_DEFAULT)
            self.capital_var.set(f"${CONFIG.PAPER_TRADING_CONFIG['initial_capital']:,.2f}")
            
            # Guardar configuración permanentemente en archivo
            CONFIG.save_config_to_file()
            
            # Recargar configuración desde archivo para asegurar persistencia
            CONFIG.load_config_from_file()
            
            # Actualizar variables de la interfaz con los valores recargados
            self.auto_trading_var.set(CONFIG.AUTO_TRADING_DEFAULT)
            self.capital_var.set(f"${CONFIG.PAPER_TRADING_CONFIG['initial_capital']:,.2f}")
            
            # Sincronizar archivo de sesión con nueva configuración de capital
            self._sync_session_with_config()
            
            self.add_log("✅ Configuración guardada, recargada y aplicada exitosamente")
            
            # Mostrar resumen de cambios
            summary = f"""✅ Configuración Guardada Exitosamente

🤖 Auto Trading: {'Activado' if CONFIG.AUTO_TRADING_DEFAULT else 'Desactivado'}
📊 Sensibilidad Breakout: {sensitivity:.1%}
💰 Capital Inicial: ${initial_capital:,.2f}
🔄 Auto-sync: {'Activado' if CONFIG.SYNC_CONFIG['auto_sync_enabled'] else 'Desactivado'}

Los cambios han sido aplicados inmediatamente al sistema."""
            
            messagebox.showinfo("Configuración Guardada", summary)
            config_window.destroy()
            
        except Exception as e:
            error_msg = f"Error guardando configuración: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def _restore_config_defaults(self):
        """Restaurar configuración por defecto"""
        try:
            # Restaurar valores por defecto
            self.config_vars['auto_trading_default'].set(True)
            self.config_vars['breakout_sensitivity'].set(0.7)
            self.config_vars['min_volume_ratio'].set(1.5)
            self.config_vars['min_price_change_pct'].set(0.5)
            self.config_vars['detection_interval'].set(30)
            self.config_vars['auto_sync_enabled'].set(True)
            self.config_vars['sync_interval'].set(60)
            self.config_vars['initial_capital'].set(10000.0)
            self.config_vars['commission_rate'].set(0.001)
            self.config_vars['slippage_base'].set(0.05)
            
            self.add_log("🔄 Configuración restaurada a valores por defecto")
            
        except Exception as e:
            self.add_log(f"❌ Error restaurando configuración: {e}")
    
    def add_log(self, message: str):
        """Agregar mensaje a logs con limpieza automática mejorada"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            self.logs_text.insert(tk.END, log_message)
            
            # Limpieza automática más eficiente
            self._cleanup_text_widget(self.logs_text, max_lines=150)
            
            self.logs_text.see(tk.END)
                
        except Exception as e:
            print(f"Error agregando log: {e}")
    
    def _cleanup_text_widget(self, text_widget, max_lines=150):
        """Limpiar widget de texto manteniendo solo las últimas líneas"""
        try:
            # Obtener número de líneas actual
            current_lines = int(text_widget.index('end-1c').split('.')[0])
            
            if current_lines > max_lines:
                # Calcular cuántas líneas eliminar
                lines_to_delete = current_lines - max_lines
                
                # Eliminar líneas desde el principio
                text_widget.delete(1.0, f"{lines_to_delete + 1}.0")
                
        except Exception as e:
            SICAR_LOGGER.log_error("TEXT_WIDGET_CLEANUP", str(e))
    
    def _sync_session_with_config(self):
        """Sincronizar archivo de sesión con configuración actualizada"""
        try:
            # Actualizar datos de sesión con nueva configuración
            new_initial_capital = CONFIG.PAPER_TRADING_CONFIG['initial_capital']
            
            # Resetear sesión con nuevo capital
            session_data = {
                'initial_capital': new_initial_capital,
                'current_capital': new_initial_capital,
                'total_trades': 0,
                'auto_trading': CONFIG.AUTO_TRADING_DEFAULT
            }
            
            # Usar sync_manager para actualizar
            self.sync_manager.update_data(session_data)
            
            self.add_log(f"📊 Sesión sincronizada con nuevo capital: ${new_initial_capital:,.2f}")
            
        except Exception as e:
            SICAR_LOGGER.log_error("SESSION_SYNC", str(e))
            self.add_log(f"❌ Error sincronizando sesión: {str(e)}")

    def start_portfolio_integration(self):
        """Iniciar integración de portfolio"""
        if not PORTFOLIO_INTEGRATION_AVAILABLE:
            messagebox.showerror("Error", "Integración de portfolio no disponible")
            return
            
        try:
            if self.portfolio_integrator is None:
                # Crear integrador
                self.portfolio_integrator = BreakoutPortfolioIntegrator()
                
                # Configurar callback para señales
                self.portfolio_integrator.add_signal_callback(self.on_portfolio_signal)
            
            # Obtener estrategia seleccionada
            strategy_name = self.portfolio_strategy_var.get()
            strategy = BreakoutPortfolioStrategy[strategy_name.upper()]
            
            # Iniciar integración
            self.portfolio_integrator.start_integration(strategy)
            
            # Actualizar UI
            self.portfolio_integration_active.set(True)
            self.portfolio_status_label.config(text="🟢 Activo")
            self.start_portfolio_btn.config(state='disabled')
            self.stop_portfolio_btn.config(state='normal')
            
            self.add_log(f"🚀 Integración de portfolio iniciada con estrategia: {strategy_name}")
            self.add_portfolio_log(f"🚀 Integración iniciada - Estrategia: {strategy_name}")
            
        except Exception as e:
            error_msg = f"Error iniciando integración de portfolio: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def stop_portfolio_integration(self):
        """Detener integración de portfolio"""
        try:
            if self.portfolio_integrator:
                self.portfolio_integrator.stop_integration()
            
            # Actualizar UI
            self.portfolio_integration_active.set(False)
            self.portfolio_status_label.config(text="🔴 Inactivo")
            self.start_portfolio_btn.config(state='normal')
            self.stop_portfolio_btn.config(state='disabled')
            
            self.add_log("🛑 Integración de portfolio detenida")
            self.add_portfolio_log("🛑 Integración detenida")
            
        except Exception as e:
            error_msg = f"Error deteniendo integración de portfolio: {str(e)}"
            self.add_log(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def on_portfolio_signal(self, signal: BreakoutPortfolioSignal):
        """Callback para señales de portfolio"""
        try:
            # Actualizar contador de señales
            current_count = int(self.portfolio_signals_count.get())
            self.portfolio_signals_count.set(str(current_count + 1))
            
            # Actualizar performance (simulado)
            performance = signal.expected_return * 100
            self.portfolio_performance.set(f"{performance:.2f}%")
            
            # Actualizar asignación
            allocation_text = f"{signal.symbol}: {signal.recommended_allocation:.1%}"
            self.portfolio_allocation.set(allocation_text)
            
            # Agregar a log de señales
            timestamp = datetime.now().strftime("%H:%M:%S")
            signal_text = f"[{timestamp}] 🚨 {signal.symbol} | Confianza: {signal.confidence:.2f} | Asignación: {signal.recommended_allocation:.1%} | Retorno Esperado: {signal.expected_return:.2%}\n"
            
            self.add_portfolio_log(signal_text.strip())
            
        except Exception as e:
            SICAR_LOGGER.log_error("PORTFOLIO_SIGNAL", str(e))
    
    def add_portfolio_log(self, message: str):
        """Agregar mensaje a logs de portfolio"""
        try:
            if hasattr(self, 'portfolio_signals_text'):
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_message = f"[{timestamp}] {message}\n"
                
                self.portfolio_signals_text.insert(tk.END, log_message)
                self.portfolio_signals_text.see(tk.END)
                
                # Limitar líneas de log
                lines = self.portfolio_signals_text.get(1.0, tk.END).split('\n')
                if len(lines) > 50:
                    self.portfolio_signals_text.delete(1.0, f"{len(lines)-50}.0")
                    
        except Exception as e:
            SICAR_LOGGER.log_error("PORTFOLIO_LOG", str(e))

    def _update_scalping_statistics(self):
        """Actualizar estadísticas de scalping"""
        try:
            if self.paper_engine and hasattr(self.paper_engine, 'get_scalping_statistics'):
                scalping_stats = self.paper_engine.get_scalping_statistics()
                
                # Actualizar variables de UI
                self.scalping_trades_var.set(str(scalping_stats.get('total_scalping_trades', 0)))
                
                # PnL de scalping
                scalping_pnl = scalping_stats.get('scalping_pnl', 0.0)
                self.scalping_pnl_var.set(f"${scalping_pnl:,.2f}")
                
                # Win Rate
                win_rate = scalping_stats.get('scalping_win_rate', 0.0)
                self.scalping_win_rate_var.set(f"{win_rate:.1f}%")
                
                # Sesiones de scalping
                total_sessions = scalping_stats.get('total_scalping_sessions', 0)
                self.scalping_sessions_var.set(str(total_sessions))
                
                # Posiciones activas (simulado - en un sistema real sería dinámico)
                active_positions = 0  # Se actualizaría desde el ScalpingEngine
                self.scalping_active_positions_var.set(str(active_positions))
                
                # Actualizar log de scalping
                self._update_scalping_log(scalping_stats)
                
        except Exception as e:
            SICAR_LOGGER.log_error("SCALPING_STATS_UPDATE", str(e))
    
    def _update_scalping_log(self, scalping_stats):
        """Actualizar log de scalping en la pestaña correspondiente"""
        try:
            if hasattr(self, 'scalping_text'):
                # Limpiar texto anterior
                self.scalping_text.delete(1.0, tk.END)
                
                # Información general
                self.scalping_text.insert(tk.END, "🚀 ESTADÍSTICAS DE SCALPING AUTOMÁTICO\n")
                self.scalping_text.insert(tk.END, "=" * 50 + "\n\n")
                
                # Métricas principales
                self.scalping_text.insert(tk.END, f"📊 Total de Trades: {scalping_stats.get('total_scalping_trades', 0)}\n")
                self.scalping_text.insert(tk.END, f"💼 Sesiones Completadas: {scalping_stats.get('total_scalping_sessions', 0)}\n")
                self.scalping_text.insert(tk.END, f"💰 PnL Total: ${scalping_stats.get('scalping_pnl', 0.0):,.2f}\n")
                self.scalping_text.insert(tk.END, f"🎯 Win Rate: {scalping_stats.get('scalping_win_rate', 0.0):.1f}%\n")
                self.scalping_text.insert(tk.END, f"✅ Sesiones Ganadoras: {scalping_stats.get('winning_sessions', 0)}\n")
                self.scalping_text.insert(tk.END, f"❌ Sesiones Perdedoras: {scalping_stats.get('losing_sessions', 0)}\n")
                
                avg_pnl = scalping_stats.get('avg_pnl_per_session', 0.0)
                self.scalping_text.insert(tk.END, f"📈 PnL Promedio por Sesión: ${avg_pnl:.2f}\n\n")
                
                # Configuración actual
                self.scalping_text.insert(tk.END, "⚙️ CONFIGURACIÓN ACTUAL\n")
                self.scalping_text.insert(tk.END, "-" * 30 + "\n")
                
                scalping_config = CONFIG.SCALPING_CONFIG
                self.scalping_text.insert(tk.END, f"🔄 Estado: {'🟢 Activo' if scalping_config.get('enabled', False) else '🔴 Inactivo'}\n")
                self.scalping_text.insert(tk.END, f"⏱️ Duración: {scalping_config.get('operation_duration_minutes', 5)} minutos\n")
                self.scalping_text.insert(tk.END, f"🎯 Confianza Mínima: {scalping_config.get('min_confidence_threshold', 0.55):.3f}\n")
                self.scalping_text.insert(tk.END, f"📈 Take Profit: {scalping_config.get('take_profit_percentage', 2.0)}%\n")
                self.scalping_text.insert(tk.END, f"📉 Stop Loss: {scalping_config.get('stop_loss_percentage', 1.0)}%\n")
                self.scalping_text.insert(tk.END, f"💵 Tamaño Posición: ${scalping_config.get('position_size_usd', 100.0)}\n")
                self.scalping_text.insert(tk.END, f"🔢 Posiciones Máximas: {scalping_config.get('max_concurrent_positions', 3)}\n")
                
                # Símbolos permitidos
                allowed_symbols = scalping_config.get('allowed_symbols', [])
                self.scalping_text.insert(tk.END, f"📋 Símbolos: {', '.join(allowed_symbols)}\n\n")
                
                # Estado del sistema
                self.scalping_text.insert(tk.END, "📊 ESTADO DEL SISTEMA\n")
                self.scalping_text.insert(tk.END, "-" * 25 + "\n")
                self.scalping_text.insert(tk.END, f"🕐 Última Actualización: {datetime.now().strftime('%H:%M:%S')}\n")
                self.scalping_text.insert(tk.END, f"🔄 Integración: {'✅ Activa' if hasattr(self.breakout_detector, 'scalping_engine') else '❌ No disponible'}\n")
                
                # Auto-scroll al final
                self.scalping_text.see(tk.END)
                
        except Exception as e:
            SICAR_LOGGER.log_error("SCALPING_LOG_UPDATE", str(e))
    
    def toggle_scalping(self):
        """Alternar estado del scalping automático"""
        try:
            new_state = self.scalping_enabled_var.get()
            
            # Actualizar configuración
            CONFIG.SCALPING_CONFIG['enabled'] = new_state
            CONFIG.save_config_to_file()
            
            # Notificar al sistema
            if hasattr(self.breakout_detector, 'scalping_engine') and self.breakout_detector.scalping_engine:
                if new_state:
                    self.add_log("🚀 Scalping automático ACTIVADO")
                    SICAR_LOGGER.log_alert("SCALPING", "Sistema de scalping automático activado", "INFO")
                else:
                    self.add_log("🛑 Scalping automático DESACTIVADO")
                    SICAR_LOGGER.log_alert("SCALPING", "Sistema de scalping automático desactivado", "WARNING")
            else:
                self.add_log("⚠️ Motor de scalping no disponible")
                
            # Actualizar estadísticas inmediatamente
            self._update_scalping_statistics()
            
        except Exception as e:
            self.add_log(f"❌ Error al cambiar estado de scalping: {e}")
            SICAR_LOGGER.log_error("SCALPING_TOGGLE", str(e))

    def toggle_drl(self):
        """Activar/desactivar sistema DRL"""
        try:
            new_state = self.drl_enabled_var.get()
            
            if new_state:
                self.initialize_drl_system()
            else:
                self.shutdown_drl_system()
                
        except Exception as e:
            self.add_log(f"❌ Error al cambiar estado de DRL: {e}")
            SICAR_LOGGER.log_error("DRL_TOGGLE", str(e))

    def initialize_drl_system(self):
        """Inicializar sistema DRL integrado"""
        try:
            # Importar sistema DRL integrado
            from paper_trading_system import DRLIntegratedPaperTrading
            from drl_monitoring_system import DRLMonitoringSystem
            
            # Crear sistema integrado
            self.drl_integrated_system = DRLIntegratedPaperTrading(
                initial_capital=10000.0,
                symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
                enable_drl=True,
                enable_manual_trading=True
            )
            
            # Crear sistema de monitoreo
            self.drl_monitoring_system = DRLMonitoringSystem(
                monitoring_interval=30,  # 30 segundos
                history_size=1000
            )
            
            # Conectar sistemas
            self.drl_monitoring_system.set_integrated_system(self.drl_integrated_system)
            
            # Iniciar monitoreo
            self.drl_monitoring_system.start_monitoring()
            
            # Actualizar estado
            self.drl_status_var.set("🟢 Conectado")
            self.drl_mode_var.set("Híbrido")
            
            self.add_log("🤖 Sistema DRL inicializado correctamente")
            SICAR_LOGGER.log_alert("DRL", "Sistema DRL integrado activado", "INFO")
            
        except Exception as e:
            self.drl_enabled_var.set(False)
            self.drl_status_var.set("🔴 Error")
            self.add_log(f"❌ Error inicializando DRL: {e}")
            SICAR_LOGGER.log_error("DRL_INIT", str(e))

    def shutdown_drl_system(self):
        """Apagar sistema DRL"""
        try:
            if self.drl_monitoring_system:
                self.drl_monitoring_system.stop_monitoring()
                self.drl_monitoring_system = None
            
            if self.drl_integrated_system:
                self.drl_integrated_system = None
            
            # Actualizar estado
            self.drl_status_var.set("🔴 Desconectado")
            self.drl_mode_var.set("Manual")
            self.drl_confidence_var.set("0.00")
            self.drl_sharpe_var.set("0.00")
            self.drl_win_rate_var.set("0.0%")
            self.drl_total_reward_var.set("0.00")
            self.drl_episodes_var.set("0")
            
            self.add_log("🛑 Sistema DRL desactivado")
            SICAR_LOGGER.log_alert("DRL", "Sistema DRL desactivado", "WARNING")
            
        except Exception as e:
            self.add_log(f"❌ Error apagando DRL: {e}")
            SICAR_LOGGER.log_error("DRL_SHUTDOWN", str(e))

    def open_drl_dashboard(self):
        """Abrir dashboard DRL en navegador"""
        try:
            import webbrowser
            webbrowser.open("http://localhost:8502")
            self.add_log("📊 Dashboard DRL abierto en navegador")
        except Exception as e:
            self.add_log(f"❌ Error abriendo dashboard DRL: {e}")

    def update_drl_metrics(self):
        """Actualizar métricas DRL en la interfaz"""
        try:
            if not self.drl_monitoring_system or not self.drl_integrated_system:
                return
            
            # Obtener métricas del sistema de monitoreo
            status = self.drl_monitoring_system.get_current_status()
            
            if status and status.get('metrics_collected', 0) > 0:
                # Obtener resumen del sistema integrado
                summary = self.drl_integrated_system.get_integrated_summary()
                
                # Actualizar variables de la interfaz
                if 'drl_performance' in summary:
                    drl_perf = summary['drl_performance']
                    
                    self.drl_confidence_var.set(f"{drl_perf.get('confidence', 0):.2f}")
                    self.drl_sharpe_var.set(f"{drl_perf.get('sharpe_ratio', 0):.2f}")
                    self.drl_win_rate_var.set(f"{drl_perf.get('win_rate', 0):.1f}%")
                    self.drl_total_reward_var.set(f"{drl_perf.get('total_reward', 0):.3f}")
                    self.drl_episodes_var.set(str(drl_perf.get('episodes_completed', 0)))
                
                # Actualizar modo de trading
                self.drl_mode_var.set(summary.get('trading_mode', 'Manual').title())
                
                # Actualizar estado basado en rendimiento
                if summary.get('drl_enabled', False):
                    if drl_perf.get('sharpe_ratio', 0) > 0.5:
                        self.drl_status_var.set("🟢 Excelente")
                    elif drl_perf.get('sharpe_ratio', 0) > 0.2:
                        self.drl_status_var.set("🟡 Bueno")
                    else:
                        self.drl_status_var.set("🟠 Aprendiendo")
                else:
                    self.drl_status_var.set("🔴 Desconectado")
                    
        except Exception as e:
            SICAR_LOGGER.log_error("DRL_METRICS_UPDATE", str(e))

    def run(self):
        """Ejecutar dashboard"""
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.root.mainloop()
        except Exception as e:
            SICAR_LOGGER.log_error("DASHBOARD_RUN", str(e))
    
    def on_closing(self):
        """Manejar cierre de aplicación"""
        try:
            # Detener sistemas
            self.systems_running = False
            self.breakout_detector.stop_detection()
            self.sync_manager.stop_auto_sync()
            
            # Detener integración de portfolio si está activa
            if PORTFOLIO_INTEGRATION_AVAILABLE and hasattr(self, 'portfolio_integrator') and self.portfolio_integrator:
                self.portfolio_integrator.stop_integration()
            
            # Detener sistema DRL si está activo
            if hasattr(self, 'drl_monitoring_system') and self.drl_monitoring_system:
                self.drl_monitoring_system.stop_monitoring()
            
            # Cerrar ventana
            self.root.destroy()
            
            SICAR_LOGGER.log_alert("DASHBOARD", "Dashboard cerrado correctamente", "INFO")
            
        except Exception as e:
            SICAR_LOGGER.log_error("DASHBOARD_CLOSE", str(e))
            self.root.destroy()

def main():
    """Función principal"""
    try:
        dashboard = EnhancedDashboard()
        dashboard.run()
    except Exception as e:
        print(f"Error iniciando dashboard: {e}")
        SICAR_LOGGER.log_error("MAIN", str(e))

if __name__ == "__main__":
    main()