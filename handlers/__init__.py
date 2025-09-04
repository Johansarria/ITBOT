# handlers/__init__.py - Re-exportar funciones desde handlers.py

import sys
import os
import importlib.util

# Importar desde el archivo handlers.py en el directorio raíz
try:
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    handlers_py_path = os.path.join(parent_dir, 'handlers.py')
    
    # Cargar el módulo handlers.py
    spec = importlib.util.spec_from_file_location("handlers_root", handlers_py_path)
    if spec and spec.loader:
        handlers_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handlers_module)
    else:
        raise ImportError(f"No se pudo cargar el spec para {handlers_py_path}")
    
    # Re-exportar las funciones principales
    start = handlers_module.start
    main_menu_handlers = handlers_module.main_menu_handlers
    action_handlers = handlers_module.action_handlers
    conv_handlers = handlers_module.conv_handlers
    get_my_id = handlers_module.get_my_id
    
    # Exportar también otras funciones importantes
    show_control_operativo = handlers_module.show_control_operativo
    show_gestion_riesgo = handlers_module.show_gestion_riesgo
    show_reportes_analisis = handlers_module.show_reportes_analisis
    show_mlops_menu = handlers_module.show_mlops_menu
    show_system_menu = handlers_module.show_system_menu
    show_emergency_menu = handlers_module.show_emergency_menu
    show_panel_control = handlers_module.show_panel_control
    
except Exception as e:
    print(f"Error importando handlers.py: {e}")
    import traceback
    traceback.print_exc()
    # Definir placeholders vacíos para evitar errores
    start = None
    main_menu_handlers = []
    action_handlers = []
    conv_handlers = []
    get_my_id = None