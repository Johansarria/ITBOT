#!/usr/bin/env python3
"""
Análisis Detallado - Backtest Fase 1 SICAR
==========================================

Análisis profundo de los resultados del backtest completo de Fase 1
con insights, métricas avanzadas y recomendaciones estratégicas.

Año: 2025
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class Phase1DetailedAnalysis:
    """
    Análisis detallado de resultados del backtest Fase 1
    """
    
    def __init__(self, report_file: str):
        """
        Inicializar análisis con archivo de reporte
        
        Args:
            report_file: Ruta al archivo JSON del reporte
        """
        self.report_file = report_file
        self.report = self.load_report()
        
        print("📊 Análisis Detallado Fase 1 - SICAR")
        print("="*50)
        
    def load_report(self) -> Dict:
        """Cargar reporte desde archivo JSON"""
        try:
            with open(self.report_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error cargando reporte: {e}")
            return {}
            
    def analyze_trading_performance(self) -> Dict:
        """
        Análisis detallado del rendimiento de trading
        
        Returns:
            Análisis de rendimiento
        """
        print("\n🎯 ANÁLISIS DE RENDIMIENTO DE TRADING")
        print("-" * 40)
        
        analysis = {}
        
        # Análisis por clase de activo
        for asset_class, data in self.report.get('asset_class_results', {}).items():
            performance = data['performance']
            trade_history = performance.get('trade_history', [])
            
            print(f"\n📈 {asset_class.upper()}:")
            print(f"   • Capital inicial: ${performance['initial_capital']:,.2f}")
            print(f"   • Capital final: ${performance['final_capital']:,.2f}")
            print(f"   • Retorno total: ${performance['total_return']:,.2f}")
            print(f"   • Retorno %: {performance['total_return_pct']:+.2f}%")
            print(f"   • Total trades: {performance['total_trades']}")
            print(f"   • Trades ganadores: {performance['winning_trades']}")
            print(f"   • Win Rate: {performance['win_rate']:.1f}%")
            
            # Análisis de trades individuales
            if trade_history:
                winning_trades = [t for t in trade_history if t.get('pnl', 0) > 0]
                losing_trades = [t for t in trade_history if t.get('pnl', 0) < 0]
                
                print(f"\n   📊 Análisis de Trades:")
                print(f"      • Trades ganadores: {len(winning_trades)}")
                print(f"      • Trades perdedores: {len(losing_trades)}")
                
                if winning_trades:
                    avg_win = np.mean([t['pnl'] for t in winning_trades])
                    max_win = max([t['pnl'] for t in winning_trades])
                    print(f"      • Ganancia promedio: ${avg_win:.2f}")
                    print(f"      • Máxima ganancia: ${max_win:.2f}")
                
                if losing_trades:
                    avg_loss = np.mean([t['pnl'] for t in losing_trades])
                    max_loss = min([t['pnl'] for t in losing_trades])
                    print(f"      • Pérdida promedio: ${avg_loss:.2f}")
                    print(f"      • Máxima pérdida: ${max_loss:.2f}")
                
                # Análisis por símbolo
                symbol_performance = {}
                for trade in trade_history:
                    symbol = trade['symbol']
                    if symbol not in symbol_performance:
                        symbol_performance[symbol] = {'trades': 0, 'pnl': 0, 'returns': []}
                    
                    symbol_performance[symbol]['trades'] += 1
                    symbol_performance[symbol]['pnl'] += trade.get('pnl', 0)
                    symbol_performance[symbol]['returns'].append(trade.get('return_pct', 0))
                
                print(f"\n   🏷️  Rendimiento por Símbolo:")
                for symbol, perf in symbol_performance.items():
                    avg_return = np.mean(perf['returns']) if perf['returns'] else 0
                    print(f"      • {symbol}: {perf['trades']} trades, "
                          f"PnL: ${perf['pnl']:+.2f}, "
                          f"Retorno avg: {avg_return:+.2f}%")
            
            analysis[asset_class] = {
                'performance': performance,
                'trade_analysis': self._analyze_trades(trade_history),
                'symbol_performance': symbol_performance if trade_history else {}
            }
        
        return analysis
        
    def _analyze_trades(self, trade_history: List[Dict]) -> Dict:
        """Análisis detallado de trades"""
        if not trade_history:
            return {}
        
        returns = [t.get('return_pct', 0) for t in trade_history]
        pnls = [t.get('pnl', 0) for t in trade_history]
        
        return {
            'total_trades': len(trade_history),
            'avg_return': np.mean(returns),
            'std_return': np.std(returns),
            'max_return': max(returns),
            'min_return': min(returns),
            'avg_pnl': np.mean(pnls),
            'total_pnl': sum(pnls),
            'positive_trades': len([p for p in pnls if p > 0]),
            'negative_trades': len([p for p in pnls if p < 0])
        }
        
    def analyze_risk_metrics(self) -> Dict:
        """
        Análisis de métricas de riesgo
        
        Returns:
            Métricas de riesgo
        """
        print("\n⚠️  ANÁLISIS DE RIESGO")
        print("-" * 25)
        
        risk_analysis = {}
        
        # Métricas avanzadas del reporte
        advanced_metrics = self.report.get('advanced_metrics', {})
        
        for category, metrics in advanced_metrics.items():
            if category == 'by_asset_class':
                for asset_class, class_metrics in metrics.items():
                    print(f"\n📊 {asset_class.upper()}:")
                    print(f"   • Sharpe Ratio: {class_metrics.get('sharpe_ratio', 0):.3f}")
                    print(f"   • Profit Factor: {class_metrics.get('profit_factor', 0):.3f}")
                    print(f"   • Max Drawdown: {class_metrics.get('max_drawdown', 0):.2f}%")
                    
                    # Interpretación del Sharpe Ratio
                    sharpe = class_metrics.get('sharpe_ratio', 0)
                    if sharpe > 1:
                        sharpe_rating = "Excelente"
                    elif sharpe > 0.5:
                        sharpe_rating = "Bueno"
                    elif sharpe > 0:
                        sharpe_rating = "Aceptable"
                    else:
                        sharpe_rating = "Pobre"
                    
                    print(f"   • Calificación Sharpe: {sharpe_rating}")
                    
                    # Interpretación del Profit Factor
                    pf = class_metrics.get('profit_factor', 0)
                    if pf > 2:
                        pf_rating = "Excelente"
                    elif pf > 1.5:
                        pf_rating = "Bueno"
                    elif pf > 1:
                        pf_rating = "Rentable"
                    else:
                        pf_rating = "No rentable"
                    
                    print(f"   • Calificación Profit Factor: {pf_rating}")
                    
            elif category == 'combined_portfolio':
                print(f"\n🌐 PORTFOLIO COMBINADO:")
                print(f"   • Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.3f}")
                print(f"   • Profit Factor: {metrics.get('profit_factor', 0):.3f}")
                print(f"   • Max Drawdown: {metrics.get('max_drawdown', 0):.2f}%")
        
        return risk_analysis
        
    def analyze_correlation_insights(self) -> Dict:
        """
        Análisis de insights de correlación
        
        Returns:
            Insights de correlación
        """
        print("\n🔗 ANÁLISIS DE CORRELACIONES")
        print("-" * 30)
        
        correlation_analysis = self.report.get('correlation_analysis', {})
        
        if not correlation_analysis:
            print("⚠️ No hay datos de correlación disponibles")
            return {}
        
        # Análisis por clase de activo
        asset_class_analysis = correlation_analysis.get('asset_class_analysis', {})
        
        for asset_class, data in asset_class_analysis.items():
            print(f"\n📊 {asset_class.upper()}:")
            print(f"   • Símbolos analizados: {data.get('count', 0)}")
            print(f"   • Correlación promedio: {data.get('avg_correlation', 0):.3f}")
            print(f"   • Correlación máxima: {data.get('max_correlation', 0):.3f}")
            print(f"   • Correlación mínima: {data.get('min_correlation', 0):.3f}")
            
            # Interpretación de correlación
            avg_corr = data.get('avg_correlation', 0)
            if avg_corr > 0.8:
                corr_interpretation = "Muy alta correlación - Riesgo de concentración"
            elif avg_corr > 0.6:
                corr_interpretation = "Alta correlación - Diversificación limitada"
            elif avg_corr > 0.4:
                corr_interpretation = "Correlación moderada - Diversificación aceptable"
            elif avg_corr > 0.2:
                corr_interpretation = "Baja correlación - Buena diversificación"
            else:
                corr_interpretation = "Correlación muy baja - Excelente diversificación"
            
            print(f"   • Interpretación: {corr_interpretation}")
        
        # Sugerencias de portfolio
        portfolio_suggestions = correlation_analysis.get('portfolio_suggestions', {})
        if portfolio_suggestions:
            print(f"\n💡 SUGERENCIAS DE PORTFOLIO:")
            print(f"   • Activos sugeridos: {portfolio_suggestions.get('asset_count', 0)}")
            print(f"   • Score de diversificación: {portfolio_suggestions.get('diversification_score', 0):.3f}")
            
            div_score = portfolio_suggestions.get('diversification_score', 0)
            if div_score > 0.7:
                div_rating = "Excelente diversificación"
            elif div_score > 0.5:
                div_rating = "Buena diversificación"
            elif div_score > 0.3:
                div_rating = "Diversificación moderada"
            else:
                div_rating = "Diversificación insuficiente"
            
            print(f"   • Calificación: {div_rating}")
        
        return correlation_analysis
        
    def generate_strategic_recommendations(self) -> List[str]:
        """
        Generar recomendaciones estratégicas basadas en el análisis
        
        Returns:
            Lista de recomendaciones estratégicas
        """
        print("\n💡 RECOMENDACIONES ESTRATÉGICAS")
        print("-" * 35)
        
        recommendations = []
        
        # Análisis de rendimiento general
        total_return = 0
        total_trades = 0
        
        for asset_class, data in self.report.get('asset_class_results', {}).items():
            performance = data['performance']
            total_return += performance.get('total_return_pct', 0)
            total_trades += performance.get('total_trades', 0)
        
        # Recomendaciones basadas en rendimiento
        if total_return < -1:
            recommendations.append("🔴 CRÍTICO: Revisar estrategia de trading - pérdidas significativas")
            recommendations.append("📊 Considerar ajustar parámetros de entrada y salida")
            recommendations.append("⏰ Evaluar timeframes alternativos para señales")
        elif total_return < 0:
            recommendations.append("🟡 ATENCIÓN: Optimizar estrategia - rendimiento negativo")
            recommendations.append("🎯 Mejorar gestión de riesgo por posición")
        else:
            recommendations.append("🟢 Estrategia rentable - continuar optimización")
        
        # Recomendaciones basadas en win rate
        avg_win_rate = 0
        asset_count = 0
        
        for asset_class, data in self.report.get('asset_class_results', {}).items():
            performance = data['performance']
            avg_win_rate += performance.get('win_rate', 0)
            asset_count += 1
        
        if asset_count > 0:
            avg_win_rate /= asset_count
            
            if avg_win_rate < 30:
                recommendations.append("📈 URGENTE: Win rate muy bajo - revisar señales de entrada")
                recommendations.append("🔍 Implementar filtros adicionales para calidad de señales")
            elif avg_win_rate < 50:
                recommendations.append("⚡ Mejorar precisión de señales - win rate subóptimo")
        
        # Recomendaciones basadas en correlaciones
        correlation_analysis = self.report.get('correlation_analysis', {})
        if correlation_analysis:
            portfolio_suggestions = correlation_analysis.get('portfolio_suggestions', {})
            div_score = portfolio_suggestions.get('diversification_score', 0)
            
            if div_score < 0.3:
                recommendations.append("🌐 CRÍTICO: Diversificación insuficiente - alto riesgo de concentración")
                recommendations.append("🔄 Incorporar activos de diferentes clases con baja correlación")
            elif div_score < 0.5:
                recommendations.append("📊 Mejorar diversificación del portfolio")
        
        # Recomendaciones específicas por número de trades
        if total_trades < 5:
            recommendations.append("📊 Aumentar frecuencia de trading o ampliar universo de activos")
        elif total_trades > 50:
            recommendations.append("⚠️ Considerar reducir frecuencia - posible overtrading")
        
        # Recomendaciones técnicas
        recommendations.extend([
            "🔧 Implementar stop-loss dinámico basado en volatilidad",
            "📱 Desarrollar sistema de alertas en tiempo real",
            "🤖 Considerar machine learning para optimización de parámetros",
            "📊 Implementar backtesting walk-forward para validación robusta",
            "💰 Establecer límites de riesgo por sector/clase de activo"
        ])
        
        # Mostrar recomendaciones
        for i, rec in enumerate(recommendations, 1):
            print(f"{i:2d}. {rec}")
        
        return recommendations
        
    def calculate_performance_score(self) -> Dict:
        """
        Calcular score general de rendimiento
        
        Returns:
            Score de rendimiento
        """
        print("\n🏆 SCORE DE RENDIMIENTO GENERAL")
        print("-" * 35)
        
        scores = {}
        total_score = 0
        max_score = 0
        
        # Score de retorno (30% del total)
        return_score = 0
        for asset_class, data in self.report.get('asset_class_results', {}).items():
            return_pct = data['performance'].get('total_return_pct', 0)
            if return_pct > 5:
                return_score = 30
            elif return_pct > 2:
                return_score = 25
            elif return_pct > 0:
                return_score = 20
            elif return_pct > -2:
                return_score = 10
            else:
                return_score = 0
        
        scores['return'] = return_score
        total_score += return_score
        max_score += 30
        
        # Score de win rate (25% del total)
        win_rate_score = 0
        for asset_class, data in self.report.get('asset_class_results', {}).items():
            win_rate = data['performance'].get('win_rate', 0)
            if win_rate > 60:
                win_rate_score = 25
            elif win_rate > 50:
                win_rate_score = 20
            elif win_rate > 40:
                win_rate_score = 15
            elif win_rate > 30:
                win_rate_score = 10
            else:
                win_rate_score = 5
        
        scores['win_rate'] = win_rate_score
        total_score += win_rate_score
        max_score += 25
        
        # Score de diversificación (20% del total)
        div_score = 0
        correlation_analysis = self.report.get('correlation_analysis', {})
        if correlation_analysis:
            portfolio_suggestions = correlation_analysis.get('portfolio_suggestions', {})
            diversification = portfolio_suggestions.get('diversification_score', 0)
            
            if diversification > 0.7:
                div_score = 20
            elif diversification > 0.5:
                div_score = 15
            elif diversification > 0.3:
                div_score = 10
            else:
                div_score = 5
        
        scores['diversification'] = div_score
        total_score += div_score
        max_score += 20
        
        # Score de gestión de riesgo (25% del total)
        risk_score = 0
        advanced_metrics = self.report.get('advanced_metrics', {})
        
        for category, metrics in advanced_metrics.items():
            if 'sharpe_ratio' in metrics:
                sharpe = metrics.get('sharpe_ratio', 0)
                if sharpe > 1:
                    risk_score = 25
                elif sharpe > 0.5:
                    risk_score = 20
                elif sharpe > 0:
                    risk_score = 15
                else:
                    risk_score = 5
                break
        
        scores['risk_management'] = risk_score
        total_score += risk_score
        max_score += 25
        
        # Calcular score final
        final_score = (total_score / max_score) * 100 if max_score > 0 else 0
        
        print(f"📊 Desglose de Scores:")
        print(f"   • Retorno: {return_score}/30 pts")
        print(f"   • Win Rate: {win_rate_score}/25 pts")
        print(f"   • Diversificación: {div_score}/20 pts")
        print(f"   • Gestión de Riesgo: {risk_score}/25 pts")
        print(f"\n🏆 SCORE FINAL: {final_score:.1f}/100")
        
        # Calificación
        if final_score >= 80:
            grade = "A - Excelente"
        elif final_score >= 70:
            grade = "B - Bueno"
        elif final_score >= 60:
            grade = "C - Aceptable"
        elif final_score >= 50:
            grade = "D - Necesita mejoras"
        else:
            grade = "F - Requiere revisión completa"
        
        print(f"📈 CALIFICACIÓN: {grade}")
        
        return {
            'scores': scores,
            'total_score': total_score,
            'max_score': max_score,
            'final_score': final_score,
            'grade': grade
        }
        
    def run_complete_analysis(self) -> Dict:
        """
        Ejecutar análisis completo
        
        Returns:
            Análisis completo
        """
        print("🚀 Iniciando Análisis Detallado Completo...")
        
        # Ejecutar todos los análisis
        trading_analysis = self.analyze_trading_performance()
        risk_analysis = self.analyze_risk_metrics()
        correlation_insights = self.analyze_correlation_insights()
        recommendations = self.generate_strategic_recommendations()
        performance_score = self.calculate_performance_score()
        
        # Compilar análisis completo
        complete_analysis = {
            'timestamp': datetime.now().isoformat(),
            'original_report': self.report_file,
            'trading_analysis': trading_analysis,
            'risk_analysis': risk_analysis,
            'correlation_insights': correlation_insights,
            'strategic_recommendations': recommendations,
            'performance_score': performance_score,
            'summary': {
                'total_capital': self.report.get('initial_capital', 0),
                'asset_classes_tested': len(self.report.get('asset_class_results', {})),
                'total_symbols': self.report.get('summary', {}).get('total_symbols_tested', 0),
                'overall_performance': 'Negativo' if performance_score['final_score'] < 50 else 'Positivo'
            }
        }
        
        # Guardar análisis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        analysis_file = f"phase1_detailed_analysis_{timestamp}.json"
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(complete_analysis, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Análisis detallado guardado en: {analysis_file}")
        print("\n✅ Análisis Detallado Completo finalizado")
        
        return complete_analysis

def main():
    """Función principal"""
    # Buscar el archivo de reporte más reciente
    import glob
    import os
    
    report_files = glob.glob("phase1_complete_backtest_*.json")
    
    if not report_files:
        print("❌ No se encontraron archivos de reporte de Fase 1")
        return None
    
    # Usar el archivo más reciente
    latest_report = max(report_files, key=os.path.getctime)
    print(f"📄 Analizando reporte: {latest_report}")
    
    # Crear analizador
    analyzer = Phase1DetailedAnalysis(latest_report)
    
    # Ejecutar análisis completo
    analysis = analyzer.run_complete_analysis()
    
    return analyzer

if __name__ == "__main__":
    analyzer = main()