import pytest
import os
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import config
from database.database_manager import init_db, get_db_session, create_tables

# Fixture para asegurar un estado limpio para cada test
@pytest.fixture(autouse=True)
def setup_db_test(monkeypatch):
    # Usar una base de datos en memoria para los tests unitarios
    monkeypatch.setattr('database.database_manager.DB_PATH', ':memory:')
    monkeypatch.setattr('database.database_manager.DB_DIR', '/tmp/test_db_dir') # No se usará para :memory: pero es buena práctica

    # Asegurarse de que el directorio temporal exista si no es :memory:
    if not os.path.exists('/tmp/test_db_dir'):
        os.makedirs('/tmp/test_db_dir', exist_ok=True)

    yield

    # No es necesario limpiar para :memory:

    # Re-initialize the database manager with the in-memory DB
    # This will also call create_tables()
    init_db()

    yield # Test runs here

    # Clean up: restore original DB_URL (if needed for other tests)
    config.DATABASE_URL = original_db_url

# Test init_db and create_tables
def test_init_db_and_create_tables(in_memory_db):
    """
    Test that init_db successfully initializes the engine and creates tables.
    """
    # After in_memory_db fixture runs, tables should be created.
    # Verify by inspecting the in-memory database.
    engine = create_engine(config.DATABASE_URL)
    inspector = inspect(engine)

    assert inspector.has_table("operations")
    assert inspector.has_table("klines")
    assert inspector.has_table("discarded_signals")

def test_init_db_handles_sqlalchemy_error():
    """
    Test that init_db handles SQLAlchemyError during engine creation.
    """
    original_db_url = config.DATABASE_URL
    config.DATABASE_URL = "invalid_url" # Force an error

    with pytest.raises(SQLAlchemyError):
        init_db()
        
        mock_makedirs.assert_called_once_with('/tmp/test_db_dir', exist_ok=True)
        mock_connect.assert_called_once_with(':memory:')
        mock_conn.cursor.assert_called_once()
        mock_conn.commit.assert_called_once()

    config.DATABASE_URL = original_db_url # Restore for other tests

# Test add_operation
def test_add_operation(in_memory_db):
    from database.database_manager import add_operation
    op_data = {
        'operation_id': 'test_op_1',
        'timestamp': '2025-01-01 10:00:00',
        'symbol': 'BTCUSDT',
        'side': 'BUY',
        'price': 10000.0,
        'quantity': 0.001,
        'status': 'OPEN',
        'mode': 'live',
        'decision': 'ML_BUY',
        'escudo': None,
        'riesgo_forzado_activo': 0,
        'ganancia_pct_operacion': None,
        'close_price': None,
        'close_timestamp': None,
        'close_reason': None
    }
    add_operation(op_data)

    # Verify data was inserted
    engine = create_engine(config.DATABASE_URL)
    with sessionmaker(bind=engine)() as session:
        result = session.execute(text("SELECT * FROM operations WHERE operation_id = 'test_op_1'")).fetchone()
        assert result is not None
        assert result.symbol == 'BTCUSDT'

# Test get_open_positions_df
def test_get_open_positions_df(in_memory_db):
    from database.database_manager import add_operation, get_open_positions_df
    op_data = {
        'operation_id': 'test_op_2',
        'timestamp': '2025-01-02 10:00:00',
        'symbol': 'ETHUSDT',
        'side': 'BUY',
        'price': 2000.0,
        'quantity': 0.01,
        'status': 'OPEN',
        'mode': 'live',
        'decision': 'ML_BUY',
        'escudo': None,
        'riesgo_forzado_activo': 0,
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
    from database.database_manager import add_operation, update_position_status
    op_data = {
        'operation_id': 'test_op_3',
        'timestamp': '2025-01-03 10:00:00',
        'symbol': 'LTCUSDT',
        'side': 'BUY',
        'price': 100.0,
        'quantity': 0.1,
        'status': 'OPEN',
        'mode': 'live',
        'decision': 'ML_BUY',
        'escudo': None,
        'riesgo_forzado_activo': 0,
        'ganancia_pct_operacion': None,
        'close_price': None,
        'close_timestamp': None,
        'close_reason': None
    }
    add_operation(op_data)

    update_position_status('test_op_3', 'CLOSED', 105.0, '2025-01-03 11:00:00', 'TP')

    engine = create_engine(config.DATABASE_URL)
    with sessionmaker(bind=engine)() as session:
        result = session.execute(text("SELECT status, close_price FROM operations WHERE operation_id = 'test_op_3'")).fetchone()
        assert result.status == 'CLOSED'
        assert result.close_price == 105.0

# Test add_klines
def test_add_klines(in_memory_db):
    from database.database_manager import add_klines
    klines_data = pd.DataFrame([
        {'timestamp': 1672531200000, 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000, 'close_time': 1672534799999},
        {'timestamp': 1672534800000, 'open': 105, 'high': 115, 'low': 95, 'close': 110, 'volume': 1200, 'close_time': 1672538399999}
    ])
    add_klines(klines_data, 'TESTSYM', '1h')

    engine = create_engine(config.DATABASE_URL)
    with sessionmaker(bind=engine)() as session:
        result = session.execute(text("SELECT COUNT(*) FROM klines WHERE symbol = 'TESTSYM'")).scalar()
        assert result == 2

# Test get_klines
def test_get_klines(in_memory_db):
    from database.database_manager import add_klines, get_klines
    klines_data = pd.DataFrame([
        {'timestamp': 1672531200000, 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1000, 'close_time': 1672534799999},
        {'timestamp': 1672534800000, 'open': 105, 'high': 115, 'low': 95, 'close': 110, 'volume': 1200, 'close_time': 1672538399999}
    ])
    add_klines(klines_data, 'ANOTHER', '1h')

    df = get_klines('ANOTHER', '1h')
    assert not df.empty
    assert len(df) == 2
    assert df.index.name == 'timestamp'

# Test save_discarded_signal
def test_save_discarded_signal(in_memory_db):
    from database.database_manager import save_discarded_signal
    signal_data = {
        'timestamp': '2025-01-04 10:00:00',
        'strategy': 'ML_Strategy',
        'symbol': 'XRPUSDT',
        'interval': '4h',
        'decision': 'SELL',
        'score': 0.85,
        'features': {'feat1': 10, 'feat2': 20}
    }
    save_discarded_signal(signal_data)

    engine = create_engine(config.DATABASE_URL)
    with sessionmaker(bind=engine)() as session:
        result = session.execute(text("SELECT * FROM discarded_signals WHERE symbol = 'XRPUSDT'")).fetchone()
        assert result is not None
        assert result.decision == 'SELL'
        assert 'feat1' in result.features # Features is TEXT, so it's a JSON string
def test_init_db_handles_sqlite_error():
    """
    Test that init_db handles sqlite3.Error during connection or execution.
    """
    with patch('os.makedirs'), \
         patch('sqlite3.connect') as mock_connect:
        
        mock_connect.side_effect = sqlite3.Error("Test DB Error")
        
        with pytest.raises(sqlite3.Error) as excinfo:
            init_db()
        
        assert "Test DB Error" in str(excinfo.value)
        mock_connect.assert_called_once_with(':memory:')
