import pytest
import pandas as pd
from unittest.mock import patch
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from config import settings
from database.database_manager import (
    init_db,
    add_operation,
    get_open_positions_df,
    update_position_status,
    add_klines,
    get_klines,
    save_discarded_signal,
    get_db_session, # Import the session getter
    get_engine # Import the engine getter
)

# Test init_db and table creation
def test_init_db_and_create_tables(in_memory_db):
    """
    Test that init_db successfully initializes the engine and creates tables.
    The in_memory_db fixture handles setup and teardown.
    """
    # The fixture has already run init_db(). We just verify the tables exist.
    engine = get_engine()
    inspector = inspect(engine)
    assert inspector.has_table("operations")
    assert inspector.has_table("klines")
    assert inspector.has_table("discarded_signals")


def test_init_db_handles_sqlalchemy_error(monkeypatch):
    """
    Test that init_db logs an error if the database connection fails.
    This test does NOT use the in_memory_db fixture because it needs to mock the connection itself.
    """
    # Patch get_engine to raise an error
    with patch('database.database_manager.get_engine', side_effect=SQLAlchemyError("Connection Failed")) as mock_get_engine:
        with patch('logging.Logger.error') as mock_logger_error, pytest.raises(SQLAlchemyError):
            init_db()
            mock_get_engine.assert_called_once()
            mock_logger_error.assert_called_with("Error during database initialization: Connection Failed", exc_info=True)


# Test add_operation
def test_add_operation(in_memory_db):
    op_data = {
        'operation_id': 'test_op_1',
        'timestamp': pd.to_datetime('2025-01-01 10:00:00').to_pydatetime(),
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'price': 10000.0,
        'quantity': 0.001,
        'status': 'OPEN',
        'mode': 'live',
        'decision': 'buy_signal',
        'escudo': 'none',
        'riesgo_forzado_activo': False,
        'ganancia_pct_operacion': None,
        'close_price': None,
        'close_timestamp': None,
        'close_reason': None
    }
    add_operation(op_data)

    # Verify data was inserted using a session
    with get_db_session() as session:
        result = session.execute(text("SELECT * FROM operations WHERE operation_id = 'test_op_1'")).fetchone()
        assert result is not None
        assert result.symbol == 'BTCUSDT'


# Test get_open_positions_df
def test_get_open_positions_df(in_memory_db):
    op_data = {
        'operation_id': 'test_op_2',
        'timestamp': pd.to_datetime('2025-01-02 10:00:00').to_pydatetime(),
        'symbol': 'ETHUSDT',
        'side': 'BUY',
        'price': 2000.0,
        'quantity': 0.01,
        'status': 'OPEN',
        'mode': 'live',
        'decision': 'buy_signal',
        'escudo': 'none',
        'riesgo_forzado_activo': False,
        'ganancia_pct_operacion': None,
        'close_price': None,
        'close_timestamp': None,
        'close_reason': None
    }
    add_operation(op_data)

    df = get_open_positions_df()
    assert not df.empty
    assert 'test_op_2' in df['operation_id'].values


# Test update_position_status
def test_update_position_status(in_memory_db):
    op_data = {
        'operation_id': 'test_op_3',
        'timestamp': pd.to_datetime('2025-01-03 10:00:00').to_pydatetime(),
        'symbol': 'LTCUSDT',
        'side': 'BUY',
        'price': 100.0,
        'quantity': 0.1,
        'status': 'OPEN',
        'mode': 'live',
        'decision': 'buy_signal',
        'escudo': 'none',
        'riesgo_forzado_activo': False,
        'ganancia_pct_operacion': None,
        'close_price': None,
        'close_timestamp': None,
        'close_reason': None
    }
    add_operation(op_data)

    update_position_status('test_op_3', 'CLOSED', 105.0, pd.to_datetime('2025-01-03 11:00:00').to_pydatetime(), 'TP')

    with get_db_session() as session:
        result = session.execute(text("SELECT status, close_price FROM operations WHERE operation_id = 'test_op_3'")).fetchone()
        assert result.status == 'CLOSED'
        assert result.close_price == 105.0


# Test add_klines
def test_add_klines(in_memory_db):
    klines_data = pd.DataFrame({
        'timestamp': [1672531200000, 1672534800000],
        'open': [100, 105],
        'high': [110, 115],
        'low': [90, 95],
        'close': [105, 110],
        'volume': [1000, 1200],
        'close_time': [1672534799999, 1672538399999]
    })
    add_klines(klines_data, 'TESTSYM', '1h')

    with get_db_session() as session:
        result = session.execute(text("SELECT COUNT(*) FROM klines WHERE symbol = 'TESTSYM'")).scalar_one()
        assert result == 2


# Test get_klines
def test_get_klines(in_memory_db):
    klines_data = pd.DataFrame({
        'timestamp': [1672531200000, 1672534800000],
        'open': [100, 105],
        'high': [110, 115],
        'low': [90, 95],
        'close': [105, 110],
        'volume': [1000, 1200],
        'close_time': [1672534799999, 1672538399999]
    })
    add_klines(klines_data, 'ANOTHER', '1h')

    df = get_klines('ANOTHER', '1h')
    assert not df.empty
    assert len(df) == 2
    assert df.index.name == 'timestamp'


# Test save_discarded_signal
def test_save_discarded_signal(in_memory_db):
    import json
    signal_data = {
        'timestamp': pd.to_datetime('2025-01-04 10:00:00').to_pydatetime(),
        'strategy': 'ML_Strategy',
        'symbol': 'XRPUSDT',
        'interval': '4h',
        'decision': 'SELL',
        'score': 0.85,
        'features': {"feat1": 10, "feat2": 20}
    }
    save_discarded_signal(signal_data)

    with get_db_session() as session:
        result = session.execute(text("SELECT * FROM discarded_signals WHERE symbol = 'XRPUSDT'")).fetchone()
        assert result is not None
        assert result.decision == 'SELL'
        features = json.loads(result.features)
        assert features['feat1'] == 10