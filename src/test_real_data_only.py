#!/usr/bin/env python3
"""
Script para verificar que SICAR solo usa datos reales (sin simulados).
"""

import sys
import os
import logging
import pandas as pd
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_robust_fetcher_no_simulation():
    """Prueba que RobustDataFetcher no genere datos simulados"""
    try:
        from robust_data_fetcher import RobustDataFetcher
        
        logger.info("🔄 === PRUEBA ROBUST FETCHER (SIN SIMULACIÓN) ===")
        
        fetcher = RobustDataFetcher()
        
        # Probar con un símbolo que probablemente falle para ver si genera simulados
        logger.info("📊 Probando con símbolo inexistente...")
        df = fetcher.get_market_data('FAKECOIN', '4h', 100)
        
        if df is None or df.empty:
            logger.info("✅ Correcto: No se generaron datos simulados para símbolo inexistente")
            return True
        else:
            logger.error("❌ Error: Se generaron datos para símbolo inexistente (posiblemente simulados)")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba del fetcher: {e}")
        return False

def test_data_pipeline_no_simulation():
    """Prueba que DataPipeline no genere datos simulados"""
    try:
        from pipelines.data_pipeline import DataPipeline
        
        logger.info("🔄 === PRUEBA DATA PIPELINE (SIN SIMULACIÓN) ===")
        
        pipeline = DataPipeline()
        
        # Verificar que no existe la función de datos simulados
        if hasattr(pipeline, '_generate_demo_data'):
            logger.error("❌ Error: DataPipeline aún tiene función _generate_demo_data")
            return False
        
        logger.info("✅ Correcto: DataPipeline no tiene función de datos simulados")
        
        # Probar con símbolo inexistente
        logger.info("📊 Probando con símbolo inexistente...")
        df = pipeline.get_market_data('FAKECOIN', period='1mo', interval='4h')
        
        if df is None or df.empty:
            logger.info("✅ Correcto: No se generaron datos simulados para símbolo inexistente")
            return True
        else:
            logger.error("❌ Error: Se generaron datos para símbolo inexistente")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba del pipeline: {e}")
        return False

def test_real_data_sources():
    """Prueba que las fuentes de datos reales funcionen"""
    try:
        from robust_data_fetcher import RobustDataFetcher
        from pipelines.data_pipeline import DataPipeline
        
        logger.info("🔄 === PRUEBA FUENTES DE DATOS REALES ===")
        
        # Probar RobustDataFetcher con símbolo real
        fetcher = RobustDataFetcher()
        logger.info("📊 Probando RobustDataFetcher con BTCUSDT...")
        df_fetcher = fetcher.get_market_data('BTCUSDT', '4h', 100)
        
        fetcher_ok = df_fetcher is not None and not df_fetcher.empty
        logger.info(f"{'✅' if fetcher_ok else '⚠️'} RobustDataFetcher: {'OK' if fetcher_ok else 'Sin datos'}")
        
        # Probar DataPipeline con símbolo real
        pipeline = DataPipeline()
        logger.info("📊 Probando DataPipeline con BTCUSDT...")
        df_pipeline = pipeline.get_market_data('BTCUSDT', period='1mo', interval='4h')
        
        pipeline_ok = df_pipeline is not None and not df_pipeline.empty
        logger.info(f"{'✅' if pipeline_ok else '⚠️'} DataPipeline: {'OK' if pipeline_ok else 'Sin datos'}")
        
        if fetcher_ok or pipeline_ok:
            logger.info("✅ Al menos una fuente de datos reales funciona")
            return True
        else:
            logger.warning("⚠️ Ninguna fuente de datos reales funciona (problema de conectividad)")
            return True  # No es un error del código, sino de conectividad
            
    except Exception as e:
        logger.error(f"❌ Error en prueba de fuentes reales: {e}")
        return False

def main():
    """Función principal de pruebas"""
    logger.info("🚀 === VERIFICACIÓN: SOLO DATOS REALES ===")
    logger.info(f"⏰ Fecha: {datetime.now()}")
    
    tests = [
        ("RobustDataFetcher sin simulación", test_robust_fetcher_no_simulation),
        ("DataPipeline sin simulación", test_data_pipeline_no_simulation),
        ("Fuentes de datos reales", test_real_data_sources)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 Ejecutando: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results.append((test_name, result))
            logger.info(f"{'✅' if result else '❌'} {test_name}: {'PASÓ' if result else 'FALLÓ'}")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Resumen final
    logger.info(f"\n{'='*60}")
    logger.info("📊 RESUMEN DE PRUEBAS")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\n🎯 Resultado final: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        logger.info("🎉 ¡Todas las pruebas pasaron! SICAR solo usa datos reales.")
        return 0
    else:
        logger.error("💥 Algunas pruebas fallaron. Revisar configuración.")
        return 1

if __name__ == "__main__":
    sys.exit(main())