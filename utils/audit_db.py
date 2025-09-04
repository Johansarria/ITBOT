import os
import json
import psycopg2
from psycopg2.extras import Json
from typing import Any, Dict


def _build_db_config() -> Dict[str, Any]:
    """Construye la configuración de DB a partir de env vars.
    Prioriza DATABASE_URL y POSTGRES_*, con fallback a ITBOT_DB_*.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # psycopg2 soporta directamente la URL
        return {"dsn": database_url}

    # Preferir variables estándar de docker-compose
    host = os.getenv("POSTGRES_HOST") or os.getenv("ITBOT_DB_HOST") or "localhost"
    port = int(os.getenv("POSTGRES_PORT") or os.getenv("ITBOT_DB_PORT") or 5432)
    user = os.getenv("POSTGRES_USER") or os.getenv("ITBOT_DB_USER") or "itbot"
    password = os.getenv("POSTGRES_PASSWORD") or os.getenv("ITBOT_DB_PASSWORD") or "itbot"
    dbname = os.getenv("POSTGRES_DB") or os.getenv("ITBOT_DB_NAME") or "itbot_audit"

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "dbname": dbname,
    }


def get_db_connection():
    cfg = _build_db_config()
    # Si viene como DSN usar esa firma, de lo contrario kwargs
    if "dsn" in cfg:
        return psycopg2.connect(cfg["dsn"])  # type: ignore[arg-type]
    return psycopg2.connect(**cfg)

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
