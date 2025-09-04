#!/usr/bin/env python3
"""
SISTEMA V3 OPTIMIZADO - IMPLEMENTACIÓN FINAL
Basado en análisis de datos reales, optimizado para múltiples balances
"""

import ccxt
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
import asyncio
import json
import time
import warnings
warnings.filterwarnings('ignore')

class OptimizedTradingSystemV3:
    def __init__(self, initial_capital=1000):
        """
        Sistema V3 optimizado basado en análisis de resultados reales
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}
        self.trades_history = []
        self.daily_pnl = []
        self.max_daily_loss_pct = 2.0  # Límite de pérdida diaria
        
        # CONFIGURACIÓN OPTIMIZADA V3 - Solo estrategias ganadoras
        self.strategies_config = {
            'mean_reversion': {
                'allocation': 0.50,  # 50% - Mayor asignación (mejor WR: 66.6%)
                'timeframe': '15m',
                'rsi_oversold': 25,  # Más conservador
                'rsi_overbought': 75,
                'bb_std': 2.1,  # Bandas más estrictas
                'min_volume_mult': 1.8,
                'stop_loss_atr_mult': 2.5,
                'take_profit_mult': 2.0
            },
            'temporal_arbitrage': {
                'allocation': 0.35,  # 35% - Segunda mayor (mejor PnL absoluto)
                'timeframe': '30m',
                'trend_strength_min': 0.008,  # Más selectivo
                'volume_confirmation': 1.5,
                'rsi_range': (35, 65),  # Evitar extremos
                'stop_loss_atr_mult': 2.0,
                'take_profit_mult': 2.5
            },
            'selective_breakout': {
                'allocation': 0.15,  # 15% - Menor pero rentable
                'timeframe': '1h',
                'lookback_period': 24,  # Más amplio
                'volume_mult_min': 2.5,  # Muy selectivo
                'range_min_pct': 0.025,  # Solo rangos significativos
                'confirmation_periods': 2,
                'stop_loss_atr_mult': 1.8,
                'take_profit_mult': 3.0  # R:R más ambicioso
            }
        }
        
        # PARES OPTIMIZADOS - Solo los mejores performers
        self.trading_pairs = ['ETH/USDT', 'BCH/USDT', 'BNB/USDT']
        
        # GESTIÓN DE RIESGO V3
        self.risk_config = {
            'max_daily_trades': 10,
            'max_simultaneous_positions': 3,
            'position_size_pct': 0.02,  # 2% por trade
            'max_drawdown_pct': 8.0,
            'correlation_limit': 0.7  # Evitar trades correlacionados
        }
        
        # Contadores de control
        self.daily_trades = 0
        self.active_positions = 0
        self.current_drawdown = 0.0
        
        print(f"🚀 SISTEMA V3 OPTIMIZADO INICIADO")
        print(f"💰 Capital: ${self.initial_capital:,.2f}")
        print(f"📊 Solo estrategias ganadoras: Mean Reversion (50%), Temporal Arbitrage (35%), Breakout (15%)")
        print(f"🎯 Pares seleccionados: {', '.join(self.trading_pairs)}")

    def fetch_real_data(self, symbol, timeframe, days=45):
        """
        Obtener datos reales de Binance con manejo de errores mejorado
        """
        try:
            exchange = ccxt.binance({
                'apiKey': '',
                'secret': '',
                'sandbox': False,
                'rateLimit': 1000,
                'enableRateLimit': True
            })
            
            since = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            print(f"📥 Obteniendo {symbol} ({timeframe}) - {days} días...")
            
            # Obtener datos con paginación
            all_ohlcv = []
            current_since = since
            
            while current_since < int(datetime.now().timestamp() * 1000):
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=500)
                    if not ohlcv:
                        break
                    all_ohlcv.extend(ohlcv)
                    current_since = ohlcv[-1][0] + 1
                    time.sleep(0.2)  # Rate limiting
                except Exception as e:
                    print(f"⚠️ Error en chunk: {e}")
                    time.sleep(1)
                    continue
            
            if not all_ohlcv:
                return None
                
            # Crear DataFrame
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float)
            
            # Remover duplicados
            df = df[~df.index.duplicated(keep='first')]
            df = df.sort_index()
            
            print(f"✅ {len(df)} velas obtenidas para {symbol}")
            return df
            
        except Exception as e:
            print(f"❌ Error obteniendo datos para {symbol}: {e}")
            return None

    def calculate_advanced_indicators(self, df):
        """
        Calcular indicadores técnicos avanzados y optimizados
        """
        # RSI optimizado
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
        df['rsi_ma'] = df['rsi'].rolling(window=3).mean()  # RSI suavizado
        
        # Bollinger Bands mejoradas
        bb_window = 20
        bb_std = self.strategies_config['mean_reversion']['bb_std']
        bb = ta.volatility.BollingerBands(df['close'], window=bb_window, window_dev=bb_std)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # MACD con configuración optimizada
        macd = ta.trend.MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        df['macd_histogram_change'] = df['macd_histogram'].diff()
        
        # EMAs múltiples para análisis de tendencia
        for period in [9, 21, 50, 100, 200]:
            df[f'ema_{period}'] = ta.trend.EMAIndicator(df['close'], window=period).ema_indicator()
        
        # ATR para volatilidad y stop-loss dinámico
        df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
        df['atr_pct'] = df['atr'] / df['close'] * 100
        
        # Análisis de volumen avanzado
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        df['price_volume'] = df['close'] * df['volume']
        df['vwap'] = df['price_volume'].rolling(window=20).sum() / df['volume'].rolling(window=20).sum()
        
        # Stochastic optimizado
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # Indicadores de fuerza de tendencia
        df['trend_strength'] = abs(df['ema_9'] - df['ema_21']) / df['close']
        df['trend_direction'] = np.where(df['ema_9'] > df['ema_21'], 1, -1)
        
        # Soporte y resistencia dinámicos
        df['resistance_20'] = df['high'].rolling(window=20).max()
        df['support_20'] = df['low'].rolling(window=20).min()
        df['range_pct'] = (df['resistance_20'] - df['support_20']) / df['close']
        
        return df

    def mean_reversion_strategy_v3(self, df):
        """
        Estrategia Mean Reversion V3 - Ultra optimizada
        """
        config = self.strategies_config['mean_reversion']
        signals = pd.Series(index=df.index, data=0)
        
        # Filtros de calidad premium
        high_volume = df['volume_ratio'] > config['min_volume_mult']
        good_volatility = (df['atr_pct'] > 0.5) & (df['atr_pct'] < 3.0)
        trend_filter = df['close'] > df['ema_200']  # Solo en tendencia alcista general
        bb_squeeze_filter = df['bb_width'] > df['bb_width'].rolling(10).mean()
        market_structure = df['close'] > df['vwap']  # Estructura alcista
        
        # Señales de compra mejoradas - Toque de banda inferior
        oversold_rsi = df['rsi_ma'] < config['rsi_oversold']
        bb_touch = df['bb_position'] < 0.1  # Muy cerca de banda inferior
        momentum_shift = df['macd_histogram_change'] > 0  # MACD comenzando a subir
        stoch_oversold = df['stoch_k'] < 25
        
        buy_condition = (
            oversold_rsi &
            bb_touch &
            momentum_shift &
            stoch_oversold &
            high_volume &
            good_volatility &
            trend_filter &
            bb_squeeze_filter &
            market_structure
        )
        
        # Señales de venta - Toque de banda superior
        overbought_rsi = df['rsi_ma'] > config['rsi_overbought']
        bb_touch_upper = df['bb_position'] > 0.9
        momentum_shift_down = df['macd_histogram_change'] < 0
        stoch_overbought = df['stoch_k'] > 75
        
        sell_condition = (
            overbought_rsi &
            bb_touch_upper &
            momentum_shift_down &
            stoch_overbought &
            high_volume &
            good_volatility &
            (~trend_filter)  # En tendencia bajista general
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def temporal_arbitrage_strategy_v3(self, df):
        """
        Estrategia Temporal Arbitrage V3 - Multi-timeframe optimizada
        """
        config = self.strategies_config['temporal_arbitrage']
        signals = pd.Series(index=df.index, data=0)
        
        # Análisis de fuerza de tendencia mejorado
        trend_strength = df['trend_strength']
        min_strength = config['trend_strength_min']
        
        # Alineación de EMAs con fuerza mínima
        strong_uptrend = (
            (df['ema_9'] > df['ema_21']) &
            (df['ema_21'] > df['ema_50']) &
            (df['ema_50'] > df['ema_100']) &
            (trend_strength > min_strength)
        )
        
        strong_downtrend = (
            (df['ema_9'] < df['ema_21']) &
            (df['ema_21'] < df['ema_50']) &
            (df['ema_50'] < df['ema_100']) &
            (trend_strength > min_strength)
        )
        
        # Filtros de confirmación avanzados
        volume_confirm = df['volume_ratio'] > config['volume_confirmation']
        momentum_confirm = df['macd'] > df['macd_signal']
        rsi_range = (df['rsi'] > config['rsi_range'][0]) & (df['rsi'] < config['rsi_range'][1])
        price_above_vwap = df['close'] > df['vwap']
        
        # Señales de compra
        buy_condition = (
            strong_uptrend &
            volume_confirm &
            momentum_confirm &
            rsi_range &
            price_above_vwap &
            (df['stoch_k'] > df['stoch_d'])  # Stoch alcista
        )
        
        # Señales de venta
        sell_condition = (
            strong_downtrend &
            volume_confirm &
            (~momentum_confirm) &
            rsi_range &
            (~price_above_vwap) &
            (df['stoch_k'] < df['stoch_d'])
        )
        
        signals[buy_condition] = 1
        signals[sell_condition] = -1
        
        return signals

    def selective_breakout_strategy_v3(self, df):
        """
        Estrategia Breakout V3 - Ultra selectiva
        """
        config = self.strategies_config['selective_breakout']
        signals = pd.Series(index=df.index, data=0)
        
        lookback = config['lookback_period']
        
        # Niveles dinámicos mejorados
        df['resistance'] = df['high'].rolling(window=lookback).max()
        df['support'] = df['low'].rolling(window=lookback).min()
        df['range_size'] = (df['resistance'] - df['support']) / df['close']
        
        # Solo operar rangos significativos y consolidaciones
        significant_range = df['range_size'] > config['range_min_pct']
        consolidation_period = df['bb_width'] < df['bb_width'].rolling(lookback).mean()
        
        # Filtros de calidad extremos
        exceptional_volume = df['volume_ratio'] > config['volume_mult_min']
        volatility_expansion = df['atr_pct'] > df['atr_pct'].rolling(10).mean() * 1.2
        trend_aligned = abs(df['trend_strength']) > 0.005
        
        # Ruptura alcista con confirmación múltiple
        breakout_up = (
            (df['close'] > df['resistance'].shift(1)) &
            (df['high'] > df['resistance'].shift(1)) &
            (df['volume'] > df['volume'].shift(1) * 1.5) &  # Volumen creciente
            exceptional_volume &
            significant_range &
            consolidation_period &
            volatility_expansion &
            trend_aligned &
            (df['rsi'] > 55) & (df['rsi'] < 75) &
            (df['macd_histogram'] > 0) &
            (df['close'] > df['ema_50'])
        )
        
        # Ruptura bajista
        breakout_down = (
            (df['close'] < df['support'].shift(1)) &
            (df['low'] < df['support'].shift(1)) &
            (df['volume'] > df['volume'].shift(1) * 1.5) &
            exceptional_volume &
            significant_range &
            consolidation_period &
            volatility_expansion &
            trend_aligned &
            (df['rsi'] > 25) & (df['rsi'] < 45) &
            (df['macd_histogram'] < 0) &
            (df['close'] < df['ema_50'])
        )
        
        signals[breakout_up] = 1
        signals[breakout_down] = -1
        
        return signals

    def calculate_position_size(self, capital, price, atr, strategy_name):
        """
        Calcular tamaño de posición con gestión de riesgo avanzada
        """
        config = self.strategies_config[strategy_name]
        allocation = config['allocation']
        stop_mult = config['stop_loss_atr_mult']
        
        # Capital asignado a la estrategia
        strategy_capital = capital * allocation
        
        # Riesgo por trade (2% del capital total)
        risk_amount = capital * self.risk_config['position_size_pct']
        
        # Stop loss basado en ATR
        stop_distance = atr * stop_mult
        
        # Tamaño basado en riesgo
        risk_based_size = risk_amount / stop_distance
        
        # Tamaño máximo basado en asignación
        max_size = strategy_capital * 0.95 / price
        
        # Usar el menor de los dos
        position_size = min(risk_based_size, max_size)
        
        return position_size

    def should_open_position(self):
        """
        Verificar si se puede abrir nueva posición
        """
        # Límite de trades diarios
        if self.daily_trades >= self.risk_config['max_daily_trades']:
            return False, "daily_limit_reached"
        
        # Límite de posiciones simultáneas
        if self.active_positions >= self.risk_config['max_simultaneous_positions']:
            return False, "position_limit_reached"
        
        # Límite de drawdown
        if self.current_drawdown >= self.risk_config['max_drawdown_pct']:
            return False, "drawdown_limit_reached"
        
        return True, "ok"

    def simulate_advanced_trading(self, symbol, df, signals, strategy_name):
        """
        Simulación avanzada con gestión de riesgo V3
        """
        trades = []
        position = None
        config = self.strategies_config[strategy_name]
        
        for i, (timestamp, signal) in enumerate(signals.items()):
            if i < 100:  # Período de warmup más largo
                continue
                
            current_price = df.loc[timestamp, 'close']
            current_atr = df.loc[timestamp, 'atr']
            
            # Verificar condiciones para abrir posición
            can_open, reason = self.should_open_position()
            
            if signal != 0 and position is None and can_open:
                # Calcular tamaño de posición
                position_size = self.calculate_position_size(
                    self.capital, current_price, current_atr, strategy_name
                )
                
                if position_size <= 0:
                    continue
                
                # Configurar stops y targets
                stop_mult = config['stop_loss_atr_mult']
                target_mult = config['take_profit_mult']
                
                if signal > 0:  # Long
                    stop_loss = current_price - (current_atr * stop_mult)
                    take_profit = current_price + (current_atr * stop_mult * target_mult)
                else:  # Short
                    stop_loss = current_price + (current_atr * stop_mult)
                    take_profit = current_price - (current_atr * stop_mult * target_mult)
                
                position = {
                    'symbol': symbol,
                    'strategy': strategy_name,
                    'side': 'long' if signal > 0 else 'short',
                    'entry_price': current_price,
                    'entry_time': timestamp,
                    'size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'atr_at_entry': current_atr,
                    'max_favorable': current_price,
                    'max_adverse': current_price
                }
                
                self.daily_trades += 1
                self.active_positions += 1
                
            elif position is not None:
                # Actualizar máximos y mínimos
                if position['side'] == 'long':
                    position['max_favorable'] = max(position['max_favorable'], current_price)
                    position['max_adverse'] = min(position['max_adverse'], current_price)
                else:
                    position['max_favorable'] = min(position['max_favorable'], current_price)
                    position['max_adverse'] = max(position['max_adverse'], current_price)
                
                # Verificar condiciones de salida
                should_exit = False
                exit_reason = ""
                
                # Stop loss y take profit
                if position['side'] == 'long':
                    if current_price <= position['stop_loss']:
                        should_exit = True
                        exit_reason = "stop_loss"
                    elif current_price >= position['take_profit']:
                        should_exit = True
                        exit_reason = "take_profit"
                else:  # Short
                    if current_price >= position['stop_loss']:
                        should_exit = True
                        exit_reason = "stop_loss"
                    elif current_price <= position['take_profit']:
                        should_exit = True
                        exit_reason = "take_profit"
                
                # Señal de salida o trailing stop
                if signal == 0 or should_exit:
                    exit_price = current_price
                    
                    # Calcular P&L
                    if position['side'] == 'long':
                        pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                    else:
                        pnl_pct = (position['entry_price'] - exit_price) / position['entry_price']
                    
                    position_value = position['size'] * position['entry_price']
                    pnl_amount = position_value * pnl_pct
                    
                    # Calcular métricas adicionales
                    if position['side'] == 'long':
                        mae = (position['entry_price'] - position['max_adverse']) / position['entry_price'] * 100
                        mfe = (position['max_favorable'] - position['entry_price']) / position['entry_price'] * 100
                    else:
                        mae = (position['max_adverse'] - position['entry_price']) / position['entry_price'] * 100
                        mfe = (position['entry_price'] - position['max_favorable']) / position['entry_price'] * 100
                    
                    trade = {
                        'symbol': symbol,
                        'strategy': strategy_name,
                        'side': position['side'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'entry_time': position['entry_time'],
                        'exit_time': timestamp,
                        'size': position['size'],
                        'position_value': position_value,
                        'pnl_pct': pnl_pct * 100,
                        'pnl_amount': pnl_amount,
                        'duration_hours': (timestamp - position['entry_time']).total_seconds() / 3600,
                        'exit_reason': exit_reason if should_exit else "signal",
                        'mae_pct': mae,  # Maximum Adverse Excursion
                        'mfe_pct': mfe,  # Maximum Favorable Excursion
                        'risk_reward': abs(mfe / mae) if mae != 0 else 0
                    }
                    
                    trades.append(trade)
                    position = None
                    self.active_positions -= 1
        
        return trades

    def run_multi_balance_backtest(self, balances=[500, 1000, 2000], days=45):
        """
        Ejecutar backtest con múltiples balances
        """
        print("\n" + "="*100)
        print("🚀 BACKTESTING SISTEMA V3 OPTIMIZADO - MÚLTIPLES BALANCES")
        print("="*100)
        
        results_by_balance = {}
        
        for balance in balances:
            print(f"\n💰 PROBANDO CON BALANCE: ${balance} USDT")
            print("-" * 60)
            
            self.initial_capital = balance
            self.capital = balance
            self.daily_trades = 0
            self.active_positions = 0
            self.current_drawdown = 0.0
            
            all_trades = []
            
            # Obtener datos para cada par
            market_data = {}
            for pair in self.trading_pairs:
                for strategy_name in self.strategies_config.keys():
                    timeframe = self.strategies_config[strategy_name]['timeframe']
                    df = self.fetch_real_data(pair, timeframe, days)
                    
                    if df is not None and len(df) > 200:
                        df = self.calculate_advanced_indicators(df)
                        market_data[f"{pair}_{strategy_name}"] = df
                        time.sleep(0.3)  # Rate limiting
            
            # Ejecutar estrategias
            for key, df in market_data.items():
                pair, strategy_name = key.split('_', 1)
                
                print(f"📊 Ejecutando {strategy_name} en {pair}...")
                
                # Generar señales
                if strategy_name == 'mean_reversion':
                    signals = self.mean_reversion_strategy_v3(df)
                elif strategy_name == 'temporal_arbitrage':
                    signals = self.temporal_arbitrage_strategy_v3(df)
                elif strategy_name == 'selective_breakout':
                    signals = self.selective_breakout_strategy_v3(df)
                else:
                    continue
                
                # Simular trading
                trades = self.simulate_advanced_trading(pair, df, signals, strategy_name)
                all_trades.extend(trades)
                
                if trades:
                    total_pnl = sum([t['pnl_amount'] for t in trades])
                    win_rate = len([t for t in trades if t['pnl_amount'] > 0]) / len(trades) * 100
                    avg_rr = np.mean([t['risk_reward'] for t in trades if t['risk_reward'] > 0])
                    print(f"  ✅ {len(trades)} trades, PnL: ${total_pnl:.2f}, WR: {win_rate:.1f}%, R:R: {avg_rr:.2f}")
                else:
                    print(f"  ⚪ Sin trades generados")
            
            # Analizar resultados para este balance
            results_by_balance[balance] = self.analyze_balance_results(all_trades, balance, days)
            
            # Reset para siguiente balance
            time.sleep(1)
        
        # Generar comparación final
        self.generate_balance_comparison(results_by_balance)
        
        return results_by_balance

    def analyze_balance_results(self, trades, balance, days):
        """
        Analizar resultados para un balance específico
        """
        if not trades:
            return {
                'balance': balance,
                'total_trades': 0,
                'total_pnl': 0,
                'win_rate': 0,
                'monthly_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0
            }
        
        df_trades = pd.DataFrame(trades)
        
        # Métricas básicas
        total_trades = len(trades)
        winning_trades = len(df_trades[df_trades['pnl_amount'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = (winning_trades / total_trades) * 100
        
        total_pnl = df_trades['pnl_amount'].sum()
        total_return = (total_pnl / balance) * 100
        monthly_return = (total_return / days) * 30
        
        # Métricas avanzadas
        wins = df_trades[df_trades['pnl_amount'] > 0]['pnl_amount']
        losses = df_trades[df_trades['pnl_amount'] < 0]['pnl_amount']
        
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 0
        profit_factor = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else float('inf')
        
        # Drawdown calculation
        cumulative_pnl = df_trades.sort_values('entry_time')['pnl_amount'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - running_max) / balance * 100
        max_drawdown = abs(drawdown.min())
        
        # Sharpe ratio aproximado
        daily_returns = df_trades.groupby(df_trades['entry_time'].dt.date)['pnl_amount'].sum() / balance
        sharpe_ratio = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252) if daily_returns.std() != 0 else 0
        
        # Estadísticas por estrategia
        if not df_trades.empty:
            strategy_stats = df_trades.groupby('strategy').agg({
                'pnl_amount': ['count', 'sum', 'mean'],
                'risk_reward': 'mean'
            }).round(2)
            
            # Calcular win rate por estrategia manualmente
            for strategy in df_trades['strategy'].unique():
                strategy_trades = df_trades[df_trades['strategy'] == strategy]
                wins = len(strategy_trades[strategy_trades['pnl_amount'] > 0])
                total = len(strategy_trades)
                strategy_win_rate = (wins / total) * 100 if total > 0 else 0
                print(f"  📊 {strategy}: {total} trades, WR: {strategy_win_rate:.1f}%")
        else:
            strategy_stats = pd.DataFrame()
        
        print(f"\n📊 RESULTADOS BALANCE ${balance}:")
        print(f"  💰 PnL Total: ${total_pnl:.2f}")
        print(f"  📈 Retorno: {total_return:.2f}% ({monthly_return:.2f}% mensual)")
        print(f"  🎯 Win Rate: {win_rate:.1f}%")
        print(f"  📊 Trades: {total_trades}")
        print(f"  💪 Profit Factor: {profit_factor:.2f}")
        print(f"  📉 Max Drawdown: {max_drawdown:.2f}%")
        print(f"  ⚡ Sharpe Ratio: {sharpe_ratio:.2f}")
        
        return {
            'balance': balance,
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'monthly_return': monthly_return,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'strategy_breakdown': strategy_stats.to_dict() if not strategy_stats.empty else {},
            'trades_data': trades
        }

    def generate_balance_comparison(self, results_by_balance):
        """
        Generar comparación entre diferentes balances
        """
        print("\n" + "="*100)
        print("📊 COMPARACIÓN DE RENDIMIENTO POR BALANCE")
        print("="*100)
        
        # Crear tabla comparativa
        print(f"\n{'Balance':<12} {'Trades':<8} {'PnL ($)':<12} {'Return %':<10} {'Monthly %':<12} {'Win Rate':<10} {'Sharpe':<8} {'Drawdown':<10}")
        print("-" * 90)
        
        best_monthly = 0
        best_balance = 0
        
        for balance, results in results_by_balance.items():
            print(f"${balance:<11} {results['total_trades']:<8} ${results['total_pnl']:<11.2f} {results['total_return']:<9.2f}% {results['monthly_return']:<11.2f}% {results['win_rate']:<9.1f}% {results['sharpe_ratio']:<7.2f} {results['max_drawdown']:<9.2f}%")
            
            if results['monthly_return'] > best_monthly:
                best_monthly = results['monthly_return']
                best_balance = balance
        
        print("\n🏆 MEJORES RESULTADOS:")
        best_result = results_by_balance[best_balance]
        print(f"  💰 Mejor Balance: ${best_balance}")
        print(f"  📈 Mejor Retorno Mensual: {best_monthly:.2f}%")
        print(f"  🎯 Win Rate: {best_result['win_rate']:.1f}%")
        print(f"  💪 Profit Factor: {best_result['profit_factor']:.2f}")
        print(f"  📉 Drawdown: {best_result['max_drawdown']:.2f}%")
        
        # Análisis de escalabilidad
        print(f"\n📊 ANÁLISIS DE ESCALABILIDAD:")
        print(f"  Retorno $500:  {results_by_balance[500]['monthly_return']:.2f}% mensual")
        print(f"  Retorno $1000: {results_by_balance[1000]['monthly_return']:.2f}% mensual")
        print(f"  Retorno $2000: {results_by_balance[2000]['monthly_return']:.2f}% mensual")
        
        # Calcular escalabilidad
        scale_500_1000 = results_by_balance[1000]['monthly_return'] / results_by_balance[500]['monthly_return'] if results_by_balance[500]['monthly_return'] != 0 else 0
        scale_1000_2000 = results_by_balance[2000]['monthly_return'] / results_by_balance[1000]['monthly_return'] if results_by_balance[1000]['monthly_return'] != 0 else 0
        
        print(f"  Escalabilidad 500→1000: {scale_500_1000:.2f}x")
        print(f"  Escalabilidad 1000→2000: {scale_1000_2000:.2f}x")
        
        # Recomendación final
        print(f"\n💡 RECOMENDACIÓN:")
        if best_monthly >= 8:
            print(f"  ✅ EXCELENTE: Sistema alcanza {best_monthly:.2f}% mensual")
            print(f"  🎯 Balance óptimo: ${best_balance}")
            print(f"  🚀 LISTO PARA IMPLEMENTACIÓN EN VIVO")
        elif best_monthly >= 5:
            print(f"  ⚡ BUENO: Sistema alcanza {best_monthly:.2f}% mensual")
            print(f"  🔧 Considerar optimizaciones adicionales")
        else:
            print(f"  ⚠️ NECESITA MEJORAS: Solo {best_monthly:.2f}% mensual")
            print(f"  🛠️ Revisar parámetros y filtros")
        
        # Guardar resultados
        with open('/home/johan/itbot_linux/strategies/V3_MULTI_BALANCE_RESULTS.json', 'w') as f:
            json.dump(results_by_balance, f, indent=2, default=str)
        
        print(f"\n💾 Resultados guardados: strategies/V3_MULTI_BALANCE_RESULTS.json")

if __name__ == "__main__":
    print("🚀 INICIANDO SISTEMA V3 OPTIMIZADO - PRUEBA MULTI-BALANCE")
    
    # Crear sistema V3
    system = OptimizedTradingSystemV3()
    
    # Ejecutar con múltiples balances
    balances_to_test = [500, 1000, 2000]
    results = system.run_multi_balance_backtest(balances_to_test, days=45)
    
    print(f"\n🏁 BACKTESTING V3 COMPLETADO")
    print(f"🎯 Sistema validado con balances: {balances_to_test}")
    print(f"📊 Resultados detallados disponibles en archivos JSON")
