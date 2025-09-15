import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class TechnicalIndicators:
    """Estructura para almacenar indicadores técnicos"""
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_width: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    volume_sma: Optional[float] = None
    
@dataclass
class MarketSignal:
    """Señal de mercado generada por el análisis"""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: float   # 0-100, fuerza de la señal
    confidence: float # 0-100, confianza en la señal
    reasons: List[str]
    timestamp: datetime
    indicators: TechnicalIndicators
    
class TechnicalAnalyzer:
    """Analizador de indicadores técnicos en tiempo real"""
    
    def __init__(self, max_periods: int = 200):
        self.max_periods = max_periods
        self.price_data: Dict[str, deque] = {}
        self.volume_data: Dict[str, deque] = {}
        self.indicators_cache: Dict[str, TechnicalIndicators] = {}
        
    def add_price_data(self, symbol: str, price: float, volume: float = 0, timestamp: datetime = None):
        """Añade datos de precio y volumen para un símbolo"""
        if timestamp is None:
            timestamp = datetime.now()
            
        if symbol not in self.price_data:
            self.price_data[symbol] = deque(maxlen=self.max_periods)
            self.volume_data[symbol] = deque(maxlen=self.max_periods)
            
        self.price_data[symbol].append({
            'price': price,
            'timestamp': timestamp
        })
        self.volume_data[symbol].append({
            'volume': volume,
            'timestamp': timestamp
        })
        
        # Actualizar indicadores
        self._update_indicators(symbol)
        
    def _update_indicators(self, symbol: str):
        """Actualiza todos los indicadores técnicos para un símbolo"""
        if symbol not in self.price_data or len(self.price_data[symbol]) < 20:
            return
            
        prices = [data['price'] for data in self.price_data[symbol]]
        volumes = [data['volume'] for data in self.volume_data[symbol]]
        
        indicators = TechnicalIndicators()
        
        # RSI
        indicators.rsi = self._calculate_rsi(prices)
        
        # MACD
        macd_data = self._calculate_macd(prices)
        if macd_data:
            indicators.macd = macd_data['macd']
            indicators.macd_signal = macd_data['signal']
            indicators.macd_histogram = macd_data['histogram']
            
        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(prices)
        if bb_data:
            indicators.bb_upper = bb_data['upper']
            indicators.bb_middle = bb_data['middle']
            indicators.bb_lower = bb_data['lower']
            indicators.bb_width = bb_data['width']
            
        # Medias móviles
        indicators.sma_20 = self._calculate_sma(prices, 20)
        indicators.sma_50 = self._calculate_sma(prices, 50)
        indicators.ema_12 = self._calculate_ema(prices, 12)
        indicators.ema_26 = self._calculate_ema(prices, 26)
        
        # Volumen promedio
        if volumes:
            indicators.volume_sma = self._calculate_sma(volumes, 20)
            
        self.indicators_cache[symbol] = indicators
        
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> Optional[float]:
        """Calcula el RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return None
            
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
        
    def _calculate_macd(self, prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict]:
        """Calcula MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow + signal:
            return None
            
        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)
        
        if ema_fast is None or ema_slow is None:
            return None
            
        macd_line = ema_fast - ema_slow
        
        # Calcular señal MACD (necesitamos historial de MACD)
        # Simplificado para tiempo real
        macd_signal = macd_line * 0.9  # Aproximación
        histogram = macd_line - macd_signal
        
        return {
            'macd': macd_line,
            'signal': macd_signal,
            'histogram': histogram
        }
        
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2) -> Optional[Dict]:
        """Calcula Bollinger Bands"""
        if len(prices) < period:
            return None
            
        recent_prices = prices[-period:]
        sma = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        width = ((upper - lower) / sma) * 100
        
        return {
            'upper': upper,
            'middle': sma,
            'lower': lower,
            'width': width
        }
        
    def _calculate_sma(self, values: List[float], period: int) -> Optional[float]:
        """Calcula Simple Moving Average"""
        if len(values) < period:
            return None
        return np.mean(values[-period:])
        
    def _calculate_ema(self, prices: List[float], period: int) -> Optional[float]:
        """Calcula Exponential Moving Average"""
        if len(prices) < period:
            return None
            
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            
        return ema
        
    def get_indicators(self, symbol: str) -> Optional[TechnicalIndicators]:
        """Obtiene los indicadores actuales para un símbolo"""
        return self.indicators_cache.get(symbol)
        
