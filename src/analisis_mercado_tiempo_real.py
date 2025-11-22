# /src/analisis_mercado_tiempo_real.py
"""
Sistema de Análisis de Mercado en Tiempo Real
Funciona en paralelo con el sistema de alertas sin interferir
"""

import asyncio
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Tuple
import colorama
from colorama import Fore, Back, Style
import os
import sys

# Importar módulos del sistema
from binance_data_provider import BinanceDataProvider
from module_xai import generate_cognitive_report
from module_1_causal import CausalCartographer
from module_2_regime import RegimeClassifier

colorama.init()

class AnalisisMercadoTiempoReal:
    def __init__(self):
        """Inicializar el sistema de análisis de mercado"""
        self.setup_logging()
        self.data_provider = BinanceDataProvider()
        self.causal_cartographer = CausalCartographer()
        self.regime_classifier = RegimeClassifier()
        
        # Símbolos principales para análisis
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
        
        # Base de datos para análisis
        self.db_path = 'analisis_mercado_tiempo_real.db'
        self.init_database()
        
        # Estado del mercado
        self.market_state = {
            'trend': 'NEUTRAL',
            'volatility': 'NORMAL',
            'sentiment': 'NEUTRAL',
            'risk_level': 'MEDIUM'
        }
        
        self.logger.info("🔍 Sistema de Análisis de Mercado en Tiempo Real inicializado")

    def setup_logging(self):
        """Configurar sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def init_database(self):
        """Inicializar base de datos para análisis"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabla para análisis de mercado
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analisis_mercado (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    precio_actual REAL,
                    volumen_24h REAL,
                    cambio_24h REAL,
                    rsi REAL,
                    macd REAL,
                    bollinger_position REAL,
                    trend_strength REAL,
                    volatility_score REAL,
                    sentiment_score REAL,
                    recomendacion TEXT,
                    confianza REAL
                )
            ''')
            
            # Tabla para estado general del mercado
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS estado_mercado (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    trend_general TEXT,
                    volatility_general TEXT,
                    sentiment_general TEXT,
                    risk_level TEXT,
                    market_cap_total REAL,
                    dominancia_btc REAL,
                    fear_greed_index INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
            self.logger.info("✅ Base de datos de análisis inicializada")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando base de datos: {e}")

    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Obtener datos de mercado para un símbolo"""
        try:
            # Obtener datos históricos
            df = self.data_provider.get_historical_data(symbol, '1m', 100)
            if df is None or df.empty:
                return None
            
            # Calcular indicadores técnicos
            current_price = float(df['close'].iloc[-1])
            volume_24h = float(df['volume'].sum())
            change_24h = ((current_price - float(df['close'].iloc[-24])) / float(df['close'].iloc[-24])) * 100
            
            # RSI
            rsi = self.calculate_rsi(df['close'])
            
            # MACD
            macd = self.calculate_macd(df['close'])
            
            # Bollinger Bands
            bollinger_pos = self.calculate_bollinger_position(df['close'])
            
            # Fuerza de tendencia
            trend_strength = self.calculate_trend_strength(df['close'])
            
            # Volatilidad
            volatility = self.calculate_volatility(df['close'])
            
            return {
                'symbol': symbol,
                'precio_actual': current_price,
                'volumen_24h': volume_24h,
                'cambio_24h': change_24h,
                'rsi': rsi,
                'macd': macd,
                'bollinger_position': bollinger_pos,
                'trend_strength': trend_strength,
                'volatility_score': volatility,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo datos para {symbol}: {e}")
            return None

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calcular RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except:
            return 50.0

    def calculate_macd(self, prices: pd.Series) -> float:
        """Calcular MACD"""
        try:
            ema12 = prices.ewm(span=12).mean()
            ema26 = prices.ewm(span=26).mean()
            macd = ema12 - ema26
            return float(macd.iloc[-1])
        except:
            return 0.0

    def calculate_bollinger_position(self, prices: pd.Series, period: int = 20) -> float:
        """Calcular posición en Bollinger Bands"""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper = sma + (std * 2)
            lower = sma - (std * 2)
            current = prices.iloc[-1]
            position = (current - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
            return float(position)
        except:
            return 0.5

    def calculate_trend_strength(self, prices: pd.Series) -> float:
        """Calcular fuerza de tendencia"""
        try:
            # Usar pendiente de regresión lineal
            x = np.arange(len(prices))
            slope = np.polyfit(x, prices, 1)[0]
            return float(slope / prices.iloc[-1] * 100)
        except:
            return 0.0

    def calculate_volatility(self, prices: pd.Series, period: int = 20) -> float:
        """Calcular volatilidad"""
        try:
            returns = prices.pct_change()
            volatility = returns.rolling(window=period).std() * np.sqrt(period)
            return float(volatility.iloc[-1] * 100)
        except:
            return 0.0

    def analyze_symbol(self, data: Dict) -> Dict:
        """Analizar un símbolo y generar recomendación"""
        try:
            # Análisis técnico
            rsi = data['rsi']
            macd = data['macd']
            bollinger_pos = data['bollinger_position']
            trend_strength = data['trend_strength']
            volatility = data['volatility_score']
            
            # Puntuación de sentimiento
            sentiment_score = 0
            
            # RSI
            if rsi < 30:
                sentiment_score += 2  # Sobreventa - bullish
            elif rsi > 70:
                sentiment_score -= 2  # Sobrecompra - bearish
            
            # MACD
            if macd > 0:
                sentiment_score += 1
            else:
                sentiment_score -= 1
            
            # Bollinger Bands
            if bollinger_pos < 0.2:
                sentiment_score += 1  # Cerca del límite inferior
            elif bollinger_pos > 0.8:
                sentiment_score -= 1  # Cerca del límite superior
            
            # Tendencia
            if trend_strength > 0.1:
                sentiment_score += 1
            elif trend_strength < -0.1:
                sentiment_score -= 1
            
            # Generar recomendación
            if sentiment_score >= 3:
                recomendacion = "COMPRA FUERTE"
                confianza = 0.8
            elif sentiment_score >= 1:
                recomendacion = "COMPRA"
                confianza = 0.6
            elif sentiment_score <= -3:
                recomendacion = "VENTA FUERTE"
                confianza = 0.8
            elif sentiment_score <= -1:
                recomendacion = "VENTA"
                confianza = 0.6
            else:
                recomendacion = "MANTENER"
                confianza = 0.4
            
            # Ajustar confianza por volatilidad
            if volatility > 5:  # Alta volatilidad
                confianza *= 0.8
            
            data['sentiment_score'] = sentiment_score
            data['recomendacion'] = recomendacion
            data['confianza'] = confianza
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando símbolo: {e}")
            data['sentiment_score'] = 0
            data['recomendacion'] = "ERROR"
            data['confianza'] = 0
            return data

    def save_analysis(self, analysis: Dict):
        """Guardar análisis en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analisis_mercado (
                    symbol, precio_actual, volumen_24h, cambio_24h,
                    rsi, macd, bollinger_position, trend_strength,
                    volatility_score, sentiment_score, recomendacion, confianza
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis['symbol'],
                analysis['precio_actual'],
                analysis['volumen_24h'],
                analysis['cambio_24h'],
                analysis['rsi'],
                analysis['macd'],
                analysis['bollinger_position'],
                analysis['trend_strength'],
                analysis['volatility_score'],
                analysis['sentiment_score'],
                analysis['recomendacion'],
                analysis['confianza']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando análisis: {e}")

    def update_market_state(self, analyses: List[Dict]):
        """Actualizar estado general del mercado"""
        try:
            if not analyses:
                return
            
            # Calcular métricas generales
            avg_sentiment = np.mean([a['sentiment_score'] for a in analyses])
            avg_volatility = np.mean([a['volatility_score'] for a in analyses])
            avg_trend = np.mean([a['trend_strength'] for a in analyses])
            
            # Determinar tendencia general
            if avg_trend > 0.1:
                self.market_state['trend'] = 'ALCISTA'
            elif avg_trend < -0.1:
                self.market_state['trend'] = 'BAJISTA'
            else:
                self.market_state['trend'] = 'LATERAL'
            
            # Determinar volatilidad
            if avg_volatility > 4:
                self.market_state['volatility'] = 'ALTA'
            elif avg_volatility < 2:
                self.market_state['volatility'] = 'BAJA'
            else:
                self.market_state['volatility'] = 'NORMAL'
            
            # Determinar sentimiento
            if avg_sentiment > 1:
                self.market_state['sentiment'] = 'OPTIMISTA'
            elif avg_sentiment < -1:
                self.market_state['sentiment'] = 'PESIMISTA'
            else:
                self.market_state['sentiment'] = 'NEUTRAL'
            
            # Determinar nivel de riesgo
            risk_factors = 0
            if avg_volatility > 4:
                risk_factors += 1
            if abs(avg_sentiment) > 2:
                risk_factors += 1
            if abs(avg_trend) > 0.2:
                risk_factors += 1
            
            if risk_factors >= 2:
                self.market_state['risk_level'] = 'ALTO'
            elif risk_factors == 1:
                self.market_state['risk_level'] = 'MEDIO'
            else:
                self.market_state['risk_level'] = 'BAJO'
            
        except Exception as e:
            self.logger.error(f"❌ Error actualizando estado del mercado: {e}")

    def display_analysis(self, analyses: List[Dict]):
        """Mostrar análisis en consola"""
        try:
            # Limpiar pantalla
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"{Fore.CYAN}{'='*80}")
            print(f"{Fore.YELLOW}🔍 ANÁLISIS DE MERCADO EN TIEMPO REAL - SICAR")
            print(f"{Fore.CYAN}{'='*80}")
            print(f"{Fore.WHITE}🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Estado general del mercado
            trend_color = Fore.GREEN if self.market_state['trend'] == 'ALCISTA' else Fore.RED if self.market_state['trend'] == 'BAJISTA' else Fore.YELLOW
            vol_color = Fore.RED if self.market_state['volatility'] == 'ALTA' else Fore.GREEN if self.market_state['volatility'] == 'BAJA' else Fore.YELLOW
            sent_color = Fore.GREEN if self.market_state['sentiment'] == 'OPTIMISTA' else Fore.RED if self.market_state['sentiment'] == 'PESIMISTA' else Fore.YELLOW
            risk_color = Fore.RED if self.market_state['risk_level'] == 'ALTO' else Fore.YELLOW if self.market_state['risk_level'] == 'MEDIO' else Fore.GREEN
            
            print(f"{Fore.CYAN}📊 ESTADO GENERAL DEL MERCADO:")
            print(f"├─ Tendencia: {trend_color}{self.market_state['trend']}")
            print(f"{Fore.CYAN}├─ Volatilidad: {vol_color}{self.market_state['volatility']}")
            print(f"{Fore.CYAN}├─ Sentimiento: {sent_color}{self.market_state['sentiment']}")
            print(f"{Fore.CYAN}└─ Riesgo: {risk_color}{self.market_state['risk_level']}")
            print()
            
            # Análisis por símbolo
            print(f"{Fore.CYAN}💰 ANÁLISIS POR SÍMBOLO:")
            print(f"{Fore.WHITE}{'Symbol':<10} {'Precio':<12} {'24h %':<8} {'RSI':<6} {'Rec.':<12} {'Conf.':<6}")
            print(f"{Fore.CYAN}{'-'*60}")
            
            for analysis in analyses:
                symbol = analysis['symbol']
                precio = f"${analysis['precio_actual']:.4f}"
                cambio = f"{analysis['cambio_24h']:+.2f}%"
                rsi = f"{analysis['rsi']:.1f}"
                rec = analysis['recomendacion']
                conf = f"{analysis['confianza']:.2f}"
                
                # Colores según recomendación
                if 'COMPRA' in rec:
                    rec_color = Fore.GREEN
                elif 'VENTA' in rec:
                    rec_color = Fore.RED
                else:
                    rec_color = Fore.YELLOW
                
                # Color según cambio 24h
                cambio_color = Fore.GREEN if analysis['cambio_24h'] > 0 else Fore.RED
                
                print(f"{Fore.WHITE}{symbol:<10} {precio:<12} {cambio_color}{cambio:<8} {Fore.WHITE}{rsi:<6} {rec_color}{rec:<12} {Fore.WHITE}{conf:<6}")
            
            print()
            print(f"{Fore.CYAN}{'─'*80}")
            print(f"{Fore.YELLOW}Próxima actualización en 60 segundos... | Ctrl+C para detener")
            print(f"{Fore.CYAN}{'─'*80}")
            print(f"{Style.RESET_ALL}")
            
        except Exception as e:
            self.logger.error(f"❌ Error mostrando análisis: {e}")

    async def run_analysis_cycle(self):
        """Ejecutar un ciclo completo de análisis"""
        try:
            analyses = []
            
            for symbol in self.symbols:
                self.logger.info(f"📈 Analizando {symbol}...")
                
                # Obtener datos de mercado
                market_data = await self.get_market_data(symbol)
                if market_data:
                    # Analizar símbolo
                    analysis = self.analyze_symbol(market_data)
                    analyses.append(analysis)
                    
                    # Guardar análisis
                    self.save_analysis(analysis)
                
                # Pequeña pausa entre símbolos
                await asyncio.sleep(1)
            
            # Actualizar estado general del mercado
            self.update_market_state(analyses)
            
            # Mostrar análisis
            self.display_analysis(analyses)
            
            return analyses
            
        except Exception as e:
            self.logger.error(f"❌ Error en ciclo de análisis: {e}")
            return []

    async def run(self):
        """Ejecutar sistema de análisis en tiempo real"""
        self.logger.info("🚀 Iniciando análisis de mercado en tiempo real...")
        
        try:
            while True:
                # Ejecutar ciclo de análisis
                await self.run_analysis_cycle()
                
                # Esperar 60 segundos antes del próximo análisis
                await asyncio.sleep(60)
                
        except KeyboardInterrupt:
            self.logger.info("🛑 Análisis de mercado detenido por el usuario")
        except Exception as e:
            self.logger.error(f"❌ Error en análisis de mercado: {e}")

if __name__ == "__main__":
    # Crear y ejecutar sistema de análisis
    analyzer = AnalisisMercadoTiempoReal()
    asyncio.run(analyzer.run())