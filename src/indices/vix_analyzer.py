"""
VIX Analyzer Module for SICAR System
====================================

Módulo especializado para análisis del VIX (Volatility Index) y métricas de volatilidad
del mercado. Proporciona análisis de miedo/codicia, predicción de volatilidad y 
señales de trading basadas en volatilidad.

Author: SICAR System
Date: 2024-10-27
Version: 1.0
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

class VIXLevel(Enum):
    """Niveles de volatilidad del VIX"""
    EXTREMELY_LOW = "extremely_low"      # VIX < 12
    LOW = "low"                         # VIX 12-16
    NORMAL = "normal"                   # VIX 16-20
    ELEVATED = "elevated"               # VIX 20-30
    HIGH = "high"                       # VIX 30-40
    EXTREMELY_HIGH = "extremely_high"   # VIX > 40

class MarketSentiment(Enum):
    """Sentimiento del mercado basado en VIX"""
    EXTREME_GREED = "extreme_greed"
    GREED = "greed"
    NEUTRAL = "neutral"
    FEAR = "fear"
    EXTREME_FEAR = "extreme_fear"

@dataclass
class VIXSignal:
    """Señal de trading basada en VIX"""
    timestamp: datetime
    vix_value: float
    vix_level: VIXLevel
    sentiment: MarketSentiment
    signal_type: str  # 'buy', 'sell', 'hold'
    signal_strength: float  # 0-1
    confidence: float  # 0-1
    reasoning: str

@dataclass
class VIXAnalysis:
    """Resultado completo del análisis VIX"""
    current_vix: float
    vix_level: VIXLevel
    sentiment: MarketSentiment
    percentile_rank: float
    mean_reversion_signal: str
    volatility_trend: str
    fear_greed_index: float
    trading_signal: VIXSignal
    historical_context: Dict
    recommendations: List[str]

class VIXAnalyzer:
    """
    Analizador completo del VIX para el sistema SICAR
    
    Funcionalidades:
    - Análisis en tiempo real del VIX
    - Cálculo de niveles de miedo/codicia
    - Señales de trading basadas en volatilidad
    - Análisis de reversión a la media
    - Contexto histórico y percentiles
    """
    
    def __init__(self, lookback_days: int = 252):
        """
        Inicializar el analizador VIX
        
        Args:
            lookback_days: Días históricos para análisis (default: 252 = 1 año)
        """
        self.lookback_days = lookback_days
        self.vix_data = None
        self.spy_data = None
        self.last_update = None
        
        # Umbrales de VIX
        self.vix_thresholds = {
            VIXLevel.EXTREMELY_LOW: (0, 12),
            VIXLevel.LOW: (12, 16),
            VIXLevel.NORMAL: (16, 20),
            VIXLevel.ELEVATED: (20, 30),
            VIXLevel.HIGH: (30, 40),
            VIXLevel.EXTREMELY_HIGH: (40, 100)
        }
        
        # Configuración de señales
        self.signal_config = {
            'mean_reversion_threshold': 1.5,  # Desviaciones estándar
            'trend_window': 10,  # Días para calcular tendencia
            'signal_cooldown': 5,  # Días entre señales
            'min_confidence': 0.6  # Confianza mínima para señales
        }
    
    def update_data(self, force_update: bool = False) -> bool:
        """
        Actualizar datos del VIX y SPY
        
        Args:
            force_update: Forzar actualización aunque los datos sean recientes
            
        Returns:
            bool: True si la actualización fue exitosa
        """
        try:
            # Verificar si necesitamos actualizar
            if not force_update and self.last_update:
                time_diff = datetime.now() - self.last_update
                if time_diff.total_seconds() < 3600:  # 1 hora
                    return True
            
            # Calcular fechas
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.lookback_days + 30)
            
            # Descargar datos VIX
            vix_ticker = yf.Ticker("^VIX")
            self.vix_data = vix_ticker.history(
                start=start_date,
                end=end_date,
                interval="1d"
            )
            
            # Descargar datos SPY para correlación
            spy_ticker = yf.Ticker("SPY")
            self.spy_data = spy_ticker.history(
                start=start_date,
                end=end_date,
                interval="1d"
            )
            
            if len(self.vix_data) > 0 and len(self.spy_data) > 0:
                self.last_update = datetime.now()
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error actualizando datos VIX: {e}")
            return False
    
    def get_vix_level(self, vix_value: float) -> VIXLevel:
        """
        Determinar el nivel de VIX basado en el valor
        
        Args:
            vix_value: Valor actual del VIX
            
        Returns:
            VIXLevel: Nivel de volatilidad correspondiente
        """
        for level, (min_val, max_val) in self.vix_thresholds.items():
            if min_val <= vix_value < max_val:
                return level
        return VIXLevel.EXTREMELY_HIGH
    
    def get_market_sentiment(self, vix_value: float, percentile: float) -> MarketSentiment:
        """
        Determinar sentimiento del mercado basado en VIX y percentil histórico
        
        Args:
            vix_value: Valor actual del VIX
            percentile: Percentil histórico del VIX
            
        Returns:
            MarketSentiment: Sentimiento del mercado
        """
        if percentile <= 10 or vix_value < 12:
            return MarketSentiment.EXTREME_GREED
        elif percentile <= 25 or vix_value < 16:
            return MarketSentiment.GREED
        elif percentile <= 75 and 16 <= vix_value <= 25:
            return MarketSentiment.NEUTRAL
        elif percentile <= 90 or vix_value < 35:
            return MarketSentiment.FEAR
        else:
            return MarketSentiment.EXTREME_FEAR
    
    def calculate_fear_greed_index(self, vix_value: float, percentile: float) -> float:
        """
        Calcular índice de miedo/codicia (0-100)
        
        Args:
            vix_value: Valor actual del VIX
            percentile: Percentil histórico
            
        Returns:
            float: Índice 0-100 (0=Extreme Fear, 100=Extreme Greed)
        """
        # Invertir percentil (VIX alto = miedo = índice bajo)
        base_index = 100 - percentile
        
        # Ajustar por niveles absolutos de VIX
        if vix_value > 40:
            adjustment = -20
        elif vix_value > 30:
            adjustment = -10
        elif vix_value < 12:
            adjustment = 20
        elif vix_value < 16:
            adjustment = 10
        else:
            adjustment = 0
        
        fear_greed_index = max(0, min(100, base_index + adjustment))
        return fear_greed_index
    
    def analyze_mean_reversion(self, current_vix: float) -> Tuple[str, float]:
        """
        Analizar señal de reversión a la media del VIX
        
        Args:
            current_vix: Valor actual del VIX
            
        Returns:
            Tuple[str, float]: (señal, fuerza de la señal)
        """
        if self.vix_data is None or len(self.vix_data) < 30:
            return "hold", 0.0
        
        # Calcular estadísticas históricas
        vix_closes = self.vix_data['Close'].dropna()
        mean_vix = vix_closes.mean()
        std_vix = vix_closes.std()
        
        # Calcular desviación de la media
        z_score = (current_vix - mean_vix) / std_vix
        
        # Generar señales
        threshold = self.signal_config['mean_reversion_threshold']
        
        if z_score > threshold:
            # VIX muy alto -> esperar reversión -> señal de compra
            signal = "buy"
            strength = min(1.0, abs(z_score) / (threshold * 2))
        elif z_score < -threshold:
            # VIX muy bajo -> esperar aumento volatilidad -> señal de venta
            signal = "sell"
            strength = min(1.0, abs(z_score) / (threshold * 2))
        else:
            signal = "hold"
            strength = 0.0
        
        return signal, strength
    
    def analyze_volatility_trend(self) -> str:
        """
        Analizar tendencia de la volatilidad
        
        Returns:
            str: 'increasing', 'decreasing', 'stable'
        """
        if self.vix_data is None or len(self.vix_data) < self.signal_config['trend_window']:
            return "stable"
        
        # Obtener datos recientes
        recent_data = self.vix_data['Close'].tail(self.signal_config['trend_window'])
        
        # Calcular tendencia usando regresión lineal simple
        x = np.arange(len(recent_data))
        y = recent_data.values
        
        # Coeficiente de correlación
        correlation = np.corrcoef(x, y)[0, 1]
        
        if correlation > 0.3:
            return "increasing"
        elif correlation < -0.3:
            return "decreasing"
        else:
            return "stable"
    
    def generate_trading_signal(self, analysis_data: Dict) -> VIXSignal:
        """
        Generar señal de trading basada en análisis VIX
        
        Args:
            analysis_data: Datos del análisis VIX
            
        Returns:
            VIXSignal: Señal de trading generada
        """
        current_vix = analysis_data['current_vix']
        sentiment = analysis_data['sentiment']
        mean_reversion_signal = analysis_data['mean_reversion_signal']
        volatility_trend = analysis_data['volatility_trend']
        percentile = analysis_data['percentile_rank']
        
        # Lógica de señales
        signal_type = "hold"
        signal_strength = 0.0
        confidence = 0.5
        reasoning = "Condiciones neutrales"
        
        # Señales basadas en extremos de VIX
        if sentiment == MarketSentiment.EXTREME_FEAR and mean_reversion_signal == "buy":
            signal_type = "buy"
            signal_strength = 0.8
            confidence = 0.9
            reasoning = "VIX en niveles extremos de miedo - oportunidad de compra"
            
        elif sentiment == MarketSentiment.EXTREME_GREED and mean_reversion_signal == "sell":
            signal_type = "sell"
            signal_strength = 0.7
            confidence = 0.8
            reasoning = "VIX en niveles de complacencia extrema - riesgo de corrección"
            
        elif sentiment == MarketSentiment.FEAR and volatility_trend == "decreasing":
            signal_type = "buy"
            signal_strength = 0.6
            confidence = 0.7
            reasoning = "Miedo disminuyendo - posible recuperación del mercado"
            
        elif sentiment == MarketSentiment.GREED and volatility_trend == "increasing":
            signal_type = "sell"
            signal_strength = 0.5
            confidence = 0.6
            reasoning = "Complacencia con volatilidad creciente - precaución"
        
        # Ajustar por percentil histórico
        if percentile > 95:
            if signal_type == "buy":
                signal_strength = min(1.0, signal_strength + 0.2)
                confidence = min(1.0, confidence + 0.1)
        elif percentile < 5:
            if signal_type == "sell":
                signal_strength = min(1.0, signal_strength + 0.2)
                confidence = min(1.0, confidence + 0.1)
        
        return VIXSignal(
            timestamp=datetime.now(),
            vix_value=current_vix,
            vix_level=analysis_data['vix_level'],
            sentiment=sentiment,
            signal_type=signal_type,
            signal_strength=signal_strength,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def get_historical_context(self) -> Dict:
        """
        Obtener contexto histórico del VIX
        
        Returns:
            Dict: Estadísticas históricas del VIX
        """
        if self.vix_data is None:
            return {}
        
        vix_closes = self.vix_data['Close'].dropna()
        
        return {
            'mean': float(vix_closes.mean()),
            'median': float(vix_closes.median()),
            'std': float(vix_closes.std()),
            'min': float(vix_closes.min()),
            'max': float(vix_closes.max()),
            'percentile_25': float(vix_closes.quantile(0.25)),
            'percentile_75': float(vix_closes.quantile(0.75)),
            'current_vs_mean': float(vix_closes.iloc[-1] / vix_closes.mean()),
            'days_analyzed': len(vix_closes)
        }
    
    def generate_recommendations(self, analysis: VIXAnalysis) -> List[str]:
        """
        Generar recomendaciones basadas en análisis VIX
        
        Args:
            analysis: Análisis VIX completo
            
        Returns:
            List[str]: Lista de recomendaciones
        """
        recommendations = []
        
        # Recomendaciones por nivel de VIX
        if analysis.vix_level == VIXLevel.EXTREMELY_HIGH:
            recommendations.extend([
                "Considerar oportunidades de compra en activos de calidad",
                "Implementar estrategias de volatilidad (venta de opciones)",
                "Mantener liquidez para aprovechar dislocaciones del mercado"
            ])
        elif analysis.vix_level == VIXLevel.EXTREMELY_LOW:
            recommendations.extend([
                "Considerar protección de cartera (compra de puts)",
                "Reducir exposición a activos de riesgo",
                "Prepararse para aumento de volatilidad"
            ])
        
        # Recomendaciones por sentimiento
        if analysis.sentiment == MarketSentiment.EXTREME_FEAR:
            recommendations.append("Oportunidad contrarian - mercado oversold")
        elif analysis.sentiment == MarketSentiment.EXTREME_GREED:
            recommendations.append("Precaución - mercado potencialmente overbought")
        
        # Recomendaciones por señal de trading
        if analysis.trading_signal.signal_type == "buy" and analysis.trading_signal.confidence > 0.7:
            recommendations.append("Señal de compra con alta confianza - considerar incrementar posiciones")
        elif analysis.trading_signal.signal_type == "sell" and analysis.trading_signal.confidence > 0.7:
            recommendations.append("Señal de venta con alta confianza - considerar reducir exposición")
        
        return recommendations
    
    def analyze(self, force_update: bool = False) -> Optional[VIXAnalysis]:
        """
        Realizar análisis completo del VIX
        
        Args:
            force_update: Forzar actualización de datos
            
        Returns:
            Optional[VIXAnalysis]: Análisis completo o None si hay error
        """
        try:
            # Actualizar datos
            if not self.update_data(force_update):
                return None
            
            if self.vix_data is None or len(self.vix_data) == 0:
                return None
            
            # Obtener valor actual del VIX
            current_vix = float(self.vix_data['Close'].iloc[-1])
            
            # Calcular percentil histórico
            vix_closes = self.vix_data['Close'].dropna()
            percentile_rank = (vix_closes <= current_vix).mean() * 100
            
            # Determinar nivel y sentimiento
            vix_level = self.get_vix_level(current_vix)
            sentiment = self.get_market_sentiment(current_vix, percentile_rank)
            
            # Calcular índice miedo/codicia
            fear_greed_index = self.calculate_fear_greed_index(current_vix, percentile_rank)
            
            # Analizar reversión a la media
            mean_reversion_signal, _ = self.analyze_mean_reversion(current_vix)
            
            # Analizar tendencia de volatilidad
            volatility_trend = self.analyze_volatility_trend()
            
            # Obtener contexto histórico
            historical_context = self.get_historical_context()
            
            # Preparar datos para señal de trading
            analysis_data = {
                'current_vix': current_vix,
                'vix_level': vix_level,
                'sentiment': sentiment,
                'percentile_rank': percentile_rank,
                'mean_reversion_signal': mean_reversion_signal,
                'volatility_trend': volatility_trend
            }
            
            # Generar señal de trading
            trading_signal = self.generate_trading_signal(analysis_data)
            
            # Crear análisis completo
            analysis = VIXAnalysis(
                current_vix=current_vix,
                vix_level=vix_level,
                sentiment=sentiment,
                percentile_rank=percentile_rank,
                mean_reversion_signal=mean_reversion_signal,
                volatility_trend=volatility_trend,
                fear_greed_index=fear_greed_index,
                trading_signal=trading_signal,
                historical_context=historical_context,
                recommendations=[]
            )
            
            # Generar recomendaciones
            analysis.recommendations = self.generate_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            print(f"Error en análisis VIX: {e}")
            return None
    
    def get_vix_correlation_with_spy(self, days: int = 30) -> float:
        """
        Calcular correlación entre VIX y SPY
        
        Args:
            days: Días para calcular correlación
            
        Returns:
            float: Coeficiente de correlación
        """
        if self.vix_data is None or self.spy_data is None:
            return 0.0
        
        try:
            # Obtener datos recientes
            vix_recent = self.vix_data['Close'].tail(days)
            spy_recent = self.spy_data['Close'].tail(days)
            
            # Alinear fechas
            common_dates = vix_recent.index.intersection(spy_recent.index)
            if len(common_dates) < 10:
                return 0.0
            
            vix_aligned = vix_recent.loc[common_dates]
            spy_aligned = spy_recent.loc[common_dates]
            
            # Calcular correlación
            correlation = np.corrcoef(vix_aligned.values, spy_aligned.values)[0, 1]
            return float(correlation) if not np.isnan(correlation) else 0.0
            
        except Exception:
            return 0.0
    
    def export_analysis_to_dict(self, analysis: VIXAnalysis) -> Dict:
        """
        Exportar análisis a diccionario para integración con otros módulos
        
        Args:
            analysis: Análisis VIX
            
        Returns:
            Dict: Análisis en formato diccionario
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'current_vix': analysis.current_vix,
            'vix_level': analysis.vix_level.value,
            'sentiment': analysis.sentiment.value,
            'percentile_rank': analysis.percentile_rank,
            'fear_greed_index': analysis.fear_greed_index,
            'mean_reversion_signal': analysis.mean_reversion_signal,
            'volatility_trend': analysis.volatility_trend,
            'trading_signal': {
                'type': analysis.trading_signal.signal_type,
                'strength': analysis.trading_signal.signal_strength,
                'confidence': analysis.trading_signal.confidence,
                'reasoning': analysis.trading_signal.reasoning
            },
            'historical_context': analysis.historical_context,
            'recommendations': analysis.recommendations,
            'spy_correlation': self.get_vix_correlation_with_spy()
        }

