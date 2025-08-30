#!/usr/bin/env python3
"""
Script de reentrenamiento automático del modelo ML
Ejecuta reentrenamiento periódico con datos actualizados
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/ml_retraining.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def check_model_performance():
    """Verifica si el modelo necesita reentrenamiento"""
    
    try:
        from utils.ml_monitor import ml_monitor
        
        # Obtener estadísticas recientes
        stats_24h = ml_monitor.get_recent_stats(hours=24)
        stats_7d = ml_monitor.get_recent_stats(hours=168)  # 7 días
        
        logger.info("📊 Evaluando rendimiento del modelo ML...")
        
        if "error" in stats_24h:
            logger.warning(f"No hay datos recientes: {stats_24h['error']}")
            return False, "No hay datos suficientes para evaluar"
        
        # Criterios para reentrenamiento
        needs_retrain = False
        reasons = []
        
        # 1. Baja confianza en predicciones
        if stats_24h.get('avg_max_probability', 1.0) < 0.6:
            needs_retrain = True
            reasons.append(f"Baja confianza promedio: {stats_24h['avg_max_probability']:.3f}")
        
        # 2. Demasiadas predicciones neutras (MANTENER)
        mantener_pct = stats_24h.get('decision_counts', {}).get('MANTENER', 0) / stats_24h.get('total_predictions', 1)
        if mantener_pct > 0.8:
            needs_retrain = True
            reasons.append(f"Exceso de decisiones MANTENER: {mantener_pct:.1%}")
        
        # 3. Poca diferencia entre probabilidades (modelo indeciso)
        if stats_24h.get('avg_probability_diff', 1.0) < 0.1:
            needs_retrain = True
            reasons.append(f"Diferencias de probabilidad muy bajas: {stats_24h['avg_probability_diff']:.3f}")
        
        # 4. Modelo muy antiguo (verificar fecha del archivo)
        try:
            model_file = Path("lightgbm_model.pkl")
            if model_file.exists():
                model_age = datetime.now() - datetime.fromtimestamp(model_file.stat().st_mtime)
                if model_age.days > 30:
                    needs_retrain = True
                    reasons.append(f"Modelo antiguo: {model_age.days} días")
        except Exception as e:
            logger.warning(f"Error verificando edad del modelo: {e}")
        
        # Log resultados
        if needs_retrain:
            logger.warning(f"🚨 REENTRENAMIENTO RECOMENDADO:")
            for reason in reasons:
                logger.warning(f"   • {reason}")
        else:
            logger.info("✅ Modelo funcionando correctamente, no necesita reentrenamiento")
        
        return needs_retrain, reasons
        
    except Exception as e:
        logger.error(f"Error evaluando rendimiento del modelo: {e}")
        return False, [f"Error en evaluación: {str(e)}"]

async def retrain_model(force: bool = False):
    """Ejecuta reentrenamiento del modelo"""
    
    logger.info("🔄 Iniciando proceso de reentrenamiento...")
    
    try:
        # Verificar si es necesario el reentrenamiento
        if not force:
            needs_retrain, reasons = await check_model_performance()
            if not needs_retrain:
                logger.info("⏭️ Saltando reentrenamiento - no es necesario")
                return True
            else:
                logger.info(f"✅ Reentrenamiento justificado: {', '.join(reasons)}")
        
        # Actualizar datos históricos
        logger.info("📥 Actualizando datos históricos...")
        import subprocess
        result = subprocess.run([sys.executable, "download_historical_data.py"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning(f"Advertencia en descarga de datos: {result.stderr}")
        
        # Ejecutar entrenamiento
        logger.info("🤖 Iniciando entrenamiento del modelo...")
        result = subprocess.run([sys.executable, "ml_model_trainer.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ Reentrenamiento completado exitosamente")
            logger.info(f"Salida del entrenamiento: {result.stdout}")
            
            # Crear backup del modelo anterior
            import shutil
            backup_name = f"lightgbm_model_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            try:
                if Path("lightgbm_model.pkl").exists():
                    Path("storage").mkdir(exist_ok=True)
                    shutil.copy2("lightgbm_model.pkl", f"storage/{backup_name}")
                    logger.info(f"💾 Backup creado: {backup_name}")
            except Exception as e:
                logger.warning(f"Error creando backup: {e}")
            
            return True
        else:
            logger.error(f"❌ Error durante el reentrenamiento: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en reentrenamiento: {e}")
        return False

async def main():
    """Función principal"""
    
    parser = argparse.ArgumentParser(description="Reentrenamiento automático del modelo ML")
    parser.add_argument("--force", action="store_true", help="Forzar reentrenamiento sin verificar rendimiento")
    parser.add_argument("--check-only", action="store_true", help="Solo verificar si se necesita reentrenamiento")
    parser.add_argument("--stats", action="store_true", help="Mostrar estadísticas del modelo")
    
    args = parser.parse_args()
    
    logger.info("🚀 Iniciando script de reentrenamiento ML")
    
    try:
        if args.stats:
            from utils.ml_monitor import ml_monitor
            
            print("📊 ESTADÍSTICAS DEL MODELO ML")
            print("=" * 50)
            
            stats_24h = ml_monitor.get_recent_stats(hours=24)
            distribution = ml_monitor.get_prediction_distribution()
            
            if "error" not in stats_24h:
                print(f"Predicciones (24h): {stats_24h['total_predictions']}")
                print(f"Confianza promedio: {stats_24h['avg_max_probability']:.3f}")
                print(f"Decisiones:")
                for decision, count in stats_24h['decision_counts'].items():
                    print(f"  • {decision}: {count}")
            
            if "error" not in distribution:
                print(f"\nDistribución de probabilidades:")
                print(f"  • Buy promedio: {distribution['buy_probability_stats']['mean']:.3f}")
                print(f"  • Sell promedio: {distribution['sell_probability_stats']['mean']:.3f}")
            
            return
        
        if args.check_only:
            needs_retrain, reasons = await check_model_performance()
            if needs_retrain:
                print("🚨 REENTRENAMIENTO RECOMENDADO:")
                for reason in reasons:
                    print(f"   • {reason}")
                sys.exit(1)  # Exit code 1 indica que se necesita reentrenamiento
            else:
                print("✅ Modelo funcionando correctamente")
                sys.exit(0)
        
        # Ejecutar reentrenamiento
        success = await retrain_model(force=args.force)
        
        if success:
            logger.info("🎉 Proceso completado exitosamente")
            sys.exit(0)
        else:
            logger.error("💥 Proceso fallido")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Proceso interrumpido por el usuario")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Error inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
