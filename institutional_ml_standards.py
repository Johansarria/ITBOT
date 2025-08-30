#!/usr/bin/env python3
"""
Estándares de Acertividad ML de Nivel Institucional
Implementa métricas profesionales para fondos de inversión y trading algorítmico
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class InstitutionalMetrics:
    """Métricas de acertividad institucional"""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    hit_rate: float
    profit_factor: float
    expectancy: float
    win_loss_ratio: float
    var_95: float  # Value at Risk 95%
    cvar_95: float  # Conditional VaR 95%
    kelly_criterion: float
    information_ratio: float
    
class InstitutionalMLValidator:
    """
    Validador de acertividad ML para estándares institucionales
    """
    
    def __init__(self):
        self.institutional_standards = {
            # Métricas mínimas para fondos institucionales
            "minimum_standards": {
                "accuracy": 0.55,           # 55% mínimo
                "precision": 0.52,          # 52% precisión
                "recall": 0.50,             # 50% recall
                "sharpe_ratio": 1.5,        # Sharpe > 1.5
                "max_drawdown": 0.15,       # Max 15% drawdown
                "calmar_ratio": 1.0,        # Calmar > 1.0
                "hit_rate": 0.52,           # 52% trades ganadores
                "profit_factor": 1.3,       # PF > 1.3
                "var_95": 0.05,             # VaR diario < 5%
                "kelly_criterion": 0.25,    # Kelly conservador
                "min_trades": 500,          # Mínimo 500 trades
                "min_data_points": 17520,   # 2 años de datos horarios
                "max_model_age_days": 30    # Reentrenar cada 30 días
            },
            # Estándares objetivo para fondos top-tier
            "target_standards": {
                "accuracy": 0.62,           # 62% objetivo
                "precision": 0.60,          # 60% precisión
                "recall": 0.58,             # 58% recall
                "sharpe_ratio": 2.0,        # Sharpe > 2.0
                "max_drawdown": 0.10,       # Max 10% drawdown
                "calmar_ratio": 1.5,        # Calmar > 1.5
                "hit_rate": 0.58,           # 58% trades ganadores
                "profit_factor": 1.6,       # PF > 1.6
                "var_95": 0.03,             # VaR diario < 3%
                "kelly_criterion": 0.35,    # Kelly más agresivo
                "information_ratio": 0.8    # IR > 0.8
            },
            # Benchmarks de la industria (fondos cuantitativos élite)
            "elite_standards": {
                "accuracy": 0.68,           # 68% élite
                "precision": 0.65,          # 65% precisión
                "recall": 0.62,             # 62% recall
                "sharpe_ratio": 2.5,        # Sharpe > 2.5
                "max_drawdown": 0.08,       # Max 8% drawdown
                "calmar_ratio": 2.0,        # Calmar > 2.0
                "hit_rate": 0.62,           # 62% trades ganadores
                "profit_factor": 2.0,       # PF > 2.0
                "var_95": 0.02,             # VaR diario < 2%
                "kelly_criterion": 0.45     # Kelly óptimo
            }
        }
        
    def calculate_ml_accuracy_metrics(self, predictions: pd.DataFrame, actual_returns: pd.Series) -> InstitutionalMetrics:
        """
        Calcula métricas de acertividad ML según estándares institucionales
        """
        # Convertir predicciones ML a señales binarias
        pred_signals = np.where(predictions['buy_probability'] > predictions['sell_probability'], 1, 
                               np.where(predictions['sell_probability'] > predictions['buy_probability'], -1, 0))
        
        # Calcular retornos reales direccionales
        actual_signals = np.where(actual_returns > 0, 1, np.where(actual_returns < 0, -1, 0))
        
        # Métricas de clasificación
        correct_predictions = (pred_signals == actual_signals).sum()
        total_predictions = len(pred_signals)
        accuracy = correct_predictions / total_predictions
        
        # True/False positives para compras
        buy_mask = pred_signals == 1
        tp_buy = ((pred_signals == 1) & (actual_signals == 1)).sum()
        fp_buy = ((pred_signals == 1) & (actual_signals != 1)).sum()
        fn_buy = ((pred_signals != 1) & (actual_signals == 1)).sum()
        
        precision = tp_buy / (tp_buy + fp_buy) if (tp_buy + fp_buy) > 0 else 0
        recall = tp_buy / (tp_buy + fn_buy) if (tp_buy + fn_buy) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Métricas financieras
        strategy_returns = pred_signals[1:] * actual_returns[1:].values  # Desfase de 1 período
        
        # Sharpe Ratio (anualizado)
        if len(strategy_returns) > 0 and strategy_returns.std() > 0:
            sharpe_ratio = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(365*24)  # Hourly to annual
        else:
            sharpe_ratio = 0
        
        # Maximum Drawdown
        cumulative_returns = (1 + strategy_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        
        # Calmar Ratio
        annual_return = strategy_returns.mean() * 365 * 24
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0
        
        # Hit Rate (% trades ganadores)
        winning_trades = (strategy_returns > 0).sum()
        total_trades = len(strategy_returns[strategy_returns != 0])
        hit_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Profit Factor
        gross_profit = strategy_returns[strategy_returns > 0].sum()
        gross_loss = abs(strategy_returns[strategy_returns < 0].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Expectancy
        avg_win = strategy_returns[strategy_returns > 0].mean() if len(strategy_returns[strategy_returns > 0]) > 0 else 0
        avg_loss = strategy_returns[strategy_returns < 0].mean() if len(strategy_returns[strategy_returns < 0]) > 0 else 0
        expectancy = (hit_rate * avg_win) + ((1 - hit_rate) * avg_loss)
        
        # Win/Loss Ratio
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Value at Risk (95%)
        var_95 = np.percentile(strategy_returns, 5) if len(strategy_returns) > 0 else 0
        
        # Conditional VaR (95%)
        cvar_95 = strategy_returns[strategy_returns <= var_95].mean() if len(strategy_returns[strategy_returns <= var_95]) > 0 else 0
        
        # Kelly Criterion
        if win_loss_ratio > 0 and hit_rate > 0:
            kelly_criterion = hit_rate - ((1 - hit_rate) / win_loss_ratio)
        else:
            kelly_criterion = 0
        
        # Information Ratio (vs benchmark = 0)
        tracking_error = strategy_returns.std()
        information_ratio = (strategy_returns.mean() / tracking_error) if tracking_error > 0 else 0
        
        return InstitutionalMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            hit_rate=hit_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            win_loss_ratio=win_loss_ratio,
            var_95=var_95,
            cvar_95=cvar_95,
            kelly_criterion=kelly_criterion,
            information_ratio=information_ratio
        )
    
    def evaluate_institutional_compliance(self, metrics: InstitutionalMetrics, 
                                        data_points: int, model_age_days: int) -> Dict:
        """
        Evalúa el cumplimiento con estándares institucionales
        """
        results = {
            "compliance_level": "NONE",
            "grade": "F",
            "score": 0,
            "certifications": [],
            "requirements_met": [],
            "requirements_failed": [],
            "recommendations": []
        }
        
        # Verificar datos mínimos
        min_data = self.institutional_standards["minimum_standards"]["min_data_points"]
        if data_points < min_data:
            results["requirements_failed"].append(f"Datos insuficientes: {data_points} < {min_data}")
            results["recommendations"].append(f"Descargar al menos {min_data:,} puntos de datos históricos")
            return results
        
        # Evaluar contra estándares mínimos
        min_std = self.institutional_standards["minimum_standards"]
        min_score = 0
        min_passed = 0
        min_total = 0
        
        metrics_to_check = [
            ("accuracy", metrics.accuracy, "≥"),
            ("precision", metrics.precision, "≥"),
            ("recall", metrics.recall, "≥"),
            ("sharpe_ratio", metrics.sharpe_ratio, "≥"),
            ("max_drawdown", metrics.max_drawdown, "≤"),
            ("calmar_ratio", metrics.calmar_ratio, "≥"),
            ("hit_rate", metrics.hit_rate, "≥"),
            ("profit_factor", metrics.profit_factor, "≥"),
            ("var_95", abs(metrics.var_95), "≤"),
            ("kelly_criterion", metrics.kelly_criterion, "≥")
        ]
        
        for metric_name, metric_value, operator in metrics_to_check:
            if metric_name in min_std:
                min_total += 1
                threshold = min_std[metric_name]
                
                if operator == "≥":
                    passed = metric_value >= threshold
                else:  # "≤"
                    passed = metric_value <= threshold
                
                if passed:
                    min_passed += 1
                    results["requirements_met"].append(f"{metric_name}: {metric_value:.3f} {operator} {threshold}")
                    min_score += 10
                else:
                    results["requirements_failed"].append(f"{metric_name}: {metric_value:.3f} {operator} {threshold}")
                    results["recommendations"].append(f"Mejorar {metric_name} a {operator} {threshold}")
        
        # Evaluar estándares objetivo
        target_std = self.institutional_standards["target_standards"]
        target_score = 0
        target_passed = 0
        
        for metric_name, metric_value, operator in metrics_to_check:
            if metric_name in target_std:
                threshold = target_std[metric_name]
                
                if operator == "≥":
                    passed = metric_value >= threshold
                else:
                    passed = metric_value <= threshold
                
                if passed:
                    target_passed += 1
                    target_score += 15
        
        # Evaluar estándares élite
        elite_std = self.institutional_standards["elite_standards"]
        elite_score = 0
        elite_passed = 0
        
        for metric_name, metric_value, operator in metrics_to_check:
            if metric_name in elite_std:
                threshold = elite_std[metric_name]
                
                if operator == "≥":
                    passed = metric_value >= threshold
                else:
                    passed = metric_value <= threshold
                
                if passed:
                    elite_passed += 1
                    elite_score += 20
        
        # Determinar nivel de compliance
        total_score = min_score + target_score + elite_score
        results["score"] = total_score
        
        if min_passed >= 8:  # 80% de métricas mínimas
            results["compliance_level"] = "INSTITUTIONAL_MINIMUM"
            results["grade"] = "C"
            results["certifications"].append("Aprobado para trading institucional básico")
            
            if target_passed >= 7:  # 70% de métricas objetivo
                results["compliance_level"] = "INSTITUTIONAL_TARGET"
                results["grade"] = "B"
                results["certifications"].append("Cumple estándares institucionales objetivo")
                
                if elite_passed >= 6:  # 60% de métricas élite
                    results["compliance_level"] = "INSTITUTIONAL_ELITE"
                    results["grade"] = "A"
                    results["certifications"].append("Nivel élite - Fondos cuantitativos top-tier")
        
        # Recomendaciones adicionales
        if model_age_days > min_std["max_model_age_days"]:
            results["recommendations"].append(f"Reentrenar modelo (edad: {model_age_days} días)")
        
        if metrics.kelly_criterion > 0.5:
            results["recommendations"].append("Kelly Criterion muy alto - reducir apalancamiento")
        
        if metrics.max_drawdown > 0.20:
            results["recommendations"].append("Drawdown excesivo - revisar gestión de riesgo")
        
        return results
    
    def generate_institutional_report(self, metrics: InstitutionalMetrics, 
                                    compliance: Dict, symbol: str = "BTCUSDT") -> str:
        """
        Genera reporte completo de certificación institucional
        """
        report = f"""
