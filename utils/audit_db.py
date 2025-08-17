import os
import json
import psycopg2
from psycopg2.extras import Json
from typing import Any, Dict

DB_CONFIG = {
    "host": os.getenv("ITBOT_DB_HOST", "localhost"),
    "port": int(os.getenv("ITBOT_DB_PORT", 5432)),
    "user": os.getenv("ITBOT_DB_USER", "itbot"),
    "password": os.getenv("ITBOT_DB_PASSWORD", "itbot"),
    "dbname": os.getenv("ITBOT_DB_NAME", "itbot_audit")
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_audit_table():
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS audit_decisions (
        id SERIAL PRIMARY KEY,
        trade_id UUID NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        symbol TEXT,
        type TEXT,
        side TEXT,
        quantity NUMERIC,
        strategy_id TEXT,
        timestamp_decision TIMESTAMPTZ,
        features JSONB,
        score NUMERIC,
        thresholds JSONB,
        reason TEXT,
        model_version TEXT,
        result TEXT,
        error TEXT
    );
    '''
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
        conn.commit()

def log_decision_to_db(data: Dict[str, Any]):
    ensure_audit_table()
    insert_sql = '''
    INSERT INTO audit_decisions (
        trade_id, symbol, type, side, quantity, strategy_id, timestamp_decision,
        features, score, thresholds, reason, model_version, result, error
    ) VALUES (
        %(trade_id)s, %(symbol)s, %(type)s, %(side)s, %(quantity)s, %(strategy_id)s, %(timestamp_decision)s,
        %(features)s, %(score)s, %(thresholds)s, %(reason)s, %(model_version)s, %(result)s, %(error)s
    );
    '''
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(insert_sql, {
                "trade_id": data.get("trade_id"),
                "symbol": data.get("symbol"),
                "type": data.get("type"),
                "side": data.get("side"),
                "quantity": data.get("quantity"),
                "strategy_id": data.get("strategy_id"),
                "timestamp_decision": data.get("timestamp_decision"),
                "features": Json(data.get("features", {})),
                "score": data.get("score"),
                "thresholds": Json(data.get("thresholds", {})),
                "reason": data.get("reason"),
                "model_version": data.get("model_version"),
                "result": data.get("result"),
                "error": data.get("error")
            })
        conn.commit()
