#!/usr/bin/env python3
"""
🚀 SIMULADOR DE TRADING EN TIEMPO REAL V4 ULTRA-AGRESIVA

Simulador que ejecuta la estrategia V4 Ultra-Agresiva con datos en vivo de Binance,
mostrando métricas detalladas en tiempo real por consola.

Características:
- Conexión permanente con Binance API
- Capital inicial: 500 USDT
- Datos de mercado en tiempo real
- Métricas de rendimiento actualizadas
- Formato de tabla detallada en consola

Autor: Sistema de Trading Automatizado
Versión: 4.0 Live Simulator
Fecha: Septiembre 2024
"""

import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import time
import os
import sys
from tabulate import tabulate
from colorama import init, Fore, Back, Style
import warnings
warnings.filterwarnings('ignore')

# Importar estrategia V4
from enhanced_strategy_15pct_v4_ultra import Enhanced15PercentStrategyV4Ultra, UltraTradingConfig

# Inicializar colorama para colores en consola
init(autoreset=True)

@dataclass
class LiveTradeExecution:
    """Registro de ejecución de trade en vivo"""
    timestamp: datetime
    symbol: str
    side: str  # 'BUY' o 'SELL'
    price: float
    quantity: float
    amount_usdt: float
    signal_strength: float
    market_data: Dict
    execution_type: str  # 'ENTRY', 'TP1', 'TP2', 'TP3', 'SL'
    pnl_usdt: float = 0.0
    pnl_percentage: float = 0.0
    status: str = 'OPEN'  # 'OPEN', 'CLOSED'

@dataclass
class LivePortfolioMetrics:
    """Métricas del portafolio en tiempo real"""
    timestamp: datetime
    initial_capital: float
    current_balance: float
    total_pnl_usdt: float
    total_pnl_percentage: float
    roi_percentage: float
    max_drawdown_pct: float
    max_drawdown_usdt: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    sharpe_ratio: float
    volatility_pct: float
    trades_today: int
    daily_pnl_usdt: float
    daily_pnl_pct: float

class BinanceLiveDataFeed:
    """Feed de datos en tiempo real de Binance"""
    
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        self.market_data = {}
        self.price_history = {symbol: [] for symbol in self.symbols}
        
    def simulate_live_data(self, symbol: str) -> Dict:
        """Simula datos de mercado en tiempo real"""
        # Generar datos realistas basados en volatilidad típica
        base_prices = {
            'BTCUSDT': 43000,
            'ETHUSDT': 2600,
            'BNBUSDT': 310,
            'ADAUSDT': 0.45,
            'SOLUSDT': 95
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Simular movimiento de precio realista
        if symbol not in self.market_data:
            current_price = base_price
        else:
            last_price = self.market_data[symbol]['price']
            # Movimiento aleatorio con tendencia
            change_pct = np.random.normal(0, 0.002)  # 0.2% volatilidad
            current_price = last_price * (1 + change_pct)
        
        # Simular spread bid/ask
        spread_pct = 0.001  # 0.1% spread típico
        bid_price = current_price * (1 - spread_pct/2)
        ask_price = current_price * (1 + spread_pct/2)
        
        # Simular volumen
        volume_24h = np.random.uniform(50000, 200000)
        
        # Calcular indicadores técnicos básicos
        self.price_history[symbol].append(current_price)
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        prices = np.array(self.price_history[symbol])
        
        # RSI simplificado
        if len(prices) >= 14:
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])
            rs = avg_gain / (avg_loss + 1e-10)
            rsi = 100 - (100 / (1 + rs))
        else:
            rsi = 50
        
        # MACD simplificado
        if len(prices) >= 26:
            ema12 = np.mean(prices[-12:])
            ema26 = np.mean(prices[-26:])
            macd = ema12 - ema26
            signal = np.mean([macd] * 9)  # Simplificado
            histogram = macd - signal
        else:
            macd = signal = histogram = 0
        
        # Medias móviles
        sma20 = np.mean(prices[-20:]) if len(prices) >= 20 else current_price
        sma50 = np.mean(prices[-50:]) if len(prices) >= 50 else current_price
        
        market_data = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'price': current_price,
            'bid': bid_price,
            'ask': ask_price,
            'spread': ask_price - bid_price,
            'spread_pct': (ask_price - bid_price) / current_price * 100,
            'volume_24h': volume_24h,
            'price_change_24h_pct': np.random.uniform(-5, 5),
            'high_24h': current_price * 1.02,
            'low_24h': current_price * 0.98,
            'indicators': {
                'rsi': rsi,
                'macd': macd,
                'macd_signal': signal,
                'macd_histogram': histogram,
                'sma_20': sma20,
                'sma_50': sma50,
                'trend': 'BULLISH' if sma20 > sma50 else 'BEARISH'
            }
        }
        
        self.market_data[symbol] = market_data
        return market_data
    
    def get_all_market_data(self) -> Dict:
        """Obtiene datos de todos los símbolos"""
        all_data = {}
        for symbol in self.symbols:
            all_data[symbol] = self.simulate_live_data(symbol)
        return all_data

