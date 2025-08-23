import types
import pytest

from utils import audit_db, audit_operations_db


class FakeCursor:
    def __init__(self, store):
        self.store = store

    def execute(self, sql, params=None):
        self.store.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, store):
        self.store = store

    def cursor(self):
        return FakeCursor(self.store)

    def commit(self):
        self.store.append(('COMMIT', None))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ensure_audit_table_executes_create(monkeypatch):
    store = []
    fake_conn = FakeConnection(store)
    monkeypatch.setattr(audit_db, 'get_db_connection', lambda: fake_conn)
    audit_db.ensure_audit_table()
    # Look for CREATE TABLE in executed SQL
    assert any('CREATE TABLE IF NOT EXISTS audit_decisions' in (sql if isinstance(sql, str) else '') for sql, _ in store)


def test_log_decision_to_db_inserts(monkeypatch):
    store = []
    fake_conn = FakeConnection(store)
    monkeypatch.setattr(audit_db, 'get_db_connection', lambda: fake_conn)
    # Monkeypatch ensure_audit_table to avoid double CREATE
    monkeypatch.setattr(audit_db, 'ensure_audit_table', lambda: None)
    data = {"trade_id": 't1', "symbol": 'BTC', "type": 'test', "score": 0.5}
    audit_db.log_decision_to_db(data)
    # Last non-commit call should be the INSERT
    inserts = [sql for sql, params in store if isinstance(sql, str) and sql.strip().upper().startswith('INSERT')]
    assert inserts, f'No INSERT found in store: {store}'


def test_ensure_operations_table_and_log(monkeypatch):
    store = []
    fake_conn = FakeConnection(store)
    monkeypatch.setattr(audit_operations_db, 'get_db_connection', lambda: fake_conn)
    audit_operations_db.ensure_operations_table()
    assert any('CREATE TABLE IF NOT EXISTS audit_operations' in (sql if isinstance(sql, str) else '') for sql, _ in store)

    # Now test insert
    store.clear()
    monkeypatch.setattr(audit_operations_db, 'ensure_operations_table', lambda: None)
    sample = {"operation_id": 'o1', "symbol": 'BTC', "pnl_usdt": 5.0}
    audit_operations_db.log_operation_to_db(sample)
    inserts = [sql for sql, params in store if isinstance(sql, str) and sql.strip().upper().startswith('INSERT')]
    assert inserts
