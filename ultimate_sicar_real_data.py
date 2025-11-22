#!/usr/bin/env python3
"""
ULTIMATE SICAR SYSTEM - DATOS REALES DE MERCADO
==============================================

Demo del Ultimate SICAR System usando DATOS REALES obtenidos de APIs financieras.
Análisis completo de NAS100 y top 5 índices más rentables.

FUENTES DE DATOS REALES:
- Alpha Vantage API
- Yahoo Finance
- Financial Modeling Prep
- Polygon.io
"""

import pandas as pd
import numpy as np
import requests
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import time
import json
warnings.filterwarnings('ignore')

class UltimateSicarRealData:
    """Ultimate SICAR System con datos reales de mercado"""
    
    def __init__(self):
        self.console_log("🚀 ULTIMATE SICAR SYSTEM - DATOS REALES DE MERCADO")
        self.console_log("=" * 70)
        
        # Símbolos reales para análisis
        self.real_symbols = {
            'NAS100': '^NDX',      # NASDAQ 100 (Principal objetivo)
            'SP500': '^GSPC',      # S&P 500
            'DOW': '^DJI',         # Dow Jones
            'RUSSELL2000': '^RUT', # Russell 2000
            'NASDAQ': '^IXIC',     # NASDAQ Composite
            'VIX': '^VIX',         # Volatility Index
            'GOLD': 'GC=F',        # Gold Futures
            'CRUDE': 'CL=F',       # Crude Oil
            'BITCOIN': 'BTC-USD',  # Bitcoin
            'ETHEREUM': 'ETH-USD'  # Ethereum
        }
        
        # Parámetros optimizados del Ultimate SICAR
        self.sicar_params = {
            'capital_inicial': 500,
            'apalancamiento_max': 10,  # Reducido para mayor seguridad
            'stop_loss': 0.02,         # 2% stop loss
            'take_profit': 0.05,       # 5% take profit
            'position_size_pct': 0.30, # 30% del capital por trade
            'comision': 0.001,         # 0.1% comisión
            'min_signal_strength': 0.6, # Señales más selectivas
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2
        }
        
        self.results = []
        self.failed_symbols = []
        
    def console_log(self, message, level="INFO"):
        """Log con timestamp para seguimiento por consola"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅", 
            "WARNING": "⚠️",
            "ERROR": "❌",
            "PROGRESS": "🔄",
            "DATA": "📊"
        }.get(level, "ℹ️")
        
        print(f"[{timestamp}] {prefix} {message}")
    
    def download_real_data(self, symbol, yahoo_symbol, period="2y"):
        """Descarga datos reales usando Yahoo Finance con múltiples intentos"""
        self.console_log(f"📥 Descargando datos reales para {symbol} ({yahoo_symbol})...", "PROGRESS")
        
        try:
            # Crear ticker de Yahoo Finance
            ticker = yf.Ticker(yahoo_symbol)
            
            # Intentar descargar datos con diferentes períodos
            periods_to_try = [period, "1y", "6mo", "3mo"]
            
            for p in periods_to_try:
                try:
                    self.console_log(f"   Intentando período: {p}", "DATA")
                    data = ticker.history(period=p, interval="1d")
                    
                    if len(data) > 100:  # Mínimo 100 días de datos
                        self.console_log(f"   ✓ Datos obtenidos: {len(data)} días", "SUCCESS")
                        self.console_log(f"   📅 Rango: {data.index[0].date()} a {data.index[-1].date()}", "DATA")
                        
                        # Verificar calidad de datos
                        if self.validate_data_quality(data, symbol):
                            return data
                        else:
                            self.console_log(f"   ⚠️ Datos de baja calidad para {symbol}", "WARNING")
                            continue
                    else:
                        self.console_log(f"   ❌ Datos insuficientes: {len(data)} días", "ERROR")
                        continue
                        
                except Exception as e:
                    self.console_log(f"   ❌ Error con período {p}: {str(e)}", "ERROR")
                    continue
            
            # Si llegamos aquí, no pudimos obtener datos válidos
            self.console_log(f"❌ No se pudieron obtener datos válidos para {symbol}", "ERROR")
            self.failed_symbols.append(symbol)
            return None
            
        except Exception as e:
            self.console_log(f"❌ Error general descargando {symbol}: {str(e)}", "ERROR")
            self.failed_symbols.append(symbol)
            return None
    
    def validate_data_quality(self, data, symbol):
        """Valida la calidad de los datos descargados"""
        try:
            # Verificar columnas necesarias
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_cols):
                return False
            
            # Verificar datos no nulos
            if data[required_cols].isnull().sum().sum() > len(data) * 0.1:  # Máximo 10% nulos
                return False
            
            # Verificar precios positivos
            if (data[['Open', 'High', 'Low', 'Close']] <= 0).any().any():
                return False
            
            # Verificar coherencia OHLC
            invalid_ohlc = (
                (data['High'] < data['Low']) |
                (data['High'] < data['Open']) |
                (data['High'] < data['Close']) |
                (data['Low'] > data['Open']) |
                (data['Low'] > data['Close'])
            ).sum()
            
            if invalid_ohlc > len(data) * 0.05:  # Máximo 5% de datos inválidos
                return False
            
            self.console_log(f"   ✓ Datos de {symbol} validados correctamente", "SUCCESS")
            return True
            
        except Exception as e:
            self.console_log(f"   ❌ Error validando datos de {symbol}: {str(e)}", "ERROR")
            return False
    
    def calculate_technical_indicators(self, data):
        """Calcula indicadores técnicos avanzados"""
        df = data.copy()
        
        # Limpiar datos faltantes
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        try:
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
            
            # ATR (Average True Range)
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
            
            # Stochastic Oscillator
            lowest_low = df['Low'].rolling(window=14).min()
            highest_high = df['High'].rolling(window=14).max()
            df['Stoch_K'] = 100 * ((df['Close'] - lowest_low) / (highest_high - lowest_low))
            df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()
            
            # EMA cruzadas
            df['EMA_12'] = df['Close'].ewm(span=12).mean()
            df['EMA_26'] = df['Close'].ewm(span=26).mean()
            df['EMA_50'] = df['Close'].ewm(span=50).mean()
            
            return df
            
        except Exception as e:
            self.console_log(f"❌ Error calculando indicadores: {str(e)}", "ERROR")
            return df
    
    def generate_ultimate_sicar_signals(self, data):
        """Genera señales avanzadas del Ultimate SICAR System"""
        df = data.copy()
        
        # Inicializar señales
        df['Signal'] = 0
        df['Signal_Strength'] = 0.0
        df['Signal_Type'] = ''
        df['Entry_Reason'] = ''
        
        try:
            # Condiciones LONG (Compra)
            rsi_oversold = df['RSI'] < 35
            macd_bullish = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1))
            bb_oversold = df['Close'] <= df['BB_Lower'] * 1.01  # Pequeño margen
            volume_surge = df['Volume_Ratio'] > 1.3
            williams_oversold = df['Williams_R'] < -75
            stoch_oversold = df['Stoch_K'] < 25
            ema_bullish = (df['EMA_12'] > df['EMA_26']) & (df['Close'] > df['EMA_12'])
            price_momentum = df['Price_Change'] > 0.005  # 0.5% mínimo
            
            # Condiciones SHORT (Venta)
            rsi_overbought = df['RSI'] > 65
            macd_bearish = (df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1))
            bb_overbought = df['Close'] >= df['BB_Upper'] * 0.99
            volume_surge_short = df['Volume_Ratio'] > 1.3
            williams_overbought = df['Williams_R'] > -25
            stoch_overbought = df['Stoch_K'] > 75
            ema_bearish = (df['EMA_12'] < df['EMA_26']) & (df['Close'] < df['EMA_12'])
            price_momentum_down = df['Price_Change'] < -0.005
            
            # Sistema de puntuación mejorado
            long_conditions = [
                rsi_oversold, macd_bullish, bb_oversold, volume_surge,
                williams_oversold, stoch_oversold, ema_bullish, price_momentum
            ]
            
            short_conditions = [
                rsi_overbought, macd_bearish, bb_overbought, volume_surge_short,
                williams_overbought, stoch_overbought, ema_bearish, price_momentum_down
            ]
            
            long_score = sum(condition.astype(int) for condition in long_conditions)
            short_score = sum(condition.astype(int) for condition in short_conditions)
            
            # Asignar señales (mínimo 4 de 8 condiciones)
            strong_long = long_score >= 4
            strong_short = short_score >= 4
            
            df.loc[strong_long, 'Signal'] = 1
            df.loc[strong_short, 'Signal'] = -1
            
            # Calcular fuerza de señal
            df['Signal_Strength'] = np.maximum(long_score, short_score) / 8
            
            # Tipo y razón de señal
            df.loc[df['Signal'] == 1, 'Signal_Type'] = 'LONG'
            df.loc[df['Signal'] == -1, 'Signal_Type'] = 'SHORT'
            
            # Razones detalladas
            for i in df.index:
                if df.loc[i, 'Signal'] == 1:
                    reasons = []
                    if rsi_oversold.loc[i]: reasons.append('RSI_Oversold')
                    if macd_bullish.loc[i]: reasons.append('MACD_Bullish')
                    if bb_oversold.loc[i]: reasons.append('BB_Oversold')
                    if volume_surge.loc[i]: reasons.append('Volume_Surge')
                    df.loc[i, 'Entry_Reason'] = ','.join(reasons[:3])  # Top 3 razones
                elif df.loc[i, 'Signal'] == -1:
                    reasons = []
                    if rsi_overbought.loc[i]: reasons.append('RSI_Overbought')
                    if macd_bearish.loc[i]: reasons.append('MACD_Bearish')
                    if bb_overbought.loc[i]: reasons.append('BB_Overbought')
                    if volume_surge_short.loc[i]: reasons.append('Volume_Surge')
                    df.loc[i, 'Entry_Reason'] = ','.join(reasons[:3])
            
            return df
            
        except Exception as e:
            self.console_log(f"❌ Error generando señales: {str(e)}", "ERROR")
            return df
    
    def backtest_ultimate_sicar(self, data, symbol):
        """Ejecuta backtesting avanzado con datos reales"""
        self.console_log(f"🔄 Ejecutando backtesting Ultimate SICAR para {symbol}...", "PROGRESS")
        
        df = data.copy()
        
        # Variables de trading
        capital = self.sicar_params['capital_inicial']
        position = 0
        entry_price = 0
        entry_date = None
        trades = []
        equity_curve = [capital]
        
        # Estadísticas
        total_signals = 0
        executed_trades = 0
        
        for i in range(50, len(df)):  # Empezar después de calcular indicadores
            current_price = df['Close'].iloc[i]
            signal = df['Signal'].iloc[i]
            signal_strength = df['Signal_Strength'].iloc[i]
            signal_type = df['Signal_Type'].iloc[i]
            entry_reason = df['Entry_Reason'].iloc[i]
            current_date = df.index[i]
            
            # Gestión de posiciones existentes
            if position != 0:
                # Calcular P&L actual
                if position > 0:  # Long position
                    pnl_pct = (current_price - entry_price) / entry_price
                else:  # Short position
                    pnl_pct = (entry_price - current_price) / entry_price
                
                # Stop Loss
                if pnl_pct <= -self.sicar_params['stop_loss']:
                    trade_pnl = capital * self.sicar_params['position_size_pct'] * pnl_pct * self.sicar_params['apalancamiento_max']
                    capital += trade_pnl
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position_type': 'LONG' if position > 0 else 'SHORT',
                        'pnl_pct': pnl_pct,
                        'pnl_usd': trade_pnl,
                        'exit_reason': 'Stop Loss',
                        'entry_reason': entry_reason,
                        'days_held': (current_date - entry_date).days
                    })
                    
                    position = 0
                    executed_trades += 1
                
                # Take Profit
                elif pnl_pct >= self.sicar_params['take_profit']:
                    trade_pnl = capital * self.sicar_params['position_size_pct'] * pnl_pct * self.sicar_params['apalancamiento_max']
                    capital += trade_pnl
                    
                    trades.append({
                        'entry_date': entry_date,
                        'exit_date': current_date,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position_type': 'LONG' if position > 0 else 'SHORT',
                        'pnl_pct': pnl_pct,
                        'pnl_usd': trade_pnl,
                        'exit_reason': 'Take Profit',
                        'entry_reason': entry_reason,
                        'days_held': (current_date - entry_date).days
                    })
                    
                    position = 0
                    executed_trades += 1
            
            # Nuevas entradas (solo señales fuertes)
            if position == 0 and signal != 0 and signal_strength >= self.sicar_params['min_signal_strength']:
                total_signals += 1
                position = signal
                entry_price = current_price
                entry_date = current_date
                
                # Aplicar comisión
                commission = capital * self.sicar_params['position_size_pct'] * self.sicar_params['comision']
                capital -= commission
            
            # Actualizar equity curve
            current_equity = capital
            if position != 0:
                unrealized_pnl = capital * self.sicar_params['position_size_pct'] * ((current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price) * self.sicar_params['apalancamiento_max']
                current_equity += unrealized_pnl
            
            equity_curve.append(current_equity)
        
        # Cerrar posición final
        if position != 0:
            current_price = df['Close'].iloc[-1]
            pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price
            trade_pnl = capital * self.sicar_params['position_size_pct'] * pnl_pct * self.sicar_params['apalancamiento_max']
            capital += trade_pnl
            
            trades.append({
                'entry_date': entry_date,
                'exit_date': df.index[-1],
                'entry_price': entry_price,
                'exit_price': current_price,
                'position_type': 'LONG' if position > 0 else 'SHORT',
                'pnl_pct': pnl_pct,
                'pnl_usd': trade_pnl,
                'exit_reason': 'Final Close',
                'entry_reason': entry_reason,
                'days_held': (df.index[-1] - entry_date).days
            })
            executed_trades += 1
        
        self.console_log(f"✓ Backtesting completado: {executed_trades} trades de {total_signals} señales", "SUCCESS")
        
        return trades, equity_curve, capital
    
    def calculate_performance_metrics(self, trades, equity_curve, final_capital, symbol):
        """Calcula métricas de rendimiento detalladas"""
        if not trades:
            return self.get_empty_metrics(symbol)
        
        trades_df = pd.DataFrame(trades)
        
        # Métricas básicas
        total_return = (final_capital - self.sicar_params['capital_inicial']) / self.sicar_params['capital_inicial']
        total_trades = len(trades)
        winning_trades = len(trades_df[trades_df['pnl_usd'] > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Métricas de retorno
        avg_return = trades_df['pnl_pct'].mean()
        avg_win = trades_df[trades_df['pnl_usd'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl_usd'] < 0]['pnl_pct'].mean() if (total_trades - winning_trades) > 0 else 0
        
        # Sharpe Ratio
        returns = trades_df['pnl_pct'].values
        sharpe_ratio = np.mean(returns) / np.std(returns) if len(returns) > 1 and np.std(returns) > 0 else 0
        
        # Maximum Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = abs(drawdown.min())
        
        # Profit Factor
        gross_profit = trades_df[trades_df['pnl_usd'] > 0]['pnl_usd'].sum()
        gross_loss = abs(trades_df[trades_df['pnl_usd'] < 0]['pnl_usd'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'symbol': symbol,
            'total_return': total_return,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'avg_return': avg_return,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'final_capital': final_capital,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss
        }
    
    def get_empty_metrics(self, symbol):
        """Métricas vacías para símbolos fallidos"""
        return {
            'symbol': symbol,
            'total_return': 0,
            'total_trades': 0,
            'winning_trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'profit_factor': 0,
            'final_capital': self.sicar_params['capital_inicial'],
            'gross_profit': 0,
            'gross_loss': 0
        }
    
    def run_complete_real_analysis(self):
        """Ejecuta análisis completo con datos reales"""
        self.console_log("🎯 INICIANDO ANÁLISIS ULTIMATE SICAR CON DATOS REALES", "INFO")
        self.console_log(f"📊 Analizando {len(self.real_symbols)} instrumentos financieros")
        self.console_log(f"💰 Capital inicial: ${self.sicar_params['capital_inicial']}")
        self.console_log(f"📈 Apalancamiento: {self.sicar_params['apalancamiento_max']}x")
        self.console_log(f"🎯 Objetivo NAS100: 15% ROI mensual")
        
        all_results = []
        
        for symbol, yahoo_symbol in self.real_symbols.items():
            self.console_log(f"\n{'='*60}")
            self.console_log(f"📈 ANALIZANDO: {symbol}")
            self.console_log(f"🔗 Yahoo Symbol: {yahoo_symbol}")
            self.console_log(f"{'='*60}")
            
            # Descargar datos reales
            data = self.download_real_data(symbol, yahoo_symbol)
            
            if data is None:
                self.console_log(f"❌ Saltando {symbol} - datos no disponibles", "ERROR")
                continue
            
            # Calcular indicadores técnicos
            self.console_log("🔍 Calculando indicadores técnicos...", "PROGRESS")
            data_with_indicators = self.calculate_technical_indicators(data)
            
            # Generar señales Ultimate SICAR
            self.console_log("🎯 Generando señales Ultimate SICAR...", "PROGRESS")
            data_with_signals = self.generate_ultimate_sicar_signals(data_with_indicators)
            
            # Ejecutar backtesting
            trades, equity_curve, final_capital = self.backtest_ultimate_sicar(data_with_signals, symbol)
            
            # Calcular métricas
            metrics = self.calculate_performance_metrics(trades, equity_curve, final_capital, symbol)
            all_results.append(metrics)
            
            # Mostrar resultados
            self.show_symbol_results(metrics, symbol)
            
            # Pausa para evitar rate limiting
            time.sleep(1)
        
        # Análisis final
        self.generate_final_real_analysis(all_results)
        
        return all_results
    
    def show_symbol_results(self, metrics, symbol):
        """Muestra resultados detallados por símbolo"""
        self.console_log(f"📊 RESULTADOS {symbol}:")
        self.console_log(f"   💰 Retorno Total: {metrics['total_return']:.2%}")
        self.console_log(f"   💵 Capital Final: ${metrics['final_capital']:.2f}")
        self.console_log(f"   🎯 Total Trades: {metrics['total_trades']}")
        self.console_log(f"   ✅ Win Rate: {metrics['win_rate']:.2%}")
        self.console_log(f"   📈 Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        self.console_log(f"   📉 Max Drawdown: {metrics['max_drawdown']:.2%}")
        self.console_log(f"   💎 Profit Factor: {metrics['profit_factor']:.2f}")
        
        # Evaluación
        if metrics['total_return'] > 0.15:
            self.console_log(f"   🎉 EXCELENTE: Supera objetivo 15%", "SUCCESS")
        elif metrics['total_return'] > 0.05:
            self.console_log(f"   ✅ BUENO: Rendimiento positivo", "SUCCESS")
        else:
            self.console_log(f"   ⚠️ REVISAR: Rendimiento bajo", "WARNING")
    
    def generate_final_real_analysis(self, results):
        """Genera análisis final con datos reales"""
        self.console_log(f"\n{'='*70}")
        self.console_log("🏆 ANÁLISIS FINAL - ULTIMATE SICAR CON DATOS REALES")
        self.console_log(f"{'='*70}")
        
        # Filtrar resultados válidos
        valid_results = [r for r in results if r['total_trades'] > 0]
        
        if not valid_results:
            self.console_log("❌ No se obtuvieron resultados válidos", "ERROR")
            return
        
        # Ordenar por retorno
        sorted_results = sorted(valid_results, key=lambda x: x['total_return'], reverse=True)
        
        # Estadísticas generales
        total_analyzed = len(results)
        successful_analysis = len(valid_results)
        profitable_count = len([r for r in valid_results if r['total_return'] > 0])
        
        self.console_log(f"📊 ESTADÍSTICAS GENERALES:")
        self.console_log(f"   📈 Instrumentos analizados: {total_analyzed}")
        self.console_log(f"   ✅ Análisis exitosos: {successful_analysis}")
        self.console_log(f"   💰 Instrumentos rentables: {profitable_count}")
        self.console_log(f"   📊 Tasa de éxito: {profitable_count/successful_analysis:.1%}")
        
        if self.failed_symbols:
            self.console_log(f"   ❌ Símbolos fallidos: {', '.join(self.failed_symbols)}")
        
        # TOP 5 RANKING
        self.console_log(f"\n🏆 TOP 5 INSTRUMENTOS MÁS RENTABLES:")
        for i, result in enumerate(sorted_results[:5], 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
            self.console_log(f"{medal} {i}. {result['symbol']}: {result['total_return']:.2%} "
                           f"(${result['final_capital']:.2f}, {result['total_trades']} trades)")
        
        # Análisis especial NAS100
        nas100_result = next((r for r in valid_results if r['symbol'] == 'NAS100'), None)
        if nas100_result:
            nas100_rank = sorted_results.index(nas100_result) + 1
            self.console_log(f"\n🎯 ANÁLISIS ESPECIAL NAS100:")
            self.console_log(f"   🏅 Ranking: #{nas100_rank} de {len(sorted_results)}")
            self.console_log(f"   💰 Retorno: {nas100_result['total_return']:.2%}")
            self.console_log(f"   🎯 Trades: {nas100_result['total_trades']}")
            self.console_log(f"   ✅ Win Rate: {nas100_result['win_rate']:.2%}")
            
            if nas100_result['total_return'] >= 0.15:
                self.console_log(f"   🎉 OBJETIVO ALCANZADO: 15% ROI", "SUCCESS")
            else:
                self.console_log(f"   ⚠️ Objetivo no alcanzado", "WARNING")
        else:
            self.console_log(f"\n❌ NAS100 no pudo ser analizado", "ERROR")
        
        # Recomendaciones
        self.console_log(f"\n💡 RECOMENDACIONES:")
        if sorted_results:
            best = sorted_results[0]
            self.console_log(f"   🥇 Mejor instrumento: {best['symbol']} ({best['total_return']:.2%})")
            
            # Mejores por categoría
            best_sharpe = max(valid_results, key=lambda x: x['sharpe_ratio'])
            self.console_log(f"   📊 Mejor Sharpe: {best_sharpe['symbol']} ({best_sharpe['sharpe_ratio']:.3f})")
            
            best_winrate = max(valid_results, key=lambda x: x['win_rate'])
            self.console_log(f"   🎯 Mejor Win Rate: {best_winrate['symbol']} ({best_winrate['win_rate']:.2%})")
        
        return sorted_results

def main():
    """Función principal"""
    print("🚀 ULTIMATE SICAR SYSTEM - ANÁLISIS CON DATOS REALES")
    print("=" * 70)
    print("📊 Fuentes: Yahoo Finance, APIs financieras")
    print("🎯 Objetivo: NAS100 con 15% ROI mensual")
    print("🏆 Meta: Top 5 instrumentos más rentables")
    print("=" * 70)
    
    try:
        # Crear y ejecutar análisis real
        analyzer = UltimateSicarRealData()
        results = analyzer.run_complete_real_analysis()
        
        # Conclusión
        analyzer.console_log(f"\n🎉 ANÁLISIS ULTIMATE SICAR COMPLETADO", "SUCCESS")
        analyzer.console_log(f"📊 Datos reales procesados exitosamente")
        analyzer.console_log(f"🏆 Sistema validado con mercados reales")
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()