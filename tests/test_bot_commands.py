import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp

from utils.bot_commands import set_bot_commands

@pytest.mark.asyncio
async def test_set_bot_commands_success():
    mock_bot = AsyncMock()
    
    await set_bot_commands(mock_bot)
    
    mock_bot.set_my_commands.assert_called_once()
    args, kwargs = mock_bot.set_my_commands.call_args
    
    # Check that commands list is passed and contains expected commands
    commands = args[0]
    assert len(commands) == 7

    # Create a dictionary for easy lookup and assertion
    commands_dict = {c.command: c.description for c in commands}

    expected_commands = {
        "/status": "Verificar si el bot está funcionando.",
        "/posiciones": "Mostrar un resumen de las posiciones abiertas.",
        "/ayuda": "Mostrar este mensaje de ayuda.",
        "/reportes": "Generar reportes de operaciones.",
        "/riesgo": "Consultar o ajustar el nivel de riesgo.",
        "/analizar": "Realizar un análisis técnico del mercado.",
        "/estrategia": "Ver/cambiar la estrategia de análisis.",
    }
    
    assert commands_dict == expected_commands

@pytest.mark.asyncio
async def test_set_bot_commands_aiohttp_client_error():
    mock_bot = AsyncMock()
    mock_bot.set_my_commands.side_effect = aiohttp.ClientError("Connection error")
    
    with patch('utils.bot_commands.logger') as mock_logger:
        await set_bot_commands(mock_bot)
        
        mock_bot.set_my_commands.assert_called_once()
        mock_logger.error.assert_called_once()
        assert "Error de conexión o API al registrar los comandos del bot" in mock_logger.error.call_args[0][0]

@pytest.mark.asyncio
async def test_set_bot_commands_general_exception():
    mock_bot = AsyncMock()
    mock_bot.set_my_commands.side_effect = Exception("Unexpected error")
    
    with patch('utils.bot_commands.logger') as mock_logger:
        await set_bot_commands(mock_bot)
        
        mock_bot.set_my_commands.assert_called_once()
        mock_logger.exception.assert_called_once()
        assert "Error inesperado al registrar los comandos del bot" in mock_logger.exception.call_args[0][0]
