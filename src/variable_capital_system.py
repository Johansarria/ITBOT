#!/usr/bin/env python3
"""
Sistema de Capital Variable con Reinversión Automática
Capital base: 200-500 USDT (spot trading)
Reinversión automática de ganancias para crecimiento compuesto
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import os

class VariableCapitalManager:
    def __init__(self, 
                 min_capital: float = 200.0,
                 max_capital: float = 500.0,
                 reinvestment_threshold: float = 0.05,  # 5% ganancia para reinvertir
                 max_position_size: float = 0.25):      # 25% máximo por posición
        
        self.min_capital = min_capital
        self.max_capital = max_capital
        self.current_capital = min_capital
        self.initial_capital = min_capital
        self.reinvestment_threshold = reinvestment_threshold
        self.max_position_size = max_position_size
        
        # Tracking
        self.total_profits = 0.0
        self.total_reinvested = 0.0
        self.trade_history = []
        self.capital_history = []
        
        # Performance metrics
        self.win_rate = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Configurar logging para el sistema"""
        logger = logging.getLogger('VariableCapitalSystem')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.FileHandler('variable_capital_system.log')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def calculate_position_size(self, 
                              symbol: str, 
                              confidence: float = 0.5,
                              volatility: float = 0.02) -> float:
        """
        Calcula el tamaño de posición basado en:
        - Capital actual
        - Confianza en la señal
        - Volatilidad del activo
        - Límites de riesgo
        """
        # Base position size (porcentaje del capital)
        base_size = self.current_capital * self.max_position_size
        
        # Ajustar por confianza (0.1 - 1.0)
        confidence_multiplier = max(0.1, min(1.0, confidence))
        
        # Ajustar por volatilidad (reducir en alta volatilidad)
        volatility_multiplier = max(0.5, 1.0 - (volatility * 10))
        
        # Calcular tamaño final
        position_size = base_size * confidence_multiplier * volatility_multiplier
        
        # Asegurar límites mínimos y máximos
        min_position = 10.0  # Mínimo $10 USDT
        max_position = self.current_capital * 0.5  # Máximo 50% del capital
        
        position_size = max(min_position, min(position_size, max_position))
        
        self.logger.info(f"Position size calculated for {symbol}: ${position_size:.2f} "
                        f"(Capital: ${self.current_capital:.2f}, Confidence: {confidence:.2f})")
        
        return position_size
    
    def execute_trade(self, 
                     symbol: str,
                     action: str,  # 'buy' or 'sell'
                     price: float,
                     confidence: float = 0.5,
                     volatility: float = 0.02) -> Dict:
        """
        Ejecuta un trade con el sistema de capital variable
        """
        if action.lower() == 'buy':
            position_size = self.calculate_position_size(symbol, confidence, volatility)
            quantity = position_size / price
            
            trade = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': action,
                'price': price,
                'quantity': quantity,
                'position_size': position_size,
                'capital_before': self.current_capital,
                'confidence': confidence,
                'volatility': volatility,
                'status': 'open'
            }
            
            # Reducir capital disponible
            self.current_capital -= position_size
            
        else:  # sell
            # Buscar posición abierta correspondiente
            open_position = None
            for trade in reversed(self.trade_history):
                if (trade['symbol'] == symbol and 
                    trade['action'] == 'buy' and 
                    trade['status'] == 'open'):
                    open_position = trade
                    break
            
            if not open_position:
                self.logger.warning(f"No open position found for {symbol}")
                return {}
            
            # Calcular PnL
            buy_price = open_position['price']
            quantity = open_position['quantity']
            position_size = open_position['position_size']
            
            sell_value = quantity * price
            pnl = sell_value - position_size
            pnl_percentage = (pnl / position_size) * 100
            
            # Actualizar capital
            self.current_capital += sell_value
            
            # Actualizar estadísticas
            self.total_trades += 1
            if pnl > 0:
                self.winning_trades += 1
                self.total_profits += pnl
            
            self.win_rate = (self.winning_trades / self.total_trades) * 100
            
            trade = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': action,
                'price': price,
                'quantity': quantity,
                'position_size': sell_value,
                'capital_after': self.current_capital,
                'pnl': pnl,
                'pnl_percentage': pnl_percentage,
                'status': 'closed'
            }
            
            # Marcar posición como cerrada
            open_position['status'] = 'closed'
            open_position['pnl'] = pnl
            open_position['pnl_percentage'] = pnl_percentage
            
            # Verificar si reinvertir
            self._check_reinvestment()
            
            self.logger.info(f"Trade closed: {symbol} PnL: ${pnl:.2f} ({pnl_percentage:.2f}%) "
                           f"New capital: ${self.current_capital:.2f}")
        
        self.trade_history.append(trade)
        self._update_capital_history()
        
        return trade
    
    def _check_reinvestment(self):
        """
        Verifica si es momento de reinvertir ganancias
        """
        current_roi = (self.current_capital - self.initial_capital) / self.initial_capital
        
        if current_roi >= self.reinvestment_threshold and self.current_capital < self.max_capital:
            # Calcular cuánto reinvertir
            available_for_reinvestment = self.current_capital - self.initial_capital
            max_reinvestment = self.max_capital - self.initial_capital
            
            reinvestment_amount = min(available_for_reinvestment, max_reinvestment)
            
            if reinvestment_amount > 0:
                self.initial_capital += reinvestment_amount
                self.total_reinvested += reinvestment_amount
                
                self.logger.info(f"REINVESTMENT: ${reinvestment_amount:.2f} added to base capital. "
                               f"New base: ${self.initial_capital:.2f}")
                
                # Registrar evento de reinversión
                reinvestment_event = {
                    'timestamp': datetime.now().isoformat(),
                    'type': 'reinvestment',
                    'amount': reinvestment_amount,
                    'new_base_capital': self.initial_capital,
                    'total_reinvested': self.total_reinvested,
                    'roi_at_reinvestment': current_roi
                }
                
                self.trade_history.append(reinvestment_event)
    
    def _update_capital_history(self):
        """Actualiza el historial de capital"""
        self.capital_history.append({
            'timestamp': datetime.now().isoformat(),
            'current_capital': self.current_capital,
            'base_capital': self.initial_capital,
            'total_roi': ((self.current_capital - 200.0) / 200.0) * 100,  # ROI desde capital inicial original
            'current_roi': ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        })
    
    def get_performance_summary(self) -> Dict:
        """Genera resumen de rendimiento"""
        total_roi = ((self.current_capital - 200.0) / 200.0) * 100  # ROI total desde $200 inicial
        current_cycle_roi = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        
        return {
            'initial_capital_original': 200.0,
            'current_base_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_roi_percentage': total_roi,
            'current_cycle_roi_percentage': current_cycle_roi,
            'total_profits': self.total_profits,
            'total_reinvested': self.total_reinvested,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate_percentage': self.win_rate,
            'capital_growth': self.current_capital - 200.0,
            'reinvestment_cycles': len([t for t in self.trade_history if t.get('type') == 'reinvestment'])
        }
    
    def save_state(self, filename: str = 'variable_capital_state.json'):
        """Guarda el estado actual del sistema"""
        state = {
            'config': {
                'min_capital': self.min_capital,
                'max_capital': self.max_capital,
                'reinvestment_threshold': self.reinvestment_threshold,
                'max_position_size': self.max_position_size
            },
            'current_state': {
                'current_capital': self.current_capital,
                'initial_capital': self.initial_capital,
                'total_profits': self.total_profits,
                'total_reinvested': self.total_reinvested,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'win_rate': self.win_rate
            },
            'trade_history': self.trade_history,
            'capital_history': self.capital_history,
            'performance_summary': self.get_performance_summary(),
            'last_updated': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)
        
        self.logger.info(f"State saved to {filename}")
    
    def load_state(self, filename: str = 'variable_capital_state.json'):
        """Carga el estado desde archivo"""
        try:
            with open(filename, 'r') as f:
                state = json.load(f)
            
            # Restaurar configuración
            config = state['config']
            self.min_capital = config['min_capital']
            self.max_capital = config['max_capital']
            self.reinvestment_threshold = config['reinvestment_threshold']
            self.max_position_size = config['max_position_size']
            
            # Restaurar estado actual
            current = state['current_state']
            self.current_capital = current['current_capital']
            self.initial_capital = current['initial_capital']
            self.total_profits = current['total_profits']
            self.total_reinvested = current['total_reinvested']
            self.total_trades = current['total_trades']
            self.winning_trades = current['winning_trades']
            self.win_rate = current['win_rate']
            
            # Restaurar historiales
            self.trade_history = state['trade_history']
            self.capital_history = state['capital_history']
            
            self.logger.info(f"State loaded from {filename}")
            
        except FileNotFoundError:
            self.logger.info(f"No state file found at {filename}, starting fresh")
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")

