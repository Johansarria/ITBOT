#!/usr/bin/env python3
"""
Estrategia de Probabilidad Dinámica con Datos Reales de Binance
Pruebas con 30, 60 y 90 días de datos históricos reales
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

class BinanceDataFetcher:
    """Obtiene datos históricos reales de Binance"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        
    def get_historical_klines(self, symbol: str, interval: str, days: int) -> pd.DataFrame:
        """Obtiene datos históricos de Binance"""
        try:
            # Calcular timestamps
            end_time = int(time.time() * 1000)
            start_time = end_time - (days * 24 * 60 * 60 * 1000)
            
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000
            }
            
            all_data = []
            current_start = start_time
            
            while current_start < end_time:
                params['startTime'] = current_start
                response = requests.get(url, params=params)
                
                if response.status_code != 200:
                    print(f"Error obteniendo datos para {symbol}: {response.status_code}")
                    break
                    
                data = response.json()
                if not data:
                    break
                    
                all_data.extend(data)
                current_start = data[-1][6] + 1  # Siguiente timestamp
                time.sleep(0.1)  # Rate limiting
                
            if not all_data:
                return pd.DataFrame()
                
            # Convertir a DataFrame
            df = pd.DataFrame(all_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convertir tipos
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col])
                
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.set_index('timestamp')
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"Error obteniendo datos para {symbol}: {e}")
            return pd.DataFrame()

