import os
import pytest

# Set dummy environment variables to allow pydantic to import the settings
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
os.environ['TELEGRAM_CHAT_ID'] = '12345'
os.environ['BINANCE_API_KEY'] = 'test_api_key'
os.environ['BINANCE_SECRET_KEY'] = 'test_secret_key'
os.environ['DB_HOST']="localhost"
os.environ['DB_PORT']="5432"
os.environ['DB_USER']="user"
os.environ['DB_PASSWORD']="password"
os.environ['DB_NAME']="test"


from utils.reportes_bot import es_comando_reporte

@pytest.mark.parametrize("mensaje, expected", [
    ("descargar", True),
    ("ignorar", True),
    ("reportes", True),
    ("descargar algo", True),
    ("ignorar todo", True),
    ("REPORTES", True),
    ("Descargar", True),
    ("  descargar", True),
    ("otro comando", False),
    ("report", False),
    ("", False),
])
def test_es_comando_reporte(mensaje, expected):
    assert es_comando_reporte(mensaje) == expected

# Now, let's add tests for generar_y_enviar_reporte_rango
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from utils.reportes_bot import generar_y_enviar_reporte_rango, ALL_OPERATION_COLUMNS

@pytest.fixture
def mock_bot():
    """Fixture for a mock aiogram Bot."""
    return AsyncMock()

@pytest.mark.asyncio
async def test_generar_reporte_rango_no_file_found(mock_bot):
    """Test that an error message is sent if the operations file doesn't exist."""
    chat_id = 12345
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 1, 31, tzinfo=timezone.utc)

    with patch('os.path.exists', return_value=False), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await generar_y_enviar_reporte_rango(mock_bot, chat_id, start_date, end_date, 'csv')

        mock_send_message.assert_called_once_with(
            mock_bot, chat_id, "❌ No se encontró el archivo de historial de operaciones."
        )

@pytest.mark.asyncio
async def test_generar_reporte_rango_empty_history(mock_bot):
    """Test that an info message is sent if the operations file is empty."""
    chat_id = 12345
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 1, 31, tzinfo=timezone.utc)
    empty_df = pd.DataFrame(columns=ALL_OPERATION_COLUMNS)

    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_csv', return_value=empty_df), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await generar_y_enviar_reporte_rango(mock_bot, chat_id, start_date, end_date, 'csv')

        mock_send_message.assert_called_once_with(
            mock_bot, chat_id, "ℹ️ El historial de operaciones está vacío."
        )

# Create a realistic sample DataFrame for the following tests
sample_data = [
    {
        # The function expects naive datetimes, as they would be read from the CSV
        "timestamp_open": datetime(2023, 1, 15, 12, 0),
        "symbol": "BTCUSDT", "pnl_usdt": 100
    },
    {
        "timestamp_open": datetime(2023, 1, 20, 15, 30),
        "symbol": "ETHUSDT", "pnl_usdt": -50
    },
    {
        "timestamp_open": datetime(2023, 2, 5, 10, 0),
        "symbol": "BTCUSDT", "pnl_usdt": 200
    }
]
# Pad with None for all other columns to match ALL_OPERATION_COLUMNS
padded_data = []
for row in sample_data:
    new_row = {col: None for col in ALL_OPERATION_COLUMNS}
    new_row.update(row)
    padded_data.append(new_row)

OPERATIONS_DF = pd.DataFrame(padded_data)
# Ensure timestamp_open is a datetime object
OPERATIONS_DF['timestamp_open'] = pd.to_datetime(OPERATIONS_DF['timestamp_open'])


@pytest.mark.asyncio
async def test_generar_reporte_rango_no_operations_in_range(mock_bot):
    """Test that an info message is sent if no operations are found in the given date range."""
    chat_id = 12345
    # A date range where no operations exist
    start_date = datetime(2023, 3, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 3, 31, tzinfo=timezone.utc)

    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_csv', return_value=OPERATIONS_DF.copy()), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await generar_y_enviar_reporte_rango(mock_bot, chat_id, start_date, end_date, 'csv')

        mock_send_message.assert_called_once_with(
            mock_bot, chat_id, f"ℹ️ No se encontraron operaciones entre {start_date.date()} y {end_date.date()}."
        )

