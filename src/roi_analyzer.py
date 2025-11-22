# /src/roi_analyzer.py
"""
Analizador de ROI para optimizar el sistema hacia 15% mensual después de fees
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import sys
import os

# Configuración del logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ROIAnalyzer:
    """Analizador de ROI para optimización del sistema de trading."""
    
    def __init__(self, target_monthly_roi: float = 0.15):
        """
        Inicializa el analizador de ROI.
        
        Args:
            target_monthly_roi: ROI objetivo mensual (0.15 = 15%)
        """
        self.target_monthly_roi = target_monthly_roi
        self.binance_maker_fee = 0.001  # 0.1% fee maker
        self.binance_taker_fee = 0.001  # 0.1% fee taker
        
    def calculate_current_performance(self, results_file: str) -> Dict[str, Any]:
        """
        Calcula el rendimiento actual del sistema.
        
        Args:
            results_file: Archivo CSV con resultados del backtesting
            
        Returns:
            Diccionario con métricas de rendimiento
        """
        try:
            # Cargar datos
            df = pd.read_csv(results_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Calcular duración del backtest
            start_date = df['timestamp'].min()
            end_date = df['timestamp'].max()
            duration_days = (end_date - start_date).days
            duration_months = duration_days / 30.44  # Promedio de días por mes
            
            # Obtener valores inicial y final
            initial_value = df['portfolio_value'].iloc[0]
            final_value = df['portfolio_value'].iloc[-1]
            
            # Calcular retorno total
            total_return = (final_value - initial_value) / initial_value
            
            # Calcular ROI mensual actual
            if duration_months > 0:
                monthly_roi = (((final_value / initial_value) ** (1/duration_months)) - 1)
            else:
                monthly_roi = 0
            
            # Contar operaciones
            trades_count = len(df[df['position'] != 'none'])
            
            # Calcular fees estimados
            estimated_fees = self._estimate_trading_fees(df)
            
            # ROI después de fees
            roi_after_fees = monthly_roi - (estimated_fees / initial_value / duration_months)
            
            # Calcular volatilidad
            daily_returns = df['portfolio_value'].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252)  # Anualizada
            
            # Calcular Sharpe ratio
            sharpe_ratio = (monthly_roi * 12) / volatility if volatility > 0 else 0
            
            # Calcular drawdown máximo
            rolling_max = df['portfolio_value'].expanding().max()
            drawdown = (df['portfolio_value'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            performance = {
                'duration_days': duration_days,
                'duration_months': duration_months,
                'initial_value': initial_value,
                'final_value': final_value,
                'total_return': total_return,
                'monthly_roi_before_fees': monthly_roi,
                'estimated_fees': estimated_fees,
                'monthly_roi_after_fees': roi_after_fees,
                'target_monthly_roi': self.target_monthly_roi,
                'roi_gap': self.target_monthly_roi - roi_after_fees,
                'trades_count': trades_count,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'trades_per_day': trades_count / duration_days if duration_days > 0 else 0
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error calculando rendimiento: {e}")
            return {}
    
    def _estimate_trading_fees(self, df: pd.DataFrame) -> float:
        """
        Estima los fees de trading basado en las operaciones.
        
        Args:
            df: DataFrame con datos de trading
            
        Returns:
            Fees estimados totales
        """
        try:
            # Identificar cambios de posición (nuevas operaciones)
            position_changes = df[df['position'] != df['position'].shift(1)]
            
            total_fees = 0
            for _, row in position_changes.iterrows():
                if row['position'] != 'none':
                    # Estimar volumen de la operación (2% del capital disponible)
                    trade_volume = row['portfolio_value'] * 0.02
                    # Aplicar fee (asumimos taker fee)
                    trade_fee = trade_volume * self.binance_taker_fee
                    total_fees += trade_fee
            
            return total_fees
            
        except Exception as e:
            logger.error(f"Error estimando fees: {e}")
            return 0
    
    def calculate_required_improvements(self, performance: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula las mejoras necesarias para alcanzar el objetivo.
        
        Args:
            performance: Métricas de rendimiento actual
            
        Returns:
            Diccionario con mejoras requeridas
        """
        current_roi = performance.get('monthly_roi_after_fees', 0)
        roi_gap = performance.get('roi_gap', 0)
        
        # Factor de mejora necesario
        if current_roi > 0:
            improvement_factor = self.target_monthly_roi / current_roi
        else:
            improvement_factor = float('inf')
        
        # Estrategias de mejora
        improvements = {
            'current_monthly_roi': current_roi,
            'target_monthly_roi': self.target_monthly_roi,
            'roi_gap': roi_gap,
            'improvement_factor': improvement_factor,
            'strategies': []
        }
        
        # Sugerencias específicas
        if roi_gap > 0.10:  # Gap mayor al 10%
            improvements['strategies'].extend([
                'Implementar apalancamiento controlado (2x-3x)',
                'Aumentar frecuencia de trading',
                'Optimizar umbrales de señales',
                'Implementar arbitraje entre exchanges'
            ])
        elif roi_gap > 0.05:  # Gap entre 5-10%
            improvements['strategies'].extend([
                'Mejorar timing de entrada y salida',
                'Implementar stop-loss dinámico',
                'Optimizar gestión de posiciones'
            ])
        else:  # Gap menor al 5%
            improvements['strategies'].extend([
                'Ajustes finos en indicadores',
                'Optimización de fees',
                'Mejora en gestión de riesgo'
            ])
        
        return improvements
    
    def generate_optimization_report(self, results_file: str) -> str:
        """
        Genera un reporte completo de optimización.
        
        Args:
            results_file: Archivo con resultados del backtesting
            
        Returns:
            Reporte de optimización
        """
        try:
            performance = self.calculate_current_performance(results_file)
            improvements = self.calculate_required_improvements(performance)
            
            report = f"""
=== REPORTE DE ANÁLISIS ROI ===
Objetivo: {self.target_monthly_roi*100:.1f}% ROI mensual después de fees

RENDIMIENTO ACTUAL:
- Duración del backtest: {performance.get('duration_days', 0):.0f} días ({performance.get('duration_months', 0):.1f} meses)
- Capital inicial: ${performance.get('initial_value', 0):.2f}
- Capital final: ${performance.get('final_value', 0):.2f}
- Retorno total: {performance.get('total_return', 0)*100:.2f}%
- ROI mensual (antes de fees): {performance.get('monthly_roi_before_fees', 0)*100:.2f}%
- Fees estimados: ${performance.get('estimated_fees', 0):.2f}
- ROI mensual (después de fees): {performance.get('monthly_roi_after_fees', 0)*100:.2f}%

MÉTRICAS DE RIESGO:
- Volatilidad anualizada: {performance.get('volatility', 0)*100:.2f}%
- Sharpe ratio: {performance.get('sharpe_ratio', 0):.2f}
- Drawdown máximo: {performance.get('max_drawdown', 0)*100:.2f}%
- Operaciones totales: {performance.get('trades_count', 0)}
- Operaciones por día: {performance.get('trades_per_day', 0):.2f}

ANÁLISIS DE BRECHA:
- ROI objetivo: {self.target_monthly_roi*100:.1f}%
- ROI actual: {improvements.get('current_monthly_roi', 0)*100:.2f}%
- Brecha a cubrir: {improvements.get('roi_gap', 0)*100:.2f}%
- Factor de mejora necesario: {improvements.get('improvement_factor', 0):.2f}x

ESTRATEGIAS DE MEJORA RECOMENDADAS:
"""
            
            for i, strategy in enumerate(improvements.get('strategies', []), 1):
                report += f"{i}. {strategy}\n"
            
            # Cálculos adicionales
            report += f"""
PROYECCIONES:
- Para alcanzar 15% mensual necesitamos:
  * Mejorar el rendimiento en {improvements.get('improvement_factor', 0):.1f}x
  * Generar ${performance.get('initial_value', 500) * self.target_monthly_roi:.2f} adicionales por mes
  * Mantener drawdown < 10%
  * Sharpe ratio > 2.0

PRÓXIMOS PASOS:
1. Implementar cálculo de fees en tiempo real
2. Optimizar estrategias de trading
3. Implementar gestión de riesgo avanzada
4. Considerar apalancamiento controlado
5. Aumentar frecuencia de operaciones
"""
            
            return report
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return f"Error generando reporte: {e}"

def main():
    """Función principal para análisis de ROI."""
    analyzer = ROIAnalyzer(target_monthly_roi=0.15)
    
    # Analizar resultados del backtester avanzado
    results_file = 'advanced_rebalancing_backtest_results.csv'
    
    if os.path.exists(results_file):
        print("Analizando rendimiento del sistema actual...")
        report = analyzer.generate_optimization_report(results_file)
        print(report)
        
        # Guardar reporte
        with open('roi_analysis_report.txt', 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\nReporte guardado en: roi_analysis_report.txt")
    else:
        print(f"Archivo de resultados no encontrado: {results_file}")
        print("Ejecuta primero el backtester avanzado.")

if __name__ == "__main__":
    main()