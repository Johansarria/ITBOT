# strategies/base_strategy.py

from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseStrategy(ABC):
    """
    Clase base abstracta para todas las estrategias de trading.
    Define la interfaz que cada estrategia debe implementar.
    """

    def __init__(self, name: str, description: str):
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @abstractmethod
    async def analyze(self, historical_data: pd.DataFrame, current_index: int) -> Dict[str, Any]:
        """
        Implementa la lógica de análisis técnico y decisión de la estrategia.
        Debe aceptar un DataFrame de klines y devolver una decisión (str) y un score (int).
        Esta es una corrutina.
        """
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        Devuelve un diccionario con los parámetros configurables de la estrategia.
        """
        pass

    @abstractmethod
    def set_parameters(self, params: Dict[str, Any]):
        """
        Establece los parámetros configurables de la estrategia.
        """
        pass
