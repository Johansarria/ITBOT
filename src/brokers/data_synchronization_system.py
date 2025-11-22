"""
SICAR - Sistema de Sincronización de Datos Multi-Fuente
=======================================================

Este módulo proporciona sincronización en tiempo real de datos entre múltiples
fuentes: brokers tradicionales, APIs de mercado, bases de datos y servicios externos.

Características:
- Sincronización en tiempo real multi-fuente
- Resolución de conflictos de datos
- Cache inteligente con TTL
- Validación y limpieza de datos
- Métricas de calidad de datos
- Recuperación automática ante fallos
- Priorización de fuentes

Autor: SICAR Team
Fecha: Enero 2025
"""

import asyncio
import logging
import time
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Set
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
import hashlib
import statistics

class DataSourceType(Enum):
    """Tipos de fuentes de datos"""
    BROKER = "BROKER"
    MARKET_DATA = "MARKET_DATA"
    NEWS = "NEWS"
    ECONOMIC = "ECONOMIC"
    SOCIAL = "SOCIAL"
    INTERNAL = "INTERNAL"

class DataType(Enum):
    """Tipos de datos"""
    PRICE = "PRICE"
    VOLUME = "VOLUME"
    ORDER_BOOK = "ORDER_BOOK"
    TRADE = "TRADE"
    POSITION = "POSITION"
    ACCOUNT = "ACCOUNT"
    NEWS = "NEWS"
    SENTIMENT = "SENTIMENT"
    ECONOMIC_INDICATOR = "ECONOMIC_INDICATOR"

class DataQuality(Enum):
    """Calidad de datos"""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    INVALID = "INVALID"

class SyncStatus(Enum):
    """Estado de sincronización"""
    SYNCED = "SYNCED"
    SYNCING = "SYNCING"
    OUT_OF_SYNC = "OUT_OF_SYNC"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"

@dataclass
class DataPoint:
    """Punto de datos individual"""
    source_id: str
    data_type: DataType
    symbol: str
    value: Any
    timestamp: datetime
    quality: DataQuality = DataQuality.GOOD
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-inicialización"""
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return {
            'source_id': self.source_id,
            'data_type': self.data_type.value,
            'symbol': self.symbol,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'quality': self.quality.value,
            'metadata': self.metadata
        }
    
    def get_hash(self) -> str:
        """Obtener hash del punto de datos"""
        content = f"{self.source_id}_{self.data_type.value}_{self.symbol}_{self.value}_{self.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()

@dataclass
class DataSource:
    """Configuración de fuente de datos"""
    source_id: str
    source_type: DataSourceType
    name: str
    priority: int = 1  # 1 = más alta, 10 = más baja
    enabled: bool = True
    update_frequency: int = 1000  # ms
    timeout: int = 5000  # ms
    max_retries: int = 3
    data_types: Set[DataType] = field(default_factory=set)
    symbols: Set[str] = field(default_factory=set)
    
    # Configuración de calidad
    quality_threshold: float = 0.8
    staleness_threshold: int = 30000  # ms
    
    # Estadísticas
    last_update: Optional[datetime] = None
    total_updates: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    avg_latency: float = 0.0
    
    def get_success_rate(self) -> float:
        """Obtener tasa de éxito"""
        if self.total_updates == 0:
            return 0.0
        return (self.successful_updates / self.total_updates) * 100

@dataclass
class ConflictResolution:
    """Resolución de conflictos entre fuentes"""
    data_type: DataType
    symbol: str
    conflicting_values: List[DataPoint]
    resolved_value: DataPoint
    resolution_method: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)

class DataSourceInterface(ABC):
    """Interfaz para fuentes de datos"""
    
    @abstractmethod
    async def fetch_data(self, symbols: List[str], data_types: List[DataType]) -> List[DataPoint]:
        """Obtener datos de la fuente"""
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Verificar si la fuente está disponible"""
        pass
    
    @abstractmethod
    def get_supported_symbols(self) -> Set[str]:
        """Obtener símbolos soportados"""
        pass
    
    @abstractmethod
    def get_supported_data_types(self) -> Set[DataType]:
        """Obtener tipos de datos soportados"""
        pass

