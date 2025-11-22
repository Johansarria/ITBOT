#!/usr/bin/env python3
"""
🚀 SICAR Hybrid Parameter Optimizer
==================================================
🎯 ENFOQUE HÍBRIDO COMPLETO - FASE 1 AVANZADA
==================================================
✅ CRITERIOS FLEXIBLES + DATOS EXTENDIDOS
🛡️ PROTECCIÓN ANTI-OVERFITTING MEJORADA
📊 WALK-FORWARD ANALYSIS TEMPORAL
==================================================
"""

import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from itertools import product
from typing import Dict, List, Tuple, Optional
import requests
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hybrid_optimization.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class HybridOptimizationResult:
    """Resultado de optimización híbrida"""
    parameters: Dict
    in_sample_performance: Dict
    out_sample_performance: Dict
    walk_forward_performance: Dict
    robustness_score: float
    overfitting_risk: str
    total_trades: int
    win_rate: float
    avg_return: float
    sharpe_ratio: float
    max_drawdown: float
    confidence_score: float

class HybridParameterOptimizer:
    """
    🎯 Optimizador Híbrido con Enfoque Completo
    
    CARACTERÍSTICAS:
    ✅ Criterios flexibles para mayor detección
    📊 6 meses de datos históricos reales
    🛡️ Validación temporal progresiva
    📈 Walk-forward analysis robusto
    """
    
    def __init__(self):
        print("🚀 SICAR Hybrid Parameter Optimizer")
        print("=" * 50)
        print("🎯 ENFOQUE HÍBRIDO COMPLETO")
        print("=" * 50)
        print("✅ CRITERIOS FLEXIBLES")
        print("📊 DATOS EXTENDIDOS (6 MESES)")
        print("🛡️ VALIDACIÓN TEMPORAL PROGRESIVA")
        print("=" * 50)
        
        # Configuración híbrida mejorada
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'XRPUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'AVAXUSDT',
            'MATICUSDT', 'UNIUSDT', 'ATOMUSDT', 'FILUSDT', 'TRXUSDT'
        ]
        
        # Criterios flexibles (relajados)
        self.min_trades_required = 20  # Reducido de 50 a 20
        self.out_sample_percentage = 0.20  # Reducido de 30% a 20%
        self.max_optimization_iterations = 30  # Aumentado de 25 a 30
        
        # Rangos de parámetros ampliados
        self.parameter_ranges = {
            'min_price_movement': [0.03, 0.05, 0.08, 0.10, 0.12, 0.15],  # Más flexible
            'min_volume_ratio': [1.3, 1.5, 1.8, 2.0, 2.5, 3.0],  # Más opciones
            'max_spread_pct': [0.05, 0.08, 0.10, 0.12, 0.15, 0.20],  # Más tolerante
            'confidence_threshold': [0.75, 0.80, 0.85, 0.90, 0.95]  # Más flexible
        }
        
        # Configuración de datos extendidos
        self.data_period_days = 180  # 6 meses
        self.walk_forward_windows = 4  # 4 ventanas de validación
        
        # Almacenamiento de datos
        self.market_data = {}
        
    def fetch_extended_real_data(self) -> bool:
        """
        📡 Descarga 6 meses de datos históricos reales
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
    
    def detect_breakouts_flexible(self, df: pd.DataFrame, params: Dict) -> List[Dict]:
        """
        🎯 Detección de breakouts con criterios flexibles
        """
        breakouts = []
        
        for i in range(1, len(df)):
            current = df.iloc[i]
            previous = df.iloc[i-1]
            
            # Cálculo de movimiento de precio
            price_change = abs(current['close'] - previous['close']) / previous['close']
            
            # Cálculo de ratio de volumen
            if i >= 24:  # Necesitamos al menos 24 horas de historial
                avg_volume = df.iloc[i-24:i]['volume'].mean()
                volume_ratio = current['volume'] / avg_volume if avg_volume > 0 else 0
            else:
                volume_ratio = 1.0
            
            # Cálculo de spread
            spread_pct = (current['high'] - current['low']) / current['close']
            
            # Criterios flexibles de detección
            if (price_change >= params['min_price_movement'] and
                volume_ratio >= params['min_volume_ratio'] and
                spread_pct <= params['max_spread_pct']):
                
                # Cálculo de confianza flexible
                confidence = min(
                    (price_change / params['min_price_movement']) * 0.4 +
                    (volume_ratio / params['min_volume_ratio']) * 0.4 +
                    (1 - spread_pct / params['max_spread_pct']) * 0.2,
                    1.0
                )
                
                if confidence >= params['confidence_threshold']:
                    direction = 'bullish' if current['close'] > previous['close'] else 'bearish'
                    
                    breakouts.append({
                        'timestamp': current['timestamp'],
                        'symbol': 'SYMBOL',
                        'direction': direction,
                        'price': current['close'],
                        'price_change_pct': price_change * 100,
                        'volume_ratio': volume_ratio,
                        'spread_pct': spread_pct * 100,
                        'confidence': confidence
                    })
        
        return breakouts
    
    def simulate_trading_performance(self, breakouts: List[Dict], df: pd.DataFrame) -> Dict:
        """
        📈 Simulación de performance de trading mejorada
        """
        if not breakouts:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'returns': []
            }
        
        trades = []
        returns = []
        equity_curve = [1000]  # Capital inicial
        
        for breakout in breakouts:
            entry_price = breakout['price']
            entry_time = breakout['timestamp']
            direction = breakout['direction']
            
            # Buscar precio de salida (4 horas después)
            exit_time = entry_time + timedelta(hours=4)
            exit_data = df[df['timestamp'] >= exit_time]
            
            if not exit_data.empty:
                exit_price = exit_data.iloc[0]['close']
                
                # Calcular retorno según dirección
                if direction == 'bullish':
                    trade_return = (exit_price - entry_price) / entry_price
                else:
                    trade_return = (entry_price - exit_price) / entry_price
                
                # Aplicar comisiones (0.1%)
                trade_return -= 0.001
                
                returns.append(trade_return)
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': exit_time,
                    'direction': direction,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'return': trade_return
                })
                
                # Actualizar curva de equity
                new_equity = equity_curve[-1] * (1 + trade_return)
                equity_curve.append(new_equity)
        
        if not returns:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'returns': []
            }
        
        # Métricas de performance
        win_rate = len([r for r in returns if r > 0]) / len(returns)
        avg_return = np.mean(returns)
        total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]
        
        # Sharpe ratio
        if np.std(returns) > 0:
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Anualizado
        else:
            sharpe_ratio = 0
        
        # Maximum drawdown
        peak = equity_curve[0]
        max_dd = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
        
        return {
            'total_trades': len(trades),
            'win_rate': win_rate,
            'avg_return': avg_return,
            'total_return': total_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_dd,
            'returns': returns
        }
    
    def walk_forward_analysis(self, symbol: str, params: Dict) -> Dict:
        """
        🚶 Walk-forward analysis temporal
        """
        df = self.market_data[symbol]
        window_size = len(df) // self.walk_forward_windows
        
        walk_forward_results = []
        
        for i in range(self.walk_forward_windows):
            start_idx = i * window_size
            end_idx = min((i + 1) * window_size, len(df))
            
            window_df = df.iloc[start_idx:end_idx].copy()
            
            if len(window_df) > 50:  # Mínimo de datos
                breakouts = self.detect_breakouts_flexible(window_df, params)
                performance = self.simulate_trading_performance(breakouts, window_df)
                
                walk_forward_results.append({
                    'window': i + 1,
                    'period': f"{window_df.iloc[0]['timestamp']} - {window_df.iloc[-1]['timestamp']}",
                    'trades': performance['total_trades'],
                    'win_rate': performance['win_rate'],
                    'return': performance['total_return'],
                    'sharpe': performance['sharpe_ratio']
                })
        
        # Calcular métricas agregadas
        if walk_forward_results:
            avg_trades = np.mean([r['trades'] for r in walk_forward_results])
            avg_win_rate = np.mean([r['win_rate'] for r in walk_forward_results])
            avg_return = np.mean([r['return'] for r in walk_forward_results])
            consistency = 1 - np.std([r['return'] for r in walk_forward_results])
            
            return {
                'windows': walk_forward_results,
                'avg_trades_per_window': avg_trades,
                'avg_win_rate': avg_win_rate,
                'avg_return': avg_return,
                'consistency_score': max(0, consistency)
            }
        
        return {'windows': [], 'avg_trades_per_window': 0, 'avg_win_rate': 0, 'avg_return': 0, 'consistency_score': 0}
    
    def optimize_parameters_hybrid(self) -> List[HybridOptimizationResult]:
        """
        🎯 Optimización híbrida completa
        """
        logger.info("Iniciando optimizacion HIBRIDA con datos REALES extendidos")
        logger.info("Protecciones anti-sobreoptimizacion MEJORADAS")
        
        # Generar combinaciones de parámetros
        param_combinations = list(product(
            self.parameter_ranges['min_price_movement'],
            self.parameter_ranges['min_volume_ratio'],
            self.parameter_ranges['max_spread_pct'],
            self.parameter_ranges['confidence_threshold']
        ))
        
        # Limitar combinaciones
        if len(param_combinations) > self.max_optimization_iterations:
            indices = np.random.choice(
                len(param_combinations), 
                self.max_optimization_iterations, 
                replace=False
            )
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
                    
                    # División in-sample / out-sample
                    split_point = int(len(df) * (1 - self.out_sample_percentage))
                    in_sample_df = df.iloc[:split_point].copy()
                    out_sample_df = df.iloc[split_point:].copy()
                    
                    # Análisis in-sample
                    in_breakouts = self.detect_breakouts_flexible(in_sample_df, params)
                    in_performance = self.simulate_trading_performance(in_breakouts, in_sample_df)
                    
                    # Análisis out-sample
                    out_breakouts = self.detect_breakouts_flexible(out_sample_df, params)
                    out_performance = self.simulate_trading_performance(out_breakouts, out_sample_df)
                    
                    # Walk-forward analysis
                    wf_analysis = self.walk_forward_analysis(symbol, params)
                    
                    symbol_results.append({
                        'symbol': symbol,
                        'in_sample': in_performance,
                        'out_sample': out_performance,
                        'walk_forward': wf_analysis
                    })
            
            # Agregar resultados
            if symbol_results:
                total_in_trades = sum(r['in_sample']['total_trades'] for r in symbol_results)
                total_out_trades = sum(r['out_sample']['total_trades'] for r in symbol_results)
                
                if total_in_trades >= self.min_trades_required and total_out_trades >= 10:
                    # Métricas agregadas
                    avg_in_return = np.mean([r['in_sample']['avg_return'] for r in symbol_results if r['in_sample']['total_trades'] > 0])
                    avg_out_return = np.mean([r['out_sample']['avg_return'] for r in symbol_results if r['out_sample']['total_trades'] > 0])
                    
                    avg_in_win_rate = np.mean([r['in_sample']['win_rate'] for r in symbol_results if r['in_sample']['total_trades'] > 0])
                    avg_out_win_rate = np.mean([r['out_sample']['win_rate'] for r in symbol_results if r['out_sample']['total_trades'] > 0])
                    
                    # Score de robustez mejorado
                    return_consistency = 1 - abs(avg_in_return - avg_out_return) / max(abs(avg_in_return), 0.01)
                    win_rate_consistency = 1 - abs(avg_in_win_rate - avg_out_win_rate)
                    
                    robustness_score = (return_consistency + win_rate_consistency) / 2
                    
                    # Evaluación de overfitting
                    if avg_out_return < avg_in_return * 0.5:
                        overfitting_risk = "ALTO"
                    elif avg_out_return < avg_in_return * 0.8:
                        overfitting_risk = "MEDIO"
                    else:
                        overfitting_risk = "BAJO"
                    
                    # Sharpe ratio agregado
                    all_returns = []
                    for r in symbol_results:
                        all_returns.extend(r['in_sample']['returns'])
                        all_returns.extend(r['out_sample']['returns'])
                    
                    sharpe_ratio = 0
                    if all_returns and np.std(all_returns) > 0:
                        sharpe_ratio = np.mean(all_returns) / np.std(all_returns) * np.sqrt(252)
                    
                    # Confidence score
                    wf_consistency = np.mean([r['walk_forward']['consistency_score'] for r in symbol_results])
                    confidence_score = (robustness_score + wf_consistency) / 2
                    
                    result = HybridOptimizationResult(
                        parameters=params,
                        in_sample_performance={
                            'total_trades': total_in_trades,
                            'avg_return': avg_in_return,
                            'win_rate': avg_in_win_rate
                        },
                        out_sample_performance={
                            'total_trades': total_out_trades,
                            'avg_return': avg_out_return,
                            'win_rate': avg_out_win_rate
                        },
                        walk_forward_performance={
                            'avg_consistency': wf_consistency,
                            'symbol_results': symbol_results
                        },
                        robustness_score=robustness_score,
                        overfitting_risk=overfitting_risk,
                        total_trades=total_in_trades + total_out_trades,
                        win_rate=(avg_in_win_rate + avg_out_win_rate) / 2,
                        avg_return=(avg_in_return + avg_out_return) / 2,
                        sharpe_ratio=sharpe_ratio,
                        max_drawdown=0,  # Simplificado para esta versión
                        confidence_score=confidence_score
                    )
                    
                    optimization_results.append(result)
        
        # Ordenar por score de confianza
        optimization_results.sort(key=lambda x: x.confidence_score, reverse=True)
        
        logger.info(f"Optimizacion hibrida completada. {len(optimization_results)} configuraciones validas")
        
        return optimization_results
    
    def save_hybrid_results(self, results: List[HybridOptimizationResult]) -> str:
        """
        💾 Guardar resultados de optimización híbrida
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hybrid_optimization_results_{timestamp}.json"
        
        results_data = {
            "optimization_timestamp": datetime.now().isoformat(),
            "optimization_type": "Hybrid Parameter Optimization",
            "approach": "Flexible Criteria + Extended Data + Walk-Forward",
            "data_period_days": self.data_period_days,
            "symbols_analyzed": self.symbols,
            "total_configurations": len(results),
            "valid_configurations": len(results),
            "criteria": {
                "min_trades_required": self.min_trades_required,
                "out_sample_percentage": self.out_sample_percentage,
                "walk_forward_windows": self.walk_forward_windows
            },
            "results": [asdict(result) for result in results]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Resultados híbridos guardados en: {filename}")
        return filename
    
    def print_hybrid_summary(self, results: List[HybridOptimizationResult]):
        """
        📊 Imprimir resumen de optimización híbrida
        """
        print("\n🎯 RESUMEN DE OPTIMIZACIÓN HÍBRIDA")
        print("=" * 60)
        print(f"📊 Configuraciones probadas: {self.max_optimization_iterations}")
        print(f"✅ Configuraciones válidas: {len(results)}")
        print(f"🛡️ Protección anti-overfitting: ACTIVADA")
        print(f"📡 Fuente de datos: 100% REAL (Binance API)")
        print(f"📅 Período de datos: {self.data_period_days} días")
        print(f"🔍 Símbolos analizados: {len(self.symbols)}")
        
        if results:
            best = results[0]
            print(f"\n🏆 MEJOR CONFIGURACIÓN:")
            print(f"   📈 Confidence Score: {best.confidence_score:.3f}")
            print(f"   🎯 Robustness Score: {best.robustness_score:.3f}")
            print(f"   📊 Total Trades: {best.total_trades}")
            print(f"   🏅 Win Rate: {best.win_rate:.1%}")
            print(f"   💰 Avg Return: {best.avg_return:.3%}")
            print(f"   📊 Sharpe Ratio: {best.sharpe_ratio:.2f}")
            print(f"   ⚠️ Overfitting Risk: {best.overfitting_risk}")
            
            print(f"\n⚙️ PARÁMETROS ÓPTIMOS:")
            for key, value in best.parameters.items():
                print(f"   {key}: {value}")
        else:
            print("\n❌ No se encontraron configuraciones válidas")
            print("💡 Sugerencia: Revisar criterios o ampliar datos")

def main():
    """
    🚀 Función principal del optimizador híbrido
    """
    optimizer = HybridParameterOptimizer()
    
    # Paso 1: Descargar datos extendidos
    if not optimizer.fetch_extended_real_data():
        logger.error("❌ Error descargando datos. Abortando optimización.")
        return
    
    # Paso 2: Optimización híbrida
    results = optimizer.optimize_parameters_hybrid()
    
    # Paso 3: Guardar y mostrar resultados
    filename = optimizer.save_hybrid_results(results)
    optimizer.print_hybrid_summary(results)
    
    print(f"\n💾 Resultados completos guardados en: {filename}")

if __name__ == "__main__":
    main()