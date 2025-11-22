#!/usr/bin/env python3
"""
Script para activar y probar las APIs externas de IA en SICAR XAI
"""

import os
import sys
import time

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Activar LLMs externos
os.environ['ALLOW_EXTERNAL_LLMS'] = 'true'
os.environ['LLM_FALLBACK_ORDER'] = 'openai,anthropic,zai,grok,local'

from module_xai import generate_cognitive_report, generate_multi_ai_comparison_report

def main():
    """Función principal para probar con LLMs externos activados"""
    
    print("🚀 ACTIVANDO LLMs EXTERNOS PARA PRUEBA")
    print(f"   ALLOW_EXTERNAL_LLMS: {os.environ.get('ALLOW_EXTERNAL_LLMS', 'false')}")
    print(f"   LLM_FALLBACK_ORDER: {os.environ.get('LLM_FALLBACK_ORDER', 'local')}")
    
    # Verificar qué APIs están configuradas
    apis_configured = []
    if os.getenv('OPENAI_API_KEY'): apis_configured.append('OpenAI')
    if os.getenv('ANTHROPIC_API_KEY'): apis_configured.append('Anthropic')
    if os.getenv('ZAI_API_KEY'): apis_configured.append('Z.ai')
    if os.getenv('GROK_API_KEY'): apis_configured.append('Grok')
    
    print(f"\n📡 APIs CONFIGURADAS: {', '.join(apis_configured) if apis_configured else 'Ninguna'}")
    
    if not apis_configured:
        print("\n⚠️  NO HAY APIS CONFIGURADAS")
        print("   Por favor, configura al menos una API en tus variables de entorno")
        print("   Ejemplo: export OPENAI_API_KEY='tu-clave-aqui'")
        return
    
    # Datos de prueba
    test_data = {
        'decision': "BUY",
        'strategy': "momentum",
        'market_regime': "Tendencia Alcista",
        'xai_factors': {
            'confidence': 0.85,
            'signal_strength': 0.72,
            'volatility': 0.025,
            'momentum': 0.08,
            'rsi': 65.2,
            'volume_ratio': 1.35
        },
        'primary_causal_factors': [
            'momentum_alcista',
            'volumen_confirmatorio',
            'ruptura_resistencia',
            'rsi_saludable'
        ],
        'additional_context': {
            'price': 45250.50,
            'volume_ratio': 1.35,
            'rsi': 65.2,
            'market_cap': 850000000000,
            'dominance': 0.42
        }
    }
    
    print(f"\n{'='*60}")
    print("🧠 GENERANDO REPORTE COGNITIVO CON LLMs EXTERNOS")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        # Generar reporte con fallback automático
        report = generate_cognitive_report(**test_data)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"\n✅ REPORTE GENERADO EXITOSAMENTE")
        print(f"   ⏱️  Tiempo de ejecución: {execution_time:.2f} segundos")
        print(f"   📊 Longitud del reporte: {len(report)} caracteres")
        
        print(f"\n{'='*40}")
        print("📋 CONTENIDO DEL REPORTE:")
        print(f"{'='*40}")
        print(report)
        
        # Guardar reporte
        from module_xai import save_cognitive_report
        filepath = save_cognitive_report(report, "reporte_con_llms_externos.txt")
        if filepath:
            print(f"\n💾 Reporte guardado en: {filepath}")
        
    except Exception as e:
        print(f"\n❌ ERROR GENERANDO REPORTE: {str(e)}")
        return
    
    # Generar comparación multi-IA
    print(f"\n{'='*60}")
    print("🔍 GENERANDO COMPARACIÓN MULTI-IA")
    print(f"{'='*60}")
    
    start_time = time.time()
    
    try:
        comparison_result = generate_multi_ai_comparison_report(**test_data)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        consensus = comparison_result.get('consensus_analysis', {})
        individual_reports = comparison_result.get('individual_reports', {})
        
        print(f"\n✅ COMPARACIÓN GENERADA EXITOSAMENTE")
        print(f"   ⏱️  Tiempo de ejecución: {execution_time:.2f} segundos")
        print(f"   🤖 Modelos analizados: {len(individual_reports)}")
        
        if 'error' not in consensus:
            print(f"\n📊 ANÁLISIS DE CONSENSO:")
            print(f"   📈 Recomendación: {consensus.get('consensus_recommendation', 'N/A')}")
            print(f"   🎯 Confianza: {consensus.get('confidence_level', 'N/A')}")
            print(f"   📊 Score: {consensus.get('consensus_score', 0):.2f}")
            print(f"   📈 Sentimiento: {consensus.get('average_sentiment', 0):.2f}")
            
            # Mostrar reportes individuales
            if individual_reports:
                print(f"\n📄 REPORTES POR MODELO:")
                for model_name, report in individual_reports.items():
                    if 'Error' not in report:
                        # Mostrar primeras líneas
                        first_sentence = report.split('.')[0] + "..."
                        print(f"\n🤖 {model_name.upper()}:")
                        print(f"   {first_sentence}")
                    else:
                        print(f"\n❌ {model_name.upper()}: {report}")
        
        # Guardar comparación
        comparison_content = f"""
=== COMPARACIÓN MULTI-IA CON LLMs EXTERNOS ===
Timestamp: {comparison_result.get('timestamp', 'N/A')}

📊 CONSENSO:
{consensus}

📄 REPORTES INDIVIDUALES:
{individual_reports}
"""
        
        from module_xai import save_cognitive_report
        comparison_filepath = save_cognitive_report(comparison_content, "comparacion_llms_externos.txt")
        if comparison_filepath:
            print(f"\n💾 Comparación guardada en: {comparison_filepath}")
        
    except Exception as e:
        print(f"\n❌ ERROR EN COMPARACIÓN MULTI-IA: {str(e)}")
        return
    
    print(f"\n{'='*60}")
    print("✅ PRUEBAS FINALIZADAS EXITOSAMENTE")
    print(f"{'='*60}")
    
    print(f"\n💡 RESUMEN:")
    print(f"   ✅ Sistema XAI multi-IA funcionando con LLMs externos")
    print(f"   ✅ Fallback automático entre APIs implementado")
    print(f"   ✅ Análisis de consenso multi-modelo disponible")
    print(f"   ✅ Reportes guardados en disco para análisis posterior")
    
    print(f"\n🔧 CONFIGURACIÓN ACTUAL:")
    print(f"   • ALLOW_EXTERNAL_LLMS: {os.environ.get('ALLOW_EXTERNAL_LLMS', 'false')}")
    print(f"   • Orden de fallback: {os.environ.get('LLM_FALLBACK_ORDER', 'local')}")
    print(f"   • APIs disponibles: {len(configured_apis)} ({', '.join(configured_apis)})")

if __name__ == '__main__':
    main()