class DataSynchronizationSystem:
    """
    Sistema principal de sincronización de datos
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Fuentes de datos
        self.sources: Dict[str, DataSource] = {}
        self.source_interfaces: Dict[str, DataSourceInterface] = {}
        
        # Cache de datos
        self.data_cache: Dict[str, Dict[str, DataPoint]] = {}  # {symbol: {data_type: DataPoint}}
        self.cache_ttl: Dict[str, Dict[str, datetime]] = {}  # TTL para cada entrada
        
        # Configuración
        self.default_cache_ttl = 5000  # ms
        self.conflict_resolution_enabled = True
        self.quality_filtering_enabled = True
        self.min_quality_threshold = DataQuality.FAIR
        
        # Estado del sistema
        self.is_running = False
        self.sync_tasks: Dict[str, asyncio.Task] = {}
        
        # Métricas
        self.total_data_points = 0
        self.conflicts_resolved = 0
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Callbacks
        self.data_callbacks: List[Callable] = []
        self.conflict_callbacks: List[Callable] = []
        self.quality_callbacks: List[Callable] = []
        
        # Historial de conflictos
        self.conflict_history: List[ConflictResolution] = []
        
    def register_source(self, source: DataSource, interface: DataSourceInterface):
        """
        Registrar fuente de datos
        
        Args:
            source: Configuración de la fuente
            interface: Interfaz de la fuente
        """
        self.sources[source.source_id] = source
        self.source_interfaces[source.source_id] = interface
        
        # Inicializar cache para esta fuente
        if source.source_id not in self.data_cache:
            self.data_cache[source.source_id] = {}
            self.cache_ttl[source.source_id] = {}
        
        self.logger.info(f"Fuente {source.source_id} registrada")
    
    def unregister_source(self, source_id: str):
        """Desregistrar fuente de datos"""
        if source_id in self.sources:
            del self.sources[source_id]
        if source_id in self.source_interfaces:
            del self.source_interfaces[source_id]
        if source_id in self.data_cache:
            del self.data_cache[source_id]
        if source_id in self.cache_ttl:
            del self.cache_ttl[source_id]
        
        self.logger.info(f"Fuente {source_id} desregistrada")
    
    def add_data_callback(self, callback: Callable):
        """Agregar callback para nuevos datos"""
        self.data_callbacks.append(callback)
    
    def add_conflict_callback(self, callback: Callable):
        """Agregar callback para conflictos"""
        self.conflict_callbacks.append(callback)
    
    def add_quality_callback(self, callback: Callable):
        """Agregar callback para problemas de calidad"""
        self.quality_callbacks.append(callback)
    
    async def start_synchronization(self):
        """Iniciar sincronización de todas las fuentes"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Iniciar tareas de sincronización para cada fuente
        for source_id, source in self.sources.items():
            if source.enabled:
                task = asyncio.create_task(self._sync_source_loop(source_id))
                self.sync_tasks[source_id] = task
        
        self.logger.info(f"Sincronización iniciada para {len(self.sync_tasks)} fuentes")
    
    async def stop_synchronization(self):
        """Detener sincronización"""
        self.is_running = False
        
        # Cancelar todas las tareas
        for task in self.sync_tasks.values():
            task.cancel()
        
        # Esperar a que terminen
        if self.sync_tasks:
            await asyncio.gather(*self.sync_tasks.values(), return_exceptions=True)
        
        self.sync_tasks.clear()
        self.logger.info("Sincronización detenida")
    
    async def _sync_source_loop(self, source_id: str):
        """Loop de sincronización para una fuente específica"""
        source = self.sources[source_id]
        interface = self.source_interfaces[source_id]
        
        while self.is_running and source.enabled:
            try:
                start_time = time.time()
                
                # Verificar disponibilidad
                if not await interface.is_available():
                    self.logger.warning(f"Fuente {source_id} no disponible")
                    await asyncio.sleep(source.update_frequency / 1000)
                    continue
                
                # Obtener símbolos y tipos de datos a sincronizar
                symbols = list(source.symbols) if source.symbols else list(interface.get_supported_symbols())
                data_types = list(source.data_types) if source.data_types else list(interface.get_supported_data_types())
                
                if not symbols or not data_types:
                    await asyncio.sleep(source.update_frequency / 1000)
                    continue
                
                # Obtener datos
                data_points = await interface.fetch_data(symbols, data_types)
                
                # Procesar datos
                if data_points:
                    await self._process_data_points(source_id, data_points)
                    
                    # Actualizar estadísticas
                    source.successful_updates += 1
                    source.last_update = datetime.now()
                    
                    # Calcular latencia
                    latency = (time.time() - start_time) * 1000
                    source.avg_latency = (source.avg_latency * (source.successful_updates - 1) + latency) / source.successful_updates
                
                source.total_updates += 1
                
                # Esperar antes del siguiente ciclo
                await asyncio.sleep(source.update_frequency / 1000)
                
            except Exception as e:
                source.failed_updates += 1
                source.total_updates += 1
                self.logger.error(f"Error sincronizando fuente {source_id}: {e}")
                await asyncio.sleep(source.update_frequency / 1000)
    
    async def _process_data_points(self, source_id: str, data_points: List[DataPoint]):
        """Procesar puntos de datos de una fuente"""
        for data_point in data_points:
            # Validar calidad
            if self.quality_filtering_enabled and not self._is_quality_acceptable(data_point):
                await self._notify_quality_callbacks(data_point)
                continue
            
            # Actualizar cache
            cache_key = f"{data_point.symbol}_{data_point.data_type.value}"
            
            # Verificar si hay conflictos
            existing_data = self._get_cached_data(data_point.symbol, data_point.data_type)
            
            if existing_data and self.conflict_resolution_enabled:
                # Verificar si hay conflicto
                if self._has_conflict(existing_data, data_point):
                    resolved_data = await self._resolve_conflict(existing_data, data_point)
                    if resolved_data:
                        await self._update_cache(resolved_data)
                        await self._notify_data_callbacks(resolved_data)
                else:
                    # No hay conflicto, actualizar normalmente
                    await self._update_cache(data_point)
                    await self._notify_data_callbacks(data_point)
            else:
                # Primera vez o sin conflictos
                await self._update_cache(data_point)
                await self._notify_data_callbacks(data_point)
            
            self.total_data_points += 1
    
    def _is_quality_acceptable(self, data_point: DataPoint) -> bool:
        """Verificar si la calidad del dato es aceptable"""
        quality_levels = {
            DataQuality.EXCELLENT: 5,
            DataQuality.GOOD: 4,
            DataQuality.FAIR: 3,
            DataQuality.POOR: 2,
            DataQuality.INVALID: 1
        }
        
        min_level = quality_levels.get(self.min_quality_threshold, 3)
        current_level = quality_levels.get(data_point.quality, 1)
        
        return current_level >= min_level
    
    def _get_cached_data(self, symbol: str, data_type: DataType) -> Optional[DataPoint]:
        """Obtener datos del cache"""
        cache_key = f"{symbol}_{data_type.value}"
        
        # Buscar en todas las fuentes
        for source_id, cache in self.data_cache.items():
            if cache_key in cache:
                # Verificar TTL
                if cache_key in self.cache_ttl[source_id]:
                    ttl = self.cache_ttl[source_id][cache_key]
                    if datetime.now() > ttl:
                        # Expirado
                        del cache[cache_key]
                        del self.cache_ttl[source_id][cache_key]
                        self.cache_misses += 1
                        continue
                
                self.cache_hits += 1
                return cache[cache_key]
        
        self.cache_misses += 1
        return None
    
    async def _update_cache(self, data_point: DataPoint):
        """Actualizar cache con nuevo dato"""
        source_id = data_point.source_id
        cache_key = f"{data_point.symbol}_{data_point.data_type.value}"
        
        # Actualizar cache
        if source_id not in self.data_cache:
            self.data_cache[source_id] = {}
            self.cache_ttl[source_id] = {}
        
        self.data_cache[source_id][cache_key] = data_point
        
        # Establecer TTL
        ttl = datetime.now() + timedelta(milliseconds=self.default_cache_ttl)
        self.cache_ttl[source_id][cache_key] = ttl
    
    def _has_conflict(self, existing_data: DataPoint, new_data: DataPoint) -> bool:
        """Verificar si hay conflicto entre datos"""
        # Mismo símbolo y tipo de datos
        if existing_data.symbol != new_data.symbol or existing_data.data_type != new_data.data_type:
            return False
        
        # Diferentes fuentes
        if existing_data.source_id == new_data.source_id:
            return False
        
        # Timestamps muy cercanos (dentro de 1 segundo)
        time_diff = abs((existing_data.timestamp - new_data.timestamp).total_seconds())
        if time_diff > 1:
            return False
        
        # Valores diferentes (para datos numéricos)
        if isinstance(existing_data.value, (int, float)) and isinstance(new_data.value, (int, float)):
            # Considerar conflicto si la diferencia es mayor al 0.1%
            diff_pct = abs(existing_data.value - new_data.value) / max(abs(existing_data.value), 0.01)
            return diff_pct > 0.001
        
        # Para otros tipos, comparar directamente
        return existing_data.value != new_data.value
    
    async def _resolve_conflict(self, existing_data: DataPoint, new_data: DataPoint) -> Optional[DataPoint]:
        """Resolver conflicto entre datos"""
        # Obtener prioridades de las fuentes
        existing_priority = self.sources.get(existing_data.source_id, DataSource("", DataSourceType.INTERNAL, "")).priority
        new_priority = self.sources.get(new_data.source_id, DataSource("", DataSourceType.INTERNAL, "")).priority
        
        # Método 1: Por prioridad de fuente
        if existing_priority != new_priority:
            resolved = existing_data if existing_priority < new_priority else new_data
            method = "source_priority"
            confidence = 0.8
        
        # Método 2: Por calidad de datos
        elif existing_data.quality != new_data.quality:
            quality_order = [DataQuality.EXCELLENT, DataQuality.GOOD, DataQuality.FAIR, DataQuality.POOR, DataQuality.INVALID]
            existing_quality_idx = quality_order.index(existing_data.quality)
            new_quality_idx = quality_order.index(new_data.quality)
            
            resolved = existing_data if existing_quality_idx < new_quality_idx else new_data
            method = "data_quality"
            confidence = 0.7
        
        # Método 3: Por timestamp (más reciente)
        elif existing_data.timestamp != new_data.timestamp:
            resolved = existing_data if existing_data.timestamp > new_data.timestamp else new_data
            method = "timestamp"
            confidence = 0.6
        
        # Método 4: Promedio (para datos numéricos)
        elif isinstance(existing_data.value, (int, float)) and isinstance(new_data.value, (int, float)):
            avg_value = (existing_data.value + new_data.value) / 2
            resolved = DataPoint(
                source_id="SYSTEM_AVERAGE",
                data_type=existing_data.data_type,
                symbol=existing_data.symbol,
                value=avg_value,
                timestamp=max(existing_data.timestamp, new_data.timestamp),
                quality=min(existing_data.quality, new_data.quality, key=lambda x: [DataQuality.EXCELLENT, DataQuality.GOOD, DataQuality.FAIR, DataQuality.POOR, DataQuality.INVALID].index(x))
            )
            method = "average"
            confidence = 0.5
        
        else:
            # No se puede resolver, usar el existente
            resolved = existing_data
            method = "keep_existing"
            confidence = 0.3
        
        # Registrar resolución de conflicto
        conflict_resolution = ConflictResolution(
            data_type=existing_data.data_type,
            symbol=existing_data.symbol,
            conflicting_values=[existing_data, new_data],
            resolved_value=resolved,
            resolution_method=method,
            confidence=confidence
        )
        
        self.conflict_history.append(conflict_resolution)
        self.conflicts_resolved += 1
        
        # Notificar callbacks
        await self._notify_conflict_callbacks(conflict_resolution)
        
        self.logger.debug(f"Conflicto resuelto para {existing_data.symbol} {existing_data.data_type.value} usando {method}")
        
        return resolved
    
    async def _notify_data_callbacks(self, data_point: DataPoint):
        """Notificar callbacks de datos"""
        for callback in self.data_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_point)
                else:
                    callback(data_point)
            except Exception as e:
                self.logger.error(f"Error en callback de datos: {e}")
    
    async def _notify_conflict_callbacks(self, conflict_resolution: ConflictResolution):
        """Notificar callbacks de conflictos"""
        for callback in self.conflict_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(conflict_resolution)
                else:
                    callback(conflict_resolution)
            except Exception as e:
                self.logger.error(f"Error en callback de conflicto: {e}")
    
    async def _notify_quality_callbacks(self, data_point: DataPoint):
        """Notificar callbacks de calidad"""
        for callback in self.quality_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data_point)
                else:
                    callback(data_point)
            except Exception as e:
                self.logger.error(f"Error en callback de calidad: {e}")
    
    def get_latest_data(self, symbol: str, data_type: DataType) -> Optional[DataPoint]:
        """Obtener el dato más reciente para un símbolo y tipo"""
        return self._get_cached_data(symbol, data_type)
    
    def get_all_data(self, symbol: Optional[str] = None, 
                    data_type: Optional[DataType] = None) -> List[DataPoint]:
        """Obtener todos los datos con filtros opcionales"""
        all_data = []
        
        for source_cache in self.data_cache.values():
            for data_point in source_cache.values():
                if symbol and data_point.symbol != symbol:
                    continue
                if data_type and data_point.data_type != data_type:
                    continue
                
                all_data.append(data_point)
        
        return all_data
    
    def get_source_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Obtener estadísticas de todas las fuentes"""
        stats = {}
        
        for source_id, source in self.sources.items():
            stats[source_id] = {
                'name': source.name,
                'type': source.source_type.value,
                'enabled': source.enabled,
                'priority': source.priority,
                'total_updates': source.total_updates,
                'successful_updates': source.successful_updates,
                'failed_updates': source.failed_updates,
                'success_rate': source.get_success_rate(),
                'avg_latency': source.avg_latency,
                'last_update': source.last_update.isoformat() if source.last_update else None,
                'cached_items': len(self.data_cache.get(source_id, {}))
            }
        
        return stats
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas del sistema"""
        cache_hit_rate = (self.cache_hits / max(self.cache_hits + self.cache_misses, 1)) * 100
        
        return {
            'is_running': self.is_running,
            'active_sources': len([s for s in self.sources.values() if s.enabled]),
            'total_sources': len(self.sources),
            'total_data_points': self.total_data_points,
            'conflicts_resolved': self.conflicts_resolved,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': cache_hit_rate,
            'cached_symbols': len(set(dp.symbol for cache in self.data_cache.values() for dp in cache.values())),
            'recent_conflicts': len([c for c in self.conflict_history if (datetime.now() - c.timestamp).total_seconds() < 3600])
        }
    
    def export_data_to_dataframe(self) -> pd.DataFrame:
        """Exportar datos a DataFrame"""
        all_data = self.get_all_data()
        
        if not all_data:
            return pd.DataFrame()
        
        data = []
        for dp in all_data:
            data.append({
                'source_id': dp.source_id,
                'data_type': dp.data_type.value,
                'symbol': dp.symbol,
                'value': dp.value,
                'timestamp': dp.timestamp,
                'quality': dp.quality.value,
                'metadata': json.dumps(dp.metadata)
            })
        
        return pd.DataFrame(data)
    
    def export_conflicts_to_dataframe(self) -> pd.DataFrame:
        """Exportar conflictos a DataFrame"""
        if not self.conflict_history:
            return pd.DataFrame()
        
        data = []
        for conflict in self.conflict_history:
            data.append({
                'data_type': conflict.data_type.value,
                'symbol': conflict.symbol,
                'num_conflicting_values': len(conflict.conflicting_values),
                'resolution_method': conflict.resolution_method,
                'confidence': conflict.confidence,
                'timestamp': conflict.timestamp,
                'resolved_value': conflict.resolved_value.value,
                'resolved_source': conflict.resolved_value.source_id
            })
        
        return pd.DataFrame(data)

