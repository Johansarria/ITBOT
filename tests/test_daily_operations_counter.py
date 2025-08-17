# tests/test_daily_operations_counter.py

import pytest
from unittest.mock import patch, mock_open
from datetime import datetime, timedelta
import json
import os
from freezegun import freeze_time # Para controlar el tiempo en los tests

# Importar el módulo a testear
from utils import daily_operations_counter

# Fixture para mockear las operaciones de archivo y asegurar un estado limpio
@pytest.fixture
def mock_counter_file(tmp_path):
    # Crear el directorio 'data' dentro del directorio temporal
    temp_data_dir = tmp_path / "data"
    temp_data_dir.mkdir(exist_ok=True)
    
    # Parchear la ruta del archivo del contador en el módulo
    with patch('utils.daily_operations_counter.COUNTER_FILE', str(temp_data_dir / "daily_operations_count.json")):
        yield

# Fixture para mockear el logger (para evitar salida en consola durante los tests)
@pytest.fixture(autouse=True)
def mock_logger():
    with patch('utils.daily_operations_counter.logger') as mock_log:
        yield mock_log

# --- Tests para get_daily_operations_count ---

def test_get_daily_operations_count_initial(mock_counter_file, mock_logger):
    # Simular que el archivo no existe inicialmente
    with patch('os.path.exists', return_value=False):
        count = daily_operations_counter.get_daily_operations_count()
        assert count == 0
        # Verificar que se intentó guardar el estado inicial
        mock_logger.info.assert_called_with("Nuevo día detectado. Reseteando contador de operaciones diarias. Anterior: 0")

def test_get_daily_operations_count_same_day(mock_counter_file, mock_logger):
    # Simular que el archivo existe y es del mismo día
    initial_state = {"date": "2025-01-01", "count": 5}
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=json.dumps(initial_state))):
            with freeze_time("2025-01-01"):
                count = daily_operations_counter.get_daily_operations_count()
                assert count == 5
                mock_logger.info.assert_not_called() # No debería resetearse

def test_get_daily_operations_count_new_day(mock_counter_file, mock_logger):
    # Simular que el archivo existe y es de un día anterior
    initial_state = {"date": "2025-01-01", "count": 5}
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=json.dumps(initial_state))):
            with patch('utils.daily_operations_counter._save_counter_state') as mock_save:
                with freeze_time("2025-01-02"):
                    count = daily_operations_counter.get_daily_operations_count()
                    assert count == 0
                    mock_logger.info.assert_called_with("Nuevo día detectado. Reseteando contador de operaciones diarias. Anterior: 5")
                    mock_save.assert_called_once_with({"date": "2025-01-02", "count": 0})

# --- Tests para increment_daily_operations_count ---

def test_increment_daily_operations_count_normal(mock_counter_file, mock_logger):
    # Simular que el archivo existe y es del mismo día
    initial_state = {"date": "2025-01-01", "count": 2}
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=json.dumps(initial_state))):
            with patch('utils.daily_operations_counter._save_counter_state') as mock_save:
                with freeze_time("2025-01-01"):
                    daily_operations_counter.increment_daily_operations_count()
                    mock_save.assert_called_once_with({"date": "2025-01-01", "count": 3})
                    mock_logger.info.assert_called_with("Contador de operaciones diarias incrementado a 3.")

def test_increment_daily_operations_count_new_day_reset(mock_counter_file, mock_logger):
    # Simular que el archivo existe y es de un día anterior
    initial_state = {"date": "2025-01-01", "count": 5}
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=json.dumps(initial_state))):
            with patch('utils.daily_operations_counter._save_counter_state') as mock_save:
                with freeze_time("2025-01-02"):
                    daily_operations_counter.increment_daily_operations_count()
                    mock_save.assert_called_once_with({"date": "2025-01-02", "count": 1})
                    from unittest.mock import call
                    mock_logger.info.assert_has_calls([
                        call("Nuevo día detectado al incrementar. Reseteando contador de operaciones diarias. Anterior: 5"),
                        call("Contador de operaciones diarias incrementado a 1.")
                    ])

# --- Tests para reset_daily_operations_count_manual ---

def test_reset_daily_operations_count_manual(mock_counter_file, mock_logger):
    # Simular un estado previo
    initial_state = {"date": "2025-01-01", "count": 10}
    with patch('os.path.exists', return_value=True):
        with patch('builtins.open', mock_open(read_data=json.dumps(initial_state))):
            with patch('utils.daily_operations_counter._save_counter_state') as mock_save:
                with freeze_time("2025-01-01"):
                    daily_operations_counter.reset_daily_operations_count_manual()
                    mock_save.assert_called_once_with({"date": "2025-01-01", "count": 0})
                    mock_logger.info.assert_called_with("Contador de operaciones diarias reseteado manualmente.")
