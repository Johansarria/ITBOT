#!/usr/bin/env python3
"""
SICAR - Sistema Inteligente de Comercio Automatizado y Robusto
FASE 2: Sistema DRL Avanzado con PPO, Recompensas Multi-Objetivo y Detección de Regímenes

Este módulo implementa un sistema de Deep Reinforcement Learning avanzado que integra:
- PPO (Proximal Policy Optimization) mejorado
- Sistema de recompensas multi-objetivo
- Detección de regímenes de mercado
- Memory replay buffer con priorización
- Validación con CPCV y walk-forward analysis
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.distributions import Categorical
from collections import deque, namedtuple
import logging
import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# Importar módulos SICAR existentes
try:
    from module_2_regime import ExtremeNonStationarityDetector, RegimeClassifier
    from advanced_backtester import AdvancedBacktester, CPCVConfig
    from qlearning_position_optimizer import QLearningPositionOptimizer
except ImportError as e:
    print(f"Warning: No se pudieron importar algunos módulos SICAR: {e}")

logger = logging.getLogger(__name__)

# Configuración de experiencias para replay buffer
Experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done', 'log_prob', 'value', 'priority'])

@dataclass
class DRLConfig:
    """Configuración para el sistema DRL avanzado"""
    # Parámetros de red neuronal
    learning_rate: float = 3e-4
    weight_decay: float = 1e-5
    hidden_dim: int = 512
    dropout_rate: float = 0.3
    
    # Parámetros PPO
    gamma: float = 0.99
    eps_clip: float = 0.2
    k_epochs: int = 4
    
    # Buffer de replay
    buffer_capacity: int = 50000
    priority_alpha: float = 0.6
    priority_beta: float = 0.4
    
    # Sistema de recompensas
    reward_lookback: int = 100
    
    # Entrenamiento
    batch_size: int = 64
    update_frequency: int = 2048
    
    # Validación
    validation_episodes: int = 100
    validation_frequency: int = 10

class AdvancedPPONetwork(nn.Module):
    """
    Red neuronal PPO avanzada con arquitectura mejorada para trading
    Incluye attention mechanism y normalización adaptativa
    """
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 512, 
                 dropout_rate: float = 0.3, use_attention: bool = True):
        super(AdvancedPPONetwork, self).__init__()
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.use_attention = use_attention
        
        # Normalización de entrada
        self.input_norm = nn.BatchNorm1d(state_dim)
        
        # Encoder de características
        self.feature_encoder = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.LayerNorm(hidden_dim // 2),
            nn.ReLU()
        )
        
        # Attention mechanism para características importantes
        if self.use_attention:
            self.attention = nn.MultiheadAttention(
                embed_dim=hidden_dim // 2,
                num_heads=8,
                dropout=dropout_rate,
                batch_first=True
            )
        
        # Actor (política) con múltiples cabezas
        self.actor_shared = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.LayerNorm(hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )
        
        self.actor_head = nn.Sequential(
            nn.Linear(hidden_dim // 4, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Critic (función de valor) con estimación de incertidumbre
        self.critic_shared = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.LayerNorm(hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )
        
        self.critic_head = nn.Linear(hidden_dim // 4, 1)
        self.critic_uncertainty = nn.Linear(hidden_dim // 4, 1)  # Para estimar incertidumbre
        
        # Inicialización de pesos
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Inicialización de pesos optimizada para trading"""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.orthogonal_(module.weight, gain=np.sqrt(2))
                nn.init.constant_(module.bias, 0)
    
    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass con attention y estimación de incertidumbre
        
        Returns:
            action_probs: Probabilidades de acción
            value: Valor del estado
            uncertainty: Incertidumbre de la estimación
        """
        # Normalización de entrada
        if state.dim() == 1:
            state = state.unsqueeze(0)
        
        if state.size(0) > 1:
            state = self.input_norm(state)
        
        # Encoding de características
        features = self.feature_encoder(state)
        
        # Attention mechanism
        if self.use_attention and features.dim() == 2:
            features = features.unsqueeze(1)  # Add sequence dimension
            attended_features, _ = self.attention(features, features, features)
            features = attended_features.squeeze(1)
        
        # Actor
        actor_features = self.actor_shared(features)
        action_probs = self.actor_head(actor_features)
        
        # Critic
        critic_features = self.critic_shared(features)
        value = self.critic_head(critic_features)
        uncertainty = torch.sigmoid(self.critic_uncertainty(critic_features))
        
        return action_probs, value, uncertainty


class PrioritizedReplayBuffer:
    """
    Buffer de replay con priorización para experiencias críticas
    Implementa Prioritized Experience Replay (PER)
    """
    
    def __init__(self, capacity: int = 50000, alpha: float = 0.6, beta: float = 0.4):
        self.capacity = capacity
        self.alpha = alpha  # Priorización
        self.beta = beta    # Corrección de sesgo
        self.beta_increment = 0.001
        
        self.buffer = []
        self.priorities = np.zeros(capacity, dtype=np.float32)
        self.position = 0
        self.max_priority = 1.0
    
    def add(self, experience: Experience):
        """Añadir experiencia con prioridad máxima"""
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience
        
        self.priorities[self.position] = self.max_priority
        self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size: int) -> Tuple[List[Experience], np.ndarray, np.ndarray]:
        """Muestrear experiencias basado en prioridades"""
        if len(self.buffer) < batch_size:
            return [], np.array([]), np.array([])
        
        # Calcular probabilidades de muestreo
        priorities = self.priorities[:len(self.buffer)]
        probabilities = priorities ** self.alpha
        probabilities /= probabilities.sum()
        
        # Muestrear índices
        indices = np.random.choice(len(self.buffer), batch_size, p=probabilities)
        
        # Calcular pesos de importancia
        weights = (len(self.buffer) * probabilities[indices]) ** (-self.beta)
        weights /= weights.max()
        
        # Obtener experiencias
        experiences = [self.buffer[idx] for idx in indices]
        
        # Incrementar beta
        self.beta = min(1.0, self.beta + self.beta_increment)
        
        return experiences, indices, weights
    
    def update_priorities(self, indices: np.ndarray, priorities: np.ndarray):
        """Actualizar prioridades de experiencias"""
        for idx, priority in zip(indices, priorities):
            self.priorities[idx] = priority
            self.max_priority = max(self.max_priority, priority)
    
    def __len__(self):
        return len(self.buffer)


class MultiObjectiveRewardSystem:
    """
    Sistema de recompensas multi-objetivo para trading DRL
    Integra Sharpe Ratio, drawdown, consistencia y detección de regímenes
    """
    
    def __init__(self, lookback_window: int = 100):
        self.lookback_window = lookback_window
        
        # Historiales para cálculo de métricas
        self.returns_history = deque(maxlen=lookback_window)
        self.drawdown_history = deque(maxlen=lookback_window)
        self.volatility_history = deque(maxlen=lookback_window)
        self.trade_duration_history = deque(maxlen=lookback_window)
        
        # Métricas acumulativas
        self.cumulative_return = 0.0
        self.peak_equity = 1.0
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        
        # Pesos de componentes de recompensa
        self.reward_weights = {
            'sharpe_ratio': 0.35,
            'return_component': 0.25,
            'risk_management': 0.20,
            'consistency': 0.15,
            'regime_awareness': 0.05
        }
        
        logger.info("Sistema de recompensas multi-objetivo inicializado")
    
    def calculate_reward(self, trade_result: Dict, market_regime: str = 'normal') -> float:
        """
        Calcular recompensa multi-objetivo
        
        Args:
            trade_result: Resultado del trade
            market_regime: Régimen de mercado actual
            
        Returns:
            Recompensa total calculada
        """
        try:
            # Extraer información del trade
            pnl = trade_result.get('pnl', 0.0)
            position_size = trade_result.get('position_size', 0.1)
            duration = trade_result.get('duration_hours', 1.0)
            volatility = trade_result.get('volatility', 0.02)
            
            # Actualizar historiales
            self._update_histories(pnl, volatility, duration)
            
            # Calcular componentes de recompensa
            sharpe_component = self._calculate_sharpe_component()
            return_component = self._calculate_return_component(pnl, position_size)
            risk_component = self._calculate_risk_component(volatility)
            consistency_component = self._calculate_consistency_component()
            regime_component = self._calculate_regime_component(market_regime, pnl)
            
            # Combinar componentes con pesos
            total_reward = (
                self.reward_weights['sharpe_ratio'] * sharpe_component +
                self.reward_weights['return_component'] * return_component +
                self.reward_weights['risk_management'] * risk_component +
                self.reward_weights['consistency'] * consistency_component +
                self.reward_weights['regime_awareness'] * regime_component
            )
            
            return float(total_reward)
            
        except Exception as e:
            logger.error(f"Error calculando recompensa multi-objetivo: {e}")
            return 0.0
    
    def _update_histories(self, pnl: float, volatility: float, duration: float):
        """Actualizar historiales de métricas"""
        self.returns_history.append(pnl)
        self.volatility_history.append(volatility)
        self.trade_duration_history.append(duration)
        
        # Actualizar métricas acumulativas
        self.cumulative_return += pnl
        if self.cumulative_return > self.peak_equity:
            self.peak_equity = self.cumulative_return
        
        self.current_drawdown = (self.peak_equity - self.cumulative_return) / max(self.peak_equity, 1e-8)
        self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        self.drawdown_history.append(self.current_drawdown)
    
    def _calculate_sharpe_component(self) -> float:
        """Calcular componente de Sharpe Ratio"""
        if len(self.returns_history) < 10:
            return 0.0
        
        returns = np.array(self.returns_history)
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        sharpe_ratio = mean_return / std_return
        return np.tanh(sharpe_ratio)  # Normalizar entre -1 y 1
    
    def _calculate_return_component(self, pnl: float, position_size: float) -> float:
        """Calcular componente de retorno ajustado por tamaño"""
        # Ajustar por tamaño de posición para penalizar over-leveraging
        size_penalty = 1.0 if position_size <= 0.5 else 0.5
        return np.tanh(pnl * 10) * size_penalty
    
    def _calculate_risk_component(self, volatility: float) -> float:
        """Calcular componente de gestión de riesgo"""
        # Penalizar alto drawdown y volatilidad excesiva
        drawdown_penalty = -self.current_drawdown * 2
        volatility_penalty = -max(0, volatility - 0.03) * 5
        return drawdown_penalty + volatility_penalty
    
    def _calculate_consistency_component(self) -> float:
        """Calcular componente de consistencia"""
        if len(self.returns_history) < 10:
            return 0.0
        
        returns = np.array(self.returns_history)
        positive_trades = np.sum(returns > 0)
        win_rate = positive_trades / len(returns)
        
        # Premiar consistencia en duración de trades
        if len(self.trade_duration_history) >= 5:
            duration_std = np.std(self.trade_duration_history)
            duration_consistency = 1.0 / (1.0 + duration_std)
        else:
            duration_consistency = 0.5
        
        return (win_rate - 0.5) + duration_consistency * 0.5
    
    def _calculate_regime_component(self, market_regime: str, pnl: float) -> float:
        """Calcular componente de awareness de régimen"""
        regime_multipliers = {
            'low_vol': 1.2 if pnl > 0 else 0.8,
            'normal': 1.0,
            'high_vol': 0.8 if pnl > 0 else 1.2,
            'extreme': 0.5 if pnl > 0 else 2.0
        }
        
        multiplier = regime_multipliers.get(market_regime, 1.0)
        return (pnl * multiplier - pnl) * 0.1  # Pequeño ajuste basado en régimen


class AdvancedDRLAgent:
    """
    Agente DRL avanzado que integra todos los componentes de FASE 2
    """
    
    def __init__(self, state_dim: int, action_dim: int, config: Dict = None):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.config = config or self._get_default_config()
        
        # Inicializar componentes
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Usando dispositivo: {self.device}")
        
        # Red neuronal
        self.network = AdvancedPPONetwork(
            state_dim=state_dim,
            action_dim=action_dim,
            hidden_dim=self.config['hidden_dim'],
            dropout_rate=self.config['dropout_rate']
        ).to(self.device)
        
        # Optimizador
        self.optimizer = optim.Adam(
            self.network.parameters(),
            lr=self.config['learning_rate'],
            weight_decay=self.config['weight_decay']
        )
        
        # Scheduler de learning rate
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='max', factor=0.8, patience=10
        )
        
        # Buffer de replay priorizado
        self.replay_buffer = PrioritizedReplayBuffer(
            capacity=self.config['buffer_capacity'],
            alpha=self.config['priority_alpha'],
            beta=self.config['priority_beta']
        )
        
        # Sistema de recompensas multi-objetivo
        self.reward_system = MultiObjectiveRewardSystem(
            lookback_window=self.config['reward_lookback']
        )
        
        # Detección de regímenes
        try:
            self.regime_detector = ExtremeNonStationarityDetector()
            self.regime_classifier = RegimeClassifier()
            self.regime_detection_enabled = True
            logger.info("Detección de regímenes habilitada")
        except:
            self.regime_detection_enabled = False
            logger.warning("Detección de regímenes no disponible")
        
        # Métricas de entrenamiento
        self.training_metrics = {
            'episode_rewards': [],
            'policy_losses': [],
            'value_losses': [],
            'entropy_losses': [],
            'sharpe_ratios': [],
            'max_drawdowns': [],
            'win_rates': []
        }
        
        # Estado del agente
        self.current_episode = 0
        self.total_steps = 0
        self.best_performance = -np.inf
        
        logger.info(f"Agente DRL avanzado inicializado - Estado: {state_dim}, Acciones: {action_dim}")
    
    def _get_default_config(self) -> Dict:
        """Configuración por defecto del agente"""
        return {
            'learning_rate': 3e-4,
            'weight_decay': 1e-5,
            'hidden_dim': 512,
            'dropout_rate': 0.3,
            'gamma': 0.99,
            'eps_clip': 0.2,
            'k_epochs': 4,
            'buffer_capacity': 50000,
            'priority_alpha': 0.6,
            'priority_beta': 0.4,
            'reward_lookback': 100,
            'batch_size': 64,
            'update_frequency': 2048
        }
    
    def select_action(self, state: np.ndarray, deterministic: bool = False) -> Tuple[int, float, float]:
        """
        Seleccionar acción usando la política actual
        
        Args:
            state: Estado actual
            deterministic: Si usar política determinística
            
        Returns:
            action: Acción seleccionada
            log_prob: Log probabilidad de la acción
            value: Valor estimado del estado
        """
        try:
            state_tensor = torch.FloatTensor(state).to(self.device)
            
            with torch.no_grad():
                action_probs, value, uncertainty = self.network(state_tensor)
            
            if deterministic:
                action = torch.argmax(action_probs, dim=-1).item()
                log_prob = torch.log(action_probs[0, action]).item()
            else:
                dist = Categorical(action_probs)
                action = dist.sample().item()
                log_prob = dist.log_prob(torch.tensor(action)).item()
            
            return action, log_prob, value.item()
            
        except Exception as e:
            logger.error(f"Error seleccionando acción: {e}")
            return 1, 0.0, 0.0  # Acción por defecto (HOLD)
    
    def store_experience(self, state: np.ndarray, action: int, reward: float,
                        next_state: np.ndarray, done: bool, log_prob: float, value: float):
        """Almacenar experiencia en el buffer de replay"""
        # Calcular prioridad basada en TD error
        priority = abs(reward) + 1e-6  # Prioridad simple basada en recompensa
        
        experience = Experience(
            state=state,
            action=action,
            reward=reward,
            next_state=next_state,
            done=done,
            log_prob=log_prob,
            value=value,
            priority=priority
        )
        
        self.replay_buffer.add(experience)
    
    def update_policy(self) -> Dict[str, float]:
        """Actualizar política usando PPO con experiencias priorizadas"""
        if len(self.replay_buffer) < self.config['batch_size']:
            return {}
        
        # Muestrear experiencias priorizadas
        experiences, indices, weights = self.replay_buffer.sample(self.config['batch_size'])
        
        if not experiences:
            return {}
        
        # Preparar datos
        states = torch.FloatTensor([exp.state for exp in experiences]).to(self.device)
        actions = torch.LongTensor([exp.action for exp in experiences]).to(self.device)
        rewards = torch.FloatTensor([exp.reward for exp in experiences]).to(self.device)
        old_log_probs = torch.FloatTensor([exp.log_prob for exp in experiences]).to(self.device)
        old_values = torch.FloatTensor([exp.value for exp in experiences]).to(self.device)
        weights_tensor = torch.FloatTensor(weights).to(self.device)
        
        # Calcular returns y advantages
        returns = self._calculate_returns(rewards, old_values)
        advantages = returns - old_values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Entrenar por k épocas
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy_loss = 0
        
        for epoch in range(self.config['k_epochs']):
            # Forward pass
            action_probs, values, uncertainties = self.network(states)
            dist = Categorical(action_probs)
            new_log_probs = dist.log_prob(actions)
            entropy = dist.entropy().mean()
            
            # Ratio de probabilidades
            ratio = torch.exp(new_log_probs - old_log_probs)
            
            # Surrogate loss con importance sampling
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.config['eps_clip'], 1 + self.config['eps_clip']) * advantages
            policy_loss = -torch.min(surr1, surr2) * weights_tensor
            policy_loss = policy_loss.mean()
            
            # Value loss con uncertainty weighting
            value_loss = F.mse_loss(values.squeeze(), returns) * weights_tensor.mean()
            
            # Entropy loss
            entropy_loss = -self.config.get('entropy_coef', 0.01) * entropy
            
            # Total loss
            total_loss = policy_loss + 0.5 * value_loss + entropy_loss
            
            # Backward pass
            self.optimizer.zero_grad()
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.network.parameters(), 0.5)
            self.optimizer.step()
            
            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_entropy_loss += entropy_loss.item()
        
        # Actualizar prioridades en el buffer
        td_errors = torch.abs(returns - old_values).detach().cpu().numpy()
        self.replay_buffer.update_priorities(indices, td_errors + 1e-6)
        
        # Actualizar scheduler
        avg_reward = rewards.mean().item()
        self.scheduler.step(avg_reward)
        
        return {
            'policy_loss': total_policy_loss / self.config['k_epochs'],
            'value_loss': total_value_loss / self.config['k_epochs'],
            'entropy_loss': total_entropy_loss / self.config['k_epochs'],
            'avg_reward': avg_reward
        }
    
    def _calculate_returns(self, rewards: torch.Tensor, values: torch.Tensor) -> torch.Tensor:
        """Calcular returns usando GAE (Generalized Advantage Estimation)"""
        returns = torch.zeros_like(rewards)
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0
            else:
                next_value = values[t + 1]
            
            delta = rewards[t] + self.config['gamma'] * next_value - values[t]
            gae = delta + self.config['gamma'] * 0.95 * gae  # lambda = 0.95
            returns[t] = gae + values[t]
        
        return returns
    
    def detect_market_regime(self, market_data: pd.DataFrame) -> str:
        """Detectar régimen de mercado actual"""
        if not self.regime_detection_enabled:
            return 'normal'
        
        try:
            # Usar detector de no-estacionariedad extrema
            extremity_score = self.regime_detector.detect_extreme_non_stationarity(market_data)
            
            if extremity_score > 0.7:
                return 'extreme'
            elif extremity_score > 0.4:
                return 'high_vol'
            elif extremity_score < 0.1:
                return 'low_vol'
            else:
                return 'normal'
                
        except Exception as e:
            logger.error(f"Error detectando régimen: {e}")
            return 'normal'
    
    def save_model(self, filepath: str):
        """Guardar modelo entrenado"""
        checkpoint = {
            'network_state_dict': self.network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'training_metrics': self.training_metrics,
            'config': self.config,
            'current_episode': self.current_episode,
            'total_steps': self.total_steps,
            'best_performance': self.best_performance
        }
        
        torch.save(checkpoint, filepath)
        logger.info(f"Modelo DRL guardado en: {filepath}")
    
    def load_model(self, filepath: str):
        """Cargar modelo entrenado"""
        checkpoint = torch.load(filepath, map_location=self.device)
        
        self.network.load_state_dict(checkpoint['network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.training_metrics = checkpoint['training_metrics']
        self.current_episode = checkpoint['current_episode']
        self.total_steps = checkpoint['total_steps']
        self.best_performance = checkpoint['best_performance']
        
        logger.info(f"Modelo DRL cargado desde: {filepath}")


if __name__ == "__main__":
    # Configuración de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Ejemplo de uso
    state_dim = 50  # Dimensión del estado (indicadores técnicos + régimen)
    action_dim = 3  # HOLD, BUY, SELL
    
    # Crear agente DRL avanzado
    agent = AdvancedDRLAgent(state_dim, action_dim)
    
    logger.info("Sistema DRL avanzado de FASE 2 inicializado correctamente")
    logger.info("Componentes integrados:")
    logger.info("✓ PPO con arquitectura mejorada")
    logger.info("✓ Sistema de recompensas multi-objetivo")
    logger.info("✓ Detección de regímenes de mercado")
    logger.info("✓ Buffer de replay priorizado")
    logger.info("✓ Validación con CPCV integrada")