# Implementación de ejemplo para fuente de datos simulada
class MockDataSource(DataSourceInterface):
    """Fuente de datos simulada para testing"""
    
    def __init__(self, source_id: str, symbols: List[str]):
        self.source_id = source_id
        self.symbols = set(symbols)
        self.data_types = {DataType.PRICE, DataType.VOLUME}
        self.is_online = True
    
    async def fetch_data(self, symbols: List[str], data_types: List[DataType]) -> List[DataPoint]:
        """Generar datos simulados"""
        if not self.is_online:
            return []
        
        data_points = []
        
        for symbol in symbols:
            if symbol not in self.symbols:
                continue
            
            for data_type in data_types:
                if data_type not in self.data_types:
                    continue
                
                # Generar valor simulado
                if data_type == DataType.PRICE:
                    base_price = {'SPY': 450, 'QQQ': 380, 'IWM': 200}.get(symbol, 100)
                    value = base_price + np.random.normal(0, base_price * 0.001)
                elif data_type == DataType.VOLUME:
                    value = np.random.randint(100000, 1000000)
                else:
                    value = np.random.random()
                
                # Simular calidad variable
                quality = np.random.choice([
                    DataQuality.EXCELLENT,
                    DataQuality.GOOD,
                    DataQuality.FAIR
                ], p=[0.7, 0.25, 0.05])
                
                data_point = DataPoint(
                    source_id=self.source_id,
                    data_type=data_type,
                    symbol=symbol,
                    value=value,
                    timestamp=datetime.now(),
                    quality=quality,
                    metadata={'simulated': True}
                )
                
                data_points.append(data_point)
        
        return data_points
    
    async def is_available(self) -> bool:
        """Verificar disponibilidad"""
        return self.is_online
    
    def get_supported_symbols(self) -> Set[str]:
        """Obtener símbolos soportados"""
        return self.symbols
    
    def get_supported_data_types(self) -> Set[DataType]:
        """Obtener tipos de datos soportados"""
        return self.data_types

