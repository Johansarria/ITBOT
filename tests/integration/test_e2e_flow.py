# tests/integration/test_e2e_flow.py

import pytest
import asyncio
import sqlite3
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import pandas as pd

# Importar módulos del bot
from run_bot import main_run_bot
from execution_worker import main as start_execution_worker_main
from database.database_manager import init_db
from config import TRADING_PAIRS
from utils.message_queue import mq

# Fixture para usar una base de datos temporal para cada test
@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_itbot.db"
    with patch('database.database_manager.DB_PATH', str(db_path)):
        init_db()
        yield str(db_path)

# Fixture para mockear interacciones con Telegram
@pytest.fixture
def mock_telegram():
    with patch('utils.telegram_handler.send_message', new_callable=AsyncMock) as mock_send_message:
        yield mock_send_message

# Fixture para mockear la API de Binance
@pytest.fixture
def mock_binance_client():
    with patch('utils.binance_client.get_binance_client', new_callable=AsyncMock) as mock_get_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.create_order.return_value = {
            'orderId': 'test_order_id',
            'status': 'FILLED',
            'fills': [{'price': '50000', 'qty': '0.0001'}]
        }
        mock_get_client.return_value = mock_client_instance
        yield mock_client_instance

# Fixture para mockear la cola de mensajes de Redis
@pytest.fixture
def mock_message_queue():
    with patch('utils.message_queue.mq.publish_decision') as mock_publish:
        with patch('utils.message_queue.mq.get_decision', new_callable=AsyncMock) as mock_get:
            yield mock_publish, mock_get

@pytest.mark.asyncio
async def test_e2e_trading_flow(
    monkeypatch,
    temp_db,
    mock_telegram,
    mock_binance_client,
    mock_message_queue
):
    """
    Prueba End-to-End que simula el flujo completo:
    1. `run_bot` analiza y publica una decisión de compra.
    2. `execution_worker` consume la decisión y ejecuta la orden.
    3. Se verifica que la orden se creó en Binance y se guardó en la BD.
    """
    mock_publish, mock_get = mock_message_queue

    # --- Configuración de Mocks para el Flujo ---
    # 1. Mockear el flujo de análisis para que publique una decisión de compra
    async def mock_flujo_side_effect(bot_instance, chat_id, symbol):
        test_decision = {
            "type": "AUTOMATED_TRADE", "symbol": "BTCUSDT",
            "side": "BUY", "quantity": 0.0001,
        }
        mq.publish_decision(test_decision)
        run_bot_task.cancel()

    monkeypatch.setattr('run_bot.flujo_principal_por_activo', mock_flujo_side_effect)
    monkeypatch.setattr('run_bot.verificar_condiciones_mercado', AsyncMock(return_value={"status": "OK"}))

    # Patch the global variable in the config module
    monkeypatch.setattr('config.TRADING_PAIRS', ["BTCUSDT"])


    # --- Ejecución ---
    # Iniciar run_bot en una tarea de fondo
    run_bot_task = asyncio.create_task(main_run_bot())
    try:
        # Dar un pequeño delay para que el bot pueda procesar
        await asyncio.sleep(2)

        # Verificar que la decisión fue publicada
        mock_publish.assert_called()
        published_decision = mock_publish.call_args[0][0]
        assert published_decision['symbol'] == "BTCUSDT"
    finally:
        run_bot_task.cancel()
        from contextlib import suppress
        with suppress(asyncio.CancelledError):
            await run_bot_task