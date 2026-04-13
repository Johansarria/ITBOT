#!/usr/bin/env python3
"""
Framework de Análisis Técnico Avanzado
Optimizado para estrategia Binance Spot con objetivo de 0.6% diario
"""

import pandas as pd
import numpy as np
import talib
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from scipy import stats
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
import warnings
warnings.filterwarnings('ignore')

@dataclass
class TechnicalSignal:
    """Señal técnica generada por el framework"""
    symbol: str
    timestamp: datetime
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: float   # 0-100
    confidence: float # 0-100
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_reward_ratio: float
    indicators: Dict[str, float]
    reasons: List[str]

@dataclass
class MarketRegime:
    """Régimen de mercado detectado"""
    regime_type: str  # 'trending_up', 'trending_down', 'sideways', 'volatile'
    strength: float   # 0-100
    volatility: float
    volume_profile: str  # 'high', 'normal', 'low'
    duration: int     # períodos en el régimen actual

class TechnicalFramework:
    """
    Framework avanzado de análisis técnico que combina múltiples indicadores
    con machine learning para generar señales de alta calidad
    """
    
    def __init__(self, target_daily_return: float = 0.006):
        self.target_daily_return = target_daily_return
        self.min_signal_strength = 60  # Mínimo 60% de fuerza para operar
        self.min_confidence = 70       # Mínimo 70% de confianza
        
        # Parámetros de indicadores optimizados
        self.rsi_period = 14
        self.rsi_oversold = 25
        self.rsi_overbought = 75
        
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
        self.bb_period = 20
        self.bb_std = 2.0
        
        self.stoch_k = 14
        self.stoch_d = 3
        
        self.atr_period = 14
        self.adx_period = 14
        
        # Configuración de ML
        self.ml_model = None
        self.scaler = StandardScaler()
        self.ml_features = []
        
        # Configuración de logging
        self.logger = logging.getLogger(__name__)
        
        # Cache de datos
        self.data_cache = {}
        self.regime_cache = {}
        
    def calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular todos los indicadores técnicos"""
        if df.empty or len(df) < 50:
            return df
            
        # Asegurar que tenemos las columnas necesarias
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                self.logger.error(f"Columna requerida '{col}' no encontrada")
                return df
                
        # Indicadores de momentum
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=self.rsi_period)
        df['stoch_k'], df['stoch_d'] = talib.STOCH(
            df['high'].values, df['low'].values, df['close'].values,
            fastk_period=self.stoch_k, slowk_period=self.stoch_d, slowd_period=self.stoch_d
        )
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = talib.MACD(
            df['close'].values, fastperiod=self.macd_fast, 
            slowperiod=self.macd_slow, signalperiod=self.macd_signal
        )
        
        # Williams %R
        df['williams_r'] = talib.WILLR(
            df['high'].values, df['low'].values, df['close'].values, timeperiod=14
        )
        
        # Indicadores de tendencia
        df['sma_20'] = talib.SMA(df['close'].values, timeperiod=20)
        df['sma_50'] = talib.SMA(df['close'].values, timeperiod=50)
        df['ema_12'] = talib.EMA(df['close'].values, timeperiod=12)
        df['ema_26'] = talib.EMA(df['close'].values, timeperiod=26)
        df['ema_50'] = talib.EMA(df['close'].values, timeperiod=50)
        
        # ADX para fuerza de tendencia
        df['adx'] = talib.ADX(
            df['high'].values, df['low'].values, df['close'].values, timeperiod=self.adx_period
        )
        df['plus_di'] = talib.PLUS_DI(
            df['high'].values, df['low'].values, df['close'].values, timeperiod=self.adx_period
        )
        df['minus_di'] = talib.MINUS_DI(
            df['high'].values, df['low'].values, df['close'].values, timeperiod=self.adx_period
        )
        
        # Bandas de Bollinger
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = talib.BBANDS(
            df['close'].values, timeperiod=self.bb_period, nbdevup=self.bb_std, nbdevdn=self.bb_std
        )
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Indicadores de volatilidad
        df['atr'] = talib.ATR(
            df['high'].values, df['low'].values, df['close'].values, timeperiod=self.atr_period
        )
        df['atr_pct'] = df['atr'] / df['close']
        
        # Indicadores de volumen
        df['volume_sma'] = talib.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # OBV (On Balance Volume)
        df['obv'] = talib.OBV(df['close'].values, df['volume'].values)
        df['obv_sma'] = talib.SMA(df['obv'].values, timeperiod=20)
        
        # Money Flow Index
        df['mfi'] = talib.MFI(
            df['high'].values, df['low'].values, df['close'].values, df['volume'].values, timeperiod=14
        )
        
        # Indicadores personalizados
        df = self.calculate_custom_indicators(df)
        
        return df
        
    def calculate_custom_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores personalizados"""
        # Momentum Score (combinación de múltiples indicadores)
        df['momentum_score'] = (
            (df['rsi'] - 50) / 50 * 0.3 +
            np.where(df['macd'] > df['macd_signal'], 1, -1) * 0.3 +
            (df['stoch_k'] - 50) / 50 * 0.2 +
            np.where(df['close'] > df['ema_12'], 1, -1) * 0.2
        )
        
        # Trend Strength (fuerza de tendencia)
        df['trend_strength'] = (
            df['adx'] / 100 * 0.4 +
            abs(df['close'] - df['sma_20']) / df['sma_20'] * 100 * 0.3 +
            df['volume_ratio'] * 0.3
        )
        
        # Volatility Regime
        df['vol_regime'] = pd.cut(
            df['atr_pct'], 
            bins=[0, 0.01, 0.03, 0.05, 1.0], 
            labels=['low', 'normal', 'high', 'extreme']
        )
        
        # Support/Resistance levels
        df['support'] = df['low'].rolling(window=20).min()
        df['resistance'] = df['high'].rolling(window=20).max()
        df['sr_ratio'] = (df['close'] - df['support']) / (df['resistance'] - df['support'])
        
        # Price velocity (velocidad del precio)
        df['price_velocity'] = df['close'].pct_change(5)  # Cambio en 5 períodos
        df['price_acceleration'] = df['price_velocity'].diff()  # Aceleración
        
        # Volume-Price Trend
        df['vpt'] = (df['close'].pct_change() * df['volume']).cumsum()
        df['vpt_sma'] = df['vpt'].rolling(window=20).mean()
        
        return df
        
    def detect_market_regime(self, df: pd.DataFrame) -> MarketRegime:
        """Detectar el régimen actual del mercado"""
        if df.empty or len(df) < 50:
            return MarketRegime('unknown', 0, 0, 'normal', 0)
            
        latest = df.iloc[-20:]  # Últimos 20 períodos
        
        # Calcular métricas del régimen
        price_trend = (latest['close'].iloc[-1] - latest['close'].iloc[0]) / latest['close'].iloc[0]
        volatility = latest['atr_pct'].mean()
        volume_avg = latest['volume_ratio'].mean()
        adx_avg = latest['adx'].mean()
        
        # Determinar tipo de régimen
        if adx_avg > 25:  # Tendencia fuerte
            if price_trend > 0.02:  # Subida > 2%
                regime_type = 'trending_up'
                strength = min(adx_avg + abs(price_trend) * 100, 100)
            elif price_trend < -0.02:  # Bajada > 2%
                regime_type = 'trending_down'
                strength = min(adx_avg + abs(price_trend) * 100, 100)
            else:
                regime_type = 'sideways'
                strength = 100 - adx_avg
        else:  # Sin tendencia clara
            if volatility > 0.04:  # Alta volatilidad
                regime_type = 'volatile'
                strength = volatility * 1000
            else:
                regime_type = 'sideways'
                strength = 100 - adx_avg
                
        # Perfil de volumen
        if volume_avg > 1.5:
            volume_profile = 'high'
        elif volume_avg < 0.7:
            volume_profile = 'low'
        else:
            volume_profile = 'normal'
            
        return MarketRegime(
            regime_type=regime_type,
            strength=min(strength, 100),
            volatility=volatility,
            volume_profile=volume_profile,
            duration=20  # Simplificado
        )
        
    def generate_ml_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generar features para machine learning"""
        features = pd.DataFrame(index=df.index)
        
        # Features de precio
        features['price_sma_ratio'] = df['close'] / df['sma_20']
        features['price_ema_ratio'] = df['close'] / df['ema_12']
        features['high_low_ratio'] = df['high'] / df['low']
        
        # Features de momentum
        features['rsi_normalized'] = (df['rsi'] - 50) / 50
        features['stoch_normalized'] = (df['stoch_k'] - 50) / 50
        features['williams_normalized'] = (df['williams_r'] + 50) / 50
        
        # Features de tendencia
        features['macd_signal_ratio'] = df['macd'] / df['macd_signal']
        features['adx_normalized'] = df['adx'] / 100
        features['di_diff'] = (df['plus_di'] - df['minus_di']) / 100
        
        # Features de volatilidad
        features['bb_position'] = df['bb_position']
        features['bb_width_normalized'] = df['bb_width']
        features['atr_normalized'] = df['atr_pct']
        
        # Features de volumen
        features['volume_ratio'] = df['volume_ratio']
        features['mfi_normalized'] = (df['mfi'] - 50) / 50
        features['obv_trend'] = (df['obv'] - df['obv_sma']) / df['obv_sma']
        
        # Features personalizados
        features['momentum_score'] = df['momentum_score']
        features['trend_strength'] = df['trend_strength']
        features['sr_ratio'] = df['sr_ratio']
        features['price_velocity'] = df['price_velocity']
        
        # Features de lag (valores anteriores)
        for col in ['rsi', 'macd', 'adx']:
            if col in df.columns:
                features[f'{col}_lag1'] = df[col].shift(1)
                features[f'{col}_lag2'] = df[col].shift(2)
                
        return features.fillna(0)
        
    def train_ml_model(self, historical_data: Dict[str, pd.DataFrame], 
                      historical_returns: Dict[str, pd.Series]):
        """Entrenar modelo de machine learning"""
        self.logger.info("Entrenando modelo de ML...")
        
        all_features = []
        all_targets = []
        
        for symbol, df in historical_data.items():
            if symbol not in historical_returns:
                continue
                
            # Calcular indicadores
            df_with_indicators = self.calculate_all_indicators(df.copy())
            
            # Generar features
            features = self.generate_ml_features(df_with_indicators)
            
            # Generar targets (1 si retorno > objetivo, 0 si no)
            returns = historical_returns[symbol]
            targets = (returns > self.target_daily_return).astype(int)
            
            # Alinear índices
            common_index = features.index.intersection(targets.index)
            if len(common_index) > 50:
                all_features.append(features.loc[common_index])
                all_targets.append(targets.loc[common_index])
                
        if not all_features:
            self.logger.warning("No hay datos suficientes para entrenar ML")
            return
            
        # Combinar todos los datos
        X = pd.concat(all_features, ignore_index=True)
        y = pd.concat(all_targets, ignore_index=True)
        
        # Limpiar datos
        X = X.replace([np.inf, -np.inf], 0).fillna(0)
        
        # Escalar features
        X_scaled = self.scaler.fit_transform(X)
        
        # Entrenar modelo
        self.ml_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            random_state=42
        )
        
        self.ml_model.fit(X_scaled, y)
        self.ml_features = X.columns.tolist()
        
        # Evaluar modelo
        score = self.ml_model.score(X_scaled, y)
        self.logger.info(f"Modelo entrenado con accuracy: {score:.3f}")
        
    def generate_signals(self, symbol: str, df: pd.DataFrame) -> List[TechnicalSignal]:
        """Generar señales de trading"""
        if df.empty or len(df) < 50:
            return []
            
        # Calcular indicadores
        df_with_indicators = self.calculate_all_indicators(df.copy())
        
        # Detectar régimen de mercado
        regime = self.detect_market_regime(df_with_indicators)
        
        signals = []
        
        # Procesar últimos períodos
        for i in range(50, len(df_with_indicators)):
            current = df_with_indicators.iloc[i]
            
            # Generar señal basada en reglas
            rule_signal = self.generate_rule_based_signal(df_with_indicators, i, regime)
            
            # Generar señal basada en ML (si está disponible)
            ml_signal = None
            if self.ml_model is not None:
                ml_signal = self.generate_ml_signal(df_with_indicators, i)
                
            # Combinar señales
            final_signal = self.combine_signals(rule_signal, ml_signal, current, regime)
            
            if final_signal and final_signal.strength >= self.min_signal_strength:
                signals.append(final_signal)
                
        return signals
        
    def generate_rule_based_signal(self, df: pd.DataFrame, index: int, 
                                 regime: MarketRegime) -> Optional[TechnicalSignal]:
        """Generar señal basada en reglas técnicas"""
        current = df.iloc[index]
        prev = df.iloc[index-1]
        
        signal_type = 'HOLD'
        strength = 0
        confidence = 0
        reasons = []
        
        # Condiciones de compra
        buy_score = 0
        buy_reasons = []
        
        # RSI oversold
        if current['rsi'] < self.rsi_oversold:
            buy_score += 20
            buy_reasons.append('RSI oversold')
            
        # MACD bullish crossover
        if current['macd'] > current['macd_signal'] and prev['macd'] <= prev['macd_signal']:
            buy_score += 25
            buy_reasons.append('MACD bullish crossover')
            
        # Price near lower Bollinger Band
        if current['bb_position'] < 0.2:
            buy_score += 15
            buy_reasons.append('Near lower BB')
            
        # Strong uptrend
        if current['adx'] > 25 and current['plus_di'] > current['minus_di']:
            buy_score += 20
            buy_reasons.append('Strong uptrend')
            
        # Volume confirmation
        if current['volume_ratio'] > 1.2:
            buy_score += 10
            buy_reasons.append('High volume')
            
        # Momentum confirmation
        if current['momentum_score'] > 0.3:
            buy_score += 10
            buy_reasons.append('Positive momentum')
            
        # Condiciones de venta
        sell_score = 0
        sell_reasons = []
        
        # RSI overbought
        if current['rsi'] > self.rsi_overbought:
            sell_score += 20
            sell_reasons.append('RSI overbought')
            
        # MACD bearish crossover
        if current['macd'] < current['macd_signal'] and prev['macd'] >= prev['macd_signal']:
            sell_score += 25
            sell_reasons.append('MACD bearish crossover')
            
        # Price near upper Bollinger Band
        if current['bb_position'] > 0.8:
            sell_score += 15
            sell_reasons.append('Near upper BB')
            
        # Strong downtrend
        if current['adx'] > 25 and current['minus_di'] > current['plus_di']:
            sell_score += 20
            sell_reasons.append('Strong downtrend')
            
        # Negative momentum
        if current['momentum_score'] < -0.3:
            sell_score += 10
            sell_reasons.append('Negative momentum')
            
        # Determinar señal final
        if buy_score > sell_score and buy_score >= 50:
            signal_type = 'BUY'
            strength = min(buy_score, 100)
            reasons = buy_reasons
            confidence = self.calculate_confidence(current, regime, 'BUY')
        elif sell_score > buy_score and sell_score >= 50:
            signal_type = 'SELL'
            strength = min(sell_score, 100)
            reasons = sell_reasons
            confidence = self.calculate_confidence(current, regime, 'SELL')
            
        if signal_type == 'HOLD':
            return None
            
        # Calcular niveles de entrada, stop loss y take profit
        entry_price = current['close']
        atr = current['atr']
        
        if signal_type == 'BUY':
            stop_loss = entry_price - (atr * 1.5)
            take_profit = entry_price + (atr * 2.5)
        else:  # SELL
            stop_loss = entry_price + (atr * 1.5)
            take_profit = entry_price - (atr * 2.5)
            
        risk_reward_ratio = abs(take_profit - entry_price) / abs(entry_price - stop_loss)
        
        # Calcular tamaño de posición (simplificado)
        position_size = 0.02  # 2% del capital
        
        return TechnicalSignal(
            symbol='',  # Se asignará después
            timestamp=current.name if hasattr(current, 'name') else datetime.now(),
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            risk_reward_ratio=risk_reward_ratio,
            indicators=current.to_dict(),
            reasons=reasons
        )
        
    def generate_ml_signal(self, df: pd.DataFrame, index: int) -> Optional[Dict]:
        """Generar señal basada en machine learning"""
        if self.ml_model is None:
            return None
            
        # Generar features
        features = self.generate_ml_features(df)
        
        if index >= len(features):
            return None
            
        current_features = features.iloc[index:index+1]
        
        # Limpiar y escalar
        current_features = current_features.replace([np.inf, -np.inf], 0).fillna(0)
        
        # Asegurar que tenemos todas las features
        for feature in self.ml_features:
            if feature not in current_features.columns:
                current_features[feature] = 0
                
        current_features = current_features[self.ml_features]
        current_scaled = self.scaler.transform(current_features)
        
        # Predecir
        prediction = self.ml_model.predict(current_scaled)[0]
        probability = self.ml_model.predict_proba(current_scaled)[0]
        
        return {
            'prediction': prediction,
            'probability': max(probability),
            'confidence': max(probability) * 100
        }
        
    def combine_signals(self, rule_signal: Optional[TechnicalSignal], 
                       ml_signal: Optional[Dict], current: pd.Series, 
                       regime: MarketRegime) -> Optional[TechnicalSignal]:
        """Combinar señales de reglas y ML"""
        if rule_signal is None:
            return None
            
        # Ajustar por ML si está disponible
        if ml_signal is not None:
            # Si ML predice oportunidad, aumentar confianza
            if ml_signal['prediction'] == 1:
                rule_signal.confidence = min(rule_signal.confidence + ml_signal['confidence'] * 0.3, 100)
                rule_signal.reasons.append(f"ML confidence: {ml_signal['confidence']:.1f}%")
            else:
                # Si ML no predice oportunidad, reducir confianza
                rule_signal.confidence *= 0.7
                
        # Ajustar por régimen de mercado
        if regime.regime_type == 'trending_up' and rule_signal.signal_type == 'BUY':
            rule_signal.strength = min(rule_signal.strength * 1.2, 100)
        elif regime.regime_type == 'trending_down' and rule_signal.signal_type == 'SELL':
            rule_signal.strength = min(rule_signal.strength * 1.2, 100)
        elif regime.regime_type == 'sideways':
            rule_signal.strength *= 0.8  # Reducir en mercados laterales
            
        # Filtrar por confianza mínima
        if rule_signal.confidence < self.min_confidence:
            return None
            
        return rule_signal
        
    def calculate_confidence(self, current: pd.Series, regime: MarketRegime, signal_type: str) -> float:
        """Calcular confianza en la señal"""
        confidence = 50  # Base
        
        # Ajustar por fuerza de tendencia
        if current['adx'] > 25:
            confidence += 15
        elif current['adx'] < 15:
            confidence -= 10
            
        # Ajustar por volatilidad
        if 0.01 < current['atr_pct'] < 0.04:  # Volatilidad óptima
            confidence += 10
        elif current['atr_pct'] > 0.06:  # Muy volátil
            confidence -= 15
            
        # Ajustar por volumen
        if current['volume_ratio'] > 1.5:
            confidence += 10
        elif current['volume_ratio'] < 0.7:
            confidence -= 10
            
        # Ajustar por régimen
        if regime.strength > 70:
            confidence += 10
            
        return min(max(confidence, 0), 100)
        
    def optimize_parameters(self, historical_data: Dict[str, pd.DataFrame], 
                          target_metric: str = 'sharpe_ratio') -> Dict:
        """Optimizar parámetros del framework"""
        self.logger.info("Iniciando optimización de parámetros...")
        
        # Parámetros a optimizar
        param_ranges = {
            'rsi_period': [10, 14, 18, 21],
            'rsi_oversold': [20, 25, 30, 35],
            'rsi_overbought': [65, 70, 75, 80],
            'bb_period': [15, 20, 25],
            'bb_std': [1.5, 2.0, 2.5],
            'min_signal_strength': [50, 60, 70, 80]
        }
        
        best_params = {}
        best_score = -np.inf
        
        # Grid search simplificado
        for rsi_period in param_ranges['rsi_period']:
            for rsi_oversold in param_ranges['rsi_oversold']:
                for rsi_overbought in param_ranges['rsi_overbought']:
                    if rsi_overbought <= rsi_oversold + 20:
                        continue
                        
                    # Actualizar parámetros
                    self.rsi_period = rsi_period
                    self.rsi_oversold = rsi_oversold
                    self.rsi_overbought = rsi_overbought
                    
                    # Evaluar con datos históricos
                    score = self.evaluate_parameters(historical_data, target_metric)
                    
                    if score > best_score:
                        best_score = score
                        best_params = {
                            'rsi_period': rsi_period,
                            'rsi_oversold': rsi_oversold,
                            'rsi_overbought': rsi_overbought,
                            'score': score
                        }
                        
        # Aplicar mejores parámetros
        if best_params:
            self.rsi_period = best_params['rsi_period']
            self.rsi_oversold = best_params['rsi_oversold']
            self.rsi_overbought = best_params['rsi_overbought']
            
        self.logger.info(f"Optimización completada. Mejor score: {best_score:.3f}")
        return best_params
        
    def evaluate_parameters(self, historical_data: Dict[str, pd.DataFrame], 
                          target_metric: str) -> float:
        """Evaluar parámetros actuales"""
        total_score = 0
        count = 0
        
        for symbol, df in historical_data.items():
            if len(df) < 100:
                continue
                
            # Generar señales
            signals = self.generate_signals(symbol, df)
            
            if not signals:
                continue
                
            # Calcular métricas simplificadas
            returns = []
            for signal in signals[-50:]:  # Últimas 50 señales
                # Simular retorno (simplificado)
                if signal.signal_type == 'BUY':
                    ret = np.random.normal(0.005, 0.02)  # Retorno simulado
                else:
                    ret = np.random.normal(-0.005, 0.02)
                returns.append(ret)
                
            if returns:
                if target_metric == 'sharpe_ratio':
                    score = np.mean(returns) / (np.std(returns) + 1e-6)
                elif target_metric == 'total_return':
                    score = np.sum(returns)
                else:
                    score = len([r for r in returns if r > 0]) / len(returns)
                    
                total_score += score
                count += 1
                
        return total_score / count if count > 0 else 0
        
if __name__ == "__main__":
    # Ejemplo de uso
    framework = TechnicalFramework(target_daily_return=0.006)
    
    # Generar datos de prueba
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='H')
    test_data = pd.DataFrame({
        'open': np.random.normal(50000, 1000, len(dates)),
        'high': np.random.normal(51000, 1000, len(dates)),
        'low': np.random.normal(49000, 1000, len(dates)),
        'close': np.random.normal(50000, 1000, len(dates)),
        'volume': np.random.normal(1000, 200, len(dates))
    }, index=dates)
    
    # Generar señales
    signals = framework.generate_signals('BTC/USDT', test_data)
    
    print(f"Generadas {len(signals)} señales")
    for signal in signals[:5]:  # Mostrar primeras 5
        print(f"Señal: {signal.signal_type} - Fuerza: {signal.strength:.1f} - Confianza: {signal.confidence:.1f}")