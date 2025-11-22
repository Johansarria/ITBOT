#!/usr/bin/env python3
"""
Sistema SICAR Final con Capital Variable
Versión corregida y optimizada para trading con reinversión automática
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import os
import time
import random

class SicarCapitalVariableFinal:
    def __init__(self, 
                 initial_capital: float = 200.0,
                 max_capital: float = 500.0,
                 symbols: List[str] = None,
                 reinvestment_threshold: float = 0.05):
        
        # Configuración
        if symbols is None:
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT']
        
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.max_capital = max_capital
        self.reinvestment_threshold = reinvestment_threshold
        
        # Estado del capital
        self.current_capital = initial_capital
        self.base_capital = initial_capital
        self.total_reinvested = 0.0
        self.available_capital = initial_capital
        
        # Estado de trading
        self.active_positions = {}
        self.trade_history = []
        self.performance_history = []
        
        # Métricas
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        # Configuración de riesgo
        self.max_position_size = 0.25  # 25% máximo por posición
        self.min_confidence = 0.35     # Confianza mínima para trade
        self.max_positions = 3         # Máximo 3 posiciones simultáneas
        
        print(f"🚀 Sistema SICAR Capital Variable inicializado")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        print(f"🎯 Capital máximo: ${self.max_capital:.2f}")
        print(f"📊 Símbolos: {', '.join(self.symbols)}")
        print(f"🔄 Umbral reinversión: {self.reinvestment_threshold:.1%}")
        
    def generate_market_data(self, symbol: str, periods: int = 30) -> pd.DataFrame:
        """Genera datos de mercado realistas"""
        
        # Precios base realistas
        base_prices = {
            'BTCUSDT': 43500 + random.uniform(-2000, 2000),
            'ETHUSDT': 2650 + random.uniform(-200, 200),
            'ADAUSDT': 0.43 + random.uniform(-0.05, 0.05),
            'DOTUSDT': 6.3 + random.uniform(-0.8, 0.8)
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generar serie temporal
        random.seed(int(time.time() * 1000) % 10000 + hash(symbol) % 1000)
        
        prices = []
        current_price = base_price
        
        # Tendencia aleatoria
        trend = random.uniform(-0.001, 0.002)
        volatility = random.uniform(0.015, 0.03)
        
        for i in range(periods):
            # Movimiento diario
            daily_change = trend + random.gauss(0, volatility)
            
            # Añadir algunos breakouts
            if random.random() < 0.1:  # 10% probabilidad
                daily_change += random.choice([-1, 1]) * random.uniform(0.02, 0.04)
            
            current_price *= (1 + daily_change)
            current_price = max(current_price, base_price * 0.7)  # Evitar caídas extremas
            prices.append(current_price)
        
        # Crear DataFrame
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='1H')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(random.gauss(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(random.gauss(0, 0.005))) for p in prices],
            'close': prices,
            'volume': [random.uniform(1000000, 3000000) for _ in prices]
        })
        
        return df
    
    def calculate_simple_indicators(self, df: pd.DataFrame) -> Dict:
        """Calcula indicadores técnicos simplificados y robustos"""
        close_prices = df['close'].values
        volumes = df['volume'].values
        
        if len(close_prices) < 15:
            return {'error': 'insufficient_data'}
        
        current_price = close_prices[-1]
        
        # Medias móviles simples
        sma_5 = np.mean(close_prices[-5:])
        sma_10 = np.mean(close_prices[-10:])
        sma_15 = np.mean(close_prices[-15:])
        
        # RSI simplificado
        def calculate_rsi(prices, period=14):
            if len(prices) < period + 1:
                return 50
            
            deltas = np.diff(prices[-period-1:])
            gains = deltas[deltas > 0]
            losses = -deltas[deltas < 0]
            
            avg_gain = np.mean(gains) if len(gains) > 0 else 0
            avg_loss = np.mean(losses) if len(losses) > 0 else 0
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        
        rsi = calculate_rsi(close_prices)
        
        # Momentum
        momentum = (current_price - close_prices[-5]) / close_prices[-5] if len(close_prices) >= 5 else 0
        
        # Volatilidad
        returns = np.diff(close_prices[-10:]) / close_prices[-11:-1]
        volatility = np.std(returns) if len(returns) > 0 else 0.02
        
        # Volume analysis
        avg_volume = np.mean(volumes[-10:])
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
        
        # Tendencia
        trend_strength = (sma_5 - sma_15) / sma_15 if sma_15 > 0 else 0
        
        # Bollinger Bands simplificadas
        bb_middle = sma_15
        bb_std = np.std(close_prices[-15:])
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        
        # Posición de precio
        price_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper > bb_lower else 0.5
        
        return {
            'current_price': current_price,
            'sma_5': sma_5,
            'sma_10': sma_10,
            'sma_15': sma_15,
            'rsi': rsi,
            'momentum': momentum,
            'volatility': volatility,
            'volume_ratio': volume_ratio,
            'trend_strength': trend_strength,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'price_position': price_position
        }
    
    def generate_trading_signal(self, symbol: str, indicators: Dict) -> Dict:
        """Genera señal de trading robusta"""
        
        signal = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'action': 'hold',
            'confidence': 0.0,
            'reasons': [],
            'price': indicators['current_price'],
            'volatility': indicators['volatility']
        }
        
        # Sistema de puntuación
        score = 0
        max_score = 0
        reasons = []
        
        # 1. Tendencia (SMA) - Peso: 3
        max_score += 3
        if indicators['sma_5'] > indicators['sma_10'] > indicators['sma_15']:
            score += 3
            reasons.append('strong_bullish_trend')
        elif indicators['sma_5'] > indicators['sma_10']:
            score += 2
            reasons.append('bullish_trend')
        elif indicators['sma_5'] < indicators['sma_10'] < indicators['sma_15']:
            score -= 2
            reasons.append('bearish_trend')
        
        # 2. RSI - Peso: 2
        max_score += 2
        rsi = indicators['rsi']
        if 30 < rsi < 70:
            score += 2
            reasons.append('rsi_neutral_zone')
        elif 20 < rsi <= 30:
            score += 1.5
            reasons.append('rsi_oversold')
        elif rsi >= 80:
            score -= 1.5
            reasons.append('rsi_overbought')
        
        # 3. Momentum - Peso: 2
        max_score += 2
        momentum = indicators['momentum']
        if momentum > 0.01:
            score += 2
            reasons.append('positive_momentum')
        elif momentum > 0:
            score += 1
            reasons.append('slight_positive_momentum')
        elif momentum < -0.01:
            score -= 1
            reasons.append('negative_momentum')
        
        # 4. Volume - Peso: 1
        max_score += 1
        if indicators['volume_ratio'] > 1.2:
            score += 1
            reasons.append('high_volume')
        elif indicators['volume_ratio'] < 0.8:
            score -= 0.5
            reasons.append('low_volume')
        
        # 5. Posición de precio (Bollinger) - Peso: 1
        max_score += 1
        price_pos = indicators['price_position']
        if 0.2 < price_pos < 0.8:
            score += 1
            reasons.append('good_price_position')
        elif price_pos <= 0.2:
            score += 0.5
            reasons.append('near_support')
        
        # 6. Volatilidad - Peso: 1
        max_score += 1
        volatility = indicators['volatility']
        if 0.01 < volatility < 0.04:
            score += 1
            reasons.append('good_volatility')
        elif volatility > 0.05:
            score -= 0.5
            reasons.append('high_volatility')
        
        # Calcular confianza
        confidence = max(0, min(1, score / max_score)) if max_score > 0 else 0
        
        # Determinar acción
        if confidence >= 0.5 and score >= 4:
            signal['action'] = 'buy'
        elif confidence >= 0.4 and score <= -2:
            signal['action'] = 'sell'
        else:
            signal['action'] = 'hold'
        
        signal['confidence'] = confidence
        signal['reasons'] = reasons
        signal['score'] = score
        signal['max_score'] = max_score
        
        return signal
    
    def calculate_position_size(self, symbol: str, confidence: float, volatility: float) -> float:
        """Calcula tamaño de posición dinámico"""
        
        # Tamaño base
        base_size = self.available_capital * self.max_position_size
        
        # Ajustar por confianza
        confidence_multiplier = 0.5 + (confidence * 1.0)
        
        # Ajustar por volatilidad
        volatility_multiplier = max(0.6, 1.0 - (volatility * 15))
        
        # Ajustar por posiciones activas
        position_multiplier = max(0.7, 1.0 - (len(self.active_positions) * 0.15))
        
        # Calcular tamaño final
        position_size = base_size * confidence_multiplier * volatility_multiplier * position_multiplier
        
        # Límites
        min_size = 15.0  # Mínimo $15
        max_size = self.available_capital * 0.4  # Máximo 40%
        
        position_size = max(min_size, min(position_size, max_size))
        
        return position_size
    
    def execute_trade(self, signal: Dict) -> Optional[Dict]:
        """Ejecuta trades"""
        
        symbol = signal['symbol']
        action = signal['action']
        price = signal['price']
        confidence = signal['confidence']
        volatility = signal['volatility']
        
        if action == 'buy':
            # Verificaciones
            if symbol in self.active_positions:
                return None
            
            if len(self.active_positions) >= self.max_positions:
                return None
            
            if confidence < self.min_confidence:
                return None
            
            # Calcular posición
            position_size = self.calculate_position_size(symbol, confidence, volatility)
            
            if position_size > self.available_capital:
                return None
            
            quantity = position_size / price
            
            # Stop loss y take profit
            stop_loss_pct = max(0.04, min(0.08, volatility * 2.5))  # 4-8%
            take_profit_pct = max(0.08, min(0.15, volatility * 4))  # 8-15%
            
            # Ejecutar compra
            self.active_positions[symbol] = {
                'entry_price': price,
                'quantity': quantity,
                'position_size': position_size,
                'entry_time': datetime.now(),
                'confidence': confidence,
                'stop_loss': price * (1 - stop_loss_pct),
                'take_profit': price * (1 + take_profit_pct),
                'stop_loss_pct': stop_loss_pct,
                'take_profit_pct': take_profit_pct
            }
            
            self.available_capital -= position_size
            
            trade = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': 'buy',
                'price': price,
                'quantity': quantity,
                'position_size': position_size,
                'confidence': confidence,
                'stop_loss': self.active_positions[symbol]['stop_loss'],
                'take_profit': self.active_positions[symbol]['take_profit'],
                'available_capital_after': self.available_capital
            }
            
            self.trade_history.append(trade)
            print(f"🟢 BUY {symbol}: ${position_size:.2f} at ${price:.2f} (Conf: {confidence:.1%})")
            
            return trade
        
        elif action == 'sell':
            if symbol not in self.active_positions:
                return None
            
            position = self.active_positions[symbol]
            quantity = position['quantity']
            entry_price = position['entry_price']
            position_size = position['position_size']
            
            # Calcular PnL
            sell_value = quantity * price
            pnl = sell_value - position_size
            pnl_percentage = (pnl / position_size) * 100
            
            # Actualizar capital
            self.available_capital += sell_value
            self.current_capital = self.available_capital + sum(
                pos['position_size'] for pos in self.active_positions.values() if pos != position
            )
            
            # Estadísticas
            self.total_trades += 1
            self.total_pnl += pnl
            
            if pnl > 0:
                self.winning_trades += 1
            
            # Remover posición
            del self.active_positions[symbol]
            
            trade = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': 'sell',
                'price': price,
                'quantity': quantity,
                'position_size': sell_value,
                'entry_price': entry_price,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage,
                'confidence': confidence,
                'current_capital': self.current_capital,
                'available_capital': self.available_capital
            }
            
            self.trade_history.append(trade)
            
            emoji = "🟢" if pnl > 0 else "🔴"
            print(f"{emoji} SELL {symbol}: PnL ${pnl:.2f} ({pnl_percentage:.1f}%) - Capital: ${self.current_capital:.2f}")
            
            # Verificar reinversión
            self._check_reinvestment()
            
            return trade
        
        return None
    
    def _check_stop_loss_take_profit(self, symbol: str, current_price: float):
        """Verifica stop-loss y take-profit"""
        
        if symbol not in self.active_positions:
            return
        
        position = self.active_positions[symbol]
        
        # Check stop-loss
        if current_price <= position['stop_loss']:
            signal = {
                'symbol': symbol,
                'action': 'sell',
                'price': current_price,
                'confidence': 0.9,
                'volatility': 0.02,
                'reason': 'stop_loss'
            }
            trade = self.execute_trade(signal)
            if trade:
                print(f"🛑 STOP LOSS {symbol}")
            
        # Check take-profit
        elif current_price >= position['take_profit']:
            signal = {
                'symbol': symbol,
                'action': 'sell',
                'price': current_price,
                'confidence': 0.9,
                'volatility': 0.02,
                'reason': 'take_profit'
            }
            trade = self.execute_trade(signal)
            if trade:
                print(f"🎯 TAKE PROFIT {symbol}")
    
    def _check_reinvestment(self):
        """Verifica reinversión automática"""
        
        current_roi = (self.current_capital - self.base_capital) / self.base_capital
        
        if current_roi >= self.reinvestment_threshold and self.base_capital < self.max_capital:
            
            profit = self.current_capital - self.base_capital
            max_reinvestment = self.max_capital - self.base_capital
            reinvestment = min(profit, max_reinvestment)
            
            if reinvestment >= 15:  # Mínimo $15 para reinvertir
                
                self.base_capital += reinvestment
                self.total_reinvested += reinvestment
                
                reinvestment_event = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'reinvestment',
                    'amount': reinvestment,
                    'new_base_capital': self.base_capital,
                    'total_reinvested': self.total_reinvested,
                    'roi_at_reinvestment': current_roi
                }
                
                self.trade_history.append(reinvestment_event)
                print(f"💰 REINVERSIÓN: ${reinvestment:.2f} - Nuevo capital base: ${self.base_capital:.2f}")
    
    def run_trading_simulation(self, cycles: int = 30) -> Dict:
        """Ejecuta simulación de trading"""
        
        print(f"\n🚀 Iniciando simulación - {cycles} ciclos")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        
        session_start = datetime.now()
        signals_generated = 0
        trades_executed = 0
        
        for cycle in range(cycles):
            print(f"\n--- Ciclo {cycle + 1}/{cycles} ---")
            
            # Procesar cada símbolo
            for symbol in self.symbols:
                try:
                    # Generar datos de mercado
                    market_data = self.generate_market_data(symbol, 30)
                    
                    # Calcular indicadores
                    indicators = self.calculate_simple_indicators(market_data)
                    
                    if 'error' in indicators:
                        continue
                    
                    # Generar señal
                    signal = self.generate_trading_signal(symbol, indicators)
                    signals_generated += 1
                    
                    print(f"📊 {symbol}: {signal['action'].upper()} (Conf: {signal['confidence']:.1%}, Score: {signal['score']:.1f})")
                    
                    # Ejecutar trade
                    trade = self.execute_trade(signal)
                    if trade:
                        trades_executed += 1
                    
                    # Verificar stop-loss y take-profit
                    self._check_stop_loss_take_profit(symbol, indicators['current_price'])
                    
                except Exception as e:
                    print(f"❌ Error procesando {symbol}: {e}")
            
            # Mostrar estado actual
            win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            roi = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
            
            print(f"💼 Capital: ${self.current_capital:.2f} | ROI: {roi:.2f}% | Trades: {self.total_trades} | WR: {win_rate:.1f}% | Posiciones: {len(self.active_positions)}")
            
            # Pausa entre ciclos
            time.sleep(0.1)
        
        # Cerrar posiciones abiertas al final
        for symbol in list(self.active_positions.keys()):
            market_data = self.generate_market_data(symbol, 30)
            indicators = self.calculate_simple_indicators(market_data)
            if 'error' not in indicators:
                signal = {
                    'symbol': symbol,
                    'action': 'sell',
                    'price': indicators['current_price'],
                    'confidence': 0.8,
                    'volatility': indicators['volatility'],
                    'reason': 'session_end'
                }
                self.execute_trade(signal)
        
        # Resultados finales
        final_roi = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        final_win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        results = {
            'session_duration': str(datetime.now() - session_start),
            'cycles_completed': cycles,
            'signals_generated': signals_generated,
            'trades_executed': trades_executed,
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_roi': final_roi,
            'total_pnl': self.total_pnl,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': final_win_rate,
            'active_positions': len(self.active_positions),
            'total_reinvested': self.total_reinvested,
            'base_capital': self.base_capital,
            'average_pnl_per_trade': self.total_pnl / self.total_trades if self.total_trades > 0 else 0
        }
        
        return results
    
    def get_performance_summary(self) -> Dict:
        """Genera resumen de rendimiento"""
        
        total_roi = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        
        return {
            'capital_summary': {
                'initial_capital': self.initial_capital,
                'current_capital': self.current_capital,
                'base_capital': self.base_capital,
                'available_capital': self.available_capital,
                'total_roi_percentage': total_roi,
                'total_reinvested': self.total_reinvested,
                'capital_growth': self.current_capital - self.initial_capital
            },
            'trading_performance': {
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'win_rate_percentage': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
                'total_pnl': self.total_pnl,
                'average_pnl_per_trade': self.total_pnl / self.total_trades if self.total_trades > 0 else 0,
                'active_positions': len(self.active_positions)
            },
            'recent_trades': self.trade_history[-10:] if len(self.trade_history) > 10 else self.trade_history
        }

def run_final_demo():
    """Demo final del sistema"""
    
    print("🎯 === SISTEMA SICAR CAPITAL VARIABLE FINAL ===")
    print("⚙️ Configuración: 200-500 USDT con reinversión automática")
    
    # Crear sistema
    system = SicarCapitalVariableFinal(
        initial_capital=200.0,
        max_capital=500.0,
        symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT'],
        reinvestment_threshold=0.05
    )
    
    # Ejecutar simulación
    results = system.run_trading_simulation(cycles=35)
    
    # Mostrar resultados finales
    print(f"\n🎉 === RESULTADOS FINALES ===")
    print(f"⏱️ Duración: {results['session_duration']}")
    print(f"🔄 Ciclos completados: {results['cycles_completed']}")
    print(f"📡 Señales generadas: {results['signals_generated']}")
    print(f"💼 Trades ejecutados: {results['trades_executed']}")
    print(f"💰 Capital inicial: ${results['initial_capital']:.2f}")
    print(f"💰 Capital final: ${results['final_capital']:.2f}")
    print(f"📈 ROI total: {results['total_roi']:.2f}%")
    print(f"💵 PnL total: ${results['total_pnl']:.2f}")
    print(f"🎯 Win rate: {results['win_rate']:.1f}%")
    print(f"📊 PnL promedio: ${results['average_pnl_per_trade']:.2f}")
    print(f"🔄 Total reinvertido: ${results['total_reinvested']:.2f}")
    print(f"💎 Capital base actual: ${results['base_capital']:.2f}")
    
    # Análisis de rendimiento
    if results['total_roi'] > 0:
        # Proyección mensual (asumiendo que cada ciclo = 1 día)
        daily_roi = results['total_roi'] / results['cycles_completed']
        monthly_projection = daily_roi * 30
        
        print(f"\n📊 === PROYECCIÓN MENSUAL ===")
        print(f"📈 ROI diario promedio: {daily_roi:.3f}%")
        print(f"🎯 ROI mensual proyectado: {monthly_projection:.2f}%")
        
        if monthly_projection >= 5.0:
            print("✅ ¡OBJETIVO DE 5% MENSUAL ALCANZABLE!")
        else:
            optimizacion_necesaria = 5.0 - monthly_projection
            print(f"📈 Necesita {optimizacion_necesaria:.2f}% adicional para alcanzar objetivo")
            
        # Proyección con reinversión
        if results['total_reinvested'] > 0:
            print(f"💰 Reinversión activa: ${results['total_reinvested']:.2f}")
            print(f"🚀 Crecimiento exponencial en progreso")
    
    # Guardar resultados
    with open('sicar_capital_variable_final_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Guardar resumen de rendimiento
    summary = system.get_performance_summary()
    with open('sicar_performance_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\n💾 Resultados guardados en archivos JSON")
    
    # Recomendaciones
    print(f"\n🔧 === RECOMENDACIONES ===")
    if results['win_rate'] < 60:
        print("📊 Optimizar filtros de señales para mejorar win rate")
    if results['average_pnl_per_trade'] < 2:
        print("💰 Ajustar gestión de posiciones para mayor PnL promedio")
    if results['total_trades'] < 10:
        print("🔄 Aumentar frecuencia de trading con señales más sensibles")
    if monthly_projection < 5:
        print("🎯 Implementar estrategias adicionales para alcanzar 5% mensual")
    
    return system, results

if __name__ == "__main__":
    run_final_demo()