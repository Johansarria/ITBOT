"""
Enhanced Dashboard Module - Dashboard mejorado para ITBOT

Proporciona una interfaz de usuario mejorada con información en tiempo real,
accesos rápidos y integración completa del sistema dinámico.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Importaciones locales
import telegram_logic_adapter as logic_stubs
from modules.dynamic_pair_manager import dynamic_pair_manager

def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales para MarkdownV2."""
    text = str(text)
    escape_chars = r'_*[]()~`>#+-.=|{}!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\\1', text)

async def enhanced_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Dashboard principal mejorado con integración del sistema dinámico
    """
    try:
        # Obtener estado consolidado del sistema
        status = await logic_stubs.get_consolidated_status()
        
        # Obtener estado del sistema dinámico
        dynamic_status = await dynamic_pair_manager.get_status_report()
        dynamic_info = dynamic_status.get("system_status", {})
        
        # Formatear información básica del sistema
        mode = status.get('mode', 'N/A')
        running_status = '🟢 ACTIVO' if status.get('running') else '🔴 DETENIDO'
        
        # Información de pares dinámicos
        current_pairs = dynamic_info.get('current_pairs', [])
        pairs_count = len(current_pairs)
        pairs_display = ', '.join(current_pairs[:4])
        if len(current_pairs) > 4:
            pairs_display += f" (+{len(current_pairs)-4} más)"
        
        # Última evaluación dinámica
        last_eval = dynamic_info.get('last_evaluation')
        hours_since = dynamic_info.get('hours_since_last_evaluation', 0)
        
        if last_eval and hours_since is not None:
            if hours_since < 1:
                eval_time = f"Hace {int(hours_since * 60)}min"
            else:
                eval_time = f"Hace {hours_since:.1f}h"
        else:
            eval_time = "Nunca"
        
        # PnL información
        daily_pnl = status.get('daily_pnl_percent', 0.0)
        total_pnl = status.get('total_pnl_percent', 0.0)
        
        # Determinar color de PnL
        daily_color = "🟢" if daily_pnl >= 0 else "🔴"
        total_color = "🟢" if total_pnl >= 0 else "🔴"
        
        # Información de posiciones
        open_positions = status.get('open_positions', 'N/A')
        
        # Hora actual
        now = datetime.now().strftime("%H:%M")
        
        # Construir mensaje del dashboard
        text = f"""🤖 *ITBOT v2\\.0 \\- Dashboard Principal*
{'━' * 35}

📊 *ESTADO DEL SISTEMA*
{running_status} `{escape_markdown(mode)}` \\| 🕐 {escape_markdown(now)}

🎯 *SISTEMA DINÁMICO*
📈 {escape_markdown(str(pairs_count))} pares activos \\| ⏰ {escape_markdown(eval_time)}
`{escape_markdown(pairs_display)}`

💰 *RENDIMIENTO*
{daily_color} Diario: `{escape_markdown(f'{daily_pnl:.2f}')}%` \\| {total_color} Total: `{escape_markdown(f'{total_pnl:.2f}')}%`
📊 Posiciones: `{escape_markdown(str(open_positions))}`

