#!/usr/bin/env python3
"""
Adaptador DRL para Paper Trading SICAR
Integra el sistema DRL avanzado de FASE 2 con el motor de paper trading.
"""

import logging
import numpy as np
import pandas as pd
import torch
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import json

# Importar componentes SICAR
from advanced_drl_system import AdvancedDRLAgent, DRLConfig
from paper_trading_system import PaperTradingEngine, OrderType, PositionSide
from binance_data_provider import BinanceDataProvider
from advanced_technical_analyzer import AdvancedTechnicalAnalyzer

logger = logging.getLogger(__name__)

@dataclass
class DRLTradingConfig:
    """Configuración para el trading DRL."""
    # Configuración del agente DRL
    state_dim: int = 20
    action_dim: int = 3  # 0: Hold, 1: Buy, 2: Sell
    learning_rate: float = 0.0003
    hidden_dim: int = 256
    
    # Configuración de trading
    max_position_size: float = 0.1  # 10% del capital por posición
    min_confidence_threshold: float = 0.6
    risk_per_trade: float = 0.02  # 2% de riesgo por trade
    
    # Configuración de datos
    lookback_periods: int = 50
    update_frequency: int = 10  # Actualizar agente cada N trades
    
    # Configuración de recompensas
    profit_reward_multiplier: float = 10.0
    risk_penalty_multiplier: float = 5.0
    holding_penalty: float = 0.001

