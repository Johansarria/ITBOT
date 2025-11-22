#!/usr/bin/env python3
"""
SICAR - Sistema de Capital Variable v2.0
Sistema de trading con capital variable entre 200-500 USDT y reinversión automática
Versión corregida sin errores de broadcasting
"""

import numpy as np
import pandas as pd
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import random

class SicarCapitalVariableV2:
    def __init__(self, initial_capital: float = 200.0):
        """
        Inicializa el sistema SICAR con capital variable
        
        Args:
            initial_capital: Capital inicial en USDT (mínimo 200)
        """
        self.initial_capital = max(initial_capital, 200.0)
        self.current_capital = self.initial_capital
        self.base_capital = self.initial_capital
        self.max_capital = 500.0
        self.min_capital = 200.0
        
        # Configuración de trading
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT']
        self.reinvestment_threshold = 0.05  # 5% ROI para reinvertir
        self.max_position_size = 0.25  # 25% del capital por posición
        self.min_position_size = 0.05  # 5% del capital por posición
        
        # Tracking
        self.trades = []
        self.positions = {}
        self.total_pnl = 0.0
        self.total_reinvested = 0.0
        self.cycles_completed = 0
        
        # Configuración de indicadores
        self.sma_period = 10
        self.rsi_period = 14
        self.bb_period = 20
        self.bb_std = 2.0
        
        print(f"🚀 SICAR Capital Variable v2.0 iniciado")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        print(f"📊 Símbolos: {', '.join(self.symbols)}")
        print(f"🔄 Umbral de reinversión: {self.reinvestment_threshold*100}%")

    def generate_market_data(self, symbol: str, periods: int = 50) -> pd.DataFrame:
        """
        Genera datos de mercado simulados realistas
        
        Args:
            symbol: Símbolo del par de trading
            periods: Número de períodos a generar
            
        Returns:
            DataFrame con datos OHLCV
        """
        # Precios base por símbolo
        base_prices = {
            'BTCUSDT': 45000,
            'ETHUSDT': 2800,
            'ADAUSDT': 0.45,
            'DOTUSDT': 7.5
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generar datos con tendencia y volatilidad realista
        timestamps = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []
        
        current_time = datetime.now()
        current_price = base_price
        
        for i in range(periods):
            # Timestamp
            timestamps.append(current_time - timedelta(minutes=periods-i))
            
            # Precio de apertura
            open_price = current_price
            opens.append(open_price)
            
            # Volatilidad realista (0.5% - 3%)
            volatility = random.uniform(0.005, 0.03)
            price_change = random.gauss(0, volatility)
            
            # Precio de cierre con tendencia ligera
            trend = random.uniform(-0.002, 0.002)
            close_price = open_price * (1 + price_change + trend)
            closes.append(close_price)
            
            # High y Low
            high_price = max(open_price, close_price) * random.uniform(1.001, 1.015)
            low_price = min(open_price, close_price) * random.uniform(0.985, 0.999)
            highs.append(high_price)
            lows.append(low_price)
            
            # Volumen
            base_volume = random.uniform(1000000, 5000000)
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

    def calculate_volatility(self, prices: List[float], period: int = 10) -> float:
        """Calcula volatilidad como desviación estándar de retornos"""
        if len(prices) < period + 1:
            return 0.02  # Volatilidad por defecto
        
        returns = [(prices[i] / prices[i-1] - 1) for i in range(-period, 0)]
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return variance ** 0.5

    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Genera señales de trading basadas en múltiples indicadores
        
        Args:
            df: DataFrame con datos de mercado
            symbol: Símbolo del par
            
        Returns:
            Diccionario con información de la señal
        """
        if len(df) < 20:
            return {'action': 'HOLD', 'confidence': 0.0, 'reason': 'Datos insuficientes'}
        
        prices = df['close'].tolist()
        volumes = df['volume'].tolist()
        current_price = prices[-1]
        
        # Calcular indicadores
        sma_10 = self.calculate_sma(prices, 10)
        sma_20 = self.calculate_sma(prices, 20)
        rsi = self.calculate_rsi(prices, 14)
        upper_bb, middle_bb, lower_bb = self.calculate_bollinger_bands(prices, 20)
        volatility = self.calculate_volatility(prices, 10)
        
        # Análisis de volumen
        avg_volume = sum(volumes[-10:]) / 10
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Sistema de puntuación
        score = 0
        reasons = []
        
        # 1. Análisis de tendencia (SMA)
        if current_price > sma_10 > sma_20:
            score += 2
            reasons.append("Tendencia alcista (SMA)")
        elif current_price < sma_10 < sma_20:
            score -= 2
            reasons.append("Tendencia bajista (SMA)")
        
        # 2. Análisis RSI
        if rsi < 30:
            score += 2
            reasons.append(f"RSI sobreventa ({rsi:.1f})")
        elif rsi > 70:
            score -= 2
            reasons.append(f"RSI sobrecompra ({rsi:.1f})")
        elif 40 <= rsi <= 60:
            score += 1
            reasons.append("RSI neutral")
        
        # 3. Bollinger Bands
        if current_price <= lower_bb:
            score += 2
            reasons.append("Precio en banda inferior BB")
        elif current_price >= upper_bb:
            score -= 2
            reasons.append("Precio en banda superior BB")
        
        # 4. Análisis de volumen
        if volume_ratio > 1.5:
            score += 1
            reasons.append(f"Volumen alto ({volume_ratio:.1f}x)")
        elif volume_ratio < 0.5:
            score -= 1
            reasons.append(f"Volumen bajo ({volume_ratio:.1f}x)")
        
        # 5. Volatilidad
        if volatility > 0.05:  # Alta volatilidad
            score -= 1
            reasons.append("Alta volatilidad")
        elif volatility < 0.01:  # Baja volatilidad
            score += 1
            reasons.append("Baja volatilidad")
        
        # Determinar acción
        confidence = min(abs(score) / 6.0, 1.0)  # Normalizar a 0-1
        
        if score >= 3:
            action = 'BUY'
        elif score <= -3:
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
                'sma_10': sma_10,
                'sma_20': sma_20,
                'rsi': rsi,
                'bb_upper': upper_bb,
                'bb_lower': lower_bb,
                'volatility': volatility,
                'volume_ratio': volume_ratio
            }
        }

    def calculate_position_size(self, signal: Dict, symbol: str) -> float:
        """
        Calcula el tamaño de posición basado en confianza y volatilidad
        
        Args:
            signal: Señal de trading
            symbol: Símbolo del par
            
        Returns:
            Tamaño de posición en USDT
        """
        base_size = self.current_capital * 0.15  # 15% base
        confidence_multiplier = signal['confidence']
        volatility = signal['indicators']['volatility']
        
        # Ajustar por volatilidad (menor posición con mayor volatilidad)
        volatility_factor = max(0.5, 1 - (volatility * 10))
        
        # Calcular tamaño final
        position_size = base_size * confidence_multiplier * volatility_factor
        
        # Aplicar límites
        max_size = self.current_capital * self.max_position_size
        min_size = self.current_capital * self.min_position_size
        
        position_size = max(min_size, min(position_size, max_size))
        
        return position_size

    def execute_trade(self, symbol: str, signal: Dict) -> bool:
        """
        Ejecuta un trade basado en la señal
        
        Args:
            symbol: Símbolo del par
            signal: Señal de trading
            
        Returns:
            True si el trade fue ejecutado
        """
        if signal['action'] == 'HOLD':
            return False
        
        # Verificar si ya hay posición abierta
        if symbol in self.positions:
            return False
        
        position_size = self.calculate_position_size(signal, symbol)
        
        if position_size < self.current_capital * self.min_position_size:
            return False
        
        current_price = signal['indicators']['price']
        volatility = signal['indicators']['volatility']
        
        # Calcular stop loss y take profit
        if signal['action'] == 'BUY':
            stop_loss = current_price * (1 - volatility * 3)
            take_profit = current_price * (1 + volatility * 4)
        else:  # SELL
            stop_loss = current_price * (1 + volatility * 3)
            take_profit = current_price * (1 - volatility * 4)
        
        # Crear posición
        position = {
            'symbol': symbol,
            'action': signal['action'],
            'entry_price': current_price,
            'position_size': position_size,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'timestamp': datetime.now(),
            'confidence': signal['confidence']
        }
        
        self.positions[symbol] = position
        self.current_capital -= position_size
        
        print(f"📈 {signal['action']} {symbol} | ${position_size:.2f} @ ${current_price:.4f} | SL: ${stop_loss:.4f} | TP: ${take_profit:.4f}")
        
        return True

    def check_positions(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """
        Verifica y cierra posiciones según stop loss/take profit
        
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
                # Calcular PnL
                if position['action'] == 'BUY':
                    pnl = position_size * (current_price / entry_price - 1)
                else:  # SELL
                    pnl = position_size * (entry_price / current_price - 1)
                
                # Cerrar posición
                self.current_capital += position_size + pnl
                self.total_pnl += pnl
                
                # Registrar trade
                trade = {
                    'symbol': symbol,
                    'action': position['action'],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'position_size': position_size,
                    'pnl': pnl,
                    'pnl_percent': (pnl / position_size) * 100,
                    'entry_time': position['timestamp'],
                    'exit_time': datetime.now(),
                    'close_reason': close_reason,
                    'confidence': position['confidence']
                }
                
                self.trades.append(trade)
                positions_to_close.append(symbol)
                
                print(f"💰 Cerrado {symbol} | {close_reason} | PnL: ${pnl:.2f} ({trade['pnl_percent']:.1f}%)")
        
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

    def get_performance_stats(self) -> Dict:
        """Calcula estadísticas de rendimiento"""
        if not self.trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_pnl': 0.0,
                'total_pnl': self.total_pnl,
                'current_roi': 0.0,
                'total_reinvested': self.total_reinvested
            }
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(self.trades) * 100
        avg_pnl = sum(t['pnl'] for t in self.trades) / len(self.trades)
        current_roi = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        
        return {
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'total_pnl': self.total_pnl,
            'current_roi': current_roi,
            'total_reinvested': self.total_reinvested
        }

    def run_trading_session(self, duration_minutes: int = 60) -> Dict:
        """
        Ejecuta una sesión de trading
        
        Args:
            duration_minutes: Duración de la sesión en minutos
            
        Returns:
            Resultados de la sesión
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        cycle = 0
        
        print(f"\n🎯 === INICIANDO SESIÓN DE TRADING ===")
        print(f"⏱️ Duración: {duration_minutes} minutos")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        
        while datetime.now() < end_time:
            cycle += 1
            print(f"\n--- Ciclo {cycle} ---")
            
            # Generar datos de mercado para todos los símbolos
            market_data = {}
            for symbol in self.symbols:
                market_data[symbol] = self.generate_market_data(symbol, 50)
            
            # Verificar posiciones existentes
            self.check_positions(market_data)
            
            # Generar nuevas señales
            signals_generated = 0
            for symbol in self.symbols:
                if symbol not in self.positions:  # Solo si no hay posición abierta
                    signal = self.generate_signal(market_data[symbol], symbol)
                    if signal['action'] != 'HOLD' and signal['confidence'] > 0.6:
                        if self.execute_trade(symbol, signal):
                            signals_generated += 1
            
            # Verificar reinversión
            self.check_reinvestment()
            
            # Mostrar estado actual
            stats = self.get_performance_stats()
            print(f"💼 Capital: ${self.current_capital:.2f} | ROI: {stats['current_roi']:.2f}% | Trades: {stats['total_trades']} | WR: {stats['win_rate']:.1f}% | Posiciones: {len(self.positions)}")
            
            # Pausa entre ciclos
            time.sleep(2)
            self.cycles_completed += 1
        
        return self.generate_final_report()

    def generate_final_report(self) -> Dict:
        """Genera reporte final de la sesión"""
        stats = self.get_performance_stats()
        
        # Proyección mensual
        if self.cycles_completed > 0:
            cycles_per_day = (self.cycles_completed / 60) * 24  # Asumiendo 1 ciclo por minuto
            daily_roi = stats['current_roi'] / (self.cycles_completed / cycles_per_day) if cycles_per_day > 0 else 0
            monthly_projection = daily_roi * 30
        else:
            monthly_projection = 0
        
        report = {
            'session_summary': {
                'duration_cycles': self.cycles_completed,
                'signals_generated': len(self.trades),
                'trades_executed': len(self.trades),
                'positions_open': len(self.positions)
            },
            'capital_management': {
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'base_capital': self.base_capital,
                'total_reinvested': self.total_reinvested
            },
            'performance': {
                'total_roi': stats['current_roi'],
                'total_pnl': stats['total_pnl'],
                'avg_pnl_per_trade': stats['avg_pnl'],
                'win_rate': stats['win_rate'],
                'monthly_projection': monthly_projection
            },
            'trades': self.trades,
            'recommendations': self.generate_recommendations(stats, monthly_projection)
        }
        
        return report

    def generate_recommendations(self, stats: Dict, monthly_projection: float) -> List[str]:
        """Genera recomendaciones basadas en el rendimiento"""
        recommendations = []
        
        if stats['win_rate'] < 50:
            recommendations.append("📊 Optimizar filtros de señales para mejorar win rate")
        
        if stats['avg_pnl'] < 5:
            recommendations.append("💰 Ajustar gestión de posiciones para mayor PnL promedio")
        
        if len(self.trades) < 5:
            recommendations.append("🔄 Aumentar frecuencia de trading con señales más sensibles")
        
        if monthly_projection < 5:
            recommendations.append("🎯 Implementar estrategias adicionales para alcanzar 5% ROI mensual")
        
        if self.total_reinvested == 0:
            recommendations.append("💎 Optimizar umbral de reinversión para crecimiento exponencial")
        
        return recommendations

def run_demo():
    """Ejecuta una demostración del sistema"""
    print("🚀 === SICAR CAPITAL VARIABLE V2.0 ===")
    print("💰 Sistema de trading con capital variable y reinversión automática")
    
    # Inicializar sistema
    sicar = SicarCapitalVariableV2(initial_capital=200.0)
    
    # Ejecutar sesión de trading
    results = sicar.run_trading_session(duration_minutes=30)
    
    # Mostrar resultados finales
    print(f"\n🎉 === RESULTADOS FINALES ===")
    print(f"🔄 Ciclos completados: {results['session_summary']['duration_cycles']}")
    print(f"📡 Señales generadas: {results['session_summary']['signals_generated']}")
    print(f"💼 Trades ejecutados: {results['session_summary']['trades_executed']}")
    print(f"💰 Capital inicial: ${results['capital_management']['initial_capital']:.2f}")
    print(f"💰 Capital final: ${results['capital_management']['final_capital']:.2f}")
    print(f"📈 ROI total: {results['performance']['total_roi']:.2f}%")
    print(f"💵 PnL total: ${results['performance']['total_pnl']:.2f}")
    print(f"🎯 Win rate: {results['performance']['win_rate']:.1f}%")
    print(f"📊 PnL promedio: ${results['performance']['avg_pnl_per_trade']:.2f}")
    print(f"🔄 Total reinvertido: ${results['capital_management']['total_reinvested']:.2f}")
    print(f"📈 Proyección mensual: {results['performance']['monthly_projection']:.1f}%")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"sicar_capital_variable_v2_results_{timestamp}.json"
    
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
    
    return results

if __name__ == "__main__":
    run_demo()