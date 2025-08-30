#!/usr/bin/env python3
"""
Análisis de rendimiento del modelo ML con 50,000 datos históricos.
Mide tiempos de carga, transformación, predicción y toma de decisiones.
"""

import time
import pandas as pd
import numpy as np
import asyncio
import logging
from datetime import datetime, timedelta
import sys
import os

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Agregar el directorio raíz al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.technical_analysis import analyze_market, load_ml_model
from utils.feature_pipeline import FeaturePipeline
from database.database_manager import get_klines

def generate_synthetic_klines(count: int = 50000, symbol: str = "BTCUSDT") -> pd.DataFrame:
    """
    Genera datos sintéticos de klines para pruebas de rendimiento.
    
    Args:
        count: Número de registros a generar
        symbol: Símbolo de trading
        
    Returns:
        DataFrame con datos sintéticos realistas
    """
    logger.info(f"🔧 Generando {count:,} registros sintéticos para {symbol}")
    
    # Crear timestamps con intervalo de 1 hora
    start_time = datetime.now() - timedelta(hours=count)
    timestamps = pd.date_range(start=start_time, periods=count, freq='1H')
    
    # Generar precios usando random walk con drift
    np.random.seed(42)  # Para reproducibilidad
    initial_price = 50000  # Precio inicial BTC
    returns = np.random.normal(0.0001, 0.02, count)  # Media positiva, volatilidad 2%
    
    # Crear serie de precios con random walk
    prices = [initial_price]
    for i in range(1, count):
        new_price = prices[-1] * (1 + returns[i])
        prices.append(max(new_price, 1.0))  # Evitar precios negativos
    
    prices = np.array(prices)
    
    # Generar OHLC realista
    noise_factor = 0.01  # 1% de ruido
    high_noise = np.random.uniform(1, 1 + noise_factor, count)
    low_noise = np.random.uniform(1 - noise_factor, 1, count)
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices * np.random.uniform(0.999, 1.001, count),
        'high': prices * high_noise,
        'low': prices * low_noise,
        'close': prices,
        'volume': np.random.uniform(100, 10000, count),  # Volumen aleatorio
        'symbol': symbol,
        'interval': '1h'
    })
    
    # Asegurar que high >= max(open, close) y low <= min(open, close)
    df['high'] = np.maximum(df['high'], np.maximum(df['open'], df['close']))
    df['low'] = np.minimum(df['low'], np.minimum(df['open'], df['close']))
    
    logger.info(f"✅ Datos sintéticos generados: {len(df):,} registros")
    logger.info(f"📊 Rango de precios: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
    
    return df

def benchmark_feature_generation(df: pd.DataFrame) -> dict:
    """
    Mide el tiempo de generación de features técnicas.
    """
    logger.info(f"⏱️ Benchmark: Generación de features con {len(df):,} registros")
    
    start_time = time.perf_counter()
    
    feature_pipeline = FeaturePipeline()
    df_features = feature_pipeline.transform(df.copy())
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    result = {
        'feature_generation_time': duration,
        'features_per_second': len(df) / duration if duration > 0 else 0,
        'input_records': len(df),
        'output_features': len(df_features.columns),
        'memory_usage_mb': df_features.memory_usage(deep=True).sum() / 1024 / 1024
    }
    
    logger.info(f"✅ Features generadas en {duration:.3f}s ({result['features_per_second']:.0f} records/s)")
    logger.info(f"📊 Features técnicas: {result['output_features']} columnas")
    logger.info(f"💾 Uso de memoria: {result['memory_usage_mb']:.1f} MB")
    
    return result

def benchmark_model_loading() -> dict:
    """
    Mide el tiempo de carga del modelo ML.
    """
    logger.info("⏱️ Benchmark: Carga del modelo ML")
    
    start_time = time.perf_counter()
    
    # Forzar recarga del modelo
    import utils.technical_analysis as ta_module
    ta_module.ml_model = None
    load_ml_model()
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    result = {
        'model_loading_time': duration,
        'model_loaded': ta_module.ml_model is not None
    }
    
    logger.info(f"✅ Modelo cargado en {duration:.3f}s")
    
    return result

async def benchmark_prediction_time(df: pd.DataFrame) -> dict:
    """
    Mide el tiempo de predicción y toma de decisiones.
    """
    logger.info(f"⏱️ Benchmark: Predicción con {len(df):,} registros")
    
    start_time = time.perf_counter()
    
    # Realizar análisis completo
    result = await analyze_market(
        symbol="BTCUSDT",
        interval="1h",
        limit=None,
        export=False,
        df_klines=df
    )
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    benchmark_result = {
        'prediction_time': duration,
        'records_processed': len(df),
        'records_per_second': len(df) / duration if duration > 0 else 0,
        'decision': result.get('decision', 'UNKNOWN'),
        'score': result.get('score', 0),
        'ml_status': result.get('ml_status', 'UNKNOWN'),
        'confidence_level': result.get('ml_confidence_level', 'UNKNOWN')
    }
    
    logger.info(f"✅ Predicción completada en {duration:.3f}s")
    logger.info(f"🎯 Decisión: {benchmark_result['decision']} (Score: {benchmark_result['score']:.1f})")
    logger.info(f"🚀 Rendimiento: {benchmark_result['records_per_second']:.0f} records/s")
    
    return benchmark_result

def benchmark_memory_usage(df: pd.DataFrame) -> dict:
    """
    Analiza el uso de memoria durante el procesamiento.
    """
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    
    # Memoria antes del procesamiento
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Procesar datos
    feature_pipeline = FeaturePipeline()
    df_features = feature_pipeline.transform(df.copy())
    
    # Memoria después del procesamiento
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    
    result = {
        'memory_before_mb': memory_before,
        'memory_after_mb': memory_after,
        'memory_increase_mb': memory_after - memory_before,
        'data_memory_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
        'features_memory_mb': df_features.memory_usage(deep=True).sum() / 1024 / 1024
    }
    
    logger.info(f"💾 Uso de memoria: {memory_before:.1f} MB → {memory_after:.1f} MB (+{result['memory_increase_mb']:.1f} MB)")
    
    return result

async def run_full_benchmark():
    """
    Ejecuta el benchmark completo con 50,000 datos.
    """
    logger.info("🚀 INICIANDO BENCHMARK DE RENDIMIENTO - 50,000 DATOS")
    logger.info("=" * 70)
    
    # Generar datos sintéticos
    df_50k = generate_synthetic_klines(50000)
    
    # Benchmark 1: Carga del modelo
    logger.info("\n📊 FASE 1: Carga del Modelo ML")
    logger.info("-" * 40)
    model_benchmark = benchmark_model_loading()
    
    # Benchmark 2: Generación de features
    logger.info("\n📊 FASE 2: Generación de Features Técnicas")
    logger.info("-" * 40)
    feature_benchmark = benchmark_feature_generation(df_50k)
    
    # Benchmark 3: Uso de memoria
    logger.info("\n📊 FASE 3: Análisis de Memoria")
    logger.info("-" * 40)
    memory_benchmark = benchmark_memory_usage(df_50k)
    
    # Benchmark 4: Predicción completa
    logger.info("\n📊 FASE 4: Predicción y Toma de Decisiones")
    logger.info("-" * 40)
    prediction_benchmark = await benchmark_prediction_time(df_50k)
    
    # Calcular tiempo total
    total_time = (model_benchmark['model_loading_time'] + 
                  feature_benchmark['feature_generation_time'] + 
                  prediction_benchmark['prediction_time'])
    
    # Resumen final
    logger.info("\n" + "=" * 70)
    logger.info("📋 RESUMEN EJECUTIVO - RENDIMIENTO CON 50,000 DATOS")
    logger.info("=" * 70)
    
    print(f"""
🎯 TIEMPO TOTAL DE ANÁLISIS: {total_time:.3f} segundos
   
⚡ DESGLOSE DE TIEMPOS:
   • Carga del modelo ML:     {model_benchmark['model_loading_time']:.3f}s
   • Generación de features:  {feature_benchmark['feature_generation_time']:.3f}s  
   • Predicción y decisión:   {prediction_benchmark['prediction_time']:.3f}s

🚀 RENDIMIENTO:
   • Records procesados/seg:  {prediction_benchmark['records_per_second']:,.0f}
   • Features generados/seg:  {feature_benchmark['features_per_second']:,.0f}
   • Throughput total:        {50000/total_time:,.0f} records/seg

💾 USO DE MEMORIA:
   • Datos originales:       {memory_benchmark['data_memory_mb']:.1f} MB
   • Features técnicas:      {memory_benchmark['features_memory_mb']:.1f} MB
   • Incremento de memoria:  {memory_benchmark['memory_increase_mb']:.1f} MB
   • Memoria total usada:    {memory_benchmark['memory_after_mb']:.1f} MB

🎯 RESULTADO DEL ANÁLISIS:
   • Decisión final:         {prediction_benchmark['decision']}
   • Score de confianza:     {prediction_benchmark['score']:.1f}/100
   • Nivel de confianza ML:  {prediction_benchmark['confidence_level']}
   • Estado del ML:          {prediction_benchmark['ml_status']}

⏰ TIEMPO REAL DE TRADING:
   • Tiempo por decisión:    {total_time:.3f}s
   • Decisiones por minuto:  {60/total_time:.0f}
   • Decisiones por hora:    {3600/total_time:.0f}

📊 EVALUACIÓN DE RENDIMIENTO:
   • {'🟢 EXCELENTE' if total_time < 1 else '🟡 BUENO' if total_time < 5 else '🟠 ACEPTABLE' if total_time < 10 else '🔴 LENTO'} - Tiempo de análisis
   • {'🟢 EFICIENTE' if memory_benchmark['memory_after_mb'] < 500 else '🟡 MODERADO' if memory_benchmark['memory_after_mb'] < 1000 else '🔴 ALTO'} - Uso de memoria
   • {'🟢 ÓPTIMO' if prediction_benchmark['records_per_second'] > 10000 else '🟡 BUENO' if prediction_benchmark['records_per_second'] > 5000 else '🔴 MEJORABLE'} - Throughput
""")

    # Guardar resultados detallados
    results = {
        'timestamp': datetime.now().isoformat(),
        'data_points': 50000,
        'total_analysis_time': total_time,
        'model_loading': model_benchmark,
        'feature_generation': feature_benchmark,
        'memory_usage': memory_benchmark,
        'prediction': prediction_benchmark,
        'performance_rating': 'EXCELLENT' if total_time < 1 else 'GOOD' if total_time < 5 else 'ACCEPTABLE' if total_time < 10 else 'SLOW'
    }
    
    import json
    with open('data/performance_benchmark_50k.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n💾 Resultados guardados: data/performance_benchmark_50k.json")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_full_benchmark())
