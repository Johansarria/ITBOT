import asyncio
import websockets
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
import threading
import time
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.enums import *

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('paper_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Trade:
    """Representa un trade ejecutado en el simulador"""
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    timestamp: datetime
    trade_id: str
    pnl: float = 0.0
    status: str = 'OPEN'  # 'OPEN', 'CLOSED'
    
@dataclass
class Position:
    """Representa una posición abierta"""
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
@dataclass
class PortfolioConfig:
    """Configuración del portafolio basada en análisis previo"""
    initial_capital: float = 10000.0
    # Diversificación recomendada del análisis
    allocations: Dict[str, float] = field(default_factory=lambda: {
        'BNBUSDT': 0.15,    # 15% - Mejor performer crypto
        'ADAUSDT': 0.10,    # 10% - Alto retorno crypto
        'SOLUSDT': 0.10,    # 10% - Máximo retorno crypto
        'ETHUSDT': 0.10,    # 10% - Estable crypto
        'BTCUSDT': 0.05,    # 5% - Conservador crypto
        'NAS100': 0.20,     # 20% - Índice principal
        'AUDCAD': 0.15,     # 15% - Forex estable
        'XAUUSD': 0.15      # 15% - Oro como refugio
    })
    max_position_size: float = 0.25  # Máximo 25% en una posición
    stop_loss_pct: float = 0.02      # 2% stop loss
    take_profit_pct: float = 0.04    # 4% take profit

class MarketDataManager:
    """Gestor de datos de mercado en tiempo real"""
    
    def __init__(self):
        self.price_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.current_prices: Dict[str, float] = {}
        self.callbacks: List[Callable] = []
        self.running = False
        
    def add_price_callback(self, callback: Callable):
        """Añade callback para actualizaciones de precio"""
        self.callbacks.append(callback)
        
    def update_price(self, symbol: str, price: float, timestamp: datetime = None):
        """Actualiza precio de un símbolo"""
        if timestamp is None:
            timestamp = datetime.now()
            
        self.current_prices[symbol] = price
        self.price_data[symbol].append({
            'price': price,
            'timestamp': timestamp
        })
        
        # Notificar callbacks
        for callback in self.callbacks:
            try:
                callback(symbol, price, timestamp)
            except Exception as e:
                logger.error(f"Error en callback: {e}")
                
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Obtiene precio actual de un símbolo"""
        return self.current_prices.get(symbol)
        
    def get_price_history(self, symbol: str, periods: int = 20) -> List[float]:
        """Obtiene historial de precios"""
        if symbol not in self.price_data:
            return []
        return [data['price'] for data in list(self.price_data[symbol])[-periods:]]

class PaperTradingSimulator:
    """Simulador principal de paper trading"""
    
    def __init__(self, config: PortfolioConfig = None):
        self.config = config or PortfolioConfig()
        self.market_data = MarketDataManager()
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.balance = self.config.initial_capital
        self.equity = self.config.initial_capital
        self.running = False
        
        # Métricas de performance
        self.total_pnl = 0.0
        self.win_trades = 0
        self.lose_trades = 0
        self.max_drawdown = 0.0
        self.peak_equity = self.config.initial_capital
        
        # Setup callbacks
        self.market_data.add_price_callback(self._on_price_update)
        
        logger.info(f"Paper Trading Simulator inicializado con capital: ${self.config.initial_capital}")
        
    def _on_price_update(self, symbol: str, price: float, timestamp: datetime):
        """Callback para actualizaciones de precio"""
        # Actualizar posiciones abiertas
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = price
            
            # Calcular PnL no realizado
            if position.side == 'BUY':
                position.unrealized_pnl = (price - position.entry_price) * position.quantity
            else:
                position.unrealized_pnl = (position.entry_price - price) * position.quantity
                
        # Actualizar equity total
        self._update_equity()
        
        # Verificar condiciones de stop loss / take profit
        self._check_exit_conditions(symbol, price)
        
    def _update_equity(self):
        """Actualiza el equity total incluyendo PnL no realizado"""
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        self.equity = self.balance + unrealized_pnl
        
        # Actualizar métricas
        if self.equity > self.peak_equity:
            self.peak_equity = self.equity
        
        current_drawdown = (self.peak_equity - self.equity) / self.peak_equity
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
            
    def _check_exit_conditions(self, symbol: str, current_price: float):
        """Verifica condiciones de salida (stop loss / take profit)"""
        if symbol not in self.positions:
            return
            
        position = self.positions[symbol]
        
        # Calcular porcentaje de cambio
        if position.side == 'BUY':
            pct_change = (current_price - position.entry_price) / position.entry_price
        else:
            pct_change = (position.entry_price - current_price) / position.entry_price
            
        # Stop Loss
        if pct_change <= -self.config.stop_loss_pct:
            logger.info(f"Stop Loss activado para {symbol} en {current_price}")
            self.close_position(symbol, "STOP_LOSS")
            
        # Take Profit
        elif pct_change >= self.config.take_profit_pct:
            logger.info(f"Take Profit activado para {symbol} en {current_price}")
            self.close_position(symbol, "TAKE_PROFIT")
            
    def open_position(self, symbol: str, side: str, quantity: float, price: float, reason: str = "") -> bool:
        """Abre una nueva posición"""
        try:
            # Verificar si ya existe posición
            if symbol in self.positions:
                logger.warning(f"Ya existe posición abierta para {symbol}")
                return False
                
            # Calcular valor de la posición
            position_value = quantity * price
            
            # Verificar capital disponible
            if position_value > self.balance:
                logger.warning(f"Capital insuficiente para abrir posición {symbol}")
                return False
                
            # Crear posición
            position = Position(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=price,
                current_price=price
            )
            
            # Crear trade
            trade = Trade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                timestamp=datetime.now(),
                trade_id=f"{symbol}_{len(self.trades)+1}"
            )
            
            # Actualizar balance
            self.balance -= position_value
            
            # Guardar posición y trade
            self.positions[symbol] = position
            self.trades.append(trade)
            
            logger.info(f"Posición abierta: {side} {quantity} {symbol} @ {price} - Razón: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error abriendo posición: {e}")
            return False
            
    def close_position(self, symbol: str, reason: str = "") -> bool:
        """Cierra una posición existente"""
        try:
            if symbol not in self.positions:
                logger.warning(f"No existe posición para {symbol}")
                return False
                
            position = self.positions[symbol]
            current_price = self.market_data.get_current_price(symbol)
            
            if current_price is None:
                logger.error(f"No se puede obtener precio actual para {symbol}")
                return False
                
            # Calcular PnL realizado
            if position.side == 'BUY':
                pnl = (current_price - position.entry_price) * position.quantity
                exit_side = 'SELL'
            else:
                pnl = (position.entry_price - current_price) * position.quantity
                exit_side = 'BUY'
                
            # Actualizar balance
            position_value = position.quantity * current_price
            self.balance += position_value
            self.total_pnl += pnl
            
            # Actualizar estadísticas
            if pnl > 0:
                self.win_trades += 1
            else:
                self.lose_trades += 1
                
            # Crear trade de cierre
            close_trade = Trade(
                symbol=symbol,
                side=exit_side,
                quantity=position.quantity,
                price=current_price,
                timestamp=datetime.now(),
                trade_id=f"{symbol}_close_{len(self.trades)+1}",
                pnl=pnl,
                status='CLOSED'
            )
            
            self.trades.append(close_trade)
            
            # Eliminar posición
            del self.positions[symbol]
            
            logger.info(f"Posición cerrada: {symbol} @ {current_price} - PnL: ${pnl:.2f} - Razón: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}")
            return False
            
    def get_portfolio_summary(self) -> Dict:
        """Obtiene resumen del portafolio"""
        total_trades = len(self.trades)
        win_rate = (self.win_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'balance': self.balance,
            'equity': self.equity,
            'total_pnl': self.total_pnl,
            'unrealized_pnl': sum(pos.unrealized_pnl for pos in self.positions.values()),
            'open_positions': len(self.positions),
            'total_trades': total_trades,
            'win_trades': self.win_trades,
            'lose_trades': self.lose_trades,
            'win_rate': win_rate,
            'max_drawdown': self.max_drawdown * 100,
            'return_pct': ((self.equity - self.config.initial_capital) / self.config.initial_capital) * 100
        }
        
    def start_simulation(self):
        """Inicia la simulación"""
        self.running = True
        logger.info("Simulación de Paper Trading iniciada")
        
    def stop_simulation(self):
        """Detiene la simulación"""
        self.running = False
        
        # Cerrar todas las posiciones abiertas
        for symbol in list(self.positions.keys()):
            self.close_position(symbol, "SIMULATION_STOP")
            
        logger.info("Simulación de Paper Trading detenida")
        
if __name__ == "__main__":
    # Ejemplo de uso básico
    simulator = PaperTradingSimulator()
    
    # Simular algunos precios
    simulator.market_data.update_price('BNBUSDT', 300.0)
    simulator.market_data.update_price('ETHUSDT', 2500.0)
    
    # Abrir posiciones de prueba
    simulator.open_position('BNBUSDT', 'BUY', 10, 300.0, "TEST")
    simulator.open_position('ETHUSDT', 'BUY', 2, 2500.0, "TEST")
    
    # Simular cambio de precios
    simulator.market_data.update_price('BNBUSDT', 310.0)  # +3.33%
    simulator.market_data.update_price('ETHUSDT', 2450.0)  # -2%
    
    # Mostrar resumen
    summary = simulator.get_portfolio_summary()
    print("\n=== RESUMEN DEL PORTAFOLIO ===")
    for key, value in summary.items():
        print(f"{key}: {value}")