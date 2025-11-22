#!/usr/bin/env python3
"""
Sistema SICAR Optimizado - Versión Final Mejorada
Combina los mejores elementos de Momentum Agresivo + Timeframes Diarios
Sin apalancamiento, con ML optimizado y gestión de riesgo avanzada
Objetivo: 15% ROI mensual
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Importaciones para ML y análisis técnico
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import classification_report, accuracy_score
import talib
from scipy import stats
from scipy.signal import find_peaks
import yfinance as yf

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sicar_optimized_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SICAROptimizedSystem:
    def __init__(self):
        """Inicializar el sistema SICAR optimizado"""
        self.symbols = ['ETHUSDT', 'BTCUSDT', 'ADAUSDT', 'SOLUSDT', 'XRPUSDT', 'LINKUSDT', 'LTCUSDT']
        self.timeframes = ['15m', '1h', '4h', '1d']
        self.initial_balance = 10000.0
        self.current_balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.ml_models = {}
        self.scalers = {}
        
        # Parámetros optimizados sin apalancamiento
        self.max_position_size = 0.15  # 15% máximo por posición
        self.stop_loss_pct = 0.03      # 3% stop loss
        self.take_profit_pct = 0.08    # 8% take profit
        self.min_confidence = 0.75     # Confianza mínima para operar
        self.max_daily_trades = 5      # Máximo 5 trades por día
        self.max_drawdown = 0.10       # 10% máximo drawdown
        
        # Contadores y métricas
        self.daily_trades = 0
        self.last_trade_date = None
        self.peak_balance = self.initial_balance
        self.max_drawdown_reached = 0
        
        logger.info("Sistema SICAR Optimizado inicializado sin apalancamiento")

    def fetch_historical_data(self, symbol, timeframe, days=365):
        """Obtener datos históricos extendidos para backtesting robusto"""
        try:
            # Mapeo de timeframes
            tf_map = {
                '15m': '15m',
                '1h': '1h', 
                '4h': '4h',
                '1d': '1d'
            }
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Usar yfinance para datos más extensos
            ticker = symbol.replace('USDT', '-USD')
            data = yf.download(ticker, start=start_date, end=end_date, interval=tf_map[timeframe])
            
            if data.empty:
                logger.warning(f"No se pudieron obtener datos para {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Renombrar columnas para consistencia
            data.columns = ['open', 'high', 'low', 'close', 'adj_close', 'volume']
            data = data.drop('adj_close', axis=1)
            data.reset_index(inplace=True)
            data.rename(columns={'Date': 'timestamp'}, inplace=True)
            
            logger.info(f"Datos obtenidos para {symbol} {timeframe}: {len(data)} registros")
            return data
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol} {timeframe}: {e}")
            return pd.DataFrame()

    def calculate_advanced_indicators(self, df):
        """Calcular indicadores técnicos avanzados con mayor precisión"""
        if len(df) < 50:
            return df
        
        try:
            # Indicadores básicos mejorados
            df['sma_20'] = talib.SMA(df['close'], timeperiod=20)
            df['sma_50'] = talib.SMA(df['close'], timeperiod=50)
            df['ema_12'] = talib.EMA(df['close'], timeperiod=12)
            df['ema_26'] = talib.EMA(df['close'], timeperiod=26)
            
            # RSI con múltiples períodos
            df['rsi_14'] = talib.RSI(df['close'], timeperiod=14)
            df['rsi_21'] = talib.RSI(df['close'], timeperiod=21)
            
            # MACD mejorado
            macd, macd_signal, macd_hist = talib.MACD(df['close'])
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_hist
            
            # Bollinger Bands con desviaciones múltiples
            bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'], timeperiod=20, nbdevup=2, nbdevdn=2)
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            df['bb_width'] = (bb_upper - bb_lower) / bb_middle
            df['bb_position'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
            
            # ATR para volatilidad
            df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
            df['atr_pct'] = df['atr'] / df['close']
            
            # Stochastic mejorado
            slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'])
            df['stoch_k'] = slowk
            df['stoch_d'] = slowd
            
            # Williams %R
            df['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'])
            
            # CCI (Commodity Channel Index)
            df['cci'] = talib.CCI(df['high'], df['low'], df['close'])
            
            # ADX para fuerza de tendencia
            df['adx'] = talib.ADX(df['high'], df['low'], df['close'])
            
            # Momentum indicators
            df['momentum'] = talib.MOM(df['close'], timeperiod=10)
            df['roc'] = talib.ROC(df['close'], timeperiod=10)
            
            # Volume indicators
            df['volume_sma'] = talib.SMA(df['volume'], timeperiod=20)
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price patterns
            df['doji'] = talib.CDLDOJI(df['open'], df['high'], df['low'], df['close'])
            df['hammer'] = talib.CDLHAMMER(df['open'], df['high'], df['low'], df['close'])
            df['shooting_star'] = talib.CDLSHOOTINGSTAR(df['open'], df['high'], df['low'], df['close'])
            
            # Support/Resistance levels
            df = self.calculate_support_resistance(df)
            
            # Trend strength
            df['trend_strength'] = self.calculate_trend_strength(df)
            
            # Market regime detection
            df['market_regime'] = self.detect_market_regime(df)
            
            return df.fillna(method='ffill').fillna(0)
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {e}")
            return df

    def calculate_support_resistance(self, df):
        """Calcular niveles de soporte y resistencia dinámicos"""
        try:
            window = min(20, len(df) // 4)
            if window < 5:
                df['support'] = df['low']
                df['resistance'] = df['high']
                return df
            
            # Encontrar mínimos y máximos locales
            lows = df['low'].rolling(window=window, center=True).min()
            highs = df['high'].rolling(window=window, center=True).max()
            
            df['support'] = lows
            df['resistance'] = highs
            
            # Distancia a soporte/resistencia
            df['dist_to_support'] = (df['close'] - df['support']) / df['close']
            df['dist_to_resistance'] = (df['resistance'] - df['close']) / df['close']
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando soporte/resistencia: {e}")
            df['support'] = df['low']
            df['resistance'] = df['high']
            df['dist_to_support'] = 0
            df['dist_to_resistance'] = 0
            return df

    def calculate_trend_strength(self, df):
        """Calcular fuerza de tendencia"""
        try:
            if len(df) < 20:
                return pd.Series([0] * len(df), index=df.index)
            
            # Pendiente de SMA
            sma_slope = df['sma_20'].diff(5) / df['sma_20']
            
            # Consistencia de dirección
            price_direction = np.sign(df['close'].diff())
            consistency = price_direction.rolling(10).mean().abs()
            
            # Volumen confirmación
            volume_trend = df['volume_ratio'].rolling(5).mean()
            
            trend_strength = (sma_slope.abs() * consistency * np.log1p(volume_trend)).fillna(0)
            return trend_strength
            
        except Exception as e:
            logger.error(f"Error calculando fuerza de tendencia: {e}")
            return pd.Series([0] * len(df), index=df.index)

    def detect_market_regime(self, df):
        """Detectar régimen de mercado (trending, ranging, volatile)"""
        try:
            if len(df) < 20:
                return pd.Series(['ranging'] * len(df), index=df.index)
            
            # Volatilidad
            volatility = df['atr_pct'].rolling(10).mean()
            
            # Tendencia
            trend = df['trend_strength']
            
            # Clasificar régimen
            regimes = []
            for i in range(len(df)):
                if trend.iloc[i] > 0.02 and volatility.iloc[i] < 0.05:
                    regimes.append('trending')
                elif volatility.iloc[i] > 0.08:
                    regimes.append('volatile')
                else:
                    regimes.append('ranging')
            
            return pd.Series(regimes, index=df.index)
            
        except Exception as e:
            logger.error(f"Error detectando régimen de mercado: {e}")
            return pd.Series(['ranging'] * len(df), index=df.index)

    def create_ml_features(self, df):
        """Crear features avanzadas para ML"""
        try:
            features = []
            
            # Features técnicos
            feature_cols = [
                'rsi_14', 'rsi_21', 'macd', 'macd_histogram', 'bb_position', 'bb_width',
                'stoch_k', 'stoch_d', 'williams_r', 'cci', 'adx', 'momentum', 'roc',
                'volume_ratio', 'atr_pct', 'dist_to_support', 'dist_to_resistance',
                'trend_strength'
            ]
            
            for col in feature_cols:
                if col in df.columns:
                    features.append(df[col])
            
            # Features de precio
            features.append(df['close'].pct_change(1))  # Retorno 1 período
            features.append(df['close'].pct_change(5))  # Retorno 5 períodos
            features.append(df['close'].pct_change(10)) # Retorno 10 períodos
            
            # Features de volatilidad
            features.append(df['close'].rolling(10).std() / df['close'])
            features.append(df['high'].rolling(5).max() / df['close'] - 1)
            features.append(df['close'] / df['low'].rolling(5).min() - 1)
            
            # Features de volumen
            features.append(np.log1p(df['volume']))
            features.append(df['volume'].rolling(5).std() / df['volume'].rolling(5).mean())
            
            # Features de momentum
            for period in [3, 7, 14]:
                features.append(df['close'].rolling(period).mean() / df['close'] - 1)
            
            # Features de patrones
            features.append(df['doji'])
            features.append(df['hammer'])
            features.append(df['shooting_star'])
            
            # Combinar features
            feature_matrix = pd.concat(features, axis=1)
            feature_matrix.columns = [f'feature_{i}' for i in range(len(features))]
            
            return feature_matrix.fillna(0)
            
        except Exception as e:
            logger.error(f"Error creando features ML: {e}")
            return pd.DataFrame()

    def create_targets(self, df, lookahead=5):
        """Crear targets para ML con múltiples horizontes"""
        try:
            targets = []
            
            # Target principal: retorno futuro
            future_return = df['close'].shift(-lookahead) / df['close'] - 1
            
            # Clasificar en señales
            buy_threshold = 0.02   # 2% ganancia mínima para BUY
            sell_threshold = -0.015 # 1.5% pérdida para SELL
            
            signals = []
            for ret in future_return:
                if pd.isna(ret):
                    signals.append(0)  # HOLD
                elif ret > buy_threshold:
                    signals.append(1)  # BUY
                elif ret < sell_threshold:
                    signals.append(-1) # SELL
                else:
                    signals.append(0)  # HOLD
            
            return pd.Series(signals, index=df.index)
            
        except Exception as e:
            logger.error(f"Error creando targets: {e}")
            return pd.Series([0] * len(df), index=df.index)

    def train_ml_models(self, symbol, df):
        """Entrenar modelos ML optimizados con ensemble"""
        try:
            logger.info(f"Entrenando modelos ML para {symbol}")
            
            # Crear features y targets
            features = self.create_ml_features(df)
            targets = self.create_targets(df)
            
            if len(features) < 100:
                logger.warning(f"Datos insuficientes para entrenar ML en {symbol}")
                return False
            
            # Filtrar datos válidos
            valid_idx = ~(features.isna().any(axis=1) | targets.isna())
            X = features[valid_idx]
            y = targets[valid_idx]
            
            if len(X) < 50:
                logger.warning(f"Datos válidos insuficientes para {symbol}")
                return False
            
            # Split temporal
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Escalado robusto
            scaler = RobustScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Modelos base optimizados
            rf = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                min_samples_split=10,
                min_samples_leaf=5,
                random_state=42,
                n_jobs=-1
            )
            
            gb = GradientBoostingClassifier(
                n_estimators=150,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                random_state=42
            )
            
            lr = LogisticRegression(
                random_state=42,
                max_iter=1000,
                C=1.0
            )
            
            # Ensemble con voting
            ensemble = VotingClassifier(
                estimators=[('rf', rf), ('gb', gb), ('lr', lr)],
                voting='soft'
            )
            
            # Entrenar ensemble
            ensemble.fit(X_train_scaled, y_train)
            
            # Evaluar
            y_pred = ensemble.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Modelo {symbol} - Accuracy: {accuracy:.3f}")
            
            # Guardar modelo y scaler
            self.ml_models[symbol] = ensemble
            self.scalers[symbol] = scaler
            
            return True
            
        except Exception as e:
            logger.error(f"Error entrenando modelo para {symbol}: {e}")
            return False

    def generate_momentum_signals(self, df):
        """Generar señales de momentum agresivo mejoradas"""
        try:
            if len(df) < 20:
                return pd.Series([0] * len(df), index=df.index)
            
            signals = []
            
            for i in range(len(df)):
                score = 0
                
                # RSI momentum
                if df['rsi_14'].iloc[i] < 30 and df['rsi_14'].iloc[i] > df['rsi_14'].iloc[i-1]:
                    score += 2
                elif df['rsi_14'].iloc[i] > 70 and df['rsi_14'].iloc[i] < df['rsi_14'].iloc[i-1]:
                    score -= 2
                
                # MACD momentum
                if df['macd'].iloc[i] > df['macd_signal'].iloc[i] and df['macd_histogram'].iloc[i] > 0:
                    score += 1
                elif df['macd'].iloc[i] < df['macd_signal'].iloc[i] and df['macd_histogram'].iloc[i] < 0:
                    score -= 1
                
                # Bollinger Bands
                if df['bb_position'].iloc[i] < 0.2 and df['close'].iloc[i] > df['bb_lower'].iloc[i]:
                    score += 1
                elif df['bb_position'].iloc[i] > 0.8 and df['close'].iloc[i] < df['bb_upper'].iloc[i]:
                    score -= 1
                
                # Trend strength
                if df['trend_strength'].iloc[i] > 0.01:
                    score += 1
                elif df['trend_strength'].iloc[i] < -0.01:
                    score -= 1
                
                # Volume confirmation
                if df['volume_ratio'].iloc[i] > 1.5:
                    score += 1
                
                # ADX strength
                if df['adx'].iloc[i] > 25:
                    score += 1
                
                # Market regime
                if df['market_regime'].iloc[i] == 'trending':
                    score += 1
                elif df['market_regime'].iloc[i] == 'volatile':
                    score -= 1
                
                # Generar señal
                if score >= 4:
                    signals.append(1)  # BUY
                elif score <= -4:
                    signals.append(-1) # SELL
                else:
                    signals.append(0)  # HOLD
            
            return pd.Series(signals, index=df.index)
            
        except Exception as e:
            logger.error(f"Error generando señales momentum: {e}")
            return pd.Series([0] * len(df), index=df.index)

    def generate_ml_signals(self, symbol, df):
        """Generar señales ML con confianza"""
        try:
            if symbol not in self.ml_models:
                return pd.Series([0] * len(df), index=df.index), pd.Series([0] * len(df), index=df.index)
            
            features = self.create_ml_features(df)
            if features.empty:
                return pd.Series([0] * len(df), index=df.index), pd.Series([0] * len(df), index=df.index)
            
            # Escalar features
            features_scaled = self.scalers[symbol].transform(features.fillna(0))
            
            # Predicciones
            predictions = self.ml_models[symbol].predict(features_scaled)
            probabilities = self.ml_models[symbol].predict_proba(features_scaled)
            
            # Calcular confianza
            confidences = []
            for prob in probabilities:
                max_prob = np.max(prob)
                confidences.append(max_prob)
            
            return pd.Series(predictions, index=df.index), pd.Series(confidences, index=df.index)
            
        except Exception as e:
            logger.error(f"Error generando señales ML para {symbol}: {e}")
            return pd.Series([0] * len(df), index=df.index), pd.Series([0] * len(df), index=df.index)

    def combine_signals(self, momentum_signals, ml_signals, ml_confidence):
        """Combinar señales con pesos optimizados"""
        try:
            combined_signals = []
            combined_confidence = []
            
            for i in range(len(momentum_signals)):
                momentum_sig = momentum_signals.iloc[i]
                ml_sig = ml_signals.iloc[i]
                ml_conf = ml_confidence.iloc[i]
                
                # Pesos dinámicos
                momentum_weight = 0.6
                ml_weight = 0.4 * ml_conf  # Peso ML basado en confianza
                
                # Combinar señales
                if momentum_sig == ml_sig and momentum_sig != 0:
                    # Señales coinciden
                    final_signal = momentum_sig
                    final_confidence = min(0.9, momentum_weight + ml_weight)
                elif momentum_sig != 0 and ml_sig == 0:
                    # Solo momentum
                    final_signal = momentum_sig
                    final_confidence = momentum_weight
                elif ml_sig != 0 and momentum_sig == 0 and ml_conf > 0.7:
                    # Solo ML con alta confianza
                    final_signal = ml_sig
                    final_confidence = ml_weight
                else:
                    # Señales conflictivas o débiles
                    final_signal = 0
                    final_confidence = 0
                
                combined_signals.append(final_signal)
                combined_confidence.append(final_confidence)
            
            return pd.Series(combined_signals), pd.Series(combined_confidence)
            
        except Exception as e:
            logger.error(f"Error combinando señales: {e}")
            return pd.Series([0] * len(momentum_signals)), pd.Series([0] * len(momentum_signals))

    def calculate_position_size(self, signal, confidence, current_price, volatility):
        """Calcular tamaño de posición dinámico sin apalancamiento"""
        try:
            if signal == 0 or confidence < self.min_confidence:
                return 0
            
            # Tamaño base
            base_size = self.max_position_size
            
            # Ajustar por confianza
            confidence_multiplier = min(confidence / 0.8, 1.2)
            
            # Ajustar por volatilidad (menor volatilidad = mayor posición)
            volatility_multiplier = max(0.5, min(1.5, 1 / (1 + volatility * 10)))
            
            # Calcular tamaño final
            position_size = base_size * confidence_multiplier * volatility_multiplier
            
            # Limitar tamaño máximo
            position_size = min(position_size, self.max_position_size)
            
            # Calcular cantidad en USD
            position_value = self.current_balance * position_size
            
            return position_value / current_price
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return 0

    def check_risk_management(self):
        """Verificar gestión de riesgo avanzada"""
        try:
            # Verificar drawdown
            current_drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if current_drawdown > self.max_drawdown:
                logger.warning(f"Drawdown máximo alcanzado: {current_drawdown:.2%}")
                return False
            
            # Verificar límite de trades diarios
            current_date = datetime.now().date()
            if self.last_trade_date != current_date:
                self.daily_trades = 0
                self.last_trade_date = current_date
            
            if self.daily_trades >= self.max_daily_trades:
                logger.info("Límite de trades diarios alcanzado")
                return False
            
            # Actualizar peak balance
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
            
            return True
            
        except Exception as e:
            logger.error(f"Error en gestión de riesgo: {e}")
            return False

    def execute_trade(self, symbol, signal, quantity, price, confidence):
        """Ejecutar trade con gestión de riesgo"""
        try:
            if not self.check_risk_management():
                return False
            
            trade_value = quantity * price
            
            # Verificar balance suficiente
            if signal == 1 and trade_value > self.current_balance * 0.95:
                logger.warning(f"Balance insuficiente para {symbol}")
                return False
            
            # Calcular stop loss y take profit
            if signal == 1:  # BUY
                stop_loss = price * (1 - self.stop_loss_pct)
                take_profit = price * (1 + self.take_profit_pct)
            else:  # SELL
                stop_loss = price * (1 + self.stop_loss_pct)
                take_profit = price * (1 - self.take_profit_pct)
            
            # Registrar trade
            trade = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'signal': 'BUY' if signal == 1 else 'SELL',
                'quantity': quantity,
                'price': price,
                'value': trade_value,
                'confidence': confidence,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'status': 'OPEN'
            }
            
            self.trades.append(trade)
            self.daily_trades += 1
            
            # Actualizar posiciones
            if symbol not in self.positions:
                self.positions[symbol] = {'quantity': 0, 'avg_price': 0}
            
            if signal == 1:  # BUY
                old_quantity = self.positions[symbol]['quantity']
                old_value = old_quantity * self.positions[symbol]['avg_price']
                new_quantity = old_quantity + quantity
                new_value = old_value + trade_value
                
                self.positions[symbol]['quantity'] = new_quantity
                self.positions[symbol]['avg_price'] = new_value / new_quantity if new_quantity > 0 else 0
                self.current_balance -= trade_value
                
            else:  # SELL
                self.positions[symbol]['quantity'] -= quantity
                if self.positions[symbol]['quantity'] <= 0:
                    self.positions[symbol] = {'quantity': 0, 'avg_price': 0}
                self.current_balance += trade_value
            
            logger.info(f"Trade ejecutado: {symbol} {trade['signal']} {quantity:.6f} @ {price:.4f} (Conf: {confidence:.2f})")
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando trade: {e}")
            return False

    def run_backtest(self, days=180):
        """Ejecutar backtesting extenso"""
        try:
            logger.info(f"Iniciando backtesting de {days} días")
            
            # Obtener datos para todos los símbolos
            all_data = {}
            for symbol in self.symbols:
                data = self.fetch_historical_data(symbol, '1h', days)
                if not data.empty:
                    data = self.calculate_advanced_indicators(data)
                    all_data[symbol] = data
                    
                    # Entrenar modelo ML
                    self.train_ml_models(symbol, data)
            
            if not all_data:
                logger.error("No se pudieron obtener datos para backtesting")
                return
            
            # Ejecutar backtesting
            total_signals = 0
            successful_trades = 0
            
            for symbol, data in all_data.items():
                logger.info(f"Procesando {symbol} - {len(data)} registros")
                
                # Generar señales
                momentum_signals = self.generate_momentum_signals(data)
                ml_signals, ml_confidence = self.generate_ml_signals(symbol, data)
                combined_signals, combined_confidence = self.combine_signals(momentum_signals, ml_signals, ml_confidence)
                
                # Procesar señales
                for i in range(50, len(data)):  # Empezar después de período de calentamiento
                    signal = combined_signals.iloc[i]
                    confidence = combined_confidence.iloc[i]
                    price = data['close'].iloc[i]
                    volatility = data['atr_pct'].iloc[i]
                    
                    if signal != 0 and confidence >= self.min_confidence:
                        total_signals += 1
                        quantity = self.calculate_position_size(signal, confidence, price, volatility)
                        
                        if quantity > 0:
                            success = self.execute_trade(symbol, signal, quantity, price, confidence)
                            if success:
                                successful_trades += 1
            
            # Calcular métricas finales
            self.calculate_final_metrics(total_signals, successful_trades)
            
        except Exception as e:
            logger.error(f"Error en backtesting: {e}")

    def calculate_final_metrics(self, total_signals, successful_trades):
        """Calcular métricas finales del sistema"""
        try:
            # Calcular valor total del portfolio
            portfolio_value = self.current_balance
            for symbol, position in self.positions.items():
                if position['quantity'] > 0:
                    # Usar último precio conocido (simplificado)
                    portfolio_value += position['quantity'] * position['avg_price']
            
            # Métricas básicas
            total_return = (portfolio_value - self.initial_balance) / self.initial_balance
            monthly_roi = total_return * (30 / 180)  # Aproximación mensual
            
            # Métricas de trades
            total_trades = len(self.trades)
            win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Drawdown
            max_drawdown = self.max_drawdown_reached
            
            # Gap al objetivo
            target_roi = 0.15
            gap_to_target = target_roi - monthly_roi
            
            # Resultados
            results = {
                'Sistema': 'SICAR Optimizado',
                'ROI Mensual (%)': f"{monthly_roi * 100:.2f}%",
                'Total Operaciones': total_trades,
                'Win Rate (%)': f"{win_rate:.1f}%",
                'Max Drawdown (%)': f"{max_drawdown * 100:.2f}%",
                'Apalancamiento': '1.0x (Sin apalancamiento)',
                'Gap al Objetivo (%)': f"{gap_to_target * 100:.2f}%",
                'Balance Final': f"${portfolio_value:.2f}",
                'Señales Generadas': total_signals,
                'Trades Exitosos': successful_trades
            }
            
            # Guardar resultados
            results_df = pd.DataFrame([results])
            results_df.to_csv('sicar_optimized_results.csv', index=False)
            
            # Log resultados
            logger.info("=== RESULTADOS SISTEMA SICAR OPTIMIZADO ===")
            for key, value in results.items():
                logger.info(f"{key}: {value}")
            
            # Guardar trades detallados
            if self.trades:
                trades_df = pd.DataFrame(self.trades)
                trades_df.to_csv('sicar_optimized_trades.csv', index=False)
                logger.info(f"Trades guardados en sicar_optimized_trades.csv")
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculando métricas finales: {e}")
            return {}

def main():
    """Función principal"""
    try:
        logger.info("=== INICIANDO SISTEMA SICAR OPTIMIZADO ===")
        
        # Crear e inicializar sistema
        system = SICAROptimizedSystem()
        
        # Ejecutar backtesting extenso
        system.run_backtest(days=180)  # 6 meses de datos
        
        logger.info("=== SISTEMA SICAR OPTIMIZADO COMPLETADO ===")
        
    except Exception as e:
        logger.error(f"Error en función principal: {e}")

if __name__ == "__main__":
    main()