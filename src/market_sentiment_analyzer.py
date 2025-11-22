"""
Sistema Avanzado de Análisis de Sentimiento de Mercado - Phase 2
Analiza múltiples fuentes para determinar el sentimiento del mercado
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import requests
import time
from typing import Dict, List, Tuple, Optional
import json
import re
from dataclasses import dataclass
from enum import Enum

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentimentLevel(Enum):
    """Niveles de sentimiento del mercado"""
    EXTREMELY_BEARISH = -2
    BEARISH = -1
    NEUTRAL = 0
    BULLISH = 1
    EXTREMELY_BULLISH = 2

@dataclass
class SentimentData:
    """Estructura de datos para sentimiento"""
    timestamp: datetime
    symbol: str
    overall_sentiment: float
    sentiment_level: SentimentLevel
    news_sentiment: float
    social_sentiment: float
    fear_greed_index: float
    volume_sentiment: float
    confidence: float
    sources_count: int

class MarketSentimentAnalyzer:
    """
    Analizador avanzado de sentimiento de mercado
    Combina múltiples fuentes para análisis integral
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.sentiment_history = {}
        self.fear_greed_cache = {}
        self.news_keywords = {
            'bullish': ['bull', 'rally', 'surge', 'pump', 'moon', 'breakout', 'bullish', 'positive', 'growth', 'rise'],
            'bearish': ['bear', 'crash', 'dump', 'fall', 'drop', 'bearish', 'negative', 'decline', 'correction', 'sell-off']
        }
        
        # Pesos para diferentes fuentes de sentimiento
        self.sentiment_weights = {
            'news': 0.3,
            'social': 0.25,
            'fear_greed': 0.25,
            'volume': 0.2
        }
        
        self.logger.info("✅ MarketSentimentAnalyzer inicializado")
    
    def analyze_sentiment(self, symbol: str, market_data: pd.DataFrame = None) -> SentimentData:
        """
        Análisis completo de sentimiento para un símbolo
        """
        try:
            timestamp = datetime.now()
            
            # Análisis de diferentes fuentes
            news_sentiment = self._analyze_news_sentiment(symbol)
            social_sentiment = self._analyze_social_sentiment(symbol)
            fear_greed = self._get_fear_greed_index()
            volume_sentiment = self._analyze_volume_sentiment(symbol, market_data)
            
            # Calcular sentimiento general ponderado
            overall_sentiment = (
                news_sentiment * self.sentiment_weights['news'] +
                social_sentiment * self.sentiment_weights['social'] +
                fear_greed * self.sentiment_weights['fear_greed'] +
                volume_sentiment * self.sentiment_weights['volume']
            )
            
            # Determinar nivel de sentimiento
            sentiment_level = self._classify_sentiment_level(overall_sentiment)
            
            # Calcular confianza basada en consistencia de fuentes
            confidence = self._calculate_confidence([news_sentiment, social_sentiment, fear_greed, volume_sentiment])
            
            # Contar fuentes válidas
            sources_count = sum(1 for s in [news_sentiment, social_sentiment, fear_greed, volume_sentiment] if s is not None)
            
            sentiment_data = SentimentData(
                timestamp=timestamp,
                symbol=symbol,
                overall_sentiment=overall_sentiment,
                sentiment_level=sentiment_level,
                news_sentiment=news_sentiment or 0.0,
                social_sentiment=social_sentiment or 0.0,
                fear_greed_index=fear_greed or 0.0,
                volume_sentiment=volume_sentiment or 0.0,
                confidence=confidence,
                sources_count=sources_count
            )
            
            # Guardar en historial
            if symbol not in self.sentiment_history:
                self.sentiment_history[symbol] = []
            self.sentiment_history[symbol].append(sentiment_data)
            
            # Mantener solo últimos 100 registros
            if len(self.sentiment_history[symbol]) > 100:
                self.sentiment_history[symbol] = self.sentiment_history[symbol][-100:]
            
            self.logger.info(f"📊 Sentimiento analizado para {symbol}: {sentiment_level.name} ({overall_sentiment:.3f})")
            
            return sentiment_data
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando sentimiento para {symbol}: {e}")
            return self._create_neutral_sentiment(symbol)
    
    def _analyze_news_sentiment(self, symbol: str) -> Optional[float]:
        """
        Análisis de sentimiento basado en noticias
        Simula análisis de noticias financieras
        """
        try:
            # Simulación de análisis de noticias
            # En implementación real, se conectaría a APIs de noticias
            
            # Generar sentimiento simulado basado en patrones de mercado
            base_sentiment = np.random.normal(0, 0.3)
            
            # Ajustar según símbolo (BTC tiende a tener más noticias positivas)
            if 'BTC' in symbol.upper():
                base_sentiment += 0.1
            elif 'ETH' in symbol.upper():
                base_sentiment += 0.05
            
            # Normalizar entre -1 y 1
            news_sentiment = np.clip(base_sentiment, -1, 1)
            
            self.logger.debug(f"📰 Sentimiento de noticias para {symbol}: {news_sentiment:.3f}")
            return news_sentiment
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error en análisis de noticias para {symbol}: {e}")
            return None
    
    def _analyze_social_sentiment(self, symbol: str) -> Optional[float]:
        """
        Análisis de sentimiento de redes sociales
        Simula análisis de Twitter, Reddit, etc.
        """
        try:
            # Simulación de análisis de redes sociales
            # En implementación real, se conectaría a APIs de Twitter, Reddit, etc.
            
            # Generar sentimiento simulado con más volatilidad
            social_sentiment = np.random.normal(0, 0.4)
            
            # Añadir sesgo según hora del día (más actividad en ciertas horas)
            hour = datetime.now().hour
            if 14 <= hour <= 22:  # Horas de mayor actividad
                social_sentiment += np.random.normal(0, 0.2)
            
            # Normalizar entre -1 y 1
            social_sentiment = np.clip(social_sentiment, -1, 1)
            
            self.logger.debug(f"📱 Sentimiento social para {symbol}: {social_sentiment:.3f}")
            return social_sentiment
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error en análisis social para {symbol}: {e}")
            return None
    
    def _get_fear_greed_index(self) -> Optional[float]:
        """
        Obtiene el índice de Fear & Greed
        Simula conexión a API de Fear & Greed Index
        """
        try:
            # Verificar cache (actualizar cada hora)
            now = datetime.now()
            if 'timestamp' in self.fear_greed_cache:
                cache_age = now - self.fear_greed_cache['timestamp']
                if cache_age < timedelta(hours=1):
                    return self.fear_greed_cache['value']
            
            # Simulación de Fear & Greed Index
            # En implementación real, se conectaría a API oficial
            
            # Generar índice simulado (0-100, convertir a -1 a 1)
            fear_greed_raw = np.random.uniform(20, 80)  # Evitar extremos
            fear_greed_normalized = (fear_greed_raw - 50) / 50  # Convertir a -1 a 1
            
            # Guardar en cache
            self.fear_greed_cache = {
                'value': fear_greed_normalized,
                'timestamp': now,
                'raw_value': fear_greed_raw
            }
            
            self.logger.debug(f"😨 Fear & Greed Index: {fear_greed_raw:.1f} ({fear_greed_normalized:.3f})")
            return fear_greed_normalized
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error obteniendo Fear & Greed Index: {e}")
            return None
    
    def _analyze_volume_sentiment(self, symbol: str, market_data: pd.DataFrame = None) -> Optional[float]:
        """
        Análisis de sentimiento basado en volumen
        """
        try:
            if market_data is None or len(market_data) < 20:
                # Generar sentimiento de volumen simulado
                return np.random.normal(0, 0.2)
            
            # Calcular métricas de volumen
            recent_volume = market_data['volume'].tail(5).mean()
            avg_volume = market_data['volume'].tail(20).mean()
            
            if avg_volume == 0:
                return 0.0
            
            # Ratio de volumen reciente vs promedio
            volume_ratio = recent_volume / avg_volume
            
            # Convertir a sentimiento (-1 a 1)
            if volume_ratio > 1.5:
                volume_sentiment = 0.5  # Alto volumen = bullish
            elif volume_ratio > 1.2:
                volume_sentiment = 0.3
            elif volume_ratio < 0.7:
                volume_sentiment = -0.3  # Bajo volumen = bearish
            elif volume_ratio < 0.5:
                volume_sentiment = -0.5
            else:
                volume_sentiment = 0.0
            
            self.logger.debug(f"📊 Sentimiento de volumen para {symbol}: {volume_sentiment:.3f}")
            return volume_sentiment
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error en análisis de volumen para {symbol}: {e}")
            return None
    
    def _classify_sentiment_level(self, sentiment: float) -> SentimentLevel:
        """
        Clasifica el sentimiento numérico en niveles
        """
        if sentiment >= 0.6:
            return SentimentLevel.EXTREMELY_BULLISH
        elif sentiment >= 0.2:
            return SentimentLevel.BULLISH
        elif sentiment <= -0.6:
            return SentimentLevel.EXTREMELY_BEARISH
        elif sentiment <= -0.2:
            return SentimentLevel.BEARISH
        else:
            return SentimentLevel.NEUTRAL
    
    def _calculate_confidence(self, sentiments: List[Optional[float]]) -> float:
        """
        Calcula la confianza basada en la consistencia de las fuentes
        """
        valid_sentiments = [s for s in sentiments if s is not None]
        
        if len(valid_sentiments) < 2:
            return 0.3  # Baja confianza con pocas fuentes
        
        # Calcular desviación estándar
        std_dev = np.std(valid_sentiments)
        
        # Convertir a confianza (menor desviación = mayor confianza)
        confidence = max(0.1, 1.0 - std_dev)
        
        return min(1.0, confidence)
    
    def _create_neutral_sentiment(self, symbol: str) -> SentimentData:
        """
        Crea un objeto de sentimiento neutral en caso de error
        """
        return SentimentData(
            timestamp=datetime.now(),
            symbol=symbol,
            overall_sentiment=0.0,
            sentiment_level=SentimentLevel.NEUTRAL,
            news_sentiment=0.0,
            social_sentiment=0.0,
            fear_greed_index=0.0,
            volume_sentiment=0.0,
            confidence=0.1,
            sources_count=0
        )
    
    def get_sentiment_trend(self, symbol: str, periods: int = 10) -> Dict:
        """
        Obtiene la tendencia de sentimiento para un símbolo
        """
        if symbol not in self.sentiment_history or len(self.sentiment_history[symbol]) < 2:
            return {
                'trend': 'neutral',
                'strength': 0.0,
                'direction': 0,
                'periods_analyzed': 0
            }
        
        history = self.sentiment_history[symbol][-periods:]
        sentiments = [data.overall_sentiment for data in history]
        
        # Calcular tendencia
        if len(sentiments) >= 3:
            recent_avg = np.mean(sentiments[-3:])
            older_avg = np.mean(sentiments[:-3]) if len(sentiments) > 3 else sentiments[0]
            
            trend_strength = abs(recent_avg - older_avg)
            direction = 1 if recent_avg > older_avg else -1 if recent_avg < older_avg else 0
            
            if trend_strength > 0.3:
                trend = 'strong_bullish' if direction > 0 else 'strong_bearish'
            elif trend_strength > 0.1:
                trend = 'bullish' if direction > 0 else 'bearish'
            else:
                trend = 'neutral'
        else:
            trend = 'neutral'
            trend_strength = 0.0
            direction = 0
        
        return {
            'trend': trend,
            'strength': trend_strength,
            'direction': direction,
            'periods_analyzed': len(sentiments)
        }
    
    def get_sentiment_signal(self, symbol: str) -> Dict:
        """
        Genera señal de trading basada en sentimiento
        """
        if symbol not in self.sentiment_history or not self.sentiment_history[symbol]:
            return {
                'signal': 'hold',
                'strength': 0.0,
                'confidence': 0.0,
                'reason': 'No hay datos de sentimiento'
            }
        
        latest_sentiment = self.sentiment_history[symbol][-1]
        trend = self.get_sentiment_trend(symbol)
        
        # Generar señal basada en sentimiento y tendencia
        sentiment_value = latest_sentiment.overall_sentiment
        confidence = latest_sentiment.confidence
        
        if sentiment_value > 0.4 and trend['direction'] > 0:
            signal = 'strong_buy'
            strength = min(1.0, sentiment_value + trend['strength'])
        elif sentiment_value > 0.2:
            signal = 'buy'
            strength = sentiment_value
        elif sentiment_value < -0.4 and trend['direction'] < 0:
            signal = 'strong_sell'
            strength = min(1.0, abs(sentiment_value) + trend['strength'])
        elif sentiment_value < -0.2:
            signal = 'sell'
            strength = abs(sentiment_value)
        else:
            signal = 'hold'
            strength = 0.0
        
        return {
            'signal': signal,
            'strength': strength,
            'confidence': confidence,
            'reason': f"Sentimiento: {latest_sentiment.sentiment_level.name}, Tendencia: {trend['trend']}"
        }
    
    def get_statistics(self) -> Dict:
        """
        Obtiene estadísticas del analizador de sentimiento
        """
        total_symbols = len(self.sentiment_history)
        total_analyses = sum(len(history) for history in self.sentiment_history.values())
        
        if total_analyses == 0:
            return {
                'total_symbols': 0,
                'total_analyses': 0,
                'avg_sentiment': 0.0,
                'sentiment_distribution': {},
                'avg_confidence': 0.0
            }
        
        # Calcular estadísticas
        all_sentiments = []
        all_confidences = []
        sentiment_levels = {level.name: 0 for level in SentimentLevel}
        
        for history in self.sentiment_history.values():
            for data in history:
                all_sentiments.append(data.overall_sentiment)
                all_confidences.append(data.confidence)
                sentiment_levels[data.sentiment_level.name] += 1
        
        return {
            'total_symbols': total_symbols,
            'total_analyses': total_analyses,
            'avg_sentiment': np.mean(all_sentiments),
            'sentiment_distribution': sentiment_levels,
            'avg_confidence': np.mean(all_confidences),
            'cache_status': {
                'fear_greed_cached': 'timestamp' in self.fear_greed_cache,
                'cache_age_minutes': (datetime.now() - self.fear_greed_cache.get('timestamp', datetime.now())).total_seconds() / 60 if 'timestamp' in self.fear_greed_cache else 0
            }
        }

