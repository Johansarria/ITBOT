#!/usr/bin/env python3
"""
Comando para verificar compliance institucional del sistema ML
"""

import sys
import os

# Añadir el directorio raíz al path
sys.path.append('/home/johan/itbot_linux')

def check_institutional_compliance():
    """Verifica el estado de compliance institucional actual"""
    
    print("🏛️ VERIFICACIÓN DE COMPLIANCE INSTITUCIONAL")
    print("=" * 55)
    
    try:
        # Importar monitor institucional
        from utils.institutional_monitor import institutional_monitor, get_institutional_compliance
        
        # Obtener estado actual
        status = get_institutional_compliance()
        
        print(f"\n📊 ESTADO ACTUAL:")
        print(f"   Status: {status.get('status', 'UNKNOWN')}")
        print(f"   Compliance: {status.get('compliance', 'UNKNOWN')}")
        print(f"   Datos disponibles: {status.get('data_points', 0):,} puntos")
        print(f"   Readiness institucional: {status.get('institutional_readiness_pct', 0):.1f}%")
        print(f"   Predicciones recientes: {status.get('recent_predictions', 0)}")
        print(f"   Alertas activas (24h): {status.get('active_alerts', 0)}")
        
        # Mostrar dashboard completo
        print("\n" + "=" * 55)
        dashboard = institutional_monitor.generate_compliance_dashboard()
        print(dashboard)
        
        # Verificar archivos de datos
        print(f"\n📁 VERIFICACIÓN DE ARCHIVOS:")
        data_files = [
            "data/institutional_ml_metrics.json",
            "data/ml_predictions_log.json", 
            "data/ml_data_sufficiency_analysis.json",
            "data/institutional_metrics.json"
        ]
        
        for file_path in data_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"   ✅ {file_path}: {size:,} bytes")
            else:
                print(f"   ❌ {file_path}: No existe")
        
        # Recomendaciones específicas
        print(f"\n💡 ANÁLISIS Y RECOMENDACIONES:")
        
        compliance_level = status.get('compliance', 'NON_COMPLIANT')
        data_points = status.get('data_points', 0)
        
        if compliance_level == "FULL_COMPLIANCE":
            print("   🏆 EXCELENTE: Sistema ready para trading institucional")
            print("   📊 Mantener estándares actuales")
            print("   🔄 Reentrenamiento programado cada 30 días")
        elif compliance_level == "PARTIAL_COMPLIANCE":
            print("   ⚠️ PARCIAL: Sistema en proceso de certificación institucional")
            print("   📈 Continuar acumulando datos de calidad")
            print("   🎯 Target: 80%+ readiness institucional")
        elif compliance_level == "PROFESSIONAL_COMPLIANCE":
            print("   ✅ PROFESIONAL: Apto para trading profesional")
            print("   📊 Aumentar datos históricos para nivel institucional")
            print(f"   🎯 Target: {17520 - data_points:,} puntos adicionales")
        else:
            print("   🔴 DESARROLLO: Sistema no ready para trading real")
            print("   📥 CRÍTICO: Descargar datos históricos completos")
            print("   ⚡ Ejecutar: python3 improve_ml_accuracy.py")
        
        # Próximos pasos
        print(f"\n🚀 PRÓXIMOS PASOS RECOMENDADOS:")
        if data_points < 17520:
            print("   1. 📥 Ejecutar descarga de datos históricos")
            print("   2. 🧪 Realizar backtesting completo")
            print("   3. 📊 Generar métricas de performance")
        else:
            print("   1. 🔍 Realizar auditoría completa de métricas")
            print("   2. 📈 Optimizar parámetros ML")
            print("   3. 🏛️ Solicitar certificación institucional")
        
        print("   4. 📋 Documentar todos los procesos")
        print("   5. 🔄 Establecer monitoreo continuo")
        
    except ImportError as e:
        print(f"❌ Error importando módulos: {e}")
        print("💡 Asegúrate de estar en el entorno virtual correcto")
    except Exception as e:
        print(f"❌ Error verificando compliance: {e}")
        import traceback
        traceback.print_exc()

def show_institutional_standards():
    """Muestra los estándares institucionales detallados"""
    
    standards = {
        "MÍNIMO INSTITUCIONAL": {
            "accuracy": "≥55%",
            "precision": "≥52%", 
            "recall": "≥50%",
            "sharpe_ratio": "≥1.5",
            "max_drawdown": "≤15%",
            "hit_rate": "≥52%",
            "profit_factor": "≥1.3",
            "data_points": "17,520+ (2 años)",
            "capital_recommended": "$100K - $1M"
        },
        "TARGET INSTITUCIONAL": {
            "accuracy": "≥62%",
            "precision": "≥60%",
            "recall": "≥58%", 
            "sharpe_ratio": "≥2.0",
            "max_drawdown": "≤10%",
            "hit_rate": "≥58%",
            "profit_factor": "≥1.6",
            "information_ratio": "≥0.8",
            "capital_recommended": "$1M - $10M"
        },
        "ÉLITE CUANTITATIVO": {
            "accuracy": "≥68%",
            "precision": "≥65%",
            "recall": "≥62%",
            "sharpe_ratio": "≥2.5", 
            "max_drawdown": "≤8%",
            "hit_rate": "≥62%",
            "profit_factor": "≥2.0",
            "kelly_criterion": "≤45%",
            "capital_recommended": "$10M+"
        }
    }
    
    print("🎯 ESTÁNDARES INSTITUCIONALES DETALLADOS")
    print("=" * 50)
    
    for level, metrics in standards.items():
        print(f"\n🏛️ {level}:")
        print("-" * 30)
        for metric, value in metrics.items():
            print(f"   {metric:<20}: {value}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--standards":
        show_institutional_standards()
    else:
        check_institutional_compliance()
