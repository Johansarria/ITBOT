# tests/test_risk_manager.py

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
from freezegun import freeze_time
from unittest.mock import patch, mock_open
import json

from config import settings


@pytest.fixture
def mock_file_paths(tmp_path):
    """Fixture to mock the file paths for operations and thresholds."""
    ops_path = tmp_path / "operaciones.csv"
    threshold_path = tmp_path / "thresholds.json"
    with patch('utils.risk_manager.OPERATIONS_LOG', str(ops_path)), \
         patch('utils.risk_manager.UMBRAL_FILE', str(threshold_path)):
        yield {"ops": ops_path, "thresholds": threshold_path}

@pytest.fixture(autouse=True)
def mock_state_manager():
    """Fixture que mockea el StateManager para aislar los tests de riesgo."""
    # Estado inicial por defecto para cada test
    mock_state = {
        "risk_manager": {
            "riesgo_actual": settings.DEFAULT_RISK_PERCENTAGE / 100.0,
            "riesgo_forzado": False,
            "tiempo_riesgo_forzado": None,
            "ganancias_riesgo_forzado": 0.0,
            "operaciones_riesgo_forzado": [],
            "recordatorio_riesgo_forzado_hoy": True,
        }
    }

    # Usar un diccionario en memoria para simular el archivo JSON
    state_store = {"risk_manager": mock_state["risk_manager"].copy()}

    def get_state(module, key=None):
        if key:
            return state_store.get(module, {}).get(key)
        return state_store.get(module)

    def update_module_state(module, updates):
        if module not in state_store:
            state_store[module] = {}
        state_store[module].update(updates)

    with patch('utils.risk_manager.StateManager') as mock_sm_class:
        mock_sm_instance = mock_sm_class.return_value
        mock_sm_instance.get_state.side_effect = get_state
        mock_sm_instance.update_module_state.side_effect = update_module_state
        yield

# --- Tests para las funciones de risk_manager ---

def test_obtener_riesgo_actual_initial():
    from utils import risk_manager
    assert risk_manager.obtener_riesgo_actual() == settings.DEFAULT_RISK_PERCENTAGE / 100

def test_riesgo_forzado_activo_initial():
    from utils import risk_manager
    assert not risk_manager.riesgo_forzado_activo()

def test_activar_riesgo_forzado():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(5.0)
    assert risk_manager.obtener_riesgo_actual() == 0.05
    assert risk_manager.riesgo_forzado_activo()
    state = risk_manager._get_risk_state()
    assert state.get("tiempo_riesgo_forzado") is not None
    assert state.get("recordatorio_riesgo_forzado_hoy") is True

def test_registrar_resultado_operacion():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(1.0) # Activar para que registre
    risk_manager.registrar_resultado_operacion(1.5)
    risk_manager.registrar_resultado_operacion(-0.5)
    state = risk_manager._get_risk_state()
    assert state.get("ganancias_riesgo_forzado") == 1.0
    assert state.get("operaciones_riesgo_forzado") == [1.5, -0.5]

def test_duracion_riesgo_forzado():
    from utils import risk_manager
    assert risk_manager.duracion_riesgo_forzado() == "0h"
    with freeze_time("2025-01-01 12:00:00"):
        risk_manager.activar_riesgo_forzado(5.0)
    with freeze_time("2025-01-01 15:00:00"):
        assert risk_manager.duracion_riesgo_forzado() == "3h"

def test_ganancias_durante_riesgo_forzado():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(1.0)
    risk_manager.registrar_resultado_operacion(2.0)
    risk_manager.registrar_resultado_operacion(-1.0)
    assert risk_manager.ganancias_durante_riesgo_forzado() == 1.0

def test_operaciones_en_riesgo_forzado():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(1.0)
    risk_manager.registrar_resultado_operacion(2.0)
    risk_manager.registrar_resultado_operacion(-1.0)
    risk_manager.registrar_resultado_operacion(0.5)
    stats = risk_manager.operaciones_en_riesgo_forzado()
    assert stats["total"] == 3
    assert stats["positivas"] == 2
    assert stats["negativas"] == 1

def test_calcular_probabilidad_ganancia_perdida_empty():
    from utils import risk_manager
    prob = risk_manager.calcular_probabilidad_ganancia_perdida()
    assert prob["ganar"] == 50.0
    assert prob["perder"] == 50.0

