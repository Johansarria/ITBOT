#!/usr/bin/env python3
"""
Test de Integración DRL + Paper Trading SICAR
Prueba completa del sistema integrado DRL con paper trading.
"""

import logging
import time
import json
from datetime import datetime
from typing import Dict, List, Any
import numpy as np

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_drl_integration():
    """
    Ejecuta pruebas completas de la integración DRL + Paper Trading.
    
    Returns:
        Dict con resultados de las pruebas
    """
    print("🚀 INICIANDO PRUEBAS DE INTEGRACIÓN DRL + PAPER TRADING")
    print("=" * 60)
    
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {},
        'overall_success': False,
        'errors': []
    }
    
    try:
        # TEST 1: Importar y crear adaptador DRL
        print("\n📋 TEST 1: Creación del Adaptador DRL")
        try:
            from drl_paper_trading_adapter import DRLPaperTradingAdapter, DRLTradingConfig
            
            config = DRLTradingConfig(
                state_dim=20,
                action_dim=3,
                learning_rate=0.0003,
                max_position_size=0.1,
                min_confidence_threshold=0.5
            )
            
            adapter = DRLPaperTradingAdapter(
                initial_capital=10000.0,
                symbols=['BTCUSDT', 'ETHUSDT'],
                config=config
            )
            
            test_results['tests']['drl_adapter_creation'] = {
                'status': 'PASSED',
                'message': 'Adaptador DRL creado exitosamente',
                'details': {
                    'initial_capital': adapter.paper_engine.initial_capital,
                    'symbols': adapter.symbols,
                    'state_dim': adapter.config.state_dim,
                    'action_dim': adapter.config.action_dim
                }
            }
            print("   ✅ Adaptador DRL creado exitosamente")
            
        except Exception as e:
            test_results['tests']['drl_adapter_creation'] = {
                'status': 'FAILED',
                'message': f'Error creando adaptador DRL: {e}',
                'error': str(e)
            }
            test_results['errors'].append(f"TEST 1 FAILED: {e}")
            print(f"   ❌ Error: {e}")
            return test_results
        
        # TEST 2: Crear sistema integrado
        print("\n📋 TEST 2: Sistema Integrado DRL + Paper Trading")
        try:
            from paper_trading_system import DRLIntegratedPaperTrading
            
            integrated_system = DRLIntegratedPaperTrading(
                initial_capital=10000.0,
                symbols=['BTCUSDT', 'ETHUSDT', 'ADAUSDT'],
                enable_drl=True,
                enable_manual_trading=True
            )
            
            # Verificar componentes
            assert integrated_system.paper_engine is not None
            assert integrated_system.drl_adapter is not None
            assert integrated_system.trading_mode == 'hybrid'
            
            test_results['tests']['integrated_system_creation'] = {
                'status': 'PASSED',
                'message': 'Sistema integrado creado exitosamente',
                'details': {
                    'trading_mode': integrated_system.trading_mode,
                    'drl_enabled': integrated_system.enable_drl,
                    'manual_enabled': integrated_system.enable_manual_trading,
                    'symbols_count': len(integrated_system.symbols)
                }
            }
            print("   ✅ Sistema integrado creado exitosamente")
            
        except Exception as e:
            test_results['tests']['integrated_system_creation'] = {
                'status': 'FAILED',
                'message': f'Error creando sistema integrado: {e}',
                'error': str(e)
            }
            test_results['errors'].append(f"TEST 2 FAILED: {e}")
            print(f"   ❌ Error: {e}")
            return test_results
        
        # TEST 3: Procesamiento de datos de mercado
        print("\n📋 TEST 3: Procesamiento de Datos de Mercado")
        try:
            # Simular datos de mercado
            market_data = {
                'BTCUSDT': 45000.0,
                'ETHUSDT': 3000.0,
                'ADAUSDT': 1.2
            }
            
            # Procesar datos
            integrated_system.process_market_update(market_data)
            
            # Verificar que se procesaron
            portfolio_summary = integrated_system.get_integrated_summary()
            assert 'current_capital' in portfolio_summary
            assert 'trading_mode' in portfolio_summary
            
            test_results['tests']['market_data_processing'] = {
                'status': 'PASSED',
                'message': 'Datos de mercado procesados correctamente',
                'details': {
                    'market_data_symbols': list(market_data.keys()),
                    'current_capital': portfolio_summary['current_capital'],
                    'portfolio_value': portfolio_summary.get('total_portfolio_value', 0)
                }
            }
            print("   ✅ Datos de mercado procesados correctamente")
            
        except Exception as e:
            test_results['tests']['market_data_processing'] = {
                'status': 'FAILED',
                'message': f'Error procesando datos de mercado: {e}',
                'error': str(e)
            }
            test_results['errors'].append(f"TEST 3 FAILED: {e}")
            print(f"   ❌ Error: {e}")
        
        # TEST 4: Señales DRL
        print("\n📋 TEST 4: Generación de Señales DRL")
        try:
            signals_generated = 0
            
            for symbol in ['BTCUSDT', 'ETHUSDT']:
                signal = integrated_system.get_drl_signals(symbol)
                if signal:
                    signals_generated += 1
                    assert 'action' in signal
                    assert 'confidence' in signal
                    assert 'action_name' in signal
                    assert signal['action'] in [0, 1, 2]  # Hold, Buy, Sell
            
            test_results['tests']['drl_signals'] = {
                'status': 'PASSED',
                'message': f'Señales DRL generadas para {signals_generated} símbolos',
                'details': {
                    'signals_generated': signals_generated,
                    'total_symbols': len(integrated_system.symbols)
                }
            }
            print(f"   ✅ Señales DRL generadas para {signals_generated} símbolos")
            
        except Exception as e:
            test_results['tests']['drl_signals'] = {
                'status': 'FAILED',
                'message': f'Error generando señales DRL: {e}',
                'error': str(e)
            }
            test_results['errors'].append(f"TEST 4 FAILED: {e}")
            print(f"   ❌ Error: {e}")
        
        # TEST 5: Trading manual
        print("\n📋 TEST 5: Trading Manual")
        try:
            from paper_trading_system import OrderType
            
            # Colocar orden manual
            order_id = integrated_system.place_manual_order(
                symbol='BTCUSDT',
                side='buy',
                order_type=OrderType.MARKET,
                quantity=0.001,
                price=45000.0
            )
            
            assert order_id is not None
            
            # Procesar la orden
            integrated_system.process_market_update({'BTCUSDT': 45000.0})
            
            test_results['tests']['manual_trading'] = {
                'status': 'PASSED',
                'message': 'Orden manual ejecutada correctamente',
                'details': {
                    'order_id': order_id,
                    'symbol': 'BTCUSDT',
                    'side': 'buy',
                    'quantity': 0.001
                }
            }
            print("   ✅ Orden manual ejecutada correctamente")
            
        except Exception as e:
            test_results['tests']['manual_trading'] = {
                'status': 'FAILED',
                'message': f'Error en trading manual: {e}',
                'error': str(e)
            }
            test_results['errors'].append(f"TEST 5 FAILED: {e}")
            print(f"   ❌ Error: {e}")
        
        # TEST 6: Sistema de monitoreo
        print("\n📋 TEST 6: Sistema de Monitoreo DRL")
        try:
            from drl_monitoring_system import DRLMonitoringSystem
            
            monitoring = DRLMonitoringSystem(
                monitoring_interval=5,  # 5 segundos para prueba
                history_size=100
            )
            
            # Conectar sistema integrado
            monitoring.set_integrated_system(integrated_system)
            
            # Iniciar monitoreo por unos segundos
            monitoring.start_monitoring()
            time.sleep(3)  # Esperar 3 segundos
            
            # Verificar estado
            status = monitoring.get_current_status()
            assert status['monitoring_active'] == True
            
            monitoring.stop_monitoring()
            
            test_results['tests']['monitoring_system'] = {
                'status': 'PASSED',
                'message': 'Sistema de monitoreo funcionando correctamente',
                'details': {
                    'monitoring_active': status['monitoring_active'],
                    'metrics_collected': status['metrics_collected'],
                    'session_duration': status['session_duration_minutes']
                }
            }
            print("   ✅ Sistema de monitoreo funcionando correctamente")
            
        except Exception as e:
            test_results['tests']['monitoring_system'] = {
                'status': 'FAILED',
                'message': f'Error en sistema de monitoreo: {e}',
                'error': str(e)
            }
            test_results['errors'].append(f"TEST 6 FAILED: {e}")
            print(f"   ❌ Error: {e}")
        
        # TEST 7: Cambio de modos de trading
        print("\n📋 TEST 7: Modos de Trading")
        try:
            # Probar diferentes modos
            modes_tested = []
            
            for mode in ['manual', 'drl', 'hybrid']:
                integrated_system.set_trading_mode(mode)
                assert integrated_system.trading_mode == mode
                modes_tested.append(mode)
            
            test_results['tests']['trading_modes'] = {
                'status': 'PASSED',
                'message': 'Cambio de modos de trading exitoso',
                'details': {
                    'modes_tested': modes_tested,
                    'current_mode': integrated_system.trading_mode
                }
            }
            print("   ✅ Cambio de modos de trading exitoso")
            
        except Exception as e:
            test_results['tests']['trading_modes'] = {
                'status': 'FAILED',
                'message': f'Error cambiando modos de trading: {e}',
                'error': str(e)
            }
            test_results['errors'].append(f"TEST 7 FAILED: {e}")
            print(f"   ❌ Error: {e}")
        
        # TEST 8: Resumen integrado
        print("\n📋 TEST 8: Resumen Integrado")
        try:
            summary = integrated_system.get_integrated_summary()
            
            # Verificar campos requeridos
            required_fields = [
                'current_capital', 'total_portfolio_value', 'trading_mode',
                'drl_enabled', 'manual_enabled', 'drl_performance', 'system_status'
            ]
            
            for field in required_fields:
                assert field in summary, f"Campo requerido '{field}' no encontrado"
            
            test_results['tests']['integrated_summary'] = {
                'status': 'PASSED',
                'message': 'Resumen integrado generado correctamente',
                'details': {
                    'fields_verified': len(required_fields),
                    'current_capital': summary['current_capital'],
                    'trading_mode': summary['trading_mode'],
                    'drl_enabled': summary['drl_enabled']
                }
            }
            print("   ✅ Resumen integrado generado correctamente")
            
        except Exception as e:
            test_results['tests']['integrated_summary'] = {
                'status': 'FAILED',
                'message': f'Error generando resumen integrado: {e}',
                'error': str(e)
            }
            test_results['errors'].append(f"TEST 8 FAILED: {e}")
            print(f"   ❌ Error: {e}")
        
        # Calcular resultado general
        passed_tests = sum(1 for test in test_results['tests'].values() 
                          if test['status'] == 'PASSED')
        total_tests = len(test_results['tests'])
        success_rate = (passed_tests / total_tests) * 100
        
        test_results['overall_success'] = success_rate >= 75  # 75% mínimo
        test_results['summary'] = {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': success_rate
        }
        
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE PRUEBAS")
        print(f"   Total de pruebas: {total_tests}")
        print(f"   Pruebas exitosas: {passed_tests}")
        print(f"   Pruebas fallidas: {total_tests - passed_tests}")
        print(f"   Tasa de éxito: {success_rate:.1f}%")
        
        if test_results['overall_success']:
            print("   🎉 INTEGRACIÓN DRL + PAPER TRADING: ✅ EXITOSA")
        else:
            print("   ⚠️ INTEGRACIÓN DRL + PAPER TRADING: ❌ REQUIERE ATENCIÓN")
        
        return test_results
        
    except Exception as e:
        test_results['overall_success'] = False
        test_results['errors'].append(f"ERROR GENERAL: {e}")
        logger.error(f"Error general en pruebas: {e}")
        print(f"\n❌ ERROR GENERAL: {e}")
        return test_results

def save_test_results(results: Dict[str, Any], filepath: str = None):
    """Guarda los resultados de las pruebas."""
    if filepath is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"drl_integration_test_results_{timestamp}.json"
    
    try:
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Resultados guardados en: {filepath}")
        
    except Exception as e:
        print(f"❌ Error guardando resultados: {e}")

if __name__ == "__main__":
    print("🤖 SICAR - Test de Integración DRL + Paper Trading")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ejecutar pruebas
    results = test_drl_integration()
    
    # Guardar resultados
    save_test_results(results)
    
    # Mostrar resultado final
    if results['overall_success']:
        print("\n🎉 ¡INTEGRACIÓN COMPLETADA EXITOSAMENTE!")
        print("El sistema DRL está listo para usar con paper trading.")
    else:
        print("\n⚠️ La integración requiere atención.")
        print("Revisar errores y corregir antes de usar en producción.")
    
    print("\n🔚 Pruebas finalizadas.")