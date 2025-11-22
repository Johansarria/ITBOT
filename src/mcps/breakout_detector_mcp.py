"""
Breakout Detector MCP
Detector de breakouts como Micro-Controller Process independiente
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import numpy as np
import pandas as pd
import pytz

from mcp_framework import MCPBase, MCPMessage, MCPResponse
from enhanced_config import CONFIG
from enhanced_logger import SICAR_LOGGER
from enhanced_breakout_detector import (
    BreakoutType, BreakoutStrength, BreakoutSignal, 
    EnhancedBreakoutDetector
)

class BreakoutDetectorMCP(MCPBase):
    """MCP para detección de breakouts independiente"""
    
    def __init__(self, name: str = "breakout_detector", port: int = 8766):
        super().__init__(name, port)
        
        # Detector de breakouts interno
        self.detector = EnhancedBreakoutDetector()
        
        # Estado del MCP
        self.detection_active = False
        self.last_signals: Dict[str, Dict] = {}
        self.signal_history: List[Dict] = []
        self.max_history_size = 1000
        
        # Estadísticas
        self.stats = {
            "signals_generated": 0,
            "bullish_signals": 0,
            "bearish_signals": 0,
            "strong_signals": 0,
            "detection_cycles": 0,
            "last_signal_time": None,
            "uptime_start": None
        }
        
        # Configuración de callbacks
        self.external_callbacks: List[str] = []  # MCPs que quieren recibir señales
        
        # Registrar handlers específicos del detector
        self.register_handler("start_detection", self._handle_start_detection)
        self.register_handler("stop_detection", self._handle_stop_detection)
        self.register_handler("get_signals", self._handle_get_signals)
        self.register_handler("get_signal_history", self._handle_get_signal_history)
        self.register_handler("update_price_data", self._handle_update_price_data)
        self.register_handler("get_detector_status", self._handle_get_detector_status)
        self.register_handler("update_sensitivity", self._handle_update_sensitivity)
        self.register_handler("register_callback", self._handle_register_callback)
        self.register_handler("unregister_callback", self._handle_unregister_callback)
        self.register_handler("force_detection", self._handle_force_detection)
        self.register_handler("get_stats", self._handle_get_stats)
        
        # Configurar logging
        self.logger = logging.getLogger(f"BreakoutDetectorMCP_{self.name}")
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self.logger.info("BreakoutDetectorMCP inicializado")
    
    async def start(self):
        """Iniciar el MCP del detector de breakouts"""
        await super().start()
        
        # Configurar callback interno para capturar señales
        self.detector.add_alert_callback(self._on_breakout_signal)
        
        self.stats["uptime_start"] = datetime.now()
        self.logger.info("BreakoutDetectorMCP iniciado exitosamente")
    
    async def stop(self):
        """Detener el MCP del detector de breakouts"""
        # Detener detección si está activa
        if self.detection_active:
            await self._stop_detection_internal()
        
        await super().stop()
        self.logger.info("BreakoutDetectorMCP detenido")
    
    def _on_breakout_signal(self, signal: BreakoutSignal):
        """Callback interno para procesar señales de breakout"""
        try:
            # Convertir señal a diccionario
            signal_dict = signal.to_dict()
            
            # Actualizar estadísticas
            self.stats["signals_generated"] += 1
            self.stats["last_signal_time"] = datetime.now().isoformat()
            
            if signal.breakout_type == BreakoutType.BULLISH:
                self.stats["bullish_signals"] += 1
            elif signal.breakout_type == BreakoutType.BEARISH:
                self.stats["bearish_signals"] += 1
            
            if signal.strength in [BreakoutStrength.STRONG, BreakoutStrength.VERY_STRONG]:
                self.stats["strong_signals"] += 1
            
            # Guardar en historial
            self.last_signals[signal.symbol] = signal_dict
            self.signal_history.append(signal_dict)
            
            # Mantener tamaño del historial
            if len(self.signal_history) > self.max_history_size:
                self.signal_history = self.signal_history[-self.max_history_size:]
            
            # Notificar a MCPs registrados
            asyncio.create_task(self._notify_signal_callbacks(signal_dict))
            
            self.logger.info(f"Señal de breakout procesada: {signal.symbol} {signal.breakout_type.value}")
            
        except Exception as e:
            self.logger.error(f"Error procesando señal de breakout: {e}")
    
    async def _notify_signal_callbacks(self, signal_dict: Dict):
        """Notificar señal a MCPs registrados"""
        if not self.external_callbacks:
            return
        
        try:
            # Enviar notificación broadcast a todos los callbacks registrados
            await self.server.broadcast("breakout_signal", {
                "signal": signal_dict,
                "timestamp": datetime.now().isoformat(),
                "source": "breakout_detector"
            })
            
        except Exception as e:
            self.logger.error(f"Error notificando callbacks: {e}")
    
    async def _handle_start_detection(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para iniciar detección"""
        try:
            params = message.params or {}
            if self.detection_active:
                return {
                    "success": False,
                    "message": "Detección ya está activa",
                    "status": "already_running"
                }
            
            # Iniciar detección
            self.detector.start_detection()
            self.detection_active = True
            
            self.logger.info("Detección de breakouts iniciada")
            
            return {
                "success": True,
                "message": "Detección de breakouts iniciada exitosamente",
                "status": "running",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error iniciando detección: {e}")
            return {
                "success": False,
                "message": f"Error iniciando detección: {str(e)}",
                "status": "error"
            }
    
    async def _handle_stop_detection(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para detener detección"""
        try:
            params = message.params or {}
            return await self._stop_detection_internal()
            
        except Exception as e:
            self.logger.error(f"Error deteniendo detección: {e}")
            return {
                "success": False,
                "message": f"Error deteniendo detección: {str(e)}",
                "status": "error"
            }
    
    async def _stop_detection_internal(self) -> Dict[str, Any]:
        """Detener detección internamente"""
        if not self.detection_active:
            return {
                "success": False,
                "message": "Detección no está activa",
                "status": "not_running"
            }
        
        # Detener detección
        self.detector.stop_detection()
        self.detection_active = False
        
        self.logger.info("Detección de breakouts detenida")
        
        return {
            "success": True,
            "message": "Detección de breakouts detenida exitosamente",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _handle_get_signals(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para obtener señales recientes"""
        try:
            params = message.params or {}
            symbol = params.get("symbol")
            limit = params.get("limit", 10)
            
            if symbol:
                # Señal específica de un símbolo
                signal = self.last_signals.get(symbol)
                return {
                    "success": True,
                    "signal": signal,
                    "symbol": symbol,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Últimas señales de todos los símbolos
                recent_signals = list(self.last_signals.values())[-limit:]
                return {
                    "success": True,
                    "signals": recent_signals,
                    "count": len(recent_signals),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error obteniendo señales: {e}")
            return {
                "success": False,
                "message": f"Error obteniendo señales: {str(e)}"
            }
    
    async def _handle_get_signal_history(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para obtener historial de señales"""
        try:
            params = message.params or {}
            limit = params.get("limit", 50)
            symbol = params.get("symbol")
            
            history = self.signal_history
            
            # Filtrar por símbolo si se especifica
            if symbol:
                history = [s for s in history if s.get("symbol") == symbol]
            
            # Limitar resultados
            history = history[-limit:]
            
            return {
                "success": True,
                "history": history,
                "count": len(history),
                "total_signals": len(self.signal_history),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo historial: {e}")
            return {
                "success": False,
                "message": f"Error obteniendo historial: {str(e)}"
            }
    
    async def _handle_update_price_data(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para actualizar datos de precio"""
        try:
            params = message.params or {}
            symbol = params.get("symbol")
            price_data = params.get("price_data")
            
            # Si no hay price_data, construir desde parámetros individuales
            if not price_data:
                price = params.get("price")
                volume = params.get("volume")
                timestamp = params.get("timestamp")
                
                if symbol and price is not None:
                    price_data = {
                        "price": price,
                        "volume": volume or 0,
                        "timestamp": timestamp or datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "message": "Parámetros 'symbol' y 'price' requeridos"
                    }
            
            if not symbol:
                return {
                    "success": False,
                    "message": "Parámetro 'symbol' requerido"
                }
            
            # Actualizar datos en el detector
            self.detector.update_price_data(symbol, price_data)
            
            return {
                "success": True,
                "message": f"Datos de precio actualizados para {symbol}",
                "symbol": symbol,
                "data_points": len(price_data) if isinstance(price_data, list) else 1,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error actualizando datos de precio: {e}")
            return {
                "success": False,
                "message": f"Error actualizando datos: {str(e)}"
            }
    
    async def _handle_get_detector_status(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para obtener estado del detector"""
        try:
            params = message.params or {}
            uptime = None
            if self.stats["uptime_start"]:
                uptime = (datetime.now() - self.stats["uptime_start"]).total_seconds()
            
            # Convertir stats a formato serializable
            serializable_stats = {}
            for key, value in self.stats.items():
                if isinstance(value, datetime):
                    serializable_stats[key] = value.isoformat()
                else:
                    serializable_stats[key] = value
            
            return {
                "success": True,
                "status": {
                    "detection_active": self.detection_active,
                    "detector_running": self.detector.running,
                    "sensitivity": self.detector.sensitivity,
                    "min_volume_ratio": self.detector.min_volume_ratio,
                    "min_price_change": self.detector.min_price_change,
                    "symbols_tracked": len(self.detector.price_history),
                    "callbacks_registered": len(self.external_callbacks),
                    "uptime_seconds": uptime
                },
                "statistics": serializable_stats,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado: {e}")
            return {
                "success": False,
                "message": f"Error obteniendo estado: {str(e)}"
            }
    
    async def _handle_update_sensitivity(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para actualizar sensibilidad"""
        try:
            params = message.params or {}
            sensitivity = params.get("sensitivity")
            
            if sensitivity is None:
                return {
                    "success": False,
                    "message": "Parámetro 'sensitivity' requerido"
                }
            
            # Actualizar sensibilidad
            self.detector.update_sensitivity(float(sensitivity))
            
            return {
                "success": True,
                "message": f"Sensibilidad actualizada a {sensitivity}",
                "new_sensitivity": self.detector.sensitivity,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error actualizando sensibilidad: {e}")
            return {
                "success": False,
                "message": f"Error actualizando sensibilidad: {str(e)}"
            }
    
    async def _handle_register_callback(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para registrar callback de señales"""
        try:
            params = message.params or {}
            mcp_name = params.get("mcp_name")
            
            if not mcp_name:
                return {
                    "success": False,
                    "message": "Parámetro 'mcp_name' requerido"
                }
            
            if mcp_name not in self.external_callbacks:
                self.external_callbacks.append(mcp_name)
            
            return {
                "success": True,
                "message": f"Callback registrado para {mcp_name}",
                "registered_callbacks": len(self.external_callbacks),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error registrando callback: {e}")
            return {
                "success": False,
                "message": f"Error registrando callback: {str(e)}"
            }
    
    async def _handle_unregister_callback(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para desregistrar callback"""
        try:
            params = message.params or {}
            mcp_name = params.get("mcp_name")
            
            if not mcp_name:
                return {
                    "success": False,
                    "message": "Parámetro 'mcp_name' requerido"
                }
            
            if mcp_name in self.external_callbacks:
                self.external_callbacks.remove(mcp_name)
            
            return {
                "success": True,
                "message": f"Callback desregistrado para {mcp_name}",
                "registered_callbacks": len(self.external_callbacks),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error desregistrando callback: {e}")
            return {
                "success": False,
                "message": f"Error desregistrando callback: {str(e)}"
            }
    
    async def _handle_force_detection(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para forzar detección en símbolos específicos"""
        try:
            params = message.params or {}
            symbols = params.get("symbols", [])
            
            if not symbols:
                return {
                    "success": False,
                    "message": "Parámetro 'symbols' requerido (lista de símbolos)"
                }
            
            results = {}
            
            for symbol in symbols:
                try:
                    # Forzar análisis del símbolo
                    signal = self.detector.analyze_symbol(symbol, force_detection=True)
                    
                    if signal:
                        results[symbol] = {
                            "success": True,
                            "signal_generated": True,
                            "signal": signal.to_dict()
                        }
                    else:
                        results[symbol] = {
                            "success": True,
                            "signal_generated": False,
                            "message": "No se generó señal"
                        }
                        
                except Exception as e:
                    results[symbol] = {
                        "success": False,
                        "error": str(e)
                    }
            
            return {
                "success": True,
                "message": f"Detección forzada completada para {len(symbols)} símbolos",
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error en detección forzada: {e}")
            return {
                "success": False,
                "message": f"Error en detección forzada: {str(e)}"
            }
    
    async def _handle_get_stats(self, message: MCPMessage) -> Dict[str, Any]:
        """Handler para obtener estadísticas detalladas"""
        try:
            params = message.params or {}
            # Calcular estadísticas adicionales
            uptime = None
            if self.stats["uptime_start"]:
                uptime = (datetime.now() - self.stats["uptime_start"]).total_seconds()
            
            # Estadísticas de señales por hora
            signals_per_hour = 0
            if uptime and uptime > 0:
                signals_per_hour = (self.stats["signals_generated"] / uptime) * 3600
            
            # Estadísticas de tipos de señales
            total_signals = self.stats["signals_generated"]
            bullish_pct = (self.stats["bullish_signals"] / total_signals * 100) if total_signals > 0 else 0
            bearish_pct = (self.stats["bearish_signals"] / total_signals * 100) if total_signals > 0 else 0
            strong_pct = (self.stats["strong_signals"] / total_signals * 100) if total_signals > 0 else 0
            
            # Convertir stats a formato serializable
            serializable_stats = {}
            for key, value in self.stats.items():
                if isinstance(value, datetime):
                    serializable_stats[key] = value.isoformat()
                else:
                    serializable_stats[key] = value
            
            return {
                "success": True,
                "statistics": {
                    **serializable_stats,
                    "uptime_seconds": uptime,
                    "signals_per_hour": round(signals_per_hour, 2),
                    "bullish_percentage": round(bullish_pct, 1),
                    "bearish_percentage": round(bearish_pct, 1),
                    "strong_signals_percentage": round(strong_pct, 1),
                    "active_symbols": len(self.detector.price_history),
                    "history_size": len(self.signal_history),
                    "registered_callbacks": len(self.external_callbacks)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                "success": False,
                "message": f"Error obteniendo estadísticas: {str(e)}"
            }
    
    def get_info(self) -> Dict[str, Any]:
        """Información del MCP"""
        return {
            "name": "breakout_detector",
            "version": "1.0.0",
            "description": "Detector de breakouts independiente",
            "capabilities": [
                "detect_breakouts",
                "get_recent_signals", 
                "process_market_data",
                "get_status",
                "get_stats",
                "force_detection"
            ],
            "status": "active" if self.detection_active else "inactive"
        }
    
    async def initialize(self) -> bool:
        """Inicializar el MCP"""
        try:
            self.stats["uptime_start"] = datetime.now()
            self.logger.info("BreakoutDetectorMCP inicializado correctamente")
            return True
        except Exception as e:
            self.logger.error(f"Error inicializando BreakoutDetectorMCP: {e}")
            return False
    
    async def process_message(self, message: MCPMessage) -> MCPResponse:
        """Procesar mensajes del MCP"""
        self.logger.debug(f"=== INICIANDO process_message para {message.method} ===")
        try:
            method = message.method
            params = message.params or {}
            self.logger.debug(f"Procesando método: {method}")
            
            # Mapear métodos a handlers
            handlers = {
                "get_detector_status": self._handle_get_detector_status,
                "get_signal_history": self._handle_get_signals,
                "update_price_data": self._handle_update_price_data,
                "start_detection": self._handle_start_detection,
                "stop_detection": self._handle_stop_detection,
                "force_detection": self._handle_force_detection,
                "get_stats": self._handle_get_stats
            }
            
            if method in handlers:
                self.logger.debug(f"Handler encontrado para {method}")
                result = await handlers[method](message)
                self.logger.debug(f"Resultado del handler: {type(result)} - {result}")
                
                # Verificar que result es un diccionario
                if not isinstance(result, dict):
                    self.logger.error(f"Handler devolvió tipo incorrecto: {type(result)}")
                    return MCPResponse(
                        request_id=message.id,
                        success=False,
                        data={"error": f"Handler devolvió tipo incorrecto: {type(result)}"}
                    )
                
                response = MCPResponse(
                    request_id=message.id,
                    success=result.get("success", True),
                    data=result
                )
                self.logger.debug(f"MCPResponse creado: {type(response)}")
                self.logger.debug(f"=== FINALIZANDO process_message exitosamente ===")
                return response
            else:
                self.logger.warning(f"Método no soportado: {method}")
                return MCPResponse(
                    request_id=message.id,
                    success=False,
                    data={"error": f"Método no soportado: {method}"}
                )
                
        except Exception as e:
            self.logger.error(f"Error procesando mensaje: {e}")
            return MCPResponse(
                request_id=message.id,
                success=False,
                data={"error": str(e)}
            )