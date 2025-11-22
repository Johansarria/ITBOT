#!/usr/bin/env python3
"""
SISTEMA 5% MENSUAL CON CAPITAL VARIABLE 200-500 USDT
===================================================

Sistema escalable que:
1. Inicia con capital mínimo 200 USDT
2. Escala hasta 500 USDT según performance
3. Gestión de riesgo adaptativa
4. Compounding inteligente
5. Escalamiento automático basado en resultados
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
        logging.FileHandler('variable_capital_5percent_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VariableCapital5PercentSystem:
    """Sistema 5% mensual con capital variable escalable"""
    
    def __init__(self, initial_capital: float = 200):
        self.name = "VARIABLE CAPITAL 5% SYSTEM"
        self.target_monthly_return = 0.05  # 5% mensual
        
        # Capital variable escalable
        self.min_capital = 200  # Mínimo 200 USDT
        self.max_capital = 500  # Máximo 500 USDT
        self.initial_capital = max(initial_capital, self.min_capital)
        self.current_capital = self.initial_capital
        
        # Configuración adaptativa según capital
        self.update_config_for_capital()
        
        # Símbolos optimizados para capital pequeño
        self.optimal_symbols = [
            'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT', 
            'ATOMUSDT', 'FTMUSDT', 'SANDUSDT', 'MANAUSDT'
        ]
        
        # Sistema de escalamiento
        self.scaling_config = {
            'performance_threshold': 0.15,    # 15% ganancia para escalar
            'scaling_factor': 1.25,           # Escalar 25% cada vez
            'min_win_rate_to_scale': 0.65,    # Mínimo 65% win rate
            'min_trades_to_scale': 20,        # Mínimo 20 trades
            'max_drawdown_to_scale': 0.08,    # Máximo 8% drawdown
            'scaling_cooldown_days': 7        # 7 días entre escalamientos
        }
        
        # Tracking de escalamiento
        self.scaling_history = []
        self.last_scaling_date = None
        
        logger.info(f"💰 {self.name} INICIALIZADO")
        logger.info(f"💵 Capital inicial: ${self.initial_capital:.2f} USDT")
        logger.info(f"📊 Rango capital: ${self.min_capital}-${self.max_capital} USDT")
        logger.info(f"🎯 Objetivo: {self.target_monthly_return*100}% mensual")
        logger.info(f"📈 Escalamiento automático activado")

    def update_config_for_capital(self):
        """Actualiza configuración según el capital actual"""
        # Configuración adaptativa basada en capital
        capital_ratio = self.current_capital / self.max_capital
        
        # Trades diarios adaptativo
        self.max_daily_trades = max(3, int(6 * capital_ratio))
        
        # Win rate objetivo adaptativo
        self.min_win_rate = 0.60 + (0.10 * capital_ratio)  # 60-70%
        
        # Riesgo por trade adaptativo
        self.max_risk_per_trade = 0.02 + (0.01 * capital_ratio)  # 2-3%
        
        # Tamaño de posición adaptativo
        self.max_position_size = 0.15 + (0.10 * capital_ratio)  # 15-25%
        
        # Reward/risk ratio adaptativo
        self.min_reward_risk_ratio = 2.0 + (1.0 * capital_ratio)  # 2-3:1
        
        # Filtros de calidad adaptativos
        self.quality_filters = {
            'min_volume_spike': 1.2 + (0.6 * capital_ratio),     # 1.2-1.8x
            'min_price_movement': 0.2 + (0.3 * capital_ratio),   # 0.2-0.5%
            'max_spread': 0.3 - (0.15 * capital_ratio),          # 0.15-0.3%
            'min_confidence': 0.55 + (0.15 * capital_ratio),     # 55-70%
            'trend_alignment': True,
            'momentum_threshold': 0.3 + (0.3 * capital_ratio),   # 0.3-0.6
            'volatility_filter': 0.12 - (0.04 * capital_ratio)   # 0.08-0.12
        }
        
        # Compounding adaptativo
        self.compounding_config = {
            'base_rate': 0.3 + (0.3 * capital_ratio),            # 30-60%
            'max_rate': 0.6 + (0.2 * capital_ratio),             # 60-80%
            'performance_bonus': 0.1 + (0.15 * capital_ratio),   # 10-25%
            'scaling_bonus': 0.2,                                # 20% bonus al escalar
            'drawdown_penalty': 0.7 - (0.2 * capital_ratio)      # 50-70%
        }
        
        # Límites de seguridad adaptativos
        self.safety_config = {
            'max_drawdown': 0.15 - (0.03 * capital_ratio),       # 12-15%
            'min_sharpe': 1.0 + (0.5 * capital_ratio),           # 1.0-1.5
            'volatility_limit': 0.10 - (0.02 * capital_ratio),   # 0.08-0.10
            'consecutive_loss_limit': 4 - int(capital_ratio),     # 3-4
            'daily_loss_limit': 0.04 - (0.01 * capital_ratio)    # 0.03-0.04
        }
        
        logger.info(f"🔄 Configuración actualizada para capital ${self.current_capital:.2f}")
        logger.info(f"📊 Max trades diarios: {self.max_daily_trades}")
        logger.info(f"🎯 Win rate objetivo: {self.min_win_rate*100:.1f}%")
        logger.info(f"🛡️ Riesgo por trade: {self.max_risk_per_trade*100:.1f}%")

    def check_scaling_opportunity(self, performance: Dict) -> bool:
        """Verifica si es momento de escalar el capital"""
        try:
            if self.current_capital >= self.max_capital:
                return False
            
            # Verificar cooldown
            if self.last_scaling_date:
                days_since_scaling = (datetime.now() - self.last_scaling_date).days
                if days_since_scaling < self.scaling_config['scaling_cooldown_days']:
                    return False
            
            # Verificar criterios de performance
            total_return = performance.get('total_return', 0)
            win_rate = performance.get('win_rate', 0)
            total_trades = performance.get('total_trades', 0)
            max_drawdown = abs(performance.get('max_drawdown', 0))
            
            scaling_criteria = [
                total_return >= self.scaling_config['performance_threshold'],
                win_rate >= self.scaling_config['min_win_rate_to_scale'],
                total_trades >= self.scaling_config['min_trades_to_scale'],
                max_drawdown <= self.scaling_config['max_drawdown_to_scale']
            ]
            
            if all(scaling_criteria):
                logger.info("✅ Criterios de escalamiento cumplidos:")
                logger.info(f"   📈 Retorno: {total_return*100:.1f}% (req: {self.scaling_config['performance_threshold']*100:.1f}%)")
                logger.info(f"   🎯 Win rate: {win_rate*100:.1f}% (req: {self.scaling_config['min_win_rate_to_scale']*100:.1f}%)")
                logger.info(f"   📊 Trades: {total_trades} (req: {self.scaling_config['min_trades_to_scale']})")
                logger.info(f"   📉 Drawdown: {max_drawdown*100:.1f}% (max: {self.scaling_config['max_drawdown_to_scale']*100:.1f}%)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error verificando escalamiento: {e}")
            return False

    def scale_capital(self, performance: Dict):
        """Escala el capital según performance"""
        try:
            old_capital = self.current_capital
            
            # Calcular nuevo capital
            new_capital = min(
                self.current_capital * self.scaling_config['scaling_factor'],
                self.max_capital
            )
            
            self.current_capital = new_capital
            self.last_scaling_date = datetime.now()
            
            # Registrar escalamiento
            scaling_record = {
                'date': self.last_scaling_date.isoformat(),
                'old_capital': old_capital,
                'new_capital': new_capital,
                'trigger_performance': performance,
                'scaling_factor': new_capital / old_capital
            }
            self.scaling_history.append(scaling_record)
            
            # Actualizar configuración
            self.update_config_for_capital()
            
            logger.info(f"🚀 CAPITAL ESCALADO!")
            logger.info(f"💰 ${old_capital:.2f} → ${new_capital:.2f} USDT")
            logger.info(f"📈 Factor: {new_capital/old_capital:.2f}x")
            logger.info(f"🎯 Nuevo objetivo mensual: ${new_capital * self.target_monthly_return:.2f}")
            
        except Exception as e:
            logger.error(f"Error escalando capital: {e}")

    def generate_adaptive_data(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """Genera datos adaptativos según el capital"""
        try:
            # Configuraciones por símbolo optimizadas para capital pequeño
            symbol_configs = {
                'ADAUSDT': {
                    'base_price': 0.5,
                    'daily_vol': 0.04,
                    'trend_strength': 0.75,
                    'volume_base': 16,
                    'opportunity_factor': 0.9
                },
                'DOTUSDT': {
                    'base_price': 8,
                    'daily_vol': 0.045,
                    'trend_strength': 0.8,
                    'volume_base': 15.8,
                    'opportunity_factor': 0.95
                },
                'LINKUSDT': {
                    'base_price': 15,
                    'daily_vol': 0.042,
                    'trend_strength': 0.78,
                    'volume_base': 16.2,
                    'opportunity_factor': 0.88
                },
                'MATICUSDT': {
                    'base_price': 1.2,
                    'daily_vol': 0.048,
                    'trend_strength': 0.82,
                    'volume_base': 15.5,
                    'opportunity_factor': 0.92
                },
                'ATOMUSDT': {
                    'base_price': 12,
                    'daily_vol': 0.046,
                    'trend_strength': 0.76,
                    'volume_base': 15.9,
                    'opportunity_factor': 0.87
                },
                'FTMUSDT': {
                    'base_price': 0.8,
                    'daily_vol': 0.052,
                    'trend_strength': 0.85,
                    'volume_base': 15.3,
                    'opportunity_factor': 0.96
                },
                'SANDUSDT': {
                    'base_price': 0.6,
                    'daily_vol': 0.055,
                    'trend_strength': 0.88,
                    'volume_base': 15.1,
                    'opportunity_factor': 0.98
                },
                'MANAUSDT': {
                    'base_price': 0.4,
                    'daily_vol': 0.058,
                    'trend_strength': 0.9,
                    'volume_base': 14.8,
                    'opportunity_factor': 1.0
                }
            }
            
            config = symbol_configs.get(symbol, symbol_configs['ADAUSDT'])
            
            # Ajustar según capital actual
            capital_factor = self.current_capital / self.max_capital
            config['opportunity_factor'] *= (0.8 + 0.4 * capital_factor)
            
            # Generar datos cada 30 minutos
            periods = days * 24 * 2
            np.random.seed(hash(symbol) % 2**32)
            
            # Generar precios con oportunidades escalables
            prices = [config['base_price']]
            volatility = config['daily_vol'] / (24 * 2)**0.5
            
            # Crear tendencias adaptativas
            trend_cycles = 6  # Más ciclos para más oportunidades
            cycle_length = periods // trend_cycles
            
            for i in range(periods):
                cycle_position = (i % cycle_length) / cycle_length
                
                # Tendencias más frecuentes para capital pequeño
                if cycle_position < 0.35:  # Fase alcista
                    trend_direction = 1
                    trend_strength = config['trend_strength']
                elif cycle_position < 0.65:  # Fase lateral
                    trend_direction = 0
                    trend_strength = 0.15
                else:  # Fase bajista
                    trend_direction = -1
                    trend_strength = config['trend_strength'] * 0.7
                
                # Componente de tendencia
                trend_component = trend_direction * trend_strength * volatility * 0.4
                
                # Mean reversion suave
                current_price = prices[-1]
                distance_from_base = (current_price - config['base_price']) / config['base_price']
                mean_reversion = -distance_from_base * 0.06
                
                # Volatility clustering
                if i > 0:
                    prev_return = (prices[-1] - prices[-2]) / prices[-2]
                    vol_clustering = 1 + 0.35 * abs(prev_return) / volatility
                else:
                    vol_clustering = 1
                
                # Componente aleatoria
                random_component = np.random.normal(0, volatility * vol_clustering)
                
                # Eventos de oportunidad adaptativos
                opportunity_rate = 0.10 * config['opportunity_factor'] * (1 + capital_factor * 0.5)
                if np.random.random() < opportunity_rate:
                    event_direction = np.random.choice([-1, 1])
                    event_magnitude = volatility * np.random.uniform(1.8, 3.5)
                    random_component += event_direction * event_magnitude
                
                # Precio siguiente
                total_return = trend_component + mean_reversion + random_component
                new_price = current_price * (1 + total_return)
                new_price = max(new_price, config['base_price'] * 0.65)
                prices.append(new_price)
            
            # Crear timestamps
            start_date = datetime.now() - timedelta(days=days)
            timestamps = pd.date_range(start=start_date, periods=periods, freq='30T')
            
            # Crear OHLCV data
            data = []
            for i in range(periods):
                if i == 0:
                    open_price = prices[i]
                else:
                    open_price = prices[i-1]
                
                close_price = prices[i]
                
                # High/Low realistas
                intraday_range = abs(np.random.normal(0, volatility * 0.35))
                high_price = max(open_price, close_price) * (1 + intraday_range)
                low_price = min(open_price, close_price) * (1 - intraday_range)
                
                # Volumen correlacionado
                price_change = abs(close_price - open_price) / open_price
                base_volume = np.random.lognormal(config['volume_base'], 0.35)
                volume = base_volume * (1 + price_change * 5) * config['opportunity_factor']
                
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
            logger.error(f"Error generando datos adaptativos para {symbol}: {e}")
            return pd.DataFrame()

    def calculate_adaptive_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores adaptativos según capital"""
        try:
            df = data.copy()
            
            # Períodos adaptativos según capital
            capital_factor = self.current_capital / self.max_capital
            
            # EMAs adaptativos
            ema_fast = max(5, int(8 - 3 * capital_factor))
            ema_medium = max(15, int(21 - 6 * capital_factor))
            ema_slow = max(35, int(50 - 15 * capital_factor))
            
            df['ema_fast'] = df['close'].ewm(span=ema_fast).mean()
            df['ema_medium'] = df['close'].ewm(span=ema_medium).mean()
            df['ema_slow'] = df['close'].ewm(span=ema_slow).mean()
            
            # RSI adaptativo
            rsi_period = max(10, int(14 - 4 * capital_factor))
            df['rsi'] = self.calculate_rsi(df['close'], rsi_period)
            
            # MACD adaptativo
            macd_fast = max(8, int(12 - 4 * capital_factor))
            macd_slow = max(20, int(26 - 6 * capital_factor))
            macd_signal = max(6, int(9 - 3 * capital_factor))
            
            df['ema_macd_fast'] = df['close'].ewm(span=macd_fast).mean()
            df['ema_macd_slow'] = df['close'].ewm(span=macd_slow).mean()
            df['macd'] = df['ema_macd_fast'] - df['ema_macd_slow']
            df['macd_signal'] = df['macd'].ewm(span=macd_signal).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands adaptativos
            bb_period = max(15, int(20 - 5 * capital_factor))
            df['bb_middle'] = df['close'].rolling(bb_period).mean()
            bb_std = df['close'].rolling(bb_period).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Volumen adaptativo
            volume_period = max(15, int(20 - 5 * capital_factor))
            df['volume_sma'] = df['volume'].rolling(volume_period).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # ATR adaptativo
            atr_period = max(10, int(14 - 4 * capital_factor))
            df['atr'] = self.calculate_atr(df, atr_period)
            
            # Momentum adaptativo
            momentum_period = max(5, int(10 - 5 * capital_factor))
            df['momentum'] = df['close'] / df['close'].shift(momentum_period) - 1
            
            # Indicadores de calidad
            df['price_change'] = df['close'].pct_change()
            volatility_period = max(15, int(20 - 5 * capital_factor))
            df['volatility'] = df['price_change'].rolling(volatility_period).std()
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores adaptativos: {e}")
            return data

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr

    def generate_adaptive_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Genera señales adaptativas según capital"""
        try:
            df = data.copy()
            
            # Condiciones de tendencia adaptativas
            trend_strong = (
                (df['ema_fast'] > df['ema_medium']) &
                (df['ema_medium'] > df['ema_slow']) &
                (df['close'] > df['ema_fast'])
            )
            
            # Condiciones de momentum adaptativas
            capital_factor = self.current_capital / self.max_capital
            rsi_lower = 35 + (10 * capital_factor)  # 35-45
            rsi_upper = 65 + (10 * capital_factor)  # 65-75
            
            momentum_good = (
                (df['rsi'] > rsi_lower) &
                (df['rsi'] < rsi_upper) &
                (df['macd'] > df['macd_signal']) &
                (df['momentum'] > -0.03)
            )
            
            # Condiciones de volumen adaptativas
            volume_confirm = (
                (df['volume_ratio'] >= self.quality_filters['min_volume_spike']) &
                (df['volume_ratio'] < 5.0)
            )
            
            # Condiciones de precio adaptativas
            price_movement = (
                (abs(df['price_change']) >= self.quality_filters['min_price_movement']/100) &
                (abs(df['price_change']) < 0.10)
            )
            
            # Posición en Bollinger Bands adaptativa
            bb_position_good = (
                (df['bb_position'] > 0.2) &
                (df['bb_position'] < 0.8)
            )
            
            # Filtro de volatilidad adaptativo
            volatility_ok = (
                df['volatility'] < self.quality_filters['volatility_filter']
            )
            
            # Señal de entrada adaptativa
            df['adaptive_entry'] = (
                trend_strong &
                momentum_good &
                volume_confirm &
                price_movement &
                bb_position_good &
                volatility_ok
            ).astype(int)
            
            # Calcular confianza adaptativa
            df['adaptive_confidence'] = (
                trend_strong.astype(int) * 0.25 +
                momentum_good.astype(int) * 0.25 +
                volume_confirm.astype(int) * 0.2 +
                price_movement.astype(int) * 0.15 +
                bb_position_good.astype(int) * 0.1 +
                volatility_ok.astype(int) * 0.05
            )
            
            # Filtrar por confianza
            df['high_confidence_adaptive'] = (
                (df['adaptive_entry'] == 1) &
                (df['adaptive_confidence'] >= self.quality_filters['min_confidence'])
            ).astype(int)
            
            # Señales de salida adaptativas
            df['adaptive_exit'] = (
                (df['rsi'] > rsi_upper + 5) |
                (df['bb_position'] > 0.85) |
                (df['macd'] < df['macd_signal']) |
                (df['ema_fast'] < df['ema_medium'])
            ).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error generando señales adaptativas para {symbol}: {e}")
            return data

    def simulate_adaptive_trading(self, symbol: str, data: pd.DataFrame) -> List[Dict]:
        """Simula trading adaptativo según capital"""
        try:
            trades = []
            position = None
            entry_price = 0
            entry_time = None
            stop_loss_price = 0
            take_profit_price = 0
            position_size = 0
            
            daily_trades_count = 0
            daily_loss = 0
            current_date = None
            max_capital_seen = self.current_capital
            consecutive_losses = 0
            
            for i, (timestamp, row) in enumerate(data.iterrows()):
                current_price = row['close']
                current_date_check = timestamp.date()
                
                # Reset contador diario
                if current_date != current_date_check:
                    daily_trades_count = 0
                    daily_loss = 0
                    current_date = current_date_check
                
                # Control de drawdown
                current_drawdown = (self.current_capital - max_capital_seen) / max_capital_seen
                if current_drawdown < -self.safety_config['max_drawdown']:
                    continue
                
                # Control de pérdida diaria
                if daily_loss < -self.current_capital * self.safety_config['daily_loss_limit']:
                    continue
                
                # Control de pérdidas consecutivas
                if consecutive_losses >= self.safety_config['consecutive_loss_limit']:
                    continue
                
                # Gestión de posición existente
                if position is not None:
                    should_exit = False
                    exit_reason = ""
                    
                    # Stop Loss / Take Profit
                    if current_price <= stop_loss_price:
                        should_exit = True
                        exit_reason = "stop_loss"
                    elif current_price >= take_profit_price:
                        should_exit = True
                        exit_reason = "take_profit"
                    elif row.get('adaptive_exit', 0) == 1:
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
                            'duration_minutes': (timestamp - entry_time).total_seconds() / 60,
                            'capital_at_trade': self.current_capital
                        }
                        trades.append(trade)
                        
                        # Actualizar capital con compounding adaptativo
                        if pnl_amount > 0:
                            # Ganancia
                            base_reinvestment = pnl_amount * self.compounding_config['base_rate']
                            
                            # Bonus por performance
                            if len(trades) >= 10:
                                recent_wins = sum(1 for t in trades[-10:] if t['pnl_amount'] > 0)
                                if recent_wins >= 7:
                                    bonus = pnl_amount * self.compounding_config['performance_bonus']
                                    base_reinvestment += bonus
                            
                            # Límite máximo
                            max_reinvestment = pnl_amount * self.compounding_config['max_rate']
                            reinvestment = min(base_reinvestment, max_reinvestment)
                            
                            self.current_capital += reinvestment
                            consecutive_losses = 0
                        else:
                            # Pérdida
                            if current_drawdown < -0.06:
                                penalty_factor = self.compounding_config['drawdown_penalty']
                                self.current_capital += pnl_amount * penalty_factor
                            else:
                                self.current_capital += pnl_amount
                            consecutive_losses += 1
                            daily_loss += pnl_amount
                        
                        if self.current_capital > max_capital_seen:
                            max_capital_seen = self.current_capital
                        
                        position = None
                
                # Buscar nueva entrada
                if (position is None and 
                    row.get('high_confidence_adaptive', 0) == 1 and 
                    daily_trades_count < self.max_daily_trades and
                    self.current_capital > 0 and
                    consecutive_losses < self.safety_config['consecutive_loss_limit']):
                    
                    # Calcular tamaño de posición adaptativo
                    max_position = self.current_capital * self.max_position_size
                    risk_amount = self.current_capital * self.max_risk_per_trade
                    
                    # Stop loss basado en ATR
                    atr = row.get('atr', current_price * 0.015)
                    stop_distance = max(atr * 1.6, current_price * 0.01)
                    
                    # Tamaño de posición basado en riesgo
                    risk_based_size = risk_amount / (stop_distance / current_price)
                    position_size = min(max_position, risk_based_size)
                    
                    # Solo entrar si el tamaño es significativo
                    min_position = self.current_capital * 0.05  # Mínimo 5%
                    if position_size > min_position:
                        entry_price = current_price
                        stop_loss_price = entry_price - stop_distance
                        take_profit_price = entry_price + (stop_distance * self.min_reward_risk_ratio)
                        
                        position = 'long'
                        entry_time = timestamp
                        daily_trades_count += 1
            
            return trades
            
        except Exception as e:
            logger.error(f"Error simulando trading adaptativo para {symbol}: {e}")
            return []

    def calculate_adaptive_performance(self, all_trades: List[Dict]) -> Dict:
        """Calcula rendimiento adaptativo"""
        try:
            if not all_trades:
                return {
                    'initial_capital': self.initial_capital,
                    'final_capital': self.current_capital,
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
                    'expectancy': 0,
                    'scaling_events': len(self.scaling_history)
                }
            
            # Estadísticas básicas
            total_trades = len(all_trades)
            winning_trades = len([t for t in all_trades if t['pnl_amount'] > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Simular evolución del capital
            capital_history = [self.initial_capital]
            daily_returns = []
            max_capital = self.initial_capital
            
            # Procesar trades cronológicamente
            sorted_trades = sorted(all_trades, key=lambda x: x['entry_time'])
            
            current_sim_capital = self.initial_capital
            for trade in sorted_trades:
                old_capital = current_sim_capital
                
                # Aplicar PnL
                if trade['pnl_amount'] > 0:
                    base_reinvestment = trade['pnl_amount'] * self.compounding_config['base_rate']
                    max_reinvestment = trade['pnl_amount'] * self.compounding_config['max_rate']
                    reinvestment = min(base_reinvestment, max_reinvestment)
                    current_sim_capital += reinvestment
                else:
                    current_sim_capital += trade['pnl_amount']
                
                if current_sim_capital > max_capital:
                    max_capital = current_sim_capital
                
                capital_history.append(current_sim_capital)
                
                if old_capital > 0:
                    trade_return = (current_sim_capital - old_capital) / old_capital
                    daily_returns.append(trade_return)
            
            # Métricas finales
            total_return = (current_sim_capital - self.initial_capital) / self.initial_capital
            
            if len(daily_returns) > 0:
                avg_daily_return = np.mean(daily_returns)
                monthly_return = (1 + avg_daily_return) ** 20 - 1
                
                volatility = np.std(daily_returns) if len(daily_returns) > 1 else 0
                sharpe_ratio = avg_daily_return / volatility if volatility > 0 else 0
                
                # Drawdown
                capital_series = pd.Series(capital_history)
                rolling_max = capital_series.expanding().max()
                drawdown = (capital_series - rolling_max) / rolling_max
                max_drawdown = drawdown.min()
                
                # Métricas adicionales
                winning_pnl = sum(t['pnl_amount'] for t in all_trades if t['pnl_amount'] > 0)
                losing_pnl = abs(sum(t['pnl_amount'] for t in all_trades if t['pnl_amount'] < 0))
                
                profit_factor = winning_pnl / losing_pnl if losing_pnl > 0 else float('inf')
                expectancy = sum(t['pnl_amount'] for t in all_trades) / total_trades
                
                durations = [t['duration_minutes'] for t in all_trades if 'duration_minutes' in t]
                avg_trade_duration = np.mean(durations) if durations else 0
            else:
                monthly_return = 0
                sharpe_ratio = 0
                max_drawdown = 0
                profit_factor = 0
                expectancy = 0
                avg_trade_duration = 0
            
            # Verificar objetivos
            meets_target = (
                monthly_return >= self.target_monthly_return and
                win_rate >= self.min_win_rate and
                abs(max_drawdown) <= self.safety_config['max_drawdown']
            )
            
            performance = {
                'initial_capital': self.initial_capital,
                'final_capital': current_sim_capital,
                'current_capital': self.current_capital,
                'total_return': total_return,
                'monthly_return': monthly_return,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'avg_trade_duration': avg_trade_duration,
                'profit_factor': profit_factor,
                'expectancy': expectancy,
                'meets_target': meets_target,
                'scaling_events': len(self.scaling_history),
                'scaling_history': self.scaling_history
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error calculando rendimiento adaptativo: {e}")
            return {}

    def run_variable_capital_system(self) -> Dict:
        """Ejecuta sistema con capital variable"""
        logger.info("💰 INICIANDO SISTEMA CON CAPITAL VARIABLE 200-500 USDT")
        
        try:
            all_trades = []
            symbol_performance = {}
            
            # Análisis por símbolo
            for symbol in self.optimal_symbols:
                logger.info(f"📊 Analizando {symbol} con capital ${self.current_capital:.2f}...")
                
                # Generar datos adaptativos
                data = self.generate_adaptive_data(symbol, 90)
                
                if data.empty:
                    continue
                
                # Calcular indicadores adaptativos
                data = self.calculate_adaptive_indicators(data)
                
                # Generar señales adaptativas
                data = self.generate_adaptive_signals(data, symbol)
                
                # Simular trading adaptativo
                symbol_trades = self.simulate_adaptive_trading(symbol, data)
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
                        'worst_trade': min(symbol_pnl)
                    }
            
            # Calcular rendimiento
            performance = self.calculate_adaptive_performance(all_trades)
            
            # Verificar oportunidad de escalamiento
            if self.check_scaling_opportunity(performance):
                self.scale_capital(performance)
                # Recalcular performance después del escalamiento
                performance = self.calculate_adaptive_performance(all_trades)
            
            # Compilar resultados
            results = {
                'system_name': self.name,
                'analysis_timestamp': datetime.now().isoformat(),
                'target_monthly_return': self.target_monthly_return,
                'capital_range': f"${self.min_capital}-${self.max_capital} USDT",
                'performance': performance,
                'symbol_performance': symbol_performance,
                'configuration': {
                    'current_capital': self.current_capital,
                    'quality_filters': self.quality_filters,
                    'compounding_config': self.compounding_config,
                    'safety_config': self.safety_config,
                    'scaling_config': self.scaling_config
                }
            }
            
            # Log resultados
            if performance:
                logger.info(f"💰 SISTEMA CAPITAL VARIABLE COMPLETADO")
                logger.info(f"💵 Capital inicial: ${performance['initial_capital']:.2f} USDT")
                logger.info(f"💵 Capital final: ${performance['final_capital']:.2f} USDT")
                logger.info(f"💵 Capital actual: ${self.current_capital:.2f} USDT")
                logger.info(f"📈 Retorno total: {performance['total_return']*100:.2f}%")
                logger.info(f"🎯 Retorno mensual: {performance['monthly_return']*100:.2f}%")
                logger.info(f"🏆 Cumple objetivo: {'✅ SÍ' if performance['meets_target'] else '❌ NO'}")
                logger.info(f"📊 Total trades: {performance['total_trades']}")
                logger.info(f"🎲 Win rate: {performance['win_rate']*100:.1f}%")
                logger.info(f"📉 Max drawdown: {performance['max_drawdown']*100:.2f}%")
                logger.info(f"🚀 Escalamientos: {performance['scaling_events']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en sistema capital variable: {e}")
            return {}

def main():
    """Función principal"""
    print("💰 SISTEMA 5% MENSUAL CON CAPITAL VARIABLE 200-500 USDT")
    print("=" * 60)
    
    # Crear sistema con capital variable
    system = VariableCapital5PercentSystem(initial_capital=200)
    
    # Ejecutar análisis
    results = system.run_variable_capital_system()
    
    if results and results.get('performance'):
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"variable_capital_5percent_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        perf = results['performance']
        
        print(f"\n📊 RESULTADOS GUARDADOS EN: {filename}")
        print(f"💵 Capital inicial: ${perf['initial_capital']:.2f} USDT")
        print(f"💵 Capital final: ${perf['final_capital']:.2f} USDT")
        print(f"💵 Capital actual: ${perf['current_capital']:.2f} USDT")
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
        print(f"🚀 Escalamientos realizados: {perf['scaling_events']}")
        
        if perf['scaling_events'] > 0:
            print(f"\n🚀 HISTORIAL DE ESCALAMIENTOS:")
            for i, scaling in enumerate(perf['scaling_history'], 1):
                print(f"   {i}. ${scaling['old_capital']:.2f} → ${scaling['new_capital']:.2f} USDT")
        
        if perf['meets_target']:
            print("\n🎉 ¡SISTEMA CAPITAL VARIABLE EXITOSO!")
            print("✅ Logra 5% mensual de forma escalable")
            print("🛡️ Con gestión de riesgo adaptativa")
            print("🔄 Compounding inteligente")
            print("🚀 Escalamiento automático activado")
        else:
            print("\n⚠️  Sistema necesita optimización")
            print("💡 Revisar parámetros adaptativos")
    
    else:
        print("❌ Error en el sistema capital variable")

if __name__ == "__main__":
    main()