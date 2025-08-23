import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock
from binance.exceptions import BinanceAPIException

def generate_klines_data(num_klines: int, base_price: float, volatility_factor: float = 0.01):
    klines = []
    current_price = base_price
    for i in range(num_klines):
        open_price = current_price
        high_price = open_price * (1 + volatility_factor * (0.5 + i/num_klines))
        low_price = open_price * (1 - volatility_factor * (0.5 + i/num_klines))
        close_price = open_price * (1 + volatility_factor * (0.5 - i/num_klines))
        high_price = max(open_price, close_price, high_price)
        low_price = min(open_price, close_price, low_price)
        klines.append([
            i * 1000, str(open_price), str(high_price), str(low_price), str(close_price),
            "100", (i + 1) * 1000, "0", "0", "0", "0", "0"
        ])
        current_price = close_price
    return klines

@pytest.fixture(autouse=True)
def mock_shield_state_manager():
    """Patches the state_manager INSTANCE within shield_manager and ensures clean state for each test."""
    state_store = {}

    def get_state(module, key=None, default=None):
        if key is not None:
            return state_store.get(module, {}).get(key, default)
        return state_store.get(module, {})

    def update_module_state(module, updates):
        if module not in state_store:
            state_store[module] = {}
        state_store[module].update(updates)

    mock_manager = MagicMock()
    mock_manager.get_state.side_effect = get_state
    mock_manager.update_module_state.side_effect = update_module_state

    with patch('utils.shield_manager.state_manager', mock_manager):
        # Reset state before each test that uses this fixture
        state_store["shield_manager"] = {
            "escudo_activo": False,
            "tipo_escudo": "ninguno",
            "fuente_escudo": None,
            "activado_at": None,
            "desactivado_at": None,
        }
        yield mock_manager

@pytest.fixture
def mock_send_message():
    with patch('utils.shield_manager.send_message', new_callable=AsyncMock) as mock_sm:
        yield mock_sm

@pytest.fixture
def mock_bot_instance():
    return AsyncMock()

# --- Tests for shield_manager functions ---

@pytest.mark.asyncio
async def test_activar_escudo_conservador(mock_bot_instance, mock_send_message):
    from utils import shield_manager
    await shield_manager.activar_escudo(mock_bot_instance, 123, tipo="conservador", fuente="manual")
    assert shield_manager.escudo_activo() == "conservador"
    mock_send_message.assert_called_once()
    assert "ESCUDO CONSERVADOR ACTIVADO por el usuario" in mock_send_message.call_args[0][2]

@pytest.mark.asyncio
async def test_desactivar_escudo(mock_bot_instance, mock_send_message, mock_shield_state_manager):
    from utils import shield_manager
    mock_shield_state_manager.update_module_state("shield_manager", {"escudo_activo": True, "tipo_escudo": "conservador"})
    mock_send_message.reset_mock()
    await shield_manager.desactivar_escudo(mock_bot_instance, 123, fuente="manual")
    assert shield_manager.escudo_activo() == "ninguno"
    mock_send_message.assert_called_once()
    assert "ESCUDO DESACTIVADO por el usuario" in mock_send_message.call_args[0][2]

@pytest.mark.asyncio
async def test_verificar_condiciones_mercado_volatilidad_alta(mock_bot_instance, mock_send_message):
    from utils import shield_manager
    mock_client = AsyncMock() # Changed to AsyncMock
    mock_client.get_klines.return_value = generate_klines_data(15, 100, 0.05)
    with patch('utils.shield_manager.get_binance_client', return_value=mock_client):
        result = await shield_manager.verificar_condiciones_mercado(mock_bot_instance, 123)
        assert result["status"] == "DANGER"
        assert shield_manager.escudo_activo() == "extremo" # Changed expected value
        mock_send_message.assert_called_once()

@pytest.mark.asyncio
async def test_verificar_condiciones_mercado_estable_sin_escudo_previo(mock_bot_instance, mock_send_message):
    from utils import shield_manager
    mock_client = AsyncMock() # Changed to AsyncMock
    mock_client.get_klines.return_value = generate_klines_data(15, 100, 0.001)
    with patch('utils.shield_manager.get_binance_client', return_value=mock_client):
        result = await shield_manager.verificar_condiciones_mercado(mock_bot_instance, 123)
        assert result["status"] == "SAFE"
        assert shield_manager.escudo_activo() == "ninguno"
        mock_send_message.assert_not_called()

@pytest.mark.asyncio
async def test_verificar_condiciones_mercado_estable_con_escudo_previo(mock_bot_instance, mock_send_message, mock_shield_state_manager):
    from utils import shield_manager
    mock_shield_state_manager.update_module_state("shield_manager", {
        "escudo_activo": True, "tipo_escudo": "volatilidad_alta", "fuente_escudo": "bot"
    })
    mock_client = AsyncMock() # Changed to AsyncMock
    mock_client.get_klines.return_value = generate_klines_data(15, 100, 0.001)
    with patch('utils.shield_manager.get_binance_client', return_value=mock_client):
        result = await shield_manager.verificar_condiciones_mercado(mock_bot_instance, 123)
        assert result["status"] == "SAFE"
        assert shield_manager.escudo_activo() == "ninguno"
        mock_send_message.assert_called_once()

@pytest.mark.asyncio
async def test_verificar_condiciones_mercado_api_error(mock_bot_instance, mock_send_message):
    from utils import shield_manager
    mock_client = AsyncMock() # Changed to AsyncMock
    mock_client.get_klines.side_effect = BinanceAPIException(response=MagicMock(), status_code=400, text='{"code":-1000, "msg":"API Error"}')
    with patch('utils.shield_manager.get_binance_client', return_value=mock_client):
        result = await shield_manager.verificar_condiciones_mercado(mock_bot_instance, 123)
        assert result["status"] == "DANGER"
        assert shield_manager.escudo_activo() == "extremo"
        mock_send_message.assert_called_once()

def test_obtener_estado_escudo_texto_inactivo():
    from utils import shield_manager
    _, status_text = shield_manager.obtener_estado_escudo()
    assert "✅ INACTIVO" == status_text