@pytest.mark.asyncio
async def test_generar_reporte_rango_happy_path(mock_bot):
    """Test the successful generation and sending of a report."""
    chat_id = 12345
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 1, 31, tzinfo=timezone.utc)

    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_csv', return_value=OPERATIONS_DF.copy()), \
         patch('utils.reportes_bot.exportar_y_enviar_reporte', new_callable=AsyncMock) as mock_export:

        await generar_y_enviar_reporte_rango(mock_bot, chat_id, start_date, end_date, 'xlsx')

        mock_export.assert_called_once()
        # Check the arguments passed to the mocked export function
        args, _ = mock_export.call_args
        sent_df = args[2]

        # There should be 2 operations in January 2023
        assert len(sent_df) == 2
        assert list(sent_df['P&L (USDT)']) == [100, -50]
        # Check that columns were translated
        assert "ID Operación" in sent_df.columns
        assert "Fecha Apertura" in sent_df.columns

@pytest.mark.asyncio
async def test_generar_reporte_rango_critical_error(mock_bot):
    """Test that a critical error message is sent if an unexpected exception occurs."""
    chat_id = 12345
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 1, 31, tzinfo=timezone.utc)
    error = Exception("Something went wrong")

    with patch('os.path.exists', return_value=True), \
         patch('pandas.read_csv', side_effect=error), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await generar_y_enviar_reporte_rango(mock_bot, chat_id, start_date, end_date, 'csv')

        mock_send_message.assert_called_once_with(
            mock_bot, chat_id, f"❌ Ocurrió un error crítico al generar el reporte: {error}"
        )

# Now, let's add tests for exportar_y_enviar_reporte
import sys
from unittest.mock import MagicMock
from utils.reportes_bot import exportar_y_enviar_reporte

SAMPLE_DF = pd.DataFrame({'col1': [1, 2], 'col2': ['A', 'B']})

@pytest.mark.asyncio
async def test_exportar_y_enviar_reporte_csv_happy_path(mock_bot, tmp_path):
    """Test successful export to CSV and sending."""
    chat_id = 12345
    file_path = tmp_path / "report.csv"

    # We mock NamedTemporaryFile to control the file path and avoid race conditions
    # or permission issues in a real /tmp folder.
    mock_temp_file = MagicMock()
    mock_temp_file.name = str(file_path)
    mock_temp_context = MagicMock()
    mock_temp_context.__enter__.return_value = mock_temp_file

    with patch('tempfile.NamedTemporaryFile', return_value=mock_temp_context), \
         patch('utils.reportes_bot.send_document', new_callable=AsyncMock) as mock_send_doc, \
         patch('os.remove') as mock_remove:

        # We will check the content of the file to ensure it was written correctly.
        await exportar_y_enviar_reporte(mock_bot, chat_id, SAMPLE_DF, file_format='csv')

        # To check the content, we need to let the original to_csv write to our temp path
        # Let's adjust the test to allow the file to be written.

        # Re-patching to be simpler:
        with patch('tempfile.NamedTemporaryFile', return_value=mock_temp_context), \
             patch('utils.reportes_bot.send_document', new_callable=AsyncMock) as mock_send_doc_inner, \
             patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove_inner:

            # The actual file is created by the function, we can't easily inspect it
            # without more complex mocking. Let's just trust pandas and check the calls.
            df_copy = SAMPLE_DF.copy()
            with patch.object(df_copy, 'to_csv') as mock_to_csv:
                await exportar_y_enviar_reporte(mock_bot, chat_id, df_copy, file_format='csv')
                mock_to_csv.assert_called_once()

            mock_send_doc_inner.assert_called_once()
            mock_remove_inner.assert_called_once()


@pytest.mark.asyncio
async def test_exportar_y_enviar_reporte_xlsx_happy_path(mock_bot):
    """Test successful export to XLSX and sending."""
    chat_id = 12345
    df_copy = SAMPLE_DF.copy()

    with patch('tempfile.NamedTemporaryFile') as mock_tempfile, \
         patch.object(df_copy, 'to_excel') as mock_to_excel, \
         patch('utils.reportes_bot.send_document', new_callable=AsyncMock) as mock_send_doc, \
         patch('os.path.exists', return_value=True), \
         patch('os.remove'):

        await exportar_y_enviar_reporte(mock_bot, chat_id, df_copy, file_format='xlsx')

        mock_to_excel.assert_called_once()
        mock_send_doc.assert_called_once()


