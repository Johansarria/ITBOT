#!/usr/bin/env python3
"""
AJUSTE DE LÍMITES DE TRADING PARA BALANCE ÓPTIMO
Balancear seguridad con viabilidad operativa
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def optimize_trading_limits():
    print("⚖️ OPTIMIZACIÓN DE LÍMITES DE TRADING")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"🎯 Objetivo: Seguridad óptima + Viabilidad operativa")
    
    # Análisis del balance actual
    current_balance = 5.86
    
    print(f"\n📊 ANÁLISIS DE BALANCE ACTUAL:")
    print(f"   💰 Balance Total: ${current_balance:.2f}")
    print(f"   🚨 Problema detectado: Límite $3.00 demasiado restrictivo")
    print(f"   📊 Con $3.00: Solo 1.95 trades antes de quedarse sin capital")
    
    # Cálculos para límites óptimos
    print(f"\n🎯 CÁLCULO DE LÍMITES ÓPTIMOS:")
    
    # Regla de gestión de riesgo: No más del 15-20% por trade
    recommended_percentages = [10, 12, 15, 18, 20]
    
    for pct in recommended_percentages:
        trade_size = (current_balance * pct) / 100
        max_trades = current_balance / trade_size
        print(f"   {pct:2d}% del balance: ${trade_size:.2f} (permite {max_trades:.1f} trades)")
    
    # Análisis de sostenibilidad
    print(f"\n📈 ANÁLISIS DE SOSTENIBILIDAD:")
    
    scenarios = [
        {"size": 1.0, "desc": "Ultra Conservador", "trades": current_balance / 1.0},
        {"size": 1.2, "desc": "Muy Conservador", "trades": current_balance / 1.2},
        {"size": 1.5, "desc": "Conservador Óptimo", "trades": current_balance / 1.5},
        {"size": 2.0, "desc": "Balanceado", "trades": current_balance / 2.0},
        {"size": 2.5, "desc": "Agresivo Controlado", "trades": current_balance / 2.5},
    ]
    
    for scenario in scenarios:
        trades_possible = scenario["trades"]
        pct_of_balance = (scenario["size"] / current_balance) * 100
        print(f"   ${scenario['size']:.1f} ({scenario['desc']}): {trades_possible:.1f} trades posibles ({pct_of_balance:.0f}%)")
    
    # Recomendación basada en análisis
    print(f"\n💡 RECOMENDACIÓN PROFESIONAL:")
    
    # Límite óptimo: 20-25% del balance pero con mínimo absoluto
    optimal_pct = 20
    optimal_size = (current_balance * optimal_pct) / 100
    
    # Ajustar a números redondos
    if optimal_size < 1.0:
        recommended_size = 1.0
    elif optimal_size < 1.5:
        recommended_size = 1.2
    else:
        recommended_size = round(optimal_size * 2) / 2  # Redondear a 0.5
    
    print(f"   🎯 Tamaño recomendado: ${recommended_size:.1f}")
    print(f"   📊 Representa: {(recommended_size/current_balance)*100:.0f}% del balance")
    print(f"   🔄 Permite: {current_balance/recommended_size:.1f} trades consecutivos")
    
    # Configuraciones ajustadas
    optimized_configs = {
        'MICRO_TRADE_MAX_USDT': recommended_size,
        'MAX_POSITION_SIZE_USDT': recommended_size + 0.5,  # Poco más para flexibilidad
        'MIN_BALANCE_FOR_TRADING': 0.5,  # Reducir umbral mínimo
        'RESERVE_BALANCE_PCT': 10,  # Reducir reserva de 20% a 10%
        'MAX_DAILY_LOSS_PCT': 8,  # Aumentar límite diario de 5% a 8%
        'MAX_TOTAL_EXPOSURE_PCT': 150,  # Aumentar de 120% a 150%
    }
    
    print(f"\n⚙️ CONFIGURACIONES AJUSTADAS:")
    for key, value in optimized_configs.items():
        print(f"   ✅ {key}: {value}")
    
    # Crear configuración optimizada
    try:
        with open('/app/config.py', 'r') as f:
            current_config = f.read()
        
        # Reemplazar configuraciones específicas
        import re
        
        replacements = {
            r'MICRO_TRADE_MAX_USDT[:\s]*=?\s*[\d.]+': f'MICRO_TRADE_MAX_USDT: float = {optimized_configs["MICRO_TRADE_MAX_USDT"]}',
            r'MAX_POSITION_SIZE_USDT[:\s]*=?\s*[\d.]+': f'MAX_POSITION_SIZE_USDT: float = {optimized_configs["MAX_POSITION_SIZE_USDT"]}',
            r'MIN_BALANCE_FOR_TRADING[:\s]*=?\s*[\d.]+': f'MIN_BALANCE_FOR_TRADING: float = {optimized_configs["MIN_BALANCE_FOR_TRADING"]}',
            r'RESERVE_BALANCE_PCT[:\s]*=?\s*[\d.]+': f'RESERVE_BALANCE_PCT: int = {optimized_configs["RESERVE_BALANCE_PCT"]}',
            r'MAX_DAILY_LOSS_PCT[:\s]*=?\s*[\d.]+': f'MAX_DAILY_LOSS_PCT: int = {optimized_configs["MAX_DAILY_LOSS_PCT"]}',
            r'MAX_TOTAL_EXPOSURE_PCT[:\s]*=?\s*[\d.]+': f'MAX_TOTAL_EXPOSURE_PCT: int = {optimized_configs["MAX_TOTAL_EXPOSURE_PCT"]}',
        }
        
        updated_config = current_config
        for pattern, replacement in replacements.items():
            updated_config = re.sub(pattern, replacement, updated_config)
        
        # Agregar comentario de optimización
        optimization_comment = f'''
# ==========================================
# LÍMITES OPTIMIZADOS POST-ANÁLISIS
# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Balance: ${current_balance:.2f}
# Tamaño óptimo: ${recommended_size:.1f} ({(recommended_size/current_balance)*100:.0f}% del balance)
# Trades posibles: {current_balance/recommended_size:.1f}
# ==========================================

'''
        
        if "# LÍMITES OPTIMIZADOS POST-ANÁLISIS" not in updated_config:
            updated_config = optimization_comment + updated_config
        
        with open('/app/config_optimized.py', 'w') as f:
            f.write(updated_config)
        
        print(f"\n✅ Configuración optimizada guardada")
        
    except Exception as e:
        print(f"❌ Error creando configuración optimizada: {e}")
        return False
    
    # Comparación con límites anteriores
    print(f"\n📊 COMPARACIÓN DE LÍMITES:")
    print(f"   Anterior (muy conservador): $3.00 → {current_balance/3.0:.1f} trades")
    print(f"   Optimizado (balanceado): ${recommended_size:.1f} → {current_balance/recommended_size:.1f} trades")
    print(f"   Mejora operativa: {((current_balance/recommended_size) / (current_balance/3.0) - 1)*100:+.0f}%")
    
    # Análisis de riesgo con nuevos límites
    print(f"\n🛡️ ANÁLISIS DE RIESGO:")
    
    # Escenario pesimista: 3 pérdidas consecutivas
    worst_case_loss = recommended_size * 3
    remaining_after_losses = current_balance - worst_case_loss
    
    print(f"   📊 3 pérdidas consecutivas: -${worst_case_loss:.2f}")
    print(f"   💰 Balance restante: ${remaining_after_losses:.2f}")
    print(f"   🎯 % del balance original: {(remaining_after_losses/current_balance)*100:.0f}%")
    
    if remaining_after_losses > 1.0:
        risk_status = "✅ RIESGO ACEPTABLE"
    elif remaining_after_losses > 0.5:
        risk_status = "⚠️ RIESGO MODERADO"
    else:
        risk_status = "🚨 RIESGO ALTO"
    
    print(f"   🎯 Evaluación: {risk_status}")
    
    return True, optimized_configs

def apply_optimized_limits():
    """Aplicar los límites optimizados"""
    print(f"\n⚡ APLICANDO LÍMITES OPTIMIZADOS:")
    
    try:
        # Reemplazar configuración actual
        import shutil
        shutil.copy('/app/config_optimized.py', '/app/config.py')
        
        print(f"   ✅ Configuración optimizada aplicada")
        print(f"   🔄 Requiere reinicio de servicios para activar")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error aplicando configuración: {e}")
        return False

if __name__ == "__main__":
    print(f"🎯 INICIANDO OPTIMIZACIÓN DE LÍMITES")
    
    success, configs = optimize_trading_limits()
    
    if success:
        apply_result = apply_optimized_limits()
        
        if apply_result:
            print(f"\n✅ OPTIMIZACIÓN COMPLETADA")
            print(f"🎯 Nuevos límites balancean seguridad y viabilidad")
            print(f"💡 Reiniciar servicios para activar cambios")
        else:
            print(f"\n❌ ERROR EN APLICACIÓN")
    else:
        print(f"\n❌ ERROR EN OPTIMIZACIÓN")
