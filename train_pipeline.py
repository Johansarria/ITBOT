"""
Pipeline reproducible de entrenamiento ML con logging, versionado y uso de feature store.
"""
import pandas as pd
import numpy as np
import logging
import random
import os
import sys
from datetime import datetime
from features.feature_store import save_features, load_features
from utils.drift_detection import detect_feature_drift, log_and_alert_drift
from utils.ml_model_utils import log_model_validation
from sklearn.model_selection import train_test_split
from lightgbm import LGBMClassifier
import joblib

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


# 1. Cargar datos crudos y generar features
RAW_PATH = 'data/analisis/historical_klines_BTCUSDT_4h_1_Jan_2022_now.csv'
FEATURE_NAME = 'btc_features'
FEATURE_VERSION = datetime.now().strftime('%Y%m%d')

logging.info('Cargando datos crudos...')
df = pd.read_csv(RAW_PATH)
# Aquí iría la lógica de generación de features (placeholder)
df['feature1'] = df['close'].pct_change().fillna(0)
df['feature2'] = df['volume'].rolling(3).mean().fillna(0)
# ... más features ...
features = df[['feature1', 'feature2']].copy()
features['target'] = (df['close'].shift(-1) > df['close']).astype(int)

# 2. Detección de drift: comparar features actuales vs. referencia previa
import os
ref_version = None
ref_features = None
feature_dir = os.path.join(os.path.dirname(__file__), 'data/features')
if os.path.exists(feature_dir):
	files = sorted([f for f in os.listdir(feature_dir) if f.startswith(FEATURE_NAME) and f.endswith('.parquet')])
	if len(files) > 1:
		ref_file = files[-2]  # penúltima versión
		ref_features = load_features(FEATURE_NAME, ref_file.split('_')[-1].replace('.parquet',''))
		drifted = detect_feature_drift(ref_features.drop('target', axis=1), features.drop('target', axis=1))
		log_and_alert_drift(drifted)

# 3. Guardar features en el feature store
save_features(features, FEATURE_NAME, FEATURE_VERSION)
logging.info(f'Features guardados: {FEATURE_NAME}_{FEATURE_VERSION}')

# 3. Cargar features para entrenamiento
Xy = load_features(FEATURE_NAME, FEATURE_VERSION)
X = Xy.drop('target', axis=1)
y = Xy['target']

# 4. Split reproducible
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)

# 5. Entrenamiento reproducible
model = LGBMClassifier(random_state=SEED)
model.fit(X_train, y_train)



# 6. Guardar modelo versionado (antes de validar)
MODEL_DIR = 'data/ml_models/'
os.makedirs(MODEL_DIR, exist_ok=True)
model_path = os.path.join(MODEL_DIR, f'lgbm_model_{FEATURE_VERSION}.pkl')
joblib.dump(model, model_path)
logging.info(f'Modelo guardado: {model_path}')

# 7. Validación y logging
metrics = log_model_validation(
	model_path=model_path,
	model=model,
	X_test=X_test,
	y_test=y_test
)
logging.info(f'Métricas de validación: {metrics}')
