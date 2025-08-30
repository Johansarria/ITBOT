import matplotlib.pyplot as plt
import pandas as pd
from utils.reporting_metrics import fetch_operations_df
from typing import Optional

def plot_equity_curve(start: Optional[str] = None, end: Optional[str] = None, save_path: Optional[str] = None):
    df = fetch_operations_df(start, end)
    if df.empty:
        print("No hay operaciones para graficar.")
        return None
    df = df.sort_values("timestamp_open")
    df["pnl_usdt"] = pd.to_numeric(df["pnl_usdt"], errors="coerce").fillna(0)
    df["equity"] = df["pnl_usdt"].cumsum()
    plt.figure(figsize=(10, 5))
    plt.plot(df["timestamp_open"], df["equity"], label="Equity Curve", color="blue")
    plt.xlabel("Fecha")
    plt.ylabel("Equity (USDT)")
    plt.title("Evolución de Equity (Paper Trading)")
    plt.legend()
    plt.grid(True)
    if save_path:
        plt.savefig(save_path)
    plt.close()  # Evita UserWarning en backend non-interactive
    return df

def plot_pnl_histogram(start: Optional[str] = None, end: Optional[str] = None, save_path: Optional[str] = None):
    df = fetch_operations_df(start, end)
    if df.empty:
        print("No hay operaciones para graficar.")
        return None
    df["pnl_usdt"] = pd.to_numeric(df["pnl_usdt"], errors="coerce").fillna(0)
    plt.figure(figsize=(8, 4))
    plt.hist(df["pnl_usdt"], bins=20, color="green", alpha=0.7)
    plt.xlabel("P&L por operación (USDT)")
    plt.ylabel("Frecuencia")
    plt.title("Distribución de P&L por operación")
    plt.grid(True)
    if save_path:
        plt.savefig(save_path)
    plt.close()  # Evita UserWarning en backend non-interactive
    return df
