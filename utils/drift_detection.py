"""
Herramientas para detección de drift y alertas de gobernanza de modelo.
"""
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
import logging

logger = logging.getLogger(__name__)

DRIFT_ALERT_THRESHOLD = 0.05  # p-valor para KS-test


def detect_feature_drift(ref_df: pd.DataFrame, new_df: pd.DataFrame, feature_cols=None, threshold=DRIFT_ALERT_THRESHOLD):
    """
    Compara la distribución de features entre dos dataframes y retorna features con drift significativo.
    """
    if feature_cols is None:
        feature_cols = [col for col in ref_df.columns if col in new_df.columns]
    drifted = []
    for col in feature_cols:
        ref, new = ref_df[col].dropna(), new_df[col].dropna()
        if len(ref) > 20 and len(new) > 20:
            stat, pval = ks_2samp(ref, new)
            if pval < threshold:
                drifted.append((col, pval))
    return drifted


def log_and_alert_drift(drifted, chat_id=None, bot_instance=None):
    if drifted:
        msg = f"⚠️ Drift detectado en features: {', '.join([f'{col} (p={pval:.3g})' for col, pval in drifted])}"
        logger.warning(msg)
        # Enviar alerta por Telegram si hay bot y chat
        if bot_instance and chat_id:
            import asyncio
            asyncio.create_task(bot_instance.send_message(chat_id, msg))
        # Si el drift es severo (ej: más de 1 feature clave), activar escudo
        if len(drifted) >= 2:
            logger.error("Drift severo: activando escudo de protección de capital.")
            # Aquí se puede llamar a la función de escudo global
            try:
                from utils.shield_manager import activar_escudo_drift
                activar_escudo_drift(reason=msg)
            except Exception as e:
                logger.error(f"Error al activar escudo por drift: {e}")
    else:
        logger.info("No se detectó drift significativo en features.")
