# database/database_manager.py
import logging
import os
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import config # Import the config module

logger = logging.getLogger(__name__)

# Database engine and session setup
engine = None
SessionLocal = None

def get_db_session():
    """
    Returns a new SQLAlchemy session.
    """
    if SessionLocal is None:
        raise Exception("Database engine not initialized. Call init_db() first.")
    return SessionLocal()

def init_db():
    """
    Initializes the database engine and creates tables if they don't exist.
    This function should be called once at bot startup.
    """
    global engine, SessionLocal

    # Ensure config is loaded
    config.load_configurations()

    if config.DATABASE_URL is None:
        raise ValueError("DATABASE_URL is not set in config.py. Check environment variables.")

    try:
        engine = create_engine(config.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Test connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info(f"Conexión a la base de datos establecida: {config.DATABASE_URL}")

        # Create tables
        create_tables()

    except SQLAlchemyError as e:
        logger.error(f"Error al inicializar la base de datos: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error inesperado al inicializar la base de datos: {e}", exc_info=True)
        raise

def create_tables():
    """
    Creates database tables if they don't exist, adapting for PostgreSQL.
    """
    # Use a session to execute DDL
    with get_db_session() as session:
        try:
            inspector = inspect(engine)

            # Operations table
            if not inspector.has_table("operations"):
                session.execute(text("""
                    CREATE TABLE operations (
                        operation_id VARCHAR(255) PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        symbol VARCHAR(255) NOT NULL,
                        side VARCHAR(255) NOT NULL,
                        price NUMERIC NOT NULL,
                        quantity NUMERIC NOT NULL,
                        status VARCHAR(255) NOT NULL,
                        mode VARCHAR(255) NOT NULL,
                        decision VARCHAR(255),
                        escudo VARCHAR(255),
                        riesgo_forzado_activo BOOLEAN,
                        ganancia_pct_operacion NUMERIC,
                        close_price NUMERIC,
                        close_timestamp TIMESTAMP,
                        close_reason VARCHAR(255)
                    )
                """))
                logger.info("Tabla 'operations' creada.")
            else:
                logger.info("Tabla 'operations' ya existe.")

            # Klines table
            if not inspector.has_table("klines"):
                session.execute(text("""
                    CREATE TABLE klines (
                        timestamp BIGINT NOT NULL, -- Unix timestamp in milliseconds
                        symbol VARCHAR(255) NOT NULL,
                        interval VARCHAR(255) NOT NULL,
                        open NUMERIC NOT NULL,
                        high NUMERIC NOT NULL,
                        low NUMERIC NOT NULL,
                        close NUMERIC NOT NULL,
                        volume NUMERIC NOT NULL,
                        close_time BIGINT NOT NULL,
                        PRIMARY KEY (timestamp, symbol, interval)
                    )
                """))
                logger.info("Tabla 'klines' creada.")
            else:
                logger.info("Tabla 'klines' ya existe.")

            # Discarded signals table
            if not inspector.has_table("discarded_signals"):
                session.execute(text("""
                    CREATE TABLE discarded_signals (
                        id SERIAL PRIMARY KEY, -- SERIAL for auto-incrementing integer in PostgreSQL
                        timestamp TIMESTAMP NOT NULL,
                        strategy VARCHAR(255) NOT NULL,
                        symbol VARCHAR(255) NOT NULL,
                        interval VARCHAR(255) NOT NULL,
                        decision VARCHAR(255) NOT NULL,
                        score NUMERIC,
                        features TEXT -- JSON string con features relevantes
                    )
                """))
                logger.info("Tabla 'discarded_signals' creada.")
            else:
                logger.info("Tabla 'discarded_signals' ya existe.")

            session.commit()
            logger.info("Tablas de base de datos verificadas/creadas.")

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error al crear tablas: {e}", exc_info=True)
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Error inesperado al crear tablas: {e}", exc_info=True)
            raise

# --- Funciones de Interacción con la Base de Datos ---

def add_operation(op_data: Dict[str, Any]):
    """
    Añade una nueva operación a la base de datos.
    """
    query = text("""
        INSERT INTO operations (
            operation_id, timestamp, symbol, side, price, quantity, status, mode,
            decision, escudo, riesgo_forzado_activo, ganancia_pct_operacion,
            close_price, close_timestamp, close_reason
        ) VALUES (
            :operation_id, :timestamp, :symbol, :side, :price, :quantity, :status, :mode,
            :decision, :escudo, :riesgo_forzado_activo, :ganancia_pct_operacion,
            :close_price, :close_timestamp, :close_reason
        )
    """)
    params = {
        'operation_id': op_data.get('operation_id'),
        'timestamp': op_data.get('timestamp'),
        'symbol': op_data.get('symbol'),
        'side': op_data.get('side'),
        'price': op_data.get('price'),
        'quantity': op_data.get('quantity'),
        'status': op_data.get('status'),
        'mode': op_data.get('mode'),
        'decision': op_data.get('decision'),
        'escudo': op_data.get('escudo'),
        'riesgo_forzado_activo': op_data.get('riesgo_forzado_activo'),
        'ganancia_pct_operacion': op_data.get('ganancia_pct_operacion'),
        'close_price': op_data.get('close_price'),
        'close_timestamp': op_data.get('close_timestamp'),
        'close_reason': op_data.get('close_reason')
    }
    try:
        with get_db_session() as session:
            session.execute(query, params)
            session.commit()
        logger.info(f"Operación {op_data.get('operation_id')} añadida a la base de datos.")
    except SQLAlchemyError as e:
        logger.error(f"Error al añadir operación a la BD: {e}", exc_info=True)
        raise

def get_open_positions_df() -> pd.DataFrame:
    """
    Obtiene todas las posiciones con estado 'OPEN' o similar desde la BD.
    """
    query = text("SELECT * FROM operations WHERE status = 'OPEN'")
    try:
        with get_db_session() as session:
            # Use pandas.read_sql with SQLAlchemy connection
            df = pd.read_sql(query, session.bind)
            return df
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener posiciones abiertas desde la BD: {e}", exc_info=True)
        return pd.DataFrame()

def update_position_status(operation_id: str, new_status: str, close_price: float, close_timestamp: str, reason: str):
    """
    Actualiza el estado, precio y motivo de cierre de una operación.
    """
    query = text("""
        UPDATE operations
        SET status = :new_status, close_price = :close_price, close_timestamp = :close_timestamp, close_reason = :reason
        WHERE operation_id = :operation_id
    """)
    params = {
        'new_status': new_status,
        'close_price': close_price,
        'close_timestamp': close_timestamp,
        'reason': reason,
        'operation_id': operation_id
    }
    try:
        with get_db_session() as session:
            session.execute(query, params)
            session.commit()
        logger.info(f"Posición {operation_id} actualizada en la BD a {new_status}.")
    except SQLAlchemyError as e:
        logger.error(f"Error al actualizar posición en la BD: {e}", exc_info=True)
        raise

def add_klines(klines_df: pd.DataFrame, symbol: str, interval: str):
    """
    Añade datos de klines a la base de datos.
    Asume que klines_df tiene las columnas: timestamp (ms), open, high, low, close, volume, close_time (ms).
    """
    # PostgreSQL equivalent of INSERT OR IGNORE is INSERT ... ON CONFLICT DO NOTHING
    query = text("""
        INSERT INTO klines (
            timestamp, symbol, interval, open, high, low, close, volume, close_time
        ) VALUES (
            :timestamp, :symbol, :interval, :open, :high, :low, :close, :volume, :close_time
        ) ON CONFLICT (timestamp, symbol, interval) DO NOTHING
    """)
    data_to_insert = []
    for _, row in klines_df.iterrows():
        data_to_insert.append({
            "timestamp": row["timestamp"],
            "symbol": symbol,
            "interval": interval,
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "close_time": row["close_time"]
        })
    try:
        with get_db_session() as session:
            session.execute(query, data_to_insert) # Use execute with a list of dicts for executemany
            session.commit()
        logger.info(f"Añadidos {len(data_to_insert)} klines para {symbol}-{interval} a la base de datos.")
    except SQLAlchemyError as e:
        logger.error(f"Error al añadir klines a la BD: {e}", exc_info=True)
        raise

def get_klines(symbol: str, interval: str, start_time: Optional[int] = None, end_time: Optional[int] = None) -> pd.DataFrame:
    """
    Obtiene datos de klines desde la base de datos.
    start_time y end_time deben ser timestamps Unix en milisegundos.
    """
    query_str = "SELECT timestamp, open, high, low, close, volume, close_time FROM klines WHERE symbol = :symbol AND interval = :interval"
    params = {"symbol": symbol, "interval": interval}
    if start_time:
        query_str += " AND timestamp >= :start_time"
        params["start_time"] = start_time
    if end_time:
        query_str += " AND timestamp <= :end_time"
        params["end_time"] = end_time
    query_str += " ORDER BY timestamp ASC"
    query = text(query_str)

    try:
        with get_db_session() as session:
            df = pd.read_sql(query, session.bind, params=params)
            if not df.empty:
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                # Asegurarse de que las columnas numéricas sean del tipo correcto
                numeric_cols = ["open", "high", "low", "close", "volume"]
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            return df
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener klines desde la BD: {e}", exc_info=True)
        return pd.DataFrame()

def save_discarded_signal(signal: dict):
    """
    Persiste una señal descartada en la base de datos para entrenamiento futuro.
    El campo 'features' debe ser un JSON serializado.
    """
    import json
    query = text("""
        INSERT INTO discarded_signals (timestamp, strategy, symbol, interval, decision, score, features)
        VALUES (:timestamp, :strategy, :symbol, :interval, :decision, :score, :features)
    """)
    params = {
        'timestamp': signal.get('timestamp'),
        'strategy': signal.get('strategy'),
        'symbol': signal.get('symbol'),
        'interval': signal.get('interval'),
        'decision': signal.get('decision'),
        'score': signal.get('score'),
        'features': json.dumps(signal.get('features', {}))
    }
    try:
        with get_db_session() as session:
            session.execute(query, params)
            session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Error al guardar señal descartada: {e}", exc_info=True)
        raise