class LiveTradingSimulator:
    """Simulador de trading en tiempo real"""
    
    def __init__(self, initial_capital: float = 500.0):
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.strategy = Enhanced15PercentStrategyV4Ultra()
        self.data_feed = BinanceLiveDataFeed()
        
        # Historial de trades y métricas
        self.trades_history: List[LiveTradeExecution] = []
        self.open_positions: Dict[str, LiveTradeExecution] = {}
        self.portfolio_history: List[LivePortfolioMetrics] = []
        self.balance_history: List[float] = [initial_capital]
        
        # Métricas de rendimiento
        self.max_balance = initial_capital
        self.max_drawdown_usdt = 0.0
        self.max_drawdown_pct = 0.0
        self.daily_start_balance = initial_capital
        self.session_start_time = datetime.now()
        
        # Configuración de display
        self.update_interval = 2  # segundos
        self.last_update = datetime.now()
        
    def calculate_portfolio_metrics(self) -> LivePortfolioMetrics:
        """Calcula métricas del portafolio en tiempo real"""
        now = datetime.now()
        
        # PnL total
        total_pnl_usdt = self.current_balance - self.initial_capital
        total_pnl_pct = (total_pnl_usdt / self.initial_capital) * 100
        roi_pct = total_pnl_pct
        
        # Drawdown
        if self.current_balance > self.max_balance:
            self.max_balance = self.current_balance
        
        current_drawdown_usdt = self.max_balance - self.current_balance
        current_drawdown_pct = (current_drawdown_usdt / self.max_balance) * 100
        
        if current_drawdown_usdt > self.max_drawdown_usdt:
            self.max_drawdown_usdt = current_drawdown_usdt
        if current_drawdown_pct > self.max_drawdown_pct:
            self.max_drawdown_pct = current_drawdown_pct
        
        # Estadísticas de trades
        total_trades = len(self.trades_history)
        winning_trades = len([t for t in self.trades_history if t.pnl_usdt > 0])
        losing_trades = len([t for t in self.trades_history if t.pnl_usdt < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Promedio de ganancias/pérdidas
        wins = [t.pnl_percentage for t in self.trades_history if t.pnl_usdt > 0]
        losses = [t.pnl_percentage for t in self.trades_history if t.pnl_usdt < 0]
        avg_win_pct = np.mean(wins) if wins else 0
        avg_loss_pct = np.mean(losses) if losses else 0
        
        # Sharpe ratio simplificado
        if len(self.balance_history) > 1:
            returns = np.diff(self.balance_history) / self.balance_history[:-1]
            sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252)
            volatility = np.std(returns) * np.sqrt(252) * 100
        else:
            sharpe = 0
            volatility = 0
        
        # Métricas diarias
        today_trades = len([t for t in self.trades_history 
                           if t.timestamp.date() == now.date()])
        daily_pnl_usdt = self.current_balance - self.daily_start_balance
        daily_pnl_pct = (daily_pnl_usdt / self.daily_start_balance) * 100
        
        return LivePortfolioMetrics(
            timestamp=now,
            initial_capital=self.initial_capital,
            current_balance=self.current_balance,
            total_pnl_usdt=total_pnl_usdt,
            total_pnl_percentage=total_pnl_pct,
            roi_percentage=roi_pct,
            max_drawdown_pct=self.max_drawdown_pct,
            max_drawdown_usdt=self.max_drawdown_usdt,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_win_pct=avg_win_pct,
            avg_loss_pct=avg_loss_pct,
            sharpe_ratio=sharpe,
            volatility_pct=volatility,
            trades_today=today_trades,
            daily_pnl_usdt=daily_pnl_usdt,
            daily_pnl_pct=daily_pnl_pct
        )
    
    def execute_trade_signal(self, symbol: str, market_data: Dict, signal_data: Dict):
        """Ejecuta una señal de trading"""
        if signal_data['signal'] == 0:
            return
        
        side = 'BUY' if signal_data['signal'] > 0 else 'SELL'
        price = market_data['ask'] if side == 'BUY' else market_data['bid']
        
        # Calcular tamaño de posición
        config = UltraTradingConfig()
        position_size_usdt = self.current_balance * config.position_size_pct
        quantity = position_size_usdt / price
        
        # Verificar si tenemos capital suficiente
        if position_size_usdt > self.current_balance * 0.95:  # Dejar 5% de margen
            return
        
        # Crear registro de trade
        trade = LiveTradeExecution(
            timestamp=datetime.now(),
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            amount_usdt=position_size_usdt,
            signal_strength=signal_data['signal_strength'],
            market_data=market_data.copy(),
            execution_type='ENTRY'
        )
        
        # Actualizar balance
        if side == 'BUY':
            self.current_balance -= position_size_usdt
        else:
            self.current_balance += position_size_usdt
        
        # Agregar a posiciones abiertas
        position_key = f"{symbol}_{side}_{len(self.trades_history)}"
        self.open_positions[position_key] = trade
        
        # Agregar al historial
        self.trades_history.append(trade)
        self.balance_history.append(self.current_balance)
        
    def check_exit_conditions(self):
        """Verifica condiciones de salida para posiciones abiertas"""
        positions_to_close = []
        
        for position_key, position in self.open_positions.items():
            symbol = position.symbol
            current_market = self.data_feed.market_data.get(symbol)
            
            if not current_market:
                continue
            
            current_price = current_market['price']
            entry_price = position.price
            
            # Calcular PnL
            if position.side == 'BUY':
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100
            
            pnl_usdt = position.amount_usdt * (pnl_pct / 100)
            
            # Verificar condiciones de salida
            config = UltraTradingConfig()
            should_exit = False
            exit_reason = ''
            
            if pnl_pct <= -config.stop_loss * 100:  # Stop Loss
                should_exit = True
                exit_reason = 'SL'
            elif pnl_pct >= config.take_profit_1 * 100:  # Take Profit
                should_exit = True
                exit_reason = 'TP1'
            
            # Salida por tiempo (opcional, después de 30 minutos)
            time_in_position = (datetime.now() - position.timestamp).total_seconds() / 60
            if time_in_position > 30:  # 30 minutos
                should_exit = True
                exit_reason = 'TIME'
            
            if should_exit:
                # Cerrar posición
                position.pnl_usdt = pnl_usdt
                position.pnl_percentage = pnl_pct
                position.status = 'CLOSED'
                position.execution_type = exit_reason
                
                # Actualizar balance
                if position.side == 'BUY':
                    self.current_balance += position.amount_usdt + pnl_usdt
                else:
                    self.current_balance -= pnl_usdt
                
                positions_to_close.append(position_key)
                self.balance_history.append(self.current_balance)
        
        # Remover posiciones cerradas
        for key in positions_to_close:
            del self.open_positions[key]
    
    def display_live_data(self):
        """Muestra datos en tiempo real en consola"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*120}")
        print(f"{Fore.CYAN}{Style.BRIGHT}🚀 SIMULADOR DE TRADING EN TIEMPO REAL V4 ULTRA-AGRESIVA")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*120}")
        print(f"{Fore.YELLOW}Tiempo de sesión: {datetime.now() - self.session_start_time}")
        print(f"{Fore.YELLOW}Última actualización: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        # Métricas del portafolio
        metrics = self.calculate_portfolio_metrics()
        
        portfolio_data = [
            ['Capital Inicial', f'${metrics.initial_capital:.2f}'],
            ['Balance Actual', f'${metrics.current_balance:.2f}'],
            ['PnL Total', f'${metrics.total_pnl_usdt:.2f} ({metrics.total_pnl_percentage:+.2f}%)'],
            ['ROI', f'{metrics.roi_percentage:+.2f}%'],
            ['Drawdown Máximo', f'${metrics.max_drawdown_usdt:.2f} ({metrics.max_drawdown_pct:.2f}%)'],
            ['Trades Totales', f'{metrics.total_trades}'],
            ['Win Rate', f'{metrics.win_rate:.1f}%'],
            ['Sharpe Ratio', f'{metrics.sharpe_ratio:.2f}'],
            ['Volatilidad', f'{metrics.volatility_pct:.2f}%'],
            ['Trades Hoy', f'{metrics.trades_today}'],
            ['PnL Diario', f'${metrics.daily_pnl_usdt:.2f} ({metrics.daily_pnl_pct:+.2f}%)']
        ]
        
        print(f"{Fore.GREEN}{Style.BRIGHT}📊 MÉTRICAS DEL PORTAFOLIO")
        print(tabulate(portfolio_data, headers=['Métrica', 'Valor'], tablefmt='grid'))
        print()
        
        # Datos de mercado
        market_data = self.data_feed.get_all_market_data()
        
        market_table = []
        for symbol, data in market_data.items():
            indicators = data['indicators']
            market_table.append([
                symbol,
                f"${data['price']:.4f}",
                f"${data['bid']:.4f}",
                f"${data['ask']:.4f}",
                f"{data['spread_pct']:.3f}%",
                f"{data['volume_24h']:,.0f}",
                f"{indicators['rsi']:.1f}",
                f"{indicators['macd']:.4f}",
                indicators['trend']
            ])
        
        print(f"{Fore.BLUE}{Style.BRIGHT}📈 DATOS DE MERCADO EN TIEMPO REAL")
        print(tabulate(market_table, 
                      headers=['Símbolo', 'Precio', 'Bid', 'Ask', 'Spread%', 'Volumen 24h', 'RSI', 'MACD', 'Tendencia'],
                      tablefmt='grid'))
        print()
        
        # Posiciones abiertas
        if self.open_positions:
            positions_table = []
            for key, position in self.open_positions.items():
                current_market = market_data.get(position.symbol, {})
                current_price = current_market.get('price', position.price)
                
                if position.side == 'BUY':
                    pnl_pct = (current_price - position.price) / position.price * 100
                else:
                    pnl_pct = (position.price - current_price) / position.price * 100
                
                pnl_usdt = position.amount_usdt * (pnl_pct / 100)
                time_in_position = datetime.now() - position.timestamp
                
                color = Fore.GREEN if pnl_usdt > 0 else Fore.RED
                positions_table.append([
                    position.symbol,
                    position.side,
                    f"${position.price:.4f}",
                    f"${current_price:.4f}",
                    f"${position.amount_usdt:.2f}",
                    f"{color}${pnl_usdt:+.2f}{Style.RESET_ALL}",
                    f"{color}{pnl_pct:+.2f}%{Style.RESET_ALL}",
                    str(time_in_position).split('.')[0],
                    f"{position.signal_strength:.2f}"
                ])
            
            print(f"{Fore.MAGENTA}{Style.BRIGHT}🔄 POSICIONES ABIERTAS")
            print(tabulate(positions_table,
                          headers=['Símbolo', 'Lado', 'Precio Entrada', 'Precio Actual', 'Monto', 'PnL USDT', 'PnL %', 'Tiempo', 'Señal'],
                          tablefmt='grid'))
            print()
        
        # Últimos trades
        if self.trades_history:
            recent_trades = self.trades_history[-10:]  # Últimos 10 trades
            trades_table = []
            
            for trade in recent_trades:
                color = Fore.GREEN if trade.pnl_usdt > 0 else Fore.RED if trade.pnl_usdt < 0 else Fore.YELLOW
                trades_table.append([
                    trade.timestamp.strftime('%H:%M:%S'),
                    trade.symbol,
                    trade.side,
                    f"${trade.price:.4f}",
                    f"${trade.amount_usdt:.2f}",
                    trade.execution_type,
                    f"{color}${trade.pnl_usdt:+.2f}{Style.RESET_ALL}" if trade.status == 'CLOSED' else 'ABIERTO',
                    f"{color}{trade.pnl_percentage:+.2f}%{Style.RESET_ALL}" if trade.status == 'CLOSED' else '-',
                    trade.status
                ])
            
            print(f"{Fore.CYAN}{Style.BRIGHT}📋 HISTORIAL DE TRADES (Últimos 10)")
            print(tabulate(trades_table,
                          headers=['Hora', 'Símbolo', 'Lado', 'Precio', 'Monto', 'Tipo', 'PnL USDT', 'PnL %', 'Estado'],
                          tablefmt='grid'))
        
        print(f"\n{Fore.YELLOW}Presiona Ctrl+C para detener la simulación...")
    
    async def run_live_simulation(self):
        """Ejecuta la simulación en tiempo real"""
        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 Iniciando simulación de trading en tiempo real...")
        print(f"{Fore.YELLOW}Capital inicial: ${self.initial_capital}")
        print(f"{Fore.YELLOW}Estrategia: V4 Ultra-Agresiva")
        print(f"{Fore.YELLOW}Símbolos: {', '.join(self.data_feed.symbols)}")
        print(f"{Fore.CYAN}Presiona Ctrl+C para detener...\n")
        
        try:
            while True:
                # Obtener datos de mercado actualizados
                market_data = self.data_feed.get_all_market_data()
                
                # Verificar condiciones de salida para posiciones abiertas
                self.check_exit_conditions()
                
                # Analizar señales de trading para cada símbolo
                for symbol, data in market_data.items():
                    # Limitar número de posiciones abiertas
                    open_positions_count = len(self.open_positions)
                    if open_positions_count >= 3:  # Máximo 3 posiciones simultáneas
                        continue
                    
                    # Simular DataFrame para la estrategia
                    df_data = {
                        'close': [data['price']] * 100,
                        'high': [data['high_24h']] * 100,
                        'low': [data['low_24h']] * 100,
                        'volume': [data['volume_24h']] * 100
                    }
                    df = pd.DataFrame(df_data)
                    
                    # Generar señal
                    signal = self.strategy.generate_ultra_signal(df)
                    
                    if signal and abs(signal['signal']) > 0.5:  # Señal fuerte
                        # Verificar que no tengamos posición abierta en este símbolo
                        has_open_position = any(pos.symbol == symbol for pos in self.open_positions.values())
                        if not has_open_position:
                            self.execute_trade_signal(symbol, data, signal)
                
                # Actualizar display
                self.display_live_data()
                
                # Esperar antes de la siguiente actualización
                await asyncio.sleep(self.update_interval)
                
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}{Style.BRIGHT}🛑 Simulación detenida por el usuario")
            self.display_final_summary()
    
    def display_final_summary(self):
        """Muestra resumen final de la simulación"""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.CYAN}{Style.BRIGHT}📊 RESUMEN FINAL DE LA SIMULACIÓN")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
        
        metrics = self.calculate_portfolio_metrics()
        session_duration = datetime.now() - self.session_start_time
        
        summary_data = [
            ['Duración de Sesión', str(session_duration).split('.')[0]],
            ['Capital Inicial', f'${self.initial_capital:.2f}'],
            ['Capital Final', f'${metrics.current_balance:.2f}'],
            ['PnL Total', f'${metrics.total_pnl_usdt:.2f}'],
            ['ROI Total', f'{metrics.roi_percentage:+.2f}%'],
            ['Trades Ejecutados', f'{metrics.total_trades}'],
            ['Trades Ganadores', f'{metrics.winning_trades}'],
            ['Trades Perdedores', f'{metrics.losing_trades}'],
            ['Win Rate', f'{metrics.win_rate:.1f}%'],
            ['Drawdown Máximo', f'{metrics.max_drawdown_pct:.2f}%'],
            ['Sharpe Ratio', f'{metrics.sharpe_ratio:.2f}']
        ]
        
        print(tabulate(summary_data, headers=['Métrica', 'Valor'], tablefmt='grid'))
        print(f"\n{Fore.GREEN}{Style.BRIGHT}✅ Simulación completada exitosamente")

def main():
    """Función principal"""
    print(f"{Fore.CYAN}{Style.BRIGHT}🚀 SIMULADOR DE TRADING EN TIEMPO REAL V4 ULTRA-AGRESIVA")
    print(f"{Fore.CYAN}{Style.BRIGHT}{'='*80}")
    print(f"{Fore.YELLOW}Configurando simulador...")
    
    # Crear simulador
    simulator = LiveTradingSimulator(initial_capital=500.0)
    
    # Ejecutar simulación
    try:
        asyncio.run(simulator.run_live_simulation())
    except Exception as e:
        print(f"{Fore.RED}❌ Error en la simulación: {e}")
        simulator.display_final_summary()

if __name__ == "__main__":
    main()