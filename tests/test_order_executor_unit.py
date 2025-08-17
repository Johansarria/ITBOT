import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import utils.order_executor as order_executor

@pytest.mark.asyncio
async def test_calcular_cantidad_operar_escudo():
    # Prueba los diferentes ajustes de escudo
    base = 1000
    riesgo = 0.01
    assert order_executor.calcular_cantidad_operar(base, riesgo, escudo="ninguno") == 10.0
    assert order_executor.calcular_cantidad_operar(base, riesgo, escudo="conservador") == 5.0
    assert order_executor.calcular_cantidad_operar(base, riesgo, escudo="noticias_negativas") == 2.5
    assert order_executor.calcular_cantidad_operar(base, riesgo, escudo="extremo") == 0.0
    assert order_executor.calcular_cantidad_operar(base, riesgo, escudo="agresivo") == 15.0

@pytest.mark.asyncio
async def test_registrar_operacion_crea_archivo(tmp_path, monkeypatch):
    # Forzar OPERATIONS_LOG a un archivo temporal
    monkeypatch.setattr(order_executor, "OPERATIONS_LOG", str(tmp_path / "ops.csv"))
    # Mock send_message para no enviar nada real
    monkeypatch.setattr(order_executor, "send_message", AsyncMock())
    # Mock state_manager para no afectar estado global
    class DummyStateManager:
        def get_state(self, *a, **k): return 0
        def set_state(self, *a, **k): pass
    monkeypatch.setattr(order_executor, "state_manager", DummyStateManager())
    # Mock log_operation_to_db to prevent actual DB connection
    monkeypatch.setattr("utils.order_executor.log_operation_to_db", MagicMock())
    data = {"a": 1, "b": 2}
    await order_executor.registrar_operacion(MagicMock(), 123, data)
    # Verifica que el archivo se creó y contiene los datos
    import pandas as pd
    df = pd.read_csv(tmp_path / "ops.csv")
    assert df.iloc[0]["a"] == 1
    assert df.iloc[0]["b"] == 2

@pytest.mark.asyncio
async def test_mostrar_estado_riesgo_no_envia(monkeypatch):
    # Si bot_instance o chat_id es None, no debe enviar mensaje
    monkeypatch.setattr(order_executor, "send_message", AsyncMock())
    await order_executor.mostrar_estado_riesgo(None, 123)
    await order_executor.mostrar_estado_riesgo(MagicMock(), None)
    order_executor.send_message.assert_not_awaited()
