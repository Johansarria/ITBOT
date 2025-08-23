# ml_model_trainer.py

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import os
import logging
from datetime import datetime
import zoneinfo
import asyncio
import mlflow
import mlflow.sklearn
import hashlib

from utils.logger_setup import setup_logging
from utils.telegram_handler import send_message, await_confirmation
from utils.ml_model_utils import log_model_validation, MLModelWrapper
from utils.feature_pipeline import FeaturePipeline
import mlflow.pyfunc

setup_logging()
logger = logging.getLogger(__name__)

def initialize_mlflow():
    """Initializes the MLflow tracking URI and experiment."""
    # Correct the path to be relative to the project root, not the parent of the root.
    tracking_uri = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "mlruns"))
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("ITBot_ML_Model_Training")

def _get_file_hash(filepath):
    """Calculates the SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def _load_and_prepare_data(
    data_path: str,
    target_movement_pct: float,
    future_periods: int
):
    """Loads data, creates target variable, and prepares features for ML training."""
    try:
        df_features = pd.read_parquet(data_path)
        logger.info(f"Datos cargados desde {data_path}. Filas: {len(df_features)}")
    except FileNotFoundError:
        logger.error(f"Archivo de features no encontrado en {data_path}. Por favor, asegúrate de que el feature store ha sido construido.")
        return None, None, None, None, None, None

    mlflow.log_artifact(data_path, artifact_path="input_features")

    df_features['future_close'] = df_features['close'].shift(-future_periods)
    df_features['future_change_pct'] = (df_features['future_close'] - df_features['close']) / df_features['close']

    df_features['target'] = np.nan
    df_features.loc[df_features['future_change_pct'] >= target_movement_pct, 'target'] = 1
    df_features.loc[df_features['future_change_pct'] <= -target_movement_pct, 'target'] = 0
    
    df_ml = df_features.dropna(subset=['target']).copy()
    df_ml['target'] = df_ml['target'].astype(int)
    
    # NOTE: The model was originally trained on a subset of features.
    # To maintain consistency, we'll continue to use this subset.
    # A future improvement would be to make feature selection part of the ML pipeline.
    columns_to_use = [
        'rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci',
        'adx', 'plus_di', 'minus_di', 'atr', 'bb_upper', 'bb_lower'
    ]

    feature_pipeline = FeaturePipeline()
    available_features = feature_pipeline.get_feature_names()

    existing_feature_columns = []
    for col in columns_to_use:
        if col not in df_ml.columns:
            logger.warning(f"Columna de característica '{col}' no encontrada en el DataFrame. Se omitirá.")
        elif col not in available_features:
            logger.warning(f"Columna de característica '{col}' no está en el FeaturePipeline. Se omitirá.")
        else:
            df_ml[col] = pd.to_numeric(df_ml[col], errors='coerce').fillna(0)
            existing_feature_columns.append(col)

    X = df_ml[existing_feature_columns].copy()
    y = df_ml['target']
    
    logger.info(f"Datos preparados. Filas para ML: {len(X)}. Clases del target: {y.value_counts()}")

    if len(X) == 0:
        logger.warning("No hay suficientes datos válidos para entrenar el modelo después de la preparación.")
        return None, None, None, None, None, None

    test_size_ratio = 0.2
    split_index = int(len(X) * (1 - test_size_ratio))
    X_train_full, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train_full, y_test = y.iloc[:split_index], y.iloc[split_index:]
    logger.info(f"Datos divididos temporalmente. Entrenamiento completo: {len(X_train_full)} filas, Prueba: {len(X_test)} filas.")

    return X, y, X_train_full, y_train_full, X_test, y_test

def _build_and_train_pipeline(X_train_full: pd.DataFrame, y_train_full: pd.Series):
    """Builds and trains the ML pipeline using GridSearchCV and TimeSeriesSplit."""
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('model', LGBMClassifier(random_state=42, n_jobs=-1))
    ])

    param_grid = {
        'model__n_estimators': [100],
        'model__learning_rate': [0.05],
        'model__num_leaves': [31],
        'model__max_depth': [5]
    }

    tscv = TimeSeriesSplit(n_splits=3)

    grid_search = GridSearchCV(estimator=pipeline, param_grid=param_grid, cv=tscv, scoring='f1_weighted', verbose=1, n_jobs=-1)
    
    logger.info("Iniciando GridSearchCV con TimeSeriesSplit para optimización de hiperparámetros...")
    grid_search.fit(X_train_full, y_train_full)

    model_pipeline = grid_search.best_estimator_
    logger.info(f"Mejores hiperparámetros encontrados: {grid_search.best_params_}")
    logger.info(f"Mejor F1-score (weighted) en validación cruzada temporal: {grid_search.best_score_:.4f}")

    mlflow.log_params(grid_search.best_params_)
    mlflow.log_metric("cv_f1_weighted_score", grid_search.best_score_)

    logger.info("Modelo de LightGBM entrenado con los mejores hiperparámetros y pipeline de preprocesamiento.")
    return model_pipeline, grid_search.best_params_, grid_search.best_score_

def _evaluate_model(model_pipeline, X_test: pd.DataFrame, y_test: pd.Series):
    """Evaluates the trained model on the test set."""
    y_pred = model_pipeline.predict(X_test)
    
    report = classification_report(y_test, y_pred, output_dict=True)
    mlflow.log_metrics({
        "test_accuracy": report["accuracy"],
        "test_f1_score_weighted": report["weighted avg"]["f1-score"],
        "test_precision_weighted": report["weighted avg"]["precision"],
        "test_recall_weighted": report["weighted avg"]["recall"]
    })

    logger.info("\n--- Reporte de Clasificación en Conjunto de Prueba ---")
    logger.info(classification_report(y_test, y_pred))
    logger.info("\n--- Matriz de Confusión en Conjunto de Prueba ---")
    logger.info(confusion_matrix(y_test, y_pred))
    return report

def _save_model_and_log_mlflow(
    model_pipeline,
    model_base_output_path: str,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    X_train_full: pd.DataFrame,
    y_train_full: pd.Series,
    best_params: dict,
    cv_score: float
):
    """Saves the model and logs advanced validation metrics to MLflow."""
    timestamp = datetime.now(zoneinfo.ZoneInfo("UTC")).strftime("%Y%m%d_%H%M%S")
    model_output_path_versioned = f"{model_base_output_path}_{timestamp}.pkl"
    os.makedirs(os.path.dirname(model_base_output_path), exist_ok=True)
    joblib.dump(model_pipeline, model_output_path_versioned)
    logger.info(f"Modelo (pipeline scikit-learn) guardado en {model_output_path_versioned}")

    joblib.dump(model_pipeline, f"{model_base_output_path}.pkl")
    logger.info(f"Copia del modelo (pipeline scikit-learn) más reciente guardada como {model_base_output_path}.pkl")

    # Envolver y loggear el modelo como un pyfunc model de MLflow
    feature_columns = X_train_full.columns.to_list()
    mlflow_pyfunc_model = MLModelWrapper(model=model_pipeline, feature_columns_to_use=feature_columns)

    mlflow.pyfunc.log_model(
        artifact_path="model",
        python_model=mlflow_pyfunc_model,
        code_paths=["utils/feature_pipeline.py", "utils/ml_model_utils.py"] # Dependencias de código
    )
    logger.info("Modelo MLflow PyFunc (wrapper con pipeline) loggeado en MLflow.")

    # El loggeo de validación avanzada puede continuar como estaba
    try:
        calib_size = int(0.1 * len(X_train_full))
        if calib_size > 0:
            X_calib, y_calib = X_train_full[-calib_size:], y_train_full[-calib_size:]
        else:
            X_calib, y_calib = None, None
        validation_info = log_model_validation(
            model_output_path_versioned,
            model_pipeline,
            X_test,
            y_test,
            X_calib,
            y_calib
        )
        logger.info(f"ML Model Validation Summary: {validation_info}")
        
        if validation_info and "metrics" in validation_info:
            mlflow.log_metrics({f"advanced_test_{k}": v for k, v in validation_info["metrics"].items() if v is not None})
        if validation_info and "calibration" in validation_info and validation_info["calibration"] and "metrics" in validation_info["calibration"]:
            mlflow.log_metrics({f"calibrated_test_{k}": v for k, v in validation_info["calibration"]["metrics"].items() if v is not None})

    except Exception as e:
        logger.error(f"Error en validación avanzada del modelo ML: {e}", exc_info=True)

def train_and_save_model(
    data_path: str = "data/features/klines_enriched.parquet",
    model_base_output_path: str = "data/ml_models/lightgbm_model",
    target_movement_pct: float = 0.005,
    future_periods: int = 1
):
    logger.info("Iniciando entrenamiento del modelo de Machine Learning.")
    initialize_mlflow()
    with mlflow.start_run():
        mlflow.log_param("data_path", data_path)
        mlflow.log_param("target_movement_pct", target_movement_pct)
        mlflow.log_param("future_periods", future_periods)

        feature_pipeline_path = "utils/feature_pipeline.py"
        if os.path.exists(feature_pipeline_path):
            pipeline_hash = _get_file_hash(feature_pipeline_path)
            mlflow.log_param("feature_pipeline_code_hash", pipeline_hash)
            mlflow.log_artifact(feature_pipeline_path, artifact_path="feature_pipeline_code")
            logger.info(f"FeaturePipeline code hash logged: {pipeline_hash}")
        else:
            logger.warning(f"FeaturePipeline code not found at {feature_pipeline_path}. Skipping code version logging.")

        X, y, X_train_full, y_train_full, X_test, y_test = _load_and_prepare_data(
            data_path, target_movement_pct, future_periods
        )
        if X is None or y is None:
            return

        model_pipeline, best_params, cv_score = _build_and_train_pipeline(X_train_full, y_train_full)
        _evaluate_model(model_pipeline, X_test, y_test)
        _save_model_and_log_mlflow(
            model_pipeline,
            model_base_output_path,
            X_test,
            y_test,
            X_train_full,
            y_train_full,
            best_params,
            cv_score
        )

async def train_and_notify(bot_instance, chat_id):
    """
    Función que envía notificaciones a través de Telegram antes, durante y después del entrenamiento del modelo ML.
    """
    await send_message(bot_instance, chat_id, "⚙️ El entrenamiento del modelo ML tomará aproximadamente 10 minutos. ¿Deseas continuar? (Responde 'sí' para proceder)")

    confirmation = await await_confirmation(bot_instance, chat_id)
    if confirmation.lower() != 'sí':
        await send_message(bot_instance, chat_id, "❌ Entrenamiento cancelado por el usuario.")
        return

    try:
        train_and_save_model()
        await send_message(bot_instance, chat_id, "✅ Entrenamiento completado exitosamente. El modelo ha sido guardado.")
    except Exception as e:
        await send_message(bot_instance, chat_id, f"❌ Error durante el entrenamiento del modelo ML: {e}")

if __name__ == "__main__":
    # import config
    # from aiogram import Bot

    # bot = Bot(token=config.TELEGRAM_TOKEN)
    # chat_id = config.TELEGRAM_CHAT_ID

    # asyncio.run(train_and_notify(bot, chat_id))
    train_and_save_model()
