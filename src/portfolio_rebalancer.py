# /src/portfolio_rebalancer.py
"""
Sistema de Rebalanceo Automático del Portfolio para SICAR
Ajusta dinámicamente las asignaciones de capital basado en rendimiento y riesgo.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SymbolMetrics:
    """Métricas de rendimiento para un símbolo específico."""
    symbol: str
    returns: List[float]
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    avg_trade_duration: float
    current_allocation: float
    recommended_allocation: float

class PortfolioRebalancer:
    """
    Sistema de rebalanceo automático del portfolio.
    
    Características:
    - Análisis de rendimiento por símbolo
    - Cálculo de métricas de riesgo
    - Rebalanceo basado en Sharpe ratio y volatilidad
    - Límites de asignación por seguridad
    """
    
    def __init__(self, 
                 min_allocation: float = 0.1,
                 max_allocation: float = 0.7,
                 rebalance_threshold: float = 0.05,
                 lookback_periods: int = 100):
        """
        Inicializa el rebalanceador.
        
        Args:
            min_allocation: Asignación mínima por símbolo (10%)
            max_allocation: Asignación máxima por símbolo (70%)
            rebalance_threshold: Umbral para activar rebalanceo (5%)
            lookback_periods: Períodos históricos para análisis
        """
        self.min_allocation = min_allocation
        self.max_allocation = max_allocation
        self.rebalance_threshold = rebalance_threshold
        self.lookback_periods = lookback_periods
        
        # Historial de rebalanceos
        self.rebalance_history = []
        
        logger.info(f"Rebalanceador inicializado:")
        logger.info(f"  Asignacion minima: {min_allocation*100:.1f}%")
        logger.info(f"  Asignacion maxima: {max_allocation*100:.1f}%")
        logger.info(f"  Umbral de rebalanceo: {rebalance_threshold*100:.1f}%")
    
    def calculate_symbol_metrics(self, 
                                results_df: pd.DataFrame, 
                                symbol: str) -> SymbolMetrics:
        """
        Calcula métricas de rendimiento para un símbolo.
        
        Args:
            results_df: DataFrame con resultados del backtesting
            symbol: Símbolo a analizar
            
        Returns:
            SymbolMetrics con las métricas calculadas
        """
        try:
            # Filtrar datos del símbolo
            symbol_data = results_df[results_df['symbol'] == symbol].copy()
            
            if symbol_data.empty:
                logger.warning(f"No hay datos para {symbol}")
                return SymbolMetrics(
                    symbol=symbol,
                    returns=[],
                    volatility=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    win_rate=0.0,
                    avg_trade_duration=0.0,
                    current_allocation=0.5,  # Default
                    recommended_allocation=0.5
                )
            
            # Calcular retornos
            symbol_data['price_change'] = symbol_data['price'].pct_change()
            returns = symbol_data['price_change'].dropna().tolist()
            
            # Métricas básicas
            volatility = np.std(returns) * np.sqrt(252) if returns else 0.0  # Anualizada
            mean_return = np.mean(returns) if returns else 0.0
            sharpe_ratio = (mean_return / volatility) if volatility > 0 else 0.0
            
            # Calcular drawdown máximo
            cumulative_returns = (1 + pd.Series(returns)).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = abs(drawdown.min()) if not drawdown.empty else 0.0
            
            # Métricas de trading
            trades = symbol_data[symbol_data['position'] != 'none']
            win_rate = 0.0
            avg_trade_duration = 0.0
            
            if not trades.empty:
                # Calcular win rate basado en cambios de precio
                trade_returns = trades['price'].pct_change().dropna()
                if not trade_returns.empty:
                    win_rate = len(trade_returns[trade_returns > 0]) / len(trade_returns)
                
                # Duración promedio (aproximada)
                avg_trade_duration = len(trades) / max(1, len(trades.groupby('position')))
            
            return SymbolMetrics(
                symbol=symbol,
                returns=returns[-self.lookback_periods:],  # Últimos N períodos
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                avg_trade_duration=avg_trade_duration,
                current_allocation=0.5,  # Se actualizará externamente
                recommended_allocation=0.5  # Se calculará después
            )
            
        except Exception as e:
            logger.error(f"Error calculando métricas para {symbol}: {e}")
            return SymbolMetrics(
                symbol=symbol,
                returns=[],
                volatility=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                avg_trade_duration=0.0,
                current_allocation=0.5,
                recommended_allocation=0.5
            )
    
    def calculate_optimal_allocation(self, 
                                   symbol_metrics: List[SymbolMetrics]) -> Dict[str, float]:
        """
        Calcula la asignación óptima basada en métricas de rendimiento.
        
        Args:
            symbol_metrics: Lista de métricas por símbolo
            
        Returns:
            Diccionario con asignaciones recomendadas
        """
        try:
            if not symbol_metrics:
                return {}
            
            # Calcular scores compuestos
            scores = {}
            
            for metrics in symbol_metrics:
                # Score basado en Sharpe ratio (40%)
                sharpe_score = max(0, metrics.sharpe_ratio) * 0.4
                
                # Score basado en win rate (30%)
                win_rate_score = metrics.win_rate * 0.3
                
                # Penalización por volatilidad (20%)
                volatility_penalty = max(0, 1 - metrics.volatility) * 0.2
                
                # Penalización por drawdown (10%)
                drawdown_penalty = max(0, 1 - metrics.max_drawdown) * 0.1
                
                # Score total
                total_score = sharpe_score + win_rate_score + volatility_penalty + drawdown_penalty
                scores[metrics.symbol] = max(0.1, total_score)  # Mínimo 0.1
            
            # Normalizar scores para que sumen 1.0
            total_score = sum(scores.values())
            if total_score > 0:
                normalized_allocations = {
                    symbol: score / total_score 
                    for symbol, score in scores.items()
                }
            else:
                # Distribución equitativa si no hay scores válidos
                equal_allocation = 1.0 / len(symbol_metrics)
                normalized_allocations = {
                    metrics.symbol: equal_allocation 
                    for metrics in symbol_metrics
                }
            
            # Aplicar límites de asignación
            final_allocations = {}
            for symbol, allocation in normalized_allocations.items():
                final_allocations[symbol] = max(
                    self.min_allocation, 
                    min(self.max_allocation, allocation)
                )
            
            # Renormalizar después de aplicar límites
            total_final = sum(final_allocations.values())
            if total_final > 0:
                final_allocations = {
                    symbol: allocation / total_final 
                    for symbol, allocation in final_allocations.items()
                }
            
            logger.info("Asignaciones calculadas:")
            for symbol, allocation in final_allocations.items():
                logger.info(f"  {symbol}: {allocation*100:.1f}%")
            
            return final_allocations
            
        except Exception as e:
            logger.error(f"Error calculando asignación óptima: {e}")
            # Distribución equitativa como fallback
            equal_allocation = 1.0 / len(symbol_metrics)
            return {metrics.symbol: equal_allocation for metrics in symbol_metrics}
    
    def should_rebalance(self, 
                        current_allocations: Dict[str, float],
                        recommended_allocations: Dict[str, float]) -> bool:
        """
        Determina si es necesario rebalancear el portfolio.
        
        Args:
            current_allocations: Asignaciones actuales
            recommended_allocations: Asignaciones recomendadas
            
        Returns:
            True si se debe rebalancear
        """
        try:
            max_deviation = 0.0
            
            for symbol in current_allocations.keys():
                current = current_allocations.get(symbol, 0.0)
                recommended = recommended_allocations.get(symbol, 0.0)
                deviation = abs(current - recommended)
                max_deviation = max(max_deviation, deviation)
            
            should_rebalance = max_deviation > self.rebalance_threshold
            
            logger.info(f"Desviacion maxima: {max_deviation*100:.2f}%")
            logger.info(f"Umbral de rebalanceo: {self.rebalance_threshold*100:.2f}%")
            logger.info(f"Rebalanceo necesario: {'Si' if should_rebalance else 'No'}")
            
            return should_rebalance
            
        except Exception as e:
            logger.error(f"Error evaluando necesidad de rebalanceo: {e}")
            return False
    
    def execute_rebalance(self, 
                         portfolio,
                         new_allocations: Dict[str, float]) -> bool:
        """
        Ejecuta el rebalanceo del portfolio.
        
        Args:
            portfolio: Instancia del MultiSymbolPortfolio
            new_allocations: Nuevas asignaciones de capital
            
        Returns:
            True si el rebalanceo fue exitoso
        """
        try:
            logger.info("Ejecutando rebalanceo del portfolio...")
            
            # Cerrar todas las posiciones abiertas
            for symbol in portfolio.symbols:
                if portfolio.is_position_open(symbol):
                    current_price = portfolio.positions[symbol].current_price
                    portfolio.close_position(symbol, current_price)
                    logger.info(f"Posicion cerrada para {symbol}")
            
            # Actualizar asignaciones de capital
            total_capital = portfolio.total_capital
            
            for symbol, allocation in new_allocations.items():
                if symbol in portfolio.positions:
                    new_capital = total_capital * allocation
                    portfolio.positions[symbol].allocated_capital = new_capital
                    portfolio.positions[symbol].available_capital = new_capital
                    
                    logger.info(f"{symbol}: Nueva asignacion ${new_capital:.2f} ({allocation*100:.1f}%)")
            
            # Actualizar la distribución en el portfolio
            portfolio.capital_allocation = new_allocations.copy()
            
            # Registrar el rebalanceo
            rebalance_record = {
                'timestamp': datetime.now(),
                'allocations': new_allocations.copy(),
                'total_capital': total_capital
            }
            self.rebalance_history.append(rebalance_record)
            
            logger.info("Rebalanceo completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando rebalanceo: {e}")
            return False
    
    def analyze_and_rebalance(self, 
                             portfolio,
                             results_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analiza el rendimiento y ejecuta rebalanceo si es necesario.
        
        Args:
            portfolio: Instancia del MultiSymbolPortfolio
            results_df: DataFrame con resultados del backtesting
            
        Returns:
            Diccionario con información del análisis y rebalanceo
        """
        try:
            logger.info("Iniciando analisis para rebalanceo...")
            
            # Calcular métricas por símbolo
            symbol_metrics = []
            current_allocations = {}
            
            for symbol in portfolio.symbols:
                metrics = self.calculate_symbol_metrics(results_df, symbol)
                metrics.current_allocation = portfolio.capital_allocation.get(symbol, 0.5)
                symbol_metrics.append(metrics)
                current_allocations[symbol] = metrics.current_allocation
            
            # Calcular asignaciones óptimas
            recommended_allocations = self.calculate_optimal_allocation(symbol_metrics)
            
            # Actualizar métricas con recomendaciones
            for metrics in symbol_metrics:
                metrics.recommended_allocation = recommended_allocations.get(metrics.symbol, 0.5)
            
            # Determinar si se necesita rebalanceo
            needs_rebalance = self.should_rebalance(current_allocations, recommended_allocations)
            
            rebalance_executed = False
            if needs_rebalance:
                rebalance_executed = self.execute_rebalance(portfolio, recommended_allocations)
            
            return {
                'timestamp': datetime.now(),
                'symbol_metrics': symbol_metrics,
                'current_allocations': current_allocations,
                'recommended_allocations': recommended_allocations,
                'needs_rebalance': needs_rebalance,
                'rebalance_executed': rebalance_executed,
                'rebalance_count': len(self.rebalance_history)
            }
            
        except Exception as e:
            logger.error(f"Error en análisis de rebalanceo: {e}")
            return {
                'timestamp': datetime.now(),
                'error': str(e),
                'needs_rebalance': False,
                'rebalance_executed': False
            }
    
    def get_rebalance_summary(self) -> Dict[str, Any]:
        """
        Obtiene un resumen del historial de rebalanceos.
        
        Returns:
            Diccionario con estadísticas de rebalanceo
        """
        if not self.rebalance_history:
            return {
                'total_rebalances': 0,
                'last_rebalance': None,
                'avg_days_between_rebalances': 0
            }
        
        total_rebalances = len(self.rebalance_history)
        last_rebalance = self.rebalance_history[-1]['timestamp']
        
        # Calcular días promedio entre rebalanceos
        avg_days = 0
        if total_rebalances > 1:
            first_rebalance = self.rebalance_history[0]['timestamp']
            total_days = (last_rebalance - first_rebalance).days
            avg_days = total_days / (total_rebalances - 1)
        
        return {
            'total_rebalances': total_rebalances,
            'last_rebalance': last_rebalance,
            'avg_days_between_rebalances': avg_days,
            'rebalance_history': self.rebalance_history
        }

def create_rebalancer(config: Dict[str, Any] = None) -> PortfolioRebalancer:
    """
    Crea una instancia del rebalanceador con configuración personalizada.
    
    Args:
        config: Configuración opcional del rebalanceador
        
    Returns:
        Instancia configurada del PortfolioRebalancer
    """
    default_config = {
        'min_allocation': 0.1,
        'max_allocation': 0.7,
        'rebalance_threshold': 0.05,
        'lookback_periods': 100
    }
    
    if config:
        default_config.update(config)
    
    return PortfolioRebalancer(**default_config)

if __name__ == "__main__":
    # Ejemplo de uso
    logging.basicConfig(level=logging.INFO)
    
    # Crear rebalanceador
    rebalancer = create_rebalancer()
    
    print("Sistema de rebalanceo automático inicializado")
    print(f"Configuración:")
    print(f"  - Asignación mínima: {rebalancer.min_allocation*100:.1f}%")
    print(f"  - Asignación máxima: {rebalancer.max_allocation*100:.1f}%")
    print(f"  - Umbral de rebalanceo: {rebalancer.rebalance_threshold*100:.1f}%")