# Función de utilidad para uso rápido
def get_vix_analysis(force_update: bool = False) -> Optional[Dict]:
    """
    Función de utilidad para obtener análisis VIX rápido
    
    Args:
        force_update: Forzar actualización de datos
        
    Returns:
        Optional[Dict]: Análisis VIX en formato diccionario
    """
    analyzer = VIXAnalyzer()
    analysis = analyzer.analyze(force_update)
    
    if analysis:
        return analyzer.export_analysis_to_dict(analysis)
    return None

if __name__ == "__main__":
    # Demo del módulo VIX
    print("=== SICAR VIX Analyzer Demo ===")
    
    analyzer = VIXAnalyzer()
    analysis = analyzer.analyze(force_update=True)
    
    if analysis:
        print(f"\n📊 VIX Actual: {analysis.current_vix:.2f}")
        print(f"📈 Nivel: {analysis.vix_level.value}")
        print(f"😰 Sentimiento: {analysis.sentiment.value}")
        print(f"📊 Percentil Histórico: {analysis.percentile_rank:.1f}%")
        print(f"😱 Índice Miedo/Codicia: {analysis.fear_greed_index:.1f}/100")
        print(f"🔄 Señal Reversión: {analysis.mean_reversion_signal}")
        print(f"📈 Tendencia Volatilidad: {analysis.volatility_trend}")
        
        print(f"\n🎯 Señal de Trading:")
        signal = analysis.trading_signal
        print(f"   Tipo: {signal.signal_type.upper()}")
        print(f"   Fuerza: {signal.signal_strength:.2f}")
        print(f"   Confianza: {signal.confidence:.2f}")
        print(f"   Razón: {signal.reasoning}")
        
        print(f"\n💡 Recomendaciones:")
        for i, rec in enumerate(analysis.recommendations, 1):
            print(f"   {i}. {rec}")
    else:
        print("❌ Error obteniendo análisis VIX")