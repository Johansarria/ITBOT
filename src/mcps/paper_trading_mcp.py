"""
Paper Trading MCP
Micro-Controller Process para el sistema de paper trading de SICAR
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import threading

# Importaciones del framework MCP
from mcp_framework import MCPBase, MCPMessage, MCPResponse

# Importaciones de SICAR
from paper_trading_system import (
    PaperTradingEngine, OrderType, OrderStatus, PositionSide
)

logger = logging.getLogger(__name__)

class PaperTradingMCP(MCPBase):
    """
    MCP para el sistema de paper trading.
    
    Funcionalidades:
    - Gestión de capital virtual
    - Colocación y ejecución de órdenes
    - Seguimiento de posiciones
    - Cálculo de métricas de performance
    - Operaciones de scalping
    - Gestión de stop loss y take profit
    """
    
    def __init__(self, name: str = "paper_trading", port: int = 8767):
        super().__init__(name, port)
        
        # Inicializar el motor de paper trading
        self.engine = None
        self.is_active = False
        
        # Configuración por defecto
        self.default_config = {
            'initial_capital': 10000.0,
            'commission_rate': 0.001,
            'slippage_factor': 0.0005
        }
        
        # Callbacks registrados para notificaciones
        self.trade_callbacks = set()
        self.position_callbacks = set()
        
        # Registrar handlers específicos
        self._register_handlers()
        
        logger.info(f"🎯 PaperTradingMCP inicializado en puerto {port}")
    
    def _register_handlers(self):
        """Registra todos los handlers específicos del paper trading"""
        
        # Gestión del motor
        self.register_handler("initialize_engine", self._handle_initialize_engine)
        self.register_handler("reset_engine", self._handle_reset_engine)
        self.register_handler("get_engine_status", self._handle_get_engine_status)
        
        # Gestión de órdenes
        self.register_handler("place_order", self._handle_place_order)
        self.register_handler("cancel_order", self._handle_cancel_order)
        self.register_handler("get_orders", self._handle_get_orders)
        self.register_handler("get_order_history", self._handle_get_order_history)
        
        # Gestión de posiciones
        self.register_handler("get_positions", self._handle_get_positions)
        self.register_handler("close_position", self._handle_close_position)
        self.register_handler("close_all_positions", self._handle_close_all_positions)
        self.register_handler("update_position_stops", self._handle_update_position_stops)
        
        # Datos de mercado
        self.register_handler("process_market_data", self._handle_process_market_data)
        self.register_handler("update_price", self._handle_update_price)
        
        # Métricas y reportes
        self.register_handler("get_portfolio_summary", self._handle_get_portfolio_summary)
        self.register_handler("get_trade_history", self._handle_get_trade_history)
        self.register_handler("get_performance_metrics", self._handle_get_performance_metrics)
        
        # Operaciones de scalping
        self.register_handler("create_scalping_position", self._handle_create_scalping_position)
        self.register_handler("get_scalping_stats", self._handle_get_scalping_stats)
        
        # Gestión de estado
        self.register_handler("save_state", self._handle_save_state)
        self.register_handler("load_state", self._handle_load_state)
        
        # Callbacks y notificaciones
        self.register_handler("register_trade_callback", self._handle_register_trade_callback)
        self.register_handler("register_position_callback", self._handle_register_position_callback)
        self.register_handler("unregister_callback", self._handle_unregister_callback)
    
    async def _handle_initialize_engine(self, message: MCPMessage) -> MCPResponse:
        """Inicializa el motor de paper trading"""
        try:
            params = message.params or {}
            
            initial_capital = params.get('initial_capital', self.default_config['initial_capital'])
            commission_rate = params.get('commission_rate', self.default_config['commission_rate'])
            
            self.engine = PaperTradingEngine(
                initial_capital=initial_capital,
                commission_rate=commission_rate
            )
            
            self.is_active = True
            
            logger.info(f"✅ Motor de paper trading inicializado con ${initial_capital:,.2f}")
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "message": "Motor de paper trading inicializado",
                    "initial_capital": initial_capital,
                    "commission_rate": commission_rate
                }
            )
            
        except Exception as e:
            logger.error(f"Error inicializando motor: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error inicializando motor: {str(e)}"}
            )
    
    async def _handle_reset_engine(self, message: MCPMessage) -> MCPResponse:
        """Resetea el motor de paper trading"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            params = message.params or {}
            new_capital = params.get('new_capital', self.default_config['initial_capital'])
            close_positions = params.get('close_positions', True)
            reset_history = params.get('reset_history', True)
            
            self.engine.reset_capital(new_capital, close_positions, reset_history)
            
            logger.info(f"🔄 Motor reseteado con ${new_capital:,.2f}")
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "message": "Motor reseteado exitosamente",
                    "new_capital": new_capital
                }
            )
            
        except Exception as e:
            logger.error(f"Error reseteando motor: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error reseteando motor: {str(e)}"}
            )
    
    async def _handle_get_engine_status(self, message: MCPMessage) -> MCPResponse:
        """Obtiene el estado del motor"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                        "success": True,
                        "is_active": False,
                        "engine_initialized": False
                    }
                )
            
            summary = self.engine.get_portfolio_summary()
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "is_active": self.is_active,
                    "engine_initialized": True,
                    "portfolio_summary": summary,
                    "open_positions": len(self.engine.positions),
                    "pending_orders": len([o for o in self.engine.orders.values() 
                                         if o.status == OrderStatus.PENDING])
                }
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo estado: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error obteniendo estado: {str(e)}"}
            )
    
    async def _handle_place_order(self, message: MCPMessage) -> MCPResponse:
        """Coloca una orden de trading"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            params = message.params or {}
            required_fields = ['symbol', 'side', 'order_type', 'quantity']
            
            for field in required_fields:
                if field not in params:
                    return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Campo requerido faltante: {field}"}
                    )
            
            # Convertir string a enum si es necesario
            order_type = params['order_type']
            if isinstance(order_type, str):
                order_type = OrderType(order_type.lower())
            
            order_id = self.engine.place_order(
                symbol=params['symbol'],
                side=params['side'],
                order_type=order_type,
                quantity=params['quantity'],
                price=params.get('price'),
                stop_price=params.get('stop_price')
            )
            
            # Notificar a callbacks registrados
            await self._notify_trade_callbacks({
                'event': 'order_placed',
                'order_id': order_id,
                'symbol': params['symbol'],
                'side': params['side'],
                'quantity': params['quantity'],
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"📝 Orden colocada: {order_id} - {params['symbol']} {params['side']}")
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "order_id": order_id,
                    "message": "Orden colocada exitosamente"
                }
            )
            
        except Exception as e:
            logger.error(f"Error colocando orden: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error colocando orden: {str(e)}"}
            )
    
    async def _handle_process_market_data(self, message: MCPMessage) -> MCPResponse:
        """Procesa datos de mercado para ejecutar órdenes"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            params = message.params or {}
            market_data = params.get('market_data', {})
            
            if not market_data:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Datos de mercado requeridos"}
                )
            
            # Procesar datos de mercado
            executed_orders = self.engine.process_market_data(market_data)
            
            # Notificar ejecuciones
            for order_id in executed_orders:
                await self._notify_trade_callbacks({
                    'event': 'order_executed',
                    'order_id': order_id,
                    'timestamp': datetime.now().isoformat()
                })
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "executed_orders": executed_orders,
                    "processed_symbols": list(market_data.keys())
                }
            )
            
        except Exception as e:
            logger.error(f"Error procesando datos de mercado: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error procesando datos: {str(e)}"}
            )
    
    async def _handle_get_positions(self, message: MCPMessage) -> MCPResponse:
        """Obtiene todas las posiciones abiertas"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            positions = self.engine.get_positions_summary()
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "positions": positions,
                    "count": len(positions)
                }
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error obteniendo posiciones: {str(e)}"}
            )
    
    async def _handle_get_portfolio_summary(self, message: MCPMessage) -> MCPResponse:
        """Obtiene resumen completo del portfolio"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            summary = self.engine.get_portfolio_summary()
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "portfolio_summary": summary
                }
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error obteniendo resumen: {str(e)}"}
            )
    
    async def _handle_create_scalping_position(self, message: MCPMessage) -> MCPResponse:
        """Crea una posición de scalping"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            params = message.params or {}
            required_fields = ['symbol', 'direction', 'entry_price']
            
            for field in required_fields:
                if field not in params:
                    return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Campo requerido faltante: {field}"}
                    )
            
            scalping_id = self.engine.create_scalping_position(
                symbol=params['symbol'],
                direction=params['direction'],
                entry_price=params['entry_price'],
                take_profit_pct=params.get('take_profit_pct', 2.0),
                stop_loss_pct=params.get('stop_loss_pct', 1.0),
                position_size_usd=params.get('position_size_usd', 100.0),
                duration_minutes=params.get('duration_minutes', 5)
            )
            
            if scalping_id:
                await self._notify_trade_callbacks({
                    'event': 'scalping_position_created',
                    'scalping_id': scalping_id,
                    'symbol': params['symbol'],
                    'direction': params['direction'],
                    'timestamp': datetime.now().isoformat()
                })
                
                return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                        "success": True,
                        "scalping_id": scalping_id,
                        "message": "Posición de scalping creada"
                    }
                )
            else:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Error creando posición de scalping"}
                )
            
        except Exception as e:
            logger.error(f"Error creando scalping: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error creando scalping: {str(e)}"}
            )
    
    async def _handle_get_scalping_stats(self, message: MCPMessage) -> MCPResponse:
        """Obtiene estadísticas de scalping"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            stats = self.engine.get_scalping_statistics()
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "scalping_statistics": stats
                }
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de scalping: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error obteniendo estadísticas: {str(e)}"}
            )
    
    async def _handle_register_trade_callback(self, message: MCPMessage) -> MCPResponse:
        """Registra un callback para notificaciones de trades"""
        try:
            params = message.params or {}
            callback_id = params.get('callback_id', message.client_id)
            
            self.trade_callbacks.add(callback_id)
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "callback_id": callback_id,
                    "message": "Callback de trades registrado"
                }
            )
            
        except Exception as e:
            logger.error(f"Error registrando callback: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error registrando callback: {str(e)}"}
            )
    
    async def _notify_trade_callbacks(self, trade_data: Dict[str, Any]):
        """Notifica a todos los callbacks registrados sobre eventos de trading"""
        if not self.trade_callbacks:
            return
        
        notification = {
            "method": "trade_notification",
            "params": trade_data
        }
        
        # Enviar notificación a todos los callbacks registrados
        for callback_id in self.trade_callbacks.copy():
            try:
                await self.send_notification(callback_id, notification)
            except Exception as e:
                logger.warning(f"Error enviando notificación a {callback_id}: {e}")
                # Remover callback si falla
                self.trade_callbacks.discard(callback_id)
    
    # Handlers adicionales para completar la funcionalidad
    async def _handle_cancel_order(self, message: MCPMessage) -> MCPResponse:
        """Cancela una orden pendiente"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            params = message.params or {}
            order_id = params.get('order_id')
            
            if not order_id:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "order_id requerido"}
                )
            
            success = self.engine.cancel_order(order_id)
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": success,
                    "message": "Orden cancelada" if success else "Orden no encontrada"
                }
            )
            
        except Exception as e:
            logger.error(f"Error cancelando orden: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error cancelando orden: {str(e)}"}
            )
    
    async def _handle_get_orders(self, message: MCPMessage) -> MCPResponse:
        """Obtiene órdenes pendientes"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            orders = []
            for order in self.engine.orders.values():
                orders.append({
                    'order_id': order.order_id,
                    'symbol': order.symbol,
                    'side': order.side,
                    'order_type': order.order_type.value,
                    'quantity': order.quantity,
                    'price': order.price,
                    'status': order.status.value,
                    'created_at': order.created_at.isoformat()
                })
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "orders": orders,
                    "count": len(orders)
                }
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo órdenes: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error obteniendo órdenes: {str(e)}"}
            )
    
    async def _handle_get_trade_history(self, message: MCPMessage) -> MCPResponse:
        """Obtiene historial de trades"""
        try:
            if not self.engine:
                return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": "Motor no inicializado"}
                )
            
            params = message.params or {}
            limit = params.get('limit', 50)
            
            history = self.engine.trade_history[-limit:] if limit else self.engine.trade_history
            
            return MCPResponse(
                request_id=message.id,
                success=True,
                data={
                    "success": True,
                    "trade_history": history,
                    "count": len(history)
                }
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error={"code": -1, "message": f"Error obteniendo historial: {str(e)}"}
            )
    
    # Handlers stub para funcionalidades adicionales
    async def _handle_get_order_history(self, message: MCPMessage) -> MCPResponse:
        """Obtiene historial de órdenes"""
        # Implementación similar a get_trade_history pero para órdenes
        pass
    
    async def _handle_close_position(self, message: MCPMessage) -> MCPResponse:
        """Cierra una posición específica"""
        # Implementación para cerrar posición individual
        pass
    
    async def _handle_close_all_positions(self, message: MCPMessage) -> MCPResponse:
        """Cierra todas las posiciones"""
        # Implementación para cerrar todas las posiciones
        pass
    
    async def _handle_update_position_stops(self, message: MCPMessage) -> MCPResponse:
        """Actualiza stop loss y take profit de una posición"""
        # Implementación para actualizar stops
        pass
    
    async def _handle_update_price(self, message: MCPMessage) -> MCPResponse:
        """Actualiza precio de un símbolo específico"""
        # Implementación para actualizar precio individual
        pass
    
    async def _handle_get_performance_metrics(self, message: MCPMessage) -> MCPResponse:
        """Obtiene métricas de performance detalladas"""
        # Implementación para métricas avanzadas
        pass
    
    async def _handle_save_state(self, message: MCPMessage) -> MCPResponse:
        """Guarda el estado del motor"""
        # Implementación para guardar estado
        pass
    
    async def _handle_load_state(self, message: MCPMessage) -> MCPResponse:
        """Carga el estado del motor"""
        # Implementación para cargar estado
        pass
    
    async def _handle_register_position_callback(self, message: MCPMessage) -> MCPResponse:
        """Registra callback para notificaciones de posiciones"""
        # Implementación para callbacks de posiciones
        pass
    
    async def _handle_unregister_callback(self, message: MCPMessage) -> MCPResponse:
        """Desregistra un callback"""
        # Implementación para desregistrar callbacks
        pass
    
    # Métodos abstractos requeridos por MCPBase
    
    def get_info(self) -> Dict[str, Any]:
        """Obtiene información específica del MCP"""
        return {
            "name": self.name,
            "type": "paper_trading",
            "version": "1.0.0",
            "description": "Sistema de paper trading para SICAR",
            "capabilities": [
                "order_management",
                "position_tracking", 
                "portfolio_analysis",
                "scalping_operations",
                "risk_management"
            ],
            "engine_active": self.is_active,
            "engine_initialized": self.engine is not None,
            "default_config": self.default_config
        }
    
    async def initialize(self) -> bool:
        """Inicializa el MCP"""
        try:
            self.logger.info("Inicializando Paper Trading MCP...")
            
            # Registrar handlers para todos los métodos
            self.register_handler("initialize_engine", self._handle_initialize_engine)
            self.register_handler("reset_engine", self._handle_reset_engine)
            self.register_handler("place_order", self._handle_place_order)
            self.register_handler("cancel_order", self._handle_cancel_order)
            self.register_handler("get_orders", self._handle_get_orders)
            self.register_handler("get_positions", self._handle_get_positions)
            self.register_handler("process_market_data", self._handle_process_market_data)
            self.register_handler("get_portfolio_summary", self._handle_get_portfolio_summary)
            self.register_handler("get_trade_history", self._handle_get_trade_history)
            self.register_handler("create_scalping_position", self._handle_create_scalping_position)
            self.register_handler("get_scalping_stats", self._handle_get_scalping_stats)
            self.register_handler("get_engine_status", self._handle_get_engine_status)
            self.register_handler("register_trade_callback", self._handle_register_trade_callback)
            
            self.logger.info("Paper Trading MCP inicializado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error inicializando Paper Trading MCP: {e}")
            return False
    
    async def process_message(self, message: MCPMessage) -> MCPResponse:
        """Procesa un mensaje específico del MCP"""
        try:
            # Los mensajes se procesan a través de los handlers registrados
            # Este método se llama cuando no hay handler específico
            
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error=f"Método no soportado: {message.method}"
            )
            
        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error=str(e)
            )

if __name__ == "__main__":
    # Prueba básica del MCP
    async def test_paper_trading_mcp():
        mcp = PaperTradingMCP()
        await mcp.start()
        
        # Mantener el MCP corriendo
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await mcp.stop()
    
    asyncio.run(test_paper_trading_mcp())