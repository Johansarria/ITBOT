#!/usr/bin/env python3
"""
CONFIGURACIÓN PARA MICRO-PRUEBAS SEGURAS
Ajustar límites para pruebas con pérdida máxima diaria 10% del capital
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def configure_micro_testing_limits():
    print("🧪 CONFIGURACIÓN DE MICRO-PRUEBAS SEGURAS")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    
    current_balance = 5.86
    daily_loss_limit_pct = 10  # 10% máximo diario
    daily_loss_limit_usd = current_balance * (daily_loss_limit_pct / 100)
    
    print(f"💰 Balance actual: ${current_balance:.2f}")
    print(f"📊 Límite pérdida diaria: {daily_loss_limit_pct}% = ${daily_loss_limit_usd:.2f}")
    
    # Calcular límites para micro-pruebas
    # Si queremos hacer múltiples pruebas por día, cada una debe ser muy pequeña
    max_loss_per_trade = daily_loss_limit_usd / 4  # Permitir hasta 4 pérdidas por día
    
    # Con SL de 2%, el tamaño de posición debe ser:
    # Pérdida = Posición * SL%
    # Posición = Pérdida / SL%
    sl_percentage = 2  # 2% stop loss
    max_position_size = max_loss_per_trade / (sl_percentage / 100)
    
    print(f"\n🧪 CÁLCULOS PARA MICRO-PRUEBAS:")
    print(f"   📉 Máx pérdida por trade: ${max_loss_per_trade:.2f}")
    print(f"   🛡️ Stop Loss: {sl_percentage}%")
    print(f"   💰 Máx posición calculada: ${max_position_size:.2f}")
    
    # Ajustar a valores prácticos y seguros
    recommended_max_trade = min(max_position_size, 0.75)  # Máximo $0.75 por trade
    
    print(f"   ✅ Recomendado por trade: ${recommended_max_trade:.2f}")
    
    # 1. Leer configuración actual
    try:
        with open('/app/config.py', 'r') as f:
            current_config = f.read()
        
        print(f"\n📋 Configuración actual leída")
        
    except Exception as e:
        print(f"❌ Error leyendo configuración: {e}")
        return False
    
    # 2. Configuraciones de micro-pruebas
    micro_test_configs = {
        # Límites ultra-conservadores para micro-pruebas
        'MICRO_TRADE_MAX_USDT': 0.75,  # Máximo $0.75 por trade
        'MAX_POSITION_SIZE_USDT': 0.80,  # Absoluto máximo $0.80
        'MAX_CONCURRENT_POSITIONS': 3,  # Permitir hasta 3 micro-posiciones
        
        # Control estricto de pérdidas
        'MAX_DAILY_LOSS_PCT': 10,  # 10% pérdida diaria máxima
        'MAX_DAILY_LOSS_USD': round(daily_loss_limit_usd, 2),
        'MAX_LOSS_PER_TRADE_USD': round(max_loss_per_trade, 2),
        
        # Balance y reservas
        'MIN_BALANCE_FOR_TRADING': 1.0,  # Parar si balance < $1
        'RESERVE_BALANCE_PCT': 15,  # Solo 15% reserva para micro-pruebas
        
        # Filtros de entrada (mantener alta calidad)
        'ML_THRESHOLD_LOW': 0.65,  # Mantener alta selectividad
        'MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT': 18.0,  # ROI mínimo 18%
        'MIN_CONFIDENCE_SCORE': 0.70,  # Confianza mínima
        
        # Stop Loss muy conservador para micro-pruebas
        'MANDATORY_STOP_LOSS': True,
        'MAX_SL_DISTANCE_PCT': 2.0,  # SL máximo 2%
        'AUTO_TRAILING_STOP': True,
        'BREAK_EVEN_MOVE_THRESHOLD': 1.0,  # Mover a BE con solo 1% ganancia
        
        # Control de frecuencia para pruebas
        'MAX_TRADES_PER_HOUR': 1,  # Solo 1 trade por hora para micro-pruebas
        'COOL_DOWN_AFTER_LOSS_MINUTES': 60,  # 1 hora de pausa después de pérdida
        'MAX_TRADES_PER_DAY': 4,  # Máximo 4 pruebas por día
        
        # Monitoreo intensivo
        'POSITION_MONITOR_INTERVAL': 120,  # Cada 2 minutos
        'RISK_ALERT_THRESHOLD': 8,  # Alertar si riesgo > 8%
    }
    
    print(f"\n🛡️ CONFIGURACIONES DE MICRO-PRUEBAS:")
    for key, value in micro_test_configs.items():
        print(f"   ✅ {key}: {value}")
    
    # 3. Crear configuración actualizada
    config_additions = f'''
# ==========================================
# CONFIGURACIÓN DE MICRO-PRUEBAS SEGURAS
# Pérdida máxima diaria: 10% del capital
# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Balance: ${current_balance:.2f}
# ==========================================

# Límites ultra-conservadores para micro-pruebas
MICRO_TRADE_MAX_USDT: float = {micro_test_configs['MICRO_TRADE_MAX_USDT']}
MAX_POSITION_SIZE_USDT: float = {micro_test_configs['MAX_POSITION_SIZE_USDT']}
MAX_CONCURRENT_POSITIONS: int = {micro_test_configs['MAX_CONCURRENT_POSITIONS']}

# Control estricto de pérdidas diarias
MAX_DAILY_LOSS_PCT: int = {micro_test_configs['MAX_DAILY_LOSS_PCT']}
MAX_DAILY_LOSS_USD: float = {micro_test_configs['MAX_DAILY_LOSS_USD']}
MAX_LOSS_PER_TRADE_USD: float = {micro_test_configs['MAX_LOSS_PER_TRADE_USD']}

# Balance y reservas para micro-pruebas
MIN_BALANCE_FOR_TRADING: float = {micro_test_configs['MIN_BALANCE_FOR_TRADING']}
RESERVE_BALANCE_PCT: int = {micro_test_configs['RESERVE_BALANCE_PCT']}

# Filtros de entrada (alta calidad)
ML_THRESHOLD_LOW: float = {micro_test_configs['ML_THRESHOLD_LOW']}
MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT: float = {micro_test_configs['MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT']}
MIN_CONFIDENCE_SCORE: float = {micro_test_configs['MIN_CONFIDENCE_SCORE']}

# Stop Loss conservador para micro-pruebas
MANDATORY_STOP_LOSS: bool = {micro_test_configs['MANDATORY_STOP_LOSS']}
MAX_SL_DISTANCE_PCT: float = {micro_test_configs['MAX_SL_DISTANCE_PCT']}
AUTO_TRAILING_STOP: bool = {micro_test_configs['AUTO_TRAILING_STOP']}
BREAK_EVEN_MOVE_THRESHOLD: float = {micro_test_configs['BREAK_EVEN_MOVE_THRESHOLD']}

# Control de frecuencia para pruebas controladas
MAX_TRADES_PER_HOUR: int = {micro_test_configs['MAX_TRADES_PER_HOUR']}
COOL_DOWN_AFTER_LOSS_MINUTES: int = {micro_test_configs['COOL_DOWN_AFTER_LOSS_MINUTES']}
MAX_TRADES_PER_DAY: int = {micro_test_configs['MAX_TRADES_PER_DAY']}

# Monitoreo intensivo
POSITION_MONITOR_INTERVAL: int = {micro_test_configs['POSITION_MONITOR_INTERVAL']}
RISK_ALERT_THRESHOLD: int = {micro_test_configs['RISK_ALERT_THRESHOLD']}

# Modo de micro-pruebas
MICRO_TESTING_MODE: bool = True
ULTRA_SAFE_MODE: bool = True
CAPITAL_PRESERVATION_ABSOLUTE: bool = True

'''
    
    # Eliminar configuraciones anteriores conflictivas
    import re
    
    patterns_to_remove = [
        r'MICRO_TRADE_MAX_USDT[:\s]*=?\s*[\d.]+.*\n',
        r'MAX_DAILY_LOSS_PCT[:\s]*=?\s*[\d.]+.*\n',
        r'ML_THRESHOLD_LOW[:\s]*=?\s*[\d.]+.*\n',
        r'MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT[:\s]*=?\s*[\d.]+.*\n',
        r'MAX_TRADES_PER_HOUR[:\s]*=?\s*[\d.]+.*\n',
    ]
    
    updated_config = current_config
    for pattern in patterns_to_remove:
        updated_config = re.sub(pattern, '', updated_config)
    
    # Remover configuraciones previas de seguridad para evitar duplicados
    if "# CONFIGURACIÓN DE MICRO-PRUEBAS SEGURAS" not in updated_config:
        updated_config += config_additions
    
    # 4. Guardar configuración
    try:
        with open('/app/config_micro_testing.py', 'w') as f:
            f.write(updated_config)
        
        print(f"\n✅ Configuración de micro-pruebas guardada")
        
    except Exception as e:
        print(f"❌ Error guardando configuración: {e}")
        return False
    
    # 5. Mostrar impacto de la configuración
    print(f"\n📊 IMPACTO DE MICRO-PRUEBAS:")
    print(f"   💰 Máximo por trade: ${micro_test_configs['MICRO_TRADE_MAX_USDT']:.2f}")
    print(f"   📊 Trades por día: máximo {micro_test_configs['MAX_TRADES_PER_DAY']}")
    print(f"   📉 Pérdida máxima por trade: ${micro_test_configs['MAX_LOSS_PER_TRADE_USD']:.2f}")
    print(f"   📉 Pérdida máxima diaria: ${micro_test_configs['MAX_DAILY_LOSS_USD']:.2f} ({micro_test_configs['MAX_DAILY_LOSS_PCT']}%)")
    
    # Ejemplo de escenarios
    print(f"\n🧪 ESCENARIOS DE MICRO-PRUEBAS:")
    print(f"   ✅ Escenario optimista: 4 trades ganadores = +${4 * 0.02:.2f}")
    print(f"   ⚠️ Escenario pesimista: 4 trades perdedores = -${micro_test_configs['MAX_DAILY_LOSS_USD']:.2f}")
    print(f"   📊 Balance después del peor día: ${current_balance - micro_test_configs['MAX_DAILY_LOSS_USD']:.2f}")
    
    # Días de supervivencia
    survival_days = current_balance / micro_test_configs['MAX_DAILY_LOSS_USD']
    print(f"   🛡️ Días de supervivencia (peor caso): {survival_days:.0f} días")
    
    print(f"\n💡 VENTAJAS DE MICRO-PRUEBAS:")
    advantages = [
        "✅ Riesgo mínimo por operación",
        "✅ Múltiples oportunidades de aprendizaje",
        "✅ Capital preservado a largo plazo",
        "✅ Datos estadísticos confiables",
        "✅ Stress testing del sistema",
        "✅ Optimización gradual de parámetros"
    ]
    
    for advantage in advantages:
        print(f"   {advantage}")
    
    return True

def show_activation_steps():
    """Mostrar pasos para activar micro-pruebas"""
    print(f"\n" + "="*60)
    print(f"📋 PASOS PARA ACTIVAR MICRO-PRUEBAS")
    print(f"="*60)
    
    steps = [
        "1️⃣ Aplicar configuración: cp config_micro_testing.py config.py",
        "2️⃣ Reiniciar servicios: docker-compose restart", 
        "3️⃣ Verificar límites aplicados",
        "4️⃣ Iniciar micro-pruebas controladas"
    ]
    
    for step in steps:
        print(f"   {step}")
    
    print(f"\n🎯 RESULTADO ESPERADO:")
    print(f"   🧪 Sistema listo para micro-pruebas ultra-seguras")
    print(f"   📊 Máximo riesgo diario: 10% del capital")
    print(f"   🛡️ Capital protegido para operación a largo plazo")

if __name__ == "__main__":
    success = configure_micro_testing_limits()
    
    if success:
        show_activation_steps()
        print(f"\n✅ CONFIGURACIÓN DE MICRO-PRUEBAS COMPLETADA")
        print(f"🧪 Lista para activar modo ultra-seguro")
    else:
        print(f"\n❌ ERROR EN CONFIGURACIÓN")
