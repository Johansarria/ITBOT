#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulación de Trading Real - XAUUSD (Metales) con Resiliencia
Terminal ID: 6
Proxy: BTCUSDT (Bitcoin como proxy para metales preciosos)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulacion_real_binance import BinanceRealDataSimulator
from datetime import datetime
import time
import traceback
import signal
import json

class ResilientXAUUSDSimulator:
    def __init__(self):
        self.max_retries = 5
        self.retry_delay = 30  # segundos
        self.restart_count = 0
        self.max_restarts = 10
        self.running = True
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Maneja señales del sistema para cierre limpio"""
        print(f"\n⚠️  Señal {signum} recibida. Cerrando simulación...")
        self.running = False
    
    def log_error(self, error_msg, exception=None):
        """Registra errores en archivo de log"""
        error_log = {
            'timestamp': datetime.now().isoformat(),
            'terminal': 6,
            'symbol': 'XAUUSD',
            'error': error_msg,
            'exception': str(exception) if exception else None,
            'restart_count': self.restart_count
        }
        
        try:
            with open('logs_simulacion/XAUUSD_errors.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_log, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"❌ Error escribiendo log de errores: {e}")
    
    def create_simulator(self):
        """Crea una nueva instancia del simulador"""
        simulator = BinanceRealDataSimulator(
            symbol="PAXGUSDT",  # PAX Gold (oro tokenizado)
            initial_capital=1000.0,
            terminal_id=6
        )
        
        # Configurar parámetros específicos para metales
        simulator.win_rate = 0.75  # 75% win rate para metales
        simulator.avg_return = 0.015  # 1.5% retorno promedio
        simulator.volatility = 0.022  # 2.2% volatilidad
        simulator.trade_frequency = 360  # Trade cada 6 minutos
        
        return simulator
    
    def run_with_resilience(self):
        """Ejecuta la simulación con mecanismos de resiliencia"""
        while self.running and self.restart_count < self.max_restarts:
            try:
                print(f"\n🎯 Iniciando Simulación XAUUSD (Terminal 6) - Intento #{self.restart_count + 1}")
                print(f"📊 Símbolo: PAXGUSDT (Oro tokenizado)")
                print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Crear simulador
                simulator = self.create_simulator()
                
                # Configurar archivos específicos con timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                simulator.log_file = f"logs_simulacion/XAUUSD_{timestamp}.jsonl"
                simulator.report_file = f"reportes_simulacion/XAUUSD_{timestamp}.json"
                
                # Ejecutar simulación con reintentos
                for attempt in range(self.max_retries):
                    try:
                        simulator.run_simulation()
                        print("✅ Simulación XAUUSD completada exitosamente")
                        return  # Salir si se completa exitosamente
                        
                    except Exception as e:
                        error_msg = f"Error en intento {attempt + 1}/{self.max_retries}: {str(e)}"
                        print(f"❌ {error_msg}")
                        self.log_error(error_msg, e)
                        
                        if attempt < self.max_retries - 1:
                            print(f"⏳ Esperando {self.retry_delay}s antes del siguiente intento...")
                            time.sleep(self.retry_delay)
                        else:
                            raise e
                            
            except Exception as e:
                self.restart_count += 1
                error_msg = f"Fallo crítico en simulación XAUUSD (restart #{self.restart_count})"
                print(f"❌ {error_msg}: {str(e)}")
                print(f"📋 Traceback: {traceback.format_exc()}")
                self.log_error(error_msg, e)
                
                if self.restart_count < self.max_restarts:
                    wait_time = min(60 * self.restart_count, 300)  # Espera progresiva, máx 5 min
                    print(f"🔄 Reiniciando en {wait_time}s... ({self.restart_count}/{self.max_restarts})")
                    time.sleep(wait_time)
                else:
                    print(f"🛑 Máximo de reinicios alcanzado ({self.max_restarts}). Deteniendo simulación.")
                    break
        
        print("🏁 Simulación XAUUSD finalizada")

def main():
    """Función principal con resiliencia"""
    resilient_sim = ResilientXAUUSDSimulator()
    resilient_sim.run_with_resilience()

if __name__ == "__main__":
    main()