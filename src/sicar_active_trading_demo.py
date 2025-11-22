#!/usr/bin/env python3
"""
Demo Activo del Sistema SICAR con Capital Variable
Configuración optimizada para generar más actividad de trading
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import os
import time

class SicarActiveTradingDemo:
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
        
        # Configuración de riesgo (más agresiva para demo)
        self.max_position_size = 0.30  # 30% máximo por posición
        self.min_confidence = 0.25     # Confianza mínima reducida
        self.max_positions = 4         # Máximo 4 posiciones simultáneas
        
        # Configuración de mercado
        self.market_volatility = 0.025  # Volatilidad base
        self.trend_strength = 0.002     # Fuerza de tendencia
        
        print(f"🚀 Sistema SICAR Activo inicializado")
        print(f"💰 Capital inicial: ${self.current_capital:.2f}")
        print(f"📊 Símbolos: {', '.join(self.symbols)}")
        print(f"⚙️ Confianza mínima: {self.min_confidence:.0%}")
        print(f"📈 Tamaño máximo posición: {self.max_position_size:.0%}")
        
    def generate_realistic_market_data(self, symbol: str, periods: int = 50) -> pd.DataFrame:
        """Genera datos de mercado más realistas y volátiles"""
        
        # Precios base
        base_prices = {
            'BTCUSDT': 43000 + np.random.uniform(-2000, 2000),
            'ETHUSDT': 2600 + np.random.uniform(-200, 200),
            'ADAUSDT': 0.42 + np.random.uniform(-0.05, 0.05),
            'DOTUSDT': 6.2 + np.random.uniform(-0.8, 0.8)
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generar movimientos más dinámicos
        np.random.seed(int(time.time() * 1000) % 10000 + hash(symbol) % 1000)
        
        prices = [base_price]
        volumes = []
        
        # Crear tendencias y reversiones
        trend_direction = np.random.choice([-1, 1])
        trend_strength = np.random.uniform(0.001, 0.003)
        
        for i in range(periods - 1):
            # Movimiento base con tendencia
            base_move = trend_direction * trend_strength
            
            # Ruido aleatorio
            noise = np.random.normal(0, self.market_volatility)
            
            # Reversiones ocasionales
            if np.random.random() < 0.15:  # 15% probabilidad de reversión
                base_move *= -2
                
            # Breakouts ocasionales
            if np.random.random() < 0.08:  # 8% probabilidad de breakout
                noise += np.random.choice([-1, 1]) * np.random.uniform(0.02, 0.04)
            
            # Cambio de tendencia gradual
            if i % 15 == 0:
                trend_direction *= np.random.choice([-1, 1])
                trend_strength = np.random.uniform(0.001, 0.003)
            
            daily_return = base_move + noise
            new_price = prices[-1] * (1 + daily_return)
            
            # Evitar precios negativos
            new_price = max(new_price, base_price * 0.7)
            prices.append(new_price)
            
            # Volumen correlacionado con movimiento
            volume_base = np.random.uniform(800000, 3000000)
            volume_multiplier = 1 + abs(daily_return) * 20
            volumes.append(volume_base * volume_multiplier)
        
        volumes.append(volumes[-1] if volumes else 1000000)
        
        # Crear DataFrame
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='1H')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.008))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.008))) for p in prices],
            'close': prices,
            'volume': volumes
        })
        
        return df
    
    def calculate_enhanced_indicators(self, df: pd.DataFrame) -> Dict:
        """Calcula indicadores técnicos mejorados"""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values
        
        if len(close) < 20:
            return {'error': 'insufficient_data'}
        
        # Medias móviles
        sma_5 = np.mean(close[-5:])
        sma_10 = np.mean(close[-10:])
        sma_20 = np.mean(close[-20:])
        
        # EMA más responsivas
        ema_8 = self._calculate_ema(close, 8)
        ema_21 = self._calculate_ema(close, 21)
        
        # RSI
        rsi = self._calculate_rsi(close, 14)
        
        # MACD
        macd_line = ema_8 - ema_21
        macd_signal = self._calculate_ema([macd_line] if isinstance(macd_line, (int, float)) else close[-9:], 9)
        
        # Bollinger Bands
        bb_middle = sma_20
        bb_std = np.std(close[-20:])
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        
        # Volatilidad
        returns = np.diff(close[-10:]) / close[-11:-1]
        volatility = np.std(returns)
        
        # Momentum
        momentum = (close[-1] - close[-5]) / close[-5] if len(close) >= 5 else 0
        
        # Volume analysis
        avg_volume = np.mean(volume[-10:])
        volume_ratio = volume[-1] / avg_volume if avg_volume > 0 else 1
        
        # Price position
        current_price = close[-1]
        price_range = np.max(close[-20:]) - np.min(close[-20:])
        price_position = (current_price - np.min(close[-20:])) / price_range if price_range > 0 else 0.5
        
        # Trend strength
        trend_strength = abs(sma_5 - sma_20) / sma_20 if sma_20 > 0 else 0
        
        return {
            'current_price': current_price,
            'sma_5': sma_5,
            'sma_10': sma_10,
            'sma_20': sma_20,
            'ema_8': ema_8,
            'ema_21': ema_21,
            'rsi': rsi,
            'macd_line': macd_line,
            'macd_signal': macd_signal,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'volatility': volatility,
            'momentum': momentum,
            'volume_ratio': volume_ratio,
            'price_position': price_position,
            'trend_strength': trend_strength
        }
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calcula EMA"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = np.mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calcula RSI"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_enhanced_signal(self, symbol: str, indicators: Dict) -> Dict:
        """Genera señales más sensibles y activas"""
        
        signal = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'action': 'hold',
            'confidence': 0.0,
            'reasons': [],
            'price': indicators['current_price'],
            'volatility': indicators['volatility']
        }
        
        # Sistema de puntuación más sensible
        score = 0
        max_score = 0
        reasons = []
        
        # 1. Tendencia múltiple (peso alto)
        max_score += 3
        if indicators['sma_5'] > indicators['sma_10'] > indicators['sma_20']:
            score += 3
            reasons.append('strong_bullish_trend')
        elif indicators['sma_5'] > indicators['sma_10']:
            score += 2
            reasons.append('bullish_trend')
        elif indicators['sma_5'] < indicators['sma_10'] < indicators['sma_20']:
            score -= 2
            reasons.append('strong_bearish_trend')
        elif indicators['sma_5'] < indicators['sma_10']:
            score -= 1
            reasons.append('bearish_trend')
        
        # 2. EMA crossover (peso medio)
        max_score += 2
        if indicators['ema_8'] > indicators['ema_21']:
            score += 2
            reasons.append('ema_bullish')
        else:
            score -= 1
            reasons.append('ema_bearish')
        
        # 3. RSI (más permisivo)
        max_score += 2
        rsi = indicators['rsi']
        if 25 < rsi < 75:
            score += 2
            reasons.append('rsi_good_range')
        elif rsi < 35:
            score += 1.5
            reasons.append('rsi_oversold_opportunity')
        elif rsi > 65:
            score += 0.5
            reasons.append('rsi_momentum')
        
        # 4. MACD
        max_score += 2
        if isinstance(indicators['macd_line'], (int, float)) and isinstance(indicators['macd_signal'], (int, float)):
            if indicators['macd_line'] > indicators['macd_signal']:
                score += 2
                reasons.append('macd_bullish')
            else:
                score -= 0.5
                reasons.append('macd_bearish')
        
        # 5. Momentum
        max_score += 1
        momentum = indicators['momentum']
        if momentum > 0.01:
            score += 1
            reasons.append('positive_momentum')
        elif momentum < -0.01:
            score -= 0.5
            reasons.append('negative_momentum')
        
        # 6. Volume
        max_score += 1
        if indicators['volume_ratio'] > 1.1:
            score += 1
            reasons.append('volume_support')
        
        # 7. Volatilidad (oportunidad)
        max_score += 1
        if 0.015 < indicators['volatility'] < 0.04:
            score += 1
            reasons.append('good_volatility')
        
        # 8. Posición de precio
        max_score += 1
        price_pos = indicators['price_position']
        if 0.2 < price_pos < 0.8:
            score += 1
            reasons.append('good_price_level')
        
        # Calcular confianza
        confidence = max(0, min(1, score / max_score)) if max_score > 0 else 0
        
        # Determinar acción (más agresivo)
        if confidence > 0.4 and score > 2:
            signal['action'] = 'buy'
        elif confidence > 0.35 and score < -1:
            signal['action'] = 'sell'
        else:
            signal['action'] = 'hold'
        
        signal['confidence'] = confidence
        signal['reasons'] = reasons
        signal['score'] = score
        signal['max_score'] = max_score
        
        return signal
    
    def calculate_dynamic_position_size(self, symbol: str, confidence: float, volatility: float) -> float:
        """Calcula tamaño de posición dinámico"""
        
        # Tamaño base más agresivo
        base_size = self.available_capital * self.max_position_size
        
        # Multiplicador por confianza (más agresivo)
        confidence_multiplier = 0.5 + (confidence * 1.5)
        
        # Ajuste por volatilidad
        volatility_multiplier = max(0.6, 1.2 - (volatility * 20))
        
        # Ajuste por posiciones activas
        position_multiplier = max(0.6, 1.0 - (len(self.active_positions) * 0.1))
        
        # Calcular tamaño final
        position_size = base_size * confidence_multiplier * volatility_multiplier * position_multiplier
        
        # Límites
        min_size = 12.0  # Mínimo $12
        max_size = self.available_capital * 0.45  # Máximo 45%
        
        position_size = max(min_size, min(position_size, max_size))
        
        return position_size
    
    def execute_trade(self, signal: Dict) -> Optional[Dict]:
        """Ejecuta trades con lógica mejorada"""
        
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
            position_size = self.calculate_dynamic_position_size(symbol, confidence, volatility)
            
            if position_size > self.available_capital:
                return None
            
            quantity = position_size / price
            
            # Stop loss y take profit dinámicos
            stop_loss_pct = max(0.03, min(0.08, volatility * 2))  # 3-8%
            take_profit_pct = max(0.06, min(0.15, volatility * 3))  # 6-15%
            
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
            print(f"🟢 BUY {symbol}: ${position_size:.2f} at ${price:.4f} (Conf: {confidence:.1%}, SL: {stop_loss_pct:.1%}, TP: {take_profit_pct:.1%})")
            
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
                print(f"🛑 STOP LOSS activado para {symbol}")
            
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
                print(f"🎯 TAKE PROFIT activado para {symbol}")
    
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
    
    def run_active_demo(self, cycles: int = 20) -> Dict:
        """Ejecuta demo activo con múltiples ciclos"""
        
        print(f"\n🚀 Iniciando demo activo - {cycles} ciclos de trading")
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
                    market_data = self.generate_realistic_market_data(symbol, 50)
                    
                    # Calcular indicadores
                    indicators = self.calculate_enhanced_indicators(market_data)
                    
                    if 'error' in indicators:
                        continue
                    
                    # Generar señal
                    signal = self.generate_enhanced_signal(symbol, indicators)
                    signals_generated += 1
                    
                    print(f"📊 {symbol}: {signal['action'].upper()} (Conf: {signal['confidence']:.1%}, Score: {signal['score']:.1f}/{signal['max_score']})")
                    
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
            time.sleep(0.2)
        
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
            'base_capital': self.base_capital
        }
        
        return results

def run_active_demo():
    """Ejecuta demo activo completo"""
    
    print("🎯 === DEMO ACTIVO SICAR CAPITAL VARIABLE ===")
    print("⚙️ Configuración optimizada para máxima actividad")
    
    # Crear sistema
    system = SicarActiveTradingDemo(
        initial_capital=200.0,
        max_capital=500.0,
        symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT'],
        reinvestment_threshold=0.05
    )
    
    # Ejecutar demo
    results = system.run_active_demo(cycles=25)
    
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
    print(f"📊 Posiciones activas: {results['active_positions']}")
    print(f"🔄 Total reinvertido: ${results['total_reinvested']:.2f}")
    print(f"💎 Capital base actual: ${results['base_capital']:.2f}")
    
    # Análisis de rendimiento
    if results['total_roi'] > 0:
        monthly_projection = results['total_roi'] * 30  # Proyección mensual
        print(f"\n📊 === PROYECCIÓN MENSUAL ===")
        print(f"🎯 ROI mensual proyectado: {monthly_projection:.2f}%")
        
        if monthly_projection >= 5.0:
            print("✅ ¡OBJETIVO DE 5% MENSUAL ALCANZABLE!")
        else:
            print(f"📈 Necesita {5.0 - monthly_projection:.2f}% adicional para alcanzar objetivo")
    
    # Guardar resultados
    with open('sicar_active_demo_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Resultados guardados en 'sicar_active_demo_results.json'")
    
    return system, results

if __name__ == "__main__":
    run_active_demo()