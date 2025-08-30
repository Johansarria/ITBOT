import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np


def _read_recent_predictions(log_file: str, hours: int) -> List[Dict]:
    if not os.path.exists(log_file):
        return []
    cutoff = datetime.now() - timedelta(hours=hours)
    out: List[Dict] = []
    try:
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    ts = datetime.fromisoformat(entry.get("timestamp"))
                    if ts >= cutoff:
                        out.append(entry)
                except Exception:
                    continue
    except Exception:
        return []
    return out


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def get_dynamic_thresholds(settings) -> Dict[str, float]:
    """
    Calcula umbrales dinámicos a partir de la distribución reciente de probabilidades
    registradas por el modelo ML en logs/ml_predictions.jsonl.

    Política simple y robusta:
    - high = p90 de max_probability, acotado entre [HIGH_MIN, HIGH_MAX]
    - medium = p75 de max_probability, acotado entre [MEDIUM_MIN, MEDIUM_MAX]
    - low = valor fijo de settings.ML_THRESHOLD_LOW (o mínimo global)
    Fallback a umbrales de settings si no hay datos suficientes.
    """
    # Defaults/base
    base_high = getattr(settings, 'ML_THRESHOLD_HIGH', 0.80)
    base_med = getattr(settings, 'ML_THRESHOLD_MEDIUM', 0.65)
    base_low = getattr(settings, 'ML_THRESHOLD_LOW', 0.55)

    window_h = getattr(settings, 'ML_DYNAMIC_WINDOW_HOURS', 24)
    high_min = getattr(settings, 'ML_DYNAMIC_HIGH_MIN', base_high)
    high_max = getattr(settings, 'ML_DYNAMIC_HIGH_MAX', 0.90)
    med_min = getattr(settings, 'ML_DYNAMIC_MEDIUM_MIN', base_med)
    med_max = getattr(settings, 'ML_DYNAMIC_MEDIUM_MAX', base_high)

    log_file = os.path.join('logs', 'ml_predictions.jsonl')
    preds = _read_recent_predictions(log_file, window_h)

    # Requiere al menos 50 muestras para ser estable
    if len(preds) < 50:
        return {
            'high': base_high,
            'medium': base_med,
            'low': base_low,
        }

    max_probs = np.array([max(p.get('ml_buy_probability', 0.0), p.get('ml_sell_probability', 0.0)) for p in preds], dtype=float)
    # Evitar NaNs
    max_probs = max_probs[np.isfinite(max_probs)]
    if max_probs.size < 50:
        return {
            'high': base_high,
            'medium': base_med,
            'low': base_low,
        }

    p90 = float(np.quantile(max_probs, 0.90))
    p75 = float(np.quantile(max_probs, 0.75))

    high = _clamp(p90, high_min, high_max)
    medium = _clamp(p75, med_min, med_max)

    # Garantizar orden lógico y margen mínimo
    if medium > high - 0.02:
        medium = max(med_min, high - 0.02)

    return {
        'high': round(high, 3),
        'medium': round(medium, 3),
        'low': base_low,
    }
