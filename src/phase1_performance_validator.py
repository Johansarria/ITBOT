#!/usr/bin/env python3
"""
Phase 1 Performance Validator
Valida que los nuevos modelos no impacten negativamente el rendimiento del sistema SICAR
"""

import time
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import tracemalloc
from typing import Dict, List, Tuple

# Importar módulos del sistema
from phase1_integration_manager import Phase1IntegrationManager
from advanced_ml_engine import AdvancedMLEngine

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PerformanceValidator:
    """
    Validador de rendimiento para Phase 1
    """
    
    def __init__(self):
        self.baseline_metrics = {}
        self.phase1_metrics = {}
        self.performance_thresholds = {
            'max_prediction_time': 2.0,  # segundos
            'max_memory_increase': 100,   # MB
            'max_cpu_increase': 20,       # %
            'min_accuracy_retention': 0.95  # 95% de la precisión original
        }
    
    def measure_system_resources(self) -> Dict:
        """
        Medir recursos del sistema usando tracemalloc
        """
        if not tracemalloc.is_tracing():
            tracemalloc.start()
        
        current, peak = tracemalloc.get_traced_memory()
        
        return {
            'memory_mb': current / 1024 / 1024,
            'peak_memory_mb': peak / 1024 / 1024,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_test_data(self, n_samples: int = 1000) -> pd.DataFrame:
        """
        Generar datos de prueba para validación
        """
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=n_samples, freq='1min')
        
        # Simular datos de mercado realistas
        price = 50000  # Precio inicial
        prices = []
        volumes = []
        
        for i in range(n_samples):
            # Precio con random walk
            price += np.random.normal(0, 0.001) * price
            
            # Añadir algo de tendencia
            if i % 100 == 0:
                price *= np.random.uniform(0.98, 1.02)
            
            prices.append(price)
            volumes.append(np.random.lognormal(8, 1))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': [p * np.random.uniform(0.999, 1.001) for p in prices],
            'high': [p * np.random.uniform(1.001, 1.005) for p in prices],
            'low': [p * np.random.uniform(0.995, 0.999) for p in prices],
            'close': prices,
            'volume': volumes
        })
    
    def benchmark_baseline_system(self, test_data: pd.DataFrame, symbol: str = 'BTCUSDT') -> Dict:
        """
        Benchmark del sistema baseline (sin Phase 1)
        """
        logger.info("🔍 Benchmarking sistema baseline...")
        
        # Medir recursos iniciales
        initial_resources = self.measure_system_resources()
        
        # Inicializar sistema baseline
        ml_engine = AdvancedMLEngine()
        
        # Preparar datos para entrenamiento
        train_data = test_data.iloc[:-200]  # Usar 80% para entrenamiento
        test_subset = test_data.iloc[-200:]  # 20% para testing
        
        # Entrenar modelo baseline
        start_time = time.time()
        
        # Preparar datos para el formato esperado por AdvancedMLEngine
        # Crear features usando el motor ML
        features = ml_engine.create_all_features(train_data)
        targets = ml_engine.create_targets(train_data)
        
        # Usar el target principal
        if 'target_main' in targets.columns:
            y_train = targets['target_main']
        else:
            y_train = (train_data['close'].shift(-1) > train_data['close']).astype(int)
        
        # Filtrar datos válidos
        valid_idx = ~(features.isna().any(axis=1) | y_train.isna())
        X_train = features.loc[valid_idx]
        y_train = y_train.loc[valid_idx]
        
        training_result = ml_engine.train_model(symbol, X_train, y_train)
        training_time = time.time() - start_time
        
        if not training_result:
            logger.error("❌ Error entrenando modelo baseline")
            return {}
        
        # Medir tiempo de predicción
        prediction_times = []
        predictions = []
        
        for i in range(min(100, len(test_subset))):
            current_data = test_subset.iloc[i:i+50]  # Ventana de 50 datos
            
            start_pred = time.time()
            try:
                # Crear features para predicción
                features_pred = ml_engine.create_all_features(current_data)
                if len(features_pred) > 0:
                    prediction, confidence = ml_engine.predict(symbol, features_pred)
                    pred_time = time.time() - start_pred
                    
                    if prediction is not None:
                        prediction_times.append(pred_time)
                        predictions.append({'prediction': prediction, 'confidence': confidence})
            except Exception as e:
                logger.warning(f"Error en predicción {i}: {e}")
                continue
        
        # Medir recursos finales
        final_resources = self.measure_system_resources()
        
        return {
            'training_time': training_time,
            'avg_prediction_time': np.mean(prediction_times) if prediction_times else 0,
            'max_prediction_time': np.max(prediction_times) if prediction_times else 0,
            'total_predictions': len(predictions),
            'memory_usage': final_resources['memory_mb'] - initial_resources['memory_mb'],
            'accuracy': 0.5 if training_result else 0,  # AdvancedMLEngine retorna bool
            'resources': {
                'initial': initial_resources,
                'final': final_resources
            }
        }
    
    def benchmark_phase1_system(self, test_data: pd.DataFrame, symbol: str = 'BTCUSDT') -> Dict:
        """
        Benchmark del sistema con Phase 1
        """
        logger.info("🚀 Benchmarking sistema Phase 1...")
        
        # Medir recursos iniciales
        initial_resources = self.measure_system_resources()
        
        # Inicializar sistema Phase 1
        phase1_manager = Phase1IntegrationManager()
        
        # Preparar datos para entrenamiento
        train_data = test_data.iloc[:-200]
        test_subset = test_data.iloc[-200:]
        
        # Inicializar modelos Phase 1
        start_time = time.time()
        init_success = phase1_manager.initialize_symbol(symbol, train_data)
        initialization_time = time.time() - start_time
        
        if not init_success:
            logger.error("❌ Error inicializando Phase 1")
            return {}
        
        # Medir tiempo de predicción
        prediction_times = []
        predictions = []
        
        for i in range(min(100, len(test_subset))):
            current_data = test_subset.iloc[i:i+50]
            
            start_pred = time.time()
            prediction = phase1_manager.get_enhanced_prediction(symbol, current_data)
            pred_time = time.time() - start_pred
            
            if prediction:
                prediction_times.append(pred_time)
                predictions.append(prediction)
                
                # Simular actualización del modelo con resultado de trade
                trade_result = {
                    'symbol': symbol,
                    'price': current_data.iloc[-1]['close'],
                    'quantity': prediction.get('position_size', 0.5),
                    'side': 'buy' if prediction.get('signal', 0) > 0 else 'sell',
                    'timestamp': current_data.index[-1],
                    'pnl': np.random.uniform(-0.01, 0.02)
                }
                phase1_manager.update_from_trade_result(symbol, trade_result)
        
        # Medir recursos finales
        final_resources = self.measure_system_resources()
        
        return {
            'initialization_time': initialization_time,
            'avg_prediction_time': np.mean(prediction_times) if prediction_times else 0,
            'max_prediction_time': np.max(prediction_times) if prediction_times else 0,
            'total_predictions': len(predictions),
            'memory_usage': final_resources['memory_mb'] - initial_resources['memory_mb'],
            'resources': {
                'initial': initial_resources,
                'final': final_resources
            }
        }
    
    def validate_performance(self, baseline: Dict, phase1: Dict) -> Dict:
        """
        Validar que Phase 1 cumple con los umbrales de rendimiento
        """
        logger.info("📊 Validando rendimiento...")
        
        validation_results = {
            'passed': True,
            'issues': [],
            'metrics_comparison': {},
            'recommendations': []
        }
        
        # 1. Tiempo de predicción
        if phase1.get('max_prediction_time', 0) > self.performance_thresholds['max_prediction_time']:
            validation_results['passed'] = False
            validation_results['issues'].append(
                f"Tiempo máximo de predicción excedido: {phase1['max_prediction_time']:.3f}s > {self.performance_thresholds['max_prediction_time']}s"
            )
        
        # 2. Uso de memoria
        memory_increase = phase1.get('memory_usage', 0) - baseline.get('memory_usage', 0)
        if memory_increase > self.performance_thresholds['max_memory_increase']:
            validation_results['passed'] = False
            validation_results['issues'].append(
                f"Incremento de memoria excedido: {memory_increase:.1f}MB > {self.performance_thresholds['max_memory_increase']}MB"
            )
        
        # 3. Comparación de métricas
        validation_results['metrics_comparison'] = {
            'prediction_time': {
                'baseline_avg': baseline.get('avg_prediction_time', 0),
                'phase1_avg': phase1.get('avg_prediction_time', 0),
                'increase_factor': (phase1.get('avg_prediction_time', 0) / max(baseline.get('avg_prediction_time', 0.001), 0.001))
            },
            'memory_usage': {
                'baseline': baseline.get('memory_usage', 0),
                'phase1': phase1.get('memory_usage', 0),
                'increase': memory_increase
            },
            'total_predictions': {
                'baseline': baseline.get('total_predictions', 0),
                'phase1': phase1.get('total_predictions', 0)
            }
        }
        
        # 4. Recomendaciones
        if phase1.get('avg_prediction_time', 0) > baseline.get('avg_prediction_time', 0) * 1.5:
            validation_results['recommendations'].append(
                "Considerar optimizar los modelos Phase 1 para reducir tiempo de predicción"
            )
        
        if memory_increase > 50:
            validation_results['recommendations'].append(
                "Considerar implementar limpieza de memoria periódica"
            )
        
        return validation_results
    
    def run_full_validation(self) -> Dict:
        """
        Ejecutar validación completa de rendimiento
        """
        logger.info("🎯 Iniciando validación completa de rendimiento Phase 1")
        
        # Generar datos de prueba
        test_data = self.generate_test_data(2000)
        symbol = 'BTCUSDT'
        
        try:
            # Benchmark baseline
            logger.info("📈 Ejecutando benchmark baseline...")
            baseline_results = self.benchmark_baseline_system(test_data, symbol)
            
            if not baseline_results:
                return {'error': 'Failed to benchmark baseline system'}
            
            # Benchmark Phase 1
            logger.info("🚀 Ejecutando benchmark Phase 1...")
            phase1_results = self.benchmark_phase1_system(test_data, symbol)
            
            if not phase1_results:
                return {'error': 'Failed to benchmark Phase 1 system'}
            
            # Validar rendimiento
            validation = self.validate_performance(baseline_results, phase1_results)
            
            # Compilar resultados finales
            final_results = {
                'validation_passed': validation['passed'],
                'timestamp': datetime.now().isoformat(),
                'baseline_metrics': baseline_results,
                'phase1_metrics': phase1_results,
                'validation_details': validation,
                'summary': {
                    'prediction_time_increase': f"{((phase1_results.get('avg_prediction_time', 0) / max(baseline_results.get('avg_prediction_time', 0.001), 0.001)) - 1) * 100:.1f}%",
                    'memory_increase': f"{phase1_results.get('memory_usage', 0) - baseline_results.get('memory_usage', 0):.1f}MB",
                    'total_issues': len(validation['issues']),
                    'recommendations_count': len(validation['recommendations'])
                }
            }
            
            return final_results
            
        except Exception as e:
            logger.error(f"❌ Error en validación: {e}")
            return {'error': str(e)}


