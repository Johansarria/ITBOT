
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from utils.alerta_manager import Alerter, SeverityLevel


@pytest.fixture(autouse=True)
def reset_singleton():
    Alerter._instance = None
    yield
    Alerter._instance = None


@pytest.mark.asyncio
async def test_not_configured_suppresses_alert():
    alerter = Alerter()  # no configure()
    with patch('utils.alerta_manager.send_telegram_message', new_callable=AsyncMock) as mock_send:
        await alerter.send_alert("k1", SeverityLevel.INFO, "Src", "Msg")
        mock_send.assert_not_awaited()


def test_format_message_without_details():
    alerter = Alerter()
    # Configure minimally to avoid side effects; we just call _format_message
    text = alerter._format_message(SeverityLevel.INFO, "Core", "All good", details=None)
    assert "Detalles Adicionales" not in text
    assert "INFO: Core" in text
    assert "All good" in text


def test_format_message_default_emoji_on_unknown_severity():
    alerter = Alerter()
    # Objeto no mapeado pero con atributo 'value' para no romper la lógica
    class Dummy:
        value = "UNKNOWN"
    text = alerter._format_message(Dummy(), "Core", "Ping")  # type: ignore[arg-type]
    assert text.startswith("📢 ")


@pytest.mark.asyncio
async def test_send_alert_handles_exception_and_not_update_last_alert():
    alerter = Alerter()
    bot = AsyncMock()
    alerter.configure(bot_instance=bot, chat_id=123)
    with patch('utils.alerta_manager.send_telegram_message', new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = RuntimeError("network down")
        await alerter.send_alert("net_err", SeverityLevel.ERROR, "Network", "Failing")
        # No registro de last_alerts al fallar
        assert "net_err" not in alerter._last_alerts


@pytest.mark.asyncio
async def test_format_message_fallback_when_json_dumps_raises_typeerror():
    alerter = Alerter()
    with patch('utils.alerta_manager.json.dumps', side_effect=TypeError("bad type")):
        text = alerter._format_message(SeverityLevel.WARNING, "Fmt", "x", details={"a": object()})
        # Fallback usa representación string en backticks
        assert "Detalles Adicionales" in text
        assert text.count("`") >= 2


@pytest.mark.asyncio
async def test_deduplication_within_epsilon_is_suppressed():
    alerter = Alerter()
    bot = AsyncMock()
    alerter.configure(bot_instance=bot, chat_id=1)
    key = "dup_eps"
    # Simular primer envío exitoso
    with patch('utils.alerta_manager.send_telegram_message', new_callable=AsyncMock) as mock_send:
        await alerter.send_alert(key, SeverityLevel.INFO, "Src", "First")
        assert mock_send.await_count == 1
    # Colocar last_alerts cerca del límite (dentro de epsilon)
    now = datetime.now()
    # Delta = silence - 75ms => (delta + epsilon 50ms) < silence => se suprime
    alerter._last_alerts[key] = now - alerter._silence_period + timedelta(milliseconds=75)
    with patch('utils.alerta_manager.send_telegram_message', new_callable=AsyncMock) as mock_send2:
        await alerter.send_alert(key, SeverityLevel.INFO, "Src", "Second")
        mock_send2.assert_not_awaited()
