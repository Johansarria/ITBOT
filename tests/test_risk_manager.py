import pytest

from risk_manager import RiskConfig, AccountState, RiskManager


@pytest.fixture
def base_account():
    return AccountState(capital=10000.0, peak_balance_today=10000.0)


def test_can_open_trade_exposure_limit(base_account):
    cfg = RiskConfig(max_exposure_pct=0.1)
    rm = RiskManager(cfg, base_account)

    # can open a trade within exposure
    assert rm.can_open_trade('BTCUSD', 500.0)

    # opening large trade exceeding exposure
    assert not rm.can_open_trade('BTCUSD', 2000.0)


def test_concurrent_trades_limit(base_account):
    cfg = RiskConfig(max_concurrent_trades=2)
    rm = RiskManager(cfg, base_account)
    rm.register_new_position('A', 100)
    rm.register_new_position('B', 100)
    assert not rm.can_open_trade('C', 50)


def test_daily_drawdown_limit(base_account):
    cfg = RiskConfig(max_daily_drawdown=0.01)  # 1%
    base_account.realized_pnl_today = -200.0
    base_account.peak_balance_today = 10000.0
    rm = RiskManager(cfg, base_account)
    # allowed_drawdown = -100. So -200 < -100 -> should be denied
    assert not rm.can_open_trade('X', 10)


def test_stop_loss_take_profit_evaluation(base_account):
    cfg = RiskConfig(max_trade_loss=50.0, max_trade_profit=200.0)
    rm = RiskManager(cfg, base_account)
    res = rm.evaluate_trade_risk(entry_price=100.0, current_price=49.0, quantity=1)
    assert res['stop_loss_hit'] is True
    assert res['take_profit_hit'] is False


def test_kill_switch_liquidation(base_account):
    cfg = RiskConfig()
    rm = RiskManager(cfg, base_account)
    rm.register_new_position('A', 100)
    rm.register_new_position('B', 200)
    rm.engage_kill_switch()
    assert not rm.can_open_trade('C', 10)
    liquidated = rm.liquidate_all()
    assert 'A' in liquidated and 'B' in liquidated
# tests/test_risk_manager.py

import pytest
import pandas as pd
from datetime import datetime, timedelta
import sys
from freezegun import freeze_time
from unittest.mock import patch, mock_open, AsyncMock
import json

from config import settings


@pytest.fixture
def mock_file_paths(tmp_path):
    """Fixture to mock the file paths for operations and thresholds."""
    ops_path = tmp_path / "operaciones.csv"
    threshold_path = tmp_path / "thresholds.json"
    with patch('utils.risk_manager.OPERATIONS_LOG', str(ops_path)), \
         patch('utils.risk_manager.UMBRAL_FILE', str(threshold_path)):
        yield {"ops": ops_path, "thresholds": threshold_path}

@pytest.fixture(autouse=True)
def mock_state_manager():
    """Fixture que mockea el StateManager para aislar los tests de riesgo."""
    # Estado inicial por defecto para cada test
    mock_state = {
        "risk_manager": {
            "riesgo_actual": settings.DEFAULT_RISK_PERCENTAGE / 100.0,
            "riesgo_forzado": False,
            "tiempo_riesgo_forzado": None,
            "ganancias_riesgo_forzado": 0.0,
            "operaciones_riesgo_forzado": [],
            "recordatorio_riesgo_forzado_hoy": True,
        }
    }

    # Usar un diccionario en memoria para simular el archivo JSON
    state_store = {"risk_manager": mock_state["risk_manager"].copy()}

    def get_state(module, key=None, default_value=None):
        if key:
            return state_store.get(module, {}).get(key, default_value)
        return state_store.get(module, default_value)

    def update_module_state(module, updates):
        if module not in state_store:
            state_store[module] = {}
        state_store[module].update(updates)

    with patch('utils.risk_manager.StateManager') as mock_sm_class:
        mock_sm_instance = mock_sm_class.return_value
        mock_sm_instance.get_state.side_effect = get_state
        mock_sm_instance.update_module_state.side_effect = update_module_state
        yield

# --- Tests para las funciones de risk_manager ---

def test_obtener_riesgo_actual_initial():
    from utils import risk_manager
    assert risk_manager.obtener_riesgo_actual() == settings.DEFAULT_RISK_PERCENTAGE / 100

def test_riesgo_forzado_activo_initial():
    from utils import risk_manager
    assert not risk_manager.riesgo_forzado_activo()

