#!/usr/bin/env python3
"""
Análisis de Impacto del OrderBook en Decisiones de Trading
Compara métricas antes y después de la integración
"""

import sqlite3
import os
from datetime import datetime, timedelta

def analizar_impacto_orderbook():
    print('🔍 ANÁLISIS DE IMPACTO DEL ORDERBOOK EN DECISIONES')
    print('='*60)

    # Análisis de métricas de orderbook por símbolo
    orderbook_db = 'orderbook_analysis.db'
    if os.path.exists(orderbook_db):
        conn = sqlite3.connect(orderbook_db)
        cursor = conn.cursor()
        
        # Análisis por símbolo
        cursor.execute('''SELECT symbol, COUNT(*) as registros, 
                         AVG(spread_percentage) as avg_spread, 
                         AVG(liquidity_score) as avg_liquidity, 
                         AVG(depth_quality) as avg_quality 
                         FROM orderbook_metrics 
                         GROUP BY symbol 
                         ORDER BY registros DESC''')
        symbol_stats = cursor.fetchall()
        
        print('📊 ESTADÍSTICAS POR SÍMBOLO:')
        print('-' * 60)
        for symbol, count, avg_spread, avg_liquidity, avg_quality in symbol_stats:
            print(f'{symbol:8} | {count:3} registros | Spread: {avg_spread:.4f}% | Liquidez: {avg_liquidity:.1f} | Calidad: {avg_quality:.1f}%')
        
        # Análisis temporal
        print('\n⏰ ANÁLISIS TEMPORAL:')
        print('-' * 60)
        cursor.execute('''SELECT DATE(timestamp) as fecha, 
                         COUNT(*) as mediciones, 
                         AVG(spread_percentage) as avg_spread 
                         FROM orderbook_metrics 
                         GROUP BY DATE(timestamp) 
                         ORDER BY fecha DESC''')
        daily_stats = cursor.fetchall()
        
        for fecha, mediciones, avg_spread in daily_stats:
            print(f'{fecha} | {mediciones:2} mediciones | Spread promedio: {avg_spread:.4f}%')
        
        # Alertas de calidad
        print('\n🚨 ALERTAS DE CALIDAD DEL ORDERBOOK:')
        print('-' * 60)
        cursor.execute('''SELECT symbol, alert_type, COUNT(*) as cantidad 
                         FROM orderbook_alerts 
                         GROUP BY symbol, alert_type 
                         ORDER BY cantidad DESC''')
        alert_stats = cursor.fetchall()
        
        for symbol, alert_type, cantidad in alert_stats:
            print(f'{symbol:8} | {alert_type:20} | {cantidad:2} alertas')
        
        conn.close()

    print('\n' + '='*60)

    # Análisis de correlación con performance
    advanced_db = 'advanced_logging.db'
    if os.path.exists(advanced_db):
        conn = sqlite3.connect(advanced_db)
        cursor = conn.cursor()
        
        print('📈 CORRELACIÓN CON PERFORMANCE:')
        print('-' * 60)
        
        # Performance reciente
        cursor.execute('''SELECT COUNT(*) as total_metrics 
                         FROM performance_metrics 
                         WHERE timestamp > datetime('now', '-24 hours')''')
        total_metrics = cursor.fetchone()[0]
        
        if total_metrics > 0:
            print(f'Métricas últimas 24h: {total_metrics}')
            
            # Obtener estadísticas de performance
            cursor.execute('''SELECT AVG(cpu_usage_percent), AVG(memory_usage_mb), AVG(api_response_time_ms) 
                             FROM performance_metrics 
                             WHERE timestamp > datetime('now', '-24 hours')''')
            perf_data = cursor.fetchone()
            
            if perf_data[0] is not None:
                print(f'CPU promedio: {perf_data[0]:.1f}%')
                print(f'Memoria promedio: {perf_data[1]:.1f}MB')
                print(f'Tiempo respuesta API: {perf_data[2]:.1f}ms')
        
        # Logs por nivel
        cursor.execute('''SELECT level, COUNT(*) 
                         FROM log_entries 
                         WHERE timestamp > datetime('now', '-24 hours') 
                         GROUP BY level''')
        log_levels = cursor.fetchall()
        
        print('\n📝 LOGS ÚLTIMAS 24H:')
        for level, count in log_levels:
            print(f'{level:12} | {count:5} entradas')
        
        conn.close()

    print('\n' + '='*60)
    
    # Análisis de monitoreo proactivo
    proactive_db = 'proactive_monitoring.db'
    if os.path.exists(proactive_db):
        conn = sqlite3.connect(proactive_db)
        cursor = conn.cursor()
        
        print('🔍 MONITOREO PROACTIVO:')
        print('-' * 60)
        
        # Alertas recientes
        cursor.execute('''SELECT COUNT(*) 
                         FROM alerts 
                         WHERE timestamp > datetime('now', '-24 hours')''')
        recent_alerts = cursor.fetchone()[0]
        print(f'Alertas últimas 24h: {recent_alerts}')
        
        # System metrics
        cursor.execute('''SELECT COUNT(*) 
                         FROM system_metrics 
                         WHERE timestamp > datetime('now', '-24 hours')''')
        sys_metrics = cursor.fetchone()[0]
        print(f'Métricas de sistema: {sys_metrics}')
        
        conn.close()
    
    print('✅ ANÁLISIS DE IMPACTO COMPLETADO')

if __name__ == "__main__":
    analizar_impacto_orderbook()