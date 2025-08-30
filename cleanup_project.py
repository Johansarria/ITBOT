#!/usr/bin/env python3
"""
Script de Limpieza del Proyecto ITBOT
Remueve archivos temporales, experimentales y duplicados
"""

import os
import shutil
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def cleanup_project():
    """Limpia archivos temporales y experimentales del proyecto"""
    
    # Lista de archivos experimentales/temporales para mover a carpeta archive/
    experimental_files = [
        'analyze_20k_accuracy_projection.py',
        'performance_analysis_50k.py',
        'setup_100k_configuration.py',
        'download_150k_historical_data.py',
        'temp_download_real_data.py',
        'log_dummy_operation.py',
        'test_real_strategies.py',
        'check_historical_data.py',
        'improve_ml_accuracy.py',
        'analyze_ml_data_sufficiency.py',
        'final_50k_performance_test.py',
        'realtime_performance_analysis.py',
        'accuracy_analysis_50k.py',
        'comprehensive_volume_analysis.py',
        'prepare_100k_download.py',
        'download_100k_fixed.py',
        'download_100k_simple.py',
        'setup_150k_configuration.py',
        'analyze_150k_performance.py',
        'multi_pair_executive_report.py',
        'download_multi_pair_data.py',
        'train_multi_pair_models.py',
        'dynamic_trading_system.py',
        'test_dynamic_system.py',
        'demo_dynamic_system.py',
        'download_dynamic_pairs_data.py',
        'download_dynamic_multi_pair.py',
        'fix_data_reading.py',
    ]
    
    # Crear carpeta archive si no existe
    archive_dir = Path('archive')
    archive_dir.mkdir(exist_ok=True)
    
    moved_count = 0
    for filename in experimental_files:
        filepath = Path(filename)
        if filepath.exists():
            try:
                shutil.move(str(filepath), str(archive_dir / filename))
                logger.info(f"✓ Movido {filename} a archive/")
                moved_count += 1
            except Exception as e:
                logger.error(f"✗ Error moviendo {filename}: {e}")
    
    # Limpiar archivos de caché Python
    cache_patterns = [
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.pyd',
        '**/.pytest_cache',
        '**/.coverage',
        '**/htmlcov',
    ]
    
    cleaned_cache = 0
    for pattern in cache_patterns:
        for path in Path('.').glob(pattern):
            try:
                if path.is_file():
                    path.unlink()
                    cleaned_cache += 1
                elif path.is_dir():
                    shutil.rmtree(path)
                    cleaned_cache += 1
                logger.info(f"✓ Eliminado cache: {path}")
            except Exception as e:
                logger.error(f"✗ Error eliminando cache {path}: {e}")
    
    # Limpiar logs antiguos (mantener últimos 7 días)
    logs_dir = Path('logs')
    if logs_dir.exists():
        import time
        week_ago = time.time() - (7 * 24 * 60 * 60)
        
        for log_file in logs_dir.glob('*.log'):
            try:
                if log_file.stat().st_mtime < week_ago:
                    log_file.unlink()
                    logger.info(f"✓ Eliminado log antiguo: {log_file}")
            except Exception as e:
                logger.error(f"✗ Error eliminando log {log_file}: {e}")
    
    # Resumen
    logger.info(f"""
    
🧹 LIMPIEZA COMPLETADA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Archivos experimentales movidos: {moved_count}
✓ Archivos de caché eliminados: {cleaned_cache}
✓ Logs antiguos eliminados
✓ Proyecto optimizado

📁 Archivos experimentales archivados en: ./archive/
🗑️  Para eliminar definitivamente: rm -rf ./archive/
    """)

def check_code_quality():
    """Verifica calidad del código después de limpieza"""
    
    logger.info("\n🔍 VERIFICANDO CALIDAD DEL CÓDIGO:")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    issues = []
    
    # Verificar archivos críticos
    critical_files = [
        'run_bot.py',
        'main.py', 
        'config.py',
        'strategies/strategy_manager.py',
        'utils/technical_analysis.py',
        'database/database_manager.py'
    ]
    
    for file_path in critical_files:
        if not Path(file_path).exists():
            issues.append(f"❌ Archivo crítico faltante: {file_path}")
        else:
            logger.info(f"✓ Archivo crítico presente: {file_path}")
    
    # Verificar estructura de directorios
    required_dirs = [
        'strategies',
        'utils', 
        'database',
        'tests',
        'web',
        'modules',
        'data'
    ]
    
    for dir_name in required_dirs:
        if not Path(dir_name).is_dir():
            issues.append(f"❌ Directorio faltante: {dir_name}")
        else:
            logger.info(f"✓ Directorio presente: {dir_name}")
    
    if issues:
        logger.error("\n🚨 ISSUES ENCONTRADOS:")
        for issue in issues:
            logger.error(issue)
    else:
        logger.info("\n✅ CÓDIGO VERIFICADO - Sin issues críticos detectados")

if __name__ == "__main__":
    logger.info("🚀 Iniciando limpieza del proyecto ITBOT...")
    cleanup_project()
    check_code_quality()
    logger.info("🎉 Limpieza completada exitosamente!")
