#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard V4 Ultra-Agresivo en Consola
Estrategia de Trading con Datos Reales de Binance
Objetivo: 15% mensual con apalancamiento 3x
Formato: Dashboard visual en consola
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
import shutil

# Inicializar colorama para Windows
init(autoreset=True)

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
    """Posición abierta"""
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
            print(f"❌ Error obteniendo ticker {symbol}: {e}")
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
            print(f"❌ Error obteniendo klines {symbol}: {e}")
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
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.position_counter = 0
        self.trade_counter = 0
        
    def open_position(self, signal: TradingSignal, current_price: float, capital: float) -> Optional[Position]:
        """Abrir nueva posición"""
        self.position_counter += 1
        position_id = f"POS_{self.position_counter:04d}"
        
        # Calcular cantidad basada en el capital disponible
        margin_used = signal.position_size / signal.leverage
        
        if margin_used > capital * 0.8:  # No usar más del 80% del capital
            return None
            
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
            status="OPEN"
        )
        
        self.positions[position_id] = position
        return position
        
    def update_positions(self, market_data: Dict[str, MarketData]):
        """Actualizar posiciones con precios actuales"""
        for position in self.positions.values():
            if position.status == "OPEN" and position.symbol in market_data:
                current_price = market_data[position.symbol].price
                position.current_price = current_price
                
                # Calcular PnL no realizado
                if position.side == "LONG":
                    price_diff = current_price - position.entry_price
                else:  # SHORT
                    price_diff = position.entry_price - current_price
                    
                position.unrealized_pnl = (price_diff / position.entry_price) * position.quantity
                position.unrealized_pnl_pct = (price_diff / position.entry_price) * 100
                
    def check_exit_conditions(self, market_data: Dict[str, MarketData]) -> List[Trade]:
        """Verificar condiciones de salida"""
        executed_trades = []
        
        for position in list(self.positions.values()):
            if position.status != "OPEN" or position.symbol not in market_data:
                continue
                
            current_price = market_data[position.symbol].price
            exit_reason = None
            
            # Verificar Stop Loss
            if position.side == "LONG" and current_price <= position.stop_loss:
                exit_reason = "SL"
            elif position.side == "SHORT" and current_price >= position.stop_loss:
                exit_reason = "SL"
                
            # Verificar Take Profits
            elif position.side == "LONG":
                if current_price >= position.take_profit_3:
                    exit_reason = "TP3"
                elif current_price >= position.take_profit_2:
                    exit_reason = "TP2"
                elif current_price >= position.take_profit_1:
                    exit_reason = "TP1"
            else:  # SHORT
                if current_price <= position.take_profit_3:
                    exit_reason = "TP3"
                elif current_price <= position.take_profit_2:
                    exit_reason = "TP2"
                elif current_price <= position.take_profit_1:
                    exit_reason = "TP1"
                    
            if exit_reason:
                trade = self.close_position(position, current_price, exit_reason)
                if trade:
                    executed_trades.append(trade)
                    
        return executed_trades
        
    def close_position(self, position: Position, exit_price: float, exit_reason: str) -> Optional[Trade]:
        """Cerrar posición"""
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
        
        # Remover posición de las activas
        if position.id in self.positions:
            del self.positions[position.id]
            
        return trade
        
    def get_open_positions(self) -> List[Position]:
        """Obtener posiciones abiertas"""
        return [pos for pos in self.positions.values() if pos.status == "OPEN"]
        
    def get_total_unrealized_pnl(self) -> float:
        """Obtener PnL total no realizado"""
        return sum(pos.unrealized_pnl for pos in self.get_open_positions())
        
    def get_total_margin_used(self) -> float:
        """Obtener margen total usado"""
        return sum(pos.margin_used for pos in self.get_open_positions())
        
    def get_trading_stats(self) -> Dict:
        """Obtener estadísticas de trading"""
        if not self.trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0
            }
            
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
            "profit_factor": total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
        }

