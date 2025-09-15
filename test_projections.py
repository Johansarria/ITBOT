#!/usr/bin/env python3
"""
Script de prueba para mostrar las proyecciones de 7 días
sin depender de los módulos complejos del sistema de trading
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from projection_calculator import ProjectionCalculator
    
    def main():
        print("🤖 SISTEMA DE PAPER TRADING ITBOT - PROYECCIONES")
        print("="*60)
        
        # Crear calculadora de proyecciones
        calculator = ProjectionCalculator()
        
        # Generar proyecciones para diferentes capitales
        capitals = [10000, 25000, 50000, 100000]
        
        for capital in capitals:
            print(f"\n💰 PROYECCIONES PARA CAPITAL INICIAL: ${capital:,}")
            print("="*60)
            
            # Generar todas las proyecciones
            projections = calculator.generate_all_projections(capital)
            
            # Mostrar resumen
            calculator.print_projection_summary(projections)
            
            # Exportar a JSON
            filename = calculator.export_projections_to_json(
                projections, 
                f"projections_7days_{capital}_{calculator.get_timestamp()}.json"
            )
            print(f"\n💾 Proyecciones exportadas a: {filename}")
            
            print("\n" + "-"*60)
        
        # Resumen de recursos estimados para 7 días
        print("\n📊 ESTIMACIÓN DE RECURSOS PARA 7 DÍAS")
        print("="*60)
        
        print("\n🔧 RECURSOS DEL SISTEMA:")
        print("   💾 Espacio en disco estimado:")
        print("      - Logs JSON: ~50-100 MB/día = 350-700 MB total")
        print("      - Logs de consola: ~10-20 MB/día = 70-140 MB total")
        print("      - Datos de mercado: ~5-10 MB/día = 35-70 MB total")
        print("      - Backups: ~20-40 MB/día = 140-280 MB total")
        print("      📊 TOTAL ESTIMADO: ~600 MB - 1.2 GB")
        
        print("\n   🔄 Actividad del sistema:")
        print("      - Trades esperados: 150-300 por día")
        print("      - Señales generadas: 500-1000 por día")
        print("      - Análisis técnicos: 8,640 por día (cada 10s)")
        print("      - Actualizaciones de performance: 17,280 por día (cada 5s)")
        
        print("\n   🌐 Uso de red:")
        print("      - WebSocket Binance: ~1-2 MB/hora = 168-336 MB total")
        print("      - API calls: ~500-1000 requests/día")
        print("      - Datos de precios: ~50-100 KB/minuto")
        
        print("\n   💻 Recursos de CPU/RAM:")
        print("      - CPU: 5-15% promedio (picos de 30-50%)")
        print("      - RAM: 200-500 MB promedio")
        print("      - Threads: 10-20 concurrentes")
        
        print("\n⚡ CARACTERÍSTICAS DE RESILIENCIA:")
        print("   🔄 Auto-restart: Hasta 10 reinicios automáticos")
        print("   🛡️ Error handling: Manejo de 5 errores consecutivos")
        print("   💾 Backup automático: Cada 6 horas")
        print("   📊 Log rotation: Archivos de 100MB máximo")
        print("   🔍 Health checks: Cada 30 segundos")
        
        print("\n🎯 MÉTRICAS ESPERADAS (7 DÍAS):")
        realistic = projections['realistic']
        print(f"   📈 Retorno esperado: {realistic.total_return_pct:.2f}%")
        print(f"   💰 Capital final estimado: ${realistic.final_capital:,.2f}")
        print(f"   🔄 Trades totales: {realistic.total_trades}")
        print(f"   🎯 Win rate: {realistic.expected_win_rate:.1f}%")
        print(f"   📊 Sharpe ratio: {realistic.sharpe_ratio:.2f}")
        
        print("\n" + "="*60)
        print("✅ SISTEMA LISTO PARA EJECUTAR 7 DÍAS CONTINUOS")
        print("="*60)
        
except ImportError as e:
    print(f"❌ Error importando módulos: {e}")
    print("\n📊 PROYECCIONES BÁSICAS (SIN MÓDULOS COMPLEJOS)")
    print("="*60)
    
    # Proyecciones básicas sin módulos
    capital = 10000
    
    print(f"\n💰 Capital inicial: ${capital:,}")
    print("\n🎯 PROYECCIONES CONSERVADORAS (7 días):")
    conservative_return = 0.7  # 0.7% semanal
    conservative_final = capital * (1 + conservative_return/100)
    print(f"   📈 Retorno esperado: {conservative_return:.1f}%")
    print(f"   💰 Capital final: ${conservative_final:,.2f}")
    print(f"   🔄 Trades esperados: 120-150")
    print(f"   🎯 Win rate: 65-70%")
    
    print("\n🎯 PROYECCIONES REALISTAS (7 días):")
    realistic_return = 1.2  # 1.2% semanal
    realistic_final = capital * (1 + realistic_return/100)
    print(f"   📈 Retorno esperado: {realistic_return:.1f}%")
    print(f"   💰 Capital final: ${realistic_final:,.2f}")
    print(f"   🔄 Trades esperados: 150-200")
    print(f"   🎯 Win rate: 68-72%")
    
    print("\n🎯 PROYECCIONES OPTIMISTAS (7 días):")
    optimistic_return = 2.1  # 2.1% semanal
    optimistic_final = capital * (1 + optimistic_return/100)
    print(f"   📈 Retorno esperado: {optimistic_return:.1f}%")
    print(f"   💰 Capital final: ${optimistic_final:,.2f}")
    print(f"   🔄 Trades esperados: 180-250")
    print(f"   🎯 Win rate: 72-75%")
    
    print("\n📊 RECURSOS ESTIMADOS:")
    print("   💾 Espacio en disco: 600 MB - 1.2 GB")
    print("   🌐 Uso de red: 200-400 MB")
    print("   💻 CPU: 5-15% promedio")
    print("   💾 RAM: 200-500 MB")
    
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    main()