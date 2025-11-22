"""
Sistema Avanzado de Análisis Técnico - Phase 2
Detecta patrones complejos, ondas de Elliott, y análisis técnico avanzado
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum
import scipy.signal as signal
from scipy.stats import linregress

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PatternType(Enum):
    """Tipos de patrones técnicos"""
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "inverse_head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIANGLE_ASCENDING = "triangle_ascending"
    TRIANGLE_DESCENDING = "triangle_descending"
    TRIANGLE_SYMMETRICAL = "triangle_symmetrical"
    WEDGE_RISING = "wedge_rising"
    WEDGE_FALLING = "wedge_falling"
    FLAG_BULLISH = "flag_bullish"
    FLAG_BEARISH = "flag_bearish"
    PENNANT = "pennant"
    CUP_AND_HANDLE = "cup_and_handle"

class WaveType(Enum):
    """Tipos de ondas de Elliott"""
    IMPULSE_1 = "impulse_1"
    IMPULSE_3 = "impulse_3"
    IMPULSE_5 = "impulse_5"
    CORRECTIVE_A = "corrective_a"
    CORRECTIVE_B = "corrective_b"
    CORRECTIVE_C = "corrective_c"

@dataclass
class TechnicalPattern:
    """Estructura para patrones técnicos detectados"""
    pattern_type: PatternType
    confidence: float
    start_index: int
    end_index: int
    key_levels: List[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    timeframe_strength: str
    description: str

@dataclass
class WaveAnalysis:
    """Análisis de ondas de Elliott"""
    wave_type: WaveType
    wave_degree: str
    start_price: float
    end_price: float
    retracement_level: float
    projection_target: Optional[float]
    confidence: float

@dataclass
class TechnicalSignal:
    """Señal técnica completa"""
    signal_type: str
    strength: float
    confidence: float
    entry_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    timeframe: str
    indicators_confluence: int
    pattern_support: bool

class AdvancedTechnicalAnalyzer:
    """
    Analizador técnico avanzado con detección de patrones complejos
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.patterns_history = {}
        self.waves_history = {}
        
        # Configuración de parámetros
        self.fibonacci_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]
        self.pattern_min_bars = 20
        self.pattern_max_bars = 200
        
        self.logger.info("✅ AdvancedTechnicalAnalyzer inicializado")
    
    def analyze_patterns(self, symbol: str, data: pd.DataFrame) -> List[TechnicalPattern]:
        """
        Análisis completo de patrones técnicos
        """
        try:
            if len(data) < self.pattern_min_bars:
                self.logger.warning(f"⚠️ Datos insuficientes para análisis de patrones: {len(data)} < {self.pattern_min_bars}")
                return []
            
            patterns = []
            
            # Detectar diferentes tipos de patrones
            patterns.extend(self._detect_head_and_shoulders(data))
            patterns.extend(self._detect_double_tops_bottoms(data))
            patterns.extend(self._detect_triangles(data))
            patterns.extend(self._detect_wedges(data))
            patterns.extend(self._detect_flags_pennants(data))
            patterns.extend(self._detect_cup_and_handle(data))
            
            # Filtrar patrones por confianza
            patterns = [p for p in patterns if p.confidence > 0.6]
            
            # Guardar en historial
            if symbol not in self.patterns_history:
                self.patterns_history[symbol] = []
            
            timestamp = datetime.now()
            for pattern in patterns:
                self.patterns_history[symbol].append({
                    'timestamp': timestamp,
                    'pattern': pattern
                })
            
            # Mantener solo últimos 50 patrones
            if len(self.patterns_history[symbol]) > 50:
                self.patterns_history[symbol] = self.patterns_history[symbol][-50:]
            
            self.logger.info(f"📊 Detectados {len(patterns)} patrones para {symbol}")
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando patrones para {symbol}: {e}")
            return []
    
    def _detect_head_and_shoulders(self, data: pd.DataFrame) -> List[TechnicalPattern]:
        """
        Detecta patrones de cabeza y hombros
        """
        patterns = []
        
        try:
            highs = data['high'].values
            lows = data['low'].values
            
            # Buscar picos y valles
            peaks, _ = signal.find_peaks(highs, distance=5, prominence=np.std(highs) * 0.5)
            valleys, _ = signal.find_peaks(-lows, distance=5, prominence=np.std(lows) * 0.5)
            
            if len(peaks) >= 3 and len(valleys) >= 2:
                # Verificar patrón de cabeza y hombros
                for i in range(len(peaks) - 2):
                    left_shoulder = peaks[i]
                    head = peaks[i + 1]
                    right_shoulder = peaks[i + 2]
                    
                    # Verificar que la cabeza sea más alta que los hombros
                    if (highs[head] > highs[left_shoulder] and 
                        highs[head] > highs[right_shoulder] and
                        abs(highs[left_shoulder] - highs[right_shoulder]) / highs[head] < 0.05):
                        
                        # Calcular confianza
                        height_ratio = (highs[head] - min(highs[left_shoulder], highs[right_shoulder])) / highs[head]
                        symmetry = 1 - abs(highs[left_shoulder] - highs[right_shoulder]) / highs[head]
                        confidence = min(0.95, (height_ratio + symmetry) / 2)
                        
                        if confidence > 0.6:
                            # Encontrar línea de cuello
                            neckline_valleys = [v for v in valleys if left_shoulder < v < right_shoulder]
                            if neckline_valleys:
                                neckline_level = np.mean([lows[v] for v in neckline_valleys])
                                target_price = neckline_level - (highs[head] - neckline_level)
                                
                                pattern = TechnicalPattern(
                                    pattern_type=PatternType.HEAD_AND_SHOULDERS,
                                    confidence=confidence,
                                    start_index=left_shoulder,
                                    end_index=right_shoulder,
                                    key_levels=[highs[left_shoulder], highs[head], highs[right_shoulder], neckline_level],
                                    target_price=target_price,
                                    stop_loss=highs[head] * 1.02,
                                    timeframe_strength="medium",
                                    description=f"Cabeza y hombros con objetivo en {target_price:.2f}"
                                )
                                patterns.append(pattern)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error detectando cabeza y hombros: {e}")
        
        return patterns
    
    def _detect_double_tops_bottoms(self, data: pd.DataFrame) -> List[TechnicalPattern]:
        """
        Detecta patrones de doble techo y doble suelo
        """
        patterns = []
        
        try:
            highs = data['high'].values
            lows = data['low'].values
            
            # Buscar picos para doble techo
            peaks, _ = signal.find_peaks(highs, distance=10, prominence=np.std(highs) * 0.3)
            
            for i in range(len(peaks) - 1):
                peak1 = peaks[i]
                peak2 = peaks[i + 1]
                
                # Verificar que los picos sean similares
                price_diff = abs(highs[peak1] - highs[peak2]) / max(highs[peak1], highs[peak2])
                
                if price_diff < 0.03:  # Diferencia menor al 3%
                    # Buscar valle entre los picos
                    valley_between = np.argmin(lows[peak1:peak2+1]) + peak1
                    valley_depth = (min(highs[peak1], highs[peak2]) - lows[valley_between]) / min(highs[peak1], highs[peak2])
                    
                    if valley_depth > 0.02:  # Valle significativo
                        confidence = min(0.9, (1 - price_diff) * valley_depth * 10)
                        
                        if confidence > 0.6:
                            support_level = lows[valley_between]
                            target_price = support_level - (max(highs[peak1], highs[peak2]) - support_level) * 0.618
                            
                            pattern = TechnicalPattern(
                                pattern_type=PatternType.DOUBLE_TOP,
                                confidence=confidence,
                                start_index=peak1,
                                end_index=peak2,
                                key_levels=[highs[peak1], highs[peak2], support_level],
                                target_price=target_price,
                                stop_loss=max(highs[peak1], highs[peak2]) * 1.02,
                                timeframe_strength="strong",
                                description=f"Doble techo con soporte en {support_level:.2f}"
                            )
                            patterns.append(pattern)
            
            # Buscar valles para doble suelo
            valleys, _ = signal.find_peaks(-lows, distance=10, prominence=np.std(lows) * 0.3)
            
            for i in range(len(valleys) - 1):
                valley1 = valleys[i]
                valley2 = valleys[i + 1]
                
                price_diff = abs(lows[valley1] - lows[valley2]) / max(lows[valley1], lows[valley2])
                
                if price_diff < 0.03:
                    peak_between = np.argmax(highs[valley1:valley2+1]) + valley1
                    peak_height = (highs[peak_between] - max(lows[valley1], lows[valley2])) / max(lows[valley1], lows[valley2])
                    
                    if peak_height > 0.02:
                        confidence = min(0.9, (1 - price_diff) * peak_height * 10)
                        
                        if confidence > 0.6:
                            resistance_level = highs[peak_between]
                            target_price = resistance_level + (resistance_level - min(lows[valley1], lows[valley2])) * 0.618
                            
                            pattern = TechnicalPattern(
                                pattern_type=PatternType.DOUBLE_BOTTOM,
                                confidence=confidence,
                                start_index=valley1,
                                end_index=valley2,
                                key_levels=[lows[valley1], lows[valley2], resistance_level],
                                target_price=target_price,
                                stop_loss=min(lows[valley1], lows[valley2]) * 0.98,
                                timeframe_strength="strong",
                                description=f"Doble suelo con resistencia en {resistance_level:.2f}"
                            )
                            patterns.append(pattern)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error detectando dobles techos/suelos: {e}")
        
        return patterns
    
    def _detect_triangles(self, data: pd.DataFrame) -> List[TechnicalPattern]:
        """
        Detecta patrones triangulares
        """
        patterns = []
        
        try:
            if len(data) < 30:
                return patterns
            
            highs = data['high'].values
            lows = data['low'].values
            
            # Analizar últimos 50 períodos
            window = min(50, len(data))
            recent_highs = highs[-window:]
            recent_lows = lows[-window:]
            
            # Encontrar líneas de tendencia
            x = np.arange(len(recent_highs))
            
            # Línea de resistencia (máximos decrecientes)
            peaks, _ = signal.find_peaks(recent_highs, distance=3)
            if len(peaks) >= 2:
                resistance_slope, resistance_intercept, r_value_res, _, _ = linregress(peaks, recent_highs[peaks])
                
                # Línea de soporte (mínimos crecientes)
                valleys, _ = signal.find_peaks(-recent_lows, distance=3)
                if len(valleys) >= 2:
                    support_slope, support_intercept, r_value_sup, _, _ = linregress(valleys, recent_lows[valleys])
                    
                    # Determinar tipo de triángulo
                    if abs(r_value_res) > 0.7 and abs(r_value_sup) > 0.7:
                        if resistance_slope < -0.001 and support_slope > 0.001:
                            # Triángulo simétrico
                            pattern_type = PatternType.TRIANGLE_SYMMETRICAL
                            confidence = min(0.9, (abs(r_value_res) + abs(r_value_sup)) / 2)
                        elif resistance_slope > -0.0005 and support_slope > 0.001:
                            # Triángulo ascendente
                            pattern_type = PatternType.TRIANGLE_ASCENDING
                            confidence = min(0.85, abs(r_value_sup) * 0.9)
                        elif resistance_slope < -0.001 and support_slope > -0.0005:
                            # Triángulo descendente
                            pattern_type = PatternType.TRIANGLE_DESCENDING
                            confidence = min(0.85, abs(r_value_res) * 0.9)
                        else:
                            pattern_type = None
                            confidence = 0
                        
                        if confidence > 0.6:
                            # Calcular punto de convergencia
                            convergence_x = (support_intercept - resistance_intercept) / (resistance_slope - support_slope)
                            
                            if 0 < convergence_x < window * 1.5:  # Convergencia razonable
                                current_resistance = resistance_intercept + resistance_slope * (window - 1)
                                current_support = support_intercept + support_slope * (window - 1)
                                
                                # Objetivo basado en altura del triángulo
                                triangle_height = abs(recent_highs[peaks[0]] - recent_lows[valleys[0]])
                                
                                if pattern_type == PatternType.TRIANGLE_ASCENDING:
                                    target_price = current_resistance + triangle_height * 0.75
                                    stop_loss = current_support * 0.99
                                elif pattern_type == PatternType.TRIANGLE_DESCENDING:
                                    target_price = current_support - triangle_height * 0.75
                                    stop_loss = current_resistance * 1.01
                                else:  # Simétrico
                                    target_price = None
                                    stop_loss = None
                                
                                pattern = TechnicalPattern(
                                    pattern_type=pattern_type,
                                    confidence=confidence,
                                    start_index=len(data) - window,
                                    end_index=len(data) - 1,
                                    key_levels=[current_resistance, current_support],
                                    target_price=target_price,
                                    stop_loss=stop_loss,
                                    timeframe_strength="medium",
                                    description=f"Triángulo {pattern_type.value} con convergencia en {convergence_x:.0f} períodos"
                                )
                                patterns.append(pattern)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error detectando triángulos: {e}")
        
        return patterns
    
    def _detect_wedges(self, data: pd.DataFrame) -> List[TechnicalPattern]:
        """
        Detecta patrones de cuña
        """
        patterns = []
        
        try:
            if len(data) < 25:
                return patterns
            
            # Análisis similar a triángulos pero con criterios específicos para cuñas
            highs = data['high'].values
            lows = data['low'].values
            
            window = min(40, len(data))
            recent_highs = highs[-window:]
            recent_lows = lows[-window:]
            
            peaks, _ = signal.find_peaks(recent_highs, distance=3)
            valleys, _ = signal.find_peaks(-recent_lows, distance=3)
            
            if len(peaks) >= 3 and len(valleys) >= 3:
                # Calcular pendientes
                resistance_slope, _, r_res, _, _ = linregress(peaks, recent_highs[peaks])
                support_slope, _, r_sup, _, _ = linregress(valleys, recent_lows[valleys])
                
                # Cuña ascendente (ambas líneas suben, pero soporte más rápido)
                if (resistance_slope > 0 and support_slope > 0 and 
                    support_slope > resistance_slope and
                    abs(r_res) > 0.6 and abs(r_sup) > 0.6):
                    
                    confidence = min(0.8, (abs(r_res) + abs(r_sup)) / 2)
                    
                    if confidence > 0.6:
                        pattern = TechnicalPattern(
                            pattern_type=PatternType.WEDGE_RISING,
                            confidence=confidence,
                            start_index=len(data) - window,
                            end_index=len(data) - 1,
                            key_levels=[recent_highs[peaks[-1]], recent_lows[valleys[-1]]],
                            target_price=recent_lows[valleys[0]] * 0.95,  # Objetivo bajista
                            stop_loss=recent_highs[peaks[-1]] * 1.02,
                            timeframe_strength="medium",
                            description="Cuña ascendente - patrón bajista"
                        )
                        patterns.append(pattern)
                
                # Cuña descendente (ambas líneas bajan, pero resistencia más rápido)
                elif (resistance_slope < 0 and support_slope < 0 and 
                      resistance_slope < support_slope and
                      abs(r_res) > 0.6 and abs(r_sup) > 0.6):
                    
                    confidence = min(0.8, (abs(r_res) + abs(r_sup)) / 2)
                    
                    if confidence > 0.6:
                        pattern = TechnicalPattern(
                            pattern_type=PatternType.WEDGE_FALLING,
                            confidence=confidence,
                            start_index=len(data) - window,
                            end_index=len(data) - 1,
                            key_levels=[recent_highs[peaks[-1]], recent_lows[valleys[-1]]],
                            target_price=recent_highs[peaks[0]] * 1.05,  # Objetivo alcista
                            stop_loss=recent_lows[valleys[-1]] * 0.98,
                            timeframe_strength="medium",
                            description="Cuña descendente - patrón alcista"
                        )
                        patterns.append(pattern)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error detectando cuñas: {e}")
        
        return patterns
    
    def _detect_flags_pennants(self, data: pd.DataFrame) -> List[TechnicalPattern]:
        """
        Detecta banderas y banderines
        """
        patterns = []
        
        try:
            if len(data) < 20:
                return patterns
            
            closes = data['close'].values
            highs = data['high'].values
            lows = data['low'].values
            
            # Buscar movimiento fuerte previo (mástil)
            for i in range(10, len(data) - 10):
                # Verificar movimiento alcista fuerte
                price_change = (closes[i] - closes[i-10]) / closes[i-10]
                
                if abs(price_change) > 0.05:  # Movimiento > 5%
                    # Analizar consolidación posterior
                    consolidation_data = data.iloc[i:i+10]
                    
                    if len(consolidation_data) >= 8:
                        cons_highs = consolidation_data['high'].values
                        cons_lows = consolidation_data['low'].values
                        
                        # Verificar que la consolidación sea estrecha
                        range_ratio = (np.max(cons_highs) - np.min(cons_lows)) / closes[i]
                        
                        if range_ratio < 0.03:  # Consolidación estrecha
                            # Determinar dirección de la bandera
                            flag_slope, _, r_value, _, _ = linregress(
                                range(len(consolidation_data)), 
                                consolidation_data['close'].values
                            )
                            
                            if abs(r_value) > 0.5:  # Tendencia clara en la bandera
                                if price_change > 0:  # Movimiento alcista previo
                                    if flag_slope < 0:  # Bandera bajista (continuación alcista)
                                        pattern_type = PatternType.FLAG_BULLISH
                                        target_price = closes[i] + abs(closes[i] - closes[i-10])
                                        stop_loss = np.min(cons_lows) * 0.99
                                    else:
                                        pattern_type = None
                                        target_price = None
                                        stop_loss = None
                                else:  # Movimiento bajista previo
                                    if flag_slope > 0:  # Bandera alcista (continuación bajista)
                                        pattern_type = PatternType.FLAG_BEARISH
                                        target_price = closes[i] - abs(closes[i] - closes[i-10])
                                        stop_loss = np.max(cons_highs) * 1.01
                                    else:
                                        pattern_type = None
                                        target_price = None
                                        stop_loss = None
                                
                                if pattern_type is not None:
                                    confidence = min(0.8, abs(r_value) * (1 - range_ratio * 10))
                                    
                                    if confidence > 0.6:
                                        pattern = TechnicalPattern(
                                            pattern_type=pattern_type,
                                            confidence=confidence,
                                            start_index=i-10,
                                            end_index=i+10,
                                            key_levels=[closes[i-10], closes[i], np.mean(cons_highs), np.mean(cons_lows)],
                                            target_price=target_price,
                                            stop_loss=stop_loss,
                                            timeframe_strength="short",
                                            description=f"Bandera {pattern_type.value} tras movimiento de {price_change*100:.1f}%"
                                        )
                                        patterns.append(pattern)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error detectando banderas: {e}")
        
        return patterns
    
    def _detect_cup_and_handle(self, data: pd.DataFrame) -> List[TechnicalPattern]:
        """
        Detecta patrones de taza y asa
        """
        patterns = []
        
        try:
            if len(data) < 50:
                return patterns
            
            closes = data['close'].values
            highs = data['high'].values
            lows = data['low'].values
            
            # Buscar formación de taza (U invertida)
            for i in range(30, len(data) - 20):
                # Verificar que hay un máximo al inicio
                left_peak = np.max(highs[i-30:i-20])
                left_peak_idx = np.argmax(highs[i-30:i-20]) + i - 30
                
                # Buscar mínimo en el medio (fondo de la taza)
                cup_bottom = np.min(lows[i-20:i])
                cup_bottom_idx = np.argmin(lows[i-20:i]) + i - 20
                
                # Verificar recuperación hacia el nivel inicial
                right_recovery = np.max(highs[i:i+15]) if i+15 < len(highs) else np.max(highs[i:])
                
                # Criterios para taza válida
                cup_depth = (left_peak - cup_bottom) / left_peak
                recovery_ratio = right_recovery / left_peak
                
                if (0.1 < cup_depth < 0.5 and  # Profundidad razonable
                    recovery_ratio > 0.9 and   # Buena recuperación
                    i - left_peak_idx > 15):   # Tiempo suficiente
                    
                    # Buscar asa (pequeña consolidación)
                    if i + 10 < len(data):
                        handle_data = highs[i:i+10]
                        handle_high = np.max(handle_data)
                        handle_low = np.min(lows[i:i+10])
                        
                        handle_depth = (handle_high - handle_low) / handle_high
                        
                        if handle_depth < 0.15:  # Asa poco profunda
                            confidence = min(0.85, (1 - cup_depth) * recovery_ratio * (1 - handle_depth))
                            
                            if confidence > 0.6:
                                target_price = left_peak + (left_peak - cup_bottom) * 0.618
                                
                                pattern = TechnicalPattern(
                                    pattern_type=PatternType.CUP_AND_HANDLE,
                                    confidence=confidence,
                                    start_index=left_peak_idx,
                                    end_index=i+10,
                                    key_levels=[left_peak, cup_bottom, handle_high, handle_low],
                                    target_price=target_price,
                                    stop_loss=handle_low * 0.95,
                                    timeframe_strength="strong",
                                    description=f"Taza y asa con profundidad {cup_depth*100:.1f}%"
                                )
                                patterns.append(pattern)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error detectando taza y asa: {e}")
        
        return patterns
    
    def analyze_elliott_waves(self, symbol: str, data: pd.DataFrame) -> List[WaveAnalysis]:
        """
        Análisis básico de ondas de Elliott
        """
        waves = []
        
        try:
            if len(data) < 50:
                return waves
            
            closes = data['close'].values
            highs = data['high'].values
            lows = data['low'].values
            
            # Identificar puntos de giro significativos
            peaks, _ = signal.find_peaks(highs, distance=5, prominence=np.std(highs) * 0.3)
            valleys, _ = signal.find_peaks(-lows, distance=5, prominence=np.std(lows) * 0.3)
            
            # Combinar y ordenar puntos de giro
            turning_points = []
            for peak in peaks:
                turning_points.append((peak, highs[peak], 'peak'))
            for valley in valleys:
                turning_points.append((valley, lows[valley], 'valley'))
            
            turning_points.sort(key=lambda x: x[0])
            
            if len(turning_points) >= 5:
                # Buscar secuencias de 5 ondas (patrón impulso)
                for i in range(len(turning_points) - 4):
                    sequence = turning_points[i:i+5]
                    
                    # Verificar alternancia pico-valle
                    types = [point[2] for point in sequence]
                    if (types == ['valley', 'peak', 'valley', 'peak', 'valley'] or
                        types == ['peak', 'valley', 'peak', 'valley', 'peak']):
                        
                        # Analizar proporciones de Fibonacci
                        prices = [point[1] for point in sequence]
                        
                        if types[0] == 'valley':  # Secuencia alcista
                            wave_1 = prices[1] - prices[0]
                            wave_2 = prices[1] - prices[2]
                            wave_3 = prices[3] - prices[2]
                            wave_4 = prices[3] - prices[4]
                            
                            # Verificar reglas de Elliott
                            if (wave_3 > wave_1 and  # Onda 3 no es la más corta
                                wave_2 / wave_1 < 1.0 and  # Onda 2 no retrocede más del 100%
                                wave_4 / wave_3 < 0.618):  # Onda 4 retrocede menos que onda 2
                                
                                # Calcular confianza basada en proporciones de Fibonacci
                                fib_score = 0
                                if 0.5 <= wave_2 / wave_1 <= 0.618:
                                    fib_score += 0.3
                                if 1.618 <= wave_3 / wave_1 <= 2.618:
                                    fib_score += 0.4
                                if 0.236 <= wave_4 / wave_3 <= 0.5:
                                    fib_score += 0.3
                                
                                if fib_score > 0.5:
                                    # Proyección de onda 5
                                    wave_5_target = prices[4] + wave_1 * 0.618
                                    
                                    wave = WaveAnalysis(
                                        wave_type=WaveType.IMPULSE_5,
                                        wave_degree="minor",
                                        start_price=prices[0],
                                        end_price=prices[4],
                                        retracement_level=wave_4 / wave_3,
                                        projection_target=wave_5_target,
                                        confidence=fib_score
                                    )
                                    waves.append(wave)
            
            # Guardar en historial
            if symbol not in self.waves_history:
                self.waves_history[symbol] = []
            
            timestamp = datetime.now()
            for wave in waves:
                self.waves_history[symbol].append({
                    'timestamp': timestamp,
                    'wave': wave
                })
            
            self.logger.info(f"🌊 Detectadas {len(waves)} ondas de Elliott para {symbol}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error analizando ondas de Elliott: {e}")
        
        return waves
    
    def generate_technical_signal(self, symbol: str, data: pd.DataFrame) -> TechnicalSignal:
        """
        Genera señal técnica basada en análisis completo
        """
        try:
            patterns = self.analyze_patterns(symbol, data)
            waves = self.analyze_elliott_waves(symbol, data)
            
            # Calcular indicadores adicionales
            closes = data['close'].values
            current_price = closes[-1]
            
            # RSI
            rsi = self._calculate_rsi(closes)
            
            # MACD
            macd_line, signal_line = self._calculate_macd(closes)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes)
            
            # Confluencia de indicadores
            confluence_score = 0
            signal_strength = 0
            signal_type = "hold"
            
            # Análisis de patrones
            bullish_patterns = [p for p in patterns if p.pattern_type in [
                PatternType.DOUBLE_BOTTOM, PatternType.TRIANGLE_ASCENDING,
                PatternType.WEDGE_FALLING, PatternType.FLAG_BULLISH,
                PatternType.CUP_AND_HANDLE, PatternType.INVERSE_HEAD_AND_SHOULDERS
            ]]
            
            bearish_patterns = [p for p in patterns if p.pattern_type in [
                PatternType.DOUBLE_TOP, PatternType.TRIANGLE_DESCENDING,
                PatternType.WEDGE_RISING, PatternType.FLAG_BEARISH,
                PatternType.HEAD_AND_SHOULDERS
            ]]
            
            # Scoring basado en patrones
            if bullish_patterns:
                pattern_score = sum(p.confidence for p in bullish_patterns) / len(bullish_patterns)
                signal_strength += pattern_score * 0.4
                confluence_score += 1
            
            if bearish_patterns:
                pattern_score = sum(p.confidence for p in bearish_patterns) / len(bearish_patterns)
                signal_strength -= pattern_score * 0.4
                confluence_score += 1
            
            # Scoring basado en indicadores
            if rsi < 30:
                signal_strength += 0.3
                confluence_score += 1
            elif rsi > 70:
                signal_strength -= 0.3
                confluence_score += 1
            
            if macd_line > signal_line:
                signal_strength += 0.2
                confluence_score += 1
            else:
                signal_strength -= 0.2
                confluence_score += 1
            
            if current_price < bb_lower:
                signal_strength += 0.2
                confluence_score += 1
            elif current_price > bb_upper:
                signal_strength -= 0.2
                confluence_score += 1
            
            # Determinar tipo de señal
            if signal_strength > 0.5:
                signal_type = "strong_buy"
            elif signal_strength > 0.2:
                signal_type = "buy"
            elif signal_strength < -0.5:
                signal_type = "strong_sell"
            elif signal_strength < -0.2:
                signal_type = "sell"
            
            # Calcular objetivos y stop loss
            target_price = None
            stop_loss = None
            
            if bullish_patterns:
                best_pattern = max(bullish_patterns, key=lambda p: p.confidence)
                target_price = best_pattern.target_price
                stop_loss = best_pattern.stop_loss
            elif bearish_patterns:
                best_pattern = max(bearish_patterns, key=lambda p: p.confidence)
                target_price = best_pattern.target_price
                stop_loss = best_pattern.stop_loss
            
            confidence = min(0.95, abs(signal_strength) * (confluence_score / 5))
            
            technical_signal = TechnicalSignal(
                signal_type=signal_type,
                strength=abs(signal_strength),
                confidence=confidence,
                entry_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                timeframe="medium",
                indicators_confluence=confluence_score,
                pattern_support=len(patterns) > 0
            )
            
            self.logger.info(f"📈 Señal técnica para {symbol}: {signal_type} "
                           f"(fuerza: {signal_strength:.3f}, confluencia: {confluence_score})")
            
            return technical_signal
            
        except Exception as e:
            self.logger.error(f"❌ Error generando señal técnica para {symbol}: {e}")
            return TechnicalSignal(
                signal_type="hold",
                strength=0.0,
                confidence=0.0,
                entry_price=data['close'].iloc[-1],
                target_price=None,
                stop_loss=None,
                timeframe="medium",
                indicators_confluence=0,
                pattern_support=False
            )
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calcula RSI"""
        if len(prices) < period + 1:
            return 50.0
        
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
    
    def _calculate_macd(self, prices: np.ndarray) -> Tuple[float, float]:
        """Calcula MACD"""
        if len(prices) < 26:
            return 0.0, 0.0
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        macd_line = ema_12 - ema_26
        signal_line = self._calculate_ema(np.array([macd_line]), 9)
        
        return macd_line, signal_line
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calcula EMA"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20, std_dev: int = 2) -> Tuple[float, float, float]:
        """Calcula Bandas de Bollinger"""
        if len(prices) < period:
            mean_price = np.mean(prices)
            return mean_price, mean_price, mean_price
        
        recent_prices = prices[-period:]
        middle = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def get_statistics(self) -> Dict:
        """
        Obtiene estadísticas del analizador técnico
        """
        total_symbols = len(self.patterns_history)
        total_patterns = sum(len(history) for history in self.patterns_history.values())
        total_waves = sum(len(history) for history in self.waves_history.values())
        
        pattern_types = {}
        for history in self.patterns_history.values():
            for entry in history:
                pattern_type = entry['pattern'].pattern_type.value
                pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1
        
        return {
            'total_symbols': total_symbols,
            'total_patterns_detected': total_patterns,
            'total_waves_detected': total_waves,
            'pattern_distribution': pattern_types,
            'avg_patterns_per_symbol': total_patterns / max(1, total_symbols),
            'supported_patterns': len(PatternType),
            'supported_wave_types': len(WaveType)
        }

# Función de prueba
def test_advanced_technical_analyzer():
    """
    Función de prueba para el analizador técnico avanzado
    """
    print("🧪 Iniciando pruebas del Analizador Técnico Avanzado...")
    
    # Crear analizador
    analyzer = AdvancedTechnicalAnalyzer()
    
    # Generar datos de prueba con patrones
    np.random.seed(42)
    periods = 200
    
    # Crear datos con tendencia y patrones
    base_price = 50000
    trend = np.linspace(0, 5000, periods)
    noise = np.random.normal(0, 500, periods)
    
    # Añadir patrón de doble techo
    double_top = np.zeros(periods)
    double_top[50:70] = 2000 * np.sin(np.linspace(0, np.pi, 20))
    double_top[120:140] = 1800 * np.sin(np.linspace(0, np.pi, 20))
    
    prices = base_price + trend + noise + double_top
    
    # Crear DataFrame
    test_data = pd.DataFrame({
        'timestamp': pd.date_range(start='2025-01-01', periods=periods, freq='1H'),
        'open': prices + np.random.normal(0, 100, periods),
        'high': prices + np.abs(np.random.normal(200, 100, periods)),
        'low': prices - np.abs(np.random.normal(200, 100, periods)),
        'close': prices,
        'volume': np.random.uniform(1000, 10000, periods)
    })
    
    # Probar análisis de patrones
    symbols = ['BTCUSDT', 'ETHUSDT']
    
    for symbol in symbols:
        print(f"\n📊 Analizando patrones técnicos para {symbol}...")
        
        # Detectar patrones
        patterns = analyzer.analyze_patterns(symbol, test_data)
        print(f"  Patrones detectados: {len(patterns)}")
        
        for pattern in patterns:
            print(f"    - {pattern.pattern_type.value}: confianza {pattern.confidence:.3f}")
            if pattern.target_price:
                print(f"      Objetivo: {pattern.target_price:.2f}")
        
        # Analizar ondas de Elliott
        waves = analyzer.analyze_elliott_waves(symbol, test_data)
        print(f"  Ondas de Elliott detectadas: {len(waves)}")
        
        for wave in waves:
            print(f"    - {wave.wave_type.value}: confianza {wave.confidence:.3f}")
        
        # Generar señal técnica
        signal = analyzer.generate_technical_signal(symbol, test_data)
        print(f"  Señal técnica: {signal.signal_type}")
        print(f"    Fuerza: {signal.strength:.3f}")
        print(f"    Confianza: {signal.confidence:.3f}")
        print(f"    Confluencia de indicadores: {signal.indicators_confluence}")
        print(f"    Soporte de patrones: {signal.pattern_support}")
    
    # Mostrar estadísticas
    stats = analyzer.get_statistics()
    print(f"\n📈 Estadísticas del Analizador Técnico:")
    print(f"  Símbolos analizados: {stats['total_symbols']}")
    print(f"  Patrones detectados: {stats['total_patterns_detected']}")
    print(f"  Ondas detectadas: {stats['total_waves_detected']}")
    print(f"  Distribución de patrones: {stats['pattern_distribution']}")
    print(f"  Patrones soportados: {stats['supported_patterns']}")
    
    print("\n✅ Pruebas del Analizador Técnico Avanzado completadas")

if __name__ == "__main__":
    test_advanced_technical_analyzer()