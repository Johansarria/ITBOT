#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Estrategia Inteligente 15% Mensual
Combina Machine Learning, filtros de calidad y gestión de riesgo adaptativa
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import warnings
warnings.filterwarnings('ignore')

class Smart15PctStrategy:
    """
    Estrategia inteligente que combina ML y análisis técnico para 15% mensual
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {
            # Gestión de riesgo inteligente
            'base_risk_per_trade': 0.03,  # 3% base
            'max_risk_per_trade': 0.06,   # 6% máximo
            'min_risk_per_trade': 0.01,   # 1% mínimo
            'daily_risk_limit': 0.15,     # 15% diario
            'max_consecutive_losses': 3,
            
            # Filtros de calidad
            'min_ml_confidence': 0.75,
            'min_signal_strength': 6,
            'max_daily_trades': 8,
            'min_profit_target': 0.008,   # 0.8% mínimo
            
            # Indicadores técnicos optimizados
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9,
            'bb_period': 20,
            'bb_std': 2.0,
            'atr_period': 14,
            
            # Filtros de mercado
            'min_volatility': 0.005,
            'max_volatility': 0.04,
            'trend_strength_threshold': 0.6,
            
            # ML parameters
            'lookback_periods': 50,
            'feature_window': 20,
            'retrain_frequency': 100,
        }
        
        self.ml_model = None
        self.scaler = StandardScaler()
        self.model_trained = False
        self.consecutive_losses = 0
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.last_retrain = 0
        
    def calculate_advanced_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos avanzados y features para ML
        """
        df = data.copy()
        
        # Indicadores básicos
        df['rsi'] = self._calculate_rsi(df['close'], self.config['rsi_period'])
        
        # MACD
        macd_data = self._calculate_macd(df['close'])
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        
        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_data['upper']
        df['bb_middle'] = bb_data['middle']
        df['bb_lower'] = bb_data['lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # ATR y volatilidad
        df['atr'] = self._calculate_atr(df)
        df['volatility'] = df['close'].rolling(20).std() / df['close'].rolling(20).mean()
        
        # EMAs múltiples
        for period in [8, 13, 21, 34, 55]:
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
        
        # Features avanzados para ML
        df['price_momentum_5'] = df['close'].pct_change(5)
        df['price_momentum_10'] = df['close'].pct_change(10)
        df['price_momentum_20'] = df['close'].pct_change(20)
        
        # Volumen features
        if 'volume' in df.columns:
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            df['price_volume_trend'] = ((df['close'] - df['close'].shift(1)) / df['close'].shift(1)) * df['volume']
        else:
            df['volume_ratio'] = 1.0
            df['price_volume_trend'] = 0.0
        
        # Trend strength
        df['trend_strength'] = self._calculate_trend_strength(df)
        
        # Support/Resistance
        df['support'] = df['low'].rolling(20).min()
        df['resistance'] = df['high'].rolling(20).max()
        df['support_distance'] = (df['close'] - df['support']) / df['close']
        df['resistance_distance'] = (df['resistance'] - df['close']) / df['close']
        
        # Market structure
        df['higher_highs'] = (df['high'] > df['high'].shift(1)) & (df['high'].shift(1) > df['high'].shift(2))
        df['lower_lows'] = (df['low'] < df['low'].shift(1)) & (df['low'].shift(1) < df['low'].shift(2))
        
        # Candlestick patterns
        df['doji'] = abs(df['open'] - df['close']) < (df['high'] - df['low']) * 0.1
        df['hammer'] = (df['close'] > df['open']) & ((df['close'] - df['open']) > 2 * (df['open'] - df['low']))
        df['shooting_star'] = (df['open'] > df['close']) & ((df['high'] - df['open']) > 2 * (df['close'] - df['low']))
        
        # Fibonacci levels
        df['fib_23'] = df['support'] + (df['resistance'] - df['support']) * 0.236
        df['fib_38'] = df['support'] + (df['resistance'] - df['support']) * 0.382
        df['fib_61'] = df['support'] + (df['resistance'] - df['support']) * 0.618
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> Dict[str, pd.Series]:
        """Calcula MACD"""
        ema_fast = prices.ewm(span=self.config['macd_fast']).mean()
        ema_slow = prices.ewm(span=self.config['macd_slow']).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.config['macd_signal']).mean()
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
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> pd.Series:
        """Calcula fuerza de tendencia"""
        # Basado en la alineación de EMAs
        ema_8 = df['ema_8']
        ema_21 = df['ema_21']
        ema_55 = df['ema_55']
        
        bullish_alignment = (ema_8 > ema_21) & (ema_21 > ema_55)
        bearish_alignment = (ema_8 < ema_21) & (ema_21 < ema_55)
        
        trend_strength = pd.Series(0.0, index=df.index)
        trend_strength[bullish_alignment] = 1.0
        trend_strength[bearish_alignment] = -1.0
        
        return trend_strength.rolling(10).mean()
    
    def prepare_ml_features(self, df: pd.DataFrame, idx: int) -> np.ndarray:
        """
        Prepara features para el modelo de ML
        """
        if idx < self.config['feature_window']:
            return None
        
        # Seleccionar features relevantes
        feature_cols = [
            'rsi', 'macd', 'macd_histogram', 'bb_position',
            'volatility', 'price_momentum_5', 'price_momentum_10',
            'volume_ratio', 'trend_strength', 'support_distance',
            'resistance_distance'
        ]
        
        # Obtener ventana de datos
        start_idx = max(0, idx - self.config['feature_window'] + 1)
        window_data = df.iloc[start_idx:idx+1]
        
        features = []
        for col in feature_cols:
            if col in window_data.columns:
                # Estadísticas de la ventana
                values = window_data[col].dropna()
                if len(values) > 0:
                    features.extend([
                        values.iloc[-1],  # Valor actual
                        values.mean(),    # Media
                        values.std(),     # Desviación estándar
                        values.min(),     # Mínimo
                        values.max(),     # Máximo
                    ])
                else:
                    features.extend([0, 0, 0, 0, 0])
            else:
                features.extend([0, 0, 0, 0, 0])
        
        return np.array(features).reshape(1, -1)
    
    def train_ml_model(self, df: pd.DataFrame, start_idx: int, end_idx: int):
        """
        Entrena el modelo de ML con datos históricos
        """
        features_list = []
        labels_list = []
        
        for i in range(start_idx + self.config['feature_window'], end_idx - 5):
            # Preparar features
            features = self.prepare_ml_features(df, i)
            if features is None:
                continue
            
            # Calcular label (dirección del precio en los próximos 5 períodos)
            current_price = df.iloc[i]['close']
            future_price = df.iloc[i + 5]['close']
            price_change = (future_price - current_price) / current_price
            
            # Clasificación: 0 = vender, 1 = mantener, 2 = comprar
            if price_change > 0.005:  # +0.5%
                label = 2  # Comprar
            elif price_change < -0.005:  # -0.5%
                label = 0  # Vender
            else:
                label = 1  # Mantener
            
            features_list.append(features.flatten())
            labels_list.append(label)
        
        if len(features_list) < 50:  # Necesitamos suficientes datos
            return False
        
        X = np.array(features_list)
        y = np.array(labels_list)
        
        # Dividir datos
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Escalar features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entrenar modelo ensemble
        rf_model = RandomForestClassifier(n_estimators=100, random_state=42, max_depth=10)
        gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42, max_depth=6)
        
        rf_model.fit(X_train_scaled, y_train)
        gb_model.fit(X_train_scaled, y_train)
        
        # Evaluar modelos
        rf_score = rf_model.score(X_test_scaled, y_test)
        gb_score = gb_model.score(X_test_scaled, y_test)
        
        # Seleccionar mejor modelo
        if rf_score > gb_score:
            self.ml_model = rf_model
        else:
            self.ml_model = gb_model
        
        self.model_trained = True
        self.last_retrain = end_idx
        
        return True
    
    def get_ml_prediction(self, df: pd.DataFrame, idx: int) -> Tuple[int, float]:
        """
        Obtiene predicción del modelo ML
        """
        if not self.model_trained or self.ml_model is None:
            return 1, 0.5  # Mantener con baja confianza
        
        features = self.prepare_ml_features(df, idx)
        if features is None:
            return 1, 0.5
        
        try:
            features_scaled = self.scaler.transform(features)
            prediction = self.ml_model.predict(features_scaled)[0]
            probabilities = self.ml_model.predict_proba(features_scaled)[0]
            confidence = max(probabilities)
            
            return prediction, confidence
        except:
            return 1, 0.5
    
    def calculate_signal_strength(self, df: pd.DataFrame, idx: int) -> Tuple[int, str]:
        """
        Calcula la fuerza de la señal basada en múltiples factores
        """
        if idx < 50:
            return 0, "MANTENER"
        
        current = df.iloc[idx]
        prev = df.iloc[idx - 1]
        
        buy_signals = 0
        sell_signals = 0
        
        # RSI signals
        if current['rsi'] < self.config['rsi_oversold'] and current['rsi'] > prev['rsi']:
            buy_signals += 2
        elif current['rsi'] > self.config['rsi_overbought'] and current['rsi'] < prev['rsi']:
            sell_signals += 2
        
        # MACD signals
        if prev['macd'] < prev['macd_signal'] and current['macd'] > current['macd_signal']:
            buy_signals += 3
        elif prev['macd'] > prev['macd_signal'] and current['macd'] < current['macd_signal']:
            sell_signals += 3
        
        # Bollinger Bands
        if current['bb_position'] < 0.2 and prev['bb_position'] < current['bb_position']:
            buy_signals += 2
        elif current['bb_position'] > 0.8 and prev['bb_position'] > current['bb_position']:
            sell_signals += 2
        
        # Trend alignment
        if current['trend_strength'] > self.config['trend_strength_threshold']:
            buy_signals += 2
        elif current['trend_strength'] < -self.config['trend_strength_threshold']:
            sell_signals += 2
        
        # EMA alignment
        if current['ema_8'] > current['ema_21'] > current['ema_55']:
            buy_signals += 1
        elif current['ema_8'] < current['ema_21'] < current['ema_55']:
            sell_signals += 1
        
        # Volatility filter
        if current['volatility'] < self.config['min_volatility'] or current['volatility'] > self.config['max_volatility']:
            buy_signals = max(0, buy_signals - 3)
            sell_signals = max(0, sell_signals - 3)
        
        # Support/Resistance
        if current['support_distance'] < 0.01:  # Near support
            buy_signals += 1
        elif current['resistance_distance'] < 0.01:  # Near resistance
            sell_signals += 1
        
        # Determine signal
        if buy_signals >= self.config['min_signal_strength'] and buy_signals > sell_signals:
            return buy_signals, "COMPRAR"
        elif sell_signals >= self.config['min_signal_strength'] and sell_signals > buy_signals:
            return sell_signals, "VENDER"
        else:
            return max(buy_signals, sell_signals), "MANTENER"
    
    def calculate_dynamic_risk(self) -> float:
        """
        Calcula riesgo dinámico basado en performance reciente
        """
        base_risk = self.config['base_risk_per_trade']
        
        # Reducir riesgo después de pérdidas consecutivas
        if self.consecutive_losses >= self.config['max_consecutive_losses']:
            risk_multiplier = 0.5
        elif self.consecutive_losses >= 2:
            risk_multiplier = 0.7
        elif self.consecutive_losses >= 1:
            risk_multiplier = 0.85
        else:
            # Aumentar riesgo después de ganancias
            risk_multiplier = 1.2 if self.daily_pnl > 0.05 else 1.0
        
        dynamic_risk = base_risk * risk_multiplier
        
        # Aplicar límites
        return max(self.config['min_risk_per_trade'], 
                  min(self.config['max_risk_per_trade'], dynamic_risk))
    
    def generate_signal(self, df: pd.DataFrame, idx: int) -> Dict[str, Any]:
        """
        Genera señal de trading inteligente
        """
        # Verificar límites diarios
        if self.daily_trades >= self.config['max_daily_trades']:
            return {'action': 'MANTENER', 'reason': 'Max daily trades reached'}
        
        if abs(self.daily_pnl) >= self.config['daily_risk_limit']:
            return {'action': 'MANTENER', 'reason': 'Daily risk limit reached'}
        
        # Re-entrenar modelo si es necesario
        if idx - self.last_retrain >= self.config['retrain_frequency']:
            start_idx = max(0, idx - 500)
            self.train_ml_model(df, start_idx, idx)
        
        # Obtener predicción ML
        ml_prediction, ml_confidence = self.get_ml_prediction(df, idx)
        
        # Calcular fuerza de señal técnica
        signal_strength, technical_signal = self.calculate_signal_strength(df, idx)
        
        # Combinar señales
        if ml_confidence < self.config['min_ml_confidence']:
            return {'action': 'MANTENER', 'reason': 'Low ML confidence'}
        
        # Verificar alineación entre ML y análisis técnico
        ml_actions = {0: 'VENDER', 1: 'MANTENER', 2: 'COMPRAR'}
        ml_action = ml_actions[ml_prediction]
        
        if ml_action == technical_signal and signal_strength >= self.config['min_signal_strength']:
            # Calcular riesgo dinámico
            risk_per_trade = self.calculate_dynamic_risk()
            
            # Calcular stop loss y take profit
            current_price = df.iloc[idx]['close']
            atr = df.iloc[idx]['atr']
            
            if ml_action == 'COMPRAR':
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 3.0)
            elif ml_action == 'VENDER':
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 3.0)
            else:
                stop_loss = take_profit = current_price
            
            return {
                'action': ml_action,
                'ml_confidence': ml_confidence,
                'signal_strength': signal_strength,
                'risk_per_trade': risk_per_trade,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'reason': f'ML + Technical alignment (confidence: {ml_confidence:.2f})'
            }
        
        return {'action': 'MANTENER', 'reason': 'No signal alignment'}
    
    def update_performance(self, pnl: float, is_win: bool):
        """
        Actualiza métricas de performance
        """
        self.daily_pnl += pnl
        self.daily_trades += 1
        
        if is_win:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
    
    def reset_daily_stats(self):
        """Resetea estadísticas diarias"""
        self.daily_pnl = 0.0
        self.daily_trades = 0


