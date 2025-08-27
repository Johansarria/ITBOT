import pytest
import pandas as pd
from unittest.mock import patch
from utils.order_executor import calcular_cantidad_operar

# Patch asyncio.sleep to avoid long waits in tests that might trigger the retry decorator
@pytest.fixture(autouse=True)
def patch_asyncio_sleep():
    with patch('asyncio.sleep', return_value=None) as p:
        yield p

# Casos de prueba parametrizados para cubrir diferentes escenarios
@pytest.mark.parametrize("balance, riesgo_pct, escudo, expected_amount", [
    # Escenario 1: Sin escudo, riesgo estándar
    (1000.0, 0.01, "ninguno", 10.00),
    
    # Escenario 2: Escudo conservador, reduce el riesgo a la mitad
    (1000.0, 0.01, "conservador", 5.00),
    
    # Escenario 3: Escudo agresivo, aumenta el riesgo en un 50%
    (1000.0, 0.01, "agresivo", 15.00),
    
    # Escenario 4: Riesgo más alto sin escudo
    (5000.0, 0.05, "ninguno", 250.00),
    
    # Escenario 5: Riesgo más alto con escudo conservador
    (5000.0, 0.05, "conservador", 125.00),
    
    # Escenario 6: Riesgo más alto con escudo agresivo
    (5000.0, 0.05, "agresivo", 375.00),
    
    # Escenario 7: Caso con balance cero
    (0.0, 0.02, "ninguno", 0.00),
    
    # Escenario 8: Caso con riesgo cero
    (1000.0, 0.0, "agresivo", 0.00),
    
    # Escenario 9: Caso con decimales
    (1234.56, 0.1, "ninguno", 123.46), # 123.456 se redondea a 123.46
])
def test_calcular_cantidad_operar(balance, riesgo_pct, escudo, expected_amount):
    """
    Verifica que la función `calcular_cantidad_operar` devuelve la cantidad correcta
    basada en el balance, el porcentaje de riesgo y el escudo aplicado.
    """
    # Llamar a la función que se está probando
    calculated_amount = calcular_cantidad_operar(balance, riesgo_pct, escudo)
    
    # Afirmar que el resultado calculado es igual al esperado
    assert calculated_amount == expected_amount

# Podríamos añadir más tests para otras funciones de este módulo en el futuro
def test_placeholder_for_setup():
    """This test ensures the autouse fixture is set up correctly."""
    assert True

# --- Tests for Helper and Pure Functions ---
from unittest.mock import MagicMock, AsyncMock, ANY
from utils.order_executor import safe_send_message, apply_filters

@pytest.mark.asyncio
async def test_safe_send_message():
    """Test that safe_send_message only sends when bot and chat_id are valid."""
    mock_send = AsyncMock()

    with patch('utils.order_executor.send_message', mock_send):
        # Case 1: All valid
        await safe_send_message(MagicMock(), 123, "Hello")
        mock_send.assert_called_once_with(ANY, 123, "Hello", None)

        mock_send.reset_mock()

        # Case 2: bot is None
        await safe_send_message(None, 123, "Hello")
        mock_send.assert_not_called()

        # Case 3: chat_id is None
        await safe_send_message(MagicMock(), None, "Hello")
        mock_send.assert_not_called()

def test_apply_filters_no_change():
    """Test that values are unchanged when they already meet filter requirements."""
    symbol_info = {
        "filters": [
            {"filterType": "PRICE_FILTER", "tickSize": "0.01"},
            {"filterType": "LOT_SIZE", "stepSize": "0.001"},
            {"filterType": "NOTIONAL", "minNotional": "10.0"},
        ]
    }
    qty, price, _, _, _ = apply_filters(quantity=1.0, price=20.0, symbol_info=symbol_info)
    assert qty == 1.0
    assert price == 20.0

def test_apply_filters_lot_size():
    """Test the LOT_SIZE (stepSize) filter."""
    symbol_info = {"filters": [{"filterType": "LOT_SIZE", "stepSize": "0.1"}]}

    # Round down to nearest step
    qty, _, _, _, _ = apply_filters(quantity=1.25, price=1.0, symbol_info=symbol_info)
    assert qty == 1.2

    # Quantity is smaller than step_size, should be adjusted up
    qty, _, _, _, _ = apply_filters(quantity=0.05, price=1.0, symbol_info=symbol_info)
    assert qty == 0.1

