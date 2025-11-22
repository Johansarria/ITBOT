# /src/manage_sessions.py
"""
Utilidad de Gestión de Sesiones SICAR
Script para gestionar nombres de sesiones y sistemas en ejecución
"""

import sys
import os
from session_manager import get_session_manager
from datetime import datetime

def print_header():
    """Imprime el encabezado del sistema"""
    print("🎯" + "=" * 60)
    print("    SICAR - GESTOR DE SESIONES DE SISTEMAS")
    print("    Asegurando nombres en memoria para sistemas activos")
    print("=" * 62)
    print()

def show_current_status():
    """Muestra el estado actual de las sesiones"""
    sm = get_session_manager()
    
    print("📊 ESTADO ACTUAL DE SESIONES:")
    print("-" * 40)
    
    sessions = sm.list_sessions()
    if not sessions:
        print("   ℹ️ No hay sesiones activas en memoria")
        return
    
    for session in sessions:
        status_icon = "🟢" if session['status'] == 'active' else "🔴"
        print(f"   {status_icon} {session['name']}")
        print(f"      📅 Creada: {session['created_at'][:19]}")
        print(f"      🔧 Sistemas: {len(session['systems'])}")
        print(f"      📝 {session['description']}")
        print()

def create_new_session():
    """Crea una nueva sesión interactivamente"""
    sm = get_session_manager()
    
    print("🆕 CREAR NUEVA SESIÓN:")
    print("-" * 25)
    
    name = input("   📝 Nombre de la sesión (Enter para auto-generar): ").strip()
    description = input("   📄 Descripción (opcional): ").strip()
    
    if not name:
        name = None  # Se auto-generará
    
    session_id = sm.create_session(name=name, description=description)
    
    print(f"\n   ✅ Sesión creada exitosamente!")
    print(f"   🆔 ID: {session_id}")
    print(f"   📛 Nombre: {sm.sessions[session_id]['name']}")
    
    return session_id

def auto_detect_and_create():
    """Detecta sistemas automáticamente y crea una sesión"""
    sm = get_session_manager()
    
    print("🔍 DETECCIÓN AUTOMÁTICA DE SISTEMAS:")
    print("-" * 35)
    
    running_systems = sm.detect_running_systems()
    
    if not running_systems:
        print("   ℹ️ No se detectaron sistemas SICAR en ejecución")
        return None
    
    print(f"   🔍 Sistemas detectados: {len(running_systems)}")
    for system in running_systems:
        print(f"      • {system['script']} (PID: {system['pid']})")
    
    confirm = input("\n   ❓ ¿Crear sesión para estos sistemas? (s/N): ").strip().lower()
    
    if confirm in ['s', 'si', 'sí', 'y', 'yes']:
        session_id = sm.auto_create_session_for_current_systems()
        print(f"\n   ✅ Sesión automática creada: {sm.sessions[session_id]['name']}")
        return session_id
    else:
        print("   ❌ Operación cancelada")
        return None

def show_session_details():
    """Muestra detalles de una sesión específica"""
    sm = get_session_manager()
    
    sessions = sm.list_sessions()
    if not sessions:
        print("   ℹ️ No hay sesiones disponibles")
        return
    
    print("📋 SESIONES DISPONIBLES:")
    for i, session in enumerate(sessions, 1):
        print(f"   {i}. {session['name']} ({session['status']})")
    
    try:
        choice = int(input("\n   🔢 Selecciona una sesión (número): ")) - 1
        if 0 <= choice < len(sessions):
            session = sessions[choice]
            print(f"\n{sm.get_session_summary(session['id'])}")
        else:
            print("   ❌ Selección inválida")
    except ValueError:
        print("   ❌ Por favor ingresa un número válido")

def ensure_current_session():
    """Asegura que existe una sesión para los sistemas actuales"""
    sm = get_session_manager()
    
    print("🔒 ASEGURAR SESIÓN ACTUAL:")
    print("-" * 25)
    
    # Verificar si ya existe una sesión activa
    current_session = sm.get_current_session()
    
    if current_session:
        print(f"   ✅ Sesión activa encontrada: {current_session['name']}")
        print(f"   🔧 Sistemas: {len(current_session['systems'])}")
        
        # Verificar si hay nuevos sistemas que añadir
        running_systems = sm.detect_running_systems()
        existing_pids = {sys.get('pid') for sys in current_session['systems']}
        new_systems = [sys for sys in running_systems if sys['pid'] not in existing_pids]
        
        if new_systems:
            print(f"   🆕 Nuevos sistemas detectados: {len(new_systems)}")
            for system in new_systems:
                sm.add_system_to_session(current_session['id'], system)
                print(f"      ➕ Añadido: {system['script']}")
        else:
            print("   ℹ️ No hay nuevos sistemas para añadir")
    else:
        print("   ⚠️ No hay sesión activa")
        print("   🔄 Creando sesión automática...")
        session_id = sm.auto_create_session_for_current_systems()
        if session_id:
            print(f"   ✅ Sesión creada: {sm.sessions[session_id]['name']}")
        else:
            print("   ℹ️ No se detectaron sistemas para crear sesión")

def main_menu():
    """Menú principal interactivo"""
    while True:
        print_header()
        show_current_status()
        
        print("🎛️ OPCIONES DISPONIBLES:")
        print("   1. 🔒 Asegurar sesión para sistemas actuales")
        print("   2. 🆕 Crear nueva sesión")
        print("   3. 🔍 Detectar y crear sesión automática")
        print("   4. 📋 Ver detalles de sesión")
        print("   5. 📊 Actualizar estado")
        print("   0. 🚪 Salir")
        print()
        
        choice = input("   🔢 Selecciona una opción: ").strip()
        
        if choice == "1":
            ensure_current_session()
        elif choice == "2":
            create_new_session()
        elif choice == "3":
            auto_detect_and_create()
        elif choice == "4":
            show_session_details()
        elif choice == "5":
            continue  # Refresca la pantalla
        elif choice == "0":
            print("\n   👋 ¡Hasta luego!")
            break
        else:
            print("\n   ❌ Opción inválida")
        
        input("\n   ⏸️ Presiona Enter para continuar...")
        print("\n" * 2)

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            # Modo comando directo
            command = sys.argv[1].lower()
            sm = get_session_manager()
            
            if command == "ensure":
                ensure_current_session()
            elif command == "auto":
                auto_detect_and_create()
            elif command == "status":
                show_current_status()
            elif command == "create":
                create_new_session()
            else:
                print(f"❌ Comando desconocido: {command}")
                print("📖 Comandos disponibles: ensure, auto, status, create")
        else:
            # Modo interactivo
            main_menu()
    
    except KeyboardInterrupt:
        print("\n\n   🛑 Operación interrumpida por el usuario")
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        print("   🔧 Contacta al administrador del sistema")