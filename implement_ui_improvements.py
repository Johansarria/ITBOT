#!/usr/bin/env python3
"""
Script para implementar mejoras de UI en el sistema ITBOT
Actualiza los archivos en el contenedor y reinicia los servicios necesarios
"""

import subprocess
import sys
import time
from pathlib import Path

def run_command(cmd, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        print(f"Error output: {e.stderr}")
        return None

def main():
    print("🚀 IMPLEMENTANDO MEJORAS DE UI PARA ITBOT")
    print("=" * 50)
    
    # Verificar que estamos en el directorio correcto
    if not Path("docker-compose.yml").exists():
        print("❌ Error: No se encuentra docker-compose.yml")
        print("   Por favor ejecuta desde el directorio /home/johan/itbot_linux")
        sys.exit(1)
    
    # 1. Copiar archivos mejorados al contenedor
    files_to_copy = [
        ("handlers/enhanced_dashboard.py", "/app/handlers/"),
        ("handlers/quick_commands.py", "/app/handlers/"),
        ("main.py", "/app/"),
        ("keyboards.py", "/app/")
    ]
    
    print("📁 Copiando archivos mejorados...")
    for local_file, container_path in files_to_copy:
        if Path(local_file).exists():
            cmd = f"docker cp {local_file} itbot_listener:{container_path}"
            result = run_command(cmd, f"Copiando {local_file}")
            if not result:
                continue
        else:
            print(f"⚠️  Archivo no encontrado: {local_file}")
    
    print("\n" + "=" * 50)
    
    # 2. Reiniciar el servicio listener para cargar los cambios
    print("🔄 Reiniciando servicios para cargar mejoras...")
    
    # Reiniciar listener (Telegram bot)
    run_command("docker-compose restart listener", "Reiniciando listener")
    
    # Esperar un poco para que se inicialice
    print("⏳ Esperando inicialización...")
    time.sleep(10)
    
    # 3. Verificar estado de los contenedores
    print("\n📊 Verificando estado de contenedores...")
    run_command("docker ps --filter name=itbot", "Estado de contenedores")
    
    # 4. Mostrar logs recientes del listener
    print("\n📋 Logs recientes del listener:")
    run_command("docker logs --tail=10 itbot_listener", "Logs del listener")
    
    print("\n" + "=" * 50)
    print("🎉 IMPLEMENTACIÓN DE MEJORAS COMPLETADA")
    print("\n📱 NUEVOS COMANDOS DISPONIBLES:")
    print("• /dashboard - Dashboard principal mejorado")
    print("• /pares - Sistema dinámico de pares")
    print("• /reevaluar - Re-evaluar pares dinámicos")
    print("• /posiciones - Ver posiciones abiertas")
    print("• /pnl - Rendimiento actual")
    print("• /salud - Estado de salud del sistema")
    print("• /config - Configuración rápida")
    print("• /help - Lista completa de comandos")
    
    print("\n🚀 CARACTERÍSTICAS NUEVAS:")
    print("• Dashboard con información en tiempo real")
    print("• Integración completa del sistema dinámico")
    print("• Accesos rápidos a funciones principales")
    print("• Comandos alias intuitivos")
    print("• Métricas de rendimiento en tiempo real")
    
    print("\n💡 PRUEBA EL NUEVO SISTEMA:")
    print("Envía /dashboard al bot de Telegram para ver las mejoras!")

if __name__ == "__main__":
    main()
