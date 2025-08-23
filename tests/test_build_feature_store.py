import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
import runpy

# Import directo de la función a probar
from build_feature_store import build_and_save_feature_store


@patch('build_feature_store.get_klines')
@patch('build_feature_store.enrich_features')
@patch('build_feature_store.calculate_all_indicators')
@patch('pandas.DataFrame.to_parquet')
def test_build_and_save_feature_store(mock_to_parquet,
                                      mock_calc_indicators,
                                      mock_enrich_features,
                                      mock_get_klines):
    """Prueba directa de build_and_save_feature_store (sin mlflow)."""

    # Setup
    mock_get_klines.return_value = pd.DataFrame({'close': [1, 2, 3]})
    mock_calc_indicators.return_value = pd.DataFrame({'close': [1, 2, 3], 'ind': [0.1, 0.2, 0.3]})
    mock_enrich_features.return_value = pd.DataFrame({'close': [1, 2, 3], 'feat': [10, 20, 30]})

    # Run
    build_and_save_feature_store()

    # Checks
    mock_get_klines.assert_called_once()
    mock_calc_indicators.assert_called_once()
    mock_enrich_features.assert_called_once()
    mock_to_parquet.assert_called_once()


@patch('mlflow.start_run')
@patch('mlflow.log_param')
@patch('mlflow.log_artifact')
@patch('build_feature_store.build_and_save_feature_store') # Mock the function to avoid running it again
def test_main_block_triggers_mlflow(mock_build_and_save, 
                                    mock_log_artifact,
                                    mock_log_param,
                                    mock_start_run):
    """Prueba que el bloque __main__ ejecute mlflow al correr como script."""

    mock_run_context = MagicMock()
    mock_start_run.return_value.__enter__.return_value = mock_run_context

    # Ejecutar build_feature_store como si fuera __main__
    runpy.run_module("build_feature_store", run_name="__main__")

    # Assert que mlflow fue usado
    mock_start_run.assert_called_once()
    mock_log_param.assert_called()
    mock_log_artifact.assert_called()
    mock_build_and_save.assert_called_once()