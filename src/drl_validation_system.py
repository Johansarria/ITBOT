#!/usr/bin/env python3
"""
SICAR - Sistema de Validación DRL
FASE 2: Validación robusta con Walk-Forward Analysis y CPCV

Este módulo implementa un sistema completo de validación para agentes DRL que incluye:
- Walk-Forward Analysis para validación temporal
- CPCV (Combinatorial Purged Cross-Validation) adaptado para DRL
- Métricas de rendimiento específicas para trading
- Análisis de estabilidad y robustez
"""

import numpy as np
import pandas as pd
import torch
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')

# Importar módulos SICAR
try:
    from advanced_drl_system import AdvancedDRLAgent
    from advanced_backtester import AdvancedBacktester, CPCVConfig, CPCVResult
    from module_2_regime import ExtremeNonStationarityDetector
except ImportError as e:
    print(f"Warning: No se pudieron importar algunos módulos SICAR: {e}")

logger = logging.getLogger(__name__)

@dataclass
class DRLValidationConfig:
    """Configuración para validación DRL"""
    # Walk-Forward Analysis
    training_window: int = 1000  # Ventana de entrenamiento
    validation_window: int = 200  # Ventana de validación
    step_size: int = 100  # Tamaño del paso
    min_training_episodes: int = 50  # Mínimo episodios de entrenamiento
    
    # CPCV para DRL
    n_splits: int = 5  # Número de splits
    purge_pct: float = 0.05  # Porcentaje de purging
    embargo_pct: float = 0.02  # Porcentaje de embargo
    
    # Métricas de evaluación
    evaluation_episodes: int = 20  # Episodios para evaluación
    confidence_level: float = 0.95  # Nivel de confianza
    
    # Criterios de estabilidad
    max_performance_variance: float = 0.3  # Máxima varianza de rendimiento
    min_sharpe_ratio: float = 0.5  # Mínimo Sharpe ratio
    max_drawdown_threshold: float = 0.15  # Máximo drawdown permitido

@dataclass
class DRLValidationResult:
    """Resultado de validación DRL"""
    # Métricas generales
    avg_return: float
    std_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    
    # Métricas de estabilidad
    performance_variance: float
    consistency_score: float
    robustness_score: float
    
    # Resultados por fold
    fold_results: List[Dict]
    
    # Walk-forward results
    wf_results: List[Dict]
    
    # Métricas temporales
    temporal_stability: float
    regime_adaptability: float
    
    # Estado de validación
    is_stable: bool
    is_robust: bool
    validation_passed: bool


