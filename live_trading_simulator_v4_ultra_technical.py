#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulador V4 Ultra-Agresivo con Información Técnica Detallada
Estrategia de Trading con Datos Reales de Binance
Objetivo: 15% mensual con apalancamiento 3x
Incluye: Posiciones abiertas, rendimientos y gestión de trades
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
from colorama import init, Fore, Back, Style
import os

# Inicializar colorama para Windows
init(autoreset=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('simulation_logs_detailed.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Configurar el handler de consola para evitar errores de codificación
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream.name == '<stderr>':
        handler.stream.reconfigure(encoding='utf-8', errors='replace')

logger = logging.getLogger(__name__)

@dataclass
class TechnicalIndicators:
    """Indicadores técnicos calculados"""
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_width: float
    ema_fast: float
    ema_slow: float
    volume_sma: float
    price_change_1h: float
    price_change_4h: float
    volatility: float
    momentum: float
    
@dataclass
class MarketData:
    """Datos de mercado en tiempo real"""
    symbol: str
    price: float
    volume: float
    high_24h: float
    low_24h: float
    change_24h: float
    timestamp: datetime
    indicators: TechnicalIndicators
    
@dataclass
class TradingSignal:
    """Señal de trading generada"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    strength: str  # WEAK, MEDIUM, STRONG, ULTRA
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    position_size: float
    leverage: float
    risk_reward: float
    reason: str
    technical_score: float
    momentum_score: float
    volatility_score: float
    timestamp: datetime

@dataclass
class Position:
    """Representa una posición abierta"""
    id: str
    symbol: str
    side: str  # LONG, SHORT
    entry_price: float
    current_price: float
    quantity: float
    leverage: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    margin_used: float
    entry_time: datetime
    status: str  # OPEN, CLOSED
    # Nuevos campos para protección de ganancias
    trailing_stop_active: bool = False
    trailing_stop_distance: float = 0.0
    highest_price: float = 0.0  # Para LONG
    lowest_price: float = 0.0   # Para SHORT
    break_even_triggered: bool = False
    partial_tp_executed: List[str] = None  # Lista de TPs ejecutados parcialmente
    
    def __post_init__(self):
        if self.partial_tp_executed is None:
            self.partial_tp_executed = []
    
    @property
    def duration(self) -> float:
        """Duración de la posición en minutos"""
        return (datetime.now() - self.entry_time).total_seconds() / 60.0
    
@dataclass
class Trade:
    """Trade ejecutado"""
    id: str
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    quantity: float
    leverage: float
    pnl: float
    pnl_pct: float
    entry_time: datetime
    exit_time: datetime
    duration: timedelta
    exit_reason: str  # TP1, TP2, TP3, SL, MANUAL

class BinanceRealDataProvider:
    """Proveedor de datos reales de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.session = requests.Session()
        
    def get_ticker_24h(self, symbol: str) -> Dict:
        """Obtener datos de ticker 24h"""
        try:
            response = self.session.get(f"{self.base_url}/ticker/24hr", 
                                      params={"symbol": symbol})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo ticker {symbol}: {e}")
            return {}
            
    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 100) -> List:
        """Obtener datos de velas"""
        try:
            response = self.session.get(f"{self.base_url}/klines",
                                      params={
                                          "symbol": symbol,
                                          "interval": interval,
                                          "limit": limit
                                      })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error obteniendo klines {symbol}: {e}")
            return []
            
class TechnicalAnalyzer:
    """Analizador técnico avanzado"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calcular RSI"""
        if len(prices) < period + 1:
            return 50.0
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
        
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """Calcular MACD"""
        if len(prices) < slow:
            return 0.0, 0.0, 0.0
            
        prices_array = np.array(prices)
        ema_fast = TechnicalAnalyzer.calculate_ema(prices, fast)
        ema_slow = TechnicalAnalyzer.calculate_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # Calcular señal MACD (simplificado)
        signal_line = macd_line * 0.8  # Aproximación
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
        
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> float:
        """Calcular EMA"""
        if len(prices) < period:
            return np.mean(prices) if prices else 0.0
            
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            
        return ema
        
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[float, float, float, float]:
        """Calcular Bandas de Bollinger"""
        if len(prices) < period:
            avg = np.mean(prices) if prices else 0.0
            return avg, avg, avg, 0.0
            
        recent_prices = prices[-period:]
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        width = ((upper - lower) / middle) * 100 if middle > 0 else 0
        
        return upper, middle, lower, width

class PositionManager:
    """Gestor de posiciones"""
    
    def __init__(self):
        logger.debug("Initializing PositionManager")
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.position_counter = 0
        self.trade_counter = 0
        
    def open_position(self, signal: TradingSignal, current_price: float, capital: float) -> Optional[Position]:
        logger.debug(f"Entering open_position: symbol={signal.symbol}, action={signal.action}, confidence={signal.confidence}, price={current_price}, capital={capital}")
        self.position_counter += 1
        position_id = f"POS_{self.position_counter:04d}"
        
        # Calcular cantidad basada en el capital disponible
        margin_used = signal.position_size / signal.leverage
        max_margin = capital * 0.8
        
        print(f"🔍 DEBUG POSITION - Position size: ${signal.position_size:.2f}, Leverage: {signal.leverage}x")
        print(f"🔍 DEBUG POSITION - Margin needed: ${margin_used:.2f}, Max margin (80%): ${max_margin:.2f}")
        
        if margin_used > max_margin:  # No usar más del 80% del capital
            print(f"❌ POSICIÓN RECHAZADA - Margen requerido (${margin_used:.2f}) > Máximo permitido (${max_margin:.2f})")
            return None
        
        print(f"✅ POSICIÓN APROBADA - Margen OK")
            
        side = "LONG" if signal.action == "BUY" else "SHORT"
        
        position = Position(
            id=position_id,
            symbol=signal.symbol,
            side=side,
            entry_price=current_price,
            current_price=current_price,
            quantity=signal.position_size,
            leverage=signal.leverage,
            stop_loss=signal.stop_loss,
            take_profit_1=signal.take_profit_1,
            take_profit_2=signal.take_profit_2,
            take_profit_3=signal.take_profit_3,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            margin_used=margin_used,
            entry_time=datetime.now(),
            status="OPEN",
            # Inicializar campos de protección de ganancias
            trailing_stop_active=False,
            trailing_stop_distance=abs(current_price - signal.stop_loss) * 0.5,  # 50% de la distancia inicial
            highest_price=current_price if signal.action == "BUY" else 0.0,
            lowest_price=current_price if signal.action == "SELL" else float('inf'),
            break_even_triggered=False,
            partial_tp_executed=[]
        )
        
        self.positions[position_id] = position
        logger.info(f"Opened position: ID={position.id}, Symbol={position.symbol}, Side={position.side}, Entry Price={position.entry_price}, Quantity={position.quantity}, Leverage={position.leverage}, SL={position.stop_loss}, TP1={position.take_profit_1}, TP2={position.take_profit_2}, TP3={position.take_profit_3}, Margin Used={position.margin_used}")
        return position
        
    def update_positions(self, market_data: Dict[str, MarketData]):
        logger.debug(f"Updating positions with {len(market_data)} market data entries")
        for position in self.positions.values():
            if position.status == "OPEN" and position.symbol in market_data:
                current_price = market_data[position.symbol].price
                position.current_price = current_price
                
                # Calcular PnL no realizado
                if position.side == "LONG":
                    price_diff = current_price - position.entry_price
                else:  # SHORT
                    price_diff = position.entry_price - current_price
                    
                # PnL = (diferencia_precio / precio_entrada) * valor_posicion * apalancamiento
                position_value = position.quantity
                position.unrealized_pnl = (price_diff / position.entry_price) * position_value * position.leverage
                position.unrealized_pnl_pct = (price_diff / position.entry_price) * 100
                
                # Aplicar nuevas funciones de protección de ganancias
                self.update_trailing_stop(position, current_price)
                self.check_break_even(position, current_price)
                
    def check_exit_conditions(self, market_data: Dict[str, MarketData]) -> List[Trade]:
        logger.debug(f"Checking exit conditions for {len(self.positions)} positions")
        executed_trades = []
        
        for position in list(self.positions.values()):
            if position.status != "OPEN" or position.symbol not in market_data:
                continue
                
            current_price = market_data[position.symbol].price
            exit_reason = None
            
            # Verificar take profit parcial primero
            partial_trade = self.check_partial_take_profit(position, current_price)
            if partial_trade:
                executed_trades.append(partial_trade)
            
            # Verificar Stop Loss
            if position.side == "LONG" and current_price <= position.stop_loss:
                exit_reason = "SL"
            elif position.side == "SHORT" and current_price >= position.stop_loss:
                exit_reason = "SL"
                
            # Verificar Take Profit 3 (cierre completo)
            elif position.side == "LONG":
                if current_price >= position.take_profit_3:
                    exit_reason = "TP3"
            else:  # SHORT
                if current_price <= position.take_profit_3:
                    exit_reason = "TP3"
                    
            # Solo cerrar completamente si hay una razón de salida
            if exit_reason:
                trade = self.close_position(position, current_price, exit_reason)
                if trade:
                    executed_trades.append(trade)
                    
        return executed_trades
        
    def close_position(self, position: Position, exit_price: float, exit_reason: str) -> Optional[Trade]:
        logger.debug(f"Closing position {position.id}: exit_price={exit_price}, reason={exit_reason}")
        if position.status != "OPEN":
            return None
            
        self.trade_counter += 1
        trade_id = f"TRD_{self.trade_counter:04d}"
        
        # Calcular PnL
        if position.side == "LONG":
            price_diff = exit_price - position.entry_price
        else:  # SHORT
            price_diff = position.entry_price - exit_price
            
        pnl = (price_diff / position.entry_price) * position.quantity
        pnl_pct = (price_diff / position.entry_price) * 100
        
        trade = Trade(
            id=trade_id,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=position.quantity,
            leverage=position.leverage,
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            duration=datetime.now() - position.entry_time,
            exit_reason=exit_reason
        )
        
        position.status = "CLOSED"
        self.trades.append(trade)
        if position.id in self.positions:
            del self.positions[position.id]
        logger.info(f"Closed trade: ID={trade.id}, Symbol={trade.symbol}, Side={trade.side}, Entry Price={trade.entry_price}, Exit Price={trade.exit_price}, Quantity={trade.quantity}, Leverage={trade.leverage}, PnL={trade.pnl}, PnL %={trade.pnl_pct}, Duration={trade.duration}, Reason={trade.exit_reason}")
        return trade
        
    def get_open_positions(self) -> List[Position]:
        logger.debug("Retrieving open positions")
        return [pos for pos in self.positions.values() if pos.status == "OPEN"]
        
    def get_total_unrealized_pnl(self) -> float:
        logger.debug("Calculating total unrealized PnL")
        return sum(pos.unrealized_pnl for pos in self.get_open_positions())
        
    def get_total_margin_used(self) -> float:
        logger.debug("Calculating total margin used")
        return sum(pos.margin_used for pos in self.get_open_positions())
        
    def get_trading_stats(self) -> Dict:
        logger.debug("Generating trading statistics")
        
        # Obtener posiciones abiertas y PnL no realizado
        open_positions = self.get_open_positions()
        unrealized_pnl = self.get_total_unrealized_pnl()
        
        if not self.trades:
            stats = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "open_positions": len(open_positions),
                "unrealized_pnl": unrealized_pnl,
                "total_pnl_including_unrealized": unrealized_pnl
            }
            logger.info(f"Trading stats summary: {stats}")
            return stats
            
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl < 0]
        
        total_pnl = sum(t.pnl for t in self.trades)
        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        
        return {
            "total_trades": len(self.trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(self.trades) * 100 if self.trades else 0,
            "total_pnl": total_pnl,
            "avg_win": total_wins / len(winning_trades) if winning_trades else 0,
            "avg_loss": total_losses / len(losing_trades) if losing_trades else 0,
            "profit_factor": total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0,
            "open_positions": len(open_positions),
            "unrealized_pnl": unrealized_pnl,
            "total_pnl_including_unrealized": total_pnl + unrealized_pnl
        }
    
    def update_trailing_stop(self, position: Position, current_price: float):
        """Actualizar trailing stop dinámico"""
        if position.side == "LONG":
            # Actualizar precio más alto
            if current_price > position.highest_price:
                position.highest_price = current_price
                # Activar trailing stop si hay ganancia del 1%
                if not position.trailing_stop_active and current_price > position.entry_price * 1.01:
                    position.trailing_stop_active = True
                    logger.info(f"Trailing stop activado para {position.symbol} en {current_price}")
                
                # Actualizar stop loss si trailing stop está activo
                if position.trailing_stop_active:
                    new_stop = position.highest_price - position.trailing_stop_distance
                    if new_stop > position.stop_loss:
                        position.stop_loss = new_stop
                        logger.debug(f"Stop loss actualizado a {new_stop} para {position.symbol}")
        
        else:  # SHORT
            # Actualizar precio más bajo
            if current_price < position.lowest_price:
                position.lowest_price = current_price
                # Activar trailing stop si hay ganancia del 1%
                if not position.trailing_stop_active and current_price < position.entry_price * 0.99:
                    position.trailing_stop_active = True
                    logger.info(f"Trailing stop activado para {position.symbol} en {current_price}")
                
                # Actualizar stop loss si trailing stop está activo
                if position.trailing_stop_active:
                    new_stop = position.lowest_price + position.trailing_stop_distance
                    if new_stop < position.stop_loss:
                        position.stop_loss = new_stop
                        logger.debug(f"Stop loss actualizado a {new_stop} para {position.symbol}")
    
    def check_break_even(self, position: Position, current_price: float):
        """Verificar y aplicar break-even automático"""
        if position.break_even_triggered:
            return
        
        profit_threshold = 0.015  # 1.5% de ganancia para activar break-even
        
        if position.side == "LONG":
            if current_price >= position.entry_price * (1 + profit_threshold):
                position.stop_loss = position.entry_price * 1.001  # Break-even + 0.1%
                position.break_even_triggered = True
                logger.info(f"Break-even activado para {position.symbol} LONG en {current_price}")
        
        else:  # SHORT
            if current_price <= position.entry_price * (1 - profit_threshold):
                position.stop_loss = position.entry_price * 0.999  # Break-even + 0.1%
                position.break_even_triggered = True
                logger.info(f"Break-even activado para {position.symbol} SHORT en {current_price}")
    
    def check_partial_take_profit(self, position: Position, current_price: float) -> Optional[Trade]:
        """Verificar y ejecutar take profit parcial"""
        partial_size = 0.33  # 33% de la posición
        
        if position.side == "LONG":
            # TP1 parcial
            if "TP1" not in position.partial_tp_executed and current_price >= position.take_profit_1:
                position.partial_tp_executed.append("TP1")
                return self._execute_partial_close(position, current_price, "TP1_PARTIAL", partial_size)
            
            # TP2 parcial
            elif "TP2" not in position.partial_tp_executed and current_price >= position.take_profit_2:
                position.partial_tp_executed.append("TP2")
                return self._execute_partial_close(position, current_price, "TP2_PARTIAL", partial_size)
        
        else:  # SHORT
            # TP1 parcial
            if "TP1" not in position.partial_tp_executed and current_price <= position.take_profit_1:
                position.partial_tp_executed.append("TP1")
                return self._execute_partial_close(position, current_price, "TP1_PARTIAL", partial_size)
            
            # TP2 parcial
            elif "TP2" not in position.partial_tp_executed and current_price <= position.take_profit_2:
                position.partial_tp_executed.append("TP2")
                return self._execute_partial_close(position, current_price, "TP2_PARTIAL", partial_size)
        
        return None
    
    def _execute_partial_close(self, position: Position, exit_price: float, exit_reason: str, partial_size: float) -> Trade:
        """Ejecutar cierre parcial de posición"""
        self.trade_counter += 1
        trade_id = f"TRD_{self.trade_counter:04d}"
        
        # Calcular cantidad parcial
        partial_quantity = position.quantity * partial_size
        
        # Calcular PnL parcial
        if position.side == "LONG":
            price_diff = exit_price - position.entry_price
        else:  # SHORT
            price_diff = position.entry_price - exit_price
            
        pnl = (price_diff / position.entry_price) * partial_quantity
        pnl_pct = (price_diff / position.entry_price) * 100
        
        # Reducir la posición
        position.quantity -= partial_quantity
        position.margin_used *= (1 - partial_size)
        
        trade = Trade(
            id=trade_id,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            quantity=partial_quantity,
            leverage=position.leverage,
            pnl=pnl,
            pnl_pct=pnl_pct,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            duration=datetime.now() - position.entry_time,
            exit_reason=exit_reason
        )
        
        self.trades.append(trade)
        logger.info(f"Cierre parcial ejecutado: {exit_reason} - {partial_size*100}% de {position.symbol} - PnL: {pnl:.2f}")
        return trade

class UltraAggressiveStrategyV4:
    def __init__(self, capital: float = 500.0, leverage: float = 3.0):
        logger.debug(f"Initializing UltraAggressiveStrategyV4 with capital={capital}, leverage={leverage}")
        self.initial_capital = capital
        self.current_capital = capital
        self.leverage = leverage
        self.risk_per_trade = 0.05  # 5% del capital por trade
        self.min_confidence = 0.30  # Confianza mínima para ejecutar (30%)
        self.analyzer = TechnicalAnalyzer()
        self.position_manager = PositionManager()
        
    def update_capital(self, realized_pnl: float):
        """Actualizar capital con PnL realizado"""
        self.current_capital += realized_pnl
        
    def get_available_capital(self) -> float:
        """Obtener capital disponible para trading"""
        margin_used = self.position_manager.get_total_margin_used()
        return self.current_capital - margin_used
        
    def analyze_market_data(self, market_data: MarketData) -> TradingSignal:
        """Analizar datos de mercado y generar señal"""
        indicators = market_data.indicators
        
        # Scores individuales
        rsi_score = self._calculate_rsi_score(indicators.rsi)
        logger.debug(f"RSI score: {rsi_score}")
        macd_score = self._calculate_macd_score(indicators.macd, indicators.macd_signal)
        logger.debug(f"MACD score: {macd_score}")
        bb_score = self._calculate_bb_score(market_data.price, indicators.bb_upper, 
                                          indicators.bb_middle, indicators.bb_lower)
        logger.debug(f"BB score: {bb_score}")
        momentum_score = self._calculate_momentum_score(indicators.momentum)
        logger.debug(f"Momentum score: {momentum_score}")
        volatility_score = self._calculate_volatility_score(indicators.volatility)
        logger.debug(f"Volatility score: {volatility_score}")
        volume_score = self._calculate_volume_score(market_data.volume, indicators.volume_sma)
        
        # Score técnico combinado
        technical_score = (rsi_score * 0.25 + macd_score * 0.25 + bb_score * 0.20 + 
                          momentum_score * 0.15 + volatility_score * 0.10 + volume_score * 0.05)
        
        # Determinar acción y confianza
        action, confidence, strength = self._determine_action(technical_score, indicators)
        logger.debug(f"Determined action: {action}, confidence: {confidence}, strength: {strength}")
        
        # Calcular precios de entrada y salida
        entry_price = market_data.price
        stop_loss, tp1, tp2, tp3 = self._calculate_levels(entry_price, action, indicators.volatility)
        
        # Calcular tamaño de posición
        position_size = self._calculate_position_size(entry_price, stop_loss)
        logger.debug(f"Calculated position size: {position_size}")
        
        # Razón de la señal
        reason = self._generate_reason(rsi_score, macd_score, bb_score, momentum_score)
        logger.debug(f"Generated reason: {reason}")
        
        return TradingSignal(
            symbol=market_data.symbol,
            action=action,
            confidence=confidence,
            strength=strength,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            position_size=position_size,
            leverage=self.leverage,
            risk_reward=abs((tp1 - entry_price) / (entry_price - stop_loss)) if action == "BUY" else abs((entry_price - tp1) / (stop_loss - entry_price)),
            reason=reason,
            technical_score=technical_score,
            momentum_score=momentum_score,
            volatility_score=volatility_score,
            timestamp=datetime.now()
        )
        
    def _calculate_rsi_score(self, rsi: float) -> float:
        """Calcular score basado en RSI"""
        if rsi <= 20:
            return 1.0  # Muy oversold - señal de compra fuerte
        elif rsi <= 30:
            return 0.7  # Oversold - señal de compra
        elif rsi >= 80:
            return -1.0  # Muy overbought - señal de venta fuerte
        elif rsi >= 70:
            return -0.7  # Overbought - señal de venta
        else:
            return 0.0  # Neutral
            
    def _calculate_macd_score(self, macd: float, signal: float) -> float:
        """Calcular score basado en MACD"""
        if macd > signal and macd > 0:
            return 0.8  # Tendencia alcista fuerte
        elif macd > signal:
            return 0.5  # Cruce alcista
        elif macd < signal and macd < 0:
            return -0.8  # Tendencia bajista fuerte
        elif macd < signal:
            return -0.5  # Cruce bajista
        else:
            return 0.0
            
    def _calculate_bb_score(self, price: float, upper: float, middle: float, lower: float) -> float:
        """Calcular score basado en Bandas de Bollinger"""
        if price <= lower:
            return 0.9  # Precio en banda inferior - señal de compra
        elif price >= upper:
            return -0.9  # Precio en banda superior - señal de venta
        elif price > middle:
            return 0.3  # Precio sobre media
        else:
            return -0.3  # Precio bajo media
            
    def _calculate_momentum_score(self, momentum: float) -> float:
        """Calcular score basado en momentum"""
        return max(-1.0, min(1.0, momentum / 10.0))
        
    def _calculate_volatility_score(self, volatility: float) -> float:
        """Calcular score basado en volatilidad"""
        if volatility > 5.0:
            return 0.8  # Alta volatilidad - buena para scalping
        elif volatility > 2.0:
            return 0.5
        else:
            return 0.2
            
    def _calculate_volume_score(self, volume: float, volume_sma: float) -> float:
        """Calcular score basado en volumen"""
        if volume_sma > 0:
            ratio = volume / volume_sma
            if ratio > 1.5:
                return 0.7  # Volumen alto
            elif ratio > 1.2:
                return 0.4
            else:
                return 0.1
        return 0.0
        
    def _determine_action(self, technical_score: float, indicators: TechnicalIndicators) -> Tuple[str, float, str]:
        """Determinar acción basada en score técnico"""
        confidence = abs(technical_score)
        
        if technical_score >= 0.8:
            return "BUY", confidence, "ULTRA"
        elif technical_score >= 0.6:
            return "BUY", confidence, "STRONG"
        elif technical_score >= 0.3:  # Ajustado para coincidir con min_confidence
            return "BUY", confidence, "MEDIUM"
        elif technical_score <= -0.8:
            return "SELL", confidence, "ULTRA"
        elif technical_score <= -0.6:
            return "SELL", confidence, "STRONG"
        elif technical_score <= -0.3:  # Ajustado para coincidir con min_confidence
            return "SELL", confidence, "MEDIUM"
        else:
            return "HOLD", confidence, "WEAK"
            
    def _calculate_levels(self, entry_price: float, action: str, volatility: float) -> Tuple[float, float, float, float]:
        """Calcular niveles de stop loss y take profit"""
        # Ajustar niveles basado en volatilidad
        base_sl = 0.015  # 1.5% base
        base_tp1 = 0.025  # 2.5% base
        base_tp2 = 0.045  # 4.5% base
        base_tp3 = 0.070  # 7.0% base
        
        # Ajustar por volatilidad
        vol_multiplier = max(0.5, min(2.0, volatility / 3.0))
        
        sl_pct = base_sl * vol_multiplier
        tp1_pct = base_tp1 * vol_multiplier
        tp2_pct = base_tp2 * vol_multiplier
        tp3_pct = base_tp3 * vol_multiplier
        
        if action == "BUY":
            stop_loss = entry_price * (1 - sl_pct)
            tp1 = entry_price * (1 + tp1_pct)
            tp2 = entry_price * (1 + tp2_pct)
            tp3 = entry_price * (1 + tp3_pct)
        else:  # SELL
            stop_loss = entry_price * (1 + sl_pct)
            tp1 = entry_price * (1 - tp1_pct)
            tp2 = entry_price * (1 - tp2_pct)
            tp3 = entry_price * (1 - tp3_pct)
            
        return stop_loss, tp1, tp2, tp3
        
    def _calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calcular tamaño de posición basado en riesgo"""
        available_capital = self.get_available_capital()
        risk_amount = available_capital * self.risk_per_trade
        price_diff = abs(entry_price - stop_loss)
        
        if price_diff > 0:
            position_size = (risk_amount / price_diff) * self.leverage
            max_position = available_capital * self.leverage * 0.3  # Máximo 30% del capital disponible
            return min(position_size, max_position)
        return 0.0
        
    def _generate_reason(self, rsi_score: float, macd_score: float, bb_score: float, momentum_score: float) -> str:
        """Generar razón de la señal"""
        reasons = []
        
        if abs(rsi_score) > 0.6:
            reasons.append(f"RSI {'oversold' if rsi_score > 0 else 'overbought'}")
        if abs(macd_score) > 0.4:
            reasons.append(f"MACD {'bullish' if macd_score > 0 else 'bearish'}")
        if abs(bb_score) > 0.6:
            reasons.append(f"BB {'lower band' if bb_score > 0 else 'upper band'}")
        if abs(momentum_score) > 0.5:
            reasons.append(f"Strong {'positive' if momentum_score > 0 else 'negative'} momentum")
            
        return ", ".join(reasons) if reasons else "Weak signals"

class LiveTradingSimulatorV4:
    """Simulador de trading en vivo V4 con gestión de posiciones y rendimientos"""
    
    def __init__(self):
        self.data_provider = BinanceRealDataProvider()
        self.strategy = UltraAggressiveStrategyV4()
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
        self.running = False
        self.signals_generated = 0
        self.start_time = datetime.now()
        
    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Obtener datos de mercado completos"""
        try:
            # Obtener ticker 24h
            ticker = self.data_provider.get_ticker_24h(symbol)
            if not ticker:
                return None
                
            # Obtener klines para indicadores
            klines = self.data_provider.get_klines(symbol, "1m", 100)
            if not klines:
                return None
                
            # Extraer precios de cierre
            prices = [float(kline[4]) for kline in klines]
            volumes = [float(kline[5]) for kline in klines]
            
            current_price = float(ticker['lastPrice'])
            current_volume = float(ticker['volume'])
            
            # Calcular indicadores técnicos
            rsi = self.strategy.analyzer.calculate_rsi(prices)
            macd, macd_signal, macd_hist = self.strategy.analyzer.calculate_macd(prices)
            bb_upper, bb_middle, bb_lower, bb_width = self.strategy.analyzer.calculate_bollinger_bands(prices)
            
            ema_fast = self.strategy.analyzer.calculate_ema(prices, 12)
            ema_slow = self.strategy.analyzer.calculate_ema(prices, 26)
            volume_sma = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
            
            # Calcular cambios de precio
            price_change_1h = ((current_price - prices[-60]) / prices[-60] * 100) if len(prices) >= 60 else 0
            price_change_4h = ((current_price - prices[-240]) / prices[-240] * 100) if len(prices) >= 240 else 0
            
            # Calcular volatilidad y momentum
            volatility = np.std(prices[-20:]) / np.mean(prices[-20:]) * 100 if len(prices) >= 20 else 0
            momentum = price_change_1h * 2 + price_change_4h  # Weighted momentum
            
            indicators = TechnicalIndicators(
                rsi=rsi,
                macd=macd,
                macd_signal=macd_signal,
                macd_histogram=macd_hist,
                bb_upper=bb_upper,
                bb_middle=bb_middle,
                bb_lower=bb_lower,
                bb_width=bb_width,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                volume_sma=volume_sma,
                price_change_1h=price_change_1h,
                price_change_4h=price_change_4h,
                volatility=volatility,
                momentum=momentum
            )
            
            return MarketData(
                symbol=symbol,
                price=current_price,
                volume=current_volume,
                high_24h=float(ticker['highPrice']),
                low_24h=float(ticker['lowPrice']),
                change_24h=float(ticker['priceChangePercent']),
                timestamp=datetime.now(),
                indicators=indicators
            )
            
        except Exception as e:
            print(f"❌ Error obteniendo datos para {symbol}: {e}")
            return None
            
    def print_portfolio_status(self):
        """Imprimir estado del portfolio"""
        open_positions = self.strategy.position_manager.get_open_positions()
        total_unrealized_pnl = self.strategy.position_manager.get_total_unrealized_pnl()
        total_margin_used = self.strategy.position_manager.get_total_margin_used()
        available_capital = self.strategy.get_available_capital()
        stats = self.strategy.position_manager.get_trading_stats()
        total_balance = self.strategy.current_capital + total_unrealized_pnl
        total_return = ((total_balance - self.strategy.initial_capital) / self.strategy.initial_capital) * 100
        session_time = (datetime.now() - self.start_time).total_seconds() / 3600
        
        print(f"{Fore.CYAN}┌{'─' * 50}┐")
        print(f"{Fore.CYAN}│{Fore.WHITE} 💼 ESTADO DEL PORTFOLIO {' ' * 23}{Fore.CYAN}│")
        print(f"{Fore.CYAN}├{'─' * 50}┤")
        print(f"{Fore.CYAN}│{Fore.WHITE} 💰 Capital inicial: {Fore.GREEN}${self.strategy.initial_capital:.2f} USDT {' ' * 5}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 💰 Capital actual: {Fore.GREEN}${self.strategy.current_capital:.2f} USDT {' ' * 6}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 💰 Capital disponible: {Fore.YELLOW}${available_capital:.2f} USDT {Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 🔒 Margen usado: {Fore.RED}${total_margin_used:.2f} USDT {' ' * 10}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 📊 PnL no realizado: {Fore.GREEN if total_unrealized_pnl >= 0 else Fore.RED}${total_unrealized_pnl:+.2f} USDT {Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 💼 Balance total: {Fore.CYAN}${total_balance:.2f} USDT {' ' * 11}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 📈 Rendimiento total: {Fore.GREEN if total_return >= 0 else Fore.RED}{total_return:+.2f}% {Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} ⏰ Tiempo de sesión: {session_time:.1f} horas {Fore.CYAN}│")
        print(f"{Fore.CYAN}└{'─' * 50}┘")
        
        print(f"{Fore.CYAN}┌{'─' * 50}┐")
        print(f"{Fore.CYAN}│{Fore.WHITE} 📊 ESTADÍSTICAS DE TRADING {' ' * 22}{Fore.CYAN}│")
        print(f"{Fore.CYAN}├{'─' * 50}┤")
        print(f"{Fore.CYAN}│{Fore.WHITE} 📈 Total trades: {stats['total_trades']} {' ' * 25}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} ✅ Trades ganadores: {stats['winning_trades']} {' ' * 21}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} ❌ Trades perdedores: {stats['losing_trades']} {' ' * 19}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 🎯 Win rate: {stats['win_rate']:.1f}% {' ' * 26}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 💰 PnL total realizado: {Fore.GREEN if stats['total_pnl'] >= 0 else Fore.RED}${stats['total_pnl']:+.2f} USDT {Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 🔓 Posiciones abiertas: {stats['open_positions']} {' ' * 19}{Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 📊 PnL no realizado: {Fore.GREEN if stats['unrealized_pnl'] >= 0 else Fore.RED}${stats['unrealized_pnl']:+.2f} USDT {Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 💎 PnL total (incl. no real.): {Fore.GREEN if stats['total_pnl_including_unrealized'] >= 0 else Fore.RED}${stats['total_pnl_including_unrealized']:+.2f} USDT {Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 📊 Ganancia promedio: {Fore.GREEN}${stats['avg_win']:.2f} USDT {Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} 📊 Pérdida promedio: {Fore.RED}${stats['avg_loss']:.2f} USDT {Fore.CYAN}│")
        print(f"{Fore.CYAN}│{Fore.WHITE} ⚖️ Factor de ganancia: {stats['profit_factor']:.2f} {Fore.CYAN}│")
        print(f"{Fore.CYAN}└{'─' * 50}┘")
        
        print(f"{Fore.CYAN}┌{'─' * 50}┐")
        print(f"{Fore.CYAN}│{Fore.WHITE} 🔓 POSICIONES ABIERTAS ({len(open_positions)}): {' ' * 15}{Fore.CYAN}│")
        print(f"{Fore.CYAN}├{'─' * 50}┤")
        if not open_positions:
            print(f"{Fore.CYAN}│{Fore.YELLOW}   No hay posiciones abiertas {' ' * 21}{Fore.CYAN}│")
        else:
            for pos in open_positions:
                print(f"{Fore.CYAN}│{Fore.WHITE}   ID: {pos.id} | {pos.symbol} {pos.side} | Entrada: ${pos.entry_price:.2f} | Actual: ${pos.current_price:.2f} {Fore.CYAN}│")
                print(f"{Fore.CYAN}│{Fore.WHITE}     PnL: ${pos.unrealized_pnl:+.2f} ({pos.unrealized_pnl_pct:+.2f}%) | Duración: {pos.duration:.1f} min {Fore.CYAN}│")
                
                # Información de protección de ganancias
                trailing_status = "🟢 ACTIVO" if pos.trailing_stop_active else "🔴 INACTIVO"
                break_even_status = "🟢 ACTIVADO" if pos.break_even_triggered else "🔴 PENDIENTE"
                partial_tp_count = len(pos.partial_tp_executed) if pos.partial_tp_executed else 0
                
                print(f"{Fore.CYAN}│{Fore.WHITE}     🎯 Trailing Stop: {trailing_status} | Break-Even: {break_even_status} {Fore.CYAN}│")
                print(f"{Fore.CYAN}│{Fore.WHITE}     📊 TPs Parciales: {partial_tp_count}/3 | SL: ${pos.stop_loss:.2f} {Fore.CYAN}│")
                
                if pos.trailing_stop_active:
                    if pos.side == "LONG":
                        print(f"{Fore.CYAN}│{Fore.WHITE}     📈 Precio máximo: ${pos.highest_price:.2f} | Distancia TS: {pos.trailing_stop_distance:.2f}% {Fore.CYAN}│")
                    else:
                        print(f"{Fore.CYAN}│{Fore.WHITE}     📉 Precio mínimo: ${pos.lowest_price:.2f} | Distancia TS: {pos.trailing_stop_distance:.2f}% {Fore.CYAN}│")
                        
                print(f"{Fore.CYAN}│{' ' * 50}{Fore.CYAN}│")  # Línea separadora
        print(f"{Fore.CYAN}└{'─' * 50}┘")
        
        print(f"{Fore.CYAN}{'='*100}\n")
            
    def print_technical_analysis(self, market_data: MarketData, signal: TradingSignal):
        """Imprimir análisis técnico detallado"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}📊 ANÁLISIS TÉCNICO DETALLADO - {market_data.symbol}")
        print(f"{Fore.CYAN}{'='*80}")
        
        # Datos básicos de mercado
        print(f"{Fore.WHITE}💰 Precio actual: {Fore.YELLOW}${market_data.price:,.4f}")
        print(f"{Fore.WHITE}📈 Cambio 24h: {Fore.GREEN if market_data.change_24h >= 0 else Fore.RED}{market_data.change_24h:+.2f}%")
        print(f"{Fore.WHITE}📊 Volumen 24h: {Fore.CYAN}{market_data.volume:,.0f}")
        print(f"{Fore.WHITE}🔺 Máximo 24h: {Fore.GREEN}${market_data.high_24h:,.4f}")
        print(f"{Fore.WHITE}🔻 Mínimo 24h: {Fore.RED}${market_data.low_24h:,.4f}")
        
        # Indicadores técnicos
        print(f"\n{Fore.MAGENTA}🔍 INDICADORES TÉCNICOS:")
        print(f"{Fore.WHITE}📊 RSI (14): {Fore.YELLOW}{market_data.indicators.rsi:.1f} {self._get_rsi_interpretation(market_data.indicators.rsi)}")
        print(f"{Fore.WHITE}📈 MACD: {Fore.CYAN}{market_data.indicators.macd:.6f}")
        print(f"{Fore.WHITE}📉 MACD Signal: {Fore.CYAN}{market_data.indicators.macd_signal:.6f}")
        print(f"{Fore.WHITE}📊 MACD Hist: {Fore.YELLOW}{market_data.indicators.macd_histogram:.6f}")
        
        # Bandas de Bollinger
        print(f"\n{Fore.BLUE}📏 BANDAS DE BOLLINGER:")
        print(f"{Fore.WHITE}🔺 Superior: {Fore.RED}${market_data.indicators.bb_upper:.4f}")
        print(f"{Fore.WHITE}➖ Media: {Fore.YELLOW}${market_data.indicators.bb_middle:.4f}")
        print(f"{Fore.WHITE}🔻 Inferior: {Fore.GREEN}${market_data.indicators.bb_lower:.4f}")
        print(f"{Fore.WHITE}📏 Ancho: {Fore.CYAN}{market_data.indicators.bb_width:.2f}%")
        
        # EMAs
        print(f"\n{Fore.GREEN}📈 MEDIAS MÓVILES:")
        print(f"{Fore.WHITE}⚡ EMA 12: {Fore.CYAN}${market_data.indicators.ema_fast:.4f}")
        print(f"{Fore.WHITE}🐌 EMA 26: {Fore.CYAN}${market_data.indicators.ema_slow:.4f}")
        
        # Momentum y Volatilidad
        print(f"\n{Fore.RED}⚡ MOMENTUM Y VOLATILIDAD:")
        print(f"{Fore.WHITE}🚀 Cambio 1h: {Fore.GREEN if market_data.indicators.price_change_1h >= 0 else Fore.RED}{market_data.indicators.price_change_1h:+.2f}%")
        print(f"{Fore.WHITE}🚀 Cambio 4h: {Fore.GREEN if market_data.indicators.price_change_4h >= 0 else Fore.RED}{market_data.indicators.price_change_4h:+.2f}%")
        print(f"{Fore.WHITE}💥 Volatilidad: {Fore.YELLOW}{market_data.indicators.volatility:.2f}%")
        print(f"{Fore.WHITE}⚡ Momentum: {Fore.CYAN}{market_data.indicators.momentum:.2f}")
        
        # Análisis de señal
        print(f"\n{Fore.YELLOW}🎯 ANÁLISIS DE SEÑAL:")
        print(f"{Fore.WHITE}📊 Score Técnico: {Fore.CYAN}{signal.technical_score:.3f}")
        print(f"{Fore.WHITE}⚡ Score Momentum: {Fore.CYAN}{signal.momentum_score:.3f}")
        print(f"{Fore.WHITE}💥 Score Volatilidad: {Fore.CYAN}{signal.volatility_score:.3f}")
        
        # Señal generada
        action_color = Fore.GREEN if signal.action == "BUY" else Fore.RED if signal.action == "SELL" else Fore.YELLOW
        strength_emoji = "🔥" if signal.strength == "ULTRA" else "💪" if signal.strength == "STRONG" else "👍" if signal.strength == "MEDIUM" else "😴"
        
        print(f"\n{Fore.MAGENTA}🎯 SEÑAL GENERADA:")
        print(f"{Fore.WHITE}🎬 Acción: {action_color}{signal.action} {strength_emoji}")
        print(f"{Fore.WHITE}💯 Confianza: {Fore.CYAN}{signal.confidence:.1%}")
        print(f"{Fore.WHITE}💪 Fuerza: {Fore.YELLOW}{signal.strength}")
        print(f"{Fore.WHITE}🧠 Razón: {Fore.WHITE}{signal.reason}")
        
        if signal.action != "HOLD":
            print(f"\n{Fore.GREEN}💰 NIVELES DE TRADING:")
            print(f"{Fore.WHITE}🎯 Entrada: {Fore.YELLOW}${signal.entry_price:.4f}")
            print(f"{Fore.WHITE}🛑 Stop Loss: {Fore.RED}${signal.stop_loss:.4f}")
            print(f"{Fore.WHITE}🎯 TP1: {Fore.GREEN}${signal.take_profit_1:.4f}")
            print(f"{Fore.WHITE}🎯 TP2: {Fore.GREEN}${signal.take_profit_2:.4f}")
            print(f"{Fore.WHITE}🎯 TP3: {Fore.GREEN}${signal.take_profit_3:.4f}")
            print(f"{Fore.WHITE}📊 Tamaño: {Fore.CYAN}${signal.position_size:.2f}")
            print(f"{Fore.WHITE}⚡ Apalancamiento: {Fore.YELLOW}{signal.leverage}x")
            print(f"{Fore.WHITE}📈 Risk/Reward: {Fore.CYAN}{signal.risk_reward:.2f}")
        
        print(f"{Fore.CYAN}{'='*80}\n")
        
    def _get_rsi_interpretation(self, rsi: float) -> str:
        """Obtener interpretación del RSI"""
        if rsi <= 20:
            return f"{Fore.GREEN}(MUY OVERSOLD - COMPRA FUERTE)"
        elif rsi <= 30:
            return f"{Fore.GREEN}(OVERSOLD - COMPRA)"
        elif rsi >= 80:
            return f"{Fore.RED}(MUY OVERBOUGHT - VENTA FUERTE)"
        elif rsi >= 70:
            return f"{Fore.RED}(OVERBOUGHT - VENTA)"
        elif rsi >= 60:
            return f"{Fore.YELLOW}(ALCISTA)"
        elif rsi <= 40:
            return f"{Fore.YELLOW}(BAJISTA)"
        else:
            return f"{Fore.WHITE}(NEUTRAL)"
            
    def print_header(self):
        """Imprimir header del simulador"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*100}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🚀 SIMULADOR V4 ULTRA-AGRESIVO CON GESTIÓN DE POSICIONES")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*100}")
        print(f"{Fore.WHITE}💰 Capital inicial: {Fore.GREEN}${self.strategy.initial_capital:.2f} USDT")
        print(f"{Fore.WHITE}⚡ Apalancamiento: {Fore.YELLOW}{self.strategy.leverage}x")
        print(f"{Fore.WHITE}🎯 Objetivo mensual: {Fore.GREEN}15%")
        print(f"{Fore.WHITE}🔄 Actualización: {Fore.CYAN}cada 5s")
        print(f"{Fore.WHITE}📊 Pares: {Fore.MAGENTA}{', '.join(self.symbols)}")
        print(f"{Fore.WHITE}⏰ Hora: {Fore.YELLOW}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*100}\n")
        
    def print_market_dashboard(self, market_data_dict: Dict[str, MarketData]):
        """Imprimir dashboard de mercado con tabla de símbolos"""
        print(f"{Fore.CYAN}┌{'─' * 100}┐")
        print(f"{Fore.CYAN}│{Fore.WHITE} 📊 DASHBOARD DE MERCADO EN TIEMPO REAL {' ' * 50}{Fore.CYAN}│")
        print(f"{Fore.CYAN}├{'─' * 100}┤")
        print(f"{Fore.CYAN}│{Fore.WHITE} Símbolo   | Precio     | 24h %     | RSI    | MACD      | Señal     | Fuerza    | Confianza {Fore.CYAN}│")
        print(f"{Fore.CYAN}├{'─' * 100}┤")
        
        for symbol, data in market_data_dict.items():
            # Generar señal para cada símbolo (asumiendo que analyze_market_data está disponible)
            signal = self.strategy.analyze_market_data(data)
            action_color = Fore.GREEN if signal.action == 'BUY' else Fore.RED if signal.action == 'SELL' else Fore.YELLOW
            print(f"{Fore.CYAN}│{Fore.WHITE} {symbol:<10} | {data.price:>10.2f} | {data.change_24h:>8.2f}% | {data.indicators.rsi:>6.1f} | {data.indicators.macd:>9.4f} | {action_color}{signal.action:<9}{Fore.WHITE} | {signal.strength:<9} | {signal.confidence:>9.1%} {Fore.CYAN}│")
        
        print(f"{Fore.CYAN}└{'─' * 100}┘\n")
    
    async def run_simulation(self):
        """Ejecutar simulación principal"""
        self.running = True
        logger.info("Iniciando simulación V4 Ultra-Agresiva con gestión de posiciones...")
        logger.info("Conectando a Binance API...")
        
        while self.running:
            try:
                self.print_header()
                self.print_portfolio_status()
                
                # Obtener datos de mercado para todos los símbolos
                market_data_dict = {}
                for symbol in self.symbols:
                    market_data = self.get_market_data(symbol)
                    if market_data:
                        market_data_dict[symbol] = market_data
                
                # Imprimir dashboard de mercado
                self.print_market_dashboard(market_data_dict)
                
                # Actualizar posiciones existentes
                self.strategy.position_manager.update_positions(market_data_dict)
                
                # Verificar condiciones de salida
                executed_trades = self.strategy.position_manager.check_exit_conditions(market_data_dict)
                
                # Procesar trades ejecutados
                for trade in executed_trades:
                    self.strategy.update_capital(trade.pnl)
                    print(f"{Fore.GREEN}✅ Trade cerrado: {trade.symbol} {trade.side} | "
                          f"PnL: ${trade.pnl:+.2f} ({trade.pnl_pct:+.2f}%) | "
                          f"Razón: {trade.exit_reason}")
                
                # Analizar cada símbolo para nuevas señales
                for symbol in self.symbols:
                    if symbol not in market_data_dict:
                        continue
                        
                    print(f"{Fore.BLUE}🔍 Analizando {symbol}...")
                    
                    market_data = market_data_dict[symbol]
                    signal = self.strategy.analyze_market_data(market_data)
                    self.print_technical_analysis(market_data, signal)
                    
                    # Ejecutar señal si cumple criterios
                    available_capital = self.strategy.get_available_capital()
                    print(f"🔍 DEBUG - Señal: {signal.action}, Confianza: {signal.confidence:.1%}, Capital disponible: ${available_capital:.2f}")
                    
                    position = None  # Inicializar position
                    
                    if signal.action != "HOLD":
                        print(f"✅ Acción válida: {signal.action}")
                        
                        # Verificar si ya existe una posición abierta para este símbolo
                        existing_positions = [pos for pos in self.strategy.position_manager.get_open_positions() 
                                            if pos.symbol == symbol and pos.status == "OPEN"]
                        
                        if existing_positions:
                            print(f"❌ Ya existe posición abierta para {symbol} - Saltando")
                        elif signal.confidence >= self.strategy.min_confidence:
                            print(f"✅ Confianza suficiente: {signal.confidence:.1%} >= {self.strategy.min_confidence:.1%}")
                            if available_capital > 50:
                                print(f"✅ Capital suficiente: ${available_capital:.2f} > $50")
                                print(f"🚀 INTENTANDO ABRIR POSICIÓN...")
                                
                                position = self.strategy.position_manager.open_position(
                                    signal, market_data.price, available_capital
                                )
                            else:
                                print(f"❌ Capital insuficiente: ${available_capital:.2f} <= $50")
                        else:
                            print(f"❌ Confianza insuficiente: {signal.confidence:.1%} < {self.strategy.min_confidence:.1%}")
                    else:
                        print(f"⏸️ Señal HOLD - No se ejecuta trade")
                        
                    if position:
                        self.signals_generated += 1
                        print(f"{Fore.GREEN}🚀 POSICIÓN ABIERTA: {position.symbol} {position.side} | "
                              f"Entrada: ${position.entry_price:.4f} | "
                              f"Cantidad: ${position.quantity:.2f} | "
                              f"Margen: ${position.margin_used:.2f}")
                    else:
                        if signal.action != "HOLD" and signal.confidence >= self.strategy.min_confidence:
                            print(f"{Fore.YELLOW}⚠️ No se pudo abrir posición para {symbol} (revisar logs de debug)")
                    
                    await asyncio.sleep(1)  # Pausa entre símbolos
                
                print(f"{Fore.CYAN}⏳ Esperando próximo ciclo de análisis...\n")
                await asyncio.sleep(5)  # Pausa entre ciclos
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}⏹️ Simulación detenida por el usuario")
                self.running = False
            except Exception as e:
                logger.exception(f"Error en simulación: {e}")
                await asyncio.sleep(5)
                time.sleep(5)  # Retraso para visualizar el dashboard

if __name__ == "__main__":
    simulator = LiveTradingSimulatorV4()
    
    try:
        asyncio.run(simulator.run_simulation())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Simulación finalizada")