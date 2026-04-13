#!/usr/bin/env python3
"""
🔍 MONITOR DE SEÑALES DE TRADING V4 ULTRA-AGRESIVA

Monitor simplificado que muestra claramente las señales de trading generadas
por la estrategia V4 Ultra-Agresiva en tiempo real.

Autor: Sistema de Trading Automatizado
Versión: 4.0 Signal Monitor
Fecha: Septiembre 2024
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from colorama import init, Fore, Back, Style
from tabulate import tabulate
import warnings
warnings.filterwarnings('ignore')

# Importar estrategia V4
try:
    from enhanced_strategy_15pct_v4_ultra import Enhanced15PercentStrategyV4Ultra, UltraTradingConfig
except ImportError:
    print("⚠️ No se pudo importar la estrategia V4. Usando simulación básica.")
    Enhanced15PercentStrategyV4Ultra = None
    UltraTradingConfig = None

# Inicializar colorama
init(autoreset=True)

class SignalMonitor:
    """Monitor de señales de trading"""
    
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        self.strategy = Enhanced15PercentStrategyV4Ultra() if Enhanced15PercentStrategyV4Ultra else None
        self.config = UltraTradingConfig() if UltraTradingConfig else None
        self.signal_history = []
        self.market_data = {}
        self.price_history = {symbol: [] for symbol in self.symbols}
        
    def generate_market_data(self, symbol: str) -> dict:
        """Genera datos de mercado simulados"""
        base_prices = {
            'BTCUSDT': 43000 + np.random.normal(0, 500),
            'ETHUSDT': 2600 + np.random.normal(0, 50),
            'BNBUSDT': 310 + np.random.normal(0, 10),
            'ADAUSDT': 0.45 + np.random.normal(0, 0.02),
            'SOLUSDT': 95 + np.random.normal(0, 5)
        }
        
        price = base_prices[symbol]
        self.price_history[symbol].append(price)
        
        # Mantener solo últimos 100 precios
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        # Calcular indicadores básicos
        prices = np.array(self.price_history[symbol])
        
        # RSI
        if len(prices) >= 14:
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # MACD
        if len(prices) >= 26:
            ema12 = np.mean(prices[-12:])
            ema26 = np.mean(prices[-26:])
            macd = ema12 - ema26
            signal_line = macd * 0.9  # Simplificado
            histogram = macd - signal_line
        else:
            macd = signal_line = histogram = 0
        
        # Medias móviles
        sma20 = np.mean(prices[-20:]) if len(prices) >= 20 else price
        sma50 = np.mean(prices[-50:]) if len(prices) >= 50 else price
        
        # Volatilidad
        volatility = np.std(prices[-20:]) if len(prices) >= 20 else 0
        
        return {
            'symbol': symbol,
            'price': price,
            'rsi': rsi,
            'macd': macd,
            'macd_signal': signal_line,
            'macd_histogram': histogram,
            'sma20': sma20,
            'sma50': sma50,
            'volatility': volatility,
            'trend': 'BULLISH' if sma20 > sma50 else 'BEARISH',
            'volume': np.random.uniform(50000, 200000)
        }
    
    def generate_trading_signal(self, symbol: str, market_data: dict) -> dict:
        """Genera señal de trading usando la estrategia V4"""
        if not self.strategy:
            # Señal simulada básica
            rsi = market_data['rsi']
            macd = market_data['macd']
            trend = market_data['trend']
            
            signal_strength = 0
            signal_type = 0
            reason = "Sin estrategia cargada"
            
            # Lógica básica de señales
            if rsi < 30 and macd > 0 and trend == 'BULLISH':
                signal_strength = 0.8
                signal_type = 1  # BUY
                reason = "RSI oversold + MACD bullish + Trend up"
            elif rsi > 70 and macd < 0 and trend == 'BEARISH':
                signal_strength = 0.8
                signal_type = -1  # SELL
                reason = "RSI overbought + MACD bearish + Trend down"
            elif rsi < 35 and trend == 'BULLISH':
                signal_strength = 0.6
                signal_type = 1
                reason = "RSI oversold + Bullish trend"
            elif rsi > 65 and trend == 'BEARISH':
                signal_strength = 0.6
                signal_type = -1
                reason = "RSI overbought + Bearish trend"
            else:
                signal_strength = np.random.uniform(0, 0.4)  # Señales débiles aleatorias
                signal_type = 0
                reason = "Sin señal clara"
            
            return {
                'signal': signal_type,
                'signal_strength': signal_strength,
                'reason': reason,
                'confidence': signal_strength * 100,
                'entry_price': market_data['price'],
                'stop_loss': market_data['price'] * (0.997 if signal_type == 1 else 1.003),
                'take_profit': market_data['price'] * (1.02 if signal_type == 1 else 0.98)
            }
        
        # Usar estrategia V4 real
        try:
            # Crear DataFrame simulado
            df_data = {
                'close': [market_data['price']] * 100,
                'high': [market_data['price'] * 1.01] * 100,
                'low': [market_data['price'] * 0.99] * 100,
                'volume': [market_data['volume']] * 100
            }
            df = pd.DataFrame(df_data)
            
            signal = self.strategy.generate_ultra_signal(df)
            
            if signal:
                return {
                    'signal': signal.get('signal', 0),
                    'signal_strength': signal.get('signal_strength', 0),
                    'reason': signal.get('reason', 'Estrategia V4'),
                    'confidence': signal.get('signal_strength', 0) * 100,
                    'entry_price': market_data['price'],
                    'stop_loss': signal.get('stop_loss', market_data['price'] * 0.997),
                    'take_profit': signal.get('take_profit', market_data['price'] * 1.02)
                }
        except Exception as e:
            print(f"Error en estrategia V4: {e}")
        
        return {
            'signal': 0,
            'signal_strength': 0,
            'reason': 'Error en estrategia',
            'confidence': 0,
            'entry_price': market_data['price'],
            'stop_loss': market_data['price'],
            'take_profit': market_data['price']
        }
    
    def display_signals(self):
        """Muestra las señales de trading en tiempo real"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*100}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🔍 MONITOR DE SEÑALES DE TRADING V4 ULTRA-AGRESIVA")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*100}")
        print(f"{Fore.YELLOW}Hora actual: {datetime.now().strftime('%H:%M:%S')}")
        print(f"{Fore.YELLOW}Estrategia: {'V4 Ultra-Agresiva' if self.strategy else 'Simulación Básica'}")
        print()
        
        # Generar datos y señales para todos los símbolos
        signals_data = []
        strong_signals = []
        
        for symbol in self.symbols:
            market_data = self.generate_market_data(symbol)
            signal_data = self.generate_trading_signal(symbol, market_data)
            
            # Determinar color según la señal
            if signal_data['signal'] > 0:
                signal_color = Fore.GREEN
                signal_text = "🟢 BUY"
            elif signal_data['signal'] < 0:
                signal_color = Fore.RED
                signal_text = "🔴 SELL"
            else:
                signal_color = Fore.YELLOW
                signal_text = "⚪ HOLD"
            
            # Determinar fuerza de la señal
            strength = signal_data['signal_strength']
            if strength >= 0.7:
                strength_text = f"{Fore.GREEN}🔥 FUERTE{Style.RESET_ALL}"
                if signal_data['signal'] != 0:
                    strong_signals.append((symbol, signal_data))
            elif strength >= 0.5:
                strength_text = f"{Fore.YELLOW}⚡ MEDIA{Style.RESET_ALL}"
            else:
                strength_text = f"{Fore.WHITE}💤 DÉBIL{Style.RESET_ALL}"
            
            signals_data.append([
                symbol,
                f"${market_data['price']:.4f}",
                f"{market_data['rsi']:.1f}",
                f"{market_data['macd']:.4f}",
                market_data['trend'],
                f"{signal_color}{signal_text}{Style.RESET_ALL}",
                strength_text,
                f"{signal_data['confidence']:.1f}%",
                signal_data['reason'][:30] + "..." if len(signal_data['reason']) > 30 else signal_data['reason']
            ])
        
        # Mostrar tabla de señales
        print(f"{Fore.BLUE}{Style.BRIGHT}📊 SEÑALES DE TRADING EN TIEMPO REAL")
        print(tabulate(signals_data,
                      headers=['Símbolo', 'Precio', 'RSI', 'MACD', 'Tendencia', 'Señal', 'Fuerza', 'Confianza', 'Razón'],
                      tablefmt='grid'))
        print()
        
        # Mostrar señales fuertes
        if strong_signals:
            print(f"{Fore.RED}{Style.BRIGHT}🚨 SEÑALES FUERTES DETECTADAS:")
            for symbol, signal in strong_signals:
                action = "COMPRAR" if signal['signal'] > 0 else "VENDER"
                print(f"{Fore.WHITE}• {symbol}: {action} a ${signal['entry_price']:.4f}")
                print(f"  Confianza: {signal['confidence']:.1f}%")
                print(f"  Stop Loss: ${signal['stop_loss']:.4f}")
                print(f"  Take Profit: ${signal['take_profit']:.4f}")
                print(f"  Razón: {signal['reason']}")
                print()
        else:
            print(f"{Fore.CYAN}ℹ️ No hay señales fuertes en este momento")
        
        # Agregar al historial
        timestamp = datetime.now()
        for symbol in self.symbols:
            market_data = self.generate_market_data(symbol)
            signal_data = self.generate_trading_signal(symbol, market_data)
            
            if abs(signal_data['signal']) > 0.5:  # Solo señales significativas
                self.signal_history.append({
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'signal': signal_data['signal'],
                    'strength': signal_data['signal_strength'],
                    'price': market_data['price'],
                    'reason': signal_data['reason']
                })
        
        # Mantener solo últimas 20 señales
        if len(self.signal_history) > 20:
            self.signal_history = self.signal_history[-20:]
        
        # Mostrar historial de señales
        if self.signal_history:
            print(f"{Fore.MAGENTA}{Style.BRIGHT}📋 HISTORIAL DE SEÑALES (Últimas 10)")
            history_data = []
            for signal in self.signal_history[-10:]:
                action = "BUY" if signal['signal'] > 0 else "SELL"
                color = Fore.GREEN if signal['signal'] > 0 else Fore.RED
                history_data.append([
                    signal['timestamp'].strftime('%H:%M:%S'),
                    signal['symbol'],
                    f"{color}{action}{Style.RESET_ALL}",
                    f"${signal['price']:.4f}",
                    f"{signal['strength']:.2f}",
                    signal['reason'][:40] + "..." if len(signal['reason']) > 40 else signal['reason']
                ])
            
            print(tabulate(history_data,
                          headers=['Hora', 'Símbolo', 'Acción', 'Precio', 'Fuerza', 'Razón'],
                          tablefmt='grid'))
        
        print(f"\n{Fore.YELLOW}Presiona Ctrl+C para detener el monitor...")
    
    def run_monitor(self):
        """Ejecuta el monitor de señales"""
        print(f"{Fore.GREEN}{Style.BRIGHT}🔍 Iniciando monitor de señales...")
        print(f"{Fore.YELLOW}Presiona Ctrl+C para detener...\n")
        
        try:
            while True:
                self.display_signals()
                time.sleep(3)  # Actualizar cada 3 segundos
                
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}{Style.BRIGHT}🛑 Monitor detenido por el usuario")
            print(f"{Fore.CYAN}Total de señales registradas: {len(self.signal_history)}")
            
            # Mostrar resumen final
            if self.signal_history:
                buy_signals = len([s for s in self.signal_history if s['signal'] > 0])
                sell_signals = len([s for s in self.signal_history if s['signal'] < 0])
                avg_strength = np.mean([s['strength'] for s in self.signal_history])
                
                print(f"{Fore.GREEN}Señales de compra: {buy_signals}")
                print(f"{Fore.RED}Señales de venta: {sell_signals}")
                print(f"{Fore.YELLOW}Fuerza promedio: {avg_strength:.2f}")

def main():
    """Función principal"""
    print(f"{Fore.CYAN}{Style.BRIGHT}🔍 MONITOR DE SEÑALES DE TRADING V4")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*60}")
    
    monitor = SignalMonitor()
    monitor.run_monitor()

if __name__ == "__main__":
    main()