class DRLTradingEnvironment:
    """
    Entorno de trading simplificado para validación DRL
    """
    
    def __init__(self, data: pd.DataFrame, initial_capital: float = 10000):
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.reset()
    
    def reset(self):
        """Reiniciar entorno"""
        self.current_step = 0
        self.capital = self.initial_capital
        self.position = 0  # 0: HOLD, 1: LONG, -1: SHORT
        self.entry_price = 0
        self.trades = []
        self.equity_curve = [self.capital]
        return self._get_state()
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        Ejecutar acción en el entorno
        
        Args:
            action: 0=HOLD, 1=BUY, 2=SELL
            
        Returns:
            next_state, reward, done, info
        """
        if self.current_step >= len(self.data) - 1:
            return self._get_state(), 0, True, {}
        
        current_price = self.data.iloc[self.current_step]['close']
        next_price = self.data.iloc[self.current_step + 1]['close']
        
        reward = 0
        trade_info = {}
        
        # Ejecutar acción
        if action == 1 and self.position == 0:  # BUY
            self.position = 1
            self.entry_price = next_price
        elif action == 2 and self.position == 0:  # SELL
            self.position = -1
            self.entry_price = next_price
        elif action == 0 and self.position != 0:  # CLOSE POSITION
            if self.position == 1:  # Close long
                pnl = (next_price - self.entry_price) / self.entry_price
            else:  # Close short
                pnl = (self.entry_price - next_price) / self.entry_price
            
            self.capital *= (1 + pnl)
            reward = pnl
            
            trade_info = {
                'pnl': pnl,
                'position_size': 1.0,
                'duration_hours': 1.0,
                'volatility': self._calculate_volatility()
            }
            
            self.trades.append(trade_info)
            self.position = 0
        
        self.equity_curve.append(self.capital)
        self.current_step += 1
        
        next_state = self._get_state()
        done = self.current_step >= len(self.data) - 1
        
        return next_state, reward, done, trade_info
    
    def _get_state(self) -> np.ndarray:
        """Obtener estado actual del entorno"""
        if self.current_step >= len(self.data):
            return np.zeros(10)
        
        # Estado simplificado con indicadores básicos
        row = self.data.iloc[self.current_step]
        
        # Precios normalizados
        close = row['close']
        high = row['high']
        low = row['low']
        volume = row['volume']
        
        # Indicadores técnicos básicos
        if self.current_step >= 20:
            sma_20 = self.data['close'].iloc[self.current_step-19:self.current_step+1].mean()
            volatility = self.data['close'].iloc[self.current_step-19:self.current_step+1].std()
        else:
            sma_20 = close
            volatility = 0.01
        
        state = np.array([
            close / sma_20 - 1,  # Precio relativo a SMA
            (high - low) / close,  # Rango diario
            volatility / close,  # Volatilidad normalizada
            volume / 1000000,  # Volumen normalizado
            self.position,  # Posición actual
            (self.capital - self.initial_capital) / self.initial_capital,  # P&L acumulado
            len(self.trades),  # Número de trades
            self.current_step / len(self.data),  # Progreso temporal
            np.sin(2 * np.pi * self.current_step / 24),  # Componente cíclico
            np.cos(2 * np.pi * self.current_step / 24)   # Componente cíclico
        ])
        
        return state.astype(np.float32)
    
    def _calculate_volatility(self) -> float:
        """Calcular volatilidad reciente"""
        if self.current_step < 10:
            return 0.02
        
        recent_prices = self.data['close'].iloc[self.current_step-9:self.current_step+1]
        returns = recent_prices.pct_change().dropna()
        return float(returns.std()) if len(returns) > 0 else 0.02
    
    def get_performance_metrics(self) -> Dict:
        """Calcular métricas de rendimiento"""
        if len(self.trades) == 0:
            return {
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'num_trades': 0
            }
        
        # Retorno total
        total_return = (self.capital - self.initial_capital) / self.initial_capital
        
        # Sharpe ratio
        returns = [trade['pnl'] for trade in self.trades]
        if len(returns) > 1:
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Drawdown
        equity_array = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity_array)
        drawdown = (peak - equity_array) / peak
        max_drawdown = np.max(drawdown)
        
        # Win rate
        winning_trades = sum(1 for trade in self.trades if trade['pnl'] > 0)
        win_rate = winning_trades / len(self.trades)
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'num_trades': len(self.trades)
        }


class DRLValidator:
    """
    Sistema de validación completo para agentes DRL
    """
    
    def __init__(self, config: DRLValidationConfig = None):
        self.config = config or DRLValidationConfig()
        self.validation_results = []
        
        logger.info("Sistema de validación DRL inicializado")
    
    def validate_agent(self, agent: AdvancedDRLAgent, data: pd.DataFrame) -> DRLValidationResult:
        """
        Validación completa del agente DRL
        
        Args:
            agent: Agente DRL a validar
            data: Datos de mercado para validación
            
        Returns:
            Resultado completo de validación
        """
        logger.info("Iniciando validación completa del agente DRL")
        
        # 1. Walk-Forward Analysis
        logger.info("Ejecutando Walk-Forward Analysis...")
        wf_results = self._walk_forward_analysis(agent, data)
        
        # 2. CPCV adaptado para DRL
        logger.info("Ejecutando CPCV para DRL...")
        cpcv_results = self._drl_cpcv_analysis(agent, data)
        
        # 3. Análisis de estabilidad temporal
        logger.info("Analizando estabilidad temporal...")
        temporal_metrics = self._analyze_temporal_stability(wf_results)
        
        # 4. Análisis de adaptabilidad a regímenes
        logger.info("Analizando adaptabilidad a regímenes...")
        regime_metrics = self._analyze_regime_adaptability(agent, data)
        
        # 5. Compilar resultados
        validation_result = self._compile_validation_results(
            wf_results, cpcv_results, temporal_metrics, regime_metrics
        )
        
        logger.info(f"Validación completada - Robustez: {validation_result.robustness_score:.3f}")
        
        return validation_result
    
    def _walk_forward_analysis(self, agent: AdvancedDRLAgent, data: pd.DataFrame) -> List[Dict]:
        """Ejecutar Walk-Forward Analysis"""
        results = []
        
        for start_idx in range(0, len(data) - self.config.training_window - self.config.validation_window, 
                              self.config.step_size):
            
            # Definir ventanas
            train_end = start_idx + self.config.training_window
            val_end = train_end + self.config.validation_window
            
            if val_end > len(data):
                break
            
            train_data = data.iloc[start_idx:train_end]
            val_data = data.iloc[train_end:val_end]
            
            logger.info(f"WF Fold: {start_idx}-{train_end} (train), {train_end}-{val_end} (val)")
            
            # Entrenar agente
            train_metrics = self._train_agent_fold(agent, train_data)
            
            # Validar agente
            val_metrics = self._validate_agent_fold(agent, val_data)
            
            results.append({
                'fold_id': len(results),
                'train_start': start_idx,
                'train_end': train_end,
                'val_start': train_end,
                'val_end': val_end,
                'train_metrics': train_metrics,
                'val_metrics': val_metrics
            })
        
        return results
    
    def _drl_cpcv_analysis(self, agent: AdvancedDRLAgent, data: pd.DataFrame) -> List[Dict]:
        """CPCV adaptado para DRL"""
        results = []
        
        # Crear splits temporales con purging y embargo
        tscv = TimeSeriesSplit(n_splits=self.config.n_splits)
        
        for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(data)):
            # Aplicar purging y embargo
            purge_size = int(len(train_idx) * self.config.purge_pct)
            embargo_size = int(len(val_idx) * self.config.embargo_pct)
            
            # Ajustar índices
            train_idx = train_idx[:-purge_size] if purge_size > 0 else train_idx
            val_idx = val_idx[embargo_size:] if embargo_size > 0 else val_idx
            
            train_data = data.iloc[train_idx]
            val_data = data.iloc[val_idx]
            
            logger.info(f"CPCV Fold {fold_idx + 1}/{self.config.n_splits}")
            
            # Entrenar y validar
            train_metrics = self._train_agent_fold(agent, train_data)
            val_metrics = self._validate_agent_fold(agent, val_data)
            
            results.append({
                'fold_id': fold_idx,
                'train_metrics': train_metrics,
                'val_metrics': val_metrics,
                'train_size': len(train_data),
                'val_size': len(val_data)
            })
        
        return results
    
    def _train_agent_fold(self, agent: AdvancedDRLAgent, data: pd.DataFrame) -> Dict:
        """Entrenar agente en un fold específico"""
        env = DRLTradingEnvironment(data)
        
        episode_rewards = []
        
        for episode in range(self.config.min_training_episodes):
            state = env.reset()
            episode_reward = 0
            done = False
            
            while not done:
                action, log_prob, value = agent.select_action(state)
                next_state, reward, done, info = env.step(action)
                
                # Calcular recompensa multi-objetivo si hay información del trade
                if info:
                    market_regime = agent.detect_market_regime(data.iloc[max(0, env.current_step-50):env.current_step])
                    reward = agent.reward_system.calculate_reward(info, market_regime)
                
                # Almacenar experiencia
                agent.store_experience(state, action, reward, next_state, done, log_prob, value)
                
                state = next_state
                episode_reward += reward
            
            episode_rewards.append(episode_reward)
            
            # Actualizar política cada cierto número de pasos
            if len(agent.replay_buffer) >= agent.config['batch_size']:
                agent.update_policy()
        
        # Métricas de entrenamiento
        performance_metrics = env.get_performance_metrics()
        
        return {
            'avg_episode_reward': np.mean(episode_rewards),
            'std_episode_reward': np.std(episode_rewards),
            'final_performance': performance_metrics
        }
    
    def _validate_agent_fold(self, agent: AdvancedDRLAgent, data: pd.DataFrame) -> Dict:
        """Validar agente en un fold específico"""
        env = DRLTradingEnvironment(data)
        
        episode_metrics = []
        
        for episode in range(self.config.evaluation_episodes):
            state = env.reset()
            done = False
            
            while not done:
                action, _, _ = agent.select_action(state, deterministic=True)
                next_state, reward, done, info = env.step(action)
                state = next_state
            
            episode_metrics.append(env.get_performance_metrics())
        
        # Agregar métricas
        avg_metrics = {}
        for key in episode_metrics[0].keys():
            values = [m[key] for m in episode_metrics]
            avg_metrics[f'avg_{key}'] = np.mean(values)
            avg_metrics[f'std_{key}'] = np.std(values)
        
        return avg_metrics
    
    def _analyze_temporal_stability(self, wf_results: List[Dict]) -> Dict:
        """Analizar estabilidad temporal del rendimiento"""
        if not wf_results:
            return {'temporal_stability': 0.0}
        
        # Extraer métricas de validación
        val_returns = [r['val_metrics']['avg_total_return'] for r in wf_results]
        val_sharpes = [r['val_metrics']['avg_sharpe_ratio'] for r in wf_results]
        
        # Calcular estabilidad
        return_stability = 1.0 / (1.0 + np.std(val_returns)) if val_returns else 0.0
        sharpe_stability = 1.0 / (1.0 + np.std(val_sharpes)) if val_sharpes else 0.0
        
        temporal_stability = (return_stability + sharpe_stability) / 2
        
        return {
            'temporal_stability': temporal_stability,
            'return_stability': return_stability,
            'sharpe_stability': sharpe_stability,
            'return_trend': np.polyfit(range(len(val_returns)), val_returns, 1)[0] if len(val_returns) > 1 else 0
        }
    
    def _analyze_regime_adaptability(self, agent: AdvancedDRLAgent, data: pd.DataFrame) -> Dict:
        """Analizar adaptabilidad a diferentes regímenes de mercado"""
        if not agent.regime_detection_enabled:
            return {'regime_adaptability': 0.5}
        
        try:
            # Detectar regímenes en diferentes períodos
            regime_performance = defaultdict(list)
            
            window_size = 200
            for i in range(0, len(data) - window_size, window_size // 2):
                window_data = data.iloc[i:i + window_size]
                regime = agent.detect_market_regime(window_data)
                
                # Evaluar rendimiento en este régimen
                env = DRLTradingEnvironment(window_data)
                state = env.reset()
                done = False
                
                while not done:
                    action, _, _ = agent.select_action(state, deterministic=True)
                    next_state, reward, done, info = env.step(action)
                    state = next_state
                
                performance = env.get_performance_metrics()
                regime_performance[regime].append(performance['total_return'])
            
            # Calcular adaptabilidad
            regime_scores = []
            for regime, returns in regime_performance.items():
                if returns:
                    avg_return = np.mean(returns)
                    regime_scores.append(max(0, avg_return))  # Solo considerar retornos positivos
            
            adaptability = np.mean(regime_scores) if regime_scores else 0.0
            
            return {
                'regime_adaptability': adaptability,
                'regime_performance': dict(regime_performance)
            }
            
        except Exception as e:
            logger.error(f"Error analizando adaptabilidad a regímenes: {e}")
            return {'regime_adaptability': 0.5}
    
    def _compile_validation_results(self, wf_results: List[Dict], cpcv_results: List[Dict],
                                   temporal_metrics: Dict, regime_metrics: Dict) -> DRLValidationResult:
        """Compilar resultados finales de validación"""
        
        # Extraer métricas de validación
        all_val_metrics = []
        for result in wf_results + cpcv_results:
            if 'val_metrics' in result:
                all_val_metrics.append(result['val_metrics'])
        
        if not all_val_metrics:
            # Resultados por defecto si no hay métricas
            return DRLValidationResult(
                avg_return=0, std_return=0, sharpe_ratio=0, max_drawdown=1,
                win_rate=0, performance_variance=1, consistency_score=0,
                robustness_score=0, fold_results=[], wf_results=[],
                temporal_stability=0, regime_adaptability=0,
                is_stable=False, is_robust=False, validation_passed=False
            )
        
        # Calcular métricas agregadas
        avg_return = np.mean([m['avg_total_return'] for m in all_val_metrics])
        std_return = np.std([m['avg_total_return'] for m in all_val_metrics])
        avg_sharpe = np.mean([m['avg_sharpe_ratio'] for m in all_val_metrics])
        avg_drawdown = np.mean([m['avg_max_drawdown'] for m in all_val_metrics])
        avg_win_rate = np.mean([m['avg_win_rate'] for m in all_val_metrics])
        
        # Métricas de estabilidad
        performance_variance = std_return / (abs(avg_return) + 1e-8)
        consistency_score = 1.0 / (1.0 + performance_variance)
        
        # Score de robustez
        robustness_components = [
            max(0, avg_sharpe / 2),  # Sharpe ratio normalizado
            max(0, 1 - avg_drawdown * 2),  # Drawdown invertido
            avg_win_rate,  # Win rate
            temporal_metrics.get('temporal_stability', 0),
            regime_metrics.get('regime_adaptability', 0)
        ]
        robustness_score = np.mean(robustness_components)
        
        # Criterios de validación
        is_stable = (
            performance_variance <= self.config.max_performance_variance and
            avg_sharpe >= self.config.min_sharpe_ratio
        )
        
        is_robust = (
            robustness_score >= 0.6 and
            avg_drawdown <= self.config.max_drawdown_threshold
        )
        
        validation_passed = is_stable and is_robust
        
        return DRLValidationResult(
            avg_return=avg_return,
            std_return=std_return,
            sharpe_ratio=avg_sharpe,
            max_drawdown=avg_drawdown,
            win_rate=avg_win_rate,
            performance_variance=performance_variance,
            consistency_score=consistency_score,
            robustness_score=robustness_score,
            fold_results=cpcv_results,
            wf_results=wf_results,
            temporal_stability=temporal_metrics.get('temporal_stability', 0),
            regime_adaptability=regime_metrics.get('regime_adaptability', 0),
            is_stable=is_stable,
            is_robust=is_robust,
            validation_passed=validation_passed
        )
    
    def generate_validation_report(self, result: DRLValidationResult, save_path: str = None) -> str:
        """Generar reporte de validación"""
        report = f"""
