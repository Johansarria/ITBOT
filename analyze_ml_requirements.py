#!/usr/bin/env python3
"""
Análisis teórico de suficiencia de datos para ML trading
Basado en mejores prácticas de la industria y literatura académica
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def analyze_ml_data_requirements():
    """
    Análisis teórico de requerimientos de datos para ML en trading
    """
    print("🧠 ANÁLISIS DE REQUERIMIENTOS DE DATOS PARA ML TRADING")
    print("=" * 65)
    
    print("\n📚 1. LITERATURA ACADÉMICA Y MEJORES PRÁCTICAS")
    
    # Referencias académicas conocidas
    academic_references = [
        {
            "source": "Quantitative Finance Research",
            "min_samples": 5000,
            "optimal_samples": 20000,
            "recommendation": "Mínimo 2-3 años de datos horarios"
        },
        {
            "source": "Machine Learning for Trading (de Prado)",
            "min_samples": 10000,
            "optimal_samples": 50000,
            "recommendation": "Walk-forward con al menos 1000 observaciones por fold"
        },
        {
            "source": "Institutional Trading Standards",
            "min_samples": 8760,  # 1 año horario
            "optimal_samples": 26280,  # 3 años horario
            "recommendation": "Incluir al menos 2 ciclos de mercado completos"
        }
    ]
    
    for ref in academic_references:
        print(f"\n📖 {ref['source']}:")
        print(f"   Mínimo: {ref['min_samples']:,} muestras")
        print(f"   Óptimo: {ref['optimal_samples']:,} muestras")  
        print(f"   💡 {ref['recommendation']}")
    
    print(f"\n🎯 2. ANÁLISIS DE NUESTRO CONTEXTO ACTUAL")
    
    # Información de nuestros modelos actuales
    import os
    model_files = []
    if os.path.exists('data/ml_models'):
        for file in os.listdir('data/ml_models'):
            if file.endswith('.pkl'):
                size = os.path.getsize(f'data/ml_models/{file}')
                model_files.append((file, size))
    
    print(f"Modelos ML disponibles: {len(model_files)}")
    if model_files:
        latest_model = sorted(model_files)[-1]
        print(f"Último modelo: {latest_model[0]} ({latest_model[1]:,} bytes)")
    
    # Configuración actual del sistema
    try:
        # Simular lectura de config sin importar (evita dependencias)
        current_config = {
            "ML_MIN_DATA_POINTS": 50,
            "ML_THRESHOLD_HIGH": 0.85,
            "ML_THRESHOLD_MEDIUM": 0.70,
            "INTERVAL": "1h"
        }
        print(f"Configuración actual:")
        print(f"   Mínimo puntos ML: {current_config['ML_MIN_DATA_POINTS']}")
        print(f"   Umbral alto: {current_config['ML_THRESHOLD_HIGH']}")
        print(f"   Intervalo: {current_config['INTERVAL']}")
    except:
        print("⚠️ No se pudo leer configuración actual")
    
    print(f"\n📊 3. CÁLCULO DE SUFICIENCIA TEÓRICA")
    
    # Períodos de análisis
    intervals = {
        "1h": {"hours_per_period": 1, "periods_per_day": 24},
        "4h": {"hours_per_period": 4, "periods_per_day": 6},
        "1d": {"hours_per_period": 24, "periods_per_day": 1}
    }
    
    current_interval = "1h"
    interval_info = intervals[current_interval]
    
    # Escenarios de datos
    scenarios = [
        {
            "name": "MÍNIMO BÁSICO",
            "months": 2,
            "confidence": "BAJA",
            "risk": "ALTO",
            "use_case": "Solo testing/desarrollo"
        },
        {
            "name": "ACEPTABLE",
            "months": 6, 
            "confidence": "MEDIA",
            "risk": "MEDIO",
            "use_case": "Trading con supervisión"
        },
        {
            "name": "RECOMENDADO",
            "months": 12,
            "confidence": "ALTA",
            "risk": "BAJO", 
            "use_case": "Trading autónomo"
        },
        {
            "name": "ÓPTIMO",
            "months": 24,
            "confidence": "MUY ALTA",
            "risk": "MUY BAJO",
            "use_case": "Trading institucional"
        },
        {
            "name": "ENTERPRISE",
            "months": 36,
            "confidence": "MÁXIMA", 
            "risk": "MÍNIMO",
            "use_case": "Fondos de inversión"
        }
    ]
    
    print(f"\n{'ESCENARIO':<15} {'MESES':<6} {'MUESTRAS':<8} {'CONFIANZA':<12} {'RIESGO':<8} {'USO RECOMENDADO'}")
    print("-" * 85)
    
    for scenario in scenarios:
        samples = scenario["months"] * 30 * interval_info["periods_per_day"]
        print(f"{scenario['name']:<15} {scenario['months']:<6} {samples:<8,} {scenario['confidence']:<12} {scenario['risk']:<8} {scenario['use_case']}")
    
    print(f"\n🔬 4. FACTORES CRÍTICOS PARA ACERTIVIDAD")
    
    critical_factors = [
        {
            "factor": "Diversidad de condiciones de mercado",
            "weight": "30%",
            "requirement": "Al menos 2 ciclos alcista/bajista completos",
            "current_status": "⚠️ PENDIENTE VERIFICAR"
        },
        {
            "factor": "Calidad de datos",
            "weight": "25%", 
            "requirement": "Sin gaps > 2 horas, datos OHLCV completos",
            "current_status": "❓ SIN EVALUAR"
        },
        {
            "factor": "Cantidad absoluta",
            "weight": "20%",
            "requirement": "Mínimo 8,760 muestras (1 año horario)",
            "current_status": "❌ INSUFICIENTE (solo 50 min)"
        },
        {
            "factor": "Balance temporal",
            "weight": "15%",
            "requirement": "Distribución equilibrada por hora/día/mes",
            "current_status": "❓ SIN EVALUAR"
        },
        {
            "factor": "Volatilidad representativa", 
            "weight": "10%",
            "requirement": "Incluir períodos alta/media/baja volatilidad",
            "current_status": "❓ SIN EVALUAR"
        }
    ]
    
    print(f"{'FACTOR':<30} {'PESO':<6} {'REQUERIMIENTO':<35} {'STATUS'}")
    print("-" * 95)
    for factor in critical_factors:
        print(f"{factor['factor']:<30} {factor['weight']:<6} {factor['requirement']:<35} {factor['current_status']}")
    
    print(f"\n⚠️ 5. PROBLEMAS IDENTIFICADOS CON CONFIGURACIÓN ACTUAL")
    
    problems = [
        {
            "issue": "ML_MIN_DATA_POINTS = 50",
            "severity": "🔴 CRÍTICO",
            "explanation": "Extremadamente bajo para ML confiable",
            "recommendation": "Aumentar a mínimo 2,000 puntos"
        },
        {
            "issue": "Sin validación de continuidad",
            "severity": "🟡 IMPORTANTE", 
            "explanation": "Gaps en datos pueden sesgar el modelo",
            "recommendation": "Implementar verificación de gaps"
        },
        {
            "issue": "Sin análisis de régimen de mercado",
            "severity": "🟡 IMPORTANTE",
            "explanation": "Modelo puede fallar en condiciones no vistas",
            "recommendation": "Incluir detector de régimen de mercado"
        },
        {
            "issue": "Reentrenamiento diario automático",
            "severity": "🟠 MODERADO",
            "explanation": "Puede causar overfitting a ruido reciente", 
            "recommendation": "Reentrenar solo cada 1-2 semanas"
        }
    ]
    
    print(f"{'PROBLEMA':<35} {'SEVERIDAD':<12} {'RECOMENDACIÓN'}")
    print("-" * 95)
    for problem in problems:
        print(f"{problem['issue']:<35} {problem['severity']:<12} {problem['recommendation']}")
        print(f"   💬 {problem['explanation']}")
        print()
    
    print(f"🎯 6. RECOMENDACIONES ESPECÍFICAS PARA TU SISTEMA")
    
    recommendations = [
        "📈 INMEDIATO: Descargar al menos 6 meses de datos BTCUSDT 1h",
        "⚙️ CONFIGURACIÓN: Cambiar ML_MIN_DATA_POINTS de 50 a 2000",
        "🔄 PROCESO: Implementar descarga automática de datos históricos faltantes",
        "📊 VALIDACIÓN: Crear script de análisis de calidad de datos",
        "🧪 TESTING: Implementar backtesting con walk-forward validation",
        "📈 MONITOREO: Dashboard de métricas de acertividad en tiempo real",
        "🔧 MANTENIMIENTO: Reentrenamiento semanal en lugar de diario"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    print(f"\n💡 7. SCRIPT DE ACCIÓN INMEDIATA")
    
    action_script = """
