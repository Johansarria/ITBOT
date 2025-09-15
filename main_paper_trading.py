#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Principal de Paper Trading
Integra todos los componentes para simulación de trading en tiempo real
"""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional
import json
import traceback
import time
from pathlib import Path

# Importar componentes del sistema
from paper_trading_simulator import PaperTradingSimulator
from performance_reporter import PerformanceReporter
from monitoring_system import MonitoringSystem, LogLevel
from market_analyzer import TechnicalAnalyzer, MarketConditionAnalyzer
from trading_signals import StrategyEngine, StrategyType
from portfolio_manager import PortfolioManager
from trade_executor import TradingSimulator
from json_logger import JSONLogger
from projection_calculator import ProjectionCalculator

class PaperTradingSystem:
    """Sistema principal de paper trading resiliente"""
    
    def __init__(self, config_file: str = "trading_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        
        # Inicializar componentes
        self.simulator = None
        self.performance_reporter = None
        self.monitoring_system = None
        self.market_analyzer = None
        self.strategy_engine = None
        self.json_logger = None
        self.projection_calculator = None
        
        # Estado del sistema
        self.is_running = False
        self.shutdown_requested = False
        self.restart_count = 0
        self.max_restarts = 10
        self.last_restart_time = None
        
        # Configurar manejo de señales
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def load_config(self) -> Dict:
        """Carga configuración del sistema"""
        default_config = {
            "initial_capital": 10000.0,
            "symbols": [
                "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", 
                "SOLUSDT", "LTCUSDT", "MATICUSDT", "XRPUSDT",
                "LINKUSDT", "DOTUSDT", "NAS100", "AUDCAD", "XAUUSD"
            ],
            "strategies": {
                "momentum": {"enabled": True, "weight": 0.25},
                "mean_reversion": {"enabled": True, "weight": 0.20},
                "trend_following": {"enabled": True, "weight": 0.25},
                "breakout": {"enabled": True, "weight": 0.15},
                "probability": {"enabled": True, "weight": 0.15}
            },
            "risk_management": {
                "max_risk_per_trade": 0.02,  # 2% por trade
                "max_total_risk": 0.10,      # 10% total
                "max_positions": 8,
                "stop_loss_pct": 0.05,       # 5%
                "take_profit_pct": 0.10      # 10%
            },
            "portfolio_allocation": {
                "BTCUSDT": 0.15,
                "ETHUSDT": 0.12,
                "BNBUSDT": 0.08,
                "ADAUSDT": 0.06,
                "SOLUSDT": 0.06,
                "LTCUSDT": 0.05,
                "MATICUSDT": 0.04,
                "XRPUSDT": 0.04,
                "LINKUSDT": 0.04,
                "DOTUSDT": 0.04,
                "NAS100": 0.12,
                "AUDCAD": 0.10,
                "XAUUSD": 0.10
            },
            "monitoring": {
                "show_debug": False,
                "show_signals": True,
                "show_performance": True,
                "compact_mode": False,
                "update_interval_seconds": 60
            },
            "binance": {
                "testnet": True,
                "api_key": "",
                "api_secret": ""
            }
        }
        
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Merge con configuración por defecto
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"Error cargando configuración: {e}")
                print("Usando configuración por defecto")
                
        # Guardar configuración actualizada
        self.save_config(default_config)
        
        return default_config
        
    def save_config(self, config: Dict):
        """Guarda configuración"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando configuración: {e}")
            
    async def initialize_components(self):
        """Inicializa todos los componentes del sistema de forma resiliente"""
        print("🔧 Inicializando componentes del sistema...")
        
        try:
            # 0. Inicializar logger JSON
            self.json_logger = JSONLogger(
                log_dir=self.config.get('log_directory', 'logs'),
                max_file_size_mb=self.config.get('max_log_file_size_mb', 100),
                backup_count=self.config.get('log_backup_count', 10)
            )
            print("✅ Logger JSON inicializado")
            
            # 0.1. Inicializar calculadora de proyecciones
            self.projection_calculator = ProjectionCalculator()
            print("✅ Calculadora de proyecciones inicializada")
            
            # 1. Simulador principal
            self.simulator = PaperTradingSimulator(
                initial_capital=self.config["initial_capital"],
                symbols=self.config["symbols"]
            )
            print("✅ Simulador de paper trading inicializado")
            
            # 2. Reporter de performance
            self.performance_reporter = PerformanceReporter(
                self.simulator.trading_simulator,
                self.simulator.portfolio_manager
            )
            print("✅ Sistema de reportes inicializado")
            
            # 3. Sistema de monitoreo
            self.monitoring_system = MonitoringSystem(
                self.simulator,
                self.performance_reporter
            )
            
            # Configurar opciones de monitoreo
            monitor_config = self.config["monitoring"]
            self.monitoring_system.set_display_options(
                show_debug=monitor_config["show_debug"],
                show_signals=monitor_config["show_signals"],
                show_performance=monitor_config["show_performance"],
                compact_mode=monitor_config["compact_mode"]
            )
            print("✅ Sistema de monitoreo configurado")
            
            # 4. Analizador de mercado
            self.market_analyzer = TechnicalAnalyzer()
            print("✅ Analizador técnico inicializado")
            
            # 5. Motor de estrategias
            self.strategy_engine = StrategyEngine()
            print("✅ Motor de estrategias inicializado")
            
            # Configurar estrategias
            for strategy_name, strategy_config in self.config["strategies"].items():
                if strategy_config["enabled"]:
                    strategy_type = getattr(StrategyType, strategy_name.upper(), None)
                    if strategy_type:
                        print(f"✅ Estrategia {strategy_name} habilitada (peso: {strategy_config['weight']})")
            
            # Log de inicialización exitosa
            await self.json_logger.log_system_event({
                'event': 'system_initialized',
                'restart_count': self.restart_count,
                'components': ['simulator', 'performance_reporter', 'market_analyzer', 
                             'strategy_engine', 'monitoring_system'],
                'config': {
                    'initial_capital': self.config["initial_capital"],
                    'symbols_count': len(self.config["symbols"]),
                    'strategies_enabled': len([s for s in self.config["strategies"].values() if s["enabled"]])
                }
            })
                        
            print("🎉 Todos los componentes inicializados correctamente")
            
        except Exception as e:
            error_msg = f"Error inicializando componentes: {e}"
            print(f"❌ {error_msg}")
            if self.json_logger:
                await self.json_logger.log_error({
                    'error_type': 'initialization_error',
                    'error_message': str(e),
                    'traceback': traceback.format_exc(),
                    'restart_count': self.restart_count
                })
            raise
            
    def signal_handler(self, signum, frame):
        """Maneja señales del sistema"""
        print(f"\n⚠️ Señal recibida ({signum}). Iniciando cierre ordenado...")
        self.shutdown_requested = True
        
    async def start_system(self):
        """Inicia el sistema completo"""
        if self.is_running:
            print("⚠️ El sistema ya está ejecutándose")
            return
            
        try:
            print("🚀 Iniciando sistema de paper trading...")
            
            # Inicializar componentes
            self.initialize_components()
            
            # Iniciar monitoreo
            self.monitoring_system.start_monitoring()
            
            # Marcar como ejecutándose
            self.is_running = True
            
            # Log de inicio
            self.monitoring_system.log_custom_event(
                "SYSTEM", 
                f"Sistema iniciado con capital inicial de ${self.config['initial_capital']:,.2f}",
                LogLevel.INFO
            )
            
            # Iniciar simulador
            await self.simulator.start()
            
            print("✅ Sistema iniciado correctamente")
            
        except Exception as e:
            print(f"❌ Error iniciando sistema: {e}")
            await self.stop_system()
            raise
            
    async def stop_system(self):
        """Detiene el sistema ordenadamente"""
        if not self.is_running:
            return
            
        print("🛑 Deteniendo sistema...")
        
        try:
            # Detener simulador
            if self.simulator:
                await self.simulator.stop()
                
            # Detener monitoreo
            if self.monitoring_system:
                self.monitoring_system.stop_monitoring()
                
            # Generar reporte final
            if self.performance_reporter:
                final_report = self.performance_reporter.generate_real_time_report()
                print(f"📊 Reporte final generado")
                
            self.is_running = False
            print("✅ Sistema detenido correctamente")
            
        except Exception as e:
            print(f"❌ Error deteniendo sistema: {e}")
            
    async def run_trading_loop(self):
        """Loop principal de trading con manejo de errores resiliente"""
        print("🚀 Iniciando loop principal de trading...")
        
        monitoring_task = None
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        try:
            # Log inicio del loop
            await self.json_logger.log_system_event({
                'event': 'trading_loop_started',
                'restart_count': self.restart_count,
                'config': {
                    'loop_interval': self.config.get('loop_interval', 5),
                    'symbols': self.config.get('symbols', [])
                }
            })
            
            # Inicializar conexiones
            await self.market_analyzer.start()
            
            # Iniciar monitoreo
            monitoring_task = asyncio.create_task(
                self.monitoring_system.start_monitoring()
            )
            
            # Loop principal
            while self.is_running and not self.shutdown_requested:
                try:
                    loop_start_time = time.time()
                    
                    # Obtener datos de mercado
                    market_data = await self.market_analyzer.get_latest_data()
                    
                    # Generar señales de trading
                    signals = await self.strategy_engine.generate_signals(market_data)
                    
                    # Log señales generadas
                    if signals:
                        await self.json_logger.log_signals([
                            {
                                'symbol': signal.symbol,
                                'action': signal.action,
                                'price': signal.price,
                                'confidence': signal.confidence,
                                'strategy': signal.strategy
                            } for signal in signals
                        ])
                    
                    # Procesar señales
                    for signal in signals:
                        if signal.action in ['BUY', 'SELL']:
                            try:
                                # Calcular tamaño de posición
                                position_size = self.portfolio_manager.calculate_position_size(
                                    signal.symbol, signal.confidence
                                )
                                
                                # Ejecutar trade
                                if position_size > 0:
                                    trade_result = await self.simulator.execute_trade(
                                        symbol=signal.symbol,
                                        action=signal.action,
                                        quantity=position_size,
                                        price=signal.price,
                                        strategy=signal.strategy
                                    )
                                    
                                    if trade_result:
                                        # Log trade exitoso
                                        await self.json_logger.log_trade({
                                            'symbol': signal.symbol,
                                            'action': signal.action,
                                            'quantity': position_size,
                                            'price': signal.price,
                                            'strategy': signal.strategy,
                                            'result': 'executed',
                                            'trade_id': trade_result.get('trade_id')
                                        })
                                        
                                        print(f"✅ Trade ejecutado: {signal.action} {position_size} {signal.symbol} @ {signal.price}")
                                        
                            except Exception as trade_error:
                                await self.json_logger.log_error({
                                    'error_type': 'trade_execution_error',
                                    'error_message': str(trade_error),
                                    'signal': {
                                        'symbol': signal.symbol,
                                        'action': signal.action,
                                        'price': signal.price
                                    },
                                    'traceback': traceback.format_exc()
                                })
                                print(f"⚠️ Error ejecutando trade: {trade_error}")
                    
                    # Actualizar performance
                    try:
                        performance_data = await self.performance_reporter.update_performance()
                        if performance_data:
                            await self.json_logger.log_performance(performance_data)
                    except Exception as perf_error:
                        print(f"⚠️ Error actualizando performance: {perf_error}")
                    
                    # Reset contador de errores consecutivos
                    consecutive_errors = 0
                    
                    # Calcular tiempo de espera
                    loop_duration = time.time() - loop_start_time
                    sleep_time = max(0, self.config.get('loop_interval', 5) - loop_duration)
                    
                    # Esperar antes del siguiente ciclo
                    await asyncio.sleep(sleep_time)
                    
                except Exception as e:
                    consecutive_errors += 1
                    error_msg = f"Error en loop de trading (#{consecutive_errors}): {e}"
                    print(f"⚠️ {error_msg}")
                    
                    await self.json_logger.log_error({
                        'error_type': 'trading_loop_error',
                        'error_message': str(e),
                        'consecutive_errors': consecutive_errors,
                        'traceback': traceback.format_exc()
                    })
                    
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"❌ Demasiados errores consecutivos ({consecutive_errors}). Reiniciando sistema...")
                        await self.restart_system()
                        break
                    
                    # Espera progresiva en caso de errores
                    await asyncio.sleep(min(consecutive_errors * 2, 30))
                    
        except Exception as e:
            error_msg = f"Error crítico en loop de trading: {e}"
            print(f"❌ {error_msg}")
            await self.json_logger.log_error({
                'error_type': 'critical_trading_loop_error',
                'error_message': str(e),
                'traceback': traceback.format_exc(),
                'restart_count': self.restart_count
            })
            raise
        finally:
            # Cleanup
            if monitoring_task:
                monitoring_task.cancel()
                try:
                    await monitoring_task
                except asyncio.CancelledError:
                    pass
            
            try:
                await self.market_analyzer.stop()
            except Exception as e:
                print(f"⚠️ Error cerrando market analyzer: {e}")
            
            await self.json_logger.log_system_event({
                'event': 'trading_loop_stopped',
                'restart_count': self.restart_count
            })
            
    async def restart_system(self):
        """Reinicia el sistema de forma controlada"""
        if self.restart_count >= self.max_restarts:
            print(f"❌ Máximo número de reinicios alcanzado ({self.max_restarts})")
            self.shutdown_requested = True
            return
            
        current_time = time.time()
        if self.last_restart_time and (current_time - self.last_restart_time) < 60:
            print("⚠️ Reinicio muy frecuente, esperando...")
            await asyncio.sleep(60)
            
        self.restart_count += 1
        self.last_restart_time = current_time
        
        print(f"🔄 Reiniciando sistema (intento {self.restart_count}/{self.max_restarts})...")
        
        try:
            # Detener sistema actual
            await self.stop_system()
            
            # Esperar un momento
            await asyncio.sleep(5)
            
            # Reinicializar componentes
            await self.initialize_components()
            
            # Reiniciar sistema
            await self.start_system()
            
            print("✅ Sistema reiniciado correctamente")
            
        except Exception as e:
            print(f"❌ Error reiniciando sistema: {e}")
            await self.json_logger.log_error({
                'error_type': 'restart_error',
                'error_message': str(e),
                'restart_count': self.restart_count,
                'traceback': traceback.format_exc()
            })
            self.shutdown_requested = True
            
    async def run(self):
        """Ejecuta el sistema completo"""
        try:
            # Iniciar sistema
            await self.start_system()
            
            # Ejecutar loop principal de trading
            await self.run_trading_loop()
            
        except KeyboardInterrupt:
            print("\n⚠️ Interrupción por teclado detectada")
        except Exception as e:
            print(f"❌ Error crítico: {e}")
        finally:
            # Detener sistema
            await self.stop_system()
            
    def show_system_info(self):
        """Muestra información del sistema"""
        info = f"""
╔══════════════════════════════════════════════════════════════╗
║                 PAPER TRADING SYSTEM INFO                    ║
╚══════════════════════════════════════════════════════════════╝

📊 CONFIGURACIÓN:
• Capital inicial: ${self.config['initial_capital']:,.2f}
• Símbolos monitoreados: {len(self.config['symbols'])}
• Estrategias activas: {len([s for s in self.config['strategies'].values() if s['enabled']])}
• Riesgo máximo por trade: {self.config['risk_management']['max_risk_per_trade']*100:.1f}%
• Riesgo máximo total: {self.config['risk_management']['max_total_risk']*100:.1f}%
• Posiciones máximas: {self.config['risk_management']['max_positions']}

🎯 SÍMBOLOS:
{', '.join(self.config['symbols'])}

⚙️ ESTRATEGIAS HABILITADAS:
"""
        
        for name, config in self.config['strategies'].items():
            if config['enabled']:
                info += f"• {name.title()}: {config['weight']*100:.1f}%\n"
                
        info += f"""
📁 ARCHIVOS:
• Configuración: {self.config_file}
• Logs: paper_trading.log
• Reportes: reports/

🔧 COMANDOS:
• python main_paper_trading.py          - Ejecutar sistema
• python main_paper_trading.py --info   - Mostrar información
• python main_paper_trading.py --config - Editar configuración
"""
        
        print(info)
        
    async def generate_projections_report(self):
        """Genera y muestra el reporte de proyecciones para 7 días"""
        try:
            print("\n" + "="*80)
            print("📊 GENERANDO PROYECCIONES PARA 7 DÍAS")
            print("="*80)
            
            # Generar proyecciones
            projections = self.projection_calculator.generate_all_projections(
                initial_capital=self.config.get('initial_capital', 10000)
            )
            
            # Mostrar resumen
            self.projection_calculator.print_projection_summary(projections)
            
            # Exportar a JSON
            filename = self.projection_calculator.export_projections_to_json(projections)
            print(f"\n💾 Proyecciones exportadas a: {filename}")
            
            # Log de proyecciones generadas
            await self.json_logger.log_system_event({
                'event': 'projections_generated',
                'projections_file': filename,
                'initial_capital': self.config.get('initial_capital', 10000),
                'projection_types': list(projections.keys())
            })
            
            return projections
            
        except Exception as e:
            print(f"❌ Error generando proyecciones: {e}")
            await self.json_logger.log_error({
                'error_type': 'projection_generation_error',
                'error_message': str(e),
                'traceback': traceback.format_exc()
            })
            return None
        
