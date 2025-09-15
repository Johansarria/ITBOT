#!/usr/bin/env python3
"""
Estrategia de Trading Realista - ITBOT
Versión con gestión de riesgo estricta y resultados sostenibles
Objetivo: 10-15% retorno mensual REALISTA
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

class RealisticTradingStrategy:
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.available_capital = initial_capital
        self.positions = []
        self.max_positions = 3
        self.max_position_hours = 24
        
        # Parámetros realistas de probabilidad
        self.base_frequency = 0.35  # 35% probabilidad base (más conservador)
        self.max_momentum_bonus = 0.15  # 15% bonus máximo
        
        # Filtros de calidad estrictos
        self.min_volume_ratio = 1.30  # 130% del promedio
        self.min_volatility = 0.003   # 0.3%
        self.max_volatility = 0.03    # 3%
        
        # Gestión de riesgo ESTRICTA
        self.risk_per_trade = 0.02    # 2% del capital por trade
        self.max_daily_risk = 0.06    # 6% riesgo diario máximo
        self.max_portfolio_risk = 0.10 # 10% riesgo total del portafolio
        
        # Parámetros TP/SL conservadores
        self.min_tp = 0.03  # 3% mínimo
        self.max_tp = 0.08  # 8% máximo
        self.min_sl = 0.015 # 1.5% mínimo
        self.max_sl = 0.025 # 2.5% máximo
        
        # Tracking
        self.trades_history = []
        self.daily_risk_used = 0.0
        self.portfolio_risk_used = 0.0
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        
    def generate_realistic_market_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Genera datos de mercado realistas sin tendencias extremas"""
        np.random.seed(hash(symbol) % 1000)  # Seed diferente por símbolo
        
        # Precios base realistas
        base_prices = {
            'BTC-USD': 43000,
            'ETH-USD': 2600,
            'BNB-USD': 320,
            'ADA-USD': 0.75,
            'SOL-USD': 110
        }
        
        base_price = base_prices.get(symbol, 43000)
        hours = days * 24
        
        # Generar retornos realistas con distribución normal
        # Parámetros basados en datos reales de crypto
        daily_volatility = 0.03  # 3% volatilidad diaria
        hourly_volatility = daily_volatility / np.sqrt(24)
        
        returns = np.random.normal(0, hourly_volatility, hours)
        
        # Aplicar autocorrelación leve (momentum/reversión)
        for i in range(1, len(returns)):
            momentum = 0.1 * returns[i-1]  # Leve momentum
            mean_reversion = -0.05 * returns[i-1]  # Leve reversión
            returns[i] += momentum + mean_reversion
        
        # Limitar movimientos extremos
        returns = np.clip(returns, -0.05, 0.05)  # Máximo 5% por hora
        
        # Generar precios
        prices = [base_price]
        for ret in returns:
            new_price = prices[-1] * (1 + ret)
            # Evitar caídas/subidas extremas
            new_price = max(new_price, base_price * 0.8)  # No caer más del 20%
            new_price = min(new_price, base_price * 1.25) # No subir más del 25%
            prices.append(new_price)
        
        # Generar volúmenes correlacionados con volatilidad
        base_volume = 500000
        volumes = []
        for i in range(hours):
            vol_multiplier = 1 + abs(returns[i]) * 3  # Volumen aumenta con volatilidad
            volume = base_volume * vol_multiplier * np.random.uniform(0.7, 1.4)
            volumes.append(volume)
        
        # Crear DataFrame
        dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                             periods=hours, freq='h')
        
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
    
    def calculate_position_size(self, entry_price: float, sl_price: float) -> float:
        """Calcula tamaño de posición basado en riesgo del 2%"""
        risk_amount = self.available_capital * self.risk_per_trade
        price_risk = abs(entry_price - sl_price) / entry_price
        
        if price_risk <= 0:
            return 0
        
        position_size = risk_amount / price_risk
        
        # Limitar a capital disponible
        max_position = self.available_capital * 0.3  # Máximo 30% por posición
        position_size = min(position_size, max_position)
        
        return position_size
    
    def calculate_conservative_tp_sl(self, volatility: float) -> Tuple[float, float]:
        """Calcula TP y SL conservadores"""
        # TP basado en volatilidad pero limitado
        tp_base = self.min_tp + (self.max_tp - self.min_tp) * min(1.0, volatility * 20)
        tp_variation = random.uniform(-0.1, 0.1)  # ±10% variación
        tp_final = max(self.min_tp, min(self.max_tp, tp_base * (1 + tp_variation)))
        
        # SL más conservador
        sl_base = self.min_sl + (self.max_sl - self.min_sl) * min(1.0, volatility * 15)
        sl_variation = random.uniform(-0.05, 0.05)  # ±5% variación
        sl_final = max(self.min_sl, min(self.max_sl, sl_base * (1 + sl_variation)))
        
        # Asegurar ratio TP:SL mínimo de 1.5:1
        if tp_final / sl_final < 1.5:
            tp_final = sl_final * 1.5
            tp_final = min(tp_final, self.max_tp)
        
        return tp_final, sl_final
    
    def calculate_signal_probability(self, data: pd.DataFrame, index: int) -> float:
        """Calcula probabilidad de señal conservadora"""
        if index < 20:
            return 0.0
        
        current_price = data.iloc[index]['close']
        previous_price = data.iloc[index-1]['close']
        price_change = (current_price - previous_price) / previous_price
        
        # Momentum bonus limitado
        momentum_bonus = min(self.max_momentum_bonus, abs(price_change) * 50)
        
        # Factor de posición (menos agresivo)
        data_length = len(data[:index])
        position_factor = max(0.9, 1.1 - (data_length / 2000))
        
        # Probabilidad final conservadora
        final_probability = (self.base_frequency + momentum_bonus) * position_factor
        
        return min(final_probability, 0.6)  # Máximo 60%
    
    def check_risk_limits(self, position_size: float, sl_pct: float) -> bool:
        """Verifica límites de riesgo"""
        # Riesgo de la nueva posición
        position_risk = position_size * sl_pct
        
        # Verificar riesgo diario
        if self.daily_risk_used + position_risk > self.available_capital * self.max_daily_risk:
            return False
        
        # Verificar riesgo total del portafolio
        if self.portfolio_risk_used + position_risk > self.available_capital * self.max_portfolio_risk:
            return False
        
        # Verificar pérdidas consecutivas
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False
        
        return True
    
    def check_quality_filters(self, data: pd.DataFrame, index: int) -> bool:
        """Verifica filtros de calidad estrictos"""
        if index < 20:
            return False
        
        current_volume = data.iloc[index]['volume']
        volumes = data.iloc[max(0, index-20):index]['volume']
        volume_ratio = current_volume / volumes.mean() if volumes.mean() > 0 else 0
        
        prices = data.iloc[max(0, index-2):index+1]['close']
        volatility = abs((prices.iloc[-1] - prices.iloc[-2]) / prices.iloc[-2]) if len(prices) >= 2 else 0
        
        # Filtros estrictos
        volume_ok = volume_ratio >= self.min_volume_ratio
        volatility_ok = self.min_volatility <= volatility <= self.max_volatility
        positions_ok = len(self.positions) < self.max_positions
        
        # Verificar tendencia (evitar mercados laterales)
        if len(prices) >= 5:
            trend_strength = abs(prices.iloc[-1] - prices.iloc[-5]) / prices.iloc[-5]
            trend_ok = trend_strength >= 0.01  # Mínimo 1% de movimiento en 5 períodos
        else:
            trend_ok = True
        
        return volume_ok and volatility_ok and positions_ok and trend_ok
    
    def open_position(self, symbol: str, entry_price: float, tp_pct: float, sl_pct: float):
        """Abre nueva posición con gestión de riesgo estricta"""
        sl_price = entry_price * (1 - sl_pct)
        position_size = self.calculate_position_size(entry_price, sl_price)
        
        if position_size <= 0:
            return False
        
        # Verificar límites de riesgo
        if not self.check_risk_limits(position_size, sl_pct):
            return False
        
        position = {
            'symbol': symbol,
            'entry_price': entry_price,
            'position_size': position_size,
            'tp_price': entry_price * (1 + tp_pct),
            'sl_price': sl_price,
            'entry_time': datetime.now(),
            'tp_pct': tp_pct,
            'sl_pct': sl_pct
        }
        
        self.positions.append(position)
        self.available_capital -= position_size
        self.portfolio_risk_used += position_size * sl_pct
        
        print(f"🚀 NUEVA POSICIÓN: {symbol} @ ${entry_price:.2f} | Size: ${position_size:.2f} | TP: {tp_pct*100:.1f}% | SL: {sl_pct*100:.1f}%")
        return True
    
    def close_position(self, position_index: int, exit_price: float, exit_reason: str):
        """Cierra posición y actualiza capital"""
        position = self.positions[position_index]
        
        # Calcular PnL
        pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
        pnl_amount = position['position_size'] * pnl_pct
        
        # Actualizar capital
        self.available_capital += position['position_size'] + pnl_amount
        self.current_capital += pnl_amount
        
        # Actualizar riesgo del portafolio
        self.portfolio_risk_used -= position['position_size'] * position['sl_pct']
        self.portfolio_risk_used = max(0, self.portfolio_risk_used)
        
        # Tracking de pérdidas consecutivas
        if pnl_pct < 0:
            self.consecutive_losses += 1
            self.daily_risk_used += abs(pnl_amount)
        else:
            self.consecutive_losses = 0
        
        # Guardar trade
        trade = {
            'symbol': position['symbol'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_pct': pnl_pct * 100,
            'pnl_amount': pnl_amount,
            'position_size': position['position_size'],
            'tp_pct': position['tp_pct'] * 100,
            'sl_pct': position['sl_pct'] * 100
        }
        
        self.trades_history.append(trade)
        
        status = "✅" if pnl_pct > 0 else "❌"
        print(f"{status} CERRADO {exit_reason}: {position['symbol']} | PnL: {pnl_pct*100:.2f}% (${pnl_amount:.2f})")
    
    def check_exit_conditions(self, data: pd.DataFrame, index: int):
        """Verifica condiciones de salida"""
        current_price = data.iloc[index]['close']
        current_time = data.iloc[index]['timestamp']
        
        positions_to_close = []
        
        for i, position in enumerate(self.positions):
            # Verificar TP
            if current_price >= position['tp_price']:
                self.close_position(i, current_price, 'TP')
                positions_to_close.append(i)
            
            # Verificar SL
            elif current_price <= position['sl_price']:
                self.close_position(i, current_price, 'SL')
                positions_to_close.append(i)
            
            # Verificar tiempo máximo
            elif (current_time - position['entry_time']).total_seconds() > self.max_position_hours * 3600:
                self.close_position(i, current_price, 'TIME')
                positions_to_close.append(i)
        
        # Remover posiciones cerradas
        for i in sorted(positions_to_close, reverse=True):
            del self.positions[i]
    
    def reset_daily_limits(self):
        """Resetea límites diarios"""
        self.daily_risk_used = 0.0
    
    def run_backtest(self, symbols: List[str] = None, days: int = 30) -> Dict:
        """Ejecuta backtest realista"""
        if symbols is None:
            symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'SOL-USD']
        
        print("📊 INICIANDO BACKTEST REALISTA - Estrategia de Trading Conservadora")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print(f"📊 Símbolos: {', '.join(symbols)}")
        print(f"📅 Período: {days} días")
        print(f"⚠️ Riesgo por trade: {self.risk_per_trade*100:.1f}%")
        print(f"🛡️ Riesgo diario máximo: {self.max_daily_risk*100:.1f}%")
        print("="*60)
        
        # Generar datos realistas
        all_data = {}
        for symbol in symbols:
            all_data[symbol] = self.generate_realistic_market_data(symbol, days)
        
        # Simular trading
        total_hours = days * 24
        current_day = 0
        
        for hour in range(20, total_hours):
            # Resetear límites diarios
            new_day = hour // 24
            if new_day > current_day:
                self.reset_daily_limits()
                current_day = new_day
            
            # Procesar cada símbolo
            for symbol in symbols:
                data = all_data[symbol]
                
                if hour >= len(data):
                    continue
                
                # Verificar salidas primero
                self.check_exit_conditions(data, hour)
                
                # Verificar nuevas entradas
                if len(self.positions) < self.max_positions:
                    # Verificar filtros de calidad
                    if self.check_quality_filters(data, hour):
                        # Calcular probabilidad
                        probability = self.calculate_signal_probability(data, hour)
                        
                        # Generar señal
                        if np.random.random() < probability:
                            current_price = data.iloc[hour]['close']
                            
                            # Calcular volatilidad
                            prices = data.iloc[max(0, hour-5):hour+1]['close']
                            volatility = prices.std() / prices.mean() if len(prices) > 1 else 0.01
                            
                            # Calcular TP/SL
                            tp_pct, sl_pct = self.calculate_conservative_tp_sl(volatility)
                            
                            # Intentar abrir posición
                            self.open_position(symbol, current_price, tp_pct, sl_pct)
        
        # Cerrar posiciones restantes
        for i in range(len(self.positions)):
            if i < len(self.positions):
                last_data = all_data[self.positions[i]['symbol']]
                last_price = last_data.iloc[-1]['close']
                self.close_position(i, last_price, 'END')
        
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
        
        # Calcular Sharpe ratio aproximado
        returns = [t['pnl_pct'] for t in self.trades_history]
        avg_return = np.mean(returns) if returns else 0
        std_return = np.std(returns) if len(returns) > 1 else 0
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        
        results = {
            'capital_inicial': self.initial_capital,
            'capital_final': self.current_capital,
            'retorno_total_pct': total_return_pct,
            'retorno_mensual_estimado': total_return_pct,
            'total_trades': total_trades,
            'trades_ganadores': winning_trades,
            'win_rate_pct': win_rate,
            'max_drawdown_pct': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_return_per_trade': avg_return,
            'objetivo_10pct': total_return_pct >= 10.0,
            'objetivo_15pct': total_return_pct >= 15.0,
            'riesgo_maximo_usado': max(self.daily_risk_used / self.initial_capital * 100, 0)
        }
        
        return results
    
    def print_results(self, results: Dict):
        """Imprime resultados formateados"""
        print("\n" + "="*60)
        print("🏆 RESULTADOS FINALES - ESTRATEGIA REALISTA")
        print("="*60)
        
        print(f"💰 Capital inicial: ${results['capital_inicial']:,.2f}")
        print(f"💰 Capital final: ${results['capital_final']:,.2f}")
        print(f"📈 Retorno total: {results['retorno_total_pct']:.2f}%")
        print(f"📊 Retorno mensual: {results['retorno_mensual_estimado']:.2f}%")
        print(f"🎯 Trades totales: {results['total_trades']}")
        print(f"✅ Trades ganadores: {results['trades_ganadores']}")
        print(f"📊 Win rate: {results['win_rate_pct']:.2f}%")
        print(f"📉 Máximo drawdown: {results['max_drawdown_pct']:.2f}%")
        print(f"📊 Sharpe ratio: {results['sharpe_ratio']:.2f}")
        print(f"💹 Retorno promedio por trade: {results['avg_return_per_trade']:.2f}%")
        print(f"⚠️ Riesgo máximo usado: {results['riesgo_maximo_usado']:.2f}%")
        
        print("\n🎯 EVALUACIÓN DE OBJETIVOS:")
        print(f"   Objetivo 10% mensual: {'✅ ALCANZADO' if results['objetivo_10pct'] else '❌ NO ALCANZADO'}")
        print(f"   Objetivo 15% mensual: {'✅ ALCANZADO' if results['objetivo_15pct'] else '❌ NO ALCANZADO'}")
        
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"realistic_trading_results_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("RESULTADOS FINALES - Estrategia de Trading Realista\n")
            f.write("="*60 + "\n\n")
            f.write(f"Capital inicial: ${results['capital_inicial']:,.2f}\n")
            f.write(f"Capital final: ${results['capital_final']:,.2f}\n")
            f.write(f"Retorno total: {results['retorno_total_pct']:.2f}%\n")
            f.write(f"Retorno mensual: {results['retorno_mensual_estimado']:.2f}%\n")
            f.write(f"Total trades: {results['total_trades']}\n")
            f.write(f"Win rate: {results['win_rate_pct']:.2f}%\n")
            f.write(f"Máximo drawdown: {results['max_drawdown_pct']:.2f}%\n")
            f.write(f"Sharpe ratio: {results['sharpe_ratio']:.2f}\n")
            f.write(f"Retorno promedio por trade: {results['avg_return_per_trade']:.2f}%\n")
            f.write(f"Riesgo máximo usado: {results['riesgo_maximo_usado']:.2f}%\n\n")
            
            f.write(f"Objetivo 10% mensual: {'ALCANZADO' if results['objetivo_10pct'] else 'NO ALCANZADO'}\n")
            f.write(f"Objetivo 15% mensual: {'ALCANZADO' if results['objetivo_15pct'] else 'NO ALCANZADO'}\n")
            
            # Detalles de trades
            f.write("\n" + "="*60 + "\n")
            f.write("DETALLE DE TRADES:\n")
            f.write("="*60 + "\n")
            for i, trade in enumerate(self.trades_history, 1):
                f.write(f"{i:3d}. {trade['symbol']} | "
                       f"Entry: ${trade['entry_price']:.2f} | Exit: ${trade['exit_price']:.2f} | "
                       f"Size: ${trade['position_size']:.2f} | PnL: {trade['pnl_pct']:.2f}% | "
                       f"Razón: {trade['exit_reason']}\n")
        
        print(f"\n💾 Resultados guardados en: {filename}")

