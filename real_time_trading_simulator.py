#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador de Trading en Tiempo Real con Datos de Binance
Simulación completa con capital inicial de 500 USDT, gestión de riesgo,
métricas de rendimiento y visualización en tiempo real.
"""

import os
import json
import time
import asyncio
import websockets
import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend sin ventanas
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
import signal
import sys
from dataclasses import dataclass, asdict
from collections import deque
import warnings
warnings.filterwarnings('ignore')

# Configurar matplotlib para modo no interactivo sin ventanas
plt.ioff()

@dataclass
class Trade:
    """Estructura de datos para un trade"""
    timestamp: str
    symbol: str
    side: str  # 'BUY' o 'SELL'
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    commission: float
    duration_seconds: int
    strategy_signal: str
    is_winner: bool

@dataclass
class MarketData:
    """Estructura de datos del mercado"""
    timestamp: str
    symbol: str
    price: float
    volume: float
    bid: float
    ask: float
    spread: float
    spread_pct: float

class TechnicalIndicators:
    """Calculadora de indicadores técnicos"""
    
    @staticmethod
    def sma(prices: List[float], period: int) -> float:
        """Media móvil simple"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
    @staticmethod
    def ema(prices: List[float], period: int) -> float:
        """Media móvil exponencial"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema_value = prices[0]
        
        for price in prices[1:]:
            ema_value = (price * multiplier) + (ema_value * (1 - multiplier))
        
        return ema_value
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        """Índice de Fuerza Relativa"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[float, float, float]:
        """Bandas de Bollinger (upper, middle, lower)"""
        if len(prices) < period:
            price = prices[-1] if prices else 0
            return price, price, price
        
        sma = sum(prices[-period:]) / period
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = variance ** 0.5
        
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        
        return upper, sma, lower

class RiskManager:
    """Gestor de riesgo avanzado con spreads, comisiones y slippage realistas"""
    
    def __init__(self, initial_capital: float, config: Dict = None):
        self.initial_capital = initial_capital
        self.config = config or {}
        
        # Parámetros de riesgo configurables
        self.max_risk_per_trade = self.config.get('max_risk_per_trade', 0.02)  # 2% máximo por trade
        self.max_daily_loss = self.config.get('max_daily_loss', 0.05)  # 5% pérdida máxima diaria
        self.max_drawdown = self.config.get('max_drawdown', 0.10)  # 10% drawdown máximo
        self.max_open_positions = self.config.get('max_open_positions', 3)
        self.max_position_size_pct = self.config.get('max_position_size_pct', 0.1)  # 10% del capital por posición
        
        # Costos de trading realistas
        self.maker_fee = self.config.get('maker_fee', 0.001)      # 0.1% comisión maker
        self.taker_fee = self.config.get('taker_fee', 0.001)      # 0.1% comisión taker
        self.spread_pct = self.config.get('spread_pct', 0.0005)   # 0.05% spread promedio
        self.slippage_pct = self.config.get('slippage_pct', 0.0002)  # 0.02% slippage promedio
        
        # Límites de volatilidad y volumen
        self.max_volatility = self.config.get('max_volatility', 0.05)  # 5% volatilidad máxima
        self.min_volume_threshold = self.config.get('min_volume_threshold', 100000)  # Volumen mínimo
        
        # Control de frecuencia de trading
        self.min_time_between_trades = self.config.get('min_time_between_trades', 60)  # 60 segundos
        self.last_trade_time = {}
        
    def calculate_position_size(self, capital: float, entry_price: float, stop_loss: float) -> float:
        """Calcula el tamaño de posición basado en el riesgo y stop loss"""
        risk_amount = capital * self.max_risk_per_trade
        price_risk = abs(entry_price - stop_loss)
        
        if price_risk == 0:
            return 0
        
        # Tamaño de posición basado en stop loss
        position_size = risk_amount / price_risk
        
        # Limitar al máximo permitido
        max_position_value = capital * self.max_position_size_pct
        max_quantity = max_position_value / entry_price
        
        return min(position_size, max_quantity)
    
    def calculate_trading_costs(self, quantity: float, price: float, side: str, 
                               is_market_order: bool = True) -> Dict[str, float]:
        """Calcula todos los costos de trading incluyendo comisiones, spread y slippage"""
        notional_value = quantity * price
        
        # Comisión
        fee_rate = self.taker_fee if is_market_order else self.maker_fee
        commission = notional_value * fee_rate
        
        # Spread (solo para compras)
        spread_cost = 0
        if side == 'BUY':
            spread_cost = notional_value * self.spread_pct
        
        # Slippage
        slippage_cost = notional_value * self.slippage_pct
        
        total_cost = commission + spread_cost + slippage_cost
        
        return {
            'commission': commission,
            'spread': spread_cost,
            'slippage': slippage_cost,
            'total_cost': total_cost,
            'cost_pct': (total_cost / notional_value) * 100
        }
    
    def calculate_commission(self, quantity: float, price: float) -> float:
        """Calcula la comisión del trade (método legacy)"""
        return quantity * price * self.taker_fee
    
    def calculate_spread_cost(self, quantity: float, price: float) -> float:
        """Calcula el costo del spread (método legacy)"""
        return quantity * price * self.spread_pct
    
    def apply_slippage(self, price: float, side: str, market_volatility: float = 0.001) -> float:
        """Aplica slippage realista al precio"""
        # Slippage aumenta con volatilidad
        dynamic_slippage = self.slippage_pct * (1 + market_volatility * 10)
        
        if side == 'BUY':
            # Compra: precio más alto
            return price * (1 + dynamic_slippage)
        else:
            # Venta: precio más bajo
            return price * (1 - dynamic_slippage)
    
    def can_open_position(self, current_capital: float, daily_pnl: float, open_positions: int, 
                         symbol: str = None, market_data: Dict = None) -> Tuple[bool, str]:
        """Verifica si se puede abrir una nueva posición con validaciones avanzadas"""
        
        # Verificar pérdida diaria
        if daily_pnl < -self.initial_capital * self.max_daily_loss:
            return False, f"Límite de pérdida diaria alcanzado ({daily_pnl:.2f})"
        
        # Verificar drawdown
        drawdown = (self.initial_capital - current_capital) / self.initial_capital
        if drawdown > self.max_drawdown:
            return False, f"Límite de drawdown alcanzado ({drawdown:.2%})"
        
        # Verificar posiciones abiertas
        if open_positions >= self.max_open_positions:
            return False, f"Máximo de posiciones abiertas alcanzado ({open_positions}/{self.max_open_positions})"
        
        # Verificar tiempo entre trades si se proporciona símbolo
        if symbol and symbol in self.last_trade_time:
            time_diff = (datetime.now() - self.last_trade_time[symbol]).total_seconds()
            if time_diff < self.min_time_between_trades:
                return False, f"Tiempo insuficiente entre trades ({time_diff:.0f}s < {self.min_time_between_trades}s)"
        
        # Verificar volumen mínimo si se proporcionan datos de mercado
        if market_data and 'volume' in market_data:
            volume = market_data['volume']
            if volume < self.min_volume_threshold:
                return False, f"Volumen insuficiente ({volume:,.0f} < {self.min_volume_threshold:,.0f})"
        
        return True, "Posición aprobada"
    
    def update_last_trade_time(self, symbol: str):
        """Actualiza el tiempo del último trade para un símbolo"""
        self.last_trade_time[symbol] = datetime.now()
    
    def get_risk_metrics(self, current_capital: float, daily_pnl: float, peak_capital: float = None) -> Dict:
        """Obtiene métricas de riesgo actuales"""
        if peak_capital is None:
            peak_capital = max(self.initial_capital, current_capital)
            
        drawdown = (peak_capital - current_capital) / peak_capital if peak_capital > 0 else 0
        daily_loss_pct = (daily_pnl / current_capital) * 100 if current_capital > 0 else 0
        
        return {
            'current_drawdown_pct': drawdown * 100,
            'max_drawdown_limit_pct': self.max_drawdown * 100,
            'daily_pnl_pct': daily_loss_pct,
            'daily_loss_limit_pct': self.max_daily_loss * 100,
            'risk_utilization_pct': (drawdown / self.max_drawdown) * 100 if self.max_drawdown > 0 else 0,
            'position_size_limit_pct': self.max_position_size_pct * 100,
            'max_open_positions': self.max_open_positions
        }

