#!/usr/bin/env python3
"""
Sistema de Análisis Continuo de Patrones de Rompimiento MEJORADO
Integración de mejoras basadas en análisis de datos:
- Filtros de mercado zombie
- Análisis híbrido OpenAI + Grok
- Umbrales de confianza dinámicos
- Alertas de cambio de régimen
"""

import time
import os
import sys
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np
from colorama import init, Fore, Back, Style
import json
import io
from contextlib import redirect_stdout
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Variables de entorno cargadas desde .env")
except ImportError:
    logger.warning("⚠️ python-dotenv no disponible, usando variables de entorno del sistema")

# Inicializar colorama para Windows
init(autoreset=True)

# Importar módulos de IA
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI no disponible")

# Configuración de APIs de IA
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GROK_API_KEY = os.getenv('GROK_API_KEY')
GROK_BASE_URL = os.getenv('GROK_BASE_URL', 'https://api.x.ai/v1')

@dataclass
class MarketRegime:
    """Clase para representar el régimen de mercado"""
    name: str
    confidence_threshold: float
    volume_threshold: float
    pattern_count_threshold: int
    description: str

class MarketRegimeType(Enum):
    """Tipos de régimen de mercado"""
    ZOMBIE = MarketRegime("ZOMBIE", 0.0, 0.8, 0, "Mercado sin actividad significativa")
    LOW_ACTIVITY = MarketRegime("BAJA_ACTIVIDAD", 15.0, 1.0, 1, "Actividad limitada")
    NORMAL = MarketRegime("NORMAL", 30.0, 1.2, 2, "Actividad normal del mercado")
    HIGH_ACTIVITY = MarketRegime("ALTA_ACTIVIDAD", 50.0, 1.5, 3, "Alta actividad y oportunidades")
    BREAKOUT = MarketRegime("ROMPIMIENTO", 70.0, 2.0, 4, "Condiciones de rompimiento")

@dataclass
class ZombieMarketMetrics:
    """Métricas para detectar mercado zombie"""
    consecutive_zero_patterns: int = 0
    avg_confidence_last_10: float = 0.0
    avg_volume_last_10: float = 0.0
    time_since_last_pattern: int = 0
    is_zombie: bool = False