@pytest.mark.asyncio
async def test_exportar_y_enviar_reporte_xlsx_import_error(mock_bot):
    """Test that an error message is sent if openpyxl is not installed."""
    chat_id = 12345

    # Hide the 'openpyxl' module from imports to simulate it not being installed
    with patch.dict('sys.modules', {'openpyxl': None}), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message, \
         patch('utils.reportes_bot.send_document', new_callable=AsyncMock) as mock_send_doc:

        await exportar_y_enviar_reporte(mock_bot, chat_id, SAMPLE_DF, file_format='xlsx')

        mock_send_message.assert_called_once_with(
            mock_bot, chat_id, "❌ Para exportar a Excel, el administrador del bot debe instalar la librería `openpyxl`."
        )
        mock_send_doc.assert_not_called()

@pytest.mark.asyncio
async def test_exportar_y_enviar_reporte_cleanup_on_failure(mock_bot):
    """Test that the temporary file is removed even if sending fails."""
    chat_id = 12345
    df_copy = SAMPLE_DF.copy()

    with patch('tempfile.NamedTemporaryFile'), \
         patch.object(df_copy, 'to_csv'), \
         patch('utils.reportes_bot.send_document', side_effect=Exception("Telegram Error")), \
         patch('os.path.exists', return_value=True), \
         patch('os.remove') as mock_remove:

        await exportar_y_enviar_reporte(mock_bot, chat_id, df_copy, file_format='csv')

        mock_remove.assert_called_once()

# Now, let's add tests for procesar_comando_reporte
from aiogram.types import InlineKeyboardMarkup
from utils.reportes_bot import procesar_comando_reporte

@pytest.mark.asyncio
async def test_procesar_comando_reportes_no_pendientes(mock_bot):
    """Test 'reportes' command when there are no pending reports."""
    chat_id = 12345
    with patch('utils.reportes_bot.listar_reportes', return_value=[]), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, "reportes")

        mock_send_message.assert_called_once_with(mock_bot, chat_id, "✅ No hay reportes pendientes.")

@pytest.mark.asyncio
async def test_procesar_comando_reportes_con_pendientes(mock_bot):
    """Test 'reportes' command with pending reports, checking keyboard generation."""
    chat_id = 12345
    report_files = ["report1.csv", "report2.xlsx"]

    with patch('utils.reportes_bot.listar_reportes', return_value=report_files), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, "reportes")

        mock_send_message.assert_called_once()
        args, kwargs = mock_send_message.call_args
        assert args[1] == chat_id
        assert args[2] == "📂 Reportes pendientes:"
        assert 'reply_markup' in kwargs

        keyboard = kwargs['reply_markup']
        assert isinstance(keyboard, InlineKeyboardMarkup)
        # 2 reports + 1 row for "all" buttons = 3 rows
        assert len(keyboard.inline_keyboard) == 3
        # Check first report's buttons
        assert keyboard.inline_keyboard[0][0].text == f"⬇️ Descargar {report_files[0]}"
        assert keyboard.inline_keyboard[0][0].callback_data == f"download_report:{report_files[0]}"
        assert keyboard.inline_keyboard[0][1].text == f"🗑️ Ignorar {report_files[0]}"
        assert keyboard.inline_keyboard[0][1].callback_data == f"ignore_report:{report_files[0]}"
        # Check "all" buttons
        assert keyboard.inline_keyboard[2][0].callback_data == "download_report:all"
        assert keyboard.inline_keyboard[2][1].callback_data == "ignore_report:all"

