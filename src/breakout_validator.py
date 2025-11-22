#!/usr/bin/env python3
"""
Sistema de validación de rupturas anti-fakeout
Valida señales de trading usando 6 factores para evitar falsas rupturas
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
import ta

logger = logging.getLogger(__name__)

class BreakoutStatus(Enum):
    """Estado de validación de ruptura"""
    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class BreakoutType(Enum):
    """Tipo de ruptura"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class BreakoutValidator:
    """
    Validador de rupturas anti-fakeout con sistema de 6 factores
    """
    
    def __init__(self):
        self.validation_threshold = 4  # Mínimo 4/6 factores para validar
        self.factors = {}
        self.validation_history = []
    
    def validate_breakout(self, 
                         data: pd.DataFrame, 
                         signal_type: str,
                         current_price: float,
                         sentiment_data: Dict = None,
                         structural_levels: Dict = None) -> Dict:
        """
        Validar ruptura usando sistema de 6 factores
        
        Args:
            data: DataFrame con datos OHLCV
            signal_type: Tipo de señal (BUY/SELL)
            current_price: Precio actual
            sentiment_data: Datos de sentimiento de mercado
            structural_levels: Niveles estructurales de soporte/resistencia
            
        Returns:
            Dict con resultado de validación
        """
        logger.info(f"Validando ruptura {signal_type} a ${current_price:,.2f}")
        
        if len(data) < 50:
            return self._create_insufficient_result("Datos insuficientes")
        
        # Determinar tipo de ruptura
        breakout_type = BreakoutType.BULLISH if signal_type == "BUY" else BreakoutType.BEARISH
        
        # Inicializar factores
        factors = {}
        warnings = []
        
        # Factor 1: Volumen (¿Volumen actual > 1.5x promedio 20 días?)
        volume_score, volume_warning = self._check_volume_factor(data)
        factors['volume'] = volume_score
        if volume_warning:
            warnings.append(volume_warning)
        
        # Factor 2: Momentum (RSI tiene espacio, no sobrecomprado/sobrevendido)
        momentum_score, momentum_warning = self._check_momentum_factor(data, breakout_type)
        factors['momentum'] = momentum_score
        if momentum_warning:
            warnings.append(momentum_warning)
        
        # Factor 3: Tiempo (¿Están alineados H4 y D1?)
        timeframe_score, timeframe_warning = self._check_timeframe_alignment(data, breakout_type)
        factors['timeframe'] = timeframe_score
        if timeframe_warning:
            warnings.append(timeframe_warning)
        
        # Factor 4: Proximidad (¿Estamos lejos de resistencia/sobre soporte?)
        proximity_score, proximity_warning = self._check_proximity_factor(
            data, current_price, breakout_type, structural_levels
        )
        factors['proximity'] = proximity_score
        if proximity_warning:
            warnings.append(proximity_warning)
        
        # Factor 5: Volatilidad (¿Precio está en bandas lógicas?)
        volatility_score, volatility_warning = self._check_volatility_factor(data, current_price)
        factors['volatility'] = volatility_score
        if volatility_warning:
            warnings.append(volatility_warning)
        
        # Factor 6: Sentimiento (¿No operamos contra sentimiento extremo?)
        sentiment_score, sentiment_warning = self._check_sentiment_factor(sentiment_data, breakout_type)
        factors['sentiment'] = sentiment_score
        if sentiment_warning:
            warnings.append(sentiment_warning)
        
        # Calcular score total
        total_score = sum(factors.values())
        is_valid = total_score >= self.validation_threshold
        
        # Determinar estado
        status = BreakoutStatus.VALID if is_valid else BreakoutStatus.INVALID
        
        # Crear resultado
        result = {
            'status': status.value,
            'breakout_type': breakout_type.value,
            'total_score': total_score,
            'validation_threshold': self.validation_threshold,
            'factors': factors,
            'is_valid': is_valid,
            'warnings': warnings,
            'recommendation': self._get_recommendation(is_valid, total_score, warnings),
            'timestamp': datetime.now().isoformat(),
            'price': current_price,
            'signal_type': signal_type
        }
        
        # Guardar en historial
        self.validation_history.append(result)
        
        logger.info(f"Validación completada: {status.value} (Score: {total_score}/{self.validation_threshold})")
        logger.info(f"Factores: {factors}")
        
        return result
    
    def _check_volume_factor(self, data: pd.DataFrame) -> Tuple[int, Optional[str]]:
        """
        Factor 1: Volumen - ¿El volumen actual es > 1.5x el promedio de 20 días?
        """
        try:
            if 'volume' not in data.columns:
                return 0, "Volumen no disponible"
            
            current_volume = data['volume'].iloc[-1]
            volume_ma_20 = data['volume'].rolling(window=20).mean().iloc[-1]
            
            if volume_ma_20 <= 0:
                return 0, "Promedio de volumen inválido"
            
            volume_ratio = current_volume / volume_ma_20
            
            if volume_ratio > 1.5:
                return 1, None  # ✅ Volumen confirmado
            elif volume_ratio > 1.2:
                return 0, "Volumen ligeramente alto pero no suficiente"
            else:
                return 0, f"Volumen insuficiente ({volume_ratio:.2f}x vs 1.5x requerido)"
                
        except Exception as e:
            logger.error(f"Error en factor volumen: {e}")
            return 0, f"Error calculando volumen: {e}"
    
    def _check_momentum_factor(self, data: pd.DataFrame, breakout_type: BreakoutType) -> Tuple[int, Optional[str]]:
        """
        Factor 2: Momentum - ¿RSI tiene espacio? (No sobrecomprado/sobrevendido)
        """
        try:
            if len(data) < 14:
                return 0, "Datos insuficientes para RSI"
            
            # Calcular RSI
            rsi = ta.momentum.RSIIndicator(data['close']).rsi()
            current_rsi = rsi.iloc[-1]
            
            if pd.isna(current_rsi):
                return 0, "RSI no calculable"
            
            # Validar según tipo de ruptura
            if breakout_type == BreakoutType.BULLISH:
                # Para compra: RSI no debe estar sobrecomprado (>75)
                if current_rsi < 70:
                    return 1, None  # ✅ RSI tiene espacio al alza
                elif current_rsi < 75:
                    return 0, f"RSI cercano a sobrecompra ({current_rsi:.1f})"
                else:
                    return 0, f"RSI sobrecomprado ({current_rsi:.1f} > 75)"
            
            else:  # BEARISH
                # Para venta: RSI no debe estar sobrevendido (<25)
                if current_rsi > 30:
                    return 1, None  # ✅ RSI tiene espacio a la baja
                elif current_rsi > 25:
                    return 0, f"RSI cercano a sobrevendido ({current_rsi:.1f})"
                else:
                    return 0, f"RSI sobrevendido ({current_rsi:.1f} < 25)"
                    
        except Exception as e:
            logger.error(f"Error en factor momentum: {e}")
            return 0, f"Error calculando RSI: {e}"
    
    def _check_timeframe_alignment(self, data: pd.DataFrame, breakout_type: BreakoutType) -> Tuple[int, Optional[str]]:
        """
        Factor 3: Tiempo - ¿Están alineados H4 y D1?
        """
        try:
            if len(data) < 100:
                return 0, "Datos insuficientes para análisis de timeframe"
            
            # Calcular tendencias en diferentes ventanas
            # Tendencia de 4 horas (últimos 4-6 períodos dependiendo de timeframe)
            recent_data = data.tail(6)  # Aproximadamente 6 horas
            older_data = data.tail(24).head(18)  # 18 horas previas
            
            if len(recent_data) < 4 or len(older_data) < 10:
                return 0, "Datos insuficientes para tendencias"
            
            # Calcular tendencias usando pendientes de regresión lineal
            recent_trend = self._calculate_trend_slope(recent_data['close'])
            older_trend = self._calculate_trend_slope(older_data['close'])
            
            # Verificar alineación
            if breakout_type == BreakoutType.BULLISH:
                # Ambas tendencias deben ser alcistas
                if recent_trend > 0 and older_trend > 0:
                    return 1, None  # ✅ Tendencias alineadas al alza
                elif recent_trend > 0:
                    return 0, "Tendencia reciente alcista pero tendencia mayor mixta"
                else:
                    return 0, f"Tendencias conflictivas (reciente: {recent_trend:.4f}, mayor: {older_trend:.4f})"
            
            else:  # BEARISH
                # Ambas tendencias deben ser bajistas
                if recent_trend < 0 and older_trend < 0:
                    return 1, None  # ✅ Tendencias alineadas a la baja
                elif recent_trend < 0:
                    return 0, "Tendencia reciente bajista pero tendencia mayor mixta"
                else:
                    return 0, f"Tendencias conflictivas (reciente: {recent_trend:.4f}, mayor: {older_trend:.4f})"
                    
        except Exception as e:
            logger.error(f"Error en factor timeframe: {e}")
            return 0, f"Error analizando timeframes: {e}"
    
    def _check_proximity_factor(self, data: pd.DataFrame, current_price: float, 
                               breakout_type: BreakoutType, structural_levels: Dict = None) -> Tuple[int, Optional[str]]:
        """
        Factor 4: Proximidad - ¿Estamos lejos de resistencia/sobre soporte?
        """
        try:
            # Obtener niveles clave
            if structural_levels and 'resistance_levels' in structural_levels and 'support_levels' in structural_levels:
                resistance_levels = structural_levels['resistance_levels']
                support_levels = structural_levels['support_levels']
            else:
                # Calcular niveles desde datos recientes
                recent_high = data['high'].tail(50).max()
                recent_low = data['low'].tail(50).min()
                resistance_levels = [recent_high * 0.98, recent_high]  # 2% debajo y en el máximo
                support_levels = [recent_low, recent_low * 1.02]  # En el mínimo y 2% arriba
            
            if breakout_type == BreakoutType.BULLISH:
                # Para compra: verificar distancia a resistencia más cercana
                if resistance_levels:
                    nearest_resistance = min([level for level in resistance_levels if level > current_price], default=None)
                    if nearest_resistance:
                        distance_pct = (nearest_resistance - current_price) / current_price
                        if distance_pct > 0.05:  # Más del 5% de espacio
                            return 1, None  # ✅ Espacio suficiente al alza
                        elif distance_pct > 0.03:  # Entre 3-5%
                            return 0, f"Cerca de resistencia ({distance_pct:.1%} de espacio)"
                        else:
                            return 0, f"Demasiado cerca de resistencia ({distance_pct:.1%} < 5%)"
                
                # Si no hay resistencia clara, verificar si estamos sobre soporte
                if support_levels:
                    nearest_support = max([level for level in support_levels if level < current_price], default=None)
                    if nearest_support:
                        support_distance_pct = (current_price - nearest_support) / current_price
                        if support_distance_pct < 0.02:  # Muy cerca del soporte
                            return 1, None  # ✅ Sobre soporte
                        else:
                            return 0, "Lejos de niveles clave de soporte"
                
                return 0, "No se encontraron niveles de resistencia/soporte relevantes"
            
            else:  # BEARISH
                # Para venta: verificar distancia a soporte más cercano
                if support_levels:
                    nearest_support = max([level for level in support_levels if level < current_price], default=None)
                    if nearest_support:
                        distance_pct = (current_price - nearest_support) / current_price
                        if distance_pct > 0.05:  # Más del 5% de espacio
                            return 1, None  # ✅ Espacio suficiente a la baja
                        elif distance_pct > 0.03:  # Entre 3-5%
                            return 0, f"Cerca de soporte ({distance_pct:.1%} de espacio)"
                        else:
                            return 0, f"Demasiado cerca de soporte ({distance_pct:.1%} < 5%)"
                
                # Si no hay soporte claro, verificar si estamos bajo resistencia
                if resistance_levels:
                    nearest_resistance = min([level for level in resistance_levels if level > current_price], default=None)
                    if nearest_resistance:
                        resistance_distance_pct = (nearest_resistance - current_price) / current_price
                        if resistance_distance_pct < 0.02:  # Muy cerca de la resistencia
                            return 1, None  # ✅ Bajo resistencia
                        else:
                            return 0, "Lejos de niveles clave de resistencia"
                
                return 0, "No se encontraron niveles de soporte/resistencia relevantes"
                
        except Exception as e:
            logger.error(f"Error en factor proximidad: {e}")
            return 0, f"Error analizando proximidad: {e}"
    
    def _check_volatility_factor(self, data: pd.DataFrame, current_price: float) -> Tuple[int, Optional[str]]:
        """
        Factor 5: Volatilidad - ¿El precio está en bandas lógicas?
        """
        try:
            if len(data) < 20:
                return 0, "Datos insuficientes para análisis de volatilidad"
            
            # Calcular Bollinger Bands
            bb = ta.volatility.BollingerBands(data['close'])
            upper_band = bb.bollinger_hband().iloc[-1]
            lower_band = bb.bollinger_lband().iloc[-1]
            
            if pd.isna(upper_band) or pd.isna(lower_band):
                return 0, "Bandas de Bollinger no calculables"
            
            # Verificar si el precio está en zona extrema (más allá de 2% de las bandas)
            upper_threshold = upper_band * 1.02  # 2% arriba de la banda superior
            lower_threshold = lower_band * 0.98  # 2% abajo de la banda inferior
            
            if current_price > upper_threshold:
                return 0, f"Precio en extensión volátil extrema (>{upper_threshold:.2f})"
            elif current_price < lower_threshold:
                return 0, f"Precio en extensión volátil extrema (<{lower_threshold:.2f})"
            elif current_price > upper_band or current_price < lower_band:
                return 0, "Precio fuera de bandas de Bollinger (alta volatilidad)"
            else:
                return 1, None  # ✅ Precio en rango volátil normal
                
        except Exception as e:
            logger.error(f"Error en factor volatilidad: {e}")
            return 0, f"Error analizando volatilidad: {e}"
    
    def _check_sentiment_factor(self, sentiment_data: Dict, breakout_type: BreakoutType) -> Tuple[int, Optional[str]]:
        """
        Factor 6: Sentimiento - ¿No operamos contra sentimiento extremo?
        """
        try:
            if not sentiment_data:
                return 0, "Datos de sentimiento no disponibles"
            
            # Obtener score de sentimiento
            combined_score = sentiment_data.get('combined_score', 0)
            extreme_fear = sentiment_data.get('extreme_fear_signal', False)
            extreme_greed = sentiment_data.get('extreme_greed_signal', False)
            
            # Lógica contrarian adaptada
            if breakout_type == BreakoutType.BULLISH:
                # Para compra: evitar comprar en miedo extremo sin confirmación
                if extreme_fear and combined_score < -0.5:
                    return 0, "Miedo extremo detectado (Catching Knife)"
                elif extreme_fear and combined_score > -0.3:
                    return 1, None  # ✅ Miedo moderado, oportunidad de compra
                elif extreme_greed:
                    return 0, "Codicia extrema detectada (posible tope)"
                else:
                    return 1, None  # ✅ Sentimiento neutral o favorable
            
            else:  # BEARISH
                # Para venta: evitar vender en codicia extrema sin confirmación
                if extreme_greed and combined_score > 0.5:
                    return 0, "Codicia extrema detectada (posible fondo)"
                elif extreme_greed and combined_score < 0.3:
                    return 1, None  # ✅ Codicia moderada, oportunidad de venta
                elif extreme_fear:
                    return 0, "Miedo extremo detectado (posible rebote)"
                else:
                    return 1, None  # ✅ Sentimiento neutral o favorable
                    
        except Exception as e:
            logger.error(f"Error en factor sentimiento: {e}")
            return 0, f"Error analizando sentimiento: {e}"
    
    def _calculate_trend_slope(self, prices: pd.Series) -> float:
        """
        Calcular pendiente de tendencia usando regresión lineal
        """
        try:
            if len(prices) < 3:
                return 0.0
            
            x = np.arange(len(prices))
            y = prices.values
            
            # Regresión lineal
            slope = np.polyfit(x, y, 1)
            
            return float(slope[0])
            
        except Exception as e:
            logger.error(f"Error calculando pendiente de tendencia: {e}")
            return 0.0
    
    def _get_recommendation(self, is_valid: bool, total_score: int, warnings: List[str]) -> str:
        """
        Generar recomendación basada en validación
        """
        if is_valid:
            if total_score == 6:
                return "SEÑAL FUERTE: Alta probabilidad de éxito"
            elif total_score >= 5:
                return "SEÑAL VÁLIDA: Buena probabilidad de éxito"
            else:
                return "SEÑAL VÁLIDA: Probabilidad moderada de éxito"
        else:
            if total_score <= 2:
                return "EVITAR: Muy baja probabilidad de éxito"
            elif total_score <= 3:
                return "ESPERAR: Condiciones no favorables"
            else:
                return "ESPERAR: Casi válido pero con riesgos"
    
    def get_validation_summary(self, limit: int = 10) -> Dict:
        """
        Obtener resumen de validaciones recientes
        """
        if not self.validation_history:
            return {'message': 'No hay validaciones en el historial'}
        
        recent_validations = self.validation_history[-limit:]
        
        valid_count = sum(1 for v in recent_validations if v['is_valid'])
        total_count = len(recent_validations)
        
        avg_score = sum(v['total_score'] for v in recent_validations) / total_count
        
        factor_performance = {}
        for factor in ['volume', 'momentum', 'timeframe', 'proximity', 'volatility', 'sentiment']:
            factor_scores = [v['factors'].get(factor, 0) for v in recent_validations]
            factor_performance[factor] = {
                'avg_score': sum(factor_scores) / len(factor_scores),
                'success_rate': sum(factor_scores) / len(factor_scores) * 100
            }
        
        return {
            'total_validations': total_count,
            'valid_signals': valid_count,
            'invalid_signals': total_count - valid_count,
            'success_rate': (valid_count / total_count * 100) if total_count > 0 else 0,
            'average_score': avg_score,
            'factor_performance': factor_performance,
            'recent_validations': recent_validations
        }

