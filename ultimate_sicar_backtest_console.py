#!/usr/bin/env python3
"""
ULTIMATE SICAR SYSTEM - BACKTESTING COMPLETO CON DATOS REALES
============================================================

Este script realiza un backtesting exhaustivo del Ultimate SICAR System
utilizando datos reales de 2020-2025 y muestra todo el proceso por consola.

Características:
- Backtesting de NAS100 con la estrategia Ultimate SICAR
- Análisis de múltiples índices para identificar top 5 más rentables
- Validación estadística completa
- Reporte detallado con métricas avanzadas
"""

import asyncio
import sys
import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Agregar el directorio src al path para importar módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

class UltimateSicarBacktester:
    """Backtester completo para el Ultimate SICAR System"""
    
    def __init__(self):
        self.console_log("🚀 INICIANDO ULTIMATE SICAR SYSTEM BACKTESTER")
        self.console_log("=" * 60)
        
        # Configuración de índices principales para análisis
        self.indices = {
            'NAS100': '^NDX',      # NASDAQ 100 (Principal objetivo)
            'SP500': '^GSPC',      # S&P 500 Index
            'NASDAQ': '^IXIC',     # NASDAQ Composite
            'DOW': '^DJI',         # Dow Jones Industrial Average
            'RUSSELL2000': '^RUT', # Russell 2000
            'VIX': '^VIX',         # Volatility Index
            'GOLD': 'GC=F',        # Gold Futures
            'CRUDE': 'CL=F',       # Crude Oil Futures
            'BITCOIN': 'BTC-USD',  # Bitcoin
            'ETHEREUM': 'ETH-USD'  # Ethereum
        }
        
        # Parámetros del Ultimate SICAR System
        self.sicar_params = {
            'capital_inicial': 500,
            'apalancamiento_max': 15,
            'stop_loss': 0.03,  # 3%
            'take_profit_levels': [0.05, 0.10, 0.15, 0.20],  # 5%, 10%, 15%, 20%
            'position_size_pct': 0.50,  # 50% del capital con apalancamiento
            'comision': 0.001,  # 0.1%
            'timeframes': ['15m', '1h', '4h', '1d'],
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2
        }
        
        self.results = {}
        self.data_cache = {}
        
    def console_log(self, message, level="INFO"):
        """Log con timestamp para seguimiento por consola"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "PROGRESS": "🔄"
        }.get(level, "ℹ️")
        
        print(f"[{timestamp}] {prefix} {message}")
        
    def download_real_data(self, symbol, period="5y"):
        """Descarga datos reales de Yahoo Finance"""
        try:
            self.console_log(f"Descargando datos para {symbol}...", "PROGRESS")
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval="1d")
            
            if data.empty:
                self.console_log(f"No se pudieron obtener datos para {symbol}", "WARNING")
                # Intentar con período más corto
                self.console_log(f"Intentando con período de 2 años para {symbol}...", "PROGRESS")
                data = ticker.history(period="2y", interval="1d")
                
                if data.empty:
                    self.console_log(f"Falló descarga definitiva para {symbol}", "ERROR")
                    return None
                
            # Verificar que tenemos suficientes datos
            if len(data) < 100:
                self.console_log(f"Datos insuficientes para {symbol}: {len(data)} días", "WARNING")
                return None
                
            # Calcular indicadores técnicos
            data = self.calculate_technical_indicators(data)
            
            self.console_log(f"✓ Datos descargados: {len(data)} días para {symbol}", "SUCCESS")
            self.console_log(f"  📅 Período: {data.index[0].date()} a {data.index[-1].date()}")
            return data
            
        except Exception as e:
            self.console_log(f"Error descargando {symbol}: {str(e)}", "ERROR")
            return None
    
    def calculate_technical_indicators(self, data):
        """Calcula todos los indicadores técnicos del Ultimate SICAR System"""
        df = data.copy()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.sicar_params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.sicar_params['rsi_period']).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=self.sicar_params['macd_fast']).mean()
        exp2 = df['Close'].ewm(span=self.sicar_params['macd_slow']).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=self.sicar_params['macd_signal']).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=self.sicar_params['bb_period']).mean()
        bb_std = df['Close'].rolling(window=self.sicar_params['bb_period']).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * self.sicar_params['bb_std'])
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * self.sicar_params['bb_std'])
        
        # ATR para volatilidad
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(window=14).mean()
        
        # Momentum indicators
        df['Price_Change'] = df['Close'].pct_change()
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        return df
    
    def generate_ultimate_sicar_signals(self, data):
        """Genera señales del Ultimate SICAR System"""
        df = data.copy()
        
        # Inicializar señales
        df['Signal'] = 0
        df['Signal_Strength'] = 0.0
        
        # Condiciones de compra (múltiples criterios)
        buy_conditions = (
            (df['RSI'] < 30) |  # RSI oversold
            ((df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))) |  # MACD crossover
            (df['Close'] <= df['BB_Lower']) |  # Precio en banda inferior
            ((df['Close'] > df['Close'].shift(1)) & (df['Volume_Ratio'] > 1.5))  # Breakout con volumen
        )
        
        # Condiciones de venta
        sell_conditions = (
            (df['RSI'] > 70) |  # RSI overbought
            ((df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1))) |  # MACD crossover down
            (df['Close'] >= df['BB_Upper']) |  # Precio en banda superior
            (df['Price_Change'] < -0.02)  # Caída fuerte
        )
        
        # Asignar señales
        df.loc[buy_conditions, 'Signal'] = 1
        df.loc[sell_conditions, 'Signal'] = -1
        
        # Calcular fuerza de la señal (0-1)
        rsi_strength = np.abs(df['RSI'] - 50) / 50
        macd_strength = np.abs(df['MACD_Histogram']) / df['ATR']
        bb_strength = np.where(df['Close'] < df['BB_Lower'], 
                              (df['BB_Lower'] - df['Close']) / (df['BB_Upper'] - df['BB_Lower']),
                              np.where(df['Close'] > df['BB_Upper'],
                                      (df['Close'] - df['BB_Upper']) / (df['BB_Upper'] - df['BB_Lower']),
                                      0))
        
        df['Signal_Strength'] = np.clip((rsi_strength + macd_strength + bb_strength) / 3, 0, 1)
        
        return df
    
    def backtest_strategy(self, data, symbol):
        """Ejecuta el backtesting de la estrategia Ultimate SICAR"""
        self.console_log(f"🔄 Ejecutando backtesting para {symbol}...", "PROGRESS")
        
        df = data.copy()
        
        # Variables de trading
        capital = self.sicar_params['capital_inicial']
        position = 0
        entry_price = 0
        trades = []
        equity_curve = [capital]
        
        for i in range(1, len(df)):
            current_price = df['Close'].iloc[i]
            signal = df['Signal'].iloc[i]
            signal_strength = df['Signal_Strength'].iloc[i]
            
            # Gestión de posiciones existentes
            if position != 0:
                # Calcular P&L actual
                if position > 0:  # Long position
                    pnl_pct = (current_price - entry_price) / entry_price
                else:  # Short position
                    pnl_pct = (entry_price - current_price) / entry_price
                
                # Stop Loss
                if abs(pnl_pct) >= self.sicar_params['stop_loss']:
                    # Cerrar posición por stop loss
                    trade_pnl = position * pnl_pct * self.sicar_params['apalancamiento_max']
                    capital += trade_pnl
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': df.index[i],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position_size': position,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': trade_pnl,
                        'exit_reason': 'Stop Loss'
                    })
                    
                    position = 0
                    entry_price = 0
                
                # Take Profit (escalonado)
                elif pnl_pct >= self.sicar_params['take_profit_levels'][0]:
                    # Cerrar posición por take profit
                    trade_pnl = position * pnl_pct * self.sicar_params['apalancamiento_max']
                    capital += trade_pnl
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': df.index[i],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position_size': position,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': trade_pnl,
                        'exit_reason': 'Take Profit'
                    })
                    
                    position = 0
                    entry_price = 0
            
            # Nuevas entradas
            if position == 0 and signal != 0 and signal_strength > 0.3:
                position_size = capital * self.sicar_params['position_size_pct']
                position = position_size * signal  # Positivo para long, negativo para short
                entry_price = current_price
                entry_date = df.index[i]
                
                # Aplicar comisión
                commission = abs(position) * self.sicar_params['comision']
                capital -= commission
            
            equity_curve.append(capital)
        
        # Cerrar posición final si existe
        if position != 0:
            current_price = df['Close'].iloc[-1]
            if position > 0:
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            trade_pnl = position * pnl_pct * self.sicar_params['apalancamiento_max']
            capital += trade_pnl
            
            trades.append({
                'entry_date': entry_date,
                'exit_date': df.index[-1],
                'entry_price': entry_price,
                'exit_price': current_price,
                'position_size': position,
                'pnl_pct': pnl_pct,
                'pnl_usd': trade_pnl,
                'exit_reason': 'Final Close'
            })
        
        return trades, equity_curve, capital
    
    def calculate_performance_metrics(self, trades, equity_curve, final_capital, symbol):
        """Calcula métricas de rendimiento detalladas"""
        if not trades:
            return {
                'symbol': symbol,
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0
            }
        
        trades_df = pd.DataFrame(trades)
        
        # Métricas básicas
        total_return = (final_capital - self.sicar_params['capital_inicial']) / self.sicar_params['capital_inicial']
        total_trades = len(trades)
        winning_trades = len(trades_df[trades_df['pnl_usd'] > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Retornos promedio
        avg_return = trades_df['pnl_pct'].mean() if total_trades > 0 else 0
        
        # Sharpe Ratio (simplificado)
        returns = trades_df['pnl_pct'].values
        sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        # Maximum Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        
        # Profit Factor
        gross_profit = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum()
        gross_loss = abs(trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'symbol': symbol,
            'total_return': total_return,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'final_capital': final_capital,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss
        }
    
    async def run_complete_analysis(self):
        """Ejecuta el análisis completo de todos los índices"""
        self.console_log("🎯 INICIANDO ANÁLISIS COMPLETO DE ÍNDICES", "INFO")
        self.console_log(f"📊 Analizando {len(self.indices)} índices principales")
        
        all_results = []
        
        for name, symbol in self.indices.items():
            self.console_log(f"\n{'='*50}")
            self.console_log(f"📈 ANALIZANDO: {name} ({symbol})")
            self.console_log(f"{'='*50}")
            
            # Descargar datos
            data = self.download_real_data(symbol)
            if data is None:
                continue
            
            # Generar señales
            self.console_log("🔍 Generando señales Ultimate SICAR...", "PROGRESS")
            data_with_signals = self.generate_ultimate_sicar_signals(data)
            
            # Ejecutar backtesting
            trades, equity_curve, final_capital = self.backtest_strategy(data_with_signals, name)
            
            # Calcular métricas
            metrics = self.calculate_performance_metrics(trades, equity_curve, final_capital, name)
            all_results.append(metrics)
            
            # Mostrar resultados por consola
            self.console_log(f"📊 RESULTADOS PARA {name}:")
            self.console_log(f"   💰 Retorno Total: {metrics['total_return']:.2%}")
            self.console_log(f"   📈 Capital Final: ${metrics['final_capital']:.2f}")
            self.console_log(f"   🎯 Total Trades: {metrics['total_trades']}")
            self.console_log(f"   ✅ Win Rate: {metrics['win_rate']:.2%}")
            self.console_log(f"   📊 Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
            self.console_log(f"   📉 Max Drawdown: {metrics['max_drawdown']:.2%}")
            self.console_log(f"   💎 Profit Factor: {metrics['profit_factor']:.2f}")
            
            # Guardar datos para análisis posterior
            self.data_cache[name] = {
                'data': data_with_signals,
                'trades': trades,
                'equity_curve': equity_curve,
                'metrics': metrics
            }
        
        # Ranking de mejores índices
        self.console_log(f"\n{'='*60}")
        self.console_log("🏆 RANKING DE MEJORES ÍNDICES")
        self.console_log(f"{'='*60}")
        
        # Ordenar por retorno total
        sorted_results = sorted(all_results, key=lambda x: x['total_return'], reverse=True)
        
        self.console_log("🥇 TOP 5 ÍNDICES MÁS RENTABLES:")
        for i, result in enumerate(sorted_results[:5], 1):
            self.console_log(f"{i}. {result['symbol']}: {result['total_return']:.2%} "
                           f"(${result['final_capital']:.2f}, {result['total_trades']} trades)")
        
        # Análisis especial de NAS100
        nas100_result = next((r for r in all_results if r['symbol'] == 'NAS100'), None)
        if nas100_result:
            self.console_log(f"\n🎯 ANÁLISIS ESPECIAL NAS100:")
            self.console_log(f"   Posición en ranking: {sorted_results.index(nas100_result) + 1}")
            self.console_log(f"   Retorno vs mejor índice: "
                           f"{nas100_result['total_return'] - sorted_results[0]['total_return']:.2%}")
        
        return sorted_results
    
    def generate_detailed_report(self, results):
        """Genera reporte detallado de resultados"""
        self.console_log(f"\n{'='*60}")
        self.console_log("📋 REPORTE DETALLADO ULTIMATE SICAR SYSTEM")
        self.console_log(f"{'='*60}")
        
        if not results:
            self.console_log("⚠️ No se obtuvieron resultados válidos para el análisis")
            return results
        
        # Estadísticas generales
        total_indices = len(results)
        profitable_indices = len([r for r in results if r['total_return'] > 0])
        avg_return = np.mean([r['total_return'] for r in results])
        avg_trades = np.mean([r['total_trades'] for r in results])
        avg_win_rate = np.mean([r['win_rate'] for r in results])
        
        self.console_log(f"📊 ESTADÍSTICAS GENERALES:")
        self.console_log(f"   Total índices analizados: {total_indices}")
        if total_indices > 0:
            self.console_log(f"   Índices rentables: {profitable_indices} ({profitable_indices/total_indices:.1%})")
        else:
            self.console_log(f"   Índices rentables: 0 (0.0%)")
        self.console_log(f"   Retorno promedio: {avg_return:.2%}")
        self.console_log(f"   Trades promedio: {avg_trades:.0f}")
        self.console_log(f"   Win rate promedio: {avg_win_rate:.2%}")
        
        # Top performers
        self.console_log(f"\n🏆 TOP PERFORMERS DETALLADO:")
        for i, result in enumerate(results[:5], 1):
            self.console_log(f"\n{i}. {result['symbol']}:")
            self.console_log(f"   💰 Retorno: {result['total_return']:.2%}")
            self.console_log(f"   💵 Capital final: ${result['final_capital']:.2f}")
            self.console_log(f"   📊 Trades: {result['total_trades']}")
            self.console_log(f"   ✅ Win rate: {result['win_rate']:.2%}")
            self.console_log(f"   📈 Sharpe: {result['sharpe_ratio']:.3f}")
            self.console_log(f"   📉 Max DD: {result['max_drawdown']:.2%}")
            self.console_log(f"   💎 Profit Factor: {result['profit_factor']:.2f}")
        
        # Recomendaciones
        self.console_log(f"\n💡 RECOMENDACIONES:")
        best_performer = results[0]
        self.console_log(f"   🥇 Mejor índice: {best_performer['symbol']} "
                       f"({best_performer['total_return']:.2%})")
        
        if best_performer['total_return'] > 0.15:  # 15% objetivo mensual
            self.console_log(f"   ✅ Objetivo de 15% ROI mensual: ALCANZADO")
        else:
            self.console_log(f"   ⚠️ Objetivo de 15% ROI mensual: NO ALCANZADO")
        
        # Análisis de riesgo
        high_risk_indices = [r for r in results if r['max_drawdown'] > 0.20]
        if high_risk_indices:
            self.console_log(f"   ⚠️ Índices de alto riesgo (DD > 20%): "
                           f"{[r['symbol'] for r in high_risk_indices]}")
        
        return results

async def main():
    """Función principal para ejecutar el backtesting completo"""
    print("🚀 ULTIMATE SICAR SYSTEM - BACKTESTING COMPLETO")
    print("=" * 60)
    print("📅 Período: 2020-2025 (Datos reales)")
    print("🎯 Objetivo: Identificar top 5 índices más rentables")
    print("📊 Enfoque especial: NAS100")
    print("=" * 60)
    
    # Crear instancia del backtester
    backtester = UltimateSicarBacktester()
    
    try:
        # Ejecutar análisis completo
        results = await backtester.run_complete_analysis()
        
        # Generar reporte final
        backtester.generate_detailed_report(results)
        
        # Conclusiones finales
        backtester.console_log(f"\n🎉 ANÁLISIS COMPLETADO EXITOSAMENTE", "SUCCESS")
        backtester.console_log(f"📊 {len(results)} índices analizados")
        backtester.console_log(f"🏆 Mejor performer: {results[0]['symbol']} "
                             f"({results[0]['total_return']:.2%})")
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Ejecutar el análisis completo
    asyncio.run(main())