# Función de prueba
def test_sentiment_analyzer():
    """
    Función de prueba para el analizador de sentimiento
    """
    print("🧪 Iniciando pruebas del Analizador de Sentimiento...")
    
    # Crear analizador
    analyzer = MarketSentimentAnalyzer()
    
    # Generar datos de prueba
    test_data = pd.DataFrame({
        'timestamp': pd.date_range(start='2025-01-01', periods=100, freq='1H'),
        'open': np.random.uniform(40000, 50000, 100),
        'high': np.random.uniform(40000, 50000, 100),
        'low': np.random.uniform(40000, 50000, 100),
        'close': np.random.uniform(40000, 50000, 100),
        'volume': np.random.uniform(1000, 10000, 100)
    })
    
    # Probar análisis de sentimiento
    symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    
    for symbol in symbols:
        print(f"\n📊 Analizando sentimiento para {symbol}...")
        
        # Realizar múltiples análisis
        for i in range(5):
            sentiment = analyzer.analyze_sentiment(symbol, test_data)
            print(f"  Análisis {i+1}: {sentiment.sentiment_level.name} "
                  f"({sentiment.overall_sentiment:.3f}, confianza: {sentiment.confidence:.3f})")
        
        # Obtener tendencia
        trend = analyzer.get_sentiment_trend(symbol)
        print(f"  Tendencia: {trend['trend']} (fuerza: {trend['strength']:.3f})")
        
        # Obtener señal
        signal = analyzer.get_sentiment_signal(symbol)
        print(f"  Señal: {signal['signal']} (fuerza: {signal['strength']:.3f}, "
              f"confianza: {signal['confidence']:.3f})")
    
    # Mostrar estadísticas
    stats = analyzer.get_statistics()
    print(f"\n📈 Estadísticas del Analizador:")
    print(f"  Símbolos analizados: {stats['total_symbols']}")
    print(f"  Total análisis: {stats['total_analyses']}")
    print(f"  Sentimiento promedio: {stats['avg_sentiment']:.3f}")
    print(f"  Confianza promedio: {stats['avg_confidence']:.3f}")
    print(f"  Distribución de sentimientos: {stats['sentiment_distribution']}")
    
    print("\n✅ Pruebas del Analizador de Sentimiento completadas")

if __name__ == "__main__":
    test_sentiment_analyzer()