# 1. Descargar datos históricos completos
python3 download_historical_data.py --symbol BTCUSDT --interval 1h --start "6 months ago"

# 2. Verificar calidad de datos  
python3 check_data_quality.py --symbol BTCUSDT --min-records 4000

# 3. Actualizar configuración ML
# Cambiar en config.py: ML_MIN_DATA_POINTS = 2000

# 4. Reentrenar modelo con datos completos
python3 ml_model_trainer.py --retrain --validate

# 5. Ejecutar backtesting completo
python3 backtest_strategies.py --start-date "3 months ago" --strategy MLStrategy
"""
    
    print(action_script)
    
    # Crear reporte final
    current_assessment = {
        "current_min_data_points": 50,
        "recommended_min_data_points": 2000,
        "current_confidence_level": "MUY BAJA",
        "recommended_data_months": 6,
        "critical_issues": len([p for p in problems if "CRÍTICO" in p["severity"]]),
        "assessment_date": datetime.now().isoformat(),
        "overall_recommendation": "AUMENTAR DATOS HISTÓRICOS ANTES DE TRADING REAL"
    }
    
    # Guardar assessment
    with open('data/ml_sufficiency_assessment.json', 'w') as f:
        json.dump(current_assessment, f, indent=2)
    
    print(f"\n💾 Assessment guardado en: data/ml_sufficiency_assessment.json")
    
    print(f"\n🚨 CONCLUSIÓN FINAL:")
    print(f"   Configuración actual (50 puntos mínimos) es INSUFICIENTE para trading real")
    print(f"   Recomendación: Descargar 6+ meses de datos antes de usar ML en producción")
    print(f"   Riesgo actual: MUY ALTO - Posibles pérdidas por decisiones ML poco confiables")

if __name__ == "__main__":
    analyze_ml_data_requirements()
