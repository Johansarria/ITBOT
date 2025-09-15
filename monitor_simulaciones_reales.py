#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Monitor en tiempo real para simulaciones con datos reales de Binance
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import glob

class RealSimulationMonitor:
    """Monitor para simulaciones con datos reales de Binance"""
    
    def __init__(self):
        self.symbols = ['BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        self.terminal_mapping = {
            'BNBUSDT': 1,
            'ADAUSDT': 2,
            'SOLUSDT': 3
        }
        self.refresh_interval = 5  # segundos
        
    def read_simulation_logs(self, symbol: str) -> Dict:
        """Lee los logs de una simulación específica"""
        terminal_id = self.terminal_mapping.get(symbol, 1)
        log_file = f"simulacion_{symbol.lower()}_{terminal_id}.jsonl"
        
        if not os.path.exists(log_file):
            return {
                'status': 'not_started',
                'symbol': symbol,
                'terminal': terminal_id,
                'message': 'Simulación no iniciada'
            }
        
        try:
            trades = []
            simulation_info = None
            last_update = None
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        
                        if entry['event_type'] == 'simulation_start':
                            simulation_info = entry['data']
                        elif entry['event_type'] == 'trade_executed':
                            trades.append(entry['data'])
                            last_update = entry['timestamp']
                        elif entry['event_type'] == 'simulation_end':
                            return {
                                'status': 'completed',
                                'symbol': symbol,
                                'terminal': terminal_id,
                                'final_report': entry['data']
                            }
                    except json.JSONDecodeError:
                        continue
            
            if not trades:
                return {
                    'status': 'starting',
                    'symbol': symbol,
                    'terminal': terminal_id,
                    'message': 'Simulación iniciando...'
                }
            
            # Calcular estadísticas
            current_capital = trades[-1]['capital_after'] if trades else 1000.0
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t['is_winner'])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_return = ((current_capital - 1000.0) / 1000.0) * 100
            
            # Verificar si está activa (última actualización en los últimos 10 minutos)
            if last_update:
                last_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                time_diff = datetime.now() - last_time.replace(tzinfo=None)
                is_active = time_diff < timedelta(minutes=10)
            else:
                is_active = False
            
            return {
                'status': 'running' if is_active else 'stalled',
                'symbol': symbol,
                'terminal': terminal_id,
                'current_capital': current_capital,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'total_return': total_return,
                'last_trade': trades[-1] if trades else None,
                'last_update': last_update,
                'is_active': is_active
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'symbol': symbol,
                'terminal': terminal_id,
                'error': str(e)
            }
    
    def get_status_icon(self, status: str, is_active: bool = True) -> str:
        """Retorna el icono de estado apropiado"""
        if status == 'running' and is_active:
            return '🟢'
        elif status == 'running' and not is_active:
            return '🟡'
        elif status == 'completed':
            return '✅'
        elif status == 'error':
            return '❌'
        elif status == 'starting':
            return '🔄'
        else:
            return '⚪'
    
    def display_dashboard(self):
        """Muestra el dashboard en tiempo real"""
        # Limpiar pantalla
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 80)
        print("📊 MONITOR DE SIMULACIONES CON DATOS REALES DE BINANCE")
        print("=" * 80)
        print(f"⏰ Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 Actualización automática cada {self.refresh_interval}s")
        print()
        
        total_capital = 0
        total_trades = 0
        active_simulations = 0
        total_return = 0
        
        for symbol in self.symbols:
            data = self.read_simulation_logs(symbol)
            status = data['status']
            terminal = data['terminal']
            
            status_icon = self.get_status_icon(status, data.get('is_active', False))
            
            print(f"{status_icon} {symbol} (Terminal {terminal}):")
            
            if status == 'running' or status == 'stalled':
                capital = data['current_capital']
                trades = data['total_trades']
                win_rate = data['win_rate']
                return_pct = data['total_return']
                
                total_capital += capital
                total_trades += trades
                total_return += return_pct
                
                if data.get('is_active', False):
                    active_simulations += 1
                
                # Mostrar último trade
                last_trade = data.get('last_trade')
                if last_trade:
                    price = last_trade['price']
                    trend = last_trade['trend']
                    pnl = last_trade['pnl']
                    
                    print(f"   💰 Capital: ${capital:,.2f} ({return_pct:+.2f}%)")
                    print(f"   📊 Trades: {trades} | Win Rate: {win_rate:.1f}%")
                    print(f"   💵 Precio actual: ${price:,.4f} | Tendencia: {trend.upper()}")
                    print(f"   📈 Último P&L: ${pnl:+.2f}")
                    
                    if data.get('last_update'):
                        last_time = datetime.fromisoformat(data['last_update'].replace('Z', '+00:00'))
                        print(f"   ⏰ Última actualización: {last_time.strftime('%H:%M:%S')}")
                else:
                    print(f"   💰 Capital: ${capital:,.2f}")
                    print(f"   📊 Trades: {trades}")
                    print(f"   ⚠️  Sin datos de último trade")
                    
            elif status == 'completed':
                final_report = data.get('final_report', {})
                if final_report:
                    summary = final_report.get('simulation_summary', {})
                    stats = final_report.get('trading_stats', {})
                    
                    final_capital = summary.get('final_capital', 0)
                    final_return = summary.get('total_return_pct', 0)
                    total_trades_final = stats.get('total_trades', 0)
                    win_rate_final = stats.get('win_rate_pct', 0)
                    
                    print(f"   ✅ COMPLETADA")
                    print(f"   💰 Capital final: ${final_capital:,.2f} ({final_return:+.2f}%)")
                    print(f"   📊 Trades totales: {total_trades_final} | Win Rate: {win_rate_final:.1f}%")
                else:
                    print(f"   ✅ COMPLETADA (sin detalles)")
                    
            elif status == 'starting':
                print(f"   🔄 {data.get('message', 'Iniciando...')}")
                
            elif status == 'not_started':
                print(f"   ⚪ {data.get('message', 'No iniciada')}")
                
            elif status == 'error':
                print(f"   ❌ ERROR: {data.get('error', 'Error desconocido')}")
            
            print()
        
        # Resumen general
        print("-" * 80)
        print("📈 RESUMEN GENERAL:")
        print(f"💰 Capital total: ${total_capital:,.2f}")
        print(f"📊 Trades totales: {total_trades}")
        print(f"🟢 Simulaciones activas: {active_simulations}/{len(self.symbols)}")
        if active_simulations > 0:
            avg_return = total_return / active_simulations
            print(f"📈 Retorno promedio: {avg_return:+.2f}%")
        print("-" * 80)
        
        # Información adicional
        print("💡 INFORMACIÓN:")
        print("   🟢 = Activa y operando")
        print("   🟡 = Pausada o sin actividad reciente")
        print("   ✅ = Completada exitosamente")
        print("   🔄 = Iniciando")
        print("   ⚪ = No iniciada")
        print("   ❌ = Error")
        print()
        print("📡 Datos en tiempo real desde API de Binance")
        print("⚠️  Presiona Ctrl+C para salir")
    
    def run(self):
        """Ejecuta el monitor en tiempo real"""
        print("🚀 Iniciando monitor de simulaciones reales...")
        print("📡 Conectando con datos de Binance...")
        time.sleep(2)
        
        try:
            while True:
                self.display_dashboard()
                time.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Monitor detenido por el usuario")
            print("👋 ¡Hasta luego!")

def main():
    """Función principal"""
    monitor = RealSimulationMonitor()
    monitor.run()

if __name__ == "__main__":
    main()