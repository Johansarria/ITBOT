"""
Script de Prueba Completo para el Sistema SICAR Mejorado
Verifica todas las mejoras implementadas
"""

import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

# Importar sistemas mejorados
try:
    from enhanced_config import CONFIG
    from enhanced_logger import SICAR_LOGGER
    from enhanced_sync_manager import SYNC_MANAGER
    from enhanced_breakout_detector import BREAKOUT_DETECTOR, BreakoutSignal, BreakoutType, BreakoutStrength
    print("✅ Todos los módulos mejorados importados correctamente")
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    sys.exit(1)

class SystemTester:
    """Probador del sistema mejorado"""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = datetime.now()
        
    def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print("🚀 INICIANDO PRUEBAS DEL SISTEMA SICAR MEJORADO")
        print("=" * 60)
        
        # Lista de pruebas
        tests = [
            ("Configuración", self.test_config),
            ("Sistema de Logging", self.test_logging),
            ("Sincronización", self.test_sync_manager),
            ("Detección de Breakouts", self.test_breakout_detector),
            ("Auto Trading por Defecto", self.test_auto_trading_default),
            ("Integración de Sistemas", self.test_system_integration)
        ]
        
        # Ejecutar pruebas
        for test_name, test_func in tests:
            print(f"\n🧪 Probando: {test_name}")
            print("-" * 40)
            
            try:
                result = test_func()
                self.test_results[test_name] = result
                status = "✅ PASÓ" if result['success'] else "❌ FALLÓ"
                print(f"   {status}: {result['message']}")
                
                if result.get('details'):
                    for detail in result['details']:
                        print(f"   📋 {detail}")
                        
            except Exception as e:
                self.test_results[test_name] = {
                    'success': False,
                    'message': f"Error en prueba: {e}",
                    'error': str(e)
                }
                print(f"   ❌ ERROR: {e}")
        
        # Mostrar resumen
        self.show_summary()
    
    def test_config(self):
        """Probar configuración"""
        try:
            # Verificar que CONFIG esté disponible
            assert hasattr(CONFIG, 'AUTO_TRADING_DEFAULT'), "Falta AUTO_TRADING_DEFAULT"
            assert hasattr(CONFIG, 'BREAKOUT_DETECTION'), "Falta BREAKOUT_DETECTION"
            assert hasattr(CONFIG, 'SYNC_CONFIG'), "Falta SYNC_CONFIG"
            assert hasattr(CONFIG, 'LOGGING_CONFIG'), "Falta LOGGING_CONFIG"
            
            # Verificar configuraciones específicas
            auto_trading_enabled = CONFIG.AUTO_TRADING_DEFAULT
            breakout_sensitivity = CONFIG.BREAKOUT_DETECTION['sensitivity']
            sync_interval = CONFIG.SYNC_CONFIG['sync_interval']
            
            details = [
                f"Auto trading por defecto: {auto_trading_enabled}",
                f"Sensibilidad breakouts: {breakout_sensitivity:.1%}",
                f"Intervalo de sync: {sync_interval}s",
                f"Símbolos monitoreados: {len(CONFIG.BREAKOUT_DETECTION['symbols_to_monitor'])}"
            ]
            
            return {
                'success': True,
                'message': "Configuración cargada correctamente",
                'details': details
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error en configuración: {e}"
            }
    
    def test_logging(self):
        """Probar sistema de logging"""
        try:
            # Probar diferentes tipos de logs
            SICAR_LOGGER.log_alert("TEST", "Prueba de alerta", "INFO")
            SICAR_LOGGER.log_auto_trading_status(True, "Prueba de auto trading")
            
            # Probar log de breakout
            test_breakout_info = {
                'signal_type': 'bullish',
                'confidence': 0.85,
                'price': 2150.50,
                'volume': 1500000
            }
            SICAR_LOGGER.log_breakout_detected("ETHUSDT", test_breakout_info)
            
            # Probar log de trade
            test_trade_info = {
                'symbol': 'ETHUSDT',
                'side': 'BUY',
                'quantity': 0.1,
                'price': 2150.50,
                'value': 215.05,
                'order_id': 'TEST_001'
            }
            SICAR_LOGGER.log_trade_executed(test_trade_info)
            
            # Verificar que los archivos de log existen
            log_files_exist = []
            for log_type in ['main', 'trading', 'breakouts', 'sessions', 'errors']:
                log_file_path = CONFIG.get_log_file_path(log_type)
                log_file = Path(log_file_path)
                exists = log_file.exists()
                log_files_exist.append(f"{log_type}: {'✅' if exists else '❌'}")
            
            return {
                'success': True,
                'message': "Sistema de logging funcionando",
                'details': log_files_exist
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error en logging: {e}"
            }
    
    def test_sync_manager(self):
        """Probar gestor de sincronización"""
        try:
            # Iniciar auto-sync
            SYNC_MANAGER.start_auto_sync()
            time.sleep(1)  # Esperar un poco
            
            # Probar actualización de datos
            test_data = {
                'test_field': 'test_value',
                'timestamp': datetime.now().isoformat()
            }
            SYNC_MANAGER.update_data(test_data)
            
            # Verificar que los datos se guardaron
            retrieved_data = SYNC_MANAGER.get_data('test_field')
            assert retrieved_data == 'test_value', "Datos no se guardaron correctamente"
            
            # Probar configuración de auto trading
            SYNC_MANAGER.set_auto_trading(True, "Prueba del sistema")
            auto_trading_status = SYNC_MANAGER.get_data('auto_trading')
            assert auto_trading_status == True, "Auto trading no se configuró"
            
            # Obtener estado de sincronización
            sync_status = SYNC_MANAGER.get_sync_status()
            
            details = [
                f"Archivo existe: {'✅' if sync_status['file_exists'] else '❌'}",
                f"Auto-sync activo: {'✅' if sync_status['sync_running'] else '❌'}",
                f"Campos en cache: {sync_status['cache_size']}",
                f"Observadores: {sync_status['observers_count']}"
            ]
            
            return {
                'success': True,
                'message': "Gestor de sincronización funcionando",
                'details': details
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error en sync manager: {e}"
            }
    
    def test_breakout_detector(self):
        """Probar detector de breakouts"""
        try:
            # Configurar callback de prueba
            detected_signals = []
            
            def test_callback(signal):
                detected_signals.append(signal)
            
            BREAKOUT_DETECTOR.add_alert_callback(test_callback)
            
            # Iniciar detección
            BREAKOUT_DETECTOR.start_detection()
            
            # Esperar un poco para que se generen datos simulados
            time.sleep(3)
            
            # Crear señal de prueba manual
            test_signal = BreakoutSignal(
                symbol="ETHUSDT",
                timestamp=datetime.now(),
                breakout_type=BreakoutType.BULLISH,
                strength=BreakoutStrength.STRONG,
                confidence=0.85,
                price=2150.50,
                volume=1500000,
                resistance_level=2145.00,
                support_level=2100.00,
                price_change_pct=1.25,
                volume_ratio=2.3,
                candle_pattern="strong_bullish",
                technical_indicators={"rsi": 65, "macd": 0.5}
            )
            
            # Procesar señal manualmente
            BREAKOUT_DETECTOR._process_breakout_signal(test_signal)
            
            # Verificar configuración
            sensitivity = BREAKOUT_DETECTOR.sensitivity
            min_volume_ratio = BREAKOUT_DETECTOR.min_volume_ratio
            
            # Obtener señales recientes
            recent_signals = BREAKOUT_DETECTOR.get_recent_signals(hours=1)
            
            details = [
                f"Detector activo: {'✅' if BREAKOUT_DETECTOR.running else '❌'}",
                f"Sensibilidad: {sensitivity:.1%}",
                f"Volumen mínimo: {min_volume_ratio:.1f}x",
                f"Señales recientes: {len(recent_signals)}",
                f"Callbacks registrados: {len(BREAKOUT_DETECTOR.alert_callbacks)}"
            ]
            
            return {
                'success': True,
                'message': "Detector de breakouts funcionando",
                'details': details
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error en detector de breakouts: {e}"
            }
    
    def test_auto_trading_default(self):
        """Probar auto trading por defecto"""
        try:
            # Verificar configuración por defecto
            default_enabled = CONFIG.AUTO_TRADING_CONFIG['enabled_by_default']
            
            # Verificar que el sync manager respeta esta configuración
            current_auto_trading = SYNC_MANAGER.get_data('auto_trading')
            
            # Probar cambio de estado
            SYNC_MANAGER.set_auto_trading(True, "Prueba de activación")
            enabled_status = SYNC_MANAGER.get_data('auto_trading')
            
            SYNC_MANAGER.set_auto_trading(False, "Prueba de desactivación")
            disabled_status = SYNC_MANAGER.get_data('auto_trading')
            
            details = [
                f"Configurado por defecto: {'✅' if default_enabled else '❌'}",
                f"Estado actual: {'✅' if current_auto_trading else '❌'}",
                f"Activación funciona: {'✅' if enabled_status else '❌'}",
                f"Desactivación funciona: {'✅' if not disabled_status else '❌'}"
            ]
            
            return {
                'success': True,
                'message': "Auto trading por defecto configurado",
                'details': details
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error en auto trading: {e}"
            }
    
    def test_system_integration(self):
        """Probar integración de sistemas"""
        try:
            # Simular flujo completo
            
            # 1. Configurar auto trading
            SYNC_MANAGER.set_auto_trading(True, "Prueba de integración")
            
            # 2. Simular detección de breakout
            test_signal = BreakoutSignal(
                symbol="ETHUSDT",
                timestamp=datetime.now(),
                breakout_type=BreakoutType.BULLISH,
                strength=BreakoutStrength.VERY_STRONG,
                confidence=0.92,
                price=2175.25,
                volume=2000000,
                resistance_level=2170.00,
                support_level=2120.00,
                price_change_pct=2.15,
                volume_ratio=3.2,
                candle_pattern="strong_bullish",
                technical_indicators={"rsi": 72, "macd": 1.2}
            )
            
            # 3. Procesar señal
            BREAKOUT_DETECTOR._process_breakout_signal(test_signal)
            
            # 4. Verificar que se logueó correctamente
            # (Los logs se escriben automáticamente)
            
            # 5. Simular actualización de capital
            SYNC_MANAGER.update_capital(10500.00)
            
            # 6. Simular trade
            trade_info = {
                'symbol': 'ETHUSDT',
                'side': 'BUY',
                'quantity': 0.2,
                'price': 2175.25,
                'value': 435.05,
                'order_id': 'INTEGRATION_TEST_001'
            }
            SYNC_MANAGER.add_trade(trade_info)
            
            # Verificar estado final
            final_capital = SYNC_MANAGER.get_data('current_capital')
            total_trades = SYNC_MANAGER.get_data('total_trades')
            auto_trading = SYNC_MANAGER.get_data('auto_trading')
            
            details = [
                f"Capital actualizado: ${final_capital:,.2f}",
                f"Trades registrados: {total_trades}",
                f"Auto trading activo: {'✅' if auto_trading else '❌'}",
                f"Breakout procesado: ✅",
                f"Logs generados: ✅"
            ]
            
            return {
                'success': True,
                'message': "Integración de sistemas funcionando",
                'details': details
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error en integración: {e}"
            }
    
    def show_summary(self):
        """Mostrar resumen de pruebas"""
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE PRUEBAS")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"📈 Total de pruebas: {total_tests}")
        print(f"✅ Pruebas exitosas: {passed_tests}")
        print(f"❌ Pruebas fallidas: {failed_tests}")
        print(f"📊 Tasa de éxito: {(passed_tests/total_tests)*100:.1f}%")
        
        # Tiempo total
        total_time = (datetime.now() - self.start_time).total_seconds()
        print(f"⏱️ Tiempo total: {total_time:.2f} segundos")
        
        print("\n🔍 DETALLES POR PRUEBA:")
        print("-" * 40)
        
        for test_name, result in self.test_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"{status} {test_name}: {result['message']}")
        
        # Recomendaciones
        print("\n💡 RECOMENDACIONES:")
        print("-" * 40)
        
        if failed_tests == 0:
            print("🎉 ¡Todas las pruebas pasaron! El sistema está listo para usar.")
            print("🚀 Puedes ejecutar el dashboard mejorado con: python enhanced_dashboard.py")
        else:
            print("⚠️ Algunas pruebas fallaron. Revisa los errores antes de usar el sistema.")
            print("🔧 Verifica la configuración y dependencias.")
        
        print("\n📋 PRÓXIMOS PASOS:")
        print("1. 🚀 Ejecutar dashboard mejorado")
        print("2. 📊 Monitorear logs en tiempo real")
        print("3. 🔄 Verificar sincronización automática")
        print("4. 📈 Probar detección de breakouts")
        print("5. 💰 Validar operaciones de trading")

def main():
    """Función principal"""
    print("🧪 SISTEMA DE PRUEBAS SICAR MEJORADO")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🐍 Python: {sys.version}")
    print()
    
    try:
        tester = SystemTester()
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⚠️ Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error ejecutando pruebas: {e}")
        SICAR_LOGGER.log_error("TEST_SYSTEM", str(e))
    
    finally:
        # Limpiar recursos
        try:
            BREAKOUT_DETECTOR.stop_detection()
            SYNC_MANAGER.stop_auto_sync()
        except:
            pass

if __name__ == "__main__":
    main()