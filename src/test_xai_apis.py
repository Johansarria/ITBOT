#!/usr/bin/env python3
"""
Script de prueba para verificar la integración de APIs de IA en SICAR XAI
"""

import os
import sys
import time
from typing import Dict, Any

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_xai import (
    generate_cognitive_report, 
    generate_multi_ai_comparison_report,
    _generate_report_openai,
    _generate_report_anthropic,
    _generate_report_zai,
    _generate_report_grok
)

def test_api_integration(api_name: str, test_function, **kwargs) -> Dict[str, Any]:
    """Prueba una API específica y devuelve los resultados"""
    print(f"\n{'='*50}")
    print(f"🧪 PROBANDO {api_name.upper()}")
    print(f"{'='*50}")
    
    start_time = time.time()
    
    try:
        result = test_function(**kwargs)
        success = True
        error = None
        
        # Si es un reporte, verificar que tenga contenido
        if isinstance(result, str):
            content_length = len(result)
            has_content = content_length > 100  # Mínimo 100 caracteres
        else:
            content_length = len(str(result))
            has_content = content_length > 0
            
    except Exception as e:
        success = False
        error = str(e)
        content_length = 0
        has_content = False
        result = None
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    return {
        'api_name': api_name,
        'success': success,
        'error': error,
        'execution_time': execution_time,
        'content_length': content_length,
        'has_content': has_content,
        'result': result
    }

def main():
    """Función principal de pruebas"""
    print("🚀 INICIANDO PRUEBAS DE INTEGRACIÓN XAI MULTI-API")
    
    # Datos de prueba estándar
    test_data = {
        'decision': "BUY",
        'strategy': "momentum",
        'market_regime': "Tendencia Alcista",
        'xai_factors': {
            'confidence': 0.85,
            'signal_strength': 0.72,
            'volatility': 0.025,
            'momentum': 0.08
        },
        'primary_causal_factors': [
            'momentum_alcista',
            'volumen_confirmatorio',
            'ruptura_resistencia'
        ],
        'additional_context': {
            'price': 45250.50,
            'volume_ratio': 1.35,
            'rsi': 65.2
        }
    }
    
    # Verificar qué APIs están configuradas
    apis_config = {
        'OpenAI': {
            'key': os.getenv('OPENAI_API_KEY'),
            'function': _generate_report_openai
        },
        'Anthropic': {
            'key': os.getenv('ANTHROPIC_API_KEY'),
            'function': _generate_report_anthropic
        },
        'Z.ai': {
            'key': os.getenv('ZAI_API_KEY'),
            'function': _generate_report_zai
        },
        'Grok': {
            'key': os.getenv('GROK_API_KEY'),
            'function': _generate_report_grok
        }
    }
    
    print("\n📋 CONFIGURACIÓN ACTUAL:")
    print(f"   ALLOW_EXTERNAL_LLMS: {os.getenv('ALLOW_EXTERNAL_LLMS', 'false')}")
    print(f"   LLM_FALLBACK_ORDER: {os.getenv('LLM_FALLBACK_ORDER', 'openai,anthropic,zai,grok,local')}")
    
    # Mostrar estado de APIs
    configured_apis = []
    for api_name, config in apis_config.items():
        status = "✅ CONFIGURADA" if config['key'] else "❌ NO CONFIGURADA"
        print(f"   {api_name}: {status}")
        if config['key']:
            configured_apis.append(api_name)
    
    if not configured_apis:
        print("\n⚠️  NINGUNA API EXTERNA ESTÁ CONFIGURADA")
        print("   El sistema usará análisis local por defecto")
        return
    
    # Ejecutar pruebas individuales
    results = []
    for api_name in configured_apis:
        config = apis_config[api_name]
        result = test_api_integration(api_name, config['function'], **test_data)
        results.append(result)
    
    # Ejecutar prueba de sistema completo (con fallback automático)
    print(f"\n{'='*50}")
    print("🔄 PROBANDO SISTEMA COMPLETO CON FALLBACK")
    print(f"{'='*50}")
    
    start_time = time.time()
    try:
        system_report = generate_cognitive_report(**test_data)
        system_success = True
        system_error = None
        system_content_length = len(system_report)
    except Exception as e:
        system_success = False
        system_error = str(e)
        system_content_length = 0
        system_report = None
    
    end_time = time.time()
    system_execution_time = end_time - start_time
    
    # Ejecutar comparación multi-IA
    print(f"\n{'='*50}")
    print("🔍 PROBANDO COMPARACIÓN MULTI-IA")
    print(f"{'='*50}")
    
    start_time = time.time()
    try:
        comparison_result = generate_multi_ai_comparison_report(**test_data)
        comparison_success = True
        comparison_error = None
        comparison_models = len(comparison_result.get('individual_reports', {}))
    except Exception as e:
        comparison_success = False
        comparison_error = str(e)
        comparison_models = 0
        comparison_result = None
    
    end_time = time.time()
    comparison_execution_time = end_time - start_time
    
    # Resumen de resultados
    print(f"\n{'='*60}")
    print("📊 RESUMEN DE PRUEBAS")
    print(f"{'='*60}")
    
    print("\n🔍 RESULTADOS INDIVIDUALES:")
    for result in results:
        status = "✅ EXITOSO" if result['success'] else "❌ FALLIDO"
        print(f"   {result['api_name']}: {status}")
        if result['success']:
            print(f"     ├─ Tiempo: {result['execution_time']:.2f}s")
            print(f"     ├─ Longitud: {result['content_length']} caracteres")
            print(f"     └─ Contenido válido: {'✅' if result['has_content'] else '❌'}")
        else:
            print(f"     └─ Error: {result['error']}")
    
    print(f"\n🔄 SISTEMA CON FALLBACK:")
    system_status = "✅ EXITOSO" if system_success else "❌ FALLIDO"
    print(f"   Sistema completo: {system_status}")
    if system_success:
        print(f"     ├─ Tiempo: {system_execution_time:.2f}s")
        print(f"     └─ Longitud: {system_content_length} caracteres")
    else:
        print(f"     └─ Error: {system_error}")
    
    print(f"\n🔍 COMPARACIÓN MULTI-IA:")
    comparison_status = "✅ EXITOSO" if comparison_success else "❌ FALLIDO"
    print(f"   Comparación: {comparison_status}")
    if comparison_success:
        print(f"     ├─ Tiempo: {comparison_execution_time:.2f}s")
        print(f"     └─ Modelos analizados: {comparison_models}")
    else:
        print(f"     └─ Error: {comparison_error}")
    
    # Recomendaciones
    print(f"\n💡 RECOMENDACIONES:")
    working_apis = [r['api_name'] for r in results if r['success'] and r['has_content']]
    
    if working_apis:
        print(f"   ✅ APIs funcionando: {', '.join(working_apis)}")
        print(f"   📋 Para usar estas APIs, configura:")
        print(f"     ├─ ALLOW_EXTERNAL_LLMS=true")
        print(f"     └─ Asegúrate de tener las claves API en tus variables de entorno")
    else:
        print(f"   ⚠️  Ninguna API externa está funcionando actualmente")
        print(f"   📋 El sistema usará análisis local por defecto")
    
    if 'Grok' in [r['api_name'] for r in results if not r['success']]:
        print(f"   🔧 Grok: Verifica la URL de la API, podría ser diferente")
    
    print(f"\n{'='*60}")
    print("✅ PRUEBAS FINALIZADAS")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()