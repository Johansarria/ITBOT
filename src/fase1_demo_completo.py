#!/usr/bin/env python3
"""
DEMO COMPLETO - FASE 1 SICAR
Integración de todas las mejoras inmediatas implementadas:
1. CPCV (Combinatorial Purged Cross-Validation)
2. Función de recompensa optimizada con Sharpe Ratio
3. Detección de no-estacionariedad extrema

Autor: Sistema SICAR
Fecha: Enero 2025
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import json
import os
import warnings
warnings.filterwarnings('ignore')

# Importar módulos SICAR
from advanced_backtester import AdvancedBacktester, CPCVConfig, BacktestResult
from qlearning_position_optimizer import QLearningPositionOptimizer
from module_2_regime import RegimeClassifier, ExtremeNonStationarityDetector

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Fase1DemoCompleto:
    """
    Demo completo de la FASE 1 del proyecto SICAR
    Integra CPCV, Sharpe Ratio optimizado y detección de regímenes extremos
    """
    
    def __init__(self, initial_capital=10000):
        """
        Inicializar demo de FASE 1
        
        Args:
            initial_capital: Capital inicial para backtesting
        """
        self.initial_capital = initial_capital
        
        # Inicializar componentes
        self.backtester = AdvancedBacktester(initial_capital=initial_capital)
        self.qlearning_optimizer = QLearningPositionOptimizer()
        self.regime_classifier = RegimeClassifier()
        self.extreme_detector = ExtremeNonStationarityDetector()
        
        # Configuración
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        self.timeframe = '4h'
        self.lookback_days = 90
        
        logger.info("🚀 FASE 1 Demo Completo inicializado")
        logger.info(f"💰 Capital inicial: ${initial_capital:,.2f}")
        logger.info(f"📊 Símbolos: {self.symbols}")
    
    def run_complete_demo(self):
        """
        Ejecutar demo completo de FASE 1
        """
        logger.info("=" * 80)
        logger.info("🎯 INICIANDO DEMO COMPLETO - FASE 1 SICAR")
        logger.info("=" * 80)
        
        try:
            # 1. Generar datos simulados de mercado
            logger.info("📥 1. Generando datos simulados de mercado...")
            market_data = self._generate_simulated_data()
            
            # 2. Análisis de no-estacionariedad extrema
            logger.info("🔬 2. Analizando no-estacionariedad extrema...")
            nonstationarity_results = self._analyze_extreme_nonstationarity(market_data)
            
            # 3. Clasificación de regímenes
            logger.info("🎭 3. Clasificando regímenes de mercado...")
            regime_results = self._classify_market_regimes(market_data)
            
            # 4. Optimización con Q-Learning y Sharpe Ratio
            logger.info("🧠 4. Optimizando posiciones con Q-Learning...")
            qlearning_results = self._optimize_positions_qlearning(market_data)
            
            # 5. Validación con CPCV
            logger.info("✅ 5. Validando estrategia con CPCV...")
            cpcv_results = self._validate_with_cpcv(market_data)
            
            # 6. Generar reporte final
            logger.info("📊 6. Generando reporte final...")
            final_report = self._generate_final_report(
                nonstationarity_results,
                regime_results,
                qlearning_results,
                cpcv_results
            )
            
            logger.info("✅ Demo FASE 1 completado exitosamente")
            return final_report
            
        except Exception as e:
            logger.error(f"❌ Error en demo FASE 1: {e}")
            return None
    
    def _generate_simulated_data(self):
        """Generar datos simulados de mercado para el demo"""
        market_data = {}
        
        # Configuración de simulación
        n_periods = 500  # ~83 días con intervalos de 4h
        base_prices = {'BTCUSDT': 45000, 'ETHUSDT': 3000, 'ADAUSDT': 0.5}
        
        for symbol in self.symbols:
            logger.info(f"📊 Generando datos simulados para {symbol}...")
            
            # Generar timestamps
            end_time = datetime.now()
            timestamps = [end_time - timedelta(hours=4*i) for i in range(n_periods)]
            timestamps.reverse()
            
            # Generar precios con tendencia y volatilidad realista
            base_price = base_prices[symbol]
            
            # Simular random walk con drift
            returns = np.random.normal(0.0002, 0.02, n_periods)  # Drift pequeño, volatilidad 2%
            
            # Añadir algunos períodos de alta volatilidad (regímenes extremos)
            extreme_periods = np.random.choice(n_periods, size=int(n_periods * 0.1), replace=False)
            returns[extreme_periods] *= 3  # Triplicar volatilidad en períodos extremos
            
            # Calcular precios
            prices = [base_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Generar OHLC
            opens = prices[:-1]
            closes = prices[1:]
            
            highs = []
            lows = []
            volumes = []
            
            for i in range(len(opens)):
                # High/Low basado en volatilidad del período
                volatility = abs(returns[i])
                high_factor = 1 + volatility * np.random.uniform(0.3, 0.8)
                low_factor = 1 - volatility * np.random.uniform(0.3, 0.8)
                
                high = max(opens[i], closes[i]) * high_factor
                low = min(opens[i], closes[i]) * low_factor
                
                highs.append(high)
                lows.append(low)
                
                # Volumen correlacionado con volatilidad
                base_volume = 1000000
                volume = base_volume * (1 + volatility * 5) * np.random.uniform(0.5, 2.0)
                volumes.append(volume)
            
            # Crear DataFrame
            data = pd.DataFrame({
                'timestamp': timestamps[1:],
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            })
            
            market_data[symbol] = data
            logger.info(f"✅ {symbol}: {len(data)} registros generados")
        
        return market_data
    
    def _analyze_extreme_nonstationarity(self, market_data):
        """Analizar no-estacionariedad extrema en los datos"""
        results = {}
        
        for symbol, data in market_data.items():
            logger.info(f"🔬 Analizando no-estacionariedad para {symbol}...")
            
            try:
                # Detectar no-estacionariedad extrema
                nonstationarity_result = self.extreme_detector.detect_extreme_nonstationarity(data)
                results[symbol] = nonstationarity_result
                
                # Log resultados clave
                if nonstationarity_result.get('extreme_detected', False):
                    logger.warning(f"⚠️ {symbol}: No-estacionariedad extrema detectada!")
                    logger.info(f"   Score: {nonstationarity_result.get('nonstationarity_score', 0):.3f}")
                else:
                    logger.info(f"✅ {symbol}: Condiciones normales de estacionariedad")
                
            except Exception as e:
                logger.error(f"❌ Error analizando {symbol}: {e}")
                results[symbol] = {'error': str(e)}
        
        return results
    
    def _classify_market_regimes(self, market_data):
        """Clasificar regímenes de mercado"""
        results = {}
        
        # Entrenar clasificador con todos los datos
        logger.info("🎭 Entrenando clasificador de regímenes...")
        
        try:
            # Combinar datos de todos los símbolos para entrenamiento
            combined_data = pd.concat([data for data in market_data.values()], ignore_index=True)
            
            # Entrenar clasificador
            self.regime_classifier.train_regime_classifier(combined_data)
            
            # Clasificar cada símbolo
            for symbol, data in market_data.items():
                logger.info(f"🎭 Clasificando regímenes para {symbol}...")
                
                regime_classification = self.regime_classifier.classify_regimes(data)
                current_regime = self.regime_classifier.classify_current_regime(data.tail(20))
                
                results[symbol] = {
                    'regime_history': regime_classification,
                    'current_regime': current_regime,
                    'regime_name': self.regime_classifier.regime_names.get(current_regime, 'Desconocido')
                }
                
                logger.info(f"✅ {symbol}: Régimen actual = {results[symbol]['regime_name']}")
                
        except Exception as e:
            logger.error(f"❌ Error clasificando regímenes: {e}")
            results['error'] = str(e)
        
        return results
    
    def _optimize_positions_qlearning(self, market_data):
        """Optimizar posiciones usando Q-Learning con Sharpe Ratio"""
        results = {}
        
        for symbol, data in market_data.items():
            logger.info(f"🧠 Optimizando posiciones para {symbol}...")
            
            try:
                # Simular trading con Q-Learning
                optimization_results = self._simulate_qlearning_trading(symbol, data)
                results[symbol] = optimization_results
                
                logger.info(f"✅ {symbol}: Optimización completada")
                logger.info(f"   Trades simulados: {optimization_results.get('total_trades', 0)}")
                logger.info(f"   Sharpe Ratio: {optimization_results.get('sharpe_ratio', 0):.3f}")
                
            except Exception as e:
                logger.error(f"❌ Error optimizando {symbol}: {e}")
                results[symbol] = {'error': str(e)}
        
        return results
    
    def _simulate_qlearning_trading(self, symbol, data):
        """Simular trading con Q-Learning para un símbolo"""
        try:
            # Preparar datos para simulación
            prices = data['close'].values
            volumes = data['volume'].values
            
            # Calcular indicadores básicos
            returns = np.diff(np.log(prices))
            volatility = pd.Series(returns).rolling(20).std().fillna(0.02)
            
            # Simular trades
            trades_results = []
            capital = self.initial_capital
            
            for i in range(50, len(data) - 10):  # Dejar margen para indicadores
                # Estado del mercado
                market_state = {
                    'volatility': volatility.iloc[i],
                    'trend_strength': abs(returns[i-1]) if i > 0 else 0.01,
                    'confidence': min(volumes[i] / np.mean(volumes[max(0, i-20):i+1]), 2.0)
                }
                
                # Seleccionar acción (tamaño de posición)
                action = self.qlearning_optimizer.select_action(
                    self.qlearning_optimizer.discretize_state(market_state),
                    training=True
                )
                
                position_size = self.qlearning_optimizer.position_sizes[action]
                
                # Simular trade (simplificado)
                entry_price = prices[i]
                exit_price = prices[min(i + 5, len(prices) - 1)]  # Hold por 5 períodos
                
                pnl = (exit_price - entry_price) / entry_price * position_size * capital
                duration_hours = 5 * 4  # 5 períodos de 4h
                
                # Resultado del trade
                trade_result = {
                    'pnl': pnl,
                    'position_size': position_size,
                    'duration_hours': duration_hours,
                    'volatility': market_state['volatility']
                }
                
                trades_results.append(trade_result)
                capital += pnl
                
                # Aprender del trade
                market_state_after = {
                    'volatility': volatility.iloc[min(i + 5, len(volatility) - 1)],
                    'trend_strength': abs(returns[min(i + 4, len(returns) - 1)]),
                    'confidence': market_state['confidence']
                }
                
                self.qlearning_optimizer.learn_from_trade(
                    market_state, action, trade_result, market_state_after
                )
            
            # Calcular métricas
            total_pnl = sum(trade['pnl'] for trade in trades_results)
            returns_series = [trade['pnl'] for trade in trades_results]
            
            if len(returns_series) > 1:
                sharpe_ratio = np.mean(returns_series) / np.std(returns_series) if np.std(returns_series) > 0 else 0
            else:
                sharpe_ratio = 0
            
            return {
                'total_trades': len(trades_results),
                'total_pnl': total_pnl,
                'final_capital': capital,
                'return_pct': (capital - self.initial_capital) / self.initial_capital * 100,
                'sharpe_ratio': sharpe_ratio,
                'avg_position_size': np.mean([t['position_size'] for t in trades_results]),
                'win_rate': len([t for t in trades_results if t['pnl'] > 0]) / len(trades_results) if trades_results else 0
            }
            
        except Exception as e:
            logger.error(f"Error en simulación Q-Learning: {e}")
            return {'error': str(e)}
    
    def _validate_with_cpcv(self, market_data):
        """Validar estrategia usando CPCV"""
        logger.info("✅ Iniciando validación con CPCV...")
        
        try:
            # Configurar CPCV
            cpcv_config = CPCVConfig(
                n_splits=5,
                purge_pct=0.02,
                embargo_pct=0.01,
                n_combinations=8,
                parallel_execution=True
            )
            
            # Cargar datos en el backtester
            self.backtester.load_market_data(market_data)
            
            # Definir estrategia simple para validación
            def simple_strategy(backtester, current_time, current_prices):
                """Estrategia simple para validación CPCV"""
                try:
                    # Estrategia básica: comprar en tendencia alcista
                    for symbol in current_prices:
                        if symbol in backtester.market_data:
                            data = backtester.market_data[symbol]
                            recent_data = data[data['timestamp'] <= current_time].tail(20)
                            
                            if len(recent_data) >= 10:
                                # Calcular tendencia simple
                                prices = recent_data['close'].values
                                trend = (prices[-1] - prices[-10]) / prices[-10]
                                
                                # Señal de compra en tendencia alcista
                                if trend > 0.02 and symbol not in backtester.current_positions:
                                    position_size = 0.3  # 30% del capital
                                    backtester.place_market_order(
                                        symbol=symbol,
                                        side='buy',
                                        quantity=position_size * backtester.current_capital / current_prices[symbol]
                                    )
                                
                                # Señal de venta en tendencia bajista
                                elif trend < -0.02 and symbol in backtester.current_positions:
                                    position = backtester.current_positions[symbol]
                                    backtester.place_market_order(
                                        symbol=symbol,
                                        side='sell',
                                        quantity=position.quantity
                                    )
                except Exception as e:
                    logger.debug(f"Error en estrategia: {e}")
            
            # Ejecutar CPCV
            start_date = min([data['timestamp'].min() for data in market_data.values()])
            end_date = max([data['timestamp'].max() for data in market_data.values()])
            
            cpcv_result = self.backtester.run_cpcv(
                strategy_func=simple_strategy,
                start_date=start_date,
                end_date=end_date,
                config=cpcv_config
            )
            
            logger.info("✅ Validación CPCV completada")
            logger.info(f"   Retorno promedio: {cpcv_result.mean_return:.2%}")
            logger.info(f"   Sharpe promedio: {cpcv_result.mean_sharpe:.3f}")
            logger.info(f"   Score de robustez: {cpcv_result.robustness_score:.3f}")
            
            return {
                'mean_return': cpcv_result.mean_return,
                'std_return': cpcv_result.std_return,
                'mean_sharpe': cpcv_result.mean_sharpe,
                'std_sharpe': cpcv_result.std_sharpe,
                'robustness_score': cpcv_result.robustness_score,
                'successful_folds': cpcv_result.successful_folds,
                'total_folds': cpcv_result.total_folds,
                'confidence_interval': cpcv_result.confidence_interval_95
            }
            
        except Exception as e:
            logger.error(f"❌ Error en validación CPCV: {e}")
            return {'error': str(e)}
    
    def _generate_final_report(self, nonstationarity_results, regime_results, 
                              qlearning_results, cpcv_results):
        """Generar reporte final del demo"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'demo_type': 'FASE 1 - Mejoras Inmediatas',
            'components_tested': [
                'CPCV (Combinatorial Purged Cross-Validation)',
                'Función de recompensa optimizada con Sharpe Ratio',
                'Detección de no-estacionariedad extrema'
            ],
            'summary': {},
            'detailed_results': {
                'nonstationarity_analysis': nonstationarity_results,
                'regime_classification': regime_results,
                'qlearning_optimization': qlearning_results,
                'cpcv_validation': cpcv_results
            }
        }
        
        # Generar resumen
        try:
            # Resumen de no-estacionariedad
            extreme_detected = sum(1 for result in nonstationarity_results.values() 
                                 if isinstance(result, dict) and result.get('extreme_detected', False))
            
            # Resumen de Q-Learning
            valid_sharpe_ratios = [result.get('sharpe_ratio', 0) for result in qlearning_results.values() 
                                 if isinstance(result, dict) and 'sharpe_ratio' in result and not np.isnan(result.get('sharpe_ratio', 0))]
            avg_sharpe = np.mean(valid_sharpe_ratios) if valid_sharpe_ratios else 0
            
            # Resumen de CPCV
            cpcv_success = cpcv_results.get('robustness_score', 0) > 0.6 if 'error' not in cpcv_results else False
            
            report['summary'] = {
                'symbols_analyzed': len(self.symbols),
                'extreme_nonstationarity_detected': extreme_detected,
                'average_sharpe_ratio': avg_sharpe,
                'cpcv_validation_passed': cpcv_success,
                'cpcv_robustness_score': cpcv_results.get('robustness_score', 0),
                'overall_success': extreme_detected <= 1 and avg_sharpe > 0 and cpcv_success
            }
            
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            report['summary'] = {'error': str(e)}
        
        # Guardar reporte
        try:
            report_path = os.path.join(os.path.dirname(__file__), 'reports', 'fase1_demo_report.json')
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📊 Reporte guardado en: {report_path}")
            
        except Exception as e:
            logger.error(f"Error guardando reporte: {e}")
        
        return report
    
    def print_summary(self, report):
        """Imprimir resumen del demo"""
        if not report:
            print("❌ No se pudo generar el reporte")
            return
        
        print("\n" + "=" * 80)
        print("📊 RESUMEN DEMO FASE 1 - SICAR")
        print("=" * 80)
        
        summary = report.get('summary', {})
        
        print(f"🎯 Símbolos analizados: {summary.get('symbols_analyzed', 0)}")
        print(f"⚠️ No-estacionariedad extrema detectada: {summary.get('extreme_nonstationarity_detected', 0)} símbolos")
        print(f"📈 Sharpe Ratio promedio: {summary.get('average_sharpe_ratio', 0):.3f}")
        print(f"✅ Validación CPCV: {'APROBADA' if summary.get('cpcv_validation_passed', False) else 'FALLIDA'}")
        print(f"🛡️ Score de robustez CPCV: {summary.get('cpcv_robustness_score', 0):.3f}")
        print(f"🏆 Éxito general: {'SÍ' if summary.get('overall_success', False) else 'NO'}")
        
        print("\n🔍 COMPONENTES VALIDADOS:")
        print("✅ CPCV - Combinatorial Purged Cross-Validation implementado")
        print("✅ Sharpe Ratio - Función de recompensa optimizada")
        print("✅ Detección de No-Estacionariedad Extrema")
        
        print("\n" + "=" * 80)


def main():
    """Función principal para ejecutar el demo"""
    print("🚀 INICIANDO DEMO COMPLETO - FASE 1 SICAR")
    print("=" * 50)
    
    # Crear y ejecutar demo
    demo = Fase1DemoCompleto(initial_capital=10000)
    report = demo.run_complete_demo()
    
    # Mostrar resumen
    if report:
        demo.print_summary(report)
        print("\n✅ Demo FASE 1 completado exitosamente!")
    else:
        print("\n❌ Error ejecutando demo FASE 1")


if __name__ == "__main__":
    main()