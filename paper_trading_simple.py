#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Paper Trading Simplificado en Tiempo Real
Simula datos de Binance con actualización cada 30 segundos
Solo usa librerías estándar de Python
"""

import json
import time
import os
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import urllib.request
import urllib.error

# Configuración
SYMBOLS = ['SOLUSDT', 'BNBUSDT', 'ADAUSDT']
CAPITAL_INICIAL = 500.0  # USDT por símbolo
REFRESH_INTERVAL = 30  # segundos
SIMULATED_MODE = True  # True para datos simulados, False para intentar API real

@dataclass
class Trade:
    """Representa un trade ejecutado"""
    symbol: str
    side: str  # 'BUY' o 'SELL'
    quantity: float
    price: float
    timestamp: datetime
    trade_id: str
    
@dataclass
class Position:
    """Representa una posición actual"""
    symbol: str
    quantity: float = 0.0
    avg_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
@dataclass
class MarketData:
    """Datos de mercado en tiempo real"""
    symbol: str
    price: float = 0.0
    volume_24h: float = 0.0
    price_change_24h: float = 0.0
    price_change_percent_24h: float = 0.0
    high_24h: float = 0.0
    low_24h: float = 0.0
    last_update: datetime = field(default_factory=datetime.now)

class MarketDataProvider:
    """Proveedor de datos de mercado"""
    
    def __init__(self):
        # Precios base realistas (aproximados a diciembre 2024)
        self.base_prices = {
            'SOLUSDT': 200.0,
            'BNBUSDT': 700.0,
            'ADAUSDT': 0.90
        }
        self.price_trends = {symbol: 0.0 for symbol in SYMBOLS}
        self.last_prices = self.base_prices.copy()
        
    def get_simulated_data(self, symbol: str) -> dict:
        """Genera datos simulados realistas"""
        base_price = self.base_prices[symbol]
        
        # Simular movimiento de precio con tendencia y volatilidad
        volatility = random.uniform(-0.02, 0.02)  # ±2% volatilidad
        trend_change = random.uniform(-0.001, 0.001)  # Cambio de tendencia
        
        self.price_trends[symbol] += trend_change
        self.price_trends[symbol] = max(-0.05, min(0.05, self.price_trends[symbol]))  # Limitar tendencia
        
        # Calcular nuevo precio
        price_change = volatility + self.price_trends[symbol]
        new_price = self.last_prices[symbol] * (1 + price_change)
        new_price = max(base_price * 0.8, min(base_price * 1.3, new_price))  # Limitar rango
        
        self.last_prices[symbol] = new_price
        
        # Calcular cambio 24h simulado
        change_24h = ((new_price - base_price) / base_price) * 100
        
        return {
            'symbol': symbol,
            'price': new_price,
            'priceChange': new_price - base_price,
            'priceChangePercent': change_24h,
            'highPrice': new_price * random.uniform(1.01, 1.05),
            'lowPrice': new_price * random.uniform(0.95, 0.99),
            'volume': random.uniform(1000000, 10000000),
            'count': random.randint(50000, 200000)
        }
    
    def get_real_data(self, symbol: str) -> Optional[dict]:
        """Intenta obtener datos reales de Binance API"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode())
                
                return {
                    'symbol': data['symbol'],
                    'price': float(data['lastPrice']),
                    'priceChange': float(data['priceChange']),
                    'priceChangePercent': float(data['priceChangePercent']),
                    'highPrice': float(data['highPrice']),
                    'lowPrice': float(data['lowPrice']),
                    'volume': float(data['volume']),
                    'count': int(data['count'])
                }
                
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError) as e:
            print(f"Error obteniendo datos reales para {symbol}: {e}")
            return None
    
    def get_market_data(self, symbol: str) -> dict:
        """Obtiene datos de mercado (real o simulado)"""
        if not SIMULATED_MODE:
            real_data = self.get_real_data(symbol)
            if real_data:
                return real_data
        
        # Fallback a datos simulados
        return self.get_simulated_data(symbol)

