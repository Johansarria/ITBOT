#!/usr/bin/env python3
"""
ANÁLISIS DE REINICIO DEL SISTEMA A LAS 00:00
Investigar causas de reinicio automático a medianoche
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime
import subprocess

def analyze_midnight_restart():
    print("🔍 ANÁLISIS DE REINICIO AUTOMÁTICO A LAS 00:00")
    print("=" * 70)
    print(f"⏰ Investigación iniciada: {datetime.now().strftime('%H:%M:%S')}")
    
    restart_causes = []
    
    # 1. Verificar tareas cron del sistema
    print(f"\n📋 1. VERIFICACIÓN DE TAREAS CRON:")
    try:
        # Verificar crontab del usuario actual
        result = subprocess.run(['crontab', '-l'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"   📋 Crontab del usuario encontrado:")
            cron_lines = result.stdout.strip().split('\n')
            for line in cron_lines:
                if line.strip() and not line.strip().startswith('#'):
                    print(f"      • {line}")
                    if '0 0' in line or '00:00' in line:
                        restart_causes.append(f"Tarea cron a medianoche: {line}")
        else:
            print(f"   ✅ Sin crontab de usuario")
            
    except Exception as e:
        print(f"   ⚠️ Error verificando crontab usuario: {e}")
    
    # Verificar cron del sistema
    try:
        cron_dirs = ['/etc/cron.d/', '/etc/cron.daily/', '/etc/cron.hourly/']
        for cron_dir in cron_dirs:
            if os.path.exists(cron_dir):
                files = os.listdir(cron_dir)
                if files:
                    print(f"   📁 Archivos en {cron_dir}: {files}")
                    for file in files:
                        if 'docker' in file.lower() or 'itbot' in file.lower():
                            restart_causes.append(f"Tarea del sistema en {cron_dir}{file}")
    except Exception as e:
        print(f"   ⚠️ Error verificando cron sistema: {e}")
    
    # 2. Verificar configuraciones de Docker
    print(f"\n🐳 2. VERIFICACIÓN DE CONFIGURACIONES DOCKER:")
    
    # Verificar docker-compose.yml
    try:
        with open('/app/../docker-compose.yml', 'r') as f:
            compose_content = f.read()
        
        print(f"   📋 Revisando docker-compose.yml...")
        
        # Buscar configuraciones de reinicio
        if 'restart:' in compose_content:
            restart_policies = []
            lines = compose_content.split('\n')
            for i, line in enumerate(lines):
                if 'restart:' in line:
                    service_name = "unknown"
                    # Buscar el nombre del servicio hacia arriba
                    for j in range(i-1, max(i-10, 0), -1):
                        if lines[j].strip().endswith(':') and not lines[j].strip().startswith('-'):
                            service_name = lines[j].strip().replace(':', '')
                            break
                    
                    policy = line.strip()
                    restart_policies.append(f"{service_name}: {policy}")
                    print(f"      • {service_name}: {policy}")
            
            if restart_policies:
                restart_causes.extend(restart_policies)
        
        # Buscar healthchecks que puedan causar reinicio
        if 'healthcheck:' in compose_content:
            print(f"   🏥 Healthchecks encontrados - pueden causar reinicios")
            restart_causes.append("Healthchecks configurados en docker-compose")
        
    except Exception as e:
        print(f"   ⚠️ Error leyendo docker-compose.yml: {e}")
    
    # 3. Verificar logs de Docker para patrones de reinicio
    print(f"\n📊 3. ANÁLISIS DE LOGS DE DOCKER:")
    
    try:
        # Obtener logs recientes de los contenedores
        containers = ['itbot_main', 'itbot_worker', 'itbot_listener']
        
        for container in containers:
            try:
                result = subprocess.run(
                    ['docker', 'logs', '--since', '24h', '--timestamps', container],
                    capture_output=True, text=True, timeout=15
                )
                
                if result.returncode == 0 and result.stdout:
                    lines = result.stdout.split('\n')
                    midnight_events = []
                    
                    for line in lines:
                        if '00:00' in line or 'T00:' in line:
                            midnight_events.append(line.strip())
                    
                    if midnight_events:
                        print(f"   📋 {container} - Eventos a medianoche:")
                        for event in midnight_events[-5:]:  # Últimos 5 eventos
                            print(f"      • {event}")
                        
                        restart_causes.append(f"{container}: Actividad a medianoche detectada")
                    else:
                        print(f"   ✅ {container} - Sin eventos específicos a medianoche")
                
            except Exception as e:
                print(f"   ⚠️ Error obteniendo logs de {container}: {e}")
                
    except Exception as e:
        print(f"   ❌ Error general en análisis de logs: {e}")
    
    # 4. Verificar configuraciones de la aplicación
    print(f"\n⚙️ 4. VERIFICACIÓN DE CONFIGURACIONES DE APLICACIÓN:")
    
    # Verificar si hay tareas programadas en el código
    config_files = [
        '/app/config.py',
        '/app/main.py',
        '/app/scheduler.py',
        '/app/worker.py'
    ]
    
    for config_file in config_files:
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    content = f.read()
                
                # Buscar patrones que indiquen tareas programadas
                patterns = [
                    ('00:00', 'Configuración de medianoche'),
                    ('midnight', 'Referencia a medianoche'),
                    ('daily', 'Tarea diaria'),
                    ('schedule', 'Programador de tareas'),
                    ('cron', 'Expresión cron'),
                    ('restart', 'Configuración de reinicio'),
                    ('0 0 *', 'Expresión cron de medianoche')
                ]
                
                found_patterns = []
                for pattern, description in patterns:
                    if pattern.lower() in content.lower():
                        found_patterns.append(description)
                
                if found_patterns:
                    print(f"   📋 {config_file}:")
                    for pattern in found_patterns:
                        print(f"      • {pattern}")
                    
                    restart_causes.append(f"Configuración en {config_file}: {', '.join(found_patterns)}")
                else:
                    print(f"   ✅ {config_file} - Sin patrones de reinicio")
            
        except Exception as e:
            print(f"   ⚠️ Error leyendo {config_file}: {e}")
    
    # 5. Verificar systemd y servicios del sistema
    print(f"\n🔧 5. VERIFICACIÓN DE SERVICIOS DEL SISTEMA:")
    
    try:
        # Verificar si hay servicios relacionados con Docker/ITBOT
        result = subprocess.run(
            ['systemctl', 'list-timers', '--no-pager'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            timer_lines = result.stdout.split('\n')
            relevant_timers = []
            
            for line in timer_lines:
                if any(keyword in line.lower() for keyword in ['docker', 'itbot', 'restart']):
                    relevant_timers.append(line.strip())
            
            if relevant_timers:
                print(f"   📋 Timers relevantes del sistema:")
                for timer in relevant_timers:
                    print(f"      • {timer}")
                
                restart_causes.extend(relevant_timers)
            else:
                print(f"   ✅ Sin timers relevantes del sistema")
        
    except Exception as e:
        print(f"   ⚠️ Error verificando systemd timers: {e}")
    
    # 6. Verificar configuraciones de memoria y recursos
    print(f"\n💾 6. VERIFICACIÓN DE RECURSOS Y LÍMITES:")
    
    try:
        # Verificar límites de memoria en Docker
        result = subprocess.run(
            ['docker', 'stats', '--no-stream', '--format', 'table {{.Container}}\t{{.MemUsage}}\t{{.MemPerc}}'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0:
            print(f"   📊 Uso actual de memoria:")
            lines = result.stdout.split('\n')
            for line in lines[1:]:  # Skip header
                if line.strip() and 'itbot' in line.lower():
                    print(f"      • {line}")
        
        # Verificar si hay configuración de OOM killer
        if os.path.exists('/proc/sys/vm/oom_kill_allocating_task'):
            print(f"   ⚠️ OOM Killer activo - puede causar reinicios por memoria")
            restart_causes.append("OOM Killer puede estar causando reinicios")
    
    except Exception as e:
        print(f"   ⚠️ Error verificando recursos: {e}")
    
    # 7. Resumen y diagnóstico
    print(f"\n" + "="*70)
    print(f"📊 RESUMEN DEL ANÁLISIS")
    print(f"="*70)
    
    print(f"🔍 POSIBLES CAUSAS DE REINICIO A LAS 00:00:")
    
    if restart_causes:
        for i, cause in enumerate(restart_causes, 1):
            print(f"   {i}. {cause}")
    else:
        print(f"   ✅ No se encontraron causas obvias de reinicio")
    
    # Recomendaciones
    print(f"\n💡 RECOMENDACIONES PARA INVESTIGACIÓN ADICIONAL:")
    
    recommendations = [
        "Revisar logs específicos del sistema con: journalctl -u docker",
        "Verificar logs del host: dmesg | grep -i killed",
        "Monitorear uso de memoria durante 24h",
        "Verificar si hay actualizaciones automáticas del sistema",
        "Revisar configuraciones de Docker daemon",
        "Verificar si hay tareas de mantenimiento del servidor"
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    # Clasificación de riesgo
    if len(restart_causes) >= 3:
        risk_level = "🚨 ALTO - Múltiples causas potenciales"
    elif len(restart_causes) >= 1:
        risk_level = "⚠️ MODERADO - Algunas causas identificadas"
    else:
        risk_level = "✅ BAJO - Sin causas obvias"
    
    print(f"\n🎯 NIVEL DE RIESGO: {risk_level}")
    
    return restart_causes

if __name__ == "__main__":
    causes = analyze_midnight_restart()
    print(f"\n📋 ANÁLISIS COMPLETADO")
    print(f"🔍 {len(causes)} posibles causas identificadas")