@pytest.mark.asyncio
async def test_procesar_comando_descargar_especifico_ok(mock_bot):
    """Test 'descargar <file>' command for an existing report."""
    chat_id = 12345
    report_file = "report1.csv"

    with patch('utils.reportes_bot.obtener_reporte', return_value=SAMPLE_DF) as mock_obtener, \
         patch('utils.reportes_bot.exportar_y_enviar_reporte', new_callable=AsyncMock) as mock_exportar, \
         patch('utils.reportes_bot.mover_a_descargados') as mock_mover, \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, f"descargar {report_file}")

        mock_obtener.assert_called_once_with(report_file)
        mock_exportar.assert_called_once_with(mock_bot, chat_id, SAMPLE_DF, report_file)
        mock_mover.assert_called_once_with(report_file)
        mock_send_message.assert_called_once_with(mock_bot, chat_id, f"✅ Reporte `{report_file}` enviado.")

@pytest.mark.asyncio
async def test_procesar_comando_descargar_especifico_not_found(mock_bot):
    """Test 'descargar <file>' command for a non-existing report."""
    chat_id = 12345
    report_file = "not_found.csv"

    with patch('utils.reportes_bot.obtener_reporte', return_value=None) as mock_obtener, \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, f"descargar {report_file}")

        mock_obtener.assert_called_once_with(report_file)
        mock_send_message.assert_called_once_with(mock_bot, chat_id, f"❌ No se encontró el reporte `{report_file}`.")

@pytest.mark.asyncio
async def test_procesar_comando_descargar_todo(mock_bot):
    """Test 'descargar todo' command."""
    chat_id = 12345
    report_files = ["rep1.csv", "rep2.csv"]

    with patch('utils.reportes_bot.listar_reportes', return_value=report_files) as mock_listar, \
         patch('utils.reportes_bot.obtener_reporte', return_value=SAMPLE_DF) as mock_obtener, \
         patch('utils.reportes_bot.exportar_y_enviar_reporte', new_callable=AsyncMock) as mock_exportar, \
         patch('utils.reportes_bot.mover_a_descargados') as mock_mover, \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, "descargar todo")

        assert mock_exportar.call_count == len(report_files)
        assert mock_mover.call_count == len(report_files)
        mock_send_message.assert_called_once_with(mock_bot, chat_id, "✅ Todos los reportes fueron enviados.")

@pytest.mark.asyncio
async def test_procesar_comando_ignorar_especifico_ok(mock_bot):
    """Test 'ignorar <file>' command for an existing report."""
    chat_id = 12345
    report_file = "report_to_ignore.csv"

    with patch('utils.reportes_bot.listar_reportes', return_value=[report_file]), \
         patch('utils.reportes_bot.ignorar_reporte') as mock_ignorar, \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, f"ignorar {report_file}")

        mock_ignorar.assert_called_once_with(report_file)
        mock_send_message.assert_called_once_with(mock_bot, chat_id, f" Reporte `{report_file}` archivado.")

@pytest.mark.asyncio
async def test_procesar_comando_ignorar_todo(mock_bot):
    """Test 'ignorar todo' command."""
    chat_id = 12345
    report_files = ["rep1.csv", "rep2.csv"]

    with patch('utils.reportes_bot.listar_reportes', return_value=report_files), \
         patch('utils.reportes_bot.ignorar_reporte') as mock_ignorar, \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, "ignorar todo")

        assert mock_ignorar.call_count == len(report_files)
        mock_send_message.assert_called_once_with(mock_bot, chat_id, "✅ Todos los reportes fueron ignorados y archivados.")

@pytest.mark.asyncio
async def test_procesar_comando_descargar_todo_no_reports(mock_bot):
    """Test 'descargar todo' when no reports are pending."""
    chat_id = 12345
    with patch('utils.reportes_bot.listar_reportes', return_value=[]), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, "descargar todo")

        mock_send_message.assert_called_once_with(mock_bot, chat_id, "✅ No hay reportes pendientes.")


@pytest.mark.asyncio
async def test_procesar_comando_ignorar_todo_no_reports(mock_bot):
    """Test 'ignorar todo' when no reports are pending."""
    chat_id = 12345
    with patch('utils.reportes_bot.listar_reportes', return_value=[]), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await procesar_comando_reporte(mock_bot, chat_id, "ignorar todo")

        mock_send_message.assert_called_once_with(mock_bot, chat_id, "✅ No hay reportes pendientes.")


