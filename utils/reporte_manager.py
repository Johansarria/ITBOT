# utils/reporte_manager.py

import os
import pandas as pd
from datetime import datetime
from typing import Literal, Optional
import logging # Importar logging

# Importar funciones de kpi_calculator
from utils.kpi_calculator import (
    get_operations_df,
    calculate_pnl,
    calculate_trade_stats,
    calculate_max_drawdown,
    calculate_trade_frequency_and_duration
)

logger = logging.getLogger(__name__) # Obtener logger para este módulo

def _is_safe_filename(filename: str) -> bool:
    """Verifica si el nombre de archivo es seguro (no contiene separadores de ruta o '..')."""
    if not filename:
        return False
    # Check for path separators, ensuring altsep is not None before checking
    if os.path.sep in filename or (os.path.altsep and os.path.altsep in filename):
        return False
    if ".." in filename:
        return False
    return True

# Ruta base donde se almacenan los reportes

REPO_PATH = "storage/reportes"

# Crear carpetas si no existen
os.makedirs(f"{REPO_PATH}/diarios", exist_ok=True)
os.makedirs(f"{REPO_PATH}/semanales", exist_ok=True)
os.makedirs(f"{REPO_PATH}/mensuales", exist_ok=True)
os.makedirs(f"{REPO_PATH}/riesgo", exist_ok=True)
os.makedirs(f"{REPO_PATH}/operaciones", exist_ok=True)
os.makedirs(f"{REPO_PATH}/pendientes", exist_ok=True)
os.makedirs(f"{REPO_PATH}/descargados", exist_ok=True)
os.makedirs(f"{REPO_PATH}/kpis", exist_ok=True)
os.makedirs(f"{REPO_PATH}/journal", exist_ok=True)
logger.info(f"Estructura de carpetas de reportes verificada en {REPO_PATH}. ")

def guardar_reporte(dataframe: pd.DataFrame, tipo: Literal['diario', 'semanal', 'mensual', 'riesgo', 'operaciones'], preguntar_descarga: bool = True) -> Optional[str]:
    fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{tipo}_{fecha_actual}.csv"

    # Map singular tipo to plural directory names where they differ
    dir_map = {'diario': 'diarios', 'semanal': 'semanales', 'mensual': 'mensuales'}
    dir_name = dir_map.get(tipo, tipo)
    path_tipo = os.path.join(REPO_PATH, dir_name)

    path_pendiente = os.path.join(REPO_PATH, "pendientes", filename)

    try:
        # Guardar en carpeta tipo y pendientes
        dataframe.to_csv(os.path.join(path_tipo, filename), index=False)
        dataframe.to_csv(path_pendiente, index=False)
        logger.info(f"Reporte '{filename}' guardado en '{path_tipo}' y 'pendientes'. ")

        if preguntar_descarga:
            return f"✅ Se generó el reporte `{filename}`.\n¿Deseas descargarlo ahora?\nEscribe: `descargar {filename}` o `no` para ignorar."
        else:
            return None
    except Exception as e:
        logger.exception(f"Error al guardar el reporte '{filename}': {e}")
        return None

def listar_reportes(tipo: Literal['pendientes', 'descargados']) -> list[str]:
    ruta = os.path.join(REPO_PATH, tipo)
    logger.debug(f"Listando reportes de tipo '{tipo}' en '{ruta}'. ")
    try:
        return sorted(os.listdir(ruta))
    except Exception as e:
        logger.exception(f"Error al listar reportes de tipo '{tipo}': {e}")
        return []

def mover_a_descargados(nombre_archivo: str) -> str:
    if not _is_safe_filename(nombre_archivo):
        logger.warning(f"Intento de acceso a ruta insegura detectado: {nombre_archivo}")
        return f"❌ Operación denegada: Nombre de archivo inválido `{nombre_archivo}`."
    origen = os.path.join(REPO_PATH, "pendientes", nombre_archivo)
    destino = os.path.join(REPO_PATH, "descargados", nombre_archivo)
    logger.info(f"Intentando mover reporte '{nombre_archivo}' de 'pendientes' a 'descargados'. ")
    try:
        if os.path.exists(origen):
            os.rename(origen, destino)
            logger.info(f"Reporte '{nombre_archivo}' movido exitosamente. ")
            return f"📁 Reporte `{nombre_archivo}` movido a 'descargados'."
        else:
            logger.warning(f"No se encontró el reporte '{nombre_archivo}' en 'pendientes' para mover. ")
            return f"❌ No se encontró el reporte `{nombre_archivo}` en 'pendientes'."
    except Exception as e:
        logger.exception(f"Error al mover el reporte '{nombre_archivo}': {e}")
        return f"❌ Error al mover el reporte `{nombre_archivo}`."

