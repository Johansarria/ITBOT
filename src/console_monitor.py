#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MONITOR DE CONSOLA EN TIEMPO REAL
=================================
Sistema de seguimiento por consola para la simulación de primera vela
"""

import json
import time
import requests
from datetime import datetime, timedelta
import pytz
import os
import sys

class ConsoleMonitor:
    """Monitor de consola para seguimiento en tiempo real"""
    
    def __init__(self):
        self.config = self.load_config()
        self.session_data_file = 'real_time_session_data.json'
        self.last_update = None
        
    def load_config(self):
        """Carga configuración del sistema"""
        try:
            with open('first_candle_strategy_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def load_session_data(self):
        """Carga datos de la sesión actual"""
        try:
            with open(self.session_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                'current_capital': 250.0,
                'positions': {},
                'trades_history': [],
                'session_trades_count': 0
            }
    
    def get_binance_price(self, symbol):
        """Obtiene precio actual de Binance"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url, timeout=5)
            data = response.json()
            return float(data['price'])
        except:
            return 0.0
    
    def calculate_next_session_time(self):
        """Calcula tiempo hasta la próxima sesión"""
        utc_now = datetime.now(pytz.UTC)
        session_hour = self.config.get('strategy_parameters', {}).get('session_start_hour', 8)
        
        # Próxima sesión hoy
        next_session_today = utc_now.replace(hour=session_hour, minute=0, second=0, microsecond=0)
        
        # Si ya pasó la hora de hoy, calcular para mañana
        if utc_now >= next_session_today:
            next_session = next_session_today + timedelta(days=1)
        else:
            next_session = next_session_today
        
        time_remaining = next_session - utc_now
        return next_session, time_remaining
    
    def format_time_remaining(self, time_remaining):
        """Formatea tiempo restante"""
        total_seconds = int(time_remaining.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def clear_screen(self):
        """Limpia la pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Muestra encabezado del monitor"""
        print("=" * 80)
        print("🚀 MONITOR DE CONSOLA - SISTEMA PRIMERA VELA")
        print("=" * 80)
        print(f"⏰ Hora actual (UTC): {datetime.now(pytz.UTC).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calcular próxima sesión
        next_session, time_remaining = self.calculate_next_session_time()
        print(f"🎯 Próxima sesión: {next_session.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"⏳ Tiempo restante: {self.format_time_remaining(time_remaining)}")
        print("=" * 80)
    
    def display_market_prices(self):
        """Muestra precios actuales del mercado"""
        print("\n📊 PRECIOS ACTUALES DEL MERCADO")
        print("-" * 50)
        
        symbols = self.config.get('symbols', ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT'])
        
        for symbol in symbols:
            price = self.get_binance_price(symbol)
            if price > 0:
                print(f"{symbol:10} ${price:>12,.4f}")
            else:
                print(f"{symbol:10} {'ERROR':>12}")
    
    def display_system_status(self):
        """Muestra estado del sistema"""
        session_data = self.load_session_data()
        
        print("\n💰 ESTADO DEL SISTEMA")
        print("-" * 50)
        
        # Capital y rendimiento
        initial_capital = self.config.get('capital_management', {}).get('initial_capital', 250)
        current_capital = session_data.get('current_capital', initial_capital)
        total_return = ((current_capital - initial_capital) / initial_capital) * 100
        
        print(f"Capital inicial:     ${initial_capital:>10.2f}")
        print(f"Capital actual:      ${current_capital:>10.2f}")
        print(f"Retorno total:       {total_return:>10.2f}%")
        
        # Posiciones
        positions = session_data.get('positions', {})
        open_positions = [p for p in positions.values() if p.get('status') == 'OPEN']
        print(f"Posiciones abiertas: {len(open_positions):>10}")
        
        # Trades
        trades_history = session_data.get('trades_history', [])
        session_trades = session_data.get('session_trades_count', 0)
        max_daily = self.config.get('risk_management', {}).get('max_daily_trades', 8)
        
        print(f"Total trades:        {len(trades_history):>10}")
        print(f"Trades hoy:          {session_trades:>10}/{max_daily}")
        
        # Estadísticas de rendimiento
        if trades_history:
            winning_trades = len([t for t in trades_history if t.get('result') == 'WIN'])
            win_rate = (winning_trades / len(trades_history)) * 100
            total_pnl = sum([t.get('pnl', 0) for t in trades_history])
            
            print(f"Tasa de aciertos:    {win_rate:>10.1f}%")
            print(f"P&L total:           ${total_pnl:>10.2f}")
        else:
            print(f"Tasa de aciertos:    {'0.0%':>10}")
            print(f"P&L total:           ${'0.00':>10}")
    
    def display_open_positions(self):
        """Muestra posiciones abiertas"""
        session_data = self.load_session_data()
        positions = session_data.get('positions', {})
        open_positions = {k: v for k, v in positions.items() if v.get('status') == 'OPEN'}
        
        if open_positions:
            print("\n📈 POSICIONES ABIERTAS")
            print("-" * 80)
            print(f"{'Símbolo':<10} {'Tipo':<5} {'Entrada':<12} {'Actual':<12} {'P&L':<12} {'%':<8}")
            print("-" * 80)
            
            for pos_id, pos in open_positions.items():
                symbol = pos.get('symbol', '')
                pos_type = pos.get('type', '')
                entry_price = pos.get('entry_price', 0)
                current_price = self.get_binance_price(symbol)
                position_size = pos.get('position_size', 0)
                
                if current_price > 0:
                    if pos_type == 'BUY':
                        pnl = (current_price - entry_price) / entry_price * position_size
                    else:
                        pnl = (entry_price - current_price) / entry_price * position_size
                    
                    pnl_pct = (pnl / position_size) * 100 if position_size > 0 else 0
                    
                    print(f"{symbol:<10} {pos_type:<5} ${entry_price:<11.4f} ${current_price:<11.4f} ${pnl:<11.2f} {pnl_pct:<7.2f}%")
        else:
            print("\n📈 POSICIONES ABIERTAS")
            print("-" * 50)
            print("No hay posiciones abiertas actualmente")
    
    def display_recent_trades(self):
        """Muestra trades recientes"""
        session_data = self.load_session_data()
        trades_history = session_data.get('trades_history', [])
        
        if trades_history:
            print("\n📊 ÚLTIMOS 5 TRADES")
            print("-" * 80)
            print(f"{'Símbolo':<10} {'Tipo':<5} {'Entrada':<12} {'Salida':<12} {'P&L':<12} {'Resultado':<10}")
            print("-" * 80)
            
            # Mostrar últimos 5 trades
            recent_trades = trades_history[-5:]
            for trade in recent_trades:
                symbol = trade.get('symbol', '')
                trade_type = trade.get('type', '')
                entry_price = trade.get('entry_price', 0)
                exit_price = trade.get('exit_price', 0)
                pnl = trade.get('pnl', 0)
                result = trade.get('result', '')
                
                print(f"{symbol:<10} {trade_type:<5} ${entry_price:<11.4f} ${exit_price:<11.4f} ${pnl:<11.2f} {result:<10}")
        else:
            print("\n📊 ÚLTIMOS TRADES")
            print("-" * 50)
            print("No hay historial de trades disponible")
    
    def display_footer(self):
        """Muestra pie de página"""
        print("\n" + "=" * 80)
        print("🔄 Actualizando cada 30 segundos | Presiona Ctrl+C para salir")
        print("=" * 80)
    
    def run_monitor(self):
        """Ejecuta el monitor en tiempo real"""
        print("🚀 Iniciando Monitor de Consola...")
        print("Presiona Ctrl+C para salir\n")
        
        try:
            while True:
                self.clear_screen()
                self.display_header()
                self.display_market_prices()
                self.display_system_status()
                self.display_open_positions()
                self.display_recent_trades()
                self.display_footer()
                
                # Esperar 30 segundos antes de la próxima actualización
                time.sleep(30)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Monitor detenido por el usuario")
            print("¡Gracias por usar el Monitor de Consola!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error en el monitor: {str(e)}")
            sys.exit(1)

def main():
    """Función principal"""
    monitor = ConsoleMonitor()
    monitor.run_monitor()

if __name__ == "__main__":
    main()