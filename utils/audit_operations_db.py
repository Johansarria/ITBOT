import os
import psycopg2
from psycopg2.extras import Json
from typing import Any, Dict
from datetime import datetime

DB_CONFIG = {
    "host": os.getenv("ITBOT_DB_HOST", "localhost"),
    "port": int(os.getenv("ITBOT_DB_PORT", 5432)),
    "user": os.getenv("ITBOT_DB_USER", "itbot"),
    "password": os.getenv("ITBOT_DB_PASSWORD", "itbot"),
    "dbname": os.getenv("ITBOT_DB_NAME", "itbot_audit")
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def ensure_operations_table():
    create_table_sql = '''
    CREATE TABLE IF NOT EXISTS audit_operations (
        id SERIAL PRIMARY KEY,
        operation_id UUID NOT NULL,
        timestamp_open TIMESTAMPTZ,
        timestamp_close TIMESTAMPTZ,
        symbol TEXT,
        side TEXT,
        entry_price NUMERIC,
        exit_price NUMERIC,
        take_profit NUMERIC,
        stop_loss NUMERIC,
        size_usdt NUMERIC,
        risk_percent NUMERIC,
        mode TEXT,
        pnl_usdt NUMERIC,
        pnl_percent NUMERIC,
        reason_open TEXT,
        reason_close TEXT,
        market_score_open NUMERIC,
        market_score_close NUMERIC,
        version_bot TEXT,
        notes TEXT,
        balance_usdt_al_abrir NUMERIC,
        escudo_activo_al_abrir TEXT,
        tipo_escudo_al_abrir TEXT,
        riesgo_forzado_al_abrir BOOLEAN,
        cantidad_token_operada NUMERIC,
        min_notional_filter NUMERIC,
        step_size_filter NUMERIC,
        price_tick_size_filter NUMERIC,
        slippage_apertura_pct NUMERIC,
        order_id_binance TEXT,
        order_status_binance TEXT
    );
    '''
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
        conn.commit()

def log_operation_to_db(data: Dict[str, Any]):
    ensure_operations_table()
    insert_sql = '''
    INSERT INTO audit_operations (
        operation_id, timestamp_open, timestamp_close, symbol, side, entry_price, exit_price, take_profit, stop_loss,
        size_usdt, risk_percent, mode, pnl_usdt, pnl_percent, reason_open, reason_close, market_score_open, market_score_close,
        version_bot, notes, balance_usdt_al_abrir, escudo_activo_al_abrir, tipo_escudo_al_abrir, riesgo_forzado_al_abrir,
        cantidad_token_operada, min_notional_filter, step_size_filter, price_tick_size_filter, slippage_apertura_pct,
        order_id_binance, order_status_binance
    ) VALUES (
        %(operation_id)s, %(timestamp_open)s, %(timestamp_close)s, %(symbol)s, %(side)s, %(entry_price)s, %(exit_price)s, %(take_profit)s, %(stop_loss)s,
        %(size_usdt)s, %(risk_percent)s, %(mode)s, %(pnl_usdt)s, %(pnl_percent)s, %(reason_open)s, %(reason_close)s, %(market_score_open)s, %(market_score_close)s,
        %(version_bot)s, %(notes)s, %(balance_usdt_al_abrir)s, %(escudo_activo_al_abrir)s, %(tipo_escudo_al_abrir)s, %(riesgo_forzado_al_abrir)s,
        %(cantidad_token_operada)s, %(min_notional_filter)s, %(step_size_filter)s, %(price_tick_size_filter)s, %(slippage_apertura_pct)s,
        %(order_id_binance)s, %(order_status_binance)s
    );
    '''
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(insert_sql, data)
        conn.commit()
