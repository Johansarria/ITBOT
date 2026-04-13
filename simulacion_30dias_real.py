#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulación con Datos Históricos Reales de Binance - Últimos 30 Días
Backtesting individual para SOLUSDT, BNBUSDT, ADAUSDT con 500 USDT cada uno
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time
import warnings
warnings.filterwarnings('ignore')

class BinanceHistoricalSimulator:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.initial_capital = 500.0  # USDT por par
        
        # Fees reales de Binance (spot trading)
        self.maker_fee = 0.001  # 0.1%
        self.taker_fee = 0.001  # 0.1%
        self.slippage = 0.0005  # 0.05% slippage estimado
        
        # Pares objetivo
        self.symbols = ['SOLUSDT', 'BNBUSDT', 'ADAUSDT']
        
        print("🚀 SIMULACIÓN CON DATOS REALES DE BINANCE")
        print(f"📅 Período: Últimos 30 días hasta ayer")
        print(f"💰 Capital inicial por par: {self.initial_capital} USDT")
        print(f"📊 Pares a analizar: {', '.join(self.symbols)}")
        print("=" * 60)
    
    def get_historical_data(self, symbol, days=30):
        """Obtiene datos históricos reales de Binance"""
        try:
            # Calcular timestamps
            end_time = datetime.now() - timedelta(days=1)  # Hasta ayer
            start_time = end_time - timedelta(days=days)
            
            start_timestamp = int(start_time.timestamp() * 1000)
            end_timestamp = int(end_time.timestamp() * 1000)
            
            print(f"📥 Descargando datos de {symbol}...")
            print(f"   Desde: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Hasta: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Endpoint para klines (candlestick data)
            url = f"{self.base_url}/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': '1h',  # Datos horarios para mayor precisión
                'startTime': start_timestamp,
                'endTime': end_timestamp,
                'limit': 1000
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Error obteniendo datos de {symbol}: {response.status_code}")
                return None
            
            data = response.json()
            
            if not data:
                print(f"❌ No hay datos disponibles para {symbol}")
                return None
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos de datos
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            print(f"✅ Datos obtenidos: {len(df)} registros horarios")
            return df
            
        except Exception as e:
            print(f"❌ Error descargando datos de {symbol}: {e}")
            return None
    
    def calculate_technical_indicators(self, df):
        """Calcula indicadores técnicos"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        return df
    
    def generate_signals(self, df):
        """Genera señales de trading basadas en múltiples indicadores"""
        signals = []
        
        for i in range(50, len(df)):  # Empezar después de que los indicadores se estabilicen
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Condiciones de compra
            buy_conditions = [
                current['rsi'] < 30,  # RSI oversold
                current['macd'] > current['macd_signal'] and prev['macd'] <= prev['macd_signal'],  # MACD crossover
                current['close'] < current['bb_lower'],  # Precio por debajo de Bollinger inferior
                current['close'] > current['sma_20'],  # Precio por encima de SMA 20
                current['volume'] > df['volume'].rolling(20).mean().iloc[i] * 1.2  # Volumen alto
            ]
            
            # Condiciones de venta
            sell_conditions = [
                current['rsi'] > 70,  # RSI overbought
                current['macd'] < current['macd_signal'] and prev['macd'] >= prev['macd_signal'],  # MACD crossover down
                current['close'] > current['bb_upper'],  # Precio por encima de Bollinger superior
                current['close'] < current['sma_20']  # Precio por debajo de SMA 20
            ]
            
            # Señal de compra (al menos 3 condiciones)
            if sum(buy_conditions) >= 3:
                signals.append({
                    'timestamp': current['timestamp'],
                    'price': current['close'],
                    'action': 'BUY',
                    'conditions_met': sum(buy_conditions)
                })
            
            # Señal de venta (al menos 2 condiciones)
            elif sum(sell_conditions) >= 2:
                signals.append({
                    'timestamp': current['timestamp'],
                    'price': current['close'],
                    'action': 'SELL',
                    'conditions_met': sum(sell_conditions)
                })
        
        return signals
    
    def execute_backtest(self, symbol, df, signals):
        """Ejecuta el backtesting con fees y slippage reales"""
        capital = self.initial_capital
        position = 0  # Cantidad de tokens
        trades = []
        equity_curve = []
        max_equity = capital
        max_drawdown = 0
        
        print(f"\n🔄 Ejecutando backtesting para {symbol}...")
        print(f"📊 Señales generadas: {len(signals)}")
        
        for signal in signals:
            timestamp = signal['timestamp']
            price = signal['price']
            action = signal['action']
            
            if action == 'BUY' and position == 0:  # Abrir posición
                # Aplicar slippage y fees
                execution_price = price * (1 + self.slippage)
                fee = capital * self.taker_fee
                
                position = (capital - fee) / execution_price
                capital = 0
                
                trades.append({
                    'timestamp': timestamp,
                    'action': 'BUY',
                    'price': price,
                    'execution_price': execution_price,
                    'quantity': position,
                    'fee': fee,
                    'capital_after': capital
                })
                
            elif action == 'SELL' and position > 0:  # Cerrar posición
                # Aplicar slippage y fees
                execution_price = price * (1 - self.slippage)
                gross_proceeds = position * execution_price
                fee = gross_proceeds * self.taker_fee
                
                capital = gross_proceeds - fee
                
                trades.append({
                    'timestamp': timestamp,
                    'action': 'SELL',
                    'price': price,
                    'execution_price': execution_price,
                    'quantity': position,
                    'fee': fee,
                    'capital_after': capital
                })
                
                position = 0
            
            # Calcular equity actual
            if position > 0:
                current_value = position * price
                current_equity = current_value
            else:
                current_equity = capital
            
            equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity
            })
            
            # Calcular drawdown
            if current_equity > max_equity:
                max_equity = current_equity
            
            drawdown = (max_equity - current_equity) / max_equity * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Si queda posición abierta, cerrarla al precio final
        if position > 0:
            final_price = df['close'].iloc[-1]
            execution_price = final_price * (1 - self.slippage)
            gross_proceeds = position * execution_price
            fee = gross_proceeds * self.taker_fee
            capital = gross_proceeds - fee
            
            trades.append({
                'timestamp': df['timestamp'].iloc[-1],
                'action': 'SELL_FINAL',
                'price': final_price,
                'execution_price': execution_price,
                'quantity': position,
                'fee': fee,
                'capital_after': capital
            })
        
        return {
            'final_capital': capital,
            'trades': trades,
            'equity_curve': equity_curve,
            'max_drawdown': max_drawdown
        }
    
    def calculate_metrics(self, symbol, backtest_result):
        """Calcula métricas detalladas del backtest"""
        initial = self.initial_capital
        final = backtest_result['final_capital']
        trades = backtest_result['trades']
        
        # Métricas básicas
        total_return = ((final - initial) / initial) * 100
        total_trades = len([t for t in trades if t['action'] in ['BUY', 'SELL']])
        
        # Calcular PnL por trade
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] in ['SELL', 'SELL_FINAL']]
        
        trade_pnls = []
        total_fees = sum(t['fee'] for t in trades)
        
        for i in range(min(len(buy_trades), len(sell_trades))):
            buy = buy_trades[i]
            sell = sell_trades[i]
            
            buy_cost = buy['quantity'] * buy['execution_price'] + buy['fee']
            sell_proceeds = sell['quantity'] * sell['execution_price'] - sell['fee']
            pnl = sell_proceeds - buy_cost
            pnl_pct = (pnl / buy_cost) * 100
            
            trade_pnls.append({
                'trade_num': i + 1,
                'buy_price': buy['execution_price'],
                'sell_price': sell['execution_price'],
                'quantity': buy['quantity'],
                'pnl_usd': pnl,
                'pnl_pct': pnl_pct,
                'duration': (sell['timestamp'] - buy['timestamp']).total_seconds() / 3600  # horas
            })
        
        # Estadísticas de trades
        winning_trades = [t for t in trade_pnls if t['pnl_usd'] > 0]
        losing_trades = [t for t in trade_pnls if t['pnl_usd'] < 0]
        
        win_rate = (len(winning_trades) / len(trade_pnls) * 100) if trade_pnls else 0
        avg_win = np.mean([t['pnl_usd'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_usd'] for t in losing_trades]) if losing_trades else 0
        
        # Ratio riesgo/beneficio
        risk_reward_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        return {
            'symbol': symbol,
            'initial_capital': initial,
            'final_capital': final,
            'total_return_pct': total_return,
            'total_return_usd': final - initial,
            'total_trades': total_trades,
            'completed_trades': len(trade_pnls),
            'win_rate': win_rate,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'avg_win_usd': avg_win,
            'avg_loss_usd': avg_loss,
            'risk_reward_ratio': risk_reward_ratio,
            'max_drawdown': backtest_result['max_drawdown'],
            'total_fees': total_fees,
            'trade_details': trade_pnls
        }
    
    def run_simulation(self):
        """Ejecuta la simulación completa"""
        results = {}
        
        for symbol in self.symbols:
            print(f"\n{'='*60}")
            print(f"🎯 ANALIZANDO {symbol}")
            print(f"{'='*60}")
            
            # Obtener datos históricos
            df = self.get_historical_data(symbol)
            if df is None:
                continue
            
            # Calcular indicadores técnicos
            df = self.calculate_technical_indicators(df)
            
            # Generar señales
            signals = self.generate_signals(df)
            
            # Ejecutar backtesting
            backtest_result = self.execute_backtest(symbol, df, signals)
            
            # Calcular métricas
            metrics = self.calculate_metrics(symbol, backtest_result)
            
            results[symbol] = metrics
            
            # Mostrar resultados preliminares
            print(f"\n📊 RESULTADOS PRELIMINARES {symbol}:")
            print(f"   💰 Capital final: ${metrics['final_capital']:.2f}")
            print(f"   📈 Retorno: {metrics['total_return_pct']:.2f}%")
            print(f"   🎯 Win Rate: {metrics['win_rate']:.1f}%")
            print(f"   📉 Max Drawdown: {metrics['max_drawdown']:.2f}%")
            print(f"   💸 Fees totales: ${metrics['total_fees']:.2f}")
            
            time.sleep(1)  # Pausa para evitar rate limiting
        
        return results
    
    def generate_report(self, results):
        """Genera reporte estructurado final"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"simulacion_30dias_real_{timestamp}.json"
        
        # Preparar reporte
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'period': '30 días hasta ayer',
                'initial_capital_per_pair': self.initial_capital,
                'total_initial_capital': self.initial_capital * len(self.symbols),
                'maker_fee': self.maker_fee,
                'taker_fee': self.taker_fee,
                'slippage': self.slippage,
                'data_source': 'Binance API Real Data'
            },
            'individual_results': results,
            'summary': self._generate_summary(results)
        }
        
        # Guardar reporte
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✅ Reporte guardado: {filename}")
        return report
    
    def _generate_summary(self, results):
        """Genera resumen consolidado"""
        total_initial = self.initial_capital * len(results)
        total_final = sum(r['final_capital'] for r in results.values())
        total_return = ((total_final - total_initial) / total_initial) * 100
        
        # Ranking por rendimiento
        sorted_results = sorted(results.items(), key=lambda x: x[1]['total_return_pct'], reverse=True)
        
        return {
            'total_initial_capital': total_initial,
            'total_final_capital': total_final,
            'total_return_pct': total_return,
            'total_return_usd': total_final - total_initial,
            'best_performer': sorted_results[0][0] if sorted_results else None,
            'worst_performer': sorted_results[-1][0] if sorted_results else None,
            'avg_return_pct': np.mean([r['total_return_pct'] for r in results.values()]),
            'total_fees': sum(r['total_fees'] for r in results.values()),
            'ranking': [{'symbol': symbol, 'return_pct': data['total_return_pct']} for symbol, data in sorted_results]
        }

