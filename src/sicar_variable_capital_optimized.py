#!/usr/bin/env python3
"""
Sistema SICAR Optimizado con Capital Variable
Versión independiente con reinversión automática y gestión de riesgo avanzada
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import os
import time

class SicarVariableCapitalOptimized:
    def __init__(self, 
                 initial_capital: float = 200.0,
                 max_capital: float = 500.0,
                 symbols: List[str] = None,
                 reinvestment_threshold: float = 0.05):
        
        # Configuración
        if symbols is None:
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'BNBUSDT']
        
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.max_capital = max_capital
        self.reinvestment_threshold = reinvestment_threshold
        
        # Estado del capital
        self.current_capital = initial_capital
        self.base_capital = initial_capital  # Capital base actual (se incrementa con reinversión)
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
        self.min_confidence = 0.4      # Confianza mínima para trade
        self.max_positions = 3         # Máximo 3 posiciones simultáneas
        
        # Logger
        self.logger = self._setup_logger()
        
        # Cargar estado si existe
        self._load_state()
        
    def _setup_logger(self):
        """Configurar logging"""
        logger = logging.getLogger('SicarVariableCapitalOptimized')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('sicar_variable_capital_optimized.log')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def generate_market_data(self, symbol: str, periods: int = 100) -> pd.DataFrame:
        """Genera datos de mercado realistas para backtesting"""
        
        # Precios base realistas
        base_prices = {
            'BTCUSDT': 45000 + np.random.uniform(-5000, 5000),
            'ETHUSDT': 2800 + np.random.uniform(-300, 300),
            'ADAUSDT': 0.45 + np.random.uniform(-0.1, 0.1),
            'DOTUSDT': 6.5 + np.random.uniform(-1, 1),
            'BNBUSDT': 320 + np.random.uniform(-50, 50)
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generar serie temporal con tendencia y volatilidad
        np.random.seed(int(time.time()) + hash(symbol) % 1000)
        
        # Parámetros de mercado
        trend = np.random.uniform(-0.0005, 0.001)  # Tendencia diaria
        volatility = np.random.uniform(0.015, 0.035)  # Volatilidad
        
        prices = [base_price]
        volumes = []
        
        for i in range(periods - 1):
            # Movimiento con tendencia y ruido
            daily_return = trend + np.random.normal(0, volatility)
            
            # Añadir algunos breakouts ocasionales
            if np.random.random() < 0.05:  # 5% probabilidad de breakout
                daily_return += np.random.choice([-1, 1]) * np.random.uniform(0.02, 0.05)
            
            new_price = prices[-1] * (1 + daily_return)
            prices.append(max(new_price, base_price * 0.5))  # Evitar precios negativos
            
            # Volumen correlacionado con volatilidad
            volume = np.random.uniform(1000000, 5000000) * (1 + abs(daily_return) * 10)
            volumes.append(volume)
        
        volumes.append(volumes[-1] if volumes else 1000000)
        
        # Crear DataFrame
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='1H')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            'close': prices,
            'volume': volumes
        })
        
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Calcula indicadores técnicos avanzados"""
        close = df['close'].values
        high = df['high'].values
        low = df['low'].values
        volume = df['volume'].values
        
        if len(close) < 20:
            return {'error': 'insufficient_data'}
        
        # Medias móviles
        sma_5 = np.mean(close[-5:])
        sma_20 = np.mean(close[-20:])
        ema_12 = self._calculate_ema(close, 12)
        ema_26 = self._calculate_ema(close, 26)
        
        # RSI
        rsi = self._calculate_rsi(close, 14)
        
        # MACD
        macd_line = ema_12 - ema_26
        macd_signal = self._calculate_ema([macd_line], 9) if isinstance(macd_line, (int, float)) else macd_line
        
        # Bollinger Bands
        bb_middle = sma_20
        bb_std = np.std(close[-20:])
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)
        
        # Volatilidad
        returns = np.diff(close[-20:]) / close[-21:-1]
        volatility = np.std(returns)
        
        # Volume analysis
        avg_volume = np.mean(volume[-20:])
        volume_ratio = volume[-1] / avg_volume if avg_volume > 0 else 1
        
        # Support/Resistance
        recent_highs = high[-10:]
        recent_lows = low[-10:]
        resistance = np.max(recent_highs)
        support = np.min(recent_lows)
        
        current_price = close[-1]
        
        return {
            'current_price': current_price,
            'sma_5': sma_5,
            'sma_20': sma_20,
            'ema_12': ema_12,
            'ema_26': ema_26,
            'rsi': rsi,
            'macd_line': macd_line,
            'macd_signal': macd_signal,
            'bb_upper': bb_upper,
            'bb_middle': bb_middle,
            'bb_lower': bb_lower,
            'volatility': volatility,
            'volume_ratio': volume_ratio,
            'resistance': resistance,
            'support': support,
            'price_position': (current_price - support) / (resistance - support) if resistance > support else 0.5
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
    
    def generate_trading_signal(self, symbol: str, indicators: Dict) -> Dict:
        """Genera señal de trading basada en múltiples indicadores"""
        
        signal = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'action': 'hold',
            'confidence': 0.0,
            'reasons': [],
            'price': indicators['current_price'],
            'volatility': indicators['volatility']
        }
        
        # Puntuación de señal
        score = 0
        max_score = 0
        reasons = []
        
        # 1. Tendencia (SMA)
        max_score += 2
        if indicators['sma_5'] > indicators['sma_20']:
            score += 2
            reasons.append('bullish_sma_trend')
        elif indicators['sma_5'] < indicators['sma_20']:
            score -= 1
            reasons.append('bearish_sma_trend')
        
        # 2. MACD
        max_score += 2
        if isinstance(indicators['macd_line'], (int, float)) and isinstance(indicators['macd_signal'], (int, float)):
            if indicators['macd_line'] > indicators['macd_signal']:
                score += 2
                reasons.append('bullish_macd')
            else:
                score -= 1
                reasons.append('bearish_macd')
        
        # 3. RSI
        max_score += 2
        rsi = indicators['rsi']
        if 30 < rsi < 70:
            score += 2
            reasons.append('rsi_neutral_good')
        elif rsi < 30:
            score += 1
            reasons.append('rsi_oversold')
        elif rsi > 80:
            score -= 2
            reasons.append('rsi_overbought')
        
        # 4. Bollinger Bands
        max_score += 1
        price = indicators['current_price']
        if indicators['bb_lower'] < price < indicators['bb_upper']:
            score += 1
            reasons.append('price_within_bb')
        elif price <= indicators['bb_lower']:
            score += 0.5
            reasons.append('price_near_bb_lower')
        
        # 5. Volume
        max_score += 1
        if indicators['volume_ratio'] > 1.2:
            score += 1
            reasons.append('high_volume')
        elif indicators['volume_ratio'] < 0.8:
            score -= 0.5
            reasons.append('low_volume')
        
        # 6. Posición de precio
        max_score += 1
        price_pos = indicators['price_position']
        if 0.3 < price_pos < 0.7:
            score += 1
            reasons.append('good_price_position')
        
        # Calcular confianza y acción
        confidence = max(0, min(1, score / max_score)) if max_score > 0 else 0
        
        # Determinar acción
        if confidence > 0.6 and score > 0:
            signal['action'] = 'buy'
        elif confidence > 0.5 and score < -2:
            signal['action'] = 'sell'
        else:
            signal['action'] = 'hold'
        
        signal['confidence'] = confidence
        signal['reasons'] = reasons
        signal['score'] = score
        signal['max_score'] = max_score
        
        return signal
    
    def calculate_position_size(self, symbol: str, confidence: float, volatility: float) -> float:
        """Calcula tamaño de posición óptimo"""
        
        # Tamaño base
        base_size = self.available_capital * self.max_position_size
        
        # Ajustar por confianza
        confidence_multiplier = confidence
        
        # Ajustar por volatilidad (reducir en alta volatilidad)
        volatility_multiplier = max(0.5, 1.0 - (volatility * 15))
        
        # Ajustar por número de posiciones activas
        position_multiplier = max(0.7, 1.0 - (len(self.active_positions) * 0.15))
        
        # Calcular tamaño final
        position_size = base_size * confidence_multiplier * volatility_multiplier * position_multiplier
        
        # Límites
        min_size = 15.0  # Mínimo $15
        max_size = self.available_capital * 0.4  # Máximo 40%
        
        position_size = max(min_size, min(position_size, max_size))
        
        return position_size
    
    def execute_trade(self, signal: Dict) -> Optional[Dict]:
        """Ejecuta un trade basado en la señal"""
        
        symbol = signal['symbol']
        action = signal['action']
        price = signal['price']
        confidence = signal['confidence']
        volatility = signal['volatility']
        
        # Filtros de calidad
        if confidence < self.min_confidence:
            return None
        
        if action == 'buy':
            # Verificar si ya tenemos posición
            if symbol in self.active_positions:
                return None
            
            # Verificar límite de posiciones
            if len(self.active_positions) >= self.max_positions:
                return None
            
            # Calcular tamaño de posición
            position_size = self.calculate_position_size(symbol, confidence, volatility)
            
            if position_size > self.available_capital:
                return None
            
            quantity = position_size / price
            
            # Ejecutar compra
            self.active_positions[symbol] = {
                'entry_price': price,
                'quantity': quantity,
                'position_size': position_size,
                'entry_time': datetime.now(),
                'confidence': confidence,
                'stop_loss': price * 0.95,  # 5% stop loss
                'take_profit': price * 1.10  # 10% take profit
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
                'available_capital_after': self.available_capital
            }
            
            self.trade_history.append(trade)
            self.logger.info(f"BUY {symbol}: ${position_size:.2f} at ${price:.4f} (Confidence: {confidence:.2f})")
            
            return trade
        
        elif action == 'sell':
            # Verificar si tenemos posición
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
            
            # Actualizar estadísticas
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
            self.logger.info(f"SELL {symbol}: PnL ${pnl:.2f} ({pnl_percentage:.2f}%) - Capital: ${self.current_capital:.2f}")
            
            # Verificar reinversión
            self._check_reinvestment()
            
            return trade
        
        return None
    
    def _check_reinvestment(self):
        """Verifica y ejecuta reinversión automática"""
        
        current_roi = (self.current_capital - self.base_capital) / self.base_capital
        
        if current_roi >= self.reinvestment_threshold and self.base_capital < self.max_capital:
            
            # Calcular reinversión
            profit = self.current_capital - self.base_capital
            max_reinvestment = self.max_capital - self.base_capital
            reinvestment = min(profit, max_reinvestment)
            
            if reinvestment >= 20:  # Mínimo $20 para reinvertir
                
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
                self.logger.info(f"REINVESTMENT: ${reinvestment:.2f} - New base capital: ${self.base_capital:.2f}")
    
    def run_trading_session(self, duration_hours: int = 24) -> Dict:
        """Ejecuta una sesión de trading"""
        
        session_start = datetime.now()
        session_results = {
            'start_time': session_start.isoformat(),
            'duration_hours': duration_hours,
            'initial_capital': self.current_capital,
            'trades_executed': 0,
            'signals_generated': 0,
            'symbols_processed': len(self.symbols)
        }
        
        self.logger.info(f"Starting trading session - Duration: {duration_hours}h, Capital: ${self.current_capital:.2f}")
        
        # Simular trading por horas
        for hour in range(duration_hours):
            
            # Procesar cada símbolo
            for symbol in self.symbols:
                try:
                    # Generar datos de mercado
                    market_data = self.generate_market_data(symbol, 100)
                    
                    # Calcular indicadores
                    indicators = self.calculate_technical_indicators(market_data)
                    
                    if 'error' in indicators:
                        continue
                    
                    # Generar señal
                    signal = self.generate_trading_signal(symbol, indicators)
                    session_results['signals_generated'] += 1
                    
                    # Ejecutar trade si es necesario
                    trade = self.execute_trade(signal)
                    if trade:
                        session_results['trades_executed'] += 1
                    
                    # Verificar stop-loss y take-profit para posiciones activas
                    self._check_stop_loss_take_profit(symbol, indicators['current_price'])
                    
                except Exception as e:
                    self.logger.error(f"Error processing {symbol}: {e}")
            
            # Simular paso del tiempo
            time.sleep(0.1)  # Pequeña pausa para simular
        
        # Resultados finales
        session_results.update({
            'end_time': datetime.now().isoformat(),
            'final_capital': self.current_capital,
            'capital_change': self.current_capital - session_results['initial_capital'],
            'roi_session': ((self.current_capital - session_results['initial_capital']) / 
                           session_results['initial_capital']) * 100,
            'active_positions': len(self.active_positions),
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0,
            'total_pnl': self.total_pnl
        })
        
        self.performance_history.append(session_results)
        self._save_state()
        
        self.logger.info(f"Session completed - Capital: ${self.current_capital:.2f}, "
                        f"ROI: {session_results['roi_session']:.2f}%, "
                        f"Trades: {session_results['trades_executed']}")
        
        return session_results
    
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
            self.execute_trade(signal)
            
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
            self.execute_trade(signal)
    
    def get_performance_report(self) -> Dict:
        """Genera reporte completo de rendimiento"""
        
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
            'risk_metrics': {
                'max_position_size_percentage': self.max_position_size * 100,
                'current_positions_count': len(self.active_positions),
                'max_positions_allowed': self.max_positions,
                'capital_utilization': ((self.current_capital - self.available_capital) / self.current_capital * 100) if self.current_capital > 0 else 0
            },
            'reinvestment_status': {
                'next_reinvestment_threshold': self.reinvestment_threshold * 100,
                'current_cycle_roi': ((self.current_capital - self.base_capital) / self.base_capital * 100) if self.base_capital > 0 else 0,
                'amount_to_next_reinvestment': max(0, (self.base_capital * self.reinvestment_threshold) - (self.current_capital - self.base_capital))
            },
            'recent_trades': self.trade_history[-10:],  # Últimos 10 trades
            'active_positions_detail': self.active_positions
        }
    
    def _save_state(self):
        """Guarda estado del sistema"""
        state = {
            'config': {
                'initial_capital': self.initial_capital,
                'max_capital': self.max_capital,
                'reinvestment_threshold': self.reinvestment_threshold,
                'symbols': self.symbols
            },
            'current_state': {
                'current_capital': self.current_capital,
                'base_capital': self.base_capital,
                'available_capital': self.available_capital,
                'total_reinvested': self.total_reinvested,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'total_pnl': self.total_pnl
            },
            'active_positions': self.active_positions,
            'trade_history': self.trade_history,
            'performance_history': self.performance_history,
            'last_updated': datetime.now().isoformat()
        }
        
        with open('sicar_variable_capital_optimized_state.json', 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    def _load_state(self):
        """Carga estado previo"""
        try:
            with open('sicar_variable_capital_optimized_state.json', 'r') as f:
                state = json.load(f)
            
            current = state.get('current_state', {})
            self.current_capital = current.get('current_capital', self.initial_capital)
            self.base_capital = current.get('base_capital', self.initial_capital)
            self.available_capital = current.get('available_capital', self.initial_capital)
            self.total_reinvested = current.get('total_reinvested', 0.0)
            self.total_trades = current.get('total_trades', 0)
            self.winning_trades = current.get('winning_trades', 0)
            self.total_pnl = current.get('total_pnl', 0.0)
            
            self.active_positions = state.get('active_positions', {})
            self.trade_history = state.get('trade_history', [])
            self.performance_history = state.get('performance_history', [])
            
            self.logger.info("State loaded successfully")
            
        except FileNotFoundError:
            self.logger.info("No previous state found, starting fresh")
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")

def run_comprehensive_demo():
    """Demo completo del sistema optimizado"""
    print("=== SICAR CAPITAL VARIABLE OPTIMIZADO ===")
    print("Configuración: 200-500 USDT, Reinversión automática al 5% ROI")
    
    # Crear sistema
    system = SicarVariableCapitalOptimized(
        initial_capital=200.0,
        max_capital=500.0,
        symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT'],
        reinvestment_threshold=0.05
    )
    
    print(f"\nCapital inicial: ${system.current_capital:.2f}")
    print(f"Capital base: ${system.base_capital:.2f}")
    print(f"Total reinvertido: ${system.total_reinvested:.2f}")
    
    # Ejecutar sesión de trading
    print("\n--- Ejecutando sesión de trading de 48 horas ---")
    session_results = system.run_trading_session(duration_hours=48)
    
    print(f"\nResultados de la sesión:")
    print(f"Señales generadas: {session_results['signals_generated']}")
    print(f"Trades ejecutados: {session_results['trades_executed']}")
    print(f"Capital final: ${session_results['final_capital']:.2f}")
    print(f"ROI sesión: {session_results['roi_session']:.2f}%")
    print(f"Win rate: {session_results['win_rate']:.1f}%")
    
    # Reporte completo
    report = system.get_performance_report()
    
    print(f"\n=== REPORTE COMPLETO ===")
    print(f"Capital inicial: ${report['capital_summary']['initial_capital']:.2f}")
    print(f"Capital actual: ${report['capital_summary']['current_capital']:.2f}")
    print(f"ROI total: {report['capital_summary']['total_roi_percentage']:.2f}%")
    print(f"Total reinvertido: ${report['capital_summary']['total_reinvested']:.2f}")
    print(f"Crecimiento: ${report['capital_summary']['capital_growth']:.2f}")
    
    print(f"\nTrades totales: {report['trading_performance']['total_trades']}")
    print(f"Win rate: {report['trading_performance']['win_rate_percentage']:.1f}%")
    print(f"PnL total: ${report['trading_performance']['total_pnl']:.2f}")
    print(f"PnL promedio: ${report['trading_performance']['average_pnl_per_trade']:.2f}")
    
    print(f"\nPosiciones activas: {report['trading_performance']['active_positions']}")
    print(f"Utilización capital: {report['risk_metrics']['capital_utilization']:.1f}%")
    
    print(f"\nPróxima reinversión en: {report['reinvestment_status']['next_reinvestment_threshold']:.1f}% ROI")
    print(f"ROI ciclo actual: {report['reinvestment_status']['current_cycle_roi']:.2f}%")
    print(f"Falta para reinversión: ${report['reinvestment_status']['amount_to_next_reinvestment']:.2f}")
    
    # Guardar reporte
    with open('sicar_variable_capital_optimized_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n✅ Reporte completo guardado en 'sicar_variable_capital_optimized_report.json'")
    
    # Proyección a 30 días
    print(f"\n=== PROYECCIÓN 30 DÍAS ===")
    if session_results['roi_session'] > 0:
        daily_roi = session_results['roi_session'] / 2  # 48h = 2 días
        monthly_roi = daily_roi * 30
        projected_capital = system.current_capital * (1 + monthly_roi / 100)
        
        print(f"ROI diario estimado: {daily_roi:.2f}%")
        print(f"ROI mensual proyectado: {monthly_roi:.2f}%")
        print(f"Capital proyectado (30 días): ${projected_capital:.2f}")
        
        if monthly_roi >= 5.0:
            print("🎯 ¡OBJETIVO DE 5% MENSUAL ALCANZABLE!")
        else:
            print(f"📈 Necesita optimización para alcanzar 5% mensual")
    
    return system

if __name__ == "__main__":
    run_comprehensive_demo()