class AnalisisContinuoPatronesMejorado:
    def __init__(self):
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        self.base_url = 'https://api.binance.com/api/v3'
        self.refresh_interval = 60  # 1 minuto
        self.iteration_count = 0
        self.log_file = "ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO (1 minuto).txt"
        
        # Nuevas funcionalidades
        self.market_history = []  # Historial de análisis para detectar regímenes
        self.zombie_metrics = ZombieMarketMetrics()
        self.current_regime = MarketRegimeType.NORMAL
        self.regime_change_alerts = []
        
        # 🔥 NUEVO: Sistema de boost temporal
        self.boost_mode = False
        self.boost_start_time = None
        self.boost_duration = 300  # 5 minutos en segundos
        
        # Umbrales dinámicos
        self.dynamic_thresholds = {
            'confidence_min': 20.0,
            'volume_min': 1.2,
            'pattern_significance': 0.5
        }
        
        # Inicializar clientes de IA
        self.openai_client = None
        self.grok_client = None
        self.ai_enabled = False
        self._initialize_ai_clients()
        
        self.ensure_log_file()
        
        # 🔥 ACTIVAR BOOST INMEDIATAMENTE para resolver el problema del 0%
        self.activate_boost_mode("Inicio del sistema - Resolver problema de 0% confianza")
    
    def ensure_log_file(self):
        """Asegurar que el archivo de log existe y crear encabezado si es nuevo"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("    ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO MEJORADO    \n")
                f.write("="*80 + "\n")
                f.write(f"Archivo creado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("Mejoras: Filtros Zombie + Análisis Híbrido + Umbrales Dinámicos + Alertas de Régimen\n")
                f.write("="*80 + "\n\n")
    
    def _initialize_ai_clients(self):
        """Inicializar clientes de IA (OpenAI y Grok xAI)"""
        try:
            # Inicializar cliente OpenAI
            if OPENAI_AVAILABLE and OPENAI_API_KEY:
                self.openai_client = OpenAI(
                    api_key=OPENAI_API_KEY,
                    base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
                )
                logger.info("✅ Cliente OpenAI inicializado exitosamente")
            else:
                logger.warning("⚠️ OpenAI no disponible - falta API key o librería")
            
            # Inicializar cliente Grok xAI
            if OPENAI_AVAILABLE and GROK_API_KEY:
                self.grok_client = OpenAI(
                    api_key=GROK_API_KEY,
                    base_url=GROK_BASE_URL
                )
                logger.info("✅ Cliente Grok xAI inicializado exitosamente")
            else:
                logger.warning("⚠️ Grok xAI no disponible - falta API key")
            
            # Verificar si al menos uno está disponible
            self.ai_enabled = (self.openai_client is not None) or (self.grok_client is not None)
            
            if self.ai_enabled:
                logger.info("🤖 Sistema de IA habilitado")
            else:
                logger.warning("⚠️ Sistema funcionando sin IA - solo análisis técnico")
                
        except Exception as e:
            logger.error(f"❌ Error inicializando clientes de IA: {e}")
            self.ai_enabled = False

    def detect_zombie_market(self, all_analysis: Dict[str, Any]) -> ZombieMarketMetrics:
        """
        🧟 FILTRO DE MERCADO ZOMBIE
        Detecta períodos de baja actividad basado en análisis histórico
        """
        # Calcular métricas actuales
        total_patterns = sum(len(analysis['patterns']) for analysis in all_analysis.values())
        confidences = [analysis['confidence'] for analysis in all_analysis.values()]
        volumes = [analysis['volume_ratio'] for analysis in all_analysis.values()]
        
        avg_confidence = np.mean(confidences) if confidences else 0
        avg_volume = np.mean(volumes) if volumes else 0
        
        # Actualizar métricas zombie
        if total_patterns == 0:
            self.zombie_metrics.consecutive_zero_patterns += 1
            self.zombie_metrics.time_since_last_pattern += 1
        else:
            self.zombie_metrics.consecutive_zero_patterns = 0
            self.zombie_metrics.time_since_last_pattern = 0
        
        # Mantener historial de últimas 10 iteraciones
        if len(self.market_history) >= 10:
            self.market_history.pop(0)
        
        self.market_history.append({
            'timestamp': datetime.now(),
            'confidence': avg_confidence,
            'volume': avg_volume,
            'patterns': total_patterns
        })
        
        # Calcular promedios de últimas 10 iteraciones
        if len(self.market_history) >= 5:  # Mínimo 5 iteraciones para análisis
            recent_confidences = [h['confidence'] for h in self.market_history[-10:]]
            recent_volumes = [h['volume'] for h in self.market_history[-10:]]
            
            self.zombie_metrics.avg_confidence_last_10 = np.mean(recent_confidences)
            self.zombie_metrics.avg_volume_last_10 = np.mean(recent_volumes)
        
        # Determinar si es mercado zombie
        zombie_conditions = [
            self.zombie_metrics.consecutive_zero_patterns >= 5,  # 5+ iteraciones sin patrones
            self.zombie_metrics.avg_confidence_last_10 < 5.0,   # Confianza promedio muy baja
            self.zombie_metrics.avg_volume_last_10 < 0.8,       # Volumen consistentemente bajo
            self.zombie_metrics.time_since_last_pattern >= 10   # 10+ minutos sin patrones
        ]
        
        self.zombie_metrics.is_zombie = sum(zombie_conditions) >= 2  # Al menos 2 condiciones
        
        return self.zombie_metrics

    def update_dynamic_thresholds(self, zombie_metrics: ZombieMarketMetrics):
        """
        🎯 UMBRALES DINÁMICOS MEJORADOS
        Ajusta umbrales basado en condiciones de mercado con niveles graduales
        """
        # 🔥 MEJORA #1: Umbrales más agresivos para detectar actividad
        if zombie_metrics.is_zombie:
            # En mercado zombie, ser MUCHO más permisivo
            self.dynamic_thresholds['confidence_min'] = 5.0  # Reducido de 10.0
            self.dynamic_thresholds['volume_min'] = 0.6      # Reducido de 0.8
            self.dynamic_thresholds['pattern_significance'] = 0.2  # Reducido de 0.3
        elif zombie_metrics.consecutive_zero_patterns > 20:
            # 🔥 NUEVO: Modo ultra-permisivo después de muchos ceros
            self.dynamic_thresholds['confidence_min'] = 3.0
            self.dynamic_thresholds['volume_min'] = 0.5
            self.dynamic_thresholds['pattern_significance'] = 0.15
        elif zombie_metrics.avg_confidence_last_10 < 5.0:
            # 🔥 NUEVO: Modo de recuperación gradual
            self.dynamic_thresholds['confidence_min'] = 8.0
            self.dynamic_thresholds['volume_min'] = 0.7
            self.dynamic_thresholds['pattern_significance'] = 0.25
        elif zombie_metrics.avg_confidence_last_10 > 40:
            # En mercado activo, ser más estricto
            self.dynamic_thresholds['confidence_min'] = 35.0
            self.dynamic_thresholds['volume_min'] = 1.5
            self.dynamic_thresholds['pattern_significance'] = 0.7
        else:
            # 🔥 MEJORA: Condiciones normales más permisivas
            self.dynamic_thresholds['confidence_min'] = 15.0  # Reducido de 20.0
            self.dynamic_thresholds['volume_min'] = 1.0       # Reducido de 1.2
            self.dynamic_thresholds['pattern_significance'] = 0.4  # Reducido de 0.5
        
        # 🔥 NUEVO: Sistema de boost temporal
        if hasattr(self, 'boost_mode') and self.boost_mode:
            self.dynamic_thresholds['confidence_min'] *= 0.7
            self.dynamic_thresholds['volume_min'] *= 0.8

    def detect_regime_change(self, all_analysis: Dict[str, Any], zombie_metrics: ZombieMarketMetrics) -> Optional[MarketRegimeType]:
        """
        🚨 DETECTOR DE CAMBIO DE RÉGIMEN
        Identifica cambios significativos en el régimen de mercado
        """
        # Calcular métricas actuales
        total_patterns = sum(len(analysis['patterns']) for analysis in all_analysis.values())
        confidences = [analysis['confidence'] for analysis in all_analysis.values()]
        volumes = [analysis['volume_ratio'] for analysis in all_analysis.values()]
        
        avg_confidence = np.mean(confidences) if confidences else 0
        avg_volume = np.mean(volumes) if volumes else 0
        
        # Determinar nuevo régimen
        new_regime = self.current_regime
        
        if zombie_metrics.is_zombie:
            new_regime = MarketRegimeType.ZOMBIE
        elif avg_confidence >= 70 and avg_volume >= 2.0 and total_patterns >= 4:
            new_regime = MarketRegimeType.BREAKOUT
        elif avg_confidence >= 50 and avg_volume >= 1.5 and total_patterns >= 3:
            new_regime = MarketRegimeType.HIGH_ACTIVITY
        elif avg_confidence >= 30 and avg_volume >= 1.2 and total_patterns >= 2:
            new_regime = MarketRegimeType.NORMAL
        elif avg_confidence >= 15 and total_patterns >= 1:
            new_regime = MarketRegimeType.LOW_ACTIVITY
        else:
            new_regime = MarketRegimeType.ZOMBIE
        
        # Detectar cambio de régimen
        if new_regime != self.current_regime:
            change_alert = {
                'timestamp': datetime.now(),
                'from_regime': self.current_regime.value.name,
                'to_regime': new_regime.value.name,
                'confidence': avg_confidence,
                'volume': avg_volume,
                'patterns': total_patterns
            }
            
            self.regime_change_alerts.append(change_alert)
            
            # Mantener solo últimas 10 alertas
            if len(self.regime_change_alerts) > 10:
                self.regime_change_alerts.pop(0)
            
            self.current_regime = new_regime
            return new_regime
        
        return None

    def get_klines(self, symbol, interval='1m', limit=100):
        """Obtener datos de velas de Binance"""
        try:
            url = f"{self.base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos de datos
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error obteniendo datos para {symbol}: {e}")
            return None

    def _detect_lateral_consolidation(self, df, current_price, resistance, support):
        """
        🔍 DETECCIÓN OPTIMIZADA DE CONSOLIDACIÓN LATERAL
        Detecta patrones de consolidación, rangos laterales y triángulos
        """
        try:
            # Análisis de últimas 20 velas para patrones de corto plazo
            recent_data = df.tail(20)
            
            # 1. ANÁLISIS DE RANGO LATERAL
            price_range = (resistance - support) / current_price
            range_position = (current_price - support) / (resistance - support) if resistance != support else 0.5
            
            # 2. ANÁLISIS DE VOLATILIDAD
            recent_closes = recent_data['close'].values
            price_volatility = np.std(recent_closes) / np.mean(recent_closes)
            
            # 3. ANÁLISIS DE MOMENTUM
            price_changes = np.diff(recent_closes)
            momentum_strength = np.mean(np.abs(price_changes)) / current_price
            
            # 4. ANÁLISIS DE VELAS CONSECUTIVAS
            consecutive_small_moves = 0
            for i in range(1, len(recent_closes)):
                change_pct = abs(recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1]
                if change_pct < 0.003:  # Movimientos menores a 0.3%
                    consecutive_small_moves += 1
            
            # 5. ANÁLISIS DE TENDENCIA DIRECCIONAL
            recent_highs = recent_data['high'].values
            recent_lows = recent_data['low'].values
            
            # Detectar si hay sesgo direccional
            upper_touches = sum(1 for high in recent_highs[-10:] if high > current_price * 1.002)
            lower_touches = sum(1 for low in recent_lows[-10:] if low < current_price * 0.998)
            
            # LÓGICA DE DETECCIÓN
            detected = False
            pattern_type = ""
            confidence = 0
            
            # CONSOLIDACIÓN LATERAL CLÁSICA
            if (0.005 < price_range < 0.035 and  # Rango entre 0.5% y 3.5%
                price_volatility < 0.015 and     # Baja volatilidad
                consecutive_small_moves >= 8):   # Muchos movimientos pequeños
                
                detected = True
                pattern_type = "LATERAL_CONSOLIDACION"
                confidence = 30
                
                # Bonus por posición en el rango
                if 0.3 <= range_position <= 0.7:  # En el centro del rango
                    confidence += 10
                
            # CONSOLIDACIÓN CON SESGO BAJISTA (como en tu captura)
            elif (0.005 < price_range < 0.04 and
                  momentum_strength < 0.008 and
                  upper_touches > lower_touches and
                  range_position > 0.6):  # En la parte alta del rango
                
                detected = True
                pattern_type = "CONSOLIDACION_SESGO_BAJISTA"
                confidence = 35
                
            # CONSOLIDACIÓN CON SESGO ALCISTA
            elif (0.005 < price_range < 0.04 and
                  momentum_strength < 0.008 and
                  lower_touches > upper_touches and
                  range_position < 0.4):  # En la parte baja del rango
                
                detected = True
                pattern_type = "CONSOLIDACION_SESGO_ALCISTA"
                confidence = 35
                
            # RANGO ESTRECHO (Posible breakout inminente)
            elif (price_range < 0.015 and  # Rango muy estrecho < 1.5%
                  consecutive_small_moves >= 12):
                
                detected = True
                pattern_type = "RANGO_ESTRECHO_BREAKOUT"
                confidence = 25
                
            # TRIÁNGULO DESCENDENTE
            elif (price_range > 0.02 and
                  upper_touches >= 3 and  # Múltiples toques de resistencia
                  momentum_strength < 0.01):
                
                detected = True
                pattern_type = "TRIANGULO_DESCENDENTE"
                confidence = 28
            
            return {
                'detected': detected,
                'pattern_type': pattern_type,
                'confidence': confidence,
                'details': {
                    'price_range_pct': price_range * 100,
                    'range_position': range_position,
                    'volatility': price_volatility,
                    'momentum_strength': momentum_strength,
                    'consecutive_small_moves': consecutive_small_moves,
                    'upper_touches': upper_touches,
                    'lower_touches': lower_touches
                }
            }
            
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Error en detección de consolidación: {e}")
            return {'detected': False, 'pattern_type': '', 'confidence': 0, 'details': {}}

    def calculate_indicators(self, df):
        """Calcular indicadores técnicos"""
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Medias móviles
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # Volume MA
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            
            return df
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error calculando indicadores: {e}")
            return None

    def detect_patterns(self, df, symbol):
        """
        🔍 DETECCIÓN DE PATRONES MEJORADA
        Utiliza umbrales dinámicos y filtros de calidad + DETECCIÓN OPTIMIZADA DE CONSOLIDACIONES
        """
        try:
            if len(df) < 50:
                return {
                    'patterns': [],
                    'confidence': 0,
                    'current_price': 0,
                    'resistance': 0,
                    'support': 0,
                    'rsi': 0,
                    'volume_ratio': 0
                }
            
            latest = df.iloc[-1]
            current_price = float(latest['close'])
            
            # Calcular niveles de soporte y resistencia
            recent_highs = df['high'].rolling(window=20).max()
            recent_lows = df['low'].rolling(window=20).min()
            resistance = float(recent_highs.iloc[-1])
            support = float(recent_lows.iloc[-1])
            
            patterns = []
            confidence_factors = []
            
            # 🆕 DETECCIÓN OPTIMIZADA DE CONSOLIDACIÓN LATERAL
            consolidation_result = self._detect_lateral_consolidation(df, current_price, resistance, support)
            if consolidation_result['detected']:
                patterns.append(consolidation_result['pattern_type'])
                confidence_factors.append(consolidation_result['confidence'])
            
            # 1. RSI Patterns (con umbrales dinámicos)
            rsi_oversold_threshold = 30 if not self.zombie_metrics.is_zombie else 35
            rsi_overbought_threshold = 70 if not self.zombie_metrics.is_zombie else 65
            
            if latest['rsi'] > rsi_overbought_threshold:
                patterns.append('RSI_Overbought')
                confidence_factors.append(15)
            elif latest['rsi'] < rsi_oversold_threshold:
                patterns.append('RSI_Oversold')
                confidence_factors.append(15)
            
            # 2. Volume Confirmation (con umbrales dinámicos)
            volume_threshold = self.dynamic_thresholds['volume_min']
            if latest['volume'] > latest['volume_ma'] * volume_threshold:
                patterns.append('Volume_Confirmation')
                confidence_factors.append(25)
            
            # 3. Resistance/Support Break
            if current_price > resistance * 1.001:  # 0.1% above resistance
                patterns.append('Resistance_Break')
                confidence_factors.append(35)
            elif current_price < support * 0.999:  # 0.1% below support
                patterns.append('Support_Break')
                confidence_factors.append(35)
            
            # 4. MACD Patterns
            if latest['macd'] > latest['macd_signal'] and df['macd'].iloc[-2] <= df['macd_signal'].iloc[-2]:
                patterns.append('MACD_Bullish_Cross')
                confidence_factors.append(20)
            elif latest['macd'] < latest['macd_signal'] and df['macd'].iloc[-2] >= df['macd_signal'].iloc[-2]:
                patterns.append('MACD_Bearish_Cross')
                confidence_factors.append(20)
            
            # 5. Bollinger Bands
            if current_price > latest['bb_upper']:
                patterns.append('BB_Upper_Break')
                confidence_factors.append(15)
            elif current_price < latest['bb_lower']:
                patterns.append('BB_Lower_Break')
                confidence_factors.append(15)
            
            # Calcular confianza total con filtros de calidad
            base_confidence = min(sum(confidence_factors), 100)
            
            # Aplicar filtros de calidad
            quality_multiplier = 1.0
            
            # Filtro de volumen
            if latest['volume'] < latest['volume_ma'] * 0.5:
                quality_multiplier *= 0.5  # Penalizar volumen muy bajo
            
            # Filtro de volatilidad
            price_range = (df['high'].iloc[-5:].max() - df['low'].iloc[-5:].min()) / current_price
            if price_range < 0.005:  # Menos de 0.5% de rango
                quality_multiplier *= 0.7  # Penalizar baja volatilidad
            
            # Aplicar multiplicador de calidad
            total_confidence = base_confidence * quality_multiplier
            
            # Filtrar patrones por significancia
            if total_confidence < self.dynamic_thresholds['confidence_min']:
                patterns = []
                total_confidence = 0
            
            return {
                'patterns': patterns,
                'confidence': total_confidence,
                'current_price': current_price,
                'resistance': resistance,
                'support': support,
                'rsi': latest['rsi'],
                'volume_ratio': latest['volume'] / latest['volume_ma'] if latest['volume_ma'] > 0 else 1
            }
            
        except Exception as e:
            print(f"{Fore.RED}❌ Error detectando patrones para {symbol}: {e}")
            return {
                'patterns': [],
                'confidence': 0,
                'current_price': 0,
                'resistance': 0,
                'support': 0,
                'rsi': 0,
                'volume_ratio': 0
            }

    def generate_hybrid_ai_analysis(self, market_data: Dict[str, Any]) -> str:
        """
        🤖 ANÁLISIS HÍBRIDO OPENAI + GROK
        Combina las fortalezas de ambos sistemas de IA
        """
        if not self.ai_enabled:
            return "🔧 Análisis de IA no disponible - funcionando con análisis técnico tradicional"
        
        try:
            # Preparar contexto del mercado
            context = self._prepare_market_context(market_data)
            
            openai_analysis = ""
            grok_analysis = ""
            
            # Obtener análisis de OpenAI (estructurado y profesional)
            if self.openai_client:
                try:
                    openai_analysis = self._get_openai_analysis(context)
                except Exception as e:
                    logger.warning(f"Error en análisis OpenAI: {e}")
            
            # Obtener análisis de Grok (práctico y directo)
            if self.grok_client:
                try:
                    grok_analysis = self._get_grok_analysis(context)
                except Exception as e:
                    logger.warning(f"Error en análisis Grok: {e}")
            
            # Combinar análisis
            hybrid_analysis = self._combine_ai_analyses(openai_analysis, grok_analysis, market_data)
            
            return hybrid_analysis
            
        except Exception as e:
            logger.error(f"Error en análisis híbrido: {e}")
            return f"❌ Error en análisis de IA: {e}"

    def _prepare_market_context(self, market_data: Dict[str, Any]) -> str:
        """Preparar contexto del mercado para IA"""
        context_parts = []
        
        # Información del régimen actual
        context_parts.append(f"RÉGIMEN ACTUAL: {self.current_regime.value.name}")
        context_parts.append(f"Descripción: {self.current_regime.value.description}")
        
        # Métricas zombie
        if self.zombie_metrics.is_zombie:
            context_parts.append(f"⚠️ MERCADO ZOMBIE DETECTADO")
            context_parts.append(f"Iteraciones sin patrones: {self.zombie_metrics.consecutive_zero_patterns}")
            context_parts.append(f"Tiempo sin actividad: {self.zombie_metrics.time_since_last_pattern} minutos")
        
        # Umbrales dinámicos actuales
        context_parts.append(f"Umbrales dinámicos:")
        context_parts.append(f"  - Confianza mínima: {self.dynamic_thresholds['confidence_min']:.1f}%")
        context_parts.append(f"  - Volumen mínimo: {self.dynamic_thresholds['volume_min']:.1f}x")
        
        # Datos de mercado
        context_parts.append("\nDatos de mercado:")
        for symbol, data in market_data.items():
            if symbol != 'market_summary':
                context_parts.append(f"{symbol}: ${data['price']:.4f}, RSI: {data['rsi']:.1f}, Vol: {data['volume_ratio']:.2f}x, Conf: {data['confidence']:.1f}%")
        
        return "\n".join(context_parts)

    def _get_openai_analysis(self, context: str) -> str:
        """Obtener análisis estructurado de OpenAI"""
        prompt = f"""
        Como analista técnico profesional, proporciona un análisis estructurado del mercado:

        {context}

        Proporciona un análisis en 5 puntos específicos:
        1. Interpretación profesional de los patrones técnicos
        2. Evaluación del sentimiento del mercado
        3. Análisis de riesgo/recompensa
        4. Perspectivas para los próximos 60 minutos
        5. Recomendaciones de gestión de riesgo

        Mantén un tono profesional y educativo.
        """
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )
        
        return response.choices[0].message.content

    def _get_grok_analysis(self, context: str) -> str:
        """Obtener análisis práctico de Grok"""
        if not self.grok_client:
            return "Grok no disponible"
            
        prompt = f"""
        Como trader experimentado, da tu análisis directo y práctico:

        {context}

        Proporciona:
        - Análisis inmediato de la situación
        - Oportunidades específicas que ves
        - Riesgos principales a evitar
        - Predicción para próximos 60 minutos
        - Recomendación de acción concreta

        Usa tu estilo directo y sin rodeos. Si el mercado está muerto, dilo claramente.
        """
        
        # Intentar con diferentes modelos de Grok (del más avanzado al más básico)
        models_to_try = ["grok-4-fast-reasoning", "grok-3", "grok-2"]
        
        for model in models_to_try:
            try:
                response = self.grok_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=400,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"Error con {model}: {e}")
                if model == models_to_try[-1]:  # Último modelo
                    return f"Análisis Grok temporalmente no disponible. Último error: {str(e)[:100]}"
                continue
        
        return "Análisis Grok no disponible"

    def _combine_ai_analyses(self, openai_analysis: str, grok_analysis: str, market_data: Dict[str, Any]) -> str:
        """Combinar análisis de ambas IAs"""
        combined = []
        
        if openai_analysis and grok_analysis:
            combined.append("🤖 ANÁLISIS HÍBRIDO OPENAI + GROK")
            combined.append("="*50)
            combined.append("\n📊 ANÁLISIS PROFESIONAL (OpenAI):")
            combined.append(openai_analysis)
            combined.append("\n🎯 PERSPECTIVA PRÁCTICA (Grok):")
            combined.append(grok_analysis)
            
            # Síntesis híbrida
            combined.append("\n🔄 SÍNTESIS HÍBRIDA:")
            if self.zombie_metrics.is_zombie:
                combined.append("• Ambos sistemas confirman: MERCADO EN MODO ZOMBIE")
                combined.append("• Recomendación: Esperar activación o reducir frecuencia de análisis")
            else:
                combined.append("• Combinando análisis estructurado con perspectiva práctica")
                combined.append("• Enfoque balanceado: Técnico + Experiencial")
        
        elif openai_analysis:
            combined.append("🤖 ANÁLISIS OPENAI")
            combined.append("="*30)
            combined.append(openai_analysis)
        
        elif grok_analysis:
            combined.append("🧠 ANÁLISIS GROK xAI")
            combined.append("="*30)
            combined.append(grok_analysis)
        
        else:
            combined.append("🔧 Análisis de IA no disponible")
        
        return "\n".join(combined)

    def clear_screen(self):
        """Limpiar pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        """Imprimir encabezado mejorado"""
        print(f"{Fore.GREEN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.GREEN}{Style.BRIGHT}    SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO MEJORADO    ")
        print(f"{Fore.GREEN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.YELLOW}Iteración: {self.iteration_count} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.YELLOW}Régimen: {self.current_regime.value.name} | Próxima actualización: {self.refresh_interval}s")
        
        # Mostrar estado de filtros
        if self.zombie_metrics.is_zombie:
            print(f"{Fore.RED}🧟 MERCADO ZOMBIE DETECTADO - Filtros activos")
        
        print(f"{Fore.GREEN}{Style.BRIGHT}{'='*80}")

    def print_symbol_analysis(self, symbol, analysis):
        """Imprimir análisis por símbolo con mejoras"""
        confidence = analysis['confidence']
        
        # Color basado en confianza y régimen
        if confidence >= 70:
            color = Fore.GREEN
            level = "ALTA"
        elif confidence >= 50:
            color = Fore.YELLOW
            level = "MEDIA"
        elif confidence >= self.dynamic_thresholds['confidence_min']:
            color = Fore.CYAN
            level = "BAJA"
        else:
            color = Fore.RED
            level = "MUY BAJA"
        
        print(f"\n{color}{Style.BRIGHT}📊 {symbol}")
        print(f"{Fore.WHITE}{'─'*50}")
        print(f"{Fore.WHITE}Precio Actual: ${analysis['current_price']:.4f}")
        print(f"{Fore.WHITE}Resistencia:   ${analysis['resistance']:.4f}")
        print(f"{Fore.WHITE}Soporte:       ${analysis['support']:.4f}")
        print(f"{Fore.WHITE}RSI:           {analysis['rsi']:.1f}")
        print(f"{Fore.WHITE}Vol. Ratio:    {analysis['volume_ratio']:.2f}x")
        print(f"{color}Confianza:     {confidence:.1f}% ({level})")
        
        if analysis['patterns']:
            print(f"{Fore.WHITE}Patrones:")
            for pattern in analysis['patterns']:
                emoji = self.get_pattern_emoji(pattern)
                pattern_name = pattern.replace('_', ' ').title()
                print(f"{Fore.WHITE}  {emoji} {pattern_name}")
        else:
            print(f"{Fore.LIGHTBLACK_EX}Sin patrones detectados")

    def get_pattern_emoji(self, pattern):
        """Obtener emoji para patrón"""
        emoji_map = {
            'RSI_Oversold': '❄️',
            'RSI_Overbought': '🔥',
            'Volume_Confirmation': '📊',
            'Resistance_Break': '🚀',
            'Support_Break': '📉',
            'MACD_Bullish_Cross': '📈',
            'MACD_Bearish_Cross': '📉',
            'BB_Upper_Break': '⬆️',
            'BB_Lower_Break': '⬇️',
            'BB_Breakout_Upper': '🚀',
            'BB_Breakout_Lower': '📉',
            'Lateral_Consolidation': '📦',
            'Bullish_Biased_Consolidation': '📦📈',
            'Bearish_Biased_Consolidation': '📦📉',
            'Narrow_Range_Breakout_Setup': '🎯',
            'Descending_Triangle': '📐'
        }
        return emoji_map.get(pattern, '🔍')

    def print_market_summary(self, all_analysis):
        """Imprimir resumen del mercado mejorado"""
        print(f"\n{Fore.GREEN}{Style.BRIGHT}{'='*80}")
        print(f"{Fore.GREEN}{Style.BRIGHT}                    RESUMEN DEL MERCADO MEJORADO                    ")
        print(f"{Fore.GREEN}{Style.BRIGHT}{'='*80}")
        
        confidences = [analysis['confidence'] for analysis in all_analysis.values()]
        avg_confidence = np.mean(confidences) if confidences else 0
        total_patterns = sum(len(analysis['patterns']) for analysis in all_analysis.values())
        
        # Determinar sentimiento
        high_conf_count = sum(1 for conf in confidences if conf >= 70)
        if high_conf_count >= 3:
            sentiment = "ALCISTA"
            sentiment_color = Fore.GREEN
        elif high_conf_count >= 1:
            sentiment = "NEUTRAL"
            sentiment_color = Fore.YELLOW
        else:
            sentiment = "BAJISTA"
            sentiment_color = Fore.RED
        
        print(f"{sentiment_color}Sentimiento General: {sentiment}")
        print(f"{Fore.WHITE}Confianza Promedio:  {avg_confidence:.1f}%")
        print(f"{Fore.WHITE}Patrones Activos:    {total_patterns}")
        print(f"{Fore.WHITE}Régimen Actual:      {self.current_regime.value.name}")
        
        # Métricas de mercado zombie
        if self.zombie_metrics.is_zombie:
            print(f"{Fore.RED}🧟 Estado Zombie:     ACTIVO")
            print(f"{Fore.RED}Sin patrones por:    {self.zombie_metrics.consecutive_zero_patterns} iteraciones")
        
        # Umbrales dinámicos
        print(f"\n{Fore.CYAN}🎯 UMBRALES DINÁMICOS:")
        print(f"{Fore.WHITE}Confianza mínima:    {self.dynamic_thresholds['confidence_min']:.1f}%")
        print(f"{Fore.WHITE}Volumen mínimo:      {self.dynamic_thresholds['volume_min']:.1f}x")
        
        # Top 3 símbolos
        sorted_symbols = sorted(all_analysis.items(), key=lambda x: x[1]['confidence'], reverse=True)
        print(f"\n{Fore.YELLOW}🏆 TOP 3 SÍMBOLOS POR CONFIANZA:")
        for i, (symbol, analysis) in enumerate(sorted_symbols[:3], 1):
            print(f"{Fore.WHITE}  {i}. {symbol}: {analysis['confidence']:.1f}%")
        
        # Alertas de cambio de régimen
        if self.regime_change_alerts:
            recent_alert = self.regime_change_alerts[-1]
            time_diff = (datetime.now() - recent_alert['timestamp']).total_seconds() / 60
            if time_diff < 5:  # Mostrar si fue en los últimos 5 minutos
                print(f"\n{Fore.MAGENTA}🚨 CAMBIO DE RÉGIMEN RECIENTE:")
                print(f"{Fore.WHITE}  {recent_alert['from_regime']} → {recent_alert['to_regime']}")
                print(f"{Fore.WHITE}  Hace {time_diff:.1f} minutos")

    def save_analysis_to_file(self, analysis_text):
        """Guardar análisis en archivo"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(analysis_text + "\n\n")
        except Exception as e:
            print(f"{Fore.RED}❌ Error guardando análisis: {e}")

    def generate_analysis_text(self, all_analysis):
        """Generar texto completo del análisis mejorado"""
        output = []
        
        # Encabezado
        output.append("="*80)
        output.append("    SICAR - ANÁLISIS CONTINUO DE PATRONES DE ROMPIMIENTO MEJORADO    ")
        output.append("="*80)
        output.append(f"Iteración: {self.iteration_count} | Actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"Régimen: {self.current_regime.value.name} | Próxima actualización en: {self.refresh_interval} segundos")
        
        # Estado de mejoras
        if self.zombie_metrics.is_zombie:
            output.append("🧟 MERCADO ZOMBIE DETECTADO - Filtros activos")
        
        output.append("="*80)
        
        # Análisis por símbolo
        for symbol in self.symbols:
            if symbol in all_analysis:
                analysis = all_analysis[symbol]
                confidence = analysis['confidence']
                
                output.append(f"\n📊 {symbol}")
                output.append("─"*50)
                output.append(f"Precio Actual: ${analysis['current_price']:.4f}")
                output.append(f"Resistencia:   ${analysis['resistance']:.4f}")
                output.append(f"Soporte:       ${analysis['support']:.4f}")
                output.append(f"RSI:           {analysis['rsi']:.1f}")
                output.append(f"Vol. Ratio:    {analysis['volume_ratio']:.2f}x")
                
                confidence_level = "ALTA" if confidence >= 70 else "MEDIA" if confidence >= 50 else "BAJA" if confidence >= self.dynamic_thresholds['confidence_min'] else "MUY BAJA"
                output.append(f"Confianza:     {confidence:.1f}% ({confidence_level})")
                
                if analysis['patterns']:
                    output.append("Patrones:")
                    for pattern in analysis['patterns']:
                        emoji = self.get_pattern_emoji(pattern)
                        pattern_name = pattern.replace('_', ' ').title()
                        output.append(f"  {emoji} {pattern_name}")
                else:
                    output.append("Sin patrones detectados")
        
        # Resumen del mercado mejorado
        output.append("\n" + "="*80)
        output.append("                    RESUMEN DEL MERCADO MEJORADO                    ")
        output.append("="*80)
        
        confidences = [analysis['confidence'] for analysis in all_analysis.values()]
        avg_confidence = np.mean(confidences) if confidences else 0
        total_patterns = sum(len(analysis['patterns']) for analysis in all_analysis.values())
        
        high_conf_count = sum(1 for conf in confidences if conf >= 70)
        if high_conf_count >= 3:
            sentiment = "ALCISTA"
        elif high_conf_count >= 1:
            sentiment = "NEUTRAL"
        else:
            sentiment = "BAJISTA"
        
        output.append(f"Sentimiento General: {sentiment}")
        output.append(f"Confianza Promedio:  {avg_confidence:.1f}%")
        output.append(f"Patrones Activos:    {total_patterns}")
        output.append(f"Régimen Actual:      {self.current_regime.value.name}")
        
        # Métricas zombie
        if self.zombie_metrics.is_zombie:
            output.append(f"🧟 Estado Zombie:     ACTIVO")
            output.append(f"Sin patrones por:    {self.zombie_metrics.consecutive_zero_patterns} iteraciones")
            output.append(f"Tiempo sin actividad: {self.zombie_metrics.time_since_last_pattern} minutos")
        
        # Umbrales dinámicos
        output.append(f"\n🎯 UMBRALES DINÁMICOS:")
        output.append(f"Confianza mínima:    {self.dynamic_thresholds['confidence_min']:.1f}%")
        output.append(f"Volumen mínimo:      {self.dynamic_thresholds['volume_min']:.1f}x")
        output.append(f"Significancia:       {self.dynamic_thresholds['pattern_significance']:.1f}")
        
        # Top 3 símbolos
        sorted_symbols = sorted(all_analysis.items(), key=lambda x: x[1]['confidence'], reverse=True)
        output.append("\n🏆 TOP 3 SÍMBOLOS POR CONFIANZA:")
        for i, (symbol, analysis) in enumerate(sorted_symbols[:3], 1):
            output.append(f"  {i}. {symbol}: {analysis['confidence']:.1f}%")
        
        # Alertas importantes
        alerts = []
        for symbol, analysis in all_analysis.items():
            if analysis['confidence'] >= 75:
                alerts.append(f"{symbol}: Confianza muy alta ({analysis['confidence']:.1f}%)")
            if 'Volume_Confirmation' in analysis['patterns'] and analysis['volume_ratio'] > 2:
                alerts.append(f"{symbol}: Volumen excepcional ({analysis['volume_ratio']:.1f}x)")
        
        if alerts:
            output.append("\n🚨 ALERTAS IMPORTANTES:")
            for alert in alerts:
                output.append(f"  • {alert}")
        
        # Alertas de cambio de régimen
        if self.regime_change_alerts:
            recent_alert = self.regime_change_alerts[-1]
            time_diff = (datetime.now() - recent_alert['timestamp']).total_seconds() / 60
            if time_diff < 10:  # Últimos 10 minutos
                output.append(f"\n🚨 CAMBIO DE RÉGIMEN RECIENTE:")
                output.append(f"  {recent_alert['from_regime']} → {recent_alert['to_regime']}")
                output.append(f"  Hace {time_diff:.1f} minutos")
        
        # Análisis de IA híbrido
        if self.ai_enabled:
            output.append("\n" + "="*80)
            output.append("                    ANÁLISIS INTELIGENTE HÍBRIDO                    ")
            output.append("="*80)
            
            # Preparar datos para IA
            market_data = {}
            for symbol, analysis in all_analysis.items():
                market_data[symbol] = {
                    'price': analysis['current_price'],
                    'resistance': analysis['resistance'],
                    'support': analysis['support'],
                    'rsi': analysis['rsi'],
                    'volume_ratio': analysis['volume_ratio'],
                    'confidence': analysis['confidence'],
                    'patterns': analysis['patterns']
                }
            
            market_data['market_summary'] = {
                'sentiment': sentiment,
                'avg_confidence': avg_confidence,
                'active_patterns': total_patterns,
                'top_symbols': [symbol for symbol, _ in sorted_symbols[:3]],
                'regime': self.current_regime.value.name,
                'is_zombie': self.zombie_metrics.is_zombie
            }
            
            # Generar análisis híbrido
            ai_analysis = self.generate_hybrid_ai_analysis(market_data)
            output.append(ai_analysis)
        else:
            output.append("\n🔧 Análisis de IA no disponible - funcionando con análisis técnico tradicional")
        
        return "\n".join(output)

    def run_analysis(self):
        """Ejecutar análisis completo mejorado"""
        all_analysis = {}
        
        for symbol in self.symbols:
            print(f"{Fore.WHITE}{Style.DIM}Analizando {symbol}...", end='\r')
            
            # Obtener datos
            df = self.get_klines(symbol)
            if df is None:
                continue
                
            # Calcular indicadores
            df = self.calculate_indicators(df)
            if df is None:
                continue
                
            # Detectar patrones con mejoras
            analysis = self.detect_patterns(df, symbol)
            all_analysis[symbol] = analysis
        
        # Aplicar filtros de mercado zombie
        zombie_metrics = self.detect_zombie_market(all_analysis)
        
        # Actualizar umbrales dinámicos
        self.update_dynamic_thresholds(zombie_metrics)
        
        # Detectar cambios de régimen
        regime_change = self.detect_regime_change(all_analysis, zombie_metrics)
        
        if regime_change:
            print(f"\n{Fore.MAGENTA}🚨 CAMBIO DE RÉGIMEN DETECTADO: {regime_change.value.name}")
        
        return all_analysis

    def run_continuous(self):
        """Ejecutar análisis continuo mejorado"""
        print(f"{Fore.GREEN}{Style.BRIGHT}🚀 Iniciando análisis continuo de patrones MEJORADO...")
        print(f"{Fore.YELLOW}Mejoras activas: Filtros Zombie + Análisis Híbrido + Umbrales Dinámicos + Alertas de Régimen")
        print(f"{Fore.MAGENTA}🚀 ACTIVANDO BOOST TEMPORAL para resolver problema de 0% confianza...")
        print(f"{Fore.YELLOW}Presiona Ctrl+C para detener")
        
        # Activar boost temporal al inicio para abordar el problema de 0% confianza
        self.activate_boost_mode("Inicio del sistema - Resolver 0% confianza")
        
        time.sleep(3)
        
        try:
            while True:
                self.iteration_count += 1
                
                # Verificar expiración del boost
                self.check_boost_expiration()
                
                # Limpiar pantalla
                self.clear_screen()
                
                # Imprimir encabezado mejorado
                self.print_header()
                
                # Ejecutar análisis mejorado
                all_analysis = self.run_analysis()
                
                if all_analysis:
                    # Generar texto completo para archivo
                    analysis_text = self.generate_analysis_text(all_analysis)
                    
                    # Guardar en archivo
                    self.save_analysis_to_file(analysis_text)
                    
                    # Mostrar análisis por símbolo
                    for symbol in self.symbols:
                        if symbol in all_analysis:
                            self.print_symbol_analysis(symbol, all_analysis[symbol])
                    
                    # Mostrar resumen del mercado mejorado
                    self.print_market_summary(all_analysis)
                    
                    # Mostrar análisis de IA híbrido
                    if self.ai_enabled:
                        print(f"\n{Fore.CYAN}{'='*80}")
                        print(f"{Fore.CYAN}                    ANÁLISIS INTELIGENTE HÍBRIDO                    ")
                        print(f"{Fore.CYAN}{'='*80}")
                        
                        # Preparar datos para IA
                        market_data = {}
                        for symbol, analysis in all_analysis.items():
                            market_data[symbol] = {
                                'price': analysis['current_price'],
                                'resistance': analysis['resistance'],
                                'support': analysis['support'],
                                'rsi': analysis['rsi'],
                                'volume_ratio': analysis['volume_ratio'],
                                'confidence': analysis['confidence'],
                                'patterns': analysis['patterns']
                            }
                        
                        # Generar análisis híbrido
                        ai_analysis = self.generate_hybrid_ai_analysis(market_data)
                        print(f"{Fore.WHITE}{ai_analysis}")
                    else:
                        print(f"\n{Fore.YELLOW}🔧 Análisis de IA no disponible - funcionando con análisis técnico tradicional")
                    
                    # Confirmar guardado
                    print(f"\n{Fore.GREEN}✅ Análisis guardado en: {self.log_file}")
                    
                    # Mostrar estadísticas de mejoras
                    print(f"\n{Fore.CYAN}📊 ESTADÍSTICAS DE MEJORAS:")
                    print(f"{Fore.WHITE}Régimen actual: {self.current_regime.value.name}")
                    if self.zombie_metrics.is_zombie:
                        print(f"{Fore.RED}Estado zombie: ACTIVO ({self.zombie_metrics.consecutive_zero_patterns} iteraciones)")
                    print(f"{Fore.WHITE}Umbrales dinámicos: Conf≥{self.dynamic_thresholds['confidence_min']:.1f}%, Vol≥{self.dynamic_thresholds['volume_min']:.1f}x")
                    print(f"{Fore.WHITE}Cambios de régimen: {len(self.regime_change_alerts)}")
                    
                    # Mostrar estado del boost si está activo
                    boost_status = self.get_boost_status()
                    if boost_status['active']:
                        print(f"{Fore.MAGENTA}🚀 BOOST ACTIVO: {boost_status['progress']:.1f}% completado, {boost_status['remaining']:.0f}s restantes")
                    
                else:
                    print(f"{Fore.RED}❌ No se pudieron obtener datos del mercado")
                
                # Ajustar intervalo basado en régimen
                if self.zombie_metrics.is_zombie:
                    actual_interval = self.refresh_interval * 2  # Reducir frecuencia en mercado zombie
                    print(f"\n{Fore.YELLOW}🧟 Mercado zombie detectado - Intervalo extendido a {actual_interval}s")
                else:
                    actual_interval = self.refresh_interval
                
                # Countdown para próxima actualización
                print(f"\n{Fore.CYAN}{'='*80}")
                print(f"{Fore.YELLOW}Esperando {actual_interval} segundos para próxima actualización...")
                
                # Esperar con countdown
                for remaining in range(actual_interval, 0, -1):
                    print(f"\r{Fore.WHITE}{Style.DIM}Próxima actualización en: {remaining:02d} segundos", end='', flush=True)
                    time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n\n{Fore.GREEN}{Style.BRIGHT}✅ Análisis continuo mejorado detenido por el usuario")
            print(f"{Fore.YELLOW}Total de iteraciones ejecutadas: {self.iteration_count}")
            print(f"{Fore.YELLOW}Cambios de régimen detectados: {len(self.regime_change_alerts)}")
            if self.zombie_metrics.is_zombie:
                print(f"{Fore.YELLOW}Estado final: MERCADO ZOMBIE")
            sys.exit(0)
        except Exception as e:
            print(f"\n\n{Fore.RED}❌ Error en análisis continuo: {e}")
            sys.exit(1)

    def activate_boost_mode(self, reason: str = "Manual activation"):
        """
        🚀 ACTIVAR MODO BOOST TEMPORAL
        Reduce temporalmente los umbrales para detectar más actividad
        """
        self.boost_mode = True
        self.boost_start_time = datetime.now()
        
        logger.info(f"🚀 MODO BOOST ACTIVADO: {reason}")
        logger.info(f"Duración: {self.boost_duration} segundos")
        
        # Aplicar boost inmediatamente
        if hasattr(self, 'dynamic_thresholds'):
            original_conf = self.dynamic_thresholds['confidence_min']
            original_vol = self.dynamic_thresholds['volume_min']
            
            self.dynamic_thresholds['confidence_min'] *= 0.7
            self.dynamic_thresholds['volume_min'] *= 0.8
            
            logger.info(f"Umbrales ajustados: Conf {original_conf:.1f}% → {self.dynamic_thresholds['confidence_min']:.1f}%")
            logger.info(f"Umbrales ajustados: Vol {original_vol:.1f}x → {self.dynamic_thresholds['volume_min']:.1f}x")
    
    def check_boost_expiration(self):
        """
        ⏰ VERIFICAR EXPIRACIÓN DEL BOOST
        Desactiva el boost si ha expirado
        """
        if self.boost_mode and self.boost_start_time:
            elapsed = (datetime.now() - self.boost_start_time).total_seconds()
            
            if elapsed >= self.boost_duration:
                self.deactivate_boost_mode("Tiempo expirado")
                return True
        
        return False
    
    def deactivate_boost_mode(self, reason: str = "Manual deactivation"):
        """
        🛑 DESACTIVAR MODO BOOST
        Restaura los umbrales normales
        """
        if self.boost_mode:
            self.boost_mode = False
            elapsed = (datetime.now() - self.boost_start_time).total_seconds() if self.boost_start_time else 0
            
            logger.info(f"🛑 MODO BOOST DESACTIVADO: {reason}")
            logger.info(f"Duración total: {elapsed:.1f} segundos")
            
            # Los umbrales se restaurarán automáticamente en la próxima actualización
            # ya que update_dynamic_thresholds() no aplicará el multiplicador boost
            
            self.boost_start_time = None
    
    def get_boost_status(self) -> dict:
        """
        📊 OBTENER ESTADO DEL BOOST
        Retorna información sobre el estado actual del boost
        """
        if not self.boost_mode:
            return {
                'active': False,
                'elapsed': 0,
                'remaining': 0,
                'progress': 0
            }
        
        elapsed = (datetime.now() - self.boost_start_time).total_seconds() if self.boost_start_time else 0
        remaining = max(0, self.boost_duration - elapsed)
        progress = min(100, (elapsed / self.boost_duration) * 100)
        
        return {
            'active': True,
            'elapsed': elapsed,
            'remaining': remaining,
            'progress': progress
        }

def main():
    """Función principal"""
    analyzer = AnalisisContinuoPatronesMejorado()
    analyzer.run_continuous()

if __name__ == "__main__":
    main()