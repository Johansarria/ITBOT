#!/usr/bin/env python3
"""
Programador de Reportes de Integración
Ejecuta reportes automáticamente cada cierto tiempo
"""

import schedule
import time
import logging
from datetime import datetime
from integration_report_generator import IntegrationReportGenerator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduled_reports.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_scheduled_report():
    """Genera un reporte programado."""
    try:
        logger.info("🕐 Iniciando generación de reporte programado...")
        
        generator = IntegrationReportGenerator()
        report = generator.generate_integration_report()
        filepath = generator.save_report(report)
        
        # Log del resumen
        summary = report.get('executive_summary', {})
        logger.info("📊 Reporte generado:")
        for key, value in summary.items():
            logger.info(f"  {value}")
        
        logger.info(f"💾 Reporte guardado en: {filepath}")
        
        # Escribir al log de enhanced_integration.log
        try:
            import os
            enhanced_log = os.path.join(os.path.dirname(__file__), 'logs', 'enhanced_integration.log')
            with open(enhanced_log, 'a', encoding='utf-8') as f:
                f.write(f"\n{datetime.now().isoformat()} - INTEGRATION REPORT GENERATED\n")
                f.write(f"Report ID: {report.get('report_id')}\n")
                f.write(f"Status: {summary.get('status', 'Unknown')}\n")
                f.write(f"Activity: {summary.get('activity', 'Unknown')}\n")
                f.write(f"Health: {summary.get('health', 'Unknown')}\n")
                f.write(f"File: {filepath}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            logger.warning(f"Error escribiendo a enhanced_integration.log: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error generando reporte programado: {e}")
        return False

def main():
    """Función principal del programador."""
    logger.info("🚀 Iniciando programador de reportes de integración...")
    
    # Programar reportes
    schedule.every(30).minutes.do(generate_scheduled_report)  # Cada 30 minutos
    schedule.every().hour.do(generate_scheduled_report)       # Cada hora
    schedule.every(6).hours.do(generate_scheduled_report)     # Cada 6 horas
    schedule.every().day.at("09:00").do(generate_scheduled_report)  # Diario a las 9 AM
    
    logger.info("📅 Reportes programados:")
    logger.info("  - Cada 30 minutos")
    logger.info("  - Cada hora")
    logger.info("  - Cada 6 horas")
    logger.info("  - Diario a las 9:00 AM")
    
    # Generar reporte inicial
    logger.info("📊 Generando reporte inicial...")
    generate_scheduled_report()
    
    # Loop principal
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
            
    except KeyboardInterrupt:
        logger.info("🛑 Programador detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error en el programador: {e}")

if __name__ == "__main__":
    main()