"""
Quick Commands Module - Comandos alias intuitivos para ITBOT

Proporciona comandos rápidos y fáciles de recordar para acceder
a las funciones principales del bot.
"""

from telegram import Update
from telegram.ext import ContextTypes
from handlers.enhanced_dashboard import enhanced_dashboard, dynamic_system_menu
from handlers.dynamic_commands import (
    cmd_dynamic_status, 
    cmd_dynamic_force_update, 
    cmd_dynamic_pairs,
    cmd_dynamic_history
)
import telegram_logic_adapter as logic_stubs

async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /dashboard - Muestra dashboard principal mejorado
    Alias: /d, /status, /estado
    """
    await enhanced_dashboard(update, context)

async def cmd_pares(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /pares - Muestra sistema dinámico de pares
    Alias: /p, /pairs, /dinamico
    """
    await dynamic_system_menu(update, context)

async def cmd_reevaluar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /reevaluar - Fuerza re-evaluación de pares
    Alias: /reeval, /actualizar, /update
    """
    # Convertir a formato esperado por el comando dinámico
    class MockMessage:
        def __init__(self, update):
            self.from_user = update.effective_user
            self.chat = update.effective_chat
            self.message_id = update.message.message_id if update.message else None
            
        async def reply(self, text, parse_mode=None):
            if update.message:
                await update.message.reply_text(text, parse_mode=parse_mode)
            elif update.callback_query:
                await update.callback_query.message.reply_text(text, parse_mode=parse_mode)
    
    mock_message = MockMessage(update)
    await cmd_dynamic_force_update(mock_message)

async def cmd_posiciones(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /posiciones - Muestra posiciones abiertas
    Alias: /pos, /positions
    """
    try:
        # Usar la lógica existente
        status = await logic_stubs.get_consolidated_status()
        positions = status.get('positions', [])
        
        if not positions:
            text = """📊 *POSICIONES ABIERTAS*
            
❌ No hay posiciones abiertas actualmente"""
        else:
            text = f"📊 *POSICIONES ABIERTAS* ({len(positions)})\n\n"
            
            for i, pos in enumerate(positions, 1):
                symbol = pos.get('symbol', 'N/A')
                side = pos.get('side', 'N/A') 
                size = pos.get('size', 0)
                pnl = pos.get('pnl', 0)
                pnl_color = "🟢" if pnl >= 0 else "🔴"
                
                text += f"{i}\\. `{symbol}` \\- {side}\n"
                text += f"   📊 Tamaño: `{size}` {pnl_color} PnL: `{pnl:.2f}%`\n\n"
        
        await update.message.reply_text(text, parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error obteniendo posiciones: {str(e)}")

async def cmd_pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /pnl - Muestra rendimiento actual
    Alias: /rendimiento, /performance
    """
    try:
        status = await logic_stubs.get_consolidated_status()
        
        daily_pnl = status.get('daily_pnl_percent', 0.0)
        total_pnl = status.get('total_pnl_percent', 0.0)
        
        daily_color = "🟢" if daily_pnl >= 0 else "🔴"
        total_color = "🟢" if total_pnl >= 0 else "🔴"
        
        text = f"""💰 *RENDIMIENTO ACTUAL*

{daily_color} *PnL Diario:* `{daily_pnl:.2f}%`
{total_color} *PnL Total:* `{total_pnl:.2f}%`

📊 *Estado:* `{status.get('mode', 'N/A')}`
📈 *Posiciones:* `{status.get('open_positions', 0)}`"""
        
        await update.message.reply_text(text, parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error obteniendo PnL: {str(e)}")

async def cmd_config(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /config - Configuración rápida
    Alias: /configurar, /settings
    """
    text = """⚙️ *CONFIGURACIÓN RÁPIDA*

🔧 **Comandos Telegram \\(Básicos\\):**
• `/modo` \\- Cambiar modo LIVE/PAPER
• `/escudos` \\- Activar/desactivar escudos
• `/riesgo` \\- Configurar gestión de riesgo
• `/pares` \\- Configurar pares dinámicos

🌐 **Panel Web \\(Avanzado\\):**
• `/web` \\- Acceder al panel web
• Configuración detallada de estrategias
• Backtesting y optimización
• Análisis técnico avanzado
• Histórico y métricas completas

🎯 **Accesos Directos:**
• `/dashboard` \\- Dashboard principal
• `/posiciones` \\- Ver posiciones
• `/pnl` \\- Rendimiento actual
• `/salud` \\- Estado del sistema

📚 **Ayuda:**
• `/help` \\- Lista completa de comandos
• `/about` \\- Información del bot"""
    
    await update.message.reply_text(text, parse_mode='MarkdownV2')

async def cmd_salud(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /salud - Estado de salud del sistema
    Alias: /health, /sistema
    """
    try:
        # Obtener estado consolidado
        status = await logic_stubs.get_consolidated_status()
        
        # Estado básico
        running = status.get('running', False)
        mode = status.get('mode', 'N/A')
        
        # Estado dinámico
        from modules.dynamic_pair_manager import dynamic_pair_manager
        dynamic_status = await dynamic_pair_manager.get_status_report()
        dynamic_info = dynamic_status.get("system_status", {})
        
        pairs_count = len(dynamic_info.get('current_pairs', []))
        is_dynamic_init = dynamic_info.get('is_initialized', False)
        
        # Determinar salud general
        health_score = 0
        health_issues = []
        
        if running:
            health_score += 30
        else:
            health_issues.append("Sistema no está ejecutándose")
            
        if is_dynamic_init:
            health_score += 25
        else:
            health_issues.append("Sistema dinámico no inicializado")
            
        if pairs_count >= 5:
            health_score += 25
        else:
            health_issues.append(f"Pocos pares activos ({pairs_count})")
            
        # Verificar shields
        shields = status.get('shield_status', {})
        if any(shields.values()):
            health_score += 10
            health_issues.append("Escudos activados (precaución)")
        else:
            health_score += 20
        
        # Determinar color de salud
        if health_score >= 90:
            health_icon = "🟢"
            health_text = "EXCELENTE"
        elif health_score >= 70:
            health_icon = "🟡" 
            health_text = "BUENO"
        elif health_score >= 50:
            health_icon = "🟠"
            health_text = "REGULAR"  
        else:
            health_icon = "🔴"
            health_text = "CRÍTICO"
        
        text = f"""🏥 *SALUD DEL SISTEMA*

{health_icon} **Estado General:** `{health_text}` \\({health_score}/100\\)

📊 **Componentes:**
• Sistema: {'🟢 OK' if running else '🔴 DETENIDO'}
• Dinámico: {'🟢 OK' if is_dynamic_init else '🔴 ERROR'}  
• Pares: {'🟢' if pairs_count >= 5 else '🟡'} `{pairs_count} activos`
• Escudos: {'⚠️ ACTIVOS' if any(shields.values()) else '🟢 NORMALES'}

🎯 **Modo Actual:** `{mode}`"""

        if health_issues:
            issues_text = '\n'.join([f"• {issue}" for issue in health_issues])
            text += f"\n\n⚠️ **Observaciones:**\n{issues_text}"
            
        await update.message.reply_text(text, parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error verificando salud del sistema: {str(e)}")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /help - Lista completa de comandos
    """
    text = """🤖 *ITBOT \\- COMANDOS DISPONIBLES*

**⚡ ACCESO RÁPIDO**
• `/q` \\- Resumen ultra\\-rápido
• `/d` \\- Dashboard principal
• `/web` \\- Panel web avanzado

**🎯 PRINCIPALES**
• `/dashboard` \\- Dashboard principal
• `/pares` \\- Sistema dinámico  
• `/posiciones` \\- Posiciones abiertas
• `/pnl` \\- Rendimiento actual

**⚡ ACCIONES RÁPIDAS**
• `/reevaluar` \\- Re\\-evaluar pares
• `/salud` \\- Estado del sistema
• `/config` \\- Configuración

**🌐 ARQUITECTURA HÍBRIDA**
• � **Telegram:** Monitoreo básico
• 🌐 **Web:** Configuración avanzada
• `/web` \\- Acceso al panel completo

**�📊 ANÁLISIS**
• `/status` \\- Estado detallado
• `/historial` \\- Historial dinámico
• `/metricas` \\- Métricas avanzadas

**⚙️ GESTIÓN**
• `/modo` \\- Cambiar LIVE/PAPER
• `/escudos` \\- Control de escudos
• `/riesgo` \\- Gestión de riesgo

**🚨 EMERGENCIA**
• `/parar` \\- Detener sistema
• `/liquidar` \\- Liquidar posiciones
• `/emergencia` \\- Menú de emergencia

💡 *Tip: Usa* `/start` *para el menú principal*
🌐 *Panel Web: Configuración avanzada y backtesting*"""

    await update.message.reply_text(text, parse_mode='MarkdownV2')

async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /about - Información del bot
    """
    text = """🤖 *ITBOT v2\\.0 \\- Sistema Dinámico*

**📊 CARACTERÍSTICAS**
• Selección dinámica de pares
• Análisis de 411+ pares USDT
• Múltiples estrategias de trading
• Gestión automática de riesgo
• Machine Learning integrado

**🎯 SISTEMA DINÁMICO**
• Re\\-evaluación automática cada 24h
• Análisis composite scoring
• Diversificación por sectores
• Adaptación a condiciones de mercado

**🔧 VERSIÓN**
• Versión: `2\\.0\\.0`
• Docker: `✅ Containerizado`
• Base de datos: `PostgreSQL \\+ CSV Fallback`
• Telegram: `✅ Bot API`

**👨‍💻 DESARROLLO**
Sistema desarrollado para trading automatizado
con enfoque en seguridad y rendimiento\\.

*¿Necesitas ayuda?* Usa `/help`"""

    await update.message.reply_text(text, parse_mode='MarkdownV2')

async def cmd_web(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /web - Enlace al panel web
    Alias: /panel, /webapp
    """
    import os
    
    try:
        # Obtener configuración del host/puerto web
        host = os.getenv('WEB_HOST', 'localhost')
        port = os.getenv('WEB_PORT', '8080')
        
        # Generar enlace con token de sesión temporal
        import uuid
        session_token = str(uuid.uuid4())[:8]
        
        web_url = f"http://{host}:{port}/dashboard?token={session_token}"
        
        text = f"""🌐 *PANEL WEB AVANZADO*

**🚀 Acceso Directo:**
[Abrir Panel Web]({web_url})

**💡 CARACTERÍSTICAS WEB:**
• ⚙️ Configuración detallada
• 📊 Dashboard avanzado  
• 📈 Backtesting completo
• 🧠 ML Training & Optimization
• 📋 Histórico detallado
• 🎯 Análisis técnico profundo

**🔒 SEGURIDAD:**
• Token temporal: `{session_token}`
• Sesión válida por 1 hora
• Acceso desde IP autorizada

**📱 USO HÍBRIDO:**
• Telegram: Monitoreo básico
• Web: Configuración avanzada

*Tip: Guarda el enlace en favoritos*"""

        await update.message.reply_text(
            text, 
            parse_mode='MarkdownV2',
            disable_web_page_preview=False
        )
        
    except Exception as e:
        fallback_text = """🌐 *PANEL WEB*

⚠️ **Panel en desarrollo**

El sistema web está siendo implementado\\. 
Mientras tanto, usa comandos de Telegram:

• `/dashboard` \\- Estado actual
• `/config` \\- Configuración básica
• `/help` \\- Ayuda completa

🚧 *Próximamente: Panel web completo*"""
        
        await update.message.reply_text(fallback_text, parse_mode='MarkdownV2')

async def cmd_quick_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando: /quick - Resumen ultra-rápido
    Alias: /q, /resumen
    """
    try:
        status = await logic_stubs.get_consolidated_status()
        
        running = "🟢 ON" if status.get('running', False) else "🔴 OFF"
        mode = status.get('mode', 'N/A')
        daily_pnl = status.get('daily_pnl_percent', 0.0)
        positions = len(status.get('positions', []))
        
        pnl_icon = "🟢" if daily_pnl >= 0 else "🔴"
        
        text = f"""⚡ *QUICK STATUS*

{running} • `{mode}` • {pnl_icon} `{daily_pnl:+.2f}%` • 📊 `{positions}pos`

💡 `/d` \\- Dashboard \\| `/web` \\- Panel"""
        
        await update.message.reply_text(text, parse_mode='MarkdownV2')
        
    except Exception as e:
        await update.message.reply_text(f"⚡ Error: `{str(e)}`", parse_mode='MarkdownV2')

# Diccionario de comandos para registro
QUICK_COMMANDS = {
    # Principales
    "dashboard": cmd_dashboard,
    "d": cmd_dashboard,  # Alias corto
    "status": cmd_dashboard,
    "estado": cmd_dashboard,
    
    # Pares dinámicos  
    "pares": cmd_pares,
    "p": cmd_pares,  # Alias corto
    "pairs": cmd_pares,
    "dinamico": cmd_pares,
    
    # Re-evaluación
    "reevaluar": cmd_reevaluar,
    "reeval": cmd_reevaluar,
    "actualizar": cmd_reevaluar,
    "update": cmd_reevaluar,
    
    # Información
    "posiciones": cmd_posiciones,
    "pos": cmd_posiciones,
    "positions": cmd_posiciones,
    
    "pnl": cmd_pnl,
    "rendimiento": cmd_pnl,
    "performance": cmd_pnl,
    
    # Quick access
    "quick": cmd_quick_summary,
    "q": cmd_quick_summary,
    "resumen": cmd_quick_summary,
    
    # Sistema
    "salud": cmd_salud,
    "health": cmd_salud,
    "sistema": cmd_salud,
    
    # Panel Web
    "web": cmd_web,
    "panel": cmd_web,
    "webapp": cmd_web,
    
    # Configuración y ayuda
    "config": cmd_config,
    "configurar": cmd_config,
    "settings": cmd_config,
    
    "help": cmd_help,
    "ayuda": cmd_help,
    
    "about": cmd_about,
    "info": cmd_about,
}
