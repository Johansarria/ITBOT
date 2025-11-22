#!/usr/bin/env python3
"""
Sistema SICAR con Timeframes Diarios - Estrategias de Largo Plazo
Optimizado para 15% ROI mensual con análisis técnico avanzado
Utiliza velas diarias para capturar tendencias de largo plazo
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import sys
import os
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_timeframe_sicar_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.robust_data_fetcher import RobustDataFetcher

class DailyTimeframeSicarSystem:
    def __init__(self, initial_capital=500, leverage=1.0):
        """
        Sistema SICAR con Timeframes Diarios
        
        Args:
            initial_capital: Capital inicial en USD
            leverage: Apalancamiento (12x para estrategias de largo plazo)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.leverage = leverage
        self.fee_rate = 0.001  # 0.1% por operación
        
        # Configuración de trading
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        self.max_positions = 3  # Máximo 3 posiciones para largo plazo
        self.position_size_pct = 0.4  # 40% del capital por posición
        
        # Configuración de indicadores técnicos
        self.sma_periods = [10, 20, 50, 100, 200]
        self.ema_periods = [12, 26, 50]
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
        
        # Configuración de señales
        self.trend_strength_threshold = 0.7
        self.momentum_threshold = 0.6
        self.volume_threshold = 1.5
        self.volatility_threshold = 0.02
        
        # Machine Learning
        self.rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.gb_model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.models_trained = False
        
        # Tracking
        self.operations = []
        self.positions = {}
        self.total_fees = 0
        self.daily_returns = []
        self.max_drawdown = 0
        self.peak_capital = initial_capital
        
        logging.info(f"🚀 Sistema SICAR Timeframes Diarios iniciado")
        logging.info(f"💰 Capital inicial: ${initial_capital}")
        logging.info(f"⚡ Apalancamiento: {leverage}x")
        logging.info(f"📊 Símbolos: {self.symbols}")
        logging.info(f"📈 Estrategia: Largo plazo con velas diarias")

    def calculate_advanced_indicators(self, data):
        """Calcula indicadores técnicos avanzados para timeframes diarios"""
        df = data.copy()
        
        # Precios básicos
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['high_low_ratio'] = (df['high'] - df['low']) / df['close']
        df['volume_change'] = df['volume'].pct_change()
        
        # Medias móviles simples
        for period in self.sma_periods:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'sma_{period}_slope'] = df[f'sma_{period}'].diff(5) / df[f'sma_{period}']
        
        # Medias móviles exponenciales
        for period in self.ema_periods:
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_ma'] = df['rsi'].rolling(10).mean()
        
        # MACD
        exp1 = df['close'].ewm(span=self.macd_fast).mean()
        exp2 = df['close'].ewm(span=self.macd_slow).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=self.macd_signal).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        df['macd_slope'] = df['macd'].diff(3)
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(self.bb_period).mean()
        bb_std = df['close'].rolling(self.bb_period).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * self.bb_std)
        df['bb_lower'] = df['bb_middle'] - (bb_std * self.bb_std)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Indicadores de tendencia
        df['trend_strength'] = self.calculate_trend_strength(df)
        df['momentum_score'] = self.calculate_momentum_score(df)
        
        # Indicadores de volumen
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['price_volume'] = df['close'] * df['volume']
        df['pv_trend'] = df['price_volume'].rolling(10).mean()
        
        # Volatilidad
        df['volatility'] = df['returns'].rolling(20).std()
        df['volatility_ma'] = df['volatility'].rolling(10).mean()
        df['atr'] = self.calculate_atr(df)
        
        # Indicadores de momentum avanzados
        df['stoch_k'] = self.calculate_stochastic_k(df)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        df['williams_r'] = self.calculate_williams_r(df)
        
        # Patrones de velas
        df['doji'] = self.detect_doji(df)
        df['hammer'] = self.detect_hammer(df)
        df['shooting_star'] = self.detect_shooting_star(df)
        
        # Niveles de soporte y resistencia
        df['support'] = df['low'].rolling(20).min()
        df['resistance'] = df['high'].rolling(20).max()
        df['support_strength'] = self.calculate_support_strength(df)
        df['resistance_strength'] = self.calculate_resistance_strength(df)
        
        return df

    def calculate_trend_strength(self, df):
        """Calcula la fuerza de la tendencia"""
        trend_scores = []
        
        for i in range(len(df)):
            if i < 50:
                trend_scores.append(0)
                continue
            
            score = 0
            current_price = df['close'].iloc[i]
            
            # Comparar con medias móviles
            for period in [10, 20, 50]:
                sma = df[f'sma_{period}'].iloc[i]
                if not pd.isna(sma):
                    if current_price > sma:
                        score += 1
                    else:
                        score -= 1
            
            # Pendiente de las medias
            for period in [10, 20]:
                slope = df[f'sma_{period}_slope'].iloc[i]
                if not pd.isna(slope):
                    if slope > 0:
                        score += 1
                    else:
                        score -= 1
            
            # Normalizar
            trend_scores.append(score / 5.0)
        
        return pd.Series(trend_scores, index=df.index)

    def calculate_momentum_score(self, df):
        """Calcula el score de momentum"""
        momentum_scores = []
        
        for i in range(len(df)):
            if i < 30:
                momentum_scores.append(0)
                continue
            
            score = 0
            
            # RSI
            rsi = df['rsi'].iloc[i]
            if not pd.isna(rsi):
                if 30 < rsi < 70:
                    score += 1
                elif rsi > 70:
                    score += 0.5
                elif rsi < 30:
                    score -= 0.5
            
            # MACD
            macd = df['macd'].iloc[i]
            macd_signal = df['macd_signal'].iloc[i]
            if not pd.isna(macd) and not pd.isna(macd_signal):
                if macd > macd_signal:
                    score += 1
                else:
                    score -= 1
            
            # Momentum de precios
            price_momentum = (df['close'].iloc[i] / df['close'].iloc[i-10] - 1) * 100
            if price_momentum > 2:
                score += 1
            elif price_momentum < -2:
                score -= 1
            
            momentum_scores.append(score / 3.0)
        
        return pd.Series(momentum_scores, index=df.index)

    def calculate_atr(self, df, period=14):
        """Calcula Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(period).mean()

    def calculate_stochastic_k(self, df, period=14):
        """Calcula Stochastic %K"""
        lowest_low = df['low'].rolling(period).min()
        highest_high = df['high'].rolling(period).max()
        k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        return k_percent

    def calculate_williams_r(self, df, period=14):
        """Calcula Williams %R"""
        highest_high = df['high'].rolling(period).max()
        lowest_low = df['low'].rolling(period).min()
        williams_r = -100 * ((highest_high - df['close']) / (highest_high - lowest_low))
        return williams_r

    def detect_doji(self, df):
        """Detecta patrones Doji"""
        body = abs(df['close'] - df['open'])
        range_size = df['high'] - df['low']
        return (body / range_size) < 0.1

    def detect_hammer(self, df):
        """Detecta patrones Hammer"""
        body = abs(df['close'] - df['open'])
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        return (lower_shadow > 2 * body) & (upper_shadow < body)

    def detect_shooting_star(self, df):
        """Detecta patrones Shooting Star"""
        body = abs(df['close'] - df['open'])
        lower_shadow = df[['open', 'close']].min(axis=1) - df['low']
        upper_shadow = df['high'] - df[['open', 'close']].max(axis=1)
        return (upper_shadow > 2 * body) & (lower_shadow < body)

    def calculate_support_strength(self, df):
        """Calcula la fuerza del soporte"""
        support_strength = []
        for i in range(len(df)):
            if i < 20:
                support_strength.append(0)
                continue
            
            current_low = df['low'].iloc[i]
            support_level = df['support'].iloc[i]
            
            if pd.isna(support_level):
                support_strength.append(0)
                continue
            
            # Contar cuántas veces el precio ha tocado este nivel
            touches = 0
            for j in range(max(0, i-20), i):
                if abs(df['low'].iloc[j] - support_level) / support_level < 0.02:
                    touches += 1
            
            support_strength.append(touches)
        
        return pd.Series(support_strength, index=df.index)

    def calculate_resistance_strength(self, df):
        """Calcula la fuerza de la resistencia"""
        resistance_strength = []
        for i in range(len(df)):
            if i < 20:
                resistance_strength.append(0)
                continue
            
            current_high = df['high'].iloc[i]
            resistance_level = df['resistance'].iloc[i]
            
            if pd.isna(resistance_level):
                resistance_strength.append(0)
                continue
            
            # Contar cuántas veces el precio ha tocado este nivel
            touches = 0
            for j in range(max(0, i-20), i):
                if abs(df['high'].iloc[j] - resistance_level) / resistance_level < 0.02:
                    touches += 1
            
            resistance_strength.append(touches)
        
        return pd.Series(resistance_strength, index=df.index)

    def train_ml_models(self, data):
        """Entrena los modelos de machine learning"""
        if len(data) < 100:
            return
        
        try:
            # Preparar features
            feature_cols = [
                'rsi', 'macd', 'bb_position', 'trend_strength', 'momentum_score',
                'volume_ratio', 'volatility', 'stoch_k', 'williams_r',
                'support_strength', 'resistance_strength'
            ]
            
            X = data[feature_cols].dropna()
            
            # Crear target (movimiento futuro de 5 días)
            future_returns = data['close'].shift(-5) / data['close'] - 1
            conditions = [
                future_returns <= -0.03,  # Bajada fuerte
                (future_returns > -0.03) & (future_returns < 0.03),  # Lateral
                future_returns >= 0.03   # Subida fuerte
            ]
            y = np.select(conditions, [0, 1, 2], default=1)
            y = pd.Series(y, index=data.index)
            
            # Alinear X e y
            common_idx = X.index.intersection(y.index)
            X = X.loc[common_idx]
            y = y.loc[common_idx]
            
            if len(X) < 50:
                return
            
            # Entrenar modelos
            X_scaled = self.scaler.fit_transform(X)
            
            self.rf_model.fit(X_scaled, y)
            self.gb_model.fit(X_scaled, y)
            
            # Evaluar modelos
            rf_pred = self.rf_model.predict(X_scaled)
            gb_pred = self.gb_model.predict(X_scaled)
            
            rf_accuracy = accuracy_score(y, rf_pred)
            gb_accuracy = accuracy_score(y, gb_pred)
            
            self.models_trained = True
            
            logging.info(f"🧠 Modelos ML entrenados:")
            logging.info(f"  RandomForest accuracy: {rf_accuracy:.3f}")
            logging.info(f"  GradientBoosting accuracy: {gb_accuracy:.3f}")
            
        except Exception as e:
            logging.warning(f"Error entrenando modelos ML: {e}")

    def generate_daily_signal(self, data, idx):
        """Genera señal de trading para timeframes diarios"""
        if idx < 100:  # Necesitamos suficiente historia
            return {'signal': 'HOLD', 'confidence': 0, 'reasons': []}
        
        current = data.iloc[idx]
        reasons = []
        signal_score = 0
        confidence_factors = []
        
        # 1. Análisis de tendencia
        trend_strength = current['trend_strength']
        if not pd.isna(trend_strength):
            if trend_strength > self.trend_strength_threshold:
                signal_score += 2
                reasons.append(f"Tendencia alcista fuerte ({trend_strength:.2f})")
                confidence_factors.append(abs(trend_strength))
            elif trend_strength < -self.trend_strength_threshold:
                signal_score -= 2
                reasons.append(f"Tendencia bajista fuerte ({trend_strength:.2f})")
                confidence_factors.append(abs(trend_strength))
        
        # 2. Análisis de momentum
        momentum_score = current['momentum_score']
        if not pd.isna(momentum_score):
            if momentum_score > self.momentum_threshold:
                signal_score += 1
                reasons.append(f"Momentum positivo ({momentum_score:.2f})")
                confidence_factors.append(momentum_score)
            elif momentum_score < -self.momentum_threshold:
                signal_score -= 1
                reasons.append(f"Momentum negativo ({momentum_score:.2f})")
                confidence_factors.append(abs(momentum_score))
        
        # 3. RSI
        rsi = current['rsi']
        if not pd.isna(rsi):
            if rsi < 30:
                signal_score += 1
                reasons.append(f"RSI sobreventa ({rsi:.1f})")
                confidence_factors.append((30 - rsi) / 30)
            elif rsi > 70:
                signal_score -= 1
                reasons.append(f"RSI sobrecompra ({rsi:.1f})")
                confidence_factors.append((rsi - 70) / 30)
        
        # 4. MACD
        macd = current['macd']
        macd_signal = current['macd_signal']
        macd_histogram = current['macd_histogram']
        
        if not pd.isna(macd) and not pd.isna(macd_signal):
            if macd > macd_signal and macd_histogram > 0:
                signal_score += 1
                reasons.append("MACD alcista")
                confidence_factors.append(0.7)
            elif macd < macd_signal and macd_histogram < 0:
                signal_score -= 1
                reasons.append("MACD bajista")
                confidence_factors.append(0.7)
        
        # 5. Bollinger Bands
        bb_position = current['bb_position']
        if not pd.isna(bb_position):
            if bb_position < 0.2:
                signal_score += 1
                reasons.append(f"Precio cerca banda inferior ({bb_position:.2f})")
                confidence_factors.append(0.2 - bb_position)
            elif bb_position > 0.8:
                signal_score -= 1
                reasons.append(f"Precio cerca banda superior ({bb_position:.2f})")
                confidence_factors.append(bb_position - 0.8)
        
        # 6. Volumen
        volume_ratio = current['volume_ratio']
        if not pd.isna(volume_ratio) and volume_ratio > self.volume_threshold:
            if signal_score > 0:
                signal_score += 0.5
                reasons.append(f"Volumen alto confirma señal ({volume_ratio:.2f})")
                confidence_factors.append(min(volume_ratio / 3, 1))
        
        # 7. Machine Learning
        if self.models_trained:
            ml_signal = self.get_ml_prediction(data, idx)
            if ml_signal['prediction'] == 2:  # Compra
                signal_score += 1
                reasons.append(f"ML predice subida (conf: {ml_signal['confidence']:.2f})")
                confidence_factors.append(ml_signal['confidence'])
            elif ml_signal['prediction'] == 0:  # Venta
                signal_score -= 1
                reasons.append(f"ML predice bajada (conf: {ml_signal['confidence']:.2f})")
                confidence_factors.append(ml_signal['confidence'])
        
        # 8. Soporte y Resistencia
        support_strength = current['support_strength']
        resistance_strength = current['resistance_strength']
        
        if not pd.isna(support_strength) and support_strength > 2:
            signal_score += 0.5
            reasons.append(f"Soporte fuerte ({support_strength})")
            confidence_factors.append(min(support_strength / 5, 1))
        
        if not pd.isna(resistance_strength) and resistance_strength > 2:
            signal_score -= 0.5
            reasons.append(f"Resistencia fuerte ({resistance_strength})")
            confidence_factors.append(min(resistance_strength / 5, 1))
        
        # Calcular confianza
        confidence = np.mean(confidence_factors) if confidence_factors else 0
        confidence = min(confidence, 0.95)
        
        # Decisión final
        if signal_score >= 3:
            return {
                'signal': 'BUY',
                'confidence': confidence,
                'score': signal_score,
                'reasons': reasons
            }
        elif signal_score <= -3:
            return {
                'signal': 'SELL',
                'confidence': confidence,
                'score': signal_score,
                'reasons': reasons
            }
        else:
            return {
                'signal': 'HOLD',
                'confidence': 0,
                'score': signal_score,
                'reasons': reasons
            }

    def get_ml_prediction(self, data, idx):
        """Obtiene predicción de machine learning"""
        try:
            feature_cols = [
                'rsi', 'macd', 'bb_position', 'trend_strength', 'momentum_score',
                'volume_ratio', 'volatility', 'stoch_k', 'williams_r',
                'support_strength', 'resistance_strength'
            ]
            
            features = []
            current = data.iloc[idx]
            
            for col in feature_cols:
                value = current[col]
                if pd.isna(value):
                    return {'prediction': 1, 'confidence': 0}
                features.append(value)
            
            # Predecir con ambos modelos
            features_scaled = self.scaler.transform([features])
            
            rf_pred = self.rf_model.predict(features_scaled)[0]
            gb_pred = self.gb_model.predict(features_scaled)[0]
            
            rf_proba = np.max(self.rf_model.predict_proba(features_scaled)[0])
            gb_proba = np.max(self.gb_model.predict_proba(features_scaled)[0])
            
            # Ensemble prediction
            if rf_pred == gb_pred:
                prediction = rf_pred
                confidence = (rf_proba + gb_proba) / 2
            else:
                # En caso de desacuerdo, usar el más confiado
                if rf_proba > gb_proba:
                    prediction = rf_pred
                    confidence = rf_proba * 0.8  # Reducir confianza por desacuerdo
                else:
                    prediction = gb_pred
                    confidence = gb_proba * 0.8
            
            return {'prediction': prediction, 'confidence': confidence}
            
        except Exception as e:
            logging.warning(f"Error en predicción ML: {e}")
            return {'prediction': 1, 'confidence': 0}

    def calculate_position_size(self, signal_data, current_price):
        """Calcula el tamaño de posición optimizado"""
        base_size = self.current_capital * self.position_size_pct
        
        # Ajustar por confianza
        confidence_multiplier = signal_data['confidence']
        
        # Ajustar por volatilidad (menor posición en alta volatilidad)
        volatility_adjustment = 1.0  # Por defecto
        
        # Tamaño final con apalancamiento
        position_size = base_size * confidence_multiplier * volatility_adjustment * self.leverage
        
        # Limitar tamaño máximo
        max_size = self.current_capital * self.leverage * 0.6
        return min(position_size, max_size)

    def execute_trade(self, signal_data, current_price, timestamp, symbol):
        """Ejecuta una operación de trading"""
        if signal_data['signal'] == 'HOLD':
            return
        
        if len(self.positions) >= self.max_positions:
            return
        
        position_size = self.calculate_position_size(signal_data, current_price)
        
        if position_size < 100:  # Mínimo $100 para largo plazo
            return
        
        quantity = position_size / current_price
        fee = position_size * self.fee_rate
        
        # Actualizar capital
        self.current_capital -= (position_size + fee)
        self.total_fees += fee
        
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
            'score': signal_data['score'],
            'reasons': signal_data['reasons'],
            'stop_loss': current_price * (0.95 if signal_data['signal'] == 'BUY' else 1.05),
            'take_profit': current_price * (1.15 if signal_data['signal'] == 'BUY' else 0.85)
        }
        
        self.positions[position_id] = position
        
        # Registrar operación
        operation = {
            'timestamp': timestamp,
            'symbol': symbol,
            'type': f"{signal_data['signal']}_DAILY",
            'price': current_price,
            'quantity': quantity,
            'size': position_size,
            'fee': fee,
            'confidence': signal_data['confidence'],
            'score': signal_data['score'],
            'capital_after': self.current_capital,
            'position_id': position_id,
            'reasons': '; '.join(signal_data['reasons'])
        }
        
        self.operations.append(operation)
        
        logging.info(f"📊 DAILY {signal_data['signal']}: {symbol} ${position_size:.2f} @ ${current_price:.2f}")
        logging.info(f"   Score: {signal_data['score']:.1f} | Conf: {signal_data['confidence']:.3f}")
        logging.info(f"   Razones: {'; '.join(signal_data['reasons'][:3])}")

    def manage_positions(self, current_prices, timestamp):
        """Gestiona las posiciones abiertas"""
        positions_to_close = []
        
        for position_id, position in self.positions.items():
            symbol = position['symbol']
            current_price = current_prices.get(symbol, position['entry_price'])
            
            # Calcular PnL
            if position['type'] == 'BUY':
                pnl_pct = (current_price - position['entry_price']) / position['entry_price']
            else:  # SELL
                pnl_pct = (position['entry_price'] - current_price) / position['entry_price']
            
            # Stop loss
            if ((position['type'] == 'BUY' and current_price <= position['stop_loss']) or
                (position['type'] == 'SELL' and current_price >= position['stop_loss'])):
                positions_to_close.append((position_id, current_price, "stop_loss"))
            
            # Take profit
            elif ((position['type'] == 'BUY' and current_price >= position['take_profit']) or
                  (position['type'] == 'SELL' and current_price <= position['take_profit'])):
                positions_to_close.append((position_id, current_price, "take_profit"))
        
        # Cerrar posiciones
        for position_id, price, reason in positions_to_close:
            self.close_position(position_id, price, timestamp, reason)

    def close_position(self, position_id, current_price, timestamp, reason="signal"):
        """Cierra una posición"""
        if position_id not in self.positions:
            return
        
        position = self.positions[position_id]
        
        # Calcular PnL
        if position['type'] == 'BUY':
            pnl = (current_price - position['entry_price']) * position['quantity']
        else:  # SELL
            pnl = (position['entry_price'] - current_price) * position['quantity']
        
        # Fees de cierre
        close_size = position['quantity'] * current_price
        close_fee = close_size * self.fee_rate
        net_pnl = pnl - close_fee
        
        # Actualizar capital
        self.current_capital += (position['size'] + net_pnl)
        self.total_fees += close_fee
        
        # Actualizar peak y drawdown
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
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
            'reason': reason
        }
        
        self.operations.append(operation)
        
        # Eliminar posición
        del self.positions[position_id]
        
        pnl_pct = (net_pnl / position['size']) * 100
        logging.info(f"🔚 CLOSE {position['type']}: {position['symbol']} PnL ${net_pnl:.2f} ({pnl_pct:.1f}%) | Reason: {reason}")

    def run_backtest(self, days=90):
        """Ejecuta backtest con timeframes diarios"""
        logging.info(f"🔄 Iniciando backtest Daily Timeframes para {len(self.symbols)} símbolos")
        
        # Obtener datos diarios para todos los símbolos
        all_data = {}
        fetcher = RobustDataFetcher()
        
        for symbol in self.symbols:
            data = fetcher.get_market_data(symbol, '1d', limit=days+50)  # Más días para indicadores
            if data is not None and not data.empty:
                data.columns = data.columns.str.lower()
                if data.index.name == 'timestamp' or 'timestamp' in str(data.index.name).lower():
                    data.reset_index(inplace=True)
                
                # Calcular indicadores avanzados
                data_with_indicators = self.calculate_advanced_indicators(data)
                all_data[symbol] = data_with_indicators
                
                logging.info(f"📊 {symbol}: {len(data)} velas diarias obtenidas")
        
        if not all_data:
            logging.error("❌ No se pudieron obtener datos")
            return
        
        # Entrenar modelos ML con el primer símbolo
        first_symbol = list(all_data.keys())[0]
        self.train_ml_models(all_data[first_symbol])
        
        # Determinar longitud mínima
        min_length = min(len(data) for data in all_data.values())
        
        logging.info("🔄 Iniciando backtest con timeframes diarios...")
        
        # Backtest
        for idx in range(100, min_length):
            current_prices = {}
            
            # Obtener precios actuales
            for symbol, data in all_data.items():
                current_prices[symbol] = data['close'].iloc[idx]
            
            timestamp = all_data[first_symbol].get('timestamp', pd.Series([idx])).iloc[idx]
            
            # Generar señales para cada símbolo
            for symbol, data in all_data.items():
                current_price = current_prices[symbol]
                
                # Generar señal diaria
                signal_data = self.generate_daily_signal(data, idx)
                
                # Ejecutar trade
                self.execute_trade(signal_data, current_price, timestamp, symbol)
            
            # Gestionar posiciones
            self.manage_positions(current_prices, timestamp)
            
            # Registrar retorno diario
            daily_return = (self.current_capital - self.initial_capital) / self.initial_capital
            self.daily_returns.append(daily_return)
        
        # Cerrar todas las posiciones al final
        final_prices = {symbol: data['close'].iloc[-1] for symbol, data in all_data.items()}
        for position_id in list(self.positions.keys()):
            position = self.positions[position_id]
            final_price = final_prices[position['symbol']]
            self.close_position(position_id, final_price, min_length-1, "backtest_end")
        
        # Calcular métricas finales
        self.calculate_final_metrics(days)

    def calculate_final_metrics(self, days):
        """Calcula métricas finales del backtest"""
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
        
        # Sharpe ratio
        if self.daily_returns:
            returns_array = np.array(self.daily_returns)
            sharpe_ratio = np.mean(returns_array) / np.std(returns_array) * np.sqrt(365) if np.std(returns_array) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Logging de resultados
        logging.info("=" * 80)
        logging.info("RESULTADOS SISTEMA DAILY TIMEFRAMES SICAR")
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
        logging.info(f"📅 Duración: {days} días ({months:.1f} meses)")
        logging.info(f"⚡ Apalancamiento: {self.leverage}x")
        logging.info(f"📉 Max Drawdown: {self.max_drawdown:.2f}%")
        logging.info(f"📊 Sharpe Ratio: {sharpe_ratio:.2f}")
        logging.info(f"⚡ Gap al objetivo: {roi_gap:.2f}% (Objetivo: {target_roi}%)")
        logging.info("=" * 80)
        
        # Guardar resultados
        self.save_results()
        
        # Resumen final
        print(f"\n✅ Backtest Daily Timeframes completado!")
        print(f"📊 ROI mensual: {monthly_roi:.2f}%")
        print(f"🎯 Objetivo: {target_roi}%")
        print(f"🔄 Total operaciones: {total_operations}")
        print(f"🏆 Win rate: {win_rate:.1f}%")
        print(f"⚡ Apalancamiento: {self.leverage}x")
        print(f"📉 Max Drawdown: {self.max_drawdown:.2f}%")
        print(f"📁 Resultados guardados en: daily_timeframe_sicar_results.csv")

    def save_results(self):
        """Guarda los resultados en CSV"""
        if self.operations:
            df = pd.DataFrame(self.operations)
            df.to_csv('daily_timeframe_sicar_results.csv', index=False)
            logging.info("💾 Resultados guardados en daily_timeframe_sicar_results.csv")

def main():
    """Función principal"""
    try:
        # Crear y ejecutar sistema de timeframes diarios
        system = DailyTimeframeSicarSystem(
            initial_capital=500,
            leverage=12.0  # Apalancamiento optimizado para largo plazo
        )
        
        # Ejecutar backtest de 90 días
        system.run_backtest(days=90)
        
    except Exception as e:
        logging.error(f"❌ Error en sistema daily timeframes: {str(e)}")
        raise

if __name__ == "__main__":
    main()