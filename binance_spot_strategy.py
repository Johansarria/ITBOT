#!/usr/bin/env python3
"""
Estrategia de Trading Algorítmico para Binance Spot
Capital inicial: 500 USDT
Objetivo: 0.6% rendimiento diario promedio
Autor: Sistema de Trading Avanzado
"""

import pandas as pd
import numpy as np
import ccxt
import talib
from datetime import datetime, timedelta
import time
import json
import logging
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class BinanceSpotStrategy:
    """
    Estrategia de trading algorítmico optimizada para Binance Spot
    con capital inicial de 500 USDT y objetivo de 0.6% diario
    """
    
    def __init__(self, initial_capital: float = 500.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.daily_target = 0.006  # 0.6% diario
        self.max_risk_per_trade = 0.02  # 2% máximo por operación
        self.commission_rate = 0.001  # 0.1% comisión Binance
        
        # Configuración de pares de trading
        self.trading_pairs = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 
            'SOL/USDT', 'MATIC/USDT', 'DOT/USDT', 'AVAX/USDT'
        ]
        
        # Parámetros técnicos optimizados
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ema_fast = 12
        self.ema_slow = 26
        self.bb_period = 20
        self.bb_std = 2
        
        # Gestión de riesgo
        self.stop_loss_pct = 0.015  # 1.5% stop loss
        self.take_profit_pct = 0.025  # 2.5% take profit
        self.max_positions = 3  # Máximo 3 posiciones simultáneas
        
        # Configuración de logging
        self.setup_logging()
        
        # Inicializar exchange
        self.exchange = None
        self.setup_exchange()
        
        # Métricas de rendimiento
        self.trades_history = []
        self.daily_returns = []
        self.drawdowns = []
        
    def setup_logging(self):
        """Configurar sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('binance_strategy.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_exchange(self):
        """Configurar conexión con Binance (modo sandbox/testnet)"""
        try:
            self.exchange = ccxt.binance({
                'apiKey': 'your_api_key',
                'secret': 'your_secret_key',
                'sandbox': True,  # Usar testnet para pruebas
                'enableRateLimit': True,
            })
            self.logger.info("Conexión con Binance establecida")
        except Exception as e:
            self.logger.error(f"Error conectando con Binance: {e}")
            
    def get_market_data(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """Obtener datos históricos del mercado"""
        try:
            if self.exchange:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            else:
                # Datos simulados para testing
                ohlcv = self.generate_mock_data(limit)
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
        except Exception as e:
            self.logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return pd.DataFrame()
            
    def generate_mock_data(self, limit: int) -> List[List]:
        """Generar datos simulados para testing"""
        np.random.seed(42)
        data = []
        base_price = 50000  # Precio base simulado
        
        for i in range(limit):
            timestamp = int((datetime.now() - timedelta(hours=limit-i)).timestamp() * 1000)
            
            # Simulación de movimiento de precios con tendencia y volatilidad
            price_change = np.random.normal(0, 0.02)  # 2% volatilidad
            if i > 0:
                base_price = data[-1][4] * (1 + price_change)  # Usar precio de cierre anterior
            
            open_price = base_price
            high_price = open_price * (1 + abs(np.random.normal(0, 0.01)))
            low_price = open_price * (1 - abs(np.random.normal(0, 0.01)))
            close_price = open_price + (high_price - low_price) * np.random.uniform(-0.5, 0.5)
            volume = np.random.uniform(1000, 10000)
            
            data.append([timestamp, open_price, high_price, low_price, close_price, volume])
            
        return data
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores técnicos"""
        if df.empty:
            return df
            
        # RSI
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=self.rsi_period)
        
        # EMAs
        df['ema_fast'] = talib.EMA(df['close'].values, timeperiod=self.ema_fast)
        df['ema_slow'] = talib.EMA(df['close'].values, timeperiod=self.ema_slow)
        
        # Bandas de Bollinger
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
            df['close'].values, timeperiod=self.bb_period, nbdevup=self.bb_std, nbdevdn=self.bb_std
        )
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(df['close'].values)
        
        # Volumen promedio
        df['volume_sma'] = talib.SMA(df['volume'].values, timeperiod=20)
        
        # ATR para volatilidad
        df['atr'] = talib.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        
        return df
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generar señales de trading basadas en análisis técnico"""
        if df.empty or len(df) < 50:
            return df
            
        df['signal'] = 0
        df['signal_strength'] = 0.0
        
        # Condiciones de compra
        buy_conditions = (
            (df['rsi'] < self.rsi_oversold) &  # RSI sobreventa
            (df['ema_fast'] > df['ema_slow']) &  # Tendencia alcista
            (df['close'] < df['bb_lower']) &  # Precio cerca de banda inferior
            (df['macd'] > df['macd_signal']) &  # MACD positivo
            (df['volume'] > df['volume_sma'] * 1.2)  # Volumen elevado
        )
        
        # Condiciones de venta
        sell_conditions = (
            (df['rsi'] > self.rsi_overbought) &  # RSI sobrecompra
            (df['ema_fast'] < df['ema_slow']) &  # Tendencia bajista
            (df['close'] > df['bb_upper']) &  # Precio cerca de banda superior
            (df['macd'] < df['macd_signal'])  # MACD negativo
        )
        
        df.loc[buy_conditions, 'signal'] = 1
        df.loc[sell_conditions, 'signal'] = -1
        
        # Calcular fuerza de la señal
        df['signal_strength'] = self.calculate_signal_strength(df)
        
        return df
        
    def calculate_signal_strength(self, df: pd.DataFrame) -> pd.Series:
        """Calcular la fuerza de las señales de trading"""
        strength = pd.Series(0.0, index=df.index)
        
        # Normalizar indicadores
        rsi_norm = (df['rsi'] - 50) / 50
        macd_norm = df['macd'] / df['close'] * 1000
        bb_position = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Combinar indicadores para fuerza de señal
        strength = abs(rsi_norm) * 0.3 + abs(macd_norm) * 0.3 + abs(bb_position - 0.5) * 0.4
        
        return strength.fillna(0)
        
    def calculate_position_size(self, signal_strength: float, current_price: float, atr: float) -> float:
        """Calcular el tamaño de posición basado en gestión de riesgo"""
        # Riesgo base por operación
        risk_amount = self.current_capital * self.max_risk_per_trade
        
        # Ajustar por volatilidad (ATR)
        volatility_factor = min(atr / current_price, 0.05)  # Máximo 5% de volatilidad
        adjusted_risk = risk_amount * (1 - volatility_factor)
        
        # Ajustar por fuerza de señal
        signal_factor = min(signal_strength, 1.0)
        final_risk = adjusted_risk * signal_factor
        
        # Calcular tamaño de posición
        stop_distance = current_price * self.stop_loss_pct
        position_size = final_risk / stop_distance
        
        # Limitar por capital disponible
        max_position_value = self.current_capital * 0.3  # Máximo 30% del capital por posición
        max_position_size = max_position_value / current_price
        
        return min(position_size, max_position_size)
        
    def backtest_strategy(self, start_date: str, end_date: str) -> Dict:
        """Realizar backtesting de la estrategia"""
        self.logger.info(f"Iniciando backtesting desde {start_date} hasta {end_date}")
        
        results = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'daily_returns': [],
            'equity_curve': []
        }
        
        # Simular trading para cada par
        for pair in self.trading_pairs:
            pair_results = self.backtest_pair(pair, start_date, end_date)
            
            results['total_trades'] += pair_results['trades']
            results['winning_trades'] += pair_results['wins']
            results['losing_trades'] += pair_results['losses']
            results['total_return'] += pair_results['return']
            
        # Calcular métricas finales
        if results['total_trades'] > 0:
            results['win_rate'] = results['winning_trades'] / results['total_trades']
            results['avg_return_per_trade'] = results['total_return'] / results['total_trades']
            
        return results
        
    def backtest_pair(self, pair: str, start_date: str, end_date: str) -> Dict:
        """Backtesting para un par específico"""
        # Obtener datos históricos
        df = self.get_market_data(pair, '1h', 1000)
        
        if df.empty:
            return {'trades': 0, 'wins': 0, 'losses': 0, 'return': 0.0}
            
        # Calcular indicadores y señales
        df = self.calculate_technical_indicators(df)
        df = self.generate_signals(df)
        
        trades = 0
        wins = 0
        losses = 0
        total_return = 0.0
        
        position = None
        
        for i in range(50, len(df)):  # Comenzar después de período de calentamiento
            current_row = df.iloc[i]
            
            if position is None and current_row['signal'] != 0:
                # Abrir posición
                position = {
                    'type': 'long' if current_row['signal'] == 1 else 'short',
                    'entry_price': current_row['close'],
                    'size': self.calculate_position_size(
                        current_row['signal_strength'], 
                        current_row['close'], 
                        current_row['atr']
                    ),
                    'stop_loss': current_row['close'] * (1 - self.stop_loss_pct) if current_row['signal'] == 1 
                                else current_row['close'] * (1 + self.stop_loss_pct),
                    'take_profit': current_row['close'] * (1 + self.take_profit_pct) if current_row['signal'] == 1 
                                  else current_row['close'] * (1 - self.take_profit_pct)
                }
                
            elif position is not None:
                # Verificar condiciones de cierre
                current_price = current_row['close']
                
                close_position = False
                pnl = 0.0
                
                if position['type'] == 'long':
                    if current_price <= position['stop_loss'] or current_price >= position['take_profit']:
                        close_position = True
                        pnl = (current_price - position['entry_price']) * position['size']
                else:  # short
                    if current_price >= position['stop_loss'] or current_price <= position['take_profit']:
                        close_position = True
                        pnl = (position['entry_price'] - current_price) * position['size']
                        
                if close_position:
                    # Aplicar comisiones
                    commission = position['entry_price'] * position['size'] * self.commission_rate * 2
                    net_pnl = pnl - commission
                    
                    trades += 1
                    if net_pnl > 0:
                        wins += 1
                    else:
                        losses += 1
                        
                    total_return += net_pnl
                    position = None
                    
        return {'trades': trades, 'wins': wins, 'losses': losses, 'return': total_return}
        
    def run_strategy(self):
        """Ejecutar la estrategia en tiempo real"""
        self.logger.info("Iniciando estrategia de trading en tiempo real")
        
        while True:
            try:
                for pair in self.trading_pairs:
                    self.process_pair(pair)
                    
                # Esperar antes del próximo ciclo
                time.sleep(60)  # Revisar cada minuto
                
            except KeyboardInterrupt:
                self.logger.info("Estrategia detenida por el usuario")
                break
            except Exception as e:
                self.logger.error(f"Error en estrategia: {e}")
                time.sleep(30)
                
    def process_pair(self, pair: str):
        """Procesar un par de trading específico"""
        df = self.get_market_data(pair, '1h', 100)
        
        if df.empty:
            return
            
        df = self.calculate_technical_indicators(df)
        df = self.generate_signals(df)
        
        latest = df.iloc[-1]
        
        if latest['signal'] != 0 and latest['signal_strength'] > 0.5:
            self.logger.info(f"Señal detectada para {pair}: {latest['signal']} (fuerza: {latest['signal_strength']:.2f})")
            # Aquí se ejecutaría la orden real
            
    def generate_report(self) -> str:
        """Generar reporte de rendimiento"""
        report = f"""
