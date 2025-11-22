#!/usr/bin/env python3
"""
Motor de ML Avanzado para Sistema SICAR
Feature Engineering optimizado y Ensemble Methods
Objetivo: Mejorar performance de ML de -10.94% a positivo
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ML Libraries
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier, 
    ExtraTreesClassifier, AdaBoostClassifier, VotingClassifier
)
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, precision_score, recall_score, f1_score
from sklearn.feature_selection import SelectKBest, f_classif, RFE
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline

# DRL Libraries
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.distributions import Categorical
from collections import deque
import random

# Feature Engineering
import talib
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
from scipy.stats import skew, kurtosis
import ta

# XAI Module
try:
    from module_xai import generate_cognitive_report, save_cognitive_report
except ImportError:
    print("Warning: Módulo XAI no encontrado. Funcionalidad de explicabilidad limitada.")
    def generate_cognitive_report(*args, **kwargs):
        return "Módulo XAI no disponible"
    def save_cognitive_report(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)

class PPOAgent:
    """
    Agente PPO (Proximal Policy Optimization) para trading
    Integrado con la infraestructura SICAR existente
    """
    
    def __init__(self, state_dim, action_dim, lr=3e-4, gamma=0.99, eps_clip=0.2, 
                 k_epochs=4, hidden_dim=256):
        """
        Inicializar agente PPO
        
        Args:
            state_dim: Dimensión del espacio de estados
            action_dim: Dimensión del espacio de acciones
            lr: Learning rate
            gamma: Factor de descuento
            eps_clip: Epsilon para clipping de PPO
            k_epochs: Número de épocas de entrenamiento
            hidden_dim: Dimensión de capas ocultas
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr
        self.gamma = gamma
        self.eps_clip = eps_clip
        self.k_epochs = k_epochs
        
        # Redes neuronales
        self.policy = PPONetwork(state_dim, action_dim, hidden_dim)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        
        # Buffer de experiencias
        self.memory = PPOMemory()
        
        # Métricas de entrenamiento
        self.training_metrics = {
            'policy_loss': [],
            'value_loss': [],
            'entropy_loss': [],
            'total_loss': [],
            'rewards': [],
            'episode_lengths': []
        }
        
        # Configuración de exploración adaptativa con volatility weighting
        self.exploration_rate = 1.0
        self.exploration_decay = 0.995
        self.min_exploration = 0.1
        self.base_exploration = 0.2
        
        # Gestión adaptativa basada en volatilidad
        self.volatility_window = 20
        self.volatility_threshold_low = 0.01
        self.volatility_threshold_high = 0.03
        self.volatility_history = deque(maxlen=self.volatility_window)
        self.market_regime = 'normal'  # 'low_vol', 'normal', 'high_vol'
        
        # Parámetros adaptativos por régimen
        self.regime_params = {
            'low_vol': {
                'exploration_multiplier': 1.5,
                'entropy_weight': 0.02,
                'learning_rate_multiplier': 1.2
            },
            'normal': {
                'exploration_multiplier': 1.0,
                'entropy_weight': 0.01,
                'learning_rate_multiplier': 1.0
            },
            'high_vol': {
                'exploration_multiplier': 0.7,
                'entropy_weight': 0.005,
                'learning_rate_multiplier': 0.8
            }
        }
        
        # Métricas de performance para adaptación
        self.performance_window = 100
        self.recent_rewards = deque(maxlen=self.performance_window)
        self.recent_sharpe_ratios = deque(maxlen=self.performance_window)
        
        logger.info(f"Agente PPO inicializado - Estado: {state_dim}, Acciones: {action_dim}")
        logger.info(f"Gestión adaptativa de exploración-explotación activada")
    
    def select_action(self, state, deterministic=False):
        """
        Seleccionar acción usando la política actual
        
        Args:
            state: Estado actual del entorno
            deterministic: Si True, selecciona la acción más probable
            
        Returns:
            action: Acción seleccionada
            log_prob: Log probabilidad de la acción
            value: Valor estimado del estado
        """
        state = torch.FloatTensor(state).unsqueeze(0)
        
        with torch.no_grad():
            action_probs, value = self.policy(state)
            
        if deterministic:
            action = torch.argmax(action_probs, dim=1)
            log_prob = torch.log(action_probs.gather(1, action.unsqueeze(1)))
        else:
            # Aplicar exploración adaptativa
            if np.random.random() < self.exploration_rate:
                # Exploración: añadir ruido a las probabilidades
                noise = torch.randn_like(action_probs) * 0.1
                action_probs = F.softmax(action_probs + noise, dim=1)
            
            dist = Categorical(action_probs)
            action = dist.sample()
            log_prob = dist.log_prob(action)
        
        return action.item(), log_prob.item(), value.item()
    
    def update_market_regime(self, market_data):
        """
        Actualizar régimen de mercado basado en volatilidad
        
        Args:
            market_data: Datos de mercado recientes (precios, retornos, etc.)
        """
        try:
            # Calcular volatilidad reciente
            if 'returns' in market_data:
                returns = market_data['returns']
                if len(returns) > 0:
                    volatility = np.std(returns) * np.sqrt(252)  # Volatilidad anualizada
                    self.volatility_history.append(volatility)
            
            # Determinar régimen de mercado
            if len(self.volatility_history) >= 5:
                avg_volatility = np.mean(list(self.volatility_history)[-5:])
                
                if avg_volatility < self.volatility_threshold_low:
                    new_regime = 'low_vol'
                elif avg_volatility > self.volatility_threshold_high:
                    new_regime = 'high_vol'
                else:
                    new_regime = 'normal'
                
                if new_regime != self.market_regime:
                    logger.info(f"Cambio de régimen: {self.market_regime} -> {new_regime} "
                              f"(Vol: {avg_volatility:.4f})")
                    self.market_regime = new_regime
                    self._adapt_parameters()
        
        except Exception as e:
            logger.warning(f"Error actualizando régimen de mercado: {e}")
    
    def _adapt_parameters(self):
        """Adaptar parámetros del agente según el régimen de mercado"""
        try:
            params = self.regime_params[self.market_regime]
            
            # Ajustar tasa de exploración
            base_exploration = self.base_exploration * params['exploration_multiplier']
            self.exploration_rate = max(self.min_exploration, base_exploration)
            
            # Ajustar learning rate del optimizador
            new_lr = self.lr * params['learning_rate_multiplier']
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = new_lr
            
            logger.debug(f"Parámetros adaptados para régimen '{self.market_regime}': "
                        f"Exploración: {self.exploration_rate:.3f}, LR: {new_lr:.6f}")
        
        except Exception as e:
            logger.warning(f"Error adaptando parámetros: {e}")
    
    def calculate_adaptive_exploration(self, performance_metrics):
        """
        Calcular tasa de exploración adaptativa basada en performance
        
        Args:
            performance_metrics: Métricas de rendimiento recientes
        """
        try:
            # Agregar métricas recientes
            if 'reward' in performance_metrics:
                self.recent_rewards.append(performance_metrics['reward'])
            
            if 'sharpe_ratio' in performance_metrics:
                self.recent_sharpe_ratios.append(performance_metrics['sharpe_ratio'])
            
            # Calcular tendencia de performance
            if len(self.recent_rewards) >= 20:
                recent_performance = np.mean(list(self.recent_rewards)[-10:])
                historical_performance = np.mean(list(self.recent_rewards)[-20:-10])
                
                performance_trend = recent_performance - historical_performance
                
                # Ajustar exploración basada en tendencia
                if performance_trend < -0.1:  # Performance empeorando
                    exploration_boost = 0.1
                elif performance_trend > 0.1:  # Performance mejorando
                    exploration_boost = -0.05
                else:
                    exploration_boost = 0.0
                
                # Aplicar ajuste con límites
                regime_params = self.regime_params[self.market_regime]
                base_exploration = self.base_exploration * regime_params['exploration_multiplier']
                
                self.exploration_rate = np.clip(
                    base_exploration + exploration_boost,
                    self.min_exploration,
                    0.8
                )
                
                logger.debug(f"Exploración adaptativa: {self.exploration_rate:.3f} "
                           f"(Tendencia: {performance_trend:.3f})")
        
        except Exception as e:
            logger.warning(f"Error calculando exploración adaptativa: {e}")
    
    def get_volatility_weighted_action(self, state, market_volatility):
        """
        Seleccionar acción con ponderación por volatilidad
        
        Args:
            state: Estado actual del entorno
            market_volatility: Volatilidad actual del mercado
            
        Returns:
            tuple: (acción, log_prob, valor)
        """
        try:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0)
                action_probs, value = self.policy(state_tensor)
                
                # Ajustar probabilidades basado en volatilidad
                volatility_factor = np.clip(market_volatility / 0.02, 0.5, 2.0)
                
                if market_volatility > self.volatility_threshold_high:
                    # Alta volatilidad: ser más conservador
                    conservative_bias = torch.tensor([0.4, 0.3, 0.2, 0.1])  # Favorecer hold/sell
                    action_probs = action_probs * 0.7 + conservative_bias * 0.3
                elif market_volatility < self.volatility_threshold_low:
                    # Baja volatilidad: ser más agresivo
                    aggressive_bias = torch.tensor([0.1, 0.4, 0.3, 0.2])  # Favorecer buy/hold
                    action_probs = action_probs * 0.7 + aggressive_bias * 0.3
                
                # Renormalizar
                action_probs = F.softmax(action_probs, dim=1)
                
                dist = Categorical(action_probs)
                action = dist.sample()
                log_prob = dist.log_prob(action)
                
                return action.item(), log_prob.item(), value.item()
        
        except Exception as e:
            logger.warning(f"Error en acción ponderada por volatilidad: {e}")
            return self.select_action(state)
    
    def store_transition(self, state, action, reward, next_state, done, log_prob, value):
        """Almacenar transición en el buffer de memoria"""
        self.memory.store(state, action, reward, next_state, done, log_prob, value)
    
    def update(self):
        """Actualizar la política usando PPO"""
        if len(self.memory) < 64:  # Mínimo de experiencias para entrenar
            return
        
        # Obtener datos del buffer
        states, actions, rewards, next_states, dones, old_log_probs, values = self.memory.get_all()
        
        # Convertir a tensores
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        old_log_probs = torch.FloatTensor(old_log_probs)
        values = torch.FloatTensor(values)
        dones = torch.BoolTensor(dones)
        
        # Calcular returns y advantages
        returns = self._calculate_returns(rewards, values, dones)
        advantages = returns - values
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # Entrenar por k épocas
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy_loss = 0
        
        for _ in range(self.k_epochs):
            # Forward pass
            action_probs, new_values = self.policy(states)
            dist = Categorical(action_probs)
            new_log_probs = dist.log_prob(actions)
            entropy = dist.entropy().mean()
            
            # Ratio de probabilidades
            ratio = torch.exp(new_log_probs - old_log_probs)
            
            # Surrogate loss
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # Value loss
            value_loss = F.mse_loss(new_values.squeeze(), returns)
            
            # Entropy loss (para fomentar exploración)
            entropy_loss = -0.01 * entropy
            
            # Loss total
            total_loss = policy_loss + 0.5 * value_loss + entropy_loss
            
            # Backward pass
            self.optimizer.zero_grad()
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy.parameters(), 0.5)
            self.optimizer.step()
            
            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_entropy_loss += entropy_loss.item()
        
        # Guardar métricas
        self.training_metrics['policy_loss'].append(total_policy_loss / self.k_epochs)
        self.training_metrics['value_loss'].append(total_value_loss / self.k_epochs)
        self.training_metrics['entropy_loss'].append(total_entropy_loss / self.k_epochs)
        self.training_metrics['total_loss'].append(
            (total_policy_loss + total_value_loss + total_entropy_loss) / self.k_epochs
        )
        
        # Calcular métricas de performance para adaptación
        avg_reward = np.mean(rewards.numpy()) if len(rewards) > 0 else 0
        performance_metrics = {
            'reward': avg_reward,
            'policy_loss': total_policy_loss / self.k_epochs,
            'value_loss': total_value_loss / self.k_epochs
        }
        
        # Calcular Sharpe ratio si hay suficientes datos
        if len(self.recent_rewards) >= 10:
            recent_rewards_array = np.array(list(self.recent_rewards)[-10:])
            if np.std(recent_rewards_array) > 0:
                performance_metrics['sharpe_ratio'] = np.mean(recent_rewards_array) / np.std(recent_rewards_array)
        
        # Actualizar exploración adaptativa
        self.calculate_adaptive_exploration(performance_metrics)
        
        # Actualizar tasa de exploración base (decay tradicional como fallback)
        base_decay_rate = max(
            self.min_exploration, 
            self.base_exploration * self.exploration_decay
        )
        
        # Usar el máximo entre la exploración adaptativa y el decay base
        if hasattr(self, 'exploration_rate'):
            self.exploration_rate = max(self.exploration_rate, base_decay_rate)
        else:
            self.exploration_rate = base_decay_rate
        
        # Limpiar memoria
        self.memory.clear()
        
        logger.debug(f"PPO actualizado - Policy Loss: {total_policy_loss/self.k_epochs:.4f}, "
                    f"Value Loss: {total_value_loss/self.k_epochs:.4f}, "
                    f"Exploration Rate: {self.exploration_rate:.4f}, "
                    f"Market Regime: {self.market_regime}")
    
    def _calculate_returns(self, rewards, values, dones):
        """Calcular returns usando GAE (Generalized Advantage Estimation)"""
        returns = torch.zeros_like(rewards)
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0
            else:
                next_value = values[t + 1]
            
            if dones[t]:
                next_value = 0
            
            delta = rewards[t] + self.gamma * next_value - values[t]
            gae = delta + self.gamma * 0.95 * gae  # lambda = 0.95 para GAE
            returns[t] = gae + values[t]
        
        return returns
    
    def get_training_metrics(self):
        """Obtener métricas de entrenamiento"""
        if not self.training_metrics['policy_loss']:
            return {}
        
        return {
            'avg_policy_loss': np.mean(self.training_metrics['policy_loss'][-100:]),
            'avg_value_loss': np.mean(self.training_metrics['value_loss'][-100:]),
            'avg_entropy_loss': np.mean(self.training_metrics['entropy_loss'][-100:]),
            'avg_total_loss': np.mean(self.training_metrics['total_loss'][-100:]),
            'exploration_rate': self.exploration_rate,
            'training_episodes': len(self.training_metrics['policy_loss'])
        }
    
    def save_model(self, filepath):
        """Guardar modelo entrenado"""
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'training_metrics': self.training_metrics,
            'exploration_rate': self.exploration_rate
        }, filepath)
        logger.info(f"Modelo PPO guardado en: {filepath}")
    
    def load_model(self, filepath):
        """Cargar modelo entrenado"""
        checkpoint = torch.load(filepath)
        self.policy.load_state_dict(checkpoint['policy_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.training_metrics = checkpoint['training_metrics']
        self.exploration_rate = checkpoint['exploration_rate']
        logger.info(f"Modelo PPO cargado desde: {filepath}")
    
    def explain_action(self, state, action, market_data=None, symbol=None):
        """
        Generar explicación XAI para una acción del agente PPO
        
        Args:
            state: Estado actual del entorno
            action: Acción tomada por el agente
            market_data: Datos de mercado adicionales (opcional)
            symbol: Símbolo del activo (opcional)
            
        Returns:
            dict: Explicación completa de la decisión
        """
        try:
            logger.info(f"Generando explicación XAI para acción {action}")
            
            # Convertir estado a tensor si es necesario
            if not isinstance(state, torch.Tensor):
                state_tensor = torch.FloatTensor(state).unsqueeze(0)
            else:
                state_tensor = state.unsqueeze(0) if state.dim() == 1 else state
            
            # Obtener probabilidades de acción y valor del estado
            with torch.no_grad():
                action_probs, state_value = self.policy(state_tensor)
                action_probs = action_probs.squeeze().numpy()
                state_value = state_value.item()
            
            # Mapear acciones a decisiones de trading
            action_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
            decision = action_map.get(action, 'UNKNOWN')
            
            # Calcular confianza de la decisión
            confidence = float(action_probs[action]) if action < len(action_probs) else 0.0
            
            # Analizar distribución de probabilidades
            prob_distribution = {
                'hold_prob': float(action_probs[0]) if len(action_probs) > 0 else 0.0,
                'buy_prob': float(action_probs[1]) if len(action_probs) > 1 else 0.0,
                'sell_prob': float(action_probs[2]) if len(action_probs) > 2 else 0.0
            }
            
            # Determinar estrategia basada en la acción y confianza
            if decision == 'BUY' and confidence > 0.7:
                strategy = 'momentum'
            elif decision == 'SELL' and confidence > 0.7:
                strategy = 'mean_reversion'
            elif decision == 'HOLD':
                strategy = 'hold'
            else:
                strategy = 'conservative'
            
            # Determinar régimen de mercado basado en volatilidad
            market_regime = self._determine_market_regime_from_state(state)
            
            # Preparar factores XAI
            xai_factors = self._extract_xai_factors(state, action_probs, state_value, confidence)
            
            # Factores causales principales
            primary_causal_factors = self._identify_causal_factors(state, action, confidence)
            
            # Contexto adicional
            additional_context = {
                'agent_type': 'PPO',
                'exploration_rate': self.exploration_rate,
                'market_regime_detected': self.market_regime,
                'state_value_estimate': state_value,
                'action_distribution': prob_distribution,
                'training_episodes': len(self.training_metrics.get('policy_loss', [])),
                'symbol': symbol or 'Unknown'
            }
            
            # Generar reporte cognitivo usando el módulo XAI
            cognitive_report = generate_cognitive_report(
                decision=decision,
                strategy=strategy,
                market_regime=market_regime,
                xai_factors=xai_factors,
                primary_causal_factors=primary_causal_factors,
                additional_context=additional_context
            )
            
            explanation = {
                'decision': decision,
                'confidence': confidence,
                'strategy': strategy,
                'market_regime': market_regime,
                'state_value': state_value,
                'action_probabilities': prob_distribution,
                'xai_factors': xai_factors,
                'causal_factors': primary_causal_factors,
                'cognitive_report': cognitive_report,
                'timestamp': pd.Timestamp.now(),
                'agent_context': additional_context
            }
            
            logger.info(f"Explicación XAI generada para decisión {decision} con confianza {confidence:.3f}")
            return explanation
            
        except Exception as e:
            logger.error(f"Error generando explicación XAI: {e}")
            return {
                'decision': 'ERROR',
                'confidence': 0.0,
                'error': str(e),
                'cognitive_report': f"Error generando explicación: {e}"
            }
    
    def _extract_xai_factors(self, state, action_probs, state_value, confidence):
        """Extraer factores explicativos del estado y decisión"""
        try:
            # Convertir estado a numpy si es tensor
            if isinstance(state, torch.Tensor):
                state_np = state.numpy()
            else:
                state_np = np.array(state)
            
            # Calcular métricas básicas del estado
            state_mean = np.mean(state_np)
            state_std = np.std(state_np)
            state_max = np.max(state_np)
            state_min = np.min(state_np)
            
            # Entropía de la distribución de acciones
            entropy = -np.sum(action_probs * np.log(action_probs + 1e-8))
            
            # Factores XAI
            xai_factors = {
                'confidence': confidence,
                'state_value_estimate': float(state_value),
                'action_entropy': float(entropy),
                'state_mean': float(state_mean),
                'state_volatility': float(state_std),
                'state_range': float(state_max - state_min),
                'exploration_rate': self.exploration_rate,
                'market_regime': self.market_regime,
                'decision_certainty': float(np.max(action_probs)),
                'decision_uncertainty': float(1 - np.max(action_probs))
            }
            
            return xai_factors
            
        except Exception as e:
            logger.error(f"Error extrayendo factores XAI: {e}")
            return {'confidence': confidence, 'error': str(e)}
    
    def _identify_causal_factors(self, state, action, confidence):
        """Identificar factores causales principales de la decisión"""
        try:
            causal_factors = []
            
            # Factores basados en confianza
            if confidence > 0.8:
                causal_factors.append('alta_confianza_modelo')
            elif confidence > 0.6:
                causal_factors.append('confianza_moderada')
            else:
                causal_factors.append('baja_confianza_decision')
            
            # Factores basados en exploración
            if self.exploration_rate > 0.3:
                causal_factors.append('fase_exploracion_activa')
            elif self.exploration_rate > 0.1:
                causal_factors.append('exploracion_moderada')
            else:
                causal_factors.append('fase_explotacion')
            
            # Factores basados en régimen de mercado
            if self.market_regime == 'high_vol':
                causal_factors.append('regimen_alta_volatilidad')
            elif self.market_regime == 'low_vol':
                causal_factors.append('regimen_baja_volatilidad')
            else:
                causal_factors.append('regimen_volatilidad_normal')
            
            # Factores basados en la acción
            action_map = {0: 'decision_mantener_posicion', 1: 'decision_compra_activa', 2: 'decision_venta_activa'}
            if action in action_map:
                causal_factors.append(action_map[action])
            
            # Factores basados en el estado
            if isinstance(state, (list, np.ndarray, torch.Tensor)):
                state_array = np.array(state) if not isinstance(state, np.ndarray) else state
                if isinstance(state, torch.Tensor):
                    state_array = state.numpy()
                
                if len(state_array) > 0:
                    if np.mean(state_array) > 0.5:
                        causal_factors.append('indicadores_alcistas')
                    elif np.mean(state_array) < -0.5:
                        causal_factors.append('indicadores_bajistas')
                    else:
                        causal_factors.append('indicadores_neutrales')
            
            return causal_factors[:5]  # Limitar a 5 factores principales
            
        except Exception as e:
            logger.error(f"Error identificando factores causales: {e}")
            return ['error_analisis_causal']
    
    def _determine_market_regime_from_state(self, state):
        """Determinar régimen de mercado basado en el estado"""
        try:
            # Usar el régimen actual del agente si está disponible
            if hasattr(self, 'market_regime') and self.market_regime:
                regime_map = {
                    'low_vol': 'Mercado Estable',
                    'normal': 'Mercado Normal',
                    'high_vol': 'Mercado Volátil'
                }
                return regime_map.get(self.market_regime, 'Mercado Normal')
            
            # Análisis básico del estado para determinar régimen
            if isinstance(state, (list, np.ndarray, torch.Tensor)):
                state_array = np.array(state) if not isinstance(state, np.ndarray) else state
                if isinstance(state, torch.Tensor):
                    state_array = state.numpy()
                
                if len(state_array) > 0:
                    volatility = np.std(state_array)
                    if volatility > 0.5:
                        return 'Mercado Volátil'
                    elif volatility < 0.1:
                        return 'Mercado Estable'
                    else:
                        return 'Mercado Normal'
            
            return 'Mercado Normal'
            
        except Exception as e:
            logger.error(f"Error determinando régimen de mercado: {e}")
            return 'Régimen Desconocido'
    
    def generate_action_explanation_report(self, state, action, market_data=None, symbol=None, save_report=True):
        """
        Generar y opcionalmente guardar un reporte completo de explicación de acción
        
        Args:
            state: Estado actual
            action: Acción tomada
            market_data: Datos de mercado adicionales
            symbol: Símbolo del activo
            save_report: Si guardar el reporte en archivo
            
        Returns:
            tuple: (explanation_dict, report_filepath)
        """
        try:
            # Generar explicación
            explanation = self.explain_action(state, action, market_data, symbol)
            
            # Guardar reporte si se solicita
            report_filepath = None
            if save_report and 'cognitive_report' in explanation:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"ppo_action_explanation_{symbol or 'unknown'}_{timestamp}.txt"
                report_filepath = save_cognitive_report(explanation['cognitive_report'], filename)
            
            return explanation, report_filepath
            
        except Exception as e:
            logger.error(f"Error generando reporte de explicación: {e}")
            return {'error': str(e)}, None


class PPONetwork(nn.Module):
    """Red neuronal para PPO con actor-critic"""
    
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super(PPONetwork, self).__init__()
        
        # Capas compartidas
        self.shared_layers = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU()
        )
        
        # Actor (política)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Linear(hidden_dim // 4, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Critic (función de valor)
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.ReLU(),
            nn.Linear(hidden_dim // 4, 1)
        )
    
    def forward(self, state):
        """Forward pass de la red"""
        shared_features = self.shared_layers(state)
        action_probs = self.actor(shared_features)
        value = self.critic(shared_features)
        return action_probs, value


class PPOMemory:
    """Buffer de memoria para PPO"""
    
    def __init__(self, max_size=10000):
        self.max_size = max_size
        self.clear()
    
    def store(self, state, action, reward, next_state, done, log_prob, value):
        """Almacenar experiencia"""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.next_states.append(next_state)
        self.dones.append(done)
        self.log_probs.append(log_prob)
        self.values.append(value)
        
        # Mantener tamaño máximo
        if len(self.states) > self.max_size:
            self.states.pop(0)
            self.actions.pop(0)
            self.rewards.pop(0)
            self.next_states.pop(0)
            self.dones.pop(0)
            self.log_probs.pop(0)
            self.values.pop(0)
    
    def get_all(self):
        """Obtener todas las experiencias"""
        return (self.states, self.actions, self.rewards, self.next_states, 
                self.dones, self.log_probs, self.values)
    
    def clear(self):
        """Limpiar memoria"""
        self.states = []
        self.actions = []
        self.rewards = []
        self.next_states = []
        self.dones = []
        self.log_probs = []
        self.values = []
    
    def __len__(self):
        return len(self.states)


class A2CAgent:
    """
    Agente A2C (Advantage Actor-Critic) para trading
    Implementación basada en hallazgos de QuantConnect
    """
    
    def __init__(self, state_dim, action_dim, lr=3e-4, gamma=0.99, hidden_dim=256):
        """
        Inicializar agente A2C
        
        Args:
            state_dim: Dimensión del espacio de estados
            action_dim: Dimensión del espacio de acciones
            lr: Learning rate
            gamma: Factor de descuento
            hidden_dim: Dimensión de capas ocultas
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr
        self.gamma = gamma
        
        # Red neuronal actor-critic
        self.network = A2CNetwork(state_dim, action_dim, hidden_dim)
        self.optimizer = optim.Adam(self.network.parameters(), lr=lr)
        
        # Buffer de experiencias
        self.memory = A2CMemory()
        
        # Métricas de entrenamiento
        self.training_metrics = {
            'actor_loss': [],
            'critic_loss': [],
            'entropy_loss': [],
            'total_loss': [],
            'rewards': [],
            'episode_lengths': []
        }
        
        logger.info(f"Agente A2C inicializado - Estado: {state_dim}, Acciones: {action_dim}")
    
    def select_action(self, state, deterministic=False):
        """Seleccionar acción usando política A2C"""
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        
        with torch.no_grad():
            action_probs, value = self.network(state_tensor)
            
        if deterministic:
            action = torch.argmax(action_probs, dim=1).item()
            log_prob = torch.log(action_probs[0, action])
        else:
            dist = Categorical(action_probs)
            action = dist.sample().item()
            log_prob = dist.log_prob(torch.tensor(action))
        
        return action, log_prob.item(), value.item()
    
    def store_transition(self, state, action, reward, next_state, done, log_prob, value):
        """Almacenar transición en el buffer de memoria"""
        self.memory.store(state, action, reward, next_state, done, log_prob, value)
    
    def update(self):
        """Actualizar la política usando A2C"""
        if len(self.memory) < 32:  # Mínimo de experiencias para entrenar
            return
        
        # Obtener datos del buffer
        states, actions, rewards, next_states, dones, log_probs, values = self.memory.get_all()
        
        # Convertir a tensores
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        values = torch.FloatTensor(values)
        log_probs = torch.FloatTensor(log_probs)
        dones = torch.BoolTensor(dones)
        
        # Calcular returns
        returns = self._calculate_returns(rewards, dones)
        advantages = returns - values
        
        # Forward pass
        action_probs, new_values = self.network(states)
        dist = Categorical(action_probs)
        new_log_probs = dist.log_prob(actions)
        entropy = dist.entropy().mean()
        
        # Actor loss
        actor_loss = -(new_log_probs * advantages.detach()).mean()
        
        # Critic loss
        critic_loss = F.mse_loss(new_values.squeeze(), returns)
        
        # Entropy loss (para fomentar exploración)
        entropy_loss = -0.01 * entropy
        
        # Loss total
        total_loss = actor_loss + 0.5 * critic_loss + entropy_loss
        
        # Backward pass
        self.optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.network.parameters(), 0.5)
        self.optimizer.step()
        
        # Guardar métricas
        self.training_metrics['actor_loss'].append(actor_loss.item())
        self.training_metrics['critic_loss'].append(critic_loss.item())
        self.training_metrics['entropy_loss'].append(entropy_loss.item())
        self.training_metrics['total_loss'].append(total_loss.item())
        
        # Limpiar memoria
        self.memory.clear()
        
        logger.debug(f"A2C actualizado - Actor Loss: {actor_loss.item():.4f}, "
                    f"Critic Loss: {critic_loss.item():.4f}")
    
    def _calculate_returns(self, rewards, dones):
        """Calcular returns usando descuento"""
        returns = []
        R = 0
        
        for i in reversed(range(len(rewards))):
            if dones[i]:
                R = 0
            R = rewards[i] + self.gamma * R
            returns.insert(0, R)
        
        return torch.FloatTensor(returns)
    
    def get_training_metrics(self):
        """Obtener métricas de entrenamiento"""
        return self.training_metrics.copy()
    
    def save_model(self, filepath):
        """Guardar modelo entrenado"""
        torch.save({
            'network_state_dict': self.network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'training_metrics': self.training_metrics
        }, filepath)
        logger.info(f"Modelo A2C guardado en: {filepath}")
    
    def load_model(self, filepath):
        """Cargar modelo entrenado"""
        checkpoint = torch.load(filepath)
        self.network.load_state_dict(checkpoint['network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.training_metrics = checkpoint['training_metrics']
        logger.info(f"Modelo A2C cargado desde: {filepath}")


class A2CNetwork(nn.Module):
    """Red neuronal para A2C con actor-critic"""
    
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super(A2CNetwork, self).__init__()
        
        # Capas compartidas
        self.shared_layers = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2)
        )
        
        # Actor (política)
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Critic (función de valor)
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1)
        )
    
    def forward(self, state):
        """Forward pass de la red"""
        shared_features = self.shared_layers(state)
        action_probs = self.actor(shared_features)
        value = self.critic(shared_features)
        return action_probs, value


class A2CMemory:
    """Buffer de memoria para A2C"""
    
    def __init__(self, max_size=5000):
        self.max_size = max_size
        self.clear()
    
    def store(self, state, action, reward, next_state, done, log_prob, value):
        """Almacenar experiencia"""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.next_states.append(next_state)
        self.dones.append(done)
        self.log_probs.append(log_prob)
        self.values.append(value)
        
        # Mantener tamaño máximo
        if len(self.states) > self.max_size:
            self.states.pop(0)
            self.actions.pop(0)
            self.rewards.pop(0)
            self.next_states.pop(0)
            self.dones.pop(0)
            self.log_probs.pop(0)
            self.values.pop(0)
    
    def get_all(self):
        """Obtener todas las experiencias"""
        return (self.states, self.actions, self.rewards, self.next_states, 
                self.dones, self.log_probs, self.values)
    
    def clear(self):
        """Limpiar memoria"""
        self.states = []
        self.actions = []
        self.rewards = []
        self.next_states = []
        self.dones = []
        self.log_probs = []
        self.values = []
    
    def __len__(self):
        return len(self.states)


class DQNAgent:
    """
    Agente DQN (Deep Q-Network) para trading
    Implementación basada en hallazgos de QuantConnect
    """
    
    def __init__(self, state_dim, action_dim, lr=1e-3, gamma=0.99, epsilon=1.0, 
                 epsilon_decay=0.995, epsilon_min=0.01, hidden_dim=256, 
                 memory_size=10000, batch_size=32, target_update_freq=100):
        """
        Inicializar agente DQN
        
        Args:
            state_dim: Dimensión del espacio de estados
            action_dim: Dimensión del espacio de acciones
            lr: Learning rate
            gamma: Factor de descuento
            epsilon: Tasa de exploración inicial
            epsilon_decay: Decaimiento de epsilon
            epsilon_min: Epsilon mínimo
            hidden_dim: Dimensión de capas ocultas
            memory_size: Tamaño del buffer de experiencias
            batch_size: Tamaño del batch para entrenamiento
            target_update_freq: Frecuencia de actualización de la red objetivo
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.update_count = 0
        
        # Redes neuronales (principal y objetivo)
        self.q_network = DQNNetwork(state_dim, action_dim, hidden_dim)
        self.target_network = DQNNetwork(state_dim, action_dim, hidden_dim)
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=lr)
        
        # Copiar pesos a la red objetivo
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Buffer de experiencias
        self.memory = DQNMemory(memory_size)
        
        # Métricas de entrenamiento
        self.training_metrics = {
            'q_loss': [],
            'epsilon': [],
            'rewards': [],
            'episode_lengths': [],
            'q_values': []
        }
        
        logger.info(f"Agente DQN inicializado - Estado: {state_dim}, Acciones: {action_dim}")
    
    def select_action(self, state, deterministic=False):
        """Seleccionar acción usando epsilon-greedy"""
        if deterministic or np.random.random() > self.epsilon:
            # Acción greedy
            state_tensor = torch.FloatTensor(state).unsqueeze(0)
            with torch.no_grad():
                q_values = self.q_network(state_tensor)
                action = torch.argmax(q_values, dim=1).item()
                q_value = q_values[0, action].item()
        else:
            # Acción aleatoria
            action = np.random.randint(self.action_dim)
            q_value = 0.0
        
        return action, 0.0, q_value  # Mantener compatibilidad con interfaz
    
    def store_transition(self, state, action, reward, next_state, done, log_prob=None, value=None):
        """Almacenar transición en el buffer de memoria"""
        self.memory.store(state, action, reward, next_state, done)
    
    def update(self):
        """Actualizar la red Q usando DQN"""
        if len(self.memory) < self.batch_size:
            return
        
        # Muestrear batch de experiencias
        batch = self.memory.sample(self.batch_size)
        states, actions, rewards, next_states, dones = batch
        
        # Convertir a tensores
        states = torch.FloatTensor(states)
        actions = torch.LongTensor(actions)
        rewards = torch.FloatTensor(rewards)
        next_states = torch.FloatTensor(next_states)
        dones = torch.BoolTensor(dones)
        
        # Q-values actuales
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Q-values objetivo
        with torch.no_grad():
            next_q_values = self.target_network(next_states).max(1)[0]
            target_q_values = rewards + (self.gamma * next_q_values * ~dones)
        
        # Loss
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        # Backward pass
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        # Actualizar epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # Actualizar red objetivo
        self.update_count += 1
        if self.update_count % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Guardar métricas
        self.training_metrics['q_loss'].append(loss.item())
        self.training_metrics['epsilon'].append(self.epsilon)
        self.training_metrics['q_values'].append(current_q_values.mean().item())
        
        logger.debug(f"DQN actualizado - Q Loss: {loss.item():.4f}, "
                    f"Epsilon: {self.epsilon:.4f}")
    
    def get_training_metrics(self):
        """Obtener métricas de entrenamiento"""
        return self.training_metrics.copy()
    
    def save_model(self, filepath):
        """Guardar modelo entrenado"""
        torch.save({
            'q_network_state_dict': self.q_network.state_dict(),
            'target_network_state_dict': self.target_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'training_metrics': self.training_metrics,
            'epsilon': self.epsilon,
            'update_count': self.update_count
        }, filepath)
        logger.info(f"Modelo DQN guardado en: {filepath}")
    
    def load_model(self, filepath):
        """Cargar modelo entrenado"""
        checkpoint = torch.load(filepath)
        self.q_network.load_state_dict(checkpoint['q_network_state_dict'])
        self.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.training_metrics = checkpoint['training_metrics']
        self.epsilon = checkpoint['epsilon']
        self.update_count = checkpoint['update_count']
        logger.info(f"Modelo DQN cargado desde: {filepath}")


