#!/usr/bin/env python3
"""
Backtester con Datos Históricos Reales de Binance
Validación exhaustiva de la estrategia 15% mensual con datos reales
"""

import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
import json
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

from enhanced_strategy_15pct import Enhanced15PercentStrategy, TradingConfig

@dataclass
class HistoricalBacktestResult:
    """Resultado del backtest histórico"""
    symbol: str
    period: str
    start_date: str
    end_date: str
    total_return: float
    daily_return_avg: float
    monthly_return_avg: float
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    final_capital: float
    days_tested: int
    meets_daily_target: bool
    meets_monthly_target: bool
    raw_data_points: int

class BinanceDataFetcher:
    """Obtiene datos históricos reales de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.session = requests.Session()
    
    def get_historical_klines(self, symbol: str, interval: str, start_time: str, end_time: str) -> List[List]:
        """Obtiene datos históricos de Binance"""
        url = f"{self.base_url}/klines"
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(pd.Timestamp(start_time).timestamp() * 1000),
            'endTime': int(pd.Timestamp(end_time).timestamp() * 1000),
            'limit': 1000
        }
        
        all_klines = []
        
        while True:
            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()
                klines = response.json()
                
                if not klines:
                    break
                
                all_klines.extend(klines)
                
                # Actualizar start_time para la siguiente página
                last_timestamp = klines[-1][0]
                params['startTime'] = last_timestamp + 1
                
                # Evitar rate limiting
                time.sleep(0.1)
                
                print(f"Descargados {len(all_klines)} registros para {symbol}...")
                
            except Exception as e:
                print(f"Error obteniendo datos: {e}")
                break
        
        return all_klines
    
    def klines_to_dataframe(self, klines: List[List]) -> pd.DataFrame:
        """Convierte datos de klines a DataFrame"""
        columns = [
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ]
        
        df = pd.DataFrame(klines, columns=columns)
        
        # Convertir tipos de datos
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
        
        # Convertir timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df[['open', 'high', 'low', 'close', 'volume']]

class HistoricalBacktester:
    """Backtester con datos históricos reales"""
    
    def __init__(self):
        self.data_fetcher = BinanceDataFetcher()
        self.results = []
    
    def run_historical_backtest(self, symbol: str, start_date: str, end_date: str, 
                              interval: str = '1h') -> HistoricalBacktestResult:
        """Ejecuta backtest con datos históricos reales"""
        
        print(f"\n🔄 Iniciando backtest histórico para {symbol}")
        print(f"Período: {start_date} a {end_date}")
        print(f"Intervalo: {interval}")
        
        # Obtener datos históricos
        print("📥 Descargando datos de Binance...")
        klines = self.data_fetcher.get_historical_klines(symbol, interval, start_date, end_date)
        
        if not klines:
            print(f"❌ No se pudieron obtener datos para {symbol}")
            return None
        
        # Convertir a DataFrame
        df = self.data_fetcher.klines_to_dataframe(klines)
        print(f"✅ Datos obtenidos: {len(df)} registros")
        
        # Configurar estrategia
        config = TradingConfig(
            initial_capital=500.0,
            max_risk_per_trade=0.025,
            
            # Parámetros optimizados
            rsi_period=12,
            rsi_oversold=25,
            rsi_overbought=75,
            
            macd_fast=10,
            macd_slow=24,
            macd_signal=8,
            
            bb_period=18,
            bb_std=2.2,
            
            stop_loss=0.015,
            take_profit_1=0.035
        )
        
        # Parámetros adicionales para el backtest
        commission = 0.001
        slippage = 0.0005
        
        strategy = Enhanced15PercentStrategy(config)
        
        # Ejecutar backtest
        print("🚀 Ejecutando backtest...")
        capital = config.initial_capital
        trades = []
        daily_returns = []
        equity_curve = [capital]
        
        position = None
        entry_price = 0
        entry_time = None
        
        for i in range(len(df)):
            current_data = df.iloc[:i+1]
            
            if len(current_data) < 50:  # Necesitamos datos suficientes
                continue
            
            current_price = current_data['close'].iloc[-1]
            current_time = current_data.index[-1]
            
            # Calcular indicadores técnicos primero
            current_data_with_indicators = strategy.analyzer.calculate_technical_indicators(current_data)
            
            # Generar señal usando el analyzer
            signals_df = strategy.analyzer.generate_enhanced_signals(current_data_with_indicators)
            signal_value = signals_df.iloc[-1]['signal'] if len(signals_df) > 0 else 0
            signal_strength = abs(signals_df.iloc[-1]['signal_combined']) if len(signals_df) > 0 and 'signal_combined' in signals_df.columns else 0.5
            signal = 'BUY' if signal_value > 0 else ('SELL' if signal_value < 0 else 'HOLD')
            
            # Gestión de posiciones
            if position is None:
                # Buscar entrada
                if signal != 'HOLD':
                    signal_numeric = 1 if signal == 'BUY' else -1
                    entry_price = current_price * (1 + slippage if signal_numeric == 1 else 1 - slippage)
                    
                    # Calcular tamaño de posición
                    risk_amount = capital * config.max_risk_per_trade
                    stop_distance = abs(entry_price - (entry_price * (1 - config.stop_loss if signal_numeric == 1 else 1 + config.stop_loss)))
                    position_size = min(risk_amount / stop_distance, capital * 0.95 / entry_price)
                    
                    if position_size > 0:
                        position = {
                            'entry_time': current_time,
                            'entry_price': entry_price,
                            'size': position_size,
                            'side': 'long' if signal_numeric == 1 else 'short',
                            'stop_loss': entry_price * (1 - config.stop_loss if signal_numeric == 1 else 1 + config.stop_loss),
                            'take_profit': entry_price * (1 + config.take_profit_1 if signal_numeric == 1 else 1 - config.take_profit_1)
                        }
                        
            elif position is not None:
                # Verificar condiciones de salida
                current_pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * (1 if position['side'] == 'long' else -1)
                
                should_exit = False
                exit_reason = ""
                
                # Stop loss
                if (position['side'] == 'long' and current_price <= position['stop_loss']) or \
                   (position['side'] == 'short' and current_price >= position['stop_loss']):
                    should_exit = True
                    exit_reason = "STOP_LOSS"
                
                # Take profit
                elif (position['side'] == 'long' and current_price >= position['take_profit']) or \
                     (position['side'] == 'short' and current_price <= position['take_profit']):
                    should_exit = True
                    exit_reason = "TAKE_PROFIT"
                
                # Señal contraria
                elif (position['side'] == 'long' and signal == 'SELL') or \
                     (position['side'] == 'short' and signal == 'BUY'):
                    should_exit = True
                    exit_reason = "SIGNAL"
                
                if should_exit:
                    # Cerrar posición
                    exit_price = current_price * (1 - slippage if position['side'] == 'long' else 1 + slippage)
                    trade_return = ((exit_price - position['entry_price']) / position['entry_price']) * (1 if position['side'] == 'long' else -1)
                    trade_pnl = position['size'] * abs(exit_price - position['entry_price']) * (1 if trade_return > 0 else -1)
                    
                    # Aplicar comisiones
                    commission_cost = position['size'] * position['entry_price'] * commission * 2
                    trade_pnl -= commission_cost
                    
                    capital += trade_pnl
                    
                    trades.append({
                         'entry_time': position['entry_time'],
                         'exit_time': current_time,
                         'entry_price': position['entry_price'],
                         'exit_price': exit_price,
                         'return_pct': trade_return * 100,
                         'pnl': trade_pnl,
                         'exit_reason': exit_reason,
                         'side': position['side'],
                         'size': position['size']
                    })
                    
                    position = None
            
            equity_curve.append(capital)
        
        # Calcular métricas
        if not trades:
            print("⚠️ No se ejecutaron trades")
            return None
        
        trades_df = pd.DataFrame(trades)
        
        # Métricas básicas
        total_return = (capital - config.initial_capital) / config.initial_capital * 100
        total_trades = len(trades)
        winning_trades = len(trades_df[trades_df['return_pct'] > 0])
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        # Profit factor
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = abs(drawdown.min())
        
        # Retornos diarios
        days_tested = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days
        daily_return_avg = (total_return / days_tested) if days_tested > 0 else 0
        monthly_return_avg = daily_return_avg * 30
        
        # Ratios de riesgo
        if len(trades_df) > 1:
            returns = trades_df['return_pct'].values
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
            
            negative_returns = returns[returns < 0]
            sortino_ratio = np.mean(returns) / np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 0 and np.std(negative_returns) > 0 else 0
            
            calmar_ratio = (total_return / 100) / (max_drawdown / 100) if max_drawdown > 0 else 0
        else:
            sharpe_ratio = sortino_ratio = calmar_ratio = 0
        
        # Verificar cumplimiento de objetivos
        meets_daily_target = daily_return_avg >= 0.6
        meets_monthly_target = monthly_return_avg >= 15.0
        
        result = HistoricalBacktestResult(
            symbol=symbol,
            period=f"{start_date} to {end_date}",
            start_date=start_date,
            end_date=end_date,
            total_return=total_return,
            daily_return_avg=daily_return_avg,
            monthly_return_avg=monthly_return_avg,
            total_trades=total_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            final_capital=capital,
            days_tested=days_tested,
            meets_daily_target=meets_daily_target,
            meets_monthly_target=meets_monthly_target,
            raw_data_points=len(df)
        )
        
        self.results.append(result)
        
        print(f"✅ Backtest completado para {symbol}")
        return result
    
    def run_multiple_symbols_backtest(self, symbols: List[str], start_date: str, 
                                     end_date: str) -> List[HistoricalBacktestResult]:
        """Ejecuta backtest en múltiples símbolos"""
        
        print(f"\n🚀 INICIANDO BACKTEST MÚLTIPLE")
        print(f"Símbolos: {', '.join(symbols)}")
        print(f"Período: {start_date} a {end_date}")
        print("="*60)
        
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Procesando {symbol}...")
            
            try:
                result = self.run_historical_backtest(symbol, start_date, end_date)
                if result:
                    results.append(result)
                    print(f"✅ {symbol}: {result.total_return:.2f}% retorno total")
                else:
                    print(f"❌ {symbol}: Falló el backtest")
            except Exception as e:
                print(f"❌ {symbol}: Error - {e}")
            
            # Pausa entre símbolos para evitar rate limiting
            if i < len(symbols):
                time.sleep(1)
        
        return results
    
    def generate_comprehensive_report(self, results: List[HistoricalBacktestResult]):
        """Genera reporte comprehensivo"""
        
        if not results:
            print("❌ No hay resultados para reportar")
            return
        
        print("\n" + "="*80)
        print("📊 REPORTE COMPREHENSIVO - BACKTEST HISTÓRICO REAL")
        print("="*80)
        
        # Estadísticas generales
        total_symbols = len(results)
        successful_symbols = len([r for r in results if r.total_return > 0])
        
        avg_total_return = np.mean([r.total_return for r in results])
        avg_daily_return = np.mean([r.daily_return_avg for r in results])
        avg_monthly_return = np.mean([r.monthly_return_avg for r in results])
        avg_win_rate = np.mean([r.win_rate for r in results])
        avg_sharpe = np.mean([r.sharpe_ratio for r in results])
        avg_max_dd = np.mean([r.max_drawdown for r in results])
        
        symbols_meeting_daily = len([r for r in results if r.meets_daily_target])
        symbols_meeting_monthly = len([r for r in results if r.meets_monthly_target])
        
        print(f"\n📈 RESUMEN GENERAL:")
        print(f"Símbolos probados: {total_symbols}")
        print(f"Símbolos rentables: {successful_symbols} ({successful_symbols/total_symbols*100:.1f}%)")
        print(f"Retorno total promedio: {avg_total_return:.2f}%")
        print(f"Retorno diario promedio: {avg_daily_return:.3f}%")
        print(f"Retorno mensual promedio: {avg_monthly_return:.2f}%")
        print(f"Win rate promedio: {avg_win_rate:.1f}%")
        print(f"Sharpe ratio promedio: {avg_sharpe:.2f}")
        print(f"Drawdown promedio: {avg_max_dd:.2f}%")
        
        print(f"\n🎯 CUMPLIMIENTO DE OBJETIVOS:")
        print(f"Símbolos que cumplen objetivo diario (0.6%): {symbols_meeting_daily}/{total_symbols} ({symbols_meeting_daily/total_symbols*100:.1f}%)")
        print(f"Símbolos que cumplen objetivo mensual (15%): {symbols_meeting_monthly}/{total_symbols} ({symbols_meeting_monthly/total_symbols*100:.1f}%)")
        
        # Mejores y peores performers
        best_performer = max(results, key=lambda x: x.total_return)
        worst_performer = min(results, key=lambda x: x.total_return)
        
        print(f"\n🏆 MEJOR PERFORMER:")
        print(f"Símbolo: {best_performer.symbol}")
        print(f"Retorno total: {best_performer.total_return:.2f}%")
        print(f"Retorno diario: {best_performer.daily_return_avg:.3f}%")
        print(f"Win rate: {best_performer.win_rate:.1f}%")
        print(f"Trades: {best_performer.total_trades}")
        
        print(f"\n📉 PEOR PERFORMER:")
        print(f"Símbolo: {worst_performer.symbol}")
        print(f"Retorno total: {worst_performer.total_return:.2f}%")
        print(f"Retorno diario: {worst_performer.daily_return_avg:.3f}%")
        print(f"Win rate: {worst_performer.win_rate:.1f}%")
        print(f"Trades: {worst_performer.total_trades}")
        
        # Tabla detallada
        print(f"\n📋 RESULTADOS DETALLADOS:")
        print("-" * 120)
        print(f"{'Símbolo':<12} {'Retorno%':<10} {'Diario%':<8} {'Mensual%':<10} {'Trades':<8} {'Win%':<6} {'Sharpe':<8} {'DD%':<6} {'Obj.D':<5} {'Obj.M':<5}")
        print("-" * 120)
        
        for result in sorted(results, key=lambda x: x.total_return, reverse=True):
            daily_check = "✅" if result.meets_daily_target else "❌"
            monthly_check = "✅" if result.meets_monthly_target else "❌"
            
            print(f"{result.symbol:<12} {result.total_return:<10.2f} {result.daily_return_avg:<8.3f} {result.monthly_return_avg:<10.2f} "
                  f"{result.total_trades:<8} {result.win_rate:<6.1f} {result.sharpe_ratio:<8.2f} {result.max_drawdown:<6.2f} "
                  f"{daily_check:<5} {monthly_check:<5}")
        
        print("-" * 120)
        
        # Evaluación final
        success_rate = symbols_meeting_monthly / total_symbols * 100
        
        print(f"\n🎯 EVALUACIÓN FINAL:")
        if success_rate >= 70:
            print(f"🟢 ESTRATEGIA APROBADA - {success_rate:.1f}% de símbolos cumplen objetivos")
        elif success_rate >= 50:
            print(f"🟡 ESTRATEGIA PARCIALMENTE VALIDADA - {success_rate:.1f}% de símbolos cumplen objetivos")
        else:
            print(f"🔴 ESTRATEGIA REQUIERE OPTIMIZACIÓN - Solo {success_rate:.1f}% de símbolos cumplen objetivos")
        
        print("="*80)

def main():
    """Función principal"""
    
    print("🚀 BACKTESTER CON DATOS HISTÓRICOS REALES DE BINANCE")
    print("Validación exhaustiva de la estrategia 15% mensual")
    
    backtester = HistoricalBacktester()
    
    # Configuración de pruebas
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'BNBUSDT']
    
    # Diferentes períodos de prueba
    test_periods = [
        ('2024-01-01', '2024-03-31'),  # Q1 2024
        ('2024-04-01', '2024-06-30'),  # Q2 2024
        ('2024-07-01', '2024-09-30'),  # Q3 2024
        ('2024-10-01', '2024-12-15'),  # Q4 2024 (hasta ahora)
    ]
    
    all_results = []
    
    for i, (start_date, end_date) in enumerate(test_periods, 1):
        print(f"\n🔄 PERÍODO {i}/4: {start_date} a {end_date}")
        
        period_results = backtester.run_multiple_symbols_backtest(symbols, start_date, end_date)
        all_results.extend(period_results)
        
        # Reporte del período
        if period_results:
            avg_return = np.mean([r.total_return for r in period_results])
            success_count = len([r for r in period_results if r.meets_monthly_target])
            print(f"\n📊 Resumen período {i}: {avg_return:.2f}% retorno promedio, {success_count}/{len(period_results)} símbolos exitosos")
    
    # Reporte final comprehensivo
    if all_results:
        backtester.generate_comprehensive_report(all_results)
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backtest_historico_{timestamp}.json"
        
        results_data = []
        for result in all_results:
            results_data.append({
            'symbol': result.symbol,
            'period': result.period,
            'total_return': float(result.total_return),
            'daily_return_avg': float(result.daily_return_avg),
            'monthly_return_avg': float(result.monthly_return_avg),
            'total_trades': int(result.total_trades),
            'win_rate': float(result.win_rate),
            'profit_factor': float(result.profit_factor),
            'max_drawdown': float(result.max_drawdown),
            'sharpe_ratio': float(result.sharpe_ratio),
            'meets_daily_target': bool(result.meets_daily_target),
            'meets_monthly_target': bool(result.meets_monthly_target),
            'days_tested': int(result.days_tested),
            'raw_data_points': int(result.raw_data_points)
        })
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Resultados guardados en: {filename}")
    
    else:
        print("❌ No se obtuvieron resultados válidos")

if __name__ == "__main__":
    main()