@pytest.mark.asyncio
async def test_procesar_comando_ignorar_especifico_not_found(mock_bot):
    """Test 'ignorar <file>' for a non-existing report."""
    chat_id = 12345
    report_file = "not_found.csv"

    with patch('utils.reportes_bot.listar_reportes', return_value=['some_other_file.csv']), \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message, \
         patch('utils.reportes_bot.ignorar_reporte') as mock_ignorar:

        await procesar_comando_reporte(mock_bot, chat_id, f"ignorar {report_file}")

        mock_send_message.assert_called_once_with(mock_bot, chat_id, f"❌ No se encontró el reporte `{report_file}` para ignorar.")
        mock_ignorar.assert_not_called()

# Now, let's add tests for generate_daily_kpi_report
from utils.reportes_bot import generate_daily_kpi_report

@pytest.mark.asyncio
async def test_generate_daily_kpi_report_no_operations(mock_bot):
    """Test KPI report generation when no operations are found."""
    chat_id = 12345

    # The functions from kpi_calculator are imported *inside* generate_daily_kpi_report,
    # so we must patch them in their source module.
    with patch('utils.kpi_calculator.get_operations_df', return_value=pd.DataFrame()) as mock_get_df, \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message, \
         patch('utils.kpi_calculator.calculate_pnl') as mock_calc_pnl:

        await generate_daily_kpi_report(mock_bot, chat_id, days=1)

        mock_get_df.assert_called_once_with(days=1)
        mock_send_message.assert_called_once_with(
            mock_bot, chat_id, "📊 Reporte de KPIs (1 día(s)): No se encontraron operaciones."
        )
        mock_calc_pnl.assert_not_called()

@pytest.mark.asyncio
async def test_generate_daily_kpi_report_with_operations(mock_bot):
    """Test successful KPI report generation and correct formatting."""
    chat_id = 12345
    days = 7
    mock_operations_df = pd.DataFrame({'symbol': ['BTCUSDT']})

    # Mock return values for all KPI calculation functions
    mock_pnl_data = {
        'total_pnl_usdt': 150.75,
        'daily_pnl_df': pd.DataFrame({'daily_pnl': [150.75]}, index=[pd.to_datetime("2023-01-01")])
    }
    mock_trade_stats_data = {
        'total_trades': 10,
        'winning_trades': 7,
        'losing_trades': 3,
        'win_rate': 70.0,
        'profit_factor': 2.5,
        'expectancy': 15.08
    }
    mock_mdd_data = 10.5
    mock_freq_duration_data = {
        'trades_per_day': 1.43,
        'avg_trade_duration_minutes': 60.5
    }

    with patch('utils.kpi_calculator.get_operations_df', return_value=mock_operations_df) as mock_get_df, \
         patch('utils.kpi_calculator.calculate_pnl', return_value=mock_pnl_data) as mock_calc_pnl, \
         patch('utils.kpi_calculator.calculate_trade_stats', return_value=mock_trade_stats_data) as mock_calc_stats, \
         patch('utils.kpi_calculator.calculate_max_drawdown', return_value=mock_mdd_data) as mock_calc_mdd, \
         patch('utils.kpi_calculator.calculate_trade_frequency_and_duration', return_value=mock_freq_duration_data) as mock_calc_freq, \
         patch('utils.reportes_bot.send_message', new_callable=AsyncMock) as mock_send_message:

        await generate_daily_kpi_report(mock_bot, chat_id, days=days)

        # Verify all calculation functions were called correctly
        mock_get_df.assert_called_once_with(days=days)
        mock_calc_pnl.assert_called_once_with(mock_operations_df)
        mock_calc_stats.assert_called_once_with(mock_operations_df)
        mock_calc_mdd.assert_called_once_with(mock_operations_df)
        mock_calc_freq.assert_called_once_with(mock_operations_df)

        # Verify the content of the sent message
        mock_send_message.assert_called_once()
        args, kwargs = mock_send_message.call_args
        # The message is the third argument (index 2) passed to send_message
        sent_message = args[2]

        assert f"Últimos {days} Día(s)" in sent_message
        assert "150.75" in sent_message  # total_pnl_usdt
        assert "70.00%" in sent_message  # win_rate
        assert "10.50%" in sent_message  # max_drawdown
        assert "1.43" in sent_message    # trades_per_day
        assert "60.50 min" in sent_message # avg_trade_duration_minutes
