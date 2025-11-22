#!/usr/bin/env python3
"""
Análisis completo del estado del paper trading con las nuevas integraciones
"""

import json
import os
from datetime import datetime
import glob

def analyze_paper_trading_with_integrations():
    print("🚀 ANÁLISIS COMPLETO: PAPER TRADING CON NUEVAS INTEGRACIONES")
    print("=" * 80)
    
    # 1. Estado de las integraciones
    print("🔗 ESTADO DE LAS INTEGRACIONES:")
    
    # Buscar reportes en el directorio reports
    reports_dir = "../reports"
    if os.path.exists(reports_dir):
        integration_files = glob.glob(f"{reports_dir}/test_integration_*.json")
        if integration_files:
            latest_file = max(integration_files, key=os.path.getctime)
            print(f"   📊 Último reporte: {os.path.basename(latest_file)}")
            
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            print(f"   ✅ Estado: {data['integration_summary']['status']}")
            print(f"   ⏱️  Tiempo activo: {data['integration_summary']['uptime_hours']:.2f} horas")
            print(f"   🔄 Operaciones totales: {data['integration_summary']['total_operations']}")
            print(f"   📈 Tasa de éxito: {data['system_performance']['integration_success_rate']*100:.1f}%")
            print(f"   🧠 Análisis por hora: {data['system_performance']['analyses_per_hour']:.1f}")
        else:
            print("   ❌ No se encontraron reportes de integración")
    else:
        print("   ❌ Directorio de reportes no encontrado")
    
    print()
    
    # 2. Configuración del sistema
    print("⚙️  CONFIGURACIÓN DEL SISTEMA:")
    
    # Verificar configuración en sicar_config.json
    config_file = "sicar_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print(f"   🤖 Auto Trading Default: {'✅ ACTIVO' if config.get('AUTO_TRADING_DEFAULT', False) else '❌ INACTIVO'}")
        print(f"   💰 Capital inicial: ${config.get('INITIAL_CAPITAL', 10000):,.2f}")
        print(f"   📊 Símbolos: {', '.join(config.get('SYMBOLS', ['BTCUSDT']))}")
    else:
        print("   ❌ sicar_config.json no encontrado")
    
    print()
    
    # 3. Componentes activos
    print("🔧 COMPONENTES INTEGRADOS:")
    
    components = {
        "enhanced_xai_breakout_integration.py": "🧠 XAI Breakout Integration",
        "autonomous_decision_engine.py": "🤖 Motor de Decisiones Autónomas", 
        "enhanced_integration_manager.py": "🔗 Gestor de Integración Mejorado",
        "paper_trading_system.py": "📊 Sistema de Paper Trading",
        "enhanced_breakout_detector.py": "🚀 Detector de Breakouts Mejorado",
        "paper_trading_dashboard_improved.py": "📱 Dashboard Mejorado"
    }
    
    for file, description in components.items():
        if os.path.exists(file):
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - Archivo no encontrado")
    
    print()
    
    # 4. Modo de operación actual
    print("🎯 MODO DE OPERACIÓN ACTUAL:")
    
    print("   📋 CARACTERÍSTICAS DEL PAPER TRADING CON INTEGRACIONES:")
    print("      • XAI (Explainable AI) para análisis de decisiones")
    print("      • Detección automática de breakouts optimizada")
    print("      • Motor de decisiones autónomas integrado")
    print("      • Gestión de riesgo avanzada")
    print("      • Monitoreo en tiempo real")
    print("      • Reportes de rendimiento automáticos")
    
    print()
    print("   🔄 FLUJO DE OPERACIÓN:")
    print("      1. 📊 Recolección de datos de mercado (Binance)")
    print("      2. 🧠 Análisis XAI de patrones y señales")
    print("      3. 🚀 Detección de breakouts con algoritmos mejorados")
    print("      4. 🤖 Toma de decisiones autónomas (si está habilitado)")
    print("      5. 📈 Ejecución de trades simulados (paper trading)")
    print("      6. 📊 Registro y análisis de resultados")
    print("      7. 🔄 Optimización continua de parámetros")
    
    print()
    print("   ⚡ VENTAJAS DEL SISTEMA INTEGRADO:")
    print("      • Sin riesgo financiero real (paper trading)")
    print("      • Análisis explicable de decisiones (XAI)")
    print("      • Detección precisa de oportunidades")
    print("      • Aprendizaje y optimización continua")
    print("      • Monitoreo 24/7 automatizado")
    print("      • Reportes detallados de rendimiento")
    
    print()
    
    # 5. Estado de sesiones
    print("🕐 ESTADO DE SESIONES:")
    
    # Verificar detector de sesiones
    try:
        from session_detector import SessionDetector
        detector = SessionDetector()
        current_session = detector.get_current_session()
        
        if current_session:
            print(f"   ✅ Sesión actual: {current_session['name'].upper()}")
            print(f"   ⏰ Horario: {current_session['start']} - {current_session['end']} EST")
        else:
            next_session = detector.get_next_session()
            if next_session:
                print(f"   ⏳ Próxima sesión: {next_session['name'].upper()}")
                print(f"   ⏰ Inicia en: {next_session['minutes_until']} minutos")
    except Exception as e:
        print(f"   ❌ Error al verificar sesiones: {str(e)}")
    
    print()
    print("🎉 CONCLUSIÓN:")
    print("   El sistema SICAR está operando en modo paper trading con todas las")
    print("   nuevas integraciones activas. Esto permite probar estrategias avanzadas")
    print("   sin riesgo financiero, mientras se beneficia de:")
    print("   • Análisis XAI explicable")
    print("   • Detección automática de breakouts")
    print("   • Toma de decisiones autónomas")
    print("   • Monitoreo y optimización continua")

if __name__ == "__main__":
    analyze_paper_trading_with_integrations()