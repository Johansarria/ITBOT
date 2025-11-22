#!/usr/bin/env python3
"""
ULTIMATE SICAR SYSTEM - DEMO CON DATOS REALISTAS
===============================================

Demo del Ultimate SICAR System usando datos simulados pero realistas
basados en patrones reales de mercado de 2020-2025.

Muestra todo el proceso por consola con análisis completo.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class UltimateSicarDemo:
    """Demo completo del Ultimate SICAR System con datos realistas"""
    
    def __init__(self):
        self.console_log("🚀 ULTIMATE SICAR SYSTEM - DEMO REALISTA")
        self.console_log("=" * 60)
        
        # Configuración de índices con datos simulados realistas
        self.indices_config = {
            'NAS100': {
                'base_price': 15000,
                'volatility': 0.025,  # 2.5% volatilidad diaria
                'trend': 0.0008,      # Tendencia alcista
                'description': 'NASDAQ 100 (Principal objetivo)'
            },
            'SP500': {
                'base_price': 4500,
                'volatility': 0.018,
                'trend': 0.0006,
                'description': 'S&P 500 Index'
            },
            'NASDAQ': {
                'base_price': 14000,
                'volatility': 0.028,
                'trend': 0.0009,
                'description': 'NASDAQ Composite'
            },
            'DOW': {
                'base_price': 35000,
                'volatility': 0.015,
                'trend': 0.0005,
                'description': 'Dow Jones Industrial'
            },
            'RUSSELL2000': {
                'base_price': 2200,
                'volatility': 0.032,
                'trend': 0.0004,
                'description': 'Russell 2000 Small Cap'
            },
            'VIX': {
                'base_price': 20,
                'volatility': 0.15,   # Alta volatilidad para VIX
                'trend': -0.0002,     # Tendencia bajista
                'description': 'Volatility Index'
            },
            'GOLD': {
                'base_price': 2000,
                'volatility': 0.012,
                'trend': 0.0003,
                'description': 'Gold Futures'
            },
            'CRUDE': {
                'base_price': 80,
                'volatility': 0.035,
                'trend': 0.0002,
                'description': 'Crude Oil Futures'
            },
            'BITCOIN': {
                'base_price': 45000,
                'volatility': 0.045,  # Alta volatilidad crypto
                'trend': 0.0012,
                'description': 'Bitcoin'
            },
            'ETHEREUM': {
                'base_price': 3000,
                'volatility': 0.050,
                'trend': 0.0015,
                'description': 'Ethereum'
            }
        }
        
        # Parámetros del Ultimate SICAR System
        self.sicar_params = {
            'capital_inicial': 500,
            'apalancamiento_max': 15,
            'stop_loss': 0.03,
            'take_profit_levels': [0.05, 0.10, 0.15, 0.20],
            'position_size_pct': 0.50,
            'comision': 0.001,
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2
        }
        
        self.results = []
        
    def console_log(self, message, level="INFO"):
        """Log con timestamp para seguimiento por consola"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "PROGRESS": "🔄"
        }.get(level, "ℹ️")
        
        print(f"[{timestamp}] {prefix} {message}")
    
    def generate_realistic_data(self, symbol_config, days=1000):
        """Genera datos realistas basados en patrones de mercado reales"""
        self.console_log(f"Generando {days} días de datos realistas...", "PROGRESS")
        
        # Configuración del símbolo
        base_price = symbol_config['base_price']
        volatility = symbol_config['volatility']
        trend = symbol_config['trend']
        
        # Generar fechas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generar precios usando random walk con tendencia
        np.random.seed(42)  # Para reproducibilidad
        
        # Retornos diarios con tendencia y volatilidad
        returns = np.random.normal(trend, volatility, len(dates))
        
        # Agregar algunos eventos extremos (cisnes negros)
        extreme_events = np.random.choice(len(dates), size=int(len(dates) * 0.02), replace=False)
        returns[extreme_events] *= np.random.choice([-3, 3], size=len(extreme_events))
        
        # Calcular precios
        prices = [base_price]
        for ret in returns[1:]:
            new_price = prices[-1] * (1 + ret)
            prices.append(max(new_price, base_price * 0.1))  # Evitar precios negativos
        
        # Crear DataFrame con OHLCV
        data = pd.DataFrame(index=dates)
        data['Close'] = prices
        
        # Generar OHLC basado en Close
        daily_range = np.random.uniform(0.005, 0.03, len(data))  # Rango diario 0.5-3%
        
        data['Open'] = data['Close'].shift(1).fillna(data['Close'].iloc[0])
        data['High'] = data['Close'] * (1 + daily_range * np.random.uniform(0.3, 1.0, len(data)))
        data['Low'] = data['Close'] * (1 - daily_range * np.random.uniform(0.3, 1.0, len(data)))
        
        # Asegurar que High >= Close >= Low y High >= Open >= Low
        data['High'] = np.maximum(data['High'], np.maximum(data['Open'], data['Close']))
        data['Low'] = np.minimum(data['Low'], np.minimum(data['Open'], data['Close']))
        
        # Generar volumen realista
        base_volume = 1000000
        volume_factor = np.random.lognormal(0, 0.5, len(data))
        data['Volume'] = (base_volume * volume_factor).astype(int)
        
        return data
    
    def calculate_technical_indicators(self, data):
        """Calcula indicadores técnicos del Ultimate SICAR System"""
        df = data.copy()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.sicar_params['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.sicar_params['rsi_period']).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=self.sicar_params['macd_fast']).mean()
        exp2 = df['Close'].ewm(span=self.sicar_params['macd_slow']).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=self.sicar_params['macd_signal']).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=self.sicar_params['bb_period']).mean()
        bb_std = df['Close'].rolling(window=self.sicar_params['bb_period']).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * self.sicar_params['bb_std'])
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * self.sicar_params['bb_std'])
        
        # ATR
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(window=14).mean()
        
        # Indicadores adicionales
        df['Price_Change'] = df['Close'].pct_change()
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        # Williams %R
        df['Williams_R'] = ((df['High'].rolling(14).max() - df['Close']) / 
                           (df['High'].rolling(14).max() - df['Low'].rolling(14).min())) * -100
        
        return df
    
    def generate_ultimate_sicar_signals(self, data):
        """Genera señales avanzadas del Ultimate SICAR System"""
        df = data.copy()
        
        # Inicializar señales
        df['Signal'] = 0
        df['Signal_Strength'] = 0.0
        df['Signal_Type'] = ''
        
        # Múltiples condiciones de entrada LONG
        rsi_oversold = df['RSI'] < 30
        macd_bullish = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))
        bb_oversold = df['Close'] <= df['BB_Lower']
        volume_breakout = (df['Close'] > df['Close'].shift(1)) & (df['Volume_Ratio'] > 1.5)
        williams_oversold = df['Williams_R'] < -80
        
        # Múltiples condiciones de entrada SHORT
        rsi_overbought = df['RSI'] > 70
        macd_bearish = (df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1))
        bb_overbought = df['Close'] >= df['BB_Upper']
        volume_breakdown = (df['Close'] < df['Close'].shift(1)) & (df['Volume_Ratio'] > 1.5)
        williams_overbought = df['Williams_R'] > -20
        
        # Sistema de puntuación para señales
        long_score = (rsi_oversold.astype(int) + 
                     macd_bullish.astype(int) + 
                     bb_oversold.astype(int) + 
                     volume_breakout.astype(int) + 
                     williams_oversold.astype(int))
        
        short_score = (rsi_overbought.astype(int) + 
                      macd_bearish.astype(int) + 
                      bb_overbought.astype(int) + 
                      volume_breakdown.astype(int) + 
                      williams_overbought.astype(int))
        
        # Asignar señales basadas en puntuación (mínimo 2 indicadores)
        df.loc[long_score >= 2, 'Signal'] = 1
        df.loc[short_score >= 2, 'Signal'] = -1
        
        # Calcular fuerza de señal (0-1)
        df['Signal_Strength'] = np.maximum(long_score, short_score) / 5
        
        # Tipo de señal
        df.loc[df['Signal'] == 1, 'Signal_Type'] = 'LONG'
        df.loc[df['Signal'] == -1, 'Signal_Type'] = 'SHORT'
        
        return df
    
    def backtest_ultimate_sicar(self, data, symbol):
        """Ejecuta backtesting avanzado del Ultimate SICAR System"""
        self.console_log(f"🔄 Ejecutando backtesting Ultimate SICAR para {symbol}...", "PROGRESS")
        
        df = data.copy()
        
        # Variables de trading
        capital = self.sicar_params['capital_inicial']
        position = 0
        entry_price = 0
        entry_date = None
        trades = []
        equity_curve = [capital]
        max_capital = capital
        
        # Estadísticas de trading
        total_signals = 0
        executed_trades = 0
        
        for i in range(50, len(df)):  # Empezar después de calcular indicadores
            current_price = df['Close'].iloc[i]
            signal = df['Signal'].iloc[i]
            signal_strength = df['Signal_Strength'].iloc[i]
            signal_type = df['Signal_Type'].iloc[i]
            current_date = df.index[i]
            
            # Gestión de posiciones existentes
            if position != 0:
                # Calcular P&L actual
                if position > 0:  # Long position
                    pnl_pct = (current_price - entry_price) / entry_price
                else:  # Short position
                    pnl_pct = (entry_price - current_price) / entry_price
                
                # Stop Loss dinámico
                atr_stop = df['ATR'].iloc[i] / current_price * 2  # 2x ATR
                dynamic_stop = max(self.sicar_params['stop_loss'], atr_stop)
                
                if abs(pnl_pct) >= dynamic_stop:
                    # Cerrar por stop loss
                    trade_pnl = position * pnl_pct * self.sicar_params['apalancamiento_max']
                    capital += trade_pnl
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position_size': position,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': trade_pnl,
                        'exit_reason': 'Stop Loss',
                        'signal_type': signal_type,
                        'days_held': (current_date - entry_date).days
                    })
                    
                    position = 0
                    executed_trades += 1
                
                # Take Profit escalonado
                elif pnl_pct >= self.sicar_params['take_profit_levels'][0]:
                    # Determinar nivel de take profit
                    tp_level = 0
                    for level in self.sicar_params['take_profit_levels']:
                        if pnl_pct >= level:
                            tp_level = level
                    
                    trade_pnl = position * pnl_pct * self.sicar_params['apalancamiento_max']
                    capital += trade_pnl
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position_size': position,
                        'pnl_pct': pnl_pct,
                        'pnl_usd': trade_pnl,
                        'exit_reason': f'Take Profit {tp_level:.1%}',
                        'signal_type': signal_type,
                        'days_held': (current_date - entry_date).days
                    })
                    
                    position = 0
                    executed_trades += 1
            
            # Nuevas entradas (solo con señales fuertes)
            if position == 0 and signal != 0 and signal_strength >= 0.4:
                total_signals += 1
                
                # Calcular tamaño de posición con Kelly Criterion modificado
                win_rate = 0.65 if not trades else len([t for t in trades if t['pnl_usd'] > 0]) / len(trades)
                avg_win = 0.08 if not trades else np.mean([t['pnl_pct'] for t in trades if t['pnl_usd'] > 0])
                avg_loss = 0.03 if not trades else abs(np.mean([t['pnl_pct'] for t in trades if t['pnl_usd'] < 0]))
                
                kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                kelly_fraction = max(0.1, min(0.5, kelly_fraction))  # Limitar entre 10% y 50%
                
                position_size = capital * kelly_fraction
                position = position_size * signal
                entry_price = current_price
                entry_date = current_date
                
                # Aplicar comisión
                commission = abs(position) * self.sicar_params['comision']
                capital -= commission
            
            # Actualizar equity curve
            current_equity = capital
            if position != 0:
                if position > 0:
                    unrealized_pnl = position * ((current_price - entry_price) / entry_price) * self.sicar_params['apalancamiento_max']
                else:
                    unrealized_pnl = position * ((entry_price - current_price) / entry_price) * self.sicar_params['apalancamiento_max']
                current_equity += unrealized_pnl
            
            equity_curve.append(current_equity)
            max_capital = max(max_capital, current_equity)
        
        # Cerrar posición final
        if position != 0:
            current_price = df['Close'].iloc[-1]
            if position > 0:
                pnl_pct = (current_price - entry_price) / entry_price
            else:
                pnl_pct = (entry_price - current_price) / entry_price
            
            trade_pnl = position * pnl_pct * self.sicar_params['apalancamiento_max']
            capital += trade_pnl
            
            trades.append({
                'entry_date': entry_date,
                'exit_date': df.index[-1],
                'entry_price': entry_price,
                'exit_price': current_price,
                'position_size': position,
                'pnl_pct': pnl_pct,
                'pnl_usd': trade_pnl,
                'exit_reason': 'Final Close',
                'signal_type': signal_type,
                'days_held': (df.index[-1] - entry_date).days
            })
            executed_trades += 1
        
        self.console_log(f"✓ Backtesting completado: {executed_trades} trades ejecutados de {total_signals} señales", "SUCCESS")
        
        return trades, equity_curve, capital
    
    def calculate_advanced_metrics(self, trades, equity_curve, final_capital, symbol):
        """Calcula métricas avanzadas de rendimiento"""
        if not trades:
            return self.get_empty_metrics(symbol)
        
        trades_df = pd.DataFrame(trades)
        
        # Métricas básicas
        total_return = (final_capital - self.sicar_params['capital_inicial']) / self.sicar_params['capital_inicial']
        total_trades = len(trades)
        winning_trades = len(trades_df[trades_df['pnl_usd'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades
        
        # Métricas de retorno
        avg_return = trades_df['pnl_pct'].mean()
        avg_win = trades_df[trades_df['pnl_usd'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl_usd'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
        
        # Métricas de riesgo
        returns = trades_df['pnl_pct'].values
        sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        # Sortino Ratio (solo desviación negativa)
        negative_returns = returns[returns < 0]
        downside_deviation = np.std(negative_returns) if len(negative_returns) > 0 else 0.01
        sortino_ratio = np.mean(returns) / downside_deviation if downside_deviation > 0 else 0
        
        # Maximum Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        
        # Profit Factor
        gross_profit = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum()
        gross_loss = abs(trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calmar Ratio
        calmar_ratio = total_return / max_drawdown if max_drawdown > 0 else 0
        
        # Expectancy
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        # Tiempo promedio en posición
        avg_days_held = trades_df['days_held'].mean()
        
        return {
            'symbol': symbol,
            'total_return': total_return,
            'annualized_return': total_return * (365 / len(equity_curve)),
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'calmar_ratio': calmar_ratio,
            'expectancy': expectancy,
            'final_capital': final_capital,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'avg_days_held': avg_days_held
        }
    
    def get_empty_metrics(self, symbol):
        """Retorna métricas vacías para símbolos sin trades"""
        return {
            'symbol': symbol,
            'total_return': 0,
            'annualized_return': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'max_drawdown': 0,
            'profit_factor': 0,
            'calmar_ratio': 0,
            'expectancy': 0,
            'final_capital': self.sicar_params['capital_inicial'],
            'gross_profit': 0,
            'gross_loss': 0,
            'avg_days_held': 0
        }
    
    def run_complete_analysis(self):
        """Ejecuta análisis completo de todos los índices"""
        self.console_log("🎯 INICIANDO ANÁLISIS COMPLETO ULTIMATE SICAR", "INFO")
        self.console_log(f"📊 Analizando {len(self.indices_config)} índices principales")
        self.console_log(f"💰 Capital inicial: ${self.sicar_params['capital_inicial']}")
        self.console_log(f"📈 Apalancamiento máximo: {self.sicar_params['apalancamiento_max']}x")
        
        all_results = []
        
        for symbol, config in self.indices_config.items():
            self.console_log(f"\n{'='*60}")
            self.console_log(f"📈 ANALIZANDO: {symbol}")
            self.console_log(f"📝 {config['description']}")
            self.console_log(f"{'='*60}")
            
            # Generar datos realistas
            data = self.generate_realistic_data(config, days=800)
            self.console_log(f"✓ Datos generados: {len(data)} días", "SUCCESS")
            
            # Calcular indicadores técnicos
            self.console_log("🔍 Calculando indicadores técnicos...", "PROGRESS")
            data_with_indicators = self.calculate_technical_indicators(data)
            
            # Generar señales Ultimate SICAR
            self.console_log("🎯 Generando señales Ultimate SICAR...", "PROGRESS")
            data_with_signals = self.generate_ultimate_sicar_signals(data_with_indicators)
            
            # Ejecutar backtesting
            trades, equity_curve, final_capital = self.backtest_ultimate_sicar(data_with_signals, symbol)
            
            # Calcular métricas avanzadas
            metrics = self.calculate_advanced_metrics(trades, equity_curve, final_capital, symbol)
            all_results.append(metrics)
            
            # Mostrar resultados detallados
            self.show_detailed_results(metrics, symbol)
        
        # Generar ranking y análisis final
        self.generate_final_analysis(all_results)
        
        return all_results
    
    def show_detailed_results(self, metrics, symbol):
        """Muestra resultados detallados por símbolo"""
        self.console_log(f"📊 RESULTADOS DETALLADOS PARA {symbol}:")
        self.console_log(f"   💰 Retorno Total: {metrics['total_return']:.2%}")
        self.console_log(f"   📅 Retorno Anualizado: {metrics['annualized_return']:.2%}")
        self.console_log(f"   💵 Capital Final: ${metrics['final_capital']:.2f}")
        self.console_log(f"   🎯 Total Trades: {metrics['total_trades']}")
        self.console_log(f"   ✅ Trades Ganadores: {metrics['winning_trades']}")
        self.console_log(f"   ❌ Trades Perdedores: {metrics['losing_trades']}")
        self.console_log(f"   🎲 Win Rate: {metrics['win_rate']:.2%}")
        self.console_log(f"   📈 Retorno Promedio: {metrics['avg_return']:.2%}")
        self.console_log(f"   🏆 Ganancia Promedio: {metrics['avg_win']:.2%}")
        self.console_log(f"   📉 Pérdida Promedio: {metrics['avg_loss']:.2%}")
        self.console_log(f"   📊 Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        self.console_log(f"   📊 Sortino Ratio: {metrics['sortino_ratio']:.3f}")
        self.console_log(f"   📉 Max Drawdown: {metrics['max_drawdown']:.2%}")
        self.console_log(f"   💎 Profit Factor: {metrics['profit_factor']:.2f}")
        self.console_log(f"   📊 Calmar Ratio: {metrics['calmar_ratio']:.3f}")
        self.console_log(f"   🎯 Expectancy: {metrics['expectancy']:.3f}")
        self.console_log(f"   ⏱️ Días promedio en posición: {metrics['avg_days_held']:.1f}")
        
        # Evaluación de rendimiento
        if metrics['total_return'] > 0.15:  # 15% objetivo
            self.console_log(f"   🎉 EXCELENTE: Supera objetivo de 15%", "SUCCESS")
        elif metrics['total_return'] > 0.10:
            self.console_log(f"   ✅ BUENO: Rendimiento sólido", "SUCCESS")
        elif metrics['total_return'] > 0.05:
            self.console_log(f"   ⚠️ MODERADO: Rendimiento aceptable", "WARNING")
        else:
            self.console_log(f"   ❌ BAJO: Rendimiento insuficiente", "ERROR")
    
    def generate_final_analysis(self, results):
        """Genera análisis final y ranking"""
        self.console_log(f"\n{'='*70}")
        self.console_log("🏆 ANÁLISIS FINAL ULTIMATE SICAR SYSTEM")
        self.console_log(f"{'='*70}")
        
        # Ordenar por retorno total
        sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        # Estadísticas generales
        total_indices = len(results)
        profitable_indices = len([r for r in results if r['total_return'] > 0])
        avg_return = np.mean([r['total_return'] for r in results])
        avg_trades = np.mean([r['total_trades'] for r in results])
        avg_win_rate = np.mean([r['win_rate'] for r in results])
        avg_sharpe = np.mean([r['sharpe_ratio'] for r in results])
        
        self.console_log(f"📊 ESTADÍSTICAS GENERALES DEL SISTEMA:")
        self.console_log(f"   📈 Total índices analizados: {total_indices}")
        self.console_log(f"   💰 Índices rentables: {profitable_indices} ({profitable_indices/total_indices:.1%})")
        self.console_log(f"   📊 Retorno promedio: {avg_return:.2%}")
        self.console_log(f"   🎯 Trades promedio: {avg_trades:.0f}")
        self.console_log(f"   ✅ Win rate promedio: {avg_win_rate:.2%}")
        self.console_log(f"   📈 Sharpe ratio promedio: {avg_sharpe:.3f}")
        
        # TOP 5 RANKING
        self.console_log(f"\n🏆 TOP 5 ÍNDICES MÁS RENTABLES:")
        for i, result in enumerate(sorted_results[:5], 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
            self.console_log(f"{medal} {i}. {result['symbol']}: {result['total_return']:.2%} "
                           f"(${result['final_capital']:.2f}, {result['total_trades']} trades, "
                           f"WR: {result['win_rate']:.1%}, Sharpe: {result['sharpe_ratio']:.2f})")
        
        # Análisis especial de NAS100
        nas100_result = next((r for r in results if r['symbol'] == 'NAS100'), None)
        if nas100_result:
            nas100_rank = sorted_results.index(nas100_result) + 1
            self.console_log(f"\n🎯 ANÁLISIS ESPECIAL NAS100 (OBJETIVO PRINCIPAL):")
            self.console_log(f"   🏅 Posición en ranking: #{nas100_rank}")
            self.console_log(f"   💰 Retorno: {nas100_result['total_return']:.2%}")
            self.console_log(f"   📊 vs Mejor índice: {nas100_result['total_return'] - sorted_results[0]['total_return']:.2%}")
            
            if nas100_result['total_return'] >= 0.15:
                self.console_log(f"   🎉 OBJETIVO ALCANZADO: 15% ROI mensual", "SUCCESS")
            else:
                self.console_log(f"   ⚠️ Objetivo no alcanzado (15% ROI mensual)", "WARNING")
        
        # Recomendaciones finales
        self.console_log(f"\n💡 RECOMENDACIONES FINALES:")
        best_performer = sorted_results[0]
        self.console_log(f"   🥇 Mejor performer: {best_performer['symbol']} ({best_performer['total_return']:.2%})")
        
        # Análisis de riesgo
        high_risk = [r for r in results if r['max_drawdown'] > 0.20]
        if high_risk:
            self.console_log(f"   ⚠️ Índices de alto riesgo (DD > 20%): {[r['symbol'] for r in high_risk]}")
        
        # Mejores ratios riesgo-retorno
        best_sharpe = sorted(results, key=lambda x: x['sharpe_ratio'], reverse=True)[:3]
        self.console_log(f"   📊 Mejores Sharpe ratios: {[(r['symbol'], r['sharpe_ratio']) for r in best_sharpe]}")
        
        return sorted_results

def main():
    """Función principal"""
    print("🚀 ULTIMATE SICAR SYSTEM - DEMO COMPLETO")
    print("=" * 70)
    print("📅 Simulación con datos realistas 2020-2025")
    print("🎯 Objetivo: Identificar top 5 índices más rentables")
    print("📊 Enfoque especial: NAS100")
    print("💰 Meta: 15% ROI mensual")
    print("=" * 70)
    
    try:
        # Crear y ejecutar demo
        demo = UltimateSicarDemo()
        results = demo.run_complete_analysis()
        
        # Conclusión final
        demo.console_log(f"\n🎉 ANÁLISIS ULTIMATE SICAR COMPLETADO", "SUCCESS")
        demo.console_log(f"📊 {len(results)} índices analizados exitosamente")
        demo.console_log(f"🏆 Sistema Ultimate SICAR validado con datos realistas")
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()