    # strategies/strategy_manager.py

import os
import importlib.util
import logging
import asyncio
import inspect
from typing import Dict, Any, List, Type, Optional
from datetime import datetime, timedelta

from strategies.base_strategy import BaseStrategy
from strategies.backtester import Backtester, generate_mock_data
from utils.technical_analysis import get_historical_klines
from utils.risk_manager import _OPTIMIZED_THRESHOLDS
from utils.state_manager import StateManager

logger = logging.getLogger(__name__)

class StrategyManager:

    async def analyze_all_strategies(self, symbol: str = "BTCUSDT", interval: str = "1h", limit: int = 200) -> dict:
        """
        Ejecuta el análisis de todas las estrategias activas con los datos más recientes y selecciona la mejor decisión para la siguiente operación.
        Devuelve un resumen con la decisión y score de cada estrategia y la recomendación final.
        """
        # Obtener datos históricos una sola vez
        historical_data = await get_historical_klines(symbol, interval, limit)
        if historical_data.empty:
            return {"error": "No se pudieron obtener datos históricos"}

        results: Dict[str, Any] = {}
        best_score = float('-inf')
        best_strategy: Optional[str] = None
        best_decision: Optional[str] = None
        for name, strategy in self._strategies.items():
            try:
                analyze_sig = inspect.signature(strategy.analyze)
                kwargs = {}
                # Pasar solo los parámetros que la estrategia declara (siempre por nombre)
                df_param_name = next((k for k in ['df', 'data', 'df_klines', 'ohlcv', 'klines', 'candles', 'historical_data'] if k in analyze_sig.parameters), None)
                if df_param_name:
                    kwargs[df_param_name] = historical_data.copy()
                if 'current_index' in analyze_sig.parameters:
                    kwargs['current_index'] = len(historical_data) - 1
                if 'symbol' in analyze_sig.parameters:
                    kwargs['symbol'] = symbol
                if 'interval' in analyze_sig.parameters:
                    kwargs['interval'] = interval

                call = strategy.analyze(**kwargs)
                if inspect.iscoroutine(call):
                    result = await call
                else:
                    result = call

                # Asegurar que result sea un dict y no una coroutina
                if inspect.iscoroutine(result):
                    result = await result

                results[name] = result
                score = result.get("score", 0) if isinstance(result, dict) else 0
                if score > best_score:
                    best_score = score
                    best_strategy = name
                    best_decision = result.get("decision")
            except Exception as e:
                results[name] = {"error": str(e)}

        return {
            "results": results,
            "best_strategy": best_strategy,
            "best_decision": best_decision,
            "best_score": best_score
        }
    _instance = None
    _strategies: Dict[str, BaseStrategy] = {}
    _active_strategy: Optional[BaseStrategy] = None
    _performance_cache: List[Dict[str, Any]] = []
    _cache_timestamp: Optional[datetime] = None
    CACHE_DURATION = timedelta(hours=4)
    _auto_mode_enabled: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StrategyManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Inicializa el estado y carga las estrategias."""
        state_manager = StateManager()
        persisted_state = state_manager.get_state("strategy_manager")
        if persisted_state:
            self._auto_mode_enabled = persisted_state.get("auto_mode_enabled", False)
        else:
            self._auto_mode_enabled = False
        logger.info(f"Modo automático de estrategias inicializado a: {'Activado' if self._auto_mode_enabled else 'Desactivado'}")
        self.reload_strategies()

    def reload_strategies(self):
        """Limpia y vuelve a descubrir todas las estrategias y limpia la caché."""
        self._strategies = {}
        logger.info("Recargando estrategias...")
        self._discover_strategies()
        self._performance_cache = []
        self._cache_timestamp = None
        logger.info("Caché de rendimiento de estrategias limpiada.")
        
        if not self._active_strategy and self._strategies:
            default_strategy_name = list(self._strategies.keys())[0]
            self._active_strategy = self._strategies[default_strategy_name]
            logger.info(f"Estrategia por defecto establecida: {self._active_strategy.name}")
        elif not self._strategies:
            self._active_strategy = None
            logger.warning("No se encontraron estrategias.")

    def _discover_strategies(self):
        strategy_dir = os.path.dirname(__file__)
        for filename in os.listdir(strategy_dir):
            if filename.endswith(".py") and filename not in ["__init__.py", "base_strategy.py", "strategy_manager.py", "backtester.py"]:
                module_name = filename[:-3]
                file_path = os.path.join(strategy_dir, filename)
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        for attribute_name in dir(module):
                            attribute = getattr(module, attribute_name)
                            # Solo instanciar clases concretas que hereden de BaseStrategy (no la abstracta)
                            if (
                                isinstance(attribute, type)
                                and issubclass(attribute, BaseStrategy)
                                and attribute is not BaseStrategy
                            ):
                                try:
                                    # Preferir instanciación con (name, description) si el constructor lo soporta
                                    try:
                                        strategy_instance = attribute(name=attribute.__name__, description=attribute.__doc__ or "")
                                    except TypeError:
                                        # Fallback: instanciar sin argumentos (las estrategias suelen llamar a super().__init__ internamente)
                                        strategy_instance = attribute()
                                    # Registrar estrategia si expone 'name'
                                    name = getattr(strategy_instance, 'name', None) or attribute.__name__
                                    self._strategies[name] = strategy_instance
                                    logger.info(f"Estrategia descubierta: {name}")
                                except Exception as e:
                                    logger.exception(f"Error al instanciar la estrategia {attribute.__name__}: {e}")
                except Exception as e:
                    logger.exception(f"Error al cargar la estrategia desde {filename}: {e}")

    async def update_performance_cache(self, symbol: str = "BTCUSDT", interval: str = "4h", limit: int = 500):
        """Ejecuta un backtest para cada estrategia y actualiza la caché de rendimiento."""
        logger.info("Iniciando actualización de caché de rendimiento de estrategias...")
        try:
            historical_data = await get_historical_klines(symbol, interval, limit)
            if historical_data.empty:
                raise ValueError("Datos históricos vacíos desde la API.")
            logger.info("Datos reales obtenidos para el backtesting.")
        except (asyncio.TimeoutError, ValueError) as e:
            logger.warning(f"No se pudieron obtener datos reales ({e}). Usando datos de prueba (mock data) para el backtesting.")
            historical_data = generate_mock_data(days=limit)

        if historical_data.empty:
            logger.error("No se pudieron obtener ni generar datos para el backtesting de rendimiento.")
            self._performance_cache = []
            return

        results = []
        for name, strategy in self._strategies.items():
            backtester = Backtester(historical_data.copy())
            metrics = await backtester.run(strategy)
            results.append({
                "name": name,
                "description": strategy.description,
                "performance": metrics
            })
        
        self._performance_cache = results
        self._cache_timestamp = datetime.now()
        logger.info(f"Caché de rendimiento de estrategias actualizada exitosamente a las {self._cache_timestamp}.")

    def get_strategies_with_performance(self) -> List[Dict[str, Any]]:
        """Devuelve el rendimiento de las estrategias desde la caché."""
        return self._performance_cache

    def is_cache_valid(self) -> bool:
        """Verifica si la caché de rendimiento es reciente y no está vacía."""
        if not self._performance_cache or not self._cache_timestamp:
            return False
        return datetime.now() - self._cache_timestamp < self.CACHE_DURATION

    def enable_auto_mode(self):
        """Activa el modo de selección automática de estrategia."""
        self._auto_mode_enabled = True
        StateManager().set_state("strategy_manager", "auto_mode_enabled", True)
        logger.info("Modo automático de selección de estrategia: ACTIVADO")

    def disable_auto_mode(self):
        """Desactiva el modo de selección automática de estrategia."""
        self._auto_mode_enabled = False
        StateManager().set_state("strategy_manager", "auto_mode_enabled", False)
        logger.info("Modo automático de selección de estrategia: DESACTIVADO")

    def is_auto_mode_enabled(self) -> bool:
        """Comprueba si el modo automático está activado."""
        return self._auto_mode_enabled

    async def select_best_strategy(self) -> str | None:
        """Realiza el backtesting y selecciona la mejor estrategia basándose en el Sharpe Ratio."""
        logger.info("Iniciando selección automática de la mejor estrategia...")
        await self.update_performance_cache()
        performance_results = self.get_strategies_with_performance()
        
        if not performance_results:
            logger.warning("No hay resultados de rendimiento para seleccionar la mejor estrategia.")
            return None

        # Ordenar por Sharpe Ratio (primario) y retorno (secundario) para desempate
        sorted_results = sorted(
            performance_results, 
            key=lambda x: (
                x.get("performance", {}).get("sharpe_ratio", -999),
                x.get("performance", {}).get("total_return_pct", -999)
            ), 
            reverse=True
        )
        
        best_strategy_info = sorted_results[0]
        best_strategy_name = best_strategy_info.get("name")
        
        if best_strategy_name:
            current_active_strategy = self.get_active_strategy().name
            if current_active_strategy != best_strategy_name:
                self.set_active_strategy(best_strategy_name)
                logger.info(f"Nueva mejor estrategia seleccionada automáticamente: {best_strategy_name}")
                return best_strategy_name
            else:
                logger.info(f"La mejor estrategia ({best_strategy_name}) ya está activa. No se realizan cambios.")
                return None # Retorna None si no hay cambio
        
        logger.error("No se pudo determinar la mejor estrategia del ranking.")
        return None

    def list_available_strategies(self) -> List[str]:
        return list(self._strategies.keys())

    def set_active_strategy(self, strategy_name: str) -> bool:
        if self.is_auto_mode_enabled():
            logger.warning("No se puede cambiar la estrategia manualmente mientras el modo automático está activado.")
            return False
        if strategy_name in self._strategies:
            self._active_strategy = self._strategies[strategy_name]
            logger.info(f"Estrategia activa cambiada a: {strategy_name}")
            return True
        logger.warning(f"Estrategia '{strategy_name}' no encontrada.")
        return False

    def get_active_strategy(self) -> BaseStrategy:
        if not self._active_strategy:
            self.reload_strategies()
            if not self._active_strategy:
                raise ValueError("No se pudo seleccionar una estrategia activa porque no se encontró ninguna.")
        return self._active_strategy

    def get_strategy_by_name(self, strategy_name: str) -> BaseStrategy | None:
        return self._strategies.get(strategy_name)

    def _reset_manager(self): # Método para uso en pruebas
        StrategyManager._instance = None
        StrategyManager._strategies = {}
        StrategyManager._active_strategy = None
        StrategyManager._performance_cache = []
        StrategyManager._cache_timestamp = None
        StrategyManager._auto_mode_enabled = False
