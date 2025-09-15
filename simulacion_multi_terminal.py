#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Simulación Multi-Terminal
Ejecuta 3 simulaciones simultáneas con los mejores símbolos
Capital base: $1000 por simulación
"""

import json
import time
import random
from datetime import datetime, timedelta
import os
from typing import Dict, List

class MultiTerminalSimulator:
    def __init__(self):
        self.base_capital = 1000.0
        self.symbols = {
            'BNBUSDT': {
                'monthly_return': 27.22,
                'weekly_return': 6.33,
                'volatility': 0.15,
                'win_rate': 0.68
            },
            'ADAUSDT': {
                'monthly_return': 27.17,
                'weekly_return': 6.32,
                'volatility': 0.18,
                'win_rate': 0.65
            },
            'SOLUSDT': {
                'monthly_return': 24.15,
                'weekly_return': 5.61,
                'volatility': 0.22,
                'win_rate': 0.62
            }
        }
        
        # Crear directorio de logs si no existe
        os.makedirs('logs_simulacion', exist_ok=True)
    
    def generate_simulation_script(self, symbol: str, terminal_id: int) -> str:
        """Genera script de simulación para un símbolo específico"""
        config_json = json.dumps(self.symbols[symbol], indent=12)
        
        script_content = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulación Terminal {terminal_id} - {symbol}
Capital Base: ${self.base_capital}
"""

import json
import time
import random
from datetime import datetime, timedelta
import os

