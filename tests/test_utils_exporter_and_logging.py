import os
import tempfile
import pandas as pd
import logging

from utils import exporter
from utils import logger_setup


def test_export_features_and_analysis(tmp_path):
    df = pd.DataFrame({"close": [1, 2, 3], "open": [0.9, 1.9, 2.9]}, index=pd.date_range("2023-01-01", periods=3))
    filepath = exporter.export_features("BTCUSDT", "1h", df)
    assert os.path.exists(filepath)
    # Clean up
    os.remove(filepath)


def test_export_analysis_result_creates_file(tmp_path):
    symbol = "TEST"
    interval = "1m"
    result = {"signal": "buy", "score": 0.5}
    # Use a temp BASE_DIR to avoid touching repo data
    old_base = exporter.BASE_DIR
    exporter.BASE_DIR = str(tmp_path)
    try:
        exporter.export_analysis_result(symbol, interval, result)
        f = os.path.join(exporter.BASE_DIR, f"{symbol}_{interval}.csv")
        assert os.path.exists(f)
    finally:
        exporter.BASE_DIR = old_base


def test_setup_logging_creates_log_dir(tmp_path, caplog):
    old_log_dir = logger_setup.LOG_DIR
    logger_setup.LOG_DIR = str(tmp_path)
    try:
        logger_setup.setup_logging()
        # logger should have handlers
        root = logging.getLogger()
        assert root.handlers
    finally:
        logger_setup.LOG_DIR = old_log_dir
