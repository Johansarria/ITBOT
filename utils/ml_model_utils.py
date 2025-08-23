# utils/ml_model_utils.py

import joblib
import os
import logging
from typing import Any, Dict
import numpy as np
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss, accuracy_score

logger = logging.getLogger(__name__)

def get_model_version(model_path: str) -> str:
    """Extrae la versión del modelo desde el nombre de archivo o metadatos si existen."""
    base = os.path.basename(model_path)
    if "v" in base:
        # Ejemplo: lightgbm_model_v1.2.3.pkl
        parts = base.split("_v")
        if len(parts) > 1:
            return parts[1].replace(".pkl", "")
    return "unknown"


def evaluate_model(model, X_test, y_test) -> Dict[str, Any]:
    """Evalúa el modelo en datos out-of-sample y retorna métricas clave."""
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None
    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_proba) if y_proba is not None else None,
        "brier_score": brier_score_loss(y_test, y_proba) if y_proba is not None else None,
        "log_loss": log_loss(y_test, y_proba) if y_proba is not None else None,
    }
    return metrics


def calibrate_model(model, X_calib, y_calib, method: str = "auto"):
    """Devuelve un modelo calibrado usando Platt (sigmoid) o Isotonic si es necesario."""
    if method == "auto":
        # Prueba ambos y elige el mejor por Brier
        cal1 = CalibratedClassifierCV(model, method="sigmoid", cv="prefit").fit(X_calib, y_calib)
        cal2 = CalibratedClassifierCV(model, method="isotonic", cv="prefit").fit(X_calib, y_calib)
        brier1 = brier_score_loss(y_calib, cal1.predict_proba(X_calib)[:, 1])
        brier2 = brier_score_loss(y_calib, cal2.predict_proba(X_calib)[:, 1])
        return cal1 if brier1 <= brier2 else cal2
    else:
        return CalibratedClassifierCV(model, method=method, cv="prefit").fit(X_calib, y_calib)


def get_thresholds(model) -> Dict[str, float]:
    """Devuelve los umbrales de decisión si están definidos en el modelo."""
    if hasattr(model, "thresholds_"):
        return {k: float(v) for k, v in model.thresholds_.items()}
    # Si no, devolver valores por defecto
    return {"default": 0.5}


def log_model_validation(model_path: str, model, X_test, y_test, X_calib=None, y_calib=None):
    version = get_model_version(model_path)
    thresholds = get_thresholds(model)
    metrics = evaluate_model(model, X_test, y_test)
    calibration = None
    if X_calib is not None and y_calib is not None:
        calibrated = calibrate_model(model, X_calib, y_calib)
        cal_metrics = evaluate_model(calibrated, X_test, y_test)
        calibration = {
            "method": "auto",
            "metrics": cal_metrics
        }
    logger.info(f"ML Model Validation | version: {version} | thresholds: {thresholds} | metrics: {metrics} | calibration: {calibration}")
    return {
        "model_version": version,
        "thresholds": thresholds,
        "metrics": metrics,
        "calibration": calibration
    }

import mlflow.pyfunc
import pandas as pd
from .feature_pipeline import FeaturePipeline

class MLModelWrapper(mlflow.pyfunc.PythonModel):
    """
    A custom MLflow model wrapper that includes the feature engineering pipeline.
    This ensures that the same feature transformations are applied during inference
    as were used during training.
    """
    def __init__(self, model, feature_columns_to_use: list[str]):
        self._model = model
        self._feature_pipeline = FeaturePipeline()
        self._feature_columns_to_use = feature_columns_to_use

    def _get_predictions(self, model, data: pd.DataFrame) -> np.ndarray:
        """Get predictions (probabilities) from the underlying model."""
        return model.predict_proba(data)

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        """
        The main prediction method for the MLflow model.
        It takes raw klines data, processes it, and returns predictions.
        """
        # 1. Generate all features from raw klines
        df_features = self._feature_pipeline.transform(model_input.copy())

        # 2. Select only the features the model was trained on
        # Ensure columns are in the same order as during training
        X = df_features[self._feature_columns_to_use]

        # 3. Get predictions (probabilities)
        probabilities = self._get_predictions(self._model, X)

        # Create a readable output
        # The model returns probabilities for class 0 (SELL) and 1 (BUY)
        results = pd.DataFrame({
            "sell_probability": probabilities[:, 0],
            "buy_probability": probabilities[:, 1]
        })

        return results
