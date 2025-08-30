"""
Quick Commands Module - Comandos simplificados para ITBOT
"""

from telegram import Update
from telegram.ext import ContextTypes
import sys
sys.path.append('/app')
import telegram_logic_adapter as logic_stubs

async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando: /dashboard - Muestra dashboard principal"""
    try:
        status = await logic_stubs.get_consolidated_status()
        
        mode = status.get('mode', 'N/A')
        running_status = '🟢 ACTIVO' if status.get('running') else '🔴 DETENIDO'
        daily_pnl = status.get('daily_pnl_percent', 0.0)
        total_pnl = status.get('total_pnl_percent', 0.0)
        open_positions = status.get('open_positions', 'N/A')
        
        daily_color = "🟢" if daily_pnl >= 0 else "🔴"
        total_color = "🟢" if total_pnl >= 0 else "🔴"
        
        text = f"""🤖 **ITBOT Dashboard v2.0**

📊 **ESTADO DEL SISTEMA**
{running_status} `{mode}`

💰 **RENDIMIENTO**
{daily_color} Diario: `{daily_pnl:.2f}%`
{total_color} Total: `{total_pnl:.2f}%`
📊 Posiciones: `{open_positions}`

💡 Usa /help para ver todos los comandos"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def cmd_pares(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando: /pares - Información de pares"""
    text = """🎯 **SISTEMA DINÁMICO DE PARES**

📊 **Estado**: En desarrollo
🔄 **Función**: Selección automática de pares óptimos
📈 **Objetivo**: Máximo rendimiento con riesgo controlado

💡 Sistema en implementación continua"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando: /help - Lista de comandos"""
    text = """🤖 **ITBOT - COMANDOS DISPONIBLES**

**🎯 PRINCIPALES**
• `/dashboard` - Dashboard principal
• `/pares` - Sistema dinámico  
• `/posiciones` - Posiciones abiertas
• `/pnl` - Rendimiento actual

**📊 ANÁLISIS**
• `/status` - Estado detallado
• `/salud` - Estado del sistema

**⚙️ GESTIÓN**
• `/config` - Configuración
• `/help` - Esta ayuda
• `/about` - Información del bot

💡 **Tip**: Usa `/start` para el menú principal con botones interactivos"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def cmd_posiciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando: /posiciones - Posiciones abiertas"""
    try:
        status = await logic_stubs.get_consolidated_status()
        positions = status.get('positions', [])
        
        if not positions:
            text = """📊 **POSICIONES ABIERTAS**
            
❌ No hay posiciones abiertas actualmente"""
        else:
            text = f"📊 **POSICIONES ABIERTAS** ({len(positions)})\n\n"
            
            for i, pos in enumerate(positions, 1):
                symbol = pos.get('symbol', 'N/A')
                side = pos.get('side', 'N/A') 
                size = pos.get('size', 0)
                pnl = pos.get('pnl', 0)
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                
                text += f"{i}. `{symbol}` - {side}\n"
                text += f"   📊 Tamaño: `{size}` {pnl_color} PnL: `{pnl:.2f}%`\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def cmd_pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando: /pnl - Rendimiento"""
    try:
        status = await logic_stubs.get_consolidated_status()
        
        daily_pnl = status.get('daily_pnl_percent', 0.0)
        total_pnl = status.get('total_pnl_percent', 0.0)
        
        daily_color = "🟢" if daily_pnl >= 0 else "🔴"
        total_color = "🟢" if total_pnl >= 0 else "🔴"
        
        text = f"""💰 **RENDIMIENTO ACTUAL**

{daily_color} **PnL Diario:** `{daily_pnl:.2f}%`
{total_color} **PnL Total:** `{total_pnl:.2f}%`

📊 **Estado:** `{status.get('mode', 'N/A')}`
📈 **Posiciones:** `{status.get('open_positions', 0)}`"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def cmd_salud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando: /salud - Estado del sistema"""
    try:
        status = await logic_stubs.get_consolidated_status()
        
        running = status.get('running', False)
        mode = status.get('mode', 'N/A')
        
        health_score = 70 if running else 30
        
        if health_score >= 70:
            health_icon = "🟢"
            health_text = "BUENO"
        else:
            health_icon = "🔴"
            health_text = "CRÍTICO"
        
        text = f"""🏥 **SALUD DEL SISTEMA**

{health_icon} **Estado General:** `{health_text}` ({health_score}/100)

📊 **Componentes:**
• Sistema: {'🟢 OK' if running else '🔴 DETENIDO'}
• Modo: `{mode}`

💡 Usa /dashboard para más detalles"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando: /about - Información del bot"""
    text = """🤖 **ITBOT v2.0 - Sistema Dinámico**

📊 **CARACTERÍSTICAS**
• Selección dinámica de pares
• Análisis técnico automatizado
• Gestión de riesgo inteligente
• Machine Learning integrado

🎯 **SISTEMA DINÁMICO**
• Análisis continuo de mercado
• Adaptación automática
• Optimización de rendimiento

**Desarrollado para trading automatizado seguro**"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

# Diccionario de comandos simplificado
QUICK_COMMANDS = {
    "dashboard": cmd_dashboard,
    "d": cmd_dashboard,
    "status": cmd_dashboard,
    
    "pares": cmd_pares,
    "pairs": cmd_pares,
    
    "posiciones": cmd_posiciones,
    "pos": cmd_posiciones,
    
    "pnl": cmd_pnl,
    "rendimiento": cmd_pnl,
    
    "salud": cmd_salud,
    "health": cmd_salud,
    
    "help": cmd_help,
    "ayuda": cmd_help,
    
    "about": cmd_about,
    "info": cmd_about,
}
