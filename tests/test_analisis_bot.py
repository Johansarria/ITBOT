# tests/test_analisis_bot.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import pandas as pd

# Importar la función a probar
from modules.analisis_bot import procesar_comando_analisis

# Mockear las dependencias externas
@pytest.fixture
def mock_dependencies():
    with patch('modules.analisis_bot.send_message', new_callable=AsyncMock) as mock_send_message, \
         patch('modules.analisis_bot.StrategyManager') as mock_strategy_manager, \
         patch('modules.analisis_bot.get_historical_klines', new_callable=AsyncMock) as mock_get_historical_klines, \
         patch('modules.analisis_bot.get_open_positions_summary') as mock_get_open_positions_summary:
        
        # Configurar mocks
        mock_strategy_instance = MagicMock()
        mock_strategy_instance.analyze = AsyncMock(return_value={"decision": "COMPRAR", "score": 0.9, "symbol": "BTCUSDT"})
        mock_strategy_instance.name = "TestStrategy"
        
        mock_strategy_manager.return_value.get_active_strategy.return_value = mock_strategy_instance
        mock_get_historical_klines.return_value = pd.DataFrame({'close': [1, 2, 3]}) # Datos no vacíos

        yield {
            "mock_send_message": mock_send_message,
            "mock_strategy_manager": mock_strategy_manager,
            "mock_get_historical_klines": mock_get_historical_klines,
            "mock_get_open_positions_summary": mock_get_open_positions_summary,
            "mock_strategy_instance": mock_strategy_instance
        }

@pytest.mark.asyncio
async def test_procesar_comando_analisis_menu(mock_dependencies):
    mock_bot = AsyncMock()
    chat_id = 123
    texto = "analizar"

    await procesar_comando_analisis(mock_bot, chat_id, texto)

    # Verificar que se envía el menú con botones
    mock_dependencies["mock_send_message"].assert_called_once()
    call_args = mock_dependencies["mock_send_message"].call_args
    assert "Selecciona el tipo de análisis" in call_args[0][2]
    assert call_args[1]["reply_markup"] is not None

@pytest.mark.asyncio
@pytest.mark.parametrize("texto_comando", ["resumen tecnico", "score tecnico", "recomendar accion"])
async def test_procesar_comando_analisis_estrategia(mock_dependencies, texto_comando):
    mock_bot = AsyncMock()
    chat_id = 123

    await procesar_comando_analisis(mock_bot, chat_id, texto_comando)

    # Verificar que se llama a la estrategia activa
    mock_dependencies["mock_strategy_manager"].assert_called_once()
    mock_dependencies["mock_get_historical_klines"].assert_called_once()
    mock_dependencies["mock_strategy_instance"].analyze.assert_called_once()

    # Verificar que se envía el mensaje de resultado
    assert mock_dependencies["mock_send_message"].call_count == 2 # "Analizando..." y el resultado
    final_call_args = mock_dependencies["mock_send_message"].call_args_list[1]
    assert "Resultado del Análisis con 'TestStrategy'" in final_call_args[0][2]
    assert "<b>Decisión:</b> COMPRAR" in final_call_args[0][2]
    assert "<b>Score:</b> 0.9" in final_call_args[0][2]

@pytest.mark.asyncio
async def test_procesar_comando_analisis_posiciones(mock_dependencies):
    mock_bot = AsyncMock()
    chat_id = 123
    texto = "posiciones"
    mock_dependencies["mock_get_open_positions_summary"].return_value = "Resumen de posiciones simulado"

    await procesar_comando_analisis(mock_bot, chat_id, texto)

    mock_dependencies["mock_get_open_positions_summary"].assert_called_once()
    mock_dependencies["mock_send_message"].assert_called_once_with(mock_bot, chat_id, "Resumen de posiciones simulado")

@pytest.mark.asyncio
async def test_procesar_comando_analisis_unknown_command(mock_dependencies):
    mock_bot = AsyncMock()
    chat_id = 123
    texto = "comando desconocido"

    await procesar_comando_analisis(mock_bot, chat_id, texto)

    mock_dependencies["mock_send_message"].assert_called_once_with(mock_bot, chat_id, "🤖 Comando de análisis no reconocido. Prueba con: `analizar` o `posiciones`.")
    mock_dependencies["mock_strategy_instance"].analyze.assert_not_called()