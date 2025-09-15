#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor de Simulaciones Multi-Terminal - 6 Instrumentos
Monitorea el progreso de las 6 simulaciones simultáneas:
- Crypto: BNBUSDT, ADAUSDT, SOLUSDT
- Índices: NAS100
- Forex: AUDCAD
- Metales: XAUUSD
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List

class SimulationMonitor6:
    def __init__(self):
        self.logs_dir = "logs_simulacion"
        # Configuración de instrumentos por categoría
        self.instruments = {
            "crypto": ["BNBUSDT", "ADAUSDT", "SOLUSDT"],
            "indices": ["NAS100"],
            "forex": ["AUDCAD"],
            "metals": ["XAUUSD"]
        }
        self.all_symbols = []
        for category in self.instruments.values():
            self.all_symbols.extend(category)
        
        self.category_icons = {
            "crypto": "₿",
            "indices": "📊",
            "forex": "💱",
            "metals": "🥇"
        }
    
    def get_latest_logs(self) -> Dict:
        """Obtiene los logs más recientes de cada simulación"""
        latest_logs = {}
        
        if not os.path.exists(self.logs_dir):
            return latest_logs
        
        for symbol in self.all_symbols:
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
            "win_rate": 0.0,
            "last_update": None,
            "status": "unknown",
            "session_start": None,
            "uptime_hours": 0.0
        }
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines:
                if line.strip():
                    event = json.loads(line)
                    
                    if event['event_type'] == 'session_start':
                        stats['session_start'] = event['timestamp']
                        stats['status'] = "running"
                    
                    elif event['event_type'] == 'trade_executed':
                        stats['total_trades'] += 1
                        if event['data']['is_winner']:
                            stats['winning_trades'] += 1
                    
                    elif event['event_type'] == 'performance_update':
                        stats['current_capital'] = event['data']['current_capital']
                        stats['total_return'] = event['data']['total_return_pct']
                        stats['win_rate'] = event['data']['win_rate_pct']
                        stats['last_update'] = event['timestamp']
                        stats['status'] = "running"
                    
                    elif event['event_type'] == 'simulation_end':
                        if 'simulation_summary' in event['data']:
                            summary = event['data']['simulation_summary']
                            stats['current_capital'] = summary['final_capital']
                            stats['total_return'] = summary['total_return_pct']
                        if 'trading_stats' in event['data']:
                            trading = event['data']['trading_stats']
                            stats['total_trades'] = trading['total_trades']
                            stats['winning_trades'] = trading['winning_trades']
                            stats['win_rate'] = trading['win_rate_pct']
                        stats['last_update'] = event['timestamp']
                        stats['status'] = "completed"
            
            # Calcular uptime
            if stats['session_start'] and stats['last_update']:
                start_time = datetime.fromisoformat(stats['session_start'].replace('Z', '+00:00'))
                last_time = datetime.fromisoformat(stats['last_update'].replace('Z', '+00:00'))
                stats['uptime_hours'] = (last_time - start_time).total_seconds() / 3600
        
        except Exception as e:
            stats['status'] = f"error: {str(e)}"
        
        return stats
    
    def get_category_for_symbol(self, symbol: str) -> str:
        """Determina la categoría de un símbolo"""
        for category, symbols in self.instruments.items():
            if symbol in symbols:
                return category
        return "unknown"
    
    def display_dashboard(self):
        """Muestra dashboard en tiempo real para 6 simulaciones"""
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 100)
            print("🚀 MONITOR DE SIMULACIONES MULTI-ASSET - 6 INSTRUMENTOS")
            print(f"📅 Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 100)
            
            latest_logs = self.get_latest_logs()
            
            if not latest_logs:
                print("❌ No se encontraron logs de simulación")
                print("   Asegúrate de que las simulaciones estén ejecutándose")
            else:
                # Estadísticas por categoría
                category_stats = {}
                total_capital = 0
                total_return = 0
                active_simulations = 0
                total_trades = 0
                total_winning_trades = 0
                
                # Procesar cada categoría
                for category, symbols in self.instruments.items():
                    category_stats[category] = {
                        'capital': 0,
                        'return': 0,
                        'active': 0,
                        'total': len(symbols),
                        'trades': 0,
                        'winning_trades': 0
                    }
                    
                    print(f"\n{self.category_icons[category]} {category.upper()}:")
                    print("-" * 50)
                    
                    for symbol in symbols:
                        if symbol in latest_logs:
                            stats = self.parse_log_file(latest_logs[symbol])
                            
                            # Determinar estado visual
                            if stats['status'] == 'running':
                                status_icon = "🟢"
                                active_simulations += 1
                                category_stats[category]['active'] += 1
                            elif stats['status'] == 'completed':
                                status_icon = "✅"
                            else:
                                status_icon = "❌"
                            
                            print(f"  {status_icon} {symbol}:")
                            print(f"     💰 Capital: ${stats['current_capital']:,.2f} ({stats['total_return']:+.2f}%)")
                            print(f"     📊 Trades: {stats['total_trades']} | Win Rate: {stats['win_rate']:.1f}%")
                            print(f"     ⏱️  Uptime: {stats['uptime_hours']:.1f}h | Estado: {stats['status']}")
                            
                            if stats['status'] in ['running', 'completed']:
                                category_stats[category]['capital'] += stats['current_capital']
                                category_stats[category]['return'] += stats['total_return']
                                category_stats[category]['trades'] += stats['total_trades']
                                category_stats[category]['winning_trades'] += stats['winning_trades']
                                
                                total_capital += stats['current_capital']
                                total_return += stats['total_return']
                                total_trades += stats['total_trades']
                                total_winning_trades += stats['winning_trades']
                        else:
                            print(f"  ⚪ {symbol}: Sin datos")
                
                # Resumen por categorías
                print("\n" + "=" * 100)
                print("📈 RESUMEN POR CATEGORÍAS:")
                print("=" * 100)
                
                for category, data in category_stats.items():
                    if data['total'] > 0:
                        avg_return = data['return'] / data['total'] if data['total'] > 0 else 0
                        win_rate = (data['winning_trades'] / data['trades'] * 100) if data['trades'] > 0 else 0
                        
                        print(f"{self.category_icons[category]} {category.upper()}:")
                        print(f"   Capital Total: ${data['capital']:,.2f} | Retorno Promedio: {avg_return:+.2f}%")
                        print(f"   Activas: {data['active']}/{data['total']} | Trades: {data['trades']} | Win Rate: {win_rate:.1f}%")
                
                # Resumen total del portfolio
                print("\n" + "=" * 100)
                print("🏆 RESUMEN TOTAL DEL PORTFOLIO:")
                print("=" * 100)
                
                initial_capital = 6000  # $1000 x 6 simulaciones
                portfolio_return = ((total_capital - initial_capital) / initial_capital) * 100
                avg_return = total_return / 6 if total_return > 0 else 0
                overall_win_rate = (total_winning_trades / total_trades * 100) if total_trades > 0 else 0
                
                print(f"💰 Capital Total: ${total_capital:,.2f} (de ${initial_capital:,.2f} inicial)")
                print(f"📈 Retorno del Portfolio: {portfolio_return:+.2f}%")
                print(f"📊 Retorno Promedio por Instrumento: {avg_return:+.2f}%")
                print(f"🎯 Simulaciones Activas: {active_simulations}/6")
                print(f"📋 Total de Trades: {total_trades} | Win Rate Global: {overall_win_rate:.1f}%")
                
                # Indicadores de rendimiento
                if portfolio_return > 2:
                    performance_icon = "🚀"
                    performance_text = "EXCELENTE"
                elif portfolio_return > 0:
                    performance_icon = "📈"
                    performance_text = "POSITIVO"
                elif portfolio_return > -2:
                    performance_icon = "⚠️"
                    performance_text = "NEUTRAL"
                else:
                    performance_icon = "📉"
                    performance_text = "REVISAR"
                
                print(f"\n{performance_icon} Rendimiento del Portfolio: {performance_text}")
            
            print("\n" + "=" * 100)
            print("⌨️  Presiona Ctrl+C para salir del monitor")
            
            try:
                time.sleep(5)  # Actualizar cada 5 segundos
            except KeyboardInterrupt:
                print("\n👋 Monitor cerrado")
                break

if __name__ == "__main__":
    monitor = SimulationMonitor6()
    monitor.display_dashboard()