=== REPORTE DE ESTRATEGIA BINANCE SPOT ===
Capital inicial: ${self.initial_capital:.2f}
Capital actual: ${self.current_capital:.2f}
Rendimiento total: {((self.current_capital / self.initial_capital) - 1) * 100:.2f}%
Objetivo diario: {self.daily_target * 100:.1f}%
Pares de trading: {len(self.trading_pairs)}
Operaciones realizadas: {len(self.trades_history)}

Parámetros de riesgo:
- Riesgo máximo por operación: {self.max_risk_per_trade * 100:.1f}%
- Stop loss: {self.stop_loss_pct * 100:.1f}%
- Take profit: {self.take_profit_pct * 100:.1f}%
- Posiciones máximas: {self.max_positions}
"""
        return report

if __name__ == "__main__":
    # Inicializar estrategia
    strategy = BinanceSpotStrategy(initial_capital=500.0)
    
    # Ejecutar backtesting
    print("Ejecutando backtesting...")
    results = strategy.backtest_strategy('2024-01-01', '2024-12-31')
    
    print("\n=== RESULTADOS DEL BACKTESTING ===")
    print(f"Total de operaciones: {results['total_trades']}")
    print(f"Operaciones ganadoras: {results['winning_trades']}")
    print(f"Operaciones perdedoras: {results['losing_trades']}")
    if results['total_trades'] > 0:
        print(f"Tasa de acierto: {results['win_rate']:.2%}")
        print(f"Rendimiento promedio por operación: {results['avg_return_per_trade']:.2f} USDT")
    print(f"Rendimiento total: {results['total_return']:.2f} USDT")
    
    # Generar reporte
    print("\n" + strategy.generate_report())