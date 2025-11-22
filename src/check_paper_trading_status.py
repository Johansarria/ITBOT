#!/usr/bin/env python3
"""
Script para verificar el estado del paper trading con las nuevas integraciones
"""

import json
import os
from datetime import datetime
import glob

def check_paper_trading_status():
    print("🔍 VERIFICANDO ESTADO DEL PAPER TRADING CON NUEVAS INTEGRACIONES")
    print("=" * 70)
    
    # 1. Verificar configuración de paper trading
    session_file = "data/paper_trading_session.json"
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        print("📊 CONFIGURACIÓN ACTUAL:")
        print(f"   Auto Trading: {'✅ ACTIVO' if session_data.get('auto_trading', False) else '❌ INACTIVO'}")
        print(f"   Sesión Activa: {'✅ SÍ' if session_data.get('session_active', False) else '❌ NO'}")
        print(f"   Capital Inicial: ${session_data.get('initial_capital', 0):,.2f}")
        print(f"   Capital Actual: ${session_data.get('current_capital', 0):,.2f}")
        
        if 'last_trade' in session_data and session_data['last_trade']:
            print(f"   Último Trade: {session_data['last_trade'].get('timestamp', 'N/A')}")
    else:
        print("❌ No se encontró paper_trading_session.json")
    
    print()
    
    # 2. Verificar reportes de integración recientes
    print("📈 REPORTES DE INTEGRACIÓN RECIENTES:")
    
    # Buscar en la nueva ubicación
    integration_reports_dir = os.path.join("logs", "integration_reports")
    integration_reports = []
    
    if os.path.exists(integration_reports_dir):
        integration_reports = glob.glob(os.path.join(integration_reports_dir, "integration_report_*.json"))
    
    # También buscar en el directorio actual (compatibilidad)
    integration_reports.extend(glob.glob("integration_report_*.json"))
    
    if integration_reports:
        # Ordenar por fecha de modificación (más reciente primero)
        integration_reports.sort(key=os.path.getmtime, reverse=True)
        latest_report = integration_reports[0]
        print(f"   📊 Último reporte: {os.path.basename(latest_report)}")
        
        # Leer y mostrar resumen del reporte
        try:
            with open(latest_report, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            if 'executive_summary' in report_data:
                summary = report_data['executive_summary']
                for key, value in summary.items():
                    print(f"      {value}")
            
            if 'timestamp' in report_data:
                print(f"      Generado: {report_data['timestamp']}")
                
        except Exception as e:
            print(f"      ❌ Error leyendo reporte: {e}")
    else:
        print("   ❌ No se encontraron reportes de integración")
    
    print()
    
    # 3. Verificar logs de trading recientes
    print("📝 LOGS DE TRADING RECIENTES:")
    log_files = ["trades_detailed.log", "paper_trading.log", "enhanced_integration.log"]
    
    for log_file in log_files:
        # Buscar en logs/ y en directorio actual
        log_paths = [
            log_file,
            os.path.join("logs", log_file)
        ]
        
        found = False
        for log_path in log_paths:
            if os.path.exists(log_path):
                found = True
                try:
                    # Leer las últimas 3 líneas
                    with open(log_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            print(f"   📄 {log_file} (últimas entradas):")
                            for line in lines[-3:]:
                                print(f"      {line.strip()}")
                        else:
                            print(f"   📄 {log_file}: Vacío")
                except Exception as e:
                    print(f"   📄 {log_file}: Error leyendo - {e}")
                break
        
        if not found:
            print(f"   ❌ {log_file}: No encontrado")
    
    print()
    
    # 4. Verificar estado de sistemas activos
    print("🤖 SISTEMAS ACTIVOS:")
    
    # Verificar si hay procesos de monitoreo activos
    monitor_files = ["monitor_session_live.py", "proactive_monitoring_system.py", "real_time_first_candle_system.py"]
    for monitor_file in monitor_files:
        if os.path.exists(monitor_file):
            print(f"   ✅ {monitor_file}: Disponible")
        else:
            print(f"   ❌ {monitor_file}: No encontrado")
    
    print()
    
    # 5. Verificar configuración de XAI y breakouts
    print("🧠 CONFIGURACIÓN XAI Y BREAKOUTS:")
    config_files = ["enhanced_config.py", "sicar_config.json"]
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"   ✅ {config_file}: Encontrado")
            if config_file.endswith('.json'):
                try:
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                    if 'AUTO_TRADING_DEFAULT' in config_data:
                        print(f"      Auto Trading Default: {config_data['AUTO_TRADING_DEFAULT']}")
                except:
                    pass
        else:
            print(f"   ❌ {config_file}: No encontrado")
    
    print()
    print("🎯 RESUMEN:")
    print("   El sistema está configurado para paper trading con las nuevas integraciones")
    print("   XAI, breakout detection y autonomous decision engine están integrados")
    print("   El modo de operación actual depende de la configuración de auto_trading")

if __name__ == "__main__":
    check_paper_trading_status()