def test_calcular_probabilidad_ganancia_perdida_with_data():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(1.0)
    risk_manager.registrar_resultado_operacion(1.0)
    risk_manager.registrar_resultado_operacion(2.0)
    risk_manager.registrar_resultado_operacion(-0.5)
    risk_manager.registrar_resultado_operacion(0.0)
    prob = risk_manager.calcular_probabilidad_ganancia_perdida()
    assert prob["ganar"] == 50.0
    assert prob["perder"] == 50.0

def test_restaurar_riesgo_automatico():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(10.0)
    risk_manager.registrar_resultado_operacion(5.0)
    risk_manager.restaurar_riesgo_automatico()
    state = risk_manager._get_risk_state()
    assert risk_manager.obtener_riesgo_actual() == settings.DEFAULT_RISK_PERCENTAGE / 100
    assert not risk_manager.riesgo_forzado_activo()
    assert state.get("tiempo_riesgo_forzado") is None
    assert state.get("ganancias_riesgo_forzado") == 0.0
    assert state.get("operaciones_riesgo_forzado") == []
    assert state.get("recordatorio_riesgo_forzado_hoy") is True

def test_recordar_riesgo_forzado():
    from utils import risk_manager
    assert risk_manager.recordar_riesgo_forzado() is True
    risk_manager.desactivar_recordatorio_hoy()
    assert not risk_manager.recordar_riesgo_forzado()

def test_obtener_riesgo_ajustado_por_ml():
    from utils import risk_manager

    # Mock _OPTIMIZED_THRESHOLDS for consistent testing
    with patch('utils.risk_manager._OPTIMIZED_THRESHOLDS', {
        "umbral_alto": 0.9,
        "umbral_medio": 0.7,
        "umbral_bajo": 0.5
    }):
        # Test cases based on the new logic
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.95, riesgo_base=10.0) == 15.0 # score > umbral_alto (1.5x)
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.80, riesgo_base=10.0) == 10.0 # umbral_medio < score <= umbral_alto (1.0x)
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.60, riesgo_base=10.0) == 7.5  # umbral_bajo < score <= umbral_medio (0.75x)
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.40, riesgo_base=10.0) == 5.0  # score <= umbral_bajo (0.5x)
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.70, riesgo_base=10.0) == 10.0 # Edge case: score == umbral_medio
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.50, riesgo_base=10.0) == 7.5  # Edge case: score == umbral_bajo

def test_obtener_riesgo_ajustado():
    from utils import risk_manager

    # Casos de prueba con diferentes combinaciones de métricas
    riesgo_base = 10.0

    # Caso 1: Todas las métricas en valores medios
    assert risk_manager.obtener_riesgo_ajustado(
        score=0.5, volatilidad=0.5, drawdown=0.5, señales_técnicas=0.5, riesgo_base=riesgo_base
    ) == pytest.approx(10.0)

    # Caso 2: Score alto, drawdown bajo, volatilidad y señales medias
    assert risk_manager.obtener_riesgo_ajustado(
        score=0.9, volatilidad=0.5, drawdown=0.2, señales_técnicas=0.5, riesgo_base=riesgo_base
    ) > 10.0

    # Caso 3: Score bajo, drawdown alto, volatilidad y señales bajas
    assert risk_manager.obtener_riesgo_ajustado(
        score=0.2, volatilidad=0.3, drawdown=0.8, señales_técnicas=0.2, riesgo_base=riesgo_base
    ) < 10.0

    # Caso 4: Todas las métricas en valores extremos
    assert risk_manager.obtener_riesgo_ajustado(
        score=1.0, volatilidad=1.0, drawdown=0.0, señales_técnicas=1.0, riesgo_base=riesgo_base
    ) > 15.0

    assert risk_manager.obtener_riesgo_ajustado(
        score=0.0, volatilidad=0.0, drawdown=1.0, señales_técnicas=0.0, riesgo_base=riesgo_base
    ) < 5.0

# --- Tests for Permission Checks ---

def test_verificar_permiso_de_operacion_kill_switch():
    """Test that permission is denied if the extreme shield is active."""
    from utils.risk_manager import verificar_permiso_de_operacion
    with patch('utils.risk_manager.escudo_activo', return_value='extremo'):
        allowed, reason = verificar_permiso_de_operacion()
        assert not allowed
        assert "Kill Switch" in reason