from live_trading_simulator_v4_ultra_technical import UltraAggressiveStrategyV4
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
        macd_score = self._calculate_macd_score(indicators.macd, indicators.macd_signal)
        bb_score = self._calculate_bb_score(market_data.price, indicators.bb_upper, 
                                          indicators.bb_middle, indicators.bb_lower)
        momentum_score = self._calculate_momentum_score(indicators.momentum)
        volatility_score = self._calculate_volatility_score(indicators.volatility)
        volume_score = self._calculate_volume_score(market_data.volume, indicators.volume_sma)
        
        # Score técnico combinado
        technical_score = (rsi_score * 0.25 + macd_score * 0.25 + bb_score * 0.20 + 
                          momentum_score * 0.15 + volatility_score * 0.10 + volume_score * 0.05)
        
        # Determinar acción y confianza (más agresivo)
        action, confidence, strength = self._determine_action(technical_score, indicators)
        
        # Hacer más agresivo: reducir umbrales
        if action == "HOLD" and abs(technical_score) > 0.15:
            if technical_score > 0:
                action = "BUY"
                strength = "MEDIUM"
            else:
                action = "SELL"
                strength = "MEDIUM"
            confidence = abs(technical_score)
        
        # Calcular precios de entrada y salida
        entry_price = market_data.price
        stop_loss, tp1, tp2, tp3 = self._calculate_levels(entry_price, action, indicators.volatility)
        
        # Calcular tamaño de posición
        position_size = self._calculate_position_size(entry_price, stop_loss)
        
        # Razón de la señal
        reason = self._generate_reason(rsi_score, macd_score, bb_score, momentum_score)
        
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
        """Determinar acción basada en score técnico (más agresivo)"""
        confidence = abs(technical_score)
        
        if technical_score >= 0.6:
            return "BUY", confidence, "ULTRA"
        elif technical_score >= 0.4:
            return "BUY", confidence, "STRONG"
        elif technical_score >= 0.2:
            return "BUY", confidence, "MEDIUM"
        elif technical_score <= -0.6:
            return "SELL", confidence, "ULTRA"
        elif technical_score <= -0.4:
            return "SELL", confidence, "STRONG"
        elif technical_score <= -0.2:
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

