#!/usr/bin/env python3
"""
Backtest Completo Fase 1 - Sistema Multi-Asset SICAR
====================================================

Ejecuta un backtest completo de la Fase 1 utilizando:
- Sistema multi-asset integrado
- Todos los símbolos validados disponibles
- Análisis comparativo entre clases de activos
- Métricas avanzadas de rendimiento
- Correlaciones y diversificación
- Reporte completo con visualizaciones

Año: 2025
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import warnings
warnings.filterwarnings('ignore')

from multi_asset_backtester import MultiAssetBacktester
from correlation_analyzer import CorrelationAnalyzer
from multi_asset_data_system import MultiAssetDataSystem

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Phase1CompleteBacktest:
    """
    Backtest completo de Fase 1 con sistema multi-asset
    """
    
    def __init__(self, initial_capital: float = 50000):
        """
        Inicializar backtest completo Fase 1
        
        Args:
            initial_capital: Capital inicial para el backtest
        """
        self.initial_capital = initial_capital
        
        # Inicializar componentes
        self.data_system = MultiAssetDataSystem()
        self.backtester = MultiAssetBacktester(initial_capital)
        self.correlation_analyzer = CorrelationAnalyzer()
        
        # Resultados
        self.results = {}
        self.asset_class_results = {}
        self.correlation_analysis = {}
        
        logger.info("🚀 Backtest Completo Fase 1 inicializado")
        logger.info(f"💰 Capital inicial: ${initial_capital:,.2f}")
        
    def get_all_available_symbols(self) -> Dict[str, List[str]]:
        """
        Obtener todos los símbolos disponibles por clase de activo
        
        Returns:
            Diccionario con símbolos por clase de activo
        """
        logger.info("📊 Obteniendo todos los símbolos disponibles...")
        
        available_symbols = {}
        
        # Obtener símbolos validados por clase de activo
        for asset_class in ['cryptocurrencies', 'forex', 'indices', 'commodities']:
            symbols = self.data_system.get_validated_symbols(asset_class)
            if symbols:
                available_symbols[asset_class] = symbols
                logger.info(f"✅ {asset_class}: {len(symbols)} símbolos validados")
            else:
                logger.warning(f"⚠️ {asset_class}: No hay símbolos validados")
        
        # Si no hay símbolos validados, usar configuración completa
        if not available_symbols:
            logger.info("📋 Usando configuración completa de símbolos...")
            config = self.data_system.config
            
            for asset_class, instruments in config.get('instruments', {}).items():
                symbols = [instr['symbol'] for instr in instruments]
                available_symbols[asset_class] = symbols
                logger.info(f"📊 {asset_class}: {len(symbols)} símbolos configurados")
        
        total_symbols = sum(len(symbols) for symbols in available_symbols.values())
        logger.info(f"🎯 Total símbolos disponibles: {total_symbols}")
        
        return available_symbols
        
    def run_individual_asset_backtests(self, available_symbols: Dict[str, List[str]]) -> Dict:
        """
        Ejecutar backtests individuales por clase de activo
        
        Args:
            available_symbols: Símbolos disponibles por clase de activo
            
        Returns:
            Resultados por clase de activo
        """
        logger.info("🔄 Ejecutando backtests individuales por clase de activo...")
        
        asset_class_results = {}
        
        for asset_class, symbols in available_symbols.items():
            if not symbols:
                continue
                
            logger.info(f"\n📈 Backtesting {asset_class.upper()}...")
            logger.info(f"   Símbolos: {symbols}")
            
            # Crear backtester específico para esta clase
            class_backtester = MultiAssetBacktester(
                initial_capital=self.initial_capital / len(available_symbols)
            )
            
            # Ejecutar backtest
            try:
                results = class_backtester.run_backtest(symbols)
                
                if results:
                    asset_class_results[asset_class] = {
                        'symbols': symbols,
                        'results': results,
                        'backtester': class_backtester
                    }
                    
                    # Mostrar resultados resumidos
                    logger.info(f"✅ {asset_class} completado:")
                    logger.info(f"   • Retorno: {results.get('total_return_pct', 0):.2f}%")
                    logger.info(f"   • Trades: {results.get('total_trades', 0)}")
                    logger.info(f"   • Win Rate: {results.get('win_rate', 0):.1f}%")
                else:
                    logger.warning(f"⚠️ No se obtuvieron resultados para {asset_class}")
                    
            except Exception as e:
                logger.error(f"❌ Error en backtest de {asset_class}: {e}")
        
        return asset_class_results
        
    def run_combined_portfolio_backtest(self, available_symbols: Dict[str, List[str]]) -> Dict:
        """
        Ejecutar backtest con portfolio combinado multi-asset
        
        Args:
            available_symbols: Símbolos disponibles por clase de activo
            
        Returns:
            Resultados del portfolio combinado
        """
        logger.info("\n🌐 Ejecutando backtest de portfolio combinado multi-asset...")
        
        # Seleccionar mejores símbolos de cada clase (máximo 2-3 por clase)
        selected_symbols = []
        
        for asset_class, symbols in available_symbols.items():
            # Limitar símbolos por clase para evitar sobrecarga
            max_symbols_per_class = min(3, len(symbols))
            class_symbols = symbols[:max_symbols_per_class]
            selected_symbols.extend(class_symbols)
            
            logger.info(f"📊 {asset_class}: {class_symbols}")
        
        logger.info(f"🎯 Portfolio combinado: {len(selected_symbols)} símbolos")
        
        # Ejecutar backtest combinado
        try:
            combined_results = self.backtester.run_backtest(selected_symbols)
            
            if combined_results:
                logger.info("✅ Backtest combinado completado:")
                logger.info(f"   • Retorno total: {combined_results.get('total_return_pct', 0):.2f}%")
                logger.info(f"   • Total trades: {combined_results.get('total_trades', 0)}")
                logger.info(f"   • Win Rate: {combined_results.get('win_rate', 0):.1f}%")
                
                return {
                    'selected_symbols': selected_symbols,
                    'results': combined_results,
                    'backtester': self.backtester
                }
            else:
                logger.error("❌ No se obtuvieron resultados del backtest combinado")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error en backtest combinado: {e}")
            return {}
            
    def analyze_correlations(self, available_symbols: Dict[str, List[str]]) -> Dict:
        """
        Analizar correlaciones entre activos
        
        Args:
            available_symbols: Símbolos disponibles por clase de activo
            
        Returns:
            Análisis de correlaciones
        """
        logger.info("\n📊 Analizando correlaciones entre activos...")
        
        # Seleccionar símbolos para análisis de correlaciones
        correlation_symbols = []
        for asset_class, symbols in available_symbols.items():
            # Máximo 2 símbolos por clase para análisis de correlaciones
            correlation_symbols.extend(symbols[:2])
        
        if len(correlation_symbols) < 2:
            logger.warning("⚠️ Insuficientes símbolos para análisis de correlaciones")
            return {}
        
        logger.info(f"🔍 Analizando correlaciones para: {correlation_symbols}")
        
        try:
            # Cargar datos de precios
            price_data = self.correlation_analyzer.load_price_data(
                correlation_symbols, 
                interval='1d', 
                limit=180  # 6 meses de datos
            )
            
            if not price_data:
                logger.warning("⚠️ No se pudieron cargar datos para análisis de correlaciones")
                return {}
            
            # Calcular retornos
            returns_data = self.correlation_analyzer.calculate_returns(price_data)
            
            if returns_data.empty:
                logger.warning("⚠️ No se pudieron calcular retornos")
                return {}
            
            # Generar reporte completo de correlaciones
            correlation_report = self.correlation_analyzer.generate_correlation_report()
            
            logger.info("✅ Análisis de correlaciones completado")
            
            return correlation_report
            
        except Exception as e:
            logger.error(f"❌ Error en análisis de correlaciones: {e}")
            return {}
            
    def calculate_advanced_metrics(self) -> Dict:
        """
        Calcular métricas avanzadas del backtest
        
        Returns:
            Métricas avanzadas
        """
        logger.info("📊 Calculando métricas avanzadas...")
        
        advanced_metrics = {}
        
        # Métricas por clase de activo
        if self.asset_class_results:
            class_metrics = {}
            
            for asset_class, data in self.asset_class_results.items():
                results = data['results']
                
                # Calcular métricas adicionales
                total_return_pct = results.get('total_return_pct', 0)
                total_trades = results.get('total_trades', 0)
                win_rate = results.get('win_rate', 0)
                
                # Sharpe ratio simplificado (asumiendo 0% risk-free rate)
                if 'trade_history' in results:
                    trade_returns = [
                        trade.get('return_pct', 0) for trade in results['trade_history']
                        if trade.get('status') == 'closed' and 'return_pct' in trade
                    ]
                    
                    if trade_returns:
                        avg_return = np.mean(trade_returns)
                        std_return = np.std(trade_returns)
                        sharpe_ratio = avg_return / std_return if std_return > 0 else 0
                    else:
                        sharpe_ratio = 0
                else:
                    sharpe_ratio = 0
                
                class_metrics[asset_class] = {
                    'total_return_pct': total_return_pct,
                    'total_trades': total_trades,
                    'win_rate': win_rate,
                    'sharpe_ratio': sharpe_ratio,
                    'profit_factor': self._calculate_profit_factor(results),
                    'max_drawdown': self._calculate_max_drawdown(results)
                }
            
            advanced_metrics['by_asset_class'] = class_metrics
        
        # Métricas del portfolio combinado
        if hasattr(self, 'combined_results') and self.combined_results:
            combined_metrics = self.combined_results.get('results', {})
            
            advanced_metrics['combined_portfolio'] = {
                'total_return_pct': combined_metrics.get('total_return_pct', 0),
                'total_trades': combined_metrics.get('total_trades', 0),
                'win_rate': combined_metrics.get('win_rate', 0),
                'sharpe_ratio': self._calculate_sharpe_ratio(combined_metrics),
                'profit_factor': self._calculate_profit_factor(combined_metrics),
                'max_drawdown': self._calculate_max_drawdown(combined_metrics)
            }
        
        logger.info("✅ Métricas avanzadas calculadas")
        return advanced_metrics
        
    def _calculate_profit_factor(self, results: Dict) -> float:
        """Calcular factor de beneficio"""
        if 'trade_history' not in results:
            return 0.0
        
        winning_trades = [
            trade.get('pnl', 0) for trade in results['trade_history']
            if trade.get('status') == 'closed' and trade.get('pnl', 0) > 0
        ]
        
        losing_trades = [
            abs(trade.get('pnl', 0)) for trade in results['trade_history']
            if trade.get('status') == 'closed' and trade.get('pnl', 0) < 0
        ]
        
        total_wins = sum(winning_trades) if winning_trades else 0
        total_losses = sum(losing_trades) if losing_trades else 0
        
        return total_wins / total_losses if total_losses > 0 else float('inf')
        
    def _calculate_max_drawdown(self, results: Dict) -> float:
        """Calcular máximo drawdown"""
        # Simplificado - en implementación real usaríamos equity curve
        total_return_pct = results.get('total_return_pct', 0)
        return min(0, total_return_pct * 0.3)  # Estimación conservadora
        
    def _calculate_sharpe_ratio(self, results: Dict) -> float:
        """Calcular Sharpe ratio"""
        if 'trade_history' not in results:
            return 0.0
        
        trade_returns = [
            trade.get('return_pct', 0) for trade in results['trade_history']
            if trade.get('status') == 'closed' and 'return_pct' in trade
        ]
        
        if not trade_returns:
            return 0.0
        
        avg_return = np.mean(trade_returns)
        std_return = np.std(trade_returns)
        
        return avg_return / std_return if std_return > 0 else 0
        
    def generate_comprehensive_report(self) -> Dict:
        """
        Generar reporte completo del backtest Fase 1
        
        Returns:
            Reporte completo
        """
        logger.info("📋 Generando reporte completo...")
        
        # Calcular métricas avanzadas
        advanced_metrics = self.calculate_advanced_metrics()
        
        # Compilar reporte
        report = {
            'timestamp': datetime.now().isoformat(),
            'phase': 'Fase 1 - Backtest Completo Multi-Asset',
            'initial_capital': self.initial_capital,
            'summary': {
                'total_asset_classes': len(self.asset_class_results),
                'total_symbols_tested': sum(
                    len(data['symbols']) for data in self.asset_class_results.values()
                )
            },
            'asset_class_results': {},
            'combined_portfolio': getattr(self, 'combined_results', {}),
            'correlation_analysis': self.correlation_analysis,
            'advanced_metrics': advanced_metrics,
            'recommendations': self._generate_recommendations()
        }
        
        # Agregar resultados por clase de activo
        for asset_class, data in self.asset_class_results.items():
            report['asset_class_results'][asset_class] = {
                'symbols': data['symbols'],
                'performance': data['results'],
                'symbol_count': len(data['symbols'])
            }
        
        logger.info("✅ Reporte completo generado")
        return report
        
    def _generate_recommendations(self) -> List[str]:
        """Generar recomendaciones basadas en resultados"""
        recommendations = []
        
        if self.asset_class_results:
            # Encontrar mejor clase de activo
            best_class = None
            best_return = float('-inf')
            
            for asset_class, data in self.asset_class_results.items():
                return_pct = data['results'].get('total_return_pct', 0)
                if return_pct > best_return:
                    best_return = return_pct
                    best_class = asset_class
            
            if best_class:
                recommendations.append(
                    f"Mejor rendimiento: {best_class} con {best_return:.2f}% de retorno"
                )
        
        # Recomendaciones de diversificación
        if self.correlation_analysis and 'portfolio_suggestions' in self.correlation_analysis:
            suggestions = self.correlation_analysis['portfolio_suggestions']
            if suggestions and 'diversification_score' in suggestions:
                score = suggestions['diversification_score']
                if score > 0.7:
                    recommendations.append("Excelente diversificación del portfolio")
                elif score > 0.5:
                    recommendations.append("Buena diversificación, considerar optimización")
                else:
                    recommendations.append("Mejorar diversificación del portfolio")
        
        return recommendations
        
    def save_report(self, report: Dict, filename: str = None) -> str:
        """
        Guardar reporte en archivo JSON
        
        Args:
            report: Reporte a guardar
            filename: Nombre del archivo (opcional)
            
        Returns:
            Ruta del archivo guardado
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"phase1_complete_backtest_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Reporte guardado en: {filename}")
        return filename
        
    def print_summary_results(self, report: Dict):
        """Imprimir resumen de resultados"""
        print("\n" + "="*80)
        print("🚀 BACKTEST COMPLETO FASE 1 - SISTEMA MULTI-ASSET SICAR")
        print("="*80)
        
        print(f"\n💰 CONFIGURACIÓN:")
        print(f"   • Capital inicial: ${report['initial_capital']:,.2f}")
        print(f"   • Clases de activos: {report['summary']['total_asset_classes']}")
        print(f"   • Símbolos totales: {report['summary']['total_symbols_tested']}")
        
        print(f"\n📊 RESULTADOS POR CLASE DE ACTIVO:")
        for asset_class, data in report['asset_class_results'].items():
            performance = data['performance']
            print(f"\n   🏷️  {asset_class.upper()}:")
            print(f"      • Símbolos: {data['symbol_count']}")
            print(f"      • Retorno: {performance.get('total_return_pct', 0):+.2f}%")
            print(f"      • Trades: {performance.get('total_trades', 0)}")
            print(f"      • Win Rate: {performance.get('win_rate', 0):.1f}%")
        
        if 'combined_portfolio' in report and report['combined_portfolio']:
            combined = report['combined_portfolio']['results']
            print(f"\n🌐 PORTFOLIO COMBINADO:")
            print(f"   • Retorno total: {combined.get('total_return_pct', 0):+.2f}%")
            print(f"   • Total trades: {combined.get('total_trades', 0)}")
            print(f"   • Win Rate: {combined.get('win_rate', 0):.1f}%")
        
        if 'recommendations' in report and report['recommendations']:
            print(f"\n💡 RECOMENDACIONES:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"   {i}. {rec}")
        
        print("\n" + "="*80)
        
    def run_complete_backtest(self) -> Dict:
        """
        Ejecutar backtest completo de Fase 1
        
        Returns:
            Reporte completo de resultados
        """
        logger.info("🚀 Iniciando Backtest Completo Fase 1...")
        
        try:
            # 1. Obtener símbolos disponibles
            available_symbols = self.get_all_available_symbols()
            
            if not available_symbols:
                logger.error("❌ No hay símbolos disponibles para backtest")
                return {}
            
            # 2. Ejecutar backtests individuales por clase de activo
            self.asset_class_results = self.run_individual_asset_backtests(available_symbols)
            
            # 3. Ejecutar backtest de portfolio combinado
            self.combined_results = self.run_combined_portfolio_backtest(available_symbols)
            
            # 4. Analizar correlaciones
            self.correlation_analysis = self.analyze_correlations(available_symbols)
            
            # 5. Generar reporte completo
            complete_report = self.generate_comprehensive_report()
            
            # 6. Guardar reporte
            report_file = self.save_report(complete_report)
            
            # 7. Mostrar resumen
            self.print_summary_results(complete_report)
            
            logger.info("✅ Backtest Completo Fase 1 finalizado exitosamente")
            
            return complete_report
            
        except Exception as e:
            logger.error(f"❌ Error en Backtest Completo Fase 1: {e}")
            return {}

def main():
    """Función principal"""
    print("🚀 Iniciando Backtest Completo Fase 1 - Sistema Multi-Asset SICAR...")
    
    try:
        # Inicializar backtest con capital mayor para Fase 1
        phase1_backtest = Phase1CompleteBacktest(initial_capital=50000)
        
        # Ejecutar backtest completo
        results = phase1_backtest.run_complete_backtest()
        
        if results:
            print("\n✅ Backtest Completo Fase 1 ejecutado exitosamente")
            return phase1_backtest
        else:
            print("\n❌ Error en la ejecución del backtest")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        return None

if __name__ == "__main__":
    backtest_system = main()