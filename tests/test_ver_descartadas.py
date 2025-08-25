import unittest
from unittest.mock import patch, MagicMock

from ver_descartadas import main as ver_descartadas_main

class TestVerDescartadas(unittest.TestCase):

    @patch('ver_descartadas.sqlite3.connect')
    def test_main_fetches_and_returns_data(self, mock_connect):
        # Arrange
        mock_cursor = MagicMock()
        mock_connection = MagicMock()

        # When sqlite3.connect is called, it returns our mock_connection
        mock_connect.return_value = mock_connection

        # The 'with' statement on the connection will call __enter__, which
        # should return the connection object itself.
        mock_connection.__enter__.return_value = mock_connection

        # The connection's cursor() method should return our mock_cursor
        mock_connection.cursor.return_value = mock_cursor

        expected_rows = [
            (1, '2025-08-10', 'ML', 'BTCUSDT', '1h', 'HOLD', 0.5),
            (2, '2025-08-11', 'TA', 'ETHUSDT', '4h', 'SELL', 0.8)
        ]
        mock_cursor.fetchall.return_value = expected_rows

        # Act
        with patch('builtins.print') as mock_print: # Mock print to keep test output clean
            result_rows = ver_descartadas_main("dummy/path.db")

        # Assert
        mock_connect.assert_called_once_with("dummy/path.db")
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT id, timestamp, strategy, symbol, interval, decision, score FROM discarded_signals ORDER BY id DESC LIMIT 5;")
        mock_cursor.fetchall.assert_called_once()

        self.assertEqual(result_rows, expected_rows)
        self.assertEqual(mock_print.call_count, len(expected_rows))
        mock_print.assert_any_call(expected_rows[0])
        mock_print.assert_any_call(expected_rows[1])
