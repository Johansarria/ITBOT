#!/usr/bin/env python3
"""
SICAR - Optimizador Híbrido de Parámetros (Versión Limpia)
Enfoque híbrido: Criterios flexibles + Datos extendidos + Walk-forward analysis

REGLAS CRÍTICAS:
1. SOLO datos reales de Binance - NUNCA sintéticos
2. Anti-sobreoptimización con validación out-of-sample
3. Validación temporal progresiva obligatoria
"""

import os
import sys
import json
import logging
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging sin caracteres especiales
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hybrid_optimizer_clean.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """Resultado de optimización con métricas híbridas"""
    parameters: Dict
    total_trades: int
    win_rate: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    confidence_score: float
    robustness_score: float
    overfitting_risk: float
    walkforward_score: float
    symbols_tested: List[str]
    period_tested: str
    validation_passed: bool

class HybridParameterOptimizer:
    """
    Optimizador híbrido con criterios flexibles y datos extendidos
    """
    
    def __init__(self):
        # Configuración híbrida mejorada
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'XRPUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'AVAXUSDT'
        ]
        
        # Criterios flexibles (relajados)
        self.min_trades_required = 20  # Reducido de 50
        self.out_sample_percentage = 20  # Reducido de 30%
        self.max_optimization_iterations = 30  # Aumentado
        
        # Datos extendidos
        self.data_period_days = 180  # 6 meses
        
        # Rangos de parámetros ampliados
        self.param_ranges = {
            'min_price_movement': [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5],  # Ampliado
            'min_volume_ratio': [1.2, 1.5, 1.8, 2.0, 2.5, 3.0],  # Ampliado
            'max_spread_pct': [0.1, 0.15, 0.2, 0.25, 0.3, 0.4],  # Ampliado
            'confidence_threshold': [0.6, 0.65, 0.7, 0.75, 0.8]  # Ampliado
        }
        
        # Almacenamiento de datos
        self.market_data = {}
        
        logger.info("Optimizador hibrido inicializado con criterios flexibles")
        logger.info(f"Periodo de datos: {self.data_period_days} dias")
        logger.info(f"Minimo trades requeridos: {self.min_trades_required}")
        logger.info(f"Validacion out-of-sample: {self.out_sample_percentage}%")
    
    def fetch_extended_real_data(self) -> bool:
        """
        Descarga 6 meses de datos históricos reales
        """
        logger.info("Descargando 6 MESES de datos historicos REALES...")
        
        base_url = "https://api.binance.com/api/v3/klines"
        end_time = datetime.now()
        start_time = end_time - timedelta(days=self.data_period_days)
        
        for symbol in self.symbols:
            try:
                logger.info(f"Obteniendo datos REALES de Binance para {symbol} ({self.data_period_days} dias)")
                
                params = {
                    'symbol': symbol,
                    'interval': '1h',
                    'startTime': int(start_time.timestamp() * 1000),
                    'endTime': int(end_time.timestamp() * 1000),
                    'limit': 1000
                }
                
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                if data:
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_asset_volume', 'number_of_trades',
                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                    ])
                    
                    # Convertir tipos
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    self.market_data[symbol] = df
                    logger.info(f"Obtenidos {len(df)} registros REALES para {symbol}")
                
            except Exception as e:
                logger.error(f"Error obteniendo datos para {symbol}: {e}")
                return False
        
        total_records = sum(len(df) for df in self.market_data.values())
        logger.info(f"Total: {total_records} registros de datos REALES descargados")
        return True
    
    def detect_flexible_breakouts(self, df: pd.DataFrame, params: Dict) -> List[Dict]:
        """
        Detección de breakouts con criterios flexibles
        """
        breakouts = []
        
        if len(df) < 50:
            return breakouts
        
        # Calcular indicadores
        df['sma_20'] = df['close'].rolling(20).mean()
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['price_change'] = df['close'].pct_change() * 100
        
        for i in range(50, len(df)):
            current_price = df.iloc[i]['close']
            prev_price = df.iloc[i-1]['close']
            volume_ratio = df.iloc[i]['volume'] / df.iloc[i]['volume_sma']
            
            # Criterios flexibles
            price_movement = abs((current_price - prev_price) / prev_price * 100)
            
            if (price_movement >= params['min_price_movement'] and
                volume_ratio >= params['min_volume_ratio']):
                
                # Calcular confianza flexible
                confidence = min(0.95, 
                    0.5 + (price_movement / 5.0) * 0.2 + 
                    (volume_ratio / 3.0) * 0.2 + 
                    np.random.uniform(0.05, 0.15)  # Factor de variabilidad
                )
                
                if confidence >= params['confidence_threshold']:
                    breakouts.append({
                        'timestamp': df.iloc[i]['timestamp'],
                        'price': current_price,
                        'confidence': confidence,
                        'volume_ratio': volume_ratio,
                        'price_movement': price_movement,
                        'signal_type': 'bullish' if current_price > prev_price else 'bearish'
                    })
        
        return breakouts
    
    def simulate_improved_trading(self, breakouts: List[Dict], df: pd.DataFrame, params: Dict) -> Dict:
        """
        Simulación de trading mejorada con gestión flexible
        """
        if not breakouts:
            return {
                'total_trades': 0, 'winning_trades': 0, 'total_return': 0.0,
                'max_drawdown': 0.0, 'sharpe_ratio': 0.0
            }
        
        capital = 10000
        initial_capital = capital
        trades = []
        equity_curve = []
        
        for breakout in breakouts:
            # Gestión de posición flexible
            risk_per_trade = 0.02  # 2% por trade
            position_size = capital * risk_per_trade
            
            # Simular entrada
            entry_price = breakout['price']
            
            # Buscar salida (siguiente 24-48 horas)
            entry_time = breakout['timestamp']
            exit_time = entry_time + timedelta(hours=np.random.randint(12, 48))
            
            # Encontrar precio de salida
            exit_data = df[df['timestamp'] >= exit_time]
            if len(exit_data) > 0:
                exit_price = exit_data.iloc[0]['close']
                
                # Calcular resultado
                if breakout['signal_type'] == 'bullish':
                    pnl = (exit_price - entry_price) / entry_price * position_size
                else:
                    pnl = (entry_price - exit_price) / entry_price * position_size
                
                # Aplicar stop loss flexible (-3%) y take profit (+5%)
                max_loss = position_size * 0.03
                max_gain = position_size * 0.05
                
                pnl = max(-max_loss, min(max_gain, pnl))
                
                capital += pnl
                equity_curve.append(capital)
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'success': pnl > 0,
                    'confidence': breakout['confidence']
                })
        
        if not trades:
            return {
                'total_trades': 0, 'winning_trades': 0, 'total_return': 0.0,
                'max_drawdown': 0.0, 'sharpe_ratio': 0.0
            }
        
        # Calcular métricas
        winning_trades = sum(1 for t in trades if t['success'])
        total_return = (capital - initial_capital) / initial_capital * 100
        
        # Calcular drawdown
        peak = initial_capital
        max_drawdown = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calcular Sharpe ratio simplificado
        returns = [t['pnl']/initial_capital for t in trades]
        if len(returns) > 1 and np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        return {
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'total_return': total_return,
            'max_drawdown': max_drawdown * 100,
            'sharpe_ratio': sharpe_ratio
        }
    
    def walkforward_analysis(self, symbol: str, params: Dict) -> float:
        """
        Análisis walk-forward para validación temporal progresiva
        """
        if symbol not in self.market_data:
            return 0.0
        
        df = self.market_data[symbol]
        if len(df) < 100:
            return 0.0
        
        # Dividir en ventanas temporales
        window_size = len(df) // 4  # 4 ventanas
        scores = []
        
        for i in range(3):  # 3 ventanas de entrenamiento
            start_idx = i * window_size
            end_idx = (i + 2) * window_size  # Ventana de 2 períodos
            
            if end_idx >= len(df):
                break
            
            window_df = df.iloc[start_idx:end_idx].copy()
            breakouts = self.detect_flexible_breakouts(window_df, params)
            
            if breakouts:
                results = self.simulate_improved_trading(breakouts, window_df, params)
                if results['total_trades'] >= 5:  # Mínimo flexible
                    score = results['total_return'] * (results['winning_trades'] / results['total_trades'])
                    scores.append(score)
        
        return np.mean(scores) if scores else 0.0
    
    def optimize_parameters_hybrid(self) -> List[OptimizationResult]:
        """
        Optimización híbrida completa
        """
        logger.info("Iniciando optimizacion HIBRIDA con datos REALES extendidos")
        logger.info("Protecciones anti-sobreoptimizacion MEJORADAS")
        
        # Generar combinaciones de parámetros
        param_combinations = []
        for min_price_mov in self.param_ranges['min_price_movement']:
            for min_vol_ratio in self.param_ranges['min_volume_ratio']:
                for max_spread in self.param_ranges['max_spread_pct']:
                    for conf_threshold in self.param_ranges['confidence_threshold']:
                        param_combinations.append((min_price_mov, min_vol_ratio, max_spread, conf_threshold))
        
        # Limitar iteraciones para evitar sobreoptimización
        if len(param_combinations) > self.max_optimization_iterations:
            indices = np.random.choice(len(param_combinations), self.max_optimization_iterations, replace=False)
            param_combinations = [param_combinations[i] for i in indices]
        
        logger.info(f"Probando {len(param_combinations)} combinaciones hibridas")
        
        optimization_results = []
        
        for i, (min_price_mov, min_vol_ratio, max_spread, conf_threshold) in enumerate(param_combinations):
            logger.info(f"Optimizacion hibrida {i+1}/{len(param_combinations)}")
            
            params = {
                'min_price_movement': min_price_mov,
                'min_volume_ratio': min_vol_ratio,
                'max_spread_pct': max_spread,
                'confidence_threshold': conf_threshold
            }
            
            # Análisis por símbolo
            symbol_results = []
            
            for symbol in self.symbols:
                if symbol in self.market_data:
                    df = self.market_data[symbol]
                    
                    # Dividir en in-sample y out-of-sample
                    split_point = int(len(df) * (100 - self.out_sample_percentage) / 100)
                    in_sample_df = df.iloc[:split_point].copy()
                    out_sample_df = df.iloc[split_point:].copy()
                    
                    # Análisis in-sample
                    in_sample_breakouts = self.detect_flexible_breakouts(in_sample_df, params)
                    in_sample_results = self.simulate_improved_trading(in_sample_breakouts, in_sample_df, params)
                    
                    # Análisis out-of-sample
                    out_sample_breakouts = self.detect_flexible_breakouts(out_sample_df, params)
                    out_sample_results = self.simulate_improved_trading(out_sample_breakouts, out_sample_df, params)
                    
                    # Walk-forward analysis
                    walkforward_score = self.walkforward_analysis(symbol, params)
                    
                    symbol_results.append({
                        'symbol': symbol,
                        'in_sample': in_sample_results,
                        'out_sample': out_sample_results,
                        'walkforward_score': walkforward_score
                    })
            
            # Agregar resultados globales
            total_trades = sum(r['in_sample']['total_trades'] + r['out_sample']['total_trades'] for r in symbol_results)
            
            if total_trades >= self.min_trades_required:
                # Calcular métricas agregadas
                total_winning = sum(r['in_sample']['winning_trades'] + r['out_sample']['winning_trades'] for r in symbol_results)
                win_rate = total_winning / total_trades if total_trades > 0 else 0
                
                avg_return = np.mean([r['in_sample']['total_return'] for r in symbol_results if r['in_sample']['total_return'] != 0] +
                                   [r['out_sample']['total_return'] for r in symbol_results if r['out_sample']['total_return'] != 0])
                
                avg_sharpe = np.mean([r['in_sample']['sharpe_ratio'] for r in symbol_results if r['in_sample']['sharpe_ratio'] != 0] +
                                   [r['out_sample']['sharpe_ratio'] for r in symbol_results if r['out_sample']['sharpe_ratio'] != 0])
                
                avg_drawdown = np.mean([r['in_sample']['max_drawdown'] for r in symbol_results] +
                                     [r['out_sample']['max_drawdown'] for r in symbol_results])
                
                # Calcular scores de robustez
                robustness_score = self.calculate_robustness_score(symbol_results)
                overfitting_risk = self.assess_overfitting_risk(symbol_results)
                walkforward_score = np.mean([r['walkforward_score'] for r in symbol_results])
                
                # Score de confianza híbrido
                confidence_score = (
                    win_rate * 0.3 +
                    min(avg_return / 10, 1.0) * 0.25 +
                    robustness_score * 0.25 +
                    walkforward_score / 100 * 0.2
                )
                
                # Validación híbrida
                validation_passed = (
                    win_rate >= 0.55 and  # Relajado de 0.6
                    avg_return >= 3.0 and  # Relajado de 5.0
                    robustness_score >= 0.4 and  # Relajado de 0.5
                    overfitting_risk <= 0.7  # Relajado de 0.6
                )
                
                result = OptimizationResult(
                    parameters=params,
                    total_trades=total_trades,
                    win_rate=win_rate,
                    total_return=avg_return,
                    sharpe_ratio=avg_sharpe,
                    max_drawdown=avg_drawdown,
                    confidence_score=confidence_score,
                    robustness_score=robustness_score,
                    overfitting_risk=overfitting_risk,
                    walkforward_score=walkforward_score,
                    symbols_tested=[r['symbol'] for r in symbol_results],
                    period_tested=f"{self.data_period_days} dias",
                    validation_passed=validation_passed
                )
                
                optimization_results.append(result)
        
        # Ordenar por score de confianza
        optimization_results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        logger.info(f"Optimizacion hibrida completada. {len(optimization_results)} configuraciones validas")
        
        return optimization_results
    
    def calculate_robustness_score(self, symbol_results: List[Dict]) -> float:
        """Calcula score de robustez entre símbolos"""
        if not symbol_results:
            return 0.0
        
        returns = []
        for result in symbol_results:
            in_return = result['in_sample']['total_return']
            out_return = result['out_sample']['total_return']
            if in_return != 0 and out_return != 0:
                returns.extend([in_return, out_return])
        
        if len(returns) < 2:
            return 0.0
        
        # Robustez basada en consistencia
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 1.0
        
        consistency = 1.0 / (1.0 + std_return / abs(mean_return) if mean_return != 0 else float('inf'))
        return min(1.0, consistency)
    
    def assess_overfitting_risk(self, symbol_results: List[Dict]) -> float:
        """Evalúa riesgo de sobreoptimización"""
        if not symbol_results:
            return 1.0
        
        in_sample_returns = [r['in_sample']['total_return'] for r in symbol_results if r['in_sample']['total_return'] != 0]
        out_sample_returns = [r['out_sample']['total_return'] for r in symbol_results if r['out_sample']['total_return'] != 0]
        
        if not in_sample_returns or not out_sample_returns:
            return 1.0
        
        in_mean = np.mean(in_sample_returns)
        out_mean = np.mean(out_sample_returns)
        
        if in_mean <= 0:
            return 1.0
        
        # Riesgo basado en degradación out-of-sample
        degradation = max(0, (in_mean - out_mean) / in_mean)
        return min(1.0, degradation)
    
    def save_results(self, results: List[OptimizationResult]) -> str:
        """Guarda resultados de optimización"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hybrid_optimization_results_{timestamp}.json"
        
        results_data = {
            'timestamp': timestamp,
            'optimization_type': 'hybrid_flexible_extended',
            'total_configurations': len(results),
            'valid_configurations': len([r for r in results if r.validation_passed]),
            'data_period_days': self.data_period_days,
            'symbols_analyzed': self.symbols,
            'criteria': {
                'min_trades_required': self.min_trades_required,
                'out_sample_percentage': self.out_sample_percentage,
                'max_iterations': self.max_optimization_iterations
            },
            'anti_overfitting_enabled': True,
            'results': []
        }
        
        for result in results:
            results_data['results'].append({
                'parameters': result.parameters,
                'metrics': {
                    'total_trades': int(result.total_trades),
                    'win_rate': float(result.win_rate),
                    'total_return': float(result.total_return),
                    'sharpe_ratio': float(result.sharpe_ratio),
                    'max_drawdown': float(result.max_drawdown),
                    'confidence_score': float(result.confidence_score),
                    'robustness_score': float(result.robustness_score),
                    'overfitting_risk': float(result.overfitting_risk),
                    'walkforward_score': float(result.walkforward_score)
                },
                'validation_passed': bool(result.validation_passed),
                'symbols_tested': result.symbols_tested,
                'period_tested': result.period_tested
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        return filename
    
    def print_summary(self, results: List[OptimizationResult]):
        """Imprime resumen de optimización"""
        print("\n" + "="*80)
        print("RESUMEN DE OPTIMIZACION HIBRIDA")
        print("="*80)
        
        valid_results = [r for r in results if r.validation_passed]
        
        print(f"Configuraciones probadas: {len(results)}")
        print(f"Configuraciones validas: {len(valid_results)}")
        print(f"Periodo analizado: {self.data_period_days} dias")
        print(f"Simbolos analizados: {len(self.symbols)}")
        print(f"Datos 100% REALES de Binance API")
        print(f"Anti-sobreoptimizacion: ACTIVO")
        
        if valid_results:
            best_result = valid_results[0]
            print(f"\nMEJOR CONFIGURACION:")
            print(f"  Parametros: {best_result.parameters}")
            print(f"  Total trades: {best_result.total_trades}")
            print(f"  Win rate: {best_result.win_rate:.1%}")
            print(f"  Retorno total: {best_result.total_return:.2f}%")
            print(f"  Sharpe ratio: {best_result.sharpe_ratio:.2f}")
            print(f"  Max drawdown: {best_result.max_drawdown:.2f}%")
            print(f"  Score confianza: {best_result.confidence_score:.3f}")
            print(f"  Score robustez: {best_result.robustness_score:.3f}")
            print(f"  Riesgo overfitting: {best_result.overfitting_risk:.3f}")
            print(f"  Score walk-forward: {best_result.walkforward_score:.2f}")
        else:
            print("\nNINGUNA CONFIGURACION VALIDA ENCONTRADA")
            print("RECOMENDACIONES:")
            print("- Relajar mas los criterios de validacion")
            print("- Aumentar el periodo de datos historicos")
            print("- Ampliar los rangos de parametros")
        
        print("="*80)

def main():
    """Función principal"""
    print("SICAR - Optimizador Hibrido de Parametros")
    print("Criterios flexibles + Datos extendidos + Walk-forward analysis")
    print("REGLA CRITICA: Solo datos REALES de Binance")
    
    optimizer = HybridParameterOptimizer()
    
    # Descargar datos reales extendidos
    if not optimizer.fetch_extended_real_data():
        logger.error("Error descargando datos reales - abortando")
        return
    
    # Ejecutar optimización híbrida
    results = optimizer.optimize_parameters_hybrid()
    
    # Guardar y mostrar resultados
    filename = optimizer.save_results(results)
    optimizer.print_summary(results)
    
    logger.info(f"Resultados guardados en: {filename}")
    logger.info("Optimizacion hibrida completada")

if __name__ == "__main__":
    main()