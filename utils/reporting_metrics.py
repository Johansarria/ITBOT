import pandas as pd
import psycopg2
import os
from typing import Optional

DB_CONFIG = {
    "host": os.getenv("ITBOT_DB_HOST", "localhost"),
    "port": int(os.getenv("ITBOT_DB_PORT", 5432)),
    "user": os.getenv("ITBOT_DB_USER", "itbot"),
    "password": os.getenv("ITBOT_DB_PASSWORD", "itbot"),
    "dbname": os.getenv("ITBOT_DB_NAME", "itbot_audit")
}

def fetch_operations_df(start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
    query = "SELECT * FROM audit_operations"
    params = []
    if start and end:
        query += " WHERE timestamp_open >= %s AND timestamp_open <= %s"
        params = [start, end]
    elif start:
        query += " WHERE timestamp_open >= %s"
        params = [start]
    elif end:
        query += " WHERE timestamp_open <= %s"
        params = [end]
    with psycopg2.connect(**DB_CONFIG) as conn:
        df = pd.read_sql(query, conn, params=params)
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
