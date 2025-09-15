#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificación final de las nuevas claves API de Binance
"""

import os
import sys
from datetime import datetime

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("dotenv no disponible, usando variables de entorno del sistema")

def verificar_configuracion():
    """Verificar que las nuevas claves API están configuradas correctamente"""
    print("="*70)
    print("🔐 VERIFICACIÓN FINAL DE CLAVES API DE BINANCE")
    print("="*70)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Verificar variables de entorno
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    print("📋 ESTADO DE CONFIGURACIÓN:")
    print("-" * 40)
    
    if api_key:
        print(f"✅ BINANCE_API_KEY: {api_key[:8]}...{api_key[-8:]}")
        if api_key == 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs':
            print("   🎯 Nuevas claves API configuradas correctamente")
        else:
            print("   ⚠️  Claves API diferentes a las nuevas")
    else:
        print("❌ BINANCE_API_KEY: No configurado")
    
    if secret_key:
        print(f"✅ BINANCE_SECRET_KEY: {secret_key[:8]}...{secret_key[-8:]}")
        if secret_key == 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy':
            print("   🎯 Secret key configurado correctamente")
        else:
            print("   ⚠️  Secret key diferente al nuevo")
    else:
        print("❌ BINANCE_SECRET_KEY: No configurado")
    
    print()
    
    # Verificar archivos de configuración
    print("📁 ARCHIVOS DE CONFIGURACIÓN:")
    print("-" * 40)
    
    archivos_config = [
        '.env',
        '.env.test'
    ]
    
    for archivo in archivos_config:
        if os.path.exists(archivo):
            print(f"✅ {archivo}: Existe")
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                    if 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs' in contenido:
                        print(f"   🎯 Contiene las nuevas claves API")
                    else:
                        print(f"   ⚠️  No contiene las nuevas claves API")
            except Exception as e:
                print(f"   ❌ Error al leer: {e}")
        else:
            print(f"❌ {archivo}: No existe")
    
    print()
    
    # Verificar scripts de prueba actualizados
    print("🧪 SCRIPTS DE PRUEBA ACTUALIZADOS:")
    print("-" * 40)
    
    scripts_prueba = [
        'test_connections.py',
        'test_simple.py',
        'test_final.py',
        'test_binance_local.py'
    ]
    
    for script in scripts_prueba:
        if os.path.exists(script):
            print(f"✅ {script}: Existe")
            try:
                with open(script, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                    if 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs' in contenido:
                        print(f"   🎯 Actualizado con nuevas claves")
                    else:
                        print(f"   ⚠️  No actualizado con nuevas claves")
            except Exception as e:
                print(f"   ❌ Error al leer: {e}")
        else:
            print(f"❌ {script}: No existe")
    
    print()
    print("="*70)
    
    # Resumen final
    if (api_key and secret_key and 
        api_key == 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs' and
        secret_key == 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'):
        print("🎉 RESULTADO: CONFIGURACIÓN EXITOSA")
        print("✅ Las nuevas claves API de Binance están configuradas correctamente")
        print("✅ El sistema está listo para operar con las nuevas credenciales")
        return True
    else:
        print("⚠️  RESULTADO: CONFIGURACIÓN INCOMPLETA")
        print("❌ Algunas claves API no están configuradas correctamente")
        return False

if __name__ == "__main__":
    # Guardar resultados en archivo
    with open('verificacion_final_resultado.txt', 'w', encoding='utf-8') as f:
        original_stdout = sys.stdout
        sys.stdout = f
        
        try:
            exito = verificar_configuracion()
        except Exception as e:
            print(f"❌ Error durante la verificación: {e}")
            exito = False
        
        sys.stdout = original_stdout
    
    print("Verificación completada. Resultados guardados en: verificacion_final_resultado.txt")
    print("✅ Nuevas claves API configuradas exitosamente" if exito else "❌ Problemas con la configuración de claves API")
    sys.exit(0 if exito else 1)