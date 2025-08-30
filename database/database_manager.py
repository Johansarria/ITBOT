# database/database_manager.py
import logging
import os
from typing import Dict, Any, List, Optional
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from config import settings  # Import the pydantic settings object

logger = logging.getLogger(__name__)

# Singleton instances, prefixed with _ to indicate they are module-internal
_engine = None
_SessionLocal = None


def get_engine():
    """
    Returns the SQLAlchemy engine, creating it only if it doesn't exist (singleton pattern).
    This prevents reloading the configuration and ensures the engine is created only once.
    """
    global _engine
    if _engine is None:
        if not settings.DATABASE_URL:
            logger.critical("DATABASE_URL is not set. Cannot create database engine.")
            raise ValueError("DATABASE_URL is not set. Check your configuration.")

        logger.info(f"Creating new database engine for: {settings.DB_TYPE}")
        _engine = create_engine(settings.DATABASE_URL)
    return _engine


def get_db_session() -> Session:
    """
    Provides a SQLAlchemy session from a singleton session factory.
    """
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        # Estilo SQLAlchemy 2.0: sin autocommit; bind via engine; conservamos autoflush=False
        _SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)
    return _SessionLocal()


def _is_sqlite() -> bool:
    """Determina si la BD actual es SQLite (incluye memoria)."""
    try:
        url = settings.DATABASE_URL or ""
        return url.startswith("sqlite")
    except Exception:
        return False


def _prepare_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte datetime -> ISO string cuando usamos SQLite para evitar DeprecationWarning.
    Mantiene los demás tipos intactos.
    """
    if not _is_sqlite() or not params:
        return params
    conv: Dict[str, Any] = {}
    for k, v in params.items():
        if isinstance(v, datetime):
            # ISO 8601 compatible con sqlite y legible
            conv[k] = v.isoformat(sep=" ")
        else:
            conv[k] = v
    return conv


def reset_db_connection():
    """
    Resets the engine and session factory. Useful for testing.
    """
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
        _engine = None
    _SessionLocal = None
    logger.info("Database connection engine and session have been reset.")


def init_db():
    """
    Initializes the database by testing the connection and creating tables.
    This function should be called once at application startup.
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection successful.")
        create_tables()
    except SQLAlchemyError as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}", exc_info=True)
        raise


def create_tables():
    """
    Creates database tables if they don't exist using the engine's inspector.
    """
    engine = get_engine()
    inspector = inspect(engine)
    
    table_definitions = {
        "operations": """
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
        """,
        "klines": """
            CREATE TABLE klines (
                timestamp BIGINT NOT NULL,
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
        """,
        "discarded_signals": """
            CREATE TABLE discarded_signals (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                strategy VARCHAR(255) NOT NULL,
                symbol VARCHAR(255) NOT NULL,
                interval VARCHAR(255) NOT NULL,
                decision VARCHAR(255) NOT NULL,
                score NUMERIC,
                features TEXT
            )
        """
    }

    with get_db_session() as session:
        try:
            for table_name, ddl in table_definitions.items():
                if not inspector.has_table(table_name):
                    session.execute(text(ddl))
                    logger.info(f"Table '{table_name}' created.")
                else:
                    logger.info(f"Table '{table_name}' already exists.")
            session.commit()
            logger.info("Database tables verified/created.")
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating tables: {e}", exc_info=True)
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error creating tables: {e}", exc_info=True)
            raise

# --- Database Interaction Functions ---

