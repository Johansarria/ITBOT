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
    if os.path.sep in filename or os.path.altsep in filename: # Verifica / y \
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
logger.info(f"Estructura de carpetas de reportes verificada en {REPO_PATH}. ")

def guardar_reporte(dataframe: pd.DataFrame, tipo: Literal['diario', 'semanal', 'mensual', 'riesgo', 'operaciones'], preguntar_descarga: bool = True) -> Optional[str]:
    fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{tipo}_{fecha_actual}.csv"
    path_tipo = os.path.join(REPO_PATH, tipo)
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