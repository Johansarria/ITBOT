# strategies/external_data_analyzer.py

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import json
import re
from textblob import TextBlob
import feedparser
from bs4 import BeautifulSoup
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor
import time
from enum import Enum

logger = logging.getLogger(__name__)

class SentimentType(Enum):
    """Tipos de sentiment"""
    VERY_BEARISH = -2
    BEARISH = -1
    NEUTRAL = 0
    BULLISH = 1
    VERY_BULLISH = 2

class NewsSource(Enum):
    """Fuentes de noticias"""
    COINDESK = "coindesk"
    COINTELEGRAPH = "cointelegraph"
    CRYPTONEWS = "cryptonews"
    REDDIT = "reddit"
    TWITTER = "twitter"
    FEAR_GREED = "fear_greed"
    GOOGLE_TRENDS = "google_trends"

@dataclass
class NewsItem:
    """Item de noticia"""
    title: str
    content: str
    source: str
    timestamp: datetime
    url: str
    sentiment_score: float = 0.0
    relevance_score: float = 0.0
    keywords: List[str] = field(default_factory=list)
    impact_level: str = "low"  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'content': self.content[:200] + '...' if len(self.content) > 200 else self.content,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'url': self.url,
            'sentiment_score': self.sentiment_score,
            'relevance_score': self.relevance_score,
            'keywords': self.keywords,
            'impact_level': self.impact_level
        }

@dataclass
class MarketSentiment:
    """Sentiment del mercado"""
    overall_sentiment: float  # -1 a 1
    sentiment_type: SentimentType
    confidence: float  # 0 a 1
    news_sentiment: float
    social_sentiment: float
    fear_greed_index: float
    trend_sentiment: float
    volume_sentiment: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_sentiment': self.overall_sentiment,
            'sentiment_type': self.sentiment_type.name,
            'confidence': self.confidence,
            'news_sentiment': self.news_sentiment,
            'social_sentiment': self.social_sentiment,
            'fear_greed_index': self.fear_greed_index,
            'trend_sentiment': self.trend_sentiment,
            'volume_sentiment': self.volume_sentiment,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class ExternalSignal:
    """Señal externa"""
    signal_type: str
    strength: float  # 0 a 1
    direction: int  # -1, 0, 1
    confidence: float
    source: str
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'signal_type': self.signal_type,
            'strength': self.strength,
            'direction': self.direction,
            'confidence': self.confidence,
            'source': self.source,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

@dataclass
class ExternalAnalysisConfig:
    """Configuración de análisis externo"""
    # Fuentes habilitadas
    enabled_sources: List[NewsSource] = field(default_factory=lambda: [
        NewsSource.COINDESK, NewsSource.COINTELEGRAPH, NewsSource.FEAR_GREED
    ])
    
    # Configuración de noticias
    news_lookback_hours: int = 24
    max_news_per_source: int = 20
    min_relevance_score: float = 0.3
    
    # Configuración de sentiment
    sentiment_weight_news: float = 0.3
    sentiment_weight_social: float = 0.2
    sentiment_weight_fear_greed: float = 0.25
    sentiment_weight_trends: float = 0.15
    sentiment_weight_volume: float = 0.1
    
    # Configuración de señales
    signal_threshold_weak: float = 0.3
    signal_threshold_medium: float = 0.6
    signal_threshold_strong: float = 0.8
    
    # Configuración de cache
    cache_duration_minutes: int = 15
    
    # Símbolos objetivo
    target_symbols: List[str] = field(default_factory=lambda: ["BNB", "SOL", "BTC", "ETH"])
    
    # APIs y configuración
    request_timeout: int = 10
    max_concurrent_requests: int = 5
    rate_limit_delay: float = 1.0

