from dataclasses import dataclass
from typing import Optional, Protocol, Any
import numpy as np

class ClusteringModel(Protocol):
    """Protocol defining the interface for any clustering model."""
    def fit_predict(self, X: np.ndarray) -> np.ndarray:
        ...

@dataclass
class NodeProfile:
    """Represents the health profile of a network node."""
    nodo_id: str
    total_fallas: int
    tiempo_promedio_minutos: float
    fallas_criticas: int
    porcentaje_critico: float
    grupo_ia: Optional[int] = None

@dataclass
class DetectionConfig:
    """Configuration parameters for the anomaly detector."""
    data_path: str
    n_clusters: int = 3
    min_fallas_threshold: int = 5
    random_state: int = 42
