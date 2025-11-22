"""
Módulo de Gestión de Riesgo Dinámico
Incluye stop loss basado en volatilidad, gestión de posiciones y cálculo de riesgo
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
import requests

class DynamicRiskManager:
    def __init__(self, db_path: str = "auto_trading_alerts.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Configuración de riesgo mejorada
        self.config = {
            'min_confidence': 75.0,  # Confianza mínima aumentada
            'max_positions': 2,      # Máximo 2 posiciones simultáneas
            'base_stop_loss': 3.0,   # Stop loss base 3%
            'max_stop_loss': 5.0,    # Stop loss máximo 5%
            'min_stop_loss': 2.0,    # Stop loss mínimo 2%
            'volatility_multiplier': 1.5,  # Multiplicador de volatilidad
            'position_size_base': 8.0,      # Tamaño base de posición 8%
            'max_position_size': 15.0,      # Tamaño máximo de posición 15%
            'min_position_size': 5.0,       # Tamaño mínimo de posición 5%
            'correlation_threshold': 0.7,   # Umbral de correlación
            'max_sector_exposure': 30.0     # Máxima exposición por sector
        }
        
        self.binance_base_url = "https://api.binance.com/api/v3"
        
    def calculate_dynamic_stop_loss(self, symbol: str, signal_type: str, 
                                  current_price: float, volatility: float = None) -> float:
        """
        Calcula stop loss dinámico basado en volatilidad
        """
        try:
            # Si no se proporciona volatilidad, calcularla
            if volatility is None:
                volatility = self._calculate_volatility(symbol)
            
            # Calcular stop loss basado en volatilidad
            volatility_factor = min(volatility / 20.0, 2.0)  # Normalizar volatilidad
            dynamic_stop = self.config['base_stop_loss'] + (volatility_factor * self.config['volatility_multiplier'])
            
            # Aplicar límites
            stop_loss_pct = max(
                self.config['min_stop_loss'],
                min(dynamic_stop, self.config['max_stop_loss'])
            )
            
            # Calcular precio de stop loss
            if signal_type.upper() == 'BUY':
                stop_price = current_price * (1 - stop_loss_pct / 100)
            else:  # SELL
                stop_price = current_price * (1 + stop_loss_pct / 100)
            
            self.logger.info(f"Stop loss dinámico para {symbol}: {stop_loss_pct:.2f}% (Volatilidad: {volatility:.2f}%)")
            
            return stop_price
            
        except Exception as e:
            self.logger.error(f"Error calculando stop loss dinámico para {symbol}: {e}")
            # Fallback al stop loss base
            if signal_type.upper() == 'BUY':
                return current_price * (1 - self.config['base_stop_loss'] / 100)
            else:
                return current_price * (1 + self.config['base_stop_loss'] / 100)
    
    def calculate_dynamic_position_size(self, symbol: str, confidence: float, 
                                      volatility: float, current_capital: float) -> float:
        """
        Calcula el tamaño de posición dinámico basado en confianza y volatilidad
        """
        try:
            # Factor de confianza (75-100% -> 0.5-1.0)
            confidence_factor = max(0.5, (confidence - 75) / 25)
            
            # Factor de volatilidad inverso (mayor volatilidad = menor posición)
            volatility_factor = max(0.5, 1 - (volatility / 100))
            
            # Tamaño base ajustado
            adjusted_size = self.config['position_size_base'] * confidence_factor * volatility_factor
            
            # Aplicar límites
            position_size_pct = max(
                self.config['min_position_size'],
                min(adjusted_size, self.config['max_position_size'])
            )
            
            position_value = current_capital * (position_size_pct / 100)
            
            self.logger.info(f"Tamaño de posición dinámico para {symbol}: {position_size_pct:.2f}% "
                           f"(Confianza: {confidence:.1f}%, Volatilidad: {volatility:.2f}%)")
            
            return position_value
            
        except Exception as e:
            self.logger.error(f"Error calculando tamaño de posición para {symbol}: {e}")
            return current_capital * (self.config['position_size_base'] / 100)
    
    def check_position_limits(self) -> Dict[str, any]:
        """
        Verifica los límites de posiciones activas
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Contar posiciones activas
            cursor.execute("""
                SELECT COUNT(*) as active_positions,
                       GROUP_CONCAT(symbol) as symbols
                FROM executed_trades 
                WHERE status = 'ACTIVE'
            """)
            
            result = cursor.fetchone()
            active_positions = result[0] if result[0] else 0
            active_symbols = result[1].split(',') if result[1] else []
            
            conn.close()
            
            can_open_position = active_positions < self.config['max_positions']
            
            return {
                'can_open_position': can_open_position,
                'active_positions': active_positions,
                'max_positions': self.config['max_positions'],
                'active_symbols': active_symbols,
                'remaining_slots': self.config['max_positions'] - active_positions
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando límites de posiciones: {e}")
            return {
                'can_open_position': False,
                'active_positions': 0,
                'max_positions': self.config['max_positions'],
                'active_symbols': [],
                'remaining_slots': 0
            }
    
    def check_correlation_risk(self, new_symbol: str, active_symbols: List[str]) -> Dict[str, any]:
        """
        Verifica el riesgo de correlación entre símbolos
        """
        try:
            if not active_symbols:
                return {'correlation_risk': 'LOW', 'max_correlation': 0.0, 'details': {}}
            
            correlations = {}
            max_correlation = 0.0
            
            for active_symbol in active_symbols:
                correlation = self._calculate_correlation(new_symbol, active_symbol)
                correlations[active_symbol] = correlation
                max_correlation = max(max_correlation, abs(correlation))
            
            # Determinar nivel de riesgo
            if max_correlation > self.config['correlation_threshold']:
                risk_level = 'HIGH'
            elif max_correlation > 0.5:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'correlation_risk': risk_level,
                'max_correlation': max_correlation,
                'details': correlations,
                'can_trade': max_correlation <= self.config['correlation_threshold']
            }
            
        except Exception as e:
            self.logger.error(f"Error verificando correlación para {new_symbol}: {e}")
            return {'correlation_risk': 'UNKNOWN', 'max_correlation': 0.0, 'details': {}, 'can_trade': True}
    
    def calculate_portfolio_risk(self) -> Dict[str, any]:
        """
        Calcula el riesgo total del portafolio
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener posiciones activas
            cursor.execute("""
                SELECT symbol, side, entry_price, quantity, stop_loss, take_profit
                FROM executed_trades 
                WHERE status = 'ACTIVE'
            """)
            
            positions = cursor.fetchall()
            conn.close()
            
            if not positions:
                return {
                    'total_risk': 0.0,
                    'max_loss': 0.0,
                    'risk_level': 'NONE',
                    'positions_analysis': []
                }
            
            total_risk = 0.0
            max_loss = 0.0
            positions_analysis = []
            
            for pos in positions:
                symbol, side, entry_price, quantity, stop_loss, take_profit = pos
                
                # Calcular riesgo por posición
                position_value = entry_price * quantity
                
                if stop_loss:
                    if side.upper() == 'BUY':
                        potential_loss = (entry_price - stop_loss) * quantity
                    else:  # SELL
                        potential_loss = (stop_loss - entry_price) * quantity
                    
                    risk_pct = (abs(potential_loss) / position_value) * 100
                    total_risk += risk_pct
                    max_loss += abs(potential_loss)
                else:
                    # Si no hay stop loss, asumir riesgo del 5%
                    risk_pct = 5.0
                    potential_loss = position_value * 0.05
                    total_risk += risk_pct
                    max_loss += potential_loss
                
                positions_analysis.append({
                    'symbol': symbol,
                    'signal_type': side,
                    'risk_percentage': risk_pct,
                    'potential_loss': abs(potential_loss),
                    'position_size': position_value
                })
            
            # Determinar nivel de riesgo del portafolio
            if total_risk > 15:
                risk_level = 'HIGH'
            elif total_risk > 8:
                risk_level = 'MEDIUM'
            else:
                risk_level = 'LOW'
            
            return {
                'total_risk': total_risk,
                'max_loss': max_loss,
                'risk_level': risk_level,
                'positions_analysis': positions_analysis,
                'active_positions': len(positions)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculando riesgo del portafolio: {e}")
            return {
                'total_risk': 0.0,
                'max_loss': 0.0,
                'risk_level': 'UNKNOWN',
                'positions_analysis': []
            }
    
    def should_execute_trade(self, signal_data: Dict) -> Dict[str, any]:
        """
        Determina si se debe ejecutar una operación basado en gestión de riesgo
        """
        try:
            symbol = signal_data.get('symbol')
            confidence = signal_data.get('confidence', 0)
            signal_type = signal_data.get('signal_type')
            
            # Verificar confianza mínima
            if confidence < self.config['min_confidence']:
                return {
                    'should_execute': False,
                    'reason': f'Confianza insuficiente: {confidence:.1f}% < {self.config["min_confidence"]}%',
                    'risk_assessment': 'HIGH'
                }
            
            # Verificar límites de posiciones
            position_limits = self.check_position_limits()
            if not position_limits['can_open_position']:
                return {
                    'should_execute': False,
                    'reason': f'Máximo de posiciones alcanzado: {position_limits["active_positions"]}/{position_limits["max_positions"]}',
                    'risk_assessment': 'HIGH'
                }
            
            # Verificar correlación
            correlation_check = self.check_correlation_risk(symbol, position_limits['active_symbols'])
            if not correlation_check['can_trade']:
                return {
                    'should_execute': False,
                    'reason': f'Alta correlación detectada: {correlation_check["max_correlation"]:.2f} > {self.config["correlation_threshold"]}',
                    'risk_assessment': 'HIGH'
                }
            
            # Verificar riesgo del portafolio
            portfolio_risk = self.calculate_portfolio_risk()
            if portfolio_risk['risk_level'] == 'HIGH':
                return {
                    'should_execute': False,
                    'reason': f'Riesgo del portafolio muy alto: {portfolio_risk["total_risk"]:.2f}%',
                    'risk_assessment': 'HIGH'
                }
            
            # Calcular parámetros de la operación
            current_price = signal_data.get('price', 0)
            volatility = signal_data.get('volatility', 25.0)
            
            stop_loss = self.calculate_dynamic_stop_loss(symbol, signal_type, current_price, volatility)
            
            # Verificar si el stop loss es razonable
            stop_loss_pct = abs((current_price - stop_loss) / current_price) * 100
            if stop_loss_pct > self.config['max_stop_loss']:
                return {
                    'should_execute': False,
                    'reason': f'Stop loss demasiado amplio: {stop_loss_pct:.2f}% > {self.config["max_stop_loss"]}%',
                    'risk_assessment': 'HIGH'
                }
            
            return {
                'should_execute': True,
                'reason': 'Todos los criterios de riesgo cumplidos',
                'risk_assessment': 'ACCEPTABLE',
                'calculated_stop_loss': stop_loss,
                'stop_loss_percentage': stop_loss_pct,
                'position_limits': position_limits,
                'correlation_risk': correlation_check,
                'portfolio_risk': portfolio_risk
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluando si ejecutar operación: {e}")
            return {
                'should_execute': False,
                'reason': f'Error en evaluación de riesgo: {str(e)}',
                'risk_assessment': 'UNKNOWN'
            }
    
    def _calculate_volatility(self, symbol: str, period: int = 20) -> float:
        """Calcula la volatilidad histórica de un símbolo"""
        try:
            url = f"{self.binance_base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': '1h',
                'limit': period + 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            closes = [float(candle[4]) for candle in data]
            
            # Calcular retornos
            returns = []
            for i in range(1, len(closes)):
                returns.append((closes[i] - closes[i-1]) / closes[i-1])
            
            # Volatilidad anualizada
            volatility = np.std(returns) * np.sqrt(365 * 24) * 100  # Para datos horarios
            
            return min(volatility, 100.0)  # Limitar a 100%
            
        except Exception as e:
            self.logger.error(f"Error calculando volatilidad para {symbol}: {e}")
            return 25.0  # Volatilidad por defecto
    
    def _calculate_correlation(self, symbol1: str, symbol2: str, period: int = 50) -> float:
        """Calcula la correlación entre dos símbolos"""
        try:
            # Obtener datos para ambos símbolos
            data1 = self._get_price_data(symbol1, period)
            data2 = self._get_price_data(symbol2, period)
            
            if len(data1) < 10 or len(data2) < 10:
                return 0.0
            
            # Calcular retornos
            returns1 = np.diff(data1) / data1[:-1]
            returns2 = np.diff(data2) / data2[:-1]
            
            # Asegurar misma longitud
            min_len = min(len(returns1), len(returns2))
            returns1 = returns1[-min_len:]
            returns2 = returns2[-min_len:]
            
            # Calcular correlación
            correlation = np.corrcoef(returns1, returns2)[0, 1]
            
            return correlation if not np.isnan(correlation) else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculando correlación entre {symbol1} y {symbol2}: {e}")
            return 0.0
    
    def _get_price_data(self, symbol: str, limit: int) -> List[float]:
        """Obtiene datos de precios para un símbolo"""
        try:
            url = f"{self.binance_base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': '1h',
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return [float(candle[4]) for candle in data]  # Precios de cierre
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos de precios para {symbol}: {e}")
            return []

# Función de prueba
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    risk_manager = DynamicRiskManager()
    
    # Probar gestión de riesgo
    test_signal = {
        'symbol': 'ADAUSDT',
        'signal_type': 'BUY',
        'confidence': 78.5,
        'price': 0.65,
        'volatility': 35.0
    }
    
    print("Probando gestión de riesgo dinámico...")
    result = risk_manager.should_execute_trade(test_signal)
    
    print(f"\n¿Ejecutar operación?: {result['should_execute']}")
    print(f"Razón: {result['reason']}")
    print(f"Evaluación de riesgo: {result['risk_assessment']}")
    
    if result['should_execute']:
        print(f"Stop loss calculado: ${result['calculated_stop_loss']:.4f}")
        print(f"Porcentaje de stop loss: {result['stop_loss_percentage']:.2f}%")
    
    # Probar límites de posiciones
    print(f"\nLímites de posiciones:")
    limits = risk_manager.check_position_limits()
    print(f"Posiciones activas: {limits['active_positions']}/{limits['max_positions']}")
    print(f"Puede abrir posición: {limits['can_open_position']}")
    
    # Probar riesgo del portafolio
    print(f"\nRiesgo del portafolio:")
    portfolio = risk_manager.calculate_portfolio_risk()
    print(f"Riesgo total: {portfolio['total_risk']:.2f}%")
    print(f"Nivel de riesgo: {portfolio['risk_level']}")