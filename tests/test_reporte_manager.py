import pytest
import os
import importlib
import pandas as pd
from unittest.mock import patch, ANY, MagicMock

@pytest.fixture
def report_manager_setup(tmp_path, monkeypatch):
    """
    Sets up a clean environment for testing the reporte_manager.
    - Redirects REPO_PATH to a temporary directory.
    - Manually creates the subdirectory structure needed for tests.
    """
    temp_repo_path = tmp_path / "storage" / "reportes"

    monkeypatch.setattr('utils.reporte_manager.REPO_PATH', str(temp_repo_path))

    subdirs = ['diarios', 'semanales', 'mensuales', 'riesgo', 'operaciones', 'pendientes', 'descargados', 'kpis', 'journal']
    for subdir in subdirs:
        os.makedirs(os.path.join(str(temp_repo_path), subdir), exist_ok=True)

    return str(temp_repo_path)


# --- Tests for Synchronous Functions ---

from utils.reporte_manager import _is_safe_filename

@pytest.mark.parametrize("filename, expected", [
    # Positive cases
    ("report_2023.csv", True),
    ("my-report_1.txt", True),
    ("a_b-c.123", True),
    ("a\\b", True), # Backslash is a valid char on Linux

    # Negative cases
    ("", False),
    ("..", False),
    ("../etc/passwd", False),
    ("a/b", False), # Forward slash is a separator
    ("/a/b", False),
])
def test_is_safe_filename(filename, expected):
    """Test the _is_safe_filename helper function."""
    assert _is_safe_filename(filename) == expected


def test_guardar_reporte_csv(report_manager_setup):
    """Test saving a DataFrame report as a CSV."""
    from utils.reporte_manager import guardar_reporte

    base_path = report_manager_setup
    df = pd.DataFrame({'a': [1], 'b': [2]})

    with patch('utils.reporte_manager.datetime') as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2023-01-01_12-00-00"

        result = guardar_reporte(df, 'diario')

        expected_filename = "diario_2023-01-01_12-00-00.csv"

        # Check return message
        assert result is not None
        assert f"`{expected_filename}`" in result

        # Check that files were created in both locations
        # The directory should be plural 'diarios' now
        path_tipo = os.path.join(base_path, "diarios", expected_filename)
        path_pendiente = os.path.join(base_path, "pendientes", expected_filename)

        assert os.path.exists(path_tipo)
        assert os.path.exists(path_pendiente)

        # Check content
        saved_df = pd.read_csv(path_tipo)
        pd.testing.assert_frame_equal(df, saved_df)

def test_guardar_reporte_no_prompt(report_manager_setup):
    """Test guardar_reporte with preguntar_descarga=False."""
    from utils.reporte_manager import guardar_reporte

    df = pd.DataFrame({'a': [1]})
    result = guardar_reporte(df, 'operaciones', preguntar_descarga=False)
    assert result is None


def test_guardar_reporte_texto(report_manager_setup):
    """Test saving a text report."""
    from utils.reporte_manager import guardar_reporte_texto
    base_path = report_manager_setup
    content = "This is a test report."

    with patch('utils.reporte_manager.datetime') as mock_dt:
        mock_dt.now.return_value.strftime.return_value = "2023-01-01_13-00-00"
        result = guardar_reporte_texto(content, 'journal')

        expected_filename = "journal_2023-01-01_13-00-00.txt"
        assert f"`{expected_filename}`" in result

        path_tipo = os.path.join(base_path, "journal", expected_filename)
        path_pendiente = os.path.join(base_path, "pendientes", expected_filename)

        assert os.path.exists(path_tipo)
        with open(path_tipo, 'r') as f:
            assert f.read() == content

        assert os.path.exists(path_pendiente)
        with open(path_pendiente, 'r') as f:
            assert f.read() == content


def test_listar_reportes(report_manager_setup):
    """Test listing reports from a directory."""
    from utils.reporte_manager import listar_reportes
    base_path = report_manager_setup

    assert listar_reportes('pendientes') == []

    open(os.path.join(base_path, "pendientes", "b.csv"), 'w').close()
    open(os.path.join(base_path, "pendientes", "a.csv"), 'w').close()

    assert listar_reportes('pendientes') == ['a.csv', 'b.csv']


def test_mover_a_descargados(report_manager_setup):
    """Test moving a report from pendientes to descargados."""
    from utils.reporte_manager import mover_a_descargados
    base_path = report_manager_setup
    filename = "test_report.csv"
    path_origen = os.path.join(base_path, "pendientes", filename)
    path_destino = os.path.join(base_path, "descargados", filename)

    open(path_origen, 'w').close()

    result = mover_a_descargados(filename)
    assert "movido a 'descargados'" in result
    assert not os.path.exists(path_origen)
    assert os.path.exists(path_destino)


