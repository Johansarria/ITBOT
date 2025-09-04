# utils/circuit_breaker.py

import logging
import time
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Circuit breaker is open, failing fast
    HALF_OPEN = "HALF_OPEN" # Testing if service has recovered

@dataclass
class CircuitBreakerStats:
    """Estadísticas del Circuit Breaker"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

class CircuitBreaker:
    """
    Circuit Breaker para prevenir fallos en cascada cuando hay problemas de conectividad.
    Específicamente diseñado para manejar problemas de base de datos alrededor de medianoche.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        
        self._state = CircuitBreakerState.CLOSED
        self._stats = CircuitBreakerStats()
        self._lock = Lock()
        
        logger.info(f"Circuit Breaker '{name}' inicializado - threshold: {failure_threshold}, timeout: {recovery_timeout}s")
    
    @property
    def state(self) -> CircuitBreakerState:
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        return self._stats
    
    def call(self, func, *args, **kwargs):
        """
        Ejecuta una función a través del circuit breaker.
        """
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"Circuit Breaker '{self.name}' -> HALF_OPEN (probando recuperación)")
                else:
                    logger.warning(f"Circuit Breaker '{self.name}' OPEN - fallando rápido")
                    raise Exception(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def async_call(self, func, *args, **kwargs):
        """
        Versión asíncrona del circuit breaker.
        """
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"Circuit Breaker '{self.name}' -> HALF_OPEN (probando recuperación)")
                else:
                    logger.warning(f"Circuit Breaker '{self.name}' OPEN - fallando rápido")
                    raise Exception(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            if hasattr(func, '__call__'):
                if hasattr(func, '__await__'):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Determina si deberíamos intentar resetear el circuit breaker."""
        if self._stats.last_failure_time is None:
            return True
        
        return (time.time() - self._stats.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Maneja el éxito de una operación."""
        with self._lock:
            self._stats.success_count += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()
            
            if self._state == CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.CLOSED
                logger.info(f"Circuit Breaker '{self.name}' -> CLOSED (recuperado)")
    
    def _on_failure(self):
        """Maneja el fallo de una operación."""
        with self._lock:
            self._stats.failure_count += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = time.time()
            
            if self._stats.consecutive_failures >= self.failure_threshold:
                if self._state != CircuitBreakerState.OPEN:
                    self._state = CircuitBreakerState.OPEN
                    logger.error(
                        f"Circuit Breaker '{self.name}' -> OPEN "
                        f"({self._stats.consecutive_failures} fallos consecutivos)"
                    )
    
    def reset(self):
        """Resetea manualmente el circuit breaker."""
        with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._stats.consecutive_failures = 0
            self._stats.consecutive_successes = 0
            logger.info(f"Circuit Breaker '{self.name}' reseteado manualmente")
    
    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado actual del circuit breaker."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "stats": {
                "failure_count": self._stats.failure_count,
                "success_count": self._stats.success_count,
                "consecutive_failures": self._stats.consecutive_failures,
                "consecutive_successes": self._stats.consecutive_successes,
                "last_failure_time": self._stats.last_failure_time,
                "last_success_time": self._stats.last_success_time,
            }
        }

# Instancia global para análisis de base de datos
db_circuit_breaker = CircuitBreaker(
    failure_threshold=3,  # Después de 3 fallos consecutivos
    recovery_timeout=60,  # Esperar 60 segundos antes de intentar de nuevo
    expected_exception=Exception,
    name="database_analysis"
)

# Instancia global para conectividad general
connectivity_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=30,
    expected_exception=Exception,
    name="general_connectivity"
)
