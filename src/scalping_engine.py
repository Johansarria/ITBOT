"""
SICAR Scalping Engine - Sistema de Scalping Automático
Gestiona operaciones de 5 minutos basadas en breakouts detectados
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from enhanced_config import SicarConfig

class ScalpingPositionStatus(Enum):
    ACTIVE = "active"
    CLOSED_PROFIT = "closed_profit"
    CLOSED_LOSS = "closed_loss"
    CLOSED_TIMEOUT = "closed_timeout"
    CLOSED_MANUAL = "closed_manual"

@dataclass
class ScalpingPosition:
    """Representa una posición de scalping activa"""
    symbol: str
    entry_price: float
    entry_time: datetime
    direction: str  # 'LONG' o 'SHORT'
    position_size: float
    take_profit_price: float
    stop_loss_price: float
    confidence: float
    status: ScalpingPositionStatus = ScalpingPositionStatus.ACTIVE
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    
    def is_expired(self, duration_minutes: int = 5) -> bool:
        """Verifica si la posición ha expirado"""
        return datetime.now() > self.entry_time + timedelta(minutes=duration_minutes)

class ScalpingEngine:
    """Motor de Scalping Automático para SICAR"""
    
    def __init__(self, paper_trading_system=None, data_provider=None):
        self.config = SicarConfig.SCALPING_CONFIG
        self.paper_trading = paper_trading_system
        self.data_provider = data_provider
        
        # Estado del motor
        self.active_positions: Dict[str, ScalpingPosition] = {}
        self.position_history: List[ScalpingPosition] = []
        self.symbol_cooldowns: Dict[str, datetime] = {}
        self.daily_stats = {
            'trades_count': 0,
            'profitable_trades': 0,
            'total_pnl': 0.0,
            'consecutive_losses': 0,
            'recovery_mode': False
        }
        
        # Logger específico para scalping
        self.logger = logging.getLogger('sicar.scalping')
        
        # Verificar si está habilitado
        if not self.config.get('enabled', False):
            self.logger.info("🚫 Scalping Engine DESHABILITADO en configuración")
            return
            
        self.logger.info("⚡ Scalping Engine INICIALIZADO")
        self.logger.info(f"📊 Configuración: TP={self.config['take_profit_pct']}%, SL={self.config['stop_loss_pct']}%")
        
    def is_enabled(self) -> bool:
        """Verifica si el scalping está habilitado"""
        return self.config.get('enabled', False)
    
    def can_open_position(self, symbol: str, confidence: float) -> Tuple[bool, str]:
        """Verifica si se puede abrir una nueva posición"""
        if not self.is_enabled():
            return False, "Scalping deshabilitado"
            
        # Verificar límites de confianza
        min_conf = self.config['min_confidence_threshold']
        max_conf = self.config['max_confidence_threshold']
        if not (min_conf <= confidence <= max_conf):
            return False, f"Confianza {confidence:.1f}% fuera del rango {min_conf}-{max_conf}%"
        
        # Verificar símbolo permitido
        if symbol not in self.config['symbols_allowed']:
            return False, f"Símbolo {symbol} no permitido para scalping"
            
        # Verificar cooldown del símbolo
        if symbol in self.symbol_cooldowns:
            cooldown_end = self.symbol_cooldowns[symbol]
            if datetime.now() < cooldown_end:
                remaining = (cooldown_end - datetime.now()).total_seconds() / 60
                return False, f"Cooldown activo para {symbol} ({remaining:.1f}m restantes)"
        
        # Verificar máximo de posiciones concurrentes
        active_count = len(self.active_positions)
        max_positions = self.config['max_concurrent_positions']
        if active_count >= max_positions:
            return False, f"Máximo de posiciones alcanzado ({active_count}/{max_positions})"
            
        # Verificar límite de pérdidas diarias
        if self._check_daily_loss_limit():
            return False, "Límite de pérdidas diarias alcanzado"
            
        # Verificar pérdidas consecutivas
        if self._check_consecutive_losses():
            return False, "Límite de pérdidas consecutivas alcanzado"
            
        return True, "OK"
    
    def process_breakout_signal(self, symbol: str, direction: str, price: float, 
                              confidence: float, volume_ratio: float) -> bool:
        """Procesa una señal de breakout para posible scalping"""
        if not self.is_enabled():
            return False
            
        # Verificar si se puede abrir posición
        can_open, reason = self.can_open_position(symbol, confidence)
        if not can_open:
            self.logger.debug(f"❌ No se puede abrir posición {symbol}: {reason}")
            return False
            
        # Verificar confirmación de volumen si está requerida
        if self.config['volume_confirmation_required']:
            min_volume = self.config['min_volume_ratio']
            if volume_ratio < min_volume:
                self.logger.debug(f"❌ Volumen insuficiente {symbol}: {volume_ratio:.2f} < {min_volume}")
                return False
        
        # Crear nueva posición
        position = self._create_position(symbol, direction, price, confidence)
        if position:
            self.active_positions[symbol] = position
            self._set_symbol_cooldown(symbol)
            
            # Ejecutar en paper trading si está disponible
            if self.paper_trading:
                self._execute_paper_trade(position)
                
            self.logger.info(f"🚀 SCALPING INICIADO: {symbol} {direction} @ ${price:.4f}")
            self.logger.info(f"   📊 Confianza: {confidence:.1f}% | TP: ${position.take_profit_price:.4f} | SL: ${position.stop_loss_price:.4f}")
            
            return True
            
        return False
    
    def _create_position(self, symbol: str, direction: str, price: float, confidence: float) -> Optional[ScalpingPosition]:
        """Crea una nueva posición de scalping"""
        try:
            # Calcular tamaño de posición
            position_size_pct = self.config['position_size_pct']
            if self.daily_stats['recovery_mode']:
                position_size_pct = self.config['risk_management']['recovery_position_size_pct']
            
            # Calcular take profit y stop loss
            tp_pct, sl_pct = self._calculate_tp_sl(confidence)
            
            if direction.upper() == 'LONG':
                take_profit_price = price * (1 + tp_pct / 100)
                stop_loss_price = price * (1 - sl_pct / 100)
            else:  # SHORT
                take_profit_price = price * (1 - tp_pct / 100)
                stop_loss_price = price * (1 + sl_pct / 100)
            
            position = ScalpingPosition(
                symbol=symbol,
                entry_price=price,
                entry_time=datetime.now(),
                direction=direction.upper(),
                position_size=position_size_pct,
                take_profit_price=take_profit_price,
                stop_loss_price=stop_loss_price,
                confidence=confidence
            )
            
            return position
            
        except Exception as e:
            self.logger.error(f"❌ Error creando posición {symbol}: {e}")
            return None
    
    def _calculate_tp_sl(self, confidence: float) -> Tuple[float, float]:
        """Calcula take profit y stop loss basado en confianza"""
        base_tp = self.config['take_profit_pct']
        base_sl = self.config['stop_loss_pct']
        
        # Escalado de ganancias si está habilitado
        if self.config['profit_scaling']['enabled']:
            min_conf = self.config['min_confidence_threshold']
            max_conf = self.config['max_confidence_threshold']
            min_tp = self.config['profit_scaling']['min_profit_pct']
            max_tp = self.config['profit_scaling']['max_profit_pct']
            
            # Interpolación lineal
            confidence_ratio = (confidence - min_conf) / (max_conf - min_conf)
            scaled_tp = min_tp + (max_tp - min_tp) * confidence_ratio
            
            return scaled_tp, base_sl
        
        return base_tp, base_sl
    
    def _set_symbol_cooldown(self, symbol: str):
        """Establece cooldown para un símbolo"""
        cooldown_minutes = self.config['cooldown_minutes']
        self.symbol_cooldowns[symbol] = datetime.now() + timedelta(minutes=cooldown_minutes)
    
    def _execute_paper_trade(self, position: ScalpingPosition):
        """Ejecuta la operación en paper trading"""
        if not self.paper_trading:
            return
            
        try:
            from paper_trading_system import OrderType
            
            # Calcular cantidad basada en el tamaño de posición y precio
            quantity = position.position_size / position.entry_price
            
            # Colocar orden de entrada
            side = 'buy' if position.direction == 'LONG' else 'sell'
            order_id = self.paper_trading.place_order(
                symbol=position.symbol,
                side=side,
                order_type=OrderType.MARKET,
                quantity=quantity,
                price=position.entry_price
            )
            
            # Procesar datos de mercado para ejecutar la orden
            market_data = {position.symbol: position.entry_price}
            self.paper_trading.process_market_data(market_data)
            
            self.logger.info(f"✅ Paper trade ejecutado: {order_id} - {side.upper()} {quantity:.6f} {position.symbol}")
            
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando paper trade: {e}")
    
    def monitor_positions(self):
        """Monitorea posiciones activas para cierre automático"""
        if not self.active_positions:
            return
            
        current_time = datetime.now()
        positions_to_close = []
        
        for symbol, position in self.active_positions.items():
            # Verificar expiración por tiempo
            if position.is_expired(self.config['operation_duration_minutes']):
                positions_to_close.append((symbol, 'TIMEOUT'))
                continue
                
            # Obtener precio actual
            current_price = self._get_current_price(symbol)
            if current_price is None:
                continue
                
            # Verificar take profit y stop loss
            if position.direction == 'LONG':
                if current_price >= position.take_profit_price:
                    positions_to_close.append((symbol, 'TAKE_PROFIT'))
                elif current_price <= position.stop_loss_price:
                    positions_to_close.append((symbol, 'STOP_LOSS'))
            else:  # SHORT
                if current_price <= position.take_profit_price:
                    positions_to_close.append((symbol, 'TAKE_PROFIT'))
                elif current_price >= position.stop_loss_price:
                    positions_to_close.append((symbol, 'STOP_LOSS'))
        
        # Cerrar posiciones
        for symbol, reason in positions_to_close:
            self.close_position(symbol, reason)
    
    def close_position(self, symbol: str, reason: str = 'MANUAL'):
        """Cierra una posición activa"""
        if symbol not in self.active_positions:
            return False
            
        position = self.active_positions[symbol]
        current_price = self._get_current_price(symbol)
        
        if current_price is None:
            self.logger.error(f"❌ No se pudo obtener precio para cerrar {symbol}")
            return False
        
        # Actualizar posición
        position.exit_price = current_price
        position.exit_time = datetime.now()
        
        # Calcular PnL
        if position.direction == 'LONG':
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        else:  # SHORT
            pnl_pct = ((position.entry_price - current_price) / position.entry_price) * 100
            
        position.pnl = pnl_pct
        
        # Determinar status
        if reason == 'TAKE_PROFIT':
            position.status = ScalpingPositionStatus.CLOSED_PROFIT
        elif reason == 'STOP_LOSS':
            position.status = ScalpingPositionStatus.CLOSED_LOSS
        elif reason == 'TIMEOUT':
            position.status = ScalpingPositionStatus.CLOSED_TIMEOUT
        else:
            position.status = ScalpingPositionStatus.CLOSED_MANUAL
        
        # Actualizar estadísticas
        self._update_daily_stats(position)
        
        # Mover a historial
        self.position_history.append(position)
        del self.active_positions[symbol]
        
        # Log del cierre
        duration = (position.exit_time - position.entry_time).total_seconds() / 60
        self.logger.info(f"🏁 SCALPING CERRADO: {symbol} {reason}")
        self.logger.info(f"   💰 PnL: {pnl_pct:+.2f}% | Duración: {duration:.1f}m")
        
        return True
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Obtiene el precio actual de un símbolo"""
        if not self.data_provider:
            return None
            
        try:
            # Obtener datos actuales
            data = self.data_provider.get_current_data(symbol)
            if data and 'close' in data:
                return float(data['close'])
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo precio {symbol}: {e}")
            
        return None
    
    def _update_daily_stats(self, position: ScalpingPosition):
        """Actualiza estadísticas diarias"""
        self.daily_stats['trades_count'] += 1
        
        if position.pnl and position.pnl > 0:
            self.daily_stats['profitable_trades'] += 1
            self.daily_stats['consecutive_losses'] = 0
            if self.daily_stats['recovery_mode']:
                self.logger.info("🔄 Saliendo de modo recuperación")
                self.daily_stats['recovery_mode'] = False
        else:
            self.daily_stats['consecutive_losses'] += 1
            
        if position.pnl:
            self.daily_stats['total_pnl'] += position.pnl
            
        # Verificar modo recuperación
        max_losses = self.config['risk_management']['max_consecutive_losses']
        if self.daily_stats['consecutive_losses'] >= max_losses:
            if self.config['risk_management']['recovery_mode_enabled']:
                self.daily_stats['recovery_mode'] = True
                self.logger.warning("⚠️ Activando modo recuperación")
    
    def _check_daily_loss_limit(self) -> bool:
        """Verifica si se alcanzó el límite de pérdidas diarias"""
        max_loss = self.config['risk_management']['max_daily_loss_pct']
        return self.daily_stats['total_pnl'] <= -max_loss
    
    def _check_consecutive_losses(self) -> bool:
        """Verifica si se alcanzó el límite de pérdidas consecutivas"""
        max_losses = self.config['risk_management']['max_consecutive_losses']
        return self.daily_stats['consecutive_losses'] >= max_losses
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas del scalping"""
        total_trades = self.daily_stats['trades_count']
        profitable = self.daily_stats['profitable_trades']
        
        return {
            'enabled': self.is_enabled(),
            'active_positions': len(self.active_positions),
            'total_trades_today': total_trades,
            'profitable_trades': profitable,
            'win_rate': (profitable / total_trades * 100) if total_trades > 0 else 0,
            'total_pnl': self.daily_stats['total_pnl'],
            'consecutive_losses': self.daily_stats['consecutive_losses'],
            'recovery_mode': self.daily_stats['recovery_mode'],
            'positions': [
                {
                    'symbol': pos.symbol,
                    'direction': pos.direction,
                    'entry_price': pos.entry_price,
                    'confidence': pos.confidence,
                    'duration_minutes': (datetime.now() - pos.entry_time).total_seconds() / 60
                }
                for pos in self.active_positions.values()
            ]
        }
    
    def close_all_positions(self, reason: str = 'MANUAL'):
        """Cierra todas las posiciones activas"""
        symbols = list(self.active_positions.keys())
        for symbol in symbols:
            self.close_position(symbol, reason)
        
        self.logger.info(f"🛑 Todas las posiciones cerradas: {reason}")
    
    def start(self):
        """Inicia el motor de scalping"""
        if not self.is_enabled():
            self.logger.warning("🚫 No se puede iniciar: Scalping deshabilitado")
            return False
            
        self.logger.info("🚀 Scalping Engine INICIADO")
        return True
    
    def stop(self):
        """Detiene el motor de scalping"""
        self.logger.info("🛑 Deteniendo Scalping Engine...")
        
        # Cerrar todas las posiciones activas
        if self.active_positions:
            self.close_all_positions("SYSTEM_STOP")
            
        self.logger.info("✅ Scalping Engine DETENIDO")