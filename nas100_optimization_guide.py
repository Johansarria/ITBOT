# nas100_optimization_guide.py
# Guía de optimización y configuración avanzada para la estrategia NAS100

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import itertools
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NAS100StrategyOptimizer:
    """
    Optimizador avanzado para la estrategia NAS100
    Incluye:
    - Optimización de parámetros
    - Análisis de sensibilidad
    - Configuraciones por condiciones de mercado
    - Métricas de rendimiento avanzadas
    """
    
    def __init__(self):
        self.optimization_results = []
        self.best_params = None
        self.best_score = -float('inf')
        
    def define_parameter_ranges(self) -> Dict[str, List]:
        """
        Define rangos de parámetros para optimización
        """
        return {
            'momentum_period_short': [3, 5, 7, 10],
            'momentum_period_long': [15, 20, 25, 30],
            'momentum_threshold': [0.01, 0.015, 0.02, 0.025],
            'breakout_period': [8, 10, 12, 15],
            'breakout_threshold': [0.015, 0.02, 0.025, 0.03],
            'session_multiplier': [1.2, 1.5, 1.8, 2.0],
            'volatility_multiplier': [1.0, 1.3, 1.5, 1.8]
        }
    
    def calculate_fitness_score(self, results: Dict[str, Any]) -> float:
        """
        Calcula score de fitness para optimización
        Combina múltiples métricas con pesos específicos
        """
        # Pesos para diferentes métricas
        weights = {
            'return': 0.4,      # 40% - Retorno total
            'sharpe': 0.25,     # 25% - Ratio Sharpe
            'drawdown': 0.2,    # 20% - Control de drawdown
            'win_rate': 0.1,    # 10% - Tasa de aciertos
            'profit_factor': 0.05  # 5% - Factor de beneficio
        }
        
        # Normalizar métricas
        return_score = min(results['total_return'] * 2, 1.0)  # Cap at 50% return
        
        # Sharpe ratio aproximado (asumiendo volatilidad)
        volatility = results.get('volatility', 0.15)  # 15% default
        sharpe_ratio = results['total_return'] / volatility if volatility > 0 else 0
        sharpe_score = min(sharpe_ratio / 2.0, 1.0)  # Cap at 2.0 Sharpe
        
        # Drawdown score (invertido - menor drawdown = mejor score)
        drawdown_score = max(0, 1 - (results['max_drawdown'] / 0.2))  # Penalizar >20% drawdown
        
        # Win rate score
        win_rate_score = results['win_rate']
        
        # Profit factor score
        profit_factor = results.get('profit_factor', 1.0)
        profit_factor_score = min((profit_factor - 1) / 2, 1.0)  # Cap at 3.0 PF
        
        # Calcular score final
        fitness_score = (
            weights['return'] * return_score +
            weights['sharpe'] * sharpe_score +
            weights['drawdown'] * drawdown_score +
            weights['win_rate'] * win_rate_score +
            weights['profit_factor'] * profit_factor_score
        )
        
        return fitness_score
    
    def optimize_parameters(self, data: pd.DataFrame, max_combinations: int = 100) -> Dict[str, Any]:
        """
        Optimiza parámetros usando grid search limitado
        """
        logger.info("Iniciando optimización de parámetros...")
        
        param_ranges = self.define_parameter_ranges()
        
        # Generar combinaciones de parámetros
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        
        # Limitar combinaciones para evitar explosión computacional
        all_combinations = list(itertools.product(*param_values))
        
        if len(all_combinations) > max_combinations:
            # Muestreo aleatorio de combinaciones
            np.random.seed(42)
            selected_indices = np.random.choice(len(all_combinations), max_combinations, replace=False)
            combinations = [all_combinations[i] for i in selected_indices]
        else:
            combinations = all_combinations
        
        logger.info(f"Probando {len(combinations)} combinaciones de parámetros")
        
        best_score = -float('inf')
        best_params = None
        best_results = None
        
        for i, combination in enumerate(combinations):
            if i % 20 == 0:
                logger.info(f"Progreso: {i}/{len(combinations)} ({i/len(combinations)*100:.1f}%)")
            
            # Crear parámetros para esta combinación
            params = dict(zip(param_names, combination))
            
            try:
                # Ejecutar backtest con estos parámetros
                results = self.run_backtest_with_params(data, params)
                
                # Calcular fitness score
                fitness_score = self.calculate_fitness_score(results)
                
                # Guardar resultado
                self.optimization_results.append({
                    'params': params.copy(),
                    'results': results.copy(),
                    'fitness_score': fitness_score
                })
                
                # Actualizar mejor resultado
                if fitness_score > best_score:
                    best_score = fitness_score
                    best_params = params.copy()
                    best_results = results.copy()
                    
            except Exception as e:
                logger.warning(f"Error en combinación {i}: {e}")
                continue
        
        logger.info(f"Optimización completada. Mejor score: {best_score:.4f}")
        
        return {
            'best_params': best_params,
            'best_results': best_results,
            'best_score': best_score,
            'all_results': self.optimization_results
        }
    
    def run_backtest_with_params(self, data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta backtest con parámetros específicos
        """
        from nas100_test import SimpleNAS100Strategy, SimpleBacktester
        
        # Crear estrategia con parámetros personalizados
        strategy = SimpleNAS100Strategy()
        
        # Aplicar parámetros
        for param_name, param_value in params.items():
            if hasattr(strategy, param_name):
                setattr(strategy, param_name, param_value)
        
        # Ejecutar backtest
        backtester = SimpleBacktester(initial_balance=100000.0)
        results = backtester.run_backtest(strategy, data)
        
        # Calcular métricas adicionales
        completed_trades = [t for t in results['trades'] if 'pnl' in t]
        if completed_trades:
            winning_pnl = sum(t['pnl'] for t in completed_trades if t['pnl'] > 0)
            losing_pnl = abs(sum(t['pnl'] for t in completed_trades if t['pnl'] < 0))
            
            results['profit_factor'] = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
            
            # Calcular volatilidad de retornos
            if len(results['balance_history']) > 1:
                balance_returns = pd.Series(results['balance_history']).pct_change().dropna()
                results['volatility'] = balance_returns.std() * np.sqrt(252)  # Anualizada
        
        return results
    
    def analyze_parameter_sensitivity(self, optimization_results: List[Dict]) -> Dict[str, Any]:
        """
        Analiza la sensibilidad de cada parámetro
        """
        logger.info("Analizando sensibilidad de parámetros...")
        
        param_impact = {}
        
        # Obtener todos los nombres de parámetros
        if optimization_results:
            param_names = list(optimization_results[0]['params'].keys())
            
            for param_name in param_names:
                param_values = []
                fitness_scores = []
                
                for result in optimization_results:
                    param_values.append(result['params'][param_name])
                    fitness_scores.append(result['fitness_score'])
                
                # Calcular correlación entre parámetro y fitness
                correlation = np.corrcoef(param_values, fitness_scores)[0, 1]
                
                # Calcular rango de impacto
                unique_values = list(set(param_values))
                if len(unique_values) > 1:
                    impact_scores = []
                    for value in unique_values:
                        scores = [fs for pv, fs in zip(param_values, fitness_scores) if pv == value]
                        if scores:
                            impact_scores.append(np.mean(scores))
                    
                    impact_range = max(impact_scores) - min(impact_scores) if len(impact_scores) > 1 else 0
                else:
                    impact_range = 0
                
                param_impact[param_name] = {
                    'correlation': correlation if not np.isnan(correlation) else 0,
                    'impact_range': impact_range,
                    'optimal_value': None
                }
                
                # Encontrar valor óptimo
                best_result = max(optimization_results, key=lambda x: x['fitness_score'])
                param_impact[param_name]['optimal_value'] = best_result['params'][param_name]
        
        return param_impact
    
    def generate_market_condition_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Genera configuraciones específicas para diferentes condiciones de mercado
        """
        return {
            'trending_bull': {
                'description': 'Mercado alcista con tendencia fuerte',
                'momentum_period_short': 3,
                'momentum_period_long': 15,
                'momentum_threshold': 0.01,
                'breakout_threshold': 0.015,
                'session_multiplier': 2.0,
                'volatility_multiplier': 1.8
            },
            'trending_bear': {
                'description': 'Mercado bajista con tendencia fuerte',
                'momentum_period_short': 5,
                'momentum_period_long': 25,
                'momentum_threshold': 0.015,
                'breakout_threshold': 0.02,
                'session_multiplier': 1.5,
                'volatility_multiplier': 1.3
            },
            'sideways_low_vol': {
                'description': 'Mercado lateral con baja volatilidad',
                'momentum_period_short': 7,
                'momentum_period_long': 30,
                'momentum_threshold': 0.025,
                'breakout_threshold': 0.03,
                'session_multiplier': 1.2,
                'volatility_multiplier': 1.0
            },
            'high_volatility': {
                'description': 'Mercado con alta volatilidad',
                'momentum_period_short': 5,
                'momentum_period_long': 20,
                'momentum_threshold': 0.02,
                'breakout_threshold': 0.025,
                'session_multiplier': 1.3,
                'volatility_multiplier': 1.5
            },
            'balanced': {
                'description': 'Configuración balanceada para condiciones mixtas',
                'momentum_period_short': 5,
                'momentum_period_long': 20,
                'momentum_threshold': 0.015,
                'breakout_threshold': 0.02,
                'session_multiplier': 1.5,
                'volatility_multiplier': 1.3
            }
        }
    
    def print_optimization_report(self, optimization_results: Dict[str, Any]):
        """
        Imprime reporte detallado de optimización
        """
        print("\n" + "="*70)
        print("REPORTE DE OPTIMIZACIÓN ESTRATEGIA NAS100")
        print("="*70)
        
        best_params = optimization_results['best_params']
        best_results = optimization_results['best_results']
        best_score = optimization_results['best_score']
        
        print(f"\n🏆 MEJORES PARÁMETROS (Score: {best_score:.4f}):")
        for param, value in best_params.items():
            print(f"  {param}: {value}")
        
        print(f"\n📊 RESULTADOS CON MEJORES PARÁMETROS:")
        print(f"  Retorno total: {best_results['total_return']:.2%}")
        print(f"  Win rate: {best_results['win_rate']:.2%}")
        print(f"  Max drawdown: {best_results['max_drawdown']:.2%}")
        print(f"  Total trades: {best_results['total_trades']}")
        print(f"  Profit factor: {best_results.get('profit_factor', 'N/A')}")
        
        # Análisis de sensibilidad
        sensitivity = self.analyze_parameter_sensitivity(optimization_results['all_results'])
        
        print(f"\n🔍 ANÁLISIS DE SENSIBILIDAD:")
        for param, analysis in sensitivity.items():
            impact_level = "Alta" if analysis['impact_range'] > 0.1 else "Media" if analysis['impact_range'] > 0.05 else "Baja"
            print(f"  {param}:")
            print(f"    Impacto: {impact_level} (rango: {analysis['impact_range']:.4f})")
            print(f"    Correlación: {analysis['correlation']:.3f}")
            print(f"    Valor óptimo: {analysis['optimal_value']}")
        
        # Configuraciones por condición de mercado
        market_configs = self.generate_market_condition_configs()
        
        print(f"\n🎯 CONFIGURACIONES POR CONDICIÓN DE MERCADO:")
        for condition, config in market_configs.items():
            print(f"\n  {condition.upper()}:")
            print(f"    {config['description']}")
            for param, value in config.items():
                if param != 'description':
                    print(f"    {param}: {value}")
        
        print("\n" + "="*70)

def run_comprehensive_optimization():
    """
    Ejecuta optimización completa de la estrategia NAS100
    """
    from nas100_test import generate_nas100_data
    
    print("🚀 Iniciando optimización completa de estrategia NAS100...")
    
    # Generar datos de prueba más extensos
    data = generate_nas100_data(days=60, start_price=15000.0)
    
    # Crear optimizador
    optimizer = NAS100StrategyOptimizer()
    
    # Ejecutar optimización
    optimization_results = optimizer.optimize_parameters(data, max_combinations=50)
    
    # Mostrar reporte
    optimizer.print_optimization_report(optimization_results)
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Guardar mejores parámetros
    with open(f"nas100_best_params_{timestamp}.txt", 'w', encoding='utf-8') as f:
        f.write("MEJORES PARÁMETROS ESTRATEGIA NAS100\n")
        f.write("=" * 40 + "\n\n")
        
        best_params = optimization_results['best_params']
        for param, value in best_params.items():
            f.write(f"{param} = {value}\n")
        
        f.write(f"\nFitness Score: {optimization_results['best_score']:.4f}\n")
        f.write(f"Retorno: {optimization_results['best_results']['total_return']:.2%}\n")
        f.write(f"Win Rate: {optimization_results['best_results']['win_rate']:.2%}\n")
    
    print(f"\n💾 Mejores parámetros guardados en: nas100_best_params_{timestamp}.txt")
    
    return optimization_results

if __name__ == "__main__":
    results = run_comprehensive_optimization()