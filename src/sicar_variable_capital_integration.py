#!/usr/bin/env python3
"""
Integración SICAR con Sistema de Capital Variable
Combina las señales SICAR con gestión de capital variable y reinversión automática
"""

import sys
import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional

# Importar sistema de capital variable
from variable_capital_system import VariableCapitalManager

# Importar componentes SICAR existentes
try:
    from ensemble_sicar_system import EnsembleSicarSystem
    from binance_data_provider import BinanceDataProvider
    from enhanced_logger import EnhancedLogger
except ImportError as e:
    print(f"Warning: Could not import SICAR components: {e}")

class SicarVariableCapitalSystem:
    def __init__(self, 
                 min_capital: float = 200.0,
                 max_capital: float = 500.0,
                 symbols: List[str] = None,
                 timeframe: str = '1h'):
        
        # Configuración por defecto
        if symbols is None:
            symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'BNBUSDT']
        
        self.symbols = symbols
        self.timeframe = timeframe
        
        # Inicializar sistema de capital variable
        self.capital_manager = VariableCapitalManager(
            min_capital=min_capital,
            max_capital=max_capital,
            reinvestment_threshold=0.05,  # 5% para reinvertir
            max_position_size=0.20        # 20% máximo por posición
        )
        
        # Inicializar componentes SICAR
        try:
            self.sicar_system = EnsembleSicarSystem()
            self.data_provider = BinanceDataProvider()
        except:
            print("Warning: SICAR components not available, using simulation mode")
            self.sicar_system = None
            self.data_provider = None
        
        # Estado del sistema
        self.active_positions = {}
        self.signal_history = []
        self.performance_metrics = {}
        
        # Logger
        self.logger = self._setup_logger()
        
        # Cargar estado previo si existe
        self.capital_manager.load_state('sicar_variable_capital_state.json')
        
    def _setup_logger(self):
        """Configurar logging"""
        logger = logging.getLogger('SicarVariableCapital')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('sicar_variable_capital.log')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def get_market_data(self, symbol: str, limit: int = 100) -> pd.DataFrame:
        """Obtiene datos de mercado para análisis"""
        if self.data_provider:
            try:
                return self.data_provider.get_historical_data(symbol, self.timeframe, limit)
            except Exception as e:
                self.logger.error(f"Error getting data for {symbol}: {e}")
                return self._generate_mock_data(symbol, limit)
        else:
            return self._generate_mock_data(symbol, limit)
    
    def _generate_mock_data(self, symbol: str, limit: int) -> pd.DataFrame:
        """Genera datos simulados para testing"""
        dates = pd.date_range(end=datetime.now(), periods=limit, freq='1H')
        
        # Precio base según símbolo
        base_prices = {
            'BTCUSDT': 45000,
            'ETHUSDT': 2800,
            'ADAUSDT': 0.45,
            'DOTUSDT': 6.5,
            'BNBUSDT': 320
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generar datos con tendencia y volatilidad
        np.random.seed(hash(symbol) % 1000)
        returns = np.random.normal(0.0001, 0.02, limit)  # Retornos con drift positivo
        prices = [base_price]
        
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(new_price)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000000, 5000000, limit)
        })
        
        return df
    
    def analyze_signal(self, symbol: str, data: pd.DataFrame) -> Dict:
        """Analiza señales de trading para un símbolo"""
        if self.sicar_system:
            try:
                # Usar sistema SICAR real
                signal = self.sicar_system.generate_signal(symbol, data)
                return signal
            except Exception as e:
                self.logger.error(f"Error in SICAR analysis for {symbol}: {e}")
                return self._generate_mock_signal(symbol, data)
        else:
            return self._generate_mock_signal(symbol, data)
    
    def _generate_mock_signal(self, symbol: str, data: pd.DataFrame) -> Dict:
        """Genera señal simulada basada en análisis técnico simple"""
        if len(data) < 20:
            return {'action': 'hold', 'confidence': 0.0, 'reason': 'insufficient_data'}
        
        # Calcular indicadores básicos
        close_prices = data['close'].values
        sma_20 = np.mean(close_prices[-20:])
        sma_5 = np.mean(close_prices[-5:])
        current_price = close_prices[-1]
        
        # RSI simple
        gains = []
        losses = []
        for i in range(1, min(15, len(close_prices))):
            change = close_prices[i] - close_prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0.001
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Volatilidad
        returns = np.diff(close_prices[-20:]) / close_prices[-21:-1]
        volatility = np.std(returns)
        
        # Generar señal
        signal = {'symbol': symbol, 'timestamp': datetime.now().isoformat()}
        
        # Lógica de señales
        if sma_5 > sma_20 and rsi < 70 and current_price > sma_5:
            signal.update({
                'action': 'buy',
                'confidence': min(0.8, 0.4 + (sma_5 - sma_20) / sma_20 * 10),
                'reason': 'bullish_trend_rsi_ok',
                'price': current_price,
                'volatility': volatility,
                'rsi': rsi
            })
        elif sma_5 < sma_20 or rsi > 80:
            signal.update({
                'action': 'sell',
                'confidence': min(0.8, 0.4 + abs(sma_5 - sma_20) / sma_20 * 10),
                'reason': 'bearish_trend_or_overbought',
                'price': current_price,
                'volatility': volatility,
                'rsi': rsi
            })
        else:
            signal.update({
                'action': 'hold',
                'confidence': 0.3,
                'reason': 'neutral_conditions',
                'price': current_price,
                'volatility': volatility,
                'rsi': rsi
            })
        
        return signal
    
    def process_signal(self, signal: Dict) -> Optional[Dict]:
        """Procesa una señal y ejecuta trades si es necesario"""
        symbol = signal['symbol']
        action = signal['action']
        confidence = signal.get('confidence', 0.5)
        price = signal.get('price', 0)
        volatility = signal.get('volatility', 0.02)
        
        # Filtros de calidad de señal
        if confidence < 0.4:
            self.logger.info(f"Signal rejected for {symbol}: low confidence ({confidence:.2f})")
            return None
        
        # Verificar si ya tenemos posición
        has_position = symbol in self.active_positions
        
        trade_result = None
        
        if action == 'buy' and not has_position:
            # Abrir posición
            trade_result = self.capital_manager.execute_trade(
                symbol=symbol,
                action='buy',
                price=price,
                confidence=confidence,
                volatility=volatility
            )
            
            if trade_result:
                self.active_positions[symbol] = {
                    'entry_price': price,
                    'entry_time': datetime.now(),
                    'quantity': trade_result['quantity'],
                    'confidence': confidence
                }
                
                self.logger.info(f"Opened position: {symbol} at ${price:.4f} "
                               f"(Size: ${trade_result['position_size']:.2f})")
        
        elif action == 'sell' and has_position:
            # Cerrar posición
            trade_result = self.capital_manager.execute_trade(
                symbol=symbol,
                action='sell',
                price=price,
                confidence=confidence,
                volatility=volatility
            )
            
            if trade_result:
                position = self.active_positions.pop(symbol)
                
                self.logger.info(f"Closed position: {symbol} at ${price:.4f} "
                               f"PnL: ${trade_result['pnl']:.2f} ({trade_result['pnl_percentage']:.2f}%)")
        
        # Guardar señal en historial
        signal['processed_at'] = datetime.now().isoformat()
        signal['trade_executed'] = trade_result is not None
        self.signal_history.append(signal)
        
        return trade_result
    
    def run_trading_cycle(self) -> Dict:
        """Ejecuta un ciclo completo de trading"""
        cycle_results = {
            'timestamp': datetime.now().isoformat(),
            'signals_processed': 0,
            'trades_executed': 0,
            'capital_before': self.capital_manager.current_capital,
            'active_positions': len(self.active_positions)
        }
        
        self.logger.info("Starting trading cycle...")
        
        # Procesar cada símbolo
        for symbol in self.symbols:
            try:
                # Obtener datos
                data = self.get_market_data(symbol)
                
                # Analizar señal
                signal = self.analyze_signal(symbol, data)
                cycle_results['signals_processed'] += 1
                
                # Procesar señal
                trade_result = self.process_signal(signal)
                if trade_result:
                    cycle_results['trades_executed'] += 1
                
            except Exception as e:
                self.logger.error(f"Error processing {symbol}: {e}")
        
        cycle_results['capital_after'] = self.capital_manager.current_capital
        cycle_results['capital_change'] = (cycle_results['capital_after'] - 
                                         cycle_results['capital_before'])
        
        # Guardar estado
        self.capital_manager.save_state('sicar_variable_capital_state.json')
        
        self.logger.info(f"Cycle completed: {cycle_results['trades_executed']} trades, "
                        f"Capital: ${cycle_results['capital_after']:.2f}")
        
        return cycle_results
    
    def get_comprehensive_report(self) -> Dict:
        """Genera reporte completo del sistema"""
        performance = self.capital_manager.get_performance_summary()
        
        # Análisis de posiciones activas
        active_positions_value = 0
        for symbol, position in self.active_positions.items():
            try:
                current_data = self.get_market_data(symbol, 1)
                current_price = current_data['close'].iloc[-1]
                position_value = position['quantity'] * current_price
                active_positions_value += position_value
                
                position['current_price'] = current_price
                position['current_value'] = position_value
                position['unrealized_pnl'] = position_value - (position['quantity'] * position['entry_price'])
            except:
                pass
        
        # Análisis de señales recientes
        recent_signals = self.signal_history[-20:] if len(self.signal_history) > 20 else self.signal_history
        signal_accuracy = 0
        if recent_signals:
            successful_signals = sum(1 for s in recent_signals if s.get('trade_executed', False))
            signal_accuracy = (successful_signals / len(recent_signals)) * 100
        
        report = {
            'system_status': {
                'active': True,
                'last_cycle': datetime.now().isoformat(),
                'symbols_monitored': len(self.symbols),
                'active_positions': len(self.active_positions)
            },
            'capital_management': performance,
            'trading_performance': {
                'signal_accuracy': signal_accuracy,
                'recent_signals_count': len(recent_signals),
                'active_positions_value': active_positions_value,
                'total_portfolio_value': self.capital_manager.current_capital + active_positions_value
            },
            'active_positions': self.active_positions,
            'recent_signals': recent_signals[-5:],  # Últimas 5 señales
            'next_reinvestment_threshold': {
                'current_roi': ((self.capital_manager.current_capital - self.capital_manager.initial_capital) / 
                              self.capital_manager.initial_capital) * 100,
                'target_roi_for_reinvestment': self.capital_manager.reinvestment_threshold * 100,
                'amount_needed': max(0, (self.capital_manager.initial_capital * 
                                       self.capital_manager.reinvestment_threshold) - 
                                      (self.capital_manager.current_capital - self.capital_manager.initial_capital))
            }
        }
        
        return report