def simulate_variable_capital_trading():
    """
    Simulación de ejemplo del sistema de capital variable
    """
    print("=== SIMULACIÓN SISTEMA CAPITAL VARIABLE ===")
    
    # Crear manager
    capital_manager = VariableCapitalManager(
        min_capital=200.0,
        max_capital=500.0,
        reinvestment_threshold=0.05,  # Reinvertir cada 5% ganancia
        max_position_size=0.25
    )
    
    # Simular algunos trades
    trades_simulation = [
        {'symbol': 'BTCUSDT', 'action': 'buy', 'price': 45000, 'confidence': 0.7, 'volatility': 0.03},
        {'symbol': 'BTCUSDT', 'action': 'sell', 'price': 46800, 'confidence': 0.7, 'volatility': 0.03},
        {'symbol': 'ETHUSDT', 'action': 'buy', 'price': 2800, 'confidence': 0.6, 'volatility': 0.04},
        {'symbol': 'ETHUSDT', 'action': 'sell', 'price': 2950, 'confidence': 0.6, 'volatility': 0.04},
        {'symbol': 'ADAUSDT', 'action': 'buy', 'price': 0.45, 'confidence': 0.8, 'volatility': 0.05},
        {'symbol': 'ADAUSDT', 'action': 'sell', 'price': 0.48, 'confidence': 0.8, 'volatility': 0.05},
    ]
    
    print(f"Capital inicial: ${capital_manager.current_capital:.2f}")
    print("\n--- Ejecutando trades ---")
    
    for trade_data in trades_simulation:
        trade = capital_manager.execute_trade(**trade_data)
        if trade.get('action') == 'sell':
            print(f"Trade cerrado: {trade['symbol']} - PnL: ${trade['pnl']:.2f} ({trade['pnl_percentage']:.2f}%)")
    
    # Mostrar resumen final
    summary = capital_manager.get_performance_summary()
    print("\n=== RESUMEN FINAL ===")
    print(f"Capital inicial original: ${summary['initial_capital_original']:.2f}")
    print(f"Capital base actual: ${summary['current_base_capital']:.2f}")
    print(f"Capital actual: ${summary['current_capital']:.2f}")
    print(f"ROI total: {summary['total_roi_percentage']:.2f}%")
    print(f"ROI ciclo actual: {summary['current_cycle_roi_percentage']:.2f}%")
    print(f"Total reinvertido: ${summary['total_reinvested']:.2f}")
    print(f"Trades totales: {summary['total_trades']}")
    print(f"Win rate: {summary['win_rate_percentage']:.1f}%")
    print(f"Ciclos de reinversión: {summary['reinvestment_cycles']}")
    
    # Guardar estado
    capital_manager.save_state()
    
    return capital_manager

if __name__ == "__main__":
    simulate_variable_capital_trading()