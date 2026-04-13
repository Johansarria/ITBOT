#!/usr/bin/env python3
"""
Bot de Trading Algorítmico para Binance Spot
Capital inicial: 500 USDT
Objetivo: 0.6% rendimiento diario promedio

Este archivo principal integra todos los componentes del sistema:
- Análisis de mercado
- Framework técnico
- Gestión de riesgos
- Backtesting avanzado
- Optimización de parámetros
- Pruebas de estrés
- Simulación final

Autor: Sistema de Trading Algorítmico
Fecha: 2024
"""

import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Importar módulos del sistema
from market_analyzer import MarketAnalyzer
from technical_framework import TechnicalFramework
from risk_management import RiskManager
from advanced_backtester import AdvancedBacktester
from parameter_optimizer import ParameterOptimizer
from stress_testing import StressTesting
from final_simulation import FinalSimulator

class TradingBotConfig:
    """Configuración del bot de trading"""
    def __init__(self):
        self.initial_capital = 500.0  # USDT
        self.daily_target = 0.006  # 0.6%
        self.max_daily_loss = 0.02  # 2%
        self.max_position_size = 0.1  # 10% del capital por posición
        self.min_trade_amount = 10.0  # USDT mínimo por trade
        self.commission_rate = 0.001  # 0.1% comisión Binance
        self.slippage_factor = 0.0005  # 0.05% slippage estimado
        
        # Pares de trading recomendados para 500 USDT
        self.trading_pairs = [
            'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT',
            'LTCUSDT', 'BCHUSDT', 'XLMUSDT', 'EOSUSDT', 'TRXUSDT'
        ]
        
        # Configuración de API Binance
        self.api_key = os.getenv('BINANCE_API_KEY', '')
        self.api_secret = os.getenv('BINANCE_API_SECRET', '')
        self.testnet = True  # Usar testnet por defecto