🏛️ CERTIFICACIÓN INSTITUCIONAL ML TRADING
════════════════════════════════════════════════════════════════════════

📊 RESUMEN EJECUTIVO:
   Símbolo: {symbol}
   Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
   Nivel de Compliance: {compliance['compliance_level']}
   Calificación: {compliance['grade']}
   Puntuación: {compliance['score']}/300

🎯 MÉTRICAS DE ACERTIVIDAD ML:
   • Accuracy (Precisión Global): {metrics.accuracy:.3f} ({metrics.accuracy*100:.1f}%)
   • Precision (Precisión Positiva): {metrics.precision:.3f} ({metrics.precision*100:.1f}%)
   • Recall (Sensibilidad): {metrics.recall:.3f} ({metrics.recall*100:.1f}%)
   • F1-Score (Balance): {metrics.f1_score:.3f}

📈 MÉTRICAS FINANCIERAS:
   • Sharpe Ratio: {metrics.sharpe_ratio:.2f}
   • Calmar Ratio: {metrics.calmar_ratio:.2f}
   • Maximum Drawdown: {metrics.max_drawdown:.3f} ({metrics.max_drawdown*100:.1f}%)
   • Hit Rate: {metrics.hit_rate:.3f} ({metrics.hit_rate*100:.1f}%)
   • Profit Factor: {metrics.profit_factor:.2f}
   • Win/Loss Ratio: {metrics.win_loss_ratio:.2f}

