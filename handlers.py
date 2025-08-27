# handlers.py

"""
Módulo de Handlers de Telegram.

Contiene toda la lógica de la interfaz de usuario, manejando los comandos
y las acciones de los botones (CallbackQuery).
"""

import re
from typing import Dict, Any, List

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

# Importaciones locales
import keyboards
import telegram_logic_adapter as logic_stubs

# --- Estados para ConversationHandler ---
CONFIRM_LIVE, CONFIRM_LIQUIDATE, CONFIRM_STOP, CONFIRM_MANUAL_RISK = range(4)

# --- Helper para escapar Markdown ---
def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales para MarkdownV2."""
    # Asegurarse de que el input sea un string
    text = str(text)
    escape_chars = r'_*[]()~`>#+-.=|{}!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# --- Handlers de Comandos ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para el comando /start. Muestra el menú principal con un resumen completo."""
    status = await logic_stubs.get_consolidated_status()

    # Escapar todos los valores dinámicos
    summary_data = {
        "mode": escape_markdown(status.get('mode', 'N/A')),
        "running_status": '✅ ACTIVO' if status.get('running') else '🛑 DETENIDO',
        "shield_status_text": f"🛡️ ACTIVOS" if any(status.get('shield_status', {}).values()) else f"✅ INACTIVOS",
        "open_positions": escape_markdown(status.get('open_positions', 'N/A')),
        "market_regime": escape_markdown(status.get('market_regime', 'N/A')),
        "daily_pnl_percent": escape_markdown(f"{status.get('daily_pnl_percent', 0.0):.2f}"),
        "total_pnl_percent": escape_markdown(f"{status.get('total_pnl_percent', 0.0):.2f}")
    }

    summary_text = (
        f"*Modo*: `{summary_data['mode']}` \\| *Estado*: `{summary_data['running_status']}`\n"
        f"*Escudos*: `{summary_data['shield_status_text']}` \\| *Posiciones*: `{summary_data['open_positions']}`\n"
        f"*Régimen*: `{summary_data['market_regime']}`\n"
        f"*PNL Diario*: `{summary_data['daily_pnl_percent']}%` \\| *PNL Total*: `{summary_data['total_pnl_percent']}%`"
    )

    text = f"""🤖 *Menú Principal de ITBOT* 🤖

*Resumen Operativo:*
{escape_markdown('------------------------------------')}
{summary_text}
{escape_markdown('------------------------------------')}

_Selecciona una categoría para empezar_"""

    keyboard = keyboards.get_main_menu_keyboard()
    
    if update.message:
        await update.message.reply_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )


