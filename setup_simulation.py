#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Configuración para la Simulación de Trading en Tiempo Real
Prepara el entorno, instala dependencias y verifica la configuración.
"""

import os
import sys
import subprocess
import json
import requests
from pathlib import Path
from datetime import datetime

class SimulationSetup:
    """Configurador de la simulación de trading"""
    
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.config_file = self.project_dir / "simulation_config.json"
        self.requirements_file = self.project_dir / "requirements_simulation.txt"
        self.log_dir = self.project_dir / "logs_simulation"
        self.reports_dir = self.project_dir / "reports_simulation"
        
    def print_header(self):
        """Imprime el encabezado del setup"""
        print("\n" + "="*70)
        print("🚀 CONFIGURACIÓN DE SIMULACIÓN DE TRADING EN TIEMPO REAL")
        print("="*70)
        print(f"📁 Directorio del proyecto: {self.project_dir}")
        print(f"⏰ Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
    
    def check_python_version(self):
        """Verifica la versión de Python"""
        print("\n🐍 Verificando versión de Python...")
        
        version = sys.version_info
        print(f"   Versión actual: {version.major}.{version.minor}.{version.micro}")
        
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("   ❌ Se requiere Python 3.8 o superior")
            return False
        else:
            print("   ✅ Versión de Python compatible")
            return True
    
    def create_directories(self):
        """Crea los directorios necesarios"""
        print("\n📁 Creando directorios...")
        
        directories = [
            self.log_dir,
            self.reports_dir,
            self.project_dir / "charts",
            self.project_dir / "data",
            self.project_dir / "backups"
        ]
        
        for directory in directories:
            try:
                directory.mkdir(exist_ok=True)
                print(f"   ✅ {directory.name}/")
            except Exception as e:
                print(f"   ❌ Error creando {directory}: {e}")
                return False
        
        return True
    
    def install_requirements(self):
        """Instala las dependencias requeridas"""
        print("\n📦 Instalando dependencias...")
        
        if not self.requirements_file.exists():
            print(f"   ❌ Archivo de requisitos no encontrado: {self.requirements_file}")
            return False
        
        try:
            # Actualizar pip primero
            print("   🔄 Actualizando pip...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # Instalar requisitos
            print("   📥 Instalando paquetes...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(self.requirements_file)],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                print("   ✅ Dependencias instaladas correctamente")
                return True
            else:
                print(f"   ❌ Error instalando dependencias: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error en la instalación: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            return False
    
    def verify_imports(self):
        """Verifica que las librerías críticas se puedan importar"""
        print("\n🔍 Verificando importaciones críticas...")
        
        critical_imports = [
            ('numpy', 'np'),
            ('pandas', 'pd'),
            ('matplotlib.pyplot', 'plt'),
            ('requests', None),
            ('websockets', None),
            ('asyncio', None),
            ('json', None),
            ('datetime', None)
        ]
        
        failed_imports = []
        
        for module, alias in critical_imports:
            try:
                if alias:
                    exec(f"import {module} as {alias}")
                else:
                    exec(f"import {module}")
                print(f"   ✅ {module}")
            except ImportError as e:
                print(f"   ❌ {module}: {e}")
                failed_imports.append(module)
            except Exception as e:
                print(f"   ⚠️  {module}: {e}")
        
        if failed_imports:
            print(f"\n   ❌ Falló la importación de: {', '.join(failed_imports)}")
            return False
        else:
            print("   ✅ Todas las importaciones críticas exitosas")
            return True
    
    def test_binance_connection(self):
        """Prueba la conexión con la API de Binance"""
        print("\n🌐 Probando conexión con Binance...")
        
        try:
            # Test de conectividad básica
            response = requests.get(
                "https://api.binance.com/api/v3/ping",
                timeout=10
            )
            
            if response.status_code == 200:
                print("   ✅ Conexión con Binance exitosa")
                
                # Test de datos de precio
                price_response = requests.get(
                    "https://api.binance.com/api/v3/ticker/price",
                    params={'symbol': 'BTCUSDT'},
                    timeout=10
                )
                
                if price_response.status_code == 200:
                    data = price_response.json()
                    price = float(data['price'])
                    print(f"   ✅ Precio de BTCUSDT: ${price:,.2f}")
                    return True
                else:
                    print(f"   ❌ Error obteniendo precio: {price_response.status_code}")
                    return False
            else:
                print(f"   ❌ Error de conexión: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print("   ❌ Timeout de conexión")
            return False
        except requests.exceptions.ConnectionError:
            print("   ❌ Error de conexión a internet")
            return False
        except Exception as e:
            print(f"   ❌ Error inesperado: {e}")
            return False
    
    def validate_config(self):
        """Valida el archivo de configuración"""
        print("\n⚙️  Validando configuración...")
        
        if not self.config_file.exists():
            print(f"   ❌ Archivo de configuración no encontrado: {self.config_file}")
            return False
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validaciones básicas
            required_sections = ['simulation', 'strategy', 'risk_management', 'costs']
            
            for section in required_sections:
                if section not in config:
                    print(f"   ❌ Sección faltante en configuración: {section}")
                    return False
                else:
                    print(f"   ✅ Sección {section} encontrada")
            
            # Validar parámetros críticos
            sim_config = config['simulation']
            if sim_config.get('initial_capital', 0) <= 0:
                print("   ❌ Capital inicial debe ser mayor a 0")
                return False
            
            if not sim_config.get('symbols'):
                print("   ❌ Debe especificar al menos un símbolo")
                return False
            
            print(f"   ✅ Capital inicial: ${sim_config['initial_capital']}")
            print(f"   ✅ Símbolos: {', '.join(sim_config['symbols'])}")
            
            return True
            
        except json.JSONDecodeError as e:
            print(f"   ❌ Error en formato JSON: {e}")
            return False
        except Exception as e:
            print(f"   ❌ Error validando configuración: {e}")
            return False
    
    def create_sample_env(self):
        """Crea un archivo .env de ejemplo"""
        print("\n📝 Creando archivo .env de ejemplo...")
        
        env_file = self.project_dir / ".env.simulation"
        
        env_content = """# Configuración de la Simulación de Trading