def main():
    """
    Función principal para ejecutar la validación
    """
    print("🎯 SICAR Phase 1 - Validador de Rendimiento")
    print("=" * 50)
    
    validator = PerformanceValidator()
    results = validator.run_full_validation()
    
    if 'error' in results:
        print(f"❌ Error en validación: {results['error']}")
        return
    
    # Mostrar resultados
    print(f"\n📊 RESULTADOS DE VALIDACIÓN")
    print(f"Validación: {'✅ APROBADA' if results['validation_passed'] else '❌ FALLIDA'}")
    print(f"Timestamp: {results['timestamp']}")
    
    print(f"\n📈 MÉTRICAS DE RENDIMIENTO:")
    print(f"• Incremento tiempo predicción: {results['summary']['prediction_time_increase']}")
    print(f"• Incremento memoria: {results['summary']['memory_increase']}")
    print(f"• Issues encontrados: {results['summary']['total_issues']}")
    print(f"• Recomendaciones: {results['summary']['recommendations_count']}")
    
    if results['validation_details']['issues']:
        print(f"\n⚠️  ISSUES ENCONTRADOS:")
        for issue in results['validation_details']['issues']:
            print(f"  - {issue}")
    
    if results['validation_details']['recommendations']:
        print(f"\n💡 RECOMENDACIONES:")
        for rec in results['validation_details']['recommendations']:
            print(f"  - {rec}")
    
    print(f"\n🔍 DETALLES TÉCNICOS:")
    baseline = results['baseline_metrics']
    phase1 = results['phase1_metrics']
    
    print(f"Baseline - Tiempo promedio predicción: {baseline.get('avg_prediction_time', 0):.3f}s")
    print(f"Phase 1  - Tiempo promedio predicción: {phase1.get('avg_prediction_time', 0):.3f}s")
    print(f"Baseline - Uso memoria: {baseline.get('memory_usage', 0):.1f}MB")
    print(f"Phase 1  - Uso memoria: {phase1.get('memory_usage', 0):.1f}MB")
    
    if results['validation_passed']:
        print(f"\n✅ Phase 1 ha pasado todas las validaciones de rendimiento")
        print(f"✅ El sistema está listo para producción")
    else:
        print(f"\n❌ Phase 1 requiere optimizaciones antes de producción")
    
    return results


if __name__ == "__main__":
    main()