import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, call
import os
import logging
from datetime import datetime
import zoneinfo

# Import the functions to be tested
from ml_model_trainer import _save_model_and_log_mlflow

# Setup logging for tests
@pytest.fixture(autouse=True)
def setup_test_logging():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)

@patch('ml_model_trainer.joblib.dump')
@patch('ml_model_trainer.mlflow')
@patch('ml_model_trainer.os.makedirs')
@patch('ml_model_trainer.log_model_validation')
def test_save_model_and_log_mlflow_success(mock_log_model_validation, mock_makedirs, mock_mlflow, mock_joblib_dump):
    # Mock the model pipeline and data
    feature_columns = ['rsi', 'macd']
    mock_model_pipeline = MagicMock()
    X_test = pd.DataFrame(np.random.rand(5, len(feature_columns)), columns=feature_columns)
    y_test = pd.Series(np.array([0, 1, 1, 1, 0]))
    X_train_full = pd.DataFrame(np.random.rand(10, len(feature_columns)), columns=feature_columns)
    y_train_full = pd.Series(np.random.randint(0, 2, 10))
    best_params = {'model__n_estimators': 100}
    cv_score = 0.85
    model_base_output_path = "test_model/model"

    mock_log_model_validation.return_value = {
        "metrics": {"accuracy": 0.9},
        "calibration": {"metrics": {"brier_score": 0.1}}
    }

    # Call the function
    from ml_model_trainer import _save_model_and_log_mlflow
    _save_model_and_log_mlflow(
        mock_model_pipeline,
        model_base_output_path,
        X_test,
        y_test,
        X_train_full,
        y_train_full,
        best_params,
        cv_score
    )

    # Assertions
    mock_makedirs.assert_called_once_with(os.path.dirname(model_base_output_path), exist_ok=True)

    # Check joblib.dump calls
    assert mock_joblib_dump.call_count == 2
    dump_calls = mock_joblib_dump.call_args_list
    assert f"{model_base_output_path}.pkl" in dump_calls[1].args[1]
    
    # Check mlflow calls
    mock_mlflow.pyfunc.log_model.assert_called_once()
    
    # Check log_model_validation call
    mock_log_model_validation.assert_called_once()

    # Check mlflow.log_metrics calls
    assert mock_mlflow.log_metrics.call_count == 2
    metrics_calls = mock_mlflow.log_metrics.call_args_list
    assert "advanced_test_accuracy" in metrics_calls[0].args[0]
    assert "calibrated_test_brier_score" in metrics_calls[1].args[0]


@patch('ml_model_trainer.joblib.dump')
@patch('ml_model_trainer.mlflow')
@patch('ml_model_trainer.os.makedirs')
@patch('ml_model_trainer.log_model_validation', side_effect=Exception("Test Exception"))
def test_save_model_and_log_mlflow_validation_exception(mock_log_model_validation, mock_makedirs, mock_mlflow, mock_joblib_dump):
    # Mock the model pipeline and data
    feature_columns = ['rsi', 'macd']
    mock_model_pipeline = MagicMock()
    X_test = pd.DataFrame(np.random.rand(5, len(feature_columns)), columns=feature_columns)
    y_test = pd.Series(np.array([0, 1, 1, 1, 0]))
    X_train_full = pd.DataFrame(np.random.rand(10, len(feature_columns)), columns=feature_columns)
    y_train_full = pd.Series(np.random.randint(0, 2, 10))
    best_params = {'model__n_estimators': 100}
    cv_score = 0.85
    model_base_output_path = "test_model/model"

    # Call the function
    from ml_model_trainer import _save_model_and_log_mlflow
    with patch('ml_model_trainer.logger') as mock_logger:
        _save_model_and_log_mlflow(
            mock_model_pipeline,
            model_base_output_path,
            X_test,
            y_test,
            X_train_full,
            y_train_full,
            best_params,
            cv_score
        )
        mock_logger.error.assert_called_once()
        assert "Error en validación avanzada del modelo ML" in mock_logger.error.call_args[0][0]

@patch('ml_model_trainer.initialize_mlflow')
@patch('ml_model_trainer._load_and_prepare_data')
@patch('ml_model_trainer._build_and_train_pipeline')
@patch('ml_model_trainer._evaluate_model')
@patch('ml_model_trainer._save_model_and_log_mlflow')
@patch('ml_model_trainer.mlflow')
def test_train_and_save_model_success(
    mock_mlflow,
    mock_save_model,
    mock_evaluate_model,
    mock_build_pipeline,
    mock_load_data,
    mock_init_mlflow
):
    # Mock return values
    X = pd.DataFrame({'a': [1]})
    y = pd.Series([1])
    X_train_full = pd.DataFrame({'a': [1]})
    y_train_full = pd.Series([1])
    X_test = pd.DataFrame({'a': [1]})
    y_test = pd.Series([1])
    mock_load_data.return_value = (X, y, X_train_full, y_train_full, X_test, y_test)
    
    mock_pipeline = MagicMock()
    mock_params = {'p': 1}
    mock_score = 0.9
    mock_build_pipeline.return_value = (mock_pipeline, mock_params, mock_score)

    # Call the function
    from ml_model_trainer import train_and_save_model
    train_and_save_model()

    # Assertions
    mock_init_mlflow.assert_called_once()
    mock_load_data.assert_called_once()
    mock_build_pipeline.assert_called_once_with(X_train_full, y_train_full)
    mock_evaluate_model.assert_called_once_with(mock_pipeline, X_test, y_test)
    mock_save_model.assert_called_once_with(
        mock_pipeline, "data/ml_models/lightgbm_model", X_test, y_test, X_train_full, y_train_full, mock_params, mock_score
    )
    assert mock_mlflow.start_run.call_count == 1


