# nas100_backtest.py

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any

from strategies.nas100_strategy import NAS100Strategy
from strategies.backtester import Backtester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_nas100_mock_data(days: int = 252, start_price: float = 15000.0) -> pd.DataFrame:
    """
    Genera datos simulados del NAS100 con características realistas:
    - Volatilidad intradiaria más alta durante sesión NY
    - Tendencias de momentum
    - Gaps ocasionales
    - Patrones de volumen realistas
    """
    logger.info(f"Generando {days} días de datos simulados para NAS100")
    
    # Configuración base
    minutes_per_day = 1440  # 24 horas * 60 minutos
    total_minutes = days * minutes_per_day
    
    # Crear timestamps
    start_date = datetime.now() - timedelta(days=days)
    timestamps = pd.date_range(start=start_date, periods=total_minutes, freq='1min')
    
    # Inicializar arrays
    prices = np.zeros(total_minutes)
    volumes = np.zeros(total_minutes)
    prices[0] = start_price
    
    # Parámetros de simulación
    base_volatility = 0.0002  # Volatilidad base por minuto
    ny_session_vol_multiplier = 2.5  # Mayor volatilidad en sesión NY
    trend_persistence = 0.02  # Persistencia de tendencias
    gap_probability = 0.001  # Probabilidad de gap por minuto
    
    # Variables de estado
    current_trend = 0.0
    trend_strength = 0.0
    
    for i in range(1, total_minutes):
        timestamp = timestamps[i]
        hour = timestamp.hour + timestamp.minute / 60.0
        
        # Determinar si estamos en sesión NY (9:30 AM - 4:00 PM EST)
        in_ny_session = 9.5 <= hour <= 16.0
        in_high_vol_period = 9.5 <= hour <= 10.5  # Primera hora
        
        # Ajustar volatilidad según sesión
        if in_ny_session:
            volatility = base_volatility * ny_session_vol_multiplier
            if in_high_vol_period:
                volatility *= 1.5
        else:
            volatility = base_volatility * 0.6
        
        # Evolución de tendencia (momentum)
        trend_change = np.random.normal(0, 0.001)
        current_trend = current_trend * (1 - trend_persistence) + trend_change
        current_trend = np.clip(current_trend, -0.002, 0.002)
        
        # Calcular cambio de precio
        random_component = np.random.normal(0, volatility)
        price_change = current_trend + random_component
        
        # Aplicar gaps ocasionales (más probables en apertura)
        if np.random.random() < gap_probability:
            gap_size = np.random.normal(0, volatility * 5)
            price_change += gap_size
        
        # Actualizar precio
        new_price = prices[i-1] * (1 + price_change)
        prices[i] = max(new_price, 100)  # Precio mínimo de seguridad
        
        # Generar volumen (mayor durante sesión NY)
        base_volume = 1000000
        if in_ny_session:
            volume_multiplier = np.random.uniform(1.5, 3.0)
            if in_high_vol_period:
                volume_multiplier *= 1.8
        else:
            volume_multiplier = np.random.uniform(0.3, 0.8)
        
        # Volumen correlacionado con volatilidad
        volatility_factor = min(abs(price_change) / volatility, 3.0)
        volumes[i] = int(base_volume * volume_multiplier * (1 + volatility_factor))
    
    # Crear DataFrame con OHLCV
    data = []
    for i in range(0, total_minutes, 5):  # Agrupar en velas de 5 minutos
        end_idx = min(i + 5, total_minutes)
        period_prices = prices[i:end_idx]
        period_volumes = volumes[i:end_idx]
        
        if len(period_prices) > 0:
            data.append({
                'timestamp': timestamps[i],
                'open': period_prices[0],
                'high': period_prices.max(),
                'low': period_prices.min(),
                'close': period_prices[-1],
                'volume': period_volumes.sum()
            })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    
    logger.info(f"Datos generados: {len(df)} velas de 5 minutos")
    logger.info(f"Rango de precios: {df['low'].min():.2f} - {df['high'].max():.2f}")
    logger.info(f"Precio final: {df['close'].iloc[-1]:.2f}")
    
    return df

