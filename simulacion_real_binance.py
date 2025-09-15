#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador de Trading con Datos Reales de Binance
Usa precios en tiempo real de la API de Binance para simular trades
"""

import os
import json
import time
import random
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import signal
import sys
import traceback

# Configurar claves API de Binance
os.environ['BINANCE_API_KEY'] = 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs'
os.environ['BINANCE_SECRET_KEY'] = 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'

class BinanceRealDataSimulator:
    """Simulador que usa datos reales de Binance para generar trades"""
    
    def __init__(self, symbol: str, initial_capital: float = 1000.0, terminal_id: int = 1):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.terminal_id = terminal_id
        self.trades = []
        self.running = True
        self.start_time = datetime.now()
        
        # Configuración de trading
        self.win_rate = 0.65  # 65% de trades ganadores
        self.avg_return = 0.008  # 0.8% retorno promedio semanal
        self.volatility = 0.015  # 1.5% volatilidad
        self.trade_frequency = 300  # Trade cada 5 minutos (300 segundos)
        
        # API de Binance
        self.base_url = "https://api.binance.com/api/v3"
        
        # Archivos de log
        self.log_file = f"simulacion_{symbol.lower()}_{terminal_id}.jsonl"
        self.report_file = f"reporte_{symbol.lower()}_{terminal_id}.json"
        
        # Configurar manejador de señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print(f"\n🚀 Iniciando simulación con datos reales de Binance")
        print(f"📊 Símbolo: {self.symbol}")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print(f"🖥️  Terminal: {self.terminal_id}")
        print(f"📝 Log: {self.log_file}")
        print(f"⏰ Frecuencia de trading: {self.trade_frequency}s")
        
    def _signal_handler(self, signum, frame):
        """Manejador de señales para cierre limpio"""
        print(f"\n⚠️  Señal {signum} recibida. Cerrando simulación...")
        self.running = False
        
    def get_real_price(self) -> Optional[float]:
        """Obtiene el precio actual del símbolo desde Binance con reintentos"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/ticker/price"
                params = {'symbol': self.symbol}
                
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    return float(data['price'])
                elif response.status_code == 429:  # Rate limit
                    print(f"⚠️  Rate limit alcanzado, esperando {retry_delay * 2}s...")
                    time.sleep(retry_delay * 2)
                    continue
                else:
                    print(f"⚠️  Error API Binance: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None
                    
            except requests.exceptions.Timeout:
                print(f"⚠️  Timeout en intento {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
            except requests.exceptions.ConnectionError:
                print(f"⚠️  Error de conexión en intento {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * 2)
                    continue
            except Exception as e:
                print(f"❌ Error obteniendo precio (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
        
        print(f"❌ No se pudo obtener precio después de {max_retries} intentos")
        return None
    
    def get_price_history(self, limit: int = 100) -> List[float]:
        """Obtiene historial de precios para análisis de tendencia con reintentos"""
        max_retries = 2
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                url = f"{self.base_url}/klines"
                params = {
                    'symbol': self.symbol,
                    'interval': '1m',  # Velas de 1 minuto
                    'limit': limit
                }
                
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    klines = response.json()
                    # Extraer precios de cierre
                    prices = [float(kline[4]) for kline in klines]
                    return prices
                elif response.status_code == 429:  # Rate limit
                    print(f"⚠️  Rate limit en historial, esperando {retry_delay * 2}s...")
                    time.sleep(retry_delay * 2)
                    continue
                else:
                    print(f"⚠️  Error API historial: {response.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return []
                    
            except requests.exceptions.Timeout:
                print(f"⚠️  Timeout historial intento {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
            except requests.exceptions.ConnectionError:
                print(f"⚠️  Error conexión historial intento {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * 2)
                    continue
            except Exception as e:
                print(f"❌ Error obteniendo historial (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
        
        print(f"⚠️  Usando datos históricos vacíos después de {max_retries} intentos")
        return []
    
    def analyze_market_trend(self, prices: List[float]) -> str:
        """Analiza la tendencia del mercado basado en precios históricos"""
        if len(prices) < 10:
            return "neutral"
        
        # Calcular medias móviles simples
        short_ma = sum(prices[-5:]) / 5  # Media de 5 períodos
        long_ma = sum(prices[-20:]) / 20  # Media de 20 períodos
        
        if short_ma > long_ma * 1.001:  # 0.1% por encima
            return "bullish"
        elif short_ma < long_ma * 0.999:  # 0.1% por debajo
            return "bearish"
        else:
            return "neutral"
    
    def simulate_trade_with_real_data(self, current_price: float, trend: str) -> Dict:
        """Simula un trade usando el precio real y análisis de tendencia"""
        # Ajustar probabilidades según la tendencia
        if trend == "bullish":
            win_probability = self.win_rate + 0.1  # +10% en tendencia alcista
        elif trend == "bearish":
            win_probability = self.win_rate - 0.1  # -10% en tendencia bajista
        else:
            win_probability = self.win_rate
        
        # Determinar si el trade es ganador
        is_winner = random.random() < win_probability
        
        # Calcular retorno basado en volatilidad real y tendencia
        if is_winner:
            base_return = abs(random.gauss(self.avg_return, self.volatility))
            if trend == "bullish":
                return_pct = base_return * random.uniform(1.2, 2.0)  # Mayores ganancias en tendencia alcista
            else:
                return_pct = base_return * random.uniform(0.8, 1.5)
        else:
            # Pérdidas más controladas
            return_pct = -abs(random.gauss(self.avg_return * 0.6, self.volatility * 0.8))
        
        # Calcular monto del trade (1-3% del capital)
        trade_amount = self.current_capital * random.uniform(0.01, 0.03)
        
        # Calcular P&L
        pnl = trade_amount * return_pct
        
        # Calcular pips basándose en el movimiento de precio
        # Para crypto, 1 pip = 0.01 (centavo)
        price_movement = current_price * (return_pct / 100)  # Movimiento absoluto del precio
        pips = price_movement / 0.01  # Convertir a pips
        
        return {
            'timestamp': datetime.now().isoformat(),
            'symbol': self.symbol,
            'price': current_price,
            'trend': trend,
            'trade_amount': trade_amount,
            'return_pct': return_pct * 100,  # Convertir a porcentaje
            'pnl': pnl,
            'pips': pips,  # Añadir pips calculados
            'is_winner': is_winner,
            'capital_before': self.current_capital,
            'capital_after': self.current_capital + pnl
        }
    
    def log_event(self, event_type: str, data: Dict):
        """Registra eventos en formato JSON Lines"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'terminal': self.terminal_id,
            'symbol': self.symbol,
            'event_type': event_type,
            'data': data
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"❌ Error escribiendo log: {e}")
    
    def display_progress(self, trade_data: Dict, trade_count: int, elapsed_time: timedelta):
        """Muestra el progreso de la simulación"""
        hours = elapsed_time.total_seconds() / 3600
        
        print(f"\n📊 Trade #{trade_count} - {self.symbol}")
        print(f"💰 Precio actual: ${trade_data['price']:,.4f}")
        print(f"📈 Tendencia: {trade_data['trend'].upper()}")
        print(f"💵 Monto trade: ${trade_data['trade_amount']:,.2f}")
        print(f"📊 Retorno: {trade_data['return_pct']:+.2f}%")
        print(f"💸 P&L: ${trade_data['pnl']:+.2f}")
        print(f"💰 Capital: ${trade_data['capital_after']:,.2f}")
        print(f"⏱️  Tiempo transcurrido: {hours:.1f}h")
        
        # Calcular estadísticas
        if self.trades:
            winning_trades = sum(1 for t in self.trades if t['is_winner'])
            win_rate = (winning_trades / len(self.trades)) * 100
            total_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
            
            print(f"📈 Win Rate: {win_rate:.1f}%")
            print(f"📊 Retorno total: {total_return:+.2f}%")
        
        print("-" * 50)
    
    def run_simulation(self, duration_hours: int = None):
        """Ejecuta la simulación indefinidamente hasta ser detenida manualmente"""
        if duration_hours:
            print(f"\n🎯 Iniciando simulación de {duration_hours} horas")
        else:
            print(f"\n🎯 Iniciando simulación indefinida (hasta detener manualmente)")
        print(f"⏰ Inicio: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Log inicial
        self.log_event('simulation_start', {
            'symbol': self.symbol,
            'initial_capital': self.initial_capital,
            'duration_hours': duration_hours or 'indefinite',
            'terminal_id': self.terminal_id
        })
        
        trade_count = 0
        end_time = self.start_time + timedelta(hours=duration_hours) if duration_hours else None
        
        try:
            while self.running and (end_time is None or datetime.now() < end_time):
                # Obtener precio actual con manejo robusto
                current_price = self.get_real_price()
                
                if current_price is None:
                    print("⚠️  No se pudo obtener precio, esperando 60s...")
                    time.sleep(60)
                    # Intentar hasta 3 veces antes de continuar
                    retry_count = 0
                    while current_price is None and retry_count < 3:
                        retry_count += 1
                        print(f"🔄 Reintentando obtener precio ({retry_count}/3)...")
                        time.sleep(30)
                        current_price = self.get_real_price()
                    
                    if current_price is None:
                        print("⚠️  Saltando este ciclo de trading por problemas de conectividad")
                        continue
                
                # Obtener historial para análisis
                price_history = self.get_price_history()
                trend = self.analyze_market_trend(price_history)
                
                # Simular trade
                trade_data = self.simulate_trade_with_real_data(current_price, trend)
                
                # Actualizar capital
                self.current_capital = trade_data['capital_after']
                
                # Guardar trade
                self.trades.append(trade_data)
                trade_count += 1
                
                # Log del trade
                self.log_event('trade_executed', trade_data)
                
                # Mostrar progreso
                elapsed_time = datetime.now() - self.start_time
                self.display_progress(trade_data, trade_count, elapsed_time)
                
                # Verificar stop loss (pérdida del 20%)
                if self.current_capital < self.initial_capital * 0.8:
                    print(f"\n🛑 STOP LOSS activado. Capital: ${self.current_capital:,.2f}")
                    break
                
                # Esperar antes del siguiente trade
                time.sleep(self.trade_frequency)
                
        except KeyboardInterrupt:
            print(f"\n⚠️  Simulación interrumpida por el usuario")
        except Exception as e:
            print(f"\n❌ Error durante la simulación: {e}")
            print(f"📋 Traceback: {traceback.format_exc()}")
            # Continuar para generar reporte final
        
        # Generar reporte final
        try:
            self.generate_final_report()
        except Exception as e:
            print(f"❌ Error generando reporte final: {e}")
            # Crear reporte mínimo
            try:
                minimal_report = {
                    'error': 'Error generando reporte completo',
                    'trades_count': len(self.trades),
                    'final_capital': self.current_capital,
                    'timestamp': datetime.now().isoformat()
                }
                with open(self.report_file, 'w', encoding='utf-8') as f:
                    json.dump(minimal_report, f, indent=2)
                print(f"📝 Reporte mínimo guardado: {self.report_file}")
            except Exception:
                print("❌ No se pudo guardar ningún reporte")
    
    def generate_final_report(self):
        """Genera el reporte final de la simulación"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        # Calcular estadísticas
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t['is_winner'])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        final_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        total_pnl = sum(t['pnl'] for t in self.trades)
        
        # Crear reporte
        report = {
            'simulation_summary': {
                'symbol': self.symbol,
                'terminal_id': self.terminal_id,
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_hours': duration.total_seconds() / 3600,
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'total_return_pct': final_return,
                'total_pnl': total_pnl
            },
            'trading_stats': {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': total_trades - winning_trades,
                'win_rate_pct': win_rate,
                'avg_trade_size': sum(t['trade_amount'] for t in self.trades) / total_trades if total_trades > 0 else 0
            },
            'performance_metrics': {
                'best_trade': max(self.trades, key=lambda x: x['pnl'])['pnl'] if self.trades else 0,
                'worst_trade': min(self.trades, key=lambda x: x['pnl'])['pnl'] if self.trades else 0,
                'avg_return_per_trade': sum(t['return_pct'] for t in self.trades) / total_trades if total_trades > 0 else 0
            }
        }
        
        # Guardar reporte
        try:
            with open(self.report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error guardando reporte: {e}")
        
        # Log final
        self.log_event('simulation_end', report)
        
        # Mostrar resumen en consola
        print(f"\n" + "=" * 60)
        print(f"📊 REPORTE FINAL - {self.symbol} (Terminal {self.terminal_id})")
        print(f"=" * 60)
        print(f"⏰ Duración: {duration.total_seconds()/3600:.1f} horas")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print(f"💰 Capital final: ${self.current_capital:,.2f}")
        print(f"📈 Retorno total: {final_return:+.2f}%")
        print(f"💸 P&L total: ${total_pnl:+.2f}")
        print(f"📊 Trades ejecutados: {total_trades}")
        print(f"✅ Trades ganadores: {winning_trades} ({win_rate:.1f}%)")
        print(f"❌ Trades perdedores: {total_trades - winning_trades}")
        print(f"📝 Reporte guardado: {self.report_file}")
        print(f"📋 Log completo: {self.log_file}")
        print(f"=" * 60)

def main():
    """Función principal"""
    if len(sys.argv) < 2:
        print("Uso: python simulacion_real_binance.py <SYMBOL> [TERMINAL_ID]")
        print("Ejemplo: python simulacion_real_binance.py BTCUSDT 1")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    terminal_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    # Crear y ejecutar simulador
    simulator = BinanceRealDataSimulator(
        symbol=symbol,
        initial_capital=1000.0,
        terminal_id=terminal_id
    )
    
    # Ejecutar simulación indefinidamente
    simulator.run_simulation()

if __name__ == "__main__":
    main()