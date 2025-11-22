"""
MCP Manager
Gestor central para coordinar todos los MCPs de SICAR
"""

import asyncio
import logging
import threading
import time
from typing import Dict, Any, List, Optional, Type
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

from .mcp_base import MCPBase, MCPStatus
from .mcp_client import MCPClient

logger = logging.getLogger(__name__)

class MCPManager:
    """Gestor central para todos los MCPs de SICAR"""
    
    def __init__(self, max_workers: int = 4):
        self.mcps: Dict[str, MCPBase] = {}
        self.mcp_processes: Dict[str, asyncio.Task] = {}
        self.client = MCPClient("sicar_manager")
        self.running = False
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger("mcp_manager")
        
        # Configuración de monitoreo
        self.health_check_interval = 30  # segundos
        self.restart_attempts = 3
        self.restart_delay = 5  # segundos
        
        # Estadísticas
        self.stats = {
            "start_time": None,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "restarts": 0
        }
    
    def register_mcp(self, mcp_class: Type[MCPBase], *args, **kwargs) -> bool:
        """Registra un MCP para ser gestionado"""
        try:
            mcp_instance = mcp_class(*args, **kwargs)
            self.mcps[mcp_instance.name] = mcp_instance
            
            # Registrar en el cliente
            self.client.register_mcp(
                mcp_instance.name,
                "localhost",
                mcp_instance.port
            )
            
            self.logger.info(f"MCP {mcp_instance.name} registrado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error registrando MCP: {e}")
            return False
    
    async def start_all(self) -> Dict[str, bool]:
        """Inicia todos los MCPs registrados"""
        self.logger.info("Iniciando todos los MCPs...")
        self.stats["start_time"] = datetime.now()
        self.running = True
        
        results = {}
        
        # Iniciar cada MCP en su propio proceso
        for name, mcp in self.mcps.items():
            try:
                self.logger.info(f"Iniciando MCP {name}...")
                
                # Crear tarea asíncrona para el MCP
                task = asyncio.create_task(self._run_mcp(mcp))
                self.mcp_processes[name] = task
                
                # Esperar un poco para que se inicie
                await asyncio.sleep(1)
                
                # Verificar que se inició correctamente
                if await self._wait_for_mcp_ready(name):
                    results[name] = True
                    self.logger.info(f"MCP {name} iniciado exitosamente")
                else:
                    results[name] = False
                    self.logger.error(f"MCP {name} no se pudo iniciar")
                    
            except Exception as e:
                self.logger.error(f"Error iniciando MCP {name}: {e}")
                results[name] = False
        
        # Conectar cliente a todos los MCPs
        await self.client.connect_to_all()
        
        # Iniciar monitoreo de salud
        asyncio.create_task(self._health_monitor())
        
        self.logger.info(f"Proceso de inicio completado. Resultados: {results}")
        return results
    
    async def stop_all(self):
        """Detiene todos los MCPs"""
        self.logger.info("Deteniendo todos los MCPs...")
        self.running = False
        
        # Desconectar cliente
        await self.client.disconnect_from_all()
        
        # Detener cada MCP
        for name, mcp in self.mcps.items():
            try:
                await mcp.stop()
                self.logger.info(f"MCP {name} detenido")
            except Exception as e:
                self.logger.error(f"Error deteniendo MCP {name}: {e}")
        
        # Cancelar tareas
        for name, task in self.mcp_processes.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.mcp_processes.clear()
        self.executor.shutdown(wait=True)
        self.logger.info("Todos los MCPs detenidos")
    
    async def restart_mcp(self, mcp_name: str) -> bool:
        """Reinicia un MCP específico"""
        if mcp_name not in self.mcps:
            self.logger.error(f"MCP {mcp_name} no está registrado")
            return False
        
        try:
            self.logger.info(f"Reiniciando MCP {mcp_name}...")
            
            # Detener MCP actual
            if mcp_name in self.mcp_processes:
                task = self.mcp_processes[mcp_name]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.mcp_processes[mcp_name]
            
            await self.mcps[mcp_name].stop()
            
            # Esperar antes de reiniciar
            await asyncio.sleep(self.restart_delay)
            
            # Reiniciar MCP
            task = asyncio.create_task(self._run_mcp(self.mcps[mcp_name]))
            self.mcp_processes[mcp_name] = task
            
            # Verificar que se reinició correctamente
            if await self._wait_for_mcp_ready(mcp_name):
                # Reconectar cliente
                await self.client.connect_to_mcp(mcp_name)
                self.stats["restarts"] += 1
                self.logger.info(f"MCP {mcp_name} reiniciado exitosamente")
                return True
            else:
                self.logger.error(f"MCP {mcp_name} no se pudo reiniciar")
                return False
                
        except Exception as e:
            self.logger.error(f"Error reiniciando MCP {mcp_name}: {e}")
            return False
    
    async def send_request(self, mcp_name: str, method: str, params: Dict[str, Any] = None) -> Any:
        """Envía una solicitud a un MCP específico"""
        try:
            self.stats["total_requests"] += 1
            response = await self.client.send_request(mcp_name, method, params)
            
            if response.success:
                self.stats["successful_requests"] += 1
                return response.data
            else:
                self.stats["failed_requests"] += 1
                self.logger.error(f"Error en solicitud a {mcp_name}.{method}: {response.error}")
                return None
                
        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Error enviando solicitud a {mcp_name}.{method}: {e}")
            return None
    
    async def broadcast_notification(self, method: str, params: Dict[str, Any] = None):
        """Envía una notificación a todos los MCPs"""
        for mcp_name in self.mcps:
            try:
                await self.client.send_notification(mcp_name, method, params)
            except Exception as e:
                self.logger.error(f"Error enviando notificación a {mcp_name}: {e}")
    
    async def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el estado de todos los MCPs"""
        return await self.client.get_all_statuses()
    
    async def get_health_report(self) -> Dict[str, Any]:
        """Obtiene un reporte de salud completo"""
        statuses = await self.get_all_statuses()
        
        healthy_count = sum(1 for status in statuses.values() if status.get("status") == "running")
        total_count = len(self.mcps)
        
        uptime = None
        if self.stats["start_time"]:
            uptime = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        return {
            "manager_status": "running" if self.running else "stopped",
            "total_mcps": total_count,
            "healthy_mcps": healthy_count,
            "unhealthy_mcps": total_count - healthy_count,
            "uptime_seconds": uptime,
            "statistics": self.stats.copy(),
            "mcp_statuses": statuses
        }
    
    async def _run_mcp(self, mcp: MCPBase):
        """Ejecuta un MCP en su propio contexto"""
        try:
            await mcp.start()
            
            # Mantener el MCP corriendo
            while self.running and mcp.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error ejecutando MCP {mcp.name}: {e}")
            mcp.status = MCPStatus.ERROR
        finally:
            if mcp.running:
                await mcp.stop()
    
    async def _wait_for_mcp_ready(self, mcp_name: str, timeout: int = 10) -> bool:
        """Espera a que un MCP esté listo"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if await self.client.ping_mcp(mcp_name):
                    return True
            except:
                pass
            await asyncio.sleep(0.5)
        
        return False
    
    async def _health_monitor(self):
        """Monitor de salud que verifica periódicamente los MCPs"""
        while self.running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if not self.running:
                    break
                
                # Verificar salud de cada MCP
                for mcp_name in self.mcps:
                    if not await self.client.ping_mcp(mcp_name):
                        self.logger.warning(f"MCP {mcp_name} no responde, intentando reiniciar...")
                        
                        # Intentar reiniciar
                        restart_success = False
                        for attempt in range(self.restart_attempts):
                            if await self.restart_mcp(mcp_name):
                                restart_success = True
                                break
                            await asyncio.sleep(self.restart_delay)
                        
                        if not restart_success:
                            self.logger.error(f"No se pudo reiniciar MCP {mcp_name} después de {self.restart_attempts} intentos")
                
            except Exception as e:
                self.logger.error(f"Error en monitor de salud: {e}")
    
    def get_mcp_names(self) -> List[str]:
        """Obtiene lista de nombres de MCPs registrados"""
        return list(self.mcps.keys())
    
    def is_mcp_registered(self, mcp_name: str) -> bool:
        """Verifica si un MCP está registrado"""
        return mcp_name in self.mcps
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del manager"""
        return self.stats.copy()