class DashboardRenderer:
    """Renderizador de dashboard en consola"""
    
    def __init__(self):
        self.terminal_width = shutil.get_terminal_size().columns
        self.terminal_height = shutil.get_terminal_size().lines
        
    def clear_screen(self):
        """Limpiar pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def create_box(self, title: str, content: List[str], width: int = 50, color: str = Fore.CYAN) -> List[str]:
        """Crear caja con contenido"""
        lines = []
        
        # Línea superior
        lines.append(f"{color}┌{'─' * (width - 2)}┐")
        
        # Título
        title_line = f"│ {title:<{width - 4}} │"
        lines.append(f"{color}{title_line}")
        lines.append(f"{color}├{'─' * (width - 2)}┤")
        
        # Contenido
        for line in content:
            if len(line) > width - 4:
                line = line[:width - 7] + "..."
            content_line = f"│ {line:<{width - 4}} │"
            lines.append(f"{color}{content_line}")
        
        # Línea inferior
        lines.append(f"{color}└{'─' * (width - 2)}┘")
        
        return lines
        
    def render_portfolio_panel(self, strategy) -> List[str]:
        """Renderizar panel de portfolio"""
        open_positions = strategy.position_manager.get_open_positions()
        total_unrealized_pnl = strategy.position_manager.get_total_unrealized_pnl()
        total_margin_used = strategy.position_manager.get_total_margin_used()
        available_capital = strategy.get_available_capital()
        stats = strategy.position_manager.get_trading_stats()
        
        # Calcular rendimiento total
        total_balance = strategy.current_capital + total_unrealized_pnl
        total_return = ((total_balance - strategy.initial_capital) / strategy.initial_capital) * 100
        
        content = [
            f"💰 Capital Inicial: ${strategy.initial_capital:.2f}",
            f"💰 Capital Actual: ${strategy.current_capital:.2f}",
            f"💰 Disponible: ${available_capital:.2f}",
            f"🔒 Margen Usado: ${total_margin_used:.2f}",
            f"📊 PnL No Real.: {'+' if total_unrealized_pnl >= 0 else ''}${total_unrealized_pnl:.2f}",
            f"💼 Balance Total: ${total_balance:.2f}",
            f"📈 Rendimiento: {'+' if total_return >= 0 else ''}{total_return:.2f}%",
            "",
            f"📈 Trades: {stats['total_trades']}",
            f"✅ Ganadores: {stats['winning_trades']}",
            f"❌ Perdedores: {stats['losing_trades']}",
            f"🎯 Win Rate: {stats['win_rate']:.1f}%",
            f"💰 PnL Real.: {'+' if stats['total_pnl'] >= 0 else ''}${stats['total_pnl']:.2f}",
            f"⚖️ Factor Gan.: {stats['profit_factor']:.2f}"
        ]
        
        return self.create_box("💼 PORTFOLIO", content, 35, Fore.CYAN)
        
    def render_positions_panel(self, strategy) -> List[str]:
        """Renderizar panel de posiciones"""
        open_positions = strategy.position_manager.get_open_positions()
        
        content = []
        if open_positions:
            for i, pos in enumerate(open_positions[:5]):  # Máximo 5 posiciones
                side_emoji = "🟢" if pos.side == "LONG" else "🔴"
                duration = datetime.now() - pos.entry_time
                duration_str = f"{duration.total_seconds()/60:.0f}m"
                
                content.append(f"{side_emoji} {pos.symbol} {pos.side}")
                content.append(f"   Entrada: ${pos.entry_price:.4f}")
                content.append(f"   Actual: ${pos.current_price:.4f}")
                content.append(f"   PnL: {'+' if pos.unrealized_pnl >= 0 else ''}${pos.unrealized_pnl:.2f}")
                content.append(f"   Duración: {duration_str}")
                if i < len(open_positions) - 1:
                    content.append("")
        else:
            content = ["No hay posiciones abiertas"]
            
        return self.create_box(f"🔓 POSICIONES ({len(open_positions)})", content, 35, Fore.YELLOW)
        
    def render_market_panel(self, market_data_dict: Dict[str, MarketData]) -> List[str]:
        """Renderizar panel de mercado"""
        content = []
        
        for symbol, data in list(market_data_dict.items())[:5]:  # Máximo 5 símbolos
            change_color = "+" if data.change_24h >= 0 else ""
            content.append(f"📊 {symbol}")
            content.append(f"   ${data.price:,.4f}")
            content.append(f"   {change_color}{data.change_24h:.2f}%")
            content.append(f"   RSI: {data.indicators.rsi:.1f}")
            content.append("")
            
        return self.create_box("📊 MERCADO", content, 25, Fore.GREEN)
        
    def render_signals_panel(self, signals: Dict[str, TradingSignal]) -> List[str]:
        """Renderizar panel de señales"""
        content = []
        
        for symbol, signal in list(signals.items())[:5]:  # Máximo 5 señales
            action_emoji = "🟢" if signal.action == "BUY" else "🔴" if signal.action == "SELL" else "⚪"
            strength_emoji = "🔥" if signal.strength == "ULTRA" else "💪" if signal.strength == "STRONG" else "👍" if signal.strength == "MEDIUM" else "😴"
            
            content.append(f"{action_emoji} {symbol}")
            content.append(f"   {signal.action} {strength_emoji}")
            content.append(f"   Conf: {signal.confidence:.1%}")
            content.append(f"   Score: {signal.technical_score:.3f}")
            content.append("")
            
        return self.create_box(f"🎯 SEÑALES", content, 30, Fore.MAGENTA)
        
    def render_technical_panel(self, symbol: str, market_data: MarketData) -> List[str]:
        """Renderizar panel técnico detallado"""
        indicators = market_data.indicators
        
        content = [
            f"💰 Precio: ${market_data.price:,.4f}",
            f"📈 24h: {'+' if market_data.change_24h >= 0 else ''}{market_data.change_24h:.2f}%",
            f"📊 Volumen: {market_data.volume:,.0f}",
            "",
            f"📊 RSI: {indicators.rsi:.1f}",
            f"📈 MACD: {indicators.macd:.6f}",
            f"📏 BB Width: {indicators.bb_width:.2f}%",
            f"⚡ EMA12: ${indicators.ema_fast:.4f}",
            f"🐌 EMA26: ${indicators.ema_slow:.4f}",
            "",
            f"🚀 1h: {'+' if indicators.price_change_1h >= 0 else ''}{indicators.price_change_1h:.2f}%",
            f"🚀 4h: {'+' if indicators.price_change_4h >= 0 else ''}{indicators.price_change_4h:.2f}%",
            f"💥 Volatilidad: {indicators.volatility:.2f}%",
            f"⚡ Momentum: {indicators.momentum:.2f}"
        ]
        
        return self.create_box(f"🔍 {symbol}", content, 35, Fore.BLUE)
        
    def render_dashboard(self, strategy, market_data_dict: Dict[str, MarketData], signals: Dict[str, TradingSignal], selected_symbol: str = None):
        """Renderizar dashboard completo"""
        self.clear_screen()
        
        # Header
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*self.terminal_width}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🚀 DASHBOARD V4 ULTRA-AGRESIVO - {now}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*self.terminal_width}")
        print()
        
        # Fila 1: Portfolio + Posiciones + Mercado
        portfolio_lines = self.render_portfolio_panel(strategy)
        positions_lines = self.render_positions_panel(strategy)
        market_lines = self.render_market_panel(market_data_dict)
        
        max_lines = max(len(portfolio_lines), len(positions_lines), len(market_lines))
        
        for i in range(max_lines):
            line = ""
            if i < len(portfolio_lines):
                line += portfolio_lines[i]
            else:
                line += " " * 35
            
            line += "  "  # Espaciado
            
            if i < len(positions_lines):
                line += positions_lines[i]
            else:
                line += " " * 35
                
            line += "  "  # Espaciado
            
            if i < len(market_lines):
                line += market_lines[i]
            
            print(line)
        
        print()
        
        # Fila 2: Señales + Análisis Técnico
        signals_lines = self.render_signals_panel(signals)
        
        # Seleccionar símbolo para análisis técnico detallado
        if not selected_symbol and market_data_dict:
            selected_symbol = list(market_data_dict.keys())[0]
            
        technical_lines = []
        if selected_symbol and selected_symbol in market_data_dict:
            technical_lines = self.render_technical_panel(selected_symbol, market_data_dict[selected_symbol])
        
        max_lines = max(len(signals_lines), len(technical_lines))
        
        for i in range(max_lines):
            line = ""
            if i < len(signals_lines):
                line += signals_lines[i]
            else:
                line += " " * 25
            
            line += "  "  # Espaciado
            
            if i < len(technical_lines):
                line += technical_lines[i]
            
            print(line)
        
        print()
        
        # Mostrar información de debug de señales
        if hasattr(self, 'signal_debug_info') and self.signal_debug_info:
            print(f"{Fore.YELLOW}🔍 DEBUG SEÑALES:")
            for debug_msg in self.signal_debug_info[-5:]:  # Últimas 5
                print(f"{Fore.YELLOW}   {debug_msg}")
            print()
        
        print(f"{Fore.CYAN}⏳ Próxima actualización en 5 segundos...")

class LiveTradingDashboardV4:
    """Dashboard de trading en vivo V4"""
    
    def __init__(self):
        self.data_provider = BinanceRealDataProvider()
        self.strategy = UltraAggressiveStrategyV4()
        self.renderer = DashboardRenderer()
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
        self.running = False
        self.signals_generated = 0
        self.start_time = datetime.now()
        self.current_symbol_index = 0
        
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
            
    async def run_dashboard(self):
        """Ejecutar dashboard principal"""
        self.running = True
        print(f"{Fore.GREEN}🚀 Iniciando Dashboard V4 Ultra-Agresivo...")
        print(f"{Fore.CYAN}📡 Conectando a Binance API...\n")
        
        while self.running:
            try:
                # Obtener datos de mercado para todos los símbolos
                market_data_dict = {}
                signals = {}
                
                for symbol in self.symbols:
                    market_data = self.get_market_data(symbol)
                    if market_data:
                        market_data_dict[symbol] = market_data
                        signals[symbol] = self.strategy.analyze_market_data(market_data)
                
                # Actualizar posiciones existentes
                self.strategy.position_manager.update_positions(market_data_dict)
                
                # Verificar condiciones de salida
                executed_trades = self.strategy.position_manager.check_exit_conditions(market_data_dict)
                
                # Procesar trades ejecutados
                for trade in executed_trades:
                    self.strategy.update_capital(trade.pnl)
                
                # Ejecutar nuevas señales
                signal_debug_info = []
                for symbol, signal in signals.items():
                    debug_msg = f"{symbol}: {signal.action} conf={signal.confidence:.3f}"
                    
                    if signal.action == "HOLD":
                        debug_msg += " (HOLD - no action)"
                    elif signal.confidence < self.strategy.min_confidence:
                        debug_msg += f" (conf < {self.strategy.min_confidence:.2f})"
                    elif self.strategy.get_available_capital() <= 50:
                        debug_msg += " (capital insuficiente)"
                    else:
                        position = self.strategy.position_manager.open_position(
                            signal, market_data_dict[symbol].price, self.strategy.get_available_capital()
                        )
                        
                        if position:
                            self.signals_generated += 1
                            debug_msg += " ✅ EJECUTADA"
                        else:
                            debug_msg += " ❌ FALLÓ"
                    
                    signal_debug_info.append(debug_msg)
                
                # Renderizar dashboard
                selected_symbol = self.symbols[self.current_symbol_index % len(self.symbols)]
                self.renderer.signal_debug_info = signal_debug_info  # Pasar info de debug
                self.renderer.render_dashboard(self.strategy, market_data_dict, signals, selected_symbol)
                
                # Rotar símbolo para análisis técnico detallado
                self.current_symbol_index += 1
                
                await asyncio.sleep(5)  # Actualizar cada 5 segundos
                
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}⏹️ Dashboard detenido por el usuario")
                self.running = False
            except Exception as e:
                print(f"{Fore.RED}❌ Error en dashboard: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    dashboard = LiveTradingDashboardV4()
    
    try:
        asyncio.run(dashboard.run_dashboard())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Dashboard finalizado")