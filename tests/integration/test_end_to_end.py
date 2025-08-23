import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock

import pandas as pd
from sqlalchemy import text

# Importar los componentes principales
from execution_worker import main as execution_worker_main
from run_bot import main_run_bot as run_bot_main

# Importar funciones y objetos necesarios
from database import database_manager
from utils.message_queue import MessageQueue
from config import settings

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
async def message_queue():
    mq = MessageQueue(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
    await mq.redis.flushdb()
    yield mq
    await mq.redis.flushdb()

@pytest.mark.integration
@patch('config.settings') # Parchear la configuración global
@patch('utils.binance_client.BinanceClient')
@patch('run_bot.send_message')
@patch('run_bot.asyncio.sleep', side_effect=asyncio.CancelledError)
class TestEndToEnd:

    @pytest.mark.asyncio
    async def test_full_cycle(self, mock_sleep, mock_send_message, mock_binance_client, mock_settings, message_queue, caplog):
        # 1. --- Configuración del Entorno de Prueba ---
        # Configurar la base de datos en memoria para esta prueba
        mock_settings.DATABASE_URL = "sqlite:///:memory:"
        mock_settings.TRADING_PAIRS = ['BTCUSDT'] # Limitar a un par para simplicidad
        
        # Inicializar la base de datos usando la URL mockeada
        database_manager.init_db()

        # Configurar mock de Binance
        mock_binance_client.return_value.get_historical_klines.return_value = pd.DataFrame({
            'timestamp': pd.to_datetime([f'2023-01-01 00:{i:02d}:00' for i in range(100)]),
            'open': [100 + i for i in range(100)],
            'high': [105 + i for i in range(100)],
            'low': [95 + i for i in range(100)],
            'close': [102 + i for i in range(100)],
            'volume': [1000 for _ in range(100)]
        })

        # 2. --- Ejecución del Ciclo ---
        execution_worker_task = asyncio.create_task(execution_worker_main())
        await asyncio.sleep(2)

        with pytest.raises(asyncio.CancelledError):
            await run_bot_main()
        
        await asyncio.sleep(5)

        # 3. --- Verificaciones ---
        decision_bytes = await message_queue.redis.blpop(mock_settings.REDIS_DECISION_QUEUE_NAME, timeout=5)
        assert decision_bytes is not None, "No se encontró ninguna decisión en la cola de Redis"
        
        assert "Procesando decisión:" in caplog.text
        assert "Ejecutando orden simulada:" in caplog.text
        
        with database_manager.get_db_session() as session:
            result = session.execute(text('SELECT * FROM operations')).fetchone()
            assert result is not None, "La operación no fue guardada en la base de datos"
            assert result.symbol == 'BTCUSDT'

        # 4. --- Limpieza ---
        execution_worker_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await execution_worker_task
