#!/usr/bin/env python3
"""
Script de prueba para verificar la corrección del sistema XAI integrado
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('test_xai_integration.log')
    ]
)
logger = logging.getLogger(__name__)

# Agregar el directorio actual al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_xai_integration():
    """Probar la integración XAI corregida"""
    try:
        logger.info("🧪 Iniciando prueba de integración XAI corregida...")
        
        # Importar el gestor de integración
        from enhanced_integration_manager import INTEGRATION_MANAGER
        
        logger.info("✅ Gestor de integración importado correctamente")
        
        # Iniciar la integración
        logger.info("🚀 Iniciando integración mejorada...")
        result = await INTEGRATION_MANAGER.start_enhanced_integration()
        
        if result:
            logger.info("✅ Integración iniciada correctamente")
            
            # Esperar un momento para que se inicialicen los sistemas
            await asyncio.sleep(5)
            
            # Verificar el estado de la integración
            status = INTEGRATION_MANAGER.get_integration_status()
            logger.info(f"📊 Estado de integración: {status}")
            
            # Probar la generación de análisis XAI
            logger.info("🧠 Probando generación de análisis XAI...")
            xai_analysis = await INTEGRATION_MANAGER._generate_integrated_xai_analysis()
            
            if xai_analysis:
                logger.info("✅ Análisis XAI generado correctamente")
                logger.info(f"📄 Contenido del análisis: {str(xai_analysis)[:200]}...")
            else:
                logger.warning("⚠️ No se pudo generar análisis XAI")
            
            # Generar reporte de integración
            logger.info("📋 Generando reporte de integración...")
            report = INTEGRATION_MANAGER.generate_integration_report()
            logger.info(f"📊 Reporte generado: {report.get('integration_summary', {})}")
            
            # Esperar un poco más para observar el funcionamiento
            logger.info("⏳ Observando funcionamiento por 30 segundos...")
            await asyncio.sleep(30)
            
            # Detener la integración
            logger.info("🛑 Deteniendo integración...")
            stop_result = await INTEGRATION_MANAGER.stop_enhanced_integration()
            
            if stop_result:
                logger.info("✅ Integración detenida correctamente")
            else:
                logger.error("❌ Error deteniendo integración")
                
        else:
            logger.error("❌ Error iniciando integración")
            
    except Exception as e:
        logger.error(f"❌ Error en prueba de integración: {str(e)}")
        import traceback
        logger.error(f"📍 Traceback: {traceback.format_exc()}")

async def main():
    """Función principal"""
    try:
        logger.info("🎯 Iniciando script de prueba XAI Integration Fix")
        logger.info(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await test_xai_integration()
        
        logger.info("✅ Prueba completada")
        
    except KeyboardInterrupt:
        logger.info("⏹️ Prueba interrumpida por el usuario")
    except Exception as e:
        logger.error(f"❌ Error general: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())