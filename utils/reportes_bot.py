# utils/reportes_bot.py

import pandas as pd
import tempfile
import os
import logging
import aiohttp
from datetime import datetime, timedelta # ADDED timedelta for KPI report

from utils.reporte_manager import (
    obtener_reporte,
    listar_reportes,
    mover_a_descargados,
    ignorar_reporte,
    generar_menu_reportes_disponibles,
)
from utils.telegram_handler import send_message, send_document
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils.exporter import generate_analysis_chart

# Importar funciones de KPI
from utils.kpi_calculator import get_operations_df, calculate_pnl, calculate_trade_stats, calculate_max_drawdown, calculate_trade_frequency_and_duration

ALL_OPERATION_COLUMNS = [
    "operation_id", "timestamp_open", "timestamp_close", "symbol", "side",
    "entry_price", "exit_price", "take_profit", "stop_loss", "size_usdt",
    "risk_percent", "mode", "pnl_usdt", "pnl_percent", "reason_open",
    "reason_close", "market_score_open", "market_score_close", "version_bot", "notes",
    "balance_usdt_al_abrir", "escudo_activo_al_abrir", "tipo_escudo_al_abrir", "riesgo_forzado_al_abrir",
    "cantidad_token_operada", "min_notional_filter", "step_size_filter", "price_tick_size_filter",
    "slippage_apertura_pct", "order_id_binance", "order_status_binance"
]

COLUMN_TRANSLATIONS = {
    "operation_id": "ID Operación",
    "timestamp_open": "Fecha Apertura",
    "timestamp_close": "Fecha Cierre",
    "symbol": "Símbolo",
    "side": "Tipo",
    "entry_price": "Precio Entrada",
    "exit_price": "Precio Salida",
    "take_profit": "Take Profit",
    "stop_loss": "Stop Loss",
    "size_usdt": "Tamaño (USDT)",
    "risk_percent": "Riesgo (%)",
    "mode": "Modo",
    "pnl_usdt": "P&L (USDT)",
    "pnl_percent": "P&L (%)",
    "reason_open": "Motivo Apertura",
    "reason_close": "Motivo Cierre",
    "market_score_open": "Score Mercado (Apertura)",
    "market_score_close": "Score Mercado (Cierre)",
    "version_bot": "Versión Bot",
    "notes": "Notas",
    "balance_usdt_al_abrir": "Balance USDT (Apertura)",
    "escudo_activo_al_abrir": "Escudo Activo (Apertura)",
    "tipo_escudo_al_abrir": "Tipo Escudo (Apertura)",
    "riesgo_forzado_al_abrir": "Riesgo Forzado (Apertura)",
    "cantidad_token_operada": "Cantidad Token",
    "min_notional_filter": "Filtro Notional Mín.",
    "step_size_filter": "Filtro Step Size",
    "price_tick_size_filter": "Filtro Tick Size",
    "slippage_apertura_pct": "Slippage Apertura (%)",
    "order_id_binance": "ID Orden Binance",
    "order_status_binance": "Estado Orden Binance"
}

logger = logging.getLogger(__name__)

async def generar_y_enviar_reporte_rango(bot_instance: Bot, chat_id: int, start_date: datetime, end_date: datetime, file_format: str):
    """Filtra las operaciones por rango de fechas y envía el reporte en el formato especificado."""
    logger.info(f"Generando reporte de operaciones desde {start_date.date()} hasta {end_date.date()} en formato {file_format}")
    operaciones_path = "data/operaciones/operaciones.csv"

    try:
        if not os.path.exists(operaciones_path):
            await send_message(bot_instance, chat_id, "❌ No se encontró el archivo de historial de operaciones.")
            return

        df = pd.read_csv(operaciones_path, names=ALL_OPERATION_COLUMNS, header=0, parse_dates=['timestamp_open'])
        
        if df.empty:
            await send_message(bot_instance, chat_id, "ℹ️ El historial de operaciones está vacío.")
            return

        df['timestamp_open'] = df['timestamp_open'].dt.tz_localize('UTC')

        mask = (df['timestamp_open'] >= start_date) & (df['timestamp_open'] <= end_date)
        df_filtered = df.loc[mask]

        df_filtered = df_filtered.rename(columns=COLUMN_TRANSLATIONS)

        if df_filtered.empty:
            await send_message(bot_instance, chat_id, f"ℹ️ No se encontraron operaciones entre {start_date.date()} y {end_date.date()}.")
            return

        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        filename = f"reporte_operaciones_{start_str}_{end_str}.{file_format}"
        caption = f"Reporte de operaciones desde {start_date.date()} hasta {end_date.date()}"
        
        await exportar_y_enviar_reporte(bot_instance, chat_id, df_filtered, filename, caption, file_format)

    except Exception as e:
        logger.exception("Error al generar o enviar el reporte por rango de fechas.")
        await send_message(bot_instance, chat_id, f"❌ Ocurrió un error crítico al generar el reporte: {e}")


