#!/usr/bin/env python3
"""
Sistema de Backtesting con Múltiples Bases de Capital
Permite evaluar estrategias con diferentes tamaños de cuenta (200-1000 USDT)
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Tuple, Optional
from dataclasses import dataclass
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_backtester import AdvancedBacktester, BacktestResult, AdvancedMetrics

@dataclass
class CapitalAnalysisResult:
    """Resultado del análisis de múltiples capitales"""
    capital: float
    backtest_result: BacktestResult
    advanced_metrics: AdvancedMetrics
    roi_percentage: float
    profit_loss: float
    trades_count: int
    win_rate: float
    avg_trade_duration: float
    max_position_size: float
    capital_efficiency: float

@dataclass
class MultiCapitalSummary:
    """Resumen del análisis de múltiples capitales"""
    capital_results: List[CapitalAnalysisResult]
    best_capital: float
    worst_capital: float
    optimal_capital_range: Tuple[float, float]
    scalability_score: float
    capital_efficiency_trend: str
    recommendations: List[str]

class MultiCapitalBacktester:
    """
    Backtester que evalúa estrategias con múltiples bases de capital
    """
    
    def __init__(self, 
                 capital_range: Tuple[float, float] = (200, 1000),
                 capital_steps: int = 9,
                 commission_rate: float = 0.001):
        """
        Inicializar el backtester multi-capital
        
        Args:
            capital_range: Rango de capital (min, max) en USDT
            capital_steps: Número de pasos entre min y max
            commission_rate: Tasa de comisión
        """
        self.capital_range = capital_range
        self.capital_steps = capital_steps
        self.commission_rate = commission_rate
        
        # Generar lista de capitales a probar
        self.capital_list = np.linspace(
            capital_range[0], 
            capital_range[1], 
            capital_steps
        ).round(2)
        
        self.logger = logging.getLogger(__name__)
        self.results: List[CapitalAnalysisResult] = []
        
        self.logger.info(f"🏦 MultiCapitalBacktester inicializado")
        self.logger.info(f"💰 Capitales a probar: {self.capital_list}")
    
    def run_multi_capital_backtest(self,
                                 market_data: Dict[str, pd.DataFrame],
                                 strategy_func: Callable,
                                 start_date: str,
                                 end_date: str,
                                 parallel: bool = True) -> MultiCapitalSummary:
        """
        Ejecutar backtest con múltiples capitales
        
        Args:
            market_data: Datos de mercado
            strategy_func: Función de estrategia
            start_date: Fecha de inicio
            end_date: Fecha de fin
            parallel: Ejecutar en paralelo
            
        Returns:
            MultiCapitalSummary: Resumen de resultados
        """
        self.logger.info("🚀 Iniciando backtest multi-capital...")
        
        if parallel:
            results = self._run_parallel_backtest(
                market_data, strategy_func, start_date, end_date
            )
        else:
            results = self._run_sequential_backtest(
                market_data, strategy_func, start_date, end_date
            )
        
        self.results = results
        summary = self._analyze_results(results)
        
        self.logger.info("✅ Backtest multi-capital completado")
        return summary
    
    def _run_parallel_backtest(self,
                             market_data: Dict[str, pd.DataFrame],
                             strategy_func: Callable,
                             start_date: str,
                             end_date: str) -> List[CapitalAnalysisResult]:
        """Ejecutar backtest en paralelo"""
        results = []
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Enviar tareas
            future_to_capital = {
                executor.submit(
                    self._run_single_capital_backtest,
                    capital, market_data, strategy_func, start_date, end_date
                ): capital
                for capital in self.capital_list
            }
            
            # Recoger resultados
            for future in as_completed(future_to_capital):
                capital = future_to_capital[future]
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.info(f"✅ Capital ${capital}: ROI {result.roi_percentage:.2f}%")
                except Exception as e:
                    self.logger.error(f"❌ Error con capital ${capital}: {e}")
        
        # Ordenar por capital
        results.sort(key=lambda x: x.capital)
        return results
    
    def _run_sequential_backtest(self,
                               market_data: Dict[str, pd.DataFrame],
                               strategy_func: Callable,
                               start_date: str,
                               end_date: str) -> List[CapitalAnalysisResult]:
        """Ejecutar backtest secuencial"""
        results = []
        
        for i, capital in enumerate(self.capital_list):
            self.logger.info(f"📊 Probando capital ${capital} ({i+1}/{len(self.capital_list)})")
            
            try:
                result = self._run_single_capital_backtest(
                    capital, market_data, strategy_func, start_date, end_date
                )
                results.append(result)
                self.logger.info(f"✅ Capital ${capital}: ROI {result.roi_percentage:.2f}%")
            except Exception as e:
                self.logger.error(f"❌ Error con capital ${capital}: {e}")
        
        return results
    
    def _run_single_capital_backtest(self,
                                   capital: float,
                                   market_data: Dict[str, pd.DataFrame],
                                   strategy_func: Callable,
                                   start_date: str,
                                   end_date: str) -> CapitalAnalysisResult:
        """Ejecutar backtest para un capital específico"""
        
        # Crear backtester con el capital específico
        backtester = AdvancedBacktester(
            initial_capital=capital,
            commission_rate=self.commission_rate
        )
        
        # Cargar datos de mercado
        backtester.load_market_data(market_data)
        
        # Ejecutar backtest
        backtest_result = backtester.run_backtest(
            strategy_func=strategy_func,
            start_date=start_date,
            end_date=end_date
        )
        
        # Calcular métricas adicionales usando el capital actual del backtester
        final_capital = backtester.current_capital
        roi_percentage = ((final_capital - capital) / capital) * 100
        profit_loss = final_capital - capital
        
        # Calcular métricas específicas de capital
        trades_count = len(backtester.all_trades)
        win_rate = self._calculate_win_rate(backtester.all_trades)
        avg_trade_duration = self._calculate_avg_trade_duration(backtester.all_trades)
        max_position_size = self._calculate_max_position_size(backtester.all_trades, capital)
        capital_efficiency = self._calculate_capital_efficiency(profit_loss, capital, trades_count)
        
        return CapitalAnalysisResult(
            capital=capital,
            backtest_result=backtest_result,
            advanced_metrics=backtest_result.advanced_metrics,
            roi_percentage=roi_percentage,
            profit_loss=profit_loss,
            trades_count=trades_count,
            win_rate=win_rate,
            avg_trade_duration=avg_trade_duration,
            max_position_size=max_position_size,
            capital_efficiency=capital_efficiency
        )
    
    def _calculate_win_rate(self, trades: List) -> float:
        """Calcular tasa de ganancia"""
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for trade in trades if hasattr(trade, 'pnl') and trade.pnl > 0)
        return (winning_trades / len(trades)) * 100
    
    def _calculate_avg_trade_duration(self, trades: List) -> float:
        """Calcular duración promedio de trades"""
        if not trades:
            return 0.0
        
        # Para trades simples, usar timestamp como aproximación
        # En un sistema más complejo, necesitaríamos entry_time y exit_time
        return 1.0  # Placeholder - 1 hora promedio
    
    def _calculate_max_position_size(self, trades: List, capital: float) -> float:
        """Calcular tamaño máximo de posición como % del capital"""
        if not trades:
            return 0.0
        
        max_size = 0.0
        for trade in trades:
            if hasattr(trade, 'quantity') and hasattr(trade, 'price'):
                position_value = trade.quantity * trade.price
                position_percentage = (position_value / capital) * 100
                max_size = max(max_size, position_percentage)
        
        return max_size
    
    def _calculate_capital_efficiency(self, profit_loss: float, capital: float, trades_count: int) -> float:
        """Calcular eficiencia del capital"""
        if trades_count == 0:
            return 0.0
        
        # Eficiencia = (Profit/Loss por trade) / Capital utilizado
        profit_per_trade = profit_loss / trades_count
        return (profit_per_trade / capital) * 10000  # Multiplicar por 10000 para mejor escala
    
    def _analyze_results(self, results: List[CapitalAnalysisResult]) -> MultiCapitalSummary:
        """Analizar resultados y generar resumen"""
        
        if not results:
            raise ValueError("No hay resultados para analizar")
        
        # Encontrar mejor y peor capital
        best_result = max(results, key=lambda x: x.roi_percentage)
        worst_result = min(results, key=lambda x: x.roi_percentage)
        
        # Calcular rango óptimo de capital
        optimal_range = self._find_optimal_capital_range(results)
        
        # Calcular score de escalabilidad
        scalability_score = self._calculate_scalability_score(results)
        
        # Analizar tendencia de eficiencia
        efficiency_trend = self._analyze_efficiency_trend(results)
        
        # Generar recomendaciones
        recommendations = self._generate_recommendations(results, optimal_range, scalability_score)
        
        return MultiCapitalSummary(
            capital_results=results,
            best_capital=best_result.capital,
            worst_capital=worst_result.capital,
            optimal_capital_range=optimal_range,
            scalability_score=scalability_score,
            capital_efficiency_trend=efficiency_trend,
            recommendations=recommendations
        )
    
    def _find_optimal_capital_range(self, results: List[CapitalAnalysisResult]) -> Tuple[float, float]:
        """Encontrar rango óptimo de capital"""
        # Filtrar resultados con ROI positivo
        positive_results = [r for r in results if r.roi_percentage > 0]
        
        if not positive_results:
            return (self.capital_range[0], self.capital_range[1])
        
        # Encontrar rango con mejor eficiencia promedio
        min_capital = min(positive_results, key=lambda x: x.capital).capital
        max_capital = max(positive_results, key=lambda x: x.capital).capital
        
        return (min_capital, max_capital)
    
    def _calculate_scalability_score(self, results: List[CapitalAnalysisResult]) -> float:
        """Calcular score de escalabilidad (0-100)"""
        if len(results) < 2:
            return 0.0
        
        # Calcular correlación entre capital y ROI
        capitals = [r.capital for r in results]
        rois = [r.roi_percentage for r in results]
        
        correlation = np.corrcoef(capitals, rois)[0, 1]
        
        # Convertir correlación a score (0-100)
        # Correlación positiva = buena escalabilidad
        score = max(0, (correlation + 1) * 50)
        
        return score
    
    def _analyze_efficiency_trend(self, results: List[CapitalAnalysisResult]) -> str:
        """Analizar tendencia de eficiencia del capital"""
        if len(results) < 3:
            return "Insuficientes datos"
        
        efficiencies = [r.capital_efficiency for r in results]
        
        # Calcular tendencia usando regresión lineal simple
        x = np.arange(len(efficiencies))
        slope = np.polyfit(x, efficiencies, 1)[0]
        
        if slope > 0.1:
            return "Creciente"
        elif slope < -0.1:
            return "Decreciente"
        else:
            return "Estable"
    
    def _generate_recommendations(self, 
                                results: List[CapitalAnalysisResult],
                                optimal_range: Tuple[float, float],
                                scalability_score: float) -> List[str]:
        """Generar recomendaciones basadas en el análisis"""
        recommendations = []
        
        # Recomendación de capital óptimo
        best_result = max(results, key=lambda x: x.roi_percentage)
        recommendations.append(
            f"💰 Capital óptimo recomendado: ${best_result.capital:.0f} USDT "
            f"(ROI: {best_result.roi_percentage:.2f}%)"
        )
        
        # Recomendación de rango
        recommendations.append(
            f"📊 Rango de capital efectivo: ${optimal_range[0]:.0f} - ${optimal_range[1]:.0f} USDT"
        )
        
        # Recomendación de escalabilidad
        if scalability_score > 70:
            recommendations.append("📈 Excelente escalabilidad - La estrategia mejora con más capital")
        elif scalability_score > 40:
            recommendations.append("⚖️ Escalabilidad moderada - Considerar optimización de parámetros")
        else:
            recommendations.append("⚠️ Baja escalabilidad - Revisar estrategia para capitales mayores")
        
        # Recomendación de gestión de riesgo
        avg_max_position = np.mean([r.max_position_size for r in results])
        if avg_max_position > 50:
            recommendations.append("🛡️ Reducir tamaño de posiciones - Riesgo elevado detectado")
        
        return recommendations
    
    def generate_report(self, summary: MultiCapitalSummary, save_path: Optional[str] = None) -> str:
        """Generar reporte detallado del análisis"""
        
        report = []
        report.append("=" * 80)
        report.append("📊 REPORTE DE ANÁLISIS MULTI-CAPITAL")
        report.append("=" * 80)
        report.append(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"💰 Rango de capital: ${self.capital_range[0]} - ${self.capital_range[1]} USDT")
        report.append(f"🔢 Capitales probados: {len(summary.capital_results)}")
        report.append("")
        
        # Resumen ejecutivo
        report.append("📋 RESUMEN EJECUTIVO")
        report.append("-" * 40)
        report.append(f"🏆 Mejor capital: ${summary.best_capital:.0f} USDT")
        report.append(f"📉 Peor capital: ${summary.worst_capital:.0f} USDT")
        report.append(f"📊 Score de escalabilidad: {summary.scalability_score:.1f}/100")
        report.append(f"📈 Tendencia de eficiencia: {summary.capital_efficiency_trend}")
        report.append("")
        
        # Resultados detallados
        report.append("📈 RESULTADOS DETALLADOS")
        report.append("-" * 40)
        report.append(f"{'Capital':<10} {'ROI%':<8} {'P&L':<10} {'Trades':<8} {'Win%':<8} {'Sharpe':<8}")
        report.append("-" * 60)
        
        for result in summary.capital_results:
            report.append(
                f"${result.capital:<9.0f} "
                f"{result.roi_percentage:<7.2f}% "
                f"${result.profit_loss:<9.2f} "
                f"{result.trades_count:<7} "
                f"{result.win_rate:<7.1f}% "
                f"{result.backtest_result.sharpe_ratio:<7.3f}"
            )
        
        report.append("")
        
        # Recomendaciones
        report.append("💡 RECOMENDACIONES")
        report.append("-" * 40)
        for i, rec in enumerate(summary.recommendations, 1):
            report.append(f"{i}. {rec}")
        
        report.append("")
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        # Guardar si se especifica ruta
        if save_path:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
            self.logger.info(f"📄 Reporte guardado en: {save_path}")
        
        return report_text
    
    def plot_capital_analysis(self, summary: MultiCapitalSummary, save_path: Optional[str] = None):
        """Crear gráficos del análisis de capital"""
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Análisis Multi-Capital', fontsize=16, fontweight='bold')
        
        # Datos para gráficos
        capitals = [r.capital for r in summary.capital_results]
        rois = [r.roi_percentage for r in summary.capital_results]
        sharpes = [r.backtest_result.sharpe_ratio for r in summary.capital_results]
        efficiencies = [r.capital_efficiency for r in summary.capital_results]
        
        # 1. ROI vs Capital
        axes[0, 0].plot(capitals, rois, 'bo-', linewidth=2, markersize=8)
        axes[0, 0].set_title('ROI vs Capital Inicial')
        axes[0, 0].set_xlabel('Capital (USDT)')
        axes[0, 0].set_ylabel('ROI (%)')
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        
        # 2. Sharpe Ratio vs Capital
        axes[0, 1].plot(capitals, sharpes, 'go-', linewidth=2, markersize=8)
        axes[0, 1].set_title('Sharpe Ratio vs Capital')
        axes[0, 1].set_xlabel('Capital (USDT)')
        axes[0, 1].set_ylabel('Sharpe Ratio')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Eficiencia del Capital
        axes[1, 0].bar(range(len(capitals)), efficiencies, color='orange', alpha=0.7)
        axes[1, 0].set_title('Eficiencia del Capital')
        axes[1, 0].set_xlabel('Capital (USDT)')
        axes[1, 0].set_ylabel('Eficiencia')
        axes[1, 0].set_xticks(range(len(capitals)))
        axes[1, 0].set_xticklabels([f'${c:.0f}' for c in capitals], rotation=45)
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Distribución de ROI
        axes[1, 1].hist(rois, bins=min(10, len(rois)), color='purple', alpha=0.7, edgecolor='black')
        axes[1, 1].set_title('Distribución de ROI')
        axes[1, 1].set_xlabel('ROI (%)')
        axes[1, 1].set_ylabel('Frecuencia')
        axes[1, 1].axvline(x=np.mean(rois), color='red', linestyle='--', 
                          label=f'Media: {np.mean(rois):.2f}%')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            self.logger.info(f"📊 Gráficos guardados en: {save_path}")
        
        plt.show()
    
    def export_results_to_json(self, summary: MultiCapitalSummary, file_path: str):
        """Exportar resultados a JSON"""
        
        data = {
            "analysis_date": datetime.now().isoformat(),
            "capital_range": self.capital_range,
            "summary": {
                "best_capital": summary.best_capital,
                "worst_capital": summary.worst_capital,
                "optimal_capital_range": summary.optimal_capital_range,
                "scalability_score": summary.scalability_score,
                "capital_efficiency_trend": summary.capital_efficiency_trend,
                "recommendations": summary.recommendations
            },
            "detailed_results": []
        }
        
        for result in summary.capital_results:
            data["detailed_results"].append({
                "capital": result.capital,
                "roi_percentage": result.roi_percentage,
                "profit_loss": result.profit_loss,
                "trades_count": result.trades_count,
                "win_rate": result.win_rate,
                "sharpe_ratio": result.backtest_result.sharpe_ratio,
                "max_drawdown": result.backtest_result.max_drawdown,
                "capital_efficiency": result.capital_efficiency
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📁 Resultados exportados a: {file_path}")


def create_sample_strategy():
    """Crear estrategia de ejemplo para testing"""
    
    def momentum_strategy(backtester, market_data, timestamp):
        """Estrategia de momentum simple"""
        
        if 'BTCUSDT' not in market_data:
            return
        
        btc_data = market_data['BTCUSDT']
        if len(btc_data) < 20:
            return
        
        # Calcular momentum (SMA 5 vs SMA 20)
        sma_5 = btc_data['close'].tail(5).mean()
        sma_20 = btc_data['close'].tail(20).mean()
        current_price = btc_data['close'].iloc[-1]
        
        # Señal de compra
        if sma_5 > sma_20 * 1.02 and len(backtester.current_positions) == 0:
            if backtester.current_capital > 50:  # Mínimo para operar
                investment = min(backtester.current_capital * 0.8, backtester.current_capital - 20)
                quantity = investment / current_price
                
                from advanced_backtester import OrderSide, OrderType
                backtester.place_order(
                    symbol='BTCUSDT',
                    side=OrderSide.BUY,
                    order_type=OrderType.MARKET,
                    quantity=quantity
                )
        
        # Señal de venta
        elif sma_5 < sma_20 * 0.98 and 'BTCUSDT' in backtester.current_positions:
            position_quantity = backtester.current_positions['BTCUSDT']
            
            from advanced_backtester import OrderSide, OrderType
            backtester.place_order(
                symbol='BTCUSDT',
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=position_quantity
            )
    
    return momentum_strategy


if __name__ == "__main__":
    # Test del sistema
    print("🧪 Probando MultiCapitalBacktester...")
    
    # Crear datos de prueba
    dates = pd.date_range('2023-01-01', '2023-12-31', freq='1H')
    np.random.seed(42)
    
    # Simular datos de BTC con tendencia alcista
    price_changes = np.random.normal(0.001, 0.02, len(dates))
    prices = [20000]
    for change in price_changes:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1000))  # Precio mínimo
    
    btc_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices[:-1],
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
        'close': prices[1:],
        'volume': np.random.uniform(100, 1000, len(dates))
    })
    
    market_data = {'BTCUSDT': btc_data}
    
    # Crear backtester multi-capital
    multi_backtester = MultiCapitalBacktester(
        capital_range=(200, 1000),
        capital_steps=9
    )
    
    # Ejecutar análisis
    strategy = create_sample_strategy()
    summary = multi_backtester.run_multi_capital_backtest(
        market_data=market_data,
        strategy_func=strategy,
        start_date='2023-01-01',
        end_date='2023-12-31',
        parallel=False
    )
    
    # Generar reporte
    report = multi_backtester.generate_report(summary)
    print(report)
    
    print("✅ Test completado exitosamente!")