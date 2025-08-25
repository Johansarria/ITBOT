import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import zoneinfo

from estado_diario import enviar_estado_diario


class TestEstadoDiario(unittest.TestCase):

    def setUp(self):
        self.mock_bot = MagicMock()
        self.chat_id = 12345
        self.now = datetime.now(zoneinfo.ZoneInfo("UTC"))

    def run_enviar_estado_diario(self, state_effects, mock_send_message, mock_state_manager_class):
        mock_state_manager_instance = MagicMock()
        mock_state_manager_class.return_value = mock_state_manager_instance
        mock_state_manager_instance.get_state.side_effect = state_effects

        asyncio.run(enviar_estado_diario(self.mock_bot, self.chat_id))

        return mock_state_manager_instance

    @patch('estado_diario.StateManager')
    @patch('estado_diario.send_message', new_callable=AsyncMock)
    def test_enviar_estado_diario_base(self, mock_send_message, mock_state_manager_class):
        state_effects = [
            {"riesgo_forzado": False, "riesgo_actual": 0.01, "tiempo_riesgo_forzado": None},
            {"escudo_activo": False, "tipo_escudo": "NINGUNO"},
            {"ia_activa": False, "modo_ia": "normal"},
            None
        ]
        mock_state_manager_instance = self.run_enviar_estado_diario(state_effects, mock_send_message, mock_state_manager_class)

        mock_send_message.assert_called_once()
        message = mock_send_message.call_args[0][2]
        self.assertIn("Riesgo forzado: ❌ (1%)", message)
        self.assertIn("Escudo activo: ❌ (NINGUNO)", message)
        self.assertIn("IA activa: ❌ (Modo: normal)", message)
        self.assertIn("Último reporte diario enviado: N/A", message)
        mock_state_manager_instance.set_state.assert_called_once()

    @patch('estado_diario.StateManager')
    @patch('estado_diario.send_message', new_callable=AsyncMock)
    def test_enviar_estado_diario_con_todo_activo(self, mock_send_message, mock_state_manager_class):
        last_report_date = (self.now - timedelta(days=1)).isoformat()
        tiempo_riesgo_forzado = (self.now - timedelta(hours=2)).isoformat()

        state_effects = [
            {"riesgo_forzado": True, "riesgo_actual": 0.05, "tiempo_riesgo_forzado": tiempo_riesgo_forzado},
            {"escudo_activo": True, "tipo_escudo": "TOTAL"},
            {"ia_activa": True, "modo_ia": "agresivo"},
            last_report_date
        ]
        mock_state_manager_instance = self.run_enviar_estado_diario(state_effects, mock_send_message, mock_state_manager_class)

        mock_send_message.assert_called_once()
        message = mock_send_message.call_args[0][2]
        self.assertIn("Riesgo forzado: ✅ (5%) desde hace 2h", message)
        self.assertIn("Escudo activo: ✅ (TOTAL)", message)
        self.assertIn("IA activa: ✅ (Modo: agresivo)", message)
        self.assertIn(f"Último reporte diario enviado: {(self.now - timedelta(days=1)).strftime('%Y-%m-%d')}", message)
        mock_state_manager_instance.set_state.assert_called_once()