def main():
    """Función principal"""
    try:
        simulator = BinanceHistoricalSimulator()
        
        print("\n🚀 Iniciando simulación...")
        results = simulator.run_simulation()
        
        if results:
            print("\n📋 Generando reporte final...")
            report = simulator.generate_report(results)
            
            print("\n" + "="*60)
            print("🏆 RESUMEN FINAL DE SIMULACIÓN")
            print("="*60)
            
            summary = report['summary']
            print(f"💰 Capital inicial total: ${summary['total_initial_capital']:.2f}")
            print(f"💰 Capital final total: ${summary['total_final_capital']:.2f}")
            print(f"📈 Retorno total: {summary['total_return_pct']:.2f}%")
            print(f"💸 Fees totales: ${summary['total_fees']:.2f}")
            print(f"\n🥇 Mejor performer: {summary['best_performer']}")
            print(f"🥉 Peor performer: {summary['worst_performer']}")
            
            print("\n📊 RANKING POR RENDIMIENTO:")
            for i, item in enumerate(summary['ranking'], 1):
                print(f"   {i}. {item['symbol']}: {item['return_pct']:.2f}%")
            
            print("\n✅ Simulación completada exitosamente")
        else:
            print("❌ No se pudieron obtener resultados")
            
    except Exception as e:
        print(f"❌ Error en simulación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()