"""
Test de regresión para pipeline de entrenamiento ML.
Verifica que el pipeline produce métricas consistentes y no hay degradación.
"""
import os
import joblib
import numpy as np
from features.feature_store import load_features
from train_pipeline import FEATURE_NAME, FEATURE_VERSION
from utils.ml_model_utils import log_model_validation

MODEL_DIR = 'data/ml_models/'

# Métricas mínimas esperadas (ajusta según baseline)
MIN_ACCURACY = 0.5


def test_regression_training():
    # Cargar modelo entrenado
    model_path = os.path.join(MODEL_DIR, f'lgbm_model_{FEATURE_VERSION}.pkl')
    assert os.path.exists(model_path), f"Modelo no encontrado: {model_path}"
    model = joblib.load(model_path)

    # Cargar features y datos de test
    Xy = load_features(FEATURE_NAME, FEATURE_VERSION)
    X = Xy.drop('target', axis=1)
    y = Xy['target']
    # Usar el mismo split que en el pipeline
    n = int(len(X) * 0.8)
    X_test, y_test = X.iloc[n:], y.iloc[n:]

    # Validar modelo
    metrics = log_model_validation(model_path=model_path, model=model, X_test=X_test, y_test=y_test)
    assert metrics['metrics']['accuracy'] >= MIN_ACCURACY, f"Accuracy degradado: {metrics['metrics']['accuracy']} < {MIN_ACCURACY}"
    print(f"Test de regresión OK. Accuracy: {metrics['metrics']['accuracy']}")
