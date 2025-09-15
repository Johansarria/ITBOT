# nas100_test.py - Prueba rápida de la estrategia NAS100

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleNAS100Strategy:
    """
    Estrategia simplificada para NAS100
    """
    
    def __init__(self):
        self.name = "SimpleNAS100Strategy"
        self.momentum_period_short = 5
        self.momentum_period_long = 20
        self.momentum_threshold = 0.015
        self.breakout_period = 10
        self.breakout_threshold = 0.02
        
    def calculate_momentum_score(self, data: pd.DataFrame) -> float:
        """Calcula score de momentum"""
        if len(data) < self.momentum_period_long:
            return 0.0
            
        current_price = data['close'].iloc[-1]
        short_price = data['close'].iloc[-self.momentum_period_short]
        long_price = data['close'].iloc[-self.momentum_period_long]
        
        short_momentum = (current_price / short_price) - 1
        long_momentum = (current_price / long_price) - 1
        
        return (short_momentum * 0.7) + (long_momentum * 0.3)
    
    def detect_breakout(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Detecta breakouts"""
        if len(data) < self.breakout_period + 1:
            return {"breakout": False, "direction": None, "strength": 0}
            
        recent_data = data.tail(self.breakout_period)
        resistance = recent_data['high'].max()
        support = recent_data['low'].min()
        current_price = data['close'].iloc[-1]
        
        if current_price > resistance * (1 + self.breakout_threshold):
            return {
                "breakout": True,
                "direction": "bullish",
                "strength": min(((current_price / resistance) - 1) * 10, 3.0)
            }
        elif current_price < support * (1 - self.breakout_threshold):
            return {
                "breakout": True,
                "direction": "bearish",
                "strength": min(((support / current_price) - 1) * 10, 3.0)
            }
            
        return {"breakout": False, "direction": None, "strength": 0}
    
    def is_ny_session(self, timestamp: pd.Timestamp) -> bool:
        """Verifica si estamos en sesión NY"""
        hour = timestamp.hour + timestamp.minute / 60.0
        return 9.5 <= hour <= 16.0
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Análisis principal"""
        if len(data) < max(self.momentum_period_long, self.breakout_period):
            return {"decision": "MANTENER", "score": 0, "reason": "Datos insuficientes"}
        
        current_timestamp = pd.Timestamp.now()
        momentum_score = self.calculate_momentum_score(data)
        breakout_info = self.detect_breakout(data)
        in_ny_session = self.is_ny_session(current_timestamp)
        
        total_score = 0
        signals = []
        
        # Factor de sesión
        session_multiplier = 1.5 if in_ny_session else 0.8
        
        # Señal de momentum
        if abs(momentum_score) > self.momentum_threshold:
            momentum_signal = np.sign(momentum_score) * min(abs(momentum_score) / self.momentum_threshold, 2.0)
            total_score += momentum_signal * session_multiplier
            signals.append(f"Momentum: {momentum_score:.3f}")
        
        # Señal de breakout
        if breakout_info["breakout"]:
            breakout_signal = breakout_info["strength"]
            if breakout_info["direction"] == "bullish":
                total_score += breakout_signal
                signals.append(f"Breakout alcista: {breakout_signal:.2f}")
            elif breakout_info["direction"] == "bearish":
                total_score -= breakout_signal
                signals.append(f"Breakout bajista: {breakout_signal:.2f}")
        
        # Determinar decisión
        if total_score > 1.0:
            decision = "COMPRAR"
        elif total_score < -1.0:
            decision = "VENDER"
        else:
            decision = "MANTENER"
        
        return {
            "decision": decision,
            "score": round(total_score, 3),
            "momentum_score": round(momentum_score, 4),
            "in_ny_session": in_ny_session,
            "breakout_detected": breakout_info["breakout"],
            "signals": signals
        }

class SimpleBacktester:
    """
    Backtester simplificado
    """
    
    def __init__(self, initial_balance: float = 100000.0, commission: float = 0.001):
        self.initial_balance = initial_balance
        self.commission = commission
        self.reset()
    
    def reset(self):
        self.balance = self.initial_balance
        self.position = 0
        self.position_value = 0
        self.trades = []
        self.balance_history = [self.initial_balance]
    
    def execute_trade(self, action: str, price: float, timestamp: str, quantity: float = None):
        """Ejecuta una operación"""
        if quantity is None:
            # Usar 10% del balance para cada operación
            quantity = (self.balance * 0.1) / price
        
        commission_cost = quantity * price * self.commission
        
        if action == "COMPRAR" and self.position <= 0:
            cost = quantity * price + commission_cost
            if cost <= self.balance:
                self.balance -= cost
                self.position += quantity
                self.position_value = quantity * price
                
                self.trades.append({
                    'timestamp': timestamp,
                    'action': 'BUY',
                    'price': price,
                    'quantity': quantity,
                    'commission': commission_cost,
                    'balance': self.balance
                })
        
        elif action == "VENDER" and self.position > 0:
            proceeds = self.position * price - commission_cost
            pnl = proceeds - self.position_value
            
            self.balance += proceeds
            
            self.trades.append({
                'timestamp': timestamp,
                'action': 'SELL',
                'price': price,
                'quantity': self.position,
                'commission': commission_cost,
                'pnl': pnl,
                'balance': self.balance
            })
            
            self.position = 0
            self.position_value = 0
    
    def run_backtest(self, strategy, data: pd.DataFrame) -> Dict[str, Any]:
        """Ejecuta el backtest"""
        logger.info(f"Iniciando backtest con {len(data)} puntos de datos")
        
        for i in range(max(strategy.momentum_period_long, strategy.breakout_period), len(data)):
            current_data = data.iloc[:i+1]
            analysis = strategy.analyze(current_data)
            
            current_price = data.iloc[i]['close']
            timestamp = str(data.index[i])
            
            if analysis['decision'] in ['COMPRAR', 'VENDER']:
                self.execute_trade(analysis['decision'], current_price, timestamp)
            
            # Actualizar valor total
            total_value = self.balance + (self.position * current_price)
            self.balance_history.append(total_value)
        
        # Cerrar posición final si existe
        if self.position > 0:
            final_price = data.iloc[-1]['close']
            self.execute_trade("VENDER", final_price, str(data.index[-1]))
        
        return self.calculate_results()
    
    def calculate_results(self) -> Dict[str, Any]:
        """Calcula métricas de resultado"""
        final_balance = self.balance_history[-1]
        total_return = (final_balance / self.initial_balance) - 1
        
        # Calcular trades ganadores/perdedores
        completed_trades = [t for t in self.trades if 'pnl' in t]
        winning_trades = len([t for t in completed_trades if t['pnl'] > 0])
        losing_trades = len([t for t in completed_trades if t['pnl'] < 0])
        total_trades = len(completed_trades)
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        total_pnl = sum(t['pnl'] for t in completed_trades)
        
        # Calcular drawdown
        peak = self.initial_balance
        max_drawdown = 0
        for balance in self.balance_history:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_return': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'balance_history': self.balance_history,
            'trades': self.trades
        }

