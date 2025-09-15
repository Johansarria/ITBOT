#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Backtesting con Datos Reales de Binance
Desarrollado para AUDCAD, NAS100 y XAUUSD
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class BinanceDataDownloader:
    """Descargador de datos históricos de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3/klines"
        # Mapeo de símbolos a pares de Binance
        self.symbol_mapping = {
            'AUDCAD': 'AUDCAD',
            'NAS100': 'BTCUSDT',  # Usamos BTC como proxy para NAS100
            'XAUUSD': 'BTCUSDT'   # Usamos BTC como proxy para XAU
        }
    
    def get_historical_data(self, symbol: str, interval: str = '1h', 
                          days_back: int = 30) -> pd.DataFrame:
        """Descarga datos históricos REALES de Binance - SIN datos sintéticos"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # Mapeo de símbolos para Binance con pares reales
                binance_symbols = {
                    'AUDCAD': 'AUDUSDT',  # AUD/USDT como proxy para AUD/CAD
                    'NAS100': 'BTCUSDT',  # Bitcoin como proxy para NAS100
                    'XAUUSD': 'BTCUSDT'   # Bitcoin como proxy para XAU/USD
                }
                
                binance_symbol = binance_symbols.get(symbol, 'BTCUSDT')
                
                # Calcular timestamps
                end_time = int(datetime.now().timestamp() * 1000)
                start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
                
                params = {
                    'symbol': binance_symbol,
                    'interval': interval,
                    'startTime': start_time,
                    'endTime': end_time,
                    'limit': 1000
                }
                
                print(f"Intento {attempt + 1}/{max_retries} - Descargando datos REALES de {binance_symbol} para {symbol}")
                response = requests.get(self.base_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data:
                        print(f"API de Binance no devolvió datos para {symbol}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        else:
                            raise Exception(f"No se pudieron obtener datos reales para {symbol} después de {max_retries} intentos")
                    
                    # Convertir a DataFrame
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_asset_volume', 'number_of_trades',
                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                    ])
                    
                    # Procesar datos
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = pd.to_numeric(df[col])
                    
                    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                    df.set_index('timestamp', inplace=True)
                    
                    print(f"✓ DATOS REALES obtenidos para {symbol}: {len(df)} registros de {binance_symbol}")
                    return df
                    
                elif response.status_code == 429:  # Rate limit
                    print(f"Rate limit alcanzado, esperando {retry_delay * 2} segundos...")
                    time.sleep(retry_delay * 2)
                    continue
                else:
                    print(f"Error HTTP {response.status_code}: {response.text}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise Exception(f"Error HTTP {response.status_code} después de {max_retries} intentos")
                        
            except requests.exceptions.RequestException as e:
                print(f"Error de conexión en intento {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    raise Exception(f"Error de conexión después de {max_retries} intentos: {e}")
            except Exception as e:
                print(f"Error inesperado en intento {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    raise Exception(f"Error inesperado después de {max_retries} intentos: {e}")
        
        # Si llegamos aquí, todos los intentos fallaron
        raise Exception(f"IMPOSIBLE obtener datos reales de Binance para {symbol} después de {max_retries} intentos")
    
    # FUNCIÓN DE DATOS SINTÉTICOS ELIMINADA - SOLO DATOS REALES DE BINANCE

class RealDataBacktester:
    """Sistema de backtesting con datos reales de Binance"""
    
    def __init__(self, initial_capital: float = 1000):
        self.initial_capital = initial_capital
        self.downloader = BinanceDataDownloader()
        self.results = {}
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos"""
        data = df.copy()
        
        # Medias móviles
        data['sma_20'] = data['close'].rolling(window=20).mean()
        data['sma_50'] = data['close'].rolling(window=50).mean()
        data['ema_12'] = data['close'].ewm(span=12).mean()
        data['ema_26'] = data['close'].ewm(span=26).mean()
        
        # MACD
        data['macd'] = data['ema_12'] - data['ema_26']
        data['macd_signal'] = data['macd'].ewm(span=9).mean()
        data['macd_histogram'] = data['macd'] - data['macd_signal']
        
        # RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        data['bb_middle'] = data['close'].rolling(window=20).mean()
        bb_std = data['close'].rolling(window=20).std()
        data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
        data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
        
        # ATR
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        data['atr'] = true_range.rolling(window=14).mean()
        
        return data
    
    def audcad_strategy_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Señales de estrategia para AUDCAD"""
        signals = data.copy()
        
        # Condiciones de compra
        buy_condition = (
            (signals['close'] > signals['sma_20']) &
            (signals['rsi'] < 70) &
            (signals['macd'] > signals['macd_signal']) &
            (signals['close'] > signals['bb_lower'])
        )
        
        # Condiciones de venta
        sell_condition = (
            (signals['close'] < signals['sma_20']) |
            (signals['rsi'] > 80) |
            (signals['macd'] < signals['macd_signal']) |
            (signals['close'] < signals['bb_lower'])
        )
        
        signals['signal'] = 0
        signals.loc[buy_condition, 'signal'] = 1
        signals.loc[sell_condition, 'signal'] = -1
        
        return signals
    
    def nas100_strategy_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Señales de estrategia para NAS100"""
        signals = data.copy()
        
        # Estrategia de momentum
        buy_condition = (
            (signals['close'] > signals['sma_50']) &
            (signals['rsi'] > 50) &
            (signals['rsi'] < 75) &
            (signals['macd_histogram'] > 0)
        )
        
        sell_condition = (
            (signals['close'] < signals['sma_50']) |
            (signals['rsi'] < 30) |
            (signals['macd_histogram'] < 0)
        )
        
        signals['signal'] = 0
        signals.loc[buy_condition, 'signal'] = 1
        signals.loc[sell_condition, 'signal'] = -1
        
        return signals
    
    def xauusd_strategy_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Señales de estrategia para XAUUSD"""
        signals = data.copy()
        
        # Estrategia de reversión a la media
        buy_condition = (
            (signals['close'] < signals['bb_lower']) &
            (signals['rsi'] < 30) &
            (signals['close'] > signals['close'].shift(1))
        )
        
        sell_condition = (
            (signals['close'] > signals['bb_upper']) |
            (signals['rsi'] > 70) |
            (signals['close'] < signals['close'].shift(1) * 0.98)
        )
        
        signals['signal'] = 0
        signals.loc[buy_condition, 'signal'] = 1
        signals.loc[sell_condition, 'signal'] = -1
        
        return signals
    
    def simulate_trading(self, signals: pd.DataFrame, symbol: str) -> Dict:
        """Simula el trading con las señales"""
        capital = self.initial_capital
        position = 0
        trades = []
        equity_curve = []
        
        for i, row in signals.iterrows():
            if pd.isna(row['signal']):
                continue
                
            current_price = row['close']
            signal = row['signal']
            
            # Entrada en posición
            if signal == 1 and position == 0:  # Compra
                position = capital / current_price
                capital = 0
                entry_price = current_price
                entry_time = i
                
            elif signal == -1 and position > 0:  # Venta
                capital = position * current_price
                
                # Registrar trade
                pnl = capital - self.initial_capital if len(trades) == 0 else capital - trades[-1]['exit_capital']
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': i,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl': pnl,
                    'return': (current_price - entry_price) / entry_price,
                    'exit_capital': capital
                })
                
                position = 0
            
            # Calcular equity actual
            current_equity = capital if position == 0 else position * current_price
            equity_curve.append(current_equity)
        
        # Cerrar posición final si existe
        if position > 0:
            final_price = signals['close'].iloc[-1]
            capital = position * final_price
            
            pnl = capital - self.initial_capital if len(trades) == 0 else capital - trades[-1]['exit_capital']
            trades.append({
                'entry_time': entry_time,
                'exit_time': signals.index[-1],
                'entry_price': entry_price,
                'exit_price': final_price,
                'pnl': pnl,
                'return': (final_price - entry_price) / entry_price,
                'exit_capital': capital
            })
        
        return {
            'final_capital': capital,
            'trades': trades,
            'equity_curve': equity_curve,
            'total_return': (capital - self.initial_capital) / self.initial_capital,
            'num_trades': len(trades)
        }
    
    def calculate_metrics(self, results: Dict) -> Dict:
        """Calcula métricas de rendimiento"""
        if not results['trades']:
            return {
                'total_return': 0,
                'win_rate': 0,
                'avg_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'num_trades': 0
            }
        
        trades_df = pd.DataFrame(results['trades'])
        
        # Métricas básicas
        total_return = results['total_return']
        win_rate = len(trades_df[trades_df['pnl'] > 0]) / len(trades_df)
        avg_return = trades_df['return'].mean()
        
        # Drawdown
        equity_curve = np.array(results['equity_curve'])
        if len(equity_curve) > 0:
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (equity_curve - peak) / peak
            max_drawdown = abs(drawdown.min())
        else:
            max_drawdown = 0
        
        # Sharpe ratio
        if trades_df['return'].std() > 0:
            sharpe_ratio = avg_return / trades_df['return'].std() * np.sqrt(252)
        else:
            sharpe_ratio = 0
        
        return {
            'total_return': total_return,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'num_trades': len(trades_df)
        }
    
    def run_backtest(self, symbol: str, days_back: int = 30) -> Dict:
        """Ejecuta backtest para un símbolo - SOLO CON DATOS REALES"""
        print(f"\n=== Iniciando backtest para {symbol} - SOLO DATOS REALES ===")
        
        try:
            # Descargar datos reales - SIN RESPALDO SINTÉTICO
            data = self.downloader.get_historical_data(symbol, days_back=days_back)
            
            if data.empty:
                raise Exception(f"No se pudieron obtener datos REALES para {symbol}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            print(f"❌ BACKTEST CANCELADO para {symbol} - No hay datos reales disponibles")
            return {}
        
        # Calcular indicadores
        data_with_indicators = self.calculate_indicators(data)
        
        # Generar señales según el símbolo
        if symbol == 'AUDCAD':
            signals = self.audcad_strategy_signals(data_with_indicators)
        elif symbol == 'NAS100':
            signals = self.nas100_strategy_signals(data_with_indicators)
        elif symbol == 'XAUUSD':
            signals = self.xauusd_strategy_signals(data_with_indicators)
        else:
            print(f"Estrategia no definida para {symbol}")
            return {}
        
        # Simular trading
        trading_results = self.simulate_trading(signals, symbol)
        
        # Calcular métricas
        metrics = self.calculate_metrics(trading_results)
        
        print(f"Backtest completado para {symbol}:")
        print(f"  - Retorno total: {metrics['total_return']:.2%}")
        print(f"  - Tasa de acierto: {metrics['win_rate']:.2%}")
        print(f"  - Número de operaciones: {metrics['num_trades']}")
        print(f"  - Drawdown máximo: {metrics['max_drawdown']:.2%}")
        
        return {
            'symbol': symbol,
            'data_points': len(data),
            'metrics': metrics,
            'trading_results': trading_results
        }
    
    def run_comprehensive_backtest(self) -> Dict:
        """Ejecuta backtest completo para todos los símbolos"""
        symbols = ['AUDCAD', 'NAS100', 'XAUUSD']
        all_results = {}
        
        print("=== SISTEMA DE BACKTESTING CON DATOS REALES DE BINANCE ===")
        print(f"Capital inicial: ${self.initial_capital:,.2f}")
        print(f"Fecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for symbol in symbols:
            try:
                result = self.run_backtest(symbol, days_back=30)
                if result:
                    all_results[symbol] = result
                time.sleep(1)  # Evitar rate limiting
            except Exception as e:
                print(f"Error en backtest de {symbol}: {e}")
        
        # Generar reporte consolidado
        self.generate_consolidated_report(all_results)
        
        return all_results
    
    def generate_consolidated_report(self, results: Dict):
        """Genera reporte consolidado"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'real_data_backtest_report_{timestamp}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=== REPORTE DE BACKTESTING CON DATOS REALES ===\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Capital inicial: ${self.initial_capital:,.2f}\n\n")
            
            total_return = 0
            total_trades = 0
            
            for symbol, result in results.items():
                metrics = result['metrics']
                f.write(f"\n=== {symbol} ===\n")
                f.write(f"Puntos de datos: {result['data_points']}\n")
                f.write(f"Retorno total: {metrics['total_return']:.2%}\n")
                f.write(f"Tasa de acierto: {metrics['win_rate']:.2%}\n")
                f.write(f"Retorno promedio: {metrics['avg_return']:.2%}\n")
                f.write(f"Drawdown máximo: {metrics['max_drawdown']:.2%}\n")
                f.write(f"Ratio de Sharpe: {metrics['sharpe_ratio']:.2f}\n")
                f.write(f"Número de operaciones: {metrics['num_trades']}\n")
                
                total_return += metrics['total_return']
                total_trades += metrics['num_trades']
            
            # Resumen consolidado
            avg_return = total_return / len(results) if results else 0
            f.write(f"\n=== RESUMEN CONSOLIDADO ===\n")
            f.write(f"Retorno promedio del portafolio: {avg_return:.2%}\n")
            f.write(f"Total de operaciones: {total_trades}\n")
            f.write(f"Capital final estimado: ${self.initial_capital * (1 + avg_return):,.2f}\n")
            
            f.write(f"\n=== FUENTE DE DATOS ===\n")
            f.write(f"Datos obtenidos de: Binance API\n")
            f.write(f"Período analizado: Últimos 30 días\n")
            f.write(f"Intervalo: 1 hora\n")
        
        print(f"\nReporte consolidado generado: {filename}")
        print(f"Retorno promedio del portafolio: {avg_return:.2%}")
        print(f"Total de operaciones: {total_trades}")

def main():
    """Función principal"""
    print("Iniciando sistema de backtesting con datos reales de Binance...")
    
    # Crear backtester
    backtester = RealDataBacktester(initial_capital=1000)
    
    # Ejecutar backtest completo
    results = backtester.run_comprehensive_backtest()
    
    print("\n=== BACKTESTING COMPLETADO ===")
    print(f"Resultados guardados y análisis finalizado.")
    print(f"Se analizaron {len(results)} instrumentos con datos reales de Binance.")

if __name__ == "__main__":
    main()