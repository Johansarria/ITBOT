"""
MCP Base Classes
Clases base para el framework MCP de SICAR
"""

import json
import uuid
import asyncio
import websockets
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class MCPMessageType(Enum):
    """Tipos de mensajes MCP"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"

class MCPStatus(Enum):
    """Estados de un MCP"""
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

@dataclass
class MCPMessage:
    """Mensaje estándar del protocolo MCP"""
    id: str
    type: MCPMessageType
    method: str
    params: Dict[str, Any]
    timestamp: datetime
    source: str
    target: Optional[str] = None
    
    def to_json(self) -> str:
        """Convierte el mensaje a JSON"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['type'] = self.type.value
        return json.dumps(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPMessage':
        """Crea un mensaje desde JSON"""
        data = json.loads(json_str)
        data['type'] = MCPMessageType(data['type'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """Crea un mensaje desde un diccionario"""
        data = data.copy()  # No modificar el original
        data['type'] = MCPMessageType(data['type'])
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class MCPResponse:
    """Respuesta estándar del protocolo MCP"""
    request_id: str
    success: bool
    data: Any
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte la respuesta a diccionario"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convierte la respuesta a JSON"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'MCPResponse':
        """Crea una respuesta desde JSON"""
        data = json.loads(json_str)
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class MCPBase(ABC):
    """Clase base para todos los MCPs"""
    
    def __init__(self, name: str, port: int = None):
        self.name = name
        self.port = port or self._get_default_port()
        self.status = MCPStatus.INITIALIZING
        self.message_handlers: Dict[str, Callable] = {}
        self.websocket = None
        self.server = None
        self.running = False
        self.logger = logging.getLogger(f"mcp.{name}")
        
        # Registrar handlers básicos
        self._register_base_handlers()
    
    def _get_default_port(self) -> int:
        """Obtiene el puerto por defecto basado en el nombre"""
        port_map = {
            "breakout_detector": 8001,
            "paper_trading": 8002,
            "scalping_engine": 8003,
            "portfolio_optimizer": 8004,
            "session_detector": 8005
        }
        return port_map.get(self.name, 8000)
    
    def _register_base_handlers(self):
        """Registra handlers básicos comunes a todos los MCPs"""
        self.register_handler("ping", self._handle_ping)
        self.register_handler("status", self._handle_status)
        self.register_handler("stop", self._handle_stop)
        self.register_handler("get_info", self._handle_get_info)
    
    def register_handler(self, method: str, handler: Callable):
        """Registra un handler para un método específico"""
        self.message_handlers[method] = handler
        self.logger.debug(f"Handler registrado para método: {method}")
    
    async def _handle_ping(self, message: MCPMessage) -> MCPResponse:
        """Handler para ping"""
        return MCPResponse(
            request_id=message.id,
            success=True,
            data={"pong": True, "timestamp": datetime.now().isoformat()}
        )
    
    async def _handle_status(self, message: MCPMessage) -> MCPResponse:
        """Handler para obtener estado"""
        return MCPResponse(
            request_id=message.id,
            success=True,
            data={
                "name": self.name,
                "status": self.status.value,
                "port": self.port,
                "running": self.running
            }
        )
    
    async def _handle_stop(self, message: MCPMessage) -> MCPResponse:
        """Handler para detener el MCP"""
        await self.stop()
        return MCPResponse(
            request_id=message.id,
            success=True,
            data={"message": "MCP stopped successfully"}
        )
    
    async def _handle_get_info(self, message: MCPMessage) -> MCPResponse:
        """Handler para obtener información del MCP"""
        return MCPResponse(
            request_id=message.id,
            success=True,
            data=self.get_info()
        )
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Obtiene información específica del MCP"""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Inicializa el MCP"""
        pass
    
    @abstractmethod
    async def process_message(self, message: MCPMessage) -> MCPResponse:
        """Procesa un mensaje específico del MCP"""
        pass
    
    async def start(self) -> bool:
        """Inicia el MCP"""
        try:
            self.logger.info(f"Iniciando MCP {self.name} en puerto {self.port}")
            
            # Inicializar el MCP específico
            if not await self.initialize():
                self.logger.error(f"Error al inicializar MCP {self.name}")
                return False
            
            # Iniciar servidor WebSocket
            self.server = await websockets.serve(
                self._handle_websocket,
                "localhost",
                self.port
            )
            
            self.status = MCPStatus.RUNNING
            self.running = True
            self.logger.info(f"MCP {self.name} iniciado exitosamente en puerto {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error al iniciar MCP {self.name}: {e}")
            self.status = MCPStatus.ERROR
            return False
    
    async def stop(self):
        """Detiene el MCP"""
        try:
            self.logger.info(f"Deteniendo MCP {self.name}")
            self.running = False
            self.status = MCPStatus.STOPPED
            
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.logger.info(f"MCP {self.name} detenido exitosamente")
            
        except Exception as e:
            self.logger.error(f"Error al detener MCP {self.name}: {e}")
    
    async def _handle_websocket(self, websocket, path):
        """Maneja conexiones WebSocket"""
        self.logger.debug(f"Nueva conexión WebSocket desde {websocket.remote_address}")
        
        try:
            async for message_str in websocket:
                try:
                    # Parsear mensaje
                    message = MCPMessage.from_json(message_str)
                    self.logger.debug(f"Mensaje recibido: {message.method}")
                    
                    # Procesar mensaje
                    if message.method in self.message_handlers:
                        result = await self.message_handlers[message.method](message)
                        # Si el handler devuelve un diccionario, envolverlo en MCPResponse
                        if isinstance(result, dict):
                            response = MCPResponse(
                                request_id=message.id,
                                success=result.get("success", True),
                                data=result
                            )
                        else:
                            response = result
                    else:
                        response = await self.process_message(message)
                    
                    # Enviar respuesta
                    await websocket.send(response.to_json())
                    
                except json.JSONDecodeError as e:
                    error_response = MCPResponse(
                        request_id="unknown",
                        success=False,
                        data=None,
                        error=f"Error de JSON: {e}"
                    )
                    await websocket.send(error_response.to_json())
                    
                except Exception as e:
                    self.logger.error(f"Error procesando mensaje: {e}")
                    error_response = MCPResponse(
                        request_id=getattr(message, 'id', 'unknown'),
                        success=False,
                        data=None,
                        error=str(e)
                    )
                    await websocket.send(error_response.to_json())
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.debug("Conexión WebSocket cerrada")
        except Exception as e:
            self.logger.error(f"Error en WebSocket: {e}")