def test_activar_riesgo_forzado():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(5.0)
    assert risk_manager.obtener_riesgo_actual() == 0.05
    assert risk_manager.riesgo_forzado_activo()
    state = risk_manager._get_risk_state()
    assert state.get("tiempo_riesgo_forzado") is not None
    assert state.get("recordatorio_riesgo_forzado_hoy") is True

def test_registrar_resultado_operacion():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(1.0) # Activar para que registre
    risk_manager.registrar_resultado_operacion(1.5)
    risk_manager.registrar_resultado_operacion(-0.5)
    state = risk_manager._get_risk_state()
    assert state.get("ganancias_riesgo_forzado") == 1.0
    assert state.get("operaciones_riesgo_forzado") == [1.5, -0.5]

def test_duracion_riesgo_forzado():
    from utils import risk_manager
    assert risk_manager.duracion_riesgo_forzado() == "0h"
    with freeze_time("2025-01-01 12:00:00"):
        risk_manager.activar_riesgo_forzado(5.0)
    with freeze_time("2025-01-01 15:00:00"):
        assert risk_manager.duracion_riesgo_forzado() == "3h"

def test_ganancias_durante_riesgo_forzado():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(1.0)
    risk_manager.registrar_resultado_operacion(2.0)
    risk_manager.registrar_resultado_operacion(-1.0)
    assert risk_manager.ganancias_durante_riesgo_forzado() == 1.0

def test_operaciones_en_riesgo_forzado():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(1.0)
    risk_manager.registrar_resultado_operacion(2.0)
    risk_manager.registrar_resultado_operacion(-1.0)
    risk_manager.registrar_resultado_operacion(0.5)
    stats = risk_manager.operaciones_en_riesgo_forzado()
    assert stats["total"] == 3
    assert stats["positivas"] == 2
    assert stats["negativas"] == 1

def test_calcular_probabilidad_ganancia_perdida_empty():
    from utils import risk_manager
    prob = risk_manager.calcular_probabilidad_ganancia_perdida()
    assert prob["ganar"] == 50.0
    assert prob["perder"] == 50.0

def test_calcular_probabilidad_ganancia_perdida_with_data():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(1.0)
    risk_manager.registrar_resultado_operacion(1.0)
    risk_manager.registrar_resultado_operacion(2.0)
    risk_manager.registrar_resultado_operacion(-0.5)
    risk_manager.registrar_resultado_operacion(0.0)
    prob = risk_manager.calcular_probabilidad_ganancia_perdida()
    assert prob["ganar"] == 50.0
    assert prob["perder"] == 50.0

def test_restaurar_riesgo_automatico():
    from utils import risk_manager
    risk_manager.activar_riesgo_forzado(10.0)
    risk_manager.registrar_resultado_operacion(5.0)
    risk_manager.restaurar_riesgo_automatico()
    state = risk_manager._get_risk_state()
    assert risk_manager.obtener_riesgo_actual() == settings.DEFAULT_RISK_PERCENTAGE / 100
    assert not risk_manager.riesgo_forzado_activo()
    assert state.get("tiempo_riesgo_forzado") is None
    assert state.get("ganancias_riesgo_forzado") == 0.0
    assert state.get("operaciones_riesgo_forzado") == []
    assert state.get("recordatorio_riesgo_forzado_hoy") is True

def test_recordar_riesgo_forzado():
    from utils import risk_manager
    assert risk_manager.recordar_riesgo_forzado() is True
    risk_manager.desactivar_recordatorio_hoy()
    assert not risk_manager.recordar_riesgo_forzado()

def test_obtener_riesgo_ajustado_por_ml():
    from utils import risk_manager

    # Mock _OPTIMIZED_THRESHOLDS for consistent testing
    with patch('utils.risk_manager._OPTIMIZED_THRESHOLDS', {
        "umbral_alto": 0.9,
        "umbral_medio": 0.7,
        "umbral_bajo": 0.5
    }):
        # Test cases based on the new logic
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.95, riesgo_base=10.0) == 15.0 # score > umbral_alto (1.5x)
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.80, riesgo_base=10.0) == 10.0 # umbral_medio < score <= umbral_alto (1.0x)
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.60, riesgo_base=10.0) == 7.5  # umbral_bajo < score <= umbral_medio (0.75x)
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.40, riesgo_base=10.0) == 5.0  # score <= umbral_bajo (0.5x)
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.70, riesgo_base=10.0) == 10.0 # Edge case: score == umbral_medio
        assert risk_manager.obtener_riesgo_ajustado_por_ml(score=0.50, riesgo_base=10.0) == 7.5  # Edge case: score == umbral_bajo

