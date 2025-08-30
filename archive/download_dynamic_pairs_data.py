#!/usr/bin/env python3
"""
Script para descargar datos históricos de los pares seleccionados dinámicamente
Este script lee la selección dinámica actual y descarga datos para esos pares
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Agregar el directorio padre al sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from download_historical_data import download_and_save_klines
from utils.logger_setup import setup_logging
from utils.structured_logger import StructuredLogger

setup_logging()
logger = StructuredLogger(__name__)

async def download_dynamic_pairs_data():
    """
    Descargar datos históricos para los pares seleccionados dinámicamente
    """
    
    logger.info("DYNAMIC_DOWNLOAD_START", "Iniciando descarga de datos para pares dinámicos")
    
    # Leer pares seleccionados dinámicamente
    dynamic_pairs_file = Path("data/dynamic_system/selected_pairs.json")
    
    if not dynamic_pairs_file.exists():
        logger.error("DYNAMIC_PAIRS_NOT_FOUND", "No se encontró archivo de pares dinámicos")
        print("❌ No se encontró selección dinámica de pares")
        print("🔍 Ejecuta primero el sistema dinámico o run_bot.py")
        return False
    
    try:
        with open(dynamic_pairs_file, 'r') as f:
            pairs_data = json.load(f)
            
        pairs_to_download = pairs_data.get('pairs', [])
        
        if not pairs_to_download:
            logger.error("DYNAMIC_PAIRS_EMPTY", "Lista de pares dinámicos está vacía")
            print("❌ No hay pares para descargar")
            return False
            
        logger.info("DYNAMIC_PAIRS_FOUND", f"Encontrados {len(pairs_to_download)} pares dinámicos", 
                   details={"pairs": pairs_to_download})
        
        print(f"🎯 DESCARGANDO DATOS PARA {len(pairs_to_download)} PARES DINÁMICOS")
        print("=" * 60)
        
        # Descargar datos para cada par
        successful_downloads = 0
        failed_downloads = []
        
        for i, pair in enumerate(pairs_to_download, 1):
            try:
                print(f"\n📊 {i}/{len(pairs_to_download)}: Descargando {pair}")
                logger.info("PAIR_DOWNLOAD_START", f"Iniciando descarga para {pair}")
                
                await download_and_save_klines(
                    symbol=pair,
                    interval="1h",
                    start_str="1 Jan, 2022",  # ~3 años de datos
                    append_to_existing=False  # Descarga completa
                )
                
                successful_downloads += 1
                print(f"✅ {pair} descargado exitosamente")
                logger.info("PAIR_DOWNLOAD_SUCCESS", f"Descarga exitosa para {pair}")
                
            except Exception as e:
                failed_downloads.append(pair)
                print(f"❌ Error descargando {pair}: {e}")
                logger.error("PAIR_DOWNLOAD_ERROR", f"Error descargando {pair}: {e}", 
                           details={"pair": pair}, exc_info=True)
        
        # Reporte final
        print("\n" + "=" * 60)
        print("📋 REPORTE DE DESCARGA DE PARES DINÁMICOS")
        print("=" * 60)
        print(f"✅ Descargas exitosas: {successful_downloads}/{len(pairs_to_download)}")
        
        if failed_downloads:
            print(f"❌ Descargas fallidas: {len(failed_downloads)}")
            print(f"   Pares fallidos: {', '.join(failed_downloads)}")
        
        success_rate = (successful_downloads / len(pairs_to_download)) * 100
        print(f"📊 Tasa de éxito: {success_rate:.1f}%")
        
        if successful_downloads >= len(pairs_to_download) * 0.75:  # 75% éxito mínimo
            print("\n🎉 DESCARGA COMPLETADA EXITOSAMENTE")
            print("🚀 El sistema dinámico está listo para operar")
            logger.info("DYNAMIC_DOWNLOAD_SUCCESS", 
                       f"Descarga completada: {successful_downloads}/{len(pairs_to_download)} pares")
            return True
        else:
            print("\n⚠️ DESCARGA PARCIALMENTE EXITOSA")
            print("🔄 Considera reintentar la descarga")
            logger.warning("DYNAMIC_DOWNLOAD_PARTIAL", 
                          f"Descarga parcial: {successful_downloads}/{len(pairs_to_download)} pares")
            return False
            
    except Exception as e:
        logger.error("DYNAMIC_DOWNLOAD_CRITICAL", f"Error crítico en descarga dinámica: {e}", exc_info=True)
        print(f"💥 Error crítico: {e}")
        return False

async def main():
    """Función principal"""
    
    print("🤖 DESCARGA DE DATOS PARA PARES DINÁMICOS")
    print("=" * 50)
    print("📥 Este script descarga datos históricos para los")
    print("   pares seleccionados automáticamente por el sistema dinámico")
    print("=" * 50)
    
    try:
        success = await download_dynamic_pairs_data()
        
        if success:
            print("\n✅ ¡PROCESO COMPLETADO EXITOSAMENTE!")
            print("🎯 Los pares dinámicos tienen datos históricos")
            print("🚀 El bot puede ejecutar análisis completos")
            return 0
        else:
            print("\n⚠️ Proceso completado con errores")
            print("🔄 Reintentar descarga si es necesario")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Descarga interrumpida por el usuario")
        return 1
    except Exception as e:
        print(f"\n💥 Error fatal: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