class DQNNetwork(nn.Module):
    """Red neuronal para DQN"""
    
    def __init__(self, state_dim, action_dim, hidden_dim=256):
        super(DQNNetwork, self).__init__()
        
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim)
        )
    
    def forward(self, state):
        """Forward pass de la red"""
        return self.network(state)


class DQNMemory:
    """Buffer de memoria para DQN con experience replay"""
    
    def __init__(self, max_size=10000):
        self.max_size = max_size
        self.memory = deque(maxlen=max_size)
    
    def store(self, state, action, reward, next_state, done):
        """Almacenar experiencia"""
        self.memory.append((state, action, reward, next_state, done))
    
    def sample(self, batch_size):
        """Muestrear batch de experiencias"""
        batch = random.sample(self.memory, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return states, actions, rewards, next_states, dones
    
    def __len__(self):
        return len(self.memory)


class DRLEnsemble:
    """
    Ensemble de algoritmos DRL (PPO + A2C + DQN)
    Basado en hallazgos de QuantConnect para trading robusto
    """
    
    def __init__(self, state_dim, action_dim, **kwargs):
        """
        Inicializar ensemble DRL
        
        Args:
            state_dim: Dimensión del espacio de estados
            action_dim: Dimensión del espacio de acciones
            **kwargs: Parámetros adicionales para los agentes
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Inicializar agentes
        self.ppo_agent = PPOAgent(state_dim, action_dim, **kwargs)
        self.a2c_agent = A2CAgent(state_dim, action_dim, **kwargs)
        self.dqn_agent = DQNAgent(state_dim, action_dim, **kwargs)
        
        # Pesos del ensemble (se pueden ajustar dinámicamente)
        self.weights = {'ppo': 0.4, 'a2c': 0.3, 'dqn': 0.3}
        
        # Métricas de rendimiento por agente
        self.performance_metrics = {
            'ppo': {'wins': 0, 'total': 0, 'avg_reward': 0.0},
            'a2c': {'wins': 0, 'total': 0, 'avg_reward': 0.0},
            'dqn': {'wins': 0, 'total': 0, 'avg_reward': 0.0}
        }
        
        logger.info(f"Ensemble DRL inicializado - PPO: {self.weights['ppo']}, "
                   f"A2C: {self.weights['a2c']}, DQN: {self.weights['dqn']}")
    
    def select_action(self, state, deterministic=False):
        """Seleccionar acción usando ensemble voting"""
        # Obtener acciones de cada agente
        ppo_action, ppo_log_prob, ppo_value = self.ppo_agent.select_action(state, deterministic)
        a2c_action, a2c_log_prob, a2c_value = self.a2c_agent.select_action(state, deterministic)
        dqn_action, _, dqn_q_value = self.dqn_agent.select_action(state, deterministic)
        
        # Voting ponderado
        action_votes = {}
        action_votes[ppo_action] = action_votes.get(ppo_action, 0) + self.weights['ppo']
        action_votes[a2c_action] = action_votes.get(a2c_action, 0) + self.weights['a2c']
        action_votes[dqn_action] = action_votes.get(dqn_action, 0) + self.weights['dqn']
        
        # Seleccionar acción con mayor peso
        ensemble_action = max(action_votes, key=action_votes.get)
        
        # Promediar valores de confianza
        ensemble_value = (ppo_value * self.weights['ppo'] + 
                         a2c_value * self.weights['a2c'] + 
                         dqn_q_value * self.weights['dqn'])
        
        return ensemble_action, 0.0, ensemble_value
    
    def store_transition(self, state, action, reward, next_state, done, log_prob=None, value=None):
        """Almacenar transición en todos los agentes"""
        self.ppo_agent.store_transition(state, action, reward, next_state, done, log_prob, value)
        self.a2c_agent.store_transition(state, action, reward, next_state, done, log_prob, value)
        self.dqn_agent.store_transition(state, action, reward, next_state, done)
    
    def update(self):
        """Actualizar todos los agentes del ensemble"""
        self.ppo_agent.update()
        self.a2c_agent.update()
        self.dqn_agent.update()
        
        # Actualizar pesos basado en rendimiento
        self._update_weights()
    
    def _update_weights(self):
        """Actualizar pesos del ensemble basado en rendimiento"""
        # Calcular rendimiento relativo
        total_performance = 0
        for agent_name in ['ppo', 'a2c', 'dqn']:
            metrics = self.performance_metrics[agent_name]
            if metrics['total'] > 0:
                win_rate = metrics['wins'] / metrics['total']
                avg_reward = metrics['avg_reward']
                performance = win_rate * 0.6 + (avg_reward + 1) * 0.4  # Normalizar reward
                total_performance += max(performance, 0.1)  # Mínimo peso
                self.performance_metrics[agent_name]['performance'] = performance
        
        # Redistribuir pesos
        if total_performance > 0:
            for agent_name in ['ppo', 'a2c', 'dqn']:
                if 'performance' in self.performance_metrics[agent_name]:
                    new_weight = self.performance_metrics[agent_name]['performance'] / total_performance
                    # Suavizar cambios de peso
                    self.weights[agent_name] = 0.9 * self.weights[agent_name] + 0.1 * new_weight
    
    def update_performance(self, agent_name, reward, is_win):
        """Actualizar métricas de rendimiento de un agente"""
        if agent_name in self.performance_metrics:
            metrics = self.performance_metrics[agent_name]
            metrics['total'] += 1
            if is_win:
                metrics['wins'] += 1
            
            # Promedio móvil de recompensas
            alpha = 0.1
            metrics['avg_reward'] = (1 - alpha) * metrics['avg_reward'] + alpha * reward
    
    def get_ensemble_metrics(self):
        """Obtener métricas del ensemble"""
        return {
            'weights': self.weights.copy(),
            'performance': self.performance_metrics.copy(),
            'ppo_metrics': self.ppo_agent.get_training_metrics(),
            'a2c_metrics': self.a2c_agent.get_training_metrics(),
            'dqn_metrics': self.dqn_agent.get_training_metrics()
        }
    
    def save_ensemble(self, base_filepath):
        """Guardar todos los modelos del ensemble"""
        self.ppo_agent.save_model(f"{base_filepath}_ppo.pth")
        self.a2c_agent.save_model(f"{base_filepath}_a2c.pth")
        self.dqn_agent.save_model(f"{base_filepath}_dqn.pth")
        
        # Guardar configuración del ensemble
        ensemble_config = {
            'weights': self.weights,
            'performance_metrics': self.performance_metrics,
            'state_dim': self.state_dim,
            'action_dim': self.action_dim
        }
        
        import json
        with open(f"{base_filepath}_ensemble_config.json", 'w') as f:
            json.dump(ensemble_config, f, indent=2)
        
        logger.info(f"Ensemble DRL guardado en: {base_filepath}")
    
    def load_ensemble(self, base_filepath):
        """Cargar todos los modelos del ensemble"""
        self.ppo_agent.load_model(f"{base_filepath}_ppo.pth")
        self.a2c_agent.load_model(f"{base_filepath}_a2c.pth")
        self.dqn_agent.load_model(f"{base_filepath}_dqn.pth")
        
        # Cargar configuración del ensemble
        import json
        try:
            with open(f"{base_filepath}_ensemble_config.json", 'r') as f:
                ensemble_config = json.load(f)
                self.weights = ensemble_config['weights']
                self.performance_metrics = ensemble_config['performance_metrics']
        except FileNotFoundError:
            logger.warning("Configuración del ensemble no encontrada, usando valores por defecto")
        
        logger.info(f"Ensemble DRL cargado desde: {base_filepath}")


class TradingEnvironment:
    """
    Entorno de trading para el agente PPO
    Integrado con las características de SICAR
    """
    
    def __init__(self, data, initial_balance=10000, transaction_cost=0.001):
        """
        Inicializar entorno de trading
        
        Args:
            data: DataFrame con datos de mercado
            initial_balance: Balance inicial
            transaction_cost: Costo de transacción
        """
        self.data = data
        self.initial_balance = initial_balance
        self.transaction_cost = transaction_cost
        
        # Estado del entorno
        self.current_step = 0
        self.balance = initial_balance
        self.position = 0  # 0: sin posición, 1: long, -1: short
        self.position_size = 0
        self.entry_price = 0
        
        # Métricas de rendimiento
        self.total_reward = 0
        self.trades_count = 0
        self.winning_trades = 0
        self.max_drawdown = 0
        self.peak_balance = initial_balance
        
        # Acciones: 0=hold, 1=buy, 2=sell, 3=close_position
        self.action_space = 4
        
        logger.info(f"Entorno de trading inicializado - Balance: ${initial_balance}")
    
    def reset(self):
        """Reiniciar entorno"""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.position_size = 0
        self.entry_price = 0
        self.total_reward = 0
        self.trades_count = 0
        self.winning_trades = 0
        self.max_drawdown = 0
        self.peak_balance = self.initial_balance
        
        return self._get_state()
    
    def step(self, action):
        """
        Ejecutar acción en el entorno
        
        Args:
            action: Acción a ejecutar (0-3)
            
        Returns:
            next_state: Siguiente estado
            reward: Recompensa obtenida
            done: Si el episodio terminó
            info: Información adicional
        """
        if self.current_step >= len(self.data) - 1:
            return self._get_state(), 0, True, {}
        
        current_price = self.data.iloc[self.current_step]['close']
        reward = 0
        
        # Ejecutar acción
        if action == 1:  # Buy
            reward = self._execute_buy(current_price)
        elif action == 2:  # Sell
            reward = self._execute_sell(current_price)
        elif action == 3:  # Close position
            reward = self._close_position(current_price)
        # action == 0 (hold) no hace nada
        
        # Calcular recompensa adicional basada en el movimiento del precio
        if self.current_step > 0:
            price_change = (current_price - self.data.iloc[self.current_step - 1]['close']) / self.data.iloc[self.current_step - 1]['close']
            
            if self.position == 1:  # Long position
                reward += price_change * 100  # Amplificar recompensa
            elif self.position == -1:  # Short position
                reward -= price_change * 100
        
        # Penalización por drawdown excesivo
        current_balance = self._calculate_current_balance(current_price)
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        drawdown = (self.peak_balance - current_balance) / self.peak_balance
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
        
        if drawdown > 0.2:  # Penalizar drawdown > 20%
            reward -= drawdown * 50
        
        self.total_reward += reward
        self.current_step += 1
        
        # Verificar si el episodio terminó
        done = (self.current_step >= len(self.data) - 1) or (current_balance <= self.initial_balance * 0.5)
        
        return self._get_state(), reward, done, {
            'balance': current_balance,
            'position': self.position,
            'drawdown': drawdown,
            'trades_count': self.trades_count
        }
    
    def _execute_buy(self, price):
        """Ejecutar orden de compra"""
        if self.position != 1:  # No está en long
            if self.position == -1:  # Cerrar short primero
                self._close_position(price)
            
            # Abrir posición long
            self.position = 1
            self.position_size = self.balance * 0.95  # Usar 95% del balance
            self.entry_price = price
            self.balance -= self.position_size * self.transaction_cost
            self.trades_count += 1
            
            return 1  # Recompensa por abrir posición
        return 0
    
    def _execute_sell(self, price):
        """Ejecutar orden de venta"""
        if self.position != -1:  # No está en short
            if self.position == 1:  # Cerrar long primero
                self._close_position(price)
            
            # Abrir posición short
            self.position = -1
            self.position_size = self.balance * 0.95
            self.entry_price = price
            self.balance -= self.position_size * self.transaction_cost
            self.trades_count += 1
            
            return 1  # Recompensa por abrir posición
        return 0
    
    def _close_position(self, price):
        """Cerrar posición actual"""
        if self.position == 0:
            return 0
        
        # Calcular P&L
        if self.position == 1:  # Cerrar long
            pnl = (price - self.entry_price) / self.entry_price * self.position_size
        else:  # Cerrar short
            pnl = (self.entry_price - price) / self.entry_price * self.position_size
        
        # Aplicar costos de transacción
        pnl -= self.position_size * self.transaction_cost
        
        self.balance += self.position_size + pnl
        
        # Actualizar estadísticas
        if pnl > 0:
            self.winning_trades += 1
        
        # Resetear posición
        self.position = 0
        self.position_size = 0
        self.entry_price = 0
        
        return pnl / self.initial_balance * 100  # Recompensa proporcional al P&L
    
    def _calculate_current_balance(self, price):
        """Calcular balance actual incluyendo posiciones abiertas"""
        if self.position == 0:
            return self.balance
        
        if self.position == 1:  # Long
            unrealized_pnl = (price - self.entry_price) / self.entry_price * self.position_size
        else:  # Short
            unrealized_pnl = (self.entry_price - price) / self.entry_price * self.position_size
        
        return self.balance + self.position_size + unrealized_pnl
    
    def _get_state(self):
        """Obtener estado actual del entorno"""
        if self.current_step >= len(self.data):
            return np.zeros(20)  # Estado por defecto
        
        # Features técnicos básicos
        current_data = self.data.iloc[max(0, self.current_step-19):self.current_step+1]
        
        if len(current_data) < 20:
            # Rellenar con ceros si no hay suficientes datos
            state = np.zeros(20)
            available_data = len(current_data)
            if available_data > 0:
                state[-available_data:] = current_data['close'].pct_change().fillna(0).values
        else:
            # Retornos de los últimos 20 períodos
            returns = current_data['close'].pct_change().fillna(0).values
            state = returns
        
        # Añadir información de posición actual
        position_info = np.array([
            self.position,  # Posición actual
            self.balance / self.initial_balance,  # Balance normalizado
            self.max_drawdown  # Drawdown máximo
        ])
        
        return np.concatenate([state, position_info])
    
    def get_performance_metrics(self):
        """Obtener métricas de rendimiento"""
        current_balance = self._calculate_current_balance(
            self.data.iloc[self.current_step]['close'] if self.current_step < len(self.data) else self.data.iloc[-1]['close']
        )
        
        total_return = (current_balance - self.initial_balance) / self.initial_balance * 100
        win_rate = self.winning_trades / max(1, self.trades_count) * 100
        
        return {
            'total_return': total_return,
            'final_balance': current_balance,
            'max_drawdown': self.max_drawdown * 100,
            'trades_count': self.trades_count,
            'win_rate': win_rate,
            'total_reward': self.total_reward
        }


class AdvancedMLEngine:
    def __init__(self):
        """Inicializar motor de ML avanzado con DRL"""
        self.models = {}
        self.scalers = {}
        self.feature_selectors = {}
        self.feature_importance = {}
        
        # Agente PPO
        self.ppo_agent = None
        self.trading_env = None
        
        # Parámetros optimizados
        self.lookback_periods = [5, 10, 20, 50]
        self.feature_selection_k = 50  # Top 50 features
        self.ensemble_size = 7  # 7 modelos en ensemble
        self.cv_folds = 5
        self.min_samples_for_training = 200
        
        logger.info("Motor de ML avanzado con DRL inicializado")
    
    def initialize_ppo_agent(self, state_dim=23, action_dim=4, **kwargs):
        """
        Inicializar agente PPO para trading
        
        Args:
            state_dim: Dimensión del espacio de estados
            action_dim: Dimensión del espacio de acciones
            **kwargs: Parámetros adicionales para PPO
        """
        self.ppo_agent = PPOAgent(state_dim, action_dim, **kwargs)
        logger.info(f"Agente PPO inicializado - Estado: {state_dim}, Acciones: {action_dim}")
    
    def create_trading_environment(self, data, **kwargs):
        """
        Crear entorno de trading para DRL
        
        Args:
            data: DataFrame con datos de mercado
            **kwargs: Parámetros adicionales para el entorno
        """
        self.trading_env = TradingEnvironment(data, **kwargs)
        logger.info("Entorno de trading creado")
    
    def train_ppo_agent(self, episodes=1000, max_steps_per_episode=1000):
        """
        Entrenar agente PPO
        
        Args:
            episodes: Número de episodios de entrenamiento
            max_steps_per_episode: Máximo de pasos por episodio
        """
        if not self.ppo_agent or not self.trading_env:
            raise ValueError("Agente PPO y entorno deben estar inicializados")
        
        logger.info(f"Iniciando entrenamiento PPO - {episodes} episodios")
        
        episode_rewards = []
        episode_lengths = []
        
        for episode in range(episodes):
            state = self.trading_env.reset()
            episode_reward = 0
            episode_length = 0
            
            for step in range(max_steps_per_episode):
                # Seleccionar acción
                action, log_prob, value = self.ppo_agent.select_action(state)
                
                # Ejecutar acción
                next_state, reward, done, info = self.trading_env.step(action)
                
                # Almacenar transición
                self.ppo_agent.store_transition(
                    state, action, reward, next_state, done, log_prob, value
                )
                
                episode_reward += reward
                episode_length += 1
                state = next_state
                
                if done:
                    break
            
            # Actualizar agente
            self.ppo_agent.update()
            
            episode_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
            
            # Log progreso
            if episode % 100 == 0:
                avg_reward = np.mean(episode_rewards[-100:])
                avg_length = np.mean(episode_lengths[-100:])
                metrics = self.ppo_agent.get_training_metrics()
                
                logger.info(f"Episodio {episode}: Reward promedio: {avg_reward:.2f}, "
                           f"Longitud promedio: {avg_length:.1f}, "
                           f"Exploración: {metrics.get('exploration_rate', 0):.3f}")
        
        # Guardar métricas finales
        self.ppo_agent.training_metrics['rewards'] = episode_rewards
        self.ppo_agent.training_metrics['episode_lengths'] = episode_lengths
        
        logger.info("Entrenamiento PPO completado")
        
        return {
            'episode_rewards': episode_rewards,
            'episode_lengths': episode_lengths,
            'final_metrics': self.ppo_agent.get_training_metrics()
        }
    
    def evaluate_ppo_agent(self, test_data, episodes=10):
        """
        Evaluar agente PPO entrenado
        
        Args:
            test_data: Datos de prueba
            episodes: Número de episodios de evaluación
        """
        if not self.ppo_agent:
            raise ValueError("Agente PPO debe estar entrenado")
        
        # Crear entorno de prueba
        test_env = TradingEnvironment(test_data)
        
        results = []
        
        for episode in range(episodes):
            state = test_env.reset()
            episode_reward = 0
            
            while True:
                # Seleccionar acción determinísticamente
                action, _, _ = self.ppo_agent.select_action(state, deterministic=True)
                
                next_state, reward, done, info = test_env.step(action)
                episode_reward += reward
                state = next_state
                
                if done:
                    break
            
            performance = test_env.get_performance_metrics()
            performance['episode_reward'] = episode_reward
            results.append(performance)
        
        # Calcular métricas promedio
        avg_metrics = {}
        for key in results[0].keys():
            avg_metrics[f'avg_{key}'] = np.mean([r[key] for r in results])
            avg_metrics[f'std_{key}'] = np.std([r[key] for r in results])
        
        logger.info(f"Evaluación PPO completada - Retorno promedio: {avg_metrics['avg_total_return']:.2f}%")
        
        return avg_metrics, results

    def create_price_features(self, df):
        """Crear features avanzadas de precio"""
        try:
            features = pd.DataFrame(index=df.index)
            
            # 1. Retornos múltiples
            for period in [1, 2, 3, 5, 10, 20]:
                features[f'return_{period}'] = df['close'].pct_change(period)
                features[f'log_return_{period}'] = np.log(df['close'] / df['close'].shift(period))
            
            # 2. Volatilidad realizada
            for period in [5, 10, 20]:
                returns = df['close'].pct_change()
                features[f'realized_vol_{period}'] = returns.rolling(period).std()
                features[f'vol_of_vol_{period}'] = features[f'realized_vol_{period}'].rolling(period).std()
            
            # 3. Rangos de precio
            features['true_range'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            
            for period in [5, 10, 20]:
                features[f'atr_{period}'] = features['true_range'].rolling(period).mean()
                features[f'atr_pct_{period}'] = features[f'atr_{period}'] / df['close']
            
            # 4. Gaps y discontinuidades
            features['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
            features['gap_filled'] = (
                (df['low'] <= df['close'].shift(1)) & 
                (df['high'] >= df['close'].shift(1))
            ).astype(int)
            
            # 5. Niveles de precio
            for period in [20, 50]:
                features[f'price_position_{period}'] = (
                    (df['close'] - df['close'].rolling(period).min()) / 
                    (df['close'].rolling(period).max() - df['close'].rolling(period).min())
                )
            
            # 6. Momentum de precio
            for period in [5, 10, 20]:
                features[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
                features[f'acceleration_{period}'] = features[f'momentum_{period}'].diff()
            
            return features.fillna(0)
            
        except Exception as e:
            logger.error(f"Error creando features de precio: {e}")
            return pd.DataFrame(index=df.index)

    def create_volume_features(self, df):
        """Crear features avanzadas de volumen"""
        try:
            features = pd.DataFrame(index=df.index)
            
            # 1. Volumen relativo
            for period in [5, 10, 20, 50]:
                features[f'volume_sma_{period}'] = df['volume'].rolling(period).mean()
                features[f'volume_ratio_{period}'] = df['volume'] / features[f'volume_sma_{period}']
            
            # 2. Volumen ponderado por precio
            features['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()
            features['price_vs_vwap'] = df['close'] / features['vwap'] - 1
            
            # 3. On-Balance Volume
            price_change = df['close'].diff()
            features['obv'] = (df['volume'] * np.sign(price_change)).cumsum()
            features['obv_sma_10'] = features['obv'].rolling(10).mean()
            features['obv_momentum'] = features['obv'] / features['obv_sma_10'] - 1
            
            # 4. Volume Rate of Change
            for period in [5, 10]:
                features[f'volume_roc_{period}'] = df['volume'].pct_change(period)
            
            # 5. Accumulation/Distribution Line
            clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
            clv = clv.fillna(0)
            features['ad_line'] = (clv * df['volume']).cumsum()
            features['ad_line_sma_10'] = features['ad_line'].rolling(10).mean()
            
            # 6. Volume-Price Trend
            features['vpt'] = (df['volume'] * df['close'].pct_change()).cumsum()
            
            # 7. Ease of Movement
            distance_moved = (df['high'] + df['low']) / 2 - (df['high'].shift(1) + df['low'].shift(1)) / 2
            box_height = df['volume'] / (df['high'] - df['low'])
            features['eom'] = distance_moved / box_height
            features['eom_sma_14'] = features['eom'].rolling(14).mean()
            
            return features.fillna(0)
            
        except Exception as e:
            logger.error(f"Error creando features de volumen: {e}")
            return pd.DataFrame(index=df.index)

    def create_technical_features(self, df):
        """Crear features técnicas avanzadas"""
        try:
            features = pd.DataFrame(index=df.index)
            
            # 1. RSI múltiples
            for period in [7, 14, 21, 28]:
                features[f'rsi_{period}'] = talib.RSI(df['close'], timeperiod=period)
                features[f'rsi_{period}_sma_5'] = features[f'rsi_{period}'].rolling(5).mean()
            
            # 2. MACD variaciones
            for fast, slow, signal in [(12, 26, 9), (5, 35, 5), (19, 39, 9)]:
                macd, macd_signal, macd_hist = talib.MACD(df['close'], fastperiod=fast, slowperiod=slow, signalperiod=signal)
                features[f'macd_{fast}_{slow}'] = macd
                features[f'macd_signal_{fast}_{slow}'] = macd_signal
                features[f'macd_hist_{fast}_{slow}'] = macd_hist
                features[f'macd_hist_momentum_{fast}_{slow}'] = macd_hist.diff()
            
            # 3. Stochastic variaciones
            for k_period, d_period in [(14, 3), (21, 3), (14, 5)]:
                slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'], 
                                         fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
                features[f'stoch_k_{k_period}_{d_period}'] = slowk
                features[f'stoch_d_{k_period}_{d_period}'] = slowd
                features[f'stoch_momentum_{k_period}_{d_period}'] = slowk - slowd
            
            # 4. Bollinger Bands variaciones
            for period, std_dev in [(20, 2), (20, 1.5), (10, 2)]:
                bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'], timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
                features[f'bb_upper_{period}_{std_dev}'] = bb_upper
                features[f'bb_lower_{period}_{std_dev}'] = bb_lower
                features[f'bb_width_{period}_{std_dev}'] = (bb_upper - bb_lower) / bb_middle
                features[f'bb_position_{period}_{std_dev}'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
                features[f'bb_squeeze_{period}_{std_dev}'] = features[f'bb_width_{period}_{std_dev}'].rolling(20).min() == features[f'bb_width_{period}_{std_dev}']
            
            # 5. Williams %R
            for period in [14, 21]:
                features[f'williams_r_{period}'] = talib.WILLR(df['high'], df['low'], df['close'], timeperiod=period)
            
            # 6. CCI (Commodity Channel Index)
            for period in [14, 20]:
                features[f'cci_{period}'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=period)
            
            # 7. ADX y DI
            for period in [14, 21]:
                features[f'adx_{period}'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=period)
                features[f'plus_di_{period}'] = talib.PLUS_DI(df['high'], df['low'], df['close'], timeperiod=period)
                features[f'minus_di_{period}'] = talib.MINUS_DI(df['high'], df['low'], df['close'], timeperiod=period)
                features[f'di_diff_{period}'] = features[f'plus_di_{period}'] - features[f'minus_di_{period}']
            
            # 8. Parabolic SAR
            features['sar'] = talib.SAR(df['high'], df['low'])
            features['sar_signal'] = (df['close'] > features['sar']).astype(int)
            
            # 9. Aroon
            aroon_down, aroon_up = talib.AROON(df['high'], df['low'], timeperiod=14)
            features['aroon_up'] = aroon_up
            features['aroon_down'] = aroon_down
            features['aroon_oscillator'] = aroon_up - aroon_down
            
            return features.fillna(0)
            
        except Exception as e:
            logger.error(f"Error creando features técnicas: {e}")
            return pd.DataFrame(index=df.index)

    def create_statistical_features(self, df):
        """Crear features estadísticas avanzadas"""
        try:
            features = pd.DataFrame(index=df.index)
            
            # 1. Momentos estadísticos
            for period in [10, 20, 50]:
                returns = df['close'].pct_change()
                features[f'skewness_{period}'] = returns.rolling(period).apply(lambda x: skew(x.dropna()))
                features[f'kurtosis_{period}'] = returns.rolling(period).apply(lambda x: kurtosis(x.dropna()))
                features[f'jarque_bera_{period}'] = features[f'skewness_{period}']**2 + features[f'kurtosis_{period}']**2/4
            
            # 2. Percentiles móviles
            for period in [20, 50]:
                for percentile in [10, 25, 75, 90]:
                    features[f'percentile_{percentile}_{period}'] = df['close'].rolling(period).quantile(percentile/100)
                    features[f'price_vs_p{percentile}_{period}'] = df['close'] / features[f'percentile_{percentile}_{period}'] - 1
            
            # 3. Z-Score
            for period in [20, 50]:
                mean = df['close'].rolling(period).mean()
                std = df['close'].rolling(period).std()
                features[f'zscore_{period}'] = (df['close'] - mean) / std
            
            # 4. Autocorrelación
            for lag in [1, 5, 10]:
                for period in [20, 50]:
                    returns = df['close'].pct_change()
                    features[f'autocorr_lag{lag}_{period}'] = returns.rolling(period).apply(
                        lambda x: x.autocorr(lag=lag) if len(x.dropna()) > lag else 0
                    )
            
            # 5. Hurst Exponent (simplificado)
            for period in [50, 100]:
                if len(df) >= period:
                    returns = df['close'].pct_change()
                    features[f'hurst_{period}'] = returns.rolling(period).apply(
                        lambda x: self.calculate_hurst_exponent(x.dropna()) if len(x.dropna()) > 10 else 0.5
                    )
            
            # 6. Fractal Dimension
            for period in [20, 50]:
                features[f'fractal_dim_{period}'] = df['close'].rolling(period).apply(
                    lambda x: self.calculate_fractal_dimension(x.dropna()) if len(x.dropna()) > 5 else 1.5
                )
            
            return features.fillna(0)
            
        except Exception as e:
            logger.error(f"Error creando features estadísticas: {e}")
            return pd.DataFrame(index=df.index)

    def calculate_hurst_exponent(self, series):
        """Calcular exponente de Hurst simplificado"""
        try:
            if len(series) < 10:
                return 0.5
            
            lags = range(2, min(20, len(series)//2))
            tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
            
            if len(tau) < 2:
                return 0.5
            
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0
            
        except:
            return 0.5

    def calculate_fractal_dimension(self, series):
        """Calcular dimensión fractal simplificada"""
        try:
            if len(series) < 5:
                return 1.5
            
            # Método de conteo de cajas simplificado
            scales = np.logspace(0.01, 0.2, num=10)
            counts = []
            
            for scale in scales:
                boxes = int(np.ceil((series.max() - series.min()) / scale))
                if boxes > 0:
                    counts.append(boxes)
                else:
                    counts.append(1)
            
            if len(counts) < 2:
                return 1.5
            
            coeffs = np.polyfit(np.log(scales), np.log(counts), 1)
            return -coeffs[0]
            
        except:
            return 1.5

    def create_pattern_features(self, df):
        """Crear features de patrones"""
        try:
            features = pd.DataFrame(index=df.index)
            
            # 1. Patrones de velas japonesas
            candlestick_patterns = [
                'CDLDOJI', 'CDLHAMMER', 'CDLSHOOTINGSTAR', 'CDLENGULFING',
                'CDLHARAMI', 'CDLPIERCING', 'CDLDARKCLOUDCOVER', 'CDLMORNINGSTAR',
                'CDLEVENINGSTAR', 'CDLTHREEWHITESOLDIERS', 'CDLTHREEBLACKCROWS'
            ]
            
            for pattern in candlestick_patterns:
                try:
                    features[pattern.lower()] = getattr(talib, pattern)(df['open'], df['high'], df['low'], df['close'])
                except:
                    features[pattern.lower()] = 0
            
            # 2. Patrones de soporte/resistencia
            for period in [20, 50]:
                # Niveles de soporte y resistencia
                features[f'support_{period}'] = df['low'].rolling(period).min()
                features[f'resistance_{period}'] = df['high'].rolling(period).max()
                
                # Distancia a S/R
                features[f'dist_to_support_{period}'] = (df['close'] - features[f'support_{period}']) / df['close']
                features[f'dist_to_resistance_{period}'] = (features[f'resistance_{period}'] - df['close']) / df['close']
                
                # Toques de S/R
                support_touch = abs(df['low'] - features[f'support_{period}']) / df['close'] < 0.01
                resistance_touch = abs(df['high'] - features[f'resistance_{period}']) / df['close'] < 0.01
                features[f'support_touches_{period}'] = support_touch.rolling(period).sum()
                features[f'resistance_touches_{period}'] = resistance_touch.rolling(period).sum()
            
            # 3. Patrones de tendencia
            for period in [10, 20]:
                # Línea de tendencia simplificada
                x = np.arange(period)
                features[f'trend_slope_{period}'] = df['close'].rolling(period).apply(
                    lambda y: np.polyfit(x, y, 1)[0] if len(y) == period else 0
                )
                features[f'trend_r2_{period}'] = df['close'].rolling(period).apply(
                    lambda y: np.corrcoef(x, y)[0, 1]**2 if len(y) == period else 0
                )
            
            # 4. Divergencias
            # RSI vs Precio
            rsi = talib.RSI(df['close'])
            features['rsi_price_divergence'] = (
                (df['close'].diff() > 0) & (rsi.diff() < 0) |
                (df['close'].diff() < 0) & (rsi.diff() > 0)
            ).astype(int)
            
            return features.fillna(0)
            
        except Exception as e:
            logger.error(f"Error creando features de patrones: {e}")
            return pd.DataFrame(index=df.index)

    def create_market_microstructure_features(self, df):
        """Crear features avanzadas de microestructura de mercado basadas en QuantConnect"""
        try:
            features = pd.DataFrame(index=df.index)
            
            # 1. Spread Analysis (Bid-Ask Spread simulado)
            features['hl_spread'] = (df['high'] - df['low']) / df['close']
            features['hl_spread_sma_10'] = features['hl_spread'].rolling(10).mean()
            features['relative_spread'] = features['hl_spread'] / features['hl_spread_sma_10']
            features['spread_volatility'] = features['hl_spread'].rolling(20).std()
            features['spread_percentile'] = features['hl_spread'].rolling(100).rank(pct=True)
            
            # 2. Tick Direction and Runs Analysis
            features['tick_direction'] = np.sign(df['close'].diff())
            features['tick_runs'] = features['tick_direction'].groupby(
                (features['tick_direction'] != features['tick_direction'].shift()).cumsum()
            ).cumsum()
            features['tick_run_length'] = features.groupby(
                (features['tick_direction'] != features['tick_direction'].shift()).cumsum()
            )['tick_direction'].transform('count')
            
            # 3. Advanced Price Impact Models
            for period in [5, 10, 20]:
                # Volume-weighted price impact
                volume_buckets = pd.qcut(df['volume'], q=10, labels=False, duplicates='drop')
                features[f'price_impact_{period}'] = df['close'].pct_change(period) / np.sqrt(volume_buckets + 1)
                
                # Temporary vs Permanent Impact
                features[f'temp_impact_{period}'] = (df['close'] - df['close'].shift(1)) / np.sqrt(df['volume'])
                features[f'perm_impact_{period}'] = (df['close'].shift(-period) - df['close']) / np.sqrt(df['volume'])
            
            # 4. Order Flow Imbalance (OFI) - Advanced
            features['ofi'] = df['volume'] * features['tick_direction']
            features['ofi_sma_10'] = features['ofi'].rolling(10).mean()
            features['ofi_sma_30'] = features['ofi'].rolling(30).mean()
            features['ofi_momentum'] = features['ofi_sma_10'] - features['ofi_sma_30']
            features['ofi_acceleration'] = features['ofi_momentum'].diff()
            
            # 5. Volume-Synchronized Probability of Informed Trading (VPIN)
            for window in [20, 50]:
                # Calcular VPIN aproximado
                volume_imbalance = abs(features['ofi']).rolling(window).sum()
                total_volume = df['volume'].rolling(window).sum()
                features[f'vpin_{window}'] = volume_imbalance / total_volume
            
            # 6. Realized Spread and Effective Spread
            mid_price = (df['high'] + df['low']) / 2
            for period in [5, 10, 20]:
                features[f'realized_spread_{period}'] = (
                    2 * features['tick_direction'] * 
                    (df['close'] - mid_price.shift(period))
                )
                features[f'effective_spread_{period}'] = 2 * abs(df['close'] - mid_price)
            
            # 7. Market Depth Indicators (simulados)
            features['depth_imbalance'] = (df['high'] - df['close']) / (df['close'] - df['low'] + 1e-8)
            features['depth_pressure'] = features['depth_imbalance'].rolling(10).mean()
            
            # 8. Liquidity Measures
            # Amihud Illiquidity Ratio
            features['amihud_illiq'] = abs(df['close'].pct_change()) / (df['volume'] + 1e-8)
            features['amihud_illiq_sma'] = features['amihud_illiq'].rolling(20).mean()
            
            # Roll's Effective Spread Estimator
            price_changes = df['close'].diff()
            features['roll_spread'] = 2 * np.sqrt(abs(price_changes.rolling(20).cov(price_changes.shift(1))))
            
            # 9. Microstructure Noise
            # Variance ratio test components
            for lag in [2, 5, 10]:
                returns_lag = df['close'].pct_change(lag)
                returns_1 = df['close'].pct_change()
                var_ratio = returns_lag.rolling(50).var() / (lag * returns_1.rolling(50).var())
                features[f'variance_ratio_{lag}'] = var_ratio
            
            # 10. Trade Classification (Lee-Ready Algorithm simulado)
            quote_midpoint = mid_price
            features['trade_classification'] = np.where(
                df['close'] > quote_midpoint, 1,  # Buy-initiated
                np.where(df['close'] < quote_midpoint, -1, 0)  # Sell-initiated or at midpoint
            )
            
            # 11. Adverse Selection Measures
            # Kyle's Lambda (price impact per unit volume)
            for window in [20, 50]:
                price_change = df['close'].pct_change()
                signed_volume = df['volume'] * features['tick_direction']
                kyle_lambda = price_change.rolling(window).cov(signed_volume) / signed_volume.rolling(window).var()
                features[f'kyle_lambda_{window}'] = kyle_lambda
            
            # 12. Intraday Patterns
            if 'timestamp' in df.columns:
                try:
                    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
                    df['minute'] = pd.to_datetime(df['timestamp']).dt.minute
                    
                    # U-shaped intraday pattern
                    features['intraday_pattern'] = np.where(
                        (df['hour'] < 10) | (df['hour'] > 15), 1.2,  # High activity
                        np.where((df['hour'] >= 12) & (df['hour'] <= 14), 0.8, 1.0)  # Low activity
                    )
                except:
                    features['intraday_pattern'] = 1.0
            else:
                features['intraday_pattern'] = 1.0
            
            # 13. Fragmentation and Consolidation Measures
            # Price clustering
            price_digits = df['close'].astype(str).str.split('.').str[1].str.len().fillna(0)
            features['price_clustering'] = (price_digits == 0).astype(int)
            
            # 14. Information Content Measures
            # Probability of Informed Trading (PIN) approximation
            buy_volume = df['volume'] * (features['tick_direction'] > 0)
            sell_volume = df['volume'] * (features['tick_direction'] < 0)
            total_volume = buy_volume + sell_volume
            
            features['pin_approx'] = abs(buy_volume - sell_volume) / (total_volume + 1e-8)
            features['pin_sma'] = features['pin_approx'].rolling(20).mean()
            
            # 15. Market Making Profitability Indicators
            # Inventory risk
            cumulative_signed_volume = (df['volume'] * features['tick_direction']).cumsum()
            features['inventory_risk'] = abs(cumulative_signed_volume) / df['volume'].rolling(100).sum()
            
            # Expected market making profit
            features['mm_profit_expectation'] = features['hl_spread'] - 2 * features['amihud_illiq']
            
            # 16. Regime Detection for Microstructure
            # Volatility regime
            volatility = df['close'].pct_change().rolling(20).std()
            vol_percentile = volatility.rolling(100).rank(pct=True)
            features['vol_regime'] = np.where(vol_percentile > 0.8, 2,  # High vol
                                            np.where(vol_percentile < 0.2, 0, 1))  # Low/Normal vol
            
            # Volume regime
            volume_percentile = df['volume'].rolling(100).rank(pct=True)
            features['volume_regime'] = np.where(volume_percentile > 0.8, 2,  # High volume
                                               np.where(volume_percentile < 0.2, 0, 1))  # Low/Normal volume
            
            return features.fillna(0)
            
        except Exception as e:
            logger.error(f"Error creando features de microestructura: {e}")
            return pd.DataFrame(index=df.index)

    def create_all_features(self, df):
        """Crear todas las features"""
        try:
            logger.info("Creando features avanzadas...")
            
            # Crear diferentes grupos de features
            price_features = self.create_price_features(df)
            volume_features = self.create_volume_features(df)
            technical_features = self.create_technical_features(df)
            statistical_features = self.create_statistical_features(df)
            pattern_features = self.create_pattern_features(df)
            microstructure_features = self.create_market_microstructure_features(df)
            
            # Combinar todas las features
            all_features = pd.concat([
                price_features,
                volume_features,
                technical_features,
                statistical_features,
                pattern_features,
                microstructure_features
            ], axis=1)
            
            # Limpiar features
            all_features = all_features.fillna(0)
            all_features = all_features.replace([np.inf, -np.inf], 0)
            
            logger.info(f"Features creadas: {all_features.shape[1]} columnas")
            return all_features
            
        except Exception as e:
            logger.error(f"Error creando features: {e}")
            return pd.DataFrame(index=df.index)

    def create_targets(self, df, lookahead_periods=[3, 5, 10]):
        """Crear targets optimizados"""
        try:
            targets = pd.DataFrame(index=df.index)
            
            for period in lookahead_periods:
                # Retorno futuro
                future_return = df['close'].shift(-period) / df['close'] - 1
                
                # Clasificación adaptativa basada en volatilidad
                volatility = df['close'].pct_change().rolling(20).std()
                
                # Thresholds dinámicos
                buy_threshold = 0.015 + volatility * 2  # Base 1.5% + volatilidad
                sell_threshold = -(0.01 + volatility * 1.5)  # Base -1% - volatilidad
                
                # Crear señales
                signals = []
                for i, ret in enumerate(future_return):
                    if pd.isna(ret):
                        signals.append(0)
                    elif ret > buy_threshold.iloc[i]:
                        signals.append(1)  # BUY
                    elif ret < sell_threshold.iloc[i]:
                        signals.append(-1)  # SELL
                    else:
                        signals.append(0)  # HOLD
                
                targets[f'target_{period}'] = signals
            
            # Target principal (promedio ponderado)
            weights = [0.5, 0.3, 0.2]  # Más peso a corto plazo
            targets['target_main'] = (
                targets['target_3'] * weights[0] +
                targets['target_5'] * weights[1] +
                targets['target_10'] * weights[2]
            ).round().astype(int)
            
            return targets
            
        except Exception as e:
            logger.error(f"Error creando targets: {e}")
            return pd.DataFrame(index=df.index)

    def select_features(self, X, y, method='rfe'):
        """Selección de features optimizada"""
        try:
            logger.info(f"Seleccionando features con método: {method}")
            
            if method == 'rfe':
                # Recursive Feature Elimination
                estimator = RandomForestClassifier(n_estimators=50, random_state=42)
                selector = RFE(estimator, n_features_to_select=self.feature_selection_k)
                
            elif method == 'univariate':
                # Selección univariada
                selector = SelectKBest(score_func=f_classif, k=self.feature_selection_k)
                
            elif method == 'variance':
                # Selección por varianza + correlación
                from sklearn.feature_selection import VarianceThreshold
                
                # Eliminar features con baja varianza
                var_selector = VarianceThreshold(threshold=0.01)
                X_var = var_selector.fit_transform(X)
                
                # Eliminar features altamente correlacionadas
                corr_matrix = pd.DataFrame(X_var).corr().abs()
                upper_tri = corr_matrix.where(
                    np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
                )
                to_drop = [column for column in upper_tri.columns if any(upper_tri[column] > 0.95)]
                
                X_final = pd.DataFrame(X_var).drop(columns=to_drop)
                
                # Seleccionar top K por importancia
                rf = RandomForestClassifier(n_estimators=50, random_state=42)
                rf.fit(X_final, y)
                
                feature_importance = pd.Series(rf.feature_importances_, index=X_final.columns)
                top_features = feature_importance.nlargest(self.feature_selection_k).index
                
                selector = lambda X: X[top_features] if hasattr(X, 'columns') else X[:, top_features]
                return selector, top_features.tolist()
            
            # Ajustar selector
            X_selected = selector.fit_transform(X, y)
            
            # Obtener features seleccionadas
            if hasattr(selector, 'get_support'):
                selected_features = np.array(X.columns)[selector.get_support()].tolist()
            else:
                selected_features = list(range(X_selected.shape[1]))
            
            logger.info(f"Features seleccionadas: {len(selected_features)}")
            return selector, selected_features
            
        except Exception as e:
            logger.error(f"Error en selección de features: {e}")
            return None, list(X.columns)

    def create_ensemble_models(self):
        """Crear ensemble de modelos optimizados"""
        try:
            models = {}
            
            # 1. Random Forest optimizado
            models['rf'] = RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_split=10,
                min_samples_leaf=5,
                max_features='sqrt',
                bootstrap=True,
                random_state=42,
                n_jobs=-1
            )
            
            # 2. Gradient Boosting optimizado
            models['gb'] = GradientBoostingClassifier(
                n_estimators=150,
                max_depth=8,
                learning_rate=0.1,
                subsample=0.8,
                max_features='sqrt',
                random_state=42
            )
            
            # 3. Extra Trees
            models['et'] = ExtraTreesClassifier(
                n_estimators=150,
                max_depth=12,
                min_samples_split=8,
                min_samples_leaf=4,
                max_features='sqrt',
                bootstrap=True,
                random_state=42,
                n_jobs=-1
            )
            
            # 4. AdaBoost
            models['ada'] = AdaBoostClassifier(
                n_estimators=100,
                learning_rate=1.0,
                random_state=42
            )
            
            # 5. Logistic Regression
            models['lr'] = LogisticRegression(
                C=1.0,
                max_iter=1000,
                random_state=42,
                n_jobs=-1
            )
            
            # 6. Ridge Classifier
            models['ridge'] = RidgeClassifier(
                alpha=1.0,
                random_state=42
            )
            
            # 7. Neural Network
            models['mlp'] = MLPClassifier(
                hidden_layer_sizes=(100, 50),
                activation='relu',
                solver='adam',
                alpha=0.001,
                learning_rate='adaptive',
                max_iter=500,
                random_state=42
            )
            
            return models
            
        except Exception as e:
            logger.error(f"Error creando modelos: {e}")
            return {}

    def train_model(self, symbol, X, y):
        """Entrenar modelo ensemble optimizado"""
        try:
            logger.info(f"Entrenando modelo para {symbol}")
            
            if len(X) < self.min_samples_for_training:
                logger.warning(f"Datos insuficientes para {symbol}: {len(X)} < {self.min_samples_for_training}")
                return False
            
            # Filtrar datos válidos
            valid_idx = ~(pd.isna(y) | np.isinf(X).any(axis=1))
            X_clean = X[valid_idx]
            y_clean = y[valid_idx]
            
            if len(X_clean) < self.min_samples_for_training:
                logger.warning(f"Datos válidos insuficientes para {symbol}")
                return False
            
            # Split temporal
            split_idx = int(len(X_clean) * 0.8)
            X_train, X_test = X_clean[:split_idx], X_clean[split_idx:]
            y_train, y_test = y_clean[:split_idx], y_clean[split_idx:]
            
            # Selección de features
            feature_selector, selected_features = self.select_features(X_train, y_train, method='rfe')
            X_train_selected = feature_selector.transform(X_train)
            X_test_selected = feature_selector.transform(X_test)
            
            # Escalado
            scaler = RobustScaler()
            X_train_scaled = scaler.fit_transform(X_train_selected)
            X_test_scaled = scaler.transform(X_test_selected)
            
            # Crear modelos
            base_models = self.create_ensemble_models()
            
            # Entrenar modelos individuales
            trained_models = {}
            model_scores = {}
            
            for name, model in base_models.items():
                try:
                    # Entrenar modelo
                    model.fit(X_train_scaled, y_train)
                    
                    # Evaluar
                    y_pred = model.predict(X_test_scaled)
                    accuracy = accuracy_score(y_test, y_pred)
                    
                    trained_models[name] = model
                    model_scores[name] = accuracy
                    
                    logger.info(f"Modelo {name} - Accuracy: {accuracy:.3f}")
                    
                except Exception as e:
                    logger.warning(f"Error entrenando modelo {name}: {e}")
            
            if not trained_models:
                logger.error(f"No se pudo entrenar ningún modelo para {symbol}")
                return False
            
            # Crear ensemble con los mejores modelos
            best_models = sorted(model_scores.items(), key=lambda x: x[1], reverse=True)[:5]
            ensemble_models = [(name, trained_models[name]) for name, score in best_models]
            
            # Voting Classifier
            ensemble = VotingClassifier(
                estimators=ensemble_models,
                voting='soft'
            )
            
            # Entrenar ensemble
            ensemble.fit(X_train_scaled, y_train)
            
            # Evaluar ensemble
            y_pred_ensemble = ensemble.predict(X_test_scaled)
            ensemble_accuracy = accuracy_score(y_test, y_pred_ensemble)
            
            logger.info(f"Ensemble {symbol} - Accuracy: {ensemble_accuracy:.3f}")
            
            # Guardar modelo y componentes
            self.models[symbol] = ensemble
            self.scalers[symbol] = scaler
            self.feature_selectors[symbol] = feature_selector
            
            # Calcular importancia de features
            if hasattr(ensemble.estimators_[0], 'feature_importances_'):
                feature_importance = np.mean([
                    estimator.feature_importances_ 
                    for estimator in ensemble.estimators_ 
                    if hasattr(estimator, 'feature_importances_')
                ], axis=0)
                
                self.feature_importance[symbol] = dict(zip(
                    selected_features, feature_importance
                ))
            
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando modelo para {symbol}: {e}")
            return False

    def predict(self, symbol, X):
        """Realizar predicciones con confianza"""
        try:
            if symbol not in self.models:
                return np.zeros(len(X)), np.zeros(len(X))
            
            # Aplicar transformaciones
            X_selected = self.feature_selectors[symbol].transform(X)
            X_scaled = self.scalers[symbol].transform(X_selected)
            
            # Predicciones
            predictions = self.models[symbol].predict(X_scaled)
            probabilities = self.models[symbol].predict_proba(X_scaled)
            
            # Calcular confianza
            confidences = np.max(probabilities, axis=1)
            
            return predictions, confidences
            
        except Exception as e:
            logger.error(f"Error en predicción para {symbol}: {e}")
            return np.zeros(len(X)), np.zeros(len(X))

    def get_feature_importance(self, symbol, top_n=20):
        """Obtener importancia de features"""
        try:
            if symbol not in self.feature_importance:
                return {}
            
            importance = self.feature_importance[symbol]
            sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)
            
            return dict(sorted_importance[:top_n])
            
        except Exception as e:
            logger.error(f"Error obteniendo importancia de features: {e}")
            return {}

    # ==================== MÉTODOS DRL ENSEMBLE ====================
    
    def initialize_drl_ensemble(self, symbol, state_dim=None, action_dim=3, **kwargs):
        """
        Inicializar ensemble DRL para un símbolo específico
        
        Args:
            symbol: Símbolo de trading
            state_dim: Dimensión del espacio de estados (se calcula automáticamente si es None)
            action_dim: Dimensión del espacio de acciones (3: hold, buy, sell)
            **kwargs: Parámetros adicionales para los agentes
        """
        try:
            # Calcular dimensión del estado si no se proporciona
            if state_dim is None:
                # Usar número de features del último modelo entrenado
                if symbol in self.feature_selectors:
                    state_dim = self.feature_selectors[symbol].k
                else:
                    state_dim = 50  # Valor por defecto
            
            # Inicializar ensemble DRL
            if not hasattr(self, 'drl_ensembles'):
                self.drl_ensembles = {}
            
            self.drl_ensembles[symbol] = DRLEnsemble(
                state_dim=state_dim,
                action_dim=action_dim,
                **kwargs
            )
            
            logger.info(f"Ensemble DRL inicializado para {symbol} - Estado: {state_dim}, Acciones: {action_dim}")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando ensemble DRL para {symbol}: {e}")
            return False
    
    def train_drl_ensemble(self, symbol, market_data, episodes=1000, max_steps_per_episode=500):
        """
        Entrenar ensemble DRL usando datos de mercado
        
        Args:
            symbol: Símbolo de trading
            market_data: DataFrame con datos de mercado
            episodes: Número de episodios de entrenamiento
            max_steps_per_episode: Máximo de pasos por episodio
        """
        try:
            if symbol not in self.drl_ensembles:
                logger.error(f"Ensemble DRL no inicializado para {symbol}")
                return False
            
            # Crear features para DRL
            features = self.create_all_features(market_data)
            if features.empty:
                logger.error(f"No se pudieron crear features para {symbol}")
                return False
            
            # Preparar datos para entrenamiento
            if symbol in self.feature_selectors and symbol in self.scalers:
                # Usar transformaciones existentes
                features_selected = self.feature_selectors[symbol].transform(features)
                features_scaled = self.scalers[symbol].transform(features_selected)
            else:
                # Usar features sin transformar (normalizar básicamente)
                features_scaled = (features - features.mean()) / (features.std() + 1e-8)
                features_scaled = features_scaled.fillna(0).values
            
            # Inicializar ambiente de trading
            if not hasattr(self, 'trading_environments'):
                self.trading_environments = {}
            
            self.trading_environments[symbol] = TradingEnvironment(
                data=market_data,
                features=features_scaled,
                initial_balance=10000,
                transaction_cost=0.001
            )
            
            ensemble = self.drl_ensembles[symbol]
            env = self.trading_environments[symbol]
            
            # Métricas de entrenamiento
            episode_rewards = []
            episode_lengths = []
            
            logger.info(f"Iniciando entrenamiento DRL para {symbol} - {episodes} episodios")
            
            for episode in range(episodes):
                state = env.reset()
                episode_reward = 0
                episode_length = 0
                
                for step in range(max_steps_per_episode):
                    # Seleccionar acción del ensemble
                    action, log_prob, value = ensemble.select_action(state)
                    
                    # Ejecutar acción en el ambiente
                    next_state, reward, done, info = env.step(action)
                    
                    # Almacenar transición
                    ensemble.store_transition(state, action, reward, next_state, done, log_prob, value)
                    
                    # Actualizar métricas de rendimiento
                    is_win = reward > 0
                    ensemble.update_performance('ppo', reward, is_win)
                    ensemble.update_performance('a2c', reward, is_win)
                    ensemble.update_performance('dqn', reward, is_win)
                    
                    state = next_state
                    episode_reward += reward
                    episode_length += 1
                    
                    if done:
                        break
                
                # Actualizar ensemble al final del episodio
                ensemble.update()
                
                episode_rewards.append(episode_reward)
                episode_lengths.append(episode_length)
                
                # Log progreso cada 100 episodios
                if (episode + 1) % 100 == 0:
                    avg_reward = np.mean(episode_rewards[-100:])
                    avg_length = np.mean(episode_lengths[-100:])
                    logger.info(f"Episodio {episode + 1}/{episodes} - "
                              f"Reward promedio: {avg_reward:.3f}, "
                              f"Longitud promedio: {avg_length:.1f}")
            
            logger.info(f"Entrenamiento DRL completado para {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando ensemble DRL para {symbol}: {e}")
            return False
    
    def predict_drl_ensemble(self, symbol, current_state, deterministic=True):
        """
        Realizar predicción usando ensemble DRL
        
        Args:
            symbol: Símbolo de trading
            current_state: Estado actual del mercado
            deterministic: Si usar predicción determinística
            
        Returns:
            tuple: (acción, confianza, valor_estimado)
        """
        try:
            if symbol not in self.drl_ensembles:
                logger.warning(f"Ensemble DRL no disponible para {symbol}")
                return 0, 0.0, 0.0  # Hold por defecto
            
            # Preparar estado
            if symbol in self.feature_selectors and symbol in self.scalers:
                # Usar transformaciones existentes si están disponibles
                if len(current_state.shape) == 1:
                    current_state = current_state.reshape(1, -1)
                
                state_selected = self.feature_selectors[symbol].transform(current_state)
                state_scaled = self.scalers[symbol].transform(state_selected)
                state_final = state_scaled.flatten()
            else:
                # Normalización básica
                state_final = (current_state - np.mean(current_state)) / (np.std(current_state) + 1e-8)
                if np.any(np.isnan(state_final)):
                    state_final = np.zeros_like(state_final)
            
            # Obtener predicción del ensemble
            ensemble = self.drl_ensembles[symbol]
            action, log_prob, value = ensemble.select_action(state_final, deterministic)
            
            # Calcular confianza basada en el valor estimado
            confidence = min(abs(value) / 10.0, 1.0)  # Normalizar a [0, 1]
            
            return action, confidence, value
            
        except Exception as e:
            logger.error(f"Error en predicción DRL para {symbol}: {e}")
            return 0, 0.0, 0.0  # Hold por defecto
    
    def get_drl_ensemble_metrics(self, symbol):
        """
        Obtener métricas del ensemble DRL
        
        Args:
            symbol: Símbolo de trading
            
        Returns:
            dict: Métricas del ensemble
        """
        try:
            if symbol not in self.drl_ensembles:
                return {}
            
            return self.drl_ensembles[symbol].get_ensemble_metrics()
            
        except Exception as e:
            logger.error(f"Error obteniendo métricas DRL para {symbol}: {e}")
            return {}
    
    def save_drl_ensemble(self, symbol, filepath):
        """
        Guardar ensemble DRL entrenado
        
        Args:
            symbol: Símbolo de trading
            filepath: Ruta base para guardar los modelos
        """
        try:
            if symbol not in self.drl_ensembles:
                logger.error(f"Ensemble DRL no disponible para {symbol}")
                return False
            
            self.drl_ensembles[symbol].save_ensemble(filepath)
            logger.info(f"Ensemble DRL guardado para {symbol} en: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando ensemble DRL para {symbol}: {e}")
            return False
    
    def load_drl_ensemble(self, symbol, filepath, state_dim, action_dim=3):
        """
        Cargar ensemble DRL entrenado
        
        Args:
            symbol: Símbolo de trading
            filepath: Ruta base de los modelos
            state_dim: Dimensión del espacio de estados
            action_dim: Dimensión del espacio de acciones
        """
        try:
            # Inicializar ensemble si no existe
            if not hasattr(self, 'drl_ensembles'):
                self.drl_ensembles = {}
            
            self.drl_ensembles[symbol] = DRLEnsemble(state_dim, action_dim)
            self.drl_ensembles[symbol].load_ensemble(filepath)
            
            logger.info(f"Ensemble DRL cargado para {symbol} desde: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando ensemble DRL para {symbol}: {e}")
            return False
    
    def get_ensemble_action_distribution(self, symbol, current_state):
        """
        Obtener distribución de acciones de cada agente del ensemble
        
        Args:
            symbol: Símbolo de trading
            current_state: Estado actual del mercado
            
        Returns:
            dict: Distribución de acciones por agente
        """
        try:
            if symbol not in self.drl_ensembles:
                return {}
            
            ensemble = self.drl_ensembles[symbol]
            
            # Preparar estado
            if symbol in self.feature_selectors and symbol in self.scalers:
                if len(current_state.shape) == 1:
                    current_state = current_state.reshape(1, -1)
                state_selected = self.feature_selectors[symbol].transform(current_state)
                state_scaled = self.scalers[symbol].transform(state_selected)
                state_final = state_scaled.flatten()
            else:
                state_final = (current_state - np.mean(current_state)) / (np.std(current_state) + 1e-8)
                if np.any(np.isnan(state_final)):
                    state_final = np.zeros_like(state_final)
            
            # Obtener acciones de cada agente
            ppo_action, ppo_log_prob, ppo_value = ensemble.ppo_agent.select_action(state_final, True)
            a2c_action, a2c_log_prob, a2c_value = ensemble.a2c_agent.select_action(state_final, True)
            dqn_action, _, dqn_q_value = ensemble.dqn_agent.select_action(state_final, True)
            
            return {
                'ppo': {'action': ppo_action, 'value': ppo_value, 'weight': ensemble.weights['ppo']},
                'a2c': {'action': a2c_action, 'value': a2c_value, 'weight': ensemble.weights['a2c']},
                'dqn': {'action': dqn_action, 'value': dqn_q_value, 'weight': ensemble.weights['dqn']},
                'ensemble_weights': ensemble.weights.copy()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo distribución de acciones para {symbol}: {e}")
            return {}
    
    def analyze_market_microstructure(self, df, symbol=None):
        """
        Análisis completo de microestructura de mercado
        
        Args:
            df: DataFrame con datos OHLCV
            symbol: Símbolo opcional para logging
            
        Returns:
            dict: Análisis completo de microestructura
        """
        try:
            logger.info(f"Iniciando análisis de microestructura para {symbol or 'datos'}")
            
            # Crear features de microestructura
            micro_features = self.create_market_microstructure_features(df)
            
            # Análisis de liquidez
            liquidity_analysis = self._analyze_liquidity(df, micro_features)
            
            # Análisis de adverse selection
            adverse_selection = self._analyze_adverse_selection(df, micro_features)
            
            # Análisis de market impact
            market_impact = self._analyze_market_impact(df, micro_features)
            
            # Análisis de regímenes de mercado
            regime_analysis = self._analyze_market_regimes(df, micro_features)
            
            # Métricas de trading costs
            trading_costs = self._analyze_trading_costs(df, micro_features)
            
            analysis = {
                'symbol': symbol,
                'timestamp': pd.Timestamp.now(),
                'data_points': len(df),
                'liquidity_analysis': liquidity_analysis,
                'adverse_selection': adverse_selection,
                'market_impact': market_impact,
                'regime_analysis': regime_analysis,
                'trading_costs': trading_costs,
                'microstructure_features': micro_features.describe().to_dict()
            }
            
            logger.info(f"Análisis de microestructura completado para {symbol or 'datos'}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error en análisis de microestructura: {e}")
            return {}
    
    def _analyze_liquidity(self, df, micro_features):
        """Análisis de liquidez del mercado"""
        try:
            # Métricas de liquidez
            avg_spread = micro_features['hl_spread'].mean()
            spread_volatility = micro_features['hl_spread'].std()
            
            # Amihud illiquidity
            avg_illiquidity = micro_features['amihud_illiq_sma'].mean()
            
            # VPIN
            avg_vpin_20 = micro_features['vpin_20'].mean()
            avg_vpin_50 = micro_features['vpin_50'].mean()
            
            # Clasificación de liquidez
            if avg_spread < 0.001 and avg_illiquidity < 1e-6:
                liquidity_level = 'High'
            elif avg_spread < 0.005 and avg_illiquidity < 1e-5:
                liquidity_level = 'Medium'
            else:
                liquidity_level = 'Low'
            
            return {
                'average_spread': avg_spread,
                'spread_volatility': spread_volatility,
                'amihud_illiquidity': avg_illiquidity,
                'vpin_20': avg_vpin_20,
                'vpin_50': avg_vpin_50,
                'liquidity_level': liquidity_level,
                'roll_spread': micro_features['roll_spread'].mean()
            }
            
        except Exception as e:
            logger.error(f"Error analizando liquidez: {e}")
            return {}
    
    def _analyze_adverse_selection(self, df, micro_features):
        """Análisis de adverse selection"""
        try:
            # Kyle's Lambda
            avg_kyle_lambda_20 = micro_features['kyle_lambda_20'].mean()
            avg_kyle_lambda_50 = micro_features['kyle_lambda_50'].mean()
            
            # PIN approximation
            avg_pin = micro_features['pin_sma'].mean()
            
            # Trade classification accuracy
            trade_class_balance = micro_features['trade_classification'].value_counts(normalize=True)
            
            # Adverse selection risk
            if avg_pin > 0.3 or abs(avg_kyle_lambda_20) > 1e-5:
                adverse_selection_risk = 'High'
            elif avg_pin > 0.2 or abs(avg_kyle_lambda_20) > 1e-6:
                adverse_selection_risk = 'Medium'
            else:
                adverse_selection_risk = 'Low'
            
            return {
                'kyle_lambda_20': avg_kyle_lambda_20,
                'kyle_lambda_50': avg_kyle_lambda_50,
                'pin_approximation': avg_pin,
                'trade_classification_balance': trade_class_balance.to_dict(),
                'adverse_selection_risk': adverse_selection_risk
            }
            
        except Exception as e:
            logger.error(f"Error analizando adverse selection: {e}")
            return {}
    
    def _analyze_market_impact(self, df, micro_features):
        """Análisis de market impact"""
        try:
            # Price impact por diferentes períodos
            impact_5 = micro_features['price_impact_5'].mean()
            impact_10 = micro_features['price_impact_10'].mean()
            impact_20 = micro_features['price_impact_20'].mean()
            
            # Temporary vs Permanent impact
            temp_impact_avg = (micro_features['temp_impact_5'].mean() + 
                             micro_features['temp_impact_10'].mean() + 
                             micro_features['temp_impact_20'].mean()) / 3
            
            perm_impact_avg = (micro_features['perm_impact_5'].mean() + 
                             micro_features['perm_impact_10'].mean() + 
                             micro_features['perm_impact_20'].mean()) / 3
            
            # Ratio temporal/permanente
            if abs(perm_impact_avg) > 1e-8:
                temp_perm_ratio = abs(temp_impact_avg) / abs(perm_impact_avg)
            else:
                temp_perm_ratio = float('inf')
            
            return {
                'price_impact_5min': impact_5,
                'price_impact_10min': impact_10,
                'price_impact_20min': impact_20,
                'temporary_impact': temp_impact_avg,
                'permanent_impact': perm_impact_avg,
                'temp_perm_ratio': temp_perm_ratio,
                'impact_decay': impact_5 - impact_20  # Decaimiento del impacto
            }
            
        except Exception as e:
            logger.error(f"Error analizando market impact: {e}")
            return {}
    
    def _analyze_market_regimes(self, df, micro_features):
        """Análisis de regímenes de mercado"""
        try:
            # Distribución de regímenes de volatilidad
            vol_regime_dist = micro_features['vol_regime'].value_counts(normalize=True)
            
            # Distribución de regímenes de volumen
            volume_regime_dist = micro_features['volume_regime'].value_counts(normalize=True)
            
            # Régimen actual (último valor)
            current_vol_regime = micro_features['vol_regime'].iloc[-1]
            current_volume_regime = micro_features['volume_regime'].iloc[-1]
            
            # Estabilidad de regímenes (cambios frecuentes indican inestabilidad)
            vol_regime_changes = (micro_features['vol_regime'].diff() != 0).sum()
            volume_regime_changes = (micro_features['volume_regime'].diff() != 0).sum()
            
            regime_stability = 1 - (vol_regime_changes + volume_regime_changes) / (2 * len(micro_features))
            
            return {
                'volatility_regime_distribution': vol_regime_dist.to_dict(),
                'volume_regime_distribution': volume_regime_dist.to_dict(),
                'current_volatility_regime': int(current_vol_regime),
                'current_volume_regime': int(current_volume_regime),
                'regime_stability': regime_stability,
                'volatility_regime_changes': vol_regime_changes,
                'volume_regime_changes': volume_regime_changes
            }
            
        except Exception as e:
            logger.error(f"Error analizando regímenes de mercado: {e}")
            return {}
    
    def _analyze_trading_costs(self, df, micro_features):
        """Análisis de costos de trading"""
        try:
            # Spread costs
            avg_effective_spread = (micro_features['effective_spread_5'].mean() + 
                                  micro_features['effective_spread_10'].mean() + 
                                  micro_features['effective_spread_20'].mean()) / 3
            
            # Market impact costs
            avg_market_impact = (micro_features['price_impact_5'].mean() + 
                               micro_features['price_impact_10'].mean() + 
                               micro_features['price_impact_20'].mean()) / 3
            
            # Timing costs (variance ratio)
            avg_variance_ratio = (micro_features['variance_ratio_2'].mean() + 
                                micro_features['variance_ratio_5'].mean() + 
                                micro_features['variance_ratio_10'].mean()) / 3
            
            # Total estimated trading cost
            total_cost_estimate = abs(avg_effective_spread) + abs(avg_market_impact)
            
            # Cost efficiency for market making
            mm_profit_expectation = micro_features['mm_profit_expectation'].mean()
            
            return {
                'average_effective_spread': avg_effective_spread,
                'average_market_impact': avg_market_impact,
                'average_variance_ratio': avg_variance_ratio,
                'total_cost_estimate': total_cost_estimate,
                'market_making_profit_expectation': mm_profit_expectation,
                'cost_efficiency_ratio': mm_profit_expectation / (total_cost_estimate + 1e-8)
            }
            
        except Exception as e:
            logger.error(f"Error analizando costos de trading: {e}")
            return {}
    
    def get_optimal_execution_strategy(self, df, target_volume, time_horizon_minutes=60):
        """
        Recomendar estrategia óptima de ejecución basada en microestructura
        
        Args:
            df: DataFrame con datos de mercado
            target_volume: Volumen objetivo a ejecutar
            time_horizon_minutes: Horizonte temporal en minutos
            
        Returns:
            dict: Estrategia de ejecución recomendada
        """
        try:
            # Análisis de microestructura
            micro_analysis = self.analyze_market_microstructure(df)
            
            # Obtener métricas clave
            liquidity_level = micro_analysis.get('liquidity_analysis', {}).get('liquidity_level', 'Medium')
            adverse_selection_risk = micro_analysis.get('adverse_selection', {}).get('adverse_selection_risk', 'Medium')
            current_vol_regime = micro_analysis.get('regime_analysis', {}).get('current_volatility_regime', 1)
            
            # Volumen promedio del mercado
            avg_volume = df['volume'].mean()
            volume_ratio = target_volume / avg_volume
            
            # Determinar estrategia
            if liquidity_level == 'High' and adverse_selection_risk == 'Low':
                if volume_ratio < 0.1:
                    strategy = 'AGGRESSIVE'  # Market orders
                    execution_rate = 0.8  # 80% del volumen objetivo por período
                else:
                    strategy = 'TWAP'  # Time-weighted average price
                    execution_rate = 0.2
            elif liquidity_level == 'Medium':
                if volume_ratio < 0.05:
                    strategy = 'MODERATE'  # Mix de market y limit orders
                    execution_rate = 0.5
                else:
                    strategy = 'VWAP'  # Volume-weighted average price
                    execution_rate = 0.15
            else:  # Low liquidity
                strategy = 'CONSERVATIVE'  # Principalmente limit orders
                execution_rate = 0.1
            
            # Ajustar por régimen de volatilidad
            if current_vol_regime == 2:  # Alta volatilidad
                execution_rate *= 0.7  # Ser más conservador
            elif current_vol_regime == 0:  # Baja volatilidad
                execution_rate *= 1.3  # Ser más agresivo
            
            # Calcular número de órdenes
            num_periods = max(1, int(time_horizon_minutes / 5))  # Períodos de 5 minutos
            volume_per_period = target_volume * execution_rate / num_periods
            
            return {
                'strategy': strategy,
                'execution_rate': execution_rate,
                'volume_per_period': volume_per_period,
                'num_periods': num_periods,
                'time_horizon_minutes': time_horizon_minutes,
                'liquidity_assessment': liquidity_level,
                'adverse_selection_risk': adverse_selection_risk,
                'volatility_regime': current_vol_regime,
                'recommendations': self._get_execution_recommendations(strategy, liquidity_level)
            }
            
        except Exception as e:
            logger.error(f"Error determinando estrategia de ejecución: {e}")
            return {'strategy': 'CONSERVATIVE', 'execution_rate': 0.1}
    
    def _get_execution_recommendations(self, strategy, liquidity_level):
        """Obtener recomendaciones específicas para la estrategia de ejecución"""
        recommendations = {
            'AGGRESSIVE': [
                "Usar órdenes de mercado para ejecución rápida",
                "Monitorear spread bid-ask continuamente",
                "Considerar fragmentar órdenes grandes"
            ],
            'MODERATE': [
                "Combinar órdenes de mercado y limit",
                "Usar órdenes iceberg para volúmenes grandes",
                "Ajustar precios límite dinámicamente"
            ],
            'TWAP': [
                "Distribuir ejecución uniformemente en el tiempo",
                "Usar órdenes limit cerca del mid-price",
                "Monitorear cambios en volatilidad"
            ],
            'VWAP': [
                "Seguir patrones históricos de volumen",
                "Aumentar participación en períodos de alto volumen",
                "Usar algoritmos adaptativos"
            ],
            'CONSERVATIVE': [
                "Usar principalmente órdenes limit",
                "Ser paciente con la ejecución",
                "Evitar períodos de alta volatilidad"
            ]
        }
        
        base_recommendations = recommendations.get(strategy, [])
        
        # Agregar recomendaciones específicas por liquidez
        if liquidity_level == 'Low':
            base_recommendations.append("Considerar ejecutar en múltiples venues")
            base_recommendations.append("Usar órdenes más pequeñas")
        elif liquidity_level == 'High':
            base_recommendations.append("Aprovechar la alta liquidez para ejecución rápida")
        
        return base_recommendations

def main():
    """Función de prueba"""
    try:
        # Crear datos de prueba
        dates = pd.date_range(start='2024-01-01', periods=500, freq='1H')
        np.random.seed(42)
        
        test_data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.cumsum(np.random.randn(500) * 0.5),
            'high': 100 + np.cumsum(np.random.randn(500) * 0.5) + np.random.rand(500) * 2,
            'low': 100 + np.cumsum(np.random.randn(500) * 0.5) - np.random.rand(500) * 2,
            'close': 100 + np.cumsum(np.random.randn(500) * 0.5),
            'volume': np.random.rand(500) * 1000000
        })
        
        # Crear motor ML
        ml_engine = AdvancedMLEngine()
        
        # Crear features
        features = ml_engine.create_all_features(test_data)
        targets = ml_engine.create_targets(test_data)
        
        print(f"Features creadas: {features.shape}")
        print(f"Targets creados: {targets.shape}")
        
        # Entrenar modelo
        if len(features) > 200:
            success = ml_engine.train_model('TEST', features, targets['target_main'])
            print(f"Entrenamiento exitoso: {success}")
            
            if success:
                # Hacer predicciones
                predictions, confidences = ml_engine.predict('TEST', features)
                print(f"Predicciones: {len(predictions)}")
                print(f"Confianza promedio: {np.mean(confidences):.3f}")
        
        print("Prueba de motor ML completada exitosamente")
        
    except Exception as e:
        print(f"Error en prueba: {e}")

if __name__ == "__main__":
    main()