{'━' * 35}
⚡ *ACCESOS RÁPIDOS*"""

        # Crear teclado con accesos rápidos
        keyboard = [
            [
                InlineKeyboardButton("🔄 Re-evaluar", callback_data="quick_reevaluate"),
                InlineKeyboardButton("📈 Posiciones", callback_data="quick_positions"),
                InlineKeyboardButton("🛡️ Escudos", callback_data="quick_shields")
            ],
            [
                InlineKeyboardButton("🎯 Pares Dinámicos", callback_data="dynamic_system_menu"),
                InlineKeyboardButton("⚡ Dashboard", callback_data="quick_refresh")
            ],
            [
                InlineKeyboardButton("⚙️ Control Operativo", callback_data="control_operativo"),
                InlineKeyboardButton("🕹️ Panel Control", callback_data="panel_control")
            ],
            [
                InlineKeyboardButton("⚖️ Gestión Riesgo", callback_data="gestion_riesgo"),
                InlineKeyboardButton("📈 Reportes", callback_data="reportes_analisis")
            ],
            [
                InlineKeyboardButton("🧠 MLOps", callback_data="inteligencia_mlops"),
                InlineKeyboardButton("🛠️ Sistema", callback_data="sistema_mantenimiento")
            ],
            [InlineKeyboardButton("🚨 EMERGENCIA 🚨", callback_data="emergencia")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        elif update.callback_query:
            query = update.callback_query
            await query.answer()
            try:
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
            except Exception as e:
                # Si no se puede editar, enviar nuevo mensaje
                await query.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN_V2
                )
        
    except Exception as e:
        error_text = f"❌ Error cargando dashboard: {str(e)}"
        if update.message:
            await update.message.reply_text(error_text)
        elif update.callback_query:
            await update.callback_query.answer(error_text)

async def dynamic_system_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Menú dedicado al sistema dinámico de pares
    """
    try:
        # Obtener información detallada del sistema dinámico
        dynamic_status = await dynamic_pair_manager.get_status_report()
        system_info = dynamic_status.get("system_status", {})
        config_info = dynamic_status.get("configuration", {})
        history_info = dynamic_status.get("history", {})
        
        # Información de pares
        current_pairs = system_info.get('current_pairs', [])
        pairs_count = len(current_pairs)
        
        # Última evaluación
        last_eval = system_info.get('last_evaluation')
        hours_since = system_info.get('hours_since_last_evaluation', 0)
        
        if last_eval and hours_since is not None:
            if hours_since < 1:
                eval_time = f"hace {int(hours_since * 60)}min"
            else:
                eval_time = f"hace {hours_since:.1f}h"
        else:
            eval_time = "nunca"
        
        # Necesidad de re-evaluación
        needs_reeval = system_info.get('needs_reevaluation', False)
        reeval_status = "⚠️ Pendiente" if needs_reeval else "✅ Actualizado"
        
        # Próxima evaluación automática
        reeval_interval = config_info.get('reevaluation_interval_hours', 24)
        if hours_since is not None:
            hours_remaining = reeval_interval - hours_since
            if hours_remaining > 0:
                next_eval = f"en {hours_remaining:.1f}h"
            else:
                next_eval = "muy pronto"
        else:
            next_eval = f"en {reeval_interval}h"
        
        # Top 6 pares con numeración
        top_pairs = current_pairs[:6]
        pairs_text = ""
        for i, pair in enumerate(top_pairs, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}\\."
            pairs_text += f"{medal} `{escape_markdown(pair)}`\\n"
        
        if len(current_pairs) > 6:
            pairs_text += f"\\.\\.\\. \\+{len(current_pairs) - 6} pares más"
        
        # Historial reciente
        total_evaluations = history_info.get('total_evaluations', 0)
        
        text = f"""🎯 *SISTEMA DINÁMICO \\- Pares Inteligentes*
{'━' * 40}

📊 *ESTADO ACTUAL*
✅ {escape_markdown(str(pairs_count))} pares activos \\| {escape_markdown(reeval_status)}
⏰ Última evaluación: {escape_markdown(eval_time)}
🔄 Próxima evaluación: {escape_markdown(next_eval)}

📈 *PARES ACTIVOS* \\(top {len(top_pairs)}\\)
{pairs_text}

📊 *ESTADÍSTICAS*
🔢 Total evaluaciones: {escape_markdown(str(total_evaluations))}
⚙️ Intervalo: {escape_markdown(str(reeval_interval))}h automático

{'━' * 40}"""

        keyboard = [
            [
                InlineKeyboardButton("🔄 Re-evaluar Ahora", callback_data="dynamic_force_update"),
                InlineKeyboardButton("📊 Ver Todos", callback_data="dynamic_show_all_pairs")
            ],
            [
                InlineKeyboardButton("📈 Métricas Detalle", callback_data="dynamic_metrics"),
                InlineKeyboardButton("📋 Historial", callback_data="dynamic_history_view")
            ],
            [
                InlineKeyboardButton("⚙️ Configurar", callback_data="dynamic_config"),
                InlineKeyboardButton("🔍 Análisis", callback_data="dynamic_analysis")
            ],
            [
                InlineKeyboardButton("↩️ Dashboard", callback_data="enhanced_dashboard"),
                InlineKeyboardButton("🏠 Menú Principal", callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
    except Exception as e:
        error_text = f"❌ Error cargando sistema dinámico: {str(e)}"
        if update.callback_query:
            await update.callback_query.answer(error_text)

async def quick_reevaluate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Re-evaluación rápida del sistema dinámico
    """
    query = update.callback_query
    await query.answer("🔄 Iniciando re-evaluación...")
    
    try:
        # Enviar mensaje de progreso
        progress_text = """🔄 *RE\\-EVALUACIÓN EN PROGRESO*

⏳ Analizando 411 pares USDT\\.\\.\\.
📊 Calculando scores composite\\.\\.\\.
🎯 Seleccionando mejores pares\\.\\.\\.

*Por favor espera\\.\\.\\.*"""
        
        await query.edit_message_text(
            text=progress_text,
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
        # Realizar re-evaluación
        changes_made, change_details = await dynamic_pair_manager.force_reevaluation()
        
        if change_details is None:
            await query.edit_message_text("❌ Error durante la re-evaluación")
            return
        
        # Formatear resultados
        if changes_made:
            pairs_added = change_details.get('pairs_added', [])
            pairs_removed = change_details.get('pairs_removed', [])
            pairs_maintained = change_details.get('pairs_maintained', [])
            
            result_text = "✅ *RE\\-EVALUACIÓN COMPLETADA*\\n\\n"
            
            if pairs_added:
                added_list = ', '.join([f"`{escape_markdown(p)}`" for p in pairs_added])
                result_text += f"✅ *Agregados:* {added_list}\\n"
            
            if pairs_removed:
                removed_list = ', '.join([f"`{escape_markdown(p)}`" for p in pairs_removed])
                result_text += f"❌ *Removidos:* {removed_list}\\n"
            
            total_pairs = len(change_details.get('new_pairs', []))
            result_text += f"\\n📊 *Total Pares:* {escape_markdown(str(total_pairs))}"
            
        else:
            result_text = """✅ *RE\\-EVALUACIÓN COMPLETADA*

ℹ️ *No se requirieron cambios*
🎯 Los pares actuales siguen siendo óptimos"""
        
        duration = change_details.get('evaluation_duration_seconds', 0)
        result_text += f"\\n⏱️ *Duración:* {escape_markdown(f'{duration:.1f}')}s"
        
        # Botones de seguimiento
        keyboard = [
            [
                InlineKeyboardButton("🎯 Ver Pares", callback_data="dynamic_system_menu"),
                InlineKeyboardButton("⚡ Dashboard", callback_data="enhanced_dashboard")
            ]
        ]
        
        await query.edit_message_text(
            text=result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        
    except Exception as e:
        error_text = f"❌ Error en re-evaluación: {str(e)}"
        await query.edit_message_text(error_text)

# Diccionario de handlers para fácil registro
ENHANCED_HANDLERS = {
    "enhanced_dashboard": enhanced_dashboard,
    "dynamic_system_menu": dynamic_system_menu,
    "quick_reevaluate": quick_reevaluate,
    "quick_refresh": enhanced_dashboard,  # Alias para refrescar dashboard
}
