# handlers.py

"""
Módulo de Handlers de Telegram.

Contiene toda la lógica de la interfaz de usuario, manejando los comandos
y las acciones de los botones (CallbackQuery).
"""

import re
from typing import Dict, Any, List
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

# Riesgo: flags y parámetros efectivos
try:
    from utils.risk_manager import (
        custom_risk_params_active,
        get_effective_risk_params,
        reset_custom_risk_params,
    )
except Exception:  # fallbacks si el módulo no está disponible
    def custom_risk_params_active() -> bool:
        return False
    def get_effective_risk_params() -> dict:
        return {}
    def reset_custom_risk_params():
        return None
from telegram.error import BadRequest

# Importaciones locales
import keyboards
import telegram_logic_adapter as logic_stubs
from config import settings

# --- Estados para ConversationHandler ---
(
    CONFIRM_LIVE,
    CONFIRM_LIQUIDATE,
    CONFIRM_STOP,
    CONFIRM_MANUAL_RISK,
    CONFIRM_KILL_SWITCH,
    CONFIRM_KILL_PASSWORD,  # Nuevo estado para password
    CONFIRM_RESUME,
) = range(7)

# --- Helper para escapar Markdown ---
def escape_markdown(text: str) -> str:
    """Función de paso. El parseo se hace ahora con HTML."""
    return str(text)

# --- Handlers de Comandos ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para el comando /start. Muestra el menú principal con un resumen completo."""
    status = await logic_stubs.get_consolidated_status()

    summary_data = {
        "mode": status.get('mode', 'N/A'),
        "running_status": '✅ ACTIVO' if status.get('running') else '🛑 DETENIDO',
    "shield_status_text": f"🛡️ ACTIVOS" if any(status.get('shield_status', {}).values()) else f"✅ INACTIVOS",
    "open_positions": status.get('open_positions', 'N/A'),
    "market_regime": (status.get('market_regime') or 'N/D'),
        "daily_pnl_percent": f"{status.get('daily_pnl_percent', 0.0):.2f}",
        "total_pnl_percent": f"{status.get('total_pnl_percent', 0.0):.2f}"
    }

    # Mapeo de régimen a etiquetas en español
    regime_map = {
        'BULLISH_TREND': 'TENDENCIA ALCISTA',
        'BEARISH_TREND': 'TENDENCIA BAJISTA',
        'BULLISH_REVERSAL': 'REVERSIÓN ALCISTA',
        'BEARISH_REVERSAL': 'REVERSIÓN BAJISTA',
        'HIGH_VOLATILITY_RANGE': 'RANGO ALTO EN VOLATILIDAD',
        'LOW_VOLATILITY_RANGE': 'RANGO BAJO EN VOLATILIDAD',
        'UNDEFINED': 'SIN DEFINIR',
        'DATA_INSUFFICIENT': 'SIN DATOS',
        'ERROR': 'ERROR'
    }
    regime_display = regime_map.get(summary_data['market_regime'], summary_data['market_regime'])

    summary_text = (
        f"<b>Modo</b>: <code>{summary_data['mode']}</code>\n"
        f"<b>Estado</b>: <code>{summary_data['running_status']}</code>\n"
        f"<b>Escudos</b>: <code>{summary_data['shield_status_text']}</code>\n"
        f"<b>Posiciones</b>: <code>{summary_data['open_positions']}</code>\n"
        f"<b>Régimen</b>: <code>{regime_display}</code>\n"
        f"<b>PNL Diario</b>: <code>{summary_data['daily_pnl_percent']}%</code>\n"
        f"<b>PNL Total</b>: <code>{summary_data['total_pnl_percent']}%</code>"
    )

    # Hora local según TZ configurada (mostrar etiqueta de zona, no el offset numérico)
    try:
        import pytz
        tz = pytz.timezone(getattr(settings, 'TIMEZONE', 'America/Bogota'))
        local_now = datetime.now(tz)
        tz_label = getattr(settings, 'TIMEZONE', 'America/Bogota')
        hora_str = f"{local_now.strftime('%Y-%m-%d %H:%M')} {tz_label}"
    except Exception:
        hora_str = f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"

    pares_list = getattr(settings, 'ASSETS_TO_TRADE', [])
    pares_str = ", ".join(pares_list[:10])  # Limitar a 10 para no saturar
    if len(pares_list) > 10:
        pares_str += f" (+{len(pares_list)-10} más)"

    extra_info = (
        f"<b>Hora</b>: <code>{hora_str}</code>\n"
        f"<b>Modelo ML</b>: <code>{settings.ML_MODEL_ID}</code>\n"
        f"<b>Pares</b>: <code>{pares_str}</code>"
    )

    # Métricas ligeras opcionales
    try:
        services = await logic_stubs.check_services_health()
        active_services = [name for name, val in services.items() if ('OPERATIONAL' in val or 'ACTIVE' in val)]
        if active_services:
            svc_line = f"<b>Servicios activos</b>: <code>{', '.join(active_services)}</code>"
        else:
            svc_line = f"<b>Servicios activos</b>: <code>Ninguno</code>"
    except Exception:
        svc_line = None

    # Uptime simple: si status trae started_at en epoch/iso
    try:
        from datetime import timezone
        started = status.get('started_at')
        uptime_line = None
        if started:
            if isinstance(started, (int, float)):
                delta = datetime.now(timezone.utc) - datetime.fromtimestamp(started, tz=timezone.utc)
            else:
                # Si viene como ISO string
                from dateutil import parser as dtparser
                dt = dtparser.isoparse(str(started))
                if not dt.tzinfo:
                    dt = dt.replace(tzinfo=timezone.utc)
                delta = datetime.now(timezone.utc) - dt
            hours = int(delta.total_seconds() // 3600)
            uptime_line = f"<b>Uptime</b>: <code>{hours}h</code>"
    except Exception:
        uptime_line = None
    # Aviso si hay parámetros personalizados de riesgo activos
    custom_flag_line = "• ⚠️ <b>Operando con valores personalizados</b>" if custom_risk_params_active() else ""

    text = f"""🤖 <b>ITBOT</b>

<b>Resumen</b>
------------------------------
{summary_text}
------------------------------

<b>Información</b>
• {extra_info.splitlines()[0]}
• {extra_info.splitlines()[1]}
• {extra_info.splitlines()[2]}
{('• ' + svc_line) if svc_line else ''}
{('• ' + uptime_line) if uptime_line else ''}
{custom_flag_line}"""

    keyboard = keyboards.get_main_menu_keyboard()

    # Enviar banner solo cuando /start se invoca como comando (no por callback)
    banner_path = getattr(settings, 'BANNER_IMAGE_PATH', None)
    if update.message and (update.message.text or '').startswith('/start') and banner_path:
        try:
            import os
            import io
            chat_id = update.effective_chat.id if update.effective_chat else None
            if chat_id and os.path.isfile(banner_path):
                lower = banner_path.lower()
                if lower.endswith((".png", ".jpg", ".jpeg", ".webp")):
                    with open(banner_path, 'rb') as f:
                        await context.bot.send_photo(chat_id=chat_id, photo=f)
                elif lower.endswith(".pdf"):
                    try:
                        import fitz  # PyMuPDF
                        doc = fitz.open(banner_path)
                        if doc.page_count > 0:
                            page = doc.load_page(0)
                            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Doble resolución
                            img_bytes = io.BytesIO(pix.tobytes("png"))
                            img_bytes.name = "banner.png"  # Necesario para Telegram
                            await context.bot.send_photo(chat_id=chat_id, photo=img_bytes)
                            doc.close()
                        else:
                            with open(banner_path, 'rb') as f:
                                await context.bot.send_document(chat_id=chat_id, document=f)
                    except Exception:
                        with open(banner_path, 'rb') as f:
                            await context.bot.send_document(chat_id=chat_id, document=f)
                else:
                    with open(banner_path, 'rb') as f:
                        await context.bot.send_document(chat_id=chat_id, document=f)
            else:
                try:
                    print(f"[Banner] Archivo no encontrado: {banner_path}")
                except Exception:
                    pass
        except Exception as e:
            try:
                print(f"[Banner] Error enviando banner: {e}")
            except Exception:
                pass

    if update.message:
        await update.message.reply_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )


# --- Handlers de Menús Principales ---
async def show_control_operativo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    current_mode = await logic_stubs.get_bot_mode()
    text = f"⚙️ <b>Control Operativo</b>\n\nModo actual: <code>{current_mode}</code>\n\nSelecciona una acción."
    
    keyboard = keyboards.get_control_operativo_keyboard(current_mode)

    await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def show_gestion_riesgo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    # Badge si hay overrides personalizados
    badge = "\n\n⚠️ <b>Operando con valores personalizados</b>" if custom_risk_params_active() else ""
    text = "⚖️ <b>Gestión de Riesgo</b>\n\nDefine parámetros de riesgo y tamaño de las operaciones." + badge
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_gestion_riesgo_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def show_reportes_analisis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "📈 <b>Reportes y Análisis</b>\n\nAnaliza el rendimiento y las decisiones pasadas del bot."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_reportes_analisis_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def show_mlops_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🧠 <b>Inteligencia y MLOps</b>\n\nSupervisa los modelos de IA y el estado del mercado."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_mlops_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def show_system_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🛠️ <b>Sistema y Mantenimiento</b>\n\nVerifica la salud de los componentes del sistema."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_system_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def show_emergency_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🚨 <b>MENÚ DE EMERGENCIA</b> 🚨\n\nUsa estas opciones con extrema precaución. Son acciones irreversibles."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_emergency_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def show_panel_control(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🕹️ <b>Panel de Control</b>\n\nMonitoriza el estado del bot en tiempo real."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_panel_control_keyboard(),
        parse_mode=ParseMode.HTML
    )


# --- Handlers de Acciones Específicas ---

