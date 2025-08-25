import unittest
from unittest.mock import patch

from reset_riesgo import main as reset_riesgo_main

class TestResetRiesgo(unittest.TestCase):

    @patch('reset_riesgo.restaurar_riesgo_automatico')
    def test_main_calls_restaurar_riesgo(self, mock_restaurar_riesgo):
        """
        Tests that the main function calls restaurar_riesgo_automatico exactly once.
        """
        # Call the main function
        reset_riesgo_main()

        # Assert that the mocked function was called
        mock_restaurar_riesgo.assert_called_once()
