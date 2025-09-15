# nas100_simple_backtest.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleNAS100Strategy:
    """
    Estrategia simplificada para NAS100 sin dependencias externas complejas
    """
    
    def __init__(self):
        self.name = "SimpleNAS100Strategy"
        self.momentum_period_short = 5
        self.momentum_period_long = 20
        self.momentum_threshold = 0.015
        self.volatility_period = 14
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
    Backtester simplificado sin dependencias externas
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

def generate_nas100_data(days: int = 90, start_price: float = 15000.0) -> pd.DataFrame:
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
    for i in range(0, periods, 1):  # Cada vela de 5 minutos
        if i < periods:
            # Simular OHLC basado en el precio de cierre
            close_price = prices[i]
            volatility_range = close_price * 0.002  # 0.2% range
            
            high = close_price + np.random.uniform(0, volatility_range)
            low = close_price - np.random.uniform(0, volatility_range)
            open_price = close_price + np.random.uniform(-volatility_range/2, volatility_range/2)
            
            # Asegurar que OHLC sea consistente
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

def plot_results(data: pd.DataFrame, results: Dict[str, Any]):
    """Genera gráficos de resultados"""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('Resultados Backtest Estrategia NAS100', fontsize=16)
    
    # Precio y señales
    ax1.plot(data.index, data['close'], label='NAS100 Price', alpha=0.7)
    
    trades = results.get('trades', [])
    buy_signals = [t for t in trades if t['action'] == 'BUY']
    sell_signals = [t for t in trades if t['action'] == 'SELL']
    
    if buy_signals:
        buy_times = [pd.to_datetime(t['timestamp']) for t in buy_signals]
        buy_prices = [t['price'] for t in buy_signals]
        ax1.scatter(buy_times, buy_prices, color='green', marker='^', s=30, label='Compra')
    
    if sell_signals:
        sell_times = [pd.to_datetime(t['timestamp']) for t in sell_signals]
        sell_prices = [t['price'] for t in sell_signals]
        ax1.scatter(sell_times, sell_prices, color='red', marker='v', s=30, label='Venta')
    
    ax1.set_title('Precio NAS100 y Señales')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Evolución del balance
    balance_history = results.get('balance_history', [])
    if balance_history:
        ax2.plot(balance_history)
        ax2.axhline(y=results['initial_balance'], color='gray', linestyle='--')
        ax2.set_title('Evolución del Balance')
        ax2.set_ylabel('Balance ($)')
        ax2.grid(True, alpha=0.3)
    
    # Distribución P&L
    completed_trades = [t for t in trades if 'pnl' in t]
    if completed_trades:
        pnl_values = [t['pnl'] for t in completed_trades]
        ax3.hist(pnl_values, bins=15, alpha=0.7, edgecolor='black')
        ax3.axvline(x=0, color='red', linestyle='--')
        ax3.set_title('Distribución P&L por Trade')
        ax3.set_xlabel('P&L ($)')
        ax3.grid(True, alpha=0.3)
    
    # Métricas clave
    metrics_text = f"""Retorno Total: {results['total_return']:.2%}
Total Trades: {results['total_trades']}
Win Rate: {results['win_rate']:.2%}
Max Drawdown: {results['max_drawdown']:.2%}"""
    
    ax4.text(0.1, 0.5, metrics_text, transform=ax4.transAxes, fontsize=12,
             verticalalignment='center', bbox=dict(boxstyle='round', facecolor='lightgray'))
    ax4.set_title('Métricas Clave')
    ax4.axis('off')
    
    plt.tight_layout()
    plt.savefig('nas100_backtest_results.png', dpi=150, bbox_inches='tight')
    plt.show()

def print_summary(results: Dict[str, Any]):
    """Imprime resumen de resultados"""
    print("\n" + "="*50)
    print("RESUMEN BACKTEST ESTRATEGIA NAS100")
    print("="*50)
    
    print(f"\nRESULTADOS GENERALES:")
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return']:.2%}")
    print(f"Máximo drawdown: {results['max_drawdown']:.2%}")
    
    print(f"\nESTADÍSTICAS DE TRADING:")
    print(f"Total trades: {results['total_trades']}")
    print(f"Trades ganadores: {results['winning_trades']}")
    print(f"Trades perdedores: {results['losing_trades']}")
    print(f"Win rate: {results['win_rate']:.2%}")
    
    if results['total_trades'] > 0:
        avg_pnl = results['total_pnl'] / results['total_trades']
        print(f"P&L promedio por trade: ${avg_pnl:,.2f}")
    
    print("\n" + "="*50)

def main():
    """Función principal"""
    print("Iniciando backtest simplificado de estrategia NAS100...")
    
    # Generar datos
    data = generate_nas100_data(days=60, start_price=15000.0)
    
    # Crear estrategia y backtester
    strategy = SimpleNAS100Strategy()
    backtester = SimpleBacktester(initial_balance=100000.0)
    
    # Ejecutar backtest
    results = backtester.run_backtest(strategy, data)
    
    # Mostrar resultados
    print_summary(results)
    
    # Generar gráficos
    plot_results(data, results)
    
    return results

if __name__ == "__main__":
    results = main()