def add_operation(op_data: Dict[str, Any]):
    """
    Adds a new operation to the database.
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
    try:
        with get_db_session() as session:
            session.execute(query, _prepare_params(op_data))
            session.commit()
        logger.info(f"Operation {op_data.get('operation_id')} added to the database.")
    except SQLAlchemyError as e:
        logger.error(f"Error adding operation to DB: {e}", exc_info=True)
        raise


def get_open_positions_df() -> pd.DataFrame:
    """
    Retrieves all positions with 'OPEN' status from the DB.
    """
    query = text("SELECT * FROM operations WHERE status = 'OPEN'")
    try:
        with get_db_session() as session:
            con = session.get_bind()
            df = pd.read_sql(query, con=con)
            return df
    except SQLAlchemyError as e:
        logger.error(f"Error getting open positions from DB: {e}", exc_info=True)
        return pd.DataFrame()


def update_position_status(operation_id: str, new_status: str, close_price: float, close_timestamp: datetime, reason: str):
    """
    Updates the status, closing price, and reason for an operation.
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
            session.execute(query, _prepare_params(params))
            session.commit()
        logger.info(f"Position {operation_id} updated in DB to {new_status}.")
    except SQLAlchemyError as e:
        logger.error(f"Error updating position in DB: {e}", exc_info=True)
        raise


def add_klines(klines_df: pd.DataFrame, symbol: str, interval: str):
    """
    Adds kline data to the database, ignoring duplicates.
    """
    query = text("""
        INSERT INTO klines (
            timestamp, symbol, interval, open, high, low, close, volume, close_time
        ) VALUES (
            :timestamp, :symbol, :interval, :open, :high, :low, :close, :volume, :close_time
        ) ON CONFLICT (timestamp, symbol, interval) DO NOTHING
    """)
    # Prepare data for bulk insert
    data_to_insert = []
    temp_df = klines_df.copy()
    temp_df['symbol'] = symbol
    temp_df['interval'] = interval
    # Ensure 'timestamp' is in the DataFrame columns if it's the index
    if temp_df.index.name == 'timestamp':
        temp_df.reset_index(inplace=True)
    
    # Convert timestamp to Unix ms integer
    temp_df['timestamp'] = (temp_df['timestamp'].astype(int) / 10**6).astype(int)
    
    data_to_insert = temp_df.to_dict(orient='records')

    try:
        with get_db_session() as session:
            if data_to_insert:
                # Para listas de diccionarios, SQLAlchemy soporta ejecutar con many params
                session.execute(query, data_to_insert)  # type: ignore[arg-type]
                session.commit()
        logger.info(f"Processed {len(data_to_insert)} klines for {symbol}-{interval}.")
    except SQLAlchemyError as e:
        logger.error(f"Error adding klines to DB: {e}", exc_info=True)
        raise


def get_klines(symbol: str, interval: str, start_time: Optional[int] = None, end_time: Optional[int] = None, limit: Optional[int] = None) -> pd.DataFrame:
    """
    Retrieves kline data from the database within a specified time range, with an optional limit.
    Timestamps are handled as Unix milliseconds.
    """
    query_str = "SELECT timestamp, open, high, low, close, volume, close_time FROM klines WHERE symbol = :symbol AND interval = :interval"
    params: Dict[str, Any] = {"symbol": symbol, "interval": interval}
    if start_time is not None:
        query_str += " AND timestamp >= :start_time"
        params["start_time"] = int(start_time)
    if end_time is not None:
        query_str += " AND timestamp <= :end_time"
        params["end_time"] = int(end_time)
    query_str += " ORDER BY timestamp DESC"
    if limit is not None:
        query_str += " LIMIT :limit"
        params["limit"] = int(limit)
    
    try:
        with get_db_session() as session:
            # The query is ordered DESC to get the latest klines, but we need to return them in ASC order.
            con = session.get_bind()
            df = pd.read_sql(text(query_str), con=con, params=params)
            if not df.empty:
                df = df.sort_values(by='timestamp', ascending=True)
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                df.set_index("timestamp", inplace=True)
                numeric_cols = ["open", "high", "low", "close", "volume"]
                df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            return df
    except SQLAlchemyError as e:
        logger.error(f"Error getting klines from DB: {e}", exc_info=True)
        return pd.DataFrame()


def save_discarded_signal(signal: dict):
    """
    Persists a discarded signal to the database for future training.
    The 'features' field should be a JSON-serialized string.
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
            session.execute(query, _prepare_params(params))
            session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Error saving discarded signal: {e}", exc_info=True)
        raise
