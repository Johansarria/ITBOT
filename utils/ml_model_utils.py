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
