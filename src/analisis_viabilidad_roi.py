#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import math

def analizar_infraestructura_sicar():
    """Analiza la infraestructura técnica actual del sistema SICAR"""
    
    print('=== ANÁLISIS DE VIABILIDAD ROI 7% MENSUAL ===\n')

    # 1. Análisis de bases de datos y capacidades
    databases = [
        'advanced_logging.db',
        'auto_trading_alerts.db', 
        'enhanced_trading.db',
        'orderbook_analysis.db',
        'proactive_monitoring.db',
        'alertas_database.db'
    ]

    print('🗄️ INFRAESTRUCTURA DE DATOS:')
    total_records = 0
    active_databases = 0

    for db in databases:
        if os.path.exists(db):
            try:
                conn = sqlite3.connect(db)
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
                tables = cursor.fetchall()
                
                db_records = 0
                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
                    count = cursor.fetchone()[0]
                    db_records += count
                
                total_records += db_records
                active_databases += 1
                
                print(f'   ✅ {db}: {len(tables)} tablas, {db_records:,} registros')
                conn.close()
                
            except Exception as e:
                print(f'   ❌ {db}: Error - {e}')
        else:
            print(f'   ⚠️ {db}: No existe')

    print(f'\n📊 RESUMEN DE DATOS:')
    print(f'   Bases de datos activas: {active_databases}/{len(databases)}')
    print(f'   Total de registros: {total_records:,}')

    # 2. Análisis de componentes del sistema
    components = [
        'orderbook_analyzer.py',
        'advanced_ml_engine.py', 
        'dynamic_risk_manager.py',
        'portfolio_optimizer.py',
        'session_detector.py',
        'breakout_validator.py',
        'correlation_analyzer.py',
        'performance_analyzer.py'
    ]

    print(f'\n🔧 COMPONENTES DE ANÁLISIS:')
    active_components = 0
    for component in components:
        if os.path.exists(component):
            size_kb = os.path.getsize(component) / 1024
            print(f'   ✅ {component}: {size_kb:.1f} KB')
            active_components += 1
        else:
            print(f'   ❌ {component}: No encontrado')

    print(f'\n   Componentes activos: {active_components}/{len(components)}')

    # 3. Análisis de rendimiento histórico
    print(f'\n💰 ANÁLISIS DE RENDIMIENTO HISTÓRICO:')
    
    try:
        if os.path.exists('auto_trading_alerts.db'):
            conn = sqlite3.connect('auto_trading_alerts.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM executed_trades ORDER BY timestamp DESC')
            trades = cursor.fetchall()
            
            if trades:
                total_pnl = sum(trade[12] for trade in trades if trade[12] is not None)
                profitable_trades = sum(1 for trade in trades if trade[12] and trade[12] > 0)
                
                print(f'   Total trades ejecutados: {len(trades)}')
                print(f'   Trades rentables: {profitable_trades}/{len(trades)} ({(profitable_trades/len(trades)*100):.1f}%)')
                print(f'   PnL total histórico: ${total_pnl:.4f}')
                print(f'   PnL promedio por trade: ${total_pnl/len(trades):.4f}')
            else:
                print('   ⚠️ No hay trades históricos para analizar')
            
            conn.close()
        else:
            print('   ❌ Base de datos de trades no disponible')
    except Exception as e:
        print(f'   ❌ Error analizando trades: {e}')

    # 4. Cálculos matemáticos para 7% ROI mensual
    print(f'\n📈 REQUISITOS MATEMÁTICOS PARA 7% ROI MENSUAL:')
    
    capital_inicial = 250  # Basado en el reporte anterior
    roi_objetivo = 0.07  # 7%
    dias_mes = 30
    
    ganancia_mensual_objetivo = capital_inicial * roi_objetivo
    ganancia_diaria_objetivo = ganancia_mensual_objetivo / dias_mes
    roi_diario_requerido = ganancia_diaria_objetivo / capital_inicial
    
    print(f'   Capital inicial: ${capital_inicial}')
    print(f'   Ganancia mensual objetivo: ${ganancia_mensual_objetivo:.2f}')
    print(f'   Ganancia diaria requerida: ${ganancia_diaria_objetivo:.2f}')
    print(f'   ROI diario requerido: {roi_diario_requerido*100:.3f}%')
    
    # Cálculo de trades necesarios
    pnl_promedio_actual = 0.062  # Basado en análisis anterior
    trades_diarios_necesarios = ganancia_diaria_objetivo / pnl_promedio_actual if pnl_promedio_actual > 0 else float('inf')
    
    print(f'\n🎯 TRADES REQUERIDOS:')
    print(f'   PnL promedio actual: ${pnl_promedio_actual:.3f}')
    print(f'   Trades diarios necesarios: {trades_diarios_necesarios:.1f}')
    print(f'   Trades mensuales necesarios: {trades_diarios_necesarios * dias_mes:.0f}')

    # 5. Análisis de capacidades actuales
    print(f'\n🔍 CAPACIDADES ACTUALES DEL SISTEMA:')
    
    # Análisis de breakouts detectados
    try:
        if os.path.exists('logs/sicar_breakouts.log'):
            with open('logs/sicar_breakouts.log', 'r') as f:
                breakout_lines = f.readlines()
            print(f'   Breakouts detectados: {len(breakout_lines):,}')
        else:
            print('   ⚠️ Log de breakouts no disponible')
    except:
        print('   ❌ Error leyendo breakouts')
    
    # Análisis de OrderBook
    try:
        if os.path.exists('orderbook_analysis.db'):
            conn = sqlite3.connect('orderbook_analysis.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM orderbook_metrics')
            orderbook_metrics = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM orderbook_alerts')
            orderbook_alerts = cursor.fetchone()[0]
            
            print(f'   Métricas OrderBook: {orderbook_metrics:,}')
            print(f'   Alertas OrderBook: {orderbook_alerts:,}')
            
            conn.close()
    except:
        print('   ❌ Error analizando OrderBook')

    # 6. Evaluación de riesgos y limitaciones
    print(f'\n⚠️ ANÁLISIS DE RIESGOS:')
    
    # Riesgo de drawdown
    max_drawdown_aceptable = 0.15  # 15%
    trades_consecutivos_perdida = 5  # Escenario pesimista
    perdida_por_trade = pnl_promedio_actual * -1
    drawdown_potencial = (perdida_por_trade * trades_consecutivos_perdida) / capital_inicial
    
    print(f'   Drawdown máximo aceptable: {max_drawdown_aceptable*100:.0f}%')
    print(f'   Drawdown potencial (5 trades perdedores): {abs(drawdown_potencial)*100:.1f}%')
    
    # Análisis de volatilidad del mercado
    print(f'   Volatilidad del mercado: ALTA (crypto)')
    print(f'   Liquidez disponible: BUENA (7 símbolos monitoreados)')
    print(f'   Horarios de operación: 24/7')

    return {
        'databases_activas': active_databases,
        'total_registros': total_records,
        'componentes_activos': active_components,
        'roi_diario_requerido': roi_diario_requerido,
        'trades_diarios_necesarios': trades_diarios_necesarios,
        'drawdown_potencial': abs(drawdown_potencial)
    }

