#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Informativo para Simulaciones de Trading
Monitorea en tiempo real el estado de las 6 simulaciones activas
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import subprocess
from pathlib import Path

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SimulationDashboard:
    def __init__(self):
        self.symbols = {
            'NAS100': {'file': 'simulacion_real_nas100_4.py', 'log': 'simulacion_btcusdt_4.jsonl', 'terminal': 4},
            'AUDCAD': {'file': 'simulacion_real_audcad_5.py', 'log': 'simulacion_audusdt_5.jsonl', 'terminal': 5},
            'XAUUSD': {'file': 'simulacion_real_xauusd_6.py', 'log': 'simulacion_btcusdt_6.jsonl', 'terminal': 6},
            'BNBUSDT': {'file': 'simulacion_real_bnbusdt_1.py', 'log': 'simulacion_bnbusdt_1.jsonl', 'terminal': 1},
            'ADAUSDT': {'file': 'simulacion_real_adausdt_2.py', 'log': 'simulacion_adausdt_2.jsonl', 'terminal': 2},
            'SOLUSDT': {'file': 'simulacion_real_solusdt_3.py', 'log': 'simulacion_solusdt_3.jsonl', 'terminal': 3}
        }
        self.stats = {}
        self.running = True
        
    def clear_screen(self):
        """Limpia la pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def read_log_file(self, log_file: str) -> List[Dict]:
        """Lee el archivo de log JSONL y retorna las últimas entradas"""
        try:
            if not os.path.exists(log_file):
                return []
                
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Leer las últimas 50 líneas para obtener estadísticas recientes
            recent_lines = lines[-50:] if len(lines) > 50 else lines
            
            entries = []
            for line in recent_lines:
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
                    
            return entries
        except Exception as e:
            return []
            
    def calculate_stats(self, symbol: str, entries: List[Dict]) -> Dict:
        """Calcula estadísticas para un símbolo"""
        if not entries:
            return {
                'status': 'Sin datos',
                'total_trades': 0,
                'total_return': 0.0,
                'win_rate': 0.0,
                'last_trade': 'N/A',
                'uptime': 'N/A',
                'avg_return_per_trade': 0.0
            }
            
        # Filtrar solo entradas de trades
        trade_entries = [e for e in entries if e.get('tipo') == 'trade']
        
        if not trade_entries:
            return {
                'status': 'Activo - Sin trades',
                'total_trades': 0,
                'total_return': 0.0,
                'win_rate': 0.0,
                'last_trade': 'N/A',
                'uptime': self.calculate_uptime(entries),
                'avg_return_per_trade': 0.0
            }
            
        # Calcular estadísticas
        total_trades = len(trade_entries)
        total_return = sum(float(e.get('retorno_total', 0)) for e in trade_entries)
        
        # Calcular win rate
        winning_trades = sum(1 for e in trade_entries if float(e.get('retorno_total', 0)) > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Último trade
        last_trade = trade_entries[-1] if trade_entries else None
        last_trade_time = last_trade.get('timestamp', 'N/A') if last_trade else 'N/A'
        
        # Retorno promedio por trade
        avg_return = total_return / total_trades if total_trades > 0 else 0
        
        return {
            'status': 'Activo',
            'total_trades': total_trades,
            'total_return': total_return,
            'win_rate': win_rate,
            'last_trade': last_trade_time,
            'uptime': self.calculate_uptime(entries),
            'avg_return_per_trade': avg_return
        }
        
    def calculate_uptime(self, entries: List[Dict]) -> str:
        """Calcula el tiempo de actividad basado en las entradas"""
        if not entries:
            return 'N/A'
            
        try:
            first_entry = entries[0]
            last_entry = entries[-1]
            
            first_time = datetime.fromisoformat(first_entry.get('timestamp', '').replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(last_entry.get('timestamp', '').replace('Z', '+00:00'))
            
            uptime = last_time - first_time
            
            hours = int(uptime.total_seconds() // 3600)
            minutes = int((uptime.total_seconds() % 3600) // 60)
            
            return f"{hours}h {minutes}m"
        except:
            return 'N/A'
            
    def check_process_status(self, symbol: str) -> str:
        """Verifica si el proceso está ejecutándose"""
        try:
            # Verificar si el archivo de log se está actualizando
            log_file = self.symbols[symbol]['log']
            if not os.path.exists(log_file):
                return 'Detenido'
                
            # Verificar la última modificación del archivo
            last_modified = os.path.getmtime(log_file)
            current_time = time.time()
            
            # Si el archivo no se ha modificado en los últimos 10 minutos, considerar detenido
            if current_time - last_modified > 600:  # 10 minutos
                return 'Posiblemente detenido'
            else:
                return 'Ejecutándose'
                
        except Exception:
            return 'Estado desconocido'
            
    def update_stats(self):
        """Actualiza las estadísticas de todas las simulaciones"""
        for symbol in self.symbols:
            log_file = self.symbols[symbol]['log']
            entries = self.read_log_file(log_file)
            stats = self.calculate_stats(symbol, entries)
            stats['process_status'] = self.check_process_status(symbol)
            self.stats[symbol] = stats
            
    def format_number(self, num: float, decimals: int = 2) -> str:
        """Formatea números para mostrar"""
        if abs(num) >= 1000:
            return f"{num:,.{decimals}f}"
        else:
            return f"{num:.{decimals}f}"
            
    def get_status_color(self, status: str) -> str:
        """Retorna código de color para el estado"""
        if status == 'Ejecutándose':
            return '\033[92m'  # Verde
        elif status == 'Detenido':
            return '\033[91m'  # Rojo
        elif status == 'Posiblemente detenido':
            return '\033[93m'  # Amarillo
        else:
            return '\033[94m'  # Azul
            
    def display_dashboard(self):
        """Muestra el dashboard"""
        self.clear_screen()
        
        # Encabezado
        print("\033[1m" + "="*80)
        print("           DASHBOARD DE SIMULACIONES DE TRADING ALGORÍTMICO")
        print("="*80 + "\033[0m")
        print(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Resumen general
        total_trades = sum(stats.get('total_trades', 0) for stats in self.stats.values())
        total_return = sum(stats.get('total_return', 0) for stats in self.stats.values())
        active_sims = sum(1 for stats in self.stats.values() if stats.get('process_status') == 'Ejecutándose')
        
        print("\033[1mRESUMEN GENERAL:\033[0m")
        print(f"  Simulaciones activas: {active_sims}/6")
        print(f"  Total de trades: {total_trades}")
        print(f"  Retorno total combinado: {self.format_number(total_return, 4)}%")
        print()
        
        # Detalles por símbolo
        print("\033[1mDETALLE POR SÍMBOLO:\033[0m")
        print("-"*80)
        
        header = f"{'SÍMBOLO':<10} {'ESTADO':<15} {'TRADES':<8} {'RETORNO%':<12} {'WIN RATE%':<10} {'UPTIME':<10}"
        print("\033[1m" + header + "\033[0m")
        print("-"*80)
        
        for symbol in sorted(self.symbols.keys()):
            stats = self.stats.get(symbol, {})
            
            status = stats.get('process_status', 'N/A')
            color = self.get_status_color(status)
            
            trades = stats.get('total_trades', 0)
            total_return = stats.get('total_return', 0)
            win_rate = stats.get('win_rate', 0)
            uptime = stats.get('uptime', 'N/A')
            
            status_display = f"{color}{status}\033[0m"
            
            row = f"{symbol:<10} {status:<15} {trades:<8} {self.format_number(total_return, 4):<12} {self.format_number(win_rate, 1):<10} {uptime:<10}"
            # Reemplazar el estado con la versión coloreada
            row = row.replace(status, status_display, 1)
            print(row)
            
        print("-"*80)
        
        # Información adicional
        print()
        print("\033[1mINFORMACIÓN ADICIONAL:\033[0m")
        
        for symbol in sorted(self.symbols.keys()):
            stats = self.stats.get(symbol, {})
            if stats.get('total_trades', 0) > 0:
                avg_return = stats.get('avg_return_per_trade', 0)
                last_trade = stats.get('last_trade', 'N/A')
                if last_trade != 'N/A':
                    try:
                        last_trade_dt = datetime.fromisoformat(last_trade.replace('Z', '+00:00'))
                        last_trade = last_trade_dt.strftime('%H:%M:%S')
                    except:
                        pass
                        
                print(f"  {symbol}: Retorno promedio por trade: {self.format_number(avg_return, 4)}% | Último trade: {last_trade}")
                
        print()
        print("\033[1mCONTROLES:\033[0m")
        print("  Presiona Ctrl+C para salir")
        print("  El dashboard se actualiza cada 30 segundos")
        
    def run(self):
        """Ejecuta el dashboard"""
        print("Iniciando Dashboard de Simulaciones...")
        print("Presiona Ctrl+C para salir")
        
        try:
            while self.running:
                self.update_stats()
                self.display_dashboard()
                time.sleep(30)  # Actualizar cada 30 segundos
                
        except KeyboardInterrupt:
            print("\n\nCerrando dashboard...")
            self.running = False
            
if __name__ == "__main__":
    dashboard = SimulationDashboard()
    dashboard.run()
