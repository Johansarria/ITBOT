# circuit_breaker_monitor.py

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from utils.circuit_breaker import db_circuit_breaker, connectivity_circuit_breaker, CircuitBreakerState
from database.database_manager import get_engine
from sqlalchemy.exc import DisconnectionError, OperationalError, SQLAlchemyError

logger = logging.getLogger(__name__)

class CircuitBreakerMonitor:
    """
    Monitor de Circuit Breakers para detectar y reportar problemas de conectividad,
    especialmente durante eventos como rotación de logs de PostgreSQL a medianoche.
    """
    
    def __init__(self):
        self.monitoring = False
        self.monitoring_start = None
        self.alert_history = []
        
    async def start_monitoring(self, check_interval: int = 30):
        """
        Inicia el monitoreo continuo de Circuit Breakers.
        
        Args:
            check_interval: Intervalo en segundos entre chequeos
        """
        self.monitoring = True
        self.monitoring_start = datetime.now()
        
        logger.info(f"🔍 Iniciando monitoreo de Circuit Breakers (intervalo: {check_interval}s)")
        
        while self.monitoring:
            try:
                await self._perform_health_check()
                await asyncio.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoreo interrumpido por usuario")
                break
            except Exception as e:
                logger.error(f"Error en monitoreo: {e}")
                await asyncio.sleep(check_interval)
    
    async def _perform_health_check(self):
        """Realiza chequeo de salud de los Circuit Breakers."""
        now = datetime.now()
        
        # Chequear estado de los Circuit Breakers
        db_status = db_circuit_breaker.get_status()
        conn_status = connectivity_circuit_breaker.get_status()
        
        # Detectar problemas críticos
        critical_issues = []
        
        # Verificar si DB Circuit Breaker está abierto
        if db_status['state'] == CircuitBreakerState.OPEN.value:
            critical_issues.append("🔴 DB Circuit Breaker ABIERTO - Sin acceso a base de datos")
            
        # Verificar si hay muchos fallos consecutivos
        if db_status['stats']['consecutive_failures'] >= 2:
            critical_issues.append(f"⚠️ DB: {db_status['stats']['consecutive_failures']} fallos consecutivos")
            
        if conn_status['stats']['consecutive_failures'] >= 3:
            critical_issues.append(f"⚠️ Conectividad: {conn_status['stats']['consecutive_failures']} fallos consecutivos")
        
        # Probar conectividad real de BD si no hay problemas críticos
        if not critical_issues:
            try:
                await self._test_db_connectivity()
            except Exception as e:
                critical_issues.append(f"🔴 Test BD falló: {e}")
        
        # Reportar estado
        if critical_issues:
            alert = {
                "timestamp": now.isoformat(),
                "level": "CRITICAL" if any("🔴" in issue for issue in critical_issues) else "WARNING",
                "issues": critical_issues,
                "db_circuit_breaker": db_status,
                "connectivity_circuit_breaker": conn_status
            }
            
            self.alert_history.append(alert)
            
            # Log detallado
            logger.error("=" * 60)
            logger.error("🚨 CIRCUIT BREAKER ALERT")
            logger.error(f"⏰ Tiempo: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            for issue in critical_issues:
                logger.error(f"   {issue}")
            logger.error(f"📊 DB CB - Estado: {db_status['state']}, Fallos: {db_status['stats']['consecutive_failures']}")
            logger.error(f"📊 Conn CB - Estado: {conn_status['state']}, Fallos: {conn_status['stats']['consecutive_failures']}")
            logger.error("=" * 60)
            
        else:
            # Todo OK - log de estado periódico
            if now.minute % 5 == 0 and now.second < 30:  # Cada 5 minutos
                logger.info(f"✅ Circuit Breakers OK - DB: {db_status['state']}, Conn: {conn_status['state']}")
    
    async def _test_db_connectivity(self):
        """Prueba la conectividad real de la base de datos."""
        from sqlalchemy import text
        engine = get_engine()
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
            if not result:
                raise Exception("DB test query failed")
    
    def stop_monitoring(self):
        """Detiene el monitoreo."""
        self.monitoring = False
        logger.info("🛑 Monitoreo de Circuit Breakers detenido")
    
    def get_monitoring_report(self) -> dict:
        """Genera un reporte del estado de monitoreo."""
        now = datetime.now()
        
        return {
            "monitoring_status": "ACTIVE" if self.monitoring else "STOPPED",
            "monitoring_duration": str(now - self.monitoring_start) if self.monitoring_start else None,
            "total_alerts": len(self.alert_history),
            "recent_alerts": [
                alert for alert in self.alert_history 
                if datetime.fromisoformat(alert["timestamp"]) > (now - timedelta(hours=1))
            ],
            "circuit_breakers": {
                "database": db_circuit_breaker.get_status(),
                "connectivity": connectivity_circuit_breaker.get_status()
            }
        }
    
    def reset_circuit_breakers(self):
        """Resetea manualmente todos los Circuit Breakers."""
        logger.warning("🔄 Reseteando todos los Circuit Breakers manualmente")
        db_circuit_breaker.reset()
        connectivity_circuit_breaker.reset()
        logger.info("✅ Circuit Breakers reseteados")

async def main():
    """Función principal para ejecutar el monitor de Circuit Breakers."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('circuit_breaker_monitor.log')
        ]
    )
    
    monitor = CircuitBreakerMonitor()
    
    try:
        # Mostrar estado inicial
        report = monitor.get_monitoring_report()
        logger.info("📋 Estado inicial de Circuit Breakers:")
        logger.info(json.dumps(report, indent=2, ensure_ascii=False))
        
        # Iniciar monitoreo
        await monitor.start_monitoring(check_interval=30)
        
    except KeyboardInterrupt:
        logger.info("Monitoreo interrumpido")
    finally:
        monitor.stop_monitoring()
        
        # Reporte final
        final_report = monitor.get_monitoring_report()
        logger.info("📋 Reporte final de monitoreo:")
        logger.info(json.dumps(final_report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
