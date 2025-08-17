# database/database_manager.py
import sqlite3
import logging
import os
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Configuración de la Base de Datos ---
DB_DIR = "storage"
DB_NAME = "itbot.db"
DB_PATH = os.path.join(DB_DIR, DB_NAME)

# --- Funciones de Inicialización ---

def init_db():
    """
    Inicializa la base de datos y crea las tablas si no existen.
    Esta función está diseñada para ser llamada una sola vez al iniciar el bot.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Crear tabla de operaciones
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    decision TEXT,
                    escudo TEXT,
                    riesgo_forzado_activo INTEGER,
                    ganancia_pct_operacion REAL,
                    close_price REAL,
                    close_timestamp TEXT,
                    close_reason TEXT
                )
            """)
            
            # Crear tabla de klines
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS klines (
                    timestamp INTEGER NOT NULL, -- Unix timestamp in milliseconds
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    close_time INTEGER NOT NULL,
                    PRIMARY KEY (timestamp, symbol, interval)
                )
            """)
            
            # Crear tabla de señales descartadas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discarded_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    score REAL,
                    features TEXT -- JSON string con features relevantes
                )
            ''')

            logger.info(f"Base de datos inicializada en {DB_PATH}. Tablas 'operations', 'klines' y 'discarded_signals' listas.")
            conn.commit()
            
    except sqlite3.Error as e:
        logger.error(f"Error al inicializar la base de datos: {e}", exc_info=True)
        raise

# --- Funciones de Interacción con la Base de Datos ---

def add_operation(op_data: Dict[str, Any]):
    """
    Añade una nueva operación a la base de datos.
    """
    query = """
        INSERT INTO operations (
            operation_id, timestamp, symbol, side, price, quantity, status, mode, 
            decision, escudo, riesgo_forzado_activo, ganancia_pct_operacion,
            close_price, close_timestamp, close_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (
        op_data.get('operation_id'), op_data.get('timestamp'), op_data.get('symbol'),
        op_data.get('side'), op_data.get('price'), op_data.get('quantity'),
        op_data.get('status'), op_data.get('mode'), op_data.get('decision'),
        op_data.get('escudo'), op_data.get('riesgo_forzado_activo'), 
        op_data.get('ganancia_pct_operacion'), op_data.get('close_price'),
        op_data.get('close_timestamp'), op_data.get('close_reason')
    )
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
        logger.info(f"Operación {op_data.get('operation_id')} añadida a la base de datos.")
    except sqlite3.Error as e:
        logger.error(f"Error al añadir operación a la BD: {e}", exc_info=True)
        raise

def get_open_positions_df() -> pd.DataFrame:
    """
    Obtiene todas las posiciones con estado 'OPEN' o similar desde la BD.
    """
    query = "SELECT * FROM operations WHERE status = 'OPEN'"
    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query(query, conn)
            return df
    except sqlite3.Error as e:
        logger.error(f"Error al obtener posiciones abiertas desde la BD: {e}", exc_info=True)
        return pd.DataFrame()

def update_position_status(operation_id: str, new_status: str, close_price: float, close_timestamp: str, reason: str):
    """
    Actualiza el estado, precio y motivo de cierre de una operación.
    """
    query = """
        UPDATE operations 
        SET status = ?, close_price = ?, close_timestamp = ?, close_reason = ?
        WHERE operation_id = ?
    """
    params = (new_status, close_price, close_timestamp, reason, operation_id)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
        logger.info(f"Posición {operation_id} actualizada en la BD a {new_status}.")
    except sqlite3.Error as e:
        logger.error(f"Error al actualizar posición en la BD: {e}", exc_info=True)
        raise

def add_klines(klines_df: pd.DataFrame, symbol: str, interval: str):
    """
    Añade datos de klines a la base de datos.
    Asume que klines_df tiene las columnas: timestamp (ms), open, high, low, close, volume, close_time (ms).
    """
    query = """
        INSERT OR IGNORE INTO klines (
            timestamp, symbol, interval, open, high, low, close, volume, close_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    data_to_insert = []
    for _, row in klines_df.iterrows():
        data_to_insert.append((
            row["timestamp"],
            symbol,
            interval,
            row["open"],
            row["high"],
            row["low"],
            row["close"],
            row["volume"],
            row["close_time"]
        ))
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.executemany(query, data_to_insert)
            conn.commit()
        logger.info(f"Añadidos {len(data_to_insert)} klines para {symbol}-{interval} a la base de datos.")
    except sqlite3.Error as e:
        logger.error(f"Error al añadir klines a la BD: {e}", exc_info=True)
        raise

def get_klines(symbol: str, interval: str, start_time: Optional[int] = None, end_time: Optional[int] = None) -> pd.DataFrame:
    """
    Obtiene datos de klines desde la base de datos.
    start_time y end_time deben ser timestamps Unix en milisegundos.
    """
    query = "SELECT timestamp, open, high, low, close, volume, close_time FROM klines WHERE symbol = ? AND interval = ?"
    params = [symbol, interval]
    if start_time:
        query += " AND timestamp >= ?"
        params.append(start_time)
    if end_time:
        query += " AND timestamp <= ?"
        params.append(end_time)
    query += " ORDER BY timestamp ASC"

    try:
        with sqlite3.connect(DB_PATH) as conn:
            df = pd.read_sql_query(query, conn, params=params)
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                # Asegurarse de que las columnas numéricas sean del tipo correcto
                numeric_cols = ["open", "high", "low", "close", "volume"]
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            return df
    except sqlite3.Error as e:
        logger.error(f"Error al obtener klines desde la BD: {e}", exc_info=True)
        return pd.DataFrame()

# --- Tabla y función para señales descartadas ---
def init_discarded_signals_table():
    """
    Crea la tabla discarded_signals si no existe.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discarded_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    interval TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    score REAL,
                    features TEXT -- JSON string con features relevantes
                )
            ''')
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error al crear tabla discarded_signals: {e}", exc_info=True)
        raise

def save_discarded_signal(signal: dict):
    """
    Persiste una señal descartada en la base de datos para entrenamiento futuro.
    El campo 'features' debe ser un JSON serializado.
    """
    import json
    os.makedirs(DB_DIR, exist_ok=True)
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO discarded_signals (timestamp, strategy, symbol, interval, decision, score, features)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal.get('timestamp'),
                signal.get('strategy'),
                signal.get('symbol'),
                signal.get('interval'),
                signal.get('decision'),
                signal.get('score'),
                json.dumps(signal.get('features', {}))
            ))
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error al guardar señal descartada: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    # Este bloque permite inicializar la BD manualmente si es necesario.
    print("Inicializando la base de datos...")
    init_db()
    print("Base de datos lista.")
