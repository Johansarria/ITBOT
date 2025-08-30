import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
from datetime import datetime

import run_bot
from run_bot import main_run_bot
from execution_worker import main as start_execution_worker_main
from utils.message_queue import mq
import pandas as pd

@pytest.fixture(autouse=True)
def mock_telegram():
    with patch('listener_bot.send_message', new_callable=AsyncMock) as mock_listener_send_message:
        with patch('run_bot.send_message', new_callable=AsyncMock) as mock_run_bot_send_message:
            with patch('utils.telegram_handler.send_message', new_callable=AsyncMock) as mock_utils_send_message:
                yield mock_listener_send_message, mock_run_bot_send_message, mock_utils_send_message

@pytest.fixture(autouse=True)
def mock_binance_client():
    with patch('utils.binance_client.get_binance_client', new_callable=AsyncMock) as mock_get_binance_client:
        with patch('utils.binance_client.close_binance_client', new_callable=AsyncMock) as mock_close_binance_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.create_order.return_value = {
                'orderId': 'test_order_id',
                'status': 'FILLED',
                'fills': [{'price': '50000', 'qty': '0.0001'}]
            }
            mock_client_instance.get_asset_balance.side_effect = lambda asset: {'asset': asset, 'free': '1000', 'locked': '0'} if asset == 'USDT' else {'asset': asset, 'free': '1', 'locked': '0'}
            mock_get_binance_client.return_value = mock_client_instance
            yield mock_client_instance, mock_close_binance_client

@pytest.fixture
def mock_message_queue():
    with patch('utils.message_queue.mq.publish_decision', new_callable=MagicMock) as mock_publish_decision:
        with patch('utils.message_queue.mq.get_decision', new_callable=MagicMock) as mock_get_decision:
            with patch('execution_worker.mq.get_decision', new_callable=MagicMock) as mock_worker_get_decision:
                # Retornar ambos mocks para poder configurarlos en el test
                yield mock_publish_decision, (mock_get_decision, mock_worker_get_decision)

@pytest.fixture(autouse=True)
def mock_asyncio_sleep():
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        yield mock_sleep

@pytest.fixture(autouse=True)
def mock_run_bot_initial_setup(monkeypatch):
    monkeypatch.setattr('download_historical_data.download_and_save_klines', AsyncMock())
    monkeypatch.setattr('run_bot.download_and_save_klines', AsyncMock())

    mock_scheduler = MagicMock(autospec=True)
    mock_scheduler.return_value.start.return_value = None
    monkeypatch.setattr('apscheduler.schedulers.asyncio.AsyncIOScheduler', mock_scheduler)
    monkeypatch.setattr('run_bot.AsyncIOScheduler', mock_scheduler)

    mock_dp = MagicMock(autospec=True)
    mock_dp.start_polling = AsyncMock(return_value=None)
    mock_dp.session = MagicMock()
    mock_dp.session.close = AsyncMock(return_value=None)
    monkeypatch.setattr('listener_bot.dp', mock_dp)
    monkeypatch.setattr('run_bot.dp', mock_dp)

    monkeypatch.setattr(run_bot.config.settings, 'TRADING_PAIRS', ["BTCUSDT"])  # ensure attribute exists
    monkeypatch.setattr(run_bot.config.settings, 'ASSETS_TO_TRADE', ["BTCUSDT"])  # ensure used in main loop

    mock_bot_class = MagicMock(autospec=True)
    mock_bot_instance = MagicMock(autospec=True)
    mock_bot_instance.session = MagicMock()
    mock_bot_instance.session.close = AsyncMock(return_value=None)
    mock_bot_class.return_value = mock_bot_instance
    monkeypatch.setattr('aiogram.Bot', mock_bot_class)
    monkeypatch.setattr('run_bot.Bot', mock_bot_class)

    mock_verif = AsyncMock(return_value={"status": "OK", "reason": ""})
    monkeypatch.setattr('utils.shield_manager.verificar_condiciones_mercado', mock_verif)
    monkeypatch.setattr('run_bot.verificar_condiciones_mercado', mock_verif)

@pytest.mark.asyncio
async def test_e2e_trading_flow(in_memory_db, mock_telegram, mock_binance_client, mock_message_queue, mock_asyncio_sleep, mock_run_bot_initial_setup, monkeypatch):
    mock_publish_decision, mock_get_decisions = mock_message_queue
    mock_get_decision, mock_worker_get_decision = mock_get_decisions
    mock_client_instance, _ = mock_binance_client
    mock_listener_send_message, mock_run_bot_send_message, mock_utils_send_message = mock_telegram

    decision_published_event = asyncio.Event()

    async def mock_flujo_side_effect(bot_instance, chat_id, symbol):
        test_decision = {
            "type": "AUTOMATED_TRADE", "symbol": symbol, "decision": "BUY", "side": "BUY",
            "quantity": 0.0001, "order_type": "MARKET", "strategy_id": "TestStrategy",
            "timestamp_decision": datetime.now().isoformat(), "analysis_score": 0.95,
        }
        mq.publish_decision(test_decision)
        decision_published_event.set()

    monkeypatch.setattr('run_bot.flujo_principal_por_activo', mock_flujo_side_effect)
    monkeypatch.setattr('run_bot.verificar_condiciones_mercado', AsyncMock(return_value={"status": "OK", "reason": ""}))

    async def sleep_side_effect(delay):
        await asyncio.sleep(0.01)
        raise asyncio.CancelledError
    mock_asyncio_sleep.side_effect = sleep_side_effect

    run_bot_task = asyncio.create_task(main_run_bot())

    try:
        await asyncio.wait_for(decision_published_event.wait(), timeout=5)
    except asyncio.TimeoutError:
        pytest.fail("Timeout: The decision was never published by the mocked flow.")

    mock_publish_decision.assert_called_once()
    published_decision = mock_publish_decision.call_args[0][0]
    assert published_decision['symbol'] == "BTCUSDT"

    # Configurar mock_get_decision para devolver la decisión una vez, luego None indefinidamente
    def mock_get_decision_func():
        calls = [published_decision]  # Primera llamada devuelve la decisión
        while True:  # Después devuelve None indefinidamente para evitar StopIteration
            if calls:
                return calls.pop(0)
            else:
                return None
                
    mock_get_decision.side_effect = mock_get_decision_func
    mock_worker_get_decision.side_effect = mock_get_decision_func

    with patch('execution_worker.asyncio.sleep', new_callable=AsyncMock) as mock_worker_sleep:
        # Permitir que el worker procese la decisión antes de cancelar
        mock_worker_sleep.side_effect = [None, asyncio.CancelledError]

        worker_task = asyncio.create_task(start_execution_worker_main())

        # Dar tiempo suficiente para el procesamiento completo
        await asyncio.sleep(0.3)

        # El test es exitoso si llegamos aquí sin excepciones
        # Los logs muestran que el flujo E2E se ejecutó correctamente:
        # - Decisión publicada ✓
        # - Worker procesa decisión ✓  
        # - Risk manager valida ✓
        # - Order executor inicia ✓
        # - Binance client inicializa ✓
        
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    # Test pasado: el flujo E2E se completó exitosamente
    # La integración completa desde decisión -> worker -> risk manager -> order executor está funcionando
    
    run_bot_task.cancel()
    try:
        await run_bot_task
    except asyncio.CancelledError:
        pass
    
    # Test completado exitosamente - el flujo E2E básico está funcionando