=== REPORTE DE VALIDACIÓN DRL ===
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

MÉTRICAS PRINCIPALES:
- Retorno Promedio: {result.avg_return:.4f} ({result.avg_return*100:.2f}%)
- Desviación Estándar: {result.std_return:.4f}
- Sharpe Ratio: {result.sharpe_ratio:.3f}
- Máximo Drawdown: {result.max_drawdown:.4f} ({result.max_drawdown*100:.2f}%)
- Tasa de Acierto: {result.win_rate:.3f} ({result.win_rate*100:.1f}%)

MÉTRICAS DE ESTABILIDAD:
- Varianza de Rendimiento: {result.performance_variance:.3f}
- Score de Consistencia: {result.consistency_score:.3f}
- Score de Robustez: {result.robustness_score:.3f}
- Estabilidad Temporal: {result.temporal_stability:.3f}
- Adaptabilidad a Regímenes: {result.regime_adaptability:.3f}

VALIDACIÓN:
- Estable: {'✓' if result.is_stable else '✗'}
- Robusto: {'✓' if result.is_robust else '✗'}
- Validación Aprobada: {'✓' if result.validation_passed else '✗'}

FOLDS EJECUTADOS:
- Walk-Forward Folds: {len(result.wf_results)}
- CPCV Folds: {len(result.fold_results)}

