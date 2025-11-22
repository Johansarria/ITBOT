"""
MCP Client
Cliente para comunicarse con MCPs remotos
"""

import asyncio
import websockets
import json
import uuid
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from .mcp_base import MCPMessage, MCPResponse, MCPMessageType

logger = logging.getLogger(__name__)

class MCPClient:
    """Cliente para comunicarse con MCPs"""
    
    def __init__(self, name: str = "sicar_dashboard"):
        self.name = name
        self.connections: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.mcp_addresses: Dict[str, str] = {}
        self.response_futures: Dict[str, asyncio.Future] = {}
        self.logger = logging.getLogger(f"mcp_client.{name}")
        
        # Configuración de timeouts
        self.connection_timeout = 5.0
        self.request_timeout = 10.0
    
    def register_mcp(self, mcp_name: str, host: str = "localhost", port: int = 8000):
        """Registra la dirección de un MCP"""
        address = f"ws://{host}:{port}"
        self.mcp_addresses[mcp_name] = address
        self.logger.info(f"MCP {mcp_name} registrado en {address}")
    
    async def connect_to_mcp(self, mcp_name: str) -> bool:
        """Conecta a un MCP específico"""
        if mcp_name not in self.mcp_addresses:
            self.logger.error(f"MCP {mcp_name} no está registrado")
            return False
        
        try:
            address = self.mcp_addresses[mcp_name]
            self.logger.info(f"Conectando a MCP {mcp_name} en {address}")
            
            websocket = await asyncio.wait_for(
                websockets.connect(address),
                timeout=self.connection_timeout
            )
            
            self.connections[mcp_name] = websocket
            self.logger.info(f"Conectado exitosamente a MCP {mcp_name}")
            
            # Iniciar listener para respuestas
            asyncio.create_task(self._listen_responses(mcp_name, websocket))
            
            return True
            
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout conectando a MCP {mcp_name}")
            return False
        except Exception as e:
            self.logger.error(f"Error conectando a MCP {mcp_name}: {e}")
            return False
    
    async def disconnect_from_mcp(self, mcp_name: str):
        """Desconecta de un MCP específico"""
        if mcp_name in self.connections:
            try:
                await self.connections[mcp_name].close()
                del self.connections[mcp_name]
                self.logger.info(f"Desconectado de MCP {mcp_name}")
            except Exception as e:
                self.logger.error(f"Error desconectando de MCP {mcp_name}: {e}")
    
    async def connect_to_all(self) -> Dict[str, bool]:
        """Conecta a todos los MCPs registrados"""
        results = {}
        for mcp_name in self.mcp_addresses:
            results[mcp_name] = await self.connect_to_mcp(mcp_name)
        return results
    
    async def disconnect_from_all(self):
        """Desconecta de todos los MCPs"""
        for mcp_name in list(self.connections.keys()):
            await self.disconnect_from_mcp(mcp_name)
    
    async def send_request(self, mcp_name: str, method: str, params: Dict[str, Any] = None) -> MCPResponse:
        """Envía una solicitud a un MCP y espera respuesta"""
        if mcp_name not in self.connections:
            if not await self.connect_to_mcp(mcp_name):
                return MCPResponse(
                    request_id="",
                    success=False,
                    data=None,
                    error=f"No se pudo conectar a MCP {mcp_name}"
                )
        
        try:
            # Crear mensaje
            request_id = str(uuid.uuid4())
            message = MCPMessage(
                id=request_id,
                type=MCPMessageType.REQUEST,
                method=method,
                params=params or {},
                timestamp=datetime.now(),
                source=self.name,
                target=mcp_name
            )
            
            # Crear future para la respuesta
            future = asyncio.Future()
            self.response_futures[request_id] = future
            
            # Enviar mensaje
            websocket = self.connections[mcp_name]
            await websocket.send(message.to_json())
            
            # Esperar respuesta con timeout
            try:
                response_json = await asyncio.wait_for(future, timeout=self.request_timeout)
                return MCPResponse.from_json(response_json)
            except asyncio.TimeoutError:
                return MCPResponse(
                    request_id=request_id,
                    success=False,
                    data=None,
                    error=f"Timeout esperando respuesta de MCP {mcp_name}"
                )
            finally:
                # Limpiar future
                if request_id in self.response_futures:
                    del self.response_futures[request_id]
                    
        except Exception as e:
            self.logger.error(f"Error enviando solicitud a MCP {mcp_name}: {e}")
            return MCPResponse(
                request_id="",
                success=False,
                data=None,
                error=str(e)
            )
    
    async def send_notification(self, mcp_name: str, method: str, params: Dict[str, Any] = None):
        """Envía una notificación a un MCP (sin esperar respuesta)"""
        if mcp_name not in self.connections:
            if not await self.connect_to_mcp(mcp_name):
                self.logger.error(f"No se pudo enviar notificación a MCP {mcp_name}")
                return
        
        try:
            message = MCPMessage(
                id=str(uuid.uuid4()),
                type=MCPMessageType.NOTIFICATION,
                method=method,
                params=params or {},
                timestamp=datetime.now(),
                source=self.name,
                target=mcp_name
            )
            
            websocket = self.connections[mcp_name]
            await websocket.send(message.to_json())
            
        except Exception as e:
            self.logger.error(f"Error enviando notificación a MCP {mcp_name}: {e}")
    
    async def ping_mcp(self, mcp_name: str) -> bool:
        """Hace ping a un MCP para verificar conectividad"""
        try:
            response = await self.send_request(mcp_name, "ping", {"timestamp": datetime.now().isoformat()})
            return response.success
        except Exception as e:
            self.logger.error(f"Error haciendo ping a MCP {mcp_name}: {e}")
            return False
    
    async def get_mcp_status(self, mcp_name: str) -> Optional[Dict[str, Any]]:
        """Obtiene el estado de un MCP"""
        try:
            response = await self.send_request(mcp_name, "status")
            if response.success:
                return response.data
            return None
        except Exception as e:
            self.logger.error(f"Error obteniendo estado de MCP {mcp_name}: {e}")
            return None
    
    async def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el estado de todos los MCPs conectados"""
        statuses = {}
        for mcp_name in self.connections:
            status = await self.get_mcp_status(mcp_name)
            if status:
                statuses[mcp_name] = status
        return statuses
    
    async def _listen_responses(self, mcp_name: str, websocket: websockets.WebSocketClientProtocol):
        """Escucha respuestas de un MCP específico"""
        try:
            async for message_str in websocket:
                try:
                    response_data = json.loads(message_str)
                    request_id = response_data.get('request_id')
                    
                    if request_id and request_id in self.response_futures:
                        future = self.response_futures[request_id]
                        if not future.done():
                            future.set_result(message_str)
                    
                except json.JSONDecodeError as e:
                    self.logger.error(f"Error decodificando respuesta de MCP {mcp_name}: {e}")
                except Exception as e:
                    self.logger.error(f"Error procesando respuesta de MCP {mcp_name}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Conexión con MCP {mcp_name} cerrada")
            if mcp_name in self.connections:
                del self.connections[mcp_name]
        except Exception as e:
            self.logger.error(f"Error escuchando respuestas de MCP {mcp_name}: {e}")
    
    def is_connected(self, mcp_name: str) -> bool:
        """Verifica si está conectado a un MCP"""
        return mcp_name in self.connections and not self.connections[mcp_name].closed
    
    def get_connected_mcps(self) -> List[str]:
        """Obtiene lista de MCPs conectados"""
        return [name for name in self.connections if not self.connections[name].closed]