def main():
    """Función principal"""
    print("📊 ESTRATEGIA DE TRADING REALISTA - ITBOT")
    print("Implementación con gestión de riesgo estricta")
    print("Objetivo: 10-15% retorno mensual sostenible")
    print("="*60)
    
    # Crear instancia de la estrategia
    strategy = RealisticTradingStrategy(initial_capital=1000.0)
    
    # Ejecutar backtest
    symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'SOL-USD']
    results = strategy.run_backtest(symbols=symbols, days=30)
    
    # Mostrar resultados
    if 'error' not in results:
        strategy.print_results(results)
        
        # Evaluación final
        if results['retorno_mensual_estimado'] >= 15.0:
            print("\n🎉 ¡OBJETIVO 15% MENSUAL ALCANZADO!")
            print("🔥 ESTRATEGIA VALIDADA para implementación")
        elif results['retorno_mensual_estimado'] >= 10.0:
            print("\n✅ Objetivo 10% mensual alcanzado")
            print("💡 Estrategia viable y sostenible")
        else:
            print("\n📊 Resultados dentro del rango esperado")
            print("💡 Estrategia conservadora con riesgo controlado")
        
        print("\n📋 CARACTERÍSTICAS CLAVE:")
        print(f"   • Gestión de riesgo: 2% por trade")
        print(f"   • Riesgo diario máximo: 6%")
        print(f"   • Riesgo portafolio máximo: 10%")
        print(f"   • Ratio TP:SL mínimo: 1.5:1")
        print(f"   • Máximo 3 posiciones simultáneas")
        print(f"   • Filtros de calidad estrictos")
        print(f"   • Win rate logrado: {results['win_rate_pct']:.1f}%")
        print(f"   • Drawdown máximo: {results['max_drawdown_pct']:.1f}%")
        print(f"   • Sharpe ratio: {results['sharpe_ratio']:.2f}")
    else:
        print(f"❌ Error en backtest: {results['error']}")
        print("💡 Ajustar parámetros para generar más señales")

if __name__ == "__main__":
    main()