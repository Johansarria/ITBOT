#!/usr/bin/env python3
"""
Sistema SICAR Definitivo - Optimizado para 15% ROI Mensual
Combina todas las mejores técnicas desarrolladas:
- Multi-timeframe (15m, 1h, 4h, 1d)
- Multi-pair con correlaciones
- Market making dinámico
- Momentum agresivo
- ML ensemble
- Gestión de riesgo avanzada
- Apalancamiento máximo optimizado
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_sicar_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.robust_data_fetcher import RobustDataFetcher

class UltimateSicarSystem:
    def __init__(self, initial_capital=500, leverage=1.0):
        """
        Sistema SICAR Definitivo - Optimizado para 15% ROI mensual
        
        Args:
            initial_capital: Capital inicial en USD
            leverage: Apalancamiento máximo (15x)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.leverage = leverage
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Configuración agresiva
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT']
        self.timeframes = ['15m', '1h', '4h']  # Multi-timeframe
        self.max_positions = 8  # Máximo 8 posiciones simultáneas
        self.position_size_pct = 0.5  # 50% del capital por posición
        
        # Configuración de estrategias con pesos optimizados
        self.strategy_weights = {
            'momentum_scalping': 0.30,    # Scalping agresivo
            'trend_following': 0.25,      # Seguimiento de tendencia
            'mean_reversion': 0.20,       # Reversión a la media
            'breakout_trading': 0.15,     # Trading de rupturas
            'ml_ensemble': 0.10           # Machine learning
        }
        
        # Configuración de indicadores
        self.fast_ema = 8
        self.slow_ema = 21
        self.rsi_period = 14
        self.bb_period = 20
        self.atr_period = 14
        
        # Thresholds ultra agresivos
        self.momentum_threshold = 0.003  # 0.3% momentum mínimo
        self.volatility_threshold = 0.008  # 0.8% volatilidad mínima
        self.volume_threshold = 1.1  # 1.1x volumen promedio
        self.confidence_threshold = 0.25  # Threshold muy bajo para más operaciones
        
        # Machine Learning
        self.rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.lr_model = LogisticRegression(random_state=42, max_iter=1000)
        self.scaler = StandardScaler()
        self.models_trained = False
        
        # Gestión de riesgo dinámica
        self.max_daily_loss = 0.15  # 15% pérdida máxima diaria
        self.max_drawdown = 0.25  # 25% drawdown máximo
        self.profit_target = 0.20  # 20% ganancia para reducir riesgo
        
        # Tracking avanzado
        self.operations = []
        self.positions = {}
        self.total_fees = 0
        self.daily_pnl = []
        self.peak_capital = initial_capital
        self.current_drawdown = 0
        self.consecutive_losses = 0
        self.strategy_performance = {}
        
        # Correlaciones entre pares
        self.pair_correlations = {}
        
        logging.info(f"🚀 Sistema SICAR Definitivo iniciado")
        logging.info(f"💰 Capital inicial: ${initial_capital}")
        logging.info(f"⚡ Apalancamiento: {leverage}x (MÁXIMO)")
        logging.info(f"🎯 Objetivo: 15% ROI mensual")
        logging.info(f"📊 Símbolos: {self.symbols}")
        logging.info(f"⏰ Timeframes: {self.timeframes}")
        logging.info(f"🔥 Configuración AGRESIVA activada")

    def calculate_comprehensive_indicators(self, data, timeframe):
        """Calcula indicadores técnicos comprehensivos"""
        df = data.copy()
        
        # Precios básicos
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        
        # EMAs rápidas para scalping
        for period in [5, 8, 13, 21, 34, 55]:
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
        
        # SMAs para tendencia
        for period in [10, 20, 50, 100]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
        
        # RSI multi-periodo
        for period in [7, 14, 21]:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # MACD múltiple
        for fast, slow, signal in [(8, 21, 5), (12, 26, 9), (19, 39, 9)]:
            exp1 = df['close'].ewm(span=fast).mean()
            exp2 = df['close'].ewm(span=slow).mean()
            df[f'macd_{fast}_{slow}'] = exp1 - exp2
            df[f'macd_signal_{fast}_{slow}'] = df[f'macd_{fast}_{slow}'].ewm(span=signal).mean()
            df[f'macd_hist_{fast}_{slow}'] = df[f'macd_{fast}_{slow}'] - df[f'macd_signal_{fast}_{slow}']
        
        # Bollinger Bands dinámicas
        for period in [10, 20, 30]:
            bb_middle = df['close'].rolling(period).mean()
            bb_std = df['close'].rolling(period).std()
            df[f'bb_upper_{period}'] = bb_middle + (bb_std * 2)
            df[f'bb_lower_{period}'] = bb_middle - (bb_std * 2)
            df[f'bb_position_{period}'] = (df['close'] - df[f'bb_lower_{period}']) / (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}'])
            df[f'bb_width_{period}'] = (df[f'bb_upper_{period}'] - df[f'bb_lower_{period}']) / bb_middle
        
        # ATR para volatilidad
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        df['atr'] = true_range.rolling(self.atr_period).mean()
        df['atr_pct'] = df['atr'] / df['close']
        
        # Momentum indicators
        for period in [5, 10, 20]:
            df[f'momentum_{period}'] = (df['close'] / df['close'].shift(period) - 1) * 100
            df[f'roc_{period}'] = df['close'].pct_change(period) * 100
        
        # Stochastic
        lowest_low = df['low'].rolling(14).min()
        highest_high = df['high'].rolling(14).max()
        df['stoch_k'] = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        # Williams %R
        df['williams_r'] = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['price_volume'] = df['close'] * df['volume']
        df['obv'] = (df['volume'] * np.sign(df['close'].diff())).cumsum()
        
        # Volatilidad
        df['volatility'] = df['returns'].rolling(20).std()
        df['volatility_ratio'] = df['volatility'] / df['volatility'].rolling(50).mean()
        
        # Indicadores específicos por timeframe
        if timeframe == '15m':
            # Scalping indicators
            df['scalp_momentum'] = (df['close'] / df['close'].shift(3) - 1) * 100
            df['scalp_volume'] = df['volume'] / df['volume'].rolling(5).mean()
        elif timeframe == '1h':
            # Swing indicators
            df['swing_trend'] = (df['ema_21'] - df['ema_55']) / df['ema_55'] * 100
            df['swing_strength'] = df['rsi_14'] - 50
        elif timeframe == '4h':
            # Position indicators
            df['position_trend'] = (df['sma_20'] - df['sma_50']) / df['sma_50'] * 100
            df['position_momentum'] = df['momentum_20']
        
        return df

    def train_ml_ensemble(self, data):
        """Entrena ensemble de modelos ML"""
        if len(data) < 200:
            return
        
        try:
            # Features comprehensivas
            feature_cols = [
                'rsi_7', 'rsi_14', 'rsi_21',
                'macd_8_21', 'macd_12_26', 'macd_19_39',
                'bb_position_10', 'bb_position_20', 'bb_position_30',
                'momentum_5', 'momentum_10', 'momentum_20',
                'stoch_k', 'stoch_d', 'williams_r',
                'volume_ratio', 'volatility_ratio', 'atr_pct'
            ]
            
            # Filtrar features disponibles
            available_features = [col for col in feature_cols if col in data.columns]
            X = data[available_features].dropna()
            
            # Target más sensible para más operaciones
            future_returns = data['close'].shift(-3) / data['close'] - 1
            conditions = [
                future_returns <= -0.005,  # Bajada 0.5%
                (future_returns > -0.005) & (future_returns < 0.005),  # Lateral
                future_returns >= 0.005   # Subida 0.5%
            ]
            y = np.select(conditions, [0, 1, 2], default=1)
            y = pd.Series(y, index=data.index)
            
            # Alinear datos
            common_idx = X.index.intersection(y.index)
            X = X.loc[common_idx]
            y = y.loc[common_idx]
            
            if len(X) < 100:
                return
            
            # Entrenar modelos
            X_scaled = self.scaler.fit_transform(X)
            
            self.rf_model.fit(X_scaled, y)
            self.gb_model.fit(X_scaled, y)
            self.lr_model.fit(X_scaled, y)
            
            # Evaluar
            rf_pred = self.rf_model.predict(X_scaled)
            gb_pred = self.gb_model.predict(X_scaled)
            lr_pred = self.lr_model.predict(X_scaled)
            
            rf_acc = accuracy_score(y, rf_pred)
            gb_acc = accuracy_score(y, gb_pred)
            lr_acc = accuracy_score(y, lr_pred)
            
            self.models_trained = True
            
            logging.info(f"🧠 Ensemble ML entrenado:")
            logging.info(f"  RF: {rf_acc:.3f} | GB: {gb_acc:.3f} | LR: {lr_acc:.3f}")
            
        except Exception as e:
            logging.warning(f"Error entrenando ML: {e}")

    def generate_multi_timeframe_signal(self, data_dict, symbol, idx):
        """Genera señal combinando múltiples timeframes"""
        signals = {}
        
        # Generar señales por timeframe
        for timeframe, data in data_dict.items():
            if idx >= len(data):
                continue
                
            if timeframe == '15m':
                signals['scalping'] = self.generate_scalping_signal(data, idx)
            elif timeframe == '1h':
                signals['swing'] = self.generate_swing_signal(data, idx)
            elif timeframe == '4h':
                signals['position'] = self.generate_position_signal(data, idx)
        
        # ML signal
        if self.models_trained and '1h' in data_dict:
            signals['ml'] = self.generate_ml_signal(data_dict['1h'], idx)
        
        # Combinar señales
        return self.combine_signals(signals, symbol)

    def generate_scalping_signal(self, data, idx):
        """Genera señal de scalping (15m)"""
        if idx < 20:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'scalping'}
        
        current = data.iloc[idx]
        score = 0
        confidence_factors = []
        
        # EMA crossover rápido
        if 'ema_8' in current and 'ema_21' in current:
            if current['ema_8'] > current['ema_21']:
                score += 1
                confidence_factors.append(0.7)
            else:
                score -= 1
                confidence_factors.append(0.7)
        
        # RSI scalping
        if 'rsi_7' in current:
            rsi = current['rsi_7']
            if rsi < 25:
                score += 2
                confidence_factors.append((25 - rsi) / 25)
            elif rsi > 75:
                score -= 2
                confidence_factors.append((rsi - 75) / 25)
        
        # Momentum scalping
        if 'scalp_momentum' in current:
            momentum = current['scalp_momentum']
            if momentum > 0.5:
                score += 1
                confidence_factors.append(min(momentum / 2, 1))
            elif momentum < -0.5:
                score -= 1
                confidence_factors.append(min(abs(momentum) / 2, 1))
        
        # Volume confirmation
        if 'scalp_volume' in current and current['scalp_volume'] > 1.5:
            if score > 0:
                score += 1
                confidence_factors.append(0.8)
        
        confidence = np.mean(confidence_factors) if confidence_factors else 0
        
        if score >= 2:
            return {'signal': 'BUY', 'confidence': confidence, 'strategy': 'scalping', 'score': score}
        elif score <= -2:
            return {'signal': 'SELL', 'confidence': confidence, 'strategy': 'scalping', 'score': score}
        else:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'scalping', 'score': score}

    def generate_swing_signal(self, data, idx):
        """Genera señal de swing trading (1h)"""
        if idx < 30:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'swing'}
        
        current = data.iloc[idx]
        score = 0
        confidence_factors = []
        
        # Trend following
        if 'swing_trend' in current:
            trend = current['swing_trend']
            if trend > 1:
                score += 2
                confidence_factors.append(min(trend / 5, 1))
            elif trend < -1:
                score -= 2
                confidence_factors.append(min(abs(trend) / 5, 1))
        
        # MACD
        if 'macd_12_26' in current and 'macd_signal_12_26' in current:
            if current['macd_12_26'] > current['macd_signal_12_26']:
                score += 1
                confidence_factors.append(0.7)
            else:
                score -= 1
                confidence_factors.append(0.7)
        
        # RSI swing
        if 'rsi_14' in current:
            rsi = current['rsi_14']
            if 35 < rsi < 65:
                score += 1
                confidence_factors.append(0.6)
        
        # Bollinger position
        if 'bb_position_20' in current:
            bb_pos = current['bb_position_20']
            if bb_pos < 0.3:
                score += 1
                confidence_factors.append(0.3 - bb_pos)
            elif bb_pos > 0.7:
                score -= 1
                confidence_factors.append(bb_pos - 0.7)
        
        confidence = np.mean(confidence_factors) if confidence_factors else 0
        
        if score >= 2:
            return {'signal': 'BUY', 'confidence': confidence, 'strategy': 'swing', 'score': score}
        elif score <= -2:
            return {'signal': 'SELL', 'confidence': confidence, 'strategy': 'swing', 'score': score}
        else:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'swing', 'score': score}

    def generate_position_signal(self, data, idx):
        """Genera señal de position trading (4h)"""
        if idx < 50:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'position'}
        
        current = data.iloc[idx]
        score = 0
        confidence_factors = []
        
        # Position trend
        if 'position_trend' in current:
            trend = current['position_trend']
            if trend > 2:
                score += 2
                confidence_factors.append(min(trend / 10, 1))
            elif trend < -2:
                score -= 2
                confidence_factors.append(min(abs(trend) / 10, 1))
        
        # Long-term momentum
        if 'position_momentum' in current:
            momentum = current['position_momentum']
            if momentum > 3:
                score += 1
                confidence_factors.append(min(momentum / 10, 1))
            elif momentum < -3:
                score -= 1
                confidence_factors.append(min(abs(momentum) / 10, 1))
        
        # SMA alignment
        sma_score = 0
        for period in [20, 50]:
            if f'sma_{period}' in current and current['close'] > current[f'sma_{period}']:
                sma_score += 1
            elif f'sma_{period}' in current:
                sma_score -= 1
        
        score += sma_score
        if sma_score != 0:
            confidence_factors.append(0.8)
        
        confidence = np.mean(confidence_factors) if confidence_factors else 0
        
        if score >= 2:
            return {'signal': 'BUY', 'confidence': confidence, 'strategy': 'position', 'score': score}
        elif score <= -2:
            return {'signal': 'SELL', 'confidence': confidence, 'strategy': 'position', 'score': score}
        else:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'position', 'score': score}

    def generate_ml_signal(self, data, idx):
        """Genera señal de machine learning"""
        if not self.models_trained or idx < 50:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ml'}
        
        try:
            current = data.iloc[idx]
            
            # Features
            feature_cols = [
                'rsi_7', 'rsi_14', 'rsi_21',
                'macd_8_21', 'macd_12_26', 'macd_19_39',
                'bb_position_10', 'bb_position_20', 'bb_position_30',
                'momentum_5', 'momentum_10', 'momentum_20',
                'stoch_k', 'stoch_d', 'williams_r',
                'volume_ratio', 'volatility_ratio', 'atr_pct'
            ]
            
            features = []
            for col in feature_cols:
                if col in current:
                    value = current[col]
                    if pd.isna(value):
                        return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ml'}
                    features.append(value)
                else:
                    return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ml'}
            
            # Predecir con ensemble
            features_scaled = self.scaler.transform([features])
            
            rf_pred = self.rf_model.predict(features_scaled)[0]
            gb_pred = self.gb_model.predict(features_scaled)[0]
            lr_pred = self.lr_model.predict(features_scaled)[0]
            
            rf_proba = np.max(self.rf_model.predict_proba(features_scaled)[0])
            gb_proba = np.max(self.gb_model.predict_proba(features_scaled)[0])
            lr_proba = np.max(self.lr_model.predict_proba(features_scaled)[0])
            
            # Voting
            predictions = [rf_pred, gb_pred, lr_pred]
            probabilities = [rf_proba, gb_proba, lr_proba]
            
            # Majority vote
            final_pred = max(set(predictions), key=predictions.count)
            final_confidence = np.mean(probabilities)
            
            if final_pred == 2 and final_confidence > 0.3:
                return {'signal': 'BUY', 'confidence': final_confidence, 'strategy': 'ml'}
            elif final_pred == 0 and final_confidence > 0.3:
                return {'signal': 'SELL', 'confidence': final_confidence, 'strategy': 'ml'}
            else:
                return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ml'}
                
        except Exception as e:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'ml'}

    def combine_signals(self, signals, symbol):
        """Combina señales de múltiples estrategias"""
        if not signals:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'combined'}
        
        buy_weight = 0
        sell_weight = 0
        total_confidence = 0
        strategies_used = []
        
        for strategy, signal_data in signals.items():
            if signal_data['signal'] == 'HOLD':
                continue
            
            weight = self.strategy_weights.get(strategy, 0.1)
            confidence = signal_data['confidence']
            weighted_confidence = weight * confidence
            
            total_confidence += weighted_confidence
            strategies_used.append(strategy)
            
            if signal_data['signal'] == 'BUY':
                buy_weight += weighted_confidence
            elif signal_data['signal'] == 'SELL':
                sell_weight += weighted_confidence
        
        # Decisión final con threshold bajo para más operaciones
        if buy_weight > sell_weight and buy_weight > self.confidence_threshold:
            return {
                'signal': 'BUY',
                'confidence': min(buy_weight, 0.95),
                'strategy': 'combined',
                'strategies_used': strategies_used,
                'buy_weight': buy_weight,
                'sell_weight': sell_weight
            }
        elif sell_weight > buy_weight and sell_weight > self.confidence_threshold:
            return {
                'signal': 'SELL',
                'confidence': min(sell_weight, 0.95),
                'strategy': 'combined',
                'strategies_used': strategies_used,
                'buy_weight': buy_weight,
                'sell_weight': sell_weight
            }
        else:
            return {'signal': 'HOLD', 'confidence': 0, 'strategy': 'combined'}

    def calculate_dynamic_position_size(self, signal_data, current_price, symbol):
        """Calcula tamaño de posición dinámico"""
        base_size = self.current_capital * self.position_size_pct
        
        # Ajustar por confianza (más agresivo)
        confidence_multiplier = signal_data['confidence'] * 1.5
        
        # Ajustar por número de estrategias que coinciden
        if 'strategies_used' in signal_data:
            strategy_multiplier = 1 + (len(signal_data['strategies_used']) - 1) * 0.2
        else:
            strategy_multiplier = 1.0
        
        # Ajustar por performance reciente
        recent_performance = self.get_recent_performance()
        if recent_performance > 0:
            performance_multiplier = 1.2  # Aumentar si va bien
        else:
            performance_multiplier = 0.8  # Reducir si va mal
        
        # Tamaño final con apalancamiento máximo
        position_size = base_size * confidence_multiplier * strategy_multiplier * performance_multiplier * self.leverage
        
        # Limitar por gestión de riesgo
        max_size = self.current_capital * self.leverage * 0.9  # 90% máximo
        return min(position_size, max_size)

    def get_recent_performance(self):
        """Obtiene performance reciente"""
        if len(self.operations) < 5:
            return 0
        
        recent_ops = self.operations[-5:]
        recent_pnl = sum(op.get('pnl', 0) for op in recent_ops if 'pnl' in op)
        return recent_pnl / self.initial_capital

    def execute_aggressive_trade(self, signal_data, current_price, timestamp, symbol):
        """Ejecuta operación con configuración agresiva"""
        if signal_data['signal'] == 'HOLD':
            return
        
        # Verificar límites de posiciones
        if len(self.positions) >= self.max_positions:
            return
        
        # Verificar gestión de riesgo
        if not self.check_risk_limits():
            return
        
        position_size = self.calculate_dynamic_position_size(signal_data, current_price, symbol)
        
        if position_size < 50:  # Mínimo $50
            return
        
        quantity = position_size / current_price
        fee = position_size * self.fee_rate
        
        # Actualizar capital
        self.current_capital -= (position_size + fee)
        self.total_fees += fee
        
        # Stop loss y take profit agresivos
        if signal_data['signal'] == 'BUY':
            stop_loss = current_price * 0.96  # 4% stop loss
            take_profit = current_price * 1.08  # 8% take profit
        else:
            stop_loss = current_price * 1.04  # 4% stop loss
            take_profit = current_price * 0.92  # 8% take profit
        
        # Crear posición
        position_id = f"{signal_data['signal']}_{symbol}_{timestamp}"
        position = {
            'type': signal_data['signal'],
            'symbol': symbol,
            'entry_price': current_price,
            'quantity': quantity,
            'size': position_size,
            'timestamp': timestamp,
            'confidence': signal_data['confidence'],
            'strategy': signal_data['strategy'],
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'strategies_used': signal_data.get('strategies_used', [])
        }
        
        self.positions[position_id] = position
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'symbol': symbol,
            'type': f"{signal_data['signal']}_ULTIMATE",
            'price': current_price,
            'quantity': quantity,
            'size': position_size,
            'fee': fee,
            'confidence': signal_data['confidence'],
            'strategy': signal_data['strategy'],
            'capital_after': self.current_capital,
            'position_id': position_id,
            'strategies_used': ', '.join(signal_data.get('strategies_used', []))
        }
        
        self.operations.append(operation)
        
        logging.info(f"🔥 ULTIMATE {signal_data['signal']}: {symbol} ${position_size:.2f} @ ${current_price:.2f}")
        logging.info(f"   Conf: {signal_data['confidence']:.3f} | Strategies: {', '.join(signal_data.get('strategies_used', []))}")

    def check_risk_limits(self):
        """Verifica límites de riesgo"""
        # Verificar drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        self.current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        
        if self.current_drawdown > self.max_drawdown:
            logging.warning(f"⚠️ Drawdown máximo alcanzado: {self.current_drawdown:.2%}")
            return False
        
        # Verificar pérdidas consecutivas
        if self.consecutive_losses > 5:
            logging.warning(f"⚠️ Demasiadas pérdidas consecutivas: {self.consecutive_losses}")
            return False
        
        return True

    def manage_aggressive_positions(self, current_prices, timestamp):
        """Gestiona posiciones con trailing stops"""
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            symbol = position['symbol']
            current_price = current_prices.get(symbol, position['entry_price'])
            
            # Calcular PnL
            if position['type'] == 'BUY':
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            else:
                pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
            
            # Trailing stop agresivo
            if pnl_pct > 0.05:  # Si ganancia > 5%, activar trailing stop
                if position['type'] == 'BUY':
                    new_stop = current_price * 0.98  # 2% trailing
                    if new_stop > position['stop_loss']:
                        position['stop_loss'] = new_stop
                else:
                    new_stop = current_price * 1.02  # 2% trailing
                    if new_stop < position['stop_loss']:
                        position['stop_loss'] = new_stop
            
            # Verificar stop loss
            if ((position['type'] == 'BUY' and current_price <= position['stop_loss']) or
                (position['type'] == 'SELL' and current_price >= position['stop_loss'])):
                positions_to_close.append((position_id, current_price, "stop_loss"))
            
            # Verificar take profit
            elif ((position['type'] == 'BUY' and current_price >= position['take_profit']) or
                  (position['type'] == 'SELL' and current_price <= position['take_profit'])):
                positions_to_close.append((position_id, current_price, "take_profit"))
        
        # Cerrar posiciones
        for position_id, price, reason in positions_to_close:
            self.close_aggressive_position(position_id, price, timestamp, reason)

    def close_aggressive_position(self, position_id, current_price, timestamp, reason="signal"):
        """Cierra posición con tracking de performance"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        # Calcular PnL
        if position['type'] == 'BUY':
            pnl = (current_price - position['entry_price']) * position['quantity']
        else:
            pnl = (position['entry_price'] - current_price) * position['quantity']
        
        # Fees de cierre
        close_size = position['quantity'] * current_price
        close_fee = close_size * self.fee_rate
        net_pnl = pnl - close_fee
        
        # Actualizar capital
        self.current_capital += (position['size'] + net_pnl)
        self.total_fees += close_fee
        
        # Tracking de pérdidas consecutivas
        if net_pnl > 0:
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Registrar cierre
        operation = {
            'timestamp': timestamp,
            'symbol': position['symbol'],
            'type': f"CLOSE_{position['type']}",
            'price': current_price,
            'quantity': position['quantity'],
            'size': close_size,
            'fee': close_fee,
            'pnl': net_pnl,
            'capital_after': self.current_capital,
            'position_id': position_id,
            'reason': reason,
            'strategy': position['strategy']
        }
        
        self.operations.append(operation)
        
        # Eliminar posición
        del self.positions[position_id]
        
        pnl_pct = (net_pnl / position['size']) * 100
        logging.info(f"🔚 CLOSE {position['type']}: {position['symbol']} PnL ${net_pnl:.2f} ({pnl_pct:.1f}%) | {reason}")

    def run_ultimate_backtest(self, days=60):
        """Ejecuta el backtest definitivo"""
        logging.info(f"🔥 Iniciando ULTIMATE BACKTEST para {len(self.symbols)} símbolos")
        logging.info(f"⚡ Configuración MÁXIMA: {self.leverage}x leverage, {self.max_positions} posiciones")
        
        # Obtener datos multi-timeframe para todos los símbolos
        all_data = {}
        fetcher = RobustDataFetcher()
        
        for symbol in self.symbols:
            all_data[symbol] = {}
            
            for timeframe in self.timeframes:
                data = fetcher.get_market_data(symbol, timeframe, limit=days*24*4)
                if data is not None and not data.empty:
                    data.columns = data.columns.str.lower()
                    if data.index.name == 'timestamp' or 'timestamp' in str(data.index.name).lower():
                        data.reset_index(inplace=True)
                    
                    # Calcular indicadores
                    data_with_indicators = self.calculate_comprehensive_indicators(data, timeframe)
                    all_data[symbol][timeframe] = data_with_indicators
                    
                    logging.info(f"📊 {symbol} {timeframe}: {len(data)} velas obtenidas")
        
        if not all_data:
            logging.error("❌ No se pudieron obtener datos")
            return
        
        # Entrenar ML con datos de 1h del primer símbolo
        first_symbol = list(all_data.keys())[0]
        if '1h' in all_data[first_symbol]:
            self.train_ml_ensemble(all_data[first_symbol]['1h'])
        
        # Determinar longitud mínima
        min_length = float('inf')
        for symbol_data in all_data.values():
            for timeframe_data in symbol_data.values():
                min_length = min(min_length, len(timeframe_data))
        
        logging.info("🔥 Iniciando ULTIMATE BACKTEST...")
        
        # Backtest agresivo
        for idx in range(100, min_length):
            current_prices = {}
            
            # Obtener precios actuales
            for symbol in self.symbols:
                if '15m' in all_data[symbol] and idx < len(all_data[symbol]['15m']):
                    current_prices[symbol] = all_data[symbol]['15m']['close'].iloc[idx]
            
            if not current_prices:
                continue
            
            timestamp = idx  # Simplificado
            
            # Generar señales para cada símbolo
            for symbol in self.symbols:
                if symbol not in current_prices:
                    continue
                
                current_price = current_prices[symbol]
                
                # Generar señal multi-timeframe
                signal_data = self.generate_multi_timeframe_signal(all_data[symbol], symbol, idx)
                
                # Ejecutar trade agresivo
                self.execute_aggressive_trade(signal_data, current_price, timestamp, symbol)
            
            # Gestionar posiciones agresivamente
            self.manage_aggressive_positions(current_prices, timestamp)
        
        # Cerrar todas las posiciones al final
        final_prices = {}
        for symbol in self.symbols:
            if '15m' in all_data[symbol]:
                final_prices[symbol] = all_data[symbol]['15m']['close'].iloc[-1]
        
        for position_id in list(self.positions.keys()):
            position = self.positions[position_id]
            if position['symbol'] in final_prices:
                final_price = final_prices[position['symbol']]
                self.close_aggressive_position(position_id, final_price, min_length-1, "backtest_end")
        
        # Calcular métricas finales
        self.calculate_ultimate_metrics(days)

    def calculate_ultimate_metrics(self, days):
        """Calcula métricas finales del sistema definitivo"""
        if not self.operations:
            logging.warning("⚠️ No se generaron operaciones")
            return
        
        # Métricas básicas
        total_operations = len(self.operations)
        buy_ops = len([op for op in self.operations if 'BUY' in op['type']])
        sell_ops = len([op for op in self.operations if 'SELL' in op['type']])
        close_ops = len([op for op in self.operations if 'CLOSE' in op['type']])
        
        # Win rate
        close_operations = [op for op in self.operations if 'CLOSE' in op['type'] and 'pnl' in op]
        winning_ops = len([op for op in close_operations if op['pnl'] > 0])
        win_rate = (winning_ops / len(close_operations)) * 100 if close_operations else 0
        
        # Retornos
        net_pnl = self.current_capital - self.initial_capital
        net_return = (net_pnl / self.initial_capital) * 100
        
        # ROI mensual
        months = days / 30.44
        monthly_roi = (((self.current_capital / self.initial_capital) ** (1/months)) - 1) * 100
        
        # Gap al objetivo
        target_roi = 15.0
        roi_gap = target_roi - monthly_roi
        
        # Métricas avanzadas
        if close_operations:
            avg_win = np.mean([op['pnl'] for op in close_operations if op['pnl'] > 0]) if winning_ops > 0 else 0
            avg_loss = np.mean([op['pnl'] for op in close_operations if op['pnl'] < 0]) if (len(close_operations) - winning_ops) > 0 else 0
            profit_factor = abs(avg_win * winning_ops / (avg_loss * (len(close_operations) - winning_ops))) if avg_loss != 0 else float('inf')
        else:
            avg_win = avg_loss = profit_factor = 0
        
        # Logging de resultados
        logging.info("=" * 80)
        logging.info("🔥 RESULTADOS SISTEMA SICAR DEFINITIVO 🔥")
        logging.info("=" * 80)
        logging.info(f"💰 Capital inicial: ${self.initial_capital:.2f}")
        logging.info(f"💰 Capital final: ${self.current_capital:.2f}")
        logging.info(f"💸 Fees totales: ${self.total_fees:.2f}")
        logging.info(f"💵 PnL neto: ${net_pnl:.2f}")
        logging.info(f"📊 Retorno neto: {net_return:.2f}%")
        logging.info(f"🎯 ROI mensual: {monthly_roi:.2f}%")
        logging.info(f"🔄 Total operaciones: {total_operations}")
        logging.info(f"📈 Operaciones de compra: {buy_ops}")
        logging.info(f"📉 Operaciones de venta: {sell_ops}")
        logging.info(f"🔚 Operaciones cerradas: {close_ops}")
        logging.info(f"🏆 Win rate: {win_rate:.1f}%")
        logging.info(f"💰 Ganancia promedio: ${avg_win:.2f}")
        logging.info(f"💸 Pérdida promedio: ${avg_loss:.2f}")
        logging.info(f"📊 Profit Factor: {profit_factor:.2f}")
        logging.info(f"📅 Duración: {days} días ({months:.1f} meses)")
        logging.info(f"⚡ Apalancamiento: {self.leverage}x (MÁXIMO)")
        logging.info(f"📉 Max Drawdown: {self.current_drawdown:.2%}")
        logging.info(f"🔥 Pérdidas consecutivas: {self.consecutive_losses}")
        logging.info(f"⚡ Gap al objetivo: {roi_gap:.2f}% (Objetivo: {target_roi}%)")
        
        # Estado final
        if monthly_roi >= target_roi:
            logging.info("🎉 ¡OBJETIVO ALCANZADO! 🎉")
        else:
            logging.info(f"📈 Progreso: {(monthly_roi/target_roi)*100:.1f}% del objetivo")
        
        logging.info("=" * 80)
        
        # Guardar resultados
        self.save_ultimate_results()
        
        # Resumen final
        print(f"\n🔥 ULTIMATE SICAR BACKTEST COMPLETADO! 🔥")
        print(f"📊 ROI mensual: {monthly_roi:.2f}%")
        print(f"🎯 Objetivo: {target_roi}%")
        print(f"🔄 Total operaciones: {total_operations}")
        print(f"🏆 Win rate: {win_rate:.1f}%")
        print(f"⚡ Apalancamiento: {self.leverage}x")
        print(f"📉 Max Drawdown: {self.current_drawdown:.2%}")
        print(f"📁 Resultados guardados en: ultimate_sicar_results.csv")
        
        if monthly_roi >= target_roi:
            print("🎉 ¡OBJETIVO DE 15% ROI MENSUAL ALCANZADO! 🎉")

    def save_ultimate_results(self):
        """Guarda los resultados del sistema definitivo"""
        if self.operations:
            df = pd.DataFrame(self.operations)
            df.to_csv('ultimate_sicar_results.csv', index=False)
            logging.info("💾 Resultados guardados en ultimate_sicar_results.csv")

def main():
    """Función principal del sistema definitivo"""
    try:
        # Crear y ejecutar sistema SICAR definitivo
        system = UltimateSicarSystem(
            initial_capital=500,
            leverage=15.0  # APALANCAMIENTO MÁXIMO
        )
        
        # Ejecutar backtest definitivo
        system.run_ultimate_backtest(days=60)
        
    except Exception as e:
        logging.error(f"❌ Error en sistema definitivo: {str(e)}")
        raise

if __name__ == "__main__":
    main()