class TradingSimulator:
    def __init__(self, symbol, capital, config):
        self.symbol = symbol
        self.capital = capital
        self.initial_capital = capital
        self.config = config
        self.trades = []
        self.session_id = f"{{symbol}}_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}"
        self.log_file = f"logs_simulacion/{{self.session_id}}.jsonl"
        
    def log_event(self, event_type: str, data: dict):
        """Registra eventos en formato JSON Lines"""
        event = {{
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "symbol": self.symbol,
            "event_type": event_type,
            "data": data
        }}
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\\n')
    
    def simulate_trade(self) -> dict:
        """Simula una operación de trading"""
        # Determinar si es ganadora basado en win_rate
        is_winner = random.random() < self.config['win_rate']
        
        # Calcular retorno basado en volatilidad
        base_return = self.config['weekly_return'] / 35  # Retorno diario promedio
        volatility_factor = random.uniform(-self.config['volatility'], self.config['volatility'])
        
        if is_winner:
            return_pct = abs(base_return + volatility_factor)
        else:
            return_pct = -(abs(base_return) * random.uniform(0.3, 0.8))
        
        # Calcular monto de la operación (2-5% del capital)
        trade_amount = self.capital * random.uniform(0.02, 0.05)
        profit_loss = trade_amount * (return_pct / 100)
        
        trade = {{
            "trade_id": len(self.trades) + 1,
            "timestamp": datetime.now().isoformat(),
            "type": "BUY" if is_winner else "SELL",
            "amount": round(trade_amount, 2),
            "return_pct": round(return_pct, 4),
            "profit_loss": round(profit_loss, 2),
            "is_winner": is_winner
        }}
        
        self.capital += profit_loss
        self.trades.append(trade)
        
        return trade
    
    def run_simulation(self, duration_hours: int = 24):
        """Ejecuta la simulación por el tiempo especificado"""
        print(f"\\n=== INICIANDO SIMULACIÓN {{self.symbol}} ===")
        print(f"Terminal: {terminal_id}")
        print(f"Capital Inicial: ${{self.initial_capital:,.2f}}")
        print(f"Duración: {{duration_hours}} horas")
        print(f"Archivo de logs: {{self.log_file}}")
        print("=" * 50)
        
        # Log de inicio de sesión
        self.log_event("session_start", {{
            "initial_capital": self.initial_capital,
            "symbol": self.symbol,
            "duration_hours": duration_hours,
            "config": self.config
        }})
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        trade_count = 0
        
        try:
            while datetime.now() < end_time:
                # Simular operación cada 15-45 minutos
                wait_time = random.uniform(900, 2700)  # 15-45 minutos en segundos
                
                # Para demo, reducir tiempo de espera
                demo_wait = min(wait_time / 60, 10)  # Máximo 10 segundos para demo
                time.sleep(demo_wait)
                
                # Ejecutar trade
                trade = self.simulate_trade()
                trade_count += 1
                
                # Log del trade
                self.log_event("trade_executed", trade)
                
                # Mostrar progreso
                current_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
                print(f"Trade #{{trade_count}} | {{self.symbol}} | "
                      f"P&L: ${{trade['profit_loss']:+.2f}} | "
                      f"Capital: ${{self.capital:,.2f}} | "
                      f"Retorno: {{current_return:+.2f}}%")
                
                # Log de performance cada 10 trades
                if trade_count % 10 == 0:
                    self.log_performance_update()
                
                # Simular condición de parada por pérdidas excesivas
                if self.capital < self.initial_capital * 0.7:  # Stop loss al 30%
                    print(f"\\n⚠️  STOP LOSS ACTIVADO - Capital: ${{self.capital:,.2f}}")
                    self.log_event("stop_loss_triggered", {{
                        "remaining_capital": self.capital,
                        "loss_pct": ((self.initial_capital - self.capital) / self.initial_capital) * 100
                    }})
                    break
        
        except KeyboardInterrupt:
            print(f"\\n⏹️  Simulación interrumpida por el usuario")
            self.log_event("simulation_interrupted", {{"reason": "user_interrupt"}})
        
        # Resumen final
        self.generate_final_report()
    
    def log_performance_update(self):
        """Registra actualización de performance"""
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        winning_trades = sum(1 for t in self.trades if t['is_winner'])
        win_rate = (winning_trades / len(self.trades)) * 100 if self.trades else 0
        
        performance = {{
            "total_trades": len(self.trades),
            "current_capital": self.capital,
            "total_return_pct": round(total_return, 2),
            "win_rate_pct": round(win_rate, 2),
            "winning_trades": winning_trades,
            "losing_trades": len(self.trades) - winning_trades
        }}
        
        self.log_event("performance_update", performance)
    
    def generate_final_report(self):
        """Genera reporte final de la simulación"""
        final_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        winning_trades = sum(1 for t in self.trades if t['is_winner'])
        total_profit = sum(t['profit_loss'] for t in self.trades if t['profit_loss'] > 0)
        total_loss = sum(t['profit_loss'] for t in self.trades if t['profit_loss'] < 0)
        
        report = {{
            "session_summary": {{
                "symbol": self.symbol,
                "initial_capital": self.initial_capital,
                "final_capital": self.capital,
                "total_return_pct": round(final_return, 2),
                "total_trades": len(self.trades),
                "winning_trades": winning_trades,
                "win_rate_pct": round((winning_trades / len(self.trades)) * 100, 2) if self.trades else 0,
                "total_profit": round(total_profit, 2),
                "total_loss": round(total_loss, 2),
                "net_profit": round(self.capital - self.initial_capital, 2)
            }}
        }}
        
        # Log del reporte final
        self.log_event("session_end", report)
        
        # Mostrar resumen en consola
        print(f"\\n{{'='*60}}")
        print(f"RESUMEN FINAL - {{self.symbol}} (Terminal {terminal_id})")
        print(f"{{'='*60}}")
        print(f"Capital Inicial: ${{self.initial_capital:,.2f}}")
        print(f"Capital Final: ${{self.capital:,.2f}}")
        print(f"Retorno Total: {{final_return:+.2f}}%")
        print(f"Operaciones: {{len(self.trades)}}")
        print(f"Operaciones Ganadoras: {{winning_trades}}")
        print(f"Tasa de Éxito: {{(winning_trades / len(self.trades)) * 100:.1f}}%" if self.trades else "N/A")
        print(f"Ganancia Bruta: ${{total_profit:,.2f}}")
        print(f"Pérdida Bruta: ${{total_loss:,.2f}}")
        print(f"Ganancia Neta: ${{self.capital - self.initial_capital:+,.2f}}")
        print(f"Archivo de logs: {{self.log_file}}")
        print(f"{{'='*60}}")
        
        # Guardar reporte en JSON
        report_file = f"logs_simulacion/report_{{self.session_id}}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"📊 Reporte guardado en: {{report_file}}")

