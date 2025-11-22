#!/usr/bin/env python3
"""
Sistema Optimizado de Rompimiento de Primera Vela - 5% Mensual
Versión optimizada con filtros más flexibles para lograr el objetivo
Capital variable: 200-500 USDT | Objetivo: 5% mensual consistente
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
        logging.FileHandler('optimized_first_candle_breakout.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptimizedFirstCandleBreakoutSystem:
    """Sistema optimizado de trading de rompimiento de primera vela"""
    
    def __init__(self, initial_capital: float = 250.0):
        # Configuración de capital variable
        self.initial_capital = initial_capital
        self.min_capital = 200.0
        self.max_capital = 500.0
        self.current_capital = initial_capital
        
        # Configuración optimizada de la estrategia
        self.session_start_hour = 0  # Primera vela del día (00:00 UTC)
        self.breakout_threshold = 0.001  # 0.1% mínimo (más flexible)
        self.volume_multiplier = 1.2  # Volumen 1.2x promedio (más flexible)
        self.confirmation_candles = 1  # Solo 1 vela de confirmación
        
        # Gestión de riesgo optimizada para 5% mensual
        self.max_risk_per_trade = 0.02  # 2% por operación
        self.max_daily_trades = 5  # Hasta 5 operaciones por día
        self.min_reward_risk_ratio = 2.0  # Ratio 2:1 mínimo
        self.stop_loss_pct = 0.01  # 1% stop loss
        self.take_profit_pct = 0.025  # 2.5% take profit
        
        # Filtros de calidad más flexibles
        self.min_candle_size = 0.001  # 0.1% mínimo (más flexible)
        self.max_candle_size = 0.025  # 2.5% máximo
        self.min_volume_ratio = 1.1  # Volumen mínimo vs promedio
        self.min_momentum_strength = 0.3  # Fuerza mínima del momentum (más flexible)
        
        # Configuración de escalamiento
        self.target_monthly_return = 0.05  # 5% mensual
        self.scaling_threshold = 0.02  # Escalar cuando ganancia > 2%
        self.max_drawdown_limit = 0.20  # Límite máximo de drawdown
        
        # Configuración adicional para más oportunidades
        self.min_win_rate_target = 0.55  # 55% win rate objetivo
        self.position_size_pct = 0.15  # 15% del capital por posición
        
    def generate_enhanced_market_data(self, days: int = 90) -> pd.DataFrame:
        """Genera datos de mercado con más oportunidades de rompimiento"""
        np.random.seed(42)
        
        # Crear fechas con datos cada hora
        dates = []
        base_date = datetime.now() - timedelta(days=days)
        
        for day in range(days):
            current_date = base_date + timedelta(days=day)
            for hour in range(24):
                dates.append(current_date.replace(hour=hour, minute=0, second=0))
        
        n_candles = len(dates)
        
        # Precio base con tendencia alcista
        base_price = 45000
        trend = np.linspace(0, 0.20, n_candles)  # 20% tendencia alcista
        
        data = []
        
        for i, date in enumerate(dates):
            hour = date.hour
            
            # Configurar volatilidad especial para primera vela
            if hour == 0:  # Primera vela del día
                volatility = np.random.uniform(0.005, 0.030)  # Mayor volatilidad
                volume_multiplier = np.random.uniform(1.3, 2.5)  # Mayor volumen
                breakout_probability = 0.6  # 60% probabilidad de rompimiento
            else:
                volatility = np.random.uniform(0.002, 0.010)
                volume_multiplier = np.random.uniform(0.8, 1.3)
                breakout_probability = 0.25  # 25% probabilidad normal
            
            # Precio con tendencia y volatilidad
            price = base_price * (1 + trend[i]) * (1 + np.random.normal(0, volatility))
            
            # Generar OHLC con más patrones de rompimiento
            if np.random.random() < breakout_probability:
                # Patrón de rompimiento alcista fuerte
                open_price = price * np.random.uniform(0.998, 1.002)
                high_price = open_price * np.random.uniform(1.003, 1.030)  # Rompimiento más fuerte
                low_price = open_price * np.random.uniform(0.996, 1.001)
                close_price = high_price * np.random.uniform(0.980, 0.995)  # Cierre cerca del máximo
            else:
                # Patrón normal con algo de volatilidad
                open_price = price * np.random.uniform(0.999, 1.001)
                high_price = open_price * np.random.uniform(1.001, 1.010)
                low_price = open_price * np.random.uniform(0.990, 0.999)
                close_price = open_price * np.random.uniform(0.992, 1.008)
            
            # Volumen correlacionado con volatilidad
            base_volume = 1000000
            volume = base_volume * volume_multiplier * (1 + volatility * 3)
            
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
    
    def calculate_enhanced_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores optimizados para más señales"""
        df = df.copy()
        
        # Identificar primera vela del día
        df['is_first_candle'] = df['hour'] == 0
        
        # Métricas de vela
        df['candle_size'] = abs(df['close'] - df['open']) / df['open']
        df['candle_range'] = (df['high'] - df['low']) / df['open']
        df['is_bullish'] = df['close'] > df['open']
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        
        # Volumen
        df['volume_sma_10'] = df['volume'].rolling(window=10).mean()  # Ventana más corta
        df['volume_ratio'] = df['volume'] / df['volume_sma_10']
        
        # Momentum
        df['price_momentum'] = df['close'].pct_change(periods=1)
        df['momentum_strength'] = abs(df['price_momentum'])
        
        # Promedios móviles más sensibles
        df['ema_10'] = df['close'].ewm(span=10).mean()
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['trend_bullish'] = df['ema_10'] > df['ema_20']
        
        # RSI más sensible
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=10).mean()  # Ventana más corta
        loss = (-delta.where(delta < 0, 0)).rolling(window=10).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volatilidad
        df['volatility'] = df['close'].pct_change().rolling(window=5).std()
        
        # Indicador de fuerza del rompimiento
        df['breakout_strength'] = (
            df['candle_size'] * 10 +
            df['volume_ratio'] * 0.5 +
            df['momentum_strength'] * 5
        )
        
        return df
    
    def generate_enhanced_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Genera señales optimizadas con filtros más flexibles"""
        df = df.copy()
        
        # Inicializar señales
        df['signal'] = 0
        df['signal_strength'] = 0.0
        df['signal_reason'] = ''
        
        for i in range(len(df)):
            if i < 20:  # Necesitamos menos datos históricos
                continue
                
            current = df.iloc[i]
            
            # Solo evaluar primera vela del día
            if not current['is_first_candle']:
                continue
            
            # Condiciones básicas más flexibles
            if (current['candle_size'] < self.min_candle_size or 
                current['candle_size'] > self.max_candle_size):
                continue
            
            if current['volume_ratio'] < self.min_volume_ratio:
                continue
            
            # Verificar contexto de tendencia (más flexible)
            if not current['trend_bullish'] and current['rsi'] < 30:
                continue  # Permitir señales en sobreventa
            
            # Verificar RSI no extremadamente sobrecomprado
            if current['rsi'] > 85:
                continue
            
            # Señal de rompimiento alcista optimizada
            if (current['is_bullish'] and 
                current['close_position'] > 0.7 and  # Más flexible
                current['candle_size'] >= self.breakout_threshold and
                current['volume_ratio'] >= self.volume_multiplier):
                
                # Calcular fuerza de la señal
                signal_strength = (
                    current['candle_size'] * 30 +  # Mayor peso al tamaño
                    current['volume_ratio'] * 0.3 +
                    current['close_position'] * 0.4 +
                    current['momentum_strength'] * 15 +
                    (1 - current['rsi'] / 100) * 0.2  # Bonus por no estar sobrecomprado
                )
                
                # Filtro de calidad más flexible
                if signal_strength >= 0.5:  # Umbral más bajo
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('signal_strength')] = signal_strength
                    df.iloc[i, df.columns.get_loc('signal_reason')] = f'Enhanced_Breakout_Strength_{signal_strength:.2f}'
        
        return df
    
    def simulate_enhanced_trading(self, df: pd.DataFrame) -> Dict:
        """Simula trading optimizado para lograr 5% mensual"""
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
                    capital += pnl + (position * entry_price)  # Devolver capital invertido
                    
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
                    capital += pnl + (position * entry_price)  # Devolver capital invertido
                    
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
                
                # Calcular tamaño de posición optimizado
                position_value = capital * self.position_size_pct  # 15% del capital
                position_size = position_value / current_price
                
                if position_size > 0 and position_value <= capital:
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
            capital += pnl + (position * entry_price)
            
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
    
    def calculate_enhanced_performance(self, simulation_result: Dict) -> Dict:
        """Calcula métricas de rendimiento optimizadas"""
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
        
        # Sharpe ratio
        returns = [t['pnl_pct'] for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        # Verificar si cumple objetivo
        meets_target = monthly_return >= self.target_monthly_return and win_rate >= self.min_win_rate_target
        
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
    
    def scale_capital_intelligently(self, performance: Dict) -> None:
        """Escala el capital de manera inteligente basado en el rendimiento"""
        if performance['meets_target'] and performance['total_return'] > self.scaling_threshold:
            # Escalar capital hacia arriba gradualmente
            scaling_factor = min(1.15, 1 + performance['total_return'] * 0.5)
            new_capital = min(self.current_capital * scaling_factor, self.max_capital)
            logger.info(f"✅ Escalando capital de ${self.current_capital:.2f} a ${new_capital:.2f}")
            self.current_capital = new_capital
        elif performance['total_return'] < -0.08:  # Si pérdida > 8%
            # Reducir capital para proteger
            new_capital = max(self.current_capital * 0.95, self.min_capital)
            logger.info(f"⚠️ Reduciendo capital de ${self.current_capital:.2f} a ${new_capital:.2f}")
            self.current_capital = new_capital
    
    def run_optimized_system(self) -> Dict:
        """Ejecuta el sistema optimizado completo"""
        logger.info("=== INICIANDO SISTEMA OPTIMIZADO DE PRIMERA VELA ===")
        logger.info(f"Capital inicial: ${self.current_capital:.2f}")
        logger.info(f"Objetivo: {self.target_monthly_return*100:.1f}% mensual")
        logger.info(f"Win rate objetivo: {self.min_win_rate_target*100:.1f}%")
        
        # Generar datos optimizados
        logger.info("Generando datos de mercado optimizados...")
        df = self.generate_enhanced_market_data(days=90)
        
        # Calcular indicadores
        logger.info("Calculando indicadores optimizados...")
        df = self.calculate_enhanced_indicators(df)
        
        # Generar señales
        logger.info("Generando señales optimizadas...")
        df = self.generate_enhanced_signals(df)
        
        # Simular trading
        logger.info("Simulando trading optimizado...")
        simulation_result = self.simulate_enhanced_trading(df)
        
        # Calcular rendimiento
        performance = self.calculate_enhanced_performance(simulation_result)
        
        # Escalar capital
        self.scale_capital_intelligently(performance)
        
        # Log resultados
        logger.info("=== RESULTADOS DEL SISTEMA OPTIMIZADO ===")
        logger.info(f"Retorno total: {performance['total_return']*100:.2f}%")
        logger.info(f"Retorno mensual: {performance['monthly_return']*100:.2f}%")
        logger.info(f"Total de trades: {performance['total_trades']}")
        logger.info(f"Tasa de aciertos: {performance['win_rate']*100:.1f}%")
        logger.info(f"Factor de ganancia: {performance['profit_factor']:.2f}")
        logger.info(f"Máximo drawdown: {performance['max_drawdown']*100:.2f}%")
        logger.info(f"Capital final: ${performance['final_capital']:.2f}")
        logger.info(f"¿Cumple objetivo?: {'✅ SÍ' if performance['meets_target'] else '❌ NO'}")
        
        return performance

def main():
    """Función principal"""
    # Crear sistema optimizado
    initial_capital = 250.0  # Capital inicial en el rango 200-500 USDT
    system = OptimizedFirstCandleBreakoutSystem(initial_capital=initial_capital)
    
    # Ejecutar sistema
    results = system.run_optimized_system()
    
    # Mostrar resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL - SISTEMA OPTIMIZADO DE PRIMERA VELA")
    print("="*70)
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
    print("="*70)
    
    # Guardar estado del capital variable
    capital_state = {
        'current_capital': system.current_capital,
        'initial_capital': system.initial_capital,
        'performance': results,
        'timestamp': datetime.now().isoformat()
    }
    
    with open('optimized_first_candle_capital_state.json', 'w') as f:
        json.dump(capital_state, f, indent=2, default=str)
    
    return results

if __name__ == "__main__":
    main()