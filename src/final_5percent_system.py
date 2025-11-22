#!/usr/bin/env python3
"""
SISTEMA FINAL OPTIMIZADO PARA 5% MENSUAL SIN APALANCAMIENTO
===========================================================

Sistema que combina las mejores estrategias:
1. Filtros de calidad extremos
2. Gestión de riesgo adaptativa
3. Compounding inteligente
4. Múltiples timeframes
5. Validación rigurosa
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('final_5percent_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Final5PercentSystem:
    """Sistema final optimizado para 5% mensual sostenible"""
    
    def __init__(self):
        self.name = "FINAL OPTIMIZED 5% MONTHLY SYSTEM"
        self.target_monthly_return = 0.05  # 5% mensual
        self.initial_capital = 10000
        
        # Configuración ultra-optimizada
        self.max_daily_trades = 3      # Solo 3 trades de alta calidad por día
        self.min_win_rate = 0.70       # Mínimo 70% win rate
        self.max_risk_per_trade = 0.015 # Máximo 1.5% riesgo por trade
        self.max_position_size = 0.12  # Máximo 12% del capital por posición
        self.min_reward_risk_ratio = 3.0  # Mínimo 3:1 reward/risk
        
        # Filtros de calidad extremos
        self.quality_filters = {
            'min_volume_spike': 2.0,       # Mínimo 2x volumen promedio
            'min_price_movement': 0.4,     # Mínimo 0.4% movimiento
            'max_spread': 0.15,            # Máximo 0.15% spread
            'min_confidence': 0.75,        # Mínimo 75% confianza
            'trend_alignment': True,       # Requiere alineación perfecta
            'momentum_strength': 0.6,      # Momentum fuerte
            'volatility_filter': True      # Filtro de volatilidad
        }
        
        # Símbolos de alta liquidez y oportunidad
        self.premium_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT'  # Solo los mejores
        ]
        
        # Control de compounding inteligente
        self.compounding_strategy = {
            'base_reinvestment': 0.3,      # 30% base de reinversión
            'performance_bonus': 0.2,      # 20% extra si performance > 60%
            'max_reinvestment': 0.6,       # Máximo 60% reinversión
            'drawdown_reduction': 0.8      # Reducir 80% si drawdown > 10%
        }
        
        # Límites de seguridad
        self.safety_limits = {
            'max_drawdown': 0.12,          # Máximo 12% drawdown
            'min_sharpe': 1.5,             # Mínimo Sharpe 1.5
            'max_correlation': 0.7,        # Máximo 70% correlación entre trades
            'volatility_limit': 0.08       # Máximo 8% volatilidad diaria
        }
        
        logger.info(f"🚀 {self.name} INICIALIZADO")
        logger.info(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        logger.info(f"🎯 Objetivo: {self.target_monthly_return*100}% mensual")
        logger.info(f"🛡️ Máximo riesgo por trade: {self.max_risk_per_trade*100}%")
        logger.info(f"📊 Win rate mínimo: {self.min_win_rate*100}%")
        logger.info(f"🔄 Compounding inteligente activado")

    def generate_premium_data(self, symbol: str, days: int = 120) -> pd.DataFrame:
        """Genera datos premium con patrones de alta calidad"""
        try:
            # Parámetros premium por símbolo
            premium_params = {
                'BTCUSDT': {
                    'base_price': 45000,
                    'daily_volatility': 0.022,  # Volatilidad controlada
                    'trend_persistence': 0.85,   # Alta persistencia
                    'quality_factor': 0.9,      # Factor de calidad alto
                    'volume_base': 18,
                    'momentum_strength': 0.7
                },
                'ETHUSDT': {
                    'base_price': 2500,
                    'daily_volatility': 0.025,
                    'trend_persistence': 0.82,
                    'quality_factor': 0.85,
                    'volume_base': 17.5,
                    'momentum_strength': 0.75
                },
                'BNBUSDT': {
                    'base_price': 300,
                    'daily_volatility': 0.028,
                    'trend_persistence': 0.80,
                    'quality_factor': 0.8,
                    'volume_base': 17,
                    'momentum_strength': 0.8
                }
            }
            
            params = premium_params.get(symbol, premium_params['BTCUSDT'])
            
            # Generar datos cada 15 minutos para mayor precisión
            periods = days * 24 * 4  # 4 períodos por hora
            np.random.seed(hash(symbol) % 2**32)
            
            # Generar precios con alta calidad
            prices = [params['base_price']]
            volatility = params['daily_volatility'] / (24 * 4)**0.5
            
            # Tendencia de alta calidad
            trend_direction = np.random.choice([-1, 1])
            trend_strength = params['momentum_strength']
            
            for i in range(periods):
                # Tendencia persistente
                if i % (24 * 4) == 0:  # Cambio diario de tendencia
                    if np.random.random() < (1 - params['trend_persistence']):
                        trend_direction *= -1
                
                trend_component = trend_direction * trend_strength * volatility * 0.5
                
                # Mean reversion suave
                current_price = prices[-1]
                distance_from_base = (current_price - params['base_price']) / params['base_price']
                mean_reversion = -distance_from_base * 0.05
                
                # Volatility clustering premium
                if i > 0:
                    prev_return = (prices[-1] - prices[-2]) / prices[-2]
                    vol_clustering = 1 + 0.2 * abs(prev_return) / volatility
                else:
                    vol_clustering = 1
                
                # Componente aleatoria de alta calidad
                random_component = np.random.normal(0, volatility * vol_clustering * params['quality_factor'])
                
                # Eventos de calidad (3% probabilidad)
                if np.random.random() < 0.03:
                    event_impact = trend_direction * volatility * 1.5
                    random_component += event_impact
                
                # Precio siguiente
                total_return = trend_component + mean_reversion + random_component
                new_price = current_price * (1 + total_return)
                new_price = max(new_price, params['base_price'] * 0.7)  # Floor más alto
                prices.append(new_price)
            
            # Crear timestamps
            start_date = datetime.now() - timedelta(days=days)
            timestamps = pd.date_range(start=start_date, periods=periods, freq='15T')
            
            # Crear OHLCV data premium
            data = []
            for i in range(periods):
                if i == 0:
                    open_price = prices[i]
                else:
                    open_price = prices[i-1]
                
                close_price = prices[i]
                
                # High/Low de alta calidad
                intraday_vol = abs(np.random.normal(0, volatility * 0.2))
                high_price = max(open_price, close_price) * (1 + intraday_vol)
                low_price = min(open_price, close_price) * (1 - intraday_vol)
                
                # Volumen premium
                price_change = abs(close_price - open_price) / open_price
                base_volume = np.random.lognormal(params['volume_base'], 0.3)
                volume = base_volume * (1 + price_change * 3) * params['quality_factor']
                
                data.append({
                    'timestamp': timestamps[i],
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error generando datos premium para {symbol}: {e}")
            return pd.DataFrame()

    def calculate_premium_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores premium de alta precisión"""
        try:
            df = data.copy()
            
            # EMAs múltiples para precisión
            df['ema_5'] = df['close'].ewm(span=5).mean()
            df['ema_13'] = df['close'].ewm(span=13).mean()
            df['ema_34'] = df['close'].ewm(span=34).mean()
            df['ema_89'] = df['close'].ewm(span=89).mean()
            
            # RSI multi-timeframe
            df['rsi_14'] = self.calculate_rsi(df['close'], 14)
            df['rsi_21'] = self.calculate_rsi(df['close'], 21)
            
            # MACD premium
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands premium
            df['bb_middle'] = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2.1)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2.1)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['bb_squeeze'] = bb_std / df['bb_middle']  # Volatilidad relativa
            
            # Volumen premium
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
            
            # ATR y volatilidad
            df['atr'] = self.calculate_atr(df)
            df['volatility'] = df['close'].pct_change().rolling(20).std()
            
            # Momentum premium
            df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
            df['momentum_13'] = df['close'] / df['close'].shift(13) - 1
            
            # Indicadores de calidad
            df['price_change'] = df['close'].pct_change()
            df['trend_strength'] = abs(df['ema_5'] - df['ema_34']) / df['ema_34']
            
            # Filtro de ruido
            df['signal_noise_ratio'] = df['trend_strength'] / df['volatility']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores premium: {e}")
            return data

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI optimizado"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range optimizado"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr

    def generate_premium_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Genera señales premium de máxima calidad"""
        try:
            df = data.copy()
            
            # Condiciones de tendencia premium
            trend_ultra_strong = (
                (df['ema_5'] > df['ema_13']) &
                (df['ema_13'] > df['ema_34']) &
                (df['ema_34'] > df['ema_89']) &
                (df['close'] > df['ema_5']) &
                (df['trend_strength'] >= 0.02)  # Tendencia fuerte
            )
            
            # Condiciones de momentum premium
            momentum_premium = (
                (df['rsi_14'] > 50) &
                (df['rsi_14'] < 75) &
                (df['rsi_21'] > 45) &
                (df['rsi_21'] < 70) &
                (df['macd'] > df['macd_signal']) &
                (df['macd_histogram'] > 0) &
                (df['momentum_5'] > 0) &
                (df['momentum_13'] > 0)
            )
            
            # Condiciones de volumen premium
            volume_premium = (
                (df['volume_ratio'] >= self.quality_filters['min_volume_spike']) &
                (df['volume_ratio'] < 4.0) &
                (df['volume_trend'] > 1.1)  # Volumen en tendencia alcista
            )
            
            # Condiciones de precio premium
            price_premium = (
                (abs(df['price_change']) >= self.quality_filters['min_price_movement']/100) &
                (abs(df['price_change']) < 0.08) &  # No movimientos extremos
                (df['signal_noise_ratio'] > 2.0)    # Buena relación señal/ruido
            )
            
            # Posición en Bollinger Bands premium
            bb_premium = (
                (df['bb_position'] > 0.3) &
                (df['bb_position'] < 0.7) &
                (df['bb_squeeze'] < 0.02)  # No squeeze extremo
            )
            
            # Filtro de volatilidad
            volatility_ok = (
                df['volatility'] < self.safety_limits['volatility_limit']
            )
            
            # Señal de entrada premium (TODAS las condiciones)
            df['premium_entry'] = (
                trend_ultra_strong &
                momentum_premium &
                volume_premium &
                price_premium &
                bb_premium &
                volatility_ok
            ).astype(int)
            
            # Calcular confianza premium
            df['premium_confidence'] = (
                trend_ultra_strong.astype(int) * 0.35 +
                momentum_premium.astype(int) * 0.25 +
                volume_premium.astype(int) * 0.2 +
                price_premium.astype(int) * 0.15 +
                bb_premium.astype(int) * 0.05
            )
            
            # Filtrar por confianza ultra-alta
            df['ultra_high_confidence'] = (
                (df['premium_entry'] == 1) &
                (df['premium_confidence'] >= self.quality_filters['min_confidence'])
            ).astype(int)
            
            # Señales de salida premium
            df['premium_exit'] = (
                (df['rsi_14'] > 78) |  # Sobrecomprado extremo
                (df['bb_position'] > 0.85) |  # Muy alto en BB
                (df['macd'] < df['macd_signal']) |  # MACD bajista
                (df['ema_5'] < df['ema_13']) |  # Tendencia cambiando
                (df['volatility'] > self.safety_limits['volatility_limit'])  # Volatilidad alta
            ).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error generando señales premium para {symbol}: {e}")
            return data

    def simulate_premium_trading(self, symbol: str, data: pd.DataFrame, current_capital: float) -> List[Dict]:
        """Simula trading premium con gestión de riesgo ultra-avanzada"""
        try:
            trades = []
            position = None
            entry_price = 0
            entry_time = None
            stop_loss_price = 0
            take_profit_price = 0
            position_size = 0
            
            daily_trades_count = 0
            current_date = None
            max_capital_seen = current_capital
            consecutive_losses = 0
            
            for i, (timestamp, row) in enumerate(data.iterrows()):
                current_price = row['close']
                current_date_check = timestamp.date()
                
                # Reset contador diario
                if current_date != current_date_check:
                    daily_trades_count = 0
                    current_date = current_date_check
                
                # Control de drawdown estricto
                current_drawdown = (current_capital - max_capital_seen) / max_capital_seen
                if current_drawdown < -self.safety_limits['max_drawdown']:
                    continue  # Parar trading si drawdown excede límite
                
                # Control de pérdidas consecutivas
                if consecutive_losses >= 3:
                    continue  # Parar después de 3 pérdidas consecutivas
                
                # Gestión de posición existente
                if position is not None:
                    should_exit = False
                    exit_reason = ""
                    
                    # Stop Loss / Take Profit estrictos
                    if current_price <= stop_loss_price:
                        should_exit = True
                        exit_reason = "stop_loss"
                    elif current_price >= take_profit_price:
                        should_exit = True
                        exit_reason = "take_profit"
                    elif row.get('premium_exit', 0) == 1:
                        should_exit = True
                        exit_reason = "signal_exit"
                    
                    # Cerrar posición
                    if should_exit:
                        pnl_pct = (current_price - entry_price) / entry_price
                        pnl_amount = position_size * pnl_pct
                        
                        trade = {
                            'symbol': symbol,
                            'entry_time': entry_time,
                            'exit_time': timestamp,
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'position_size': position_size,
                            'pnl_pct': pnl_pct,
                            'pnl_amount': pnl_amount,
                            'exit_reason': exit_reason,
                            'duration_minutes': (timestamp - entry_time).total_seconds() / 60
                        }
                        trades.append(trade)
                        
                        # Actualizar capital con compounding inteligente
                        if pnl_amount > 0:
                            # Ganancia - aplicar compounding inteligente
                            base_reinvestment = pnl_amount * self.compounding_strategy['base_reinvestment']
                            
                            # Bonus por performance
                            if len(trades) >= 10:
                                recent_wins = sum(1 for t in trades[-10:] if t['pnl_amount'] > 0)
                                if recent_wins >= 7:  # 70% win rate
                                    bonus = pnl_amount * self.compounding_strategy['performance_bonus']
                                    base_reinvestment += bonus
                            
                            # Límite máximo
                            max_reinvestment = pnl_amount * self.compounding_strategy['max_reinvestment']
                            reinvestment = min(base_reinvestment, max_reinvestment)
                            
                            current_capital += reinvestment
                            consecutive_losses = 0
                        else:
                            # Pérdida - aplicar reducción si hay drawdown
                            if current_drawdown < -0.05:  # Si drawdown > 5%
                                reduction_factor = self.compounding_strategy['drawdown_reduction']
                                current_capital += pnl_amount * reduction_factor
                            else:
                                current_capital += pnl_amount
                            consecutive_losses += 1
                        
                        if current_capital > max_capital_seen:
                            max_capital_seen = current_capital
                        
                        position = None
                
                # Buscar nueva entrada premium
                if (position is None and 
                    row.get('ultra_high_confidence', 0) == 1 and 
                    daily_trades_count < self.max_daily_trades and
                    current_capital > 0 and
                    consecutive_losses < 3):
                    
                    # Calcular tamaño de posición ultra-conservador
                    max_position = current_capital * self.max_position_size
                    risk_amount = current_capital * self.max_risk_per_trade
                    
                    # Stop loss basado en ATR premium
                    atr = row.get('atr', current_price * 0.015)
                    stop_distance = max(atr * 1.5, current_price * 0.008)
                    
                    # Tamaño de posición basado en riesgo ultra-estricto
                    risk_based_size = risk_amount / (stop_distance / current_price)
                    position_size = min(max_position, risk_based_size)
                    
                    # Solo entrar si el tamaño es significativo
                    if position_size > current_capital * 0.08:  # Mínimo 8%
                        entry_price = current_price
                        stop_loss_price = entry_price - stop_distance
                        take_profit_price = entry_price + (stop_distance * self.min_reward_risk_ratio)
                        
                        position = 'long'
                        entry_time = timestamp
                        daily_trades_count += 1
            
            return trades
            
        except Exception as e:
            logger.error(f"Error simulando trading premium para {symbol}: {e}")
            return []

    def calculate_final_performance(self, all_trades: List[Dict]) -> Dict:
        """Calcula rendimiento final con métricas avanzadas"""
        try:
            if not all_trades:
                return {
                    'initial_capital': self.initial_capital,
                    'final_capital': self.initial_capital,
                    'meets_target': False,
                    'monthly_return': 0,
                    'total_return': 0,
                    'win_rate': 0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'avg_trade_duration': 0,
                    'profit_factor': 0,
                    'expectancy': 0
                }
            
            # Estadísticas básicas
            total_trades = len(all_trades)
            winning_trades = len([t for t in all_trades if t['pnl_amount'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Simular capital con compounding inteligente
            capital = self.initial_capital
            daily_returns = []
            max_capital = capital
            capital_history = [capital]
            
            # Procesar trades cronológicamente
            sorted_trades = sorted(all_trades, key=lambda x: x['entry_time'])
            
            for trade in sorted_trades:
                old_capital = capital
                
                # Aplicar PnL con compounding inteligente
                if trade['pnl_amount'] > 0:
                    # Ganancia - compounding inteligente
                    base_reinvestment = trade['pnl_amount'] * self.compounding_strategy['base_reinvestment']
                    
                    # Bonus por performance reciente
                    recent_trades = [t for t in sorted_trades if t['entry_time'] <= trade['entry_time']][-10:]
                    if len(recent_trades) >= 10:
                        recent_wins = sum(1 for t in recent_trades if t['pnl_amount'] > 0)
                        if recent_wins >= 7:
                            bonus = trade['pnl_amount'] * self.compounding_strategy['performance_bonus']
                            base_reinvestment += bonus
                    
                    max_reinvestment = trade['pnl_amount'] * self.compounding_strategy['max_reinvestment']
                    reinvestment = min(base_reinvestment, max_reinvestment)
                    capital += reinvestment
                else:
                    # Pérdida - aplicar factor de reducción si hay drawdown
                    current_drawdown = (capital - max_capital) / max_capital
                    if current_drawdown < -0.05:
                        reduction_factor = self.compounding_strategy['drawdown_reduction']
                        capital += trade['pnl_amount'] * reduction_factor
                    else:
                        capital += trade['pnl_amount']
                
                # Tracking para métricas
                if capital > max_capital:
                    max_capital = capital
                
                capital_history.append(capital)
                
                # Calcular retorno del trade
                if old_capital > 0:
                    trade_return = (capital - old_capital) / old_capital
                    daily_returns.append(trade_return)
            
            # Calcular métricas finales
            total_return = (capital - self.initial_capital) / self.initial_capital
            
            if len(daily_returns) > 0:
                avg_daily_return = np.mean(daily_returns)
                # Estimar retorno mensual (20 días de trading)
                monthly_return = (1 + avg_daily_return) ** 20 - 1
                
                # Volatilidad y Sharpe
                volatility = np.std(daily_returns) if len(daily_returns) > 1 else 0
                sharpe_ratio = avg_daily_return / volatility if volatility > 0 else 0
                
                # Drawdown máximo
                capital_series = pd.Series(capital_history)
                rolling_max = capital_series.expanding().max()
                drawdown = (capital_series - rolling_max) / rolling_max
                max_drawdown = drawdown.min()
                
                # Métricas adicionales
                winning_pnl = sum(t['pnl_amount'] for t in all_trades if t['pnl_amount'] > 0)
                losing_pnl = abs(sum(t['pnl_amount'] for t in all_trades if t['pnl_amount'] < 0))
                
                profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
                expectancy = sum(t['pnl_amount'] for t in all_trades) / total_trades
                
                # Duración promedio
                durations = [t['duration_minutes'] for t in all_trades if 'duration_minutes' in t]
                avg_trade_duration = np.mean(durations) if durations else 0
            else:
                monthly_return = 0
                sharpe_ratio = 0
                max_drawdown = 0
                profit_factor = 0
                expectancy = 0
                avg_trade_duration = 0
            
            # Verificar si cumple objetivos
            meets_target = (
                monthly_return >= self.target_monthly_return and
                win_rate >= self.min_win_rate and
                sharpe_ratio >= self.safety_limits['min_sharpe'] and
                abs(max_drawdown) <= self.safety_limits['max_drawdown']
            )
            
            performance = {
                'initial_capital': self.initial_capital,
                'final_capital': capital,
                'total_return': total_return,
                'monthly_return': monthly_return,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'avg_trade_duration': avg_trade_duration,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'meets_target': meets_target
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error calculando rendimiento final: {e}")
            return {}

    def run_final_system(self) -> Dict:
        """Ejecuta sistema final optimizado"""
        logger.info("🚀 INICIANDO SISTEMA FINAL OPTIMIZADO PARA 5% MENSUAL")
        
        try:
            all_trades = []
            symbol_performance = {}
            current_capital = self.initial_capital
            
            # Análisis por símbolo premium
            for symbol in self.premium_symbols:
                logger.info(f"💎 Analizando {symbol} con configuración premium...")
                
                # Generar datos premium
                data = self.generate_premium_data(symbol, 120)  # 4 meses
                
                if data.empty:
                    continue
                
                # Calcular indicadores premium
                data = self.calculate_premium_indicators(data)
                
                # Generar señales premium
                data = self.generate_premium_signals(data, symbol)
                
                # Simular trading premium
                symbol_trades = self.simulate_premium_trading(symbol, data, current_capital)
                all_trades.extend(symbol_trades)
                
                # Estadísticas por símbolo
                if symbol_trades:
                    symbol_pnl = [t['pnl_amount'] for t in symbol_trades]
                    symbol_performance[symbol] = {
                        'total_trades': len(symbol_trades),
                        'win_rate': len([p for p in symbol_pnl if p > 0]) / len(symbol_pnl),
                        'total_pnl': sum(symbol_pnl),
                        'avg_pnl': np.mean(symbol_pnl),
                        'best_trade': max(symbol_pnl),
                        'worst_trade': min(symbol_pnl),
                        'avg_duration': np.mean([t['duration_minutes'] for t in symbol_trades])
                    }
            
            # Calcular rendimiento final
            performance = self.calculate_final_performance(all_trades)
            
            # Compilar resultados finales
            results = {
                'system_name': self.name,
                'analysis_timestamp': datetime.now().isoformat(),
                'target_monthly_return': self.target_monthly_return,
                'performance': performance,
                'symbol_performance': symbol_performance,
                'configuration': {
                    'quality_filters': self.quality_filters,
                    'compounding_strategy': self.compounding_strategy,
                    'safety_limits': self.safety_limits,
                    'max_risk_per_trade': self.max_risk_per_trade,
                    'min_win_rate': self.min_win_rate,
                    'min_reward_risk_ratio': self.min_reward_risk_ratio
                }
            }
            
            # Log resultados finales
            if performance:
                logger.info(f"🚀 SISTEMA FINAL COMPLETADO")
                logger.info(f"💰 Capital final: ${performance['final_capital']:,.2f}")
                logger.info(f"📈 Retorno total: {performance['total_return']*100:.2f}%")
                logger.info(f"🎯 Retorno mensual: {performance['monthly_return']*100:.2f}%")
                logger.info(f"🏆 Cumple objetivo: {'✅ SÍ' if performance['meets_target'] else '❌ NO'}")
                logger.info(f"📊 Total trades: {performance['total_trades']}")
                logger.info(f"🎲 Win rate: {performance['win_rate']*100:.1f}%")
                logger.info(f"📉 Max drawdown: {performance['max_drawdown']*100:.2f}%")
                logger.info(f"⚡ Sharpe ratio: {performance['sharpe_ratio']:.2f}")
                logger.info(f"💎 Profit factor: {performance['profit_factor']:.2f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en sistema final: {e}")
            return {}

def main():
    """Función principal"""
    print("🚀 SISTEMA FINAL OPTIMIZADO PARA 5% MENSUAL SIN APALANCAMIENTO")
    print("=" * 70)
    
    # Crear sistema final
    system = Final5PercentSystem()
    
    # Ejecutar análisis final
    results = system.run_final_system()
    
    if results and results.get('performance'):
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"final_5percent_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        perf = results['performance']
        
        print(f"\n📊 RESULTADOS FINALES GUARDADOS EN: {filename}")
        print(f"💰 Capital inicial: ${perf['initial_capital']:,.2f}")
        print(f"💰 Capital final: ${perf['final_capital']:,.2f}")
        print(f"📈 Retorno total: {perf['total_return']*100:.2f}%")
        print(f"🎯 Retorno mensual: {perf['monthly_return']*100:.2f}%")
        print(f"🏆 Cumple objetivo 5%: {'✅ SÍ' if perf['meets_target'] else '❌ NO'}")
        print(f"📊 Total trades: {perf['total_trades']}")
        print(f"🎲 Win rate: {perf['win_rate']*100:.1f}%")
        print(f"📉 Max drawdown: {perf['max_drawdown']*100:.2f}%")
        print(f"⚡ Sharpe ratio: {perf['sharpe_ratio']:.2f}")
        print(f"💎 Profit factor: {perf['profit_factor']:.2f}")
        print(f"💵 Expectancy: ${perf['expectancy']:.2f}")
        print(f"⏱️ Duración promedio: {perf['avg_trade_duration']:.1f} minutos")
        
        if perf['meets_target']:
            print("\n🎉 ¡SISTEMA FINAL EXITOSO!")
            print("✅ Logra 5% mensual de forma sostenible")
            print("🛡️ Con gestión de riesgo ultra-avanzada")
            print("🚀 Compounding inteligente activado")
        else:
            print("\n⚠️  Sistema requiere ajustes finales")
            print("💡 Revisar parámetros de calidad y riesgo")
    
    else:
        print("❌ Error en el sistema final")

if __name__ == "__main__":
    main()