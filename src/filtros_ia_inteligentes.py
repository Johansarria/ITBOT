#!/usr/bin/env python3
"""
Sistema de Filtros Inteligentes con IA Continua
Implementa filtros avanzados usando análisis de IA para mejorar decisiones de trading
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
import requests
from typing import Dict, List, Optional, Tuple
import threading
from dataclasses import dataclass
import os

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | FILTROS_IA | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('filtros_ia_inteligentes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MarketSignal:
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float  # 0-100
    reasoning: str
    timestamp: datetime
    technical_score: float
    sentiment_score: float
    volume_score: float
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH'

class IntelligentFiltersAI:
    def __init__(self):
        self.config = self.load_config()
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        self.running = False
        self.last_analysis = {}
        
        # Parámetros de filtros inteligentes - AJUSTADOS PARA MAYOR SENSIBILIDAD
        self.min_confidence = 25.0  # Reducido de 70.0 a 25.0
        self.min_volume_threshold = 500000   # Reducido de 1M a 500K USDT
        self.max_risk_level = 'HIGH'  # Cambiado de MEDIUM a HIGH para permitir más señales
        
        # Historial para análisis de tendencias
        self.signal_history = []
        self.market_memory = {}
        
    def load_config(self) -> Dict:
        """Cargar configuración"""
        try:
            with open('sicar_config.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return {}
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Obtener datos de mercado en tiempo real"""
        try:
            # Datos de precio
            ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            ticker_response = requests.get(ticker_url, timeout=10)
            ticker_data = ticker_response.json()
            
            # Datos de velas
            klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
            klines_response = requests.get(klines_url, timeout=10)
            klines_data = klines_response.json()
            
            return {
                'ticker': ticker_data,
                'klines': klines_data,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return None
    
    def calculate_technical_score(self, klines_data: List) -> float:
        """Calcular puntuación técnica basada en indicadores"""
        try:
            # Convertir a DataFrame
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convertir a números
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            # Calcular indicadores
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            df['rsi'] = self.calculate_rsi(df['close'])
            
            # Puntuación basada en tendencias
            current_price = df['close'].iloc[-1]
            sma_20 = df['sma_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            rsi = df['rsi'].iloc[-1]
            
            score = 50  # Base neutral
            
            # Análisis de medias móviles
            if current_price > sma_20 > sma_50:
                score += 20  # Tendencia alcista fuerte
            elif current_price > sma_20:
                score += 10  # Tendencia alcista moderada
            elif current_price < sma_20 < sma_50:
                score -= 20  # Tendencia bajista fuerte
            elif current_price < sma_20:
                score -= 10  # Tendencia bajista moderada
            
            # Análisis RSI
            if 30 <= rsi <= 70:
                score += 10  # RSI en zona neutral (bueno)
            elif rsi < 30:
                score += 15  # Sobreventa (oportunidad de compra)
            elif rsi > 70:
                score -= 15  # Sobrecompra (riesgo)
            
            # Análisis de volumen
            avg_volume = df['volume'].tail(20).mean()
            current_volume = df['volume'].iloc[-1]
            
            if current_volume > avg_volume * 1.5:
                score += 15  # Volumen alto (confirmación)
            elif current_volume < avg_volume * 0.5:
                score -= 10  # Volumen bajo (debilidad)
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error calculando puntuación técnica: {e}")
            return 50
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcular RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_sentiment_score(self, symbol: str, ticker_data: Dict) -> float:
        """Calcular puntuación de sentimiento basada en datos de mercado"""
        try:
            # Análisis de cambio de precio
            price_change = float(ticker_data['priceChangePercent'])
            
            score = 50  # Base neutral
            
            # Puntuación basada en cambio de precio
            if price_change > 5:
                score += 25  # Muy positivo
            elif price_change > 2:
                score += 15  # Positivo
            elif price_change > 0:
                score += 5   # Ligeramente positivo
            elif price_change < -5:
                score -= 25  # Muy negativo
            elif price_change < -2:
                score -= 15  # Negativo
            elif price_change < 0:
                score -= 5   # Ligeramente negativo
            
            # Análisis de spread bid-ask (usando datos disponibles)
            high = float(ticker_data['highPrice'])
            low = float(ticker_data['lowPrice'])
            current = float(ticker_data['lastPrice'])
            
            # Posición dentro del rango del día
            if high != low:
                position_in_range = (current - low) / (high - low)
                if position_in_range > 0.8:
                    score += 10  # Cerca del máximo
                elif position_in_range < 0.2:
                    score -= 10  # Cerca del mínimo
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error calculando sentimiento para {symbol}: {e}")
            return 50
    
    def calculate_volume_score(self, ticker_data: Dict) -> float:
        """Calcular puntuación de volumen"""
        try:
            volume_24h = float(ticker_data['quoteVolume'])
            count_24h = int(ticker_data['count'])
            
            score = 50  # Base neutral
            
            # Análisis de volumen
            if volume_24h > 1000000000:  # > 1B USDT
                score += 20
            elif volume_24h > 500000000:  # > 500M USDT
                score += 15
            elif volume_24h > 100000000:  # > 100M USDT
                score += 10
            elif volume_24h < 10000000:   # < 10M USDT
                score -= 20
            
            # Análisis de número de trades
            if count_24h > 1000000:
                score += 10
            elif count_24h > 500000:
                score += 5
            elif count_24h < 100000:
                score -= 10
            
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"Error calculando puntuación de volumen: {e}")
            return 50
    
    def determine_risk_level(self, technical_score: float, sentiment_score: float, volume_score: float) -> str:
        """Determinar nivel de riesgo"""
        avg_score = (technical_score + sentiment_score + volume_score) / 3
        
        if avg_score >= 75:
            return 'LOW'
        elif avg_score >= 50:
            return 'MEDIUM'
        else:
            return 'HIGH'
    
    def generate_signal(self, symbol: str, market_data: Dict) -> Optional[MarketSignal]:
        """Generar señal de trading usando IA"""
        try:
            ticker_data = market_data['ticker']
            klines_data = market_data['klines']
            
            # Calcular puntuaciones
            technical_score = self.calculate_technical_score(klines_data)
            sentiment_score = self.calculate_sentiment_score(symbol, ticker_data)
            volume_score = self.calculate_volume_score(ticker_data)
            
            # Calcular confianza general
            confidence = (technical_score + sentiment_score + volume_score) / 3
            
            # Determinar tipo de señal - UMBRALES AJUSTADOS PARA MAYOR SENSIBILIDAD
            if confidence >= 55:  # Reducido de 70 a 55
                signal_type = 'BUY'
                reasoning = f"Señal de COMPRA: Técnico={technical_score:.1f}, Sentimiento={sentiment_score:.1f}, Volumen={volume_score:.1f}"
            elif confidence <= 45:  # Aumentado de 30 a 45
                signal_type = 'SELL'
                reasoning = f"Señal de VENTA: Técnico={technical_score:.1f}, Sentimiento={sentiment_score:.1f}, Volumen={volume_score:.1f}"
            else:
                signal_type = 'HOLD'
                reasoning = f"Señal de MANTENER: Técnico={technical_score:.1f}, Sentimiento={sentiment_score:.1f}, Volumen={volume_score:.1f}"
            
            # Determinar nivel de riesgo
            risk_level = self.determine_risk_level(technical_score, sentiment_score, volume_score)
            
            return MarketSignal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                reasoning=reasoning,
                timestamp=datetime.now(),
                technical_score=technical_score,
                sentiment_score=sentiment_score,
                volume_score=volume_score,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error generando señal para {symbol}: {e}")
            return None
    
    def apply_intelligent_filters(self, signals: List[MarketSignal]) -> List[MarketSignal]:
        """Aplicar filtros inteligentes a las señales"""
        filtered_signals = []
        
        for signal in signals:
            # Filtro de confianza mínima
            if signal.confidence < self.min_confidence:
                continue
            
            # Filtro de nivel de riesgo
            if signal.risk_level == 'HIGH' and self.max_risk_level != 'HIGH':
                continue
            
            # Filtro de volumen (usando volume_score como proxy) - AJUSTADO
            if signal.volume_score < 20:  # Reducido de 40 a 20 para permitir más señales
                continue
            
            # Filtro de consistencia temporal
            if self.is_signal_consistent(signal):
                filtered_signals.append(signal)
        
        return filtered_signals
    
    def is_signal_consistent(self, signal: MarketSignal) -> bool:
        """Verificar consistencia de la señal con el historial"""
        # Buscar señales recientes del mismo símbolo
        recent_signals = [
            s for s in self.signal_history[-10:]  # Últimas 10 señales
            if s.symbol == signal.symbol and 
            (datetime.now() - s.timestamp).total_seconds() < 3600  # Última hora
        ]
        
        if not recent_signals:
            return True  # Primera señal, aceptar
        
        # Verificar consistencia
        same_type_count = sum(1 for s in recent_signals if s.signal_type == signal.signal_type)
        
        # Si más del 40% de señales recientes son del mismo tipo, es consistente (reducido de 60% a 40%)
        return same_type_count / len(recent_signals) >= 0.4
    
    def save_signals_to_file(self, signals: List[MarketSignal]):
        """Guardar señales en archivo"""
        try:
            signals_data = []
            for signal in signals:
                signals_data.append({
                    'symbol': signal.symbol,
                    'signal_type': signal.signal_type,
                    'confidence': signal.confidence,
                    'reasoning': signal.reasoning,
                    'timestamp': signal.timestamp.isoformat(),
                    'technical_score': signal.technical_score,
                    'sentiment_score': signal.sentiment_score,
                    'volume_score': signal.volume_score,
                    'risk_level': signal.risk_level
                })
            
            with open('filtros_ia_signals.json', 'w') as f:
                json.dump(signals_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error guardando señales: {e}")
    
    def display_signals(self, signals: List[MarketSignal]):
        """Mostrar señales en consola con formato avanzado"""
        if not signals:
            print("🔍 No hay señales que cumplan los filtros inteligentes")
            return
        
        print("\n" + "="*100)
        print("🧠 FILTROS INTELIGENTES IA - SEÑALES DETECTADAS")
        print("="*100)
        
        for signal in signals:
            # Emoji según tipo de señal
            emoji = "🟢" if signal.signal_type == "BUY" else "🔴" if signal.signal_type == "SELL" else "🟡"
            
            # Color de riesgo
            risk_emoji = "🟢" if signal.risk_level == "LOW" else "🟡" if signal.risk_level == "MEDIUM" else "🔴"
            
            print(f"\n{emoji} {signal.symbol} | {signal.signal_type} | Confianza: {signal.confidence:.1f}%")
            print(f"   📊 Técnico: {signal.technical_score:.1f} | 💭 Sentimiento: {signal.sentiment_score:.1f} | 📈 Volumen: {signal.volume_score:.1f}")
            print(f"   {risk_emoji} Riesgo: {signal.risk_level} | ⏰ {signal.timestamp.strftime('%H:%M:%S')}")
            print(f"   💡 {signal.reasoning}")
        
        print("="*100)
    
    def run_continuous_analysis(self):
        """Ejecutar análisis continuo"""
        logger.info("🧠 Iniciando sistema de filtros inteligentes IA...")
        self.running = True
        
        while self.running:
            try:
                all_signals = []
                
                print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Analizando mercado con IA...")
                
                for symbol in self.symbols:
                    market_data = self.get_market_data(symbol)
                    if market_data:
                        signal = self.generate_signal(symbol, market_data)
                        if signal:
                            all_signals.append(signal)
                
                # Aplicar filtros inteligentes
                filtered_signals = self.apply_intelligent_filters(all_signals)
                
                # Actualizar historial
                self.signal_history.extend(filtered_signals)
                self.signal_history = self.signal_history[-100:]  # Mantener últimas 100
                
                # Mostrar y guardar resultados
                self.display_signals(filtered_signals)
                self.save_signals_to_file(filtered_signals)
                
                # Estadísticas
                if filtered_signals:
                    avg_confidence = sum(s.confidence for s in filtered_signals) / len(filtered_signals)
                    print(f"\n📊 Estadísticas: {len(filtered_signals)} señales | Confianza promedio: {avg_confidence:.1f}%")
                
                # Esperar antes del siguiente análisis
                time.sleep(30)  # Análisis cada 30 segundos
                
            except KeyboardInterrupt:
                logger.info("🛑 Deteniendo sistema de filtros IA...")
                break
            except Exception as e:
                logger.error(f"❌ Error en análisis continuo: {e}")
                time.sleep(10)
        
        self.running = False

def main():
    """Función principal"""
    print("🧠 SISTEMA DE FILTROS INTELIGENTES CON IA CONTINUA")
    print("="*60)
    
    filters_ai = IntelligentFiltersAI()
    
    try:
        filters_ai.run_continuous_analysis()
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())