def es_comando_reporte(mensaje: str) -> bool:
    comandos = ["descargar", "ignorar", "reportes"]
    return any(mensaje.strip().lower().startswith(cmd) for cmd in comandos)

async def exportar_y_enviar_reporte(bot_instance: Bot, chat_id: int, df: pd.DataFrame, nombre_archivo: str = "reporte.csv", caption: str = " Aquí tienes tu reporte", file_format: str = 'csv'):
    logger.info(f"Exportando y enviando reporte: {nombre_archivo}")
    
    suffix = f".{file_format}"
    temp_file_path = None

    try:
        with tempfile.NamedTemporaryFile(mode='w+', suffix=suffix, delete=False) as temp_file:
            temp_file_path = temp_file.name
            if file_format == 'csv':
                df.to_csv(temp_file_path, index=False)
            elif file_format == 'xlsx':
                try:
                    import openpyxl
                    for col in df.select_dtypes(include=['datetime64[ns, UTC]']).columns:
                        df[col] = df[col].dt.tz_convert(None)
                    df.to_excel(temp_file_path, index=False, engine='openpyxl')
                except ImportError:
                    logger.error("La librería 'openpyxl' es necesaria para exportar a Excel. Por favor, instálala (`pip install openpyxl`).")
                    await send_message(bot_instance, chat_id, "❌ Para exportar a Excel, el administrador del bot debe instalar la librería `openpyxl`.")
                    return

        if temp_file_path and os.path.exists(temp_file_path):
            await send_document(bot_instance, chat_id, temp_file_path, caption)
            logger.info(f"Reporte {nombre_archivo} enviado exitosamente a Telegram.")

    except Exception as e:
        logger.exception(f"Error inesperado al enviar reporte/gráfico {nombre_archivo} a Telegram: {e}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            logger.debug(f"Archivo temporal {temp_file_path} eliminado.")

async def procesar_comando_reporte(bot_instance: Bot, chat_id: int, mensaje: str):
    mensaje = mensaje.strip()
    logger.info(f"Procesando comando de reporte: {mensaje}")

    if mensaje.lower() == "reportes":
        archivos = listar_reportes("pendientes")
        if not archivos:
            await send_message(bot_instance, chat_id, "✅ No hay reportes pendientes.")
            logger.info("No hay reportes pendientes para mostrar.")
            return

        keyboard_buttons = []
        for archivo in archivos:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"⬇️ Descargar {archivo}", callback_data=f"download_report:{archivo}"),
                InlineKeyboardButton(text=f"🗑️ Ignorar {archivo}", callback_data=f"ignore_report:{archivo}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬇️ Descargar Todos", callback_data="download_report:all"),
            InlineKeyboardButton(text="🗑️ Ignorar Todos", callback_data="ignore_report:all")
        ])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await send_message(bot_instance, chat_id, "📂 Reportes pendientes:", reply_markup=reply_markup)
        logger.info("Menú de reportes pendientes con botones en línea enviado.")
        return

    if mensaje.lower().startswith("descargar "):
        argumento = mensaje[len("descargar "):].strip()
        logger.info(f"Comando descargar recibido: {argumento}")

        if argumento == "todo":
            archivos = listar_reportes("pendientes")
            if not archivos:
                await send_message(bot_instance, chat_id, "✅ No hay reportes pendientes.")
                logger.info("No hay reportes pendientes para descargar.")
                return
            for archivo in archivos:
                df = obtener_reporte(archivo)
                if df is not None:
                    await exportar_y_enviar_reporte(bot_instance, chat_id, df, archivo)
                    mover_a_descargados(archivo)
            await send_message(bot_instance, chat_id, "✅ Todos los reportes fueron enviados.")
            logger.info("Todos los reportes pendientes fueron enviados.")
        else:
            df = obtener_reporte(argumento)
            if df is not None:
                await exportar_y_enviar_reporte(bot_instance, chat_id, df, argumento)
                mover_a_descargados(argumento)
                await send_message(bot_instance, chat_id, f"✅ Reporte `{argumento}` enviado.")
                logger.info(f"Reporte {argumento} enviado.")
            else:
                await send_message(bot_instance, chat_id, f"❌ No se encontró el reporte `{argumento}`.")
                logger.warning(f"No se encontró el reporte {argumento} para descargar.")
        return

    if mensaje.lower().startswith("ignorar "):
        argumento = mensaje[len("ignorar "):].strip()
        logger.info(f"Comando ignorar recibido: {argumento}")

        if argumento == "todo":
            archivos = listar_reportes("pendientes")
            if not archivos:
                await send_message(bot_instance, chat_id, "✅ No hay reportes pendientes.")
                logger.info("No hay reportes pendientes para ignorar.")
                return
            for archivo in archivos:
                ignorar_reporte(archivo)
            await send_message(bot_instance, chat_id, "✅ Todos los reportes fueron ignorados y archivados.")
            logger.info("Todos los reportes pendientes fueron ignorados.")
        else:
            if argumento in listar_reportes("pendientes"):
                ignorar_reporte(argumento)
                await send_message(bot_instance, chat_id, f" Reporte `{argumento}` archivado.")
                logger.info(f"Reporte {argumento} ignorado.")
            else:
                await send_message(bot_instance, chat_id, f"❌ No se encontró el reporte `{argumento}` para ignorar.")
                logger.warning(f"No se encontró el reporte `{argumento}` para ignorar.")
        return

