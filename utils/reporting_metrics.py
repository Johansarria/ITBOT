import pandas as pd
import psycopg2
from sqlalchemy import create_engine
import os
from typing import Optional, Dict, Any, Sequence


def _build_db_config() -> Dict[str, Any]:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}
    host = os.getenv("POSTGRES_HOST") or os.getenv("ITBOT_DB_HOST") or "localhost"
    port = int(os.getenv("POSTGRES_PORT") or os.getenv("ITBOT_DB_PORT") or 5432)
    user = os.getenv("POSTGRES_USER") or os.getenv("ITBOT_DB_USER") or "itbot"
    password = os.getenv("POSTGRES_PASSWORD") or os.getenv("ITBOT_DB_PASSWORD") or "itbot"
    dbname = os.getenv("POSTGRES_DB") or os.getenv("ITBOT_DB_NAME") or "itbot_audit"
    return {"host": host, "port": port, "user": user, "password": password, "dbname": dbname}

def _connect():
    cfg = _build_db_config()
    if "dsn" in cfg:
        return psycopg2.connect(cfg["dsn"])  # type: ignore[arg-type]
    return psycopg2.connect(**cfg)


def _sqlalchemy_url() -> str:
    cfg = _build_db_config()
    if "dsn" in cfg:
        return cfg["dsn"]  # type: ignore[index]
    # Build postgres URL
    host = cfg["host"]
    port = cfg["port"]
    user = cfg["user"]
    password = cfg["password"]
    dbname = cfg["dbname"]
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


def fetch_operations_df(start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
    query = "SELECT * FROM audit_operations"
    params: Sequence[object] | None = None
    if start and end:
        query += " WHERE timestamp_open >= %s AND timestamp_open <= %s"
        params = (start, end)
    elif start:
        query += " WHERE timestamp_open >= %s"
        params = (start,)
    elif end:
        query += " WHERE timestamp_open <= %s"
        params = (end,)
    engine = create_engine(_sqlalchemy_url())
    with engine.connect() as conn:
        df = pd.read_sql_query(sql=query, con=conn, params=params)
    return df

def generate_report(start: Optional[str] = None, end: Optional[str] = None) -> str:
    df = fetch_operations_df(start, end)
    if df.empty:
        return "No hay operaciones en el rango seleccionado."
    df["pnl_usdt"] = pd.to_numeric(df["pnl_usdt"], errors="coerce")
    df["pnl_percent"] = pd.to_numeric(df["pnl_percent"], errors="coerce")
    total_trades = len(df)
    total_pnl = df["pnl_usdt"].sum(skipna=True)
    avg_pnl = df["pnl_usdt"].mean(skipna=True)
    win_trades = (df["pnl_usdt"] > 0).sum()
    loss_trades = (df["pnl_usdt"] < 0).sum()
    winrate = win_trades / total_trades * 100 if total_trades else 0
    max_drawdown = (df["pnl_usdt"].cumsum().cummax() - df["pnl_usdt"].cumsum()).max()
    report = f"""
Resumen de Operaciones ({start or 'inicio'} a {end or 'fin'}):
- Total de operaciones: {total_trades}
- P&L total: {total_pnl:.2f} USDT
- P&L promedio: {avg_pnl:.2f} USDT
- Winrate: {winrate:.1f}%
- Máximo drawdown: {max_drawdown:.2f} USDT
- Operaciones ganadoras: {win_trades}
- Operaciones perdedoras: {loss_trades}
"""
    return report
