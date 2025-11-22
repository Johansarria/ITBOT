#!/usr/bin/env python3
"""
SICAR - Sistema de Capital Variable REALISTA v3.0
Sistema de trading con capital variable entre 200-500 USDT y reinversión automática
Versión realista con frecuencia de trading apropiada
"""

import numpy as np
import pandas as pd
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import random

class SicarCapitalVariableRealista:
    def __init__(self, initial_capital: float = 200.0):
        """
        Inicializa el sistema SICAR con capital variable - Versión Realista
        
        Args:
            initial_capital: Capital inicial en USDT (mínimo 200)
        """
        self.initial_capital = max(initial_capital, 200.0)
        self.current_capital = self.initial_capital
        self.base_capital = self.initial_capital
        self.max_capital = 500.0
        self.min_capital = 200.0
        
        # Configuración de trading REALISTA
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT']
        self.reinvestment_threshold = 0.05  # 5% ROI para reinvertir
        self.max_position_size = 0.20  # 20% del capital por posición (más conservador)
        self.min_position_size = 0.08  # 8% del capital por posición
        
        # CONFIGURACIÓN REALISTA DE FRECUENCIA
        self.min_time_between_trades = 15  # Mínimo 15 minutos entre trades del mismo símbolo
        self.min_confidence_threshold = 0.75  # Mayor confianza requerida
        self.max_daily_trades = 8  # Máximo 8 trades por día
        self.max_positions_simultaneous = 2  # Máximo 2 posiciones abiertas
        
        # Costos realistas
        self.trading_fee = 0.001  # 0.1% comisión por trade (Binance)
        self.slippage = 0.0005  # 0.05% slippage promedio
        
        # Tracking
        self.trades = []
        self.positions = {}
        self.total_pnl = 0.0
        self.total_reinvested = 0.0
        self.cycles_completed = 0
        self.last_trade_time = {}  # Tiempo del último trade por símbolo
        self.daily_trades_count = 0
        self.session_start_time = datetime.now()
        
        # Configuración de indicadores
        self.sma_period = 20  # Períodos más largos para mayor estabilidad
        self.rsi_period = 14
        self.bb_period = 20
        self.bb_std = 2.0
        
        print(f"🚀 SICAR Capital Variable REALISTA v3.0 iniciado")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        print(f"📊 Símbolos: {', '.join(self.symbols)}")
        print(f"🔄 Umbral de reinversión: {self.reinvestment_threshold*100}%")
        print(f"⏱️ Tiempo mínimo entre trades: {self.min_time_between_trades} min")
        print(f"🎯 Confianza mínima: {self.min_confidence_threshold*100}%")
        print(f"📈 Máximo trades diarios: {self.max_daily_trades}")

    def generate_market_data(self, symbol: str, periods: int = 100) -> pd.DataFrame:
        """
        Genera datos de mercado simulados más realistas
        
        Args:
            symbol: Símbolo del par de trading
            periods: Número de períodos a generar
            
        Returns:
            DataFrame con datos OHLCV
        """
        # Precios base por símbolo (más actualizados)
        base_prices = {
            'BTCUSDT': 67000,
            'ETHUSDT': 2600,
            'ADAUSDT': 0.38,
            'DOTUSDT': 4.2
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generar datos con tendencia y volatilidad más realista
        timestamps = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        current_time = datetime.now()
        current_price = base_price
        
        for i in range(periods):
            # Timestamp (intervalos de 5 minutos)
            timestamps.append(current_time - timedelta(minutes=(periods-i)*5))
            
            # Precio de apertura
            open_price = current_price
            opens.append(open_price)
            
            # Volatilidad más realista (0.2% - 1.5%)
            volatility = random.uniform(0.002, 0.015)
            price_change = random.gauss(0, volatility)
            
            # Tendencia más sutil
            trend = random.uniform(-0.001, 0.001)
            close_price = open_price * (1 + price_change + trend)
            closes.append(close_price)
            
            # High y Low más realistas
            high_price = max(open_price, close_price) * random.uniform(1.0005, 1.008)
            low_price = min(open_price, close_price) * random.uniform(0.992, 0.9995)
            highs.append(high_price)
            lows.append(low_price)
            
            # Volumen más estable
            base_volume = random.uniform(500000, 2000000)
            volumes.append(base_volume)
            
            current_price = close_price
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        return df

    def calculate_sma(self, prices: List[float], period: int) -> float:
        """Calcula Simple Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcula Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Valor neutral
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]
        
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float]:
        """Calcula Bollinger Bands"""
        if len(prices) < period:
            price = prices[-1] if prices else 0
            return price, price, price
        
        recent_prices = prices[-period:]
        sma = sum(recent_prices) / period
        variance = sum((p - sma) ** 2 for p in recent_prices) / period
        std = variance ** 0.5
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return upper_band, sma, lower_band

    def calculate_volatility(self, prices: List[float], period: int = 20) -> float:
        """Calcula volatilidad como desviación estándar de retornos"""
        if len(prices) < period + 1:
            return 0.01  # Volatilidad por defecto más baja
        
        returns = [(prices[i] / prices[i-1] - 1) for i in range(-period, 0)]
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return variance ** 0.5

    def can_trade_symbol(self, symbol: str) -> bool:
        """
        Verifica si se puede hacer trading en un símbolo específico
        
        Args:
            symbol: Símbolo a verificar
            
        Returns:
            True si se puede tradear
        """
        current_time = datetime.now()
        
        # Verificar tiempo mínimo entre trades
        if symbol in self.last_trade_time:
            time_diff = (current_time - self.last_trade_time[symbol]).total_seconds() / 60
            if time_diff < self.min_time_between_trades:
                return False
        
        # Verificar límite diario de trades
        if self.daily_trades_count >= self.max_daily_trades:
            return False
        
        # Verificar máximo de posiciones simultáneas
        if len(self.positions) >= self.max_positions_simultaneous:
            return False
        
        # Verificar si ya hay posición abierta en este símbolo
        if symbol in self.positions:
            return False
        
        return True

    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Genera señales de trading más conservadoras y realistas
        
        Args:
            df: DataFrame con datos de mercado
            symbol: Símbolo del par
            
        Returns:
            Diccionario con información de la señal
        """
        if len(df) < 50:  # Necesitamos más datos para análisis robusto
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': 'Datos insuficientes'}
        
        prices = df['close'].tolist()
        volumes = df['volume'].tolist()
        current_price = prices[-1]
        
        # Calcular indicadores con períodos más largos
        sma_20 = self.calculate_sma(prices, 20)
        sma_50 = self.calculate_sma(prices, 50)
        rsi = self.calculate_rsi(prices, 14)
        upper_bb, middle_bb, lower_bb = self.calculate_bollinger_bands(prices, 20)
        volatility = self.calculate_volatility(prices, 20)
        
        # Análisis de volumen más sofisticado
        avg_volume_20 = sum(volumes[-20:]) / 20
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1.0
        
        # Sistema de puntuación más estricto
        score = 0
        reasons = []
        
        # 1. Análisis de tendencia (SMA) - Más peso
        if current_price > sma_20 > sma_50:
            score += 3
            reasons.append("Tendencia alcista fuerte (SMA 20>50)")
        elif current_price < sma_20 < sma_50:
            score -= 3
            reasons.append("Tendencia bajista fuerte (SMA 20<50)")
        elif current_price > sma_20:
            score += 1
            reasons.append("Precio sobre SMA 20")
        elif current_price < sma_20:
            score -= 1
            reasons.append("Precio bajo SMA 20")
        
        # 2. Análisis RSI más estricto
        if rsi < 25:  # Sobreventa extrema
            score += 3
            reasons.append(f"RSI sobreventa extrema ({rsi:.1f})")
        elif rsi > 75:  # Sobrecompra extrema
            score -= 3
            reasons.append(f"RSI sobrecompra extrema ({rsi:.1f})")
        elif 30 <= rsi <= 70:  # Zona neutral
            score += 1
            reasons.append("RSI en zona neutral")
        
        # 3. Bollinger Bands
        bb_position = (current_price - lower_bb) / (upper_bb - lower_bb)
        if bb_position <= 0.1:  # Muy cerca de banda inferior
            score += 2
            reasons.append("Precio en banda inferior BB")
        elif bb_position >= 0.9:  # Muy cerca de banda superior
            score -= 2
            reasons.append("Precio en banda superior BB")
        
        # 4. Análisis de volumen más estricto
        if volume_ratio > 2.0:  # Volumen muy alto
            score += 2
            reasons.append(f"Volumen muy alto ({volume_ratio:.1f}x)")
        elif volume_ratio < 0.3:  # Volumen muy bajo
            score -= 1
            reasons.append(f"Volumen muy bajo ({volume_ratio:.1f}x)")
        
        # 5. Control de volatilidad
        if volatility > 0.03:  # Volatilidad muy alta
            score -= 2
            reasons.append("Volatilidad muy alta - riesgo")
        elif volatility < 0.005:  # Volatilidad muy baja
            score -= 1
            reasons.append("Volatilidad muy baja - sin momentum")
        
        # Determinar acción con umbrales más altos
        confidence = min(abs(score) / 8.0, 1.0)  # Normalizar a 0-1
        
        if score >= 5 and confidence >= self.min_confidence_threshold:
            action = 'BUY'
        elif score <= -5 and confidence >= self.min_confidence_threshold:
            action = 'SELL'
        else:
            action = 'HOLD'
        
        return {
            'action': action,
            'confidence': confidence,
            'score': score,
            'reason': '; '.join(reasons),
            'indicators': {
                'price': current_price,
                'sma_20': sma_20,
                'sma_50': sma_50,
                'rsi': rsi,
                'bb_upper': upper_bb,
                'bb_lower': lower_bb,
                'volatility': volatility,
                'volume_ratio': volume_ratio
            }
        }

    def calculate_position_size(self, signal: Dict, symbol: str) -> float:
        """
        Calcula el tamaño de posición más conservador
        
        Args:
            signal: Señal de trading
            symbol: Símbolo del par
            
        Returns:
            Tamaño de posición en USDT
        """
        base_size = self.current_capital * 0.12  # 12% base (más conservador)
        confidence_multiplier = signal['confidence']
        volatility = signal['indicators']['volatility']
        
        # Ajustar por volatilidad (reducir más con alta volatilidad)
        volatility_factor = max(0.3, 1 - (volatility * 15))
        
        # Ajustar por número de posiciones abiertas
        position_factor = 1.0 - (len(self.positions) * 0.2)
        
        # Calcular tamaño final
        position_size = base_size * confidence_multiplier * volatility_factor * position_factor
        
        # Aplicar límites más estrictos
        max_size = self.current_capital * self.max_position_size
        min_size = self.current_capital * self.min_position_size
        
        position_size = max(min_size, min(position_size, max_size))
        
        return position_size

    def execute_trade(self, symbol: str, signal: Dict) -> bool:
        """
        Ejecuta un trade con validaciones realistas
        
        Args:
            symbol: Símbolo del par
            signal: Señal de trading
            
        Returns:
            True si el trade fue ejecutado
        """
        if signal['action'] == 'HOLD':
            return False
        
        # Verificar si se puede tradear este símbolo
        if not self.can_trade_symbol(symbol):
            return False
        
        position_size = self.calculate_position_size(signal, symbol)
        
        if position_size < self.current_capital * self.min_position_size:
            return False
        
        current_price = signal['indicators']['price']
        volatility = signal['indicators']['volatility']
        
        # Aplicar slippage realista
        if signal['action'] == 'BUY':
            entry_price = current_price * (1 + self.slippage)
            stop_loss = entry_price * (1 - volatility * 2.5)
            take_profit = entry_price * (1 + volatility * 3.5)
        else:  # SELL
            entry_price = current_price * (1 - self.slippage)
            stop_loss = entry_price * (1 + volatility * 2.5)
            take_profit = entry_price * (1 - volatility * 3.5)
        
        # Aplicar comisión
        position_size_after_fee = position_size * (1 - self.trading_fee)
        
        # Crear posición
        position = {
            'symbol': symbol,
            'action': signal['action'],
            'entry_price': entry_price,
            'position_size': position_size_after_fee,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now(),
            'confidence': signal['confidence'],
            'original_size': position_size,
            'fee_paid': position_size * self.trading_fee
        }
        
        self.positions[symbol] = position
        self.current_capital -= position_size
        self.last_trade_time[symbol] = datetime.now()
        self.daily_trades_count += 1
        
        print(f"📈 {signal['action']} {symbol} | ${position_size:.2f} @ ${entry_price:.4f} | SL: ${stop_loss:.4f} | TP: ${take_profit:.4f} | Fee: ${position['fee_paid']:.2f}")
        
        return True

    def check_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Verifica y cierra posiciones con costos realistas
        
        Args:
            market_data: Datos de mercado actuales
        """
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            if symbol not in market_data:
                continue
            
            df = market_data[symbol]
            if len(df) == 0:
                continue
            
            current_price = df['close'].iloc[-1]
            entry_price = position['entry_price']
            position_size = position['position_size']
            
            should_close = False
            close_reason = ""
            
            if position['action'] == 'BUY':
                if current_price <= position['stop_loss']:
                    should_close = True
                    close_reason = "Stop Loss"
                elif current_price >= position['take_profit']:
                    should_close = True
                    close_reason = "Take Profit"
            else:  # SELL
                if current_price >= position['stop_loss']:
                    should_close = True
                    close_reason = "Stop Loss"
                elif current_price <= position['take_profit']:
                    should_close = True
                    close_reason = "Take Profit"
            
            if should_close:
                # Aplicar slippage al cierre
                if position['action'] == 'BUY':
                    exit_price = current_price * (1 - self.slippage)
                    pnl = position_size * (exit_price / entry_price - 1)
                else:  # SELL
                    exit_price = current_price * (1 + self.slippage)
                    pnl = position_size * (entry_price / exit_price - 1)
                
                # Aplicar comisión de cierre
                exit_fee = position_size * self.trading_fee
                pnl_after_fees = pnl - exit_fee
                
                # Cerrar posición
                self.current_capital += position_size + pnl_after_fees
                self.total_pnl += pnl_after_fees
                
                # Registrar trade
                trade = {
                    'symbol': symbol,
                    'action': position['action'],
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'position_size': position_size,
                    'pnl_gross': pnl,
                    'pnl_net': pnl_after_fees,
                    'pnl_percent': (pnl_after_fees / position['original_size']) * 100,
                    'entry_time': position['timestamp'],
                    'exit_time': datetime.now(),
                    'close_reason': close_reason,
                    'confidence': position['confidence'],
                    'entry_fee': position['fee_paid'],
                    'exit_fee': exit_fee,
                    'total_fees': position['fee_paid'] + exit_fee,
                    'slippage_cost': position['original_size'] * self.slippage * 2
                }
                
                self.trades.append(trade)
                positions_to_close.append(symbol)
                
                print(f"💰 Cerrado {symbol} | {close_reason} | PnL: ${pnl_after_fees:.2f} ({trade['pnl_percent']:.1f}%) | Fees: ${trade['total_fees']:.2f}")
        
        # Remover posiciones cerradas
        for symbol in positions_to_close:
            del self.positions[symbol]

    def check_reinvestment(self) -> bool:
        """
        Verifica si se debe reinvertir las ganancias
        
        Returns:
            True si se reinvirtió
        """
        current_roi = (self.current_capital - self.base_capital) / self.base_capital
        
        if current_roi >= self.reinvestment_threshold and self.current_capital < self.max_capital:
            # Calcular cantidad a reinvertir
            profit = self.current_capital - self.base_capital
            reinvestment_amount = min(profit, self.max_capital - self.base_capital)
            
            self.base_capital += reinvestment_amount
            self.total_reinvested += reinvestment_amount
            
            print(f"🔄 REINVERSIÓN: +${reinvestment_amount:.2f} | Nueva base: ${self.base_capital:.2f}")
            return True
        
        return False

    def reset_daily_counters(self) -> None:
        """Resetea contadores diarios si es necesario"""
        current_time = datetime.now()
        if (current_time - self.session_start_time).days >= 1:
            self.daily_trades_count = 0
            self.session_start_time = current_time
            print("🔄 Contadores diarios reseteados")

    def get_performance_stats(self) -> Dict:
        """Calcula estadísticas de rendimiento realistas"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_pnl_net': 0.0,
                'total_pnl_net': self.total_pnl,
                'current_roi': 0.0,
                'total_reinvested': self.total_reinvested,
                'total_fees_paid': 0.0,
                'avg_trade_duration': 0.0
            }
        
        winning_trades = [t for t in self.trades if t['pnl_net'] > 0]
        win_rate = len(winning_trades) / len(self.trades) * 100
        avg_pnl_net = sum(t['pnl_net'] for t in self.trades) / len(self.trades)
        current_roi = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        total_fees = sum(t['total_fees'] for t in self.trades)
        
        # Calcular duración promedio de trades
        durations = []
        for trade in self.trades:
            if isinstance(trade['entry_time'], str):
                entry_time = datetime.fromisoformat(trade['entry_time'])
                exit_time = datetime.fromisoformat(trade['exit_time'])
            else:
                entry_time = trade['entry_time']
                exit_time = trade['exit_time']
            duration = (exit_time - entry_time).total_seconds() / 60
            durations.append(duration)
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'avg_pnl_net': avg_pnl_net,
            'total_pnl_net': self.total_pnl,
            'current_roi': current_roi,
            'total_reinvested': self.total_reinvested,
            'total_fees_paid': total_fees,
            'avg_trade_duration': avg_duration
        }

    def run_trading_session(self, duration_hours: int = 8) -> Dict:
        """
        Ejecuta una sesión de trading realista
        
        Args:
            duration_hours: Duración de la sesión en horas
            
        Returns:
            Resultados de la sesión
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        cycle = 0
        
        print(f"\n🎯 === INICIANDO SESIÓN DE TRADING REALISTA ===")
        print(f"⏱️ Duración: {duration_hours} horas")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        print(f"📊 Configuración: Max {self.max_daily_trades} trades/día, {self.max_positions_simultaneous} posiciones simultáneas")
        
        while datetime.now() < end_time:
            cycle += 1
            
            # Resetear contadores diarios si es necesario
            self.reset_daily_counters()
            
            if cycle % 12 == 1:  # Mostrar progreso cada hora aprox
                print(f"\n--- Ciclo {cycle} ({datetime.now().strftime('%H:%M:%S')}) ---")
            
            # Generar datos de mercado para todos los símbolos
            market_data = {}
            for symbol in self.symbols:
                market_data[symbol] = self.generate_market_data(symbol, 100)
            
            # Verificar posiciones existentes
            self.check_positions(market_data)
            
            # Generar nuevas señales (solo si podemos tradear)
            signals_generated = 0
            for symbol in self.symbols:
                if self.can_trade_symbol(symbol):
                    signal = self.generate_signal(market_data[symbol], symbol)
                    if signal['action'] != 'HOLD' and signal['confidence'] >= self.min_confidence_threshold:
                        if self.execute_trade(symbol, signal):
                            signals_generated += 1
            
            # Verificar reinversión
            self.check_reinvestment()
            
            # Mostrar estado actual cada hora
            if cycle % 12 == 0:
                stats = self.get_performance_stats()
                print(f"💼 Capital: ${self.current_capital:.2f} | ROI: {stats['current_roi']:.2f}% | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | Posiciones: {len(self.positions)} | Trades hoy: {self.daily_trades_count}")
            
            # Pausa realista entre ciclos (5 minutos)
            time.sleep(5)  # En producción sería 300 segundos (5 min)
            self.cycles_completed += 1
        
        return self.generate_final_report()

    def generate_final_report(self) -> Dict:
        """Genera reporte final realista de la sesión"""
        stats = self.get_performance_stats()
        
        # Proyección mensual más realista
        if self.cycles_completed > 0 and stats['total_trades'] > 0:
            # Calcular ROI por hora
            session_hours = self.cycles_completed * 5 / 60  # 5 min por ciclo
            hourly_roi = stats['current_roi'] / session_hours if session_hours > 0 else 0
            
            # Proyección conservadora (6 horas de trading por día, 22 días al mes)
            daily_roi = hourly_roi * 6
            monthly_projection = daily_roi * 22
        else:
            monthly_projection = 0
        
        report = {
            'session_summary': {
                'duration_cycles': self.cycles_completed,
                'duration_hours': self.cycles_completed * 5 / 60,
                'signals_generated': len(self.trades),
                'trades_executed': len(self.trades),
                'positions_open': len(self.positions),
                'daily_trades_count': self.daily_trades_count
            },
            'capital_management': {
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'base_capital': self.base_capital,
                'total_reinvested': self.total_reinvested
            },
            'performance': {
                'total_roi': stats['current_roi'],
                'total_pnl_net': stats['total_pnl_net'],
                'avg_pnl_per_trade': stats['avg_pnl_net'],
                'win_rate': stats['win_rate'],
                'monthly_projection': monthly_projection,
                'total_fees_paid': stats['total_fees_paid'],
                'avg_trade_duration_minutes': stats['avg_trade_duration']
            },
            'trading_metrics': {
                'trades_per_hour': len(self.trades) / (self.cycles_completed * 5 / 60) if self.cycles_completed > 0 else 0,
                'max_daily_trades': self.max_daily_trades,
                'max_simultaneous_positions': self.max_positions_simultaneous,
                'min_confidence_threshold': self.min_confidence_threshold,
                'trading_fee_rate': self.trading_fee,
                'slippage_rate': self.slippage
            },
            'trades': self.trades,
            'recommendations': self.generate_recommendations(stats, monthly_projection)
        }
        
        return report

    def generate_recommendations(self, stats: Dict, monthly_projection: float) -> List[str]:
        """Genera recomendaciones realistas basadas en el rendimiento"""
        recommendations = []
        
        if stats['win_rate'] < 55:
            recommendations.append("📊 Aumentar umbral de confianza para mejorar win rate")
        
        if stats['avg_pnl_net'] < 2:
            recommendations.append("💰 Optimizar gestión de riesgo para mayor PnL promedio")
        
        if len(self.trades) < 2:
            recommendations.append("🔄 Considerar reducir umbral de confianza para más oportunidades")
        
        if monthly_projection < 5:
            recommendations.append("🎯 Ajustar parámetros para alcanzar 5% ROI mensual objetivo")
        
        if stats['total_fees_paid'] > stats['total_pnl_net'] * 0.3:
            recommendations.append("💸 Optimizar frecuencia de trading para reducir impacto de comisiones")
        
        if self.total_reinvested == 0 and stats['current_roi'] > 3:
            recommendations.append("💎 Considerar reducir umbral de reinversión para crecimiento más rápido")
        
        return recommendations

def run_demo_realista():
    """Ejecuta una demostración realista del sistema"""
    print("🚀 === SICAR CAPITAL VARIABLE REALISTA v3.0 ===")
    print("💰 Sistema de trading con frecuencia y costos realistas")
    
    # Inicializar sistema
    sicar = SicarCapitalVariableRealista(initial_capital=200.0)
    
    # Ejecutar sesión de trading de 8 horas
    results = sicar.run_trading_session(duration_hours=8)
    
    # Mostrar resultados finales
    print(f"\n🎉 === RESULTADOS FINALES REALISTAS ===")
    print(f"⏱️ Duración: {results['session_summary']['duration_hours']:.1f} horas")
    print(f"🔄 Ciclos completados: {results['session_summary']['duration_cycles']}")
    print(f"📡 Señales generadas: {results['session_summary']['signals_generated']}")
    print(f"💼 Trades ejecutados: {results['session_summary']['trades_executed']}")
    print(f"📊 Trades por hora: {results['trading_metrics']['trades_per_hour']:.1f}")
    print(f"💰 Capital inicial: ${results['capital_management']['initial_capital']:.2f}")
    print(f"💰 Capital final: ${results['capital_management']['final_capital']:.2f}")
    print(f"📈 ROI total: {results['performance']['total_roi']:.2f}%")
    print(f"💵 PnL neto: ${results['performance']['total_pnl_net']:.2f}")
    print(f"💸 Comisiones pagadas: ${results['performance']['total_fees_paid']:.2f}")
    print(f"🎯 Win rate: {results['performance']['win_rate']:.1f}%")
    print(f"📊 PnL promedio: ${results['performance']['avg_pnl_per_trade']:.2f}")
    print(f"⏱️ Duración promedio trade: {results['performance']['avg_trade_duration_minutes']:.1f} min")
    print(f"🔄 Total reinvertido: ${results['capital_management']['total_reinvested']:.2f}")
    print(f"📈 Proyección mensual: {results['performance']['monthly_projection']:.1f}%")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sicar_realista_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    # Mostrar recomendaciones
    if results['recommendations']:
        print(f"\n🔧 === RECOMENDACIONES ===")
        for rec in results['recommendations']:
            print(rec)
    
    # Verificar objetivo de 5% ROI
    if results['performance']['monthly_projection'] >= 5.0:
        print(f"\n✅ ¡OBJETIVO ALCANZADO! Proyección mensual: {results['performance']['monthly_projection']:.1f}%")
    else:
        print(f"\n⚠️ Objetivo pendiente. Proyección actual: {results['performance']['monthly_projection']:.1f}% (Meta: 5.0%)")
        print("💡 Sugerencia: Ajustar parámetros o aumentar capital base")
    
    return results

if __name__ == "__main__":
    run_demo_realista()