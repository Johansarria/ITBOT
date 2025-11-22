"""
SICAR - Integración Breakout-Portfolio
Sistema integrado que combina señales de rompimiento de primer vela con optimización de portafolio
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import json
import threading
import time
from collections import defaultdict

# Importar módulos existentes
from first_candle_breakout import FirstCandleBreakoutDetector, BreakoutSignal
from enhanced_breakout_detector import EnhancedBreakoutDetector, BreakoutType, BreakoutStrength
from portfolio_optimizer import PortfolioOptimizer, OptimizationMethod, OptimizationConstraints
from session_detector import SessionDetector

class BreakoutPortfolioStrategy(Enum):
    """Estrategias de integración breakout-portfolio"""
    MOMENTUM_WEIGHTED = "momentum_weighted"  # Peso basado en momentum de breakout
    RISK_ADJUSTED = "risk_adjusted"         # Ajustado por riesgo de breakout
    CONFIDENCE_SCALED = "confidence_scaled"  # Escalado por confianza de señal
    DYNAMIC_ALLOCATION = "dynamic_allocation" # Asignación dinámica basada en señales
    SECTOR_ROTATION = "sector_rotation"     # Rotación sectorial con breakouts

@dataclass
class BreakoutPortfolioSignal:
    """Señal integrada de breakout y portafolio"""
    timestamp: datetime
    symbol: str
    breakout_signal: BreakoutSignal
    portfolio_weight: float
    recommended_allocation: float
    risk_score: float
    confidence_score: float
    strategy_used: BreakoutPortfolioStrategy
    session: str
    expected_return: float
    risk_adjusted_return: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'breakout_signal': asdict(self.breakout_signal),
            'portfolio_weight': self.portfolio_weight,
            'recommended_allocation': self.recommended_allocation,
            'risk_score': self.risk_score,
            'confidence_score': self.confidence_score,
            'strategy_used': self.strategy_used.value,
            'session': self.session,
            'expected_return': self.expected_return,
            'risk_adjusted_return': self.risk_adjusted_return
        }

class BreakoutPortfolioIntegrator:
    """
    Integrador principal que combina señales de breakout con optimización de portafolio
    """
    
    def __init__(self, initial_capital: float = 10000.0):
        self.logger = logging.getLogger(__name__)
        
        # Componentes principales
        self.breakout_detector = FirstCandleBreakoutDetector()
        self.enhanced_breakout = EnhancedBreakoutDetector()
        self.portfolio_optimizer = PortfolioOptimizer()
        self.session_detector = SessionDetector()
        
        # Configuración
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_position_size = 0.20  # Máximo 20% por posición
        self.min_confidence_threshold = 0.65
        self.rebalance_frequency = timedelta(hours=4)  # Rebalanceo cada 4 horas
        
        # Estado del sistema
        self.active_signals = {}  # symbol -> BreakoutPortfolioSignal
        self.portfolio_weights = {}  # symbol -> weight
        self.last_rebalance = None
        self.performance_history = []
        
        # Configuración de estrategias
        self.strategy_config = {
            BreakoutPortfolioStrategy.MOMENTUM_WEIGHTED: {
                'momentum_factor': 2.0,
                'decay_rate': 0.95,
                'max_concentration': 0.30
            },
            BreakoutPortfolioStrategy.RISK_ADJUSTED: {
                'risk_penalty': 1.5,
                'volatility_target': 0.15,
                'max_drawdown_limit': 0.10
            },
            BreakoutPortfolioStrategy.CONFIDENCE_SCALED: {
                'confidence_power': 1.2,
                'min_confidence': 0.70,
                'scaling_factor': 1.5
            },
            BreakoutPortfolioStrategy.DYNAMIC_ALLOCATION: {
                'allocation_speed': 0.3,
                'momentum_threshold': 0.02,
                'reversion_factor': 0.1
            }
        }
        
        # Métricas de rendimiento
        self.performance_metrics = {
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'avg_holding_period': 0.0,
            'portfolio_turnover': 0.0
        }
        
        # Threading para monitoreo continuo
        self.is_running = False
        self.monitoring_thread = None
        self.lock = threading.RLock()
        
        self.logger.info("✅ BreakoutPortfolioIntegrator inicializado")
    
    def start_integration(self, strategy: BreakoutPortfolioStrategy = BreakoutPortfolioStrategy.CONFIDENCE_SCALED):
        """
        Iniciar la integración breakout-portfolio
        
        Args:
            strategy: Estrategia de integración a usar
        """
        try:
            with self.lock:
                if self.is_running:
                    self.logger.warning("La integración ya está ejecutándose")
                    return
                
                self.current_strategy = strategy
                self.is_running = True
                
                # Iniciar componentes
                self.enhanced_breakout.start_detection()
                
                # Configurar callbacks
                self.enhanced_breakout.add_alert_callback(self._on_breakout_detected)
                
                # Iniciar thread de monitoreo
                self.monitoring_thread = threading.Thread(
                    target=self._monitoring_loop, 
                    daemon=True
                )
                self.monitoring_thread.start()
                
                self.logger.info(f"🚀 Integración iniciada con estrategia: {strategy.value}")
                
        except Exception as e:
            self.logger.error(f"Error iniciando integración: {e}")
            self.is_running = False
    
    def stop_integration(self):
        """Detener la integración"""
        try:
            with self.lock:
                self.is_running = False
                self.enhanced_breakout.stop_detection()
                
                if self.monitoring_thread and self.monitoring_thread.is_alive():
                    self.monitoring_thread.join(timeout=5)
                
                self.logger.info("🛑 Integración detenida")
                
        except Exception as e:
            self.logger.error(f"Error deteniendo integración: {e}")
    
    def _on_breakout_detected(self, breakout_signal):
        """
        Callback cuando se detecta un breakout
        
        Args:
            breakout_signal: Señal de breakout detectada
        """
        try:
            current_session = self.session_detector.get_current_session()
            if not current_session:
                return
            
            # Convertir señal enhanced a formato estándar si es necesario
            if hasattr(breakout_signal, 'breakout_type'):
                # Es una señal enhanced, convertir
                standard_signal = self._convert_enhanced_signal(breakout_signal)
            else:
                standard_signal = breakout_signal
            
            # Verificar confianza mínima
            if standard_signal.confidence < self.min_confidence_threshold:
                self.logger.debug(f"Señal {standard_signal.symbol} descartada por baja confianza: {standard_signal.confidence:.2f}")
                return
            
            # Generar señal integrada
            integrated_signal = self._generate_integrated_signal(
                standard_signal, current_session
            )
            
            if integrated_signal:
                # Actualizar portafolio
                self._update_portfolio_allocation(integrated_signal)
                
                # Registrar señal
                self.active_signals[integrated_signal.symbol] = integrated_signal
                
                self.logger.info(f"📊 Señal integrada generada para {integrated_signal.symbol}: "
                               f"Asignación {integrated_signal.recommended_allocation:.1%}")
                
        except Exception as e:
            self.logger.error(f"Error procesando breakout: {e}")
    
    def _convert_enhanced_signal(self, enhanced_signal) -> BreakoutSignal:
        """
        Convertir señal enhanced a formato estándar
        
        Args:
            enhanced_signal: Señal del enhanced detector
            
        Returns:
            BreakoutSignal: Señal en formato estándar
        """
        # Determinar tipo de señal
        if enhanced_signal.breakout_type == BreakoutType.BULLISH:
            signal_type = 'bullish_breakout'
        elif enhanced_signal.breakout_type == BreakoutType.BEARISH:
            signal_type = 'bearish_breakout'
        else:
            signal_type = 'no_signal'
        
        # Calcular niveles de stop loss y take profit basados en soporte/resistencia
        if signal_type == 'bullish_breakout':
            stop_loss = enhanced_signal.support_level
            take_profit = enhanced_signal.price + (enhanced_signal.price - enhanced_signal.support_level) * 2
        elif signal_type == 'bearish_breakout':
            stop_loss = enhanced_signal.resistance_level
            take_profit = enhanced_signal.price - (enhanced_signal.resistance_level - enhanced_signal.price) * 2
        else:
            stop_loss = enhanced_signal.price
            take_profit = enhanced_signal.price
        
        # Crear señal estándar
        return BreakoutSignal(
            timestamp=enhanced_signal.timestamp,
            symbol=enhanced_signal.symbol,
            session=self.session_detector.get_current_session() or 'unknown',
            signal_type=signal_type,
            entry_price=enhanced_signal.price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume_ratio=enhanced_signal.volume_ratio,
            confidence=enhanced_signal.confidence,
            candle_data={
                'open': enhanced_signal.price,
                'high': enhanced_signal.price,
                'low': enhanced_signal.price,
                'close': enhanced_signal.price,
                'volume': enhanced_signal.volume
            }
        )
    
    def _generate_integrated_signal(self, breakout_signal: BreakoutSignal, session: str) -> Optional[BreakoutPortfolioSignal]:
        """
        Generar señal integrada combinando breakout y optimización de portafolio
        
        Args:
            breakout_signal: Señal de breakout
            session: Sesión actual
            
        Returns:
            BreakoutPortfolioSignal: Señal integrada o None
        """
        try:
            symbol = breakout_signal.symbol
            
            # Calcular peso actual en portafolio
            current_weight = self.portfolio_weights.get(symbol, 0.0)
            
            # Calcular métricas de riesgo
            risk_score = self._calculate_risk_score(breakout_signal)
            
            # Calcular retorno esperado
            expected_return = self._calculate_expected_return(breakout_signal)
            
            # Calcular retorno ajustado por riesgo
            risk_adjusted_return = expected_return / max(risk_score, 0.01)
            
            # Calcular asignación recomendada según estrategia
            recommended_allocation = self._calculate_recommended_allocation(
                breakout_signal, risk_score, expected_return
            )
            
            # Crear señal integrada
            integrated_signal = BreakoutPortfolioSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                breakout_signal=breakout_signal,
                portfolio_weight=current_weight,
                recommended_allocation=recommended_allocation,
                risk_score=risk_score,
                confidence_score=breakout_signal.confidence,
                strategy_used=self.current_strategy,
                session=session,
                expected_return=expected_return,
                risk_adjusted_return=risk_adjusted_return
            )
            
            return integrated_signal
            
        except Exception as e:
            self.logger.error(f"Error generando señal integrada para {breakout_signal.symbol}: {e}")
            return None
    
    def _calculate_risk_score(self, breakout_signal: BreakoutSignal) -> float:
        """
        Calcular score de riesgo para la señal
        
        Args:
            breakout_signal: Señal de breakout
            
        Returns:
            float: Score de riesgo (0-1, donde 1 es más riesgo)
        """
        try:
            # Factores de riesgo
            volatility_factor = min(breakout_signal.volume_ratio / 5.0, 1.0)  # Normalizar volumen
            
            # Distancia a stop loss como proxy de riesgo
            price_distance = abs(breakout_signal.entry_price - breakout_signal.stop_loss) / breakout_signal.entry_price
            distance_factor = min(price_distance * 10, 1.0)  # Normalizar distancia
            
            # Factor de confianza inverso (menor confianza = mayor riesgo)
            confidence_factor = 1.0 - breakout_signal.confidence
            
            # Combinar factores
            risk_score = (volatility_factor * 0.4 + distance_factor * 0.4 + confidence_factor * 0.2)
            
            return max(0.1, min(risk_score, 1.0))  # Mantener en rango [0.1, 1.0]
            
        except Exception as e:
            self.logger.error(f"Error calculando risk score: {e}")
            return 0.5  # Riesgo medio por defecto
    
    def _calculate_expected_return(self, breakout_signal: BreakoutSignal) -> float:
        """
        Calcular retorno esperado basado en la señal
        
        Args:
            breakout_signal: Señal de breakout
            
        Returns:
            float: Retorno esperado (decimal)
        """
        try:
            # Calcular retorno potencial basado en take profit
            potential_return = (breakout_signal.take_profit - breakout_signal.entry_price) / breakout_signal.entry_price
            
            # Ajustar por confianza
            confidence_adjusted_return = potential_return * breakout_signal.confidence
            
            # Ajustar por volumen (mayor volumen = mayor probabilidad)
            volume_factor = min(breakout_signal.volume_ratio / 2.0, 1.5)  # Cap en 1.5x
            volume_adjusted_return = confidence_adjusted_return * volume_factor
            
            return max(-0.1, min(volume_adjusted_return, 0.2))  # Cap entre -10% y +20%
            
        except Exception as e:
            self.logger.error(f"Error calculando retorno esperado: {e}")
            return 0.02  # 2% por defecto
    
    def _calculate_recommended_allocation(self, breakout_signal: BreakoutSignal, 
                                        risk_score: float, expected_return: float) -> float:
        """
        Calcular asignación recomendada según la estrategia actual
        
        Args:
            breakout_signal: Señal de breakout
            risk_score: Score de riesgo
            expected_return: Retorno esperado
            
        Returns:
            float: Asignación recomendada (0-1)
        """
        try:
            strategy_config = self.strategy_config[self.current_strategy]
            
            if self.current_strategy == BreakoutPortfolioStrategy.CONFIDENCE_SCALED:
                # Escalado por confianza
                base_allocation = self.max_position_size
                confidence_factor = (breakout_signal.confidence ** strategy_config['confidence_power'])
                scaling_factor = strategy_config['scaling_factor']
                
                allocation = base_allocation * confidence_factor * scaling_factor
                
            elif self.current_strategy == BreakoutPortfolioStrategy.RISK_ADJUSTED:
                # Ajustado por riesgo
                base_allocation = self.max_position_size
                risk_penalty = strategy_config['risk_penalty']
                
                allocation = base_allocation * (1.0 - risk_score * risk_penalty)
                
            elif self.current_strategy == BreakoutPortfolioStrategy.MOMENTUM_WEIGHTED:
                # Peso basado en momentum
                momentum_factor = strategy_config['momentum_factor']
                volume_momentum = min(breakout_signal.volume_ratio / 2.0, 2.0)
                
                allocation = self.max_position_size * volume_momentum * momentum_factor / 4.0
                
            else:
                # Asignación dinámica por defecto
                allocation = self.max_position_size * breakout_signal.confidence * (expected_return / 0.05)
            
            # Aplicar límites
            allocation = max(0.01, min(allocation, self.max_position_size))
            
            return allocation
            
        except Exception as e:
            self.logger.error(f"Error calculando asignación recomendada: {e}")
            return 0.05  # 5% por defecto
    
    def _update_portfolio_allocation(self, integrated_signal: BreakoutPortfolioSignal):
        """
        Actualizar asignación del portafolio basada en la señal integrada
        
        Args:
            integrated_signal: Señal integrada
        """
        try:
            with self.lock:
                symbol = integrated_signal.symbol
                new_allocation = integrated_signal.recommended_allocation
                
                # Actualizar peso en portafolio
                old_weight = self.portfolio_weights.get(symbol, 0.0)
                self.portfolio_weights[symbol] = new_allocation
                
                # Normalizar pesos para que sumen 1.0
                self._normalize_portfolio_weights()
                
                # Registrar cambio
                weight_change = new_allocation - old_weight
                
                self.logger.info(f"💼 Portafolio actualizado - {symbol}: "
                               f"{old_weight:.1%} → {new_allocation:.1%} "
                               f"(Δ{weight_change:+.1%})")
                
                # Actualizar métricas de performance
                self._update_performance_metrics()
                
        except Exception as e:
            self.logger.error(f"Error actualizando portafolio: {e}")
    
    def _normalize_portfolio_weights(self):
        """Normalizar pesos del portafolio para que sumen 1.0"""
        try:
            total_weight = sum(self.portfolio_weights.values())
            
            if total_weight > 0:
                # Normalizar
                for symbol in self.portfolio_weights:
                    self.portfolio_weights[symbol] /= total_weight
                
                # Mantener cash si la suma es menor a 1.0
                if total_weight < 1.0:
                    self.portfolio_weights['CASH'] = 1.0 - sum(
                        w for k, w in self.portfolio_weights.items() if k != 'CASH'
                    )
            else:
                # Todo en cash si no hay posiciones
                self.portfolio_weights = {'CASH': 1.0}
                
        except Exception as e:
            self.logger.error(f"Error normalizando pesos: {e}")
    
    def _update_performance_metrics(self):
        """Actualizar métricas de performance del portafolio"""
        try:
            # Calcular métricas básicas
            active_positions = len([w for w in self.portfolio_weights.values() if w > 0.01])
            total_allocation = sum(w for k, w in self.portfolio_weights.items() if k != 'CASH')
            
            # Actualizar métricas
            self.performance_metrics.update({
                'active_positions': active_positions,
                'total_allocation': total_allocation,
                'cash_position': self.portfolio_weights.get('CASH', 0.0),
                'last_update': datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"Error actualizando métricas: {e}")
    
    def _monitoring_loop(self):
        """Loop principal de monitoreo"""
        try:
            while self.is_running:
                try:
                    # Verificar si necesita rebalanceo
                    if self._should_rebalance():
                        self._rebalance_portfolio()
                    
                    # Limpiar señales expiradas
                    self._cleanup_expired_signals()
                    
                    # Actualizar métricas
                    self._update_performance_metrics()
                    
                    # Esperar antes del siguiente ciclo
                    time.sleep(30)  # Revisar cada 30 segundos
                    
                except Exception as e:
                    self.logger.error(f"Error en loop de monitoreo: {e}")
                    time.sleep(60)  # Esperar más tiempo si hay error
                    
        except Exception as e:
            self.logger.error(f"Error crítico en monitoring loop: {e}")
        finally:
            self.logger.info("🔄 Loop de monitoreo terminado")
    
    def _should_rebalance(self) -> bool:
        """Verificar si el portafolio necesita rebalanceo"""
        try:
            if not self.last_rebalance:
                return True
            
            time_since_rebalance = datetime.now() - self.last_rebalance
            return time_since_rebalance >= self.rebalance_frequency
            
        except Exception as e:
            self.logger.error(f"Error verificando rebalanceo: {e}")
            return False
    
    def _rebalance_portfolio(self):
        """Rebalancear el portafolio"""
        try:
            with self.lock:
                self.logger.info("⚖️ Iniciando rebalanceo de portafolio...")
                
                # Aquí se implementaría la lógica de rebalanceo real
                # Por ahora, solo actualizamos el timestamp
                self.last_rebalance = datetime.now()
                
                self.logger.info("✅ Rebalanceo completado")
                
        except Exception as e:
            self.logger.error(f"Error en rebalanceo: {e}")
    
    def _cleanup_expired_signals(self):
        """Limpiar señales expiradas"""
        try:
            current_time = datetime.now()
            expired_symbols = []
            
            for symbol, signal in self.active_signals.items():
                # Expirar señales después de 4 horas
                if current_time - signal.timestamp > timedelta(hours=4):
                    expired_symbols.append(symbol)
            
            # Remover señales expiradas
            for symbol in expired_symbols:
                del self.active_signals[symbol]
                if symbol in self.portfolio_weights:
                    # Reducir gradualmente la posición
                    self.portfolio_weights[symbol] *= 0.5
                    if self.portfolio_weights[symbol] < 0.01:
                        del self.portfolio_weights[symbol]
            
            if expired_symbols:
                self.logger.info(f"🧹 Limpiadas {len(expired_symbols)} señales expiradas")
                self._normalize_portfolio_weights()
                
        except Exception as e:
            self.logger.error(f"Error limpiando señales: {e}")
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        Obtener estado actual del portafolio
        
        Returns:
            Dict: Estado del portafolio
        """
        try:
            with self.lock:
                return {
                    'is_running': self.is_running,
                    'strategy': self.current_strategy.value if hasattr(self, 'current_strategy') else None,
                    'portfolio_weights': self.portfolio_weights.copy(),
                    'active_signals': len(self.active_signals),
                    'performance_metrics': self.performance_metrics.copy(),
                    'last_rebalance': self.last_rebalance.isoformat() if self.last_rebalance else None,
                    'current_capital': self.current_capital
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo estado del portafolio: {e}")
            return {}
    
    def get_active_signals(self) -> List[Dict[str, Any]]:
        """
        Obtener señales activas
        
        Returns:
            List: Lista de señales activas
        """
        try:
            with self.lock:
                return [signal.to_dict() for signal in self.active_signals.values()]
                
        except Exception as e:
            self.logger.error(f"Error obteniendo señales activas: {e}")
            return []

# Instancia global del integrador
BREAKOUT_PORTFOLIO_INTEGRATOR = BreakoutPortfolioIntegrator()

def start_breakout_portfolio_integration(strategy: BreakoutPortfolioStrategy = BreakoutPortfolioStrategy.CONFIDENCE_SCALED):
    """Iniciar integración breakout-portfolio"""
    BREAKOUT_PORTFOLIO_INTEGRATOR.start_integration(strategy)

def stop_breakout_portfolio_integration():
    """Detener integración breakout-portfolio"""
    BREAKOUT_PORTFOLIO_INTEGRATOR.stop_integration()

def get_integration_status():
    """Obtener estado de la integración"""
    return BREAKOUT_PORTFOLIO_INTEGRATOR.get_portfolio_status()

def get_integration_signals():
    """Obtener señales activas de la integración"""
    return BREAKOUT_PORTFOLIO_INTEGRATOR.get_active_signals()

if __name__ == "__main__":
    # Configurar logging para pruebas
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=== SICAR Breakout-Portfolio Integration - Prueba ===")
    print()
    
    # Crear integrador
    integrator = BreakoutPortfolioIntegrator()
    
    try:
        # Iniciar integración
        print("🚀 Iniciando integración...")
        integrator.start_integration(BreakoutPortfolioStrategy.CONFIDENCE_SCALED)
        
        # Esperar un poco para ver actividad
        print("⏳ Monitoreando por 30 segundos...")
        time.sleep(30)
        
        # Mostrar estado
        status = integrator.get_portfolio_status()
        print(f"\n📊 Estado del portafolio:")
        print(f"  Ejecutándose: {status.get('is_running', False)}")
        print(f"  Estrategia: {status.get('strategy', 'N/A')}")
        print(f"  Señales activas: {status.get('active_signals', 0)}")
        print(f"  Posiciones: {len(status.get('portfolio_weights', {}))}")
        
        # Mostrar pesos del portafolio
        weights = status.get('portfolio_weights', {})
        if weights:
            print(f"\n💼 Pesos del portafolio:")
            for symbol, weight in weights.items():
                print(f"  {symbol}: {weight:.1%}")
        
        # Mostrar señales activas
        signals = integrator.get_active_signals()
        if signals:
            print(f"\n🚨 Señales activas ({len(signals)}):")
            for signal in signals[:3]:  # Mostrar solo las primeras 3
                print(f"  {signal['symbol']}: {signal['confidence_score']:.1%} confianza, "
                      f"{signal['recommended_allocation']:.1%} asignación")
        
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo integración...")
    finally:
        integrator.stop_integration()
        print("✅ Integración detenida")