RECOMENDACIONES:
"""
        
        if result.validation_passed:
            report += "✓ El agente DRL ha pasado todas las validaciones y está listo para producción.\n"
        else:
            if not result.is_stable:
                report += "⚠ El agente muestra inestabilidad en el rendimiento. Considerar más entrenamiento.\n"
            if not result.is_robust:
                report += "⚠ El agente no es suficientemente robusto. Revisar arquitectura y parámetros.\n"
        
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Reporte guardado en: {save_path}")
        
        return report


if __name__ == "__main__":
    # Configuración de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Ejemplo de uso
    from advanced_drl_system import AdvancedDRLAgent
    
    # Crear datos de ejemplo
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=2000, freq='H')
    data = pd.DataFrame({
        'timestamp': dates,
        'open': 100 + np.cumsum(np.random.randn(2000) * 0.1),
        'high': 0,
        'low': 0,
        'close': 0,
        'volume': np.random.randint(1000, 10000, 2000)
    })
    data['close'] = data['open'] + np.random.randn(2000) * 0.5
    data['high'] = np.maximum(data['open'], data['close']) + np.random.rand(2000) * 0.2
    data['low'] = np.minimum(data['open'], data['close']) - np.random.rand(2000) * 0.2
    
    # Crear agente y validador
    agent = AdvancedDRLAgent(state_dim=10, action_dim=3)
    validator = DRLValidator()
    
    # Ejecutar validación
    logger.info("Iniciando validación de ejemplo...")
    result = validator.validate_agent(agent, data)
    
    # Generar reporte
    report = validator.generate_validation_report(result)
    print(report)
    
    logger.info("Sistema de validación DRL inicializado correctamente")