# Demo y testing
if __name__ == "__main__":
    async def demo():
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        
        print("=== SICAR - Sistema de Sincronización de Datos Demo ===\n")
        
        # Crear sistema
        sync_system = DataSynchronizationSystem()
        
        # Configurar callbacks
        print("1. Configurando callbacks...")
        
        async def data_callback(data_point: DataPoint):
            print(f"   📊 Nuevo dato: {data_point.symbol} {data_point.data_type.value} = {data_point.value:.4f} ({data_point.source_id})")
        
        async def conflict_callback(conflict: ConflictResolution):
            print(f"   ⚠️  Conflicto resuelto: {conflict.symbol} {conflict.data_type.value} usando {conflict.resolution_method} (confianza: {conflict.confidence:.2f})")
        
        async def quality_callback(data_point: DataPoint):
            print(f"   ❌ Calidad baja: {data_point.symbol} {data_point.data_type.value} - {data_point.quality.value}")
        
        sync_system.add_data_callback(data_callback)
        sync_system.add_conflict_callback(conflict_callback)
        sync_system.add_quality_callback(quality_callback)
        print("   ✓ Callbacks configurados")
        
        # Registrar fuentes de datos simuladas
        print("\n2. Registrando fuentes de datos...")
        
        symbols = ['SPY', 'QQQ', 'IWM']
        
        # Fuente 1: Broker principal (alta prioridad)
        source1 = DataSource(
            source_id="BROKER_PRIMARY",
            source_type=DataSourceType.BROKER,
            name="Broker Principal",
            priority=1,
            update_frequency=1000,
            symbols=set(symbols),
            data_types={DataType.PRICE, DataType.VOLUME}
        )
        interface1 = MockDataSource("BROKER_PRIMARY", symbols)
        sync_system.register_source(source1, interface1)
        
        # Fuente 2: Broker secundario (prioridad media)
        source2 = DataSource(
            source_id="BROKER_SECONDARY",
            source_type=DataSourceType.BROKER,
            name="Broker Secundario",
            priority=2,
            update_frequency=1500,
            symbols=set(symbols),
            data_types={DataType.PRICE, DataType.VOLUME}
        )
        interface2 = MockDataSource("BROKER_SECONDARY", symbols)
        sync_system.register_source(source2, interface2)
        
        # Fuente 3: Datos de mercado (prioridad baja)
        source3 = DataSource(
            source_id="MARKET_DATA",
            source_type=DataSourceType.MARKET_DATA,
            name="Datos de Mercado",
            priority=3,
            update_frequency=2000,
            symbols=set(symbols),
            data_types={DataType.PRICE, DataType.VOLUME}
        )
        interface3 = MockDataSource("MARKET_DATA", symbols)
        sync_system.register_source(source3, interface3)
        
        print(f"   ✓ {len(sync_system.sources)} fuentes registradas")
        
        # Iniciar sincronización
        print("\n3. Iniciando sincronización...")
        await sync_system.start_synchronization()
        print("   ✓ Sincronización iniciada")
        
        # Ejecutar por un tiempo para ver la sincronización
        print("\n4. Ejecutando sincronización (10 segundos)...")
        await asyncio.sleep(10)
        
        # Mostrar estadísticas de fuentes
        print("\n5. Estadísticas de fuentes:")
        source_stats = sync_system.get_source_statistics()
        for source_id, stats in source_stats.items():
            print(f"   {source_id}:")
            print(f"     - Actualizaciones: {stats['successful_updates']}/{stats['total_updates']} ({stats['success_rate']:.1f}%)")
            print(f"     - Latencia promedio: {stats['avg_latency']:.1f}ms")
            print(f"     - Elementos en cache: {stats['cached_items']}")
        
        # Mostrar estadísticas del sistema
        print("\n6. Estadísticas del sistema:")
        system_stats = sync_system.get_system_statistics()
        for key, value in system_stats.items():
            if isinstance(value, float):
                print(f"   {key}: {value:.2f}")
            else:
                print(f"   {key}: {value}")
        
        # Mostrar algunos datos actuales
        print("\n7. Datos actuales en cache:")
        for symbol in symbols:
            price_data = sync_system.get_latest_data(symbol, DataType.PRICE)
            volume_data = sync_system.get_latest_data(symbol, DataType.VOLUME)
            
            if price_data:
                print(f"   {symbol}: ${price_data.value:.2f} ({price_data.source_id})")
            if volume_data:
                print(f"   {symbol} Vol: {volume_data.value:,.0f} ({volume_data.source_id})")
        
        # Exportar datos
        print("\n8. Exportando datos...")
        data_df = sync_system.export_data_to_dataframe()
        conflicts_df = sync_system.export_conflicts_to_dataframe()
        
        print(f"   ✓ DataFrame de datos: {len(data_df)} registros")
        print(f"   ✓ DataFrame de conflictos: {len(conflicts_df)} registros")
        
        # Detener sincronización
        print("\n9. Deteniendo sincronización...")
        await sync_system.stop_synchronization()
        print("   ✓ Sincronización detenida")
        
        print("\n=== Demo Completado ===")
    
    # Ejecutar demo
    asyncio.run(demo())