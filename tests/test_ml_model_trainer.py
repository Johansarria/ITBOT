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

@pytest.fixture
def sample_feature_df():
    """Provides a sample DataFrame for testing ML data preparation."""
    data = {
        'close': np.linspace(100, 150, 100),
        'rsi': np.random.rand(100) * 100,
        'macd': np.random.rand(100),
        'macd_signal': np.random.rand(100),
        'stoch_k': np.random.rand(100) * 100,
        'stoch_d': np.random.rand(100) * 100,
        'cci': np.random.rand(100) * 200 - 100,
        'adx': np.random.rand(100) * 100,
        'plus_di': np.random.rand(100) * 100,
        'minus_di': np.random.rand(100) * 100,
        'atr': np.random.rand(100) * 10,
        'bb_upper': np.linspace(110, 160, 100),
        'bb_lower': np.linspace(90, 140, 100),
    }
    return pd.DataFrame(data)

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

@patch('ml_model_trainer.classification_report')
@patch('ml_model_trainer.mlflow')
def test_evaluate_model(mock_mlflow, mock_report, sample_feature_df):
    """Test the model evaluation and MLflow logging."""
    from ml_model_trainer import _evaluate_model

    # Prepare mock report
    mock_report.return_value = {
        "accuracy": 0.9,
        "weighted avg": {
            "f1-score": 0.88,
            "precision": 0.89,
            "recall": 0.87
        }
    }

    # Prepare mock pipeline and data
    mock_pipeline = MagicMock()
    mock_pipeline.predict.return_value = [0, 1] * 50
    X_test = sample_feature_df
    y_test = pd.Series([0, 1] * 50)

    # Call the function
    report = _evaluate_model(mock_pipeline, X_test, y_test)

    # Assertions
    mock_pipeline.predict.assert_called_once_with(X_test)
    assert mock_report.call_count == 2 # Called once for the dict, once for the string log

    expected_metrics = {
        "test_accuracy": 0.9,
        "test_f1_score_weighted": 0.88,
        "test_precision_weighted": 0.89,
        "test_recall_weighted": 0.87
    }
    mock_mlflow.log_metrics.assert_called_once_with(expected_metrics)
    assert report == mock_report.return_value

@patch('ml_model_trainer.GridSearchCV')
@patch('ml_model_trainer.mlflow')
def test_build_and_train_pipeline(mock_mlflow, mock_grid_search_cv, sample_feature_df):
    """Test the model building and training pipeline orchestration."""
    from ml_model_trainer import _build_and_train_pipeline

    # Prepare mock GridSearchCV instance
    mock_grid_instance = MagicMock()
    mock_grid_instance.best_estimator_ = "best_model"
    mock_grid_instance.best_params_ = {"model__n_estimators": 200}
    mock_grid_instance.best_score_ = 0.95
    mock_grid_search_cv.return_value = mock_grid_instance

    # Prepare dummy data
    X_train = sample_feature_df
    y_train = pd.Series([0, 1] * 50)

    # Call the function
    model, params, score = _build_and_train_pipeline(X_train, y_train)

    # Assertions
    mock_grid_search_cv.assert_called_once() # Check that GridSearchCV was initialized
    mock_grid_instance.fit.assert_called_once_with(X_train, y_train) # Check that fit was called

    assert model == "best_model"
    assert params == {"model__n_estimators": 200}
    assert score == 0.95

    mock_mlflow.log_params.assert_called_once_with({"model__n_estimators": 200})
    mock_mlflow.log_metric.assert_called_once_with("cv_f1_weighted_score", 0.95)

# --- Tests for _load_and_prepare_data ---

@patch('ml_model_trainer.pd.read_parquet', side_effect=FileNotFoundError)
def test_load_and_prepare_data_file_not_found(mock_read_parquet):
    """Test that the function handles a FileNotFoundError gracefully."""
    from ml_model_trainer import _load_and_prepare_data

    results = _load_and_prepare_data("dummy_path.parquet", 0.005, 1)
    assert all(res is None for res in results)

def test_load_and_prepare_data_happy_path(sample_feature_df):
    """Test the successful data preparation path."""
    from ml_model_trainer import _load_and_prepare_data

    with patch('ml_model_trainer.pd.read_parquet', return_value=sample_feature_df.copy()), \
         patch('ml_model_trainer.mlflow'): # Mock mlflow to avoid logging

        X, y, X_train, y_train, X_test, y_test = _load_and_prepare_data("dummy_path.parquet", 0.005, 1)

        assert X is not None
        assert y is not None
        assert not X.empty
        assert not y.empty
        assert len(X) == len(y)
        assert 'target' not in X.columns
        assert y.name == 'target'
        assert y.dtype == int
        assert len(X_train) + len(X_test) == len(X)

def test_load_and_prepare_data_no_valid_rows(sample_feature_df):
    """Test the case where no rows remain after dropping NaNs."""
    from ml_model_trainer import _load_and_prepare_data

    # Modify data so no target can be created
    df = sample_feature_df.copy()
    df['close'] = 100

    with patch('ml_model_trainer.pd.read_parquet', return_value=df), \
         patch('ml_model_trainer.mlflow'):

        results = _load_and_prepare_data("dummy_path.parquet", 0.005, 1)
        assert all(res is None for res in results)