@patch('ml_model_trainer.initialize_mlflow')
@patch('ml_model_trainer._load_and_prepare_data')
@patch('ml_model_trainer._build_and_train_pipeline')
@patch('ml_model_trainer._evaluate_model')
@patch('ml_model_trainer._save_model_and_log_mlflow')
@patch('ml_model_trainer.mlflow')
def test_train_and_save_model_load_data_fails(
    mock_mlflow,
    mock_save_model,
    mock_evaluate_model,
    mock_build_pipeline,
    mock_load_data,
    mock_init_mlflow
):
    # Mock return values
    mock_load_data.return_value = (None, None, None, None, None, None)

    # Call the function
    from ml_model_trainer import train_and_save_model
    train_and_save_model()

    # Assertions
    mock_init_mlflow.assert_called_once()
    mock_load_data.assert_called_once()
    mock_build_pipeline.assert_not_called()
    mock_evaluate_model.assert_not_called()
    mock_save_model.assert_not_called()
    assert mock_mlflow.start_run.call_count == 1

@pytest.mark.asyncio
@patch('ml_model_trainer.send_message')
@patch('ml_model_trainer.await_confirmation')
@patch('ml_model_trainer.train_and_save_model')
async def test_train_and_notify_confirmed(
    mock_train_and_save_model,
    mock_await_confirmation,
    mock_send_message
):
    # Mock
    bot_instance = MagicMock()
    chat_id = 12345
    mock_await_confirmation.return_value = 'sí'

    # Call
    from ml_model_trainer import train_and_notify
    await train_and_notify(bot_instance, chat_id)

    # Assert
    assert mock_send_message.call_count == 2
    mock_train_and_save_model.assert_called_once()
    final_message = mock_send_message.call_args_list[1].args[2]
    assert "✅ Entrenamiento completado exitosamente" in final_message

@pytest.mark.asyncio
@patch('ml_model_trainer.send_message')
@patch('ml_model_trainer.await_confirmation')
@patch('ml_model_trainer.train_and_save_model')
async def test_train_and_notify_cancelled(
    mock_train_and_save_model,
    mock_await_confirmation,
    mock_send_message
):
    # Mock
    bot_instance = MagicMock()
    chat_id = 12345
    mock_await_confirmation.return_value = 'no'

    # Call
    from ml_model_trainer import train_and_notify
    await train_and_notify(bot_instance, chat_id)

    # Assert
    assert mock_send_message.call_count == 2
    mock_train_and_save_model.assert_not_called()
    final_message = mock_send_message.call_args_list[1].args[2]
    assert "❌ Entrenamiento cancelado por el usuario" in final_message

@pytest.mark.asyncio
@patch('ml_model_trainer.send_message')
@patch('ml_model_trainer.await_confirmation')
@patch('ml_model_trainer.train_and_save_model', side_effect=Exception("Training Error"))
async def test_train_and_notify_exception(
    mock_train_and_save_model,
    mock_await_confirmation,
    mock_send_message
):
    # Mock
    bot_instance = MagicMock()
    chat_id = 12345
    mock_await_confirmation.return_value = 'sí'

    # Call
    from ml_model_trainer import train_and_notify
    await train_and_notify(bot_instance, chat_id)

    # Assert
    assert mock_send_message.call_count == 2
    mock_train_and_save_model.assert_called_once()
    final_message = mock_send_message.call_args_list[1].args[2]
    assert "❌ Error durante el entrenamiento del modelo ML" in final_message
    assert "Training Error" in final_message

@patch('ml_model_trainer.mlflow')
@patch('ml_model_trainer.os.path.abspath')
def test_initialize_mlflow(mock_abspath, mock_mlflow):
    # Mock
    mock_abspath.return_value = '/fake/path/mlruns'

    # Call
    from ml_model_trainer import initialize_mlflow
    initialize_mlflow()

    # Assert
    mock_mlflow.set_tracking_uri.assert_called_once_with("file:///fake/path/mlruns")
    mock_mlflow.set_experiment.assert_called_once_with("ITBot_ML_Model_Training")
