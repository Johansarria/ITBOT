"""
MCP Server
Servidor WebSocket para MCPs con protocolo JSON-RPC
"""

import asyncio
import json
import logging
import uuid
import websockets
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from .mcp_base import MCPMessage, MCPResponse, MCPMessageType

logger = logging.getLogger(__name__)

class MCPServer:
    """Servidor WebSocket para comunicación MCP"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.running = False
        self.logger = logging.getLogger(f"mcp_server_{port}")
        
        # Estadísticas
        self.stats = {
            "start_time": None,
            "connections": 0,
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0
        }
        
        # Registrar handlers básicos
        self.register_handler("ping", self._handle_ping)
        self.register_handler("status", self._handle_status)
    
    def register_handler(self, method: str, handler: Callable):
        """Registra un manejador para un método específico"""
        self.message_handlers[method] = handler
        self.logger.debug(f"Handler registrado para método: {method}")
    
    async def start(self):
        """Inicia el servidor WebSocket"""
        try:
            self.logger.info(f"Iniciando servidor MCP en {self.host}:{self.port}")
            
            self.server = await websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.running = True
            self.stats["start_time"] = datetime.now()
            
            self.logger.info(f"Servidor MCP iniciado en {self.host}:{self.port}")
            
        except Exception as e:
            self.logger.error(f"Error iniciando servidor: {e}")
            raise
    
    async def stop(self):
        """Detiene el servidor WebSocket"""
        self.logger.info("Deteniendo servidor MCP...")
        self.running = False
        
        # Cerrar todas las conexiones
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients.values()],
                return_exceptions=True
            )
        
        # Cerrar servidor
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        self.clients.clear()
        self.logger.info("Servidor MCP detenido")
    
    async def _handle_client(self, websocket, path):
        """Maneja una conexión de cliente"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        self.logger.info(f"Nueva conexión de cliente: {client_id}")
        
        self.clients[client_id] = websocket
        self.stats["connections"] += 1
        
        try:
            async for message in websocket:
                await self._process_message(websocket, message, client_id)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Cliente {client_id} desconectado")
        except Exception as e:
            self.logger.error(f"Error manejando cliente {client_id}: {e}")
            self.stats["errors"] += 1
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def _process_message(self, websocket, raw_message: str, client_id: str):
        """Procesa un mensaje recibido"""
        try:
            self.stats["messages_received"] += 1
            
            # Parsear mensaje JSON
            message_data = json.loads(raw_message)
            message = MCPMessage.from_dict(message_data)
            
            self.logger.debug(f"Mensaje recibido de {client_id}: {message.method}")
            
            # Procesar según el tipo de mensaje
            if message.type == MCPMessageType.REQUEST:
                response = await self._handle_request(message)
                await self._send_response(websocket, response)
            elif message.type == MCPMessageType.NOTIFICATION:
                await self._handle_notification(message)
            else:
                self.logger.warning(f"Tipo de mensaje no soportado: {message.type}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parseando JSON de {client_id}: {e}")
            error_response = MCPResponse(
                request_id="unknown",
                success=False,
                data=None,
                error=f"JSON inválido: {str(e)}"
            )
            await self._send_response(websocket, error_response)
            
        except Exception as e:
            self.logger.error(f"Error procesando mensaje de {client_id}: {e}")
            self.stats["errors"] += 1
            
            error_response = MCPResponse(
                request_id=getattr(message, 'id', "unknown") if 'message' in locals() else "unknown",
                success=False,
                data=None,
                error=f"Error interno: {str(e)}"
            )
            await self._send_response(websocket, error_response)
    
    async def _handle_request(self, message: MCPMessage) -> MCPResponse:
        """Maneja una solicitud y devuelve una respuesta"""
        try:
            # Buscar handler para el método
            if message.method in self.message_handlers:
                handler = self.message_handlers[message.method]
                
                # Ejecutar handler
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(message)
                else:
                    result = handler(message)
                
                return MCPResponse(
                    request_id=message.id,
                    success=True,
                    data=result
                )
            else:
                return MCPResponse(
                    request_id=message.id,
                    success=False,
                    data=None,
                    error=f"Método no encontrado: {message.method}"
                )
                
        except Exception as e:
            self.logger.error(f"Error ejecutando handler para {message.method}: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data=None,
                error=f"Error ejecutando método: {str(e)}"
            )
    
    async def _handle_notification(self, message: MCPMessage):
        """Maneja una notificación (sin respuesta)"""
        try:
            if message.method in self.message_handlers:
                handler = self.message_handlers[message.method]
                
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
                    
        except Exception as e:
            self.logger.error(f"Error ejecutando handler de notificación para {message.method}: {e}")
    
    async def _send_response(self, websocket, response: MCPResponse):
        """Envía una respuesta al cliente"""
        try:
            self.logger.debug(f"Enviando respuesta de tipo: {type(response)}")
            if not isinstance(response, MCPResponse):
                self.logger.error(f"Se esperaba MCPResponse pero se recibió: {type(response)}")
                return
            response_json = json.dumps(response.to_dict())
            await websocket.send(response_json)
            self.stats["messages_sent"] += 1
            
        except Exception as e:
            self.logger.error(f"Error enviando respuesta: {e}")
            self.stats["errors"] += 1
    
    async def broadcast(self, method: str, params: Dict[str, Any] = None):
        """Envía una notificación a todos los clientes conectados"""
        if not self.clients:
            return
        
        message = MCPMessage(
            id=str(uuid.uuid4()),
            type=MCPMessageType.NOTIFICATION,
            method=method,
            params=params or {},
            timestamp=datetime.now(),
            source=self.name
        )
        
        message_json = message.to_json()
        
        # Enviar a todos los clientes
        disconnected_clients = []
        for client_id, websocket in self.clients.items():
            try:
                await websocket.send(message_json)
                self.stats["messages_sent"] += 1
            except Exception as e:
                self.logger.error(f"Error enviando broadcast a {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Limpiar clientes desconectados
        for client_id in disconnected_clients:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def _handle_ping(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler para ping"""
        return {
            "pong": True,
            "timestamp": datetime.now().isoformat(),
            "server_info": {
                "host": self.host,
                "port": self.port,
                "clients": len(self.clients)
            }
        }
    
    async def _handle_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler para status"""
        uptime = None
        if self.stats["start_time"]:
            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        return {
            "status": "running" if self.running else "stopped",
            "host": self.host,
            "port": self.port,
            "clients_connected": len(self.clients),
            "uptime_seconds": uptime,
            "statistics": self.stats.copy(),
            "handlers": list(self.message_handlers.keys())
        }
    
    def get_client_count(self) -> int:
        """Obtiene el número de clientes conectados"""
        return len(self.clients)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del servidor"""
        return self.stats.copy()
    
    def is_running(self) -> bool:
        """Verifica si el servidor está corriendo"""
        return self.running