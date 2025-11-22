#!/usr/bin/env python3
"""
Debug Capital Scaling - SICAR
=============================

Verificar por qué todos los niveles de capital producen resultados idénticos.
Analizar si el problema está en los datos, señales o cálculo de posiciones.

Año: 2025
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List
import json

from multi_asset_backtester import MultiAssetBacktester
from multi_asset_data_system import MultiAssetDataSystem

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CapitalScalingDebugger:
    """
    Debugger para analizar el escalado de capital
    """
    
    def __init__(self):
        """Inicializar debugger"""
        self.test_capitals = [200, 500, 1000]
        self.test_symbols = ['BTCUSDT', 'ETHUSDT']
        self.debug_results = {}
        
        logger.info("🔍 Debugger de Escalado de Capital inicializado")
        
    def debug_position_sizing(self) -> Dict:
        """
        Debuggear el cálculo de tamaños de posición
        """
        logger.info("\n🔍 DEBUGGEANDO TAMAÑOS DE POSICIÓN...")
        
        debug_data = {
            'position_sizes': {},
            'capital_usage': {},
            'trade_details': {}
        }
        
        for capital in self.test_capitals:
            logger.info(f"\n💰 Analizando capital: ${capital:,.0f}")
            
            # Crear backtester
            backtester = MultiAssetBacktester(initial_capital=capital)
            
            # Simular cálculo de posición para cada símbolo
            position_data = {}
            for symbol in self.test_symbols:
                # Precio simulado
                test_price = 50000 if symbol == 'BTCUSDT' else 3000
                
                # Calcular tamaño de posición
                position_size = backtester.calculate_position_size(symbol, test_price)
                position_pct = (position_size / capital) * 100
                
                position_data[symbol] = {
                    'position_size_usd': position_size,
                    'position_pct': position_pct,
                    'quantity': position_size / test_price,
                    'test_price': test_price
                }
                
                logger.info(f"  {symbol}: ${position_size:.2f} ({position_pct:.2f}%) = {position_size/test_price:.6f} units")
            
            debug_data['position_sizes'][capital] = position_data
            debug_data['capital_usage'][capital] = {
                'initial_capital': capital,
                'current_capital': backtester.current_capital,
                'total_position_value': sum(p['position_size_usd'] for p in position_data.values()),
                'capital_utilization_pct': (sum(p['position_size_usd'] for p in position_data.values()) / capital) * 100
            }
        
        return debug_data
        
    def debug_actual_backtest_differences(self) -> Dict:
        """
        Debuggear diferencias en backtests reales
        """
        logger.info("\n🔍 DEBUGGEANDO BACKTESTS REALES...")
        
        backtest_debug = {
            'trade_histories': {},
            'signal_analysis': {},
            'performance_comparison': {}
        }
        
        for capital in self.test_capitals:
            logger.info(f"\n💰 Ejecutando backtest con capital: ${capital:,.0f}")
            
            # Crear backtester
            backtester = MultiAssetBacktester(initial_capital=capital)
            
            # Ejecutar backtest
            results = backtester.run_backtest(self.test_symbols)
            
            if results:
                # Extraer información detallada
                trade_history = results.get('trade_history', [])
                
                # Analizar trades
                trade_analysis = {
                    'total_trades': len(trade_history),
                    'trade_details': [],
                    'position_sizes': [],
                    'quantities': [],
                    'entry_prices': []
                }
                
                for trade in trade_history:
                    trade_detail = {
                        'symbol': trade.get('symbol'),
                        'side': trade.get('side'),
                        'quantity': trade.get('quantity'),
                        'entry_price': trade.get('entry_price'),
                        'position_size': trade.get('position_size'),
                        'position_size_pct': (trade.get('position_size', 0) / capital) * 100,
                        'signal_strength': trade.get('signal_strength')
                    }
                    
                    trade_analysis['trade_details'].append(trade_detail)
                    trade_analysis['position_sizes'].append(trade.get('position_size', 0))
                    trade_analysis['quantities'].append(trade.get('quantity', 0))
                    trade_analysis['entry_prices'].append(trade.get('entry_price', 0))
                
                # Calcular estadísticas
                if trade_analysis['position_sizes']:
                    trade_analysis['avg_position_size'] = np.mean(trade_analysis['position_sizes'])
                    trade_analysis['avg_position_pct'] = (trade_analysis['avg_position_size'] / capital) * 100
                    trade_analysis['total_position_value'] = sum(trade_analysis['position_sizes'])
                
                backtest_debug['trade_histories'][capital] = trade_analysis
                
                # Información de performance
                backtest_debug['performance_comparison'][capital] = {
                    'initial_capital': results.get('initial_capital'),
                    'final_capital': results.get('final_capital'),
                    'total_return': results.get('total_return'),
                    'total_return_pct': results.get('total_return_pct'),
                    'total_trades': results.get('total_trades'),
                    'win_rate': results.get('win_rate')
                }
                
                logger.info(f"  Trades: {len(trade_history)}, Retorno: {results.get('total_return_pct', 0):+.2f}%")
            
        return backtest_debug
        
    def analyze_scaling_consistency(self, debug_data: Dict) -> Dict:
        """
        Analizar consistencia del escalado
        """
        logger.info("\n📊 ANALIZANDO CONSISTENCIA DEL ESCALADO...")
        
        analysis = {
            'position_size_scaling': {},
            'return_consistency': {},
            'scaling_issues': []
        }
        
        # Analizar escalado de tamaños de posición
        capitals = list(debug_data['trade_histories'].keys())
        
        if len(capitals) >= 2:
            base_capital = capitals[0]
            base_data = debug_data['trade_histories'][base_capital]
            
            for capital in capitals[1:]:
                current_data = debug_data['trade_histories'][capital]
                
                # Verificar si el número de trades es igual
                if base_data['total_trades'] != current_data['total_trades']:
                    analysis['scaling_issues'].append(f"Número de trades diferente: {base_capital} vs {capital}")
                
                # Verificar escalado de posiciones
                if (base_data['trade_details'] and current_data['trade_details'] and 
                    len(base_data['trade_details']) == len(current_data['trade_details'])):
                    
                    scaling_factor = capital / base_capital
                    
                    for i, (base_trade, current_trade) in enumerate(zip(base_data['trade_details'], current_data['trade_details'])):
                        expected_position_size = base_trade['position_size'] * scaling_factor
                        actual_position_size = current_trade['position_size']
                        
                        scaling_ratio = actual_position_size / expected_position_size if expected_position_size > 0 else 0
                        
                        if abs(scaling_ratio - 1.0) > 0.01:  # Tolerancia del 1%
                            analysis['scaling_issues'].append(
                                f"Trade {i}: Escalado incorrecto {base_capital}->{capital}. "
                                f"Esperado: ${expected_position_size:.2f}, Actual: ${actual_position_size:.2f}"
                            )
                
                # Verificar consistencia de retornos porcentuales
                base_return = debug_data['performance_comparison'][base_capital]['total_return_pct']
                current_return = debug_data['performance_comparison'][capital]['total_return_pct']
                
                if abs(base_return - current_return) > 0.001:  # Tolerancia de 0.001%
                    analysis['scaling_issues'].append(
                        f"Retorno % inconsistente: {base_capital} ({base_return:.3f}%) vs {capital} ({current_return:.3f}%)"
                    )
        
        # Resumen de análisis
        if not analysis['scaling_issues']:
            analysis['conclusion'] = "✅ El escalado funciona correctamente - resultados idénticos son esperados"
        else:
            analysis['conclusion'] = "⚠️ Se encontraron problemas en el escalado"
        
        return analysis
        
    def print_debug_results(self, position_debug: Dict, backtest_debug: Dict, scaling_analysis: Dict):
        """
        Imprimir resultados del debug
        """
        print("\n" + "="*80)
        print("🔍 RESULTADOS DEL DEBUG - ESCALADO DE CAPITAL")
        print("="*80)
        
        # Tamaños de posición teóricos
        print(f"\n💰 TAMAÑOS DE POSICIÓN TEÓRICOS:")
        print("-" * 50)
        for capital, data in position_debug['position_sizes'].items():
            print(f"\nCapital: ${capital:,.0f}")
            for symbol, pos_data in data.items():
                print(f"  {symbol}: ${pos_data['position_size_usd']:7.2f} ({pos_data['position_pct']:4.1f}%) "
                      f"= {pos_data['quantity']:.6f} units @ ${pos_data['test_price']:,.0f}")
        
        # Backtests reales
        print(f"\n📊 BACKTESTS REALES:")
        print("-" * 30)
        for capital, data in backtest_debug['performance_comparison'].items():
            print(f"${capital:4.0f}: {data['total_return_pct']:+6.3f}% | "
                  f"{data['total_trades']:2.0f} trades | "
                  f"${data['total_return']:+7.2f}")
        
        # Análisis de escalado
        print(f"\n🔍 ANÁLISIS DE ESCALADO:")
        print("-" * 30)
        print(f"Conclusión: {scaling_analysis['conclusion']}")
        
        if scaling_analysis['scaling_issues']:
            print(f"\n⚠️ PROBLEMAS ENCONTRADOS:")
            for issue in scaling_analysis['scaling_issues']:
                print(f"  • {issue}")
        else:
            print(f"\n✅ EXPLICACIÓN:")
            print(f"  • Los resultados idénticos son CORRECTOS")
            print(f"  • Mismos datos de mercado → mismas señales → mismos momentos de entrada/salida")
            print(f"  • Tamaños de posición escalan proporcionalmente")
            print(f"  • Retorno % es idéntico porque es la misma estrategia")
            print(f"  • Retorno absoluto escala linealmente con el capital")
        
    def run_complete_debug(self) -> Dict:
        """
        Ejecutar debug completo
        """
        logger.info("🚀 Iniciando debug completo del escalado de capital...")
        
        try:
            # 1. Debug de tamaños de posición teóricos
            position_debug = self.debug_position_sizing()
            
            # 2. Debug de backtests reales
            backtest_debug = self.debug_actual_backtest_differences()
            
            # 3. Análisis de consistencia
            scaling_analysis = self.analyze_scaling_consistency(backtest_debug)
            
            # 4. Imprimir resultados
            self.print_debug_results(position_debug, backtest_debug, scaling_analysis)
            
            # 5. Compilar resultados
            complete_results = {
                'position_debug': position_debug,
                'backtest_debug': backtest_debug,
                'scaling_analysis': scaling_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
            # 6. Guardar resultados
            with open('capital_scaling_debug_results.json', 'w', encoding='utf-8') as f:
                json.dump(complete_results, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info("✅ Debug completo finalizado")
            return complete_results
            
        except Exception as e:
            logger.error(f"❌ Error en debug: {e}")
            return {}

def main():
    """Función principal"""
    print("🔍 Iniciando Debug de Escalado de Capital SICAR...")
    
    try:
        debugger = CapitalScalingDebugger()
        results = debugger.run_complete_debug()
        
        if results:
            print("\n✅ Debug completado exitosamente")
            return debugger
        else:
            print("\n❌ Error en el debug")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error en main: {e}")
        return None

if __name__ == "__main__":
    debug_system = main()