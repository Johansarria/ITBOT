# tests/test_database_manager.py
import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock
from database.database_manager import init_db, DB_PATH, DB_DIR

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

def test_init_db_creates_directory_and_file():
    """
    Test that init_db creates the database directory and file.
    """
    with patch('os.makedirs') as mock_makedirs, \
         patch('sqlite3.connect') as mock_connect:
        
        mock_conn = MagicMock()
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        init_db()
        
        mock_makedirs.assert_called_once_with('/tmp/test_db_dir', exist_ok=True)
        mock_connect.assert_called_once_with(':memory:')
        mock_conn.cursor.assert_called_once()
        mock_conn.commit.assert_called_once()

def test_init_db_creates_operations_table():
    """
    Test that init_db executes the SQL to create all necessary tables.
    """
    with patch('os.makedirs'), \
         patch('sqlite3.connect') as mock_connect:
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn
        
        init_db()
        
        # Assert that execute was called 3 times (once for each table)
        assert mock_cursor.execute.call_count == 3

        # Check the arguments of each call
        calls = mock_cursor.execute.call_args_list

        # Check operations table creation SQL
        sql_operations = calls[0].args[0]
        assert "CREATE TABLE IF NOT EXISTS operations" in sql_operations
        assert "operation_id TEXT PRIMARY KEY" in sql_operations

        # Check klines table creation SQL
        sql_klines = calls[1].args[0]
        assert "CREATE TABLE IF NOT EXISTS klines" in sql_klines
        assert "timestamp INTEGER NOT NULL" in sql_klines
        assert "symbol TEXT NOT NULL" in sql_klines
        assert "interval TEXT NOT NULL" in sql_klines
        assert "PRIMARY KEY (timestamp, symbol, interval)" in sql_klines

        # Check discarded_signals table creation SQL
        sql_discarded_signals = calls[2].args[0]
        assert "CREATE TABLE IF NOT EXISTS discarded_signals" in sql_discarded_signals
        assert "id INTEGER PRIMARY KEY AUTOINCREMENT" in sql_discarded_signals


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
