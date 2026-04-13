#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulación Simplificada con Datos de Binance - Solo librerías estándar
"""

import urllib.request
import json
import time
from datetime import datetime, timedelta
import math

class SimpleSimulator:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.initial_capital = 500.0
        self.maker_fee = 0.001
        self.taker_fee = 0.001
        self.slippage = 0.0005
        self.symbols = ['SOLUSDT', 'BNBUSDT', 'ADAUSDT']
        
        print("🚀 SIMULACIÓN SIMPLIFICADA - DATOS REALES BINANCE")
        print(f"💰 Capital por par: {self.initial_capital} USDT")
        print(f"📊 Pares: {', '.join(self.symbols)}")
        print("=" * 50)
    
    def get_kline_data(self, symbol, days=30):
        """Obtiene datos de velas de Binance"""
        try:
            end_time = datetime.now() - timedelta(days=1)
            start_time = end_time - timedelta(days=days)
            
            start_ts = int(start_time.timestamp() * 1000)
            end_ts = int(end_time.timestamp() * 1000)
            
            url = f"{self.base_url}/api/v3/klines?symbol={symbol}&interval=4h&startTime={start_ts}&endTime={end_ts}&limit=1000"
            
            print(f"📥 Obteniendo datos de {symbol}...")
            
            with urllib.request.urlopen(url, timeout=30) as response:
                data = json.loads(response.read().decode())
            
            if not data:
                print(f"❌ Sin datos para {symbol}")
                return []
            
            # Convertir a formato simple
            candles = []
            for item in data:
                candles.append({
                    'timestamp': int(item[0]),
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4]),
                    'volume': float(item[5])
                })
            
            print(f"✅ {len(candles)} velas obtenidas")
            return candles
            
        except Exception as e:
            print(f"❌ Error obteniendo {symbol}: {e}")
            return []
    
    def calculate_sma(self, prices, period):
        """Calcula media móvil simple"""
        if len(prices) < period:
            return []
        
        sma = []
        for i in range(period - 1, len(prices)):
            avg = sum(prices[i - period + 1:i + 1]) / period
            sma.append(avg)
        
        return sma
    
    def calculate_rsi(self, prices, period=14):
        """Calcula RSI"""
        if len(prices) < period + 1:
            return []
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        rsi_values = []
        
        for i in range(period - 1, len(gains)):
            avg_gain = sum(gains[i - period + 1:i + 1]) / period
            avg_loss = sum(losses[i - period + 1:i + 1]) / period
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    def generate_simple_signals(self, candles):
        """Genera señales simples de trading"""
        if len(candles) < 50:
            return []
        
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        # Calcular indicadores
        sma_20 = self.calculate_sma(closes, 20)
        sma_50 = self.calculate_sma(closes, 50)
        rsi = self.calculate_rsi(closes, 14)
        
        signals = []
        
        # Empezar desde donde todos los indicadores están disponibles
        start_idx = max(50, len(closes) - len(sma_20), len(closes) - len(rsi))
        
        for i in range(start_idx, len(candles)):
            current_price = closes[i]
            current_volume = volumes[i]
            
            # Índices ajustados para los arrays de indicadores
            sma20_idx = i - (len(closes) - len(sma_20))
            sma50_idx = i - (len(closes) - len(sma_50))
            rsi_idx = i - (len(closes) - len(rsi))
            
            if (sma20_idx >= 0 and sma50_idx >= 0 and rsi_idx >= 0 and
                sma20_idx < len(sma_20) and sma50_idx < len(sma_50) and rsi_idx < len(rsi)):
                
                current_sma20 = sma_20[sma20_idx]
                current_sma50 = sma_50[sma50_idx]
                current_rsi = rsi[rsi_idx]
                
                # Volumen promedio
                vol_avg = sum(volumes[max(0, i-10):i+1]) / min(11, i+1)
                
                # Señal de compra
                if (current_rsi < 35 and 
                    current_price > current_sma20 and 
                    current_sma20 > current_sma50 and
                    current_volume > vol_avg * 1.1):
                    
                    signals.append({
                        'timestamp': candles[i]['timestamp'],
                        'price': current_price,
                        'action': 'BUY',
                        'rsi': current_rsi
                    })
                
                # Señal de venta
                elif (current_rsi > 65 or 
                      current_price < current_sma20 or
                      current_sma20 < current_sma50):
                    
                    signals.append({
                        'timestamp': candles[i]['timestamp'],
                        'price': current_price,
                        'action': 'SELL',
                        'rsi': current_rsi
                    })
        
        return signals
    
    def execute_backtest(self, symbol, candles, signals):
        """Ejecuta backtesting simple"""
        capital = self.initial_capital
        position = 0
        trades = []
        equity_curve = []
        max_equity = capital
        max_drawdown = 0
        
        print(f"\n🔄 Backtesting {symbol} - {len(signals)} señales")
        
        for signal in signals:
            price = signal['price']
            action = signal['action']
            
            if action == 'BUY' and position == 0:
                # Comprar
                execution_price = price * (1 + self.slippage)
                fee = capital * self.taker_fee
                position = (capital - fee) / execution_price
                capital = 0
                
                trades.append({
                    'timestamp': signal['timestamp'],
                    'action': 'BUY',
                    'price': execution_price,
                    'quantity': position,
                    'fee': fee
                })
                
            elif action == 'SELL' and position > 0:
                # Vender
                execution_price = price * (1 - self.slippage)
                gross_proceeds = position * execution_price
                fee = gross_proceeds * self.taker_fee
                capital = gross_proceeds - fee
                
                trades.append({
                    'timestamp': signal['timestamp'],
                    'action': 'SELL',
                    'price': execution_price,
                    'quantity': position,
                    'fee': fee
                })
                
                position = 0
            
            # Calcular equity
            if position > 0:
                current_equity = position * price
            else:
                current_equity = capital
            
            equity_curve.append(current_equity)
            
            # Drawdown
            if current_equity > max_equity:
                max_equity = current_equity
            
            drawdown = (max_equity - current_equity) / max_equity * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Cerrar posición final si existe
        if position > 0 and candles:
            final_price = candles[-1]['close']
            execution_price = final_price * (1 - self.slippage)
            gross_proceeds = position * execution_price
            fee = gross_proceeds * self.taker_fee
            capital = gross_proceeds - fee
            
            trades.append({
                'timestamp': candles[-1]['timestamp'],
                'action': 'SELL_FINAL',
                'price': execution_price,
                'quantity': position,
                'fee': fee
            })
        
        return {
            'final_capital': capital,
            'trades': trades,
            'max_drawdown': max_drawdown
        }
    
    def calculate_metrics(self, symbol, result):
        """Calcula métricas del backtest"""
        initial = self.initial_capital
        final = result['final_capital']
        trades = result['trades']
        
        total_return = ((final - initial) / initial) * 100
        total_trades = len([t for t in trades if t['action'] in ['BUY', 'SELL']])
        total_fees = sum(t['fee'] for t in trades)
        
        # Calcular trades completos
        buy_trades = [t for t in trades if t['action'] == 'BUY']
        sell_trades = [t for t in trades if t['action'] in ['SELL', 'SELL_FINAL']]
        
        completed_trades = min(len(buy_trades), len(sell_trades))
        
        winning_trades = 0
        total_pnl = 0
        
        for i in range(completed_trades):
            buy_cost = buy_trades[i]['quantity'] * buy_trades[i]['price'] + buy_trades[i]['fee']
            sell_proceeds = sell_trades[i]['quantity'] * sell_trades[i]['price'] - sell_trades[i]['fee']
            pnl = sell_proceeds - buy_cost
            total_pnl += pnl
            
            if pnl > 0:
                winning_trades += 1
        
        win_rate = (winning_trades / completed_trades * 100) if completed_trades > 0 else 0
        
        return {
            'symbol': symbol,
            'initial_capital': initial,
            'final_capital': final,
            'total_return_pct': total_return,
            'total_return_usd': final - initial,
            'total_trades': total_trades,
            'completed_trades': completed_trades,
            'win_rate': win_rate,
            'winning_trades': winning_trades,
            'max_drawdown': result['max_drawdown'],
            'total_fees': total_fees
        }
    
    def run_simulation(self):
        """Ejecuta simulación completa"""
        results = {}
        
        for symbol in self.symbols:
            print(f"\n{'='*50}")
            print(f"🎯 ANALIZANDO {symbol}")
            print(f"{'='*50}")
            
            # Obtener datos
            candles = self.get_kline_data(symbol)
            if not candles:
                continue
            
            # Generar señales
            signals = self.generate_simple_signals(candles)
            print(f"📊 Señales generadas: {len(signals)}")
            
            # Ejecutar backtest
            backtest_result = self.execute_backtest(symbol, candles, signals)
            
            # Calcular métricas
            metrics = self.calculate_metrics(symbol, backtest_result)
            results[symbol] = metrics
            
            # Mostrar resultados
            print(f"\n📊 RESULTADOS {symbol}:")
            print(f"   💰 Capital final: ${metrics['final_capital']:.2f}")
            print(f"   📈 Retorno: {metrics['total_return_pct']:.2f}%")
            print(f"   🎯 Win Rate: {metrics['win_rate']:.1f}%")
            print(f"   📉 Max Drawdown: {metrics['max_drawdown']:.2f}%")
            print(f"   💸 Fees: ${metrics['total_fees']:.2f}")
            print(f"   🔄 Trades: {metrics['completed_trades']}")
            
            time.sleep(2)  # Pausa para rate limiting
        
        return results
    
    def save_results(self, results):
        """Guarda resultados en archivo"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"simulacion_simple_{timestamp}.json"
        
        # Calcular resumen
        total_initial = self.initial_capital * len(results)
        total_final = sum(r['final_capital'] for r in results.values())
        total_return = ((total_final - total_initial) / total_initial) * 100
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'period': '30 días hasta ayer',
                'initial_capital_per_pair': self.initial_capital,
                'total_initial': total_initial,
                'data_source': 'Binance API Real'
            },
            'results': results,
            'summary': {
                'total_initial': total_initial,
                'total_final': total_final,
                'total_return_pct': total_return,
                'total_return_usd': total_final - total_initial,
                'total_fees': sum(r['total_fees'] for r in results.values())
            }
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Resultados guardados: {filename}")
        return report

def main():
    try:
        simulator = SimpleSimulator()
        
        print("\n🚀 Iniciando simulación...")
        results = simulator.run_simulation()
        
        if results:
            report = simulator.save_results(results)
            
            print("\n" + "="*50)
            print("🏆 RESUMEN FINAL")
            print("="*50)
            
            summary = report['summary']
            print(f"💰 Capital inicial total: ${summary['total_initial']:.2f}")
            print(f"💰 Capital final total: ${summary['total_final']:.2f}")
            print(f"📈 Retorno total: {summary['total_return_pct']:.2f}%")
            print(f"💸 Fees totales: ${summary['total_fees']:.2f}")
            
            # Ranking
            sorted_results = sorted(results.items(), key=lambda x: x[1]['total_return_pct'], reverse=True)
            print("\n📊 RANKING:")
            for i, (symbol, data) in enumerate(sorted_results, 1):
                print(f"   {i}. {symbol}: {data['total_return_pct']:.2f}%")
            
            print("\n✅ Simulación completada")
        else:
            print("❌ No se obtuvieron resultados")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()