def obtener_reporte(nombre_archivo: str) -> Optional[pd.DataFrame]:
    if not _is_safe_filename(nombre_archivo):
        logger.warning(f"Intento de acceso a ruta insegura detectado: {nombre_archivo}")
        return None
    ruta = os.path.join(REPO_PATH, "pendientes", nombre_archivo)
    logger.debug(f"Intentando obtener reporte '{nombre_archivo}' desde '{ruta}'. ")
    try:
        if os.path.exists(ruta):
            df = pd.read_csv(ruta)
            logger.info(f"Reporte '{nombre_archivo}' obtenido exitosamente. ")
            return df
        else:
            logger.warning(f"No se encontró el reporte '{nombre_archivo}' en 'pendientes'. ")
            return None
    except Exception as e:
        logger.exception(f"Error al leer el reporte '{nombre_archivo}': {e}")
        return None

def generar_menu_reportes_disponibles() -> str:
    reportes = listar_reportes("pendientes")
    if not reportes:
        logger.info("No hay reportes pendientes para generar menú. ")
        return "✅ No hay reportes pendientes por descargar."

    mensaje = "📂 Reportes disponibles para descarga:\n\n"
    for i, archivo in enumerate(reportes, 1):
        mensaje += f"{i}. {archivo}\n"

    mensaje += ("\nPuedes escribir:\n"
                "- `descargar <nombre>` para descargar un archivo\n"
                "- `descargar todo` para bajar todos\n"
                "- `ignorar <nombre>` para no mostrar ese archivo más\n"
                "- `ignorar todo` para no recordar más hoy")
    logger.debug("Menú de reportes disponibles generado. ")
    return mensaje

def ignorar_reporte(nombre_archivo: str) -> str:
    if not _is_safe_filename(nombre_archivo):
        logger.warning(f"Intento de acceso a ruta insegura detectado: {nombre_archivo}")
        return f"❌ Operación denegada: Nombre de archivo inválido `{nombre_archivo}`."
    logger.info(f"Ignorando reporte '{nombre_archivo}'. ")
    return mover_a_descargados(nombre_archivo)

async def generar_reporte_diario(bot, chat_id: int) -> Optional[str]:
    """
    Genera un reporte con las operaciones del día actual y lo guarda como un archivo CSV.
    Notifica al usuario en Telegram sobre el resultado.
    """
    logger.info("Iniciando la generación de reporte diario.")
    operaciones_path = "data/operaciones/operaciones.csv"
    try:
        if not os.path.exists(operaciones_path):
            logger.warning(f"No se encontró el archivo de operaciones en {operaciones_path}")
            await bot.send_message(chat_id, "❌ No se encontró el archivo de operaciones para generar el reporte.")
            return None

        df = pd.read_csv(operaciones_path)
        df['timestamp_open'] = pd.to_datetime(df['timestamp_open'])
        
        today = datetime.now().date()
        df_diario = df[df['timestamp_open'].dt.date == today]

        if df_diario.empty:
            logger.info("No hay operaciones hoy para generar un reporte.")
            await bot.send_message(chat_id, "ℹ️ No se encontraron operaciones en el día de hoy para generar un reporte.")
            return None
            
        # Usar la función existente para guardar el reporte
        mensaje_confirmacion = guardar_reporte(df_diario, tipo='diario', preguntar_descarga=True)

        if mensaje_confirmacion:
            logger.info("Reporte diario generado y guardado exitosamente.")
            await bot.send_message(chat_id, mensaje_confirmacion)
            return mensaje_confirmacion
        else:
            logger.error("La función guardar_reporte no retornó un mensaje de confirmación.")
            await bot.send_message(chat_id, "❌ Ocurrió un error al guardar el reporte diario.")
            return None

    except Exception as e:
        logger.exception(f"Error catastrófico al generar el reporte diario: {e}")
        await bot.send_message(chat_id, f"❌ Error crítico al generar el reporte diario: {e}")
        return None

