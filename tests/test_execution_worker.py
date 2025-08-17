import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import execution_worker

@pytest.mark.asyncio
async def test_process_decision_valid_and_risk_pass(monkeypatch):
    # Mock perform_pre_execution_risk_checks to always pass
    monkeypatch.setattr(
        execution_worker, "perform_pre_execution_risk_checks",
        AsyncMock(return_value=(True, ""))
    )
    # Mock evaluar_y_ejecutar_operacion to simulate execution
    monkeypatch.setattr(
        execution_worker, "evaluar_y_ejecutar_operacion",
        AsyncMock(return_value="Orden ejecutada correctamente")
    )
    # Mock log_decision_to_db to prevent actual DB connection
    monkeypatch.setattr("execution_worker.log_decision_to_db", MagicMock())
    decision = {
        "type": "MANUAL_TRADE",
        "symbol": "BTCUSDT",
        "side": "COMPRAR",
        "quantity": 0.01,
        "strategy_id": "SimpleTechnicalStrategy",
        "timestamp_decision": "2025-08-12T10:00:00",
        "analysis_score": 3,
        "take_profit": 1.5,
        "stop_loss": 0.5
    }
    await execution_worker.process_decision(decision)
    # If no exception, test passes

@pytest.mark.asyncio
async def test_process_decision_invalid_decision(monkeypatch, caplog):
    # Mock log_decision_to_db to prevent actual DB connection
    monkeypatch.setattr("execution_worker.log_decision_to_db", MagicMock())
    # No need to mock risk or execution, should fail before
    decision = {"type": "MANUAL_TRADE", "symbol": "BTCUSDT"} # Missing keys
    await execution_worker.process_decision(decision)
    assert any("Decisión inválida" in r for r in caplog.text.splitlines())

@pytest.mark.asyncio
async def test_process_decision_risk_fail(monkeypatch, caplog):
    monkeypatch.setattr(
        execution_worker, "perform_pre_execution_risk_checks",
        AsyncMock(return_value=(False, "Riesgo alto"))
    )
    # Mock log_decision_to_db to prevent actual DB connection
    monkeypatch.setattr("execution_worker.log_decision_to_db", MagicMock())
    decision = {
        "type": "MANUAL_TRADE",
        "symbol": "BTCUSDT",
        "side": "COMPRAR",
        "quantity": 0.01,
        "strategy_id": "SimpleTechnicalStrategy",
        "timestamp_decision": "2025-08-12T10:00:00"
    }
    await execution_worker.process_decision(decision)
    assert any("Decisión rechazada por riesgo" in r for r in caplog.text.splitlines())