def test_mover_a_descargados_not_found(report_manager_setup):
    """Test moving a non-existent report."""
    from utils.reporte_manager import mover_a_descargados
    result = mover_a_descargados("not_found.csv")
    assert "No se encontró el reporte" in result


def test_obtener_reporte(report_manager_setup):
    """Test retrieving a report DataFrame."""
    from utils.reporte_manager import obtener_reporte
    base_path = report_manager_setup
    filename = "my_report.csv"
    path_pendiente = os.path.join(base_path, "pendientes", filename)

    df = pd.DataFrame({'x': [10, 20]})
    df.to_csv(path_pendiente, index=False)

    retrieved_df = obtener_reporte(filename)
    pd.testing.assert_frame_equal(df, retrieved_df)

    assert obtener_reporte("not_found.csv") is None


def test_generar_menu_reportes_disponibles(report_manager_setup):
    """Test the generation of the reports menu string."""
    from utils.reporte_manager import generar_menu_reportes_disponibles

    with patch('utils.reporte_manager.listar_reportes', return_value=[]):
        assert "No hay reportes pendientes" in generar_menu_reportes_disponibles()

    with patch('utils.reporte_manager.listar_reportes', return_value=['rep1.csv', 'rep2.csv']):
        menu = generar_menu_reportes_disponibles()
        assert "Reportes disponibles" in menu
        assert "1. rep1.csv" in menu
        assert "2. rep2.csv" in menu


def test_ignorar_reporte(report_manager_setup):
    """Test that ignorar_reporte calls mover_a_descargados."""
    from utils.reporte_manager import ignorar_reporte
    filename = "report_to_ignore.csv"

    with patch('utils.reporte_manager.mover_a_descargados') as mock_mover:
        ignorar_reporte(filename)
        mock_mover.assert_called_once_with(filename)


# --- Tests for Missing Coverage ---

def test_guardar_reporte_exception(report_manager_setup):
    """Test exception handling in guardar_reporte."""
    from utils.reporte_manager import guardar_reporte
    with patch('pandas.DataFrame.to_csv', side_effect=IOError("Disk full")):
        result = guardar_reporte(pd.DataFrame(), 'diario')
        assert result is None

def test_listar_reportes_exception(report_manager_setup):
    """Test exception handling in listar_reportes."""
    from utils.reporte_manager import listar_reportes
    with patch('os.listdir', side_effect=IOError("Permission denied")):
        result = listar_reportes('pendientes')
        assert result == []

def test_mover_a_descargados_unsafe(report_manager_setup):
    """Test mover_a_descargados with an unsafe filename."""
    from utils.reporte_manager import mover_a_descargados
    result = mover_a_descargados("../../../etc/passwd")
    assert "inválido" in result

def test_mover_a_descargados_exception(report_manager_setup):
    """Test exception handling in mover_a_descargados."""
    from utils.reporte_manager import mover_a_descargados
    open(os.path.join(report_manager_setup, "pendientes", "file.txt"), 'w').close()
    with patch('os.rename', side_effect=IOError("Error")):
        result = mover_a_descargados("file.txt")
        assert "Error al mover" in result

def test_obtener_reporte_unsafe(report_manager_setup):
    """Test obtener_reporte with an unsafe filename."""
    from utils.reporte_manager import obtener_reporte
    assert obtener_reporte("../../../etc/passwd") is None

def test_obtener_reporte_exception(report_manager_setup):
    """Test exception handling in obtener_reporte."""
    from utils.reporte_manager import obtener_reporte
    open(os.path.join(report_manager_setup, "pendientes", "file.csv"), 'w').close()
    with patch('pandas.read_csv', side_effect=Exception("Corrupt file")):
        assert obtener_reporte("file.csv") is None

def test_ignorar_reporte_unsafe(report_manager_setup):
    """Test ignorar_reporte with an unsafe filename."""
    from utils.reporte_manager import ignorar_reporte
    result = ignorar_reporte("../../../etc/passwd")
    assert "inválido" in result

def test_guardar_reporte_texto_exception(report_manager_setup):
    """Test exception handling in guardar_reporte_texto."""
    from utils.reporte_manager import guardar_reporte_texto
    with patch('builtins.open', side_effect=IOError("Disk full")):
        result = guardar_reporte_texto("content", 'journal')
        assert result is None