class DRLPaperTradingAdapter:
    """
    Adaptador que integra el agente DRL avanzado con el sistema de paper trading.
    
    Características:
    - Procesamiento de datos de mercado en tiempo real
    - Generación de señales de trading usando DRL
    - Gestión automática de posiciones
    - Aprendizaje continuo del agente
    - Monitoreo de performance
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 symbols: List[str] = None,
                 config: DRLTradingConfig = None):
        """
        Inicializa el adaptador DRL para paper trading.
        
        Args:
            initial_capital: Capital inicial para paper trading
            symbols: Lista de símbolos a tradear
            config: Configuración del sistema DRL
        """
        self.config = config or DRLTradingConfig()
        self.symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        # Inicializar componentes
        self.paper_engine = PaperTradingEngine(
            initial_capital=initial_capital,
            commission_rate=0.001
        )
        
        self.data_provider = BinanceDataProvider()
        self.technical_analyzer = AdvancedTechnicalAnalyzer()
        
        # Configurar agente DRL
        drl_config = DRLConfig(
            learning_rate=self.config.learning_rate,
            hidden_dim=self.config.hidden_dim,
            dropout_rate=0.1,
            gamma=0.99,
            eps_clip=0.2,
            k_epochs=4,
            batch_size=64
        )
        
        self.drl_agent = AdvancedDRLAgent(
            state_dim=self.config.state_dim,
            action_dim=self.config.action_dim,
            config=drl_config.__dict__
        )
        
        # Estado del sistema
        self.market_data_history = {symbol: [] for symbol in self.symbols}
        self.last_actions = {symbol: 0 for symbol in self.symbols}  # 0: Hold
        self.trade_count = 0
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'drl_confidence_avg': 0.0
        }
        
        # Buffer de experiencias para entrenamiento
        self.experience_buffer = []
        self.max_buffer_size = 1000
        
        logger.info(f"🤖 DRL Paper Trading Adapter inicializado")
        logger.info(f"   💰 Capital inicial: ${initial_capital:,.2f}")
        logger.info(f"   📊 Símbolos: {', '.join(self.symbols)}")
        logger.info(f"   🧠 Estado DRL: {self.config.state_dim}D")
    
    def extract_market_features(self, symbol: str, timeframe: str = '1h') -> Optional[np.ndarray]:
        """
        Extrae características del mercado para el agente DRL.
        
        Args:
            symbol: Símbolo del activo
            timeframe: Timeframe de los datos
            
        Returns:
            Array de características normalizadas
        """
        try:
            # Obtener datos históricos
            df = self.data_provider.get_historical_data(
                symbol=symbol,
                interval=timeframe,
                limit=self.config.lookback_periods + 20
            )
            
            if df is None or len(df) < self.config.lookback_periods:
                logger.warning(f"Datos insuficientes para {symbol}")
                return None
            
            # Calcular indicadores técnicos
            indicators = self.technical_analyzer.calculate_all_indicators(df)
            
            # Extraer características relevantes
            features = []
            
            # 1. Precios normalizados (4 features)
            close_prices = df['close'].values[-self.config.lookback_periods:]
            price_returns = np.diff(np.log(close_prices))
            features.extend([
                np.mean(price_returns),  # Retorno promedio
                np.std(price_returns),   # Volatilidad
                (close_prices[-1] - close_prices[0]) / close_prices[0],  # Retorno total
                close_prices[-1] / np.mean(close_prices)  # Precio relativo
            ])
            
            # 2. Indicadores técnicos (8 features)
            if 'rsi' in indicators:
                features.append(indicators['rsi'].iloc[-1] / 100.0)  # RSI normalizado
            else:
                features.append(0.5)
                
            if 'macd' in indicators:
                features.append(np.tanh(indicators['macd'].iloc[-1]))  # MACD normalizado
            else:
                features.append(0.0)
                
            if 'bb_upper' in indicators and 'bb_lower' in indicators:
                bb_position = (close_prices[-1] - indicators['bb_lower'].iloc[-1]) / \
                             (indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1])
                features.append(bb_position)  # Posición en Bollinger Bands
            else:
                features.append(0.5)
                
            # Agregar más indicadores técnicos
            for indicator in ['sma_20', 'ema_12', 'stoch_k', 'williams_r', 'atr']:
                if indicator in indicators:
                    if indicator in ['sma_20', 'ema_12']:
                        features.append(close_prices[-1] / indicators[indicator].iloc[-1] - 1.0)
                    elif indicator in ['stoch_k']:
                        features.append(indicators[indicator].iloc[-1] / 100.0)
                    elif indicator in ['williams_r']:
                        features.append((indicators[indicator].iloc[-1] + 100) / 100.0)
                    else:
                        features.append(np.tanh(indicators[indicator].iloc[-1] / close_prices[-1]))
                else:
                    features.append(0.0)
            
            # 3. Información de volumen (2 features)
            volumes = df['volume'].values[-self.config.lookback_periods:]
            features.extend([
                volumes[-1] / np.mean(volumes),  # Volumen relativo
                np.std(volumes) / np.mean(volumes)  # Volatilidad del volumen
            ])
            
            # 4. Información de posición actual (3 features)
            current_position = self.paper_engine.positions.get(symbol)
            if current_position:
                features.extend([
                    1.0 if current_position.side == PositionSide.LONG else -1.0,  # Dirección
                    current_position.pnl_percentage / 100.0,  # PnL normalizado
                    min(current_position.size * current_position.current_price / 
                        self.paper_engine.current_capital, 1.0)  # Tamaño relativo
                ])
            else:
                features.extend([0.0, 0.0, 0.0])
            
            # 5. Información de mercado general (3 features)
            portfolio_summary = self.paper_engine.get_portfolio_summary()
            features.extend([
                portfolio_summary['total_pnl'] / self.paper_engine.initial_capital,  # PnL total
                len(self.paper_engine.positions) / len(self.symbols),  # Exposición
                self.last_actions[symbol] / 2.0 - 0.5  # Última acción normalizada
            ])
            
            # Asegurar que tenemos exactamente state_dim features
            features = features[:self.config.state_dim]
            while len(features) < self.config.state_dim:
                features.append(0.0)
            
            # Normalizar y clipear
            features = np.array(features, dtype=np.float32)
            features = np.clip(features, -5.0, 5.0)  # Clipear valores extremos
            
            return features
            
        except Exception as e:
            logger.error(f"Error extrayendo características para {symbol}: {e}")
            return None
    
    def get_drl_trading_signal(self, symbol: str) -> Tuple[int, float, float]:
        """
        Obtiene señal de trading del agente DRL.
        
        Args:
            symbol: Símbolo del activo
            
        Returns:
            Tupla (acción, log_prob, value)
            acción: 0=Hold, 1=Buy, 2=Sell
        """
        try:
            # Extraer características del mercado
            state = self.extract_market_features(symbol)
            if state is None:
                return 0, 0.0, 0.0  # Hold por defecto
            
            # Obtener acción del agente DRL
            action, log_prob, value = self.drl_agent.select_action(state)
            
            # Convertir a probabilidades para análisis de confianza
            action_probs = torch.softmax(torch.tensor([log_prob, value, -log_prob]), dim=0)
            confidence = float(action_probs[action])
            
            logger.debug(f"DRL Signal {symbol}: Action={action}, Confidence={confidence:.3f}")
            
            return action, confidence, float(value)
            
        except Exception as e:
            logger.error(f"Error obteniendo señal DRL para {symbol}: {e}")
            return 0, 0.0, 0.0
    
    def execute_drl_trading(self, symbol: str, current_price: float) -> Optional[str]:
        """
        Ejecuta trading basado en señales DRL.
        
        Args:
            symbol: Símbolo del activo
            current_price: Precio actual
            
        Returns:
            ID de la orden ejecutada o None
        """
        try:
            # Obtener señal DRL
            action, confidence, value = self.get_drl_trading_signal(symbol)
            
            # Verificar umbral de confianza
            if confidence < self.config.min_confidence_threshold:
                logger.debug(f"Confianza insuficiente para {symbol}: {confidence:.3f}")
                return None
            
            # Obtener posición actual
            current_position = self.paper_engine.positions.get(symbol)
            portfolio_summary = self.paper_engine.get_portfolio_summary()
            
            order_id = None
            
            if action == 1:  # BUY
                if current_position and current_position.side == PositionSide.LONG:
                    logger.debug(f"Ya tenemos posición LONG en {symbol}")
                    return None
                
                # Calcular tamaño de posición
                available_capital = portfolio_summary['available_capital']
                position_value = available_capital * self.config.max_position_size
                quantity = position_value / current_price
                
                if position_value > 100:  # Mínimo $100 por trade
                    # Cerrar posición SHORT si existe
                    if current_position and current_position.side == PositionSide.SHORT:
                        self.paper_engine.place_order(
                            symbol=symbol,
                            side='buy',
                            order_type=OrderType.MARKET,
                            quantity=current_position.size,
                            price=current_price
                        )
                    
                    # Abrir posición LONG
                    order_id = self.paper_engine.place_order(
                        symbol=symbol,
                        side='buy',
                        order_type=OrderType.MARKET,
                        quantity=quantity,
                        price=current_price
                    )
                    
                    logger.info(f"🟢 DRL BUY: {symbol} - Cantidad: {quantity:.6f} - Precio: ${current_price:.4f} - Confianza: {confidence:.3f}")
            
            elif action == 2:  # SELL
                if current_position and current_position.side == PositionSide.SHORT:
                    logger.debug(f"Ya tenemos posición SHORT en {symbol}")
                    return None
                
                # Cerrar posición LONG si existe
                if current_position and current_position.side == PositionSide.LONG:
                    order_id = self.paper_engine.place_order(
                        symbol=symbol,
                        side='sell',
                        order_type=OrderType.MARKET,
                        quantity=current_position.size,
                        price=current_price
                    )
                    
                    logger.info(f"🔴 DRL SELL: {symbol} - Cantidad: {current_position.size:.6f} - Precio: ${current_price:.4f} - Confianza: {confidence:.3f}")
                
                # Para paper trading, no implementamos short selling por simplicidad
                # En un sistema real, aquí abriríamos una posición SHORT
            
            # Actualizar última acción
            self.last_actions[symbol] = action
            
            # Almacenar experiencia para entrenamiento
            if len(self.market_data_history[symbol]) > 0:
                prev_state = self.market_data_history[symbol][-1]['state']
                reward = self.calculate_reward(symbol, action, current_price)
                
                self.experience_buffer.append({
                    'state': prev_state,
                    'action': action,
                    'reward': reward,
                    'next_state': self.extract_market_features(symbol),
                    'done': False
                })
                
                # Limitar tamaño del buffer
                if len(self.experience_buffer) > self.max_buffer_size:
                    self.experience_buffer.pop(0)
            
            # Almacenar datos para historial
            self.market_data_history[symbol].append({
                'timestamp': datetime.now(),
                'price': current_price,
                'action': action,
                'confidence': confidence,
                'value': value,
                'state': self.extract_market_features(symbol)
            })
            
            return order_id
            
        except Exception as e:
            logger.error(f"Error ejecutando trading DRL para {symbol}: {e}")
            return None
    
    def calculate_reward(self, symbol: str, action: int, current_price: float) -> float:
        """
        Calcula la recompensa para el agente DRL.
        
        Args:
            symbol: Símbolo del activo
            action: Acción tomada
            current_price: Precio actual
            
        Returns:
            Recompensa calculada
        """
        try:
            reward = 0.0
            
            # Obtener posición actual
            position = self.paper_engine.positions.get(symbol)
            
            if position:
                # Recompensa basada en PnL
                pnl_pct = position.pnl_percentage / 100.0
                reward += pnl_pct * self.config.profit_reward_multiplier
                
                # Penalización por riesgo excesivo
                if abs(pnl_pct) > self.config.risk_per_trade:
                    reward -= abs(pnl_pct) * self.config.risk_penalty_multiplier
            
            # Penalización por holding (fomentar actividad)
            if action == 0:  # Hold
                reward -= self.config.holding_penalty
            
            # Recompensa por diversificación
            num_positions = len(self.paper_engine.positions)
            if num_positions > 1:
                reward += 0.01 * num_positions
            
            return float(reward)
            
        except Exception as e:
            logger.error(f"Error calculando recompensa para {symbol}: {e}")
            return 0.0
    
    def train_drl_agent(self):
        """Entrena el agente DRL con las experiencias acumuladas."""
        try:
            if len(self.experience_buffer) < 32:  # Mínimo para entrenamiento
                return
            
            # Preparar datos de entrenamiento
            states = []
            actions = []
            rewards = []
            next_states = []
            dones = []
            
            for exp in self.experience_buffer[-32:]:  # Usar últimas 32 experiencias
                if exp['state'] is not None and exp['next_state'] is not None:
                    states.append(exp['state'])
                    actions.append(exp['action'])
                    rewards.append(exp['reward'])
                    next_states.append(exp['next_state'])
                    dones.append(exp['done'])
            
            if len(states) < 8:
                return
            
            # Convertir a tensores
            states = torch.FloatTensor(np.array(states))
            actions = torch.LongTensor(actions)
            rewards = torch.FloatTensor(rewards)
            next_states = torch.FloatTensor(np.array(next_states))
            dones = torch.BoolTensor(dones)
            
            # Entrenar agente (implementación simplificada)
            # En un sistema completo, aquí iría el algoritmo PPO completo
            logger.info(f"🧠 Entrenando agente DRL con {len(states)} experiencias")
            
            # Actualizar contador de entrenamiento
            self.trade_count += 1
            
        except Exception as e:
            logger.error(f"Error entrenando agente DRL: {e}")
    
    def update_performance_metrics(self):
        """Actualiza las métricas de performance del sistema."""
        try:
            portfolio_summary = self.paper_engine.get_portfolio_summary()
            
            self.performance_metrics.update({
                'total_trades': self.paper_engine.total_trades,
                'winning_trades': self.paper_engine.winning_trades,
                'total_pnl': portfolio_summary['total_pnl'],
                'win_rate': (self.paper_engine.winning_trades / max(self.paper_engine.total_trades, 1)) * 100,
                'current_capital': portfolio_summary['current_capital'],
                'portfolio_value': portfolio_summary['total_portfolio_value']
            })
            
            # Calcular Sharpe ratio simplificado
            if len(self.paper_engine.trade_history) > 1:
                returns = [trade['value'] for trade in self.paper_engine.trade_history[-20:]]
                if len(returns) > 1:
                    mean_return = np.mean(returns)
                    std_return = np.std(returns)
                    self.performance_metrics['sharpe_ratio'] = mean_return / max(std_return, 0.001)
            
            # Calcular confianza promedio del DRL
            confidences = []
            for symbol_history in self.market_data_history.values():
                confidences.extend([data['confidence'] for data in symbol_history[-10:]])
            
            if confidences:
                self.performance_metrics['drl_confidence_avg'] = np.mean(confidences)
            
        except Exception as e:
            logger.error(f"Error actualizando métricas: {e}")
    
    def process_market_update(self, market_data: Dict[str, float]):
        """
        Procesa actualización de datos de mercado y ejecuta trading DRL.
        
        Args:
            market_data: Diccionario con precios actuales {symbol: price}
        """
        try:
            # Actualizar paper trading engine
            self.paper_engine.process_market_data(market_data)
            
            # Procesar cada símbolo
            for symbol, price in market_data.items():
                if symbol in self.symbols:
                    # Ejecutar trading DRL
                    order_id = self.execute_drl_trading(symbol, price)
                    
                    if order_id:
                        logger.info(f"📊 Orden DRL ejecutada: {order_id} para {symbol}")
            
            # Entrenar agente periódicamente
            if self.trade_count % self.config.update_frequency == 0:
                self.train_drl_agent()
            
            # Actualizar métricas
            self.update_performance_metrics()
            
        except Exception as e:
            logger.error(f"Error procesando actualización de mercado: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del sistema DRL."""
        try:
            portfolio_summary = self.paper_engine.get_portfolio_summary()
            
            status = {
                'timestamp': datetime.now().isoformat(),
                'portfolio': portfolio_summary,
                'performance': self.performance_metrics,
                'positions': {
                    symbol: {
                        'side': pos.side.value,
                        'size': pos.size,
                        'entry_price': pos.entry_price,
                        'current_price': pos.current_price,
                        'pnl_pct': pos.pnl_percentage,
                        'unrealized_pnl': pos.unrealized_pnl
                    }
                    for symbol, pos in self.paper_engine.positions.items()
                },
                'drl_agent': {
                    'experience_buffer_size': len(self.experience_buffer),
                    'training_count': self.trade_count,
                    'last_actions': self.last_actions
                }
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error obteniendo estado del sistema: {e}")
            return {}
    
    def save_state(self, filepath: str):
        """Guarda el estado del sistema DRL."""
        try:
            state = {
                'config': self.config.__dict__,
                'performance_metrics': self.performance_metrics,
                'trade_count': self.trade_count,
                'last_actions': self.last_actions,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"💾 Estado DRL guardado en: {filepath}")
            
        except Exception as e:
            logger.error(f"Error guardando estado: {e}")

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Crear adaptador DRL
    adapter = DRLPaperTradingAdapter(
        initial_capital=10000.0,
        symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    )
    
    print("🤖 DRL Paper Trading Adapter creado exitosamente!")
    print(f"📊 Estado inicial: {adapter.get_system_status()}")