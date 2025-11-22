"""
SICAR - Breakout Monitor Dashboard
Interfaz de monitoreo visual para validar detecciones de ruptura
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from session_detector import SessionDetector
from first_candle_breakout import FirstCandleBreakoutDetector
from breakout_validator import BreakoutValidator

class BreakoutMonitorDashboard:
    """
    Dashboard visual para monitorear detecciones de ruptura en tiempo real
    """
    
    def __init__(self):
        # Componentes principales
        self.session_detector = SessionDetector()
        self.breakout_detector = FirstCandleBreakoutDetector()
        self.validator = BreakoutValidator()
        
        # Estado del monitoreo
        self.is_monitoring = False
        self.monitoring_thread = None
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Crear interfaz
        self.setup_ui()
        
        # Datos para mostrar
        self.signals_data = []
        self.session_history = []
        
    def setup_ui(self):
        """Configura la interfaz de usuario"""
        
        # Ventana principal
        self.root = tk.Tk()
        self.root.title("SICAR - Breakout Monitor Dashboard")
        self.root.geometry("1200x800")
        self.root.configure(bg='#2b2b2b')
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#2b2b2b', foreground='white')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), background='#2b2b2b', foreground='#00ff00')
        style.configure('Info.TLabel', font=('Arial', 10), background='#2b2b2b', foreground='white')
        style.configure('Status.TLabel', font=('Arial', 10, 'bold'), background='#2b2b2b')
        
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Título
        title_label = ttk.Label(main_frame, text="🚀 SICAR - First Candle Breakout Monitor", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Frame superior - Estado y controles
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.setup_status_panel(top_frame)
        self.setup_control_panel(top_frame)
        
        # Frame medio - Información de sesiones
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.setup_session_panel(middle_frame)
        
        # Frame inferior - Señales y logs
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.BOTH, expand=True)
        
        self.setup_signals_panel(bottom_frame)
        self.setup_log_panel(bottom_frame)
        
        # Inicializar datos
        self.update_display()
        
        # Actualización automática cada 5 segundos
        self.root.after(5000, self.auto_update)
    
    def setup_status_panel(self, parent):
        """Configura el panel de estado"""
        
        status_frame = ttk.LabelFrame(parent, text="Estado del Sistema", padding=10)
        status_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Estado del monitoreo
        self.monitoring_status = ttk.Label(status_frame, text="⏹️ Detenido", style='Status.TLabel', foreground='red')
        self.monitoring_status.pack(anchor=tk.W)
        
        # Sesión actual
        self.current_session_label = ttk.Label(status_frame, text="Sesión: Ninguna", style='Info.TLabel')
        self.current_session_label.pack(anchor=tk.W)
        
        # Próxima sesión
        self.next_session_label = ttk.Label(status_frame, text="Próxima: Calculando...", style='Info.TLabel')
        self.next_session_label.pack(anchor=tk.W)
        
        # Tiempo actual
        self.current_time_label = ttk.Label(status_frame, text="Hora EST: --:--:--", style='Info.TLabel')
        self.current_time_label.pack(anchor=tk.W)
        
        # Estadísticas
        self.stats_label = ttk.Label(status_frame, text="Señales: 0 | Válidas: 0", style='Info.TLabel')
        self.stats_label.pack(anchor=tk.W)
    
    def setup_control_panel(self, parent):
        """Configura el panel de controles"""
        
        control_frame = ttk.LabelFrame(parent, text="Controles", padding=10)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # Botón de inicio/parada
        self.start_stop_btn = ttk.Button(control_frame, text="▶️ Iniciar Monitoreo", command=self.toggle_monitoring)
        self.start_stop_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Botón de prueba manual
        test_btn = ttk.Button(control_frame, text="🧪 Prueba Manual", command=self.run_manual_test)
        test_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Botón de limpiar logs
        clear_btn = ttk.Button(control_frame, text="🗑️ Limpiar Logs", command=self.clear_logs)
        clear_btn.pack(fill=tk.X, pady=(0, 5))
        
        # Botón de exportar
        export_btn = ttk.Button(control_frame, text="💾 Exportar Datos", command=self.export_data)
        export_btn.pack(fill=tk.X)
    
    def setup_session_panel(self, parent):
        """Configura el panel de información de sesiones"""
        
        session_frame = ttk.LabelFrame(parent, text="Información de Sesiones", padding=10)
        session_frame.pack(fill=tk.X)
        
        # Crear tabla de sesiones
        columns = ('Sesión', 'Horario EST', 'Estado', 'Descripción')
        self.session_tree = ttk.Treeview(session_frame, columns=columns, show='headings', height=3)
        
        for col in columns:
            self.session_tree.heading(col, text=col)
            self.session_tree.column(col, width=200)
        
        self.session_tree.pack(fill=tk.X)
        
        # Llenar con datos de sesiones
        self.populate_session_tree()
    
    def setup_signals_panel(self, parent):
        """Configura el panel de señales"""
        
        signals_frame = ttk.LabelFrame(parent, text="Señales Detectadas", padding=10)
        signals_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Crear tabla de señales
        columns = ('Tiempo', 'Símbolo', 'Sesión', 'Tipo', 'Precio', 'Confianza')
        self.signals_tree = ttk.Treeview(signals_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.signals_tree.heading(col, text=col)
            self.signals_tree.column(col, width=100)
        
        # Scrollbar para señales
        signals_scroll = ttk.Scrollbar(signals_frame, orient=tk.VERTICAL, command=self.signals_tree.yview)
        self.signals_tree.configure(yscrollcommand=signals_scroll.set)
        
        self.signals_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        signals_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_log_panel(self, parent):
        """Configura el panel de logs"""
        
        log_frame = ttk.LabelFrame(parent, text="Log de Actividad", padding=10)
        log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Área de texto para logs
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=50, 
                                                 bg='#1e1e1e', fg='#00ff00', 
                                                 font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Log inicial
        self.add_log("🚀 Dashboard iniciado")
        self.add_log("📊 Esperando comandos...")
    
    def populate_session_tree(self):
        """Llena la tabla de sesiones con datos"""
        
        try:
            sessions = self.session_detector.get_session_status_report()
            
            for session_name, config in sessions['all_sessions_config'].items():
                status = "🟢 Activa" if config['active'] else "🔴 Inactiva"
                horario = f"{config['start_time']} - {config['end_time']}"
                
                self.session_tree.insert('', tk.END, values=(
                    config['name'],
                    horario,
                    status,
                    config['description']
                ))
                
        except Exception as e:
            self.add_log(f"❌ Error cargando sesiones: {e}")
    
    def toggle_monitoring(self):
        """Inicia o detiene el monitoreo"""
        
        if not self.is_monitoring:
            self.start_monitoring()
        else:
            self.stop_monitoring()
    
    def start_monitoring(self):
        """Inicia el monitoreo en tiempo real"""
        
        try:
            self.is_monitoring = True
            self.monitoring_status.configure(text="🟢 Monitoreando", foreground='green')
            self.start_stop_btn.configure(text="⏹️ Detener Monitoreo")
            
            self.add_log("🚀 Iniciando monitoreo en tiempo real...")
            
            # Iniciar hilo de monitoreo
            self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
        except Exception as e:
            self.add_log(f"❌ Error iniciando monitoreo: {e}")
            self.is_monitoring = False
    
    def stop_monitoring(self):
        """Detiene el monitoreo"""
        
        try:
            self.is_monitoring = False
            self.monitoring_status.configure(text="⏹️ Detenido", foreground='red')
            self.start_stop_btn.configure(text="▶️ Iniciar Monitoreo")
            
            self.add_log("⏹️ Monitoreo detenido")
            
        except Exception as e:
            self.add_log(f"❌ Error deteniendo monitoreo: {e}")
    
    def monitoring_loop(self):
        """Loop principal de monitoreo"""
        
        last_session = None
        
        while self.is_monitoring:
            try:
                # Verificar sesión actual
                current_session = self.session_detector.get_current_session()
                
                if current_session and current_session != last_session:
                    self.add_log(f"📊 Nueva sesión detectada: {current_session}")
                    
                    # Escanear señales
                    signals = self.breakout_detector.scan_all_symbols(current_session)
                    
                    # Procesar señales
                    valid_signals = [s for s in signals if s.signal_type != 'no_signal']
                    
                    self.add_log(f"🔍 Escaneados {len(signals)} símbolos, {len(valid_signals)} señales válidas")
                    
                    # Agregar señales a la tabla
                    for signal in valid_signals:
                        self.add_signal_to_table(signal)
                        self.add_log(f"🚨 SEÑAL: {signal.symbol} - {signal.signal_type} (Confianza: {signal.confidence:.1%})")
                    
                    last_session = current_session
                
                elif not current_session and last_session:
                    self.add_log("⏳ Sesión terminada, esperando próxima...")
                    last_session = None
                
                # Pausa
                time.sleep(30)
                
            except Exception as e:
                self.add_log(f"❌ Error en monitoreo: {e}")
                time.sleep(60)
    
    def run_manual_test(self):
        """Ejecuta una prueba manual"""
        
        try:
            self.add_log("🧪 Ejecutando prueba manual...")
            
            # Ejecutar en hilo separado para no bloquear UI
            test_thread = threading.Thread(target=self._manual_test_worker, daemon=True)
            test_thread.start()
            
        except Exception as e:
            self.add_log(f"❌ Error en prueba manual: {e}")
    
    def _manual_test_worker(self):
        """Worker para prueba manual"""
        
        try:
            results = self.validator.manual_test()
            
            if results['success']:
                self.add_log(f"✅ Prueba completada: {results['valid_signals']} señales válidas")
                
                # Agregar señales a la tabla si las hay
                for signal_data in results.get('signals_detail', []):
                    # Crear objeto signal mock para mostrar
                    self.add_signal_to_table_from_dict(signal_data)
            else:
                self.add_log(f"❌ Prueba falló: {results.get('error', 'Error desconocido')}")
                
        except Exception as e:
            self.add_log(f"❌ Error en worker de prueba: {e}")
    
    def add_signal_to_table(self, signal):
        """Agrega una señal a la tabla"""
        
        try:
            # Formatear datos
            tiempo = signal.timestamp.strftime("%H:%M:%S")
            precio = f"{signal.entry_price:.5f}"
            confianza = f"{signal.confidence:.1%}"
            
            # Insertar en tabla
            item = self.signals_tree.insert('', 0, values=(  # Insertar al inicio
                tiempo,
                signal.symbol,
                signal.session,
                signal.signal_type,
                precio,
                confianza
            ))
            
            # Colorear según tipo de señal
            if signal.signal_type == 'bullish_breakout':
                self.signals_tree.set(item, 'Tipo', '🟢 Alcista')
            elif signal.signal_type == 'bearish_breakout':
                self.signals_tree.set(item, 'Tipo', '🔴 Bajista')
            
            # Mantener solo las últimas 50 señales
            children = self.signals_tree.get_children()
            if len(children) > 50:
                self.signals_tree.delete(children[-1])
                
        except Exception as e:
            self.add_log(f"❌ Error agregando señal a tabla: {e}")
    
    def add_signal_to_table_from_dict(self, signal_data):
        """Agrega una señal a la tabla desde diccionario"""
        
        try:
            # Manejar timestamp que puede ser datetime o string
            timestamp = signal_data['timestamp']
            if isinstance(timestamp, str):
                tiempo = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
            else:
                # Ya es datetime
                tiempo = timestamp.strftime("%H:%M:%S")
                
            precio = f"{signal_data['entry_price']:.5f}"
            confianza = f"{signal_data['confidence']:.1%}"
            
            item = self.signals_tree.insert('', 0, values=(
                tiempo,
                signal_data['symbol'],
                signal_data['session'],
                signal_data['signal_type'],
                precio,
                confianza
            ))
            
            # Colorear
            if signal_data['signal_type'] == 'bullish_breakout':
                self.signals_tree.set(item, 'Tipo', '🟢 Alcista')
            elif signal_data['signal_type'] == 'bearish_breakout':
                self.signals_tree.set(item, 'Tipo', '🔴 Bajista')
                
        except Exception as e:
            self.add_log(f"❌ Error agregando señal desde dict: {e}")
    
    def add_log(self, message):
        """Agrega un mensaje al log"""
        
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            # Agregar al final
            self.log_text.insert(tk.END, log_message)
            
            # Scroll automático
            self.log_text.see(tk.END)
            
            # Mantener solo las últimas 100 líneas
            lines = self.log_text.get("1.0", tk.END).split('\n')
            if len(lines) > 100:
                self.log_text.delete("1.0", "2.0")
                
        except Exception as e:
            print(f"Error agregando log: {e}")
    
    def clear_logs(self):
        """Limpia el área de logs"""
        
        try:
            self.log_text.delete("1.0", tk.END)
            self.add_log("🗑️ Logs limpiados")
            
        except Exception as e:
            self.add_log(f"❌ Error limpiando logs: {e}")
    
    def export_data(self):
        """Exporta los datos a archivo JSON"""
        
        try:
            # Recopilar datos de señales
            signals_data = []
            for child in self.signals_tree.get_children():
                values = self.signals_tree.item(child)['values']
                signals_data.append({
                    'tiempo': values[0],
                    'simbolo': values[1],
                    'sesion': values[2],
                    'tipo': values[3],
                    'precio': values[4],
                    'confianza': values[5]
                })
            
            # Crear archivo de exportación
            export_data = {
                'timestamp': datetime.now().isoformat(),
                'total_signals': len(signals_data),
                'signals': signals_data
            }
            
            filename = f"sicar_breakout_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.add_log(f"💾 Datos exportados a: {filename}")
            messagebox.showinfo("Exportación", f"Datos exportados exitosamente a:\n{filename}")
            
        except Exception as e:
            error_msg = f"❌ Error exportando datos: {e}"
            self.add_log(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def update_display(self):
        """Actualiza la información mostrada"""
        
        try:
            # Obtener estado actual
            report = self.session_detector.get_session_status_report()
            
            # Actualizar sesión actual
            current_session = report.get('current_session')
            if current_session:
                session_info = report.get('current_session_info', {})
                self.current_session_label.configure(text=f"Sesión: {session_info.get('name', current_session)}")
            else:
                self.current_session_label.configure(text="Sesión: Ninguna")
            
            # Actualizar próxima sesión
            next_session = self.session_detector.get_next_session()
            if next_session:
                wait_time = next_session['wait_minutes']
                hours = wait_time // 60
                minutes = wait_time % 60
                self.next_session_label.configure(text=f"Próxima: {next_session['session']} en {hours}h {minutes}m")
            else:
                self.next_session_label.configure(text="Próxima: No disponible")
            
            # Actualizar tiempo actual
            current_time = report.get('current_time_est', '--:--:--')
            self.current_time_label.configure(text=f"Hora EST: {current_time}")
            
            # Actualizar estadísticas
            total_signals = len(self.signals_tree.get_children())
            self.stats_label.configure(text=f"Señales: {total_signals} | Monitoreando: {'Sí' if self.is_monitoring else 'No'}")
            
        except Exception as e:
            self.add_log(f"❌ Error actualizando display: {e}")
    
    def auto_update(self):
        """Actualización automática cada 5 segundos"""
        
        try:
            self.update_display()
        except Exception as e:
            print(f"Error en auto_update: {e}")
        finally:
            # Programar próxima actualización
            self.root.after(5000, self.auto_update)
    
    def run(self):
        """Ejecuta el dashboard"""
        
        try:
            self.add_log("🚀 Dashboard listo para usar")
            self.root.mainloop()
        except Exception as e:
            print(f"Error ejecutando dashboard: {e}")
        finally:
            # Asegurar que el monitoreo se detenga
            self.is_monitoring = False


def main():
    """Función principal"""
    
    try:
        # Crear y ejecutar dashboard
        dashboard = BreakoutMonitorDashboard()
        dashboard.run()
        
    except Exception as e:
        print(f"Error iniciando dashboard: {e}")
        messagebox.showerror("Error", f"Error iniciando dashboard:\n{e}")


if __name__ == "__main__":
    main()