def test_obtener_riesgo_ajustado():
    from utils import risk_manager

    # Casos de prueba con diferentes combinaciones de métricas
    riesgo_base = 10.0

    # Caso 1: Todas las métricas en valores medios
    assert risk_manager.obtener_riesgo_ajustado(
        score=0.5, volatilidad=0.5, drawdown=0.5, señales_técnicas=0.5, riesgo_base=riesgo_base
    ) == pytest.approx(10.0)

    # Caso 2: Score alto, drawdown bajo, volatilidad y señales medias
    assert risk_manager.obtener_riesgo_ajustado(
        score=0.9, volatilidad=0.5, drawdown=0.2, señales_técnicas=0.5, riesgo_base=riesgo_base
    ) > 10.0

    # Caso 3: Score bajo, drawdown alto, volatilidad y señales bajas
    assert risk_manager.obtener_riesgo_ajustado(
        score=0.2, volatilidad=0.3, drawdown=0.8, señales_técnicas=0.2, riesgo_base=riesgo_base
    ) < 10.0

    # Caso 4: Todas las métricas en valores extremos
    assert risk_manager.obtener_riesgo_ajustado(
        score=1.0, volatilidad=1.0, drawdown=0.0, señales_técnicas=1.0, riesgo_base=riesgo_base
    ) > 15.0

    assert risk_manager.obtener_riesgo_ajustado(
        score=0.0, volatilidad=0.0, drawdown=1.0, señales_técnicas=0.0, riesgo_base=riesgo_base
    ) < 5.0

# --- Tests for Permission Checks ---

@pytest.mark.asyncio
async def test_verificar_permiso_de_operacion_max_exposure():
    """
    Test que verifica que la operación se bloquea si se supera la exposición máxima.
    """
    from utils.risk_manager import verificar_permiso_de_operacion

    # Mockear el cliente de Binance y sus respuestas
    mock_client = AsyncMock()
    mock_client.get_asset_balance.return_value = {"free": "1000.0"} # Balance de 1000 USDT

    # Hay una posición abierta de 250 USDT. Capital total = 1000 (balance) + 250 (abierta) = 1250
    # Exposición actual = 250 / 1250 = 20%
    open_positions = pd.DataFrame([{'symbol': 'BTCUSDT', 'size_usdt': 250.0}])

    # El límite de exposición es 30%
    # Si intentamos abrir una nueva operación de 150 USDT:
    # Nueva exposición total = (250 + 150) / 1250 = 400 / 1250 = 32% > 30% -> Bloqueado
    new_trade_size_fail = 150.0

    with patch('utils.risk_manager.get_open_positions', return_value=open_positions), \
         patch('utils.risk_manager.get_binance_client', return_value=mock_client), \
         patch('utils.risk_manager.settings.RISK_MAX_EXPOSURE_PCT', 30.0), \
         patch('utils.risk_manager._get_daily_pnl_pct', new_callable=AsyncMock, return_value=0.0):

        allowed, reason = await verificar_permiso_de_operacion(new_trade_size_usdt=new_trade_size_fail)
        assert not allowed
        assert "exposición máxima" in reason

    # Caso donde es permitido. Nueva operación de 50 USDT
    # Nueva exposición total = (250 + 50) / 1250 = 300 / 1250 = 24% < 30% -> Permitido
    new_trade_size_allowed = 50.0
    with patch('utils.risk_manager.get_open_positions', return_value=open_positions), \
         patch('utils.risk_manager.get_binance_client', return_value=mock_client), \
         patch('utils.risk_manager.settings.RISK_MAX_EXPOSURE_PCT', 30.0), \
         patch('utils.risk_manager._get_daily_pnl_pct', new_callable=AsyncMock, return_value=0.0), \
         patch('utils.risk_manager.settings.RISK_MAX_CONCURRENT_TRADES', 5):

        allowed, reason = await verificar_permiso_de_operacion(new_trade_size_usdt=new_trade_size_allowed)
        assert allowed, f"La razón del fallo fue: {reason}"


