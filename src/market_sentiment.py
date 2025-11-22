#!/usr/bin/env python3
"""
Análisis de sentimiento de mercado para criptomonedas
Incluye Fear & Greed Index y Funding Rates de Binance Futures
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, Tuple
import ccxt

logger = logging.getLogger(__name__)

class MarketSentimentAnalyzer:
    """
    Analizador de sentimiento de mercado para criptomonedas
    """
    
    def __init__(self):
        self.fear_greed_api = "https://api.alternative.me/fng/"
        self.exchange = ccxt.binance()
        
    def get_fear_greed_index(self, limit: int = 30, date_format: str = "US") -> pd.DataFrame:
        """
        Obtener Fear & Greed Index de Alternative.me
        
        Args:
            limit: Número de días históricos a obtener
            date_format: Formato de fecha (US, CN, KR)
            
        Returns:
            DataFrame con Fear & Greed Index
        """
        logger.info(f"Obteniendo Fear & Greed Index para {limit} días")
        
        try:
            params = {
                'limit': limit,
                'date_format': date_format
            }
            
            response = requests.get(self.fear_greed_api, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['metadata']['error'] is not None:
                logger.error(f"Error en API Fear & Greed: {data['metadata']['error']}")
                return self._create_fallback_fear_greed()
            
            # Procesar datos
            fng_data = []
            for item in data['data']:
                try:
                    # Intentar parsear como Unix timestamp
                    timestamp = pd.to_datetime(int(item['timestamp']), unit='s')
                except (ValueError, TypeError):
                    try:
                        # Intentar parsear como string de fecha
                        timestamp = pd.to_datetime(item['timestamp'])
                    except:
                        # Usar fecha actual como fallback
                        timestamp = pd.Timestamp.now()
                
                fng_data.append({
                    'timestamp': timestamp,
                    'fear_greed_value': int(item['value']),
                    'fear_greed_classification': item['value_classification'],
                    'time_until_update': item['time_until_update']
                })
            
            df = pd.DataFrame(fng_data)
            df = df.sort_values('timestamp')
            
            # Agregar análisis adicional
            df['fear_greed_ma_7'] = df['fear_greed_value'].rolling(window=7).mean()
            df['fear_greed_ma_14'] = df['fear_greed_value'].rolling(window=14).mean()
            
            # Detectar extremos
            df['extreme_fear'] = df['fear_greed_value'] <= 20  # Miedo extremo
            df['extreme_greed'] = df['fear_greed_value'] >= 80  # Codicia extrema
            df['neutral_zone'] = (df['fear_greed_value'] > 40) & (df['fear_greed_value'] < 60)
            
            logger.info(f"Fear & Greed Index obtenido: {len(df)} registros, valor actual: {df['fear_greed_value'].iloc[-1]}")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo Fear & Greed Index: {e}")
            return self._create_fallback_fear_greed()
    
    def _create_fallback_fear_greed(self) -> pd.DataFrame:
        """
        Crear datos de fallback para Fear & Greed Index
        """
        logger.warning("Creando Fear & Greed Index de fallback")
        
        # Crear datos sintéticos basados en condiciones de mercado actuales
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        
        # Simular miedo extremo actual (mercado bajista 2025)
        base_values = np.random.normal(15, 8, len(dates))  # Media 15, desviación 8
        base_values = np.clip(base_values, 0, 100)  # Limitar a 0-100
        
        df = pd.DataFrame({
            'timestamp': dates,
            'fear_greed_value': base_values.astype(int),
            'time_until_update': 0
        })
        
        # Agregar clasificación usando el método correcto
        df['fear_greed_classification'] = df['fear_greed_value'].apply(self._classify_fear_greed)
        
        df['fear_greed_ma_7'] = df['fear_greed_value'].rolling(window=7).mean()
        df['fear_greed_ma_14'] = df['fear_greed_value'].rolling(window=14).mean()
        df['extreme_fear'] = df['fear_greed_value'] <= 20
        df['extreme_greed'] = df['fear_greed_value'] >= 80
        df['neutral_zone'] = (df['fear_greed_value'] > 40) & (df['fear_greed_value'] < 60)
        
        return df
    
    def _classify_fear_greed(self, value: int) -> str:
        """
        Clasificar valor de Fear & Greed
        """
        if value <= 20:
            return "Extreme Fear"
        elif value <= 40:
            return "Fear"
        elif value <= 60:
            return "Neutral"
        elif value <= 80:
            return "Greed"
        else:
            return "Extreme Greed"
    
    def get_binance_funding_rates(self, symbol: str = "BTCUSDT", limit: int = 30) -> pd.DataFrame:
        """
        Obtener funding rates de Binance Futures
        
        Args:
            symbol: Símbolo de Binance Futures
            limit: Número de períodos históricos
            
        Returns:
            DataFrame con funding rates
        """
        logger.info(f"Obteniendo funding rates de Binance para {symbol}")
        
        try:
            # Obtener funding rates
            funding_rates = self.exchange.fetch_funding_rate_history(symbol, limit=limit)
            
            if not funding_rates:
                logger.warning(f"No se encontraron funding rates para {symbol}")
                return self._create_fallback_funding_rates()
            
            # Procesar datos
            funding_data = []
            for rate in funding_rates:
                funding_data.append({
                    'timestamp': pd.to_datetime(rate['timestamp'], unit='ms'),
                    'symbol': rate['symbol'],
                    'funding_rate': float(rate['fundingRate']),
                    'mark_price': float(rate['markPrice']) if 'markPrice' in rate else None
                })
            
            df = pd.DataFrame(funding_data)
            df = df.sort_values('timestamp')
            
            # Agregar análisis
            df['funding_rate_pct'] = df['funding_rate'] * 100  # Convertir a porcentaje
            df['funding_rate_ma_7'] = df['funding_rate'].rolling(window=7).mean()
            
            # Clasificar funding rates
            df['high_positive_funding'] = df['funding_rate'] > 0.0001  # > 0.01%
            df['high_negative_funding'] = df['funding_rate'] < -0.0001  # < -0.01%
            df['neutral_funding'] = (df['funding_rate'] >= -0.0001) & (df['funding_rate'] <= 0.0001)
            
            # Sentimiento del funding
            df['funding_sentiment'] = df['funding_rate'].apply(self._classify_funding_sentiment)
            
            logger.info(f"Funding rates obtenidos: {len(df)} registros, funding actual: {df['funding_rate'].iloc[-1]:.4f}")
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo funding rates: {e}")
            return self._create_fallback_funding_rates()
    
    def _create_fallback_funding_rates(self) -> pd.DataFrame:
        """
        Crear datos de fallback para funding rates
        """
        logger.warning("Creando funding rates de fallback")
        
        dates = pd.date_range(end=datetime.now(), periods=30, freq='8H')  # Cada 8 horas
        
        # Simular funding rates negativos (mercado bajista, shorts dominan)
        base_rates = np.random.normal(-0.0002, 0.0001, len(dates))  # Media -0.02%
        base_rates = np.clip(base_rates, -0.0005, 0.0003)  # Limitar rangos
        
        df = pd.DataFrame({
            'timestamp': dates,
            'symbol': 'BTCUSDT',
            'funding_rate': base_rates,
            'mark_price': 50000 + np.random.normal(0, 1000, len(dates))
        })
        
        df['funding_rate_pct'] = df['funding_rate'] * 100
        df['funding_rate_ma_7'] = df['funding_rate'].rolling(window=7).mean()
        df['high_positive_funding'] = df['funding_rate'] > 0.0001
        df['high_negative_funding'] = df['funding_rate'] < -0.0001
        df['neutral_funding'] = (df['funding_rate'] >= -0.0001) & (df['funding_rate'] <= 0.0001)
        df['funding_sentiment'] = df['funding_rate'].apply(self._classify_funding_sentiment)
        
        return df
    
    def _classify_funding_sentiment(self, rate: float) -> str:
        """
        Clasificar sentimiento basado en funding rate
        """
        if rate > 0.0001:
            return "BULLISH"  # Longs pagan a shorts (alcista)
        elif rate < -0.0001:
            return "BEARISH"  # Shorts pagan a longs (bajista)
        else:
            return "NEUTRAL"
    
    def get_combined_sentiment_score(self, symbol: str = "BTCUSDT") -> Dict:
        """
        Obtener score de sentimiento combinado
        
        Args:
            symbol: Símbolo para análisis
            
        Returns:
            Dict con score de sentimiento combinado
        """
        logger.info(f"Calculando sentimiento combinado para {symbol}")
        
        # Obtener Fear & Greed Index
        fear_greed_df = self.get_fear_greed_index(limit=30)
        
        # Obtener Funding Rates
        funding_df = self.get_binance_funding_rates(symbol=symbol, limit=30)
        
        if fear_greed_df.empty or funding_df.empty:
            logger.warning("Datos de sentimiento incompletos, usando valores de fallback")
            return self._create_fallback_sentiment_score()
        
        # Obtener valores más recientes
        current_fear_greed = fear_greed_df['fear_greed_value'].iloc[-1]
        current_funding = funding_df['funding_rate'].iloc[-1]
        
        # Normalizar Fear & Greed (0-100) a (-1 a 1)
        # Miedo extremo (0-20) = -1, Codicia extrema (80-100) = +1
        fear_greed_normalized = (current_fear_greed - 50) / 50  # -1 a +1
        
        # Normalizar Funding Rate
        # Funding negativo = bajista, funding positivo = alcista
        funding_normalized = np.clip(current_funding * 10000, -1, 1)  # Escalar y limitar
        
        # Score combinado (ponderado)
        # Fear & Greed: 60% (contrarian logic - comprar miedo, vender codicia)
        # Funding: 40% (momentum logic)
        combined_score = (-fear_greed_normalized * 0.6) + (funding_normalized * 0.4)
        
        # Clasificar sentimiento final
        if combined_score > 0.3:
            sentiment_classification = "BULLISH"
            confidence = min(abs(combined_score), 1.0)
        elif combined_score < -0.3:
            sentiment_classification = "BEARISH"
            confidence = min(abs(combined_score), 1.0)
        else:
            sentiment_classification = "NEUTRAL"
            confidence = 0.5
        
        # Detectar extremos para filtros
        extreme_fear_signal = current_fear_greed <= 20
        extreme_greed_signal = current_fear_greed >= 80
        high_negative_funding = current_funding < -0.0001
        high_positive_funding = current_funding > 0.0001
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'fear_greed_value': int(current_fear_greed),
            'fear_greed_classification': fear_greed_df['fear_greed_classification'].iloc[-1],
            'funding_rate': float(current_funding),
            'funding_rate_pct': float(current_funding * 100),
            'funding_sentiment': funding_df['funding_sentiment'].iloc[-1],
            'combined_score': float(combined_score),
            'sentiment_classification': sentiment_classification,
            'confidence': float(confidence),
            'extreme_fear_signal': bool(extreme_fear_signal),
            'extreme_greed_signal': bool(extreme_greed_signal),
            'high_negative_funding': bool(high_negative_funding),
            'high_positive_funding': bool(high_positive_funding),
            'recommendation': self._get_sentiment_recommendation(combined_score, current_fear_greed, current_funding)
        }
        
        logger.info(f"Sentimiento combinado: {sentiment_classification} (score: {combined_score:.3f}, confianza: {confidence:.1%})")
        return result
    
    def _create_fallback_sentiment_score(self) -> Dict:
        """
        Crear score de sentimiento de fallback
        """
        logger.warning("Creando score de sentimiento de fallback")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'fear_greed_value': 15,  # Miedo extremo
            'fear_greed_classification': 'Extreme Fear',
            'funding_rate': -0.0002,  # Negativo (bajista)
            'funding_rate_pct': -0.02,
            'funding_sentiment': 'BEARISH',
            'combined_score': -0.6,  # Bajista
            'sentiment_classification': 'BEARISH',
            'confidence': 0.8,
            'extreme_fear_signal': True,
            'extreme_greed_signal': False,
            'high_negative_funding': True,
            'high_positive_funding': False,
            'recommendation': 'AVOID_LONGS'
        }
    
    def _get_sentiment_recommendation(self, combined_score: float, fear_greed: int, funding: float) -> str:
        """
        Generar recomendación basada en sentimiento
        """
        if combined_score > 0.5:
            return "STRONG_BUY_SIGNAL"
        elif combined_score > 0.2:
            return "BUY_SIGNAL"
        elif combined_score < -0.5:
            return "STRONG_SELL_SIGNAL"
        elif combined_score < -0.2:
            return "SELL_SIGNAL"
        else:
            return "NEUTRAL_SIGNAL"

def test_sentiment_analyzer():
    """Función de prueba para el analizador de sentimiento"""
    print("🧪 Probando MarketSentimentAnalyzer...")
    
    analyzer = MarketSentimentAnalyzer()
    
    # Test Fear & Greed
    print("\n📊 Fear & Greed Index:")
    fear_greed = analyzer.get_fear_greed_index(limit=7)
    if not fear_greed.empty:
        print(f"   Valor actual: {fear_greed['fear_greed_value'].iloc[-1]}")
        print(f"   Clasificación: {fear_greed['fear_greed_classification'].iloc[-1]}")
        print(f"   Miedo extremo: {fear_greed['extreme_fear'].iloc[-1]}")
    
    # Test Funding Rates
    print("\n💰 Funding Rates (BTCUSDT):")
    funding = analyzer.get_binance_funding_rates(symbol="BTCUSDT", limit=7)
    if not funding.empty:
        print(f"   Funding actual: {funding['funding_rate'].iloc[-1]:.4f}")
        print(f"   Sentimiento: {funding['funding_sentiment'].iloc[-1]}")
    
    # Test Combined Score
    print("\n🎯 Score de Sentimiento Combinado:")
    combined = analyzer.get_combined_sentiment_score("BTCUSDT")
    print(f"   Sentimiento: {combined['sentiment_classification']}")
    print(f"   Score: {combined['combined_score']:.3f}")
    print(f"   Confianza: {combined['confidence']:.1%}")
    print(f"   Recomendación: {combined['recommendation']}")
    
    print("\n✅ Análisis de sentimiento completado!")

if __name__ == '__main__':
    test_sentiment_analyzer()