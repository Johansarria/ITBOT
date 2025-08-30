# keyboards.py

"""
Módulo de definición de teclados (UI).

Contiene funciones que generan y devuelven objetos InlineKeyboardMarkup
para ser usados en los handlers de Telegram. Esto centraliza y separa
la definición de la interfaz de usuario de la lógica de la aplicación.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal (interfaz mínima)."""
    keyboard = [
        [InlineKeyboardButton("🚨 EMERGENCIA", callback_data="emergencia")],
        [InlineKeyboardButton("🌐 Panel Web", callback_data="web_panel_access")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_panel_control_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para el Panel de Control."""
    keyboard = [
        [InlineKeyboardButton("📈 Ver Posiciones Abiertas", callback_data="panel_show_positions")],
        [InlineKeyboardButton("🛡️ Estado de Escudos", callback_data="panel_show_shields")],
        [InlineKeyboardButton("⚙️ Salud del Sistema", callback_data="system_health_check")],
        [InlineKeyboardButton("🧠 Régimen de Mercado", callback_data="mlops_show_regime")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_control_operativo_keyboard(current_mode: str) -> InlineKeyboardMarkup:
    """
    Genera el teclado para el Control Operativo de forma dinámica.
    El texto y la acción del botón cambian según el modo actual.
    """
    if current_mode == 'LIVE':
        button_text = "✅ Cambiar a Modo PAPER"
    else:
        button_text = "🔥 Cambiar a Modo LIVE"

    keyboard = [
        [InlineKeyboardButton(button_text, callback_data="control_toggle_mode")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_gestion_riesgo_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para la Gestión de Riesgo."""
    keyboard = [
        [InlineKeyboardButton("📄 Ver Configuración de Riesgo", callback_data="risk_show_config")],
        [InlineKeyboardButton("📏 Definir Tamaño de Orden", callback_data="risk_define_size")],
        [InlineKeyboardButton("♻️ Volver a Valores por Defecto", callback_data="risk_reset_custom")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_risk_size_menu_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para el submenú de Definir Tamaño de Orden."""
    keyboard = [
        [InlineKeyboardButton("🤖 Modo Automático (ML)", callback_data="risk_set_auto")],
        [InlineKeyboardButton("✍️ Modo Manual (% Fijo)", callback_data="risk_set_manual")],
        [InlineKeyboardButton("↩️ Volver a Gestión de Riesgo", callback_data="gestion_riesgo")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_reportes_analisis_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para Reportes y Análisis."""
    keyboard = [
        [InlineKeyboardButton("🚫 Análisis de Señales Descartadas", callback_data="reports_show_discarded")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_mlops_menu_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para Inteligencia y MLOps."""
    keyboard = [
        [InlineKeyboardButton("📈 Ver Régimen de Mercado", callback_data="mlops_show_regime")],
        [InlineKeyboardButton("🤖 Estado del Modelo ML", callback_data="mlops_model_status")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_system_menu_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para Sistema y Mantenimiento."""
    keyboard = [
        [InlineKeyboardButton("❤️ Verificar Salud de Servicios", callback_data="system_health_check")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_emergency_menu_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para el menú de Emergencia con mejor seguridad."""
    keyboard = [
        [InlineKeyboardButton("⚠️ ¿QUÉ HACER EN EMERGENCIA?", callback_data="emergency_help")],
        [InlineKeyboardButton("🛑 PAUSA TOTAL (Seguro)", callback_data="emergency_pause_all")],
        [InlineKeyboardButton("🚨 KILL SWITCH (Solo Admin)", callback_data="emergency_kill_switch")],
    [InlineKeyboardButton("✅ REANUDAR SISTEMA", callback_data="emergency_resume_system")],
        [InlineKeyboardButton("↩️ Volver al Menú", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quick_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Keyboard para dashboard rápido con acciones inmediatas."""
    keyboard = [
        [
            InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_dashboard"),
            InlineKeyboardButton("📈 Ver Gráficos", callback_data="quick_charts")
        ],
        [
            InlineKeyboardButton("💰 PnL Detallado", callback_data="detailed_pnl"),
            InlineKeyboardButton("⏰ Estadísticas Día", callback_data="daily_stats")
        ],
        [InlineKeyboardButton("↩️ Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quick_positions_keyboard() -> InlineKeyboardMarkup:
    """Keyboard para gestión rápida de posiciones."""
    keyboard = [
        [
            InlineKeyboardButton("👁️ Ver Todas", callback_data="panel_show_positions"),
            InlineKeyboardButton("🔄 Actualizar", callback_data="refresh_positions")
        ],
        [
            InlineKeyboardButton("⚡ Cerrar Perdedoras", callback_data="close_losing_positions"),
            InlineKeyboardButton("🎯 Tomar Ganancias", callback_data="take_profits")
        ],
        [InlineKeyboardButton("🌐 Gestión Web", callback_data="web_positions_mgmt")],
        [InlineKeyboardButton("↩️ Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quick_pairs_keyboard() -> InlineKeyboardMarkup:
    """Keyboard para información rápida de pares dinámicos."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Ver Activos", callback_data="show_active_pairs"),
            InlineKeyboardButton("🔄 Refrescar", callback_data="refresh_pairs")
        ],
        [
            InlineKeyboardButton("⭐ Top Performers", callback_data="top_pairs"),
            InlineKeyboardButton("⚠️ Alertas", callback_data="pair_alerts")
        ],
        [InlineKeyboardButton("🌐 Análisis Web", callback_data="web_pairs_analysis")],
        [InlineKeyboardButton("↩️ Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_verification_keyboard() -> InlineKeyboardMarkup:
    """Keyboard especial para verificación de admin."""
    keyboard = [
        [InlineKeyboardButton("🔐 Soy Administrador", callback_data="verify_admin")],
        [InlineKeyboardButton("❓ ¿Cómo ser Admin?", callback_data="admin_help")],
        [InlineKeyboardButton("↩️ Volver", callback_data="emergencia")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Genera un teclado con solo un botón de cancelar."""
    keyboard = [
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_web_panel_info_keyboard() -> InlineKeyboardMarkup:
    """Keyboard con información del panel web."""
    keyboard = [
        [InlineKeyboardButton("🔑 Generar Token Acceso", callback_data="generate_web_token")],
        [InlineKeyboardButton("📱 Instrucciones Mobile", callback_data="mobile_instructions")],
        [InlineKeyboardButton("💻 Instrucciones Desktop", callback_data="desktop_instructions")],
        [InlineKeyboardButton("↩️ Volver", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)