@pytest.mark.asyncio
async def test_verificar_permiso_de_operacion_system_paused():
    """Test que la operación se bloquea si el sistema está en pausa global."""
    from utils.risk_manager import verificar_permiso_de_operacion

    with patch('utils.risk_manager.StateManager') as mock_sm_class:
        mock_sm_instance = mock_sm_class.return_value
        def get_state_side_effect(module, key=None, default_value=None):
            if module == "system" and key == "is_paused":
                return True
            return None

        mock_sm_instance.get_state.side_effect = get_state_side_effect

        allowed, reason = await verificar_permiso_de_operacion()
        assert not allowed
        assert "Sistema en pausa global" in reason

@pytest.mark.asyncio
async def test_verificar_permiso_de_operacion_drawdown_limit():
    """
    Test que la operación se bloquea si se supera el drawdown diario y que
    se activa la pausa diaria.
    """
    from utils.risk_manager import verificar_permiso_de_operacion

    with patch('utils.risk_manager._get_daily_pnl_pct', new_callable=AsyncMock, return_value=-11.0), \
         patch('utils.risk_manager.settings.RISK_MAX_DAILY_DRAWDOWN_PCT', 10.0), \
         patch('utils.risk_manager.get_open_positions', return_value=pd.DataFrame()), \
         patch('utils.risk_manager.get_binance_client', new_callable=AsyncMock): # Mock other checks

        with patch('utils.risk_manager.StateManager') as mock_sm_class:
            mock_sm_instance = mock_sm_class.return_value
            mock_sm_instance.get_state.return_value = None # No existing pause

            allowed, reason = await verificar_permiso_de_operacion()

            assert not allowed
            assert "drawdown diario" in reason

            # Verificar que la pausa diaria fue activada
            mock_sm_instance.set_state.assert_called_once()
            args, kwargs = mock_sm_instance.set_state.call_args
            assert args[0] == "system"
            assert args[1] == "drawdown_pause_until"
            assert isinstance(datetime.fromisoformat(args[2]), datetime)

@pytest.mark.asyncio
async def test_verificar_permiso_de_operacion_concurrent_trades_limit():
    """Test que la operación se bloquea si se supera el límite de trades concurrentes."""
    from utils.risk_manager import verificar_permiso_de_operacion

    open_positions = pd.DataFrame([{}, {}, {}])

    with patch('utils.risk_manager.get_open_positions', return_value=open_positions), \
         patch('utils.risk_manager.settings.RISK_MAX_CONCURRENT_TRADES', 3), \
         patch('utils.risk_manager.StateManager') as mock_sm:

        mock_sm.return_value.get_state.return_value = None # Simula que no hay pausas activas

        allowed, reason = await verificar_permiso_de_operacion()

        assert not allowed
        assert "operaciones concurrentes" in reason

@pytest.mark.asyncio
async def test_verificar_permiso_de_operacion_all_clear():
    """Test que la operación es permitida cuando no se incumple ninguna regla."""
    from utils.risk_manager import verificar_permiso_de_operacion

    mock_client = AsyncMock()
    mock_client.get_asset_balance.return_value = {"free": "1000.0"}

    with patch('utils.risk_manager.StateManager') as mock_sm, \
         patch('utils.risk_manager.get_open_positions', return_value=pd.DataFrame()), \
         patch('utils.risk_manager.get_binance_client', return_value=mock_client), \
         patch('utils.risk_manager._get_daily_pnl_pct', new_callable=AsyncMock, return_value=0.0):

        mock_sm.return_value.get_state.return_value = None # No pauses

        allowed, reason = await verificar_permiso_de_operacion(new_trade_size_usdt=100.0)

        assert allowed
        assert reason == "Permitido"

@pytest.mark.asyncio
async def test_perform_pre_execution_risk_checks():
    """Test the basic pre-execution risk checks."""
    from utils.risk_manager import perform_pre_execution_risk_checks

    # Test case with a valid decision
    valid_decision = {"symbol": "BTCUSDT", "decision": "BUY"}
    allowed, reason = await perform_pre_execution_risk_checks(valid_decision)
    assert allowed
    assert reason == "Permitido"

    # Test case with a missing symbol
    invalid_decision_symbol = {"decision": "BUY"}
    allowed, reason = await perform_pre_execution_risk_checks(invalid_decision_symbol)
    assert not allowed
    assert "Símbolo de operación no especificado" in reason

    # Test case with an invalid decision string
    invalid_decision_action = {"symbol": "BTCUSDT", "decision": "WAIT"}
    allowed, reason = await perform_pre_execution_risk_checks(invalid_decision_action)
    assert not allowed
    assert "Decisión inválida" in reason

