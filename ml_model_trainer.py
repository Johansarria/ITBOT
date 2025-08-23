# ml_model_trainer.py

import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV # MODIFIED: Added TimeSeriesSplit
from sklearn.pipeline import Pipeline # ADDED
from sklearn.preprocessing import StandardScaler # ADDED
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, confusion_matrix, make_scorer, accuracy_score, precision_score, recall_score, f1_score
import joblib # Para guardar y cargar el modelo
import os
import logging
from datetime import datetime, timezone # ADDED for model versioning
import zoneinfo
import asyncio
import mlflow
import mlflow.sklearn # ADDED for MLflow integration

from utils.technical_analysis import calculate_all_indicators
from utils.logger_setup import setup_logging
from utils.telegram_handler import send_message, await_confirmation

setup_logging() # Configurar logging para este script
logger = logging.getLogger(__name__)

# Configurar MLflow tracking URI (para desarrollo local)
# Esto creará un directorio 'mlruns' en el directorio de trabajo actual si no existe
mlflow.set_tracking_uri("file:./mlruns")
mlflow.set_experiment("ITBot_ML_Model_Training")

def train_and_save_model(
    data_path: str = "data/analisis/historical_klines_BTCUSDT_4h_1_Jan_2022_now.csv",
    model_base_output_path: str = "data/ml_models/lightgbm_model", # MODIFIED: Base path for versioning
    target_movement_pct: float = 0.005, # 0.5% de movimiento para clasificar
    future_periods: int = 1 # Predecir la siguiente vela
):
    logger.info("Iniciando entrenamiento del modelo de Machine Learning.")

    with mlflow.start_run():
        # Log parameters
        mlflow.log_param("data_path", data_path)
        mlflow.log_param("target_movement_pct", target_movement_pct)
        mlflow.log_param("future_periods", future_periods)

        # 1. Cargar datos
        try:
            df = pd.read_csv(data_path, index_col="timestamp", parse_dates=True)
            logger.info(f"Datos cargados desde {data_path}. Filas: {len(df)}")
        except FileNotFoundError:
            logger.error(f"Archivo de datos no encontrado en {data_path}. Por favor, descarga los datos primero.")
            return

        # 2. Calcular indicadores técnicos (Features)
        df_features = calculate_all_indicators(df.copy())
        logger.info("Indicadores técnicos calculados.")

        # 3. Crear la variable objetivo (Target)
        # Shift para obtener el precio de cierre futuro
        df_features['future_close'] = df_features['close'].shift(-future_periods)
        
        # Calcular el cambio porcentual futuro
        df_features['future_change_pct'] = (df_features['future_close'] - df_features['close']) / df_features['close']

        # Definir la variable objetivo: 1 si sube, 0 si baja (ignorando laterales)
        df_features['target'] = np.nan
        df_features.loc[df_features['future_change_pct'] >= target_movement_pct, 'target'] = 1
        df_features.loc[df_features['future_change_pct'] <= -target_movement_pct, 'target'] = 0
        
        # Eliminar filas con NaN en el target (movimientos laterales o datos incompletos)
        df_ml = df_features.dropna(subset=['target']).copy()
        
        # Seleccionar las características (indicadores) y el target
        # Excluir columnas que no son features o que son el target/auxiliares
        feature_columns = [
            'rsi', 'macd', 'macd_signal', 'stoch_k', 'stoch_d', 'cci',
            'adx', 'plus_di', 'minus_di', 'atr', 'bb_upper', 'bb_lower'
        ]
        
        # Asegurarse de que todas las columnas de características existen y son numéricas
        for col in feature_columns:
            if col not in df_ml.columns:
                logger.warning(f"Columna de característica '{col}' no encontrada. Se omitirá.")
                # feature_columns.remove(col) # Do not remove, as it might break pipeline later if not handled
            else:
                df_ml[col] = pd.to_numeric(df_ml[col], errors='coerce').fillna(0) # Asegurar numérico y rellenar NaN

        # Filter feature_columns to only include those present in df_ml
        X = df_ml[feature_columns].copy() # Ensure X is a copy to avoid SettingWithCopyWarning
        y = df_ml['target']
        
        logger.info(f"Datos preparados. Filas para ML: {len(X)}. Clases del target: {y.value_counts()}")

        if len(X) == 0:
            logger.warning("No hay suficientes datos válidos para entrenar el modelo después de la preparación.")
            return

        # 4. Dividir datos en entrenamiento y prueba (temporalmente)
        # Usamos un split temporal simple para el conjunto de prueba final
        test_size_ratio = 0.2
        split_index = int(len(X) * (1 - test_size_ratio))
        X_train_full, X_test = X.iloc[:split_index], X.iloc[split_index:]
        y_train_full, y_test = y.iloc[:split_index], y.iloc[split_index:]
        logger.info(f"Datos divididos temporalmente. Entrenamiento completo: {len(X_train_full)} filas, Prueba: {len(X_test)} filas.")

        # 5. Crear Pipeline de preprocesamiento y modelo
        # El pipeline se encargará de escalar las características
        pipeline = Pipeline([
            ('scaler', StandardScaler()), # Escalar características
            ('model', LGBMClassifier(random_state=42, n_jobs=-1)) # Modelo LightGBM
        ])

        # 6. Entrenar el modelo con GridSearchCV y TimeSeriesSplit
        # Grid reducido para entrenamiento rápido
        param_grid = {
            'model__n_estimators': [100], # Solo un valor
            'model__learning_rate': [0.05],
            'model__num_leaves': [31],
            'model__max_depth': [5]
        }

        # Configurar TimeSeriesSplit para validación cruzada temporal
        # n_splits determina el número de splits de entrenamiento/prueba
        # max_train_size puede limitar el tamaño del conjunto de entrenamiento en cada split
        # test_size puede especificar el tamaño del conjunto de prueba en cada split
        tscv = TimeSeriesSplit(n_splits=3) # 3 splits para acelerar

        # Configurar GridSearchCV
        # Usamos 'f1_weighted' como scoring para manejar el posible desbalance de clases
        grid_search = GridSearchCV(estimator=pipeline, param_grid=param_grid, cv=tscv, scoring='f1_weighted', verbose=1, n_jobs=-1) # n_jobs=-1 para paralelizar
        
        logger.info("Iniciando GridSearchCV con TimeSeriesSplit para optimización de hiperparámetros...")
        grid_search.fit(X_train_full, y_train_full)

        model_pipeline = grid_search.best_estimator_
        logger.info(f"Mejores hiperparámetros encontrados: {grid_search.best_params_}")
        logger.info(f"Mejor F1-score (weighted) en validación cruzada temporal: {grid_search.best_score_:.4f}")

        # Log best hyperparameters to MLflow
        mlflow.log_params(grid_search.best_params_)
        mlflow.log_metric("cv_f1_weighted_score", grid_search.best_score_)

        logger.info("Modelo de LightGBM entrenado con los mejores hiperparámetros y pipeline de preprocesamiento.")

        # 7. Evaluar el modelo en el conjunto de prueba final
        y_pred = model_pipeline.predict(X_test)
        
        # Log classification report metrics to MLflow
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

        # 8. Guardar el modelo con versionado
        timestamp = datetime.now(zoneinfo.ZoneInfo("UTC")).strftime("%Y%m%d_%H%M%S")
        model_output_path_versioned = f"{model_base_output_path}_{timestamp}.pkl"
        os.makedirs(os.path.dirname(model_base_output_path), exist_ok=True)
        joblib.dump(model_pipeline, model_output_path_versioned)
        logger.info(f"Modelo guardado en {model_output_path_versioned}")

        # Opcional: Guardar el mejor modelo también en un nombre fijo para fácil carga
        joblib.dump(model_pipeline, f"{model_base_output_path}.pkl")
        logger.info(f"Copia del modelo más reciente guardada como {model_base_output_path}.pkl")

        # Log the model to MLflow
        mlflow.sklearn.log_model(sk_model=model_pipeline, artifact_path="model")


        # --- Validación y logging avanzado del modelo ML ---
        try:
            from utils.ml_model_utils import log_model_validation
            # Usar el mismo set de test para validación out-of-sample
            # Para calibración, usar una porción del train (ejemplo: 10% final del train)
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
            
            # Log advanced validation metrics to MLflow
            if validation_info and "metrics" in validation_info:
                mlflow.log_metrics({f"advanced_test_{k}": v for k, v in validation_info["metrics"].items() if v is not None})
            if validation_info and "calibration" in validation_info and validation_info["calibration"] and "metrics" in validation_info["calibration"]:
                mlflow.log_metrics({f"calibrated_test_{k}": v for k, v in validation_info["calibration"]["metrics"].items() if v is not None})

        except Exception as e:
            logger.error(f"Error en validación avanzada del modelo ML: {e}", exc_info=True)


