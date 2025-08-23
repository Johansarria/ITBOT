import os
import numpy as np
import pandas as pd
import importlib

from utils import ml_model_utils as mmu


class DummyModel:
    def __init__(self):
        self.thresholds_ = {"a": 0.7}

    def predict(self, X):
        # Predict zeros
        return np.zeros(len(X), dtype=int)

    def predict_proba(self, X):
        # Return deterministic probabilities
        probs = np.linspace(0.1, 0.9, len(X))
        return np.column_stack([1 - probs, probs])


def test_get_model_version_from_name(tmp_path):
    path = str(tmp_path / "lightgbm_model_v1.2.3.pkl")
    assert mmu.get_model_version(path) == "1.2.3"


def test_get_model_version_unknown(tmp_path):
    path = str(tmp_path / "model.pkl")
    assert mmu.get_model_version(path) == "unknown"


def test_evaluate_model_with_proba():
    model = DummyModel()
    X_test = np.zeros((5, 2))
    # Use mixed classes so roc_auc can be computed
    y_test = np.array([0, 1, 0, 1, 0], dtype=int)
    metrics = mmu.evaluate_model(model, X_test, y_test)
    assert "accuracy" in metrics
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["roc_auc"] is not None


def test_get_thresholds_default_and_custom():
    class M: pass
    m = M()
    assert mmu.get_thresholds(m) == {"default": 0.5}
    m2 = DummyModel()
    assert mmu.get_thresholds(m2) == {"a": 0.7}


def test_log_model_validation_no_calib(tmp_path, caplog):
    model = DummyModel()
    X_test = np.zeros((4, 2))
    # Mixed classes for ROC AUC
    y_test = np.array([0, 1, 0, 1], dtype=int)
    out = mmu.log_model_validation(str(tmp_path / "m_v0.1.pkl"), model, X_test, y_test)
    # nombre "m_v0.1.pkl" contiene _v0.1, por lo que la versión extraída es '0.1'
    assert out["model_version"] == "0.1"
    assert "metrics" in out