class MarketConditionAnalyzer:
    """Analizador de condiciones de mercado y generador de señales"""
    
    def __init__(self, technical_analyzer: TechnicalAnalyzer):
        self.technical_analyzer = technical_analyzer
        self.signal_history: Dict[str, List[MarketSignal]] = {}
        
    def analyze_market_conditions(self, symbol: str) -> Optional[MarketSignal]:
        """Analiza condiciones de mercado y genera señales"""
        indicators = self.technical_analyzer.get_indicators(symbol)
        if not indicators:
            return None
            
        signal_type = "HOLD"
        strength = 0
        confidence = 0
        reasons = []
        
        # Análisis RSI
        rsi_signal, rsi_strength, rsi_reasons = self._analyze_rsi(indicators.rsi)
        
        # Análisis MACD
        macd_signal, macd_strength, macd_reasons = self._analyze_macd(
            indicators.macd, indicators.macd_signal, indicators.macd_histogram
        )
        
        # Análisis Bollinger Bands
        bb_signal, bb_strength, bb_reasons = self._analyze_bollinger_bands(
            symbol, indicators.bb_upper, indicators.bb_middle, indicators.bb_lower
        )
        
        # Análisis de tendencia (medias móviles)
        trend_signal, trend_strength, trend_reasons = self._analyze_trend(
            indicators.sma_20, indicators.sma_50, indicators.ema_12, indicators.ema_26
        )
        
        # Combinar señales
        signals = [rsi_signal, macd_signal, bb_signal, trend_signal]
        strengths = [rsi_strength, macd_strength, bb_strength, trend_strength]
        all_reasons = rsi_reasons + macd_reasons + bb_reasons + trend_reasons
        
        # Determinar señal final
        buy_signals = signals.count('BUY')
        sell_signals = signals.count('SELL')
        
        if buy_signals >= 3:
            signal_type = "BUY"
            strength = np.mean([s for s, sig in zip(strengths, signals) if sig == 'BUY'])
            confidence = (buy_signals / len(signals)) * 100
        elif sell_signals >= 3:
            signal_type = "SELL"
            strength = np.mean([s for s, sig in zip(strengths, signals) if sig == 'SELL'])
            confidence = (sell_signals / len(signals)) * 100
        elif buy_signals >= 2 and sell_signals == 0:
            signal_type = "BUY"
            strength = np.mean([s for s, sig in zip(strengths, signals) if sig == 'BUY']) * 0.7
            confidence = 60
        elif sell_signals >= 2 and buy_signals == 0:
            signal_type = "SELL"
            strength = np.mean([s for s, sig in zip(strengths, signals) if sig == 'SELL']) * 0.7
            confidence = 60
        else:
            signal_type = "HOLD"
            strength = 30
            confidence = 40
            all_reasons.append("Señales mixtas o insuficientes")
            
        signal = MarketSignal(
            symbol=symbol,
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            reasons=all_reasons,
            timestamp=datetime.now(),
            indicators=indicators
        )
        
        # Guardar en historial
        if symbol not in self.signal_history:
            self.signal_history[symbol] = []
        self.signal_history[symbol].append(signal)
        
        # Mantener solo las últimas 100 señales
        if len(self.signal_history[symbol]) > 100:
            self.signal_history[symbol] = self.signal_history[symbol][-100:]
            
        return signal
        
    def _analyze_rsi(self, rsi: Optional[float]) -> Tuple[str, float, List[str]]:
        """Analiza RSI y genera señal"""
        if rsi is None:
            return "HOLD", 0, ["RSI no disponible"]
            
        reasons = []
        
        if rsi <= 30:
            reasons.append(f"RSI sobreventa ({rsi:.1f})")
            return "BUY", min(85, (30 - rsi) * 3), reasons
        elif rsi >= 70:
            reasons.append(f"RSI sobrecompra ({rsi:.1f})")
            return "SELL", min(85, (rsi - 70) * 3), reasons
        elif rsi <= 40:
            reasons.append(f"RSI bajo ({rsi:.1f})")
            return "BUY", 40, reasons
        elif rsi >= 60:
            reasons.append(f"RSI alto ({rsi:.1f})")
            return "SELL", 40, reasons
        else:
            reasons.append(f"RSI neutral ({rsi:.1f})")
            return "HOLD", 20, reasons
            
    def _analyze_macd(self, macd: Optional[float], signal: Optional[float], histogram: Optional[float]) -> Tuple[str, float, List[str]]:
        """Analiza MACD y genera señal"""
        if macd is None or signal is None:
            return "HOLD", 0, ["MACD no disponible"]
            
        reasons = []
        
        if macd > signal and histogram and histogram > 0:
            reasons.append("MACD cruce alcista")
            return "BUY", 70, reasons
        elif macd < signal and histogram and histogram < 0:
            reasons.append("MACD cruce bajista")
            return "SELL", 70, reasons
        elif macd > 0 and signal > 0:
            reasons.append("MACD en territorio positivo")
            return "BUY", 50, reasons
        elif macd < 0 and signal < 0:
            reasons.append("MACD en territorio negativo")
            return "SELL", 50, reasons
        else:
            reasons.append("MACD neutral")
            return "HOLD", 30, reasons
            
    def _analyze_bollinger_bands(self, symbol: str, upper: Optional[float], middle: Optional[float], lower: Optional[float]) -> Tuple[str, float, List[str]]:
        """Analiza Bollinger Bands y genera señal"""
        if not all([upper, middle, lower]):
            return "HOLD", 0, ["Bollinger Bands no disponibles"]
            
        # Obtener precio actual
        current_price = None
        if symbol in self.technical_analyzer.price_data:
            price_data = self.technical_analyzer.price_data[symbol]
            if price_data:
                current_price = price_data[-1]['price']
                
        if current_price is None:
            return "HOLD", 0, ["Precio actual no disponible"]
            
        reasons = []
        
        # Calcular posición relativa en las bandas
        bb_position = (current_price - lower) / (upper - lower)
        
        if current_price <= lower:
            reasons.append(f"Precio en banda inferior ({current_price:.2f} <= {lower:.2f})")
            return "BUY", 80, reasons
        elif current_price >= upper:
            reasons.append(f"Precio en banda superior ({current_price:.2f} >= {upper:.2f})")
            return "SELL", 80, reasons
        elif bb_position <= 0.2:
            reasons.append(f"Precio cerca de banda inferior (posición: {bb_position:.2f})")
            return "BUY", 60, reasons
        elif bb_position >= 0.8:
            reasons.append(f"Precio cerca de banda superior (posición: {bb_position:.2f})")
            return "SELL", 60, reasons
        else:
            reasons.append(f"Precio en rango medio de BB (posición: {bb_position:.2f})")
            return "HOLD", 30, reasons
            
    def _analyze_trend(self, sma_20: Optional[float], sma_50: Optional[float], 
                      ema_12: Optional[float], ema_26: Optional[float]) -> Tuple[str, float, List[str]]:
        """Analiza tendencia usando medias móviles"""
        reasons = []
        
        if not any([sma_20, sma_50, ema_12, ema_26]):
            return "HOLD", 0, ["Medias móviles no disponibles"]
            
        signals = []
        
        # SMA 20 vs SMA 50
        if sma_20 and sma_50:
            if sma_20 > sma_50:
                signals.append('BUY')
                reasons.append(f"SMA20 > SMA50 (tendencia alcista)")
            else:
                signals.append('SELL')
                reasons.append(f"SMA20 < SMA50 (tendencia bajista)")
                
        # EMA 12 vs EMA 26
        if ema_12 and ema_26:
            if ema_12 > ema_26:
                signals.append('BUY')
                reasons.append(f"EMA12 > EMA26 (momentum alcista)")
            else:
                signals.append('SELL')
                reasons.append(f"EMA12 < EMA26 (momentum bajista)")
                
        if not signals:
            return "HOLD", 20, reasons
            
        buy_count = signals.count('BUY')
        sell_count = signals.count('SELL')
        
        if buy_count > sell_count:
            return "BUY", 60, reasons
        elif sell_count > buy_count:
            return "SELL", 60, reasons
        else:
            return "HOLD", 30, reasons
            
    def get_signal_history(self, symbol: str, limit: int = 10) -> List[MarketSignal]:
        """Obtiene historial de señales para un símbolo"""
        if symbol not in self.signal_history:
            return []
        return self.signal_history[symbol][-limit:]
        
    def get_market_summary(self, symbols: List[str]) -> Dict:
        """Obtiene resumen de condiciones de mercado para múltiples símbolos"""
        summary = {
            'timestamp': datetime.now(),
            'symbols_analyzed': len(symbols),
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0,
            'signals': {}
        }
        
        for symbol in symbols:
            signal = self.analyze_market_conditions(symbol)
            if signal:
                summary['signals'][symbol] = {
                    'signal': signal.signal_type,
                    'strength': signal.strength,
                    'confidence': signal.confidence,
                    'reasons': signal.reasons[:3]  # Solo las 3 principales
                }
                
                if signal.signal_type == 'BUY':
                    summary['buy_signals'] += 1
                elif signal.signal_type == 'SELL':
                    summary['sell_signals'] += 1
                else:
                    summary['hold_signals'] += 1
                    
        return summary