🛡️ MÉTRICAS DE RIESGO:
   • VaR (95%): {metrics.var_95:.4f} ({metrics.var_95*100:.2f}%)
   • CVaR (95%): {metrics.cvar_95:.4f} ({metrics.cvar_95*100:.2f}%)
   • Kelly Criterion: {metrics.kelly_criterion:.3f} ({metrics.kelly_criterion*100:.1f}%)
   • Information Ratio: {metrics.information_ratio:.2f}
   • Expectancy: {metrics.expectancy:.4f}

✅ CERTIFICACIONES OBTENIDAS:
"""
        
        for cert in compliance['certifications']:
            report += f"   🏆 {cert}\n"
        
        if not compliance['certifications']:
            report += "   ❌ No cumple estándares institucionales mínimos\n"
        
        report += f"""
✅ REQUERIMIENTOS CUMPLIDOS ({len(compliance['requirements_met'])}):
"""
        for req in compliance['requirements_met']:
            report += f"   ✓ {req}\n"
        
        report += f"""
❌ REQUERIMIENTOS FALLIDOS ({len(compliance['requirements_failed'])}):
"""
        for req in compliance['requirements_failed']:
            report += f"   ✗ {req}\n"
        
        report += f"""
💡 RECOMENDACIONES PRIORITARIAS:
"""
        for i, rec in enumerate(compliance['recommendations'], 1):
            report += f"   {i}. {rec}\n"
        
        # Benchmarks de la industria
        report += f"""