def test_verificar_permiso_de_operacion_loss_limit():
    """Test that permission is denied if the daily loss limit is exceeded."""
    from utils.risk_manager import verificar_permiso_de_operacion
    with patch('utils.risk_manager._get_daily_pnl_pct', return_value=-11.0), \
         patch('utils.risk_manager.settings.MAX_DAILY_LOSS_PCT', 10.0):
        allowed, reason = verificar_permiso_de_operacion()
        assert not allowed
        assert "Límite de pérdida diaria" in reason

def test_verificar_permiso_de_operacion_position_limit():
    """Test that permission is denied if the concurrent position limit is exceeded."""
    from utils.risk_manager import verificar_permiso_de_operacion
    with patch('utils.risk_manager.get_open_positions', return_value=pd.DataFrame([{}, {}, {}])), \
         patch('utils.risk_manager.settings.MAX_CONCURRENT_POSITIONS', 3):
        allowed, reason = verificar_permiso_de_operacion()
        assert not allowed
        assert "Límite de posiciones concurrentes" in reason

def test_verificar_permiso_de_operacion_allowed():
    """Test that permission is granted when no limits are exceeded."""
    from utils.risk_manager import verificar_permiso_de_operacion
    with patch('utils.risk_manager.escudo_activo', return_value='ninguno'), \
         patch('utils.risk_manager._get_daily_pnl_pct', return_value=-1.0), \
         patch('utils.risk_manager.get_open_positions', return_value=pd.DataFrame()), \
         patch('utils.risk_manager.settings.MAX_DAILY_LOSS_PCT', 10.0), \
         patch('utils.risk_manager.settings.MAX_CONCURRENT_POSITIONS', 5):
        allowed, reason = verificar_permiso_de_operacion()
        assert allowed
        assert reason == "Permitido"

@pytest.mark.asyncio
async def test_perform_pre_execution_risk_checks():
    """Test the pre-execution risk checks."""
    from utils.risk_manager import perform_pre_execution_risk_checks

    # Test that it calls the general check
    with patch('utils.risk_manager.verificar_permiso_de_operacion', return_value=(False, "Test block")) as mock_general_check:
        allowed, reason = await perform_pre_execution_risk_checks({})
        assert not allowed
        assert reason == "Test block"
        mock_general_check.assert_called_once()

    # Test invalid quantity
    with patch('utils.risk_manager.verificar_permiso_de_operacion', return_value=(True, "")):
        allowed, reason = await perform_pre_execution_risk_checks({'quantity': 0})
        assert not allowed
        assert "Cantidad de operación inválida" in reason

# --- Tests for File I/O Functions ---

def test_get_daily_pnl_pct(mock_file_paths):
    """Test the _get_daily_pnl_pct function."""
    from utils.risk_manager import _get_daily_pnl_pct

    # Test with no file
    assert _get_daily_pnl_pct() == 0.0

    # Test with file and data for today
    with freeze_time("2025-08-13"):
        df = pd.DataFrame([
            {'timestamp_open': "2025-08-13", 'pnl_percent': 1.5},
            {'timestamp_open': "2025-08-13", 'pnl_percent': -0.5},
            {'timestamp_open': "2025-08-12", 'pnl_percent': 5.0}, # Yesterday
        ])
        df.to_csv(mock_file_paths["ops"], index=False)
        assert _get_daily_pnl_pct() == pytest.approx(1.0)

def test_cargar_umbrales_optimizado(mock_file_paths):
    """Test loading thresholds from a JSON file."""
    from utils.risk_manager import cargar_umbrales_optimizado

    # Test file not found (should return defaults)
    defaults = cargar_umbrales_optimizado()
    assert "umbral_alto" in defaults

    # Test successful load
    thresholds = {"umbral_alto": 0.95, "umbral_medio": 0.75, "umbral_bajo": 0.55}
    with open(mock_file_paths["thresholds"], "w") as f:
        json.dump(thresholds, f)
    loaded = cargar_umbrales_optimizado()
    assert loaded == thresholds

    # Test invalid JSON
    mock_file_paths["thresholds"].write_text("{invalid json")
    defaults_again = cargar_umbrales_optimizado()
    assert defaults_again["umbral_alto"] != 0.95 # Should be default, not the one from the last successful read

def test_guardar_umbrales_optimizado(mock_file_paths):
    """Test saving thresholds to a JSON file."""
    from utils.risk_manager import guardar_umbrales_optimizado

    thresholds = {"test_key": "test_value"}
    guardar_umbrales_optimizado(thresholds)

    with open(mock_file_paths["thresholds"], "r") as f:
        saved_data = json.load(f)

    assert saved_data == thresholds
