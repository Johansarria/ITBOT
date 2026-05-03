import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from modules.node_anomaly.node_detector import NodeAnomalyDetector
from modules.node_anomaly.models import DetectionConfig

@pytest.fixture
def sample_data_path(tmp_path):
    """Crea un archivo CSV temporal con datos de prueba."""
    df = pd.DataFrame({
        'Nodo': ['A']*10 + ['B']*10,
        'Tipo_Falla': ['F']*20,
        'Minutos_Resolucion': [10]*20,
        'Prioridad': ['ALTA']*20
    })
    path = tmp_path / "test_data.csv"
    df.to_csv(path, index=False)
    return str(path)

@pytest.fixture
def mock_model():
    """Mock del modelo de clustering."""
    model = MagicMock()
    # Simulamos que fit_predict devuelve 0 para el primer nodo y 1 para el segundo
    model.fit_predict.return_value = np.array([0, 1])
    return model

def test_detector_uses_injected_model(sample_data_path, mock_model):
    """Verifica que el detector use el modelo inyectado (DI)."""
    config = DetectionConfig(data_path=sample_data_path, min_fallas_threshold=2)
    detector = NodeAnomalyDetector(config, mock_model)
    
    detector.load_and_prepare_data()
    detector.train()
    
    # Verificamos que se llamó a fit_predict del mock
    mock_model.fit_predict.assert_called_once()
    
def test_critical_cluster_logic_with_mock(sample_data_path, mock_model):
    """Verifica la lógica de selección de cluster crítico usando un mock."""
    config = DetectionConfig(data_path=sample_data_path, min_fallas_threshold=2)
    detector = NodeAnomalyDetector(config, mock_model)
    
    detector.load_and_prepare_data()
    detector.train()
    
    critical_nodes = detector.get_critical_nodes(top_n=1)
    # El cluster 0 tiene igual volumen de fallas, se elige el primero
    assert len(critical_nodes) == 1
