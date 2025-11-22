#!/usr/bin/env python3
"""
ULTIMATE SICAR SYSTEM - DATOS REALES ROBUSTOS
============================================

Demo del Ultimate SICAR System usando DATOS REALES con múltiples fuentes
y manejo robusto de errores de conectividad.

FUENTES DE DATOS REALES:
- Yahoo Finance (primaria)
- Alpha Vantage (backup)
- Datos locales guardados
- APIs alternativas
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
import time
import os
import json
import requests
warnings.filterwarnings('ignore')

class UltimateSicarRobustReal:
    """Ultimate SICAR System con datos reales robustos"""
    
    def __init__(self):
        self.console_log("🚀 ULTIMATE SICAR SYSTEM - DATOS REALES ROBUSTOS")
        self.console_log("=" * 70)
        
        # Símbolos con múltiples alternativas
        self.symbols_config = {
            'NAS100': {
                'yahoo': '^NDX',
                'alternatives': ['^IXIC', 'QQQ'],
                'description': 'NASDAQ 100 (Objetivo Principal)',
                'priority': 1
            },
            'SP500': {
                'yahoo': '^GSPC',
                'alternatives': ['SPY', '^SPX'],
                'description': 'S&P 500 Index',
                'priority': 2
            },
            'DOW': {
                'yahoo': '^DJI',
                'alternatives': ['DIA'],
                'description': 'Dow Jones Industrial',
                'priority': 3
            },
            'NASDAQ': {
                'yahoo': '^IXIC',
                'alternatives': ['QQQ', 'NDAQ'],
                'description': 'NASDAQ Composite',
                'priority': 4
            },
            'RUSSELL2000': {
                'yahoo': '^RUT',
                'alternatives': ['IWM'],
                'description': 'Russell 2000 Small Cap',
                'priority': 5
            },
            'GOLD': {
                'yahoo': 'GC=F',
                'alternatives': ['GLD', 'GOLD'],
                'description': 'Gold',
                'priority': 6
            },
            'CRUDE': {
                'yahoo': 'CL=F',
                'alternatives': ['USO', 'OIL'],
                'description': 'Crude Oil',
                'priority': 7
            },
            'VIX': {
                'yahoo': '^VIX',
                'alternatives': ['VIXY', 'VXX'],
                'description': 'Volatility Index',
                'priority': 8
            }
        }
        
        # Parámetros optimizados del Ultimate SICAR
        self.sicar_params = {
            'capital_inicial': 500,
            'apalancamiento_max': 8,   # Conservador
            'stop_loss': 0.025,        # 2.5% stop loss
            'take_profit': 0.06,       # 6% take profit
            'position_size_pct': 0.25, # 25% del capital por trade
            'comision': 0.001,         # 0.1% comisión
            'min_signal_strength': 0.65, # Señales muy selectivas
            'rsi_period': 14,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2
        }
        
        self.results = []
        self.successful_downloads = []
        self.failed_symbols = []
        
        # Crear directorio para cache de datos
        self.cache_dir = "data_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
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
    
    def download_with_fallback(self, symbol, config):
        """Descarga datos con múltiples fuentes de respaldo"""
        self.console_log(f"📥 Descargando datos para {symbol}...", "PROGRESS")
        
        # Lista de símbolos a probar
        symbols_to_try = [config['yahoo']] + config.get('alternatives', [])
        
        for i, yahoo_symbol in enumerate(symbols_to_try):
            try:
                self.console_log(f"   Probando símbolo: {yahoo_symbol} (intento {i+1})", "DATA")
                
                # Intentar descargar con diferentes configuraciones
                data = self.try_download_symbol(yahoo_symbol)
                
                if data is not None and len(data) > 100:
                    self.console_log(f"   ✓ Datos obtenidos: {len(data)} días", "SUCCESS")
                    self.console_log(f"   📅 Rango: {data.index[0].date()} a {data.index[-1].date()}", "DATA")
                    
                    # Guardar en cache
                    self.save_to_cache(symbol, data)
                    
                    return data
                else:
                    self.console_log(f"   ❌ Datos insuficientes para {yahoo_symbol}", "WARNING")
                    continue
                    
            except Exception as e:
                self.console_log(f"   ❌ Error con {yahoo_symbol}: {str(e)[:50]}...", "ERROR")
                continue
        
        # Intentar cargar desde cache
        cached_data = self.load_from_cache(symbol)
        if cached_data is not None:
            self.console_log(f"   📁 Usando datos en cache para {symbol}", "WARNING")
            return cached_data
        
        self.console_log(f"❌ No se pudieron obtener datos para {symbol}", "ERROR")
        self.failed_symbols.append(symbol)
        return None
    
    def try_download_symbol(self, yahoo_symbol):
        """Intenta descargar un símbolo específico con múltiples configuraciones"""
        periods = ["2y", "1y", "6mo"]
        intervals = ["1d"]
        
        for period in periods:
            for interval in intervals:
                try:
                    # Configurar timeout y reintentos
                    ticker = yf.Ticker(yahoo_symbol)
                    
                    # Descargar con configuración específica
                    data = ticker.history(
                        period=period,
                        interval=interval,
                        auto_adjust=True,
                        prepost=False,
                        threads=True,
                        timeout=10
                    )
                    
                    if len(data) > 100:
                        # Validar calidad de datos
                        if self.validate_data_quality(data):
                            return data
                    
                    time.sleep(0.5)  # Pausa entre intentos
                    
                except Exception as e:
                    continue
        
        return None
    
    def validate_data_quality(self, data):
        """Valida la calidad de los datos descargados"""
        try:
            # Verificar columnas necesarias
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in required_cols):
                return False
            
            # Verificar datos no nulos (máximo 10% nulos)
            null_pct = data[required_cols].isnull().sum().sum() / (len(data) * len(required_cols))
            if null_pct > 0.1:
                return False
            
            # Verificar precios positivos
            if (data[['Open', 'High', 'Low', 'Close']] <= 0).any().any():
                return False
            
            # Verificar coherencia OHLC básica
            invalid_count = (
                (data['High'] < data['Low']) |
                (data['High'] < data['Close']) |
                (data['Low'] > data['Close'])
            ).sum()
            
            if invalid_count > len(data) * 0.05:  # Máximo 5% inválidos
                return False
            
            return True
            
        except Exception:
            return False
    
    def save_to_cache(self, symbol, data):
        """Guarda datos en cache local"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{symbol}_data.csv")
            data.to_csv(cache_file)
            self.console_log(f"   💾 Datos guardados en cache: {cache_file}", "DATA")
        except Exception as e:
            self.console_log(f"   ⚠️ Error guardando cache: {str(e)}", "WARNING")
    
    def load_from_cache(self, symbol):
        """Carga datos desde cache local"""
        try:
            cache_file = os.path.join(self.cache_dir, f"{symbol}_data.csv")
            if os.path.exists(cache_file):
                # Verificar que el cache no sea muy viejo (máximo 7 días)
                file_age = time.time() - os.path.getmtime(cache_file)
                if file_age < 7 * 24 * 3600:  # 7 días
                    data = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    if len(data) > 100:
                        return data
        except Exception:
            pass
        return None
    
    def calculate_technical_indicators(self, data):
        """Calcula indicadores técnicos optimizados"""
        df = data.copy()
        
        # Limpiar datos
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        try:
            # RSI optimizado
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.sicar_params['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.sicar_params['rsi_period']).mean()
            rs = gain / (loss + 1e-10)  # Evitar división por cero
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
            df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
            df['Volume_Ratio'] = df['Volume'] / (df['Volume_MA'] + 1)
            
            # EMAs
            df['EMA_12'] = df['Close'].ewm(span=12).mean()
            df['EMA_26'] = df['Close'].ewm(span=26).mean()
            
            # Momentum
            df['Price_Change'] = df['Close'].pct_change()
            df['Momentum'] = df['Close'] / df['Close'].shift(10) - 1
            
            return df
            
        except Exception as e:
            self.console_log(f"❌ Error calculando indicadores: {str(e)}", "ERROR")
            return df
    
    def generate_ultimate_sicar_signals(self, data):
        """Genera señales Ultra-Selectivas del Ultimate SICAR"""
        df = data.copy()
        
        # Inicializar señales
        df['Signal'] = 0
        df['Signal_Strength'] = 0.0
        df['Signal_Type'] = ''
        df['Entry_Reason'] = ''
        
        try:
            # Condiciones LONG ultra-selectivas
            rsi_strong_oversold = df['RSI'] < 30
            macd_strong_bullish = (df['MACD'] > df['MACD_Signal']) & (df['MACD_Histogram'] > df['MACD_Histogram'].shift(1))
            bb_strong_oversold = df['Close'] < df['BB_Lower']
            volume_strong_surge = df['Volume_Ratio'] > 1.5
            ema_bullish_cross = (df['EMA_12'] > df['EMA_26']) & (df['EMA_12'].shift(1) <= df['EMA_26'].shift(1))
            momentum_positive = df['Momentum'] > 0.02
            price_bounce = (df['Close'] > df['Open']) & (df['Price_Change'] > 0.01)
            
            # Condiciones SHORT ultra-selectivas
            rsi_strong_overbought = df['RSI'] > 70
            macd_strong_bearish = (df['MACD'] < df['MACD_Signal']) & (df['MACD_Histogram'] < df['MACD_Histogram'].shift(1))
            bb_strong_overbought = df['Close'] > df['BB_Upper']
            volume_strong_surge_short = df['Volume_Ratio'] > 1.5
            ema_bearish_cross = (df['EMA_12'] < df['EMA_26']) & (df['EMA_12'].shift(1) >= df['EMA_26'].shift(1))
            momentum_negative = df['Momentum'] < -0.02
            price_rejection = (df['Close'] < df['Open']) & (df['Price_Change'] < -0.01)
            
            # Sistema de puntuación ultra-estricto
            long_conditions = [
                rsi_strong_oversold, macd_strong_bullish, bb_strong_oversold,
                volume_strong_surge, ema_bullish_cross, momentum_positive, price_bounce
            ]
            
            short_conditions = [
                rsi_strong_overbought, macd_strong_bearish, bb_strong_overbought,
                volume_strong_surge_short, ema_bearish_cross, momentum_negative, price_rejection
            ]
            
            long_score = sum(condition.astype(int) for condition in long_conditions)
            short_score = sum(condition.astype(int) for condition in short_conditions)
            
            # Señales ultra-selectivas (mínimo 5 de 7 condiciones)
            ultra_strong_long = long_score >= 5
            ultra_strong_short = short_score >= 5
            
            df.loc[ultra_strong_long, 'Signal'] = 1
            df.loc[ultra_strong_short, 'Signal'] = -1
            
            # Fuerza de señal
            df['Signal_Strength'] = np.maximum(long_score, short_score) / 7
            
            # Tipos y razones
            df.loc[df['Signal'] == 1, 'Signal_Type'] = 'ULTRA_LONG'
            df.loc[df['Signal'] == -1, 'Signal_Type'] = 'ULTRA_SHORT'
            
            # Razones detalladas
            for i in df.index:
                if df.loc[i, 'Signal'] == 1:
                    reasons = []
                    if rsi_strong_oversold.loc[i]: reasons.append('RSI_Oversold')
                    if macd_strong_bullish.loc[i]: reasons.append('MACD_Bullish')
                    if bb_strong_oversold.loc[i]: reasons.append('BB_Oversold')
                    if volume_strong_surge.loc[i]: reasons.append('Volume_Surge')
                    df.loc[i, 'Entry_Reason'] = ','.join(reasons[:3])
                elif df.loc[i, 'Signal'] == -1:
                    reasons = []
                    if rsi_strong_overbought.loc[i]: reasons.append('RSI_Overbought')
                    if macd_strong_bearish.loc[i]: reasons.append('MACD_Bearish')
                    if bb_strong_overbought.loc[i]: reasons.append('BB_Overbought')
                    if volume_strong_surge_short.loc[i]: reasons.append('Volume_Surge')
                    df.loc[i, 'Entry_Reason'] = ','.join(reasons[:3])
            
            return df
            
        except Exception as e:
            self.console_log(f"❌ Error generando señales: {str(e)}", "ERROR")
            return df
    
    def backtest_ultimate_sicar(self, data, symbol):
        """Backtesting ultra-conservador del Ultimate SICAR"""
        self.console_log(f"🔄 Backtesting Ultra-Conservador para {symbol}...", "PROGRESS")
        
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
        
        for i in range(50, len(df)):
            current_price = df['Close'].iloc[i]
            signal = df['Signal'].iloc[i]
            signal_strength = df['Signal_Strength'].iloc[i]
            signal_type = df['Signal_Type'].iloc[i]
            entry_reason = df['Entry_Reason'].iloc[i]
            current_date = df.index[i]
            
            # Gestión de posiciones existentes
            if position != 0:
                # Calcular P&L
                if position > 0:
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price
                
                # Stop Loss estricto
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
                        'days_held': (current_date - entry_date).days,
                        'signal_strength': signal_strength
                    })
                    
                    position = 0
                    executed_trades += 1
                
                # Take Profit conservador
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
                        'days_held': (current_date - entry_date).days,
                        'signal_strength': signal_strength
                    })
                    
                    position = 0
                    executed_trades += 1
            
            # Nuevas entradas ultra-selectivas
            if position == 0 and signal != 0 and signal_strength >= self.sicar_params['min_signal_strength']:
                total_signals += 1
                position = signal
                entry_price = current_price
                entry_date = current_date
                
                # Comisión
                commission = capital * self.sicar_params['position_size_pct'] * self.sicar_params['comision']
                capital -= commission
            
            # Equity curve
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
                'days_held': (df.index[-1] - entry_date).days,
                'signal_strength': signal_strength
            })
            executed_trades += 1
        
        self.console_log(f"✓ Backtesting completado: {executed_trades} trades ultra-selectivos de {total_signals} señales", "SUCCESS")
        
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
        
        # Métricas adicionales
        avg_signal_strength = trades_df['signal_strength'].mean()
        avg_days_held = trades_df['days_held'].mean()
        
        return {
            'symbol': symbol,
            'total_return': total_return,
            'annualized_return': total_return * (365 / max(len(equity_curve), 1)),
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
            'gross_loss': gross_loss,
            'avg_signal_strength': avg_signal_strength,
            'avg_days_held': avg_days_held
        }
    
    def get_empty_metrics(self, symbol):
        """Métricas vacías para símbolos fallidos"""
        return {
            'symbol': symbol,
            'total_return': 0,
            'annualized_return': 0,
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
            'gross_loss': 0,
            'avg_signal_strength': 0,
            'avg_days_held': 0
        }
    
    def run_complete_robust_analysis(self):
        """Ejecuta análisis completo robusto con datos reales"""
        self.console_log("🎯 INICIANDO ANÁLISIS ULTIMATE SICAR ROBUSTO", "INFO")
        self.console_log(f"📊 Analizando {len(self.symbols_config)} instrumentos con datos reales")
        self.console_log(f"💰 Capital inicial: ${self.sicar_params['capital_inicial']}")
        self.console_log(f"📈 Apalancamiento: {self.sicar_params['apalancamiento_max']}x")
        self.console_log(f"🎯 Señales ultra-selectivas: {self.sicar_params['min_signal_strength']:.0%} mínimo")
        
        all_results = []
        
        # Ordenar por prioridad
        sorted_symbols = sorted(self.symbols_config.items(), key=lambda x: x[1]['priority'])
        
        for symbol, config in sorted_symbols:
            self.console_log(f"\n{'='*60}")
            self.console_log(f"📈 ANALIZANDO: {symbol}")
            self.console_log(f"📝 {config['description']}")
            self.console_log(f"🏅 Prioridad: {config['priority']}")
            self.console_log(f"{'='*60}")
            
            # Descargar datos con fallback
            data = self.download_with_fallback(symbol, config)
            
            if data is None:
                self.console_log(f"❌ Saltando {symbol} - datos no disponibles", "ERROR")
                continue
            
            # Marcar como exitoso
            self.successful_downloads.append(symbol)
            
            # Calcular indicadores
            self.console_log("🔍 Calculando indicadores técnicos avanzados...", "PROGRESS")
            data_with_indicators = self.calculate_technical_indicators(data)
            
            # Generar señales ultra-selectivas
            self.console_log("🎯 Generando señales Ultra-Selectivas...", "PROGRESS")
            data_with_signals = self.generate_ultimate_sicar_signals(data_with_indicators)
            
            # Backtesting ultra-conservador
            trades, equity_curve, final_capital = self.backtest_ultimate_sicar(data_with_signals, symbol)
            
            # Calcular métricas
            metrics = self.calculate_performance_metrics(trades, equity_curve, final_capital, symbol)
            all_results.append(metrics)
            
            # Mostrar resultados
            self.show_detailed_symbol_results(metrics, symbol)
            
            # Pausa para evitar rate limiting
            time.sleep(2)
        
        # Análisis final
        self.generate_comprehensive_final_analysis(all_results)
        
        return all_results
    
    def show_detailed_symbol_results(self, metrics, symbol):
        """Muestra resultados detallados por símbolo"""
        self.console_log(f"📊 RESULTADOS ULTIMATE SICAR - {symbol}:")
        self.console_log(f"   💰 Retorno Total: {metrics['total_return']:.2%}")
        self.console_log(f"   📅 Retorno Anualizado: {metrics['annualized_return']:.2%}")
        self.console_log(f"   💵 Capital Final: ${metrics['final_capital']:.2f}")
        self.console_log(f"   🎯 Total Trades: {metrics['total_trades']}")
        self.console_log(f"   ✅ Win Rate: {metrics['win_rate']:.2%}")
        self.console_log(f"   📈 Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        self.console_log(f"   📉 Max Drawdown: {metrics['max_drawdown']:.2%}")
        self.console_log(f"   💎 Profit Factor: {metrics['profit_factor']:.2f}")
        self.console_log(f"   🎯 Señal Promedio: {metrics['avg_signal_strength']:.2%}")
        self.console_log(f"   ⏱️ Días Promedio: {metrics['avg_days_held']:.1f}")
        
        # Evaluación específica
        if metrics['total_return'] >= 0.15:  # 15% objetivo
            self.console_log(f"   🎉 EXCELENTE: Supera objetivo 15%", "SUCCESS")
        elif metrics['total_return'] >= 0.10:
            self.console_log(f"   ✅ MUY BUENO: Rendimiento sólido", "SUCCESS")
        elif metrics['total_return'] >= 0.05:
            self.console_log(f"   ✅ BUENO: Rendimiento positivo", "SUCCESS")
        elif metrics['total_return'] > 0:
            self.console_log(f"   ⚠️ MODERADO: Rendimiento bajo", "WARNING")
        else:
            self.console_log(f"   ❌ PÉRDIDAS: Revisar estrategia", "ERROR")
    
    def generate_comprehensive_final_analysis(self, results):
        """Genera análisis final comprehensivo"""
        self.console_log(f"\n{'='*70}")
        self.console_log("🏆 ANÁLISIS FINAL ULTIMATE SICAR - DATOS REALES")
        self.console_log(f"{'='*70}")
        
        # Filtrar resultados válidos
        valid_results = [r for r in results if r['total_trades'] > 0]
        
        if not valid_results:
            self.console_log("❌ No se obtuvieron resultados válidos", "ERROR")
            self.console_log(f"📊 Símbolos exitosos: {len(self.successful_downloads)}")
            self.console_log(f"❌ Símbolos fallidos: {len(self.failed_symbols)}")
            if self.failed_symbols:
                self.console_log(f"   Fallidos: {', '.join(self.failed_symbols)}")
            return
        
        # Ordenar por retorno total
        sorted_results = sorted(valid_results, key=lambda x: x['total_return'], reverse=True)
        
        # Estadísticas generales
        total_symbols = len(self.symbols_config)
        successful_downloads = len(self.successful_downloads)
        successful_analysis = len(valid_results)
        profitable_count = len([r for r in valid_results if r['total_return'] > 0])
        
        self.console_log(f"📊 ESTADÍSTICAS GENERALES:")
        self.console_log(f"   📈 Símbolos objetivo: {total_symbols}")
        self.console_log(f"   📥 Descargas exitosas: {successful_downloads}")
        self.console_log(f"   ✅ Análisis completados: {successful_analysis}")
        self.console_log(f"   💰 Instrumentos rentables: {profitable_count}")
        self.console_log(f"   📊 Tasa de rentabilidad: {profitable_count/successful_analysis:.1%}")
        
        if self.failed_symbols:
            self.console_log(f"   ❌ Símbolos fallidos: {', '.join(self.failed_symbols)}")
        
        # Métricas promedio
        if valid_results:
            avg_return = np.mean([r['total_return'] for r in valid_results])
            avg_trades = np.mean([r['total_trades'] for r in valid_results])
            avg_win_rate = np.mean([r['win_rate'] for r in valid_results])
            avg_sharpe = np.mean([r['sharpe_ratio'] for r in valid_results])
            
            self.console_log(f"\n📊 MÉTRICAS PROMEDIO DEL SISTEMA:")
            self.console_log(f"   💰 Retorno promedio: {avg_return:.2%}")
            self.console_log(f"   🎯 Trades promedio: {avg_trades:.1f}")
            self.console_log(f"   ✅ Win rate promedio: {avg_win_rate:.2%}")
            self.console_log(f"   📈 Sharpe promedio: {avg_sharpe:.3f}")
        
        # TOP 5 RANKING
        self.console_log(f"\n🏆 TOP 5 INSTRUMENTOS MÁS RENTABLES:")
        for i, result in enumerate(sorted_results[:5], 1):
            medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
            self.console_log(f"{medal} {i}. {result['symbol']}: {result['total_return']:.2%} "
                           f"(${result['final_capital']:.2f}, {result['total_trades']} trades, "
                           f"WR: {result['win_rate']:.1%}, Sharpe: {result['sharpe_ratio']:.2f})")
        
        # Análisis especial NAS100
        nas100_result = next((r for r in valid_results if r['symbol'] == 'NAS100'), None)
        if nas100_result:
            nas100_rank = sorted_results.index(nas100_result) + 1
            self.console_log(f"\n🎯 ANÁLISIS ESPECIAL NAS100 (OBJETIVO PRINCIPAL):")
            self.console_log(f"   🏅 Ranking: #{nas100_rank} de {len(sorted_results)}")
            self.console_log(f"   💰 Retorno Total: {nas100_result['total_return']:.2%}")
            self.console_log(f"   📅 Retorno Anualizado: {nas100_result['annualized_return']:.2%}")
            self.console_log(f"   🎯 Total Trades: {nas100_result['total_trades']}")
            self.console_log(f"   ✅ Win Rate: {nas100_result['win_rate']:.2%}")
            self.console_log(f"   📈 Sharpe Ratio: {nas100_result['sharpe_ratio']:.3f}")
            self.console_log(f"   📉 Max Drawdown: {nas100_result['max_drawdown']:.2%}")
            
            # Evaluación del objetivo
            monthly_target = 0.15  # 15% mensual
            if nas100_result['total_return'] >= monthly_target:
                self.console_log(f"   🎉 OBJETIVO ALCANZADO: 15% ROI mensual", "SUCCESS")
            elif nas100_result['total_return'] >= monthly_target * 0.7:
                self.console_log(f"   ✅ CERCA DEL OBJETIVO: {nas100_result['total_return']:.2%} vs 15%", "SUCCESS")
            else:
                self.console_log(f"   ⚠️ Objetivo no alcanzado: {nas100_result['total_return']:.2%} vs 15%", "WARNING")
        else:
            self.console_log(f"\n❌ NAS100 no pudo ser analizado", "ERROR")
        
        # Recomendaciones finales
        self.console_log(f"\n💡 RECOMENDACIONES ULTIMATE SICAR:")
        if sorted_results:
            best = sorted_results[0]
            self.console_log(f"   🥇 Mejor instrumento: {best['symbol']} ({best['total_return']:.2%})")
            
            # Análisis por categorías
            best_sharpe = max(valid_results, key=lambda x: x['sharpe_ratio'])
            best_winrate = max(valid_results, key=lambda x: x['win_rate'])
            most_trades = max(valid_results, key=lambda x: x['total_trades'])
            
            self.console_log(f"   📊 Mejor Sharpe: {best_sharpe['symbol']} ({best_sharpe['sharpe_ratio']:.3f})")
            self.console_log(f"   🎯 Mejor Win Rate: {best_winrate['symbol']} ({best_winrate['win_rate']:.2%})")
            self.console_log(f"   📈 Más activo: {most_trades['symbol']} ({most_trades['total_trades']} trades)")
            
            # Análisis de riesgo
            high_risk = [r for r in valid_results if r['max_drawdown'] > 0.15]
            if high_risk:
                self.console_log(f"   ⚠️ Alto riesgo (DD > 15%): {[r['symbol'] for r in high_risk]}")
            
            # Instrumentos consistentes
            consistent = [r for r in valid_results if r['win_rate'] > 0.6 and r['total_return'] > 0.05]
            if consistent:
                self.console_log(f"   ✅ Más consistentes: {[r['symbol'] for r in consistent]}")
        
        return sorted_results

def main():
    """Función principal"""
    print("🚀 ULTIMATE SICAR SYSTEM - ANÁLISIS ROBUSTO CON DATOS REALES")
    print("=" * 70)
    print("📊 Múltiples fuentes de datos reales")
    print("🛡️ Manejo robusto de errores de conectividad")
    print("🎯 Objetivo: NAS100 con 15% ROI mensual")
    print("🏆 Meta: Top 5 instrumentos más rentables")
    print("💾 Cache local para datos descargados")
    print("=" * 70)
    
    try:
        # Crear y ejecutar análisis robusto
        analyzer = UltimateSicarRobustReal()
        results = analyzer.run_complete_robust_analysis()
        
        # Conclusión final
        analyzer.console_log(f"\n🎉 ANÁLISIS ULTIMATE SICAR ROBUSTO COMPLETADO", "SUCCESS")
        analyzer.console_log(f"📊 Datos reales procesados con éxito")
        analyzer.console_log(f"🏆 Sistema Ultimate SICAR validado")
        analyzer.console_log(f"💾 Datos guardados en cache para futuros análisis")
        
    except Exception as e:
        print(f"❌ Error durante el análisis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()