📊 BENCHMARKS DE LA INDUSTRIA:
   
   FONDOS CUANTITATIVOS ÉLITE (Top 10%):
   • Sharpe Ratio: 2.5+     │ Tu sistema: {metrics.sharpe_ratio:.2f}
   • Max Drawdown: <8%      │ Tu sistema: {metrics.max_drawdown*100:.1f}%
   • Hit Rate: 62%+         │ Tu sistema: {metrics.hit_rate*100:.1f}%
   • Accuracy: 68%+         │ Tu sistema: {metrics.accuracy*100:.1f}%
   
   FONDOS INSTITUCIONALES (Promedio):
   • Sharpe Ratio: 1.5-2.0  │ Tu sistema: {metrics.sharpe_ratio:.2f}
   • Max Drawdown: 10-15%   │ Tu sistema: {metrics.max_drawdown*100:.1f}%
   • Hit Rate: 52-58%       │ Tu sistema: {metrics.hit_rate*100:.1f}%
   • Accuracy: 55-62%       │ Tu sistema: {metrics.accuracy*100:.1f}%

🔮 PROYECCIÓN DE CAPITAL RECOMENDADA:
"""
        
        if compliance['compliance_level'] == "INSTITUTIONAL_ELITE":
            report += "   💎 $10M+ - Apto para fondos cuantitativos de élite\n"
        elif compliance['compliance_level'] == "INSTITUTIONAL_TARGET":
            report += "   💰 $1M-$10M - Apto para fondos institucionales\n"
        elif compliance['compliance_level'] == "INSTITUTIONAL_MINIMUM":
            report += "   💵 $100K-$1M - Apto para trading profesional\n"
        else:
            report += "   ⚠️ <$100K - Solo para desarrollo y testing\n"
        
        report += f"""