class RealDataProbabilityStrategy:
    """Estrategia de probabilidad con datos reales de Binance"""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.data_fetcher = BinanceDataFetcher()
        
        # Parámetros de la estrategia
        self.base_probability = 0.60
        self.max_momentum_bonus = 0.30
        self.fixed_trade_amount = initial_capital * 0.18  # 18% del capital inicial
        self.max_positions = 3
        self.position_time_limit = 24  # horas
        
        # Rangos dinámicos
        self.tp_range = (0.06, 0.15)  # 6-15%
        self.sl_range = (0.015, 0.025)  # 1.5-2.5%
        
        # Filtros de calidad
        self.min_volume_ratio = 1.2
        self.volatility_range = (0.002, 0.05)  # 0.2-5%
        
        # Control de riesgo
        self.max_total_loss = 0.20  # 20%
        self.max_consecutive_losses = 3
        self.consecutive_losses = 0
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos"""
        if len(df) < 50:
            return df
            
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Medias móviles
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['sma_20']
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volatilidad
        df['volatility'] = df['close'].pct_change().rolling(window=20).std()
        
        # Volumen promedio
        df['avg_volume'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['avg_volume']
        
        return df
        
    def calculate_signal_probability(self, df: pd.DataFrame, idx: int) -> Tuple[float, str]:
        """Calcula la probabilidad de señal basada en condiciones técnicas"""
        if idx < 50:  # Necesitamos suficientes datos
            return 0.0, "Datos Insuficientes"
            
        current = df.iloc[idx]
        prev = df.iloc[idx-1]
        
        # Filtros de calidad
        if pd.isna(current['volume_ratio']) or current['volume_ratio'] < self.min_volume_ratio:
            return 0.0, "Volumen Bajo"
            
        if pd.isna(current['volatility']) or not (self.volatility_range[0] <= current['volatility'] <= self.volatility_range[1]):
            return 0.0, "Volatilidad Inadecuada"
            
        probability = self.base_probability
        signal_type = "Entrada Base"
        
        # Momentum positivo
        if (current['close'] > current['sma_20'] and 
            current['sma_20'] > current['sma_50'] and
            current['rsi'] > 50 and current['rsi'] < 70):
            probability += 0.15
            signal_type = "Momentum Positivo"
            
        # Bounce en soporte
        elif (current['close'] <= current['bb_lower'] * 1.02 and
              current['close'] > prev['close'] and
              current['rsi'] < 35):
            probability += 0.20
            signal_type = "Bounce en Soporte"
            
        # Breakout con volumen
        elif (current['close'] > current['bb_upper'] and
              current['volume_ratio'] > 1.5 and
              current['rsi'] > 55):
            probability += 0.25
            signal_type = "Breakout Volumen"
            
        # Entrada aleatoria ponderada
        else:
            momentum_factor = min((current['close'] / current['sma_20'] - 1) * 10, self.max_momentum_bonus)
            probability += momentum_factor
            signal_type = "Entrada Aleatoria Ponderada"
            
        return min(probability, 0.95), signal_type
        
    def calculate_dynamic_tp_sl(self, entry_price: float, volatility: float) -> Tuple[float, float]:
        """Calcula TP y SL dinámicos basados en volatilidad"""
        # Ajustar rangos según volatilidad
        vol_factor = min(volatility / 0.02, 2.0)  # Normalizar volatilidad
        
        tp_pct = self.tp_range[0] + (self.tp_range[1] - self.tp_range[0]) * vol_factor
        sl_pct = self.sl_range[0] + (self.sl_range[1] - self.sl_range[0]) * vol_factor
        
        tp_price = entry_price * (1 + tp_pct)
        sl_price = entry_price * (1 - sl_pct)
        
        return tp_price, sl_price
        
    def check_position_exit(self, symbol: str, current_price: float, current_time: datetime) -> Optional[str]:
        """Verifica si una posición debe cerrarse"""
        if symbol not in self.positions:
            return None
            
        position = self.positions[symbol]
        
        # Check TP/SL
        if current_price >= position['tp_price']:
            return "TP"
        elif current_price <= position['sl_price']:
            return "SL"
            
        # Check tiempo límite
        time_diff = (current_time - position['entry_time']).total_seconds() / 3600
        if time_diff >= self.position_time_limit:
            return "Tiempo"
            
        return None
        
    def execute_trade(self, symbol: str, action: str, price: float, timestamp: datetime, 
                     reason: str = "", signal_type: str = "") -> None:
        """Ejecuta una operación"""
        if action == "BUY":
            if len(self.positions) >= self.max_positions:
                return
                
            # Verificar capital disponible
            if self.capital < self.fixed_trade_amount:
                return
                
            # Calcular TP/SL dinámicos
            volatility = 0.02  # Valor por defecto si no está disponible
            tp_price, sl_price = self.calculate_dynamic_tp_sl(price, volatility)
            
            self.positions[symbol] = {
                'entry_price': price,
                'entry_time': timestamp,
                'tp_price': tp_price,
                'sl_price': sl_price,
                'amount': self.fixed_trade_amount,
                'signal_type': signal_type
            }
            
            self.capital -= self.fixed_trade_amount
            
        elif action == "SELL" and symbol in self.positions:
            position = self.positions[symbol]
            pnl_amount = (price - position['entry_price']) / position['entry_price'] * position['amount']
            pnl_pct = (price - position['entry_price']) / position['entry_price'] * 100
            
            self.capital += position['amount'] + pnl_amount
            
            # Registrar trade
            self.trades.append({
                'symbol': symbol,
                'entry_time': position['entry_time'],
                'exit_time': timestamp,
                'entry_price': position['entry_price'],
                'exit_price': price,
                'amount': position['amount'],
                'pnl_amount': pnl_amount,
                'pnl_pct': pnl_pct,
                'reason': reason,
                'signal_type': position['signal_type']
            })
            
            # Actualizar contador de pérdidas consecutivas
            if pnl_amount < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
                
            del self.positions[symbol]
            
    def run_backtest(self, symbols: List[str], days: int) -> Dict:
        """Ejecuta backtest con datos reales de Binance"""
        print(f"\n=== INICIANDO BACKTEST CON DATOS REALES DE BINANCE ({days} DÍAS) ===")
        print(f"Símbolos: {symbols}")
        print(f"Capital inicial: ${self.initial_capital:,.2f}")
        
        # Obtener datos para todos los símbolos
        all_data = {}
        for symbol in symbols:
            print(f"Obteniendo datos para {symbol}...")
            df = self.data_fetcher.get_historical_klines(symbol, '1h', days)
            
            if df.empty:
                print(f"No se pudieron obtener datos para {symbol}")
                continue
                
            df = self.calculate_technical_indicators(df)
            all_data[symbol] = df
            print(f"Datos obtenidos: {len(df)} registros")
            
        if not all_data:
            print("No se pudieron obtener datos para ningún símbolo")
            return {}
            
        # Crear timeline unificado
        all_timestamps = set()
        for df in all_data.values():
            all_timestamps.update(df.index)
            
        timeline = sorted(all_timestamps)
        print(f"Timeline creado: {len(timeline)} puntos temporales")
        
        # Ejecutar simulación
        for i, timestamp in enumerate(timeline):
            if i < 50:  # Skip primeros puntos por indicadores
                continue
                
            # Verificar control de riesgo
            total_loss = (self.initial_capital - self.capital) / self.initial_capital
            if total_loss >= self.max_total_loss or self.consecutive_losses >= self.max_consecutive_losses:
                print(f"Deteniendo por control de riesgo en {timestamp}")
                break
                
            # Verificar salidas de posiciones existentes
            for symbol in list(self.positions.keys()):
                if symbol in all_data and timestamp in all_data[symbol].index:
                    current_price = all_data[symbol].loc[timestamp, 'close']
                    exit_reason = self.check_position_exit(symbol, current_price, timestamp)
                    
                    if exit_reason:
                        self.execute_trade(symbol, "SELL", current_price, timestamp, exit_reason)
                        
            # Buscar nuevas entradas
            if len(self.positions) < self.max_positions:
                for symbol in symbols:
                    if symbol not in all_data or timestamp not in all_data[symbol].index:
                        continue
                        
                    if symbol in self.positions:  # Ya tenemos posición
                        continue
                        
                    df = all_data[symbol]
                    idx = df.index.get_loc(timestamp)
                    
                    if idx < 50:
                        continue
                        
                    probability, signal_type = self.calculate_signal_probability(df, idx)
                    
                    if probability > 0.65:  # Umbral de entrada
                        current_price = df.loc[timestamp, 'close']
                        self.execute_trade(symbol, "BUY", current_price, timestamp, 
                                         "Señal", signal_type)
                        
        # Cerrar posiciones abiertas
        for symbol in list(self.positions.keys()):
            if symbol in all_data:
                final_price = all_data[symbol]['close'].iloc[-1]
                final_time = all_data[symbol].index[-1]
                self.execute_trade(symbol, "SELL", final_price, final_time, "Final")
                
        return self.calculate_results()
        
    def calculate_results(self) -> Dict:
        """Calcula métricas de rendimiento"""
        if not self.trades:
            return {
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'max_drawdown': 0
            }
            
        df_trades = pd.DataFrame(self.trades)
        
        # Métricas básicas
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        win_rate = len(df_trades[df_trades['pnl_pct'] > 0]) / len(df_trades) * 100
        
        # Drawdown
        capital_curve = [self.initial_capital]
        running_capital = self.initial_capital
        
        for _, trade in df_trades.iterrows():
            running_capital += trade['pnl_amount']
            capital_curve.append(running_capital)
            
        capital_series = pd.Series(capital_curve)
        rolling_max = capital_series.expanding().max()
        drawdown = (capital_series - rolling_max) / rolling_max * 100
        max_drawdown = abs(drawdown.min())
        
        return {
            'initial_capital': self.initial_capital,
            'final_capital': self.capital,
            'total_return': total_return,
            'win_rate': win_rate,
            'total_trades': len(self.trades),
            'max_drawdown': max_drawdown,
            'trades': self.trades
        }

def main():
    """Función principal"""
    # Símbolos a probar (formato Binance)
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
    
    # Períodos a probar
    test_periods = [30, 60, 90]
    
    all_results = {}
    
    for days in test_periods:
        print(f"\n{'='*60}")
        print(f"PRUEBA CON {days} DÍAS DE DATOS REALES")
        print(f"{'='*60}")
        
        strategy = RealDataProbabilityStrategy(initial_capital=1000.0)
        results = strategy.run_backtest(symbols, days)
        
        if results:
            all_results[f'{days}_days'] = results
            
            print(f"\n=== RESULTADOS {days} DÍAS ===")
            print(f"Capital inicial: ${results['initial_capital']:,.2f}")
            print(f"Capital final: ${results['final_capital']:,.2f}")
            print(f"Retorno total: {results['total_return']:.2f}%")
            print(f"Tasa de acierto: {results['win_rate']:.2f}%")
            print(f"Total de trades: {results['total_trades']}")
            print(f"Máximo drawdown: {results['max_drawdown']:.2f}%")
            
            # Guardar resultados detallados
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"real_binance_results_{days}days_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"RESULTADOS ESTRATEGIA PROBABILIDAD DINÁMICA - DATOS REALES BINANCE\n")
                f.write(f"Período: {days} días\n")
                f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n\n")
                
                f.write(f"MÉTRICAS PRINCIPALES:\n")
                f.write(f"Capital inicial: ${results['initial_capital']:,.2f}\n")
                f.write(f"Capital final: ${results['final_capital']:,.2f}\n")
                f.write(f"Retorno total: {results['total_return']:.2f}%\n")
                f.write(f"Tasa de acierto: {results['win_rate']:.2f}%\n")
                f.write(f"Total de trades: {results['total_trades']}\n")
                f.write(f"Máximo drawdown: {results['max_drawdown']:.2f}%\n\n")
                
                if results['trades']:
                    f.write(f"DETALLE DE TRADES:\n")
                    f.write(f"{'='*80}\n")
                    for i, trade in enumerate(results['trades'], 1):
                        f.write(f"Trade {i}: {trade['symbol']}\n")
                        f.write(f"  Entrada: {trade['entry_time']} @ ${trade['entry_price']:.4f}\n")
                        f.write(f"  Salida: {trade['exit_time']} @ ${trade['exit_price']:.4f}\n")
                        f.write(f"  PnL: {trade['pnl_pct']:.2f}% (${trade['pnl_amount']:.2f})\n")
                        f.write(f"  Razón: {trade['reason']} | Tipo: {trade['signal_type']}\n")
                        f.write(f"  {'-'*40}\n")
                        
            print(f"Resultados guardados en: {filename}")
        else:
            print(f"No se pudieron obtener resultados para {days} días")
            
    # Resumen comparativo
    if all_results:
        print(f"\n{'='*60}")
        print("RESUMEN COMPARATIVO")
        print(f"{'='*60}")
        
        for period, results in all_results.items():
            days = period.replace('_days', '')
            print(f"{days} días: {results['total_return']:.2f}% retorno, {results['total_trades']} trades, {results['win_rate']:.1f}% acierto")
            
if __name__ == "__main__":
    main()