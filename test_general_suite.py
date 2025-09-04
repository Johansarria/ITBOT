"""
🧪 SUITE DE PRUEBAS GENERALES - SISTEMA V3 DINÁMICO
==================================================

Pruebas integrales del sistema completo.

Autor: Johan Sarria
Fecha: 1 septiembre 2025
"""

import asyncio
import sys
import traceback
from datetime import datetime
import logging
import aiohttp
import json
import pandas as pd
import numpy as np

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeneralTestSuite:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results = []
    
    def test_result(self, test_name: str, success: bool, message: str = ""):
        """Registrar resultado de prueba"""
        if success:
            self.tests_passed += 1
            status = "✅ PASS"
            logger.info(f"✅ {test_name}: {message}")
        else:
            self.tests_failed += 1
            status = "❌ FAIL"
            logger.error(f"❌ {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "status": status,
            "success": success,
            "message": message
        })
        
        return success
    
    def test_imports(self):
        """Probar importación de módulos críticos"""
        logger.info("🔧 PRUEBA 1: Importación de módulos")
        
        try:
            # Importar config
            from config import get_settings
            settings = get_settings()
            self.test_result("Import config", True, "Configuración cargada")
            
            # Importar estrategias V3
            try:
                sys.path.append('/home/johan/itbot_linux/strategies')
                from v3_dynamic_system import V3DynamicSystem, MarketRegimeAnalyzer
                self.test_result("Import V3 Dynamic System", True, "Sistema V3 dinámico disponible")
            except ImportError as e:
                self.test_result("Import V3 Dynamic System", False, f"Error: {str(e)}")
            
            # Importar handlers
            try:
                from handlers.v3_dynamic_handlers import setup_v3_dynamic_handlers
                self.test_result("Import V3 Handlers", True, "Handlers V3 disponibles")
            except ImportError as e:
                self.test_result("Import V3 Handlers", False, f"Error: {str(e)}")
            
            return True
            
        except Exception as e:
            self.test_result("Import config", False, f"Error crítico: {str(e)}")
            return False
    
    def test_environment_variables(self):
        """Probar variables de entorno"""
        logger.info("🌍 PRUEBA 2: Variables de entorno")
        
        try:
            from config import get_settings
            settings = get_settings()
            
            # Verificar Telegram
            if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN != "DUMMY":
                self.test_result("Telegram Token", True, "Token configurado")
            else:
                self.test_result("Telegram Token", False, "Token no configurado")
            
            if settings.TELEGRAM_CHAT_ID and settings.TELEGRAM_CHAT_ID != 0:
                self.test_result("Telegram Chat ID", True, f"Chat ID: {settings.TELEGRAM_CHAT_ID}")
            else:
                self.test_result("Telegram Chat ID", False, "Chat ID no configurado")
            
            # Verificar Binance
            if settings.BINANCE_API_KEY and settings.BINANCE_API_KEY != "DUMMY":
                self.test_result("Binance API Key", True, "API Key configurada")
            else:
                self.test_result("Binance API Key", False, "API Key no configurada")
            
            if settings.BINANCE_SECRET_KEY and settings.BINANCE_SECRET_KEY != "DUMMY":
                self.test_result("Binance Secret Key", True, "Secret Key configurada")
            else:
                self.test_result("Binance Secret Key", False, "Secret Key no configurada")
            
            return True
            
        except Exception as e:
            self.test_result("Environment Variables", False, f"Error: {str(e)}")
            return False
    
    def test_v3_core_functionality(self):
        """Probar funcionalidad core del sistema V3"""
        logger.info("🎯 PRUEBA 3: Funcionalidad V3 Core")
        
        try:
            sys.path.append('/home/johan/itbot_linux/strategies')
            from v3_dynamic_system import MarketRegimeAnalyzer, MarketCondition, MarketRegime
            
            # Crear analizador
            analyzer = MarketRegimeAnalyzer()
            self.test_result("Create Analyzer", True, "Analizador creado")
            
            # Generar datos de prueba
            np.random.seed(42)
            dates = pd.date_range('2025-01-01', periods=100, freq='5T')
            
            # Datos de alta volatilidad
            high_vol_data = pd.DataFrame({
                'timestamp': dates,
                'close': 50000 + np.random.normal(0, 2000, 100).cumsum(),
                'high': 50000 + np.random.normal(500, 2000, 100).cumsum(),
                'low': 50000 + np.random.normal(-500, 2000, 100).cumsum(),
                'volume': np.random.uniform(1000000, 5000000, 100)
            })
            
            current_prices = {'BTC/USDT': 52000}
            
            # Analizar régimen
            condition = analyzer.analyze_regime(high_vol_data, current_prices)
            
            if condition.confidence > 0.5:
                self.test_result("Market Regime Analysis", True, 
                               f"Régimen: {condition.regime.value}, Confianza: {condition.confidence:.1%}")
            else:
                self.test_result("Market Regime Analysis", False, "Confianza muy baja")
            
            return True
            
        except Exception as e:
            self.test_result("V3 Core Functionality", False, f"Error: {str(e)}")
            traceback.print_exc()
            return False
    
    def test_docker_services(self):
        """Probar servicios Docker"""
        logger.info("🐳 PRUEBA 4: Servicios Docker")
        
        import subprocess
        
        try:
            # Verificar contenedores
            result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
            
            if result.returncode == 0:
                output = result.stdout
                services = ['itbot_redis', 'itbot_postgres_db', 'itbot_main', 'itbot_listener', 'itbot_worker', 'itbot_web']
                
                running_services = 0
                for service in services:
                    if service in output:
                        running_services += 1
                        self.test_result(f"Docker Service {service}", True, "Running")
                    else:
                        self.test_result(f"Docker Service {service}", False, "Not running")
                
                if running_services >= 4:  # Al menos 4 servicios críticos
                    self.test_result("Docker Services Overall", True, f"{running_services}/{len(services)} servicios corriendo")
                else:
                    self.test_result("Docker Services Overall", False, f"Solo {running_services}/{len(services)} servicios corriendo")
                
                return True
            else:
                self.test_result("Docker Services", False, "Docker no disponible")
                return False
                
        except Exception as e:
            self.test_result("Docker Services", False, f"Error: {str(e)}")
            return False
    
    def test_data_processing(self):
        """Probar procesamiento de datos"""
        logger.info("📊 PRUEBA 5: Procesamiento de datos")
        
        try:
            # Crear datos sintéticos para prueba
            dates = pd.date_range('2025-01-01', periods=100, freq='5T')
            test_data = pd.DataFrame({
                'timestamp': dates,
                'close': 50000 + np.random.normal(0, 1000, 100).cumsum(),
                'high': 51000 + np.random.normal(0, 1000, 100).cumsum(),
                'low': 49000 + np.random.normal(0, 1000, 100).cumsum(),
                'volume': np.random.uniform(1000000, 3000000, 100)
            })
            
            # Verificar integridad de datos
            if test_data.isnull().sum().sum() == 0:
                self.test_result("Data Integrity", True, "Sin valores nulos")
            else:
                self.test_result("Data Integrity", False, "Contiene valores nulos")
            
            # Verificar cálculos básicos
            test_data['returns'] = test_data['close'].pct_change()
            volatility = test_data['returns'].std() * np.sqrt(288)  # Volatilidad anualizada
            
            if 0.1 <= volatility <= 5.0:  # Volatilidad razonable
                self.test_result("Volatility Calculation", True, f"Volatilidad: {volatility:.2%}")
            else:
                self.test_result("Volatility Calculation", False, f"Volatilidad anómala: {volatility:.2%}")
            
            # Probar indicadores técnicos básicos
            test_data['sma_20'] = test_data['close'].rolling(20).mean()
            test_data['rsi'] = self._calculate_rsi(test_data['close'])
            
            if not test_data['sma_20'].iloc[-1] == 0 and not np.isnan(test_data['rsi'].iloc[-1]):
                self.test_result("Technical Indicators", True, "SMA y RSI calculados correctamente")
            else:
                self.test_result("Technical Indicators", False, "Error en cálculo de indicadores")
            
            return True
            
        except Exception as e:
            self.test_result("Data Processing", False, f"Error: {str(e)}")
            return False
    
    def _calculate_rsi(self, prices, period=14):
        """Calcular RSI simple para pruebas"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    async def test_telegram_connectivity(self):
        """Probar conectividad con Telegram (sin enviar mensajes)"""
        logger.info("📱 PRUEBA 6: Conectividad Telegram")
        
        try:
            from config import get_settings
            settings = get_settings()
            
            if settings.TELEGRAM_BOT_TOKEN == "DUMMY":
                self.test_result("Telegram Connectivity", False, "Token no configurado")
                return False
            
            # Probar conexión sin enviar mensajes
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/getMe"
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get('ok'):
                                bot_info = data.get('result', {})
                                self.test_result("Telegram Connectivity", True, 
                                               f"Bot: {bot_info.get('first_name', 'Unknown')}")
                                return True
                            else:
                                self.test_result("Telegram Connectivity", False, "API response not OK")
                        else:
                            self.test_result("Telegram Connectivity", False, f"HTTP {response.status}")
                except asyncio.TimeoutError:
                    self.test_result("Telegram Connectivity", False, "Timeout")
                except Exception as e:
                    self.test_result("Telegram Connectivity", False, f"Error: {str(e)}")
            
            return False
            
        except Exception as e:
            self.test_result("Telegram Connectivity", False, f"Error: {str(e)}")
            return False
    
    def generate_test_report(self):
        """Generar reporte final de pruebas"""
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests) * 100 if total_tests > 0 else 0
        
        logger.info("=" * 70)
        logger.info("🏁 REPORTE FINAL DE PRUEBAS GENERALES")
        logger.info("=" * 70)
        logger.info(f"📊 Total pruebas ejecutadas: {total_tests}")
        logger.info(f"✅ Pruebas exitosas: {self.tests_passed}")
        logger.info(f"❌ Pruebas fallidas: {self.tests_failed}")
        logger.info(f"📈 Tasa de éxito: {success_rate:.1f}%")
        logger.info("")
        
        if success_rate >= 80:
            logger.info("🎉 SISTEMA EN BUEN ESTADO - Listo para operaciones")
            status = "✅ APROBADO"
        elif success_rate >= 60:
            logger.info("⚠️ SISTEMA FUNCIONAL - Algunas mejoras requeridas")
            status = "⚠️ CONDICIONAL"
        else:
            logger.info("❌ SISTEMA REQUIERE ATENCIÓN - Problemas críticos detectados")
            status = "❌ REPROBADO"
        
        logger.info(f"🎯 Estado general: {status}")
        
        # Crear archivo de reporte
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"GENERAL_TEST_REPORT_{timestamp}.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "passed": self.tests_passed,
            "failed": self.tests_failed,
            "success_rate": success_rate,
            "status": status,
            "test_details": self.test_results
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Reporte guardado en: {report_file}")
        
        return success_rate >= 60

async def main():
    """Ejecutar suite completa de pruebas"""
    
    print("🧪 SUITE DE PRUEBAS GENERALES - SISTEMA V3 DINÁMICO")
    print("=" * 70)
    print(f"📅 Fecha: {datetime.now().strftime('%d de %B de %Y - %H:%M:%S')}")
    print("")
    
    suite = GeneralTestSuite()
    
    try:
        # Ejecutar pruebas secuencialmente
        tests = [
            suite.test_imports,
            suite.test_environment_variables,
            suite.test_v3_core_functionality,
            suite.test_docker_services,
            suite.test_data_processing,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                logger.error(f"Error en prueba {test.__name__}: {str(e)}")
                suite.test_result(test.__name__, False, f"Excepción: {str(e)}")
        
        # Prueba asíncrona de Telegram
        await suite.test_telegram_connectivity()
        
        # Generar reporte final
        success = suite.generate_test_report()
        
        if success:
            print("\n🎉 PRUEBAS GENERALES COMPLETADAS EXITOSAMENTE")
            print("🚀 Sistema listo para activación V3 dinámico")
        else:
            print("\n⚠️ ALGUNAS PRUEBAS FALLARON")
            print("🔧 Revisar logs y corregir problemas antes de activación")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error crítico en suite de pruebas: {str(e)}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(main())
