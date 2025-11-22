#!/usr/bin/env python3
"""
Sistema de Pruebas Multi-Capital SICAR
=====================================

Prueba el sistema SICAR con diferentes bases de capital entre 200 y 1000 USDT
para evaluar escalabilidad, rendimiento y comportamiento del sistema.

Año: 2025
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import warnings
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

from multi_asset_backtester import MultiAssetBacktester
from correlation_analyzer import CorrelationAnalyzer
from multi_asset_data_system import MultiAssetDataSystem

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiCapitalTester:
    """
    Sistema de pruebas con múltiples niveles de capital
    """
    
    def __init__(self):
        """
        Inicializar sistema de pruebas multi-capital
        """
        # Definir rangos de capital a probar
        self.capital_levels = [
            200, 300, 400, 500, 600, 700, 800, 900, 1000
        ]
        
        # Configuración de pruebas
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        
        # Inicializar componentes
        self.data_system = MultiAssetDataSystem()
        
        # Resultados
        self.results_by_capital = {}
        self.comparative_analysis = {}
        
        logger.info("🚀 Sistema de Pruebas Multi-Capital inicializado")
        logger.info(f"💰 Niveles de capital: {self.capital_levels}")
        logger.info(f"📊 Símbolos de prueba: {self.test_symbols}")
        
    def run_single_capital_test(self, capital: float) -> Dict:
        """
        Ejecutar prueba con un nivel específico de capital
        
        Args:
            capital: Nivel de capital a probar
            
        Returns:
            Resultados del backtest
        """
        logger.info(f"\n💰 Probando con capital: ${capital:,.0f} USDT")
        
        try:
            # Crear backtester con capital específico
            backtester = MultiAssetBacktester(initial_capital=capital)
            
            # Ejecutar backtest
            results = backtester.run_backtest(self.test_symbols)
            
            if results:
                # Calcular métricas adicionales específicas para el capital
                additional_metrics = self._calculate_capital_specific_metrics(results, capital)
                results.update(additional_metrics)
                
                logger.info(f"✅ Capital ${capital:,.0f}: Retorno {results.get('total_return_pct', 0):+.2f}%")
                return results
            else:
                logger.warning(f"⚠️ No se obtuvieron resultados para capital ${capital:,.0f}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error con capital ${capital:,.0f}: {e}")
            return {}
            
    def _calculate_capital_specific_metrics(self, results: Dict, capital: float) -> Dict:
        """
        Calcular métricas específicas para el nivel de capital
        
        Args:
            results: Resultados del backtest
            capital: Nivel de capital
            
        Returns:
            Métricas adicionales
        """
        additional_metrics = {
            'capital_level': capital,
            'capital_efficiency': 0,
            'risk_adjusted_return': 0,
            'position_size_avg': 0,
            'trades_per_1000_usdt': 0
        }
        
        try:
            # Eficiencia de capital (retorno absoluto / capital)
            total_return = results.get('total_return', 0)
            additional_metrics['capital_efficiency'] = (total_return / capital) * 100 if capital > 0 else 0
            
            # Retorno ajustado por riesgo (simplificado)
            return_pct = results.get('total_return_pct', 0)
            total_trades = results.get('total_trades', 0)
            if total_trades > 0:
                risk_factor = min(1.0, total_trades / 10)  # Factor de riesgo basado en número de trades
                additional_metrics['risk_adjusted_return'] = return_pct * risk_factor
            
            # Tamaño promedio de posición
            trade_history = results.get('trade_history', [])
            if trade_history:
                position_sizes = [trade.get('position_size', 0) for trade in trade_history]
                additional_metrics['position_size_avg'] = np.mean(position_sizes)
                
                # Trades por 1000 USDT (normalización)
                additional_metrics['trades_per_1000_usdt'] = (total_trades / capital) * 1000
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculando métricas adicionales: {e}")
        
        return additional_metrics
        
    def run_all_capital_tests(self) -> Dict:
        """
        Ejecutar pruebas con todos los niveles de capital
        
        Returns:
            Resultados de todas las pruebas
        """
        logger.info("🔄 Ejecutando pruebas con todos los niveles de capital...")
        
        for capital in self.capital_levels:
            results = self.run_single_capital_test(capital)
            if results:
                self.results_by_capital[capital] = results
        
        logger.info(f"✅ Completadas {len(self.results_by_capital)} pruebas de capital")
        return self.results_by_capital
        
    def analyze_scalability(self) -> Dict:
        """
        Analizar escalabilidad del sistema
        
        Returns:
            Análisis de escalabilidad
        """
        logger.info("\n📊 Analizando escalabilidad del sistema...")
        
        if not self.results_by_capital:
            logger.warning("⚠️ No hay resultados para analizar")
            return {}
        
        scalability_analysis = {
            'capital_levels': list(self.results_by_capital.keys()),
            'performance_metrics': {},
            'scalability_insights': [],
            'optimal_capital_range': {}
        }
        
        # Extraer métricas por nivel de capital
        metrics_data = {
            'capital': [],
            'return_pct': [],
            'return_absolute': [],
            'total_trades': [],
            'win_rate': [],
            'capital_efficiency': [],
            'risk_adjusted_return': [],
            'position_size_avg': [],
            'trades_per_1000_usdt': []
        }
        
        for capital, results in self.results_by_capital.items():
            metrics_data['capital'].append(capital)
            metrics_data['return_pct'].append(results.get('total_return_pct', 0))
            metrics_data['return_absolute'].append(results.get('total_return', 0))
            metrics_data['total_trades'].append(results.get('total_trades', 0))
            metrics_data['win_rate'].append(results.get('win_rate', 0))
            metrics_data['capital_efficiency'].append(results.get('capital_efficiency', 0))
            metrics_data['risk_adjusted_return'].append(results.get('risk_adjusted_return', 0))
            metrics_data['position_size_avg'].append(results.get('position_size_avg', 0))
            metrics_data['trades_per_1000_usdt'].append(results.get('trades_per_1000_usdt', 0))
        
        # Crear DataFrame para análisis
        df = pd.DataFrame(metrics_data)
        
        # Calcular correlaciones con el capital
        correlations = {}
        for metric in ['return_pct', 'return_absolute', 'total_trades', 'win_rate', 
                      'capital_efficiency', 'risk_adjusted_return']:
            if metric in df.columns:
                corr = df['capital'].corr(df[metric])
                correlations[metric] = corr
        
        scalability_analysis['performance_metrics'] = metrics_data
        scalability_analysis['correlations_with_capital'] = correlations
        
        # Generar insights de escalabilidad
        insights = []
        
        # Análisis de retorno porcentual vs capital
        return_corr = correlations.get('return_pct', 0)
        if return_corr > 0.3:
            insights.append("✅ El retorno porcentual mejora con mayor capital")
        elif return_corr < -0.3:
            insights.append("⚠️ El retorno porcentual empeora con mayor capital")
        else:
            insights.append("📊 El retorno porcentual es independiente del capital")
        
        # Análisis de eficiencia de capital
        efficiency_corr = correlations.get('capital_efficiency', 0)
        if efficiency_corr > 0.3:
            insights.append("📈 Mayor capital es más eficiente")
        elif efficiency_corr < -0.3:
            insights.append("📉 Menor capital es más eficiente")
        else:
            insights.append("⚖️ Eficiencia constante independiente del capital")
        
        # Análisis de número de trades
        trades_corr = correlations.get('total_trades', 0)
        if trades_corr > 0.5:
            insights.append("🔄 Mayor capital genera más oportunidades de trading")
        elif trades_corr < -0.5:
            insights.append("🎯 Menor capital es más selectivo en trades")
        
        # Encontrar rango óptimo de capital
        best_return_idx = df['return_pct'].idxmax()
        best_efficiency_idx = df['capital_efficiency'].idxmax()
        best_risk_adjusted_idx = df['risk_adjusted_return'].idxmax()
        
        optimal_range = {
            'best_return_capital': df.loc[best_return_idx, 'capital'],
            'best_efficiency_capital': df.loc[best_efficiency_idx, 'capital'],
            'best_risk_adjusted_capital': df.loc[best_risk_adjusted_idx, 'capital'],
            'recommended_range': self._calculate_recommended_range(df)
        }
        
        scalability_analysis['scalability_insights'] = insights
        scalability_analysis['optimal_capital_range'] = optimal_range
        
        # Mostrar resultados
        self._print_scalability_results(scalability_analysis)
        
        return scalability_analysis
        
    def _calculate_recommended_range(self, df: pd.DataFrame) -> Dict:
        """Calcular rango recomendado de capital"""
        try:
            # Encontrar el rango donde el rendimiento es más consistente
            df_sorted = df.sort_values('capital')
            
            # Calcular métricas combinadas
            df_sorted['combined_score'] = (
                df_sorted['return_pct'].rank(pct=True) * 0.4 +
                df_sorted['capital_efficiency'].rank(pct=True) * 0.3 +
                df_sorted['risk_adjusted_return'].rank(pct=True) * 0.3
            )
            
            # Encontrar el mejor rango
            best_idx = df_sorted['combined_score'].idxmax()
            best_capital = df_sorted.loc[best_idx, 'capital']
            
            # Definir rango alrededor del mejor capital
            range_size = 200  # ±200 USDT
            min_capital = max(200, best_capital - range_size)
            max_capital = min(1000, best_capital + range_size)
            
            return {
                'min_recommended': min_capital,
                'max_recommended': max_capital,
                'optimal_capital': best_capital,
                'combined_score': df_sorted.loc[best_idx, 'combined_score']
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error calculando rango recomendado: {e}")
            return {'min_recommended': 400, 'max_recommended': 600, 'optimal_capital': 500}
            
    def _print_scalability_results(self, analysis: Dict):
        """Imprimir resultados de escalabilidad"""
        print("\n" + "="*60)
        print("📊 ANÁLISIS DE ESCALABILIDAD - SISTEMA SICAR")
        print("="*60)
        
        # Mostrar métricas por capital
        print(f"\n💰 RENDIMIENTO POR NIVEL DE CAPITAL:")
        print("-" * 50)
        
        metrics = analysis['performance_metrics']
        for i, capital in enumerate(metrics['capital']):
            return_pct = metrics['return_pct'][i]
            return_abs = metrics['return_absolute'][i]
            trades = metrics['total_trades'][i]
            win_rate = metrics['win_rate'][i]
            efficiency = metrics['capital_efficiency'][i]
            
            print(f"${capital:4.0f} USDT: {return_pct:+6.2f}% | "
                  f"${return_abs:+7.2f} | {trades:2.0f} trades | "
                  f"{win_rate:4.1f}% WR | Eff: {efficiency:5.2f}%")
        
        # Mostrar correlaciones
        print(f"\n🔗 CORRELACIONES CON CAPITAL:")
        print("-" * 35)
        correlations = analysis['correlations_with_capital']
        for metric, corr in correlations.items():
            direction = "📈" if corr > 0.3 else "📉" if corr < -0.3 else "➡️"
            print(f"{direction} {metric:20s}: {corr:+6.3f}")
        
        # Mostrar insights
        print(f"\n💡 INSIGHTS DE ESCALABILIDAD:")
        print("-" * 35)
        for i, insight in enumerate(analysis['scalability_insights'], 1):
            print(f"{i}. {insight}")
        
        # Mostrar rango óptimo
        optimal = analysis['optimal_capital_range']
        print(f"\n🎯 RANGO ÓPTIMO DE CAPITAL:")
        print("-" * 30)
        print(f"• Mejor retorno: ${optimal['best_return_capital']:,.0f} USDT")
        print(f"• Mejor eficiencia: ${optimal['best_efficiency_capital']:,.0f} USDT")
        print(f"• Mejor riesgo-retorno: ${optimal['best_risk_adjusted_capital']:,.0f} USDT")
        
        recommended = optimal['recommended_range']
        print(f"\n🏆 RECOMENDACIÓN FINAL:")
        print(f"   Capital óptimo: ${recommended['optimal_capital']:,.0f} USDT")
        print(f"   Rango recomendado: ${recommended['min_recommended']:,.0f} - ${recommended['max_recommended']:,.0f} USDT")
        
    def generate_visual_analysis(self) -> str:
        """
        Generar análisis visual de los resultados
        
        Returns:
            Ruta del archivo de gráficos generado
        """
        logger.info("📈 Generando análisis visual...")
        
        if not self.results_by_capital:
            logger.warning("⚠️ No hay datos para generar gráficos")
            return ""
        
        try:
            # Preparar datos
            metrics = self.comparative_analysis.get('performance_metrics', {})
            if not metrics:
                return ""
            
            df = pd.DataFrame(metrics)
            
            # Crear figura con subplots
            fig, axes = plt.subplots(2, 3, figsize=(18, 12))
            fig.suptitle('Análisis de Escalabilidad SICAR - Múltiples Niveles de Capital', fontsize=16)
            
            # Gráfico 1: Retorno % vs Capital
            axes[0, 0].plot(df['capital'], df['return_pct'], 'bo-', linewidth=2, markersize=8)
            axes[0, 0].set_title('Retorno % vs Capital')
            axes[0, 0].set_xlabel('Capital (USDT)')
            axes[0, 0].set_ylabel('Retorno (%)')
            axes[0, 0].grid(True, alpha=0.3)
            
            # Gráfico 2: Retorno Absoluto vs Capital
            axes[0, 1].plot(df['capital'], df['return_absolute'], 'go-', linewidth=2, markersize=8)
            axes[0, 1].set_title('Retorno Absoluto vs Capital')
            axes[0, 1].set_xlabel('Capital (USDT)')
            axes[0, 1].set_ylabel('Retorno (USDT)')
            axes[0, 1].grid(True, alpha=0.3)
            
            # Gráfico 3: Número de Trades vs Capital
            axes[0, 2].plot(df['capital'], df['total_trades'], 'ro-', linewidth=2, markersize=8)
            axes[0, 2].set_title('Número de Trades vs Capital')
            axes[0, 2].set_xlabel('Capital (USDT)')
            axes[0, 2].set_ylabel('Total Trades')
            axes[0, 2].grid(True, alpha=0.3)
            
            # Gráfico 4: Win Rate vs Capital
            axes[1, 0].plot(df['capital'], df['win_rate'], 'mo-', linewidth=2, markersize=8)
            axes[1, 0].set_title('Win Rate vs Capital')
            axes[1, 0].set_xlabel('Capital (USDT)')
            axes[1, 0].set_ylabel('Win Rate (%)')
            axes[1, 0].grid(True, alpha=0.3)
            
            # Gráfico 5: Eficiencia de Capital
            axes[1, 1].plot(df['capital'], df['capital_efficiency'], 'co-', linewidth=2, markersize=8)
            axes[1, 1].set_title('Eficiencia de Capital')
            axes[1, 1].set_xlabel('Capital (USDT)')
            axes[1, 1].set_ylabel('Eficiencia (%)')
            axes[1, 1].grid(True, alpha=0.3)
            
            # Gráfico 6: Trades por 1000 USDT
            axes[1, 2].plot(df['capital'], df['trades_per_1000_usdt'], 'yo-', linewidth=2, markersize=8)
            axes[1, 2].set_title('Trades por 1000 USDT')
            axes[1, 2].set_xlabel('Capital (USDT)')
            axes[1, 2].set_ylabel('Trades/1000 USDT')
            axes[1, 2].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Guardar gráfico
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_file = f"multi_capital_analysis_{timestamp}.png"
            plt.savefig(chart_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"📊 Gráficos guardados en: {chart_file}")
            return chart_file
            
        except Exception as e:
            logger.error(f"❌ Error generando gráficos: {e}")
            return ""
            
    def generate_comprehensive_report(self) -> Dict:
        """
        Generar reporte comprensivo de todas las pruebas
        
        Returns:
            Reporte completo
        """
        logger.info("📋 Generando reporte comprensivo...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_configuration': {
                'capital_levels': self.capital_levels,
                'test_symbols': self.test_symbols,
                'total_tests': len(self.results_by_capital)
            },
            'results_by_capital': self.results_by_capital,
            'scalability_analysis': self.comparative_analysis,
            'summary': self._generate_summary(),
            'recommendations': self._generate_recommendations()
        }
        
        return report
        
    def _generate_summary(self) -> Dict:
        """Generar resumen ejecutivo"""
        if not self.results_by_capital:
            return {}
        
        # Calcular estadísticas generales
        returns = [r.get('total_return_pct', 0) for r in self.results_by_capital.values()]
        trades = [r.get('total_trades', 0) for r in self.results_by_capital.values()]
        win_rates = [r.get('win_rate', 0) for r in self.results_by_capital.values()]
        
        return {
            'total_capital_levels_tested': len(self.capital_levels),
            'capital_range': f"${min(self.capital_levels):,.0f} - ${max(self.capital_levels):,.0f} USDT",
            'avg_return_pct': np.mean(returns),
            'best_return_pct': max(returns),
            'worst_return_pct': min(returns),
            'avg_trades': np.mean(trades),
            'avg_win_rate': np.mean(win_rates),
            'successful_tests': len([r for r in returns if r > 0]),
            'total_tests': len(returns)
        }
        
    def _generate_recommendations(self) -> List[str]:
        """Generar recomendaciones basadas en los resultados"""
        recommendations = []
        
        if not self.results_by_capital:
            return ["No hay datos suficientes para generar recomendaciones"]
        
        # Análisis de rendimiento general
        returns = [r.get('total_return_pct', 0) for r in self.results_by_capital.values()]
        avg_return = np.mean(returns)
        
        if avg_return > 0:
            recommendations.append("✅ El sistema muestra rentabilidad promedio positiva")
        else:
            recommendations.append("⚠️ El sistema requiere optimización - rentabilidad promedio negativa")
        
        # Recomendaciones específicas de capital
        if hasattr(self, 'comparative_analysis') and self.comparative_analysis:
            optimal = self.comparative_analysis.get('optimal_capital_range', {})
            if optimal:
                recommended = optimal.get('recommended_range', {})
                if recommended:
                    min_cap = recommended.get('min_recommended', 400)
                    max_cap = recommended.get('max_recommended', 600)
                    recommendations.append(f"💰 Rango de capital recomendado: ${min_cap:,.0f} - ${max_cap:,.0f} USDT")
        
        # Recomendaciones de escalabilidad
        recommendations.extend([
            "📊 Monitorear rendimiento con capital real antes de escalar",
            "🔄 Considerar ajustar tamaños de posición según capital disponible",
            "⚖️ Implementar gestión de riesgo proporcional al capital",
            "📈 Evaluar diferentes estrategias para diferentes niveles de capital"
        ])
        
        return recommendations
        
    def save_report(self, report: Dict, filename: str = None) -> str:
        """Guardar reporte en archivo"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_capital_test_report_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Reporte guardado en: {filename}")
        return filename
        
    def run_complete_multi_capital_test(self) -> Dict:
        """
        Ejecutar prueba completa con múltiples niveles de capital
        
        Returns:
            Reporte completo de resultados
        """
        logger.info("🚀 Iniciando prueba completa multi-capital...")
        
        try:
            # 1. Ejecutar pruebas con todos los niveles de capital
            self.run_all_capital_tests()
            
            # 2. Analizar escalabilidad
            self.comparative_analysis = self.analyze_scalability()
            
            # 3. Generar análisis visual
            chart_file = self.generate_visual_analysis()
            
            # 4. Generar reporte comprensivo
            complete_report = self.generate_comprehensive_report()
            
            # 5. Guardar reporte
            report_file = self.save_report(complete_report)
            
            logger.info("✅ Prueba completa multi-capital finalizada exitosamente")
            
            return complete_report
            
        except Exception as e:
            logger.error(f"❌ Error en prueba multi-capital: {e}")
            return {}

def main():
    """Función principal"""
    print("🚀 Iniciando Sistema de Pruebas Multi-Capital SICAR...")
    print("💰 Probando con bases de capital entre 200 y 1000 USDT")
    
    try:
        # Inicializar sistema de pruebas
        tester = MultiCapitalTester()
        
        # Ejecutar prueba completa
        results = tester.run_complete_multi_capital_test()
        
        if results:
            print("\n✅ Pruebas multi-capital completadas exitosamente")
            return tester
        else:
            print("\n❌ Error en las pruebas multi-capital")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        return None

if __name__ == "__main__":
    tester_system = main()