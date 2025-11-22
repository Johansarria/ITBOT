#!/usr/bin/env python3
"""
Sistema de Filtros de Calidad para Señales SICAR
Mejora la precisión de señales mediante filtros avanzados
Objetivo: Aumentar win rate del 25.9% a >60%
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import talib
from scipy import stats
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class SignalQualityFilters:
    def __init__(self):
        """Inicializar filtros de calidad"""
        self.min_signal_strength = 0.7
        self.min_volume_confirmation = 1.3
        self.min_trend_consistency = 0.6
        self.max_volatility_threshold = 0.08
        self.min_market_cap_rank = 20  # Top 20 cryptos
        
        logger.info("Filtros de calidad inicializados")

    def filter_by_market_structure(self, df):
        """Filtrar por estructura de mercado"""
        try:
            if len(df) < 50:
                return pd.Series([False] * len(df), index=df.index)
            
            filters = []
            
            for i in range(len(df)):
                valid = True
                
                # 1. Estructura de tendencia clara
                if i >= 20:
                    sma_20 = df['sma_20'].iloc[i]
                    sma_50 = df['sma_50'].iloc[i]
                    price = df['close'].iloc[i]
                    
                    # Tendencia alcista: precio > SMA20 > SMA50
                    # Tendencia bajista: precio < SMA20 < SMA50
                    trend_structure = (
                        (price > sma_20 > sma_50) or  # Alcista
                        (price < sma_20 < sma_50)     # Bajista
                    )
                    
                    if not trend_structure:
                        valid = False
                
                # 2. Volatilidad controlada
                if 'atr_pct' in df.columns:
                    volatility = df['atr_pct'].iloc[i]
                    if volatility > self.max_volatility_threshold:
                        valid = False
                
                # 3. Volumen significativo
                if 'volume_ratio' in df.columns:
                    volume_ratio = df['volume_ratio'].iloc[i]
                    if volume_ratio < self.min_volume_confirmation:
                        valid = False
                
                filters.append(valid)
            
            return pd.Series(filters, index=df.index)
            
        except Exception as e:
            logger.error(f"Error en filtro de estructura de mercado: {e}")
            return pd.Series([True] * len(df), index=df.index)

    def filter_by_momentum_quality(self, df):
        """Filtrar por calidad del momentum"""
        try:
            if len(df) < 20:
                return pd.Series([False] * len(df), index=df.index)
            
            filters = []
            
            for i in range(len(df)):
                valid = True
                
                # 1. RSI en zona válida (no extremos)
                if 'rsi_14' in df.columns:
                    rsi = df['rsi_14'].iloc[i]
                    # Evitar zonas de sobrecompra/sobreventa extremas
                    if rsi > 85 or rsi < 15:
                        valid = False
                
                # 2. MACD con momentum consistente
                if all(col in df.columns for col in ['macd', 'macd_signal', 'macd_histogram']):
                    macd = df['macd'].iloc[i]
                    macd_signal = df['macd_signal'].iloc[i]
                    macd_hist = df['macd_histogram'].iloc[i]
                    
                    # Verificar consistencia de momentum
                    if i >= 3:
                        hist_trend = df['macd_histogram'].iloc[i-3:i+1].diff().mean()
                        # Momentum debe ser consistente
                        if abs(hist_trend) < 0.001:
                            valid = False
                
                # 3. Stochastic no en extremos
                if 'stoch_k' in df.columns:
                    stoch_k = df['stoch_k'].iloc[i]
                    if stoch_k > 90 or stoch_k < 10:
                        valid = False
                
                # 4. ADX indica tendencia fuerte
                if 'adx' in df.columns:
                    adx = df['adx'].iloc[i]
                    if adx < 20:  # Tendencia débil
                        valid = False
                
                filters.append(valid)
            
            return pd.Series(filters, index=df.index)
            
        except Exception as e:
            logger.error(f"Error en filtro de calidad de momentum: {e}")
            return pd.Series([True] * len(df), index=df.index)

    def filter_by_price_action(self, df):
        """Filtrar por acción del precio"""
        try:
            if len(df) < 10:
                return pd.Series([False] * len(df), index=df.index)
            
            filters = []
            
            for i in range(len(df)):
                valid = True
                
                # 1. Patrones de velas válidos
                if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                    open_price = df['open'].iloc[i]
                    high_price = df['high'].iloc[i]
                    low_price = df['low'].iloc[i]
                    close_price = df['close'].iloc[i]
                    
                    # Evitar velas con sombras extremas (>80% del rango)
                    body_size = abs(close_price - open_price)
                    total_range = high_price - low_price
                    
                    if total_range > 0:
                        body_ratio = body_size / total_range
                        if body_ratio < 0.2:  # Vela con cuerpo muy pequeño
                            valid = False
                
                # 2. Soporte/Resistencia respetados
                if all(col in df.columns for col in ['support', 'resistance', 'close']):
                    price = df['close'].iloc[i]
                    support = df['support'].iloc[i]
                    resistance = df['resistance'].iloc[i]
                    
                    # Verificar que el precio no esté muy cerca de S/R
                    if support > 0 and resistance > 0:
                        dist_to_support = (price - support) / price
                        dist_to_resistance = (resistance - price) / price
                        
                        # Evitar trades muy cerca de S/R (zona de indecisión)
                        if dist_to_support < 0.01 or dist_to_resistance < 0.01:
                            valid = False
                
                # 3. Consistencia de dirección
                if i >= 5:
                    recent_closes = df['close'].iloc[i-4:i+1]
                    price_direction = np.sign(recent_closes.diff().dropna())
                    
                    # Al menos 60% de consistencia en dirección
                    if len(price_direction) > 0:
                        consistency = abs(price_direction.mean())
                        if consistency < self.min_trend_consistency:
                            valid = False
                
                filters.append(valid)
            
            return pd.Series(filters, index=df.index)
            
        except Exception as e:
            logger.error(f"Error en filtro de acción del precio: {e}")
            return pd.Series([True] * len(df), index=df.index)

    def filter_by_volume_profile(self, df):
        """Filtrar por perfil de volumen"""
        try:
            if len(df) < 20:
                return pd.Series([False] * len(df), index=df.index)
            
            filters = []
            
            for i in range(len(df)):
                valid = True
                
                # 1. Volumen creciente en dirección de la tendencia
                if i >= 5 and 'volume' in df.columns:
                    recent_volumes = df['volume'].iloc[i-4:i+1]
                    recent_prices = df['close'].iloc[i-4:i+1]
                    
                    volume_trend = recent_volumes.diff().mean()
                    price_trend = recent_prices.diff().mean()
                    
                    # Volumen debe confirmar la dirección del precio
                    if price_trend > 0 and volume_trend < 0:  # Precio sube, volumen baja
                        valid = False
                    elif price_trend < 0 and volume_trend < 0:  # Precio baja, volumen baja
                        valid = False
                
                # 2. Volumen relativo significativo
                if 'volume_ratio' in df.columns:
                    volume_ratio = df['volume_ratio'].iloc[i]
                    if volume_ratio < 1.2:  # Volumen debe ser al menos 20% superior al promedio
                        valid = False
                
                # 3. No hay picos de volumen anómalos
                if i >= 10 and 'volume' in df.columns:
                    recent_volumes = df['volume'].iloc[i-9:i+1]
                    current_volume = df['volume'].iloc[i]
                    avg_volume = recent_volumes.mean()
                    
                    # Evitar picos de volumen extremos (posibles manipulaciones)
                    if current_volume > avg_volume * 5:
                        valid = False
                
                filters.append(valid)
            
            return pd.Series(filters, index=df.index)
            
        except Exception as e:
            logger.error(f"Error en filtro de perfil de volumen: {e}")
            return pd.Series([True] * len(df), index=df.index)

    def filter_by_market_regime(self, df):
        """Filtrar por régimen de mercado"""
        try:
            if len(df) < 30:
                return pd.Series([False] * len(df), index=df.index)
            
            filters = []
            
            for i in range(len(df)):
                valid = True
                
                # 1. Régimen de mercado favorable
                if 'market_regime' in df.columns:
                    regime = df['market_regime'].iloc[i]
                    # Solo operar en mercados trending o ranging estables
                    if regime == 'volatile':
                        valid = False
                
                # 2. Correlación con Bitcoin (si no es BTC)
                # Simplificado: verificar que no haya divergencias extremas
                if i >= 10:
                    price_change = df['close'].iloc[i] / df['close'].iloc[i-10] - 1
                    # Evitar movimientos extremos (>20% en 10 períodos)
                    if abs(price_change) > 0.20:
                        valid = False
                
                # 3. Estabilidad de volatilidad
                if i >= 20 and 'atr_pct' in df.columns:
                    recent_volatility = df['atr_pct'].iloc[i-19:i+1]
                    vol_stability = recent_volatility.std()
                    
                    # Volatilidad debe ser estable
                    if vol_stability > 0.02:
                        valid = False
                
                filters.append(valid)
            
            return pd.Series(filters, index=df.index)
            
        except Exception as e:
            logger.error(f"Error en filtro de régimen de mercado: {e}")
            return pd.Series([True] * len(df), index=df.index)

    def filter_by_timing(self, df):
        """Filtrar por timing óptimo"""
        try:
            filters = []
            
            for i in range(len(df)):
                valid = True
                
                # 1. Evitar fines de semana (menor liquidez)
                if 'timestamp' in df.columns:
                    timestamp = df['timestamp'].iloc[i]
                    if hasattr(timestamp, 'weekday'):
                        # Evitar domingo (6) y lunes temprano
                        if timestamp.weekday() == 6:
                            valid = False
                
                # 2. Múltiples timeframes alineados
                # Simplificado: verificar que la tendencia sea consistente
                if i >= 5:
                    short_trend = df['close'].iloc[i] / df['close'].iloc[i-2] - 1
                    medium_trend = df['close'].iloc[i] / df['close'].iloc[i-5] - 1
                    
                    # Tendencias deben estar alineadas
                    if np.sign(short_trend) != np.sign(medium_trend):
                        valid = False
                
                filters.append(valid)
            
            return pd.Series(filters, index=df.index)
            
        except Exception as e:
            logger.error(f"Error en filtro de timing: {e}")
            return pd.Series([True] * len(df), index=df.index)

    def calculate_signal_quality_score(self, df, signal_idx):
        """Calcular puntuación de calidad de señal"""
        try:
            if signal_idx >= len(df):
                return 0
            
            score = 0
            max_score = 0
            
            # 1. Fuerza del momentum (0-20 puntos)
            max_score += 20
            if 'rsi_14' in df.columns:
                rsi = df['rsi_14'].iloc[signal_idx]
                if 30 <= rsi <= 70:  # Zona neutral
                    score += 15
                elif 20 <= rsi <= 80:  # Zona aceptable
                    score += 10
                else:
                    score += 5
            
            # 2. Confirmación de volumen (0-15 puntos)
            max_score += 15
            if 'volume_ratio' in df.columns:
                vol_ratio = df['volume_ratio'].iloc[signal_idx]
                if vol_ratio >= 2.0:
                    score += 15
                elif vol_ratio >= 1.5:
                    score += 10
                elif vol_ratio >= 1.2:
                    score += 5
            
            # 3. Estructura de tendencia (0-20 puntos)
            max_score += 20
            if signal_idx >= 20 and all(col in df.columns for col in ['sma_20', 'sma_50']):
                sma_20 = df['sma_20'].iloc[signal_idx]
                sma_50 = df['sma_50'].iloc[signal_idx]
                price = df['close'].iloc[signal_idx]
                
                if (price > sma_20 > sma_50) or (price < sma_20 < sma_50):
                    score += 20
                elif (price > sma_20) or (price < sma_20):
                    score += 10
            
            # 4. Volatilidad controlada (0-10 puntos)
            max_score += 10
            if 'atr_pct' in df.columns:
                volatility = df['atr_pct'].iloc[signal_idx]
                if volatility <= 0.03:
                    score += 10
                elif volatility <= 0.05:
                    score += 7
                elif volatility <= 0.08:
                    score += 4
            
            # 5. Soporte/Resistencia (0-15 puntos)
            max_score += 15
            if all(col in df.columns for col in ['support', 'resistance', 'close']):
                price = df['close'].iloc[signal_idx]
                support = df['support'].iloc[signal_idx]
                resistance = df['resistance'].iloc[signal_idx]
                
                if support > 0 and resistance > 0:
                    dist_to_support = (price - support) / price
                    dist_to_resistance = (resistance - price) / price
                    
                    # Mejor puntuación si está lejos de S/R
                    min_dist = min(dist_to_support, dist_to_resistance)
                    if min_dist >= 0.05:
                        score += 15
                    elif min_dist >= 0.03:
                        score += 10
                    elif min_dist >= 0.02:
                        score += 5
            
            # 6. Consistencia direccional (0-20 puntos)
            max_score += 20
            if signal_idx >= 5:
                recent_closes = df['close'].iloc[signal_idx-4:signal_idx+1]
                price_changes = recent_closes.diff().dropna()
                
                if len(price_changes) > 0:
                    consistency = abs(np.sign(price_changes).mean())
                    if consistency >= 0.8:
                        score += 20
                    elif consistency >= 0.6:
                        score += 15
                    elif consistency >= 0.4:
                        score += 10
                    else:
                        score += 5
            
            # Normalizar score (0-1)
            if max_score > 0:
                normalized_score = score / max_score
            else:
                normalized_score = 0
            
            return normalized_score
            
        except Exception as e:
            logger.error(f"Error calculando puntuación de calidad: {e}")
            return 0

    def apply_all_filters(self, df, signals, confidences):
        """Aplicar todos los filtros de calidad"""
        try:
            logger.info("Aplicando filtros de calidad a señales")
            
            # Aplicar filtros individuales
            market_structure_filter = self.filter_by_market_structure(df)
            momentum_filter = self.filter_by_momentum_quality(df)
            price_action_filter = self.filter_by_price_action(df)
            volume_filter = self.filter_by_volume_profile(df)
            regime_filter = self.filter_by_market_regime(df)
            timing_filter = self.filter_by_timing(df)
            
            # Combinar filtros
            combined_filter = (
                market_structure_filter & 
                momentum_filter & 
                price_action_filter & 
                volume_filter & 
                regime_filter & 
                timing_filter
            )
            
            # Aplicar filtros a señales
            filtered_signals = signals.copy()
            filtered_confidences = confidences.copy()
            
            # Calcular puntuaciones de calidad
            quality_scores = []
            for i in range(len(df)):
                if signals.iloc[i] != 0 and combined_filter.iloc[i]:
                    quality_score = self.calculate_signal_quality_score(df, i)
                    quality_scores.append(quality_score)
                    
                    # Solo mantener señales de alta calidad
                    if quality_score < self.min_signal_strength:
                        filtered_signals.iloc[i] = 0
                        filtered_confidences.iloc[i] = 0
                    else:
                        # Ajustar confianza por calidad
                        filtered_confidences.iloc[i] = min(1.0, confidences.iloc[i] * quality_score)
                else:
                    quality_scores.append(0)
                    if signals.iloc[i] != 0:
                        filtered_signals.iloc[i] = 0
                        filtered_confidences.iloc[i] = 0
            
            # Estadísticas de filtrado
            original_signals = (signals != 0).sum()
            filtered_signals_count = (filtered_signals != 0).sum()
            filter_rate = (original_signals - filtered_signals_count) / original_signals if original_signals > 0 else 0
            
            logger.info(f"Señales originales: {original_signals}")
            logger.info(f"Señales filtradas: {filtered_signals_count}")
            logger.info(f"Tasa de filtrado: {filter_rate:.1%}")
            
            return filtered_signals, filtered_confidences, pd.Series(quality_scores, index=df.index)
            
        except Exception as e:
            logger.error(f"Error aplicando filtros: {e}")
            return signals, confidences, pd.Series([0] * len(df), index=df.index)

def main():
    """Función de prueba"""
    try:
        # Crear datos de prueba
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        np.random.seed(42)
        
        test_data = pd.DataFrame({
            'timestamp': dates,
            'open': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'high': 100 + np.cumsum(np.random.randn(100) * 0.5) + np.random.rand(100) * 2,
            'low': 100 + np.cumsum(np.random.randn(100) * 0.5) - np.random.rand(100) * 2,
            'close': 100 + np.cumsum(np.random.randn(100) * 0.5),
            'volume': np.random.rand(100) * 1000000
        })
        
        # Calcular indicadores básicos
        test_data['sma_20'] = test_data['close'].rolling(20).mean()
        test_data['sma_50'] = test_data['close'].rolling(50).mean()
        test_data['rsi_14'] = talib.RSI(test_data['close'], timeperiod=14)
        test_data['volume_ratio'] = test_data['volume'] / test_data['volume'].rolling(20).mean()
        test_data['atr_pct'] = talib.ATR(test_data['high'], test_data['low'], test_data['close']) / test_data['close']
        
        # Señales de prueba
        signals = pd.Series(np.random.choice([-1, 0, 1], size=100), index=test_data.index)
        confidences = pd.Series(np.random.rand(100), index=test_data.index)
        
        # Aplicar filtros
        filters = SignalQualityFilters()
        filtered_signals, filtered_confidences, quality_scores = filters.apply_all_filters(
            test_data, signals, confidences
        )
        
        print("Prueba de filtros completada exitosamente")
        
    except Exception as e:
        print(f"Error en prueba: {e}")

if __name__ == "__main__":
    main()