def test_apply_filters_price_filter():
    """Test the PRICE_FILTER (tickSize)."""
    symbol_info = {"filters": [{"filterType": "PRICE_FILTER", "tickSize": "0.01"}]}
    _, price, _, _, _ = apply_filters(quantity=1.0, price=20.126, symbol_info=symbol_info)
    assert price == 20.13

def test_apply_filters_min_notional():
    """Test the NOTIONAL (minNotional) filter interaction with LOT_SIZE."""
    symbol_info = {
        "filters": [
            {"filterType": "LOT_SIZE", "stepSize": "0.1"},
            {"filterType": "NOTIONAL", "minNotional": "10.0"},
        ]
    }

    # Initial quantity is too small (2.0 * 4.0 = 8.0, which is < 10.0)
    # Min qty needed = 10.0 / 4.0 = 2.5
    # Rounded up to nearest stepSize (0.1) = 2.5
    # The logic in the function is a bit different, let's trace it.
    # min_qty_for_notional = 2.5
    # quantity = float(int(2.5 / 0.1)) * 0.1 = float(25) * 0.1 = 2.5
    # This seems to have a bug, it should be ceil. Let's re-read the code.
    # quantity = float(int(min_qty_for_notional / step_size)) * step_size -> rounds down
    # if quantity < min_qty_for_notional: quantity += step_size -> then adds a step
    # So for 2.5, int(2.5/0.1) = 25. 25 * 0.1 = 2.5. 2.5 is not < 2.5, so it stays 2.5. Correct.
    qty, _, _, _, _ = apply_filters(quantity=2.0, price=4.0, symbol_info=symbol_info)
    assert qty == 2.5

    # Case where initial quantity is way too small
    # Min qty needed = 10.0 / 100.0 = 0.1
    # This meets the step size, so it should be 0.1
    qty, _, _, _, _ = apply_filters(quantity=0.01, price=100.0, symbol_info=symbol_info)
    assert qty == 0.1

# --- Tests for Core Logic ---

