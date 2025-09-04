import os
import json
import shutil
from datetime import datetime, timedelta

import numpy as np

from utils.dynamic_thresholds import get_dynamic_thresholds


class _DummySettings:
    # Base thresholds
    ML_THRESHOLD_HIGH = 0.71
    ML_THRESHOLD_MEDIUM = 0.69
    ML_THRESHOLD_LOW = 0.55
    # Dynamic config
    ML_DYNAMIC_WINDOW_HOURS = 24
    ML_DYNAMIC_HIGH_MIN = 0.60
    ML_DYNAMIC_HIGH_MAX = 0.95
    ML_DYNAMIC_MEDIUM_MIN = 0.55
    ML_DYNAMIC_MEDIUM_MAX = 0.90


def _write_logs(entries):
    os.makedirs('logs', exist_ok=True)
    with open(os.path.join('logs', 'ml_predictions.jsonl'), 'w') as f:
        for e in entries:
            f.write(json.dumps(e) + '\n')


def _mk_entry(buy, sell, ts=None):
    return {
        'timestamp': (ts or datetime.now()).isoformat(),
        'ml_buy_probability': float(buy),
        'ml_sell_probability': float(sell),
    }


def test_dynamic_thresholds_fallback_when_no_file(tmp_path, monkeypatch):
    # Asegurar entorno limpio sin logs
    if os.path.exists('logs'):
        shutil.rmtree('logs')
    # Debe retornar los valores base
    s = _DummySettings()
    dyn = get_dynamic_thresholds(s)
    assert dyn['high'] == s.ML_THRESHOLD_HIGH
    assert dyn['medium'] == s.ML_THRESHOLD_MEDIUM
    assert dyn['low'] == s.ML_THRESHOLD_LOW


def test_dynamic_thresholds_fallback_when_insufficient_samples(tmp_path):
    # Escribir menos de 50 entradas
    entries = [_mk_entry(0.6, 0.4) for _ in range(10)]
    _write_logs(entries)
    s = _DummySettings()
    dyn = get_dynamic_thresholds(s)
    assert dyn['high'] == s.ML_THRESHOLD_HIGH
    assert dyn['medium'] == s.ML_THRESHOLD_MEDIUM
    assert dyn['low'] == s.ML_THRESHOLD_LOW


def test_dynamic_thresholds_quantiles_and_clamp(tmp_path):
    # Crear 100 entradas con distribución conocida en max(buy, sell)
    now = datetime.now()
    max_vals = np.concatenate([
        np.linspace(0.50, 0.80, 80),  # mayoría
        np.linspace(0.81, 0.95, 20),  # cola alta
    ])
    entries = []
    for i, v in enumerate(max_vals):
        # alternar canal de mayor probabilidad
        if i % 2 == 0:
            entries.append(_mk_entry(v, v - 0.1, ts=now - timedelta(minutes=i)))
        else:
            entries.append(_mk_entry(v - 0.1, v, ts=now - timedelta(minutes=i)))
    _write_logs(entries)

    s = _DummySettings()
    dyn = get_dynamic_thresholds(s)

    # p90 ~ alrededor del valor 90% de max_vals (~ entre 0.85-0.90)
    assert s.ML_DYNAMIC_HIGH_MIN <= dyn['high'] <= s.ML_DYNAMIC_HIGH_MAX
    assert s.ML_DYNAMIC_MEDIUM_MIN <= dyn['medium'] <= min(s.ML_DYNAMIC_MEDIUM_MAX, dyn['high'])
    # medium debe ser menor que high por al menos 0.02
    assert dyn['medium'] <= round(dyn['high'] - 0.02, 3)
    # low se mantiene igual al base
    assert dyn['low'] == s.ML_THRESHOLD_LOW


def test_dynamic_thresholds_old_entries_ignored(tmp_path):
    # Mezclar entradas antiguas (fuera de ventana) con recientes
    past = datetime.now() - timedelta(hours=48)
    recent = datetime.now() - timedelta(hours=1)
    entries = []
    # 60 antiguas altas
    for _ in range(60):
        entries.append(_mk_entry(0.95, 0.10, ts=past))
    # 60 recientes moderadas
    for _ in range(60):
        entries.append(_mk_entry(0.70, 0.10, ts=recent))
    _write_logs(entries)

    s = _DummySettings()
    dyn = get_dynamic_thresholds(s)
    # Debe reflejar recientes (~0.70 p75 y p90 cercano)
    assert dyn['high'] <= 0.90
    assert 0.65 <= dyn['medium'] <= dyn['high']