# Copiar a .env y completar con valores reales

# API de Binance (opcional para simulación)
BINANCE_API_KEY=tu_api_key_aqui
BINANCE_SECRET_KEY=tu_secret_key_aqui

# Configuración de Telegram (opcional)
TELEGRAM_BOT_TOKEN=tu_bot_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui

# Configuración de la simulación
SIMULATION_MODE=paper_trading
LOG_LEVEL=INFO
SAVE_CHARTS=true
REAL_TIME_VISUALIZATION=true

# Configuración de base de datos (opcional)
DATABASE_URL=sqlite:///simulation.db

# Configuración de alertas
ALERT_ENABLED=true
ALERT_LARGE_LOSS_PCT=3.0
ALERT_DRAWDOWN_THRESHOLD=8.0
"""
        
        try:
            with open(env_file, 'w', encoding='utf-8') as f:
                f.write(env_content)
            print(f"   ✅ Archivo creado: {env_file.name}")
            return True
        except Exception as e:
            print(f"   ❌ Error creando .env: {e}")
            return False
    
    def run_setup(self):
        """Ejecuta el setup completo"""
        self.print_header()
        
        steps = [
            ("Verificar Python", self.check_python_version),
            ("Crear directorios", self.create_directories),
            ("Instalar dependencias", self.install_requirements),
            ("Verificar importaciones", self.verify_imports),
            ("Probar conexión Binance", self.test_binance_connection),
            ("Validar configuración", self.validate_config),
            ("Crear archivo .env", self.create_sample_env)
        ]
        
        results = []
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            try:
                result = step_func()
                results.append((step_name, result))
                if not result:
                    print(f"   ⚠️  {step_name} falló, pero continuando...")
            except Exception as e:
                print(f"   ❌ Error en {step_name}: {e}")
                results.append((step_name, False))
        
        # Resumen final
        print("\n" + "="*70)
        print("📊 RESUMEN DEL SETUP")
        print("="*70)
        
        success_count = 0
        for step_name, success in results:
            status = "✅" if success else "❌"
            print(f"   {status} {step_name}")
            if success:
                success_count += 1
        
        print(f"\n📈 Éxito: {success_count}/{len(results)} pasos completados")
        
        if success_count == len(results):
            print("\n🎉 ¡Setup completado exitosamente!")
            print("\n🚀 Para ejecutar la simulación:")
            print("   python real_time_trading_simulator.py")
        elif success_count >= len(results) * 0.7:  # 70% de éxito
            print("\n⚠️  Setup completado con advertencias")
            print("   La simulación debería funcionar, pero revisa los errores")
        else:
            print("\n❌ Setup falló. Revisa los errores antes de continuar")
        
        print("\n" + "="*70)
        
        return success_count == len(results)

def main():
    """Función principal"""
    setup = SimulationSetup()
    
    try:
        success = setup.run_setup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error fatal en setup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()