def generate_nas100_data(days: int = 30, start_price: float = 15000.0) -> pd.DataFrame:
    """Genera datos simulados del NAS100"""
    logger.info(f"Generando {days} días de datos simulados para NAS100")
    
    periods = days * 288  # 5-minute candles (288 per day)
    start_date = datetime.now() - timedelta(days=days)
    timestamps = pd.date_range(start=start_date, periods=periods, freq='5min')
    
    prices = np.zeros(periods)
    prices[0] = start_price
    
    base_volatility = 0.001
    trend_persistence = 0.02
    current_trend = 0.0
    
    for i in range(1, periods):
        timestamp = timestamps[i]
        hour = timestamp.hour + timestamp.minute / 60.0
        
        # Mayor volatilidad en sesión NY
        if 9.5 <= hour <= 16.0:
            volatility = base_volatility * 2.0
        else:
            volatility = base_volatility * 0.6
        
        # Evolución de tendencia
        trend_change = np.random.normal(0, 0.0005)
        current_trend = current_trend * (1 - trend_persistence) + trend_change
        current_trend = np.clip(current_trend, -0.002, 0.002)
        
        # Cambio de precio
        random_component = np.random.normal(0, volatility)
        price_change = current_trend + random_component
        
        new_price = prices[i-1] * (1 + price_change)
        prices[i] = max(new_price, 100)
    
    # Crear OHLCV data
    data = []
    for i in range(0, periods, 1):
        if i < periods:
            close_price = prices[i]
            volatility_range = close_price * 0.002
            
            high = close_price + np.random.uniform(0, volatility_range)
            low = close_price - np.random.uniform(0, volatility_range)
            open_price = close_price + np.random.uniform(-volatility_range/2, volatility_range/2)
            
            high = max(high, open_price, close_price)
            low = min(low, open_price, close_price)
            
            volume = np.random.randint(500000, 2000000)
            
            data.append({
                'timestamp': timestamps[i],
                'open': open_price,
                'high': high,
                'low': low,
                'close': close_price,
                'volume': volume
            })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    logger.info(f"Datos generados: {len(df)} velas")
    logger.info(f"Rango de precios: {df['low'].min():.2f} - {df['high'].max():.2f}")
    
    return df

