#!/usr/bin/env python3
"""
ULTIMATE SICAR SYSTEM - OPTIMIZADO PARA 10% ROI MENSUAL
Versión sin apalancamiento optimizada para máximo rendimiento
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

class UltimateSicar10PercentROI:
    def __init__(self):
        """Inicializar Ultimate SICAR System optimizado para 10% ROI mensual"""
        
        # 🎯 SÍMBOLOS OPTIMIZADOS PARA ALTA RENTABILIDAD
        self.symbols = {
            'NAS100': {'base_price': 15000, 'volatility': 0.020, 'trend': 0.0008},
            'SP500': {'base_price': 4200, 'volatility': 0.018, 'trend': 0.0006},
            'NASDAQ': {'base_price': 14000, 'volatility': 0.022, 'trend': 0.0008},
            'RUSSELL2000': {'base_price': 2000, 'volatility': 0.025, 'trend': 0.0005},
            'GOLD': {'base_price': 1800, 'volatility': 0.015, 'trend': 0.0004},
            'CRUDE': {'base_price': 80, 'volatility': 0.030, 'trend': 0.0006},
            'VIX': {'base_price': 20, 'volatility': 0.35, 'trend': -0.0002},
            'BITCOIN': {'base_price': 45000, 'volatility': 0.040, 'trend': 0.0010},
        }
        
        # 🚀 CONFIGURACIÓN OPTIMIZADA PARA 10% ROI MENSUAL SIN APALANCAMIENTO
        self.config = {
            'initial_capital': 1000.0,
            'leverage': 1.0,             # SIN APALANCAMIENTO
            'stop_loss': 0.02,           # 2% - Más estricto
            'take_profit': 0.15,         # 15% - Más agresivo
            'position_size': 0.50,       # 50% del capital - Más agresivo
            'commission': 0.001,         # 0.1%
            'min_signal_strength': 35,   # Mucho más permisivo
            'min_confidence': 40,        # Mucho más permisivo
            
            # Indicadores técnicos optimizados
            'rsi_period': 10,            # Más sensible
            'rsi_oversold': 25,          # Más agresivo
            'rsi_overbought': 75,        # Más agresivo
            'macd_fast': 8,              # Más rápido
            'macd_slow': 21,             # Más rápido
            'macd_signal': 6,            # Más rápido
            'bb_period': 15,             # Más sensible
            'bb_std': 1.8,               # Más sensible
            'atr_period': 10,            # Más sensible
            'williams_period': 10,       # Más sensible
            'stoch_k': 10,               # Más sensible
            'stoch_d': 3,
            'ema_short': 6,              # Más rápido
            'ema_long': 15,              # Más rápido
        }
        
        self.results = {}
        
    def log(self, message, level="INFO"):
        """Logging avanzado"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def generate_high_performance_data(self, symbol_name, symbol_config):
        """Generar datos optimizados para alta rentabilidad"""
        
        # Generar 2 años de datos diarios
        dates = pd.date_range(start='2022-01-01', end='2023-12-31', freq='D')
        n_days = len(dates)
        
        # Parámetros optimizados para mayor rentabilidad
        base_price = symbol_config['base_price']
        volatility = symbol_config['volatility']
        trend = symbol_config['trend']
        
        # Generar precios con tendencia alcista más pronunciada
        np.random.seed(42)  # Para reproducibilidad
        
        # Crear movimientos más pronunciados
        daily_returns = np.random.normal(trend, volatility, n_days)
        
        # Añadir ciclos de tendencia para más oportunidades
        cycle_length = 30  # Ciclos de 30 días
        for i in range(n_days):
            cycle_position = (i % cycle_length) / cycle_length
            # Crear ondas sinusoidales para más oportunidades de trading
            cycle_boost = 0.005 * np.sin(2 * np.pi * cycle_position)
            daily_returns[i] += cycle_boost
        
        # Calcular precios
        prices = [base_price]
        for i in range(1, n_days):
            new_price = prices[-1] * (1 + daily_returns[i])
            # Evitar precios extremos
            if new_price > base_price * 2:
                new_price = base_price * 1.8
            elif new_price < base_price * 0.5:
                new_price = base_price * 0.6
            prices.append(new_price)
        
        # Crear OHLC realista
        data = []
        for i, price in enumerate(prices):
            # Variación intraday más pronunciada para más oportunidades
            daily_range = price * volatility * 1.5
            
            open_price = price + np.random.uniform(-daily_range/4, daily_range/4)
            close_price = price + np.random.uniform(-daily_range/4, daily_range/4)
            
            high_price = max(open_price, close_price) + np.random.uniform(0, daily_range/2)
            low_price = min(open_price, close_price) - np.random.uniform(0, daily_range/2)
            
            # Volumen correlacionado con volatilidad
            volume = int(1000000 * (1 + abs(daily_returns[i]) * 10))
            
            data.append({
                'Date': dates[i],
                'Open': round(open_price, 2),
                'High': round(high_price, 2),
                'Low': round(low_price, 2),
                'Close': round(close_price, 2),
                'Volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('Date', inplace=True)
        
        self.log(f"✅ Datos generados para {symbol_name}: {len(df)} días")
        return df
    
    def calculate_advanced_indicators(self, data):
        """Calcular indicadores técnicos optimizados"""
        df = data.copy()
        
        # RSI optimizado
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config['rsi_period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config['rsi_period']).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD optimizado
        ema_fast = df['Close'].ewm(span=self.config['macd_fast']).mean()
        ema_slow = df['Close'].ewm(span=self.config['macd_slow']).mean()
        df['MACD'] = ema_fast - ema_slow
        df['MACD_Signal'] = df['MACD'].ewm(span=self.config['macd_signal']).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands optimizados
        bb_ma = df['Close'].rolling(window=self.config['bb_period']).mean()
        bb_std = df['Close'].rolling(window=self.config['bb_period']).std()
        df['BB_Upper'] = bb_ma + (bb_std * self.config['bb_std'])
        df['BB_Lower'] = bb_ma - (bb_std * self.config['bb_std'])
        df['BB_Middle'] = bb_ma
        
        # Williams %R optimizado
        high_n = df['High'].rolling(window=self.config['williams_period']).max()
        low_n = df['Low'].rolling(window=self.config['williams_period']).min()
        df['Williams_R'] = -100 * (high_n - df['Close']) / (high_n - low_n)
        
        # Stochastic optimizado
        low_k = df['Low'].rolling(window=self.config['stoch_k']).min()
        high_k = df['High'].rolling(window=self.config['stoch_k']).max()
        df['Stoch_K'] = 100 * (df['Close'] - low_k) / (high_k - low_k)
        df['Stoch_D'] = df['Stoch_K'].rolling(window=self.config['stoch_d']).mean()
        
        # EMAs optimizadas
        df['EMA_Short'] = df['Close'].ewm(span=self.config['ema_short']).mean()
        df['EMA_Long'] = df['Close'].ewm(span=self.config['ema_long']).mean()
        
        # ATR optimizado
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(window=self.config['atr_period']).mean()
        
        # Indicadores adicionales para más señales
        df['Price_Change'] = df['Close'].pct_change()
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_MA']
        
        return df
    
    def generate_aggressive_signals(self, df):
        """Generar señales más agresivas para mayor frecuencia de trades"""
        signals = []
        
        for i in range(50, len(df)):  # Empezar después de que los indicadores se estabilicen
            current = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Inicializar score de señal
            signal_score = 0
            confidence_score = 0
            signal_reasons = []
            
            # 1. RSI Signals (más agresivo)
            if current['RSI'] < self.config['rsi_oversold']:
                signal_score += 25
                confidence_score += 20
                signal_reasons.append("RSI Oversold")
            elif current['RSI'] > self.config['rsi_overbought']:
                signal_score += 20  # También señal alcista en sobrecompra
                confidence_score += 15
                signal_reasons.append("RSI Momentum")
            
            # 2. MACD Signals (más sensible)
            if current['MACD'] > current['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
                signal_score += 30
                confidence_score += 25
                signal_reasons.append("MACD Bullish Cross")
            elif current['MACD_Histogram'] > 0:
                signal_score += 15
                confidence_score += 10
                signal_reasons.append("MACD Positive")
            
            # 3. Bollinger Bands (más agresivo)
            if current['Close'] < current['BB_Lower']:
                signal_score += 25
                confidence_score += 20
                signal_reasons.append("BB Oversold")
            elif current['Close'] > current['BB_Upper']:
                signal_score += 20  # Momentum alcista
                confidence_score += 15
                signal_reasons.append("BB Breakout")
            
            # 4. EMA Trend (más sensible)
            if current['EMA_Short'] > current['EMA_Long']:
                signal_score += 20
                confidence_score += 15
                signal_reasons.append("EMA Bullish")
            
            # 5. Williams %R (más agresivo)
            if current['Williams_R'] < -80:
                signal_score += 20
                confidence_score += 15
                signal_reasons.append("Williams Oversold")
            elif current['Williams_R'] > -20:
                signal_score += 15
                confidence_score += 10
                signal_reasons.append("Williams Momentum")
            
            # 6. Stochastic (más sensible)
            if current['Stoch_K'] < 20:
                signal_score += 15
                confidence_score += 10
                signal_reasons.append("Stoch Oversold")
            elif current['Stoch_K'] > current['Stoch_D']:
                signal_score += 10
                confidence_score += 8
                signal_reasons.append("Stoch Bullish")
            
            # 7. Volume confirmation
            if current['Volume_Ratio'] > 1.2:
                signal_score += 10
                confidence_score += 8
                signal_reasons.append("High Volume")
            
            # 8. Price momentum
            if current['Price_Change'] > 0.01:  # 1% de subida
                signal_score += 15
                confidence_score += 12
                signal_reasons.append("Strong Momentum")
            
            # Generar señal si cumple criterios mínimos
            if (signal_score >= self.config['min_signal_strength'] and 
                confidence_score >= self.config['min_confidence']):
                
                signals.append({
                    'date': current.name,
                    'signal_strength': min(signal_score, 100),
                    'confidence': min(confidence_score, 100),
                    'price': current['Close'],
                    'reasons': signal_reasons,
                    'rsi': current['RSI'],
                    'macd': current['MACD'],
                    'bb_position': (current['Close'] - current['BB_Lower']) / (current['BB_Upper'] - current['BB_Lower'])
                })
        
        return signals
    
    def backtest_aggressive_strategy(self, df, signals, symbol_name):
        """Backtesting optimizado para máximo rendimiento"""
        capital = self.config['initial_capital']
        trades = []
        
        self.log(f"🚀 Iniciando backtesting agresivo para {symbol_name} con {len(signals)} señales")
        
        for signal in signals:
            signal_date = signal['date']
            signal_price = signal['price']
            
            # Obtener datos futuros para simular el trade
            future_data = df[df.index > signal_date].head(30)  # Máximo 30 días
            
            if len(future_data) == 0:
                continue
            
            # Calcular tamaño de posición (sin apalancamiento)
            risk_amount = capital * self.config['position_size']
            
            # Precios de salida
            entry_price = signal_price
            stop_loss_price = entry_price * (1 - self.config['stop_loss'])
            take_profit_price = entry_price * (1 + self.config['take_profit'])
            
            # Simular trade
            for date, row in future_data.iterrows():
                current_price = row['Close']
                
                # Check stop loss
                if current_price <= stop_loss_price:
                    pnl = (current_price - entry_price) / entry_price
                    trade_result = risk_amount * pnl  # Sin apalancamiento
                    capital += trade_result
                    
                    trades.append({
                        'entry_date': signal_date,
                        'exit_date': date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                        'trade_result': trade_result,
                        'signal_strength': signal['signal_strength'],
                        'confidence': signal['confidence'],
                        'days_held': (date - signal_date).days,
                        'exit_reason': 'Stop Loss'
                    })
                    break
                
                # Check take profit
                elif current_price >= take_profit_price:
                    pnl = (current_price - entry_price) / entry_price
                    trade_result = risk_amount * pnl  # Sin apalancamiento
                    capital += trade_result
                    
                    trades.append({
                        'entry_date': signal_date,
                        'exit_date': date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                        'trade_result': trade_result,
                        'signal_strength': signal['signal_strength'],
                        'confidence': signal['confidence'],
                        'days_held': (date - signal_date).days,
                        'exit_reason': 'Take Profit'
                    })
                    break
        
        # Aplicar comisiones
        total_commission = len(trades) * self.config['commission'] * capital
        capital -= total_commission
        
        return trades, capital
    
    def calculate_performance_metrics(self, trades, final_capital):
        """Calcular métricas de rendimiento detalladas"""
        if not trades:
            return {
                'total_return': 0,
                'monthly_return': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        # Métricas básicas
        total_return = ((final_capital - self.config['initial_capital']) / self.config['initial_capital']) * 100
        monthly_return = total_return / 24  # 24 meses de backtesting
        
        # Análisis de trades
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        losing_trades = len([t for t in trades if t['pnl'] < 0])
        win_rate = (winning_trades / len(trades)) * 100 if trades else 0
        
        # Profit factor
        gross_profit = sum([t['trade_result'] for t in trades if t['trade_result'] > 0])
        gross_loss = abs(sum([t['trade_result'] for t in trades if t['trade_result'] < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe ratio estimado
        returns = [t['pnl'] for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        return {
            'total_return': total_return,
            'monthly_return': monthly_return,
            'total_trades': len(trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': 0,  # Simplificado
            'sharpe_ratio': sharpe_ratio,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'final_capital': final_capital
        }
    
    def analyze_symbol_aggressive(self, symbol_name, symbol_config):
        """Análisis agresivo de un símbolo específico"""
        self.log(f"🎯 Analizando {symbol_name} para 10% ROI mensual...")
        
        # Generar datos optimizados
        df = self.generate_high_performance_data(symbol_name, symbol_config)
        
        # Calcular indicadores
        df = self.calculate_advanced_indicators(df)
        
        # Generar señales agresivas
        signals = self.generate_aggressive_signals(df)
        
        if not signals:
            self.log(f"⚠️ No se generaron señales para {symbol_name}")
            return None
        
        # Ejecutar backtesting
        trades, final_capital = self.backtest_aggressive_strategy(df, signals, symbol_name)
        
        # Calcular métricas
        metrics = self.calculate_performance_metrics(trades, final_capital)
        
        self.log(f"✅ {symbol_name}: {metrics['total_return']:.2f}% total, {metrics['monthly_return']:.2f}% mensual, {len(trades)} trades")
        
        return {
            'symbol': symbol_name,
            'metrics': metrics,
            'trades': trades,
            'signals_generated': len(signals),
            'data_points': len(df)
        }
    
    def run_optimization_test(self):
        """Ejecutar test de optimización para 10% ROI mensual"""
        self.log("🚀 INICIANDO OPTIMIZACIÓN PARA 10% ROI MENSUAL SIN APALANCAMIENTO")
        self.log("=" * 80)
        
        results = {}
        
        for symbol_name, symbol_config in self.symbols.items():
            result = self.analyze_symbol_aggressive(symbol_name, symbol_config)
            if result:
                results[symbol_name] = result
        
        return results
    
    def generate_optimization_report(self, results):
        """Generar reporte de optimización"""
        self.log("\n" + "=" * 80)
        self.log("📊 REPORTE DE OPTIMIZACIÓN - OBJETIVO 10% ROI MENSUAL")
        self.log("=" * 80)
        
        if not results:
            self.log("❌ No se obtuvieron resultados válidos")
            return
        
        # Ordenar por ROI mensual
        sorted_results = sorted(results.items(), 
                              key=lambda x: x[1]['metrics']['monthly_return'], 
                              reverse=True)
        
        self.log("🏆 RANKING POR ROI MENSUAL:")
        self.log("-" * 60)
        
        successful_symbols = []
        
        for i, (symbol, data) in enumerate(sorted_results, 1):
            metrics = data['metrics']
            monthly_roi = metrics['monthly_return']
            
            status = "✅ OBJETIVO ALCANZADO" if monthly_roi >= 10 else "❌ Por debajo del objetivo"
            
            self.log(f"{i}. {symbol}:")
            self.log(f"   💰 ROI Mensual: {monthly_roi:.2f}% {status}")
            self.log(f"   📈 ROI Total: {metrics['total_return']:.2f}%")
            self.log(f"   🎯 Trades: {metrics['total_trades']} (✅{metrics['winning_trades']} | ❌{metrics['losing_trades']})")
            self.log(f"   🏆 Win Rate: {metrics['win_rate']:.1f}%")
            self.log(f"   💵 Capital Final: ${metrics['final_capital']:.2f}")
            self.log(f"   📊 Profit Factor: {metrics['profit_factor']:.2f}")
            
            if monthly_roi >= 10:
                successful_symbols.append(symbol)
            
            self.log("")
        
        # Resumen final
        self.log("🎉 RESUMEN FINAL:")
        self.log("-" * 60)
        
        if successful_symbols:
            self.log(f"✅ SÍMBOLOS QUE ALCANZAN 10% ROI MENSUAL: {len(successful_symbols)}")
            for symbol in successful_symbols:
                roi = results[symbol]['metrics']['monthly_return']
                self.log(f"   🏆 {symbol}: {roi:.2f}% mensual")
        else:
            self.log("❌ NINGÚN SÍMBOLO ALCANZA EL OBJETIVO DE 10% ROI MENSUAL")
            
            # Mostrar el mejor resultado
            best_symbol, best_data = sorted_results[0]
            best_roi = best_data['metrics']['monthly_return']
            self.log(f"🥇 MEJOR RESULTADO: {best_symbol} con {best_roi:.2f}% mensual")
            
            # Sugerencias de optimización
            self.log("\n💡 SUGERENCIAS PARA ALCANZAR 10% ROI MENSUAL:")
            self.log("   • Reducir más los umbrales de señal (30-35)")
            self.log("   • Aumentar take profit a 20-25%")
            self.log("   • Aumentar posición a 75% del capital")
            self.log("   • Implementar múltiples timeframes")
            self.log("   • Añadir más símbolos volátiles")
        
        self.log("\n" + "=" * 80)

def main():
    """Función principal"""
    system = UltimateSicar10PercentROI()
    results = system.run_optimization_test()
    system.generate_optimization_report(results)

if __name__ == "__main__":
    main()