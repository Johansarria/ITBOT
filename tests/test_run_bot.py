import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import run_bot
from aiogram import Bot

@pytest.mark.asyncio
async def test_flujo_principal_escudo_danger(monkeypatch):
    # Mock verificar_condiciones_mercado para devolver DANGER
    monkeypatch.setattr(
        run_bot, "verificar_condiciones_mercado",
        AsyncMock(return_value={"status": "DANGER", "reason": "Mercado peligroso"})
    )
    # Mock send_message para no enviar nada real
    monkeypatch.setattr(run_bot, "send_message", AsyncMock())
    bot = MagicMock(spec=Bot)
    chat_id = 12345
    symbol = "BTCUSDT" # Añadir un símbolo
    await run_bot.flujo_principal_por_activo(bot, chat_id, symbol)
    run_bot.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_flujo_principal_analisis_y_decision(monkeypatch):
    # Mock verificar_condiciones_mercado para devolver SAFE
    monkeypatch.setattr(
        run_bot, "verificar_condiciones_mercado",
        AsyncMock(return_value={"status": "SAFE", "reason": "Mercado seguro"})
    )

    # Mock StrategyManager y su método analyze_all_strategies
    mock_manager = MagicMock()
    mock_manager.analyze_all_strategies = AsyncMock(return_value={
        "results": {"SimpleTechnicalStrategy": {"decision": "COMPRAR", "score": 3, "symbol": "BTCUSDT"}},
        "best_strategy": "SimpleTechnicalStrategy",
        "best_decision": "COMPRAR",
        "best_score": 3
    })
    monkeypatch.setattr(run_bot, "StrategyManager", MagicMock(return_value=mock_manager))

    # Mock get_historical_klines
    monkeypatch.setattr(run_bot.technical_analysis, "get_historical_klines", AsyncMock(return_value=MagicMock(empty=False)))
    # Mock mq.publish_decision
    monkeypatch.setattr(run_bot.mq, "publish_decision", MagicMock(return_value=True))
    # Mock send_message
    monkeypatch.setattr(run_bot, "send_message", AsyncMock())
    bot = MagicMock(spec=Bot)
    chat_id = 12345
    symbol = "BTCUSDT" # Añadir un símbolo
    await run_bot.flujo_principal_por_activo(bot, chat_id, symbol)
    run_bot.mq.publish_decision.assert_called()
