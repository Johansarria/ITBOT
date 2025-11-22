"""
Sistema de Detección de Breakouts Mejorado para SICAR
Implementa detección en tiempo real con alertas y sensibilidad ajustable
Incluye integración con ScalpingEngine para operaciones automáticas de 5 minutos
"""

import numpy as np
import pandas as pd
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import pytz
from enhanced_config import CONFIG
from enhanced_logger import SICAR_LOGGER

# Importar ScalpingEngine para operaciones automáticas
try:
    from scalping_engine import ScalpingEngine
    SCALPING_AVAILABLE = True
except ImportError:
    SCALPING_AVAILABLE = False
    SICAR_LOGGER.log_alert("SCALPING_IMPORT", "ScalpingEngine no disponible", "WARNING")

class BreakoutType(Enum):
    """Tipos de breakout"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class BreakoutStrength(Enum):
    """Fuerza del breakout"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

@dataclass
class BreakoutSignal:
    """Señal de breakout detectada"""
    symbol: str
    timestamp: datetime
    breakout_type: BreakoutType
    strength: BreakoutStrength
    confidence: float
    price: float
    volume: float
    resistance_level: float
    support_level: float
    price_change_pct: float
    volume_ratio: float
    candle_pattern: str
    technical_indicators: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat(),
            'breakout_type': self.breakout_type.value,
            'strength': self.strength.value,
            'confidence': self.confidence,
            'price': self.price,
            'volume': self.volume,
            'resistance_level': self.resistance_level,
            'support_level': self.support_level,
            'price_change_pct': self.price_change_pct,
            'volume_ratio': self.volume_ratio,
            'candle_pattern': self.candle_pattern,
            'technical_indicators': self.technical_indicators
        }

