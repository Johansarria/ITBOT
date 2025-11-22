#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SICAR - Ejecutor del Sistema Multi-Timeframe Paper Trading
=========================================================

Script principal para ejecutar el sistema de paper trading con análisis
multi-timeframe y modelos de ML entrenados.

Autor: SICAR Team
Fecha: 2025-01-21
"""

import os
import sys
import asyncio
import logging
import signal
from datetime import datetime
from pathlib import Path

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('multi_timeframe_paper_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Importar módulos del sistema
try:
    from integrated_multi_timeframe_paper_trading import IntegratedMultiTimeframePaperTrading
    from paper_trading_system import PaperTradingEngine
except ImportError as e:
    logger.error(f"❌ Error importando módulos: {e}")
    logger.info("💡 Usando modo de compatibilidad...")
    
    # Modo de compatibilidad
    class IntegratedMultiTimeframePaperTrading:
        def __init__(self, initial_capital=1000.0):
            self.initial_capital = initial_capital
            self.running = False
            logger.info(f"🔧 Modo compatibilidad - Capital inicial: ${initial_capital}")
        
        async def initialize(self):
            logger.info("🔧 Inicializando en modo compatibilidad...")
            return True
        
        async def start_monitoring(self):
            logger.info("🔧 Iniciando monitoreo en modo compatibilidad...")
            self.running = True
            while self.running:
                logger.info("📊 Simulando análisis multi-timeframe...")
                await asyncio.sleep(60)  # Análisis cada minuto

class MultiTimeframePaperTradingRunner:
    """Ejecutor del sistema multi-timeframe"""
    
    def __init__(self, initial_capital: float = 1000.0):
        """Inicializar ejecutor"""
        self.initial_capital = initial_capital
        self.system = None
        self.running = False
        
        logger.info("🚀 MultiTimeframePaperTradingRunner inicializado")
        logger.info(f"💰 Capital inicial: ${initial_capital}")
    
    async def initialize_system(self) -> bool:
        """Inicializar el sistema integrado"""
        logger.info("🔧 Inicializando sistema integrado...")
        
        try:
            self.system = IntegratedMultiTimeframePaperTrading(
                initial_capital=self.initial_capital
            )
            
            # Inicializar componentes
            init_success = await self.system.initialize()
            
            if init_success:
                logger.info("✅ Sistema integrado inicializado exitosamente")
                return True
            else:
                logger.warning("⚠️ Inicialización parcial del sistema")
                return True  # Continuar en modo limitado
                
        except Exception as e:
            logger.error(f"❌ Error inicializando sistema: {e}")
            return False
    
    def setup_signal_handlers(self):
        """Configurar manejadores de señales para cierre limpio"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Señal recibida: {signum}")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def stop(self):
        """Detener el sistema"""
        logger.info("🛑 Deteniendo sistema...")
        self.running = False
        
        if hasattr(self.system, 'running'):
            self.system.running = False
    
    async def run_monitoring_loop(self):
        """Ejecutar el bucle principal de monitoreo"""
        logger.info("🔄 Iniciando bucle de monitoreo...")
        
        self.running = True
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                logger.info(f"🔄 Iteración {iteration} - {datetime.now().strftime('%H:%M:%S')}")
                
                try:
                    # Ejecutar monitoreo del sistema
                    if hasattr(self.system, 'start_monitoring'):
                        await asyncio.wait_for(
                            self.system.start_monitoring(),
                            timeout=300  # 5 minutos timeout
                        )
                    else:
                        # Modo básico
                        logger.info("📊 Ejecutando análisis básico...")
                        await asyncio.sleep(60)
                    
                except asyncio.TimeoutError:
                    logger.warning("⏰ Timeout en iteración de monitoreo")
                    continue
                except Exception as e:
                    logger.error(f"❌ Error en iteración {iteration}: {e}")
                    await asyncio.sleep(30)  # Pausa antes de reintentar
                    continue
                
                # Pausa entre iteraciones
                if self.running:
                    await asyncio.sleep(5)
                    
        except KeyboardInterrupt:
            logger.info("⌨️ Interrupción por teclado detectada")
        except Exception as e:
            logger.error(f"❌ Error en bucle de monitoreo: {e}")
        finally:
            logger.info("🏁 Bucle de monitoreo finalizado")
    
    async def run(self):
        """Ejecutar el sistema completo"""
        logger.info("=" * 80)
        logger.info("🚀 INICIANDO SISTEMA MULTI-TIMEFRAME PAPER TRADING")
        logger.info("=" * 80)
        
        # Configurar manejadores de señales
        self.setup_signal_handlers()
        
        # Inicializar sistema
        if not await self.initialize_system():
            logger.error("❌ Fallo en inicialización del sistema")
            return False
        
        # Mostrar información del sistema
        logger.info("📊 INFORMACIÓN DEL SISTEMA:")
        logger.info(f"  💰 Capital inicial: ${self.initial_capital}")
        logger.info(f"  🕐 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"  🔧 Modo: {'Integrado' if hasattr(self.system, 'ml_manager') else 'Compatibilidad'}")
        
        # Ejecutar bucle de monitoreo
        try:
            await self.run_monitoring_loop()
        except Exception as e:
            logger.error(f"❌ Error ejecutando sistema: {e}")
            return False
        finally:
            logger.info("🛑 Sistema detenido")
            logger.info("=" * 80)
        
        return True

async def main():
    """Función principal"""
    # Configuración por defecto
    INITIAL_CAPITAL = 1000.0
    
    # Verificar argumentos de línea de comandos
    if len(sys.argv) > 1:
        try:
            INITIAL_CAPITAL = float(sys.argv[1])
            logger.info(f"💰 Capital personalizado: ${INITIAL_CAPITAL}")
        except ValueError:
            logger.warning(f"⚠️ Capital inválido '{sys.argv[1]}', usando ${INITIAL_CAPITAL}")
    
    # Crear y ejecutar runner
    runner = MultiTimeframePaperTradingRunner(initial_capital=INITIAL_CAPITAL)
    
    try:
        success = await runner.run()
        if success:
            logger.info("✅ Sistema ejecutado exitosamente")
        else:
            logger.error("❌ Sistema terminó con errores")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("⌨️ Ejecución interrumpida por usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Información de inicio
    print("=" * 80)
    print("🚀 SICAR - Sistema Multi-Timeframe Paper Trading")
    print("=" * 80)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Directorio: {Path.cwd()}")
    print("💡 Uso: python run_multi_timeframe_paper_trading.py [capital_inicial]")
    print("⌨️  Presiona Ctrl+C para detener")
    print("=" * 80)
    
    # Ejecutar sistema
    asyncio.run(main())