def print_summary(results: Dict[str, Any]):
    """Imprime resumen de resultados"""
    print("\n" + "="*60)
    print("RESUMEN BACKTEST ESTRATEGIA NAS100")
    print("="*60)
    
    print(f"\n📊 RESULTADOS GENERALES:")
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return']:.2%}")
    print(f"Máximo drawdown: {results['max_drawdown']:.2%}")
    
    # Calcular retorno anualizado aproximado
    if results['total_return'] != 0:
        days_simulated = 30  # Aproximadamente
        annualized_return = ((1 + results['total_return']) ** (365/days_simulated)) - 1
        print(f"Retorno anualizado estimado: {annualized_return:.2%}")
    
    print(f"\n📈 ESTADÍSTICAS DE TRADING:")
    print(f"Total trades: {results['total_trades']}")
    print(f"Trades ganadores: {results['winning_trades']}")
    print(f"Trades perdedores: {results['losing_trades']}")
    print(f"Win rate: {results['win_rate']:.2%}")
    
    if results['total_trades'] > 0:
        avg_pnl = results['total_pnl'] / results['total_trades']
        print(f"P&L promedio por trade: ${avg_pnl:,.2f}")
        
        # Profit factor
        winning_pnl = sum(t['pnl'] for t in results['trades'] if 'pnl' in t and t['pnl'] > 0)
        losing_pnl = abs(sum(t['pnl'] for t in results['trades'] if 'pnl' in t and t['pnl'] < 0))
        
        if losing_pnl > 0:
            profit_factor = winning_pnl / losing_pnl
            print(f"Profit factor: {profit_factor:.2f}")
    
    print(f"\n💰 ANÁLISIS DE RENDIMIENTO:")
    if results['total_return'] > 0.15:  # 15%+
        print("✅ EXCELENTE: Retorno superior al 15% objetivo")
    elif results['total_return'] > 0.10:  # 10%+
        print("✅ BUENO: Retorno sólido por encima del 10%")
    elif results['total_return'] > 0.05:  # 5%+
        print("⚠️ MODERADO: Retorno positivo pero mejorable")
    elif results['total_return'] > 0:
        print("⚠️ BAJO: Retorno positivo pero insuficiente")
    else:
        print("❌ PÉRDIDAS: La estrategia necesita optimización")
    
    if results['win_rate'] > 0.6:
        print("✅ Win rate excelente (>60%)")
    elif results['win_rate'] > 0.5:
        print("✅ Win rate bueno (>50%)")
    else:
        print("⚠️ Win rate bajo (<50%) - revisar estrategia")
    
    if results['max_drawdown'] < 0.05:
        print("✅ Drawdown bajo (<5%) - riesgo controlado")
    elif results['max_drawdown'] < 0.10:
        print("⚠️ Drawdown moderado (<10%)")
    else:
        print("❌ Drawdown alto (>10%) - revisar gestión de riesgo")
    
    print("\n" + "="*60)
    
    # Mostrar algunos trades de ejemplo
    completed_trades = [t for t in results['trades'] if 'pnl' in t]
    if completed_trades:
        print("\n📋 ÚLTIMOS 5 TRADES COMPLETADOS:")
        for trade in completed_trades[-5:]:
            pnl_symbol = "📈" if trade['pnl'] > 0 else "📉"
            print(f"{pnl_symbol} {trade['timestamp'][:16]} - P&L: ${trade['pnl']:,.2f}")

def main():
    """Función principal"""
    print("🚀 Iniciando backtest de estrategia NAS100...")
    
    # Generar datos
    data = generate_nas100_data(days=30, start_price=15000.0)
    
    # Crear estrategia y backtester
    strategy = SimpleNAS100Strategy()
    backtester = SimpleBacktester(initial_balance=100000.0)
    
    # Ejecutar backtest
    results = backtester.run_backtest(strategy, data)
    
    # Mostrar resultados
    print_summary(results)
    
    # Guardar resultados básicos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"nas100_results_{timestamp}.txt"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS BACKTEST ESTRATEGIA NAS100\n")
        f.write("=" * 40 + "\n\n")
        f.write(f"Balance inicial: ${results['initial_balance']:,.2f}\n")
        f.write(f"Balance final: ${results['final_balance']:,.2f}\n")
        f.write(f"Retorno total: {results['total_return']:.2%}\n")
        f.write(f"Total trades: {results['total_trades']}\n")
        f.write(f"Win rate: {results['win_rate']:.2%}\n")
        f.write(f"Max drawdown: {results['max_drawdown']:.2%}\n")
    
    print(f"\n💾 Resultados guardados en: {results_file}")
    
    return results

if __name__ == "__main__":
    results = main()