# --- Tests for File I/O Functions ---

@pytest.mark.asyncio
async def test_get_daily_pnl_pct_real_and_unrealized(mock_file_paths):
    """
    Test que _get_daily_pnl_pct calcula correctamente el PnL combinado
    de operaciones cerradas hoy y posiciones abiertas.
    """
    from utils.risk_manager import _get_daily_pnl_pct
    from datetime import timezone

    # 1. Setup: Datos de prueba
    with freeze_time("2025-08-14 12:00:00 UTC"):
        # Operaciones cerradas (en CSV)
        closed_ops_df = pd.DataFrame([
            # Cerrada hoy, PnL = +10 USDT
            {'timestamp_open': "2025-08-14T09:00:00Z", 'timestamp_close': "2025-08-14T10:00:00Z", 'pnl_usdt': 10.0},
            # Cerrada ayer, debe ser ignorada
            {'timestamp_open': "2025-08-13T09:00:00Z", 'timestamp_close': "2025-08-13T10:00:00Z", 'pnl_usdt': 50.0},
        ])
        closed_ops_df.to_csv(mock_file_paths["ops"], index=False)

        # Posiciones abiertas
        open_positions = pd.DataFrame([
            # Abierta, PnL no realizado = (51000 - 50000) * 0.01 = +10 USDT
            {'symbol': 'BTCUSDT', 'entry_price': 50000.0, 'cantidad_token_operada': 0.01, 'side': 'LONG', 'size_usdt': 500.0},
            # Abierta, PnL no realizado = (3100 - 3000) * 0.5 = +50 USDT
            {'symbol': 'ETHUSDT', 'entry_price': 3100.0, 'cantidad_token_operada': 0.5, 'side': 'SHORT', 'size_usdt': 1550.0},
        ])

        # Mock de Binance
        mock_client = AsyncMock()
        mock_client.get_all_tickers.return_value = [
            {'symbol': 'BTCUSDT', 'price': '51000.0'},
            {'symbol': 'ETHUSDT', 'price': '3000.0'}
        ]
        # Capital: 1000 (balance) + 500 (BTC) + 1550 (ETH) = 3050 USDT
        mock_client.get_asset_balance.return_value = {'free': '1000.0'}

        # 2. Ejecución
        with patch('utils.risk_manager.get_open_positions', return_value=open_positions), \
             patch('utils.risk_manager.get_binance_client', return_value=mock_client):

            pnl_pct = await _get_daily_pnl_pct()

            # 3. Aserción
            # PnL Realizado = +10 USDT
            # PnL No Realizado = +10 (BTC) + 50 (ETH) = +60 USDT
            # PnL Total = 10 + 60 = 70 USDT
            # Capital Total = 1000 (balance) + 500 (BTC) + 1550 (ETH) = 3050 USDT
            # Porcentaje esperado = (70 / 3050) * 100 = 2.295%
            assert pnl_pct == pytest.approx(2.295, abs=1e-3)

def test_cargar_umbrales_optimizado(mock_file_paths):
    """Test loading thresholds from a JSON file."""
    from utils.risk_manager import cargar_umbrales_optimizado

    # Test file not found (should return defaults)
    defaults = cargar_umbrales_optimizado()
    assert "umbral_alto" in defaults

    # Test successful load
    thresholds = {"umbral_alto": 0.95, "umbral_medio": 0.75, "umbral_bajo": 0.55}
    with open(mock_file_paths["thresholds"], "w") as f:
        json.dump(thresholds, f)
    loaded = cargar_umbrales_optimizado()
    assert loaded == thresholds

    # Test invalid JSON
    mock_file_paths["thresholds"].write_text("{invalid json")
    defaults_again = cargar_umbrales_optimizado()
    assert defaults_again["umbral_alto"] != 0.95 # Should be default, not the one from the last successful read

def test_guardar_umbrales_optimizado(mock_file_paths):
    """Test saving thresholds to a JSON file."""
    from utils.risk_manager import guardar_umbrales_optimizado

    thresholds = {"test_key": "test_value"}
    guardar_umbrales_optimizado(thresholds)

    with open(mock_file_paths["thresholds"], "r") as f:
        saved_data = json.load(f)

    assert saved_data == thresholds
