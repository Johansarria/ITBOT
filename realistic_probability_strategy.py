#!/usr/bin/env python3
"""
Estrategia de Probabilidad Dinámica Realista - ITBOT
Versión optimizada con parámetros conservadores y datos realistas
Objetivo: 15% retorno mensual sostenible
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class RealisticProbabilityStrategy:
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = []
        self.max_positions = 3
        self.max_position_hours = 24
        
        # Parámetros de probabilidad balanceados
        self.base_frequency = 0.55  # 55% probabilidad base (balanceado)
        self.max_momentum_bonus = 0.20  # Máximo 20% bonus (balanceado)
        
        # Filtros de calidad balanceados
        self.min_volume_ratio = 1.15  # 115% del promedio (menos estricto)
        self.min_volatility = 0.002   # 0.2% (menos estricto)
        self.max_volatility = 0.035   # 3.5% (menos conservador)
        
        # Gestión de riesgo más conservadora
        self.position_size_pct = 0.10  # 10% del capital (reducido de 18%)
        self.max_daily_loss = 0.05     # 5% pérdida diaria máxima (más conservador)
        self.consecutive_losses = 0
        self.max_consecutive_losses = 2  # Más estricto
        
        # Tracking
        self.trades_history = []
        self.daily_pnl = 0.0
        self.current_day = None
        
    def generate_realistic_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Genera datos más realistas para crypto trading"""
        np.random.seed(42)  # Para reproducibilidad
        
        # Parámetros más realistas
        base_prices = {
            'BTC-USD': 45000,
            'ETH-USD': 2800,
            'BNB-USD': 350,
            'ADA-USD': 0.85,
            'SOL-USD': 120
        }
        
        base_price = base_prices.get(symbol, 45000)
        hours = days * 24
        
        # Generar retornos más realistas (menor volatilidad)
        returns = np.random.normal(0.0001, 0.008, hours)  # Retornos horarios más conservadores
        prices = [base_price]
        
        for i in range(1, hours):
            # Momentum más suave
            momentum = 0.05 * returns[i-1] if i > 0 else 0
            # Reversión a la media más fuerte
            mean_reversion = -0.02 * (prices[-1] / base_price - 1)
            
            price_change = returns[i] + momentum + mean_reversion
            # Limitar cambios extremos
            price_change = max(-0.05, min(0.05, price_change))  # Máximo 5% cambio por hora
            
            new_price = prices[-1] * (1 + price_change)
            new_price = max(new_price, base_price * 0.7)  # No caer más del 30%
            new_price = min(new_price, base_price * 1.5)  # No subir más del 50%
            prices.append(new_price)
        
        # Generar volúmenes más estables
        base_volume = 500000
        volumes = []
        for i in range(hours):
            vol_multiplier = 1 + abs(returns[i]) * 5  # Correlación más suave
            volume = base_volume * vol_multiplier * np.random.uniform(0.8, 1.2)
            volumes.append(volume)
        
        # Crear DataFrame
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                             periods=hours, freq='H')
        
        # Asegurar longitudes correctas
        data_length = min(len(dates), len(prices)-1, len(volumes))
        
        df = pd.DataFrame({
            'timestamp': dates[:data_length],
            'open': prices[:data_length],
            'high': [p * np.random.uniform(1.001, 1.008) for p in prices[:data_length]],
            'low': [p * np.random.uniform(0.992, 0.999) for p in prices[:data_length]],
            'close': prices[1:data_length+1],
            'volume': volumes[:data_length]
        })
        
        return df
    
    def calculate_volatility(self, prices: pd.Series) -> float:
        """Calcula volatilidad como cambio porcentual absoluto"""
        if len(prices) < 2:
            return 0.0
        return abs((prices.iloc[-1] - prices.iloc[-2]) / prices.iloc[-2])
    
    def calculate_volume_ratio(self, volumes: pd.Series, current_volume: float) -> float:
        """Calcula ratio de volumen actual vs promedio 20 períodos"""
        if len(volumes) < 20:
            return 1.0
        avg_volume = volumes.tail(20).mean()
        return current_volume / avg_volume if avg_volume > 0 else 1.0
    
    def calculate_dynamic_tp_sl(self, volatility: float, signal_type: str) -> Tuple[float, float]:
        """Calcula TP y SL dinámicos más conservadores"""
        # Take Profit más conservador (3% - 8%)
        if signal_type == 'A':  # Momentum
            tp_base = 0.04 + (0.08 - 0.04) * min(1.0, volatility * 40)
        elif signal_type == 'B':  # Bounce
            tp_base = 0.03 + (0.06 - 0.03) * min(1.0, volatility * 30)
        elif signal_type == 'C':  # Breakout
            tp_base = 0.05 + (0.08 - 0.05) * min(1.0, volatility * 50)
        else:  # Tipo D
            tp_base = 0.03 + (0.07 - 0.03) * min(1.0, volatility * 35)
        
        tp_variation = random.uniform(-0.10, 0.10)
        tp_final = max(0.025, min(0.08, tp_base * (1 + tp_variation)))
        
        # Stop Loss más conservador (1.0% - 1.8%)
        sl_base = 0.01 + (0.018 - 0.01) * min(1.0, volatility * 25)
        sl_variation = random.uniform(-0.05, 0.05)
        sl_final = max(0.008, min(0.02, sl_base * (1 + sl_variation)))
        
        return tp_final, sl_final
    
    def calculate_signal_probability(self, data: pd.DataFrame, index: int) -> Tuple[float, str]:
        """Calcula probabilidad de señal más conservadora"""
        if index < 20:
            return 0.0, 'none'
        
        current_price = data.iloc[index]['close']
        previous_price = data.iloc[index-1]['close']
        price_change = (current_price - previous_price) / previous_price
        
        # Factor posicional más conservador
        data_length = len(data[:index])
        position_factor = max(0.9, 1.1 - (data_length / 2000))  # Menos agresivo
        
        # Momentum bonus más conservador
        momentum_bonus = min(self.max_momentum_bonus, abs(price_change) * 50)  # Reducido
        
        # Probabilidad final
        final_probability = (self.base_frequency + momentum_bonus) * position_factor
        
        # Determinar tipo de señal con criterios balanceados
        signal_type = 'none'
        if price_change > 0.005:  # Cambio > 0.5% (menos estricto)
            signal_type = 'A'  # Momentum Positivo
        elif current_price <= data.iloc[max(0, index-15):index]['close'].min() * 1.005:
            signal_type = 'B'  # Bounce en Soporte
        elif data.iloc[index]['volume'] > data.iloc[max(0, index-20):index]['volume'].mean() * 1.4:
            signal_type = 'C'  # Breakout Volumen (menos estricto)
        else:
            signal_type = 'D'  # Entrada Aleatoria Ponderada
        
        return final_probability, signal_type
    
    def check_quality_filters(self, data: pd.DataFrame, index: int) -> bool:
        """Verifica filtros de calidad más estrictos"""
        if index < 20:
            return False
        
        current_volume = data.iloc[index]['volume']
        volumes = data.iloc[max(0, index-20):index]['volume']
        volume_ratio = self.calculate_volume_ratio(volumes, current_volume)
        
        prices = data.iloc[max(0, index-2):index+1]['close']
        volatility = self.calculate_volatility(prices)
        
        # Verificar filtros más estrictos
        volume_ok = volume_ratio >= self.min_volume_ratio
        volatility_ok = self.min_volatility < volatility < self.max_volatility
        positions_ok = len(self.positions) < self.max_positions
        
        # Filtro adicional: no operar si hay mucha volatilidad reciente
        recent_volatilities = []
        for i in range(max(0, index-5), index):
            if i >= 1:
                vol = abs((data.iloc[i]['close'] - data.iloc[i-1]['close']) / data.iloc[i-1]['close'])
                recent_volatilities.append(vol)
        
        avg_recent_vol = np.mean(recent_volatilities) if recent_volatilities else 0
        volatility_stable = avg_recent_vol < 0.025  # Volatilidad promedio < 2.5% (menos estricto)
        
        return volume_ok and volatility_ok and positions_ok and volatility_stable
    
    def open_position(self, symbol: str, entry_price: float, tp_pct: float, sl_pct: float, signal_type: str):
        """Abre nueva posición con gestión de capital conservadora"""
        # Usar un porcentaje fijo del capital inicial para evitar compounding extremo
        position_size = self.initial_capital * self.position_size_pct
        
        position = {
            'symbol': symbol,
            'entry_price': entry_price,
            'position_size': position_size,
            'tp_price': entry_price * (1 + tp_pct),
            'sl_price': entry_price * (1 - sl_pct),
            'entry_time': datetime.now(),
            'signal_type': signal_type,
            'tp_pct': tp_pct,
            'sl_pct': sl_pct
        }
        
        self.positions.append(position)
        print(f"🚀 NUEVA POSICIÓN {signal_type}: {symbol} @ ${entry_price:.2f} | TP: {tp_pct*100:.1f}% | SL: {sl_pct*100:.1f}%")
    
    def check_exit_conditions(self, data: pd.DataFrame, index: int):
        """Verifica condiciones de salida"""
        current_price = data.iloc[index]['close']
        current_time = data.iloc[index]['timestamp']
        
        positions_to_close = []
        
        for i, position in enumerate(self.positions):
            entry_price = position['entry_price']
            tp_price = position['tp_price']
            sl_price = position['sl_price']
            entry_time = position['entry_time']
            
            # Verificar TP
            if current_price >= tp_price:
                pnl = (current_price - entry_price) / entry_price
                self.close_position(i, current_price, 'TP', pnl)
                positions_to_close.append(i)
            
            # Verificar SL
            elif current_price <= sl_price:
                pnl = (current_price - entry_price) / entry_price
                self.close_position(i, current_price, 'SL', pnl)
                positions_to_close.append(i)
            
            # Verificar tiempo máximo
            elif (current_time - entry_time).total_seconds() > self.max_position_hours * 3600:
                pnl = (current_price - entry_price) / entry_price
                self.close_position(i, current_price, 'TIME', pnl)
                positions_to_close.append(i)
        
        # Remover posiciones cerradas
        for i in sorted(positions_to_close, reverse=True):
            del self.positions[i]
    
    def close_position(self, position_index: int, exit_price: float, exit_reason: str, pnl_pct: float):
        """Cierra posición y actualiza capital"""
        position = self.positions[position_index]
        
        # Calcular PnL sobre el monto invertido
        pnl_amount = position['position_size'] * pnl_pct
        self.current_capital += pnl_amount
        self.daily_pnl += pnl_amount
        
        # Tracking de pérdidas consecutivas
        if pnl_pct < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Guardar trade
        trade = {
            'symbol': position['symbol'],
            'signal_type': position['signal_type'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100,
            'pnl_amount': pnl_amount,
            'tp_pct': position['tp_pct'] * 100,
            'sl_pct': position['sl_pct'] * 100
        }
        
        self.trades_history.append(trade)
        
        status = "✅" if pnl_pct > 0 else "❌"
        print(f"{status} CERRADO {exit_reason}: {position['symbol']} | PnL: {pnl_pct*100:.2f}% (${pnl_amount:.2f})")
    
    def should_stop_trading(self) -> bool:
        """Verifica si debe parar el trading"""
        # Parar si pérdida diaria excede límite
        daily_loss_pct = self.daily_pnl / self.current_capital
        if daily_loss_pct < -self.max_daily_loss:
            return True
        
        # Parar si pérdidas consecutivas exceden límite
        if self.consecutive_losses >= self.max_consecutive_losses:
            return True
        
        return False
    
    def run_backtest(self, symbols: List[str] = None, days: int = 30) -> Dict:
        """Ejecuta backtest realista"""
        if symbols is None:
            symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD']
        
        print("🎲 INICIANDO BACKTEST REALISTA - Estrategia de Probabilidad Dinámica")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print(f"📊 Símbolos: {', '.join(symbols)}")
        print(f"📅 Período: {days} días")
        print("="*60)
        
        # Generar datos realistas
        all_data = {}
        for symbol in symbols:
            all_data[symbol] = self.generate_realistic_data(symbol, days)
        
        # Simular trading
        total_hours = days * 24
        
        for hour in range(20, total_hours):
            if self.should_stop_trading():
                print("🛑 TRADING DETENIDO - Límites de riesgo alcanzados")
                break
            
            # Resetear PnL diario
            current_hour = hour % 24
            if current_hour == 0:
                self.daily_pnl = 0.0
            
            # Procesar cada símbolo
            for symbol in symbols:
                data = all_data[symbol]
                
                if hour >= len(data):
                    continue
                
                # Verificar salidas primero
                self.check_exit_conditions(data, hour)
                
                # Verificar nuevas entradas (menos frecuente)
                if len(self.positions) < self.max_positions and hour % 2 == 0:  # Solo cada 2 horas
                    probability, signal_type = self.calculate_signal_probability(data, hour)
                    
                    # Generar señal con probabilidad reducida
                    if np.random.random() < probability * 0.7:  # Reducir probabilidad general
                        if self.check_quality_filters(data, hour):
                            current_price = data.iloc[hour]['close']
                            prices = data.iloc[max(0, hour-2):hour+1]['close']
                            volatility = self.calculate_volatility(prices)
                            
                            tp_pct, sl_pct = self.calculate_dynamic_tp_sl(volatility, signal_type)
                            self.open_position(symbol, current_price, tp_pct, sl_pct, signal_type)
        
        # Cerrar posiciones restantes
        for i in range(len(self.positions)):
            if i < len(self.positions):
                last_data = all_data[self.positions[i]['symbol']]
                last_price = last_data.iloc[-1]['close']
                entry_price = self.positions[i]['entry_price']
                pnl = (last_price - entry_price) / entry_price
                self.close_position(i, last_price, 'END', pnl)
        
        self.positions = []
        
        return self.generate_results()
    
    def generate_results(self) -> Dict:
        """Genera reporte de resultados"""
        if not self.trades_history:
            return {'error': 'No hay trades para analizar'}
        
        # Calcular métricas
        total_trades = len(self.trades_history)
        winning_trades = len([t for t in self.trades_history if t['pnl_pct'] > 0])
        win_rate = (winning_trades / total_trades) * 100
        
        total_return_pct = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        monthly_return = total_return_pct
        
        # Calcular drawdown máximo
        running_capital = self.initial_capital
        peak_capital = self.initial_capital
        max_drawdown = 0
        
        for trade in self.trades_history:
            running_capital += trade['pnl_amount']
            if running_capital > peak_capital:
                peak_capital = running_capital
            drawdown = (peak_capital - running_capital) / peak_capital * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Distribución por tipo de señal
        signal_types = {}
        for trade in self.trades_history:
            signal_type = trade['signal_type']
            if signal_type not in signal_types:
                signal_types[signal_type] = {'count': 0, 'wins': 0, 'total_pnl': 0}
            signal_types[signal_type]['count'] += 1
            if trade['pnl_pct'] > 0:
                signal_types[signal_type]['wins'] += 1
            signal_types[signal_type]['total_pnl'] += trade['pnl_pct']
        
        results = {
            'capital_inicial': self.initial_capital,
            'capital_final': self.current_capital,
            'retorno_total_pct': total_return_pct,
            'retorno_mensual_estimado': monthly_return,
            'total_trades': total_trades,
            'trades_ganadores': winning_trades,
            'win_rate_pct': win_rate,
            'max_drawdown_pct': max_drawdown,
            'signal_types': signal_types,
            'objetivo_10pct': monthly_return >= 10.0,
            'objetivo_15pct': monthly_return >= 15.0,
            'superacion_objetivo': monthly_return / 10.0 if monthly_return > 0 else 0
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Imprime resultados formateados"""
        print("\n" + "="*60)
        print("🏆 RESULTADOS DEL BACKTEST REALISTA")
        print("="*60)
        
        print(f"💰 Capital inicial: ${results['capital_inicial']:,.2f}")
        print(f"💰 Capital final: ${results['capital_final']:,.2f}")
        print(f"📈 Retorno total: {results['retorno_total_pct']:.2f}%")
        print(f"📊 Retorno mensual estimado: {results['retorno_mensual_estimado']:.2f}%")
        print(f"🎯 Trades totales: {results['total_trades']}")
        print(f"✅ Trades ganadores: {results['trades_ganadores']}")
        print(f"📊 Win rate: {results['win_rate_pct']:.2f}%")
        print(f"📉 Máximo drawdown: {results['max_drawdown_pct']:.2f}%")
        
        if results['signal_types']:
            print("\n📊 DISTRIBUCIÓN POR TIPO DE SEÑAL:")
            for signal_type, data in results['signal_types'].items():
                win_rate = (data['wins'] / data['count']) * 100 if data['count'] > 0 else 0
                avg_pnl = data['total_pnl'] / data['count'] if data['count'] > 0 else 0
                print(f"   Tipo {signal_type}: {data['count']} trades | {win_rate:.1f}% win rate | {avg_pnl:.2f}% avg PnL")
        
        print("\n🎯 EVALUACIÓN DE OBJETIVOS:")
        print(f"   Objetivo 10% mensual: {'✅ ALCANZADO' if results['objetivo_10pct'] else '❌ NO ALCANZADO'}")
        print(f"   Objetivo 15% mensual: {'✅ ALCANZADO' if results['objetivo_15pct'] else '❌ NO ALCANZADO'}")
        print(f"   Superación del objetivo: {results['superacion_objetivo']:.1f}x")
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"realistic_probability_results_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("RESULTADOS - Estrategia de Probabilidad Dinámica Realista\n")
            f.write("="*60 + "\n\n")
            f.write(f"Capital inicial: ${results['capital_inicial']:,.2f}\n")
            f.write(f"Capital final: ${results['capital_final']:,.2f}\n")
            f.write(f"Retorno total: {results['retorno_total_pct']:.2f}%\n")
            f.write(f"Retorno mensual estimado: {results['retorno_mensual_estimado']:.2f}%\n")
            f.write(f"Total trades: {results['total_trades']}\n")
            f.write(f"Win rate: {results['win_rate_pct']:.2f}%\n")
            f.write(f"Máximo drawdown: {results['max_drawdown_pct']:.2f}%\n\n")
            
            if results['signal_types']:
                f.write("Distribución por tipo de señal:\n")
                for signal_type, data in results['signal_types'].items():
                    win_rate = (data['wins'] / data['count']) * 100 if data['count'] > 0 else 0
                    avg_pnl = data['total_pnl'] / data['count'] if data['count'] > 0 else 0
                    f.write(f"Tipo {signal_type}: {data['count']} trades | {win_rate:.1f}% win rate | {avg_pnl:.2f}% avg PnL\n")
            
            f.write(f"\nObjetivo 10% mensual: {'ALCANZADO' if results['objetivo_10pct'] else 'NO ALCANZADO'}\n")
            f.write(f"Objetivo 15% mensual: {'ALCANZADO' if results['objetivo_15pct'] else 'NO ALCANZADO'}\n")
            f.write(f"Superación del objetivo: {results['superacion_objetivo']:.1f}x\n")
            
            # Detalles de trades
            f.write("\n" + "="*60 + "\n")
            f.write("DETALLE DE TRADES:\n")
            f.write("="*60 + "\n")
            for i, trade in enumerate(self.trades_history, 1):
                f.write(f"{i:3d}. {trade['symbol']} | Tipo {trade['signal_type']} | "
                       f"Entry: ${trade['entry_price']:.2f} | Exit: ${trade['exit_price']:.2f} | "
                       f"PnL: {trade['pnl_pct']:.2f}% | Razón: {trade['exit_reason']}\n")
        
        print(f"\n💾 Resultados guardados en: {filename}")

def main():
    """Función principal"""
    print("🎲 ESTRATEGIA DE PROBABILIDAD DINÁMICA REALISTA - ITBOT")
    print("Versión optimizada para resultados sostenibles")
    print("="*60)
    
    # Crear instancia de la estrategia
    strategy = RealisticProbabilityStrategy(initial_capital=1000.0)
    
    # Ejecutar backtest
    symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD']
    results = strategy.run_backtest(symbols=symbols, days=30)
    
    # Mostrar resultados
    if 'error' not in results:
        strategy.print_results(results)
        
        # Evaluación final
        if results['retorno_mensual_estimado'] >= 15.0:
            print("\n🎉 ¡OBJETIVO 15% MENSUAL ALCANZADO!")
            print(f"🚀 Retorno logrado: {results['retorno_mensual_estimado']:.2f}%")
        elif results['retorno_mensual_estimado'] >= 10.0:
            print("\n✅ Objetivo 10% mensual alcanzado")
            print(f"📈 Retorno logrado: {results['retorno_mensual_estimado']:.2f}%")
        else:
            print("\n⚠️ Objetivo no alcanzado - Parámetros necesitan optimización")
            print(f"📊 Retorno logrado: {results['retorno_mensual_estimado']:.2f}%")
            print("💡 Sugerencias: Ajustar filtros de calidad o parámetros de TP/SL")
    else:
        print(f"❌ Error en backtest: {results['error']}")

if __name__ == "__main__":
    main()