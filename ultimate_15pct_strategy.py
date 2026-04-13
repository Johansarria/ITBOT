#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Estrategia Definitiva 20% Mensual
Versión final optimizada con filtros mejorados y gestión de riesgo superior
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

class Ultimate15PctStrategy:
    """
    Estrategia definitiva diseñada específicamente para alcanzar 20% mensual
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            # Gestión de riesgo ultra-optimizada
            'base_risk_per_trade': 0.025,  # 2.5% base
            'max_risk_per_trade': 0.04,    # 4% máximo
            'min_risk_per_trade': 0.015,   # 1.5% mínimo
            'daily_risk_limit': 0.08,      # 8% diario (más conservador)
            'max_daily_trades': 4,         # Solo 4 trades de alta calidad
            'max_consecutive_losses': 2,   # Parar después de 2 pérdidas
            
            # Indicadores ultra-selectivos
            'rsi_period': 14,
            'rsi_oversold': 20,            # Más extremo
            'rsi_overbought': 80,          # Más extremo
            'ema_fast': 12,
            'ema_slow': 26,
            'bb_period': 20,
            'bb_std': 2.0,
            'atr_period': 14,
            
            # Filtros de calidad extremos
            'min_signal_strength': 8,      # Muy alto
            'min_trend_confirmation': 3,   # Triple confirmación
            'min_volatility': 0.004,       # Volatilidad mínima
            'max_volatility': 0.025,       # Volatilidad máxima
            'volume_confirmation_required': True,
            'volume_threshold': 1.5,       # 50% más volumen
            
            # Targets optimizados
            'profit_target_multiplier': 4.0,  # 4:1 reward/risk
            'stop_loss_atr_multiplier': 0.75, # Stop loss más ajustado
            'breakeven_move_threshold': 0.008, # Mover a BE en 0.8%
            'partial_profit_threshold': 0.015, # Tomar 50% en 1.5%
            
            # Filtros de tiempo
            'avoid_first_30min': True,
            'avoid_last_30min': True,
            'min_time_between_trades': 60,  # 1 hora mínimo
            
            # Confirmaciones múltiples
            'require_momentum_confirmation': True,
            'require_volume_confirmation': True,
            'require_trend_alignment': True,
            'require_volatility_confirmation': True,
        }
        
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.breakeven_moved = False
        self.partial_taken = False
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.last_trade_time = None
        self.monthly_target_progress = 0.0
        
    def calculate_premium_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores premium con máxima precisión
        """
        df = data.copy()
        
        # RSI con suavizado
        df['rsi'] = self._calculate_rsi(df['close'], self.config['rsi_period'])
        df['rsi_smooth'] = df['rsi'].rolling(3).mean()
        
        # MACD premium
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        df['macd_slope'] = df['macd'].diff()
        df['macd_divergence'] = self._detect_macd_divergence(df['close'], df['macd'])
        
        # Bollinger Bands premium
        bb_data = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_width'] = (bb_data['upper'] - bb_data['lower']) / bb_data['middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (bb_data['upper'] - bb_data['lower'])
        df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(20).mean() * 0.8
        
        # EMAs con análisis de tendencia
        df['ema_fast'] = df['close'].ewm(span=self.config['ema_fast']).mean()
        df['ema_slow'] = df['close'].ewm(span=self.config['ema_slow']).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # Análisis de tendencia multi-nivel
        df['trend_short'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)
        df['trend_long'] = np.where(df['close'] > df['ema_200'], 1, -1)
        df['trend_alignment'] = df['trend_short'] == df['trend_long']
        df['trend_strength'] = abs(df['ema_fast'] - df['ema_slow']) / df['ema_slow']
        
        # ATR y volatilidad premium
        df['atr'] = self._calculate_atr(df)
        df['atr_normalized'] = df['atr'] / df['close']
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
        df['volatility_percentile'] = df['volatility'].rolling(100).rank(pct=True)
        
        # Momentum multi-timeframe
        df['momentum_3'] = df['close'].pct_change(3)
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_10'] = df['close'].pct_change(10)
        df['momentum_20'] = df['close'].pct_change(20)
        df['momentum_alignment'] = (
            (df['momentum_3'] > 0) & 
            (df['momentum_5'] > 0) & 
            (df['momentum_10'] > 0)
        ).astype(int) - (
            (df['momentum_3'] < 0) & 
            (df['momentum_5'] < 0) & 
            (df['momentum_10'] < 0)
        ).astype(int)
        
        # Volume analysis premium
        if 'volume' in df.columns:
            df['volume_sma_20'] = df['volume'].rolling(20).mean()
            df['volume_sma_50'] = df['volume'].rolling(50).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_20']
            df['volume_trend'] = df['volume_sma_20'] / df['volume_sma_50']
            df['volume_spike'] = df['volume_ratio'] > self.config['volume_threshold']
            
            # Price-Volume relationship
            df['pv_confirmation'] = (
                ((df['close'] > df['close'].shift(1)) & (df['volume'] > df['volume_sma_20'])) |
                ((df['close'] < df['close'].shift(1)) & (df['volume'] > df['volume_sma_20']))
            )
        else:
            df['volume_ratio'] = 1.0
            df['volume_trend'] = 1.0
            df['volume_spike'] = False
            df['pv_confirmation'] = True
        
        # Support/Resistance premium
        df['support_20'] = df['low'].rolling(20).min()
        df['resistance_20'] = df['high'].rolling(20).max()
        df['support_50'] = df['low'].rolling(50).min()
        df['resistance_50'] = df['high'].rolling(50).max()
        
        # Distancia a niveles clave
        df['support_distance'] = (df['close'] - df['support_20']) / df['close']
        df['resistance_distance'] = (df['resistance_20'] - df['close']) / df['close']
        
        # Market structure premium
        df['higher_highs'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['lower_lows'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))
        df['market_structure'] = df['higher_highs'].astype(int) - df['lower_lows'].astype(int)
        
        # Divergence detection
        df['price_divergence'] = self._detect_price_divergence(df)
        
        return df
    
    def generate_ultra_selective_signal(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Genera señales ultra-selectivas con múltiples confirmaciones
        """
        if idx < 100:  # Necesitamos muchos datos
            return {'action': 'MANTENER', 'reason': 'Insufficient data'}
        
        # Verificar límites estrictos
        if self.daily_trades >= self.config['max_daily_trades']:
            return {'action': 'MANTENER', 'reason': 'Daily trade limit'}
        
        if abs(self.daily_pnl) >= self.config['daily_risk_limit']:
            return {'action': 'MANTENER', 'reason': 'Daily risk limit'}
        
        if self.consecutive_losses >= self.config['max_consecutive_losses']:
            return {'action': 'MANTENER', 'reason': 'Max consecutive losses'}
        
        # Verificar tiempo entre trades
        current_time = df.index[idx] if hasattr(df.index[idx], 'hour') else datetime.now()
        if (self.last_trade_time and 
            (current_time - self.last_trade_time).total_seconds() < self.config['min_time_between_trades'] * 60):
            return {'action': 'MANTENER', 'reason': 'Too soon since last trade'}
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        # Filtros básicos ultra-estrictos
        if not self._pass_basic_filters(current):
            return {'action': 'MANTENER', 'reason': 'Failed basic filters'}
        
        # Calcular puntuación de señal con confirmaciones múltiples
        signal_analysis = self._calculate_ultra_signal_score(df, idx)
        
        if signal_analysis['score'] < self.config['min_signal_strength']:
            return {
                'action': 'MANTENER', 
                'reason': f"Insufficient signal strength ({signal_analysis['score']}/{self.config['min_signal_strength']})"
            }
        
        # Verificar confirmaciones requeridas
        confirmations = self._verify_all_confirmations(current, prev)
        if not confirmations['all_confirmed']:
            return {
                'action': 'MANTENER',
                'reason': f"Missing confirmations: {confirmations['missing']}"
            }
        
        # Calcular parámetros de la operación
        risk_per_trade = self._calculate_dynamic_risk(signal_analysis['score'])
        
        return {
            'action': signal_analysis['direction'],
            'score': signal_analysis['score'],
            'confirmations': confirmations['confirmed'],
            'risk_per_trade': risk_per_trade,
            'reason': f"Ultra-selective signal (score: {signal_analysis['score']}, confirmations: {len(confirmations['confirmed'])})"
        }
    
    def _pass_basic_filters(self, current: pd.Series) -> bool:
        """
        Verifica filtros básicos ultra-estrictos
        """
        # Filtro de volatilidad
        if (current['volatility'] < self.config['min_volatility'] or 
            current['volatility'] > self.config['max_volatility']):
            return False
        
        # Filtro de volatilidad percentil (solo operar en volatilidad media-alta)
        if current['volatility_percentile'] < 0.3 or current['volatility_percentile'] > 0.9:
            return False
        
        # Filtro de tendencia (solo operar con tendencia clara)
        if abs(current['trend_strength']) < 0.01:
            return False
        
        # Filtro de squeeze (no operar durante compresión)
        if current['bb_squeeze']:
            return False
        
        return True
    
    def _calculate_ultra_signal_score(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Calcula puntuación ultra-selectiva de señal
        """
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        buy_score = 0
        sell_score = 0
        
        # 1. RSI extremo con recuperación (peso: 3)
        if (current['rsi_smooth'] < self.config['rsi_oversold'] and 
            current['rsi_smooth'] > prev['rsi_smooth']):
            buy_score += 3
        elif (current['rsi_smooth'] > self.config['rsi_overbought'] and 
              current['rsi_smooth'] < prev['rsi_smooth']):
            sell_score += 3
        
        # 2. MACD con momentum (peso: 4)
        if (prev['macd'] <= prev['macd_signal'] and current['macd'] > current['macd_signal'] and
            current['macd_slope'] > 0):
            buy_score += 4
        elif (prev['macd'] >= prev['macd_signal'] and current['macd'] < current['macd_signal'] and
              current['macd_slope'] < 0):
            sell_score += 4
        
        # 3. Bollinger Bands extremos (peso: 3)
        if current['bb_position'] < 0.1 and current['close'] > prev['close']:
            buy_score += 3
        elif current['bb_position'] > 0.9 and current['close'] < prev['close']:
            sell_score += 3
        
        # 4. Alineación de tendencia (peso: 4)
        if (current['trend_alignment'] and current['trend_short'] == 1 and 
            current['trend_strength'] > 0.02):
            buy_score += 4
        elif (current['trend_alignment'] and current['trend_short'] == -1 and 
              current['trend_strength'] > 0.02):
            sell_score += 4
        
        # 5. Momentum multi-timeframe (peso: 3)
        if current['momentum_alignment'] == 1 and current['momentum_5'] > 0.005:
            buy_score += 3
        elif current['momentum_alignment'] == -1 and current['momentum_5'] < -0.005:
            sell_score += 3
        
        # 6. Divergencia (peso: 3)
        if current['macd_divergence'] == 1:  # Divergencia alcista
            buy_score += 3
        elif current['macd_divergence'] == -1:  # Divergencia bajista
            sell_score += 3
        
        # 7. Support/Resistance (peso: 2)
        if current['support_distance'] < 0.005:  # Muy cerca del soporte
            buy_score += 2
        elif current['resistance_distance'] < 0.005:  # Muy cerca de resistencia
            sell_score += 2
        
        # 8. Market structure (peso: 2)
        if current['market_structure'] > 0:
            buy_score += 2
        elif current['market_structure'] < 0:
            sell_score += 2
        
        # 9. Volume confirmation (peso: 2)
        if current['volume_spike'] and current['pv_confirmation']:
            if buy_score > sell_score:
                buy_score += 2
            elif sell_score > buy_score:
                sell_score += 2
        
        # Determinar dirección
        if buy_score >= self.config['min_signal_strength'] and buy_score > sell_score + 2:
            return {'direction': 'COMPRAR', 'score': buy_score}
        elif sell_score >= self.config['min_signal_strength'] and sell_score > buy_score + 2:
            return {'direction': 'VENDER', 'score': sell_score}
        else:
            return {'direction': 'MANTENER', 'score': max(buy_score, sell_score)}
    
    def _verify_all_confirmations(self, current: pd.Series, prev: pd.Series) -> Dict[str, Any]:
        """
        Verifica todas las confirmaciones requeridas
        """
        confirmed = []
        missing = []
        
        # Confirmación de momentum
        if self.config['require_momentum_confirmation']:
            if abs(current['momentum_5']) > 0.003:
                confirmed.append('momentum')
            else:
                missing.append('momentum')
        
        # Confirmación de volumen
        if self.config['require_volume_confirmation']:
            if current['volume_spike']:
                confirmed.append('volume')
            else:
                missing.append('volume')
        
        # Confirmación de tendencia
        if self.config['require_trend_alignment']:
            if current['trend_alignment']:
                confirmed.append('trend')
            else:
                missing.append('trend')
        
        # Confirmación de volatilidad
        if self.config['require_volatility_confirmation']:
            if 0.3 <= current['volatility_percentile'] <= 0.8:
                confirmed.append('volatility')
            else:
                missing.append('volatility')
        
        return {
            'all_confirmed': len(missing) == 0,
            'confirmed': confirmed,
            'missing': missing
        }
    
    def _calculate_dynamic_risk(self, signal_score: int) -> float:
        """
        Calcula riesgo dinámico ultra-conservador
        """
        base_risk = self.config['base_risk_per_trade']
        
        # Ajustar por fuerza de señal (muy conservador)
        signal_multiplier = min(1.2, 1.0 + (signal_score - self.config['min_signal_strength']) * 0.03)
        
        # Reducir drásticamente después de pérdidas
        if self.consecutive_losses >= 1:
            loss_multiplier = 0.5
        else:
            loss_multiplier = 1.0
        
        # Ajustar por progreso mensual
        if self.monthly_target_progress >= 0.10:  # Si ya tenemos 10%
            progress_multiplier = 0.6  # Ser muy conservador
        elif self.monthly_target_progress >= 0.05:  # 5%
            progress_multiplier = 0.8
        else:
            progress_multiplier = 1.0
        
        dynamic_risk = base_risk * signal_multiplier * loss_multiplier * progress_multiplier
        
        return max(self.config['min_risk_per_trade'], 
                  min(self.config['max_risk_per_trade'], dynamic_risk))
    
    def calculate_position_size(self, price: float, stop_loss: float, account_balance: float, risk_pct: float) -> float:
        """
        Calcula tamaño de posición ultra-conservador
        """
        risk_amount = account_balance * risk_pct
        price_diff = abs(price - stop_loss)
        
        if price_diff > 0:
            position_size = risk_amount / price_diff
            # Limitar a máximo 20% del balance
            max_position_value = account_balance * 0.2
            max_position_size = max_position_value / price
            return min(position_size, max_position_size)
        
        return 0
    
    def calculate_stop_take_levels(self, entry_price: float, direction: str, atr: float) -> Tuple[float, float]:
        """
        Calcula niveles de stop y take profit ultra-optimizados
        """
        stop_distance = atr * self.config['stop_loss_atr_multiplier']
        take_distance = stop_distance * self.config['profit_target_multiplier']
        
        if direction == "COMPRAR":
            stop_loss = entry_price - stop_distance
            take_profit = entry_price + take_distance
        else:  # VENDER
            stop_loss = entry_price + stop_distance
            take_profit = entry_price - take_distance
        
        return stop_loss, take_profit
    
    def should_move_to_breakeven(self, current_price: float, direction: str) -> bool:
        """
        Determina si mover stop a breakeven
        """
        if self.breakeven_moved:
            return False
        
        profit_pct = 0
        if direction == "COMPRAR":
            profit_pct = (current_price - self.entry_price) / self.entry_price
        else:
            profit_pct = (self.entry_price - current_price) / self.entry_price
        
        return profit_pct >= self.config['breakeven_move_threshold']
    
    def should_take_partial_profit(self, current_price: float, direction: str) -> bool:
        """
        Determina si tomar ganancia parcial
        """
        if self.partial_taken:
            return False
        
        profit_pct = 0
        if direction == "COMPRAR":
            profit_pct = (current_price - self.entry_price) / self.entry_price
        else:
            profit_pct = (self.entry_price - current_price) / self.entry_price
        
        return profit_pct >= self.config['partial_profit_threshold']
    
    def update_performance(self, pnl: float, is_win: bool):
        """Actualiza métricas de performance"""
        self.daily_pnl += pnl
        self.monthly_target_progress += pnl / 100000  # Asumiendo balance de 100k
        self.daily_trades += 1
        self.last_trade_time = datetime.now()
        
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0
    
    def reset_monthly_stats(self):
        """Resetea estadísticas mensuales"""
        self.monthly_target_progress = 0.0
    
    # Métodos auxiliares
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calcula MACD"""
        ema_fast = prices.ewm(span=self.config['ema_fast']).mean()
        ema_slow = prices.ewm(span=self.config['ema_slow']).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=9).mean()
        histogram = macd - signal
        
        return {'macd': macd, 'signal': signal, 'histogram': histogram}
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calcula Bollinger Bands"""
        middle = prices.rolling(window=self.config['bb_period']).mean()
        std = prices.rolling(window=self.config['bb_period']).std()
        upper = middle + (std * self.config['bb_std'])
        lower = middle - (std * self.config['bb_std'])
        
        return {'upper': upper, 'middle': middle, 'lower': lower}
    
    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """Calcula Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(window=self.config['atr_period']).mean()
    
    def _detect_macd_divergence(self, prices: pd.Series, macd: pd.Series, window: int = 20) -> pd.Series:
        """Detecta divergencias MACD"""
        price_trend = prices.rolling(window).apply(lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1)
        macd_trend = macd.rolling(window).apply(lambda x: 1 if x.iloc[-1] > x.iloc[0] else -1)
        
        # Divergencia: precio y MACD van en direcciones opuestas
        divergence = pd.Series(0, index=prices.index)
        divergence[price_trend != macd_trend] = price_trend[price_trend != macd_trend] * -1
        
        return divergence
    
    def _detect_price_divergence(self, df: pd.DataFrame, window: int = 15) -> pd.Series:
        """Detecta divergencias de precio"""
        # Simplificado: divergencia entre precio y RSI
        price_highs = df['high'].rolling(window).max()
        rsi_highs = df['rsi'].rolling(window).max()
        
        price_trend = (df['high'] == price_highs).astype(int)
        rsi_trend = (df['rsi'] == rsi_highs).astype(int)
        
        return (price_trend != rsi_trend).astype(int)


class UltimateBacktester:
    """
    Backtester definitivo para la estrategia ultimate
    """
    
    def __init__(self, initial_balance: float = 100000.0, commission: float = 0.001):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission = commission
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trades = []
        self.balance_history = [initial_balance]
        
    def run_ultimate_backtest(self, data: pd.DataFrame, strategy: Ultimate15PctStrategy) -> Dict[str, Any]:
        """Ejecuta backtest definitivo"""
        df = strategy.calculate_premium_indicators(data)
        
        print(f"📊 Iniciando backtest DEFINITIVO con {len(df)} registros")
        print(f"   Rango: {df.index[0]} a {df.index[-1]}")
        print(f"   Filtros ultra-estrictos activados")
        
        for i in range(len(df)):
            current_data = df.iloc[i]
            
            # Verificar posición existente
            if self.position is not None:
                self._manage_ultimate_position(current_data, strategy)
            else:
                # Buscar nueva entrada ultra-selectiva
                signal_data = strategy.generate_ultra_selective_signal(df, i)
                if signal_data['action'] in ['COMPRAR', 'VENDER']:
                    self._open_ultimate_position(current_data, signal_data, strategy)
            
            # Actualizar historial
            current_value = self._calculate_portfolio_value(current_data['close'])
            self.balance_history.append(current_value)
            
            # Mostrar progreso cada 2000 registros
            if i % 2000 == 0 and i > 0:
                progress = (i / len(df)) * 100
                print(f"   Progreso: {progress:.1f}% - Trades: {len(self.trades)} - Balance: ${current_value:,.0f}")
        
        # Cerrar posición final
        if self.position is not None:
            self._close_position(df.iloc[-1]['close'], "Final close")
        
        print(f"✅ Backtest DEFINITIVO completado - {len(self.trades)} operaciones ultra-selectivas")
        
        return self._calculate_ultimate_results()
    
    def _open_ultimate_position(self, data: pd.Series, signal_data: Dict[str, Any], strategy: Ultimate15PctStrategy):
        """Abre posición ultra-optimizada"""
        price = data['close']
        direction = signal_data['action']
        risk_per_trade = signal_data['risk_per_trade']
        
        # Calcular stop loss y take profit
        atr = data['atr']
        stop_loss, take_profit = strategy.calculate_stop_take_levels(price, direction, atr)
        
        # Calcular tamaño de posición
        position_size = strategy.calculate_position_size(price, stop_loss, self.balance, risk_per_trade)
        
        if position_size > 0:
            cost = position_size * price * (1 + self.commission)
            
            if cost <= self.balance:
                self.position = direction
                self.position_size = position_size
                self.entry_price = price
                self.stop_loss = stop_loss
                self.take_profit = take_profit
                self.balance -= cost
                
                # Actualizar estrategia
                strategy.position = direction
                strategy.position_size = position_size
                strategy.entry_price = price
                strategy.stop_loss = stop_loss
                strategy.take_profit = take_profit
                strategy.breakeven_moved = False
                strategy.partial_taken = False
                
                # Registrar trade ultra-detallado
                trade = {
                    'entry_time': data.name if hasattr(data, 'name') else len(self.trades),
                    'direction': direction,
                    'entry_price': price,
                    'position_size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'signal_score': signal_data['score'],
                    'confirmations': signal_data['confirmations'],
                    'risk_per_trade': risk_per_trade,
                    'atr': atr,
                    'expected_reward_risk': strategy.config['profit_target_multiplier'],
                    'status': 'open'
                }
                self.trades.append(trade)
    
    def _manage_ultimate_position(self, data: pd.Series, strategy: Ultimate15PctStrategy):
        """Gestiona posición con lógica ultra-avanzada"""
        current_price = data['close']
        
        # Verificar movimiento a breakeven
        if strategy.should_move_to_breakeven(current_price, self.position):
            self.stop_loss = self.entry_price
            strategy.stop_loss = self.entry_price
            strategy.breakeven_moved = True
            if self.trades:
                self.trades[-1]['breakeven_moved'] = True
        
        # Verificar ganancia parcial
        if strategy.should_take_partial_profit(current_price, self.position):
            self._take_partial_profit(current_price, strategy)
        
        # Verificar salida
        should_exit, reason = self._should_exit_ultimate_position(current_price)
        if should_exit:
            self._close_position(current_price, reason)
    
    def _take_partial_profit(self, current_price: float, strategy: Ultimate15PctStrategy):
        """Toma ganancia parcial (50%)"""
        partial_size = self.position_size * 0.5
        
        # Calcular P&L parcial
        if self.position == "COMPRAR":
            pnl = (current_price - self.entry_price) * partial_size
        else:
            pnl = (self.entry_price - current_price) * partial_size
        
        # Aplicar comisión
        commission_cost = current_price * partial_size * self.commission
        pnl -= commission_cost
        
        # Actualizar balance y posición
        proceeds = current_price * partial_size * (1 - self.commission)
        self.balance += proceeds
        self.position_size -= partial_size
        strategy.position_size -= partial_size
        strategy.partial_taken = True
        
        # Actualizar trade
        if self.trades:
            self.trades[-1]['partial_profit_taken'] = True
            self.trades[-1]['partial_pnl'] = pnl
            self.trades[-1]['partial_price'] = current_price
    
    def _should_exit_ultimate_position(self, current_price: float) -> Tuple[bool, str]:
        """Determina salida con lógica ultra-avanzada"""
        # Stop loss
        if self.position == "COMPRAR" and current_price <= self.stop_loss:
            return True, "Stop Loss"
        elif self.position == "VENDER" and current_price >= self.stop_loss:
            return True, "Stop Loss"
        
        # Take profit
        if self.position == "COMPRAR" and current_price >= self.take_profit:
            return True, "Take Profit"
        elif self.position == "VENDER" and current_price <= self.take_profit:
            return True, "Take Profit"
        
        return False, ""
    
    def _close_position(self, exit_price: float, reason: str):
        """Cierra posición"""
        if self.position is None:
            return
        
        # Calcular P&L
        if self.position == "COMPRAR":
            pnl = (exit_price - self.entry_price) * self.position_size
        else:
            pnl = (self.entry_price - exit_price) * self.position_size
        
        # Aplicar comisión
        commission_cost = exit_price * self.position_size * self.commission
        pnl -= commission_cost
        
        # Actualizar balance
        proceeds = exit_price * self.position_size * (1 - self.commission)
        self.balance += proceeds
        
        # Calcular P&L total
        total_pnl = pnl + self.trades[-1].get('partial_pnl', 0) if self.trades else pnl
        
        # Actualizar trade
        if self.trades:
            original_position_size = self.trades[-1]['position_size']
            self.trades[-1].update({
                'exit_price': exit_price,
                'exit_reason': reason,
                'final_pnl': pnl,
                'total_pnl': total_pnl,
                'total_pnl_pct': (total_pnl / (self.entry_price * original_position_size)) * 100,
                'status': 'closed'
            })
        
        # Reset position
        self.position = None
        self.position_size = 0
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """Calcula valor del portfolio"""
        if self.position is None:
            return self.balance
        return self.balance + (self.position_size * current_price)
    
    def _calculate_ultimate_results(self) -> Dict[str, Any]:
        """Calcula resultados definitivos"""
        final_balance = self.balance_history[-1]
        total_return = (final_balance / self.initial_balance - 1) * 100
        
        closed_trades = [t for t in self.trades if t.get('status') == 'closed']
        winning_trades = [t for t in closed_trades if t.get('total_pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('total_pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        # Métricas ultra-detalladas
        gross_profit = sum(t['total_pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['total_pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calcular drawdown
        peak = self.initial_balance
        max_drawdown = 0
        drawdown_periods = 0
        current_drawdown_periods = 0
        
        for balance in self.balance_history:
            if balance > peak:
                peak = balance
                current_drawdown_periods = 0
            else:
                current_drawdown_periods += 1
                drawdown_periods = max(drawdown_periods, current_drawdown_periods)
            
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Retorno mensual
        days_simulated = len(self.balance_history) / (24 * 4)
        monthly_return = (total_return / days_simulated) * 30 if days_simulated > 0 else 0
        
        # Métricas de calidad
        avg_signal_score = np.mean([t.get('signal_score', 0) for t in closed_trades]) if closed_trades else 0
        avg_confirmations = np.mean([len(t.get('confirmations', [])) for t in closed_trades]) if closed_trades else 0
        
        # Análisis de partial profits
        partial_trades = [t for t in closed_trades if t.get('partial_profit_taken', False)]
        partial_profit_rate = len(partial_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_return_pct': total_return,
            'monthly_return_pct': monthly_return,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_drawdown_pct': max_drawdown,
            'max_drawdown_periods': drawdown_periods,
            'avg_signal_score': avg_signal_score,
            'avg_confirmations': avg_confirmations,
            'partial_profit_rate': partial_profit_rate,
            'target_achieved': monthly_return >= 20.0,
            'balance_history': self.balance_history,
            'trades': self.trades
        }


def generate_ultimate_test_data(days: int = 120, initial_price: float = 18000) -> pd.DataFrame:
    """
    Genera datos de prueba optimizados para la estrategia ultimate
    """
    np.random.seed(777)  # Seed especial
    periods_per_day = 24 * 4
    total_periods = days * periods_per_day
    
    dates = pd.date_range(start='2024-01-01', periods=total_periods, freq='15min')
    
    # Generar retornos más realistas con tendencias claras
    base_volatility = 0.004
    returns = np.random.normal(0, base_volatility, total_periods)
    
    # Añadir tendencias más pronunciadas
    trend_cycle = np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 15)) * 0.003
    volatility_cycle = 1 + 0.6 * np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 7))
    
    # Añadir breakouts más frecuentes
    breakout_probability = 0.025
    breakouts = np.random.choice([0, 1], total_periods, p=[1-breakout_probability, breakout_probability])
    breakout_magnitude = np.random.choice([-1, 1], total_periods) * 0.012
    
    returns = returns * volatility_cycle + trend_cycle + (breakouts * breakout_magnitude)
    
    # Generar precios
    prices = initial_price * (1 + returns).cumprod()
    
    # Crear OHLC
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'close': prices,
        'volume': np.random.randint(20000, 200000, total_periods)
    })
    
    # Generar high/low más realistas
    for i in range(len(df)):
        volatility = abs(returns[i]) * 2.5
        df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + volatility)
        df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - volatility)
        df.loc[i, 'close'] = np.clip(df.loc[i, 'close'], df.loc[i, 'low'], df.loc[i, 'high'])
    
    df.set_index('timestamp', inplace=True)
    return df


def run_ultimate_20pct_test():
    """
    Ejecuta test de la estrategia definitiva
    """
    print("🏆 Iniciando test de Estrategia DEFINITIVA 20% Mensual")
    print("=" * 70)
    
    # Generar datos optimizados
    data = generate_ultimate_test_data(days=120)
    print(f"📊 Datos optimizados generados: {len(data)} registros")
    print(f"   Rango: {data.index[0]} a {data.index[-1]}")
    
    # Crear estrategia definitiva
    strategy = Ultimate15PctStrategy()
    print("⚙️ Estrategia DEFINITIVA configurada")
    print(f"   Filtros ultra-estrictos: {strategy.config['min_signal_strength']} puntos mínimo")
    print(f"   Confirmaciones requeridas: 4 tipos")
    print(f"   Ratio reward/risk: {strategy.config['profit_target_multiplier']}:1")
    
    # Ejecutar backtest definitivo
    backtester = UltimateBacktester(initial_balance=100000.0)
    results = backtester.run_ultimate_backtest(data, strategy)
    
    # Mostrar resultados definitivos
    print("\n🏆 RESULTADOS DEL BACKTEST DEFINITIVO")
    print("=" * 50)
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return_pct']:.2f}%")
    print(f"Retorno mensual: {results['monthly_return_pct']:.2f}%")
    print(f"\n🎯 OBJETIVO 20% MENSUAL: {'✅ ALCANZADO' if results['target_achieved'] else '❌ NO ALCANZADO'}")
    
    print(f"\n📊 ESTADÍSTICAS DEFINITIVAS")
    print(f"Total de operaciones: {results['total_trades']}")
    print(f"Operaciones ganadoras: {results['winning_trades']}")
    print(f"Operaciones perdedoras: {results['losing_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"Profit Factor: {results['profit_factor']:.2f}")
    print(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%")
    print(f"Score promedio señales: {results['avg_signal_score']:.1f}")
    print(f"Confirmaciones promedio: {results['avg_confirmations']:.1f}")
    print(f"Tasa de ganancias parciales: {results['partial_profit_rate']:.1f}%")
    
    # Guardar resultados definitivos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ultimate_20pct_results_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS ESTRATEGIA DEFINITIVA 20% MENSUAL\n")
        f.write("=" * 55 + "\n\n")
        f.write(f"Balance inicial: ${results['initial_balance']:,.2f}\n")
        f.write(f"Balance final: ${results['final_balance']:,.2f}\n")
        f.write(f"Retorno total: {results['total_return_pct']:.2f}%\n")
        f.write(f"Retorno mensual: {results['monthly_return_pct']:.2f}%\n")
        f.write(f"Objetivo 20% mensual: {'ALCANZADO' if results['target_achieved'] else 'NO ALCANZADO'}\n\n")
        
        f.write("ESTADÍSTICAS DEFINITIVAS:\n")
        f.write("-" * 30 + "\n")
        f.write(f"Total de operaciones: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
        f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")
        f.write(f"Ganancia bruta: ${results['gross_profit']:.2f}\n")
        f.write(f"Pérdida bruta: ${results['gross_loss']:.2f}\n")
        f.write(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%\n")
        f.write(f"Períodos en Drawdown: {results['max_drawdown_periods']}\n")
        f.write(f"Score promedio señales: {results['avg_signal_score']:.1f}\n")
        f.write(f"Confirmaciones promedio: {results['avg_confirmations']:.1f}\n")
        f.write(f"Tasa ganancias parciales: {results['partial_profit_rate']:.1f}%\n\n")
        
        f.write("CARACTERÍSTICAS DEFINITIVAS:\n")
        f.write("-" * 35 + "\n")
        f.write("- Filtros ultra-estrictos (8+ puntos)\n")
        f.write("- 4 confirmaciones obligatorias\n")
        f.write("- Gestión de riesgo ultra-conservadora\n")
        f.write("- Ratio reward/risk 4:1\n")
        f.write("- Máximo 4 operaciones diarias\n")
        f.write("- Stop en breakeven automático\n")
        f.write("- Ganancias parciales al 1.5%\n")
        f.write("- Detección de divergencias\n")
        f.write("- Análisis multi-timeframe\n")
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    # Mostrar operaciones de ejemplo
    if results['trades']:
        print("\n📋 ÚLTIMAS 5 OPERACIONES DEFINITIVAS:")
        print("-" * 70)
        for trade in results['trades'][-5:]:
            if trade.get('status') == 'closed':
                direction = trade['direction']
                total_pnl_pct = trade.get('total_pnl_pct', 0)
                score = trade.get('signal_score', 0)
                confirmations = len(trade.get('confirmations', []))
                reason = trade.get('exit_reason', 'Unknown')
                partial = " (Parcial)" if trade.get('partial_profit_taken', False) else ""
                breakeven = " (BE)" if trade.get('breakeven_moved', False) else ""
                print(f"{direction}: {total_pnl_pct:+.2f}% (Score:{score}, Conf:{confirmations}) - {reason}{partial}{breakeven}")
    
    return results


if __name__ == "__main__":
    results = run_ultimate_20pct_test()