@pytest.mark.asyncio
async def test_generar_reporte_journal_save_error(mock_bot, report_manager_setup):
    """Test error handling when guardar_reporte_texto returns None in journal generation."""
    from utils.reporte_manager import generar_reporte_journal
    # Provide a DataFrame with all necessary columns to avoid KeyErrors
    df = pd.DataFrame([{
        'operation_id': 'op1', 'timestamp_open': pd.to_datetime('2023-01-01 10:00'),
        'timestamp_close': pd.to_datetime('2023-01-01 11:00'), 'symbol': 'BTCUSDT',
        'side': 'BUY', 'entry_price': 50000, 'exit_price': 51000,
        'take_profit': 51000, 'stop_loss': 49000, 'pnl_usdt': 100, 'pnl_percent': 1.0,
        'reason_open': 'Test Open', 'reason_close': 'Test Close', 'market_score_open': 0.8,
        'market_score_close': 0.7, 'risk_percent': 1, 'notes': 'A test note'
    }])
    with patch('utils.reporte_manager.get_operations_df', return_value=df), \
         patch('utils.reporte_manager.guardar_reporte_texto', return_value=None) as mock_guardar:
        await generar_reporte_journal(mock_bot, 12345, days=1)
        mock_guardar.assert_called_once()
        mock_bot.send_message.assert_any_call(12345, "❌ Ocurrió un error al guardar el diario de trading.")

@pytest.mark.asyncio
async def test_generar_reporte_journal_exception(mock_bot, report_manager_setup):
    """Test exception handling during journal generation."""
    from utils.reporte_manager import generar_reporte_journal
    error = Exception("DB Error")
    with patch('utils.reporte_manager.get_operations_df', side_effect=error):
        await generar_reporte_journal(mock_bot, 12345, days=1)
        mock_bot.send_message.assert_any_call(12345, f"❌ Error crítico al generar el diario de trading: {error}")

@pytest.mark.asyncio
async def test_generar_reporte_kpis_exception(mock_bot, report_manager_setup):
    """Test exception handling during KPI report generation."""
    from utils.reporte_manager import generar_reporte_kpis
    error = Exception("DB Error")
    with patch('utils.reporte_manager.get_operations_df', side_effect=error):
        await generar_reporte_kpis(mock_bot, 12345, days=1)
        mock_bot.send_message.assert_any_call(12345, f"❌ Error crítico al generar el reporte de KPIs: {error}")


# --- Tests for Asynchronous Functions ---

from unittest.mock import AsyncMock