def run_nas100_backtest(data: pd.DataFrame, initial_balance: float = 100000.0) -> Dict[str, Any]:
    """
    Ejecuta backtest completo de la estrategia NAS100
    """
    logger.info("Iniciando backtest de estrategia NAS100")
    
    strategy = NAS100Strategy()
    backtester = Backtester(initial_balance=initial_balance)
    
    # Ejecutar backtest
    results = backtester.run_backtest(strategy, data)
    
    # Calcular métricas adicionales específicas para NAS100
    trades = results.get('trades', [])
    if trades:
        # Análisis por sesiones
        ny_session_trades = []
        other_session_trades = []
        
        for trade in trades:
            trade_time = pd.to_datetime(trade['timestamp'])
            hour = trade_time.hour + trade_time.minute / 60.0
            
            if 9.5 <= hour <= 16.0:  # Sesión NY
                ny_session_trades.append(trade)
            else:
                other_session_trades.append(trade)
        
        # Métricas por sesión
        ny_session_pnl = sum(t['pnl'] for t in ny_session_trades)
        other_session_pnl = sum(t['pnl'] for t in other_session_trades)
        
        results['ny_session_trades'] = len(ny_session_trades)
        results['other_session_trades'] = len(other_session_trades)
        results['ny_session_pnl'] = ny_session_pnl
        results['other_session_pnl'] = other_session_pnl
        
        if ny_session_trades:
            results['ny_session_win_rate'] = len([t for t in ny_session_trades if t['pnl'] > 0]) / len(ny_session_trades)
        
        if other_session_trades:
            results['other_session_win_rate'] = len([t for t in other_session_trades if t['pnl'] > 0]) / len(other_session_trades)
    
    return results