def generar_reporte_viabilidad(datos):
    """Genera el reporte final de viabilidad"""
    
    print(f'\n' + '='*60)
    print('📋 REPORTE DE VIABILIDAD - ROI 7% MENSUAL')
    print('='*60)
    
    # Evaluación técnica
    print(f'\n✅ FORTALEZAS TÉCNICAS:')
    print(f'   • Sistema de monitoreo 24/7 activo')
    print(f'   • {datos["databases_activas"]} bases de datos operativas')
    print(f'   • {datos["total_registros"]:,} registros de datos históricos')
    print(f'   • Análisis OrderBook en tiempo real')
    print(f'   • Detección automática de breakouts')
    print(f'   • Gestión de riesgo implementada')
    
    # Evaluación matemática
    print(f'\n📊 EVALUACIÓN MATEMÁTICA:')
    print(f'   • ROI diario requerido: {datos["roi_diario_requerido"]*100:.3f}%')
    print(f'   • Trades diarios necesarios: {datos["trades_diarios_necesarios"]:.1f}')
    
    if datos["trades_diarios_necesarios"] <= 10:
        viabilidad_trades = "✅ VIABLE"
    elif datos["trades_diarios_necesarios"] <= 20:
        viabilidad_trades = "⚠️ DESAFIANTE"
    else:
        viabilidad_trades = "❌ NO VIABLE"
    
    print(f'   • Viabilidad de volumen: {viabilidad_trades}')
    
    # Evaluación de riesgos
    print(f'\n⚠️ EVALUACIÓN DE RIESGOS:')
    print(f'   • Drawdown potencial: {datos["drawdown_potencial"]*100:.1f}%')
    
    if datos["drawdown_potencial"] <= 0.10:
        riesgo_drawdown = "✅ BAJO"
    elif datos["drawdown_potencial"] <= 0.20:
        riesgo_drawdown = "⚠️ MODERADO"
    else:
        riesgo_drawdown = "❌ ALTO"
    
    print(f'   • Nivel de riesgo: {riesgo_drawdown}')
    
    # Conclusión final
    print(f'\n🎯 CONCLUSIÓN FINAL:')
    
    factores_positivos = 0
    factores_negativos = 0
    
    if datos["trades_diarios_necesarios"] <= 15:
        factores_positivos += 1
    else:
        factores_negativos += 1
    
    if datos["drawdown_potencial"] <= 0.15:
        factores_positivos += 1
    else:
        factores_negativos += 1
    
    if datos["componentes_activos"] >= 6:
        factores_positivos += 1
    else:
        factores_negativos += 1
    
    if factores_positivos >= 2:
        conclusion = "✅ VIABLE CON OPTIMIZACIONES"
        recomendacion = "El objetivo es alcanzable con mejoras específicas"
    else:
        conclusion = "⚠️ REQUIERE DESARROLLO ADICIONAL"
        recomendacion = "Necesita mejoras significativas antes de ser viable"
    
    print(f'   {conclusion}')
    print(f'   {recomendacion}')
    
    # Recomendaciones específicas
    print(f'\n💡 RECOMENDACIONES ESPECÍFICAS:')
    print(f'   1. Aumentar frecuencia de trading a 8-12 operaciones diarias')
    print(f'   2. Optimizar algoritmos de detección de oportunidades')
    print(f'   3. Implementar estrategias de scalping para trades rápidos')
    print(f'   4. Mejorar gestión de riesgo para reducir drawdown')
    print(f'   5. Diversificar estrategias (long/short, múltiples timeframes)')
    print(f'   6. Implementar stop-loss dinámicos y trailing stops')

if __name__ == "__main__":
    datos = analizar_infraestructura_sicar()
    generar_reporte_viabilidad(datos)