if __name__ == "__main__":
    # Ejemplo de uso
    analyzer = TechnicalAnalyzer()
    market_analyzer = MarketConditionAnalyzer(analyzer)
    
    # Simular datos de precio
    symbol = "BNBUSDT"
    prices = [300, 302, 305, 303, 308, 310, 307, 312, 315, 318, 316, 320, 322, 319, 325]
    
    for i, price in enumerate(prices):
        analyzer.add_price_data(symbol, price, volume=1000 + i*10)
        
    # Analizar condiciones
    signal = market_analyzer.analyze_market_conditions(symbol)
    if signal:
        print(f"\nSeñal para {symbol}:")
        print(f"Tipo: {signal.signal_type}")
        print(f"Fuerza: {signal.strength:.1f}")
        print(f"Confianza: {signal.confidence:.1f}%")
        print(f"Razones: {', '.join(signal.reasons)}")
        
        indicators = signal.indicators
        print(f"\nIndicadores:")
        print(f"RSI: {indicators.rsi:.1f}" if indicators.rsi else "RSI: N/A")
        print(f"MACD: {indicators.macd:.3f}" if indicators.macd else "MACD: N/A")
        print(f"BB Superior: {indicators.bb_upper:.2f}" if indicators.bb_upper else "BB: N/A")