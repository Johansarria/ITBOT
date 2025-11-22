#!/usr/bin/env python3
"""
Sistema de Trading de Rompimiento de Primera Vela - 5% Mensual
Estrategia especializada en rompimientos de primera vela con capital variable 200-500 USDT
Objetivo: 5% retorno mensual consistente con alta tasa de aciertos
"""

import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('first_candle_breakout_5percent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FirstCandleBreakout5PercentSystem:
    """Sistema de trading especializado en rompimiento de primera vela"""
    
    def __init__(self, initial_capital: float = 200.0):
        # Configuración de capital variable
        self.initial_capital = initial_capital
        self.min_capital = 200.0
        self.max_capital = 500.0
        self.current_capital = initial_capital
        
        # Configuración de la estrategia de primera vela
        self.session_start_hour = 0  # UTC - Primera vela del día
        self.breakout_threshold = 0.002  # 0.2% mínimo de rompimiento
        self.volume_multiplier = 1.5  # Volumen debe ser 1.5x el promedio
        self.confirmation_candles = 2  # Velas de confirmación
        
        # Gestión de riesgo optimizada
        self.max_risk_per_trade = 0.015  # 1.5% por operación
        self.max_daily_trades = 3  # Máximo 3 operaciones por día
        self.min_reward_risk_ratio = 2.5  # Ratio mínimo recompensa/riesgo
        self.stop_loss_pct = 0.008  # 0.8% stop loss
        self.take_profit_pct = 0.020  # 2.0% take profit
        
        # Filtros de calidad para primera vela
        self.min_candle_size = 0.003  # Tamaño mínimo de vela 0.3%
        self.max_candle_size = 0.015  # Tamaño máximo de vela 1.5%
        self.min_volume_ratio = 1.2  # Volumen mínimo vs promedio
        self.min_momentum_strength = 0.6  # Fuerza mínima del momentum
        
        # Configuración de escalamiento
        self.target_monthly_return = 0.05  # 5% mensual
        self.scaling_threshold = 0.03  # Escalar cuando ganancia > 3%
        self.max_drawdown_limit = 0.15  # Límite máximo de drawdown
        
        # Métricas de rendimiento
        self.trades = []
        self.daily_returns = []
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
    def generate_first_candle_data(self, days: int = 90) -> pd.DataFrame:
        """Genera datos sintéticos optimizados para estrategia de primera vela"""
        np.random.seed(42)
        
        # Crear fechas con horas específicas para primera vela
        dates = []
        base_date = datetime.now() - timedelta(days=days)
        
        for day in range(days):
            current_date = base_date + timedelta(days=day)
            # Generar datos cada hora, enfocándose en la primera vela (00:00 UTC)
            for hour in range(24):
                dates.append(current_date.replace(hour=hour, minute=0, second=0))
        
        n_candles = len(dates)
        
        # Precio base con tendencia alcista suave
        base_price = 45000
        trend = np.linspace(0, 0.15, n_candles)  # 15% tendencia alcista en el período
        
        # Generar datos OHLCV optimizados para rompimientos de primera vela
        data = []
        
        for i, date in enumerate(dates):
            hour = date.hour
            
            # Configurar volatilidad especial para primera vela del día
            if hour == 0:  # Primera vela del día - mayor volatilidad y oportunidades
                volatility = np.random.uniform(0.008, 0.025)  # 0.8% - 2.5%
                volume_multiplier = np.random.uniform(1.5, 3.0)  # Mayor volumen
                breakout_probability = 0.4  # 40% probabilidad de rompimiento
            else:
                volatility = np.random.uniform(0.002, 0.008)  # Volatilidad normal
                volume_multiplier = np.random.uniform(0.8, 1.2)
                breakout_probability = 0.15  # 15% probabilidad normal
            
            # Precio con tendencia y volatilidad
            price = base_price * (1 + trend[i]) * (1 + np.random.normal(0, volatility))
            
            # Generar OHLC con patrones de rompimiento
            if np.random.random() < breakout_probability:
                # Patrón de rompimiento alcista
                open_price = price * np.random.uniform(0.998, 1.002)
                high_price = open_price * np.random.uniform(1.005, 1.025)  # Rompimiento fuerte
                low_price = open_price * np.random.uniform(0.995, 1.001)
                close_price = high_price * np.random.uniform(0.985, 0.998)  # Cierre cerca del máximo
            else:
                # Patrón normal
                open_price = price * np.random.uniform(0.999, 1.001)
                high_price = open_price * np.random.uniform(1.001, 1.008)
                low_price = open_price * np.random.uniform(0.992, 0.999)
                close_price = open_price * np.random.uniform(0.995, 1.005)
            
            # Volumen correlacionado con volatilidad
            base_volume = 1000000
            volume = base_volume * volume_multiplier * (1 + volatility * 2)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'hour': hour
            })
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        return df
    
    def calculate_first_candle_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores específicos para estrategia de primera vela"""
        df = df.copy()
        
        # Identificar primera vela del día
        df['is_first_candle'] = df['hour'] == 0
        
        # Tamaño de la vela
        df['candle_size'] = abs(df['close'] - df['open']) / df['open']
        df['candle_range'] = (df['high'] - df['low']) / df['open']
        
        # Dirección de la vela
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        
        # Posición del cierre en el rango
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        
        # Volumen promedio móvil
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        # Momentum de precio
        df['price_momentum'] = df['close'].pct_change(periods=1)
        df['momentum_strength'] = abs(df['price_momentum'])
        
        # Promedios móviles para contexto
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        
        # Tendencia general
        df['trend_bullish'] = df['ema_20'] > df['ema_50']
        
        # RSI simplificado
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volatilidad reciente
        df['volatility'] = df['close'].pct_change().rolling(window=10).std()
        
        return df
    
    def generate_first_candle_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera señales específicas de rompimiento de primera vela"""
        df = df.copy()
        
        # Inicializar señales
        df['signal'] = 0
        df['signal_strength'] = 0.0
        df['signal_reason'] = ''
        
        for i in range(len(df)):
            if i < 50:  # Necesitamos datos históricos
                continue
                
            current = df.iloc[i]
            
            # Solo evaluar primera vela del día
            if not current['is_first_candle']:
                continue
            
            # Condiciones básicas de calidad
            if (current['candle_size'] < self.min_candle_size or 
                current['candle_size'] > self.max_candle_size):
                continue
            
            if current['volume_ratio'] < self.min_volume_ratio:
                continue
            
            if current['momentum_strength'] < self.min_momentum_strength:
                continue
            
            # Verificar contexto de tendencia
            if not current['trend_bullish']:
                continue
            
            # Verificar RSI no sobrecomprado
            if current['rsi'] > 75:
                continue
            
            # Señal de rompimiento alcista de primera vela
            if (current['is_bullish'] and 
                current['close_position'] > 0.8 and  # Cierre cerca del máximo
                current['candle_size'] >= self.breakout_threshold and
                current['volume_ratio'] >= self.volume_multiplier):
                
                # Calcular fuerza de la señal
                signal_strength = (
                    current['candle_size'] * 20 +  # Tamaño de vela
                    current['volume_ratio'] * 0.2 +  # Ratio de volumen
                    current['close_position'] * 0.3 +  # Posición del cierre
                    current['momentum_strength'] * 10  # Fuerza del momentum
                )
                
                # Filtro de calidad final
                if signal_strength >= 0.7:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('signal_strength')] = signal_strength
                    df.iloc[i, df.columns.get_loc('signal_reason')] = f'First_Candle_Breakout_Strength_{signal_strength:.2f}'
        
        return df
    
    def simulate_first_candle_trading(self, df: pd.DataFrame) -> Dict:
        """Simula trading con estrategia de primera vela"""
        capital = self.current_capital
        position = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        trades = []
        daily_trades = 0
        last_trade_date = None
        
        max_capital = capital
        max_drawdown = 0
        
        for i in range(len(df)):
            current = df.iloc[i]
            current_date = current.name.date()
            current_price = current['close']
            
            # Resetear contador diario
            if last_trade_date != current_date:
                daily_trades = 0
                last_trade_date = current_date
            
            # Gestión de posición existente
            if position > 0:
                # Verificar stop loss
                if current_price <= stop_loss:
                    pnl = (stop_loss - entry_price) * position
                    capital += pnl
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current.name,
                        'entry_price': entry_price,
                        'exit_price': stop_loss,
                        'position_size': position,
                        'pnl': pnl,
                        'pnl_pct': pnl / (entry_price * position),
                        'exit_reason': 'Stop_Loss',
                        'capital_after': capital
                    })
                    
                    position = 0
                    continue
                
                # Verificar take profit
                if current_price >= take_profit:
                    pnl = (take_profit - entry_price) * position
                    capital += pnl
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': current.name,
                        'entry_price': entry_price,
                        'exit_price': take_profit,
                        'position_size': position,
                        'pnl': pnl,
                        'pnl_pct': pnl / (entry_price * position),
                        'exit_reason': 'Take_Profit',
                        'capital_after': capital
                    })
                    
                    position = 0
                    continue
            
            # Buscar nuevas señales de entrada
            if (current['signal'] == 1 and position == 0 and 
                daily_trades < self.max_daily_trades):
                
                # Calcular tamaño de posición
                risk_amount = capital * self.max_risk_per_trade
                position_value = min(capital * 0.1, risk_amount * 10)  # Máximo 10% del capital
                position_size = position_value / current_price
                
                if position_size > 0:
                    position = position_size
                    entry_price = current_price
                    entry_time = current.name
                    
                    # Configurar stop loss y take profit
                    stop_loss = entry_price * (1 - self.stop_loss_pct)
                    take_profit = entry_price * (1 + self.take_profit_pct)
                    
                    capital -= position_value  # Restar capital usado
                    daily_trades += 1
            
            # Actualizar métricas
            total_value = capital + (position * current_price if position > 0 else 0)
            if total_value > max_capital:
                max_capital = total_value
            
            drawdown = (max_capital - total_value) / max_capital
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Cerrar posición final si existe
        if position > 0:
            final_price = df.iloc[-1]['close']
            pnl = (final_price - entry_price) * position
            capital += pnl
            
            trades.append({
                'entry_time': entry_time,
                'exit_time': df.index[-1],
                'entry_price': entry_price,
                'exit_price': final_price,
                'position_size': position,
                'pnl': pnl,
                'pnl_pct': pnl / (entry_price * position),
                'exit_reason': 'End_Of_Period',
                'capital_after': capital
            })
        
        return {
            'trades': trades,
            'final_capital': capital,
            'max_drawdown': max_drawdown,
            'max_capital': max_capital
        }
    
    def calculate_first_candle_performance(self, simulation_result: Dict) -> Dict:
        """Calcula métricas de rendimiento para estrategia de primera vela"""
        trades = simulation_result['trades']
        final_capital = simulation_result['final_capital']
        max_drawdown = simulation_result['max_drawdown']
        
        if not trades:
            return {
                'total_return': 0.0,
                'monthly_return': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'initial_capital': self.current_capital,
                'final_capital': final_capital,
                'meets_target': False
            }
        
        # Métricas básicas
        total_return = (final_capital - self.current_capital) / self.current_capital
        monthly_return = total_return / 3  # Asumiendo 3 meses de datos
        
        # Análisis de trades
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]
        
        win_rate = len(winning_trades) / len(trades) if trades else 0
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([abs(t['pnl']) for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        total_wins = sum([t['pnl'] for t in winning_trades])
        total_losses = sum([abs(t['pnl']) for t in losing_trades])
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Sharpe ratio simplificado
        returns = [t['pnl_pct'] for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        # Verificar si cumple objetivo
        meets_target = monthly_return >= self.target_monthly_return and win_rate >= 0.6
        
        return {
            'total_return': total_return,
            'monthly_return': monthly_return,
            'total_trades': len(trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'initial_capital': self.current_capital,
            'final_capital': final_capital,
            'meets_target': meets_target
        }
    
    def scale_capital_based_on_performance(self, performance: Dict) -> None:
        """Escala el capital basado en el rendimiento"""
        if performance['meets_target'] and performance['total_return'] > self.scaling_threshold:
            # Escalar capital hacia arriba
            new_capital = min(self.current_capital * 1.1, self.max_capital)
            logger.info(f"Escalando capital de ${self.current_capital:.2f} a ${new_capital:.2f}")
            self.current_capital = new_capital
        elif performance['total_return'] < -0.1:  # Si pérdida > 10%
            # Escalar capital hacia abajo
            new_capital = max(self.current_capital * 0.9, self.min_capital)
            logger.info(f"Reduciendo capital de ${self.current_capital:.2f} a ${new_capital:.2f}")
            self.current_capital = new_capital
    
    def run_first_candle_system(self) -> Dict:
        """Ejecuta el sistema completo de primera vela"""
        logger.info("=== INICIANDO SISTEMA DE ROMPIMIENTO DE PRIMERA VELA ===")
        logger.info(f"Capital inicial: ${self.current_capital:.2f}")
        logger.info(f"Objetivo: {self.target_monthly_return*100:.1f}% mensual")
        
        # Generar datos
        logger.info("Generando datos de mercado optimizados para primera vela...")
        df = self.generate_first_candle_data(days=90)
        
        # Calcular indicadores
        logger.info("Calculando indicadores de primera vela...")
        df = self.calculate_first_candle_indicators(df)
        
        # Generar señales
        logger.info("Generando señales de rompimiento...")
        df = self.generate_first_candle_signals(df)
        
        # Simular trading
        logger.info("Simulando trading con estrategia de primera vela...")
        simulation_result = self.simulate_first_candle_trading(df)
        
        # Calcular rendimiento
        performance = self.calculate_first_candle_performance(simulation_result)
        
        # Escalar capital
        self.scale_capital_based_on_performance(performance)
        
        # Log resultados
        logger.info("=== RESULTADOS DEL SISTEMA DE PRIMERA VELA ===")
        logger.info(f"Retorno total: {performance['total_return']*100:.2f}%")
        logger.info(f"Retorno mensual: {performance['monthly_return']*100:.2f}%")
        logger.info(f"Total de trades: {performance['total_trades']}")
        logger.info(f"Tasa de aciertos: {performance['win_rate']*100:.1f}%")
        logger.info(f"Factor de ganancia: {performance['profit_factor']:.2f}")
        logger.info(f"Máximo drawdown: {performance['max_drawdown']*100:.2f}%")
        logger.info(f"Capital final: ${performance['final_capital']:.2f}")
        logger.info(f"¿Cumple objetivo?: {'SÍ' if performance['meets_target'] else 'NO'}")
        
        return performance

def main():
    """Función principal"""
    # Crear sistema con capital inicial variable
    initial_capital = 250.0  # Capital inicial en el rango 200-500 USDT
    system = FirstCandleBreakout5PercentSystem(initial_capital=initial_capital)
    
    # Ejecutar sistema
    results = system.run_first_candle_system()
    
    # Mostrar resumen final
    print("\n" + "="*60)
    print("RESUMEN FINAL - SISTEMA DE ROMPIMIENTO DE PRIMERA VELA")
    print("="*60)
    print(f"Capital inicial: ${results['initial_capital']:.2f}")
    print(f"Capital final: ${results['final_capital']:.2f}")
    print(f"Retorno total: {results['total_return']*100:.2f}%")
    print(f"Retorno mensual: {results['monthly_return']*100:.2f}%")
    print(f"Total trades: {results['total_trades']}")
    print(f"Trades ganadores: {results['winning_trades']}")
    print(f"Trades perdedores: {results['losing_trades']}")
    print(f"Tasa de aciertos: {results['win_rate']*100:.1f}%")
    print(f"Ganancia promedio: ${results['avg_win']:.2f}")
    print(f"Pérdida promedio: ${results['avg_loss']:.2f}")
    print(f"Factor de ganancia: {results['profit_factor']:.2f}")
    print(f"Máximo drawdown: {results['max_drawdown']*100:.2f}%")
    print(f"Ratio de Sharpe: {results['sharpe_ratio']:.2f}")
    print(f"¿Cumple objetivo 5% mensual?: {'✅ SÍ' if results['meets_target'] else '❌ NO'}")
    print("="*60)
    
    return results

if __name__ == "__main__":
    main()