class TradingStrategy:
    """Estrategia de trading configurable"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.indicators = TechnicalIndicators()
        self.price_history = deque(maxlen=100)
        self.volume_history = deque(maxlen=50)
        self.last_signal = None
        self.signal_history = []
        
        # Parámetros configurables
        self.sma_short = self.config.get('sma_fast', 10)
        self.sma_long = self.config.get('sma_slow', 20)
        self.rsi_period = self.config.get('rsi_period', 14)
        self.rsi_oversold = self.config.get('rsi_oversold', 30)
        self.rsi_overbought = self.config.get('rsi_overbought', 70)
        self.bb_period = self.config.get('bb_period', 20)
        self.bb_std = self.config.get('bb_std', 2)
        self.min_confidence = self.config.get('min_signal_confidence', 0.6)
        self.volume_threshold = self.config.get('volume_threshold', 1.5)
        
    def update_data(self, price: float, volume: float):
        """Actualiza los datos de precio y volumen"""
        self.price_history.append(price)
        self.volume_history.append(volume)
    
    def generate_signal(self) -> str:
        """Genera señal de trading basada en múltiples indicadores"""
        try:
            if len(self.price_history) < self.sma_long:
                return 'HOLD'
            
            prices = list(self.price_history)
            volumes = list(self.volume_history)
            current_price = prices[-1]
            
            # Medias móviles
            sma_short = self.indicators.sma(prices, self.sma_short)
            sma_long = self.indicators.sma(prices, self.sma_long)
            
            # RSI
            rsi = self.indicators.rsi(prices, self.rsi_period)
            
            # Bandas de Bollinger
            bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(prices, self.bb_period, self.bb_std)
            
            # Calcular fuerza de señal
            signal_strength = 0
            reasons = []
            
            # Señal de medias móviles
            if sma_short > sma_long:
                signal_strength += 0.4
                reasons.append('SMA alcista')
            elif sma_short < sma_long:
                signal_strength -= 0.4
                reasons.append('SMA bajista')
            
            # Señal de RSI
            if rsi < self.rsi_oversold:
                signal_strength += 0.3
                reasons.append(f'RSI sobreventa ({rsi:.1f})')
            elif rsi > self.rsi_overbought:
                signal_strength -= 0.3
                reasons.append(f'RSI sobrecompra ({rsi:.1f})')
            
            # Señal de Bandas de Bollinger
            if current_price < bb_lower:
                signal_strength += 0.2
                reasons.append('Precio bajo BB inferior')
            elif current_price > bb_upper:
                signal_strength -= 0.2
                reasons.append('Precio sobre BB superior')
            
            # Señal basada en volumen
            if len(volumes) >= 2:
                volume_ratio = volumes[-1] / volumes[-2] if volumes[-2] > 0 else 1
                if volume_ratio > self.volume_threshold:
                    signal_strength += 0.1 if signal_strength > 0 else -0.1
                    reasons.append(f'Alto volumen ({volume_ratio:.1f}x)')
            
            # Crear señal detallada
            signal_data = {
                'action': 'HOLD',
                'confidence': abs(signal_strength),
                'strength': signal_strength,
                'reasons': reasons,
                'indicators': {
                    'sma_fast': sma_short,
                    'sma_slow': sma_long,
                    'rsi': rsi,
                    'bb_upper': bb_upper,
                    'bb_middle': bb_middle,
                    'bb_lower': bb_lower
                },
                'timestamp': datetime.now()
            }
            
            # Determinar acción final
            if signal_strength > self.min_confidence:
                signal_data['action'] = 'BUY'
            elif signal_strength < -self.min_confidence:
                signal_data['action'] = 'SELL'
            
            self.last_signal = signal_data
            self.signal_history.append(signal_data)
            
            # Mantener solo las últimas 100 señales
            if len(self.signal_history) > 100:
                self.signal_history = self.signal_history[-100:]
            
            return signal_data['action']
            
        except Exception as e:
            print(f"❌ Error generando señal: {e}")
            return 'HOLD'

class PerformanceMetrics:
    """Calculadora de métricas de rendimiento"""
    
    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        
    def add_trade(self, trade: Trade):
        """Añade un trade al historial"""
        self.trades.append(trade)
    
    def update_equity(self, current_capital: float):
        """Actualiza la curva de equity"""
        self.equity_curve.append({
            'timestamp': datetime.now().isoformat(),
            'equity': current_capital,
            'return_pct': ((current_capital - self.initial_capital) / self.initial_capital) * 100
        })
    
    def calculate_metrics(self) -> Dict:
        """Calcula métricas de rendimiento completas"""
        if not self.trades:
            return {}
        
        # Métricas básicas
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.is_winner)
        losing_trades = total_trades - winning_trades
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        # P&L
        total_pnl = sum(t.pnl for t in self.trades)
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = sum(t.pnl for t in self.trades if t.pnl < 0)
        
        # Profit Factor
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')
        
        # Average trades
        avg_win = gross_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = gross_loss / losing_trades if losing_trades > 0 else 0
        
        # Drawdown
        peak = self.initial_capital
        max_drawdown = 0
        current_equity = self.initial_capital + total_pnl
        
        for equity_point in self.equity_curve:
            equity = equity_point['equity']
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Sharpe Ratio (simplificado)
        sharpe_ratio = 0
        if len(self.equity_curve) > 1:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_equity = self.equity_curve[i-1]['equity']
                curr_equity = self.equity_curve[i]['equity']
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(daily_return)
            
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'max_drawdown': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio,
            'current_equity': current_equity,
            'total_return_pct': ((current_equity - self.initial_capital) / self.initial_capital) * 100
        }
    
    def calculate_unrealized_pnl(self, positions: Dict, current_prices: Dict) -> float:
        """Calcula P&L no realizado de posiciones abiertas"""
        unrealized = 0.0
        for symbol, position in positions.items():
            if position.quantity > 0 and symbol in current_prices:
                current_price = current_prices[symbol]
                unrealized += (current_price - position.avg_price) * position.quantity
        return unrealized

class BinanceDataProvider:
    """Proveedor de datos de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.ws_url = "wss://stream.binance.com:9443/ws"
        
    def get_ticker_price(self, symbol: str) -> Optional[Dict]:
        """Obtiene precio actual y datos del ticker"""
        try:
            response = requests.get(
                f"{self.base_url}/ticker/24hr",
                params={'symbol': symbol},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'symbol': data['symbol'],
                    'price': float(data['lastPrice']),
                    'volume': float(data['volume']),
                    'bid': float(data['bidPrice']),
                    'ask': float(data['askPrice']),
                    'spread': float(data['askPrice']) - float(data['bidPrice']),
                    'spread_pct': ((float(data['askPrice']) - float(data['bidPrice'])) / float(data['lastPrice'])) * 100
                }
        except Exception as e:
            print(f"❌ Error obteniendo datos de {symbol}: {e}")
        
        return None
    
    def get_klines(self, symbol: str, interval: str = '1m', limit: int = 100) -> List[Dict]:
        """Obtiene datos de velas"""
        try:
            response = requests.get(
                f"{self.base_url}/klines",
                params={
                    'symbol': symbol,
                    'interval': interval,
                    'limit': limit
                },
                timeout=10
            )
            
            if response.status_code == 200:
                klines = response.json()
                return [{
                    'timestamp': kline[0],
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                } for kline in klines]
        except Exception as e:
            print(f"❌ Error obteniendo klines de {symbol}: {e}")
        
        return []

