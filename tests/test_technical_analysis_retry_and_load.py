import asyncio
import joblib
import types
import os
import importlib
import pytest

from utils import technical_analysis as ta


def test_load_ml_model_file_not_found(monkeypatch, tmp_path):
    # Point MODEL_PATH to a non-existing file
    old_path = ta.MODEL_PATH
    ta.MODEL_PATH = str(tmp_path / "no_model.pkl")
    try:
        ta.ml_model = None
        ta.load_ml_model()
        assert ta.ml_model is None
    finally:
        ta.MODEL_PATH = old_path


def test_retry_decorator_runs_and_retries(monkeypatch):
    calls = {'count': 0}

    async def flaky(x):
        calls['count'] += 1
        if calls['count'] < 3:
            raise ValueError('no')
        return 'ok'

    wrapped = ta.retry((ValueError,), tries=4, delay=0, backoff=1, logger=None)(flaky)

    res = asyncio.run(wrapped(1))
    assert res == 'ok'
