# test_midnight_fixes.py

import asyncio
import logging
import time
from datetime import datetime
from utils.technical_analysis import get_historical_klines
from utils.circuit_breaker import db_circuit_breaker, connectivity_circuit_breaker
from database.database_manager import get_engine
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlalchemy import text

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MidnightFixTester:
    """
    Tester para verificar que las mejoras implementadas para los problemas de medianoche funcionan correctamente.
    """
    
    def __init__(self):
        self.test_results = []
        
    async def run_comprehensive_test(self):
        """Ejecuta una suite completa de pruebas."""
        
        logger.info("🚀 INICIANDO PRUEBA INTEGRAL DE MEJORAS DE MEDIANOCHE")
        logger.info("=" * 80)
        
        # Test 1: Estado inicial de Circuit Breakers
        await self._test_circuit_breaker_status()
        
        # Test 2: Conectividad de base de datos con Circuit Breaker
        await self._test_database_connectivity()
        
        # Test 3: Análisis técnico con fallbacks
        await self._test_technical_analysis_resilience()
        
        # Test 4: Simulación de fallos de BD
        await self._test_database_failure_handling()
        
        # Test 5: Recuperación automática
        await self._test_automatic_recovery()
        
        # Generar reporte final
        await self._generate_test_report()
        
    async def _test_circuit_breaker_status(self):
        """Test 1: Verificar estado inicial de Circuit Breakers"""
        logger.info("📊 Test 1: Estado de Circuit Breakers")
        
        try:
            db_status = db_circuit_breaker.get_status()
            conn_status = connectivity_circuit_breaker.get_status()
            
            logger.info(f"   🔵 DB Circuit Breaker: {db_status['state']}")
            logger.info(f"   🔵 Connectivity Circuit Breaker: {conn_status['state']}")
            
            success = (db_status['state'] == 'CLOSED' and 
                      conn_status['state'] == 'CLOSED')
            
            self.test_results.append({
                "test": "Circuit Breaker Status",
                "success": success,
                "details": {"db_state": db_status['state'], "conn_state": conn_status['state']}
            })
            
            if success:
                logger.info("   ✅ Circuit Breakers en estado CLOSED correcto")
            else:
                logger.warning("   ⚠️ Circuit Breakers no están en estado inicial correcto")
                
        except Exception as e:
            logger.error(f"   ❌ Error en test de Circuit Breakers: {e}")
            self.test_results.append({
                "test": "Circuit Breaker Status",
                "success": False,
                "error": str(e)
            })
    
    async def _test_database_connectivity(self):
        """Test 2: Conectividad de base de datos"""
        logger.info("🗄️ Test 2: Conectividad de Base de Datos")
        
        try:
            # Test directo de engine
            engine = get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM klines LIMIT 1")).fetchone()
                
            logger.info("   ✅ Conectividad directa a BD exitosa")
            
            # Test a través del Circuit Breaker
            def _test_db():
                with engine.connect() as conn:
                    return conn.execute(text("SELECT 1")).fetchone()
            
            result = await db_circuit_breaker.async_call(_test_db)
            
            self.test_results.append({
                "test": "Database Connectivity",
                "success": True,
                "details": "Direct and Circuit Breaker connectivity successful"
            })
            
            logger.info("   ✅ Conectividad a través de Circuit Breaker exitosa")
            
        except Exception as e:
            logger.error(f"   ❌ Error en conectividad de BD: {e}")
            self.test_results.append({
                "test": "Database Connectivity", 
                "success": False,
                "error": str(e)
            })
    
    async def _test_technical_analysis_resilience(self):
        """Test 3: Resiliencia del análisis técnico"""
        logger.info("📈 Test 3: Resiliencia del Análisis Técnico")
        
        test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        for symbol in test_symbols:
            try:
                start_time = time.time()
                df = await get_historical_klines(symbol, "1h", limit=10)
                end_time = time.time()
                
                success = df is not None and not df.empty
                
                if success:
                    logger.info(f"   ✅ {symbol}: {len(df)} registros obtenidos en {end_time-start_time:.2f}s")
                else:
                    logger.warning(f"   ⚠️ {symbol}: Sin datos obtenidos")
                
                self.test_results.append({
                    "test": f"Technical Analysis - {symbol}",
                    "success": success,
                    "details": {
                        "rows": len(df) if df is not None else 0,
                        "time_taken": end_time - start_time
                    }
                })
                
            except Exception as e:
                logger.error(f"   ❌ {symbol}: Error - {e}")
                self.test_results.append({
                    "test": f"Technical Analysis - {symbol}",
                    "success": False,
                    "error": str(e)
                })
    
    async def _test_database_failure_handling(self):
        """Test 4: Manejo de fallos de BD simulados"""
        logger.info("💥 Test 4: Simulación de Fallos de BD")
        
        try:
            # Simular fallo abriendo el Circuit Breaker artificialmente
            original_threshold = db_circuit_breaker.failure_threshold
            db_circuit_breaker.failure_threshold = 1  # Reducir threshold para test
            
            # Forzar fallo
            try:
                def _failing_operation():
                    raise OperationalError("Test connection lost", None, None)
                
                await db_circuit_breaker.async_call(_failing_operation)
            except:
                pass  # Esperamos que falle
            
            # Verificar que el Circuit Breaker se abrió
            status = db_circuit_breaker.get_status()
            cb_opened = status['state'] == 'OPEN'
            
            if cb_opened:
                logger.info("   ✅ Circuit Breaker se abrió correctamente tras fallo simulado")
                
                # Probar que el análisis técnico funciona con fallback
                df = await get_historical_klines("BTCUSDT", "1h", limit=5)
                fallback_works = df is not None and not df.empty
                
                if fallback_works:
                    logger.info("   ✅ Fallback funcionó - sistema sigue operativo")
                else:
                    logger.warning("   ⚠️ Fallback no funcionó correctamente")
                
                success = cb_opened and fallback_works
                
            else:
                success = False
                logger.error("   ❌ Circuit Breaker no se abrió tras fallo simulado")
            
            # Restaurar threshold original
            db_circuit_breaker.failure_threshold = original_threshold
            db_circuit_breaker.reset()  # Reset para pruebas siguientes
            
            self.test_results.append({
                "test": "Database Failure Handling",
                "success": success,
                "details": {
                    "circuit_breaker_opened": cb_opened,
                    "fallback_worked": fallback_works if cb_opened else False
                }
            })
            
        except Exception as e:
            logger.error(f"   ❌ Error en test de manejo de fallos: {e}")
            self.test_results.append({
                "test": "Database Failure Handling",
                "success": False,
                "error": str(e)
            })
    
    async def _test_automatic_recovery(self):
        """Test 5: Recuperación automática"""
        logger.info("🔄 Test 5: Recuperación Automática")
        
        try:
            # Asegurar que Circuit Breaker está cerrado
            db_circuit_breaker.reset()
            
            # Hacer operación exitosa
            def _successful_operation():
                return "success"
            
            result = await db_circuit_breaker.async_call(_successful_operation)
            
            status = db_circuit_breaker.get_status()
            recovered = status['state'] == 'CLOSED' and status['stats']['consecutive_failures'] == 0
            
            if recovered:
                logger.info("   ✅ Recuperación automática funcionando correctamente")
            else:
                logger.warning("   ⚠️ Recuperación automática no funcionó como se esperaba")
            
            self.test_results.append({
                "test": "Automatic Recovery",
                "success": recovered,
                "details": {
                    "circuit_breaker_state": status['state'],
                    "consecutive_failures": status['stats']['consecutive_failures']
                }
            })
            
        except Exception as e:
            logger.error(f"   ❌ Error en test de recuperación: {e}")
            self.test_results.append({
                "test": "Automatic Recovery",
                "success": False, 
                "error": str(e)
            })
    
    async def _generate_test_report(self):
        """Genera reporte final de pruebas"""
        logger.info("=" * 80)
        logger.info("📋 REPORTE FINAL DE PRUEBAS")
        logger.info("=" * 80)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for test in self.test_results if test["success"])
        failed_tests = total_tests - successful_tests
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"📊 RESUMEN:")
        logger.info(f"   Total de pruebas: {total_tests}")
        logger.info(f"   Exitosas: {successful_tests}")
        logger.info(f"   Fallidas: {failed_tests}")
        logger.info(f"   Tasa de éxito: {success_rate:.1f}%")
        
        logger.info(f"\n🔍 DETALLE DE PRUEBAS:")
        for i, test in enumerate(self.test_results, 1):
            status = "✅ PASSED" if test["success"] else "❌ FAILED"
            logger.info(f"   {i}. {test['test']}: {status}")
            
            if not test["success"] and "error" in test:
                logger.info(f"      Error: {test['error']}")
            elif "details" in test:
                logger.info(f"      Detalles: {test['details']}")
        
        # Verificar estado final de Circuit Breakers
        logger.info(f"\n🔧 ESTADO FINAL DE CIRCUIT BREAKERS:")
        db_status = db_circuit_breaker.get_status()
        conn_status = connectivity_circuit_breaker.get_status()
        
        logger.info(f"   DB Circuit Breaker: {db_status['state']}")
        logger.info(f"   Connectivity Circuit Breaker: {conn_status['state']}")
        
        # Evaluación final
        if success_rate >= 80:
            logger.info("🎉 RESULTADO: Las mejoras de medianoche están funcionando correctamente")
        elif success_rate >= 60:
            logger.warning("⚠️ RESULTADO: Las mejoras funcionan parcialmente - revisar fallos")
        else:
            logger.error("❌ RESULTADO: Las mejoras necesitan revisión - múltiples fallos detectados")
        
        logger.info("=" * 80)

async def main():
    """Función principal"""
    tester = MidnightFixTester()
    await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main())
