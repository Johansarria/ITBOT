#!/usr/bin/env python3
"""
Script específico para probar la integración con Z.ai API
"""

import os
import sys
import time
import requests

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar Z.ai API key
os.environ['ZAI_API_KEY'] = '810916269b0a45b4bea346db43c334f4.i9X0Fygr30fvkjQN'
os.environ['ALLOW_EXTERNAL_LLMS'] = 'true'

from module_xai import _generate_report_zai, save_cognitive_report

def test_zai_api():
    """Prueba específica de la API de Z.ai"""
    
    print("🧪 PROBANDO API DE Z.AI")
    print("="*50)
    
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
            'ruptura_resistencia'
        ],
        'additional_context': {
            'price': 45250.50,
            'volume_ratio': 1.35,
            'rsi': 65.2,
            'market_cap': 850000000000,
            'dominance': 0.42
        }
    }
    
    print(f"\n📊 Configuración:")
    print(f"   ZAI_API_KEY: {os.environ.get('ZAI_API_KEY', 'No configurada')[:20]}...")
    print(f"   ALLOW_EXTERNAL_LLMS: {os.environ.get('ALLOW_EXTERNAL_LLMS', 'false')}")
    
    # Primero, vamos a probar una llamada directa a la API
    print(f"\n🔍 PROBANDO LLAMADA DIRECTA A Z.AI API...")
    
    try:
        import requests
        
        # Preparar el payload para Z.ai
        prompt = f"""
        Genera un reporte cognitivo para la siguiente decisión de trading del sistema SICAR:
        
        **DECISIÓN TOMADA:** {test_data['decision']}
        **ESTRATEGIA SELECCIONADA:** {test_data['strategy']}
        **RÉGIMEN DE MERCADO:** {test_data['market_regime']}
        
        **FACTORES EXPLICATIVOS:**
        - Confianza: {test_data['xai_factors']['confidence']}
        - Fuerza de señal: {test_data['xai_factors']['signal_strength']}
        - Volatilidad: {test_data['xai_factors']['volatility']}
        - Momentum: {test_data['xai_factors']['momentum']}
        
        **CONTEXTO ADICIONAL:**
        - Precio: ${test_data['additional_context']['price']}
        - Ratio de Volumen: {test_data['additional_context']['volume_ratio']}
        - RSI: {test_data['additional_context']['rsi']}
        
        Proporciona un análisis claro y conciso de esta decisión de trading.
        """
        
        zai_api_key = os.environ.get('ZAI_API_KEY')
        zai_api_url = os.environ.get('ZAI_API_URL', 'https://api.z.ai/api/paas/v4')
        
        headers = {
            'Authorization': f'Bearer {zai_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': 'glm-4.6',
            'messages': [
                {
                    'role': 'system',
                    'content': """Eres un analista financiero experto especializado en explicar decisiones de trading algorítmico. 
                    Tu tarea es generar reportes cognitivos claros y comprensibles que expliquen las decisiones de trading 
                    del sistema SICAR (Sistema Inteligente de Cartografía y Análisis de Riesgos).
                    
                    Características de tus reportes:
                    - Claros y concisos (máximo 300 palabras)
                    - Técnicamente precisos pero accesibles
                    - Enfocados en el razonamiento detrás de la decisión
                    - Incluyen factores de riesgo y confianza
                    - Proporcionan contexto de mercado relevante"""
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': 500,
            'temperature': 0.3
        }
        
        print(f"\n📡 Realizando petición a Z.ai...")
        print(f"   URL: {zai_api_url}/chat/completions")
        print(f"   Modelo: glm-4.6")
        
        start_time = time.time()
        
        response = requests.post(
            f"{zai_api_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        print(f"\n📊 Resultado de la petición:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Tiempo de respuesta: {response_time:.2f}s")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ RESPUESTA EXITOSA:")
            print(f"   Modelo: {result.get('model', 'N/A')}")
            print(f"   Choices: {len(result.get('choices', []))}")
            
            if result.get('choices'):
                content = result['choices'][0].get('message', {}).get('content', '')
                print(f"\n📝 Contenido del reporte:")
                print("-" * 50)
                print(content)
                print("-" * 50)
                
                # Guardar el reporte
                from module_xai import save_cognitive_report
                filepath = save_cognitive_report(content, "reporte_zai_directo.txt")
                if filepath:
                    print(f"\n💾 Reporte guardado en: {filepath}")
                    
                return True
        else:
            print(f"\n❌ ERROR EN LA PETICIÓN:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            # Intentar parsear error
            try:
                error_data = response.json()
                print(f"   Error details: {error_data}")
            except:
                pass
                
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {str(e)}")
        return False
    
    # Si la llamada directa falla, probar con la función del módulo
    print(f"\n🔧 PROBANDO FUNCIÓN DEL MÓDULO XAI...")
    
    try:
        report = _generate_report_zai(**test_data)
        
        if report and 'Error' not in report:
            print(f"\n✅ REPORTE GENERADO CON MÓDULO XAI:")
            print("-" * 50)
            print(report)
            print("-" * 50)
            
            # Guardar reporte
            filepath = save_cognitive_report(report, "reporte_zai_modulo.txt")
            if filepath:
                print(f"\n💾 Reporte guardado en: {filepath}")
                
            return True
        else:
            print(f"\n❌ Error en función del módulo: {report}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR EN FUNCIÓN DEL MÓDULO: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🚀 INICIANDO PRUEBA DE Z.AI API")
    print("="*60)
    
    success = test_zai_api()
    
    print(f"\n{'='*60}")
    if success:
        print("✅ PRUEBA DE Z.AI COMPLETADA EXITOSAMENTE")
    else:
        print("❌ PRUEBA DE Z.AI FALLIDA")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()