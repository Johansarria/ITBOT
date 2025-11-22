#!/usr/bin/env python3
"""
Capital Strategy Evaluator - SICAR
===================================

Sistema avanzado para evaluar diferentes estrategias de trading
según niveles de capital disponible.

Estrategias implementadas:
- Conservadora: 200-500 USDT (bajo riesgo, alta diversificación)
- Moderada: 500-1000 USDT (riesgo medio, diversificación balanceada)
- Agresiva: 1000+ USDT (alto riesgo, concentración estratégica)

Año: 2025
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass

from multi_asset_backtester import MultiAssetBacktester
from multi_asset_data_system import MultiAssetDataSystem

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StrategyConfig:
    """Configuración de estrategia por nivel de capital"""
    name: str
    capital_range: Tuple[float, float]
    max_position_size: float
    risk_multiplier: float
    max_symbols: int
    stop_loss_pct: float
    take_profit_pct: float
    volatility_threshold: float
    correlation_limit: float
    signal_strength_min: float
    description: str

class StrategyBacktester(MultiAssetBacktester):
    """
    Backtester personalizado que aplica configuraciones de estrategia específicas
    """
    
    def __init__(self, initial_capital: float, strategy: StrategyConfig):
        """Inicializar con estrategia específica"""
        super().__init__(initial_capital)
        self.strategy = strategy
        
        # Aplicar configuración de estrategia a todos los asset classes
        for asset_class in ['cryptocurrencies', 'forex', 'indices', 'commodities']:
            self.risk_params[asset_class] = {
                'max_position_size': strategy.max_position_size,
                'volatility_multiplier': strategy.risk_multiplier,
                'stop_loss_pct': strategy.stop_loss_pct,
                'take_profit_pct': strategy.take_profit_pct,
                'correlation_limit': strategy.correlation_limit,
                'volatility_threshold': strategy.volatility_threshold,
                'signal_strength_min': strategy.signal_strength_min
            }
    
    def calculate_position_size(self, symbol: str, price: float, 
                              volatility: float = None) -> float:
        """
        Calcular tamaño de posición usando configuración de estrategia
        """
        # Usar configuración de estrategia
        max_position_size = self.strategy.max_position_size
        volatility_multiplier = self.strategy.risk_multiplier
        
        # Tamaño base de posición
        base_position_size = self.current_capital * max_position_size
        
        # Ajustar por volatilidad si está disponible
        if volatility is not None:
            # Reducir tamaño si la volatilidad es alta
            volatility_adjustment = 1.0 / (1.0 + volatility * volatility_multiplier)
            base_position_size *= volatility_adjustment
        
        # Asegurar que no excedemos límites
        max_position_value = min(base_position_size, self.current_capital * 0.1)  # Máximo 10%
        
        return max_position_value

class CapitalStrategyEvaluator:
    """
    Evaluador de estrategias por niveles de capital
    """
    
    def __init__(self):
        """Inicializar evaluador"""
        self.strategies = self._define_strategies()
        self.test_capitals = [200, 350, 500, 750, 1000, 1500, 2000]
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        self.results = {}
        
        logger.info("🎯 Evaluador de Estrategias por Capital inicializado")
        
    def _define_strategies(self) -> Dict[str, StrategyConfig]:
        """
        Definir estrategias diferenciadas por capital
        """
        strategies = {
            'conservadora': StrategyConfig(
                name='Conservadora',
                capital_range=(200, 500),
                max_position_size=0.015,  # 1.5% por posición
                risk_multiplier=0.5,      # Menor riesgo
                max_symbols=8,            # Mayor diversificación
                stop_loss_pct=0.03,       # 3% stop loss
                take_profit_pct=0.06,     # 6% take profit
                volatility_threshold=0.15, # Menor volatilidad
                correlation_limit=0.6,    # Menor correlación
                signal_strength_min=0.3,  # Señales más fuertes
                description="Estrategia de bajo riesgo con alta diversificación"
            ),
            
            'moderada': StrategyConfig(
                name='Moderada',
                capital_range=(500, 1000),
                max_position_size=0.025,  # 2.5% por posición
                risk_multiplier=0.75,     # Riesgo medio
                max_symbols=6,            # Diversificación balanceada
                stop_loss_pct=0.04,       # 4% stop loss
                take_profit_pct=0.08,     # 8% take profit
                volatility_threshold=0.20, # Volatilidad media
                correlation_limit=0.7,    # Correlación media
                signal_strength_min=0.25, # Señales moderadas
                description="Estrategia balanceada de riesgo-retorno"
            ),
            
            'agresiva': StrategyConfig(
                name='Agresiva',
                capital_range=(1000, float('inf')),
                max_position_size=0.04,   # 4% por posición
                risk_multiplier=1.2,      # Mayor riesgo
                max_symbols=4,            # Menor diversificación
                stop_loss_pct=0.06,       # 6% stop loss
                take_profit_pct=0.12,     # 12% take profit
                volatility_threshold=0.30, # Mayor volatilidad
                correlation_limit=0.8,    # Mayor correlación permitida
                signal_strength_min=0.2,  # Señales más flexibles
                description="Estrategia de alto riesgo con concentración"
            )
        }
        
        return strategies
        
    def get_strategy_for_capital(self, capital: float) -> StrategyConfig:
        """
        Obtener estrategia apropiada para nivel de capital
        """
        for strategy in self.strategies.values():
            if strategy.capital_range[0] <= capital <= strategy.capital_range[1]:
                return strategy
        
        # Si el capital es muy alto, usar estrategia agresiva
        return self.strategies['agresiva']
        
    def create_custom_backtester(self, capital: float, strategy: StrategyConfig) -> StrategyBacktester:
        """
        Crear backtester personalizado según estrategia
        """
        return StrategyBacktester(capital, strategy)
        
    def run_strategy_comparison(self) -> Dict:
        """
        Ejecutar comparación completa de estrategias
        """
        logger.info("🚀 Iniciando evaluación de estrategias por capital...")
        
        comparison_results = {
            'strategy_performance': {},
            'capital_analysis': {},
            'optimization_recommendations': {},
            'timestamp': datetime.now().isoformat()
        }
        
        for capital in self.test_capitals:
            logger.info(f"\n💰 Evaluando capital: ${capital:,.0f}")
            
            # Obtener estrategia apropiada
            strategy = self.get_strategy_for_capital(capital)
            logger.info(f"📊 Estrategia seleccionada: {strategy.name}")
            
            # Crear backtester personalizado
            backtester = self.create_custom_backtester(capital, strategy)
            
            # Seleccionar símbolos según estrategia
            selected_symbols = self.test_symbols[:strategy.max_symbols]
            
            # Ejecutar backtest
            results = backtester.run_backtest(selected_symbols)
            
            if results:
                # Calcular métricas adicionales
                enhanced_results = self._calculate_enhanced_metrics(results, strategy, capital)
                
                comparison_results['strategy_performance'][capital] = {
                    'strategy_name': strategy.name,
                    'strategy_config': strategy.__dict__,
                    'backtest_results': enhanced_results,
                    'symbols_used': selected_symbols,
                    'capital_efficiency': enhanced_results.get('total_return', 0) / capital * 100
                }
                
                logger.info(f"  Retorno: {enhanced_results.get('total_return_pct', 0):+.2f}%")
                logger.info(f"  Trades: {enhanced_results.get('total_trades', 0)}")
                logger.info(f"  Win Rate: {enhanced_results.get('win_rate', 0):.1f}%")
            
        # Analizar resultados por estrategia
        comparison_results['capital_analysis'] = self._analyze_strategy_performance(comparison_results['strategy_performance'])
        
        # Generar recomendaciones
        comparison_results['optimization_recommendations'] = self._generate_strategy_recommendations(comparison_results)
        
        return comparison_results
        
    def _calculate_enhanced_metrics(self, results: Dict, strategy: StrategyConfig, capital: float) -> Dict:
        """
        Calcular métricas mejoradas para análisis
        """
        enhanced = results.copy()
        
        # Métricas de eficiencia de capital
        total_return = results.get('total_return', 0)
        enhanced['capital_efficiency'] = (total_return / capital) * 100
        enhanced['risk_adjusted_return'] = total_return / max(strategy.max_position_size * capital, 1)
        
        # Métricas de riesgo
        trade_history = results.get('trade_history', [])
        if trade_history:
            returns = [trade.get('pnl_pct', 0) for trade in trade_history]
            enhanced['volatility'] = np.std(returns) if returns else 0
            enhanced['max_drawdown'] = min(returns) if returns else 0
            enhanced['sharpe_ratio'] = np.mean(returns) / max(np.std(returns), 0.001) if returns else 0
        
        # Métricas de estrategia
        enhanced['strategy_score'] = self._calculate_strategy_score(enhanced, strategy)
        
        return enhanced
        
    def _calculate_strategy_score(self, results: Dict, strategy: StrategyConfig) -> float:
        """
        Calcular puntuación de estrategia (0-100)
        """
        score = 0
        
        # Rentabilidad (40%)
        return_pct = results.get('total_return_pct', 0)
        if return_pct > 0:
            score += min(return_pct * 2, 40)  # Máximo 40 puntos
        
        # Win Rate (25%)
        win_rate = results.get('win_rate', 0)
        score += (win_rate / 100) * 25
        
        # Sharpe Ratio (20%)
        sharpe = results.get('sharpe_ratio', 0)
        if sharpe > 0:
            score += min(sharpe * 10, 20)  # Máximo 20 puntos
        
        # Eficiencia de capital (15%)
        efficiency = results.get('capital_efficiency', 0)
        if efficiency > 0:
            score += min(efficiency, 15)  # Máximo 15 puntos
        
        return min(score, 100)
        
    def _analyze_strategy_performance(self, performance_data: Dict) -> Dict:
        """
        Analizar rendimiento por estrategia
        """
        analysis = {
            'by_strategy': {},
            'best_capital_ranges': {},
            'performance_trends': {}
        }
        
        # Agrupar por estrategia
        strategy_groups = {}
        for capital, data in performance_data.items():
            strategy_name = data['strategy_name']
            if strategy_name not in strategy_groups:
                strategy_groups[strategy_name] = []
            strategy_groups[strategy_name].append((capital, data))
        
        # Analizar cada estrategia
        for strategy_name, capital_data in strategy_groups.items():
            returns = [data['backtest_results'].get('total_return_pct', 0) for _, data in capital_data]
            scores = [data['backtest_results'].get('strategy_score', 0) for _, data in capital_data]
            
            analysis['by_strategy'][strategy_name] = {
                'avg_return': np.mean(returns),
                'avg_score': np.mean(scores),
                'consistency': 1 - (np.std(returns) / max(abs(np.mean(returns)), 1)),
                'capital_count': len(capital_data),
                'best_capital': max(capital_data, key=lambda x: x[1]['backtest_results'].get('strategy_score', 0))[0]
            }
        
        return analysis
        
    def _generate_strategy_recommendations(self, results: Dict) -> Dict:
        """
        Generar recomendaciones estratégicas
        """
        recommendations = {
            'by_capital_level': {},
            'general_insights': [],
            'optimization_suggestions': []
        }
        
        # Recomendaciones por nivel de capital
        for capital, data in results['strategy_performance'].items():
            strategy_score = data['backtest_results'].get('strategy_score', 0)
            return_pct = data['backtest_results'].get('total_return_pct', 0)
            
            if strategy_score >= 70:
                recommendation = "Excelente - Mantener estrategia actual"
            elif strategy_score >= 50:
                recommendation = "Buena - Considerar optimizaciones menores"
            elif strategy_score >= 30:
                recommendation = "Regular - Requiere optimización"
            else:
                recommendation = "Pobre - Cambio de estrategia necesario"
            
            recommendations['by_capital_level'][capital] = {
                'recommendation': recommendation,
                'strategy_used': data['strategy_name'],
                'score': strategy_score,
                'return': return_pct,
                'suggested_improvements': self._suggest_improvements(data)
            }
        
        # Insights generales
        best_strategy = max(results['capital_analysis']['by_strategy'].items(), 
                          key=lambda x: x[1]['avg_score'])
        
        recommendations['general_insights'] = [
            f"Mejor estrategia general: {best_strategy[0]} (Score: {best_strategy[1]['avg_score']:.1f})",
            f"Capital óptimo identificado: ${best_strategy[1]['best_capital']:,.0f}",
            "Todas las estrategias requieren optimización debido a rentabilidad negativa",
            "Se recomienda implementar señales long/short dinámicas"
        ]
        
        return recommendations
        
    def _suggest_improvements(self, strategy_data: Dict) -> List[str]:
        """
        Sugerir mejoras específicas para una estrategia
        """
        improvements = []
        results = strategy_data['backtest_results']
        
        if results.get('win_rate', 0) < 40:
            improvements.append("Mejorar filtros de señales para aumentar win rate")
        
        if results.get('total_return_pct', 0) < 0:
            improvements.append("Implementar señales long en mercados alcistas")
        
        if results.get('sharpe_ratio', 0) < 0.5:
            improvements.append("Optimizar gestión de riesgo y stop-loss dinámico")
        
        if results.get('volatility', 0) > 0.1:
            improvements.append("Reducir volatilidad con mejor diversificación")
        
        return improvements
        
    def create_visual_analysis(self, results: Dict) -> str:
        """
        Crear análisis visual de estrategias
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Análisis de Estrategias por Nivel de Capital - SICAR 2025', fontsize=16, fontweight='bold')
        
        # Datos para gráficos
        capitals = list(results['strategy_performance'].keys())
        returns = [results['strategy_performance'][c]['backtest_results'].get('total_return_pct', 0) for c in capitals]
        scores = [results['strategy_performance'][c]['backtest_results'].get('strategy_score', 0) for c in capitals]
        strategies = [results['strategy_performance'][c]['strategy_name'] for c in capitals]
        
        # Gráfico 1: Retorno por Capital
        axes[0, 0].plot(capitals, returns, 'o-', linewidth=2, markersize=8)
        axes[0, 0].set_title('Retorno % por Nivel de Capital')
        axes[0, 0].set_xlabel('Capital (USDT)')
        axes[0, 0].set_ylabel('Retorno (%)')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axhline(y=0, color='red', linestyle='--', alpha=0.5)
        
        # Gráfico 2: Score por Capital
        colors = ['green' if s >= 50 else 'orange' if s >= 30 else 'red' for s in scores]
        axes[0, 1].bar(range(len(capitals)), scores, color=colors, alpha=0.7)
        axes[0, 1].set_title('Score de Estrategia por Capital')
        axes[0, 1].set_xlabel('Nivel de Capital')
        axes[0, 1].set_ylabel('Score (0-100)')
        axes[0, 1].set_xticks(range(len(capitals)))
        axes[0, 1].set_xticklabels([f'${c}' for c in capitals], rotation=45)
        
        # Gráfico 3: Estrategias utilizadas
        strategy_counts = pd.Series(strategies).value_counts()
        axes[1, 0].pie(strategy_counts.values, labels=strategy_counts.index, autopct='%1.1f%%')
        axes[1, 0].set_title('Distribución de Estrategias Utilizadas')
        
        # Gráfico 4: Eficiencia de Capital
        efficiencies = [results['strategy_performance'][c]['capital_efficiency'] for c in capitals]
        axes[1, 1].scatter(capitals, efficiencies, c=scores, cmap='RdYlGn', s=100, alpha=0.7)
        axes[1, 1].set_title('Eficiencia de Capital vs Score')
        axes[1, 1].set_xlabel('Capital (USDT)')
        axes[1, 1].set_ylabel('Eficiencia (%)')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Guardar gráfico
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'capital_strategy_analysis_{timestamp}.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return filename
        
    def print_comprehensive_report(self, results: Dict):
        """
        Imprimir reporte completo
        """
        print("\n" + "="*100)
        print("📊 EVALUACIÓN DE ESTRATEGIAS POR NIVEL DE CAPITAL - SICAR 2025")
        print("="*100)
        
        # Resumen por capital
        print(f"\n💰 RENDIMIENTO POR NIVEL DE CAPITAL:")
        print("-" * 80)
        print(f"{'Capital':<10} {'Estrategia':<12} {'Retorno %':<10} {'Score':<8} {'Trades':<8} {'Win Rate':<10}")
        print("-" * 80)
        
        for capital, data in results['strategy_performance'].items():
            br = data['backtest_results']
            print(f"${capital:<9.0f} {data['strategy_name']:<12} {br.get('total_return_pct', 0):+7.2f}% "
                  f"{br.get('strategy_score', 0):6.1f}   {br.get('total_trades', 0):6.0f}   "
                  f"{br.get('win_rate', 0):7.1f}%")
        
        # Análisis por estrategia
        print(f"\n📈 ANÁLISIS POR ESTRATEGIA:")
        print("-" * 60)
        for strategy, analysis in results['capital_analysis']['by_strategy'].items():
            print(f"\n🎯 {strategy.upper()}:")
            print(f"  • Retorno promedio: {analysis['avg_return']:+.2f}%")
            print(f"  • Score promedio: {analysis['avg_score']:.1f}/100")
            print(f"  • Consistencia: {analysis['consistency']:.2f}")
            print(f"  • Mejor capital: ${analysis['best_capital']:,.0f}")
        
        # Recomendaciones
        print(f"\n🎯 RECOMENDACIONES POR CAPITAL:")
        print("-" * 50)
        for capital, rec in results['optimization_recommendations']['by_capital_level'].items():
            print(f"\n💰 ${capital:,.0f} ({rec['strategy_used']}):")
            print(f"  📊 {rec['recommendation']}")
            print(f"  📈 Score: {rec['score']:.1f}/100")
            if rec['suggested_improvements']:
                print(f"  🔧 Mejoras sugeridas:")
                for improvement in rec['suggested_improvements']:
                    print(f"     • {improvement}")
        
        # Insights generales
        print(f"\n💡 INSIGHTS GENERALES:")
        print("-" * 30)
        for insight in results['optimization_recommendations']['general_insights']:
            print(f"  • {insight}")
        
    def save_results(self, results: Dict) -> str:
        """
        Guardar resultados completos
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'capital_strategy_evaluation_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📁 Resultados guardados en: {filename}")
        return filename
        
    def run_complete_evaluation(self) -> Dict:
        """
        Ejecutar evaluación completa
        """
        logger.info("🚀 Iniciando evaluación completa de estrategias por capital...")
        
        try:
            # 1. Ejecutar comparación de estrategias
            results = self.run_strategy_comparison()
            
            # 2. Crear análisis visual
            chart_file = self.create_visual_analysis(results)
            results['chart_file'] = chart_file
            
            # 3. Imprimir reporte
            self.print_comprehensive_report(results)
            
            # 4. Guardar resultados
            results_file = self.save_results(results)
            results['results_file'] = results_file
            
            logger.info("✅ Evaluación completa finalizada")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error en evaluación: {e}")
            return {}

def main():
    """Función principal"""
    print("🎯 Iniciando Evaluación de Estrategias por Capital SICAR...")
    
    try:
        evaluator = CapitalStrategyEvaluator()
        results = evaluator.run_complete_evaluation()
        
        if results:
            print("\n✅ Evaluación completada exitosamente")
            print(f"📊 Gráfico guardado: {results.get('chart_file', 'N/A')}")
            print(f"📁 Resultados guardados: {results.get('results_file', 'N/A')}")
            return evaluator
        else:
            print("\n❌ Error en la evaluación")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        return None

if __name__ == "__main__":
    strategy_evaluator = main()