#!/usr/bin/env python3
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
            
            print("=" * 80)
            print("MONITOR DE SIMULACIONES MULTI-TERMINAL")
            print(f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
            
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
                print("\n" + "-" * 80)
                print("RESUMEN TOTAL:")
                print(f"Capital Total: ${total_capital:,.2f} (de $3,000 inicial)")
                print(f"Retorno Promedio: {total_return/3:.2f}%")
                print(f"Simulaciones Activas: {active_simulations}/3")
                
                portfolio_return = ((total_capital - 3000) / 3000) * 100
                print(f"Retorno del Portfolio: {portfolio_return:+.2f}%")
            
            print("\n" + "=" * 80)
            print("Presiona Ctrl+C para salir del monitor")
            
            try:
                time.sleep(5)  # Actualizar cada 5 segundos
            except KeyboardInterrupt:
                print("\n👋 Monitor cerrado")
                break

if __name__ == "__main__":
    monitor = SimulationMonitor()
    monitor.display_dashboard()
