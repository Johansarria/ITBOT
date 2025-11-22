#!/usr/bin/env python3
"""
Script de depuración específico para Grok API
"""

import os
import requests
import json

# Configurar credenciales
os.environ['GROK_API_KEY'] = 'xai-J6SqzFhZY7ZbtUe2M5KCMF0q0lVPICiK2IuBt9j4BNPH92mmViZqRgTsOmKTDFDMK6GEDzaEmxc4apqj'

def test_grok_models():
    """Probar diferentes modelos de Grok"""
    
    api_key = os.environ.get('GROK_API_KEY')
    base_url = 'https://api.x.ai/v1'
    
    if not api_key:
        print("❌ No se encontró GROK_API_KEY")
        return
    
    # Modelos a probar
    models_to_test = [
        'grok-beta',
        'grok-2-latest', 
        'grok-1',
        'grok-2',
        'grok-3'
    ]
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    test_prompt = "¿Cuál es el significado de la vida, el universo y todo lo demás?"
    
    print("🧪 PROBANDO DIFERENTES MODELOS DE GROK")
    print("="*50)
    
    for model in models_to_test:
        print(f"\n📡 Probando modelo: {model}")
        
        payload = {
            'model': model,
            'messages': [
                {
                    'role': 'system',
                    'content': 'Eres un asistente útil y directo.'
                },
                {
                    'role': 'user',
                    'content': test_prompt
                }
            ],
            'max_tokens': 100,
            'temperature': 0.7
        }
        
        try:
            response = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', 'Sin contenido')
                print(f"   ✅ ÉXITO: {content[:100]}...")
            else:
                print(f"   ❌ ERROR: {response.text}")
                
        except Exception as e:
            print(f"   ❌ EXCEPCIÓN: {str(e)}")

def test_grok_direct():
    """Prueba directa con cURL"""
    print(f"\n🔍 PRUEBA DIRECTA CON CURL")
    print("="*50)
    
    curl_command = '''
curl -X POST "https://api.x.ai/v1/chat/completions" \\
  -H "Authorization: Bearer xai-J6SqzFhZY7ZbtUe2M5KCMF0q0lVPICiK2IuBt9j4BNPH92mmViZqRgTsOmKTDFDMK6GEDzaEmxc4apqj" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "grok-beta",
    "messages": [
      {"role": "user", "content": "Hello, Grok!"}
    ],
    "max_tokens": 50
  }'
'''
    
    print("Comando cURL para probar manualmente:")
    print(curl_command)

if __name__ == '__main__':
    test_grok_models()
    test_grok_direct()