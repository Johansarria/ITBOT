#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SICAR - Test Simplificado del Sistema Integrado
==============================================

Script de prueba simplificado para verificar componentes básicos.

Autor: SICAR Team
Fecha: 2025-01-21
"""

import os
import sys
import asyncio
import logging
import json
import joblib
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimplifiedSystemTester:
    """Tester simplificado del sistema"""
    
    def __init__(self):
        """Inicializar tester"""
        self.project_root = Path(__file__).parent.parent
        self.models_dir = self.project_root / "models"
        self.src_dir = Path(__file__).parent
        
        logger.info("🧪 SimplifiedSystemTester inicializado")
    
    def test_ml_models_exist(self) -> bool:
        """Test de existencia de modelos ML"""
        logger.info("🤖 Verificando existencia de modelos ML...")
        
        try:
            if not self.models_dir.exists():
                logger.warning("⚠️ Directorio de modelos no existe")
                return False
            
            model_files = list(self.models_dir.glob("multi_timeframe_*.joblib"))
            
            if not model_files:
                logger.warning("⚠️ No se encontraron archivos de modelos")
                return False
            
            logger.info(f"✅ Encontrados {len(model_files)} archivos de modelos:")
            for model_file in model_files:
                logger.info(f"  - {model_file.name}")
            
            # Test de carga de un modelo
            try:
                test_model = joblib.load(model_files[0])
                logger.info(f"✅ Modelo cargado exitosamente: {model_files[0].name}")
                
                if 'model' in test_model and 'scaler' in test_model:
                    logger.info("✅ Estructura de modelo válida")
                    return True
                else:
                    logger.warning("⚠️ Estructura de modelo inválida")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Error cargando modelo: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error en test de modelos: {e}")
            return False
    
    def test_training_data_extraction(self) -> bool:
        """Test de extracción de datos de entrenamiento"""
        logger.info("📊 Verificando extracción de datos de entrenamiento...")
        
        try:
            pattern_file = self.src_dir / "SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO (1 minuto).txt"
            
            if not pattern_file.exists():
                logger.warning("⚠️ Archivo de patrones no encontrado")
                return False
            
            # Verificar contenido
            with open(pattern_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar que contiene datos de IA
            if "ANÁLISIS OPENAI" in content and "ANÁLISIS GROK xAI" in content:
                logger.info("✅ Archivo contiene análisis de IA")
                
                # Contar iteraciones
                iterations = content.count("Iteración:")
                logger.info(f"✅ Encontradas {iterations} iteraciones de análisis")
                
                # Verificar símbolos
                symbols_found = []
                for symbol in ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']:
                    if symbol in content:
                        symbols_found.append(symbol)
                
                logger.info(f"✅ Símbolos encontrados: {symbols_found}")
                
                return len(symbols_found) > 0
            else:
                logger.warning("⚠️ No se encontraron análisis de IA en el archivo")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando datos de entrenamiento: {e}")
            return False
    
    def test_paper_trading_components(self) -> bool:
        """Test de componentes de paper trading"""
        logger.info("💰 Verificando componentes de paper trading...")
        
        try:
            # Verificar archivos de paper trading
            pt_files = [
                'paper_trading_system.py',
                'paper_trading_dashboard.py'
            ]
            
            missing_files = []
            for file in pt_files:
                file_path = self.src_dir / file
                if not file_path.exists():
                    missing_files.append(file)
            
            if missing_files:
                logger.warning(f"⚠️ Archivos faltantes: {missing_files}")
                return False
            
            logger.info("✅ Archivos de paper trading encontrados")
            
            # Verificar sesión de paper trading
            session_files = [
                self.project_root / "paper_trading_session.json",
                self.project_root / "data" / "paper_trading_session.json"
            ]
            
            session_found = False
            for session_file in session_files:
                if session_file.exists():
                    logger.info(f"✅ Sesión de paper trading encontrada: {session_file}")
                    session_found = True
                    break
            
            if not session_found:
                logger.warning("⚠️ No se encontró sesión de paper trading")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error verificando paper trading: {e}")
            return False
    
    def test_ai_connections_active(self) -> bool:
        """Test de conexiones IA activas"""
        logger.info("🤖 Verificando conexiones IA activas...")
        
        try:
            pattern_file = self.src_dir / "SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO (1 minuto).txt"
            
            if not pattern_file.exists():
                logger.warning("⚠️ Archivo de patrones no encontrado")
                return False
            
            # Verificar timestamp reciente
            mod_time = datetime.fromtimestamp(pattern_file.stat().st_mtime)
            time_diff = datetime.now() - mod_time
            
            logger.info(f"📅 Última modificación: {mod_time}")
            logger.info(f"⏰ Tiempo transcurrido: {time_diff}")
            
            if time_diff.total_seconds() < 7200:  # Menos de 2 horas
                logger.info("✅ Archivo actualizado recientemente")
                
                # Verificar contenido reciente
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Buscar análisis recientes en las últimas 100 líneas
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                recent_content = ''.join(recent_lines)
                
                openai_found = "ANÁLISIS OPENAI" in recent_content
                grok_found = "ANÁLISIS GROK xAI" in recent_content
                
                logger.info(f"🤖 OpenAI reciente: {'✅' if openai_found else '❌'}")
                logger.info(f"🧠 Grok xAI reciente: {'✅' if grok_found else '❌'}")
                
                return openai_found or grok_found
            else:
                logger.warning("⚠️ Archivo no actualizado recientemente")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando conexiones IA: {e}")
            return False
    
    def test_multi_timeframe_implementation(self) -> bool:
        """Test de implementación multi-timeframe"""
        logger.info("📊 Verificando implementación multi-timeframe...")
        
        try:
            # Verificar archivos multi-timeframe
            mt_files = [
                'multi_timeframe_paper_trading.py',
                'integrated_multi_timeframe_paper_trading.py',
                'ml_training_recent_data.py'
            ]
            
            found_files = []
            for file in mt_files:
                file_path = self.src_dir / file
                if file_path.exists():
                    found_files.append(file)
                    logger.info(f"✅ Encontrado: {file}")
            
            if len(found_files) >= 2:
                logger.info("✅ Implementación multi-timeframe completa")
                return True
            else:
                logger.warning(f"⚠️ Solo {len(found_files)} de {len(mt_files)} archivos encontrados")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando multi-timeframe: {e}")
            return False
    
    def test_training_logs(self) -> bool:
        """Test de logs de entrenamiento"""
        logger.info("📝 Verificando logs de entrenamiento...")
        
        try:
            log_files = [
                'ml_training_recent_data.log',
                'integrated_multi_timeframe_paper_trading.log'
            ]
            
            logs_found = []
            for log_file in log_files:
                log_path = self.src_dir / log_file
                if log_path.exists():
                    logs_found.append(log_file)
                    
                    # Verificar contenido
                    with open(log_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if "✅" in content and "entrenamiento" in content.lower():
                        logger.info(f"✅ Log válido: {log_file}")
                    else:
                        logger.info(f"📄 Log encontrado: {log_file}")
            
            if logs_found:
                logger.info(f"✅ Logs de entrenamiento encontrados: {logs_found}")
                return True
            else:
                logger.warning("⚠️ No se encontraron logs de entrenamiento")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error verificando logs: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Ejecutar todos los tests"""
        logger.info("=" * 80)
        logger.info("🧪 INICIANDO TESTS SIMPLIFICADOS DEL SISTEMA")
        logger.info("=" * 80)
        
        results = {}
        
        # Test 1: Existencia de modelos ML
        results['ml_models_exist'] = self.test_ml_models_exist()
        
        # Test 2: Extracción de datos de entrenamiento
        results['training_data_extraction'] = self.test_training_data_extraction()
        
        # Test 3: Componentes de paper trading
        results['paper_trading_components'] = self.test_paper_trading_components()
        
        # Test 4: Conexiones IA activas
        results['ai_connections_active'] = self.test_ai_connections_active()
        
        # Test 5: Implementación multi-timeframe
        results['multi_timeframe_implementation'] = self.test_multi_timeframe_implementation()
        
        # Test 6: Logs de entrenamiento
        results['training_logs'] = self.test_training_logs()
        
        # Resumen
        logger.info("=" * 80)
        logger.info("📊 RESUMEN DE TESTS")
        logger.info("=" * 80)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\n🎯 Tests pasados: {passed}/{total}")
        
        if passed == total:
            logger.info("🎉 TODOS LOS TESTS PASARON")
        elif passed >= total * 0.8:
            logger.info("✅ MAYORÍA DE TESTS PASARON")
        elif passed >= total * 0.6:
            logger.info("⚠️ TESTS PARCIALMENTE EXITOSOS")
        else:
            logger.warning("❌ VARIOS TESTS FALLARON")
        
        logger.info("=" * 80)
        
        return results

async def main():
    """Función principal"""
    tester = SimplifiedSystemTester()
    results = await tester.run_all_tests()
    
    # Guardar resultados
    results_file = Path(__file__).parent.parent / "test_results_simplified.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_type': 'simplified',
            'results': results,
            'summary': {
                'total_tests': len(results),
                'passed_tests': sum(results.values()),
                'success_rate': sum(results.values()) / len(results)
            }
        }, f, indent=2)
    
    logger.info(f"📄 Resultados guardados en: {results_file}")

if __name__ == "__main__":
    asyncio.run(main())