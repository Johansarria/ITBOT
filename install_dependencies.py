#!/usr/bin/env python3
"""
Script de instalación de dependencias para SICAR Trading Bot
Instala todas las librerías necesarias para el funcionamiento completo del bot.
"""

import subprocess
import sys
import os

def install_package(package):
    """Instala un paquete usando pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} instalado correctamente")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Error instalando {package}")
        return False

def main():
    """Instala todas las dependencias necesarias."""
    print("🚀 Instalando dependencias para SICAR Trading Bot...")
    print("=" * 50)
    
    # Lista de dependencias principales
    dependencies = [
        # Trading y APIs
        "python-binance>=1.0.19",
        "ccxt>=4.1.0",
        
        # Análisis de datos
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "yfinance>=0.2.0",
        "ta>=0.10.2",
        
        # Machine Learning
        "scikit-learn>=1.3.0",
        "xgboost>=1.7.0",
        "lightgbm>=4.0.0",
        
        # Procesamiento de texto y NLP
        "nltk>=3.8.0",
        "spacy>=3.6.0",
        "textblob>=0.17.0",
        
        # Visualización
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        "plotly>=5.15.0",
        
        # APIs de IA
        "openai>=1.0.0",
        "anthropic>=0.7.0",
        
        # Utilidades
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
        
        # Logging y configuración
        "colorlog>=6.7.0",
        "pyyaml>=6.0.0",
        "configparser>=6.0.0",
        
        # Testing
        "pytest>=7.4.0",
        "pytest-cov>=4.1.0"
    ]
    
    # Instalar dependencias
    failed_packages = []
    for package in dependencies:
        if not install_package(package):
            failed_packages.append(package)
    
    print("\n" + "=" * 50)
    
    if failed_packages:
        print(f"❌ {len(failed_packages)} paquetes fallaron:")
        for package in failed_packages:
            print(f"   - {package}")
        print("\nPuedes intentar instalarlos manualmente:")
        print(f"pip install {' '.join(failed_packages)}")
    else:
        print("✅ Todas las dependencias instaladas correctamente!")
    
    # Descargar modelos de spaCy
    print("\n📦 Descargando modelos de spaCy...")
    try:
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        print("✅ Modelo spaCy en_core_web_sm descargado")
    except subprocess.CalledProcessError:
        print("❌ Error descargando modelo spaCy (opcional)")
    
    # Descargar datos de NLTK
    print("\n📦 Descargando datos de NLTK...")
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('vader_lexicon', quiet=True)
        print("✅ Datos de NLTK descargados")
    except Exception as e:
        print(f"❌ Error descargando datos NLTK: {e}")
    
    print("\n🎉 Instalación completada!")
    print("\n📋 Próximos pasos:")
    print("1. Copia .env.example a .env")
    print("2. Configura tus credenciales de Binance Testnet")
    print("3. Ejecuta: python src/main_bot.py")
    print("\n📖 Para más información, consulta el README.md")

if __name__ == "__main__":
    main()