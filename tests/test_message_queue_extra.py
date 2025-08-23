import types
import json
import pytest

from utils import message_queue


def test_publish_returns_false_when_no_redis(monkeypatch):
    # Force the singleton to have no redis client
    message_queue.MessageQueue._instance = None
    mq = message_queue.MessageQueue()
    mq.redis_client = None
    assert mq.publish_decision({"x": 1}) is False


def test_get_decision_handles_exception(monkeypatch):
    class BadRedis:
        def brpop(self, name, timeout=1):
            raise Exception('boom')

    # Create instance and inject bad redis
    message_queue.MessageQueue._instance = None
    mq = message_queue.MessageQueue()
    mq.redis_client = BadRedis()
    res = mq.get_decision()
    assert res is None


def test_publish_and_get_roundtrip(monkeypatch):
    storage = []

    class FakeRedis:
        def __init__(self):
            pass

        def lpush(self, name, value):
            storage.append((name, value))

        def brpop(self, name, timeout=1):
            if storage:
                return storage.pop()
            return None

    message_queue.MessageQueue._instance = None
    mq = message_queue.MessageQueue()
    mq.redis_client = FakeRedis()
    ok = mq.publish_decision({"type": "T", "v": 1})
    assert ok is True
    got = mq.get_decision()
    assert isinstance(got, dict)