async def train_and_notify(bot_instance, chat_id):
    """
    Función que envía notificaciones a través de Telegram antes, durante y después del entrenamiento del modelo ML.
    """
    # Notificar al usuario sobre el inicio del proceso
    await send_message(bot_instance, chat_id, "⚙️ El entrenamiento del modelo ML tomará aproximadamente 10 minutos. ¿Deseas continuar? (Responde 'sí' para proceder)")

    # Esperar confirmación del usuario
    confirmation = await await_confirmation(bot_instance, chat_id)
    if confirmation.lower() != 'sí':
        await send_message(bot_instance, chat_id, "❌ Entrenamiento cancelado por el usuario.")
        return

    # Iniciar el entrenamiento
    # await send_message(bot_instance, chat_id, "⏳ Iniciando el entrenamiento del modelo ML...")
    try:
        train_and_save_model()
        await send_message(bot_instance, chat_id, "✅ Entrenamiento completado exitosamente. El modelo ha sido guardado.")
    except Exception as e:
        await send_message(bot_instance, chat_id, f"❌ Error durante el entrenamiento del modelo ML: {e}")

if __name__ == "__main__":
    import config
    from aiogram import Bot

    bot = Bot(token=config.TELEGRAM_TOKEN)
    chat_id = config.TELEGRAM_CHAT_ID

    asyncio.run(train_and_notify(bot, chat_id))
