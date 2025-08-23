import json
import types
import pandas as pd

import pytest

from utils import message_queue
from utils import reporting_metrics


class DummyRedis:
    def __init__(self):
        self.storage = []

    def ping(self):
        return True

    def lpush(self, name, value):
        self.storage.append((name, value))

    def brpop(self, name, timeout=1):
        if self.storage:
            n, v = self.storage.pop()
            return (n, v)
        return None


def test_message_queue_publish_and_get(monkeypatch):
    dummy = DummyRedis()

    def fake_strict_redis(**kwargs):
        return dummy

    monkeypatch.setattr(message_queue, 'redis', types.SimpleNamespace(StrictRedis=lambda **k: dummy, exceptions=message_queue.redis.exceptions if hasattr(message_queue, 'redis') else __import__('redis').exceptions))
    # Force new singleton
    message_queue.MessageQueue._instance = None
    mq = message_queue.MessageQueue()
    ok = mq.publish_decision({"type": "TEST", "value": 1})
    assert ok is True
    got = mq.get_decision()
    assert got is not None


def test_generate_report_no_data(monkeypatch):
    # Monkeypatch fetch_operations_df to return empty DataFrame
    monkeypatch.setattr(reporting_metrics, 'fetch_operations_df', lambda start=None, end=None: pd.DataFrame())
    res = reporting_metrics.generate_report()
    assert "No hay operaciones" in res

def test_generate_report_with_data(monkeypatch):
    df = pd.DataFrame({
        'timestamp_open': ['2023-01-01', '2023-01-02'],
        'pnl_usdt': [10, -5],
        'pnl_percent': [1.0, -0.5]
    })
    monkeypatch.setattr(reporting_metrics, 'fetch_operations_df', lambda start=None, end=None: df)
    res = reporting_metrics.generate_report()
    assert 'Total de operaciones' in res
