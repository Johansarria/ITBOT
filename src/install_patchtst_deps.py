#!/usr/bin/env python3
"""
Script de instalación de dependencias para PatchTST
"""

import subprocess
import sys

def install_dependencies():
    """Instalar todas las dependencias necesarias para PatchTST"""
    
    dependencies = [
        'torch>=2.0.0',
        'torchvision',
        'numpy>=1.21.0',
        'pandas>=1.3.0',
        'scikit-learn>=1.0.0',
        'transformers>=4.36.0',
        'huggingface-hub>=0.19.0',
        'matplotlib>=3.5.0',
        'seaborn>=0.11.0',
        'tqdm>=4.64.0',
        'yfinance>=0.2.0',  # Para obtener datos de cripto
        'ccxt>=4.0.0',      # Para datos de exchanges
        'ta>=0.10.0',       # Indicadores técnicos
    ]
    
    print("📦 Instalando dependencias para PatchTST...")
    print("="*50)
    
    for dependency in dependencies:
        try:
            print(f"Instalando {dependency}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dependency])
            print(f"✅ {dependency} instalado")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error instalando {dependency}: {e}")
            return False
    
    print("\n🎉 Todas las dependencias instaladas exitosamente!")
    return True

def verify_installation():
    """Verificar que todas las librerías están instaladas"""
    print("\n🔍 Verificando instalación...")
    
    try:
        import torch
        import numpy as np
        import pandas as pd
        import sklearn
        import transformers
        import matplotlib
        import yfinance
        import ccxt
        import ta
        
        print("✅ Todas las librerías están disponibles")
        
        # Info adicional
        print(f"\n📊 Versiones instaladas:")
        print(f"   PyTorch: {torch.__version__}")
        print(f"   NumPy: {np.__version__}")
        print(f"   Pandas: {pd.__version__}")
        print(f"   Scikit-learn: {sklearn.__version__}")
        print(f"   Transformers: {transformers.__version__}")
        
        # Verificar GPU
        if torch.cuda.is_available():
            print(f"   CUDA disponible: {torch.cuda.get_device_name(0)}")
        else:
            print("   CUDA no disponible, usando CPU")
            
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False

if __name__ == '__main__':
    print("🚀 Instalador de dependencias PatchTST para SICAR")
    print("="*60)
    
    if install_dependencies():
        if verify_installation():
            print("\n🎉 Instalación completada exitosamente!")
            print("\n📚 Puedes usar PatchTST ahora:")
            print("   python src/module_patchtst.py")
        else:
            print("\n❌ Verificación fallida")
    else:
        print("\n❌ Instalación fallida")