class SmartBacktester:
    """
    Backtester para estrategia inteligente
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
        
    def run_backtest(self, data: pd.DataFrame, strategy: Smart15PctStrategy) -> Dict[str, Any]:
        """Ejecuta backtest inteligente"""
        df = strategy.calculate_advanced_indicators(data)
        
        # Entrenar modelo inicial
        if len(df) > 200:
            strategy.train_ml_model(df, 100, 200)
        
        for i in range(len(df)):
            current_data = df.iloc[i]
            
            # Verificar posición existente
            if self.position is not None:
                self._check_exit_conditions(current_data, strategy)
            else:
                # Buscar nueva entrada
                signal_data = strategy.generate_signal(df, i)
                if signal_data['action'] in ['COMPRAR', 'VENDER']:
                    self._open_position(current_data, signal_data, strategy)
            
            # Actualizar historial
            current_value = self._calculate_portfolio_value(current_data['close'])
            self.balance_history.append(current_value)
        
        # Cerrar posición final
        if self.position is not None:
            self._close_position(df.iloc[-1]['close'], "Final close")
        
        return self._calculate_results()
    
    def _open_position(self, data: pd.Series, signal_data: Dict[str, Any], strategy: Smart15PctStrategy):
        """Abre nueva posición"""
        price = data['close']
        direction = signal_data['action']
        risk_per_trade = signal_data['risk_per_trade']
        
        # Calcular tamaño de posición
        risk_amount = self.balance * risk_per_trade
        price_diff = abs(price - signal_data['stop_loss'])
        
        if price_diff > 0:
            position_size = risk_amount / price_diff
            cost = position_size * price * (1 + self.commission)
            
            if cost <= self.balance:
                self.position = direction
                self.position_size = position_size
                self.entry_price = price
                self.stop_loss = signal_data['stop_loss']
                self.take_profit = signal_data['take_profit']
                self.balance -= cost
                
                # Registrar trade
                trade = {
                    'entry_time': data.name if hasattr(data, 'name') else len(self.trades),
                    'direction': direction,
                    'entry_price': price,
                    'position_size': position_size,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'ml_confidence': signal_data['ml_confidence'],
                    'signal_strength': signal_data['signal_strength'],
                    'status': 'open'
                }
                self.trades.append(trade)
    
    def _check_exit_conditions(self, data: pd.Series, strategy: Smart15PctStrategy):
        """Verifica condiciones de salida"""
        current_price = data['close']
        
        # Stop loss
        if ((self.position == "COMPRAR" and current_price <= self.stop_loss) or
            (self.position == "VENDER" and current_price >= self.stop_loss)):
            self._close_position(current_price, "Stop Loss")
            return
        
        # Take profit
        if ((self.position == "COMPRAR" and current_price >= self.take_profit) or
            (self.position == "VENDER" and current_price <= self.take_profit)):
            self._close_position(current_price, "Take Profit")
            return
    
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
        
        # Actualizar trade
        if self.trades:
            self.trades[-1].update({
                'exit_price': exit_price,
                'exit_reason': reason,
                'pnl': pnl,
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
    
    def _calculate_results(self) -> Dict[str, Any]:
        """Calcula resultados finales"""
        final_balance = self.balance_history[-1]
        total_return = (final_balance / self.initial_balance - 1) * 100
        
        closed_trades = [t for t in self.trades if t.get('status') == 'closed']
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        # Calcular drawdown
        peak = self.initial_balance
        max_drawdown = 0
        for balance in self.balance_history:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Retorno mensual
        days_simulated = len(self.balance_history)
        monthly_return = (total_return / days_simulated) * 30 if days_simulated > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_return_pct': total_return,
            'monthly_return_pct': monthly_return,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'win_rate_pct': win_rate,
            'max_drawdown_pct': max_drawdown,
            'target_achieved': monthly_return >= 15.0,
            'balance_history': self.balance_history,
            'trades': self.trades
        }


def generate_realistic_data(days: int = 90, initial_price: float = 18000) -> pd.DataFrame:
    """
    Genera datos más realistas para testing
    """
    np.random.seed(123)  # Diferente seed para variedad
    periods_per_day = 24 * 4  # 15 min intervals
    total_periods = days * periods_per_day
    
    dates = pd.date_range(start='2024-01-01', periods=total_periods, freq='15min')
    
    # Generar retornos más realistas
    base_volatility = 0.003
    returns = np.random.normal(0, base_volatility, total_periods)
    
    # Añadir ciclos de mercado
    trend_cycle = np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 30)) * 0.001
    volatility_cycle = 1 + 0.5 * np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 7))
    
    returns = returns * volatility_cycle + trend_cycle
    
    # Generar precios
    prices = initial_price * (1 + returns).cumprod()
    
    # Crear OHLC más realista
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'close': prices,
        'volume': np.random.randint(5000, 50000, total_periods)
    })
    
    # Generar high/low más realistas
    for i in range(len(df)):
        volatility = abs(returns[i]) * 2
        df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + volatility)
        df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - volatility)
        
        # Ajustar close dentro del rango
        df.loc[i, 'close'] = np.clip(df.loc[i, 'close'], 
                                    df.loc[i, 'low'], 
                                    df.loc[i, 'high'])
    
    df.set_index('timestamp', inplace=True)
    return df


def run_smart_strategy_test():
    """
    Ejecuta test de la estrategia inteligente
    """
    print("🧠 Iniciando test de Estrategia Inteligente 15% Mensual")
    print("=" * 60)
    
    # Generar datos
    data = generate_realistic_data(days=120)  # 4 meses
    print(f"📊 Datos generados: {len(data)} períodos")
    
    # Crear estrategia
    strategy = Smart15PctStrategy()
    print("⚙️ Estrategia inteligente configurada")
    
    # Ejecutar backtest
    backtester = SmartBacktester(initial_balance=100000.0)
    results = backtester.run_backtest(data, strategy)
    
    # Mostrar resultados
    print("\n📈 RESULTADOS DEL BACKTEST INTELIGENTE")
    print("=" * 45)
    print(f"Balance inicial: ${results['initial_balance']:,.2f}")
    print(f"Balance final: ${results['final_balance']:,.2f}")
    print(f"Retorno total: {results['total_return_pct']:.2f}%")
    print(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%")
    print(f"\n🎯 OBJETIVO 15% MENSUAL: {'✅ ALCANZADO' if results['target_achieved'] else '❌ NO ALCANZADO'}")
    
    print(f"\n📊 ESTADÍSTICAS DE TRADING")
    print(f"Total de operaciones: {results['total_trades']}")
    print(f"Operaciones ganadoras: {results['winning_trades']}")
    print(f"Win Rate: {results['win_rate_pct']:.2f}%")
    print(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%")
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"smart_15pct_results_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("RESULTADOS ESTRATEGIA INTELIGENTE 15% MENSUAL\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Balance inicial: ${results['initial_balance']:,.2f}\n")
        f.write(f"Balance final: ${results['final_balance']:,.2f}\n")
        f.write(f"Retorno total: {results['total_return_pct']:.2f}%\n")
        f.write(f"Retorno mensual promedio: {results['monthly_return_pct']:.2f}%\n")
        f.write(f"Objetivo 15% mensual: {'ALCANZADO' if results['target_achieved'] else 'NO ALCANZADO'}\n\n")
        f.write(f"Total de operaciones: {results['total_trades']}\n")
        f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
        f.write(f"Máximo Drawdown: {results['max_drawdown_pct']:.2f}%\n\n")
        
        f.write("CARACTERÍSTICAS DE LA ESTRATEGIA:\n")
        f.write("-" * 35 + "\n")
        f.write("- Machine Learning con Random Forest/Gradient Boosting\n")
        f.write("- Gestión de riesgo adaptativa\n")
        f.write("- Filtros de calidad estrictos\n")
        f.write("- Múltiples indicadores técnicos\n")
        f.write("- Re-entrenamiento automático del modelo\n")
    
    print(f"\n💾 Resultados guardados en: {filename}")
    
    return results


if __name__ == "__main__":
    try:
        results = run_smart_strategy_test()
    except ImportError as e:
        print(f"❌ Error: Falta instalar scikit-learn")
        print("Ejecuta: pip install scikit-learn")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")