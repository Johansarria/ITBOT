import unittest
from unittest.mock import patch

from init_tabla_descartadas import main as init_tabla_descartadas_main

class TestInitTablaDescartadas(unittest.TestCase):

    @patch('init_tabla_descartadas.create_tables')
    def test_main_calls_create_tables(self, mock_create_tables):
        """
        Tests that the main function calls create_tables exactly once.
        """
        # Call the main function
        init_tabla_descartadas_main()

        # Assert that the mocked function was called
        mock_create_tables.assert_called_once()
