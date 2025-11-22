"""
Motor de Decisiones Autónomas para SICAR
Integra análisis XAI, reconocimiento de patrones y detección de breakouts
para tomar decisiones automáticas de entrada y salida
"""

import asyncio
import json
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from enhanced_logger import SICAR_LOGGER
from module_xai import generate_dynamic_cognitive_report
from enhanced_xai_breakout_integration import EnhancedXAIBreakoutSystem, XAIBreakoutDecision, DecisionConfidenceLevel, RiskLevel
from advanced_pattern_recognition import PATTERN_RECOGNITION_SYSTEM, PatternSignal, PatternType, PatternStrength

logger = logging.getLogger(__name__)

class DecisionType(Enum):
    """Tipos de decisiones de trading"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"
    SCALE_IN = "SCALE_IN"
    SCALE_OUT = "SCALE_OUT"

class PositionType(Enum):
    """Tipos de posiciones"""
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"

class ExecutionStatus(Enum):
    """Estados de ejecución"""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"

@dataclass
class TradingSignal:
    """Señal de trading generada por el sistema autónomo"""
    symbol: str
    timestamp: datetime
    decision_type: DecisionType
    confidence: float
    entry_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    position_size: float
    risk_reward_ratio: float
    reasoning: str
    sources: List[str]  # XAI, Pattern, Breakout, etc.
    urgency: int  # 1-10, donde 10 es máxima urgencia
    validity_duration: int  # minutos de validez
    
class PositionManager:
    """Gestor de posiciones activas"""
    
    def __init__(self):
        self.positions = {}  # symbol -> position_info
        self.position_history = []
        self.max_positions = 5
        self.max_risk_per_trade = 0.02  # 2% del capital por operación
        self.total_risk_limit = 0.10    # 10% riesgo total máximo
        
    def can_open_position(self, symbol: str, position_size: float) -> bool:
        """Verificar si se puede abrir una nueva posición"""
        try:
            # Verificar límite de posiciones
            if len(self.positions) >= self.max_positions:
                return False
            
            # Verificar si ya hay posición en este símbolo
            if symbol in self.positions:
                return False
            
            # Verificar límite de riesgo
            current_risk = sum(pos.get('risk_amount', 0) for pos in self.positions.values())
            new_risk = position_size * self.max_risk_per_trade
            
            if current_risk + new_risk > self.total_risk_limit:
                return False
            
            return True
            
        except Exception as e:
            SICAR_LOGGER.log_error("POSITION_CHECK", f"Error verificando posición: {e}")
            return False
    
    def open_position(self, signal: TradingSignal) -> bool:
        """Abrir nueva posición"""
        try:
            if not self.can_open_position(signal.symbol, signal.position_size):
                return False
            
            position_info = {
                'symbol': signal.symbol,
                'type': PositionType.LONG if signal.decision_type == DecisionType.BUY else PositionType.SHORT,
                'entry_price': signal.entry_price,
                'size': signal.position_size,
                'target_price': signal.target_price,
                'stop_loss': signal.stop_loss,
                'timestamp': signal.timestamp,
                'risk_amount': signal.position_size * self.max_risk_per_trade,
                'reasoning': signal.reasoning,
                'status': 'OPEN'
            }
            
            self.positions[signal.symbol] = position_info
            
            SICAR_LOGGER.log_alert("POSITION_OPENED", 
                f"Posición abierta: {signal.symbol} {position_info['type'].value} @ {signal.entry_price}", "INFO")
            
            return True
            
        except Exception as e:
            SICAR_LOGGER.log_error("POSITION_OPEN", f"Error abriendo posición: {e}")
            return False
    
    def close_position(self, symbol: str, exit_price: float, reason: str) -> bool:
        """Cerrar posición existente"""
        try:
            if symbol not in self.positions:
                return False
            
            position = self.positions[symbol]
            
            # Calcular P&L
            if position['type'] == PositionType.LONG:
                pnl = (exit_price - position['entry_price']) / position['entry_price']
            else:
                pnl = (position['entry_price'] - exit_price) / position['entry_price']
            
            pnl_amount = pnl * position['size']
            
            # Guardar en historial
            closed_position = position.copy()
            closed_position.update({
                'exit_price': exit_price,
                'exit_timestamp': datetime.now(),
                'pnl': pnl,
                'pnl_amount': pnl_amount,
                'exit_reason': reason,
                'status': 'CLOSED'
            })
            
            self.position_history.append(closed_position)
            
            # Remover de posiciones activas
            del self.positions[symbol]
            
            SICAR_LOGGER.log_alert("POSITION_CLOSED", 
                f"Posición cerrada: {symbol} @ {exit_price}, P&L: {pnl:.2%} ({reason})", "INFO")
            
            return True
            
        except Exception as e:
            SICAR_LOGGER.log_error("POSITION_CLOSE", f"Error cerrando posición: {e}")
            return False
    
    def get_position_status(self) -> Dict[str, Any]:
        """Obtener estado de todas las posiciones"""
        return {
            'active_positions': len(self.positions),
            'positions': self.positions,
            'total_risk': sum(pos.get('risk_amount', 0) for pos in self.positions.values()),
            'available_slots': self.max_positions - len(self.positions),
            'recent_trades': self.position_history[-10:] if self.position_history else []
        }

class AutonomousDecisionEngine:
    """Motor principal de decisiones autónomas"""
    
    def __init__(self):
        self.is_running = False
        self.position_manager = PositionManager()
        self.xai_breakout_system = EnhancedXAIBreakoutSystem()
        self.decision_history = []
        self.performance_metrics = {}
        
        # Configuración del motor
        self.config = {
            'decision_interval': 30,  # segundos entre decisiones
            'min_confidence_threshold': 0.70,
            'max_decisions_per_hour': 10,
            'enable_autonomous_execution': True,
            'risk_management_strict': True,
            'pattern_weight': 0.3,
            'xai_weight': 0.4,
            'breakout_weight': 0.3,
            'symbols': ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT']
        }
        
        # Contadores y límites
        self.decisions_this_hour = 0
        self.last_hour_reset = datetime.now()
        
        # Datos de mercado (simulados para el ejemplo)
        self.market_data = {}
        
        SICAR_LOGGER.log_alert("AUTONOMOUS_ENGINE_INIT", 
                              "Motor de decisiones autónomas inicializado", "INFO")
    
    async def start_autonomous_trading(self):
        """Iniciar el sistema de trading autónomo"""
        try:
            if self.is_running:
                SICAR_LOGGER.log_warning("AUTONOMOUS_START", "El sistema ya está ejecutándose")
                return
            
            self.is_running = True
            
            # Iniciar sistema XAI-Breakout
            self.xai_breakout_system.start_system()
            
            SICAR_LOGGER.log_alert("AUTONOMOUS_START", 
                                  "Sistema de trading autónomo iniciado", "INFO")
            
            # Bucle principal de decisiones
            while self.is_running:
                try:
                    await self._decision_cycle()
                    await asyncio.sleep(self.config['decision_interval'])
                    
                except Exception as e:
                    SICAR_LOGGER.log_error("DECISION_CYCLE", f"Error en ciclo de decisiones: {e}")
                    await asyncio.sleep(5)  # Pausa corta antes de reintentar
            
        except Exception as e:
            SICAR_LOGGER.log_error("AUTONOMOUS_START", f"Error iniciando sistema autónomo: {e}")
            self.is_running = False
    
    async def stop_autonomous_trading(self):
        """Detener el sistema de trading autónomo"""
        try:
            self.is_running = False
            
            # Detener sistema XAI-Breakout
            await self.xai_breakout_system.stop()
            
            SICAR_LOGGER.log_alert("AUTONOMOUS_STOP", 
                                  "Sistema de trading autónomo detenido", "INFO")
            
        except Exception as e:
            SICAR_LOGGER.log_error("AUTONOMOUS_STOP", f"Error deteniendo sistema: {e}")
    
    async def _decision_cycle(self):
        """Ciclo principal de toma de decisiones"""
        try:
            # Resetear contador horario si es necesario
            self._reset_hourly_counters()
            
            # Verificar límites
            if self.decisions_this_hour >= self.config['max_decisions_per_hour']:
                return
            
            # Analizar cada símbolo
            for symbol in self.config['symbols']:
                try:
                    await self._analyze_symbol(symbol)
                except Exception as e:
                    SICAR_LOGGER.log_error("SYMBOL_ANALYSIS", f"Error analizando {symbol}: {e}")
            
            # Gestionar posiciones existentes
            await self._manage_existing_positions()
            
        except Exception as e:
            SICAR_LOGGER.log_error("DECISION_CYCLE", f"Error en ciclo de decisiones: {e}")
    
    async def _analyze_symbol(self, symbol: str):
        """Analizar un símbolo específico para decisiones"""
        try:
            # Obtener datos de mercado (simulado)
            market_data = await self._get_market_data(symbol)
            if market_data is None or market_data.empty:
                return
            
            # Análisis XAI
            xai_analysis = await self._get_xai_analysis(symbol, market_data)
            
            # Análisis de patrones
            pattern_analysis = await self._get_pattern_analysis(symbol, market_data)
            
            # Análisis de breakouts
            breakout_analysis = await self._get_breakout_analysis(symbol, market_data)
            
            # Integrar análisis y generar decisión
            decision = await self._integrate_analyses(
                symbol, xai_analysis, pattern_analysis, breakout_analysis, market_data
            )
            
            # Ejecutar decisión si es válida
            if decision and decision.confidence >= self.config['min_confidence_threshold']:
                await self._execute_decision(decision)
            
        except Exception as e:
            SICAR_LOGGER.log_error("SYMBOL_ANALYSIS", f"Error analizando {symbol}: {e}")
    
    async def _get_xai_analysis(self, symbol: str, data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Obtener análisis XAI para el símbolo"""
        try:
            # Por ahora retornamos análisis por defecto hasta que los módulos XAI estén completamente configurados
            return {
                'decision': 'HOLD',
                'confidence': 0.6,
                'reasoning': 'Análisis XAI no disponible - usando valores por defecto',
                'market_regime': 'unknown',
                'risk_level': 'medium'
            }
            
        except Exception as e:
            SICAR_LOGGER.log_error("XAI_ANALYSIS", f"Error en análisis XAI: {e}")
            return None
    
    async def _get_pattern_analysis(self, symbol: str, data: pd.DataFrame) -> Optional[List[PatternSignal]]:
        """Obtener análisis de patrones para el símbolo"""
        try:
            patterns = PATTERN_RECOGNITION_SYSTEM.detect_patterns(data, symbol)
            return patterns if patterns else None
            
        except Exception as e:
            SICAR_LOGGER.log_error("PATTERN_ANALYSIS", f"Error en análisis de patrones: {e}")
            return None
    
    async def _get_breakout_analysis(self, symbol: str, data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Obtener análisis de breakouts para el símbolo"""
        try:
            # Simular análisis de breakout (integrar con sistema real)
            current_price = data['Close'].iloc[-1] if not data.empty else 0
            
            # Calcular niveles de soporte y resistencia
            recent_highs = data['High'].rolling(20).max().iloc[-1]
            recent_lows = data['Low'].rolling(20).min().iloc[-1]
            
            # Determinar si hay breakout
            breakout_type = None
            confidence = 0.5
            
            if current_price > recent_highs * 1.001:  # Breakout alcista
                breakout_type = "BULLISH"
                confidence = min(0.9, 0.6 + (current_price - recent_highs) / recent_highs * 10)
            elif current_price < recent_lows * 0.999:  # Breakout bajista
                breakout_type = "BEARISH"
                confidence = min(0.9, 0.6 + (recent_lows - current_price) / recent_lows * 10)
            
            return {
                'breakout_type': breakout_type,
                'confidence': confidence,
                'support_level': recent_lows,
                'resistance_level': recent_highs,
                'current_price': current_price
            } if breakout_type else None
            
        except Exception as e:
            SICAR_LOGGER.log_error("BREAKOUT_ANALYSIS", f"Error en análisis de breakouts: {e}")
            return None
    
    async def _integrate_analyses(self, symbol: str, xai_analysis: Optional[Dict], 
                                pattern_analysis: Optional[List[PatternSignal]], 
                                breakout_analysis: Optional[Dict], 
                                market_data: pd.DataFrame) -> Optional[TradingSignal]:
        """Integrar todos los análisis para generar una decisión final"""
        try:
            if market_data.empty:
                return None
            
            current_price = market_data['Close'].iloc[-1]
            
            # Inicializar scores
            buy_score = 0.0
            sell_score = 0.0
            confidence_factors = []
            reasoning_parts = []
            sources = []
            
            # Integrar análisis XAI
            if xai_analysis:
                xai_weight = self.config['xai_weight']
                xai_confidence = xai_analysis['confidence']
                
                if xai_analysis['decision'] == 'BUY':
                    buy_score += xai_weight * xai_confidence
                elif xai_analysis['decision'] == 'SELL':
                    sell_score += xai_weight * xai_confidence
                
                confidence_factors.append(xai_confidence)
                reasoning_parts.append(f"XAI: {xai_analysis['reasoning'][:100]}")
                sources.append("XAI")
            
            # Integrar análisis de patrones
            if pattern_analysis:
                pattern_weight = self.config['pattern_weight']
                
                for pattern in pattern_analysis:
                    pattern_confidence = pattern.confidence
                    
                    if pattern.pattern_type in [PatternType.BULLISH_REVERSAL, PatternType.CONTINUATION_BULLISH]:
                        buy_score += pattern_weight * pattern_confidence * 0.5  # 0.5 porque puede haber múltiples patrones
                    elif pattern.pattern_type in [PatternType.BEARISH_REVERSAL, PatternType.CONTINUATION_BEARISH]:
                        sell_score += pattern_weight * pattern_confidence * 0.5
                    
                    confidence_factors.append(pattern_confidence)
                    reasoning_parts.append(f"Patrón {pattern.pattern_type.value}: {pattern_confidence:.2f}")
                
                sources.append("PATTERNS")
            
            # Integrar análisis de breakouts
            if breakout_analysis:
                breakout_weight = self.config['breakout_weight']
                breakout_confidence = breakout_analysis['confidence']
                
                if breakout_analysis['breakout_type'] == 'BULLISH':
                    buy_score += breakout_weight * breakout_confidence
                elif breakout_analysis['breakout_type'] == 'BEARISH':
                    sell_score += breakout_weight * breakout_confidence
                
                confidence_factors.append(breakout_confidence)
                reasoning_parts.append(f"Breakout {breakout_analysis['breakout_type']}: {breakout_confidence:.2f}")
                sources.append("BREAKOUT")
            
            # Determinar decisión final
            if not confidence_factors:
                return None
            
            final_confidence = np.mean(confidence_factors)
            
            # Verificar si hay señal clara
            if buy_score > sell_score and buy_score > 0.5:
                decision_type = DecisionType.BUY
                final_score = buy_score
            elif sell_score > buy_score and sell_score > 0.5:
                decision_type = DecisionType.SELL
                final_score = sell_score
            else:
                return None  # No hay señal clara
            
            # Calcular parámetros de la operación
            position_size = self._calculate_position_size(symbol, final_confidence)
            target_price, stop_loss = self._calculate_targets(
                current_price, decision_type, final_confidence
            )
            risk_reward = self._calculate_risk_reward(current_price, target_price, stop_loss)
            
            # Crear señal de trading
            signal = TradingSignal(
                symbol=symbol,
                timestamp=datetime.now(),
                decision_type=decision_type,
                confidence=final_confidence,
                entry_price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                position_size=position_size,
                risk_reward_ratio=risk_reward,
                reasoning=" | ".join(reasoning_parts),
                sources=sources,
                urgency=min(10, int(final_confidence * 10)),
                validity_duration=30  # 30 minutos de validez
            )
            
            return signal
            
        except Exception as e:
            SICAR_LOGGER.log_error("ANALYSIS_INTEGRATION", f"Error integrando análisis: {e}")
            return None
    
    async def _execute_decision(self, signal: TradingSignal):
        """Ejecutar una decisión de trading"""
        try:
            # Verificar si la ejecución autónoma está habilitada
            if not self.config['enable_autonomous_execution']:
                SICAR_LOGGER.log_alert("DECISION_SIMULATED", 
                    f"Decisión simulada: {signal.symbol} {signal.decision_type.value} @ {signal.entry_price:.4f} "
                    f"(Confianza: {signal.confidence:.2f})", "INFO")
                return
            
            # Verificar límites de decisiones
            if self.decisions_this_hour >= self.config['max_decisions_per_hour']:
                return
            
            # Ejecutar según el tipo de decisión
            executed = False
            
            if signal.decision_type == DecisionType.BUY:
                executed = self.position_manager.open_position(signal)
            elif signal.decision_type == DecisionType.SELL:
                # Si hay posición larga, cerrarla
                if signal.symbol in self.position_manager.positions:
                    executed = self.position_manager.close_position(
                        signal.symbol, signal.entry_price, "Señal de venta autónoma"
                    )
                else:
                    # Abrir posición corta (si está permitido)
                    executed = self.position_manager.open_position(signal)
            
            if executed:
                self.decisions_this_hour += 1
                self.decision_history.append(signal)
                
                SICAR_LOGGER.log_alert("DECISION_EXECUTED", 
                    f"Decisión ejecutada: {signal.symbol} {signal.decision_type.value} @ {signal.entry_price:.4f} "
                    f"(Confianza: {signal.confidence:.2f}, Fuentes: {', '.join(signal.sources)})", "INFO")
            
        except Exception as e:
            SICAR_LOGGER.log_error("DECISION_EXECUTION", f"Error ejecutando decisión: {e}")
    
    async def _manage_existing_positions(self):
        """Gestionar posiciones existentes (stop loss, take profit, etc.)"""
        try:
            for symbol, position in list(self.position_manager.positions.items()):
                try:
                    # Obtener precio actual
                    current_data = await self._get_market_data(symbol)
                    if current_data is None or current_data.empty:
                        continue
                    
                    current_price = current_data['Close'].iloc[-1]
                    
                    # Verificar stop loss
                    if position['stop_loss']:
                        if position['type'] == PositionType.LONG and current_price <= position['stop_loss']:
                            self.position_manager.close_position(symbol, current_price, "Stop Loss")
                            continue
                        elif position['type'] == PositionType.SHORT and current_price >= position['stop_loss']:
                            self.position_manager.close_position(symbol, current_price, "Stop Loss")
                            continue
                    
                    # Verificar take profit
                    if position['target_price']:
                        if position['type'] == PositionType.LONG and current_price >= position['target_price']:
                            self.position_manager.close_position(symbol, current_price, "Take Profit")
                            continue
                        elif position['type'] == PositionType.SHORT and current_price <= position['target_price']:
                            self.position_manager.close_position(symbol, current_price, "Take Profit")
                            continue
                    
                    # Verificar tiempo máximo de posición (24 horas)
                    position_age = datetime.now() - position['timestamp']
                    if position_age.total_seconds() > 86400:  # 24 horas
                        self.position_manager.close_position(symbol, current_price, "Tiempo máximo alcanzado")
                
                except Exception as e:
                    SICAR_LOGGER.log_error("POSITION_MANAGEMENT", f"Error gestionando posición {symbol}: {e}")
        
        except Exception as e:
            SICAR_LOGGER.log_error("POSITION_MANAGEMENT", f"Error en gestión de posiciones: {e}")
    
    async def _get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Obtener datos de mercado para un símbolo (simulado)"""
        try:
            # En implementación real, esto obtendría datos de Binance
            # Por ahora, generar datos simulados
            
            if symbol not in self.market_data:
                # Generar datos iniciales
                dates = pd.date_range(start=datetime.now() - timedelta(days=1), 
                                    end=datetime.now(), freq='1min')
                
                # Precio base según el símbolo
                base_prices = {
                    'BTCUSDT': 45000,
                    'ETHUSDT': 3000,
                    'ADAUSDT': 0.5,
                    'DOTUSDT': 8.0,
                    'LINKUSDT': 15.0
                }
                
                base_price = base_prices.get(symbol, 100)
                
                # Generar datos OHLCV simulados
                np.random.seed(hash(symbol) % 1000)
                returns = np.random.normal(0, 0.001, len(dates))
                prices = base_price * np.exp(np.cumsum(returns))
                
                data = pd.DataFrame({
                    'Open': prices * (1 + np.random.normal(0, 0.0005, len(dates))),
                    'High': prices * (1 + np.abs(np.random.normal(0, 0.001, len(dates)))),
                    'Low': prices * (1 - np.abs(np.random.normal(0, 0.001, len(dates)))),
                    'Close': prices,
                    'Volume': np.random.lognormal(10, 1, len(dates))
                }, index=dates)
                
                self.market_data[symbol] = data
            
            return self.market_data[symbol].tail(100)  # Últimas 100 velas
            
        except Exception as e:
            SICAR_LOGGER.log_error("MARKET_DATA", f"Error obteniendo datos de {symbol}: {e}")
            return None
    
    def _calculate_position_size(self, symbol: str, confidence: float) -> float:
        """Calcular tamaño de posición basado en confianza y gestión de riesgo"""
        try:
            # Tamaño base como porcentaje del capital
            base_size = 0.1  # 10% del capital
            
            # Ajustar por confianza
            confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5 a 1.0
            
            # Ajustar por volatilidad (simulado)
            volatility_adjustment = 0.8  # Reducir por volatilidad
            
            final_size = base_size * confidence_multiplier * volatility_adjustment
            
            return max(0.01, min(0.2, final_size))  # Entre 1% y 20%
            
        except Exception as e:
            SICAR_LOGGER.log_error("POSITION_SIZE", f"Error calculando tamaño: {e}")
            return 0.05  # 5% por defecto
    
    def _calculate_targets(self, entry_price: float, decision_type: DecisionType, 
                          confidence: float) -> Tuple[Optional[float], Optional[float]]:
        """Calcular precio objetivo y stop loss"""
        try:
            # Factores base
            base_target_pct = 0.02  # 2%
            base_stop_pct = 0.01    # 1%
            
            # Ajustar por confianza
            target_pct = base_target_pct * (0.5 + confidence * 0.5)
            stop_pct = base_stop_pct * (1.5 - confidence * 0.5)
            
            if decision_type == DecisionType.BUY:
                target_price = entry_price * (1 + target_pct)
                stop_loss = entry_price * (1 - stop_pct)
            else:  # SELL
                target_price = entry_price * (1 - target_pct)
                stop_loss = entry_price * (1 + stop_pct)
            
            return target_price, stop_loss
            
        except Exception as e:
            SICAR_LOGGER.log_error("TARGET_CALCULATION", f"Error calculando objetivos: {e}")
            return None, None
    
    def _calculate_risk_reward(self, entry_price: float, target_price: Optional[float], 
                              stop_loss: Optional[float]) -> float:
        """Calcular ratio riesgo/recompensa"""
        try:
            if not target_price or not stop_loss:
                return 1.0
            
            reward = abs(target_price - entry_price)
            risk = abs(entry_price - stop_loss)
            
            return reward / risk if risk > 0 else 1.0
            
        except Exception as e:
            SICAR_LOGGER.log_error("RISK_REWARD", f"Error calculando R/R: {e}")
            return 1.0
    
    def _reset_hourly_counters(self):
        """Resetear contadores horarios"""
        try:
            current_time = datetime.now()
            if (current_time - self.last_hour_reset).total_seconds() >= 3600:
                self.decisions_this_hour = 0
                self.last_hour_reset = current_time
        except Exception as e:
            SICAR_LOGGER.log_error("COUNTER_RESET", f"Error reseteando contadores: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """Obtener estado completo del sistema"""
        try:
            position_status = self.position_manager.get_position_status()
            
            return {
                'is_running': self.is_running,
                'decisions_this_hour': self.decisions_this_hour,
                'max_decisions_per_hour': self.config['max_decisions_per_hour'],
                'autonomous_execution': self.config['enable_autonomous_execution'],
                'position_status': position_status,
                'recent_decisions': [asdict(d) for d in self.decision_history[-5:]],
                'config': self.config,
                'performance_metrics': self.performance_metrics
            }
            
        except Exception as e:
            SICAR_LOGGER.log_error("SYSTEM_STATUS", f"Error obteniendo estado: {e}")
            return {'error': str(e)}

# Instancia global del motor de decisiones autónomas
AUTONOMOUS_ENGINE = AutonomousDecisionEngine()

async def start_autonomous_trading():
    """Función de conveniencia para iniciar trading autónomo"""
    await AUTONOMOUS_ENGINE.start_autonomous_trading()

async def stop_autonomous_trading():
    """Función de conveniencia para detener trading autónomo"""
    await AUTONOMOUS_ENGINE.stop_autonomous_trading()

def get_autonomous_status() -> Dict[str, Any]:
    """Función de conveniencia para obtener estado"""
    return AUTONOMOUS_ENGINE.get_system_status()