class PaperTradingEngine:
    """Motor principal de paper trading"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.market_data: Dict[str, MarketData] = {}
        self.balance_usdt = len(SYMBOLS) * CAPITAL_INICIAL
        self.initial_balance = self.balance_usdt
        self.data_provider = MarketDataProvider()
        
        # Inicializar posiciones
        for symbol in SYMBOLS:
            self.positions[symbol] = Position(symbol=symbol)
            self.market_data[symbol] = MarketData(symbol=symbol)
    
    def update_market_data(self):
        """Actualiza datos de mercado para todos los símbolos"""
        for symbol in SYMBOLS:
            try:
                data = self.data_provider.get_market_data(symbol)
                
                md = self.market_data[symbol]
                md.price = data['price']
                md.volume_24h = data['volume']
                md.price_change_24h = data['priceChange']
                md.price_change_percent_24h = data['priceChangePercent']
                md.high_24h = data['highPrice']
                md.low_24h = data['lowPrice']
                md.last_update = datetime.now()
                
            except Exception as e:
                print(f"Error actualizando datos para {symbol}: {e}")
    
    def execute_trade(self, symbol: str, side: str, quantity: float, price: float) -> bool:
        """Ejecuta un trade simulado"""
        try:
            position = self.positions[symbol]
            trade_value = quantity * price
            
            if side == 'BUY':
                if trade_value > self.balance_usdt:
                    return False  # Fondos insuficientes
                
                # Actualizar posición
                total_quantity = position.quantity + quantity
                if total_quantity > 0:
                    position.avg_price = ((position.quantity * position.avg_price) + 
                                        (quantity * price)) / total_quantity
                position.quantity = total_quantity
                self.balance_usdt -= trade_value
                
            elif side == 'SELL':
                if quantity > position.quantity:
                    return False  # Cantidad insuficiente
                
                # Calcular PnL realizado
                realized_pnl = quantity * (price - position.avg_price)
                position.realized_pnl += realized_pnl
                position.quantity -= quantity
                self.balance_usdt += trade_value
                
                if position.quantity == 0:
                    position.avg_price = 0.0
            
            # Registrar trade
            trade = Trade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                timestamp=datetime.now(),
                trade_id=f"{symbol}_{int(time.time())}_{len(self.trades)}"
            )
            self.trades.append(trade)
            
            return True
            
        except Exception as e:
            print(f"Error ejecutando trade: {e}")
            return False
    
    def update_unrealized_pnl(self):
        """Actualiza PnL no realizado"""
        for symbol, position in self.positions.items():
            if position.quantity > 0 and symbol in self.market_data:
                current_price = self.market_data[symbol].price
                if current_price > 0:
                    position.unrealized_pnl = position.quantity * (current_price - position.avg_price)
    
    def get_total_portfolio_value(self) -> float:
        """Calcula el valor total del portafolio"""
        total_value = self.balance_usdt
        
        for symbol, position in self.positions.items():
            if position.quantity > 0 and symbol in self.market_data:
                current_price = self.market_data[symbol].price
                if current_price > 0:
                    total_value += position.quantity * current_price
        
        return total_value
    
    def get_performance_metrics(self) -> dict:
        """Calcula métricas de rendimiento"""
        total_value = self.get_total_portfolio_value()
        total_pnl = sum(pos.realized_pnl + pos.unrealized_pnl for pos in self.positions.values())
        
        return {
            'total_value': total_value,
            'initial_balance': self.initial_balance,
            'total_pnl': total_pnl,
            'total_return_pct': ((total_value - self.initial_balance) / self.initial_balance) * 100,
            'total_trades': len(self.trades),
            'balance_usdt': self.balance_usdt
        }

class SimpleStrategy:
    """Estrategia simple de trading basada en momentum"""
    
    def __init__(self, engine: PaperTradingEngine):
        self.engine = engine
        self.last_signals = {}
        self.price_history = defaultdict(list)
        
    def analyze_and_trade(self, symbol: str):
        """Analiza el mercado y ejecuta trades si es necesario"""
        if symbol not in self.engine.market_data:
            return
            
        market_data = self.engine.market_data[symbol]
        current_price = market_data.price
        
        if current_price <= 0:
            return
            
        # Mantener historial de precios (últimos 10 puntos)
        self.price_history[symbol].append(current_price)
        if len(self.price_history[symbol]) > 10:
            self.price_history[symbol].pop(0)
            
        if len(self.price_history[symbol]) < 5:
            return  # Necesitamos más datos
            
        # Estrategia simple: momentum y cambio porcentual
        prices = self.price_history[symbol]
        short_avg = sum(prices[-3:]) / 3  # Promedio de últimos 3 puntos
        long_avg = sum(prices[-5:]) / 5   # Promedio de últimos 5 puntos
        
        position = self.engine.positions[symbol]
        price_change_pct = market_data.price_change_percent_24h
        
        # Señal de compra: tendencia alcista y cambio positivo
        if (current_price > short_avg > long_avg and 
            price_change_pct > 1.0 and 
            position.quantity == 0):
            
            # Comprar con 1/3 del capital disponible para este símbolo
            trade_amount = CAPITAL_INICIAL / 3
            quantity = trade_amount / current_price
            
            if self.engine.execute_trade(symbol, 'BUY', quantity, current_price):
                self.last_signals[symbol] = 'BUY'
                
        # Señal de venta: tendencia bajista o stop loss
        elif position.quantity > 0:
            # Stop loss: -3% o tendencia bajista fuerte
            unrealized_pnl_pct = (position.unrealized_pnl / (position.quantity * position.avg_price)) * 100
            
            if (unrealized_pnl_pct < -3.0 or  # Stop loss
                (current_price < short_avg < long_avg and price_change_pct < -1.0)):  # Tendencia bajista
                
                # Vender toda la posición
                if self.engine.execute_trade(symbol, 'SELL', position.quantity, current_price):
                    self.last_signals[symbol] = 'SELL'

class ConsoleDisplay:
    """Maneja la visualización en consola"""
    
    def __init__(self, engine: PaperTradingEngine):
        self.engine = engine
        
    def clear_screen(self):
        """Limpia la pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def format_number(self, num: float, decimals: int = 2) -> str:
        """Formatea números para visualización"""
        if abs(num) >= 1000000:
            return f"{num/1000000:.{decimals}f}M"
        elif abs(num) >= 1000:
            return f"{num/1000:.{decimals}f}K"
        else:
            return f"{num:.{decimals}f}"
    
    def display_header(self):
        """Muestra el encabezado"""
        mode_text = "SIMULADO" if SIMULATED_MODE else "DATOS REALES"
        print("\n" + "="*80)
        print(f"🚀 PAPER TRADING EN TIEMPO REAL - BINANCE ({mode_text})")
        print(f"Actualización automática cada {REFRESH_INTERVAL} segundos")
        print(f"Hora actual: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
    
    def display_market_data(self):
        """Muestra datos de mercado"""
        print("\n📊 DATOS DE MERCADO EN TIEMPO REAL")
        print("-"*80)
        print(f"{'Símbolo':<10} {'Precio':<12} {'24h %':<10} {'Volumen 24h':<15} {'Última Act.':<20}")
        print("-"*80)
        
        for symbol in SYMBOLS:
            if symbol in self.engine.market_data:
                md = self.engine.market_data[symbol]
                price_str = f"${self.format_number(md.price, 4)}"
                change_str = f"{md.price_change_percent_24h:+.2f}%"
                volume_str = self.format_number(md.volume_24h)
                time_str = md.last_update.strftime("%H:%M:%S")
                
                # Indicador de cambio de precio
                change_indicator = "↗" if md.price_change_percent_24h >= 0 else "↘"
                
                print(f"{symbol:<10} {price_str:<12} {change_indicator}{change_str:<9} {volume_str:<15} {time_str:<20}")
    
    def display_positions(self):
        """Muestra posiciones actuales"""
        print("\n💼 POSICIONES ACTUALES")
        print("-"*80)
        print(f"{'Símbolo':<10} {'Cantidad':<12} {'Precio Prom':<12} {'PnL Real':<12} {'PnL No Real':<12}")
        print("-"*80)
        
        for symbol in SYMBOLS:
            if symbol in self.engine.positions:
                pos = self.engine.positions[symbol]
                if pos.quantity > 0:
                    qty_str = self.format_number(pos.quantity, 6)
                    price_str = f"${self.format_number(pos.avg_price, 4)}"
                    real_pnl_str = f"${pos.realized_pnl:+.2f}"
                    unreal_pnl_str = f"${pos.unrealized_pnl:+.2f}"
                    
                    print(f"{symbol:<10} {qty_str:<12} {price_str:<12} {real_pnl_str:<12} {unreal_pnl_str:<12}")
                else:
                    print(f"{symbol:<10} {'0':<12} {'$0.00':<12} {f'${pos.realized_pnl:+.2f}':<12} {'$0.00':<12}")
    
    def display_recent_trades(self):
        """Muestra trades recientes"""
        print("\n📈 TRADES RECIENTES (Últimos 8)")
        print("-"*80)
        print(f"{'Hora':<10} {'Símbolo':<10} {'Lado':<6} {'Cantidad':<12} {'Precio':<12}")
        print("-"*80)
        
        recent_trades = self.engine.trades[-8:] if self.engine.trades else []
        
        if not recent_trades:
            print("No hay trades ejecutados aún")
        else:
            for trade in reversed(recent_trades):
                time_str = trade.timestamp.strftime("%H:%M:%S")
                qty_str = self.format_number(trade.quantity, 6)
                price_str = f"${self.format_number(trade.price, 4)}"
                side_indicator = "↗" if trade.side == 'BUY' else "↘"
                
                print(f"{time_str:<10} {trade.symbol:<10} {side_indicator}{trade.side:<5} {qty_str:<12} {price_str:<12}")
    
    def display_performance(self):
        """Muestra métricas de rendimiento"""
        metrics = self.engine.get_performance_metrics()
        
        print("\n📊 RENDIMIENTO DEL PORTAFOLIO")
        print("-"*80)
        
        print(f"💰 Valor Total del Portafolio: ${self.format_number(metrics['total_value'])}")
        print(f"💵 Balance en USDT: ${self.format_number(metrics['balance_usdt'])}")
        print(f"📈 PnL Total: ${metrics['total_pnl']:+.2f}")
        print(f"📊 Retorno Total: {metrics['total_return_pct']:+.2f}%")
        print(f"🔄 Total de Trades: {metrics['total_trades']}")
    
    def display_all(self):
        """Muestra toda la información"""
        self.clear_screen()
        self.display_header()
        self.display_market_data()
        self.display_positions()
        self.display_recent_trades()
        self.display_performance()
        
        print("\n" + "="*80)
        print("Presiona Ctrl+C para detener el sistema")
        print("="*80)

def main():
    """Función principal"""
    print("🚀 Iniciando Paper Trading en Tiempo Real...")
    
    # Inicializar componentes
    engine = PaperTradingEngine()
    strategy = SimpleStrategy(engine)
    display = ConsoleDisplay(engine)
    
    try:
        print("✅ Sistema iniciado correctamente")
        print(f"Modo: {'Simulado' if SIMULATED_MODE else 'Datos Reales'}")
        time.sleep(2)
        
        # Loop principal
        iteration = 0
        while True:
            iteration += 1
            
            # Actualizar datos de mercado
            engine.update_market_data()
            
            # Actualizar PnL no realizado
            engine.update_unrealized_pnl()
            
            # Ejecutar estrategia para cada símbolo (cada 3 iteraciones)
            if iteration % 3 == 0:
                for symbol in SYMBOLS:
                    strategy.analyze_and_trade(symbol)
            
            # Mostrar información
            display.display_all()
            
            # Esperar antes de la siguiente actualización
            time.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo sistema...")
    except Exception as e:
        print(f"\n❌ Error en el sistema: {e}")
    finally:
        # Mostrar resumen final
        print("\n" + "="*50)
        print("📊 RESUMEN FINAL")
        print("="*50)
        metrics = engine.get_performance_metrics()
        print(f"Valor Final del Portafolio: ${metrics['total_value']:.2f}")
        print(f"Retorno Total: {metrics['total_return_pct']:+.2f}%")
        print(f"Total de Trades: {metrics['total_trades']}")
        print("¡Gracias por usar el sistema!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Sistema detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")