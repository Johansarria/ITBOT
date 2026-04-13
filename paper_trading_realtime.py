#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Paper Trading en Tiempo Real con Binance
Actualización cada 30 segundos con visualización en consola
"""

import asyncio
import websockets
import json
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import sys

# Configuración de símbolos a monitorear
SYMBOLS = ['SOLUSDT', 'BNBUSDT', 'ADAUSDT']
CAPITAL_INICIAL = 500.0  # USDT por símbolo
REFRESH_INTERVAL = 30  # segundos

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

class PaperTradingEngine:
    """Motor principal de paper trading"""
    
    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.market_data: Dict[str, MarketData] = {}
        self.balance_usdt = len(SYMBOLS) * CAPITAL_INICIAL
        self.initial_balance = self.balance_usdt
        self.running = False
        
        # Inicializar posiciones
        for symbol in SYMBOLS:
            self.positions[symbol] = Position(symbol=symbol)
            self.market_data[symbol] = MarketData(symbol=symbol)
    
    def update_market_data(self, symbol: str, data: dict):
        """Actualiza datos de mercado"""
        if symbol in self.market_data:
            md = self.market_data[symbol]
            md.price = float(data.get('c', md.price))  # close price
            md.volume_24h = float(data.get('v', md.volume_24h))  # volume
            md.price_change_24h = float(data.get('P', md.price_change_24h))  # price change %
            md.high_24h = float(data.get('h', md.high_24h))  # high
            md.low_24h = float(data.get('l', md.low_24h))  # low
            md.last_update = datetime.now()
    
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
            
        # Estrategia simple: momentum
        prices = self.price_history[symbol]
        short_avg = sum(prices[-3:]) / 3  # Promedio de últimos 3 puntos
        long_avg = sum(prices[-5:]) / 5   # Promedio de últimos 5 puntos
        
        position = self.engine.positions[symbol]
        
        # Señal de compra: precio actual > promedio corto > promedio largo
        if current_price > short_avg > long_avg and position.quantity == 0:
            # Comprar con 1/3 del capital disponible para este símbolo
            trade_amount = CAPITAL_INICIAL / 3
            quantity = trade_amount / current_price
            
            if self.engine.execute_trade(symbol, 'BUY', quantity, current_price):
                self.last_signals[symbol] = 'BUY'
                
        # Señal de venta: precio actual < promedio corto < promedio largo
        elif current_price < short_avg < long_avg and position.quantity > 0:
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
    
    def display_market_data(self):
        """Muestra datos de mercado"""
        print("\n" + "="*80)
        print("📊 DATOS DE MERCADO EN TIEMPO REAL")
        print("="*80)
        print(f"{'Símbolo':<10} {'Precio':<12} {'24h %':<10} {'Volumen 24h':<15} {'Última Act.':<20}")
        print("-"*80)
        
        for symbol in SYMBOLS:
            if symbol in self.engine.market_data:
                md = self.engine.market_data[symbol]
                price_str = f"${self.format_number(md.price, 4)}"
                change_str = f"{md.price_change_24h:+.2f}%"
                volume_str = self.format_number(md.volume_24h)
                time_str = md.last_update.strftime("%H:%M:%S")
                
                # Color para cambio de precio
                change_color = "🟢" if md.price_change_24h >= 0 else "🔴"
                
                print(f"{symbol:<10} {price_str:<12} {change_color}{change_str:<9} {volume_str:<15} {time_str:<20}")
    
    def display_positions(self):
        """Muestra posiciones actuales"""
        print("\n" + "="*80)
        print("💼 POSICIONES ACTUALES")
        print("="*80)
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
        print("\n" + "="*80)
        print("📈 TRADES RECIENTES (Últimos 10)")
        print("="*80)
        print(f"{'Hora':<10} {'Símbolo':<10} {'Lado':<6} {'Cantidad':<12} {'Precio':<12}")
        print("-"*80)
        
        recent_trades = self.engine.trades[-10:] if self.engine.trades else []
        
        for trade in reversed(recent_trades):
            time_str = trade.timestamp.strftime("%H:%M:%S")
            qty_str = self.format_number(trade.quantity, 6)
            price_str = f"${self.format_number(trade.price, 4)}"
            side_emoji = "🟢" if trade.side == 'BUY' else "🔴"
            
            print(f"{time_str:<10} {trade.symbol:<10} {side_emoji}{trade.side:<5} {qty_str:<12} {price_str:<12}")
    
    def display_performance(self):
        """Muestra métricas de rendimiento"""
        metrics = self.engine.get_performance_metrics()
        
        print("\n" + "="*80)
        print("📊 RENDIMIENTO DEL PORTAFOLIO")
        print("="*80)
        
        print(f"💰 Valor Total del Portafolio: ${self.format_number(metrics['total_value'])}")
        print(f"💵 Balance en USDT: ${self.format_number(metrics['balance_usdt'])}")
        print(f"📈 PnL Total: ${metrics['total_pnl']:+.2f}")
        print(f"📊 Retorno Total: {metrics['total_return_pct']:+.2f}%")
        print(f"🔄 Total de Trades: {metrics['total_trades']}")
        print(f"⏰ Última Actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def display_all(self):
        """Muestra toda la información"""
        self.clear_screen()
        print("🚀 PAPER TRADING EN TIEMPO REAL - BINANCE")
        print(f"Actualización automática cada {REFRESH_INTERVAL} segundos")
        
        self.display_market_data()
        self.display_positions()
        self.display_recent_trades()
        self.display_performance()
        
        print("\n" + "="*80)
        print("Presiona Ctrl+C para detener el sistema")
        print("="*80)

class BinanceWebSocketClient:
    """Cliente WebSocket para Binance"""
    
    def __init__(self, engine: PaperTradingEngine):
        self.engine = engine
        self.running = False
        
    async def connect_and_listen(self):
        """Conecta y escucha datos de WebSocket"""
        # Crear streams para todos los símbolos
        streams = [f"{symbol.lower()}@ticker" for symbol in SYMBOLS]
        stream_names = '/'.join(streams)
        
        uri = f"wss://stream.binance.com:9443/ws/{stream_names}"
        
        try:
            print(f"Conectando a Binance WebSocket...")
            async with websockets.connect(uri) as websocket:
                print("✅ Conectado a Binance WebSocket")
                self.running = True
                
                async for message in websocket:
                    if not self.running:
                        break
                        
                    try:
                        data = json.loads(message)
                        
                        if 'stream' in data and 'data' in data:
                            stream = data['stream']
                            ticker_data = data['data']
                            
                            # Extraer símbolo del stream
                            symbol = ticker_data.get('s', '').upper()
                            
                            if symbol in SYMBOLS:
                                self.engine.update_market_data(symbol, ticker_data)
                                
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Error procesando mensaje: {e}")
                        
        except Exception as e:
            print(f"Error en WebSocket: {e}")
            self.running = False
    
    def stop(self):
        """Detiene el cliente WebSocket"""
        self.running = False

async def main():
    """Función principal"""
    print("🚀 Iniciando Paper Trading en Tiempo Real...")
    
    # Inicializar componentes
    engine = PaperTradingEngine()
    strategy = SimpleStrategy(engine)
    display = ConsoleDisplay(engine)
    ws_client = BinanceWebSocketClient(engine)
    
    # Iniciar WebSocket en background
    ws_task = asyncio.create_task(ws_client.connect_and_listen())
    
    try:
        # Esperar un poco para que se establezca la conexión
        await asyncio.sleep(3)
        
        # Loop principal
        while True:
            # Actualizar PnL no realizado
            engine.update_unrealized_pnl()
            
            # Ejecutar estrategia para cada símbolo
            for symbol in SYMBOLS:
                strategy.analyze_and_trade(symbol)
            
            # Mostrar información
            display.display_all()
            
            # Esperar antes de la siguiente actualización
            await asyncio.sleep(REFRESH_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo sistema...")
    except Exception as e:
        print(f"\n❌ Error en el sistema: {e}")
    finally:
        ws_client.stop()
        if not ws_task.done():
            ws_task.cancel()
        
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
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Sistema detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")