#!/usr/bin/env python3
"""
Script para analizar el estado actual del bot SICAR sin interrumpir la simulación.
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def analyze_bot_status():
    """Analiza el estado actual del bot SICAR"""
    
    print("🔍 === ANÁLISIS DEL ESTADO DEL BOT SICAR ===")
    print(f"⏰ Análisis realizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Verificar archivos de configuración
    config_status = check_configuration()
    
    # 2. Analizar logs de trading
    trading_status = analyze_trading_logs()
    
    # 3. Revisar reportes recientes
    reports_status = analyze_recent_reports()
    
    # 4. Verificar datos de mercado
    market_data_status = check_market_data()
    
    # 5. Resumen general
    print_summary(config_status, trading_status, reports_status, market_data_status)

def check_configuration():
    """Verifica la configuración del bot"""
    print("\n📋 === CONFIGURACIÓN DEL BOT ===")
    
    try:
        # Importar configuración
        import sys
        sys.path.append('.')
        from config import Config
        
        config = Config()
        
        print(f"💰 Capital inicial: ${config.INITIAL_CAPITAL}")
        print(f"📊 Símbolo: {config.SYMBOL}")
        print(f"⏱️ Timeframe: {config.TIMEFRAME}")
        print(f"⚡ Riesgo por trade: {config.RISK_PER_TRADE * 100}%")
        print(f"🎯 Confianza mínima: {config.MIN_CONFIDENCE * 100}%")
        print(f"📝 Modo: {'PAPER TRADING' if config.PAPER_TRADING else 'TRADING REAL'}")
        
        return {
            'status': 'OK',
            'capital': config.INITIAL_CAPITAL,
            'symbol': config.SYMBOL,
            'timeframe': config.TIMEFRAME,
            'paper_trading': config.PAPER_TRADING
        }
        
    except Exception as e:
        print(f"❌ Error cargando configuración: {e}")
        return {'status': 'ERROR', 'error': str(e)}

def analyze_trading_logs():
    """Analiza los logs de trading"""
    print("\n📈 === ANÁLISIS DE TRADING ===")
    
    try:
        # Verificar archivo de trades JSONL
        trades_file = Path("../logs/trades_data.jsonl")
        
        if not trades_file.exists():
            print("📝 No hay archivo de trades aún (normal en inicio)")
            return {'status': 'NO_TRADES', 'trades_count': 0}
        
        # Leer trades
        trades = []
        with open(trades_file, 'r') as f:
            for line in f:
                if line.strip():
                    trades.append(json.loads(line))
        
        if not trades:
            print("📝 No hay trades registrados aún")
            return {'status': 'NO_TRADES', 'trades_count': 0}
        
        # Analizar trades
        total_trades = len(trades)
        profitable_trades = sum(1 for t in trades if t.get('pnl', 0) > 0)
        total_pnl = sum(t.get('pnl', 0) for t in trades)
        
        print(f"📊 Total de trades: {total_trades}")
        print(f"✅ Trades rentables: {profitable_trades}")
        print(f"📈 Win rate: {(profitable_trades/total_trades)*100:.1f}%")
        print(f"💰 PnL total: ${total_pnl:.2f}")
        
        return {
            'status': 'OK',
            'trades_count': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': (profitable_trades/total_trades)*100,
            'total_pnl': total_pnl
        }
        
    except Exception as e:
        print(f"❌ Error analizando logs: {e}")
        return {'status': 'ERROR', 'error': str(e)}

def analyze_recent_reports():
    """Analiza los reportes recientes"""
    print("\n📋 === REPORTES RECIENTES ===")
    
    try:
        reports_dir = Path("../reports")
        
        if not reports_dir.exists():
            print("📝 No hay directorio de reportes")
            return {'status': 'NO_REPORTS'}
        
        # Buscar reportes recientes
        report_files = list(reports_dir.glob("reporte_dinamico_*.txt"))
        
        if not report_files:
            print("📝 No hay reportes dinámicos generados")
            return {'status': 'NO_REPORTS'}
        
        # Ordenar por fecha (más reciente primero)
        report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Analizar el reporte más reciente
        latest_report = report_files[0]
        
        with open(latest_report, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraer información clave
        lines = content.split('\n')
        decision = None
        strategy = None
        confidence = None
        
        for line in lines:
            if 'Decisión:' in line:
                decision = line.split('Decisión:')[1].strip()
            elif 'Estrategia:' in line:
                strategy = line.split('Estrategia:')[1].strip()
            elif 'Confianza:' in line:
                confidence = line.split('Confianza:')[1].strip()
        
        print(f"📄 Último reporte: {latest_report.name}")
        print(f"🎯 Decisión: {decision or 'No detectada'}")
        print(f"📊 Estrategia: {strategy or 'No detectada'}")
        print(f"🔥 Confianza: {confidence or 'No detectada'}")
        print(f"📅 Total de reportes: {len(report_files)}")
        
        return {
            'status': 'OK',
            'latest_report': latest_report.name,
            'decision': decision,
            'strategy': strategy,
            'confidence': confidence,
            'total_reports': len(report_files)
        }
        
    except Exception as e:
        print(f"❌ Error analizando reportes: {e}")
        return {'status': 'ERROR', 'error': str(e)}

def check_market_data():
    """Verifica el estado de los datos de mercado"""
    print("\n📊 === DATOS DE MERCADO ===")
    
    try:
        # Verificar cache de datos
        cache_dir = Path("../data/cache")
        
        if cache_dir.exists():
            cache_files = list(cache_dir.glob("*.csv"))
            print(f"💾 Archivos en cache: {len(cache_files)}")
            
            if cache_files:
                # Verificar el archivo más reciente
                latest_cache = max(cache_files, key=lambda x: x.stat().st_mtime)
                mod_time = datetime.fromtimestamp(latest_cache.stat().st_mtime)
                age = datetime.now() - mod_time
                
                print(f"📁 Último cache: {latest_cache.name}")
                print(f"⏰ Actualizado hace: {age}")
                
                # Verificar si el cache es reciente (menos de 1 hora)
                if age < timedelta(hours=1):
                    print("✅ Datos de mercado actualizados")
                    status = 'FRESH'
                else:
                    print("⚠️ Datos de mercado algo antiguos")
                    status = 'STALE'
            else:
                print("📝 No hay archivos de cache")
                status = 'NO_CACHE'
        else:
            print("📝 No hay directorio de cache")
            status = 'NO_CACHE'
        
        # Verificar datos procesados
        processed_dir = Path("../data/processed")
        if processed_dir.exists():
            processed_files = list(processed_dir.glob("*.csv"))
            print(f"🔄 Archivos procesados: {len(processed_files)}")
        
        return {'status': status, 'cache_files': len(cache_files) if 'cache_files' in locals() else 0}
        
    except Exception as e:
        print(f"❌ Error verificando datos: {e}")
        return {'status': 'ERROR', 'error': str(e)}

def print_summary(config_status, trading_status, reports_status, market_data_status):
    """Imprime un resumen del análisis"""
    print("\n" + "=" * 60)
    print("🎯 === RESUMEN DEL ANÁLISIS ===")
    print("=" * 60)
    
    # Estado general
    overall_status = "🟢 FUNCIONANDO"
    issues = []
    
    if config_status['status'] != 'OK':
        overall_status = "🔴 PROBLEMAS"
        issues.append("Configuración con errores")
    
    if trading_status['status'] == 'ERROR':
        overall_status = "🔴 PROBLEMAS"
        issues.append("Errores en logs de trading")
    
    if market_data_status['status'] == 'ERROR':
        overall_status = "🔴 PROBLEMAS"
        issues.append("Errores en datos de mercado")
    
    print(f"🚦 Estado general: {overall_status}")
    
    if issues:
        print("⚠️ Problemas detectados:")
        for issue in issues:
            print(f"   • {issue}")
    
    # Estadísticas clave
    print("\n📊 Estadísticas clave:")
    
    if config_status['status'] == 'OK':
        print(f"   💰 Capital: ${config_status['capital']}")
        print(f"   📊 Símbolo: {config_status['symbol']}")
        print(f"   📝 Modo: {'Simulación' if config_status['paper_trading'] else 'Real'}")
    
    if trading_status['status'] == 'OK':
        print(f"   📈 Trades: {trading_status['trades_count']}")
        print(f"   ✅ Win rate: {trading_status['win_rate']:.1f}%")
        print(f"   💰 PnL: ${trading_status['total_pnl']:.2f}")
    elif trading_status['status'] == 'NO_TRADES':
        print("   📝 Sin trades aún (esperando señales)")
    
    if reports_status['status'] == 'OK':
        print(f"   📋 Reportes: {reports_status['total_reports']}")
        print(f"   🎯 Última decisión: {reports_status['decision']}")
    
    print(f"   💾 Cache: {market_data_status.get('cache_files', 0)} archivos")
    
    # Recomendaciones
    print("\n💡 Recomendaciones:")
    
    if trading_status['status'] == 'NO_TRADES':
        print("   • El bot está esperando señales de trading - esto es normal")
        print("   • Los análisis se realizan cada 4 horas según el timeframe")
    
    if market_data_status['status'] == 'STALE':
        print("   • Los datos de mercado podrían necesitar actualización")
    
    if reports_status['status'] == 'OK' and reports_status['decision'] == 'HOLD':
        print("   • El bot está en modo HOLD - esperando mejores oportunidades")
    
    print("\n✅ Análisis completado. El bot continúa funcionando.")

if __name__ == "__main__":
    analyze_bot_status()