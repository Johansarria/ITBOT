#!/usr/bin/env python3
"""
Sistema de Trading Mejorado con Filtros Avanzados
Implementa todas las mejoras identificadas en el análisis de fallas
"""

import requests
import sqlite3
import json
import logging
import time
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import talib
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('enhanced_trading_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradingSignal:
    symbol: str
    signal_type: str  # BUY/SELL
    confidence: float
    price: float
    timestamp: datetime
    reason: str
    risk_level: str
    volume_score: float
    technical_scores: Dict
    market_context: Dict

@dataclass
class MarketContext:
    btc_trend: str  # BULLISH/BEARISH/NEUTRAL
    eth_trend: str
    market_correlation: float
    overall_sentiment: str
    volatility_regime: str

class EnhancedTradingSystem:
    def __init__(self):
        """Inicializar sistema de trading mejorado."""
        
        # Símbolos principales para análisis de mercado
        self.market_leaders = ['BTCUSDT', 'ETHUSDT']
        
        # Símbolos para trading
        self.trading_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'XRPUSDT', 'DOGEUSDT', 'AVAXUSDT', 'DOTUSDT', 'MATICUSDT'
        ]
        
        # Configuración mejorada de trading
        self.trading_config = {
            'min_confidence': 75.0,  # Aumentado de 60% a 75%
            'max_risk_level': 'MEDIUM',
            'position_size_pct': 8.0,  # Reducido de 10% a 8%
            'base_stop_loss_pct': 3.0,  # Aumentado de 2% a 3%
            'base_take_profit_pct': 6.0,  # Aumentado de 4% a 6%
            'max_positions': 2,  # Reducido de 3 a 2
            'volume_multiplier_min': 2.0,  # Volumen mínimo 2x promedio
            'correlation_threshold': 0.7,  # Correlación mínima con BTC/ETH
            'timeframes': ['1h', '4h', '1d'],  # Múltiples timeframes
            'min_timeframe_confirmations': 2  # Mínimo 2 timeframes confirmando
        }
        
        # Estado del sistema
        self.active_positions = {}
        self.market_context = None
        self.volatility_cache = {}
        self.volume_averages = {}
        
        # Base de datos
        self.init_enhanced_database()
        
        logger.info("[INIT] Sistema de Trading Mejorado inicializado")
        logger.info(f"[CONFIG] Confianza mínima: {self.trading_config['min_confidence']}%")
        logger.info(f"[CONFIG] Stop loss base: {self.trading_config['base_stop_loss_pct']}%")
        logger.info(f"[CONFIG] Máximo posiciones: {self.trading_config['max_positions']}")
    
    def init_enhanced_database(self):
        """Inicializar base de datos mejorada."""
        try:
            conn = sqlite3.connect('enhanced_trading.db')
            cursor = conn.cursor()
            
            # Tabla de señales con análisis técnico
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    price REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    reason TEXT,
                    risk_level TEXT,
                    volume_score REAL,
                    rsi_1h REAL,
                    rsi_4h REAL,
                    rsi_1d REAL,
                    macd_1h REAL,
                    macd_4h REAL,
                    macd_1d REAL,
                    bb_position REAL,
                    market_correlation REAL,
                    btc_trend TEXT,
                    eth_trend TEXT,
                    timeframe_confirmations INTEGER,
                    executed BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Tabla de contexto de mercado
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    btc_trend TEXT,
                    eth_trend TEXT,
                    market_correlation REAL,
                    overall_sentiment TEXT,
                    volatility_regime TEXT,
                    btc_price REAL,
                    eth_price REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("[DB] Base de datos mejorada inicializada")
            
        except Exception as e:
            logger.error(f"[ERROR] Error inicializando base de datos: {e}")
    
    def get_klines_data(self, symbol: str, interval: str, limit: int = 100) -> Optional[pd.DataFrame]:
        """Obtener datos de velas para análisis técnico."""
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                # Convertir a tipos numéricos
                numeric_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in numeric_columns:
                    df[col] = pd.to_numeric(df[col])
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
            
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Error obteniendo datos de {symbol} {interval}: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Calcular indicadores técnicos."""
        try:
            close = df['close'].values
            high = df['high'].values
            low = df['low'].values
            volume = df['volume'].values
            
            # RSI
            rsi = talib.RSI(close, timeperiod=14)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(close)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(close)
            
            # Posición en Bollinger Bands (0-1, donde 0.5 es el centro)
            current_price = close[-1]
            bb_position = (current_price - bb_lower[-1]) / (bb_upper[-1] - bb_lower[-1])
            
            # Volumen promedio
            volume_avg = np.mean(volume[-20:])  # Promedio 20 períodos
            current_volume = volume[-1]
            volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1
            
            return {
                'rsi': rsi[-1] if not np.isnan(rsi[-1]) else 50,
                'macd': macd[-1] if not np.isnan(macd[-1]) else 0,
                'macd_signal': macd_signal[-1] if not np.isnan(macd_signal[-1]) else 0,
                'macd_histogram': macd_hist[-1] if not np.isnan(macd_hist[-1]) else 0,
                'bb_position': bb_position if not np.isnan(bb_position) else 0.5,
                'bb_upper': bb_upper[-1],
                'bb_middle': bb_middle[-1],
                'bb_lower': bb_lower[-1],
                'volume_ratio': volume_ratio,
                'volume_avg': volume_avg
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error calculando indicadores técnicos: {e}")
            return {}
    
    def analyze_market_context(self) -> MarketContext:
        """Analizar contexto general del mercado."""
        try:
            btc_data = self.get_klines_data('BTCUSDT', '1h', 50)
            eth_data = self.get_klines_data('ETHUSDT', '1h', 50)
            
            if btc_data is None or eth_data is None:
                logger.warning("[MARKET] No se pudo obtener datos de BTC/ETH")
                return MarketContext('NEUTRAL', 'NEUTRAL', 0.5, 'NEUTRAL', 'NORMAL')
            
            # Análisis de tendencia BTC
            btc_indicators = self.calculate_technical_indicators(btc_data)
            btc_trend = self.determine_trend(btc_indicators)
            
            # Análisis de tendencia ETH
            eth_indicators = self.calculate_technical_indicators(eth_data)
            eth_trend = self.determine_trend(eth_indicators)
            
            # Correlación (simplificada)
            btc_returns = btc_data['close'].pct_change().dropna()
            eth_returns = eth_data['close'].pct_change().dropna()
            correlation = btc_returns.corr(eth_returns) if len(btc_returns) > 10 else 0.7
            
            # Sentimiento general
            if btc_trend == 'BULLISH' and eth_trend == 'BULLISH':
                sentiment = 'BULLISH'
            elif btc_trend == 'BEARISH' and eth_trend == 'BEARISH':
                sentiment = 'BEARISH'
            else:
                sentiment = 'NEUTRAL'
            
            # Régimen de volatilidad
            btc_volatility = btc_returns.std() * 100
            volatility_regime = 'HIGH' if btc_volatility > 3 else 'NORMAL' if btc_volatility > 1.5 else 'LOW'
            
            context = MarketContext(
                btc_trend=btc_trend,
                eth_trend=eth_trend,
                market_correlation=correlation,
                overall_sentiment=sentiment,
                volatility_regime=volatility_regime
            )
            
            # Guardar en base de datos
            self.save_market_context(context, btc_data['close'].iloc[-1], eth_data['close'].iloc[-1])
            
            logger.info(f"[MARKET] BTC: {btc_trend}, ETH: {eth_trend}, Sentimiento: {sentiment}")
            logger.info(f"[MARKET] Correlación: {correlation:.3f}, Volatilidad: {volatility_regime}")
            
            return context
            
        except Exception as e:
            logger.error(f"[ERROR] Error analizando contexto de mercado: {e}")
            return MarketContext('NEUTRAL', 'NEUTRAL', 0.5, 'NEUTRAL', 'NORMAL')
    
    def determine_trend(self, indicators: Dict) -> str:
        """Determinar tendencia basada en indicadores."""
        try:
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            bb_position = indicators.get('bb_position', 0.5)
            
            bullish_signals = 0
            bearish_signals = 0
            
            # RSI
            if rsi > 60:
                bullish_signals += 1
            elif rsi < 40:
                bearish_signals += 1
            
            # MACD
            if macd > macd_signal and macd > 0:
                bullish_signals += 1
            elif macd < macd_signal and macd < 0:
                bearish_signals += 1
            
            # Bollinger Bands
            if bb_position > 0.7:
                bullish_signals += 1
            elif bb_position < 0.3:
                bearish_signals += 1
            
            if bullish_signals >= 2:
                return 'BULLISH'
            elif bearish_signals >= 2:
                return 'BEARISH'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            logger.error(f"[ERROR] Error determinando tendencia: {e}")
            return 'NEUTRAL'
    
    def calculate_dynamic_stop_loss(self, symbol: str, price: float, signal_type: str) -> float:
        """Calcular stop loss dinámico basado en volatilidad."""
        try:
            # Obtener datos históricos para calcular volatilidad
            df = self.get_klines_data(symbol, '1h', 50)
            if df is None:
                # Usar stop loss base si no hay datos
                base_stop = self.trading_config['base_stop_loss_pct'] / 100
                return price * (1 + base_stop) if signal_type == 'SELL' else price * (1 - base_stop)
            
            # Calcular volatilidad histórica
            returns = df['close'].pct_change().dropna()
            volatility = returns.std() * 100  # Volatilidad en %
            
            # Ajustar stop loss según volatilidad
            if volatility > 4:  # Alta volatilidad
                stop_pct = 5.0
            elif volatility > 2:  # Volatilidad media
                stop_pct = 4.0
            else:  # Baja volatilidad
                stop_pct = 3.0
            
            stop_multiplier = stop_pct / 100
            
            if signal_type == 'SELL':
                return price * (1 + stop_multiplier)
            else:
                return price * (1 - stop_multiplier)
                
        except Exception as e:
            logger.error(f"[ERROR] Error calculando stop loss dinámico: {e}")
            base_stop = self.trading_config['base_stop_loss_pct'] / 100
            return price * (1 + base_stop) if signal_type == 'SELL' else price * (1 - base_stop)
    
    def analyze_multi_timeframe(self, symbol: str) -> Dict:
        """Analizar múltiples timeframes para confirmación."""
        try:
            timeframes = self.trading_config['timeframes']
            analysis = {}
            confirmations = 0
            
            for tf in timeframes:
                df = self.get_klines_data(symbol, tf, 50)
                if df is not None:
                    indicators = self.calculate_technical_indicators(df)
                    trend = self.determine_trend(indicators)
                    
                    analysis[tf] = {
                        'trend': trend,
                        'rsi': indicators.get('rsi', 50),
                        'macd': indicators.get('macd', 0),
                        'volume_ratio': indicators.get('volume_ratio', 1)
                    }
                    
                    # Contar confirmaciones alcistas/bajistas
                    if trend in ['BULLISH', 'BEARISH']:
                        confirmations += 1
                else:
                    analysis[tf] = {
                        'trend': 'NEUTRAL',
                        'rsi': 50,
                        'macd': 0,
                        'volume_ratio': 1
                    }
            
            analysis['confirmations'] = confirmations
            return analysis
            
        except Exception as e:
            logger.error(f"[ERROR] Error en análisis multi-timeframe: {e}")
            return {'confirmations': 0}
    
    def should_execute_trade(self, signal: TradingSignal, market_context: MarketContext) -> Tuple[bool, str]:
        """Determinar si se debe ejecutar la operación con filtros mejorados."""
        
        # 1. Verificar confianza mínima
        if signal.confidence < self.trading_config['min_confidence']:
            return False, f"Confianza insuficiente ({signal.confidence:.1f}% < {self.trading_config['min_confidence']}%)"
        
        # 2. Verificar máximo de posiciones
        if len(self.active_positions) >= self.trading_config['max_positions']:
            return False, f"Máximo de posiciones alcanzado ({len(self.active_positions)}/{self.trading_config['max_positions']})"
        
        # 3. Verificar si ya hay posición en este símbolo
        if signal.symbol in self.active_positions:
            return False, "Ya hay posición activa en este símbolo"
        
        # 4. Filtro de tendencia de mercado (CRÍTICO)
        if signal.symbol not in self.market_leaders:  # Solo para altcoins
            if signal.signal_type == 'BUY' and market_context.overall_sentiment == 'BEARISH':
                return False, "Mercado general bajista - no comprar altcoins"
            elif signal.signal_type == 'SELL' and market_context.overall_sentiment == 'BULLISH':
                return False, "Mercado general alcista - no vender altcoins"
        
        # 5. Verificar correlación con mercado
        if signal.market_context.get('market_correlation', 0) < self.trading_config['correlation_threshold']:
            return False, f"Baja correlación con mercado ({signal.market_context.get('market_correlation', 0):.2f})"
        
        # 6. Verificar volumen
        if signal.volume_score < self.trading_config['volume_multiplier_min']:
            return False, f"Volumen insuficiente ({signal.volume_score:.1f}x < {self.trading_config['volume_multiplier_min']}x)"
        
        # 7. Verificar confirmaciones de timeframes
        timeframe_confirmations = signal.technical_scores.get('confirmations', 0)
        if timeframe_confirmations < self.trading_config['min_timeframe_confirmations']:
            return False, f"Insuficientes confirmaciones de timeframes ({timeframe_confirmations}/{self.trading_config['min_timeframe_confirmations']})"
        
        return True, "Todos los filtros pasados"
    
    def save_market_context(self, context: MarketContext, btc_price: float, eth_price: float):
        """Guardar contexto de mercado en base de datos."""
        try:
            conn = sqlite3.connect('enhanced_trading.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO market_context 
                (timestamp, btc_trend, eth_trend, market_correlation, overall_sentiment, 
                 volatility_regime, btc_price, eth_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                context.btc_trend,
                context.eth_trend,
                context.market_correlation,
                context.overall_sentiment,
                context.volatility_regime,
                btc_price,
                eth_price
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"[ERROR] Error guardando contexto de mercado: {e}")
    
    def run_enhanced_analysis(self):
        """Ejecutar análisis mejorado del mercado."""
        try:
            logger.info("[START] Iniciando análisis mejorado del mercado...")
            
            # 1. Analizar contexto general del mercado
            self.market_context = self.analyze_market_context()
            
            # 2. Analizar cada símbolo
            signals_detected = 0
            
            for symbol in self.trading_symbols:
                logger.info(f"[ANALYSIS] Analizando {symbol}...")
                
                # Análisis multi-timeframe
                mtf_analysis = self.analyze_multi_timeframe(symbol)
                
                # Solo proceder si hay suficientes confirmaciones
                if mtf_analysis.get('confirmations', 0) >= self.trading_config['min_timeframe_confirmations']:
                    logger.info(f"[SIGNAL] {symbol} tiene {mtf_analysis['confirmations']} confirmaciones de timeframes")
                    signals_detected += 1
                else:
                    logger.info(f"[SKIP] {symbol} - Insuficientes confirmaciones ({mtf_analysis.get('confirmations', 0)}/{self.trading_config['min_timeframe_confirmations']})")
            
            logger.info(f"[SUMMARY] Análisis completado - {signals_detected} señales potenciales detectadas")
            logger.info(f"[MARKET] Contexto: {self.market_context.overall_sentiment}")
            logger.info(f"[POSITIONS] Posiciones activas: {len(self.active_positions)}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error en análisis mejorado: {e}")

def main():
    """Función principal."""
    system = EnhancedTradingSystem()
    
    try:
        while True:
            system.run_enhanced_analysis()
            logger.info("[WAIT] Esperando 5 minutos para el próximo análisis...")
            time.sleep(300)  # 5 minutos
            
    except KeyboardInterrupt:
        logger.info("[STOP] Sistema detenido por el usuario")
    except Exception as e:
        logger.error(f"[ERROR] Error crítico: {e}")

if __name__ == "__main__":
    main()