class TradingBot:
    """Bot principal de trading algorítmico"""
    
    def __init__(self, config: TradingBotConfig):
        self.config = config
        self.logger = self._setup_logging()
        self.client = None
        self.is_running = False
        self.current_positions = {}
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        
        # Inicializar componentes
        self.market_analyzer = MarketAnalyzer()
        self.technical_framework = TechnicalFramework()
        self.risk_manager = RiskManager(config.initial_capital)
        self.backtester = AdvancedBacktester()
        self.optimizer = ParameterOptimizer()
        self.stress_tester = StressTesting()
        self.simulator = FinalSimulator()
        
        self.logger.info("Bot de trading inicializado con capital: ${:.2f}".format(config.initial_capital))
    
    def _setup_logging(self) -> logging.Logger:
        """Configurar sistema de logging"""
        logger = logging.getLogger('TradingBot')
        logger.setLevel(logging.INFO)
        
        # Crear handler para archivo
        file_handler = logging.FileHandler('trading_bot.log')
        file_handler.setLevel(logging.INFO)
        
        # Crear handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formato de logs
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def initialize_binance_client(self) -> bool:
        """Inicializar cliente de Binance"""
        try:
            if not self.config.api_key or not self.config.api_secret:
                self.logger.warning("API keys no configuradas. Usando modo simulación.")
                return False
            
            self.client = Client(
                self.config.api_key,
                self.config.api_secret,
                testnet=self.config.testnet
            )
            
            # Verificar conexión
            account_info = self.client.get_account()
            self.logger.info("Conexión a Binance establecida exitosamente")
            return True
            
        except BinanceAPIException as e:
            self.logger.error(f"Error conectando a Binance: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error inesperado: {e}")
            return False
    
    async def run_comprehensive_analysis(self) -> Dict:
        """Ejecutar análisis comprehensivo del sistema"""
        self.logger.info("Iniciando análisis comprehensivo del sistema...")
        
        results = {
            'market_analysis': {},
            'backtesting': {},
            'optimization': {},
            'stress_testing': {},
            'final_simulation': {},
            'recommendations': []
        }
        
        try:
            # 1. Análisis de mercado
            self.logger.info("Ejecutando análisis de mercado...")
            market_data = await self._analyze_market_conditions()
            results['market_analysis'] = market_data
            
            # 2. Backtesting con datos históricos
            self.logger.info("Ejecutando backtesting...")
            backtest_results = await self._run_backtesting()
            results['backtesting'] = backtest_results
            
            # 3. Optimización de parámetros
            self.logger.info("Optimizando parámetros...")
            optimization_results = await self._optimize_parameters()
            results['optimization'] = optimization_results
            
            # 4. Pruebas de estrés
            self.logger.info("Ejecutando pruebas de estrés...")
            stress_results = await self._run_stress_tests()
            results['stress_testing'] = stress_results
            
            # 5. Simulación final
            self.logger.info("Ejecutando simulación final...")
            simulation_results = await self._run_final_simulation()
            results['final_simulation'] = simulation_results
            
            # 6. Generar recomendaciones
            recommendations = self._generate_recommendations(results)
            results['recommendations'] = recommendations
            
            # Guardar resultados
            self._save_analysis_results(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error en análisis comprehensivo: {e}")
            raise
    
    async def _analyze_market_conditions(self) -> Dict:
        """Analizar condiciones actuales del mercado"""
        try:
            # Obtener datos de mercado para pares seleccionados
            market_data = {}
            
            for pair in self.config.trading_pairs:
                try:
                    # Simular datos de mercado (en producción usar API real)
                    pair_data = {
                        'symbol': pair,
                        'price': np.random.uniform(100, 50000),
                        'volume_24h': np.random.uniform(1000000, 10000000),
                        'price_change_24h': np.random.uniform(-5, 5),
                        'volatility': np.random.uniform(0.01, 0.05),
                        'liquidity_score': np.random.uniform(0.7, 1.0),
                        'spread': np.random.uniform(0.001, 0.01)
                    }
                    
                    market_data[pair] = pair_data
                    
                except Exception as e:
                    self.logger.warning(f"Error obteniendo datos para {pair}: {e}")
            
            # Analizar y puntuar pares
            scored_pairs = self.market_analyzer.score_trading_pairs(
                market_data, self.config.initial_capital
            )
            
            return {
                'total_pairs_analyzed': len(market_data),
                'viable_pairs': len([p for p in scored_pairs if p['score'] > 0.6]),
                'top_pairs': scored_pairs[:5],
                'market_conditions': self._assess_market_regime(market_data)
            }
            
        except Exception as e:
            self.logger.error(f"Error en análisis de mercado: {e}")
            return {}
    
    def _assess_market_regime(self, market_data: Dict) -> str:
        """Evaluar régimen actual del mercado"""
        try:
            avg_change = np.mean([data['price_change_24h'] for data in market_data.values()])
            avg_volatility = np.mean([data['volatility'] for data in market_data.values()])
            
            if avg_change > 2 and avg_volatility < 0.03:
                return 'bull_market'
            elif avg_change < -2 and avg_volatility > 0.04:
                return 'bear_market'
            elif abs(avg_change) < 1 and avg_volatility < 0.02:
                return 'sideways_market'
            else:
                return 'volatile_market'
                
        except Exception:
            return 'unknown'
    
    async def _run_backtesting(self) -> Dict:
        """Ejecutar backtesting comprehensivo"""
        try:
            # Generar datos históricos simulados
            historical_data = self._generate_historical_data()
            
            # Configurar parámetros de backtesting
            backtest_config = {
                'initial_capital': self.config.initial_capital,
                'commission_rate': self.config.commission_rate,
                'slippage_factor': self.config.slippage_factor,
                'max_position_size': self.config.max_position_size
            }
            
            # Ejecutar backtesting
            results = self.backtester.run_backtest(
                historical_data,
                self.technical_framework,
                backtest_config
            )
            
            return {
                'total_trades': results.get('total_trades', 0),
                'win_rate': results.get('win_rate', 0),
                'total_return': results.get('total_return', 0),
                'sharpe_ratio': results.get('sharpe_ratio', 0),
                'max_drawdown': results.get('max_drawdown', 0),
                'daily_avg_return': results.get('daily_avg_return', 0),
                'meets_target': results.get('daily_avg_return', 0) >= self.config.daily_target
            }
            
        except Exception as e:
            self.logger.error(f"Error en backtesting: {e}")
            return {}
    
    def _generate_historical_data(self) -> pd.DataFrame:
        """Generar datos históricos simulados para backtesting"""
        # Simular 1 año de datos diarios
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        
        # Generar precios simulados con tendencia y volatilidad realista
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, len(dates))  # 0.1% promedio, 2% volatilidad
        prices = [100]  # Precio inicial
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Crear DataFrame con datos OHLCV
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
            'low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
            'close': prices,
            'volume': np.random.uniform(1000000, 5000000, len(dates))
        })
        
        return data
    
    async def _optimize_parameters(self) -> Dict:
        """Optimizar parámetros de la estrategia"""
        try:
            # Definir espacio de parámetros
            parameter_space = {
                'rsi_period': [14, 21, 28],
                'rsi_oversold': [25, 30, 35],
                'rsi_overbought': [65, 70, 75],
                'ema_fast': [12, 15, 20],
                'ema_slow': [26, 30, 35],
                'bb_period': [20, 25, 30],
                'bb_std': [1.5, 2.0, 2.5]
            }
            
            # Ejecutar optimización
            optimization_results = self.optimizer.optimize_parameters(
                parameter_space,
                self._generate_historical_data(),
                target_metric='sharpe_ratio'
            )
            
            return {
                'best_parameters': optimization_results.get('best_params', {}),
                'best_score': optimization_results.get('best_score', 0),
                'optimization_iterations': optimization_results.get('iterations', 0),
                'parameter_sensitivity': optimization_results.get('sensitivity', {})
            }
            
        except Exception as e:
            self.logger.error(f"Error en optimización: {e}")
            return {}
    
    async def _run_stress_tests(self) -> Dict:
        """Ejecutar pruebas de estrés"""
        try:
            # Definir escenarios de estrés
            stress_scenarios = [
                {'name': 'market_crash', 'severity': 0.8},
                {'name': 'high_volatility', 'severity': 0.6},
                {'name': 'low_liquidity', 'severity': 0.7},
                {'name': 'trending_market', 'severity': 0.5}
            ]
            
            stress_results = {}
            
            for scenario in stress_scenarios:
                try:
                    result = self.stress_tester.run_stress_scenario(
                        scenario,
                        self._generate_historical_data(),
                        self.technical_framework
                    )
                    stress_results[scenario['name']] = result
                    
                except Exception as e:
                    self.logger.warning(f"Error en escenario {scenario['name']}: {e}")
            
            return {
                'scenarios_tested': len(stress_results),
                'worst_case_drawdown': max([r.get('max_drawdown', 0) for r in stress_results.values()]),
                'stress_test_results': stress_results,
                'system_resilience': self._calculate_resilience_score(stress_results)
            }
            
        except Exception as e:
            self.logger.error(f"Error en pruebas de estrés: {e}")
            return {}
    
    def _calculate_resilience_score(self, stress_results: Dict) -> float:
        """Calcular puntuación de resistencia del sistema"""
        try:
            if not stress_results:
                return 0.0
            
            scores = []
            for result in stress_results.values():
                # Puntuación basada en drawdown y recuperación
                drawdown = result.get('max_drawdown', 1.0)
                recovery_time = result.get('recovery_time', 100)
                
                score = max(0, 1 - drawdown) * max(0, 1 - recovery_time/50)
                scores.append(score)
            
            return np.mean(scores)
            
        except Exception:
            return 0.0
    
    async def _run_final_simulation(self) -> Dict:
        """Ejecutar simulación final del sistema completo"""
        try:
            # Configurar simulación
            simulation_config = {
                'initial_capital': self.config.initial_capital,
                'daily_target': self.config.daily_target,
                'simulation_days': 30,
                'monte_carlo_runs': 100
            }
            
            # Ejecutar simulación
            simulation_results = self.simulator.run_comprehensive_simulation(
                simulation_config,
                self.technical_framework,
                self.risk_manager
            )
            
            return {
                'simulation_days': simulation_config['simulation_days'],
                'monte_carlo_runs': simulation_config['monte_carlo_runs'],
                'success_rate': simulation_results.get('success_rate', 0),
                'avg_daily_return': simulation_results.get('avg_daily_return', 0),
                'target_achievement': simulation_results.get('target_achievement', False),
                'risk_metrics': simulation_results.get('risk_metrics', {}),
                'confidence_interval': simulation_results.get('confidence_interval', {})
            }
            
        except Exception as e:
            self.logger.error(f"Error en simulación final: {e}")
            return {}
    
    def _generate_recommendations(self, analysis_results: Dict) -> List[str]:
        """Generar recomendaciones basadas en los resultados del análisis"""
        recommendations = []
        
        try:
            # Analizar resultados de backtesting
            backtest = analysis_results.get('backtesting', {})
            if backtest.get('meets_target', False):
                recommendations.append("✅ La estrategia cumple el objetivo de 0.6% diario en backtesting")
            else:
                recommendations.append("⚠️ La estrategia requiere optimización para cumplir el objetivo")
            
            # Analizar win rate
            win_rate = backtest.get('win_rate', 0)
            if win_rate > 0.6:
                recommendations.append(f"✅ Excelente win rate: {win_rate:.1%}")
            elif win_rate > 0.5:
                recommendations.append(f"✅ Win rate aceptable: {win_rate:.1%}")
            else:
                recommendations.append(f"⚠️ Win rate bajo: {win_rate:.1%} - Revisar señales")
            
            # Analizar Sharpe ratio
            sharpe = backtest.get('sharpe_ratio', 0)
            if sharpe > 1.5:
                recommendations.append(f"✅ Excelente Sharpe ratio: {sharpe:.2f}")
            elif sharpe > 1.0:
                recommendations.append(f"✅ Buen Sharpe ratio: {sharpe:.2f}")
            else:
                recommendations.append(f"⚠️ Sharpe ratio bajo: {sharpe:.2f}")
            
            # Analizar drawdown
            drawdown = backtest.get('max_drawdown', 0)
            if drawdown < 0.05:
                recommendations.append(f"✅ Drawdown controlado: {drawdown:.1%}")
            elif drawdown < 0.1:
                recommendations.append(f"⚠️ Drawdown moderado: {drawdown:.1%}")
            else:
                recommendations.append(f"🚨 Drawdown alto: {drawdown:.1%} - Revisar gestión de riesgo")
            
            # Analizar simulación final
            simulation = analysis_results.get('final_simulation', {})
            success_rate = simulation.get('success_rate', 0)
            if success_rate > 0.8:
                recommendations.append(f"✅ Alta probabilidad de éxito: {success_rate:.1%}")
            elif success_rate > 0.6:
                recommendations.append(f"✅ Probabilidad moderada de éxito: {success_rate:.1%}")
            else:
                recommendations.append(f"⚠️ Baja probabilidad de éxito: {success_rate:.1%}")
            
            # Recomendaciones generales
            recommendations.extend([
                "📊 Monitorear métricas diariamente",
                "🔄 Reoptimizar parámetros mensualmente",
                "🛡️ Mantener stop-loss estricto",
                "💰 Comenzar con capital mínimo en testnet",
                "📈 Escalar gradualmente tras validación"
            ])
            
        except Exception as e:
            self.logger.error(f"Error generando recomendaciones: {e}")
            recommendations.append("⚠️ Error generando recomendaciones específicas")
        
        return recommendations
    
    def _save_analysis_results(self, results: Dict):
        """Guardar resultados del análisis"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'analysis_results_{timestamp}.json'
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Resultados guardados en: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error guardando resultados: {e}")
    
    async def start_trading(self):
        """Iniciar el bot de trading en modo producción"""
        self.logger.info("Iniciando bot de trading...")
        
        if not self.initialize_binance_client():
            self.logger.error("No se pudo conectar a Binance. Abortando.")
            return
        
        self.is_running = True
        
        try:
            while self.is_running:
                # Lógica principal de trading
                await self._trading_loop()
                await asyncio.sleep(60)  # Esperar 1 minuto entre iteraciones
                
        except KeyboardInterrupt:
            self.logger.info("Deteniendo bot por interrupción del usuario")
        except Exception as e:
            self.logger.error(f"Error en loop de trading: {e}")
        finally:
            self.is_running = False
            self.logger.info("Bot de trading detenido")
    
    async def _trading_loop(self):
        """Loop principal de trading"""
        try:
            # Obtener señales de trading
            signals = await self._get_trading_signals()
            
            # Procesar cada señal
            for signal in signals:
                if await self._should_execute_trade(signal):
                    await self._execute_trade(signal)
            
            # Monitorear posiciones existentes
            await self._monitor_positions()
            
            # Actualizar métricas
            await self._update_metrics()
            
        except Exception as e:
            self.logger.error(f"Error en loop de trading: {e}")
    
    async def _get_trading_signals(self) -> List[Dict]:
        """Obtener señales de trading"""
        signals = []
        
        try:
            for pair in self.config.trading_pairs:
                # Obtener datos de mercado
                market_data = await self._get_market_data(pair)
                
                # Generar señal técnica
                signal = self.technical_framework.generate_signal(market_data)
                
                if signal['action'] != 'hold':
                    signals.append({
                        'pair': pair,
                        'action': signal['action'],
                        'confidence': signal['confidence'],
                        'price': market_data['close'],
                        'timestamp': datetime.now()
                    })
        
        except Exception as e:
            self.logger.error(f"Error obteniendo señales: {e}")
        
        return signals
    
    async def _get_market_data(self, pair: str) -> Dict:
        """Obtener datos de mercado para un par"""
        try:
            if self.client:
                # Usar API real de Binance
                klines = self.client.get_klines(symbol=pair, interval='1m', limit=100)
                # Procesar datos...
                pass
            else:
                # Datos simulados para testing
                return {
                    'open': 100,
                    'high': 102,
                    'low': 98,
                    'close': 101,
                    'volume': 1000000
                }
        
        except Exception as e:
            self.logger.error(f"Error obteniendo datos para {pair}: {e}")
            return {}
    
    async def _should_execute_trade(self, signal: Dict) -> bool:
        """Determinar si se debe ejecutar un trade"""
        try:
            # Validar con gestión de riesgos
            risk_check = self.risk_manager.validate_trade(
                signal['pair'],
                signal['action'],
                signal['price'],
                self.config.min_trade_amount
            )
            
            return risk_check['approved']
            
        except Exception as e:
            self.logger.error(f"Error validando trade: {e}")
            return False
    
    async def _execute_trade(self, signal: Dict):
        """Ejecutar un trade"""
        try:
            self.logger.info(f"Ejecutando {signal['action']} en {signal['pair']}")
            
            # Calcular tamaño de posición
            position_size = self.risk_manager.calculate_position_size(
                signal['pair'],
                signal['price'],
                self.config.max_position_size
            )
            
            if self.client:
                # Ejecutar orden real
                # order = self.client.create_order(...)
                pass
            else:
                # Simular ejecución
                self.logger.info(f"Trade simulado: {signal['action']} {position_size} {signal['pair']}")
            
        except Exception as e:
            self.logger.error(f"Error ejecutando trade: {e}")
    
    async def _monitor_positions(self):
        """Monitorear posiciones existentes"""
        try:
            # Revisar stop-loss y take-profit
            # Actualizar posiciones
            pass
            
        except Exception as e:
            self.logger.error(f"Error monitoreando posiciones: {e}")
    
    async def _update_metrics(self):
        """Actualizar métricas de rendimiento"""
        try:
            # Calcular PnL diario
            # Actualizar estadísticas
            pass
            
        except Exception as e:
            self.logger.error(f"Error actualizando métricas: {e}")
    
    def stop_trading(self):
        """Detener el bot de trading"""
        self.is_running = False
        self.logger.info("Señal de parada enviada al bot")

async def main():
    """Función principal"""
    print("🤖 Bot de Trading Algorítmico para Binance Spot")
    print("💰 Capital inicial: 500 USDT")
    print("🎯 Objetivo: 0.6% rendimiento diario promedio")
    print("="*50)
    
    # Crear configuración
    config = TradingBotConfig()
    
    # Crear bot
    bot = TradingBot(config)
    
    # Menú de opciones
    while True:
        print("\n📋 Opciones disponibles:")
        print("1. Ejecutar análisis comprehensivo")
        print("2. Iniciar trading en vivo (testnet)")
        print("3. Ver documentación")
        print("4. Salir")
        
        try:
            choice = input("\nSelecciona una opción (1-4): ").strip()
            
            if choice == '1':
                print("\n🔍 Ejecutando análisis comprehensivo...")
                results = await bot.run_comprehensive_analysis()
                
                print("\n📊 Resumen de resultados:")
                print(f"- Pares analizados: {results.get('market_analysis', {}).get('total_pairs_analyzed', 0)}")
                print(f"- Win rate: {results.get('backtesting', {}).get('win_rate', 0):.1%}")
                print(f"- Sharpe ratio: {results.get('backtesting', {}).get('sharpe_ratio', 0):.2f}")
                print(f"- Cumple objetivo: {'✅' if results.get('backtesting', {}).get('meets_target', False) else '❌'}")
                
                print("\n💡 Recomendaciones:")
                for rec in results.get('recommendations', []):
                    print(f"  {rec}")
            
            elif choice == '2':
                print("\n🚀 Iniciando trading en vivo (testnet)...")
                print("Presiona Ctrl+C para detener")
                await bot.start_trading()
            
            elif choice == '3':
                print("\n📚 Ver archivo: strategy_documentation.md")
                print("📁 Archivos del sistema creados:")
                files = [
                    'market_analyzer.py',
                    'technical_framework.py',
                    'risk_management.py',
                    'advanced_backtester.py',
                    'parameter_optimizer.py',
                    'stress_testing.py',
                    'final_simulation.py',
                    'strategy_documentation.md'
                ]
                for file in files:
                    print(f"  - {file}")
            
            elif choice == '4':
                print("\n👋 ¡Hasta luego!")
                break
            
            else:
                print("\n❌ Opción inválida. Intenta de nuevo.")
                
        except KeyboardInterrupt:
            print("\n\n👋 ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    # Configurar variables de entorno para API de Binance
    print("⚙️ Configuración inicial:")
    print("Para usar API real de Binance, configura las variables de entorno:")
    print("  BINANCE_API_KEY=tu_api_key")
    print("  BINANCE_API_SECRET=tu_api_secret")
    print("\n🔒 Por defecto se usa modo simulación (sin API keys)")
    
    # Ejecutar aplicación
    asyncio.run(main())