# --- Handlers de Menús Principales ---
async def show_control_operativo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    current_mode = await logic_stubs.get_bot_mode()
    text = f"⚙️ *Control Operativo*\\n\\nModo actual: `{escape_markdown(current_mode)}`\\n\\nSelecciona una acción\\."
    
    if current_mode == 'LIVE':
        keyboard = keyboards.get_control_operativo_live_keyboard()
    else:
        keyboard = keyboards.get_control_operativo_keyboard()

    await query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_gestion_riesgo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "⚖️ *Gestión de Riesgo*\\n\\nDefine parámetros de riesgo y tamaño de las operaciones\\."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_gestion_riesgo_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_reportes_analisis(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "📈 *Reportes y Análisis*\\n\\nAnaliza el rendimiento y las decisiones pasadas del bot\\."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_reportes_analisis_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_mlops_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🧠 *Inteligencia y MLOps*\\n\\nSupervisa los modelos de IA y el estado del mercado\\."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_mlops_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_system_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🛠️ *Sistema y Mantenimiento*\\n\\nVerifica la salud de los componentes del sistema\\."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_system_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_emergency_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🚨 *MENÚ DE EMERGENCIA* 🚨\\n\\nUsa estas opciones con extrema precaución\\. Son acciones irreversibles\\."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_emergency_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_panel_control(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "🕹️ *Panel de Control*\\n\\nMonitoriza el estado del bot en tiempo real\\."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_panel_control_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )


# --- Handlers de Acciones Específicas ---

async def reports_show_discarded(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Consultando señales...")
    signals = await logic_stubs.get_last_discarded_signals()
    
    if not signals:
        text = "✅ No hay señales descartadas recientemente\\."
    else:
        text_parts = ["*Últimas Señales Descartadas*"]
        for s in signals:
            ts = escape_markdown(s.get('timestamp', 'N/A'))
            asset = escape_markdown(s.get('asset', 'N/A'))
            signal = escape_markdown(s.get('signal', 'N/A'))
            reason = escape_markdown(s.get('reason', 'N/A'))
            text_parts.append(f"`{ts}` - `{asset}` - `{signal}` - *Razón*: {reason}")
        text = "\\n".join(text_parts)

    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_reportes_analisis_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def system_health_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Verificando servicios...")
    health = await logic_stubs.check_services_health()
    
    text_parts = ["*❤️ Verificación de Salud del Sistema*"]
    for service, status in health.items():
        icon = "✅" if "OPERATIONAL" in status or "ACTIVE" in status else "❌"
        service_esc = escape_markdown(service)
        status_esc = escape_markdown(status)
        text_parts.append(f"{icon} *{service_esc}*: `{status_esc}`")
    
    text = "\\n".join(text_parts)
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_system_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

# --- Handlers para los botones nuevos ---

async def risk_define_size_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text = "📏 *Definir Tamaño de Orden*\\n\\nSelecciona cómo se debe calcular el riesgo para cada operación\\."
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_risk_size_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def mlops_show_regime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Analizando régimen de mercado...")
    regime = await logic_stubs.get_market_regime()
    text = f"🧠 *Régimen de Mercado Actual*\\n\\nEl modelo de IA ha detectado un régimen: `{escape_markdown(regime)}`"
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_mlops_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def mlops_model_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Consultando estado del modelo...")
    status = await logic_stubs.get_ml_model_status()
    
    status_escaped = {k: escape_markdown(v) for k, v in status.items()}
    
    text = f"""
🤖 *Estado del Modelo de Machine Learning*

- *ID de Modelo*: `{status_escaped.get('model_id', 'N/A')}`
- *Último Reentrenamiento*: `{status_escaped.get('last_retrained', 'N/A')}`
- *Drift de Performance*: `{status_escaped.get('performance_drift', 'N/A')}`
- *Próximo Entrenamiento*: `{status_escaped.get('next_training_scheduled', 'N/A')}`"""
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_mlops_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def panel_show_positions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra un resumen de las posiciones abiertas."""
    query = update.callback_query
    await query.answer("Consultando posiciones abiertas...")
    summary = await logic_stubs.get_open_positions_summary(context.bot)
    await query.edit_message_text(
        text=summary,
        reply_markup=keyboards.get_panel_control_keyboard(),
        parse_mode=ParseMode.HTML
    )

async def panel_show_shields(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Muestra el estado de los escudos de protección."""
    query = update.callback_query
    await query.answer()
    status_text = logic_stubs.get_shield_status()
    text = f"🛡️ *Estado de los Escudos*\n\n{escape_markdown(status_text)}"
    await query.edit_message_text(
        text=text,
        reply_markup=keyboards.get_panel_control_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def risk_set_auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Configura el riesgo en modo automático."""
    query = update.callback_query
    await query.answer("Cambiando a riesgo automático...")
    logic_stubs.set_risk_auto()
    await query.edit_message_text(
        text="✅ *Riesgo configurado en modo Automático*\\.\n\nEl sistema ajustará el riesgo según el modelo ML.",
        reply_markup=keyboards.get_risk_size_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

# --- Conversation and Action Handlers ---

async def set_mode_paper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Cambiando a modo PAPER...")
    await logic_stubs.set_bot_mode("PAPER_TRADING")
    await show_control_operativo(update, context)

async def change_mode_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    current_mode = await logic_stubs.get_bot_mode()

    if current_mode == 'LIVE':
        text = "✅ El bot ya se encuentra en modo `LIVE`\\."
        keyboard = keyboards.get_control_operativo_live_keyboard()
    else:
        text = (
            f"⚠️ *Confirmación Requerida* ⚠️\\n\\n"
            f"El bot está actualmente en modo `{escape_markdown(current_mode)}`\\.\\n\\n"
            f"Para cambiar a modo **LIVE**, por favor, escribe `CONFIRMAR LIVE`\\. \\n\\n"
            f"Esta acción expondrá capital real al mercado\\."
        )
        keyboard = keyboards.get_cancel_keyboard()

    await query.edit_message_text(
        text=text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )
    
    return CONFIRM_LIVE if current_mode != 'LIVE' else ConversationHandler.END


async def confirm_live_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message and update.message.text == "CONFIRMAR LIVE":
        await update.message.reply_text(
            text="✅ Confirmado\\. Cambiando a modo LIVE\\.\\.\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        await logic_stubs.set_bot_mode("LIVE")
        
        # Simular un callback query para volver al menú anterior
        from telegram import CallbackQuery
        fake_query = CallbackQuery(id="fake_query_from_live_confirm", user=update.message.from_user, chat_instance="fake_chat")
        fake_update = Update(update.update_id, callback_query=fake_query)
        fake_update.callback_query.message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Cargando menú...")
        await show_control_operativo(fake_update, context)
        
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            text="❌ Texto incorrecto\\. Escribe `CONFIRMAR LIVE` o presiona cancelar\\.",
            reply_markup=keyboards.get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return CONFIRM_LIVE

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
        await logic_stubs.liquidate_all_positions()
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

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la acción actual y vuelve al menú principal."""
    query = update.callback_query
    await query.answer()
    # Reutilizamos la función start para mostrar el menú principal
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
        # Reemplazar comas por puntos para formatos decimales europeos
        risk_value = float(user_input.replace(',', '.'))
        if not (0 < risk_value <= 100):
            raise ValueError("El riesgo debe estar entre 0 y 100.")

        logic_stubs.set_risk_manual(risk_value)

        await update.message.reply_text(
            text=f"✅ *Riesgo manual establecido en {risk_value}%*\\.\n\nTodas las nuevas operaciones usarán este valor.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        # Volver al menú de gestión de riesgo
        # Simular un callback query para la navegación
        from telegram import CallbackQuery
        fake_query = CallbackQuery(id="fake_query_from_risk_confirm", user=update.message.from_user, chat_instance="fake_chat")
        fake_update = Update(update.update_id, callback_query=fake_query)
        # Es necesario crear un mensaje 'falso' al que responder
        fake_update.callback_query.message = await context.bot.send_message(chat_id=update.effective_chat.id, text="Cargando menú...")
        await show_gestion_riesgo(fake_update, context)

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
    CallbackQueryHandler(show_control_operativo, pattern="^control_operativo$"),
    CallbackQueryHandler(show_panel_control, pattern="^panel_control$"),
    CallbackQueryHandler(show_gestion_riesgo, pattern="^gestion_riesgo$"),
    CallbackQueryHandler(show_reportes_analisis, pattern="^reportes_analisis$"),
    CallbackQueryHandler(show_mlops_menu, pattern="^inteligencia_mlops$"),
    CallbackQueryHandler(show_system_menu, pattern="^sistema_mantenimiento$"),
    CallbackQueryHandler(show_emergency_menu, pattern="^emergencia$"),
]

action_handlers = [
    CallbackQueryHandler(reports_show_discarded, pattern="^reports_show_discarded$"),
    CallbackQueryHandler(system_health_check, pattern="^system_health_check$"),
    CallbackQueryHandler(risk_define_size_menu, pattern="^risk_define_size$"),
    CallbackQueryHandler(mlops_show_regime, pattern="^mlops_show_regime$"),
    CallbackQueryHandler(mlops_model_status, pattern="^mlops_model_status$"),
    CallbackQueryHandler(set_mode_paper, pattern="^control_set_paper$"),
    CallbackQueryHandler(panel_show_positions, pattern="^panel_show_positions$"),
    CallbackQueryHandler(panel_show_shields, pattern="^panel_show_shields$"),
    CallbackQueryHandler(risk_set_auto, pattern="^risk_set_auto$"),
]

conv_handlers = [
    ConversationHandler(
        entry_points=[CallbackQueryHandler(change_mode_start, pattern="^control_change_mode$")],
        states={
            CONFIRM_LIVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_live_mode)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        per_user=True,
        per_chat=True,
        per_message=True,
    ),
    ConversationHandler(
        entry_points=[CallbackQueryHandler(liquidate_start, pattern="^emergency_liquidate$")],
        states={
            CONFIRM_LIQUIDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_liquidate)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        per_user=True,
        per_chat=True,
        per_message=True,
    ),
    ConversationHandler(
        entry_points=[CallbackQueryHandler(stop_start, pattern="^emergency_full_stop$")],
        states={
            CONFIRM_STOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_stop)]
        },
        fallbacks=[CallbackQueryHandler(cancel_conversation, pattern="^cancel_conversation$")],
        per_user=True,
        per_chat=True,
        per_message=True,
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
]