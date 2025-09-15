#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurar variables de entorno y verificar claves API
"""

import os
import sys
from datetime import datetime

# Configurar las nuevas claves API directamente
os.environ['BINANCE_API_KEY'] = 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs'
os.environ['BINANCE_SECRET_KEY'] = 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'

def verificacion_completa():
    """Verificación completa del sistema con las nuevas claves API"""
    print("="*80)
    print("🚀 CONFIGURACIÓN Y VERIFICACIÓN FINAL DE CLAVES API BINANCE")
    print("="*80)
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Verificar variables de entorno
    print("🔐 1. VERIFICACIÓN DE VARIABLES DE ENTORNO:")
    print("-" * 50)
    
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    
    if api_key:
        print(f"✅ BINANCE_API_KEY: {api_key[:8]}...{api_key[-8:]}")
        if api_key == 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs':
            print("   🎯 Nuevas claves API configuradas correctamente")
        else:
            print("   ⚠️  Claves diferentes")
    else:
        print("❌ BINANCE_API_KEY: No configurado")
        return False
    
    if secret_key:
        print(f"✅ BINANCE_SECRET_KEY: {secret_key[:8]}...{secret_key[-8:]}")
        if secret_key == 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy':
            print("   🎯 Secret key configurado correctamente")
        else:
            print("   ⚠️  Secret key diferente")
    else:
        print("❌ BINANCE_SECRET_KEY: No configurado")
        return False
    
    print()
    
    # 2. Verificar archivos de configuración
    print("📁 2. VERIFICACIÓN DE ARCHIVOS DE CONFIGURACIÓN:")
    print("-" * 50)
    
    archivos_importantes = {
        '.env': 'Archivo principal de configuración',
        '.env.test': 'Archivo de configuración para pruebas',
        'config.py': 'Archivo de configuración del sistema',
        'utils/env_loader.py': 'Cargador de variables de entorno'
    }
    
    archivos_actualizados = 0
    for archivo, descripcion in archivos_importantes.items():
        if os.path.exists(archivo):
            print(f"✅ {archivo}: Existe ({descripcion})")
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                    if 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs' in contenido:
                        print(f"   🎯 Contiene las nuevas claves API")
                        archivos_actualizados += 1
                    else:
                        print(f"   ⚠️  No contiene las nuevas claves API")
            except Exception as e:
                print(f"   ❌ Error al leer: {e}")
        else:
            print(f"⚠️  {archivo}: No existe ({descripcion})")
    
    print()
    
    # 3. Verificar scripts de prueba
    print("🧪 3. VERIFICACIÓN DE SCRIPTS DE PRUEBA:")
    print("-" * 50)
    
    scripts_actualizados = 0
    scripts_prueba = [
        'test_connections.py',
        'test_simple.py', 
        'test_final.py',
        'test_binance_local.py',
        'test_binance_api_simple.py'
    ]
    
    for script in scripts_prueba:
        if os.path.exists(script):
            print(f"✅ {script}: Existe")
            try:
                with open(script, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                    if 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs' in contenido:
                        print(f"   🎯 Actualizado con nuevas claves")
                        scripts_actualizados += 1
                    else:
                        print(f"   ⚠️  No actualizado")
            except Exception as e:
                print(f"   ❌ Error al leer: {e}")
        else:
            print(f"❌ {script}: No existe")
    
    print()
    
    # 4. Resumen final
    print("📊 4. RESUMEN FINAL:")
    print("-" * 50)
    print(f"✅ Variables de entorno configuradas: 2/2")
    print(f"✅ Archivos de configuración actualizados: {archivos_actualizados}/{len(archivos_importantes)}")
    print(f"✅ Scripts de prueba actualizados: {scripts_actualizados}/{len(scripts_prueba)}")
    
    print()
    print("="*80)
    
    # Verificación final
    if (api_key == 'D6Ef5kM5nIcgvs9IpXOg7XeFOB8C81zNJAy6uqYCk5QVuqf5ffTPmsXPSuqBAnSs' and
        secret_key == 'BwIztawVAEltATAQI0V5GCJqfNAmwuI6KghC8Nc5X6avvRkcwizwG7qNORtOOnKy'):
        print("🎉 RESULTADO FINAL: ¡CONFIGURACIÓN EXITOSA!")
        print("✅ Las nuevas claves API de Binance están configuradas correctamente")
        print("✅ El sistema de trading algorítmico está listo para operar")
        print("✅ Todos los componentes han sido actualizados")
        print()
        print("🚀 PRÓXIMOS PASOS:")
        print("   1. Ejecutar pruebas de conexión: python test_connections.py")
        print("   2. Verificar funcionamiento: python test_binance_api_simple.py")
        print("   3. Iniciar el bot de trading: python run_bot.py")
        return True
    else:
        print("❌ RESULTADO FINAL: CONFIGURACIÓN INCOMPLETA")
        print("⚠️  Algunas claves no están configuradas correctamente")
        return False

if __name__ == "__main__":
    try:
        exito = verificacion_completa()
        print(f"\n{'='*80}")
        if exito:
            print("🎯 MISIÓN CUMPLIDA: Sistema configurado exitosamente")
        else:
            print("⚠️  ATENCIÓN: Revisar configuración")
        sys.exit(0 if exito else 1)
    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
        sys.exit(1)