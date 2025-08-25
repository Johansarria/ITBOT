import unittest
from unittest.mock import patch, MagicMock

from init_audit_db import main as init_audit_db_main

class TestInitAuditDb(unittest.TestCase):

    @patch('init_audit_db.setup_logging')
    @patch('init_audit_db.ensure_operations_table')
    @patch('init_audit_db.logging.getLogger')
    def test_main_success(self, mock_get_logger, mock_ensure_table, mock_setup_logging):
        # Setup mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Call the main function
        init_audit_db_main()

        # Assertions
        mock_setup_logging.assert_called_once()
        mock_ensure_table.assert_called_once()
        self.assertEqual(mock_logger.info.call_count, 2)
        mock_logger.error.assert_not_called()

    @patch('init_audit_db.setup_logging')
    @patch('init_audit_db.ensure_operations_table')
    @patch('init_audit_db.logging.getLogger')
    def test_main_failure(self, mock_get_logger, mock_ensure_table, mock_setup_logging):
        # Setup mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Configure the mock to raise an exception
        mock_ensure_table.side_effect = Exception("DB connection failed")

        # Call the main function
        init_audit_db_main()

        # Assertions
        mock_setup_logging.assert_called_once()
        mock_ensure_table.assert_called_once()
        mock_logger.info.assert_called_once() # Only the first info call should happen
        mock_logger.error.assert_called_once()
