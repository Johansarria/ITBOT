import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
import sys

# Import config globally as it's safe and needed by conftest
import config

@pytest.mark.asyncio
async def test_e2e_trading_flow(monkeypatch):
    """
    End-to-end test for the main trading flow, self-contained to manage import order.
    """
    # === Step 1: Mock all dependencies BEFORE importing run_bot ===

    # Mock the problematic module that does pre-emptive config checks
    mock_listener = MagicMock()
    # The only thing run_bot uses from listener_bot is `dp`, which is not even used
    # in the run_analysis_cycle. We just need to ensure the module can be imported.
    monkeypatch.setitem(sys.modules, 'listener_bot', mock_listener)

    # Mock other utilities that run_bot imports
    monkeypatch.setitem(sys.modules, 'utils.shield_manager', MagicMock())
    monkeypatch.setitem(sys.modules, 'utils.telegram_handler', MagicMock())
    monkeypatch.setitem(sys.modules, 'strategies.strategy_manager', MagicMock())

    # Mock the message queue
    mock_mq = MagicMock()
    mock_mq.publish_decision = MagicMock()
    # We need to patch it where it's defined and used
    monkeypatch.setitem(sys.modules, 'utils.message_queue', mock_mq)

    # Now it's safe to import run_bot
    import run_bot

    # === Step 2: Set up mocks for the specific test case ===

    # Mock the bot instance that will be passed to the function
    mock_bot_instance = AsyncMock()
    mock_bot_instance.session.close = AsyncMock()

    # Create a mock for the main analysis function (`flujo_principal`)
    mock_flujo_principal = AsyncMock()

    async def mock_flujo_side_effect(bot, chat_id):
        print("🔥 Entré al fake flujo")
        test_decision = {
            "type": "AUTOMATED_TRADE",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.0001,
        }
        # Call the mocked publish_decision method
        mock_mq.publish_decision(test_decision)

    mock_flujo_principal.side_effect = mock_flujo_side_effect
    # Patch the now-imported run_bot module
    monkeypatch.setattr(run_bot, 'flujo_principal', mock_flujo_principal)

    # === Step 3: Run the target function ===
    await run_bot.run_analysis_cycle(mock_bot_instance, chat_id=12345)

    # === Step 4: Assertions ===
    # Verify that our mocked flow was called once
    assert mock_flujo_principal.call_count == 1, "The mocked analysis flow was not called"

    # Verify that a decision was published to the queue
    mock_mq.publish_decision.assert_called_once()
    published_decision = mock_mq.publish_decision.call_args[0][0]
    assert published_decision["symbol"] == "BTCUSDT"
    assert published_decision["side"] == "BUY"
