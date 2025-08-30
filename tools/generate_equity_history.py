#!/usr/bin/env python3
"""
Genera logs/equity_history.csv a partir de operaciones cerradas en la base de datos.

Reglas:
- Usa close_timestamp cuando esté disponible; si no, timestamp.
- PnL USDT aproximado:
  LONG:  (close_price - price) * quantity
  SHORT: (price - close_price) * quantity
- Balance inicial configurable por ENV EQUITY_INITIAL_BALANCE (default 10000 USDT).

Uso:
  python tools/generate_equity_history.py
"""
import os
from datetime import datetime
import pandas as pd

from database.database_manager import get_db_session
from sqlalchemy import text


def compute_equity_df(initial_balance: float = 10000.0) -> pd.DataFrame:
    query = text(
        """
        SELECT 
          COALESCE(close_timestamp, timestamp) AS ts,
          price, close_price, side, quantity,
          status
        FROM operations
        WHERE close_timestamp IS NOT NULL
        ORDER BY ts ASC
        """
    )
    with get_db_session() as session:
        con = session.get_bind()
        df = pd.read_sql(query, con=con)
    if df.empty:
        return pd.DataFrame(columns=["timestamp", "equity"])  # vacío

    # Asegurar tipos numéricos
    for c in ["price", "close_price", "quantity"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["side"] = df["side"].astype(str)

    def pnl_row(r):
        if r["side"].upper().startswith("LONG"):
            return float((r["close_price"] - r["price"]) * r["quantity"])
        elif r["side"].upper().startswith("SHORT"):
            return float((r["price"] - r["close_price"]) * r["quantity"])
        return 0.0

    df["pnl_usdt"] = df.apply(pnl_row, axis=1)
    eq = []
    bal = float(initial_balance)
    for v in df["pnl_usdt"].tolist():
        bal += float(v)
        eq.append(bal)

    out = pd.DataFrame({
        "timestamp": pd.to_datetime(df["ts"]).dt.strftime("%Y-%m-%d %H:%M:%S"),
        "equity": eq
    })
    return out


def main():
    initial = float(os.getenv("EQUITY_INITIAL_BALANCE", "10000"))
    out_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "equity_history.csv")
    df = compute_equity_df(initial)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
