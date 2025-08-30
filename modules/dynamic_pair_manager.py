"""
Dynamic Pair Manager - Gestión autónoma de selección de pares de trading

Este módulo integra la selección dinámica de pares directamente en el bot principal,
eliminando la dependencia de tareas cron externas y garantizando operación autónoma.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os
import sys

# Agregar el directorio padre al sys.path para importar dynamic_pair_selector
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dynamic_pair_selector import DynamicPairSelector
from utils.state_manager import StateManager
from utils.structured_logger import StructuredLogger

logger = StructuredLogger(__name__)

class DynamicPairManager:
    """
    Gestor autónomo de selección de pares de trading que se ejecuta
    internamente en el bot sin dependencias externas.
    """
    
    def __init__(self, 
                 max_pairs: int = 8,
                 reevaluation_interval_hours: int = 24,
                 data_dir: str = "data/dynamic_system"):
        """
        Inicializar el gestor de pares dinámico
        
        Args:
            max_pairs: Número máximo de pares a seleccionar
            reevaluation_interval_hours: Horas entre re-evaluaciones
            data_dir: Directorio para almacenar datos del sistema
        """
        self.max_pairs = max_pairs
        self.reevaluation_interval_hours = reevaluation_interval_hours
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.pair_selector = DynamicPairSelector()
        self.state_manager = StateManager()
        
        # Archivos de estado
        self.selected_pairs_file = self.data_dir / "selected_pairs.json"
        self.last_evaluation_file = self.data_dir / "last_evaluation.json"
        self.evaluation_history_file = self.data_dir / "evaluation_history.json"
        
        # Estado interno
        self.current_pairs: List[str] = []
        self.last_evaluation_time: Optional[datetime] = None
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """
        Inicializar el sistema dinámico
        
        Returns:
            bool: True si la inicialización fue exitosa
        """
        try:
            logger.info("DYNAMIC_INIT_START", "Inicializando Dynamic Pair Manager")
            
            # Cargar estado previo si existe
            await self._load_previous_state()
            
            # Verificar si necesitamos evaluación inicial
            if not self.current_pairs or await self._needs_reevaluation():
                logger.info("DYNAMIC_INIT_EVAL", "Realizando evaluación inicial de pares")
                await self._perform_evaluation(is_initial=True)
            
            self.is_initialized = True
            logger.info("DYNAMIC_INIT_SUCCESS", 
                       f"Dynamic Pair Manager inicializado con {len(self.current_pairs)} pares",
                       details={"current_pairs": self.current_pairs})
            
            return True
            
        except Exception as e:
            logger.error("DYNAMIC_INIT_ERROR", f"Error inicializando Dynamic Pair Manager: {e}", 
                        exc_info=True)
            return False
    
    async def get_current_pairs(self) -> List[str]:
        """
        Obtener los pares actualmente seleccionados
        
        Returns:
            List[str]: Lista de pares de trading activos
        """
        if not self.is_initialized:
            await self.initialize()
        
        return self.current_pairs.copy()
    
    async def check_and_update_pairs(self) -> Tuple[bool, Optional[Dict]]:
        """
        Verificar si es necesaria una re-evaluación y realizarla si es necesario
        
        Returns:
            Tuple[bool, Optional[Dict]]: (cambios_realizados, detalles_cambios)
        """
        if not self.is_initialized:
            await self.initialize()
        
        try:
            if await self._needs_reevaluation():
                logger.info("DYNAMIC_REEVALUATION", "Iniciando re-evaluación de pares")
                return await self._perform_evaluation(is_initial=False)
            
            return False, None
            
        except Exception as e:
            logger.error("DYNAMIC_UPDATE_ERROR", f"Error en check_and_update_pairs: {e}", 
                        exc_info=True)
            return False, None
    
    async def force_reevaluation(self) -> Tuple[bool, Optional[Dict]]:
        """
        Forzar una re-evaluación inmediata de pares
        
        Returns:
            Tuple[bool, Optional[Dict]]: (cambios_realizados, detalles_cambios)
        """
        logger.info("DYNAMIC_FORCE_EVAL", "Iniciando re-evaluación forzada")
        return await self._perform_evaluation(is_initial=False)
    
    async def _load_previous_state(self):
        """Cargar estado previo del sistema"""
        try:
            # Cargar pares seleccionados
            if self.selected_pairs_file.exists():
                with open(self.selected_pairs_file, 'r') as f:
                    data = json.load(f)
                    self.current_pairs = data.get('pairs', [])
                    logger.info("DYNAMIC_LOAD_STATE", 
                               f"Cargados {len(self.current_pairs)} pares del estado previo",
                               details={"pairs": self.current_pairs})
            
            # Cargar timestamp de última evaluación
            if self.last_evaluation_file.exists():
                with open(self.last_evaluation_file, 'r') as f:
                    data = json.load(f)
                    timestamp_str = data.get('last_evaluation')
                    if timestamp_str:
                        self.last_evaluation_time = datetime.fromisoformat(timestamp_str)
                        logger.info("DYNAMIC_LOAD_TIMESTAMP", 
                                   f"Última evaluación: {self.last_evaluation_time}")
                        
        except Exception as e:
            logger.warning("DYNAMIC_LOAD_STATE_ERROR", 
                          f"Error cargando estado previo: {e}")
    
    async def _needs_reevaluation(self) -> bool:
        """
        Determinar si es necesaria una re-evaluación
        
        Returns:
            bool: True si es necesaria re-evaluación
        """
        if not self.last_evaluation_time:
            return True
        
        time_since_last = datetime.now() - self.last_evaluation_time
        hours_since_last = time_since_last.total_seconds() / 3600
        
        needs_eval = hours_since_last >= self.reevaluation_interval_hours
        
        if needs_eval:
            logger.info("DYNAMIC_NEEDS_EVAL", 
                       f"Re-evaluación necesaria. Último análisis hace {hours_since_last:.1f} horas")
        
        return needs_eval
    
    async def _perform_evaluation(self, is_initial: bool = False) -> Tuple[bool, Optional[Dict]]:
        """
        Realizar evaluación de pares y actualizar selección
        
        Args:
            is_initial: Si es la evaluación inicial del sistema
            
        Returns:
            Tuple[bool, Optional[Dict]]: (cambios_realizados, detalles_cambios)
        """
        try:
            evaluation_start = datetime.now()
            
            # Realizar selección dinámica
            logger.info("DYNAMIC_EVALUATION_START", "Iniciando análisis de pares disponibles")
            
            # Primero evaluamos todos los pares
            pair_metrics = await self.pair_selector.evaluate_all_pairs()
            
            if not pair_metrics:
                logger.error("DYNAMIC_EVALUATION_FAILED", "No se pudieron obtener métricas de pares")
                return False, None
            
            # Luego seleccionamos los mejores
            selected_pair_symbols = self.pair_selector.select_best_pairs(
                target_count=self.max_pairs, 
                diversification=True
            )
            
            if not selected_pair_symbols:
                logger.error("DYNAMIC_SELECTION_FAILED", "No se pudieron seleccionar pares")
                return False, None
            
            # Obtener métricas de los pares seleccionados
            selected_pairs_with_metrics = [
                {
                    'symbol': symbol,
                    'score': pair_metrics[symbol]['composite_score'],
                    'volume': pair_metrics[symbol]['volume_24h_usdt']
                }
                for symbol in selected_pair_symbols if symbol in pair_metrics
            ]
            
            # Extraer solo los símbolos para comparación
            new_pairs = selected_pair_symbols
            
            # Comparar con pares actuales
            previous_pairs = self.current_pairs.copy()
            changes_made = set(new_pairs) != set(previous_pairs)
            
            evaluation_details = {
                "timestamp": evaluation_start.isoformat(),
                "is_initial": is_initial,
                "previous_pairs": previous_pairs,
                "new_pairs": new_pairs,
                "changes_made": changes_made,
                "pairs_added": list(set(new_pairs) - set(previous_pairs)),
                "pairs_removed": list(set(previous_pairs) - set(new_pairs)),
                "pairs_maintained": list(set(new_pairs) & set(previous_pairs)),
                "total_pairs_analyzed": len(pair_metrics),
                "selected_pairs_details": selected_pairs_with_metrics,
                "evaluation_duration_seconds": (datetime.now() - evaluation_start).total_seconds()
            }
            
            if changes_made or is_initial:
                # Actualizar pares actuales
                self.current_pairs = new_pairs
                self.last_evaluation_time = evaluation_start
                
                # Guardar nuevo estado
                await self._save_state(evaluation_details)
                
                # Logging detallado
                if is_initial:
                    logger.info("DYNAMIC_INITIAL_SELECTION", 
                               f"Selección inicial: {len(new_pairs)} pares",
                               details=evaluation_details)
                else:
                    logger.info("DYNAMIC_PAIRS_UPDATED", 
                               f"Pares actualizados. Agregados: {len(evaluation_details['pairs_added'])}, "
                               f"Removidos: {len(evaluation_details['pairs_removed'])}",
                               details=evaluation_details)
                
                return True, evaluation_details
            
            else:
                # Sin cambios, solo actualizar timestamp
                self.last_evaluation_time = evaluation_start
                await self._save_timestamp()
                
                logger.info("DYNAMIC_NO_CHANGES", 
                           "Re-evaluación completada sin cambios en la selección",
                           details={"current_pairs": self.current_pairs})
                
                return False, evaluation_details
                
        except Exception as e:
            logger.error("DYNAMIC_EVALUATION_ERROR", 
                        f"Error durante evaluación de pares: {e}", 
                        exc_info=True)
            return False, None
    
    async def _save_state(self, evaluation_details: Dict):
        """Guardar estado completo del sistema"""
        try:
            # Guardar pares seleccionados
            pairs_data = {
                "pairs": self.current_pairs,
                "last_updated": evaluation_details["timestamp"],
                "total_pairs": len(self.current_pairs)
            }
            
            with open(self.selected_pairs_file, 'w') as f:
                json.dump(pairs_data, f, indent=2)
            
            # Guardar timestamp de evaluación
            await self._save_timestamp()
            
            # Guardar en historial
            await self._save_to_history(evaluation_details)
            
            logger.info("DYNAMIC_STATE_SAVED", "Estado del sistema guardado exitosamente")
            
        except Exception as e:
            logger.error("DYNAMIC_SAVE_ERROR", f"Error guardando estado: {e}")
    
    async def _save_timestamp(self):
        """Guardar solo el timestamp de última evaluación"""
        timestamp_data = {
            "last_evaluation": self.last_evaluation_time.isoformat() if self.last_evaluation_time else None
        }
        
        with open(self.last_evaluation_file, 'w') as f:
            json.dump(timestamp_data, f, indent=2)
    
    async def _save_to_history(self, evaluation_details: Dict):
        """Agregar evaluación al historial"""
        try:
            history = []
            
            # Cargar historial existente
            if self.evaluation_history_file.exists():
                with open(self.evaluation_history_file, 'r') as f:
                    history = json.load(f)
            
            # Agregar nueva evaluación
            history.append(evaluation_details)
            
            # Mantener solo las últimas 30 evaluaciones
            history = history[-30:]
            
            # Guardar historial actualizado
            with open(self.evaluation_history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error("DYNAMIC_HISTORY_ERROR", f"Error guardando historial: {e}")
    
    async def get_evaluation_history(self) -> List[Dict]:
        """
        Obtener historial de evaluaciones
        
        Returns:
            List[Dict]: Lista de evaluaciones históricas
        """
        try:
            if self.evaluation_history_file.exists():
                with open(self.evaluation_history_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error("DYNAMIC_GET_HISTORY_ERROR", f"Error obteniendo historial: {e}")
            return []
    
    async def get_status_report(self) -> Dict:
        """
        Generar reporte de estado del sistema dinámico
        
        Returns:
            Dict: Reporte completo del estado
        """
        try:
            # Si este proceso (por ejemplo, el panel web) no ha inicializado
            # el gestor pero existen archivos de estado persistidos por el bot,
            # cargarlos para reflejar correctamente el estado actual.
            if (not self.is_initialized) and (not self.current_pairs):
                try:
                    await self._load_previous_state()
                    # Considerar "inicializado" si ya hay pares cargados del estado previo
                    if self.current_pairs:
                        self.is_initialized = True
                except Exception:
                    # No bloquear el reporte por un fallo al cargar
                    pass
            history = await self.get_evaluation_history()
            
            status_report = {
                "system_status": {
                    "is_initialized": self.is_initialized,
                    "current_pairs_count": len(self.current_pairs),
                    "current_pairs": self.current_pairs,
                    "last_evaluation": self.last_evaluation_time.isoformat() if self.last_evaluation_time else None,
                    "hours_since_last_evaluation": None,
                    "needs_reevaluation": await self._needs_reevaluation()
                },
                "configuration": {
                    "max_pairs": self.max_pairs,
                    "reevaluation_interval_hours": self.reevaluation_interval_hours,
                    "data_directory": str(self.data_dir)
                },
                "history": {
                    "total_evaluations": len(history),
                    "recent_evaluations": history[-5:] if history else []
                }
            }
            
            # Calcular horas desde última evaluación
            if self.last_evaluation_time:
                time_since = datetime.now() - self.last_evaluation_time
                status_report["system_status"]["hours_since_last_evaluation"] = time_since.total_seconds() / 3600
            
            return status_report
            
        except Exception as e:
            logger.error("DYNAMIC_STATUS_ERROR", f"Error generando reporte de estado: {e}")
            return {"error": str(e)}

# Instancia global para uso en el bot
dynamic_pair_manager = DynamicPairManager()
