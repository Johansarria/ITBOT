import os
import tempfile
import pandas as pd
import numpy as np
import types
import time

from utils import exporter
from utils import message_queue
from utils import ml_model_utils


def test_generate_analysis_chart_empty():
    df = pd.DataFrame()
    res = exporter.generate_analysis_chart(df, "BTCUSDT", "1h", "empty_chart.png")
    assert res is None


def test_generate_analysis_chart_creates_file(tmp_path):
    # Create a longer DataFrame so indicators can compute
    idx = pd.date_range("2025-01-01", periods=30, freq="h")
    df = pd.DataFrame({"close": np.linspace(100, 200, len(idx))}, index=idx)
    old_chart_dir = exporter.CHART_DIR
    exporter.CHART_DIR = str(tmp_path)
    try:
        out = exporter.generate_analysis_chart(df, "BTCUSDT", "1h", "chart.png")
        assert out is not None and os.path.exists(out)
    finally:
        exporter.CHART_DIR = old_chart_dir


def test_message_queue_connection_failure(monkeypatch):
    # Force redis.StrictRedis to raise ConnectionError every attempt
    import redis

    def raise_conn(**kwargs):
        raise redis.exceptions.ConnectionError("fail")

    # Make retries minimal and avoid sleeping to keep the test fast
    monkeypatch.setattr(message_queue, 'MAX_RETRIES', 1)
    monkeypatch.setattr(message_queue, 'RETRY_DELAY_SECONDS', 0)
    monkeypatch.setattr(message_queue, 'redis', types.SimpleNamespace(StrictRedis=raise_conn, exceptions=redis.exceptions))
    # Avoid actual sleep
    monkeypatch.setattr(message_queue, 'time', types.SimpleNamespace(sleep=lambda s: None))

    # Reset singleton and instantiate
    message_queue.MessageQueue._instance = None
    mq = message_queue.MessageQueue()
    # When redis client is None after retries, publish_decision should return False
    assert mq.redis_client is None
    ok = mq.publish_decision({"type": "X"})
    assert ok is False


def test_calibrate_model_auto_choice():
    # Use a simple sklearn estimator to exercise calibration
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    X = np.vstack([np.random.normal(0, 1, (50, 2)), np.random.normal(3, 1, (50, 2))])
    y = np.array([0] * 50 + [1] * 50)
    clf = LogisticRegression()
    clf.fit(X, y)

    # calibration data
    X_calib = X[:20]
    y_calib = y[:20]

    calibrated = ml_model_utils.calibrate_model(clf, X_calib, y_calib, method="auto")
    assert calibrated is not None
    # calibrated should implement predict_proba
    assert hasattr(calibrated, 'predict_proba')
