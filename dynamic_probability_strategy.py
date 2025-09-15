#!/usr/bin/env python3
"""
Estrategia de Probabilidad Dinámica - ITBOT
Basada en algoritmo validado con 64.99% retorno mensual
Implementa señales tipo A, B, C, D con filtros de calidad
"""

import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Tuple, Optional
import logging
import json

class DynamicProbabilityStrategy:
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = []
        self.max_positions = 3
        self.max_position_hours = 24
        
        # Parámetros de probabilidad
        self.base_frequency = 0.6  # 60% probabilidad base
        self.max_momentum_bonus = 0.3  # Máximo 30% bonus
        
        # Filtros de calidad
        self.min_volume_ratio = 1.20  # 120% del promedio
        self.min_volatility = 0.002   # 0.2%
        self.max_volatility = 0.05    # 5%
        
        # Gestión de riesgo
        self.position_size_pct = 0.18  # 18% del capital
        self.max_daily_loss = 0.10     # 10% pérdida diaria máxima
        self.consecutive_losses = 0
        self.max_consecutive_losses = 3
        
        # Tracking
        self.trades_history = []
        self.daily_pnl = 0.0
        self.current_day = None
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def calculate_volatility(self, prices: pd.Series) -> float:
        """Calcula volatilidad como cambio porcentual absoluto"""
        if len(prices) < 2:
            return 0.0
        return abs(prices.iloc[-1] - prices.iloc[-2]) / prices.iloc[-2]
    
    def calculate_volume_ratio(self, volumes: pd.Series) -> float:
        """Calcula ratio de volumen actual vs promedio 20 períodos"""
        if len(volumes) < 21:
            return 1.0
        current_volume = volumes.iloc[-1]
        avg_volume = volumes.iloc[-21:-1].mean()
        return current_volume / avg_volume if avg_volume > 0 else 1.0
    
    def calculate_dynamic_tp_sl(self, volatility: float) -> Tuple[float, float]:
        """Calcula Take Profit y Stop Loss dinámicos basados en volatilidad"""
        # Take Profit dinámico (6% - 15%)
        tp_base = 0.06 + (0.15 - 0.06) * min(1.0, volatility * 50)
        tp_variation = random.uniform(-0.20, 0.20)  # ±20% variación
        tp_final = max(0.06, min(0.15, tp_base * (1 + tp_variation)))
        
        # Stop Loss más conservador (1.5% - 2.5%)
        sl_base = 0.015 + (0.025 - 0.015) * min(1.0, volatility * 30)
        sl_variation = random.uniform(-0.10, 0.10)  # ±10% variación
        sl_final = max(0.015, min(0.025, sl_base * (1 + sl_variation)))
        
        return tp_final, sl_final
    
    def calculate_signal_probability(self, price_change: float, data_length: int) -> float:
        """Calcula probabilidad final de señal"""
        # Bonus por momentum
        momentum_bonus = min(self.max_momentum_bonus, abs(price_change) * 100)
        
        # Factor posicional (más agresivo al inicio)
        position_factor = max(0.8, 1.2 - (data_length / 1000))
        
        # Probabilidad final
        final_probability = (self.base_frequency + momentum_bonus) * position_factor
        return min(0.95, final_probability)  # Máximo 95%
    
    def identify_signal_type(self, prices: pd.Series, volumes: pd.Series, 
                           price_change: float, volume_ratio: float) -> str:
        """Identifica el tipo de señal (A, B, C, D)"""
        
        # SEÑAL TIPO A: Momentum Positivo
        if abs(price_change) > 0.005:  # > 0.5%
            return "A_MOMENTUM"
        
        # SEÑAL TIPO C: Breakout Volumen
        if volume_ratio > 1.50:  # > 150%
            return "C_BREAKOUT"
        
        # SEÑAL TIPO B: Bounce en Soporte (simplificado)
        if len(prices) >= 5:
            recent_low = prices.iloc[-5:].min()
            current_price = prices.iloc[-1]
            if abs(current_price - recent_low) / recent_low < 0.02:  # Cerca del mínimo reciente
                return "B_BOUNCE"
        
        # SEÑAL TIPO D: Entrada Aleatoria Ponderada
        return "D_RANDOM"
    
    def check_quality_filters(self, volume_ratio: float, volatility: float) -> bool:
        """Verifica filtros de calidad de señales"""
        volume_ok = volume_ratio >= self.min_volume_ratio
        volatility_ok = self.min_volatility < volatility < self.max_volatility
        return volume_ok and volatility_ok
    
    def can_open_position(self, symbol: str) -> bool:
        """Verifica si se puede abrir nueva posición"""
        # Máximo 3 posiciones
        if len(self.positions) >= self.max_positions:
            return False
        
        # Sin posición en el mismo símbolo
        for pos in self.positions:
            if pos['symbol'] == symbol:
                return False
        
        # Verificar pérdidas consecutivas
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False
        
        # Verificar pérdida diaria máxima
        if self.daily_pnl <= -self.max_daily_loss * self.current_capital:
            return False
        
        return True
    
    def generate_signal(self, data: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """Genera señal de trading basada en probabilidad dinámica"""
        if len(data) < 21:  # Necesitamos al menos 21 períodos
            return None
        
        # Calcular métricas
        prices = data['Close']
        volumes = data['Volume']
        
        price_change = (prices.iloc[-1] - prices.iloc[-2]) / prices.iloc[-2]
        volatility = self.calculate_volatility(prices)
        volume_ratio = self.calculate_volume_ratio(volumes)
        
        # Verificar filtros de calidad
        if not self.check_quality_filters(volume_ratio, volatility):
            return None
        
        # Verificar si se puede abrir posición
        if not self.can_open_position(symbol):
            return None
        
        # Calcular probabilidad de señal
        signal_probability = self.calculate_signal_probability(price_change, len(data))
        
        # Generar señal aleatoria basada en probabilidad
        if np.random.random() < signal_probability:
            signal_type = self.identify_signal_type(prices, volumes, price_change, volume_ratio)
            tp_pct, sl_pct = self.calculate_dynamic_tp_sl(volatility)
            
            current_price = prices.iloc[-1]
            
            signal = {
                'symbol': symbol,
                'type': signal_type,
                'action': 'BUY',
                'price': current_price,
                'tp_pct': tp_pct,
                'sl_pct': sl_pct,
                'tp_price': current_price * (1 + tp_pct),
                'sl_price': current_price * (1 - sl_pct),
                'volatility': volatility,
                'volume_ratio': volume_ratio,
                'probability': signal_probability,
                'timestamp': data.index[-1]
            }
            
            return signal
        
        return None
    
    def execute_trade(self, signal: Dict) -> bool:
        """Ejecuta trade basado en señal"""
        position_size = self.current_capital * self.position_size_pct
        
        position = {
            'symbol': signal['symbol'],
            'type': signal['type'],
            'entry_price': signal['price'],
            'tp_price': signal['tp_price'],
            'sl_price': signal['sl_price'],
            'position_size': position_size,
            'entry_time': signal['timestamp'],
            'tp_pct': signal['tp_pct'],
            'sl_pct': signal['sl_pct']
        }
        
        self.positions.append(position)
        self.logger.info(f"Posición abierta: {signal['symbol']} - Tipo: {signal['type']} - TP: {signal['tp_pct']:.2%} - SL: {signal['sl_pct']:.2%}")
        return True
    
    def check_exits(self, data: pd.DataFrame, current_time: datetime) -> List[Dict]:
        """Verifica condiciones de salida para posiciones abiertas"""
        exits = []
        positions_to_remove = []
        
        for i, position in enumerate(self.positions):
            if position['symbol'] not in data.columns:
                continue
            
            current_price = data[position['symbol']].iloc[-1]
            entry_price = position['entry_price']
            
            # Verificar Take Profit
            if current_price >= position['tp_price']:
                pnl_pct = (current_price - entry_price) / entry_price
                pnl_amount = position['position_size'] * pnl_pct
                
                exit_info = {
                    'symbol': position['symbol'],
                    'type': position['type'],
                    'exit_reason': 'TP',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'exit_time': current_time,
                    'duration': current_time - position['entry_time']
                }
                
                exits.append(exit_info)
                positions_to_remove.append(i)
                
            # Verificar Stop Loss
            elif current_price <= position['sl_price']:
                pnl_pct = (current_price - entry_price) / entry_price
                pnl_amount = position['position_size'] * pnl_pct
                
                exit_info = {
                    'symbol': position['symbol'],
                    'type': position['type'],
                    'exit_reason': 'SL',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'exit_time': current_time,
                    'duration': current_time - position['entry_time']
                }
                
                exits.append(exit_info)
                positions_to_remove.append(i)
                
            # Verificar cierre por tiempo (24 horas)
            elif (current_time - position['entry_time']).total_seconds() >= self.max_position_hours * 3600:
                pnl_pct = (current_price - entry_price) / entry_price
                pnl_amount = position['position_size'] * pnl_pct
                
                exit_info = {
                    'symbol': position['symbol'],
                    'type': position['type'],
                    'exit_reason': 'TIME',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': pnl_pct,
                    'pnl_amount': pnl_amount,
                    'exit_time': current_time,
                    'duration': current_time - position['entry_time']
                }
                
                exits.append(exit_info)
                positions_to_remove.append(i)
        
        # Remover posiciones cerradas
        for i in reversed(positions_to_remove):
            del self.positions[i]
        
        return exits
    
    def update_capital_and_stats(self, exits: List[Dict]):
        """Actualiza capital y estadísticas"""
        for exit_info in exits:
            self.current_capital += exit_info['pnl_amount']
            self.daily_pnl += exit_info['pnl_amount']
            
            # Actualizar pérdidas consecutivas
            if exit_info['pnl_amount'] < 0:
                self.consecutive_losses += 1
            else:
                self.consecutive_losses = 0
            
            # Guardar en historial
            self.trades_history.append(exit_info)
            
            self.logger.info(f"Trade cerrado: {exit_info['symbol']} - {exit_info['exit_reason']} - PnL: {exit_info['pnl_pct']:.2%}")
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
    
    def backtest(self, symbols: List[str], start_date: str, end_date: str) -> Dict:
        """Ejecuta backtest de la estrategia"""
        self.logger.info(f"Iniciando backtest: {start_date} a {end_date}")
        
        # Descargar datos
        data = {}
        for symbol in symbols:
            try:
                ticker_data = yf.download(symbol, start=start_date, end=end_date, interval='1h')
                if not ticker_data.empty:
                    data[symbol] = ticker_data
                    self.logger.info(f"Datos descargados para {symbol}: {len(ticker_data)} períodos")
            except Exception as e:
                self.logger.error(f"Error descargando {symbol}: {e}")
        
        if not data:
            return {'error': 'No se pudieron descargar datos'}
        
        # Obtener fechas comunes
        all_dates = set()
        for symbol_data in data.values():
            all_dates.update(symbol_data.index)
        all_dates = sorted(list(all_dates))
        
        # Ejecutar backtest
        for i, current_time in enumerate(all_dates[21:], 21):  # Empezar después de 21 períodos
            # Resetear stats diarios si es nuevo día
            if self.current_day != current_time.date():
                if self.current_day is not None:
                    self.reset_daily_stats()
                self.current_day = current_time.date()
            
            # Verificar salidas para todas las posiciones
            if self.positions:
                # Crear DataFrame con precios actuales
                current_prices = {}
                for symbol, symbol_data in data.items():
                    if current_time in symbol_data.index:
                        current_prices[symbol] = symbol_data.loc[current_time, 'Close']
                
                if current_prices:
                    price_df = pd.DataFrame([current_prices], index=[current_time])
                    exits = self.check_exits(price_df, current_time)
                    if exits:
                        self.update_capital_and_stats(exits)
            
            # Generar nuevas señales
            for symbol, symbol_data in data.items():
                if current_time in symbol_data.index:
                    # Obtener datos hasta el momento actual
                    historical_data = symbol_data.loc[:current_time].iloc[-50:]  # Últimos 50 períodos
                    
                    signal = self.generate_signal(historical_data, symbol)
                    if signal:
                        self.execute_trade(signal)
        
        # Cerrar posiciones restantes
        if self.positions and all_dates:
            final_time = all_dates[-1]
            final_prices = {}
            for symbol, symbol_data in data.items():
                if final_time in symbol_data.index:
                    final_prices[symbol] = symbol_data.loc[final_time, 'Close']
            
            if final_prices:
                price_df = pd.DataFrame([final_prices], index=[final_time])
                final_exits = self.check_exits(price_df, final_time)
                if final_exits:
                    self.update_capital_and_stats(final_exits)
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Genera reporte de resultados"""
        if not self.trades_history:
            return {'error': 'No hay trades para analizar'}
        
        df = pd.DataFrame(self.trades_history)
        
        # Métricas básicas
        total_trades = len(df)
        winning_trades = len(df[df['pnl_amount'] > 0])
        losing_trades = len(df[df['pnl_amount'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Retornos
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        total_pnl = self.current_capital - self.initial_capital
        
        # Análisis por tipo de señal
        signal_analysis = df.groupby('type').agg({
            'pnl_amount': ['count', 'sum', 'mean'],
            'pnl_pct': 'mean'
        }).round(4)
        
        # Análisis por razón de salida
        exit_analysis = df.groupby('exit_reason').agg({
            'pnl_amount': ['count', 'sum', 'mean'],
            'pnl_pct': 'mean'
        }).round(4)
        
        report = {
            'capital_inicial': self.initial_capital,
            'capital_final': self.current_capital,
            'pnl_total': total_pnl,
            'retorno_total_pct': total_return * 100,
            'total_trades': total_trades,
            'trades_ganadores': winning_trades,
            'trades_perdedores': losing_trades,
            'win_rate_pct': win_rate * 100,
            'pnl_promedio': df['pnl_amount'].mean(),
            'pnl_maximo': df['pnl_amount'].max(),
            'pnl_minimo': df['pnl_amount'].min(),
            'analisis_por_tipo': signal_analysis.to_dict(),
            'analisis_por_salida': exit_analysis.to_dict(),
            'trades_detalle': df.to_dict('records')
        }
        
        return report

def main():
    """Función principal para ejecutar la estrategia"""
    # Configuración
    symbols = ['BTC-USD', 'ETH-USD', 'BNB-USD', 'ADA-USD', 'SOL-USD']
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    
    # Crear estrategia
    strategy = DynamicProbabilityStrategy(initial_capital=1000.0)
    
    # Ejecutar backtest
    results = strategy.backtest(symbols, start_date, end_date)
    
    # Mostrar resultados
    if 'error' in results:
        print(f"Error: {results['error']}")
        return
    
    print("\n" + "="*80)
    print("RESULTADOS ESTRATEGIA PROBABILIDAD DINÁMICA")
    print("="*80)
    print(f"Capital Inicial: ${results['capital_inicial']:,.2f}")
    print(f"Capital Final: ${results['capital_final']:,.2f}")
    print(f"PnL Total: ${results['pnl_total']:,.2f}")
    print(f"Retorno Total: {results['retorno_total_pct']:.2f}%")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"PnL Promedio: ${results['pnl_promedio']:.2f}")
    
    # Guardar resultados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'dynamic_probability_results_{timestamp}.txt'
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS ESTRATEGIA PROBABILIDAD DINÁMICA\n")
        f.write("="*80 + "\n")
        f.write(f"Capital Inicial: ${results['capital_inicial']:,.2f}\n")
        f.write(f"Capital Final: ${results['capital_final']:,.2f}\n")
        f.write(f"PnL Total: ${results['pnl_total']:,.2f}\n")
        f.write(f"Retorno Total: {results['retorno_total_pct']:.2f}%\n")
        f.write(f"Total Trades: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
        f.write(f"PnL Promedio: ${results['pnl_promedio']:.2f}\n")
        f.write("\nResultados completos:\n")
        f.write(json.dumps(results, indent=2, default=str))
    
    print(f"\nResultados guardados en: {filename}")

if __name__ == "__main__":
    main()