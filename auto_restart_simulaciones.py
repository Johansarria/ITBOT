#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Auto-Reinicio para Simulaciones de Trading
Gestiona el reinicio automático de todas las simulaciones con resiliencia
"""

import subprocess
import time
import json
import signal
import sys
from datetime import datetime
from typing import Dict, List
import threading
import os

class AutoRestartManager:
    def __init__(self):
        self.processes = {}
        self.running = True
        self.restart_counts = {}
        self.max_global_restarts = 50
        self.check_interval = 60  # Verificar cada minuto
        
        # Configuración de simulaciones
        self.simulations = {
            'NAS100': {
                'script': 'simulacion_real_nas100_4.py',
                'terminal_id': 4,
                'type': 'indices',
                'max_restarts': 15
            },
            'AUDCAD': {
                'script': 'simulacion_real_audcad_5.py', 
                'terminal_id': 5,
                'type': 'forex',
                'max_restarts': 15
            },
            'XAUUSD': {
                'script': 'simulacion_real_xauusd_6.py',
                'terminal_id': 6,
                'type': 'metales',
                'max_restarts': 15
            }
        }
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Inicializar contadores
        for sim_name in self.simulations:
            self.restart_counts[sim_name] = 0
    
    def signal_handler(self, signum, frame):
        """Maneja señales del sistema para cierre limpio"""
        print(f"\n⚠️  Señal {signum} recibida. Cerrando gestor de simulaciones...")
        self.running = False
        self.stop_all_simulations()
    
    def log_event(self, event_type: str, data: Dict):
        """Registra eventos del gestor"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'manager': 'AutoRestartManager',
            'event_type': event_type,
            'data': data
        }
        
        try:
            with open('logs_simulacion/auto_restart_manager.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"❌ Error escribiendo log del gestor: {e}")
    
    def start_simulation(self, sim_name: str) -> bool:
        """Inicia una simulación específica"""
        try:
            sim_config = self.simulations[sim_name]
            script_path = sim_config['script']
            
            print(f"🚀 Iniciando {sim_name} ({sim_config['type']})...")
            
            # Crear proceso
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes[sim_name] = {
                'process': process,
                'start_time': datetime.now(),
                'script': script_path,
                'config': sim_config
            }
            
            self.log_event('simulation_started', {
                'simulation': sim_name,
                'pid': process.pid,
                'script': script_path,
                'restart_count': self.restart_counts[sim_name]
            })
            
            print(f"✅ {sim_name} iniciado (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Error iniciando {sim_name}: {e}")
            self.log_event('simulation_start_error', {
                'simulation': sim_name,
                'error': str(e)
            })
            return False
    
    def check_simulation_status(self, sim_name: str) -> bool:
        """Verifica si una simulación está ejecutándose"""
        if sim_name not in self.processes:
            return False
        
        process_info = self.processes[sim_name]
        process = process_info['process']
        
        # Verificar si el proceso sigue vivo
        poll_result = process.poll()
        
        if poll_result is None:
            # Proceso sigue ejecutándose
            return True
        else:
            # Proceso terminó
            runtime = datetime.now() - process_info['start_time']
            
            self.log_event('simulation_ended', {
                'simulation': sim_name,
                'exit_code': poll_result,
                'runtime_seconds': runtime.total_seconds(),
                'restart_count': self.restart_counts[sim_name]
            })
            
            print(f"⚠️  {sim_name} terminó (código: {poll_result}, tiempo: {runtime})")
            
            # Limpiar proceso terminado
            del self.processes[sim_name]
            return False
    
    def restart_simulation(self, sim_name: str) -> bool:
        """Reinicia una simulación específica"""
        sim_config = self.simulations[sim_name]
        
        # Verificar límite de reinicios
        if self.restart_counts[sim_name] >= sim_config['max_restarts']:
            print(f"🛑 {sim_name}: Máximo de reinicios alcanzado ({sim_config['max_restarts']})")
            return False
        
        self.restart_counts[sim_name] += 1
        
        print(f"🔄 Reiniciando {sim_name} (intento #{self.restart_counts[sim_name]})...")
        
        # Esperar antes del reinicio
        wait_time = min(30 * self.restart_counts[sim_name], 180)  # Máx 3 min
        print(f"⏳ Esperando {wait_time}s antes del reinicio...")
        time.sleep(wait_time)
        
        return self.start_simulation(sim_name)
    
    def stop_simulation(self, sim_name: str):
        """Detiene una simulación específica"""
        if sim_name in self.processes:
            process_info = self.processes[sim_name]
            process = process_info['process']
            
            print(f"🛑 Deteniendo {sim_name}...")
            
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print(f"⚡ Forzando cierre de {sim_name}...")
                process.kill()
                process.wait()
            
            del self.processes[sim_name]
            
            self.log_event('simulation_stopped', {
                'simulation': sim_name,
                'restart_count': self.restart_counts[sim_name]
            })
    
    def stop_all_simulations(self):
        """Detiene todas las simulaciones"""
        print("🛑 Deteniendo todas las simulaciones...")
        
        for sim_name in list(self.processes.keys()):
            self.stop_simulation(sim_name)
    
    def start_all_simulations(self):
        """Inicia todas las simulaciones"""
        print("🚀 Iniciando todas las simulaciones...")
        
        for sim_name in self.simulations:
            if not self.check_simulation_status(sim_name):
                self.start_simulation(sim_name)
                time.sleep(5)  # Esperar entre inicios
    
    def monitor_simulations(self):
        """Monitorea y reinicia simulaciones según sea necesario"""
        print(f"👁️  Iniciando monitoreo de simulaciones (intervalo: {self.check_interval}s)")
        
        while self.running:
            try:
                for sim_name in self.simulations:
                    if not self.check_simulation_status(sim_name):
                        # Simulación no está ejecutándose, intentar reiniciar
                        if self.restart_counts[sim_name] < self.simulations[sim_name]['max_restarts']:
                            self.restart_simulation(sim_name)
                        else:
                            print(f"⚠️  {sim_name}: No se puede reiniciar (límite alcanzado)")
                
                # Mostrar estado actual
                active_sims = len(self.processes)
                total_restarts = sum(self.restart_counts.values())
                
                print(f"📊 Estado: {active_sims}/3 simulaciones activas, {total_restarts} reinicios totales")
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Error en monitoreo: {e}")
                self.log_event('monitor_error', {'error': str(e)})
                time.sleep(30)
    
    def run(self):
        """Ejecuta el gestor de auto-reinicio"""
        print("🎯 Iniciando Gestor de Auto-Reinicio de Simulaciones")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.log_event('manager_started', {
            'simulations': list(self.simulations.keys()),
            'check_interval': self.check_interval
        })
        
        try:
            # Iniciar todas las simulaciones
            self.start_all_simulations()
            
            # Comenzar monitoreo
            self.monitor_simulations()
            
        except KeyboardInterrupt:
            print("\n⚠️  Interrupción del usuario")
        except Exception as e:
            print(f"❌ Error crítico en gestor: {e}")
            self.log_event('manager_error', {'error': str(e)})
        finally:
            self.stop_all_simulations()
            print("🏁 Gestor de Auto-Reinicio finalizado")
            
            self.log_event('manager_stopped', {
                'total_restarts': sum(self.restart_counts.values()),
                'final_restart_counts': self.restart_counts
            })

def main():
    """Función principal"""
    # Crear directorios necesarios
    os.makedirs('logs_simulacion', exist_ok=True)
    os.makedirs('reportes_simulacion', exist_ok=True)
    
    # Crear y ejecutar gestor
    manager = AutoRestartManager()
    manager.run()

if __name__ == "__main__":
    main()
