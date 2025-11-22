#!/usr/bin/env python3
"""
SICAR Core Adaptation Tester
Sistema de testing integrado para validar la adaptación core completa
Valida: fuentes de datos, parámetros calibrados, filtros de mercado
"""

import pandas as pd
import numpy as np
import logging
import unittest
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import warnings
import traceback
import time
warnings.filterwarnings('ignore')

# Importar módulos de adaptación core
from indices_data_adapter import IndicesDataAdapter
from indices_parameters_calibrator import IndicesParametersCalibrator
from us_market_filters import USMarketFilters, TradingSession
from main_bot_indices import IndicesTradingBot
from indices_config import IndicesConfigManager

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoreAdaptationTester:
    """
    Sistema de testing integrado para validación de adaptación core
    
    Valida:
    - Adaptador de datos (Yahoo Finance/IEX)
    - Calibrador de parámetros técnicos
    - Filtros de mercado US
    - Integración completa del sistema
    """
    
    def __init__(self):
        """Inicializar el sistema de testing"""
        self.test_results = {
            'data_adapter': {},
            'parameters_calibrator': {},
            'market_filters': {},
            'integration': {},
            'overall': {}
        }
        
        self.test_symbols = ['SPY', 'QQQ', 'DIA', 'IWM']
        self.test_start_date = datetime.now() - timedelta(days=30)
        self.test_end_date = datetime.now()
        
        logger.info("🧪 Sistema de testing de adaptación core inicializado")
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Ejecutar todos los tests de validación
        
        Returns:
            Diccionario con resultados completos de testing
        """
        try:
            logger.info("🚀 Iniciando tests completos de adaptación core...")
            
            # Test 1: Adaptador de datos
            logger.info("📊 Testing adaptador de datos...")
            self.test_results['data_adapter'] = self._test_data_adapter()
            
            # Test 2: Calibrador de parámetros
            logger.info("⚙️ Testing calibrador de parámetros...")
            self.test_results['parameters_calibrator'] = self._test_parameters_calibrator()
            
            # Test 3: Filtros de mercado
            logger.info("🕐 Testing filtros de mercado...")
            self.test_results['market_filters'] = self._test_market_filters()
            
            # Test 4: Integración completa
            logger.info("🔗 Testing integración completa...")
            self.test_results['integration'] = self._test_integration()
            
            # Calcular resultados generales
            self.test_results['overall'] = self._calculate_overall_results()
            
            # Generar reporte
            self._generate_test_report()
            
            logger.info("✅ Tests completos de adaptación core finalizados")
            return self.test_results
            
        except Exception as e:
            logger.error(f"❌ Error en tests de adaptación core: {e}")
            logger.error(traceback.format_exc())
            return {'error': str(e), 'traceback': traceback.format_exc()}
    
    def _test_data_adapter(self) -> Dict[str, Any]:
        """Test del adaptador de datos"""
        try:
            results = {
                'passed': 0,
                'failed': 0,
                'tests': {},
                'performance': {},
                'errors': []
            }
            
            # Inicializar adaptador
            adapter = IndicesDataAdapter()
            
            # Test 1: Inicialización
            test_name = "initialization"
            try:
                assert adapter is not None
                assert hasattr(adapter, 'yahoo_client')
                assert hasattr(adapter, 'iex_client')
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Adaptador inicializado correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 2: Obtención de datos para cada símbolo
            for symbol in self.test_symbols:
                test_name = f"data_fetch_{symbol}"
                try:
                    start_time = time.time()
                    
                    # Obtener datos
                    data = adapter.get_indices_data(
                        symbol=symbol,
                        interval='1d',
                        period='1mo'
                    )
                    
                    fetch_time = time.time() - start_time
                    
                    # Validaciones
                    assert data is not None
                    assert isinstance(data, pd.DataFrame)
                    assert not data.empty
                    assert len(data) > 0
                    
                    # Verificar columnas requeridas
                    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
                    for col in required_columns:
                        assert col in data.columns, f"Columna {col} faltante"
                    
                    # Verificar columnas SICAR
                    sicar_columns = ['price', 'returns', 'volatility']
                    for col in sicar_columns:
                        assert col in data.columns, f"Columna SICAR {col} faltante"
                    
                    # Verificar calidad de datos
                    assert not data.isnull().all().any(), "Datos contienen columnas completamente nulas"
                    assert data['Volume'].sum() > 0, "Volumen total es cero"
                    
                    results['tests'][test_name] = {
                        'status': 'PASS',
                        'message': f'Datos obtenidos correctamente ({len(data)} registros)',
                        'records': len(data),
                        'fetch_time': fetch_time
                    }
                    results['passed'] += 1
                    
                    # Guardar métricas de performance
                    results['performance'][symbol] = {
                        'records': len(data),
                        'fetch_time': fetch_time,
                        'records_per_second': len(data) / fetch_time if fetch_time > 0 else 0
                    }
                    
                except Exception as e:
                    results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                    results['failed'] += 1
                    results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 3: Mapeo de símbolos crypto a índices
            test_name = "symbol_mapping"
            try:
                crypto_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
                for crypto_symbol in crypto_symbols:
                    mapped_symbol = adapter.map_crypto_to_index(crypto_symbol)
                    assert mapped_symbol in self.test_symbols, f"Mapeo inválido: {crypto_symbol} -> {mapped_symbol}"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Mapeo de símbolos funciona correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 4: Filtros de calidad de datos
            test_name = "data_quality_filters"
            try:
                # Crear datos de prueba con problemas
                test_data = pd.DataFrame({
                    'Open': [100, 101, np.nan, 103],
                    'High': [102, 103, 104, 105],
                    'Low': [99, 100, 101, 102],
                    'Close': [101, 102, 103, 104],
                    'Volume': [1000000, 0, 500000, 1200000],  # Volumen cero
                    'Adj Close': [101, 102, 103, 104]
                })
                
                filtered_data = adapter._apply_data_quality_filters(test_data, 'SPY')
                
                # Verificar que se filtraron los datos problemáticos
                assert len(filtered_data) < len(test_data), "Filtros de calidad no funcionaron"
                assert not filtered_data.isnull().any().any(), "Datos filtrados contienen NaN"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Filtros de calidad funcionan correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en test de adaptador de datos: {e}")
            return {
                'passed': 0,
                'failed': 1,
                'tests': {'general_error': {'status': 'FAIL', 'message': str(e)}},
                'errors': [str(e)]
            }
    
    def _test_parameters_calibrator(self) -> Dict[str, Any]:
        """Test del calibrador de parámetros"""
        try:
            results = {
                'passed': 0,
                'failed': 0,
                'tests': {},
                'calibrated_params': {},
                'errors': []
            }
            
            # Inicializar calibrador
            calibrator = IndicesParametersCalibrator()
            
            # Test 1: Inicialización
            test_name = "initialization"
            try:
                assert calibrator is not None
                assert hasattr(calibrator, 'crypto_params')
                assert hasattr(calibrator, 'adjustment_factors')
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Calibrador inicializado correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 2: Análisis de características de mercado
            test_name = "market_analysis"
            try:
                # Crear datos de prueba
                test_data = pd.DataFrame({
                    'Close': np.random.randn(100).cumsum() + 100,
                    'Volume': np.random.randint(1000000, 5000000, 100),
                    'High': np.random.randn(100).cumsum() + 102,
                    'Low': np.random.randn(100).cumsum() + 98
                })
                test_data.index = pd.date_range(start='2024-01-01', periods=100, freq='D')
                
                analysis = calibrator.analyze_market_characteristics(test_data, 'SPY')
                
                # Verificar que el análisis contiene métricas esperadas
                required_metrics = ['volatility', 'avg_volume', 'price_range', 'trend_strength']
                for metric in required_metrics:
                    assert metric in analysis, f"Métrica {metric} faltante en análisis"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Análisis de mercado funciona correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 3: Calibración de parámetros para cada símbolo
            for symbol in self.test_symbols:
                test_name = f"parameter_calibration_{symbol}"
                try:
                    # Crear datos de prueba más realistas
                    np.random.seed(42)  # Para reproducibilidad
                    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
                    prices = 100 + np.random.randn(100).cumsum() * 0.5
                    
                    test_data = pd.DataFrame({
                        'Open': prices + np.random.randn(100) * 0.1,
                        'High': prices + np.abs(np.random.randn(100)) * 0.2,
                        'Low': prices - np.abs(np.random.randn(100)) * 0.2,
                        'Close': prices,
                        'Volume': np.random.randint(1000000, 5000000, 100),
                        'Adj Close': prices
                    }, index=dates)
                    
                    calibrated_params = calibrator.calibrate_parameters(test_data, symbol)
                    
                    # Verificar que se calibraron parámetros
                    assert calibrated_params is not None
                    assert isinstance(calibrated_params, dict)
                    assert len(calibrated_params) > 0
                    
                    # Verificar categorías de parámetros
                    expected_categories = ['timeframes', 'volatility', 'trend', 'momentum']
                    for category in expected_categories:
                        assert category in calibrated_params, f"Categoría {category} faltante"
                    
                    results['tests'][test_name] = {
                        'status': 'PASS',
                        'message': f'Parámetros calibrados correctamente para {symbol}',
                        'param_count': len(calibrated_params)
                    }
                    results['passed'] += 1
                    
                    # Guardar parámetros calibrados
                    results['calibrated_params'][symbol] = calibrated_params
                    
                except Exception as e:
                    results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                    results['failed'] += 1
                    results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 4: Validación de parámetros calibrados
            test_name = "parameter_validation"
            try:
                for symbol, params in results['calibrated_params'].items():
                    # Verificar que los parámetros están en rangos razonables
                    if 'timeframes' in params:
                        for tf_name, tf_value in params['timeframes'].items():
                            assert isinstance(tf_value, (int, float)), f"Timeframe {tf_name} no es numérico"
                            assert tf_value > 0, f"Timeframe {tf_name} debe ser positivo"
                    
                    if 'volatility' in params:
                        vol_params = params['volatility']
                        if 'threshold' in vol_params:
                            assert 0 < vol_params['threshold'] < 1, "Threshold de volatilidad fuera de rango"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Validación de parámetros exitosa'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en test de calibrador de parámetros: {e}")
            return {
                'passed': 0,
                'failed': 1,
                'tests': {'general_error': {'status': 'FAIL', 'message': str(e)}},
                'errors': [str(e)]
            }
    
    def _test_market_filters(self) -> Dict[str, Any]:
        """Test de filtros de mercado"""
        try:
            results = {
                'passed': 0,
                'failed': 0,
                'tests': {},
                'session_analysis': {},
                'errors': []
            }
            
            # Inicializar filtros
            filters = USMarketFilters()
            
            # Test 1: Inicialización
            test_name = "initialization"
            try:
                assert filters is not None
                assert hasattr(filters, 'market_hours')
                assert hasattr(filters, 'session_times')
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Filtros inicializados correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 2: Detección de sesión de trading
            test_name = "session_detection"
            try:
                # Test con diferentes horarios
                test_times = [
                    datetime(2024, 1, 15, 9, 0),   # Pre-market
                    datetime(2024, 1, 15, 10, 0),  # Market open
                    datetime(2024, 1, 15, 14, 0),  # Afternoon
                    datetime(2024, 1, 15, 17, 0),  # After hours
                    datetime(2024, 1, 15, 22, 0),  # Overnight
                ]
                
                for test_time in test_times:
                    session = filters.get_current_trading_session(test_time)
                    assert isinstance(session, TradingSession), f"Sesión inválida para {test_time}"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Detección de sesiones funciona correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 3: Verificación de trading permitido
            test_name = "trading_permission"
            try:
                # Test diferentes acciones
                actions = ['new_position', 'close_position', 'modify_position']
                
                for action in actions:
                    permission = filters.is_trading_allowed(action)
                    assert isinstance(permission, dict), f"Respuesta inválida para {action}"
                    assert 'allowed' in permission, f"Campo 'allowed' faltante para {action}"
                    assert 'session' in permission, f"Campo 'session' faltante para {action}"
                    assert isinstance(permission['allowed'], bool), f"Campo 'allowed' no es booleano para {action}"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Verificación de permisos funciona correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 4: Filtrado de datos por horarios
            test_name = "data_filtering"
            try:
                # Crear datos de prueba con diferentes horarios
                dates = pd.date_range(
                    start='2024-01-15 04:00:00',
                    end='2024-01-15 20:00:00',
                    freq='H',
                    tz='US/Eastern'
                )
                
                test_data = pd.DataFrame({
                    'Open': np.random.randn(len(dates)) + 100,
                    'High': np.random.randn(len(dates)) + 102,
                    'Low': np.random.randn(len(dates)) + 98,
                    'Close': np.random.randn(len(dates)) + 100,
                    'Volume': np.random.randint(100000, 1000000, len(dates)),
                    'Adj Close': np.random.randn(len(dates)) + 100,
                    'volatility': np.random.rand(len(dates)) * 0.05
                }, index=dates)
                
                # Test diferentes tipos de filtros
                filter_types = ['standard', 'strict', 'extended']
                
                for filter_type in filter_types:
                    filtered_data = filters.filter_trading_data(test_data, 'SPY', filter_type)
                    assert isinstance(filtered_data, pd.DataFrame), f"Resultado no es DataFrame para {filter_type}"
                    assert len(filtered_data) <= len(test_data), f"Datos filtrados más largos que originales para {filter_type}"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Filtrado de datos funciona correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 5: Sesiones óptimas por símbolo
            test_name = "optimal_sessions"
            try:
                for symbol in self.test_symbols:
                    optimal_sessions = filters.get_optimal_trading_sessions(symbol)
                    assert isinstance(optimal_sessions, list), f"Sesiones óptimas no es lista para {symbol}"
                    assert len(optimal_sessions) > 0, f"No hay sesiones óptimas para {symbol}"
                    
                    for session in optimal_sessions:
                        assert isinstance(session, TradingSession), f"Sesión inválida para {symbol}"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Sesiones óptimas funcionan correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en test de filtros de mercado: {e}")
            return {
                'passed': 0,
                'failed': 1,
                'tests': {'general_error': {'status': 'FAIL', 'message': str(e)}},
                'errors': [str(e)]
            }
    
    def _test_integration(self) -> Dict[str, Any]:
        """Test de integración completa"""
        try:
            results = {
                'passed': 0,
                'failed': 0,
                'tests': {},
                'integration_metrics': {},
                'errors': []
            }
            
            # Test 1: Inicialización del bot de índices
            test_name = "bot_initialization"
            try:
                # Configuración de prueba
                test_config = {
                    'symbols': ['SPY'],
                    'capital': 10000,
                    'risk_per_trade': 0.02,
                    'max_positions': 3
                }
                
                bot = IndicesTradingBot(test_config)
                
                assert bot is not None
                assert hasattr(bot, 'data_adapter')
                assert hasattr(bot, 'parameters_calibrator')
                assert hasattr(bot, 'market_filters')
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Bot de índices inicializado correctamente'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 2: Flujo completo de datos
            test_name = "data_flow"
            try:
                # Simular flujo completo: obtener datos -> calibrar -> filtrar
                adapter = IndicesDataAdapter()
                calibrator = IndicesParametersCalibrator()
                filters = USMarketFilters()
                
                # 1. Obtener datos
                data = adapter.get_indices_data('SPY', '1d', '1mo')
                assert not data.empty, "No se obtuvieron datos"
                
                # 2. Calibrar parámetros
                params = calibrator.calibrate_parameters(data, 'SPY')
                assert params is not None, "No se calibraron parámetros"
                
                # 3. Filtrar datos
                filtered_data = filters.filter_trading_data(data, 'SPY', 'standard')
                assert not filtered_data.empty, "Datos filtrados están vacíos"
                
                results['tests'][test_name] = {
                    'status': 'PASS',
                    'message': 'Flujo completo de datos funciona correctamente',
                    'original_records': len(data),
                    'filtered_records': len(filtered_data),
                    'filter_ratio': len(filtered_data) / len(data)
                }
                results['passed'] += 1
                
                # Guardar métricas de integración
                results['integration_metrics'] = {
                    'data_quality': len(filtered_data) / len(data),
                    'parameter_count': len(params),
                    'processing_success': True
                }
                
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            # Test 3: Compatibilidad con sistema SICAR existente
            test_name = "sicar_compatibility"
            try:
                # Verificar que los datos adaptados tienen el formato SICAR
                adapter = IndicesDataAdapter()
                data = adapter.get_indices_data('SPY', '1d', '1mo')
                
                # Verificar columnas SICAR requeridas
                sicar_columns = ['price', 'returns', 'volatility', 'Open', 'High', 'Low', 'Close', 'Volume']
                for col in sicar_columns:
                    assert col in data.columns, f"Columna SICAR {col} faltante"
                
                # Verificar tipos de datos
                assert pd.api.types.is_numeric_dtype(data['price']), "Columna 'price' no es numérica"
                assert pd.api.types.is_numeric_dtype(data['returns']), "Columna 'returns' no es numérica"
                assert pd.api.types.is_numeric_dtype(data['volatility']), "Columna 'volatility' no es numérica"
                
                results['tests'][test_name] = {'status': 'PASS', 'message': 'Compatibilidad con SICAR verificada'}
                results['passed'] += 1
            except Exception as e:
                results['tests'][test_name] = {'status': 'FAIL', 'message': str(e)}
                results['failed'] += 1
                results['errors'].append(f"{test_name}: {str(e)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en test de integración: {e}")
            return {
                'passed': 0,
                'failed': 1,
                'tests': {'general_error': {'status': 'FAIL', 'message': str(e)}},
                'errors': [str(e)]
            }
    
    def _calculate_overall_results(self) -> Dict[str, Any]:
        """Calcular resultados generales"""
        try:
            total_passed = 0
            total_failed = 0
            total_tests = 0
            
            component_scores = {}
            
            for component, results in self.test_results.items():
                if component == 'overall':
                    continue
                
                if isinstance(results, dict) and 'passed' in results and 'failed' in results:
                    passed = results['passed']
                    failed = results['failed']
                    total = passed + failed
                    
                    total_passed += passed
                    total_failed += failed
                    total_tests += total
                    
                    # Calcular score del componente
                    score = (passed / total * 100) if total > 0 else 0
                    component_scores[component] = {
                        'score': score,
                        'passed': passed,
                        'failed': failed,
                        'total': total
                    }
            
            # Calcular score general
            overall_score = (total_passed / total_tests * 100) if total_tests > 0 else 0
            
            # Determinar estado general
            if overall_score >= 90:
                status = 'EXCELLENT'
            elif overall_score >= 75:
                status = 'GOOD'
            elif overall_score >= 60:
                status = 'ACCEPTABLE'
            else:
                status = 'NEEDS_IMPROVEMENT'
            
            return {
                'overall_score': overall_score,
                'status': status,
                'total_passed': total_passed,
                'total_failed': total_failed,
                'total_tests': total_tests,
                'component_scores': component_scores,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculando resultados generales: {e}")
            return {
                'overall_score': 0,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def _generate_test_report(self):
        """Generar reporte de testing"""
        try:
            logger.info("\n" + "="*80)
            logger.info("📋 REPORTE DE TESTING - ADAPTACIÓN CORE SICAR")
            logger.info("="*80)
            
            overall = self.test_results.get('overall', {})
            
            # Resumen general
            logger.info(f"🎯 SCORE GENERAL: {overall.get('overall_score', 0):.1f}%")
            logger.info(f"📊 STATUS: {overall.get('status', 'UNKNOWN')}")
            logger.info(f"✅ Tests Pasados: {overall.get('total_passed', 0)}")
            logger.info(f"❌ Tests Fallidos: {overall.get('total_failed', 0)}")
            logger.info(f"📈 Total Tests: {overall.get('total_tests', 0)}")
            
            # Resultados por componente
            logger.info("\n📋 RESULTADOS POR COMPONENTE:")
            logger.info("-" * 50)
            
            component_scores = overall.get('component_scores', {})
            for component, score_info in component_scores.items():
                score = score_info.get('score', 0)
                passed = score_info.get('passed', 0)
                failed = score_info.get('failed', 0)
                total = score_info.get('total', 0)
                
                status_icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
                
                logger.info(f"{status_icon} {component.upper()}: {score:.1f}% ({passed}/{total})")
            
            # Errores encontrados
            all_errors = []
            for component, results in self.test_results.items():
                if isinstance(results, dict) and 'errors' in results:
                    all_errors.extend(results['errors'])
            
            if all_errors:
                logger.info("\n🚨 ERRORES ENCONTRADOS:")
                logger.info("-" * 50)
                for i, error in enumerate(all_errors[:10], 1):  # Mostrar máximo 10 errores
                    logger.info(f"{i}. {error}")
                
                if len(all_errors) > 10:
                    logger.info(f"... y {len(all_errors) - 10} errores más")
            
            # Recomendaciones
            logger.info("\n💡 RECOMENDACIONES:")
            logger.info("-" * 50)
            
            if overall.get('overall_score', 0) >= 90:
                logger.info("🎉 Excelente! La adaptación core está lista para producción")
            elif overall.get('overall_score', 0) >= 75:
                logger.info("👍 Buena adaptación, revisar errores menores antes de producción")
            elif overall.get('overall_score', 0) >= 60:
                logger.info("⚠️ Adaptación aceptable, pero requiere mejoras importantes")
            else:
                logger.info("🔧 La adaptación necesita trabajo significativo antes de usar")
            
            logger.info("\n" + "="*80)
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")

def run_core_adaptation_tests():
    """Función principal para ejecutar tests de adaptación core"""
    tester = CoreAdaptationTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    # Ejecutar tests
    print("🧪 Iniciando tests de adaptación core SICAR...")
    
    results = run_core_adaptation_tests()
    
    if 'error' in results:
        print(f"❌ Error en testing: {results['error']}")
    else:
        overall_score = results.get('overall', {}).get('overall_score', 0)
        status = results.get('overall', {}).get('status', 'UNKNOWN')
        
        print(f"\n🏁 Testing completado!")
        print(f"📊 Score: {overall_score:.1f}%")
        print(f"🎯 Status: {status}")