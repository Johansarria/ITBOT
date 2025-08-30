"""
Enhanced Dashboard Module - Dashboard mejorado para ITBOT (Versión Simplificada)
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import re
import sys
import os

# Agregar el path del app para las importaciones
sys.path.append('/app')

# Importaciones locales
import telegram_logic_adapter as logic_stubs

def escape_markdown(text: str) -> str:
    """Escapa caracteres especiales para MarkdownV2."""
    text = str(text)
    escape_chars = r'_*[]()~`>#+-.=|{}!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\\1', text)

async def enhanced_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Dashboard principal mejorado con información básica del sistema
    """
    try:
        # Obtener estado consolidado del sistema
        status = await logic_stubs.get_consolidated_status()
        
        # Formatear información básica del sistema
        mode = status.get('mode', 'N/A')
        running_status = '🟢 ACTIVO' if status.get('running') else '🔴 DETENIDO'
        
        # PnL información
        daily_pnl = status.get('daily_pnl_percent', 0.0)
        total_pnl = status.get('total_pnl_percent', 0.0)
        
        # Determinar color de PnL
        daily_color = "🟢" if daily_pnl >= 0 else "🔴"
        total_color = "🟢" if total_pnl >= 0 else "🔴"
        
        # Información de posiciones
        open_positions = status.get('open_positions', 'N/A')
        
        # Construir mensaje del dashboard
        text = f"""🤖 *ITBOT v2\\.0 \\- Dashboard Principal*
{'━' * 35}

📊 *ESTADO DEL SISTEMA*
{running_status} `{escape_markdown(mode)}`

💰 *RENDIMIENTO*
{daily_color} Diario: `{escape_markdown(f'{daily_pnl:.2f}')}%` \\| {total_color} Total: `{escape_markdown(f'{total_pnl:.2f}')}%`
📊 Posiciones: `{escape_markdown(str(open_positions))}`

{'━' * 35}"""

        # Crear teclado con accesos rápidos
        keyboard = [
            [
                InlineKeyboardButton("📈 Posiciones", callback_data="panel_show_positions"),
                InlineKeyboardButton("🛡️ Escudos", callback_data="panel_show_shields")
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
            [InlineKeyboardButton("🏠 Menú Principal", callback_data="main_menu")]
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

# Diccionario de handlers para fácil registro
ENHANCED_HANDLERS = {
    "enhanced_dashboard": enhanced_dashboard,
}
