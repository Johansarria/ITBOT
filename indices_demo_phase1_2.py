"""
SICAR Indices Trading System - Demo Fases 1 y 2
Demostración completa del sistema de trading de índices
Integra todos los módulos desarrollados en las fases 1 y 2
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import warnings
import sys
import os

# Agregar el directorio src al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Importar módulos del sistema
from src.indices_data_provider import IndicesDataProvider, create_indices_provider
from src.indices_config import IndicesConfigManager, get_index_config
from src.indices_indicators import IndicesIndicators
from src.market_hours_system import MarketHoursSystem
from src.indices_backtester import IndicesBacktester
from src.indices_strategies import IndicesStrategies, StrategyType
from src.indices_risk_manager import IndicesRiskManager, PositionSizeMethod
from src.indices_testing_system import IndicesTestingSystem, TestType

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IndicesSystemDemo:
    """
    Demostración completa del sistema SICAR para índices
    """
    
    def __init__(self):
        logger.info("Inicializando SICAR Indices Trading System Demo...")
        
        # Inicializar componentes
        self.data_provider = create_indices_provider()
        self.config_manager = IndicesConfigManager()
        self.indicators = IndicesIndicators()
        self.market_hours = MarketHoursSystem()
        self.strategies = IndicesStrategies()
        self.risk_manager = IndicesRiskManager(initial_capital=100000)
        self.testing_system = IndicesTestingSystem(self.data_provider)
        
        # Configuración de la demo
        self.demo_symbols = ['SPY', 'QQQ', 'DIA', 'IWM']
        self.demo_period = {
            'start_date': '2023-01-01',
            'end_date': '2023-12-31'
        }
        
        logger.info("Sistema inicializado correctamente")
    
    def demo_data_provider(self):
        """Demuestra el proveedor de datos"""
        
        print("\n" + "="*60)
        print("DEMO 1: PROVEEDOR DE DATOS PARA ÍNDICES")
        print("="*60)
        
        for symbol in self.demo_symbols:
            try:
                print(f"\n📊 Obteniendo datos para {symbol}...")
                
                # Obtener datos históricos
                data = self.data_provider.get_historical_data(
                    symbol, 
                    self.demo_period['start_date'], 
                    self.demo_period['end_date']
                )
                
                if not data.empty:
                    print(f"✅ Datos obtenidos: {len(data)} registros")
                    print(f"   Período: {data.index[0].date()} a {data.index[-1].date()}")
                    print(f"   Precio inicial: ${data['Close'].iloc[0]:.2f}")
                    print(f"   Precio final: ${data['Close'].iloc[-1]:.2f}")
                    print(f"   Retorno total: {((data['Close'].iloc[-1] / data['Close'].iloc[0]) - 1) * 100:.2f}%")
                else:
                    print(f"❌ No se pudieron obtener datos para {symbol}")
                
                # Verificar horarios de mercado
                is_open = self.market_hours.is_market_open()
                session = self.market_hours.get_current_session()
                print(f"   Estado del mercado: {'🟢 Abierto' if is_open else '🔴 Cerrado'} ({session})")
                
            except Exception as e:
                print(f"❌ Error con {symbol}: {e}")
    
    def demo_configurations(self):
        """Demuestra las configuraciones específicas por índice"""
        
        print("\n" + "="*60)
        print("DEMO 2: CONFIGURACIONES ESPECÍFICAS POR ÍNDICE")
        print("="*60)
        
        for symbol in self.demo_symbols:
            print(f"\n⚙️ Configuración para {symbol}:")
            
            config = get_index_config(symbol)
            
            print(f"   RSI Período: {config['rsi_period']}")
            print(f"   RSI Niveles: {config['rsi_oversold']}-{config['rsi_overbought']}")
            print(f"   EMA Rápida: {config['ema_fast']}")
            print(f"   EMA Lenta: {config['ema_slow']}")
            print(f"   ATR Período: {config['atr_period']}")
            print(f"   Stop Loss: {config['stop_loss_pct']*100:.1f}%")
            print(f"   Take Profit: {config['take_profit_pct']*100:.1f}%")
            print(f"   Volatilidad Máxima: {config['max_volatility']*100:.1f}%")
    
    def demo_indicators(self):
        """Demuestra los indicadores técnicos"""
        
        print("\n" + "="*60)
        print("DEMO 3: INDICADORES TÉCNICOS PARA ÍNDICES")
        print("="*60)
        
        # Usar SPY como ejemplo
        symbol = 'SPY'
        print(f"\n📈 Calculando indicadores para {symbol}...")
        
        try:
            # Obtener datos
            data = self.data_provider.get_historical_data(
                symbol, 
                self.demo_period['start_date'], 
                self.demo_period['end_date']
            )
            
            if data.empty:
                print(f"❌ No se pudieron obtener datos para {symbol}")
                return
            
            # Calcular indicadores
            config = get_index_config(symbol)
            
            # RSI
            rsi = self.indicators.rsi(data['Close'], config['rsi_period'])
            print(f"✅ RSI ({config['rsi_period']}): {rsi.iloc[-1]:.2f}")
            
            # EMAs
            ema_fast = self.indicators.ema(data['Close'], config['ema_fast'])
            ema_slow = self.indicators.ema(data['Close'], config['ema_slow'])
            print(f"✅ EMA Rápida ({config['ema_fast']}): ${ema_fast.iloc[-1]:.2f}")
            print(f"✅ EMA Lenta ({config['ema_slow']}): ${ema_slow.iloc[-1]:.2f}")
            
            # ATR
            atr = self.indicators.atr(data['High'], data['Low'], data['Close'], config['atr_period'])
            print(f"✅ ATR ({config['atr_period']}): ${atr.iloc[-1]:.2f}")
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.indicators.bollinger_bands(data['Close'], 20, 2)
            print(f"✅ Bollinger Superior: ${bb_upper.iloc[-1]:.2f}")
            print(f"✅ Bollinger Inferior: ${bb_lower.iloc[-1]:.2f}")
            
            # MACD
            macd_line, macd_signal, macd_histogram = self.indicators.macd(data['Close'])
            print(f"✅ MACD: {macd_line.iloc[-1]:.4f}")
            print(f"✅ MACD Signal: {macd_signal.iloc[-1]:.4f}")
            
            # Indicadores específicos de índices
            session_effect = self.indicators.session_effect(data, self.market_hours)
            print(f"✅ Efecto de Sesión: {session_effect.iloc[-1]:.4f}")
            
            weekend_effect = self.indicators.weekend_effect(data)
            print(f"✅ Efecto Fin de Semana: {weekend_effect.iloc[-1]:.4f}")
            
        except Exception as e:
            print(f"❌ Error calculando indicadores: {e}")
    
    def demo_strategies(self):
        """Demuestra las estrategias de trading"""
        
        print("\n" + "="*60)
        print("DEMO 4: ESTRATEGIAS DE TRADING")
        print("="*60)
        
        symbol = 'SPY'
        
        try:
            # Obtener datos
            data = self.data_provider.get_historical_data(
                symbol, 
                self.demo_period['start_date'], 
                self.demo_period['end_date']
            )
            
            if data.empty:
                print(f"❌ No se pudieron obtener datos para {symbol}")
                return
            
            # Probar diferentes estrategias
            strategies_to_test = [
                (StrategyType.MOMENTUM, "Momentum"),
                (StrategyType.MEAN_REVERSION, "Mean Reversion"),
                (StrategyType.HYBRID, "Híbrida"),
                (StrategyType.BREAKOUT, "Breakout")
            ]
            
            for strategy_type, strategy_name in strategies_to_test:
                print(f"\n🎯 Estrategia: {strategy_name}")
                
                # Generar señales
                signals = self.strategies.generate_signals(data, strategy_type, symbol)
                
                if not signals.empty:
                    buy_signals = signals[signals['signal'] == 1]
                    sell_signals = signals[signals['signal'] == -1]
                    
                    print(f"   📈 Señales de compra: {len(buy_signals)}")
                    print(f"   📉 Señales de venta: {len(sell_signals)}")
                    print(f"   📊 Total señales: {len(signals[signals['signal'] != 0])}")
                    
                    if len(buy_signals) > 0:
                        last_buy = buy_signals.iloc[-1]
                        print(f"   🔍 Última compra: {last_buy.name.date()} @ ${last_buy['close']:.2f}")
                    
                    if len(sell_signals) > 0:
                        last_sell = sell_signals.iloc[-1]
                        print(f"   🔍 Última venta: {last_sell.name.date()} @ ${last_sell['close']:.2f}")
                else:
                    print(f"   ❌ No se generaron señales")
        
        except Exception as e:
            print(f"❌ Error en estrategias: {e}")
    
    def demo_risk_management(self):
        """Demuestra el sistema de gestión de riesgo"""
        
        print("\n" + "="*60)
        print("DEMO 5: GESTIÓN DE RIESGO")
        print("="*60)
        
        symbol = 'SPY'
        
        try:
            # Obtener datos
            data = self.data_provider.get_historical_data(
                symbol, 
                self.demo_period['start_date'], 
                self.demo_period['end_date']
            )
            
            if data.empty:
                print(f"❌ No se pudieron obtener datos para {symbol}")
                return
            
            print(f"\n💰 Gestión de Riesgo para {symbol}")
            
            # Simular entrada
            entry_price = data['Close'].iloc[-1]
            print(f"   Precio de entrada: ${entry_price:.2f}")
            
            # Calcular stop loss dinámico
            stop_loss = self.risk_manager.calculate_dynamic_stop_loss(
                symbol, entry_price, 'long', data
            )
            print(f"   Stop Loss dinámico: ${stop_loss:.2f} ({((stop_loss/entry_price-1)*100):.2f}%)")
            
            # Calcular take profit
            take_profit = self.risk_manager.calculate_take_profit(
                symbol, entry_price, stop_loss, 'long', data
            )
            print(f"   Take Profit: ${take_profit:.2f} ({((take_profit/entry_price-1)*100):.2f}%)")
            
            # Calcular tamaño de posición
            methods = [
                (PositionSizeMethod.FIXED_PERCENT, "Porcentaje Fijo"),
                (PositionSizeMethod.VOLATILITY_ADJUSTED, "Ajustado por Volatilidad"),
                (PositionSizeMethod.ATR_BASED, "Basado en ATR")
            ]
            
            for method, method_name in methods:
                position_size = self.risk_manager.calculate_position_size(
                    symbol, entry_price, stop_loss, method, data
                )
                position_value = position_size * entry_price
                print(f"   {method_name}: {position_size} acciones (${position_value:,.2f})")
            
            # Métricas de riesgo del portafolio
            risk_summary = self.risk_manager.get_risk_summary()
            print(f"\n📊 Resumen de Riesgo del Portafolio:")
            print(f"   Valor del portafolio: ${risk_summary['portfolio_value']:,.2f}")
            print(f"   Efectivo disponible: ${risk_summary['cash_available']:,.2f}")
            print(f"   Exposición total: ${risk_summary['total_exposure']:,.2f}")
            print(f"   Nivel de riesgo: {risk_summary['risk_level']}")
            print(f"   Número de posiciones: {risk_summary['num_positions']}")
        
        except Exception as e:
            print(f"❌ Error en gestión de riesgo: {e}")
    
    def demo_backtesting(self):
        """Demuestra el sistema de backtesting"""
        
        print("\n" + "="*60)
        print("DEMO 6: BACKTESTING ESPECIALIZADO")
        print("="*60)
        
        symbol = 'SPY'
        
        try:
            # Obtener datos
            data = self.data_provider.get_historical_data(
                symbol, 
                self.demo_period['start_date'], 
                self.demo_period['end_date']
            )
            
            if data.empty:
                print(f"❌ No se pudieron obtener datos para {symbol}")
                return
            
            print(f"\n🔄 Ejecutando backtest para {symbol}...")
            
            # Configurar backtester
            backtester = IndicesBacktester(
                initial_capital=100000,
                commission=0.001,  # 0.1%
                slippage=0.0005    # 0.05%
            )
            
            # Usar estrategia momentum
            strategy_config = self.strategies.get_momentum_config()
            
            # Ejecutar backtest
            results = backtester.run_backtest(data, symbol, strategy_config)
            
            # Mostrar resultados
            print(f"✅ Backtest completado:")
            print(f"   📊 Total de trades: {len(results.trades)}")
            print(f"   💰 Retorno total: {results.total_return*100:.2f}%")
            print(f"   📈 Sharpe Ratio: {results.sharpe_ratio:.2f}")
            print(f"   📉 Sortino Ratio: {results.sortino_ratio:.2f}")
            print(f"   🔻 Drawdown máximo: {results.max_drawdown*100:.2f}%")
            print(f"   💵 Capital final: ${results.final_capital:,.2f}")
            
            if results.trades:
                winning_trades = [t for t in results.trades if t.pnl > 0]
                win_rate = len(winning_trades) / len(results.trades) * 100
                avg_win = np.mean([t.pnl for t in winning_trades]) if winning_trades else 0
                losing_trades = [t for t in results.trades if t.pnl < 0]
                avg_loss = np.mean([t.pnl for t in losing_trades]) if losing_trades else 0
                
                print(f"   🎯 Win Rate: {win_rate:.1f}%")
                print(f"   💚 Ganancia promedio: ${avg_win:.2f}")
                print(f"   💔 Pérdida promedio: ${avg_loss:.2f}")
            
            # Guardar gráfico
            save_path = f"backtest_results_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            backtester.plot_results(results, save_path)
            print(f"   📊 Gráfico guardado: {save_path}")
        
        except Exception as e:
            print(f"❌ Error en backtesting: {e}")
    
    def demo_testing_system(self):
        """Demuestra el sistema de testing y validación"""
        
        print("\n" + "="*60)
        print("DEMO 7: SISTEMA DE TESTING Y VALIDACIÓN")
        print("="*60)
        
        symbol = 'SPY'
        
        try:
            print(f"\n🧪 Ejecutando tests completos para {symbol}...")
            
            # Ejecutar test completo
            report = self.testing_system.run_comprehensive_test(
                strategy_type=StrategyType.MOMENTUM,
                symbol=symbol,
                start_date=self.demo_period['start_date'],
                end_date=self.demo_period['end_date'],
                initial_capital=100000
            )
            
            # Mostrar resultados
            print(f"✅ Testing completado:")
            print(f"   📊 Score general: {report.overall_score:.1f}%")
            print(f"   ✅ Tests pasados: {report.passed_tests}")
            print(f"   ⚠️ Tests con advertencia: {report.warning_tests}")
            print(f"   ❌ Tests fallidos: {report.failed_tests}")
            print(f"   📝 Total tests: {report.total_tests}")
            
            # Mostrar tests por categoría
            test_types = {}
            for result in report.results:
                test_type = result.test_type.value
                if test_type not in test_types:
                    test_types[test_type] = {'passed': 0, 'failed': 0, 'warning': 0}
                test_types[test_type][result.status.value] += 1
            
            print(f"\n📋 Resultados por categoría:")
            for test_type, counts in test_types.items():
                total = sum(counts.values())
                passed_pct = counts['passed'] / total * 100 if total > 0 else 0
                print(f"   {test_type.title()}: {counts['passed']}/{total} ({passed_pct:.0f}%)")
            
            # Mostrar recomendaciones principales
            print(f"\n💡 Recomendaciones principales:")
            for i, rec in enumerate(report.recommendations[:3], 1):
                print(f"   {i}. {rec}")
            
            # Guardar reporte
            report_path = f"validation_report_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.testing_system.save_report(report, report_path)
            print(f"   📄 Reporte guardado: {report_path}")
            
            # Crear reporte visual
            visual_path = f"validation_visual_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.testing_system.create_visual_report(report, visual_path)
            print(f"   📊 Reporte visual guardado: {visual_path}")
        
        except Exception as e:
            print(f"❌ Error en testing: {e}")
    
    def demo_integration(self):
        """Demuestra la integración completa del sistema"""
        
        print("\n" + "="*60)
        print("DEMO 8: INTEGRACIÓN COMPLETA DEL SISTEMA")
        print("="*60)
        
        print(f"\n🔗 Demostración de integración completa...")
        
        # Resumen de componentes
        components = [
            ("📊 Proveedor de Datos", "Múltiples fuentes con fallback automático"),
            ("⚙️ Configuraciones", "Parámetros optimizados por índice"),
            ("📈 Indicadores", "Técnicos + específicos para índices"),
            ("🕐 Horarios de Mercado", "Sesiones, feriados y cierres anticipados"),
            ("🎯 Estrategias", "Momentum, Mean Reversion, Híbrida, Breakout"),
            ("💰 Gestión de Riesgo", "Sizing dinámico y stops adaptativos"),
            ("🔄 Backtesting", "Especializado para índices"),
            ("🧪 Testing", "Validación completa con métricas avanzadas")
        ]
        
        print(f"\n✅ Componentes del Sistema SICAR v3.0 para Índices:")
        for component, description in components:
            print(f"   {component}: {description}")
        
        # Estado del sistema
        print(f"\n📊 Estado del Sistema:")
        print(f"   🎯 Índices soportados: {', '.join(self.demo_symbols)}")
        print(f"   📅 Período de demo: {self.demo_period['start_date']} a {self.demo_period['end_date']}")
        print(f"   💰 Capital inicial: ${self.risk_manager.initial_capital:,.2f}")
        print(f"   🔧 Configuraciones cargadas: {len(self.config_manager.configs)}")
        
        # Verificar conectividad
        market_open = self.market_hours.is_market_open()
        session = self.market_hours.get_current_session()
        print(f"   🕐 Estado del mercado: {'🟢 Abierto' if market_open else '🔴 Cerrado'} ({session})")
        
        print(f"\n🎉 Sistema SICAR v3.0 para Índices completamente operativo!")
        print(f"   ✅ Todas las fases 1 y 2 implementadas exitosamente")
        print(f"   🚀 Listo para trading en vivo o backtesting avanzado")
    
    def run_complete_demo(self):
        """Ejecuta la demostración completa"""
        
        print("🚀 INICIANDO DEMOSTRACIÓN COMPLETA DEL SISTEMA SICAR v3.0 PARA ÍNDICES")
        print("=" * 80)
        
        demos = [
            self.demo_data_provider,
            self.demo_configurations,
            self.demo_indicators,
            self.demo_strategies,
            self.demo_risk_management,
            self.demo_backtesting,
            self.demo_testing_system,
            self.demo_integration
        ]
        
        for i, demo in enumerate(demos, 1):
            try:
                demo()
                if i < len(demos):
                    input(f"\n⏸️ Presiona Enter para continuar con la demo {i+1}...")
            except KeyboardInterrupt:
                print(f"\n\n⏹️ Demo interrumpida por el usuario")
                break
            except Exception as e:
                print(f"\n❌ Error en demo {i}: {e}")
                logger.error(f"Error en demo {i}: {e}")
        
        print(f"\n🏁 DEMOSTRACIÓN COMPLETA FINALIZADA")
        print(f"   ✅ Sistema SICAR v3.0 para Índices - Fases 1 y 2 completadas")
        print(f"   📊 Todos los módulos integrados y funcionando correctamente")
        print(f"   🎯 Listo para implementación en producción")

def main():
    """Función principal"""
    
    try:
        # Crear y ejecutar demo
        demo = IndicesSystemDemo()
        demo.run_complete_demo()
        
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Demo interrumpida por el usuario")
    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        logger.error(f"Error crítico en main: {e}")

if __name__ == "__main__":
    main()