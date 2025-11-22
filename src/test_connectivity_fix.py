#!/usr/bin/env python3
"""
Script de prueba para verificar las correcciones de conectividad
"""

import sys
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_robust_data_fetcher():
    """Prueba el fetcher robusto de datos"""
    try:
        from robust_data_fetcher import RobustDataFetcher
        
        logger.info("🧪 === PRUEBA DEL FETCHER ROBUSTO ===")
        
        # Crear instancia del fetcher
        fetcher = RobustDataFetcher()
        
        # Probar obtención de datos
        logger.info("📊 Probando obtención de datos para BTCUSDT...")
        df = fetcher.get_market_data('BTCUSDT', '4h', 100)
        
        if df is not None and not df.empty:
            logger.info(f"✅ Datos obtenidos exitosamente!")
            logger.info(f"📈 Filas: {len(df)}")
            logger.info(f"📊 Columnas: {list(df.columns)}")
            logger.info(f"📅 Período: {df.index[0]} a {df.index[-1]}")
            logger.info(f"💰 Precio actual: ${df['Close'].iloc[-1]:.2f}")
            return True
        else:
            logger.error("❌ No se pudieron obtener datos")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba del fetcher: {e}")
        return False

def test_main_bot_data_function():
    """Prueba la función de datos del bot principal"""
    try:
        from main_bot import get_binance_data
        
        logger.info("🤖 === PRUEBA DE FUNCIÓN DEL BOT PRINCIPAL ===")
        
        # Probar función del bot
        logger.info("📊 Probando función get_binance_data...")
        df = get_binance_data('BTCUSDT', '4h')
        
        if df is not None and not df.empty:
            logger.info(f"✅ Función del bot funciona correctamente!")
            logger.info(f"📈 Filas: {len(df)}")
            logger.info(f"📊 Columnas: {list(df.columns)}")
            logger.info(f"💰 Precio actual: ${df['Close'].iloc[-1]:.2f}")
            return True
        else:
            logger.error("❌ La función del bot no pudo obtener datos")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba del bot: {e}")
        return False

def test_data_pipeline():
    """Prueba el pipeline de datos actualizado"""
    try:
        from pipelines.data_pipeline import DataPipeline
        
        logger.info("🔄 === PRUEBA DEL PIPELINE DE DATOS ===")
        
        # Crear pipeline
        pipeline = DataPipeline()
        
        # Probar obtención de datos
        logger.info("📊 Probando pipeline para BTCUSDT...")
        df = pipeline.get_market_data('BTCUSDT', period='1mo', interval='4h')
        
        if df is not None and not df.empty:
            logger.info(f"✅ Pipeline funciona correctamente!")
            logger.info(f"📈 Filas: {len(df)}")
            logger.info(f"📊 Columnas: {list(df.columns)}")
            return True
        else:
            logger.error("❌ El pipeline no pudo obtener datos")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en prueba del pipeline: {e}")
        return False

def main():
    """Función principal de pruebas"""
    logger.info("🚀 === INICIANDO PRUEBAS DE CONECTIVIDAD ===")
    logger.info(f"⏰ Hora: {datetime.now()}")
    
    results = []
    
    # Ejecutar pruebas
    logger.info("\n" + "="*50)
    results.append(("Fetcher Robusto", test_robust_data_fetcher()))
    
    logger.info("\n" + "="*50)
    results.append(("Función Bot Principal", test_main_bot_data_function()))
    
    logger.info("\n" + "="*50)
    results.append(("Pipeline de Datos", test_data_pipeline()))
    
    # Resumen de resultados
    logger.info("\n" + "="*50)
    logger.info("📋 === RESUMEN DE PRUEBAS ===")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("🎉 ¡TODAS LAS PRUEBAS PASARON!")
        logger.info("✅ Las correcciones de conectividad están funcionando")
    else:
        logger.error("⚠️ Algunas pruebas fallaron")
        logger.error("❌ Se requieren más correcciones")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)