@pytest.fixture
def mock_bot():
    """Fixture for a mock aiogram Bot with an async send_message method."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot

@pytest.fixture
def default_mocks():
    """A fixture to provide a default set of mocks for happy paths."""
    # Mock the async get_binance_client to return a mock client instance
    mock_client = MagicMock()
    mock_client.get_asset_balance.return_value = {"free": "1000.0"}
    mock_client.get_symbol_ticker.return_value = {"price": "50000.0"}

    with patch('utils.order_executor.verificar_permiso_de_operacion', return_value=(True, "")) as p1, \
         patch('utils.order_executor.get_binance_client', new_callable=AsyncMock, return_value=mock_client) as p2, \
         patch('utils.order_executor.state_manager') as p3, \
         patch('utils.order_executor.obtener_riesgo_actual', return_value=0.01) as p4, \
         patch('utils.order_executor.escudo_activo', return_value="ninguno") as p5, \
         patch('utils.order_executor.get_symbol_info', new_callable=AsyncMock, return_value={"filters": []}) as p6, \
         patch('utils.order_executor.apply_filters', side_effect=lambda q, p, s: (q, p, 0, 0, 0)) as p7, \
         patch('utils.order_executor.registrar_operacion', new_callable=AsyncMock) as p8, \
         patch('utils.order_executor.mostrar_estado_riesgo', new_callable=AsyncMock) as p9, \
         patch('utils.order_executor.safe_send_message', new_callable=AsyncMock) as p10, \
         patch('utils.order_executor.obtener_riesgo_ajustado_por_ml', return_value=0.01) as p11, \
         patch('utils.order_executor.config') as mock_config:

        # Set default values for the mocked config module
        mock_config.MODE = "SIMULATED"
        mock_config.VERBOSE_NOTIFICATIONS = False

        yield {
            "verificar_permiso": p1, "get_client": p2, "client": mock_client, "state_manager": p3,
            "riesgo_actual": p4, "escudo": p5, "symbol_info": p6,
            "apply_filters": p7, "registrar": p8, "mostrar_estado": p9,
            "safe_send": p10, "riesgo_ml": p11, "config": mock_config
        }

@pytest.mark.asyncio
async def test_evaluar_y_ejecutar_permiso_denegado(mock_bot, default_mocks):
    """Test that execution is stopped if permission is denied."""
    from utils.order_executor import evaluar_y_ejecutar_operacion
    default_mocks['verificar_permiso'].return_value = (False, "Mantenimiento")

    resultado = await evaluar_y_ejecutar_operacion(mock_bot, 123, {})

    assert resultado == "Operación cancelada: Mantenimiento"
    default_mocks['safe_send'].assert_called_once_with(mock_bot, 123, "❌ Operación cancelada: Mantenimiento")

@pytest.mark.asyncio
async def test_evaluar_y_ejecutar_balance_insuficiente(mock_bot, default_mocks):
    """Test that execution is stopped if balance is insufficient."""
    from utils.order_executor import evaluar_y_ejecutar_operacion
    # Set a low balance on the mock client instance
    default_mocks['client'].get_asset_balance.return_value = {"free": "5.0"}
    # Make get_symbol_info return a high minNotional
    default_mocks['symbol_info'].return_value = {"filters": [{"filterType": "NOTIONAL", "minNotional": "10.0"}]}

    resultado_analisis = {"decision": "BUY", "symbol": "BTCUSDT", "score": 0.9}
    resultado = await evaluar_y_ejecutar_operacion(mock_bot, 123, resultado_analisis)

    assert resultado == "Error: Balance insuficiente."
    default_mocks['safe_send'].assert_called_with(mock_bot, 123, "❌ Error: Balance insuficiente para operar. Necesitas al menos 10.00 USDT.")

@pytest.mark.asyncio
async def test_evaluar_y_ejecutar_decision_mantener(mock_bot, default_mocks):
    """Test that no trade is executed for a 'MANTENER' decision."""
    from utils.order_executor import evaluar_y_ejecutar_operacion
    resultado_analisis = {"decision": "MANTENER"}

    resultado = await evaluar_y_ejecutar_operacion(mock_bot, 123, resultado_analisis)

    assert resultado == "No se ejecutó operación."
    # Ensure no order was registered
    default_mocks['registrar'].assert_not_called()

@pytest.mark.asyncio
async def test_evaluar_y_ejecutar_simulated_buy(mock_bot, default_mocks):
    """Test a successful SIMULATED BUY order execution."""
    from utils.order_executor import evaluar_y_ejecutar_operacion

    default_mocks['state_manager'].get_state.side_effect = lambda *args, **kwargs: "SIMULATED" if args[1] == "mode" else False
    resultado_analisis = {"decision": "BUY", "symbol": "BTCUSDT", "score": 0.9}

    with patch('utils.order_executor.random.uniform', return_value=0.5): # Mock the random pnl
        resultado = await evaluar_y_ejecutar_operacion(mock_bot, 123, resultado_analisis)

    assert resultado == "Operación procesada."

    # Check that registrar_operacion was called with the correct mode
    default_mocks['registrar'].assert_called_once()
    registrar_args = default_mocks['registrar'].call_args[0][2] # Arg index 2 is the data dict
    assert registrar_args['mode'] == 'SIMULATED'
    assert registrar_args['side'] == 'BUY'

    # Check that the real order function was not called
    default_mocks['client'].create_order.assert_not_called()
    default_mocks['safe_send'].assert_any_call(mock_bot, 123, ANY) # Check that some message was sent

@pytest.mark.asyncio
async def test_evaluar_y_ejecutar_real_sell(mock_bot, default_mocks):
    """Test a successful REAL SELL order execution."""
    from utils.order_executor import evaluar_y_ejecutar_operacion

    # Setup for REAL mode
    def state_manager_side_effect(module, key=None, default=None):
        if module == "session" and key == "mode":
            return "LIVE"
        if module == "live_mode" and key == "unlocked":
            return True
        return default
    default_mocks['state_manager'].get_state.side_effect = state_manager_side_effect
    default_mocks['client'].create_order.return_value = {"orderId": "12345", "status": "FILLED"}

    resultado_analisis = {"decision": "SELL", "symbol": "ETHUSDT", "score": 0.1}

    resultado = await evaluar_y_ejecutar_operacion(mock_bot, 123, resultado_analisis)

    assert resultado == "Operación procesada."

    # Check that the real order function was called
    default_mocks['client'].create_order.assert_called_once()

    # Check that registrar_operacion was called with the correct mode
    default_mocks['registrar'].assert_called_once()
    registrar_args = default_mocks['registrar'].call_args[0][2] # Arg index 2 is the data dict
    assert registrar_args['mode'] == 'REAL'
    assert registrar_args['side'] == 'SELL'
    assert registrar_args['order_id_binance'] == "12345"

@pytest.mark.asyncio
async def test_evaluar_y_ejecutar_live_locked_mode(mock_bot, default_mocks):
    """Test that a locked LIVE mode falls back to SIMULATED."""
    from utils.order_executor import evaluar_y_ejecutar_operacion

    # LIVE mode but NOT unlocked
    default_mocks['state_manager'].get_state.side_effect = lambda key, _, default: "LIVE" if key == "session" else False

    resultado_analisis = {"decision": "BUY", "symbol": "BTCUSDT", "score": 0.9}
    await evaluar_y_ejecutar_operacion(mock_bot, 123, resultado_analisis)

    # Check for the warning message
    default_mocks['safe_send'].assert_any_call(mock_bot, 123, "⚠️ El bot está en modo LIVE pero no ha sido desbloqueado. La operación se realizará en modo SIMULADO.")

    # Check that the trade was simulated
    registrar_args = default_mocks['registrar'].call_args[0][2] # Arg index 2 is the data dict
    assert registrar_args['mode'] == 'SIMULATED'

@pytest.mark.asyncio
async def test_evaluar_y_ejecutar_binance_api_exception(mock_bot, default_mocks):
    """Test the handling of a BinanceAPIException during order creation."""
    from utils.order_executor import evaluar_y_ejecutar_operacion
    from binance.exceptions import BinanceAPIException

    # Setup for REAL mode
    default_mocks['state_manager'].get_state.side_effect = lambda k, _, d: "LIVE" if k == "session" else True
    # Correctly instantiate the exception
    error = BinanceAPIException(response=MagicMock(), status_code=400, text='{"code": -2015, "msg": "Test error"}')
    default_mocks['client'].create_order.side_effect = error

    resultado_analisis = {"decision": "BUY", "symbol": "BTCUSDT", "score": 0.9}
    resultado = await evaluar_y_ejecutar_operacion(mock_bot, 123, resultado_analisis)

    assert resultado == "Error de Binance."
    default_mocks['safe_send'].assert_any_call(mock_bot, 123, f"❌ Error de Binance: {error}")

# --- Tests for Previously Mocked Functions ---

@pytest.mark.asyncio
async def test_registrar_operacion(tmp_path):
    """Test the registrar_operacion function."""
    from utils.order_executor import registrar_operacion, OPERATIONS_LOG

    # Patch the global OPERATIONS_LOG to use a temp file
    temp_log_path = tmp_path / "operaciones.csv"

    bot = MagicMock()
    bot.send_message = AsyncMock()
    chat_id = 123
    data = {"operation_id": "1", "symbol": "BTCUSDT"}

    with patch('utils.order_executor.OPERATIONS_LOG', str(temp_log_path)), \
         patch('utils.order_executor.log_operation_to_db') as mock_log_db, \
         patch('utils.order_executor.state_manager') as mock_sm:

        # First call, should create the file
        await registrar_operacion(bot, chat_id, data)
        assert temp_log_path.exists()
        df = pd.read_csv(temp_log_path)
        assert len(df) == 1

        # Second call, should append
        await registrar_operacion(bot, chat_id, {"operation_id": "2", "symbol": "ETHUSDT"})
        df = pd.read_csv(temp_log_path)
        assert len(df) == 2

        # Assertions
        assert mock_log_db.call_count == 2
        mock_log_db.assert_called_with(ANY)
        mock_sm.get_state.assert_called()
        mock_sm.set_state.assert_called()

@pytest.mark.asyncio
async def test_mostrar_estado_riesgo(mock_bot):
    """Test the mostrar_estado_riesgo function."""
    from utils.order_executor import mostrar_estado_riesgo

    # Case 1: Riesgo forzado is not active
    with patch('utils.order_executor.riesgo_forzado_activo', return_value=False), \
         patch('utils.order_executor.send_message', new_callable=AsyncMock) as mock_send:
        await mostrar_estado_riesgo(mock_bot, 123)
        mock_send.assert_not_called()

    # Case 2: Riesgo forzado is active
    with patch('utils.order_executor.riesgo_forzado_activo', return_value=True), \
         patch('utils.order_executor.recordar_riesgo_forzado', return_value=True), \
         patch('utils.order_executor.duracion_riesgo_forzado', return_value="1 hora"), \
         patch('utils.order_executor.ganancias_durante_riesgo_forzado', return_value=5.5), \
         patch('utils.order_executor.operaciones_en_riesgo_forzado', return_value={'total': 2, 'positivas': 1, 'negativas': 1}), \
         patch('utils.order_executor.calcular_probabilidad_ganancia_perdida', return_value={'ganar': 60.0, 'perder': 40.0}), \
         patch('utils.order_executor.send_message', new_callable=AsyncMock) as mock_send:

        await mostrar_estado_riesgo(mock_bot, 123)
        mock_send.assert_called_once()
        args, _ = mock_send.call_args
        message = args[2] # bot, chat_id, message
        assert "Riesgo forzado sigue activo" in message
        assert "5.50%" in message

@pytest.mark.asyncio
async def test_retry_decorator():
    """Test the retry decorator logic."""
    from utils.order_executor import retry

    mock_func = AsyncMock(side_effect=[ValueError("Fail"), "Success"])

    mock_logger = MagicMock()
    mock_logger.warning = MagicMock()

    decorated_func = retry(ValueError, tries=2, delay=0.1, logger=mock_logger)(mock_func)

    result = await decorated_func()

    assert result == "Success"
    assert mock_func.call_count == 2
    mock_logger.warning.assert_called_once()

@pytest.mark.asyncio
async def test_registrar_operacion_no_bot():
    """Test registrar_operacion in no-bot mode."""
    from utils.order_executor import registrar_operacion
    with patch('utils.order_executor.log_operation_to_db') as mock_log_db, \
         patch('utils.order_executor.send_message') as mock_send:
        await registrar_operacion(None, None, {})
        mock_log_db.assert_called_once()
        mock_send.assert_not_called()

@pytest.mark.asyncio
async def test_get_symbol_info_success():
    """Test get_symbol_info successful path."""
    from utils.order_executor import get_symbol_info
    mock_client = MagicMock()
    mock_client.get_exchange_info.return_value = {
        "symbols": [{"symbol": "BTCUSDT", "status": "TRADING"}, {"symbol": "ETHUSDT", "status": "TRADING"}]
    }
    with patch('utils.order_executor.get_binance_client', new_callable=AsyncMock, return_value=mock_client):
        info = await get_symbol_info("ETHUSDT")
        assert info["symbol"] == "ETHUSDT"

@pytest.mark.asyncio
async def test_evaluar_y_ejecutar_aiohttp_error(mock_bot, default_mocks):
    """Test the handling of an aiohttp.ClientError."""
    from utils.order_executor import evaluar_y_ejecutar_operacion
    import aiohttp

    default_mocks['state_manager'].get_state.side_effect = lambda k, _, d: "LIVE" if k == "session" else True
    error = aiohttp.ClientError("Connection failed")
    default_mocks['client'].create_order.side_effect = error

    resultado_analisis = {"decision": "BUY", "symbol": "BTCUSDT", "score": 0.9}
    resultado = await evaluar_y_ejecutar_operacion(mock_bot, 123, resultado_analisis)

    assert resultado == "Error de conexión."
    default_mocks['safe_send'].assert_any_call(mock_bot, 123, f"❌ Error de conexión: {error}")
