# keyboards.py

"""
Módulo de definición de teclados (UI).

Contiene funciones que generan y devuelven objetos InlineKeyboardMarkup
para ser usados en los handlers de Telegram. Esto centraliza y separa
la definición de la interfaz de usuario de la lógica de la aplicación.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado del menú principal."""
    keyboard = [
        [InlineKeyboardButton("📊 Panel de Control", callback_data="panel_control")],
        [InlineKeyboardButton("⚙️ Control Operativo", callback_data="control_operativo")],
        [InlineKeyboardButton("⚖️ Gestión de Riesgo", callback_data="gestion_riesgo")],
        [InlineKeyboardButton("📈 Reportes y Análisis", callback_data="reportes_analisis")],
        [InlineKeyboardButton("🧠 Inteligencia y MLOps", callback_data="inteligencia_mlops")],
        [InlineKeyboardButton("🛠️ Sistema y Mantenimiento", callback_data="sistema_mantenimiento")],
        [InlineKeyboardButton("🚨 EMERGENCIA 🚨", callback_data="emergencia")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_panel_control_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para el Panel de Control."""
    keyboard = [
        [InlineKeyboardButton("👁️ Ver Panel General", callback_data="dashboard_show")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_control_operativo_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para el Control Operativo."""
    keyboard = [
        [InlineKeyboardButton("🔄 Cambiar Modo (LIVE/PAPER)", callback_data="control_change_mode")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_control_operativo_live_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para el Control Operativo cuando el modo es LIVE."""
    keyboard = [
        [InlineKeyboardButton("✅ Cambiar a Modo PAPER", callback_data="control_set_paper")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_gestion_riesgo_keyboard() -> InlineKeyboardMarkup:
    """Genera el teclado para la Gestión de Riesgo."""
    keyboard = [
        [InlineKeyboardButton("📏 Definir Tamaño de Orden", callback_data="risk_define_size")],
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
    """Genera el teclado para el menú de Emergencia."""
    keyboard = [
        [InlineKeyboardButton("🔥 LIQUIDAR TODO 🔥", callback_data="emergency_liquidate")],
        [InlineKeyboardButton("🛑 PAUSA TOTAL 🛑", callback_data="emergency_full_stop")],
        [InlineKeyboardButton("↩️ Volver al Menú Principal", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Genera un teclado con solo un botón de cancelar."""
    keyboard = [
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    return InlineKeyboardMarkup(keyboard)