def test_breakout_validator():
    """Función de prueba para el validador de rupturas"""
    print("🧪 Probando BreakoutValidator...")
    
    # Crear datos de prueba
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1H')
    
    # Simular datos con tendencia alcista
    base_price = 50000
    trend = np.linspace(0, 0.1, len(dates))  # Tendencia alcista 10%
    noise = np.random.normal(0, 0.02, len(dates))
    
    prices = base_price * (1 + trend + noise)
    
    test_data = pd.DataFrame({
        'timestamp': dates,
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000, 5000, len(dates))
    })
    
    # Agregar indicadores técnicos
    test_data['rsi'] = ta.momentum.RSIIndicator(test_data['close']).rsi()
    
    validator = BreakoutValidator()
    
    # Test BUY signal
    print("\n📈 Validando señal BUY:")
    sentiment_data = {
        'combined_score': -0.2,  # Sentimiento neutral ligeramente bajista
        'extreme_fear_signal': False,
        'extreme_greed_signal': False
    }
    
    result = validator.validate_breakout(
        data=test_data,
        signal_type="BUY",
        current_price=test_data['close'].iloc[-1],
        sentiment_data=sentiment_data
    )
    
    print(f"   Estado: {result['status']}")
    print(f"   Score: {result['total_score']}/{result['validation_threshold']}")
    print(f"   Factores: {result['factors']}")
    print(f"   Recomendación: {result['recommendation']}")
    
    # Test SELL signal
    print("\n📉 Validando señal SELL:")
    result_sell = validator.validate_breakout(
        data=test_data,
        signal_type="SELL",
        current_price=test_data['close'].iloc[-1],
        sentiment_data=sentiment_data
    )
    
    print(f"   Estado: {result_sell['status']}")
    print(f"   Score: {result_sell['total_score']}/{result_sell['validation_threshold']}")
    print(f"   Recomendación: {result_sell['recommendation']}")
    
    # Resumen
    print("\n📊 Resumen de validaciones:")
    summary = validator.get_validation_summary()
    print(f"   Tasa de éxito: {summary['success_rate']:.1f}%")
    print(f"   Score promedio: {summary['average_score']:.2f}")
    
    print("\n✅ Validación de rupturas completada!")

if __name__ == '__main__':
    test_breakout_validator()