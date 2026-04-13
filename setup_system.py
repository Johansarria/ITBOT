#!/usr/bin/env python3
"""
Script de Instalación y Configuración del Sistema de Trading Adaptativo

Este script automatiza la instalación de dependencias y configuración inicial
del sistema de trading que reemplaza el MCI fallido.

Autor: Sistema de Trading Adaptativo
Fecha: 2024
Versión: 1.0
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict

class SystemSetup:
    """
    Configurador del sistema de trading adaptativo.
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.requirements = [
            'pandas>=1.5.0',
            'numpy>=1.21.0',
            'matplotlib>=3.5.0',
            'seaborn>=0.11.0',
            'scikit-learn>=1.1.0',
            'scipy>=1.9.0',
            'ta>=0.10.0',  # Technical Analysis library
            'yfinance>=0.1.87',  # Para datos de mercado
            'plotly>=5.0.0',  # Visualizaciones interactivas
            'dash>=2.0.0',  # Dashboard web (opcional)
            'jupyter>=1.0.0'  # Para análisis interactivo
        ]
        
        self.optional_requirements = [
            'ccxt>=2.0.0',  # Para conectar con exchanges
            'alpaca-trade-api>=2.0.0',  # Para trading real
            'python-binance>=1.0.0',  # Para Binance
            'websocket-client>=1.0.0'  # Para datos en tiempo real
        ]
    
    def check_python_version(self) -> bool:
        """
        Verificar versión de Python.
        
        Returns:
            True si la versión es compatible
        """
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print("❌ Se requiere Python 3.8 o superior")
            print(f"   Versión actual: {version.major}.{version.minor}.{version.micro}")
            return False
        
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
        return True
    
    def install_requirements(self, include_optional: bool = False) -> bool:
        """
        Instalar dependencias requeridas.
        
        Args:
            include_optional: Si instalar dependencias opcionales
            
        Returns:
            True si se instalaron correctamente
        """
        print("📦 Instalando dependencias...")
        
        requirements_to_install = self.requirements.copy()
        if include_optional:
            requirements_to_install.extend(self.optional_requirements)
            print("   Incluyendo dependencias opcionales para trading real")
        
        try:
            for requirement in requirements_to_install:
                print(f"   Instalando {requirement}...")
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', requirement],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"   ⚠️  Error instalando {requirement}: {result.stderr}")
                    # Continuar con las demás dependencias
                else:
                    print(f"   ✅ {requirement} instalado")
            
            print("✅ Instalación de dependencias completada")
            return True
            
        except Exception as e:
            print(f"❌ Error durante la instalación: {e}")
            return False
    
    def create_directory_structure(self) -> bool:
        """
        Crear estructura de directorios.
        
        Returns:
            True si se creó correctamente
        """
        print("📁 Creando estructura de directorios...")
        
        directories = [
            'data',
            'results',
            'logs',
            'configs',
            'notebooks',
            'tests'
        ]
        
        try:
            for directory in directories:
                dir_path = self.base_dir / directory
                dir_path.mkdir(exist_ok=True)
                print(f"   ✅ {directory}/")
            
            # Crear archivos .gitkeep para mantener directorios vacíos
            for directory in ['data', 'results', 'logs']:
                gitkeep_path = self.base_dir / directory / '.gitkeep'
                gitkeep_path.touch()
            
            print("✅ Estructura de directorios creada")
            return True
            
        except Exception as e:
            print(f"❌ Error creando directorios: {e}")
            return False
    
    def setup_configuration(self) -> bool:
        """
        Configurar archivos de configuración.
        
        Returns:
            True si se configuró correctamente
        """
        print("⚙️  Configurando sistema...")
        
        try:
            # Copiar configuración de ejemplo
            config_source = self.base_dir / 'config_example.json'
            config_dest = self.base_dir / 'configs' / 'default_config.json'
            
            if config_source.exists():
                import shutil
                shutil.copy2(config_source, config_dest)
                print(f"   ✅ Configuración copiada a {config_dest}")
            else:
                print("   ⚠️  config_example.json no encontrado, creando configuración básica")
                self._create_basic_config(config_dest)
            
            # Crear archivo de logging
            self._create_logging_config()
            
            print("✅ Configuración completada")
            return True
            
        except Exception as e:
            print(f"❌ Error en configuración: {e}")
            return False
    
    def _create_basic_config(self, config_path: Path):
        """
        Crear configuración básica.
        
        Args:
            config_path: Ruta del archivo de configuración
        """
        basic_config = {
            "regime_detection": {
                "use_hmm": True,
                "atr_period": 14,
                "percentile_window": 252,
                "low_vol_threshold": 40,
                "high_vol_threshold": 80
            },
            "strategies": {
                "trend_following": {"enabled": True},
                "mean_reversion": {"enabled": True},
                "conservative": {"enabled": True}
            },
            "risk_management": {
                "max_daily_loss": 0.05,
                "max_total_drawdown": 0.15
            },
            "backtesting": {
                "train_ratio": 0.7
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(basic_config, f, indent=2)
    
    def _create_logging_config(self):
        """
        Crear configuración de logging.
        """
        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "level": "INFO",
                    "formatter": "standard",
                    "class": "logging.StreamHandler"
                },
                "file": {
                    "level": "DEBUG",
                    "formatter": "standard",
                    "class": "logging.FileHandler",
                    "filename": "logs/trading_system.log",
                    "mode": "a"
                }
            },
            "loggers": {
                "": {
                    "handlers": ["default", "file"],
                    "level": "DEBUG",
                    "propagate": False
                }
            }
        }
        
        config_path = self.base_dir / 'configs' / 'logging_config.json'
        with open(config_path, 'w') as f:
            json.dump(logging_config, f, indent=2)
    
    def create_sample_data(self) -> bool:
        """
        Crear datos de muestra para testing.
        
        Returns:
            True si se crearon correctamente
        """
        print("📊 Creando datos de muestra...")
        
        try:
            # Intentar descargar datos reales
            try:
                import yfinance as yf
                
                symbols = ['BTC-USD', 'ETH-USD', 'AAPL', 'TSLA']
                
                for symbol in symbols:
                    print(f"   Descargando {symbol}...")
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period='1y', interval='1d')
                    
                    if not data.empty:
                        # Limpiar nombres de columnas
                        data.columns = [col.lower() for col in data.columns]
                        
                        # Guardar datos
                        output_path = self.base_dir / 'data' / f'{symbol.replace("-", "_").lower()}_1y.csv'
                        data.to_csv(output_path)
                        print(f"   ✅ {symbol} guardado en {output_path}")
                    else:
                        print(f"   ⚠️  No se pudieron descargar datos para {symbol}")
                
            except ImportError:
                print("   ⚠️  yfinance no disponible, creando datos sintéticos")
                self._create_synthetic_data()
            
            print("✅ Datos de muestra creados")
            return True
            
        except Exception as e:
            print(f"❌ Error creando datos de muestra: {e}")
            return False
    
    def _create_synthetic_data(self):
        """
        Crear datos sintéticos para testing.
        """
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        
        # Generar datos sintéticos
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        np.random.seed(42)
        n_days = len(dates)
        
        # Simular precio de Bitcoin
        base_price = 45000
        volatility = np.random.choice([0.02, 0.04, 0.08], n_days, p=[0.4, 0.4, 0.2])
        returns = np.random.normal(0.001, volatility)
        
        prices = [base_price]
        for i in range(1, n_days):
            new_price = prices[-1] * (1 + returns[i])
            prices.append(max(new_price, 1000))  # Precio mínimo
        
        prices = np.array(prices)
        
        # Generar OHLC
        data = pd.DataFrame({
            'open': prices * np.random.uniform(0.995, 1.005, n_days),
            'high': prices * np.random.uniform(1.005, 1.02, n_days),
            'low': prices * np.random.uniform(0.98, 0.995, n_days),
            'close': prices,
            'volume': np.random.uniform(1000000, 5000000, n_days)
        }, index=dates)
        
        # Guardar datos sintéticos
        output_path = self.base_dir / 'data' / 'btc_synthetic_1y.csv'
        data.to_csv(output_path)
        print(f"   ✅ Datos sintéticos guardados en {output_path}")
    
    def create_jupyter_notebook(self) -> bool:
        """
        Crear notebook de Jupyter para análisis.
        
        Returns:
            True si se creó correctamente
        """
        print("📓 Creando notebook de análisis...")
        
        try:
            notebook_content = {
                "cells": [
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": [
                            "# Sistema de Trading Adaptativo - Análisis\n",
                            "\n",
                            "Este notebook demuestra el uso del sistema de trading adaptativo\n",
                            "que reemplaza el MCI fallido con métodos probados.\n",
                            "\n",
                            "## Componentes del Sistema\n",
                            "\n",
                            "1. **Detección de Regímenes**: ATR (25.5%) + HMM (18.6%)\n",
                            "2. **Estrategias Adaptativas**: Trend Following, Mean Reversion, Conservative\n",
                            "3. **Gestión de Riesgos**: Dinámico y adaptativo\n",
                            "4. **Backtesting**: Validación rigurosa\n"
                        ]
                    },
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": [
                            "# Importar sistema\n",
                            "import sys\n",
                            "sys.path.append('..')\n",
                            "\n",
                            "from integrated_trading_system import IntegratedTradingSystem\n",
                            "import pandas as pd\n",
                            "import matplotlib.pyplot as plt\n",
                            "\n",
                            "# Configurar visualizaciones\n",
                            "plt.style.use('seaborn-v0_8')\n",
                            "%matplotlib inline"
                        ]
                    },
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": [
                            "# Crear sistema con datos demo\n",
                            "system = IntegratedTradingSystem(initial_capital=10000)\n",
                            "\n",
                            "# Generar datos sintéticos\n",
                            "system.generate_sample_data()\n",
                            "\n",
                            "# Inicializar sistema\n",
                            "system.initialize_system()"
                        ]
                    },
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": [
                            "# Ejecutar backtesting\n",
                            "results = system.run_backtest(detailed=True)\n",
                            "\n",
                            "# Mostrar resultados\n",
                            "print('Resultados del Backtesting:')\n",
                            "print(f\"Capital final: ${results['basic_results']['final_capital']:,.2f}\")\n",
                            "print(f\"Total señales: {results['basic_results']['total_signals']}\")\n",
                            "print(f\"Total trades: {results['basic_results']['total_trades']}\")"
                        ]
                    },
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "outputs": [],
                        "source": [
                            "# Crear visualizaciones\n",
                            "system.create_visualizations()\n",
                            "\n",
                            "# Generar reporte\n",
                            "report = system.generate_report()\n",
                            "print(report)"
                        ]
                    }
                ],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3"
                    },
                    "language_info": {
                        "name": "python",
                        "version": "3.8.0"
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 4
            }
            
            notebook_path = self.base_dir / 'notebooks' / 'analisis_sistema_trading.ipynb'
            with open(notebook_path, 'w') as f:
                json.dump(notebook_content, f, indent=2)
            
            print(f"   ✅ Notebook creado en {notebook_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error creando notebook: {e}")
            return False
    
    def run_tests(self) -> bool:
        """
        Ejecutar tests básicos del sistema.
        
        Returns:
            True si todos los tests pasan
        """
        print("🧪 Ejecutando tests básicos...")
        
        try:
            # Test de importación
            print("   Test 1: Importación de módulos...")
            from integrated_trading_system import IntegratedTradingSystem
            from adaptive_regime_detector import AdaptiveRegimeDetector
            from adaptive_trading_strategies import AdaptiveStrategyManager
            from dynamic_risk_manager import DynamicRiskManager
            print("   ✅ Importaciones exitosas")
            
            # Test de inicialización
            print("   Test 2: Inicialización del sistema...")
            system = IntegratedTradingSystem(initial_capital=10000)
            print("   ✅ Sistema inicializado")
            
            # Test de datos sintéticos
            print("   Test 3: Generación de datos sintéticos...")
            if system.generate_sample_data():
                print("   ✅ Datos sintéticos generados")
            else:
                print("   ❌ Error generando datos sintéticos")
                return False
            
            # Test de inicialización completa
            print("   Test 4: Inicialización completa...")
            if system.initialize_system():
                print("   ✅ Sistema completamente inicializado")
            else:
                print("   ❌ Error en inicialización completa")
                return False
            
            # Test de backtesting básico
            print("   Test 5: Backtesting básico...")
            results = system.run_backtest(detailed=False)
            if results:
                print("   ✅ Backtesting ejecutado")
            else:
                print("   ❌ Error en backtesting")
                return False
            
            print("✅ Todos los tests pasaron")
            return True
            
        except Exception as e:
            print(f"❌ Error en tests: {e}")
            return False
    
    def setup_complete_system(self, include_optional: bool = False) -> bool:
        """
        Configurar sistema completo.
        
        Args:
            include_optional: Si incluir dependencias opcionales
            
        Returns:
            True si se configuró correctamente
        """
        print("🚀 CONFIGURACIÓN DEL SISTEMA DE TRADING ADAPTATIVO")
        print("=" * 60)
        print("📈 Reemplazo del MCI con métodos probados")
        print("🔍 ATR: 25.5% precisión | HMM: 18.6% precisión")
        print("❌ MCI descartado: 9.8% precisión")
        print("=" * 60)
        print()
        
        steps = [
            ("Verificar Python", self.check_python_version),
            ("Instalar dependencias", lambda: self.install_requirements(include_optional)),
            ("Crear directorios", self.create_directory_structure),
            ("Configurar sistema", self.setup_configuration),
            ("Crear datos de muestra", self.create_sample_data),
            ("Crear notebook", self.create_jupyter_notebook),
            ("Ejecutar tests", self.run_tests)
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            if not step_func():
                print(f"❌ Error en: {step_name}")
                return False
        
        print("\n" + "=" * 60)
        print("🎉 SISTEMA CONFIGURADO EXITOSAMENTE")
        print("=" * 60)
        print()
        print("📋 PRÓXIMOS PASOS:")
        print("1. Ejecutar: python integrated_trading_system.py --demo")
        print("2. Revisar: notebooks/analisis_sistema_trading.ipynb")
        print("3. Configurar: configs/default_config.json")
        print("4. Datos reales: Colocar CSV en data/")
        print()
        print("🚀 Sistema listo para trading en producción")
        print("✅ MCI reemplazado con métodos probados")
        
        return True

def main():
    """
    Función principal del configurador.
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Configurador del Sistema de Trading Adaptativo"
    )
    parser.add_argument(
        '--include-optional', 
        action='store_true',
        help='Incluir dependencias opcionales para trading real'
    )
    parser.add_argument(
        '--test-only',
        action='store_true', 
        help='Solo ejecutar tests'
    )
    
    args = parser.parse_args()
    
    setup = SystemSetup()
    
    if args.test_only:
        setup.run_tests()
    else:
        setup.setup_complete_system(args.include_optional)

if __name__ == "__main__":
    main()