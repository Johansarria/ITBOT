#!/usr/bin/env python3
"""
Q-Learning Avanzado para Optimización de Tamaños de Posición
Sistema SICAR - Fase 2 Mejorada
Optimización inteligente con función de recompensa basada en Sharpe Ratio
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
import json
import os
from collections import defaultdict, deque
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class QLearningPositionOptimizer:
    """
    Q-Learning Agent avanzado para optimizar tamaños de posición
    Incluye función de recompensa optimizada basada en Sharpe Ratio
    """
    
    def __init__(self, learning_rate=0.1, discount_factor=0.95, epsilon=0.1):
        """
        Inicializar Q-Learning Agent
        
        Args:
            learning_rate: Tasa de aprendizaje (alpha)
            discount_factor: Factor de descuento (gamma)
            epsilon: Probabilidad de exploración
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        
        # Q-Table: state -> action -> value
        self.q_table = defaultdict(lambda: defaultdict(float))
        
        # Historial de experiencias para cálculo de Sharpe
        self.experience_buffer = deque(maxlen=1000)
        self.returns_history = deque(maxlen=252)  # 1 año de retornos para Sharpe
        self.volatility_history = deque(maxlen=100)  # Historial de volatilidad
        
        # Estados y acciones
        self.position_sizes = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]  # Porcentajes del capital
        self.actions = list(range(len(self.position_sizes)))
        
        # Métricas avanzadas
        self.total_trades = 0
        self.successful_trades = 0
        self.total_reward = 0.0
        self.cumulative_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_equity = 0.0
        
        # Configuración de recompensa
        self.risk_free_rate = 0.02  # 2% anual
        self.sharpe_weight = 0.4    # Peso del Sharpe Ratio en la recompensa
        self.return_weight = 0.3    # Peso del retorno en la recompensa
        self.risk_weight = 0.2      # Peso del riesgo en la recompensa
        self.consistency_weight = 0.1  # Peso de la consistencia
        
        # Configuración
        self.state_features = ['volatility_level', 'trend_strength', 'confidence_level']
        
        logger.info("Q-Learning Position Optimizer Avanzado inicializado")
        logger.info(f"Tamaños de posición disponibles: {self.position_sizes}")
        logger.info(f"Función de recompensa optimizada con Sharpe Ratio activada")

    def discretize_state(self, market_state):
        """
        Convertir estado continuo del mercado a estado discreto
        
        Args:
            market_state: Dict con features del mercado
            
        Returns:
            str: Estado discretizado
        """
        try:
            # Extraer features clave
            volatility = market_state.get('volatility', 0.02)
            trend_strength = market_state.get('trend_strength', 0.5)
            confidence = market_state.get('confidence', 0.5)
            
            # Discretizar volatilidad (0: baja, 1: media, 2: alta)
            if volatility < 0.015:
                vol_level = 0
            elif volatility < 0.03:
                vol_level = 1
            else:
                vol_level = 2
            
            # Discretizar fuerza de tendencia (0: débil, 1: moderada, 2: fuerte)
            if trend_strength < 0.3:
                trend_level = 0
            elif trend_strength < 0.7:
                trend_level = 1
            else:
                trend_level = 2
            
            # Discretizar confianza (0: baja, 1: media, 2: alta)
            if confidence < 0.4:
                conf_level = 0
            elif confidence < 0.7:
                conf_level = 1
            else:
                conf_level = 2
            
            # Crear estado como string
            state = f"{vol_level}_{trend_level}_{conf_level}"
            return state
            
        except Exception as e:
            logger.error(f"Error discretizando estado: {e}")
            return "1_1_1"  # Estado por defecto
    
    def select_action(self, state, training=True):
        """
        Seleccionar acción usando epsilon-greedy policy
        
        Args:
            state: Estado actual del mercado
            training: Si está en modo entrenamiento
            
        Returns:
            int: Índice de la acción seleccionada
        """
        try:
            # Exploración vs Explotación
            if training and np.random.random() < self.epsilon:
                # Exploración: acción aleatoria
                action = np.random.choice(self.actions)
                logger.debug(f"Exploración: acción {action}")
            else:
                # Explotación: mejor acción conocida
                q_values = [self.q_table[state][action] for action in self.actions]
                
                if all(q == 0 for q in q_values):
                    # Si no hay experiencia previa, usar acción conservadora
                    action = 2  # Posición media (0.3)
                else:
                    action = np.argmax(q_values)
                
                logger.debug(f"Explotación: acción {action}, Q-values: {q_values}")
            
            return action
            
        except Exception as e:
            logger.error(f"Error seleccionando acción: {e}")
            return 2  # Acción por defecto (posición media)
    
    def calculate_advanced_reward(self, trade_result):
        """
        Función de recompensa avanzada basada en Sharpe Ratio y métricas de riesgo
        
        Args:
            trade_result: Dict con información del trade
            
        Returns:
            float: Recompensa calculada con métricas avanzadas
        """
        try:
            pnl = trade_result.get('pnl', 0.0)
            position_size = trade_result.get('position_size', 0.1)
            duration = trade_result.get('duration_hours', 1.0)
            volatility = trade_result.get('volatility', 0.02)
            
            # Actualizar historiales
            self.returns_history.append(pnl)
            self.volatility_history.append(volatility)
            self.cumulative_pnl += pnl
            
            # Actualizar drawdown
            if self.cumulative_pnl > self.peak_equity:
                self.peak_equity = self.cumulative_pnl
            current_drawdown = (self.peak_equity - self.cumulative_pnl) / max(self.peak_equity, 1e-8)
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
            
            # 1. Componente de Sharpe Ratio
            sharpe_component = self._calculate_sharpe_component()
            
            # 2. Componente de retorno ajustado por riesgo
            return_component = self._calculate_return_component(pnl, position_size, volatility)
            
            # 3. Componente de gestión de riesgo
            risk_component = self._calculate_risk_component(current_drawdown, volatility)
            
            # 4. Componente de consistencia
            consistency_component = self._calculate_consistency_component()
            
            # 5. Penalizaciones adicionales
            duration_penalty = self._calculate_duration_penalty(duration)
            concentration_penalty = self._calculate_concentration_penalty(position_size)
            
            # Recompensa final ponderada
            reward = (
                self.sharpe_weight * sharpe_component +
                self.return_weight * return_component +
                self.risk_weight * risk_component +
                self.consistency_weight * consistency_component -
                duration_penalty - concentration_penalty
            )
            
            # Normalizar recompensa
            reward = np.clip(reward, -2.0, 2.0)
            
            logger.debug(f"Recompensa avanzada: {reward:.3f} "
                        f"(Sharpe: {sharpe_component:.3f}, Return: {return_component:.3f}, "
                        f"Risk: {risk_component:.3f}, Consistency: {consistency_component:.3f})")
            
            return reward
            
        except Exception as e:
            logger.error(f"Error calculando recompensa avanzada: {e}")
            return 0.0
    
    def _calculate_sharpe_component(self):
        """Calcula componente de recompensa basado en Sharpe Ratio"""
        if len(self.returns_history) < 10:
            return 0.0
        
        returns = np.array(self.returns_history)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 1.0 if mean_return > 0 else -1.0
        
        # Sharpe Ratio anualizado (asumiendo retornos diarios)
        daily_risk_free = self.risk_free_rate / 252
        sharpe_ratio = (mean_return - daily_risk_free) / std_return
        
        # Normalizar Sharpe ratio a rango [-1, 1]
        normalized_sharpe = np.tanh(sharpe_ratio / 2.0)
        
        return normalized_sharpe
    
    def _calculate_return_component(self, pnl, position_size, volatility):
        """Calcula componente de retorno ajustado por riesgo"""
        if position_size == 0:
            return 0.0
        
        # Retorno ajustado por tamaño de posición
        risk_adjusted_return = pnl / position_size
        
        # Ajustar por volatilidad (penalizar retornos en alta volatilidad)
        volatility_adjustment = 1.0 / (1.0 + volatility * 10)
        
        adjusted_return = risk_adjusted_return * volatility_adjustment
        
        # Normalizar usando tanh
        return np.tanh(adjusted_return * 10)
    
    def _calculate_risk_component(self, current_drawdown, volatility):
        """Calcula componente de gestión de riesgo"""
        # Penalizar drawdowns altos
        drawdown_penalty = -current_drawdown * 2.0
        
        # Penalizar volatilidad excesiva
        volatility_penalty = -max(0, (volatility - 0.03) * 10)
        
        # Bonificar baja volatilidad
        volatility_bonus = max(0, (0.02 - volatility) * 5)
        
        risk_score = drawdown_penalty + volatility_penalty + volatility_bonus
        
        return np.clip(risk_score, -1.0, 1.0)
    
    def _calculate_consistency_component(self):
        """Calcula componente de consistencia de resultados"""
        if len(self.returns_history) < 5:
            return 0.0
        
        recent_returns = list(self.returns_history)[-10:]  # Últimos 10 trades
        
        # Calcular ratio de trades positivos
        positive_trades = sum(1 for r in recent_returns if r > 0)
        win_rate = positive_trades / len(recent_returns)
        
        # Calcular estabilidad de retornos (menor desviación = mayor consistencia)
        returns_std = np.std(recent_returns)
        stability_score = 1.0 / (1.0 + returns_std * 50)
        
        # Combinar win rate y estabilidad
        consistency_score = (win_rate * 0.6 + stability_score * 0.4) * 2 - 1
        
        return np.clip(consistency_score, -1.0, 1.0)
    
    def _calculate_duration_penalty(self, duration):
        """Calcula penalización por duración excesiva"""
        # Penalizar trades que duran más de 48 horas
        if duration > 48:
            return (duration - 48) * 0.01
        return 0.0
    
    def _calculate_concentration_penalty(self, position_size):
        """Calcula penalización por concentración excesiva"""
        # Penalizar posiciones muy grandes (>70% del capital)
        if position_size > 0.7:
            return (position_size - 0.7) * 0.5
        return 0.0
    
    def calculate_reward(self, trade_result):
        """
        Función de recompensa principal (mantiene compatibilidad)
        Ahora usa la función avanzada por defecto
        """
        return self.calculate_advanced_reward(trade_result)

    def update_q_table(self, state, action, reward, next_state):
        """
        Actualizar Q-Table usando Q-Learning update rule
        
        Args:
            state: Estado actual
            action: Acción tomada
            reward: Recompensa recibida
            next_state: Siguiente estado
        """
        try:
            # Q-Learning update: Q(s,a) = Q(s,a) + α[r + γ*max(Q(s',a')) - Q(s,a)]
            current_q = self.q_table[state][action]
            
            # Mejor Q-value del siguiente estado
            next_q_values = [self.q_table[next_state][a] for a in self.actions]
            max_next_q = max(next_q_values) if next_q_values else 0
            
            # Actualización
            new_q = current_q + self.learning_rate * (
                reward + self.discount_factor * max_next_q - current_q
            )
            
            self.q_table[state][action] = new_q
            
            logger.debug(f"Q-Table actualizada: {state}[{action}] = {new_q:.3f}")
            
        except Exception as e:
            logger.error(f"Error actualizando Q-Table: {e}")
    
    def learn_from_trade(self, market_state_before, action, trade_result, market_state_after):
        """
        Aprender de un trade completado
        
        Args:
            market_state_before: Estado del mercado antes del trade
            action: Acción tomada (índice de position size)
            trade_result: Resultado del trade
            market_state_after: Estado del mercado después del trade
        """
        try:
            # Discretizar estados
            state_before = self.discretize_state(market_state_before)
            state_after = self.discretize_state(market_state_after)
            
            # Calcular recompensa
            reward = self.calculate_reward(trade_result)
            
            # Actualizar Q-Table
            self.update_q_table(state_before, action, reward, state_after)
            
            # Guardar experiencia
            experience = {
                'state_before': state_before,
                'action': action,
                'reward': reward,
                'state_after': state_after,
                'timestamp': datetime.now().isoformat()
            }
            self.experience_buffer.append(experience)
            
            # Actualizar métricas
            self.total_trades += 1
            self.total_reward += reward
            
            if trade_result.get('pnl', 0) > 0:
                self.successful_trades += 1
            
            # Decay epsilon
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay
            
            logger.info(f"Aprendizaje completado: Estado {state_before} -> Acción {action} -> Recompensa {reward:.3f}")
            
        except Exception as e:
            logger.error(f"Error en aprendizaje: {e}")
    
    def get_optimal_position_size(self, market_state, training=False):
        """
        Obtener tamaño de posición óptimo para el estado actual
        
        Args:
            market_state: Estado actual del mercado
            training: Si está en modo entrenamiento
            
        Returns:
            dict: Información de la decisión
        """
        try:
            # Discretizar estado
            state = self.discretize_state(market_state)
            
            # Seleccionar acción
            action = self.select_action(state, training)
            
            # Obtener tamaño de posición
            position_size = self.position_sizes[action]
            
            # Q-values para análisis
            q_values = [self.q_table[state][a] for a in self.actions]
            
            decision_info = {
                'position_size': position_size,
                'action_index': action,
                'state': state,
                'q_values': q_values,
                'epsilon': self.epsilon,
                'confidence': max(q_values) if any(q != 0 for q in q_values) else 0.0
            }
            
            logger.debug(f"Posición óptima: {position_size:.1%} para estado {state}")
            
            return decision_info
            
        except Exception as e:
            logger.error(f"Error obteniendo posición óptima: {e}")
            return {
                'position_size': 0.3,  # Posición por defecto
                'action_index': 2,
                'state': '1_1_1',
                'q_values': [0] * len(self.actions),
                'epsilon': self.epsilon,
                'confidence': 0.0
            }
    
    def get_performance_metrics(self):
        """Obtener métricas de rendimiento del agente"""
        try:
            if self.total_trades == 0:
                return {
                    'total_trades': 0,
                    'win_rate': 0.0,
                    'avg_reward': 0.0,
                    'epsilon': self.epsilon,
                    'q_table_size': len(self.q_table)
                }
            
            win_rate = self.successful_trades / self.total_trades
            avg_reward = self.total_reward / self.total_trades
            
            return {
                'total_trades': self.total_trades,
                'successful_trades': self.successful_trades,
                'win_rate': win_rate,
                'avg_reward': avg_reward,
                'total_reward': self.total_reward,
                'epsilon': self.epsilon,
                'q_table_size': len(self.q_table),
                'experience_buffer_size': len(self.experience_buffer)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return {}
    
    def save_model(self, filepath):
        """Guardar modelo Q-Learning"""
        try:
            model_data = {
                'q_table': dict(self.q_table),
                'learning_rate': self.learning_rate,
                'discount_factor': self.discount_factor,
                'epsilon': self.epsilon,
                'total_trades': self.total_trades,
                'successful_trades': self.successful_trades,
                'total_reward': self.total_reward,
                'position_sizes': self.position_sizes,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(model_data, f, indent=2)
            
            logger.info(f"Modelo Q-Learning guardado en: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando modelo: {e}")
            return False
    
    def load_model(self, filepath):
        """Cargar modelo Q-Learning"""
        try:
            if not os.path.exists(filepath):
                logger.warning(f"Archivo no encontrado: {filepath}")
                return False
            
            with open(filepath, 'r') as f:
                model_data = json.load(f)
            
            # Reconstruir Q-Table
            self.q_table = defaultdict(lambda: defaultdict(float))
            for state, actions in model_data['q_table'].items():
                for action, value in actions.items():
                    self.q_table[state][int(action)] = value
            
            # Restaurar parámetros
            self.learning_rate = model_data.get('learning_rate', self.learning_rate)
            self.discount_factor = model_data.get('discount_factor', self.discount_factor)
            self.epsilon = model_data.get('epsilon', self.epsilon)
            self.total_trades = model_data.get('total_trades', 0)
            self.successful_trades = model_data.get('successful_trades', 0)
            self.total_reward = model_data.get('total_reward', 0.0)
            
            logger.info(f"Modelo Q-Learning cargado desde: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            return False


class PositionSizeIntegrator:
    """
    Integrador para usar Q-Learning con el sistema SICAR existente
    """
    
    def __init__(self):
        """Inicializar integrador"""
        self.qlearning_agents = {}
        self.default_position_size = 0.3
        
        logger.info("Position Size Integrator inicializado")
    
    def get_agent_for_symbol(self, symbol):
        """Obtener o crear agente Q-Learning para un símbolo"""
        if symbol not in self.qlearning_agents:
            self.qlearning_agents[symbol] = QLearningPositionOptimizer()
            logger.info(f"Nuevo agente Q-Learning creado para {symbol}")
        
        return self.qlearning_agents[symbol]
    
    def optimize_position_size(self, symbol, market_data, ml_prediction):
        """
        Optimizar tamaño de posición usando Q-Learning
        
        Args:
            symbol: Símbolo de trading
            market_data: Datos del mercado
            ml_prediction: Predicción del modelo ML
            
        Returns:
            dict: Información de la posición optimizada
        """
        try:
            agent = self.get_agent_for_symbol(symbol)
            
            # Preparar estado del mercado
            market_state = self._prepare_market_state(market_data, ml_prediction)
            
            # Obtener posición óptima
            decision = agent.get_optimal_position_size(market_state, training=True)
            
            logger.debug(f"Posición optimizada para {symbol}: {decision['position_size']:.1%}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error optimizando posición: {e}")
            return {
                'position_size': self.default_position_size,
                'action_index': 2,
                'state': 'error',
                'confidence': 0.0
            }
    
    def _prepare_market_state(self, market_data, ml_prediction):
        """Preparar estado del mercado para Q-Learning"""
        try:
            # Calcular volatilidad
            if 'close' in market_data and len(market_data['close']) > 20:
                returns = np.diff(np.log(market_data['close'][-20:]))
                volatility = np.std(returns) * np.sqrt(252)  # Volatilidad anualizada
            else:
                volatility = 0.02  # Volatilidad por defecto
            
            # Calcular fuerza de tendencia (usando SMA)
            if 'close' in market_data and len(market_data['close']) > 20:
                prices = market_data['close'][-20:]
                sma_short = np.mean(prices[-5:])
                sma_long = np.mean(prices[-20:])
                trend_strength = abs(sma_short - sma_long) / sma_long
            else:
                trend_strength = 0.5
            
            # Confianza del modelo ML
            confidence = ml_prediction.get('confidence', 0.5)
            
            market_state = {
                'volatility': volatility,
                'trend_strength': trend_strength,
                'confidence': confidence
            }
            
            return market_state
            
        except Exception as e:
            logger.error(f"Error preparando estado del mercado: {e}")
            return {
                'volatility': 0.02,
                'trend_strength': 0.5,
                'confidence': 0.5
            }
    
    def update_from_trade_result(self, symbol, trade_info):
        """
        Actualizar agente Q-Learning con resultado de trade
        
        Args:
            symbol: Símbolo de trading
            trade_info: Información completa del trade
        """
        try:
            if symbol not in self.qlearning_agents:
                logger.warning(f"No hay agente para {symbol}")
                return
            
            agent = self.qlearning_agents[symbol]
            
            # Extraer información necesaria
            market_state_before = trade_info.get('market_state_before', {})
            action = trade_info.get('action_index', 2)
            trade_result = trade_info.get('trade_result', {})
            market_state_after = trade_info.get('market_state_after', {})
            
            # Aprender del trade
            agent.learn_from_trade(
                market_state_before, action, trade_result, market_state_after
            )
            
            logger.info(f"Agente actualizado para {symbol}")
            
        except Exception as e:
            logger.error(f"Error actualizando agente: {e}")
    
    def get_all_performance_metrics(self):
        """Obtener métricas de todos los agentes"""
        try:
            all_metrics = {}
            
            for symbol, agent in self.qlearning_agents.items():
                all_metrics[symbol] = agent.get_performance_metrics()
            
            return all_metrics
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas: {e}")
            return {}


if __name__ == "__main__":
    # Test básico
    logging.basicConfig(level=logging.INFO)
    
    # Crear agente
    agent = QLearningPositionOptimizer()
    
    # Simular algunos trades
    for i in range(10):
        # Estado del mercado simulado
        market_state = {
            'volatility': np.random.uniform(0.01, 0.05),
            'trend_strength': np.random.uniform(0.0, 1.0),
            'confidence': np.random.uniform(0.3, 0.9)
        }
        
        # Obtener decisión
        decision = agent.get_optimal_position_size(market_state, training=True)
        
        # Simular resultado del trade
        trade_result = {
            'pnl': np.random.uniform(-0.02, 0.03),
            'position_size': decision['position_size'],
            'duration_hours': np.random.uniform(1, 48)
        }
        
        # Aprender del trade
        agent.learn_from_trade(market_state, decision['action_index'], trade_result, market_state)
    
    # Mostrar métricas
    metrics = agent.get_performance_metrics()
    print("Métricas del agente:", metrics)
    
    # Guardar modelo
    agent.save_model('test_qlearning_model.json')
    
    print("✅ Test del Q-Learning Position Optimizer completado exitosamente")


    def get_advanced_performance_metrics(self):
        """
        Obtener métricas de rendimiento avanzadas incluyendo Sharpe Ratio
        
        Returns:
            dict: Métricas avanzadas de rendimiento
        """
        try:
            base_metrics = self.get_performance_metrics()
            
            # Calcular métricas adicionales
            if len(self.returns_history) > 0:
                returns = np.array(self.returns_history)
                
                # Sharpe Ratio
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                daily_risk_free = self.risk_free_rate / 252
                sharpe_ratio = (mean_return - daily_risk_free) / std_return if std_return > 0 else 0
                
                # Sortino Ratio (solo considera volatilidad negativa)
                negative_returns = returns[returns < 0]
                downside_std = np.std(negative_returns) if len(negative_returns) > 0 else std_return
                sortino_ratio = (mean_return - daily_risk_free) / downside_std if downside_std > 0 else 0
                
                # Calmar Ratio
                calmar_ratio = mean_return / self.max_drawdown if self.max_drawdown > 0 else 0
                
                # Volatilidad promedio
                avg_volatility = np.mean(self.volatility_history) if self.volatility_history else 0
                
                advanced_metrics = {
                    **base_metrics,
                    'sharpe_ratio': sharpe_ratio,
                    'sortino_ratio': sortino_ratio,
                    'calmar_ratio': calmar_ratio,
                    'max_drawdown': self.max_drawdown,
                    'avg_volatility': avg_volatility,
                    'cumulative_pnl': self.cumulative_pnl,
                    'total_returns': len(self.returns_history),
                    'returns_std': std_return,
                    'avg_return': mean_return
                }
                
                return advanced_metrics
            else:
                return base_metrics
                
        except Exception as e:
            logger.error(f"Error calculando métricas avanzadas: {e}")
            return self.get_performance_metrics()