async def reports_show_discarded(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Consultando señales...")
    signals = await logic_stubs.get_last_discarded_signals()
    
    if not signals:
        text = "✅ No hay señales descartadas recientemente."
    else:
        import html as _html
        text_parts = ["<b>Últimas Señales Descartadas</b>"]
        for s in signals:
            ts = _html.escape(str(s.get('timestamp', 'N/A')))
            asset = _html.escape(str(s.get('asset', 'N/A')))
            signal = _html.escape(str(s.get('signal', 'N/A')))
            reason = _html.escape(str(s.get('reason', 'N/A')))
            text_parts.append(f"<code>{ts}</code> • <code>{asset}</code> • <code>{signal}</code> • <b>Razón</b>: {reason}")
        text = "\n".join(text_parts)

    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_reportes_analisis_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def system_health_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Verificando servicios...")
    health = await logic_stubs.check_services_health()
    
    import html as _html
    text_parts = ["<b>❤️ Verificación de Salud del Sistema</b>"]
    for service, status in health.items():
        icon = "✅" if "OPERATIONAL" in status or "ACTIVE" in status else "❌"
        service_esc = _html.escape(service)
        status_esc = _html.escape(status)
        text_parts.append(f"{icon} <b>{service_esc}</b>: <code>{status_esc}</code>")
    
    text = "\n".join(text_parts)
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_system_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def risk_define_size_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "📏 <b>Definir Tamaño de Orden</b>\n\nSelecciona cómo se debe calcular el riesgo para cada operación."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_risk_size_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def risk_show_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Mostrando configuración de riesgo...")
    # Valores efectivos (ce) vs por defecto (cd)
    ce = get_effective_risk_params() or {}
    cd = {
        "RISK_PER_TRADE_STOP_LOSS_PCT": getattr(settings, 'RISK_PER_TRADE_STOP_LOSS_PCT', None),
        "RISK_PER_TRADE_TAKE_PROFIT_PCT": getattr(settings, 'RISK_PER_TRADE_TAKE_PROFIT_PCT', None),
        "RISK_MAX_CONCURRENT_TRADES": getattr(settings, 'RISK_MAX_CONCURRENT_TRADES', None),
        "RISK_MAX_EXPOSURE_PCT": getattr(settings, 'RISK_MAX_EXPOSURE_PCT', None),
        "RISK_MAX_DAILY_DRAWDOWN_PCT": getattr(settings, 'RISK_MAX_DAILY_DRAWDOWN_PCT', None),
        "DEFAULT_RISK_PERCENTAGE": getattr(settings, 'DEFAULT_RISK_PERCENTAGE', None),
    }
    warning = "\n\n⚠️ <b>Operando con valores personalizados</b>" if custom_risk_params_active() else ""
    text = (
        "📄 <b>Configuración de Riesgo</b>\n\n"
        f"• <b>Stop Loss por operación</b>: <code>{ce.get('RISK_PER_TRADE_STOP_LOSS_PCT', cd['RISK_PER_TRADE_STOP_LOSS_PCT'])}%</code> <i>(def: {cd['RISK_PER_TRADE_STOP_LOSS_PCT']}%)</i>\n"
        f"• <b>Take Profit por operación</b>: <code>{ce.get('RISK_PER_TRADE_TAKE_PROFIT_PCT', cd['RISK_PER_TRADE_TAKE_PROFIT_PCT'])}%</code> <i>(def: {cd['RISK_PER_TRADE_TAKE_PROFIT_PCT']}%)</i>\n"
        f"• <b>Máx. operaciones concurrentes</b>: <code>{ce.get('RISK_MAX_CONCURRENT_TRADES', cd['RISK_MAX_CONCURRENT_TRADES'])}</code> <i>(def: {cd['RISK_MAX_CONCURRENT_TRADES']})</i>\n"
        f"• <b>Exposición Máxima</b>: <code>{ce.get('RISK_MAX_EXPOSURE_PCT', cd['RISK_MAX_EXPOSURE_PCT'])}%</code> <i>(def: {cd['RISK_MAX_EXPOSURE_PCT']}%)</i>\n"
        f"• <b>Drawdown Diario Máximo</b>: <code>{ce.get('RISK_MAX_DAILY_DRAWDOWN_PCT', cd['RISK_MAX_DAILY_DRAWDOWN_PCT'])}%</code> <i>(def: {cd['RISK_MAX_DAILY_DRAWDOWN_PCT']}%)</i>\n"
        f"• <b>Riesgo base por operación</b>: <code>{ce.get('DEFAULT_RISK_PERCENTAGE', cd['DEFAULT_RISK_PERCENTAGE'])}%</code> <i>(def: {cd['DEFAULT_RISK_PERCENTAGE']}%)</i>"
        + warning +
        "\n\n<i>Para modificar estos valores, usa el Panel Web → Configuración.</i>"
    )
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_gestion_riesgo_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def mlops_show_regime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Analizando régimen de mercado...")
    regime = await logic_stubs.get_market_regime()
    import html as _html
    text = f"🧠 <b>Régimen de Mercado Actual</b>\n\nEl modelo de IA ha detectado un régimen: <code>{_html.escape(str(regime))}</code>"
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_mlops_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def mlops_model_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Consultando estado del modelo...")
    status = await logic_stubs.get_ml_model_status()
    import html as _html
    se = {k: _html.escape(str(v)) for k, v in status.items()}
    text = (
        "🤖 <b>Estado del Modelo de Machine Learning</b>\n\n"
        f"• <b>ID de Modelo</b>: <code>{se.get('model_id', 'N/A')}</code>\n"
        f"• <b>Último Reentrenamiento</b>: <code>{se.get('last_retrained', 'N/A')}</code>\n"
        f"• <b>Drift de Performance</b>: <code>{se.get('performance_drift', 'N/A')}</code>\n"
        f"• <b>Próximo Entrenamiento</b>: <code>{se.get('next_training_scheduled', 'N/A')}</code>"
    )
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_mlops_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def panel_show_positions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Consultando posiciones abiertas...")
    summary = await logic_stubs.get_open_positions_summary(context.bot)
    await query.edit_message_text(
        text=summary,
        reply_markup=keyboards.get_panel_control_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def panel_show_shields(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    status_text = logic_stubs.get_shield_status()
    import html as _html
    text = f"🛡️ <b>Estado de los Escudos</b>\n\n<code>{_html.escape(str(status_text))}</code>"
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_panel_control_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def risk_set_auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Cambiando a riesgo automático...")
    logic_stubs.set_risk_auto()
    # Si hay overrides personalizados activos, resetearlos al volver a automático
    try:
        if custom_risk_params_active():
            reset_custom_risk_params()
    except Exception:
        pass
    await query.edit_message_text(
    text="✅ <b>Riesgo configurado en modo Automático</b>\n\nEl sistema ajustará el riesgo según el modelo ML.",
        reply_markup=keyboards.get_risk_size_menu_keyboard(),
    parse_mode=ParseMode.HTML
    )

async def risk_reset_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Acción rápida para restablecer valores por defecto (borra overrides personalizados)."""
    query = update.callback_query
    await query.answer("Restableciendo valores por defecto...")
    try:
        reset_custom_risk_params()
        msg = "🔄 <b>Parámetros de riesgo restablecidos</b> a valores por defecto."
    except Exception as e:
        msg = f"❌ No se pudo restablecer: {e}"
    await query.edit_message_text(
        text=msg,
        reply_markup=keyboards.get_gestion_riesgo_keyboard(),
        parse_mode=ParseMode.HTML
    )

# --- REFACTORED CONVERSATION AND ACTION HANDLERS ---

async def toggle_operative_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Inicia el proceso de cambio de modo.
    • Si está en LIVE, cambia a PAPER directamente.
    • Si está en PAPER, pide confirmación para cambiar a LIVE.
    """
    query = update.callback_query
    await query.answer()
    current_mode = await logic_stubs.get_bot_mode()

    if current_mode == 'LIVE':
        await logic_stubs.set_bot_mode("PAPER_TRADING")
        await query.edit_message_text(
            text="✅ *Modo de Operación Cambiado a `PAPER_TRADING`*\n\nEl bot operará en modo de simulación\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await start(update, context)
        return ConversationHandler.END
    else: # paper o cualquier otro estado
        text = (
            f"⚠️ *Confirmación Requerida* ⚠️\n\n"
            f"El bot está actualmente en modo `{escape_markdown(current_mode)}`\\.\n\n"
            f"Para cambiar a modo **LIVE**, por favor, escribe `CONFIRMAR LIVE`\\. \n\n"
            f"Esta acción expondrá capital real al mercado\\."
        )
        await query.edit_message_text(text=text, reply_markup=keyboards.get_cancel_keyboard(), parse_mode=ParseMode.MARKDOWN_V2)
        return CONFIRM_LIVE

async def confirm_and_set_live_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y cambia el modo a LIVE."""
    if update.message and update.message.text == "CONFIRMAR LIVE":
        await logic_stubs.set_bot_mode("LIVE")
        await update.message.reply_text(
            text="✅ *Modo de Operación Cambiado a `LIVE`*\n\nEl bot ahora operará con capital real\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        # Simplificado: Llama a start() con el update actual para reenviar el menú.
        await start(update, context)
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            text="❌ Texto incorrecto\\. El cambio a modo LIVE ha sido cancelado\\. Vuelve a intentarlo desde el menú de Control Operativo\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return ConversationHandler.END

async def liquidate_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("¡ACCIÓN CRÍTICA!", show_alert=True)
    text = (
        "🔥🔥🔥 *CONFIRMACIÓN DE LIQUIDACIÓN TOTAL* 🔥🔥🔥\\n\\n"
        "Estás a punto de liquidar **TODAS** las posiciones abiertas a precio de mercado\\.\\n\\n"
        "Esta acción es **IRREVERSIBLE**\\.\\n\\n"
        "Para proceder, escribe `LIQUIDAR TODO`\\."
    )
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    return CONFIRM_LIQUIDATE

async def confirm_liquidate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message and update.message.text == "LIQUIDAR TODO":
        await update.message.reply_text(
            text="🔥 Confirmado\\. Ejecutando liquidación total\\.\\.\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        # This function is being deprecated in favor of execute_kill_switch
        # For now, we call the new robust function
        await logic_stubs.execute_kill_switch()
        await update.message.reply_text(
            text="✅ *Liquidación Completada*\\. Todas las posiciones han sido cerradas\\.",
            reply_markup=keyboards.get_emergency_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            text="❌ Texto incorrecto\\. Escribe `LIQUIDAR TODO` o presiona cancelar\\.",
            reply_markup=keyboards.get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return CONFIRM_LIQUIDATE

async def stop_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("¡ACCIÓN CRÍTICA!", show_alert=True)
    text = (
        "🛑🛑🛑 *CONFIRMACIÓN DE PAUSA TOTAL* 🛑🛑🛑\\n\\n"
        "Estás a punto de detener **TODOS** los procesos de trading del bot\\. No se abrirán nuevas posiciones hasta que se reactive manualmente\\.\\n\\n"
        "Esta acción es **SEGURA** y no cierra posiciones abiertas\\.\\n\\n"
        "Para proceder, escribe `PAUSA TOTAL`\\."
    )
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    return CONFIRM_STOP

async def confirm_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message and update.message.text == "PAUSA TOTAL":
        await update.message.reply_text(
            text="🛑 Confirmado\\. Iniciando secuencia de pausa total\\.\\.\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await logic_stubs.full_system_stop()
        await update.message.reply_text(
            text="✅ *Sistema en Pausa*\\. El bot ha dejado de operar\\.",
            reply_markup=keyboards.get_emergency_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            text="❌ Texto incorrecto\\. Escribe `PAUSA TOTAL` o presiona cancelar\\.",
            reply_markup=keyboards.get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return CONFIRM_STOP


# --- Handlers de Comandos Rápidos ---

async def show_quick_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra un dashboard rápido con información esencial."""
    query = update.callback_query
    await query.answer("Cargando dashboard...")
    
    status = await logic_stubs.get_consolidated_status()
    
    # Información básica del bot
    mode = status.get('mode', 'N/A')
    running = "🟢 ACTIVO" if status.get('running') else "🔴 DETENIDO"
    positions = status.get('open_positions', 0)
    daily_pnl = status.get('daily_pnl_percent', 0.0)
    total_pnl = status.get('total_pnl_percent', 0.0)
    
    # Emoji para PnL
    daily_emoji = "🟢" if daily_pnl >= 0 else "🔴"
    total_emoji = "🟢" if total_pnl >= 0 else "🔴"
    
    # Estado de escudos
    shields = status.get('shield_status', {})
    shields_active = any(shields.values())
    shield_status = "🛡️ ACTIVOS" if shields_active else "✅ INACTIVOS"
    
    text = f"""📊 **DASHBOARD RÁPIDO**

🤖 **Estado**: {running}
📋 **Modo**: `{escape_markdown(mode)}`
🛡️ **Escudos**: {shield_status}

💰 **Rendimiento**:
{daily_emoji} Diario: `{daily_pnl:+.2f}%`
{total_emoji} Total: `{total_pnl:+.2f}%`

📈 **Posiciones Abiertas**: `{positions}`

🔄 _Actualizado: {escape_markdown(datetime.now().strftime('%H:%M:%S'))}_"""

    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_quick_dashboard_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_quick_positions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra un resumen rápido de posiciones."""
    query = update.callback_query
    await query.answer("Consultando posiciones...")
    
    # Usar la función existente pero con formato más conciso
    summary = await logic_stubs.get_open_positions_summary(context.bot)
    
    text = f"""📈 **POSICIONES ACTIVAS**

{summary}

🌐 _Para gestión avanzada, usa el Panel Web_"""

    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_quick_positions_keyboard(),
        parse_mode=ParseMode.HTML  # El summary ya viene en HTML
    )

async def show_quick_pairs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra información rápida de pares dinámicos."""
    query = update.callback_query
    await query.answer("Consultando pares...")
    
    # Simulamos datos de pares - en la implementación real obtendríamos esto del dynamic_pair_manager
    text = """🎯 **PARES DINÁMICOS ACTIVOS**

_Función en desarrollo..._

🌐 **Panel Web**: Para análisis completo de pares, volatilidad, y selección dinámica, utiliza el panel web.

⚡ **Acceso rápido**: /web_panel"""

    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_quick_pairs_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_quick_shields(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra estado rápido de escudos."""
    query = update.callback_query
    await query.answer()
    
    status_text = logic_stubs.get_shield_status()
    text = f"""🛡️ **ESTADO DE ESCUDOS**

{escape_markdown(status_text)}

💡 **Info**: Los escudos protegen tu capital pausando operaciones cuando se detectan condiciones adversas."""
    
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_panel_control_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_web_panel_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra información de acceso al panel web."""
    query = update.callback_query
    await query.answer()
    
    # Obtener el host y puerto del panel web (usando valores del .env)
    web_host = "localhost"  # Por defecto
    web_port = "8080"      # Por defecto
    
    try:
        import os
        web_host = os.getenv('WEB_HOST', 'localhost')
        web_port = os.getenv('WEB_PORT', '8080')
        public_url = os.getenv('WEB_PUBLIC_URL') or os.getenv('PUBLIC_URL')
    except Exception:
        public_url = None  # Usar valores por defecto
    
    import html as _html
    # Construir URL a mostrar
    if public_url:
        url = _html.escape(public_url)
    else:
        host_display = str(web_host)
        if host_display in ("0.0.0.0", "::"):
            host_display = "localhost"
        url = f"http://{_html.escape(host_display)}:{_html.escape(str(web_port))}"
    text = (
        "🌐 <b>PANEL WEB COMPLETO</b>\n\n"
        f"🔗 <b>URL</b>: <code>{url}</code>\n\n"
        "📱 <b>Características</b>:\n"
        "• Dashboard en tiempo real\n"
        "• Gráficos avanzados\n"
        "• Gestión de posiciones\n"
        "• Configuración completa\n"
        "• Backtesting\n"
        "• Logs del sistema\n\n"
    "🔐 <b>Acceso</b>: Se requiere token de autenticación\n\n"
    "💡 <i>Tip</i>: Si accedes desde otro dispositivo en tu red, usa la IP de tu equipo con el mismo puerto (p. ej. http://192.168.x.x:" + _html.escape(str(web_port)) + ")"
    )

    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_web_panel_info_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def generate_web_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Genera un token temporal para el acceso web (mock/simple)."""
    query = update.callback_query
    await query.answer("Generando token...")
    import os, html as _html
    import asyncio
    try:
        import httpx
    except Exception:
        httpx = None

    # Construir URL pública/base para abrir el panel
    web_host = os.getenv('WEB_HOST', 'localhost')
    web_port = os.getenv('WEB_PORT', '8080')
    public_url = os.getenv('WEB_PUBLIC_URL') or os.getenv('PUBLIC_URL')
    if public_url:
        base_url = public_url.rstrip('/')
    else:
        host_display = web_host
        if host_display in ("0.0.0.0", "::"):
            host_display = "localhost"
        base_url = f"http://{host_display}:{web_port}"

    # Preparar lista de endpoints posibles para crear el token (soporta múltiples despliegues)
    candidates = []
    # 1) URL interna configurable
    internal_override = os.getenv('WEB_INTERNAL_API_URL')
    if internal_override:
        candidates.append(internal_override.rstrip('/') + '/api/generate_token')
    # 2) Nombre de servicio Docker por defecto
    candidates.append('http://web:8080/api/generate_token')
    # 2b) Container name explícito
    candidates.append('http://itbot_web:8080/api/generate_token')
    # 3) Host/puerto conocidos
    local_host = web_host
    if local_host in ("0.0.0.0", "::"):
        local_host = "localhost"
    candidates.append(f"http://{local_host}:{web_port}/api/generate_token")
    # 4) Fallbacks locales
    candidates.append('http://127.0.0.1:8080/api/generate_token')
    candidates.append('http://localhost:8080/api/generate_token')
    user_id = str(update.effective_user.id) if update.effective_user else 'default'
    token = None
    expires_at = None
    error_msg = None
    last_exc = None
    try:
        if httpx is None:
            raise RuntimeError("httpx no disponible")
        async with httpx.AsyncClient(timeout=5) as client:
            for attempt in range(3):
                for api_url in candidates:
                    try:
                        resp = await client.post(api_url, json={"user_id": user_id})
                        data = resp.json()
                        if resp.status_code == 200 and data.get('success'):
                            token = data.get('token')
                            expires_at = data.get('expires_at')
                            error_msg = None
                            break
                        else:
                            last_exc = Exception(data.get('error') or f"HTTP {resp.status_code}")
                    except Exception as e:
                        last_exc = e
                if token:
                    break
                # pequeño backoff
                try:
                    await asyncio.sleep(0.6)
                except Exception:
                    pass
            if not token and last_exc:
                raise last_exc
    except Exception as e:
        error_msg = str(e)

    if token:
        # Construir URL sin escapar para el botón; escapar solo para mostrar
        final_url = f"{base_url}/dashboard?token={token}"
        from urllib.parse import urlparse
        try:
            parsed = urlparse(base_url)
            host = (parsed.hostname or "").lower()
        except Exception:
            host = ""
        is_local = host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
        text = (
            "🔑 <b>Token de Acceso Generado</b>\n\n"
            f"<b>Token</b>: <code>{_html.escape(token)}</code>\n"
            f"<b>Expira</b>: <code>{_html.escape(str(expires_at))}</code>\n\n"
            f"<b>Enlace</b>: <code>{_html.escape(final_url)}</code>\n\n"
            + ("<i>Nota</i>: Define WEB_PUBLIC_URL en .env para habilitar un botón clicable." if is_local else "Pulsa el botón para abrir el panel con el token.")
        )
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        buttons = []
        if not is_local:
            buttons.append([InlineKeyboardButton("🌐 Abrir Panel con Token", url=final_url)])
        buttons.append([InlineKeyboardButton("↩️ Volver", callback_data="web_panel_access")])
        km = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text=text, reply_markup=km, parse_mode=ParseMode.HTML)
    else:
        hint = (
            "\n\nSugerencias:\n"
            "• Verifica que el servicio 'web' esté corriendo\n"
            "• Si estás fuera de Docker, define WEB_INTERNAL_API_URL (p.ej. http://localhost:8080)\n"
            "• En producción, configura WEB_PUBLIC_URL para enlaces clicables"
        )
        text = (
            "❌ <b>No se pudo generar el token</b>\n\n"
            f"Error: <code>{_html.escape(str(error_msg or 'desconocido'))}</code>" + hint
        )
        await query.edit_message_text(text=text, reply_markup=keyboards.get_web_panel_info_keyboard(), parse_mode=ParseMode.HTML)

async def mobile_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra instrucciones para acceder al panel desde móvil."""
    query = update.callback_query
    await query.answer()
    text = (
        "📱 <b>Instrucciones Mobile</b>\n\n"
        "1) Abre el navegador en tu móvil\n"
        "2) Ingresa la URL del panel\n"
        "3) Ingresa el token de acceso\n"
        "4) Añade a Inicio para acceso rápido (opcional)"
    )
    await query.edit_message_text(text=text, reply_markup=keyboards.get_web_panel_info_keyboard(), parse_mode=ParseMode.HTML)

async def desktop_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra instrucciones para acceder al panel desde desktop."""
    query = update.callback_query
    await query.answer()
    text = (
        "💻 <b>Instrucciones Desktop</b>\n\n"
        "1) Abre tu navegador preferido (Chrome/Firefox)\n"
        "2) Ingresa la URL del panel\n"
        "3) Ingresa el token de acceso\n"
        "4) Guarda la página en Favoritos"
    )
    await query.edit_message_text(text=text, reply_markup=keyboards.get_web_panel_info_keyboard(), parse_mode=ParseMode.HTML)

# --- Handlers de Emergencia Mejorados ---

async def show_emergency_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra ayuda sobre qué hacer en emergencias."""
    query = update.callback_query
    await query.answer()
    
    text = (
        "⚠️ <b>GUÍA DE EMERGENCIA</b>\n\n"
        "🛑 <b>PAUSA TOTAL</b> (Recomendado):\n"
        "• Detiene nuevas operaciones\n"
        "• Mantiene posiciones abiertas\n"
        "• Acción segura y reversible\n\n"
        "🚨 <b>KILL SWITCH</b> (Solo Emergencias):\n"
        "• Cierra TODAS las posiciones\n"
        "• Detiene el bot completamente\n"
        "• Solo para administradores\n"
        "• Acción <b>IRREVERSIBLE</b>\n\n"
        "🆘 <b>En caso de pánico</b>: Usar PAUSA TOTAL primero; luego evaluar desde el panel web."
    )

    keyboard = [
        [InlineKeyboardButton("🛑 PAUSA TOTAL", callback_data="emergency_pause_all")],
        [InlineKeyboardButton("↩️ Menú Emergencia", callback_data="emergencia")],
    ]
    
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def emergency_pause_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pausa todo el sistema de forma segura."""
    query = update.callback_query
    await query.answer("Ejecutando pausa segura...")
    
    try:
        await logic_stubs.full_system_stop()
        text = (
            "✅ <b>SISTEMA PAUSADO</b>\n\n"
            "🛑 El bot ha sido pausado de forma segura\n"
            "📈 Las posiciones abiertas se mantienen\n"
            "🔄 Para reanudar: usar botón <b>REANUDAR SISTEMA</b>\n\n"
            "💡 Esta acción es segura y reversible."
        )
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboards.get_emergency_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await query.edit_message_text(
            text=f"❌ <b>ERROR</b>: {str(e)}",
            reply_markup=keyboards.get_emergency_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )

def is_admin(user_id: int) -> bool:
    """Verifica si el ID de usuario corresponde al administrador."""
    try:
        admin_id = settings.ADMIN_TELEGRAM_ID
        print(f"DEBUG: Verificando admin - User ID: {user_id}, Admin ID configurado: {admin_id}")
        return user_id == admin_id
    except Exception as e:
        print(f"ERROR verificando admin: {e}")
        return False

def verify_kill_switch_password(password: str) -> bool:
    """Verifica si el password del Kill Switch es correcto."""
    try:
        configured_password = settings.KILL_SWITCH_PASSWORD or "emergency123"
        return password.strip() == configured_password
    except Exception as e:
        print(f"ERROR verificando password: {e}")
        return False

async def verify_kill_switch_password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler que verifica la contraseña del Kill Switch."""
    user_password = update.message.text.strip() if update.message else ""
    
    # Límite de intentos y cooldown por usuario
    import time as _time
    # Usar user_data sin reasignarlo (PTB no permite asignar un nuevo dict)
    ud = context.user_data
    if ud is None:
        # Salvaguarda (no debería ocurrir)
        await update.message.reply_text(
            "❌ Error de contexto. Intenta nuevamente.",
            reply_markup=keyboards.get_cancel_keyboard()
        )
        return ConversationHandler.END
    # Establecer valores por defecto de forma segura
    ud.setdefault('ks_attempts', 0)
    ud.setdefault('ks_cooldown_until', None)
    now = _time.time()
    # Cooldown de 60s si excede 3 intentos
    cooldown_until = ud.get('ks_cooldown_until')
    if cooldown_until and now < cooldown_until:
        wait = int(cooldown_until - now)
        await update.message.reply_text(
            f"⏳ Demasiados intentos fallidos. Intenta de nuevo en {wait}s.",
            reply_markup=keyboards.get_cancel_keyboard()
        )
        return ConversationHandler.END

    attempts = ud.get('ks_attempts', 0)
    if attempts >= 3:
        ud['ks_cooldown_until'] = now + 60
        ud['ks_attempts'] = 0
        await update.message.reply_text(
            "⏳ Demasiados intentos fallidos. Espera 60s antes de reintentar.",
            reply_markup=keyboards.get_cancel_keyboard()
        )
        return ConversationHandler.END

    # Log simple (sin exponer el password)
    try:
        print(f"[KillSwitch] Password recibido. Longitud={len(user_password)}")
    except Exception:
        pass

    if verify_kill_switch_password(user_password):
        print("[KillSwitch] Password OK. Avanzando a confirmación final.")
        # Resetear contadores
        ud['ks_attempts'] = 0
        ud['ks_cooldown_until'] = None
        # Contraseña correcta, pasar a la confirmación final
        return await confirm_kill_switch(update, context)
    else:
        print("[KillSwitch] Password inválido. Cancelando.")
        # Contraseña incorrecta
        ud['ks_attempts'] = attempts + 1
        await update.message.reply_text(
            "❌ Contraseña incorrecta. Kill Switch cancelado.",
            reply_markup=keyboards.get_cancel_keyboard()
        )
        return ConversationHandler.END


async def kill_switch_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la secuencia del Kill Switch desde un comando /kill_switch."""
    # 1. Verificar si el usuario es administrador
    if not is_admin(update.message.from_user.id):
        await update.message.reply_text("🚫 ACCESO DENEGADO. Este comando solo puede ser ejecutado por un administrador.")
        return ConversationHandler.END

    # 2. Según configuración, requerir contraseña o ir directo a confirmación
    context.user_data.setdefault('return_to', 'emergencia')
    if getattr(settings, 'KILL_SWITCH_REQUIRE_PASSWORD', False):
        text = (
            "🚨 <b>KILL SWITCH - VERIFICACIÓN ADICIONAL</b> 🚨\n\n"
            "⚠️ Se requiere contraseña adicional de seguridad.\n\n"
            "🔐 Escribe la contraseña para continuar:"
        )
        await update.message.reply_text(
            text=text,
            reply_markup=keyboards.get_cancel_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return CONFIRM_KILL_PASSWORD
    else:
        text = (
            "🚨🚨🚨 CONFIRMACIÓN DE KILL SWITCH 🚨🚨🚨\n\n"
            "Esta acción liquidará TODAS las posiciones abiertas y detendrá TODA la operativa del bot.\n\n"
            "Esta acción es IRREVERSIBLE.\n\n"
            "Para proceder, escribe CONFIRMAR KILL SWITCH"
        )
        await update.message.reply_text(
            text=text,
            reply_markup=keyboards.get_cancel_keyboard()
        )
        return CONFIRM_KILL_SWITCH


async def kill_switch_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la secuencia del Kill Switch, verificando primero la autorización."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not is_admin(user_id):
        # Construir el texto con el emoji por código para evitar problemas de codificación
        denied = f"{chr(0x1F6AB)} ACCESO DENEGADO {chr(0x1F6AB)}"
        await query.answer(denied, show_alert=True)
        return ConversationHandler.END

    await query.answer("❗ ACCIÓN DE EMERGENCIA ❗", show_alert=True)
    # Guardar retorno al menú de emergencia en caso de cancelación
    context.user_data.setdefault('return_to', 'emergencia')
    if getattr(settings, 'KILL_SWITCH_REQUIRE_PASSWORD', False):
        text = (
            "🚨 <b>KILL SWITCH - VERIFICACIÓN ADICIONAL</b> 🚨\n\n"
            "⚠️ Se requiere contraseña adicional de seguridad.\n\n"
            "🔐 Escribe la contraseña para continuar:"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=keyboards.get_cancel_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return CONFIRM_KILL_PASSWORD
    else:
        text = (
            "🚨🚨🚨 CONFIRMACIÓN DE KILL SWITCH 🚨🚨🚨\n\n"
            "Esta acción liquidará TODAS las posiciones abiertas y detendrá TODA la operativa del bot.\n\n"
            "Esta acción es IRREVERSIBLE.\n\n"
            "Para proceder, escribe CONFIRMAR KILL SWITCH"
        )
        await query.edit_message_text(
            text=text,
            reply_markup=keyboards.get_cancel_keyboard()
        )
        return CONFIRM_KILL_SWITCH

async def confirm_kill_switch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y ejecuta el Kill Switch cuando se recibe el texto correcto."""
    # Si el flujo requiere password, esta función es llamada tras verify_kill_switch_password_handler
    # En ambos casos esperamos el texto "CONFIRMAR KILL SWITCH" para ejecutar
    msg = (update.message.text or "").strip() if update.message else ""
    if msg == "CONFIRMAR KILL SWITCH":
        # Mensaje previo
        await update.message.reply_text(
            "🔥 Confirmado. Ejecutando Kill Switch Atómico... El sistema se pausará primero y luego se liquidarán las posiciones."
        )
        # Ejecutar lógica atómica
        results = await logic_stubs.atomic_kill_switch()
        closed_count = len(results.get('closed_positions', []))
        failed = results.get('failed_positions', []) or []
        failed_count = len(failed)
        report_parts = [f"✅ <b>Liquidación completada</b>: {closed_count} posiciones cerradas."]
        if failed_count:
            report_parts.append(f"❌ <b>ATENCIÓN</b>: {failed_count} posiciones NO pudieron cerrarse y requieren intervención manual.")
            for pos in failed:
                try:
                    sym = pos.get('symbol') if isinstance(pos, dict) else str(pos)
                except Exception:
                    sym = str(pos)
                report_parts.append(f"  • <code>{sym}</code>")
        report_parts.append("\n🛑 <b>Sistema en Pausa</b>. El bot no realizará nuevas operaciones.")
        await update.message.reply_text(
            text="\n".join(report_parts),
            reply_markup=keyboards.get_emergency_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ Texto incorrecto. El Kill Switch ha sido cancelado.",
            reply_markup=keyboards.get_cancel_keyboard()
        )
        return CONFIRM_KILL_SWITCH

async def execute_kill_switch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ejecuta el Kill Switch tras la confirmación final del administrador."""
    if update.message and update.message.text == "CONFIRMAR KILL SWITCH":
        await update.message.reply_text(
            "🔥 Confirmado. Ejecutando Kill Switch Atómico... El sistema se pausará primero y luego se liquidarán las posiciones."
        )

        # Ejecutar lógica de liquidación y pausa de forma atómica
        results = await logic_stubs.atomic_kill_switch()

        # Formatear el reporte para el usuario
        closed_count = len(results['closed_positions'])
        failed_count = len(results['failed_positions'])
        report_parts = [f"✅ <b>Liquidación completada</b>: {closed_count} posiciones cerradas."]
        if failed_count > 0:
            report_parts.append(f"❌ <b>ATENCIÓN</b>: {failed_count} posiciones NO pudieron cerrarse y requieren intervención manual.")
            for pos in results['failed_positions']:
                report_parts.append(f"  • <code>{pos['symbol']}</code>")

        report_parts.append("\n🛑 <b>Sistema en Pausa</b>. El bot no realizará nuevas operaciones.")

        await update.message.reply_text(
            text="\n".join(report_parts),
            reply_markup=keyboards.get_emergency_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ Texto incorrecto. El Kill Switch ha sido cancelado.",
            reply_markup=keyboards.get_cancel_keyboard()
        )
        return CONFIRM_KILL_SWITCH

async def resume_system_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la secuencia para reanudar el sistema."""
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("🚫 ACCESO DENEGADO 🚫", show_alert=True)
        return ConversationHandler.END

    await query.answer()
    text = (
        "✅ <b>Reanudar Operativa</b> ✅\n\n"
        "Estás a punto de reactivar el bot. Volverá a analizar el mercado y a abrir posiciones según su estrategia.\n\n"
        "Para proceder, escribe <code>REANUDAR SISTEMA</code>."
    )
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode=ParseMode.HTML
    )
    return CONFIRM_RESUME

async def confirm_resume_system(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y reanuda el sistema."""
    user_txt = (update.message.text if update.message and update.message.text else "").strip()
    if user_txt.upper() == "REANUDAR SISTEMA":
        await update.message.reply_text(
            "✅ Confirmado. Reanudando la operativa...",
            parse_mode=ParseMode.HTML
        )
        await logic_stubs.resume_system()
        await update.message.reply_text(
            "🚀 <b>Sistema Reactivado</b>. El bot está operativo.",
            reply_markup=keyboards.get_emergency_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "❌ Texto incorrecto. La reanudación ha sido cancelada.",
            reply_markup=keyboards.get_cancel_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return CONFIRM_RESUME
async def show_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra ayuda sobre cómo configurar el admin."""
    query = update.callback_query
    await query.answer()
    
    text = f"""❓ **CONFIGURACIÓN DE ADMINISTRADOR**

🔍 **Tu ID actual**: `{query.from_user.id}`

⚙️ **Para ser administrador**:
1. Copia tu ID: `{query.from_user.id}`
2. Edita el archivo `.env`
3. Cambia: `ADMIN_TELEGRAM_ID={query.from_user.id}`
4. Reinicia el bot

🔄 **Reiniciar bot**:
• `docker-compose restart`
• O desde panel web

🛡️ **Seguridad**: Solo el admin puede usar Kill Switch"""

    keyboard = [
        [InlineKeyboardButton("📋 Copiar Mi ID", callback_data=f"copy_id_{query.from_user.id}")],
        [InlineKeyboardButton("🌐 Panel Web", callback_data="web_panel_access")],
        [InlineKeyboardButton("↩️ Volver", callback_data="emergencia")],
    ]

    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def verify_admin_access(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verifica nuevamente el acceso de admin."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if is_admin(user_id):
        await query.answer("✅ Admin verificado!")
        text = """✅ **ADMIN VERIFICADO**

🔐 Tienes acceso completo al Kill Switch y funciones administrativas.

⚠️ **Recuerda**: El Kill Switch es irreversible. Úsalo solo en verdaderas emergencias."""

        keyboard = [
            [InlineKeyboardButton("🚨 Proceder con Kill Switch", callback_data="emergency_kill_switch")],
            [InlineKeyboardButton("↩️ Menú Emergencia", callback_data="emergencia")],
        ]
        
        await query.edit_message_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await query.answer("❌ Aún no eres admin", show_alert=True)
        await show_admin_help(update, context)

async def get_my_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para obtener el ID de Telegram del usuario."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Sin username"
    first_name = update.effective_user.first_name or "Sin nombre"
    
    is_current_admin = is_admin(user_id)
    admin_status = "✅ ADMIN" if is_current_admin else "❌ No Admin"
    
    text = f"""🆔 **TU INFORMACIÓN DE TELEGRAM**

👤 **Nombre**: {escape_markdown(first_name)}
🏷️ **Username**: @{escape_markdown(username)}
🆔 **ID**: `{user_id}`
🔐 **Estado**: {admin_status}

💡 **Para ser admin**: Copia tu ID y configúralo en el archivo .env como ADMIN_TELEGRAM_ID"""

    keyboard = [
        [InlineKeyboardButton("📋 ID Copiable", callback_data=f"show_copyable_id_{user_id}")],
        [InlineKeyboardButton("🔧 ¿Cómo configurar?", callback_data="admin_help")],
    ]
    
    if update.message:
        await update.message.reply_text(
            text=text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    # Redirigir al menú anterior según contexto
    dest = context.user_data.get('return_to')
    if dest == 'emergencia':
        # Limpiar la pista y mostrar el menú de emergencia
        context.user_data.pop('return_to', None)
        await show_emergency_menu(update, context)
    else:
        await start(update, context)
    return ConversationHandler.END

async def risk_set_manual_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia la conversación para establecer un riesgo manual."""
    query = update.callback_query
    await query.answer()
    text = (
        "✍️ *Configurar Riesgo Manual*\\n\\n"
        "Por favor, introduce el porcentaje de riesgo fijo que deseas usar por operación (ej. `1.5` para 1.5%)\\.\\n\\n"
        "Este valor anulará el cálculo automático del modelo ML."
    )
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )
    return CONFIRM_MANUAL_RISK

async def confirm_manual_risk_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Valida y establece el valor de riesgo manual."""
    user_input = update.message.text
    try:
        risk_value = float(user_input.replace(',', '.'))
        if not (0 < risk_value <= 100):
            raise ValueError("El riesgo debe estar entre 0 y 100.")

        logic_stubs.set_risk_manual(risk_value)

        await update.message.reply_text(
            text=f"✅ *Riesgo manual establecido en {risk_value}%*\\.\n\nTodas las nuevas operaciones usarán este valor.",
            reply_markup=keyboards.get_gestion_riesgo_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )

        return ConversationHandler.END

    except (ValueError, TypeError):
        await update.message.reply_text(
            text="❌ *Valor inválido*\\.\n\nPor favor, introduce un número válido (ej. `1.5` o `2`)\\. Inténtalo de nuevo o cancela la operación.",
            reply_markup=keyboards.get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return CONFIRM_MANUAL_RISK

# --- Agrupación de Handlers para main.py ---

main_menu_handlers = [
    CallbackQueryHandler(start, pattern="^main_menu$"),
    CallbackQueryHandler(show_emergency_menu, pattern="^emergencia$"),
    CallbackQueryHandler(show_web_panel_access, pattern="^web_panel_access$"),
    # Subopciones del Panel Web
    CallbackQueryHandler(generate_web_token, pattern="^generate_web_token$"),
    CallbackQueryHandler(mobile_instructions, pattern="^mobile_instructions$"),
    CallbackQueryHandler(desktop_instructions, pattern="^desktop_instructions$"),
    # Emergencia subopciones
    CallbackQueryHandler(show_emergency_help, pattern="^emergency_help$"),
    CallbackQueryHandler(emergency_pause_all, pattern="^emergency_pause_all$"),
    CallbackQueryHandler(show_admin_help, pattern="^admin_help$"),
    CallbackQueryHandler(verify_admin_access, pattern="^verify_admin$"),
    # Gestión de riesgo
    CallbackQueryHandler(show_gestion_riesgo, pattern="^gestion_riesgo$"),
    CallbackQueryHandler(risk_show_config, pattern="^risk_show_config$"),
    CallbackQueryHandler(risk_define_size_menu, pattern="^risk_define_size$"),
    CallbackQueryHandler(risk_set_auto, pattern="^risk_set_auto$"),
    CallbackQueryHandler(risk_reset_custom, pattern="^risk_reset_custom$"),
]

action_handlers = []

conv_handlers = [
    ConversationHandler(
        entry_points=[CallbackQueryHandler(toggle_operative_mode, pattern="^control_toggle_mode$")],
        states={
            CONFIRM_LIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_and_set_live_mode)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
    per_user=True,
    per_chat=True,
    per_message=False,
    ),
    ConversationHandler(
        # Este es el nuevo handler para el Kill Switch unificado, accesible por botón y comando.
        entry_points=[
            CallbackQueryHandler(kill_switch_start, pattern="^emergency_kill_switch$"),
            CommandHandler("kill_switch", kill_switch_command_handler)
        ],
        states={
            CONFIRM_KILL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_kill_switch_password_handler)],
            CONFIRM_KILL_SWITCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_kill_switch)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        per_user=True,
        per_chat=True,
    per_message=False,
    ),
    ConversationHandler(
        # Nuevo handler para reanudar el sistema
        entry_points=[CallbackQueryHandler(resume_system_start, pattern="^emergency_resume_system$")],
        states={
            CONFIRM_RESUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_resume_system)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        per_user=True,
        per_chat=True,
    per_message=False,
    ),
    ConversationHandler(
        entry_points=[CallbackQueryHandler(risk_set_manual_start, pattern="^risk_set_manual$")],
        states={
            CONFIRM_MANUAL_RISK: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_manual_risk_value)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        per_user=True,
        per_chat=True,
        per_message=True,
    ),
    # Los handlers 'liquidate_start' y 'stop_start' se eliminan en favor del nuevo 'kill_switch_start'
]

# --- Exportar todas las funciones necesarias para main.py ---
__all__ = [
    'start', 'main_menu_handlers', 'action_handlers', 'conv_handlers', 'get_my_id',
    'show_control_operativo', 'show_gestion_riesgo', 'show_reportes_analisis', 
    'show_mlops_menu', 'show_system_menu', 'show_emergency_menu', 'show_panel_control'
]