if __name__ == "__main__":
    # Configuración del símbolo
    symbol = "{symbol}"
    config = {config_json}
    
    # Crear simulador
    simulator = TradingSimulator(symbol, {self.base_capital}, config)
    
    # Ejecutar simulación (24 horas simuladas en ~5 minutos reales)
    simulator.run_simulation(duration_hours=24)
'''
        return script_content
    
    def create_simulation_scripts(self):
        """Crea los scripts de simulación para cada símbolo"""
        scripts = {}
        
        for i, symbol in enumerate(self.symbols.keys(), 1):
            script_content = self.generate_simulation_script(symbol, i)
            script_filename = f"simulacion_{symbol.lower()}_{i}.py"
            script_path = os.path.join(os.getcwd(), script_filename)
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            scripts[symbol] = {
                'terminal_id': i,
                'script_file': script_filename,
                'script_path': script_path
            }
            
            print(f"✅ Script creado: {script_filename} (Terminal {i} - {symbol})")
        
        return scripts
    
    def generate_launcher_commands(self, scripts: Dict) -> List[str]:
        """Genera comandos para lanzar las simulaciones en terminales separadas"""
        commands = []
        
        print(f"\n{'='*60}")
        print("COMANDOS PARA EJECUTAR EN TERMINALES SEPARADAS")
        print(f"{'='*60}")
        
        for symbol, info in scripts.items():
            command = f"python {info['script_file']}"
            commands.append(command)
            
            print(f"\nTerminal {info['terminal_id']} ({symbol}):")
            print(f"Comando: {command}")
            print(f"Archivo: {info['script_file']}")
        
        print(f"\n{'='*60}")
        print("INSTRUCCIONES:")
        print("1. Abrir 3 terminales separadas")
        print("2. Navegar al directorio del proyecto en cada terminal")
        print("3. Ejecutar cada comando en su terminal correspondiente")
        print("4. Las simulaciones correrán simultáneamente")
        print("5. Los logs se guardarán en la carpeta 'logs_simulacion'")
        print(f"{'='*60}")
        
        return commands
    
    def create_monitoring_script(self):
        """Crea script para monitorear todas las simulaciones"""
        monitor_script = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de Simulaciones Multi-Terminal
Monitorea el progreso de las 3 simulaciones simultáneas
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List

class SimulationMonitor:
    def __init__(self):
        self.logs_dir = "logs_simulacion"
        self.symbols = ["BNBUSDT", "ADAUSDT", "SOLUSDT"]
    
    def get_latest_logs(self) -> Dict:
        """Obtiene los logs más recientes de cada simulación"""
        latest_logs = {}
        
        if not os.path.exists(self.logs_dir):
            return latest_logs
        
        for symbol in self.symbols:
            # Buscar el archivo de log más reciente para cada símbolo
            log_files = [f for f in os.listdir(self.logs_dir) 
                        if f.startswith(symbol) and f.endswith('.jsonl')]
            
            if log_files:
                latest_file = max(log_files, key=lambda x: os.path.getctime(os.path.join(self.logs_dir, x)))
                latest_logs[symbol] = os.path.join(self.logs_dir, latest_file)
        
        return latest_logs
    
    def parse_log_file(self, log_file: str) -> Dict:
        """Parsea un archivo de log y extrae estadísticas"""
        stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "current_capital": 1000.0,
            "total_return": 0.0,
            "last_update": None,
            "status": "unknown"
        }
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                if line.strip():
                    event = json.loads(line)
                    
                    if event['event_type'] == 'trade_executed':
                        stats['total_trades'] += 1
                        if event['data']['is_winner']:
                            stats['winning_trades'] += 1
                    
                    elif event['event_type'] == 'performance_update':
                        stats['current_capital'] = event['data']['current_capital']
                        stats['total_return'] = event['data']['total_return_pct']
                        stats['last_update'] = event['timestamp']
                        stats['status'] = "running"
                    
                    elif event['event_type'] == 'session_end':
                        stats['current_capital'] = event['data']['session_summary']['final_capital']
                        stats['total_return'] = event['data']['session_summary']['total_return_pct']
                        stats['total_trades'] = event['data']['session_summary']['total_trades']
                        stats['winning_trades'] = event['data']['session_summary']['winning_trades']
                        stats['last_update'] = event['timestamp']
                        stats['status'] = "completed"
        
        except Exception as e:
            stats['status'] = f"error: {str(e)}"
        
        return stats
    
    def display_dashboard(self):
        """Muestra dashboard en tiempo real"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"{'='*80}")
            print(f"MONITOR DE SIMULACIONES MULTI-TERMINAL")
            print(f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            
            latest_logs = self.get_latest_logs()
            
            if not latest_logs:
                print("❌ No se encontraron logs de simulación")
                print("   Asegúrate de que las simulaciones estén ejecutándose")
            else:
                total_capital = 0
                total_return = 0
                active_simulations = 0
                
                for symbol in self.symbols:
                    if symbol in latest_logs:
                        stats = self.parse_log_file(latest_logs[symbol])
                        
                        # Determinar estado visual
                        if stats['status'] == 'running':
                            status_icon = "🟢"
                            active_simulations += 1
                        elif stats['status'] == 'completed':
                            status_icon = "✅"
                        else:
                            status_icon = "❌"
                        
                        # Calcular win rate
                        win_rate = (stats['winning_trades'] / stats['total_trades'] * 100) if stats['total_trades'] > 0 else 0
                        
                        print(f"\n{status_icon} {symbol}:")
                        print(f"   Capital: ${stats['current_capital']:,.2f} ({stats['total_return']:+.2f}%)")
                        print(f"   Trades: {stats['total_trades']} | Ganadores: {stats['winning_trades']} ({win_rate:.1f}%)")
                        print(f"   Estado: {stats['status']}")
                        
                        if stats['status'] in ['running', 'completed']:
                            total_capital += stats['current_capital']
                            total_return += stats['total_return']
                    else:
                        print(f"\n⚪ {symbol}: Sin datos")
                
                # Resumen total
                print(f"\n{'-'*80}")
                print(f"RESUMEN TOTAL:")
                print(f"Capital Total: ${total_capital:,.2f} (de $3,000 inicial)")
                print(f"Retorno Promedio: {total_return/3:.2f}%")
                print(f"Simulaciones Activas: {active_simulations}/3")
                
                portfolio_return = ((total_capital - 3000) / 3000) * 100
                print(f"Retorno del Portfolio: {portfolio_return:+.2f}%")
            
            print(f"\n{'='*80}")
            print("Presiona Ctrl+C para salir del monitor")
            
            try:
                time.sleep(5)  # Actualizar cada 5 segundos
            except KeyboardInterrupt:
                print("\n👋 Monitor cerrado")
                break

if __name__ == "__main__":
    monitor = SimulationMonitor()
    monitor.display_dashboard()
'''
        
        with open('monitor_simulaciones.py', 'w', encoding='utf-8') as f:
            f.write(monitor_script)
        
        print(f"\n📊 Monitor creado: monitor_simulaciones.py")
        print("   Ejecuta 'python monitor_simulaciones.py' para monitorear todas las simulaciones")

def main():
    print("🚀 GENERADOR DE SIMULACIONES MULTI-TERMINAL")
    print("Capital base por simulación: $1,000")
    print("Símbolos: BNBUSDT, ADAUSDT, SOLUSDT")
    print("="*60)
    
    simulator = MultiTerminalSimulator()
    
    # Crear scripts de simulación
    scripts = simulator.create_simulation_scripts()
    
    # Generar comandos de ejecución
    commands = simulator.generate_launcher_commands(scripts)
    
    # Crear script de monitoreo
    simulator.create_monitoring_script()
    
    print(f"\n✅ Sistema de simulación multi-terminal creado exitosamente!")
    print(f"📁 Logs se guardarán en: logs_simulacion/")
    
    return scripts, commands

if __name__ == "__main__":
    main()