async def generate_daily_kpi_report(bot_instance: Bot, chat_id: int, days: int = 1):
    """
    Genera y envía un reporte diario de KPIs por Telegram.
    """
    logger.info(f"Generando reporte de KPIs para los últimos {days} día(s)...")
    
    from utils.kpi_calculator import get_operations_df, calculate_pnl, calculate_trade_stats, calculate_max_drawdown, calculate_trade_frequency_and_duration

    operations_df = get_operations_df(days=days)

    if operations_df.empty:
        await send_message(bot_instance, chat_id, f"📊 Reporte de KPIs ({days} día(s)): No se encontraron operaciones.")
        return

    # Calcular todos los KPIs
    pnl_data = calculate_pnl(operations_df)
    trade_stats = calculate_trade_stats(operations_df)
    mdd = calculate_max_drawdown(operations_df)
    freq_duration = calculate_trade_frequency_and_duration(operations_df)

    # Formatear el mensaje
    report_message = (
        f"📊 **Reporte de KPIs - Últimos {days} Día(s)** 📊\n\n"
        f"📈 **PnL Acumulado:** {pnl_data['total_pnl_usdt']:.2f} USDT\n"
    )

    if not pnl_data['daily_pnl_df'].empty:
        last_day_pnl = pnl_data['daily_pnl_df'].iloc[-1]
        report_message += f"  (Hoy: {last_day_pnl['daily_pnl']:.2f} USDT)\n"

    report_message += (
        f"\n📊 **Estadísticas de Trading:**\n"
        f"  Total Trades: {trade_stats['total_trades']}\n"
        f"  Trades Ganadores: {trade_stats['winning_trades']}\n"
        f"  Trades Perdedores: {trade_stats['losing_trades']}\n"
        f"  Win Rate: {trade_stats['win_rate']:.2f}%\n"
        f"  Profit Factor: {trade_stats['profit_factor']:.2f}\n"
        f"  Expectancy: {trade_stats['expectancy']:.2f} USDT/trade\n"
        f"  Max Drawdown: {mdd:.2f}%\n"
        f"  Trades por Día: {freq_duration['trades_per_day']:.2f}\n"
        f"  Duración Media por Trade: {freq_duration['avg_trade_duration_minutes']:.2f} min\n"
    )

    await send_message(bot_instance, chat_id, report_message)
    logger.info("Reporte de KPIs enviado exitosamente.")