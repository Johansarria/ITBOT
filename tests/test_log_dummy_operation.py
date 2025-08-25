import unittest
from unittest.mock import patch, AsyncMock
import asyncio

from log_dummy_operation import log_dummy_operation

class TestLogDummyOperation(unittest.IsolatedAsyncioTestCase):

    @patch('log_dummy_operation.registrar_operacion', new_callable=AsyncMock)
    @patch('log_dummy_operation.escudo_activo')
    @patch('log_dummy_operation.riesgo_forzado_activo')
    async def test_log_dummy_operation_calls_registrar(
        self, mock_riesgo_forzado, mock_escudo, mock_registrar
    ):
        # Configure mocks
        mock_escudo.return_value = "ninguno"
        mock_riesgo_forzado.return_value = False

        # Call the async function
        await log_dummy_operation()

        # --- Assertions ---

        # 1. Assert that registrar_operacion was called
        mock_registrar.assert_called_once()

        # 2. Capture the arguments passed to the mock
        call_args, call_kwargs = mock_registrar.call_args
        dummy_bot, dummy_chat_id, log_data = call_args

        # 3. Verify the structure and content of log_data
        self.assertIsInstance(log_data, dict)
        self.assertIn("operation_id", log_data)
        self.assertIn("entry_price", log_data)

        # 4. Check that the mocked values were used
        self.assertEqual(log_data["escudo_activo_al_abrir"], False) # "ninguno" != "ninguno" is False
        self.assertEqual(log_data["tipo_escudo_al_abrir"], "ninguno")
        self.assertEqual(log_data["riesgo_forzado_al_abrir"], False)

        # 5. Check some data types
        self.assertIsInstance(log_data["operation_id"], str)
        self.assertIsInstance(log_data["entry_price"], float)
        self.assertIsInstance(log_data["size_usdt"], float)
