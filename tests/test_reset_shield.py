import unittest
from unittest.mock import patch, MagicMock

from reset_shield import reset_shield

class TestResetShield(unittest.TestCase):

    @patch('reset_shield.setup_logging')
    @patch('reset_shield.logging.getLogger')
    @patch('reset_shield.StateManager')
    def test_reset_shield_when_already_inactive(self, mock_state_manager_class, mock_get_logger, mock_setup_logging):
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_state_manager_instance = MagicMock()
        mock_state_manager_class.return_value = mock_state_manager_instance
        mock_state_manager_instance.get_state.return_value = {"escudo_activo": False}

        # Act
        reset_shield()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_state_manager_instance.get_state.assert_called_once_with("shield_manager")
        mock_state_manager_instance.update_module_state.assert_not_called()
        mock_logger.info.assert_called_with("El escudo ya se encuentra desactivado.")

    @patch('reset_shield.setup_logging')
    @patch('reset_shield.logging.getLogger')
    @patch('reset_shield.StateManager')
    @patch('reset_shield.datetime')
    def test_reset_shield_when_active(self, mock_datetime, mock_state_manager_class, mock_get_logger, mock_setup_logging):
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_state_manager_instance = MagicMock()
        mock_state_manager_class.return_value = mock_state_manager_instance
        mock_state_manager_instance.get_state.return_value = {"escudo_activo": True}

        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2025-01-01T12:00:00"
        mock_datetime.now.return_value = mock_now

        # Act
        reset_shield()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_state_manager_instance.get_state.assert_called_once_with("shield_manager")

        expected_payload = {
            "escudo_activo": False,
            "tipo_escudo": "ninguno",
            "fuente_escudo": "manual_reset",
            "desactivado_at": "2025-01-01T12:00:00"
        }
        mock_state_manager_instance.update_module_state.assert_called_once_with("shield_manager", expected_payload)
        mock_logger.info.assert_called_with("Kill Switch (Escudo Extremo) ha sido desactivado manualmente.")

    @patch('reset_shield.setup_logging')
    @patch('reset_shield.logging.getLogger')
    @patch('reset_shield.StateManager')
    def test_reset_shield_handles_exception(self, mock_state_manager_class, mock_get_logger, mock_setup_logging):
        # Arrange
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        mock_state_manager_instance = MagicMock()
        mock_state_manager_class.return_value = mock_state_manager_instance
        mock_state_manager_instance.get_state.side_effect = Exception("Failed to connect to state file")

        # Act
        reset_shield()

        # Assert
        mock_setup_logging.assert_called_once()
        mock_logger.exception.assert_called_once_with("Error al ejecutar reset_shield.py")
