#!/usr/bin/env python3
"""
Script de prueba específico para Grok con modelo grok-4-fast-reasoning
"""

import os
import requests
import json

# Configurar credenciales
os.environ['GROK_API_KEY'] = 'xai-J6SqzFhZY7ZbtUe2M5KCMF0q0lVPICiK2IuBt9j4BNPH92mmViZqRgTsOmKTDFDMK6GEDzaEmxc4apqj'

def test_grok_correct_model():
    """Probar Grok con el modelo correcto grok-4-fast-reasoning"""
    
    api_key = os.environ.get('GROK_API_KEY')
    base_url = 'https://api.x.ai/v1'
    
    if not api_key:
        print("❌ No se encontró GROK_API_KEY")
        return False
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Datos de prueba para trading
    test_prompt = """
    Analiza la siguiente decisión de trading:
    
    DECISIÓN: COMPRAR Bitcoin
    ESTRATEGIA: Momentum trading
    PRECIO ACTUAL: $45,250
    VOLUMEN: Alto (1.35x del promedio)
    RSI: 65.2
    
    Proporciona un análisis breve y claro de esta decisión.
    """
    
    print("🧪 PROBANDO GROK CON MODELO grok-4-fast-reasoning")
    print("="*60)
    
    payload = {
        'model': 'grok-4-fast-reasoning',
        'messages': [
            {
                'role': 'system',
                'content': 'Eres un analista financiero experto especializado en criptomonedas y trading algorítmico.'
            },
            {
                'role': 'user',
                'content': test_prompt
            }
        ],
        'max_tokens': 300,
        'temperature': 0.3
    }
    
    try:
        print(f"📡 Realizando petición a Grok...")
        print(f"   URL: {base_url}/chat/completions")
        print(f"   Modelo: grok-4-fast-reasoning")
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"\n📊 Resultado:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', 'Sin contenido')
            
            print(f"\n✅ RESPUESTA EXITOSA:")
            print("-" * 50)
            print(content)
            print("-" * 50)
            
            return True
        else:
            print(f"\n❌ ERROR:")
            print(f"   Response: {response.text}")
            
            # Parsear error si es JSON
            try:
                error_data = response.json()
                print(f"   Error details: {error_data}")
            except:
                pass
                
            return False
            
    except Exception as e:
        print(f"\n❌ EXCEPCIÓN: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_grok_correct_model()
    
    print(f"\n{'='*60}")
    if success:
        print("✅ GROK FUNCIONANDO CORRECTAMENTE")
    else:
        print("❌ GROK CON PROBLEMAS")
    print(f"{'='*60}")