import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Message
from datetime import datetime
from zoneinfo import ZoneInfo

# Importar la función a probar y sus dependencias


# Mockear las dependencias externas
@pytest.fixture
def mock_dependencies():
    with (
        patch('listener_bot.flujo_principal', new_callable=AsyncMock) as mock_flujo_principal,
        patch('listener_bot.es_comando_reporte') as mock_es_comando_reporte,
        patch('listener_bot.procesar_comando_reporte', new_callable=AsyncMock) as mock_procesar_comando_reporte,
        patch('listener_bot.es_comando_riesgo') as mock_es_comando_riesgo,
        patch('listener_bot.procesar_comando_riesgo', new_callable=AsyncMock) as mock_procesar_comando_riesgo,
        patch('listener_bot.es_comando_analisis') as mock_es_comando_analisis,
        patch('listener_bot.procesar_comando_analisis', new_callable=AsyncMock) as mock_procesar_comando_analisis,
        patch('listener_bot.send_message', new_callable=AsyncMock) as mock_send_message
    ):
        # Importar las funciones después de aplicar los patches
        from listener_bot import manejar_mensajes, bot, chat_id_int

        yield {
            "manejar_mensajes": manejar_mensajes,
            "bot": bot,
            "chat_id_int": chat_id_int,
            "mock_flujo_principal": mock_flujo_principal,
            "mock_es_comando_reporte": mock_es_comando_reporte,
            "mock_procesar_comando_reporte": mock_procesar_comando_reporte,
            "mock_es_comando_riesgo": mock_es_comando_riesgo,
            "mock_procesar_comando_riesgo": mock_procesar_comando_riesgo,
            "mock_es_comando_analisis": mock_es_comando_analisis,
            "mock_procesar_comando_analisis": mock_procesar_comando_analisis,
            "mock_send_message": mock_send_message
        }