def plot_backtest_results(data: pd.DataFrame, results: Dict[str, Any]):
    """
    Genera gráficos de los resultados del backtest
    """
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle('Resultados Backtest Estrategia NAS100', fontsize=16)
    
    # Gráfico 1: Precio y señales
    ax1.plot(data.index, data['close'], label='NAS100 Price', alpha=0.7)
    
    trades = results.get('trades', [])
    buy_signals = [t for t in trades if t['action'] == 'BUY']
    sell_signals = [t for t in trades if t['action'] == 'SELL']
    
    if buy_signals:
        buy_times = [pd.to_datetime(t['timestamp']) for t in buy_signals]
        buy_prices = [t['price'] for t in buy_signals]
        ax1.scatter(buy_times, buy_prices, color='green', marker='^', s=50, label='Compra')
    
    if sell_signals:
        sell_times = [pd.to_datetime(t['timestamp']) for t in sell_signals]
        sell_prices = [t['price'] for t in sell_signals]
        ax1.scatter(sell_times, sell_prices, color='red', marker='v', s=50, label='Venta')
    
    ax1.set_title('Precio NAS100 y Señales de Trading')
    ax1.set_ylabel('Precio')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Gráfico 2: Evolución del balance
    balance_history = results.get('balance_history', [])
    if balance_history:
        ax2.plot(balance_history, label='Balance')
        ax2.axhline(y=results['initial_balance'], color='gray', linestyle='--', label='Balance Inicial')
        ax2.set_title('Evolución del Balance')
        ax2.set_ylabel('Balance ($)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    # Gráfico 3: Distribución de P&L por trade
    if trades:
        pnl_values = [t['pnl'] for t in trades]
        ax3.hist(pnl_values, bins=20, alpha=0.7, edgecolor='black')
        ax3.axvline(x=0, color='red', linestyle='--', label='Break Even')
        ax3.set_title('Distribución P&L por Trade')
        ax3.set_xlabel('P&L ($)')
        ax3.set_ylabel('Frecuencia')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    
    # Gráfico 4: Métricas por sesión
    sessions = ['Sesión NY', 'Otras Sesiones']
    ny_trades = results.get('ny_session_trades', 0)
    other_trades = results.get('other_session_trades', 0)
    
    if ny_trades > 0 or other_trades > 0:
        trade_counts = [ny_trades, other_trades]
        ax4.bar(sessions, trade_counts, alpha=0.7)
        ax4.set_title('Trades por Sesión')
        ax4.set_ylabel('Número de Trades')
        
        # Añadir win rates si están disponibles
        ny_wr = results.get('ny_session_win_rate', 0)
        other_wr = results.get('other_session_win_rate', 0)
        
        for i, (count, wr) in enumerate(zip(trade_counts, [ny_wr, other_wr])):
            if count > 0:
                ax4.text(i, count + max(trade_counts) * 0.02, f'WR: {wr:.1%}', 
                        ha='center', va='bottom')
    
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def print_backtest_summary(results: Dict[str, Any]):
    """
    Imprime resumen detallado de los resultados
    """
    print("\n" + "="*60)
    print("RESUMEN BACKTEST ESTRATEGIA NAS100")
    print("="*60)
    
    print(f"\nRESULTADOS GENERALES:")
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return']:.2%}")
    print(f"Retorno anualizado: {results.get('annualized_return', 0):.2%}")
    print(f"Máximo drawdown: {results.get('max_drawdown', 0):.2%}")
    print(f"Ratio Sharpe: {results.get('sharpe_ratio', 0):.2f}")
    
    print(f"\nESTADÍSTICAS DE TRADING:")
    print(f"Total trades: {results['total_trades']}")
    print(f"Trades ganadores: {results['winning_trades']}")
    print(f"Trades perdedores: {results['losing_trades']}")
    print(f"Win rate: {results['win_rate']:.2%}")
    print(f"Profit factor: {results.get('profit_factor', 0):.2f}")
    
    if results['total_trades'] > 0:
        print(f"P&L promedio por trade: ${results['total_pnl'] / results['total_trades']:,.2f}")
    
    print(f"\nANÁLISIS POR SESIONES:")
    print(f"Trades en sesión NY: {results.get('ny_session_trades', 0)}")
    print(f"Trades en otras sesiones: {results.get('other_session_trades', 0)}")
    print(f"P&L sesión NY: ${results.get('ny_session_pnl', 0):,.2f}")
    print(f"P&L otras sesiones: ${results.get('other_session_pnl', 0):,.2f}")
    
    if results.get('ny_session_trades', 0) > 0:
        print(f"Win rate sesión NY: {results.get('ny_session_win_rate', 0):.2%}")
    if results.get('other_session_trades', 0) > 0:
        print(f"Win rate otras sesiones: {results.get('other_session_win_rate', 0):.2%}")
    
    print("\n" + "="*60)

def main():
    """
    Función principal para ejecutar el backtest completo
    """
    print("Iniciando backtest de estrategia NAS100...")
    
    # Generar datos de prueba
    data = generate_nas100_mock_data(days=90, start_price=15000.0)  # 3 meses de datos
    
    # Ejecutar backtest
    results = run_nas100_backtest(data, initial_balance=100000.0)
    
    # Mostrar resultados
    print_backtest_summary(results)
    
    # Generar gráficos
    plot_backtest_results(data, results)
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"nas100_backtest_results_{timestamp}.txt"
    
    with open(results_file, 'w') as f:
        f.write("RESULTADOS BACKTEST ESTRATEGIA NAS100\n")
        f.write("="*50 + "\n\n")
        for key, value in results.items():
            if isinstance(value, (int, float)):
                f.write(f"{key}: {value}\n")
            elif isinstance(value, list) and len(value) < 10:  # Solo listas pequeñas
                f.write(f"{key}: {value}\n")
    
    print(f"\nResultados guardados en: {results_file}")
    
    return results

if __name__ == "__main__":
    results = main()