def run_sicar_variable_capital_demo():
    """Demo del sistema integrado"""
    print("=== DEMO SICAR + CAPITAL VARIABLE ===")
    
    # Crear sistema
    system = SicarVariableCapitalSystem(
        min_capital=200.0,
        max_capital=500.0,
        symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    )
    
    print(f"Sistema iniciado con capital: ${system.capital_manager.current_capital:.2f}")
    
    # Ejecutar varios ciclos
    for cycle in range(5):
        print(f"\n--- Ciclo {cycle + 1} ---")
        results = system.run_trading_cycle()
        print(f"Señales procesadas: {results['signals_processed']}")
        print(f"Trades ejecutados: {results['trades_executed']}")
        print(f"Capital: ${results['capital_after']:.2f}")
        
        # Pausa simulada entre ciclos
        import time
        time.sleep(1)
    
    # Reporte final
    report = system.get_comprehensive_report()
    print("\n=== REPORTE FINAL ===")
    print(f"Capital inicial: ${report['capital_management']['initial_capital_original']:.2f}")
    print(f"Capital actual: ${report['capital_management']['current_capital']:.2f}")
    print(f"ROI total: {report['capital_management']['total_roi_percentage']:.2f}%")
    print(f"Win rate: {report['capital_management']['win_rate_percentage']:.1f}%")
    print(f"Total reinvertido: ${report['capital_management']['total_reinvested']:.2f}")
    print(f"Posiciones activas: {report['system_status']['active_positions']}")
    
    # Guardar reporte
    with open('sicar_variable_capital_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print("\n✅ Reporte guardado en 'sicar_variable_capital_report.json'")
    
    return system

if __name__ == "__main__":
    run_sicar_variable_capital_demo()