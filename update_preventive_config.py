#!/usr/bin/env python3
"""
CONFIGURACIÓN PREVENTIVA PARA FUTUROS TRADES
Ajustar configuraciones para evitar sobreexposición futura
"""

import sys
import os
sys.path.append('/app')

def update_preventive_configuration():
    print("⚙️ CONFIGURACIÓN PREVENTIVA ANTI-SOBREEXPOSICIÓN")
    print("=" * 60)
    
    # 1. Leer configuración actual
    try:
        with open('/app/config.py', 'r') as f:
            config_content = f.read()
        
        print("📋 Configuración actual detectada")
        
        # 2. Identificar valores críticos actuales
        current_configs = {}
        for line in config_content.split('\n'):
            if 'MICRO_TRADE_MAX_USDT' in line and '=' in line:
                current_configs['MICRO_TRADE_MAX_USDT'] = line.strip()
            elif 'POSITION_MAX_PERCENTAGE' in line and '=' in line:
                current_configs['POSITION_MAX_PERCENTAGE'] = line.strip()
            elif 'MAX_OPEN_POSITIONS' in line and '=' in line:
                current_configs['MAX_OPEN_POSITIONS'] = line.strip()
        
        print("\n📊 CONFIGURACIONES DE RIESGO ACTUALES:")
        for key, value in current_configs.items():
            print(f"   {key}: {value}")
        
        # 3. Calcular nuevos valores seguros
        print(f"\n🛡️ NUEVAS CONFIGURACIONES RECOMENDADAS:")
        
        new_configs = {
            'MICRO_TRADE_MAX_USDT': 3.0,  # Reducir de ~7.52 a 3.0 (50% del balance)
            'POSITION_MAX_PERCENTAGE_OF_BALANCE': 40,  # Máximo 40% del balance por posición
            'MAX_CONCURRENT_POSITIONS': 2,  # Máximo 2 posiciones simultáneas
            'EMERGENCY_BALANCE_THRESHOLD': 1.0,  # Parar trading si balance < $1
            'MAX_TOTAL_EXPOSURE_PERCENTAGE': 150,  # Máximo 150% de exposición total
        }
        
        for key, value in new_configs.items():
            print(f"   ✅ {key}: {value}")
        
        # 4. Preparar configuración actualizada
        updated_config = config_content
        
        # Actualizar MICRO_TRADE_MAX_USDT
        if 'MICRO_TRADE_MAX_USDT' in updated_config:
            import re
            pattern = r'MICRO_TRADE_MAX_USDT\s*=\s*[\d.]+(\s*#.*)?'
            replacement = f'MICRO_TRADE_MAX_USDT = {new_configs["MICRO_TRADE_MAX_USDT"]}  # Reducido para prevenir sobreexposición'
            updated_config = re.sub(pattern, replacement, updated_config)
        else:
            # Agregar si no existe
            updated_config += f'\n# Configuración preventiva de riesgo\nMICRO_TRADE_MAX_USDT = {new_configs["MICRO_TRADE_MAX_USDT"]}\n'
        
        # Agregar configuraciones adicionales de seguridad
        safety_config = f"""
# ==========================================
# CONFIGURACIONES DE SEGURIDAD ANTI-RIESGO
# Agregadas después de evento de sobreexposición
# ==========================================

# Límites de exposición por posición
POSITION_MAX_PERCENTAGE_OF_BALANCE = {new_configs["POSITION_MAX_PERCENTAGE_OF_BALANCE"]}

# Límite de posiciones concurrentes
MAX_CONCURRENT_POSITIONS = {new_configs["MAX_CONCURRENT_POSITIONS"]}

# Balance mínimo para continuar trading
EMERGENCY_BALANCE_THRESHOLD = {new_configs["EMERGENCY_BALANCE_THRESHOLD"]}

# Exposición total máxima permitida
MAX_TOTAL_EXPOSURE_PERCENTAGE = {new_configs["MAX_TOTAL_EXPOSURE_PERCENTAGE"]}

# Control de riesgo dinámico
DYNAMIC_RISK_CONTROL = True
BALANCE_PROTECTION_MODE = True

# Monitoreo cada 5 minutos en situación de riesgo
RISK_MONITORING_INTERVAL = 300  # segundos

"""
        
        if "# CONFIGURACIONES DE SEGURIDAD ANTI-RIESGO" not in updated_config:
            updated_config += safety_config
        
        # 5. Escribir configuración actualizada
        with open('/app/config_updated.py', 'w') as f:
            f.write(updated_config)
        
        print(f"\n✅ Configuración actualizada guardada en config_updated.py")
        
        # 6. Mostrar resumen de cambios
        print(f"\n📋 RESUMEN DE CAMBIOS CRÍTICOS:")
        print(f"   🎯 Tamaño máximo por trade: ${new_configs['MICRO_TRADE_MAX_USDT']:.1f} (vs ~$7.5 anterior)")
        print(f"   🎯 Máximo por posición: {new_configs['POSITION_MAX_PERCENTAGE_OF_BALANCE']}% del balance")
        print(f"   🎯 Posiciones concurrentes: {new_configs['MAX_CONCURRENT_POSITIONS']}")
        print(f"   🎯 Exposición total máxima: {new_configs['MAX_TOTAL_EXPOSURE_PERCENTAGE']}%")
        
        # 7. Cálculo de impacto en balance actual
        current_balance = 6.11
        new_max_per_trade = new_configs['MICRO_TRADE_MAX_USDT']
        max_exposure = (new_max_per_trade * new_configs['MAX_CONCURRENT_POSITIONS'])
        
        print(f"\n💡 IMPACTO EN BALANCE ACTUAL (${current_balance:.2f}):")
        print(f"   💰 Máximo por trade: ${new_max_per_trade:.2f} ({(new_max_per_trade/current_balance)*100:.0f}% del balance)")
        print(f"   💰 Exposición máxima total: ${max_exposure:.2f} ({(max_exposure/current_balance)*100:.0f}% del balance)")
        print(f"   ✅ Reducción de riesgo: ~{((28.59 - max_exposure)/28.59)*100:.0f}% menos exposición")
        
        # 8. Instrucciones para aplicar cambios
        print(f"\n📌 INSTRUCCIONES PARA APLICAR:")
        print(f"   1️⃣ Revisar config_updated.py")
        print(f"   2️⃣ Reemplazar config.py cuando esté listo")
        print(f"   3️⃣ Reiniciar servicios para aplicar cambios")
        print(f"   4️⃣ Validar que no se abran posiciones > ${new_max_per_trade:.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando configuración: {e}")
        return False

if __name__ == "__main__":
    success = update_preventive_configuration()
    if success:
        print("\n✅ CONFIGURACIÓN PREVENTIVA COMPLETADA")
        print("🛡️ Sistema preparado para prevenir futura sobreexposición")
    else:
        print("\n❌ ERROR EN CONFIGURACIÓN PREVENTIVA")