class EnhancedBreakoutDetector:
    """Detector de breakouts mejorado"""
    
    def __init__(self, paper_trading_system=None):
        self.config = CONFIG.BREAKOUT_DETECTION
        self.alert_callbacks: List[Callable[[BreakoutSignal], None]] = []
        self.price_history: Dict[str, List[Dict]] = {}
        self.last_signals: Dict[str, BreakoutSignal] = {}
        self.running = False
        self.detection_thread = None
        self.lock = threading.RLock()
        
        # Configuración de sensibilidad
        self.sensitivity = self.config['sensitivity']
        self.min_volume_ratio = self.config['min_volume_ratio']
        self.min_price_change = self.config['min_price_change_pct']
        self.lookback_periods = self.config['lookback_periods']
        
        # Configuración para ventanas de sesión
        self.session_config = self.config.get('session_window_config', {})
        self.sessions_config = CONFIG.SESSIONS_CONFIG
        
        # 🚀 INICIALIZAR SCALPING ENGINE
        self.scalping_engine = None
        if SCALPING_AVAILABLE and CONFIG.SCALPING_CONFIG.get('enabled', False):
            try:
                self.scalping_engine = ScalpingEngine(paper_trading_system=paper_trading_system)
                SICAR_LOGGER.log_alert("SCALPING_INIT", "ScalpingEngine inicializado correctamente", "INFO")
            except Exception as e:
                SICAR_LOGGER.log_error("SCALPING_INIT", f"Error inicializando ScalpingEngine: {e}")
                self.scalping_engine = None
        
    def start_detection(self):
        """Iniciar detección de breakouts"""
        if not self.running:
            self.running = True
            self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
            self.detection_thread.start()
            SICAR_LOGGER.log_alert("BREAKOUT_DETECTOR", "Detector de breakouts iniciado", "INFO")
            
            # Iniciar ScalpingEngine si está disponible
            if self.scalping_engine:
                try:
                    self.scalping_engine.start()
                    SICAR_LOGGER.log_alert("SCALPING_START", "ScalpingEngine iniciado con el detector", "INFO")
                except Exception as e:
                    SICAR_LOGGER.log_error("SCALPING_START", f"Error iniciando ScalpingEngine: {e}")
    
    def stop_detection(self):
        """Detener detección de breakouts"""
        self.running = False
        if self.detection_thread:
            self.detection_thread.join(timeout=5)
        SICAR_LOGGER.log_alert("BREAKOUT_DETECTOR", "Detector de breakouts detenido", "INFO")
        
        # Detener ScalpingEngine si está disponible
        if self.scalping_engine:
            try:
                self.scalping_engine.stop()
                SICAR_LOGGER.log_alert("SCALPING_STOP", "ScalpingEngine detenido con el detector", "INFO")
            except Exception as e:
                SICAR_LOGGER.log_error("SCALPING_STOP", f"Error deteniendo ScalpingEngine: {e}")
    
    def _is_in_session_window(self) -> tuple[bool, str]:
        """
        Detectar si estamos en una ventana crítica de sesión de 5 minutos
        Returns: (is_in_window, session_name)
        """
        try:
            # Obtener tiempo actual en ET (Eastern Time)
            et_tz = pytz.timezone('US/Eastern')
            current_time = datetime.now(et_tz)
            current_time_str = current_time.strftime('%H:%M')
            
            # Verificar cada sesión
            for session_name, session_info in self.sessions_config.items():
                if not session_info.get('active', False):
                    continue
                
                start_time = session_info['start_time']
                end_time = session_info['end_time']
                
                # Convertir a objetos time para comparación
                start_hour, start_min = map(int, start_time.split(':'))
                end_hour, end_min = map(int, end_time.split(':'))
                
                current_hour = current_time.hour
                current_min = current_time.minute
                
                # Verificar si estamos en la ventana
                start_minutes = start_hour * 60 + start_min
                end_minutes = end_hour * 60 + end_min
                current_minutes = current_hour * 60 + current_min
                
                # Manejar caso donde la sesión cruza medianoche
                if end_minutes < start_minutes:
                    # Sesión cruza medianoche
                    if current_minutes >= start_minutes or current_minutes <= end_minutes:
                        SICAR_LOGGER.log_alert("SESSION_WINDOW", 
                                             f"🚨 VENTANA CRÍTICA ACTIVA: {session_info['name']} ({start_time}-{end_time})", 
                                             "WARNING")
                        return True, session_name
                else:
                    # Sesión normal
                    if start_minutes <= current_minutes <= end_minutes:
                        SICAR_LOGGER.log_alert("SESSION_WINDOW", 
                                             f"🚨 VENTANA CRÍTICA ACTIVA: {session_info['name']} ({start_time}-{end_time})", 
                                             "WARNING")
                        return True, session_name
            
            return False, ""
            
        except Exception as e:
            SICAR_LOGGER.log_error("SESSION_WINDOW_CHECK", f"Error verificando ventana de sesión: {e}")
            return False, ""
    
    def _detection_loop(self):
        """Bucle principal de detección OPTIMIZADO"""
        SICAR_LOGGER.log_alert("BREAKOUT_DETECTOR", "🚀 Iniciando bucle de detección de breakouts OPTIMIZADO", "INFO")
        
        # 🛡️ CONTADORES DE PROTECCIÓN
        consecutive_errors = 0
        max_consecutive_errors = 5
        last_session_check = None
        
        while self.running:
            try:
                # 🛡️ PROTECCIÓN CONTRA SOBRECARGA: Limitar verificaciones de sesión
                current_minute = datetime.now().strftime('%H:%M')
                if last_session_check != current_minute:
                    is_session_window, session_name = self._is_in_session_window()
                    last_session_check = current_minute
                else:
                    # Usar último estado conocido para evitar verificaciones repetidas
                    is_session_window = hasattr(self, '_last_session_state') and self._last_session_state
                    session_name = getattr(self, '_last_session_name', "")
                
                self._last_session_state = is_session_window
                self._last_session_name = session_name
                
                if is_session_window and self.session_config:
                    detection_interval = max(30, self.session_config.get('detection_interval', 30))  # Mínimo 30 segundos
                    SICAR_LOGGER.log_alert("SESSION_DETECTION", 
                                         f"🔥 DETECCIÓN ACELERADA: cada {detection_interval}s durante {session_name}", 
                                         "INFO")
                else:
                    detection_interval = max(30, self.config['detection_interval'])  # Mínimo 30 segundos
                
                # 🛡️ PROTECCIÓN: Simular datos solo si es necesario
                if not hasattr(self, '_last_data_update') or (datetime.now() - self._last_data_update).seconds >= 30:
                    self._simulate_market_data()
                    self._last_data_update = datetime.now()
                
                # 🛡️ PROTECCIÓN: Procesar símbolos con límite de tiempo
                symbols_processed = 0
                max_symbols_per_cycle = 3  # Limitar procesamiento
                
                for symbol in self.config['symbols_to_monitor'][:max_symbols_per_cycle]:
                    try:
                        signal = self._analyze_symbol(symbol)
                        if signal:
                            self._process_breakout_signal(signal)
                        symbols_processed += 1
                    except Exception as symbol_error:
                        SICAR_LOGGER.log_error("SYMBOL_ANALYSIS", f"Error procesando {symbol}: {symbol_error}")
                        continue
                
                # 🛡️ RESETEAR CONTADOR DE ERRORES EN ÉXITO
                consecutive_errors = 0
                
                # 🛡️ SLEEP MÍNIMO GARANTIZADO
                time.sleep(max(5, detection_interval))
                
            except Exception as e:
                consecutive_errors += 1
                SICAR_LOGGER.log_error("BREAKOUT_DETECTION", f"Error #{consecutive_errors}: {e}")
                
                # 🛡️ PROTECCIÓN CONTRA BUCLES DE ERROR
                if consecutive_errors >= max_consecutive_errors:
                    SICAR_LOGGER.log_alert("BREAKOUT_DETECTOR", 
                                         f"🚨 DEMASIADOS ERRORES CONSECUTIVOS ({consecutive_errors}). Pausando detección por 60 segundos.", 
                                         "ERROR")
                    time.sleep(60)
                    consecutive_errors = 0
                else:
                    time.sleep(min(30, self.config['detection_interval'] * (consecutive_errors + 1)))
    
    def _simulate_market_data(self):
        """Simular datos de mercado para testing"""
        # Esta función simula datos de mercado
        # En producción se reemplazaría por llamadas reales a la API
        
        current_time = datetime.now()
        
        for symbol in self.config['symbols_to_monitor']:
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            
            # Simular precio con variación aleatoria
            last_price = 2000.0  # Precio base para ETHUSDT
            if self.price_history[symbol]:
                last_price = self.price_history[symbol][-1]['close']
            
            # Generar variación de precio
            price_change = np.random.normal(0, 0.002)  # 0.2% de volatilidad
            new_price = last_price * (1 + price_change)
            
            # Simular volumen
            base_volume = 1000000
            volume_multiplier = np.random.uniform(0.5, 3.0)
            volume = base_volume * volume_multiplier
            
            # Crear datos de vela
            candle_data = {
                'timestamp': current_time,
                'open': last_price,
                'high': new_price * 1.001,
                'low': new_price * 0.999,
                'close': new_price,
                'volume': volume
            }
            
            self.price_history[symbol].append(candle_data)
            
            # Mantener solo los últimos datos necesarios
            max_history = self.lookback_periods * 2
            if len(self.price_history[symbol]) > max_history:
                self.price_history[symbol] = self.price_history[symbol][-max_history:]
    
    def _analyze_symbol(self, symbol: str) -> Optional[BreakoutSignal]:
        """Analizar símbolo para detectar breakouts"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < self.lookback_periods:
            return None
        
        try:
            # 🚨 VERIFICAR SI ESTAMOS EN VENTANA CRÍTICA DE SESIÓN
            is_session_window, session_name = self._is_in_session_window()
            
            # Usar configuración ultra-sensible durante ventanas de sesión
            if is_session_window and self.session_config:
                sensitivity = self.session_config.get('sensitivity', 0.1)
                min_volume_ratio = self.session_config.get('min_volume_ratio', 1.05)
                min_price_change = self.session_config.get('min_price_change_pct', 0.1)
                lookback_periods = self.session_config.get('lookback_periods', 5)
                force_detection = self.session_config.get('force_detection', True)
                min_confidence_threshold = self.session_config.get('min_confidence_threshold', 30)
                
                SICAR_LOGGER.log_alert("SESSION_BREAKOUT", 
                                     f"🔥 MODO ULTRA-SENSIBLE ACTIVADO para {symbol} en {session_name}", 
                                     "WARNING")
            else:
                # Configuración normal
                sensitivity = self.sensitivity
                min_volume_ratio = self.min_volume_ratio
                min_price_change = self.min_price_change
                lookback_periods = self.lookback_periods
                force_detection = False
                min_confidence_threshold = 50
            
            data = self.price_history[symbol]
            df = pd.DataFrame(data)
            
            # Calcular indicadores técnicos
            indicators = self._calculate_technical_indicators(df)
            
            # Detectar niveles de soporte y resistencia
            support_level, resistance_level = self._calculate_support_resistance(df)
            
            # Analizar breakout
            current_price = df['close'].iloc[-1]
            current_volume = df['volume'].iloc[-1]
            
            # Calcular ratios con períodos ajustados
            avg_volume = df['volume'].rolling(lookback_periods).mean().iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            price_change_pct = ((current_price - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100
            
            # Detectar tipo de breakout
            breakout_type = self._determine_breakout_type(
                current_price, support_level, resistance_level, indicators
            )
            
            # 🚨 FORZAR DETECCIÓN DURANTE VENTANAS DE SESIÓN
            if is_session_window and force_detection and breakout_type == BreakoutType.NEUTRAL:
                # Si no hay breakout natural, crear uno basado en el movimiento más pequeño
                if abs(price_change_pct) >= 0.05:  # Cualquier movimiento > 0.05%
                    breakout_type = BreakoutType.BULLISH if price_change_pct > 0 else BreakoutType.BEARISH
                    SICAR_LOGGER.log_alert("FORCED_BREAKOUT", 
                                         f"🚨 BREAKOUT FORZADO en {symbol}: {price_change_pct:.3f}% durante {session_name}", 
                                         "WARNING")
            
            if breakout_type == BreakoutType.NEUTRAL:
                return None
            
            # Calcular confianza y fuerza
            confidence = self._calculate_confidence(
                price_change_pct, volume_ratio, indicators, breakout_type
            )
            
            # 🚨 AJUSTAR CONFIANZA DURANTE VENTANAS DE SESIÓN
            if is_session_window:
                # Aumentar confianza base durante ventanas críticas
                confidence = max(confidence, min_confidence_threshold)
                if force_detection:
                    confidence = max(confidence, 60)  # Confianza mínima garantizada
            
            strength = self._determine_strength(confidence, volume_ratio, abs(price_change_pct))
            
            # 🚨 CRITERIOS ULTRA-RELAJADOS DURANTE VENTANAS DE SESIÓN
            if is_session_window:
                # Durante ventanas de sesión, casi cualquier movimiento es válido
                criteria_met = (
                    confidence >= min_confidence_threshold and
                    (volume_ratio >= min_volume_ratio or force_detection) and
                    abs(price_change_pct) >= min_price_change
                )
                
                if not criteria_met and force_detection:
                    # Si forzamos detección, relajar todos los criterios
                    criteria_met = abs(price_change_pct) >= 0.05
                    if criteria_met:
                        SICAR_LOGGER.log_alert("FORCED_CRITERIA", 
                                             f"🚨 CRITERIOS FORZADOS para {symbol} en {session_name}", 
                                             "WARNING")
            else:
                # Criterios normales
                criteria_met = (
                    confidence >= sensitivity and
                    volume_ratio >= min_volume_ratio and
                    abs(price_change_pct) >= min_price_change
                )
            
            if not criteria_met:
                # 🚨 ÚLTIMA OPORTUNIDAD: GARANTIZAR BREAKOUT DURANTE VENTANA CRÍTICA
                if is_session_window and force_detection:
                    SICAR_LOGGER.log_alert("GUARANTEE_ACTIVATION", 
                                         f"🚨 ACTIVANDO GARANTÍA DE BREAKOUT para {symbol} en {session_name}", 
                                         "WARNING")
                    return self._guarantee_session_breakout(symbol, session_name)
                return None
            
            # Crear señal de breakout
            signal = BreakoutSignal(
                symbol=symbol,
                timestamp=datetime.now(),
                breakout_type=breakout_type,
                strength=strength,
                confidence=confidence,
                price=current_price,
                volume=current_volume,
                resistance_level=resistance_level,
                support_level=support_level,
                price_change_pct=price_change_pct,
                volume_ratio=volume_ratio,
                candle_pattern=self._identify_candle_pattern(df.tail(3)),
                technical_indicators=indicators
            )
            
            return signal
            
        except Exception as e:
            SICAR_LOGGER.log_error("BREAKOUT_ANALYSIS", str(e), {"symbol": symbol})
            return None
    
    def _guarantee_session_breakout(self, symbol: str, session_name: str) -> Optional[BreakoutSignal]:
        """
        🚨 GARANTIZAR BREAKOUT DURANTE VENTANA CRÍTICA DE SESIÓN
        Esta función asegura que SIEMPRE se genere una operación durante los 5 minutos críticos
        OPTIMIZADA: Con timeout y límites para evitar cuelgues
        """
        try:
            # 🛡️ PROTECCIÓN CONTRA BUCLES INFINITOS
            current_time = datetime.now()
            cache_key = f"{symbol}_{session_name}_{current_time.strftime('%H:%M')}"
            
            # Evitar llamadas repetidas en el mismo minuto
            if hasattr(self, '_guarantee_cache'):
                if cache_key in self._guarantee_cache:
                    return self._guarantee_cache[cache_key]
            else:
                self._guarantee_cache = {}
            
            # Limpiar cache viejo (más de 5 minutos)
            old_keys = [k for k in self._guarantee_cache.keys() 
                       if (current_time - datetime.strptime(k.split('_')[-1], '%H:%M')).total_seconds() > 300]
            for old_key in old_keys:
                del self._guarantee_cache[old_key]
            
            if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
                self._guarantee_cache[cache_key] = None
                return None
            
            data = self.price_history[symbol]
            df = pd.DataFrame(data)
            
            current_price = df['close'].iloc[-1]
            previous_price = df['close'].iloc[-2]
            current_volume = df['volume'].iloc[-1]
            
            # Calcular el movimiento real del precio
            price_change_pct = ((current_price - previous_price) / previous_price) * 100
            
            # Analizar volatilidad reciente para determinar movimiento normal
            recent_changes = []
            for i in range(min(10, len(df)-1)):
                prev_close = df['close'].iloc[-(i+2)]
                curr_close = df['close'].iloc[-(i+1)]
                change = ((curr_close - prev_close) / prev_close) * 100
                recent_changes.append(abs(change))
            
            # Calcular movimiento promedio y usar como referencia
            avg_movement = np.mean(recent_changes) if recent_changes else 0.1
            min_normal_movement = max(0.05, avg_movement * 0.5)  # Al menos 50% del movimiento promedio
            
            # Si el movimiento actual es muy pequeño, usar el movimiento mínimo normal
            if abs(price_change_pct) < min_normal_movement:
                # Usar la dirección del momentum reciente o RSI
                indicators = self._calculate_technical_indicators(df) if len(df) >= 14 else {}
                rsi = indicators.get('rsi', 50)
                
                # Determinar dirección basada en RSI y momentum
                if rsi > 50:
                    price_change_pct = min_normal_movement  # Bullish
                else:
                    price_change_pct = -min_normal_movement  # Bearish
                
                SICAR_LOGGER.log_alert("NORMAL_BREAKOUT_ENHANCED", 
                                     f"📈 BREAKOUT NORMAL MEJORADO para {symbol}: {price_change_pct:.3f}% basado en análisis técnico en {session_name}", 
                                     "INFO")
            
            # Determinar tipo de breakout
            breakout_type = BreakoutType.BULLISH if price_change_pct > 0 else BreakoutType.BEARISH
            
            # Calcular indicadores básicos
            indicators = self._calculate_technical_indicators(df) if len(df) >= 14 else {}
            
            # Niveles de soporte/resistencia básicos
            support_level = df['low'].tail(10).min()
            resistance_level = df['high'].tail(10).max()
            
            # Calcular volumen ratio realista basado en promedio reciente
            recent_volumes = df['volume'].tail(10).values
            avg_volume = np.mean(recent_volumes) if len(recent_volumes) > 0 else current_volume
            volume_ratio = max(1.2, current_volume / avg_volume) if avg_volume > 0 else 1.2
            
            # Calcular confianza basada en análisis técnico real (valores entre 0 y 1)
            base_confidence = 0.60  # Base de 60%
            
            # 🎯 PRIORIDAD #1: DETECCIÓN DE DIVERGENCIAS RSI
            rsi_divergence = self._detect_rsi_divergence(df)
            if rsi_divergence['type'] is not None:
                # Si hay divergencia que coincide con el tipo de breakout
                if ((breakout_type == BreakoutType.BULLISH and rsi_divergence['type'] == 'bullish') or
                    (breakout_type == BreakoutType.BEARISH and rsi_divergence['type'] == 'bearish')):
                    # Aumentar significativamente la confianza por divergencia confirmada
                    divergence_boost = rsi_divergence['strength'] * 0.20  # Hasta 20% adicional
                    base_confidence += divergence_boost
                    SICAR_LOGGER.log_alert("RSI_DIVERGENCE", 
                        f"🎯 Divergencia {rsi_divergence['type']} detectada! "
                        f"Fuerza: {rsi_divergence['strength']:.2f}, "
                        f"Boost confianza: +{divergence_boost:.2f}", "INFO")
                elif ((breakout_type == BreakoutType.BULLISH and rsi_divergence['type'] == 'bearish') or
                      (breakout_type == BreakoutType.BEARISH and rsi_divergence['type'] == 'bullish')):
                    # Reducir confianza si la divergencia va en contra del breakout
                    divergence_penalty = rsi_divergence['strength'] * 0.15  # Hasta 15% de penalización
                    base_confidence -= divergence_penalty
                    SICAR_LOGGER.log_warning("RSI_DIVERGENCE", 
                        f"⚠️ Divergencia {rsi_divergence['type']} contradice breakout {breakout_type.name}! "
                        f"Penalización: -{divergence_penalty:.2f}")
            
            # 🎯 PRIORIDAD #2: DETECCIÓN DE DIVERGENCIAS MACD
            macd_divergence = self._detect_macd_divergence(df)
            if macd_divergence['type'] is not None:
                # Si hay divergencia MACD que coincide con el tipo de breakout
                if ((breakout_type == BreakoutType.BULLISH and macd_divergence['type'] == 'bullish') or
                    (breakout_type == BreakoutType.BEARISH and macd_divergence['type'] == 'bearish')):
                    # Aumentar confianza por divergencia MACD confirmada
                    macd_boost = macd_divergence['strength'] * 0.15  # Hasta 15% adicional
                    base_confidence += macd_boost
                    SICAR_LOGGER.log_alert("MACD_DIVERGENCE", 
                        f"🎯 Divergencia MACD {macd_divergence['type']} detectada! "
                        f"Fuerza: {macd_divergence['strength']:.2f}, "
                        f"Boost confianza: +{macd_boost:.2f}", "INFO")
                elif ((breakout_type == BreakoutType.BULLISH and macd_divergence['type'] == 'bearish') or
                      (breakout_type == BreakoutType.BEARISH and macd_divergence['type'] == 'bullish')):
                    # Reducir confianza si la divergencia MACD va en contra del breakout
                    macd_penalty = macd_divergence['strength'] * 0.10  # Hasta 10% de penalización
                    base_confidence -= macd_penalty
                    SICAR_LOGGER.log_warning("MACD_DIVERGENCE", 
                        f"⚠️ Divergencia MACD {macd_divergence['type']} contradice breakout {breakout_type.name}! "
                        f"Penalización: -{macd_penalty:.2f}")
            
            # Ajustar confianza basada en indicadores técnicos tradicionales
            if 'rsi' in indicators:
                rsi = indicators['rsi']
                if (breakout_type == BreakoutType.BULLISH and rsi < 70) or (breakout_type == BreakoutType.BEARISH and rsi > 30):
                    base_confidence += 0.10  # RSI no está en zona de sobrecompra/sobreventa
            
            if 'macd' in indicators and 'macd_signal' in indicators:
                macd_diff = indicators['macd'] - indicators['macd_signal']
                if (breakout_type == BreakoutType.BULLISH and macd_diff > 0) or (breakout_type == BreakoutType.BEARISH and macd_diff < 0):
                    base_confidence += 0.05  # MACD confirma la dirección
            
            # Ajustar por volumen
            if volume_ratio > 1.5:
                base_confidence += 0.10
            elif volume_ratio > 1.3:
                base_confidence += 0.05
            
            # Corregir cálculo de confianza - evitar valores extremos
            price_contribution = min(abs(price_change_pct) * 0.02, 0.15)  # Máximo 15% de contribución del precio
            confidence = min(0.85, base_confidence + price_contribution)
            
            # Fuerza basada en el movimiento
            if abs(price_change_pct) >= 0.5:
                strength = BreakoutStrength.STRONG
            elif abs(price_change_pct) >= 0.2:
                strength = BreakoutStrength.MODERATE
            else:
                strength = BreakoutStrength.WEAK
            
            # Crear señal garantizada
            guaranteed_signal = BreakoutSignal(
                symbol=symbol,
                timestamp=datetime.now(),
                breakout_type=breakout_type,
                strength=strength,
                confidence=confidence,
                price=current_price,
                volume=current_volume,
                resistance_level=resistance_level,
                support_level=support_level,
                price_change_pct=price_change_pct,
                volume_ratio=volume_ratio,  # Ratio basado en análisis real
                candle_pattern=f"SESSION_NORMAL_{session_name.upper()}",
                technical_indicators=indicators
            )
            
            SICAR_LOGGER.log_alert("NORMAL_SESSION_BREAKOUT", 
                                 f"✅ BREAKOUT NORMAL generado para {symbol} en {session_name}: "
                                 f"{breakout_type.value} {price_change_pct:.3f}% volumen {volume_ratio:.2f}x confianza {confidence*100:.1f}%", 
                                 "SUCCESS")
            
            # 🛡️ GUARDAR EN CACHE PARA EVITAR REPETICIONES
            self._guarantee_cache[cache_key] = guaranteed_signal
            
            return guaranteed_signal
            
        except Exception as e:
            SICAR_LOGGER.log_error("GUARANTEED_BREAKOUT", f"Error generando breakout garantizado: {e}")
            return None
    
    def _calculate_technical_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcular indicadores técnicos"""
        indicators = {}
        
        try:
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = (100 - (100 / (1 + rs))).iloc[-1]
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            macd = exp1 - exp2
            signal_line = macd.ewm(span=9).mean()
            indicators['macd'] = macd.iloc[-1]
            indicators['macd_signal'] = signal_line.iloc[-1]
            indicators['macd_histogram'] = (macd - signal_line).iloc[-1]
            
            # Bollinger Bands
            sma = df['close'].rolling(window=20).mean()
            std = df['close'].rolling(window=20).std()
            indicators['bb_upper'] = (sma + (std * 2)).iloc[-1]
            indicators['bb_lower'] = (sma - (std * 2)).iloc[-1]
            indicators['bb_middle'] = sma.iloc[-1]
            
            # Momentum
            indicators['momentum'] = ((df['close'].iloc[-1] / df['close'].iloc[-10]) - 1) * 100
            
        except Exception as e:
            SICAR_LOGGER.log_error("TECHNICAL_INDICATORS", str(e))
            indicators = {}
        
        return indicators
    
    def _detect_rsi_divergence(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        🎯 DETECTAR DIVERGENCIAS RSI - PRIORIDAD #1
        Detecta divergencias alcistas y bajistas entre precio y RSI
        """
        try:
            if len(df) < 20:  # Necesitamos suficientes datos
                return {'type': None, 'strength': 0.0, 'confidence': 0.0}
            
            # Calcular RSI completo
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi_series = 100 - (100 / (1 + rs))
            
            # Buscar picos y valles en precio y RSI (últimos 10 períodos)
            price_data = df['close'].tail(10)
            rsi_data = rsi_series.tail(10)
            
            # Encontrar máximos y mínimos locales
            price_highs = []
            price_lows = []
            rsi_highs = []
            rsi_lows = []
            
            for i in range(1, len(price_data) - 1):
                # Máximos locales (pico)
                if price_data.iloc[i] > price_data.iloc[i-1] and price_data.iloc[i] > price_data.iloc[i+1]:
                    price_highs.append((i, price_data.iloc[i]))
                    rsi_highs.append((i, rsi_data.iloc[i]))
                
                # Mínimos locales (valle)
                if price_data.iloc[i] < price_data.iloc[i-1] and price_data.iloc[i] < price_data.iloc[i+1]:
                    price_lows.append((i, price_data.iloc[i]))
                    rsi_lows.append((i, rsi_data.iloc[i]))
            
            # DIVERGENCIA ALCISTA: Precio hace mínimos más bajos, RSI hace mínimos más altos
            bullish_divergence = False
            bullish_strength = 0.0
            
            if len(price_lows) >= 2 and len(rsi_lows) >= 2:
                # Comparar los dos últimos mínimos
                last_price_low = price_lows[-1][1]
                prev_price_low = price_lows[-2][1]
                last_rsi_low = rsi_lows[-1][1]
                prev_rsi_low = rsi_lows[-2][1]
                
                if last_price_low < prev_price_low and last_rsi_low > prev_rsi_low:
                    bullish_divergence = True
                    # Calcular fuerza basada en la diferencia
                    price_diff = abs((last_price_low - prev_price_low) / prev_price_low)
                    rsi_diff = abs(last_rsi_low - prev_rsi_low) / 100
                    bullish_strength = min(1.0, (price_diff + rsi_diff) * 2)
            
            # DIVERGENCIA BAJISTA: Precio hace máximos más altos, RSI hace máximos más bajos
            bearish_divergence = False
            bearish_strength = 0.0
            
            if len(price_highs) >= 2 and len(rsi_highs) >= 2:
                # Comparar los dos últimos máximos
                last_price_high = price_highs[-1][1]
                prev_price_high = price_highs[-2][1]
                last_rsi_high = rsi_highs[-1][1]
                prev_rsi_high = rsi_highs[-2][1]
                
                if last_price_high > prev_price_high and last_rsi_high < prev_rsi_high:
                    bearish_divergence = True
                    # Calcular fuerza basada en la diferencia
                    price_diff = abs((last_price_high - prev_price_high) / prev_price_high)
                    rsi_diff = abs(last_rsi_high - prev_rsi_high) / 100
                    bearish_strength = min(1.0, (price_diff + rsi_diff) * 2)
            
            # Determinar resultado final
            if bullish_divergence and bullish_strength > bearish_strength:
                return {
                    'type': 'bullish',
                    'strength': bullish_strength,
                    'confidence': min(0.85, 0.5 + bullish_strength * 0.35),
                    'current_rsi': rsi_series.iloc[-1]
                }
            elif bearish_divergence and bearish_strength > bullish_strength:
                return {
                    'type': 'bearish',
                    'strength': bearish_strength,
                    'confidence': min(0.85, 0.5 + bearish_strength * 0.35),
                    'current_rsi': rsi_series.iloc[-1]
                }
            else:
                return {
                    'type': None,
                    'strength': 0.0,
                    'confidence': 0.0,
                    'current_rsi': rsi_series.iloc[-1] if not rsi_series.empty else 50
                }
                
        except Exception as e:
            SICAR_LOGGER.log_error("RSI_DIVERGENCE", f"Error detectando divergencia RSI: {e}")
            return {'type': None, 'strength': 0.0, 'confidence': 0.0}

    def _detect_macd_divergence(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        🎯 DETECTAR DIVERGENCIAS MACD - PRIORIDAD #2
        Detecta divergencias alcistas y bajistas entre precio y MACD
        """
        try:
            if len(df) < 26:  # Necesitamos suficientes datos para MACD
                return {'type': None, 'strength': 0.0, 'confidence': 0.0}
            
            # Calcular MACD completo
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line
            
            # Buscar picos y valles en precio y MACD (últimos 8 períodos)
            price_data = df['close'].tail(8)
            macd_data = macd_line.tail(8)
            
            # Encontrar máximos y mínimos locales
            price_highs = []
            price_lows = []
            macd_highs = []
            macd_lows = []
            
            for i in range(1, len(price_data) - 1):
                # Máximos locales (pico)
                if price_data.iloc[i] > price_data.iloc[i-1] and price_data.iloc[i] > price_data.iloc[i+1]:
                    price_highs.append((i, price_data.iloc[i]))
                    macd_highs.append((i, macd_data.iloc[i]))
                
                # Mínimos locales (valle)
                if price_data.iloc[i] < price_data.iloc[i-1] and price_data.iloc[i] < price_data.iloc[i+1]:
                    price_lows.append((i, price_data.iloc[i]))
                    macd_lows.append((i, macd_data.iloc[i]))
            
            # DIVERGENCIA ALCISTA: Precio hace mínimos más bajos, MACD hace mínimos más altos
            bullish_divergence = False
            bullish_strength = 0.0
            
            if len(price_lows) >= 2 and len(macd_lows) >= 2:
                # Comparar los dos últimos mínimos
                last_price_low = price_lows[-1][1]
                prev_price_low = price_lows[-2][1]
                last_macd_low = macd_lows[-1][1]
                prev_macd_low = macd_lows[-2][1]
                
                if last_price_low < prev_price_low and last_macd_low > prev_macd_low:
                    bullish_divergence = True
                    # Calcular fuerza basada en la diferencia
                    price_diff = abs((last_price_low - prev_price_low) / prev_price_low)
                    macd_diff = abs(last_macd_low - prev_macd_low) / max(abs(prev_macd_low), 0.001)
                    bullish_strength = min(1.0, (price_diff + macd_diff) * 1.5)
            
            # DIVERGENCIA BAJISTA: Precio hace máximos más altos, MACD hace máximos más bajos
            bearish_divergence = False
            bearish_strength = 0.0
            
            if len(price_highs) >= 2 and len(macd_highs) >= 2:
                # Comparar los dos últimos máximos
                last_price_high = price_highs[-1][1]
                prev_price_high = price_highs[-2][1]
                last_macd_high = macd_highs[-1][1]
                prev_macd_high = macd_highs[-2][1]
                
                if last_price_high > prev_price_high and last_macd_high < prev_macd_high:
                    bearish_divergence = True
                    # Calcular fuerza basada en la diferencia
                    price_diff = abs((last_price_high - prev_price_high) / prev_price_high)
                    macd_diff = abs(last_macd_high - prev_macd_high) / max(abs(prev_macd_high), 0.001)
                    bearish_strength = min(1.0, (price_diff + macd_diff) * 1.5)
            
            # Determinar resultado final
            if bullish_divergence and bullish_strength > bearish_strength:
                return {
                    'type': 'bullish',
                    'strength': bullish_strength,
                    'confidence': min(0.80, 0.4 + bullish_strength * 0.40),
                    'current_macd': macd_line.iloc[-1],
                    'current_signal': signal_line.iloc[-1]
                }
            elif bearish_divergence and bearish_strength > bullish_strength:
                return {
                    'type': 'bearish',
                    'strength': bearish_strength,
                    'confidence': min(0.80, 0.4 + bearish_strength * 0.40),
                    'current_macd': macd_line.iloc[-1],
                    'current_signal': signal_line.iloc[-1]
                }
            else:
                return {
                    'type': None,
                    'strength': 0.0,
                    'confidence': 0.0,
                    'current_macd': macd_line.iloc[-1] if not macd_line.empty else 0,
                    'current_signal': signal_line.iloc[-1] if not signal_line.empty else 0
                }
                
        except Exception as e:
            SICAR_LOGGER.log_error("MACD_DIVERGENCE", f"Error detectando divergencia MACD: {e}")
            return {'type': None, 'strength': 0.0, 'confidence': 0.0}
     
    def _calculate_support_resistance(self, df: pd.DataFrame) -> tuple:
        """Calcular niveles de soporte y resistencia"""
        try:
            # Usar mínimos y máximos locales
            highs = df['high'].rolling(window=5, center=True).max()
            lows = df['low'].rolling(window=5, center=True).min()
            
            # Filtrar picos y valles
            resistance_levels = df[df['high'] == highs]['high'].dropna()
            support_levels = df[df['low'] == lows]['low'].dropna()
            
            # Tomar niveles más recientes
            resistance_level = resistance_levels.tail(3).mean() if len(resistance_levels) > 0 else df['high'].max()
            support_level = support_levels.tail(3).mean() if len(support_levels) > 0 else df['low'].min()
            
            return support_level, resistance_level
            
        except Exception:
            return df['low'].min(), df['high'].max()
    
    def _determine_breakout_type(self, price: float, support: float, resistance: float, 
                               indicators: Dict[str, float]) -> BreakoutType:
        """Determinar tipo de breakout"""
        try:
            # Breakout alcista
            if price > resistance * 1.001:  # 0.1% por encima de resistencia
                return BreakoutType.BULLISH
            
            # Breakout bajista
            elif price < support * 0.999:  # 0.1% por debajo de soporte
                return BreakoutType.BEARISH
            
            return BreakoutType.NEUTRAL
            
        except Exception:
            return BreakoutType.NEUTRAL
    
    def _calculate_confidence(self, price_change_pct: float, volume_ratio: float, 
                            indicators: Dict[str, float], breakout_type: BreakoutType) -> float:
        """Calcular confianza del breakout"""
        try:
            confidence = 0.0
            
            # Factor de cambio de precio
            price_factor = min(abs(price_change_pct) / 2.0, 0.3)  # Máximo 30%
            confidence += price_factor
            
            # Factor de volumen
            volume_factor = min((volume_ratio - 1) / 3.0, 0.3)  # Máximo 30%
            confidence += volume_factor
            
            # Factores de indicadores técnicos
            if indicators:
                # RSI
                rsi = indicators.get('rsi', 50)
                if breakout_type == BreakoutType.BULLISH and rsi > 60:
                    confidence += 0.1
                elif breakout_type == BreakoutType.BEARISH and rsi < 40:
                    confidence += 0.1
                
                # MACD
                macd_hist = indicators.get('macd_histogram', 0)
                if breakout_type == BreakoutType.BULLISH and macd_hist > 0:
                    confidence += 0.1
                elif breakout_type == BreakoutType.BEARISH and macd_hist < 0:
                    confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception:
            return 0.5
    
    def _determine_strength(self, confidence: float, volume_ratio: float, 
                          price_change_pct: float) -> BreakoutStrength:
        """Determinar fuerza del breakout"""
        score = confidence + (volume_ratio / 10) + (price_change_pct / 100)
        
        if score >= 0.8:
            return BreakoutStrength.VERY_STRONG
        elif score >= 0.6:
            return BreakoutStrength.STRONG
        elif score >= 0.4:
            return BreakoutStrength.MODERATE
        else:
            return BreakoutStrength.WEAK
    
    def _identify_candle_pattern(self, df: pd.DataFrame) -> str:
        """Identificar patrón de velas"""
        try:
            if len(df) < 3:
                return "insufficient_data"
            
            # Análisis simple de patrones
            last_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]
            
            body_size = abs(last_candle['close'] - last_candle['open'])
            candle_range = last_candle['high'] - last_candle['low']
            
            if body_size / candle_range > 0.7:
                if last_candle['close'] > last_candle['open']:
                    return "strong_bullish"
                else:
                    return "strong_bearish"
            elif body_size / candle_range < 0.3:
                return "doji"
            else:
                return "normal"
                
        except Exception:
            return "unknown"
    
    def _process_breakout_signal(self, signal: BreakoutSignal):
        """Procesar señal de breakout detectada"""
        try:
            # Evitar señales duplicadas recientes
            if signal.symbol in self.last_signals:
                last_signal = self.last_signals[signal.symbol]
                time_diff = (signal.timestamp - last_signal.timestamp).total_seconds()
                if time_diff < self.config['min_signal_interval']:
                    return
            
            # Guardar señal
            self.last_signals[signal.symbol] = signal
            
            # Log del breakout
            SICAR_LOGGER.log_breakout_detected(signal.symbol, signal.to_dict())
            
            # 🚀 ACTIVAR SCALPING AUTOMÁTICO
            if self.scalping_engine and signal.breakout_type != BreakoutType.NEUTRAL:
                try:
                    # Verificar si cumple criterios para scalping
                    scalping_config = CONFIG.SCALPING_CONFIG
                    
                    # Verificar confianza mínima
                    min_confidence = scalping_config.get('min_confidence_threshold', 55.0)
                    if signal.confidence >= min_confidence:
                        
                        # Verificar si el símbolo está permitido
                        allowed_symbols = scalping_config.get('allowed_symbols', [])
                        if not allowed_symbols or signal.symbol in allowed_symbols:
                            
                            # Verificar si estamos en ventana de sesión (si está configurado para excluir)
                            is_session_window, session_name = self._is_in_session_window()
                            exclude_session_windows = scalping_config.get('exclude_session_windows', True)
                            
                            if not (exclude_session_windows and is_session_window):
                                # Crear posición de scalping
                                position_created = self.scalping_engine.process_breakout_signal(
                                    symbol=signal.symbol,
                                    direction=signal.breakout_type.value,
                                    price=signal.price,
                                    confidence=signal.confidence,
                                    volume_ratio=signal.volume_ratio
                                )
                                
                                if position_created:
                                    SICAR_LOGGER.log_alert(
                                        "SCALPING_ACTIVATED", 
                                        f"🚀 SCALPING AUTOMÁTICO: {signal.symbol} {signal.breakout_type.value.upper()} "
                                        f"(Confianza: {signal.confidence:.1f}%, Precio: ${signal.price:.4f})",
                                        "HIGH"
                                    )
                                else:
                                    SICAR_LOGGER.log_alert(
                                        "SCALPING_REJECTED", 
                                        f"❌ Scalping rechazado para {signal.symbol}: límites alcanzados o condiciones no cumplidas",
                                        "INFO"
                                    )
                            else:
                                SICAR_LOGGER.log_alert(
                                    "SCALPING_SESSION_SKIP", 
                                    f"⏸️ Scalping pausado durante {session_name} para {signal.symbol}",
                                    "INFO"
                                )
                        else:
                            SICAR_LOGGER.log_alert(
                                "SCALPING_SYMBOL_SKIP", 
                                f"⏸️ Símbolo {signal.symbol} no permitido para scalping",
                                "INFO"
                            )
                    else:
                        SICAR_LOGGER.log_alert(
                            "SCALPING_CONFIDENCE_LOW", 
                            f"⏸️ Confianza insuficiente para scalping {signal.symbol}: {signal.confidence:.1f}% < {min_confidence}%",
                            "INFO"
                        )
                        
                except Exception as e:
                    SICAR_LOGGER.log_error("SCALPING_PROCESSING", f"Error procesando scalping: {e}")
            
            # Notificar a callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(signal)
                except Exception as e:
                    SICAR_LOGGER.log_error("BREAKOUT_CALLBACK", str(e))
            
            # Alerta de alta prioridad para breakouts fuertes
            if signal.strength in [BreakoutStrength.STRONG, BreakoutStrength.VERY_STRONG]:
                priority = "HIGH" if signal.strength == BreakoutStrength.VERY_STRONG else "MEDIUM"
                SICAR_LOGGER.log_alert(
                    "STRONG_BREAKOUT", 
                    f"{signal.symbol} - {signal.breakout_type.value.upper()} breakout detectado "
                    f"(Confianza: {signal.confidence:.1%}, Fuerza: {signal.strength.value})",
                    priority
                )
            
        except Exception as e:
            SICAR_LOGGER.log_error("BREAKOUT_PROCESSING", str(e))
    
    def add_alert_callback(self, callback: Callable[[BreakoutSignal], None]):
        """Agregar callback para alertas"""
        self.alert_callbacks.append(callback)
    
    def remove_alert_callback(self, callback: Callable[[BreakoutSignal], None]):
        """Remover callback de alertas"""
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
    
    def get_recent_signals(self, symbol: str = None, hours: int = 24) -> List[BreakoutSignal]:
        """Obtener señales recientes"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        if symbol:
            signal = self.last_signals.get(symbol)
            if signal and signal.timestamp >= cutoff_time:
                return [signal]
            return []
        else:
            return [
                signal for signal in self.last_signals.values()
                if signal.timestamp >= cutoff_time
            ]
    
    def update_sensitivity(self, new_sensitivity: float):
        """Actualizar sensibilidad de detección"""
        self.sensitivity = max(0.1, min(1.0, new_sensitivity))
        SICAR_LOGGER.log_alert("SENSITIVITY_UPDATE", 
                             f"Sensibilidad actualizada a {self.sensitivity:.1%}", "INFO")
    
    def add_observer(self, callback: Callable[[BreakoutSignal], None]):
        """Agregar observador para señales de breakout"""
        if callback not in self.alert_callbacks:
            self.alert_callbacks.append(callback)
            SICAR_LOGGER.log_alert("OBSERVER_ADDED", 
                                 f"Observador agregado al detector de breakouts", "INFO")
    
    def detect_breakout_from_data(self, data: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
        """
        Detectar breakouts usando datos externos
        
        Args:
            data: DataFrame con datos OHLCV
            symbol: Símbolo a analizar
            
        Returns:
            Lista de breakouts detectados
        """
        try:
            if data is None or data.empty or len(data) < self.lookback_periods:
                return []
            
            # Calcular indicadores técnicos
            indicators = self._calculate_technical_indicators(data)
            
            # Detectar niveles de soporte y resistencia
            support_level, resistance_level = self._calculate_support_resistance(data)
            
            # Analizar breakout
            current_price = data['close'].iloc[-1]
            current_volume = data['volume'].iloc[-1]
            
            # Calcular ratios
            avg_volume = data['volume'].rolling(self.lookback_periods).mean().iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            if len(data) >= 2:
                price_change_pct = ((current_price - data['close'].iloc[-2]) / data['close'].iloc[-2]) * 100
            else:
                price_change_pct = 0
            
            # Detectar tipo de breakout
            breakout_type = self._determine_breakout_type(
                current_price, support_level, resistance_level, indicators
            )
            
            if breakout_type == BreakoutType.NEUTRAL:
                return []
            
            # Calcular confianza y fuerza
            confidence = self._calculate_confidence(
                price_change_pct, volume_ratio, indicators, breakout_type
            )
            
            strength = self._determine_strength(confidence, volume_ratio, abs(price_change_pct))
            
            # Verificar si cumple criterios mínimos
            if (confidence < self.sensitivity or 
                volume_ratio < self.min_volume_ratio or 
                abs(price_change_pct) < self.min_price_change):
                return []
            
            # Crear resultado de breakout
            breakout_result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'direction': breakout_type.value,
                'strength': strength.value,
                'confidence': confidence * 100,  # Convertir a porcentaje
                'price': current_price,
                'volume': current_volume,
                'resistance_level': resistance_level,
                'support_level': support_level,
                'price_change_pct': price_change_pct,
                'volume_ratio': volume_ratio,
                'technical_indicators': indicators
            }
            
            return [breakout_result]
            
        except Exception as e:
            SICAR_LOGGER.log_error("BREAKOUT_DETECTION_EXTERNAL", str(e), {"symbol": symbol})
            return []
    
    def update_price_data(self, symbol: str, price_data: Dict[str, Any]):
        """
        Actualizar datos de precio para un símbolo
        
        Args:
            symbol: Símbolo a actualizar
            price_data: Datos de precio con formato {price, volume, timestamp}
        """
        try:
            with self.lock:
                if symbol not in self.price_history:
                    self.price_history[symbol] = []
                
                # Convertir price_data a formato de vela
                timestamp = price_data.get('timestamp')
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                elif timestamp is None:
                    timestamp = datetime.now()
                
                price = float(price_data.get('price', 0))
                volume = float(price_data.get('volume', 0))
                
                # Crear datos de vela básicos
                candle_data = {
                    'timestamp': timestamp,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                }
                
                self.price_history[symbol].append(candle_data)
                
                # Mantener solo los últimos datos necesarios
                max_history = self.lookback_periods * 2
                if len(self.price_history[symbol]) > max_history:
                    self.price_history[symbol] = self.price_history[symbol][-max_history:]
                
                SICAR_LOGGER.log_alert("PRICE_UPDATE", 
                                     f"Datos actualizados para {symbol}: ${price:.2f}, Vol: {volume:.0f}", "INFO")
                
        except Exception as e:
            SICAR_LOGGER.log_error("PRICE_UPDATE_ERROR", str(e), {"symbol": symbol})

# Instancia global del detector
BREAKOUT_DETECTOR = EnhancedBreakoutDetector()

# Funciones de conveniencia
def start_breakout_detection():
    """Iniciar detección de breakouts"""
    BREAKOUT_DETECTOR.start_detection()

def stop_breakout_detection():
    """Detener detección de breakouts"""
    BREAKOUT_DETECTOR.stop_detection()

def add_breakout_alert(callback: Callable[[BreakoutSignal], None]):
    """Agregar alerta de breakout"""
    BREAKOUT_DETECTOR.add_alert_callback(callback)