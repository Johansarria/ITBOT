#!/usr/bin/env python3
"""
Sistema de Optimización de Parámetros SICAR Simplificado
Optimiza automáticamente los parámetros del sistema para alcanzar 15% ROI mensual
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Any
import itertools
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sicar_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SICARParameterOptimizer:
    """
    Optimizador de parámetros simplificado para el sistema SICAR
    """
    
    def __init__(self):
        # Parámetros base del sistema
        self.base_config = {
            'initial_capital': 10000,
            'symbols': ['BTCUSDT', 'ETHUSDT'],
            'timeframe': '1h',
            'lookback_days': 30
        }
        
        # Rangos de parámetros a optimizar (más enfocados)
        self.parameter_ranges = {
            'risk_per_trade': [0.02, 0.05, 0.08, 0.10],        # 2% a 10%
            'stop_loss_pct': [0.03, 0.05, 0.08, 0.10],         # 3% a 10%
            'take_profit_pct': [0.10, 0.15, 0.20, 0.25],       # 10% a 25%
            'position_size_pct': [0.30, 0.50, 0.70],           # 30% a 70%
            'confidence_threshold': [0.55, 0.65, 0.75],        # 55% a 75%
            'max_positions': [1, 2, 3],                        # 1 a 3 posiciones
        }
        
        self.target_monthly_roi = 0.15  # 15% mensual
        self.best_config = None
        self.best_performance = -float('inf')
        self.optimization_results = []
        
    def generate_parameter_combinations(self, max_combinations: int = 50) -> List[Dict]:
        """
        Genera combinaciones de parámetros para optimizar
        """
        logger.info(f"🔧 Generando combinaciones de parámetros (máx: {max_combinations})")
        
        # Generar todas las combinaciones posibles
        keys = list(self.parameter_ranges.keys())
        values = list(self.parameter_ranges.values())
        
        all_combinations = list(itertools.product(*values))
        
        # Limitar el número de combinaciones si es necesario
        if len(all_combinations) > max_combinations:
            selected_indices = np.linspace(0, len(all_combinations)-1, max_combinations, dtype=int)
            selected_combinations = [all_combinations[i] for i in selected_indices]
        else:
            selected_combinations = all_combinations
        
        # Convertir a diccionarios
        parameter_configs = []
        for combination in selected_combinations:
            config = dict(zip(keys, combination))
            
            # Validar configuración
            if self._validate_config(config):
                parameter_configs.append(config)
        
        logger.info(f"✅ Generadas {len(parameter_configs)} configuraciones válidas")
        return parameter_configs
    
    def _validate_config(self, config: Dict) -> bool:
        """
        Valida que una configuración de parámetros sea lógica
        """
        # Take profit debe ser mayor que stop loss
        if config['take_profit_pct'] <= config['stop_loss_pct']:
            return False
        
        # Risk per trade no debe ser mayor que position size
        if config['risk_per_trade'] > config['position_size_pct']:
            return False
        
        return True
    
    def simulate_trading_strategy(self, config: Dict) -> Dict[str, Any]:
        """
        Simula una estrategia de trading con parámetros específicos
        """
        try:
            # Generar datos sintéticos para simulación
            np.random.seed(42)
            days = 30
            hours_per_day = 24
            total_hours = days * hours_per_day
            
            # Simular precios con tendencia alcista y volatilidad
            initial_price = 50000  # BTC inicial
            returns = np.random.normal(0.001, 0.02, total_hours)  # 0.1% promedio, 2% volatilidad
            prices = [initial_price]
            
            for ret in returns:
                new_price = prices[-1] * (1 + ret)
                prices.append(new_price)
            
            # Crear DataFrame de precios
            timestamps = pd.date_range(start='2024-01-01', periods=len(prices), freq='H')
            price_data = pd.DataFrame({
                'timestamp': timestamps,
                'close': prices,
                'high': [p * 1.01 for p in prices],
                'low': [p * 0.99 for p in prices],
                'volume': np.random.uniform(1000, 5000, len(prices))
            })
            
            # Simular trading
            results = self._simulate_trades(price_data, config)
            
            # Calcular métricas
            performance = self._calculate_performance_metrics(results, config)
            
            return performance
            
        except Exception as e:
            logger.error(f"❌ Error en simulación: {str(e)}")
            return {'error': str(e), 'config': config}
    
    def _simulate_trades(self, price_data: pd.DataFrame, config: Dict) -> Dict:
        """
        Simula trades basado en señales técnicas simples
        """
        capital = self.base_config['initial_capital']
        positions = []
        trades = []
        portfolio_values = []
        
        # Calcular indicadores simples
        price_data['sma_20'] = price_data['close'].rolling(20).mean()
        price_data['sma_50'] = price_data['close'].rolling(50).mean()
        price_data['rsi'] = self._calculate_rsi(price_data['close'], 14)
        
        for i in range(50, len(price_data)):  # Empezar después de tener suficientes datos
            current_price = price_data['close'].iloc[i]
            current_rsi = price_data['rsi'].iloc[i]
            sma_20 = price_data['sma_20'].iloc[i]
            sma_50 = price_data['sma_50'].iloc[i]
            
            # Calcular valor del portafolio
            portfolio_value = capital
            for pos in positions:
                portfolio_value += pos['quantity'] * (current_price - pos['entry_price'])
            
            portfolio_values.append({
                'timestamp': price_data['timestamp'].iloc[i],
                'portfolio_value': portfolio_value,
                'price': current_price
            })
            
            # Gestionar posiciones existentes
            positions_to_close = []
            for j, pos in enumerate(positions):
                # Stop loss
                if pos['direction'] == 'long':
                    if current_price <= pos['stop_loss']:
                        pnl = (current_price - pos['entry_price']) * pos['quantity']
                        trades.append({
                            'entry_price': pos['entry_price'],
                            'exit_price': current_price,
                            'quantity': pos['quantity'],
                            'pnl': pnl,
                            'exit_reason': 'stop_loss',
                            'direction': 'long'
                        })
                        capital += pos['quantity'] * current_price
                        positions_to_close.append(j)
                    # Take profit
                    elif current_price >= pos['take_profit']:
                        pnl = (current_price - pos['entry_price']) * pos['quantity']
                        trades.append({
                            'entry_price': pos['entry_price'],
                            'exit_price': current_price,
                            'quantity': pos['quantity'],
                            'pnl': pnl,
                            'exit_reason': 'take_profit',
                            'direction': 'long'
                        })
                        capital += pos['quantity'] * current_price
                        positions_to_close.append(j)
            
            # Cerrar posiciones
            for j in reversed(positions_to_close):
                positions.pop(j)
            
            # Señales de entrada (estrategia simple)
            if len(positions) < config['max_positions']:
                # Señal alcista: SMA 20 > SMA 50 y RSI < 70
                if (sma_20 > sma_50 and current_rsi < 70 and 
                    np.random.random() > (1 - config['confidence_threshold'])):
                    
                    position_value = capital * config['position_size_pct']
                    quantity = position_value / current_price
                    
                    if position_value > 100:  # Mínimo $100 por trade
                        stop_loss = current_price * (1 - config['stop_loss_pct'])
                        take_profit = current_price * (1 + config['take_profit_pct'])
                        
                        positions.append({
                            'entry_price': current_price,
                            'quantity': quantity,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'direction': 'long'
                        })
                        
                        capital -= position_value
        
        return {
            'trades': trades,
            'portfolio_values': portfolio_values,
            'final_capital': capital + sum(pos['quantity'] * price_data['close'].iloc[-1] for pos in positions)
        }
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calcula RSI
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_performance_metrics(self, results: Dict, config: Dict) -> Dict:
        """
        Calcula métricas de rendimiento
        """
        trades = results['trades']
        portfolio_values = results['portfolio_values']
        
        if not trades:
            return {
                'total_return': 0,
                'monthly_roi': 0,
                'total_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'score': -1000,
                'config': config
            }
        
        # Calcular métricas básicas
        initial_capital = self.base_config['initial_capital']
        final_capital = results['final_capital']
        total_return = (final_capital - initial_capital) / initial_capital
        
        # ROI mensual
        monthly_roi = total_return  # Asumiendo 30 días de simulación
        
        # Estadísticas de trades
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        
        total_profit = sum(t['pnl'] for t in winning_trades)
        total_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Drawdown máximo
        portfolio_vals = [pv['portfolio_value'] for pv in portfolio_values]
        peak = portfolio_vals[0]
        max_drawdown = 0
        
        for value in portfolio_vals:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Score compuesto
        roi_score = monthly_roi * 100
        win_rate_score = win_rate * 20
        profit_factor_score = min(profit_factor, 5) * 10
        drawdown_penalty = max_drawdown * -50
        trade_frequency_score = min(len(trades) / 10, 5) * 5
        
        score = roi_score + win_rate_score + profit_factor_score + drawdown_penalty + trade_frequency_score
        
        return {
            'total_return': total_return,
            'monthly_roi': monthly_roi,
            'total_trades': len(trades),
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'score': score,
            'target_achieved': monthly_roi >= self.target_monthly_roi,
            'config': config
        }
    
    def optimize_parameters(self, max_combinations: int = 30) -> Dict:
        """
        Ejecuta la optimización de parámetros
        """
        logger.info("🚀 Iniciando optimización de parámetros SICAR")
        logger.info(f"🎯 Objetivo: {self.target_monthly_roi:.1%} ROI mensual")
        
        # Generar combinaciones de parámetros
        parameter_configs = self.generate_parameter_combinations(max_combinations)
        
        logger.info(f"🔄 Probando {len(parameter_configs)} configuraciones...")
        
        # Ejecutar simulaciones
        for i, config in enumerate(parameter_configs):
            logger.info(f"⏳ Probando configuración {i+1}/{len(parameter_configs)}")
            
            result = self.simulate_trading_strategy(config)
            
            if 'error' not in result:
                self.optimization_results.append(result)
                
                # Actualizar mejor configuración
                if result['score'] > self.best_performance:
                    self.best_performance = result['score']
                    self.best_config = result
                    
                    logger.info(f"🎯 Nueva mejor configuración encontrada!")
                    logger.info(f"   📈 ROI Mensual: {result['monthly_roi']:.2%}")
                    logger.info(f"   🎯 Score: {result['score']:.2f}")
                    logger.info(f"   📊 Win Rate: {result['win_rate']:.1%}")
                    logger.info(f"   💹 Profit Factor: {result['profit_factor']:.2f}")
        
        # Generar reporte final
        self._generate_optimization_report()
        
        return self.best_config
    
    def _generate_optimization_report(self):
        """
        Genera reporte detallado de la optimización
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Ordenar resultados por score
        sorted_results = sorted(
            self.optimization_results, 
            key=lambda x: x['score'], 
            reverse=True
        )
        
        # Reporte de texto
        report_path = f"sicar_optimization_report_{timestamp}.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=== REPORTE DE OPTIMIZACIÓN SICAR ===\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Objetivo: {self.target_monthly_roi:.1%} ROI mensual\n\n")
            
            f.write("📊 MEJORES CONFIGURACIONES:\n")
            f.write("=" * 50 + "\n")
            
            for i, result in enumerate(sorted_results[:5], 1):
                f.write(f"\n{i}. Score: {result['score']:.2f}\n")
                f.write(f"   ROI Mensual: {result['monthly_roi']:.2%}\n")
                f.write(f"   Total Trades: {result['total_trades']}\n")
                f.write(f"   Win Rate: {result['win_rate']:.1%}\n")
                f.write(f"   Profit Factor: {result['profit_factor']:.2f}\n")
                f.write(f"   Max Drawdown: {result['max_drawdown']:.1%}\n")
                f.write(f"   Objetivo Alcanzado: {'✅' if result['target_achieved'] else '❌'}\n")
                
                f.write("   Configuración:\n")
                for key, value in result['config'].items():
                    f.write(f"     {key}: {value}\n")
        
        # Resultados JSON
        json_path = f"sicar_optimization_results_{timestamp}.json"
        with open(json_path, 'w') as f:
            json.dump({
                'timestamp': timestamp,
                'target_monthly_roi': self.target_monthly_roi,
                'best_config': self.best_config,
                'all_results': sorted_results,
                'summary': {
                    'total_configurations_tested': len(self.optimization_results),
                    'configurations_achieving_target': len([r for r in self.optimization_results if r['target_achieved']]),
                    'best_monthly_roi': max([r['monthly_roi'] for r in self.optimization_results]) if self.optimization_results else 0
                }
            }, f, indent=2, default=str)
        
        logger.info(f"📄 Reporte generado: {report_path}")
        logger.info(f"📊 Datos JSON: {json_path}")
        
        if self.best_config and self.best_config['target_achieved']:
            logger.info("🎉 ¡OBJETIVO ALCANZADO! Configuración óptima encontrada")
        else:
            logger.info("⚠️ Objetivo no alcanzado. Considerar ajustar rangos de parámetros")

def main():
    """
    Función principal para ejecutar la optimización
    """
    optimizer = SICARParameterOptimizer()
    
    logger.info("🎯 Iniciando optimización para alcanzar 15% ROI mensual")
    
    # Ejecutar optimización
    best_config = optimizer.optimize_parameters(max_combinations=30)
    
    if best_config:
        logger.info("✅ Optimización completada")
        logger.info(f"🏆 Mejor ROI mensual: {best_config['monthly_roi']:.2%}")
        logger.info(f"🎯 Objetivo alcanzado: {'✅' if best_config['target_achieved'] else '❌'}")
        
        # Mostrar configuración óptima
        logger.info("🔧 Configuración óptima encontrada:")
        for key, value in best_config['config'].items():
            logger.info(f"   {key}: {value}")
    else:
        logger.error("❌ No se encontraron configuraciones válidas")

if __name__ == "__main__":
    main()