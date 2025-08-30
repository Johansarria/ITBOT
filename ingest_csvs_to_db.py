import argparse
import logging
import os
from typing import List

import pandas as pd

from database.database_manager import add_klines, init_db


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("ingest_csvs_to_db")


def find_csv_path(symbol: str, interval: str) -> str:
    """Return expected CSV path for a given symbol/interval."""
    return os.path.join(
        "data",
        "analisis",
        f"historical_klines_{symbol}_{interval}_1_Jan_2022_now.csv",
    )


def load_csv(symbol: str, interval: str) -> pd.DataFrame:
    """
    Load klines CSV into a DataFrame with the required columns and dtypes.
    Expected columns: timestamp, open, high, low, close, volume, close_time
    """
    csv_path = find_csv_path(symbol, interval)
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV no encontrado: {csv_path}")

    logger.info(f"Leyendo CSV: {csv_path}")
    df = pd.read_csv(csv_path)

    required = ["timestamp", "open", "high", "low", "close", "volume", "close_time"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV {csv_path} no tiene columnas requeridas: {missing}")

    # Parse timestamp with mixed formats safely
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()

    # Ensure numeric types
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["close_time"] = pd.to_numeric(df["close_time"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["open", "high", "low", "close", "volume", "close_time"]).copy()

    # Sort by time ascending and set index for add_klines compatibility
    df = df.sort_values("timestamp")
    df = df.set_index("timestamp")

    # Keep only required columns in order
    df = df[["open", "high", "low", "close", "volume", "close_time"]]
    logger.info(
        f"CSV listo para {symbol}-{interval}. Filas: {len(df)} | Rango: {df.index.min()} -> {df.index.max()}"
    )
    return df


def ingest_symbol(symbol: str, interval: str, chunk_size: int = 5000):
    """Ingest one symbol's CSV into DB in chunks to avoid large payloads."""
    df = load_csv(symbol, interval)
    total = len(df)
    if total == 0:
        logger.warning(f"Sin filas para {symbol}-{interval}")
        return

    logger.info(f"Iniciando ingesta para {symbol}-{interval}: {total} filas")
    start = 0
    processed = 0
    while start < total:
        end = min(start + chunk_size, total)
        batch = df.iloc[start:end]
        add_klines(batch, symbol, interval)
        processed += len(batch)
        logger.info(f"Progreso {symbol}-{interval}: {processed}/{total}")
        start = end

    logger.info(f"Ingesta completada para {symbol}-{interval}: {processed} filas")


def parse_args():
    parser = argparse.ArgumentParser(description="Ingesta de klines desde CSV a la BD")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT", "TRXUSDT", "XRPUSDT"],
        help="Lista de símbolos a ingerir",
    )
    parser.add_argument(
        "--interval",
        default="1h",
        help="Intervalo de klines (por defecto 1h)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=5000,
        help="Tamaño del lote para inserciones por lotes",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Asegurar conexión y tablas
    init_db()

    for sym in args.symbols:
        try:
            ingest_symbol(sym, args.interval, args.chunk_size)
        except FileNotFoundError as e:
            logger.warning(str(e))
        except Exception as e:
            logger.exception(f"Error ingiriendo {sym}-{args.interval}: {e}")


if __name__ == "__main__":
    main()
