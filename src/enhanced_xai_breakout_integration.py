"""
Sistema de Integración XAI-Breakout Mejorado para SICAR
Combina análisis explicable de IA con detección de breakouts para decisiones autónomas
"""

import numpy as np
import pandas as pd
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

# Importar módulos SICAR existentes
from module_xai import generate_dynamic_cognitive_report
from enhanced_breakout_detector import EnhancedBreakoutDetector, BreakoutSignal, BreakoutType, BreakoutStrength
from enhanced_logger import SICAR_LOGGER
from enhanced_config import SicarConfig

logger = logging.getLogger(__name__)

@dataclass
class XAIBreakoutDecision:
    """Decisión integrada XAI-Breakout"""
    symbol: str
    timestamp: datetime
    decision: str  # BUY, SELL, HOLD
    confidence: float
    xai_confidence: float
    breakout_confidence: float
    strategy: str
    reasoning: str
    risk_level: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None

class DecisionConfidenceLevel(Enum):
    """Niveles de confianza para decisiones"""
    VERY_HIGH = "very_high"  # >90%
    HIGH = "high"           # 80-90%
    MEDIUM = "medium"       # 60-80%
    LOW = "low"            # 40-60%
    VERY_LOW = "very_low"  # <40%

class RiskLevel(Enum):
    """Niveles de riesgo"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

class EnhancedXAIBreakoutSystem:
    """Sistema integrado XAI-Breakout para decisiones autónomas"""
    
    def __init__(self, metacontroller=None, regime_classifier=None, causal_cartographer=None):
        self.metacontroller = metacontroller
        self.regime_classifier = regime_classifier
        self.causal_cartographer = causal_cartographer
        
        # Configuración del sistema
        self.config = getattr(SicarConfig, 'XAI_BREAKOUT_CONFIG', {
            'min_confidence_threshold': 0.70,
            'autonomous_trading_enabled': True,
            'risk_management_enabled': True,
            'max_position_size': 0.1,  # 10% del capital
            'stop_loss_pct': 0.02,     # 2%
            'take_profit_pct': 0.04    # 4%
        })
        
        # Detector de breakouts mejorado
        self.breakout_detector = EnhancedBreakoutDetector()
        
        # Historial de decisiones
        self.decision_history: List[XAIBreakoutDecision] = []
        self.active_positions: Dict[str, XAIBreakoutDecision] = {}
        
        # Control de threading
        self.running = False
        self.analysis_thread = None
        self.lock = threading.RLock()
        
        # Callbacks para decisiones
        self.decision_callbacks: List[callable] = []
        
        SICAR_LOGGER.log_alert("XAI_BREAKOUT_INIT", "Sistema XAI-Breakout inicializado", "INFO")
    
    def start_system(self):
        """Iniciar el sistema integrado"""
        if not self.running:
            self.running = True
            
            # Iniciar detector de breakouts
            self.breakout_detector.start_detection()
            
            # Agregar callback para procesar señales de breakout
            self.breakout_detector.add_alert_callback(self._process_breakout_with_xai)
            
            # Iniciar hilo de análisis continuo
            self.analysis_thread = threading.Thread(target=self._continuous_analysis_loop, daemon=True)
            self.analysis_thread.start()
            
            SICAR_LOGGER.log_alert("XAI_BREAKOUT_START", "Sistema XAI-Breakout iniciado", "INFO")
    
    def stop_system(self):
        """Detener el sistema integrado"""
        self.running = False
        
        # Detener detector de breakouts
        self.breakout_detector.stop_detection()
        
        if self.analysis_thread:
            self.analysis_thread.join(timeout=5)
        
        SICAR_LOGGER.log_alert("XAI_BREAKOUT_STOP", "Sistema XAI-Breakout detenido", "INFO")
    
    def _process_breakout_with_xai(self, breakout_signal: BreakoutSignal):
        """Procesar señal de breakout con análisis XAI"""
        try:
            with self.lock:
                # Obtener datos de mercado actuales
                market_data = self._get_market_data(breakout_signal.symbol)
                if market_data is None or market_data.empty:
                    return
                
                # Generar decisión XAI
                xai_decision = self._generate_xai_decision(breakout_signal, market_data)
                
                # Combinar análisis de breakout y XAI
                integrated_decision = self._integrate_breakout_xai_analysis(
                    breakout_signal, xai_decision, market_data
                )
                
                # Evaluar si ejecutar decisión autónoma
                if self._should_execute_autonomous_decision(integrated_decision):
                    self._execute_autonomous_decision(integrated_decision)
                
                # Registrar decisión
                self.decision_history.append(integrated_decision)
                
                # Notificar callbacks
                for callback in self.decision_callbacks:
                    try:
                        callback(integrated_decision)
                    except Exception as e:
                        SICAR_LOGGER.log_error("XAI_CALLBACK", str(e))
                
                SICAR_LOGGER.log_alert("XAI_DECISION", 
                    f"Decisión XAI-Breakout: {integrated_decision.symbol} -> {integrated_decision.decision} "
                    f"(Confianza: {integrated_decision.confidence:.1%})", "INFO")
        
        except Exception as e:
            SICAR_LOGGER.log_error("XAI_BREAKOUT_PROCESS", str(e))
    
    def _generate_xai_decision(self, breakout_signal: BreakoutSignal, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Generar decisión usando análisis XAI"""
        try:
            # Determinar decisión base según breakout
            if breakout_signal.breakout_type == BreakoutType.BULLISH:
                base_decision = "BUY"
                base_strategy = "breakout_bullish"
            elif breakout_signal.breakout_type == BreakoutType.BEARISH:
                base_decision = "SELL"
                base_strategy = "breakout_bearish"
            else:
                base_decision = "HOLD"
                base_strategy = "neutral"
            
            # Generar reporte cognitivo dinámico
            if (self.metacontroller and self.regime_classifier and 
                self.causal_cartographer and not market_data.empty):
                
                cognitive_report = generate_dynamic_cognitive_report(
                    metacontroller=self.metacontroller,
                    regime_classifier=self.regime_classifier,
                    causal_cartographer=self.causal_cartographer,
                    market_data=market_data,
                    decision=base_decision,
                    strategy=base_strategy,
                    confidence=breakout_signal.confidence,
                    additional_context={
                        'breakout_strength': breakout_signal.strength.value,
                        'price_change': f"{breakout_signal.price_change_pct:.2f}%",
                        'volume_ratio': f"{breakout_signal.volume_ratio:.2f}x"
                    }
                )
                
                # Extraer confianza XAI del reporte
                xai_confidence = self._extract_xai_confidence(cognitive_report)
                
                return {
                    'decision': base_decision,
                    'strategy': base_strategy,
                    'confidence': xai_confidence,
                    'reasoning': cognitive_report,
                    'market_regime': 'unknown'  # Se extraería del reporte
                }
            else:
                # Fallback sin módulos XAI completos
                return {
                    'decision': base_decision,
                    'strategy': base_strategy,
                    'confidence': breakout_signal.confidence,
                    'reasoning': f"Decisión basada en breakout {breakout_signal.breakout_type.value}",
                    'market_regime': 'unknown'
                }
        
        except Exception as e:
            SICAR_LOGGER.log_error("XAI_DECISION_GEN", str(e))
            return {
                'decision': 'HOLD',
                'strategy': 'error_fallback',
                'confidence': 0.5,
                'reasoning': f"Error en análisis XAI: {str(e)}",
                'market_regime': 'error'
            }
    
    def _integrate_breakout_xai_analysis(self, breakout_signal: BreakoutSignal, 
                                       xai_decision: Dict[str, Any], 
                                       market_data: pd.DataFrame) -> XAIBreakoutDecision:
        """Integrar análisis de breakout y XAI para decisión final"""
        try:
            # Combinar confianzas usando promedio ponderado
            breakout_weight = 0.6  # 60% peso al breakout
            xai_weight = 0.4       # 40% peso al XAI
            
            combined_confidence = (
                breakout_signal.confidence * breakout_weight + 
                xai_decision['confidence'] * xai_weight
            )
            
            # Determinar decisión final
            final_decision = self._determine_final_decision(
                breakout_signal, xai_decision, combined_confidence
            )
            
            # Calcular niveles de riesgo y gestión
            risk_levels = self._calculate_risk_management(
                breakout_signal, market_data, combined_confidence
            )
            
            # Determinar nivel de confianza
            confidence_level = self._get_confidence_level(combined_confidence)
            
            # Crear decisión integrada
            integrated_decision = XAIBreakoutDecision(
                symbol=breakout_signal.symbol,
                timestamp=datetime.now(),
                decision=final_decision,
                confidence=combined_confidence,
                xai_confidence=xai_decision['confidence'],
                breakout_confidence=breakout_signal.confidence,
                strategy=f"{xai_decision['strategy']}_integrated",
                reasoning=self._build_integrated_reasoning(breakout_signal, xai_decision),
                risk_level=confidence_level.value,
                entry_price=breakout_signal.price,
                stop_loss=risk_levels.get('stop_loss'),
                take_profit=risk_levels.get('take_profit'),
                position_size=risk_levels.get('position_size')
            )
            
            return integrated_decision
        
        except Exception as e:
            SICAR_LOGGER.log_error("XAI_INTEGRATION", str(e))
            # Fallback a decisión básica
            return XAIBreakoutDecision(
                symbol=breakout_signal.symbol,
                timestamp=datetime.now(),
                decision="HOLD",
                confidence=0.5,
                xai_confidence=0.5,
                breakout_confidence=breakout_signal.confidence,
                strategy="error_fallback",
                reasoning=f"Error en integración: {str(e)}",
                risk_level="conservative"
            )
    
    def _determine_final_decision(self, breakout_signal: BreakoutSignal, 
                                xai_decision: Dict[str, Any], 
                                combined_confidence: float) -> str:
        """Determinar decisión final basada en análisis combinado"""
        
        # Si la confianza es muy baja, mantener HOLD
        if combined_confidence < self.config['min_confidence_threshold']:
            return "HOLD"
        
        # Si ambos análisis coinciden, usar esa decisión
        breakout_decision = "BUY" if breakout_signal.breakout_type == BreakoutType.BULLISH else "SELL"
        if breakout_decision == xai_decision['decision']:
            return breakout_decision
        
        # Si hay conflicto, usar el análisis con mayor confianza
        if breakout_signal.confidence > xai_decision['confidence']:
            return breakout_decision
        else:
            return xai_decision['decision']
    
    def _calculate_risk_management(self, breakout_signal: BreakoutSignal, 
                                 market_data: pd.DataFrame, 
                                 confidence: float) -> Dict[str, float]:
        """Calcular niveles de gestión de riesgo"""
        try:
            current_price = breakout_signal.price
            
            # Ajustar tamaño de posición según confianza
            base_position_size = self.config['max_position_size']
            confidence_multiplier = min(confidence / 0.8, 1.0)  # Máximo en 80% confianza
            position_size = base_position_size * confidence_multiplier
            
            # Calcular stop loss y take profit
            if breakout_signal.breakout_type == BreakoutType.BULLISH:
                stop_loss = current_price * (1 - self.config['stop_loss_pct'])
                take_profit = current_price * (1 + self.config['take_profit_pct'])
            else:
                stop_loss = current_price * (1 + self.config['stop_loss_pct'])
                take_profit = current_price * (1 - self.config['take_profit_pct'])
            
            return {
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit
            }
        
        except Exception as e:
            SICAR_LOGGER.log_error("RISK_CALC", str(e))
            return {
                'position_size': 0.05,  # Posición conservadora
                'stop_loss': breakout_signal.price * 0.98,
                'take_profit': breakout_signal.price * 1.02
            }
    
    def _should_execute_autonomous_decision(self, decision: XAIBreakoutDecision) -> bool:
        """Evaluar si ejecutar decisión de forma autónoma"""
        if not self.config.get('autonomous_trading_enabled', False):
            return False
        
        # Solo ejecutar si la confianza es alta
        if decision.confidence < self.config['min_confidence_threshold']:
            return False
        
        # No ejecutar si ya hay posición activa para este símbolo
        if decision.symbol in self.active_positions:
            return False
        
        # Verificar que la decisión no sea HOLD
        if decision.decision == "HOLD":
            return False
        
        return True
    
    def _execute_autonomous_decision(self, decision: XAIBreakoutDecision):
        """Ejecutar decisión de forma autónoma"""
        try:
            SICAR_LOGGER.log_alert("AUTONOMOUS_EXECUTION", 
                f"🤖 EJECUTANDO DECISIÓN AUTÓNOMA: {decision.symbol} -> {decision.decision} "
                f"(Confianza: {decision.confidence:.1%})", "HIGH")
            
            # Registrar posición activa
            self.active_positions[decision.symbol] = decision
            
            # Aquí se integraría con el sistema de trading real
            # Por ahora solo registramos la decisión
            
            # Programar monitoreo de la posición
            self._schedule_position_monitoring(decision)
        
        except Exception as e:
            SICAR_LOGGER.log_error("AUTONOMOUS_EXEC", str(e))
    
    def _schedule_position_monitoring(self, decision: XAIBreakoutDecision):
        """Programar monitoreo de posición activa"""
        def monitor_position():
            try:
                # Monitorear por 1 hora o hasta que se cierre
                start_time = datetime.now()
                while (datetime.now() - start_time).seconds < 3600:
                    if decision.symbol not in self.active_positions:
                        break
                    
                    # Verificar condiciones de salida
                    current_data = self._get_market_data(decision.symbol)
                    if current_data is not None and not current_data.empty:
                        current_price = current_data['Close'].iloc[-1]
                        
                        # Verificar stop loss y take profit
                        should_close = self._check_exit_conditions(decision, current_price)
                        if should_close:
                            self._close_position(decision, current_price)
                            break
                    
                    time.sleep(30)  # Verificar cada 30 segundos
            
            except Exception as e:
                SICAR_LOGGER.log_error("POSITION_MONITOR", str(e))
        
        # Ejecutar monitoreo en hilo separado
        monitor_thread = threading.Thread(target=monitor_position, daemon=True)
        monitor_thread.start()
    
    def _check_exit_conditions(self, decision: XAIBreakoutDecision, current_price: float) -> bool:
        """Verificar condiciones de salida de posición"""
        if decision.decision == "BUY":
            # Para posición larga
            if current_price <= decision.stop_loss or current_price >= decision.take_profit:
                return True
        elif decision.decision == "SELL":
            # Para posición corta
            if current_price >= decision.stop_loss or current_price <= decision.take_profit:
                return True
        
        return False
    
    def _close_position(self, decision: XAIBreakoutDecision, exit_price: float):
        """Cerrar posición activa"""
        try:
            # Calcular P&L
            if decision.decision == "BUY":
                pnl_pct = ((exit_price - decision.entry_price) / decision.entry_price) * 100
            else:
                pnl_pct = ((decision.entry_price - exit_price) / decision.entry_price) * 100
            
            SICAR_LOGGER.log_alert("POSITION_CLOSED", 
                f"🔒 POSICIÓN CERRADA: {decision.symbol} -> P&L: {pnl_pct:.2f}% "
                f"(Entrada: {decision.entry_price:.3f}, Salida: {exit_price:.3f})", "INFO")
            
            # Remover de posiciones activas
            if decision.symbol in self.active_positions:
                del self.active_positions[decision.symbol]
        
        except Exception as e:
            SICAR_LOGGER.log_error("POSITION_CLOSE", str(e))
    
    def _continuous_analysis_loop(self):
        """Bucle de análisis continuo"""
        while self.running:
            try:
                # Análisis cada 60 segundos
                time.sleep(60)
                
                # Revisar posiciones activas
                self._review_active_positions()
                
                # Limpiar historial antiguo (mantener últimas 24 horas)
                self._cleanup_old_decisions()
            
            except Exception as e:
                SICAR_LOGGER.log_error("CONTINUOUS_ANALYSIS", str(e))
                time.sleep(30)
    
    def _review_active_positions(self):
        """Revisar posiciones activas"""
        for symbol, position in list(self.active_positions.items()):
            try:
                # Verificar si la posición debe cerrarse por tiempo
                time_elapsed = (datetime.now() - position.timestamp).seconds
                if time_elapsed > 3600:  # 1 hora máximo
                    SICAR_LOGGER.log_alert("POSITION_TIMEOUT", 
                        f"⏰ Cerrando posición por timeout: {symbol}", "WARNING")
                    del self.active_positions[symbol]
            
            except Exception as e:
                SICAR_LOGGER.log_error("POSITION_REVIEW", str(e))
    
    def _cleanup_old_decisions(self):
        """Limpiar decisiones antiguas del historial"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.decision_history = [
            decision for decision in self.decision_history 
            if decision.timestamp > cutoff_time
        ]
    
    def _get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Obtener datos de mercado para un símbolo"""
        try:
            # Aquí se integraría con el proveedor de datos real
            # Por ahora retornamos None para evitar errores
            return None
        except Exception as e:
            SICAR_LOGGER.log_error("MARKET_DATA", str(e))
            return None
    
    def _extract_xai_confidence(self, cognitive_report: str) -> float:
        """Extraer confianza del reporte cognitivo XAI"""
        try:
            # Buscar patrones de confianza en el reporte
            import re
            confidence_patterns = [
                r'confianza[:\s]+(\d+(?:\.\d+)?)%',
                r'confidence[:\s]+(\d+(?:\.\d+)?)%',
                r'(\d+(?:\.\d+)?)%\s+confianza'
            ]
            
            for pattern in confidence_patterns:
                match = re.search(pattern, cognitive_report.lower())
                if match:
                    return float(match.group(1)) / 100.0
            
            # Si no encuentra patrón, usar confianza por defecto
            return 0.75
        
        except Exception:
            return 0.75
    
    def _get_confidence_level(self, confidence: float) -> DecisionConfidenceLevel:
        """Obtener nivel de confianza categórico"""
        if confidence >= 0.9:
            return DecisionConfidenceLevel.VERY_HIGH
        elif confidence >= 0.8:
            return DecisionConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return DecisionConfidenceLevel.MEDIUM
        elif confidence >= 0.4:
            return DecisionConfidenceLevel.LOW
        else:
            return DecisionConfidenceLevel.VERY_LOW
    
    def _build_integrated_reasoning(self, breakout_signal: BreakoutSignal, 
                                  xai_decision: Dict[str, Any]) -> str:
        """Construir razonamiento integrado"""
        reasoning = f"""
🔍 ANÁLISIS INTEGRADO XAI-BREAKOUT:

📊 Breakout Detectado:
- Tipo: {breakout_signal.breakout_type.value.upper()}
- Fuerza: {breakout_signal.strength.value}
- Confianza: {breakout_signal.confidence:.1%}
- Cambio precio: {breakout_signal.price_change_pct:.2f}%
- Ratio volumen: {breakout_signal.volume_ratio:.2f}x

🧠 Análisis XAI:
- Decisión: {xai_decision['decision']}
- Estrategia: {xai_decision['strategy']}
- Confianza: {xai_decision['confidence']:.1%}

💡 Razonamiento XAI:
{xai_decision['reasoning'][:200]}...
        """
        return reasoning.strip()
    
    def add_decision_callback(self, callback: callable):
        """Agregar callback para decisiones"""
        self.decision_callbacks.append(callback)
    
    def get_recent_decisions(self, hours: int = 1) -> List[XAIBreakoutDecision]:
        """Obtener decisiones recientes"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            decision for decision in self.decision_history 
            if decision.timestamp > cutoff_time
        ]
    
    def get_active_positions(self) -> Dict[str, XAIBreakoutDecision]:
        """Obtener posiciones activas"""
        return self.active_positions.copy()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado del sistema"""
        return {
            'running': self.running,
            'breakout_detector_active': self.breakout_detector.running,
            'active_positions': len(self.active_positions),
            'decisions_last_hour': len(self.get_recent_decisions(1)),
            'autonomous_trading': self.config.get('autonomous_trading_enabled', False),
            'min_confidence': self.config['min_confidence_threshold']
        }

# Instancia global del sistema integrado
XAI_BREAKOUT_SYSTEM = None

def initialize_xai_breakout_system(metacontroller=None, regime_classifier=None, causal_cartographer=None):
    """Inicializar sistema XAI-Breakout"""
    global XAI_BREAKOUT_SYSTEM
    XAI_BREAKOUT_SYSTEM = EnhancedXAIBreakoutSystem(
        metacontroller=metacontroller,
        regime_classifier=regime_classifier,
        causal_cartographer=causal_cartographer
    )
    return XAI_BREAKOUT_SYSTEM

def start_xai_breakout_system():
    """Iniciar sistema XAI-Breakout"""
    if XAI_BREAKOUT_SYSTEM:
        XAI_BREAKOUT_SYSTEM.start_system()

def stop_xai_breakout_system():
    """Detener sistema XAI-Breakout"""
    if XAI_BREAKOUT_SYSTEM:
        XAI_BREAKOUT_SYSTEM.stop_system()