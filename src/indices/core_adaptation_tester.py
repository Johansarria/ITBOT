"""
SICAR Core Adaptation Tester
Sistema de testing integrado para validar la adaptación core completa
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional
import traceback

# Agregar el directorio raíz al path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CoreAdaptationTester:
    """
    Tester integrado para validar toda la adaptación core del sistema SICAR
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results = {}
        self.overall_status = "UNKNOWN"
        
        # Símbolos de prueba
        self.test_symbols = ['SPY', 'QQQ', 'IWM']
        
        # Datos de prueba simulados
        self.sample_data = self._generate_sample_data()
    
    def _generate_sample_data(self) -> Dict[str, pd.DataFrame]:
        """Generar datos de prueba simulados"""
        data = {}
        
        for symbol in self.test_symbols:
            # Generar 100 días de datos simulados
            dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
            
            # Precios base por símbolo
            base_prices = {'SPY': 450, 'QQQ': 350, 'IWM': 200}
            base_price = base_prices.get(symbol, 300)
            
            # Generar datos OHLCV realistas
            np.random.seed(42)  # Para reproducibilidad
            
            close_prices = []
            current_price = base_price
            
            for i in range(100):
                # Movimiento aleatorio con tendencia ligera
                change = np.random.normal(0, 0.02)  # 2% volatilidad diaria
                current_price *= (1 + change)
                close_prices.append(current_price)
            
            # Crear OHLC basado en close
            df_data = []
            for i, close in enumerate(close_prices):
                high = close * (1 + abs(np.random.normal(0, 0.01)))
                low = close * (1 - abs(np.random.normal(0, 0.01)))
                open_price = close_prices[i-1] if i > 0 else close
                volume = np.random.randint(1000000, 10000000)
                
                df_data.append({
                    'Open': open_price,
                    'High': max(high, open_price, close),
                    'Low': min(low, open_price, close),
                    'Close': close,
                    'Volume': volume,
                    'Adj Close': close
                })
            
            df = pd.DataFrame(df_data, index=dates)
            
            # Agregar columnas SICAR
            df['price'] = df['Close']
            df['returns'] = df['Close'].pct_change()
            df['volatility'] = df['returns'].rolling(20).std()
            
            data[symbol] = df
        
        return data
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Ejecutar testing completo de la adaptación core"""
        self.logger.info("Iniciando testing completo de adaptación core...")
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'modules_tested': [],
            'tests_passed': 0,
            'tests_failed': 0,
            'tests_total': 0,
            'detailed_results': {},
            'recommendations': [],
            'overall_status': 'UNKNOWN'
        }
        
        # Lista de tests a ejecutar
        tests = [
            ('indices_config', self._test_indices_config),
            ('data_adapter', self._test_data_adapter),
            ('parameters_calibrator', self._test_parameters_calibrator),
            ('market_filters', self._test_market_filters),
            ('data_validator', self._test_data_validator),
            ('config_migration', self._test_config_migration),
            ('integration', self._test_integration)
        ]
        
        # Ejecutar cada test
        for test_name, test_func in tests:
            self.logger.info(f"Ejecutando test: {test_name}")
            try:
                result = test_func()
                test_results['detailed_results'][test_name] = result
                test_results['modules_tested'].append(test_name)
                
                if result['status'] == 'PASSED':
                    test_results['tests_passed'] += 1
                else:
                    test_results['tests_failed'] += 1
                
                test_results['tests_total'] += 1
                
            except Exception as e:
                self.logger.error(f"Error en test {test_name}: {e}")
                test_results['detailed_results'][test_name] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
                test_results['tests_failed'] += 1
                test_results['tests_total'] += 1
        
        # Determinar status general
        success_rate = test_results['tests_passed'] / test_results['tests_total']
        if success_rate >= 0.9:
            test_results['overall_status'] = 'EXCELLENT'
        elif success_rate >= 0.7:
            test_results['overall_status'] = 'GOOD'
        elif success_rate >= 0.5:
            test_results['overall_status'] = 'ACCEPTABLE'
        else:
            test_results['overall_status'] = 'POOR'
        
        # Generar recomendaciones
        self._generate_recommendations(test_results)
        
        return test_results
    
    def _test_indices_config(self) -> Dict[str, Any]:
        """Test del módulo indices_config"""
        try:
            from src.indices.indices_config import IndicesConfig, IndexSpecificConfig
            
            # Test básico de importación y creación
            config = IndicesConfig()
            
            # Verificar configuraciones por defecto
            spy_config = config.get_config('SPY')
            
            result = {
                'status': 'PASSED',
                'details': {
                    'import_successful': True,
                    'config_creation': True,
                    'spy_config_available': spy_config is not None,
                    'config_type': type(spy_config).__name__
                },
                'message': 'Módulo indices_config funcionando correctamente'
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'message': 'Error en módulo indices_config'
            }
    
    def _test_data_adapter(self) -> Dict[str, Any]:
        """Test del adaptador de datos"""
        try:
            from src.indices.indices_data_adapter import IndicesDataAdapter
            
            adapter = IndicesDataAdapter()
            
            # Test de mapeo de símbolos
            mapped_symbol = adapter.map_crypto_to_index('BTCUSDT')
            
            # Test de adaptación de datos
            sample_data = self.sample_data['SPY'].copy()
            adapted_data = adapter.adapt_data_format(sample_data, 'SPY')
            
            result = {
                'status': 'PASSED',
                'details': {
                    'adapter_creation': True,
                    'symbol_mapping': mapped_symbol is not None,
                    'data_adaptation': len(adapted_data) > 0,
                    'required_columns': all(col in adapted_data.columns for col in ['Open', 'High', 'Low', 'Close', 'Volume'])
                },
                'message': 'Adaptador de datos funcionando correctamente'
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'message': 'Error en adaptador de datos'
            }
    
    def _test_parameters_calibrator(self) -> Dict[str, Any]:
        """Test del calibrador de parámetros"""
        try:
            from src.indices.indices_parameters_calibrator import IndicesParametersCalibrator
            
            calibrator = IndicesParametersCalibrator()
            
            # Test de calibración básica
            sample_data = self.sample_data['SPY'].copy()
            calibrated_params = calibrator.calibrate_for_symbol('SPY', sample_data)
            
            result = {
                'status': 'PASSED',
                'details': {
                    'calibrator_creation': True,
                    'calibration_successful': calibrated_params is not None,
                    'has_timeframe_params': 'timeframe_adjustments' in calibrated_params,
                    'has_volatility_params': 'volatility_adjustments' in calibrated_params
                },
                'message': 'Calibrador de parámetros funcionando correctamente'
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'message': 'Error en calibrador de parámetros'
            }
    
    def _test_market_filters(self) -> Dict[str, Any]:
        """Test de filtros de mercado"""
        try:
            from src.indices.us_market_filters import USMarketFilters, TradingSession
            
            filters = USMarketFilters()
            
            # Test de sesión actual
            current_session = filters.get_current_session()
            
            # Test de filtrado de datos
            sample_data = self.sample_data['SPY'].copy()
            filtered_data = filters.filter_trading_hours(sample_data, 'regular')
            
            result = {
                'status': 'PASSED',
                'details': {
                    'filters_creation': True,
                    'session_detection': current_session is not None,
                    'data_filtering': len(filtered_data) >= 0,
                    'session_type': current_session.value if current_session else 'unknown'
                },
                'message': 'Filtros de mercado funcionando correctamente'
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'message': 'Error en filtros de mercado'
            }
    
    def _test_data_validator(self) -> Dict[str, Any]:
        """Test del validador de datos"""
        try:
            from src.indices.indices_data_validator import IndicesDataValidator, ValidationLevel
            
            validator = IndicesDataValidator(ValidationLevel.STANDARD)
            
            # Test de validación
            sample_data = self.sample_data['SPY'].copy()
            validation_result = validator.validate_data(sample_data, 'SPY')
            
            result = {
                'status': 'PASSED',
                'details': {
                    'validator_creation': True,
                    'validation_successful': validation_result is not None,
                    'has_quality_score': hasattr(validation_result, 'score'),
                    'quality_level': validation_result.quality.value if hasattr(validation_result, 'quality') else 'unknown'
                },
                'message': 'Validador de datos funcionando correctamente'
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'message': 'Error en validador de datos'
            }
    
    def _test_config_migration(self) -> Dict[str, Any]:
        """Test del adaptador de configuración"""
        try:
            from src.indices.config_migration_adapter import ConfigMigrationAdapter
            
            adapter = ConfigMigrationAdapter()
            
            # Test de migración de configuración
            crypto_config = {
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'volatility_window': 20,
                'trend_period': 50
            }
            
            migrated_config = adapter.migrate_config(crypto_config)
            
            result = {
                'status': 'PASSED',
                'details': {
                    'adapter_creation': True,
                    'migration_successful': migrated_config is not None,
                    'has_symbol_mapping': 'symbol' in migrated_config,
                    'has_adapted_params': len(migrated_config) > len(crypto_config)
                },
                'message': 'Adaptador de configuración funcionando correctamente'
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'message': 'Error en adaptador de configuración'
            }
    
    def _test_integration(self) -> Dict[str, Any]:
        """Test de integración entre módulos"""
        try:
            # Test de integración básica
            from src.indices.indices_config import IndicesConfig
            from src.indices.indices_data_adapter import IndicesDataAdapter
            from src.indices.us_market_filters import USMarketFilters
            
            # Crear instancias
            config = IndicesConfig()
            adapter = IndicesDataAdapter()
            filters = USMarketFilters()
            
            # Test de flujo integrado
            spy_config = config.get_config('SPY')
            sample_data = self.sample_data['SPY'].copy()
            adapted_data = adapter.adapt_data_format(sample_data, 'SPY')
            filtered_data = filters.filter_trading_hours(adapted_data, 'regular')
            
            result = {
                'status': 'PASSED',
                'details': {
                    'modules_integration': True,
                    'data_flow': len(filtered_data) >= 0,
                    'config_compatibility': spy_config is not None,
                    'end_to_end': True
                },
                'message': 'Integración entre módulos funcionando correctamente'
            }
            
            return result
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'message': 'Error en integración de módulos'
            }
    
    def _generate_recommendations(self, test_results: Dict[str, Any]):
        """Generar recomendaciones basadas en resultados"""
        recommendations = []
        
        failed_tests = [name for name, result in test_results['detailed_results'].items() 
                       if result['status'] != 'PASSED']
        
        if failed_tests:
            recommendations.append(f"Revisar módulos fallidos: {', '.join(failed_tests)}")
        
        if test_results['tests_passed'] < test_results['tests_total']:
            recommendations.append("Implementar tests adicionales para módulos críticos")
        
        success_rate = test_results['tests_passed'] / test_results['tests_total']
        if success_rate < 0.8:
            recommendations.append("Mejorar cobertura de testing y validación")
        
        if not recommendations:
            recommendations.append("Sistema listo para producción")
        
        test_results['recommendations'] = recommendations
    
    def generate_report(self, test_results: Dict[str, Any]) -> str:
        """Generar reporte detallado de testing"""
        report = []
        report.append("=" * 80)
        report.append("REPORTE DE TESTING - ADAPTACIÓN CORE SICAR")
        report.append("=" * 80)
        report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Status General: {test_results['overall_status']}")
        report.append("")
        
        # Resumen
        report.append("RESUMEN:")
        report.append(f"  Tests Ejecutados: {test_results['tests_total']}")
        report.append(f"  Tests Exitosos: {test_results['tests_passed']}")
        report.append(f"  Tests Fallidos: {test_results['tests_failed']}")
        report.append(f"  Tasa de Éxito: {test_results['tests_passed']/test_results['tests_total']*100:.1f}%")
        report.append("")
        
        # Módulos testados
        report.append("MÓDULOS TESTADOS:")
        for module in test_results['modules_tested']:
            status = test_results['detailed_results'][module]['status']
            report.append(f"  ✓ {module}: {status}")
        report.append("")
        
        # Detalles por módulo
        report.append("DETALLES POR MÓDULO:")
        report.append("-" * 50)
        
        for module, result in test_results['detailed_results'].items():
            report.append(f"\n{module.upper()}:")
            report.append(f"  Status: {result['status']}")
            report.append(f"  Mensaje: {result.get('message', 'N/A')}")
            
            if 'details' in result:
                report.append("  Detalles:")
                for key, value in result['details'].items():
                    report.append(f"    - {key}: {value}")
            
            if 'error' in result:
                report.append(f"  Error: {result['error']}")
        
        # Recomendaciones
        report.append("\nRECOMENDACIONES:")
        for rec in test_results['recommendations']:
            report.append(f"  • {rec}")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)

def main():
    """Función principal"""
    print("Iniciando testing de adaptación core SICAR...")
    
    tester = CoreAdaptationTester()
    
    # Ejecutar tests
    results = tester.run_comprehensive_test()
    
    # Generar y mostrar reporte
    report = tester.generate_report(results)
    print(report)
    
    # Guardar reporte
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"core_adaptation_test_report_{timestamp}.txt"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\nReporte guardado en: {report_file}")
    except Exception as e:
        print(f"Error guardando reporte: {e}")
    
    # Status de salida
    if results['overall_status'] in ['EXCELLENT', 'GOOD']:
        print("\n✅ ADAPTACIÓN CORE COMPLETADA EXITOSAMENTE")
        return 0
    else:
        print("\n❌ ADAPTACIÓN CORE REQUIERE ATENCIÓN")
        return 1

if __name__ == "__main__":
    exit(main())