════════════════════════════════════════════════════════════════════════
🏛️ CERTIFICADO POR: Sistema de Validación Institucional ITBOT v2.0
📅 VÁLIDO HASTA: {(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}
════════════════════════════════════════════════════════════════════════
"""
        
        return report

# Función principal de evaluación
def evaluate_institutional_standards():
    """
    Función principal para evaluar estándares institucionales
    """
    print("🏛️ EVALUACIÓN DE ESTÁNDARES INSTITUCIONALES ML")
    print("=" * 60)
    
    # Simulación de métricas (en producción vendría de backtesting real)
    # Estos valores son ejemplos de un sistema de nivel intermedio
    sample_metrics = InstitutionalMetrics(
        accuracy=0.58,           # 58% - Por encima del mínimo
        precision=0.55,          # 55% - Justo en el límite
        recall=0.52,             # 52% - En el mínimo
        f1_score=0.535,          # Balance razonable
        sharpe_ratio=1.8,        # Bueno para crypto
        max_drawdown=0.12,       # 12% - Aceptable
        calmar_ratio=1.2,        # Por encima del mínimo
        hit_rate=0.54,           # 54% - Decente
        profit_factor=1.4,       # Positivo
        expectancy=0.002,        # Expectancy positiva
        win_loss_ratio=1.3,      # Wins > Losses
        var_95=-0.04,            # 4% VaR diario
        cvar_95=-0.06,           # 6% CVaR
        kelly_criterion=0.28,    # Conservador
        information_ratio=0.6    # Aceptable
    )
    
    validator = InstitutionalMLValidator()
    
    # Evaluar compliance (simulando 1 año de datos)
    compliance = validator.evaluate_institutional_compliance(
        metrics=sample_metrics,
        data_points=8760,  # 1 año de datos horarios
        model_age_days=15  # Modelo reciente
    )
    
    # Generar reporte
    report = validator.generate_institutional_report(sample_metrics, compliance)
    
    print(report)
    
    # Guardar reporte
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"institutional_certification_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n💾 Reporte guardado: {report_file}")
    
    # Guardar métricas JSON para integración
    metrics_dict = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {
            "accuracy": sample_metrics.accuracy,
            "precision": sample_metrics.precision,
            "recall": sample_metrics.recall,
            "f1_score": sample_metrics.f1_score,
            "sharpe_ratio": sample_metrics.sharpe_ratio,
            "max_drawdown": sample_metrics.max_drawdown,
            "calmar_ratio": sample_metrics.calmar_ratio,
            "hit_rate": sample_metrics.hit_rate,
            "profit_factor": sample_metrics.profit_factor,
            "var_95": sample_metrics.var_95,
            "kelly_criterion": sample_metrics.kelly_criterion
        },
        "compliance": compliance
    }
    
    with open("data/institutional_metrics.json", 'w') as f:
        json.dump(metrics_dict, f, indent=2)
    
    return compliance['compliance_level'], compliance['score']

if __name__ == "__main__":
    compliance_level, score = evaluate_institutional_standards()
    
    print(f"\n🎯 RESULTADO FINAL:")
    print(f"   Nivel: {compliance_level}")
    print(f"   Score: {score}/300")
    
    if score >= 200:
        print("   🏆 ¡EXCELENTE! Apto para fondos institucionales")
    elif score >= 100:
        print("   ✅ BUENO - Cumple estándares básicos institucionales") 
    else:
        print("   ⚠️ MEJORAR - No apto para trading institucional aún")