async def main():
    """Función principal"""
    print("🤖 Iniciando Sistema de Paper Trading ITBOT")
    print("="*50)
    
    # Crear sistema
    system = PaperTradingSystem()
    
    try:
        # Inicializar componentes
        await system.initialize_components()
        
        # Generar proyecciones antes de iniciar
        await system.generate_projections_report()
        
        # Preguntar al usuario si desea continuar
        print("\n" + "="*50)
        response = input("¿Desea iniciar el paper trading? (s/n): ").lower().strip()
        
        if response in ['s', 'si', 'y', 'yes']:
            # Ejecutar sistema
            await system.run()
        else:
            print("📊 Solo se generaron las proyecciones. Sistema no iniciado.")
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupción del usuario")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        if hasattr(system, 'json_logger') and system.json_logger:
            await system.json_logger.log_error({
                'error_type': 'critical_system_error',
                'error_message': str(e),
                'traceback': traceback.format_exc()
            })
    finally:
        try:
            await system.stop_system()
        except:
            pass
        print("\n👋 Sistema detenido")

def main_cli():
    """Función principal para CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sistema de Paper Trading')
    parser.add_argument('--config', '-c', default='trading_config.json', 
                       help='Archivo de configuración')
    parser.add_argument('--info', action='store_true', 
                       help='Mostrar información del sistema')
    parser.add_argument('--edit-config', action='store_true',
                       help='Editar configuración')
    
    args = parser.parse_args()
    
    # Crear sistema
    system = PaperTradingSystem(args.config)
    
    if args.info:
        system.show_system_info()
        return
        
    if args.edit_config:
        print(f"📝 Editar configuración en: {args.config}")
        print("💡 Reinicia el sistema después de modificar la configuración")
        return
        
    # Ejecutar sistema
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main_cli()