class ExternalDataAnalyzer:
    """Analizador de datos externos para trading"""
    
    def __init__(self, config: ExternalAnalysisConfig = None):
        self.config = config or ExternalAnalysisConfig()
        
        # Cache de datos
        self._news_cache: Dict[str, List[NewsItem]] = {}
        self._sentiment_cache: Dict[str, MarketSentiment] = {}
        self._signals_cache: Dict[str, List[ExternalSignal]] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Session HTTP
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Executor para tareas CPU-intensivas
        self._executor = ThreadPoolExecutor(max_workers=4)
        
        # URLs de fuentes
        self._news_urls = {
            NewsSource.COINDESK: "https://www.coindesk.com/arc/outboundfeeds/rss/",
            NewsSource.COINTELEGRAPH: "https://cointelegraph.com/rss",
            NewsSource.CRYPTONEWS: "https://cryptonews.com/news/feed"
        }
        
        # Palabras clave por símbolo
        self._symbol_keywords = {
            "BNB": ["binance", "bnb", "binance coin", "bsc", "binance smart chain"],
            "SOL": ["solana", "sol", "solana network", "solana blockchain"],
            "BTC": ["bitcoin", "btc", "cryptocurrency", "crypto"],
            "ETH": ["ethereum", "eth", "ether", "ethereum network"]
        }
        
        logger.info("ExternalDataAnalyzer inicializado")
    
    async def __aenter__(self):
        """Context manager entry"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self._session:
            await self._session.close()
        self._executor.shutdown(wait=True)
    
    async def get_comprehensive_analysis(self, symbol: str) -> Dict[str, Any]:
        """Obtiene análisis completo de datos externos"""
        logger.info(f"Obteniendo análisis completo para {symbol}")
        
        try:
            # Verificar cache
            cache_key = f"analysis_{symbol}"
            if self._is_cache_valid(cache_key):
                logger.debug(f"Usando cache para análisis de {symbol}")
                return self._get_cached_analysis(cache_key)
            
            # Obtener datos en paralelo
            tasks = [
                self._get_news_sentiment(symbol),
                self._get_social_sentiment(symbol),
                self._get_fear_greed_index(),
                self._get_trend_sentiment(symbol),
                self._get_volume_sentiment(symbol)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Procesar resultados
            news_sentiment = results[0] if not isinstance(results[0], Exception) else 0.0
            social_sentiment = results[1] if not isinstance(results[1], Exception) else 0.0
            fear_greed = results[2] if not isinstance(results[2], Exception) else 50.0
            trend_sentiment = results[3] if not isinstance(results[3], Exception) else 0.0
            volume_sentiment = results[4] if not isinstance(results[4], Exception) else 0.0
            
            # Calcular sentiment general
            market_sentiment = self._calculate_overall_sentiment(
                news_sentiment, social_sentiment, fear_greed, trend_sentiment, volume_sentiment
            )
            
            # Generar señales
            external_signals = await self._generate_external_signals(symbol, market_sentiment)
            
            # Obtener noticias relevantes
            recent_news = await self._get_recent_news(symbol)
            
            # Compilar análisis
            analysis = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'market_sentiment': market_sentiment.to_dict(),
                'external_signals': [signal.to_dict() for signal in external_signals],
                'recent_news': [news.to_dict() for news in recent_news[:5]],  # Top 5
                'analysis_summary': self._generate_analysis_summary(market_sentiment, external_signals),
                'trading_recommendation': self._generate_trading_recommendation(market_sentiment, external_signals)
            }
            
            # Guardar en cache
            self._cache_timestamps[cache_key] = datetime.now()
            self._sentiment_cache[cache_key] = analysis
            
            logger.info(f"Análisis completo generado para {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error en análisis completo para {symbol}: {e}")
            return self._get_fallback_analysis(symbol)
    
    async def _get_news_sentiment(self, symbol: str) -> float:
        """Obtiene sentiment de noticias"""
        try:
            news_items = await self._fetch_news_for_symbol(symbol)
            
            if not news_items:
                return 0.0
            
            # Calcular sentiment promedio ponderado por relevancia
            total_weight = 0
            weighted_sentiment = 0
            
            for news in news_items:
                weight = news.relevance_score
                weighted_sentiment += news.sentiment_score * weight
                total_weight += weight
            
            return weighted_sentiment / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error obteniendo sentiment de noticias: {e}")
            return 0.0
    
    async def _get_social_sentiment(self, symbol: str) -> float:
        """Obtiene sentiment de redes sociales"""
        try:
            # Simular sentiment de redes sociales
            # En implementación real, conectar con APIs de Twitter, Reddit, etc.
            
            # Generar sentiment basado en volatilidad y tendencia reciente
            base_sentiment = np.random.normal(0, 0.3)
            
            # Ajustar por símbolo
            if symbol in ["BTC", "ETH"]:
                base_sentiment *= 0.8  # Menos volátil
            elif symbol in ["SOL", "BNB"]:
                base_sentiment *= 1.2  # Más volátil
            
            return np.clip(base_sentiment, -1, 1)
            
        except Exception as e:
            logger.error(f"Error obteniendo sentiment social: {e}")
            return 0.0
    
    async def _get_fear_greed_index(self) -> float:
        """Obtiene índice de miedo y codicia"""
        try:
            # Simular índice de miedo y codicia
            # En implementación real, usar API de Alternative.me
            
            if self._session:
                try:
                    async with self._session.get(
                        "https://api.alternative.me/fng/",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            return float(data['data'][0]['value'])
                except:
                    pass
            
            # Fallback: generar índice simulado
            return np.random.uniform(20, 80)
            
        except Exception as e:
            logger.error(f"Error obteniendo índice miedo/codicia: {e}")
            return 50.0  # Neutral
    
    async def _get_trend_sentiment(self, symbol: str) -> float:
        """Obtiene sentiment de tendencias de búsqueda"""
        try:
            # Simular sentiment de Google Trends
            # En implementación real, usar pytrends
            
            # Generar tendencia basada en símbolo
            if symbol == "BTC":
                trend_sentiment = np.random.normal(0.1, 0.2)
            elif symbol == "ETH":
                trend_sentiment = np.random.normal(0.05, 0.15)
            elif symbol == "SOL":
                trend_sentiment = np.random.normal(0.15, 0.25)
            elif symbol == "BNB":
                trend_sentiment = np.random.normal(0.08, 0.18)
            else:
                trend_sentiment = np.random.normal(0, 0.1)
            
            return np.clip(trend_sentiment, -1, 1)
            
        except Exception as e:
            logger.error(f"Error obteniendo sentiment de tendencias: {e}")
            return 0.0
    
    async def _get_volume_sentiment(self, symbol: str) -> float:
        """Obtiene sentiment basado en volumen"""
        try:
            # Simular análisis de volumen
            # En implementación real, analizar volumen de trading vs promedio
            
            # Generar sentiment de volumen
            volume_ratio = np.random.uniform(0.5, 2.0)  # Ratio vs promedio
            
            if volume_ratio > 1.5:
                return 0.3  # Alto volumen = bullish
            elif volume_ratio > 1.2:
                return 0.1  # Volumen moderado
            elif volume_ratio < 0.7:
                return -0.2  # Bajo volumen = bearish
            else:
                return 0.0  # Volumen normal
            
        except Exception as e:
            logger.error(f"Error obteniendo sentiment de volumen: {e}")
            return 0.0
    
    async def _fetch_news_for_symbol(self, symbol: str) -> List[NewsItem]:
        """Obtiene noticias para un símbolo"""
        try:
            all_news = []
            
            # Obtener noticias de cada fuente habilitada
            for source in self.config.enabled_sources:
                if source in self._news_urls:
                    source_news = await self._fetch_news_from_source(source, symbol)
                    all_news.extend(source_news)
                    
                    # Delay para rate limiting
                    await asyncio.sleep(self.config.rate_limit_delay)
            
            # Filtrar por relevancia
            relevant_news = [
                news for news in all_news 
                if news.relevance_score >= self.config.min_relevance_score
            ]
            
            # Ordenar por relevancia y timestamp
            relevant_news.sort(key=lambda x: (x.relevance_score, x.timestamp), reverse=True)
            
            return relevant_news[:self.config.max_news_per_source]
            
        except Exception as e:
            logger.error(f"Error obteniendo noticias para {symbol}: {e}")
            return []
    
    async def _fetch_news_from_source(self, source: NewsSource, symbol: str) -> List[NewsItem]:
        """Obtiene noticias de una fuente específica"""
        try:
            if not self._session:
                return []
            
            url = self._news_urls.get(source)
            if not url:
                return []
            
            # Obtener feed RSS
            async with self._session.get(url) as response:
                if response.status != 200:
                    return []
                
                content = await response.text()
            
            # Parsear RSS en thread separado
            news_items = await asyncio.get_event_loop().run_in_executor(
                self._executor, self._parse_rss_feed, content, source.value, symbol
            )
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error obteniendo noticias de {source.value}: {e}")
            return []
    
    def _parse_rss_feed(self, content: str, source: str, symbol: str) -> List[NewsItem]:
        """Parsea feed RSS"""
        try:
            feed = feedparser.parse(content)
            news_items = []
            
            cutoff_time = datetime.now() - timedelta(hours=self.config.news_lookback_hours)
            
            for entry in feed.entries[:self.config.max_news_per_source]:
                try:
                    # Extraer información
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    link = entry.get('link', '')
                    
                    # Parsear timestamp
                    pub_date = entry.get('published_parsed')
                    if pub_date:
                        timestamp = datetime(*pub_date[:6])
                    else:
                        timestamp = datetime.now()
                    
                    # Filtrar por tiempo
                    if timestamp < cutoff_time:
                        continue
                    
                    # Calcular relevancia
                    relevance = self._calculate_news_relevance(title + " " + summary, symbol)
                    
                    if relevance < self.config.min_relevance_score:
                        continue
                    
                    # Calcular sentiment
                    sentiment = self._calculate_text_sentiment(title + " " + summary)
                    
                    # Extraer keywords
                    keywords = self._extract_keywords(title + " " + summary, symbol)
                    
                    # Determinar impacto
                    impact = self._determine_impact_level(title, summary, relevance)
                    
                    news_item = NewsItem(
                        title=title,
                        content=summary,
                        source=source,
                        timestamp=timestamp,
                        url=link,
                        sentiment_score=sentiment,
                        relevance_score=relevance,
                        keywords=keywords,
                        impact_level=impact
                    )
                    
                    news_items.append(news_item)
                    
                except Exception as e:
                    logger.debug(f"Error procesando entrada de feed: {e}")
                    continue
            
            return news_items
            
        except Exception as e:
            logger.error(f"Error parseando RSS feed: {e}")
            return []
    
    def _calculate_news_relevance(self, text: str, symbol: str) -> float:
        """Calcula relevancia de noticia para símbolo"""
        try:
            text_lower = text.lower()
            keywords = self._symbol_keywords.get(symbol, [])
            
            # Contar menciones de keywords
            relevance_score = 0.0
            
            for keyword in keywords:
                count = text_lower.count(keyword.lower())
                if count > 0:
                    relevance_score += min(count * 0.2, 0.5)  # Máximo 0.5 por keyword
            
            # Bonus por menciones en título vs contenido
            title_mentions = sum(1 for kw in keywords if kw.lower() in text_lower[:100])
            if title_mentions > 0:
                relevance_score += 0.3
            
            # Palabras clave generales de crypto
            crypto_keywords = ['crypto', 'blockchain', 'defi', 'trading', 'market', 'price']
            crypto_mentions = sum(1 for kw in crypto_keywords if kw in text_lower)
            relevance_score += min(crypto_mentions * 0.1, 0.3)
            
            return min(relevance_score, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculando relevancia: {e}")
            return 0.0
    
    def _calculate_text_sentiment(self, text: str) -> float:
        """Calcula sentiment de texto"""
        try:
            # Usar TextBlob para análisis básico
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 a 1
            
            # Ajustar por palabras clave específicas de crypto
            bullish_words = ['bull', 'bullish', 'rise', 'surge', 'pump', 'moon', 'gain', 'profit']
            bearish_words = ['bear', 'bearish', 'fall', 'crash', 'dump', 'loss', 'decline']
            
            text_lower = text.lower()
            
            bullish_count = sum(1 for word in bullish_words if word in text_lower)
            bearish_count = sum(1 for word in bearish_words if word in text_lower)
            
            # Ajustar sentiment
            crypto_sentiment = (bullish_count - bearish_count) * 0.1
            final_sentiment = polarity + crypto_sentiment
            
            return np.clip(final_sentiment, -1, 1)
            
        except Exception as e:
            logger.error(f"Error calculando sentiment: {e}")
            return 0.0
    
    def _extract_keywords(self, text: str, symbol: str) -> List[str]:
        """Extrae keywords relevantes"""
        try:
            # Keywords específicos del símbolo
            symbol_keywords = self._symbol_keywords.get(symbol, [])
            
            # Keywords generales
            general_keywords = [
                'price', 'trading', 'market', 'volume', 'bullish', 'bearish',
                'support', 'resistance', 'breakout', 'rally', 'correction'
            ]
            
            text_lower = text.lower()
            found_keywords = []
            
            # Buscar keywords
            for keyword in symbol_keywords + general_keywords:
                if keyword.lower() in text_lower:
                    found_keywords.append(keyword)
            
            return list(set(found_keywords))  # Eliminar duplicados
            
        except Exception as e:
            logger.error(f"Error extrayendo keywords: {e}")
            return []
    
    def _determine_impact_level(self, title: str, content: str, relevance: float) -> str:
        """Determina nivel de impacto de noticia"""
        try:
            # Palabras de alto impacto
            high_impact_words = [
                'regulation', 'ban', 'approval', 'partnership', 'acquisition',
                'hack', 'exploit', 'upgrade', 'launch', 'listing'
            ]
            
            # Palabras de impacto medio
            medium_impact_words = [
                'analysis', 'prediction', 'forecast', 'trend', 'movement',
                'support', 'resistance', 'technical'
            ]
            
            text = (title + " " + content).lower()
            
            # Verificar impacto alto
            if any(word in text for word in high_impact_words) or relevance > 0.8:
                return "high"
            
            # Verificar impacto medio
            if any(word in text for word in medium_impact_words) or relevance > 0.5:
                return "medium"
            
            return "low"
            
        except Exception as e:
            logger.error(f"Error determinando impacto: {e}")
            return "low"
    
    def _calculate_overall_sentiment(self, news_sentiment: float, social_sentiment: float,
                                   fear_greed: float, trend_sentiment: float, 
                                   volume_sentiment: float) -> MarketSentiment:
        """Calcula sentiment general del mercado"""
        try:
            # Normalizar fear_greed (0-100 a -1 a 1)
            normalized_fear_greed = (fear_greed - 50) / 50
            
            # Calcular sentiment ponderado
            overall_sentiment = (
                news_sentiment * self.config.sentiment_weight_news +
                social_sentiment * self.config.sentiment_weight_social +
                normalized_fear_greed * self.config.sentiment_weight_fear_greed +
                trend_sentiment * self.config.sentiment_weight_trends +
                volume_sentiment * self.config.sentiment_weight_volume
            )
            
            # Determinar tipo de sentiment
            if overall_sentiment >= 0.5:
                sentiment_type = SentimentType.VERY_BULLISH
            elif overall_sentiment >= 0.2:
                sentiment_type = SentimentType.BULLISH
            elif overall_sentiment <= -0.5:
                sentiment_type = SentimentType.VERY_BEARISH
            elif overall_sentiment <= -0.2:
                sentiment_type = SentimentType.BEARISH
            else:
                sentiment_type = SentimentType.NEUTRAL
            
            # Calcular confianza basada en consistencia
            sentiments = [news_sentiment, social_sentiment, normalized_fear_greed, 
                         trend_sentiment, volume_sentiment]
            sentiment_std = np.std(sentiments)
            confidence = max(0.1, 1 - sentiment_std)  # Menor desviación = mayor confianza
            
            return MarketSentiment(
                overall_sentiment=overall_sentiment,
                sentiment_type=sentiment_type,
                confidence=confidence,
                news_sentiment=news_sentiment,
                social_sentiment=social_sentiment,
                fear_greed_index=fear_greed,
                trend_sentiment=trend_sentiment,
                volume_sentiment=volume_sentiment,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error calculando sentiment general: {e}")
            return MarketSentiment(
                overall_sentiment=0.0,
                sentiment_type=SentimentType.NEUTRAL,
                confidence=0.5,
                news_sentiment=0.0,
                social_sentiment=0.0,
                fear_greed_index=50.0,
                trend_sentiment=0.0,
                volume_sentiment=0.0,
                timestamp=datetime.now()
            )
    
    async def _generate_external_signals(self, symbol: str, sentiment: MarketSentiment) -> List[ExternalSignal]:
        """Genera señales basadas en datos externos"""
        signals = []
        
        try:
            # Señal de sentiment general
            if abs(sentiment.overall_sentiment) >= self.config.signal_threshold_weak:
                strength = min(abs(sentiment.overall_sentiment), 1.0)
                direction = 1 if sentiment.overall_sentiment > 0 else -1
                
                signals.append(ExternalSignal(
                    signal_type="sentiment_overall",
                    strength=strength,
                    direction=direction,
                    confidence=sentiment.confidence,
                    source="external_analyzer",
                    timestamp=datetime.now(),
                    metadata={
                        'sentiment_type': sentiment.sentiment_type.name,
                        'components': {
                            'news': sentiment.news_sentiment,
                            'social': sentiment.social_sentiment,
                            'fear_greed': sentiment.fear_greed_index,
                            'trends': sentiment.trend_sentiment,
                            'volume': sentiment.volume_sentiment
                        }
                    }
                ))
            
            # Señal de noticias específica
            if abs(sentiment.news_sentiment) >= self.config.signal_threshold_medium:
                signals.append(ExternalSignal(
                    signal_type="news_sentiment",
                    strength=abs(sentiment.news_sentiment),
                    direction=1 if sentiment.news_sentiment > 0 else -1,
                    confidence=sentiment.confidence * 0.8,  # Menor confianza para noticias solas
                    source="news_analysis",
                    timestamp=datetime.now(),
                    metadata={'news_sentiment': sentiment.news_sentiment}
                ))
            
            # Señal de miedo/codicia extremo
            if sentiment.fear_greed_index <= 20 or sentiment.fear_greed_index >= 80:
                # Contrarian signal - miedo extremo = oportunidad de compra
                direction = -1 if sentiment.fear_greed_index >= 80 else 1
                strength = abs(sentiment.fear_greed_index - 50) / 50
                
                signals.append(ExternalSignal(
                    signal_type="fear_greed_extreme",
                    strength=strength,
                    direction=direction,
                    confidence=0.7,
                    source="fear_greed_index",
                    timestamp=datetime.now(),
                    metadata={
                        'fear_greed_value': sentiment.fear_greed_index,
                        'signal_type': 'contrarian'
                    }
                ))
            
            # Señal de volumen anómalo
            if abs(sentiment.volume_sentiment) >= self.config.signal_threshold_medium:
                signals.append(ExternalSignal(
                    signal_type="volume_anomaly",
                    strength=abs(sentiment.volume_sentiment),
                    direction=1 if sentiment.volume_sentiment > 0 else -1,
                    confidence=0.6,
                    source="volume_analysis",
                    timestamp=datetime.now(),
                    metadata={'volume_sentiment': sentiment.volume_sentiment}
                ))
            
            logger.debug(f"Generadas {len(signals)} señales externas para {symbol}")
            return signals
            
        except Exception as e:
            logger.error(f"Error generando señales externas: {e}")
            return []
    
    async def _get_recent_news(self, symbol: str) -> List[NewsItem]:
        """Obtiene noticias recientes"""
        try:
            return await self._fetch_news_for_symbol(symbol)
        except Exception as e:
            logger.error(f"Error obteniendo noticias recientes: {e}")
            return []
    
    def _generate_analysis_summary(self, sentiment: MarketSentiment, signals: List[ExternalSignal]) -> str:
        """Genera resumen de análisis"""
        try:
            summary_parts = []
            
            # Sentiment general
            sentiment_desc = {
                SentimentType.VERY_BULLISH: "muy alcista",
                SentimentType.BULLISH: "alcista",
                SentimentType.NEUTRAL: "neutral",
                SentimentType.BEARISH: "bajista",
                SentimentType.VERY_BEARISH: "muy bajista"
            }
            
            summary_parts.append(
                f"Sentiment general: {sentiment_desc[sentiment.sentiment_type]} "
                f"(confianza: {sentiment.confidence:.1%})"
            )
            
            # Componentes principales
            if abs(sentiment.news_sentiment) > 0.3:
                news_trend = "positivas" if sentiment.news_sentiment > 0 else "negativas"
                summary_parts.append(f"Noticias predominantemente {news_trend}")
            
            if sentiment.fear_greed_index <= 25:
                summary_parts.append("Miedo extremo en el mercado (oportunidad contrarian)")
            elif sentiment.fear_greed_index >= 75:
                summary_parts.append("Codicia extrema en el mercado (precaución)")
            
            # Señales activas
            strong_signals = [s for s in signals if s.strength >= self.config.signal_threshold_strong]
            if strong_signals:
                signal_directions = [s.direction for s in strong_signals]
                if sum(signal_directions) > 0:
                    summary_parts.append(f"{len(strong_signals)} señales fuertes alcistas")
                else:
                    summary_parts.append(f"{len(strong_signals)} señales fuertes bajistas")
            
            return ". ".join(summary_parts) + "."
            
        except Exception as e:
            logger.error(f"Error generando resumen: {e}")
            return "Análisis externo completado con datos limitados."
    
    def _generate_trading_recommendation(self, sentiment: MarketSentiment, signals: List[ExternalSignal]) -> Dict[str, Any]:
        """Genera recomendación de trading"""
        try:
            # Calcular score agregado de señales
            total_signal_score = 0
            signal_count = 0
            
            for signal in signals:
                weighted_score = signal.strength * signal.direction * signal.confidence
                total_signal_score += weighted_score
                signal_count += 1
            
            avg_signal_score = total_signal_score / signal_count if signal_count > 0 else 0
            
            # Combinar con sentiment general
            combined_score = (
                sentiment.overall_sentiment * 0.6 +
                avg_signal_score * 0.4
            ) * sentiment.confidence
            
            # Determinar recomendación
            if combined_score >= 0.4:
                action = "BUY"
                confidence = "HIGH" if combined_score >= 0.6 else "MEDIUM"
            elif combined_score <= -0.4:
                action = "SELL"
                confidence = "HIGH" if combined_score <= -0.6 else "MEDIUM"
            else:
                action = "HOLD"
                confidence = "LOW"
            
            # Calcular intensidad de posición sugerida
            position_intensity = min(abs(combined_score), 0.5)  # Máximo 50% basado en externos
            
            return {
                'action': action,
                'confidence': confidence,
                'combined_score': combined_score,
                'position_intensity': position_intensity,
                'reasoning': self._generate_reasoning(sentiment, signals, combined_score),
                'risk_factors': self._identify_risk_factors(sentiment, signals)
            }
            
        except Exception as e:
            logger.error(f"Error generando recomendación: {e}")
            return {
                'action': 'HOLD',
                'confidence': 'LOW',
                'combined_score': 0.0,
                'position_intensity': 0.0,
                'reasoning': 'Datos insuficientes para recomendación',
                'risk_factors': ['Análisis externo limitado']
            }
    
    def _generate_reasoning(self, sentiment: MarketSentiment, signals: List[ExternalSignal], score: float) -> str:
        """Genera razonamiento para recomendación"""
        reasons = []
        
        if abs(sentiment.overall_sentiment) > 0.3:
            direction = "alcista" if sentiment.overall_sentiment > 0 else "bajista"
            reasons.append(f"Sentiment general {direction}")
        
        strong_signals = [s for s in signals if s.strength >= 0.6]
        if strong_signals:
            reasons.append(f"{len(strong_signals)} señales fuertes detectadas")
        
        if sentiment.fear_greed_index <= 25:
            reasons.append("Oportunidad contrarian por miedo extremo")
        elif sentiment.fear_greed_index >= 75:
            reasons.append("Precaución por codicia extrema")
        
        if abs(sentiment.news_sentiment) > 0.4:
            news_tone = "positivo" if sentiment.news_sentiment > 0 else "negativo"
            reasons.append(f"Tono de noticias {news_tone}")
        
        return "; ".join(reasons) if reasons else "Análisis neutral"
    
    def _identify_risk_factors(self, sentiment: MarketSentiment, signals: List[ExternalSignal]) -> List[str]:
        """Identifica factores de riesgo"""
        risks = []
        
        if sentiment.confidence < 0.5:
            risks.append("Baja confianza en análisis de sentiment")
        
        if len(signals) < 2:
            risks.append("Pocas señales externas disponibles")
        
        conflicting_signals = len([s for s in signals if s.direction > 0]) > 0 and len([s for s in signals if s.direction < 0]) > 0
        if conflicting_signals:
            risks.append("Señales contradictorias detectadas")
        
        if sentiment.fear_greed_index >= 80:
            risks.append("Mercado en zona de codicia extrema")
        
        # Verificar volatilidad de sentiment
        sentiments = [sentiment.news_sentiment, sentiment.social_sentiment, 
                     sentiment.trend_sentiment, sentiment.volume_sentiment]
        if np.std(sentiments) > 0.5:
            risks.append("Alta volatilidad en componentes de sentiment")
        
        return risks if risks else ["Riesgos externos mínimos"]
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Verifica si el cache es válido"""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_time = self._cache_timestamps[cache_key]
        expiry_time = cache_time + timedelta(minutes=self.config.cache_duration_minutes)
        
        return datetime.now() < expiry_time
    
    def _get_cached_analysis(self, cache_key: str) -> Dict[str, Any]:
        """Obtiene análisis del cache"""
        return self._sentiment_cache.get(cache_key, {})
    
    def _get_fallback_analysis(self, symbol: str) -> Dict[str, Any]:
        """Obtiene análisis de fallback"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'market_sentiment': {
                'overall_sentiment': 0.0,
                'sentiment_type': 'NEUTRAL',
                'confidence': 0.3,
                'news_sentiment': 0.0,
                'social_sentiment': 0.0,
                'fear_greed_index': 50.0,
                'trend_sentiment': 0.0,
                'volume_sentiment': 0.0
            },
            'external_signals': [],
            'recent_news': [],
            'analysis_summary': 'Análisis externo limitado por falta de datos.',
            'trading_recommendation': {
                'action': 'HOLD',
                'confidence': 'LOW',
                'combined_score': 0.0,
                'position_intensity': 0.0,
                'reasoning': 'Datos insuficientes',
                'risk_factors': ['Análisis externo no disponible']
            }
        }

if __name__ == "__main__":
    # Ejemplo de uso
    async def main():
        print("=== ANÁLISIS DE DATOS EXTERNOS ===")
        
        config = ExternalAnalysisConfig(
            enabled_sources=[NewsSource.COINDESK, NewsSource.FEAR_GREED],
            news_lookback_hours=12,
            max_news_per_source=10
        )
        
        async with ExternalDataAnalyzer(config) as analyzer:
            # Analizar BNB
            print("\nAnalizando BNBUSDT...")
            bnb_analysis = await analyzer.get_comprehensive_analysis("BNB")
            
            print(f"Sentiment: {bnb_analysis['market_sentiment']['sentiment_type']}")
            print(f"Score: {bnb_analysis['market_sentiment']['overall_sentiment']:.2f}")
            print(f"Confianza: {bnb_analysis['market_sentiment']['confidence']:.1%}")
            print(f"Recomendación: {bnb_analysis['trading_recommendation']['action']}")
            print(f"Señales: {len(bnb_analysis['external_signals'])}")
            print(f"Noticias: {len(bnb_analysis['recent_news'])}")
            
            # Analizar SOL
            print("\nAnalizando SOLUSDT...")
            sol_analysis = await analyzer.get_comprehensive_analysis("SOL")
            
            print(f"Sentiment: {sol_analysis['market_sentiment']['sentiment_type']}")
            print(f"Score: {sol_analysis['market_sentiment']['overall_sentiment']:.2f}")
            print(f"Confianza: {sol_analysis['market_sentiment']['confidence']:.1%}")
            print(f"Recomendación: {sol_analysis['trading_recommendation']['action']}")
            print(f"Señales: {len(sol_analysis['external_signals'])}")
            print(f"Noticias: {len(sol_analysis['recent_news'])}")
    
    # Ejecutar
    asyncio.run(main())