def guardar_reporte_texto(content: str, tipo: str, preguntar_descarga: bool = True) -> Optional[str]:
    """Guarda contenido de texto en un archivo y lo gestiona."""
    fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{tipo}_{fecha_actual}.txt"
    path_tipo = os.path.join(REPO_PATH, tipo)
    path_pendiente = os.path.join(REPO_PATH, "pendientes", filename)

    try:
        with open(os.path.join(path_tipo, filename), 'w', encoding='utf-8') as f:
            f.write(content)
        with open(path_pendiente, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Reporte de texto '{filename}' guardado en '{path_tipo}' y 'pendientes'.")

        if preguntar_descarga:
            return f"✅ Se generó el reporte `{filename}`.\n¿Deseas descargarlo ahora?\nEscribe: `descargar {filename}`"
        else:
            return None
    except Exception as e:
        logger.exception(f"Error al guardar el reporte de texto '{filename}': {e}")
        return None

async def generar_reporte_journal(bot, chat_id: int, days: int = 7):
    """
    Genera un "diario de trading" detallado para un período específico.
    """
    logger.info(f"Iniciando la generación de diario de trading para los últimos {days} días.")
    await bot.send_message(chat_id, f"⏳ Generando diario de trading para los últimos {days} días...")

    try:
        # 1. Obtener datos de operaciones
        operations_df = get_operations_df(days=days)

        if operations_df.empty:
            logger.warning(f"No se encontraron operaciones en los últimos {days} días para el diario.")
            await bot.send_message(chat_id, f"ℹ️ No hay operaciones registradas en los últimos {days} días.")
            return

        # 2. Ordenar por fecha de apertura
        operations_df = operations_df.sort_values(by='timestamp_open', ascending=False)

        # 3. Construir el contenido del reporte
        journal_content = f"📓 **Diario de Trading (Últimos {days} Días)** 📓\n"
        journal_content += "=" * 40 + "\n\n"

        for _, trade in operations_df.iterrows():
            trade_duration = "N/A"
            if pd.notna(trade['timestamp_close']) and pd.notna(trade['timestamp_open']):
                duration_td = trade['timestamp_close'] - trade['timestamp_open']
                trade_duration = str(duration_td).split('.')[0] # Formato más limpio

            pnl_status = "✅ GANANCIA" if trade['pnl_usdt'] > 0 else "❌ PÉRDIDA" if trade['pnl_usdt'] < 0 else "➖ SIN CAMBIO"

            journal_content += (
                f"🗓️ **Fecha:** {trade['timestamp_open'].strftime('%Y-%m-%d %H:%M')}\n"
                f"🆔 **ID:** `{trade['operation_id']}`\n"
                f"📈 **Símbolo:** {trade['symbol']} ({trade['side']})\n"
                f"-------------------------------------------------\n"
                f"**Entrada:**\n"
                f"  - **Precio:** {trade['entry_price']:.4f}\n"
                f"  - **Razón:** {trade.get('reason_open', 'N/A')}\n"
                f"  - **Score de Mercado:** {trade.get('market_score_open', 'N/A')}\n"
                f"**Salida:**\n"
                f"  - **Precio:** {trade['exit_price']:.4f}\n"
                f"  - **Razón:** {trade.get('reason_close', 'N/A')}\n"
                f"  - **Score de Mercado:** {trade.get('market_score_close', 'N/A')}\n"
                f"**Resultado:**\n"
                f"  - **PnL:** {trade['pnl_usdt']:.2f} USDT ({trade['pnl_percent']:.2f}%) {pnl_status}\n"
                f"  - **Duración:** {trade_duration}\n"
                f"**Configuración de Riesgo:**\n"
                f"  - **Take Profit:** {trade['take_profit']:.4f}\n"
                f"  - **Stop Loss:** {trade['stop_loss']:.4f}\n"
                f"  - **Riesgo Planeado:** {trade.get('risk_percent', 'N/A')}%\n"
                f"  - **Notas:** {trade.get('notes', 'Sin notas.')}\n"
                f"\n" + "="*40 + "\n\n"
            )

        # 4. Guardar y notificar
        mensaje_confirmacion = guardar_reporte_texto(journal_content, tipo='journal', preguntar_descarga=True)
        if mensaje_confirmacion:
            # Enviar un resumen al chat y luego la opción de descargar
            summary_message = (
                f"✅ Diario de trading generado con {len(operations_df)} operaciones.\n"
                "El reporte completo está listo para ser descargado."
            )
            await bot.send_message(chat_id, summary_message)
            await bot.send_message(chat_id, mensaje_confirmacion)
        else:
            await bot.send_message(chat_id, "❌ Ocurrió un error al guardar el diario de trading.")

    except Exception as e:
        logger.exception(f"Error catastrófico al generar el diario de trading: {e}")
        await bot.send_message(chat_id, f"❌ Error crítico al generar el diario de trading: {e}")


async def generar_reporte_kpis(bot, chat_id: int, days: int = 30):
    """
    Genera un reporte de KPIs de rendimiento y lo envía a Telegram.
    """
    logger.info(f"Iniciando la generación de reporte de KPIs para los últimos {days} días.")
    await bot.send_message(chat_id, f"⏳ Calculando KPIs de rendimiento para los últimos {days} días...")

    try:
        # 1. Obtener datos
        operations_df = get_operations_df(days=days)

        if operations_df.empty:
            logger.warning(f"No se encontraron operaciones en los últimos {days} días para el reporte de KPIs.")
            await bot.send_message(chat_id, f"ℹ️ No hay operaciones registradas en los últimos {days} días. No se puede generar el reporte de KPIs.")
            return

        # 2. Calcular todos los KPIs
        pnl_data = calculate_pnl(operations_df)
        trade_stats = calculate_trade_stats(operations_df)
        max_drawdown = calculate_max_drawdown(operations_df)
        freq_duration = calculate_trade_frequency_and_duration(operations_df)

        # 3. Formatear el reporte
        report_content = f"""
        📊 **Reporte de Rendimiento (Últimos {days} días)** 📊
        -------------------------------------------------
        **Resumen de PnL:**
        - PnL Total: {pnl_data['total_pnl_usdt']:.2f} USDT

        **Estadísticas de Trading:**
        - Total de Operaciones: {trade_stats['total_trades']}
        - Operaciones Ganadoras: {trade_stats['winning_trades']}
        - Operaciones Perdedoras: {trade_stats['losing_trades']}
        - Win Rate: {trade_stats['win_rate']:.2f}%
        - Profit Factor: {trade_stats['profit_factor']:.2f}
        - Expectancy por Trade: {trade_stats['expectancy']:.2f} USDT

        **Gestión de Riesgo:**
        - Max Drawdown: {max_drawdown:.2f}%
        - Ganancia Bruta: {trade_stats['gross_profit']:.2f} USDT
        - Pérdida Bruta: {trade_stats['gross_loss']:.2f} USDT

        **Frecuencia y Duración:**
        - Trades Promedio por Día: {freq_duration['trades_per_day']:.2f}
        - Duración Media de Trade: {freq_duration['avg_trade_duration_minutes']:.2f} minutos
        -------------------------------------------------
        *Este es un reporte automático basado en las operaciones auditadas.*
        """

        # 4. Enviar como mensaje y opcionalmente guardar como archivo
        await bot.send_message(chat_id, report_content, parse_mode='Markdown')
        
        # Guardar el reporte de texto para descarga opcional
        mensaje_confirmacion = guardar_reporte_texto(report_content, tipo='kpis', preguntar_descarga=True)
        if mensaje_confirmacion:
            await bot.send_message(chat_id, mensaje_confirmacion)

    except Exception as e:
        logger.exception(f"Error catastrófico al generar el reporte de KPIs: {e}")
        await bot.send_message(chat_id, f"❌ Error crítico al generar el reporte de KPIs: {e}")

if __name__ == '__main__':
    import asyncio
    from unittest.mock import MagicMock, AsyncMock

    # Configurar logging para pruebas
    from utils.logger_setup import setup_logging
    setup_logging()

    async def test_journal_generation():
        print("\n--- Probando Generación de Diario de Trading ---")

        # Mock del bot de Telegram y chat_id
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock()
        test_chat_id = 12345

        # Llamar a la función para generar el diario
        # Asumimos que la base de datos tiene datos de los últimos 7 días.
        # Si no, la función debe manejarlo elegantemente.
        await generar_reporte_journal(mock_bot, test_chat_id, days=7)

        # Verificar que send_message fue llamado (al menos para el mensaje inicial)
        try:
            mock_bot.send_message.assert_called()
            print("✅ La función `generar_reporte_journal` se ejecutó y llamó a `send_message`.")

            # Listar los reportes generados para confirmar
            reportes_journal = listar_reportes("pendientes")
            journal_files = [r for r in reportes_journal if r.startswith('journal_')]
            if journal_files:
                print(f"✅ Se encontró un nuevo reporte de diario: {journal_files[-1]}")
                # Opcional: leer el contenido para verificar
                # df = obtener_reporte(journal_files[-1]) # No es un df, es un txt
                # print(f"Contenido de muestra: ...")
            else:
                print("⚠️ No se generó un nuevo archivo de diario (puede ser normal si no hay operaciones).")

        except AssertionError:
            print("❌ La función `generar_reporte_journal` no llamó a `send_message` como se esperaba.")
        except Exception as e:
            print(f"❌ Ocurrió un error durante la prueba del diario: {e}")

    # Ejecutar la prueba asíncrona
    asyncio.run(test_journal_generation())