class RealTimeTradingSimulator:
    """Simulador principal de trading en tiempo real"""
    
    def __init__(self, symbols: List[str], initial_capital: float = 500.0, strategy_config: Dict = None):
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.running = True
        self.start_time = datetime.now()
        
        # Configuración de estrategia
        self.strategy_config = strategy_config or {
            'sma_fast': 10,
            'sma_slow': 20,
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'bb_period': 20,
            'bb_std': 2,
            'min_signal_confidence': 0.6,
            'volume_threshold': 1.5
        }
        
        # Componentes
        self.data_provider = BinanceDataProvider()
        self.risk_manager = RiskManager(initial_capital)
        self.strategy = TradingStrategy(self.strategy_config)
        self.performance = PerformanceMetrics(initial_capital)
        
        # Estado del trading
        self.open_positions = {}
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
        
        # Archivos de log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"real_time_simulation_{timestamp}.jsonl"
        self.report_file = f"simulation_report_{timestamp}.json"
        
        # Configurar señales
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Configurar visualización
        self.setup_visualization()
        
        print(f"\n🚀 Simulador de Trading en Tiempo Real Iniciado")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f} USDT")
        print(f"📊 Símbolos: {', '.join(self.symbols)}")
        print(f"📝 Log: {self.log_file}")
        print(f"📈 Reporte: {self.report_file}")
        print(f"⏰ Inicio: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
    
    def setup_visualization(self):
        """Configura la visualización en tiempo real"""
        plt.style.use('dark_background')
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        self.fig.suptitle('Simulación de Trading en Tiempo Real', fontsize=16, color='white')
        
        # Configurar subplots
        self.ax1.set_title('Curva de Equity', color='white')
        self.ax1.set_ylabel('Capital (USDT)', color='white')
        
        self.ax2.set_title('P&L por Trade', color='white')
        self.ax2.set_ylabel('P&L (USDT)', color='white')
        
        self.ax3.set_title('Distribución de Retornos', color='white')
        self.ax3.set_ylabel('Frecuencia', color='white')
        
        self.ax4.set_title('Métricas en Tiempo Real', color='white')
        self.ax4.axis('off')
        
        plt.tight_layout()
        # plt.show(block=False)  # Deshabilitado para evitar ventanas
    
    def _signal_handler(self, signum, frame):
        """Manejador de señales para cierre limpio"""
        print(f"\n⚠️  Señal {signum} recibida. Cerrando simulación...")
        self.running = False
    
    def log_event(self, event_type: str, data: Dict):
        """Registra eventos en formato JSON Lines"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"❌ Error escribiendo log: {e}")
    
    def reset_daily_metrics(self):
        """Resetea métricas diarias"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
            print(f"📅 Nuevo día: {current_date}. Métricas diarias reseteadas.")
    
    def execute_trade(self, symbol: str, signal: str, market_data: MarketData) -> Optional[Trade]:
        """Ejecuta un trade basado en la señal"""
        if signal == 'HOLD':
            return None
        
        # Verificar si se puede abrir posición
        if not self.risk_manager.can_open_position(
            self.current_capital, 
            self.daily_pnl, 
            len(self.open_positions)
        ):
            return None
        
        # Calcular precios de entrada y salida
        if signal == 'BUY':
            entry_price = market_data.ask  # Comprar al ask
            stop_loss = entry_price * 0.98  # 2% stop loss
            take_profit = entry_price * 1.04  # 4% take profit
        else:  # SELL
            entry_price = market_data.bid  # Vender al bid
            stop_loss = entry_price * 1.02  # 2% stop loss
            take_profit = entry_price * 0.96  # 4% take profit
        
        # Calcular tamaño de posición
        position_size = self.risk_manager.calculate_position_size(
            self.current_capital, entry_price, stop_loss
        )
        
        if position_size <= 0:
            return None
        
        # Simular ejecución del trade
        commission = self.risk_manager.calculate_commission(position_size, entry_price)
        spread_cost = self.risk_manager.calculate_spread_cost(position_size, entry_price)
        
        # Simular resultado del trade (simplificado)
        # En una implementación real, esto sería determinado por el mercado
        import random
        
        # Probabilidad de éxito basada en la calidad de la señal
        success_probability = 0.6  # 60% de trades exitosos
        is_winner = random.random() < success_probability
        
        if is_winner:
            exit_price = take_profit
        else:
            exit_price = stop_loss
        
        # Calcular P&L
        if signal == 'BUY':
            pnl = (exit_price - entry_price) * position_size
        else:
            pnl = (entry_price - exit_price) * position_size
        
        # Restar costos
        total_costs = commission + spread_cost
        net_pnl = pnl - total_costs
        pnl_pct = (net_pnl / (position_size * entry_price)) * 100
        
        # Actualizar capital
        self.current_capital += net_pnl
        self.daily_pnl += net_pnl
        
        # Crear objeto Trade
        trade = Trade(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            side=signal,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=position_size,
            pnl=net_pnl,
            pnl_pct=pnl_pct,
            commission=total_costs,
            duration_seconds=random.randint(30, 300),  # Duración simulada
            strategy_signal=signal,
            is_winner=is_winner
        )
        
        # Registrar trade
        self.performance.add_trade(trade)
        self.performance.update_equity(self.current_capital)
        
        return trade
    
    def update_visualization(self):
        """Actualiza la visualización en tiempo real"""
        try:
            # Limpiar plots
            for ax in [self.ax1, self.ax2, self.ax3, self.ax4]:
                ax.clear()
            
            # Curva de Equity
            if self.performance.equity_curve:
                timestamps = [datetime.fromisoformat(eq['timestamp']) for eq in self.performance.equity_curve]
                equity_values = [eq['equity'] for eq in self.performance.equity_curve]
                
                self.ax1.plot(timestamps, equity_values, 'cyan', linewidth=2)
                self.ax1.axhline(y=self.initial_capital, color='white', linestyle='--', alpha=0.5)
                self.ax1.set_title('Curva de Equity', color='white')
                self.ax1.set_ylabel('Capital (USDT)', color='white')
                self.ax1.tick_params(colors='white')
            
            # P&L por Trade
            if self.performance.trades:
                trade_pnls = [t.pnl for t in self.performance.trades]
                colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
                
                self.ax2.bar(range(len(trade_pnls)), trade_pnls, color=colors, alpha=0.7)
                self.ax2.axhline(y=0, color='white', linestyle='-', alpha=0.5)
                self.ax2.set_title('P&L por Trade', color='white')
                self.ax2.set_ylabel('P&L (USDT)', color='white')
                self.ax2.tick_params(colors='white')
            
            # Distribución de Retornos
            if len(self.performance.trades) > 5:
                returns = [t.pnl_pct for t in self.performance.trades]
                self.ax3.hist(returns, bins=20, color='orange', alpha=0.7, edgecolor='white')
                self.ax3.axvline(x=0, color='white', linestyle='--', alpha=0.5)
                self.ax3.set_title('Distribución de Retornos', color='white')
                self.ax3.set_ylabel('Frecuencia', color='white')
                self.ax3.tick_params(colors='white')
            
            # Métricas en Tiempo Real
            metrics = self.performance.calculate_metrics()
            if metrics:
                metrics_text = f"""
Capital Actual: ${metrics.get('current_equity', 0):,.2f}
Retorno Total: {metrics.get('total_return_pct', 0):+.2f}%
Trades Totales: {metrics.get('total_trades', 0)}
Tasa de Aciertos: {metrics.get('win_rate', 0):.1f}%
Factor de Ganancia: {metrics.get('profit_factor', 0):.2f}
Drawdown Máximo: {metrics.get('max_drawdown', 0):.2f}%
Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
P&L Diario: ${self.daily_pnl:+,.2f}
"""
                self.ax4.text(0.1, 0.9, metrics_text, transform=self.ax4.transAxes, 
                            fontsize=12, color='white', verticalalignment='top',
                            fontfamily='monospace')
            
            self.ax4.set_title('Métricas en Tiempo Real', color='white')
            self.ax4.axis('off')
            
            plt.tight_layout()
            plt.draw()
            plt.pause(0.01)
            
        except Exception as e:
            print(f"❌ Error actualizando visualización: {e}")
    
    def display_console_progress(self, symbol: str, market_data: MarketData, trade: Optional[Trade], signal_info: Dict = None):
        """Muestra progreso detallado por consola"""
        elapsed = datetime.now() - self.start_time
        current_time = datetime.now().strftime('%H:%M:%S')
        
        # Header con timestamp
        print(f"\n{'='*80}")
        print(f"[{current_time}] 📈 SIMULACIÓN DE TRADING EN TIEMPO REAL")
        print(f"{'='*80}")
        
        # Información del mercado
        print(f"🏷️  Símbolo: {symbol}")
        print(f"💲 Precio: ${market_data.price:,.4f}")
        print(f"📊 Spread: {market_data.spread_pct:.3f}%")
        print(f"📈 Volumen: {market_data.volume:,.0f}")
        
        # Información de la señal
        if signal_info:
            action_emoji = {
                'BUY': '🟢',
                'SELL': '🔴', 
                'HOLD': '⚪'
            }.get(signal_info.get('action', 'HOLD'), '⚪')
            
            confidence = signal_info.get('confidence', 0)
            reasons = signal_info.get('reasons', [])
            
            print(f"\n🎯 SEÑAL: {action_emoji} {signal_info.get('action', 'HOLD')}")
            print(f"🎲 Confianza: {confidence:.2f} ({confidence*100:.1f}%)")
            
            if reasons:
                print(f"📋 Razones: {', '.join(reasons[:3])}")
            
            # Indicadores técnicos
            indicators = signal_info.get('indicators', {})
            if indicators:
                print(f"📈 Indicadores:")
                if 'sma_fast' in indicators and indicators['sma_fast']:
                    print(f"   SMA Rápida: ${indicators['sma_fast']:.4f}")
                if 'sma_slow' in indicators and indicators['sma_slow']:
                    print(f"   SMA Lenta: ${indicators['sma_slow']:.4f}")
                if 'rsi' in indicators and indicators['rsi']:
                    print(f"   RSI: {indicators['rsi']:.1f}")
        
        # Información de capital y rendimiento
        total_pnl = self.performance.realized_pnl + self.performance.calculate_unrealized_pnl(self.open_positions, {symbol: market_data.price})
        roi_pct = (total_pnl / self.initial_capital) * 100
        
        print(f"\n💰 RENDIMIENTO:")
        print(f"   Capital Actual: ${self.current_capital:,.2f}")
        print(f"   P&L Diario: ${self.daily_pnl:+,.2f}")
        print(f"   P&L Total: ${total_pnl:+,.2f}")
        print(f"   ROI: {roi_pct:+.2f}%")
        
        # Información de trade si existe
        if trade:
            action_emoji = "🟢" if trade.side == 'BUY' else "🔴"
            status = "✅ GANADOR" if trade.is_winner else "❌ PERDEDOR"
            print(f"\n{action_emoji} TRADE EJECUTADO:")
            print(f"   Acción: {trade.side}")
            print(f"   Cantidad: {trade.quantity:.6f} {symbol}")
            print(f"   Precio: ${trade.entry_price:,.4f}")
            print(f"   Valor: ${trade.quantity * trade.entry_price:,.2f}")
            print(f"   Estado: {status}")
            print(f"   P&L: ${trade.pnl:+,.2f} ({trade.pnl_pct:+.2f}%)")
            if hasattr(trade, 'strategy_signal'):
                print(f"   Señal: {trade.strategy_signal}")
        
        # Posiciones actuales
        if self.open_positions:
            print(f"\n📊 POSICIONES ABIERTAS:")
            for pos_symbol, position in self.open_positions.items():
                if position.quantity > 0:
                    current_price = market_data.price if pos_symbol == symbol else position.avg_price
                    unrealized = (current_price - position.avg_price) * position.quantity
                    unrealized_pct = (unrealized / (position.avg_price * position.quantity)) * 100
                    
                    print(f"   {pos_symbol}:")
                    print(f"     Cantidad: {position.quantity:.6f}")
                    print(f"     Precio Promedio: ${position.avg_price:,.4f}")
                    print(f"     Precio Actual: ${current_price:,.4f}")
                    print(f"     P&L: ${unrealized:+,.2f} ({unrealized_pct:+.2f}%)")
        else:
            print(f"\n📊 POSICIONES: Sin posiciones abiertas")
        
        # Estadísticas de trading
        metrics = self.performance.calculate_metrics()
        if metrics and metrics.get('total_trades', 0) > 0:
            print(f"\n📈 ESTADÍSTICAS:")
            print(f"   Total Trades: {metrics['total_trades']}")
            print(f"   Tasa de Aciertos: {metrics['win_rate']:.1f}%")
            print(f"   Factor de Ganancia: {metrics.get('profit_factor', 0):.2f}")
            print(f"   Drawdown Máximo: {metrics.get('max_drawdown', 0):.2f}%")
            print(f"   Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        
        print(f"\n⏱️  Tiempo transcurrido: {str(elapsed).split('.')[0]}")
        print(f"{'='*80}")
    
    def display_table_format(self, symbol: str, market_data: MarketData, signal_info: Dict = None, trade: Optional[Trade] = None):
        """Muestra los datos en formato tabla para análisis"""
        current_time = datetime.now().strftime('%H:%M:%S')
        elapsed = datetime.now() - self.start_time
        
        # Limpiar pantalla
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Header principal
        print(f"\n{'='*120}")
        print(f"{'SIMULADOR DE TRADING EN TIEMPO REAL':^120}")
        print(f"{'Actualización: ' + current_time + ' | Tiempo: ' + str(elapsed).split('.')[0]:^120}")
        print(f"{'='*120}")
        
        # Tabla de datos de mercado
        print(f"\n📊 DATOS DE MERCADO")
        print(f"┌{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*15}┐")
        print(f"│{'SÍMBOLO':^15}│{'PRECIO':^15}│{'SPREAD %':^15}│{'VOLUMEN':^15}│{'SEÑAL':^15}│{'CONFIANZA':^15}│")
        print(f"├{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*15}┤")
        
        signal_action = signal_info.get('action', 'HOLD') if signal_info else 'HOLD'
        confidence = signal_info.get('confidence', 0) if signal_info else 0
        
        print(f"│{symbol:^15}│${market_data.price:>13.4f}│{market_data.spread_pct:>13.3f}%│{market_data.volume:>13,.0f}│{signal_action:^15}│{confidence*100:>13.1f}%│")
        print(f"└{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*15}┘")
        
        # Tabla de rendimiento
        total_pnl = self.performance.realized_pnl + self.performance.calculate_unrealized_pnl(self.open_positions, {symbol: market_data.price})
        roi_pct = (total_pnl / self.initial_capital) * 100
        
        print(f"\n💰 RENDIMIENTO Y CAPITAL")
        print(f"┌{'─'*20}┬{'─'*20}┬{'─'*20}┬{'─'*20}┬{'─'*20}┐")
        print(f"│{'CAPITAL INICIAL':^20}│{'CAPITAL ACTUAL':^20}│{'P&L DIARIO':^20}│{'P&L TOTAL':^20}│{'ROI %':^20}│")
        print(f"├{'─'*20}┼{'─'*20}┼{'─'*20}┼{'─'*20}┼{'─'*20}┤")
        print(f"│${self.initial_capital:>18.2f}│${self.current_capital:>18.2f}│${self.daily_pnl:>18.2f}│${total_pnl:>18.2f}│{roi_pct:>18.2f}%│")
        print(f"└{'─'*20}┴{'─'*20}┴{'─'*20}┴{'─'*20}┴{'─'*20}┘")
        
        # Tabla de trades recientes
        print(f"\n📈 TRADES RECIENTES (Últimos 5)")
        print(f"┌{'─'*12}┬{'─'*8}┬{'─'*12}┬{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*12}┐")
        print(f"│{'SÍMBOLO':^12}│{'LADO':^8}│{'CANTIDAD':^12}│{'PRECIO':^15}│{'P&L':^15}│{'P&L %':^15}│{'ESTADO':^12}│")
        print(f"├{'─'*12}┼{'─'*8}┼{'─'*12}┼{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*12}┤")
        
        recent_trades = self.performance.trades[-5:] if self.performance.trades else []
        if recent_trades:
            for t in recent_trades:
                status = "GANADOR" if t.is_winner else "PERDEDOR"
                print(f"│{t.symbol:^12}│{t.side:^8}│{t.quantity:>10.6f}│${t.entry_price:>13.4f}│${t.pnl:>13.2f}│{t.pnl_pct:>13.2f}%│{status:^12}│")
        else:
            print(f"│{'Sin trades ejecutados':^92}│")
        print(f"└{'─'*12}┴{'─'*8}┴{'─'*12}┴{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*12}┘")
        
        # Tabla de posiciones
        print(f"\n📊 POSICIONES ABIERTAS")
        print(f"┌{'─'*12}┬{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*15}┐")
        print(f"│{'SÍMBOLO':^12}│{'CANTIDAD':^15}│{'PRECIO PROM':^15}│{'PRECIO ACTUAL':^15}│{'P&L NO REAL':^15}│{'P&L %':^15}│")
        print(f"├{'─'*12}┼{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*15}┤")
        
        if self.open_positions:
            for pos_symbol, position in self.open_positions.items():
                if position.quantity > 0:
                    current_price = market_data.price if pos_symbol == symbol else position.avg_price
                    unrealized = (current_price - position.avg_price) * position.quantity
                    unrealized_pct = (unrealized / (position.avg_price * position.quantity)) * 100
                    
                    print(f"│{pos_symbol:^12}│{position.quantity:>13.6f}│${position.avg_price:>13.4f}│${current_price:>13.4f}│${unrealized:>13.2f}│{unrealized_pct:>13.2f}%│")
        else:
            print(f"│{'Sin posiciones abiertas':^87}│")
        print(f"└{'─'*12}┴{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*15}┘")
        
        # Tabla de estadísticas
        metrics = self.performance.calculate_metrics()
        print(f"\n📈 ESTADÍSTICAS DE TRADING")
        print(f"┌{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*15}┬{'─'*15}┐")
        print(f"│{'TOTAL TRADES':^15}│{'TASA ACIERTO':^15}│{'FACTOR GANAN':^15}│{'DRAWDOWN MAX':^15}│{'SHARPE RATIO':^15}│{'TRADES GANAN':^15}│")
        print(f"├{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*15}┼{'─'*15}┤")
        
        if metrics and metrics.get('total_trades', 0) > 0:
            print(f"│{metrics['total_trades']:^15}│{metrics['win_rate']:>13.1f}%│{metrics.get('profit_factor', 0):>13.2f}│{metrics.get('max_drawdown', 0):>13.2f}%│{metrics.get('sharpe_ratio', 0):>13.2f}│{metrics['winning_trades']:^15}│")
        else:
            print(f"│{'Sin estadísticas disponibles':^90}│")
        print(f"└{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*15}┴{'─'*15}┘")
        
        # Información del último trade si existe
        if trade:
            action_emoji = "🟢" if trade.side == 'BUY' else "🔴"
            status = "GANADOR" if trade.is_winner else "PERDEDOR"
            print(f"\n{action_emoji} ÚLTIMO TRADE EJECUTADO: {trade.side} {trade.quantity:.6f} {symbol} @ ${trade.entry_price:,.4f} | P&L: ${trade.pnl:+,.2f} ({trade.pnl_pct:+.2f}%) | {status}")
        
        print(f"\n{'='*120}")
        print(f"{'SIMULACIÓN EJECUTÁNDOSE INDEFINIDAMENTE - Presiona Ctrl+C para detener':^120}")
        print(f"{'='*120}")
    
    def save_report(self):
        """Guarda reporte final de la simulación"""
        metrics = self.performance.calculate_metrics()
        
        report = {
            'simulation_info': {
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
                'symbols': self.symbols,
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital
            },
            'performance_metrics': metrics,
            'trades': [asdict(trade) for trade in self.performance.trades],
            'equity_curve': self.performance.equity_curve
        }
        
        try:
            with open(self.report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"\n📄 Reporte guardado: {self.report_file}")
        except Exception as e:
            print(f"❌ Error guardando reporte: {e}")
    
    async def run_simulation(self):
        """Ejecuta la simulación principal"""
        print("\n🎯 Iniciando simulación en tiempo real...")
        print("📊 Actualizando progreso cada 30 segundos...\n")
        
        iteration = 0
        last_display_time = datetime.now()
        
        try:
            # Ejecutar indefinidamente hasta Ctrl+C
            while True:
                iteration += 1
                current_time = datetime.now()
                
                # Resetear métricas diarias si es necesario
                self.reset_daily_metrics()
                
                # Procesar cada símbolo
                for symbol in self.symbols:
                    
                    # Obtener datos del mercado
                    ticker_data = self.data_provider.get_ticker_price(symbol)
                    if not ticker_data:
                        continue
                    
                    market_data = MarketData(
                        timestamp=datetime.now().isoformat(),
                        symbol=symbol,
                        price=ticker_data['price'],
                        volume=ticker_data['volume'],
                        bid=ticker_data['bid'],
                        ask=ticker_data['ask'],
                        spread=ticker_data['spread'],
                        spread_pct=ticker_data['spread_pct']
                    )
                    
                    # Actualizar estrategia con nuevos datos
                    self.strategy.update_data(market_data.price, market_data.volume)
                    
                    # Generar señal de trading
                    signal = self.strategy.generate_signal()
                    
                    # Obtener información detallada de la señal
                    signal_info = self.strategy.last_signal if self.strategy.last_signal else {
                        'action': signal,
                        'confidence': 0,
                        'reasons': []
                    }
                    
                    # Ejecutar trade si hay señal
                    trade = None
                    if signal in ['BUY', 'SELL']:
                        trade = self.execute_trade(symbol, signal, market_data)
                        if trade:
                            trade.strategy_signal = f"{signal} (conf: {signal_info['confidence']:.2f})"
                    
                    # Registrar eventos
                    self.log_event('market_data', asdict(market_data))
                    if trade:
                        self.log_event('trade_executed', asdict(trade))
                    
                    # Mostrar progreso en formato tabla cada 30 segundos o si hay trade
                    time_since_display = (current_time - last_display_time).total_seconds()
                    if time_since_display >= 30 or trade:
                        self.display_table_format(symbol, market_data, signal_info, trade)
                        last_display_time = current_time
                    
                    # Actualizar visualización
                    if iteration % 10 == 0:  # Cada 10 iteraciones
                        self.update_visualization()
                    
                    # Pausa entre símbolos
                    await asyncio.sleep(2)
                
                # Pausa entre ciclos (ajustado para refresh de 30 segundos)
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            print("\n⚠️  Simulación interrumpida por el usuario")
        except Exception as e:
            print(f"❌ Error en simulación: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Guardar reporte final
            self.save_report()
            
            # Mostrar resumen final
            print("\n" + "="*60)
            print("📊 RESUMEN FINAL DE LA SIMULACIÓN")
            print("="*60)
            
            metrics = self.performance.calculate_metrics()
            if metrics:
                print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
                print(f"💰 Capital final: ${metrics['current_equity']:,.2f}")
                print(f"📈 Retorno total: {metrics['total_return_pct']:+.2f}%")
                print(f"🎯 Trades totales: {metrics['total_trades']}")
                print(f"✅ Tasa de aciertos: {metrics['win_rate']:.1f}%")
                print(f"📊 Factor de ganancia: {metrics['profit_factor']:.2f}")
                print(f"📉 Drawdown máximo: {metrics['max_drawdown']:.2f}%")
                print(f"📈 Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            
            duration = datetime.now() - self.start_time
            print(f"⏱️  Duración: {str(duration).split('.')[0]}")
            print("="*60)
            
            # Gráficos deshabilitados para modo consola
            print("\n📈 Simulación completada. Los gráficos están deshabilitados para evitar ventanas.")
            # try:
            #     plt.show()
            # except:
            #     pass

def main():
    """Función principal"""
    # Configuración de la simulación
    SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']  # Símbolos a tradear
    INITIAL_CAPITAL = 500.0  # Capital inicial en USDT
    
    # Configuración de estrategia personalizable
    STRATEGY_CONFIG = {
        'sma_fast': 10,
        'sma_slow': 20,
        'rsi_period': 14,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'bb_period': 20,
        'bb_std': 2,
        'min_signal_confidence': 0.6,
        'volume_threshold': 1.5
    }
    
    # Crear y ejecutar simulador
    simulator = RealTimeTradingSimulator(SYMBOLS, INITIAL_CAPITAL, STRATEGY_CONFIG)
    
    # Ejecutar simulación
    try:
        asyncio.run(simulator.run_simulation())
    except KeyboardInterrupt:
        print("\n👋 Simulación finalizada")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()