@pytest.fixture
def mock_bot():
    """Fixture for a mock aiogram Bot with an async send_message method."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot

@pytest.mark.asyncio
async def test_generar_reporte_diario_no_file(mock_bot, report_manager_setup):
    """Test generar_reporte_diario when the operations file does not exist."""
    from utils.reporte_manager import generar_reporte_diario
    chat_id = 12345

    with patch('os.path.exists', return_value=False):
        result = await generar_reporte_diario(mock_bot, chat_id)
        assert result is None
        mock_bot.send_message.assert_called_once_with(chat_id, "❌ No se encontró el archivo de operaciones para generar el reporte.")

@pytest.mark.asyncio
async def test_generar_reporte_diario_no_ops_today(mock_bot, report_manager_setup):
    """Test generar_reporte_diario when there are no operations for the current day."""
    from utils.reporte_manager import generar_reporte_diario
    chat_id = 12345

    # Create a DF with an old date
    df = pd.DataFrame({'timestamp_open': [pd.to_datetime('2023-01-01')]})

    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_csv', return_value=df):
        result = await generar_reporte_diario(mock_bot, chat_id)
        assert result is None
        mock_bot.send_message.assert_called_once_with(chat_id, "ℹ️ No se encontraron operaciones en el día de hoy para generar un reporte.")

@pytest.mark.asyncio
async def test_generar_reporte_diario_happy_path(mock_bot, report_manager_setup):
    """Test the successful generation of a daily report."""
    from utils.reporte_manager import generar_reporte_diario
    chat_id = 12345

    # Create a DF with a current date
    df = pd.DataFrame({'timestamp_open': [pd.to_datetime('now')]})
    confirmation_msg = "✅ Reporte generado."

    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_csv', return_value=df), \
         patch('utils.reporte_manager.guardar_reporte', return_value=confirmation_msg) as mock_guardar:

        result = await generar_reporte_diario(mock_bot, chat_id)

        assert result == confirmation_msg
        mock_guardar.assert_called_once()
        mock_bot.send_message.assert_called_once_with(chat_id, confirmation_msg)

@pytest.mark.asyncio
async def test_generar_reporte_diario_exception(mock_bot, report_manager_setup):
    """Test critical error handling in generar_reporte_diario."""
    from utils.reporte_manager import generar_reporte_diario
    chat_id = 12345
    error = Exception("Test Error")

    with patch('os.path.exists', side_effect=error):
        result = await generar_reporte_diario(mock_bot, chat_id)
        assert result is None
        mock_bot.send_message.assert_called_once_with(chat_id, f"❌ Error crítico al generar el reporte diario: {error}")


@pytest.mark.asyncio
async def test_generar_reporte_journal_no_ops(mock_bot, report_manager_setup):
    """Test journal generation when there are no operations."""
    from utils.reporte_manager import generar_reporte_journal
    chat_id = 12345

    with patch('utils.reporte_manager.get_operations_df', return_value=pd.DataFrame()) as mock_get_df:
        await generar_reporte_journal(mock_bot, chat_id, days=7)

        mock_get_df.assert_called_once_with(days=7)
        assert mock_bot.send_message.call_count == 2
        mock_bot.send_message.assert_any_call(chat_id, "ℹ️ No hay operaciones registradas en los últimos 7 días.")

@pytest.mark.asyncio
async def test_generar_reporte_journal_happy_path(mock_bot, report_manager_setup):
    """Test successful journal generation."""
    from utils.reporte_manager import generar_reporte_journal
    chat_id = 12345

    journal_df = pd.DataFrame([{
        'operation_id': 'op1', 'timestamp_open': pd.to_datetime('2023-01-01 10:00'),
        'timestamp_close': pd.to_datetime('2023-01-01 11:00'), 'symbol': 'BTCUSDT',
        'side': 'BUY', 'entry_price': 50000, 'exit_price': 51000,
        'take_profit': 51000, 'stop_loss': 49000, 'pnl_usdt': 100, 'pnl_percent': 1.0,
        'reason_open': 'Test Open', 'reason_close': 'Test Close', 'market_score_open': 0.8,
        'market_score_close': 0.7, 'risk_percent': 1, 'notes': 'A test note'
    }])
    confirmation_msg = "✅ Journal generado."

    with patch('utils.reporte_manager.get_operations_df', return_value=journal_df) as mock_get_df, \
         patch('utils.reporte_manager.guardar_reporte_texto', return_value=confirmation_msg) as mock_guardar:

        await generar_reporte_journal(mock_bot, chat_id, days=7)

        mock_get_df.assert_called_once_with(days=7)
        mock_guardar.assert_called_once()

        args, _ = mock_guardar.call_args
        journal_content = args[0]
        assert "Diario de Trading" in journal_content
        assert "op1" in journal_content

        mock_bot.send_message.assert_any_call(chat_id, confirmation_msg)

@pytest.mark.asyncio
async def test_generar_reporte_kpis_no_ops(mock_bot, report_manager_setup):
    """Test KPI report generation when there are no operations."""
    from utils.reporte_manager import generar_reporte_kpis
    chat_id = 12345

    with patch('utils.reporte_manager.get_operations_df', return_value=pd.DataFrame()) as mock_get_df:
        await generar_reporte_kpis(mock_bot, chat_id, days=30)

        mock_get_df.assert_called_once_with(days=30)
        mock_bot.send_message.assert_any_call(chat_id, "ℹ️ No hay operaciones registradas en los últimos 30 días. No se puede generar el reporte de KPIs.")

@pytest.mark.asyncio
async def test_generar_reporte_kpis_happy_path(mock_bot, report_manager_setup):
    """Test successful KPI report generation."""
    from utils.reporte_manager import generar_reporte_kpis
    chat_id = 12345

    df = pd.DataFrame({'symbol': ['BTCUSDT']})
    pnl_data = {'total_pnl_usdt': 1000}
    trade_stats = {'total_trades': 10, 'winning_trades': 8, 'losing_trades': 2, 'win_rate': 80.0, 'profit_factor': 5.0, 'expectancy': 100, 'gross_profit': 1200, 'gross_loss': -200}
    max_drawdown = 5.0
    freq_duration = {'trades_per_day': 1.0, 'avg_trade_duration_minutes': 120}
    confirmation_msg = "✅ KPIs generados."

    with patch('utils.reporte_manager.get_operations_df', return_value=df) as mock_get_df, \
         patch('utils.reporte_manager.calculate_pnl', return_value=pnl_data) as mock_pnl, \
         patch('utils.reporte_manager.calculate_trade_stats', return_value=trade_stats) as mock_stats, \
         patch('utils.reporte_manager.calculate_max_drawdown', return_value=max_drawdown) as mock_mdd, \
         patch('utils.reporte_manager.calculate_trade_frequency_and_duration', return_value=freq_duration) as mock_freq, \
         patch('utils.reporte_manager.guardar_reporte_texto', return_value=confirmation_msg) as mock_guardar:

        await generar_reporte_kpis(mock_bot, chat_id, days=30)

        mock_pnl.assert_called_once_with(df)
        mock_stats.assert_called_once_with(df)

        mock_guardar.assert_called_once()
        mock_bot.send_message.assert_any_call(chat_id, confirmation_msg)

        content = mock_guardar.call_args[0][0]
        assert "1000.00 USDT" in content
        assert "80.00%" in content
